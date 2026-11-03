# Carry-ins from finished units to later ones (lead, 2026-11-03)

Each line is checked against its unit's own action list at that unit's start; B8's own list is `B8/CARRY.md`.

- B3, B4, B5, B6, B7: the `setup()`s of their files still answer a bool (B2 converted the core's and the overrides in
  Wi-Fi and notification). Each unit converts its own, test first, except the two a product caller reads: dev's
  `UARTComm.setup()` (`asy_uart_link_driver.py:290`) and the FRAM driver's (`asy_fram_manager.py:671`).
- B8: once no `setup()` in the boot setup list answers anything, `SetupFct` in `asy_base_classes.py` goes back to
  `Awaitable[None]` (it reads `Awaitable[object]` since B2).
- B4: the reader timer trio (`_trigger_loop`, `_timer_fault`, `_timer_failed`, `_rearm_timer`; S2-G4-7's reader sites)
  and its `period is not None` narrowing are untouched; B2 removed only `_timer_reported`, so `_timer_fault()` persists
  every failure into one slot. `asy_bmp3xx_driver.py`'s `_CHIP_WRITE_FAILED` now routes only the POR re-apply.
- B4, B5, B7: B2 edited their files for its items 5, 8 and 9 (the four drivers' setup-failure paths, the Wi-Fi and
  notification `setup()` overrides, Wi-Fi's `quiet=` re-arm); start from the integration head that carries them.
- R2: `tests_hardware/flash/test_system_commands.py::test_a_reset_mid_erase_leaves_every_chunk_old_or_blank[1000]` and
  `[2000]` fail under `--twin`, the same at `93224dab`. B2's reading: the twin's 256 KB erase ends in about 1,064 ms, so
  neither cut lands inside it. Root-cause and fix in R2 (the twin's erase timing or the test's cut points).
- R2: `scripts/run_digital_twin_ci.sh --only` does not select scenarios (it ran all 67); it prints
  `ss: command not found` where `ss` is missing (the port-53 holder listing).
- R2: `tests/machine.py`'s reset-register model (`mem32` at the REASON and CHIP_RESET addresses) has no product reader
  left; the twin loop-end test and the bench reset test read it.
- R2 (bench): `tests_hardware/manual/manual_persistence.py`'s HAD_POR and RUN-bit checks lost their `ResetBits` read;
  each needs a device-side read of its own.
