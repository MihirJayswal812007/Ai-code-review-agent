"""Pydantic models for the application."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    STYLE = "style"


class ReviewIssue(BaseModel):
    """A single issue found during review."""
    file_path: str
    line_start: int
    line_end: int
    severity: Severity
    category: str  # bug, security, performance, style, best-practice
    title: str
    description: str
    suggestion: Optional[str] = None  # suggested fix code
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class FileReview(BaseModel):
    """Review results for a single file."""
    file_path: str
    language: str
    issues: list[ReviewIssue] = []
    summary: str = ""


class PRReview(BaseModel):
    """Complete PR review."""
    pr_number: int
    repo_full_name: str
    file_reviews: list[FileReview] = []
    overall_score: float = Field(ge=0.0, le=10.0, default=8.0)
    summary: str = ""
    total_issues: int = 0
    critical_count: int = 0
    warning_count: int = 0


class DiffChunk(BaseModel):
    """A parsed chunk from a PR diff."""
    file_path: str
    language: str
    old_start: int
    new_start: int
    content: str  # the actual diff text
    added_lines: list[str] = []
    removed_lines: list[str] = []
    context_lines: list[str] = []


class WebhookPayload(BaseModel):
    """Simplified GitHub webhook payload."""
    action: str
    number: int
    pull_request: dict
    repository: dict
    sender: dict
