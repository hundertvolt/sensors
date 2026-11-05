R3 row table, written by the agent (Wed Nov  4 16:16:51 UTC 2026)

Read-only, on `S/wt-r3` at `17688315` (R2 merged). Nothing was run, built or edited. `S` is the scratchpad.
Line references are to that head. "measure in phase B" marks a time no record holds.

## Totals

- Rows: 25. These are the 19 group-B3 owner rows, OR26 (PLAN's R3 bullet with OR22-OR25), U35's 09, 37 and 52,
  the bus-hazard rule and the wear table.
- Met on the final tree: 7 (OR20, OR36, OR40 for R3's part, OR45, OR55, OR77, OR79).
- Remaining: 18. Every remaining item is reading, a static walk or one measured run. None needs a source change.
- Limits for the owner: 3 sentences (OR19, OR39, OR29.a (2)'s datasheets); their rows also count as remaining.
- Remaining machine runs: 7, about 3 to 5.5 h in all:
  - the static walks and a collection check, about 5 min;
  - one coverage run, 25-35 min (estimate; CI took 16:54 at R0);
  - one plant run, measure in phase B (estimate up to 1.5 h);
  - the twin instrument runner, both stages, measure in phase B (bound: 3,600 s per stage for the flash run, plus
    the device scripts);
  - one per-file heap probe, about 12 min (one unit-tier stage);
  - the twin side of the bench probes, about 10 min;
  - R3's gate if anything is committed, about 50 min (test.sh 700-727 s per stage, twin dev 600-627 s + 57 s per
    stage, from R2's gate).
- What it adds:
  - certain: OR49.a (1)'s two L2 load tests from LD+CM3's patch, about 114 lines and no new file;
  - only where phase B finds a real gap: up to 7 kinds of test (A3-A9 below), expected few or none;
  - fidelity-table rows in an existing table.
  - Not recommended: re-committing the twin record and its test (about 1,600 lines; PLAN's text, not the row's).
  - Every working record goes under `S/u35r/r3/`. The committed `audit/b3/*.md` copies stay as they are until D.
- Marks: 2 "owner" (conditional, both below) and 10 "adds" (1 certain, 1 PLAN-only, 7 conditional, 1 doc rows).

## 1. The rows

### OR16, silently broken chains (OR16.a (1)-(4)): remaining
- (1) The twin boots every device: met.
  - CI runs `digital-twin-e2e` for each derived device × [-1, 32768] (`ci.yml:567-569`, 12 jobs since R2).
  - `test_sensortask[<device>]` passes 101/101 for all six devices (`S/u35/lead/r2x_gate2_unit.log`).
  - The lead reads snapshot 34's CI (`d14239ce`).
- (2) Collection and skips: met by the runner.
  - `scripts/test.sh`'s summary names every skip and deselect with its reason (R2's final gate: 80 skipped files,
    6 deselected, "Checked nothing: none").
  - Remaining: read that list once for reasons still valid (tokens), and run `pytest tests_hardware
    --collect-only` once (seconds) for the hardware markers.
- (3) Coverage: remaining.
  - One `--coverage` run on the final tree: 25-35 min locally (estimate), or snapshot CI's artifact.
  - Each new unexecuted line is classed feature, guard or dead (`audit/sweeps/e51_sweep.py`, `e51_verdicts.json`).
  - A dead line is listed, not removed: **owner** (the owner, 2026-10-23: "Double check it's really dead code").
- (4) Fault planting: remaining.
  - `audit/b3/faults.md` (153 rows, `2e826c28`) carries over where the planted site is unchanged.
  - `plant.py` over `plant_set.py` on the final tree shows which regexes no longer match. Those sites are replanted
    only in the owner's scope ("complex measurement tests", 2026-10-23).
  - Time: measure in phase B. A surviving fault is a gap: **adds** (A3), OR16.a (4).

### OR19, biting tests: remaining, with a limit
- `audit/b3/review.md` has 8,673 rows (`98d8b71d`). R1 recorded no verdicts.
- Since `497b3eda` the hunks touch about 1,100 test-function contexts; 117 `def test_` lines were added.
- Work: `redflags.py` and `review_rows.py` on the final tree (seconds), output in `S/u35r/r3/`.
- A verdict for every flagged row whose test or target changed (estimate up to 100 rows, tokens).
- A weak test is strengthened in place, its goal kept (OR12).
- **Limit for the owner:** a test that is unchanged but whose target R1 changed keeps the scan's verdict and its
  green gate, not a fresh human read. That covers most of the 5,824 unit tests, too many for R3's share.

### OR20, test placement and isolation: met
- `SPECIFICATION.md:5995` (E.9 Driver/DUT process separation).
- The twin scenarios run host-side (`scripts/_digital_twin_scenarios.py`).
- R2 removed the twin knobs that only their own tests read (`b315f98b`). It restored the BMP3xx EVENT model, which a
  probe reads (`14ed9e5e`).
- The business-logic half is OR36's row.

### OR21, silent test blindness: remaining
- (3) Met: the summary block reports skipped, deselected, gated and "Checked nothing".
- (2) No new control arms: honoured.
- (1) R1 and R2 already turned their own check-style tests red:
  - R2's F2 plant (`r2x_f2red`) and the held-port plants (`r2x_dns_bind`);
  - the loop-end test, red 4/5;
  - B-units' test-first reds.
- Remaining: list the other check-style tests whose subject changed since `faults.md` and trigger each once, in
  OR16's plant run (no extra run). The hardware half is OR29.a (4).

### OR22, tests for generated code: remaining (small)
- Met:
  - the per-device tests (`test_sensortask[<device>]` × 6);
  - `tests/test_generated_boot_entry.py`;
  - the website definitions under `tests_js/`;
  - the frozen HTML (`tests_scripts/test_stage_website.py`).
- Generated code is traced (`tests/_coverage_runner.py:24`, `build/generated_src/`).
- Remaining: read `htmlcov_generated` from OR16's coverage run. A real gap: **adds** (A4), OR22.a (2).

### OR23, tests for buildgen: remaining (small)
- Met: the host coverage (`scripts/test.sh:495`, `--source=buildgen,scripts,toolchain`; rendered at `:1112-1114`).
- B8's ~260 removed build checks left with their tests.
- Remaining: read `htmlcov_host` from the same run; an unexecuted error path gets a test or a reason. A real gap:
  **adds** (A4), OR23.a (3).

### OR25, intent at every layer: remaining
- `audit/b3/levels_walk.py` renders `intent.md` and `levels.md`, last at `497b3eda`.
- Re-render on the final tree (seconds, after `rebuild.sh`) into `S/u35r/r3/`, then read the changed rows:
  - removed mechanisms drop out (the subtraction);
  - an unmapped item gets a test: **adds** (A4), OR25.a (2).
- (3) is OR16's coverage run.

### OR26, no uncaught exceptions (PLAN's R3 bullet): remaining
- `audit/b3/raising_walk.py` (seconds) for the src modules R1 changed (28 files since `497b3eda`).
- Hand verdicts for the new raise and call sites, a working copy under `S/u35r/r3/`.
- A defect counts only with a reproduction, then gets its regression test: **adds** (A5), OR12.a.

### OR29.a (4), every hardware test once against the twin: remaining
- One run of `scripts/record_twin_instrument_runs.py`, which covers both stages itself (`GC_THRESHOLDS`, `:39`).
- Its reasons JSON: the 35 reasons in `S/u35r/knowledge/twin_record_exceptions.md`, plus the held SDA (E.6.6's
  `held-i2c-line-silicon` row).
- Time: measure in phase B, bounded by `_FLASH_RUN_TIMEOUT_S` (3,600 s per stage) plus the device scripts.
- It writes `tests_hardware/twin_record.json`. Phase B moves that file to `S/u35r/r3/`, so the tree stays clean.
- The row is met by the run plus its listed exceptions:
  - the owner's "ok" `twin-first-for-instruments` (`audit/review/decisions.json:1141-1151`) names the committed
    runner, which stays, and listed exceptions, not a committed record;
  - PLAN's "the record and its test are committed again" would restore the ~1,600 lines R0 removed (`ffdee74e`):
    **adds** (A2), PLAN only, not recommended.
- Expected reds:
  - the mid-erase cuts, now `_MID_ERASE_RESETS_MS = (50, 150, 250)` (`flash/test_system_commands.py:48`, B3);
    R2's carry saw `[1000]`/`[2000]` fail against a ~1,064 ms twin erase;
  - the held SDA.
- Each reproduced red goes to the hand-back as (a), (b) or (c).

### OR36, production image purity: met
- R1 removed test-only product code (PLAN R1: the `setup()` bools, the `deinit()`/`set_level()` bools,
  `set_utc_valid(valid=)`, `_shutdown_task`).
- The row's three examples are gone:
  - `_NTP_UDP_PORT = const(123)` (`asy_ntp_client.py:73`);
  - the link's `self._uart` is private (`asy_uart_link_driver.py:82`);
  - the ISL29125 driver takes no address (`asy_isl29125_driver.py:216`).
- BMP3XX's `address=0x77` (`:422`) is the chip's SDO-selectable address, a hardware function (OR36.a (3)).
- The seam grep over R1/R2's additions is part of OR37's pass.

### OR37, harmful constructs and races: remaining
- The passes of units U10-U35 stand (PLAN 0).
- Since `497b3eda`, R1 and R2 added about 3,700 lines in `src/`, `buildgen/`, the test directories, `digital_twin/`,
  `scripts/` and `js/`.
- Work: read those additions once, and pattern-scan the whole tree (mass files, unbounded loops and retries, fixed
  ports, unguarded destructive host steps). Tokens, and grep in seconds.
- A race needs a forced interleaving as its proof: **adds** (A6), OR37.a (3).
- R2's falsifier found one and it is fixed (`d974aa9d`).

### OR38, hygiene and isolation: remaining
- The same pass as OR37 covers leaked sockets, timers, tasks and temp dirs, and shared ports or names.
- Plus the per-file live-heap probe from R1's B36 (snapshot 29's leak):
  - one pass over `tests/`, about 12 min (one unit-tier stage);
  - a fix only where a file grows per test.
- Two R2 carries are not R3 work; they go to the findings list:
  - `run_digital_twin_ci.sh --only` reaches the suite's runs only, not the harness scenarios (`:51` →
    `_digital_twin_ci_suite.py:352`);
  - a missing `ss` prints "command not found" (`:105`, `|| true`).

