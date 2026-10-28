DR5 decision review, written by the part (Wed Oct 28 11:44:47 UTC 2026)

# DR5: the owner-review list, units U24-U30 (TEST, TWIN, HW L3/L4, SCR, CI, SEC, MEM)

Input: `inputs/DR5_register_rows.txt`, 112 rows (`REG:<line>` = the line in `inputs/REGISTER_11b66cd8.md`). Read-only:
git at `11b66cd8` (product tree `497b3eda`), the pinned MicroPython v1.29.0 source, `datasheets/` (read with
`pdftotext`), the scan files. Nothing was run on the Unix port, the twin or the tests.

**Sub-ids.** Where one row bundles decisions that get different verdicts, they are split as `REG:<line> (1)`,
`(2)` ... (or `(a)`, `(b)`); the text after the id says which part. The verdict table behind the counts is
`S/u35r/decrev/dr5work/verdicts.tsv`.

**Basis used most.** The owner's words of 2026-10-28 (brief): "The unit tests shall have good quality, but don't need
deep dives. The audit verification machinery is just a temporary tool." and "hardcoded delay checks like this are a
very bad, very awkward pattern"; OR20, OR30, OR35.a/b, OR36, OR39, OR110 (`S/u35r/picture/or_quotes.txt`); the owner's
2026-10-23 rulings on planting and on device wiring and the 2026-10-21/26/27 answers
(`S/u35r/recovered/owner_rulings_after_LN118.md`, REGISTER lines 783-785); the review page (`inputs/answers.json`,
`inputs/DR1_review_decisions.tsv`); SCAN2 (`G1.md`, `G2.md`, `G4.md`) and the first scan's `E.md` and `REPORT.md` §9.

## 1. Counts

- **Rows:** 112. **Facts (no verdict):** 8 rows: REG:679 (process), REG:709 (docs-records), REG:720, REG:721,
  REG:735 (ci-tooling), REG:733 (tests-hardware), REG:734 (process), REG:745 (core-logging).
- **Decision rows:** 104, counted as **129 decisions** after the splits.

| verdict | decisions |
|---|---|
| SAME | 83 |
| OWN | 20 |
| SUP | 12 |
| DIFF | 7 |
| FORM | 4 |
| OBS | 3 |
| CHECK | 0 |

Per topic (decisions; facts not included):

| topic | all | SAME | OWN | SUP | DIFF | FORM | OBS | CHECK |
|---|---|---|---|---|---|---|---|---|
| process | 31 | 26 | 5 | 0 | 0 | 0 | 0 | 0 |
| ci-tooling | 30 | 19 | 5 | 4 | 0 | 2 | 0 | 0 |
| tests-unit | 12 | 10 | 0 | 1 | 1 | 0 | 0 | 0 |
| twin | 12 | 6 | 0 | 3 | 2 | 1 | 0 | 0 |
| tests-hardware | 10 | 6 | 2 | 2 | 0 | 0 | 0 | 0 |
| memory-gc | 7 | 3 | 3 | 0 | 0 | 1 | 0 | 0 |
| docs-records | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| uart | 5 | 2 | 1 | 1 | 1 | 0 | 0 | 0 |
| security | 4 | 3 | 1 | 0 | 0 | 0 | 0 | 0 |
| core-logging | 3 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| config | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| storage-fram | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| timing-waits | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| driver-scd30 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| wifi | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| webserver-rest | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| ntp-dns | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| led-notification | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| supervisor-reset-watchdog | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |

**Reading the set as a whole.** Most of the 112 rows are records of how the tooling units ran (lane plans, gates, CI
runs, routings, accepted time growth). Those stand: they are process, root-caused, and mostly reduced effort
(L8). The DIFFs come from the few rows that put product code or rig machinery in place for a trigger nobody
observed, or a timed check, plus the U30 product changes that serve the test tiers. Seven rows were overtaken by
the owner's own later answers (Q1-Q3, Q5, Q6, Q8, the 2026-10-23 wiring ruling), and what was built follows each.

## 2. DIFF rows

### D1. REG:704 (2): the unreproduced twin shutdown hang carried on as OF-215
- **As taken** (agent, 2026-10-19, U28 gate1b): SF-U28-21 (one SIGINT not acted on in 15 s) got a diagnostic that names
  the kernel's SIGINT state (`bf42ac8`), and "the rest goes to U30, OF-215". It then ran through U30 (stages 1-2) and
  U35 (stage 3, lane T `8b524eb`: "`spawn()` owns `--stop-file`, `shutdown()` touches it, SIGINT stays the
  fallback").
- **New answer:** stop after the diagnostic. A recurrence fails by name with the SIGINT state recorded; OF-215 closes
  as not reproduced, with no in-band stop mechanism added to the launcher.
- **Basis:**
  - The owner, on the analogous grkizi crash (2026-10-21, REGISTER line 784): "a - if not reproducible by what you
    already did, probably really a glitch. if you made sure it won't be overseen, should it ever reoccur, this is
    fine."
  - OR20 (2026-09-25): "Try to avoid putting test code inside the digital twin or the test tier rigs as far as
    possible. Only if there is no alternative, and keep tiny anyway."
  - The fact: OF-215 at `11b66cd8` (`audit/sweeps/open_findings.md:223`): "Not reproduced in about 1,900 deliberate
    SIGINTs ... no Python or C handler that can swallow a KeyboardInterrupt".
- **Topic** twin; **line** L2 (misfit), L4.
- **What changes:** `scripts/_twin_process.py`'s stop-file ownership. It came in with `656fc82f` (the `stop_file`
  field, its touch and the DIAG fallback in `shutdown()`, the `--stop-file` refusal in `spawn()`): about 15 lines
  plus its tests. OF-215's later stages come out of the records. The runner's own `--stop-file` option is older
  (U18/U25, `git log -S'stop-file'`) and stays. REG:725 names three second-SIGINT cases from the same chain: whether
  they go with it is read from their commit during the cleanup.

