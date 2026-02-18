"""Tests for diff_parser module."""

from src.diff_parser import parse_diff, detect_language, _build_chunk


def test_detect_language():
    """Test language detection from file extensions."""
    assert detect_language("app.py") == "python"
    assert detect_language("main.js") == "javascript"
    assert detect_language("component.tsx") == "typescript"
    assert detect_language("Main.java") == "java"
    assert detect_language("unknown.xyz") == "unknown"


def test_parse_simple_diff(sample_python_diff):
    """Test parsing a simple unified diff."""
    chunks = parse_diff(sample_python_diff)
    
    assert len(chunks) > 0
    chunk = chunks[0]
    assert chunk.file_path == "app.py"
    assert chunk.language == "python"
    assert len(chunk.added_lines) > 0
    assert len(chunk.removed_lines) > 0


def test_parse_empty_diff():
    """Test parsing an empty diff."""
    chunks = parse_diff("")
    assert len(chunks) == 0


def test_parse_diff_with_language_filter():
    """Test filtering diffs by supported languages."""
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,1 +1,1 @@
-old
+new
diff --git a/test.rb b/test.rb
--- a/test.rb
+++ b/test.rb
@@ -1,1 +1,1 @@
-old
+new
"""
    chunks = parse_diff(diff, supported_languages=["python"])
    assert len(chunks) == 1
    assert chunks[0].language == "python"


def test_build_chunk():
    """Test building a DiffChunk from raw lines."""
    lines = [
        "@@ -10,3 +10,3 @@",
        " context",
        "-removed",
        "+added",
    ]
    chunk = _build_chunk("test.py", 10, 10, lines)
    
    assert chunk is not None
    assert chunk.file_path == "test.py"
    assert chunk.language == "python"
    assert "added" in chunk.added_lines
    assert "removed" in chunk.removed_lines
    assert "context" in chunk.context_lines
