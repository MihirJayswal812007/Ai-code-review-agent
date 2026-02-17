# 🔍 AI Code Review Agent — Complete Build Pipeline for Claude Sonnet

> **Instructions for Claude Sonnet**: Follow each phase sequentially. Complete every file and step before moving to the next phase. Every code block is production-ready — implement exactly as shown.

---

## 📌 Project Overview

**What**: A GitHub App/Action that auto-reviews PRs using LLMs — detects bugs, suggests fixes, checks style, rates quality, and posts inline comments.

**Tech Stack**: Python 3.11+ · FastAPI · GitHub API · Groq LLM (free) · tree-sitter · Docker

**Cost**: $0 (Groq free tier)

---

## PHASE 0: Project Scaffolding (Step 1 of 7)

### Step 0.1 — Create directory structure

```
ai-code-review-agent/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── code-review.yml          # GitHub Action workflow
├── src/
│   ├── __init__.py
│   ├── app.py                       # FastAPI webhook server
│   ├── github_client.py             # GitHub API wrapper
│   ├── diff_parser.py               # Parse PR diffs into chunks
│   ├── code_analyzer.py             # tree-sitter AST analysis
│   ├── llm_reviewer.py              # LLM prompt + review logic
│   ├── comment_formatter.py         # Format reviews as GitHub markdown
│   ├── models.py                    # Pydantic models
│   └── config.py                    # Settings & env vars
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_diff_parser.py
│   ├── test_code_analyzer.py
│   ├── test_llm_reviewer.py
│   └── test_comment_formatter.py
├── examples/
│   └── sample_diff.patch
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── setup.py
├── README.md
├── LICENSE
└── action.yml                       # GitHub Action definition
```

### Step 0.2 — Create `requirements.txt`

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
httpx==0.27.0
pydantic==2.9.0
pydantic-settings==2.5.0
python-dotenv==1.0.1
PyGithub==2.4.0
groq==0.11.0
tree-sitter==0.23.0
tree-sitter-python==0.23.0
tree-sitter-javascript==0.23.0
tree-sitter-typescript==0.23.0
cryptography==43.0.0
pyjwt==2.9.0
```

### Step 0.3 — Create `requirements-dev.txt`

```txt
-r requirements.txt
pytest==8.3.0
pytest-asyncio==0.24.0
pytest-cov==5.0.0
httpx==0.27.0
ruff==0.6.0
mypy==1.11.0
pre-commit==3.8.0
```

### Step 0.4 — Create `.env.example`

```env
# LLM Provider
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile

# GitHub App (choose ONE auth method)
# Method 1: GitHub App
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY_PATH=
GITHUB_WEBHOOK_SECRET=

# Method 2: Personal Access Token (simpler, for testing)
GITHUB_TOKEN=your_github_pat_here

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info

# Review Settings
MAX_FILES_PER_REVIEW=20
MAX_DIFF_LINES=500
REVIEW_LANGUAGES=python,javascript,typescript,java
```

### Step 0.5 — Create `.gitignore`

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.env
.venv/
venv/
*.log
.mypy_cache/
.pytest_cache/
.ruff_cache/
```

### Step 0.6 — Create `LICENSE` (MIT)

Use standard MIT License with current year and author name.

---

## PHASE 1: Core Configuration & Models (Step 2 of 7)

### Step 1.1 — Create `src/config.py`

```python
"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # LLM
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    llm_model: str = Field("llama-3.3-70b-versatile", env="LLM_MODEL")

    # GitHub — support both App and PAT auth
    github_token: Optional[str] = Field(None, env="GITHUB_TOKEN")
    github_app_id: Optional[str] = Field(None, env="GITHUB_APP_ID")
    github_private_key_path: Optional[str] = Field(None, env="GITHUB_PRIVATE_KEY_PATH")
    github_webhook_secret: Optional[str] = Field(None, env="GITHUB_WEBHOOK_SECRET")

    # Server
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    log_level: str = Field("info", env="LOG_LEVEL")

    # Review limits
    max_files_per_review: int = Field(20, env="MAX_FILES_PER_REVIEW")
    max_diff_lines: int = Field(500, env="MAX_DIFF_LINES")
    review_languages: str = Field(
        "python,javascript,typescript,java",
        env="REVIEW_LANGUAGES"
    )

    @property
    def supported_languages(self) -> list[str]:
        return [lang.strip() for lang in self.review_languages.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
```

