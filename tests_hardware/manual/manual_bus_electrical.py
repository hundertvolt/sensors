"""Manual tests, an execution mode of L3 (manual/runner.py): bus and electrical behaviour needing a human's hands on the
breadboard - the recovery ladder under a pulled or held line, the FRAM's and UART link's return after a pull, and the
WS2812 and FRAM chip-select timings only an instrument can see; each judged against /status, then by the operator."""

import time
from typing import TYPE_CHECKING

import evidence
from error_log_helpers import ErrcountEntry, code, errcount_entry, get_errcount, save_errcount
from harness import SRC_DIR, Board, boot_lines
from runner import confirm, confirm_pass, countdown, dut_ip, observe, print_instruction, record_assertion, register, rest_get, state_expected_outcome

from buildgen.model import MAINTENANCE_NAMES
from buildgen.validate import module_int_const

if TYPE_CHECKING:
    from collections.abc import Callable

    from http_client import JSONObject

# @tunable l4.manual_bus_electrical_recovery_watch_s = 30.0
_RECOVERY_WATCH_S = 30.0
# @tunable l4.manual_bus_electrical_reboot_watch_s = 30.0
_REBOOT_WATCH_S = 30.0
# @tunable l4.manual_bus_electrical_lead_window_s = 20
_LEAD_WINDOW_S = 20
# @tunable l4.manual_bus_electrical_fram_detect_watch_s = 120.0
_FRAM_DETECT_WATCH_S = 120.0
_POLL_S = 1.0  # a recorded latency's resolution: one /status read a second
_RR_WATCHDOG, _RR_TASK_BUDGET = (module_int_const(SRC_DIR, "asy_system_service.py", name) for name in ("_RR_WATCHDOG", "_RR_TASK_BUDGET"))


def _block(status: "JSONObject", name: str) -> "JSONObject":
    block = status.get(name)
    assert isinstance(block, dict), f"/status carries no {name} block: {status}"
    return block


def _keep_off(held_s: "float | None", within_s: float, message: str) -> None:
    # The lines stay off for the lead window at least, however soon the pull was seen (held_s; None: within_s passed).
    remaining = _LEAD_WINDOW_S - (held_s if held_s is not None else within_s)
    if remaining > 0:
        countdown(int(remaining), message)


def _link(status: "JSONObject") -> "dict[str, int]":
    # The UART link's maintenance counters in GET /status's sensors list; a device wiring no uart_link pair has none.
    sensors = status.get("sensors")
    link = sensors.get(MAINTENANCE_NAMES["uart_link"]) if isinstance(sensors, dict) else None
    assert isinstance(link, dict) and all(isinstance(link.get(key), int) for key in ("Transfers", "Failures")), f"GET /status carries no {MAINTENANCE_NAMES['uart_link']} entry with Transfers and Failures - the bench device wires no uart_link pair: {sensors!r}"
    return {key: int(str(link[key])) for key in ("Transfers", "Failures")}


def _new_codes(before: "dict[str, ErrcountEntry]", after: "dict[str, ErrcountEntry]") -> "dict[str, list[str]]":
    # Each logger's entries between two errcount reads, as type and number (E82), newest last: the newest entries its
    # counter grew by, as error_log_helpers.new_task_raised() windows them, plus a count of those its ring no longer holds.
    found: dict[str, list[str]] = {}
    for name in sorted(after):
        used = [h for h in errcount_entry(after, name)["history"] if h.get("type") != "N"]
        grew = errcount_entry(after, name)["counter"] - (errcount_entry(before, name)["counter"] if name in before else 0)
        if grew != 0:
            window = used if grew < 0 else used[len(used) - min(grew, len(used)) :]
            found[name] = [f"{h.get('type')}{h.get('num')}" for h in window] + ([f"+{grew - len(used)} past the ring"] if grew > len(used) else [])
    return found


def _scd30(path: str, field: str) -> object:
    # One SCD30 field of GET /measurements or GET /sensors.
    sensor = rest_get(path).get("SCD30")
    assert isinstance(sensor, dict), f"GET {path} carries no SCD30 entry"
    return sensor.get(field)


