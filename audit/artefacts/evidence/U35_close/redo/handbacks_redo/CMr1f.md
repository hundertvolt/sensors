CMr1f hand-back, saved by the lead from the message it sent (2026-10-27). Commits 6f41678e, a425deec on audit/u35-cmr1b (on 02506cc5).

CMr1f hand-back. Branch audit/u35-cmr1b in S/wt-u35cmr1b. I added two commits on 02506cc5. Nothing is pushed and nothing is left uncommitted. I stopped at the seam after item 2, at about 79 tool calls. Logs and scripts are in S/u35/laneC/cmr1f/ (times.txt, load.txt, the bite dirs, the item*.sh files).

**Commits**
- 6f41678e, item 1: a direct test of `_poll_unless_idle`.
- a425deec, item 2: the ntp booted scenarios now run on one driven clock, and `DrivenWall` moved to a shared helper.

**Item 1 (6f41678e)**
- New file `tests/test_digital_twin_unix_port_idle_poll.py`. It has 5 cases and passes 5/5 at both stages, with zero memory markers:
  - dt 0 with only clear flags: the real wait is not called;
  - a set flag, placed after a clear one: it is called;
  - a non-flag stream (a stand-in whose own `state` is 0, and a real socket): it is called;
  - dt 1, 5 and -1: it is called;
  - an empty map at dt 0: skipped. The comment gives what the real wait would do there, with lines: `core.py:158-177` calls it with a task due and nothing registered; `modselect.c:207-208` counts an empty set as all fds; `:353-364` set t to 0; `:370`'s poll() returns 0 at once and `:390` returns it. The skip also passes over `:345`'s `mp_handle_pending()`, which `py/vm.c:1371` runs as well.
- Bites: five copies of the module, each with one branch removed. Each fails exactly its own case.
  - `dt==0` guard removed: the timeout case fails.
  - Type test removed: the non-flag case fails.
  - `state` test removed: the set-flag case fails.
  - `else: return` removed: the clear-flags case and the empty-map case fail.
  - `and queue.map` added: the empty-map case fails.
- **Needs your look:** `tests_scripts/test_level_containment.py` failed on the new twin file until it had an E.6.6 row. I added a `twin-instrument` row to SPECIFICATION.md, modelled on the `test_digital_twin_unix_port_unretrieved_report` row. If you would rather route that row differently, it is the one line in that commit.
- digital_twin/README.md: one clause added to the `unix_port_idle_poll.py` entry, naming the new test. No digital_twin code changed, so no equivalence evidence is owed.

**Item 2 (a425deec)**
- **Where `DrivenWall` went:** into `tests/_digital_twin_construction_scenarios.py`, an existing twin-test helper that both files already import. Its private `_wall()` moved with it, and the helper's docstring names the new export.
  - Why not a new `tests/_*.py`: the main mypy pass cannot resolve `_wall_clock`, so a new file would also need a pyproject.toml exclude and a digital_twin/typecheck.ini entry.
  - Import direction: twin-test helper to `_fake_time` and `_wall_clock`. `_fake_time` imports nothing new.
  - In clock_jump, `_DrivenWall` and `_wall` are removed, and the `DrivenTime` import moved under TYPE_CHECKING (ruff TC002).
- **ntp change:**
  - `_booted` enters `DrivenWall(*_driven_modules(), sleeps=True)` after `_wall_clock.install`. The list is every `asy_*` module holding asyncio, plus `machine`, `network` and `_ntp_responder`. This follows the per-file idiom.
  - `_until` and `_ticks_to_attempt` now elapse the clock, and each scenario takes the clock.
  - The generated module is not on the list: it has no asyncio and reads only `time.gmtime()`, which `_wall_clock` already covers. `DrivenTime(sleeps=True)` needs an `asyncio` attribute.
- **Keeps:**
  - every booted scenario's real main(), every wiring (restore 4, lost-sync 2) and every assertion;
  - the real loopback UDP exchange with the responder;
  - every product wait (WiFi connect delay, fetch timeout, UDP poll waits, SCD30 interval, SGP40 cycle, notification flash), each still elapsed in driven milliseconds;
  - the restore test's existing 1 s fetch override, unchanged.
- **Skips:** only the wall-clock length of those waits.
- **Wait-length subjects:** none of the booted scenarios has one. The outage test reads `_retry_wait_s` and counts ticks fired by hand.
- **Left on the real clock:** the responder-alone tests and the UDP-shim tests, about 4 s in all. One of them, "serving never starves", is about the real loop.
- **Bites:**
  - ntp: a copy whose `_until` yields without elapsing fails all 5 booted tests ("no first sync within 20.0 driven s", "the boot's attempt never failed…", "no unsync failure…"). This shows the product's waits are still there.
  - clock_jump (CMr1d's bite, redone on the moved helper): `_wall()` returning the built-in time fails the expiry check with `(1793083809, [])`.
- **Possible side effect, not checked:** product tasks that main() spawns and `cancel_all` does not reach should now stay parked on the closed clock's wake events instead of running on in real time.

**Times in s, -1 / 32768**
These are lever checks at load 1.13 and 0.28, not the formal pair: the "U35 lead mc_cov" line in RUNS.md had no done line yet.

| File | base52 (CMr1d) | head (CMr1d) | after |
|---|---|---|---|
| ntp | 34.7 / 34.0 | 62.0 / 64.3 | 39.4 / 43.5 |
| clock_jump | 25.3 / 25.7 | 17.3 / 18.8 | 17.1 / 19.0 |

- ntp per test at -1: restore 36.8 → 24.8, lost-sync 10.5 → 5.1, outage 6.6 → 2.8, first sync 1.8 → 1.05.
- **ntp is not done: +14 % / +28 % over base.**
  - A probe copy with the idle-poll skip (not committed, per your ruling) takes -1 to 34.5 s. So the 1 ms poll tax is about 4.9 s of the remainder.
  - Restore still takes 21.8 s with the skip, about 2.7 s for each of its 8 boots. That is neither product waits nor the poll tax. It is most likely CPU spent per boot (build_system, setups, FRAM), but I did not probe it. That is the next step.

**Checks:** lint_direct rc=0 after the TC002 fix. All three mypy passes are clean from a cold cache, and the twin pass was re-run after the import move. Readers: 1310 passed. The construction file passes 4/4 on dev.

**Not done:**
- Item 3, bus_hazard: the stagger, the timed pause, the erase race and the FRAM tests are untouched; CMr1e's lever list still applies.
- Item 4, the formal pairs: mc_cov is still running.
- Item 5.
- No site classes.

**Runs:** 22 RUNNING lines named U35 lane CMr1f, 22 done lines. No process of mine is listed.

nothing of mine is running
