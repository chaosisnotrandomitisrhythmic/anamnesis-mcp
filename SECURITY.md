# Security

## Network access

Anamnesis makes **no network calls** during normal operation. The MCP server reads and writes local markdown files only.

The one exception is the optional **SessionEnd hook** (`scripts/session-summary.sh`), which calls the Anthropic API to generate session summaries. This requires `ANTHROPIC_API_KEY` set as an environment variable — the key is never stored in files or logged.

## File system access

The server reads and writes markdown files **only within the configured vault directory** (`ANAMNESIS_VAULT`, default `~/Documents/Anamnesis`). It does not access files outside this path.

## Data sensitivity

Session logs may contain PII, code snippets, or project details from your Claude Code conversations. Recommendations:

- Add your vault directory to `.gitignore` if it lives inside a repo
- Use Obsidian Sync or another encrypted sync service if syncing across devices
- The vault is plain markdown — you can audit, edit, or delete any file at any time

## No telemetry

Anamnesis collects no analytics, telemetry, or usage data. There is no phone-home behavior.

## `run_analysis` tool

The `run_analysis` tool executes arbitrary Python code against session data. It is **only available in local/stdio transport mode** (not over HTTP). It uses `toolslm.funccall.python` with a timeout. Use with the same caution as any code execution tool.

## Reporting vulnerabilities

If you find a security issue, please email andreas@chaosisnotrandomitisrhythmic.xyz rather than opening a public issue. I'll respond within 48 hours.
