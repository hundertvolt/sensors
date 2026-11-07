E scan, written by the lane (Wed Oct 28 07:50:25 UTC 2026)

Part E covers tests and tooling, plus the website. Range `25caf528..497b3eda`, read in `S/wt-u35int` with `arduino/` excluded. Read-only: nothing was run or built.
Method: whole-file line counts at both ends (`git ls-tree` + `git show`), files grouped by name with the first matching rule winning, renamed
files mapped by hand. "Growth" means head minus base, in net lines. Commits are attributed with `git log --no-merges --numstat`. Rules are
cited by line from the worktree's `CLAUDE.md` and from `audit/CONSOLIDATION.md` (pillars P1-P12, lines 25-36). The helper script and the
classification rules are in `S/u35r/scan/E_work/` (`tools/classify.py`, `rules_*.tsv`).

## Headline

- **Growth.** The eight test and tool areas (website excluded) went from 105,942 to 232,891 lines: +126,949, or 2.2×. Files went from 328
  to 655. Product code grew much less over the same range: `src/` 13,214 → 16,678 (+3,464), `buildgen/` 3,681 → 6,227 (+2,546), and
  `js/`+`html/` 4,107 → 4,407 (+300). That is about **20 test/tool lines added per product line added**.
- **Split of the +126.9k:**

  | Class | Lines | Share |
  |---|---|---|
  | (a) tests that pin firmware, buildgen or website behaviour | +73.3k | 58% |
  | (c) harness infrastructure | +44.0k | 35% |
  | (b) machinery and convention gates born in the audit | +6.0k | 5% |
  | (d) CI | +1.6k | 1% |
  | build chain | +1.0k | |
  | docs inside these directories | +1.0k | |

  About **30k lines are tests whose subject is a tool**: a fake, a runner, the harness, CI or lint config, rather than the firmware.
- **Test functions:**

  | Area | Base | Head |
  |---|---|---|
  | `tests/` | 3,200 | 4,705 |
  | `tests_scripts/` | 1,017 | 3,014 |
  | `tests_hardware/` | 149 | 231 |
  | `tests_js/` | 192 | 453 |

- **Origin.** The tooling-only units (U7, U21, U24-U29, U35) add about +64.5k net here against about +500 product lines. U35's redo after
  the preliminary push (`656fc82f..497b3eda`, 233 commits) adds +14,156/−3,325 here against +281/−230 in the product.
- **CI cost.** The timeouts went from 45 to 175 minutes for both `unit-tests` and `unit-tests-gc-threshold`, and to 95 minutes for
  `unit-tests-coverage`. A warm run takes 9-10 minutes. The `digital-twin-e2e` matrix went from 6 to 24 jobs.

Per-unit growth in these areas compared with the product (net lines; tests and tools vs `src`+`buildgen`+`js`+`html`+`devices`):

| Unit | Tests/tools | Product | Unit | Tests/tools | Product | Unit | Tests/tools | Product |
|---|---|---|---|---|---|---|---|---|
| U0 | +2,120 | +2 | U13 | +4,173 | +590 | U24 | +5,885 | +33 |
| U3 | +1,596 | −22 | U15 | +3,284 | +512 | U25 | +9,643 | +26 |
| U6 | +2,048 | −1,159 | U17 | +2,272 | +267 | U26 | +14,304 | +54 |
| U7 | +4,512 | 0 | U18 | +3,277 | +281 | U27 | +5,096 | +35 |
| U8 | +2,331 | +143 | U19 | +2,881 | +451 | U28 | +2,049 | +2 |
| U10 | +3,325 | −21 | U20 | +6,105 | +1,919 | U30 | +5,289 | +416 |
| U11 | +4,208 | +236 | U21 | +4,336 | 0 | U31 | +1,769 | +70 |
| U12 | +842 | +74 | U22 | +1,987 | +79 | U32 | +972 | +83 |
| | | | U23 | +7,100 | +1,608 | U35 | +18,254 | +349 |

## Per area

### tests/: +76,142/−27,881 (62,532 → 110,793, +48,261)

