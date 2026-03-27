import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import frontmatter

from .models import Session, LogEntry
from . import get_logger

logger = get_logger(__name__)

def detect_claude_session_id() -> str:
    """Auto-detect the current Claude Code session ID.

    Walks up the process tree checking ~/.claude/sessions/{pid}.json
    since the MCP server is a child process of Claude Code.
    """
    sessions_dir = Path.home() / ".claude" / "sessions"
    if not sessions_dir.exists():
        return ""

    pid = os.getpid()
    for _ in range(5):
        session_file = sessions_dir / f"{pid}.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                session_id = data.get("sessionId", "")
                if session_id:
                    logger.info(f"Detected Claude session: {session_id} (pid {pid})")
                    return session_id
            except (json.JSONDecodeError, OSError):
                pass
        try:
            result = subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(pid)],
                capture_output=True,
                text=True,
                timeout=2,
            )
            ppid = int(result.stdout.strip())
            if ppid <= 1:
                break
            pid = ppid
        except Exception:
            break

    return ""


DEFAULT_VAULT = Path.home() / "Documents" / "Anamnesis"

# Regex patterns for parsing markdown body
ENTRY_HEADER = re.compile(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})")
PLAN_RE = re.compile(r"^- \*\*Plan\*\*:\s*(.+)", re.DOTALL)
DONE_RE = re.compile(r"^- \*\*Done\*\*:\s*(.+)", re.DOTALL)
OPEN_RE = re.compile(r"^- \*\*Open\*\*:\s*(.+)", re.DOTALL)

# Footer fallback (for files without YAML frontmatter)
FOOTER_HOST = re.compile(
    r"\*Session: `([^`]+)` \| Updated: ([^|]+)\| Host: ([^(]+)\(([^)]+)\)\*"
)
FOOTER_SIMPLE = re.compile(r"\*Session: `([^`]+)` \| Updated: ([^*]+)\*")
FOOTER_DIR = re.compile(r"\*Session: `([^`]+)` \| Directory: `([^`]+)`\*")


def _parse_entries(text: str) -> list[LogEntry]:
    """Parse ## timestamped entries from markdown body."""
    entries = []
    chunks = re.split(
        r"(?=^## \d{4}-\d{2}-\d{2} \d{2}:\d{2})", text, flags=re.MULTILINE
    )

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        header_match = ENTRY_HEADER.match(chunk)
        if not header_match:
            continue

        timestamp = header_match.group(1)
        body = chunk[header_match.end() :].strip()

        plan = done = open_items = ""
        current_bullet = ""
        bullet_lines: list[str] = []

        for line in body.split("\n"):
            if line.startswith("- **"):
                if current_bullet:
                    bullet_lines.append(current_bullet)
                current_bullet = line
            elif current_bullet:
                current_bullet += "\n" + line

        if current_bullet:
            bullet_lines.append(current_bullet)

        for bullet in bullet_lines:
            m = PLAN_RE.match(bullet)
            if m:
                plan = m.group(1).strip()
                continue
            m = DONE_RE.match(bullet)
            if m:
                done = m.group(1).strip()
                continue
            m = OPEN_RE.match(bullet)
            if m:
                open_items = m.group(1).strip()

        entries.append(
            LogEntry(
                timestamp=timestamp,
                plan=plan,
                done=done,
                open_items=open_items,
            )
        )

    return entries


def _parse_footer(text: str) -> dict:
    """Extract metadata from footer line (fallback for files without frontmatter)."""
    result = {"session_id": "", "host": "", "cwd": ""}

    m = FOOTER_HOST.search(text)
    if m:
        result["session_id"] = m.group(1).strip()
        result["host"] = m.group(3).strip()
        return result

    m = FOOTER_DIR.search(text)
    if m:
        result["session_id"] = m.group(1).strip()
        result["cwd"] = m.group(2).strip()
        return result

    m = FOOTER_SIMPLE.search(text)
    if m:
        result["session_id"] = m.group(1).strip()
        return result

    return result


