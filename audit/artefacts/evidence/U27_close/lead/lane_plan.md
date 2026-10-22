# U27 (SCR: `scripts/` and the host-side script tooling) lane plan (sites at `0c0ad52`)

**One pass (agent, 2026-10-15)**: plan, cut and briefs from the audit tree at `0c0ad52` (U26's pushed unit commit, CI green;
the U27 base, no relocation), read only through git. Every site below is `file:line` at `0c0ad52` with its quoted text; the
M and A texts in the packets carry the A-L HEAD's line numbers, so lanes locate by quoted text. Rulings: `briefs/rulings.md`
(R-1..R-25). Placeholders kept literal: `<API>` (`audit/u27-api`: T's T1 commit on `0c0ad52`), `<W1>` (`audit/u27-w1`: the
four code lanes merged plus the lead step), `<W2>` (`<W1>` plus M and X). Binding for every agent: `S/CHECKLIST.md`,
`S/u21/CONCURRENCY.md` (rule 13 above all: effort is the measure).

## 0. Sources and tools

Sources at `0c0ad52`: `audit/actions/U27.md` (A.U27.01-.39; Ledger, Register fixes, Open points, Closing inventory),
`audit/order/work_order.json` (U27), the M entries its steps name (`audit/consolidation/M_*.md`), `audit/REGISTER.md` rows
naming U27 (13: `:53`, `:577`, `:604`, `:615`, `:618`, `:651`, `:656`, `:663`, `:664`, `:666`, `:670`, `:740`, `:742`),
`audit/sweeps/open_findings.md` (28 rows name U27: 25 target it, OF-125/141/183 name a U27 part), U26's close record
`audit/sweeps/scan_runs/20261015_U26_close.md` (`:70-78`) and review list
(`audit/artefacts/evidence/U26_close/lead/review_list.md`: `:21`, `:23`, `:29`, `:30`, `:89`, `:99`, `:116`, `:122`, `:146`,
`:165`). Models: U26's plan, gaps, packets and briefs; command forms `S/u24/briefs/common.md` "Runs" (`:49-80`) and "Before
every commit" (`:93-103`), cited, never copied.

Tools (`S/u27/tools/`, each `python3 -I <tool>`): `root_0c0ad52/` (git archive of `audit/` parts at `0c0ad52`, never
evidence); `step_packet.py` (the audit tool on that copy) → `pk/U27_steps.md` (966 KB, every step's merged text and action);
`steps.py` → `u27_steps.json`, `all_acts.txt`; `index.py` → `changes_index.txt`; `judged.py` (the per-change placement:
lane, verdict, U27 part, check, round); `routed.py` (open findings, register and review rows per lane); `lanes.py` (the sets,
`../files_<L>.txt`, disjointness per wave, sizes); `extract.py` → `pk/packet_lane<L>.md`; `cap_new.py` (the comment-cap
gate's new counting over a tree copy, the R-4 numbers); `enc_sites.py` (OF-118's site count); `show.py <ID>` prints any M
entry or action. The two counts ran over a throwaway `git archive` of `0c0ad52`, deleted after (rerun: archive the
eight scopes plus `js/`, `tests_js/`, `html/` into a scratch dir and pass it).

## 1. Counted against the work order

- **Steps**: the work order's 246 changes in 204 numbered steps (192 explicit + 54 implicit) are all placed (`judged.py`,
  none unplaced): 188 to write (147 code/test `apply`, 35 docs `x`, 6 `lead`), 51 `verify` (landed earlier, each with its
  proof, R-10), 7 `u28` (no U27 part: the line is U28's). Two co-landing groups: step 31 (4 changes, all U) and step 77
  (40 changes: B 27, T 8, S 5; one squash lands it, each lane applies its own members). Per lane (changes / steps written):
  T 41/35 (+13 verify), U 29/26 (+24 verify, 1 u28), B 56/31 (+8 verify), S 21/17 (+4 verify), X 35/35, lead 6/6
  (+2 verify, 6 u28). M holds no work-order step: it carries OF-118 (§6).
- **Actions**: 58 = the work order's `actions` field = the union of the steps' `carries` (39 A.U27, 4 each A.U21, A.U26,
  A.U7, 2 each A.U20, A.U24, 1 each A.S0930, A.U18, A.U8); every one is in at least one packet (`tools/act_lanes.json`).
  A.U26.56 (the off-subnet spoof attempt) is a verify row with its hardware part parked (R1 [H61]).
- **Files**: 216 in the work order; the lane sets hold 245 distinct paths (T 40 incl. T1's 12, U 61, B 47, S 27, M 95 of
  which 36 are wave-1 files again, X 6, lead 5);
  the work-order paths outside every set are verify-only, U28's, retired (`tests/_webserver_concurrency_scenarios.py`,
  `tests/test_digital_twin_real_website_integration.py`, `tests_hardware/isl29125_conformance.py`), renamed
  (`src/api_response.py` → `src/asy_api_response.py`, `tests/test_api_response.py` → `tests/test_asy_api_response.py`,
  `digital_twin/_unix_port_udp_addr_shim.py` → `digital_twin/unixport/`) or the lead's W1 one-liners (gaps.md §1, §4).
- **Scoped tests**: 239 in the work order. **Full gate**: its seven items (lint; the three mypy passes; `scripts/test.sh` at
  -1 with the tests_scripts tier; at 32768; `scripts/run_digital_twin_ci.sh <device>` for every device; the web tier;
  `--coverage` and `npm run test:coverage`). **Hardware rounds**: R0 [H56, H57], R1 [H61, H73], R3 [H73], R6 [H63] (§7);
  nothing runs on hardware in U27.
- **Register**: no parked delta for U27 is open (`step_packet.py` lists none); the 13 rows are routed in §6.

## 2. The cut (R-1): four code lanes, one API stop, then two lanes on the merged tree

| wave | lane | family | base | changes / steps written | est. lines / files |
|---|---|---|---|---|---|
| 1 | **T** runners and the shared runner libraries | T1 first: `scripts/_unix_port.sh`, `micropypath.toml`, `_devices.sh`, `_require_python.sh`, `_port_lock.py` with `test_unix_port_sh.py`, `test_devices_sh.py`, `test_port_lock.py`, `test_shell_conventions.py`, `test_twin_never_needs_tests_on_its_path.py`, `test_require_python.py`, `_devices.py`; then `scripts/test.sh`, `_port_lock.sh`, `_summary_block.sh`, `_archive_evidence.py`, `_run_lower_levels.sh`, `_require_clean_hardware_run.sh`, the five hardware runner shells and the new rollover runner, `mpremote_connect.sh`, `setup_cross_browser_toolchain.sh`, `tests_scripts/conftest.py`, `test_test_sh.py` and the runner tests, `tests_hardware/twin_board.py`, `kick_then_reset.py`, `spoof_udp.py`, `manual/manual_bus_electrical.py` | `0c0ad52` | 41 / 35 | ~2200 / 40 |
| 1 | **U** unit tier, `src/` comments, the comment-cap gate and headers | `src/asy_api_response.py` (`parse_cmd_request()` goes), five `src/` comment sites, `tests/test_setter_microdot_integration.py` on the product routes, `tests/test_asy_api_response.py`, `test_asy_webserver_service.py`, `tests/_src_const.py` and its 27 callers, the 24 headerless `tests/` files, the four divider files, `tests_scripts/test_comment_block_cap.py`, `html/index.html`, eight `tests_js/` headers, `js/mock-server.js`'s code table (`tests_scripts/test_js_api_mirrors.py:130` mirrors it), OF-150/151/155/158/168 | `0c0ad52` | 29 / 26 | ~1400 / 61 |
| 1b | **B** build chain and its gates | `scripts/build_firmware.py`, `_strip_type_checking.py`, `_generate_sensortask_modules.py`, `build_website.sh`, `build_frozen_html.sh`, `build_device_websites.sh`, `_stage_website.py`, `_render_coverage.py`, `lint.sh`, `typecheck.sh`, new `_require_venv.sh`, `_check_gc_collect_sites.py`; `buildgen/{codegen,generate,validate,definitions,source_ast,frozen_modules}.py`; `toolchain/{setup_toolchain,micropython_overrides}.py`, `versions.toml`; `pyproject.toml`, `host_typecheck.ini`, `digital_twin/typecheck.ini`; ci.yml's two U27 stages; their tests (new `test_stripped_image_boots.py`, `test_frozen_inputs_reproducible.py`, `test_lint_type_scopes.py`, `test_require_venv_sh.py`, `test_host_cli_exit_idiom.py`) | `<API>` | 56 / 31 | ~2800 / 47 |
| 1b | **S** twin suite, harness, twin runners, the JS twin frame | `scripts/_digital_twin_ci_suite.py`, `_twin_process.py`, `_digital_twin_scenarios.py`, `run_digital_twin_ci.sh`, `run_unix_port_integration.sh`, `cross_browser_smoke.mjs`, `record_twin_instrument_runs.py`; `digital_twin/run_generic_integration.py`, `machine.py`, `_sgp40_chip.py`; the suite/harness tests (new `test_run_digital_twin_ci_sh.py`), `tests/test_digital_twin_machine.py`, `..._run_generic_integration.py`; `tests_js/_twin_process.js`, the two live commands, new `_micropypath.js`, the live tests; one line each in `tsconfig.node.json`, `eslint.config.js`; OF-114/147/157/162-166/181 | `<API>` | 21 / 17 | ~1400 / 27 |
| 2 | **M** the host text-encoding sweep | new `tests_scripts/test_host_text_encoding.py` and every `scripts/`, `toolchain/`, `tests_scripts/` file with a site at `<W1>` (94 at `0c0ad52`) | `<W1>` | OF-118 | ~800 / 95 |
| 2 | **X** docs from the relay | SPECIFICATION.md, README.md, CLAUDE.md, BACKLOG.md, digital_twin/README.md, tests_hardware/README.md | `<W1>` | 35 / 35 | ~1000 / 6 |
| — | **lead** | the shrink-only lists (`_citation_allowlist.txt`, `_decision_vocab_allowlist.txt`, `test_import_placement.py` `_PENDING`, `test_no_variant_literals.py` `_NOT_YET_CLEANED`, `test_mypy_any_baseline.py`); at W1, after the lanes: the relayed config lines, A.U27.37's two one-line callers, the conftest insert with `pythonpath`, the setter override (R-6, R-7, R-8) | merge points | 6 / 6 | ~30 / 5 (+ one-liners) |

