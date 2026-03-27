"""Tests for VaultStore: parse, filter, save_session."""

from pathlib import Path

from anamnesis.store import VaultStore, _parse_entries, _parse_footer


class TestParseEntries:
    def test_parses_plan_done_open(self):
        text = (
            "## 2026-03-14 14:30\n"
            "- **Plan**: Do something\n"
            "- **Done**: Did it\n"
            "- **Open**: Still pending\n"
        )
        entries = _parse_entries(text)
        assert len(entries) == 1
        assert entries[0].timestamp == "2026-03-14 14:30"
        assert entries[0].plan == "Do something"
        assert entries[0].done == "Did it"
        assert entries[0].open_items == "Still pending"

    def test_parses_multiple_entries(self):
        text = (
            "## 2026-03-14 14:30\n"
            "- **Plan**: First task\n"
            "- **Done**: First done\n"
            "\n"
            "## 2026-03-14 16:00\n"
            "- **Plan**: Second task\n"
            "- **Done**: Second done\n"
        )
        entries = _parse_entries(text)
        assert len(entries) == 2
        assert entries[0].timestamp == "2026-03-14 14:30"
        assert entries[1].timestamp == "2026-03-14 16:00"

    def test_handles_missing_open(self):
        text = (
            "## 2026-03-14 14:30\n"
            "- **Plan**: Task\n"
            "- **Done**: Completed\n"
        )
        entries = _parse_entries(text)
        assert len(entries) == 1
        assert entries[0].open_items == ""

    def test_empty_text_returns_empty(self):
        assert _parse_entries("") == []

    def test_no_entries_returns_empty(self):
        assert _parse_entries("Just some random text\nwith no entries") == []


class TestParseFooter:
    def test_parses_full_footer(self):
        text = "*Session: `abc123` | Updated: 2026-03-14 16:00 | Host: myhost (Darwin arm64)*"
        result = _parse_footer(text)
        assert result["session_id"] == "abc123"
        assert result["host"] == "myhost"

    def test_parses_simple_footer(self):
        text = "*Session: `abc123` | Updated: 2026-03-14 16:00*"
        result = _parse_footer(text)
        assert result["session_id"] == "abc123"

    def test_parses_dir_footer(self):
        text = "*Session: `abc123` | Directory: `/home/user/project`*"
        result = _parse_footer(text)
        assert result["session_id"] == "abc123"
        assert result["cwd"] == "/home/user/project"

    def test_no_footer_returns_empty(self):
        result = _parse_footer("no footer here")
        assert result["session_id"] == ""


class TestVaultStore:
    def test_loads_sessions_from_vault(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        sessions = store.all()
        assert len(sessions) == 2

    def test_session_fields_populated(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        sessions = store.all()
        titles = {s.title for s in sessions}
        assert "Implement BM25 search" in titles
        assert "Configure Obsidian vault" in titles

    def test_session_entries_parsed(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        sessions = store.all()
        bm25_session = next(s for s in sessions if "BM25" in s.title)
        assert len(bm25_session.entries) == 2
        assert bm25_session.entries[0].plan == "Add BM25 search index for session logs"

    def test_get_by_id(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        sessions = store.all()
        for s in sessions:
            retrieved = store.get(s.id)
            assert retrieved is not None
            assert retrieved.id == s.id

    def test_get_nonexistent_returns_none(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        store.all()  # trigger load
        assert store.get("nonexistent1") is None

    def test_filter_by_date(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        results = store.filter(date="2026-03-14")
        assert len(results) == 1
        assert results[0].title == "Implement BM25 search"

    def test_filter_by_tags(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        results = store.filter(tags=["obsidian"])
        assert len(results) == 1
        assert results[0].title == "Configure Obsidian vault"

    def test_filter_by_host(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        results = store.filter(host="testhost")
        assert len(results) == 2

    def test_filter_with_limit(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        results = store.filter(limit=1)
        assert len(results) == 1

    def test_legacy_file_without_frontmatter(self, tmp_vault_with_legacy: Path):
        store = VaultStore(tmp_vault_with_legacy)
        sessions = store.all()
        assert len(sessions) == 3
        legacy = next(s for s in sessions if "Legacy" in s.title)
        assert "legacy-sess-id" in legacy.session_id

    def test_save_session_creates_file(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        result = store.save_session(
            title="New Test Session",
            summary="Testing save_session",
            plan="Write tests",
            done="Tests written",
            open_items="Run CI",
            cwd="/tmp/test",
            tags=["test"],
            session_id="manual-test-id",
        )
        assert result["created"] is True
        assert result["session_id"] == "manual-test-id"
        assert (tmp_vault / result["filename"]).exists()

        # Verify the file can be parsed back
        sessions = store.all()
        new_session = next(s for s in sessions if "New Test Session" in s.title)
        assert new_session.entries[0].plan == "Write tests"

    def test_save_session_updates_existing(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        # Create first
        result1 = store.save_session(
            title="Update Me",
            summary="First version",
            plan="Plan A",
            done="Done A",
            session_id="update-test-id",
        )
        assert result1["created"] is True

        # Update
        result2 = store.save_session(
            title="Update Me",
            summary="Updated version",
            plan="Plan B",
            done="Done B",
            session_id="update-test-id",
        )
        assert result2["created"] is False
        assert result2["filename"] == result1["filename"]

    def test_save_session_auto_generates_id(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        result = store.save_session(
            title="Auto ID Session",
            summary="No explicit session_id",
            plan="Auto",
            done="Auto",
        )
        assert result["created"] is True
        assert len(result["session_id"]) > 0

    def test_freshness_detects_new_file(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        assert len(store.all()) == 2
        gen1 = store.generation

        # Add a new file
        new_md = (
            "---\nsession_id: \"new-sess\"\ndate: \"2026-03-16\"\n"
            "host: \"h\"\ncwd: \"/\"\ntags: []\n---\n\n# New\n\nNew session.\n"
        )
        (tmp_vault / "2026-03-16_new.md").write_text(new_md)
        assert len(store.all()) == 3
        assert store.generation > gen1

    def test_get_all_tags(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        tags = store.get_all_tags()
        assert "mcp" in tags
        assert "testing" in tags
        assert "obsidian" in tags
