#!/usr/bin/env bash
set -euo pipefail

# Thin wrapper for SessionEnd hook.
# Reads hook input from stdin, backgrounds the Python script.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="${HOME}/.claude/scripts/session-summary.log"
INPUT=$(cat)

mkdir -p "$(dirname "$LOG_FILE")"
(echo "$INPUT" | python3 "$SCRIPT_DIR/session_summary.py") >> "$LOG_FILE" 2>&1 &
disown

exit 0