### OR39, speed and footprint: remaining, with a limit
- (1) Met: `tests_scripts/test_gc_collect_sites.py` with SPEC I.4(f.1).
- (2)(3) Remaining: the final per-tier wall clock, from R3's gate and the final snapshot's CI, set against R0's
  `S/u35r/r0/ci/jobs.tsv`. No extra run. R0's times:
  - unit-tests 11:55, the gc-threshold job 12:46, coverage 16:54;
  - 24 twin jobs, median 9:57 (12 jobs now).
- Peak RSS comes from the same gate runs (`/usr/bin/time -v`; measure in phase B).
- **Limit for the owner:** no peak RSS was ever recorded before (`audit/b3/timing.md`'s table is empty and R0 kept
  wall clock only), so footprint is reported as an after-figure only.

### OR40, GC discipline and the two stages: met (R3's part)
- (1) `test_gc_collect_sites.py` covers `src/` and generated code; the boot entry sets `gc.threshold(32768)` once.
- (2) Both stages run:
  - the unit tier: `unit-tests` and `unit-tests-gc-threshold`;
  - the twin tier: `ci.yml:569`;
  - R2's gates passed at both.
- (3) The two-image proof belongs to the last round, not R3.

### OR41, recombination and concurrency: remaining
- `audit/b3/matrices.md` (`34380155`) holds only the device-pick sites; its actor × resource table is empty.
- Work, a reading aid under `S/u35r/r3/`: for each actor × shared resource, a reason or an existing test (the
  bus-hazard set, `test_uart_comm_hazard`, the per-device web-server concurrency files, the recombination scenarios).
