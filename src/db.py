"""SQLite-backed storage for review history."""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "reviews.db"


class ReviewDatabase:
    """Persistent storage for code review results using SQLite."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create the reviews table if it doesn't exist."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    repo TEXT NOT NULL,
                    pr_number INTEGER NOT NULL,
                    pr_url TEXT NOT NULL,
                    score REAL NOT NULL,
                    total_issues INTEGER NOT NULL DEFAULT 0,
                    critical INTEGER NOT NULL DEFAULT 0,
                    warnings INTEGER NOT NULL DEFAULT 0,
                    commit_sha TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reviews_repo_pr
                ON reviews (repo, pr_number)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reviews_commit
                ON reviews (commit_sha)
            """)

    def _connect(self) -> sqlite3.Connection:
        """Create a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def save_review(
        self,
        timestamp: str,
        repo: str,
        pr_number: int,
        pr_url: str,
        score: float,
        total_issues: int,
        critical: int,
        warnings: int,
        commit_sha: str = "",
    ) -> int:
        """Save a review to the database. Returns the row ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reviews
                    (timestamp, repo, pr_number, pr_url, score, total_issues, critical, warnings, commit_sha)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (timestamp, repo, pr_number, pr_url, score, total_issues, critical, warnings, commit_sha),
            )
            return cursor.lastrowid

    def get_recent_reviews(self, limit: int = 50) -> list[dict]:
        """Get the most recent reviews."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reviews ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def has_reviewed_commit(self, repo: str, pr_number: int, commit_sha: str) -> bool:
        """Check if a specific commit on a PR has already been reviewed."""
        if not commit_sha:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM reviews WHERE repo = ? AND pr_number = ? AND commit_sha = ? LIMIT 1",
                (repo, pr_number, commit_sha),
            ).fetchone()
            return row is not None

    def get_stats(self) -> dict:
        """Get aggregate statistics."""
        with self._connect() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_reviews,
                    COALESCE(SUM(total_issues), 0) as total_issues,
                    COALESCE(ROUND(AVG(score), 1), 0) as avg_score
                FROM reviews
            """).fetchone()
            return dict(row)
