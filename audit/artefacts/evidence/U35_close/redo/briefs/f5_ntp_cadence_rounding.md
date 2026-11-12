# F5: the synced NTP cadence is due on the tick nearest its boundary (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Worktree `S/wt-u35f5`, branch `audit/u35-f5` at `d07c8537` (the integration
head: F2r's cadence change and F3r's unsynced-wait change are both in it); logs in `S/u35/laneR/f5/`. Sources: F3r's
hand-back `S/u35r/handbacks_redo/F3r.md` (Findings, first bullet) and LEAD NOTES 178. Re-check every fact yourself.

## The finding (F3r, the lead's reading; not yet proven)
`src/asy_ntp_client.py` `_refresh_loop()`, synced branch: `self._ntp_sec_count = self._cadence.read()` (a `TickSeconds`,
`src/asy_base_classes.py:336`: whole seconds, the millisecond remainder kept, so it reads the floor of the elapsed time),
then `due = self._ntp_sec_count >= ntp_interv[0] * 60 * 60`. The cadence restarts inside `if due:`, after the awaits of
that same tick, so a few milliseconds after the 10 s timer fired; the later fires keep the timer's own phase. The tick at
the boundary would then read one second short and the resync would run one tick (10 s) late, nearly every cycle. Before
U35 the cadence counted ticks (`+= _NTP_CHECK_INTERV`) and was due at exactly N ticks; the elapsed-time change was made so
a dropped tick delays nothing. F3r's unsynced wait already rounds a gap to the nearest check interval
(`max(_NTP_CHECK_INTERV, (gap + _NTP_CHECK_INTERV // 2) // _NTP_CHECK_INTERV * _NTP_CHECK_INTERV)`).

## What to do
1. Prove it first: a unit test (tests/test_asy_ntp_client.py, the file's own fake-clock style) in which the restart
   lands some milliseconds after a fire and later fires come on the timer's phase; it must show the resync one tick late
   on the current code at both GC stages. If it does not reproduce, stop and hand back what you measured.
2. The smallest fix that makes the boundary tick due while a dropped tick still delays nothing: compare elapsed time
   rounded to the nearest check interval, the same rounding as the unsynced wait (one shared expression or helper if
   that reads cleaner; Part G's catalog first). Keep every pinned behaviour: F2r's and F3r's tests, and the twin files
   test_digital_twin_ntp.py and test_digital_twin_clock_jump.py, all green. A comment of at most 3 lines with the tag
   "(agent, <date -u>)".
3. The stale rule just above (`self._sync_age.read() >= _NTP_ASYNC_INTERV * ...`) reads a floored `TickSeconds` too.
   Report, do not change: whether it has the same one-tick lateness, and since when (`git log -S` with
   `-- . ':!arduino'`); it is owner-reviewed (its comment says so).
4. SPECIFICATION.md wherever it states when the synced resync is due (grep the NTP cadence text, A.4 and Part N's
   NTP rows); `tests_scripts/test_counter_steps.py` must stay green with no new allow-list row.

## Proof and checks
Each new test red first, both stages, zero memory markers. tests/test_asy_ntp_client.py, the two twin NTP files and
every other importer of asy_ntp_client at both stages (TEST_DEVICE per device where the file needs it); ruff; the mypy
passes (stubs at `S/shared/typings` or `S/u35/laneR/f2r/typings`); the comment cap; the tests_scripts readers of the
changed files including test_counter_steps and test_tunables_register. Your base has F4a's `toolchain/`: run test files
with the shared binary directly; a tests_scripts file that starts a twin runner runs only with
`PICO_TOOLCHAIN_DIR=S/tc-int` (built for this base; never run its setup). No scripts/test.sh, no twin CI: the lead's
whole-tier run is using the machine, so keep CPU use modest.

## Not yours
Everything outside src/asy_ntp_client.py, its tests and the SPEC lines above, in particular asy_print_log.py,
asy_system_service.py, the FRAM files, toolchain/, audit/, and every allow-list. Commit subject `U35 lane F5: <summary>`,
the two trailers; do not push. Hand-back: the commit, the red and green with log paths, the stale-rule facts, the
effect per device and mode, anything that surprised you; last line "nothing of mine is running".
