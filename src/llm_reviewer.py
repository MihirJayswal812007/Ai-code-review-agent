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
