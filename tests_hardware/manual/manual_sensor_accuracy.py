"""Manual tests, an execution mode of L3 (manual/runner.py): real sensor accuracy against a genuine external
reference - apart from flash/test_sensor_accuracy.py's automated plausibility check (sane bounds, not an exact
reference) - and the NeoPixel rig's geometry, recorded as evidence."""

import datetime

import bench_facts
import evidence
from harness import bench_device
from runner import confirm, confirm_pass, print_instruction, register, state_expected_outcome

_DUT_IP_HINT = "the DUT's IP (see tests_hardware/README.md for how to find it)"

# The fitted BMP384, datasheets/bmp3xx/bst-bmp384-ds003.pdf Table 2 (pp. 6-7): absolute pressure accuracy +-0.50 hPa
# (300-1100 hPa, 0-65 degC), absolute temperature accuracy +-0.65 degC (0-65 degC). The BMP388 sheet's +-0.5 degC differs.
_BMP384_PRESSURE_TOLERANCE_HPA = 0.5  # source: datasheets/bmp3xx/bst-bmp384-ds003.pdf Table 2, p. 7
_BMP384_TEMP_TOLERANCE_C = 0.65  # source: datasheets/bmp3xx/bst-bmp384-ds003.pdf Table 2, p. 7

# SGP40 response, datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf Table 1: VOC Index 1-500, response time
# <10 s (63%) to <30 s (90%) for a 5 -> 10 ppm ethanol step, <60 s after switch-on until VOC events are reliable.
_SGP40_RESPONSE_63_PCT_S = 10
_SGP40_RESPONSE_90_PCT_S = 30

# The ISL29125 datasheet states no lux accuracy, and absolute lux or CCT against a WS2812's three narrow emission
# lines means nothing - hence the automated sweep's relative-only checks. By hand: repeatability and range continuity.
# @tunable l4.manual_sensor_accuracy_isl29125_repeatability_pct = 10.0
_ISL29125_REPEATABILITY_TOLERANCE_PCT = 10.0


def _neopixel_pin() -> object:
    # The bench board's NeoPixel data pin, from its TOML through the rendered bench facts.
    instances = bench_facts.build(bench_device())["instances"]
    assert isinstance(instances, dict), f"no instance table in the bench facts: {instances!r}"
    return next((spec.get("pin") for spec in instances.values() if isinstance(spec, dict) and spec.get("driver") == "neopixel"), "unwired")


@register(
    "bmp3xx_real_pressure_temperature_vs_reference",
    f"Supply a reference reading (a calibrated barometer, or a known-altitude/known-pressure location) and compare against the DUT's BMP384 reading within its datasheet's absolute accuracy (+-{_BMP384_PRESSURE_TOLERANCE_HPA} hPa, +-{_BMP384_TEMP_TOLERANCE_C} degC - datasheets/bmp3xx/bst-bmp384-ds003.pdf Table 2). The twin's calibration block is not a real chip's, so this validates the compensation against genuine factory trim.",
    "[USB+WiFi][MANUAL]",
)
def test_bmp3xx_real_pressure_temperature_vs_reference() -> None:
    print_instruction(f"Fetch the DUT's current BMP3XX reading now: GET /measurements against {_DUT_IP_HINT}, note its Pres (hPa) and Temp (degC) fields.")
    confirm("Press Enter once you've noted the DUT's own reading")
    print_instruction("Now obtain a reference reading from a calibrated barometer, or compute the expected pressure for a known-altitude location (e.g. a weather-station figure, adjusted for the DUT's altitude).")
    reference_pressure = input("    Enter the reference pressure in hPa: ").strip()
    reference_temp = input("    Enter the reference temperature in degC: ").strip()
    print_instruction(f"Reference: {reference_pressure} hPa, {reference_temp} degC.")
    state_expected_outcome(f"the DUT's Pres is within +-{_BMP384_PRESSURE_TOLERANCE_HPA} hPa of the reference, and Temp within +-{_BMP384_TEMP_TOLERANCE_C} degC.")
    confirm_pass("Are both within those tolerances? [y/N]")


