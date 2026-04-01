"""Daily note integration via Obsidian CLI.

Appends session summary blocks to a daily note after each session log write.
Falls back to raw file I/O when the Obsidian CLI is unavailable.

Configuration via environment variables:
  ANAMNESIS_DAILY_DIR  — directory for daily notes (default: ANAMNESIS_VAULT/../Scanner Daybook/Daily Logs)
  OBSIDIAN_CLI         — path to the obsidian binary (default: obsidian)
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from . import get_logger

logger = get_logger(__name__)

_cli_available: bool | None = None


def _get_obsidian_cli() -> str:
    """Get path to Obsidian CLI binary."""
    return os.environ.get("OBSIDIAN_CLI", shutil.which("obsidian") or "obsidian")


def _get_daily_dir(vault_path: Path) -> Path:
    """Get daily notes directory, configurable via ANAMNESIS_DAILY_DIR."""
    env = os.environ.get("ANAMNESIS_DAILY_DIR")
    if env:
        return Path(env)
    # Default: sibling of session dir, under Scanner Daybook/Daily Logs
    return vault_path.parent / "Scanner Daybook" / "Daily Logs"


def obsidian_cli_available() -> bool:
    """Check if Obsidian CLI is enabled (cached).

    Note: `obsidian --version` returns exit code 0 even when CLI is disabled,
    so we probe with `obsidian vault` which actually requires the CLI to be on.
    """
    global _cli_available
    if _cli_available is None:
        cli = _get_obsidian_cli()
        try:
            result = subprocess.run(
                [cli, "vault"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # When disabled, stdout contains "Command line interface is not enabled"
            _cli_available = result.returncode == 0 and "not enabled" not in result.stdout
        except Exception:
            _cli_available = False
        logger.info(f"Obsidian CLI available: {_cli_available}")
    return _cli_available


def obsidian_create(name: str, content: str) -> bool:
    """Create a new note via Obsidian CLI. Returns True on success."""
    if not obsidian_cli_available():
        return False
    cli = _get_obsidian_cli()
    try:
        result = subprocess.run(
            [cli, "create", f"name={name}", f"content={content}", "silent"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info(f"Created note via CLI: {name}")
            return True
        logger.warning(f"CLI create failed: {result.stderr}")
        return False
    except Exception as e:
        logger.warning(f"CLI create error: {e}")
        return False


def format_daily_block(
    title: str,
    summary: str,
    done: str,
    open_items: str,
    cwd: str,
    session_filename: str,
    timestamp: str,
    session_folder: str = "Claude Sessions",
) -> str:
    """Format a session summary block for the daily note."""
    # Extract time from timestamp (HH:MM)
    time_str = timestamp
    if " " in timestamp:
        time_str = timestamp.split(" ", 1)[1]

    # Build wikilink: strip .md extension for Obsidian link
    link_name = session_filename.removesuffix(".md")
    link = f"[[{session_folder}/{link_name}|{title}]]"

    lines = [
        "---",
        "",
        f"### 🤖 Claude Session ({time_str})",
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
    timestamp: str | None = None,
    vault_path: Path | None = None,
    session_folder: str = "Claude Sessions",
) -> None:
    """Append a session block to today's daily note.

    Tries Obsidian CLI first, falls back to raw file I/O.
    """
    now = datetime.now()
    if not timestamp:
        timestamp = now.strftime("%Y-%m-%d %H:%M")

    block = format_daily_block(
        title=title,
        summary=summary,
        done=done,
        open_items=open_items,
        cwd=cwd,
        session_filename=session_filename,
        timestamp=timestamp,
        session_folder=session_folder,
    )

    # Try Obsidian CLI
    if obsidian_cli_available():
        cli = _get_obsidian_cli()
        try:
            result = subprocess.run(
                [cli, "daily:append", f"content={block}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info("Appended to daily note via CLI")
                return
            logger.warning(f"CLI daily:append failed: {result.stderr}")
        except Exception as e:
            logger.warning(f"CLI daily:append error: {e}")

    # Fallback: raw file I/O
    if vault_path is None:
        from .store import DEFAULT_VAULT
        vault_path = Path(os.environ.get("ANAMNESIS_VAULT", str(DEFAULT_VAULT)))

    daily_dir = _get_daily_dir(vault_path)
    daily_path = daily_dir / str(now.year) / f"{now.month:02d}" / f"{now.strftime('%Y-%m-%d')}.md"
    daily_path.parent.mkdir(parents=True, exist_ok=True)

    if not daily_path.exists():
        header = f"# {now.strftime('%Y-%m-%d')} - Daily Scanner Log\n\n"
        daily_path.write_text(header + block)
        logger.info(f"Created daily note with session block: {daily_path}")
    else:
        with open(daily_path, "a") as f:
            f.write("\n" + block)
        logger.info(f"Appended to daily note via file I/O: {daily_path}")
