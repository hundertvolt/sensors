# A-L verify SUPP_owner_0930 (HEAD b46b352)
Counts: 30 actions checked · OK 13 · FIX 17 (A.S0930.01, .02, .03, .04, .05, .06, .12, .13, .14, .17, .18, .24, .26, .27, .28, .29, .30) · REJECT 0; ledger gaps (OR125.a has no row and no owning action; OR118.a (1)'s recovery-ladder clause has no rung plan); 24 findings (FIX 21, ADD 3)

HEAD `b46b352`; the file states `5f46cf1`/`cde3bb0`. `git diff --stat cde3bb0 b46b352 -- . ':!audit' ':!PROJECT_AUDIT_PLAN.md'`
is empty, so every cited code/test/doc line holds at `b46b352` (re-opened here, not trusted). `git diff b46b352 HEAD`
touches only `audit/actions/AC_NOTES.md` (item 34).

**Primary sources checked by the verifier.** MicroPython v1.29.0 (`scratchpad/mp`, `py/mpconfig.h:41-43`):
`extmod/asyncio/stream.py:141-142` (`wait_closed()` = `await self.task`), `:147-159` (the server task's `CancelledError`
handler closes the listening socket and re-raises unless `close()` set `state`), `task.py:164-166` (a cancel is forwarded
to the awaited task), `core.py:18` (`CancelledError(BaseException)`) — A.S0930.18's DONE-AT-HEAD claim is right;
`stream.py:106-110` (`open_connection()` raises only a synchronous non-EINPROGRESS connect error); `ports/unix/modsocket.c:516-534`
(no `getsockname`); `ports/rp2/modules/_boot.py:9` (littlefs mount); `lib/littlefs/lfs2.c:6054` (`lfs2_remove`).
Datasheets (`scratchpad/dstxt`): MB85RS2MTA 262,144 × 8 bit, 40 MHz max (`:15-30`), a byte is written once its 8 bits
are in, no write wait (`:301-305`); MB85RS64V 20 MHz max (`:24`); W25Q16JV tPP ≤ 3 ms, tSE ≤ 400 ms (`:3104-3105`).
Neither FRAM datasheet states the initial contents of a new part (grep `initial|shipp|factory|delivered`: packing lines
only). Arithmetic re-derived from `src/asy_fram_driver.py:154-231` (five CS sessions per unit write: WREN 1, RDSR 2,
WRITE 4+256 or 3+256, WRDI 1, RDSR 2 = 266/265 B), `src/asy_spi_driver.py:109` (1 MHz default), `:20` (2 µs CS settle),
`devices/*.toml` `[bus.spi0]` pins only, `devices/dev.toml:119` (`0x40000`), five others `0x2000`: 2.128 ms per unit,
1,024 units = 2.18 s; 32 units × 2.12 ms = 68 ms; pass 1 = 4 × 11 B = 44 B = 0.35 ms per chunk — all correct.
"0x00 never validates": `src/asy_fram_manager.py:223-239` (0x00 = `_STATUS_UNINIT` → uninit), `:265-267` (mixed pair →
error), `:299-308` (uninit → `(True, 0)` before data/CRC), `:206` (valid only when `valid_bytes == self.size`),
`:648-650`/`:690-692` (size 0 refused); `src/crc_checks.py:29-33, 99-106` (init defaults to all-ones; valid only when the
register ends at 0), `:150-162` (polys 0x31/0x1021/0x04C11DB7, constant term 1, so ×x⁸ is injective mod P and a non-zero
register never reaches 0 over zero bytes); `src/print_log.py:238` (`crc=CRC8()`), `src/asy_sgp40_driver.py:181-183`
(`crc=CRC32()`). The two-gate proof is correct; its torn-state part needs pass 1 to have succeeded (V.SUPP_owner_0930.10).

## Findings

- V.SUPP_owner_0930.01 | A.S0930.03 | FIX | Site and test list name the wrong file: the tests cited as
  `tests/test_asy_uart_link_driver.py:190, 207, 219, 308, 339, 485, 489` are `tests/test_digital_twin_uart_link.py`'s
  (L2, generated dev graph: `:190 test_a_get_and_a_set_both_complete_with_no_errors_counted`, `:207`, `:219`, `:308`,
  `:339`, `:485`, `:489`); `tests/test_asy_uart_link_driver.py` has 392 lines and 20 tests, and its byte-moving tests are
  the eight that call `build_pair()` (`:168-362`). Why quotes OR116.a as "confirm and extend where the exerciser itself is
  involved" — no such text in `PROJECT_AUDIT_PLAN.md` (OR116.a row :504) or LEAD. The ledger's DONE evidence
  "`tests/test_asy_uart_comm.py:2163` runs its load arm on CRC16" is the legacy BSEC bus-floor test
  (`test_the_legacy_bsec_bus_parameters_meet_every_floor_but_one`), not a load arm. | Why → "LEAD/R31 — "exercised in both
  CRC modes (none and CRC16) at L1"; State "test in U17/U24 (L1)"; OR116.a "at HEAD only L1 runs both modes
  (`tests/test_uart_comm_hazard.py`, `test_asy_uart_comm.py`: no CRC and CRC16)" and (1) "at every level that can reach
  it" (owner, 2026-09-30); the exerciser layer is the agent's reading of (1)". Site → "`tests/test_asy_uart_link_driver.py:34-47`
  (`Pair`), `:71-75` (`build_pair()`), the tests that move bytes `:163, :175, :188, :200, :227, :236, :247, :357`".
  Change's test list → "`test_exercise_loop_counts_a_transfer_for_a_correct_banner_answer` (`:163`),
  `…_wrong_payload_as_a_failure_not_a_transfer` (`:175`), `test_banner_get_across_a_real_responder_via_get_callback`
  (`:188`), `test_echo_round_trip_across_a_real_responder_via_set_and_get_callbacks` (`:200`),
  `test_unanswerable_command_id_is_rejected_not_crashed` (`:227`), `test_exercise_loop_counts_a_failure_when_nothing_answers`
  (`:236`), `test_get_error_counter_delegates_to_the_inner_comms_own_log` (`:247`),
  `test_a_persisted_fault_during_a_transfer_does_not_stall_other_tasks` (`:357`) — become `_check_*` functions registered
  per mode; `build_pair(…, crc=None)` passes it to `Pair`". Ledger row R31 L1 evidence → "`tests/test_uart_comm_hazard.py:51,
  1273-1296`; `tests/test_asy_uart_comm.py:2163` (the BSEC floor check builds its bus with `crc=CRC16()`)".

- V.SUPP_owner_0930.02 | A.S0930.04 | FIX | Point (4) (the CI suite's `uart_link:silent` cell per CRC mode, the new
  `--device-toml` option of `scripts/_digital_twin_ci_suite.py`, the second run in `scripts/run_digital_twin_ci.sh`) sits
  inside the Blast slot after "uart —", so it reads as blast, not as a planned change. | Move "(4) The CI suite's
  sustained-fault cell … zero `MemoryError` markers." from Blast to the end of Change; Blast's tests slot gains
  "`tests_scripts/test_digital_twin_ci_suite_*.py` (the new `--device-toml` option parses; generation from a derived path)".

- V.SUPP_owner_0930.03 | A.S0930.05 | FIX | (a) "its `RESULT:` line names the mode" conflicts with A.U26.68 (U26.md:
  device scripts print `FACT <key>=<json>` lines and the host test gives the verdict; `RESULT:` lines go). (b) The mode is
  a per-run value, not a board fact: A.U26.44's facts dict renders each UART bus's TOML `crc` (`none` on `dev`), and per-run
  values travel as `render_device_script(path, **extras)` (U26.md A.U26.44 (2)). (c) A.U26.87 changes the same script
  (`uart_link_under_concurrent_system_load.py:40-45, 160-190`, a multi-chunk SET under load) and is not named. | Change →
  "each script takes `CRC_MODE` as a render extra (`board.run_isolated(script, CRC_MODE=mode)`, A.U26.44's `**extras`;
  default `"none"`) and builds both buses with `crc=CRC16()` when it is `"crc16"`; it prints `FACT crc_mode="<mode>"`
  (A.U26.68) and the host assertion checks it". Depends += "A.U26.68, A.U26.87 (same script; its multi-chunk SET runs in
  both modes)".

