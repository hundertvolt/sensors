V5 hand-back (lane V, last block). Branch audit/u35-v in S/wt-u35v. One commit, 8edb5aa, on c805172. Nothing pushed, nothing uncommitted, no typings link left. Nothing of mine is running. About 82 tool calls.

**Parts by verdict**
- `_flash_stall.py` on a memoryview: **applied.** A slice's count is now `len(data)`, and the wrapper is typed `IO[bytes]`. Seen red first on c805172: twin suite Run 1 on dev, `AttributeError: 'memoryview' object has no attribute 'encode'` at boot.
- `_DirWrites`: **applied.** A write of `<x>.tmp` counts as a write of `<x>` once renamed onto it. A stand-in for asy_config_manager's `os` reports each rename. A direct write still counts at its open. Seen red first: arzi -1 recorded only the `.tmp` names. Bite: dropping the product's rename gives `AssertionError: []`.
- bus_hazard_multi_device :1095: **confirmed green**, 22/22 at both stages. The rename keeps every look whole, so `_littlefs_fake` is not used. Its stale comment ("no suspension point") now names the rename. No meaning change.
- LEAD NOTES 34: **partly applied.** Two new scenarios. One has an exception escaping the supervisor: its entry reaches FRAM, then nothing feeds. The other cancels main(): the cancel ends the loop task, and every armed Timer fired with no yield (the blocked loop's structural half) adds no feed. Both first call every collected timer starter.
  - Finding: V2's stuck-task check "every other live Timer fired" was empty before, because `_boot` arms no timer. It now arms them and fires 5.
  - Bites, each red, on arzi and dev:
    - b1, the cancel leaves the loop running: run_until fails.
    - b2, a Timer callback feeds: "a Timer callback fed the watchdog".
    - b3, the handler feeds: fault 11 vs 12.
    - b4, no entry: ErrCount 0.
  - The stuck-task scenario does not see b2. That is by design: the starve flag stops feed_watchdog().
- **Left for the lead:**
  - Pin IRQs need a pin registry in tests/machine.py:49 (Y's file).
  - Not written (out of calls): forty days' WiFi uptime, NTP age and resyncs, ring saturation, ISL29125/UART stored ticks; the storm's periodic paths, scan budget, recovery, ladder rungs and L2 half. They fit tests/_sensortask_scenarios.py beside `forty_days_of_uptime_keep_every_invariant` and `fault_storm_keeps_every_module_within_its_persisted_log_rate`.

**Times** (test_sensortask, a11603a's scenarios then head, alternated, runner beside each copy; seconds at -1 / 32768)

| Device | -1 | 32768 |
|---|---|---|
| arzi | 30.84→31.40 | 35.59→36.42 |
| dev | 48.40→49.92 | 57.63→59.08 |
| grkizi | 30.98→31.65 | 35.63→36.13 |
| klkizi | 30.93→31.42 | 35.80→36.47 |
| schlafzi | 30.75→31.57 | 35.80→36.46 |
| wozi | 34.33→35.70 | 40.24→41.19 |

- Every file grew under 5%.
- Per part (ms): exception 274-553; cancelled main 161-322; the fresh-filesystem scenario, now passing, 409-835.
- The base fails only the fresh-filesystem scenario (95/96). The head passes 98/98 on all six at both stages.

**Checks**
- ruff and all three mypy passes are clean. D.15 shows only the known `@_register` line.
- Twin CI on 8edb5aa, every row rc=0 and PASS:
  - suite: dev 572/506 s, arzi 480/482 s;
  - crc16 Run 3 on dev at both stages;
  - harness: dev 550/557 s, arzi 433/439 s;
  - generated_boot 22 passed.
- I ran the twin CI the way run_digital_twin_ci.sh does, with three deviations:
  - no setcap: each run is root in its own namespace;
  - the harness runs took the port locks inside each namespace;
  - the harness used rebuild.sh's fresh per-device sites.
- In one pytest process I ran the 12 commit checks, the 17 scans and 23 readers. 1697 passed, 4 red:
  - `test_tunables_register`: `src/asy_config_manager.py:71: config.flush_slice_bytes is tagged but has no SPECIFICATION.md Part N row` (P4's, waits on D), plus Y2's known `test_bus_hazard_multi_device.py:64` line.
  - `test_microtest`, lane P's file: `asyncio.run()` outside the harness at `tests/test_asy_config_manager.py:3325`, and `json.loads` 10 != 2 allowed in the same file. Owed to P5 or the lead.
  - `test_twin_record`: expected.
- Memory: zero MemoryError and zero "memory allocation failed" in any output. The only matches were the suite's own "carries none of" lines and a source comment in the crc16 run's generated copies.

**Decisions (agent, 2026-10-21)**
- A sibling's write counts at its rename.
- The stall wrapper takes bytes only, since the store writes "wb".
- The scenarios call the timer starters directly.
- The twin CI deviations above.

**Scan:** no new finding. Class-5 note: the twin stalls once, at the sibling's close, and not for the rename's commit. It puts the whole worst-case budget into that one window, so it is conservative.

**Effect per mode:** tests and twin only. STA, AP, Silent, Off and USB are unchanged on every device.

**Runs, all with RUNS.md lines:**
- seen 7585 rc=0;
- chainA 10090: stopped by me (rc=143) to fix the empty Timer check;
- quick 11169, chainA2 11553, chainB 24377 and chainC 30227: all rc=0;
- checks c1 rc=1 (the reds above);
- twin mypy rc=0.

Logs are in S/u35/laneV/v5/: seen sf_*; bites bite_b0 and bite2_*; pairs pb_*/ph_*; twin CI twinci/; checks c1_*/c2_*. The bite copies are deleted.