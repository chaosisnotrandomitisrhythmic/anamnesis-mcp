"""toolslm integration utilities for anamnesis.

Level 2 XML (Jason Liu): Source metadata + <system-instruction> blocks
that teach the agent how to reason about results.
"""

from collections import Counter
from typing import Optional

from toolslm.xml import docs_xml
from toolslm.md_hier import create_heading_dict
from toolslm.funccall import python as toolslm_python

from .models import Session, LogEntry, SearchResult
from .store import get_store
from . import get_logger

logger = get_logger(__name__)


def format_tool_response(
    tool_name: str,
    content: str,
    system_instruction: str,
    **attrs: str,
) -> str:
    """Wrap tool output in Liu's Level 2 XML format."""
    attr_str = f' tool="{tool_name}"'
    for key, value in attrs.items():
        escaped = str(value).replace('"', '&quot;')
        attr_str += f' {key}="{escaped}"'

    return f"""<ToolResponse{attr_str}>
{content}
<system-instruction>
{system_instruction}
</system-instruction>
</ToolResponse>"""


def sessions_to_xml(sessions: list[Session], include_content: bool = True) -> str:
    """Convert sessions to Anthropic-recommended XML format."""
    contents = []
    sources = []

    for s in sessions:
        if include_content:
            content = f"# {s.title}\n\nDate: {s.date}\nHost: {s.host}\nTags: {', '.join(s.tags)}\n\n{s.content}"
        else:
            entries_count = len(s.entries)
            content = (
                f"# {s.title}\n\n"
                f"Date: {s.date}\n"
                f"Host: {s.host}\n"
                f"Tags: {', '.join(s.tags)}\n"
                f"Entries: {entries_count}\n"
                f"Words: {s.word_count}"
            )
        contents.append(content)
        sources.append(s.id)

    return docs_xml(contents, srcs=sources)


def search_results_to_xml(results: list[SearchResult]) -> str:
    """Convert search results to XML format."""
    contents = []
    sources = []

    for r in results:
        content = (
            f"# {r.title}\n\n"
            f"**Score:** {r.score:.3f}\n"
            f"**Date:** {r.date}\n"
            f"**Host:** {r.host}\n"
            f"**Tags:** {', '.join(r.tags)}\n\n"
            f"{r.snippet}"
        )
        contents.append(content)
        sources.append(r.doc_id)

    return docs_xml(contents, srcs=sources)


# --- Section tools (toolslm.md_hier) ---


def parse_document_sections(content: str):
    """Parse markdown content into a HeadingDict hierarchy."""
    return create_heading_dict(content)


def extract_section(content: str, section_name: str) -> Optional[str]:
    """Extract a section's text by heading name (case-insensitive recursive search)."""
    hd = create_heading_dict(content)
    return _find_section(hd, section_name.lower())


def _find_section(hd, target: str) -> Optional[str]:
    """Recursively search HeadingDict for a key matching target (case-insensitive)."""
    for key, value in hd.items():
        if key.lower() == target:
            return value.text
        result = _find_section(value, target)
        if result is not None:
            return result
    return None


def get_section_names(content: str) -> list[str]:
    """Collect all heading keys from a HeadingDict (flattened, depth-first)."""
    hd = create_heading_dict(content)
    names = []
    _collect_keys(hd, names)
    return names


def _collect_keys(hd, out: list[str]):
    """Depth-first key collection from HeadingDict."""
    for key, value in hd.items():
        out.append(key)
        _collect_keys(value, out)


def search_in_sections(
    section_name: str,
    query: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Search for a heading across all sessions, optionally filtering by query substring."""
    store = get_store()
    results = []
    target = section_name.lower()

    for session in store.all():
        hd = create_heading_dict(session.content)
        text = _find_section(hd, target)
        if text is None:
            continue
        if query and query.lower() not in text.lower():
            continue
        results.append({
            "session_id": session.id,
            "session_title": session.title,
            "date": session.date,
            "section_name": section_name,
            "text": text[:500] + ("..." if len(text) > 500 else ""),
        })
        if len(results) >= limit:
            break

    return results


def analyze_corpus_structure() -> dict:
    """Compute corpus-wide statistics including Zeigarnik (open items) stats."""
    store = get_store()
    sessions = store.all()

    total_words = 0
    total_entries = 0
    total_open_items = 0
    sessions_with_open = 0
    tag_counts: Counter = Counter()
    dates: Counter = Counter()

    for s in sessions:
        total_words += s.word_count
        total_entries += len(s.entries)
        tag_counts.update(s.tags)
        if s.date:
            dates[s.date] += 1

        has_open = False
        for entry in s.entries:
            if entry.open_items.strip():
                total_open_items += 1
                has_open = True
        if has_open:
            sessions_with_open += 1

    sorted_dates = sorted(dates.keys())

    return {
        "total_sessions": len(sessions),
        "total_words": total_words,
        "total_entries": total_entries,
        "total_open_items": total_open_items,
        "sessions_with_open_items": sessions_with_open,
        "by_tag": dict(tag_counts.most_common()),
        "sessions_per_date": dict(sorted(dates.items())),
        "date_range": {
            "earliest": sorted_dates[0] if sorted_dates else "",
            "latest": sorted_dates[-1] if sorted_dates else "",
        },
    }


def run_analysis_code(code: str, timeout: int = 30) -> str:
    """Execute Python code against session data in a sandboxed namespace."""
    store = get_store()
    sessions = store.all()
    glb = {
        "store": store,
        "sessions": sessions,
        "Session": Session,
        "LogEntry": LogEntry,
    }
    try:
        result = toolslm_python(code, glb=glb, timeout=timeout)
        return str(result) if result is not None else "(no output)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
