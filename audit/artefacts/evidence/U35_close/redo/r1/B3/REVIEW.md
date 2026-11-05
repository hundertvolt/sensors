# B3 lead review (2026-11-03, 16:2x UTC): `src/` at cc5daeb7 against 90691b6d

Read in full: every `src/` hunk (`git diff 90691b6d cc5daeb7 -- src/`; the hunk list is `review_hunks_lead.out`),
and the whole of cc5daeb7 (suite, comments, SPECIFICATION and the twin test's comment).

- `asy_crc_checks.py`: the constructor and `length()`'s comment are 25caf528's form again (renamed attributes only);
  `add_into()`/`check_from()` keep 90691b6d's pass-mode bounds (A-K2 kept, lead 2026-11-03), so the diff against
  90691b6d is the width-field revert alone.
- `asy_fram_driver.py`: no lost-chip chain (`_check_write_anomaly`, `_report_chip_lost`, `lost`, `is_ready`, the
  `_PROBE_AT` tunable), no bus-down guard or E52, no partial-WP E53; `setup()` reads WP as all-bits and takes the bus
  lock only; `verify_present()` matches 25caf528 apart from the dead ValueError branch removed before this unit;
  `SPIDevice(..., baudrate=8_000_000)` matches the owner's 2026-11-02 15:51 ruling (24 MHz / 3).
- `asy_fram_manager.py`: `_blank_verdict`, `_copy_out`, the ALLOC entries and `_no_check_logged` gone; a missing
  check buffer returns 25caf528's not-valid answer (fault False), so a read logs W63 and returns False, as before
  the audit; the watch loop parks for a chip that set up; `erase_ready()` is the plain two-term form.
- `asy_spi_driver.py`: `available` gone; no remaining reader (`git grep`).
- `asy_system_service.py`: the preflight's catch and re-check gone; `_unpause_at`/`_start_time_set` back to their
  pre-audit order.
- cc5daeb7's comments: the two-block hard failure cites the owner's 2026-07-18 rule, recorded at SPECIFICATION.md
  :266; "the next write heals it" matches `test_two_valid_but_differing_copies_..._the_next_write_heals_them`.
- Run 3: the responder skip reads the role from the wiring model, as `_link_crc_modes()` does; the setup-write
  allowance applies to the attempts check only, the writes check is unchanged (lead approvals, 2026-11-03).

Nothing to change. Left for the falsifier: whether the removed re-check after the preflight can matter (claim 3).