| Class | Growth |
|---|---|
| (a) unit tests of `src/` modules (renames mapped: base 44,267 → 70,361) | +26,094 |
| (a) mock-tier integration and hazard suites (`_sensortask_scenarios.py` 1,294 → 3,918, bus/UART hazard) | +4,859 |
| (a) twin-tier firmware scenarios that boot the generated graph | +4,781 |
| (a) host lwIP tests of the shipped modlwip patch (`tests/lwip_host/`) | +540 |
| (c) self-tests of the twin fakes and runner (`test_digital_twin_machine.py` 539 → 1,769, `..._run_generic_integration.py` 290 → 1,221, chip fakes, `http_client`, `launch`) | +5,466 |
| (c) harness infrastructure (`machine.py` 707 → 1,551, `rp2.py` 245, `_fake_time.py`, `_async_harness.py`, `_cancel_sweep.py`, 26 new `_*.py` helpers) | +3,586 |
| (c) self-tests of the harness (`test_fakes.py`, `test_shared_helpers.py`, `test_driven_time.py`, `test_async_harness.py`, `test_microtest_hooks.py`, `test_untraced.py`) | +2,935 |
| (b) | none directly. About 2.5k lines of (a) were written to fill audit rows (CO1-5, IN+LV, CEr2, CFr/CFr2) |

**Keep:**
- `test_digital_twin_fram_crash_points.py`: power is cut after every SPI transaction of a chunk write. Added in U25 `311aef80`.
- `test_digital_twin_timer_pool.py`: rp2's 16-alarm pool running out. U25.
- `test_digital_twin_hot_replug.py`. U25.
- `test_digital_twin_held_i2c_line.py`. CO4 `a0ea910a`.
- `test_asy_webserver_connections.py`. U19 `f5c82557`.
- The compare-before-write tests in `test_asy_config_manager.py` (P9).
- The driven-clock rewrites that kept every assertion: the notification file went from 19.0 s to 0.19 s (`656fc82f`).
- microtest's ABORT line, which names a hung test (U24 `aa3530f7`).

**Excessive** (deep dives and campaigns):
- **Test size relative to the module tested:**

  | Module | Test lines | Module lines | Ratio | At base |
  |---|---|---|---|---|
  | `asy_udp_socket` | 1,935 | 172 | 11.2× | 1,659 test lines already |
  | `asy_captive_dns` | | | 6.9× | |
  | `asy_ntp_client` | | | 6.0× | |
  | `asy_system_service` | 4,761 (203 tests) | 813 | 5.9× | 1,427 lines, 86 tests |
  | `asy_wifi_service` | 5,254 | | 5.3× | |

- **Coverage chase:** CEr2 `1298e714`, "direct tests for every owed uncovered src line" (+619). CFr `ec7d7ea7` and CFr2 `2e826c28`, "direct
  tests for the plant survivors".
- **Filling audit-table cells:** CO1-CO5, 18 commits, +1,421 (e.g. `7303e4d0`, "U15's 33 rung rows get their cells"). IN+LV `d2e96297`
  maps each intent.md row to a biting test; its domain-edge sweep, `_schema_cases.py`, is worth keeping on its own.
- **Multiplying tests per device wiring:** CMr1-CMr1m, 30 commits, +2,190/−1,147 (e.g. `d87bd0d8`: the SCD30/SGP40 twin-bus tests run once
  per distinct wiring).
- **@tunable tagging:** N8-N11, 23 commits, +1,013/−487. `tests/` now holds 450 `@tunable` lines; there were none at base.

**Runaway** (tools testing tools):
- `test_shared_helpers.py`, 690 lines. Its header reads: "The shared test doubles and readers no consumer test pins yet".
- `test_driven_time.py`, 646 lines, for a 368-line `_fake_time.py`.
- The twin runner's argument and flag tests: 1,221 lines.

**Violations:**
- Owner, 2026-10-28 (brief): "The unit tests shall have good quality, but don't need deep dives". This is broken by the unit-tier depth and
  by the coverage, survivor and cell campaigns above.
- P8 "One source of truth, generated not copied" (`CONSOLIDATION.md:32`): there are two fakes of one port, `tests/machine.py` and
  `digital_twin/machine.py`. They are held equal by `_machine_contract.py`, `_mem_backup_contract.py` and `test_fake_surface_conformance.py`.
