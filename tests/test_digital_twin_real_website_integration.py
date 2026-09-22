"""Boots the real sensortask_wozi object graph (digital_twin) with the REAL website - not
html_stub - wired in as `frozen_html`, and proves it over real HTTP: the Unix-port counterpart to
scripts/build_firmware.py's real ARM build, which can only be compiled here, never executed."""

import asyncio
import json
import sys

sys.path.insert(0, "ext")  # reaches the real, vendored ext/microdot.py - same convention as
# test_digital_twin_sensortask_integration.py's own comment.
sys.path.insert(0, "digital_twin")

# Must run before `import sensortask_wozi` below: MicroPython's import machinery checks sys.modules by name
# before touching the filesystem (v1.29.0's py/builtinimport.c, the same lookup CPython does), so pre-
# registering "frozen_html" binds that import to the real website, not the html_stub build.
import frozen_website_wozi  # type: ignore[import-not-found]  # mounts /html with the real website content

sys.modules["frozen_html"] = frozen_website_wozi

import _http_client  # noqa: E402
import sensortask_wozi  # noqa: E402
from _tmp_scratch import TmpScratch  # noqa: E402

# Mirrors asy_wifi_service.py's own _PHASE_STA_SEEKING/_PHASE_HOTSPOT values - same
# not-importable-once-const()-folded reasoning as tests/test_asy_wifi_service.py's own copy; keep in
# sync with asy_wifi_service.py's own definitions if those ever change.
_PHASE_STA_SEEKING = 0
_PHASE_HOTSPOT = 2

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# Per-test config-file isolation via tests/_tmp_scratch.py - see that module's docstring and
# tests/test_tmp_scratch.py for the mechanism. Own port range (19300+) so a parallel or adjacent run of
# test_digital_twin_sensortask_integration.py never collides on either.
_scratch = TmpScratch("dtrw")
_next_port = 19300


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


def _next_test_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


async def _boot(port: int) -> None:
    await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)


async def _start_webserver() -> "asyncio.Task[None]":
    assert sensortask_wozi.webserver is not None
    task = sensortask_wozi.webserver.get_task_starters()[0]()
    # WP1/CLAUDE.md's implicit-FRAM-wiring rule made webserver.pr real-FRAM-backed whenever the device wires
    # FRAM, so _run() now awaits a real self.pr.setup() - a real chunk read/write - before start_server(),
    # not the instant no-op a RAM-only logger's setup() was.
    #
    # Measured directly against this file's real twin fakes: consistently ready within ~400ms, so 1.0s keeps
    # a ~2.5x margin rather than a bare-minimum guess.
    await asyncio.sleep(1.0)
    return task


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def _decompress(body: "bytes | bytearray") -> bytes:
    # Same technique as test_frozen_html_integration.py/test_website_build_integration.py - see
    # either file's own comment for why deflate.DeflateIO(..., AUTO, ...) is the right call here.
    import io

    import deflate

    d = deflate.DeflateIO(io.BytesIO(body), deflate.AUTO, 0, True)
    return d.read()  # type: ignore[no-any-return]


def test_real_website_root_serves_the_actual_production_index_html_not_the_stub() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/")
            assert res.status_code == 200
            assert res.headers["Content-Encoding"] == "gzip"
            body = _decompress(res.body)
            assert b"Sensor Station" in body  # the real prod index.html's own title - never "Hello, wozi!" (html_stub's marker)
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


def test_real_website_inlined_definitions_matches_the_booted_devices_own_id() -> None:
    # definitions.json is no longer a separately-fetched route (scripts/build_website.sh's own
    # "Inlining" comment - SPECIFICATION.md Part H.7): it's embedded directly into
    # index.html at build time instead, so this now reads it out of the real page body.
    #
    # "wozi" is hardcoded deliberately, not a stale device-specific leftover (Part L.4, re-verified): this
    # file's device.id assertion comes from whichever device's real website bundle scripts/test.sh built -
    # frozen_website_wozi.py, the only one - never from sensortask_wozi.py's construction.
    #
    # Generalizing it would mean teaching scripts/test.sh to build a second real gzip+freezefs+inlined
    # bundle per device, real added build cost for all 6, just to re-prove a pipeline this file already
    # proves once.
    #
    # The per-device DATA correctness - a device's real definitions.json carrying its own device.id - is
    # already proven generically for all 6 by tests_scripts/test_buildgen_definitions.py. This file's job is
    # that the gzip/freezefs/inlining pipeline executes correctly under the Unix port at all.
    #
    # That is the same code path whichever device's data flows through it, so picking wozi, this project's
    # exemplary base variant, once is complete coverage rather than a gap.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/definitions.json")
            assert res.status_code == 404  # no longer a separate route at all

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/")
            assert res.status_code == 200
            body = _decompress(res.body).decode()
            marker_start = '<script type="application/json" id="inlined-definitions">'
            start = body.index(marker_start) + len(marker_start)
            end = body.index("</script>", start)
            data = json.loads(body[start:end])
            assert data["device"]["id"] == "wozi"
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


