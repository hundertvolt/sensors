"""Real-socket concurrent-connection regression coverage for WebserverService, booted against the
real digital_twin buses - genuinely concurrent TCP connections, unlike
tests/test_asy_webserver_service.py Section F's in-process _serve()-against-fakes tests.
Parametrized across all 6 real devices (BUILD_CHAIN_PLAN.md's Session 6.2): every scenario below has
zero device-specific assertions (pure connection-count/HTTP-status/timing logic - WebserverService's
own accept/reject machinery is identical regardless of which sensors a device has), so generalizing
this file needed no assertion rework - only which device's freshly-buildgen-generated module gets
booted."""

# See SPECIFICATION.md Part H.7 and this module's own comments below for the full rationale.

# Every existing test client in this project before this file (curl, Python's http.client,
# digital_twin/_http_client.py itself) has always issued exactly one request at a time, so nothing
# has ever driven more than one simultaneous real TCP connection against a live server - Section F
# above drives WebserverService._serve() directly against in-process reader/writer fakes, never the
# real accept()/select.poll() layer. digital_twin/README.md's "Known gaps" section records a real,
# already-fixed MicroPython Unix-port segfault found by a real user report firing 8+ concurrent
# clients (digital_twin/run_generic_integration.py's own soak-section comment) - this file's own
# high-concurrency test deliberately revisits that exact scale as a regression check, in-process,
# so a recurrence of that class of bug crashes this test file's own interpreter process and fails
# loudly under scripts/test.sh's per-file timeout+retry, the same way test_asy_webserver_service.py's
# own F.9 soak already relies on for its identical in-process crash-detection story.
#
# One thing this file deliberately does NOT attempt: a "different source host" variant. Confirmed
# directly by reading WebserverService._serve() (src/asy_webserver_service.py) - it makes no
# per-source-IP distinction anywhere, and the pinned MicroPython Unix port's own
# asyncio.open_connection() has no local_addr parameter to bind a distinct source address from
# regardless. Concurrent connections from one client machine and from many are handled by literally
# the same code path, so a second source IP would add no real coverage here - what actually
# matters, and is what every test below varies, is the number of connections in flight and their
# behavior.

import asyncio
import gc
import json
import os
import sys
import time

sys.path.insert(0, "ext")  # reaches the real, vendored ext/microdot.py - same convention as
# test_digital_twin_sensortask_integration.py's own comment.
sys.path.insert(0, "digital_twin")

import _http_client
import machine

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# Every real device (devices/*.toml) - buildgen generates each one's own module + wiring plan into
# build/generated_src/ before scripts/test.sh ever runs this file (scripts/_generate_sensortask_modules.py).
_DEVICES = ("wozi", "dev", "arzi", "klkizi", "grkizi", "schlafzi")


def _wiring_plan(device: str) -> "dict[str, Any]":
    with open(f"build/generated_src/sensortask_{device}_wiring_plan.json") as f:
        plan: dict[str, Any] = json.load(f)
    return plan


# ---------------------------------------------------------------------------
# Per-test config-file isolation - same shape every other tests/test_digital_twin_*.py integration
# file uses. Own port range (19700+), distinct from test_digital_twin_sensortask_integration.py's
# 19100+ and test_digital_twin_real_website_integration.py's 19300+.
# ---------------------------------------------------------------------------

_TMP_DIR = "tests/_tmp"
_next_dir = 0
_next_port = 19700


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    try:
        entries = os.listdir(_TMP_DIR)
    except OSError:
        return
    for entry in entries:
        if not entry.startswith(prefix):
            continue
        dir_path = _TMP_DIR + "/" + entry
        try:
            for filename in os.listdir(dir_path):
                try:
                    os.remove(dir_path + "/" + filename)
                except OSError:
                    pass
            os.rmdir(dir_path)
        except OSError:
            pass


_sweep_stale_tmp_dirs("dtcc_")


def _tmp_cfg_dir() -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    _next_dir += 1
    path = _TMP_DIR + "/dtcc_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    return path + "/"


def _next_test_port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


async def _boot(port: int, device: str) -> "Any":
    # configure_wiring() first: every digital-twin I2C/SPI construction reads the shared
    # machine._wiring_plan global (BUILD_CHAIN_PLAN.md's Session 6.2 finding - see this file's own
    # git history/PR description) - "last configure_wiring() call before construction wins", so this
    # must run immediately before build_system(), not once at module import time, since several
    # devices' own modules get booted in the same process across this file's full test run.
    machine.configure_wiring(_wiring_plan(device))
    module = __import__(f"sensortask_{device}")
    await module.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
    return module


