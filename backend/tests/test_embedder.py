"""Embedding backend tests — Strategy selection + the API backend (HTTP mocked).

No torch and no network: LocalEmbedder is only checked for *selection*, and the
API path is exercised with httpx.post monkeypatched, so these stay fast/offline.
"""

import math

import pytest

from app.services import embedder
from app.services.embedder import ApiEmbedder, LocalEmbedder, _normalize


def test_normalize_produces_unit_vector():
    out = _normalize([3.0, 4.0])  # 3-4-5 triangle → length 5
    assert math.isclose(out[0], 0.6) and math.isclose(out[1], 0.8)
    assert math.isclose(math.sqrt(sum(x * x for x in out)), 1.0)


def test_normalize_handles_zero_vector():
    assert _normalize([0.0, 0.0]) == [0.0, 0.0]  # no divide-by-zero


def test_get_embedder_selects_backend_by_env(monkeypatch):
    embedder.get_embedder.cache_clear()
    monkeypatch.setattr(embedder.settings, "EMBEDDING_BACKEND", "local")
    assert isinstance(embedder.get_embedder(), LocalEmbedder)

    embedder.get_embedder.cache_clear()
    monkeypatch.setattr(embedder.settings, "EMBEDDING_BACKEND", "api")
    assert isinstance(embedder.get_embedder(), ApiEmbedder)
    embedder.get_embedder.cache_clear()


def test_api_embedder_normalizes_and_sends_batch(monkeypatch):
    captured = {}

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return [[3.0, 4.0], [0.0, 5.0]]  # unnormalized, like the raw API

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["auth"] = headers.get("Authorization")
        return _Resp()

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)

    emb = ApiEmbedder("https://example/api", token="tok", timeout=5.0)
    out = emb.embed(["a", "b"])

    assert captured["json"]["inputs"] == ["a", "b"]  # batched in one call
    assert captured["auth"] == "Bearer tok"
    # Both vectors returned unit-normalized (parity with LocalEmbedder).
    assert all(math.isclose(math.sqrt(sum(x * x for x in v)), 1.0) for v in out)


def test_api_embedder_empty_input_skips_call(monkeypatch):
    import httpx

    def boom(*a, **k):  # must not be called
        raise AssertionError("no HTTP call expected for empty input")

    monkeypatch.setattr(httpx, "post", boom)
    assert ApiEmbedder("u", "t", 1.0).embed([]) == []


def test_api_embedder_rejects_bad_shape(monkeypatch):
    class _Resp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"error": "model loading"}  # not a list of vectors

    import httpx

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp())
    with pytest.raises(RuntimeError, match="Unexpected embedding API response"):
        ApiEmbedder("u", "t", 1.0).embed(["x"])
