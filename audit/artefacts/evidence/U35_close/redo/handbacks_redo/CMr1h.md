CMr1h hand-back, written by the lane (2026-10-27)

Worktree S/wt-u35cm2, branch audit/u35-cm2 at cce274e1. **No commits.** The tree is clean: the item 1 attempt was measured slower and reverted, and my scratch copies in tests/ are deleted. I stopped at about 80 tool calls, at the seam after items 1 and 2 and the integration file's skips. Logs, scripts and probes are in S/u35/laneC/cmr1h/: times.txt, load.txt, matrix.txt, heap_ntp_m1.txt, the probe extras and one.sh. RUNS.md has 14 RUNNING lines and 14 done lines, all named U35 lane CMr1h. I changed no wait's value.

## Item 1: bus_hazard's last lever. Attempted, failed, reverted
**What I built:**
- `DrivenTime.release()` in tests/_fake_time.py, with two self-tests in test_driven_time.py (21/21 passed).
  - After release, `now` runs on at the real rate from the instant reached, so every stamp stays on the one 2**30 clock with no discontinuity.
  - Each module's `asyncio` becomes the real one again.
  - Each parked sleep, and each parked `wait_for()` bound, ends on the real clock after the time it had left. A bound keeps awaiting the same task.
  - Release was needed because a bound is parked when the boot ends. A first version that refused bounds failed both tests with exactly that.
- In the two tests, `_driven_boot()` drove `_boot()` and `_supervised_graph()` (the stagger and the timer sequencer) on the clock, then released it before the shutdown sequence. Every boot, wiring and assertion was kept.
- Both tests passed with zero memory markers at -1.

**Measured** at -1, base then head back to back, 1-2 heavy processes, load about 2 (load.txt):

| run | SCD30 system commands | erase race | the two |
|---|---|---|---|
| base | 23.47 / 23.56 s | 6.53 / 6.26 s | 30.03 / 29.86 s |
| driven boot | 27.94 s | 9.39 s | 37.37 s |
| driven boot, asyncio restored at release | 28.31 s | 9.34 s | 37.68 s |

**Phase probe** over 11 boots (8 SCD30, 3 erase; bootprobe_*_m1.log):

| phase | base | driven |
|---|---|---|
| `_boot` | 2.91 s | 2.63 s (11,848 settle rounds) |
| `_supervised_graph` | 14.14 s | 3.49 s (1,581 rounds) |

- So the driven start saves 10.9 s as intended, but the part after release grows by about 18 s, and the tests end 7.5 s slower.
- That growth is not attributed within this block. Candidates, neither measured:
  - every `time` read of the driven modules, the twin machine's per-transfer reads among them, now goes through DrivenTime's Python `ticks_ms()`;
  - the twin chips, which are not on the clock, run on real time while their drivers saw about 1.3 s pass. That shifts their phase (for example the SCD30 healthy window).
- The attempt made the file slower, so it is reverted, `release()` included, since it would have no user. **The formal pair was not taken**: the reverted head is CMr1g's measured head (bus_hazard 96.0/97.6 → 118.9/128.4 s against base52).

**The residual and its cause** (from the base phase probe):
- Each real boot costs `_boot` plus `_supervised_graph`:
  - arzi: 0.18-0.28 + 1.04-1.06 s;
  - dev: 0.30-0.36 + 1.57 s.
  - The graph phase is the 1.0 s `start_tasks()` stagger plus the timer sequencer.
- **SCD30 test:** the added wiring (dev) adds 4 boots, about 7.5 s, plus dev's healthy-window cycle.
- **Erase race:** the added dev and grkizi boots add about 3.1 s, plus dev's 256 KiB erase.
- These real boots of the added wirings are the measured residual of the two tests.

## Item 2: the heap step
Probe: ntp's first-sync test (arzi) run 8 times in one process. After each run: reset, `gc.collect()`, then `micropython.qstr_info(1)` and `mem_info(1)`. Log heap_ntp_m1.log, summary heap_ntp_m1.txt.

**The qstr pool is not the cause:**
- The first boot interns 1,829 qstrs (24,486 string bytes): n_qstr 2687 → 4517, n_total_bytes 89,575 → 115,892.
- Every later re-boot interns 0 new qstrs, and the pool stays at 4517 / 115,892 through rep7.

**The step is real, fixed and unbounded** in the test process:
- mem_alloc after a collect grows by exactly **+147,488 B** per arzi re-boot, identical at every one of reps 1-7: 0.97 → 1.86 MB. It does not stop growing.
- The heap map shows the same head deltas at every re-boot: 1194 other objects ('h'), 267 tuples, 86 str, 73 lists, 61 bytearrays/arrays, 52 dicts, 13 bytecode functions, 4 floats.
- So part of each boot's object graph (about a third of the first boot's +420 KB) stays reachable.