def _seconds_until(changed: "Callable[[], bool]", within_s: float) -> "float | None":
    # Polls from now, once a second: the seconds until changed() first holds, None when it has not within within_s.
    start = time.monotonic()
    while True:
        if changed():
            return round(time.monotonic() - start, 1)
        if time.monotonic() - start >= within_s:
            return None
        time.sleep(_POLL_S)


@register(
    "hot_unplug_replug_i2c_recovery",
    "Hot-unplug/replug an SCD30's I2C leads (SDA/SCL) and confirm the recovery ladder - the participant's soft reset, the bus clear, the controller re-init (SPECIFICATION.md F.2) - brings its reads back without a reboot.",
    "[USB+WiFi][MANUAL]",
)
def test_hot_unplug_replug_i2c_recovery() -> None:
    before, ts_before = _block(rest_get("/status"), "system"), _scd30("/measurements", "TS")
    count_before = get_errcount(dut_ip())["SCD30"]["counter"]
    print_instruction(f"Disconnect BOTH the SCD30's SDA and SCL leads now. You have {_LEAD_WINDOW_S:g} seconds.")
    state_expected_outcome("the system keeps running (no reboot); the SCD30 log gains its read-failure entries while the leads are off.")
    countdown(_LEAD_WINDOW_S, "Disconnect the SCD30 I2C leads now")
    confirm("Confirm both leads are fully disconnected, then press Enter")
    print_instruction(f"Now reconnect BOTH leads exactly as they were. You have {_LEAD_WINDOW_S:g} seconds.")
    countdown(_LEAD_WINDOW_S, "Reconnect the SCD30 I2C leads now")
    confirm("Confirm both leads are reconnected, then press Enter")
    interval = _scd30("/sensors", "MeasInterval")
    countdown(max(int(_RECOVERY_WATCH_S), 3 * int(str(interval))), "Waiting three measurement intervals for a fresh SCD30 reading")
    after, ts_after = _block(rest_get("/status"), "system"), _scd30("/measurements", "TS")
    log = get_errcount(dut_ip())["SCD30"]
    print_instruction(f"SCD30 log {count_before} -> {log['counter']} entries, TS {ts_before} -> {ts_after}, ResetReason {after.get('ResetReason')}, SysUptime {before.get('SysUptime')} -> {after.get('SysUptime')}.")
    record_assertion()
    assert log["counter"] > count_before and any(e.get("num") == code("E", "READ") for e in log["history"]), f"no SCD30 read failure was logged while the leads were off: {log}"
    assert ts_after != ts_before, f"no fresh SCD30 reading within three intervals of the replug: TS {ts_after}"
    assert int(str(after.get("SysUptime"))) > int(str(before.get("SysUptime"))), f"the board rebooted: {before} -> {after}"
    confirm_pass("Did the log and the readings look as stated above? [y/N]")


@register(
    "fram_unplug_replug_recovery",
    "Pull the FRAM's SPI lines and CS, then replug them: the seconds from the pull to the first FRAM log entry are recorded, the FRAM-backed loggers keep their write failures in RAM meanwhile, and after the replug the FRAM manager's recovery re-initialises the chip and /status shows FRAM-backed entries written again; no reboot.",
    "[USB+WiFi][MANUAL]",
)
def test_fram_unplug_replug_recovery() -> None:
    before = _block(rest_get("/status"), "system")
    fram_before = errcount_entry(get_errcount(dut_ip()), "FRAM")["counter"]
    print_instruction("Disconnect the FRAM's SCK, MOSI, MISO and CS leads now.")
    confirm("Press Enter the moment the last of the four leads is off")
    # A read-only stretch reaches the silent chip only through reads, so detection may come late: the figure is recorded.
    detected_s = _seconds_until(lambda: errcount_entry(get_errcount(dut_ip()), "FRAM")["counter"] > fram_before, _FRAM_DETECT_WATCH_S)
    latency = f"{detected_s:g} s" if detected_s is not None else f"none within {_FRAM_DETECT_WATCH_S:g} s"
    evidence.save_text("fram-pull-latency.txt", f"seconds from the FRAM pull to its first FRAM log entry: {latency}\n")
    print_instruction(f"The first FRAM log entry after the pull: {latency}.")
    _keep_off(detected_s, _FRAM_DETECT_WATCH_S, "Keep the FRAM leads off")
    print_instruction(f"Reconnect all four leads exactly as they were. You have {_LEAD_WINDOW_S:g} seconds.")
    countdown(_LEAD_WINDOW_S, "Reconnect the FRAM leads now")
    countdown(int(_RECOVERY_WATCH_S), "Waiting for the FRAM manager's recovery")
    after = _block(rest_get("/status"), "system")
    record_assertion()
    assert int(str(after.get("SysUptime"))) > int(str(before.get("SysUptime"))), f"the board rebooted: {before} -> {after}"
    state_expected_outcome("GET /status's errcount shows the FRAM log's failure entries from the gap, and a FRAM-backed module's newer entries are kept again after the replug.")
    confirm_pass("Does /status show that? [y/N]")


