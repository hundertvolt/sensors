R3 falsification, written by the agent (Wed Nov  4 21:52:00 UTC 2026)

Subject: `13a833c7` against base `17688315` (pre-audit `25caf528`), worktree `S/wt-r3f`. Twelve runs, all through
`S/u35/lead/run.sh`, one at a time, labels and logs `S/u35/lead/r3f_*.log`. Every plant was restored with
`git checkout -- <path>`; the tree ends clean at `13a833c7` (only the linked `node_modules` untracked) and its
`build/generated_src` was regenerated from the restored sources inside the last run. A `src/` plant makes
`tests/_generated_tree.py`'s input stamp stale (`r3f_tp_tickplant` died on it in 0 s, a lost run), so each later
`src/` plant run starts with `python scripts/_generate_sensortask_modules.py` inside the same wrapped command.

| # | label | what | result |
|---|---|---|---|
| 1 | `r3f_rebuild` | `S/u23/rebuild.sh` | rc 0 |
| 2 | `r3f_tp_tickplant` | timer pool, tick plant, no regeneration | rc 1: stale generated tree (no test ran) |
| 3 | `r3f_tp_tickplant2` | timer pool (wozi), tick plant + a drop print | 4/4 PASS |
| 4 | `r3f_tp_nofill` | timer pool (wozi), a queue that never fills | 4/4 PASS |
| 5 | `r3f_dns_plant` | hotspot DNS scenario (wozi, -1), flood answered + wrong A after it | scenario PASSED |
| 6 | `r3f_i2c_spin` | `tests/test_asy_i2c_driver.py`, one yield then a synchronous SCL spin | 114/114 PASS |
| 7 | `r3f_listener_plant` | `tests_hardware/flash/test_modlwip_listener_close.py --twin`, a failed-listen socket left open | FAILED at the port-held assert (errno 98) |
| 8 | `r3f_bytecode` | every `src/*.py` compiled at both commits (`mpy-cross -s`, as `module_sizes.sh`) | 28 modules, 194,883 B each side, 0 differ |
| 9 | `r3f_recorder_plant` | `tests_scripts/test_record_twin_instrument_runs.py`, the plugin's staging report broken | 5 passed |
| 10 | `r3f_comment_cap` | `tests_scripts/test_comment_block_cap.py` | 655 passed |
| 11 | `r3f_scd30_early` | `tests/test_digital_twin_scd30.py`, the fallback read a tick early | FAIL of the missed-edge test |
| 12 | `r3f_tp_tickplant3` | timer pool (wozi), tick plant with clean evidence prints; then restore + regenerate | 4/4 PASS |

## 1. Timer pool and DNS flood: REFUTED (three of its five parts)

**(a) "fails when the product's recovery after a lost soft callback is broken": REFUTED.** Plant (`r3f_tp_tickplant3`):
`arm_tick_timer()` (`src/asy_base_classes.py:378-389`, the system uptime, WiFi uptime and NTP sync-age ticks) arms a
`ONE_SHOT` that re-arms itself from its callback instead of a `PERIODIC` - normal operation unchanged, but exactly the
"a dropped one-shot never fires again" break SPECIFICATION.md C.9 (`SPECIFICATION.md:4257-4259`) makes `PERIODIC` guard
against. Log: the three ticks fire at 1990, 2990, 3990 ms; at 4990 ms all three are dropped (`PLANT_DROP 0 1000 4990`,
mode 0 = ONE_SHOT); the spell runs on to 10490 ms (32 drops); no tick fires again in that test; the test PASSES.
Why: `recording_init` keeps only `PERIODIC` timers (`tests/test_digital_twin_timer_pool.py:253`), so a must-fire timer
turned one-shot leaves the watched set; the readers are checked by their reads, but these three ticks feed no reader,
log nothing when stopped, and the watchdog is fed by the supervisor's sleep (`src/asy_system_service.py:568-570`), not
by a tick. The test catches the same plant only on a reader's own timer (by its reads), not on the tick timers.

