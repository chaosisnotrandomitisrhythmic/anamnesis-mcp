"""Central config for all MCP tool prompts and instructions."""


class ToolConfig:

    SERVER_INSTRUCTIONS = (
        "Anamnesis — un-forgetting for AI.\n"
        "\n"
        "Search and browse past Claude Code session logs.\n"
        "\n"
        "Core tools:\n"
        "- search_sessions: BM25 full-text search over session logs\n"
        "- get_session: Retrieve full session by ID\n"
        "- list_sessions: Browse/paginate with date/tag/host filters\n"
        "- search_entries: Cross-session search for Plan/Done/Open items\n"
        "\n"
        "Section tools:\n"
        "- get_section: Extract a specific section from a session by heading\n"
        "- list_sections: List all section headings in a session\n"
        "- search_sections: Find a section type across all sessions\n"
        "\n"
        "Write tools:\n"
        "- save_session: Save a session log (for environments without SessionEnd hooks)\n"
        "\n"
        "Analysis tools:\n"
        "- analyze_corpus: Get statistics about the knowledge base\n"
        "- run_analysis: Execute Python code for ad-hoc analysis (local only)\n"
        "\n"
        "All responses use XML format with <system-instruction> blocks.\n"
        "Follow the instructions in each response.\n"
        "\n"
        "When working with tool results, write down any important information "
        "you might need later in your response, as the original tool result "
        "may be cleared later."
    )

    # search_sessions
    SEARCH_DESCRIPTION = (
        "Search session logs using BM25 full-text search.\n"
        "\n"
        "Args:\n"
        "    query: Search terms (required)\n"
        "    date: Filter to specific date (YYYY-MM-DD)\n"
        "    tags: Filter to sessions with ALL these tags\n"
        "    limit: Max results (default 10)\n"
        "\n"
        "Returns:\n"
        "    XML with matching sessions ranked by relevance"
    )

    SEARCH_INSTRUCTION = (
        "Use session IDs with get_session to retrieve full content. "
        "Use search_entries to find specific Plan/Done/Open items across sessions."
    )

    SEARCH_NO_RESULTS_INSTRUCTION = (
        "No results found. Try broader search terms or remove filters."
    )

    # get_session
    GET_SESSION_DESCRIPTION = (
        "Retrieve a full session by ID.\n"
        "\n"
        "Args:\n"
        "    session_id: The 12-character session ID (from search results)\n"
        "\n"
        "Returns:\n"
        "    XML with full session content including all log entries"
    )

    GET_SESSION_INSTRUCTION = (
        "This is the full session log. Summarize the key decisions and outcomes "
        "when presenting to the user."
    )

    # list_sessions
    LIST_SESSIONS_DESCRIPTION = (
        "List sessions with optional filtering.\n"
        "\n"
        "Args:\n"
        "    date: Filter to specific date (YYYY-MM-DD)\n"
        "    tags: Filter to sessions with ALL these tags\n"
        "    host: Filter to specific hostname\n"
        "    limit: Max results (default 20)\n"
        "    offset: Skip first N results for pagination\n"
        "\n"
        "Returns:\n"
        "    XML listing of sessions sorted by date (newest first)"
    )

    LIST_SESSIONS_INSTRUCTION = (
        "Use get_session with a session ID to retrieve full content. "
        "Sessions are sorted newest first."
    )

    # search_entries
    SEARCH_ENTRIES_DESCRIPTION = (
        "Search across all session log entries (Plan/Done/Open items).\n"
        "\n"
        "Finds specific entry types across all sessions. Great for:\n"
        "- Finding all open items: entry_type='open'\n"
        "- Finding what was done on a topic: entry_type='done', query='terraform'\n"
        "- Finding all plans: entry_type='plan'\n"
        "\n"
        "Args:\n"
        "    entry_type: Filter by type: 'plan', 'done', or 'open' (optional)\n"
        "    query: Text to search within entries (optional)\n"
        "    date: Filter to specific date (YYYY-MM-DD, optional)\n"
        "    limit: Max results (default 20)\n"
        "\n"
        "Returns:\n"
        "    XML with matching entries from across all sessions"
    )

    SEARCH_ENTRIES_INSTRUCTION = (
        "These are individual log entries from across sessions. "
        "Use get_session with the session ID for full context."
    )

    SEARCH_ENTRIES_NO_RESULTS_INSTRUCTION = (
        "No matching entries found. Try broader search terms or remove filters."
    )

    # get_section
    GET_SECTION_DESCRIPTION = (
        "Extract a specific section from a session by heading.\n"
        "\n"
        "Session files have ## YYYY-MM-DD HH:MM timestamped headings.\n"
        "\n"
        "Args:\n"
        "    session_id: The 12-character session ID\n"
        "    section_name: The heading text to find (case-insensitive)\n"
        "\n"
        "Returns:\n"
        "    XML with the section content"
    )

    GET_SECTION_INSTRUCTION = (
        "This is a single section from the session. "
        "Use get_session for full context."
    )

    GET_SECTION_NOT_FOUND_INSTRUCTION = (
        "Section not found. Use list_sections to see available headings."
    )

    # list_sections
    LIST_SECTIONS_DESCRIPTION = (
        "List all section headings in a session.\n"
        "\n"
        "Args:\n"
        "    session_id: The 12-character session ID\n"
        "\n"
        "Returns:\n"
        "    XML listing all headings in the session"
    )

    LIST_SECTIONS_INSTRUCTION = (
        "Use get_section with a heading name to extract its content."
    )

    # search_sections
    SEARCH_SECTIONS_DESCRIPTION = (
        "Find a specific heading across all sessions.\n"
        "\n"
        "Note: headings are timestamps (YYYY-MM-DD HH:MM), not semantic names.\n"
        "Use search_entries for Plan/Done/Open content search.\n"
        "\n"
        "Args:\n"
        "    section_name: The heading text to find (case-insensitive)\n"
        "    query: Optional text to filter within matched sections\n"
        "    limit: Max results (default 10)\n"
        "\n"
        "Returns:\n"
        "    XML with matching sections from across sessions"
    )

    SEARCH_SECTIONS_INSTRUCTION = (
        "Use get_session with a session ID for full context."
    )

    SEARCH_SECTIONS_NO_RESULTS_INSTRUCTION = (
        "No matching sections found. Try different heading text or use search_sessions for full-text search."
    )

    # analyze_corpus
    ANALYZE_CORPUS_DESCRIPTION = (
        "Get corpus-wide statistics about the session knowledge base.\n"
        "\n"
        "Returns:\n"
        "    Session count, word count, tag distribution, open items count "
        "(Zeigarnik stats), sessions per date, date range"
    )

    ANALYZE_CORPUS_INSTRUCTION = (
        "Open items (Zeigarnik stats) represent unresolved tasks that create cognitive tension. "
        "Use search_entries with entry_type='open' to surface specific unresolved items."
    )

    # run_analysis
    RUN_ANALYSIS_DESCRIPTION = (
        "Execute Python code for ad-hoc analysis of session data. LOCAL ONLY.\n"
        "\n"
        "Available in namespace: sessions (list[Session]), store (VaultStore), "
        "Session, LogEntry\n"
        "\n"
        "Args:\n"
        "    code: Python code to execute (last expression is returned)\n"
        "    timeout: Max execution time in seconds (default 30)\n"
        "\n"
        "Returns:\n"
        "    String result of the last expression"
    )

    RUN_ANALYSIS_INSTRUCTION = (
        "This is the result of ad-hoc Python analysis. "
        "Present it clearly to the user."
    )

    # save_session
    SAVE_SESSION_DESCRIPTION = (
        "Save a session log to the vault.\n"
        "\n"
        "Use this when running in an environment without SessionEnd hooks\n"
        "(e.g. Cursor, VS Code) to capture session history before clearing.\n"
        "\n"
        "The calling agent should summarize the conversation into the fields below.\n"
        "\n"
        "Args:\n"
        "    title: Descriptive session title (no # prefix)\n"
        "    summary: 2-5 sentence overview of the session\n"
        "    plan: What the user set out to do\n"
        "    done: What was accomplished\n"
        "    open_items: Unfinished items or next steps (optional)\n"
        "    cwd: Working directory (optional)\n"
        "    tags: List of tags (optional)\n"
        "\n"
        "Returns:\n"
        "    Confirmation with the filename written"
    )

    SAVE_SESSION_INSTRUCTION = (
        "Session saved. The file is now in the vault and will be "
        "picked up by the search index automatically."
    )

    # Shared
    SESSION_NOT_FOUND_INSTRUCTION = (
        "Check the session ID. Use search_sessions to find valid IDs."
    )

    @staticmethod
    def session_not_found_error(session_id: str) -> str:
        return f"<error>Session '{session_id}' not found</error>"

    @staticmethod
    def section_not_found_error(section_name: str, session_title: str) -> str:
        return f"<error>Section '{section_name}' not found in '{session_title}'</error>"
