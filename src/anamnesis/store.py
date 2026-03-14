import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import frontmatter

from .models import Session, LogEntry
from . import get_logger

logger = get_logger(__name__)

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
    Read-only — the SessionEnd hook is the only writer.
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
