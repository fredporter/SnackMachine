"""Bridge client: bounded submission to uCore with honest failures."""
from __future__ import annotations

import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from snackmachine_ext import bridge_client  # noqa: E402


class _Response:
    def __init__(self, payload: dict, status: int = 201) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


def test_submit_posts_bounded_text(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response({"run_id": "cap-1", "path": "/vault/x.md", "status": "completed"})

    monkeypatch.setattr(bridge_client, "urlopen", fake_urlopen)

    receipt = bridge_client.submit_capture("hello", "req-1", title="Note")

    assert receipt["run_id"] == "cap-1"
    assert captured["url"].endswith("/api/host/capture")
    assert captured["body"] == {
        "text": "hello",
        "request_id": "req-1",
        "title": "Note",
    }


def test_refusal_is_reported_with_the_server_reason(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url,
            403,
            "Forbidden",
            {},
            io.BytesIO(json.dumps({"error": "Guest profiles cannot capture"}).encode("utf-8")),
        )

    monkeypatch.setattr(bridge_client, "urlopen", fake_urlopen)

    with pytest.raises(bridge_client.BridgeError, match="Guest profiles"):
        bridge_client.submit_capture("hello", "req-2")


def test_empty_text_never_reaches_the_service(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("uCore must not be called")

    monkeypatch.setattr(bridge_client, "urlopen", fail)

    with pytest.raises(bridge_client.BridgeError, match="text is required"):
        bridge_client.submit_capture("   ", "req-3")