### D2. REG:705 (2): a shared twin retired by its wall-clock age (SF-U28-23)
- **As taken** (agent, 2026-10-19, `a628c4d`):
  - `scripts/_digital_twin_scenarios.py` gains `_SHARED_BOOT_DEADLINE_S = 89.0` and `_SHARED_BOOT_BUDGET_S = 30.0`
    (Part N `l2.scenario_shared_boot_deadline_s`, `l2.scenario_shared_boot_budget_s`).
  - A shared twin "close to its deadline is retired", and a count moved past the deadline fails as "the boot's
    overrun".
- **New answer:** tell the boot's own background apart by its event, not by the twin's age. On a shared boot that
  never syncs NTP (hotspot mode), the idle check names SGP40's untimestamped-backup warning as the boot's own. No
  deadline, no budget, no retirement by age.
- **Basis:**
  - The owner (2026-10-28): "hardcoded delay checks like this are a very bad, very awkward pattern" (L2's general
    value: no timed check).
  - The commit's own facts. The failure it fixed named the move by module, level and code:
    `{'SGP40': (0, 1, [['W', 35]])}`. Its time "60 x BackupPeriod + WaitTimeNTP - 1 = 89 read cycles" is the first
    untimestamped backup, an event. One idle dev twin measured it at +94.0 s and +155.1 s, so the 89 s is only the
    earliest time.
- **Topic** twin; **line** L2 (misfit).
- **What changes** (estimate): about 15 lines in `scripts/_digital_twin_scenarios.py`, two Part N rows, and the
  clocked-stub test in `tests_scripts`. The boot sharing itself (REG:659) stays.

### D3. REG:730 (2): product console lines in the logger-less UART driver, for the memory gates
- **As taken** (agent, 2026-10-20, lanes M `296a4e7` and M2 `efa4c93`):
  - The driver prints a caught MemoryError's text through `console()` at every DebugLevel, at its read, frame and line
    buffers, the CRC check and frame, the receive ring, the readiness poll and the teardown's unregister. It also
    prints `re-init teardown failed` on a False `deinit()`.
  - The lines are `src/asy_uart_driver.py:436, 468, 524, 541, 550, 574, 649, 663, 732, 772, 792` at `497b3eda`.
  - The module header gives the reason (`:52-53`): "the line the memory gates read (CLAUDE.md memory rule)".
- **New answer:** no console line in the product for the gates.
  - The catches stay, with their sentinels (the owner-decided degrade, UC-4 option (c)).
  - Visibility comes through the owning module's level-gated logger, as REG:730 (1) already does for
    `UARTComm._allocate()`. Option 1 turns that logger on in the tests.
  - The re-init line goes too: no product path re-inits a UART.
- **Basis:**
  - OR36 (2026-09-26): "contains zero artifacts specifically added for testing, neither functions, nor specific
    variables. Testing must adapt to fit the code, never vice versa."
  - The owner's "Option 1 is good" (2026-10-20, REG:729): the gates get their visibility from the tests' logging
    level.
  - Q6 "Option a" (2026-10-26) keeps level 0 quiet.
  - S2-G2-3 (H, P4): "keep: nothing in the product; the catches themselves stay".
  - S2-G2-11: `UART.deinit()` is called only by `init()`, where `_uart` is still None. `git grep deinit 497b3eda --
    buildgen` is empty.
  - SCAN2 §9: "The handlers that have no logger route their text through the owning module's logger".
  - A real cost besides P4: OF-83 (`open_findings.md`) shows that each console line can hold the loop up to 500 ms
    behind a USB host that does not read (`shared/tinyusb/mp_usbd_cdc.c:125-131`). These lines widen that exposure.
