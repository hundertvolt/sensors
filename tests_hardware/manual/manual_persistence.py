"""Manual tests, Part 2 category C (tmp_hardware_test_candidates.md items 6, 7, 7b): genuine power
loss, distinct from the automated tier's own soft/hard-reset-only persistence tests
(tests_hardware/flash/test_reboot_persistence.py) - neither a soft reset nor mpremote's DTR-based
hard reset can reproduce the specific failure modes only a real, physical power interruption can:
torn writes mid-flight, and whatever the real MB85RS64V/SCD30 do (or don't) preserve across a
genuine supply-voltage loss rather than a controlled reset sequence."""

from __future__ import annotations

from runner import confirm, countdown, print_instruction, register, state_expected_outcome

_DUT_IP_HINT = "the DUT's IP (see tests_hardware/README.md for how to find it without disturbing the running system)"


@register(
    "real_fram_persistence_across_power_cycle",
    "Physically cut power to the board (not machine.reset()) after a stated write completes, wait a stated interval, then restore power - confirms the real MB85RS64V's dual-copy+CRC contents survive genuine power loss (datasheets/fram/MB85RS64V-DS501-00015-4v0-E.pdf: data retention >=10 years at +85 degC, so the wait interval here is about proving the write completed and survived the power interruption itself, not about retention time).",
    "[USB][MANUAL]",
)
def test_real_fram_persistence_across_power_cycle() -> None:
    marker = "424242"
    print_instruction(f"Trigger a real FRAM-backed write now, e.g. PUT /notification WarnCO2={marker} against {_DUT_IP_HINT}, and confirm it returns 200/Valid.")
    confirm("Press Enter once the write has completed and returned a real 200 response")
    print_instruction("Now physically disconnect the board's power supply (unplug USB or the bench power switch, whichever actually removes power - NOT a reset button). You have 20 seconds.")
    countdown(20, "Cut power to the board now")
    print_instruction("Wait 10 seconds with power OFF, to make sure this is a genuine loss, not a fast bounce.")
    countdown(10, "Keep power off")
    print_instruction("Now restore power to the board.")
    confirm("Press Enter once power is restored and the board is powering back up")
    print_instruction(f"Waiting up to 60s for the board to boot and become reachable again, then re-checking WarnCO2 via GET /notification against {_DUT_IP_HINT}.")
    state_expected_outcome(f"GET /notification reports WarnCO2={marker}, the same value written before the power cycle.")
    confirm("Press Enter once you've confirmed the value survived")


@register(
    "real_scd30_nvm_persistence_across_power_cycle",
    "Same idea as the FRAM test, for the sensor's own onboard NVM (measurement interval, ambient pressure, altitude, temp offset, self-cal) rather than the board's own FRAM.",
    "[USB][MANUAL]",
)
def test_real_scd30_nvm_persistence_across_power_cycle() -> None:
    marker = 7
    print_instruction(f"Trigger a real SCD30 NVM write now, e.g. PUT /sensors {{\"SCD30\": {{\"MeasInt\": {marker}}}}} against {_DUT_IP_HINT}, and confirm it returns 200/Valid.")
    confirm("Press Enter once the write has completed and returned a real 200 response")
    print_instruction("Now physically disconnect the board's power supply entirely (removes power to the SCD30 too, not just the RP2040). You have 20 seconds.")
    countdown(20, "Cut power to the board (and SCD30) now")
    countdown(10, "Keep power off")
    print_instruction("Now restore power.")
    confirm("Press Enter once power is restored")
    state_expected_outcome(f"GET /sensors reports SCD30 MeasInt={marker}, the same value written before the power cycle - confirms it round-tripped through the sensor's own onboard NVM, not just the RP2040's own config file.")
    confirm("Press Enter once you've confirmed the value survived")


@register(
    "genuine_power_loss_mid_write",
    "Cut power at a stated moment DURING an active config.json/FRAM write (not after it completes) - real torn-write behavior on real flash, ground the automated tier's soft-reset test and the digital twin's simulation can't reach at all, since neither can interrupt a write mid-flight the way a genuine power loss can.",
    "[USB][MANUAL]",
)
def test_genuine_power_loss_mid_write() -> None:
    print_instruction(f"Prepare to trigger a real write against {_DUT_IP_HINT} (e.g. PUT /notification WarnCO2=1234) - have your finger on the power switch/USB cable BEFORE you send it.")
    confirm("Press Enter once you're ready to send the write and cut power immediately after")
    print_instruction("Send the write now, and cut power to the board as close to immediately afterward as you physically can (a second or two of slop is fine and expected - this is inherently imprecise by hand).")
    confirm("Press Enter once you've sent the write and cut power")
    countdown(10, "Keep power off")
    print_instruction("Restore power.")
    confirm("Press Enter once power is restored")
    state_expected_outcome(
        "one of two acceptable outcomes, not exactly one specific value: either the write completed "
        "before power was actually lost (WarnCO2=1234, timing was too slow to catch it mid-write) or "
        "the write was genuinely interrupted and the board recovers cleanly with its PREVIOUS valid "
        "value intact (no corruption, no crash, no unreadable config) - what's NOT acceptable is a "
        "crash on boot, a config file that fails to parse, or a value that's neither the old nor the "
        "new one (a genuinely torn/corrupted write)."
    )
    confirm("Press Enter once you've checked GET /notification and confirmed one of the two acceptable outcomes above (not the unacceptable one)")