- A real interaction with no test: **adds** (A7), OR41.a (2). Expected few or none. Tokens only.

### OR45, test levels build on each other: met
- One ladder: E.6.1 (`SPECIFICATION.md:5681`).
- Execution containment: `scripts/_run_lower_levels.sh` runs both stages and stops before the board.
- `--skip-lower-levels` is never clean (`run_flash_hardware_suite.sh:13`, exit 4).
- Scenario containment: `tests_scripts/test_level_containment.py` against E.6.6 (`:5783`), green at R2's gate.
- (4)'s matrix is `levels.md`, re-rendered in OR25's walk.

### OR49, load limits: remaining
- `audit/b3/load.md`'s table is empty (`656fc82f`).
- Work: one cell per finite resource, naming a test or a reason (working record, tokens). The resources: heap,
  sockets, tasks, the soft-IRQ queue, the alarm pool, bus locks, log slots, UART buffers, CPU against the watchdog,
  request rates, DNS, and malformed or oversized input.
- PLAN's two tests from `S/u35r/paused_pub/lane_ldcm3.patch.gz`: **adds** (A1), OR49.a (1):
  - `a_dns_flood_leaves_the_captive_dns_answering_and_logs_nothing`: about 35 lines in
    `scripts/_digital_twin_scenarios.py`, needs exclusive port 53;
  - `test_a_full_scheduler_queue_loses_every_soft_callback_for_a_spell_and_every_timer_fires_again`: about 79
    lines in `tests/test_digital_twin_timer_pool.py`.
