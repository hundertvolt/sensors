DR1 decision review, written by the part (Wed Oct 28 11:52:44 UTC 2026)

# DR1: the review page's planning decisions, re-checked against the refined picture

Scope: the 364 planning decisions of the A-C review page (`inputs/DR1_review_decisions.tsv`, full items in
`inputs/decisions.json`), checked against the refined picture (`picture/PICTURE.md` sections 2, 4, 7, 8), the second pass
(`scan2/SCAN2.md` and its part files), the first scan (`scan_pub/REPORT.md`, rows `A.md`-`F.md`), the owner's record
(`PROJECT_AUDIT_PLAN.md` at `11b66cd8`, OR rows; `recovered/owner_rulings_after_LN118.md`; `inputs/answers.json`) and
the review page's own replies (`audit/review/page_extra.json` at `11b66cd8`: `replies`, `answered_in_chat`). Static
checks only: `git show`/`git grep` at `11b66cd8` (product tree as at `497b3eda`), the pinned MicroPython v1.29.0
source. Nothing was run; nothing in the repo or the earlier scan files was changed.

How the owner's words reach this set, beyond the 68 answered items:
- **OR140** (2026-10-02) records the page's answers: "45 fine, 5 change, 18 with a question or an addition; the routine
  group left unanswered". All 296 unanswered items are routine.
- **OR141** (2026-10-05), the owner in the conversation: "Concerning the answers to my questions: do all as you
  suggested, especially for the multiple choice questions - keep keys in the device files, and UART in the DMA ring
  buffer, but keep a strict eye on how that integrates with the heap allocation and fragmentation; to the usual unit
  tests also add hammering and concurrent load tests, and think about how we can test the interrupts off situation
  without actually writing the flash." This adopts the page's replies to the five question-notes (`replies` in
  `page_extra.json`) and the four chat choices (`answered_in_chat`: "Keep in the device files", "DMA receive ring",
  "Firmware graph only, named exceptions", "Keep it literal").
- **The Wi-Fi settlement** (owner, 2026-10-28): "We thoroughly discussed the WiFi issues and I decided everything
  already." It covers the Wi-Fi behaviour rows (form only).
- **"The OK in the review stay valid."** (owner, 2026-10-28) covers the 45 "ok" ticks.

