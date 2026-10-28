V3 hand-back (lane V, block 3). Branch audit/u35-v in S/wt-u35v. Commits on 58b0713: ad1ac1f (OF-200), 7836588 (recombination test), e305fcd (D.15 order). Nothing pushed, nothing uncommitted, no typings link. Nothing of mine is running. About 71 tool calls.

**Profile (arzi, 32768, the timed copy).** The file took 40.6 s. V2's groups took about 8.7 s: forty days 5.04, dropped tick 2.05, storm 1.04, stuck task 0.41, stale clock about 0.2.
- Forty days: 4.57 s of its 5.04 s was the 960-step loop, about 4.8 ms per step. Dropped tick: 1.86 s of its loop was 600 steps, about 3.1 ms per step.
- The cost is scheduler rounds, not CPU work. One bare `_core.sleep_ms(0)` costs 1.13 ms, because while a ThreadSafeFlag waits, the pinned extmod/modselect.c:353-370 passes a 1 ms timeout to the system `poll()`.
- gc is a small share: it ran on 109 of 960 steps at 32768 (about 10 %) and never at -1, with the same total time.

**Fixes (ad1ac1f; every assertion kept).**
- Forty days now runs as 160 six-hour stalls, still through `jump()`. It still crosses the same four wraps and keeps the decay's 100 clean passes.
- Dropped tick now runs for 120 s. Its events moved to seconds 31-35, 62 and 92, each keeping its residue mod 3. So the pause's deadline still falls on a dropped tick and the pause still ends exactly one tick late, at the bound's edge.
- Bites, each in a scratch src copy that I then deleted:
  - `now - self._last`: forty days red (4410029 vs 4496429).
  - delta capped at 1000: both groups red.
  - pause ends one tick early: late = -1000, red.
  - pause ends one tick late: late = 2000, red.
- After: forty days 1.29-1.47 s, dropped tick 0.59-0.74 s at 32768 on all devices.

**Times, test_sensortask (s, 58b0713 → head, alternating, at -1 / 32768):**

| Device | -1 | 32768 |
|---|---|---|
| arzi | 37.34→31.53 | 41.53→35.90 |
| dev | 54.83→49.49 | 64.22→59.10 |
| grkizi | 36.06→31.07 | 40.44→35.50 |
| klkizi | 36.05→30.99 | 40.88→35.81 |
| schlafzi | 36.11→30.98 | 40.80→35.82 |
| wozi | 40.16→34.43 | 46.53→40.16 |

All 96/96. Zero MemoryError and zero "memory allocation failed" in every log.

**Recombination test (7836588).**
- New finding: the old test never reached the ESTABLISHED state. It waited for the twin's link only, so its disconnect landed inside the first connect attempt, and the loss went down the SEEKING path. The trace is in dbg.log: phase 0 throughout. Class: a check that matches nothing; twin, STA, dev.
- The test now waits for `_conn_phase == _PHASE_STA_ESTABLISHED`, then scripts one STAT_CONNECT_FAIL. It asserts:
  - the retry is at least 59 s long;
  - the shared bus log grows during the retry;
  - wifi_mode_lock is never held for half the retry (1 s polls).
- The comment keeps the owner's paraphrase with its actor and date, and names the change.
- Seen failing on planted retries:
  - lock held through the retry → "held through 60 polls";
  - retry never ends → "never recovered", at 77 s;
  - retry skipped → "back 6008 ms ... never ran";
  - bus guard (a fresh log in a scratch test copy) → "no i2c1 transaction".
- Time, twin bus hazard file, 97a034c → head: 85.26 → 146.95 s at -1 and 86.25 → 148.75 s at 32768. The +62 s is the real retry, which is the scenario's subject.
- Risk: the test alone takes 74.1 s, so its 75 s window has only about 3-4 s to spare. I did not change the bound.

**D.15 (e305fcd).**
- The helpers now sit in one sorted block after `_StaggerClock`; ruff's F821 on an unquoted annotation forced that place. The three classes' methods are in D.15 order.
- Verified unchanged: the line multiset, the 378 blank-line pairs, the top-level AST multiset, the fixed statements' order and the 96 registrations' order. No meaning change.
- d15.py stays red on one line: it counts the `@_register` scenarios as sortable, but their definition order is their registration order. This is the same class of import-time miss as LEAD NOTES 36. I am routing it to the lead.

**Checks.** ruff clean. mypy main, main2 and twin passes rc=0 (cold cache, typings link removed after). The 12 checks plus readers are green except Y2's known red, waiting on D: `tests/test_bus_hazard_multi_device.py:64: l1.bus_fault_isolation_bound_s is tagged but has no SPECIFICATION.md Part N row`. No allow-list row is orphaned. No relay lines written.

**Decisions (agent, 2026-10-21):**
- the stall and event layout above, grounded in modselect.c and CLAUDE.md's "find the invariant instead";
- no new tunables;
- the registered scenarios stay in place.

**Facts owed:**
- To the lead: the 1 ms-per-round poll cost applies to every Unix-port test while a ThreadSafeFlag waits.
- To D (Part N): the 75 s `l2.bus_hazard_concurrency_flap_window_s` now bounds a path of about 67 s.

**RUNS.md gap.** These runs have start and done lines: pids 21572, 22091, 22651, 24000, 25245, 26355, 28397, 14204, 14215. These foreground runs have none: two dbg traces (77 s, 17.5 s) and three check runs (about 2.5 min each).

**V4's start:** e305fcd, clean tree.
- Open: the stall residual (LEAD NOTES 40). `5cf361c` is already merged as 58b0713.
- Open: LEAD NOTES 34's uncovered parts, not taken because of the call budget.
- Open: the lane's final 17 scans and readers.

Logs are in S/u35/laneV/v3/: prof*, bite_b*, rbite_r*, rhead_-1, bus_bite, dbg, pb_*/ph_*, bb_*/bh_*, c3_*.