"""Digital-twin integration for the ISL29125's auto-range machinery: the real src/ driver against digital_twin/_isl29125_chip.py's stateful chip model, over the real bus fakes.
This is the CI-every-commit version of the NeoPixel rig - continuity, hysteresis, colour invariance, requirement 17's dead-interrupt path and gain-ratio convergence, none of which any mock-tier test can prove because none of them has a chip whose gain actually changes."""

import asyncio
import os
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    from _isl29125_chip import Isl29125Chip

    from asy_isl29125_driver import ISL29125
    from print_log import ErrorLog

    T = TypeVar("T")

# digital_twin/ must precede tests/ so `machine` resolves to the twin's own stateful fake rather
# than tests/machine.py's register dictionary - see test_digital_twin_machine.py's own comment.
sys.path.insert(0, "digital_twin")

import machine
from machine import Pin

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_Reader

_RANGE_LOW_LUX = 375
_RANGE_HIGH_LUX = 10000
_GAIN_RATIO_NOMINAL = 26.666666666666668
_CHIP_GAIN_RATIO = 25.9  # _isl29125_chip.py's own per-instance default - the value to be learned

# The fake's effective full scales, and therefore the real switch points the driver lands on:
# up at 85% of the low range's 375 lx, down at 1.5% of the high range's own 375 x 25.9.
_SWITCH_UP_LUX = 0.85 * 375.0
_SWITCH_DOWN_LUX = 0.015 * 375.0 * _CHIP_GAIN_RATIO

_TMP_DIR = "tests/_tmp"


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


def _tmp_cfg_path(name: str) -> str:
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    path = _TMP_DIR + "/isltwin_" + name + "_"
    try:
        os.remove(path + "config_ISL29125.cfg")
    except OSError:
        pass
    return path


def make_dev_reader(name: str, *, resolution: int = 16, dwell_s: float = 0.0, settle_cycles: int = 2) -> "tuple[Isl29125Chip, ISL29125_Reader]":
    # The dev profile is the only one that wires this sensor at all (requirement 18).
    machine.configure_i2c_wiring("dev")
    Pin.reset_registry()
    i2c = asy_i2c_driver.I2C(1, 15, 14, frequency=50000)
    assert i2c._i2c is not None
    chip = i2c._i2c.devices[0x44]
    # The fake keeps CONVERTING on its own timer - that is load-bearing here, not incidental: a
    # CONFIG1 write restarts the conversion and leaves the previous cycle's values readable
    # (exactly as real double-buffered hardware does), so only a real conversion during the
    # settle window produces a sample on the new gain. What is switched off instead is the
    # random WALK: with lux_step = 0 the illumination moves only when a test says so.
    chip._lux_step = 0.0
    reader = ISL29125_Reader(i2c, 6, cfg_path=_tmp_cfg_path(name))
    # AutoRangeDwell defaults to 10 s, which is right on a real bench and would make every test
    # below a ten-second wait. The dwell itself is covered at tier 1
    # (test_switch_down_is_suppressed_inside_the_dwell_window).
    reader._ar_dwell_s = dwell_s

    async def boot() -> None:
        await reader.cfgmgr.setup()
        assert await reader._init_isl() is True
        reader._ar_dwell_s = dwell_s  # _init_isl() reloads it from the config file
        # AutoRangeSettle = 2 rather than the shipped default of 1, and the reason is a property
        # of SIMULATED time rather than of the driver. On real silicon the ADC restarts during
        # the I2C write itself (Table 7 p10) while the driver arms its deadline once that write
        # has returned - hundreds of microseconds later at 50 kHz - so one cycle of settle is
        # genuinely enough. In the twin the write costs nothing, so the chip's next conversion
        # and the driver's deadline land on the same millisecond and which wins is a coin flip.
        # One extra cycle removes the tie without weakening anything: the settle-margin
        # arithmetic itself is proven exactly at tier 1, for both 1 and 5 cycles.
        assert await reader.set_autorange_settle(settle_cycles) is True
        if resolution != 16:
            assert await reader.set_resolution(resolution) is True

    run(boot())
    return chip, reader


