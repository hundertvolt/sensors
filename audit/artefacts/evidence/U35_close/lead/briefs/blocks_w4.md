# U35 wave 4 blocks (lead, 2026-10-21)

Each block reads `S/u35/briefs/common_u35.md` first, then its own section here. About 60-80 tool calls each: count
them, and at 70 finish the step in hand, commit, and hand back the rest (CHECKLIST 21). CHECKLIST 22 (disk) is binding.
Lane C is split (LEAD NOTES 19): lanes F, Q and E branch from C2b's head `0547def`, each in its own worktree
(`S/wt-u35f`, `S/wt-u35q`, `S/wt-u35e`, rebuilt), and lane C continues there with the clock. A lane's last block runs
its complete checks (the common brief's "Before your lane's final").

## The driven clock's cancel hang (N1's finding; F1 root-causes it)
Under `DrivenTime(sleeps=True)`, start two driver tasks, give one yield, cancel both: both cancels finish and the scenario
returns, but `run()` never completes (idle until the 300 s file timeout, rc 124, 4.6 s CPU). The same scenario on the
real asyncio, or with `clock.elapse(0)` before the cancels, completes. Reproducer `S/u35/laneN/dbg/dbg_setup.py` (against
`dbg_real.py` and `dbg_settle.py`; run from the worktree with that folder first on MICROPYPATH); the hung run's log
`S/u35/laneN/head1_m1.log`. N1's unconfirmed lead: the external-cancel path at tests/_fake_time.py:162
(`runner.cancel()`), where the real `extmod/asyncio/funcs.py` cancels the awaited task instead. Until `<SHIMFIX>`, a
block that cancels tasks under the shim lets them start first and names each such site in its hand-back. Fixed by
`<SHIMFIX>` `1d77560` (LEAD NOTES 22): lanes N, Q, E and G start on it, and the workaround no longer applies there.

## N2 (lane N: the notification service on the driven clock)
Start: audit/u35-n at `2ed3946` in S/wt-u35n: N1's `32bb1eb` plus the lead's merges of `<PARTN>` `5f97080`
(SPECIFICATION.md only) and `<SHIMFIX>` `1d77560`. N1's hand-back `S/u35/handbacks/N1_final.md`. File this block:
tests/test_asy_notification_service.py.
- Steps 45-49 (P1's rows in lane_plan.md :64 and :153-156): `_make_coordinator` becomes `_make_service` (no `debug=`,
  calls `setup()`); `_one_cycle()` and every real sleep move to `DrivenTime(sleeps=True)`, each bound from the service's
  own rule with no margin (N1's `_ramp_ms()` form); 48 withdraws `l1.asy_notification_service_override_bound_ms` with its
  literal, the bound read through `src_int` (:1280); the tags at :35-42 and :152 are decided per literal (45's row).
- Seen failing first: every converted assertion bitten by a planted service in a scratch copy at both stages (N1's
  method, `S/u35/laneN/bites*.log`), including an extra-cycle plant that shows the bounds have no margin.
- Readers: import_placement, ticks_wrap_scan, tunables_register. After 48, tunables_register is red on exactly one row,
  `l1.bus_fault_isolation_bound_s` (Y2's tag, not in lane N); prove that is its only red.
- Runs: the file paired base/head at both stages (U31 19.0/19.1; over 10 s, so it must not grow, LEAD NOTES 4).
- Hand-back: steps by verdict; N3's start state.

## N3 (lane N: the integration files on the driven clock; N's last block)
Start: audit/u35-n at `66e496d` in S/wt-u35n (rebuilt; N2 changed no src/); N2's hand-back
`S/u35/handbacks/N2_final.md`. Files: the four tests/test_notification_*_integration.py files,
tests/test_neopixel_wifi_integration.py, tests/test_digital_twin_network_neopixel.py, tests/test_asy_neopixel_driver.py.
- Steps 86-90 and 99 (P1's rows in lane_plan.md): each real sleep that no assertion measures moves to the driven clock,
  each bound from the service's own rule with no margin; N2's `_driven()` and `_one_cycle()`
  (tests/test_asy_notification_service.py:50, :167) are the model. 86's `l1.asy_neopixel_driver_*` tag site is decided
  per literal (45's row). A wait whose real time is the subject stays, with a one-line reason.
- LEAD NOTES 22: N1's setup test (tests/test_asy_neopixel_driver.py:880-886 at `2ed3946`) moves to the driven clock,
  since `<SHIMFIX>` lifts the "let tasks start before a cancel" rule.
- Seen failing first: every converted assertion bitten by a planted service or driver in a scratch copy at both stages
  (N2's method), including a plant that shows the bounds have no margin.
- Runs: each file paired base/head at both stages, the twin file per device if it takes TEST_DEVICE.
- N's complete checks: the 17 scans and every reader of an N file. tunables_register's one known red
  (`l1.bus_fault_isolation_bound_s`, Y2's tag; it resolves at W6) stays the only red.
- Hand-back: steps by verdict; the wait table; the times; the checks.

## N4 (lane N: step 99's restarted-signal-task test; N's last block)
Start: audit/u35-n at `189d4e8` in S/wt-u35n (rebuilt; N3's `aa521ac` plus the lead's allow-list shrink); N3's
hand-back `S/u35/handbacks/N3_final.md`; LEAD NOTES 45. File: tests/test_digital_twin_network_neopixel.py.
- Step 99's A.U22.01 case (`python3 -I S/u35/tools/steps.py --standing 99`, its Change text):
  `test_a_restarted_signal_task_ends_dark_with_the_overlay_restored`. Boot the first generated device whose plan wires
  the NeoPixel (the C4 boot form the twin integration file uses); overlay on, a signal requested, the twin pixel's
  `raise_on_write` set mid-ramp so the signal task ends, then cleared; the supervisor restarts the task; the pixel's
  writes after the restart are black, then the overlay colour, and no frame of the old ramp colour follows; SYSTEM
  persisted exactly one task-end entry. Bounded by a condition wait on the pixel's writes, never a fixed sleep.
- Seen failing first on planted defects run from their own scratch directory (R1's finding): a restart that resumes the
  old ramp; a restart that leaves the overlay off; a task end that persists no entry.
- If the twin cannot boot a generated device from this file, state why at line level and stop that item.
- Runs: the file at both stages, paired against `189d4e8`; the test's added time. N's checks: the 12 commit checks, the
  17 scans and the file's readers.
- Hand-back: the test's verdict; the bites; the times; the checks.

## F1 (lane F: the hang; lane F's only block)
Start: audit/u35-f at `0547def` in S/wt-u35f. Files: tests/_fake_time.py, tests/test_driven_time.py.
- Root-cause the hang against the pinned asyncio source (`extmod/asyncio/` in the toolchain's MicroPython checkout under
  `/root/pico-toolchain`, read only), the mechanism stated at line level, shim and core.
- Seen failing first in tests/test_driven_time.py in a bounded form: the case fails by an assertion, never by the file's
  timeout. Fix it in the shim; C1's planted off-by-ones still bite the self-test. Relay `<SHIMFIX> <hash>` under `## C`.
- List every site on every lane branch with the root cause's shape (`git grep` on the `audit/u35-*` branches, read
  only), one line each with its branch; the lead routes them.
- Runs: every importer of `_fake_time` at both stages on the head (C2b counted 21); test_driven_time after-only.
- F's complete checks.
- Hand-back: the root cause and the fix; the site list; the runs.

## Q1 (lane Q: the UDP socket's cancel defect, the `_serve()` sweep, two D.15 orders)
Start: audit/u35-q at `1d77560` (`<SHIMFIX>`) in S/wt-u35q; C2b's hand-back `S/u35/handbacks/C2b_final.md`. Files:
src/asy_udp_socket.py, tests/test_asy_udp_socket.py, tests/test_asy_webserver_connections.py.
- 65's connect half. C2b found that a cancel during `_connect()`'s backoff `sleep_ms` (src/asy_udp_socket.py:73) skips the
  self-heal at :75-76, leaving `_sock` set with `connected` False, so every later `_connect()` skips setup until a
  `disconnect()`. Commit the half seen failing on the product first ("a socket left half set up"; C2b's two-half test and
  scratch fix are in `S/u35/laneC/bite_udp/fix/`). Then fix it: the self-heal moves into a `finally:` of that try. Check
  against the pinned asyncio that the await in that `finally` runs on a cancel.
- The `src/` edit: the mpy-cross compare of both stages' bytes (LEAD NOTES 7); test_twin_record goes red, expected. Effect
  per device and mode: latent on every device in every mode today, since every caller (the DNS and NTP clients'
  per-request sockets, the captive DNS server loop at src/asy_captive_dns.py:142) disconnects in its own `finally`; name
  it per mode (STA, AP, Silent, Off, USB).
- 67 (R-19): the sweep over `_serve()` in test_asy_webserver_connections.py, seen failing on a planted missing cleanup.
- D.15's module-level order for test_asy_webserver_connections.py and test_asy_udp_socket.py: its own commit, no content
  change, checked by line multiset (C2a's dns form).
- Runs: udp (C2b's head 5.97/5.95) and webserver_connections (1.41/1.44) paired base/head at both stages; every test file
  importing `asy_udp_socket` at both stages on the head.
- Hand-back: steps by verdict; the per-mode statement; Q2's start state.

## Q2 (lane Q: OF-211's audit, the wifi and captive sweeps; Q's last block)
Start: audit/u35-q at `5fba3da` in S/wt-u35q (rebuilt at `e50f813`; the later commits are test-only); Q1's hand-back
`S/u35/handbacks/Q1_final.md`. Files: tests/test_asy_wifi_service.py, tests/test_asy_captive_dns.py, and Q's
src/asy_udp_socket.py for the item below (LEAD NOTES 36).
- Q1's class-4 finding: `_connect()`'s self-heal drops `_disconnect_locked()`'s bool (src/asy_udp_socket.py:76 at
  `5fba3da`). Trace at line level what a False leaves behind (`_sock`, `poller`, `connected`) and whether the next
  `_connect()` recovers. If state is left that blocks recovery, or the failure reaches no caller, fix it in that file,
  seen failing first on a planted close failure, with the mpy-cross compare and the per-mode effect; if the caller
  already learns of the failure through `connected` False, state that path and change nothing.
- OF-211's fallback (blocks_w2.md's C2b item, unchanged): U27's held-responder audit (`S/u27/ci/repro/audit.sh`, extended
  to every `tests/` file that opens a socket, both stages) on your head; state the result and relay D2's E.1 rule as
  one line under `## D`.
- 71: a cancel sweep for the wifi service; 79: one for the captive DNS server (`_FakeUDPS` :408). Each seen failing on a
  planted missing cleanup.
- Runs: paired base/head at both stages: wifi (U31 24.4/24.7) and captive (U30 25.6/25.6), both over 10 s, so they must
  not grow (LEAD NOTES 4).
- Q's complete checks.
- Hand-back: steps by verdict; the audit's result.

## E1 (lane E: OF-81's pin, the FRAM driver's lock-busy bound, two interleaving gates)
Start: audit/u35-e at `1d77560` (`<SHIMFIX>`) in S/wt-u35e. Files: tests/test_asy_base_classes.py, tests/test_asy_fram_driver.py,
tests/test_asy_isl29125_driver.py, tests/test_asy_scd30_driver.py.
- OF-81 (R-11): a pin in test_asy_base_classes.py that `Lockable.__aexit__` swallowing `RuntimeError` on a double
  release stays visible to the sweep's lock-balance invariant; seen failing on a planted double release. No product change.
- 41: the lock-busy test (:1010-1048) runs on the driven clock: `advance(999)` not done, then `advance(1)` gives False;
  bitten by a bound 1 ms short.
- 52: isl :4046's `sleep(0)` becomes an Event gate; :4075's comment reads "# one yield lets configure() park on the held
  lock (a limit, not an interleaving claim)". 58: scd30 :2340's `sleep(0)` becomes an Event gate. Each gate seen failing
  on a planted unlocked path.
- Runs: paired base/head at both stages: base_classes (U31 0.9/0.5), fram_driver (base to measure), isl (U30 2.6/3.5),
  scd30 (U31 22.1/28.9; over 10 s, so it must not grow).
- Hand-back: steps by verdict; E2's start state.

## E2 (lane E: the BMP3xx interleaving; E's last block)
Start: audit/u35-e at `8fb6241` in S/wt-u35e (rebuilt; E1 changed no src/); E1's hand-back
`S/u35/handbacks/E1_final.md`. Files: tests/test_asy_bmp3xx_driver.py, and E's other files for the D.15 order.
- 39: the interleaving (:1410-1435) is reproduced, not only counted; the "can't be reproduced" comment (:1415-1417)
  goes. Seen failing on a planted unlocked read.
- Runs: bmp3xx paired base/head at both stages (U31 13.7/13.8; over 10 s).
- D.15's module-level order (LEAD NOTES 38) for base_classes, isl29125 and scd30 (and bmp3xx if out of order), each
  file its own commit, no content change, checked by line multiset and the top-level AST node multiset (Q1's form).
- Run test-file batches that start MicroPython one at a time against your timing runs, in `unshare -n S/u24/ns_xdg.sh`
  where they bind ports (CHECKLIST 12).
- E's complete checks.
- Hand-back: steps by verdict.

## C4 (lane C: the stale clock, owner question 7)
Start: audit/u35-c at `0547def` in S/wt-u35c. LEAD NOTES 11 is the spec (the owner's words, the question, the lead's
form). Files: src/asy_ntp_client.py, src/asy_sgp40_driver.py (its comment naming the callback), buildgen/codegen.py,
buildgen/definitions.py, mockdata/samples.json, tests/test_asy_ntp_client.py, tests_scripts/test_buildgen_generate.py,
tests_scripts/test_buildgen_definitions.py, tests_js/templates.test.js, tests_js/definitions-mockdata-coverage.test.js.
- `ntp_clock_valid()`: true from each successful sync until an NTP settings change (`ntp_force_sync()`); staleness, which
  clears only `Synced`, leaves it set. Seen failing first in test_asy_ntp_client.py on each of the three transitions.
- Codegen: `UTCTime` and `SgpBackup(<fram>, ...)` read it in place of `ntp_issynced`; SystemService's boot signature keeps
  `ntp_issynced`. `/status` `system` gains `TimeStale` after `UnixTime`: null until the clock was first set this boot,
  then true while `NTPSynced` is false, false while synced. Seen failing first in test_buildgen_generate.py.
- The website row: label "Time May Be Stale", readonly, a description saying when it is true and that the times shown
  may then have drifted; the mock data and both JS tests (npm runs in `unshare -n S/u24/ns_xdg.sh`).
- The `src/` edits: the mpy-cross compare (LEAD NOTES 7); test_twin_record goes red, expected. Effect per device (all
  six run the NTP client; the VOC backup on each SGP40) and per mode (AP and Silent turn stale 3 x `NTPInterval` after
  their last sync; name Off and USB).
- Relay `<CLOCK> <hash>` under `## C` once the src and codegen half is committed (Y4 and T4 wait on it), and one line under
  `## D` for D2's A.8 and F.1 sentences.
- Runs: test_asy_ntp_client.py paired base/head at both stages (U30 23.9/25.6; over 10 s); every test file that runs a
  generated module, at both stages on the head (grep `_generate_sensortask_modules` and `sensortask_`); the readers of
  your files (test_definitions_js_mirrors, the buildgen readers, grep's).
- Hand-back: steps by verdict; the per-mode statement; C5's start state.

## C5 (lane C: the NTP file's time, graph.py's comment, C's complete checks)
Start: audit/u35-c at `7442273` (C4's `8c2b458` plus the lead's merge of `<SHIMFIX>`) in S/wt-u35c; C4's hand-back
`S/u35/handbacks/C4_final.md`. Files: C's, plus buildgen/graph.py (LEAD NOTES 23).
- test_asy_ntp_client grew +2.6 s (+11 %) at C4 (23.53/23.61 to 26.14/26.27 at -1): fold
  `test_the_clock_stays_valid_when_the_sync_goes_stale` into `test_refresh_marks_the_sync_stale_three_intervals_after_the_last_success`
  (the same 1081-tick drive), every assertion kept; C4's bite on that transition still bites; re-time paired against
  `0547def` at both stages.
- buildgen/graph.py:65's comment names `ntp.ntp_issynced` alone; restate it for both checks the generated module now uses.
- C's complete checks over every file lane C changed since `feae592` (C1, C2a, C2b, C4, and this block), plus the D.15
  order of C's test files. tests/_sensortask_scenarios.py:2726-2728's red is V2's, not C's.
- Hand-back: the fold and its times; the checks.
