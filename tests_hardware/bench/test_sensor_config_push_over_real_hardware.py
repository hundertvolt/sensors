"""Bench-tier automated tests, gap fix: real PUT /sensors config pushes against real hardware -
the "integration checks currently running on mocks shall be done for real wherever possible" ask
(tests/test_setter_microdot_integration.py exercises this exact REST path against a fake sensor
module; this file is its real-hardware counterpart). A "Valid" result in the response is direct
evidence the real live-push callback (asy_bmp3xx_driver.py's set_pressure_oversampling()/
set_temperature_oversampling()/set_filter_coefficient(), asy_sgp40_driver.py's reset_voc()) ran
a real I2C write against real hardware and didn't fail - base_classes.py's _set_dict_cfg() only
reports "Valid" once persistence succeeded AND the push callback itself returned True. A follow-up
GET /sensors confirms the values were actually applied on the real sensor (BMP3XX_I2C.get_config_snapshot()
reads the real OSR/CONFIG registers back), not just accepted.

SCD30 has no live-push config fields at all (asy_scd30_driver.py registers no _push_callbacks
entries - confirmed directly) - there is nothing to add a real-push-parity test for on that sensor."""

from __future__ import annotations

from typing import Any

import http_client
from error_log_helpers import assert_module_error_log_empty, reset_all_error_logs
from harness import Board

# Deliberately different from every driver default (_VAL_POV/_VAL_TOV/_VAL_FC in
# asy_bmp3xx_driver.py: PressOvers=1, TempOvers=1, FiltCoeff=0) and all real, allowed discrete
# settings (_OSR_SETTINGS=(1,2,4,8,16,32), _IIR_SETTINGS=(0,1,3,7,15,31,63,127)) - a real change
# must actually take effect on the real hardware for this test to mean anything.
_BMP3XX_TEST_VALUES = {"PressOvers": 4, "TempOvers": 2, "FiltCoeff": 3}


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

    # A fully valid push-and-restore round trip is not a fault - config_manager.py's own errno=12
    # (see test_network_resilience.py's nonsense-field-values test) only fires on a rejected
    # key, which none of these were. Both BMP3XX and its own CFGMGR_BMP3XX log are checked.
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
