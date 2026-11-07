DR7 decision review, written by the part (Wed Oct 28 11:50:36 UTC 2026)

# DR7: SPECIFICATION.md Part N (Tunable Parameters) at `11b66cd8`

**Scope.** The values and rules agents chose in Part N of `inputs/SPEC_11b66cd8.md`: the N.1 rules (SPEC:11929), the N.2
tag grammar and check (SPEC:11974), the N.3 register tables (SPEC:12012-13341: 1,284 rows) and the N.4 rule rows
(SPEC:13342 on: 10 rows). Firmware, build and N.4 rows get one verdict each; the test-tier, CI and runner rows get one
verdict per family, with single rows called out. The scheme (N.1, N.2) is split into 13 items, `N1-a` to `N2-e`.

**Method.**
- Static only.
- The rows were parsed from the input file. Each N.3 basis commit was resolved in the repo.
  - The clone is shallow (boundary 2026-09-09). A basis hash that does not resolve is older than the audit start
    `25caf528`; the resolving ones carry their own dates.
  - Pre-audit values were confirmed with `git show 25caf528:<path>` where it mattered.
- Test-tier sites were read from `git archive 11b66cd8`. A scan of every tagged constant used as a sleep followed by an
  assertion found 29 candidate rows; seven of them were confirmed as positive sleep-then-assert by reading the source.
- Owner words come from the plan's OR rows at `11b66cd8`, `recovered/owner_rulings_after_LN118.md`, `inputs/answers.json`
  with `inputs/DR1_review_decisions.tsv`, `S/CHECKLIST.md`, and the owner quotes in the lead's notes (`S/u35/lane_plan.md`).