- **Topic** uart (memory-gc); **line** L6 (misfit; PICTURE M6).
- **What changes:** about 12 `console()` lines, `_NAME` and the import in `src/asy_uart_driver.py`; the UART
  changelog's B81-B84 rows restated (Python-internal); about 10 driver test functions that assert the printed text
  (S2-G2-3's count). The gates' reach is recorded as facts in C4.

### D4. REG:738 (1): the resolver's `range(tries)` guard (fix F1c)
- **As taken** (agent, 2026-10-20, `12f4966`): `resolve_ipv4()` builds `range(tries)` in a guard before any socket. A
  `tries` past a machine word answers `(None, DNS_NOT_SENT)`. "the DNS guard also catches `OverflowError`"
  (`src/asy_dns_client.py:146-149` at `497b3eda`).
- **New answer:** no guard.
- **Basis:**
  - Verified by grep: the only caller is `src/asy_ntp_client.py:415` (`tries=self._dns_tries`). It passes the
    generated `_DNS_TRIES = const(1)` (`buildgen/codegen.py:30`, `:430`).
  - The code's own comment: "a non-int is a typing breakage mypy refuses (D.2)".
  - The owner (2026-10-27): "A strong hint for an unnecessary check is that it is proven to be fully covered by typing
    adherence alone, and that it is unreachable with today's code".
  - The owner (2026-10-28): "building upon hypothetical findings is a clear no-go".
  - The same family: G4 §4, "typing-only guards ... none (owner, 2026-10-27)".
- **Topic** ntp-dns; **line** L2 (misfit; PICTURE M4).
- **What changes:** 4 lines in `src/asy_dns_client.py`; one test (`tests/test_asy_dns_client.py:587`).

### D5. REG:738 (2): NotificationService logs its unreadable config once per episode (fix F1c)
- **As taken** (agent, 2026-10-20): "the episode is a local flag, as BMP3XX's". A good read or a task restart ends the
  episode, and state 4 is still published each cycle (`src/asy_notification_service.py:253`, `:268`).
- **New answer:** no episode flag. Each failed read goes to the logger, whose newest-entry rule (`_keep()`) keeps the
  slots from flooding, and the console keeps printing.
- **Basis:**
  - OR35.a (2026-09-26): "Console logs actually should keep printing all."
  - OR35.b: "just don't repeat the same error in the slots. Pure and simple."
  - S2-G1-8: notification `:256-275` is among seven flags laid over the central rule (H, OV A-P1). Its one reachable
    trigger is a directory where the config file belongs.
  - The same unit's F1d applies OR35.b centrally ("a repeat of the newest code during a reset is marked, not
    appended", REG:739).
- **Topic** led-notification; **line** L3 (misfit; PICTURE M3).
- **What changes:** about 6 lines in `src/asy_notification_service.py`; the test at
  `tests/test_asy_notification_service.py:1411`.

### D6. REG:746: a bounded wait on the escalation's entry write (OF-222's planned fix)
- **As taken** (agent, 2026-10-20): OF-222 was routed to U31 with "a seen-failing test first, then a bounded wait on
  the escalation's entry write". U31 built it at `fbd0f77`, `143a555` and `696bc87`: `_ESCALATION_ENTRY_WAIT_MS`
  (1,200 ms), `wait_for_ms`, a TimeoutError arm and a MemoryError `console()` arm (`src/asy_system_service.py:586-600`
  at `497b3eda`).
- **New answer:** no bound. Keep `write_reset_record(escalate)` before the entry, which has already landed, and then a
  plain awaited entry write. A lock held by an overflow in `release()` then ends in the watchdog reset, which reads
  the recorded code 20.
- **Basis:**
  - Source at `497b3eda`, `src/asy_system_service.py:581-584`: "The reset is recorded before the escalation's first
    await ... should what follows fail, the watchdog's reset still reads this code".
  - S2-G1-6 (C, DELAY): the premise V7 is unverified and was never observed. The bound is partial even on that
    premise: the next await, `_reboot()` → `_flush_config_stores()`, takes `owner_lock` with no bound.
  - SCAN2 §7 item 4: "goes".
  - The owner (2026-10-28): "hardcoded delay checks like this are a very bad, very awkward pattern".
- **Topic** supervisor-reset-watchdog; **line** L2 (misfit; PICTURE M2).
- **What changes:** about 12-14 lines, the `@tunable` and its Part N row, the console arm, and the escalation test's
  timeout case. The C-stack reboot itself stays exactly as decided (review `c-stack-reboot`, "ok").

### D7. REG:747 (2): a rig override for the Unix port's stale parse-tree root (OF-224)
- **As taken** (agent, 2026-10-20, F1e): "the rig-level clear of the root (`toolchain/micropython_overrides.py`) to
  U36 as OF-224". OF-223 (the two UART link soaks) waits on it (its status at `11b66cd8`).
- **New answer:** no rig override. Where a soak needs it, apply F1e's own test-level form (each period ends
  collected). Close OF-224. Close OF-223 on U32's sweep unless a soak trips.
- **Basis:**
  - OR20 (2026-09-25): "Try to avoid putting test code inside the digital twin or the test tier rigs as far as
    possible. Only if there is no alternative, and keep tiny anyway."
  - The alternative exists, in the row's own words: "the test-level fix, not a rig override (smaller, local, and
    robust to any fixed stale root)".
  - OF-223 at `11b66cd8`: "40 paddings at -1 and at 32768, 80 runs, both soaks passing in every run, 0 memory
    markers".
- **Topic** tests-unit; **line** L4 (misfit).
- **What changes:** records only (OF-223, OF-224). No new override is added to `toolchain/micropython_overrides.py`,
  and no seen-failing padding test is needed for it.

## 3. OBS rows

| id | decision (one line) | root it depends on | topic |
|---|---|---|---|
| REG:663 (b) | OF-184 (every scratch build records `W CONFIG_LOST` in production SYSTEM history) documented, no code change | W69 itself: S2-G4-21 ("hypothetical; OF-184 is created by it"); G4 chain 10 "Removal takes ~20 lines and OF-184" | config |
| REG:670 (b) | OF-60's manual FRAM-pull latency observation (a chip lost in a read-only stretch is caught only at the next write) routed to U27, then round R2 item H17 | the lost-FRAM chain (A-D1's write-path probe and `lost`): S2-G4-5, SCAN2 §3 "premise unverified (hardware item) ~60 go"; G4 chain 3 | storage-fram |
| REG:732 | an early first read (up to 1 s, once per episode) after a read-trigger arm fails while its reader's task is down: no change | the refused-timer-arm family (`_rearm_timer()`, `_timer_failed()`): S2-G1-7 / S2-G4-7, trigger refuted (A.md V6); the owner on boot-time timer shortage (Q2, 2026-10-21): "a - if the shortage came each boot, this would be a malformed firmware, which would already be seen in the tests - nothing which would happen by itself as a surprise." | timing-waits |

Each stays documented as general knowledge. If V10 (the absent chip's SO level, a hardware item) keeps the bit-0
write refusal, that refusal is a write-path refusal and does not bring back OF-60's read-path question (S2-G4-5,
"keep").

## 4. FORM rows

