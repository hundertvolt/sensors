"""Shared scenario library: real-socket concurrent-connection coverage for WebserverService over
the real digital_twin buses - genuinely concurrent TCP, unlike test_asy_webserver_service.py
Section F. Not a test file; SPECIFICATION.md Parts H.7 and E.2.1 have the rationale."""

# See SPECIFICATION.md Part H.7 and this module's own comments below for the full rationale.

# Every existing test client in this project - curl, http.client, digital_twin/_http_client.py - has always
# issued one request at a time, so nothing has ever driven more than one simultaneous real TCP connection
# against a live server; Section F drives _serve() against in-process fakes, never real accept()/poll().
#
# digital_twin/README.md's "Known gaps" records a real, already-fixed Unix-port segfault found by a user
# report firing 8+ concurrent clients. This file's high-concurrency test revisits that exact scale as a
# regression check, in-process, so a recurrence crashes this file's interpreter and fails loudly.
#
# One thing this file deliberately does NOT attempt is a "different source host" variant: _serve() makes no
# per-source-IP distinction anywhere, and the pinned Unix port's asyncio.open_connection() has no local_addr
# to bind a distinct source from regardless.
#
# Concurrent connections from one client machine and from many take literally the same path, so a second
# source IP adds no coverage - what matters, and what every test below varies, is the number of connections
# in flight and their behavior.

import asyncio
import gc
import json
import socket
import sys
import time

sys.path.insert(0, "ext")  # reaches the real, vendored ext/microdot.py - same convention as
# test_digital_twin_sensortask_integration.py's own comment.
sys.path.insert(0, "digital_twin")

import _http_client
import machine
from _tmp_scratch import TmpScratch
from microdot import Request  # type: ignore[import-not-found]

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


# Per-test config-file isolation via tests/_tmp_scratch.py - see that module's docstring for the mechanism.
# Own port range base (19700+, one 200-port block per device), distinct from the twin integration suites'
# 19100+ and 19300+.
#
# Both the scratch key and the port range are keyed per device, not shared across all 6 in one process: each
# device's tests run as their own OS process, potentially concurrently, so two must never resolve
# TmpScratch's tests/_tmp/<key>/ path - or a real localhost bind - to the same place.
_PORT_BASE_BY_DEVICE = {device: 19700 + 200 * i for i, device in enumerate(_DEVICES)}

_scratch: "TmpScratch | None" = None
_next_port = 0


def _tmp_cfg_dir() -> str:
    assert _scratch is not None, "register_for_device() must run before any scenario calls _tmp_cfg_dir()"
    return _scratch.dir()


def _next_test_port() -> int:
    global _next_port
    assert _next_port != 0, "register_for_device() must run before any scenario calls _next_test_port()"
    _next_port += 1
    return _next_port


async def _boot(port: int, device: str) -> "Any":
    # configure_wiring() first: every twin I2C/SPI construction reads the shared machine._wiring_plan global
    # (Part L.4), where the last call before construction wins - so this runs immediately before
    # build_system(), not once at import, several devices being booted in one process here.
    machine.configure_wiring(_wiring_plan(device))
    module = __import__(f"sensortask_{device}")
    await module.build_system(cfg_path=_tmp_cfg_dir(), web_host="127.0.0.1", web_port=port)
    return module


_BODY_CAP = 2048  # WebserverService's shipped max_content_length (Part I.6), stated, never read back


def _ceiling(module: "Any") -> int:
    """The admission ceiling of the build under test, read off the real service rather than
    restated - every burst below scales with it, so raising a device's own max_connections makes
    these scenarios bite harder instead of leaving them pinned at a number that used to be right."""
    assert module.webserver is not None
    ceiling: int = module.webserver._max_connections
    # The bursts below floor at 2 page loads' or OpenHAB's pair of slots: under 4 they would exceed
    # the ceiling and assert refusals away, so such a device needs scenario shapes of its own.
    assert ceiling >= 4, f"max_connections {ceiling} is below the 4 these scenarios are shaped for"
    return ceiling


def _backlog(module: "Any") -> int:
    assert module.webserver is not None
    depth: int = module.webserver._backlog
    return depth


