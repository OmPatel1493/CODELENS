"""Build a module dependency graph from a repository's archived source.

Parses import statements per file and resolves intra-repo edges, so the frontend
can draw "which file imports which." Built on demand from the stored archive
(reusing the ingestion archive reader) — no schema change, no re-index.

Resolution is heuristic (suffix-matching on paths), which is robust to src-layouts
and good enough for a visualization; external/stdlib imports are ignored.
"""

from __future__ import annotations

import re

from app.core.config import settings
from app.models.repository import Repository, RepoSource
from app.services.indexing_service import _normalize_path, iter_archive_files
from app.services.storage import StorageBackend

_PY_EXTS = {".py"}
_JS_EXTS = {".js", ".jsx", ".ts", ".tsx"}

# Python: `import a.b`, `import a.b as c`, `from a.b import c`, `from . import x`
# Note: use [ \t] (not \s) in the names group so a match can't run past the line
# end and swallow the next import statement.
_PY_IMPORT = re.compile(r"^[ \t]*import[ \t]+([\w.]+)", re.MULTILINE)
_PY_FROM = re.compile(r"^[ \t]*from[ \t]+(\.*[\w.]*)[ \t]+import[ \t]+([\w*,\t ]+)", re.MULTILINE)
# JS/TS: `from '...'`, `import '...'`, `require('...')`
_JS_SPEC = re.compile(r"""(?:from|import|require\()\s*['"]([^'"]+)['"]""")

# Cap graph size so a huge repo stays legible in the browser.
_MAX_NODES = 80


def _ext(path: str) -> str:
    dot = path.rfind(".")
    return path[dot:].lower() if dot != -1 else ""


def _archive_ext(repo: Repository) -> str:
    return "zip" if repo.source is RepoSource.upload else "tar.gz"


def _py_targets(text: str) -> list[str]:
    """Dotted module names imported by a Python file (relative kept with leading dots)."""
    out: list[str] = []
    out += _PY_IMPORT.findall(text)
    for base, names in _PY_FROM.findall(text):
        if base.startswith("."):
            # relative: pair the dots with each imported name (submodule candidate)
            for n in names.split(","):
                n = n.strip().split(" as ")[0].strip()
                if n and n != "*":
                    out.append(base + n)
            out.append(base)  # also the package itself
        else:
            out.append(base)
    return out


def _resolve_py(target: str, cur_path: str, py_files: set[str]) -> str | None:
    """Resolve a Python import target to a repo file path via suffix matching."""
    if target.startswith("."):
        # relative import: walk up from the current file's directory
        dots = len(target) - len(target.lstrip("."))
        rest = target[dots:].replace(".", "/")
        parts = cur_path.split("/")[:-1]  # directory of current file
        up = parts[: len(parts) - (dots - 1)] if dots > 1 else parts
        frag = "/".join([*up, rest]).strip("/")
        candidates = (
            [f"{frag}.py", f"{frag}/__init__.py"] if rest else [f"{'/'.join(up)}/__init__.py"]
        )
    else:
        frag = target.replace(".", "/")
        candidates = [f"{frag}.py", f"{frag}/__init__.py"]
    for f in py_files:
        if any(f == c or f.endswith("/" + c) for c in candidates):
            return f
    return None


def _resolve_js(spec: str, cur_path: str, js_files: set[str]) -> str | None:
    if not spec.startswith("."):  # bare = external package
        return None
    parts = cur_path.split("/")[:-1]
    for seg in spec.split("/"):
        if seg == "." or seg == "":
            continue
        if seg == "..":
            parts = parts[:-1]
        else:
            parts.append(seg)
    base = "/".join(parts)
    for ext in (".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js", "/index.jsx"):
        cand = base + ext
        for f in js_files:
            if f == cand or f.endswith("/" + cand):
                return f
    # already has an extension?
    return base if base in js_files else None


def build_graph(storage: StorageBackend, repo: Repository) -> dict:
    """Return {nodes, edges, truncated} describing intra-repo import dependencies."""
    if not repo.archive_key or not storage.exists(repo.archive_key):
        raise ValueError(
            "Source archive unavailable (the free-tier disk resets on restart). "
            "Click Re-index on the Repositories page to rebuild it."
        )

    ext = _archive_ext(repo)
    data = storage.load_bytes(repo.archive_key)

    files: dict[str, str] = {}  # path -> text (code files only)
    for raw_path, raw in iter_archive_files(data, ext):
        path = _normalize_path(raw_path, ext)
        if _ext(path) not in (_PY_EXTS | _JS_EXTS) or len(raw) > settings.MAX_FILE_BYTES:
            continue
        try:
            files[path] = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue

    py_files = {p for p in files if _ext(p) in _PY_EXTS}
    js_files = {p for p in files if _ext(p) in _JS_EXTS}

    edges: set[tuple[str, str]] = set()
    for path, text in files.items():
        if path in py_files:
            for t in _py_targets(text):
                tgt = _resolve_py(t, path, py_files)
                if tgt and tgt != path:
                    edges.add((path, tgt))
        else:
            for spec in _JS_SPEC.findall(text):
                tgt = _resolve_js(spec, path, js_files)
                if tgt and tgt != path:
                    edges.add((path, tgt))

    # Keep only files that participate in an edge (drop isolated nodes for a cleaner graph).
    connected = {p for e in edges for p in e}
    truncated = False
    if len(connected) > _MAX_NODES:
        # Keep the highest-degree nodes.
        degree: dict[str, int] = {}
        for a, b in edges:
            degree[a] = degree.get(a, 0) + 1
            degree[b] = degree.get(b, 0) + 1
        keep = set(sorted(connected, key=lambda p: degree.get(p, 0), reverse=True)[:_MAX_NODES])
        edges = {(a, b) for a, b in edges if a in keep and b in keep}
        connected = keep
        truncated = True

    in_degree: dict[str, int] = {p: 0 for p in connected}
    for _a, b in edges:
        in_degree[b] = in_degree.get(b, 0) + 1

    nodes = [
        {
            "id": p,
            "label": p.rsplit("/", 1)[-1],
            "group": p.split("/", 1)[0] if "/" in p else "",
            "in_degree": in_degree.get(p, 0),
        }
        for p in sorted(connected)
    ]
    edge_list = [{"source": a, "target": b} for a, b in sorted(edges)]
    return {"nodes": nodes, "edges": edge_list, "truncated": truncated}
