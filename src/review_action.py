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

    if not full_name or "/" not in full_name:
        logger.error(f"Invalid repository full_name: '{full_name}'")
        return

    owner, repo_name = full_name.split("/", 1)

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
