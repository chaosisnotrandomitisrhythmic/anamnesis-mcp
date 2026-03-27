"""Tests for BM25 SearchIndex."""

from pathlib import Path
from unittest.mock import patch

from anamnesis.index import SearchIndex
from anamnesis.store import VaultStore


class TestSearchIndex:
    def _make_index(self, vault_path: Path) -> SearchIndex:
        """Create a SearchIndex backed by a temporary vault."""
        store = VaultStore(vault_path)
        index = SearchIndex()
        # Patch get_store to return our test store
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
        return index

    def test_build_indexes_sessions(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        index = SearchIndex()
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
        assert len(index._doc_ids) == 2

    def test_search_returns_relevant_results(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        index = SearchIndex()
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
            results = index.search("BM25 search")
        assert len(results) > 0
        assert any("BM25" in r.title for r in results)

    def test_search_ranks_relevant_higher(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        index = SearchIndex()
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
            results = index.search("Obsidian vault integration")
        assert len(results) > 0
        assert results[0].title == "Configure Obsidian vault"

    def test_search_empty_query_returns_empty(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        index = SearchIndex()
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
            results = index.search("")
        assert results == []

    def test_search_no_match_returns_empty(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        index = SearchIndex()
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
            results = index.search("xyzzyplughnotaword")
        assert results == []

    def test_search_with_date_filter(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        index = SearchIndex()
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
            results = index.search("session", date="2026-03-14")
        for r in results:
            assert r.date == "2026-03-14"

    def test_search_with_tag_filter(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        index = SearchIndex()
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
            results = index.search("session", tags=["obsidian"])
        for r in results:
            assert "obsidian" in r.tags

    def test_search_with_limit(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        index = SearchIndex()
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
            results = index.search("session", limit=1)
        assert len(results) <= 1

    def test_empty_vault_builds_without_error(self, tmp_path: Path):
        store = VaultStore(tmp_path)
        index = SearchIndex()
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
        assert index._doc_ids == []

    def test_empty_vault_search_returns_empty(self, tmp_path: Path):
        store = VaultStore(tmp_path)
        index = SearchIndex()
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
            results = index.search("anything")
        assert results == []

    def test_result_fields_populated(self, tmp_vault: Path):
        store = VaultStore(tmp_vault)
        index = SearchIndex()
        with patch("anamnesis.index.get_store", return_value=store):
            index._build()
            results = index.search("BM25")
        assert len(results) > 0
        r = results[0]
        assert r.doc_id
        assert r.title
        assert r.score > 0
        assert r.date
