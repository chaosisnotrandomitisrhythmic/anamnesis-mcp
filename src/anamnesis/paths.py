"""Centralized path configuration for Anamnesis."""

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AnamnesisPaths:
    """All file paths and settings, configurable via env vars."""

    vault_root: Path = field(default_factory=lambda: Path.home() / "Documents" / "Anamnesis")
    vault_dir: Path = field(default=None)
    daily_log_dir: Path = field(default=None)
    model: str = "claude-opus-4-6"
    daily_summary_hour: int = 20
    daily_summary_minute: int = 3
    obsidian_cli: str = field(default_factory=lambda: shutil.which("obsidian") or "obsidian")

    def __post_init__(self):
        if self.vault_dir is None:
            object.__setattr__(self, "vault_dir", self.vault_root)
        if self.daily_log_dir is None:
            object.__setattr__(self, "daily_log_dir", self.vault_root.parent / "Daily Logs")

    @classmethod
    def from_env(cls) -> "AnamnesisPaths":
        """Create config from environment variables."""
        vault_root = Path(os.environ.get("ANAMNESIS_VAULT_ROOT", str(Path.home() / "Documents" / "Anamnesis")))

        vault_dir = None
        if "ANAMNESIS_VAULT" in os.environ:
            vault_dir = Path(os.environ["ANAMNESIS_VAULT"])

        daily_log_dir = None
        if "ANAMNESIS_DAILY_DIR" in os.environ:
            daily_log_dir = Path(os.environ["ANAMNESIS_DAILY_DIR"])

        model = os.environ.get("ANAMNESIS_MODEL", "claude-opus-4-6")

        try:
            hour = int(os.environ.get("ANAMNESIS_DAILY_HOUR", "20"))
        except ValueError:
            hour = 20
        try:
            minute = int(os.environ.get("ANAMNESIS_DAILY_MINUTE", "3"))
        except ValueError:
            minute = 3

        return cls(
            vault_root=vault_root,
            vault_dir=vault_dir,
            daily_log_dir=daily_log_dir,
            model=model,
            daily_summary_hour=hour,
            daily_summary_minute=minute,
        )

    @property
    def index_file(self) -> Path:
        return self.vault_dir / ".session-index"

    @property
    def log_dir(self) -> Path:
        return Path.home() / ".claude" / "scripts"

    @property
    def session_summary_log(self) -> Path:
        return self.log_dir / "session-summary.log"

    @property
    def daily_summary_log(self) -> Path:
        return self.log_dir / "daily-summary.log"


config = AnamnesisPaths.from_env()

# Backward-compatible constants
VAULT_ROOT = config.vault_root
VAULT_DIR = config.vault_dir
DAILY_LOG_DIR = config.daily_log_dir
INDEX_FILE = config.index_file
SESSION_SUMMARY_LOG = config.session_summary_log
DAILY_SUMMARY_LOG = config.daily_summary_log
MODEL = config.model
OBSIDIAN_CLI = config.obsidian_cli