### Step 1.2 — Create `src/models.py`

```python
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
```

---

## PHASE 2: GitHub Integration (Step 3 of 7)

### Step 2.1 — Create `src/github_client.py`

Implement a class `GitHubClient` with these methods:

```python
"""GitHub API client for PR interactions."""

import httpx
import logging
from typing import Optional
from src.config import get_settings

logger = logging.getLogger(__name__)


class GitHubClient:
    """Handles all GitHub API interactions."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        settings = get_settings()
        self.token = token or settings.github_token
        if not self.token:
            raise ValueError("GitHub token is required")
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=self.headers,
            timeout=30.0,
        )

    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Fetch the raw diff of a pull request."""
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        response = await self.client.get(
            f"/repos/{owner}/{repo}/pulls/{pr_number}",
            headers=headers,
        )
        response.raise_for_status()
        return response.text

    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        """Get list of files changed in a PR."""
        response = await self.client.get(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
        )
        response.raise_for_status()
        return response.json()

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str
    ) -> str:
        """Get full file content at a specific ref/branch."""
        response = await self.client.get(
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
        )
        response.raise_for_status()
        import base64
        data = response.json()
        return base64.b64decode(data["content"]).decode("utf-8")

    async def create_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        comments: list[dict],
        event: str = "COMMENT",  # APPROVE, REQUEST_CHANGES, COMMENT
    ) -> dict:
        """Submit a PR review with inline comments."""
        payload = {
            "body": body,
            "event": event,
            "comments": comments,  # [{path, position/line, body}, ...]
        }
        response = await self.client.post(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def post_comment(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> dict:
        """Post a top-level comment on a PR."""
        response = await self.client.post(
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            json={"body": body},
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()
```

---

## PHASE 3: Diff Parser (Step 4 of 7)

### Step 3.1 — Create `src/diff_parser.py`

```python
"""Parse unified diffs into structured chunks for review."""

import re
import logging
from pathlib import Path
from src.models import DiffChunk

logger = logging.getLogger(__name__)

# Map file extensions to language names
EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
}

HUNK_HEADER_RE = re.compile(
    r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@"
)


def detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    ext = Path(file_path).suffix.lower()
    return EXTENSION_MAP.get(ext, "unknown")


def parse_diff(raw_diff: str, supported_languages: list[str] | None = None) -> list[DiffChunk]:
    """
    Parse a unified diff string into a list of DiffChunk objects.

    Args:
        raw_diff: The raw unified diff text from GitHub API
        supported_languages: Only include files with these languages (None = all)

    Returns:
        List of DiffChunk objects ready for review
    """
    chunks: list[DiffChunk] = []
    current_file = None
    current_hunks: list[str] = []
    hunk_old_start = 0
    hunk_new_start = 0

    for line in raw_diff.split("\n"):
        # Detect file header
        if line.startswith("diff --git"):
            # Save previous hunk if exists
            if current_file and current_hunks:
                chunk = _build_chunk(
                    current_file, hunk_old_start, hunk_new_start, current_hunks
                )
                if chunk and (
                    supported_languages is None
                    or chunk.language in supported_languages
                ):
                    chunks.append(chunk)
                current_hunks = []

            # Extract file path — handle "a/path" and "b/path"
            parts = line.split(" b/")
            current_file = parts[-1] if len(parts) > 1 else None

        # Detect hunk header
        elif line.startswith("@@"):
            # Save previous hunk
            if current_file and current_hunks:
                chunk = _build_chunk(
                    current_file, hunk_old_start, hunk_new_start, current_hunks
                )
                if chunk and (
                    supported_languages is None
                    or chunk.language in supported_languages
                ):
                    chunks.append(chunk)
                current_hunks = []

            match = HUNK_HEADER_RE.match(line)
            if match:
                hunk_old_start = int(match.group(1))
                hunk_new_start = int(match.group(2))
            current_hunks.append(line)

        elif current_file and current_hunks:
            current_hunks.append(line)

    # Don't forget the last hunk
    if current_file and current_hunks:
        chunk = _build_chunk(
            current_file, hunk_old_start, hunk_new_start, current_hunks
        )
        if chunk and (
            supported_languages is None or chunk.language in supported_languages
        ):
            chunks.append(chunk)

    logger.info(f"Parsed {len(chunks)} diff chunks from diff")
    return chunks


def _build_chunk(
    file_path: str,
    old_start: int,
    new_start: int,
    lines: list[str],
) -> DiffChunk | None:
    """Build a DiffChunk from raw lines."""
    if not file_path:
        return None

    content = "\n".join(lines)
    added = [l[1:] for l in lines if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:] for l in lines if l.startswith("-") and not l.startswith("---")]
    context = [l[1:] for l in lines if l.startswith(" ")]

    return DiffChunk(
        file_path=file_path,
        language=detect_language(file_path),
        old_start=old_start,
        new_start=new_start,
        content=content,
        added_lines=added,
        removed_lines=removed,
        context_lines=context,
    )
```

