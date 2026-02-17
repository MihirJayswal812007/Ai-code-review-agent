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
