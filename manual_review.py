"""
Manual Review Script
This script demonstrates the AI Code Review Agent by running a review on a local sample diff file.
It simulates what happens when a Pull Request is opened, but runs entirely locally.
"""

import asyncio
import os
from src.diff_parser import parse_diff
from src.llm_reviewer import LLMReviewer
from src.comment_formatter import format_summary_comment, format_inline_comments

async def main():
    print("🚀 Starting Manual AI Code Review...")
    
    # 1. Read the sample diff file
    diff_path = "examples/sample_diff.patch"
    if not os.path.exists(diff_path):
        print(f"❌ Error: {diff_path} not found.")
        return

    print(f"📖 Reading diff from {diff_path}...")
    with open(diff_path, "r") as f:
        raw_diff = f.read()

    # 2. Parse the diff
    print("🔍 Parsing diff...")
    chunks = parse_diff(raw_diff)
    print(f"   Found {len(chunks)} chunks to review.")

    # 3. Initialize LLM Reviewer
    # Note: This requires GROQ_API_KEY to be set in .env
    print("🤖 Initializing LLM Reviewer (Groq)...")
    try:
        reviewer = LLMReviewer()
    except Exception as e:
        print(f"❌ Error initializing reviewer: {e}")
        print("   Make sure GROQ_API_KEY is set in your .env file")
        return

    # 4. Run the review
    print("🧠 Analyzing code with AI... (this may take a few seconds)")
    try:
        review = reviewer.review_pr(chunks)
    except Exception as e:
        print(f"❌ Error during review: {e}")
        return

    # 5. Display Results
    print("\n" + "="*50)
    print("✅ REVIEW COMPLETE")
    print("="*50 + "\n")

    # Mock PR details for formatting
    review.pr_number = 123
    review.repo_full_name = "test/repo"

    # Print Summary
    print(format_summary_comment(review))
    
    print("\n" + "-"*50)
    print("📝 INLINE COMMENTS GENERATED:")
    print("-" * 50)
    
    comments = format_inline_comments(review)
    for i, comment in enumerate(comments, 1):
        print(f"\n[Comment #{i}] File: {comment['path']} (Line {comment['line']})")
        print(f"Body: \n{comment['body']}")

if __name__ == "__main__":
    asyncio.run(main())
