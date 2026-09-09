"""Host-side (CPython stdlib `urllib.request` only) HTTP client for bench-tier live-system checks -
mirrors digital_twin/_http_client.py's `HttpResponse`/`fetch()` shape closely enough that a
shared-behavior function written against one translates directly to the other, though synchronous."""

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
        # A non-2xx response is still a meaningful REST response here (e.g. a validation failure has
        # a real JSON body) - surface it like a success instead of forcing callers to catch HTTPError.
        return HttpResponse(exc.code, dict(exc.headers or {}), exc.read())