**Per-row file.** Every row's verdict, family and topic are in
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35r/decrev/dr7work/DR7_rows.tsv`
(1,294 rows, id `SPEC:<line>`), for the crosswalk.

## 1. Counts

**Decisions:** 1,273. That is 1,260 register rows plus 13 scheme items. **Facts:** 34 rows, given no verdict:
- 27 legacy values carried unchanged;
- 4 datasheet values (`i2c.clear_half_period_us`, `spi.cs_settle_us`, `uart.flash_hold_max_ms` as a datasheet trace,
  and `isl29125.cal_converge_tol`, a single measurement);
- 3 measured quantities (`uart.gc_pause_worst_ms`, `mem.max_await_depth`, `web.connections_per_page_load`).

| verdict | count |
|---|---|
| SAME | 1,183 |
| OWN | 35 |
| FORM | 23 |
| DIFF | 14 |
| OBS | 12 |
| CHECK | 6 |
| SUP | 0 |

**Per area** (rows; the scheme items are a row of their own):

| area | SAME | FORM | DIFF | OBS | OWN | CHECK | fact | total |
|---|---|---|---|---|---|---|---|---|
| Firmware | 64 | 1 |  | 7 | 19 | 2 | 32 | 125 |
| Build | 26 |  |  |  | 3 |  |  | 29 |
| L0 | 50 |  |  |  | 1 |  | 1 | 52 |
| L1 | 245 | 19 | 5 | 2 | 1 |  |  | 272 |
| L2 | 219 |  | 3 | 1 |  |  | 1 | 224 |
| L3/L4 | 542 |  |  |  | 2 | 4 |  | 548 |
| CI | 19 |  | 2 |  |  |  |  | 21 |
| Runners | 10 |  | 1 | 1 | 1 |  |  | 13 |
| N.4 rule rows | 6 | 1 |  | 1 | 2 |  |  | 10 |
| N.1/N.2 scheme | 2 | 2 | 3 |  | 6 |  |  | 13 |

**Per topic:**

| topic | SAME | FORM | DIFF | OBS | OWN | CHECK | fact | total |
|---|---|---|---|---|---|---|---|---|
| bus-i2c-spi | 5 | 1 |  | 1 |  |  | 2 | 9 |
| ci-tooling | 39 |  | 3 | 1 | 3 |  |  | 46 |
| docs-records | 2 | 2 | 3 |  | 6 |  |  | 13 |
| driver-bmp3xx | 4 |  |  |  |  |  |  | 4 |
| driver-isl29125 | 10 |  |  |  |  |  | 1 | 11 |
| driver-scd30 | 1 |  |  | 1 | 1 |  | 2 | 5 |
| driver-sgp40 | 2 |  |  | 1 | 2 |  | 2 | 7 |
| led-notification | 5 |  |  | 2 |  |  | 2 | 9 |
| memory-gc | 1 |  |  |  | 1 |  |  | 2 |
| ntp-dns | 10 |  |  |  | 2 |  | 7 | 19 |
| storage-fram | 1 |  |  |  |  | 2 |  | 3 |
| supervisor-reset-watchdog | 8 | 1 |  | 1 | 1 |  | 1 | 12 |
| tests-hardware | 542 |  |  |  | 2 | 4 |  | 548 |
| tests-unit | 295 | 19 | 5 | 2 | 2 |  | 1 | 324 |
| timing-waits | 2 |  |  |  | 1 |  |  | 3 |
| twin | 219 |  | 3 | 1 |  |  | 1 | 224 |
| uart | 24 |  |  |  | 1 |  | 2 | 27 |
| webserver-rest | 12 |  |  | 2 | 4 |  |  | 18 |
| website | 1 |  |  |  | 4 |  |  | 5 |
| wifi |  |  |  |  | 5 |  | 13 | 18 |

**Test-tier families** (L0-L4, CI and runners: 1,130 rows). Families are assigned by name and role (rules in
`dr7work/classify.py`). Their verdicts are on the value; whether a row stays in the register is decided by scheme items
N1-b and N1-f (section 2).

| family | what it holds | rows (L0/L1/L2/L3-4) | verdicts |
|---|---|---|---|
| A | hang backstops: a bound that only ends a hung test, step, script or process | 221 (13/56/40/112) | SAME 220, OBS 1 |
| B | poll steps and their try counts (step × tries is one deadline) | 171 (3/41/39/88) | SAME 171 |
| C | condition waits and per-step timeouts inside a test | 116 (17/13/10/76) | SAME 115, OWN 1 |
| D | inputs and stimuli handed to the code under test, a fake or a client | 80 (0/43/22/15) | SAME 80 |
| E | fixed waits: settles, reaches, parks, quiet windows, margins, tails | 273 (11/67/63/132) | SAME 261, DIFF 7, CHECK 4, OBS 1 |
| F | real-time assertions on product timing (bands, maxima, minima) | 33 (0/19/1/13) | FORM 19 (L1), SAME 14 |
| G | load, soak and sweep sizes and durations | 123 (2/17/39/65) | SAME 120, OBS 1, OWN 1, fact 1 |
| H | discriminating thresholds: heap and leak budgets, tolerances, ratios, floors | 67 (5/14/9/39) | SAME 64, DIFF 1, OWN 1, fact 1 |
| R | retry and attempt counts | 12 (1/2/1/8) | SAME 11, OWN 1 |
| CI | job budgets and the apt mirror check | 21 | SAME 19, DIFF 2 |
| RUN | runner budgets and host-speed bands | 13 | SAME 10, DIFF 1, OBS 1, OWN 1 |

## 2. DIFF rows

### N1-b — the register's scope covers every tuned literal inside every test (SPEC:11921, SPEC:11936)
- **As taken.** Every test tier's sleeps, poll steps, reach waits, fake inputs and per-test bounds became tuned values,
  each with a tag and a row. This was the test-tier classification pass after U8 (2,265 hits) and the tagging lanes
  that followed it.
  - SPEC:11921 credits this scope to "(owner, 2026-09-25, paraphrase)".
- **New answer.** The register lists the values OR30 describes, plus the firmware and build values:
  - suite-level budgets: CI minutes, per-file timeouts and retries, `-X heapsize`;
  - twin run and soak sizes;
  - hardware-tier budgets;
  - discriminating thresholds.

  These are families G, H, R, F, CI and RUN, about 270 rows. The values inside a test file (families A-E, about 860
  rows) stay in the test as named constants, with no tag and no row.
- **Basis.**
  - OR30's own qualifier: "many tunable parameters which are substantial for correct functioning, but may be subject to
    change - for example, runtime and timeout parameters for test suites - essential for clear test result
    discrimination, but prone to changes on updates". A 10 ms poll step or a 5 ms reach sleep in a unit test is none of
    these.
  - OR30.a (1), answered "yes to all three", names the suite-level set only: "CI `timeout-minutes` ...; per-file
    timeouts and retries; Unix-port `-X heapsize`; twin run and soak durations; hardware-tier budgets".
  - The owner, 2026-10-28: "The unit tests shall have good quality, but don't need deep dives. The audit verification
    machinery is just a temporary tool."
  - REPORT.md section 9 lists "the `@tunable` tagging (1,249 tags, from 0)" among the runaway areas. F.md section 5
    item 1 records 562 KB, 47 % of all doc growth, and 1,127 of the 1,284 rows being test, CI or runner values.
- **Topic, line.** docs-records; L4 (misfit) and L7: an agent paraphrase is credited to the owner.
- **What changes.**
  - About 860 Part N rows and their `@tunable` lines leave the test files. The constants themselves stay.
  - `test_tunables_register.py` stops scanning test-internal constants.
  - Part N shrinks by roughly 400 KB.
  - No test behaviour changes.

### N1-f — every test budget is sized against the measured worst case on the slowest host (SPEC:11960-11963)
- **As taken.** "A test budget is sized so host load cannot fail a healthy test: its Margin is stated against the
  measured worst case on the slowest host that runs it". In practice every estimated test row carries a measurement
  obligation: 951 test-tier rows read "measurement owed" (F.md).
- **New answer.**
  - Keep the principle: host load must not fail a healthy test.
  - Drop the per-value measurement obligation for test values.
  - A test budget is re-measured only when it fails or is tightened. "No timeout is tightened without a measurement"
    (OR39.a (3)) stays.
- **Basis.**
  - REPORT.md "What went wrong", item 3: "Rules written for the firmware (bite every test, cover every cell, measure
    every tunable) were applied to the test machinery and the audit records as well, so the effort multiplied". The
    owner agreed: "I agree with wour conclusions about scope and effort." (REPORT.md header of that section, 2026-10-28.)
  - DRIFT.md rule 4, "Tiered rigor".
- **Topic, line.** docs-records; L4 (misfit).
- **What changes.**
  - About 950 "measurement owed" cells go.
  - The test-tier measuring that ran slowest-of at both GC stages under load is not repeated.

### N2-b2 — the check counts tags per file, so a deleted second tag of one ID fails (SPEC:11993, SPEC:12005-12010)
- **As taken.** The Sites cell states `(n tags)` and the check compares the counts. This was the agent's decision of
  2026-10-26 closing OF-16. The lead decided it under CHECKLIST 1d, the owner's 2026-10-26 delegation: "That's actually
  a combination you don't need to ask me for."
- **New answer.** Return to OR30.a (2)'s three conditions: "fails when a tagged value is unlisted, a listed value is
  untagged, or the listed number differs from the code". The count and the `(n tags)` notation go, and OF-16 stays a
  documented blind spot.
- **Basis.**
  - F.md section 5 item 1: "`test_tunables_register.py` needs every Sites cell to list exactly its files and tag counts,
    so every test edit reopens the register".
  - The blind spot changes no number. The other tag of the same literal in the same file still carries it.
  - The owner, 2026-10-28, quoted under N1-b: the verification machinery is temporary.
  - REG:243 (in the DR2 set) had called this extension "the owner's to accept".
- **Topic, line.** docs-records; L4.
- **What changes.** About 15-25 lines in the check, and the count notation in the Sites cells that carry it.

### SPEC:12741 `l2.zero_think_reader_floor` = 10
- **As taken.** In the twin scenario `reader_saturation`, each of four zero-think-time `/status` readers must be answered
  at least 10 of its 20 times (agent, 2026-10-22).
- **New answer.** No per-reader floor. The scenario stays the degradation check OR72.a (1) kept: no crash, reboot, task
  end or memory marker, and full recovery once the load stops.
- **Basis.**
  - The owner on this test (OR72, 2026-09-26): "1. Not sure. Only okay if it ever has a realistic chance to pass. Very
    hypothetical test."
  - OR72.a (1) kept it "as an OR49.a degradation check only", calling four zero-think readers "a hypothetical client".
  - The floor, added four weeks later, makes it a starvation check again.
- **Topic, line.** twin; L2 (misfit), L4.
- **What changes.** One assertion and its row. `l2.zero_think_reads_per_reader` (SPEC:12740) stays as the load size.

### Seven positive sleep-then-assert waits (family E1)
- **The rows.** SPEC:12266 `l1.asy_webserver_service_admit_settle_s`, SPEC:12370 `l1.asy_uart_comm_inside_lock_ms`,
  SPEC:12342 `l1.uart_comm_hazard_in_flight_ms`, SPEC:12321 `l1.captive_dns_bind_wait_ms`, SPEC:12412
  `l1.asy_ntp_client_reply_process_s`, SPEC:12649 `l2.run_generic_integration_reach_ms`, SPEC:12657
  `l2.run_generic_integration_slot_reach_ms`.
- **As taken.** A fixed real-time sleep "to let" another task reach a point, then an assertion that it did. Anchors:
  - `test_asy_webserver_service.py:2204-2205`: `sleep(_ADMIT_SETTLE_S)`, then `assert ... _open_conns ... == 2`.
  - `test_asy_uart_comm.py`: `sleep_ms(_INSIDE_LOCK_MS)`, then `assert bus.session_lock.locked() is True`.
  - `test_digital_twin_run_generic_integration.py`: `sleep_ms(_SLOT_REACH_MS)`, then `assert booted.webserver.closed == 1`.
- **New answer.** Wait for the observable with a bounded poll or an event; the same files already have `_wait_until`
  helpers and poll-try pairs. The value then becomes the poll's backstop. A loaded host can then delay the test but not
  fail it.
- **Basis.**
  - OR37.a (3), answered by the owner "1. yes 2. yes 3. yes, all exactly like this.": "A race is proven by analysis plus
    deterministic tests that force the interleaving (scripted schedule, fake clock, barrier)".
  - The owner's words on a firmware timed check apply to the same shape: "hardcoded delay checks like this are a very
    bad, very awkward pattern" (2026-10-28, REPORT.md "Why this scan").
  - Precedent in the DR4 set, REG:507: "their tests are ordered by events now, not by sleeps".
  - N.1's own sizing rule: host load cannot fail a healthy test.
- **Topic, line.** tests-unit (5), twin (2); L4 (misfit).
- **What changes.** About 7-12 test lines each. The seven rows become backstop rows, or leave the register under N1-b.
- **Not taken.** A negative window ("nothing happens within X") cannot fail a healthy test under load, so those rows are
  SAME (section 8, E2). Reach-then-cancel waits weaken a test if missed rather than redden it; they are SAME too.

### SPEC:13331 `runner.scenarios_timeout_s` = 2555 s, with SPEC:13318 `ci.unit_tests_timeout_min` and SPEC:13319 `ci.unit_tests_gc_threshold_timeout_min` = 175 min
- **As taken.** The scenario-harness job's timeout is 5× CI's slowest run (511 s). The two CI budgets then follow:
  1.27 × the warm run plus one hung scenario job's retry budget (3 × 2,555 s ≈ 128 min).
- **New answer.** The per-file default's own margin, about 2.9× the slowest job (SPEC:13328), applied to the scenario
  jobs. That gives about 1,500 s; the two CI budgets come to roughly 90-100 min.
- **Basis.**
  - The row's own measurement (511 s on CI, 2026-10-20).
  - E.md: "In practice, a hung job runs for two hours before it is named", against CLAUDE.md's "hanging tests are never
    allowed".
  - PICTURE.md M8: "CI went from 45 to 175 minutes, against OR39's 'speeding up'".
  - OR39.a (3) "no timeout is tightened without a measurement" is met, because the measurement exists.
- **Topic, line.** ci-tooling; L4, L8.
- **What changes.** Three literals and their rows. Retries stay as the owner's retry rule has them.

## 3. OBS rows

| id | tunable | the root it depends on (scan row) | topic |
|---|---|---|---|
| SPEC:12032 | `web.start_retries` = 3 | the start retry beside the supervisor's restart: WS-11 (H), S2-G4-11; SCAN2 section 3 "webserver start retries ... ~19 go, nothing stays"; review `webserver-start-retry` unanswered; PICTURE M2 | webserver-rest |
| SPEC:12033 | `web.start_retry_s` = 5 s | as above | webserver-rest |
| SPEC:12060 | `system.escalation_entry_wait_ms` = 1200 ms | the escalation's bounded entry write: A-S14 (C/DELAY), S2-G1-6; SCAN2 section 7 item 4 "goes" | supervisor-reset-watchdog |
| SPEC:12106 | `led.overlay_refresh_ms` = 300000 ms | the NeoPixel 300 s rewrite, NP-5 (H, with its confirmed lost-cancel defect); REPORT section 3 "revert ... removes 5 lines"; SCAN2 section 5 "with NP-5 reverted". The owner on this check (2026-10-28): "I completely don't understand what lead you to implementing a pattern like that arbitrary 5 minutes check." | led-notification |
| SPEC:12110 | `notify.sample_max_age_s` = 10800 s | the sample-age checks at two consumers: NT-3, S2-G1-18, S2-G4-10; SCAN2 section 7 item 3 (the SCD30 re-stamps every cycle, so the age never grows) | led-notification |
| SPEC:12122 | `sgp40.comp_max_age_s` = 10800 s | as above (SGP-2) | driver-sgp40 |
| SPEC:12115 | `scd30.not_ready_warn_at` = 5 | SCD-6 (H, implausible); SCAN2 section 3 "sample-age checks ... (plus SCD-6) ... ~30 go" | driver-scd30 |
| SPEC:13352 | `i2c.timeout_consumer_us` (rule row) | S2-G3-2: the watchdog branch never binds; the rule binds only on dev's UART link above ~575 ms `poll_idle_ms`. G3 classes it H and leaves dev's link as an owner matter | bus-i2c-spi |
| SPEC:12647 | `l2.run_generic_integration_cut_wait_ms` = 50 ms | "it stands for `system.escalation_entry_wait_`...": S2-G1-6 | twin |
| SPEC:12386 | `l1.asy_base_classes_trigger_loop_bound_s` = 1 s | "a trigger loop that ends by itself on its failed re-arm": the refused-timer-arm family, S2-G1-7 and S2-G4-7 (trigger refuted, A.md V6) | tests-unit |
| SPEC:12312 | `l1.sensortask_notify_cycle_rounds` = 200 | the per-device `State` scenario: S2-G4X-2 (the State key and its state machinery go; NT-2 H) | tests-unit |
| SPEC:13330 | `runner.port_lock_attempts` = 10 | the port lock in three languages: REPORT section 9 "port isolation (a lock in three languages, port bands, loopback addresses)" under runaway areas; E.md (P8 break) | ci-tooling |

All 12 stay documented as general knowledge.
- The 300 s and 10,800 s rows are the owner's "hardcoded delay checks" class (PICTURE M2).
- `scd30.not_ready_warn_at` shares its count with `isl29125.periodic_only_warn_at`, a pre-audit value that stays.

## 4. FORM rows

| id | the decision | smaller form | scan row | topic |
|---|---|---|---|---|
| SPEC:12129 `i2c.timeout_max_us` = 200000 µs | refuse an I2C timeout that would let the boot clear outlast the watchdog | one check, not two. The budget sum (`bus.boot-clear-budget`) is the exact form and allows one bus up to ~545 ms; the 200,000 µs ceiling, its tag and its row go | S2-G3-1 (D-H17, D-H18) | bus-i2c-spi |
| SPEC:13358 `system.scan_budget` (rule row) | a supervisor pass with every task dead stays under the watchdog | drop the term "bounded by `system.escalation_entry_wait_ms`". With the bound gone the reboot's entry write is unbounded, and a hung write ends in the watchdog reboot the decision wants anyway | S2-G1-6; SCAN2 section 7 item 4 | supervisor-reset-watchdog |
| N1-g "Writing a row" (SPEC:11965) | each row states basis, margin and re-check trigger (the columns are OR30.a (2), owner) | for test rows that stay, Basis and Margin only where known. "estimated ... — measurement owed" as the mandatory form goes (a 7-column row with three placeholder cells records nothing) | F.md section 5 item 1; REPORT section 10 ("1,063 cells read 'measurement owed'") | docs-records |
| N2-c check conditions 5-6 (SPEC:11995-11996) | rows must not have empty cells; a rule row names its check | condition 5's clause "an `estimated` Basis has no 'measurement owed'" goes with N1-f; condition 6 stays | as N1-g | docs-records |
| 19 L1 timing-band rows (family F, L1) | check the product's timing: the captive-DNS receive backoff, the UDP deadline, a prompt return, the notification's next sleep | virtual time: the driven clock with exact intervals, as the notification and NTP files already use it (E.md "Keep": "the notification file went from 19.0 s to 0.19 s" with every assertion kept; review `driven-time-and-rtc-steps` "ok"). The test files already swap the module's `asyncio` (`asy_udp_socket.asyncio = recorder`). The 11 captive-DNS band edges become about three exact assertions on `dns_server.recv_backoff_*` | E.md (driven-clock keep) | tests-unit |

The 19 band rows:
- SPEC:12319 `l1.captive_dns_no_backoff_elapsed_max_ms`;
- SPEC:12327-12333 and SPEC:12335-12336: the captive-DNS `gap_*_min/max_ms` (initial, doubled, quad, no_backoff, cap);
- SPEC:12389 `l1.asy_dns_client_prompt_return_max_ms`;
- SPEC:12405 `l1.asy_notification_service_next_sleep_min_ms`;
- SPEC:12445-12448 `l1.asy_udp_socket_in_time_*` and `too_late_*`;
- SPEC:12452 `l1.asy_udp_socket_ms_check_elapsed_max_ms`;
- SPEC:12455 `l1.asy_udp_socket_icmp_elapsed_max_ms`;
- SPEC:12460 `l1.asy_udp_socket_retry_cycle_max_ms`.

The 14 F rows on L2-L4 measure silicon or twin real time, so they stay as they are (SAME).

## 5. OWN rows

| id | tunable | the owner's words, source | follows? gap |
|---|---|---|---|
| SPEC:12023 | `web.per_call_timeout_s` = 5.0 s | review `lwip-retry-on-full-queue` "ok": "... retries cooperatively until the peer acknowledges or the 5-second per-call timeout ends it." | yes. Its newer dependant `_trace_before_close()` on the refusal arm becomes obsolete (SCAN2 section 7 item 7); the value stays |
| SPEC:12025 | `web.poll_backoff_max_ms` = 60000 | review `website-unattended` "ok": "failed polls back off to at most 60 s" | yes |
| SPEC:12026 | `web.device_watch_interval_ms` = 60000 | the same: "The device check runs every 60 s" | yes. Form note: the watch's extra `/status` (SCAN2 section 3, website, ~6 lines) |
| SPEC:12027 | `web.clock_mismatch_s` = 5 s | review `website-display-details` (text: "'clock mismatch' below -5 s"), note "Fine, and maintain a reasonable number of digits per value ..." | yes. The "and ..." part is built as `web.default_decimals` |
| SPEC:12029 | `web.chunk_bytes` = 256 B | OR72 "3. a" (the 256 B pieces accepted, OR72.a (3)) | yes |
| SPEC:12030 / SPEC:12031 | `web.max_header_lines` = 32, `web.max_head_bytes` = 2048 B | review `http-head-limits` "ok": "more than 32 header lines or a request line and headers over 2,048 bytes in total, before the memory is allocated" | yes (WS-1). WS-2's further refusals are H and not part of the ok |
| SPEC:12052 | `wdt.timeout_ms` = 8000 | owner, 2026-09-26 (C07/OR70.a), the row's own basis | yes |
| SPEC:12084-12087, SPEC:12091 | `wifi.led_hotspot_client_*`, `wifi.led_deactivated_*`, `wifi.sta_disconnect_wait_iters` | the owner, 2026-10-28: "We thoroughly discussed the WiFi issues and I decided everything already."; for the deactivated pattern also review `wifi-off-led-pattern`, "Generally fine, and as discussed already, this shall respect the general WiFi LED setting" | yes; the row states "it shows through the Wi-Fi LED setting like every pattern". Gap: the estimated Wi-Fi rows carry "measurement owed" and re-check triggers on settled behaviour (section 7, item 9) |
| SPEC:12096 | `udp.poll_wait_ms` = 20 ms | the 20 ms rate owner-confirmed (2026-07-19), restated in review `idle-poll-rate` ("the 20 ms you confirmed") | yes |
| SPEC:12097 | `udp.poll_idle_ms` = 100 ms | OR141, 2026-10-05: "do all as you suggested", covering the reply on the idle-poll note (OR141.a (5): "the idle poll rate at 100 ms, its measurement owed") | yes |
| SPEC:12111 | `scd30.cmd_response_wait_ms` = 50 ms | owner, 2026-07-13 (owner-tested), the row's basis | yes |
| SPEC:12116 / SPEC:12117 | `sgp40.measure_wait_ms` = 100 ms, `sgp40.serial_read_wait_ms` = 3 ms | owner, 2026-07-21 and 2026-07-13 | yes |
| SPEC:12145 | `gc.threshold_bytes` = 32768 | owner, 2026-09-26 (OR40 "the agreed value") | yes |
| SPEC:12153 | `web.default_decimals` = 2 | review `website-display-details`: "e.g. limit to 2 or 3 digits behind the decimal point ... Configured in the website config file" | yes |
| SPEC:12165 / SPEC:12166 | `tool.uv_sync_attempts` = 3, `tool.uv_sync_backoff_step_s` = 10 s | owner, 2026-09-26: the three-attempt retry stays (OR37.a (2) "the three-attempt `uv sync` retry") | yes |
| SPEC:13351 | `uart.rx_ring_floor` (rule row) | OR141 "UART in the DMA ring buffer ... keep a strict eye on how that integrates with the heap allocation"; the ring derived, "never a bare number" (owner, 2026-10-05, as recorded) | yes |
| SPEC:13354 | `loop.uart_call_span_max_us` (rule row) | CLAUDE.md, project owner, 2026-09-11: the UART modules "may never block the asyncio loop" | the rule yes. The 1/3 frame fraction is the agent's and is SAME |
| SPEC:12213 | `l0.vitest_timeout_retries` = 2 | owner, 2026-10-20: "Simply put, do the consistent rule adaptation to tests only and only for those running into timeout." | yes (vitest's own timeout message only) |
| SPEC:13329 | `runner.per_file_attempts` = 3 | owner, 2026-09-26 (standing backstop) and 2026-10-20 (as above) | yes |
| SPEC:12512 | `l1.lwip_host_spin_window_rounds` = 3 | owner, 2026-10-13: "Then option b is fine." | yes |
| SPEC:13099 | `l3.heap_headroom_after_full_system_build_max_used` = 100000 | review `heap-floors-kept` "ok": "survivors at most 100,000 B ... each states its basis and changes only through a new derivation of the need, never to fit a reading" | value yes. **Gap:** the row's Basis reads "estimated ... — measurement owed: the value's own observable on the dev bench"; that invites the fit-to-a-reading the owner excluded. Only one of the three floors in the text has a row |
| SPEC:12938 | `l4.console_starvation_drain_timeout_s` = 30 s | review `console-starvation-bench-test`: "Fine if 'a gated bench test' means 'only if additional write wear is allowed by the flag'." | yes: the test carries `@pytest.mark.persistence_write` (`test_network_resilience.py:929`). Its premise (WS-9's rebind) is on the hardware list (SCAN2 section 8) |
| N1-a (SPEC:11931) | tags plus rows, changed together | OR30: "That list needs to be updated on changing parameters or whenever such parameter is added"; OR30.a "yes to all three" | yes |
| N1-d (SPEC:11953) | per-service timeouts | owner, 2026-07-28 ('define the timeouts per service … Only the individual timeouts need to be set as parameter') | yes |
| N1-e (SPEC:11960 first sentence) | widening names its measurement; stale values corrected with the measurement | OR30.a (3): "stale values are corrected with the measurement behind them" | yes. "never widened on an unproven hypothesis" is the agent's reading and fits L2. Four rows break it (section 7, item 3) |
| N2-a (SPEC:11976) | the one-line tag | OR30.a (2): "each value carries a one-line machine-read `# @tunable` tag in code (like `@web`/`@limits`)" | yes |
| N2-b1 (SPEC:11989-11993 without the count) | fail on unlisted, untagged, mismatched | OR30.a (2) | yes. The near-miss distance is the pre-audit L.5 tag rule |
| N2-e (SPEC:12005) | the register's form | OR30.a (2): "location, dependants, how it was determined (measured/derived/estimated), margin, and re-check trigger" | yes |