**(b) "cannot pass on a scheduler queue that never fills": REFUTED.** Plant (`r3f_tp_nofill`):
`digital_twin/machine.py:1428` `elif callback is not None:` -> `if callback is not None:` - the counter
`drop_next_soft_callbacks` still runs down, every callback is still delivered. The test PASSES. It never observes a
lost callback itself: it waits for the twin's counter to reach 0 (`:267-268`) and then checks only what happens after
the spell (`:270-279`); nothing asserts that any timer's fire count stalled during it.

**(c) "the flood's answers are checked": REFUTED.** Plant (`r3f_dns_plant`), `src/asy_captive_dns.py` after
`dns.response()`: every datagram shorter than a header is answered with 12 bytes, and the next valid query after the
flood gets the A record 0.0.0.0. Twin log: 200 `PLANT_FLOOD_REPLY`, 1 `PLANT_WRONG_A`; the scenario PASSED in 54.8 s.
The flood's own socket never reads (`scripts/_digital_twin_scenarios.py:1051-1053`), and the answer after it is
checked only for being non-empty (`:1054`), unlike the first query's ID, QR bit, length and A record (`:1046-1047`).
Side fact from the same run: all 200 malformed datagrams reached the server (200 replies), so in the twin the flood
is not "well past lwIP's per-socket queue" (`:125`) at all - the host stack queues every datagram; the 4-datagram
limit (`extmod/modlwip.c` per `src/asy_captive_dns.py:88`) is never exercised there.

Stands: inside the existing `needs_exclusive_port_53=True` scenario's one `ctx.boot()` (`:1038-1056`), no new boot;
`_REQUEST_TIMEOUT_S = 10.0` (`:79`) and `_HOTSPOT_WAIT_S = 90.0` (`:93`) are unchanged from `17688315`.

## 2. Strengthened tests: (a)-(c) STAND, (d) REFUTED

- **(a) STANDS** (by reading). `tests/test_asy_isl29125_driver.py:2904-2906`: the fake's `init()` clears `callback`
  and raises before it sets `period` (`tests/machine.py:1309-1317`), so an armed timer, a wired callback or a
  persisted entry each fails an assert. Note: under `RaiseOnArm` every `init()` raises, so the period/callback
  asserts can only be broken by a direct attribute write - they pin the fake's state more than a product choice.
  At `25caf528` the test asserted only the IRQ handler (`is not None`); now `== reader._on_irq`: stronger.
- **(b) STANDS** (by reading). `tests/test_digital_twin_hot_replug.py:127-135`: `ErrCount` against the count before
  the cycle plus no E/W entry; OSR/CONFIG against `_OSR_RESET 0x02`/`_CONFIG_RESET 0x00`
  (`digital_twin/_bmp3xx_chip.py:41-42`). The driver's defaults write OSR 0x00 (PresOvers 1, TempOvers 1,
  `src/asy_bmp3xx_driver.py:97-98`), so a driver re-applying its config after the cycle is caught; a twin whose
  `power_cycle()` kept OSR would be caught too (0x00 != 0x02). CONFIG's default equals its reset value, so a CONFIG
  left as the driver wrote it is indistinguishable - but that is at the reset value, not "other than" it.
- **(c) STANDS** (by reading). `tests/test_asy_scd30_driver.py:1247-1263`: exact `{"ContMeas": "Failed"}` and an
  exact entry list `[("E", CHIP_SET)]`; a Valid, a W, a second entry or none all fail it.
- **(d) "a synchronous wait fails it": REFUTED.** Plant (`r3f_i2c_spin`), `src/asy_i2c_driver.py:68-76`
  `_scl_released()`: one `await asyncio.sleep_ms(0)` up front, then the SCL wait as a plain spin with no yield. The
  log shows `PLANT_SPIN 4794 reads without a yield` (the whole 3 ms `_HELD_SCL_TIMEOUT_US` held the loop) followed by
  `PASS test_a_runtime_clear_whose_scl_is_held_lets_another_task_run_before_it_reports_it`; the whole file 114/114.
  The test asks only `ran > 0` over the whole clear (`tests/test_asy_i2c_driver.py:1592`), so any single yield
  anywhere in it satisfies it. It does catch the fully synchronous form (`awaited` ignored, no yield at all: the clear
  then has no suspension point - `asyncio.Lock.acquire()` on a free lock does not yield).

