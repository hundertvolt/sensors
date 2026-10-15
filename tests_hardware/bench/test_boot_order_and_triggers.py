"""The boot order and the read-trigger spacing, observed on silicon: the webserver answers before the first NTP sync
completes, after every boot line, and readers sharing a bus keep the stagger the build plans for them (SPECIFICATION.md
C.9.1); the console stamped on arrival by the host, the round's boot log saved as evidence."""

import itertools
import threading
import time
from typing import TYPE_CHECKING

import _load
import evidence
import http_client
import pytest
import serial
from harness import SRC_DIR, Board, boot_lines, device_toml, kick_then_reset, restore_board_to_serving
from soak_durations import SOAK_DURATION_SECONDS

from buildgen.codegen import trigger_spread
from buildgen.driver_registry import class_has_read_triggers
from buildgen.graph import build_construction_order
from buildgen.validate import build_model

if TYPE_CHECKING:
    from bench_control import BenchBridge

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("construction", "sensortask_integration")

# @tunable l4.boot_order_status_poll_s = 0.5
_STATUS_POLL_S = 0.5
# @tunable l4.boot_order_window_s = 90.0
_BOOT_WINDOW_S = 90.0
# @tunable l4.boot_order_console_read_timeout_s = 0.2
_CONSOLE_READ_TIMEOUT_S = 0.2
# @tunable l4.boot_order_console_reopen_s = 0.2
_CONSOLE_REOPEN_S = 0.2
# Host-side arrival stamps carry the USB poll and print scheduling jitter on top of the planned gap.
# @tunable l4.boot_order_trigger_stamp_tolerance_ms = 20.0
_STAMP_TOLERANCE_MS = 20.0
# @tunable l4.boot_order_probe_timeout_s = 5.0
_PROBE_TIMEOUT_S = 5.0
# @tunable l4.boot_order_join_timeout_s = 10.0
_JOIN_TIMEOUT_S = 10.0
_BAUDRATE = 115200
_SYSTEM = "asy_system_service.py"
_TRIGGER_LINE = "sensor trigger"
# SCD30's read follows the chip's own data-ready, never its stagger slot (src/asy_scd30_driver.py _read_event).
_DATA_READY_DRIVERS = ("scd30",)
_STA_LINE = "WLAN connection established"  # src/asy_wifi_service.py
_NTP_START_LINE = "NTP sync starting."  # src/asy_ntp_client.py
_RTC_SET_LINE = "RTC set to:"  # src/asy_ntp_client.py


def test_webserver_answers_before_the_first_ntp_sync_completes(board: Board, bench: "BenchBridge", dut_ip: str, result_note: "_load.Note") -> None:
    stop = threading.Event()
    log: list[tuple[float, str]] = []
    answers: list[float] = []
    threads = [threading.Thread(target=_stamp_console, args=(board.device, stop, log), name="console"), threading.Thread(target=_poll_status, args=(dut_ip, stop, answers), name="status-poller")]
    reset_at = time.monotonic()
    try:
        kick_then_reset(board, bench)
        reset_at = time.monotonic()
        for thread in threads:
            thread.start()
        stop.wait(_BOOT_WINDOW_S)
    finally:
        stop.set()
        alive = _load.join(threads, _JOIN_TIMEOUT_S)
        restore_board_to_serving(board, bench, dut_ip)
    assert not alive, f"{alive} still running after the boot window"
    evidence.save_text("boot-log.txt", "\n".join(f"{t - reset_at:8.3f} {line}" for t, line in log))
    assert answers, f"no GET /status answered within {_BOOT_WINDOW_S:g}s of the reset"
    first_ok = answers[0]
    boots = [t for t, line in log if boot_lines([line])]
    assert boots, f"no boot line in the stamped log: the console needs DebugLevel >= 3 (log tail {[line for _t, line in log[-5:]]})"
    assert max(boots) <= first_ok, f"a boot line came {max(boots) - first_ok:.2f}s after the first 200: the webserver answered mid-setup"
    rtc_at = _first(log, _RTC_SET_LINE)
    ntp_lines = [(t, line) for t, line in log if t <= first_ok and (_NTP_START_LINE in line or _RTC_SET_LINE in line)]
    in_first_sync = bool(ntp_lines) and _NTP_START_LINE in ntp_lines[-1][1]
    assert rtc_at is None or first_ok < rtc_at or in_first_sync, f"the first 200 ({first_ok - reset_at:.2f}s) came after the first RTC set ({rtc_at - reset_at:.2f}s) with no sync under way"
    sta_at = _first(log, _STA_LINE)
    assert sta_at is not None, "no STA-connect line in the stamped log"
    result_note(f"STA connect to the first 200: {first_ok - sta_at:.2f}s (l4.dut_serving_after_sta_s's measured figure); reset to the first 200: {first_ok - reset_at:.2f}s")