class VaultStore:
    """Reads session .md files directly from the vault directory.

    Auto-refreshes when files change (mtime-based).
    Writers: SessionEnd hook (Claude Code) and save_session tool (Cursor/VS Code).
    """

    def __init__(self, vault_path: Path | None = None):
        self._vault_path = vault_path or Path(
            os.environ.get("ANAMNESIS_VAULT", str(DEFAULT_VAULT))
        )
        self._cache: dict[str, Session] = {}
        self._mtimes: dict[str, float] = {}
        self._generation: int = 0

    @property
    def generation(self) -> int:
        return self._generation

    def _check_freshness(self):
        """Compare file mtimes against cache, reload if stale."""
        if not self._vault_path.exists():
            return

        current_files: dict[str, float] = {}
        for path in self._vault_path.glob("*.md"):
            current_files[path.name] = path.stat().st_mtime

        if current_files == self._mtimes:
            return

        changed = {
            name
            for name, mtime in current_files.items()
            if name not in self._mtimes or self._mtimes[name] != mtime
        }
        deleted = set(self._mtimes.keys()) - set(current_files.keys())

        if not changed and not deleted:
            return

        # Remove deleted sessions
        if deleted:
            file_to_id = {
                name: sid
                for sid, s in self._cache.items()
                for name in [self._find_filename(sid)]
                if name
            }
            for name in deleted:
                if name in file_to_id:
                    del self._cache[file_to_id[name]]

        # Reload changed/new files
        for name in changed:
            path = self._vault_path / name
            session = self._parse_file(path)
            if session:
                self._cache[session.id] = session

        self._mtimes = current_files
        self._generation += 1
        logger.info(
            f"Vault refreshed: {len(changed)} changed, {len(deleted)} deleted, "
            f"{len(self._cache)} total (gen {self._generation})"
        )

    def _find_filename(self, session_id: str) -> str | None:
        """Find which filename a session came from (best effort)."""
        return None

    def _parse_file(self, path: Path) -> Session | None:
        """Parse a single .md file into a Session."""
        try:
            post = frontmatter.load(path)
        except Exception as e:
            logger.warning(f"Failed to parse {path.name}: {e}")
            return None

        metadata = post.metadata
        body = post.content

        # Get metadata from frontmatter, fall back to footer
        session_id = metadata.get("session_id", "")
        host = metadata.get("host", "")
        cwd = metadata.get("cwd", "")
        tags = metadata.get("tags", [])
        date = metadata.get("date", "")

        if not session_id:
            footer = _parse_footer(body)
            session_id = footer["session_id"]
            host = host or footer["host"]
            cwd = cwd or footer["cwd"]

        if not session_id:
            session_id = f"backfill-{path.stem}"

        if not date:
            m = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
            date = m.group(1) if m else ""

        # Ensure date is a string (frontmatter may parse as datetime.date)
        date = str(date)

        doc_id = hashlib.sha256(session_id.encode()).hexdigest()[:12]

        # Parse title and summary from body
        title = ""
        for line in body.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break

        summary = ""
        parts = body.split("\n---\n")
        if parts:
            first_part = parts[0]
            after_title = first_part.split("\n", 1)
            if len(after_title) > 1:
                summary = after_title[1].strip()
                if "## " in summary:
                    summary = summary[: summary.index("## ")].strip()

        # Parse log entries
        log_text = ""
        if len(parts) >= 3:
            log_text = "\n---\n".join(parts[1:-1])
        elif len(parts) == 2 and "## " in parts[0]:
            idx = parts[0].index("## ")
            log_text = parts[0][idx:]

        entries = _parse_entries(log_text) if log_text else []

        full_text = path.read_text()

        return Session(
            id=doc_id,
            session_id=session_id,
            title=title,
            summary=summary,
            entries=entries,
            content=full_text,
            tags=tags if isinstance(tags, list) else [],
            cwd=cwd,
            host=host,
            date=date,
            created_at=f"{date}T00:00:00" if date else "",
            updated_at=datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            word_count=len(body.split()),
        )

    def get(self, session_id: str) -> Session | None:
        self._check_freshness()
        return self._cache.get(session_id)

    def all(self) -> list[Session]:
        self._check_freshness()
        return list(self._cache.values())

    def filter(
        self,
        date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        host: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Session]:
        self._check_freshness()
        results = sorted(self._cache.values(), key=lambda s: s.updated_at, reverse=True)

        if date:
            results = [s for s in results if s.date == date]
        if tags:
            results = [s for s in results if all(t in s.tags for t in tags)]
        if host:
            results = [s for s in results if s.host == host]

        return results[offset : offset + limit]

    def save_session(
        self,
        title: str,
        summary: str,
        plan: str,
        done: str,
        open_items: str = "",
        cwd: str = "",
        tags: list[str] | None = None,
        session_id: str | None = None,
    ) -> dict:
        """Write or update a session log file in the vault.

        If session_id matches an existing file, appends a new log entry
        and updates the summary. Otherwise creates a new file.

        Returns dict with keys: filename, session_id, created (bool).
        """
        now = datetime.now()
        host = socket.gethostname()
        date = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%Y-%m-%d %H:%M")
        system = f"{platform.system()} {platform.machine()}"

        # Auto-detect session_id if not provided
        if not session_id:
            session_id = detect_claude_session_id()
            if session_id:
                logger.info(f"Auto-detected session_id: {session_id}")

        # Try to find existing file for this session_id
        existing_path = None
        if session_id:
            existing_path = self._find_session_file(session_id)

        if existing_path and existing_path.exists():
            # --- UPDATE existing file ---
            content = existing_path.read_text()

            # Strip frontmatter to get body
            body = content
            fm_block = ""
            if content.startswith("---\n"):
                end = content.find("\n---\n", 4)
                if end != -1:
                    fm_block = content[: end + 5]
                    body = content[end + 5 :].lstrip("\n")

            # Split body into: header_section --- log_entries --- footer
            parts = body.split("\n---\n")

            # Rebuild header with updated summary
            title_line = ""
            for line in body.split("\n"):
                if line.startswith("# "):
                    title_line = line
                    break
            if not title_line:
                title_line = f"# {title}"

            # Extract existing log entries
            existing_entries = ""
            if len(parts) >= 3:
                existing_entries = "\n---\n".join(parts[1:-1]).strip()
            elif len(parts) == 2 and "## " in parts[0]:
                idx = parts[0].index("## ")
                existing_entries = parts[0][idx:].strip()

            # Build new entry
            new_entry_lines = [
                f"## {timestamp}",
                f"- **Plan**: {plan}",
                f"- **Done**: {done}",
            ]
            if open_items:
                new_entry_lines.append(f"- **Open**: {open_items}")
            new_entry = "\n".join(new_entry_lines)

            # Reassemble
            sections = [title_line, ""]
            if summary:
                sections.append(summary)
            sections.extend(["", "---", ""])
            if existing_entries:
                sections.append(existing_entries)
                sections.append("")
            sections.append(new_entry)
            sections.extend(
                [
                    "",
                    "---",
                    f"*Session: `{session_id}` | Updated: {timestamp} | Host: {host} ({system})*",
                    "",
                ]
            )

            updated = fm_block + "\n".join(sections)
            existing_path.write_text(updated)
            logger.info(f"Updated session: {existing_path.name} ({len(updated)} bytes)")
            return {
                "filename": existing_path.name,
                "session_id": session_id,
                "created": False,
            }

        else:
            # --- CREATE new file ---
            if not session_id:
                session_id = str(uuid.uuid4())

            fm = (
                "---\n"
                f'session_id: "{session_id}"\n'
                f'date: "{date}"\n'
                f'host: "{host}"\n'
                f'cwd: "{cwd}"\n'
                f"tags: {tags or []}\n"
                "---\n\n"
            )

            sections = [f"# {title}", ""]
            if summary:
                sections.append(summary)
            sections.extend(["", "---", ""])

            sections.append(f"## {timestamp}")
            sections.append(f"- **Plan**: {plan}")
            sections.append(f"- **Done**: {done}")
            if open_items:
                sections.append(f"- **Open**: {open_items}")

            sections.extend(
                [
                    "",
                    "---",
                    f"*Session: `{session_id}` | Updated: {timestamp} | Host: {host} ({system})*",
                    "",
                ]
            )

            content = fm + "\n".join(sections)

            slug = title.lower()
            for ch in ":/\\?*\"<>|'(),&.!":
                slug = slug.replace(ch, "")
            slug = "-".join(slug.split())[:60]
            filename = f"{now.strftime('%Y-%m-%d_%H%M')}_{slug}.md"

            out_path = self._vault_path / filename
            out_path.write_text(content)
            logger.info(f"Created session: {filename} ({len(content)} bytes)")
            return {"filename": filename, "session_id": session_id, "created": True}

    def _find_session_file(self, session_id: str) -> Path | None:
        """Find the vault file for a given session_id by scanning frontmatter."""
        for path in self._vault_path.glob("*.md"):
            try:
                # Quick check: read first few lines for session_id
                with open(path) as f:
                    head = f.read(500)
                if f'session_id: "{session_id}"' in head:
                    return path
            except Exception:
                continue
        return None

    def get_all_tags(self) -> dict[str, int]:
        self._check_freshness()
        tag_counts: dict[str, int] = {}
        for s in self._cache.values():
            for tag in s.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return dict(sorted(tag_counts.items(), key=lambda x: -x[1]))


_store: VaultStore | None = None


def get_store() -> VaultStore:
    global _store
    if _store is None:
        _store = VaultStore()
    return _store
