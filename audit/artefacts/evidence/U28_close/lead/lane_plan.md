# U28 (CI: the workflow, the composite action, the zizmor policy, the job graph and the config files its clauses name) lane plan (sites at `b1fecfb`)

**One pass (agent, 2026-10-19)**: plan, cut and briefs from the audit tree at `b1fecfb` (U27's pushed head, CI 45/45 green,
run 38777834467; the U28 base, no relocation), read only through git. Every site below is `file:line` at `b1fecfb` with its
quoted text; the M and A texts in the packets carry the A-L HEAD's line numbers, so lanes locate by quoted text. Rulings:
`briefs/rulings.md` (R-1..R-23). Placeholders kept literal: `<API>` (`audit/u28-api`: R's R1 commit on `b1fecfb`), `<W1>`
(`audit/u28-w1`: C, W, R, P merged plus the lead step), `<W2>` (`<W1>` plus X and the datasheet move). Binding for every
agent: `S/CHECKLIST.md`, `S/u21/CONCURRENCY.md` (rule 13 above all: effort is the measure).

## 0. Sources and tools

Sources at `b1fecfb`: `audit/actions/U28.md` (A.U28.01-.43; Ledger, Register fixes, Open points, Closing inventory),
`audit/order/work_order.json` (U28), the M entries its steps name, `audit/REGISTER.md` rows naming U28 (`:54`, `:186`, `:656`,
`:666`, `:671`, `:681`, `:682`, `:718`), `audit/sweeps/open_findings.md` (23 rows target U28; OF-70, OF-183, OF-184 name a U28
part with target C), U27's close record `audit/sweeps/scan_runs/20261015_U27_close.md` (its "Process" lessons, the CI it
defers here) and U27's review rows (REGISTER `:672-690`). Models: `S/u27/lane_plan.md`, `gaps.md`, `pk/`, `briefs/`; command
forms `S/u24/briefs/common.md` "Runs" (`:49-80`) and "Before every commit" (`:93-103`), cited, never copied.

Tools (`S/u28/tools/`, each `python3 -I <tool>`): `root_b1fecfb/` (git archive of `audit/` parts, never evidence),
`tree/` (git archive of the eight scopes and the config files, for counting only); `step_packet.py` (the audit tool on that
copy) → `pk/U28_steps.md` (650 KB); `steps.py` → `u28_steps.json`, `all_acts.txt`; `index.py` → `changes_index.txt`;
`judged.py` (per change: lane, verdict, U28 part, check, round) → `step_table.md`; `routed.py` (open findings, register rows
per lane); `ast_count.py` (the host-lint estimate of R-4/R-5, never ruff's verdict); `noqa_tables.py` → `supp_<L>.md` (every
suppression site the sweep touches, with its end form); `lanes.py` (the sets, `../files_<L>.txt`, disjointness, sizes);
`extract.py` → `pk/packet_lane<L>.md`; `show.py <ID>` prints any M entry or action.

## 1. Counted against the work order

- **Steps**: the work order's 156 changes in 147 numbered steps (96 explicit + 60 implicit; groups: step 2 of 7, step 61 of 4)
  are all placed (`judged.py` asserts none missing): 115 to write (88 code/test `apply`: C 32, R 23, P 17, W 16; 24 docs `x`;
  3 `lead`) and 41 `verify` (C 10, R 12, P 14, W 4, X 1). Per lane (changes to write / steps): C 32/29, W 16/16, R 23/21,
  P 17/17, X 24/24, lead 3/3.
- **Actions**: 56 = the work order's `actions` field = the union of the steps' `carries` (43 A.U28, A.SDEP.19, A.U0.23,
  A.U1.15, A.U11.09, A.U17.19, A.U23.34, A.U24.72, A.U26.75, A.U27.08, A.U27.10, A.U6.11, A.U6.12, A.U8.14); each is in at
  least one packet. A.U28.36 (budgets) and A.U28.37/.38 (docs) land through the lead's CI step and X.
- **Files**: 113 in the work order (17 absent at `b1fecfb`: born here, renamed or gone, gaps.md §4); the lane sets hold 197
  entries (C 27, W 20, R 73, P 64, lead 7, X 6), the excess the suppression sweep and the host fixes (gaps.md §3).
- **Scoped tests**: 200. **Full gate**: its seven items (lint; the three mypy passes; `scripts/test.sh` at -1 with the
  tests_scripts tier; at 32768; `scripts/run_digital_twin_ci.sh <device>` for every device; the web tier; `--coverage` and
  `npm run test:coverage`). **Hardware rounds**: R0 [H57], R1 [H73], R3 [H73] (§7); nothing runs on hardware in U28.
- **Open findings**: the 23 rows targeting U28 are each placed (§6); three moved rows (OF-70, OF-183, OF-184) stay C.

## 2. The cut (R-1): four code lanes, one API stop, then the docs lane

| wave | lane | family | base | changes / steps written | est. lines / files |
|---|---|---|---|---|---|
| 1 | **C** CI and the scripts it runs | `.github/workflows/ci.yml`, both composite actions (`setup-micropython-toolchain`, new `uv-sync`), `.github/zizmor.yml`, `.gitignore`, new `scripts/uv_sync_retried.sh`, the four runners that sync first, `scripts/test.sh` (coverage outputs, OF-204), `_render_coverage.py`, `_unix_port.sh` (OF-191), `typecheck.sh` (OF-125); tests: new `test_ci_workflow.py`, `test_uv_sync_retried_sh.py`; `test_device_tomls.py`, `test_lint_type_scopes.py`, `test_test_sh.py`, the runner, probe and render tests | `b1fecfb` | 32 / 29 | ~1300 (+ the D.15 reorder) / 27 |
| 1 | **W** web and JS config, the smoke, the installers' web steps | `scripts/cross_browser_smoke.mjs`, `_cross_browser_probe.mjs`, `setup_cross_browser_toolchain.sh`, new `preview_server.py`, `tsconfig.json`, `tsconfig.node.json`, new `tsconfig.base.json`, `tests_js/vitest-commands.d.ts`, `vitest.config.js`, `eslint.config.js`, `package.json`, `.htmlvalidate.json`, `toolchain/setup_toolchain.py` (Playwright), `tests_js/_twin_process.js` (only if the smoke needs an export); tests: the probe, installer, preview, html-validate and `test_setup_toolchain_env.py` | `b1fecfb` | 16 / 16 | ~800 / 20 |
| 1 | **R** ruff config and host tooling (R1 = the API) | `pyproject.toml` (the ruff block, the pins), new `test_ruff_exemptions_live.py`, `test_suppression_form.py`, `test_config_paths_resolve.py`, `test_tool_pins.py`; host fixes and noqa homes in `buildgen/`, `scripts/` (not C's or W's), `toolchain/micropython_overrides.py`, `tests_scripts/`, `tests_hardware/` (not `device_scripts/`); OF-28, OF-194, OF-195 | `b1fecfb` | 23 / 21 | ~1300 / 73 |
| 1b | **P** the MicroPython-run suppression sweep | `src/` (B905 noqa, the seven reasons, the trigger lines, PYI046, OF-159), `tests/`, `digital_twin/`, `tests_hardware/device_scripts/` (noqa to central homes, E731, the `_srgb_` rename, list order, E402 reasons), OF-151, the twin cancelled-session case | `<API>` | 17 / 17 | ~400 / 64 |
| 2 | **X** docs from the relay | SPECIFICATION.md, README.md, CLAUDE.md, BACKLOG.md, tests_hardware/README.md, UART_C_PORT_CHANGELOG.md | `<W1>` | 24 / 24 | ~700 / 6 |
| — | **lead** | the shrink-only lists (`test_comment_block_cap.py` `_HEADER_PENDING`, `test_no_variant_literals.py` `_NOT_YET_CLEANED`, the two allow-lists), `uv.lock`, the datasheet move (`datasheets/`, `.gitmodules`), the CI re-measure | merge points, CI | 3 / 3 | ~30 / 7 (+ one-liners) |

