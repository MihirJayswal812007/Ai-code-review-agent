"""Pytest configuration and shared fixtures."""

import pytest
from src.models import DiffChunk, ReviewIssue, FileReview, PRReview, Severity


@pytest.fixture
def sample_python_diff():
    """Sample Python diff for testing."""
    return """diff --git a/app.py b/app.py
index 1234567..abcdefg 100644
--- a/app.py
+++ b/app.py
@@ -10,7 +10,7 @@ def calculate_total(items):
     total = 0
     for item in items:
-        total += item.price
+        total += item.price * item.quantity
     return total
"""


@pytest.fixture
def sample_chunk():
    """Sample DiffChunk for testing."""
    return DiffChunk(
        file_path="app.py",
        language="python",
        old_start=10,
        new_start=10,
        content="sample diff content",
        added_lines=["    total += item.price * item.quantity"],
        removed_lines=["    total += item.price"],
        context_lines=["def calculate_total(items):"],
    )


@pytest.fixture
def sample_issue():
    """Sample ReviewIssue for testing."""
    return ReviewIssue(
        file_path="app.py",
        line_start=13,
        line_end=13,
        severity=Severity.WARNING,
        category="bug",
        title="Missing null check",
        description="item.quantity might be null",
        suggestion="if item.quantity is not None:\n    total += item.price * item.quantity",
    )


@pytest.fixture
def sample_review():
    """Sample PRReview for testing."""
    issue = ReviewIssue(
        file_path="app.py",
        line_start=13,
        line_end=13,
        severity=Severity.WARNING,
        category="bug",
        title="Test issue",
        description="Test description",
    )
    file_review = FileReview(
        file_path="app.py",
        language="python",
        issues=[issue],
        summary="Test file review",
    )
    return PRReview(
        pr_number=123,
        repo_full_name="test/repo",
        file_reviews=[file_review],
        overall_score=8.5,
        summary="Test PR summary",
        total_issues=1,
        critical_count=0,
        warning_count=1,
    )
