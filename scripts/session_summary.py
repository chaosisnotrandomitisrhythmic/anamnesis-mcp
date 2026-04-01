#!/usr/bin/env python3
"""Session summary logger (Anamnesis SessionEnd hook).

Called by the SessionEnd hook wrapper. Reads a Claude Code transcript,
calls the Anthropic API to generate a structured log entry, and
writes/updates a dated markdown file in your vault directory.

The MCP server reads these .md files directly — no JSON intermediary.

Three-context prompt design:
  <full-session>    — entire transcript for full context
  <new-content>     — only the portion since the last summary
  <previous-log>    — existing log entries from the vault file
"""

import json
import logging
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

VAULT_DIR = Path(
    os.environ.get("ANAMNESIS_VAULT", str(Path.home() / "Documents" / "Anamnesis"))
)
DAILY_LOG_DIR = Path(
    os.environ.get("ANAMNESIS_DAILY_DIR", str(VAULT_DIR.parent / "Daily Logs"))
)
INDEX_FILE = VAULT_DIR / ".session-index"
LOG_FILE = Path.home() / ".claude" / "scripts" / "session-summary.log"
OBSIDIAN_CLI = shutil.which("obsidian") or "obsidian"
WIKILINK_PREFIX = os.environ.get("ANAMNESIS_WIKILINK_PREFIX", VAULT_DIR.name + "/")

logging.basicConfig(
    filename=str(LOG_FILE),
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


def parse_transcript(path: str) -> list[dict]:
    """Parse JSONL transcript into a list of {role, text, timestamp} dicts."""
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") not in ("user", "assistant"):
                continue

            message = entry.get("message", {})
            role = message.get("role", entry["type"])
            content = message.get("content", "")
            timestamp = entry.get("timestamp", "")

            # String content
            if isinstance(content, str) and content.strip():
                entries.append({"role": role, "text": content.strip(), "ts": timestamp})
                continue

            # Array content — text blocks only
            if isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        t = block.get("text", "").strip()
                        if t:
                            texts.append(t)
                if texts:
                    entries.append({"role": role, "text": "\n".join(texts), "ts": timestamp})

    return entries


def format_conversation(entries: list[dict]) -> str:
    """Format transcript entries into readable text."""
    lines = []
    for e in entries:
        ts = ""
        if e["ts"]:
            try:
                dt = datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))
                ts = f" ({dt.strftime('%H:%M')})"
            except (ValueError, TypeError):
                pass
        lines.append(f"[{e['role']}{ts}]: {e['text']}")
    return "\n\n".join(lines)


def read_index() -> dict:
    """Read session index: {session_id: {file: str, offset: int}}."""
    index = {}
    if not INDEX_FILE.exists():
        return index
    for line in INDEX_FILE.read_text().splitlines():
        parts = line.strip().split("|")
        if len(parts) == 3:
            index[parts[0]] = {"file": parts[1], "offset": int(parts[2])}
    return index


def write_index(index: dict):
    """Write session index back to disk."""
    lines = []
    for sid, info in index.items():
        lines.append(f"{sid}|{info['file']}|{info['offset']}")
    INDEX_FILE.write_text("\n".join(lines) + "\n")