- V.SUPP_owner_0930.04 | A.S0930.06 | FIX | The CRC16 build keeps the default output name `firmware-<device>.uf2`, so it
  overwrites `build/firmware-dev.uf2` and the image record beside it (A.U26.02) that A.U26.03's check compares against;
  the `finally` then "rebuild[s] and reflash[es] the standard image" — a rebuild carries a new build date, so it is not the
  round's image and A.U26.79 ("every hardware round ends on the release `dev` image", U26.md) and A.U26.03 can no longer
  prove the board runs this round's image. | Change (3) → "build it with `--device-toml <tmp>` `--output
  tmp_path/firmware-dev-crc16.uf2` (its image record lands beside it); `reflash(board, <that path>)`; … in `finally`,
  `reflash(board, <the round's standard .uf2, unchanged>)` — no rebuild — and assert the board serves, A.U26.03's image
  check passes and `UARTLINK.Failures` stays 0 over two polls". Depends += "A.U26.79 (end state)".

- V.SUPP_owner_0930.05 | A.S0930.01 | FIX | (a) "(a non-string reaches the same message)" is false for a TOML array or
  inline table: `spec.fields.get("crc", "none") not in UART_CRC_MODES` on a `list`/`dict` raises `TypeError: unhashable`
  (dict membership). (b) Blast "`tests_scripts/test_device_tomls.py` field-set checks (grep `ALLOWED_INSTANCE_FIELDS`)":
  that grep finds no hit in `tests_scripts/` — the catch-all is `buildgen/validate.py:392`. (c) Callers "`validate()`/
  `build_model()`": there is no `validate()`; both lines are in `build_model()` (`validate.py:730-753`). | (3) →
  "`crc = spec.fields.get("crc", "none")`; `if spec.driver == "uart_link" and (not isinstance(crc, str) or crc not in
  UART_CRC_MODES): raise BuildError(…)` (every non-string, arrays and tables included, reaches this message)"; new L0 case
  list gains `crc = ["crc16"]`. Blast tests → "the catch-all `validate.py:392` reads `ALLOWED_INSTANCE_FIELDS`, so the key
  is accepted; `tests_scripts/test_device_tomls.py` pins no `uart_link` field set (grep)". Callers → "`build_model()`
  (`validate.py:736, 752`)"; `validate.py:11`'s buildspec import gains `UART_CRC_MODES`.

- V.SUPP_owner_0930.06 | A.S0930.02 | FIX | `buildgen/codegen.py` imports nothing from `buildgen.buildspec` (`:5-13`), and
  the change indexes `UART_CRC_MODES`. | Change gains "`codegen.py`'s imports gain `from buildgen.buildspec import
  UART_CRC_MODES`".

- V.SUPP_owner_0930.07 | A.S0930.12 | FIX | (a) `self._storage` is used by the gate (`erase_ready()`) and the sequence but
  is created nowhere: A.U5.02 (U5.md) renames the parameter to `storage` "the `AsyFramManager` whose `set_pause` it uses"
  and stores only `storage_pause`; the Depends note "(`storage` parameter kept as `self._storage`)" attributes to A.U5.02 a
  step it does not contain. (b) Blast "device scripts calling `reboot_*`/`pause_permanent_storage` directly (grep …: none
  else)" is wrong: `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:79, 86, 88, 93, 94, 117` and
  `tests/test_digital_twin_sensortask_integration.py:811` call `pause_permanent_storage()` directly. | Change's state list
  gains "`self._storage: AsyFramManager | None = storage` (the manager itself; `storage_pause` stays as A.U5.02 sets
  it)"; Depends → "A.U5.02 (`storage` parameter)". Blast callers → "…`reboot_fallback_starves_the_watchdog.py:38` calls
  `_reboot()`; `fram_pause_unpause_and_gating.py:79-117` and `tests/test_digital_twin_sensortask_integration.py:811` call
  `pause_permanent_storage()` and ignore its result — they hold".

- V.SUPP_owner_0930.08 | A.S0930.13 (and design S0 (3)) | FIX | The supervisor's park point and its restart/escalation
  suppression are keyed on `self._shutdown`, which S0 (3) sets **before** the preflight and S0 (4)/(5) clear again on a
  refusal. If the preflight ever yields, the supervisor can observe `_shutdown`, park on `self._never` (never set) and stay
  parked after the refusal clears `_shutdown` — nothing feeds again and a *refused* command ends in a watchdog reset.
  Latent at HEAD only because `erase_ready()` → `FRAM_SPI.get_write_protected()` completes without suspending on the
  initialized path (`src/asy_fram_driver.py:268-275`); any preflight that opens an SPI session yields
  (`asy_spi_driver.py:175`, `await asyncio.sleep(0)` in `__aexit__`). | (4) → "`_supervise()`'s pass begins with `if
  self._feed_owned: self._supervisor_parked.set(); await self._never.wait()`; the dead-task restart loop breaks and the
  escalation branch runs only `if not self._feed_owned` — keyed on the one-way acceptance latch, never on `_shutdown`,
  which only gates the other commands and can be cleared by a failed preflight". Design S0 (3)'s "and the supervisor
  stops restarting and escalating" moves to S0 (6). New L1 case in A.S0930.24: a refused `erasefram` (write-protected
  chip, preflight made to await one `asyncio.sleep(0)` from outside) leaves the supervisor feeding — `feed_count` rises
  over the next two passes.

- V.SUPP_owner_0930.09 | A.S0930.14 | FIX | (a) S2 is specified twice, inconsistently: the design says "through U11's
  `_flush_config_stores()` wrapper", A.S0930.14 inlines its own `try/except` per store to feed per store and track `ok`;
  A.U11.03 point 3 defines `_flush_config_stores(self, *, close=False) -> None`, which can neither feed per store nor
  report failure — two copies of the guarded flush. (b) The timing paragraph bounds S1, S2, S3, S5 but not S4 (a cancel
  lands at the task's next await; `src/captive_dns.py:129-150` and `src/asy_wifi_service.py:534` show product tasks that
  run cleanup after `CancelledError`). | (a) one wrapper: A.U11.03's becomes `async def _flush_config_stores(self, *,
  close: bool = False, step_done: "Callable[[], None] | None" = None) -> bool` (False when any flush raised; `step_done()`
  after each store) and S2 is `ok = await self._flush_config_stores(close=True, step_done=self._own_feed)`; Depends notes
  the A.U11.03 signature change (A-C merges). (b) Timing gains "S4: per task, the cancel lands at its next await; a
  supervised task whose `CancelledError` handler awaits cleanup is bounded by that cleanup, fed after each task; the
  healthy-run proof is A.S0930.26/.27 on every device".

- V.SUPP_owner_0930.10 | A.S0930.17 | FIX | (a) `erase_chip()` runs pass 2 even when a pass-1 `invalidate()` failed
  (`ok = await chunk.invalidate() and ok` continues), while the design's torn-state proof (4) rests on "Pass 1 marks both
  status bytes of every allocated block 0x00 … before pass 2 writes any data"; a power cut mid-pass-2 over a chunk whose
  blanking failed is exactly the 2⁻⁸ case the proof excludes. (b) Planned comment text "every byte is zeroed — the chip's
  own blank state (Part A.4)" (and design (3) "0x00 is the chip's own blank state") states a hardware fact neither FRAM
  datasheet gives (see header); the fakes' `bytearray(size)` (`digital_twin/_fram_chip.py:43`,
  `tests/_fram_chip_fake.py:26`) are not a source. (c) Why quotes OR120.a (2) as "the whole-chip overwrite in chunks";
  the row reads "(the whole-chip FRAM overwrite in chunks)". | (a) after pass 1: `if not ok: self.pr.err("FRAM erase: a
  chunk could not be blanked, chip not overwritten"); return False` (code 9 through S5), before the buffer allocation;
  A.S0930.21 (e) gains "`invalidate()` failing for one chunk (fake chip refusing that status write): no pass-2 write
  reaches the chip, code 9". (b) comment → "Erase FRAM (owner, 2026-09-30): every chunk's blocks are marked blank first, so
  no interrupted later write can leave a block that validates; then every byte is zeroed — the manager's uninitialised
  status value and its own clear pattern (Part A.4)."; design (3) likewise. (c) quote exactly.

- V.SUPP_owner_0930.11 | A.S0930.18 | FIX | The planned test uses "a free port", but the Unix-port socket has no
  `getsockname()` (`mp/ports/unix/modsocket.c:516-534`), so a port-0 bind cannot be read back; `tests/` binds fixed
  per-file port blocks (`tests/_webserver_concurrency_scenarios.py:71-77`, 19700+ per device). And "`open_connection()` to
  that port raises `OSError`" holds only when the kernel refuses the non-blocking connect synchronously; an EINPROGRESS
  connect surfaces on the first read/write (`stream.py:106-110, 121`). Blast "`scripts/test.sh`'s port rule (ephemeral
  port …)" describes the host `tests_scripts/` tier, not this one. | Change → "… a `WebserverService` on `127.0.0.1` and
  a fixed port from a block owned by this file (the `_PORT_BASE_BY_DEVICE` pattern, a range no other `tests/` file uses) …
  → connecting to that port fails: `open_connection()` raises `OSError`, or the first write/read on the returned stream
  raises `OSError` or reads EOF"; Blast → "CLAUDE.md "two suites that bind real ports" (the tier runs apart from `npm
  test`)".

