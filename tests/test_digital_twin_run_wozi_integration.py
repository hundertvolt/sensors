"""Deterministic unit tests for digital_twin/_http_client.py's pure request/response parsing plus digital_twin/run_wozi_integration.py's own parse_args() - same split as test_digital_twin_launch.py's, applied to the twin's own entry point."""

import asyncio
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

sys.path.insert(0, "ext")  # run_wozi_integration.py transitively imports sensortask_wozi ->
# asy_webserver_service -> microdot - same convention test_sensortask_wozi.py's own comment uses.
sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import _http_client as http_client  # noqa: E402
from run_wozi_integration import RunConfig, _soak, main, parse_args  # noqa: E402


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


def run_timed(coro: "Coroutine[Any, Any, T]", timeout_s: float = 5.0) -> "T":
    return asyncio.run(asyncio.wait_for(coro, timeout_s))


# ---------------------------------------------------------------------------
# _http_client.build_request()
# ---------------------------------------------------------------------------


def test_build_request_get_has_no_body_and_no_content_type() -> None:
    req = http_client.build_request("GET", "/status", "localhost")
    assert req.startswith(b"GET /status HTTP/1.1\r\n")
    assert b"Content-Type" not in req
    assert b"Content-Length: 0\r\n" in req
    assert req.endswith(b"\r\n\r\n")


def test_build_request_put_includes_a_json_body_and_content_type() -> None:
    req = http_client.build_request("PUT", "/notification", "localhost", {"WarnCO2": 1800})
    header, _, body = req.partition(b"\r\n\r\n")
    assert b"PUT /notification HTTP/1.1" in header
    assert b"Content-Type: application/json" in header
    assert body == b'{"WarnCO2": 1800}'
    assert f"Content-Length: {len(body)}".encode() in header


def test_build_request_always_asks_for_connection_close() -> None:
    # asy_webserver_service.py's own _mark_connection_close() always sets this on the response too -
    # this client never implements keep-alive (see this file's own module docstring).
    req = http_client.build_request("GET", "/", "localhost")
    assert b"Connection: close\r\n" in req


def test_build_request_includes_the_host_header() -> None:
    req = http_client.build_request("GET", "/measurements", "127.0.0.1")
    assert b"Host: 127.0.0.1\r\n" in req


# ---------------------------------------------------------------------------
# _http_client.parse_status_line()
# ---------------------------------------------------------------------------


def test_parse_status_line_extracts_the_numeric_code() -> None:
    assert http_client.parse_status_line(b"HTTP/1.1 200 OK\r\n") == 200
    assert http_client.parse_status_line(b"HTTP/1.1 404 Not found\r\n") == 404


def test_parse_status_line_rejects_a_malformed_line() -> None:
    try:
        http_client.parse_status_line(b"garbage\r\n")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# _http_client.parse_header_line()
# ---------------------------------------------------------------------------


def test_parse_header_line_splits_name_and_value() -> None:
    assert http_client.parse_header_line(b"Content-Length: 42\r\n") == ("Content-Length", "42")


def test_parse_header_line_strips_surrounding_whitespace() -> None:
    assert http_client.parse_header_line(b"Content-Type:   application/json  \r\n") == ("Content-Type", "application/json")


def test_parse_header_line_returns_none_for_the_blank_terminator() -> None:
    assert http_client.parse_header_line(b"\r\n") is None
    assert http_client.parse_header_line(b"\n") is None
    assert http_client.parse_header_line(b"") is None  # EOF-truncated readline()


# ---------------------------------------------------------------------------
# HttpResponse.json()
# ---------------------------------------------------------------------------


def test_http_response_json_decodes_the_body() -> None:
    res = http_client.HttpResponse(200, {}, b'{"res": "OK"}')
    assert res.json() == {"res": "OK"}


# ---------------------------------------------------------------------------
# fetch() - one real end-to-end smoke test against a minimal hand-built asyncio.start_server(),
# proving the whole wire protocol round-trips correctly (request bytes out, status/headers/body
# parsed back in) - same "does the mechanism work at all" spirit test_digital_twin_launch.py's own
# main() smoke test and test_digital_twin_machine.py's own Timer/WDT live-timing tests already use,
# not a claim about src/asy_webserver_service.py's own behavior (that's this file's other sibling,
# tests/test_digital_twin_sensortask_integration.py's, job).
# ---------------------------------------------------------------------------


