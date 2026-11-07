# Neopixel test timing failures: VM wake-up latency (SF-U5-05)

Evidence behind SF-U5-05 (`audit/sweeps/scan_runs/20261006_U5_close.md`). `tests/test_asy_neopixel_driver.py` failed
1-3 of 75 runs under heavy host load, a different test each time, at U4 and U5 alike. The tests wait fixed real times
with 30-50 ms of slack. The cause was measured outside the simulation.

- `runs/npx_gap2/g_1.log`..`g_3.log`: three independent `gapprobe2.py` processes run at once under the same load. Each
  line lists every >30 ms overshoot of a 10 ms sleep as (CLOCK_MONOTONIC start ms, overshoot ms, own CPU ms, voluntary
  switches, system-wide steal ms). The three processes stall at the same millisecond (e.g. 46114498/46114476),
  for 36-99 ms, with 0 ms of their own CPU: the VM delayed every sleeping process's wake-up at once. Steal covers
  only part of it. `stat0`/`stat1` are `/proc/stat` before and after; `npm.log` is the load generator's output.
- `runs/npx_gap1/`: the first probe (`gapprobe.py`): overshoots up to 141 ms with 0 CPU ms and 0 forced switches.
- `runs/h_*.log`, `runs/p_*.log`: repeated runs of the test file during the investigation; `runs/lat2_*.log`:
  `lat2.py` runs (each lists its >25 ms overshoots over 180 s).
- `probes/npx_trace*.py`, `npx_dbg.py`: the test with every pixel write timestamped; the failing runs
  show the driver's write sequence intact, only late. `repro.py` shows a synchronous stall longer than the
  test's settle wait reproduces the failure; `dur.py`, `gctime.py`, `cpuchk.py`, `lat.py` rule out ramp length, GC
  and own-CPU time.

Run any probe from a checkout at U5 (`c3df14e`) with the Unix-port interpreter and `MICROPYPATH=src:tests`, e.g.
`micropython -X heapsize=16M audit/artefacts/evidence/U5_neopixel_wakeup_latency/probes/gapprobe2.py`; start three at
once, beside a load such as `npm test`, to see the shared stall. Conclusion: no simulation or product defect; the
fix is driven time for this test file (M.TEST_UNIT.078/.079, U35).