**Owner-asked mechanisms with agent values (counted SAME, not OWN).** The mechanism is the owner's; the number is not:
- `uart.chunk_bytes` and `uart.max_transfer_bytes`: the owner's go-ahead note (2026-10-05), "a reasonably defaulted
  chunk size constructor argument" and "A general maximum buffer size, catching uncapped heap flooding".
- `led.signal_wait_ms`: review `led-request-internal-queue`, "Fine, and this for a reason: internal LED commands are
  guaranteed to be bounded by number and frequency".
- The CI apt mirror check (SPEC:13311-13313): the owner, 2026-10-27 at 20:53 UTC, "Yes do it like you proposed".
  - This came after "Don't care about proven external issues so far." (16:48).
  - It also came after "Maybe it actually would be good to investigate." (20:23).
- `module.recover_*_at`: OR113, with the rung order "(owner, 2026-09-30: smallest blast radius first)".
- `uart.rx_ring_default` and `dev.uart_rx_ring`: OR141.

## 6. SUP rows and CHECK rows

**SUP:** none. No row in this set was overtaken by a later decision. The one superseded owner statement
("Don't care about proven external issues so far.", overtaken the same evening) concerns a mechanism, not a row.

**CHECK** (6):

| id | tunable | why it is suspicious either way | the one minimal check | outcomes |
|---|---|---|---|---|
| SPEC:12132 | `fram.chip_probe_at` = 2 | root of the lost-FRAM chain, A-D1 (H, triaged "suspicious"; V10 unverified); SCAN2 lists the chain as "go" with the premise unverified | REPORT section 7 hardware item 2: the FRAM SPI SO level with the chip absent, on the dev board at the pre-audit image `25caf528` | reads 0x00 (pad pull-down): writes are refused with a warning, so no silent loss; the chain and this value are OBS. Reads 0xFF: "reported as landed" is real; the write-path detection stays, value SAME |
| SPEC:12131 | `fram.setup_id_attempts` = 3 | A-D3 is rated R under OR113, but it is SCAN2 pattern 8 exactly ("an owner's general principle applied by an agent to a case found by reading"). No W29 (`FRAM_ID_RETRIED`) appears in any committed bench evidence (`git grep` over `audit/` at `11b66cd8`: only the action and catalog texts) | count W29 entries in the dev board's FRAM log over the hardware round's boots, read before any `ResetErrors` | none: pattern 8 applies (L3: the escalation and reboot carry a disturbed boot RDID), the retry and this row are OBS. Any: SAME |
| SPEC:13025-13028 | `l3.fram_pause_unpause_and_gating_pause_s`, `_rearm_s`, `_pause_margin_s`, `_rearm_margin_s` | timed checks on silicon whose margins assume A-S21's deadline-on-the-status-pass form ("lands at most one 1 s uptime pass late"). A-S21 is H, "suspicious", with its frequency unverified (hardware item HW5) | HW5: whether 8 or more soft callbacks queue at once under the shipped load. `scheduler_saturation_drop.py` forces a drop and does not answer frequency | drops seen under realistic load: A-S21 stays, rows SAME. None: the pre-audit one-shot timer returns, and the four margins re-derive from it |

