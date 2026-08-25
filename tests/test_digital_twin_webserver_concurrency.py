"""Real-socket concurrent-connection regression coverage for WebserverService, booted against the
real digital_twin buses - genuinely concurrent TCP connections, not
tests/test_asy_webserver_service.py Section F's in-process _serve()-against-fakes tests. See
WEBSITE_PLAN.md §10 item 5 and this module's own comments below for the full rationale."""

# Every existing test client in this project before this file (curl, Python's http.client,
# digital_twin/_http_client.py itself) has always issued exactly one request at a time, so nothing
# has ever driven more than one simultaneous real TCP connection against a live server - Section F
# above drives WebserverService._serve() directly against in-process reader/writer fakes, never the
# real accept()/select.poll() layer. digital_twin/README.md's "Known gaps" section records a real,
# already-fixed MicroPython Unix-port segfault found by a real user report firing 8+ concurrent
# clients (digital_twin/run_wozi_integration.py's own soak-section comment) - this file's own
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
import os
import sys
import time

sys.path.insert(0, "ext")  # reaches the real, vendored ext/microdot.py - same convention as
# test_digital_twin_sensortask_integration.py's own comment.
sys.path.insert(0, "digital_twin")

import _http_client  # noqa: E402
from unix_port_poll_prewarm import prewarm_poll_set  # noqa: E402
from unix_port_sigpipe_ignore import ignore_sigpipe  # noqa: E402

import sensortask_wozi  # noqa: E402

ignore_sigpipe()  # Keep-alive means a healthy test client that reads its one expected response and
# moves on (closing its own socket immediately after, per ordinary HTTP client behavior) can already
# be gone by the time the server writes a second response over the same connection - see
# digital_twin/unix_port_sigpipe_ignore.py's own module docstring for the confirmed Unix-port-only
# SIGPIPE crash this avoids. Module-level, not per-test: must run before any test in this file opens
# a real socket, and a process-wide signal disposition has no per-test scope to reset anyway.
prewarm_poll_set(port=19699)  # This file's own tests previously never needed this (confirmed crash-
# free without it, pre-keep-alive) - keep-alive means each physical connection now cycles through
# several handle_request() calls (several more asyncio.wait_for()-driven poll registrations) instead
# of just one, and this file's own high-concurrency test (test_high_concurrency_burst_at_
# historical_segfault_repro_scale_survives) pushed real, reproducible registration churn past the
# growth threshold that triggers extmod/modselect.c's dangling-pointer bug without this - confirmed
# directly via a gdb backtrace landing at poll_obj_get_revents (modselect.c:132), the exact site
# digital_twin/README.md's "Known gaps" section already documents. Port 19699 sits just below this
# file's own 19700+ per-test range (see below) so it can never collide with a real per-test port.

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


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


async def _healthy_request(host: str, port: int, path: str = "/measurements") -> int:
    res = await _http_client.fetch(host, port, "GET", path)
    return res.status_code


