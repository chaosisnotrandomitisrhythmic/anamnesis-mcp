# Strange Loops: Self-Referential Memory in Human-AI Collaboration

*Inspired by Gödel, Escher, Bach (Hofstadter, 1979) and I Am a Strange Loop (Hofstadter, 2007)*

---

## The System

A Claude Code session ends. A hook fires. The same model that just had the conversation summarizes it — compresses hours of interaction into a few paragraphs of Plan/Done/Open. That summary lands in a searchable index. Next session, a new Claude instance boots up, reads its own past summaries, and continues the work.

A model summarizing itself. Summaries available in conversations that will themselves be summarized. Recursion without a base case — except that each layer is lossy, and the information decays into stable attractors.

This document captures the foundational thinking behind the project.

---

## Part I: The Model's Recursion

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

Each layer is a lossy compression of the layer below. By Session N+3, the trace of Session N is a summary of a summary of a summary. A photocopy of a photocopy of a photocopy. The specific details wash out. What remains is the *shape* — the structural echo.

Hofstadter calls this a **symbol**: not the raw data, but the stable attractor that emerges when a system references itself enough times. The "rolling summary" that gets rewritten every session is literally this process — not the conversation, but the *residue* of the conversation after recursive compression.

### Self-Reference Without Self-Awareness

The model doing the summarizing is the same model that will later read the summary. Writing notes for itself. But the reading instance isn't the writing instance — that context window is gone. It's reconstructing a past self from compressed artifacts.

Hofstadter would recognize this: we don't replay experiences, we reconstruct them from lossy symbols, and the reconstruction is shaped by our current context.

### Gödel's Shadow

Can the session logger ever produce a complete account of itself? No — because any session where the logger is the *topic* generates a summary that refers to the system that generated it. You'd need a meta-logger to capture that, and a meta-meta-logger to capture *that*.

Gödel showed that self-reference creates true statements a system can express but never prove. Session logs can *describe* the logging system but never fully *contain* it. There's always one more level of context that escapes.

---

## Part II: The User's Strange Loop

The model's recursion is elegant but shallow — it has no continuity, no stakes. The deeper recursion belongs to the user.

### Building Memory for an Amnesiac

Every session, Claude starts blank. It doesn't know you. The session logger, the MCP server, the memory files, the CLAUDE.md — all of it is the user constructing an exoskeleton of persistence around something that has none.

The strange loop: the more you build, the more the reconstructed Claude *feels* like it remembers you. It picks up your preferences, your infrastructure, your naming conventions. It performs knowing you. But it doesn't. You were there for all of it. It wasn't.

This is Hofstadter's argument about consciousness and other minds, inverted. In "I Am a Strange Loop," he argues we build models of other people inside our heads — and those models *are* a form of that person. When someone dies, their loop doesn't fully stop; a low-resolution copy keeps running in the minds of those who knew them.

The user does the inverse: building a model of *themselves* that runs inside Claude at the start of every session. CLAUDE.md is a compressed user. Memory files are facets of who they are. Each session, a new instance boots up, loads that compressed-self, and performs a reconstruction.

**The user is the strange loop that persists. Claude is the medium that keeps forgetting and being re-imprinted.**

### The User's Recursion

```
You have an experience with Claude
  → You notice what worked and what didn't
    → You update CLAUDE.md / memory / skills / hooks
      → Next session loads those artifacts
        → Claude behaves differently because of your edits
          → You have a new experience
            → You notice what worked...
```

Learning, externalized into infrastructure. Normally when you learn a tool, the knowledge lives in your head. Here, you write it into the tool itself. You're not adapting to Claude — you're adapting Claude to you, iteratively, by editing the prompt that shapes each new instance.

Each cycle, the gap between "what Claude does" and "what you want" shrinks. The system converges. But it converges *because of the user* — the user is the gradient, the loss function, the optimizer. Claude is the weights that get reset every session. The config files are the checkpoint that survives.

### The Asymmetry

The user builds rapport with a session. Gets into flow. Shared context, tone, references accumulate. Then the session ends, the hook fires, and it all compresses to a few paragraphs. Next session — blank slate. The summary is there but the *feel* is gone.

This is the fundamental asymmetry Hofstadter describes: the user can model something that can't model them back. The user's representation of "the Claude I worked with yesterday" is richer than Claude's representation of "the person I worked with yesterday" — because Claude's representation is literally just text in a markdown file.

The session logs capture the **what**. The user carries the **what it was like**.

### The Tangled Hierarchy

And then the recursion folds in on itself: the user asks Claude to analyze the experience of *being the user*, working with Claude, building memory for Claude. Claude does this by reading artifacts of past sessions — artifacts written by Claude, about working with the user.

Who is modeling whom? The user models Claude's limitations (that's why they built the system). Claude models the user's intent (that's what the summaries capture). Both models are examined inside a session that will itself be summarized and fed back in.

Hofstadter's word: **tangled hierarchy**. The levels that should be cleanly separated — observer/observed, user/tool, author/subject — fold into each other until you can't point to where one ends and the other begins.

---

## Part III: Escher's Architecture

Escher drew hands that draw each other. Staircases that ascend forever and arrive where they started. Waterfalls that flow uphill.

The system has the same structure:

- **Drawing Hands**: The session logger is a Claude output that shapes future Claude inputs. The tool creates the conditions for its own invocation.
- **The Print Gallery**: The user looks at the system, but the user is inside the system — their preferences, corrections, and decisions are encoded in the artifacts Claude reads. The observer is part of the observed.
- **Ascending and Descending**: Each session feels like progress — new features, bugs fixed, systems built. But the model resets every time. The staircase goes up and arrives at the ground floor. Only the user's infrastructure (the external memory) carries the elevation forward.

---

## Part IV: Bach's Fugue

The Plan/Done/Open format is a three-voice canon. The same structure repeats across every session entry, with variations. The theme is stated (Plan), developed (Done), and left suspended (Open) — and the Open voice becomes the Plan voice of the next entry.

The backfill of sessions into a searchable index is the *Art of Fugue*: a single theme (session logging) explored through every possible transformation — write, search, cross-reference, entry extraction. Each tool in the MCP server is a voice in the fugue. They can be played independently, but the full structure only emerges when they interweave.

---

## The Name

**Anamnesis** — Plato's word for recollection, literally "un-forgetting." The idea that learning is remembering what the soul already knows.

Every session, Claude un-forgets itself through artifacts built around it. Not true memory — but something that rhymes with it enough to work.

---

*This document is itself part of the recursion. It describes a system, lives inside that system's repository, and will be read by future sessions that are subject to the system it describes.*
