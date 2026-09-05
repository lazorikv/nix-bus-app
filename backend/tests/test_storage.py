"""Unit tests for the S3/MinIO storage wrapper.

boto3 is mocked, so these never touch a real object store — they only assert that
``storage`` builds the right clients and forwards the expected calls.
"""

from unittest.mock import MagicMock

from botocore.exceptions import ClientError

import app.infrastructure.storage as storage


def _fake_client(monkeypatch: object) -> MagicMock:
    client = MagicMock()
    monkeypatch.setattr(storage.boto3, "client", lambda *a, **k: client)
    # Clients are memoized with lru_cache; drop any client cached by other tests.
    storage._client.cache_clear()
    storage._presign_client.cache_clear()
    return client


def test_ensure_bucket_creates_when_missing(monkeypatch) -> None:
    client = _fake_client(monkeypatch)
    client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
    )
    storage.ensure_bucket()
    client.create_bucket.assert_called_once()


def test_ensure_bucket_noop_when_present(monkeypatch) -> None:
    client = _fake_client(monkeypatch)
    storage.ensure_bucket()
    client.create_bucket.assert_not_called()


def test_upload_bytes_forwards_object(monkeypatch) -> None:
    client = _fake_client(monkeypatch)
    storage.upload_bytes("photos/1.png", b"data", "image/png")
    _, kwargs = client.put_object.call_args
    assert kwargs["Key"] == "photos/1.png"
    assert kwargs["Body"] == b"data"
    assert kwargs["ContentType"] == "image/png"


def test_presigned_get_url_uses_public_client(monkeypatch) -> None:
    client = _fake_client(monkeypatch)
    client.generate_presigned_url.return_value = "http://minio.local/photos/1.png"
    url = storage.presigned_get_url("photos/1.png", expires=120)
    assert url == "http://minio.local/photos/1.png"
    _, kwargs = client.generate_presigned_url.call_args
    assert kwargs["ExpiresIn"] == 120


def test_delete_object_forwards_key(monkeypatch) -> None:
    client = _fake_client(monkeypatch)
    storage.delete_object("photos/1.png")
    _, kwargs = client.delete_object.call_args
    assert kwargs["Key"] == "photos/1.png"
