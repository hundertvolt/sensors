"""Manual tests, an execution mode of L3 (manual/runner.py): bus and electrical behaviour that needs a human's hands on
the breadboard - the recovery ladder under a pulled or held line, the FRAM's return after its lines come back, and
the WS2812 and FRAM chip-select timings only an instrument can see; each judged against /status, then by the operator."""

from typing import TYPE_CHECKING

import evidence
from error_log_helpers import code, get_errcount
from harness import SRC_DIR, Board, boot_lines
from runner import confirm, confirm_pass, countdown, dut_ip, observe, print_instruction, record_assertion, register, rest_get, state_expected_outcome

from buildgen.validate import module_int_const

if TYPE_CHECKING:
    from http_client import JSONObject

# @tunable l4.manual_bus_electrical_recovery_watch_s = 30.0
_RECOVERY_WATCH_S = 30.0
# @tunable l4.manual_bus_electrical_reboot_watch_s = 30.0
_REBOOT_WATCH_S = 30.0
# @tunable l4.manual_bus_electrical_lead_window_s = 20
_LEAD_WINDOW_S = 20
_RR_WATCHDOG, _RR_TASK_BUDGET = (module_int_const(SRC_DIR, "asy_system_service.py", name) for name in ("_RR_WATCHDOG", "_RR_TASK_BUDGET"))


def _block(status: "JSONObject", name: str) -> "JSONObject":
    block = status.get(name)
    assert isinstance(block, dict), f"/status carries no {name} block: {status}"
    return block


def _scd30(path: str, field: str) -> object:
    # One SCD30 field of GET /measurements or GET /sensors.
    sensor = rest_get(path).get("SCD30")
    assert isinstance(sensor, dict), f"GET {path} carries no SCD30 entry"
    return sensor.get(field)


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
    "Pull the FRAM's SPI lines and CS, then replug them: the FRAM-backed loggers keep their write failures in RAM meanwhile, and after the replug the FRAM manager's recovery re-initialises the chip and /status shows FRAM-backed entries written again; no reboot.",
    "[USB+WiFi][MANUAL]",
)
def test_fram_unplug_replug_recovery() -> None:
    before = _block(rest_get("/status"), "system")
    print_instruction(f"Disconnect the FRAM's SCK, MOSI, MISO and CS leads now. You have {_LEAD_WINDOW_S:g} seconds.")
    countdown(_LEAD_WINDOW_S, "Disconnect the FRAM leads now")
    confirm("Confirm all four leads are off, then press Enter")
    print_instruction(f"Reconnect all four leads exactly as they were. You have {_LEAD_WINDOW_S:g} seconds.")
    countdown(_LEAD_WINDOW_S, "Reconnect the FRAM leads now")
    countdown(int(_RECOVERY_WATCH_S), "Waiting for the FRAM manager's recovery")
    after = _block(rest_get("/status"), "system")
    record_assertion()
    assert int(str(after.get("SysUptime"))) > int(str(before.get("SysUptime"))), f"the board rebooted: {before} -> {after}"
    state_expected_outcome("GET /status's errcount shows the FRAM log's failure entries from the gap, and a FRAM-backed module's newer entries are kept again after the replug.")
    confirm_pass("Does /status show that? [y/N]")


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