- Only their L2 cells are new:
  - L1 exists: `test_asy_captive_dns.py:149`, `test_asy_wifi_service.py:4025`;
  - L4 exists: `bench/test_hotspot_role_reversal.py:219`;
  - the twin's queue drop is pinned at the model (`test_digital_twin_machine.py:1560`).
- The flood joins the exclusive-port-53 leg, so each of the 12 twin jobs grows by about one boot (R2: 54.5 s).
  `digital-twin-e2e`'s timeout row (`433d53b2`) is then re-derived.
- The entries for OR49.a (3) go into R5's final report.

### OR55, gc.collect() is complete on return: met
- `SPECIFICATION.md:9302` states it.
- No "next line" wording is left in CLAUDE.md or SPEC (git grep). `test_gc_collect_sites.py` holds the sites.

### OR77, bench fault injection: met (R3's part)
- Each candidate's two-part verdict is an E.6.6 row with its reason (`SPECIFICATION.md:5783-`).
- `off-subnet-spoof` reads "L4 until its first bench run".

### OR79, try the DNS fault injection: met (R3's part)
- `bench/test_hotspot_role_reversal.py::test_spoofed_off_subnet_source_address_is_ignored` no longer skips.
- Its attempt is round 1's (C.md's OR79.a action).

### U35-09, the owner's two twin recombinations: remaining (tokens)
- (2) Met: `survives_bus_and_api_load_while_ntp_is_unreachable` and `..._with_concurrent_config_writes`
  (`scripts/_digital_twin_scenarios.py:1404`, `:1410`, `656fc82f`).
- They run per device at both stages in `scripts/test.sh`'s scenario tier.
- (1) The recombination × level row goes into OR41's matrix:
  - L1 has no reset and no network;
  - L3 has no network;
  - L4 is `bench/test_bus_concurrency_under_api_load.py`.

### U35-37, normal situations accepting a logged code: remaining
- Re-run in OR19's scan: `redflags.py`'s `ns_seed_text` and `ns_allow_list` flags (37 + 2 rows at `98d8b71d`).
- Each new hit is classed (a), (b) or (c).
- (a) means the product prints only, which removes a code a user sees in `/status`'s `errcount`: **owner**, only if
  a hit occurs.

### U35-52, every recovery rung at every level: remaining
- `audit/b3/conformance.md`'s 120 rung rows (built at `e83504cb`, reviewed 2026-10-27) predate R1's changes:
  - B2's smaller ladder;
  - B3's lost-FRAM chain, now gone;
  - B4's single clock-out routine.
- Work: drop the removed rungs, then re-check the cells of the rungs that stay against today's tests (tokens,
  working record).
- A missing cell: **adds** (A8), OR113.a (2).

### Bus-hazard rule, for the final tree's bus-facing changes: remaining
- `conformance.md`'s section is empty.
- The changes to check:
  - B3: the FRAM SPI clock, 1 → 8 MHz. The twin does not model baud (fidelity row). L3 is round 1's overnight
    `long_fram.py` plus the flash-tier FRAM read/write case.
  - B4: one clock-out routine, the I2C "no bus" contract gone, BMP3XX back to its STATUS poll, the ISL29125 shadow
    compare, the SGP40 restart back to the restore.
  - B6: `_rx_stop()`, under the UART four-tier rule.