| id | the decision kept | the smaller form | scan row | topic |
|---|---|---|---|---|
| REG:705 (3) | a bound that ends a hung CI job by name, with the owner's two retries | Bound a hang where it occurs, so only the hung scenario fails by name and is retried, in minutes. The job limit then sits near the warm time (9-10 min) plus that retry, not 175 min. The per-attempt bound is 2,555 s = 5x the slowest job (R-21, agent), × 3 attempts ≈ 128 min. | E.md `.github/` cost table and "Strain on the hang rule ... a hung job runs for two hours before it is named"; REPORT §9 "a hung job can run about 128 minutes before it fails"; SPEC Part N `runner.scenarios_timeout_s` at `11b66cd8` ("7,665 s, about 128 min"); owner OR39 "Look for opportunities for speeding up the test suite" | ci-tooling |
| REG:713 | the coverage job's limit covers the pytest tier's timeout retries | A per-test bound, so the timed-out test is the one retried: the owner's "The retry logic is for tests running into timeout". Today a timeout re-runs the whole `tests_scripts` tier under its 1,200 s bound (`scripts/test.sh:488-514`), which is what lifts the job from 35 to 95 min. | as above | ci-tooling |
| REG:731 | a launch with a 256-byte or longer argument fails by name instead of looking like a dead twin (a real find) | One shared check: the Python `_uninternable()` that `tests_hardware/twin_board.py` already calls, plus `scripts/test.sh`'s refusal at start. No JS or shell copies of the literal 255 pinned equal by tests. | E.md scripts/ and tests_js/ "Violations: P8" (copies held equal by tests); REPORT §9 P8. REG:725's +108 % on `test_run_unix_port_integration_sh.py` is this copy's nine cases. | twin |
| REG:740 (1) | the memory-catalog check stays correct for what it guards | A check of OR110's forbidden case: long-lived, growing heap objects in run-phase code. That needs none of RD-1's ten short-lived forms (unfoldable tuples, `tuple()`, conditional and boolean branches, binary operands, generator expressions, private constructors, calls through an expression) and none of their per-site I.2 rows. | E.md tests_scripts "Excessive: The static-contract layer grows with every unit" and "Violations: ... the ~1,700 lines that pin SPECIFICATION.md tables are permanent CI that came out of audit rules"; PICTURE M7; OR110 "If a timer allocates, never reaches any critical value and frees some seconds later, it's less critical."; owner 2026-10-28 "The audit verification machinery is just a temporary tool." | memory-gc |

## 5. OWN rows