async def _start_webserver(module: "Any") -> "asyncio.Task[None]":
    assert module.webserver is not None
    task: asyncio.Task[None] = module.webserver.get_task_starters()[0]()
    await asyncio.sleep(0.1)  # let _run() actually reach start_server()/bind - same bound
    # test_asy_webserver_service.py's own F.8 test uses for the identical real-socket startup race.
    return task


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _healthy_request(host: str, port: int, path: str = "/measurements") -> int:
    res = await _http_client.fetch(host, port, "GET", path)
    return res.status_code


async def _flaky_connection(host: str, port: int) -> None:
    """Opens a real connection, sends a deliberately incomplete request (no terminating blank
    line, no Host header), then disconnects without ever completing it - exercises the same
    EOFError/timeout reclaim path a real client on a lossy network or a killed browser tab would
    trigger (WebserverService._serve(), src/asy_webserver_service.py)."""
    _reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(b"GET / HTTP/1.1\r\n")
        await writer.drain()
        await asyncio.sleep(0.05)  # give the server a moment to actually start reading it
    finally:
        writer.close()
        await writer.wait_closed()


async def _still_serving(host: str, port: int, timeout_s: float = 5.0) -> bool:
    # Retried, not single-shot: right after a connection burst, a still-draining prior connection
    # (its own _close_writer() await, or a reject-when-full close) can transiently leave
    # max_connections' slots looking full for a moment - a real, benign timing window, not a sign
    # the server is actually wedged. Only a *sustained* failure across this whole budget means that.
    start = time.ticks_ms()
    while True:
        try:
            if await asyncio.wait_for(_healthy_request(host, port), 2.0) == 200:
                return True
        except Exception:
            pass
        if time.ticks_diff(time.ticks_ms(), start) >= timeout_s * 1000:
            return False
        await asyncio.sleep(0.1)


async def _browser_page_load(host: str, port: int) -> "list[int]":
    """Simulates one browser tab's page-load connection burst - two concurrent GETs, matching the
    real production website's own post-inlining footprint (SPECIFICATION.md Part H.7:
    style.css/definitions.json are now inlined directly into index.html at build time, cutting a
    real page load from four connections to two - index.html + app.js). Uses this test file's own
    default (html_stub) mount's real routes ("/" and "/style.css" both exist there too) rather than
    swapping in the real website like test_digital_twin_real_website_integration.py does - this
    file cares about connection-count/timing behavior, not content, so reusing whatever's already
    mounted keeps it dependency-light while still exercising two real, concurrently-opened sockets."""

    async def _get(path: str) -> int:
        res = await _http_client.fetch(host, port, "GET", path)
        return res.status_code

    return list(await asyncio.gather(_get("/"), _get("/style.css")))


async def _openhab_poll(host: str, port: int) -> "list[int]":
    """Simulates one OpenHAB polling cycle: two concurrent GETs against two real REST endpoints -
    the project owner's own named example, matching how a real binding polls several channels at
    once rather than one at a time."""

    async def _get(path: str) -> int:
        res = await _http_client.fetch(host, port, "GET", path)
        return res.status_code

    return list(await asyncio.gather(_get("/measurements"), _get("/status")))


async def _slow_but_healthy_put(host: str, port: int, delay_s: float) -> int:
    """Opens a real connection and sends a legitimate, harmless PUT (an empty /system body - a real
    no-op, SPECIFICATION.md Part A.8) with its own body trickled in two halves and a real delay
    between them - stays genuinely open and in-flight for `delay_s`, unlike _flaky_connection()
    (which never completes a request at all). Used to prove an existing, legitimately slow
    connection survives a concurrent overflow burst landing while it's still in flight."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        body = b"{}"
        header = (
            f"PUT /system HTTP/1.1\r\nHost: test\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n"
        ).encode()
        writer.write(header + body[:1])
        await writer.drain()
        await asyncio.sleep(delay_s)
        writer.write(body[1:])
        await writer.drain()
        line = await reader.readline()
        return _http_client.parse_status_line(line)
    finally:
        writer.close()
        await writer.wait_closed()


async def _real_config_write(host: str, port: int, interval: int) -> int:
    """A real, harmless, valid config write - PUT /sensors {"SCD30": {"Interval": interval}} -
    against the real, currently-registered SCD30 driver (unlike _slow_but_healthy_put()'s own
    no-op empty /system PUT above, this genuinely reaches ConfigManager.write_config() through the
    real object graph; SCD30 is present on every real device - BUILD_CHAIN_PLAN.md's Session 2).
    Used to prove concurrent GET polling survives a real concurrent config write, not just another
    concurrent read - the digital-twin-tier equivalent of
    tests_hardware/bench/test_memory_stress_bench.py's own real-hardware hammer-load test (GET
    /measurements+/sensors concurrent with a real PUT-triggered SGP40 reset) and
    tests/test_asy_webserver_service.py's own I.4 unit-level equivalent."""
    res = await _http_client.fetch(host, port, "PUT", "/sensors", {"SCD30": {"Interval": interval}})
    return res.status_code