## 7. Contradictions, and counterparts in other sets

**Contradictions:**

1. **SPEC:11921 against OR30.**
   - *One side:* SPEC:11921 credits "every test tier's sleeps, bounds, timeouts, retries, soak durations, tolerances and
     heap budgets" to "(owner, 2026-09-25, paraphrase)".
   - *The other:* OR30's words are "runtime and timeout parameters for test suites ... substantial for correct
     functioning". OR30.a (1)'s list is suite-level.
   - *Stands:* the owner's words. The paraphrase is an agent widening (L7), and N1-b follows from it.
2. **SPEC:13099 against review `heap-floors-kept`.**
   - *One side:* N1-g and N2-c require "estimated ... — measurement owed" on every estimated row, SPEC:13099 included.
   - *The other:* the owner's "ok" on `heap-floors-kept`: "changes only through a new derivation of the need, never to
     fit a reading".
   - *Stands:* the owner. That row's basis should name its derivation (the check's `worst_case_factor`, SPEC:13100),
     not a measurement owed.
3. **N1-e against four rows.**
   - *One side:* N1-e, "a widening names its measurement".
   - *The other:* four rows record widenings without one:
     - SPEC:12245 `l1.serve_backstop_cap_mult`, "widened 4× → 20× without a stated cause";
     - SPEC:12307 `l1.fram_write_prompt_s`, 0.2 → 1.0 s "for scheduling-jitter headroom";
     - SPEC:12537 `l2.long_wait_s`, "widened 30 → 90 s after two CI failures, no elapsed recorded";
     - SPEC:12543 `l2.dns_poll_s`, tightened with it.
   - All four basis commits predate the audit; the rule was written later. `l2.long_wait_s` is the shape OR37.a (2)
     excludes: "A retry or a longer timeout never counts as a race fix".
   - *Stands:* the rule. The values are SAME as bounds. Under N1-f no new measuring is owed; the record only needs to
     say so.