@register(
    "uart_crossover_pull_recovery",
    "Pull the UART crossover jumper mid-transfer, then replug it: the seconds to the link's first failed transfer, every code logged while it was off and the seconds until its transfers resume are recorded; no reboot.",
    "[USB+WiFi][MANUAL]",
)
def test_uart_crossover_pull_recovery() -> None:
    status = rest_get("/status")
    before, link_before, logs_before = _block(status, "system"), _link(status), get_errcount(dut_ip())
    print_instruction("Pull both wires of the UART crossover jumper (tests_hardware/README.md, 'The dev bench') now, while the link exercises.")
    state_expected_outcome("the link's Failures count rises while the wires are off and its loggers log the failed transfers; after the replug its Transfers advance again, with no reboot.")
    confirm("Press Enter the moment both wires are off")
    failed_s = _seconds_until(lambda: _link(rest_get("/status"))["Failures"] > link_before["Failures"], _LEAD_WINDOW_S)
    _keep_off(failed_s, _LEAD_WINDOW_S, "Keep the jumper wires off")
    print_instruction("Reconnect both wires exactly as they were.")
    confirm("Press Enter the moment both wires are back")
    replugged = _link(rest_get("/status"))
    resumed_s = _seconds_until(lambda: _link(rest_get("/status"))["Transfers"] > replugged["Transfers"], _RECOVERY_WATCH_S)
    status = rest_get("/status")
    after, link_after, logged = _block(status, "system"), _link(status), _new_codes(logs_before, get_errcount(dut_ip()))
    save_errcount(dut_ip(), "uart-crossover-pull")
    seen = f"{failed_s:g} s" if failed_s is not None else f"none within {_LEAD_WINDOW_S:g} s"
    resumed = f"{resumed_s:g} s" if resumed_s is not None else f"not within {_RECOVERY_WATCH_S:g} s"
    text = f"first failed transfer after the pull: {seen}; Failures {link_before['Failures']} -> {link_after['Failures']}; codes logged: {logged or 'none'}; transfers resumed after the replug: {resumed}"
    evidence.save_text("uart-crossover-pull.txt", text + "\n")
    print_instruction(text)
    record_assertion()
    assert int(str(after.get("SysUptime"))) > int(str(before.get("SysUptime"))), f"the board rebooted: {before} -> {after}"
    assert link_after["Failures"] > link_before["Failures"], f"the pull left no failed transfer: {link_before} -> {link_after}"
    assert resumed_s is not None, f"the link's transfers did not resume within {_RECOVERY_WATCH_S:g}s of the replug: {replugged} -> {link_after}"
    confirm_pass("Did the codes and the recovery look as stated above? [y/N]")