async def _canned_server(reader: "Any", writer: "Any") -> None:
    await reader.readline()  # request line - ignored, this fake always answers the same way
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
    body = b'{"ok": true}'
    writer.write(f"HTTP/1.1 200 OK\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode() + body)
    await writer.drain()
    await writer.wait_closed()


def test_fetch_round_trips_a_real_request_through_a_real_socket() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(_canned_server, "127.0.0.1", 18099)
        try:
            res = await http_client.fetch("127.0.0.1", 18099, "GET", "/anything")
            assert res.status_code == 200
            assert res.json() == {"ok": True}
        finally:
            server.close()
            await server.wait_closed()

    run_timed(scenario(), timeout_s=5.0)


# ---------------------------------------------------------------------------
# _soak() resilience - regression coverage for a real crash found via a real user report running
# this exact soak against the real assembled system: src/asy_webserver_service.py's own
# max_connections=3 reject-when-full path (WebserverService._serve()) closes a rejected connection
# immediately with zero response ever written, by design (BACKLOG.md's own "reject-when-full"
# decision) - a real client hitting it sees an ECONNRESET (or an EOF-before-any-bytes, depending on
# the OS/kernel's own close-with-unread-data semantics) with no HTTP-level response at all. The real
# server already tolerates this kind of failure gracefully; _soak() previously did not - a single
# reset request anywhere in the warmup or main cycle loop raised straight out of _soak() and crashed
# the whole diagnostic run instead of being recorded as one soak failure among many.
# ---------------------------------------------------------------------------


async def _reset_immediately_server(reader: "Any", writer: "Any") -> None:
    # Never reads the request, never writes a response, closes immediately - the same "closed with
    # nothing written at all" shape WebserverService._serve()'s own reject-when-full path produces
    # (its own _close_writer() helper: writer.close() then await writer.wait_closed()).
    writer.close()
    await writer.wait_closed()


def test_soak_records_a_connection_reset_as_a_failure_instead_of_crashing() -> None:
    async def scenario() -> None:
        server = await asyncio.start_server(_reset_immediately_server, "127.0.0.1", 18098)
        try:
            failures = await _soak("127.0.0.1", 18098, cycles=1)  # must not raise
        finally:
            server.close()
            await server.wait_closed()
        assert failures  # every single request (warmup and main cycle alike) failed - some
        # failure must have been recorded, not silently dropped
        assert any("warmup" in f for f in failures)
        assert any("cycle 0" in f for f in failures)

    run_timed(scenario(), timeout_s=15.0)


# ---------------------------------------------------------------------------
# run_wozi_integration.main() - one real, short, bounded end-to-end smoke test (same "does the
# mechanism work at all" spirit as test_digital_twin_launch.py's own main() smoke test): builds the
# real sensortask_wozi object graph against the real twin, runs a tiny soak with a real injected
# bus fault, and returns - not a claim about src/asy_webserver_service.py's own per-endpoint
# behavior (that's tests/test_digital_twin_sensortask_integration.py's job) or about a real soak's
# actual duration (digital_twin/run_wozi_integration.py's own docstring covers that). In-memory
# FRAM (fram_state_path=None) keeps this deterministic and avoids ever touching a real file - same
# reasoning applies to scd30_state_path=None below.
#
# Deliberately exactly one such test, not two (a soak-only one plus a separate fault-injection
# one): main()'s own real supervisor (sensortask_wozi.main()/start_and_check_tasks()) leaves
# several real background tasks running after main()'s own main_task.cancel() - the same orphaned-
# task memory-pressure bug tests/test_digital_twin_sensortask_integration.py's own module docstring
# already documents in full, found the same way here (a second real system construction inside this
# one process ran out of heap - a real MemoryError, not hypothetical). digital_twin/launch.py's own
# test file has exactly one such smoke test for the identical reason - matched here, not
# reinvented, and both concerns (soak completes cleanly, a real fault doesn't stop it) fit in one
# run anyway.
# ---------------------------------------------------------------------------


def test_main_runs_a_tiny_bounded_soak_with_an_injected_fault_and_returns_a_clean_summary() -> None:
    # A real bus fault on one sensor must not stop the soak from completing (same "one bad
    # participant can't take down the rest" convention this codebase applies everywhere else) -
    # exercises _apply_fault() for real, not just parse_fault_spec()'s own pure parsing above.
    # soak_cycles is deliberately tiny, unlike a real soak run (digital_twin/run_wozi_integration.py's
    # own default is 20, and Step 2's own precedent this reuses is 120) - this is a smoke test, not
    # a real soak, and the memory-flat check's fixed tolerance needs far more real cycles than fit a
    # fast smoke test to reliably average out ordinary per-connection allocator noise (confirmed
    # directly: a real run at this file's own small cycle count produced a false-positive-shaped
    # gc.mem_free() dip). The endpoint-reachability and watchdog signals are meaningful even at this
    # tiny scale, so this only excludes that one specific, scale-sensitive failure message.
    config = RunConfig(
        host="127.0.0.1",
        port=19097,
        fram_state_path=None,
        scd30_state_path=None,
        soak=True,  # this test's own point is to exercise the soak + fault-injection combo, so
        # it must opt in explicitly now that a bare RunConfig() defaults to soak=False (see
        # test_parse_args_defaults below).
        soak_cycles=2,
        duration=0.0,
        faults=[("sgp40", "writeto", 3)],
    )
    summary = run_timed(main(config), timeout_s=60.0)  # _SOAK_WARMUP_CYCLES (40, see that
    # constant's own comment) adds real HTTP round trips ahead of this test's own tiny soak_cycles -
    # 30s wasn't enough once that warm-up landed.
    non_memory_failures = [f for f in summary["failures"] if "gc.mem_free()" not in f]
    assert non_memory_failures == []
    assert summary["would_have_triggered_count"] == 0


# ---------------------------------------------------------------------------
# run_wozi_integration.parse_args()
# ---------------------------------------------------------------------------


def test_parse_args_defaults() -> None:
    # A bare, no-flags run is the plain "launch the twin and serve forever, like the real rp2040
    # would" path - soak defaults to disabled, only opted into via --soak/--soak-cycles below.
    config = parse_args([])
    assert config == RunConfig(
        host="localhost",
        port=8080,
        fram_state_path="digital_twin/fram_state.json",
        scd30_state_path="digital_twin/scd30_state.json",
        seed=None,
        faults=[],
        wifi_outcomes=[],
        soak=False,
        soak_cycles=20,
        duration=None,
    )


def test_parse_args_host_and_port() -> None:
    config = parse_args(["--host", "0.0.0.0", "--port", "9090"])
    assert config.host == "0.0.0.0"
    assert config.port == 9090


def test_parse_args_empty_fram_state_path_means_in_memory_only() -> None:
    config = parse_args(["--fram-state-path", ""])
    assert config.fram_state_path is None


def test_parse_args_custom_fram_state_path() -> None:
    config = parse_args(["--fram-state-path", "scratch/fram.json"])
    assert config.fram_state_path == "scratch/fram.json"


def test_parse_args_empty_scd30_state_path_means_in_memory_only() -> None:
    config = parse_args(["--scd30-state-path", ""])
    assert config.scd30_state_path is None


def test_parse_args_custom_scd30_state_path() -> None:
    config = parse_args(["--scd30-state-path", "scratch/scd30.json"])
    assert config.scd30_state_path == "scratch/scd30.json"


def test_parse_args_seed_and_soak_cycles_and_duration() -> None:
    config = parse_args(["--seed", "7", "--soak-cycles", "5", "--duration", "0"])
    assert config.seed == 7
    assert config.soak_cycles == 5
    assert config.duration == 0.0


def test_parse_args_duration_omitted_stays_none() -> None:
    assert parse_args([]).duration is None


def test_parse_args_soak_flag_enables_soak_with_the_default_cycle_count() -> None:
    config = parse_args(["--soak"])
    assert config.soak is True
    assert config.soak_cycles == 20


def test_parse_args_soak_cycles_implies_soak() -> None:
    # Passing a cycle count is itself opting into running the soak - no need to also pass --soak.
    config = parse_args(["--soak-cycles", "5"])
    assert config.soak is True
    assert config.soak_cycles == 5


def test_parse_args_accumulates_repeated_fault_flags() -> None:
    # Reuses launch.py's own parse_fault_spec() directly - same device/op vocabulary, not
    # reimplemented (this module's own docstring explains why).
    config = parse_args(["--fault", "sgp40:writeto", "--fault", "fram:readinto:3"])
    assert config.faults == [("sgp40", "writeto", 1), ("fram", "readinto", 3)]


def test_parse_args_accumulates_repeated_wifi_outcome_flags() -> None:
    import network

    config = parse_args(["--wifi-outcome", "success", "--wifi-outcome", "no_ap"])
    assert config.wifi_outcomes == [network.STAT_GOT_IP, network.STAT_NO_AP_FOUND]


def test_parse_args_rejects_an_unrecognized_flag() -> None:
    try:
        parse_args(["--bogus"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
