"""Real-pipeline integration test for the website placeholder scaffold (see SPECIFICATION.md Part
A.9): proves the actual built artifact - scripts/build_frozen_html.sh's gzip -> freezefs --on-import mount
output, `frozen_modules/frozen_html.py` - imports cleanly, mounts for real, and is served correctly
end to end through a real WebserverService + real ext/microdot.py Microdot() app. This is deliberately
separate from tests/test_asy_webserver_service.py's own Section G, which exercises the generic
route-wiring mechanism against a synthetic VfsFrozen fixture, independent of the real stub content -
see that file's own module docstring. Per SPECIFICATION.md Part D.12 ("if this file is one layer in
a larger real call chain, also add integration tests that drive the real chain"), this is that real
chain: html_stub/ -> scripts/build_frozen_html.sh -> frozen_modules/frozen_html.py ->
`import frozen_html` (mount-on-import) -> WebserverService(static_mount=...).

Requires frozen_modules/frozen_html.py to already exist on MICROPYPATH - scripts/test.sh regenerates
it via scripts/build_frozen_html.sh before running the test suite (see that script's own comment for
why it's frozen_modules/, never the reserved ".frozen" sentinel). `import frozen_html` mounts /html
as a real, unconditional side effect (matches src/sensortask_wozi.py's own module-level import - see
this project's "imports happen once, at module load" convention) - safe to do once per test-process
run, the same way every other test file's real driver imports are.
"""

import asyncio
import json
import sys

# Same sys.path convention as tests/test_setter_microdot_integration.py - reaches the real, vendored
# ext/microdot.py without touching MICROPYPATH/pyproject.toml/scripts/test.sh.
sys.path.insert(0, "ext")

import frozen_html  # type: ignore[import-not-found]  # noqa: E402,F401  # mounts /html on import
from microdot import Microdot, Request  # type: ignore[import-not-found]  # noqa: E402

from asy_webserver_service import WebserverService  # noqa: E402

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any


def run(coro: "Any") -> "Any":
    return asyncio.run(coro)


def _decompress(body: "Any") -> bytes:
    # send_file() responses stream their body from a file-like object (VfsFrozen.open()'s own
    # BytesIO), not raw bytes - .read() first to get the real gzip bytes off the wire, matching what
    # a real HTTP client would receive. deflate.DeflateIO with AUTO auto-detects the gzip header
    # (confirmed directly against the pinned v1.28.0 Unix-port build) - the same mechanism
    # ffsmount.py's own VfsFrozen.open() would use for a freezefs-level --compress entry, applied
    # here to our own gzip-Content-Encoding bytes instead, since this project never uses freezefs's
    # own --compress (see CLAUDE.md).
    import io

    import deflate

    # No `with` - real MicroPython DeflateIO does support the context-manager protocol (confirmed
    # directly), but the micropython-rp2-rpi_pico_w-stubs package doesn't declare __enter__/__exit__
    # on it (a stub gap, same class of thing as pyproject.toml's own documented Timer()/I2C.deinit()
    # gaps) - a plain read() on this short-lived, in-memory-only stream needs no explicit close.
    d = deflate.DeflateIO(io.BytesIO(body.read()), deflate.AUTO, 0, True)
    return d.read()  # type: ignore[no-any-return]


def _make_request(app: "Microdot", method: str, path: str) -> Request:
    return Request(app, ("127.0.0.1", 12345), method, path, "1.1", {"Content-Length": "0"}, body=b"")


def _make_app() -> "tuple[WebserverService, Microdot]":
    app = Microdot()
    service = WebserverService(app, static_mount="/html")
    return service, app


def test_root_serves_the_real_stub_index_gzip_decompressed_content() -> None:
    _, app = _make_app()
    res = run(app.dispatch_request(_make_request(app, "GET", "/")))
    assert res.status_code == 200
    assert res.headers["Content-Encoding"] == "gzip"
    assert res.headers["Content-Type"].startswith("text/html")
    assert b"Hello, wozi!" in _decompress(res.body)


def test_index_html_by_name_matches_root() -> None:
    _, app = _make_app()
    res = run(app.dispatch_request(_make_request(app, "GET", "/index.html")))
    assert res.status_code == 200
    assert b"Hello, wozi!" in _decompress(res.body)


def test_style_css_has_the_right_content_type_and_real_gzip_body() -> None:
    _, app = _make_app()
    res = run(app.dispatch_request(_make_request(app, "GET", "/style.css")))
    assert res.status_code == 200
    assert res.headers["Content-Type"].startswith("text/css")
    assert res.headers["Content-Encoding"] == "gzip"
    assert b"font-family" in _decompress(res.body)


def test_functions_js_has_the_right_content_type() -> None:
    _, app = _make_app()
    res = run(app.dispatch_request(_make_request(app, "GET", "/functions.js")))
    assert res.status_code == 200
    assert res.headers["Content-Type"].startswith("application/javascript")


def test_favicon_ico_is_served_as_binary_octet_stream() -> None:
    # favicon.ico isn't in Response.types_map (ext/microdot.py), so it correctly falls back to
    # application/octet-stream - proves the pipeline handles non-text/binary placeholder content too.
    _, app = _make_app()
    res = run(app.dispatch_request(_make_request(app, "GET", "/favicon.ico")))
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/octet-stream"


def test_every_stub_page_named_in_index_html_is_actually_served() -> None:
    for path in ("/nettimeconfig.html", "/sensorconfig.html", "/systemledconfig.html"):
        _, app = _make_app()
        res = run(app.dispatch_request(_make_request(app, "GET", path)))
        assert res.status_code == 200, path
        assert res.headers["Content-Type"].startswith("text/html")


def test_unknown_path_returns_404_not_the_index() -> None:
    _, app = _make_app()
    res = run(app.dispatch_request(_make_request(app, "GET", "/this-file-does-not-exist.html")))
    assert res.status_code == 404
    assert json.loads(res.body)["descr"] == "Not found"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
