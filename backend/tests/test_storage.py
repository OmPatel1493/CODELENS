"""LocalStorageBackend tests, including the path-traversal guard."""

import pytest

from app.services.storage import LocalStorageBackend


def test_save_load_exists_delete(tmp_path):
    storage = LocalStorageBackend(str(tmp_path))
    key = "repositories/1/source.zip"

    assert storage.exists(key) is False
    storage.save_bytes(key, b"hello")
    assert storage.exists(key) is True
    assert storage.load_bytes(key) == b"hello"

    storage.delete(key)
    assert storage.exists(key) is False
    # delete is idempotent
    storage.delete(key)


def test_rejects_path_traversal(tmp_path):
    storage = LocalStorageBackend(str(tmp_path))
    with pytest.raises(ValueError):
        storage.save_bytes("../escape.txt", b"nope")