# ---------------------------------------------------------------------------
# Scenario bodies - one per distinct concurrency shape, each parametrized by `device` and
# registered once per real device below via _register()/globals(), rather than 6 hand-duplicated
# copies of every test. Renamed from a bare test_* to _scenario_* + _register() purely so this
# file's own dynamic-registration loop (mirroring microtest.py's test_* discovery-by-globals()
# convention, the only parametrization mechanism available without a real pytest) can generate
# `test_<name>_<device>` for every device from one shared body.
# ---------------------------------------------------------------------------

_SCENARIOS: "list[tuple[str, Callable[[str], Coroutine[Any, Any, None]], float]]" = []


def _register(name: str, timeout_s: float) -> "Callable[[Callable[[str], Coroutine[Any, Any, None]]], Callable[[str], Coroutine[Any, Any, None]]]":
    def deco(fn: "Callable[[str], Coroutine[Any, Any, None]]") -> "Callable[[str], Coroutine[Any, Any, None]]":
        _SCENARIOS.append((name, fn, timeout_s))
        return fn

    return deco


@_register("n_healthy_concurrent_connections_up_to_max_connections_all_succeed", 15.0)
async def _scenario_n_healthy_up_to_max(device: str) -> None:
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        # 4 matches WebserverService's own real max_connections default
        # (src/asy_webserver_service.py) - every one of these must be admitted, not rejected.
        results = await asyncio.gather(*(_healthy_request("127.0.0.1", port) for _ in range(4)))
        assert results.count(200) == 4, results
    finally:
        await _cancel(task)


@_register("connections_beyond_max_connections_are_rejected_cleanly_not_crashed", 20.0)
async def _scenario_beyond_max_rejected_cleanly(device: str) -> None:
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:

        async def one() -> "int | str":
            try:
                return await _healthy_request("127.0.0.1", port)
            except OSError:
                return "rejected"  # the documented reject-when-full outcome - a clean reset,
                # not an exception this test should treat as a real failure.

        results = await asyncio.gather(*(one() for _ in range(8)))
        # max_connections bounds how many are open *at once*, not the total resolved across
        # this whole burst - against a fast local server, an early connection can finish and
        # free its slot before a later one even arrives, so more than max_connections can
        # legitimately succeed in total (confirmed directly: a real run here saw 6/8 succeed).
        # What's actually guaranteed: at least one succeeds, at least one instance of the
        # documented reject-when-full outcome is possible under a big enough burst (not
        # asserted as a strict must-happen-every-run, since it's timing-dependent), and nothing
        # else leaks out.
        assert results.count(200) >= 1, results
        assert all(r in (200, "rejected") for r in results), results  # nothing else - no
        # unexpected exception type leaked out of any of the 8 concurrent attempts
        assert await _still_serving("127.0.0.1", port)  # the actual regression this test
        # guards: the server itself must still be healthy after a full-then-overflowing burst,
        # not just that each individual request resolved one way or the other
    finally:
        await _cancel(task)


