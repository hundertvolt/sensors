"""Boots the real sensortask_wozi object graph (digital_twin) with the REAL website - not
html_stub - wired in as `frozen_html`, and proves it over real HTTP: the Unix-port counterpart to
scripts/build_firmware.py's real ARM build (WEBSITE_PLAN.md §10 item 4), runnable and checkable
here where the ARM build can only be compiled, never executed."""

import asyncio
import json
import os
import sys

sys.path.insert(0, "ext")  # reaches the real, vendored ext/microdot.py - same convention as
# test_digital_twin_sensortask_integration.py's own comment.
sys.path.insert(0, "digital_twin")

# Must run before `import sensortask_wozi` below: MicroPython's import machinery checks
# sys.modules by name before touching the filesystem (confirmed directly against the pinned
# v1.28.0 source, py/builtinimport.c's process_import_at_level(), same lookup CPython does) - so
# pre-registering "frozen_html" here makes sensortask_wozi.py's own top-level `import frozen_html`
# bind to the real website instead of resolving frozen_modules/frozen_html.py's html_stub build.
import frozen_website_wozi  # type: ignore[import-not-found]  # noqa: E402  # mounts /html with the real website content

sys.modules["frozen_html"] = frozen_website_wozi

import _http_client  # noqa: E402

import sensortask_wozi  # noqa: E402

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


# Same per-test config-file isolation shape as test_digital_twin_sensortask_integration.py, own
# port range (19300+) so a parallel/adjacent run of that file never collides on either.
_TMP_DIR = "tests/_tmp"
_next_dir = 0
_next_port = 19300


def _tmp_cfg_dir() -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    _next_dir += 1
    path = _TMP_DIR + "/dtrw_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    return path + "/"


def _next_test_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


async def _boot(port: int) -> None:
    await sensortask_wozi.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)


async def _start_webserver() -> "asyncio.Task[None]":
    assert sensortask_wozi.webserver is not None
    task = sensortask_wozi.webserver.get_task_starters()[0]()
    await asyncio.sleep(0.1)  # let _run() actually reach start_server()/bind - same bound
    # test_asy_webserver_service.py's own F.8 test uses for the identical real-socket startup race.
    return task


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def _decompress(body: bytes) -> bytes:
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


def test_real_website_definitions_json_matches_the_booted_devices_own_id() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/definitions.json")
            assert res.status_code == 200
            data = json.loads(_decompress(res.body))
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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
