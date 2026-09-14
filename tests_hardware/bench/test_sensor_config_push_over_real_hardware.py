"""Bench-tier automated tests: real PUT /sensors config pushes against real hardware, the
real-hardware counterpart to tests/test_setter_microdot_integration.py's mock. A "Valid" result
plus a follow-up GET /sensors confirms the live-push callback ran a real I2C write and it stuck."""

from __future__ import annotations

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


# All three are live-push fields (a real I2C write, not just a stored value) and all three differ
# from the schema defaults: 12-bit resolution is a CONFIG1 write that also restarts the conversion,
# and the two IR-compensation fields are a CONFIG2 write that does not.
_ISL29125_TEST_VALUES = {"Resolution": 12, "IrCompOffset": 1, "IrCompAdjust": 20}


def test_isl29125_resolution_and_ir_compensation_push_over_real_rest_and_readback(board: Board, dut_ip: str) -> None:
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

        # A resolution change rescales the auto-range thresholds, so the sensor must still be
        # producing real data at 12 bit - not merely have accepted the write.
        measurements = http_client.fetch(dut_ip, 80, "GET", "/measurements", timeout_s=10.0)
        assert measurements.status_code == 200, f"GET /measurements after the resolution push failed: {measurements.status_code} {measurements.body!r}"
        assert measurements.json()["ISL29125"].get("RangeAct") in (375, 10_000), f"ISL29125 stopped reporting a real range after a 12-bit push: {measurements.json()['ISL29125']!r}"
    finally:
        restore_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": original}, timeout_s=10.0)
        assert restore_res.status_code == 200, f"failed to restore original ISL29125 config {original!r}: {restore_res.status_code} {restore_res.body!r}"
        restore_results = restore_res.json()["result"]["ISL29125"]
        assert all(v == "Valid" for v in restore_results.values()), f"restoring original ISL29125 config was rejected: {restore_results!r}"

    assert_module_error_log_empty(dut_ip, "ISL29125")
    assert_module_error_log_empty(dut_ip, "CFGMGR_ISL29125")


def test_isl29125_calibrate_command_push_over_real_rest(board: Board, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    # ISLCalibrate is command-only, like SGPResetVOC above - never persisted, so there is nothing
    # to restore. It starts a bounded measuring run and must not disturb the APPLIED ratio, which
    # is an ordinary config value only a PUT can change; that is what the readback below pins.
    before = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=10.0)
    assert before.status_code == 200, f"GET /sensors failed: {before.status_code} {before.body!r}"
    applied = before.json()["ISL29125"]["GainRatio"]

    put_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": {"ISLCalibrate": True}}, timeout_s=10.0)
    assert put_res.status_code == 200, f"PUT /sensors ISLCalibrate failed: {put_res.status_code} {put_res.body!r}"
    result = put_res.json()["result"]["ISL29125"]
    assert result.get("ISLCalibrate") == "Valid", f"real start_calibration() push was rejected: {result!r}"

    after = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=10.0)
    assert after.status_code == 200, f"GET /sensors after starting a calibration failed: {after.status_code} {after.body!r}"
    assert after.json()["ISL29125"]["GainRatio"] == applied, "a calibration run must never move the applied ratio"

    get_res = http_client.fetch(dut_ip, 80, "GET", "/measurements", timeout_s=10.0)
    assert get_res.status_code == 200, f"GET /measurements after starting a calibration failed: {get_res.status_code} {get_res.body!r}"
    # GainMeas rides the measurement tuple and is legitimately null until a run produces a stable
    # pair, so its presence is the contract here, not its value - the bench light is not arranged.
    assert "GainMeas" in get_res.json()["ISL29125"], f"GET /measurements lost GainMeas: {get_res.json()['ISL29125']!r}"
    # An empty log, not an allowlist: a run that finds no usable scene reports that by leaving
    # GainMeas null, never by warning. The two wrnnos this used to permit no longer exist.
    assert_module_error_log_empty(dut_ip, "ISL29125")
