"""Bench-tier automated tests: real PUT /sensors and PUT /notification config pushes against real
hardware, the real-hardware counterpart to tests/test_setter_microdot_integration.py's mock. A
"Valid" result plus a follow-up GET confirms the live-push callback took effect and stuck."""

import time
from typing import TYPE_CHECKING

import _load
import evidence
import http_client
import pytest
from error_log_helpers import assert_module_error_log_empty, reset_all_error_logs
from harness import schema_default

if TYPE_CHECKING:
    from collections.abc import Mapping

    from harness import Board
    from http_client import JSONObject, JSONValue

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ()

# Different from every driver default (PresOvers=1, TempOvers=1, FiltCoeff=0) and all real
# allowed discrete settings (_OSR_SETTINGS, _IIR_SETTINGS in asy_bmp3xx_driver.py): a real change
# has to take effect on real hardware for this test to mean anything.
_BMP3XX_TEST_VALUES = {"PresOvers": 4, "TempOvers": 2, "FiltCoeff": 3}

# SCD30's own push spends real NVM wear through its chip store: the gated Altitude test at the end of this module.

# ISL29125 is dev-only. Of its ten config fields only these four are hardware-backed with a real
# get-back path (_get_callbacks); the rest are software knobs or command-only. Values chosen away
# from the defaults (Resolution=16, Range=10000, IRCompOffset=0, IRCompAdjust=40).

# RangeAuto goes False with them because under auto-range the chip's range bit is the state
# machine's pick, not the user's, so _read_sensor_dict() omits Range from a live snapshot
# entirely - reading back a pushed Range needs the auto-ranger off.
_ISL29125_TEST_VALUES = {"Resolution": 12, "Range": 375, "RangeAuto": False, "IRCompOffset": 1, "IRCompAdjust": 20}


# @tunable l4.sensor_config_push_over_real_hardware_probe_timeout_s = 10.0
_PROBE_TIMEOUT_S = 10.0
# @tunable l4.sensor_config_push_over_real_hardware_override_poll_s = 1.0
_OVERRIDE_POLL_S = 1.0
# @tunable l4.sensor_config_push_over_real_hardware_override_poll_tries = 10
_OVERRIDE_POLL_TRIES = 10
_BMP3XX_SRC = "asy_bmp3xx_driver.py"
_ISL29125_SRC = "asy_isl29125_driver.py"
_SCD30_SRC = "asy_scd30_driver.py"
# A shift the compensation must show, kept inside _VAL_ALTITUDE's range either way round.
# @tunable l4.sensor_config_push_altitude_step_m = 1000
_ALTITUDE_STEP_M = 1000
# @tunable l4.sensor_config_push_altitude_settle_intervals = 3
_SETTLE_INTERVALS = 3
# @tunable l4.sensor_config_push_altitude_observe_intervals = 5
_OBSERVE_INTERVALS = 5


@pytest.mark.persistence_write
def test_bmp3xx_oversampling_and_filter_push_over_real_rest_and_readback(board: "Board", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    original = _original(dut_ip, "BMP3XX", _BMP3XX_SRC, dict(_BMP3XX_TEST_VALUES), result_note)

    try:
        put_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"BMP3XX": _json_object(_BMP3XX_TEST_VALUES)}, timeout_s=_PROBE_TIMEOUT_S)
        assert put_res.status_code == 200, f"PUT /sensors failed: {put_res.status_code} {put_res.body!r}"
        results = _load.as_object(_load.as_object(put_res.json().get("result"), "result").get("BMP3XX"), "result.BMP3XX")
        failed = {k: results.get(k) for k in _BMP3XX_TEST_VALUES if results.get(k) != "Valid"}
        assert not failed, f"real hardware push rejected one or more fields: {failed!r} (full result: {results!r})"

        get_after = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=_PROBE_TIMEOUT_S)
        assert get_after.status_code == 200, f"GET /sensors after push failed: {get_after.status_code} {get_after.body!r}"
        actual = {k: _load.as_object(get_after.json().get("BMP3XX"), "GET /sensors BMP3XX").get(k) for k in _BMP3XX_TEST_VALUES}
        assert actual == _BMP3XX_TEST_VALUES, f"real hardware read-back does not match what was pushed: pushed {_BMP3XX_TEST_VALUES!r}, read back {actual!r}"
    finally:
        # Restore the board's original config regardless of outcome - this PUT mutates the real,
        # persisted config file and live hardware registers of a shared bench rig.
        restore_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"BMP3XX": original}, timeout_s=_PROBE_TIMEOUT_S)
        assert restore_res.status_code == 200, f"failed to restore original BMP3XX config {original!r}: {restore_res.status_code} {restore_res.body!r}"
        restore_results = _load.as_object(_load.as_object(restore_res.json().get("result"), "result").get("BMP3XX"), "result.BMP3XX")
        # "Unchanged" counts as restored: if the body failed before its own PUT landed, the board is
        # still at `original` and this is a legitimate no-op - rejecting it would replace the real
        # failure with a cleanup assertion.
        assert all(v in ("Valid", "Unchanged") for v in restore_results.values()), f"restoring original BMP3XX config was rejected: {restore_results!r}"

    # A fully valid push-and-restore round trip is not a fault - asy_config_manager.py's BAD_ARG only
    # fires on a rejected key, which none of these were.
    assert_module_error_log_empty(dut_ip, "BMP3XX")
    assert_module_error_log_empty(dut_ip, "CFGMGR_BMP3XX")