Why this shape (rule 13): five shared files (the Unix-port probe, the MICROPYPATH layouts, the derived device list, the
Python check, the CPython port lock) are read by nearly every runner, build script and twin launcher, so they come first as
T's T1 with the guards that judge every script (shell conventions, every launch site reading the layout file, the Python
check): each later lane's seen-failing-first is a T1 guard red on its own file at `<API>`. U needs none of them and starts
at once beside T1. Lint/typecheck and the build chain are one lane because A.U27.09 puts the generated output into both
gates and every finding there is fixed at the template (`buildgen/codegen.py`), and because `toolchain/setup_toolchain.py`
carries both A.U27.02's typed pins and A.U27.29's error contract. The encoding sweep spans ~94 files no parallel set may
hold, so it runs alone on the merged tree beside the docs. At most four lanes run at once (wave 1b), two in wave 2.

**Disjointness**: `cd S/u27; for w in "T U B S LEAD" "M X"; do for a in $w; do for b in $w; do [[ $a < $b ]] && comm -12
<(sort files_$a.txt) <(sort files_$b.txt); done; done; done` prints nothing, and `cat files_{T,U,B,S,LEAD}.txt | sort |
uniq -d` and `cat files_{M,X}.txt | sort | uniq -d` print nothing (checked by `tools/lanes.py`). Wave 2 overlaps wave 1's
files by design (it starts from `<W1>`, after every wave-1 lane is done). A change that turns another file red carries that
file into its lane wherever the file is the change's own family; the exceptions are the doc checks (X's), the shrink-only
lists (the lead's) and the T1 guards, which are red on other lanes' scripts until those lanes land (R-9).

## 3. Merge points, the API stop and the relay

1. **`<API>`** (the one stop): T commits **T1** first (`U27 lane T WIP T1: <summary>`): the five shared files, the six test
   files and `tests_scripts/_devices.py`'s docstring (`files_T1.txt`), with their command forms exactly as M.SCR.007-.010/.013 state (`derived_devices`,
   `require_device NAME` → exit 2 naming the valid devices; `require_python311`; `unix_port_bin|check|ensure <flavour>`,
   `micropypath unit|twin`, the record and input-hash rebuild conditions, the shared toolchain lock; `micropypath.toml` with
   exactly `unit = "build/generated_src:src:tests:frozen_modules:.frozen"` and `twin =
   "build/generated_src:src:digital_twin:ext:frozen_modules:.frozen"` — today's `scripts/_twin_process.py:24`
   `TWIN_MICROPYPATH = "build/generated_src:src:digital_twin:ext:frozen_modules:.frozen"`; `port_lock(port, runner)` with
   M.SCR.012's contract). Its own L0 files green; the three guards (`test_shell_conventions.py`,
   `test_twin_never_needs_tests_on_its_path.py`, `test_require_python.py`) red only on other files, each red line listed in
   the hand-back. The lead merges T1 `--no-ff` onto `0c0ad52` as `audit/u27-api`, rebuilds (`S/u23/rebuild.sh`), runs ruff,
   shellcheck, the three mypy passes cold and the T1 files, then launches B and S on `<API>` and resumes T.
2. **`<W1>`**: T, U, B, S finals merged (`audit/u27-w1`); rebuild; the **lead step** (brief_lead.md): the relayed
   `pyproject.toml` lines (R-7), A.U27.37's two callers, conftest's insert with `pythonpath = ["."]`, the setter override,
   the Any-baseline section the suite's cleared `Any` empties, the list rows U27's files make stale (R-8); every T1 guard,
   the idiom test and the scope test green; then M and X launch on `<W1>`.
