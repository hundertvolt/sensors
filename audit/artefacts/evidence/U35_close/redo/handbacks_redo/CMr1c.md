CMr1c hand-back, saved by the lead from the message it sent (2026-10-27). Commits 149d145d, 56c3eb8e, 4cf293d0 on audit/u35-cmr1b (on 52f691dc).

CMr1c hand-back. Branch audit/u35-cmr1b in S/wt-u35cmr1b. Three commits on 52f691dc, not pushed, nothing uncommitted. Each commit was checked green.
- 149d145d: CMr1b's item 3, the deduplication. Files: `_twin_devices.py`, the wiring contract test, integration, network_neopixel and neopixel_wifi.
- 56c3eb8e: items 1-2. Files: bus_hazard, fram, clock_jump, ntp and hot_replug.
- 4cf293d0: my rows in audit/b3/matrices.md, one per pick site: class, measured reason and device set, with the open sites marked open.

**My changes to CMr1b's diff.** I kept everything else.
- `wiring_read()` missed module constants. A device's warn thresholds sit in `_FIELD_WARN_*`, not in the construction line. It now also reads every `_CONSTANT` a driver's statement names. Two new contract cases cover it, one named and one unnamed. The groups on the real tree are unchanged: they match CMr1b's table.
- Root cause of the ntp red (w_w2_ntp, 2 of 16 failing at both stages). The file's boot through main() never wired the UART crossover's bounded pollers. On dev, the only device with a UART link, a real select.poll() queried the twin's UART fake, and the per-test reset raised "a real select.poll() queried a UART fake N times". The file now wires the crossover after construction, the same step the runner and the construction scenarios already take. Result: 16/16 at both stages.
- The ntp read sets now name what each scenario actually waits on, with the same groups as before:
  - restore: `sgp40, fram, scd30`, since its reading waits on SCD30 humidity.
  - lost-sync: `notification, scd30, neopixel`, since it counts NeoPixel frames.
- D.15 order: CMr1b's per-device helpers sat between the tests. I moved them into private alphabetical order in 6 files, and also fixed two orderings that were already wrong at base (clock_jump `_set_clock`, neopixel_wifi `_blocked_dir`).

**Red first, from CMr1b's logs; all green now**
- red_d1 (board inherited from the previous device): RuntimeError "configure_fram_state_path() after a bus was constructed".
- red_d2: band 19400-19419 overrun. Fixed by reusing each word's port; no band was widened.
- red_d3: "left a task parked on the scheduler".
- Final runs at both stages, all with zero memory markers: bus_hazard 22/22, fram 54/54, clock_jump 6/6, ntp 16/16, hot_replug 2/2, neopixel_wifi 8/8, network_neopixel 44/44, integration dev 14/18 (4 skipped, the same as base).
- CMr1b's batch1 head runs: all 6 integration jobs green at both stages.

**Checks:** lint_direct rc=0; all three mypy passes clean from a cold cache; the 9 reader files, 804 passed.

**Efficiency, my changes**
- clock_jump stamps test: fires the BMP3XX read event after each clock step instead of waiting out its timer (12.6 s down to 1.2 s).
- ntp restore, outage boot: the lost NTP reply is waited out at the file's own 1000 ms bound instead of the product's 5 s. No assertion reads that length.
- ntp restore, backup: fires the SGP40's read event for the backup cycle. Together these cut the restore test from 14.3 s to about 9 s per device.

**Times in s, base52 then head, at -1 / 32768.** Base figures are CMr1b's back-to-back runs, except bus_hazard, which I measured.

| File | Base | Head | Change |
|---|---|---|---|
| bus_hazard | 94.2 (-1 only) | 122.8 / 132.5 | about +30 % |
| clock_jump | 24.9 / 25.5 | 37.8 / 38.8 | +52 % (CMr1b's widened version: 49) |
| ntp | 34.6 / 33.8 | 61.0 / 63.2 | +76 % / +87 % |
| hot_replug | 8.4 / 9.1 | 17.2 / 18.6 | about +105 % |
| fram | 0.8 / 1.0 | 1.3 / 1.8 | +0.5 s |

- network_neopixel, neopixel_wifi and the integration jobs are at or below base. The integration total at -1 went from 181.8 to 168.4 s.
- Four files are still over CHECKLIST 14's 10 %: bus_hazard, clock_jump, ntp and hot_replug. Measured cause of each:
  - bus_hazard: the SCD30 system-command test went from 9.4 to 22.6 s (four words, now on arzi and dev). The erase race went from 1.5 to 6.1 s, because dev's 256 KiB chip takes longer to erase.
  - clock_jump: its backup test boots 12 times (3 boots on each of 4 wirings), and each boot spends 1.7 s in the SGP40's init waits: a 1 s general-call reset plus waits from the datasheet.
  - ntp: each restore still spends 1.3 s on the first sync, 3 s on the SCD30's first measurement and about 1.5 s on the restore cycle.
  - hot_replug: each of its 8 runs spends about 2 s in the driven-clock failure ladder.
- What I would do next: run the clock_jump and ntp boots on DrivenTime, as hot_replug's already do, which removes the wall-clock waits. I committed these four files anyway, green, as the conservative choice, because they add coverage the owner's rule requires. You can split or revert them.

**Not done, for the next block**
- Item 3's remaining sites. These are all marked open in matrices.md:
  - the scd30 helper :54, the sgp40 helper :239, launch :51, wifi_modes `_scenario_plan()`;
  - clock_jump :275/:314/:336/:354, ntp :440/:464/:495, loop_end :238, run_generic_integration :933/:1031/:1072;
  - the tests_scripts `DEVICE_NAMES[0]` sites;
  - deduplicating fram_less_boot and `_lag_run`.
- Item 4's four bites. No bites were made.

**Deviation:** batchB (the bus_hazard runs) started while 6 heavy processes were running, mostly other lanes'; CHECKLIST 12 allows at most 4. Its base and head ran back to back under that same load. The results are green, but the times may be inflated.

**E.2.1 sentence for D3r** (CMr1b's text, updated for the constants; I did not re-locate the SPEC lines): "A driver-specific scenario runs once per distinct wiring of its drivers: devices are grouped at run time by what the scenario reads of their generated plan and module (each driver's construction statement and every module constant it names, and the pins and every occupant of each bus it sits on), and each group runs on its first device; a scenario no device setting reaches runs once on the first device wiring its drivers."

**Housekeeping**
- Deleted CMr1b's scratch trees (S/u35/laneC/cmr1b/trees, 1.2 GB) with one literal-path rm, after confirming no process read them.
- Deleted my three probe copies from the worktree's tests/.
- Every run has start and done lines in RUNS.md, and all exited. Logs, times.txt and my scripts are in S/u35/laneC/cmr1c/.

nothing of mine is running
