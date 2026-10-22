"""The SCD30 forced-recalibration readiness defaults measured on the bench, in the room condition the round plan states
(stable, unoccupied): CO2 polled once per measurement interval for a soak duration, its spread and change rate over
sliding windows recorded as evidence for the readiness parameters; nothing written, only the cadence asserted."""

import time
from typing import TYPE_CHECKING

import _load
import evidence
import http_client
import pytest
from soak_durations import SOAK_DURATION_SECONDS

if TYPE_CHECKING:
    from http_client import JSONObject

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("scd30",)

# The sensor's 63 % response time is 20 s (SCD30 datasheet v1.0, section 1, CO2 sensor specifications); windows of its
# multiples up to 10 min.
# @tunable l4.scd30_frc_baseline_window_step_s = 20.0
_WINDOW_STEP_S = 20.0
# @tunable l4.scd30_frc_baseline_window_max_s = 600.0
_WINDOW_MAX_S = 600.0
# @tunable l4.scd30_frc_baseline_probe_timeout_s = 5.0
_PROBE_TIMEOUT_S = 5.0
_PERCENTILES = (50, 90, 100)


@pytest.mark.soak_duration
def test_scd30_frc_readiness_baseline(dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    duration = request.config.getoption("--soak-duration")
    if duration is None:
        pytest.skip("a passive observation over one named duration: runs with --soak-duration (the long one for the baseline)")
    interval = _load.as_object(_load.get_object(dut_ip, "/sensors", _PROBE_TIMEOUT_S).get("SCD30"), "GET /sensors SCD30").get("MeasInterval")
    assert isinstance(interval, int) and interval > 0, f"GET /sensors carries no SCD30 MeasInterval: {interval!r}"
    samples: list[tuple[float, float]] = []
    missed: list[str] = []
    last_ts: object = None
    end = time.monotonic() + SOAK_DURATION_SECONDS[duration]
    while time.monotonic() < end:
        time.sleep(interval)
        try:
            data = _scd30(dut_ip)
        except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError) as exc:
            missed.append(f"{time.monotonic() - end:.0f}s: {exc!r}")
            continue
        co2, ts = data.get("CO2"), data.get("TS")
        if not isinstance(co2, (int, float)) or ts == last_ts:
            missed.append(f"{time.monotonic() - end:.0f}s: CO2 {co2!r}, TS {ts!r} (last {last_ts!r})")
            continue
        last_ts = ts
        samples.append((time.monotonic(), float(co2)))
    windows: dict[str, dict[str, dict[str, float]]] = {}
    width = _WINDOW_STEP_S
    while width <= _WINDOW_MAX_S:
        spreads, rates = [], []
        for i, (start, _co2) in enumerate(samples):
            inside = [v for t, v in samples[i:] if t - start <= width]
            if samples[-1][0] - start >= width and len(inside) > 1:
                spreads.append(max(inside) - min(inside))
                rates.append(abs(inside[-1] - inside[0]) / width * 60)  # ppm per minute
        windows[f"{width:g}s"] = {"spread_ppm": _distribution(spreads), "rate_ppm_per_min": _distribution(rates)}
        width += _WINDOW_STEP_S
    path = evidence.save_json("scd30-frc-readiness-baseline.json", {"interval_s": interval, "samples": len(samples), "missed": missed, "windows": windows})
    result_note(f"{len(samples)} SCD30 samples at {interval}s over {SOAK_DURATION_SECONDS[duration]:g}s, {len(missed)} missed; distributions in {path.name}: 20s {windows.get('20s')}, 600s {windows.get('600s')}")
    assert not missed, f"a measurement did not arrive every {interval}s interval ({len(missed)} missed): {missed[:5]}"


def _distribution(values: "list[float]") -> "dict[str, float]":
    ordered = sorted(values)
    return {f"p{p}": ordered[min(len(ordered) - 1, len(ordered) * p // 100)] for p in _PERCENTILES} if ordered else {}


def _scd30(dut_ip: str) -> "JSONObject":
    return _load.as_object(_load.get_object(dut_ip, "/measurements", _PROBE_TIMEOUT_S).get("SCD30"), "GET /measurements SCD30")