- V.SUPP_owner_0930.12 | A.S0930.24 | FIX | (a) (b) asserts "the largest gap between consecutive `feed_times` entries during
  the sequence stays under 1,000 ms", but S1's two own feeds bracket the park wait, up to `_TASK_CHECK_TIME` (2 s,
  `system_service.py:44`) plus a pass — the design says so itself ("Longest single step … S1's park wait, ≤ 2 s"). (b)
  `feed_times` is added to `tests/machine.py`'s `WDT` only, while A.U24.17 holds both tiers' machine fakes to one contract
  that covers `WDT` (U24.md A.U24.17 lines 6, 11). | (a) → "the gap between S1's two feeds stays under
  `_TASK_CHECK_TIME * 1000 + 500` ms (read from source), every other gap under 1,000 ms (host time)". (b) twin slot →
  "`digital_twin/machine.py` `WDT` gains the same `feed_times` (a `deque(…, _LOG_MAXLEN)` like `would_have_triggered_log`),
  so A.U24.17's contract holds".

- V.SUPP_owner_0930.13 | A.S0930.26 | FIX | (4) "`gc.mem_alloc()` growth across `erase_chip()` differs by less than 256
  bytes between the 8 KB and the 256 KB fake" fails as written: every unit's `async with self.fram` allocates its
  enter/exit coroutines (the FRAM path costs 20-34 KB per logger `setup()` in a collection-free window,
  `tests/test_asy_fram_allocation_budget.py:33-37`), so collection-free growth scales with 1,024 vs 32 units. What is
  size-independent is the *retained* allocation. Also the scenario asserts "a reset is armed with code 7" — the region-0
  record needs A.U11.07's `mem_backup` fake, not in Depends. | (4) → "retained allocation independent of chip size: inside
  the measurement only, `gc.collect()` then `gc.mem_alloc()` before and after `erase_chip()` (the `_priced()` shape,
  `tests/test_asy_fram_allocation_budget.py:42-46`); the two retained deltas differ by < 256 B; and the collection-free
  allocation per unit is ≤ a measured per-unit budget (one budget per Unix-port build, as that file keeps)". Depends +=
  "A.U11.07".

- V.SUPP_owner_0930.14 | A.S0930.27 | FIX | (a) (4) says the `--test-shutdown-hang` flag rebinds "the one object that step
  waits on" and lists six objects for seven hang points — S1 has none. (b) The S5-erase hang on the FRAM driver's
  `report_set_values()` never fires on a healthy chip: pass 2 calls it only for a non-zero status (`if status and not await
  self.fram.report_set_values(status)`). (c) (2) "`erasefram` against a `silent` chip is refused by the preflight" holds
  only once A.U16.R03 has set `initialized = False` after a failed operation; before that the erase starts and stops at
  its first unit (code 9). (d) (1)(a) "the directory holds no `config_*.cfg`" after the relaunch needs A.U11.19 (a boot
  with no file writes nothing), not in Depends. | (a) add "S1: the supervisor's `_log_dead_task` rebound to a coroutine
  that never returns and one supervised task ended, so the pass never reaches its park point". (b) "the FRAM driver's
  `report_set_values`, with the twin chip refusing the first pass-2 unit (its WREN-drop knob, A.U25.15)". (c) "refused by
  the preflight once a failed chunk operation has marked the chip lost (A.U16.R03); a fresh `silent` chip lets the erase
  start and stop at unit 0 with code 9 — both cases asserted". Depends += "A.U11.19, A.U16.R03".

- V.SUPP_owner_0930.15 | A.S0930.28 | FIX | (a) (6) "the board resets 8.0-10.0 s after that line": `HANG` is printed
  after the last own feed, so the watchdog fires ~8,000 ms minus that print's delay after it — the lower bound can fail on
  a correct unit. (b) (6) "the test asserts the gap < 100 ms" — over the whole sequence the S1 park gap (≤ 2 s) and an S2
  flush (a littlefs commit can include 400 ms sector erases, W25Q16JV `:3105`) exceed it; the per-unit claim concerns S5.
  (c) (4), (5) and (7) issue `erasefram` with no FRAM evidence saved first; OR118.a (3) and LEAD/R32 ("an Erase-FRAM test
  reads and archives the FRAM error logs first") and A.U26.22 ("before any … other clearing") require it for every
  erasing test, not only (2). | (a) → "7.5-10.0 s after that line (a fed hang never resets; the 4 s reset timer is ruled
  out by the lower bound)". (b) → "the largest gap between feeds inside the erase (S5) < 100 ms, and every gap < 8,000 ms".
  (c) (4), (5), (7) each start with `save_fram_raw(board, <test name>)` (A.U26.22).

- V.SUPP_owner_0930.16 | A.S0930.29 | FIX | (a) (4) and (5) send `erasefram` without `save_errcount()`/`save_fram_raw()`
  first (same rule as V.SUPP_owner_0930.15 (c)). (b) (7) "cut power within 1 s of the reply" lands before the erase starts
  (S1 alone may wait up to 2 s), so it may test nothing mid-erase. (c) The matrix's L4 watchdog cell (.29 (6)) proves only
  the healthy run; the hang half of OR120.a (3) is not reachable over REST without a product hook (OR36) and is not marked
  so. | (a) (4), (5) start with `save_errcount(dut_ip, …)` and `save_fram_raw(board, …)`. (b) → "cut power 2.5-4.0 s after
  the reply (inside the ≈2.2 s erase that follows S1-S4)". (c) (6) gains "a hung step is not reachable at L4 without a
  product hook (OR36); it is proven at L3 (A.S0930.28 (6)) and L2", and the matrix's L4 watchdog cell says the same.