---

## PHASE 4: LLM Review Engine (Step 5 of 7)

### Step 4.1 — Create `src/llm_reviewer.py`

This is the **core brain** of the application.

```python
"""LLM-powered code review engine using Groq."""

import json
import logging
from groq import Groq
from src.config import get_settings
from src.models import DiffChunk, ReviewIssue, FileReview, PRReview, Severity

logger = logging.getLogger(__name__)

REVIEW_SYSTEM_PROMPT = """You are an expert senior software engineer performing a code review.
Analyze the provided code diff and identify issues in these categories:
- **bug**: Logic errors, null pointer risks, off-by-one errors, race conditions
- **security**: SQL injection, XSS, hardcoded secrets, insecure deserialization
- **performance**: N+1 queries, unnecessary loops, memory leaks, blocking calls
- **style**: Naming conventions, code organization, readability
- **best-practice**: Error handling, type safety, documentation, testing

For EACH issue found, respond with a JSON array of objects:
{
  "issues": [
    {
      "line_start": <int>,
      "line_end": <int>,
      "severity": "critical|warning|info|style",
      "category": "bug|security|performance|style|best-practice",
      "title": "<short title>",
      "description": "<detailed explanation of the problem>",
      "suggestion": "<suggested fix as code, or null>"
    }
  ],
  "summary": "<2-3 sentence summary of the file quality>",
  "score": <float 0-10>
}

Rules:
- Only flag REAL issues, not nitpicks on working code
- Be specific — reference exact line numbers from the diff
- Provide actionable suggestions with code when possible
- If the code looks good, return an empty issues array with a positive summary
- Respond ONLY with valid JSON, no markdown fences
"""


class LLMReviewer:
    """Reviews code diffs using Groq LLM."""

    def __init__(self):
        settings = get_settings()
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.llm_model

    def review_chunk(self, chunk: DiffChunk) -> FileReview:
        """Review a single diff chunk and return structured feedback."""
        user_prompt = (
            f"Review this {chunk.language} code diff from `{chunk.file_path}`:\n\n"
            f"```diff\n{chunk.content}\n```\n\n"
            f"The diff starts at line {chunk.new_start} in the new file."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            issues = [
                ReviewIssue(
                    file_path=chunk.file_path,
                    line_start=issue.get("line_start", chunk.new_start),
                    line_end=issue.get("line_end", chunk.new_start),
                    severity=Severity(issue.get("severity", "info")),
                    category=issue.get("category", "style"),
                    title=issue.get("title", "Issue found"),
                    description=issue.get("description", ""),
                    suggestion=issue.get("suggestion"),
                    confidence=0.85,
                )
                for issue in result.get("issues", [])
            ]

            return FileReview(
                file_path=chunk.file_path,
                language=chunk.language,
                issues=issues,
                summary=result.get("summary", ""),
            )

        except Exception as e:
            logger.error(f"LLM review failed for {chunk.file_path}: {e}")
            return FileReview(
                file_path=chunk.file_path,
                language=chunk.language,
                issues=[],
                summary=f"Review failed: {str(e)}",
            )

    def review_pr(self, chunks: list[DiffChunk]) -> PRReview:
        """Review all chunks in a PR."""
        file_reviews = []
        for chunk in chunks:
            review = self.review_chunk(chunk)
            file_reviews.append(review)

        # Aggregate stats
        all_issues = [i for fr in file_reviews for i in fr.issues]
        critical = sum(1 for i in all_issues if i.severity == Severity.CRITICAL)
        warnings = sum(1 for i in all_issues if i.severity == Severity.WARNING)

        # Calculate overall score (start at 10, deduct per issue)
        score = max(0.0, 10.0 - (critical * 2.0) - (warnings * 0.5) - (len(all_issues) * 0.1))

        return PRReview(
            pr_number=0,
            repo_full_name="",
            file_reviews=file_reviews,
            overall_score=round(score, 1),
            summary=self._generate_summary(file_reviews, score),
            total_issues=len(all_issues),
            critical_count=critical,
            warning_count=warnings,
        )

    def _generate_summary(self, reviews: list[FileReview], score: float) -> str:
        """Generate an overall PR summary."""
        total = sum(len(r.issues) for r in reviews)
        if total == 0:
            return "✅ No issues found. Code looks clean and well-written!"
        return (
            f"Found **{total} issue(s)** across {len(reviews)} file(s). "
            f"Overall quality score: **{score}/10**."
        )
```