def get_api_key() -> str:
    """Get Anthropic API key from env or shell rc files (zsh + bash)."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    for rc in (".zshrc", ".bashrc", ".bash_profile", ".profile"):
        rc_path = Path.home() / rc
        if rc_path.exists():
            for line in rc_path.read_text().splitlines():
                m = re.search(r'ANTHROPIC_API_KEY=["\']?([^"\'\s]+)', line)
                if m:
                    return m.group(1)
    return ""


_cli_available: bool | None = None


def obsidian_cli_available() -> bool:
    """Check if Obsidian CLI is enabled (cached).

    Note: `obsidian --version` returns exit code 0 even when CLI is disabled,
    so we probe with `obsidian vault` which actually requires the CLI to be on.
    """
    global _cli_available
    if _cli_available is None:
        try:
            result = subprocess.run(
                [OBSIDIAN_CLI, "vault"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            _cli_available = result.returncode == 0 and "not enabled" not in result.stdout
        except Exception:
            _cli_available = False
        log.info("Obsidian CLI available: %s", _cli_available)
    return _cli_available


def obsidian_create(name: str, content: str) -> bool:
    """Create a new note via Obsidian CLI. Returns True on success."""
    if not obsidian_cli_available():
        return False
    try:
        result = subprocess.run(
            [OBSIDIAN_CLI, "create", f"name={name}", f"content={content}", "silent"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            log.info("Created note via CLI: %s", name)
            return True
        log.warning("CLI create failed: %s", result.stderr)
        return False
    except Exception as e:
        log.warning("CLI create error: %s", e)
        return False


def format_daily_block(
    title: str,
    summary: str,
    done: str,
    open_items: str,
    cwd: str,
    session_filename: str,
    timestamp: str,
) -> str:
    """Format a session summary block for the daily note."""
    time_str = timestamp
    if " " in timestamp:
        time_str = timestamp.split(" ", 1)[1]

    link_name = session_filename.removesuffix(".md")
    link = f"[[{WIKILINK_PREFIX}{link_name}|{title}]]"

    lines = [
        "---",
        "",
        f"### Claude Session ({time_str})",
        "",
        f"**{link}** — `{cwd}`",
        "",
    ]

    if summary:
        lines.append(summary)
        lines.append("")

    if done:
        lines.append(f"**Done:** {done}")
    if open_items:
        lines.append(f"**Open:** {open_items}")

    lines.append("")
    return "\n".join(lines)


def append_to_daily_note(
    title: str,
    summary: str,
    done: str,
    open_items: str,
    cwd: str,
    session_filename: str,
    timestamp: str,
) -> None:
    """Append a session block to today's daily note."""
    block = format_daily_block(
        title=title,
        summary=summary,
        done=done,
        open_items=open_items,
        cwd=cwd,
        session_filename=session_filename,
        timestamp=timestamp,
    )

    if obsidian_cli_available():
        try:
            result = subprocess.run(
                [OBSIDIAN_CLI, "daily:append", f"content={block}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                log.info("Appended to daily note via CLI")
                return
            log.warning("CLI daily:append failed: %s", result.stderr)
        except Exception as e:
            log.warning("CLI daily:append error: %s", e)

    # Fallback: raw file I/O
    now = datetime.now()
    daily_path = DAILY_LOG_DIR / str(now.year) / f"{now.month:02d}" / f"{now.strftime('%Y-%m-%d')}.md"
    daily_path.parent.mkdir(parents=True, exist_ok=True)

    if not daily_path.exists():
        header = f"# {now.strftime('%Y-%m-%d')} - Daily Log\n\n"
        daily_path.write_text(header + block)
        log.info("Created daily note with session block: %s", daily_path)
    else:
        with open(daily_path, "a") as f:
            f.write("\n" + block)
        log.info("Appended to daily note via file I/O: %s", daily_path)


def call_api(system: str, user_content: str) -> str:
    """Call Anthropic Messages API with adaptive thinking."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("No ANTHROPIC_API_KEY found")

    model = os.environ.get("ANAMNESIS_MODEL", "claude-opus-4-6")

    payload = json.dumps({
        "model": model,
        "max_tokens": 16000,
        "thinking": {"type": "adaptive"},
        "system": system,
        "messages": [{"role": "user", "content": user_content}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )

    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())

    # Extract text blocks (skip thinking blocks)
    texts = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            texts.append(block["text"])

    usage = data.get("usage", {})
    log.info(
        "API call: model=%s input=%s output=%s",
        model,
        usage.get("input_tokens", "?"),
        usage.get("output_tokens", "?"),
    )
    return "\n".join(texts)


def build_frontmatter(session_id: str, cwd: str, host: str, date: str) -> str:
    """Build YAML frontmatter block for a session file."""
    return (
        "---\n"
        f'session_id: "{session_id}"\n'
        f'date: "{date}"\n'
        f'host: "{host}"\n'
        f'cwd: "{cwd}"\n'
        "tags: []\n"
        "---\n\n"
    )


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter from text if present."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:].lstrip("\n")
    return text


SYSTEM_PROMPT = """\
You are a session logger for a developer's knowledge base.

You produce two distinct outputs wrapped in XML tags:

<summary>
A concise overview of the entire session so far (2-5 sentences). This is regenerated
each time to reflect the full arc of work. It answers: what was this session about,
what was the outcome, what's the current state? Write it as a paragraph, not bullets.
</summary>

<log_entry>
A single timestamped log entry covering ONLY what happened since the last entry.
Focus on decisions, actions, and outcomes. Use this format:

## YYYY-MM-DD HH:MM
- **Plan**: What the user set out to do in this segment
- **Done**: What was accomplished
- **Open**: Unfinished items or next steps (omit if nothing is open)
</log_entry>

You receive three context sections (long context first, instructions last per best practices):
- <full-session>: Complete conversation transcript — use this to write the summary
- <new-content>: Only messages since the last log entry — use this to write the log entry
- <previous-log>: Existing log entries from prior exits — avoid repeating their content

Additional rules:
- Each bullet: 1-2 lines max. Be specific about what changed.
- The summary reflects the whole session. The log entry covers only the new segment.
- On first entry, also include a descriptive title line: # Title
- Output ONLY the two XML-tagged sections, nothing else."""


def main():
    hook_input = json.loads(sys.stdin.read())
    transcript_path = hook_input.get("transcript_path", "")
    session_id = hook_input.get("session_id", "")
    cwd = hook_input.get("cwd", "")

    if not transcript_path or not session_id or not os.path.isfile(transcript_path):
        log.error("Missing transcript_path (%s) or session_id (%s)", transcript_path, session_id)
        return

    log.info("Processing session %s", session_id)

    # Ensure vault directory exists
    VAULT_DIR.mkdir(parents=True, exist_ok=True)

    # Parse transcript
    entries = parse_transcript(transcript_path)
    if len(entries) < 2:
        log.info("Session %s too short (%d entries)", session_id, len(entries))
        return

    # Check index for previous state
    index = read_index()
    prev = index.get(session_id)
    previous_log = ""
    existing_file = None
    offset = 0

    if prev:
        existing_file = VAULT_DIR / prev["file"]
        offset = prev["offset"]
        if existing_file.exists():
            content = existing_file.read_text()
            # Strip frontmatter before parsing log entries
            body = strip_frontmatter(content)
            log_entries = re.findall(
                r"(## \d{4}-\d{2}-\d{2} \d{2}:\d{2}.*?)(?=\n## |\n---)",
                body, re.DOTALL,
            )
            previous_log = "\n\n".join(e.strip() for e in log_entries)
            log.info("Found existing log with %d entries, offset %d", len(log_entries), offset)

    # Build the three contexts
    full_text = format_conversation(entries)
    new_entries = entries[offset:] if offset > 0 else entries
    new_text = format_conversation(new_entries)

    # Truncate if needed (keep under ~150K chars for context)
    if len(full_text) > 150000:
        full_text = full_text[:150000] + "\n\n[...truncated...]"
    if len(new_text) > 80000:
        new_text = new_text[:80000] + "\n\n[...truncated...]"

    # Build user prompt
    user_content = f"""<full-session>
{full_text}
</full-session>

<new-content>
{new_text}
</new-content>

<previous-log>
{previous_log if previous_log else "(First entry — no previous log)"}
</previous-log>

<metadata>
session_id: {session_id}
cwd: {cwd}
host: {socket.gethostname()}
system: {platform.system()} {platform.machine()}
current_time: {datetime.now().strftime("%Y-%m-%d %H:%M")}
</metadata>

Generate the log entry."""

    # Call API
    result = call_api(SYSTEM_PROMPT, user_content)
    if not result.strip():
        log.error("Empty result from API")
        return

    # Parse the two XML sections from the response
    summary_match = re.search(r"<summary>(.*?)</summary>", result, re.DOTALL)
    entry_match = re.search(r"<log_entry>(.*?)</log_entry>", result, re.DOTALL)

    summary = summary_match.group(1).strip() if summary_match else ""
    new_entry = entry_match.group(1).strip() if entry_match else ""

    if not summary and not new_entry:
        # Fallback: treat entire result as a log entry
        log.warning("Could not parse XML sections, using raw result")
        new_entry = result.strip()

    # Metadata for frontmatter
    host = socket.gethostname()
    system = f"{platform.system()} {platform.machine()}"
    today = datetime.now().strftime("%Y-%m-%d")

    # Assemble the file
    if existing_file and existing_file.exists():
        content = existing_file.read_text()
        body = strip_frontmatter(content)

        # File structure: title + summary + --- + log entries + --- + footer
        parts = body.split("\n---\n")

        # Find the title line (# ...)
        title_line = ""
        for line in body.split("\n"):
            if line.startswith("# "):
                title_line = line
                break

        # Extract existing log entries
        existing_entries = ""
        if len(parts) >= 3:
            existing_entries = "\n---\n".join(parts[1:-1]).strip()
        elif len(parts) == 2:
            if "## " in parts[0]:
                idx = parts[0].index("## ")
                existing_entries = parts[0][idx:].strip()

        out_path = existing_file
    else:
        # New file — extract title from the log entry
        title_line = ""
        for line in new_entry.split("\n"):
            if line.startswith("# "):
                title_line = line
                new_entry = new_entry.replace(line + "\n", "", 1).strip()
                break

        if not title_line:
            title_line = "# Claude Code Session"

        existing_entries = ""

        # Generate filename from title
        now = datetime.now()
        slug = title_line.lstrip("# ").strip().lower()
        for ch in ":/\\?*\"<>|'(),&.!":
            slug = slug.replace(ch, "")
        slug = "-".join(slug.split())[:60]
        filename = f"{now.strftime('%Y-%m-%d_%H%M')}_{slug}.md"
        out_path = VAULT_DIR / filename

    # Build the file: frontmatter -> title -> summary -> --- -> log entries -> --- -> footer
    fm = build_frontmatter(session_id, cwd, host, today)

    sections = [title_line, ""]
    if summary:
        sections.append(summary)
    sections.append("")
    sections.append("---")
    sections.append("")

    # Existing entries + new entry
    if existing_entries:
        sections.append(existing_entries)
        sections.append("")
    if new_entry:
        sections.append(new_entry)

    # Footer
    sections.append("")
    sections.append("---")
    sections.append(f"*Session: `{session_id}` | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Host: {host} ({system})*")
    sections.append("")

    updated = fm + "\n".join(sections)

    # Write session file — CLI create for new files, raw I/O for updates and fallback
    is_new = not (existing_file and existing_file.exists())
    if is_new:
        note_name = f"{VAULT_DIR.name}/{out_path.stem}"
        if not obsidian_create(note_name, updated):
            out_path.write_text(updated)
    else:
        out_path.write_text(updated)

    # Update index
    index[session_id] = {"file": out_path.name, "offset": len(entries)}
    write_index(index)

    log.info("Wrote %s (%d bytes, %d transcript entries)", out_path.name, len(updated), len(entries))

    # Append to daily note
    try:
        # Extract done/open from the new entry
        done_text = ""
        open_text = ""
        for line in new_entry.split("\n"):
            m = re.match(r"^- \*\*Done\*\*:\s*(.+)", line)
            if m:
                done_text = m.group(1).strip()
            m = re.match(r"^- \*\*Open\*\*:\s*(.+)", line)
            if m:
                open_text = m.group(1).strip()

        append_to_daily_note(
            title=title_line.lstrip("# ").strip(),
            summary=summary,
            done=done_text,
            open_items=open_text,
            cwd=cwd,
            session_filename=out_path.name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
    except Exception:
        log.exception("Daily note append failed")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Unhandled error")