@_register("mixed_healthy_and_flaky_connections_dont_wedge_the_server", 15.0)
async def _scenario_mixed_healthy_and_flaky(device: str) -> None:
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        healthy = [_healthy_request("127.0.0.1", port) for _ in range(2)]
        flaky = [_flaky_connection("127.0.0.1", port) for _ in range(2)]
        results = await asyncio.gather(*healthy, *flaky, return_exceptions=True)
        healthy_results = results[: len(healthy)]
        assert all(r == 200 for r in healthy_results), results  # the healthy requests must
        # succeed regardless of the flaky ones sharing the same connection-count ceiling
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("all_flaky_connections_dont_wedge_the_server", 15.0)
async def _scenario_all_flaky(device: str) -> None:
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        await asyncio.gather(*(_flaky_connection("127.0.0.1", port) for _ in range(4)), return_exceptions=True)
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("high_concurrency_burst_at_historical_segfault_repro_scale_survives", 60.0)
async def _scenario_high_concurrency_burst(device: str) -> None:
    # digital_twin/run_generic_integration.py's own soak-section comment records a real, real-user-
    # reported segfault found by firing 8+ concurrent clients against the real assembled system -
    # root-caused and fixed via digital_twin/unix_port_poll_prewarm.py's raised poll-array ceiling
    # (digital_twin/README.md's "Known gaps" section). This test deliberately revisits that exact
    # scale, repeated, as an in-process regression check: a recurrence of that dangling-pointer
    # class of bug corrupts process memory and crashes the whole interpreter, which would fail this
    # test file loudly (scripts/test.sh's per-file timeout+retry backstop), not silently pass.
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        for _ in range(5):  # repeated bursts, not just one - the original bug was a race,
            # not a deterministic every-time failure

            async def one() -> "int | str":
                try:
                    return await _healthy_request("127.0.0.1", port)
                except OSError:
                    return "rejected"

            results = await asyncio.gather(*(one() for _ in range(12)))
            assert all(r in (200, "rejected") for r in results), results
            assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("connections_at_each_count_from_one_to_max_connections_all_succeed", 20.0)
async def _scenario_each_count_up_to_max(device: str) -> None:
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        for n in range(1, 5):  # 1..max_connections=4 inclusive - every count in this range
            # must be admitted in full, not just the exact ceiling (already covered above).
            results = await asyncio.gather(*(_healthy_request("127.0.0.1", port) for _ in range(n)))
            assert results.count(200) == n, (n, results)
            # A brief settle delay between rounds - the same real, benign timing window
            # _still_serving()'s own docstring already documents: without it, a round's own
            # connections can still be mid-close (_close_writer()'s own wait_closed()) when the
            # next round's burst arrives, transiently making max_connections' slots look fuller
            # than they really are and reset one of the next round's own connections.
            await asyncio.sleep(0.2)
    finally:
        await _cancel(task)


@_register("above_max_connections_mixed_healthy_and_flaky_at_least_one_healthy_succeeds", 20.0)
async def _scenario_above_max_mixed(device: str) -> None:
    # test_mixed_healthy_and_flaky_connections_dont_wedge_the_server above only exercises exactly
    # max_connections total (2 healthy + 2 flaky = 4) - this is genuinely above it (4 + 4 = 8).
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        healthy = [_healthy_request("127.0.0.1", port) for _ in range(4)]
        flaky = [_flaky_connection("127.0.0.1", port) for _ in range(4)]
        results = await asyncio.gather(*healthy, *flaky, return_exceptions=True)
        healthy_results = results[: len(healthy)]
        assert healthy_results.count(200) >= 1, results  # not every healthy attempt is
        # guaranteed a slot above the ceiling, but at least one must get through
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("above_max_connections_all_flaky_survives", 20.0)
async def _scenario_above_max_all_flaky(device: str) -> None:
    # test_all_flaky_connections_dont_wedge_the_server above only exercises exactly max_connections
    # (4) flaky connections - this is genuinely above it (8, double the ceiling).
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        await asyncio.gather(*(_flaky_connection("127.0.0.1", port) for _ in range(8)), return_exceptions=True)
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("connection_count_fluctuating_in_real_time_server_stays_healthy", 30.0)
async def _scenario_fluctuating_real_time(device: str) -> None:
    # Every burst test above fires its whole batch at once - real traffic doesn't arrive in
    # lockstep. This staggers healthy and flaky connection attempts over a real wall-clock window
    # and checks the server's health *during* the fluctuation via a concurrent health-check loop,
    # not just once at the end.
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        results: list[int | str] = []

        async def staggered_healthy(delay_s: float) -> None:
            await asyncio.sleep(delay_s)
            try:
                results.append(await _healthy_request("127.0.0.1", port))
            except OSError:
                results.append("rejected")

        async def staggered_flaky(delay_s: float) -> None:
            await asyncio.sleep(delay_s)
            await _flaky_connection("127.0.0.1", port)

        waves = []
        for i in range(6):
            delay = i * 0.15
            shape = i % 3
            if shape == 2:
                waves.append(staggered_healthy(delay))
                waves.append(staggered_flaky(delay + 0.02))
            elif shape == 1:
                waves.append(staggered_flaky(delay))
            else:
                waves.append(staggered_healthy(delay))

        async def health_checks() -> None:
            for _ in range(4):
                await asyncio.sleep(0.25)
                assert await _still_serving("127.0.0.1", port, timeout_s=3.0)

        await asyncio.gather(*waves, health_checks())
        assert results.count(200) >= 1, results
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("existing_connections_survive_an_overflow_burst_untouched", 20.0)
async def _scenario_existing_survive_overflow(device: str) -> None:
    # The project owner's own stated expectation: exceeding max_connections rejects only the new
    # arrival, never resets or disturbs an already-open connection. Confirmed correct by reading
    # _serve()/_open_conns directly (no behavior change needed) - this is the dedicated proof.
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        # Two legitimately slow (but healthy) connections occupy 2 of max_connections=4's own
        # slots for a real wall-clock window - long enough for a concurrent overflow burst to
        # land while they're still in flight.
        evtloop = asyncio.get_event_loop()
        slow = [evtloop.create_task(_slow_but_healthy_put("127.0.0.1", port, 1.0)) for _ in range(2)]
        await asyncio.sleep(0.3)  # let both slow connections actually open and start reading

        async def one() -> "int | str":
            try:
                return await _healthy_request("127.0.0.1", port)
            except OSError:
                return "rejected"

        # 6 more concurrent attempts while the 2 slow ones are still open - above the remaining
        # headroom (4 - 2 = 2 free slots), so at least one of these must be rejected, not
        # silently dropped and not a crash of either already-in-flight slow connection.
        overflow_results = await asyncio.gather(*(one() for _ in range(6)))
        assert overflow_results.count("rejected") >= 1, overflow_results

        slow_results = await asyncio.gather(*slow)
        # The actual point of this test: neither pre-existing slow connection was disturbed by
        # the overflow burst landing mid-flight - both still complete normally with a real 200.
        assert slow_results == [200, 200], slow_results
    finally:
        await _cancel(task)