---

## PHASE 5: Comment Formatter & FastAPI App (Step 6 of 7)

### Step 5.1 — Create `src/comment_formatter.py`

```python
"""Format review results as GitHub-compatible markdown."""

from src.models import PRReview, ReviewIssue, Severity

SEVERITY_EMOJI = {
    Severity.CRITICAL: "🔴",
    Severity.WARNING: "🟡",
    Severity.INFO: "🔵",
    Severity.STYLE: "⚪",
}


def format_summary_comment(review: PRReview) -> str:
    """Format the top-level summary comment for a PR."""
    score_bar = "🟢" * int(review.overall_score) + "⚫" * (10 - int(review.overall_score))

    lines = [
        "## 🤖 AI Code Review Summary\n",
        f"**Quality Score**: {review.overall_score}/10 {score_bar}\n",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total Issues | {review.total_issues} |",
        f"| 🔴 Critical | {review.critical_count} |",
        f"| 🟡 Warnings | {review.warning_count} |",
        f"| Files Reviewed | {len(review.file_reviews)} |\n",
    ]

    if review.summary:
        lines.append(f"\n**Summary**: {review.summary}\n")

    # Per-file breakdown
    if review.file_reviews:
        lines.append("\n### 📁 File Breakdown\n")
        for fr in review.file_reviews:
            issue_count = len(fr.issues)
            status = "✅" if issue_count == 0 else f"⚠️ {issue_count} issue(s)"
            lines.append(f"- `{fr.file_path}` — {status}")

    lines.append("\n---\n*Powered by AI Code Review Agent* 🤖")
    return "\n".join(lines)


def format_inline_comments(review: PRReview) -> list[dict]:
    """Format issues as GitHub inline review comments."""
    comments = []
    for fr in review.file_reviews:
        for issue in fr.issues:
            body = _format_issue_comment(issue)
            comments.append({
                "path": issue.file_path,
                "line": issue.line_end,
                "body": body,
            })
    return comments


def _format_issue_comment(issue: ReviewIssue) -> str:
    """Format a single issue as a markdown comment."""
    emoji = SEVERITY_EMOJI.get(issue.severity, "🔵")
    lines = [
        f"{emoji} **{issue.severity.value.upper()}** — {issue.title}\n",
        f"**Category**: {issue.category}\n",
        issue.description,
    ]
    if issue.suggestion:
        lines.append(f"\n**Suggested fix**:\n```\n{issue.suggestion}\n```")
    return "\n".join(lines)
```

### Step 5.2 — Create `src/app.py`

