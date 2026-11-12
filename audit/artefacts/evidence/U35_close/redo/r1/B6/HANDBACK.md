B6 hand-back, written by the agent (2026-11-03); Gate, FW and Findings filled by the lead after its session ended

Worktree `S/wt-b6`, branch `audit/r1-b6`, from 90691b6d. One commit: **1b4caa17** (source, tests and docs together).
Nothing pushed. Run logs: `S/u35/lead/b6_*.log`; the gate: `S/u35/lead/b6_gate.log`. Line numbers below are the
action list's (90691b6d tree) unless a file or commit is named.

## Items

1. **Receive-ring teardown: carried in (admitted fix)**. `_rx_stop()` (a static method beside `_arm_rx()`) points the
   data channel's CHAIN_TO at itself through the `ctrl` attribute, then aborts reload and data; `_arm_rx()` and
   `deinit()` call it. `_CTRL_CHAIN_TO_LSB`/`_MASK` added. `tests/rp2.py` and `digital_twin/rp2.py` both raise
   `RuntimeError` for `active(False)` on a busy channel chained to another live channel, and both gained the `ctrl`
   setter (BUSY stripped); `_ChannelProbe.ctrl` added; `uart_dma_ring_interrupts_off.py` drains during the stream
   (916fb878's hunk applied as is). Test: the fakes first, **16 driver tests red** (b6_r1_red: 158/174, all
   `RuntimeError: DMA abort of a busy chained channel`, the bench count), then green with `_rx_stop()` (b6_r1_green
   174/174 at both stages). Dev's twin UART files green with the twin setter (b6_r1_twin: link 22, machine_uart 26,
   comm_hazard 10, field_sweep 10, both stages), mypy's twin pass clean (b6_mypy1/3). Changelog **B94** (the bench
   branch's B93 text, with the RP2040-E13 cause). Part F line: F.5.8 (one sentence after the soft-reset note);
   `digital_twin/README.md`'s `rp2.py` bullet names the raise. The fix alone, compiled onto 90691b6d's driver,
   adds **+64 B** (7,727 to 7,791; the bench branch measured +66 on its own base), inside this unit's net decrease.
2. **UARTRSR claim: text only.** The driver's header line and the `_RSR_ERRORS` comment, SPECIFICATION.md C.3.2,
   the J.7 L3 sentence (":9991": "they do: they hold the byte the DMA read last") and A13's text amended in place
   (dev bench, 2026-10-29: 8 of 134 flagged; dev runs `crc = "none"`). No code change.
3. **Zero-length guard: removed** (B48 reversed). The four guards go; B56's negative-size refusal stays.
   `writefrom()`'s `crcsize is None` check keeps its pre-audit form **without** B89's "Unreachable" comment: with the
   zero guard gone, `add_into()` answers `None` for a zero size, so the line is reachable again and the comment would
   be false. Tests: `:2222`, `:2229`, `:2239` went; the pre-audit
   `test_a_crc_framed_write_of_nothing_is_refused_rather_than_sent_as_a_bare_crc` returned and read **red** on the
   committed source (b6_r3_red), green after; pre-audit `:1209`/`:1441` green (`:1441`'s comment back to the pre-audit
   text). Found on the way (b6_r3_green, red): `test_readinto_until_complete_refuses_a_negative_size` also pinned the
   zero case (`== 0`); that one line went, and `test_read_until_complete_refuses_a_negative_size` lost its matching
   zero line and clause (green either way; removed so neither negative-size test pins the removed guard).
4. **Write deadline: removed** (B61 reversed). `_write_all(uart, buf)` waits on `ready(POLLOUT)` and `txdone()`;
   `write()`/`writefrom()` take no `timeout_ms`; comm `_send_ack()`/`_write_frame_with_ack()`, the link's
   `_write_raw()` and `uart_comm_hazards.py:118` pass none. Tests: driver `:2325`, `:2343` and comm `:1446` went;
   `:2287` and `:2357` green (b6_r4).
