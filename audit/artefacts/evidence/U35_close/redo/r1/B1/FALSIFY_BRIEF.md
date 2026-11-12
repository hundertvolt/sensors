# B1 falsification brief (lead, 2026-11-02)

Your job: try to REFUTE the claims below about commit `39f1615b` (base `4516e60e`, pre-audit `25caf528`). You get the
claims, not the reasoning behind them. A claim stands only if you could not break it; say how hard you tried.

- Read-only worktree `S/wt-b1f` (detached at `39f1615b`); S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
  You may plant a temporary break there to test a claim, then restore it (`git -C S/wt-b1f checkout -- <path>`).
  Never commit, never push, never touch any other worktree.
- `S/u35r/r1/common_r1.md` gives the environment, the run wrapper (`S/u35/lead/run.sh`, labels `b1f_`), the one-file
  test commands and `S/u23/rebuild.sh <worktree>` (run it once before any test file). Its binding rules apply. No whole
  gate: single test files only, at most ten runs in all. Never open anything under `/root/.claude/`. Never read
  `arduino/` (`':!arduino'` in every git grep and git log).
- The owner's rule behind claim 2: "There must be a mode which is really silent on the console, ever. That's level 0.
  Nevertheless, the outputs of the modules shall be visible with higher levels so it does not become invisible."

## Claims
1. Every broad handler (`except Exception`/`BaseException`/`RuntimeError`) in `src/` and the generated modules still
   records a C-stack overflow (`RuntimeError("maximum recursion depth exceeded")`): it hands its exception object to a
   logger entry (`err`, `err_nomem`, `err_s`, `wrn`, `wrn_s`, `one`, `evt`, `all`, UARTComm's `_err`), each of which
   records it first at every level, or it starts with `report_if_fatal(e)`. The two exempt sites (`report_unretrieved`,
   the shutdown's await of a stopped task in `_shutdown_sequence`) can never carry a record anyone reads.
   `tests_scripts/test_fatal_report_sites.py` catches any handler that breaks this.
2. At DebugLevel 0 nothing in `src/` prints (the generated boot entry's `sys.print_exception` after the loop ends is
   the one admitted exception). From level 1 on, every caught MemoryError that `console()` used to print still prints
   its text, under the owning module's logger name: no site became silent at every level in a product build.
3. Every product builder of `UDPSocket`, `RegionBuffer` and `FramingCOBS`, and every product user of the UART bus
   driver, hands its logger (UART bus: `UARTComm.__init__` sets it before any of the bus's reporting paths can run).
4. `PrintLog.err_nomem()` allocates nothing on a full heap and cannot raise there.
5. E28 LOG_RAM_ONLY is logged only for a store unreadable at setup; nothing else in `src/` logs it.
6. With the pre-setup merge gone, a logger entry made before its `setup()` can only come from a construction fault.
7. `ResetErrors` resets can run concurrently (two PUT /status requests overlap on the same logger).
8. No product caller read `set_level()`'s former bool; `DebugLevel` is range-checked on the REST path, so the restored
   clamp changes no device answer.
9. The catalog rows E16, E65, W24, W43, W46, W47 have no reader in the repo (code, tests, website).
10. The removed records at `4516e60e:src/asy_system_service.py:474` and `:619` were dead (no reader could see them).
11. No product check got weaker: every test change in the diff is the mechanical consequence of an item above (look
    hardest at `tests_scripts/test_fatal_report_sites.py`, `tests_scripts/test_task_tops.py`,
    `tests/test_readiness_gates.py`, and every removed test in `tests/test_asy_print_log.py`).
12. Numbers: `src/` bytecode 207,188 B (−1,520 B against `S/u35r/r0/mpy/now.tsv`); three modules grew
    (`asy_framing_codecs.py` +105, `asy_uart_driver.py` +81, `asy_udp_socket.py` +20) only for the passed logger.

## Hand-back
Write `S/u35r/r1/B1/FALSIFY.md`, first line "B1 falsification, written by the agent (<date -u>)": per claim STANDS or
REFUTED, with file:line evidence (and the planted break or run label where you used one). Then any defect you found
outside the claims. Your final message: the path, one line per REFUTED claim, last "nothing of mine is running".