Verdicts follow the brief. A row tagged "form only" is OWN with a smaller form of the same behaviour noted; it is not
counted as FORM. The 296 unanswered rows are agents' decisions; 7 of them turned out to be covered by the owner's words
(OR141's chat choices, OR23, OR78, the Wi-Fi settlement) and are OWN.

## 1. Counts

Decisions: 364 (all rows; none is a bare fact). Facts: 0.

| verdict | rows | of them answered on the page |
|---|---|---|
| OWN | 75 | 68 |
| SAME | 255 | 0 |
| FORM | 7 | 0 |
| DIFF | 10 | 0 |
| OBS | 10 | 0 |
| SUP | 7 | 0 |
| CHECK | 0 | 0 |
| all | 364 | 68 |

OWN = the 68 answered rows (45 ok, 18 ask, 5 change) plus 7 routine rows that the owner's words cover. 11 OWN rows carry a "form only" note: c-stack-reboot, failed-push-no-flash-write, system-command-sequence-details, led-request-internal-queue, http-head-limits, ntp-synced-goes-stale, uart-flash-erase-overrun, website-unattended, website-display-details, driven-time-and-rtc-steps and twin-first-for-instruments.

Per review-page topic:

| page topic | OWN | SAME | FORM | DIFF | OBS | SUP | CHECK | all |
|---|---|---|---|---|---|---|---|---|
| system-and-memory | 10 | 25 | 0 | 4 | 1 | 3 | 0 | 43 |
| sensors-and-drivers | 12 | 17 | 2 | 2 | 2 | 0 | 0 | 35 |
| network-and-rest | 17 | 12 | 0 | 2 | 0 | 1 | 0 | 32 |
| uart-link | 1 | 8 | 0 | 0 | 1 | 0 | 0 | 10 |
| website | 6 | 3 | 0 | 0 | 0 | 0 | 0 | 9 |
| device-config-and-buildgen | 3 | 10 | 0 | 0 | 0 | 0 | 0 | 13 |
| build-chain-and-ci | 8 | 44 | 3 | 2 | 0 | 0 | 0 | 57 |
| tests | 2 | 60 | 1 | 0 | 0 | 2 | 0 | 65 |
| hardware-tests | 6 | 24 | 0 | 0 | 0 | 0 | 0 | 30 |
| digital-twin | 1 | 25 | 0 | 0 | 0 | 1 | 0 | 27 |
| documentation | 5 | 22 | 1 | 0 | 1 | 0 | 0 | 29 |
| execution-and-release | 4 | 5 | 0 | 0 | 5 | 0 | 0 | 14 |

Per crosswalk topic:

| topic | OWN | SAME | FORM | DIFF | OBS | SUP | CHECK | all |
|---|---|---|---|---|---|---|---|---|
| buildgen-toml | 3 | 8 | 0 | 0 | 0 | 0 | 0 | 11 |
| bus-i2c-spi | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| ci-tooling | 6 | 34 | 3 | 2 | 0 | 1 | 0 | 46 |
| config | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 5 |
| core-logging | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 8 |
| docs-records | 2 | 27 | 1 | 0 | 1 | 0 | 0 | 31 |
| driver-bmp3xx | 1 | 4 | 0 | 1 | 0 | 0 | 0 | 6 |
| driver-isl29125 | 1 | 3 | 1 | 0 | 1 | 0 | 0 | 6 |
| driver-other | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| driver-scd30 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 4 |
| driver-sgp40 | 5 | 4 | 0 | 0 | 0 | 0 | 0 | 9 |
| error-catalog | 0 | 3 | 0 | 1 | 0 | 1 | 0 | 5 |
| generated-code | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 4 |
| led-notification | 1 | 2 | 0 | 0 | 1 | 0 | 0 | 4 |
| licensing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 |
| memory-gc | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| ntp-dns | 5 | 8 | 0 | 0 | 0 | 0 | 0 | 13 |
| process | 1 | 4 | 0 | 0 | 5 | 0 | 0 | 10 |
| release | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 5 |
| security | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 |
| storage-fram | 0 | 2 | 0 | 0 | 0 | 1 | 0 | 3 |
| supervisor-reset-watchdog | 4 | 4 | 0 | 1 | 1 | 1 | 0 | 11 |
| tests-hardware | 8 | 28 | 0 | 0 | 0 | 0 | 0 | 36 |
| tests-unit | 1 | 60 | 0 | 0 | 0 | 2 | 0 | 63 |
| timing-waits | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 3 |
| twin | 2 | 28 | 1 | 0 | 0 | 1 | 0 | 32 |
| uart | 1 | 8 | 0 | 0 | 1 | 0 | 0 | 10 |
| webserver-rest | 8 | 4 | 0 | 1 | 0 | 0 | 0 | 13 |
| website | 6 | 5 | 0 | 0 | 0 | 0 | 0 | 11 |
| wifi | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 6 |

Per picture line: L1 38, L2 19, L3 13, L4 123, L5 65, L6 19, L7 61, L8 26. Rows marked misfit: 10 (stall-bounds, setup-returns-bool, one-timeout-mechanism, float-sleep-everywhere, new-dns-ntp-errnos, webserver-start-retry, bmp-conversion-wait, i2c-scratch-view, ci-budget-margin, harness-timeout).

## 2. DIFF rows (10)

### system-and-memory

**stall-bounds** — topic timing-waits; line L2 (misfit)
- As taken: routine product computation may hold the loop at most the 21 ms garbage-collection term, and an I2C bus
  timeout stays below half of the device's smallest hard consumer (enforced at build).
- New answer: keep the 21 ms term as timing knowledge (Part F.3). Drop the I2C half as a build rule
  (`bus.i2c-timeout-consumer`) together with its `smallest_hard_consumer()`/`HardConsumer` export. The I2C timeout
  stays held by one existing bound: the per-bus ceiling or the boot-clear budget (S2-G3-1 keeps one of the two).
- Basis:
  - S2-G3-2, by arithmetic from the src constants and probes on modified TOML copies. The watchdog branch allows
    3,000,000 µs against the 200,000 µs ceiling, so it never binds. Only dev's uart_link slack can bind, once
    `poll_idle_ms` exceeds about 575 ms; the pre-audit `bus.uart-timeout-floor` fires near 975 ms.
  - CLAUDE.md's hard rule: "For a genuinely wedged I2C bus/sensor, the hardware watchdog is the accepted backstop".
  - The bound's own tag reads "agent, 2026-10-21" (`buildgen/validate.py:618`).
- Changes (estimate):
  - `buildgen/validate.py`: −17 lines for the check and its rule row.
  - `smallest_hard_consumer()`/`HardConsumer` (~15 lines): move to a test helper, or go with the twin loop-lag
    scenario and the two bench tests that read it.
  - Records: the error-contract test row and Part N's row. A dev-only bound for the link, if wanted, is the owner's
    call (S2-G3-2).

**setup-returns-bool** — topic supervisor-reset-watchdog; line L6 (misfit), L5
- As taken: every class's `setup()` returns True or False, the Wi-Fi service and the web server included, "so the one
  setup runner treats every module alike".
- New answer: `setup()` keeps the pre-audit `None`. A bool only where product code reads it: `UARTComm.setup()`,
  read by `UARTLinkDriver.setup()` on dev (G4b closure). The logger set up first inside the boot batch (A-B16) stays.
- Basis:
  - S2-G1-10 (grep): `run_setups()` discards every answer (`asy_system_service.py:743`, `await setup()`), and so does
    every in-driver call.
  - The one other G1 reader is the lost-chip watch (A-D1, H); 23 test files await the result.
  - OR36 (owner, 2026-09-26): "contains zero artifacts specifically added for testing, neither functions, nor specific
    variables".
  - The decision's own reason does not hold at head: the runner never reads the result.
- Changes (estimate):
  - ~19-22 return lines and annotations in 19 G1 methods, plus the `ok =` chains (notification, Wi-Fi).
  - SPEC C.13's "One contract ... returns `bool`" sentence.
  - `setup-function-type` goes with it (OBS); the tests that assert the bool.

**one-timeout-mechanism** — topic timing-waits; line L2 (misfit)
- As taken: every wait that can be bounded uses one helper, `wait_for_ms`.
- New answer: one helper, yes, but only for a wait that a verified condition needs to bound. A wait on this program's
  own tasks stays unbounded, with the watchdog behind it, as `fram-waits-unbounded` already reasons (SAME).
- Basis:
  - C.md NP-5: wrapping the NeoPixel flag wait in `wait_for_ms(flag, 300000)` lost a shutdown cancel, 8/8 on the
    pinned Unix port. The timeout path cancels and awaits its runner (`extmod/asyncio/funcs.py:47-50`, v1.29.0).
  - B UDP-4 and REPORT §4.6: moving `ready()` onto `wait_for_ms()` lost a cancel too; the redo moved it back.
  - Owner (2026-10-28): "hardcoded delay checks like this are a very bad, very awkward pattern".
- Changes (estimate):
  - The rule's text in SPEC D.4/F.3 narrows.
  - Code: only the reverts already on the cleanup list: NP-5 (−5 lines, back to the pre-audit `await ...wait()`),
    UDP-4 (−~12) and WS-6's bound on the refusal arm (S2-G2-7). Nothing new.

**float-sleep-everywhere** — topic memory-gc; line L2 (misfit), L6
- As taken: the whole-millisecond sleep rule (no float per sleep call) covers every sleep in the firmware, not only
  recurring ones, so its check needs no exception list.
- New answer: no extension to one-off sleeps. At most the rule applies to waits inside loops; it may also be only a
  D.4 note without a gate. Already converted sites stay; reverting them would be churn.
- Basis:
  - OR110 (owner): forbidden are objects that "reside in the heap forever ... and which can grow"; "If a timer
    allocates, never reaches any critical value and frees some seconds later, it's less critical".
  - The cost is a short-lived float. `extmod/asyncio/core.py:62-63` (v1.29.0) is `return sleep_ms(int(t * 1000))`,
    and rp2 floats are heap objects (REPORT V4: `MICROPY_OBJ_REPR_A`).
  - PICTURE M7; REPORT §8's row "allocation cuts for temporaries you had accepted (OR110)".
- Changes (estimate):
  - The scope of `tests_scripts/test_src_sleep_forms.py`'s float half (one-off sleeps out, or the half dropped).
  - SPEC D.4's sentence. No firmware edits.

### sensors-and-drivers

**bmp-conversion-wait** — topic driver-bmp3xx; line L1 (misfit)
- As taken: the BMP3XX conversion wait is computed from the datasheet's measurement-time formula. That means one OSR
  register read per conversion and a sleep of the typical time, then the STATUS poll.
- New answer: keep the pre-audit STATUS poll (2 ms steps, 300 ms bound).
- Basis:
  - C.md BMP-3 (H): "the pre-audit poll (2 ms steps, 300 ms bound) worked; this trades bus polls for a read"; legacy
    polls STATUS every 2 ms too. The new form adds a bus read per cycle and a raise for reserved encodings.
  - Owner (2026-10-28): "Firmware state at the beginning was already quite solid ... the way it flows into the
    firmware and buildgen is *really* minimal change."
- Changes (estimate): `asy_bmp3xx_driver.py:504-510` back to the pre-audit wait (−~9 lines), its tests, and the
  register row "BMP3XX's seconds-form conversion wait".

**i2c-scratch-view** — topic bus-i2c-spi; line L2 (misfit)
- As taken: I2C register reads slice one long-lived view of the scratch buffer, and whole-buffer transfers pass the
  buffer directly.
- New answer: keep the pre-audit per-read view. The whole-buffer pass-through stays only where it is not more code.
- Basis: C.md I2C-9 (H): "the saved objects are short-lived temporaries", one 16-byte memoryview per register access,
  scheme OR110; OR110 as above; PICTURE M7.
- Changes (estimate):
  - `asy_i2c_driver.py`, ~16 lines (`:137, 192, 216-218, 245-252, 380-383, 429-431, 487-488`).
  - I2C-6/7's NACK fixes (confirmed gaps) touch the same functions and stay.

### network-and-rest

**new-dns-ntp-errnos** — topic error-catalog; line L1 (misfit)
- As taken: a captive DNS bind failure logs error 10 (INIT); an NTP request that could not be sent logs new error 72.
- New answer: no E72. A request that could not be sent ends in the existing no-reply path, as before the audit, at
  the cost of one reply wait. E10 for the bind failure stays: a 3-line mislabel fix (CD-4, K).
- Basis:
  - B NTP-4 (K): "implausible as a failure: a wrong log code by reading, plus one 5 s wait saved"; its simplest
    alternative is the pre-audit `write_and_recvfrom()`.
  - G2's families table, "a send's result checked: DNS :167-168 (DNS-4 H), NTP :269-271 (NTP-4 K)": none needed, "the
    reply wait already ends the try".
  - Owner (2026-10-28): "really minimal change".
- Changes (estimate):
  - NTP's send check and its E72 site (~3 lines); DNS-4's per-try send check in the same family (~8 lines).
  - Catalog row 72, which becomes a tombstone under the agent's never-reuse rule (S2-G4X-6).

**webserver-start-retry** — topic webserver-rest; line L3 (misfit), L2
- As taken: if the server cannot start listening, it retries 3 times, 5 s apart, before its task ends. The stated
  reason: the attempts span one 10 s close linger, "so a passing condition no longer costs a restart".
- New answer: one start. On failure the task ends and the supervisor restarts it, as before the audit
  (`asy_webserver_service.py@25caf528:733-739`).
- Basis:
  - S2-G4-11, checked here against the pinned source: the premise is refuted. `extmod/asyncio/stream.py:186` sets
    `SO_REUSEADDR` on every server socket, and rp2's lwIP builds with `SO_REUSE 1`
    (`extmod/lwip-include/lwipopts_common.h:75`), so a restarted task binds at once.
  - No start failure was ever recorded (B WS-11).
  - The owner's words: "hardcoded delay checks like this are a very bad, very awkward pattern" (2026-10-28); OR18.a
    "keeping it contained going so far may miss that opportunity".
- Changes (estimate): `_START_RETRIES`, `_START_RETRY_S` and the loop (`asy_webserver_service.py:171-175, 970-992`,
  ~19 lines), W62 (catalog line 174, then a tombstone), and their tests.

### build-chain-and-ci

**ci-budget-margin** — topic ci-tooling; line L4 (misfit), L8
- As taken: each CI job's budget is the larger of its cold and warm wall clock plus retries, plus 25 %, rounded up to
  5 minutes.
- New answer: a job budget near the measured run plus a fixed margin, with the retries bounded inside it, so that a
  hang is named within minutes of a normal run. The per-file timeout and retry stay the hang backstop (CLAUDE.md).
- Basis:
  - E.md .github: `unit-tests` and `unit-tests-gc-threshold` went from 45 to 175 minutes for a warm 9-10 minute run,
    and "a hung job runs for two hours before it is named" (3 × 2,555 s ≈ 128 min).
  - OR39: "Look for opportunities for speeding up the test suite"; REPORT §9: the hang rule "holds in letter only".
- Changes (estimate): the `.github/workflows/ci.yml` timeouts; Part N's CI rows (SPEC:13318, :13331). No product
  change.

**harness-timeout** — topic ci-tooling; line L4 (misfit), L8
- As taken: the harness job timeout starts at five times its first measured run and is re-measured later.
- New answer: a small multiple of the slowest measured run, as a starting value to re-measure, and few attempts.
- Basis: E.md .github: "The 2,555 s per attempt is 5× the slowest CI run (511 s)"; three attempts make about
  128 min. The same owner words as `ci-budget-margin`.
- Changes (estimate): the harness jobs' timeout and retry values in `ci.yml` and Part N. No product change.

## 3. OBS rows (10)

| id | page topic | root the cleanup removes (scan row) | topic |
|---|---|---|---|
| setup-function-type | system-and-memory | `setup()` widened to bool with no product reader (S2-G1-10); goes with DIFF `setup-returns-bool` | supervisor-reset-watchdog |
| notification-setup | sensors-and-drivers | bool half: S2-G1-10. Its other half, a constructor refusal persisted at `setup()`, is the general pattern (SPEC C.13) and stays | led-notification |
| isl-int-rearm-reset | sensors-and-drivers | ISL29125's dead-INT re-arm, H: "unobserved ... a quiet INT line is no error the ladder sees" (S2-G1-23, ISL-2) | driver-isl29125 |
| uart-log-codes | uart-link | UC-8 (X): construction re-checks dev's UART values that buildgen already refuses (S2-G3-4); E91/E92 are on S2-G3-7's list of codes that exist only for an H/X/C mechanism. The "91 read as a slip for 89" note stays a record fact | uart |
| hang-cause-phrase-kept | documentation | the citation gate `tests_scripts/test_citations.py` and its allow-list: docs as checked data (F.md §3); "permanent CI that came out of audit rules" (E.md tests_scripts, (b) docs policing), against the owner's "The audit verification machinery is just a temporary tool" | docs-records |
| unit-packet-lists | execution-and-release | the audit's execution apparatus in `audit/` (work order, unit packets), temporary and removed at phase D: "Nothing outside it depends on it" (F.md §4) | process |
| citation-rescan-merges | execution-and-release | as above (the dependency-refresh citation re-check) | process |
| sites-by-symbol | execution-and-release | as above (two audit checks that locate code by symbol) | process |
| unowned-files | execution-and-release | as above (which audit cluster owns `legacy/`, `dev_legacy/`, `.gitignore`) | process |
| work-order-placements | execution-and-release | as above (the work order's unit placement of two changes) | process |

## 4. FORM rows (7)

| id | page topic | the smaller form | scan row | topic |
|---|---|---|---|---|
| scd30-always-tuple | sensors-and-drivers | one source: buildgen reads the firmware tuple by AST and emits the website's flag, instead of a mirrored `alwaysExecuted` tag kept equal by a host check | D-H27 R ("Build reads `src/` facts by AST instead of mirrored constants"); E.md tests_scripts, P8 ("checks keep copies equal instead of generating them") | driver-scd30 |
| isl-counts-check | sensors-and-drivers | a typing-side narrowing (a cast; product code carries no assert) instead of a runtime branch at `asy_isl29125_driver.py:1492` ("narrows the Optional; a fixed 6-byte buffer always decodes") | S2-G4-22 (the family); SCAN2 §9 | driver-isl29125 |
| ci-mypy-scope | build-chain-and-ci | CI calls `scripts/typecheck.sh`, or reads the config's own file list, so no copy exists that a test must keep equal | E.md tests_scripts, (b/d) lint and tool gates; P8 | ci-tooling |
| port-lock-reader | build-chain-and-ci | one lock implementation that the sh, py and js runners call, instead of `.sh`, `.py` and `.js` copies (`tests_js/_port_lock.js`, 402 lines) kept equal by tests | E.md scripts/ and tests_js/, P8 | ci-tooling |
| marker-copy | build-chain-and-ci | one memory-error marker list that all four gates read, instead of a harness copy held equal by `test_memory_error_gate_agreement.py` (plus `tests_js/_memory_markers.js`, 174 lines) | E.md tests_js/, P8 | ci-tooling |
| host-check-d-tsc2 | tests | one board fake for both tiers (or the twin fake as a thin layer over the unit fake), instead of two fakes held equal by `_machine_contract.py`, `_mem_backup_contract.py` and `test_fake_surface_conformance.py`; CLAUDE.md's mypy facts decide where the fakes live, not how many there are | E.md tests/ and digital_twin/, P8 | twin |
| readme-order | documentation | the section order as a one-time edit, without a permanent host gate on the document map | E.md tests_scripts, (b) docs policing | docs-records |

## 5. OWN rows (75)

Source for every "ok": the tick on the review page (2026-10-01/02, `audit/review/answers.json`) and "The OK in the
review stay valid." (owner, 2026-10-28). The "ask" and "change" notes are quoted verbatim. "Follows" means that what
was built at `11b66cd8` matches the owner's words. Where a smaller form of the same behaviour exists, it is noted as
"form only".

### system-and-memory (10)

- **c-stack-reboot** (ok). Follows: `report_if_fatal()` at 123 sites, the supervisor's reboot with code 20 / E25, and
  the await-depth host test.
  - Form only: one check in the logger's `_line()` plus 4 explicit calls and a 3-4 line Microdot hook; about 118
    lines go (S2-G4-1; SCAN2 §3).
  - Form only: the flag writes that no reader sees any more (S2-G4-2).
  - Form only: the 1,200 ms bound on the escalation's entry write goes (S2-G1-6; SCAN2 §7.4).
  - The approved "host test fails if the chain grows past a pinned depth" landed as `_await_depth.py`, 909 lines plus
    a 207-line test (E.md: excessive).
  - Still owed: the board's peak reading (REPORT §7.1) and the logger-side check on the Unix port (SCAN2 §8).
- **unreadable-config-file** (ask). Note: "As discussed and stored here: "Damaged config files (OR138)"". OR138
  (owner): "Unreadable or damaged files should be visible in some status field, not silently swallowed. And even such
  files must be deletable by the user when triggering the newly added "delete config" command."
  - Follows: A-C1 (never overwritten, writes refused until the next boot), A-S24 (`ConfigFaults` in /status) and
    A-C15 (`delete_file()` without reading the file).
- **timestamps-before-ntp** (ok). Follows (A-B5, D-G19).
  - After an NTP settings change the two clock-valid flags answer differently (S2-G4-15). SCAN2 §9 leaves that
    unchanged as the conservative choice.
- **humidity-helpers-removed** (change). Note: "Keep them, they are also one of the kind "useful, complete the
  functional suite, small, lightweight. Adapt the tests to be in line with the others."
  - Follows: both helpers stay (SPEC's "Derived quantities" bullet), and their tests are aligned.
  - **Small gap:** `rel_humidity()` now refuses a result outside 0-100 % instead of clamping (A-H3). It needs a
    0.001 % allowance for a saturated reading (A-H4, a cascade).
    - The change rests on OR140.a (4)'s integrated text, "and the helpers with the no-clamp rule", and on the
      pre-audit D.7 note about clamps. The owner's note does not say it.
    - It changes real output against legacy (`legacy/firmware/python/CommonDrivers/math_helpers.py:65-66` clamps).
    - No product caller reads it today (A.md's minimal list).
- **system-command-words** (ok). Follows (WS-12).
- **system-command-sequence-details** (ask). Note: "Sounds fine, only it should also be ensured that no more writing
  commands are being sent to the SCD30 during reset. Actually, this should already be the case due to the rules "only
  write to SCD30 triggered by API commands" and "reject any API command while waiting for the reset". This mechanism
  is good enough, only make sure it's working watertight."
  - Follows: once a command is accepted, every PUT key answers Failed (A-B9).
  - A twin test pins it: `tests/test_digital_twin_bus_hazard_concurrency.py:1245`,
    `test_no_scd30_write_reaches_the_chip_while_a_system_command_runs`.
  - No new mechanism was added, as the owner said. Form only: the path's six reset flags and its repeated
    close/flush layers (S2-G1-12, S2-G1-13).
- **reset-reason-codes** (ask). Note: "Good, and make the numbers clickable in the website like the errno and wrnno
  numbers."
  - Follows: `buildgen/definitions.py:632-633` makes ResetReason a readonly field with its code table, clickable.
  - Codes 21/22 were added later (register SF-A14); the loop-end labels are a confirmed gap (SCAN2 §5).
- **failed-push-no-flash-write** (ok). Follows: the deferred flush is this decision's mechanism (SCAN2 §7.1).
  - Form only: one `write_config()` after the push loop; about 30 lines go and about 3 stay (S2-G4-16, S2-G1-14).
- **one-entry-per-fault** (change). Note: "It should rather stay as is, upstream layers reacting to a downstream fault
  may encounter following errors going above the original fault, so getting a notion of a traceback and blast radius
  of an error is actually desirable."
  - Follows: SPEC:3657 at `11b66cd8` reads "Every layer that meets a fault keeps its own persisted entry (owner,
    2026-10-02 ...)", and OR140.a (7) drops the planned change.
  - The routine `uart-resync-one-entry` does not touch it: within one log, one occurrence is never both a fault and a
    warning (owner OR56 (1)).
- **ntp-sync-last** (ok). Follows (D-G3).

### sensors-and-drivers (12)

- **sgp40-wait-zero** (ok). Follows (SGP-8).
- **scd30-calibration-readiness** (ok). Follows (SCD-1). The three defaults stay provisional; their measurement is
  owed.
- **led-request-internal-queue** (ask). Note: "Fine, and this for a reason: internal LED commands are guaranteed to be
  bounded by number and frequency, they won't flood the device. External commands might quickly flood it into
  exhaustion. The refusal and error message lets the external caller knows to try again later."
  - Follows: an external command is refused while busy, with "busy, retry later" (WS-17). An internal request waits
    for the running signal, bounded by `_SIGNAL_WAIT_MS` = 120 s (`asy_neopixel_driver.py`).
  - The deadline is in the approved text (SCAN2 §7.2). The 120 s value is the agent's (C.md NP-2). Its intended
    basis is the kept hand measurement, "the longest LED ramp (sets the deadline the LED request waits for)" (page
    reply, adopted by OR141).
  - Form only: W67 and the default-sink identity test go (S2-G1-17, S2-G4-9).
  - Record fact: the approved text says the request "waits for the running signal up to a deadline and then queues".
    The code drops it at the deadline ("Internal LED command dropped: signal still busy."). Nothing in the approved
    text names a drop.
- **threshold-rewrite-failure** (ok). Follows.
- **pres-offset-warning** (ok). Follows (BMP-6).
- **state-code-values** (ok). Follows (SGP-1, ISL-4). The approval names the SGP40 and ISL29125 fields only; the
  notification `State` codes are not covered (S2-G4X-2).
- **scd30-write-path** (ok). Follows.
- **stale-as-fresh-every-driver** (ok). Follows. The SCD30's re-stamp stays the named exception (SCAN2 §8.7).
- **sgp40-chip-identity** (ok). Follows (SGP-6).
- **negative-backup-age** (ok). Follows (SGP-9).
- **voc-port-order** (unanswered on the page). The owner's chat choice "Keep it literal" (2026-10-05, `answered_in_chat`
  voc-literal-port) and OR141; OR141.a (3). Follows.
- **voc-literal-names** (unanswered on the page). The same source. Follows.

### network-and-rest (17)

- **rest-key-scheme** (ok). Follows. No key migration exists (S2-G2-6: `NTP_Host` → `NTPHost`); that fits the
  approved reflash runbook, which erases the filesystem on the move.
- **rest-api-frozen-at-release** (ok). Follows (D-H7).
- **wifi-off-led-pattern** (ask). Note: "Generally fine, and as discussed already, this shall respect the general WiFi
  LED setting (stay silent if turned off, apply whatever current pattern when turned on)". Follows: WF-9 "obeying
  LEDWifiOn". Wi-Fi is settled.
- **api-unknown-key-invalid** (ok). Follows (WS-16).
- **lwip-retry-on-full-queue** (ok). Follows (the modlwip send-path patch, owner 2026-09-30, E.md toolchain/).
- **http-head-limits** (ok). Follows (WS-1).
  - Form only: WS-2's further refusals and WS-9's dedupe go; a 3-4 line Microdot rebind stays for the C-stack report
    (S2-G2-8).
- **static-no-cache** (ok). Follows (WS-8).
- **status-fields-added-and-left-out** (ask). Note: "Sounds good, and handle the dropped Http connections the same way
  as the dropped (general) connections, as we already discussed - last 24h with 24 counter buckets, no dynamic
  allocation and capped counters."
  - Follows: `HTTPDropped` runs on the hourly window counter (A-B3: one fixed 24-entry array, capped; WS-4; OR137.a),
    and `WifiTS` is in (D-G13).
  - Tension, recorded in section 7: the approved left-out list keeps notification internals out of /status; the later
    `State` key (D-G22, H) went in.
- **deactivated-snapshot** (ok). Follows. Wi-Fi is settled.
- **ntp-synced-goes-stale** (ok). Follows (NTP-11).
  - Form only: the cadence chain's two `TickSeconds` go, and NTP-11 runs on `_sync_age` alone (S2-G4-13; G2 keep
    list).
- **ntp-no-origin-check** (ok). Follows; it fits L2.
- **dns-fallback-setting** (ok). Follows (NTP-2, DNS-2).
- **hotspot-redirect** (ok). Follows.
- **envelope-codes-equal-http** (ok). Follows (A-A2, WS-24).
- **idle-poll-rate** (ask). Note, a question: "What is the general background of this, and how and where is the rate
  specified and validated?" It is no approval.
  - Answered by the page reply: one named value in the module, a row in the spec's settings table, and unit tests for
    20 ms against 100 ms. The reply also corrects the item: "the 100 ms is a reasoned choice ... not yet measured".
  - The owner then adopted the replies: OR141 "do all as you suggested" (2026-10-05); OR141.a (5).
  - Follows: `asy_udp_socket.py:34-36` (`_POLL_IDLE_MS = const(100)`), Part N `udp.poll_idle_ms` (SPEC:12097),
    UDP-3. Its measurement is still owed.
- **wifi-led-default-unreadable** (unanswered on the page). Covered by "We thoroughly discussed the WiFi issues and I
  decided everything already." (owner, 2026-10-28). WF-9. Follows.
- **hotspot-task-restart** (unanswered on the page). The same source. Follows.

### uart-link (1)

- **uart-flash-erase-overrun** (change). Note: "On which kind of flash erase could that happen? Just normal config
  writing or only during the full reset to defaults? In either case, this should not happen as a random side effect.
  Either don't lose a frame in general (preferred, if achievable with adequate effort), or halt the UART in some way
  for the time it takes (feels like a workaround only, though). Come back at me for this."
  - Answered on the page: any flash write, 45-400 ms with interrupts off.
  - Owner's choice in the conversation: "DMA receive ring" (2026-10-05), with its note, restated in OR141 as quoted
    above.
  - Follows: UD-1 (two chained DMA channels, RX interrupt off), UC-12, UC-13.
  - The interrupts-off bench script (OR141.a (4)(g)) is written and twin-run, not yet run on silicon (E.md
    tests_hardware).
  - Form only: about 11 lines of protection for states no product path creates (S2-G2-11).

### website (6)

- **website-unattended** (ok). Follows.
  - Form only: the OF-144 page build-date stamp, about 18 lines, H, an order-2 chain on this decision (S2-G3-14).
  - Form only: the device watch's extra /status (S2-G3-16, about 2 lines).
- **website-accessibility** (ask). Note: "Fine, and make the "back" function of the browser work. Currently, clicking
  through the menu / the pages leaves no history, and a "back" immediately exits to the website visited before ever
  opening the sensor page. I want "back" to move backwards through the sensor subpages openend through the menu as well
  (actually the most intuitive way)"
  - Follows: `js/shell.js:37-41` pushes a history entry per section and listens to `popstate`.
  - The inert drawer and the AA tokens are built; the contrast change is OR132 "2a".
  - `accessibility.test.js` pins them (E.md keep).
- **dns-fallback-clear-confirm** (ask). Note: "Fine, and add a dialog to all system commands and the clear error
  history as well. But only on the website, not on the API side. The API stays single command."
  - Follows: `"confirm": True` on SystemCmd (`buildgen/definitions.py:63`) and on ResetErrors (`:92`).
  - `js/render.js:238` asks before the Clear, and `:303` before each confirm field. The API is unchanged.
- **apply-failure-marks-fields** (ok). Follows.
- **favicon-inline** (ok). Follows.
- **website-display-details** (ask). Note: "Fine, and maintain a reasonable number of digits per value (e.g. limit to
  2 or 3 digits behind the decimal point, don't print full floats). But only for the website, the API delivers full
  resolution. Configured in the website config file, derived or defined from the value sourcing modules (e.g. Schema or
  inside the commented configs)."
  - Follows: `decimals=` in the drivers' `@web` tags (for example `asy_isl29125_driver.py:182-200`), a site default
    of 2, and the API untouched.
  - The CalLight tone table is this item's. SCAN2 §7.8 overrules S2-G4-18's H.
  - Form only: S2-G3-16.

### device-config-and-buildgen (3)

- **toml-build-metadata** (ask). Note, a question: "Where are these keys actually stored? Come back at me concerning
  this." It is no approval.
  - Answered by the page reply: they live in each device file's `[device]`; the build checks both and never emits
    them.
  - The owner's chat choice "Keep in the device files" (2026-10-05) and OR141 "keep keys in the device files";
    OR141.a (1). Follows.
  - G3's S2-G3-11 called the question unanswered; SCAN2 §6 corrected that.
- **hardware-family-label** (unanswered on the page). The same owner choice. Follows.
- **buildgen-error-form** (unanswered on the page). OR23 (owner, 2026-09-25): "the build always aborts on errors and
  reports them such that a user can easily see what to do as a resolution"; OR23.a "yes to all three". Follows
  (D-H1).

### build-chain-and-ci (8)

- **typecheck-stripper-text-edit**, **comment-cap-long-lines**, **ci-web-filter-base**, **bench-sudo-checked**,
  **no-gcc14-ci-leg** (ok). Follow.
- **stub-versions-pinned** (ask). Note: "Fine, and we need to ensure that this will be updated along with Micropython
  when switching to a newer release."
  - Follows: `toolchain/versions.toml:12-17` (`[stubs]`, with the owner's words) and its checks in
    `scripts/typecheck.sh` and `tests_scripts`.
- **bench-psk-fallback** (change). Note: "the password is a throwaway password used only once, no need for such
  complexity here."
  - Follows: `tests_hardware/README.md:221` reads "The AP's PSK is a throwaway password used once, passed plainly".
- **reproducible-image** (ask). Note: "Fine, but how to handle the difference between the actual build date and
  timestamp? They must differ for being genuine. Apart from that, everything shall be byte-identical."
  - Answered by the page reply: the date is a build input; the reproducibility check builds twice with a fixed date.
    Adopted by OR141.
  - Follows: `test_frozen_inputs_reproducible.py` and `test_buildgen_reproducible.py` (E.md keep). The page stamp of
    OF-144 is a separate agent addition (S2-G3-14).

### tests (2)

- **driven-time-and-rtc-steps** (ok). Follows. Form only: the per-wiring widening of the driven-clock tests runs past
  the owner's ask (E.md tests/, "multiplying tests per device wiring").
- **retry-pass-flagged** (ok). Follows.

### hardware-tests (6)

- **heap-floors-kept**, **standard-board-state** (ok). Follow.
- **standard-state-repair-optin** (ask). Note: "Fine, and if that happens, output a console message telling what
  happened and what options to repair exist."
  - Follows: `tests_hardware/conftest.py:246-255` prints "board not in the standard state:" with what was read, what
    the state holds and the remedy; `--repair-standard-state` (`:105`) is the repair option.
- **console-starvation-bench-test** (ask). Note: "Fine if "a gated bench test" means "only if additional write wear is
  allowed by the flag"."
  - Follows: `tests_hardware/bench/test_network_resilience.py:929` carries `@pytest.mark.persistence_write`.
- **twin-first-for-instruments** (ok). Follows.
  - Form only: the committed `tests_hardware/twin_record.json` and its pin, "logged output committed as source"
    (F.md, other clutter; REPORT §9).
- **bench-board-toml** (unanswered on the page). OR78 (owner): "nothing about the WoZi and Dev build shall remain
  hardcoded at any place anymore", and the chat choice "Keep in the device files" (2026-10-05). The runner override
  is the agent's.

### digital-twin (1)

- **twin-tolerates-ntp-offline** (change). Note: "A local NTP responder is built for the twin, and we can even use it
  for building more unit tests checking the NTP client (the usual functional, error handling, biting coverage,
  regression tests)"
  - Follows: `digital_twin/unixport/_ntp_responder.py:1` ("owner, 2026-10-02"), started by
    `run_generic_integration.py:1141`.
  - NTP tests use it: `tests/test_asy_ntp_client.py` (with `tests/_ntp_frames.py`), `tests/test_digital_twin_ntp.py`
    and `tests/test_digital_twin_clock_jump.py`, which does "a real sync against the local NTP responder".
  - The offline writer stays for boots that must not sync (TEST-NET-1).

### documentation (5)

- **threat-model-table**, **licence-notices**, **operator-actions-one-place** (ok). Follow. A.11's check is a genuine
  contract check (F.md §3).
- **legacy-wip-as-intent** (ask). Note: "If you mean the "improved_quality" folder which we moved to the promoted
  files, and just using what it once contained as a reference unless stated differently, yes." Follows (OR140.a (6)).
- **wozi-move-owner-operation** (ask). Note: "This is a remainder of the promotion process. There is nothing special
  for any of the builds (apart from some well contained exceptions for dev, which is somewhat special). For all normal
  builds, especially WoZi, there are no such specialties and they shall be removed from the docs."
  - **Gap:** WoZi-specific wording remains at `11b66cd8`:
    - CLAUDE.md:191-205: "WoZi is the exemplary/base variant ... it is never bench-tested ... No session ever flashes
      `wozi`";
    - CLAUDE.md:168 ("no session ever flashes or bench-tests `wozi`");
    - README.md:410 ("a session never flashes `wozi`");
    - SPECIFICATION.md:10575 ("`wozi` (the exemplary/base variant, never ...");
    - `devices/wozi.toml:1` ("the exemplary/base device; never physically flashed").
  - The register's U33 row "narrowed to sessions" the two CLAUDE.md sentences, which keeps the specialty. OR140.a
    (18) states the owner's direction: "leftover WoZi-specific wording from the promotion is removed from the docs".
  - Dev's bench rules are the owner's "well contained exceptions for dev" and stay.

### execution-and-release (4)

- **release-version-2-0**, **reflash-runbook-erase**, **release-defined-point** (ok). Follow; the tag is still to be
  made at the close.
- **hand-run-hardware-rows** (ask). Note, a question: "What are these tests good for? Are they conducted only once or
  shall they become part of the general testing? Which added value do we get from them (if any)? This sounds a bit like
  leftovers from a hardware debugging round, if these actions do not deliver any added value, we can completely drop
  them." It is no approval.
  - Answered by the page reply: "These are one-time measurements, not regular tests".
    - Kept: read time per driver, the longest LED ramp, and the recovery-step failure counts.
    - Dropped: the NTP-outage check ("your twin NTP responder covers it") and the image without the 100 ms hotspot
      settle.
  - Adopted by OR141 "do all as you suggested" and OR141.a (5): "the three kept one-time measurements and the two
    dropped".
  - With today's knowledge the three fit L4: one-time, no machinery.

Outside the 364: the go-ahead itself was "withheld" on the page with the UART chunking note (OR143). It was executed as
UC-1/UC-3 (receive cap, PieceBuffer pieces) and is R in the first scan (B).

## 6. SUP rows (7) and CHECK rows (0)

| id | page topic | superseded by | does the later one stand? | topic |
|---|---|---|---|---|
| initialized-flags | system-and-memory | SPEC C.13 (agent, 2026-10-05): only the classes "whose product code reads it" carry the flag; the reader base, web server, NeoPixel, notification and system service carry none (checked: no `self.initialized` in those files at `11b66cd8`) | yes, it fits P4/OR36. Two of its readers sit partly in the lost-chip chain, so `is_ready()` becomes an alias with one user (S2-G4-5) | supervisor-reset-watchdog |
| unpause-waiter | system-and-memory | register U11 SF-A11: "the FRAM mempause auto-unpause becomes a `ticks_ms()` deadline tested on every uptime pass; its one-shot timer, waiter task and flag go" | as built, yes. It is H (A-S21: a dropped soft one-shot is a confirmed mechanism, its frequency is the hardware item HW5); its reset guard is part of S2-G1-12's six flags (form only) | storage-fram |
| dynamic-import-ban | system-and-memory | the owner: chat choice "Firmware graph only, named exceptions" (2026-10-05) and OR142 "Option 1, record the MicroPython sites in F.1. But the places you named so far are all harmless." (OR141.a (2), OR142.a) | yes, the owner's | ci-tooling |
| ntp-malformed-text | network-and-rest | NTP-10 (K): a heap failure while parsing logs E20 apart from E69 (`asy_ntp_client.py:341-342`); E69's text at head is "the reply is malformed" | no: S2-G2-10 removes the split (~7 lines), so this item's single text is the target again | error-catalog |
| unit-test-d-t27 | tests | the fold's correction (M_TEST_UNIT D-T27, F33): a both-busy log read answers False ("read, and no copy usable"), not None | yes: it matches `_FRAMBaseChunk._read()`'s contract at `11b66cd8` (`asy_fram_manager.py:217-219`) | tests-unit |
| unit-test-d-t30 | tests | the redo moved UDP's deadline back into `_poll()` (UDP-4, C), so UDP has a tick site again (`asy_udp_socket.py:106-110`) | no: UDP-4 goes (G2 families, "hardcoded timing checks ... go"), and the item's premise holds again | tests-unit |
| twin-choice-17 | digital-twin | the owner's change on `twin-tolerates-ntp-offline` (OR140.a (13)): the twin syncs against a local responder; `tests/test_digital_twin_clock_jump.py:1-3` does "a real sync against the local NTP responder" | yes, the owner's | twin |

No CHECK rows. Every verdict here rests on source, git, the pinned MicroPython source or the owner record. The open
checks that touch these rows are already on the scans' lists:
- the C-stack peak and the logger-side form (`c-stack-reboot`; REPORT §7.1, SCAN2 §8);
- HW5's soft-callback queue (`unpause-waiter`'s later form);
- the measurement of the 100 ms idle rate and of the SCD30 readiness defaults.

## 7. Contradictions, and the likely counterparts in other sets

### Pairs that cannot both hold (23)

Agent against owner (the owner's words stand):
1. **The routine batch.** The review page's owner step said "silence on a routine batch counts as approval"
   (agent text, `audit/review/decisions.json`, owner_steps `review-and-go-ahead`). Against it:
   - OR140: "the routine group left unanswered";
   - L7 / OR48.a: "recorded decisions I took (not the session agent)".

   Recorded fact for the lead: no owner text adopts the silence rule. OR145's go-ahead approves the execution, not
   the routine items. The 296 routine items stay agents' decisions, as this review treats them.
2. `dynamic-import-ban` (repo-wide) against the owner's "Firmware graph only, named exceptions" (2026-10-05) and OR142.
   The owner stands; built follows (SPEC F.1's named list).
3. `twin-choice-17` ("the offline twin cannot sync") against the owner's change on `twin-tolerates-ntp-offline`. The
   owner stands; built follows.
4. `humidity-helpers-removed` (remove) against "Keep them". The owner stands. Built keeps the helpers; the small
   no-clamp gap is in section 5.
5. `one-entry-per-fault` (one entry) against "It should rather stay as is". The owner stands; built follows.
6. `bench-psk-fallback` (interactive nmcli mode) against "no need for such complexity here". The owner stands; built
   follows.
7. `uart-flash-erase-overrun` (accept a lost frame) against "this should not happen as a random side effect". The
   owner stands; built follows (the DMA ring).
8. `wozi-move-owner-operation` (the WoZi rule binds sessions, a runbook line) against "they shall be removed from the
   docs". The owner stands. **Gap at `11b66cd8`:** the docs keep the wording (section 5).
9. `toml-build-metadata`/`hardware-family-label`: G3's S2-G3-11 rates them H and "still unanswered", against OR141's
   "keep keys in the device files". The owner stands; SCAN2 §6 already corrected it.

Agent against agent (the side the new knowledge supports stands):
10. `one-timeout-mechanism` ("every wait that can be bounded") against `fram-waits-unbounded` (bounded-able waits
    left unbounded, the watchdog behind them). **`fram-waits-unbounded` stands**: two lost cancels came from
    blanket bounding (C-NP-5, B UDP-4), and L2/L3.
11. `setup-returns-bool` (a return value read only by tests) against `test-only-code-removed` (test-only API goes),
    both under OR36. **`test-only-code-removed` stands** (OR36; S2-G1-10).
12. `setup-returns-bool`'s own reason ("the one setup runner treats every module alike") against the code: the runner
    discards every answer (`asy_system_service.py:743`). The code fact stands.
13. `initialized-flags` (every class) against SPEC C.13's later rule (agent, 2026-10-05: only classes whose product code
    reads it). **The later rule stands** (P4).
14. `ntp-malformed-text` (one E69 text for every parse failure) against the later NTP-10 split (E20 for a heap
    failure). **The review item stands** (S2-G2-10: the split goes).
15. `unit-test-d-t27` ("None") against the fold's correction to False (M_TEST_UNIT D-T27). **The correction stands**;
    it matches `_read()`.
16. `unit-test-d-t30` ("UDP keeps no tick site") against the redo's UDP-4 deadline. **The review item stands**: UDP-4
    goes.

Agent against a picture line or owner rule:
17. `webserver-start-retry` against L3 and OR18.a ("keeping it contained going so far may miss that opportunity").
    The same set's `combined-faults-reboot` (escalate, not contain) agrees with L3. **L3 stands** (DIFF).
18. `float-sleep-everywhere` and `i2c-scratch-view` against OR110 (short-lived temporaries "less critical"). **OR110
    stands** (DIFF).
19. `stall-bounds`' I2C half against CLAUDE.md's rule that the watchdog is the accepted backstop for a wedged I2C bus.
    **The rule stands** (DIFF).
20. `bmp-conversion-wait`, `new-dns-ntp-errnos` (E72) and `webserver-start-retry` against "really minimal change"
    (owner, 2026-10-28). **The owner's words stand** (DIFF).

Recorded facts, not to be put to the owner (topics the owner decided):
21. `status-fields-added-and-left-out`, approved "Sounds good", keeps notification internals out of /status ("each
    notification signal's last value and triggered flag"). The later notification `State` key (D-G22, U22, H, no
    owner decision) went in. It is a different field, so this is a tension, not a strict contradiction. The cleanup
    removes the key (S2-G3-8, S2-G4X-2), which restores the approved list.
22. `led-request-internal-queue`, approved "Fine, and this for a reason ...":
    - the approved text: an internal request "waits for the running signal up to a deadline and then queues";
    - the code: it drops the request at the 120 s deadline;
    - the owner's reason: internal requests "won't flood the device".

    SCAN2 §7.2 read the approved text as "bounded" and kept the deadline as the owner's. What happens at the deadline
    is the agent's.
23. `c-stack-reboot` "ok" rests on a hypothetical premise, against L2 (REPORT §6.1). Settled by "The OK in the review
    stay valid." It is form only and not re-asked.

Self-corrected in the record, no conflict left: `idle-poll-rate`'s "why" claimed "measured on the bench". The page
reply said "not yet measured", and OR141.a (5) reads "its measurement owed".

### Likely counterparts in the other sets (by their words)

| this set's item | likely counterpart elsewhere |
|---|---|
| c-stack-reboot, fatal-report-home, cstack-escalation-path, stack-errno-shared, twin-stack-fault-grammar, voc-handlers-narrow, host-check-d-tsc1 | register unit table U30 "a caught C-stack overflow reported by every broad handler and rebooted with code 20"; the call-site rows (A-S15, A-P13, CD-8, NTP-22, WF-20, WS-23, UC-21) |
| failed-push-no-flash-write | register/A rows "A PUT stages, pushes, then releases one flash write after the pushes" (A-B10), `defer=`/`commit()` (A-C11) |
| led-request-internal-queue | register owner-review U9 "SF-B2: the notification coordinator recognises the default (no-LED) sink"; NP-2 |
| setup-returns-bool, setup-function-type, notification-setup | SPEC C.13 "One contract: `async def setup(self) -> bool`"; register U10 row "`UARTLinkDriver`'s `initialized`, read only by its own `setup()`'s answer" |
| initialized-flags | SPEC C.13 "Which classes carry the `initialized` flag" (agent, 2026-10-05) |
| unpause-waiter | register owner-review U11 "SF-A11: the FRAM mempause auto-unpause becomes a `ticks_ms()` deadline" and "The storage pause ends by a deadline checked on the one-second status pass" |
| one-timeout-mechanism, float-sleep-everywhere, no-sync-sleeps-check | register unit table U31 "every `src/` wait in whole milliseconds with its sleep-form guard and float-refusing fakes"; SPEC D.4 |
| stall-bounds | register U31 "the timing budget as one F.3 table recomputed from the code, the loop-lag scenario bound on every device"; D-H17 |
| i2c-scratch-view | the U30 memory-ladder rows (A.U30.21, "hot paths do not churn same-shaped objects") |
| bmp-conversion-wait | register U15 "BMP3XX's seconds-form conversion wait" (the 30-item default row) |
| webserver-start-retry | U19 rows naming W62 HTTP_START_FAILED; WS-11 |
| new-dns-ntp-errnos | U18 rows on RF160 ("a local failure recorded as the peer's silence") and RF179 |
| ntp-malformed-text | the U30 row splitting a heap failure (E20) from a malformed reply (E69) |
| uart-log-codes | U17 rows "construction refuses a delimited codec too small for a frame (E92) ... a poll interval"; UC-8 |
| idle-poll-rate | SPEC F.5.9 / Part N `udp.poll_idle_ms`; UDP-3 |
| uart-flash-erase-overrun | OR141.a (4), the DMA-ring rows of U17/U31 (UD-1, UC-12, UC-13) |
| twin-tolerates-ntp-offline, twin-choice-15, twin-choice-17, test-helper-d16 | `digital_twin/README.md` "the local NTP responder a booted twin syncs against (`_ntp_responder.py`, owner, 2026-10-02)" |
| humidity-helpers-removed | register U12 rows "`rel_humidity()` refuses outside 0-100 % instead of clamping" and "accepts a saturated reading's 0.001 % rounding step" |
| wozi-move-owner-operation | register unit table U33 "its two wozi sentences narrowed to sessions" |
| dynamic-import-ban | register U10 "the named dynamic-import sites stay" (OR141.a, OR142.a); SPEC F.1's list |
| hardware-family-label, toml-build-metadata, bench-board-toml | OR141.a (1); D-D3/D-D4 |
| website-unattended, reproducible-image | OF-144's page build-date stamp (closed in the U35 redo, landed in 656fc82f) |
| one-entry-per-fault, uart-resync-one-entry | the M_TEST_UNIT row "A.U3.05 dropped (OR140.a (7))"; SPEC C's "Every layer that meets a fault keeps its own persisted entry" |
| ci-budget-margin, harness-timeout | Part N CI rows (SPEC:13318, :13331); U28's CI rows |
| port-lock-reader, port-lock-inherit, marker-copy | U24 "The per-port lock stays per host"; the memory-gate agreement test rows |
| decision-tag-form, hang-cause-phrase-kept | U0's decision-records retrofit and the citation/vocabulary allow-list rows (register U0 "The citation and vocabulary allow-lists grew once") |
| unit-packet-lists, work-order-placements, sites-by-symbol, citation-rescan-merges, unowned-files | the work order and unit packets (`audit/order/`), register header "work order" |

## 8. SAME rows (255)

One line each: id; crosswalk topic; picture line; a few words. Grouped by review-page topic.

### system-and-memory (25)

- `fram-waits-unbounded`; storage-fram; L2; watchdog backstop, no timeout mechanism
- `trigger-starters`; generated-code; L5; D-G5 R, one declared list
- `comment-form`; ci-tooling; L5; one form; new and touched code
- `private-by-default`; core-logging; L5; harmonisation (OR1, OR24)
- `test-only-code-removed`; supervisor-reset-watchdog; L6; OR36; A-S31 R
- `validator-api`; config; L5; one primitive at the input boundary; its uses after the schema go (S2-G1-19)
- `task-names-required`; supervisor-reset-watchdog; L7; no test-only default (A-S17 R)
- `stack-errno-shared`; error-catalog; L7; catalog detail of the owner's C-stack decision
- `cstack-escalation-path`; supervisor-reset-watchdog; L3; one escalation path
- `utc-valid-no-argument`; ntp-dns; L5; one caller, one meaning
- `config-log-ram-attribute`; driver-scd30; L6; A-B17 R
- `fatal-report-home`; core-logging; L3; the logger is also the home of the smaller form (S2-G4-1)
- `crc-polynomial-parameter`; core-logging; L5; no assert in product
- `crc-out-of-range`; core-logging; L2; documented pre-audit contract; A-K3 +-0 lines
- `reset-flush-before-pause`; supervisor-reset-watchdog; L3; A-S6 R order
- `reset-errors-invalid`; webserver-rest; L5; fits api-unknown-key-invalid (ok)
- `blank-fram-read`; storage-fram; L2; confirmed gap A-M2 (V1)
- `core-wording`; docs-records; L1; comments state facts
- `no-sync-sleeps-check`; ci-tooling; L4; cheap guard of the owner's never-block rule; stated owner basis not found
- `annotation-quoting`; ci-tooling; L5; style
- `first-boot-print-only`; config; L6; OR136; evidence-triggered first-boot write
- `float32-proof`; tests-hardware; L4; HW3 on the board
- `config-field-naming`; config; L5; one name per field
- `naming-conventions`; core-logging; L5; harmonisation (OR1, OR24)
- `sensorreader-logger-removed`; core-logging; L2; typing-only checks go (2026-10-27)

### sensors-and-drivers (17)

- `voc-handlers-narrow`; driver-sgp40; L3; lets a C-stack overflow reach the SGP40 handler; also right for the logger-side form
- `tuning-ids-no-default`; docs-records; L5; ids inside the owner's OR30 list
- `neopixel-overlay-names`; led-notification; L5; naming
- `bmp-sealevel-constant`; driver-bmp3xx; L2; unreachable guard goes
- `warning-names`; error-catalog; L5; W11 serves BMP-6 (ok), W12 the pre-audit captive teardown
- `bmp-reapply-code`; driver-bmp3xx; L3; serves BMP-4's rung (R)
- `trigger-loop-name`; core-logging; L5; naming
- `sgp40-backup-type-home`; driver-sgp40; L5; placement
- `isl-int-park-tested`; driver-isl29125; L4; park is ISL-1 R; the re-arm half goes with S2-G1-23
- `isl-rung-no-set-lock`; driver-isl29125; L3; ISL-11 R
- `isl-comments`; docs-records; L1; comments
- `isl-park-int`; driver-isl29125; L7; ISL-1 R (OR101)
- `meanatmtemp-bound`; driver-bmp3xx; L1; BMP-7 R, smallest change
- `bmp-altitude-renamed`; driver-bmp3xx; L5; one name, one meaning
- `voc-at-construction`; driver-sgp40; L6; long-lived object placed at construction; no Optional
- `led-task-defined-state`; led-notification; L3; defined start state after a supervisor restart (NP-4 H by trigger, OR149 kind)
- `ts-zero-no-timestamp`; driver-sgp40; L5; one 'no timestamp' value

### network-and-rest (12)

- `unreachable-guards-removed`; ntp-dns; L2; 2026-10-27 rule
- `ntp-timing-defaults`; ntp-dns; L5; one place
- `host-label-home`; ntp-dns; L5; DNS-9 R
- `captive-dns-tag-ids`; ntp-dns; L5; naming
- `wifi-constructor-cleanup`; wifi; L6; OR36; Wi-Fi behaviour settled
- `dnssrv-warning-code`; error-catalog; L5; shared code for a pre-audit event
- `kept-branches`; ntp-dns; L2; pre-audit branches with reasons
- `socket-faults-retry-rung`; ntp-dns; L3; one mechanism at the owning layer
- `ntp-lock-hold`; docs-records; L1; a record, not code
- `led-command-validation`; webserver-rest; L5; WS-17 R
- `status-ip-and-ipv4`; webserver-rest; L1; no change asked
- `one-utc-primitive`; ntp-dns; L5; A-B5 R

### uart-link (8)

- `uart-private-names`; uart; L5; naming
- `uart-valid-frame-sync`; uart; L5; an async def without an await becomes a plain function (UC-18)
- `uart-starter-names`; uart; L5; naming
- `uart-banner-const`; uart; L6; no test-only export
- `uart-resync-one-entry`; uart; L3; OR56 (1) 'never both'
- `uart-link-initialized`; uart; L6; UL-2 R
- `uart-banner-rename`; uart; L5; naming, Class B
- `crc-empty-payload`; uart; L1; module untouched

### website (3)

- `scd30-calibration-help`; website; L7; help text
- `timezone-on-system-page`; website; L1; no move
- `website-code-details`; website; L5; no test-only seam, one copy

### device-config-and-buildgen (10)

- `boot-entry-name`; buildgen-toml; L5; one name
- `poll-interval-constant`; website; L5; one value
- `dev-toml-comment`; buildgen-toml; L1; comment cap
- `index-header-wording`; website; L1; header
- `noautostart-comment`; generated-code; L7; OR86 option
- `noautostart-output-name`; generated-code; L7; OR86 option
- `web-tag-hidden-key`; buildgen-toml; L5; one hidden field (SGP40 Temp)
- `banner-titles`; generated-code; L1; banners
- `fram-logger-derivation`; buildgen-toml; L5; OR78, no hand list
- `lwip-pool-build-error`; buildgen-toml; L2; pre-audit connection-ceiling check

### build-chain-and-ci (44)

- `ci-matrix-env`; security; L8; template injection hygiene
- `uv-retry-ids`; ci-tooling; L5; naming
- `build-returns-uf2`; ci-tooling; L1; callers unchanged
- `ci-budget-comments`; ci-tooling; L5; numbers in one place
- `versions-header`; ci-tooling; L7; fits the stub note
- `board-check-first`; ci-tooling; L8; order
- `installer-error-prefix`; ci-tooling; L5; one form
- `exemptions-with-file`; ci-tooling; L8; exemptions land with their need
- `twin-modules-typecheck`; ci-tooling; L5; placement
- `ci-comments`; ci-tooling; L1; comments
- `pyflakes-allowance`; ci-tooling; L8; timing
- `global-ignore-comments`; ci-tooling; L1; comments
- `modlwip-header`; ci-tooling; L5; provenance of the owner's patch
- `readback-env`; ci-tooling; L5; no hidden import
- `host-typecheck-ini`; ci-tooling; L8; ownership
- `monthly-firefox`; ci-tooling; L8; cache
- `uv-sync-action`; ci-tooling; L5; one retry definition
- `host-try003-em`; ci-tooling; L5; host CLIs
- `lwip-control-once`; tests-unit; L4; OR21.a 'control arms are overkill'
- `host-cli-exit`; ci-tooling; L5; one exit form
- `parse-cmd-request-deleted`; webserver-rest; L2; A-A3 R
- `toml-schema-check`; buildgen-toml; L5; L.3 genuine contract check (F.md 3)
- `shell-safety`; ci-tooling; L5; shell hygiene
- `conventions-checked`; ci-tooling; L5; cheap guard of OR24's one material
- `clean-at-start-website`; ci-tooling; L5; same rule as the firmware build
- `image-size-report`; release; L6; the trigger DRIFT rule 2 asks for
- `uv-pin-current`; ci-tooling; L8; pin
- `port53-under-test-sh`; ci-tooling; L8; real port clash (CLAUDE.md)
- `port-lock-inherit`; ci-tooling; L8; mechanics of a needed lock
- `stage-only-mode`; ci-tooling; L5; mode
- `every-device-site`; tests-unit; L4; owner 2026-10-23: tests for all devices
- `host-coverage-render`; ci-tooling; L8; coverage tool
- `pass-label-state`; ci-tooling; L5; no global
- `run1-null-time`; twin; L4; pins NTP-17 R
- `twin-archive-per-device`; twin; L6; keep three per device
- `crc16-toml-derived`; twin; L4; owner 'I want both.' (D-G30)
- `smoke-launch`; ci-tooling; L5; shared helper
- `generator-output-set`; buildgen-toml; L7; OR23 atomic output (D-H2)
- `noautostart-workdir`; ci-tooling; L8; isolation
- `job-order`; ci-tooling; L8; scheduling (OR134)
- `archive-interface`; ci-tooling; L8; archiver kept (SSD wear)
- `single-device-mode`; buildgen-toml; L5; mode
- `rollover-runner`; tests-hardware; L7; OR139 option 1
- `workaround-trigger`; docs-records; L8; each workaround names its exit

### tests (60)

- `unit-test-d-t1`; tests-unit; L4; GC stage
- `unit-test-d-t2`; tests-unit; L4; derived bounds
- `unit-test-d-t3`; tests-unit; L4; effects, no stored id (P4)
- `unit-test-d-t4`; tests-unit; L4; read from source
- `unit-test-d-t5`; tests-unit; L4; test design
- `unit-test-d-t6`; tests-unit; L4; comment
- `unit-test-d-t7`; tests-unit; L4; unit
- `unit-test-d-t8`; tests-unit; L4; refused input
- `unit-test-d-t9`; tests-unit; L4; read from source
- `unit-test-d-t10`; tests-unit; L4; builder default
- `unit-test-d-t11`; tests-unit; L4; retires with async with
- `unit-test-d-t12`; tests-unit; L4; effect, no stored status (P4)
- `unit-test-d-t14`; tests-unit; L4; fewer tests (UC-8 goes)
- `unit-test-d-t15`; tests-unit; L4; read from source
- `unit-test-d-t16`; tests-unit; L4; helper pins
- `unit-test-d-t17`; tests-unit; L4; rows
- `unit-test-d-t18`; tests-unit; L4; superseded rewrite
- `unit-test-d-t19`; tests-unit; L4; placement
- `unit-test-d-t20`; tests-unit; L4; placement
- `unit-test-d-t21`; tests-unit; L4; CLAUDE.md nested-run rule
- `unit-test-d-t22`; tests-unit; L4; host guard
- `unit-test-d-t23`; tests-unit; L4; tests for the input primitive
- `unit-test-d-t24`; tests-unit; L4; pins a kept branch
- `unit-test-d-t25`; tests-unit; L4; gate
- `unit-test-d-t26`; tests-unit; L4; executed entry
- `unit-test-d-t28`; tests-unit; L4; AST check
- `unit-test-d-t29`; tests-unit; L4; pre-audit starter log stays
- `unit-test-d-t31`; tests-unit; L4; file-local sweep
- `unit-test-d-t32`; tests-unit; L4; CRC16 only
- `unit-test-d-t33`; tests-unit; L4; placement
- `unit-test-d-t34`; tests-unit; L4; bundle check
- `unit-test-driven-clock`; tests-unit; L4; speed (OR39)
- `test-helper-d1`; tests-unit; L4; fake conformance
- `test-helper-d2`; tests-unit; L4; test knob
- `test-helper-d3`; tests-unit; L4; bounded-fake rule
- `test-helper-d4`; tests-unit; L4; counters in the fake (P4)
- `test-helper-d5`; tests-unit; L4; names
- `test-helper-d6`; tests-unit; L4; declared errors
- `test-helper-d7`; tests-unit; L4; derived owners
- `test-helper-d8`; tests-unit; L4; follows main()
- `test-helper-d9`; tests-unit; L4; module
- `test-helper-d10`; tests-unit; L4; written once
- `test-helper-d11`; tests-unit; L4; derived names
- `test-helper-d12`; tests-unit; L4; order
- `test-helper-d13`; tests-unit; L4; from get_loggers()
- `test-helper-d14`; tests-unit; L4; one scenario
- `test-helper-d15`; tests-unit; L4; module
- `test-helper-d16`; tests-unit; L4; placement
- `host-check-d-tsc1`; tests-unit; L4; placement of the owner-ok'd depth test
- `host-check-d-tsc3`; tests-unit; L4; ids
- `host-check-d-tsc4`; tests-unit; L4; placement
- `host-check-d-tsc5`; tests-unit; L4; one helper (P8)
- `host-check-d-tsc6`; tests-unit; L4; named files
- `host-check-d-tsc7`; tests-unit; L4; kept assertion
- `derived-test-copies`; tests-unit; L5; P8
- `per-device-suites`; tests-unit; L5; OR78
- `licence-checks`; licensing; L7; release obligation
- `fram-seam-count-l1`; tests-unit; L4; unit test, not AST
- `orphan-unit-files`; process; L8; ownership
- `test-file-naming`; tests-unit; L5; names

### hardware-tests (24)

- `dut-ip-option`; tests-hardware; L4; FRAM logs read before a reset (CLAUDE.md)
- `settle-polls`; tests-hardware; L4; polls on state, not sleeps
- `spoof-source-range`; tests-hardware; L4; documentation range only
- `voc-plausibility-floor`; tests-hardware; L4; algorithm reports 0
- `manual-imports`; tests-hardware; L4; imports
- `bench-mac-not-written`; tests-hardware; L4; no MAC in docs
- `bench-renames-and-carried`; tests-hardware; L4; carry-overs
- `device-script-sleeps`; tests-hardware; L4; named constants
- `shared-include-typing`; tests-hardware; L4; typing
- `reset-scripts-report-first`; tests-hardware; L4; facts before reset
- `repair-script-schema`; tests-hardware; L4; rendered from source
- `fram-wp-check`; tests-hardware; L4; raw dump
- `reset-race-nonce`; tests-hardware; L4; test band
- `dead-path-insert`; tests-hardware; L4; dead line
- `fram-scratch-regions`; tests-hardware; L4; own regions (CLAUDE.md FRAM caveat)
- `sgp40-cadence-ram`; tests-hardware; L4; no persisting write
- `float-ranges-rendered`; tests-hardware; L4; from source
- `bench-facts-dict`; tests-hardware; L4; rendered on host
- `verdict-line-format`; tests-hardware; L4; host judges
- `scd30-prereq-scripts`; tests-hardware; L4; three scripts
- `image-record-file`; tests-hardware; L4; record per image
- `destructive-last-marker`; tests-hardware; L4; safety
- `toolchain-reverify-gate`; tests-hardware; L4; opt-in
- `spoof-sudo-rule`; tests-hardware; L4; named sudo rule

### digital-twin (25)

- `twin-choice-1`; twin; L4; twin rules
- `twin-choice-2`; twin; L4; twin rules
- `twin-choice-3`; twin; L4; twin rules
- `twin-choice-4`; twin; L4; twin rules
- `twin-choice-5`; twin; L4; twin rules
- `twin-choice-6`; twin; L4; twin rules
- `twin-choice-7`; twin; L4; twin rules
- `twin-choice-8`; twin; L4; twin rules
- `twin-choice-9`; twin; L4; twin rules
- `twin-choice-10`; twin; L4; twin rules
- `twin-choice-11`; twin; L4; twin rules
- `twin-choice-12`; twin; L4; twin rules
- `twin-choice-13`; twin; L4; twin rules
- `twin-choice-14`; twin; L4; twin rules
- `twin-choice-15`; twin; L4; twin rules
- `twin-choice-16`; twin; L4; twin rules
- `twin-choice-18`; twin; L4; twin rules
- `twin-choice-19`; twin; L4; twin rules
- `twin-stack-fault-grammar`; twin; L4; existing grammar
- `twin-fram-writes-by-runner`; twin; L4; simple fake
- `twin-network-fake-typed`; twin; L4; no Any
- `twin-load-writer`; twin; L4; keeps FRAM evidence (CLAUDE.md)
- `twin-watchdog-fault-flag`; twin; L4; runner instrumentation
- `fidelity-table-rows`; twin; L4; one row per fact
- `combined-faults-reboot`; twin; L3; escalate (L3, OR18.a)

### documentation (22)

- `datasheet-text-after-move`; docs-records; L1; order
- `crc-status-as-built`; docs-records; L1; fact sentence
- `third-unix-build-named`; docs-records; L1; name
- `tier-parity-rule-home`; docs-records; L1; one home
- `backlog-items-removed`; docs-records; L1; stale out
- `claude-intro-fix`; docs-records; L1; wording
- `microdot-count-deleted`; docs-records; L1; stale count
- `class-a-clause-once`; docs-records; L1; dedupe
- `backlog-lists-wording`; docs-records; L1; lists
- `ci-job-list-checked`; docs-records; L1; one-time doc pass
- `microdot-version-once`; docs-records; L1; one place
- `spec-structure`; docs-records; L1; structure
- `spec-gap-fills`; docs-records; L1; agent text, labelled
- `spec-placements`; docs-records; L1; placement
- `term-table`; docs-records; L1; one term per concept
- `js-private-meaning`; docs-records; L1; JS meaning
- `archive-gaps-closed`; docs-records; L1; same terms
- `dst-advice`; docs-records; L1; advice
- `declined-checker-record`; docs-records; L1; no stale counts
- `decision-tag-form`; docs-records; L7; agent stays the actor (L7)
- `legacy-password-not-copied`; docs-records; L1; no new copy of the hotspot default
- `runbook-home`; docs-records; L1; where flashing is

### execution-and-release (5)

- `archive-keep-three`; process; L6; SSD wear (owner, 2026-09-26)
- `one-gate-command-set`; process; L8; one command set
- `planted-red`; tests-hardware; L4; planting allowed for memory exhaustion (owner, 2026-10-23)
- `rollover-via-runner`; tests-hardware; L4; OR139
- `tunable-search-limit`; process; L8; DRIFT rule 5: inventories are reading aids