@register(
    "wedged_i2c_bus_watchdog_backstop",
    "Hold SDA low: the SCD30 bus escalates through the ladder - its bus-recovery entries (the clear and the controller re-init), then the supervisor's reboot, ResetReason 5 after the release; a watchdog reset (2) only if a transfer never returns.",
    "[USB+WiFi][MANUAL]",
)
def test_wedged_i2c_bus_watchdog_backstop() -> None:
    board = Board()
    print_instruction("Attach a jumper wire from the SCD30's SDA pin directly to GND, holding the I2C bus low.")
    state_expected_outcome(f"bus-recovery entries ({code('W', 'BUS_RECOVERY')}: the catalog's W BUS_RECOVERY) in the SCD30 log, then a supervisor reboot (ResetReason {_RR_TASK_BUDGET}); a watchdog reset ({_RR_WATCHDOG}) only if a transfer never returns.")
    confirm("Confirm the jumper is connected (SDA held to GND), then press Enter to start watching")
    lines = board.tail_log(duration_s=_REBOOT_WATCH_S)
    print_instruction("Now remove the SDA-to-GND jumper.")
    confirm("Confirm the jumper is removed, then press Enter")
    countdown(int(_RECOVERY_WATCH_S), "Waiting for the board to serve again")
    reason = _block(rest_get("/status"), "system").get("ResetReason")
    log = get_errcount(dut_ip())["SCD30"]
    print_instruction(f"ResetReason {reason}; SCD30 log {log}")
    record_assertion()
    assert boot_lines(lines), f"no reboot within {_REBOOT_WATCH_S:g}s of holding SDA low:\n" + "\n".join(lines)
    assert reason in (_RR_TASK_BUDGET, _RR_WATCHDOG), f"the reboot read ResetReason {reason}, neither the supervisor's {_RR_TASK_BUDGET} nor the watchdog's {_RR_WATCHDOG}"
    assert any(e.get("type") == "W" and e.get("num") == code("W", "BUS_RECOVERY") for e in log["history"]), f"no bus-recovery entry in the SCD30 log: {log}"
    confirm_pass(f"ResetReason {reason} ({'the supervisor' if reason == _RR_TASK_BUDGET else 'the watchdog: a transfer never returned'}) - as observed? [y/N]")


@register(
    "real_ws2812_neopixel_signal_timing",
    "WS2812 bit timing against datasheets/ws2812/WS2812.pdf p.4 (T0H 0.35 us, T1H 0.7 us, +-150 ns; reset low above 50 us) with a scope or logic analyzer if one is at hand, colour correctness by eye otherwise - automating it needs a logic analyzer the bench does not have (no test hardware is bought, owner, 2026-09-22).",
    "[USB+WiFi][MANUAL]",
)
def test_real_ws2812_neopixel_signal_timing() -> None:
    print_instruction("If you have a scope/logic analyzer, connect its probe to the NeoPixel data line now.")
    print_instruction('Send red, green, blue and off, one PUT /notification {"LightCmdLED": {"R": .., "G": .., "B": .., "T": 1.0}} each, each only after the previous flash has finished: a command sent while a flash runs is refused and its answer asks you to retry later.')
    state_expected_outcome("four distinct, clean colours in sequence with no flicker; on an instrument, T0H 0.35 us and T1H 0.7 us within +-150 ns, and a reset low above 50 us (datasheets/ws2812/WS2812.pdf p.4).")
    confirm("Press Enter once you've sent the sequence and observed it")
    confirm_pass()


@register(
    "fram_cs_at_power_off",
    "With an oscilloscope only (none bought for the bench, owner, 2026-09-22): probe FRAM CS and VDD through a watchdog reset and a USB power removal, and record whether CS stays above 0.7 x VDD (the fitted MB85RS2MTA, its datasheet p.18; 0.8 x VDD on the MB85RS64V, p.17) until VDD is below the part's minimum.",
    "[USB][MANUAL]",
)
def test_fram_cs_at_power_off() -> None:
    print_instruction("Without an oscilloscope, answer 'not measured' below. Otherwise probe FRAM CS and VDD, trigger a watchdog reset (tests_hardware/kick_then_reset.py without its kick), then remove USB power, capturing both.")
    text = observe("Record what CS did relative to 0.7 x VDD until VDD fell below the minimum, for each event (or 'not measured'):")
    if text:
        evidence.save_text("fram-cs-power-off.txt", text + "\n")
