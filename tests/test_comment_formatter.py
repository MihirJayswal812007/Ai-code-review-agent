"""Tests for comment_formatter module."""

from src.comment_formatter import (
    format_summary_comment,
    format_inline_comments,
    _format_issue_comment,
)
from src.models import Severity


def test_format_summary_comment(sample_review):
    """Test formatting the PR summary comment."""
    summary = format_summary_comment(sample_review)
    
    assert "🤖 AI Code Review Summary" in summary
    assert "8.5/10" in summary
    assert "Total Issues" in summary
    assert "1" in summary  # total_issues
    assert "app.py" in summary
    assert "Powered by AI Code Review Agent" in summary


def test_format_summary_comment_no_issues():
    """Test summary formatting when no issues found."""
    from src.models import PRReview
    review = PRReview(
        pr_number=1,
        repo_full_name="test/repo",
        file_reviews=[],
        overall_score=10.0,
        summary="✅ No issues found. Code looks clean and well-written!",
        total_issues=0,
        critical_count=0,
        warning_count=0,
    )
    summary = format_summary_comment(review)
    
    assert "10.0/10" in summary
    assert "0" in summary


def test_format_inline_comments(sample_review):
    """Test formatting inline comments from a review."""
    comments = format_inline_comments(sample_review)
    
    assert len(comments) == 1
    comment = comments[0]
    assert comment["path"] == "app.py"
    assert comment["line"] == 13
    assert "WARNING" in comment["body"]
    assert "Test issue" in comment["body"]


def test_format_issue_comment(sample_issue):
    """Test formatting a single issue as a comment."""
    comment = _format_issue_comment(sample_issue)
    
    assert "🟡" in comment  # WARNING emoji
    assert "WARNING" in comment
    assert "Missing null check" in comment
    assert "bug" in comment
    assert "item.quantity might be null" in comment
    assert "Suggested fix" in comment
    assert "if item.quantity is not None" in comment


def test_format_issue_comment_no_suggestion():
    """Test formatting an issue without a suggestion."""
    from src.models import ReviewIssue
    issue = ReviewIssue(
        file_path="test.py",
        line_start=1,
        line_end=1,
        severity=Severity.INFO,
        category="style",
        title="Style issue",
        description="Consider using better naming",
        suggestion=None,
    )
    comment = _format_issue_comment(issue)
    
    assert "Suggested fix" not in comment
    assert "Style issue" in comment
