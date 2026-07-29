"""Dependency-graph tests — import resolution + build_graph over an in-memory zip."""

import io
import zipfile

import pytest

from app.models.repository import Repository, RepoSource, RepoStatus
from app.services import graph_service


class _FakeStorage:
    def __init__(self, data: bytes | None):
        self._data = data

    def exists(self, key: str) -> bool:
        return self._data is not None

    def load_bytes(self, key: str) -> bytes:
        assert self._data is not None
        return self._data

    def save_bytes(self, key, data): ...
    def delete(self, key): ...


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()


def _repo() -> Repository:
    return Repository(
        id=1,
        name="p",
        owner_id=1,
        status=RepoStatus.ready,
        source=RepoSource.upload,
        archive_key="k",
    )


# ── Resolution helpers ───────────────────────────────────────────


def test_py_targets_absolute_and_relative():
    text = "import proj.b\nfrom proj.util import helper\nfrom . import c\n"
    targets = graph_service._py_targets(text)
    assert "proj.b" in targets
    assert "proj.util" in targets
    assert ".c" in targets  # relative submodule


def test_resolve_py_suffix_match_handles_src_layout():
    files = {"src/proj/signer.py", "src/proj/__init__.py"}
    assert graph_service._resolve_py("proj.signer", "src/proj/x.py", files) == "src/proj/signer.py"


def test_resolve_js_relative():
    files = {"src/util.ts", "src/app.ts"}
    assert graph_service._resolve_js("./util", "src/app.ts", files) == "src/util.ts"
    assert graph_service._resolve_js("react", "src/app.ts", files) is None  # external


# ── build_graph ──────────────────────────────────────────────────


def test_build_graph_python_edges():
    data = _zip(
        {
            "proj/a.py": "import proj.b\n",
            "proj/b.py": "x = 1\n",
            "proj/c.py": "from . import b\n",
            "proj/lonely.py": "y = 2\n",  # no imports → dropped (isolated)
        }
    )
    g = graph_service.build_graph(_FakeStorage(data), _repo())
    edge_pairs = {(e["source"], e["target"]) for e in g["edges"]}
    assert ("proj/a.py", "proj/b.py") in edge_pairs
    assert ("proj/c.py", "proj/b.py") in edge_pairs
    ids = {n["id"] for n in g["nodes"]}
    assert "proj/lonely.py" not in ids  # isolated node dropped
    b = next(n for n in g["nodes"] if n["id"] == "proj/b.py")
    assert b["in_degree"] == 2  # imported by a and c
    assert g["truncated"] is False


def test_build_graph_missing_archive_raises():
    with pytest.raises(ValueError, match="Source archive unavailable"):
        graph_service.build_graph(_FakeStorage(None), _repo())