## 3. Restored tests: the recorder half REFUTED for one test, the missed-edge half STANDS

- No committed record is read: STANDS. Tests 1-2 monkeypatch `RECORD` into `tmp_path`
  (`tests_scripts/test_record_twin_instrument_runs.py:38-39`); 3-5 never reach a record. The five are byte-identical
  to the five behaviour tests of the removed `tests_scripts/test_twin_record.py` (`ffdee74e^`), its five record-reading
  tests left out (neither existed at `25caf528`).
- **"each fails on a planted break of its matching behaviour": REFUTED for
  `test_a_flash_run_whose_board_never_took_the_stage_is_refused`.** Plant (`r3f_recorder_plant`),
  `scripts/record_twin_instrument_runs.py`: `pytest_terminal_summary()` prints the staged line whenever a stage was
  asked (`:220`, the `config.stash.get(_STAGED, 0)` condition dropped) and `pytest_fixture_setup()` no longer counts a
  staged board (`:213`). A real flash run whose board never took the stage is then never refused. All 5 passed: the
  test's fake pytest prints `staged_line()` itself from its own `staged` flag (`:33-36`), so the plugin side of the
  refusal is never run, and `test_the_flash_runs_twin_board_takes_the_stage` (`:62-69`) checks only
  `board.gc_threshold`, not the stash. The other four each have a break they catch (read: charging
  `_problems()`/`_reached()`; the hash coverage of includes and imports; the binary check and its message).
  Also lost with the record (in `ffdee74e`, before this range): nothing checks a written record's per-stage
  `stages` map or that `reason` is set only on an exception - test 1 reads `result` alone.
- Missed-edge SCD30 twin test: STANDS. Planted `src/asy_scd30_driver.py:448` `>= _trigger_half_ticks - 1`
  (`r3f_scd30_early`): `AssertionError: the read fell due at ticks [False, False, False, False, True, True]`. A tick
  late (`>`, the count capped at the threshold by `:439`) never sets the event: `due` all False, caught by the same
  equality (`tests/test_digital_twin_scd30.py:170`); an entry logged by the fallback moves `ErrCount` read after
  `_error_check` (`:153`, `:165-166`, `:171`) - by reading.

## 4. Removal: STANDS

`git grep` (`':!arduino'`) finds `test_the_lowered_uptime_limit_leaves_the_output_unchanged`, `_UPTIME_GAMMA` and
`_UPTIME_GATING` only in `audit/artefacts/evidence/U18_close/fix_voc/*.log`. `src/voc_algorithm.py:427` takes
`_f16(32767 - 1)`; the 16382 the test compared against is in no `src/` file (the 16382/16383 hits are lwIP's
`TCP_MSS` bound, `toolchain/micropython_overrides.py:349`). The C-reference limit stays pinned by
`test_both_estimator_uptimes_stop_at_the_uptime_limit` (`tests/test_voc_algorithm.py:689-696`). The test did not
exist at `25caf528`; legacy's port has the same 32767 cap (`legacy/dev_drivers/voc_algorithm.py:31`, `:503`).

## 5. Hardware tiers: PERMANENT_SKIPS STANDS, uart_comm_hazards REFUTED (narrowly), listener STANDS

- `PERMANENT_SKIPS` (`scripts/_hardware_verdict.py:34-39`) names
  `tests_hardware/flash/test_memory_stress.py::test_loop_lag_under_combined_load_stays_under_the_uart_reply_budget`
  (defined at `:148`, unparametrized, skipping off-twin at `:151-152`; silicon's run is
  `tests_hardware/bench/test_memory_stress_bench.py:158`). Matching is exact tuple membership (`:63`), so it excuses no
  other test and every other skip still goes to `"failed", "unexpected skip"` unless gated (`:64-71`). Note: it
  excuses that test's skip for any reason, a skip under `--twin` included.
