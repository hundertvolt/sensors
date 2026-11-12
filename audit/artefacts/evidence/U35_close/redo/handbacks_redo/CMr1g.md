CMr1g hand-back, saved by the lead from the message it sent (2026-10-27). Commits 7534a51a, 5624046c on audit/u35-cmr1b (on a425deec).

CMr1g hand-back. Branch audit/u35-cmr1b in S/wt-u35cmr1b. I added two commits on a425deec. Nothing is pushed and nothing is uncommitted. I stopped at about 82 tool calls, after item 4. Item 5 was not reached. Logs and scripts are in S/u35/laneC/cmr1g/ (times.txt, load.txt, pairs.out, the probe logs, mkprobe.py and the *_extra.txt probes).

**Commits**
- 7534a51a: ntp takes the existing idle-poll skip. One call at module level, plus one sentence in digital_twin/README.md naming the new user.
- 5624046c: in bus_hazard, the timed storage pause runs on a driven clock. New `_driven`/`_driven_modules` helpers and `_POLL_MS`.
  - **D.10 for you:** `_driven_modules` is one more copy of the per-file idiom (hot_replug, clock_jump, timer_pool, ntp). Here it takes a device and loads it first.

**Formal pairs (item 4), in s, base52 then head back to back, -1 / 32768**
Load before each pair: 0.4-2.2, with 0-1 heavy processes (load.txt).

| File | base52 | head | Result |
|---|---|---|---|
| hot_replug | 8.85 / 9.67 | 5.27 / 6.77 | -40 % / -30 % |
| ntp | 33.73 / 34.19 | 34.57 / 38.32 | +2.5 % / **+12.1 %** |
| bus_hazard | 96.0 / 97.6 | 118.9 / 128.4 | **+24 % / +32 %** |
| clock_jump | 25.2 / 25.8 | 17.6 / 19.2 | -30 % / -26 % |

**Item 1: ntp's per-boot cost and the skip**
- **Probe:** per-task CPU, per phase, per scheduler round. The 8 restore boots took 2.5-3.9 s each. Of a 3.0 s boot:
  - 2.34 s is 2,025 polls at 1.16 ms each, in rounds where the map holds clear ThreadSafeFlags plus a real socket (the webserver's listener);
  - main()'s setups take 0.26-0.38 s;
  - the system service's gc.collects take 60-90 ms;
  - the other tasks take about 0.15 s.
  - No real waits and no unused driven clock were found. Nothing tests nothing, so nothing was dropped. The 421 driven 10 ms responder wakes per boot multiply the taxed rounds.
- **Proof that the skip is equivalent on ntp:** the real poll ran on every skipped round and asserted it woke nothing and left the map and the run-queue head unchanged.
  - 23,329 rounds at -1 and 23,321 at 32768; all 16 tests pass.
  - Bite: a skip that also passes over a set flag fails all 5 booted tests with "a skipped poll would have woken a task".
- **Gain:** about 34.0 / 38.4 s, against 39.4 / 43.5 s before. The skip leaves out 15,604 "flag + socket" rounds in the restore test alone.
- **For your decision (CHECKLIST 1c, not built):** a wider skip would also pass over a round whose fds report nothing at a zero-timeout poll of the fds alone, which is what rp2 does.
  - A probe of it takes ntp to 10.9 / 13.6 s.
  - Its verifier passes at both stages: about 44,000 rounds skipped, 20,600 of them beside a socket, and an fd was never ready on a skipped round.
  - It would change `unix_port_idle_poll.py` and the pinned case "a non-flag stream (a real socket): it is called" in its test.
- ntp's +12 % at 32768 is the measured residual of those socket rounds, plus the collects that the added boots' allocation triggers.

**Item 2: tasks parked after DrivenWall exits**
- After every test, at both stages, **0 of the tasks it created are still alive**: 88-680 created per booted test, up to 16 for the others.
- **0 driven wakes** are left on the clock, and none of them has a waiter.
- Cause: run_timed's reap cancels every tracked task before the test ends. So nothing parked can wake in a later test or hold the heap.
- **Heap, not from parked tasks:** mem_alloc after a collect goes 0.83 → 3.97 MB at -1 and 0.87 → 4.00 MB at 32768 across the file. Then it stays flat over the six tests that follow.
  - The steps line up with each newly loaded generated device module (dev +0.85 MB; grkizi and wozi in the restore test +1.98 MB).
  - Each test that boots arzi again adds about 0.15 MB: +163 KB and +147 KB.
  - No module-level or class-level list, dict or set grows. The ~0.15 MB per re-boot is not attributed yet (open; reg_ntp_m1.log, heap_ntp_*.log).

**Item 3: bus_hazard**
- **Timed pause** (5624046c): 6.93 → 1.18 s.
  - Keeps: every FRAM wiring, the mempause dispatch, the dropped write and the landing write, and the uptime-pass deadline.
  - Skips: only the wall-clock length of the boot's waits and the 2 s pause.
  - Bite: a copy whose wait yields without elapsing the clock fails "the timed pause never ended by itself".
- **SCD30 system-command test and erase race:** I built them on the driven clock, but they fail with "a task is still runnable after 1000 rounds at virtual t=3590 ms: a busy loop", so I reverted them.
  - The probe names `_shutdown_sequence` plus the twin WDT's `_countdown`. The sequence's CPU-bound work (the erase's per-unit `_own_feed` and the per-CRC-byte yields) runs more than 1000 zero-sleep rounds at one driven instant, so it trips DrivenTime.ROUNDS.
  - Raising that bound is not mine to do (CHECKLIST 4). So this is the measured residual, with its cause.
  - SCD30 test: 23.0 s over 8 boots. Per boot: the start_tasks stagger 1.06 s and the timer sequencer 0.25 s. The two healthy-window SCD30 cycles take 2.6 s each.
  - Erase race: 6.6 s over 3 boots. The stagger is 1.06 s per boot and `_armed` 0.6 s. CMr1d's "the erase is real work" is not what I measured: the erase's CPU is about 0.7 s.
  - The FRAM tests are residual setups CPU, 0.23-0.3 s per boot.
  - "Erase feeds the watchdog at bus speed" keeps its real wire time, which is its subject.
- **Checks** after the edit: lint_direct rc=0, the three mypy passes clean from a cold cache, 1310 readers passed. bus_hazard 22/22 and ntp 16/16 at both stages, zero memory markers.

**Runs and cleanup:** 38 RUNNING lines named U35 lane CMr1g, 38 done lines. My base52 copy (git archive of 52f691dc, rebuilt with rebuild.sh) is deleted.

nothing of mine is running