| id | the owner's words, source | built follows? gap |
|---|---|---|
| REG:641 | OR78 (2026-09-28): "nothing about the WoZi and Dev build shall remain hardcoded at any place anymore ... It is valid for the tests, tiers, twins, website - and any other places." | Yes: the banner is `b"uart-crossover"` (`src/asy_uart_link_driver.py:35`), with a Class B changelog row. No gap. |
| REG:665 (2) | review `console-starvation-bench-test` ("ask", 2026-10-02): "Fine if "a gated bench test" means "only if additional write wear is allowed by the flag"." | Yes: `@pytest.mark.persistence_write` on the test (`tests_hardware/bench/test_network_resilience.py:929`). Gap: CLAUDE.md tags the sentence "(owner, 2026-10-02, paraphrase)" although the owner's verbatim note exists. |
| REG:667 | review `twin-first-for-instruments` "ok" (2026-10-02): "A committed runner runs every device script and hardware test once against the twin before it enters the hardware queue, and again after a change to it or the API it calls; exceptions are listed."; "The OK in the review stay valid." (2026-10-28) | Yes: 121 instruments (21 pass, 100 exceptions, each with a reason), re-recorded when the runner, API or script hash moves (REG:673, REG:733, REG:743). Form only: E.md chain 8 and REPORT §9 count about 2,260 lines (recorder, record, `test_twin_record.py`, `twin_board.py`, `test_twin_board.py`). No scan row names a smaller form yet. |
| REG:680 (1) | review `stub-versions-pinned` ("ask", 2026-10-02): "Fine, and we need to ensure that this will be updated along with Micropython when switching to a newer release." | Yes: `toolchain/versions.toml` `[stubs]` board `1.29.0.post1`, stdlib `1.29.0.post2`; a moved stub tree fails the repair (A.U27.02). Gap: CLAUDE.md quotes the note as a paraphrase, as the row itself says. |
| REG:684 | owner (2026-10-15): "Once you are at a fitting stage, rebuild the sandbox", clarified "The instance which had the dev null issue" | Yes: rebuilt after W1 part 2, fingerprints equal, re-proof run. No gap. |
| REG:691 | owner (2026-10-19): "Finalizing firmware in U35 and running the checks in parallel to the large docs review sounds good." | Yes. The timing was later replaced by the owner's own direction, REG:722 (see C13). |
| REG:692 | owner (2026-10-19): "The way I would run it: a separate session on the Pi4, but on the same branch in Git. The interface would be a handover and result document, so both sessions can push onto the same branch without conflicts - separate files by design." | Yes (`audit/order/WORK_ORDER.md` §5). The agent's details (a push stops on an incoming path outside the other side's set; bench pushes batched) are conservative. No gap. |
| REG:693 | owner (2026-10-19): "Default is ok"; then "(a) is still the choice." | Yes (the `pyproject.toml` comment, SPEC D.6). No gap. |
| REG:706 | owner (2026-10-20): "I want it to be consistent throughout the project"; "Two retries everywhere" | Yes, narrowed by REG:707 and REG:708 (owner). |
| REG:707 | owner (2026-10-20): "pytest tier", "JS tier" and "This rule / consistency is for testing only. Firmware stays unaffected." | Yes: the pytest tier's attempts loop, the JS tier's retry, the NTP re-sync untouched. Form: see FORM REG:713. |
| REG:708 | owner (2026-10-20): "The retry logic is for tests running into timeout. ... No need to change anything about the Hotspot retires (only find the cause, as already planned)"; "Simply put, do the consistent rule adaptation to tests only and only for those running into timeout. The Hotspot remains untouched." | Yes: the bench event retries keep their counts. Gap: the guard `tests_scripts/test_retry_counts.py` (every retry tunable tabled as a timeout retry, an event retry or a bound) is the agent's addition. The owner said "Simply put", so it is a candidate under "The audit verification machinery is just a temporary tool." |
| REG:710 | review `threat-model-table` "ok" (2026-10-02); owner (2026-10-20): "Option 1, sign off A.11 as is" | Yes: A.11 unchanged by the review (REG:719). Gap: `tests_scripts/test_threat_model_statement.py` (A.U29.02, agent; REG:716's vacuity guard on top) is permanent CI that pins a SPECIFICATION.md table: the class E.md tests_scripts "Violations" sets against the owner's "temporary tool". |
| REG:715 | the Wi-Fi behaviour, owner (2026-10-28): "We thoroughly discussed the WiFi issues and I decided everything already."; the 2026-10-23 matrix rule: "the first device runs specific tests, which are always and guaranteed present and always identical for every device, fully independent from their configuration ... then it is a good thing as it saves time" | Yes: the product rule is unchanged, and the device-independent case runs on the first generated device (E.2.1). No gap. |
| REG:722 | owner (2026-10-20): "Once you are done with U35, wait for my decision in which order and at what time to start the parallel hardware session and the doc works." | Yes (`WORK_ORDER.md` §5 item 1, `03c3995`). |
| REG:724 | owner (2026-10-20): "I would like it to be fixed now, and your proposal without extra allocation sounds promising, check if this works and implement it accordingly." | Yes: fix F1d (REG:739). The agent limited the scope to a pause refusal ("a lost chip or a write fault keeping today's effect"). The lost-chip part belongs to the lost-FRAM chain (S2-G4-5, H) and drops with it. |
| REG:728 | owner (2026-10-20): "81% of re-reading really is much, try to improve here as you suggested. But don't cut back on quality or depth ever."; "And yes, do smaller packing and try to use fresh agents in most cases."; "Apply that as a standing rule for future work." | Yes (CLAUDE.md "Work split across subagents", `bf21d9e`). The "60-80 tool calls" figure is the agent's, kept as a goal, which matches the owner's 2026-10-27 words: "so it should be a goal, but not a hard limit, I'd say". |
| REG:729 | owner (2026-10-20): "Option 1 is good" (logging on at error level in the unit tests that can run out of memory) | Yes in the unit tier: a stored `DebugLevel` 1 is planted through the product's config path only when none is stored; no product hook. Gaps: (a) the twin half (every harness boot at level 1, lane V `14512c5`) goes beyond "the unit tests" and is labelled at the code as the agent's extension (`scripts/_digital_twin_scenarios.py:975-977`, REG:737); (b) the same unit's product console lines (D3) pull against the option's direction. |
| REG:739 | as REG:724 | Yes, "without extra allocation": a RAM-only reset allocates 96 B, where it allocated 416 B and 8,320 B before. The agent's bookkeeping (`_kept`, `_counted`, the repeat mark) keeps entries logged during the reset's wait, in line with the owner's "I just want to make sure no evidence to a bug, be it in the firmware or the tests, is silently lost". Its overlap case grew at U35 into a 29-bit reset set (see §7, counterparts). |
| REG:740 (2) | review `c-stack-reboot` "ok" (2026-10-01): "... The deepest await chain is measured and must stay at most half of the 7,936-byte stack; a host test fails if the chain grows past a pinned depth, and the bench reads the real peak." | Yes: RD-3, RD-4 and F3a2 make the model exact; the deepest chain is 28, the pin was not raised and the model not loosened. Form only: E.md lists `_await_depth.py` (909 lines plus a 207-line test) under "Excessive"; no smaller form is named. |
| REG:741 | review `c-stack-reboot` "ok": "A C-stack overflow caught anywhere is recorded, and the supervisor reboots the unit at its next pass with reset reason 20." | Yes: the lock-release exits and the rebound `_print_exception()` report. Form only (S2-G4-1): one check in `PrintLog._line()`, 4 explicit calls (the two lock-release exits F1b added are two of them, `asy_base_classes.py:132`, `asy_fram_driver.py:174`) and the Microdot hook. `tests_scripts/test_fatal_report_sites.py`'s every-broad-handler rule is the checker of the 123-site form and goes with it. G4 §10 check 1 confirms the fold. |

## 6. SUP rows and CHECK rows

**SUP** (the later decision stands in every case):

| id | superseded decision | by | built follows? |
|---|---|---|---|
| REG:651 (2) | A-11: "driver cases on `device_with()`'s device only" | owner (2026-10-23): "Single device tests with different wiring should actually be avoided, so these tests should go for all devices." (with "matrix deduplication is something different!") | Yes: U35's CMr1 lanes (e.g. `d87bd0d8`, the SCD30/SGP40 twin-bus tests once per distinct wiring) |
| REG:657 (2) | BACKLOG owner questions 1 and 2 with their defaults | owner (2026-10-21, REGISTER lines 783-784): Q1 "a - if not reproducible by what you already did, probably really a glitch. ..."; Q2 "a - if the shortage came each boot, this would be a malformed firmware, ..." | Yes: no code change; Q1's condition checked |
| REG:660 (2) | 34-35 s per stage accepted for `tests/test_digital_twin_ntp.py` (OF-168) | U35's driven-clock rewrite (agent, 2026-10-27; the file now runs "on one driven clock", `:126`), under the owner's "Test duration going up like this is anyhow something to fix - not cutting back strictness, but making it more efficient" | Yes |
| REG:664 (1) | M.HW_BENCH.093 (5)'s UART hazards under API load left unwritten (OF-180) | owner Q5 (2026-10-21): "b - system shall be proven stable unter max load allover" | Yes: U35 lane U (a hazard mode in dev's exerciser, twin-proven, bench test written, silicon parked); SCAN2 §5 keeps "the UART DMA ring and hazard mode" |
| REG:665 (1) | CLAUDE.md's `scd30_extra_write` sentence following the code, pending Q3 | owner Q3 (2026-10-21): "option a" (no cap) | Yes: restated at U35 lane D |
| REG:669 | growth of the wear-gate files accepted (persistence-write gating 4.0 → 9.6 s) | U27's efficiency rule and lane E2 (REG:688: 11.6 → 10.0 s) | Yes. The gate machinery's own size is a question for the cleanup plan. |
| REG:670 (a) | lane A 44 (the unit tier left at level off); lane E 94 (OF-180); the stack test reading code 5 until code 20 | owner Option 1 (REG:729); owner Q5 "b"; code 20 landed (lane C `ce87287`, REG:727) | Yes |
| REG:676 (1) | "no comment-cap length rule" (R-4, Q6 default (a)) | owner Q6 (2026-10-21): "c" (120 characters) | Yes: `tests_scripts/test_comment_block_cap.py:25` `_WRAP_WIDTH = 120`. See also C1. |
| REG:676 (2) | `@include` not an exempt tag (R-5, OF-186) | owner Q8 (2026-10-26): "These lines are not comments, they count as productive code. Option B." | Yes: `_TAGS` includes "include" (`:29`) |
| REG:676 (3) | `test_voc_algorithm.py` and `test_digital_twin_ntp.py` left unchanged after measuring | VOC: 20.0 → 6.3 s at 32768 through the rig's GC mark stack (REG:723) and constants built once (OF-90, U30); NTP: U35's driven clock | Yes |
| REG:676 (4) | "the probe gets no time bound (OF-191)" | U28 lane C's probe bound (REG:697); OF-191 closed (REG:703) | Yes |
| REG:688 (2) | each efficiency rewrite "bitten by a planted regression" | owner (2026-10-23): "I never required to plant faults for every test. Planting faults is a good measure for complex measurement tests ... but not required for the straightforward tests ... Planting errors for those straightforward tests would be complete overkill." | Applies to future work; the row does not say whether any bite was committed as a test |

