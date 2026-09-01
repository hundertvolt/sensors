"""Manual tests, Part 2 category A (tmp_hardware_test_candidates.md items 1-3): real bus/electrical
timing that needs a human's hands on the breadboard."""

from __future__ import annotations

from harness import Board
from runner import confirm, confirm_pass, countdown, print_instruction, register, state_expected_outcome


@register(
    "hot_unplug_replug_i2c_recovery",
    "Hot-unplug/replug an SCD30's I2C leads (SDA/SCL) and confirm the two-tier recovery (task respawn re-probe + reset/soft-reset) actually works, not just confirmed against the code (SPECIFICATION.md Part F.2).",
    "[USB][MANUAL]",
)
def test_hot_unplug_replug_i2c_recovery() -> None:
    board = Board()
    print_instruction("Locate the SCD30's SDA and SCL jumper wires on the breadboard.")
    print_instruction("Disconnect BOTH the SDA and SCL leads now. You have 20 seconds.")
    state_expected_outcome("the system keeps running (no crash/reboot); the SCD30 reader's own error count starts climbing in the log.")
    countdown(20, "Disconnect the SCD30 I2C leads now")
    confirm("Confirm both leads are fully disconnected, then press Enter")

    print_instruction("Now reconnect BOTH leads exactly as they were. You have 20 seconds.")
    countdown(20, "Reconnect the SCD30 I2C leads now")
    confirm("Confirm both leads are reconnected, then press Enter")

    print_instruction("Watching the live log for 30s for evidence of recovery (a fresh successful SCD30 read).")
    lines = board.tail_log(duration_s=30.0)
    joined = "\n".join(lines)
    assert "SCD30" in joined or "CO2" in joined, f"no SCD30-related recovery activity observed in the 30s window after reconnect:\n{joined}"


@register(
    "wedged_i2c_bus_watchdog_backstop",
    "Physically hold SDA (or SCL) low for a stated window, then confirm the real hardware WDT resets the board within the 8388ms cap once released (CLAUDE.md's 'hardware watchdog is the accepted backstop' policy - digital twin CI Run 10 only proves this in simulation).",
    "[USB][MANUAL]",
)
def test_wedged_i2c_bus_watchdog_backstop() -> None:
    board = Board()
    print_instruction("Attach a jumper wire from the SCD30's SDA pin directly to GND, wedging the I2C bus low.")
    state_expected_outcome("the board resets (WDT-triggered) within ~8.4s of the bus being held low long enough to starve the watchdog - you'll see the boot log lines reappear.")
    confirm("Confirm the jumper is connected (SDA held to GND), then press Enter to start watching")

    print_instruction("Watching for a reboot (up to 30s, generous relative to the 8388ms WDT cap).")
    lines = board.tail_log(duration_s=30.0)
    joined = "\n".join(lines)
    rebooted = "CFGMGR_" in joined or "FRAM SPI FRAM Driver Setup complete" in joined
    print_instruction("Now remove the SDA-to-GND jumper.")
    confirm("Confirm the jumper is removed, then press Enter")
    assert rebooted, f"no reboot observed within 30s of wedging the I2C bus - WDT backstop did not fire as expected:\n{joined}"


@register(
    "real_ws2812_neopixel_signal_timing",
    "Attach a scope/logic analyzer (or at minimum visually confirm color/animation correctness) - the twin only records writes with zero electrical timing modeled. WS2812 timing values are NOT sourced from a datasheet in this repo's datasheets/ folder (no WS2812/Neopixel datasheet present) - flagged per CLAUDE.md rather than assumed from memory; a human visual check is the only verification this test performs.",
    "[USB][MANUAL]",
)
def test_real_ws2812_neopixel_signal_timing() -> None:
    print_instruction("If you have a scope/logic analyzer, connect its probe to the Neopixel data line now.")
    print_instruction("The board will be triggered to show a red-green-blue-off sequence, ~1s per color, via the real /notification lightCmdLED endpoint.")
    state_expected_outcome("four distinct, clean colors in sequence (red, green, blue, off) with no visible flicker/glitching; on a scope, WS2812 bit timing within the datasheet's own tolerance (verify against the real WS2812B datasheet directly if you have access to one - this repo's datasheets/ folder does not include it).")
    confirm("Trigger the sequence now via a PUT /notification lightCmdLED call from another terminal, then press Enter once you've observed it")
    confirm_pass()
