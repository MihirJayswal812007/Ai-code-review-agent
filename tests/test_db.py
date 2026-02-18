"""Tests for SQLite review database."""

import tempfile
from pathlib import Path
from src.db import ReviewDatabase


def _make_db():
    """Create a test database in a temp directory."""
    tmp = tempfile.mkdtemp()
    return ReviewDatabase(db_path=Path(tmp) / "test_reviews.db")


def test_save_and_retrieve():
    """Test saving and retrieving reviews."""
    db = _make_db()
    db.save_review(
        timestamp="2025-01-01T12:00:00",
        repo="owner/repo",
        pr_number=1,
        pr_url="https://github.com/owner/repo/pull/1",
        score=8.5,
        total_issues=2,
        critical=1,
        warnings=1,
        commit_sha="abc123",
    )
    reviews = db.get_recent_reviews()
    assert len(reviews) == 1
    assert reviews[0]["repo"] == "owner/repo"
    assert reviews[0]["score"] == 8.5
    assert reviews[0]["commit_sha"] == "abc123"


def test_recent_reviews_ordering():
    """Test that reviews are returned in reverse chronological order."""
    db = _make_db()
    for i in range(3):
        db.save_review(
            timestamp=f"2025-01-0{i+1}T12:00:00",
            repo="owner/repo",
            pr_number=i + 1,
            pr_url=f"https://github.com/owner/repo/pull/{i+1}",
            score=5.0 + i,
            total_issues=i,
            critical=0,
            warnings=i,
        )
    reviews = db.get_recent_reviews()
    assert len(reviews) == 3
    # Most recent first
    assert reviews[0]["pr_number"] == 3
    assert reviews[2]["pr_number"] == 1


def test_has_reviewed_commit():
    """Test commit deduplication check."""
    db = _make_db()
    db.save_review(
        timestamp="2025-01-01T12:00:00",
        repo="owner/repo",
        pr_number=1,
        pr_url="https://github.com/owner/repo/pull/1",
        score=9.0,
        total_issues=0,
        critical=0,
        warnings=0,
        commit_sha="abc123",
    )

    assert db.has_reviewed_commit("owner/repo", 1, "abc123") is True
    assert db.has_reviewed_commit("owner/repo", 1, "def456") is False
    assert db.has_reviewed_commit("other/repo", 1, "abc123") is False
    # Empty SHA should always return False
    assert db.has_reviewed_commit("owner/repo", 1, "") is False


def test_get_stats():
    """Test aggregate statistics."""
    db = _make_db()
    # Empty DB
    stats = db.get_stats()
    assert stats["total_reviews"] == 0
    assert stats["avg_score"] == 0

    # Add reviews
    for score in [8.0, 6.0, 10.0]:
        db.save_review(
            timestamp="2025-01-01T12:00:00",
            repo="owner/repo",
            pr_number=1,
            pr_url="url",
            score=score,
            total_issues=1,
            critical=0,
            warnings=1,
        )
    stats = db.get_stats()
    assert stats["total_reviews"] == 3
    assert stats["total_issues"] == 3
    assert stats["avg_score"] == 8.0  # (8 + 6 + 10) / 3


def test_limit_recent_reviews():
    """Test that limit parameter works."""
    db = _make_db()
    for i in range(10):
        db.save_review(
            timestamp=f"2025-01-01T{i:02d}:00:00",
            repo="owner/repo",
            pr_number=i,
            pr_url="url",
            score=5.0,
            total_issues=0,
            critical=0,
            warnings=0,
        )
    reviews = db.get_recent_reviews(limit=3)
    assert len(reviews) == 3
