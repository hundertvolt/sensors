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
