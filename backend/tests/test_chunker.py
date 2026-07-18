"""Chunker tests — real tree-sitter parsing (fast, no ML deps)."""

from app.models.code_chunk import ChunkKind
from app.services.chunker import chunk_file

PYTHON_SRC = """\
class Greeter:
    def hello(self, name):
        return f"hi {name}"


def top_level():
    return 1
"""


def test_extracts_python_functions_and_classes():
    chunks = chunk_file("app/x.py", PYTHON_SRC)
    kinds = {c.kind for c in chunks}
    names = {c.symbol_name for c in chunks}
    assert ChunkKind.class_ in kinds
    assert ChunkKind.function in kinds
    assert "Greeter" in names
    assert "top_level" in names


def test_line_ranges_are_populated():
    chunks = chunk_file("app/x.py", PYTHON_SRC)
    top = next(c for c in chunks if c.symbol_name == "top_level")
    assert top.start_line > 0 and top.end_line >= top.start_line


def test_unsupported_extension_falls_back_to_whole_file():
    chunks = chunk_file("notes.txt", "just text\nmore text")
    assert len(chunks) == 1
    assert chunks[0].kind is ChunkKind.file
