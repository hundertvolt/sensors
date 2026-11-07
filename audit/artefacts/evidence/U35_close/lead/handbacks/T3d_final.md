T3d hand-back (lane T, audit/u35-t, S/wt-u35t). One commit, 5ca6b30, on dc8c180. Nothing is uncommitted and none of my runs are still going. I used about 61 tool calls. No src/ change, so no rebuild.

**Steps by verdict**
- **Fold (11): applied.** `test_a_stopped_scd30_ends_its_alerts_and_sgp40_compensation` runs on arzi. The SCD30 reads CO2 above WarnCO2 for real, and a control SGP40 cycle measures. Then ContMeas goes off through `_set_dict_cfg` (the PUT /sensors path), and the wall clock steps past both age bounds. Result: State 3, no red frame, and no 0x260F measure reaches the twin chip.
- **Fold (13): applied.** `test_a_restarted_sgp40_task_keeps_its_live_voc_state` runs on arzi. It does fed cycles and one FRAM backup, cancels the task, and the real supervisor restarts it. Result: samples 3 → 4, `_restored_from` stays None.
- **Fold (18): applied.** Test 10 sends 6 queries with no yield between them. All 6 are answered, with at most 7 listener wake-ups. It prints `MEASURE dnssrv.burst_answered=6/6`. `_CountingPoller` now counts only ready(POLLIN) rounds.
- **Waits in tests 6-9: all moved.** Every assertion is kept, and none stays real. One `_step_sensor_waits()` turns the SCD30's, SGP40's, pixel's and monitor's sleeps into a single yield. The monitor's cycle period stays real.
- `_SteppedWifiAsyncio` is renamed `_SteppedAsyncio` and gains `real_from_ms` (a consistency fix).

**Wait table** (arzi; every move bitten)
| Wait | Before | Now | Bite |
|---|---|---|---|
| SGP40 init, tests 6-8: 0.5 s self-test + 1 s reset, 2 per test | real | stepped | pWinit: "never finished its init" |
| Backup and restore polls, 6-8 (0.25 s step) | real | 10 ms step | pWbackup "backup write never completed"; pWrestore "restore never completed" |
| Test 9 CO2: SCD30 2.5 s reset settle + 2 s interval | real | stepped; the chip's timer fired each poll | pWco2: "never read the CO2" |
| Test 9: monitor's 1 s hold, 0.5 s pixel ramp | real | stepped | pWflash "no red frame"; pWsignal (assert at the signal-end wait); pWwindow "outside the window reported Triggered" |
- Per test: 6-8 went from 4.2-4.4 s to 0.73 s each. Test 9 went from 4.67 s to 0.47 s.
- Fold bites: p11n `reported as NOTIFY(Triggered=True, State=0…)`; p11s `the SGP40 measured with a stale SCD30 sample`; p13 `restored from FRAM: (1, 0), not (4, None)`; p18 (a second ready per read) `the burst took 13 listener wake-ups`.
- Each plant ran from its own scratch dir. The controls ran from tests/.

**Times** (s, head / base = dc8c180's file run from a clean dir, alternating; all rc=0, mem=0)
| Device | -1 | 32768 |
|---|---|---|
| arzi | 59.99 / 73.66 | 60.64 / 74.22 |
| dev | 22.60 / 22.37 | 23.03 / 22.92 |
| grkizi | 20.40 / 20.32 | 20.61 / 20.57 |
| klkizi | 20.57 / 20.26 | 20.55 / 20.49 |
| schlafzi | 20.33 / 20.26 | 20.50 / 20.48 |
| wozi | 20.79 / 20.93 | 21.12 / 21.00 |
- Added time per fold: (11) +0.73 s, (13) +0.60 s, (18) +0.1 s. No file is more than 10 % slower.

**Red, root-caused (my run discipline, not a defect):** r1's base arzi -1 failed tests 7 and 8 with `OSError: [Errno 2] ENOENT` at `digital_twin/_fram_chip.py:281`. The cause: my arzi bite processes ran at the same time. Each one wipes `tests/_tmp/dtsi_arzi` when it starts (`tests/_tmp_scratch.py:52`). Rerun alone (r2), it passed at 73.66 s. Never run two processes of the same device's file at once.

**Decisions (agent, 2026-10-22; the UTC date passed midnight during this block)**
- (13) runs the real supervisor over the SGP40 starter alone.
- The datasheet waits are stepped in the twin only. L1 still pins their values (tests/test_asy_scd30_driver.py:765, :786; tests/test_asy_sgp40_driver.py:78).
- A sleep of at least the flash hold + 1 ms stays real.
- (18) assumes the listener is parked in ready(POLLIN) when the counter is installed.
- 0x260F is taken from the driver's datasheet citation (Table 9) and the twin chip. I did not re-extract it from the PDF.

**Scan finding (new, my file):** class 3, mode "a check that matches nothing". (18)'s wake-up bound does not catch a listener that sleeps one idle poll before each read: every round then finds data. Proposed fix: count the socket's idle sleeps during the burst (at most 1). Left for T3e or T4.

**Checks:**
- ruff is clean. The twin mypy pass reports 0 issues in 52 files.
- 947 passed: the 12 checks, test_device_tomls (the one reader), gc_collect_sites, fake_surface_conformance, twin_fake_catalog and port_bands.
- No @tunable added. No allow-list row orphaned. Relay: none.
- Effect per mode: test-only. AP: (18). STA, Silent, Off and USB: none.

**Runs** (all in RUNS.md):
- timing base_arzi and h1_arzi: rc 0 and 1. The h1 red was the idle counter starting at False; fixed before r1.
- plants.sh: 11 bites, each rc=1 as expected.
- r1: 24 runs, rc=1 from the collision above only.
- r2: rc=0.
- checks1: rc=0.

**T3e starts** from 5ca6b30, clean, no rebuild needed. Open items:
- 149's booted boot order (R-24);
- 125 (f)-(i) and folds (1)-(3);
- the (18) detection gap above.

**Logs:** S/u35/laneT/t3d/ (r1.sum, r2.sum, plants.sum, timing/*.log, the plant dirs p11n, p11s, p13, p18 and pW*, base/, run.sh, plants.sh, edit1.py, edit2.py, commit1.txt).