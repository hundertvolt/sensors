# B6 falsification brief (lead, 2026-11-03)

Your job: try to REFUTE the claims below about commit `b3ed3d57` (base `90691b6d`, pre-audit `25caf528`). You get the
claims, not the reasoning behind them. A claim stands only if you could not break it; say how hard you tried. Also look
for a lost feature or a reintroduced real defect in these files against the pre-audit code: `asy_uart_driver.py`,
`asy_uart_comm.py`, `asy_uart_link_driver.py`, `asy_framing_codecs.py` (pre-audit `framing_codecs.py`), `PieceBuffer`
in `asy_base_classes.py`, `UART_C_PORT_CHANGELOG.md` and `buildgen/error_catalog.json`. The RP2040 datasheet is not in
`datasheets/` (only the Pico W board's); say where you took a chip fact from.

- Read-only worktree `S/wt-b6f` (detached at `b3ed3d57`); S =
  `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
  You may plant a temporary break there to test a claim, then restore it (`git -C S/wt-b6f checkout -- <path>`).
  Never commit, never push, never touch any other worktree.
- `S/u35r/r1/common_r1.md` gives the environment, the run wrapper (`S/u35/lead/run.sh`, labels `b6f_`), the one-file
  test commands and `S/u23/rebuild.sh <worktree>` (run it once before any test file; it counts as a run). Its binding
  rules apply. No whole gate: single test files only, at most ten runs in all. Every run, `rebuild.sh` included, waits
  for the lead's message that the host is free (another unit's gate holds it now); read and plan meanwhile.
  Never open anything under `/root/.claude/`. Never read
  `arduino/` (`':!arduino'` in every git grep and git log). `tests_hardware` only with `--collect-only` or `--twin`.
- The legacy tree (`python/`, `modules/`, `legacy/`) is reference-only: read it, never run or change it.

## Claims
1. The wire contract is unchanged against `25caf528` and `90691b6d`: emitted bytes, accept and reject rules, recovery
   timings and every `const()` value in `asy_uart_comm.py`; A14 and A15 behave as at `90691b6d`.
2. Stopping an armed receive ring (`_arm_rx()` re-arm, `deinit()`) never aborts a busy channel that is chained to a live
   one: chaining is cut first through the `ctrl` attribute, then both channels abort. Both DMA fakes (`tests/rp2.py`,
   `digital_twin/rp2.py`) raise where the hardware would hang, and a dev twin boot does not raise.
3. No driver or protocol call blocks the asyncio loop, even while waiting: every write waits through `ready(POLLOUT)`
   and `txdone()` with a yield per round, and no read path waits synchronously for bytes that have not arrived.
4. Zero-length reads and writes have no guard of their own; a negative size is still refused; a CRC-framed write of
   nothing is refused rather than sent as a bare CRC, as at `25caf528`.
5. No caller passes a write deadline; a stalled TX ends the transfer through the missing ACK.
6. With no closed-channel guards, no product path reads a DMA channel after it closed; `deinit()` still stops the ring,
   `init()` re-arms it, refuses a fixed ring and reads `deinit()`'s answer.
7. The sender has no cap check of its own; the receiver's cap stays the one refusal, and the twin's over-cap scenario
   passes.
8. A dropped frame logs the pre-audit text; the discard count still enters the resync total, and a wrong-length frame
   under COBS still logs E89.
9. Nothing emits, decodes or expects W57; an overrun fails the frame under its own code alone, and `rx_overruns` still
   counts it.
10. `_call()` builds no keyword dict per dispatch, and no caller passes a keyword.
11. `UARTLinkDriver.setup()` answers `None`; `initialized` follows `UARTComm.setup()`'s answer; nothing reads the link
    driver's return.
12. `PieceBuffer.copy_into(dest)` copies the whole buffer into the front of `dest`, and no caller needs an offset.
13. The crossover exchange test runs in `cobs` mode too (`--collect-only` lists it; the `--twin` exchange in `cobs` mode
    passes); recovery, hazards and load keep the CRC modes.
14. The codec's decode bound and E92 behave as at `90691b6d`: a full-length frame from a codec sized to its frame
    decodes.
15. Every narrowing branch removed from the product code was unreachable, and its typing-side form type-checks in all
    three mypy passes.
16. `UART_C_PORT_CHANGELOG.md` records every behaviour change here (B94, A13 amended, one Class B row naming each
    reversal) and no Class A row is owed.
17. No product check got weaker: every test change is the mechanical consequence of an item above. Look hardest at the
    16 driver tests that stop an armed ring, the bench hazard script's stalled-TX code (E81, not E82), the DMA fakes'
    new raise, and every removed test.
18. Numbers: `src/` bytecode 197,163 B at `1b4caa17` (-1,080 B against `90691b6d`'s 198,243 B), no module grew (the
    teardown fix's about +64 B sits inside the driver's -181 B); `b3ed3d57` only moves one method. The lead sends dev's
    `imageFreeBytes` and the `b3ed3d57` sizes by message once measured; check them then.

## Hand-back
Write `S/u35r/r1/B6/FALSIFY.md`, first line "B6 falsification, written by the agent (<date -u>)": per claim STANDS or
REFUTED, with file:line evidence (and the planted break or run label where you used one). Then any defect you found
outside the claims. Your final message: the path, one line per REFUTED claim, last "nothing of mine is running".