async def _start_webserver(module: "Any") -> "asyncio.Task[None]":
    assert module.webserver is not None
    task: asyncio.Task[None] = module.webserver.get_task_starters()[0]()
    # WP1/CLAUDE.md's implicit-FRAM-wiring rule made webserver.pr real-FRAM-backed whenever the device wires
    # FRAM, so _run() now awaits a real self.pr.setup() - a real chunk read/write - before start_server(),
    # not the instant no-op a RAM-only logger's setup() was.
    #
    # A polling readiness check was tried instead and made things measurably worse: a real fetch() probe
    # broke this file's max_connections-exactness tests, its connection not reliably released before the
    # scenario opened its N, and a bare TCP connect-then-close probe broke more of them still.
    #
    # The server's connection accounting is evidently sensitive to a well-formed-but-unread connection
    # landing first, in a way a fixed sleep never triggers. So: 0.5s, recalibrated down from 1.0s (~400ms
    # typical here), keeping margin without ~15 call sites pushing past the per-file timeout.
    await asyncio.sleep(0.5)
    return task


async def _cancel(task: "asyncio.Task[Any]") -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _healthy_request(host: str, port: int, path: str = "/measurements") -> int:
    # read_body=False throughout this file wherever only the status is read: an in-process client
    # that materializes a body it never looks at competes with the DUT for the same heap, which is
    # the regression fetch()'s drain siblings were added for (Part E.9, test_digital_twin_http_client.py).
    res = await _http_client.fetch(host, port, "GET", path, read_body=False)
    return res.status_code


async def _flaky_connection(host: str, port: int) -> None:
    """Opens a real connection, sends a deliberately incomplete request (no terminating blank line,
    no Host header), then disconnects - the same EOFError/timeout reclaim path a lossy network or a
    killed browser tab triggers (WebserverService._serve())."""
    _reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(b"GET / HTTP/1.1\r\n")
        await writer.drain()
        await asyncio.sleep(0.05)  # give the server a moment to actually start reading it
    finally:
        writer.close()
        await writer.wait_closed()


async def _still_serving(host: str, port: int, timeout_s: float = 5.0) -> bool:
    # Retried, not single-shot: right after a connection burst, a still-draining prior connection can
    # transiently leave max_connections' slots looking full - a real, benign timing window, not a wedged
    # server. Only a sustained failure across this whole budget means that.
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


async def _drained(module: "Any", timeout_s: float = 10.0) -> bool:
    """Waits for the service's own admission counter to return to zero, and reports whether it did.
    A slot is released in _serve()'s finally, AFTER the close is awaited, so it outlives the response
    the client already holds (Part H.7.1) - a burst demanding the full ceiling has to start from zero."""
    assert module.webserver is not None
    start = time.ticks_ms()
    while True:
        if (await module.webserver._open_conns.get_value() or 0) == 0:
            return True
        if time.ticks_diff(time.ticks_ms(), start) >= timeout_s * 1000:
            return False
        await asyncio.sleep(0.05)


async def _browser_page_load(host: str, port: int) -> "list[int]":
    """One browser tab's page-load burst: two concurrent GETs, the real post-inlining footprint
    (SPECIFICATION.md Part H.7). Served from the default html_stub mount, not the real website -
    this file is about connection count and timing, not content."""

    async def _get(path: str) -> int:
        res = await _http_client.fetch(host, port, "GET", path, read_body=False)
        return res.status_code

    return list(await asyncio.gather(_get("/"), _get("/style.css")))


async def _openhab_poll(host: str, port: int) -> "list[int]":
    """Simulates one OpenHAB polling cycle: two concurrent GETs against two real REST endpoints -
    the project owner's own named example, matching how a real binding polls several channels at
    once rather than one at a time."""

    async def _get(path: str) -> int:
        res = await _http_client.fetch(host, port, "GET", path, read_body=False)
        return res.status_code

    return list(await asyncio.gather(_get("/measurements"), _get("/status")))


async def _slow_but_healthy_put(host: str, port: int, delay_s: float) -> int:
    """A legitimate, harmless PUT (empty /system body - a real no-op, SPECIFICATION.md Part A.8)
    trickled in two halves, so it stays genuinely in flight for `delay_s` - unlike
    _flaky_connection(), which never completes at all. Proves a slow connection survives a burst."""
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
    """A real config write reaching ConfigManager.write_config() through the real object graph
    (SCD30 is on every device, Part L.3) - unlike _slow_but_healthy_put()'s no-op above. Proves
    concurrent GET polling survives a real write; bench and unit equivalents exist per tier."""
    res = await _http_client.fetch(host, port, "PUT", "/sensors", {"SCD30": {"Interval": interval}}, read_body=False)
    return res.status_code


