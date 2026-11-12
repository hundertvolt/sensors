V4 hand-back (lane V, block 4). Branch audit/u35-v in S/wt-u35v. Commits on e305fcd: 094bc07 (the stall residual) and a11603a (the driven retry). Nothing is pushed or uncommitted. No typings link is left. Nothing of mine is running. I made about 58 tool calls.

**Steps**
- LEAD NOTES 40, the stall residual: **applied, 094bc07.**
  - `digital_twin/_flash_stall.py` now has a plain µs clock that never wraps. `plain_us(us, ms)` adds each gap from the last reading: by ticks_us up to 2**28 µs, by ticks_ms beyond that. Windows hold (start on that clock, length) and are matched with a plain `start <= at < start + length`.
  - `machine.UARTLink` reads its wire time off the same clock. `_stall_offset_us` is now the link's origin on it, so offset + due is unbounded. EPOCH_US and machine's own copy of the gap rule are gone.
  - `restart()` is test-only.
  - Rebuild ran (rc=0).
- LEAD NOTES 47, the retry: **applied, a11603a. The clocks split.** A test-local stand-in for `asy_wifi_service.asyncio` hands only `sleep(60)` to a DrivenTime. Every other WiFi sleep stays real; the module has no other 60 s sleep. The retry stays parked while the shared bus runs 3 whole real SCD30 cycles. Then the clock advances by exactly the parked length, and the link must return.
  - Assertions: the retry is exactly 60000 ms on the driven clock; the bus log grows; the lock is not held for half the polls; a retry that parks again fails at once.
  - The test alone: 74.1 → 20.1 s.

**Seen failing first and bites**
- Period aliasing, a byte one full period after a stall:
  - test_digital_twin_machine: `(kept, dropped, OE) (32, 8, 8)`.
  - test_ticks_rollover: `(536770, (True, True, False, True))`.
- A window recorded after 2**29 µs (the 600 s test) passed at once. Two bites, both "the burst missed the stall's window": the query wrapped by ticks_diff, and the start stored by ticks_diff.
- Retry bites, each red with its own message:
  - sleep moved inside the lock: "held through 6 polls in a row of the 6";
  - the retry never ends: "parked again after its 60 s";
  - the retry skipped: "a 0 ms retry ... never ran";
  - a fresh bus log: "no i2c1 transaction".
- Nothing planted is committed; the copies are deleted.

**Times (s, -1 / 32768)**
- Twin bus hazard file, paired e305fcd → head: 147.04 → 92.99 and 149.10 → 94.63.
- Stall files on the head: machine 1.16/1.18, machine_uart 3.63/3.78, rollover 3.77/3.81, uart_link 54.92/58.86. None is slower than V1's head.

**Checks**
- ruff, D.15 and all three mypy passes are clean. I also fixed test_digital_twin_machine.py's D.15 miss, which was already red on the base.
- The 12 checks plus 15 readers: the only reds are Y2's known line (`tests/test_bus_hazard_multi_device.py:64 ... no Part N row`, waits on D) and twin_record (expected).

**Runs:** every twin importer of digital_twin/machine.py at both stages. Per-device files (construction, sensortask_integration, timer_pool) ran on all 6 devices. All rc=0 except one. Zero MemoryError and zero "memory allocation failed" in every log. RUNS.md has lines for checks, bites and lanes A, B and C.

**Red, owed to the lead (not V's file):** `tests/test_digital_twin_clock_jump.py:251: AssertionError: (0, [35, 33])` at both stages, on e305fcd and on the head. It is green on f3fff0e (6/6). The only src difference is lane C's 8c2b458 (the SGP40 backup check `ntp_issynced` → `ntp_clock_valid`), merged here as 97a034c.

**Decisions (agent, 2026-10-21)**
- One shared plain clock read by the link, not a second copy of the gap rule.
- The stand-in picks the retry by its value.
- The hold is 3 SCD30 cycles, a plain count with no new tunable.
- The lock check keeps the half rule, measured over the hold's polls.
- The 75 s bound is kept.

**Effect per mode:** twin and tests only. STA, AP, Silent, Off and USB are unchanged on every device.

**Facts owed**
- To D: `l2.bus_hazard_concurrency_flap_window_s` 75.0 now bounds a path of about 20 s. No relay line was written, since the brief asks for one only if the clocks could not split.
- To the lead: the clock_jump red above.

**V5 start state:** a11603a, clean tree. Open: the posix-file look after P4, LEAD NOTES 34's parts, and the lane's final 17 scans and readers.

Logs are in S/u35/laneV/v4/:
- seen failing: sf_*; bites: bite*;
- pairs: pb_*/ph_*; the retry test alone: r1.log;
- lane summaries: laneA/B/C*.out; checks: c3_*;
- clock jump: base_clock_jump_-1.log (red on e305fcd) and u35base_clock_jump_-1.log (green on f3fff0e).