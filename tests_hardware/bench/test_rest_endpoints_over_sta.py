"""Bench-tier automated tests: the real website and a real multi-sensor value-sanity check over
the *normal* STA/bridge network path (see tests_hardware/README.md). Bounds mirror the flash-tier
isolated-driver plausibility scripts' own datasheet-sourced bounds - loose plausibility, not exact-reference calibration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import http_client
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
    assert len(res.body) > 0, "GET / returned an empty body over the normal bridge network"


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
# The FRAM storage-pause gate, end to end over the real HTTP stack. The mock tier covers the
# clamp/re-arm/abort logic and the flash tier covers the real chip gating plus the real
# auto-unpause timer; what only this tier can prove is that the REST command actually reaches
# AsyFramManager on a real device and is visible in GET /status.
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

    # Recovery is a reboot, not a second REST call: the pause window is a fixed 300s and the
    # duration is never client-suppliable (asy_webserver_service.py forwards the enum string only),
    # so there is no REST unpause to issue. That constraint is also the assertion - AsyFramManager
    # sets _pause = False in __init__ and nothing ever restores it from FRAM, so the pause is
    # RAM-only and a reset must clear it. Leaving the bench unpaused for whatever runs next is a
    # required side effect, not incidental cleanup.
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
