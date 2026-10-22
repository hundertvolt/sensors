G1a hand-back: klkizi, GC -1, reset_errors_while_the_escalation_logs_is_refused_and_clears_nothing. Fixed in commit 02e3be8 on audit/u35-g1a. The defect was in the scenario and its test knob, not in the firmware.

**Mechanism (at 069b9fe)**
- src/asy_system_service.py:578 limits the escalation's entry write with `wait_for_ms(entry, _ESCALATION_ENTRY_WAIT_MS)`, 1200 ms (:77).
- The knob held its gate inside that same coroutine (digital_twin/run_generic_integration.py:657-659). So everything the host did ran on the firmware's 1200 ms clock, plus the real write: noticing ENTRY_HELD (boot tail and the 50 ms line poll), then GET, PUT ResetErrors and GET (scripts/_digital_twin_scenarios.py:1500-1505), then the 50 ms stdin poll (run_generic_integration.py:238/849).
- When the bound fired, `runner_task.cancel()` was passed on into the held entry (v1.29.0 extmod/asyncio/funcs.py:49-50, task.py:165-171). The cancel landed either before the write or in the middle of a block. A block cut in the middle was left BUSY, which is why the gate's relaunch printed "FRAM Read status byte is not 1 but 2". The reboot then went ahead as designed, so the relaunch had no SYSTEM entry (:1514).
- Measured on an idle host, device side: the hold took 975 ms and the write 60 ms, so the margin was only 165 ms.
- History: the scenario and the knob came in with 06a8ae5, when this write had no time limit. The limit came in with 72b1281 and the scenario was never adjusted, so since then nothing guaranteed the scenario its window.

**Reproduction (scratch copy)**
- A planted host-side sleep before ENTRY_RELEASE of 0.45, 0.55, 0.65 or 1.0 s: 4 of 4 runs failed with the gate's assertion and "its entry not persisted within 1200 ms".
- Load alone, with the unchanged 069b9fe tree under 6 busy loops (run queue 11-13, CPU idle 0%): 4 of 6 failed the same way (3 of 3 at -1, 1 of 3 at 32768). Two of those relaunches logged the half-written block.

**Fix**
- Knob: a held entry's time limit now starts only when the host releases it. It wraps the service module's `asyncio` so `wait_for_ms` waits for the release first, then runs the real 1200 ms limit on the real write. The hold itself, ENTRY_HELD and ENTRY_RELEASED are unchanged, and the knob raises an error if asy_system_service is not imported.
- Scenario: it keeps the entry held for at least `_ESCALATION_ENTRY_WAIT_MS`, so fast and slow hosts take the same path and a knob that counts the hold against the limit fails on every run. The exit message also says how long the entry was held.
- Docs: the knob's README row and its usage text now say where the limit starts.
- What the scenario proves and all its checks are unchanged. No flash or SCD30 NVM write was added or changed, and no operating mode is affected (twin-only change).

**Proof**
- Seen failing first: the new scenario on the old knob failed with the same assertion. With the fix, planted delays of 1.0 s and 3.0 s passed (device-side holds of 2.78 s and 4.68 s, writes of 49 and 46 ms).
- All 6 devices at both stages: 12 of 12 passed. These ran beside another agent's 4 busy loops (run queue 4-7). All 12 entries were persisted, with no timeouts and zero MemoryError or "memory allocation failed" lines. The largest gap between watchdog feeds was 2982 ms.
- Under load, klkizi: 3 of 3 passed at -1 and 3 of 3 at 32768 (run queue 11-13), interleaved with the failing control runs. No timeouts, nothing that would have triggered the watchdog, largest feed gap 3373 ms.
- tests/test_digital_twin_run_generic_integration.py: 43 of 43 at both stages. The runtimes of 1.53 s and 1.58 s against the base table's 1.32 s and 1.41 s were measured on a loaded host, for a file I did not change.
- tests_scripts, 28 files (the 12 pre-commit checks plus every reader of the three changed files): all green. test_twin_runner_test_flags went red once, because my error message started with "--test-" and was counted as a thirteenth flag; I reworded it and it is green.
- ruff, the twin mypy pass and the host mypy pass are clean.
- The scenario takes 10.3-10.5 s instead of 9.6-9.7 s, because of the minimum hold.

**For the lead**
- What still depends on host speed: the hold still stops the supervisor's watchdog feed, and the feed-gap check fails above 6000 ms (75% of 8000, scripts/_twin_process.py:45/276). That leaves the host about 3.3 s for its steps inside the hold. The planted 3.0 s run reached a 5767 ms gap. Taking the hold out of this check would mean changing digital_twin/machine.py, which is not in my files.
- The timeout path (entry not written, reboot anyway) has no twin scenario of its own. Only the unit test `test_an_escalation_whose_entry_write_waits_on_a_held_lock_still_records_code_20_in_budget` covers it, and with this fix the knob can no longer reach that path. Whether to add one is your call.
- Firmware question, src/ untouched: the message at src/asy_system_service.py:580, "its entry not persisted within", can be wrong. Control run 32768_7 printed it, yet its relaunch logged a half-written block and still found the entry. One of the two blocks had already been written when the cancel arrived. Proposed wording: "its write not completed within".
- tests_scripts/test_twin_record.py will be red because the runner changed, which the common rules expect. No doc goes stale; SPECIFICATION.md:6600 is still accurate.
- Silent-failure scan: class 3 (the path was chosen by host speed) is fixed by this commit. A knob whose wrapper is never reached now fails loudly through the minimum hold (class 4). The feed gap above is the class-5 residual.
- Not run: the 17 repo-wide scans, which are not in this block's proof list.

RUNS.md has start and exit lines for pytests.sh (rc=1, then fixed), p1 (rc=0) and p2 (rc=0). The logs are in S/u35/laneG/g1a/, and the scratch copy is deleted. Nothing is uncommitted.
nothing of mine is running