4. **N.1's config class against the six `dev.uart_*` rows.**
   - *One side:* N.1's class *config*, "a value set per device in `devices/*.toml` ...; not tagged".
   - *The other:* SPEC:12175-12180 tag six `dev.uart_*` values in `devices/dev.toml` as tuned (U8's "tuned, not config").
   - Agent against agent.
   - *Stands:* the rows (bench values with no user setting), but the class text should name the exception.
5. **REG:243 against N2-b2.**
   - *One side:* REG:243 (DR2 set, U9): the per-file count is "the owner's to accept".
   - *The other:* N2-b2, added 2026-10-26 by the lead under CHECKLIST 1d.
   - *Stands formally:* N2-b2, since the owner delegated test-only, no-wear, coverage-adding changes ("That's actually
     a combination you don't need to ask me for.").
   - DR7 answers DIFF on it from the 2026-10-28 knowledge.
6. **REG:242 and N1-b against the owner's tiered-effort words.**
   - *One side:* REG:242 (DR2 set, U9: "every tuned test budget is registered; measurement owed where none exists")
     and N1-b.
   - *The other:* the owner's agreement with REPORT "What went wrong" item 3, and the 2026-10-28 tiered-effort words.
   - *Stands:* the owner.
7. **Two owner statements on the refusal arm (facts for the lead; no question framed).**
   - `web.per_call_timeout_s`'s dependant `_trace_before_close()` is WS-6, owner-agreed on 2026-10-22: "Solutions you
     proposed agreed."
   - SCAN2 section 7 item 7 moves the refusal path to close-then-trace and calls that bound obsolete on that arm. It does
     this under the owner's 2026-10-28 background note: findings tied to a removed cascade "may become obsolete".
   - The value itself is covered by the review "ok" in item 5 of section 5 and stays.
8. **PICTURE.md M2 against SCAN2 section 7 item 2 on the LED deadline.**
   - *One side:* PICTURE.md M2 lists "the LED queue's 120 s deadline" among the hardcoded timed checks.
   - *The other:* SCAN2 section 7 item 2 keeps it as R, on the approved text ("waits for the running signal up to a
     deadline and then queues ... but bounded", answered "Fine, and this for a reason ...").
   - *Stands:* SCAN2. It is the later record and rests on the owner's answer. The 120 s value stays the agent's (C.md
     NP-2) and is SAME here.
9. **The estimated Wi-Fi rows against the settlement.**
   - *One side:* SPEC:12091 and the estimated `wifi.*` rows carry "measurement owed" and re-check triggers.
   - *The other:* the owner's settlement: "We thoroughly discussed the WiFi issues and I decided everything already."
   - *Stands:* the owner. A re-check trigger must not reopen settled behaviour; only a smaller form of the same behaviour
     may be noted.
10. **Coupled removals inside this set (no conflict, recorded so the cleanup takes them together).**
    - `system.escalation_entry_wait_ms` (OBS) is cited by `system.scan_budget` (FORM) and stood in for by
      `l2.run_generic_integration_cut_wait_ms` (OBS).
    - `i2c.timeout_max_us` (FORM) is cited by `boot.unfed_stretch_1_ms`'s margin text (SPEC:13355), which should name
      the budget check instead.
11. **A tension inside L1/L4 (facts for the lead).**
    - PICTURE L1 puts completeness on "the looking, understanding and recording", which would favour a complete
      register.
    - L4 and the owner's 2026-10-28 words put the verification machinery at "small and temporary".
    - The owner's agreement with REPORT item 3 settles the measuring part (N1-f). N1-b rests on OR30's own qualifier,
      not on L4 alone.
12. **`fram.setup_id_attempts` between OR113 and L2/L3 (facts for the lead).**
    - OR113, mild first: "recover mildly, but escalating up to a full bus reset is absolutely allowed".
    - PICTURE L2: "A *mechanism* for a trigger nobody observed is not wanted: ... a retry".
    - PICTURE L3: "escalate rather than contain".
    - Settled by the CHECK in section 6, not by choice.

**Likely counterparts in other sets** (same decision, decided there too):
- Review page (DR1):
  - `http-head-limits`, `website-unattended`, `website-display-details`, `wifi-off-led-pattern`,
    `lwip-retry-on-full-queue`, `heap-floors-kept`, `led-request-internal-queue` and `console-starvation-bench-test`
    (all OWN here);
  - `idle-poll-rate` (answered through OR141);
  - `webserver-start-retry`, unanswered (OBS here);
  - `stall-bounds`, unanswered: its "21 ms garbage-collection term" is `uart.gc_pause_worst_ms`, its I2C half is
    `i2c.timeout_consumer_us`;
  - `ci-budget-margin`, unanswered: the "+25 %, rounded up to 5 minutes" rule behind the CI rows;
  - `driven-time-and-rtc-steps` (the FORM basis for family F-L1);
  - `hand-run-hardware-rows`, whose concern also covers the manual L4 rows (`l4.manual_*`).
- Register sets:
  - DR2: REG:214, REG:226, REG:242, REG:243 (U8 and U9 Part N rows; the scheme items);
  - DR3: REG:117 ("stale-sample bound 10800 s ... in both consumers": the two 10,800 s OBS rows), REG:119 ("stuck-RDY
    warning after 5 consecutive not-ready reads": `scd30.not_ready_warn_at`), REG:345 ("buildgen refuses an I2C bus
    timeout outside 1..200000 us": `i2c.timeout_max_us`), REG:369 (`l2.bus_hazard_recovery_*`);
  - DR4: REG:507 (tests ordered by events, the E1 precedent);
  - DR5: REG:639 (the per-port lock: `runner.port_lock_attempts`), REG:644 (U24's new tunables);
  - DR6: REG:121 ("the WiFi LED overlay is rewritten by its own task every 300000 ms": `led.overlay_refresh_ms`).
- Any set holding:
  - U19's webserver start retry (WS-11);
  - the escalation entry bound (A-S14, from OF-222);
  - the lost-FRAM write-path probe (A-D1);
  - the boot RDID retry (A-D3);
  - the mempause deadline (A-S21);
  - the twin `reader_saturation` floor (2026-10-22).

## 8. SAME rows

**Firmware and build, one line each.** "pre" means the value predates `25caf528`.

| id | tunable | topic | why the same |
|---|---|---|---|
| SPEC:12022 | `web.max_content_length` | webserver-rest | pre; 1.9× the largest legitimate body. Its basis uses NTPHost's 253-character bound, which DNS-1 (H) may drop; the margin then only grows |
| SPEC:12024 | `web.outer_cap_s` | webserver-rest | pre (`884f3ce`); sizing rule "generous" |
| SPEC:12028 | `web.max_pending_fragments` | webserver-rest | pre |
| SPEC:12034-12037 | `uart.cancel_ack_timeout_ms`, `uart.delimited_yield_bytes`, `uart.rxbuf_default`, `uart.txbuf_default` | uart | pre |
| SPEC:12038 / 12039 | `uart.poll_wait_ms_default`, `uart.poll_idle_ms_default` | uart | default aligned to dev's TOML; no device sees a change (B.md:1790); 50 ms measured (F.5.9) |
| SPEC:12040 | `uart.rx_ring_default` | uart | the OR141 ring; D.md D1 R |
| SPEC:12041, 12044, 12045 | `uart.gate_step_ms`, `uart.poll_jitter_ms`, `uart.diag_resync_streak` | uart | pre |
| SPEC:12046 / 12047 | `uart.chunk_bytes`, `uart.max_transfer_bytes` | uart | owner-asked mechanisms (go-ahead note); 256 reuses the owner's piece size; 12,192 is the largest train at the default payload |
| SPEC:12048 | `uart.exercise_period_ms` | uart | pre |
| SPEC:12049-12051 | `uart.hazard_*` (3) | uart | dev hazard mode (UL-1 R); derived from the protocol's budgets |
| SPEC:12053 / 12054 | `system.reset_delay_s`, `system.task_check_s` | supervisor-reset-watchdog | pre |
| SPEC:12056 | `system.timer_base_period_ms` | supervisor-reset-watchdog | legacy cadence (OR75.a: `timer_sequencer(..., 1000)`) |
| SPEC:12057 | `stagger.min_read_separation_ms` | timing-waits | test bound for the owner's OR47 stagger; its only site is a test file (placement only) |
| SPEC:12058 / 12059 | `system.task_fail_increment`, `system.task_fail_max` | supervisor-reset-watchdog | pre; OR130's budget reboot |
| SPEC:12061-12064 | `module.max_error`, `module.recover_device_at`, `module.recover_bus_at`, `module.recover_controller_at` | bus-i2c-spi | pre / OR113 ladder; rung order the owner's |
| SPEC:12065 / 12066 | `dns.timeout_ms`, `dns.tries` | ntp-dns | pre; the owner's per-service rule |
| SPEC:12072-12076 | `ntp.backoff_mult`, `ntp.retry_s_default`, `ntp.retry_max_s_default`, `ntp.plausible_min_unix`, `ntp.plausible_max_unix` | ntp-dns | pre (`25caf528:asy_ntp_client.py:106-107` for the retry pair); the window closes the confirmed zero-timestamp gap |
| SPEC:12098-12100 | `dns_server.recv_backoff_*` (3) | ntp-dns | pre |
| SPEC:12102 | `led.min_signal_s` | led-notification | pre |
| SPEC:12105 | `led.signal_wait_ms` | led-notification | owner-approved deadline (SCAN2 section 7 item 2); 2× the 60 s REST ceiling |
| SPEC:12107-12109 | `notify.loop_tick_s`, `notify.min_sleep_ms`, `notify.cfg_fail_interval_s` | led-notification | pre |
| SPEC:12113 | `scd30.soft_reset_wait_ms` | driver-scd30 | pre; 1.25× the boot time |
| SPEC:12120 / 12121 | `sgp40.fram_verify_mins`, `sgp40.backup_counter_max` | driver-sgp40 | pre; SGP-16 R (OR104); a capped counter (L2) |
| SPEC:12123-12125 | `bmp3xx.cmd_rdy_timeout_ms`, `bmp3xx.meas_timeout_ms`, `bmp3xx.status_poll_ms` | driver-bmp3xx | pre |
| SPEC:12126 | `bmp3xx.reset_settle_ms` | driver-bmp3xx | 2 → 3 ms, verified: `extmod/asyncio/core.py:55-57` (v1.29.0) wakes at `ticks_add(ticks(), t)`, so a 2 ms sleep can end just over 1 ms; one value, no machinery |
| SPEC:12127 | `i2c.probe_settle_ms` | bus-i2c-spi | pre |
| SPEC:12130 | `fram.verify_lock_timeout_ms` | storage-fram | pre; `verify_present()` existed pre-audit with no product caller (a library function, L5) |
| SPEC:12134-12139, 12141-12144 | `isl29125.*` (10) | driver-isl29125 | pre (`75d222e`); the settle pair serves the confirmed settle-horizon gap |
| SPEC:12146 | `gc.emergency_exc_buf_bytes` | memory-gc | closes a confirmed gap (REPORT section 3) |
| SPEC:12152 | `web.poll_interval_ms` | website | pre; the legacy page's 3 s cadence (OR94 keeps the look) |
| SPEC:12154-12162 | `lwip.*` (9) | webserver-rest | pre (B.14.2) |
| SPEC:12163 | `tool.preprocess_timeout_s` | ci-tooling | pre |
| SPEC:12164, 12167-12174 | `tool.apt_acquire_timeout_s`, `tool.remote_query_timeout_s`, `tool.network_step_timeout_s`, `tool.build_step_timeout_s`, `tool.apt_step_timeout_s`, `tool.bench_bridge_recovery_arm_s`, `tool.bench_bridge_up_poll_s`, `tool.node_shasums_timeout_s`, `tool.node_tarball_timeout_s` | ci-tooling | U21's bounded installer, no pillar violation (E.md). The bridge arm serves the owner's dead-man's-switch rule (OR72 (9)) |
| SPEC:12175-12180 | `dev.uart_*` (6) | uart | pre or D.md D1/D2 R; bench values |
| SPEC:13349 / 13350 | `uart.timeout_floor`, `uart.rxbuf_floor` | uart | pre (J.6); both layers existed pre-audit (S2-G3-4) |
| SPEC:13353 | `loop.sync_wait_max_us` | timing-waits | F.3 (pre) |
| SPEC:13355 / 13356 | `boot.unfed_stretch_1_ms`, `boot.unfed_stretch_2_ms` | supervisor-reset-watchdog | OR31's feed rule; checked by review and scenario |
| SPEC:13357 | `boot.setup_unit_stretch_ms` | supervisor-reset-watchdog | measured on silicon; serves CLAUDE.md's boot rule ("does not starve the watchdog") |
| N1-c (SPEC:11934-11951) | the class list | docs-records | the contract exclusion is the owner's (OR30.a (1)); see item 4 of section 7 for the config wording |
| N2-d (SPEC:11998) | the relation checks | docs-records | the 8,388 ms cap is a fact; `reset_delay` < watchdog predates the audit; ×4 is an agent reading that today's 2 s meets; `connections_per_page_load` ≤ `max_connections` |

**Test tiers, one line per family** (sizes after the call-outs above; per-row ids in `DR7_rows.tsv`):

| family | SAME rows | notes |
|---|---|---|
| A, hang backstops | 220 | CLAUDE.md's standing rule "hanging tests are never allowed"; the owner, 2026-07-31: "slower is fine, hanging never is". Under N1-b the per-test ones leave the register; the runner-level ones stay |
| B, poll steps and counts | 171 | step × tries is one derived deadline; under N1-b they leave the register |
| C, condition waits | 115 | bounded waits on an observable; none can fail a healthy test |
| D, inputs and stimuli | 80 | short product timeouts and periods handed to the code under test, fake wire speeds, client socket timeouts. N.1's own "test input" class, nearly all of them |
| E, fixed waits | 261 | **E2, negative windows** (18): `l1.system_service_quiet_window_ms`, `held_window_ms`, `stalled_window_ms` and `hang_watch_ms`; `l1.captive_dns_stray_reply_wait_ms`; `l2.wdt_overrun_wait_s`; `l2.uart_field_sweep_quiet_window_ms`; `l3.uart_comm_hazards_quiet_window_ms`; the UART idle and drain windows; `l2.ntp_starve_window_ms`; `l2.scenario_refusal_feed_s`; `l2.scenario_still_serving_s`; `l1.ntp_fram_system_integration_supervisor_scan_wait_s`; `l2.http_client_silent_server_s`; `l4.network_resilience_no_reconnect_tail_s`. These are timed by nature, and load can only make them pass. **E3, the rest** (243): reach-then-cancel waits, stimulus pacing, silicon settles taken from datasheets, observation tails. The bench log-window tails (`l4.sensor_config_push_calibration_end_margin_s`, `l4.sensor_config_push_reset_voc_settle_margin_s`) belong to the bench log check, which has never run on silicon (G.md R1); they are SAME pending the hardware round |
| F, timing assertions on L2-L4 | 14 | silicon or twin real time is the measurand: watchdog starvation, the ISL29125 cycle bounds, boot-order stamps, the SGP40 cadence gap, the erase feed gap, `l2.feed_gap_share_max` |
| G, load and soak sizes | 120 | OR30.a (1) names "twin run and soak durations". Wear-spending rows stay inside the owner's gates: `l4.bus_concurrency_under_api_load_scd30_write_cycles` = 2 (behind `persistence_write` and `scd30_extra_write`, within the owner's cap of 12, 2026-10-21 "option a"); `l3.scd30_argument_reaction_loop_writes` = 20 (manual power-cut loop, up to 22 SCD30 NVM writes per run, stated in `tests_hardware/README.md`'s wear table and before each `confirm()`; the firmware reads `MeasInterval` back at init, `asy_scd30_driver.py:432`, so the chip's behaviour under a cut is a firmware premise). The `l2.timer_pool_*` rows keep the owner's 2026-07-18 rule ("each failed arm is handled in place, none reboots"); the twin file loses the cases of the refused-arm shapes that go (S2-G4-7), and its values are unaffected |
| H, thresholds | 64 | what OR30 means by "essential for clear test result discrimination": leak rates, heap growth, tolerances, the boot-contiguity control-arm ratios (`l0.boot_contiguity_arm_*`, left as they are by OR21.a: "existing control arms ... are left as they are") |
| R, retry counts | 11 | `l3.toolchain_flash_boot_picotool_load_attempts` = 5 retries only while no BOOTSEL device is enumerated (`harness.py:625-641`), so a failed attempt writes no flash |
| CI | 19 | measured cold and warm runs with B.10.1's rule; the apt mirror check is the owner's (2026-10-27, 20:53 UTC); `ci.unit_tests_coverage_timeout_min` = 95 follows the pytest tier's 1,200 s × 3 |
| RUN | 10 | pre-audit host-speed bands and fallbacks; `runner.per_file_timeout_s` measured (OR37.a (2)'s settled backstop); `runner.tests_scripts_timeout_s` and `runner.kill_after_s` pre; `runner.unix_port_probe_timeout_s` reuses an existing bound |

Nothing of DR7's ran: static reads, `git` and `grep` only.
