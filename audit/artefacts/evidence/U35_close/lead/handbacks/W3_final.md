W3 hand-back (lane W, block 3, the lane's last). Commit `7d6d255` on `audit/u35-w`, on top of W2's `0d33534`, in S/wt-u35w. Nothing is uncommitted, nothing of mine is running, and no typings link was made. About 70 tool calls.

**Steps by verdict**
- W2's red, applied: test_no_variant_literals failed on `'arzi'` at tests_js/live-backend-put-matrix.test.js:34-35. Each expected skip is now keyed by section, wired group and field, for example `sensors/BMP3XX/PresOvers option 1`, with no device name. A case runs on the first device that wires it (dedupe), and all 52 deduped ids are unique. Every skip is still checked; the head matrix had 6 skips and the hook passed.
- OF-144 wiring, applied: js/main.js and js/app.js now pass `pageBuildDate: buildDateOf(document)`. main.test.js and app.test.js are in no lane, so the test lives in shell.test.js. It drives each entry with the real shell; only `startShell`'s reload is swapped for a spy, through `vi.mock` with call-through.
- Checked map, applied: every action outside the sensors section, and each option of an enum action, is either probed or listed in `NOT_DRIVEN` with its reason. That is SystemCmd's reboot, bootloader, resetconfig and erasefram, plus `UartHazards`, so lane U's key is already listed when the lanes merge. A floor check: every probe must reach an action the definitions declare. A planted `PlantedCmd` is named. The matrix's module functions are now in D.15 order.
- `readStringSetConst`, applied: it moved to tests_js/_source_constants.js. Like its siblings, it now escapes the name and also reads an exported const. The compose result is unchanged (32/32).
- OF-214 seeding, stopped. Every matrix case runs in AP today; seeding an SSID would boot every case of the first device in STA. The twin runner also blanks DNSFallback itself (digital_twin/unixport/_offline_ntp_config.py:28, outside my set). Both skips stay listed, with the reason in the code comment.

**Seen failing first, and bites** (nothing planted was committed)
- Entries: both failed with "expected vi.fn() to be called 1 times, but got 0" before the wiring. I re-bit them after renaming the import; both failed again.
- Map: emptying `NOT_DRIVEN` failed, naming the 4 SystemCmd options.
- Floor: skipping the status section failed, naming `ResetErrors`.

**Effect per mode:** device behaviour is unchanged in STA, AP, Silent, Off and USB on every device. A page staged by build_firmware.py, which writes the build-date meta, reloads once when GET /system's BuildDate differs from it. Every other page (preview, the twin sites from build_device_websites.sh) has no stamp, so nothing changes there.

**Checks (all exit 0, zero memory markers)**
- Rebuild from a tree with build/generated_html and frozen_modules removed.
- Web tier: all 27 tests_js files, one per process, in the namespace. Put matrix: 350 passed, 6 skipped, 0 retried.
- `npm run lint`, `npm run typecheck`, lint-ceilings 4/4 (maxima unchanged).
- The 17 scans: 875 passed. The lane's 43 tests_scripts readers, one per process, which include readers.py's 29.
- The only skips in the readers: test_build_firmware's 6 opt-in slow builds, the same as at base.

**Times**
- Put matrix, one pair: 725.4 s at base, 727.2 s at head (+0.25 %).
- shell.test.js, 3 alternating pairs: 2.58-2.71 s → 3.07-3.16 s, mean +0.49 s (+18 %). That sits at the 0.5 s bar, and one pair was +0.55 s. Import time went from 2 % to 9 %: both entries' module graphs, plus W1's five tests. There is no cheaper way to drive both entries for real; the lead judges whether that is acceptable.

**Decisions (agent, 2026-10-22)**
- The entry test went into shell.test.js, with only the reload spied.
- `UartHazards` is listed now, so `NOT_DRIVEN` has no stale-entry check yet. One can be added once lane U merges.
- The skip ids drop the device name.
- The seeding item is stopped.
- The put-matrix pair ran in my tree, with base's test file as an untracked copy (deleted afterwards).
- `readStringSetConst` reads an exported const too.

**Scan (all classes)**
- A check that matched nothing is now floored (the probe-reach check).
- A failed `vi.mock` would throw before a real reload could run.
- The skip hook was seen working.
- The stale tree was rebuilt.
- The reload loop is unchanged.
- No new swallows.

**Facts owed**
- X: none.
- Y: none.
- Lead: tests_js/source-constants.test.js (no lane) has no case for `readStringSetConst`. Add a stale-row check for `NOT_DRIVEN` after the merge. tests_js/_put_field_cases.js:56 is still W6's item. No allow-list rows were orphaned.
- RUNS.md: one 8 s foreground pytest (test_build_firmware -rs, to read the skip reasons) got its line late.

**Logs:** S/u35/laneW/
- w3_entries_first.log, w3_entries_bite.log, w3_actions_bite.log, w3_floor_bite.log, w3_actions_after.log
- w3_checks*.log, w3_time_shell.txt
- w3_tier/ (summary.txt, gate.txt, per-file logs, base_put_matrix.log)