async def cycle(chip: "Isl29125Chip", reader: ISL29125_Reader, lux: float, tint: "tuple[float, float, float] | None" = None) -> "ISL29125":
    # One complete real cycle: the chip converts at its current gain, the driver reads, decides
    # the range, and stores - exactly the sequence read_loop() runs, minus the trigger wait.
    chip.set_illumination(lux, tint=tint)
    results = await reader._read_isl()
    await reader._store_isl(results)
    return await reader.get_data()


def warnings(counters: "ErrorLog") -> "list[int]":
    entry = counters["ISL29125"]
    # No strict= (ruff B905): MicroPython's zip() rejects it; ErrEntry keeps both lists in step.
    return [number for number, kind in zip(entry["ErrNum"], entry["ErrType"]) if kind == "W"]  # noqa: B905


# ---------------------------------------------------------------------------
# Continuity across the switch - the single most important property here
# ---------------------------------------------------------------------------


def test_reported_lux_is_continuous_and_monotonic_through_a_range_sweep() -> None:
    chip, reader = make_dev_reader("continuity")
    # No star-unpacking in a list display: MicroPython rejects it outright (ruff RUF005's own
    # project-wide exemption records the same limitation).
    up = [40.0, 90.0, 150.0, 220.0, 290.0, 340.0, 500.0, 900.0, 1800.0, 3000.0]
    sweep = up + list(reversed(up))

    async def scenario() -> "list[tuple[float, float, int]]":
        seen = []
        for lux in sweep:
            data = await cycle(chip, reader, lux)
            assert data.Lux is not None and data.RangeAct is not None
            seen.append((lux, data.Lux, data.RangeAct))
        return seen

    seen = run(scenario())
    # Both ranges really were used - otherwise this proves nothing about the transition.
    assert {entry[2] for entry in seen} == {_RANGE_LOW_LUX, _RANGE_HIGH_LUX}
    for true_lux, reported, _range_act in seen:
        # 4% covers the whole uncalibrated error budget: the nominal 26.67 range ratio against
        # this unit's real 25.9 is a 2.96% high-range overstatement, and that residual IS what
        # the gain-ratio calibration below removes. Without the span normalisation and the
        # per-sample range in the results tuple, the step here would be ~2567%.
        assert abs(reported - true_lux) / true_lux < 0.04, (true_lux, reported)


def test_normalised_rgb_and_brightness_are_continuous_across_the_switch_not_only_lux() -> None:
    # The regression test for the "normalise over the active range" defect specifically: under
    # that reading Lux stays continuous and every other field steps by ~26.67x at each switch.
    chip, reader = make_dev_reader("span_continuity")

    async def scenario() -> "list[tuple[int, float]]":
        seen = []
        # Starts on the high range, drops to the low one below ~146 lx, and comes back up at
        # 85% of 375 lx - so this sweep really does cross the transition in the up direction.
        for lux in (80.0, 120.0, 200.0, 280.0, 330.0, 400.0, 500.0):
            data = await cycle(chip, reader, lux)
            assert data.Green is not None and data.RangeAct is not None
            seen.append((data.RangeAct, data.Green))
        return seen

    seen = run(scenario())
    assert {entry[0] for entry in seen} == {_RANGE_LOW_LUX, _RANGE_HIGH_LUX}
    for index in range(1, len(seen)):
        previous, current = seen[index - 1][1], seen[index][1]
        assert current > previous  # brighter scene, larger normalised value, across the switch
        assert current / previous < 2.0  # a gain-ratio step would be ~26.67x, not ~1.7x


def test_the_range_does_not_oscillate_when_parked_at_the_switch_point() -> None:
    # Hysteresis, as a real state machine rather than as arithmetic: the up point is 85% of the
    # low range and the down point 1.5% of the high one, which after a switch up leaves the same
    # light at ~2.1x the down threshold.
    chip, reader = make_dev_reader("hysteresis")  # dwell 0, so only real hysteresis is under test

    async def scenario() -> "list[int]":
        ranges = []
        for _ in range(12):
            data = await cycle(chip, reader, _SWITCH_UP_LUX + 1.0)
            assert data.RangeAct is not None
            ranges.append(reader._active_range)
        return ranges

    ranges = run(scenario())
    # It switches up once and then stays there, rather than flapping every cycle.
    assert ranges[0] == _RANGE_HIGH_LUX
    assert set(ranges[1:]) == {_RANGE_HIGH_LUX}