```python
"""FastAPI webhook server for GitHub PR events."""

import hashlib
import hmac
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from src.config import get_settings
from src.github_client import GitHubClient
from src.diff_parser import parse_diff
from src.llm_reviewer import LLMReviewer
from src.comment_formatter import format_summary_comment, format_inline_comments

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

github_client: GitHubClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global github_client
    github_client = GitHubClient()
    logger.info("AI Code Review Agent started ✅")
    yield
    if github_client:
        await github_client.close()


app = FastAPI(
    title="AI Code Review Agent",
    description="Automated PR code review powered by LLMs",
    version="1.0.0",
    lifespan=lifespan,
)


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-code-review-agent"}


@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle incoming GitHub webhook events."""
    settings = get_settings()

    # Verify signature if webhook secret is configured
    if settings.github_webhook_secret:
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(body, signature, settings.github_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event = request.headers.get("X-GitHub-Event", "")

    if event != "pull_request":
        return {"status": "ignored", "reason": f"Event type: {event}"}

    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "ignored", "reason": f"Action: {action}"}

    # Extract PR info
    pr = payload["pull_request"]
    repo = payload["repository"]
    pr_number = pr["number"]
    owner, repo_name = repo["full_name"].split("/")

    logger.info(f"Reviewing PR #{pr_number} on {owner}/{repo_name}")

    try:
        # 1. Fetch the diff
        raw_diff = await github_client.get_pr_diff(owner, repo_name, pr_number)

        # 2. Parse the diff
        chunks = parse_diff(raw_diff, settings.supported_languages)
        if not chunks:
            return {"status": "skipped", "reason": "No reviewable files"}

        # Limit files
        chunks = chunks[: settings.max_files_per_review]

        # 3. Run LLM review
        reviewer = LLMReviewer()
        review = reviewer.review_pr(chunks)
        review.pr_number = pr_number
        review.repo_full_name = repo["full_name"]

        # 4. Post results
        summary = format_summary_comment(review)
        inline_comments = format_inline_comments(review)

        if inline_comments:
            event_type = (
                "REQUEST_CHANGES" if review.critical_count > 0 else "COMMENT"
            )
            await github_client.create_review(
                owner, repo_name, pr_number, summary, inline_comments, event_type
            )
        else:
            await github_client.post_comment(owner, repo_name, pr_number, summary)

        logger.info(
            f"Review posted for PR #{pr_number}: "
            f"{review.total_issues} issues, score {review.overall_score}/10"
        )
        return {
            "status": "reviewed",
            "pr": pr_number,
            "issues": review.total_issues,
            "score": review.overall_score,
        }

    except Exception as e:
        logger.error(f"Review failed for PR #{pr_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
```

---

## PHASE 6: GitHub Action + Docker (Step 7 of 7)

### Step 6.1 — Create `action.yml` (GitHub Action definition)

```yaml
name: 'AI Code Review'
description: 'AI-powered code review that detects bugs, security issues, and suggests improvements'
author: 'Your Name'

inputs:
  groq_api_key:
    description: 'Groq API key for LLM access'
    required: true
  github_token:
    description: 'GitHub token for API access'
    required: true
    default: ${{ github.token }}
  model:
    description: 'LLM model to use'
    required: false
    default: 'llama-3.3-70b-versatile'
  max_files:
    description: 'Maximum files to review per PR'
    required: false
    default: '20'

runs:
  using: 'docker'
  image: 'Dockerfile'
  env:
    GROQ_API_KEY: ${{ inputs.groq_api_key }}
    GITHUB_TOKEN: ${{ inputs.github_token }}
    LLM_MODEL: ${{ inputs.model }}
    MAX_FILES_PER_REVIEW: ${{ inputs.max_files }}
```

### Step 6.2 — Create `.github/workflows/code-review.yml`

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run AI Code Review
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python -m src.review_action
```

### Step 6.3 — Create `src/review_action.py` (GitHub Action entry point)

```python
"""Entry point for GitHub Action mode — reads PR context from env."""