@_register("a_slot_freed_by_a_stale_connections_timeout_accepts_a_new_connection", 30.0)
async def _scenario_stale_slot_reclaimed(device: str) -> None:
    # Real production wiring's own outer_cap_s default (15.0s - every generated sensortask_<device>
    # module's own WebserverService(...) call has no override) - genuinely waits out a real reclaim
    # rather than asserting the mechanism only against a short test-only timeout (already covered
    # in-process, against a short timeout, by tests/test_asy_webserver_service.py's own F.1 test).
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        # Fill every slot with a connection that opens but never sends anything - the
        # "Slowloris-shaped" gap _flaky_connection() itself doesn't quite cover (it does send a
        # partial request line) - these are reclaimed by outer_cap_s, not a per-call timeout.
        hanging = []
        for _ in range(4):
            _reader, writer = await asyncio.open_connection("127.0.0.1", port)
            hanging.append(writer)
        await asyncio.sleep(0.2)

        # Every slot is genuinely full right now - a fresh attempt must be rejected.
        try:
            immediate: int | str = await _healthy_request("127.0.0.1", port)
        except OSError:
            immediate = "rejected"
        assert immediate == "rejected", immediate

        # Once outer_cap_s elapses, the server reclaims all four - _still_serving() already
        # retries for up to its own timeout_s budget, which comfortably covers that reclaim.
        assert await _still_serving("127.0.0.1", port, timeout_s=20.0)
    finally:
        for writer in hanging:
            writer.close()
            await writer.wait_closed()
        await _cancel(task)


@_register("multiple_browser_like_sessions_concurrently_all_succeed", 20.0)
async def _scenario_multiple_browser_sessions(device: str) -> None:
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        # Two browser tabs open at once - 2 connections each, 4 total, exactly max_connections.
        results = await asyncio.gather(_browser_page_load("127.0.0.1", port), _browser_page_load("127.0.0.1", port))
        for page_results in results:
            assert page_results == [200, 200], results
    finally:
        await _cancel(task)


@_register("realistic_mixed_openhab_polling_and_browser_session_concurrently", 20.0)
async def _scenario_openhab_and_browser(device: str) -> None:
    # The project owner's own named example: an OpenHAB instance polling two endpoints alongside a
    # website open for manual sensor calibration - 2 + 2 = 4, exactly max_connections, all must
    # succeed cleanly together.
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        browser, openhab = await asyncio.gather(
            _browser_page_load("127.0.0.1", port),
            _openhab_poll("127.0.0.1", port),
        )
        assert browser == [200, 200], browser
        assert openhab == [200, 200], openhab
    finally:
        await _cancel(task)