- **uart_comm_hazards.py "only adds evidence fields": REFUTED.** At `17688315` the h2 fact's `"log"` was read after
  `_recover()` (`:162-163` there); now it is read before it (`tests_hardware/device_scripts/uart_comm_hazards.py:170-171`).
  That is an existing field changing what it holds, and it is the input of the h2 verdict
  (`tests_hardware/flash/test_uart_crossover.py:174`): entries the two recovery attempts log no longer appear there.
  On a healthy run the verdict's outcome is unchanged (E UART_PEER_INITIATED is logged inside the failed task, before
  any recovery). Everything else is additive: `_evidence()` only reads (`get_log()`, two counters,
  `src/asy_print_log.py:217-235`, `src/asy_uart_driver.py:131,146`); in h3/h1b it runs only on a failed case;
  in `_stalled_tx` it adds two awaited reads before the re-init, no frame or recovery step changed.
- listener: STANDS. 30100 appears nowhere else (`git grep`, audit and lock files aside); the host range is
  `32768 60999` (`/proc/sys/net/ipv4/ip_local_port_range`). On rp2 the round trip ends at `connect()`: lwIP's
  `LWIP_NETIF_LOOPBACK` is 0 (`/root/pico-toolchain/micropython/lib/lwip/src/include/lwip/opt.h:1792`, v1.29.0, no rp2
  override), so `ip4_route()` returns no route for 127.0.0.1 (`lib/lwip/src/core/ipv4/ip4.c:216-217`), `ERR_RTE` ->
  `EHOSTUNREACH` (`extmod/modlwip.c:226`), the `except OSError` returns before the reordered lines; the closing
  `finally` is as before. The port-held check can fail: plant `r3f_listener_plant` (the failed-listen socket left
  open, `listener_close_leaves_the_pcb_pools.py:78`) failed at `test_modlwip_listener_close.py:78` with
  `port_held_errno: 98`.

## 6. Fidelity rows: STANDS (two notes)

Against `S/u35r/r3/m/probes.md` items 1-5 and the twin files:
- SGP40 serial (`digital_twin/README.md:231`): datasheet §3.4 p.10 "hard coded during sensor production" (Sensirion
  SGP40 datasheet). Twin `digital_twin/_sgp40_chip.py:91-94`. Note: word 0 is fixed 0x0000 and two words are random,
  so "fresh random words" is two of the three; the driver reads the serial once at `initialize()` and checks word 0
  (`src/asy_sgp40_driver.py:688-692`), comparing no two reads - the row's reason holds.
- SCD30 0xDD (`:238`): twin `_scd30_chip.py:265-267` (`bytes(3)`); no datasheet cited; every driver read follows its
  command (`src/asy_scd30_driver.py:689-696`, `:822-827`).
- BMP3XX drdy (`:242`): DS001 §4.3.3 Table 27 (PDF p.32 by page count; TOC p.31): "It gets reset, when one pressure
  DATA register is read out". Twin: STATUS set to 0x70 at a conversion (`_bmp3xx_chip.py:161`), never cleared by a
  data read (`:168-172`).
- PWR_CTRL (`:243`): twin stores no 0x1B write (`:194-196`) and reads 0x00 (`:183`). No datasheet cited.
- OSR after 0xB6 (`:244`): DS001 and DS003 register maps both list `0x1C OSR 0x02` (DS001 PDF p.30, DS003 p.29);
  chip id 0x50 is DS001/DS003's `chip_id`. Twin `_soft_reset()` sets 0x02 (`:132-136`).
- **Note: the table now contradicts itself.** The unchanged row `:241` still says the twin's 0xB6 reset is "the reset
  as on silicon", while the new row `:244` records silicon reading OSR 0x00 against the twin's 0x02. probes.md item 3
  itself says `:239` (now `:241`) "is then stale for OSR"; it was not updated.

## 7. src/: STANDS

`git diff 17688315 13a833c7 -- src` is the one line `src/asy_scd30_driver.py:171` (`Datasheets/` -> `datasheets/`; the
cited page is right: Interface Description p.2, 30 ms / 150 ms once a day). `r3f_bytecode` (mpy-cross v1.29.0, mpy
v6.3): 28 modules, 194,883 B at both commits, every `.mpy` byte-identical. `src/asy_uart_comm.py` and
`src/asy_uart_driver.py` are not in the diff.