def test_hue_saturation_and_colour_temperature_hold_still_across_the_switch() -> None:
    # All three channels share one RNG bit, so any common gain factor cancels out of the R:G:B
    # ratios - H, S and CCT need none of the normalisation chain and must not move.
    chip, reader = make_dev_reader("invariance")
    tint = (1.0, 0.75, 0.45)

    async def scenario() -> "list[tuple[int, float, float, float]]":
        seen = []
        for lux in (60.0, 100.0, 200.0, 330.0, 600.0, 900.0):
            data = await cycle(chip, reader, lux, tint=tint)
            assert data.Hue is not None and data.Sat is not None and data.CCT is not None
            seen.append((reader._active_range, data.Hue, data.Sat, data.CCT))
        return seen

    seen = run(scenario())
    assert {entry[0] for entry in seen} == {_RANGE_LOW_LUX, _RANGE_HIGH_LUX}
    hues = [entry[1] for entry in seen]
    sats = [entry[2] for entry in seen]
    ccts = [entry[3] for entry in seen]
    assert max(hues) - min(hues) < 1.0  # degrees, across a 4.5x brightness change AND a switch
    assert max(sats) - min(sats) < 0.02
    assert (max(ccts) - min(ccts)) / min(ccts) < 0.02


# ---------------------------------------------------------------------------
# The scene the peak-of-three rule exists for
# ---------------------------------------------------------------------------


def test_a_single_clipped_channel_switches_the_range_up_and_does_not_fall_back() -> None:
    # Red clips while green sits well below the switch-up point. Deciding on green alone would
    # leave this scene un-ranged, and deciding "up" on the peak but "down" on green would then
    # oscillate as soon as the dwell expired. This is the case the NeoPixel rig drives for real.
    chip, reader = make_dev_reader("clipped_channel")  # dwell 0: only the peak rule can hold it up

    async def scenario() -> "list[int]":
        ranges = []
        for _ in range(6):
            await cycle(chip, reader, 200.0, tint=(3.0, 0.4, 0.3))
            ranges.append(reader._active_range)
        return ranges

    ranges = run(scenario())
    assert ranges[0] == _RANGE_HIGH_LUX  # the clipped red alone forced the switch up
    assert set(ranges) == {_RANGE_HIGH_LUX}  # and green being low never drags it back down


def test_the_clipped_scene_reports_the_tints_own_hue_once_it_is_on_the_right_range() -> None:
    chip, reader = make_dev_reader("clipped_hue")

    async def scenario() -> "tuple[float | None, float | None]":
        await cycle(chip, reader, 30.0)  # a dim scene first, so the driver really is on the low range
        assert reader._active_range == _RANGE_LOW_LUX
        clipped = await cycle(chip, reader, 200.0, tint=(3.0, 0.4, 0.3))  # red clips at this gain
        assert reader._active_range == _RANGE_HIGH_LUX  # the clipped channel forced the switch
        settled = await cycle(chip, reader, 200.0, tint=(3.0, 0.4, 0.3))  # read on the new gain
        return clipped.Hue, settled.Hue

    clipped_hue, settled_hue = run(scenario())
    assert clipped_hue is not None and settled_hue is not None
    # A clipped red flattens the ratios towards white, so the reported hue is wrong while the
    # range is wrong - and right again once the switch has taken effect.
    assert settled_hue != clipped_hue
    assert 0.0 <= settled_hue < 60.0  # red-dominant, as the tint says


# ---------------------------------------------------------------------------
# Requirement 17 - the interrupt is the fast path, never the only one
# ---------------------------------------------------------------------------


