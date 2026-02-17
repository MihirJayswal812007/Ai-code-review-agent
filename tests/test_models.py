"""Tests for models module."""

import pytest
from pydantic import ValidationError
from src.models import (
    Severity,
    ReviewIssue,
    FileReview,
    PRReview,
    DiffChunk,
)


def test_severity_enum():
    """Test Severity enum values."""
    assert Severity.CRITICAL == "critical"
    assert Severity.WARNING == "warning"
    assert Severity.INFO == "info"
    assert Severity.STYLE == "style"


def test_review_issue_creation():
    """Test creating a ReviewIssue."""
    issue = ReviewIssue(
        file_path="test.py",
        line_start=10,
        line_end=12,
        severity=Severity.WARNING,
        category="bug",
        title="Test issue",
        description="Test description",
    )
    assert issue.file_path == "test.py"
    assert issue.severity == Severity.WARNING
    assert issue.confidence == 0.8  # default value


def test_review_issue_confidence_validation():
    """Test confidence score validation."""
    # Valid confidence
    issue = ReviewIssue(
        file_path="test.py",
        line_start=1,
        line_end=1,
        severity=Severity.INFO,
        category="style",
        title="Test",
        description="Test",
        confidence=0.9,
    )
    assert issue.confidence == 0.9
    
    # Invalid confidence should raise ValidationError
    with pytest.raises(ValidationError):
        ReviewIssue(
            file_path="test.py",
            line_start=1,
            line_end=1,
            severity=Severity.INFO,
            category="style",
            title="Test",
            description="Test",
            confidence=1.5,  # > 1.0
        )


def test_file_review_creation():
    """Test creating a FileReview."""
    review = FileReview(
        file_path="test.py",
        language="python",
        summary="Test summary",
    )
    assert review.file_path == "test.py"
    assert len(review.issues) == 0  # default empty list


def test_pr_review_score_validation():
    """Test PRReview score validation."""
    # Valid score
    review = PRReview(
        pr_number=1,
        repo_full_name="owner/repo",
        overall_score=8.5,
    )
    assert review.overall_score == 8.5
    
    # Invalid score
    with pytest.raises(ValidationError):
        PRReview(
            pr_number=1,
            repo_full_name="owner/repo",
            overall_score=11.0,  # > 10.0
        )


def test_diff_chunk_creation():
    """Test creating a DiffChunk."""
    chunk = DiffChunk(
        file_path="test.py",
        language="python",
        old_start=10,
        new_start=15,
        content="test content",
        added_lines=["line 1"],
        removed_lines=["old line"],
    )
    assert chunk.file_path == "test.py"
    assert chunk.old_start == 10
    assert chunk.new_start == 15
    assert len(chunk.context_lines) == 0  # default empty
