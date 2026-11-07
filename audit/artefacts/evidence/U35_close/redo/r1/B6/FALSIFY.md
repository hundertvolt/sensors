B6 falsification, written by the agent (Tue Nov  3 17:02:59 UTC 2026)

## How this was done, and what was not
- Static only. The lead's "host is free" message never came before hand-back was enforced, so no run was made:
  no rebuild.sh, no test file, no probe, no plant, no mypy, no module_sizes.sh. No b6f_ label exists.
- A probe was written but never run: S/b6f_tmp/probe_b6f.py (agent code, outside S/u35r). It checks claims 4, 1/7
  and 5. Every item below marked "(unrun)" is what a run should confirm.
- Worktree S/wt-b6f untouched (git status clean). Chip facts: the RP2040 datasheet is not in datasheets/. I took them
  from pico-sdk at S/tc-int/pico-sdk (hardware_dma dma.h, hardware_uart uart.h, rp2040 regs/uart.h) and from
  MicroPython v1.29.0 ports/rp2 (rp2_dma.c, machine_uart.c) at S/tc-int/micropython.

## Claims
1. REFUTED as worded.
   - Against 90691b6d, conforming exchanges are unchanged: the only const change in asy_uart_comm.py is W57 going.
     A14 is at comm.py:957 and is unchanged; A15's listen loop is unchanged.
   - But emitted bytes changed on reachable API paths. An over-cap uart_set*/uart_get(exp_size) used to send nothing
     (the removed test asserted that the initiator's wire was empty). It now sends its command frame
     (comm.py:1126-1170 has no cap check). A SET is refused at the peer (comm.py:294-296: the peer logs E93, the
     sender E81). A GET with exp_size over the cap runs a whole GET, then fails with E84 (comm.py:268-271),
     and the peer logs E81.
   - write(empty) changed too: it now sends a bare CRC under CRC16 and "01 00" under COBS. At 90691b6d it sent nothing.
   - Against 25caf528 the claim does not hold. A13, A16 and A17 (accept/reject rules) were added after it, and so
     were A14 and A15. Most errno const() values were renumbered (ALLOC 14 to 20, and so on). The wire bytes'
     constants (header offsets, CMD values, UID_MAX, backoff/resync multipliers) are identical.
2. STANDS (unrun).
   - _rx_stop at driver.py:357-364 rewrites CHAIN_TO to the channel's own number through `ctrl`, then aborts the
     reload and then data. `ctrl` writes AL1_CTRL with no trigger (rp2_dma.c:427-430, dma.h:475-482).
   - The reload is never chained: its pack_ctrl default is its own channel (rp2_dma.c:530).
   - Both callers use _rx_stop: driver.py:184 and :415.
   - The fakes raise when a channel is busy and chained to a channel that is claimed: tests/rp2.py:156-161 and
     digital_twin/rp2.py:160-164. That covers more cases than real hangs, never fewer.
   - Not seen run: the planted red, the "16 tests", and the dev twin boot. A dev boot only stops idle, freshly
     claimed channels, so the boot alone never reaches the raise. The twin raise is reached by the crossover
     scripts' deinit() (uart_crossover_exchange.py:171-172).
   - Doc: SPECIFICATION.md:7270 and B94 call the cause RP2040-E13. pico-sdk dma.h:724-728 describes E13 as a
     premature ABORT clear with a spurious IRQ; dma.h:752-755 gives abort re-triggering to RP2350-E5.
3. REFUTED in letter; holds for the read and write paths.
   - _write_all (driver.py:366-384) goes through ready(), which yields (:720), or sleep_ms per round. Every read
     goes through _buffered() and the ring.
   - Counterexample: deinit() (driver.py:425) calls machine.UART.deinit(). That calls uart_tx_wait_blocking
     (machine_uart.c:484; pico-sdk uart.h:450-452), a busy-wait until the TX FIFO drains: up to 32 chars, about
     1.07 s at the hazard script's 300 baud.
   - This was there at 25caf528 and 90691b6d. No product path re-inits after construction.
4. REFUTED for write().
   - Guards gone and negative sizes refused: driver.py:520, 583, 786. writefrom(buf, 0) is refused through
     add_into (asy_crc_checks.py:96).
   - write(bytearray()) under CRC16 goes add() (crc_checks.py:81-91), which returns empty + CRC. So it sends a
     bare CRC (FFFF), as at 25caf528 (crc_checks.py:56-67 there). The claim says it is refused.
   - B48's own text (changelog:172) records exactly this as the old fault. No test pins write(empty) under CRC now.
     No product path writes zero bytes (the comm and link driver use writefrom with a full frame).
   - Also: writefrom(buf, 0) without CRC now answers False. At 25caf528 it answered True (pass-mode add_into
     returned 0), so B95's "again" is only true for the CRC case.
5. STANDS, with a limit (unrun).
   - No caller passes a write deadline: the only timeout_ms writes in the repo are the UDP socket's.
   - The bench "stalled TX" is a 300-baud line and does drain, so it ends at the ACK with E81. The host test does
     not check the code (test_uart_crossover.py:184).
   - A TX that never drains (txdone() never True, the removed tests' model) now holds the transfer and the bus lock
     forever. Not reachable on rp2 without flow control: txdone is machine_uart.c:510-513.
6. STANDS. Channels close only in setup_rx_ring's failure arm, which drops both references (driver.py:755-758).
   - deinit() stops the ring (:413-417). init() raises on a changed ring (:452-453), reads deinit()'s answer
     (:454) and re-arms (:490-494). Nothing in src re-inits at runtime.
7. STANDS (twin not run).
   - The sender has no cap check: _check_cap is gone, and comm.py:614-617 is the only _over_cap.
   - The receiver refuses at comm.py:265 and :294. The twin scenario caps the responder
     (uart_crossover_exchange.py:111-130).
   - Stale comment: comm.py:615-616 still says "a sender refuses exactly the trains its peer would".
8. STANDS.
   - The texts at comm.py:554, 681, 722 and 981 match 25caf528's (:997, 956, 755, 644).
   - The discard count: _read_frame (comm.py:703-704) and _take_discarded (:866-872) feed the resync at :780. E89
     comes from the streak at :794-798. Pinned by tests/test_asy_uart_comm.py:675-697 and 646-663.
9. STANDS. Nothing in src, tests, digital_twin, js, buildgen or tests_hardware names UART_RX_OVERRUN or W57; only
   changelog rows B75 and B96 do. The overrun test asserts E81 alone and rx_overruns == 1.
10. STANDS. _call takes *args only (comm.py:409). All five call sites (comm.py:300, 361, 544, 670, 736) are
    positional.
11. STANDS. Link driver: setup() at link.py:287-289. The boot runner discards every setup() result
    (asy_system_service.py:693-694). The remaining `is True` checks are UARTComm.setup's.
12. STANDS. The copy is at base_classes.py:185-187. No caller in the repo passes a second argument, and an empty
    buffer still copies (test :527).
13. STANDS by reading; the run is owed. Exchange: test_uart_crossover.py:97. Every other test there: _CRC_MODES
    only (:112-274). The script frames by FramingCOBS(5+48) with no CRC, which passes E92 (comm.py:926).
14. STANDS. asy_framing_codecs.py is identical at 90691b6d and b3ed3d57. The driver's bound (driver.py:233, 238)
    is unchanged.
15. STANDS by reading; mypy not run.
    - Each removed branch was unreachable:
      - The driver's _arm_rx, _rx_copy, _rx_line_len and _rx_peek: the ring and its channels are set and cleared
        together (driver.py:743-758), and nothing nulls them later.
      - comm._min_rx_ring: only _validate_receive calls it, after the bus check at :901.
      - _send_train's region: construction is refused without it.
      - _take_discarded: it runs inside a resync, which needs a bus.
      - link._run_hazards: only the exercise loop runs it, while initialized.
    - Note: the old _send_train branch also failed on read_at() False. That False is now ignored and stale TX bytes
      go out, but only if a get_callback's PieceBuffer shrinks mid-answer, and no product caller does that.
    - Note: six branches marked "Unreachable ... kept to narrow" stay in comm (:557, 685, 726, 974, 1075, and the
      :751 guard), against B95's "unreachable narrowing branches become suppressions".
16. REFUTED in part.
    - The rows exist: B94, A13 (:115), B95 and B96, and B95 names every reversal.
    - B95's third column, "No byte on the wire ... changes", is false for two of them:
      - The over-cap call now transmits and logs at both ends. A16's own C-side column says a sender never
        declares more than the receiver's cap.
      - write(empty) now sends a CRC-only frame.
    - The A13 amendment, also in SPEC C.3.2 and driver.py:76-77, says UARTRSR holds the last byte's bits. pico-sdk
      regs/uart.h:86-92 says OE is set when the FIFO is full and cleared only by a write to UARTECR, so OE is
      sticky and also fails a frame mid-stream.
    - I see no Class A row owed: no receiver rule or const changed.
17. REFUTED in part.
    - Every removed test pins a reverted item: B48, B54, B55, B61, B65/B86, B78/B85, B75 and the copy_into start.
    - The kept behaviours stay pinned elsewhere: a train at the cap (test_asy_uart_comm.py ~2660) and the
      CRC-dropped frames (test_uart_comm_hazard.py).
    - Not mechanical: uart_dma_ring_interrupts_off.py:394-403 now drains during the stream, so the ring holds the
      window alone instead of the whole stream. That brings the test into line with the product property rather
      than weakening a product check, but it is a bench-script fix, not a consequence of items 1-16.
    - Stalled TX: the host test never checked E82 or E81 (:184).
    - The new raise in the fakes is not pinned by a test of its own (no driver test names chain, abort or
      RuntimeError). It is only reached indirectly through deinit()/init().
18. Not checked by a run.
    - The B6 unit's own tables agree with the claim: sizes/base.tsv 198,243 and head.tsv 197,163, a -1,080 B
      difference. Driver -181, comm -790, base_classes -91, link -18; no module grew.
    - The 1b4caa17 to b3ed3d57 diff is a pure move.
    - The lead's imageFreeBytes and the b3ed3d57 sizes never arrived.

## Defects outside the claims
- (b) Stale docs from the cap reversal:
  - SPECIFICATION.md:10117-10120 still says an exp_size over the cap is logged once as UART_TRANSFER_CAP. It is now
    E84 after a GET exchange, plus E81 at the peer (the very case B86 fixed).
  - comm.py:615-616, as in claim 7.
- (b) A latent defect returns with B54, not reachable from the product.
  - A deinit() during ready()'s closing yield now hands _write_all a dead machine.UART (driver.py:720-721, 374-380).
    Its TX buffer has been unrooted (machine_uart.c:493), so a write after that is a use-after-free on silicon.
  - 25caf528 had the same form, and nothing in src deinits at runtime.
- (c) The E13 attribution and the OE wording, as in claims 2 and 16.
