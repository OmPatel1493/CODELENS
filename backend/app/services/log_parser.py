"""Parse a stack trace / error log into search signals.

We pull out the strongest hints a trace gives us — the exception type and message,
the files it names, and the functions in its frames — and build a natural-language
query for embedding. These signals also let bug localization *boost* files the trace
mentions directly and *explain* why each result was chosen.

Heuristic and language-agnostic on purpose: it recognizes common Python and
JS/TS trace shapes and falls back gracefully to the raw text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Path ending in a known code extension, e.g. app/auth.py or src/List.tsx
_FILE_RE = re.compile(r"[\w./\\-]+\.(?:py|js|jsx|ts|tsx|java|go|rb|rs|c|h|cpp|hpp|cs|php)\b")
# Python frame: File "app/auth.py", line 42, in authenticate_user
_PY_SYMBOL_RE = re.compile(r"\bin\s+([A-Za-z_]\w*)")
# JS/TS frame: at renderList (src/List.tsx:15:20)
_JS_SYMBOL_RE = re.compile(r"\bat\s+([A-Za-z_$][\w$.]*)\s*\(")
# Exception line: AttributeError: 'NoneType' ...  /  TypeError: Cannot read ...
_ERROR_RE = re.compile(r"^\s*([A-Za-z_][\w.]*(?:Error|Exception|Warning))\b:?\s*(.*)$")


@dataclass
class ParsedLog:
    error_type: str | None = None
    message: str | None = None
    files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    query_text: str = ""


def _dedupe(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _basename(path: str) -> str:
    return re.split(r"[/\\]", path)[-1]


def parse_log(text: str) -> ParsedLog:
    lines = text.splitlines()

    files = _dedupe(_FILE_RE.findall(text))
    symbols = _dedupe(
        [m for line in lines for m in _PY_SYMBOL_RE.findall(line)]
        + [m for line in lines for m in _JS_SYMBOL_RE.findall(line)]
    )
    # Common noise words that `in`/`at` can capture but aren't symbols.
    symbols = [s for s in symbols if s not in {"module", "the", "a"}]

    error_type: str | None = None
    message: str | None = None
    # Prefer the last exception line (Python puts it last; JS usually first — last
    # is still a fine choice when both appear).
    for line in lines:
        match = _ERROR_RE.match(line)
        if match:
            error_type, message = match.group(1), match.group(2).strip() or None

    # Build the query from the most informative parts, in priority order.
    parts: list[str] = []
    if message:
        parts.append(message)
    parts.extend(symbols)
    parts.extend(_basename(f).rsplit(".", 1)[0] for f in files)
    query_text = " ".join(parts).strip() or text.strip()[:500]

    return ParsedLog(
        error_type=error_type,
        message=message,
        files=files,
        symbols=symbols,
        query_text=query_text,
    )