3. **`<W2>`**: M and X merged; then the unit gate (`S/gate_v15.sh`, U26's re-gate layout, updated as brief_lead.md says:
   the work order's seven items, the twin tier for every device at both GC stages, `uv run pytest --collect-only
   tests_hardware -q`).

**The relay**: `S/u27/relay.md`, append-only, one heading per lane. Each lane appends before hand-back: every new or moved
`@tunable` (ID, value, site, basis); each command form or API end state another lane or X reads; config lines owed (R-7,
each with its `ruff check --config` proof); its BACKLOG build-environment line(s) (§8); doc lines owed by the doc checks
(citations, Part N, B.4/B.11/B.15/E.x/F.5.5/I.4/L.x rows the packets name for X); silicon-only facts; CI changes it would
need that are U28's (R-18); its after-times. X reads only the relay, its packet and the tree.

## 4. Sizes and the splits each lane would take (R-2)

Estimate (`tools/lanes.py`): rewritten or added lines; an existing file counts 45 % of its `0c0ad52` length unless the plan
names a smaller edit (headers, typed reads, comment lines), a new file a typical size for its kind; M counts its sites. Big
inputs: `scripts/test.sh` 945 lines, `tests_scripts/test_test_sh.py` 1835, `scripts/_digital_twin_ci_suite.py` 1731,
`scripts/_digital_twin_scenarios.py` 1656, `scripts/build_firmware.py` 268, `tests/test_setter_microdot_integration.py` 990.

- T (~2200/40) → **T-a** T1, `test.sh` and its tests | **T-b** the hardware runners, wrapper, `mpremote_connect.sh`, the
  manual steps and `twin_board.py`; costs a lane's fixed cost for a family that shares `_devices.sh` and the floor tests.
- U (~1400/61, 40+ files from one-line headers and typed reads) → **U-a** the setter rewrite, the envelope, `src/` comments,
  OF-150/151/155/158/168 | **U-b** the cap gate, every header and divider, OF-153; the two share 8 test files (headers and
  typed reads in files U-a rewrites), so the split would need a file-by-file cut.
- B (~2800/47) → **B-a** the build chain (firmware, website, generator, stripper, buildgen) | **B-b** the gates (lint.sh,
  typecheck.sh, the checker, the three mypy configs, the toolchain files, ci.yml's two stages), with the generated-scope
  findings relayed B-b → B-a.
- S (~1400/27), X (~1000/6) inside the bar. M (~800/95) is mechanical: one site class, one guard.
Kept whole (rule 13): each split adds a lane's fixed cost (reading, worktree, rebuild, checks) for no gain the merge needs.

## 5. Rulings

`briefs/rulings.md` R-1..R-25, one line each (agent, 2026-10-15), every one on the owner-review list at U27's close. One
point has no conservative default the plan can take on the owner's behalf: owner question 1 (the comment-cap length rule,
R-4's default meanwhile).

## 6. Open findings, register and review rows, by lane

Full rows with defaults and checks: each packet's "Open findings and register rows routed to this lane" (`tools/routed.py`).

| row | lane | default (ruling) |
|---|---|---|
| OF-89 tests_scripts bound comment | T | comment states the measured tier; 1200 s kept (R-12) |
| OF-124 record checked for presence only (`scripts/test.sh:177` `elif [ ! -f "$toolchain_record" ]; then`) | T (T1) | `unix_port_ensure` compares `input_sha256` |
| OF-126 binaries read while setup rebuilds them | T (T1) | shared non-blocking toolchain lock (R-15) |
| OF-60, OF-70 manual FRAM-pull latency, pulled UART line | T | written, parked R2 [H17, H37] (R-23) |
| REGISTER `:577`, `:664`, `:666`, `:670`, `:740`; review R-10, `:99`, `:116` | T | rollover runner; OF-60/70; SF-M4-06 in the job runner; TwinBoard's layout; `:116` (a streaming run API) is a reversal option, not written (gaps §5) |
| OF-150, OF-151, OF-153, OF-155, OF-158, OF-168 | U | measure-then-fix (OF-150, R-12); bus-error-only sweeps; typed `_src_const`; KeyboardInterrupt re-raised; D.15 order; event-ended cases |
| OF-186 `# @include` counted as prose | U / lead | not added to `_TAGS` (R-5) |
| OF-144 one build stamp | B | build-chain half; the page's comparison moves on (R-12) |
| OF-154 buildgen caches | B | text-keyed parse cache, per-file import cache |
| OF-182 bench sudo rule for the spoof | B | probed by `env --tier bench`; host check R0 [H57] |
| OF-141 (U28's), OF-125 (U28's), OF-183 (C) | B | the wipe; the pins; no code, R1 measurement (R-12) |
| REGISTER `:604`, `:615`, `:742`; review R-18, R-19 | B | work dir, flock and checks; OF-144; SF-M4-07's image-then-record order; M.SCR.065's other parts |
| OF-114, OF-147, OF-157, OF-162, OF-163, OF-164, OF-165, OF-166, OF-181 | S | feed-gap check; no `uv run` in the live commands; Timer drop knob; event-ended waits; runner flags; SGP40 walk sourced or kept (R-12) |
| REGISTER `:618`, `:656`, `:663` | S | OF-147, OF-114, OF-181 |
| OF-118 host text I/O without `encoding=` | M | AST guard, every site `encoding="utf-8"` (R-13) |
| REGISTER `:53`, `:651` | lead | status row at the close; A-35's routing (informational) |

## 7. Parked hardware items, per round (nothing runs in U27)

Every round: the owner's go-ahead in its own conversation (CLAUDE.md); the FRAM-backed `errcount` and the raw FRAM saved
before anything writes (U26's session fixture `fram_evidence_saved`; an isolated-driver script lands on production's first
chunk, so the logs are read before any FRAM script and before any `ResetErrors`); the lower levels L0-L2 at both GC stages
first (the runners, T's floor and `_run_lower_levels.sh`); the image record and `board_image` (U26); the standard board
state at start and end; the wear gates deselect (`persistence_write`, `scd30_extra_write`), the flash-cycle, soak,
rollover, NeoPixel and toolchain gates skip in the test body (U26).

| round | item | what runs (U27 code it depends on) | markers and wear gates |
|---|---|---|---|
| R0 | H56 | the speed-probe bands, `tool.*` step timings and the lwIP host hammer's slowest write measured on the bench host (T's speed-band cases in `test_test_sh.py` hold the logic) | none (host only) |
| R0 | H57 | `uv run toolchain/setup_toolchain.py env --tier bench` on the bench Pi: OS record, sudo/`--preserve-env`/`nmcli edit`/picotool checks, uv pin, stale packages, and OF-182's spoof sudo probe (B) | none (reads only) |
| R1 | H61 | the two spoofing tests and the off-subnet attempt (`tests_hardware/bench/test_network_resilience.py`, `test_hotspot_role_reversal.py`); needs the sudo rule H57 confirms; A.U26.56's permanent-skip entry decided after (`tests_scripts/test_hardware_verdict.py` holds it) | default run |
| R1 | H73 | A.U27.19: each runner with a caller `-m` runs the floored selection (`scripts/run_flash_hardware_suite.sh -m <expr>`, `run_bench_hardware_suite.sh`); A.U27.29: `scripts/run_manual_hardware_tests.sh --list`; A.U27.37: the bench tests reading the ceiling (`bench/test_heap_under_connection_ceiling.py`, `bench/test_network_resilience.py`); OF-183's DNAT delivery (C) | default run, wear gates off |
| R2 | H17, H37 (from OF-60, OF-70) | the FRAM unplug-replug step with its latency, the pulled crossover-jumper step (T's `manual_bus_electrical.py`) through `scripts/run_manual_hardware_tests.sh --only <step>` | manual `confirm()` before each step; no persisting write |
| R3 | H73 (gated) | the floored runners with `--allow-persistence-write` where U26's gated rows run | `--allow-persistence-write` |
| R6 | H63 | `scripts/run_bench_rollover_test.sh` (T): builds the tick-offset image (`build_firmware.py --tick-offset-test`, B; record `overrides` names it), one reflash, ~2 h of REST polls (`tests_hardware/bench/test_ticks_ms_rollover.py`, U26), then the release image again; inside session 1 after R5 and before R4 (U26 §7) | `--allow-multi-day-rollover` + `--allow-flash-cycle`; evidence saved before the reflash |

Parked from U26 and untouched here: M.HW_BENCH.038 (R1 [H25, H26]), M.HW_DEV.116 (R1 [H44]), M.HW_DEV.001 (R1 [H73]).

## 8. Operating modes, GC stages and build-environment lines

| mode | steps that touch it (lane) |
|---|---|
| `scripts/test.sh` at gc -1 | T: 12, 77 (SCR.035-.045: validation, job runner, memory gate per attempt, dispatch with one `scenarios[<device>]` job per derived device, summary), 102 (flavours through the probe), 103; U's L1 files; B's tests_scripts tier files |
| `GC_THRESHOLD=32768 scripts/test.sh` | the same files through `tests/_threshold_runner.py`; the harness jobs forward `--gc-threshold ${GC_THRESHOLD:--1}` (A.U27.38, R-16); U's twin files (OF-168) at both stages |
| the coverage build (`--coverage`, build-settrace) | T: the settrace flavour through `unix_port_ensure settrace`, harness and lwIP jobs listed under Skipped (M.TSC.136); `test_coverage_runner.py` through `check settrace` (151); B: `_render_coverage.py` (77 SCR.069) |
| the twin CI suite and harness parts | S: `run_digital_twin_ci.sh <device>` archives per device, runs the suite at -1 and 32768 then the harness at both (77 SCR.061, already wired at `scripts/run_digital_twin_ci.sh:143`), the CRC16 rerun (`:126-135`, landed); suite Runs 9-11b (107, 108, OF-162-164); harness (77 SCR.017, OF-165/166) |
| the manual twin launch and the smoke | S: `run_unix_port_integration.sh --device <d>` (77 SCR.062), `cross_browser_smoke.mjs` (77 SCR.064), both under the port-53 lock |
| hardware runner levels | T: L3 flash (9), L4 bench (101), soak duration (61), rollover (62), manual (11); the wrapper's floor (60, 63); lower levels first (93); verdict (58 verify) |
| installer tiers generic / flash / bench | B: the typed `[stubs]` table read by every tier (44, 45), `SetupError` and the handler (77 TOOL.045/.072), OF-182's bench probe; T: `unix_port_ensure` runs `setup` (T1) |
| firmware builds | B: default, `--no-autostart` (77 SCR.065), `--tick-offset-test` (with M.GEN.009/.019), `--device-toml` (landed U26), staging and manifest (77 SCR.066), image record and report (77 SCR.067) |
| website builds | B: one device (77 SCR.071), frozen archive (77 SCR.072), every device and `--stage-only` (6) |
| lint / typecheck | B: generated scope, `grep_guard`, the checker, three passes plus two single-file checks, venv and Python checks (5, 22, 59, 77) |
| the web tier | U: eight test headers; S: the JS twin frame and live tests (200-203) |

**BACKLOG build-environment lines** (CLAUDE.md "Pull request workflow"; each lane relays its line, X writes them): T1 —
"one Unix-port probe for every runner; build flavours standard/settrace/lwip" (A.U27.12), "the two MICROPYPATH layouts live
in scripts/micropypath.toml" (.15), "scripts share _devices.sh; device arguments validated up front" (.33), "every bare
python3 in scripts/ is version-checked first" (.10), "runs hold the toolchain lock shared" (OF-126); T — "test.sh builds the
first derived device's site" (.08); B — "typecheck.sh installs exact stub post-releases from versions.toml [stubs]; a moved
stub tree fails the repair" (.02), "the TYPE_CHECKING stripper no longer uses ast.unparse" (.04), "the pytest tier runs
mpy-cross from the toolchain dir" (.05), "build_frozen_html.sh gzips with -n" (.06), "lint.sh generates build/generated_src
before ruff; mypy's main pass checks it" (.09), "the generator writes atomically and prunes stale device outputs" (.11),
"lint.sh's grep guard fails on grep exit 2" (.20), "lint.sh runs a Python gc.collect site checker" (.21), "all three mypy
configs enable ignore-without-code" (.22), "typecheck.sh runs two single-file mypy checks after the three passes" (.23),
"lint.sh/typecheck.sh check the venv (uv sync --locked --check)" (.26), "host_typecheck.ini mypy_path gains scripts" (.27),
"firmware/website builds keep their work dirs under build/" (.35), "env --tier bench probes the spoof's sudo rule" (OF-182);
S — "run_digital_twin_ci.sh archives digital_twin_ci_logs/<device> under build/archive/" (.16); lead — "pytest pythonpath =
['.']" (.37); M — "a host text read or write without encoding= fails tests_scripts" (OF-118). The steps carrying them: 5, 22,
43, 45, 59, 67, 76, 94, 97 and step 77's SCR.007/.010/.025/.028/.039/.061/.065/.068/.070/.071/.072, TOOL.032/.079,
TWIN.075, TSC.131; plus OF-126 (T1), OF-182 (B), OF-118 (M).

## 9. CI time and the timing base

Base (R-21): U26's close, `audit/artefacts/evidence/U26_close/gates/final_times/final_times/times.tsv` for the tests_scripts
files it lists, and gate2 (`gates/gate2/gate2/gate.out`): lint 2 s; typecheck 36 s per run; `scripts/test.sh` at each stage
about 11 min (both stages side by side, `Test parallelism: 4`), its tests_scripts tier 698 s (`gc_default.log:6289` "5730
passed, 6 skipped in 698.16s"); the harness part of the six twins at both stages 12.9-15.3 min per device under 4-way
contention (gate1's full suite-plus-harness 29.7-37.0 min); coverage 18 min. For the 34 files with no times.tsv row
(`S/u27/base_files.txt`: 19 tests_scripts files, 13 `tests/` files at both GC stages, 2 live JS files), the lead runs one
timed sweep at `0c0ad52` before launch; lanes run no before-runs.

| CI job (timeout, `ci.yml`) | what U27 adds | estimate |
|---|---|---|
| `unit-tests`, `unit-tests-gc-threshold` (45 min, `:462`, `:500`; the job comment `:454-455` "a ~17-minute warm run") | six `scenarios[<device>]` jobs at the job's GC stage, dispatched first (T, A.U27.38); tests_scripts tier +~2 min (the stripped-image boots ~60-70 s, the reproducibility runs ~15 s, the rest ~20 s), beside the MicroPython loop | ~17 → ~24-26 min, plus one hung file's 12-min budget: ~38 of 45 (R-16); the lead checks the first CI run; U28's M.TOOL.019 re-measures |
| `unit-tests-coverage` (45 min, `:529`; "14m01s/16m56s") | tier +~2 min; no harness or lwIP jobs under `--coverage` | ~17 → ~19 min |
| `digital-twin-e2e` (20 min, `:626`) | the archive step (~1 s); OF-162/163/164 shorten Runs 9-11 (−1 to −3 min per leg), OF-165 −10 s per stage, OF-166's flags a few seconds | net ≤ today |
| `lint-and-typecheck` (15 min, `:338`) | the generation step (~15 s), ruff over `build/generated_src`, mypy over exactly `files` plus two single-file checks (+30-60 s) | ~1.5 min |
| `firmware-build-verify` (15 min, `:662`) | the image report (one `arm-none-eabi-nm`), the python check | +<1 s |
| web jobs | the probe call per twin start (~0.3 s), eight headers | +<1 s |

Every tests_scripts, `tests/` or JS file a lane adds or grows is timed alone at the stage(s) it runs; above 10 s, or 10 %
over its base and above 10 s, it is made efficient, never bounded (R-17); expected new files over 10 s:
`test_stripped_image_boots.py` (six compiled boots; `test_digital_twin_generated_boot.py`'s 59.55 s is the comparable).

## 10. Per-step table

Every change in work-order order: step (`g` = co-landing group), change, lane, verdict, the U27 part, and the
seen-failing-first check without hardware (or the proof for a verify row) with its round. Lanes read their rows in their
packet's index; the full texts are in the packets.

| step | change | lane | verdict | U27 part | seen failing first (no hardware) / round |
|---|---|---|---|---|---|
| 1 | GEN.009 | B | apply | U27 stage only: `TestOverrides` (sorted test_overrides) in the emitted build info when generated with test overrides | test_buildgen_generate.py: a device generated with test_overrides=("tick_offset_test",) emits TestOverrides, the default none (red: no parameter) |
| 2 | GEN.026 | B | apply | A.U27.37: `device_max_connections_by_name(device)` beside the path form | test_buildgen_validate.py: by-name equals the path form for every DEVICE_NAMES device (M.TSC.058, red: no name) |
| 3 | HW_BENCH.010 | lead | lead | stage 2: `configured_max_connections()` body -> `device_max_connections_by_name(device or bench_device())` (one line, after B's helper, R-6) | pure migration: test_bench_harness_helpers.py:138-143 green |
| 4 | HW_BENCH.089 | T | verify | U27 stage (the image check) landed at U26: `--rollover-image` (`tests_hardware/bench/test_ticks_ms_rollover.py:47`), record overrides (`:52`); T's runner passes the option | collect-only names it; the runner case in test_hardware_runners.py passes `--rollover-image` / R6 [H63] |
| 5 | SCR.011 | B | apply | new `scripts/_require_venv.sh` `require_project_venv` | new test_require_venv_sh.py (red: no file) |
| 6 | SCR.020 | B | apply | shell convention, `require_device` per device, OF-141's start-of-run wipe of the `--stage-only` root | test_build_device_websites_sh.py: unknown device exits 2 listing valid ones; a stale `<root>/gone/` removed (red); test_shell_conventions.py line |
| 7 | SCR.029 | T | apply | resolver through `setup_toolchain.py board`, header, `--help`; `uv_sync_retried.sh` is U28's (not written) | new test_mpremote_connect_sh.py (red: ttyACM0 default) |
| 8 | DOCS.056 | X | x | README mpremote section: the resolver sentence (A.U27.13) | test_citations.py, test_readme_reference.py |
| 9 | SCR.030 | T | apply | floor through `--marker-floor`, names, header | test_require_clean_hardware_run_sh.py -m cases (red: caller -m replaces); test_hardware_runners.py / R1 [H73] |
| 10 | SCR.004 | T | verify | the record already writes `markexpr` (`scripts/_pytest_run_record.py:115`), which carries the floored expression once the wrapper passes it | the wrapper case reads it from the canned record |
| 11 | SCR.033 | T | apply | help text and `--no-sync` held (U26); A.U27.37: the manual path imports harness from a fresh interpreter | new case: `python tests_hardware/manual/__main__.py --list` exits 0 from a fresh interpreter (guard; bite: drop harness's repo-root insert in a scratch copy) / R1 [H73] |
| 12 | SCR.038 | T | apply | trap first (status file and pidfile after `trap _cleanup EXIT`), texts (A.U27.14) | test_test_sh.py: no `mktemp` above the trap (red at `scripts/test.sh` today) |
| 13 | SCR.047 | S | apply | landed at U25: helpers from `_twin_process.py`, fail-closed log (`scripts/_twin_process.py:209`); U27: types (A.U27.27); the ceiling call is the lead's (A.U27.37, R-6) | host mypy cold with disallow_any_explicit; test_digital_twin_ci_suite_errcount.py:443, :595 green |
| 14 | SCR.073 | T | apply | A.U27.33 only (convention); the Xvfb/download changes are U28's | test_shell_conventions.py line for the installer (red where it fails) |
| 15 | SPEC.079 | X | x | E.3.1 (4): 'once per test file' (A.U27.14) | test_citations.py |
| 16 | SPEC.129 | X | x | I.4(e) (2): a missing, unreadable or empty log fails the twin gate (landed at U25; text) | test_citations.py |
| 17 | SRC_CORE.071 | U | verify | `_RequestLike` stays (imported by `src/asy_webserver_service.py`); U27's removal is step 19 | grep `_RequestLike` in src/ |
| 18 | SPEC.018 | X | x | A.5: no `parse_cmd_request` | test_citations.py |
| 19 | SRC_CORE.073 | U | apply | `parse_cmd_request()` and codes 2/3 go; `_STANDARD_CODES` the seven codes | test_asy_api_response.py every-standard-code case over (0, 1, 400, 404, 405, 413, 500) (red: 2/3 present) |
| 20 | SPEC.056 | X | x | C.5.3 without 2/3 | test_citations.py |
| 21 | SRC_SENS.030 | U | apply | the `_TicksMs` trigger comment (`src/asy_notification_service.py:28`) | comment-cap gate green; host and main mypy |
| 22 | SCR.027 | B | apply | `derive_stub_pins()`, exact pins from `[stubs]`, repairs that fail on a moved tree | test_typecheck_sh.py pin and repair cases (M.TSC.221, red) |
| 23 | SPEC.027 | X | x | B.3 (2): the `[stubs]` key | test_citations.py |
| 24 | SRC_SENS.042 | U | apply | `:180` comment gains 'Removal trigger: SPECIFICATION.md B.15' | comment-cap gate |
| 25 | SRC_SENS.048 | U | apply | the const-tuple comment's trigger | comment-cap gate |
| 26 | SRC_SENS.062 | U | verify | no stub workaround comment in `src/asy_sgp40_driver.py` (grep `Timer()`/`const(`/`_mpy_shed`: none) | grep |
| 27 | SRC_SENS.073 | U | apply | `:256` Timer() comment's trigger | comment-cap gate |
| 28 | SRC_SENS.086 | U | apply | the const-tuple comment's trigger | comment-cap gate |
| 29 | TEST_UNIT.003 | U | apply | codes 2/3 out; the override case on 404 | the file red on today's catalog |
| 30 | TEST_UNIT.006 | U | apply | `parse_cmd_request` section and `_FakeRequest` go | grep `parse_cmd_request` in tests/ and src/ empty |
| 31g | TEST_UNIT.111 | U | apply | U27 rules only: `# ====` -> `# ----` (`tests/test_asy_ntp_client.py:2535, :2539`) | the no-`=`-rule case of the cap gate (red) |
| 31g | TEST_UNIT.118 | U | apply | U27 rules only (`tests/test_asy_scd30_driver.py:753, :756`) | as above |
| 31g | TEST_UNIT.220 | U | apply | U27 rules only (`tests/test_asy_wifi_service.py:3887-4025`, four lines) | as above |
| 31g | TSC.065 | U | apply | tag line only exempt, PEP 723 inside its block, `-` rules only, header presence, `_REVIEW_ENFORCED`, the U28 pending set; the length rule per R-2 | new cases red: `src/asy_scd30_driver.py:172` (7 lines with three tags), the 22 `=` rule lines, the 24 + 8 + 1 headerless files |
| 32 | GEN.060 | U | apply | the `<!-- -->` header after the doctype (U27 part; U23 landed the rest) | header-presence case red on `html/index.html` |
| 33 | TEST_HELP.002 | U | verify | docstring present (`tests/microtest.py:1`); OF-155's drain is U's own row | header-presence case green |
| 34 | TEST_HELP.003 | U | verify | docstring present (`tests/_threshold_runner.py:1`) | header-presence case green |
| 35 | TEST_HELP.004 | U | verify | docstring present (`tests/_coverage_runner.py:1`) | header-presence case green |
| 36 | TEST_HELP.010 | U | verify | header names rp2's zero-argument Timer() and B.15 (`tests/machine.py:1-3`, landed U24) | header-presence case green |
| 37 | TEST_HELP.028 | U | apply | `#` header -> module docstring | header-presence case red on `tests/_boot_contiguity_probe.py` |
| 38 | TEST_UNIT.153 | U | apply | U27 dividers only: the 14 `=` rule lines of `tests/test_asy_uart_comm.py` | the no-`=`-rule case (red) |
| 39 | TEST_UNIT.197 | U | apply | rename `..._handled_like_the_legacy_parse_cmd_request_path` -> `..._answers_code_1` | grep `parse_cmd_request` empty |
| 40 | TEST_UNIT.332 | U | apply | the DeflateIO trigger comment (`tests/test_website_build_integration.py:52`) | comment-cap gate |
| 41 | TEST_UNIT.334 | U | apply | a <= 3-line docstring in each of the 23 headerless test files | header-presence case red on each |
| 42 | TOOL.003 | U | u28 | ci.yml's header is U28's: U lists it in the gate's pending set | the pending-set case |
| 43 | TOOL.034 | lead | lead | `pythonpath = ["."]` with its comment, beside the conftest insert's removal (M.TSC.014), at W1 (R-6) | tests_scripts collect and run with the insert gone |
| 44 | TOOL.047 | B | apply | `StubPins` in the typed versions table | test_setup_toolchain_env.py: a versions.toml without `[stubs]` raises SetupError naming the table (red) |
| 45 | TOOL.077 | B | apply | `[stubs] board/stdlib` at the installed post-releases (`S/shared/typings/*.dist-info`) | test_typecheck_sh.py pin case |
| 46 | TOOL.059 | B | apply | comment only (the retry landed U21) | comment-cap gate |
| 47 | TOOL.074 | B | apply | header: the hand pins, derivations, whose call | comment-cap gate (TOML review-enforced) |
| 48 | TOOL.078 | lead | verify | no dependency change in U27: the lock is not edited; the lead's `uv lock --check` and pin check at W1 | uv lock --check |
| 49 | TSC.002 | lead | verify | the 25 named files are clean at 0c0ad52 (none in `_NOT_YET_CLEANED`, `tests_scripts/test_no_variant_literals.py:33-46`); new U27 test files are born on DEVICE_NAMES | test_no_variant_literals.py green |
| 50 | TSC.014 | lead | lead | the repo-root insert and its comment go (`tests_scripts/conftest.py:22`), with M.TOOL.034, at W1 (R-6) | as M.TOOL.034 |
| 51 | TSC.021 | T | verify | header and the device loop landed U26; `:138-143` holds over the lead's one-line change | file green |
| 52 | TSC.035 | B | apply | `WEBSITE_WORK_DIR` in tmp_path, the valid-devices message | the unknown-device message assertion (red) |
| 53 | TSC.058 | B | apply | the by-name case | red: no name |
| 54 | TSC.099 | lead | lead | rows a U27 file no longer needs leave `_PENDING` (print, match, delete) | test_import_placement.py green |
| 55 | TSC.136 | T | apply | U27 part: the step-summary rule over every file test.sh sources or runs for its summary | guard (passes at once): bite = `GITHUB_STEP_SUMMARY` planted in a scratch copy of a sourced helper |
| 56 | SCR.001 | T | verify | no `GITHUB_STEP_SUMMARY` (`tests_scripts/test_summary_block.py:360-362`) | grep |
| 57 | SCR.002 | T | verify | as M.SCR.001 | grep |
| 58 | SCR.005 | T | verify | end-state names landed U26; the floored `-m` reaches it through the record's markexpr | test_hardware_verdict.py green |
| 59 | SCR.024 | B | apply | header, `require_python311`, `require_project_venv` | test_lint_sh.py help/argument cases; test_require_venv_sh.py |
| 60 | SCR.034 | T | apply | `--marker-floor`, the one combined `-m`, header | test_require_clean_hardware_run_sh.py (M.TSC.122, red) / R1 [H73] |
| 61 | SCR.032 | T | apply | header naming the rollover runner, `--marker-floor "soak_duration"` | test_hardware_runners.py soak block and -m case / R5 (U26's soak round) |
| 62 | SCR.074 | T | apply | new `scripts/run_bench_rollover_test.sh`: builds the tick-offset image (`build_firmware.py --tick-offset-test`, B), runs only `multi_day_rollover` through the wrapper with `--rollover-image` | test_hardware_runners.py rollover case (red: no file); test_tool_help.py TOOLS entry / R6 [H63] |
| 63 | TSC.122 | T | apply | the -m narrowing cases | red at the wrapper today |
| 64 | TSC.197 | T | verify | cases landed U26 (`tests_scripts/test_hardware_verdict.py:103`, `:140-143`); A.U26.56's permanent-skip entry stays until the phase-C attempt | file green / R1 [H61] |
| 65 | TSC.204 | T | apply | new file | red: no resolver call |
| 66 | TSC.210 | B | apply | new file | red: no file |
| 67 | TSC.213 | T | apply | T1: new test_shell_conventions.py over every scripts/*.sh; A.U24.68's runner cases | red at <API> on each lane's scripts: their seen-failing lines |
| 68 | TWIN.002 | U | verify | header (`digital_twin/_fault_injection.py:1`) passes the cap without the length rule | cap gate |
| 69 | TWIN.010 | U | verify | as M.TWIN.002 | cap gate |
| 70 | TWIN.011 | U | verify | as M.TWIN.002 | cap gate |
| 71 | TWIN.012 | U | verify | as M.TWIN.002 | cap gate |
| 72 | TWIN.013 | U | verify | as M.TWIN.002 | cap gate |
| 73 | TWIN.014 | U | verify | as M.TWIN.002 | cap gate |
| 74 | TWIN.016 | U | verify | as M.TWIN.002 | cap gate |
| 75 | TWIN.017 | U | verify | as M.TWIN.002 (`digital_twin/unixport/_unix_port_udp_addr_shim.py`) | cap gate |
| 76 | SCR.009 | T | apply | T1: new `scripts/micropypath.toml` (unit, twin) | test_twin_never_needs_tests_on_its_path.py layout case (red: no file) |
| 77g | GEN.016 | B | verify | catalog landed U20; `buildgen/definitions.py:860` already `raise SystemExit(main())` | test_buildgen_source_agreement.py green |
| 77g | GEN.018 | B | apply | U27 part: `main()` prints a user error as one line with no traceback (A.U27.29) | the CLI case of test_host_cli_exit_idiom.py (new) |
| 77g | GEN.019 | B | apply | U27 part: `test_overrides` through `generate_device()` (with M.GEN.009) | test_buildgen_generate.py case |
| 77g | HW_BENCH.106 | T | verify | idiom landed (`tests_hardware/manual/__main__.py:18-19`); the `--list` case is step 11's | test_host_cli_exit_idiom.py green on it |
| 77g | SCR.007 | T | apply | T1: new `scripts/_devices.sh` | new test_devices_sh.py (red: no file) |
| 77g | SCR.010 | T | apply | T1: new `scripts/_require_python.sh` | new test_require_python.py (red at build_frozen_html.sh: B's line) |
| 77g | SCR.017 | S | apply | the harness takes the port-53 lock through `_port_lock.py` when run alone; header; OF-165, OF-166 | test_digital_twin_scenarios.py: a held 53 lock exits 1 naming the port (red) |
| 77g | SCR.025 | B | apply | generation before ruff, `build/generated_src` in ruff, `grep_guard`, the checker call | test_lint_sh.py guard over a fabricated tree, grep exit 2 fails closed (red) |
| 77g | SCR.026 | B | apply | header, help, venv and Python checks, summary trap | test_typecheck_sh.py help/argument cases |
| 77g | SCR.028 | B | apply | generation, three passes from their configs, two single-file checks | test_lint_type_scopes.py coverage case (red: the two collision files in no run) |
| 77g | SCR.035 | T | apply | header, help, validation texts; no variant literal | test_test_sh.py rejection cases (exit 2); test_no_variant_literals.py row leaves (lead) |
| 77g | SCR.039 | T | apply | site of the first derived device, port-53 lock order | test_test_sh.py site-line case (red: `build_website.sh wozi`) |
| 77g | SCR.040 | T | apply | job runner: retries reported, the memory gate on every attempt's log before it is truncated (REGISTER :740), MICROPYPATH from the file, harness jobs | test_test_sh.py: a timed-out attempt's caught allocation failure is reported though a later attempt passes (red) |
| 77g | SCR.041 | T | apply | one `scenarios[<device>]` job per derived device (A.U27.38), dispatched first, none under --coverage | test_test_sh.py dispatch case (red: no harness job) |
| 77g | SCR.045 | T | apply | harness jobs counted under L2; the step-summary rule kept | test_test_sh.py summary case |
| 77g | SCR.048 | S | apply | per-device logs default (A.U27.16), routes from the API reference (A.U27.32), MICROPYPATH from the file (A.U27.15), the idiom (A.U27.29), the port lock when run alone (A.U27.39) | test_digital_twin_ci_suite_ceiling.py route case (red); test_tool_help.py |
| 77g | SCR.061 | S | apply | archive per device before the run, the probe, convention; harness and CRC16 rerun landed (`scripts/run_digital_twin_ci.sh:126-143`) | new test_run_digital_twin_ci_sh.py (red: no archive) |
| 77g | SCR.062 | S | apply | required device through `require_device`, probe, own site path, port-53 lock | test_shell_conventions.py runner cases (T1, red); new held-lock case |
| 77g | SCR.064 | S | apply | U27 stage only: the shared JS twin frame (probe, MICROPYPATH, port lock); the rest U28 | npm run lint/typecheck; `tests_js/port-lock.test.js`; a node run of the smoke's `--help` |
| 77g | SCR.065 | B | apply | `--no-autostart`, `--tick-offset-test`, the kept work dir, one error contract, no variant literal (`--device-toml` landed U26) | test_build_firmware.py CLI cases (M.TSC.032, red) |
| 77g | SCR.066 | B | apply | `stage_python_modules()` split, generated module through the stripper, sorted manifest | test_build_firmware.py :87 sorted form (red); test_frozen_inputs_reproducible.py |
| 77g | SCR.067 | B | apply | image report into the record, the tick-offset entry, the atomic image-then-record order (REGISTER :742) | test_build_firmware.py image_report() over a stub nm (red); a kill between copy and record leaves no new-image/old-record pair |
| 77g | SCR.068 | B | apply | all or nothing, atomic, pruned, stamp last | test_generate_sensortask_modules.py (M.TSC.158, red) |
| 77g | SCR.069 | B | apply | U27 parts only: docstring (A.U27.28), idiom (A.U27.29), the `coverage` ignore if the host pass now resolves it (A.U27.27); the rest U28 | test_host_cli_exit_idiom.py; host mypy cold (warn_unused_ignores) |
| 77g | SCR.070 | B | apply | line-preserving stripper, `StripError` | test_strip_type_checking.py (M.TSC.130, red: compound/else cases) |
| 77g | SCR.071 | B | apply | work dir, checks, `require_device`, `require_python311` | test_build_website_sh.py (M.TSC.035); test_shell_conventions.py |
| 77g | SCR.072 | B | apply | quoted inputs, `gzip -n`, the pinned clock, the 254-char check, kept work dir | test_build_frozen_html_sh.py byte-identical case (red) |
| 77g | TOOL.011 | B | apply | U27 stage of ci.yml's lint-and-typecheck: the generation step, ruff over `build/generated_src`, mypy over exactly `files` | test_lint_type_scopes.py CI-parity case (red) |
| 77g | TOOL.018 | B | apply | U27 stage of ci.yml's firmware-build-verify: `source scripts/_require_python.sh && require_python311` before the heredoc | actionlint/zizmor clean; test_require_python.py covers the helper |
| 77g | TOOL.026 | B | apply | the scope comment | comment-cap (review-enforced TOML) |
| 77g | TOOL.032 | B | apply | `files` gains build/generated_src, `ignore-without-code`, exclude comments, the shim/stub paths | test_lint_type_scopes.py (red) |
| 77g | TOOL.035 | B | apply | OverrideError(Exception), comments, idiom | test_micropython_overrides.py pytest.raises hold; test_host_cli_exit_idiom.py |
| 77g | TOOL.045 | B | apply | SetupError(Exception) | test_setup_toolchain_env.py holds |
| 77g | TOOL.072 | B | apply | the handler into `main()`, the idiom | test_host_cli_exit_idiom.py (red at `toolchain/setup_toolchain.py:1809`) |
| 77g | TOOL.079 | B | apply | U27 stages: `ignore-without-code`, the conftest reason, `mypy_path` gains scripts | test_lint_type_scopes.py |
| 77g | TSC.034 | B | apply | FROZEN_HTML_WORK_DIR, the message, reproducibility, the 254/255 case | red at today's script |
| 77g | TSC.085 | B | apply | `_boot_generated_device(root, device)`, MICROPYPATH from the file | pure migration green; the twin path guard (T1) green on it |
| 77g | TSC.104 | B | apply | new test_lint_type_scopes.py | red at today's configs |
| 77g | TSC.131 | B | apply | new test_stripped_image_boots.py | red: no `stage_python_modules()` |
| 77g | TWIN.075 | B | apply | the twin pass's `files` list, coded ignores | test_lint_type_scopes.py |
| 78 | DOCS.048 | X | x | README build: work dirs, `--no-autostart` | test_readme_reference.py, test_citations.py |
| 79 | DOCS.049 | X | x | README tests per level: the floor, the rollover runner line | as above |
| 80 | DOCS.050 | X | x | README everyday recipes: the venv sentence, the port-53 note | as above |
| 81 | DOCS.053 | X | x | README code quality: the venv check | as above |
| 82 | DOCS.094 | X | x | CLAUDE.md code-quality tooling: venv, generated scope, exclusions | test_decision_vocabulary.py, test_citations.py |
| 83 | DOCS.103 | X | x | CLAUDE.md mypy bullet: ignore-without-code; the guard fails when it cannot search | as above |
| 84 | HW_BENCH.038 | T | verify | TwinBoard launch (`tests_hardware/conformance.py:74-76`); its binary comes through `twin_board.unix_port_binary()`, which T moves onto the probe | test_twin_board.py green / R1 [H25, H26] (U26's) |
| 85 | DOCS.047 | X | x | README install: the probe note | as above |
| 86 | DOCS.097 | X | x | CLAUDE.md coverage bullet: every runner asks through `_unix_port.sh` | as above |
| 87 | HW_BENCH.091 | T | apply | stage 2: binary through `scripts/_unix_port.sh unix_port_bin standard`, the twin layout from `micropypath.toml` (R-10's reverse) | test_twin_board.py; the T1 path guard red on `tests_hardware/twin_board.py:16` until then |
| 88 | HW_BENCH.126 | X | x | tests_hardware/README.md: resolver, the floor, the rollover runner, the port-53 note | test_citations.py |
| 89 | HW_DEV.001 | B | verify | BENCH typing landed U26; CI's mypy paths keep device_scripts (A.U27.25 is step 77's) | test_lint_type_scopes.py / R1 [H73] (U26's) |
| 90 | HW_DEV.003 | B | verify | `_shared/` landed U26 (`tests_hardware/device_scripts/_shared/__init__.py`); the scope test sees it | test_lint_type_scopes.py |
| 91 | HW_DEV.116 | B | verify | the rendered import (`heap_headroom_after_full_system_build.py:10`); typecheck.sh's stale comment is step 77's | grep / R1 [H44] (U26's) |
| 92 | SCR.003 | T | apply | API landed U7; the idiom (A.U27.29) | test_archive_evidence.py green; test_host_cli_exit_idiom.py |
| 93 | SCR.006 | T | apply | `derived_devices` replaces the inline loop (`scripts/_run_lower_levels.sh:38-41`) | test_hardware_runners.py device-loop case holds; test_shell_conventions.py |
| 94 | SCR.008 | T | apply | T1: new `scripts/_unix_port.sh` (lwip flavour, record condition, OF-124's input hash, OF-126's shared lock) | new test_unix_port_sh.py (red: no file) |
| 95 | SCR.012 | T | verify | landed U24 (`scripts/_port_lock.sh`); the three launchers take it in S | test_port_lock.py green |
| 96 | SCR.013 | T | apply | T1: new `scripts/_port_lock.py` | test_port_lock.py CPython-reader cases (red) |
| 97 | SCR.015 | B | apply | new `scripts/_check_gc_collect_sites.py` | test_gc_collect_sites.py alias cases (red) |
| 98 | DOCS.089 | X | x | CLAUDE.md memory rule: the checker | as above |
| 99 | SCR.016 | S | apply | TwinRun landed U25 (`scripts/_twin_process.py:58`); U27: the twin layout from `micropypath.toml` | the T1 path guard red on `scripts/_twin_process.py:24` |
| 100 | SCR.019 | B | apply | stager CLI landed U23; the idiom (A.U27.29); its output dir is the work dir's (A.U27.35) | test_stage_website.py green; test_host_cli_exit_idiom.py |
| 101 | SCR.031 | T | apply | two steps with the floor | test_hardware_runners.py, test_require_clean_hardware_run_sh.py / R1 [H73] |
| 102 | SCR.036 | T | apply | flavours through `_unix_port.sh`, one MICROPYPATH | test_test_sh.py flavour cases retargeted (red) |
| 103 | SCR.037 | T | apply | comment only (the call unchanged); the U36 wording waits | comment-cap gate |
| 104 | SCR.044 | T | verify | renders and archive landed U24/U7; U27's part is step 55's pin | test_test_sh.py coverage cases green |
| 105 | SCR.046 | S | apply | docstring, JSON types (A.U27.27), comments without device names (A.U27.08) | host mypy cold with disallow_any_explicit; test_no_variant_literals.py row leaves (lead) |
| 106 | SCR.054 | S | apply | A.U27.08 only: the device-naming comments of Runs 5b/5c | test_no_variant_literals.py |
| 107 | SCR.057 | S | apply | U27 stage: one attempt, route-derived soak set, generic comment; offsets and calibration U35 | test_digital_twin_ci_suite_soak.py one-attempt case (M.TSC.084, red) |
| 108 | SCR.058 | S | apply | every GET route at the ceiling, the tagged slot wait | test_digital_twin_ci_suite_ceiling.py (M.TSC.083, red) |
| 109 | SPEC.034 | X | x | B.10.1 (c) mypy, (d) | test_citations.py |
| 110 | SPEC.043 | X | x | B.15 the three passes, the workaround list | as above |
| 111 | DOCS.105 | X | x | CLAUDE.md stub bullets | as above |
| 112 | SPEC.076 | X | x | E.1: shipped form, twin runner archive | as above |
| 113 | SPEC.078 | X | x | E.3 (1)-(2) | as above |
| 114 | SPEC.081 | X | x | E.5 (3) probe | as above |
| 115 | SPEC.026 | X | x | B.2 (3) | as above |
| 116 | SPEC.085 | X | x | E.9 (2)-(3) | as above |
| 117 | SPEC.104 | X | x | F.5.5 (1)-(2) | as above |
| 118 | SPEC.130 | X | x | I.4(f.1) (2) the checker | as above |
| 119 | SPEC.147 | X | x | L.4 (7) python check | as above |
| 120 | SPEC.148 | X | x | L.5 (5)-(6) classes and idiom | as above |
| 121 | SPEC.159 | X | x | B.4 shell conventions | as above |
| 122 | SPEC.035 | X | x | B.11: stubs, stripper, shipped form, frozen site, report, manifest, work dirs, --no-autostart | as above |
| 123 | TEST_HELP.033 | S | verify | retired at U25 (`tests/_webserver_concurrency_scenarios.py` absent); its scenarios run in the harness | git ls-tree |
| 124 | TEST_UNIT.295 | U | apply | one product fixture on the real service and Microdot | the rewired file red on the old `/net/cmd` routes |
| 125 | TEST_UNIT.296 | U | apply | sparse /networking bodies and refusals | red: envelope tests |
| 126 | TEST_UNIT.297 | U | apply | 404/405/500 on the real app | red |
| 127 | TEST_UNIT.298 | U | apply | sensor PUTs on product routes | red |
| 128 | TEST_UNIT.299 | U | apply | time settings over /networking and /system | red |
| 129 | TOOL.001 | lead | u28 | no U27 stage: the composite action and its build-if-missing steps are U28's | - |
| 130 | TOOL.007 | lead | u28 | U28's (its build step keeps its own path, still valid) | - |
| 131 | TOOL.010 | lead | u28 | U28's (one smoke per job: the new lock is never contended) | - |
| 132 | TOOL.017 | lead | u28 | U28's (the artifact path `digital_twin_ci_logs/` covers the per-device dir) | - |
| 133 | TOOL.019 | lead | u28 | U28's re-measure; U27's added time is plan §9's estimate | - |
| 134 | TOOL.023 | B | apply | the Python floor comment names `_require_python.sh` | comment-cap (review-enforced) |
| 135 | TOOL.030 | lead | lead | per-file entries for U27's new and renamed files: B writes its own, T, U and S relay theirs, the lead lands them at W1 (R-7); the restructure is U28's | ruff over the eight scopes |
| 136 | TOOL.033 | lead | lead | the setter override and its comment go at W1, after U's rewrite (A.U27.07 (7), R-6) | main mypy pass cold |
| 137 | TOOL.080 | B | verify | the override landed U21 (`toolchain/setup_toolchain.py:646`, `:658-686`); U27's sides are M.SCR.065/.067/.074, M.GEN.009 | test_micropython_overrides.py green |
| 138 | SPEC.162 | X | x | B.14.5 stage 2: the build information names the override | test_citations.py |
| 139 | SPEC.082 | X | x | E.6 (4) -m; (7) the rollover runner | as above |
| 140 | SPEC.150 | X | x | L.7 (4.1) the build date is a build input | as above |
| 141 | TSC.008 | B | apply | U27 part: the CLI exit-idiom cases | test_host_cli_exit_idiom.py (new) red at the five `sys.exit(main())` sites |
| 142 | TSC.015 | T | apply | `micropython_bin` through `_unix_port.sh check standard`, fail on mismatch | red: hand-built path |
| 143 | TSC.016 | B | verify | no edit: B's single-file host run checks `tests_scripts/conftest.py` | typecheck.sh's single-file run |
| 144 | TSC.029 | B | apply | BuildError/BuildInternalError expectations | red at the RuntimeError conversions (`scripts/build_firmware.py:61-90`) |
| 145 | TSC.030 | B | apply | sorted freeze form | red at `:87` |
| 146 | TSC.031 | B | apply | the staging split | red: no `stage_python_modules()` |
| 147 | TSC.032 | B | apply | CLI cases: no-autostart, lock, record, work dir | red |
| 148 | TSC.033 | B | apply | the report on the slow build; the fast stub-nm case | the fast case red; the slow one runs in CI's firmware-build-verify |
| 149 | TSC.045 | B | verify | boot-entry pins landed U20/U24; U27's idiom part is in test_host_cli_exit_idiom.py | file green |
| 150 | TSC.048 | B | verify | landed U20/U24; the stripper check follows M.SCR.070 | file green after the stripper |
| 151 | TSC.070 | T | apply | settrace through the probe, MICROPYPATH from the file | red: hand-built path |
| 152 | TSC.082 | T | apply | MICROPYPATH from the file, the parity reads test.sh's source of it | red at `tests_scripts/test_digital_twin_boot_contiguity.py` literal |
| 153 | TSC.083 | S | apply | fixture routes from a tmp reference | red |
| 154 | TSC.084 | S | apply | the one-attempt case | red |
| 155 | TSC.093 | T | apply | the binary through the probe | red: own lookup |
| 156 | TSC.094 | B | apply | new test_frozen_inputs_reproducible.py | red: no `stage_python_modules()` |
| 157 | TSC.095 | B | apply | alias cases through the checker | red |
| 158 | TSC.130 | B | apply | every form, line-preserving | red at `tests_scripts/test_strip_type_checking.py:50-62` |
| 159 | TSC.134 | T | apply | rejection contract (exit 2), tagged timeouts | red where today's exit is 1 |
| 160 | TSC.135 | T | apply | flavours, retries, fail-closed log, per-device and harness jobs | red |
| 161 | TSC.157 | B | apply | grep_guard cases; gc cases leave for the checker | red |
| 162 | TSC.158 | B | apply | all or nothing, pruned, stamped | red |
| 163 | TSC.175 | T | apply | T1: the docstring names `scripts/_devices.sh` (functions landed U24/U26) | comment-cap gate |
| 164 | TSC.177 | T | verify | landed U7 (`tests_scripts/test_archive_evidence.py`) | file green |
| 165 | TSC.180 | T | verify | the tick-offset case landed U26 (`tests_scripts/test_board_image_fixture.py:106`) | file green |
| 166 | TSC.181 | B | apply | unknown device exits 2, the stage-only wipe | red |
| 167 | TSC.189 | T | apply | T1: new test_devices_sh.py | red: no file |
| 168 | TSC.192 | S | apply | landed U25 (`tests_scripts/test_digital_twin_scenarios.py:147`); U27: the held-lock case | red |
| 169 | TSC.196 | T | apply | rollover runner, floors | red |
| 170 | TSC.201 | B | apply | the stamp path equals the generator's last-written stamp | red if the stamp moves; else guard with a bite |
| 171 | TSC.206 | T | apply | T1: the CPython reader honours the shell contract | red: no `_port_lock.py` |
| 172 | TSC.209 | T | apply | T1: new test_require_python.py | red at `scripts/build_frozen_html.sh` (B's line) |
| 173 | TSC.211 | S | apply | new test_run_digital_twin_ci_sh.py | red |
| 174 | TSC.221 | B | apply | pins, repairs, summary | red |
| 175 | TSC.222 | T | apply | T1: new test_unix_port_sh.py | red |
| 176 | TWIN.020 | U | verify | header passes without the length rule | cap gate |
| 177 | TWIN.031 | U | verify | as M.TWIN.020 | cap gate |
| 178 | TWIN.036 | U | verify | as M.TWIN.020 | cap gate |
| 179 | TWIN.040 | U | verify | as M.TWIN.020 | cap gate |
| 180 | TWIN.042 | U | verify | as M.TWIN.020 | cap gate |
| 181 | TWIN.044 | U | verify | as M.TWIN.020 | cap gate |
| 182 | TWIN.047 | U | verify | as M.TWIN.020 | cap gate |
| 183 | TWIN.050 | S | verify | A.U27.01's runner half landed U25 (one shutdown line, `scripts/_twin_process.py:266` parses it); S's OF-164/165/166 lines edit the same file | test_digital_twin_run_generic_integration.py green |
| 184 | PROC.019 | lead | u28 | U28's file; `build/` already ignored (the work dirs need no line); the `:40` comment co-lands with A.U28.33 | - |
| 185 | TSC.165 | S | verify | the missing/unreadable and empty-log cases landed U25 (`tests_scripts/test_digital_twin_ci_suite_errcount.py:443`, `:595`) | file green |
| 186 | TWIN.057 | U | verify | as M.TWIN.020 | cap gate |
| 187 | TWIN.063 | X | x | digital_twin/README.md: paths from the layout file | test_citations.py |
| 188 | TWIN.064 | X | x | digital_twin/README.md: the per-device archive, one Run 11 attempt, every GET route | as above |
| 189 | TWIN.136 | U | verify | the file went at U25; its DeflateIO comment lives only in `tests/test_website_build_integration.py` (step 40) | git ls-tree |
| 190 | WEB.051 | U | apply | header | header-presence case red |
| 191 | WEB.052 | U | apply | header | red |
| 192 | WEB.053 | U | apply | header | red |
| 193 | WEB.054 | U | apply | header | red |
| 194 | WEB.058 | U | apply | header | red |
| 195 | WEB.059 | U | apply | headers of app/main/nav .test.js | red |
| 196 | WEB.060 | U | verify | header present (`tests_js/_put_field_cases.js:1`) | header-presence case green |
| 197 | WEB.070 | S | apply | U27 line only: `tests_js/_micropypath.js` in the Node-context list (the rest U36/U28) | npm run lint |
| 198 | WEB.073 | S | apply | U27 stage: `_micropypath.js` in tsconfig.node.json's files | npm run typecheck |
| 199 | WEB.079 | S | apply | new `tests_js/_micropypath.js` | a vitest case reading `twin` (red: no file) |
| 200 | WEB.061 | S | apply | probe, MICROPYPATH from the file, port lock, no `existsSync` (`tests_js/_twin_process.js:95`), OF-147 | live-backend.test.js under unshare (wall-time bound) |
| 201 | WEB.062 | S | apply | as M.WEB.061 for the matrix | live-backend-put-matrix.test.js |
| 202 | WEB.063 | S | verify | per device, fail-never-skip landed U25 (`tests_js/live-backend.test.js:2`) | files green after the frame change |
| 203 | WEB.082 | S | apply | the shared frame landed U24; U27 edits it (M.WEB.061) | as M.WEB.061 |
| 204 | TSC.150 | T | apply | T1: every twin launch site reads `micropypath.toml`; the layout case | red at <API> on each lane's launch sites |