- V.SUPP_owner_0930.17 | A.S0930.30 | FIX | Three permanent texts become false and are not in the change: CLAUDE.md's wear
  rule "a *dispatch-only* PUT persists nothing and is deliberately outside the gate"; SPEC H `:4378` ("Dispatch-only PUT
  fields … None persisted … a dispatch-only PUT is deliberately outside it"); SPEC H `:4524-4527` ("a well-formed submission
  always reports `"Valid"`") — a refused command answers "Failed". | Add: CLAUDE.md wear rule "…a *dispatch-only* PUT
  persists nothing and is deliberately outside the gate, except `SystemCmd` `"resetconfig"`, whose purpose deletes every
  config file (owner, 2026-09-30)…"; SPEC H `:4378` row gains "— except `SystemCmd` `"resetconfig"`, which deletes every
  config file and is gated like a persisting PUT"; H `:4525-4527` "always reports `"Valid"`" → "reports `"Valid"`, or
  `"Failed"` when the command is refused (a reset armed or a shutdown under way)".

- V.SUPP_owner_0930.18 | ledger (OR125.a; conflict 9) | ADD | OR125/OR125.a is part of this unit's input and has no
  ledger row. `audit/actions/U25.md` does not cover it: A.U25.46 (`:1524-1573`) implements OR125.a (1)'s host-side
  harness but leaves "the scenarios needing DUT-side control" NOT-DONE "pending Q2" (point (4)) and plans no runner flag
  and no production-path check; Q2 (`:2321-2330`) is exactly what OR125 answered (option (a)). The owner is **U25.md** (the
  twin runner and the moved scenarios are U25's; this supplement only adds a flag). | Ledger row: "| OR125/OR125.a (owner
  row) | (1) every webserver-concurrency scenario host-side; (2)-(3) named, off-by-default runner flags and a check keeping
  them out of the production path | owned by U25: A.U25.46 (pending Q2 lifted) and the new U25 action below; this file adds
  only `--test-shutdown-hang` (A.S0930.27) to that action's flag list and check |". New U25 action (A-C numbers it):
  "### A.U25.nn The twin runner's named, off-by-default instrumentation flags — **Why**: G7/R19, G7/R01 (stated runner
  exception) — OR125 "Special test code in the twin runner: every scenario moves to the host, but the runner carries
  test-only code." (owner, 2026-09-30); OR125.a (1)-(3); settles U25 Q2 as (a). **Site**:
  `digital_twin/run_generic_integration.py` (argument parser; `main()` after `_wire_uart_crossover()`, `:369`);
  `tests/_webserver_concurrency_scenarios.py:108-123, 740, 750-766` (moved by A.U25.46); `scripts/_digital_twin_scenarios.py`.
  **Change**: flags named `--test-…`, each default off: `--test-hold-closing-slot` (rebinds `module.webserver._close_writer`
  from outside to hold until the runner releases it, printing one `SLOT_HELD`/`SLOT_RELEASED` line), `--test-stall-loop-ms
  N` (one runner task blocking the loop for N ms when triggered, printing `STALL`), `--test-conn-status-interval-ms N`
  (a runner task printing `CONN_SLOTS open=<n> backlog=<n>` from `_open_conns`/`_backlog` every N ms), and
  `--test-shutdown-hang <step>` (A.S0930.27); A.U25.46's pending-Q2 scenarios move host-side on them. **Blast**: tests new
  L0 `tests_scripts/test_twin_runner_test_flags.py` — every `--test-` flag's argparse default is off; every rebind or
  instrumentation call in the runner is reached only under its flag's `if` (`ast`); no `--test-` name, no runner module
  and no `digital_twin/` import appears in `src/`, in any generated module or in the frozen module set (A.U20.13) — the
  production entry path; a bite fixture (a flag defaulting on) fails · twin the runner · docs `digital_twin/README.md`
  flag table "test-only instrumentation (owner, 2026-09-30)"; SPEC E.9 names the runner-only exception. **Depends**:
  A.U25.46, A.U25.28, A.S0930.27. **Kind**: code, test, doc."

- V.SUPP_owner_0930.19 | ledger (OR118.a (1) recovery ladder) | ADD | OR118.a (1) requires the two commands' tests "under
  … the recovery-ladder rule", and the brief's rule 8 asks each fault path's rungs to be planned; the file plans the
  sequence's failure outcomes (continue, code 9, watchdog) but names no rung and no retry — only A.U16.R01 appears, as a
  dependency. | Design block gains, after "Order rationale": "**Recovery ladder inside the sequence** (OR113.a (2)): a
  failed erase unit is retried at the WREN rung (A.U16.R01) and then stops the erase (code 9); a failed `os.remove()`
  other than ENOENT is retried once, then left (code 9); a failed flush is logged and the next store proceeds (A.U11.03);
  every failure still ends in the one reboot, and a hung step in the watchdog — each logged once per event."
  A.S0930.16 (3): "`except OSError as e`: ENOENT → `True`; otherwise one more `os.remove()`; a second failure →
  `self.pr.err(...)`, `False`". A.S0930.21 (f) gains "a remove raising `OSError(5)` once and then succeeding → `True`, the
  file gone, code 7".

- V.SUPP_owner_0930.20 | section C (inventory) | FIX | The site scan's path list (`scratchpad/al/S0930/sites.py`) omits
  files this supplement changes (`tests/test_digital_twin_uart_link.py`, `tests_scripts/test_buildgen_validate.py`,
  `test_buildgen_generate.py`, `test_buildgen_definitions.py`, `test_digital_twin_generated_boot.py`, `tests_js/*`,
  `tests/test_digital_twin_bus_hazard_concurrency.py`, `tests_hardware/flash/test_bus_concurrency.py`,
  `tests_hardware/bench/test_bus_concurrency_under_api_load.py`, `tests_hardware/harness.py`,
  `digital_twin/run_generic_integration.py`, `tests_js/_live_matrix_command.js`, `uart_link_under_concurrent_system_load.py`,
  `tests/test_asy_fram_allocation_budget.py`, `tests_hardware/manual/manual_persistence.py`), so the table misses earlier
  actions on them (re-scan here). | Add co-land: A.U26.68 (facts, host verdict → .05, .28), A.U26.87 (same UART load
  script → .05), A.U26.79 (round end state → .06, .29), A.U26.26 (boot/reboot oracle → .28, .29), A.U24.42 (allocation
  budget file → .17), A.U24.55 (generated-boot file → .04), A.U24.53 (live harness config dir; the new words delete
  config → .27), A.U26.32 (bench hazard file → .29 (5)). Add blast-only: A.U17.05, A.U20.09, A.U20.37, A.U23.21, A.U23.32,
  A.U23.36, A.U23.37, A.U23.43, A.U24.14, A.U24.34, A.U24.51, A.U24.52, A.U24.66, A.U25.31, A.U25.33, A.U25.39, A.U25.41,
  A.U25.50, A.U25.51, A.U26.13, A.U26.37, A.U26.43, A.U26.60, A.U26.78, A.U26.80, A.U26.83. The scope sentence's "217
  actions" count changes accordingly.

- V.SUPP_owner_0930.21 | header | FIX | Title "owner rows OR116-OR119 (HEAD 5f46cf1)" — the file covers OR116-OR125 and
  was committed at `b46b352` (code unchanged since `cde3bb0`). | → "# A-L supplement — owner rows OR116-OR125 (HEAD
  b46b352)"; the second paragraph adds "unchanged at `b46b352`".

