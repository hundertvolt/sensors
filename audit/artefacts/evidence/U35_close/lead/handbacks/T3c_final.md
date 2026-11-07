T3c hand-back (lane T, audit/u35-t, S/wt-u35t). Commits: 4c88787 and dc8c180, on 0a19769. Nothing is uncommitted and nothing of mine is running. I used 62 tool calls. No src/ change, so no rebuild.

**Steps by verdict**
- **Drift check: applied (4c88787).** The slope is now the Theil-Sen median of the 21 pairwise slopes over deaths 3-9. The 32 B bound is kept. The constant's comment states the method, R1's figures and the two limits in one line: two transients at deaths 8-9 read 38 B (a false red); three mid-window transients plus a 64 B plant read 32 B (still red, at the edge). Green at -1, at 32768 and under settrace (dev).
- **Fold (14): applied as a guard.** Green on head (dev). The bites are below.
- **Fold (16): applied as a guard.** It runs at a 100 ms step: ten polls outlast the twin's 0.7 s join, so each attempt ends joined without an IP. A floor (`no_ip >= streak`) stops it passing on CONNECTING polls. Cost about 6 s on arzi, against about 25 s at the real 500 ms step.
- **Fold (15): applied as a guard.** No SSID, two window ends fired through the timer's callback; the AP comes back each time and the phase is never silent. 1 ms step, about 1 s.
- **Port band (found, fixed).** One more arzi test ran past dtsi's 16-port block: `AssertionError: dtsi ran past its port band 19100-19115` (in the watchdog test). Only the asyncio.start_server task binds the web port (asy_webserver_service.py:960), so boots that never start it now share one `_UNSERVED_PORT`. The three serving boots still take a fresh port. arzi now uses 4 of its 16.
- **Waits: partly (dc8c180).** Test 4's uptime ticks are moved; the rest are in the table.
- **Folds (11), (13) and (18): not started** (budget). They go to T4.

**Seen failing and bites** (plants in their own dirs; every control ran from tests/ with no plant)
- Drift plant (+bytearray(16) per death; a test copy alone in t3c/p_drift): `64 B retained per supervised death` at -1 and at 32768.
- (14), store branch (asy_base_classes): `scd30's failed snapshot sent {'SCD30': {...all None}}`.
- (14), bmp3xx's callback returns {}: `bmp3xx's failed snapshot sent {'BMP3XX': {...}}`. The same plant in isl29125: `isl29125's failed snapshot sent {...}`.
- (16), the no-verdict W dropped: `the streak persisted (0, 1) no-verdict and to-hotspot slots`.
- (15), no-SSID sent to silent after the first hotspot: `window 1: the hotspot never opened, phase 4`. Run twice: before and after the step change.

**Wait table**
- Test 4's uptime ticks: moved, fired once per poll. Saves about 1.3 s per device.
- Test 4's link wait: stays. The twin's 0.7 s join is real time (network.py `_CONNECT_DELAY_S`); stepping the poll saves at most 0.2 s.
- The PC-report test's link wait: stays. The drift figures were measured with it.
- Tests 6-8 (SGP40 init and cycle waits) and test 9 (SCD30 and monitor cycles): not moved (budget). They go to T4.

**Times, final file** (s, head / base; base = f9569b9's file run in the head tree from a clean dir, back to back; all rc=0, mem=0)
| Device | -1 | 32768 |
|---|---|---|
| dev | 22.58 / 22.99 | 23.23 / 23.47 |
| arzi | 73.43 / 118.66 | 75.12 / 118.50 |
| grkizi | 20.60 / 21.49 | 20.51 / 21.79 |
| klkizi | 20.53 / 21.52 | 20.67 / 21.65 |
| schlafzi | 20.32 / 21.62 | 20.62 / 21.69 |
| wozi | 20.91 / 21.98 | 21.15 / 22.05 |
- Settrace, dev (r2, the drift code as committed): 26.36 / 25.02.
- Added time: (14) about +1 s on dev; (15) plus (16) about +6.8 s on arzi.

**Decisions (agent, 2026-10-21)**
- The pairing base is f9569b9's file run in the head tree (S/wt-u35base is at f3fff0e).
- (15) and (16) run once, on the first device (`_first_device_only`), as the radio-rung test does.
- The unserved port is shared by every boot that never starts the web server.
- (16) steps at 100 ms with the floor; (15) steps at 1 ms.

**Effect per mode:** test-only. STA: (16). AP: (15), and (16)'s end. Silent: (15) proves it is never reached. Off and USB: none. The drift check runs on every device, (14) on dev, (15) and (16) on arzi.

**Checks:** ruff clean; twin mypy 0 issues in 52 files. 947 passed: the 12 checks, test_device_tomls (the one reader), gc_collect_sites, fake_surface_conformance, twin_fake_catalog and port_bands. No allow-list row orphaned. Silent-failure scan of my file: nothing new. A test that ever served on the shared port would fail visibly with EADDRINUSE.

**Runs** (all in RUNS.md)
- r1, pid 27465: rc=1, expected (the bites). Its arzi control was the port-band red.
- r2, pid 30198: rc=1 from the p15 bite only; 24 paired runs and both settrace runs rc=0.
- r3, pid 9168: arzi rc=0 at both stages; the p15 bite rc=1.
- r4, pid 12101: rc=0, 24 runs.
- Raw coverage files deleted.

**Relay:** none written. Owed: none.

**T4 starts** from dc8c180, clean, no rebuild needed. Open items:
- folds (11), (13) and (18);
- the waits in tests 6-9;
- T3b's leftovers.

**Logs:** S/u35/laneT/t3c/ (r1-r4 .sum and logs; plants p_drift, p14_scd30, p14_bmp, p14_isl, p15, p16; base/; run.sh).