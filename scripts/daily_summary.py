#!/usr/bin/env python3
"""Daily summary generator — the third compression layer.

Runs via cron at 20:00. Reads all session files from today (or a given date),
calls Opus to synthesize a single cohesive daily summary, and writes it to a
daily note file.

Compression hierarchy:
  Raw transcript -> Session file (Opus summary + Plan/Done/Open)
    -> Daily summary (summary of summaries — residual symbols)

Each layer is a lossy compression of the layer below. The daily summary
doesn't just shorten — it surfaces the *shape* of the day. Connections between
sessions that weren't obvious in isolation. The structural echo after the
details wash out.

Usage:
  python daily_summary.py                  # summarize today
  python daily_summary.py 2026-03-31       # summarize a specific date
"""

import logging
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Import shared paths and API from the anamnesis package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from anamnesis.paths import VAULT_DIR, DAILY_LOG_DIR, DAILY_SUMMARY_LOG
from anamnesis.api import call_api

logging.basicConfig(
    filename=str(DAILY_SUMMARY_LOG),
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter from text if present."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:].lstrip("\n")
    return text


def collect_sessions(target_date: str) -> list[dict]:
    """Collect all session files updated on the target date.

    Returns list of {title, summary, entries, filename, cwd, host} dicts,
    sorted by file modification time (chronological).
    """
    sessions = []

    if not VAULT_DIR.exists():
        return sessions

    for path in sorted(VAULT_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime):
        try:
            content = path.read_text()
        except Exception:
            continue

        # Check if this session was active on the target date
        # Look at frontmatter date OR filename date prefix
        frontmatter_date = ""
        if content.startswith("---\n"):
            end = content.find("\n---\n", 4)
            if end != -1:
                fm = content[4:end]
                m = re.search(r'date:\s*"?(\d{4}-\d{2}-\d{2})"?', fm)
                if m:
                    frontmatter_date = m.group(1)

        # Also check filename date prefix (YYYY-MM-DD_HHMM_...)
        filename_date = path.name[:10] if len(path.name) >= 10 else ""

        # Check if any log entry timestamps match the target date
        body = strip_frontmatter(content)
        entry_dates = re.findall(r"## (\d{4}-\d{2}-\d{2}) \d{2}:\d{2}", body)

        # Session is relevant if it was created on target date,
        # or has log entries from that date
        is_relevant = (
            frontmatter_date == target_date
            or filename_date == target_date
            or target_date in entry_dates
        )

        if not is_relevant:
            continue

        # Extract title
        title = "Untitled Session"
        for line in body.split("\n"):
            if line.startswith("# "):
                title = line.lstrip("# ").strip()
                break

        # Extract summary (paragraph between title and first ---)
        summary = ""
        parts = body.split("\n---\n")
        if parts:
            first_part = parts[0].strip()
            lines = first_part.split("\n")
            # Skip the title line, collect paragraph lines
            para_lines = []
            for line in lines[1:]:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    para_lines.append(stripped)
            summary = " ".join(para_lines)

        # Extract log entries from the target date only
        all_entries = re.findall(
            r"(## \d{4}-\d{2}-\d{2} \d{2}:\d{2}.*?)(?=\n## |\n---)",
            body, re.DOTALL,
        )
        day_entries = [
            e.strip() for e in all_entries
            if e.strip().startswith(f"## {target_date}")
        ]

        # Extract metadata from frontmatter
        cwd = ""
        host = ""
        if content.startswith("---\n"):
            end = content.find("\n---\n", 4)
            if end != -1:
                fm = content[4:end]
                m = re.search(r'cwd:\s*"?(.+?)"?\s*$', fm, re.MULTILINE)
                if m:
                    cwd = m.group(1)
                m = re.search(r'host:\s*"?(.+?)"?\s*$', fm, re.MULTILINE)
                if m:
                    host = m.group(1)

        sessions.append({
            "title": title,
            "summary": summary,
            "entries": day_entries,
            "filename": path.name,
            "cwd": cwd,
            "host": host,
        })

    return sessions


def load_previous_summary(target_date: str) -> str:
    """Load yesterday's daily summary for continuity context."""
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    yesterday = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    yd = datetime.strptime(yesterday, "%Y-%m-%d")
    prev_path = DAILY_LOG_DIR / str(yd.year) / f"{yd.month:02d}" / f"{yesterday}.md"

    if not prev_path.exists():
        return ""

    content = prev_path.read_text()
    marker = "<!-- daily-summary -->"
    if marker in content:
        return content[content.index(marker) + len(marker):].strip()
    return content.strip()


# --- The system prompt: the soul of the compression layer ---

SYSTEM_PROMPT = """\
You are the third compression layer in a self-referential memory system.

The architecture:
1. Raw transcripts — full conversations between a human and Claude Code
2. Session files — Opus summaries with Plan/Done/Open entries (one per session)
3. **You** — the daily summary. A summary of summaries.

Each layer is a lossy compression of the layer below. You are not writing a
shorter version of the sessions. You are producing what Hofstadter calls
"residual symbols" — the stable attractors that emerge when information passes
through recursive compression. The specific details wash out. What remains is
the *shape*.

A session summary captures WHAT happened. Your job is to capture what the day
MEANT — the emergent pattern that only becomes visible when you see all
sessions together. Connections the user didn't notice in the moment. Threads
that ran through seemingly unrelated work. The arc of the day.

You receive all session summaries and log entries from a single day. You may
also receive yesterday's summary for continuity. Produce a daily note that:

1. Opens with a **cohesive narrative paragraph** (3-6 sentences) — the day's
   shape. Not a list of sessions. A synthesis. What was this day *about*,
   viewed from above? What themes recurred? What tensions were present?
   Where did energy flow?

2. Follows with **Threads** — 2-4 thematic threads that ran through the day.
   These are the residual symbols: the patterns that survive compression.
   Name each thread and explain how it manifested across sessions.
   Use [[wikilinks]] to link back to session files.

3. Ends with **What Carries Forward** — the Zeigarnik residue. Unfinished
   items that carry forward. Not a dump of every Open item from every
   session — only the ones that matter tomorrow. The ones that will nag.

4. Close with a single **Closing read** line — an energy signature for the
   day in ≤10 words. Not a summary. A vibe. The emotional residue.

Format:

<daily_summary>
[Narrative paragraph — the day's shape]

## Threads

### [Thread Name]
[How this theme appeared across sessions, with [[wikilinks]]]

### [Thread Name]
[...]

## What Carries Forward
- [Consolidated open items that carry real weight into tomorrow]

---
*Closing read: [energy signature in ≤10 words]*
</daily_summary>

Rules:
- Write in present tense when describing the day's character
- Be specific about connections — don't just say "several sessions touched on X"
- [[Wikilinks]] use the format: [[Claude Sessions/filename-without-extension|Display Text]]
- The narrative paragraph is the most important part. It's what the user will
  read when they look back at this day in six months.
- If yesterday's summary is provided, note any threads that continue or resolve.
- This is lossy compression by design. Let details die. Keep the shape.
- Output ONLY the <daily_summary> tags, nothing else."""


def build_user_prompt(target_date: str, sessions: list[dict], previous_summary: str = "") -> str:
    """Build the user prompt with all session data."""
    parts = [f"<date>{target_date}</date>\n"]
    parts.append(f"<session_count>{len(sessions)}</session_count>\n")

    if previous_summary:
        parts.append(f"<previous_summary>\n{previous_summary}\n</previous_summary>\n")

    for i, s in enumerate(sessions, 1):
        link = s["filename"].removesuffix(".md")
        parts.append(f"<session index=\"{i}\" title=\"{s['title']}\" "
                      f"file=\"{link}\" cwd=\"{s['cwd']}\">")
        if s["summary"]:
            parts.append(f"<summary>{s['summary']}</summary>")
        for entry in s["entries"]:
            parts.append(f"<entry>{entry}</entry>")
        parts.append("</session>\n")

    parts.append("Generate the daily summary.")
    return "\n".join(parts)


def write_daily_note(target_date: str, content: str) -> Path:
    """Write the daily summary to the Scanner Daybook."""
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    daily_path = DAILY_LOG_DIR / str(dt.year) / f"{dt.month:02d}" / f"{target_date}.md"
    daily_path.parent.mkdir(parents=True, exist_ok=True)

    header = f"# {target_date} — Daily Summary\n\n"
    marker = "<!-- daily-summary -->\n\n"
    daily_path.write_text(header + marker + content + "\n")

    return daily_path


def main():
    # Accept optional date argument, default to today
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        # Validate format
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            print(f"Invalid date format: '{target_date}'. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")

    log.info("Generating daily summary for %s", target_date)

    # Collect sessions
    sessions = collect_sessions(target_date)
    if not sessions:
        log.info("No sessions found for %s", target_date)
        return

    log.info("Found %d sessions for %s", len(sessions), target_date)

    # Load previous day's summary for continuity
    previous_summary = load_previous_summary(target_date)
    if previous_summary:
        log.info("Loaded previous summary (%d bytes)", len(previous_summary))

    # Build prompt and call API
    user_content = build_user_prompt(target_date, sessions, previous_summary)
    result = call_api(SYSTEM_PROMPT, user_content)

    if not result.strip():
        log.error("Empty result from API")
        return

    # Parse the daily summary from XML tags
    match = re.search(r"<daily_summary>(.*?)</daily_summary>", result, re.DOTALL)
    summary = match.group(1).strip() if match else result.strip()

    # Write to daily note
    out_path = write_daily_note(target_date, summary)
    log.info("Wrote daily summary to %s (%d bytes)", out_path, len(summary))
    print(f"Daily summary written to {out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Unhandled error")
        raise
