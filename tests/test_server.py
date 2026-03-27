"""Tests for MCP server tool registration."""

from anamnesis.server import mcp


class TestServerTools:
    def test_server_has_name(self):
        assert mcp.name == "anamnesis"

    def test_tools_registered(self):
        """Verify all expected tools are registered on the FastMCP instance."""
        tool_names = {t.name for t in mcp._tool_manager._tools.values()}
        expected = {
            "search_sessions",
            "get_session",
            "list_sessions",
            "search_entries",
            "get_section",
            "list_sections",
            "search_sections",
            "save_session",
            "analyze_corpus",
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"
