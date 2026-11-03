# B6 falsification verified (lead, 2026-11-03, 17:1x UTC)

The falsifier ran nothing (it handed back before the host was free); every check below is the lead's, by reading.
The gate (`b6_gate.log`) and the quiet re-run (`b6_rerun.log`) already ran the whole suite on this tree.

- Claim 1, REFUTED as worded: true, and the wording was the lead's. A conforming exchange is unchanged and the wire
  constants are identical at all three commits; two calls no product path makes now send what they sent before the
  audit: an over-cap SET or GET (B65/B86 reversed, row 7; the receiver refuses, A16) and `write()` of nothing (B48
  reversed, row 3). The errno renumbering against 25caf528 is B1's, not a wire constant. No Class A row owed (A16's
  C-side column is a reconciliation question, not a Python promise). Fix: B95's third column (F1).
- Claim 3, REFUTED in letter: true. `machine.UART.deinit()` waits out the TX FIFO (`machine_uart.c:484`, v1.29.0):
  at most 32 bytes, 2.8 ms at 115200, about 1 s at the hazard script's 300 baud. Pre-audit form; no product path
  deinits or re-inits a UART at runtime. Not this unit's; recorded in CARRY_LATER.
- Claim 4, REFUTED for `write()`: true, and the claim misread 25caf528: `write(bytearray())` under CRC16 sends a bare
  CRC there too (B48's own row says so). Row 3's reversal restores exactly that; no product path writes nothing.
  B95's "again" holds for the CRC case only (pass mode refuses size 0 through A-K2's kept bounds). Fix: F1.
- Claim 16, REFUTED in part: true twice. B95's "No byte on the wire changes" (F1). The A13 amendment, SPEC C.3.2 and
  the driver comment say UARTRSR holds the last byte's bits; pico-sdk `regs/uart.h:86-92` (RP2040 datasheet Table
  427) has OE set when the FIFO is full and cleared only by a UARTECR write, so OE is sticky; FE and BE belong to the
  byte read. Fix: F2.
- Claim 17, REFUTED in part: not a defect. The drain-during-stream change is row 1's own (carried in from 916fb878;
  the bench reading's Day 1 windows were invalid for that reader bug). The fakes' raise is pinned through the 16
  driver tests that went red before `_rx_stop()` (bench count); no test of its own is owed.
- Outside the claims: (a) stale cap text, SPECIFICATION.md:10117-10120 and comm.py:615-616: true. An `exp_size` past
  the train the answer declares now fails as E84 (`UART_SIZE_MISMATCH`), still before any allocation. Fix: F3.
  (b) `deinit()` inside `ready()`'s closing yield: true and pre-audit; no product path deinits at runtime. No action.
  (c) E13: not changed. The bench reading (`READING_20261029.md:45`, datasheet p. 629, 2.5.5.3) has the abort with
  transfers in flight end as a completion, which fires the chain; pico-sdk's dma.h:724-728 names the same premature
  completion; RP2350-E5 is the RP2350 form and does not apply. The mechanism is silicon-confirmed (bench, 2026-10-29).
- Also seen: B95's "unreachable narrowing branches become suppressions" means the audit-added ones (row 6 kept the
  pre-audit guards with B89's comments); the attribution of B95 and B96 is the action list's. Fix: F1.
- Claim 18: sizes from the unit's tables (197,163 B at 1b4caa17, a pure move to b3ed3d57); the lead re-measures at
  the merge.

Fix commit (lead, docs and comments only, no bytecode change):
- F1 changelog B95 (third column, "again", narrowing scope, "(lead, 2026-11-03)") and B96 ("(lead, 2026-11-03)").
- F2 OE wording: changelog A13, SPECIFICATION.md C.3.2, `asy_uart_driver.py`'s `_RSR_ERRORS` comment.
- F3 SPECIFICATION.md J.8's cap sentence and `asy_uart_comm.py`'s `_over_cap()` comment.

Fix commit **a2d41eb4** (lead): `b6_fix2.log`, `tests_scripts` whole (citations, vocabulary, comment cap,
conventions, changelog readers): 7,111 passed, 6 skipped, 0 failed. Comments and docs only, so `src/` bytecode is
b3ed3d57's.
