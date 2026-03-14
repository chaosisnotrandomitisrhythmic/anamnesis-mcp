import time
from typing import Optional

import Stemmer
import bm25s

from .store import get_store
from .models import SearchResult
from . import get_logger

logger = get_logger(__name__)

LANGUAGE = "english"
STOPWORDS = "en"


class SearchIndex:
    """BM25 search index for Claude session logs.

    Pure in-memory — builds on first search, rebuilds automatically
    when the vault store detects file changes (generation-based).
    """

    def __init__(self):
        self.stemmer = Stemmer.Stemmer(LANGUAGE)
        self._index: Optional[bm25s.BM25] = None
        self._doc_ids: list[str] = []
        self._built_generation: int = -1

    def _tokenize(self, texts: list[str]) -> list[list[str]]:
        return bm25s.tokenize(texts, stopwords=STOPWORDS, stemmer=self.stemmer)

    def _build(self):
        store = get_store()
        sessions = store.all()

        if not sessions:
            logger.warning("No sessions to index")
            return

        start = time.perf_counter()

        corpus = []
        self._doc_ids = []
        for s in sessions:
            entry_text = " ".join(
                f"{e.plan} {e.done} {e.open_items}" for e in s.entries
            )
            text = f"{s.title} {s.summary} {entry_text} {' '.join(s.tags)}"
            corpus.append(text)
            self._doc_ids.append(s.id)

        tokens = self._tokenize(corpus)
        self._index = bm25s.BM25()
        self._index.index(tokens)

        self._built_generation = store.generation
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"Index ready: {len(sessions)} sessions in {elapsed_ms:.0f}ms")

    def _ensure_fresh(self):
        """Rebuild index if store has newer data."""
        store = get_store()
        if self._index is None or store.generation != self._built_generation:
            self._build()

    def search(
        self,
        query: str,
        date: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        self._ensure_fresh()

        if not self._index or not query.strip():
            return []

        k = limit * 3 if (date or tags) else limit
        k = min(k, len(self._doc_ids))

        query_tokens = self._tokenize([query])
        results, scores = self._index.retrieve(query_tokens, k=k)

        store = get_store()
        search_results = []

        for i, score in enumerate(scores[0]):
            if score <= 0:
                continue

            doc_id = self._doc_ids[int(results[0][i])]
            session = store.get(doc_id)
            if not session:
                continue

            if date and session.date != date:
                continue
            if tags and not all(t in session.tags for t in tags):
                continue

            snippet = (
                session.summary[:200].rsplit(" ", 1)[0] + "..."
                if len(session.summary) > 200
                else session.summary
            ) or session.title

            search_results.append(
                SearchResult(
                    doc_id=session.id,
                    title=session.title,
                    snippet=snippet,
                    score=round(float(score), 3),
                    date=session.date,
                    tags=session.tags,
                    host=session.host,
                )
            )

            if len(search_results) >= limit:
                break

        return search_results


_index: Optional[SearchIndex] = None


def get_index() -> SearchIndex:
    global _index
    if _index is None:
        _index = SearchIndex()
    return _index
