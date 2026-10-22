G1 hand-back (lane G, its only block). Branch audit/u35-g in S/wt-u35g. One commit, ef01de5, on top of 1d77560. Nothing is pushed and nothing is uncommitted. No typings link is left, and nothing of mine is running. I made about 64 tool calls.

**What changed.** Both files now boot and run their scenarios on one DrivenTime (tests/_fake_time.py) with sleeps=True. It is lent to every `asy_*` module that holds asyncio, plus the twin's `machine` (Timers, WDT, chip clocks) and `network`. The clock is in place before `_boot`, so every tick reading comes from that one clock. Each `_until` wait is now `clock.run_until()` within the same `_WAIT_S`, counted in driven seconds. Boot and start_tasks/start_timers run through a new `_driven()` helper. Every assertion is kept.

**Wait table** (measured real ms at base, wozi/arzi/dev; S/u35/laneG/probe_tp_wozi.log, probe_hr.log):
- Timer pool, readers case (per reader):
  - boot: 0.15 s. Moved.
  - start stagger (asy_system_service.py:759, :777): 1.0 s. Moved.
  - "task never ended on its failed arm" (trigger loop's first tick): 0.1-0.8 s. Moved.
  - "never restarted" (supervisor pass, :594, 2 s): 1.2-2.0 s. Moved.
  - "never read once the pool freed" (reader period): 1.3-4.0 s. Moved.
- Timer pool, tick case: boot and supervise 1 s; uptime fallback 0.9 s; SYSTEM re-arm 0.2 s; NTP re-arm 1.0 s; WiFi re-arm 2.5 s. All moved.
- Timer pool, reboot case: boot 1.5 s; shutdown 0.1 s; watchdog run-out 8.0 s. **Stays real.** `took` measures the run-out against the twin WDT's own clock.
- Timer pool, mempause case: boot only, no wait. Stays real.
- Hot replug, arzi's scd30 and sgp40: read before unplug 2.1/3.1 s; task end on unplug 16.2/6.1 s; restart 1.8/0.9 s; read after re-plug 3.0/1.8 s; plus boot and start. All moved.
- **dev's cases stay real**: timer pool's readers and tick cases, and hot replug's bmp3xx, isl29125 and power-cycle cases. The reason, at line level: digital_twin/machine.py:901 diffs machine's tick against `_flash_stall.EPOCH_US`, which is read off the real clock (2**62 period, _flash_stall.py:33). The driven 2**30 ticks refuse it (tests/_ticks30.py:16), so the UART crossover attach raises TypeError (seen in h1_tp_dev.log:10). The guard is `plan.get("uart")` in `_run_on_clock` in both files.

**Seen failing on plants:** 17 plants in a scratch tree, all bitten, each red with its own wait's message. Logs are bite_*.log.
- Boot and start: PA (setup hangs), PB (start_tasks hangs), PB2 (start_timers hangs).
- Readers case: PC (failed arm never ends the task), PD (supervisor skips the restart), PE (base trigger never sets read).
- Hot replug: PE2 (SGP40 trigger never sets read), PF (ladder never gives up), PG (no sample stored after a give-up).
- Tick case: PH (TickSeconds frozen), PI (uptime re-arm skipped), PJ (NTP tick retry skipped), PK (WiFi re-arm skipped).
- PW (supervisor stops feeding): "the re-plug of scd30 starved the watchdog". So the WDT assertion still catches a failure on the driven clock.
- Three first tries missed and were re-planted:
  - SCD30's own trigger: its first read comes another way.
  - The first NTP plant: it cascaded into a budget reset.
  - The first PE2 plant: the SCD30 read handler.
- Nothing planted is committed. The tree copy is deleted.

**Times** (s, base f3fff0e → head, gc -1 / 32768):
- Timer pool:
  - wozi: 34.6→11.6 / 34.8→11.7
  - arzi: 27.1→10.7 / 27.1→10.9
  - grkizi: 26.9→10.8 / 27.1→10.9
  - klkizi: 26.9→10.7 / 27.1→10.9
  - schlafzi: 27.0→10.7 / 27.1→11.0
  - dev: 43.3→43.3 / 43.5→43.6 (real)
- Hot replug: 70.8→37.3 / 71.0→37.7.
- Settrace, head only: timer pool wozi 12.5 s at 1.6 CPU-s; hot replug 39.0 s at 3.7 CPU-s. CG had 36/2.3 and 72/5.
- No file is slower.

**Checks (all green):**
- ruff on both files.
- mypy, cold cache: main pass with no args, main pass over `src tests tests_hardware/device_scripts`, and the twin pass.
- One pytest process with the 12 commit checks, the 17 repo-wide scans and the reader test_device_tomls: 1008 passed.
- Every run: rc=0, zero MemoryError and zero "memory allocation failed".

**Silent-failure scan:**
- Class 3, twin mode, new: dev's cases keep host-load-dependent real waits (`_run_on_clock` in both files). The cause is machine.py:901.
- Class 4: none. `_until` re-raises with the wait's message.
- Effect per mode: test-only. STA, AP, Silent, Off and USB are unchanged on every device.

**Decisions (agent, 2026-10-22):**
- One clock for the whole graph, from before boot. Swapping after boot would mix real 2**62 ticks with driven 2**30 ticks.
- A UART-wired plan stays real.
- The reboot case stays real.
- `_WAIT_S`/`_RUN_BOUND_S` keep their values and tags.

**Facts owed:**
- To D: SPECIFICATION.md:12107 and :12109 (`l2.timer_pool_wait_s`, `l2.hot_replug_wait_s`) now bound driven seconds, except the reboot case and dev. Their "measurement owed: elapsed of the test" text is only partly true now.
- To the lead/V: once V's `_flash_stall.plain_us` reaches machine.py:901, try removing the uart guard in both files. dev is now the slowest timer-pool device.

**Runs:** every run has its lines in RUNS.md, all done:
- the probes;
- h1/h2 head runs (the first dev run was red with the TypeError, and that led to the guard);
- 19 bite runs;
- pairs.sh (pid 12053, rc 0);
- mypy and checks.

**Logs** are in S/u35/laneG/: times.txt, pairs.out, pb_*/ph_*.log, bite_*.log, probe_*.log, h1_tp_dev.log, c_mypy_*.log, c_pytest.log.