@register(
    "sgp40_real_voc_index_response_to_real_stimulus",
    f"Apply a stated chemical stimulus (e.g. an isopropyl-alcohol swab held near the sensor) for a stated window, then remove it, and confirm the VOC index rises then decays - datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf Table 1: <{_SGP40_RESPONSE_63_PCT_S}s to 63%, <{_SGP40_RESPONSE_90_PCT_S}s to 90% of a step change; the ported Sensirion algorithm against a genuine gas signal.",
    "[USB+WiFi][MANUAL]",
)
def test_sgp40_real_voc_index_response_to_real_stimulus() -> None:
    print_instruction(f"Fetch the DUT's current baseline: GET /measurements against {_DUT_IP_HINT}, note the SGP40 VOC field before any stimulus.")
    confirm("Press Enter once you've noted the baseline")
    print_instruction("Hold an isopropyl-alcohol swab (or similar VOC source) near the SGP40 sensor for 20 seconds.")
    confirm("Press Enter once you've held the stimulus near the sensor for at least 20 seconds")
    print_instruction("Remove the stimulus now, then poll GET /measurements every ~10 s for the next 2 minutes.")
    state_expected_outcome(f"VOC rises noticeably above baseline within ~{_SGP40_RESPONSE_63_PCT_S}-{_SGP40_RESPONSE_90_PCT_S}s of the stimulus, then decays back toward baseline over ~1-2 minutes after its removal (the algorithm re-adapts to clean air).")
    confirm_pass("Did VOC rise and then decay that way? [y/N]")


@register(
    "isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry",
    f"Compare the DUT's Lux against a reference light meter, and set up and record the NeoPixel rig geometry the flash tier's --allow-neopixel-sweep tests depend on. The bar is repeatability (+-{_ISL29125_REPEATABILITY_TOLERANCE_PCT:.0f}% across repeat readings of an unchanged scene) and range continuity; the reference reading is a recorded data point, never pass/fail.",
    "[USB+WiFi][MANUAL]",
)
def test_isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry() -> None:
    print_instruction(f"Under ordinary room light, fetch the DUT's reading three times ~10s apart: GET /measurements against {_DUT_IP_HINT}, note the ISL29125 Lux and RangeAct each time.")
    confirm("Press Enter once you've noted all three readings")
    state_expected_outcome(f"all three Lux values agree within +-{_ISL29125_REPEATABILITY_TOLERANCE_PCT:.0f}% of each other, and RangeAct is the same on all three (an unchanged scene must not make the auto-range chatter).")
    confirm_pass("Do all three agree that way, on one RangeAct? [y/N]")
    reference_lux = input("    Enter the reference light meter's reading in lx for that same scene (or 'none' if no meter is available): ").strip()
    print_instruction("Now darken the scene enough to force the low range (cover the sensor partially, or switch the room lights off) and fetch the reading again.")
    state_expected_outcome("RangeAct changes to 375 and Lux falls accordingly - and the reported Lux does NOT jump discontinuously across the switch: the gain-ratio calibration makes the two ranges agree in the overlap band.")
    confirm_pass("Did the range switch with the value staying continuous? [y/N]")
    pin = _neopixel_pin()
    print_instruction(f"Finally, set up the NeoPixel rig the automated sweep needs: the on-board WS2812 (GP{pin} on this bench board) aimed at the ISL29125's window, at a fixed distance, ambient light excluded (an enclosure or a darkened room).")
    distance_mm = input("    Enter the LED-to-sensor distance in mm as actually set up: ").strip()
    ambient = input("    Describe the ambient condition (enclosure, darkened room, ...): ").strip()
    record = {"date": datetime.datetime.now(datetime.UTC).date().isoformat(), "distance_mm": distance_mm, "ambient": ambient, "reference_lux": reference_lux, "neopixel_pin": pin}
    evidence.save_json("rig-geometry.json", record)
    print_instruction(f"Recorded {record} in the run's evidence. Record the distance and ambient condition in tests_hardware/README.md's rig section with today's date.")
    state_expected_outcome("with that rig in place, `scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep` runs the two automated light programs and they pass; without it, both skip.")
