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
    expected = "sha256=" + hmac.HMAC(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.get("/")
async def root():
    """Welcome page with links to all endpoints."""
    from fastapi.responses import HTMLResponse
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
            Powered by FastAPI • Groq LLM • Tree-sitter
        </p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


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
    full_name = repo["full_name"]
    if "/" not in full_name:
        raise HTTPException(status_code=400, detail=f"Invalid repository name: {full_name}")
    owner, repo_name = full_name.split("/", 1)

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
