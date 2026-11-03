# B3 falsification verified (lead, 2026-11-03, 18:1x UTC)

The falsifier made ten runs (b3f_*), all green: six test files at both GC stages, no memory marker; sizes and the
dev firmware reproduce claim 15 (196,591 B, -1,652 B, imageFreeBytes 56,684 B).

- Claim 4, REFUTED (narrow): true. `invalidate()` and the erase loop have no catch, so an erase on a dropped SPI bus
  raises `configure()`'s RuntimeError into the shutdown sequence's catch and ends in a watchdog reset reading 9.
  `SPI.deinit()` runs only inside `SPI.init()` (`asy_spi_driver.py:67`): no product path drops the bus. 25caf528 had
  no erase. No action; the claim's "as at 25caf528" covered the read, write and setup paths only.
- Claim 5, REFUTED: true, three texts. The flash tier's mid-erase reset points (1,000 and 2,000 ms) would land after
  an 8 MHz erase and fail the test's own inside-the-erase guard in round 1 (also F2); the twin's wire-time knob and the
  bus-hazard erase test still called 8 us/byte the real clock. Fixed in 0f5cbaf7: the resets at 50, 150 and 250 ms,
  all under the erase's ~266 ms wire time alone at 8 MHz, and both comments name the 8x-slow bus.
- Claim 12, REFUTED: true in letter, the wording was the lead's. The guarded points raise when an allocation at call
  entry fails, as R0_CHECKS item 5 recorded ("the raise is the argument tuple's allocation at call entry. Revert.");
  the probes show what the restart then leaves (storage paused for the boot; a second boot signature).
  Kept reverted: CLAUDE.md's standing rule (no blanket guard against a theoretical MemoryError, F.2) and the owner's
  2026-11-03 06:00 ruling ("Yes keep it simple": a log line that cannot get its tuple raises, the backstops take it).
- F1 (ad1fae73's catch): true, same premise. A failed coroutine allocation in the erase preflight leaves `_shutdown`
  set and the command gate refusing until a reboot. Kept reverted, as claim 12; recorded in CARRY_LATER beside it.
- F2: as claim 5, fixed.
- F3, Run 3's allowance read from console lines: true (the CRC16-derived run boots with its console off). Fixed in
  0f5cbaf7: one setup write per FRAM-backed logger, counted from `/status`'s errcount minus the in-memory sources the
  suite already names; the twin README says the same.
- Process: the falsifier's wait loop during the firmware build did no host work; it read the MB85RS64V PDF from the
  main checkout read-only (the worktree has no datasheets submodule). Both noted, no harm.

Fix commit **0f5cbaf7** (lead): tests and docs only, no `src/` change; the merged head's gate runs Run 3.
The merged gate (part a) found Run 3's bound test unstubbed for the new `/status` read: second fix **b5cd0252** (lead),
the stub plus two cases; see `../MERGE_B3B6_NOTES.md`.