**CHECK:** none. The one candidate, the FRAM RDID bytes that U25 took from the driver because "the PDFs did not render"
(REG:659), was settled statically here. `pdftotext -layout -f 10 -l 10` on both datasheets gives MB85RS64V `04H 7FH 03H
02H` and MB85RS2MTA `04H 7FH 48H 03H`, equal to `digital_twin/machine.py:610-613` and `src/asy_fram_driver.py:44-47` at
`497b3eda`. So REG:659 is SAME.

## 7. Contradictions, and the likely counterparts in other sets

**Contradictions** (the owner's words stand in every case):
- **C1.** REG:676 (1) against the review.
  - The agent's R-4 (2026-10-15): "no comment-cap length rule", default (a).
  - The review `comment-cap-long-lines` "ok" (2026-10-02): "counts a long comment line as several lines at a
    110-character wrap; 84 existing blocks go over".
  - The owner's later Q6 "c" (2026-10-21, 120 characters) settles it, and the code follows.
  - Facts for the lead: by U27 the count at 110 characters had grown to 761 blocks in 437 files (REG:676), the
    agent's reason for asking again. The two owner statements differ only in the width, and the later one stands.
- **C2.** REG:676 (2) against owner Q8. The owner stands, and the code follows.
- **C3.** REG:651 (2) (A-11) against the owner's 2026-10-23 wiring ruling. The owner stands, and the code follows
  since CMr1.
- **C4.** REG:730 (2) against OR36, Option 1 (test-side) and Q6 "Option a" (level 0 quiet). The owner stands.
  - Facts for the lead: the pull comes from CLAUDE.md's memory rule ("caught-and-logged included"), which is agent
    text. G4 §10 item 5 calls the gates' reach "the owner's call".
  - The owner's words on record are OR36 and the test-side Option 1. A grep of `or_quotes.txt` for MemoryError finds
    no owner words asking the product to print for a gate; the only hits are OR26.a and agent integration text
    (OR115.a, OR118.a, "no quote").
- **C5.** REG:738 (2) (a per-module episode flag) against OR35.a/OR35.b. In the same unit it also conflicts with
  REG:739 (F1d applies OR35.b centrally). The central rule stands.
- **C6.** REG:738 (1) against the owner's 2026-10-27 rule. The owner stands. Its sibling in the same unit, REG:726,
  notes that `write_and_recvfrom()`'s `tries` guard catches TypeError only, which is moot because the method has no
  `src/` caller. Both guard values no caller can pass.
- **C7.** REG:746 (the bound) and REG:705 (2) (the 89 s deadline) against the owner's "hardcoded delay checks like
  this are a very bad, very awkward pattern" (2026-10-28). The owner stands.
- **C8.** REG:704 (2) against the owner's Q1 principle (2026-10-21) and OR20. The owner stands.
- **C9.** REG:747 (2) against OR20. Inside the same row, F1e prefers "the test-level fix, not a rig override" but
  routes a rig override (OF-224). The test-level form stands.
- **C10.** REG:705 (3) and REG:713 against L4 (OR39; REPORT §9 "The hang rule holds in letter only"): FORM.
  REG:731 against L5 (P8): FORM.
- **C11.** A chain inside the set, not a contradiction: REG:659's boot sharing (U25, an efficiency the owner wants)
  created the background-move race that REG:705 (2) then fixed with a timed check (SCAN2 pattern 3, "a placement that
  creates its own problem"). The sharing stays; only the fix's form changes (D2).
- **C12.** Scan text against owner words, for the lead. The owner stands in each, so a scan's "runaway" or "excessive"
  can only apply to form or scale:
  - E.md tests/ "Excessive: Multiplying tests per device wiring: CMr1-CMr1m" and REPORT §9 "the driven-clock and
    per-wiring widening", against the owner (2026-10-23): "Single device tests with different wiring should actually
    be avoided, so these tests should go for all devices." The driven clocks answer the owner's "Test duration going
    up like this is anyhow something to fix".
  - E.md chain 8 and REPORT §9 "the twin-record", against review `twin-first-for-instruments` "ok" (REG:667).
  - E.md chain 5 and REPORT §9 "the `@tunable` tagging", against OR30 (2026-09-25): "many tunable parameters ... for
    example, runtime and timeout parameters for test suites ... make a list and document at an appropriate place.
    That list needs to be updated on changing parameters or whenever such parameter is added." REG:644, REG:680 (2)
    and REG:717 follow OR30.
  - E.md tests_scripts "Excessive: ... `_await_depth.py`", against review `c-stack-reboot` "ok" ("a host test fails
    if the chain grows past a pinned depth"; REG:740 (2)).
- **C13.** Owner against owner, facts only. REG:691 (2026-10-19: hardware session 1 "in parallel to the large docs
  review") and REG:722 (2026-10-20: "wait for my decision in which order and at what time"). The later direction
  governs the timing, and REG:722 says so. Nothing is left open.

**A records fact for the lead.**
- These rows name lane-level decisions only "among them":
  - REG:651 (rulings A-1 to A-36);
  - REG:659 (84 lane deviations);
  - REG:661 (R-1 to R-26);
  - REG:664 (46);
  - REG:672 (R-1 to R-25);
  - REG:677 (39);
  - REG:697 (R-1 to R-4);
  - REG:700 (21);
  - REG:734 (all of U30's 15 lanes, in hand-backs only).
- The rest are in `audit/artefacts/evidence/U2x_close/.../review_list.md` and the lane hand-backs. They are outside
  this review's input and were not judged one by one.
- Also: `inputs/DR5_parked_rows.txt` (68 "Parked deltas" rows from mixed units) was not in this part's launch scope.

**Likely counterparts in other sets.**
- **Review page (DR1):**
  - `c-stack-reboot`: REG:740 (2), REG:741, REG:727 (E25, code 20), REG:725 (Run 12), REG:746.
  - The unanswered `cstack-escalation-path` and `fatal-report-home`: REG:741, REG:746.
  - `twin-first-for-instruments`: REG:667, REG:673, REG:733, REG:743.
  - `comment-cap-long-lines`: REG:676 (1).
  - `stub-versions-pinned`: REG:680 (1).
  - `console-starvation-bench-test`: REG:665 (2).
  - `threat-model-table`: REG:710, REG:716.
  - `retry-pass-flagged`: REG:643, REG:706-708.
  - The unanswered `ci-budget-margin`: REG:705 (3), REG:713, REG:719.
  - `ci-web-filter-base`: REG:700.
  - `twin-tolerates-ntp-offline` ("change": a local NTP responder). It is built (`digital_twin/unixport/_offline_ntp_config.py`
    `write_responder_ntp_config`) and relates to REG:654.
  - `driven-time-and-rtc-steps`: REG:660 (2), REG:676 (3).
  - `hand-run-hardware-rows` ("ask": "What are these tests good for? ... we can completely drop them"): the manual
    observations of REG:664 (2) and REG:670 (b).
  - `heap-floors-kept`: REG:676 (5).
  - `system-command-sequence-details`: REG:737.
  - `failed-push-no-flash-write`: REG:642 (the reap lets a due deferred flush complete).
  - `bench-psk-fallback`: REG:711.
- **Other register rows:**
  - U11's SF-M1-01 (the W69 CONFIG_LOST warning): REG:663 (b).
  - U31's OF-222 fix (`fbd0f77`, `143a555`, `696bc87`): REG:746.
  - U35 lane P's OF-221 fix (`596e7ff`: "each store reset takes the lowest free bit of a 29-bit set ... a 30th reset in
    flight is refused"): REG:744, REG:739. A form observation for that set's reviewer: the fix already refuses the
    30th overlapping reset, so refusing a second overlapping reset on one logger may be the smaller form. This is not
    verified here.
  - U35 lane T's OF-215 stage 3 (`8b524eb`): REG:704 (2).
  - U35 lane U's UART hazard mode: REG:664 (1).
  - U33's owner-answer rows (REGISTER lines 783-785): REG:657 (2), REG:665 (1), REG:676 (1), REG:664 (1).
  - U32's OF-223 sweep and U36's OF-224: REG:747.
  - U35's CMr1 per-wiring and driven-clock lanes: REG:651 (2), REG:660 (2), REG:676 (3).
  - The UART changelog's B81-B84: REG:730.
  - U15's SF-M3-01 (the 10,800 s stale-sample bound) and SF-M3-09 (the 300 s NeoPixel rewrite): the same timed-check
    family as D2 and D6 (PICTURE M2).

## 8. SAME rows

- REG:124 tests-hardware: the FRAM CS power-off sentence plus an optional, wear-free scope step; it verifies a
  datasheet requirement before any fix (L2).
- REG:125 tests-hardware: the SCD30 power-cut NVM step sits behind `confirm()`, manual, and the owner can decline it at
  the step.
- REG:127 tests-hardware: one marker table for both conftests (one source).
- REG:638 process: U24's waves cut under the owner's effort decision; at most five lanes at once.
- REG:639 tests-unit: the port lock unchanged; a per-namespace runtime directory for the session's own runs only.
- REG:640 tests-unit: the UART fake follows rp2's TX/RX pin rule (`ports/rp2/machine_uart.c`).
- REG:642 tests-unit: the async-harness reap fixes, root-caused (aborted files, a segfault); per-call cost 84 → 3.1 µs.
- REG:643 tests-unit: SIGINT first, so a hang names its test (E.md keep list); a 137 past the timeout is retried as a
  timeout, as the owner's later rule reads.
- REG:644 tests-unit: three new bounds with Part N rows, as OR30 asks; the values are measured.
- REG:645 tests-unit: four keep-as-is choices, each the cheaper or the stricter one.
- REG:646 tests-unit: boot markers from the existing `boot_phase()`; no product logging added for a test (OR36).
- REG:647 process: the launch routine written down after process slips; no work affected.
- REG:648 ci-tooling: the gate's reds root-caused to the environment and stale pins.
- REG:650 process: U25's 13 planned lanes cut to seven.
- REG:651 (1) twin: rulings that follow the port: static per-id objects, oldest-fault order, and a real poll over a
  twin UART failing the test (CLAUDE.md's bounded-fake rule).
- REG:652 twin: the access point on the loopback, the only address the twin's clients can reach.
- REG:653 twin: the hung-step scenario ends on the runner's event line, not on a wait (−68 s per stage).
- REG:654 twin: the planted NTP store is complete, so a fresh boot logs no missing-key warnings.
- REG:655 ci-tooling: the twin CI split per device, stage and part, each job under 20 min, no check dropped (OR134).
- REG:656 process: the suite's fixed waits sent to findings for removal; routing.
- REG:657 (1) docs-records: an owner tag scoped to its own record (L7).
- REG:658 ci-tooling: a run standing in for CI starts from a clean tree.
- REG:659 twin: lane deviations, the boot sharing kept; the RDID bytes verified (see §6).
- REG:660 (1) tests-unit: small measured growth for real-socket and CRC cases.
- REG:661 process: six lanes in three waves; a guard's false positives fixed in the guard.
- REG:662 tests-hardware: the lead's merge decisions; a TwinBoard keeps its filesystem as silicon keeps its flash.
- REG:663 (a) tests-hardware: dev's 512 B ring; prerequisite writes unflagged (CLAUDE.md's prerequisite rule); the
  spoof skip and the SGP40 walk kept until measured.
- REG:664 (2) tests-hardware: one fold, two manual observations moved.
- REG:665 (3) docs-records: the rollover method named on the tick-offset image (a recorded owner decision).
- REG:666 process: routing at the close.
- REG:668 ci-tooling: the gate's reds root-caused; installs that differ from the lock are refused.
- REG:670 (c) process: the remaining steps routed to their units.
- REG:671 process: one carry moved to the file's next holder.
- REG:672 process: at most four lanes at once, checked disjoint (fits OR107).
- REG:673 ci-tooling: cross-lane mismatches root-caused; the lists only shrank.
- REG:674 ci-tooling: lanes on a private toolchain copy, so no run read a binary that was being rebuilt.
- REG:675 process: the next-holder fallback for moved findings.
- REG:676 (5) twin: the SGP40 walk kept until measured; the 1,200 s tier bound; the UART floor at 32768 only (measured);
  no streaming API without an M entry.
- REG:677 ci-tooling: 39 small lane deviations, each with its consequence.
- REG:678 process: a refused script run as its three commands, each checked.
- REG:680 (2) docs-records: the docs follow the code (counting rules, the venv refusal, C.5.3, Part N bounds).
- REG:681 process: routing at the close; OF-186 put to the owner (answered by Q8).
- REG:682 process: steps landing in part; M.TSC.065 later follows Q6.
- REG:683 process: the `/dev/null` prevention rule, cheap, after a real event.
- REG:685 docs-records: a tag date kept as merged; the actor is right either way.
- REG:686 process: the whole tier once per lane before hand-back (script time, OR134).
- REG:687 process: a hand-back claims only what its logs show.
- REG:688 (1) ci-tooling: eight files made efficient (OR39), e.g. the error catalog 34.7 → 8.5 s.
- REG:689 ci-tooling: CPython's cyclic GC off during one host parse; no MicroPython heap involved.
- REG:690 ci-tooling: the gate's reds root-caused; a script dependency pinned.
- REG:694 docs-records: the retry bullet loses its incident history (current state, not history).
- REG:695 process: ordering, with the owner's "Go on, don't wait!".
- REG:696 ci-tooling: the toolchain re-recorded; the only difference is the build date (`py/makeversionhdr.py`).
- REG:697 process: four code lanes with disjoint sets.
- REG:698 ci-tooling: merge-tree fixes; the tools equal the pins.
- REG:699 process: next-holder routing (its OF-215 line depends on D1).
- REG:700 ci-tooling: 21 lane deviations, recorded and accepted.
- REG:701 process: nothing written where nothing was needed (L1).
- REG:702 ci-tooling: three files made efficient; small residual growth.
- REG:703 process: routing at the close; stalled downloads bounded.
- REG:704 (1) ci-tooling: the html-validate check skips without `node_modules` and runs where it is required.
- REG:705 (1) ci-tooling: the probe's executable bit guarded over every step.
- REG:711 security: the history scan's dispositions; the bench throwaways fall under the owner's "Such temp
  credentials are usually generated".
- REG:712 security: secret scanning left as configured.
- REG:714 process: three lanes, disjoint.
- REG:716 security: one pointer fixed (the vacuity guard is part of the check noted under REG:710).
- REG:717 ci-tooling: the owner's retry rule implemented across the tiers; three counts tagged (OR30).
- REG:718 process: two twin-fidelity gaps sent to the file's next holder.
- REG:719 ci-tooling: the review's defects fixed; suite hooks not retried (the pinned vitest).
- REG:723 memory-gc: the rig's GC mark stack at 1,024 entries.
  - It is time-only by mechanism: an overflowed push stays marked and is re-scanned (`py/gc.c:574-582`, `:620-639`,
    v1.29.0, read here).
  - It is OR39's "architectural efficiency gain"; the board's 64 entries are measured first (OF-219).
- REG:725 tests-unit: measured growth for new cases (Run 12's two launches avoid a 4 s race); its errcount and
  shell-refusal cases follow D1 and FORM REG:731.
- REG:726 process: an uncalled library method carried with its provenance note.
- REG:727 process: routing at the close (its OF-215 line depends on D1).
- REG:730 (1) uart: `UARTComm._allocate()` reports through its level-gated `err()`, an existing logger (P7).
- REG:730 (3) uart: the delimited read returns one slice (one copy where it made two); I2C/SPI `deinit()` returning
  True gets a comment and no branch (F.5.1).
- REG:736 process: the review's findings checked and fixed inside the unit.
- REG:737 webserver-rest: `ResetErrors` refused whole during a reset decision or a FRAM pause, the owner's fix-now
  direction applied to the RAM-only logs.
- REG:738 (3) tests-unit: the hammer's disarm and the recorded prints asserted.
- REG:740 (3) memory-gc: the gc site checker's three small fixes; the checker enforces OR39.a.
- REG:742 docs-records: each fix's doc line.
- REG:743 ci-tooling: repo-wide scans per lane after three missed reds.
- REG:744 core-logging: OF-221 routed as "a seen-failing test first, a fix only if it fails" (L2); its U35 fix is a
  counterpart (§7).
- REG:747 (1) memory-gc: the soak's stale-root pin fixed in the test (a `gc.collect()` baseline, OR39.a); the UART soaks
  swept first.