- No violation found in `tests/` of:
  - P4 "nothing in the product for tests" (`:28`): fakes and write counters stay outside `src/`.
  - P9 and the host-I/O wear rule (`CLAUDE.md:323`): `test_tmp_scratch.py`'s structural fix holds.
  - "hanging tests are never allowed" (`CLAUDE.md:770`): `run()`/microtest end every task and name a hung test.

### digital_twin/: +6,416/−2,531 (4,443 → 8,328, +3,885)

| Class | Growth |
|---|---|
| (c) board fakes (`machine.py`, `network.py`, `neopixel.py`, `rp2.py` 249, `_flash_stall.py`, `_fault_injection.py`) | +1,412 |
| (c) runners (`launch.py`, `run_generic_integration.py` +870, `run_device_script.py`, `_twin_common.py`) | +1,270 |
| (c) driven clocks and Unix-port shims | +486 |
| (c) chip fakes | +380 |
| README (docs, part F) | +327 |

**Keep:** the port-fidelity work behind OR17.a: the alarm pool, the DMA fake, held lines, and the FRAM corruption knobs. It came mainly from
U25 `311aef80` (+3,939/−2,273) and U13 `cbb65df2`.

**Runaway:** `_driven_clock.py` (190), `_wall_clock.py` (82), `unix_port_idle_poll.py` and `unixport/_unix_port_udp_addr_shim.py` (143)
exist to speed up or isolate the tests that the CMr1 and N15 lanes widened. Each got its own self-test: `test_digital_twin_driven_clock.py`
(287), and `test_digital_twin_unix_port_idle_poll.py` (80, `6f41678e`).

**Violations:**
- P4 is kept: the twin-only `--test-*` flags are pinned off by `test_twin_runner_test_flags.py`.
- The host-I/O wear rule (`CLAUDE.md:323`) is kept: the twin saves its FRAM state once, at shutdown (`digital_twin/machine.py:1358-1362`).
- P8 (`CONSOLIDATION.md:32`) is broken by the second fake of the same board (above).

### tests_scripts/: +48,801/−5,454 (14,529 → 57,876, +43,347; 65 → 212 files)

| Class | Growth |
|---|---|
| (a) buildgen | +6,081 |
| (a) image chain and twin boots of the built image (`build_firmware`, `stage_website`, stripped image, FRAM-less boot, boot contiguity, `micropython_overrides`) | +3,715 |
| (a) whole-tree static contracts over `src/` (error catalog, exception handler, watchdog feed sites, lock order, import graph, task tops, write sites, await depth, ticks wrap, readiness, setter and counter rules; 36 new files). About 1,700 lines of this pin `SPECIFICATION.md` tables: tunables register, timing budget, lock and task tables, memory catalog, threat model, UART changelog | +10,551 |
| (b) docs policing born in the audit (`test_citations.py`, `test_decision_vocabulary.py` plus its 393-line allowlist, comment cap, legacy paths, `_repo_scan.py` plus 3 tests of the scanner) | +2,053 |
| (b/d) lint and tool config gates (lint ceilings, ruff exemptions still firing, mypy Any baseline, lint/type scopes, tool and script pins, suppression form, shell conventions, tool `--help`, host idioms, clone check, const mirrors) | +2,275 |
| (c) tests of the runners and tools (`test.sh`, `setup_toolchain`, port lock, `_unix_port.sh`, summary block, `typecheck.sh`/`lint.sh`, hardware runners, `require_*`, cross-browser) | +6,751 |
| (c) offline tests of the hardware harness (bench log check, harness helpers, device-script facts, run record, verdict, twin record) | +5,853 |
| (c) tests of the twin harness (twin CI suite ×5, scenario frame, twin wiring/board/process, level containment) | +4,005 |
| (c) tests of the unit-tier runner (microtest, coverage and threshold runners, generated tree, port bands, session guard) | +1,038 |
| (d) CI (`test_ci_workflow.py`, `test_ci_apt_cache.py`) | +821 |

**Keep:**
- `test_firmware_write_sites.py` (P9, `656fc82f`).
- `test_buildgen_error_contract.py` and `test_buildgen_fuzz.py` (U20 `f76385a6`).
- `test_lock_order.py` and `test_watchdog_feed_sites.py` (U10 `41b47f1d`).
- `test_js_api_mirrors.py` (the web/firmware contract, U23).
- `test_frozen_inputs_reproducible.py` and `test_buildgen_reproducible.py` (P11).
- `test_stripped_image_boots.py`.

