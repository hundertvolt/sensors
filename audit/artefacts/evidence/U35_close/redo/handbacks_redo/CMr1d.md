CMr1d hand-back, saved by the lead from the message it sent (2026-10-27). Commits e7d9f4a3 and f2fd7565 on audit/u35-cmr1b (on 4cf293d0).

CMr1d hand-back. Branch audit/u35-cmr1b in S/wt-u35cmr1b, two commits on 4cf293d0, not pushed, nothing uncommitted. I stopped at a seam near 70 tool calls. Logs and scripts are in S/u35/laneC/cmr1d/ (times.txt, load.txt, ast_proof.txt).

**Commits**
- e7d9f4a3, item 1: the two reorders are undone. clock_jump's `_set_clock` is back before `_boot`, and neopixel_wifi's `_devices_with_a_neopixel` is back before `_blocked_dir`. CMr1b's new helpers stay in order.
  - AST proof against 4cf293d0 (ast_same.py): every definition has an identical AST, the other statements keep their sequence, and the non-blank lines are the same.
  - Against 52f691dc, the pre-existing definitions keep the base's relative order. The only D.15 breaks left are the two that base already had.
  - Both files green at both stages: clock_jump 6/6, neopixel_wifi 8/8. ruff and the readers are clean.
- f2fd7565, item 2 for clock_jump. The backup scenario's 12 boots, the SGP40 init and the backup or restore cycle now run on one driven clock (`_DrivenWall`, a DrivenTime subclass). Its time(), gmtime() and localtime() read the twin wall clock once it is installed, and the built-in time before that.
  - Keeps: every boot, every wiring, every assertion, the real SGP40 init through the twin chip, and FRAM persistence across boots.
  - Skips: only the wall-clock length of the 1 s general-call reset and the datasheet waits.
  - Bite: a copy whose `_wall()` returns the built-in time fails the expiry check, restoring `(1793078370, [])` instead of refusing it.
  - Checks: lint_direct rc=0, all three mypy passes clean from a cold cache, readers 804 passed.

**Times in s, base52 then head, back to back.** Load before each pair was 0.2-1.7 with at most 3 heavy processes, mostly other lanes'.

| File | -1 | 32768 | Status |
|---|---|---|---|
| clock_jump | 25.3 / 17.3 | 25.7 / 18.8 | now below base (was 37.8) |
| ntp | 34.7 / 62.0 | 34.0 / 64.3 | +79 % / +89 %, not done |
| hot_replug | 8.9 / 17.8 | 9.5 / 19.6 | +101 % / +107 %, not done |
| bus_hazard | 95.2 / 124.4 | 97.6 / 131.7 | +31 % / +35 %, not done |

**Measured causes in the three files not yet fixed**
- hot_replug: DrivenTime is already in place, so this is not a wait. Each ladder takes 1.3-1.6 s of wall time while only 30-109 driven sleeps are parked.
  - The cost is the 13 FRAM-persisted log entries. Each takes 70-100 ms; the ladder makes 1632 calls of `_CS_SETTLE_US` (sleep_us(2)), about 816 SPI transactions.
  - So the cost is the twin's CPU in the FRAM path (src/ and digital_twin/, neither mine). I found no lever that leaves the tests and wiring unchanged.
  - Conservative reading: this is the measured residual of each added wiring's real ladder. It is yours or the owner's to accept or route.
- bus_hazard, per test at 32768:
  - SCD30 system command: 9.8 -> 24.4 s, 8 boots. Each boot's `_supervised_graph` passes through `start_tasks()`, which waits 1000 // n ms between starts (`src/asy_system_service.py:778`), about 1 s per boot. Next step: drive that stagger.
  - Erase race: 1.6 -> 7.1 s, the erase of dev's 256 KiB chip. That is real work, a residual.
  - Timed pause: 2.3 -> 7.2 s, not probed.
  - The ten FRAM tests: +0.7-1.9 s each, about 0.33 s per added boot, a residual.
- ntp: not probed further. It runs the real main() with real UDP to the responder, so the clock_jump approach does not carry over directly. CMr1c's wait list is in cmr1c/probe_ntp.log.

**Deviation, root-caused:** my first base52 bus_hazard copy failed 5/22 with ENOENT. My tests-only copy lacked `buildgen/`, and `tests/_error_codes.py` finds error_catalog.json next to its own file. I linked buildgen (unchanged since 52f691dc) and reran: 22/22 at both stages. Those numbers are the ones above.

**Not done, for the next block:** item 2 for ntp, hot_replug and bus_hazard; item 3's open sites, none classified; item 4's four bites; item 5's matrices rows; the E.2.1 sentence re-check. Line numbers in the brief refer to 4cf293d0; clock_jump's have moved since f2fd7565.

**Facts owed**
- To the lead: clock_jump now duplicates hot_replug's `_driven`/`_driven_modules` helpers. I flagged this under D.10 instead of merging them silently.

**Housekeeping**
- After the restart, no run of mine was cut: every CMr1d RUNNING line has its done line, so I added no CUT line.
- I deleted my base52 tree copy with one literal-path rm.

nothing of mine is running
