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

    in_hunk = False  # Track whether we're inside a hunk

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
            in_hunk = False

        # Skip file-level headers (index, ---, +++ lines before hunks)
        elif line.startswith("index ") or line.startswith("--- ") or line.startswith("+++ "):
            continue

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
            in_hunk = True

        elif current_file and in_hunk:
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
