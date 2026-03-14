from pydantic import BaseModel, Field
from datetime import datetime


class LogEntry(BaseModel):
    """A single timestamped log entry within a session."""

    timestamp: str = Field(..., description="Entry timestamp, e.g. '2026-03-13 14:30'")
    plan: str = Field(default="", description="What the user set out to do")
    done: str = Field(default="", description="What was accomplished")
    open_items: str = Field(default="", description="Unfinished items or next steps")


class Session(BaseModel):
    """A Claude Code session log."""

    id: str = Field(..., min_length=12, max_length=12, description="12-char hash of session_id")
    session_id: str = Field(..., description="Original UUID from Claude Code")
    title: str = Field(..., description="H1 title from session summary")
    summary: str = Field(default="", description="Rolling summary paragraph")
    entries: list[LogEntry] = Field(default=[], description="Structured Plan/Done/Open entries")
    content: str = Field(default="", description="Full markdown content")
    tags: list[str] = Field(default=[], description="Auto-generated tags")
    cwd: str = Field(default="", description="Working directory")
    host: str = Field(default="", description="Hostname")
    date: str = Field(default="", description="Date string YYYY-MM-DD")
    created_at: str = Field(default="", description="ISO timestamp when first created")
    updated_at: str = Field(default="", description="ISO timestamp when last updated")
    word_count: int = Field(default=0, description="Word count of content")

    def model_post_init(self, __context):
        if not self.word_count:
            self.word_count = len(self.content.split())
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


class SearchResult(BaseModel):
    """A search result with relevance score."""

    doc_id: str = Field(..., description="Session ID to retrieve full content")
    title: str = Field(..., description="Session title")
    snippet: str = Field(..., description="Preview excerpt")
    score: float = Field(..., description="BM25 relevance score")
    date: str = Field(default="", description="Session date")
    tags: list[str] = Field(default=[], description="Session tags")
    host: str = Field(default="", description="Hostname")
