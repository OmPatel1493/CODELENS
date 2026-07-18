"""Parse source files into semantic chunks with tree-sitter.

We extract function- and class-like definitions (language-aware) so search can
return a specific function rather than a whole file. Anything we can't parse — an
unsupported language, a parse failure, or a file with no top-level definitions —
falls back to a single whole-file chunk so no code is silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.code_chunk import ChunkKind

# File extension → tree-sitter-language-pack language name.
EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".php": "php",
}

# A matching node is a definition if its type ends with one of these...
_DEF_SUFFIXES = ("_definition", "_declaration", "_item")
# ...and we classify it by these substrings.
_FUNC_HINTS = ("function", "method", "constructor")
_CLASS_HINTS = ("class", "struct", "interface", "impl", "enum", "module")
_NAME_CHILD_TYPES = {"identifier", "type_identifier", "field_identifier", "name", "constant"}


@dataclass
class ParsedChunk:
    kind: ChunkKind
    symbol_name: str | None
    start_line: int
    end_line: int
    content: str


def _classify(node_type: str) -> ChunkKind | None:
    if not node_type.endswith(_DEF_SUFFIXES):
        return None
    lowered = node_type.lower()
    if any(hint in lowered for hint in _FUNC_HINTS):
        return ChunkKind.function
    if any(hint in lowered for hint in _CLASS_HINTS):
        return ChunkKind.class_
    return None


def _symbol_name(node, source: bytes) -> str | None:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        for child in node.children:
            if child.type in _NAME_CHILD_TYPES:
                name_node = child
                break
    if name_node is None:
        return None
    return source[name_node.start_byte : name_node.end_byte].decode("utf-8", "replace")


def _whole_file_chunk(content: str) -> ParsedChunk:
    return ParsedChunk(
        kind=ChunkKind.file,
        symbol_name=None,
        start_line=1,
        end_line=content.count("\n") + 1,
        content=content,
    )


def chunk_file(file_path: str, content: str) -> list[ParsedChunk]:
    """Return the semantic chunks for one file (never empty)."""
    ext = "." + file_path.rsplit(".", 1)[-1] if "." in file_path else ""
    lang = EXT_TO_LANG.get(ext)
    if lang is None:
        return [_whole_file_chunk(content)]

    try:
        from tree_sitter_language_pack import get_parser

        parser = get_parser(lang)
        source = content.encode("utf-8")
        tree = parser.parse(source)
    except Exception:
        # Grammar missing or parse error — don't lose the file.
        return [_whole_file_chunk(content)]

    chunks: list[ParsedChunk] = []
    # Iterative pre-order walk so we also capture methods nested in classes.
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        kind = _classify(node.type)
        if kind is not None:
            chunks.append(
                ParsedChunk(
                    kind=kind,
                    symbol_name=_symbol_name(node, source),
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    content=source[node.start_byte : node.end_byte].decode("utf-8", "replace"),
                )
            )
        stack.extend(node.children)

    return chunks or [_whole_file_chunk(content)]
