"""The tick rollover survived on silicon, observed over REST only (owner, 2026-10-01): the tick-offset test image starts
its ms count 15 minutes short of 2**32, so time.ticks_ms()'s 2**30 period, the soft timers' and lwIP's 32-bit counts all
wrap soon after boot; polled for two hours, nothing reboots, stalls or stops syncing (RP2040 datasheet 4.6.2)."""

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

import _load
import http_client
import micropython_overrides
import pytest
from error_log_helpers import assert_no_task_ended, save_errcount
from harness import reflash, save_fram_raw, wait_until

if TYPE_CHECKING:
    from bench_control import BenchBridge
    from harness import Board
    from http_client import JSONObject

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("sensortask_integration",)

# Several polls on each side of the wraps.
# @tunable l4.ticks_rollover_poll_interval_s = 300.0
_POLL_INTERVAL_S = 300.0
# The wraps fall about 15 minutes after boot; the rest of the two hours is margin.
# @tunable l4.ticks_rollover_run_s = 7200.0
_RUN_S = 7200.0
# @tunable l4.ticks_rollover_sync_age_margin_s = 60.0
_SYNC_AGE_MARGIN_S = 60.0
# @tunable l4.ticks_rollover_serving_timeout_s = 120.0
_SERVING_TIMEOUT_S = 120.0
# @tunable l4.ticks_rollover_retry_s = 10.0
_RETRY_S = 10.0
# @tunable l4.ticks_rollover_probe_timeout_s = 10.0
_PROBE_TIMEOUT_S = 10.0


@pytest.mark.multi_day_rollover
@pytest.mark.flash_cycle
def test_ticks_ms_rollover_is_survived(board: "Board", bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    if not request.config.getoption("--allow-flash-cycle"):
        pytest.skip("flashes the tick-offset test image, left for the next round to replace - pass --allow-flash-cycle to deliberately run it")
    if not request.config.getoption("--allow-multi-day-rollover"):
        pytest.skip("about two hours on the tick-offset test image: runs with --allow-multi-day-rollover and --rollover-image")
    option = request.config.getoption("--rollover-image")
    assert option, "--rollover-image names no tick-offset test image: the rollover runner builds it and passes the option"
    image = Path(option)
    assert image.is_file(), f"the tick-offset test image {image} does not exist"
    record = json.loads(image.with_suffix(".json").read_text(encoding="utf-8"))
    assert isinstance(record, dict) and micropython_overrides.TICK_OFFSET_DIR_NAME in (record.get("overrides") or []), f"{image}'s record names overrides {record.get('overrides') if isinstance(record, dict) else record!r}, not the tick-offset test override"
    # The evidence first: a reflash is a clearing path (CLAUDE.md's FRAM rule). The next round flashes its own image.
    save_errcount(dut_ip, request.node.name)
    save_fram_raw(board, request.node.name)
    reflash(board, image)
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_SERVING_TIMEOUT_S, description="the tick-offset test image serving")
    assert _load.image_deviations(request, dut_ip, record, allow_rollover=True) == [], f"the board does not run the tick-offset test image: {_load.image_deviations(request, dut_ip, record, allow_rollover=True)}"
    interval_h = _load.get_object(dut_ip, "/networking", _PROBE_TIMEOUT_S).get("NTPInterval")
    assert isinstance(interval_h, int), f"GET /networking carries no int NTPInterval: {interval_h!r}"
    status, measurements = _poll(dut_ip)
    system = _load.as_object(status.get("system"), "GET /status system")
    signature, uptime = system.get("BootSignature"), system.get("SysUptime")
    assert isinstance(uptime, int), f"GET /status carries no int SysUptime: {uptime!r}"
    ts = _sensor_ts(measurements)
    n = 0
    while uptime < _RUN_S:
        time.sleep(_POLL_INTERVAL_S)
        n += 1
        status, measurements = _poll_retried(dut_ip, result_note, n)
        system = _load.as_object(status.get("system"), "GET /status system")
        now = system.get("SysUptime")
        assert system.get("BootSignature") == signature and isinstance(now, int) and now > uptime, f"poll {n}: the board rebooted or its uptime stalled ({signature!r}, {uptime} -> {system.get('BootSignature')!r}, {now!r})"
        uptime = now
        age = _load.as_object(status.get("networking"), "GET /status networking").get("NTPLastSyncAge")
        assert isinstance(age, int) and age <= interval_h * 3600 + _SYNC_AGE_MARGIN_S, f"poll {n} at uptime {uptime}s: NTPLastSyncAge {age!r} past the {interval_h} h interval plus {_SYNC_AGE_MARGIN_S:g}s"
        fresh = _sensor_ts(measurements)
        stuck = {name: value for name, value in fresh.items() if value is None or value == ts.get(name)}
        assert not stuck, f"poll {n} at uptime {uptime}s: these sensors' TS did not advance: {stuck}"
        ts = fresh
        assert_no_task_ended(dut_ip, f"the tick rollover, poll {n}")
    result_note(f"{n} polls over {uptime}s of uptime on the tick-offset image: no reboot, NTP kept, every sensor's TS advancing")


def _poll(dut_ip: str) -> "tuple[JSONObject, JSONObject]":
    # GET /status and /measurements, each strict.
    return _load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S), _load.get_object(dut_ip, "/measurements", _PROBE_TIMEOUT_S)


def _poll_retried(dut_ip: str, result_note: "_load.Note", n: int) -> "tuple[JSONObject, JSONObject]":
    # One poll, retried within the interval; each retry noted.
    deadline = time.monotonic() + _POLL_INTERVAL_S
    while True:
        try:
            return _poll(dut_ip)
        except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError) as exc:
            if time.monotonic() + _RETRY_S >= deadline:
                raise
            result_note(f"poll {n} failed ({exc!r}); retried within the interval", recovery=True)
            time.sleep(_RETRY_S)


def _sensor_ts(measurements: "JSONObject") -> "dict[str, object]":
    return {name: data.get("TS") for name, data in measurements.items() if isinstance(data, dict) and "TS" in data}