@pytest.mark.soak_duration
def test_bus_triggers_keep_their_minimum_spacing(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    duration = request.config.getoption("--soak-duration")
    if duration is None:
        pytest.skip("a passive observation over one named duration: runs with --soak-duration")
    level = _load.get_object(dut_ip, "/system", _PROBE_TIMEOUT_S).get("DebugLevel")
    assert level == 5, f"the trigger lines are events, printed at DebugLevel 5 (the standard state), not {level!r}"
    buses, slots, slot_ms = _trigger_plan()
    stop = threading.Event()
    log: list[tuple[float, str]] = []
    console = threading.Thread(target=_stamp_console, args=(board.device, stop, log), name="console")
    try:
        console.start()
        stop.wait(SOAK_DURATION_SECONDS[duration])
    finally:
        stop.set()
        alive = _load.join([console], _JOIN_TIMEOUT_S)
        restore_board_to_serving(board, bench, dut_ip)
    assert not alive, "the console reader never finished"
    stamps = {name: [t for t, line in log if line.startswith(f"{name} {_TRIGGER_LINE}")] for name in slots}
    assert all(stamps.values()), f"a timer-triggered reader printed no trigger line: { {n: len(s) for n, s in stamps.items()} }"
    report: list[str] = []
    for a, b in itertools.combinations(sorted(slots), 2):
        if buses[a] != buses[b]:
            continue
        distance = abs(slots[a] - slots[b]) * slot_ms
        planned_ms = min(distance, _load.src_number(_SYSTEM, "_TIMER_BASE_PERIOD") - distance)
        gaps = [min(abs(t - u) for u in stamps[b]) * 1000 for t in stamps[a]]
        report.append(f"{a}/{b} on {buses[a]}: planned {planned_ms:g} ms, min {min(gaps):.0f} ms, median {sorted(gaps)[len(gaps) // 2]:.0f} ms over {len(gaps)}")
        assert min(gaps) >= planned_ms - _STAMP_TOLERANCE_MS, f"{a} and {b} on {buses[a]} triggered {min(gaps):.0f} ms apart, under their planned {planned_ms:g} ms"
    result_note("trigger spacing: " + ("; ".join(report) or "no two timer-triggered readers share a bus"))


def _first(log: "list[tuple[float, str]]", text: str) -> "float | None":
    return next((t for t, line in log if text in line), None)


def _poll_status(dut_ip: str, stop: threading.Event, answers: "list[float]") -> None:
    # GET /status every _STATUS_POLL_S until stopped: each 200's arrival time.
    while not stop.is_set():
        try:
            if http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_PROBE_TIMEOUT_S).status_code == 200:
                answers.append(time.monotonic())
        except (OSError, http_client.HTTP_ERROR):
            pass  # not serving yet: the boot under observation
        stop.wait(_STATUS_POLL_S)


def _stamp_console(device: str, stop: threading.Event, log: "list[tuple[float, str]]") -> None:
    # Each console line stamped on arrival; the port is reopened while a reset's USB re-enumeration settles.
    while not stop.is_set():
        try:
            with serial.Serial(device, _BAUDRATE, timeout=_CONSOLE_READ_TIMEOUT_S) as port:
                while not stop.is_set():
                    if raw := port.readline():
                        log.append((time.monotonic(), raw.decode("utf-8", errors="replace").rstrip("\r\n")))
        except serial.SerialException:  # the node vanishes and returns across the reset
            stop.wait(_CONSOLE_REOPEN_S)


def _trigger_plan() -> "tuple[dict[str, str], dict[str, int], float]":
    # The build's own stagger (buildgen.codegen.trigger_spread()): each timer-triggered reader's bus and slot, and the
    # slot width _TIMER_BASE_PERIOD // (readers + 1) in ms (src/asy_system_service.py start_timers()).
    model = build_model(device_toml(), SRC_DIR)
    position = {node: i for i, node in enumerate(build_construction_order(model))}
    specs = sorted((s for s in model.instances.values() if s.driver_info and s.driver_info.kind == "sensor" and s.resolved_name), key=lambda s: position[s.key])
    readers = [(str(s.resolved_name), str(s.fields["bus"])) for s in specs if s.driver_info is not None and class_has_read_triggers(s.driver_info)]
    order = trigger_spread(readers)
    bus = dict(readers)
    excluded = {str(s.resolved_name) for s in specs if s.driver in _DATA_READY_DRIVERS}
    slots = {name: k for k, name in enumerate(order) if name not in excluded}
    return {name: bus[name] for name in slots}, slots, _load.src_number(_SYSTEM, "_TIMER_BASE_PERIOD") // (len(order) + 1)