**Excessive:**
- The static-contract layer grows with every unit: U30 `06a8ae5d` added `_await_depth.py` (909 lines, plus a 207-line test), U31 added the
  timing budget, U32 the task tops.
- 100 "bite/planted" self-tests in 58 files prove that each check fails on a planted fault. Examples: "the tag oracle bites", "a planted
  violation fails its rule".

**Runaway** (tools testing tools):

| Test | Lines | Tool under test | Lines |
|---|---|---|---|
| `test_test_sh.py` (155 tests) | 2,530 | `scripts/test.sh` | 1,231 |
| `test_micropython_overrides.py` | 2,126 | overrides | 1,115 |
| `test_setup_toolchain_env.py` | 2,021 | `setup_toolchain.py` | 1,850 |
| `test_port_lock.py` | 531 | the lock | 270 |
| `test_digital_twin_ci_suite_{errcount,soak,ceiling,matrix,state}.py` | 1,834 | the suite script | 1,928 |

The repo scanner used by the doc gates has its own tests: `test_repo_scan_template_literals.py` (N13 `e54fcc47`) and
`test_repo_scan_regex_literals.py` (N12 `d782b65e`). `test_ruff_exemptions_live.py` runs ruff with every exemption lifted, to prove each one
still fires.

**Violations:**
- Owner, 2026-10-28: "The audit verification machinery is just a temporary tool". The docs-policing gates and the ~1,700 lines that pin
  `SPECIFICATION.md` tables are permanent CI that came out of audit rules.
- `CLAUDE.md:516` ("current state, not the historic path"), together with the owner's "Docs to be consolidated". Every doc consolidation now
  moves CI-checked text: 11 test files read `SPECIFICATION.md`, and `_decision_vocab_allowlist.txt` was touched by 34 commits.
- P8 (`CONSOLIDATION.md:32`): checks keep copies equal instead of generating them. Examples: `test_summary_block.py` (three emitters,
  byte-identical), `test_http_client_shape_parity.py` (the twin and hardware HTTP clients), `test_isl29125_copies.py`,
  `test_definitions_js_mirrors.py`.

### tests_hardware/: +22,996/−9,379 (13,911 → 27,528, +13,617)

