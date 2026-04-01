"""Centralized path configuration for Anamnesis.

All file paths, directories, and environment-driven overrides live here.
Scripts and modules import from this module instead of defining their own constants.
"""

import os
import shutil
from pathlib import Path

# --- Vault paths ---

VAULT_ROOT = Path(
    os.environ.get("ANAMNESIS_VAULT_ROOT", str(Path.home() / "Documents" / "Anamnesis"))
)

VAULT_DIR = Path(
    os.environ.get("ANAMNESIS_VAULT", str(VAULT_ROOT))
)

DAILY_LOG_DIR = Path(
    os.environ.get("ANAMNESIS_DAILY_DIR", str(VAULT_ROOT / ".." / "Daily Logs"))
)

# --- Index and log files ---

INDEX_FILE = VAULT_DIR / ".session-index"

LOG_DIR = Path.home() / ".claude" / "scripts"

SESSION_SUMMARY_LOG = LOG_DIR / "session-summary.log"
DAILY_SUMMARY_LOG = LOG_DIR / "daily-summary.log"

# --- Obsidian CLI ---

OBSIDIAN_CLI = shutil.which("obsidian") or os.environ.get("OBSIDIAN_CLI", "obsidian")

# --- API ---

MODEL = os.environ.get("ANAMNESIS_MODEL", "claude-opus-4-6")

# --- Cron schedule ---

DAILY_SUMMARY_HOUR = int(os.environ.get("ANAMNESIS_DAILY_HOUR", "20"))
DAILY_SUMMARY_MINUTE = int(os.environ.get("ANAMNESIS_DAILY_MINUTE", "0"))
