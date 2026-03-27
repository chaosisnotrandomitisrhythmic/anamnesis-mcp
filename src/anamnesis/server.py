import json
import os
from typing import Optional

from fastmcp import FastMCP

from .config import ToolConfig
from .index import get_index
from .store import get_store
from .toolslm_utils import (
    format_tool_response,
    sessions_to_xml,
    search_results_to_xml,
    extract_section,
    get_section_names,
    search_in_sections,
    analyze_corpus_structure,
    run_analysis_code,
)
from . import get_logger

logger = get_logger(__name__)

IS_LOCAL = os.getenv("MCP_TRANSPORT", "stdio") == "stdio"

mcp = FastMCP(
    name="anamnesis",
    instructions=ToolConfig.SERVER_INSTRUCTIONS,
)


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.SEARCH_DESCRIPTION)
def search_sessions(
    query: str,
    date: Optional[str] = None,
    tags: list[str] = [],
    limit: int = 10,
) -> str:
    index = get_index()
    results = index.search(query, date=date, tags=tags, limit=limit)

    if not results:
        return format_tool_response(
            "search_sessions",
            '<results count="0" />',
            ToolConfig.SEARCH_NO_RESULTS_INSTRUCTION,
            query=query,
        )

    xml_body = search_results_to_xml(results)
    return format_tool_response(
        "search_sessions",
        f'<results count="{len(results)}">\n{xml_body}\n</results>',
        ToolConfig.SEARCH_INSTRUCTION,
        query=query,
    )


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.GET_SESSION_DESCRIPTION)
def get_session(session_id: str) -> str:
    store = get_store()
    session = store.get(session_id)
    if not session:
        return format_tool_response(
            "get_session",
            ToolConfig.session_not_found_error(session_id),
            ToolConfig.SESSION_NOT_FOUND_INSTRUCTION,
            session_id=session_id,
        )

    xml_body = sessions_to_xml([session], include_content=True)
    return format_tool_response(
        "get_session",
        xml_body,
        ToolConfig.GET_SESSION_INSTRUCTION,
        session_id=session_id,
    )


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.LIST_SESSIONS_DESCRIPTION)
def list_sessions(
    date: Optional[str] = None,
    tags: list[str] = [],
    host: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> str:
    store = get_store()
    sessions = store.filter(date=date, tags=tags, host=host, limit=limit, offset=offset)

    xml_body = sessions_to_xml(sessions, include_content=False)
    return format_tool_response(
        "list_sessions",
        f'<results count="{len(sessions)}" offset="{offset}">\n{xml_body}\n</results>',
        ToolConfig.LIST_SESSIONS_INSTRUCTION,
    )


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.SEARCH_ENTRIES_DESCRIPTION)
def search_entries(
    entry_type: Optional[str] = None,
    query: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = 20,
) -> str:
    store = get_store()
    results = []

    for session in store.all():
        if date and session.date != date:
            continue

        for entry in session.entries:
            if entry_type == "plan":
                text = entry.plan
            elif entry_type == "done":
                text = entry.done
            elif entry_type == "open":
                text = entry.open_items
            elif entry_type is None:
                text = f"{entry.plan} {entry.done} {entry.open_items}"
            else:
                continue

            if not text.strip():
                continue

            if query and query.lower() not in text.lower():
                continue

            results.append({
                "session_id": session.id,
                "session_title": session.title,
                "date": session.date,
                "timestamp": entry.timestamp,
                "type": entry_type or "all",
                "text": text[:500] + ("..." if len(text) > 500 else ""),
            })

            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    if not results:
        return format_tool_response(
            "search_entries",
            '<results count="0" />',
            ToolConfig.SEARCH_ENTRIES_NO_RESULTS_INSTRUCTION,
            entry_type=entry_type or "all",
        )

    items_xml = "\n".join(
        f'    <entry session_id="{r["session_id"]}" title="{r["session_title"]}" '
        f'date="{r["date"]}" timestamp="{r["timestamp"]}" type="{r["type"]}">\n'
        f'      {r["text"]}\n'
        f'    </entry>'
        for r in results
    )

    return format_tool_response(
        "search_entries",
        f'<results count="{len(results)}">\n{items_xml}\n</results>',
        ToolConfig.SEARCH_ENTRIES_INSTRUCTION,
        entry_type=entry_type or "all",
    )


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.GET_SECTION_DESCRIPTION)
def get_section(session_id: str, section_name: str) -> str:
    store = get_store()
    session = store.get(session_id)
    if not session:
        return format_tool_response(
            "get_section",
            ToolConfig.session_not_found_error(session_id),
            ToolConfig.SESSION_NOT_FOUND_INSTRUCTION,
            session_id=session_id,
        )

    text = extract_section(session.content, section_name)
    if text is None:
        available = get_section_names(session.content)
        sections_list = "\n".join(f"  - {name}" for name in available)
        return format_tool_response(
            "get_section",
            f"{ToolConfig.section_not_found_error(section_name, session.title)}\n"
            f"<available-sections>\n{sections_list}\n</available-sections>",
            ToolConfig.GET_SECTION_NOT_FOUND_INSTRUCTION,
            session_id=session_id,
            section_name=section_name,
        )

    return format_tool_response(
        "get_section",
        f'<section name="{section_name}">\n{text}\n</section>',
        ToolConfig.GET_SECTION_INSTRUCTION,
        session_id=session_id,
        section_name=section_name,
    )


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.LIST_SECTIONS_DESCRIPTION)
def list_sections(session_id: str) -> str:
    store = get_store()
    session = store.get(session_id)
    if not session:
        return format_tool_response(
            "list_sections",
            ToolConfig.session_not_found_error(session_id),
            ToolConfig.SESSION_NOT_FOUND_INSTRUCTION,
            session_id=session_id,
        )

    names = get_section_names(session.content)
    sections_xml = "\n".join(f'  <heading>{name}</heading>' for name in names)

    return format_tool_response(
        "list_sections",
        f'<sections count="{len(names)}">\n{sections_xml}\n</sections>',
        ToolConfig.LIST_SECTIONS_INSTRUCTION,
        session_id=session_id,
    )


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.SEARCH_SECTIONS_DESCRIPTION)
def search_sections(
    section_name: str,
    query: Optional[str] = None,
    limit: int = 10,
) -> str:
    results = search_in_sections(section_name, query=query, limit=limit)

    if not results:
        return format_tool_response(
            "search_sections",
            '<results count="0" />',
            ToolConfig.SEARCH_SECTIONS_NO_RESULTS_INSTRUCTION,
            section_name=section_name,
        )

    items_xml = "\n".join(
        f'    <section session_id="{r["session_id"]}" title="{r["session_title"]}" '
        f'date="{r["date"]}" name="{r["section_name"]}">\n'
        f'      {r["text"]}\n'
        f'    </section>'
        for r in results
    )

    return format_tool_response(
        "search_sections",
        f'<results count="{len(results)}">\n{items_xml}\n</results>',
        ToolConfig.SEARCH_SECTIONS_INSTRUCTION,
        section_name=section_name,
    )


