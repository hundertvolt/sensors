# A-C gap pass, group G4 (targets SCR, TOOL, HW_BENCH, HW_DEV)

Inputs read: the "Gaps for other clusters" section of all 16 `M_*.md` files (every item naming SCR, TOOL, HW_BENCH,
HW_DEV, or `CFG` = `pyproject.toml`, which CLUSTERS.md places under TOOL), the carrying change bodies in the four target
files, `audit/actions/AC_NOTES.md` items 34-45, `PROJECT_AUDIT_PLAN.md` OR rows through OR133 and the three late SPEC gaps
(none names a G4 target). Code at HEAD `0045d7d` (no diff since the merges' HEADs under `scripts/`, `toolchain/`,
`tests_hardware/`, `pyproject.toml`, `.github/`, `host_typecheck.ini`). Edited: `M_SCR.md`, `M_TOOL.md`, `M_HW_BENCH.md`,
`M_HW_DEV.md` (each amendment says "gap pass" in its text) and this file.

## Items

| # | Source, item | Target | Gist | Carried by | Reason (when disposed) |
|---|---|---|---|---|---|
| 1 | M_DOCS gap 2 (SCR part) | SCR | `_digital_twin_ci_suite.py:110` cites BACKLOG item 24, deleted at U19 → SPEC C.7 | amended M.SCR.046 | — (the same comment's "resets every source in turn" is also false after A.U11.31's concurrent reset; reworded in the same edit) |
| 2 | M_DOCS gap 3 (i) | HW_BENCH | README `:1188` section states the tier-parity rule itself, with A.U0.21's tags | amended M.HW_BENCH.133 | — |
| 3 | M_DOCS gap 3 (ii) | HW_BENCH | owed-list intro cites "How a round runs" | M.HW_BENCH.123 (section exists under that name) | — |
| 4 | M_DOCS gap 3 (iii) | HW_BENCH | Workarounds table has a "last checked" column | M.HW_BENCH.128 | — |
| 5 | M_DOCS gap 4 | TOOL | CLAUDE.md CI job list read against U28's `ci.yml`; M_TOOL gap 7's chroot lines | disposed | carried by DOCS itself (M.DOCS.095, M.DOCS.066); no TOOL file changes |
| 6 | M_GEN gap 1 | SCR | generator writes `sensortask_<device>_main.py`, not `<device>_boot.py` | M.SCR.068 | — |
| 7 | M_GEN gap 8 | TOOL | `frozen_html` allowances, `mypy_path += ext/typings`, generated-scope lint rules | M.TOOL.031, .033, .032, .030, .011 | — |
| 8 | M_GEN gap 10 | SCR | mention-only blast items | disposed | general pointer, no item of its own; spot-checked carried: A.U20.14 (5) → M.SCR.066, A.U11.10 → .015/.025, A.U19.20 → .068, A.U20.07/A.U24.54 → .068, A.U27.29 (3) → .066, A.U27.37 → .046 |
| 9 | M_HW_BENCH GAP-B6 | SCR | the hardware wrapper exports `$EVIDENCE_DIR` | M.SCR.034 | — |
| 10 | M_HW_DEV GAP-D5 | HW_BENCH | `harness.reflash()` carries the three tags of the loop it absorbs | amended M.HW_BENCH.014 | — |
| 11 | M_HW_DEV GAP-D6 (a) | HW_BENCH | `standard_state` reads write-protect from `fram_raw_dump.py`'s `write_protected` fact | amended M.HW_BENCH.006, .012 (`save_fram_raw` returns the dump's facts) | — |
| 12 | M_HW_DEV GAP-D6 (b) | HW_BENCH | `bench_facts`/`render_device_script()` provide every key the scripts read | amended M.HW_BENCH.041 (each key a build fact or a caller's extra, with its one source) | — |
| 13 | M_HW_DEV GAP-D11 (HW_BENCH half) | HW_BENCH | `parse_facts(…, allow_missing_done=True)` for `run_isolated_expect_reset()` readers | amended M.HW_BENCH.012 (used by .083) | — (TSC half: M_TSC's incoming list) |
| 14 | M_HW_DEV GAP-D12 | HW_BENCH | bench consumers read the scripts' facts | amended M.HW_BENCH.083, .088, .093, .096; carried M.HW_BENCH.087, .069 | `test_memory_stress_bench.py` part disposed: its end state (M.HW_BENCH.074) runs no device script (HEAD: no `run_isolated` in the file), so no fact to read |
| 15 | M_PROC gap 5 + AC_NOTES 45 | SCR, HW_BENCH | no runner selects `multi_day_rollover` | new M.SCR.074 (`scripts/run_bench_rollover_test.sh`); amended M.SCR.032, M.HW_BENCH.126 | — (agent decision AD-19, below) |
| 16 | M_PROC gap 6 | HW_BENCH | budget table's manual rows list the SCD30 `MeasInterval` step's two NVM writes | amended M.HW_BENCH.130 | — |
| 17 | M_PROC gap 7 | SCR | M_SCR's "LEAD gap" for the `.gitignore` MICROPYPATH sentence | disposed | carried by M.PROC.019 (PROC owns `.gitignore`); M.SCR.009's blast pointer updated |
| 18 | M_SCR gap 2 (a) | TOOL | `host_typecheck.ini` `mypy_path` gains `scripts` | new M.TOOL.079 | — (the file sits in no cluster and no merge carried any of its seven actions; TOOL takes the whole file) |
| 19 | M_SCR gap 2 (b) | TOOL | no `N802` per-file entry for `scripts/_strip_type_checking.py` | amended M.TOOL.030 | — |
| 20 | M_SCR gap 2 (c) | TOOL | `versions.toml` `[stubs]` and its `TypedDict` | M.TOOL.077, M.TOOL.047 | — |
| 21 | M_SCR gap 2 (d), first half | TOOL | `setup_toolchain.py board`, `toolchain_lock()` | M.TOOL.064/.072, M.TOOL.062 | — |
| 22 | M_SCR gap 2 (d), second half | TOOL | `build_firmware()` returns the applied overrides and lwIP macros | disposed | settled by M.TOOL.055 (D3: the uf2 `Path` stays the return); the consumer M.SCR.067 is amended to re-read both from the build dir (AD-20) |
| 23 | M_SCR gap 2 (e) | TOOL | `ci.yml`: generate-then-ruff, mypy paths = `files`, smoke engines flag, `_unix_port.sh ensure standard`, harness budgets | M.TOOL.011, .010, .001, .019 | — |
| 24 | M_SCR gap 2 (f) | TOOL | `.gitignore` MICROPYPATH sentence | disposed | `.gitignore` is PROC's (M_PROC gap 7): M.PROC.019 keeps A.U28.33's text |
| 25 | M_SRC_CORE GAP-G5 | HW_DEV | every direct `start_tasks()` caller passes `task_names` | M.HW_DEV.009 (2) (every system-building script, so .099 too), .026, .117 | — |
| 26 | M_SRC_CORE GAP-G13 | HW_DEV | `float_boundary_2pow24.py` calls the private `_coerce_float()` | M.HW_DEV.109 | — |
| 27 | M_SRC_NET gap 3 | SCR | A.U6.28/A.U10.05/A.U30.03/A.U10.22 checks | disposed | they are `tests_scripts/` checks: M_SCR gap 3 passed them to TSC, and M_TSC's incoming list carries "SRC_NET gap 3" |
| 28 | M_SRC_SENS GAP-5 | HW_DEV | `_overlay_*` names in two ISL29125 scripts | M.HW_DEV.142 (end-state names, B1), M.HW_DEV.143 (`:82` is the rig's own `pixel` → `_pixel`) | — |
| 29 | M_TEST_HELP GAP-H1 | HW_DEV | board mirror follows the probe's order and drops `_STARTER_LOOP_GRACE_MS` | amended M.HW_DEV.117 (it kept the grace sleep) | — |
| 30 | M_TEST_HELP GAP-H2 | SCR | owed content of the moved in-DUT scenarios lands in the harness | M.SCR.018 | — |
| 31 | M_TEST_UNIT GAP-U11 | SCR | the stager keeps one `// ---- js/<file> ----` separator per module | amended M.SCR.019 | — |
| 32 | M_TOOL gap 2 | SCR | `uv_sync_retried.sh` carries the two `tool.uv_sync_*` tags | M.SCR.014 | — |
| 33 | M_TOOL gap 3 | SCR | the image record re-reads lwIP through `read_lwip_macros_from_build()` | amended M.SCR.067 | — |
| 34 | M_TOOL gap 4 | SCR | `mpremote_connect.sh` relays `setup_toolchain: no MicroPython board found …` | amended M.SCR.029 | — |
| 35 | M_TOOL gap 6 | HW_BENCH | the manual imports carry no inline `noqa` | M.HW_BENCH.106 | — |
| 36 | M_TOOL gap 10 | SCR, HW_BENCH | a new spawning host file gets its `S603`/`S607` entry in its creating unit | M.TOOL.030 (rule D8; the entry is `pyproject.toml`'s) | — |
| 37 | M_TSC gap 3 | TOOL | confirmation of `pythonpath`/`addopts` and the per-file entries | M.TOOL.034, M.TOOL.030 | — |
| 38 | M_TWIN gap "SCR" (harness) | SCR | 8 HTTP tests, 9 website tests, API burst, `FAULT_PENDING`, `WDT_AT_FAULT` | M.SCR.018 | — |
| 39 | M_TWIN gap "SCR" (rest) | SCR | `micropypath.toml` gains `digital_twin/unixport`; Run 5's keyed SGP40 fault; `public_destinations_refused=0` | M.SCR.009, M.SCR.053, M.SCR.017/.047 | — |
| 40 | M_TWIN gap "TOOL" | TOOL | `mypy_path` unixport, `:383` exclude, ANN401 entries, PERF401 | M.TOOL.032, M.TOOL.030 | — |
| 41 | M_TWIN gap "HW_BENCH" | HW_BENCH | `twin_board.py` `MICROPYPATH` gains `digital_twin/unixport` | M.HW_BENCH.091 (stage 2 reads M.SCR.009's `twin` value) | — |
| 42 | M_WEB gap 6 (a) | SCR | JS freshness stamp beside the generated definitions | M.SCR.068 | — |
| 43 | M_WEB gap 6 (b) | SCR | `lint:html:built`'s `--stage-only` CLI | M.SCR.019/.020/.071 (AD-4) | — |
| 44 | M_WEB gap 6 (c) | SCR | the smoke reuses `tests_js/_twin_process.js` | M.SCR.064 (AD-11) | — |
| 45 | GAPS_G2.md H-3 (HW_DEV part; coordinator relay) | HW_DEV, HW_BENCH | readers of the attributes G2 made private (GAPS_G2.md item 12) follow the new names, `chunk._block_addr` included | amended M_HW_DEV's B1 convention (the full renamed set), M.HW_DEV.066 (`fram_busy_status_lockout.py:54` → `chunk._block_addr`), .097 and .099 (the watchdog proxy rebinds `sysfunct._watchdog`); M_HW_DEV GAP-D7's text follows | HW_BENCH: nothing to carry — a grep of `tests_hardware/` at HEAD for every renamed name finds only the two device-script readers above (`allocation_need_per_source.py:38`'s `sensortask_dev.watchdog` is a module global, removed by M.HW_DEV.119's A.U20.02 form); no M_HW_BENCH change reads one. Constructor keywords (`max_module_error=`) keep their names (M.SRC_CORE.036) |
| 46 | GAPS_G3 hand-off 1 | TOOL | main-pass `exclude` gains `digital_twin/run_device_script\\.py$` (twin-only `machine.configure_wiring()`) | amended M.TOOL.032 (U26 stage, M_TOOL gap 9's rule; the twin pass's `digital_twin` glob still checks it) | — |
| 47 | GAPS_G3 hand-off 2 | HW_BENCH | the `resetconfig` power-cut step states its rewrite and takes `confirm()` before `config_files_restore.py` | amended M.HW_BENCH.102 (4) | — (A.C.17's manual-branch rule, M.TSC.119) |
| 48 | GAPS_G3 hand-off 3 (a), Table B B11/B21 | SCR | L2 cases with no carrier: A.U19.07, A.U19.08/.10, A.U19.12, A.U30.19's code 20 | amended M.SCR.018 (new (l): negative `Content-Length` → 400, `HTTPDropped` +1 per forced refusal, ISL29125 `Resolution` PUT during GET loops) and M.SCR.059 (new cell (d): `--fault <instance>:<op>:stack` → exit 3, relaunch `ResetReason` 20) | — |
| 49 | GAPS_G3 hand-off 3 (b) (and M_SCR gap 4) | SCR | M.SCR.018 (h) read per-module FRAM write counts; the shutdown line carried one total `fram_writes=` | amended M.SCR.018 (h): each logger's count from `fram_writes_by=<LOGGER>:<n>,…` ≤ `rate.persisted_log` × window; the entries' sum equals `fram_writes=` (cross-check); a missing field fails | — (lead ruling: a check is never weakened to fit the line; G3 amends M.TWIN.050 so the line carries `fram_writes_by`. An earlier total-bound version of this row is withdrawn) |

## Blast-pointer check (G3's method, run for SCR, TOOL, HW_BENCH, HW_DEV)

Every "Blast carried by" item in all 16 files that names a G4 cluster was checked against the target file: 72 items by
cluster label and 212 by a G4 path (`scripts/`, `toolchain/`, `pyproject.toml`, `.github/`, `tests_hardware/`). An item
counts as carried when the target file holds its A-ID or M-ID. All 212 path items were carried. Of the 72 label items,
none needs a new carrier:
- **Carried in a G4 file under another ID or by its range:** A.S0930.20-.29/.34-.40 (the L3/L4 ones, .28/.29/.39/.40, are
  in both HW files); A.U15.R01-R03 and A.U13.R02 (M_HW_DEV/M_HW_BENCH); A.U12.18 (M_HW_DEV); M.SRC_SENS.054's "Runs
  3/4/5c → A.U13.R01" (M.SCR.051 holds the rung behaviour); A.U12.01's CRC32 board measurement (M.HW_DEV.122, R1 in
  M_PROC); A.U15.07's read-back (M_HW_BENCH); A.U20.11's expected JSON (M.SCR.068 writes whatever `expected_facts()`
  returns); A.U23.02's bundle marker (M.SCR.019's derived banner; the assertion is TEST_UNIT's); A.U25.32's smoke
  config dir (M.SCR.064).
- **Labelled G4 but the site is another cluster's:** A.U28.33 `.gitignore` (PROC, M.PROC.019); A.U36.038 ESLint config
  (WEB); A.U29.04 history scan (PROC); A.U28.30, A.U10.47 (`tests_scripts/`, TSC); A.U13.17's harness and buildgen test
  (TEST_HELP, TSC, HW_DEV M.HW_DEV.050).
- **"Unchanged" or "holds" notes, nothing to write:** A.U10.33 (class reorder; the baselines hold), A.U16.10, A.U15.32/.33,
  A.U15.S01 (L4 runs unchanged), A.U10.45 (a grep of `tests_hardware/` finds no assertion on a raise message), M.SPEC.050
  (the UART changelog is DOCS's), and the 25 items without an action ID. Each of those is a gap-section item already in
  the table above (GAP-B6, GAP-D6, GAP-G13, GAP-H2, GAP-U11) or names an existing M-ID or job: M.HW_BENCH.018/.069/.112/.121/.125,
  M.TOOL.006/.012/.030/.079, M.SCR.014, M.TSC.196.

## Hand-offs (other groups carry these; no file of theirs was edited)

1. **DOCS** — (a) M.DOCS.049's rollover line becomes `scripts/run_bench_rollover_test.sh` ("~12.4 days, start it
   detached; on top of a clean bench run"), replacing `uv run pytest tests_hardware/bench --allow-multi-day-rollover -k …`,
   which bypasses the run record and verdict (M.SCR.074). (b) M.DOCS.052's CLI reference gains the runner's entry, equal
   to its `--help` (A.U36.547's check). (c) M.DOCS.066's U27 BACKLOG paragraph gains "`scripts/run_bench_rollover_test.sh`
   (new hardware runner, shellcheck-linted, no environment change)".
2. **PROC** — M.PROC.041 starts R6 with `scripts/run_bench_rollover_test.sh` (detached under `timeout` as written) instead
   of the hand-written wrapper call; its D8 then reads "through the rollover runner" (M.SCR.074).
3. **TSC** — (a) M.TSC.196: the rollover runner runs no lower level and its block reads `Levels: rollover (not a
   level)`; (b) M.TSC.122: the rollover runner's floor `multi_day_rollover` (no caller `-m` → the floor alone; `-m foo` →
   `(multi_day_rollover) and (foo)`) with `--allow-multi-day-rollover` forwarded; (c) M.TSC.217: `TOOLS` gains
   `scripts/run_bench_rollover_test.sh`; (d) `tests_scripts/test_build_firmware.py`'s record test (A.U26.02/A.U26.85):
   `overrides` is `["modlwip_eagain"]` when the build-dir proof passes and `[]` when it raises, `lwip` the read-back dict
   (fakes for the two `micropython_overrides` readers, M.SCR.067).
4. **SPEC** — M.SPEC.156: (a) the rows `l3.toolchain_flash_boot_picotool_load_attempts`, `…_load_timeout_s`,
   `…_load_retry_backoff_s` name `tests_hardware/harness.py` (`reflash()`) as their site (the load timeout also
   `manual/manual_toolchain.py`), M.HW_BENCH.014; (b) withdrawn rows gain `l3.heap_layout_after_full_boot_sequence_starter_loop_grace_ms`
   and `…_starter_poll_ms` (both sites gone: M.TEST_HELP.028, M.HW_DEV.117).
5. **Orchestrator (CLUSTERS.md)** — `host_typecheck.ini` is named under no cluster; TOOL carries it (M.TOOL.079, D17),
   as GEN took `buildgen/limits.py` and WEB its config files.

## Agent decisions for the OR2.c review

- **AD-19** (M_SCR) `multi_day_rollover` gets its own runner. A soak-runner mode is ruled out by G1/R23 ("never in a soak
  tier", owner, 2026-09-26) and M.SCR.032's "not a soak"; a README recipe naming `_require_clean_hardware_run.sh` with
  four internal options is not OR15's copy-paste command, and HEAD's bare `uv run pytest -k` recipe gives no run record,
  verdict or evidence archive. A runner per opt-in long run is the one shape (OR24).
- **AD-20** (M_SCR) The image record re-reads `lwip` and `overrides` from the build dir (M.TOOL.055's D3 keeps the `Path`
  return); `overrides` is `["modlwip_eagain"]` exactly when `verify_modlwip_eagain_in_build()` passes, so the round's
  control image reads `[]` without any build flag.
- **D17** (M_TOOL) TOOL carries `host_typecheck.ini`; the stripper's `N802` entry is not written.

## Owner questions

None. Every item is settled by a rule, an owner row, AC_NOTES or a finished merge's end state; the two design choices
above are agent decisions for the OR2.c review.

## Counts

- Items read: 49 (rows above; the three late SPEC gaps name no G4 target; row 45 arrived from G2 and rows 46-49 from G3,
  via the coordinator). Blast pointers checked: 284 (72 by label, 212 by path), none uncarried.
- Carried as found: 23 (rows 3, 4, 6, 7, 9, 20, 21, 23, 25, 26, 28, 30, 32, 35-44).
- Amended: 18 (rows 1, 2, 10, 11, 12, 13, 14, 16, 19, 29, 31, 33, 34, 45, 46, 47, 48, 49).
- New: 2 (M.SCR.074 for row 15, with M.SCR.032 and M.HW_BENCH.126 amended; M.TOOL.079 for row 18).
- Disposed: 6 (rows 5, 8, 17, 22, 24, 27; row 14's `test_memory_stress_bench.py` part also disposed).
- Handed off: 5 (DOCS, PROC, TSC, SPEC, orchestrator).
