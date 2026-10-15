"""Bench-tier automated tests: the real website and a real multi-sensor value-sanity check over
the *normal* STA/bridge network path (see tests_hardware/README.md). Every sensor the bench TOML declares is held to its
driver's sourced plausibility bounds (plausibility_bounds.py) - loose plausibility, not exact-reference calibration."""

from typing import TYPE_CHECKING

import _load
import http_client
import pytest
import website_identity

if TYPE_CHECKING:
    from bench_control import BenchBridge
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("real_website_integration", "sensortask_integration", "ci_suite._run_1_baseline")

# ---------------------------------------------------------------------------
# The website, over the normal STA/bridge network path (not hotspot mode).
# ---------------------------------------------------------------------------


# @tunable l4.rest_endpoints_over_sta_probe_timeout_s = 10.0
_PROBE_TIMEOUT_S = 10.0
# @tunable l4.rest_endpoints_over_sta_reboot_ready_timeout_s = 120.0
_REBOOT_READY_TIMEOUT_S = 120.0
_GAIN_RATIO_PROBES = (24.5, 27.25)  # inside the driver's [20, 34] band, exactly representable as floats


def test_real_static_website_content_serves_over_the_normal_bridge_network(board: "Board", dut_ip: str, bench_device_name: str) -> None:
    res = http_client.fetch(dut_ip, 80, "GET", "/", timeout_s=_PROBE_TIMEOUT_S)
    assert res.status_code == 200, f"GET / over the normal bridge network failed: {res.status_code} {res.body!r}"
    # 200-and-non-empty passes for another device's build too, so the body is checked against this
    # device's own generated definitions.
    website_identity.assert_page_is_this_devices_build(res, "the normal bridge network", device=bench_device_name)


# ---------------------------------------------------------------------------
# Top-level API delivering sensible values for every real sensor together, over REST -
# not just HTTP status/shape (test_end_to_end_timing.py's concurrent-burst test only checks status).
# ---------------------------------------------------------------------------


def test_measurements_endpoint_returns_plausible_values_for_every_real_sensor(board: "Board", dut_ip: str, bench_device_name: str) -> None:
    body = _load.get_object(dut_ip, "/measurements", _PROBE_TIMEOUT_S)
    findings = _load.measurement_findings(body, bench_device_name)
    assert not findings, "implausible/missing real sensor values via GET /measurements: " + "; ".join(findings) + f"\nfull body: {body!r}"


# ---------------------------------------------------------------------------
# The FRAM storage-pause gate end to end over the real HTTP stack. The mock tier covers the
# clamp/re-arm/abort logic and the flash tier the real chip gating and auto-unpause timer; only
# this tier proves the REST command reaches FRAMManager and shows up in GET /status.
# ---------------------------------------------------------------------------


def test_mempause_over_real_rest_pauses_storage_and_does_not_survive_a_reboot(board: "Board", bench: "BenchBridge", dut_ip: str) -> None:
    assert _mem_paused(dut_ip) is False, "storage was already paused before this test ran - a previous test left the bench in a paused state"
    put_res = http_client.fetch(dut_ip, 80, "PUT", "/system", {"SystemCmd": "mempause"}, timeout_s=_PROBE_TIMEOUT_S)
    assert _load.as_object(put_res.json().get("result"), "result").get("SystemCmd") == "Valid", f"PUT /system mempause failed: {put_res.status_code} {put_res.body!r}"
    assert _mem_paused(dut_ip) is True, "MemPaused did not become True after a real PUT /system mempause"
    # Recovery is a reboot, not a second REST call: the window is a fixed 300s and the duration
    # is never client-suppliable, so no REST unpause exists. That is also the assertion - the
    # pause is RAM-only, so a reset must clear it, which also leaves the bench usable.
    _load.reset_and_wait(board, bench, dut_ip, timeout_s=_REBOOT_READY_TIMEOUT_S)
    assert _mem_paused(dut_ip) is False, "storage was still paused after a real reboot - the pause is supposed to be RAM-only"


# ---------------------------------------------------------------------------
# ISL29125's applied gain ratio across a real reboot. The flash tier proves the config mechanism
# survives a hard reset generically; this adds the field whose classification is newest -
# GainRatio is ordinary user-PUT config now, not a self-learned runtime value.
# ---------------------------------------------------------------------------


@pytest.mark.persistence_write
def test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value(board: "Board", bench: "BenchBridge", dut_ip: str) -> None:
    # Marked: this test OWNS its persisting writes (the probe PUT and the restore PUT), unlike the
    # dispatch-only Calibrate push, which stores nothing (CLAUDE.md's wear rule).
    original = _gain_ratio(dut_ip)
    assert isinstance(original, (int, float)), f"GainRatio is a schema field with a default - it can never be absent: {original!r}"
    # Distinguishable from the board's value, so the reboot leg proves persistence rather than re-defaulting.
    probe = _GAIN_RATIO_PROBES[1] if abs(original - _GAIN_RATIO_PROBES[0]) <= 0.01 else _GAIN_RATIO_PROBES[0]
    put = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": {"GainRatio": probe}}, timeout_s=_PROBE_TIMEOUT_S)
    word = _load.as_object(_load.as_object(put.json().get("result"), "result").get("ISL29125"), "result.ISL29125").get("GainRatio")
    assert put.status_code == 200 and word == "Valid", f"could not set GainRatio={probe}: {put.status_code} {put.body!r}"
    try:
        _load.reset_and_wait(board, bench, dut_ip, timeout_s=_REBOOT_READY_TIMEOUT_S)  # the reboot the persistence check needs
        after = _gain_ratio(dut_ip)
        assert after == probe, f"GainRatio did not survive a real reboot: set {probe!r}, read back {after!r}"
    finally:
        # Restored on every path: the applied ratio scales every later reading across a range change.
        restore = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": {"GainRatio": original}}, timeout_s=_PROBE_TIMEOUT_S)
        verdict = _load.as_object(_load.as_object(restore.json().get("result"), "result").get("ISL29125"), "result.ISL29125").get("GainRatio")
        # "Unchanged" counts as restored: if the probe PUT never landed, the board still holds the original.
        assert verdict in ("Valid", "Unchanged"), f"restoring GainRatio={original!r} was rejected: {restore.status_code} {restore.body!r}"


def _gain_ratio(dut_ip: str) -> object:
    return _load.as_object(_load.get_object(dut_ip, "/sensors", _PROBE_TIMEOUT_S).get("ISL29125"), "GET /sensors ISL29125").get("GainRatio")


def _mem_paused(dut_ip: str) -> object:
    return _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("system"), "GET /status system").get("MemPaused")
