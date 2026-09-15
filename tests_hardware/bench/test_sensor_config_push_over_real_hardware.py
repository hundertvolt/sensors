"""Bench-tier automated tests: real PUT /sensors and PUT /notification config pushes against real
hardware, the real-hardware counterpart to tests/test_setter_microdot_integration.py's mock. A
"Valid" result plus a follow-up GET confirms the live-push callback took effect and stuck."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import http_client
from error_log_helpers import assert_module_error_log_empty, reset_all_error_logs

if TYPE_CHECKING:
    from harness import Board

# Deliberately different from every driver default (_VAL_POV/_VAL_TOV/_VAL_FC in
# asy_bmp3xx_driver.py: PressOvers=1, TempOvers=1, FiltCoeff=0) and all real, allowed discrete
# settings (_OSR_SETTINGS=(1,2,4,8,16,32), _IIR_SETTINGS=(0,1,3,7,15,31,63,127)) - a real change
# must actually take effect on the real hardware for this test to mean anything.
_BMP3XX_TEST_VALUES = {"PressOvers": 4, "TempOvers": 2, "FiltCoeff": 3}

# SCD30 has no live-push config fields at all (asy_scd30_driver.py registers no _push_callbacks) -
# nothing to add a real-push-parity test for on that sensor.

# ISL29125 is dev-only (no wozi instance - CLAUDE.md). Of its ten config fields, only these four
# are hardware-backed with a real get-back path (asy_isl29125_driver.py's own _get_callbacks) - the
# rest are software-only knobs (trigger interval, auto-range settings, gain ratio) or command-only
# (ISLCalibrate) with nothing to read back. Deliberately different from the driver's own defaults
# (Resolution=16, Range=10000, IrCompOffset=0, IrCompAdjust=40) and all real, allowed settings.
# RangeAuto must also be pushed False here: under auto-range (the real default) the chip's own
# range bit is the state machine's choice, not the user's setting, so _read_sensor_dict() omits
# Range from a live snapshot entirely rather than let it misreport the auto-ranger's own pick
# (asy_isl29125_driver.py's own comment on this) - a real readback of a pushed Range needs it off.
_ISL29125_TEST_VALUES = {"Resolution": 12, "Range": 375, "RangeAuto": False, "IrCompOffset": 1, "IrCompAdjust": 20}


def test_bmp3xx_oversampling_and_filter_push_over_real_rest_and_readback(board: Board, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    get_before = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=10.0)
    assert get_before.status_code == 200, f"GET /sensors failed: {get_before.status_code} {get_before.body!r}"
    original: dict[str, Any] = {k: get_before.json()["BMP3XX"][k] for k in _BMP3XX_TEST_VALUES}

    try:
        put_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"BMP3XX": _BMP3XX_TEST_VALUES}, timeout_s=10.0)
        assert put_res.status_code == 200, f"PUT /sensors failed: {put_res.status_code} {put_res.body!r}"
        results = put_res.json()["result"]["BMP3XX"]
        failed = {k: results.get(k) for k in _BMP3XX_TEST_VALUES if results.get(k) != "Valid"}
        assert not failed, f"real hardware push rejected one or more fields: {failed!r} (full result: {results!r})"

        get_after = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=10.0)
        assert get_after.status_code == 200, f"GET /sensors after push failed: {get_after.status_code} {get_after.body!r}"
        actual = {k: get_after.json()["BMP3XX"][k] for k in _BMP3XX_TEST_VALUES}
        assert actual == _BMP3XX_TEST_VALUES, f"real hardware read-back does not match what was pushed: pushed {_BMP3XX_TEST_VALUES!r}, read back {actual!r}"
    finally:
        # Restore the board's original config regardless of outcome - this PUT mutates the real,
        # persisted config file and live hardware registers of a shared bench rig.
        restore_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"BMP3XX": original}, timeout_s=10.0)
        assert restore_res.status_code == 200, f"failed to restore original BMP3XX config {original!r}: {restore_res.status_code} {restore_res.body!r}"
        restore_results = restore_res.json()["result"]["BMP3XX"]
        assert all(v == "Valid" for v in restore_results.values()), f"restoring original BMP3XX config was rejected: {restore_results!r}"

    # A fully valid push-and-restore round trip is not a fault - config_manager.py's errno=12 only
    # fires on a rejected key, which none of these were.
    assert_module_error_log_empty(dut_ip, "BMP3XX")
    assert_module_error_log_empty(dut_ip, "CFGMGR_BMP3XX")


def test_isl29125_resolution_range_and_ir_comp_push_over_real_rest_and_readback(board: Board, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    get_before = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=10.0)
    assert get_before.status_code == 200, f"GET /sensors failed: {get_before.status_code} {get_before.body!r}"
    original: dict[str, Any] = {k: get_before.json()["ISL29125"][k] for k in _ISL29125_TEST_VALUES}

    try:
        put_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": _ISL29125_TEST_VALUES}, timeout_s=10.0)
        assert put_res.status_code == 200, f"PUT /sensors failed: {put_res.status_code} {put_res.body!r}"
        results = put_res.json()["result"]["ISL29125"]
        failed = {k: results.get(k) for k in _ISL29125_TEST_VALUES if results.get(k) != "Valid"}
        assert not failed, f"real hardware push rejected one or more fields: {failed!r} (full result: {results!r})"

        get_after = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=10.0)
        assert get_after.status_code == 200, f"GET /sensors after push failed: {get_after.status_code} {get_after.body!r}"
        actual = {k: get_after.json()["ISL29125"][k] for k in _ISL29125_TEST_VALUES}
        assert actual == _ISL29125_TEST_VALUES, f"real hardware read-back does not match what was pushed: pushed {_ISL29125_TEST_VALUES!r}, read back {actual!r}"
    finally:
        # Restore the board's original config regardless of outcome - this PUT mutates the real,
        # persisted config file and live hardware registers of a shared bench rig.
        restore_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": original}, timeout_s=10.0)
        assert restore_res.status_code == 200, f"failed to restore original ISL29125 config {original!r}: {restore_res.status_code} {restore_res.body!r}"
        restore_results = restore_res.json()["result"]["ISL29125"]
        assert all(v == "Valid" for v in restore_results.values()), f"restoring original ISL29125 config was rejected: {restore_results!r}"

    # A fully valid push-and-restore round trip is not a fault - config_manager.py's errno=12 only
    # fires on a rejected key, which none of these were.
    assert_module_error_log_empty(dut_ip, "ISL29125")
    assert_module_error_log_empty(dut_ip, "CFGMGR_ISL29125")


def test_notification_pause_time_push_counts_down_over_real_rest(board: Board, dut_ip: str) -> None:
    # PauseTime is dispatch-only (no GET /notification field to read back - it's deliberately
    # excluded from flat settings there), but IS a real live value under GET /status's own
    # "notification" section (buildgen's generated _notification_status(): "PauseTime":
    # await notification.get_override_led()) - proving the real auto_led_override() background
    # task actually decrements it on real hardware, not just that the PUT was accepted.
    reset_all_error_logs(dut_ip)
    put_res = http_client.fetch(dut_ip, 80, "PUT", "/notification", {"PauseTime": 3}, timeout_s=10.0)
    assert put_res.status_code == 200, f"PUT /notification PauseTime failed: {put_res.status_code} {put_res.body!r}"
    assert put_res.json()["result"].get("PauseTime") == "Valid", f"real PauseTime push was rejected: {put_res.json()['result']!r}"

    get_res = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0)
    assert get_res.status_code == 200, f"GET /status failed: {get_res.status_code} {get_res.body!r}"
    first = get_res.json()["notification"]["PauseTime"]
    assert first > 0, f"PauseTime read back as {first!r} immediately after a real push of 3 - the push never reached real hardware state"

    last = first
    reached_zero = False
    for _ in range(10):  # real ~1s-per-tick auto_led_override() cadence - 10s comfortably covers a 3s countdown
        time.sleep(1.0)
        get_res = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0)
        current = get_res.json()["notification"]["PauseTime"]
        assert current <= last, f"PauseTime increased ({last} -> {current}) - not a real, monotonic countdown"
        last = current
        if current == 0:
            reached_zero = True
            break
    assert reached_zero, "PauseTime never reached 0 on real hardware - the real auto_led_override() task isn't decrementing it"
    assert_module_error_log_empty(dut_ip, "NOTIFY")


def test_sgp40_reset_voc_command_push_over_real_rest(board: Board, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    # SGPResetVOC is command-only (never persisted - see asy_sgp40_driver.py's _VAL_RESET comment),
    # so there is no "original value" to restore afterward, unlike the BMP3xx fields above.
    put_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"SGPResetVOC": True}}, timeout_s=10.0)
    assert put_res.status_code == 200, f"PUT /sensors SGPResetVOC failed: {put_res.status_code} {put_res.body!r}"
    result = put_res.json()["result"]["SGP40"]
    assert result.get("SGPResetVOC") == "Valid", f"real reset_voc() push was rejected: {result!r}"

    # The sensor must still be alive and producing real readings afterward - a reset that wedged
    # the real algorithm/hardware would otherwise only surface as a silent later gap.
    get_res = http_client.fetch(dut_ip, 80, "GET", "/measurements", timeout_s=10.0)
    assert get_res.status_code == 200, f"GET /measurements after a real VOC reset failed: {get_res.status_code} {get_res.body!r}"
    assert_module_error_log_empty(dut_ip, "SGP40")
