"""Manual tests: real sensor accuracy against a genuine external reference - distinct from
tests_hardware/flash/test_sensor_accuracy.py's automated, plausibility-only (sane bounds, not
exact reference) check."""

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


# ISL29125: datasheets/isl29125/FN8424.pdf gives no lux-accuracy figure at all - only full-scale
# ranges (375/10000 lx), a dark-current DDark of typ. 1 / max 5 counts at range 0, and an IR
# spectral response. So this records a documented setup and a repeatability figure against a
# reference meter; it deliberately makes no absolute-accuracy claim, and none is checkable here.
_ISL29125_REPEATABILITY_TOLERANCE_PCT = 10.0


@register(
    "isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry",
    f"Compare the DUT's own reported Lux against a reference light meter under two stated lighting conditions, and record the NeoPixel rig's physical geometry that the flash-tier --allow-neopixel-sweep test depends on. The datasheet states no lux accuracy, so the bar here is repeatability (+-{_ISL29125_REPEATABILITY_TOLERANCE_PCT:.0f}% across repeat readings of an unchanged scene) plus a written-down setup, not an accuracy claim - and absolute lux/CCT against a WS2812's three narrow emission lines is meaningless by construction, which is exactly why the automated sweep only ever asserts relative properties.",
    "[USB][MANUAL]",
)
def test_isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry() -> None:
    print_instruction(f"Under ordinary room light, fetch the DUT's reading three times ~10s apart: GET /measurements against {_DUT_IP_HINT}, note the ISL29125 Lux and RangeAct each time.")
    confirm("Press Enter once you've noted all three readings")
    state_expected_outcome(f"all three Lux values agree within +-{_ISL29125_REPEATABILITY_TOLERANCE_PCT:.0f}% of each other, and RangeAct is the same on all three (an unchanged scene must not make the auto-range chatter).")
    confirm("Confirm both now and press Enter")
    reference_lux = input("    Enter the reference light meter's reading in lx for that same scene (or 'none' if no meter is available): ").strip()
    print_instruction(f"Reference: {reference_lux} lx. Record this in the run log - it is a data point for the record, not a pass/fail bar.")

    print_instruction("Now darken the scene enough to force the low range (cover the sensor partially, or switch the room lights off) and fetch the reading again.")
    state_expected_outcome("RangeAct changes to 375 and Lux falls accordingly - and, critically, the reported Lux does NOT jump discontinuously across the switch: the gain-ratio calibration exists to make the two ranges agree in the overlap band.")
    confirm("Confirm the range switched and the value stayed continuous, then press Enter")

    print_instruction("Finally, set up and write down the NeoPixel rig geometry the automated sweep needs: the on-board WS2812 (GP18 on the dev bench) aimed at the ISL29125's window, at a fixed, recorded distance, with ambient light excluded (an enclosure or a darkened room).")
    distance_mm = input("    Enter the LED-to-sensor distance in mm as actually set up: ").strip()
    print_instruction(f"Recorded geometry: {distance_mm} mm, ambient excluded. Note this in tests_hardware/README.md's rig section if it differs from what is written there.")
    state_expected_outcome("with that rig in place, `scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep` runs the automated sweep and it passes; without it, that test is expected to skip.")
    confirm("Press Enter once the geometry is set up and recorded (running the sweep itself is the automated tier's job, not this one)")
