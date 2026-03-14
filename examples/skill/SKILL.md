---
name: anamnesis
description: Use when the user asks to search, find, summarize, or cross-reference past Claude Code sessions. Triggers on "find session", "past session", "session about", "what did we do", "session history", "search sessions", "cross-reference sessions".
---

# Anamnesis — Session Search & Cross-Reference

Search, summarize, and cross-reference past Claude Code session logs via the Anamnesis MCP server.

## How to Execute

### 1. Search for sessions

Use the `anamnesis` MCP tools:

**Core tools:**
- **`mcp__anamnesis__search_sessions`** — BM25 full-text search (primary tool)
- **`mcp__anamnesis__get_session`** — retrieve full session by ID
- **`mcp__anamnesis__list_sessions`** — browse/paginate with date/tag/host filters
- **`mcp__anamnesis__search_entries`** — cross-session search for Plan/Done/Open items

**Section tools:**
- **`mcp__anamnesis__get_section`** — extract a specific timestamped section from a session
- **`mcp__anamnesis__list_sections`** — list all headings in a session
- **`mcp__anamnesis__search_sections`** — find a heading across all sessions

**Analysis tools:**
- **`mcp__anamnesis__analyze_corpus`** — corpus stats (sessions, words, tags, open items)
- **`mcp__anamnesis__run_analysis`** — ad-hoc Python code execution against session data (local only)

### 2. Summarize results

When presenting session search results:
- List matching sessions with **date**, **title**, and a **one-line summary**
- Quote the rolling summary paragraph for relevant hits
- Highlight **Open** items — these are unfinished work the user may want to resume

### 3. Cross-reference sessions

When asked to cross-reference or find related sessions:
- Search for overlapping topics, tools, or projects across multiple sessions
- Group related sessions chronologically to show how work evolved
- Call out when an **Open** item from one session was resolved in a later session
- Note recurring themes or tools across sessions

### 4. Resume suggestions

When a session has open items, remind the user they can resume with:
```
claude --resume <session-id>
```
The session ID is in the footer of each log file.

## Rules

1. Always search via the MCP tools — don't rely on memory alone
2. Default to `search_sessions` for topic queries, `search_entries` for finding specific Plan/Done/Open items
3. When multiple sessions match, present them in chronological order
4. Keep summaries concise — the user can ask to read the full log
5. Use `get_session` to retrieve full content when the user wants detail
