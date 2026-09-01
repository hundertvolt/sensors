"""Bench-tier automated tests, gap fix found on a later audit pass (see tests_hardware/README.md's
"gaps found and closed" section): the real website and a real multi-sensor value-sanity check, both
served over the *normal* STA/bridge network path. Before this file, the only "GET /" check anywhere
in this tier was inside test_hotspot_role_reversal.py's hotspot-mode-only scenario, and no test
anywhere checked GET /measurements' actual sensor *values* across all three sensors together (only
HTTP status/shape - see test_end_to_end_timing.py's own concurrent-burst test, and BACKLOG.md/
asy_webserver_service.py's own _get_measurements()/_get_sensors() docstring for the flat-dict shape
this relies on). Bounds mirror the flash-tier isolated-driver plausibility scripts' own datasheet-
sourced bounds (device_scripts/{scd30,bmp3xx,sgp40_voc_algorithm_quality}*.py) - loose plausibility,
not exact-reference calibration."""

from __future__ import annotations

import http_client
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
