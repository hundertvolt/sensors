# B4 fix round (lead, 2026-11-03)

Read `S/u35r/r1/common_r1.md` (binding), `B4/ACTION_LIST.md`, `B4/REVIEW.md`, `B4/FALSIFY.md` and
`B4/FALSIFY_VERIFIED.md`. Worktree `S/wt-b4`, branch `audit/r1-b4` at `963d0de1`; labels `b4x_`. Test first as
common_r1 says; one commit per fix or one for all, your choice. No gate: the lead runs one on the merged head. Run only
the test files you touch or that pin what you touch, both GC stages, plus lint and the three typechecks at the end.

- F1 the flash tier follows row 5: `por_after_setup` and its assertion (`tests_hardware/flash/test_bus_concurrency.py:258`)
  pin `reset()`'s removed EVENT read; the sweep and `_shared/bus_reader_loops.py` follow the removal, smallest form.
  Show it: the falsifier's `b4f_flash_twin` command (its log in `S/u35/lead/`) passes under `--twin`.
- F2 the two bench erase tests (`bench/test_system_commands_over_rest.py:172-174`,
  `bench/test_bus_concurrency_under_api_load.py:424-426`) admit exactly the W65 each SGP40 logs on its blank chunk after
  the erase, nothing else; `--collect-only` for both files.
- F3 `voc_algorithm.py`: the uptime cap back to 32767 (pre-audit, legacy, the C reference) without its comment; tests
  pinning 16383 follow. Show it: the falsifier's `b4f_probe_voc` (`B4/ftmp/`) finds the stored state equal to
  `25caf528`'s on every sample.
- F4 `_reset_errors_not_undone` (`scripts/_digital_twin_scenarios.py:1644-1645`): the at most one entry is that SGP40's
  W65 (`_WRN_SGP_NO_BACKUP`), nothing else.
- F5 `SharedBoot.acquire()` (`:378-380`): a boot whose W65 never comes fails there (`_expect` the wait's answer).
- F6 SPECIFICATION.md:8952-8955 says what the SCD30 holds and allocates now; `asy_isl29125_driver.py:745`'s comment
  follows the fresh snapshot copy.

Hand-back: append "## Fix round" to `S/u35r/r1/B4/HANDBACK.md` (per fix: outcome, test seen red then green, runs).
Your final message: the commit(s), one line per fix, last "nothing of mine is running".
