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

    # Add link to view full review on GitHub
    pr_url = f"https://github.com/{review.repo_full_name}/pull/{review.pr_number}"
    lines.append(f"\n[📋 View detailed review on GitHub]({pr_url}/files)")
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
