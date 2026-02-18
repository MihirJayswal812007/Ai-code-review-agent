"""FastAPI webhook server for GitHub PR events."""

import hashlib
import hmac
import logging
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from time import time as monotonic_time

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse

from src.config import get_settings
from src.github_client import GitHubClient
from src.diff_parser import parse_diff
from src.llm_reviewer import LLMReviewer
from src.comment_formatter import format_summary_comment, format_inline_comments
from src.db import ReviewDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

github_client: GitHubClient | None = None
review_db: ReviewDatabase | None = None

# Simple rate limiter: timestamps of recent reviews
_review_timestamps: deque[float] = deque(maxlen=10)
MAX_REVIEWS_PER_MINUTE = 10


@asynccontextmanager
async def lifespan(app: FastAPI):
    global github_client, review_db
    github_client = GitHubClient()
    review_db = ReviewDatabase()
    logger.info("AI Code Review Agent started ✅")
    logger.info(f"Dashboard DB: {review_db.db_path}")
    yield
    if github_client:
        await github_client.close()


app = FastAPI(
    title="AI Code Review Agent",
    description="Automated PR code review powered by LLMs",
    version="1.1.0",
    lifespan=lifespan,
    redoc_url="/redoc",
    docs_url="/docs",
)


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    expected = "sha256=" + hmac.HMAC(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _is_rate_limited() -> bool:
    """Check if we've exceeded the review rate limit."""
    now = monotonic_time()
    # Remove timestamps older than 60 seconds
    while _review_timestamps and now - _review_timestamps[0] > 60:
        _review_timestamps.popleft()
    return len(_review_timestamps) >= MAX_REVIEWS_PER_MINUTE


@app.get("/")
async def root():
    """Welcome page with links to all endpoints."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Code Review Agent</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                   max-width: 800px; margin: 50px auto; padding: 20px; background: #0d1117; color: #c9d1d9; }
            h1 { color: #58a6ff; }
            a { color: #58a6ff; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .endpoint { background: #161b22; border: 1px solid #30363d; border-radius: 6px; 
                        padding: 15px; margin: 15px 0; }
            .method { background: #238636; color: white; padding: 4px 8px; border-radius: 4px; 
                     font-size: 12px; font-weight: bold; }
            .method.post { background: #1f6feb; }
            code { background: #161b22; padding: 2px 6px; border-radius: 3px; color: #79c0ff; }
        </style>
    </head>
    <body>
        <h1>🤖 AI Code Review Agent</h1>
        <p>Automated PR code review powered by LLMs (Groq)</p>
        
        <h2>Available Endpoints</h2>
        
        <div class="endpoint">
            <p><span class="method">GET</span> <a href="/health">/health</a></p>
            <p>Health check endpoint - returns service status</p>
        </div>
        
        <div class="endpoint">
            <p><span class="method post">POST</span> /webhook</p>
            <p>GitHub webhook receiver - handles PR events (opened, synchronize, reopened)</p>
            <p>Configure this URL in your GitHub repository settings</p>
        </div>
        
        <h2>API Documentation</h2>
        <div class="endpoint">
            <p>📊 <a href="/dashboard">Review Dashboard</a> - View recent reviews in real-time</p>
            <p>📚 <a href="/docs">Interactive API Docs (Swagger UI)</a></p>
            <p>📖 <a href="/redoc">API Reference (ReDoc)</a></p>
        </div>
        
        <h2>Quick Start</h2>
        <ol>
            <li>Set <code>GROQ_API_KEY</code> and <code>GITHUB_TOKEN</code> in your <code>.env</code> file</li>
            <li>Configure webhook URL in GitHub repo settings: <code>https://your-domain.com/webhook</code></li>
            <li>Open a pull request and watch the AI review appear! 🚀</li>
        </ol>
        
        <p style="margin-top: 40px; color: #8b949e; font-size: 14px;">
            Powered by FastAPI • Groq LLM
        </p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-code-review-agent"}


@app.get("/dashboard")
async def dashboard():
    """Web dashboard showing recent reviews (persisted in SQLite)."""
    reviews = review_db.get_recent_reviews(limit=50)
    stats = review_db.get_stats()

    # Generate table rows
    rows = ""
    if not reviews:
        rows = "<tr><td colspan='6' style='text-align: center; color: #8b949e;'>No reviews yet. Create a PR to see reviews here!</td></tr>"
    else:
        for review in reviews:
            score = review["score"]
            score_color = "#238636" if score >= 7 else "#d29922" if score >= 4 else "#da3633"
            ts = review["timestamp"]
            time_display = ts.split("T")[1].split(".")[0] if "T" in ts else ts
            rows += f"""
            <tr>
                <td>{time_display}</td>
                <td><a href="{review['pr_url']}" target="_blank">{review['repo']}#{review['pr_number']}</a></td>
                <td style="color: {score_color}; font-weight: bold;">{score}/10</td>
                <td>{review['total_issues']}</td>
                <td style="color: #da3633;">{review['critical']}</td>
                <td style="color: #d29922;">{review['warnings']}</td>
            </tr>
            """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Code Review Dashboard</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                   max-width: 1200px; margin: 30px auto; padding: 20px; background: #0d1117; color: #c9d1d9; }}
            h1 {{ color: #58a6ff; }}
            a {{ color: #58a6ff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #30363d; }}
            th {{ background: #161b22; color: #8b949e; font-weight: 600; }}
            tr:hover {{ background: #161b22; }}
            .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
            .stat-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; 
                         padding: 15px; flex: 1; }}
            .stat-value {{ font-size: 32px; font-weight: bold; color: #58a6ff; }}
            .stat-label {{ color: #8b949e; margin-top: 5px; }}
        </style>
    </head>
    <body>
       <h1>🤖 AI Code Review Dashboard</h1>
        <p>Real-time view of recent code reviews • Auto-refreshes every 30 seconds</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{stats['total_reviews']}</div>
                <div class="stat-label">Total Reviews</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['total_issues']}</div>
                <div class="stat-label">Issues Found</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['avg_score']}</div>
                <div class="stat-label">Average Score</div>
            </div>
        </div>
        
        <h2>Recent Reviews</h2>
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Pull Request</th>
                    <th>Score</th>
                    <th>Total Issues</th>
                    <th>Critical</th>
                    <th>Warnings</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        
        <p style="margin-top: 40px; color: #8b949e; font-size: 14px;">
            <a href="/">← Back to home</a> | 
            <a href="/docs">API Docs</a> | 
            <a href="/health">Health Check</a>
        </p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle incoming GitHub webhook events."""
    settings = get_settings()

    # Verify webhook signature
    body = await request.body()
    if settings.github_webhook_secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(body, signature, settings.github_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid signature")
    else:
        logger.warning(
            "⚠️ GITHUB_WEBHOOK_SECRET not set — skipping signature verification. "
            "Set it in .env for production use."
        )

    payload = await request.json()
    event = request.headers.get("X-GitHub-Event", "")

    if event != "pull_request":
        return {"status": "ignored", "reason": f"Event type: {event}"}

    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "ignored", "reason": f"Action: {action}"}

    # Rate limiting
    if _is_rate_limited():
        logger.warning("Rate limit exceeded, skipping review")
        return {"status": "rate_limited", "reason": "Too many reviews per minute"}
    _review_timestamps.append(monotonic_time())

    # Extract PR info
    pr = payload["pull_request"]
    repo = payload["repository"]
    pr_number = pr["number"]
    commit_sha = pr.get("head", {}).get("sha", "")
    full_name = repo["full_name"]
    if "/" not in full_name:
        raise HTTPException(status_code=400, detail=f"Invalid repository name: {full_name}")
    owner, repo_name = full_name.split("/", 1)

    # Deduplication: skip if this exact commit was already reviewed
    if review_db and review_db.has_reviewed_commit(full_name, pr_number, commit_sha):
        logger.info(f"Skipping PR #{pr_number} — commit {commit_sha[:8]} already reviewed")
        return {"status": "already_reviewed", "commit": commit_sha[:8]}

    logger.info(f"Reviewing PR #{pr_number} on {owner}/{repo_name} (commit {commit_sha[:8]})")

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
            review_event = (
                "REQUEST_CHANGES" if review.critical_count > 0 else "COMMENT"
            )
            await github_client.create_review(
                owner, repo_name, pr_number, summary, inline_comments, review_event
            )
        else:
            await github_client.post_comment(owner, repo_name, pr_number, summary)

        logger.info(
            f"Review posted for PR #{pr_number}: "
            f"{review.total_issues} issues, score {review.overall_score}/10"
        )

        # 5. Persist review to SQLite
        if review_db:
            review_db.save_review(
                timestamp=datetime.now().isoformat(),
                repo=review.repo_full_name,
                pr_number=pr_number,
                pr_url=f"https://github.com/{review.repo_full_name}/pull/{pr_number}",
                score=review.overall_score,
                total_issues=review.total_issues,
                critical=review.critical_count,
                warnings=review.warning_count,
                commit_sha=commit_sha,
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
