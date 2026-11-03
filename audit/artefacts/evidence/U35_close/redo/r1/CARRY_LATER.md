# Carry-ins from finished units to later ones (lead, 2026-11-03)

Each line is checked against its unit's own action list at that unit's start; B8's own list is `B8/CARRY.md`.

- B3, B4, B5, B6, B7: the `setup()`s of their files still answer a bool (B2 converted the core's and the overrides in
  Wi-Fi and notification). Each unit converts its own, test first, except the two a product caller reads: dev's
  `UARTComm.setup()` (`asy_uart_link_driver.py:290`); `FRAMManager.setup()`'s reader (`asy_fram_manager.py:671`)
  goes with B3's row 2, so its bool goes too (lead, 2026-11-03).
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
- B3: clarification (e) is decided (owner, 2026-11-03: "Option A."): FRAM's E49 and W63 for one invalid block stay;
  no row for it. B3 asks nothing at its start.
- B6: clarification (c) is decided (owner, 2026-11-03: "Option A, keep as is."): no change for a UART exchange during
  a flash write; B6 asks nothing at its start for it.
  The timeout stays 1,000 ms (owner, 2026-11-03: "Keep the UART as is. Any module using the UART must be aware
  that errors like this can happen ... and provide recovery mechanisms themselves."): nothing to change.
- Next snapshot: the Stull paper left the tree (int 1daa0fae); hundertvolt/datasheets#1 merged at 10:58 UTC as
  786c947c, and the `datasheets` pointer moved to it (int a6047339).
- B3: FRAM E19 (`LOCK_TIMEOUT`) twice in B4's first scenario run (schlafzi, arzi, overflow bursts beside the
  then-unwaited boot W65 write), not in the reruns: check the lock timeout covers a boot W65 beside a burst.
- R2: twin chip knobs with no driver reader after B4 (`_bmp3xx_chip.py` `fatal_err` and the EVENT model,
  `_scd30_chip.py` `rdy_stuck_high`); bench tests that expect an empty SGP40 log after boot meet the restored W65.
- R2: `tests_hardware/flash/test_bus_concurrency.py::test_a_held_sda_line_is_cleared_and_every_device_answers` fails
  under `--twin` at `963d0de1` and after B4's fix round alike: the twin has no chip that holds SDA against a bit-banged
  read (B4 fix round, (c)).
- Round 1: after B6, the UART hazard script's stalled TX fails on the missing ACK (E81), not the write deadline (E82);
  the crossover's new `cobs` mode runs on silicon for the first time.
- B3: R0 item 5's reverts of `a4f0ccea` and `8cf55c6b`, B2's and missed by its list, are B3's row 19; `ad1fae73`'s
  is its row 4.
- Every later unit: gates and timing-sensitive runs go one at a time on this 4-core host. B3's and B6's gates side by
  side failed six wall-clock bounds at 32768 and stopped npm `test:unit`; all held alone (`B6/HANDBACK.md`, Gate).
- R2 (MicroPython re-check): `machine.UART.deinit()` waits out the TX FIFO (`machine_uart.c:484`, v1.29.0): at most
  32 bytes, 2.8 ms at 115200, about 1 s at the hazard script's 300 baud. `asy_uart_driver.py`'s `deinit()` calls it;
  pre-audit form, no product path deinits or re-inits a UART at runtime (B6 falsifier, claim 3).
- Known limits, kept by rule (B3 falsifier, claim 12 and F1): after a failed allocation at call entry, the auto-unpause
  leaves storage paused for the boot, the boot signature can be drawn twice, and the erase preflight leaves the command
  gate refusing until a reboot. CLAUDE.md's MemoryError rule and the owner's 06:00 ruling keep these unguarded.