## 8. Nothing else: STANDS

Each of the 14 files maps to a claim (README 6; scenarios 1; verdict 5; scd30 driver 7; i2c/isl/scd30/hot-replug
tests 2; scd30 twin and recorder tests 3; timer pool 1; voc 4; listener and hazards 5). Added lines outside `audit/`
hold no OR/OF/SF/LN/CM/U/R/D-style ID, lane or unit name (`plan` is the wiring plan variable). `r3f_comment_cap`:
655 passed (Python and shell, all eight scopes); the README rows are a table, not comments.

## 9. Numbers: STANDS

`git diff --shortstat 17688315 13a833c7 -- ':!arduino'`: 14 files, 343 insertions, 53 deletions.

## 10. R3's records: REFUTED in part (a further survivor; one dead line); counts STAND

Counts: `m/twin.md`'s table has 39 rows, 31 (b) and 8 (c), none (a); `m/twin_record.json` holds 126 entries, 68 pass,
58 exception (19 bench). The five classings judged most likely wrong:
1. **`m/plants.md` `r3.i2c.stretch_yield`: a further survivor.** The new test closes the recorded `pass` form, but the
   near variant of the same F.3 break - one yield, then the synchronous wait - survives the whole of today's
   `tests/test_asy_i2c_driver.py` (`r3f_i2c_spin`, item 2(d)).
2. **`m/coverage.md`, generated `_system_cmd_callback`'s last `return False` ((c) guard): a dead line.** Its only
   caller passes a member of `_SYSTEM_CMDS` (`src/asy_webserver_service.py:120`, `:721-727`), and the callback handles
   all five (`build/generated_src/sensortask_wozi.py:71-82`), so no product path reaches it in any of the six devices;
   the stated need ("the callback's bool return needs the fall-through") does not hold - the last case emitted
   without its `if` needs none. Unlike the `_init_done` guard, no "modules as libraries" ruling covers generated code.
3. `m/twin.md` `flash/test_uart_crossover.py` (b): misclassed in part, no product defect shown.
   `test_no_frame_is_lost_while_interrupts_are_off` fails in `_ring_holds_the_flash_window()`
   (`tests_hardware/flash/test_uart_crossover.py:69-77`) before any twin code runs, on silicon too: dev's 512 B ring
   against 4,608 B (BACKLOG.md:451-459). That case is not twin fidelity (R3's own finding 2 calls it (c)); a bench
   rig's configuration, out of scope per CLAUDE.md's dev rule.
4. `m/twin.md` `sgp40_voc_algorithm_quality.py` / `flash/test_sensor_accuracy.py` (b): red 2 of 15 at 32768 only, for a
   fixed-point algorithm on a seeded walk; the class rests on the walk's shape, not on why only one GC stage shows it.
   Not refuted (no run left); the stage dependence is unexplained.
5. `m/plants.md` `named.fram_alloc` "not a gap": the test states it "fails if ... any comparable per-call allocation
   regresses back into the path" (`tests/test_asy_fram_allocation_budget.py:1-3`); a 16 B allocation per
   `_write_chunk()` call is one and survives both stages. R3 reads "comparable" as per-CS-cycle scale. Contested, not
   refuted.

## Outside the claims

1. `digital_twin/README.md:241` against `:244` (item 6): one row says the twin's 0xB6 reset matches silicon, the next
   that it does not for OSR.
2. `tests_hardware/device_scripts/listener_close_leaves_the_pcb_pools.py:27`: the comment's "below ... every port band"
   is wrong - 30100 is above every band (`tests/_port_bands.py` ends at 29999, `:36`) and below the ephemeral range;
   and the fixed port is not a row of the "one table of test port bands", whose docstring lists fixed ports "so no
   other row can take it" (`tests/_port_bands.py:1-9`). No row takes it today.
3. A tool output of `r3f_tp_tickplant2` (a 1 MB recursive closure repr from my own evidence print) was saved by the
   harness under `/root/.claude/projects/...`; I did not open it. `S/u35/lead/r3f_tp_tickplant2.log` holds the same.
