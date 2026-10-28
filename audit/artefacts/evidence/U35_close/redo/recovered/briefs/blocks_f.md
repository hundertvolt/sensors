# U35 lane F, blocks F1 and F2: the firmware final before the first hardware round (lead, 2026-10-23)
[Recovered verbatim from the lead's context, 2026-10-26. File paths and line numbers refer to the lost integration
heads (0a0476a, c674288, 58a2b3c); re-locate every line on the redo's base before use.]

## Both blocks
- Why: the owner's goal for the first hardware round after U35 is a final firmware (owner, 2026-10-23: "The goal for
  the first hardware round after U35 was to have the firmware final. That's still in place."; LEAD NOTES 142). So each
  open firmware-affecting finding U35 routed out (to U36 or U37) lands here instead; a finding that needs silicon
  evidence stays with its hardware item.
- Base: the integration head the lead names. Branch `audit/u35-f<n>`, worktree `S/wt-u35f<n>`, already rebuilt. Logs in
  `S/u35/laneF/f<n>/`. Commit subject `U35 lane F<n>: <summary>`; decision tags "(agent, <date -u>)". Text outside
  `audit/` cites no audit ID, lane or plan.
- Read first: `S/CHECKLIST.md` (binding), `S/u35/briefs/common_u35.md` (its Rules), LEAD NOTES 142 (the owner's rulings
  of 2026-10-23, quoted), each finding's row in `audit/sweeps/open_findings.md` on `audit/u35-rec` (`S/wt-u35rec`), and
  SPECIFICATION.md Parts C, D and F for the module you touch. The datasheet first for any chip claim.
- Every fix: its test first, seen failing on the current tree; then the fix; the module's tests and every test file
  importing it at both GC stages, zero memory markers; ruff and mypy on changed files; one twin CI device run per stage
  where the fix reaches the task graph. State each fix's effect per device and per operating mode it touches (the
  step-102 mode list in `python3 -I S/u35/tools/steps.py --standing 102`). A sentence a fix makes stale goes to D3.
- Stop rules: a fix that changes a limited-endurance store write (flash filesystem, SCD30 NVM), the UART wire format,
  a REST field's meaning or a logged entry's contract (which code, how many entries per event) is not landed: hand
  back the finding, its options and each option's consequence per device, and the lead asks the owner. A fix that
  misses its premise or creates a new hazard stops for re-evaluation.