@mcp.tool(description=ToolConfig.SAVE_SESSION_DESCRIPTION)
def save_session(
    title: str,
    summary: str,
    plan: str,
    done: str,
    open_items: str = "",
    cwd: str = "",
    tags: list[str] = [],
    session_id: Optional[str] = None,
) -> str:
    store = get_store()
    result = store.save_session(
        title=title,
        summary=summary,
        plan=plan,
        done=done,
        open_items=open_items,
        cwd=cwd,
        tags=tags,
        session_id=session_id,
    )

    action = "Created" if result["created"] else "Updated"
    return format_tool_response(
        "save_session",
        f'<result action="{action}" filename="{result["filename"]}" '
        f'session_id="{result["session_id"]}" />',
        ToolConfig.SAVE_SESSION_INSTRUCTION,
    )


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.ANALYZE_CORPUS_DESCRIPTION)
def analyze_corpus() -> str:
    stats = analyze_corpus_structure()

    return format_tool_response(
        "analyze_corpus",
        f"<corpus-stats>\n{json.dumps(stats, indent=2)}\n</corpus-stats>",
        ToolConfig.ANALYZE_CORPUS_INSTRUCTION,
    )


if IS_LOCAL:
    @mcp.tool(description=ToolConfig.RUN_ANALYSIS_DESCRIPTION)
    def run_analysis(code: str, timeout: int = 30) -> str:
        result = run_analysis_code(code, timeout=timeout)

        return format_tool_response(
            "run_analysis",
            f"<analysis-result>\n{result}\n</analysis-result>",
            ToolConfig.RUN_ANALYSIS_INSTRUCTION,
        )
