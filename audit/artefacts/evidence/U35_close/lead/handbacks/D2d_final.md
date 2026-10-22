D2d hand-back (lane D, U35). One commit, `d1a60f7`, on `audit/u35-d2` (on top of `6dabd9b`), in S/wt-u35d2. It touches only SPECIFICATION.md, BACKLOG.md and tests_hardware/README.md. Nothing is uncommitted and nothing is pushed. I did not edit any config-file write-path sentence (A.4, C.7.3, F.3 stall.flash_program, J.6, Part N's two rows); those stay for D2e.

**Steps:**
- **34, landed by me:** G.2's watchdog entry now names the planted-fault proof for each failure class: the three per-device scenarios at tests/_sensortask_scenarios.py:1993/2038/2079 and the twin's `watchdog_fault` (E.6.6 `watchdog-fault-planted`), tagged (owner, 2026-09-25, paraphrase). The frame-codec entry gains the one-codec-per-driver sentence (agent, 2026-09-11; first written in 8850974). BACKLOG.md:1138's finding stays for U37's removal (step 126).
- **37 (5), landed:** C.8's cancellation paragraph names `cancel_at_each_await()` and says each path's sweep lives in its module's test file (10 files; agent, 2026-10-21).
- **111, landed:**
  - E.5.1 heading: "three systematic … patterns" becomes "the tracer's false negatives".
  - The tracer classes are added (continuation lines, `else:`/`finally:` headers, a `pass` that is an `if` body). I confirmed each on build-settrace with a scratch probe (S/u35/laneD/d2d/trace/probe.log). A `pass` in a loop body does fire.
  - The convention paragraph is added (owner, 2026-09-26, paraphrase; agent, 2026-09-30).
  - Named change: the UART re-checks are now "kept as type narrowing", as the code comments say. `_push_wifi_led()`'s guard joins them.
  - The dated "31 lines" count is removed. The finally paragraph is restated as the tests stand.
  - Where the tree overrides the table: the UART driver's `msg += add` catch is gone, and the new allocation catches are tested (test_asy_uart_driver.py:1808), so no "untestable" entry is needed. The js guards are gone. One wifi test is a raise, not a cancel.
  - The E.5.1-vs-coverage-report check is D3's.
- **112, landed:** F.1 gains the 2**30 scratch-build wrap sentence (<T30> e1ad71f; agent, 2026-10-22) and the silicon 15-minute tick-offset sentence (B.14.5, E.6.3).
- **126, landed:** BACKLOG's network-fault-injection bullet is removed; its open recombination is `ntp_unreachable_load` (E.6.6 row). Its one remaining fact, the CYW43 fault injected by `--fault wlan`, moves to README's netem bullet.
- **128, landed in a new `## E.2.3`:** strict JSON, months by `forty_days_of_uptime_keep_every_invariant` (agent, 2026-09-27), load with Run 3's `rate.persisted_log` bound, the system-command guards, and the const-mirror rule. E.6.6 gains the DHCP sentence (owner, 2026-09-26). K.10 gains the fault-planting pass (owner, 2026-09-25, paraphrase).
- **143 (4), landed in E.2.3:** the bite list (owner, 2026-09-25, paraphrase) and driven time (owner, 2026-09-26, paraphrase). Tree overrides the packet: `FastAsyncSleep` has 22 users, not "its one use", so the sentence states what the helper does instead.
- **144, landed:** D2b had added the planted-proof sentence but left "accepted trade-off" in J.7; I removed it (named change).
- **142, left:** the BACKLOG rows for A.U35.54's instruments.
  - Absent from the owed list: the silicon arm of the hardware memory gates, the lone-BMP3xx flash test, the torn-write bench run (test_end_to_end_timing.py:162), the two-image GC proof, the read-stagger timestamps, the speed-probe bands, and the interaction/rung cells.
  - Each needs its instrument checked in tests_hardware/ before a row is written. Its site is audit/b3/queue_c.md, which goes to U37. I stopped there for the tool budget.

**Checks:**
- 17 doc and section-reader checks before the commit: 895 passed, 1 failed.
- The 17 scans on `d1a60f7`, run once in one process: 877 passed, 1 failed, rc 1, 73 s, zero memory markers.
- The red in both runs, for the lead: `test_decision_vocabulary.py::test_the_allowlist_only_shrinks`. `tests_scripts/_decision_vocab_allowlist.txt:67` ("SPECIFICATION.md\tThe accepted trade-off is that neither test …") is orphaned by the J.7 change and needs deleting; I left it because allow-list edits are yours.
- Warning: "datasheets/ submodule not initialised" (environment).

**Modes:** documentation only, so no effect in STA, AP, Silent, Off or USB on any device. No wear question arises.

**Routed, not mine:** digital_twin/README.md's twin-record text (T4) and HEAP_FRAGMENTATION_MEASUREMENTS.md:282 (U36).

Logs and the edit script are in S/u35/laneD/d2d/ (steps.txt, edit.py, msg.txt, checks1.log, scans17.log, trace/). Runs: one settrace probe (rc 0), two pytest runs (rc 1, the red above). All have exited.
nothing of mine is running