@pytest.mark.persistence_write
def test_isl29125_resolution_range_and_ir_comp_push_over_real_rest_and_readback(board: "Board", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    original = _original(dut_ip, "ISL29125", _ISL29125_SRC, dict(_ISL29125_TEST_VALUES), result_note)

    try:
        put_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": _json_object(_ISL29125_TEST_VALUES)}, timeout_s=_PROBE_TIMEOUT_S)
        assert put_res.status_code == 200, f"PUT /sensors failed: {put_res.status_code} {put_res.body!r}"
        results = _load.as_object(_load.as_object(put_res.json().get("result"), "result").get("ISL29125"), "result.ISL29125")
        failed = {k: results.get(k) for k in _ISL29125_TEST_VALUES if results.get(k) != "Valid"}
        assert not failed, f"real hardware push rejected one or more fields: {failed!r} (full result: {results!r})"

        get_after = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=_PROBE_TIMEOUT_S)
        assert get_after.status_code == 200, f"GET /sensors after push failed: {get_after.status_code} {get_after.body!r}"
        actual = {k: _load.as_object(get_after.json().get("ISL29125"), "GET /sensors ISL29125").get(k) for k in _ISL29125_TEST_VALUES}
        assert actual == _ISL29125_TEST_VALUES, f"real hardware read-back does not match what was pushed: pushed {_ISL29125_TEST_VALUES!r}, read back {actual!r}"
    finally:
        # Restore the board's original config regardless of outcome - this PUT mutates the real,
        # persisted config file and live hardware registers of a shared bench rig.
        restore_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": original}, timeout_s=_PROBE_TIMEOUT_S)
        assert restore_res.status_code == 200, f"failed to restore original ISL29125 config {original!r}: {restore_res.status_code} {restore_res.body!r}"
        restore_results = _load.as_object(_load.as_object(restore_res.json().get("result"), "result").get("ISL29125"), "result.ISL29125")
        # "Unchanged" counts as restored: if the body failed before its own PUT landed, the board is
        # still at `original` and this is a legitimate no-op - rejecting it would replace the real
        # failure with a cleanup assertion.
        assert all(v in ("Valid", "Unchanged") for v in restore_results.values()), f"restoring original ISL29125 config was rejected: {restore_results!r}"

    # A fully valid push-and-restore round trip is not a fault - asy_config_manager.py's BAD_ARG only
    # fires on a rejected key, which none of these were.
    assert_module_error_log_empty(dut_ip, "ISL29125")
    assert_module_error_log_empty(dut_ip, "CFGMGR_ISL29125")


def test_notification_pause_time_push_counts_down_over_real_rest(board: "Board", dut_ip: str, request: pytest.FixtureRequest) -> None:
    # PauseTime counts down measured time over real HTTP: dispatch-only, so GET /notification has nothing to read back,
    # but GET /status's notification section carries it live, which proves more than the PUT's own answer.
    reset_all_error_logs(dut_ip, request.node.name)
    put_res = http_client.fetch(dut_ip, 80, "PUT", "/notification", {"PauseTime": 3}, timeout_s=_PROBE_TIMEOUT_S)
    assert put_res.status_code == 200, f"PUT /notification PauseTime failed: {put_res.status_code} {put_res.body!r}"
    assert _load.as_object(put_res.json().get("result"), "result").get("PauseTime") == "Valid", f"real PauseTime push was rejected: {put_res.body!r}"

    first = _pause_time(dut_ip)
    assert first > 0, f"PauseTime read back as {first!r} immediately after a real push of 3 - the push never reached real hardware state"

    last = first
    reached_zero = False
    for _ in range(_OVERRIDE_POLL_TRIES):  # real ~1s-per-tick _pause_loop() cadence - 10s comfortably covers a 3s countdown
        time.sleep(_OVERRIDE_POLL_S)
        current = _pause_time(dut_ip)
        assert current <= last, f"PauseTime increased ({last} -> {current}) - not a real, monotonic countdown"
        last = current
        if current == 0:
            reached_zero = True
            break
    assert reached_zero, "PauseTime never reached 0"
    assert_module_error_log_empty(dut_ip, "NOTIFY")