import os
import json
import logging
from src.github_client import GitHubClient
from src.diff_parser import parse_diff
from src.llm_reviewer import LLMReviewer
from src.comment_formatter import format_summary_comment, format_inline_comments
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # GitHub Actions provides these env vars automatically
    github_token = os.environ["GITHUB_TOKEN"]
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")

    if not event_path or not os.path.exists(event_path):
        logger.error("No GitHub event payload found")
        return

    with open(event_path) as f:
        event = json.load(f)

    pr = event.get("pull_request", {})
    repo = event.get("repository", {})
    pr_number = pr.get("number")
    full_name = repo.get("full_name", "")
    owner, repo_name = full_name.split("/")

    logger.info(f"🔍 Reviewing PR #{pr_number} on {full_name}")

    client = GitHubClient(token=github_token)

    try:
        raw_diff = await client.get_pr_diff(owner, repo_name, pr_number)
        chunks = parse_diff(raw_diff)

        max_files = int(os.environ.get("MAX_FILES_PER_REVIEW", 20))
        chunks = chunks[:max_files]

        if not chunks:
            logger.info("No reviewable changes found")
            return

        reviewer = LLMReviewer()
        review = reviewer.review_pr(chunks)
        review.pr_number = pr_number
        review.repo_full_name = full_name

        summary = format_summary_comment(review)
        inline_comments = format_inline_comments(review)

        if inline_comments:
            event_type = "REQUEST_CHANGES" if review.critical_count > 0 else "COMMENT"
            await client.create_review(
                owner, repo_name, pr_number, summary, inline_comments, event_type
            )
        else:
            await client.post_comment(owner, repo_name, pr_number, summary)

        logger.info(f"✅ Review complete: {review.total_issues} issues, score {review.overall_score}/10")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### Step 6.4 — Create `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# For webhook server mode:
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 6.5 — Create `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: pip install -r requirements-dev.txt
      - name: Lint
        run: ruff check src/ tests/
      - name: Test
        run: pytest tests/ -v --cov=src --cov-report=term-missing
```

### Step 6.6 — Create Tests

Create `tests/conftest.py`, `tests/test_diff_parser.py`, `tests/test_comment_formatter.py` with:

- **conftest.py**: Shared fixtures (sample diffs, sample review objects)
- **test_diff_parser.py**: Test `parse_diff()` with sample Python/JS diffs, edge cases (binary files, empty diffs, renames)
- **test_comment_formatter.py**: Test `format_summary_comment()` and `format_inline_comments()` produce valid markdown

### Step 6.7 — Create `README.md`

Include these sections:
1. **Hero banner** — project name + tagline + demo GIF
2. **Features** — bulleted list with emoji
3. **Quick Start** — 3-step setup (clone, env, run)
4. **Usage as GitHub Action** — YAML snippet users can copy
5. **Usage as Webhook Server** — Docker + ngrok instructions
6. **Configuration** — table of all env vars
7. **Architecture Diagram** — Mermaid flowchart: `PR Opened → Webhook → Diff Parser → LLM Review → GitHub Comments`
8. **Screenshots** — example review comments
9. **Contributing** — standard guidelines
10. **License** — MIT

---

## 🏗️ Build Order Checklist

Follow this exact order:

```
[ ] Phase 0: Scaffold project (dirs, requirements, .env, .gitignore, LICENSE)
[ ] Phase 1: src/config.py + src/models.py
[ ] Phase 2: src/github_client.py
[ ] Phase 3: src/diff_parser.py
[ ] Phase 4: src/llm_reviewer.py (THE CORE — spend the most time here)
[ ] Phase 5: src/comment_formatter.py + src/app.py
[ ] Phase 6: action.yml + review_action.py + Dockerfile + CI + tests + README
[ ] Final: Get a Groq API key, test on a real PR, record demo GIF
```

---

## 🧪 Testing Commands

```bash
# Install deps
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/

# Run webhook server locally
uvicorn src.app:app --reload

# Test with ngrok (expose local server)
ngrok http 8000
```

---

## 🔑 API Keys Needed (All Free)

| Key | Where to Get | Cost |
|-----|-------------|------|
| **Groq API Key** | [console.groq.com](https://console.groq.com) | Free (30 req/min) |
| **GitHub PAT** | GitHub → Settings → Developer Settings → Personal Access Tokens | Free |
| **ngrok** (optional) | [ngrok.com](https://ngrok.com) | Free tier available |