**Not found yet:**
- A walk of every list, dict, set and tuple reachable from `sys.modules` and `asyncio.core._io_queue` (through module globals, class dicts and container items) found **no container growing** between re-boots, and no new path (walk_ntp_m1.log).
- So the holder is reached only through an instance, a closure or a native object. The walk could not traverse these (only 3,238 nodes were reached).
- Open: the holder.

**On silicon:**
- The board runs `build_system()` once per power-up. A retention per `build_system()` therefore cannot accumulate there, and at 147 KB per boot it is a test-process artefact of re-booting in one process.
- Not shown by this measurement: whether the same holder also keeps something per supervisor task restart, which would happen on silicon. Finding the holder settles it.

## Item 3: sites
**The integration file's skips: all 50 are classed.** Sites at cce274e1; device sets computed from the generated plans in matrix.txt. The per-device counts match the lead's: arzi 1, dev 4, grkizi 10, klkizi 14, schlafzi 14, wozi 7.
- **L, lacks the part: 5 skips.**
  - :799 `_driver_specific("bmp3xx","scd30","isl29125")` runs on dev only.
  - arzi, grkizi, klkizi and schlafzi wire neither bmp3xx nor isl29125; wozi wires no isl29125.
- **D, deduplicated: 25 skips.** The skipped device's read key equals that of the device that runs it, under the owner's matrix-deduplication rule.
  - :563 sgp40+scd30: runs arzi, dev, wozi; grkizi, klkizi and schlafzi share arzi's key.
  - :935 neopixel: runs arzi, dev; grkizi, klkizi, schlafzi and wozi share arzi's key (pin 15).
  - :1030/:1054/:1088/:1118 sgp40+fram: runs arzi, dev, grkizi, wozi; klkizi and schlafzi share grkizi's key (CS 17).
  - :1171 notification+scd30: runs arzi, dev; the other four share arzi's key.
  - :1228/:1292 notification+scd30+sgp40: runs arzi, dev, wozi; grkizi, klkizi and schlafzi share arzi's key.
- **I, identical mechanism: 20 skips.**
  - :953 `_first_device_wiring("neopixel")` runs on arzi. It asserts only the DNS listener's poll_idle_ms; neopixel is needed only for the boot.
  - :759, :819 and :889 `_first_device_only()` run on arzi. They are the Wi-Fi join, hotspot and radio re-select paths, and no device TOML sets a Wi-Fi setting: the TOMLs differ only in [device] name/hostname and wiring.
- **For the lead (CHECKLIST 1c):**
  - The brief says a skip is kept "only where that device lacks what the test drives". Only L meets that literally. I kept D and I under the owner's deduplication words and CMr1b's structural grouping, not widened.
  - :759 (`test_a_dhcp_server_that_never_answers_leaves_a_persisted_trace`) reads the WIFI logger's slots. WIFI is FRAM-backed, and FRAM has 3 distinct wirings (arzi/wozi, dev, grkizi family). If that read reaches the FRAM wiring, this test is W: `_driver_specific("fram")`, 2 more boots. I did not measure whether it does.

**Not reached:** cmr1d item 3's sites. Their line numbers are from CMr1c and must be re-located:
- tests/test_digital_twin_scd30.py:54
- tests/test_digital_twin_sgp40.py:239
- tests/test_digital_twin_launch.py:51
- wifi_modes `_scenario_plan()`
- clock_jump :275/:314/:336/:354
- ntp :440/:464/:495 (the ntp booted tests use `generated_devices()[0]`, for example the first-sync test)
- loop_end :238
- run_generic_integration :933/:1031/:1072
- the tests_scripts `DEVICE_NAMES[0]` sites
- the fram_less_boot / `_lag_run` deduplication.

## Item 4: the four bites
Not reached: network_neopixel, neopixel_wifi, fram_less_boot, `_lag_run`.

## Item 5: matrices.md and E.2.1
**matrices.md is not edited**, because its "open" row still stands. Rows for the 15 integration skip sites, ready to paste: the classes and device sets above, one row per helper call with file:line at cce274e1.

**E.2.1:**
- Re-checked against `wiring_read()` and the three helpers.
- CMr1c's sentence omits `_first_device_only()`, and says "each bus" where the read covers the I2C bus, SPI bus or UART pair.
- SPECIFICATION.md lines 5159-5163 at cce274e1 still say "only on the device `tests/_twin_devices.py` picks for them". **Final text for D3r**, to replace those lines:

"`tests/test_digital_twin_sensortask_integration.py` runs each driver-specific scenario once per distinct wiring of its drivers. Devices are grouped at run time by what the scenario reads of their generated plan and module: each driver's construction statement and every module constant it names, and the pins and every occupant of each I2C bus, SPI bus or UART pair one sits on. Each group runs on its first device, and a device not wiring the drivers skips. A scenario no device setting reaches runs once, on the first device wiring its drivers. A scenario of a mechanism every device shares, whose settings no device's TOML sets (the Wi-Fi service's join, hotspot and radio re-selection paths), runs only on the first generated device. Every skip names the device that runs it instead."

nothing of mine is running