# ---------------------------------------------------------------------------
# Scenario bodies - one per distinct concurrency shape, each parametrized by `device` and registered per
# real device below, rather than 6 hand-duplicated copies. Named _scenario_* rather than test_* purely so
# the registration loop can generate `test_<name>_<device>` from one shared body.
#
# No scenario has a device-specific assertion - WebserverService's accept/reject machinery is identical
# whichever sensors a device has - so generalizing needed no assertion rework at all.
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
        # The build's own ceiling, not a restated 4: every one of these must be admitted, never
        # rejected, however high the device's max_connections has been raised.
        ceiling = _ceiling(module)
        results = await asyncio.gather(*(_healthy_request("127.0.0.1", port) for _ in range(ceiling)))
        assert results.count(200) == ceiling, (ceiling, results)
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

        results = await asyncio.gather(*(one() for _ in range(_ceiling(module) * 2)))
        # max_connections bounds how many are open at once, not the total resolved across the whole burst:
        # against a fast local server an early connection can finish and free its slot before a later one
        # arrives, so more than max_connections can legitimately succeed in total (a real run here saw 6/8).
        #
        # What is guaranteed: at least one succeeds, at least one instance of the documented reject-when-
        # full outcome is possible under a big enough burst (not asserted as must-happen, being timing-
        # dependent), and nothing else leaks out.
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
        ceiling = _ceiling(module)
        healthy = [_healthy_request("127.0.0.1", port) for _ in range(ceiling - ceiling // 2)]
        flaky = [_flaky_connection("127.0.0.1", port) for _ in range(ceiling // 2)]
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
        await asyncio.gather(*(_flaky_connection("127.0.0.1", port) for _ in range(_ceiling(module))), return_exceptions=True)
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("high_concurrency_burst_at_historical_segfault_repro_scale_survives", 60.0)
async def _scenario_high_concurrency_burst(device: str) -> None:
    # digital_twin/run_generic_integration.py's soak-section comment records a real, user-reported segfault
    # found by firing 8+ concurrent clients at the real assembled system, root-caused and fixed via
    # unix_port_poll_prewarm.py's raised poll-array ceiling.
    #
    # This deliberately revisits that exact scale, repeated, as an in-process regression check: a recurrence
    # of that dangling-pointer class of bug corrupts process memory and crashes the whole interpreter,
    # failing this file loudly under scripts/test.sh's timeout+retry rather than silently passing.
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

            results = await asyncio.gather(*(one() for _ in range(max(12, _ceiling(module) * 3))))
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
        for n in range(1, _ceiling(module) + 1):  # every count up to the build's own ceiling
            # must be admitted in full, not just the exact ceiling (already covered above).
            results = await asyncio.gather(*(_healthy_request("127.0.0.1", port) for _ in range(n)))
            assert results.count(200) == n, (n, results)
            # Each round from zero: a slot outlives its response until the close completes, so a fixed
            # settle could still leave the next round's full ceiling one slot short under load.
            assert await _drained(module), f"round {n}'s connections never released their slots"
    finally:
        await _cancel(task)


@_register("above_max_connections_mixed_healthy_and_flaky_at_least_one_healthy_succeeds", 20.0)
async def _scenario_above_max_mixed(device: str) -> None:
    # test_mixed_healthy_and_flaky_connections_dont_wedge_the_server above only exercises exactly
    # the ceiling - this is genuinely above it, one full ceiling of each kind.
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        ceiling = _ceiling(module)
        healthy = [_healthy_request("127.0.0.1", port) for _ in range(ceiling)]
        flaky = [_flaky_connection("127.0.0.1", port) for _ in range(ceiling)]
        results = await asyncio.gather(*healthy, *flaky, return_exceptions=True)
        healthy_results = results[: len(healthy)]
        assert healthy_results.count(200) >= 1, results  # not every healthy attempt is
        # guaranteed a slot above the ceiling, but at least one must get through
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("above_max_connections_all_flaky_survives", 20.0)
async def _scenario_above_max_all_flaky(device: str) -> None:
    # test_all_flaky_connections_dont_wedge_the_server above only exercises exactly the ceiling's
    # worth of flaky connections - this is genuinely above it, double.
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        await asyncio.gather(*(_flaky_connection("127.0.0.1", port) for _ in range(_ceiling(module) * 2)), return_exceptions=True)
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("connection_count_fluctuating_in_real_time_server_stays_healthy", 30.0)
async def _scenario_fluctuating_real_time(device: str) -> None:
    # Every burst test above fires its whole batch at once, and real traffic does not arrive in lockstep.
    # This staggers healthy and flaky attempts over a real wall-clock window and checks the server's health
    # during the fluctuation, via a concurrent health-check loop, not just once at the end.
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
        # Half the ceiling's slots held by legitimately slow (but healthy) connections for a real
        # wall-clock window - long enough for a concurrent overflow burst to land mid-flight.
        ceiling = _ceiling(module)
        slow_count = max(2, ceiling // 2)
        evtloop = asyncio.get_event_loop()
        slow = [evtloop.create_task(_slow_but_healthy_put("127.0.0.1", port, 1.0)) for _ in range(slow_count)]
        await asyncio.sleep(0.3)  # let both slow connections actually open and start reading

        async def one() -> "int | str":
            try:
                return await _healthy_request("127.0.0.1", port)
            except OSError:
                return "rejected"

        # Enough concurrent attempts to exceed the remaining headroom by a full ceiling, so at
        # least one must be rejected - not silently dropped, and not a crash of a slow connection.
        overflow_results = await asyncio.gather(*(one() for _ in range(ceiling - slow_count + ceiling)))
        assert overflow_results.count("rejected") >= 1, overflow_results

        slow_results = await asyncio.gather(*slow)
        # The actual point of this test: no pre-existing slow connection was disturbed by the
        # overflow burst landing mid-flight - every one still completes normally with a real 200.
        assert slow_results == [200] * slow_count, slow_results
    finally:
        await _cancel(task)


@_register("a_slot_freed_by_a_stale_connections_timeout_accepts_a_new_connection", 30.0)
async def _scenario_stale_slot_reclaimed(device: str) -> None:
    # Real production wiring's own outer_cap_s default (15.0s - no generated device module overrides it),
    # genuinely waiting out a real reclaim rather than asserting the mechanism only against a short test-
    # only timeout, which test_asy_webserver_service.py's F.1 test already covers in-process.
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        # Fill every slot with a connection that opens but never sends anything - the
        # "Slowloris-shaped" gap _flaky_connection() itself doesn't quite cover (it does send a
        # partial request line) - these are reclaimed by outer_cap_s, not a per-call timeout.
        hanging = []
        for _ in range(_ceiling(module)):
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
        # As many browser tabs at once as the ceiling admits - 2 connections each (the real
        # post-bundling page-load footprint, Part H.7), so the whole ceiling is genuinely in use.
        tabs = max(2, _ceiling(module) // 2)
        results = await asyncio.gather(*(_browser_page_load("127.0.0.1", port) for _ in range(tabs)))
        for page_results in results:
            assert page_results == [200, 200], results
    finally:
        await _cancel(task)


@_register("realistic_mixed_openhab_polling_and_browser_session_concurrently", 20.0)
async def _scenario_openhab_and_browser(device: str) -> None:
    # The project owner's own named example: an OpenHAB instance polling two endpoints alongside
    # open website tabs for manual sensor calibration, filling the whole ceiling - all must succeed
    # cleanly together, however high that ceiling has been raised.
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:
        tabs = max(1, _ceiling(module) // 2 - 1)  # 2 connections each, beside OpenHAB's own 2
        gathered = await asyncio.gather(
            *(_browser_page_load("127.0.0.1", port) for _ in range(tabs)),
            _openhab_poll("127.0.0.1", port),
        )
        for page_results in gathered:
            assert page_results == [200, 200], gathered
    finally:
        await _cancel(task)


@_register("realistic_mixed_polling_and_a_concurrent_real_config_write", 20.0)
async def _scenario_polling_and_config_write(device: str) -> None:
    # The same OpenHAB-polling mix as above with a real config write landing concurrently, proving the
    # GET+write shape stays healthy against the real assembled twin. ConfigManager's asyncio.Lock rules out
    # a data race (Part C.7); this is the "stays healthy" concern, now with a writer present.
    #
    # Exactly the ceiling at once (2 polling GETs plus writes filling the rest), the same "all must succeed
    # cleanly" bar as the up-to-max scenario - not pushed past it, which is a separate, covered concern.
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:

        writes = max(2, _ceiling(module) - 2)  # the slots OpenHAB's own pair of GETs leaves free

        async def _writes() -> "list[int]":
            return list(await asyncio.gather(*(_real_config_write("127.0.0.1", port, 5 + i) for i in range(writes))))

        openhab_result, write_results = await asyncio.gather(_openhab_poll("127.0.0.1", port), _writes())
        assert openhab_result == [200, 200], openhab_result
        assert write_results == [200] * writes, write_results
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("realistic_mixed_traffic_above_the_connection_ceiling_degrades_gracefully", 20.0)
async def _scenario_mixed_traffic_above_ceiling(device: str) -> None:
    # Same mix as above, pushed past the ceiling: more tabs open than it admits while OpenHAB is
    # already polling. Some individual GETs may see a rejected connection, but nothing must crash
    # or wedge, and the burst scales with whatever the build under test admits.
    port = _next_test_port()
    module = await _boot(port, device)
    task = await _start_webserver(module)
    try:

        async def _get_tolerant(path: str) -> "int | str":
            try:
                res = await _http_client.fetch("127.0.0.1", port, "GET", path, read_body=False)
            except OSError:
                return "rejected"
            else:
                return res.status_code

        async def page_load_tolerant() -> "list[int | str]":
            return list(await asyncio.gather(_get_tolerant("/"), _get_tolerant("/style.css")))

        async def poll_tolerant() -> "list[int | str]":
            return list(await asyncio.gather(_get_tolerant("/measurements"), _get_tolerant("/status")))

        tabs = _ceiling(module) // 2 + 1  # one tab's worth past the ceiling, beside OpenHAB's own 2
        results = await asyncio.gather(*(page_load_tolerant() for _ in range(tabs)), poll_tolerant())
        flat = [r for group in results for r in group]
        assert flat.count(200) >= 1, flat
        assert all(r in (200, "rejected") for r in flat), flat
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("every_admitted_connection_is_actually_served_a_complete_correct_response", 40.0)
async def _scenario_all_admitted_are_really_served(device: str) -> None:
    # Admission is not service. A ceiling the stack can accept but not push produces 200s with
    # truncated bodies, or responses that arrive minutes late - both of which "count(200) == N"
    # would pass. This asserts the whole ceiling's worth of REAL work completes, intact and bounded.
    port = _next_test_port()
    module = await _boot(port, device)
    ceiling = _ceiling(module)
    task = await _start_webserver(module)
    try:
        # The heaviest real endpoints, not the cheapest - /sensors and /status both grow with the
        # device's own module count and are the two that stream (Part I.3).
        paths = ("/sensors", "/status", "/measurements", "/networking", "/system")

        async def one(path: str) -> "tuple[str, int, int, object]":
            started = time.ticks_ms()
            res = await _http_client.fetch("127.0.0.1", port, "GET", path)
            return path, res.status_code, time.ticks_diff(time.ticks_ms(), started), res.json()

        # Three rounds at the full ceiling, so a leaked slot or a pool that only fills over time
        # shows up rather than passing on a single cold burst. Each starts from a real zero, which
        # is asserted rather than slept for - a slot that never comes back fails here, not later.
        for round_index in range(3):
            assert await _drained(module), f"round {round_index}: the previous round's slots never came back"
            results = await asyncio.gather(*(one(paths[i % len(paths)]) for i in range(ceiling)))
            assert len(results) == ceiling, (round_index, results)
            for path, status, elapsed_ms, body in results:
                assert status == 200, (round_index, path, status)
                # Complete and correct, not merely non-empty: a truncated stream still parses as a
                # 200 with a short body, and this is the shape _stream_dict_response() produces.
                assert isinstance(body, dict) and body, (round_index, path, body)
                assert elapsed_ms < 10000, f"round {round_index}: {path} took {elapsed_ms}ms - admitted but not served in any useful time"
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("a_full_ceiling_of_real_page_loads_is_served_without_truncation", 40.0)
async def _scenario_all_admitted_page_loads_complete(device: str) -> None:
    # The static path has its own failure mode the JSON routes do not: ext/microdot.py streams a
    # file in send_file_buffer_size chunks, so a stack that runs out of buffers mid-response
    # truncates rather than failing. Every tab must get byte-identical content.
    port = _next_test_port()
    module = await _boot(port, device)
    ceiling = _ceiling(module)
    task = await _start_webserver(module)
    try:
        tabs = max(2, ceiling // 2)  # 2 connections per page load, the real post-inlining footprint

        async def _index() -> bytes:
            res = await _http_client.fetch("127.0.0.1", port, "GET", "/")
            assert res.status_code == 200, res.status_code
            return bytes(res.body)

        # One uncontended load first, as the reference body - the strongest truncation check
        # there is, and mount-independent (the stub page and the real website differ by ~25x).
        reference = await _index()
        assert len(reference) > 0, len(reference)
        assert await _drained(module), "the reference load's own slot never came back"
        # The index twice per tab rather than index + a named asset: which assets exist depends on
        # whether the stub or the real (inlined) website is mounted, and the hazard under test is
        # concurrent streaming of one file, which this exercises directly either way.
        bodies = await asyncio.gather(*(_index() for _ in range(tabs * 2)))
        sizes = [len(body) for body in bodies]
        assert set(bodies) == {reference}, f"a concurrent page load differs - uncontended it is {len(reference)} bytes, under load {sizes}"
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


@_register("the_accept_queue_is_never_shallower_than_the_admission_ceiling", 20.0)
async def _scenario_backlog_covers_the_ceiling(device: str) -> None:
    # backlog only matters while the event loop is busy: arrivals then wait in the accept queue, and
    # past it the stack drops them. So the burst lands while the loop is stalled on purpose, and a
    # whole ceiling of it has to reach _serve() within one SYN retry (1 s on Linux) of the stall.
    port = _next_test_port()
    module = await _boot(port, device)
    ceiling = _ceiling(module)
    assert _backlog(module) >= ceiling, (_backlog(module), ceiling)
    task = await _start_webserver(module)
    clients = []
    try:
        assert await _still_serving("127.0.0.1", port)
        assert await _drained(module), "the readiness probe's slot never came back"
        addr = socket.getaddrinfo("127.0.0.1", port)[0][-1]
        for _ in range(ceiling):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            clients.append(client)
            client.setblocking(False)
            try:
                client.connect(addr)
            except OSError:
                pass  # EINPROGRESS: the kernel finishes the handshake while the loop is stalled
        time.sleep_ms(200)  # the stall: no await, so nothing is accepted until it ends
        await asyncio.sleep(0.5)
        reached = await module.webserver._open_conns.get_value()
        assert reached == ceiling, f"{reached} of a {ceiling}-arrival burst reached _serve() - the rest waited out a dropped SYN"
    finally:
        for client in clients:
            client.close()
        await _cancel(task)
    assert await _drained(module), "the burst's slots never came back"


@_register("a_connection_still_closing_holds_its_slot_after_its_client_has_the_whole_response", 30.0)
async def _scenario_closing_connection_holds_its_slot(device: str) -> None:
    # Settled, pinned at each device's own ceiling (SPECIFICATION.md H.7): a slot is freed only once
    # _close_writer() returns, while the closing connection still holds heap and a pcb. Changes with
    # test_asy_webserver_service.py's F1 twin of it, never alone.
    port = _next_test_port()
    module = await _boot(port, device)
    ceiling = _ceiling(module)
    service = module.webserver
    gate = asyncio.Event()
    real_close_writer = service._close_writer

    async def close_then_linger(writer: "Any") -> None:
        await real_close_writer(writer)  # the client sees its FIN, so a streamed body ends normally
        await gate.wait()  # ...but the close is not finished as far as the slot is concerned

    service._close_writer = close_then_linger  # type: ignore[method-assign]
    task = await _start_webserver(module)
    try:
        assert await _drained(module)
        results = await asyncio.gather(*(_http_client.fetch("127.0.0.1", port, "GET", "/status") for _ in range(ceiling)))
        for res in results:
            assert res.status_code == 200, res.status_code
            assert isinstance(res.json(), dict) and res.json(), "every client holds its complete response"
        held = await service._open_conns.get_value()
        assert held == ceiling, f"every response is out but no close has finished; all {ceiling} slots must still count, got {held}"
        try:
            beyond: int | str = await _healthy_request("127.0.0.1", port)
        except OSError:
            beyond = "rejected"
        assert beyond == "rejected", beyond
        gate.set()
        assert await _drained(module), "the slots never came back once the closes finished"
        assert await _still_serving("127.0.0.1", port)
    finally:
        gate.set()
        await _cancel(task)


@_register("a_full_ceiling_of_concurrent_request_bodies_is_answered_correctly", 30.0)
async def _scenario_simultaneous_bodies(device: str) -> None:
    # max_connections bodies can be in flight at once, each one a contiguous allocation, so the
    # simultaneous contiguous demand is max_connections x max_content_length (Part I.6) - the
    # single most likely source of a new MemoryError when the ceiling goes up.
    port = _next_test_port()
    module = await _boot(port, device)
    ceiling = _ceiling(module)
    task = await _start_webserver(module)
    try:
        results = await asyncio.gather(*(_real_config_write("127.0.0.1", port, 5 + i) for i in range(ceiling)))
        assert list(results) == [200] * ceiling, results
        # Then the same count again with bodies at the cap's own boundary: read at the cap (the
        # schema may still refuse the value), 413 one byte over - each a separate live allocation.
        assert Request.max_content_length == _BODY_CAP, Request.max_content_length
        padding = _BODY_CAP - len(json.dumps({"NTP_Host": ""}))

        async def _sized(nbytes: int) -> "int | str":
            body = {"NTP_Host": "x" * nbytes}
            try:
                res = await _http_client.fetch("127.0.0.1", port, "PUT", "/networking", body, read_body=False)
            except OSError:
                return "rejected"  # a 413 sent over a body it never read can arrive as a reset
            else:
                return res.status_code

        assert await _drained(module), "the first burst's slots never came back"
        at_cap = await asyncio.gather(*(_sized(padding) for _ in range(ceiling)))
        assert all(r not in (413, "rejected") for r in at_cap), at_cap
        assert await _drained(module), "the at-cap burst's slots never came back"
        over = await asyncio.gather(*(_sized(padding + 1) for _ in range(ceiling)))
        assert all(r in (413, "rejected") for r in over), over
        assert await _still_serving("127.0.0.1", port)
    finally:
        await _cancel(task)


# ---------------------------------------------------------------------------
# Registration: one test_<scenario> per scenario, for whichever single device the caller names -
# microtest.py discovers every callable in globals() named test_*, the only parametrization mechanism
# available here (no real pytest on MicroPython - SPECIFICATION.md Part E.1).
#
# fn and timeout are bound as default-argument values rather than read from the loop variable, or every
# generated test would share the same last-iteration fn.
#
# gc.collect() after every real object-graph build: a real MemoryError was found without it, once enough
# discarded-but-uncollected garbage accumulated across a process's run, back when one process built all 6
# devices' worth. MicroPython's own threshold-triggered collection alone could not keep pace.
#
# Kept even now that the per-device split means one process only does 15 builds rather than 90 - a proven
# defense-in-depth backstop, not the fix for anything currently broken at that smaller volume.
# ---------------------------------------------------------------------------


def register_for_device(device: str) -> "dict[str, Callable[[], None]]":
    global _scratch, _next_port
    assert device in _DEVICES, f"{device!r} is not one of this module's own real devices {_DEVICES!r}"
    _scratch = TmpScratch(f"dtcc_{device}")
    _next_port = _PORT_BASE_BY_DEVICE[device]

    tests: dict[str, Callable[[], None]] = {}
    for scenario_name, scenario_fn, scenario_timeout in _SCENARIOS:

        def _make_test(
            fn: "Callable[[str], Coroutine[Any, Any, None]]" = scenario_fn,
            timeout_s: float = scenario_timeout,
        ) -> "Callable[[], None]":
            def test() -> None:
                try:
                    run_timed(fn(device), timeout_s=timeout_s)
                finally:
                    gc.collect()

            return test

        tests[f"test_{scenario_name}"] = _make_test()
    return tests