def test_sgp40_reset_voc_command_push_over_real_rest(board: "Board", dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    # ResetVOC is command-only (never persisted - see asy_sgp40_driver.py's _VAL_RESET_VOC comment),
    # so there is no "original value" to restore afterward, unlike the BMP3xx fields above.
    put_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"ResetVOC": True}}, timeout_s=_PROBE_TIMEOUT_S)
    assert put_res.status_code == 200, f"PUT /sensors ResetVOC failed: {put_res.status_code} {put_res.body!r}"
    result = _load.as_object(_load.as_object(put_res.json().get("result"), "result").get("SGP40"), "result.SGP40")
    assert result.get("ResetVOC") == "Valid", f"real reset_voc() push was rejected: {result!r}"

    # The sensor must still be alive and producing real readings afterward - a reset that wedged
    # the real algorithm/hardware would otherwise only surface as a silent later gap.
    get_res = http_client.fetch(dut_ip, 80, "GET", "/measurements", timeout_s=_PROBE_TIMEOUT_S)
    assert get_res.status_code == 200, f"GET /measurements after a real VOC reset failed: {get_res.status_code} {get_res.body!r}"
    assert_module_error_log_empty(dut_ip, "SGP40")


def test_isl29125_calibrate_command_push_over_real_rest(board: "Board", dut_ip: str, request: pytest.FixtureRequest) -> None:
    # The one ISL29125 field the test above excludes, for the reason that earns it its own:
    # Calibrate is command-only, so no readback can show it took effect. What can be pinned is
    # the pair of invariants a run must respect, reachable only from the real REST stack.
    reset_all_error_logs(dut_ip, request.node.name)
    applied = _isl29125(dut_ip, "/sensors").get("GainRatio")
    assert applied is not None, "GainRatio is a schema field with a default - it can never be absent"

    put_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": {"Calibrate": True}}, timeout_s=_PROBE_TIMEOUT_S)
    assert put_res.status_code == 200, f"PUT /sensors Calibrate failed: {put_res.status_code} {put_res.body!r}"
    result = _load.as_object(_load.as_object(put_res.json().get("result"), "result").get("ISL29125"), "result.ISL29125")
    assert result.get("Calibrate") == "Valid", f"real start_calibration() push was rejected: {result!r}"

    # Invariant 1: a calibration run measures a CANDIDATE ratio and must never become the applied
    # one - GainRatio is ordinary config, moved only by a user PUT (asy_isl29125_driver.py's own
    # "the APPLIED factor, replaced only by a config push").
    after = _isl29125(dut_ip, "/sensors").get("GainRatio")
    assert after == applied, f"a calibration run must never move the applied ratio: was {applied!r}, now {after!r}"

    # Invariant 2: the measured candidate reaches the operator through the measurement body, which
    # is the only place it is published. Its PRESENCE is the contract, not its value - a run that
    # finds no usable scene legitimately leaves it null, and the bench light is not arranged.
    meas = _isl29125(dut_ip, "/measurements")
    assert "GainMeas" in meas, f"GET /measurements lost GainMeas: {meas!r}"

    # An empty log, not an allowlist: a run that finds no usable scene reports that by leaving
    # GainMeas null, never by warning.
    assert_module_error_log_empty(dut_ip, "ISL29125")


# ---------------------------------------------------------------------------
# SCD30's Altitude compensation while AmbPres is 0 (its help text: "only used while Ambient Pressure is 0"), measured on
# the chip: four owned NVM writes (AmbPres 0, the Altitude step, and both restores), so behind both write gates.
# ---------------------------------------------------------------------------


