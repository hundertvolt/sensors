G1b hand-back (dev, GC 32768, uart_ring_under_concurrent_load). Verdict: firmware finding, handed back. No commit; worktree S/wt-u35g1b is clean at 069b9fe.

Mechanism (069b9fe). The hammer runs one thread past the ceiling, so one thread is always being refused. Its request goes through `_status_of` (scripts/_digital_twin_scenarios.py:1927) into `_request`, which has a 10 s socket timeout (:80). A refused connection is counted at src/asy_webserver_service.py:920, then waits in `_note_drop` (:925, :799-802) for the WEBSERVER logger's lock (asy_print_log.py:335) and its FRAM chunk write (:349). Only after that does the finally close it (:965). That wait sits outside both device bounds: the 5 s per-call timeout and the 15 s outer cap (SPEC 6588, con.http_call) apply only to admitted connections. For the refused client the whole wait is one blocking read. Under FRAM-log writes and 2.1 s flash holds it grows past 10 s, and the client gets TimeoutError.
- Evidence the gate's timeout was a refusal: I booted copies of the failed boot's state. Its WEBSERVER log holds 17 events, all W 60 (refusal) and no W 48, the trace an abandoned admitted response would leave. Passing rounds hold 49-75 refusals, so each refusal in the failed round took about 3x longer.
- Alone, instrumented: an admitted request's longest single wait is 2.4 s or less. A refusal's close took 1.4-5.9 s (median trace write about 470 ms, max 2.8 s across a flash hold). Host CPU was 60-70 % idle at failure time (vmstat).

Reproduction (scratch copy only, nothing planted is committed): I made the refusal's trace take 4x its own measured time inside `_note_drop`. The run failed the same way: `a load thread raised or never ran: ["TimeoutError('timed out')" x3, 3, 3, 4, 6, 6]`. Those connections were accepted at +0.06 s and closed at +13.5 s, or not at all before the twin stopped.

Two firmware patches tried in scratch:
- **Close before trace: rejected, it creates a new hazard.** Refused clients retry at once and _serve tasks pile up on the logger lock (371 writes, 13.7 s lock wait). Then "memory allocation failed" x3, tasks end and the supervisor reboots (exit 3). The current trace-before-close order is what slows refused clients down, so it must stay.
- **p1, proposed:** count the drop, then wait for the trace at most one per-call timeout via `wait_for_ms(pr.wrn_s(...), self._per_call_timeout_ms)`, then the finally closes. Diff: S/u35/laneG/g1b/proposed_p1.diff.
  - The planted run passed: 13 traces cut short, zero memory markers.
  - Unplanted, beside 4 CPU burners I started and killed by pid: 3/3 passed at GC -1 and 3/3 at 32768. Every close came within 7.2 s, zero memory markers.
  - Under that load the trace ran past 5 s in 5 of 6 runs (4-8 times per max round), so without p1 the long tail is real.
- With p1 the scenario's 10 s timeout fits: 5 s plus one 2.129 s flash hold stays under it. The scenario and its checks are unchanged.

For the lead:
1. p1 cancels a FRAM chunk write mid-flight. The FRAM/SPI write path needs a cancellation-safety review (chip select, chunk CRC).
2. The cut arm is a silent `pass` on purpose: the entry stays in RAM and lands with the logger's next write, but is lost if a reboot comes first. That touches "Every drop leaves evidence" (owner, 2026-09-29), so it is an owner question.
3. A unit test for p1 is owed: a refusal whose trace blocks past the per-call timeout closes at that timeout. It must be seen failing on today's code first.
4. Stale doc lines:
   - SPEC 12216: `l2.scenario_request_timeout_s` says "every served request measured under 1 s". Under this load admitted requests take 6-8 s and refusals up to 5.9 s.
   - SPEC 9785 says "no failed transfer", but `_uart_load_round` allows failures in the max round (`stall_max or counts.failures == 0`).
   - SPEC 6588 (con.http_call) does not mention the refusal path.
   - The A.8 comment at src/asy_webserver_service.py:921-922 ("cheapest ... resource consumer") does not match what the code does today.
5. Scope: affects the webserver in STA and AP; Silent, Off and USB unchanged. Every device's webserver is affected; only dev runs this scenario. No flash or SCD30-NVM write is added or changed (FRAM only), and the UART wire format is untouched.

Runs: 10 starts, each with start and exit lines in S/u21/RUNS.md. All exited 0 except run_p1 and run_p1f, which were meant to fail.
- run_a1-a3 and run_p1b: alone, unplanted, PASS (run_p1b by accident: a re-apply script stopped early).
- run_dump: the evidence-state dump, PASS.
- run_p1: the planted reproduction, FAIL as expected.
- run_p1f: close-before-trace, FAIL (the heap hazard above).
- run_p1c: planted plus p1, PASS.
- loadproof: 6/6 PASS.

Logs are in S/u35/laneG/g1b/ (run_p1, run_p1c, run_p1f, run_a2, run_a3, lp_*, loadproof.out, tools/). The scratch tree copies are deleted. About 72 tool calls.
nothing of mine is running