Why this shape (rule 13): the ruff block is one file every scope's lint depends on, and the sweep that empties the inline
suppressions cannot be checked before that block exists (RUF100 judges each comment against it): R lands the block first as
R1, P starts on it, and R1's RUF100 lines on P's files are P's seen-failing-first. C and W need nothing from R1 but the list
of their own files' host findings (R-4), so they start at once. C keeps the workflow, the actions, the scripts CI runs and
the tests that read ci.yml together (each ci.yml edit turns one of those tests red); W keeps the web config and the smoke
with the installers' web steps. At most four lanes run at once (C, W, R, P), X alone after `<W1>`.

**Disjointness**: `cd S/u28; for a in C W R P LEAD; do for b in C W R P LEAD; do [[ $a < $b ]] && comm -12 <(sort
files_$a.txt) <(sort files_$b.txt); done; done` prints nothing, and `cat files_{C,W,R,P,LEAD}.txt | sort | uniq -d` prints
nothing (checked by `tools/lanes.py`; rerun after the lead's L0 listing). X starts from `<W1>` after every code lane is done.
A change that turns another file red carries that file into its lane wherever it is the change's own family; the exceptions
are the shrink-only lists (the lead's, R-10), the doc checks (X's) and R1's reds on P's files (P's seen-failing-first).

## 3. Merge points, the API stop and the relay

1. **L0, before launch** (brief_lead.md): the host listing (R-4) rewrites `files_<L>.txt` and the C/W/R briefs' finding
   lines; the base sweep (R-17, `S/u28/base_files.txt`, 15 rows); then C, W, R launch on `b1fecfb`.
2. **`<API>`**: R commits **R1** first (`U28 lane R WIP R1: <summary>`): `pyproject.toml`'s ruff block in its end form (R-3),
   `test_suppression_form.py`, `test_ruff_exemptions_live.py`, and the host fixes R's own files need to be green under it. Its
   hand-back lists every red line by file and owner (P's RUF100 and form lines; C's and W's host findings if any remain). The
   lead merges R1 `--no-ff` onto `b1fecfb` as `audit/u28-api`, rebuilds (`S/u23/rebuild.sh`), runs ruff, the three mypy passes
   cold and R1's files, then launches P on `<API>` and resumes R (`git merge --no-ff <API>` in R's worktree).
3. **`<W1>`**: C, W, R, P finals merged (`audit/u28-w1`); rebuild; the **lead step** (brief_lead.md): `uv lock` + `uv sync` +
   the version check (R-11), the shrink-only rows (R-10), the conditional `--no-respect-gitignore` (R-11), the whole
   `tests_scripts` tier once (U27's lesson), ruff over everything with R's pyproject; then X launches on `<W1>`.
4. **`<W2>`**: X merged; the datasheet move (R-15); then the unit gate (the work order's seven items on `S/gate_v15.sh`'s
   layout as U27 updated it, every device's twin at both GC stages, `uv run pytest --collect-only tests_hardware -q`), the
   whole tier before it (a lead commit runs the whole tier first, U27's lesson); push; CI; the re-measure (R-21).

**The relay**: `S/u28/relay.md`, append-only, one heading per lane. Each lane appends before hand-back: every new or moved
`@tunable` (ID, value, site, basis); each command form or ci.yml line another lane or X reads; its BACKLOG build-environment
line (§8); doc lines owed (SPEC B.10/B.10.1/H.7/H.8/D.6/F.5.5/E.1/L.5/N, README, CLAUDE.md, tests_hardware/README.md,
UART_C_PORT_CHANGELOG.md); facts the lead's CI step must prove (R-20); its after-times. X reads only the relay, its packet
and the tree.

## 4. Sizes and the splits each lane would take (R-2)

Estimate: rewritten or added lines; a new file a typical size for its kind; the sweep one line per site. Big inputs:
`.github/workflows/ci.yml` 693 lines, `scripts/test.sh` 981, `tests_scripts/test_test_sh.py` 2054 (OF-199's reorder moves
most of it), `scripts/cross_browser_smoke.mjs` 672, `toolchain/setup_toolchain.py` 1853, `pyproject.toml` 433.

- C (~1300/27) inside the bar; the split it would take: **C-a** the workflow, the actions, the retried sync and the runners |
  **C-b** test.sh, the renderer, the probe, typecheck.sh, `.gitignore`; they share A.U28.15 (ci.yml's report steps and
  test.sh's renders, both read by `test_test_sh.py`), so the split would put `test_test_sh.py` in C-b and C-a's report-step
  edit would turn it red.
- W (~800/20) inside the bar.
- R (~1300/73) → **R-a** R1 plus `buildgen/`, `scripts/`, `toolchain/`, OF-194/195 | **R-b** the `tests_scripts/` and host
  `tests_hardware/` fixes and noqa homes (mechanical one-line edits); R-b would start on `<API>` like P and pay a lane's fixed
  cost for edits that take minutes each.
- P (~400/64) → **P-a** `src/`, OF-151, OF-159, the twin case, E731, the rename | **P-b** the comment-only sweep over `tests/`,
  `digital_twin/`, `device_scripts/` (R-7: no runs).
- X (~700/6) inside the bar.
Kept whole (rule 13): each split adds a lane's fixed cost (reading, worktree, rebuild, checks) for no gain the merge needs.

## 5. Rulings

`briefs/rulings.md` R-1..R-23, one line each (agent, 2026-10-19), every one on the owner-review list at U28's close. One
point is put to the owner as a question though it has a default (R-5): owner question 1, host-test PT018 and EM/TRY003.

## 6. Open findings, register rows and U27's carries, by lane

Full rows with defaults and checks: each packet's "Open findings and register rows routed to this lane" (`tools/routed.py`).

| row | lane | default (ruling) |
|---|---|---|
| OF-24 one mypy scope | C | CI calls `typecheck.sh` with no arguments (R-13) |
| OF-57 the four Playwright apt steps | C | a tagged step timeout and apt's own retries (as `apt_options()`, `toolchain/setup_toolchain.py:599`) |
| OF-125 the stub install's and `uv run`s' bounds | C | uv's documented timeouts, or `timeout` with a tag (R-14) |
| OF-141 the built-page lint in CI | C | `npm run lint:html:built` in web-lint-and-typecheck (the wipe landed U27) |
| OF-191 the probe bound | C | `timeout -s KILL`, 60 s tagged, `unusable` on timeout (R-12) |
| OF-193 stale binaries | C | CI half: the action builds through `_unix_port.sh ensure standard`; local half to U36 (R-14) |
| OF-199 D.15 order | C | `test_test_sh.py` only (C's last edit to it); the other five keep their units |
| OF-204 six helper starts per run | C | one start, output unchanged, the tail re-timed |
| OF-48 the smoke's apt packages | W | apt's own bounds and retries in the installer; no deb cache |
| OF-140 an unknown attribute passes html-validate | W | enable the installed html-validate's rule for it, else move to U36 with the search recorded |
| OF-28 config-schema derivations | R | re-check each gap; red-first fix or the closing line (R-14) |
| OF-194 an unwritable `--output` | R | one line naming the path, exit 1 |
| OF-195 the slow build under the session lock | R | the opt-in's skip reason names "run it alone" (R-14) |
| OF-151 the ISL29125 sweep | P | only `OSError` passes, as U27's two sweeps |
| OF-159 the CRC drop | P | its own message on the existing entry (R-16) |
| OF-36 | lead | owner's question pending; no code; moved to U30 (R-14) |
| OF-47, OF-149, OF-187, OF-188 | lead | moved to U35 (R-14) |
| OF-160 | lead | moved to U29 (R-14) |
| OF-71, OF-192 | lead | at the CI re-measure (R-21) |
| OF-70, OF-183, OF-184 | — | stay C (R1 and R2 readings, no code) |
| REGISTER `:54` | lead | the unit row at the close |
| REGISTER `:186`, `:682` (U27's U28 parts, the kept `_micropypath.js` deviation) | C, W | in their packets |
| REGISTER `:671` (M.TWIN.102's cancelled-session case) | P | step 104 |
| REGISTER `:656`, `:666`, `:681`, `:718` | — | informational (their rows are placed above or landed) |
| U27's deferred CI result | lead | the close record states run 38770769289 (red, fixed in `b1fecfb`) and 38777834467 (45/45) |
| the real-port guard (brief point 4) | lead | not in U28; new open finding for U35; SPEC E.1's rule via X (R-18) |

## 7. Parked hardware items, per round (nothing runs in U28)

Every round: the owner's go-ahead in its own conversation (CLAUDE.md); the FRAM-backed `errcount` and the raw FRAM saved
before anything writes (the session fixture `fram_evidence_saved`; an isolated-driver script lands on production's first
chunk); the lower levels L0-L2 at both GC stages first; the image record and `board_image`; the standard board state at
start and end; the wear gates deselect (`persistence_write`, `scd30_extra_write`), the flash-cycle, soak, rollover, NeoPixel
and toolchain gates skip in the test body (U26).

| round | item | what runs (U28 code it depends on) | markers and wear gates |
|---|---|---|---|
| R0 | H57 | `uv run toolchain/setup_toolchain.py env --tier bench` on the bench Pi4: its uv must equal `[tool.uv] required-version` (R's pin; uv refuses otherwise), the Playwright step is now fatal under the bench tier (W, A.U28.20); a host check, reads only | none (host only) |
| R1 | H73 | the default bench round: every runner now runs `scripts/uv_sync_retried.sh` first (C); the device scripts and host L3/L4 files whose suppressions U28 moves (P: `uart_driver_read_never_blocks_the_loop.py`, `sgp40_voc_algorithm_quality.py`, `isl29125_mechanism_envelope.py`, `system_command_fram_erase.py`, `uart_comm_hazards.py`, `uart_dma_ring_interrupts_off.py`, `sgp40_sample_cadence.py`, `system_command_hang.py`; R: `bench/test_hotspot_role_reversal.py`, `test_reset_reasons.py`, `test_system_commands_over_rest.py`, `test_uart_link_crc16.py`, `flash/test_system_commands.py`, `conftest.py`'s two fixtures, `twin_board.py`) through their flash/bench tests; OF-159's message on dev's UART link | default run, wear gates off |
| R3 | H73 (gated) | the gated rows among those files with `--allow-persistence-write` (the lead lists them from the lanes' diffs at `<W1>`) | `--allow-persistence-write` |

Untouched and still parked: OF-70 (R2 [H37]), OF-183 (R1, its setup half U28's only if delivery fails), U26/U27's items.

## 8. Operating modes, GC stages and build-environment lines

| mode | what U28 touches (lane) |
|---|---|
| `scripts/test.sh` at gc -1 (`unit-tests`) | C: one summary-helper start (OF-204), the probe bound, no XML; P's code-changed files (OF-151, OF-159, E731, the rename, the twin case) at -1; R's pytest-tier files; CI: the toolchain action's uv-sync first, then `scripts/test.sh` |
| `GC_THRESHOLD=32768` (`unit-tests-gc-threshold`) | the same files through `tests/_threshold_runner.py`; the twin case at 32768; CI: the same action |
| the coverage build (`unit-tests-coverage`, build-settrace) | C: the renderer without XML, four summaries and four HTML artifacts, no Codecov; the job's own sync gone (the action's first); OF-71's per-file times (lead) |
| `digital-twin-e2e`, device x stage x part | C: the device list from `devices` (R-8), the cold-cache build in the action; budgets (lead, R-21) |
| `firmware-build-verify`, per device | C: the device list, `!cancelled() && needs.devices.result == 'success'`, the cached picotool installed first |
| `lint-and-typecheck`, `shellcheck`, `actionlint`, `zizmor` | C: the uv-sync action, mypy with no arguments (R-13); R: the ruff block, the generated tree in the MicroPython-run group |
| the web jobs (lint, unit, put-matrix x 3, coverage, smoke) | C: gating (web-unit-tests `!cancelled()`, web-coverage's test step gates), the build in the action, `lint:html:built`, the Firefox key, `--require-all-engines`, OF-57's bounds; W: the flag and verdict, `-displayfd`, the shared frame, the Chromium fallback, the tsc base, `.htmlvalidate.json` |
| the installer tiers generic / flash / bench | W: a failed Playwright install stops `env` (generic tier's npm part; bench R0 [H57]); R: the uv pin read by every tier's `uv sync` |
| hardware runner levels | C: the retried sync first in `mpremote_connect.sh`, the manual runner, the wrapper (flash, bench, soak) and the rollover runner (R1 [H73]) |
| the preview and the smoke run by hand | W: `npm run preview` on 127.0.0.1 through `scripts/preview_server.py`; the smoke without the flag warns on a missing engine |

**BACKLOG build-environment lines** (CLAUDE.md "Pull request workflow"; each lane relays its line, X writes A.U28.38's one
paragraph): C - "CI: one retried `uv sync --locked` (`scripts/uv_sync_retried.sh`) through `.github/actions/uv-sync`; the
toolchain action keys on runner image, GCC and glibc and builds through `_unix_port.sh ensure standard`; the hardware
runners sync first; `test.sh` renders no Cobertura XML; the Unix-port probe is bounded"; R - "`pyproject.toml`: `pytest`/
`mpremote` pinned, `[tool.uv] required-version` (the chroot recipe installs that uv), the ruff exemptions in two scope
groups"; W - "`setup_toolchain.py`: a failed Playwright install stops `env`; `setup_cross_browser_toolchain.sh`: Xvfb on its
own check, verified downloads, bounded apt; `npm run preview` through `scripts/preview_server.py`; `tsconfig.base.json`";
lead - "`uv.lock` re-locked". The steps carrying them: 2g (M.TOOL.028/.030), 22, 48, 49, 50-54, 55-58, 61g, 62, 64, 77, 80,
112, 115, 117, 118, 123, 128.

## 9. CI time and the timing base

Base (R-17): U27's close, `audit/artefacts/evidence/U27_close/gates/final_times/times.tsv` (the after column),
`gates/final_tail/times.tsv` and lane E2's after-times (`lane_E2/handback.md`: `test_test_sh.py` 45.5 s, `test_tool_help.py`
3.5 s, `test_require_clean_hardware_run_sh.py` 2.5 s, `test_comment_block_cap.py` 5.7 s); for the 15 rows of
`S/u28/base_files.txt` (four MicroPython files at both stages, seven `tests_scripts` files), the lead's one timed sweep at
`b1fecfb` before launch; lanes run no before-runs. U27's CI on `b1fecfb` (run 38777834467): `unit-tests` 9.6 min,
`unit-tests-gc-threshold` 9.0 min, `unit-tests-coverage` 14.2 min, 45/45 jobs.

| CI job (timeout, `ci.yml`) | what U28 adds | estimate |
|---|---|---|
| `unit-tests`, `unit-tests-gc-threshold` (45 min, `:463`, `:501`) | the retried sync moves into the action (same work); four new `tests_scripts` files (~10-20 s; `test_ruff_exemptions_live.py` one ruff run plus one generation ~5 s), the twin case at each stage (~5-15 s of the bus-hazard file), OF-204 saves ~2 s per run | ~9.6 → ~10 min; OF-192's hung-scenario case decided at the re-measure (R-21) |
| `unit-tests-coverage` (45 min, `:530`) | the same; four report steps more (seconds); Codecov gone | ~14.2 → ~14.5 min |
| `digital-twin-e2e` (20 min, `:627`) | `devices` adds one 5-minute job before it (its own run ~20 s) | per leg unchanged; +~20 s on the critical path |
| `firmware-build-verify` (15 min, `:663`) | the picotool install from the cached build (~10 s) | +<1 min |
| `lint-and-typecheck` (15 min, `:337`) | the action's pinned-uv install; mypy with no arguments (the same files) | unchanged |
| web jobs (`:73`, `:103`, `:154`, `:205`, `:282`) | web-lint gains the uv sync and the built-page lint (~1-2 min: every device's site staged); the smoke's Firefox key rolls monthly (a cold month adds the ~106 MB conda pull once) | web-lint ~3 → ~5 of 10 min |
| `devices` (new, 5 min) | a glob | ~20 s |

Every tests_scripts, `tests/` or JS file a lane adds or grows is timed alone at the stage(s) it runs; above 10 s, or 10 %
over its base, it is made efficient, never bounded (R-17). Expected near the bar: `test_ruff_exemptions_live.py` (a ruff run
over ~1000 files and a six-device generation into `tmp_path`: under 10 s if it reuses one generation), the bus-hazard twin
file (U24's base 151.6 s at -1: the new case must stay within 10 %), `test_test_sh.py` (45.5 s: OF-204 should lower it).

## 10. Per-step table

Every change in work-order order: step (`g` = co-landing group), change, lane, verdict, the U28 part, and the
seen-failing-first check without hardware (or the proof for a verify row) with its round. Lanes read their rows in their
packet's index; the full texts are in the packets.

| step | change | lane | verdict | U28 part | seen failing first (no hardware) / round |
|---|---|---|---|---|---|
| 1 | DOCS.095 | X | x | CLAUDE.md zizmor bullet: the configured audits and the commit-SHA pin form (A.U28.40) | test_decision_vocabulary.py, test_citations.py |
| 2g | GEN.003 | R | verify | nothing to write: the generated `WifiConfig(...)` takes the hotspot default positionally (`buildgen/codegen.py:506` `wifi = f"WifiConfig({_lit(device_table['hostname'])}, {_lit(device_table['hotspot_password'])}, `), a shape S105/S106 never match, so the module constant is not written (R-9) | ruff over `build/generated_src` with S105/S106 live and no generated S106 entry: clean |
| 2g | GEN.005 | R | verify | as M.GEN.003 (the `hotspot_password=_HOTSPOT_PW_DEFAULT` keyword form not written, R-9) | as M.GEN.003 |
| 2g | TOOL.028 | R | apply | R1: the global `ignore` narrowed to what holds in every scope (`pyproject.toml:65-195`); PTH, ASYNC230, PT, ASYNC110, PLW0603, TRY003/EM101/EM102, SIM105, RUF005, PLR0124, S104, N802 leave it; CPY001 reason (A.U28.32), the S105/S106 line | ruff over the eight scopes and `build/generated_src`: the only reds at `<API>` are P's RUF100 lines and the listed host findings of C and W (L0 listing); test_ruff_exemptions_live.py green on R's scopes |
| 2g | TOOL.030 | R | apply | R1: one per-file block in two scope groups plus per-file entries, each reasoned (`pyproject.toml:218-338`); every inline non-E402 `noqa` P removes has its central home first (packet table); ARG004 everywhere, ARG002 in `tests_scripts/**`, ARG005 in `tests_hardware/**`, `src/asy_wifi_service.py`'s S106 go; ANN401 entries stay while they fire (U34 removes them); PT018 and EM101/EM102/TRY003 stay for the host test suites (R-5) | test_ruff_exemptions_live.py red at b1fecfb on ARG004 (`pyproject.toml:228`, `:233`, `:234`) and the S106 of `:265`; green after |
| 2g | TOOL.031 | R | verify | the pyflakes table is already the end state (`pyproject.toml:202-204` `allowed-unused-imports = ["frozen_html", "manual_bus_electrical", ...]`) | test_ruff_exemptions_live.py keeps it (a policy entry with no finding to test: listed with its reason) |
| 2g | TSC.047 | R | verify | its U28 part is the hotspot constant, not written (R-9): `tests_scripts/test_buildgen_generate.py:1307` keeps asserting the positional form | file green |
| 2g | TSC.123 | R | apply | R1: new `tests_scripts/test_ruff_exemptions_live.py`: one ruff run with every exemption lifted over the eight scopes, the generated tree built into `tmp_path`; a policy entry with no current site listed with its reason | red at b1fecfb (ARG004/ARG002/ARG005 entries with no finding, S106 for `src/asy_wifi_service.py`); green at `<W1>` once P's inline noqa are gone (red at `<API>` on the entries P's comments still shadow: listed) |
| 3 | DOCS.096 | X | x | CLAUDE.md unit-test bullet: which scopes carry which exemptions, the liveness check (A.U28.34) | test_decision_vocabulary.py, test_citations.py |
| 4 | GEN.010 | R | apply | RUF005 in `buildgen/codegen.py`'s collectors: concatenation of a literal to unpacking (host code; RUF005 leaves the global list) | `ruff check --select RUF005 buildgen` red at b1fecfb; generated modules byte-identical (test_buildgen_generate.py, test_buildgen_reproducible.py green) |
| 5 | GEN.011 | R | apply | RUF005 at the `all_vars` concatenation of `buildgen/codegen.py` (with M.GEN.010) | as M.GEN.010 |
| 6 | HW_BENCH.036 | R | apply | pyproject only: per-file S104 for `tests_hardware/rogue_udp_responder.py` (`:20` `self._sock.bind(("0.0.0.0", local_port))  # binds the bench host's responder on the bench LAN`); the file unchanged | ruff S104 red on that line once S104 leaves the global list; clean with the entry / R1 [H73] |
| 7 | HW_BENCH.038 | R | verify | no inline noqa left in `tests_hardware/conformance.py` (U26); `tests_hardware/isl29125_conformance.py` gone | git grep '# noqa' tests_hardware/conformance.py: none |
| 8 | HW_BENCH.071 | R | apply | the password half landed (U26: `tests_hardware/bench/test_hotspot_role_reversal.py:156` `hotspot_password()`); the two inline `noqa: S603`/S607 (`:209`, `:219`) move to a per-file entry | red at `<API>`: RUF100 names the line (its code is central now); clean after / R1 [H73] |
| 9 | HW_BENCH.100 | R | verify | `tests_hardware/manual/runner.py` carries no F401 noqa; the pyflakes table names the manual modules (`pyproject.toml:204`) | git grep '# noqa' tests_hardware/manual/runner.py: none |
| 10 | HW_DEV.062 | P | verify | no inline noqa left in `fram_error_log_roundtrip.py` (U26) | git grep: none |
| 11 | HW_DEV.063 | P | verify | no inline noqa left in `fram_error_log_reset_race_seed_and_race.py` (U26) | git grep: none |
| 12 | HW_DEV.064 | P | verify | no inline noqa left in `fram_error_log_reset_race_verify.py` (U26) | git grep: none |
| 13 | HW_DEV.090 | P | verify | no lambda or noqa left in `bus_topology_autodetect_and_hazard_sweep.py` (U26) | git grep 'lambda\|noqa': none |
| 14 | HW_DEV.107 | P | verify | `timer_alarm_pool_exhaustion.py:20` `for _ in range(64):`, `:27` `fact("constructed", len(timers))` (U26); no noqa | git grep: none |
| 15 | HW_DEV.112 | R | verify | both repro scripts deleted (U26); `pyproject.toml` holds no entry for them | git ls-tree: absent |
| 16 | HW_DEV.140 | P | apply | `sgp40_voc_algorithm_quality.py:66` `# noqa: B905` goes (B905 central for device scripts) | red at `<API>`: RUF100 names the line (its code is central now); clean after / R1 [H73] |
| 17 | PROC.018 | LEAD | lead | the owner's standing push grant on `hundertvolt/datasheets` (M.DOCS.014: owner, 2026-10-05) used for A.U28.35: the populate commit pushed first, then the submodule commit | `git ls-remote` of the private repo shows `main` at the populate commit before the submodule commit is made |
| 18 | HW_BENCH.103 | R | verify | nothing at U28: the citations (`tests_hardware/manual/manual_sensor_accuracy.py:11`) keep their `datasheets/<chip>/` paths under the submodule | git grep: the path unchanged |
| 19 | SCR.009 | C | verify | `scripts/micropypath.toml` unchanged; its `.gitignore` sentence is step 124's | file unchanged |
| 20 | SCR.046 | R | apply | pyproject only: `scripts/_digital_twin_ci_suite.py` gains PLW0603 beside S603 (`:1738` `global _SUMMARY`, `:1760` `global _CURRENT_PASS_LABEL`); the script unchanged | ruff PLW0603 red on both lines once it leaves the global list; clean with the entry |
| 21 | SCR.068 | R | apply | the six bare `# noqa: E402` of `scripts/_generate_sensortask_modules.py` gain ` - <reason>` | test_suppression_form.py red at `<API>` on the line; green after |
| 22 | SCR.069 | C | apply | `--xml-file`, `cov.xml_report(...)` and the Cobertura print go (`scripts/_render_coverage.py:29`, `:50-51`, `:56-57`); `os.path`/`glob` to pathlib (PTH); docstring "HTML and a markdown summary"; the pin landed U27 (`:4` `dependencies = ["coverage==7.16.2"]`) | `--xml-file` now an argparse error (exit 2) - red at b1fecfb; `ruff check --select PTH` red at b1fecfb; test_render_coverage_anchors.py, test_test_sh.py's render cases green |
| 23 | HW_BENCH.125 | X | x | tests_hardware/README.md Prerequisites: the bench host's uv equals `pyproject.toml`'s `[tool.uv] required-version` (A.U28.02) | test_citations.py / R0 [H57] |
| 24 | SCR.070 | R | verify | the stripper defines no `visit_*` method (`git grep 'def visit_' scripts/_strip_type_checking.py`: none), so N802 needs no entry for it | git grep: none |
| 25 | SCR.065 | R | apply | A.U28.28's E402 lines already carry reasons; OF-194: an unwritable `--output` (an `OSError` from `write_image()`) prints one line naming the path, exit 1, no traceback (`scripts/build_firmware.py:323` handler) | new test_build_firmware.py case: an `--output` in a read-only directory - traceback at b1fecfb, one line after |
| 26 | SPEC.007 | X | x | A.3 first paragraph: every tool its own CI job, the job list in B.10 (A.U28.12) | test_citations.py |
| 27 | SPEC.126 | X | verify | nothing at U28: the catalog is U30's stage 4 (U28 is named only among its predecessors) | - |
| 28 | SPEC.148 | X | x | L.5 scope clause: the generated modules carry the MicroPython-run group's exemptions (A.U28.41) | test_citations.py |
| 29 | SRC_NET.096 | P | apply | `src/asy_wifi_service.py:374`, `:651` `# noqa: B905` go (B905 central for `src/**`) | red at `<API>`: RUF100 names the line (its code is central now); clean after |
| 30 | SRC_NET.130 | P | apply | `src/asy_webserver_service.py:1032` `# noqa: B905` goes; the reason stays as the one-line comment the M text gives | red at `<API>`: RUF100 names the line (its code is central now); clean after |
| 31 | SRC_SENS.038 | P | verify | nothing at U28: the datasheet citations keep their paths under the submodule | git grep: unchanged |
| 32 | TEST_HELP.003 | P | apply | `tests/_threshold_runner.py:20` `# noqa: S102` goes (per-file S102) | red at `<API>`: RUF100 names the line (its code is central now); clean after |
| 33 | TEST_HELP.004 | P | apply | `tests/_coverage_runner.py:112` `# noqa: S102` goes (per-file S102) | red at `<API>`: RUF100 names the line (its code is central now); clean after |
| 34 | TEST_HELP.010 | R | apply | pyproject only: the `tests/machine.py` entry's trailing ANN401 comment (`pyproject.toml:252`) moves above it, category labels defined before first use (A.U28.29 (3)) | review; ruff clean |
| 35 | TEST_UNIT.037 | P | verify | no ANN401 noqa left in `tests/test_asy_fram_driver.py` (U24) | git grep: none |
| 36 | TEST_UNIT.058 | P | apply | `tests/test_asy_isl29125_driver.py` noqa go: B905 `:183`, FBT001/FBT002 `:165`, `:2401`, `:2422`, `:2541`, PERF401 `:1081`, `:1297` (central groups); OF-151's sweep (P's row) | red at `<API>`: RUF100 names the line (its code is central now); clean after |
| 37 | TEST_UNIT.095 | P | apply | `tests/test_asy_ntp_client.py:261`, `:263` `= lambda ...  # noqa: E731` become local `def`s; `:490` B905 noqa goes | red at `<API>`: RUF100 names the line (its code is central now); clean after; the file green at -1 and 32768 |
| 38 | TEST_UNIT.113 | P | apply | with step 37 (same file, same sweep) | as step 37 |
| 39 | TEST_UNIT.249 | P | apply | `tests/test_asy_config_manager.py:2593` B905 noqa goes (the M text's `tests/test_config_manager.py` was renamed) | red at `<API>`: RUF100 names the line (its code is central now); clean after |
| 40 | TEST_UNIT.272 | P | apply | `tests/test_math_helpers.py:467` `test_rgb_to_xyz_pure_red_matches_the_sRGB_matrix_column` renamed `..._srgb_...` (N802 leaves the global list; a test name has no external spelling) | ruff N802 red at `<API>` on `:467`; the file green at -1 and 32768 |
| 41 | TEST_UNIT.332 | P | verify | no F401 noqa (`tests/test_website_build_integration.py:13` `import frozen_html  # mounts /html on import`) | git grep: none |
| 42 | TOOL.016 | C | apply | new `devices` job (glob `devices/*.toml`, skip `zz_test_`, empty set fails), tagged 5-minute budget | test_ci_workflow.py rule (7) red at b1fecfb (`ci.yml:631`, `:667` list the six names); actionlint, zizmor |
| 43 | DOCS.053 | X | x | README code-quality: the uv pin's location, CI's device matrices derived (A.U28.02, A.U28.06) | test_citations.py |
| 44 | TOOL.017 | C | apply | digital-twin-e2e's device dimension from `devices` (`needs: [unit-tests, devices]`), keeping the gc_threshold x part dimensions (R-8); every matrix value reaches `run:` through `env:` | test_ci_workflow.py rule (7) red at b1fecfb (`ci.yml:631` `device: [wozi, dev, ...]`); actionlint, zizmor (template injection) |
| 45 | TOOL.020 | C | verify | the first-party tags are the refreshed majors (U0: `actions/checkout@v7`, `actions/cache@v6`, `actions/setup-node@v7`, `actions/upload-artifact@v7`); the local `uses: ./` form stays (actionlint 1.7.12 rejects `$/`); no `submodules:` key (A.U28.35) | test_ci_workflow.py rules (3), (4) |
| 46 | DOCS.014 | X | x | the move's fact, minimal: README's datasheet mention names the private submodule and `git submodule update --init datasheets` (the full section is U34's, R-15) | test_citations.py (an uninitialised submodule only warns) |
| 47 | DOCS.068 | X | x | CLAUDE.md "Datasheets" short version: the submodule and its init command (U36 words the rest, R-15) | test_decision_vocabulary.py, test_citations.py |
| 48 | TOOL.024 | R | apply | `[tool.uv]` gains `required-version = "==<v>"` (the uv `uv --version` reports in the lead's environment, recorded in the hand-back) with its one comment line | test_tool_pins.py red at b1fecfb (`pyproject.toml:13-14` has no `required-version`) / R0 [H57] |
| 49 | TOOL.025 | R | apply | `"pytest"`, `"mpremote"` (`pyproject.toml:23-24`) pinned to the versions `uv.lock` resolves; the lead re-locks at `<W1>` (R-11) | test_tool_pins.py red at b1fecfb on both names; green after the lead's `uv lock` |
| 50 | SCR.014 | C | apply | new `scripts/uv_sync_retried.sh`: `uv sync --locked`, three attempts, 10 s and 20 s pauses, the two tags moved onto its literals | new test_uv_sync_retried_sh.py red (no file) |
| 51 | SCR.029 | C | apply | `scripts/mpremote_connect.sh` runs `scripts/uv_sync_retried.sh` before its first `uv run --no-sync` (`:21`) | test_mpremote_connect_sh.py: the stub uv's first call is `sync --locked` - red at b1fecfb / R1 [H73] |
| 52 | SCR.033 | C | apply | `scripts/run_manual_hardware_tests.sh` runs the retried sync before `:22` | the runner case's first stub-uv call is `sync --locked` - red at b1fecfb / R1 [H73] |
| 53 | SCR.034 | C | apply | `scripts/_require_clean_hardware_run.sh` runs the retried sync before `:67`'s first `uv run --no-sync` (the flash, bench and soak runners go through it) | test_require_clean_hardware_run_sh.py: one `sync --locked` first, every later call `--no-sync` - red at b1fecfb / R1 [H73] |
| 54 | SCR.074 | C | apply | `scripts/run_bench_rollover_test.sh` runs the retried sync before `:33` | test_hardware_runners.py rollover case - red at b1fecfb / R1 [H73] |
| 55 | TOOL.011 | C | apply | lint-and-typecheck: `uses: ./.github/actions/uv-sync` replaces `:342-356`; the U27 generation/ruff/mypy stage landed (`:357-362`); OF-24: the mypy step runs `scripts/typecheck.sh` with no arguments (R-13) | test_ci_workflow.py (no second retry loop, the uv-sync action first); test_lint_type_scopes.py's CI case red at b1fecfb under its new no-argument assertion |
| 56 | TOOL.012 | C | apply | shellcheck, actionlint, zizmor jobs take the uv-sync action (`:376-388`, `:405-417`, `:433-445` go) | test_uv_sync_retried_sh.py's grep rule: no `for attempt in` loop left in `.github/` - red at b1fecfb |
| 57 | TOOL.013 | C | apply | unit-tests: the second sync (`:474-486`) goes; the toolchain action's first step is the retried sync, ahead of `scripts/test.sh` | test_ci_workflow.py: the action (uv-sync first) precedes `scripts/test.sh` in `unit-tests` |
| 58 | TOOL.015 | C | apply | unit-tests-coverage: the second sync (`:541-553`) and both Codecov steps (`:578-595`) go; four summaries and four HTML artifacts; job comment per the M text | test_test_sh.py's report-step count (`:1687` `== 6`) becomes 8 - red at b1fecfb; test_ci_workflow.py rule (3) (codecov's `# v7` comment) |
| 59 | TOOL.021 | C | apply | `.github/zizmor.yml:1-3`, `:11-12` say what it configures (two audits; dorny the one third party) | zizmor --offline parses it; review (YAML is review-enforced) |
| 60 | SCR.025 | R | verify | `scripts/lint.sh:49` already names `build/generated_src`; R confirms ruff lints the named git-ignored tree (a finding planted in a scratch copy is reported); if it skips it, the lead adds `--no-respect-gitignore` to lint.sh and CI's ruff line at `<W1>` (R-11) | the planted finding reported - else the lead's one-liner |
| 61g | TOOL.001 | C | apply | the toolchain action: header line, three-line description naming its nine callers, input `build-unix-port`, `uses: ./.github/actions/uv-sync` first, the identity step, the key with `steps.ident.outputs.id`, the build step `scripts/_unix_port.sh ensure standard` plus the setcap the four copies carry (OF-193's CI half) | test_ci_workflow.py rule (6) red at b1fecfb (no identity, "six" callers, four build copies) |
| 61g | TOOL.002 | C | apply | new `.github/actions/uv-sync/action.yml`: the pinned uv (`require_python311` before the bare `python3`), then `scripts/uv_sync_retried.sh` | test_ci_workflow.py; actionlint; zizmor |
| 61g | TOOL.006 | C | apply | web-lint-and-typecheck: the uv-sync action after `npm ci`; `npm run lint:html:built` after html-validate (OF-141's CI half) | test_ci_workflow.py rule (9) red at b1fecfb |
| 61g | TOOL.019 | C | apply | a tag above every `timeout-minutes` (sixteen with `devices`); the two budget comments per the M text; values stay until the lead's re-measure (A.U28.36, OF-192) | test_tunables_register.py (Part N rows via X); test_ci_workflow.py: every job has a tagged budget |
| 62 | SCR.008 | C | apply | OF-191: the two probe calls (`scripts/_unix_port.sh:99`, `:275` `"$1" -c "$_UNIX_PORT_PROBE"`) run under `timeout -s KILL` with a tagged bound; a timeout reads `unusable` (R-12); A.U28.04's body is the action's | test_unix_port_sh.py: a stub `timeout` on PATH records the bound and a stub returning 137 reads `unusable` - red at b1fecfb (no bound); never a real wait |
| 63 | SCR.010 | C | verify | `scripts/_require_python.sh` unchanged; the uv-sync action sources it | file unchanged |
| 64 | SCR.021 | W | apply | new `scripts/preview_server.py` (127.0.0.1, the four site directories only, `--port`, one-line bind error); `package.json:34` `"preview"` through `uv run` | new test_preview_server.py red (no file) |
| 65 | SCR.036 | C | verify | A.U28.04 changes nothing in `scripts/test.sh` (the probe landed U27) | file's probe lines unchanged |
| 66 | SCR.072 | C | verify | `scripts/build_frozen_html.sh` unchanged; `.gitignore`'s text naming its output is step 124's | file unchanged |
| 67 | SCR.071 | C | verify | `scripts/build_website.sh` unchanged; the built-page CI step is step 61's | file unchanged |
| 68 | SPEC.114 | X | x | H.2: `npm run preview` serves the site's own directories on 127.0.0.1 (A.U28.24) | test_citations.py |
| 69 | TOOL.003 | C | apply | a first comment block before `name: CI` (`ci.yml:1`) | test_comment_block_cap.py's `_HEADER_PENDING` gained-row assertion goes red (the lead deletes the row, R-10) |
| 70 | TOOL.007 | C | apply | web-unit-tests: `!cancelled()` and the order-only comment; `with: build-unix-port: 'true'`; its build step (`:130-137`) goes | test_ci_workflow.py rules (1a), (6) red at b1fecfb |
| 71 | TOOL.008 | C | apply | web-put-matrix: the success-gated comment; build-unix-port; its build step (`:183-190`) goes | test_ci_workflow.py rules (1), (6) |
| 72 | TOOL.018 | C | apply | firmware-build-verify: device matrix from `devices` with `!cancelled() && needs.devices.result == 'success'`; the cached picotool installed before the build (A.U28.05); the cold-cache comment (`:674-675`) corrected; the python check landed U27 (`:682-683`) | test_ci_workflow.py rule (7) red at b1fecfb; the picotool step is CI-only (the lead's run proves it) |
| 73 | TOOL.027 | R | apply | the confusables comment names where `×` lives (`pyproject.toml:61-62`); the entry kept while the liveness check sees a RUF001-RUF003 finding naming it | test_ruff_exemptions_live.py |
| 74 | TOOL.038 | R | apply | `toolchain/micropython_overrides.py:294` `if queuelen < 2:  # noqa: PLR2004` -> `_MIN_TCP_SND_QUEUELEN = 2  # lwIP's own floor, ...` used in the comparison | ruff PLR2004 red once the noqa goes; test_micropython_overrides.py green |
| 75 | TOOL.046 | W | verify | nothing in the installer: `NETWORK_ATTEMPTS = 3` (`toolchain/setup_toolchain.py:104`) and `run_retried()`'s `backoff_s: float = 10.0` (`:1613`) are what C's test pins `scripts/uv_sync_retried.sh` equal to | C's test_uv_sync_retried_sh.py |
| 76 | TOOL.052 | W | verify | nothing in the installer for A.U28.05: CI installs from the cached picotool build tree (step 72) | - |
| 77 | TOOL.070 | W | apply | `ensure_playwright_browser()` (`toolchain/setup_toolchain.py:1176`): a failed `install chromium` raises `SetupError` naming `--skip-npm`; `install-deps` skipped under `skip_apt`, else its failure raises | new test_setup_toolchain_env.py cases red at b1fecfb (it logs and returns) / R0 [H57] |
| 78 | DOCS.047 | X | x | README install recipe: the uv version is `required-version`'s; `env` fails when Playwright's Chromium does not install | test_citations.py |
| 79 | DOCS.064 | X | x | BACKLOG 'Real-hardware work still owed': R0 [H57] re-runs `env --tier bench` (the uv pin, the now-fatal Playwright step) | test_citations.py / R0 [H57] |
| 80 | TOOL.071 | W | apply | `run_env()` reports ready only after the Playwright step returns (with step 77) | as step 77 |
| 81 | TSC.021 | R | verify | no inline noqa in `tests_scripts/test_bench_harness_helpers.py` (U26) | git grep: none |
| 82 | TSC.027 | R | verify | no inline noqa in `tests_scripts/test_bench_no_task_ended_completeness.py` (U26) | git grep: none |
| 83 | TSC.065 | LEAD | lead | the pending set empties (`tests_scripts/test_comment_block_cap.py:43` `_HEADER_PENDING = frozenset({"eslint.config.js", "vitest.config.js", ".github/workflows/ci.yml", ".github/actions/setup-micropython-toolchain/action.yml"})`) at `<W1>` as C and W land the headers (R-10); the length rule stays off (U27 R-4, BACKLOG owner question 6) | the gained-row assertion red on each headed file until the row goes |
| 84 | TSC.083 | R | apply | `tests_scripts/test_digital_twin_ci_suite_ceiling.py:37` `# noqa: A002` goes (per-file A002, N802 for `do_GET` `:29`, `:47`); `_GET_TIMEOUT_S` (`:20`) carries its tag | red at `<API>`: RUF100 names the line (its code is central now); clean after |
| 85 | TSC.126 | W | apply | test_setup_toolchain_env.py: Playwright install and install-deps failures raise naming the fix; `skip_apt` never calls install-deps | red at b1fecfb |
| 86 | TSC.132 | R | apply | R1: new `tests_scripts/test_suppression_form.py` (tokenised comments over the eight scopes' `.py`) | red at b1fecfb: 69 mis-ordered code lists in 27 `.py` files, the bare and parenthesised E402s, the `src/` ignores with no reason (packet tables) |
| 87 | HW_DEV.048 | P | apply | `uart_driver_read_never_blocks_the_loop.py:204` `# type: ignore[method-assign]` gains its reason (a timing wrapper stands in for the UART, a test double) | review (not `src/`); mypy cold / R1 [H73] |
| 88 | SPEC.075 | X | x | D.6: the suppression form rule in one sentence citing the check; the two scope groups (A.U28.27, A.U28.30) | test_citations.py |
| 89 | SPEC.104 | X | x | F.5.5: the suppression rule sentence (A.U28.30) | test_citations.py |
| 90 | SRC_CORE.016 | P | verify | no `type: ignore` left in `src/asy_system_service.py` (the M text's `src/system_service.py`) | git grep: none |
| 91 | SRC_NET.030 | P | apply | `src/asy_udp_socket.py:143-145`: the trigger line ("Remove the ignore once the stub narrows it (warn_unused_ignores then flags it).") joins the two reason lines | test_suppression_form.py red at `<API>` on the line; green after |
| 92 | SRC_NET.081 | P | apply | `src/asy_wifi_service.py:284` `# type: ignore[assignment]`: reason and trigger | test_suppression_form.py red at `<API>` on the line; green after |
| 93 | SRC_NET.165 | P | apply | `src/asy_uart_comm.py:411` (`# type: ignore[misc]`), `:632`, `:634`, `:635`: the trailing reason and the one comment line above the `try:` | test_suppression_form.py red at `<API>` on the line; green after |
| 94 | TSC.106 | R | apply | `tests_scripts/test_measurement_field_tuple_agreement.py:34` `# type: ignore[attr-defined]` -> a typed loop (the binding and the SCD30 `always=` case landed: `:69`, `:88-99`) | host mypy cold (warn_unused_ignores); file green |
| 95 | TSC.168 | C | verify | check only: `tests_scripts/test_js_coverage_report_dir.py:46-47`'s two substrings still hold after A.U28.16 | file green on C's ci.yml |
| 96 | TSC.175 | C | verify | `tests_scripts/_devices.py:25` `def bench_device(`, `:42` `def devices_with(` landed (U26/U27) | git grep |
| 97 | TSC.207 | W | apply | new test_preview_server.py: port 0 in a thread, the five paths, 127.0.0.1, a taken port exits 1 naming `--port` | red (no file) |
| 98 | TSC.223 | C | apply | new test_uv_sync_retried_sh.py (stub `uv`/`sleep` PATH), equal to `setup_toolchain.NETWORK_ATTEMPTS` and `run_retried()`'s `backoff_s` | red (no file) |
| 99 | TWIN.011 | P | verify | nothing at U28: `digital_twin/_fram_chip.py`'s datasheet citations keep their paths | - |
| 100 | TWIN.025 | P | verify | nothing at U28: `digital_twin/machine.py`'s FRAM table citations keep their paths | - |
| 101 | TWIN.040 | R | apply | pyproject only: per-file S104 for `digital_twin/network.py` (`:37` `_UNSET_IFCONFIG = ("0.0.0.0",) * 4`) | ruff S104 red once global goes; clean with the entry |
| 102 | TWIN.044 | R | apply | pyproject only: `digital_twin/launch.py`'s S105 under the credential block (A.U28.29) | ruff clean; liveness |
| 103 | TWIN.057 | P | verify | no ANN401 noqa left in `digital_twin/unix_port_poll_prewarm.py` | git grep: none |
| 104 | TWIN.102 | P | apply | A.U28.28's part landed (`:23` `# noqa: E402 - imported after the prewarm and the UDP shim`); REGISTER `:671`'s carry: the twin cancelled-session case (a sensor task cancelled inside its I2C session on a shared bus leaves the bus usable and the sibling's next read valid, M.TWIN.104's `test_a_sensor_task_cancelled_inside_its_session_leaves_the_bus_usable`) | a guard: passes at once; bite in a scratch copy (the cancelled session never releases its bus) red naming the case; the file at -1 and 32768 (wall-time bound), timed alone |
| 105 | TWIN.122 | P | apply | `tests/test_digital_twin_isl29125_autorange.py:110` B905, `:486`, `:505` PERF401 noqa go | red at `<API>`: RUF100 names the line (its code is central now); clean after |
| 106 | TWIN.132 | R | apply | pyproject only: `tests/test_digital_twin_network_neopixel.py`'s S106 under the credential block | ruff clean; liveness |
| 107 | TWIN.144 | P | verify | A.U28.28's part landed (`:27-29` E402 with reasons); OF-47/149/187/188 move to U35 (R-14) | git grep |
| 108 | TWIN.158 | P | apply | `tests/test_digital_twin_uart_link.py:710` PERF401 noqa goes; its 20 bare `# noqa: E402` gain the reason | red at `<API>`: RUF100 names the line (its code is central now); clean after; test_suppression_form.py red at `<API>` on the line; green after |
| 109 | TWIN.164 | P | verify | nothing: the wrappers and their library left at U24/U25 | git ls-tree: absent |
| 110 | WEB.072 | W | verify | landed at U0's refresh: `.nvmrc` `24`, `package.json:7-9` `"engines": {"node": ">=24 <25"}`, `:39` `"@types/node": "^24.19.1"`; R's test_tool_pins.py pins the agreement | test_tool_pins.py's Node case green |
| 111 | WEB.070 | W | apply | `eslint.config.js:6-10`'s JSDoc moves above the imports as the first block (A.U28.42) | `_HEADER_PENDING` gained-row red (lead, R-10); npm run lint |
| 112 | WEB.071 | W | apply | `package.json:34` `"preview": "python3 -m http.server 8000"` -> `"uv run scripts/preview_server.py"` (the rest landed U0/U6/U23) | test_preview_server.py; test_config_paths_resolve.py (the script path resolves) |
| 113 | SCR.063 | W | apply | `scripts/cross_browser_smoke.mjs`: `--require-all-engines` (else exit 2 as today, `:614-617`), header line; the device loop and probe landed | test_cross_browser_smoke_probe.py engineVerdict cases red (no export); npm run lint/typecheck |
| 114 | DOCS.055 | X | x | README website tooling: preview on 127.0.0.1, the smoke's engine flag in CI, derived device set | test_citations.py |
| 115 | SCR.073 | W | apply | `scripts/setup_cross_browser_toolchain.sh`: Xvfb its own block (`:32-39` installs it only with WebKit), Microsoft's key checked by fingerprint (`:44`), micromamba pinned and SHA-256 checked (`:65` `releases/latest`), `--fail` downloads, temporary files after one trap; OF-48's apt bounds | new test_setup_cross_browser_toolchain_sh.py cases red at b1fecfb |
| 116 | SPEC.156 | X | x | Part N rows for every tag U28 adds or moves (relay); the budget bases after the lead's re-measure | test_tunables_register.py |
| 117 | TOOL.010 | C | apply | web-cross-browser-smoke: success-gated comment, build-unix-port, `npm run build:site` its own step, the monthly Firefox key with the installer hash (`ci.yml:324` `key: cross-browser-firefox-v2-${{ runner.os }}`), `--require-all-engines` (`:328`); OF-57's Playwright steps bounded | test_ci_workflow.py rules (6), (8) red at b1fecfb |
| 118 | TOOL.009 | C | apply | web-coverage: the success-gated comment under the job key; build-unix-port; the test step gates (`:240-242` `continue-on-error: true` goes, `set -o pipefail`); report steps `always() && hashFiles(...)` | test_ci_workflow.py rules (1), (5) red at b1fecfb; test_js_coverage_report_dir.py green |
| 119 | DOCS.050 | X | x | README recipes: preview, the smoke, coverage outputs without XML | test_citations.py |
| 120 | DOCS.054 | X | x | README "Test coverage": Codecov words go with the upload | test_citations.py |
| 121 | TSC.146 | R | apply | new `tests_scripts/test_tool_pins.py`: every dev pin `==` and equal to the lock's resolved version, `required-version` exact, no second uv literal in `.github/**`, Node's majors agree; the coverage pin is `test_script_metadata_pins.py`'s (not repeated, R-11) | red at b1fecfb (`pyproject.toml:23-24`, no `required-version`) |
| 122 | SCR.038 | C | verify | nothing at U28 in the pytest tier (run record and host coverage landed U24/U27) | - |
| 123 | SCR.044 | C | apply | `scripts/test.sh:181` archives no XML; `:902`, `:904` render without `--xml-file` | test_test_sh.py's render cases (`:1656-1657` expect `--xml-file`) red under the new expectation |
| 124 | PROC.019 | C | apply | `.gitignore` end state: current facts, outside writers named, every block within the cap; `coverage.xml`/`coverage_digital_twin.xml` leave | `git check-ignore -v` of the outputs before and after; review (config text) |
| 125 | TOOL.078 | LEAD | lead | `uv lock` after R's pins, then `uv sync`, then `ruff --version`/`mypy --version`/`zizmor --version`/`actionlint --version`/`shellcheck --version` against the pins (CLAUDE.md's merge rule) | test_tool_pins.py green on `<W1>` |
| 126 | TSC.136 | C | apply | test_test_sh.py: four reports and no XML, the CI report-step count, the step-summary rule kept; OF-199 (D.15 order, last edit) and OF-204's one-start case | red at b1fecfb under the new expectations |
| 127 | TSC.172 | W | apply | test_setup_cross_browser_toolchain_sh.py: Xvfb alone, the fingerprint and SHA-256 mismatches, no executable left | red at b1fecfb |
| 128 | WEB.073 | W | apply | new `tsconfig.base.json` (shared options); `tsconfig.json`, `tsconfig.node.json` extend it, headers name their files; the `skipLibCheck: false` trial; further strictness options tried | pure migration: `npm run typecheck` clean before and after; the trial's result recorded |
| 129 | SCR.023 | W | apply | `scripts/_cross_browser_probe.mjs` exports `engineVerdict(available, results, {requireAllEngines})` | test_cross_browser_smoke_probe.py red (no export) |
| 130 | SCR.064 | W | apply | the smoke on the shared JS frame (`spawnTwin`/`stopTwin`/`waitUntilServing` of `tests_js/_twin_process.js:146`, `:192`, `:235`), its own copies (`scripts/cross_browser_smoke.mjs:163`, `:196`, `:119`) go; `startVirtualDisplay()` with `-displayfd` (A.U28.18); Chromium's sandbox fallback after the pinned build (A.U28.26) | npm run lint/typecheck; a scratch node run of `startVirtualDisplay()` on the sandbox's Xvfb; the engines' legs CI-only (the lead) |
| 131 | TOOL.005 | C | apply | web-changes: `actions: read`, the base step (last green run's head SHA through `gh api`, values via `env:`), `base:` from it, the empty-base fallback, the full input list (`ci.yml:44-61` lacks `digital_twin/**` ...), `tsconfig*.json` | test_ci_workflow.py rule (2) red at b1fecfb (`:42` `base: ${{ github.ref }}`); the `gh` call is CI-only (the lead) |
| 132 | TOOL.004 | C | apply | the concurrency and permissions comments (`ci.yml:11-12`, `:17-18`) | review; actionlint |
| 133 | TSC.184 | W | apply | test_cross_browser_smoke_probe.py: engineVerdict with and without the flag | red (no export) |
| 134 | WEB.074 | W | apply | `vitest.config.js`: the JSDoc (`:25-29`) first; the pinned Chromium unless absent, then the sandbox path (`:22-23`), comment with its removal trigger | `_HEADER_PENDING` gained-row red (lead); npm run lint/typecheck; one quick vitest file starts its browser |
| 135 | WEB.076 | W | apply | `tests_js/vitest-commands.d.ts`: the three comment texts, signatures matching the commands (or `.ts` per the skipLibCheck trial) | npm run typecheck |
| 136 | TSC.066 | R | apply | new `tests_scripts/test_config_paths_resolve.py` | a guard: green at b1fecfb unless a dead path exists; bite: a planted dead glob in a scratch copy of pyproject read by the test |
| 137 | TSC.062 | C | apply | new `tests_scripts/test_ci_workflow.py`, rules (1)-(9) plus the moved matrix rule | red at b1fecfb on rules 1, 1a, 2, 3, 5, 6, 7, 8, 9 (each line named) |
| 138 | DOCS.098 | X | x | CLAUDE.md retry and hang-backstop bullets (A.U28.10, A.U28.11 (1)) | test_decision_vocabulary.py, test_citations.py |
| 139 | DOCS.107 | X | x | CLAUDE.md "Pull request workflow": the head-commit rule (A.U28.11 (2)) | test_decision_vocabulary.py |
| 140 | SCR.061 | C | verify | `scripts/run_digital_twin_ci.sh` unchanged: CI keeps passing `--gc-threshold` and `--part` (R-8) | file unchanged |
| 141 | SPEC.124 | X | x | H.8: the CI mechanism, `tsconfig.base.json`, the built-page html-validate run, the sandbox fallback | test_citations.py |
| 142 | DOCS.066 | X | x | BACKLOG's chroot list: U28's paragraph (A.U28.38) from the relay | test_citations.py |
| 143 | SPEC.033 | X | x | B.10: sixteen jobs, the two composite actions, the cache key, the retried sync | test_citations.py |
| 144 | SPEC.034 | X | x | B.10.1: every job's shape (permissions, web-changes base, gating, picotool, coverage, the smoke, budgets after the re-measure) | test_citations.py |
| 145 | SPEC.123 | X | x | H.7.2: Xvfb for both engines, the verified downloads, `--require-all-engines`, the display by `-displayfd` | test_citations.py |
| 146 | TSC.079 | C | apply | `tests_scripts/test_device_tomls.py:208-213`'s matrix-equality test leaves (rule (7) of test_ci_workflow.py replaces it) | test_ci_workflow.py rule (7) red at b1fecfb |
| 147 | WEB.077 | W | verify | nothing at U28: `tsconfig.node.json:30` already includes `tests_js/_summary_reporter.js` | npm run typecheck |