| Class | Growth |
|---|---|
| (a) device scripts, run on the board (56 → 102) | +4,885 |
| (a) bench tier | +2,145 |
| (a) flash tier | +1,532 |
| (a) manual | +477 |
| (c) harness (`harness.py` 501 → 984, `conftest.py` 270 → 598, `bench/_load.py` 504, `bench/conftest.py` 201, `bench_facts.py`, `evidence.py`, `markers.py`) plus `twin_board.py` | +2,436 |
| (b) `twin_record.json` (OR21.a's twin-run record for each instrument) | +1,466 |
| README | +676 |

**Status:** the twin record lists 122 instruments. 67 pass in the twin and 55 cannot run there; 19 of those need the bench bridge. Going by
commit subjects, silicon was run only on the first day (`2f48f862` G12, `6f7eef7e` F1/N2). Everything after that is waiting for a hardware
session.

**Keep:** the silicon pins of the recovery ladder, reset codes and the UART read that never blocks. Examples:
`uart_driver_read_never_blocks_the_loop.py`, `reset_code_stack_exhausted.py`, `i2c_held_sda_recovery.py`, `flash/test_system_commands.py`.

**Runaway:** the CRr2 chain (25 commits: +1,526/−355 here, +1,649/−1,023 in `audit/`). It started with one gate, `59021b11` ("the bench tier
fails a test that leaves an E or W entry it was not marked to provoke"). Eleven sub-lanes then refitted each bench test's expected-entry sets
and wait windows (`c12d1bd6`, `171144df`, `fc6f42a6`, `2a7a3a72`, ...). None of these bench tests has run on silicon. Tests_scripts also
holds 5,853 lines of offline tests of this harness, which are tests of tests that have not run yet.

**Violations:**
- None of the gates is broken:
  - the go-ahead rule (`CLAUDE.md:368`);
  - P9's `persistence_write` and `flash_cycle` gates (`CLAUDE.md:323`);
  - the marking of owned writes (`device_scripts/config_files_restore.py:28`, `system_command_config_reset.py:59`).
- P5 "tests that bite at every layer" (`CONSOLIDATION.md:29`) is unproven for this tier: the tests are written and twin-run where possible,
  but have not run on silicon.

### tests_js/: +8,973/−1,504 (4,697 → 12,166, +7,469)

| Class | Growth |
|---|---|
| (a) site tests (render, templates, shell, mock-server, poll-manager, definitions, nav, accessibility, site-functions, put matrices) | +5,247 |
| (c) live-tier command modules (`_live_twin_command.js` 703, `_live_matrix_command.js` 413, `_twin_process.js` 300) | +800 |
| (c) JS copies of the shell/Python harness, with their tests (`_port_lock.js` 402, `_summary_layout.js`/`_summary_reporter.js` 282, `_memory_markers.js` 174, `_micropypath.js`, `_source_constants.js`, lint-ceilings) | +1,406 |

**Keep:**
- `accessibility.test.js`: 42 of its 45 cases failed on the tree before (U23 `9bf22747`).
- `site-functions.test.js` and `shell.test.js`.
- The mock speed-up: `mock-server.test.js` went from 47.8 s to 3.3 s.

**Violations:** P8 (`CONSOLIDATION.md:32`). `_port_lock.js` is a 402-line Node reimplementation of `scripts/_port_lock.sh`'s contract, and
`_summary_layout.js` is "byte for byte the one" the sh/py emitters produce.

### scripts/: +10,853/−2,122 (3,451 → 12,182, +8,731)

| Class | Growth |
|---|---|
| (a) L2 twin scenarios driven over HTTP (`_digital_twin_scenarios.py`, new) | +2,432 |
| (c) unit runner and lint (`test.sh` 557 → 1,231, `_unix_port.sh` 315, `_check_gc_collect_sites.py` 375, `_require_*`, `uv_sync_retried.sh`) | +1,569 |
| (c) twin runners (`_digital_twin_ci_suite.py` 1,326 → 1,928, `_twin_process.py` 485, `run_*`) | +1,234 |
| build chain (`_stage_website.py` 507, `build_firmware.py`, `_generate_sensortask_modules.py`, `_strip_type_checking.py`) | +955 |
| (c) reporting, locks and archive (`_summary_block.sh`/`.py`, `_port_lock.sh`/`.py`, `_archive_evidence.py`) | +801 |
| (c) web tooling | +528 |
| (c) hardware runners (`_hardware_verdict.py`, `_pytest_run_record.py`, `_run_lower_levels.sh`) | +515 |
| (d) `ci_apt_cache.py` | +466 |
| (b) `record_twin_instrument_runs.py` | +231 |

**Keep:** `_stage_website.py`, and `_archive_evidence.py`, which keeps three runs (SSD wear; owner, 2026-09-26).

**Runaway:** the reporting chain. U7 `40a3508f` added a summary block in sh, py and js. U26 `0c0ad52c` added a run-record plugin and a
verdict on top. That is about 700 lines of scripts, plus about 1,580 lines of tests and JS copies.

**Violations:**
- P8 (`CONSOLIDATION.md:32`) is broken: `_summary_block.py` is "byte-identical to scripts/_summary_block.sh", and the port lock exists as
  `.sh`, `.py` and `.js`.
- The hang rule (`CLAUDE.md:770`) is kept.

### toolchain/: +2,220/−878 (1,689 → 3,031, +1,342)

- `setup_toolchain.py` went from 1,171 to 1,850 lines (U21 `65088dec`): bounded, streamed and retried installer steps, a toolchain lock and a
  build record.
- `micropython_overrides.py` went from 466 to 1,115 lines and gained three overrides:
  - **`modlwip_eagain`:** a patched copy of `extmod/modlwip.c` built into every firmware image. It carries three patches:
    - the send-path EAGAIN (owner, 2026-09-30);
    - closing a listener without callbacks (owner, 2026-10-26; F4a `4de10081`);
    - allocating the accept queue first (agent, 2026-10-26, under the owner's ruling).
  - **`tick_offset`:** only for the bench rollover image (owner, 2026-10-01).
  - **`unix_lwip_host`:** a host test binary.
- **Flag:** this area carries product C code that ships in every image. All of it was decided by the owner except the third modlwip patch.
- **Tests vs code:** the tests are larger than the code they test (2,126 + 2,021 lines). No pillar violation found.

### .github/: +590/−293 (690 → 987)

All of it is (d):
- the `ci.yml` rework (U28 `8ad2bb37`: one retried sync, device matrices derived from the TOMLs, pinned tools);
- composite actions `uv-sync`, `playwright-chromium`, `apt-cache-restore` and `apt-cache-save`.

The apt cache came from the CI1 lane (`bd004254`, `3b9b2e72`; +1,307/−180 across three areas). It fixes a real slow-mirror fault, upstream
actions/runner-images#14823.

**Cost:**

| Job | Timeout before | Timeout now |
|---|---|---|
| `unit-tests` | 45 min | 175 min |
| `unit-tests-gc-threshold` | 45 min | 175 min |
| `unit-tests-coverage` | 45 min | 95 min |

The `digital-twin-e2e` matrix went from 6 to 24 jobs (device × GC stage × part). The 175 minutes are a warm 9-10 minute run plus the retry
budget of one hung scenario job: 3 × 2,555 s ≈ 128 min (`SPECIFICATION.md:13318`, `:13331`). The 2,555 s per attempt is 5× the slowest CI
run (511 s).

**Strain on the hang rule:** "hanging tests are never allowed" (`CLAUDE.md:770`) is kept in letter. In practice, a hung job runs for two
hours before it is named.

### Website: js/ (+3,034/−1,198; 1,956 → 3,792) and html/ (+108/−1,646; 2,151 → 615)

**What changed in the code:**
- `html/definitions/*.json` (1,624 lines) became buildgen output (U6 `1b59a05d`, P8: a good change).
- `js/` nearly doubled:
  - `shell.js` is new (181 lines);
  - `templates.js` +549, `render.js` +340, `definitions.js` +273;
  - `api-contract.js` is new;
  - `mock-server.js` +307 (it is never staged into the image).

**Behaviour changes it carries,** all frozen into every image:
- **Agreed with the owner:**
  - confirmation dialogs for system commands, the error reset and the DNS-fallback Clear (owner, 2026-10-01);
  - per-value decimals, with a site default of 2 (owner, 2026-10-02);
  - "Time May Be Stale" from the new `/status` `TimeStale` (owner, 2026-10-21; `656fc82f`);
  - dev's MPRLS/SHTC3 cards dropped (owner, 2026-10-13).
- **Originated by the agent or the audit** (the U23 message, `9bf22747`, quotes no owner for these):
  - a shell that polls the device every `web.device_watch_interval_ms` and reloads the page on a new firmware build, now with a check of
    the page's build date against the image's (`c56b366b`);
  - a `#section` history with Back;
  - polling that pauses in a hidden tab and backs off to `web.poll_backoff_max_ms`;
  - ages read against the device clock ("age unknown", "clock mismatch");
  - a Device Clock row, with `UnixTime` newly added to every `/status`;
  - code buttons with tones, a Clear button, and an ignored-when-set warning;
  - cards updated in place;
  - a section switch that waits for the previous section's in-flight GET (about 210 ms more);
  - a banner for a GET that does not return an object;
  - an inert drawer, AA colour tokens, and reduced motion.

**Violations:**
- `CLAUDE.md:508` ("the same top-level features … not a feature change"), together with the owner's "Agreed on new features being added".
  The agent/audit list above consists of new features with no recorded owner agreement; U23 logs several of them as "decided on the owner's
  behalf … for review".
- P6 "Efficient and compact" (`CONSOLIDATION.md:30`): `js/` grew 94% in lines and is frozen into every image. I found no before/after size
  of the site.
- P4: no test-only code in `js/`. Three exports serve the tests, but each is also used inside its own module.

## Totals by class (eight test/tool areas, +126,949)

| Class | Lines | Where |
|---|---|---|
| (a) pins firmware, buildgen or website | +73.3k | tests 36.3k, tests_scripts 20.3k, tests_hardware 9.0k (not run on silicon), tests_js 5.2k, scripts 2.4k |
| (b) audit-born machinery and convention gates | +6.0k | docs policing 2.1k, lint/tool gates 2.3k, twin record 1.7k |
| (c) harness infrastructure and its self-tests | +44.0k | tests_scripts 17.9k, tests 12.0k, digital_twin 3.5k, scripts 4.6k, tests_hardware 2.4k, tests_js 2.2k, toolchain 1.3k |
| (d) CI | +1.6k | |
| build chain | +1.0k | |
| docs in these directories | +1.0k | |

Inside (a), about 2.5k lines fill audit rows and about 2.2k come from widening tests to every wiring. Tests whose subject is a tool account
for about 30k lines across (b)+(c)+(d).

## Runaway areas and chains

1. **Driven-clock and per-wiring chain** (U35 CMr1, CMr1b-m; 30 commits, 2026-10-27/28; +2,190/−1,147; 0 product lines). The steps:
   - widening the twin tests to every device wiring (`7f1ba012`, `149d145d`, `d87bd0d8`) made them slow;
   - so they moved to driven clocks (`3658034b`, `621350ed`);
   - then an idle-poll skip was added (`02506cc5`, `7534a51a`), with a test of the skip (`6f41678e`);
   - the widening exposed leaks of parked tasks, which led to a single-task countdown in the twin watchdog (`45cf7b4a`) and a drift floor
     that builds no waiter (`7007e45f`);
   - finally, device-pick record rows (`4cf293d0`, `34380155`).
2. **Bench log-check chain** (CRr2, CRr2a/a2/b/b2-b12; 25 commits). One gate (`59021b11`) was followed by eleven lanes refitting the
   expected-entry sets and windows of bench tests that have never run on silicon.
3. **Port-isolation chain** (about 2,000 lines including tests). It started from `CLAUDE.md:905`'s "run the two tiers one after the other".
   It became:
   - a lock in three languages (U24 `aa3530f7`);
   - port bands (U25 `tests/_port_bands.py`, with its own test);
   - per-process loopback addresses (N15 `d57fbb41`: the shim and `test_twin_host_isolation.py`);
   - an entry-point-order test (`test_twin_entry_point_order.py`).
4. **Runner-reporting chain** (about 2,300 lines including tests): the summary block (U7 `40a3508f`) in sh, py and js, held byte-identical
   by tests; then the run-record plugin and the verdict (U26 `0c0ad52c`); then the manual runner's summary.
5. **Tagging chain:** the `@tunable` scheme (U8 `01e8e3eb`, asked for by the owner on 2026-09-25) was carried over every test sleep and
   bound by N8, N9, N10, N11 and N11b-e (23 commits, +1,013/−487). There are now 1,249 `@tunable` lines in these areas (0 at base), each
   with a Part N row and pinned by `test_tunables_register.py`.
6. **Coverage-machinery chain:** a coverage-tracer guard (CE2r `fef0321a`, `_untraced.py` with its test), then CEr2 `1298e714`, which wrote
   tests for every uncovered line that `audit/b3/e51.md` still owed. Alongside sits `test_coverage_runner.py`: 368 lines for a 159-line
   runner.
7. **Repo-scan chain:** `_repo_scan.py` was built for the doc gates (U0 `8104062d`). Its JS-comment reader then got fixes and tests for
   template literals and regex literals (N12 `d782b65e`, N13 `e54fcc47`).
8. **Twin-record chain** (U26 `0c0ad52c`, about 2,260 lines): `record_twin_instrument_runs.py`, `twin_record.json`, `test_twin_record.py`,
   `twin_board.py` and `test_twin_board.py`. All of it records whether each hardware instrument has a current twin run.
9. **Tests larger than the tools they test:** see the table under tests_scripts. Add `tests/test_shared_helpers.py` (690 lines), for
   helpers that, in its own words, "no consumer test pins yet".
10. **Self-bites:** 100 tests in 58 tests_scripts files prove that a check fails on a planted fault, which amounts to a test of each test.

**Caveats:** nothing was run. Wall-clock figures come from Part N rows and commit messages. Whether a hardware instrument ran on silicon was
judged from commit subjects only. The class boundaries are drawn per file, not per test function.