def test_a_real_threshold_crossing_drives_the_interrupt_line_into_the_read_event() -> None:
    # The whole mechanism end to end: the chip fake pulls its INT low, machine.py's per-id Pin
    # registry means that is the same object the driver registered a handler on, and the handler
    # sets the read event. Nothing between here and real hardware is stubbed.
    chip, reader = make_dev_reader("int_path")
    reader.start_timer()  # this is what wires the falling-edge handler
    reader.read_event.clear()
    assert reader._active_range == _RANGE_HIGH_LUX  # so the armed threshold is the DOWN crossing

    async def scenario() -> "tuple[bool, int]":
        # Four conversions with no driver read in between: AutoRangePersist defaults to 4, so the
        # chip deliberately holds the interrupt off until a light change has persisted that long.
        # That hardware transient rejection is the point of the field.
        for index in range(4):
            chip.set_illumination(5.0)  # far below the down threshold: the window is crossed
            if index < 3:
                assert reader.read_event.state == 0, "the persistence counter released too early"
        fired = bool(reader.read_event.state)
        # The destructive status read is what clears the flag and releases the line again.
        # Pin(6) is the same registry singleton object the chip fake drives and the driver
        # listens on, which is exactly what makes the whole mechanism work.
        await reader._read_isl()
        return fired, Pin(6).value() or 0

    fired, line_after_read = run(scenario())
    assert fired is True
    assert line_after_read == 1  # back to the pull-up's idle level


def test_the_range_still_tracks_when_the_interrupt_line_never_asserts() -> None:
    # Requirement 17's actual failure mode: a missing pull-up, a broken jumper, a mis-set INTSEL.
    # Without the periodic evaluation auto-range would freeze on whatever range it started on,
    # silently, and the only symptom would be readings that look like a sensor fault.
    chip, reader = make_dev_reader("int_stuck")
    chip.configure_fault("isl29125:int_stuck_high")
    reader.start_timer()

    async def scenario() -> "tuple[list[int], bool]":
        ranges = []
        for lux in (40.0, 900.0, 40.0, 900.0):
            await cycle(chip, reader, lux)
            ranges.append(reader._active_range)
        return ranges, bool(reader.read_event.state)

    ranges, interrupt_fired = run(scenario())
    assert interrupt_fired is False  # the line really never moved
    assert ranges == [_RANGE_LOW_LUX, _RANGE_HIGH_LUX, _RANGE_LOW_LUX, _RANGE_HIGH_LUX]


def test_a_dead_interrupt_line_eventually_warns_rather_than_staying_invisible() -> None:
    chip, reader = make_dev_reader("int_stuck_warn")
    chip.configure_fault("isl29125:int_stuck_high")
    reader.start_timer()

    async def scenario() -> "ErrorLog":
        for index in range(6):
            await cycle(chip, reader, 40.0 if index % 2 == 0 else 900.0)
        return await reader.get_error_counter()

    assert 15 in warnings(run(scenario()))


# ---------------------------------------------------------------------------
# Gain-ratio self-calibration - the residual step the nominal 26.67 leaves
# ---------------------------------------------------------------------------


def test_the_learned_gain_ratio_converges_towards_the_chips_own_real_ratio() -> None:
    # 12-bit for speed: a settle window is ~19 ms rather than ~303 ms, and each learn costs two
    # of them. The ratio itself is resolution-independent (it is a ratio of counts on one scale).
    chip, reader = make_dev_reader("gain_converge", resolution=12)

    async def scenario() -> "list[float]":
        seen = [reader._gain_ratio]
        for _ in range(30):
            # Park in the overlap band and let the learn period elapse, so the driver's OWN read
            # path takes the paired reading - this is the real mechanism, not a direct call to it.
            elapse_learn_period(reader)
            await cycle(chip, reader, 300.0)
            seen.append(reader._gain_ratio)
        return seen

    seen = run(scenario())
    assert seen[0] == _GAIN_RATIO_NOMINAL
    assert seen[-1] < seen[0]  # moved towards the chip's own smaller ratio, not away from it
    assert abs(seen[-1] - _CHIP_GAIN_RATIO) < 0.5
    assert abs(seen[-1] - _CHIP_GAIN_RATIO) < abs(seen[0] - _CHIP_GAIN_RATIO)


