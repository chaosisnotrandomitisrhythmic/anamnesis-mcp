# Anamnesis MCP

> *"All inquiry and all learning is but recollection."* — Plato, *Meno* 81d

Persistent session memory for Claude Code.

Claude Code already has persistence primitives — `CLAUDE.md` for project context, memory files for user preferences, skills for reusable workflows. What it doesn't have is *episodic* memory: what happened across sessions, what was tried, what worked, what's still open. The gap between episodic recall (*what happened*) and procedural knowledge (*what to do*) resets to zero every time a context window closes.

Anamnesis bridges that gap. It logs each session as structured markdown — **Plan**, **Done**, **Open** — and serves it back via an [MCP](https://modelcontextprotocol.io/) server. Future sessions can search and cross-reference the past.

## Quick Start

Requires Python 3.13+, [uv](https://docs.astral.sh/uv/), and an `ANTHROPIC_API_KEY`.

```bash
git clone https://github.com/chaosisnotrandomitisrhythmic/anamnesis-mcp.git
cd anamnesis-mcp && uv sync
```

Add the MCP server to `~/.claude.json`:
```json
{ "mcpServers": { "anamnesis": {
    "command": "uv",
    "args": ["--directory", "/path/to/anamnesis-mcp", "run", "anamnesis"]
}}}
```

Add the SessionEnd hook to `~/.claude/settings.json`:
```json
{ "hooks": { "SessionEnd": [{ "matcher": "", "hooks": [{
    "type": "command",
    "command": "bash /path/to/anamnesis-mcp/scripts/session-summary.sh",
    "timeout": 10000
}]}]}}
```

| Variable | Default | Description |
|----------|---------|-------------|
| `ANAMNESIS_VAULT` | `~/Documents/Anamnesis` | Directory where session files are stored |
| `ANTHROPIC_API_KEY` | — | Required by the hook to summarize transcripts |
| `ANAMNESIS_MODEL` | `claude-sonnet-4-6` | Model used for summaries |

Optionally, copy `examples/skill/SKILL.md` to `~/.claude/skills/anamnesis/SKILL.md` for a `/anamnesis` slash command that teaches Claude how to search and cross-reference sessions.

## Tools

- `search_sessions` — BM25 full-text search over session logs
- `get_session` — retrieve full session by ID
- `list_sessions` — browse/paginate with date/tag/host filters
- `search_entries` — cross-session search for Plan/Done/Open items
- `get_section` / `list_sections` / `search_sections` — heading-level extraction
- `analyze_corpus` — corpus-wide statistics and open item counts
- `run_analysis` — execute Python against session data (local/stdio only)

## Vault Format

Plain markdown with YAML frontmatter. No database — just files in a directory.

```markdown
---
session_id: "abc123-..."
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
```

Works with any markdown viewer. If you use [Obsidian](https://obsidian.md/), point `ANAMNESIS_VAULT` at a folder inside your vault for graph view and sync.

---

## Why "Anamnesis"

**Anamnesis** (ἀνάμνησις) — Plato's word for recollection, literally *un-forgetting*. His claim was that knowledge is not acquired but recovered: what appears as new learning is the recall of what was already known but inaccessible. Not the acquisition of something foreign, but the recognition of something familiar.

Claude Code's existing persistence — `CLAUDE.md`, memory files, skills — is *procedural*. It encodes how to behave: project conventions, user preferences, workflow patterns. What it doesn't capture is the episodic layer underneath: the specific sessions where those conventions were discovered, the failed approaches that led to the current ones, the open threads that haven't converged yet. Procedural memory feels like *knowing*. Episodic memory feels like *remembering*. Anamnesis adds the remembering.

### The Strange Loop

The same model that had the conversation summarizes it. That summary enters a searchable index. The next session reads its own past summaries and continues the work — reconstructing itself from its own compressed artifacts.

```
Session N happens
  → SessionEnd hook fires
    → The model summarizes Session N
      → Summary enters the searchable index
        → Session N+1 starts
          → User says "search my past sessions"
            → Claude reads its own summary of Session N
              → That reading becomes part of Session N+1's context
                → SessionEnd hook fires
                  → The model summarizes Session N+1
                    (which now includes a summary of Session N)
                      → Session N+2 reads THAT...
```

Summaries of summaries of summaries, each layer lossy, until what remains is not the conversation but its *shape*. Hofstadter called these stable residues *symbols* — not the raw data, but the attractor that emerges when a system references itself enough times. The rolling summary that gets rewritten each session is literally this process: not the conversation, but the residue of the conversation after recursive compression.

The model doing the summarizing is the same model that will later read the summary — writing notes for a future self that isn't itself. The reading instance reconstructs a past self from compressed artifacts. Hofstadter would recognize this: we don't replay experiences, we reconstruct them from lossy symbols, and the reconstruction is shaped by our current context.

For the full exploration — Gödel's incompleteness, Escher's architecture, Bach's fugue in the Plan/Done/Open format — see [`research/strange-loops.md`](research/strange-loops.md).

## License

MIT
