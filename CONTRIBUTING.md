# Contributing to Anamnesis MCP

Thank you for your interest in contributing.

## Reporting bugs

Open a [GitHub issue](https://github.com/chaosisnotrandomitisrhythmic/anamnesis-mcp/issues/new?template=bug_report.md) with:

- Steps to reproduce
- Expected vs actual behavior
- Python version, OS, Claude Code version

## Requesting features

Open a [feature request](https://github.com/chaosisnotrandomitisrhythmic/anamnesis-mcp/issues/new?template=feature_request.md) describing the use case and why it matters.

## Development setup

```bash
git clone https://github.com/chaosisnotrandomitisrhythmic/anamnesis-mcp.git
cd anamnesis-mcp
uv sync --extra dev
```

Run tests and linter:

```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/
```

## Code style

- Formatted with [ruff](https://docs.astral.sh/ruff/)
- No additional type-checking (Pydantic models handle runtime validation)

## Pull request process

1. Fork the repo and create a branch from `master`
2. Make your changes
3. Add or update tests for new behavior
4. Ensure `uv run pytest tests/` and `uv run ruff check src/ tests/` pass
5. Open a PR with a clear description of what and why

## Commit messages

Use [conventional commits](https://www.conventionalcommits.org/):

```
feat: add date range filter to search_sessions
fix: handle missing frontmatter in legacy files
docs: add uninstallation section to README
```

## Questions?

Open a [discussion](https://github.com/chaosisnotrandomitisrhythmic/anamnesis-mcp/issues) or file an issue.