def test_reset_cal_returns_the_ratio_to_nominal_and_it_relearns() -> None:
    chip, reader = make_dev_reader("gain_reset", resolution=12)

    async def scenario() -> "tuple[float, float, float]":
        for _ in range(10):
            elapse_learn_period(reader)
            await cycle(chip, reader, 300.0)
        learned = reader._gain_ratio
        await reader.reset_gain_calibration(flag=True)
        after_reset = reader._gain_ratio
        for _ in range(10):
            elapse_learn_period(reader)
            await cycle(chip, reader, 300.0)
        return learned, after_reset, reader._gain_ratio

    learned, after_reset, relearned = run(scenario())
    assert learned < _GAIN_RATIO_NOMINAL
    assert after_reset == _GAIN_RATIO_NOMINAL
    assert relearned < _GAIN_RATIO_NOMINAL


def test_calibration_measurably_shrinks_the_high_range_error() -> None:
    # The point of the whole mechanism, stated as the number a user would notice: the nominal
    # ratio overstates this unit's high range by ~3%, and the learned one does not.
    chip, reader = make_dev_reader("gain_effect", resolution=12)

    async def scenario() -> "tuple[float, float]":
        await cycle(chip, reader, 900.0)  # settle onto the high range
        before = await cycle(chip, reader, 900.0)
        for _ in range(40):
            elapse_learn_period(reader)
            await cycle(chip, reader, 300.0)
        await cycle(chip, reader, 900.0)
        after = await cycle(chip, reader, 900.0)
        assert before.Lux is not None and after.Lux is not None
        return before.Lux, after.Lux

    before_lux, after_lux = run(scenario())
    assert abs(before_lux - 900.0) / 900.0 > 0.02  # the uncalibrated ~3% overstatement
    assert abs(after_lux - 900.0) / 900.0 < 0.01  # calibrated away


def elapse_learn_period(reader: ISL29125_Reader) -> None:
    # Backdates the reader's own learn clock far enough that its hourly period has elapsed - the
    # one thing these tests cannot simply wait out in real time. Sets the attribute rather than
    # returning a value so the port's opaque ticks type never has to be spelled here.
    import time

    reader._gain_learn_ms = time.ticks_add(time.ticks_ms(), -4_000_000)


# ---------------------------------------------------------------------------
# Brownout, against a chip that really does come up in the post-brownout state
# ---------------------------------------------------------------------------


def test_a_freshly_constructed_chip_is_recovered_from_its_own_power_on_brownout_flag() -> None:
    # BOUTF is HIGH at power-up by design (p12, Table 18), so setup() has to clear it - otherwise
    # every single cycle would be treated as a brownout and no sample would ever be reported.
    chip, reader = make_dev_reader("brownout_poweron")

    async def scenario() -> "tuple[ISL29125, ErrorLog]":
        data = await cycle(chip, reader, 200.0)
        return data, await reader.get_error_counter()

    data, counters = run(scenario())
    assert data.Lux is not None
    assert 10 not in warnings(counters)


def test_a_real_brownout_is_detected_reconfigured_and_recovered_from() -> None:
    chip, reader = make_dev_reader("brownout_real")

    async def scenario() -> "tuple[ISL29125, ISL29125, ErrorLog]":
        good = await cycle(chip, reader, 200.0)
        chip.simulate_brownout()  # a supply dip: power-on defaults AND BOUTF high, unlike 0x46
        recovering = await cycle(chip, reader, 200.0)
        recovered = await cycle(chip, reader, 200.0)
        assert recovering.Lux == good.Lux  # the brownout cycle stored nothing new
        return good, recovered, await reader.get_error_counter()

    good, recovered, counters = run(scenario())
    assert 10 in warnings(counters)
    assert recovered.Lux is not None
    assert abs(recovered.Lux - 200.0) / 200.0 < 0.04  # reading correctly again afterwards
    assert good.Lux is not None


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
