"""Bench-tier automated tests: the real website and a real multi-sensor value-sanity check over
the *normal* STA/bridge network path (see tests_hardware/README.md). Bounds mirror the flash-tier
isolated-driver plausibility scripts' own datasheet-sourced bounds - loose plausibility, not exact-reference calibration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import http_client
import pytest
import website_identity
from harness import wait_until

if TYPE_CHECKING:
    from bench_control import BenchBridge
    from harness import Board

CO2_MIN_PPM, CO2_MAX_PPM = 400, 10_000
HUMIDITY_MIN_RH, HUMIDITY_MAX_RH = 0.0, 100.0
SCD30_TEMP_MIN_C, SCD30_TEMP_MAX_C = -40.0, 70.0
PRESSURE_MIN_HPA, PRESSURE_MAX_HPA = 300.0, 1250.0
BMP_TEMP_MIN_C, BMP_TEMP_MAX_C = -40.0, 85.0
VOC_MIN, VOC_MAX = 0, 500
RAW_MIN, RAW_MAX = 0, 65535

# ---------------------------------------------------------------------------
# The website, over the normal STA/bridge network path (not hotspot mode).
# ---------------------------------------------------------------------------


def test_real_static_website_content_serves_over_the_normal_bridge_network(board: Board, dut_ip: str) -> None:
    res = http_client.fetch(dut_ip, 80, "GET", "/", timeout_s=10.0)
    assert res.status_code == 200, f"GET / over the normal bridge network failed: {res.status_code} {res.body!r}"
    # 200-and-non-empty passes for another device's build too, so the body is checked against this
    # device's own generated definitions (queue row G9).
    website_identity.assert_page_is_this_devices_build(res, "the normal bridge network")


# ---------------------------------------------------------------------------
# Top-level API delivering sensible values, across all three real sensors together, over REST -
# not just HTTP status/shape (test_end_to_end_timing.py's concurrent-burst test only checks status).
# ---------------------------------------------------------------------------


def test_measurements_endpoint_returns_plausible_values_for_every_real_sensor(board: Board, dut_ip: str) -> None:
    res = http_client.fetch(dut_ip, 80, "GET", "/measurements", timeout_s=10.0)
    assert res.status_code == 200, f"GET /measurements failed: {res.status_code} {res.body!r}"
    body = res.json()

    for name in ("SCD30", "BMP3XX", "SGP40"):
        assert name in body, f"GET /measurements is missing the {name!r} key entirely: {body!r}"

    failures: list[str] = []

    scd30 = body["SCD30"]
    co2, hum, temp = scd30.get("CO2"), scd30.get("Hum"), scd30.get("Temp")
    if co2 is None or not (CO2_MIN_PPM <= co2 <= CO2_MAX_PPM):
        failures.append(f"SCD30.CO2={co2!r} not within [{CO2_MIN_PPM}, {CO2_MAX_PPM}] ppm")
    if hum is None or not (HUMIDITY_MIN_RH <= hum <= HUMIDITY_MAX_RH):
        failures.append(f"SCD30.Hum={hum!r} not within [{HUMIDITY_MIN_RH}, {HUMIDITY_MAX_RH}] %RH")
    if temp is None or not (SCD30_TEMP_MIN_C <= temp <= SCD30_TEMP_MAX_C):
        failures.append(f"SCD30.Temp={temp!r} not within [{SCD30_TEMP_MIN_C}, {SCD30_TEMP_MAX_C}] degC")

    bmp3xx = body["BMP3XX"]
    pres, bmp_temp, slpres = bmp3xx.get("Pres"), bmp3xx.get("Temp"), bmp3xx.get("SLPres")
    if pres is None or not (PRESSURE_MIN_HPA <= pres <= PRESSURE_MAX_HPA):
        failures.append(f"BMP3XX.Pres={pres!r} not within [{PRESSURE_MIN_HPA}, {PRESSURE_MAX_HPA}] hPa")
    if bmp_temp is None or not (BMP_TEMP_MIN_C <= bmp_temp <= BMP_TEMP_MAX_C):
        failures.append(f"BMP3XX.Temp={bmp_temp!r} not within [{BMP_TEMP_MIN_C}, {BMP_TEMP_MAX_C}] degC")
    if slpres is None or not (PRESSURE_MIN_HPA <= slpres <= PRESSURE_MAX_HPA):
        failures.append(f"BMP3XX.SLPres={slpres!r} not within [{PRESSURE_MIN_HPA}, {PRESSURE_MAX_HPA}] hPa")

    sgp40 = body["SGP40"]
    voc, raw = sgp40.get("VOC"), sgp40.get("Raw")
    if voc is None or not (VOC_MIN <= voc <= VOC_MAX):
        failures.append(f"SGP40.VOC={voc!r} not within [{VOC_MIN}, {VOC_MAX}]")
    if raw is None or not (RAW_MIN <= raw <= RAW_MAX):
        failures.append(f"SGP40.Raw={raw!r} not within [{RAW_MIN}, {RAW_MAX}]")

    assert not failures, "implausible/missing real sensor values via GET /measurements: " + "; ".join(failures) + f"\nfull body: {body!r}"


# ---------------------------------------------------------------------------
# The FRAM storage-pause gate end to end over the real HTTP stack. The mock tier covers the
# clamp/re-arm/abort logic and the flash tier the real chip gating and auto-unpause timer; only
# this tier proves the REST command reaches AsyFramManager and shows up in GET /status.
# ---------------------------------------------------------------------------


def test_mempause_over_real_rest_pauses_storage_and_does_not_survive_a_reboot(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    before = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0)
    assert before.status_code == 200, f"GET /status failed: {before.status_code} {before.body!r}"
    assert before.json()["system"]["MemPaused"] is False, "storage was already paused before this test ran - a previous test left the bench in a paused state"

    put_res = http_client.fetch(dut_ip, 80, "PUT", "/system", {"SystemCmd": "mempause"}, timeout_s=10.0)
    assert put_res.status_code == 200, f"PUT /system mempause failed: {put_res.status_code} {put_res.body!r}"

    paused = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0)
    assert paused.status_code == 200, f"GET /status after mempause failed: {paused.status_code} {paused.body!r}"
    assert paused.json()["system"]["MemPaused"] is True, f"MemPaused did not become True after a real PUT /system mempause: {paused.json()['system']!r}"

    # Recovery is a reboot, not a second REST call: the window is a fixed 300s and the duration
    # is never client-suppliable, so no REST unpause exists. That is also the assertion - the
    # pause is RAM-only, so a reset must clear it, which also leaves the bench usable.
    bench.kick_all_stations()  # see conftest.py's dut_ip docstring for why this precedes every reconnect-expecting reset
    board.hard_reset()
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200,
        timeout_s=120.0,
        poll_interval_s=3.0,
        description="DUT serving /status again after the recovery reboot",
    )
    after = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0)
    assert after.json()["system"]["MemPaused"] is False, f"storage was still paused after a real reboot - the pause is supposed to be RAM-only: {after.json()['system']!r}"


# ---------------------------------------------------------------------------
# ISL29125's applied gain ratio across a real reboot. The flash tier proves the config mechanism
# survives a hard reset generically; this adds the field whose classification is newest -
# GainRatio is ordinary user-PUT config now, not a self-learned runtime value.
# ---------------------------------------------------------------------------


@pytest.mark.persistence_write
def test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # Marked: this test OWNS its persisting writes (the probe PUT and the restore PUT), unlike the
    # dispatch-only ISLCalibrate push, which stores nothing. CLAUDE.md's wear rule, and the reason
    # tests_scripts/test_persistence_write_marker_completeness.py would fail without the marker.
    before = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=10.0)
    assert before.status_code == 200, f"GET /sensors failed: {before.status_code} {before.body!r}"
    original = before.json()["ISL29125"]["GainRatio"]
    assert original is not None, "GainRatio is a schema field with a default - it can never be absent"

    # Distinguishable from the nominal default, so the reboot leg proves persistence rather than
    # re-defaulting. Inside the driver's own [20, 34] band and exactly representable as a float.
    probe = 24.5 if abs(original - 24.5) > 0.01 else 27.25
    put = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": {"GainRatio": probe}}, timeout_s=10.0)
    assert put.status_code == 200, f"PUT /sensors GainRatio={probe} failed: {put.status_code} {put.body!r}"
    assert put.json()["result"]["ISL29125"].get("GainRatio") == "Valid", f"could not set GainRatio={probe}: {put.json()['result']['ISL29125']!r}"

    try:
        bench.kick_all_stations()  # see conftest.py's dut_ip docstring for why this precedes every reconnect-expecting reset
        board.hard_reset()
        wait_until(
            lambda: http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=5.0).status_code == 200,
            timeout_s=120.0,
            poll_interval_s=3.0,
            description="DUT serving /sensors again after the reboot this persistence check needs",
        )
        after = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=10.0).json()["ISL29125"]["GainRatio"]
        assert after == probe, f"GainRatio did not survive a real reboot: set {probe!r}, read back {after!r}"
    finally:
        # Restore regardless of outcome - this mutates the real, persisted config of a shared rig,
        # and the applied ratio scales every later reading across a range change.
        restore = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"ISL29125": {"GainRatio": original}}, timeout_s=10.0)
        assert restore.status_code == 200, f"failed to restore GainRatio={original!r}: {restore.status_code} {restore.body!r}"
        verdict = restore.json()["result"]["ISL29125"].get("GainRatio")
        # "Unchanged" counts as restored: if the probe PUT never landed, the board still holds the
        # original and this is a legitimate no-op - rejecting it would mask the real failure.
        assert verdict in ("Valid", "Unchanged"), f"restoring GainRatio={original!r} was rejected: {verdict!r}"