@pytest.mark.persistence_write
@pytest.mark.scd30_extra_write
def test_scd30_altitude_takes_effect_while_ambient_pressure_is_zero(dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    scd30 = _load.as_object(_load.get_object(dut_ip, "/sensors", _PROBE_TIMEOUT_S).get("SCD30"), "GET /sensors SCD30")
    amb, altitude, interval = scd30.get("AmbPres"), scd30.get("Altitude"), scd30.get("MeasInterval")
    assert isinstance(amb, int) and isinstance(altitude, int) and isinstance(interval, int), f"GET /sensors SCD30 lacks AmbPres/Altitude/MeasInterval: {scd30!r}"
    alt_max = _load.field_schema(_SCD30_SRC, "Altitude")[3]
    assert isinstance(alt_max, int), f"_VAL_ALTITUDE declares no int upper bound: {alt_max!r}"
    stepped = altitude + _ALTITUDE_STEP_M if altitude + _ALTITUDE_STEP_M <= alt_max else altitude - _ALTITUDE_STEP_M
    record: dict[str, JSONValue] = {"AmbPres": amb, "Altitude": altitude, "stepped": stepped, "interval_s": interval}
    words: dict[str, JSONValue] = {}
    try:
        res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SCD30": {"AmbPres": 0}}, timeout_s=_PROBE_TIMEOUT_S)
        words["AmbPres 0"] = _load.as_object(_load.as_object(res.json().get("result"), "result").get("SCD30"), "result.SCD30").get("AmbPres")
        assert words["AmbPres 0"] == "Valid", f"AmbPres 0 was refused: {res.status_code} {res.body!r}"
        record["before"] = list(_co2_samples(dut_ip, _SETTLE_INTERVALS, interval))
        res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SCD30": {"Altitude": stepped}}, timeout_s=_PROBE_TIMEOUT_S)
        words["Altitude step"] = _load.as_object(_load.as_object(res.json().get("result"), "result").get("SCD30"), "result.SCD30").get("Altitude")
        assert words["Altitude step"] == "Valid", f"Altitude {stepped} was refused: {res.status_code} {res.body!r}"
        record["after"] = list(_co2_samples(dut_ip, _OBSERVE_INTERVALS, interval))
    finally:
        restore = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SCD30": {"Altitude": altitude}}, timeout_s=_PROBE_TIMEOUT_S)
        words["Altitude restore"] = _load.as_object(_load.as_object(restore.json().get("result"), "result").get("SCD30"), "result.SCD30").get("Altitude")
        restore = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SCD30": {"AmbPres": amb}}, timeout_s=_PROBE_TIMEOUT_S)
        words["AmbPres restore"] = _load.as_object(_load.as_object(restore.json().get("result"), "result").get("SCD30"), "result.SCD30").get("AmbPres")
        record["words"] = words
        path = evidence.save_json("scd30-altitude-at-ambpres-0.json", record)
        result_note(f"SCD30 Altitude {altitude} -> {stepped} m at AmbPres 0: CO2 before {[s.get('CO2') for s in _objects(record.get('before'))]}, after {[s.get('CO2') for s in _objects(record.get('after'))]} ({path.name})")
    assert words["Altitude restore"] in ("Valid", "Unchanged") and words["AmbPres restore"] in ("Valid", "Unchanged"), f"a restore was refused: {words}"
    assert_module_error_log_empty(dut_ip, "CFGMGR_SCD30")


def _co2_samples(dut_ip: str, intervals: int, interval_s: int) -> "list[JSONObject]":
    # One /measurements SCD30 sample per measurement interval: its CO2, its TS and the host time.
    samples: list[JSONObject] = []
    for _ in range(intervals):
        time.sleep(interval_s)
        data = _load.as_object(_load.get_object(dut_ip, "/measurements", _PROBE_TIMEOUT_S).get("SCD30"), "GET /measurements SCD30")
        samples.append({"t": time.time(), "TS": data.get("TS"), "CO2": data.get("CO2")})
    return samples


def _isl29125(dut_ip: str, path: str) -> "JSONObject":
    return _load.as_object(_load.get_object(dut_ip, path, _PROBE_TIMEOUT_S).get("ISL29125"), f"GET {path} ISL29125")


def _json(value: object) -> "JSONValue":
    assert value is None or isinstance(value, (bool, int, float, str)), f"a schema default {value!r} is no JSON scalar"
    return value


def _json_object(values: "Mapping[str, JSONValue]") -> "JSONObject":
    # A test-values table as the JSON object a PUT body nests.
    return dict(values)


def _objects(value: "JSONValue") -> "list[JSONObject]":
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _original(dut_ip: str, name: str, src_file: str, values: "dict[str, object]", result_note: "_load.Note") -> "JSONObject":
    # The board's values of the pushed fields; a field still holding its test value (an earlier run aborted before its
    # restore, so its PUT would read "Unchanged" and push nothing) is first repaired to its schema default, noted.
    current = _load.as_object(_load.get_object(dut_ip, "/sensors", _PROBE_TIMEOUT_S).get(name), f"GET /sensors {name}")
    leftover: JSONObject = {field: _json(schema_default(src_file, field)) for field, value in values.items() if current.get(field) == value}
    if leftover:
        _load._repair_leftover(dut_ip, "/sensors", {name: leftover})
        result_note(f"repaired a leftover {name} {sorted(leftover)} from an aborted run to the schema defaults", recovery=True)
        current = _load.as_object(_load.get_object(dut_ip, "/sensors", _PROBE_TIMEOUT_S).get(name), f"GET /sensors {name}")
    return {field: current.get(field) for field in values}


def _pause_time(dut_ip: str) -> int:
    value = _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("notification"), "GET /status notification").get("PauseTime")
    assert isinstance(value, int), f"GET /status carries no int PauseTime: {value!r}"
    return value