async def _flaky_connection(host: str, port: int) -> None:
    """Opens a real connection, sends a deliberately incomplete request (no terminating blank
    line, no Host header), then disconnects without ever completing it - exercises the same
    EOFError/timeout reclaim path a real client on a lossy network or a killed browser tab would
    trigger (WebserverService._serve(), src/asy_webserver_service.py)."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(b"GET / HTTP/1.1\r\n")
        await writer.drain()
        await asyncio.sleep(0.05)  # give the server a moment to actually start reading it
    finally:
        writer.close()
        await writer.wait_closed()


async def _keep_alive_client(host: str, port: int, paths: "list[str]") -> "list[int]":
    """Opens ONE real connection and issues every path in `paths` as a sequential GET over it,
    reusing the connection via keep-alive (never sends `Connection: close`) - the shape a real
    browser's page load or a persistent OpenHAB client actually produces, unlike
    `_http_client.fetch()`'s deliberate one-request-per-connection simplicity (see that module's
    own docstring). Reuses `_http_client`'s own status/header-line parsing rather than
    reimplementing it - only the request-writing side differs (no `Connection: close`)."""
    reader, writer = await asyncio.open_connection(host, port)
    statuses: list[int] = []
    try:
        for path in paths:
            request = f"GET {path} HTTP/1.1\r\nHost: device.local\r\nContent-Length: 0\r\n\r\n"
            writer.write(request.encode())
            await writer.drain()
            statuses.append(_http_client.parse_status_line(await reader.readline()))
            content_length = 0
            while True:
                parsed = _http_client.parse_header_line(await reader.readline())
                if parsed is None:
                    break
                if parsed[0].lower() == "content-length":
                    content_length = int(parsed[1])
            if content_length:
                await reader.readexactly(content_length)
    finally:
        writer.close()
        await writer.wait_closed()
    return statuses


async def _slow_but_healthy_put(host: str, port: int, delay_s: float) -> int:
    """Opens a real connection and sends a well-formed PUT body in two halves with a delay
    between them - a legitimate, eventually-successful request that stays genuinely open/counted
    for a controlled duration, unlike `_flaky_connection()` (never completes) or
    `_healthy_request()` (resolves near-instantly) - lets a test hold a real connection slot open
    while driving other traffic against the ceiling, to check that traffic never disturbs it."""
    body = b'{"Interval": 5}'
    header = (
        f"PUT /networking HTTP/1.1\r\nHost: device.local\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n"
    ).encode()
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(header + body[:4])
        await writer.drain()
        await asyncio.sleep(delay_s)
        writer.write(body[4:])
        await writer.drain()
        return _http_client.parse_status_line(await reader.readline())
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
        except Exception:  # noqa: BLE001 - any failure just means "not yet", keep retrying
            pass
        if time.ticks_diff(time.ticks_ms(), start) >= timeout_s * 1000:
            return False
        await asyncio.sleep(0.1)


def test_n_healthy_concurrent_connections_up_to_max_connections_all_succeed() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            # 4 matches WebserverService's own real max_connections default
            # (src/asy_webserver_service.py) - every one of these must be admitted, not rejected.
            results = await asyncio.gather(*(_healthy_request("127.0.0.1", port) for _ in range(4)))
            assert results.count(200) == 4, results
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=15.0)


def test_connections_beyond_max_connections_are_rejected_cleanly_not_crashed() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
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

    run_timed(scenario(), timeout_s=20.0)


def test_mixed_healthy_and_flaky_connections_dont_wedge_the_server() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
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

    run_timed(scenario(), timeout_s=15.0)


def test_all_flaky_connections_dont_wedge_the_server() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            await asyncio.gather(*(_flaky_connection("127.0.0.1", port) for _ in range(4)), return_exceptions=True)
            assert await _still_serving("127.0.0.1", port)
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=15.0)


def test_high_concurrency_burst_at_historical_segfault_repro_scale_survives() -> None:
    # digital_twin/run_wozi_integration.py's own soak-section comment records a real, real-user-
    # reported segfault found by firing 8+ concurrent clients against the real assembled system -
    # root-caused and fixed via digital_twin/unix_port_poll_prewarm.py's raised poll-array ceiling
    # (digital_twin/README.md's "Known gaps" section). This test deliberately revisits that exact
    # scale, repeated, as an in-process regression check: a recurrence of that dangling-pointer
    # class of bug corrupts process memory and crashes the whole interpreter, which would fail this
    # test file loudly (scripts/test.sh's per-file timeout+retry backstop), not silently pass.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
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

    run_timed(scenario(), timeout_s=60.0)


# ---------------------------------------------------------------------------
# Follow-up coverage requested directly by the project owner after reviewing the tests above: the
# 1..max sweep (not just "at max"), above-max mixed/all-flaky (not just "at max"), real-time
# connection-count churn, existing-connections-survive-overflow and stale-reclaim-frees-a-slot as
# their own dedicated real-socket checks (not just inferred from the tests above), and the
# API-only/website-only/mixed-client shapes - matching a real deployment's actual traffic (an
# OpenHAB instance polling two endpoints, a browser session open for manual calibration, per the
# project owner's own example). NTP sync is deliberately not simulated here even though the project
# owner named it as a third realistic concurrent actor: NTP traffic is UDP, never touches
# WebserverService's TCP accept()/max_connections ceiling at all, so it wouldn't add real coverage
# of the thing these tests actually exercise.
# ---------------------------------------------------------------------------


def test_connections_at_each_count_from_one_to_max_connections_all_succeed() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            assert sensortask_wozi.webserver is not None
            max_conn = sensortask_wozi.webserver._max_connections
            for n in range(1, max_conn + 1):
                results = await asyncio.gather(*(_healthy_request("127.0.0.1", port) for _ in range(n)))
                assert results.count(200) == n, (n, results)
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=20.0)


def test_above_max_connections_mixed_healthy_and_flaky_at_least_one_healthy_succeeds() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            assert sensortask_wozi.webserver is not None
            max_conn = sensortask_wozi.webserver._max_connections
            healthy = [_healthy_request("127.0.0.1", port) for _ in range(max_conn)]
            flaky = [_flaky_connection("127.0.0.1", port) for _ in range(max_conn)]
            results = await asyncio.gather(*healthy, *flaky, return_exceptions=True)
            healthy_results = results[: len(healthy)]
            assert any(r == 200 for r in healthy_results), results  # unlike the at-ceiling mixed
            # test above, an above-ceiling burst can legitimately reject some healthy attempts too -
            # what's guaranteed is that the flaky half never starves every healthy one
            assert await _still_serving("127.0.0.1", port)
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=20.0)


def test_above_max_connections_all_flaky_survives() -> None:
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            assert sensortask_wozi.webserver is not None
            max_conn = sensortask_wozi.webserver._max_connections
            await asyncio.gather(*(_flaky_connection("127.0.0.1", port) for _ in range(max_conn * 2)), return_exceptions=True)
            assert await _still_serving("127.0.0.1", port)
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=20.0)


def test_connection_count_fluctuating_in_real_time_server_stays_healthy() -> None:
    # Real traffic doesn't arrive in neat, fixed-size batches - this drives a continuously varying
    # mix of burst shapes (small healthy, mixed-with-flaky, above-ceiling) back to back for a real
    # wall-clock window, checking server health throughout rather than only at fixed checkpoints.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            deadline = time.ticks_add(time.ticks_ms(), 3000)
            round_num = 0
            while time.ticks_diff(deadline, time.ticks_ms()) > 0:
                shape = round_num % 3
                if shape == 0:
                    await asyncio.gather(
                        *(_healthy_request("127.0.0.1", port) for _ in range(2)), return_exceptions=True
                    )
                elif shape == 1:
                    await asyncio.gather(
                        *(_healthy_request("127.0.0.1", port) for _ in range(3)),
                        _flaky_connection("127.0.0.1", port),
                        return_exceptions=True,
                    )
                else:
                    await asyncio.gather(
                        *(_healthy_request("127.0.0.1", port) for _ in range(6)), return_exceptions=True
                    )  # above ceiling
                round_num += 1
                await asyncio.sleep(0.05)  # a brief real gap between bursts, not back-to-back
            assert await _still_serving("127.0.0.1", port)
            assert round_num >= 5, f"expected several churn rounds within the time budget, got {round_num}"
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=15.0)


def test_existing_connections_survive_an_overflow_burst_untouched() -> None:
    # The project owner's explicit expectation: exceeding max_connections rejects the new arrivals
    # only - existing, already-admitted connections must keep running to completion, never get
    # dropped/reset by a later overflow burst.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            assert sensortask_wozi.webserver is not None
            max_conn = sensortask_wozi.webserver._max_connections
            held = [asyncio.create_task(_slow_but_healthy_put("127.0.0.1", port, 0.5)) for _ in range(max_conn)]
            await asyncio.sleep(0.1)  # let every held connection actually be admitted and mid-flight
            # before the overflow burst below fires

            async def _overflow_attempt() -> "int | str":
                try:
                    return await _healthy_request("127.0.0.1", port)
                except OSError:
                    return "rejected"

            overflow_results = await asyncio.gather(*(_overflow_attempt() for _ in range(max_conn * 2)))
            assert all(r in (200, "rejected") for r in overflow_results), overflow_results

            held_results = await asyncio.gather(*held)
            assert held_results == [200] * max_conn, held_results
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=15.0)


def test_a_slot_freed_by_a_stale_connections_timeout_accepts_a_new_connection() -> None:
    # Real-socket-level counterpart of tests/test_asy_webserver_service.py's own
    # test_f1_a_slot_freed_by_reclaim_accepts_the_next_connection_immediately (fake reader/writer) -
    # confirms the same reclaim-frees-a-slot behavior against the real assembled system.
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            assert sensortask_wozi.webserver is not None
            max_conn = sensortask_wozi.webserver._max_connections
            stale = [asyncio.create_task(_flaky_connection("127.0.0.1", port)) for _ in range(max_conn)]
            await asyncio.sleep(0.02)  # let them actually occupy every slot before probing below
            try:
                still_full = await asyncio.wait_for(_healthy_request("127.0.0.1", port), 0.3)
            except (OSError, asyncio.TimeoutError):
                still_full = None
            assert still_full != 200, "a slot should not have been free yet - every slot was held"
            await asyncio.gather(*stale, return_exceptions=True)  # let the stale connections finish
            # their own real per_call_timeout_s/outer_cap_s-driven reclaim
            assert await _still_serving("127.0.0.1", port)  # proves the timeout mechanism actually
            # freed a slot, not just that overflow was rejected while full
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=25.0)


def test_multiple_browser_like_sessions_concurrently_all_succeed() -> None:
    # "Just the website" - several browser tabs/sessions, no direct-API traffic at all, each one
    # reusing a single connection via keep-alive across several resource fetches in sequence (the
    # real page-load shape - see scripts/build_website.sh's own "Bundling" comment).
    port = _next_test_port()

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            assert sensortask_wozi.webserver is not None
            max_conn = sensortask_wozi.webserver._max_connections
            page_load = ["/measurements", "/sensors", "/system", "/status"]
            results = await asyncio.gather(*(_keep_alive_client("127.0.0.1", port, page_load) for _ in range(max_conn)))
            for session_statuses in results:
                assert session_statuses == [200] * len(page_load), session_statuses
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=15.0)


def test_realistic_mixed_openhab_polling_and_browser_session_concurrently() -> None:
    # The scenario the project owner named directly: "an OpenHAB instance querying two endpoints
    # and a full browser session in parallel". OpenHAB modeled as two independent single-endpoint
    # pollers (its own typical "GET this endpoint every N seconds" pattern, each its own
    # connection); the browser modeled as one _keep_alive_client() session. All within
    # max_connections, so every request must succeed cleanly - the "everything is well-behaved and
    # there's still room" baseline the above-ceiling variant below builds on.
    port = _next_test_port()

    async def openhab_poller(path: str, rounds: int) -> "list[int]":
        results: list[int] = []
        for _ in range(rounds):
            results.append(await _healthy_request("127.0.0.1", port, path))
            await asyncio.sleep(0.02)
        return results

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            results_a, results_b, browser_statuses = await asyncio.gather(
                openhab_poller("/measurements", 5),
                openhab_poller("/status", 5),
                _keep_alive_client("127.0.0.1", port, ["/measurements", "/sensors", "/system", "/status", "/notification"]),
            )
            assert all(r == 200 for r in results_a), results_a
            assert all(r == 200 for r in results_b), results_b
            assert all(r == 200 for r in browser_statuses), browser_statuses
            assert await _still_serving("127.0.0.1", port)
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=20.0)


def test_realistic_mixed_traffic_above_the_connection_ceiling_degrades_gracefully() -> None:
    # Same realistic client mix as the test above, but scaled past max_connections (two browser
    # sessions plus three OpenHAB pollers = up to 5 simultaneous connections against a ceiling of
    # 4) - the real-world "more is happening than the ceiling allows for an instant" case. Each
    # OpenHAB poller retries every round (matching its own real polling behavior), so the actual
    # regression this guards is that no client is left permanently starved and the server itself
    # never wedges under sustained above-ceiling realistic-shaped demand - not that every single
    # attempt succeeds on the first try.
    port = _next_test_port()

    async def openhab_poller(path: str, rounds: int) -> "list[int | str]":
        results: list[int | str] = []
        for _ in range(rounds):
            try:
                results.append(await _healthy_request("127.0.0.1", port, path))
            except OSError:
                results.append("rejected")
            await asyncio.sleep(0.02)
        return results

    async def browser_session(paths: "list[str]") -> "list[int] | str":
        try:
            return await _keep_alive_client("127.0.0.1", port, paths)
        except OSError:
            return "rejected"

    async def scenario() -> None:
        await _boot(port)
        task = await _start_webserver()
        try:
            results = await asyncio.gather(
                openhab_poller("/measurements", 4),
                openhab_poller("/status", 4),
                openhab_poller("/networking", 4),
                browser_session(["/measurements", "/sensors", "/system"]),
                browser_session(["/notification", "/status"]),
            )
            for poll_result in results[:3]:
                assert 200 in poll_result, poll_result  # every poller eventually gets through at
                # least once across its own retries - none permanently starved
            assert await _still_serving("127.0.0.1", port)
        finally:
            await _cancel(task)

    run_timed(scenario(), timeout_s=25.0)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
