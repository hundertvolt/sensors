U30 lane N FINAL. Branch audit/u30-n (S/wt-u30n). Commits: acc007a (before <API>), 2fc390a (merged <API> c253487), df79dc6.
Applied: OF-63/R-14 and OF-77/R-13 (FRAM check buffer and codec scratch print str(e); a chunk with no check buffer returns block 0 without rewriting block 1 and writes one ALLOC per run). The erase arm is the same class, fixed. OF-97/R-20: the rebound print skips only the timeout the proxy's read arm traced (one identity slot, no task); connections :1050 still holds. OF-98/R-21: the first start failure is persisted too; a heap failure in _body_as_dict re-raises, so the catch-all persists E23 and answers 500. OF-146/R-7: ResetErrors reads routes.is_reset_decided, _shutdown_accepted is gone, the answer stays "Failed".
Steps 37-53, 56, 57 applied. report_if_fatal now leads 42 handlers: webserver 9 arms + catch-all + gathered outcomes, wifi 16, captive DNS 4, FRAM manager 6, notification 3, uart_comm 2. The other parts of those steps had landed already or belong to later units. 39(1) skipped (dropped at U16, REGISTER A-26). 105 applied: 8 pairs collapsed, so 8 fewer tests, not 9 (the F.2b pair stays as two tests). B79 (uart_comm) and B80 (codec) are both no C impact.
Seen failing: codecs :214, :235; FRAM :673/:686, :2866, :3154; webserver C-stack :3380, body :624, decision :1355, escalation :1323; connections silent client :1033, starts :838, :865. Guards passing at once, then bitten: uart_driver :1932; command refusal (accessor ignored); mempause (always refuse).
Red check: test_tunables_register.py:253 is expected (relay ## N line written). test_twin_record is red as expected.
Codec @32768 (base .66 s, now 1.32 s), measured as asked; log in S/u30/laneN/gcmeas/results.txt.
- With GC off, base, base + `_X = 1` and my file allocate the same (2,166,112 / 4,302,816 B per sweep) and run in the same wall time (~0.23 / 0.40 s). That is about 66 and 131 collections per sweep.
- At 32768 the slow variants scale with total -X heapsize while base stays flat. Sweeps: 4M .29-.34 / .60-.63 s, 16M .45-.49 / .78-.80, 64M .97-1.26 / 2.0-2.1. Base: .25-.30 / .43-.52. One collection after the test costs 184 / 548 / 2386 µs, against 17-21 µs in base.
- Mechanism: the slow variants walk the whole heap on each collection, which is gc_deal_with_stack_overflow() (py/gc.c:620-639). It runs once the Unix port's 64-entry mark stack overflows (py/mpconfig.h:255-256). rp2 sets 1024 "to avoid slowdown" (ports/rp2/mpconfigport.h:94). Not churn and not live-heap size: one extra global changes the shape of the graph being marked.
- No test change. Remedy for the lead: build the Unix test port with rp2's stack size.
Timings: webserver 4.37 / 12.89 s (base 11.54 / 13.40); connections 1.21 / 1.36; FRAM manager 5.20 / 6.98 (+2 / +6 %); uart_driver 5.86 / 17.40 (before 5.95 / 18.34). Untouched test files within noise. All 11 files and setter pass at both stages with 0 markers.
Also green: ruff; mypy main, src+tests, host; the 12 checks; changelog; buildgen generate/reproducible; generated_boot; fake surface; suppression; exception contract.
OF-123 (analysis in my interim): reachable at lwIP level (ERR_RTE, ERR_IF, ERR_BUF); duplicate bytes not reachable through src/; no code.
Scan (findings, fixed or by design):
- C-stack swallow, all modes: fixed.
- Body heap failure, STA/AP: fixed.
- Start trace, STA/AP: fixed.
- Duplicate print at a raised level: fixed as R-20 allows.
- The catch-all's own failure stays printed only, since the persist is the allocation that failed.
- A verified FRAM write with no check buffer fails each time with E50 (by design).
For the lead:
- src/asy_fram_driver.py (1) and src/asy_spi_driver.py (2) have broad handlers without report_if_fatal, and no lane holds them.
- _SHUTDOWN_CMDS is now unused; only tests/test_shared_helpers.py:74, 93, 101 read it, so I kept it.
Decision (agent, 2026-10-20): ALLOC once on the verify path too.
Runs: b2 rc 0, conventions, bites, gc measurements; RUNS.md updated. Nothing of mine is running.