- Each change needs three kinds × four tiers, named from the existing files (tokens).
- A missing cell: **adds** (A9), the CLAUDE.md hard rule.

### Wear table: remaining
- One table: each hardware test that writes the flash FS or the SCD30 NVM, or reflashes, marked owned or
  prerequisite, with its marker.
- The markers live in `tests_hardware/conftest.py`. `test_persistence_write_marker_completeness.py` was green at
  R2's gate.
- R1 and R2 changed 120 `tests_hardware/` files, mostly by removing Part N tags. Read those first (tokens).
- A wrong marker is fixed in the test. The same table gives round 1 its wear budget.

## 2. Round 1's preparation

- P1, the owed queue in order, with expected outcomes and the wear budget: remaining (tokens).
  - BACKLOG's "Real-hardware work still owed" has 35 entries (`BACKLOG.md:194-557`).
  - PLAN's round 1 list:
    - REPORT 7's items 1, 4, 8 and the optional 12;
    - item 11's rows: reset codes 21, 22 and 10+p, the first unfed watchdog stretch, dev's ring peak;
    - the crc16 rerun with both ends' logs;
    - C.md's surviving actions: OR47.a, OR60.a (4), OR50.a (3)(b), OR79.a;
    - the provisional values of `scd30-calibration-readiness` and the serial read of `sgp40-chip-identity`;
    - B2's RUN-pin check;
    - one overnight `long_fram.py` at 8 MHz.
  - The carries:
    - the loop-end bench test (R2 F5);
    - the cobs crossover mode and the stalled TX that now ends on E81, not E82 (B6);
    - the lone-BMP3xx general call on the flash tier;
    - the reset-bit facts of `manual_persistence.py`, met at the desk by `2970ff9e` (`:304-306`).
  - The run sheet is a working file under `S/u35r/r3/`. BACKLOG is edited only where an entry is stale.
- P2, the hardware tests linted, typechecked and collection-checked.
  - Lint and the host mypy pass are met at the merged head (`r2i_lint`, `r2i_mypy_host`, 15:50-15:51 UTC).
  - Remaining: one `pytest tests_hardware --collect-only` (seconds). R2 collected only `test_reset_reasons.py`
    (16 tests).
- P3, bench correction (k): met at the desk.
  - The BOOTSEL case expects ResetReason 2 with no record (`bench/test_reset_reasons.py:85-101`, `16047d96`).
  - Its first silicon run is owed.
- P4, bench correction `loop_lag_under_combined_load`: partly met.
  - The flash test runs only under `--twin`. Silicon's run is the bench tier's production-mode test
    (`bench/test_memory_stress_bench.py:158`, `tests_hardware/README.md:863-872`).
  - So it sits in the bench tier, not in PLAN's flash tier. The reason in the tree: only the bench network reaches
    the script's server.
  - Remaining: a desk check that production mode runs on the frozen image, because the bench saw
    `ImportError: frozen_html` on the mounted entry (READING:103). Its first silicon run is owed.
- P5, the loop-end bench test R2 changed (`41d2ba96`, `17688315`; `test_reset_reasons.py:225`).
  - Checked by collect-only only; its first bench run is owed (README row 22 still reads "not yet run").
- P6, the twin fidelity table fed by the bench's probes: remaining, about 10 min.
  - The probes were never diffed against the twin (READING:102). R2 ran only the BMP3xx probe there (`r2x_bmp_twin`).
  - Run the others on the twin through a throwaway script.
  - Each disagreement becomes a row in `digital_twin/README.md:202`: **adds** (A10), doc rows in an existing table.
    It can instead become the last round's twin correction.
- P7, the chip facts against the final code: remaining (tokens).
  - The SGP40: its three serial words with their CRCs, and its self-test.
  - The SCD30: data-ready gap median 2,143 ms and maximum 2,250 ms at a 2 s interval, at most 20 not-ready polls at
    100 ms; stored settings 4.00 C, 0 m, ASC off, FRC 400.
  - Each is set against the final drivers' waits and defaults.
