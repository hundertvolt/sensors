# CRr2c: the flash tier's log check, validated through the twin with ring dumps (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back). Then `S/u35r/briefs/crr2_hardware_rows.md` (its "CRr2c" paragraph, "Proof and checks", "Not yours",
"Shell discipline" and "Added for CRr2b" are binding here). Then, on your worktree:
- CLAUDE.md's FRAM error-log bullet ("When investigating any unexpected real-hardware error or reset") and its caveat
  about isolated-driver device scripts sharing production's first FRAM chunk;
- `tests_hardware/bench/conftest.py`'s `no_unprovoked_log_entry` and `_expected_entries`, `tests_hardware/markers.py`'s
  `provokes_log` row, and `tests_hardware/error_log_helpers.py` (`read_live_system_log`, `new_logged_entries`,
  `assert_no_unprovoked_entry`, `provoked_entries`): the bench tier's check, which this lane mirrors for flash;
- `tests_hardware/harness.py`'s `parse_facts()`, `tests_hardware/device_scripts/_shared/facts.py`, and how a flash test
  runs a device script on the board and through `--twin` (TwinBoard);
- the recovered map `S/u35r/recovered/handbacks/CR4_final.md` ("Item 2: plan only") and CR3's provoked list in
  `S/u35r/recovered/handbacks/CR3_final.md`: a map to re-check, never proof;
- `S/u35r/handbacks_redo/CRr2b2.md` (its scratch-config CONFIG_LOST find) and `CRr2b12.md` (the last state of the
  fixture area).

Worktree and base: in your launch message. Logs go in `S/u35/laneC/crr2c/`.

## Why
The bench tier fails a test that leaves an E or W entry it did not set out to provoke. The flash tier has no such
check: a device script can log an entry nobody reads, and the test passes. CR4 planned the flash half and never landed
it. src/ keeps no logger registry, so no single helper can read "every logger": each script must name its own.

## Items, in order (each committed green on its own)
1. **The `logs` fact.** A shared device-script helper that reads the named loggers' E and W entries (or a sysfunct's)
   and emits them as one FACT; one call per device script that touches a logger, naming its loggers. `parse_facts()`
   collects it as it collects every fact. Find every script that needs it by reading, not by a name grep alone.
   - A script that leaves a well-formed chunk in production's first FRAM chunk fabricates evidence (CLAUDE.md's caveat):
     say for each script whether it writes there, and whether its `logs` read could read production's entries rather
     than its own.
2. **The flash fixture.** An autouse fixture in `tests_hardware/flash/conftest.py` that fails a test on a `logs` entry
   outside its `provokes_log` set, naming module, code, catalog name and test, honouring the same marker and its
   collection-time refusal as the bench tier. Re-find the provoked flash tests (CR3 counted 19) and mark each with its
   reason and its exact expected entries, from the test's own comment or name and from source lines.
   - CRr2b2's find: a scratch-config device script can write W CONFIG_LOST into production's SYSTEM FRAM log. Decide
     with source lines whether that is provoked by the test (marker) or an artefact the script must not leave (fix the
     script). Hand the evidence to the lead if it is a product question.
3. **Validation through the twin.** Every changed flash file through `--twin` at both GC stages, with each script's
   ring dumped and compared to the set its marker names (a set derived by reading alone is run through the twin wherever
   its script runs there). Each gap or surplus is root-caused: a wrong set is fixed; a twin infidelity is named with the
   twin's and rp2's source lines and handed to the lead (digital_twin/ is not yours). Scripts the twin cannot run are
   named with the reason.
4. **Bites**, in tests_scripts, each seen failing first: on synthetic script output (an unprovoked entry fails the
   fixture, a provoked one passes, a marker without a reason is refused, an entry beyond the named set fails), and through
   TwinBoard for at least one planted unprovoked entry.
5. **Checks:** the "Proof and checks" list of crr2_hardware_rows.md, plus `--collect-only` of the whole tests_hardware
   tier (state collected and deselected), and review rows re-rendered if a test's text changed.

## Notes
- No real hardware. `tests_hardware` only with `--collect-only` or `--twin`. Port-binding runs in
  `unshare -n S/u24/ns_xdg.sh`, nice 19.
- Lane CRr2d may run beside you on the bench tier's sets. You own `tests_hardware/flash/`, `tests_hardware/device_scripts/`,
  `tests_hardware/error_log_helpers.py` and `tests_hardware/markers.py`; CRr2d owns the bench tests' markers and
  `tests_hardware/bench/conftest.py`. A change you need in the other's files goes to the lead.
- test_twin_record stays red for changed hardware files; hand the lead the list of scripts whose twin record changes.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
- Commits; the scripts given a `logs` call, with their loggers; each script's production-FRAM answer.
- The marked flash tests with their reasons and sets; the CONFIG_LOST decision and its lines.
- The twin validation per file and stage (set against ring), every gap's root cause, the scripts the twin cannot run.
- The bites with their red-first evidence; the checks; the twin-record list.
- Last line: "nothing of mine is running".
