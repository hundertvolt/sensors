# U22 lane E: final report

**Branch and commits:** branch `audit/u22-e`, worktree `scratchpad/wt-u22e`, on the integration head `6d23c7d`. Two commits, not pushed:
- `14dc7cd` "U22 lane E: the Wi-Fi silent mode and the fresh-boot settings change in the docs" (the rows below);
- **`2d98110`** "U22 lane E: DEVICE_REFERENCE states the fresh-boot settings change for users" (FINAL; finding 3, written at the coordinator's request, see "Finding 3, written" below).

**Files:** the commit changes only these six files: `CLAUDE.md` (row 16 only), `BACKLOG.md`, `README.md`, `DEVICE_REFERENCE.md`, `tests_hardware/README.md` and `digital_twin/README.md`. Every fact below was checked against the code on this tree. Where a report or the packet said it differently, the difference is listed under Deviations.

## Step table

| row | M-id | status | note |
|---|---|---|---|
| 1 | M.DOCS.060 (1) | applied | `README.md:779`'s parenthesis now reads "the role reversal's stage-6 fallback". `:801`'s safety-fact list drops the deactivation item. The rest of the map is left for U36/U37. |
| 3 | M.HW_BENCH.110 (1) | applied | `tests_hardware/README.md:15-16` now reads "the role reversal's stage-6 fallback". The header rewrite and the carried A.U7.01 level wording are U36's: nothing at U22. |
| 11 | M.DOCS.027 (4) | applied | The overlay bullet (`DEVICE_REFERENCE.md:11-22`) now has the no-configuration clause ("until a reboot", "the no-configuration one included") and the silent-mode clause, with the owner quote and "Unplug and replug". Each clause was checked against `asy_wifi_service.py`: pattern constants 0.1/2.9 and 2.9/0.1 s, the dark guards, `_on_sta_connected()`, the `_PHASE_DEACTIVATED` comment "until a reboot". Parts (1)-(3) and the full rewrite are U18/U36. |
| 15 | M.DOCS.110 | applied | The networking-status sentence (`DEVICE_REFERENCE.md:42-45`) now uses the packet's text. "Quiet attempts leave theirs" was checked: `_poll_sta_connect_status()` persists a verdict warning on every attempt, the silent attempts included. |
| 16 | M.DOCS.111 | applied | `CLAUDE.md:334-337` now reads "stage-6 fallback (a failed credential reopens the DUT's hotspot once, then its silent mode)". The rest of the bullet is word for word; only its last two lines are rewrapped. The commit names this as the one meaning change (A-27; wording below). |
| 19 | M.HW_BENCH.124 (1) | applied | `tests_hardware/README.md:746-762`: the "What a failed stage-6 credential does" item replaces the deactivation-risk item. It carries A-20's clause naming (a), (b), their markers, (b)'s gate and a candidate invocation (detail below the table). `:1037` now reads "specifically to stay off that scenario's hotspot fallback". |
| 49 | M.TWIN.058 (1) | applied, with deviation 2 | The knob sentence follows the `network.py` bullet's `ifconfig()` sentence (`digital_twin/README.md:128-132`). Carried A.SDEP.08, A.U0.31, A.U14.28 and A.U7.01: nothing at U22. Plan §6 has them landed or staged for U25/U36. |
| X2 | M.DOCS.066, U22 stage | applied | BACKLOG's chroot list gains "**2026-10-12, `pyproject.toml` lint and type config only, no build impact**" before "Kept here as the running list …" (`BACKLOG.md:666-671`). It names the six modules and was checked against `git diff 65088de -- pyproject.toml`. |
| X5 | (A-20) | applied | One row in "Real-hardware work still owed" (`BACKLOG.md:366-379`) for the two stage-6 cases. It says to read and save `errcount` first (CLAUDE.md's FRAM rule; the module itself clears the logs in stages 3-5, at `test_hotspot_role_reversal.py:319, :394, :419, :433`). It gives each case's duration, what it asserts, the wear ((a) one owned write, (b) none), the gate, and the twin row `tests/test_digital_twin_wifi_modes.py`. |
| ruling 7 | twin test file listing | applied | The brief asked for the new file wherever my docs list the twin test files. The only listing-like site is `digital_twin/README.md`'s in-process tier paragraph. It gains one paragraph on `tests/test_digital_twin_wifi_modes.py` (`:254-257`). Everywhere else my docs use the `tests/test_digital_twin_*.py` glob, which already covers the file. |
| finding 3 | (lead, 2026-10-12, accepted as a U22 part) | applied in `2d98110` | `DEVICE_REFERENCE.md:47-51`, the networking-status section's new paragraph on the fresh-boot settings change for users (detail below). |

None of my rows' parts was already in its end form on this tree.

**Row 19 in full.** The new item names:
- `test_a_wrong_password_over_the_hotspot_reopens_the_hotspot`: `persistence_write`, one owned flash write, restored by the real-credentials test.
- `test_a_second_failed_streak_goes_silent_and_links_on_a_later_attempt`: about 20 min on `dev`, writes nothing. `persistence_write` is only its AND-gate and `long_soak` gates its length, so it needs the whole module with `--soak-tier` and `--allow-persistence-writes`.
- Why neither runner fits as is: the bench runner excludes `long_soak` (`scripts/run_bench_hardware_suite.sh`'s `floor`). The soak runner's own `-m long_soak`, given `--allow-persistence-writes`, selects (b) without its precondition, so (b) fails at its precondition check.
- The candidate invocation, marked "not yet run on hardware": `scripts/run_bench_soak_tests.sh --tier short --allow-persistence-writes -m role_reversal` (pytest takes the last `-m`).
- Both cases compare WIFI's history before and after and never clear it.

This is what the bench test's own comment points at ("tests_hardware/README.md names the invocation").

## Commit wording for the CLAUDE.md meaning change (A-27)

The commit message, verbatim (`14dc7cd`):

```
CLAUDE.md carries the one meaning change, following the owner's requirements
of 2026-10-08: the real-hardware go-ahead rule's safety facts name the hotspot
role-reversal scenario's stage-6 fallback (a failed credential reopens the
DUT's hotspot once, then its silent mode) in place of its stage-6
permanent-WLAN-deactivation risk. The rest of that bullet is word for word.

The owner's words, 2026-10-08. On the second failed STA streak after a hotspot
phase, which switched Wi-Fi off: "Don't permanently switch WiFi off, only stop
retrying to connect." ... "The WiFi LED stays dark, even if it is activated,
being completely silent in that mode. It should look like turned off." ...
"Entering the hotspot mode only through a reboot, as is." Told that WLAN.scan()
holds the VM past the watchdog, so the availability check is one silent
connect attempt every hotspot_time_min: "a, go ahead and add it to all layers
and tiers affected, ...". On a settings change, told that it reset neither the
failure streak nor the hotspot-used-once state (question paraphrased): "Point
1: Unify it. Simplify it. Any change of credentials, no matter from which
side, lands in the same mode as "initial connection attempt after a fresh
boot". All further steps follow normally. This means one operation flow
covering all needs."

Every other edit makes no meaning change beyond those two requirements:
```

That line is followed by one bullet per file. The full message is saved at `scratchpad/u22e_runs/commit_msg.txt` for the lead's squash. It now also carries a bullet for `2d98110`'s edit (DEVICE_REFERENCE.md, second commit), whose own message is in `scratchpad/u22e_runs/commit_msg_f3.txt`.

## Finding 3, written (`2d98110`)

The coordinator asked for finding 3 as a U22 part: U22 introduced the behaviour and the user doc holds current state (agent, 2026-10-12, for owner review). `DEVICE_REFERENCE.md`'s networking-status section gains one paragraph (`:47-51`), after the row-15 paragraph:

> Saving a changed `SSID`, `PW`, `Country`, `Hostname` or `HotspotPW` (`/networking`) restarts the Wi-Fi connection as a fresh boot does: a fresh series of connection attempts, with the fallback hotspot available once more (owner, 2026-10-08, paraphrase). A wrong password therefore brings the hotspot back after its failed connection streak, even when the hotspot has run before, so the unit stays reachable for a correction.

Checked against the code on this tree:
- **The trigger.** `buildgen/validate.py`'s `SETTINGS_GROUPS` gives the hook `post_fct=conn.reconnect_wifi` only to the identity group: `SSID`, `PW`, `Country`, `Hostname`, `HotspotPW`. `LEDWifiOn`'s own group has no hook. `tests/_sensortask_scenarios.py`'s `webserver_networking_put_ssid_group_reconnects_but_led_group_alone_does_not` pins both on every device: `LEDWifiOn` alone gives `(_reconn_wifi, _reconnect_fresh) == (False, False)`, and `Hostname` gives `(True, True)`.
- **When the hook runs.** `asy_api_response.handle_set_cmd()` runs it once, and only if a field was saved as changed (`VALID`). An unchanged or refused value restarts nothing, hence "a changed".
- **What it sets and resets.** `reconnect_wifi()` calls `_on_hotspot_window_end()` (timer deinit, flash cancel, `_reconn_wifi = True`), then sets `_reconnect_fresh = True`. The loop's next `_handle_reconnect_trigger()` takes the flag and resets `_connection_failures = 0` and `_hotspot_started_once = False`, then seeks STA (leaving the hotspot first if it was up). So "a fresh series of connection attempts" and "the hotspot available once more" are the code's two resets, and the hotspot reopens after the streak even when it ran before.
- **Scope of the word "password".** A wrong password here means a well-formed one: 8-63 characters is `_VAL_PW`'s bound. A shorter one is refused and triggers nothing.
- **Tag.** "(owner, 2026-10-08, paraphrase)", the same form as the tests_hardware item. No audit ID; Markdown wrap at 100.

Checks before the commit, one at a time at `nice -n 19` (logs `u22e_runs/f3_*.log`): `test_decision_vocabulary.py` 6 passed (10 s), `test_citations.py` 15 passed (10 s), `test_comment_block_cap.py` 453 passed (5 s). The run is entered in `u21/RUNS.md` and marked done; it has exited.

Findings 1, 2, 4, 5 and 6 are left as they are; the coordinator records them as open findings for U25, U26 and U36.

## Deviations (each conservative and reversible; decided on the owner's behalf, agent, 2026-10-12)

1. **"paraphrase" added to two tags.**
   - What: the tests_hardware item and the BACKLOG row tag the fresh-boot sentence "(owner, 2026-10-08, paraphrase)". The packet and plan give "(owner, 2026-10-08)".
   - Why: CLAUDE.md's decision-records rule (2) says a paraphrase is marked "paraphrase". "A credentials change lands in the fresh-boot state" paraphrases the owner's "Any change of credentials, no matter from which side, lands in the same mode as …". T's bench comment uses the same form.
   - Not changed: DEVICE_REFERENCE's tag quotes the owner's words exactly, so it has no marker.
   - The lead may strip the marker if the plan's bare form is wanted. W's `src/` comments use the bare form.
2. **Knob call form.** The packet writes `set_access_point_up(False)`. On this tree the knob is keyword-only, `set_access_point_up(*, up: bool)` (`digital_twin/network.py:44`; T's deviation 1), so the README says `set_access_point_up(up=False)`.
   - It also writes "a `WLAN` object's `stations_chip_down`", because the attribute is per object (`:83`).
   - It says "32 unfilled entries", because the knob returns `(bytes(6),)` × 32 (`:166`).
3. **Row 19's (b) duration.** I wrote "about 20 min on `dev`" from T's facts and my own check of the derivation:
   - `_streak_bound_s()` = 5 + 5 + 4 + 3 + 5 × (5 + 5) + 4 + 30 = 101 s;
   - the window is 8 min, and a second window or less passes before the relink.

   This is an estimate, not a measurement; nothing ran on hardware. (a)'s "about 3-4 min" in X5 is T's estimate.
4. **README `:801`.** Dropping the item leaves one short line ("gates, `BENCH_AP_PASSWORD` handling) were already"). I did not reflow the rest of that provenance paragraph, which U36 deletes. `tests_hardware/README.md:1038` likewise keeps one short line.
5. **One added paragraph not named in the packet.** The `digital_twin/README.md` paragraph on `tests/test_digital_twin_wifi_modes.py` is not in the packet. It comes from the brief's ruling-7 instruction and T's E facts.
6. **No "R3" in X5.** The plan's X5 text names "R3", a phase-C round label. Permanent text does not carry it, so the BACKLOG row leaves it out.

## Files outside my set

None edited. None needed for my rows.

## Facts owed (plan §3)

- **D:** I add, rename or withdraw no `@tunable` tag. No API end state is mine. The only doc fact for D is the D-relevant part of finding 4 below: M.DOCS.027 (3)'s U36 sentence says `/measurements`, but `State` is published on `/status`.
- **Lead:**
  - Allow-list lines: none added, retired or re-keyed. My edited sentences match no row in `_decision_vocab_allowlist.txt` or `_citation_allowlist.txt`, and both checks pass on this tree.
  - Any-baseline: none. New raises: none. Catalog: none. Website inputs: none.
- **E facts consumed:**
  - From T: the knob names, the bench names, markers, gate, durations and invocation, and the new twin file.
  - From W: the console texts (not needed: no doc of mine quotes them).
  - From P: the X2 text, and `State` on `/status`. No doc of mine lists the `/status` notification keys, so P's "wherever the `/status` keys are listed" has no site at U22.

## Tests run

This is a docs lane, so no MicroPython file, toolchain command or `scripts/test.sh` was run, and GC stages do not apply. The runs were the pre-commit pytest files, one at a time, at `nice -n 19`, on the final edits before the commit. Logs are in `scratchpad/u22e_runs/`.

| file | result | wall |
|---|---|---|
| `test_decision_vocabulary.py` | 6 passed | 10 s |
| `test_citations.py` | 15 passed | 10 s |
| `test_comment_block_cap.py` | 453 passed | 5 s |
| `test_tunables_register.py` | **1 failed**, 14 passed (expected red, D's Part N rows; lines below) | 5 s |
| `test_legacy_paths.py` | 3 passed | 2 s |
| `test_import_placement.py` | 7 passed | 8 s |
| `test_code_conventions.py` | 23 passed | 4 s |
| `test_error_catalog.py` | 33 passed | 29 s |
| `test_host_annotations.py` | 12 passed | 2 s |
| `test_lint_ceilings.py` | 19 passed | 12 s |
| `test_mypy_any_baseline.py` | 7 passed | 0 s |
| `test_memory_error_gate_agreement.py` | 13 passed | 5 s |

`test_tunables_register.py`'s exact failing lines. All are tags another lane added that wait for D's Part N rows; none is from my files:

```
src/asy_neopixel_driver.py:38: led.overlay_refresh_ms is tagged but has no SPECIFICATION.md Part N row
src/asy_notification_service.py:68: notify.sample_max_age_s is tagged but has no SPECIFICATION.md Part N row
tests/_sensortask_scenarios.py:2374: l1.sensortask_notify_cycle_rounds is tagged but has no SPECIFICATION.md Part N row
tests/test_digital_twin_wifi_modes.py:45: l2.wifi_modes_wait_poll_s is tagged but has no SPECIFICATION.md Part N row
tests/test_digital_twin_wifi_modes.py:47: l2.wifi_modes_wait_timeout_s is tagged but has no SPECIFICATION.md Part N row
tests/test_digital_twin_wifi_modes.py:49: l2.wifi_modes_run_bound_s is tagged but has no SPECIFICATION.md Part N row
tests_hardware/bench/test_hotspot_role_reversal.py:69: l4.hotspot_role_reversal_derived_wait_margin_s is tagged but has no SPECIFICATION.md Part N row
```

**Other checks:**
- ruff and mypy: I touched no `.py` file, so there is nothing to run them on and no typings link was made.
- No other `tests_scripts/` file reads my six docs; their only mentions are comments. `test_readme_reference.py` does not exist yet (M.DOCS.060's later stage).
- No test file was grown, so there are no before/after wall times. There was no behaviour change and so no test to see failing first.

**Runs:** two foreground batches, each entered in `u21/RUNS.md` (rows "lane E (fg) | wt-u22e") and marked done: the 12 files above in sequence, and the three doc checks before `2d98110`. Every run has exited; `ps` shows no pytest, mypy or ruff process of mine.

**Files the lead must run on the merged tree:**
- `test_citations.py` and `test_decision_vocabulary.py`, since D's SPEC edits land beside mine;
- `test_tunables_register.py`, after D's rows;
- `test_comment_block_cap.py`.

## Findings (out of my rows; not fixed)

1. **`tests_hardware/README.md:802-803`** (class: stale doc; owner U26/U36).
   - The text says the `dut_ip` fixture watches `self.pr.one("Permanently no WLAN connection - activating hotspot!")`, "both gated on `DebugLevel >= 3`".
   - Since U18 (`f1f800e`) that line is `pr.wrn_s(...)`, printed at `_LOG_WARN` (2) (`src/asy_print_log.py:239-242`). The `:1245` mention is the same.
   - This was not made false by U22, so it is left as it is.
2. **`digital_twin/README.md:121-123`** (stale before U22; M.TWIN.058's U36 text, A.U25.26).
   - The text says `WLAN.connect()` "transitions to a successful, connected state immediately". The twin connects after `_CONNECT_DELAY_S` (0.7 s), and now ends in `STAT_NO_AP_FOUND` while the AP switch is down.
   - The "AP-mode fidelity gap" sentence (`:132-134`) names only the address. It does not mention that the twin AP never reports `STAT_GOT_IP`, which is what A-7's test-local poke works around (T's scan #6; A.U25.72 retires it at U25).
3. **`DEVICE_REFERENCE.md`** (class 7, mode: a settings change in each Wi-Fi mode; **new**). **Written in `2d98110`** at the coordinator's request; the text below is the finding as first reported.
   - No user-facing sentence says that a credentials change lands in the fresh-boot state: a wrong new password gets the hotspot once more after its streak, so the user is not locked out. That is the owner's point in their 2026-10-08 requirement.
   - Only `tests_hardware/README.md` (bench view) and SPEC (lane D) state it. No U22 step owns a DEVICE_REFERENCE sentence on it.
   - Proposed: one sentence in U36's M.DOCS.027 rewrite (or a new delta), e.g. "Saving new Wi-Fi settings restarts the connection as a fresh boot does: if they fail, the hotspot opens once more."
4. **M.DOCS.027 (3)'s U36 sentence** reads "`/measurements`' notification `State` …". Per A-8 and P's X3/F4, `State` is published on `/status`'s `notification` block. The U36 executor should write `/status`.
5. **The no-configuration state and `LEDWifiOn`** (class 4/7, mode: unreadable configuration; inherently consistent, a wording note for U36).
   - In that state `LEDWifiOn` sits at its schema default (on), and the store refuses every write until the next boot (`asy_config_manager.py:582-586`; W's A-4 regression).
   - So the overlay bullet's "follows `LEDWifiOn` … shown as soon as it is switched on" holds, but the user cannot switch it there.
   - U36 could say "with `LEDWifiOn` at its default".
6. **`tests_hardware/README.md`'s `BENCH_AP_PASSWORD` paragraph (`:254-265`)** names only the real-credentials test as the variable's reader. Case (a) now also reads it, to derive its wrong password. This is not false; noted for U26's pass over that section.

## Silent-failure scan (my six files; both passes; doc-level)

I read each mode as a scenario and asked two things: what the docs tell an operator or a bench session, and whether that matches the code on this tree.

**Wi-Fi modes:**
- **STA seeking:** toggle every 0.5 s, `_poll_sta_connect_status()`. Consistent.
- **STA established:** on; a lost link retries after 60 s. Consistent.
- **Hotspot without a client:** 2.9/0.1 s. Consistent.
- **Hotspot with a client:** 1.5/1.5 s, held while the client stays. Consistent.
- **Silent mode:**
  - Entry: W80, one slot. Each period: one dark attempt per `hotspot_time_min`. A failed attempt leaves its verdict warning. A linking attempt is a normal connection and lights the LED. All consistent: rows 11 and 15.
  - Recovery is documented ("Unplug and replug").
  - Class 7: `/status` cannot tell silent from seeking. This is inherently safe, since no client reaches a silent unit, and after the link the WIFI history shows the change (row 15's sentence; W's finding 7).
  - A dropped fire or a failed arm is persisted (E17) and visible in `errcount`. Covered by W's L1 tests; no doc finding.
- **Unreadable configuration:** pattern 0.1/2.9 s "until a reboot". Consistent; see finding 5.
- **A task restart in each mode:** not user-visible beyond the LED, which the restart keeps. Inherently safe.
- **A settings change in each mode:** the bench docs state it (row 19). The user doc did not: finding 3, **new**, now closed by `2d98110`'s paragraph.

**The LED:**
- Enabled and disabled, and each pattern: consistent.
- The overlay against a notification flash: DEVICE_REFERENCE says a flash overrides the overlay. During the silent mode, notification flashes still light the pixel. That is A-5's reading, covered by the owner-review row `REGISTER.md:583`.
- The overlay refresh: U36's (2) sentence, not false at U22.

**Bench (b):**
- A missing precondition fails visibly; the README says so.
- The invocation is marked "not yet run on hardware".
- T's scan #2 (the `ap_down()` tolerance) and #3 (the flip-back drop after (b)) are U26's.

**FRAM-backed logs:** X5 says to read and save them first, because the module clears them in stages 3-5. Covered.

**The `dut_ip` fixture's "Permanently no WLAN connection" match** (`tests_hardware/conftest.py:265`) no longer matches the silent entry's text. It is inherently safe: the fixture watches only 60 s after a reset, and silent needs a full 8 min window first.