- V.SUPP_owner_0930.22 | conflict 9 | FIX | "the lead routes OR125.a to U25, and that action's flag list and check must
  include it" — no such U25 action exists (see V.SUPP_owner_0930.18). | → "OR125.a (2)-(3) has no U25 action at HEAD:
  A.U25.46 leaves the DUT-side scenarios pending Q2 and plans no flag or check. U25.md owns the new action
  (V.SUPP_owner_0930.18's text); A.S0930.27's `--test-shutdown-hang` joins its flag list and its production-path check."

- V.SUPP_owner_0930.23 | A.S0930.13 Blast | ADD | A.U10.08's rule also "fails … on a feed in any `while` loop other than
  (b)" and G5/R01's "never-in-loop"; the sequence's own feeds run inside `for` loops through `step_done`
  (`quiesce()`/`erase_chip()`, S2, S4). A.S0930.20 (6) admits `_own_feed()` by name but does not say that the loop rule
  exempts the calls through `step_done`, so A-C could merge a guard that fails on them. | A.S0930.20 (6) gains "the
  never-in-a-loop rule does not apply to `_own_feed()` or to calls through a `step_done` parameter (one feed per bounded
  step inside the shutdown sequence, owner, 2026-09-30); a `while` loop reaching `_own_feed()` still fails".

- V.SUPP_owner_0930.24 | A.S0930.25 | FIX (text) | "every cut point inside pass 1 (every byte, a few hundred on the 8 KB
  layout)": pass 1 writes 4 data bytes per chunk (two status bytes × two blocks), so a device with about a dozen chunks
  has about 50 cut points, not a few hundred. Harmless to the design; the count is stated as a fact. | → "every cut point
  inside pass 1 (every status byte: four per allocated chunk)".