- P8, the hardware facts R1 relied on, against the datasheets (OR29.a (2)): remaining (tokens).
  - The facts: FRAM at 8 MHz, the I2C clock-out, the BMP3XX STATUS bits, the SGP40 restore.
  - The worktree's `datasheets` submodule (`786c947c`) is not initialised. `/home/user/sensors/datasheets/` holds
    BMP3xx, FRAM, ISL29125, Pico W, SCD30 and SGP40.
  - **Limit for the owner:** there is no RP2040, W25Q16JV or CYW43439 datasheet there. Facts about those chips rest
    on the pinned MicroPython source and the Pico W datasheet, or are marked unverifiable, unless the private
    repository holds them.
- R2's LIST 6 carries:
  - the erase cuts: probably settled by B3 (see OR29.a (4)), confirmed by the runner;
  - the held SDA: a reasons entry, no code;
  - the W65 expectations: two erase tests already expect `SGP_NO_BACKUP`
    (`bench/test_bus_concurrency_under_api_load.py:393`, `bench/test_system_commands_over_rest.py:168`); the
    other boot-time expectations are checked at the desk in P1;
  - the heap probe: OR38;
  - `--only` and `ss`: the findings list;
  - `UART.deinit()`'s Part F line: R4.

## 3. The remaining work in order

1. The static runs (about 5 min; rows OR16, OR19, OR25, OR26, OR45, U35-37, P2):
   - `rebuild.sh`;
   - `pytest tests_hardware --collect-only`;
   - `redflags.py` and `review_rows.py`;
   - `levels_walk.py`;
   - `raising_walk.py`.
   Their output goes to `S/u35r/r3/` and the tree is restored. Adds nothing.
2. The coverage run, 25-35 min (estimate), or snapshot CI's artifact. Then `e51_sweep.py` classes the lines (rows
   OR16 (3), OR22, OR23, OR25 (3)). Adds only A4 on a real gap. A dead line: **owner**.
3. The plant run over the changed sites in the owner's scope, with the changed check-style triggers. Time: measure
   in phase B, estimate up to 1.5 h. Rows OR16 (4), OR19 (3), OR21 (1). Adds only A3 on a survivor.
4. The twin instrument runner, both stages. Time: measure in phase B, bound about 2 h. Rows OR29.a (4), OR21 (1),
   LIST 6. Working record only; A2 is not recommended.
5. The per-file heap probe, about 12 min (OR38, OR39). A fix only where a file grows.
6. The bench probes on the twin, about 10 min (P6). A10 is doc rows.
7. The desk items, tokens only, no machine time:
   - the OR19 verdicts;
   - the OR25 and OR26 subtraction;
   - the OR37 and OR38 read of about 3,700 added lines;
   - the OR41 matrix with U35-09's row;
   - the OR49 cells;
   - U35-37 and U35-52;
   - the bus-hazard and wear tables;
   - P1, P4, P7, P8.
   Each could add: A5 (OR26), A6 (OR37), A7 (OR41), A8 (U35-52), A9 (bus hazard), only on a real gap. U35-37's (a)
   hits are **owner**.
8. **adds** A1, OR49.a (1): the two L2 load tests from LD+CM3, about 114 lines and no new file.
   - Then the twin job's timeout row is re-derived.
   - The lead decides, weighing the L1 and L4 tests that exist.
9. Only if anything is committed:
   - R3's gate, about 50 min (test.sh at both stages, twin dev at both stages; npm only if `js/` changed);
   - a falsification check;
   - CI.
   That gate also gives OR39's final wall clock and peak RSS.

Sum: 3 to 5.5 h of machine time (items 1-6 and 9), inside PLAN's 5-8 h of wall clock for R3.

The adds list:
- A1, certain;
- A2, PLAN-only and not recommended;
- A3-A9, conditional;
- A10, doc rows.

"owner" marks: the dead-line verdicts (item 2) and U35-37's (a) hits (item 7). Both apply only if phase B finds
such a case.

Lead's note (2026-11-04 16:32 UTC, after the owner's 16:30 correction): P8's limit is withdrawn. The datasheets are in
the private repository `hundertvolt/datasheets`, cloned at `/home/user/datasheets/`, the RP2040, W25Q16JV and CYW43439
included; the table read a stale plain folder.