- Not yours: `ext/`, `legacy/`, `SPECIFICATION.md` (D3's), and the files other running blocks hold (the lead names them
  at your start). Never run real hardware tools; never read arduino/; no git stash; kill only a checked pid; one test
  run at a time in your worktree; port-binding runs inside `unshare -n S/u24/ns_xdg.sh`, `nice -n 19`; RUNS.md lines.
  About 60-80 tool calls; past 80, commit what is green and hand back the rest at a seam. Hand-back at most 35 lines:
  commits; per item landed (its test's bite, its effect per device), found already fine (the evidence) or handed back
  (options); anything for D3 with its line; last line "nothing of mine is running".

## F1: WiFi and webserver, dead code, first boot
1. The hotspot-exit window (`src/asy_wifi_service.py`; `S/u35/handbacks/N4_final.md:7-8`, its guess not proven, and the
   "Findings routed (a)" paragraph after LEAD NOTES 127 in `S/u35/lane_plan.md`): in hotspot mode an
   NTP retry due at a window's end can run a DNS lookup over the still-up AP, log a persisted NTP error, hold
   `wifi_mode_lock` for the lookup and delay the STA attempt. First show whether it happens (a deterministic unit or
   twin test driving the window's end with a retry due); then fix it or record the proof that it cannot occur.
   [Note 2026-10-26: that N4 was the W7 block N4, whose hand-back is lost; the evidence N4_final.md is an earlier N4.]
2. OF-142 (`src/asy_webserver_service.py:644` `_get_settings_flat()`): a module's unavailable marker is recognised by
   the key test `"error" in values`, so a settings field named `error` would misread every field; the marker made
   unambiguous, test first.
3. Dead code under the owner's library rule (owner, 2026-10-23: "Double check it's really dead code. I don't want real
   features or sensible functionalities removed which could be worthwhile in future use. Always regard the modules as
   libraries, not every feature must be immediately used, as long as it is a real feature."): CE's routed removals
   (`audit/b3/e51.md` on `audit/u35-ce`: the 16 reached only by a direct test, the 3 unreachable,
   `src/asy_sgp40_driver.py:697`) and U35's own removal of `SensorReader.__init__`'s `logger=` branch (find its commit
   with `git log -S` on the integration head). Each classed: a feature (a caller or a config value can reach it
   through the module's public API: kept, its direct test named; the removed one restored with its test) or dead (no
   input can reach it: removed, its proof stated in the commit). The 7 narrowing comments CE routed
   (`src/asy_scd30_driver.py:280`; `src/asy_uart_driver.py:183`, `:290`, `:357`, `:369`, `:810`;
   `src/asy_webserver_service.py:212`), comment only.
4. First boot (owner, 2026-10-23: "No behavioral difference at all should arise from a fresh flash or a first boot. If
   things happen at first boot, they must be triggered by evidence (e.g. no config available, FRAM image does no longer
   fit the layout). This should already be the case. But no special actions just triggered because it's the first
   boot."): scan `src/` and `buildgen/`'s templates for any behaviour keyed on being the first boot (a flag, a counter,
   a marker file, a "fresh" state) rather than on the evidence itself; list every first-boot behaviour with the
   evidence that triggers it. Include the boot after a commanded config reset (CR3: `W CONFIG_LOST`,
   `tests_hardware/flash/test_system_commands.py:117`): the same evidence (no config file) as a lost file, with no
   special case. A behaviour keyed on the first boot itself is a finding, fixed here under the stop rules.

## F2: storage, time, notification, UART, website
1. OF-250 (`src/asy_fram_manager.py:788` `erase_ready()` answers True in the chip-loss window, `get_write_protected()`
   at `src/asy_fram_driver.py:343` answering "not protected" for an uninitialised driver).
2. OF-232 (`src/asy_notification_service.py:225`: `utc_now()` allocates inside the try that guards the producer's
   value read): the age check outside that try, seen failing first with a refused allocation in the age check.
3. OF-247 (`src/asy_ntp_client.py:376`: the resync cadence counts delivered 10 s ticks, so a dropped tick delays the
   resync): the cadence read from elapsed time as the stale rule already is, test first with a dropped tick.
4. OF-246 (each SGP40 storm event persists two entries, so alternating codes defeat the newest-entry rule): read it
   against SPECIFICATION.md C.7's contract; it changes a logged entry's contract, so it is handed back with options
   unless the contract itself already decides it.
5. OF-242 (dev's UART hazard run: 26 small frame copies per run through `src/asy_uart_link_driver.py:230` and
   `src/asy_uart_driver.py:779`): removed where a buffer can be reused, no wire byte changed.
6. OF-139 (`html/style.css:21-22`: `--color-neutral` on `--color-neutral-bg` is 4.16:1 in the light theme, under
   WCAG AA's 4.5:1): the colour brought to at least 4.5:1, the dark theme kept at least as it is; the site tests green.
7. The two test-only rows: OF-103 (`_MAX_SIGNAL_S` and `_LIGHT_CMD_FIELDS`' T maximum, two unpinned copies of 60.0: one
   equality test) and OF-245 (six catalog codes no test names: a test each, seen failing first on a plant).

## F1 start (lead, 2026-10-23)
- Base `0a0476a` (the integration head, CE3 merged). Branch `audit/u35-f1`, worktree `S/wt-u35f1`, rebuilt.
- Item 3 grows by CE3's five re-classed unreachable rows (`S/u35/handbacks/CE3_final.md`; their proofs in e51.md and
  e51_verdicts.json): `src/asy_uart_driver.py:564-565`, `:620-621`, `:672-673` (`if not want:`),
  `src/asy_scd30_driver.py:735`, `src/asy_system_service.py:441`. Same library rule: each one re-read as a feature or
  dead. If `:564-565` goes, rename `tests/test_asy_uart_driver.py:2319`'s test, whose name states the empty-ring premise.
- Held by running blocks, not yours: T4a2's and CM's files. CF1b may add direct tests to any `tests/test_<module>.py`:
  add yours as new functions at the file's end, and the lead merges both. A twin test for item 1 goes in a new file.

## F2 start (lead, 2026-10-23)
- Base `c674288` (the integration head: CE3 and CF1b merged). Branch `audit/u35-f2`, worktree `S/wt-u35f2`, rebuilt.
- Item 2 grows by CF1b's exact-bound survivor at `src/asy_notification_service.py:230`
  (`S/u35/handbacks/CF1b_final.md`; faults.md's row has the proposed frozen-clock test):
  `test_a_stale_producer_sample_is_not_evaluated` skips the exact age, so a sample at exactly the limit gets its test,
  red on the plant faults.md names, alongside item 2's own test.
- Held by F1: wifi, webserver, F1's dead-code sites and their tests. Item 5 touches `src/asy_uart_driver.py:779`, a
  different region: keep to it, add tests as new functions at the files' ends. Item 3 last; if F1 changed
  `src/asy_ntp_client.py`, keep to the cadence lines and name the overlap.
- `html/style.css` and `tests_js/` site tests: item 6 may change the CSS; CM holds `tests_js/` matrices only.
[F2 was stopped by the usage limit on 2026-10-23 after its tests were written ("Now the fixes."); all of it is lost.]

## F3 (lead, 2026-10-23): a caught MemoryError logged at DebugLevel 0 reaches no memory gate
- Base `58a2b3c` (the integration head: CE3, CF1b and T4 merged). Branch `audit/u35-f3`, worktree `S/wt-u35f3`.
- The finding (`S/u35/handbacks/T4a2_final.md`, "Finding for the lead"): the Run 13 red's MemoryError was caught by the
  shutdown sequence's catch-all (`src/asy_system_service.py:481-484`) and logged through the level-gated `err_s`, which
  at the stored DebugLevel 0 (every logger's default, `src/asy_print_log.py` `PrintLog.__init__`) prints nothing; the
  four memory gates read printed text only, so the failure reached none of them. The same holds for every logger call
  that carries a caught MemoryError (about a dozen in src/), in every tier, silicon included. Owner rule broken
  (CLAUDE.md memory rule: zero MemoryErrors, "caught-and-logged included", machine-checked).
- The decision (agent, 2026-10-23, the lead's; LEAD NOTES 146): the fix extends the existing rule that a caught
  MemoryError's text goes through the ungated `console()` (SPECIFICATION.md G.2's console row, C.7, I.4(e); the
  webserver's MemoryError bypass of 2026-10-08 is the precedent) from layers with no logger to every logger: a
  level-gated `PrintLog` method given a MemoryError argument prints that error's text once through `console()`,
  whatever the level. No entry, code, count, REST field or wire byte changes; an OSError stays level-gated.
1. Test first, in `tests/test_asy_print_log.py` (new functions at its end): at level 0, `err` and `err_s` (and any
   other level-gated method a src/ call site gives a caught error: grep them) given a MemoryError print its text once
   and persist the same entry as before; given an OSError, print nothing. Seen failing on the current tree. The ungated
   arm allocates nothing (a heap-locked call, as the file's existing console() tests do), so it cannot raise inside the
   MemoryError arm it reports; fixed arity, no star-call (the console() comment's reason).
2. The fix in `src/asy_print_log.py`, at one place the methods share; header and comments within the cap.
3. Then what it uncovers: `scripts/test.sh` at -1 and at `GC_THRESHOLD=32768`, and `scripts/run_digital_twin_ci.sh`
   for dev and wozi at both stages. Every memory marker that now appears is a caught MemoryError the gates had missed:
   root-cause each one, fix it at its source within the stop rules (a test's deliberate injection is worded clear of
   the markers, CLAUDE.md), or hand it back with its evidence. Name each, with its file, line, tier and stage. None
   appearing is a result too: say so.
4. Effect per device and mode: on silicon at the shipped DebugLevel 0 a caught allocation failure now prints one
   console line, which can wait out a held-open USB port (SPECIFICATION.md F.1's 500 ms note), as `console()` already
   does; nothing else changes. Stale sentences (G.2's console row, C.7/C.7.1, I.4(e), the A.5 line at
   SPECIFICATION.md:563-569, CLAUDE.md's memory-gate paragraph if one is now incomplete) go to D3 with their lines.
[F3 was stopped by the usage limit on 2026-10-23; all of it is lost.]