def test_real_website_production_js_entry_is_served_not_the_prototype() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/js/app.js")
            assert res.status_code == 200
            body = _decompress(res.body)
            assert b"installMockFetch" not in body
            assert b"definitions.json" in body
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


def test_real_website_static_mount_never_shadows_a_real_api_route() -> None:
    # The generic "/" static route is registered last (see WebserverService's own routing order,
    # SPECIFICATION.md Part A.5) - proves the real website being mounted doesn't regress any real
    # API endpoint, mirroring test_digital_twin_sensortask_integration.py's own API-shape checks.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/measurements")
            assert res.status_code == 200
            assert set(res.json().keys()) == {"SCD30", "BMP3XX", "SGP40"}
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


# ---------------------------------------------------------------------------
# Captive-portal hotspot-mode redirect - full integration: the real production website, the real API, and
# real HTTP over a real socket, the one thing _sensortask_scenarios.py's in-process dispatch cannot
# exercise.
#
# No real WiFi task is started - conn._conn_phase is set directly instead, the test-seam convention both
# _sensortask_scenarios.py and this file's sibling twin integration suite already use.
#
# That sibling already covers the "reached via a genuine STA-failure transition" case against the stub
# website; this adds the real production website and full API surface on top, plus the dynamic-switch and
# error-path coverage it does not have.
# ---------------------------------------------------------------------------


def test_real_website_hotspot_mode_redirects_unmatched_path_to_root() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.conn is not None
        sensortask_wozi.conn._conn_phase = _PHASE_HOTSPOT
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/generate_204")
            assert res.status_code == 302
            assert res.headers["Location"] == "/"
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


def test_real_website_hotspot_mode_still_serves_real_index_and_real_api_route() -> None:
    # Upstream/downstream error handling: the real production website and real sensor API must keep
    # working unaffected while the device is its own hotspot - the redirect fallback only ever fires
    # for a path that matches no real route and no real static file.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.conn is not None
        sensortask_wozi.conn._conn_phase = _PHASE_HOTSPOT
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/")
            assert res.status_code == 200
            assert res.headers["Content-Encoding"] == "gzip"
            body = _decompress(res.body)
            assert b"Sensor Station" in body  # the real prod index.html, not a redirect loop

            res = await _http_client.fetch("127.0.0.1", port, "GET", "/measurements")
            assert res.status_code == 200
            assert set(res.json().keys()) == {"SCD30", "BMP3XX", "SGP40"}
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


def test_real_website_dynamic_hotspot_toggle_switches_redirect_behavior_live() -> None:
    # Dynamic-mode-switch coverage, full integration: flips the real conn's phase mid-run, over the
    # same live webserver task/socket, and confirms each real HTTP request reflects the phase at
    # request time.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.conn is not None
        conn = sensortask_wozi.conn
        assert conn._conn_phase == _PHASE_STA_SEEKING
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/generate_204")
            assert res.status_code == 404

            conn._conn_phase = _PHASE_HOTSPOT
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/generate_204")
            assert res.status_code == 302
            assert res.headers["Location"] == "/"

            conn._conn_phase = _PHASE_STA_SEEKING
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/generate_204")
            assert res.status_code == 404
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


def test_real_website_put_to_unmatched_path_in_hotspot_mode_still_405() -> None:
    # All-paths/no-crash coverage: a non-GET request to an unmatched path must still resolve to a
    # clean 405 over a real socket, hotspot mode or not - never a hang, a redirect, or a crash.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.conn is not None
        sensortask_wozi.conn._conn_phase = _PHASE_HOTSPOT
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "PUT", "/generate_204", {})
            assert res.status_code == 405
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=10.0)


def test_a_full_ceiling_of_concurrent_real_page_loads_all_serve_the_real_website() -> None:
    # Every other row here loads the real site one request at a time. A real browser opens two
    # connections per page load after bundling/inlining (Part H.7), and several tabs can be open at
    # once - so the ceiling's own worth of REAL page loads has to land together, not in sequence.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        assert sensortask_wozi.webserver is not None
        ceiling: int = sensortask_wozi.webserver._max_connections
        task = await _start_webserver()
        try:

            async def page_load() -> "list[int]":
                # The real footprint: the page plus its own bundled script, concurrently.
                return list(await asyncio.gather(_one("/"), _one("/js/app.js")))

            async def _one(path: str) -> int:
                res = await _http_client.fetch("127.0.0.1", port, "GET", path)
                assert res.status_code == 200, (path, res.status_code)
                return len(_decompress(res.body))

            tabs = max(2, ceiling // 2)
            sizes = await asyncio.gather(*(page_load() for _ in range(tabs)))
            # Every tab got the real content, not a truncated or empty body from a contended
            # static mount - the failure a concurrent burst against one frozen filesystem produces.
            for index_bytes, app_bytes in sizes:
                assert index_bytes > 1000, sizes
                assert app_bytes > 1000, sizes
            assert len({tuple(pair) for pair in sizes}) == 1, sizes  # identical for every tab
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=30.0)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
