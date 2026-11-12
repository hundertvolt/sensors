# TH1: a caller's TEST_TWIN_HOST never silently moves a host-run twin off its talkers' address (lead, 2026-10-28)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back). Then, on your worktree:
- `S/u35r/handbacks_redo/N15.md` (its "Class 7, new" finding, the fix and its doc text);
- `digital_twin/unixport/_unix_port_udp_addr_shim.py` (`_read_twin_host`, `twin_host`) and `scripts/test.sh`'s
  `unset TEST_TWIN_HOST` and pool;
- every launcher of a host-run twin whose talker reaches it at 127.0.0.1: `scripts/run_digital_twin_ci.sh` (Run 7's
  DNS queries), `scripts/_digital_twin_scenarios.py` (the scenario harness, run alone or by test.sh), the tests_scripts
  twins, and the live-tier twins (`tests_hardware` `--twin`, TwinBoard); find any other by reading;
- `digital_twin/run_generic_integration.py`'s starting line (about :1121).

Worktree and base: in your launch message. Logs go in `S/u35/laneC/th1/`.

## The finding (N15, class 7)
A `TEST_TWIN_HOST` exported in the caller's shell reaches a host-run twin. The twin binds its servers there, but its
talker still queries 127.0.0.1, so for example Run 7 fails without naming the variable. `scripts/test.sh` is already
closed: it unsets the variable and sets its own.

## Items, in order (each committed green on its own)
1. **Red first.** For each launcher, a tests_scripts test (or an extension of an existing one) that sets
   `TEST_TWIN_HOST=127.0.0.77` in the caller's environment and shows the twin binding off 127.0.0.1, or the talker
   missing it. Use the cheapest form that shows the real path: a launcher's own env construction, not a full twin boot,
   where that proves the same thing.
2. **The fix, per launcher:** the variable is unset before the twin starts (or the child's env drops it), so the twin
   binds where its talker looks. A launcher whose talker reads the same variable may keep it instead, named.
3. **Naming:** the twin's start line names `twin_host` whenever it is not the default, so a future miss is visible.
   Check first that no test reads that start line's exact text; adjust any that does.
4. **Bites:** each fix removed again in a scratch copy turns its test red.
5. **Checks:** the changed tests_scripts files and test_test_sh.py; the dev scenario harness at both stages if you
   touched it; one `run_digital_twin_ci.sh --device dev` at both stages if you touched it (inside
   `unshare -n S/u24/ns_xdg.sh`, nice 19); lint_direct, the six mypy passes, the three audit checks; review rows if a
   test's text changed.

## Notes
- digital_twin/README.md and CLAUDE.md text goes into your hand-back for the lead's D3r. Do not edit those two files.
- Port-binding runs in `unshare -n S/u24/ns_xdg.sh`, nice 19. One test run at a time in your worktree.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
- Commits; the launchers found and each one's fix or reason; red-first evidence and bites; the start-line change.
- The checks; the doc text. Last line: "nothing of mine is running".
