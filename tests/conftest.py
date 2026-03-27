"""Shared fixtures for anamnesis tests."""

import textwrap
from pathlib import Path

import pytest


SAMPLE_SESSION_MD = textwrap.dedent("""\
    ---
    session_id: "test-session-001"
    date: "2026-03-14"
    host: "testhost"
    cwd: "/home/user/project"
    tags: ["mcp", "testing"]
    ---

    # Implement BM25 search

    Added BM25 full-text search over session logs using bm25s library.

    ---

    ## 2026-03-14 14:30
    - **Plan**: Add BM25 search index for session logs
    - **Done**: Implemented SearchIndex with tokenization and query
    - **Open**: Need to add date/tag filtering

    ## 2026-03-14 16:00
    - **Plan**: Add filtering to search results
    - **Done**: Added date and tag post-filters to search

    ---

    *Session: `test-session-001` | Updated: 2026-03-14 16:00 | Host: testhost (Darwin arm64)*
""")

SAMPLE_SESSION_2_MD = textwrap.dedent("""\
    ---
    session_id: "test-session-002"
    date: "2026-03-15"
    host: "testhost"
    cwd: "/home/user/other"
    tags: ["obsidian"]
    ---

    # Configure Obsidian vault

    Set up Obsidian vault integration with anamnesis for graph view and sync.

    ---

    ## 2026-03-15 10:00
    - **Plan**: Configure vault path and Obsidian integration
    - **Done**: Added ANAMNESIS_VAULT env var support
    - **Open**: Document Obsidian setup in README

    ---

    *Session: `test-session-002` | Updated: 2026-03-15 10:00 | Host: testhost (Darwin arm64)*
""")

SAMPLE_NO_FRONTMATTER_MD = textwrap.dedent("""\
    # Legacy session

    This session has no YAML frontmatter.

    ---

    ## 2026-03-10 09:00
    - **Plan**: Test footer fallback parsing
    - **Done**: Verified footer regex works

    ---

    *Session: `legacy-sess-id` | Updated: 2026-03-10 09:00 | Host: oldhost (Linux x86_64)*
""")


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create a temporary vault with sample session files."""
    (tmp_path / "2026-03-14_1430_implement-bm25-search.md").write_text(SAMPLE_SESSION_MD)
    (tmp_path / "2026-03-15_1000_configure-obsidian-vault.md").write_text(SAMPLE_SESSION_2_MD)
    return tmp_path


@pytest.fixture
def tmp_vault_with_legacy(tmp_vault: Path) -> Path:
    """Vault that also includes a file without YAML frontmatter."""
    (tmp_vault / "2026-03-10_0900_legacy-session.md").write_text(SAMPLE_NO_FRONTMATTER_MD)
    return tmp_vault
