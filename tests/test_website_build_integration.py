"""Real-pipeline integration test for the real website build (WEBSITE_PLAN.md §10 item 4): proves
scripts/build_website.sh's staged, recursive merge - html/ + the production js/ module set, for one
device - imports cleanly, mounts for real, and is served correctly end to end through a real
WebserverService/Microdot() app, with the prototype-only files (js/app.js, js/mock-server.js,
other devices' definitions) confirmed absent.
The real chain: html/ + js/ -> scripts/build_website.sh wozi -> frozen_modules/frozen_website_wozi.py
-> `import frozen_website_wozi` (mount-on-import) -> WebserverService(static_mount=...)."""
# Requires frozen_modules/frozen_website_wozi.py already on MICROPYPATH - scripts/test.sh
# regenerates it via scripts/build_website.sh before running the suite. `import
# frozen_website_wozi` mounts /html as a real, unconditional side effect - safe to do once per
# test-process run, and distinct from test_frozen_html_integration.py's own `import frozen_html`
# (a different frozen module, built from html_stub/, never imported by this file - see that
# module's own docstring for why the two never conflict).

import asyncio
import json
import sys

sys.path.insert(0, "ext")

import frozen_website_wozi  # type: ignore[import-not-found]  # noqa: E402,F401  # mounts /html on import
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
    # See test_frozen_html_integration.py's own _decompress() for the full rationale - identical
    # mechanism, applied here to the real website's gzip-Content-Encoding bytes instead.
    import io

    import deflate

    d = deflate.DeflateIO(io.BytesIO(body.read()), deflate.AUTO, 0, True)
    return d.read()  # type: ignore[no-any-return]


def _make_request(app: "Microdot", method: str, path: str) -> Request:
    return Request(app, ("127.0.0.1", 12345), method, path, "1.1", {"Content-Length": "0"}, body=b"")


def _make_app() -> "tuple[WebserverService, Microdot]":
    app = Microdot()
    service = WebserverService(app, static_mount="/html")
    return service, app


def test_root_serves_the_real_index_html() -> None:
    _, app = _make_app()
    res = run(app.dispatch_request(_make_request(app, "GET", "/")))
    assert res.status_code == 200
    assert res.headers["Content-Encoding"] == "gzip"
    assert res.headers["Content-Type"].startswith("text/html")
    assert b"Sensor Station" in _decompress(res.body)


def test_style_css_and_definitions_json_are_not_served_as_separate_files() -> None:
    # Both are inlined directly into index.html at build time now (scripts/build_website.sh's own
    # "Inlining" comment - WEBSITE_PLAN.md §7's follow-up round) instead of being staged as their
    # own files - a page load needs one fewer connection than before. html/definitions/wozi.json
    # (the nested dev-preview path) and definitions/dev.json (a different device's file) were
    # already never shipped this way either.
    _, app = _make_app()
    for path in ("/style.css", "/definitions.json", "/definitions/wozi.json", "/definitions/dev.json"):
        res = run(app.dispatch_request(_make_request(app, "GET", path)))
        assert res.status_code == 404, path


def test_inlined_definitions_and_stylesheet_replace_the_two_separately_staged_files() -> None:
    _, app = _make_app()
    res = run(app.dispatch_request(_make_request(app, "GET", "/")))
    body = _decompress(res.body).decode()

    # style.css's own stylesheet <link> is gone - its content is a real <style> block instead.
    assert '<link rel="stylesheet" href="style.css">' not in body
    assert "<style>" in body
    assert ":root {" in body  # a real, distinctive style.css rule, not an empty block

    # definitions.json's own content is a real, valid, correctly-scoped-to-this-device JSON blob
    # inside a dedicated <script> element, not a fetch target any more.
    marker_start = '<script type="application/json" id="inlined-definitions">'
    start = body.index(marker_start) + len(marker_start)
    end = body.index("</script>", start)
    data = json.loads(body[start:end])
    assert data["device"]["id"] == "wozi"


def test_production_js_is_served_as_one_bundle_under_js() -> None:
    # The seven production modules (field-format.js, poll-manager.js, templates.js,
    # definitions.js, render.js, nav.js, main.js) are concatenated into one js/app.js at staging
    # time (scripts/build_website.sh's own "Bundling" comment - WEBSITE_PLAN.md §10 item 5), not
    # shipped as seven separate files - each of their own paths must now 404, not 200.
    _, app = _make_app()
    res = run(app.dispatch_request(_make_request(app, "GET", "/js/app.js")))
    assert res.status_code == 200
    assert res.headers["Content-Type"].startswith("application/javascript")

    for path in ("/js/definitions.js", "/js/poll-manager.js", "/js/render.js", "/js/templates.js", "/js/nav.js", "/js/field-format.js"):
        res = run(app.dispatch_request(_make_request(app, "GET", path)))
        assert res.status_code == 404, path


def test_bundled_js_contains_every_production_module_with_no_leftover_local_imports() -> None:
    _, app = _make_app()
    res = run(app.dispatch_request(_make_request(app, "GET", "/js/app.js")))
    body = _decompress(res.body)

    # Every production module's own distinctive top-level declaration made it into the bundle -
    # a real, direct check that concatenation didn't silently drop one.
    for marker in (
        b"function formatFieldValue",  # field-format.js
        b"function fetchWithTimeout",  # poll-manager.js
        b"function buildFieldGroupCard",  # templates.js
        b"function validateDefinitions",  # definitions.js
        b"function renderSection",  # render.js
        b"function initNav",  # nav.js
        b"function startApp",  # main.js
    ):
        assert marker in body, marker

    # No `import { ... } from "./local-file.js";` line survived - every such line only worked
    # because the imported name is now already in scope earlier in the same concatenated file. A
    # leftover `export { ... } from "./local-file.js";` re-export would be just as broken (the
    # bundle is one file; there is no "./local-file.js" left to resolve at runtime) but isn't
    # caught by the import-line check above - checked directly after a real instance of exactly
    # this mistake (js/templates.js briefly re-exported field-format.js's formatFieldValue this
    # way) was caught only by manually tracing the build, not by this test.
    for line in body.split(b"\n"):
        assert not line.startswith(b"import "), line
        assert not (line.startswith(b"export ") and b" from \"./" in line), line


def test_js_app_js_is_the_real_production_entry_not_the_prototype() -> None:
    # js/main.js's content, staged as js/app.js (see scripts/build_website.sh) - distinguished from
    # the prototype js/app.js by the absence of its mock-install/device-switch machinery.
    _, app = _make_app()
    res = run(app.dispatch_request(_make_request(app, "GET", "/js/app.js")))
    body = _decompress(res.body)
    assert b"installMockFetch" not in body
    assert b"KNOWN_DEVICES" not in body
    assert b"definitions.json" in body


def test_prototype_only_files_are_not_shipped() -> None:
    _, app = _make_app()
    for path in ("/js/mock-server.js",):
        res = run(app.dispatch_request(_make_request(app, "GET", path)))
        assert res.status_code == 404, path


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