## Checked OK
A.S0930.07, A.S0930.08, A.S0930.09, A.S0930.10, A.S0930.11, A.S0930.15, A.S0930.16 (except the ladder rung, V.SUPP_owner_0930.19),
A.S0930.19, A.S0930.20 (except (6)'s loop-rule note, V.SUPP_owner_0930.23), A.S0930.21, A.S0930.22, A.S0930.23,
A.S0930.25 (except the count, V.SUPP_owner_0930.24)

**Register fixes 1-5: all correct.** (1) the CRC is `asy_uart_driver.UART`'s constructor argument (`src/asy_uart_driver.py:58,
76`), read by `UART_Comm` from the bus (`asy_uart_comm.py:269, 282`); `UartLinkExerciser` passes `uart` straight on
(`asy_uart_link_driver.py:65-78`). (2) OR71.a (2) "a first boot with no config file writes nothing" (row :414) supports it.
(3) the pause check sits inside each chunk's `_op_lock` (`asy_fram_manager.py:95-98, 127-130`), so pause + one lock cycle per
chunk excludes every writer; OR120.a (2) asks for the overwrite in chunks. (4) `_SYSTEM_COMMAND_GROUP` is
`buildgen/definitions.py:55-62`, emitted statically at `:354`. (5) the group spans `:55-62`.

**Conflicts 1-8 checked against the unit files, all as stated.** 1: A.U11.04 checks `_closed` "first, before the lock" and
awaits `_pending_flush` "as today" (U11.md); the in-lock re-check is additive. 2: A.U20.06 runs the loop inline in
`supervise_tasks()`; its L0 awaited-call order holds. 3: A.U11.03 point 5; suppression while a shutdown runs is additive
(but key it on `_feed_owned`, V.SUPP_owner_0930.08). 4: A.U16.19 removes `override_pause`; `invalidate()` is a new product path used
only by the erase. 5: A.U23.17's `window.confirm` belongs to the DNS fallback Clear button, not the system commands;
LEAD/R32 at HEAD names no confirm; A.S0930.20 (5)'s zero-call spy concerns only the command card. 6: A.U17.32's sentence
"both ends agree by construction" (U17.md) must change as stated. 7: A.U26.71 (2) replaces `_ROUTE_DISPATCH_FIELDS` with
A.U6.17's derived classes; the value-level exception belongs there. 8: OR31.a (3) (2026-09-25) vs OR120 (2026-09-30) —
newer wins. Conflict 9: V.SUPP_owner_0930.22.

**DONE-AT-HEAD checked.** A.S0930.18: as the header states (v1.29.0 source). A.S0930.03's protocol half:
`tests/test_uart_comm_hazard.py:51, 1273-1296` register every `_check_*` in both modes.

**Owner quotes checked** against rows :503-522: exact except A.S0930.03's invented OR116.a phrase (V.SUPP_owner_0930.01) and
A.S0930.17's shortened OR120.a (2) phrase (V.SUPP_owner_0930.10). Permanent-text scan of every planned comment, message, doc
and test string: no audit ID (the changelog's own "A7" is a permanent entry number).

**Open points.** "None" holds: action words (OR122.a (2) leaves them to the agent), the optional key with default none
(OR116.a (2), OR123.a (1)), Wi-Fi inside the reset (OR124), latch at acceptance (stricter than OR120.a (1)) all settle
from rows; OR119.a (5) is correctly an agent proposal.

## Part B2 (HEAD d11d38c)
Counts: 11 actions checked (A.S0930.31-.41) plus the in-file amendments (conflicts 10-13, the .27 blast edit, the
design block, the OR126 ledger row, section C's co-land paragraph) · OK 2 (.34, .39) · FIX 9 (.31, .32, .33, .35, .36,
.37, .38, .40, .41) · REJECT 0; ledger complete (the OR126/OR126.a (3) row covers the clause); 13 findings (FIX 12, ADD 1)

HEAD `d11d38c`; `git diff --stat b46b352 d11d38c -- . ':!audit' ':!PROJECT_AUDIT_PLAN.md'` is empty, so every code line
Part B2 cites holds (re-opened here). Owner rows read: OR119/OR119.a, OR120/OR120.a, OR121.a, OR122.a, OR126/OR126.a
(`PROJECT_AUDIT_PLAN.md:509-524`); OR126 "(3) reboot and bootloader on the controlled shutdown sequence: "a"" and OR126.a
(3) are quoted exactly. **Primary sources checked** (v1.29.0, scratchpad `mp/`, `git describe` = `v1.29.0`):
`extmod/modmachine.c:70-73` is `machine_bootloader()`, which calls `mp_machine_bootloader()`; `ports/rp2/modmachine.c:91-97`
(board hook, ROSC enable, `reset_usb_boot(0, 0)`), `:74-79` (`machine.reset()` = `watchdog_reboot(0, SRAM_END, 0)`);
`mpconfigport.h:238-240` (empty default hook; `boards/RPI_PICO_W/mpconfigboard.h` defines none); `lib/pico-sdk` empty;
`machine_mem_backup.c:36-40`; `rp2_flash.c:170-199` (critical section: other core locked out, IRQs off), `:273-326`
`writeblocks()` — **and `:280-282, :299-301`: `mp_event_handle_nowait()` between a block's erase and its program**, which
runs `mp_handle_pending(MP_HANDLE_PENDING_CALLBACKS_AND_EXCEPTIONS)` (`py/scheduler.c:259-268`), i.e. scheduled soft-Timer
callbacks. Console: `MICROPY_HW_USB_CDC_TX_TIMEOUT` 500 ms (`ports/rp2/mphalport.h:36`), a wait per
`mp_hal_stdout_tx_strn()` call while the host holds DTR (`shared/tinyusb/mp_usbd_cdc.c:108-137`, OR126.a (2)); `print(a,
b)` issues one call per argument, separator and line end (`py/modbuiltins.c:420-432`, `shared/runtime/stdout_helpers.c:40-57`).
Watchdog: `WDT(timeout=8000)` is set in the generated boot (`buildgen/codegen.py:381`), not in `src/system_service.py`
(which receives the object); cap 8388 ms (SPEC `:3445`). Answers/codes: `_dispatch_system_cmd()` maps `True`/`False`/raise
to "Valid"/"Failed"/"Failed"+errno 2 (`src/asy_webserver_service.py:503-517`); `js/mock-server.js:16, 421` stateless;
`js/render.js:130-143` renders any "Failed"; codes 3/4 are A.U11.05's table (U11.md:25) — all as the file states.

## Findings

- V.SUPP_owner_0930.B2.01 | A.S0930.32 (and A.S0930.13 (4), A.U11.03 point 5; conflict 11) | FIX | The re-check closes
  the preflight yield only. The escalation has its own yield between its `_feed_owned` check and its arm: A.S0930.13 (4)
  runs the branch "only `if not self._feed_owned`", then A.U11.03 point 5 does `await self.pr.err_s(…)` (persisted:
  `print_log.py:203-219` → FRAM chunk write → `await asyncio.sleep(0)`, `src/asy_fram_manager.py:276, 284`), then
  `self._force_watchdog_starve = True`, then `await self._reboot(…)`. A `reboot`/`bootloader` (no preflight) or an
  `erasefram` whose preflight does not suspend, accepted during that `err_s`, passes rule (2) and the re-check
  (`_reset_armed` still `False`), sets `_feed_owned`; the escalation then resumes, sets the starve flag — which
  `_own_feed()` honours, so the accepted sequence runs **unfed** from there — and arms its own reset (code 5), which fires
  4 s later mid-sequence (for `erasefram` mid-erase), S6's `_reboot()` then logs "already armed". So one reset is armed
  (U11's guard), but the command answered "Valid" runs under the escalation's reset — the exact outcome A.S0930.32 exists
  to prevent. Reachable on every device whose SYSTEM logger is FRAM-backed. | Change gains (2): "The escalation side of
  the same race: A.U11.03 point 5's branch re-checks right after its log write, before the starve flag: `if not
  self._reset_armed: await self.pr.err_s(…)`; `if self._feed_owned: continue` (the next pass parks); `self._force_watchdog_starve
  = True`; `await self._reboot(_RR_TASK_BUDGET, "Reboot triggered", system_reset)`. From that re-check to `_reboot()`'s
  `self._reset_armed = True` (A.U11.03 point 2 (b), before its first await) nothing awaits, so exactly one of the two
  owns the reset. Comment (≤ 3 lines): "Re-checked after the log write, which yields: a system command accepted
  meanwhile owns the reset now, and nothing awaits from here until _reboot() marks it armed."" Blast tests gain: new L1
  `tests/test_system_service.py` `test_a_command_accepted_while_the_escalation_logs_keeps_its_own_reset` — the SYSTEM
  logger's `err_s` rebound from outside to await an `asyncio.Event` for the budget entry; the supervisor (always-failing
  starter, `_FastAsyncSleep`) reaches it; `reboot_system()` → `True`; the event is set: `_force_watchdog_starve` False,
  one `reset_timer.init`, region 0 code 3, `feed_count` rose through S1-S6; the same with `erase_fram()` → code 8 and
  every fake-chip byte 0. Site += "A.U11.03 point 5's escalation branch (`_supervise()` after A.S0930.13)". Conflict 11
  → "… so the gate re-checks `_reset_armed` after the preflight, and the escalation re-checks `_feed_owned` after its
  log write."

- V.SUPP_owner_0930.B2.02 | A.S0930.33 (3) (and the design block's timing paragraph `:80-84`, S6 row `:78`, A.S0930.14
  S6, A.S0930.36 (b), A.S0930.41) | FIX | Worst-case gap from the sequence's last feed to the reset: S6 feeds, then
  `_reboot()` runs record → no-op flush pass (one `config_lock` cycle per store) → `pr.evt(message)` → the FRAM manager's
  `set_pause()` line (`src/asy_fram_manager.py:727`) → "Storage paused" (`system_service.py:124`) → arm; the timer fires
  `_RESET_DELAY` later and only sets `_reset_due`; `_reset_when_due()` then waits for the loop (the longest non-yielding
  stretch of a still-running task — connection tasks, the unsupervised captive DNS — plus gc) and runs its no-op flush
  pass before `action()`. At the shipped level that is ≈ 4.0 s against the 8000 ms `WDT` (margin ≈ 3.9 s; fine). But the
  file's "4 s + `_reboot()`'s own few ms" omits the wake latency and the prelude's console output: at DebugLevel ≥ 4
  (`_LOG_EVENT`, `print_log.py:57, 124-126`) the three lines are 14 `mp_hal_stdout_tx_strn()` calls, each waiting up to
  500 ms while a host holds the port open without reading (OR126.a (2)'s accepted condition) — up to 7 s before the arm,
  so the watchdog (8 s after S6's feed) fires ~1 s after the arm, before the 4 s timer: a `bootloader` then restarts
  the firmware instead of entering BOOTSEL. HEAD never ran this tail unfed (the supervisor fed through it), so the
  exposure is new with the sequence. | (3) → "(3) The last own feed moves to the arm: `_reboot(self, code, message,
  action, *, fed: bool = False)` calls `self._own_feed()` as the statement immediately before `self.reset_timer.init(…)`
  when `fed`; S6 becomes `await self._reboot(code, message, action, fed=True)` with no feed of its own; the escalation
  passes nothing (it is starved anyway). A hung prelude (record, flush pass) is still never fed and no feed follows the
  arm. The unfed tail is then `_RESET_DELAY * 1000` plus the reset task's wake latency and its no-op flush pass —
  ≈ 4.0 s at the shipped level, ≈ 3.9 s under the 8000 ms `WDT` (`buildgen/codegen.py:381`; rp2 caps it at 8388 ms);
  at a debug level of 4 or more with a host that holds the port open without reading, each line another task prints in
  the tail can take ~2 s of that margin (the accepted debug-mode limitation). `:40` comment as planned. A.U8.08's row
  Dependants gain "the unfed tail after a system command's last feed: `_RESET_DELAY` plus the reset task's wake
  latency"." Design `:78` S6 row → "`await self._reboot(code, <message>, <action>, fed=True)` — U11's path (record →
  flush (no-op) → pause (already) → own feed → arm); no feed after the arm | once, immediately before the arm |
  `_reboot()`'s own line"; design `:81-84` "After S6 nothing feeds: the reset fires within `_RESET_DELAY` of the last own
  feed (4 s + `_reboot()`'s own few ms, under the 8000 ms `WDT`, `codegen.py:381`)" → "The last own feed is
  `_reboot()`'s, immediately before the arm; after it nothing feeds: the reset runs `_RESET_DELAY` later plus the reset
  task's wake latency (≈ 4.0 s, under the 8000 ms `WDT`, `codegen.py:381`)". A.S0930.14 S6 likewise. A.S0930.36 (b)
  and A.S0930.24 (b) gain "the last `feed_times` entry is stamped after `_reboot()`'s last console line and flush pass and
  before `reset_timer.init` (a recording `print` stand-in and the fake Timer's `init` stamp)". Depends += "A.U11.03
  (point 2's signature gains `fed`)". A.S0930.41's SPEC A.8 paragraph gains (actor-tagged, no ID): "At a debug level of 4
  or more, a USB host that holds the serial port open without reading stalls each console line up to about 2 s; such
  stalls in the last 4 s before a system command's reset can let the watchdog end it instead — a `bootloader` then
  restarts the firmware rather than entering BOOTSEL."

- V.SUPP_owner_0930.B2.03 | A.S0930.37 (1) | FIX | (a) "build, `run_setups()` (A.U24.79's boot helper), …" inside the
  command coroutine: `build()` is `run(_boot(...))` (`tests/_sensortask_scenarios.py:132-133`), so calling it inside the
  coroutine is a nested `asyncio.run()` — the Unix-port segfault CLAUDE.md forbids. (b) "`_dispatch_async(…)` returns
  `app.dispatch_request(req)`" returns an un-awaited coroutine. (c) The coroutine leaves `supervise_tasks()` (waits on
  `_never`) and possibly `_reset_task` parked in the shared queue. | (1) → "`async def _dispatch_async(module, method,
  path, json_body=None) -> Response`: builds the request as `_dispatch()` does today and `return await
  app.dispatch_request(req)`; `_dispatch()` becomes `return run(_dispatch_async(...))`. A command scenario is one
  coroutine driven by one `run()` from the synchronous scenario function: inside it `module, wdt = await
  boot_generated(device, cfg_path=…)` (A.U24.79's awaitable helper, which runs `build_system()` and `run_setups()`;
  never `build()`), `await module.sysfunct.start_tasks(module._collect_task_starters())`, `sup =
  asyncio.create_task(module.sysfunct.supervise_tasks())`, `await _dispatch_async(...)`, `await
  module.sysfunct._shutdown_task`, the fake `reset_timer.trigger()` and `await asyncio.sleep(0)` until
  `module.sysfunct._reset_task.done()`, then `sup.cancel()` awaited (catching `CancelledError`)." Depends += "A.U24.79
  (`boot_generated()` awaitable)".

- V.SUPP_owner_0930.B2.04 | section C, Part B2 co-land paragraph (U25) | ADD | A.U25.56 (3) (U25.md:1780) calls
  `reboot_system()` in-process with the alarm pool empty and expects the starve fallback: "`would_have_triggered_count >=
  1` within `timeout + 1 s`, no `machine.reset()` call". Under Part B2 that call enters the sequence; without the supervisor
  task S1 waits forever with the feed latched, so the assertion passes for the wrong reason (an S1 hang, not the arm
  failure). Not in the co-land list. Also U20.md:1495's ladder text ("error budget exhausted → `reboot_system()`
  (A.U11.03)") contradicts A.U11.03 point 5 and A.S0930.31 (4)/.34 (2). | U25 bullet gains: "A.U25.56 (3): the case
  starts `start_tasks()` and `supervise_tasks()` as a task (A.U20.06), calls `reboot_system()` → `True`, and asserts once
  `sysfunct._shutdown_task` is done: `_force_watchdog_starve` True, region 0 code 6, no `machine.reset()`/`bootloader()`
  call, and `would_have_triggered_count >= 1` within `timeout + 1 s` of the last `feed_times` entry — the S6 arm-failure
  path, L2 half of A.S0930.36 (d)." New U20 bullet: "A.U20 recovery-ladder paragraph (U20.md:1495): "error budget
  exhausted → `reboot_system()`" reads "→ `SystemService._reboot()` directly (A.U11.03 point 5), never `reboot_system()`"
  — audit text only, A-C corrects it."

- V.SUPP_owner_0930.B2.05 | A.S0930.35 Blast and section C's U11 bullet | FIX | The two disagree: section C says A.U11.03's
  new tests "(a) and (d) hold for the direct path", A.S0930.35's Blast says "A.U11.03's new (a)-(e) … drive the commands
  through the harness". A.U11.03 (e) ("`asyncio.create_task` replaced by a function raising `MemoryError` inside
  `_reboot()`: starve flag set, record code 6") cannot go through `reboot_system()` any more: S0's own `create_task`
  raises first and answers `False` with no starve (A.S0930.31 (1), .35 (c)). | Section C U11 bullet: "its new L1 tests
  (a) and (d) hold for the direct path" → "its new L1 tests (a) (no re-arm), (d) (record → flush → pause order) and (e)
  (`create_task` `MemoryError` inside `_reboot()` → starve, code 6) call `_reboot()` directly; (b) (a raising flush) runs
  through the harness — S2's flush raises with FRAM open, one CALLBACK entry persists, the reset is still armed with code
  3; (c) is the escalation". A.S0930.35 Blast "A.U11.03's new (a)-(e) and A.U11.07's "each intended path" test (reboot,
  bootloader → 3, 4) drive the commands through the harness" → "A.U11.03's new (b) and A.U11.07's "each intended path"
  test (reboot, bootloader → 3, 4) drive the commands through the harness; A.U11.03's (a), (d) and (e) call `_reboot()`
  directly".

- V.SUPP_owner_0930.B2.06 | A.S0930.40 (1)-(2) | FIX | The L4 bound does not say it must exclude a watchdog reset, and
  nothing else on the bench can: the record (code 3/4) is written before the arm, so a watchdog reset after S6 reads the
  same `ResetReason`, and rp2 reports `WDT_RESET` for `machine.reset()` too (`watchdog_reboot()` then `watchdog_caused_reboot()`, `ports/rp2/modmachine.c:74-88`).
  Timer path: reply-to-reset ≤ S1 (≤ `_TASK_CHECK_TIME` + a pass) + S2-S4 + ≈ `_RESET_DELAY`; watchdog path ≥ 8 s.
  The test's header comment (`tests_hardware/bench/test_end_to_end_timing.py:19-21`, "storage_pause()-then-wait … WDT
  isn't starved mid-sequence") also goes stale. | (1) gains: "the named margin stays below `8000 − (_RESET_DELAY +
  _TASK_CHECK_TIME) * 1000` ms (2 s, computed from the AST-read constants and the generated `WDT(timeout=…)`), so the upper
  bound also excludes a watchdog reset, which records the same code; its measured S2-S4 share is recorded in
  `result_note`." Header comment `:19-21` → "A commanded reboot over REST runs the controlled shutdown and resets through
  the armed timer, never the watchdog, on real timing." (2) the same bound.

- V.SUPP_owner_0930.B2.07 | A.S0930.41 | FIX | (a) Planned SPEC A.8 text "the reset follows up to one supervisor period plus
  4 s later" is wrong for `resetconfig`/`erasefram` (S2-S5, the whole-chip erase) and omits S2-S4 for all four. (b) The
  `README.md:314-322` line (REST `bootloader` as a reflash entry) answers no clause — OR126.a (3) and LEAD/R32's doc clause
  name SPEC A.8 and `tests_hardware/README.md`; the reflash recipe is not made stale by Part B2 (overreach). (c) The SPEC
  A.4 `:195-198` sentence it rewrites continues "(measured 20/20 in the twin against the ~1-in-8 unpaused rate)", a figure
  taken with `mempause` held over a SIGINT shutdown (Run 5c at HEAD, `digital_twin/README.md:483-489`), which A.U25.36
  turns into a real commanded reboot. | (a) → "The reply comes first; the reset follows once the supervisor has stopped
  (up to one 2 s supervisor period), the steps have run (for Erase FRAM the whole-chip overwrite) and the 4 s reset delay
  has passed." plus B2.02's debug-stall sentence. (b) drop the README line and its harness note; `README.md:314-322`
  unchanged (if wanted, one Agent-proposals entry). (c) the A.4 replacement ends "… which gates every
  `_write()`/`_read()`/`clear()` so nothing can be in flight (the twin's Run 5c proves it for a commanded reboot)" — the
  figure is re-measured by A.U25.36, A-C merges.

- V.SUPP_owner_0930.B2.08 | Part B2 preamble (`machine.bootloader()` under the sequence) | FIX | Two precisions. (a)
  `extmod/modmachine.c:70-73` is `machine_bootloader()`, the wrapper that calls `mp_machine_bootloader()`. (b) "A flash
  erase or program cannot be in flight when any Python code calls them … returns only when it is done (`:170-200,
  279-313`)" is true per operation, but `writeblocks()` runs scheduled callbacks between a block's erase and its program
  (`rp2_flash.c:280-282`, `mp_event_handle_nowait()`), so a soft-Timer callback that resets by itself — HEAD's `lambda _b:
  action()`, `src/system_service.py:126` — can land inside a littlefs block write. The conclusion holds only because
  A.U11.03 point 2 (f) makes the callback set `_reset_due` alone and runs the action in a task. | (a) "`machine.bootloader()`
  is `mp_machine_bootloader()` (`extmod/modmachine.c:70-73`)" → "`machine.bootloader()` is `machine_bootloader()`
  (`extmod/modmachine.c:70-73`), which calls `mp_machine_bootloader()`". (b) after "(`:170-200, 279-313`)" add: "— but
  `writeblocks()` runs pending scheduled callbacks between a block's erase and its program (`:280-282`), so a Timer
  callback that resets directly (HEAD, `system_service.py:126`) can cut a littlefs block write; A.U11.03 point 2 (f)'s
  callback only sets `_reset_due` and the action runs in `_reset_when_due()`, a task, which never runs inside
  `writeblocks()` — the premise this finding needs." Depends of A.S0930.31 += "A.U11.03 point 2 (f)".

- V.SUPP_owner_0930.B2.09 | conflict 10 (design block, A.S0930.12, A.S0930.14) | FIX | Part B2 leaves this file's own
  text contradicting it and hands the merge to A-C, which merges across unit files; the design block is "Settled here once
  and used by A.S0930.09-A.S0930.41". Also conflict 10's A.S0930.21 (d)/A.S0930.22 (6) amendment is not needed: both test a
  reboot during a `resetconfig`/`erasefram` sequence, where `False` stays right. | Amend in place: design `:51` "3.
  `self._shutdown = purpose` is set before any await, so from here `reboot_system()`, `reboot_bootloader()` and
  `pause_permanent_storage()` answer `False` ("Failed");" → "3. `self._shutdown = purpose` is set before any await, so
  from here another purpose's command and `pause_permanent_storage()` answer `False` ("Failed") and the same command
  `True` (rule 1);"; S0 step 4 gains "reboot and bootloader: none", and a step "4a. `_reset_armed` re-checked
  (A.S0930.32)"; `:80` "`code` is `_RR_CONFIG_RESET` (7) / …" gains "; `_RR_REBOOT` (3) / `_RR_BOOTLOADER` (4) for reboot and
  bootloader, whatever S2 met"; S5 row prefixed "(Reset to defaults and Erase FRAM only)"; `:118` → "| the supervisor
  escalation's reset armed | refused at S0, before and after the preflight ("Failed"), nothing changed; the armed reset
  proceeds (a commanded reboot or bootloader arms only in its own S6) |"; `:119` → "| another purpose's command or
  mempause during the sequence | refused ("Failed"); the same command again: "Valid", nothing new started; the supervisor
  escalation is suppressed once `_feed_owned` is set and re-checked after its log write (the sequence resets anyway) |";
  A.S0930.12 "Existing commands: `reboot_system()`/`reboot_bootloader()` → `-> bool`: `if self._shutdown: return False`,
  else the U11 path and `return True` (a repeat while armed stays U11's "request ignored" with `True`);" → "Existing
  commands: `reboot_system()`/`reboot_bootloader()` enter the same gate (A.S0930.31 (1));", and its acceptance line uses
  `_purpose_name(purpose)`; A.S0930.14 S5 prefixed "(config reset and erase only)" and S6 as B2.02. Conflict 10 then
  reads "… applied in place; A.S0930.21 (d) and A.S0930.22 (6) unchanged (they concern the other two purposes)".

- V.SUPP_owner_0930.B2.10 | A.S0930.36 (c) (and A.S0930.24 (c)'s S6 row) | FIX | "the sequence task not done, no reset
  armed except in S6" is false for S6: S6's hang is "a reset Timer whose callback never fires", after `_reboot()` returned,
  so the sequence task is done and the pending one is `_reset_task`. | → "for S1-S4 the sequence task is not done and no
  reset is armed; for S6 the sequence task is done, `svc._reset_task` is not, and the reset is armed".

- V.SUPP_owner_0930.B2.11 | A.S0930.31 (behaviour that changes) | FIX | "a commanded reset whose sequence hangs before S6
  reads `ResetReason` 2 at the next boot" misses A.U11.06's decode: a command accepted in the boot window (after the
  webserver started, before `boot_phase(BOOT_DONE)` follows the first NTP force sync) leaves region 1 at phase 4 or 5, so
  a hang reads 10 + phase. | → "reads `ResetReason` 2 at the next boot, or 10 + the boot phase when it was accepted in the
  boot window before the boot was marked done (A.U11.06's decode) — the record is written in S6's `_reboot()`".

- V.SUPP_owner_0930.B2.12 | A.S0930.33 (2) | FIX | "its `finally` blocks only release `wifi_mode_lock`,
  `asy_wifi_service.py:563, 589, 859`" cites three of seven; the fact holds for all. | → "`asy_wifi_service.py:229,
  245, 275, 367, 563, 589, 859`".

- V.SUPP_owner_0930.B2.13 | A.S0930.38 (5) | FIX | After the in-process rows assert at the armed reset, only
  `reset_timer.deinit()` is undone; `sysfunct._reset_task` (waiting on `_reset_due`) and the `supervise_tasks()` task
  (waiting on `_never`) stay parked in the process-wide queue and can resume in a later test (A.U25.07's concern). | "then
  `reset_timer.deinit()` from outside" → "then from outside `reset_timer.deinit()`, `sysfunct._reset_task.cancel()` and
  the `supervise_tasks()` task's cancel, each awaited (catching `CancelledError`), so no real-time Timer fires and no
  parked task resumes in a later test of the process".

## Checked OK (Part B2)
A.S0930.34, A.S0930.39; A.S0930.27's blast edit (Run 5c's commanded reboot runs the sequence); the OR126/OR126.a (3) ledger
row and Counts; conflicts 12 and 13 (A.U11.03 point 4 and A.U11.04's window superseded for commanded resets only; A.U25.36
(3)/A.U25.55 (b) need the `_TASK_CHECK_TIME` term); section C's co-land claims checked against U11.md (A.U11.03 points 4-5,
.04, .05, .07), U20.md (A.U20.06), U25.md (A.U25.07, .09, .36, .55, .57, .74), U26.md (A.U26.26, .28), U8.md (A.U8.08),
U10.md (A.U10.08, .09), U23.md (A.U23.33), U24.md (A.U24.43, .54), U29.md (G5/R57 register fix) — as stated except
B2.04/B2.05. Grep of `reboot_system|reboot_bootloader|SystemCmd|"reboot"|"bootloader"|_reset_when_due|_RESET_DELAY|
reset_timer|reset_count|bootloader_count` over `src/ tests/ digital_twin/ tests_hardware/ tests_scripts/ buildgen/
scripts/ js/ tests_js/`, SPEC, README, `tests_hardware/README.md`, `digital_twin/README.md`, CLAUDE.md: every existing
pin is named by .31-.41 or holds (`tests/test_asy_webserver_service.py:536-583` fake callback; `tests/test_digital_twin_machine.py:420-438`;
`tests/test_reset_call_site_invariant.py`; `tests_hardware/harness.py:474-479` `enter_bootloader()`; `tests_js` stateless mock).
Escalation vs the sequence: no deadlock (S1's park wait ends at the supervisor's next pass top, the escalation no longer
returns, A.U11.03 point 5; a supervisor that never parks leaves S1 unfed, i.e. a watchdog reset, never a fed hang); the
one race is B2.01. Permanent-text scan of every planned comment, message, test name and doc string in .31-.41: no audit ID.