5. **Closed-channel and deinit-mid-read guards: removed** (B54, B55's closed-channel clause). `_buffered()`'s,
   `_rx_copy()`'s and `_rx_level()`'s catches, `_read_delimited()`'s post-yield check and `ready()`'s
   `return self.poller is not None` (now `return True`) go; `deinit()`'s stop (with its catch), `init()`'s re-arm,
   fixed-ring refusal and teardown line stay. Tests: `:2093`, `:2414`, `:2443`, `:3153`, `:3171` went; `:482`, `:502`
   (the re-init over a closed channel logs first, then raises from `_rx_stop()`'s `ctrl` read), `:582` green (b6_r5).
6. **Narrowing branches: typing-side form.** Driver `_arm_rx()`, `_rx_copy()`, `_rx_line_len()`, `_rx_peek()`; comm
   `_min_rx_ring()`, `_send_train()`'s pieces branch, `_take_discarded()`; link `_run_hazards()`: each `if x is None:
   return ...` became a typed local, `name: T = self._attr  # type: ignore[assignment]  # <why it is set>`; the
   pieces branch is one line, `pieces.read_at(sent, self._tx.get_data_buf()[0:size])  # type: ignore[index]  # ...`
   (read_at's False was the same unreachable case). `_rx_peek()`'s "-1 without a ring" comment went with its branch.
   B89's guards kept (driver `:813` aside, item 3). mypy's three passes clean; no test changed.
7. **Sender cap: removed** (B65/B86 reversed). `_check_cap()` and its three calls go; `_chunks_for()` folded back
   into `_chunk_count()` (its pre-audit comment). Tests: `:2730`, `:2760` and the helper `_over_cap_calls()` went;
   `:2706`, `:2720`, `:2777` green; `:2795` read first: it raises the initiator's own cap for its SET half and gives
   GETs no `exp_size`, so no sender check was in its path; green. The twin's `--test-uart-over-cap` stays in the
   harness (gate, below).
8. **Dropped-frame texts: removed** (B78/B85 reversed). The four pending/dropped pairs log their pre-audit texts;
   `_peek_discarded()` folded back into `_take_discarded()`; UC-9's count and `_read_frame()`'s wrong-length
   adjustment stay. Tests: `:1373`, `:1384`, `:1426`, `:1436` and their helper `_crc16_pair_dropping()` went; the E89
   tests green. Kept unchanged: `test_a_get_left_unanswered_keeps_its_silent_message` and
   `test_a_listen_cleared_before_any_frame_keeps_its_silent_message` (they assert the pre-audit texts; their
   "dropped not in" lines now hold trivially). BACKLOG.md's bench-round item lost its dropped-frame clause.
9. **W57: removed** (B75 reversed, the lead's decision). `_WRN_UART_RX_OVERRUN` and its read in `_read_frame()` go;
   catalog `"57"` deleted (no placeholder). Tests: `:1363` renamed
   `test_a_frame_read_failing_on_a_receive_error_fails_under_its_own_code_alone` (`[E81]`, `rx_overruns == 1`) and
   `:2850` (`[E22]` alone) changed first, **red** (b6_r9_red: `['W57', 'E81']`, `['W57', 'E22']`), green after;
   `:2909`'s W57 line dropped. Changelog **B96**.
10. **`_call()`: `*args` only.** The action list's form, `Callable[..., object]`, fails mypy's
    `disallow_any_explicit` (b6_mypy1: `explicit-any` at the def), which is why B69 used a `ParamSpec`; a
    `TypeVarTuple` form fails too (the MicroPython stub `typing` has no `TypeVarTuple`/`Unpack`, b6_mypy2). Taken
    (agent, 2026-11-03): the pre-audit signature with `# type: ignore[explicit-any]  # every callback shape; a
    ParamSpec's **kwargs would build a dict per call` on the def line. `ParamSpec`/`_P` gone. mypy clean; the
    callback tests green.
11. **`UARTLinkDriver.setup() -> None`.** `initialized` still follows `UARTComm.setup()`. Tests: `:184`, `:187`,
    `:557` read `initialized` (mechanical), the test `Pair.setup()` returns both flags, the twin link builder
    (`tests/test_digital_twin_uart_link.py:286`) likewise; `tests/test_readiness_gates.py`'s link test renamed
    `..._stays_uninitialized_and_persists_the_refusal` and asserts `is None`, **red** against the committed link
    driver (b6_r11_red), green after. No hardware script reads the link's bool (they build `UARTComm`).
12. **`PieceBuffer.copy_into(dest)`: shrunk.** One line, `len(dest) >= self._size and self.read_at(0,
    memoryview(dest)[0 : self._size])`. Tests: `_copied()`, `:548`, `:558` changed (renamed `..._copies_the_whole_
    buffer_into_the_front_of_dest`, `..._a_short_dest_copies_nothing`); they pass on the old code too (no caller
    passed `start`), so their red reading is a planted break: dropping the length guard fails the short-dest test
    (b6_r12_plant), green with the real form (b6_r12). SPECIFICATION.md's G.2 line follows.
13. **`cobs` in the crossover exchange: added.** `_driver(bus, mode)` builds `CRC16()` for "crc16" and
    `FramingCOBS(5 + PAYLOAD_SIZE)` for "cobs" (no CRC), per driver; the exchange test takes `[*_CRC_MODES, "cobs"]`
    (a list: ruff PT007); recovery, hazards and load keep `_CRC_MODES`. `bench_facts.pyi:57` unchanged (`CRC_MODE: str`
    already takes it). `--collect-only` lists `[cobs]` (b6_r13_collect: 17/21, 4 deselected by the default gates);
    `--twin` run of the exchange test, all three modes, **3 passed** (b6_r13_twin). Docs: the test's header,
    `tests_hardware/README.md` (the coverage paragraph), SPECIFICATION.md J.7's L3 sentence.
14. **Codec bound and counter: kept.** `test_asy_framing_codecs.py` 21/21 at both stages; item 13's twin `cobs` run
    passes at E92's floor.
15. **A14, A15: kept.** Comm `:874`, `:1100` and the twin field sweep green (b6_uartset, gate).
16. **Kept as landed**: existing tests green.
17. **Nothing to change.**
18. **Other hunks.** `review_hunks.py 25caf528 1b4caa17` over the four files: 125 unmarked (141 before). I mapped them
    by mechanism, against the scan's per-mechanism inventory of these files (`scan/B.md` UC-1..22, UD-1..9, UL-1..5,
    "AST-normalised diff read in full") plus B1's two commits since (39f1615b, a8d0028a: rows 16's loggers): every
    hunk falls under rows 1-17, the foundations' renames and member order, or B1's loggers. Named to the lead, not
    changed: the link driver's `_read_raw()`/`_write_raw()` `if bus is None` guards (UL-1, the same never-taken
    narrowing as row 6's `_run_hazards()` one, not on the list). I made no line-by-line restore pass beyond that.

## Knowledge lines (removed items)

All removed code is at 90691b6d.
- Zero-length guards (B48): `write()`/`writefrom()` reported success sending nothing and the `*_until_complete()`
  reads answered empty for a zero size, in every CRC and codec mode; no caller passes zero (the protocol always
  moves whole frames).
- Write deadline (B61): `timeout_ms` on `write()`/`writefrom()`/`_write_all()`, the whole write's deadline, passed
  by `UARTComm` and the link's raw write; without flow control the TX ring drains at the baud rate, no stall seen.
- Closed-channel catches and deinit re-checks (B54, B55's clause): a closed DMA channel read as a silent line, and
  `ready()`/`_read_delimited()` re-checked the bus after their yields; channels close only in `setup_rx_ring()`'s
  failure arm, which drops both references, and no product caller deinit()s a live link.
- Narrowing branches (row 6): eight `if x is None: return ...` branches no caller could take; typed locals now.
- Sender cap (B65/B86): `_check_cap()`/`_chunks_for()` refused at the argument checks a train over the own cap; the
  receiver's refusal at the header (A16) is the one refusal.
- Dropped-frame texts (B78/B85): `_peek_discarded()` and four "... dropped a corrupted or incomplete frame" texts
  told a dropped frame from a silence in the log text only.
- W57 (B75): a warning beside the frame's own error for one overrun; one entry per fault per module (owner,
  2026-11-03).
- `_call()`'s `ParamSpec` (B69): typed callbacks per call site, at the cost of a keyword dict per dispatch.
- `UARTLinkDriver.setup()`'s bool: unread by the generated boot.
- `PieceBuffer.copy_into()`'s `start`: no caller passed it.

## Proof check (PLAN 0) on the remove items

None of rows 3-12 had proof: no test read before its removal reproduces a failure the device can meet (zero-length
transfers no caller makes, a transmitter the fake never drains, channels the fake closes, a `deinit()` in a yield no
product code runs, a sender cap and log texts with no failure behind them). Nothing became a shrink item beyond row
12, which the list names as one.

## Gate

`b6_gate.log` (1b4caa17, 14:06-15:49 UTC, beside the storage gate on this 4-core host): lint, mypy x3, the twin
suite and harness at both GC stages (suite 332 checks; harness 16 checks, 65 scenarios), hw collect, npm lint and
typecheck rc=0, no memory marker. Failed:
- `test_code_conventions.py[member_order]` at both stages: `_rx_stop()` out of D.15's name order. Fixed by the lead
  in **b3ed3d57** (the method moves to between `_rx_peek()` and `_write_all()`; no code change).
- At 32768 only: `test_sensortask[arzi/klkizi/wozi]`'s UTC-after-first-sync check (a 2 s skew), dev's mixed polling
  scenario (an IncompleteRead), grkizi's and schlafzi's loop-lag scenario, `test_asy_captive_dns`'s bind back-off and
  `test_driven_time`'s parked bound; npm `test:unit` stopped at `live-backend.test.js` with no case run.

`b6_rerun.log` (b3ed3d57, 16:17-16:37 UTC, alone on a quiet host): lint, mypy-main, the conventions test, the whole
GC 32768 unit stage (every file, scenarios included, no retry, no memory marker) and npm `test:unit` (26 files,
1340 tests) rc=0. Root cause of the timing failures and the npm stop: two gates at once on four cores (both npm
runs began in the same second); gates now run one at a time. The agent's session ended at the container restart
(14:05); the lead re-ran the gate and wrote this section, FW and Findings.

## Sizes

`module_sizes.sh` (`S/u35r/r1/B6/sizes/`): `src/` 198,243 B at 90691b6d to **197,163 B at 1b4caa17 (-1,080 B)**,
15,819 to 15,737 lines; against R0's 208,708 B, -11,545 B. Per module: comm 14,843 to 14,053 (-790), driver 7,727 to
7,546 (-181, with the +64 B fix inside), base classes 10,310 to 10,219 (-91), link 3,666 to 3,648 (-18), codecs
1,486 unchanged. No module grew. Pre-audit (`r0/mpy/before.tsv`): comm 13,102, driver 3,678, link 1,681, codecs
1,223. Lines in the commit: `src/` +64 -146; tests, hardware scripts and the twin +84 -323; docs +36 -41.
FW (lead): not built for B6 alone; the merged head d6bc7617 (B3 + B6) leaves dev 57,868 B free, +3,144 B against
the previous snapshot (`../B36/GATE.md`).

## Decisions taken (agent, 2026-11-03)

- Row 10's form: the ignore, since neither `Callable[..., object]` nor a `TypeVarTuple` passes the typing gates.
- Row 3: `writefrom()`'s now-reachable `crcsize is None` check returns to its pre-audit text without B89's comment.
- Row 6: one typed local per narrowed attribute (at the binding, not at each use), so each function carries one
  suppression per attribute; the pieces branch a single suppressed line.
- Row 12: `copy_into()` delegates to `read_at()` (one line, no loop of its own).
- The changelog: B94 (teardown), B95 (rows 3-8, 10-12 and row 6), B96 (row 9).

## Findings

None written by the agent (its session ended before this section). The lead's review (`REVIEW.md`: 27 hunks
of `src/` and `buildgen/`, 26 read, each mapped to an item) found nothing; the gate's member-order failure is fixed.
Observation, no action: every 32768 failure in the gate is a wall-clock bound that held alone, none recurring.
