"""Manual tests, Part 2 category E (tmp_hardware_test_candidates.md items 9-10): real sensor
accuracy against a genuine external reference - distinct from the automated tier's own plausibility-
only check (tests_hardware/flash/test_sensor_accuracy.py, sane bounds not exact reference)."""

from __future__ import annotations

from runner import confirm, print_instruction, register, state_expected_outcome

_DUT_IP_HINT = "the DUT's IP (see tests_hardware/README.md for how to find it)"

# BMP388/BMP384 typical accuracy, sourced directly from datasheets/bmp3xx/bst-bmp388-ds001.pdf
# (not assumed from memory): relative accuracy typ. +-8 Pa (900-1100 hPa, 25-40 degC), absolute
# accuracy typ. +-50 Pa (300-1100 hPa, -20 to +65 degC); temperature absolute accuracy +-0.3 degC
# @25 degC, +-0.5 degC over 0-65 degC.
_BMP388_PRESSURE_TOLERANCE_PA = 50.0
_BMP388_TEMP_TOLERANCE_C = 0.5


@register(
    "bmp3xx_real_pressure_temperature_vs_reference",
    f"Supply a reference reading (a calibrated barometer, or a known-altitude/known-pressure location) and compare against the DUT's own real BMP3xx reading, within the datasheet's own stated absolute accuracy (+-{_BMP388_PRESSURE_TOLERANCE_PA:.0f} Pa pressure, +-{_BMP388_TEMP_TOLERANCE_C:.1f} degC temperature - datasheets/bmp3xx/bst-bmp388-ds001.pdf). The digital twin's own README explicitly flags its calibration block as 'not sourced from a real chip', so this is the only way to validate the compensation formula against genuine factory trim.",
    "[USB][MANUAL]",
)
def test_bmp3xx_real_pressure_temperature_vs_reference() -> None:
    print_instruction(f"Fetch the DUT's current BMP3xx reading now: GET /measurements against {_DUT_IP_HINT}, note the Press/Temp fields.")
    confirm("Press Enter once you've noted the DUT's own reading")
    print_instruction("Now obtain a reference reading from a calibrated barometer, or compute the expected sea-level-adjusted pressure for a known-altitude location (e.g. a weather-station API for your area, adjusted for the DUT's actual altitude if not at sea level).")
    reference_pressure = input("    Enter the reference pressure in Pa (or hPa*100): ").strip()
    reference_temp = input("    Enter the reference temperature in degC: ").strip()
    print_instruction(f"Reference: {reference_pressure} Pa, {reference_temp} degC.")
    state_expected_outcome(f"the DUT's own Press value is within +-{_BMP388_PRESSURE_TOLERANCE_PA:.0f} Pa of the reference, and Temp within +-{_BMP388_TEMP_TOLERANCE_C:.1f} degC.")
    confirm("Compare the two now and press Enter once confirmed within tolerance (or Ctrl-C-abort the whole run if it's clearly outside tolerance and you want to stop here)")


# SGP40 response characteristics, sourced directly from datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf
# Table 1 (not assumed from memory): VOC Index range 1-500, response time <10s (63%) to <30s (90%)
# for a step change from 5 to 10 ppm ethanol, switch-on behavior <60s until reliably detecting VOC events.
_SGP40_RESPONSE_63_PCT_S = 10
_SGP40_RESPONSE_90_PCT_S = 30


@register(
    "sgp40_real_voc_index_response_to_real_stimulus",
    f"Apply a stated chemical stimulus (e.g. an isopropyl-alcohol swab held near the sensor) for a stated window, then remove it, and confirm the VOC index rises then decays as expected - real datasheet-sourced response timing (datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf Table 1: <{_SGP40_RESPONSE_63_PCT_S}s to 63%, <{_SGP40_RESPONSE_90_PCT_S}s to 90% of a step change), confirms the ported Sensirion algorithm behaves sensibly against a genuine gas-sensor signal, something no simulation can produce.",
    "[USB][MANUAL]",
)
def test_sgp40_real_voc_index_response_to_real_stimulus() -> None:
    print_instruction(f"Fetch the DUT's current baseline VOC index: GET /measurements against {_DUT_IP_HINT}, note the SGP40 VocIndex field before any stimulus.")
    confirm("Press Enter once you've noted the baseline")
    print_instruction("Hold an isopropyl-alcohol swab (or similar VOC source) near the SGP40 sensor for 20 seconds.")
    confirm("Press Enter once you've held the stimulus near the sensor for at least 20 seconds")
    print_instruction("Remove the stimulus now.")
    state_expected_outcome(f"VOC index rises noticeably above baseline within ~{_SGP40_RESPONSE_63_PCT_S}-{_SGP40_RESPONSE_90_PCT_S}s of applying the stimulus, then decays back toward baseline over the following ~1-2 minutes after removal (the sensor's own algorithm re-adapts to clean air).")
    confirm("Poll GET /measurements every ~10s for the next 2 minutes and press Enter once you've confirmed the rise-then-decay pattern")
