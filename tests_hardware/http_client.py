"""Host-side (CPython, stdlib `urllib.request` only - no new dependency, matching this project's
own preference for hand-rolled-over-imported seen in digital_twin/_http_client.py) HTTP client for
bench-tier live-system checks (HARDWARE_TEST_PLAN.md §4's "flash/bench live-system adapter").
Deliberately mirrors digital_twin/_http_client.py's own `HttpResponse`/`fetch()` shape (status_code,
.json(), method/path/json_body signature) closely enough that a shared-behavior function written
against one translates directly to the other, even though this one is synchronous/blocking (CPython
has no asyncio event loop running in a pytest test body) where the twin's is a coroutine."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


def fetch(host: str, port: int, method: str, path: str, json_body: dict[str, Any] | None = None, timeout_s: float = 10.0) -> HttpResponse:
    url = f"http://{host}:{port}{path}"
    data = None
    headers = {}
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:  # noqa: S310 - fixed http:// scheme, a real LAN device we constructed the URL for ourselves, never user-controlled input
            body = response.read()
            return HttpResponse(response.status, dict(response.headers), body)
    except urllib.error.HTTPError as exc:
        # A non-2xx response is still a real, meaningful HTTP response for this codebase's own REST
        # conventions (e.g. a validation failure comes back as a real JSON body with a real status
        # code, not just an exception) - surfaced the same way a successful response would be,
        # rather than forcing every caller to catch HTTPError for what's often the expected path.
        return HttpResponse(exc.code, dict(exc.headers or {}), exc.read())