@_register("realistic_mixed_polling_and_a_concurrent_real_config_write", 20.0)
async def _scenario_polling_and_config_write(device: str) -> None:
    # Same OpenHAB-polling mix as above, with a real config write landing concurrently - proves the
    # combined GET+write shape stays healthy against the real, fully assembled twin system
    # (ConfigManager's own asyncio.Lock already rules out a data race - SPECIFICATION.md Part C.7 -
    # this is about the same "stays healthy under this traffic shape" concern the GET-only tests
    # above already check, now with a real writer in the mix too). Exactly max_connections=4 at
    # once (2 polling GETs + 2 writes), same "all must succeed cleanly" bar as
    # _scenario_n_healthy_up_to_max above - not pushed past the ceiling, since that's a different,
    # already-covered concern (_scenario_mixed_traffic_above_ceiling below).
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:

        async def _writes() -> "list[int]":
            return list(
                await asyncio.gather(_real_config_write("127.0.0.1", port, 5), _real_config_write("127.0.0.1", port, 6)),
            )

        openhab_result, write_results = await asyncio.gather(_openhab_poll("127.0.0.1", port), _writes())
        assert openhab_result == [200, 200], openhab_result
        assert write_results == [200, 200], write_results
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("realistic_mixed_traffic_above_the_connection_ceiling_degrades_gracefully", 20.0)
async def _scenario_mixed_traffic_above_ceiling(device: str) -> None:
    # Same mix as above, pushed past max_connections=4: a second browser tab opens while OpenHAB is
    # already polling and the first tab is still loading - 6 connections at once against a ceiling
    # of 4. Some individual GETs may see a rejected connection, but nothing must crash or wedge.
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:

        async def _get_tolerant(path: str) -> "int | str":
            try:
                res = await _http_client.fetch("127.0.0.1", port, "GET", path)
            except OSError:
                return "rejected"
            else:
                return res.status_code

        async def page_load_tolerant() -> "list[int | str]":
            return list(await asyncio.gather(_get_tolerant("/"), _get_tolerant("/style.css")))

        async def poll_tolerant() -> "list[int | str]":
            return list(await asyncio.gather(_get_tolerant("/measurements"), _get_tolerant("/status")))

        results = await asyncio.gather(page_load_tolerant(), page_load_tolerant(), poll_tolerant())
        flat = [r for group in results for r in group]
        assert flat.count(200) >= 1, flat
        assert all(r in (200, "rejected") for r in flat), flat
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


# ---------------------------------------------------------------------------
# Registration: one test_<scenario>_<device> per (scenario, device) pair - microtest.py discovers
# every callable in globals() named test_*, the only parametrization mechanism available here
# (no real pytest on MicroPython - SPECIFICATION.md Part E.1). fn/device/timeout are bound as
# default-argument values, not read from the loop variable, since a closure over a `for` loop's own
# variable would otherwise have every generated test share the SAME (last-iteration) device/fn.
#
# gc.collect() after every one of the 90 (15 scenarios x 6 devices) real object-graph builds this
# file now does in one process (previously just 15, one per scenario, all against the same
# already-imported sensortask_wozi module) - a real MemoryError was found without it (dev's 256KB
# FRAM chip fake failing to allocate on test ~70-something) once every device's own build_system()
# accumulated enough discarded-but-uncollected garbage across the run. MicroPython's own
# gc.threshold(32768)-triggered automatic collection alone wasn't enough to keep pace with this
# file's own before-under-test object churn at this new, much higher call volume - confirmed
# directly: adding this one explicit collect() after each test resolved it with room to spare
# (measured well under scripts/test.sh's own 180s per-file timeout).
# ---------------------------------------------------------------------------

for _scenario_name, _scenario_fn, _scenario_timeout in _SCENARIOS:
    for _device in _DEVICES:

        def _make_test(
            fn: "Callable[[str], Coroutine[Any, Any, None]]" = _scenario_fn,
            device: str = _device,
            timeout_s: float = _scenario_timeout,
        ) -> "Callable[[], None]":
            def test() -> None:
                try:
                    run_timed(fn(device), timeout_s=timeout_s)
                finally:
                    gc.collect()

            return test

        globals()[f"test_{_scenario_name}_{_device}"] = _make_test()


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
