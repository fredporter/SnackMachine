"""Submit a reviewed capture to uCore's admission endpoint.

uCore owns the profile, the Vault destination and the receipt. This client only
transports bounded text and a request ID, so a replay is safe.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://127.0.0.1:8484"
TIMEOUT_SECONDS = 8


class BridgeError(RuntimeError):
    """Raised when uCore refuses the capture or cannot be reached."""


def submit_capture(
    text: str,
    request_id: str,
    *,
    title: str = "capture",
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = TIMEOUT_SECONDS,
) -> dict:
    """POST one bounded capture and return uCore's receipt."""
    if not isinstance(text, str) or not text.strip():
        raise BridgeError("text is required")
    if not request_id:
        raise BridgeError("request_id is required")

    payload = json.dumps(
        {"text": text, "request_id": request_id, "title": title}
    ).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}/api/host/capture",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        try:
            message = json.loads(detail).get("error", detail)
        except ValueError:
            message = detail or f"HTTP {exc.code}"
        raise BridgeError(str(message)) from exc
    except URLError as exc:
        raise BridgeError(f"uCore is unreachable: {exc.reason}") from exc
