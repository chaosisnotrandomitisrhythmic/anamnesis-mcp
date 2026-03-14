# Anamnesis MCP

Un-forgetting for AI — persistent session memory for Claude Code.

Anamnesis automatically logs your Claude Code sessions as structured markdown files and serves them back via an [MCP](https://modelcontextprotocol.io/) server. New sessions can search and cross-reference past ones, giving Claude continuity across conversations.

Named after the Platonic concept of *anamnesis* (un-forgetting) — knowledge isn't created, it's remembered. See [`research/strange-loops.md`](research/strange-loops.md) for the philosophy behind the project.

## How It Works

```
Session ends → SessionEnd hook fires → Anthropic API summarizes the transcript
→ Writes structured markdown (Plan/Done/Open) to a vault directory
→ MCP server indexes and serves those files to future sessions
```

Each session file has YAML frontmatter (session_id, date, host, cwd, tags) and timestamped log entries with **Plan**, **Done**, and **Open** fields. The MCP server reads them directly — no database, no JSON intermediary.

## Tools

**Core:**
- `search_sessions` — BM25 full-text search over session logs
- `get_session` — retrieve full session by ID
- `list_sessions` — browse/paginate with date/tag/host filters
- `search_entries` — cross-session search for Plan/Done/Open items

**Section:**
- `get_section` — extract a specific section from a session by heading
- `list_sections` — list all headings in a session
- `search_sections` — find a heading across all sessions

**Analysis:**
- `analyze_corpus` — corpus-wide statistics (session count, word count, tag distribution, open items)
- `run_analysis` — execute Python code against session data (local/stdio transport only)

## Installation

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/chaosisnotrandomitisrhythmic/anamnesis-mcp.git
cd anamnesis-mcp
uv sync
```

## Configuration

### 1. MCP Server

Add to your `~/.claude.json`:

```json
{
  "mcpServers": {
    "anamnesis": {
      "command": "uv",
      "args": ["--directory", "/path/to/anamnesis-mcp", "run", "anamnesis"]
    }
  }
}
```

### 2. SessionEnd Hook

Add to your `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash /path/to/anamnesis-mcp/scripts/session-summary.sh",
            "timeout": 10000
          }
        ]
      }
    ]
  }
}
```

### 3. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANAMNESIS_VAULT` | `~/Documents/Anamnesis` | Directory where session markdown files are stored |
| `ANTHROPIC_API_KEY` | — | Required for the SessionEnd hook (API call to summarize transcripts) |
| `ANAMNESIS_MODEL` | `claude-sonnet-4-6` | Model used for session summaries |

The vault directory is created automatically on first session end.

### 4. Optional: Claude Code Skill

Copy `examples/skill/SKILL.md` to `~/.claude/skills/anamnesis/SKILL.md` to add a `/anamnesis` slash command that guides Claude through searching and cross-referencing sessions.

## Vault Format

Session files are plain markdown with YAML frontmatter:

```markdown
---
session_id: "abc123-def456-..."
date: "2026-03-14"
host: "myhost"
cwd: "/home/user/project"
tags: []
---

# Session Title

Summary paragraph describing the full arc of work.

---

## 2026-03-14 14:30
- **Plan**: What the user set out to do
- **Done**: What was accomplished
- **Open**: Unfinished items or next steps

---
*Session: `abc123-def456-...` | Updated: 2026-03-14 15:00 | Host: myhost (Linux x86_64)*
```

This format works with any markdown viewer. If you use [Obsidian](https://obsidian.md/), point `ANAMNESIS_VAULT` at a folder inside your vault for full-text search, graph view, and sync.

## Architecture

- **`src/anamnesis/`** — MCP server (FastMCP + BM25 search index)
  - `server.py` — tool definitions
  - `store.py` — vault reader with mtime-based auto-refresh
  - `index.py` — in-memory BM25 search (rebuilds when files change)
  - `models.py` — Pydantic models (Session, LogEntry, SearchResult)
  - `config.py` — tool descriptions and system instructions
  - `toolslm_utils.py` — XML formatting using [toolslm](https://github.com/AnswerDotAI/toolslm)
- **`scripts/`** — SessionEnd hook (shell wrapper + Python summarizer)
- **`research/`** — philosophical background (strange loops, self-reference)

## Dependencies

- [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
- [bm25s](https://github.com/xhluca/bm25s) — fast BM25 search
- [toolslm](https://github.com/AnswerDotAI/toolslm) — XML formatting for LLM tool responses
- [python-frontmatter](https://github.com/eyeseast/python-frontmatter) — YAML frontmatter parsing
- [PyStemmer](https://github.com/snowballstem/pystemmer) — Snowball stemming for search

## License

MIT
