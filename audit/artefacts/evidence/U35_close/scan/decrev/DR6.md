DR6 decision review, written by the part (Wed Oct 28 11:49 UTC 2026)

Scope: the register's owner-review rows for U31-U35 (65 rows, `inputs/DR6_register_rows.txt`), the parked deltas (68 rows, `inputs/DR5_parked_rows.txt`), the review page's parked items, owner steps and hardware sessions (`inputs/DR6_review_parked_steps.json`, answers from `inputs/answers.json`), and the U35 redo's own lead decisions (`S/u35r/REDO.md`, `owner_report_items.md`, `closing_ledger.md`, `d3r_rec2_items.md`, and the decision-bearing LEAD NOTES of `S/u35/lane_plan.md`). Read-only; nothing ran. A bundled register row is split as `REG:<line>/<letter>`; a second decision on one redo line as `<file>:<line>/b`. Static checks used: git at `11b66cd8`, the pinned MicroPython v1.29.0 source, the scan rows (`*.md`, `scan2/*.md`).

**Owner quotes used by tag** (verbatim, with source): [Q1] owner, 2026-10-28: "building upon hypothetical findings is a clear no-go". [Q2] owner, 2026-10-28 (LN362): "The audit verification machinery is just a temporary tool." [Q3] the same: "The unit tests shall have good quality, but don't need deep dives." [Q4] the same: "hardcoded delay checks like this are a very bad, very awkward pattern". [Q5] OR36: "contains zero artifacts specifically added for testing, neither functions, nor specific variables". [Q6] OR149: "the fixes required for such reliability (if required at all, if not already safe inherently) are minimal, low complexity". [Q7] owner, 2026-10-28: "We thoroughly discussed the WiFi issues and I decided everything already." [Q8] owner (rulings file, in force): "Test duration going up like this is anyhow something to fix - not cutting back strictness, but making it more efficient"; OR39: "Look for opportunities for speeding up the test suite". [Q9] owner, 2026-10-22 (LN111): "Solutions you proposed agreed."

Scan rows: `A.md`-`F.md`, `G.md` and `REPORT` are `S/u35r/scan_pub/`; `S2-*` rows and `G1.md`-`G4b.md` are `S/u35r/scan2/`.

## 1. Counts

- Decisions: **311**; facts (no verdict): **12** register rows plus the redo fact lines listed at the end of section 8.
- Per verdict: DIFF 48, OBS 22, FORM 21, OWN 69, SUP 10, CHECK 4, SAME 137. Marked "misfit" against a picture line: 23.
- Per piece: register U31-U35 106, parked deltas 69, review page 24, redo lead 112.

| topic | DIFF | OBS | FORM | OWN | SUP | CHECK | SAME | all |
|---|---|---|---|---|---|---|---|---|
| buildgen-toml | 1 |  |  | 1 |  |  |  | 2 |
| bus-i2c-spi |  | 1 | 1 |  |  |  | 3 | 5 |
| ci-tooling | 1 |  |  | 1 | 1 |  | 8 | 11 |
| config | 4 |  |  | 6 | 2 |  |  | 12 |
| core-logging |  | 1 | 1 | 3 |  |  | 1 | 6 |
| docs-records | 5 |  |  | 7 |  |  | 9 | 21 |
| driver-bmp3xx | 3 |  |  |  |  |  |  | 3 |
| driver-isl29125 | 2 |  |  |  |  |  |  | 2 |
| driver-scd30 | 1 |  |  | 2 |  |  | 1 | 4 |
| driver-sgp40 | 1 |  |  |  | 1 |  | 2 | 4 |
| error-catalog |  | 1 |  |  |  |  | 2 | 3 |
| generated-code |  | 1 | 1 | 1 |  |  |  | 3 |
| led-notification | 4 | 3 |  |  |  |  | 2 | 9 |
| licensing |  |  |  | 1 |  |  | 2 | 3 |
| memory-gc |  | 4 |  |  |  |  | 1 | 5 |
| ntp-dns | 4 | 3 | 2 | 1 |  |  | 5 | 15 |
| process | 5 |  | 2 | 14 | 3 |  | 16 | 40 |
| release |  |  |  |  |  |  | 5 | 5 |
| security |  |  |  |  |  |  | 4 | 4 |
| storage-fram | 3 |  |  | 1 |  | 2 | 1 | 7 |
| supervisor-reset-watchdog | 4 | 5 | 1 | 4 | 1 | 2 | 7 | 24 |
| tests-hardware | 1 | 1 |  | 1 |  |  | 16 | 19 |
| tests-unit | 4 |  | 5 | 2 |  |  | 21 | 32 |
| timing-waits | 1 | 2 | 1 |  |  |  | 3 | 7 |
| twin | 2 |  | 4 | 6 |  |  | 12 | 24 |
| uart | 1 |  | 1 | 5 | 1 |  | 6 | 14 |
| webserver-rest | 1 |  | 2 | 4 |  |  | 5 | 12 |
| website |  |  |  | 1 |  |  | 3 | 4 |
| wifi |  |  |  | 8 | 1 |  | 2 | 11 |

## 2. DIFF rows

- **REG:750/c** (supervisor-reset-watchdog, L2). Taken: The supervisor's own fault persists E115 SUPERVISOR_RAISED and sets the reset decision first (OF-26). New: no entry: the unfed watchdog reset (code 2) carries the fault, as before. Basis: A.md A-S16 (H, implausible: "the watchdog resets either way; only the entry is new"); S2-G3-7 (E115 exists only for A-S16); [Q1]. Changes: ~5 src lines at the supervisor loop, catalog E115 (a tombstone under the never-reuse rule), tests_hardware/error_log_helpers.py:54, two tests.
- **REG:757/l** (buildgen-toml, L2). Taken: The I2C rule takes the minimum over every hard consumer, the watchdog's always (bus.i2c-timeout-consumer, lane C2). New: no consumer check for the field devices; one I2C check stays (S2-G3-1's budget sum); dev's link branch is the owner's call, as S2-G3-2 states. Basis: S2-G3-2: the watchdog branch allows 3,000,000 us against the 200,000 us ceiling, so it never binds on six devices; probe on modified copies; D.md H17 (H). Changes: ~17 lines in buildgen/validate.py:615-634 and its rule row; the helper moves with the loop-lag scenario.
- **REG:792** (process, L8 misfit). Taken: U35 cut into ten lanes, later split to 13-15; 70 blocks, 4,729 harness calls, eleven past the 80-call valve. New: a cut of a few lanes the lead can review line by line, no splits mid-unit. Basis: OR107: "Parallelization is generally allowed, but don't overdo it it, the resulting syncing effort should stay reasonable"; OR145: "use parallelization carefully and don't overdo it in the context of implementation"; owner, 2026-10-21: "You have many agents running at the moment. Don't overdo it"; PICTURE M9. Changes: process only, no code.
- **REG:795/b** (ntp-dns, L2). Taken: The UDP self-heal moved into a finally in lane Q (LN19), not routed. New: no change; recorded as latent. Basis: LN19's own words: "Latent on every device and in every mode, since each caller disconnects in its own `finally`"; B.md UDP-5 (H, implausible); [Q1]. Changes: ~3 lines back in asy_udp_socket.py `_connect()` and its test.
- **REG:795/c** (tests-unit, L4 misfit). Taken: "a new check is not growth of existing work" (LN20, 25, 66; applied again LN196). New: a new check's cost counts like any other growth: made efficient, or not added. Basis: [Q8]; REPORT section 9 (unit-tier timeouts 45 -> 175 min). Changes: CHECKLIST 14's reading; no code.
- **REG:795/i** (supervisor-reset-watchdog, L6 misfit). Taken: LN96: the exception-handler guard kept ("a handler already set stays"). New: the guard goes; the twin installs its printing handler after start_tasks(). Basis: S2-G1-11 (the code's own reason at asy_system_service.py:776: "the PC tiers install one that prints at every level"; no product path sets one first); [Q5]. Changes: 1 condition line; the twin helper's call order.
- **REG:795/j** (supervisor-reset-watchdog, L6 misfit). Taken: LN96: `_shutdown_task` kept ("read by tests in four files"). New: the attribute goes; tests take the task another way. Basis: git grep at 11b66cd8: src reads it nowhere (only asy_system_service.py:243, :404 assign it), tests read it in 4 files; the pinned asyncio keeps the task referenced (extmod/asyncio/core.py:147 `_task_queue.push(t)`, v1.29.0); [Q5]. Changes: 2 src lines; four test files.
- **REG:820** (ntp-dns, L2). Taken: 44-47-byte NTP replies rejected (micropython-lib 9ec1830). New: no change. Basis: B.md NTP-9 (H): the parser reads bytes 0, 1 and 40-43 only, a shorter reply raised and was caught as malformed at 25caf528 `_parse_ntp_reply`; [Q6]. Changes: ~3 lines and their test.
- **REG:827** (config, L2). Taken: SF-B3: a per-store unpersisted flag reported beside ConfigFaults. New: no /status key: the persisted errno 14 in CFGMGR's errcount already shows it (the row's own fallback); the flag stays for the shutdown flush (A-S9). Basis: D.md G17 (V2 refuted: src/config_manager.py@25caf528:378-380 logs errno 14, reproduced 3/3); REPORT section 3 (refuted list); scan2/G4b.md:278. Changes: the ConfigUnpersisted key, get_config_unpersisted(), the site row and their tests.
- **REG:829** (timing-waits, L2). Taken: SF-B5: a failed uptime tick-timer arm persisted once and re-armed on a bounded sleep. New: the pre-audit catch at the arm only. Basis: S2-G4-7 ("Six shapes for one refuted trigger"; alarm-pool exhaustion refuted, A.md V6); [Q1]. Changes: part of the ~85 lines in SCAN2 section 3 ("refused timer arm, six shapes").
- **REG:833** (driver-bmp3xx, L2). Taken: SF-B9: por_detected read each cycle, settings re-applied, W71. New: no detector; a knowledge line. Basis: C.md BMP-1 (H, implausible); S2-G3-7 (W71 exists only for BMP-1); [Q1]. Changes: BMP-1's lines, W71, its tests.
- **REG:835** (driver-isl29125, L2). Taken: SF-B11: the calibration outcome readable, a timed-out run logged (W75). New: console-only, as before. Basis: C.md ISL-9 (H, implausible); S2-G3-7 (W75 exists only for ISL-9). Changes: ISL-9's lines and W75; the bench Calibrate test's +2 min wait goes with it (owner_report_items.md:37).
- **REG:836** (storage-fram, L2). Taken: SF-B12: a RAM-only logger persisted or reported (LOG_RAM_ONLY, E28). New: the console line, as before. Basis: A.md A-P3 (H, implausible); S2-G3-7 (E28). Changes: A-P3's lines and E28; the confirmed unreadable-store branch (A-P4) stays.
- **REG:839** (ntp-dns, L2). Taken: SF-B15: a DNS reply filling the buffer taken as truncated (W16). New: no change. Basis: B.md DNS-8 (H: no EDNS is sent, so a server truncates at 512 B itself, RFC 1035 4.2.1); S2-G3-7 (W16). Changes: ~4 lines and W16; captive DNS's 512 B receive (a confirmed gap) stays.
- **REG:841** (led-notification, L5). Taken: SF-B17: an explicit inactive State on /measurements. New: no State field. Basis: C.md NT-2 (H; a new API field with no owner decision); S2-G4X-2 (the state machinery has no other reader). Changes: ~25-30 lines and the NotifyState table.
- **REG:846** (driver-scd30, L2). Taken: SF-A04: a stuck-high RDY counter (W73). New: no counter. Basis: C.md SCD-6 (H, implausible: the store keeps re-publishing, the owner's named exception); S2-G3-7 (W73). Changes: SCD-6's lines and W73.
- **REG:847** (driver-bmp3xx, L2). Taken: SF-A05: EVENT and ERR_REG read each cycle. Answer, basis and change as REG:833.
- **REG:852** (supervisor-reset-watchdog, L2). Taken: SF-A10: two mem32 reads in begin_boot() published as ResetBits. New: the decoded reset reason only (OR60). Basis: A.md A-S4 (H, implausible); D.md G14b (H); S2-G4X-1 (the registers and the mem32 read go with ResetBits). Changes: ~17 lines and the /status key.
- **REG:864** (config, L6). Taken: SF-M1-01: a littlefs reformat persists W69 CONFIG_LOST (kept again by the redo, REDO.md:18). New: nothing beyond the pre-audit console line. Basis: A.md A-S28 (H, implausible); S2-G4-21 ("An addition with its own false positive": OF-184, a false W69 after every scratch build); SCAN2 section 3 (~20 lines go, nothing stays). Changes: ~20 lines, W69 and its reset-reason exclusion.
- **REG:865** (storage-fram, L2). Taken: SF-M1-03: the unreadable-store branch reported through SF-B12's E28. Answer, basis and change as REG:836.
- **REG:866** (config, L2). Taken: SF-M1-07: the unpersisted flag set on a failed create write. Answer, basis and change as REG:827.
- **REG:870** (led-notification, L2 misfit). Taken: SF-M3-01: a consumer treats a sample older than 10,800 s as unavailable (notification, SGP40). New: no age check at the consumers. Basis: C.md NT-3, SGP-2 (H); SCAN2 section 7 item 3 and section 8 check 7 (`_store_scd()` stores `utc_now()` every cycle, ContMeas Off included); [Q4]. Changes: ~30 lines with SCD-6's part; OF-232's test (REDO.md:24) goes too.
- **REG:872** (driver-bmp3xx, L2). Taken: SF-M3-02: an out-of-range BMP3XX reading logs its own code E27. New: a plain read failure, as before (SCD-5's range gate stays). Basis: C.md BMP-5 (H, implausible, "escalation unchanged"). Changes: 3 lines.
- **REG:874** (driver-isl29125, L2). Taken: SF-M3-04: ISL29125's shadow compared every read cycle. New: as pre-audit (after a failed write or on a GET). Basis: C.md ISL-10 (H: the datasheet's only ways a CONFIG byte changes without our write are a reset or brownout, BOUTF handled). Changes: ~9 lines.
- **REG:875** (driver-sgp40, L2). Taken: SF-M3-05: a task restart keeps the live VOC state (no restore over it). New: the restore as pre-audit. Basis: C.md SGP-12 (H: "the pre-audit restart restored a backup at most one BackupPeriod old (default 1 min)"). Changes: SGP-12's lines.
- **REG:878** (led-notification, L2 misfit). Taken: SF-M3-09: the WS2812 overlay refreshed once per notification cycle (became NP-5's 300 s rewrite). New: the pre-audit `await ...wait()` with no timeout; the SGP40 SPEC sentence stays. Basis: C.md NP-5 (H; premise hardware-only; its confirmed cascade defect, a lost shutdown cancel 8/8); REPORT section 3 ("removes 5 lines"); [Q4]; owner (LN362): "it patches a rather hypothetical issue instead of cleanly and minimally implementing something clean". Changes: 5 lines, the tunable led.overlay_refresh_ms and its row.
- **review-and-go-ahead** (process, L7 misfit). Taken: "silence on a routine batch counts as approval". New: only an answered item is the owner's decision; an unanswered one stays an agent proposal. Basis: OR48.a: "recorded decisions I took (not the session agent)"; owner, 2026-10-28: "Decisions I really took are still valid." and "The OK in the review stay valid." (the OKs, not the silences); PICTURE M10. Changes: records only: the 295 unanswered review items keep their agent label (DR1's scope).
- **REDO.md:11** (webserver-rest, L2). Taken: OF-142: the flat GET's unavailable marker read by its whole shape. New: no change. Basis: OF-142's own row: "inherently safe today (no tagged field is named `error`)" (audit/sweeps/open_findings.md:150); [Q6]; S2-G4-17. Changes: the shape test and its tests.
- **REDO.md:18** (config, L6). Taken: CONFIG_LOST kept after the first-boot scan (LN147). Answer, basis and change as REG:864.
- **REDO.md:25** (ntp-dns, L2 misfit). Taken: OF-247: the NTP resync cadence read from elapsed time. New: the pre-audit count of delivered ticks. Basis: owner, 2026-10-27, Q10: "Option a, the 10s don't matter at all relative to the interval, and on top, the interval as such is arbitrary."; B.md NTP-12 (H); S2-G4-13. Changes: ~14 lines: two TickSeconds, the rounding helper, their tests.
- **REDO.md:25/b** (uart, L6). Taken: OF-242: the hazard run's 26 frame copies cut. New: no change. Basis: OR110: "If a timer allocates, never reaches any critical value and frees some seconds later, it's less critical"; PICTURE M7; OF-242 is dev's on-demand run only (open_findings.md:250). Changes: the copies' rework, if landed.
- **REDO.md:54** (tests-unit, L4 misfit). Taken: CEr: every uncovered src line classed; the owed direct tests red-first on a plant. New: coverage stays advisory; no campaign. Basis: [Q3]; REPORT section 9 ("campaigns to cover every uncovered line and every audit-table cell"); CLAUDE.md: coverage "never gates anything". Changes: records only; the tests landed stay where they test real behaviour.
- **REDO.md:59** (docs-records, L4 misfit). Taken: CRr: review.md (every test, its verdict), redflags rewrite, device-script facts; RF1 later (closing_ledger.md:13). New: no per-test verdict ledger. Basis: [Q2]; OR48.a: "make sure everything is found, but no list or permanent record"; REPORT section 11 (records walks: 20 lanes, about 35 k audit lines). Changes: the CRr/RF1 lanes and their records; no product line.
- **REDO.md:60** (tests-hardware, L4 misfit). Taken: The bench log check: no_unprovoked_log_entry fixture, provokes_log marker and its sets (CRr2b..b12, CRr2c, CRr2d). New: none before the bench tier has run on silicon; read the FRAM logs by hand in the round. Basis: REPORT section 11 ("the bench log check (12 lanes, never run on silicon)"); [Q2]. Changes: the fixture, marker, sets and their tests (paused lanes not resumed).
- **REDO.md:68** (docs-records, L4). Taken: CM3 (all pairs, config-value dimensions) and CM4 (interaction matrix, recombination row); closing_ledger items 1 and 7. New: none. Basis: as REDO.md:59. Changes: records only.
- **REDO.md:72** (docs-records, L4). Taken: B2r's record measurements (raising.md's 414 rows, reasons.json, conformance/intent/levels/load cells, Basis values). New: keep timing.md's columns (the owner's test-time measure); the rest none. Basis: as REDO.md:59. Changes: records only.
- **REDO.md:108** (process, L1 misfit). Taken: Records lanes fix any defect they find in-lane, src/ included (also LN256's "plan risk"). New: a finding outside a brief goes to a list; product code changes only on an observed failure or a reproduction. Basis: [Q1] and "Hypothetical findings which are suspicious to be real need to be verified"; owner (LN364): "in the dimension of a few lines per module, very minimal and clever ... Surely not by patching multiple loops over another.". Changes: process; the BR2/BR3 product fixes are owner_report_items.md:62/:67.
- **REDO.md:113** (docs-records, L4). Taken: Q35's additions (the levels walk re-run, faults row, queue_c items, e51 rows, intent codes, walks re-run on old trees). New: none (the BACKLOG chroot paragraph aside). Basis: as REDO.md:59. Changes: records only.
- **owner_report_items.md:67** (storage-fram, L2). Taken: BR3: a chunk read's data copy MemoryError degrades to "not read" with one entry. New: no catch. Basis: OR26.a: "graceful degradation on expectable memory errors"; PICTURE M1 (F.2's "only worth closing for a concrete, non-hypothetical threat" belongs back); a chunk-sized copy, the largest read being the SGP40 backup, 268 B, once per boot (LN290). Changes: ~4 lines and a test.
- **owner_report_items.md:71** (process, L4). Taken: The merge checks also run the audit record checks (raising, e51, review rows; LN269) and levels_walk at every merge (LN353); REC2 re-locates line-number cites (d3r_rec2_items.md:111, :121; LN280). New: no record checks at merges; no re-location passes. Basis: [Q2]; REPORT section 11 ("20 commits that only re-render records keyed on line numbers"). Changes: process only.
- **owner_report_items.md:159** (tests-unit, L4). Taken: The drift check's concurrent arm and CMr1n "both arms separate in every layout" (LN356; closing_ledger.md:12). New: record the measured limit (the parked arm's zero margin) beside HP2's no-leak result; no further lane. Basis: closing_ledger.md:29-32 (a measured limit "accepted and recorded"); [Q3]. Changes: CMr1n not run.
- **owner_report_items.md:206** (twin, L2). Taken: WR1: each bus's own settings in the device picks (LN325: 0 of 14 call shapes change). New: a knowledge line; only the SGP40 twin bus's 100 kHz default fixed. Basis: the lead's own probe (0 of 14 picks change); [Q1]. Changes: wiring_read()'s bus statements and their tests.
- **owner_report_items.md:232** (led-notification, L3 misfit). Taken: The lost-cancel answer: a rule, one shared timed-wait primitive, a scan of every wait_for site, the overlay on the primitive (LC1 sweep lane, LN337, LN358). New: revert NP-5 (the overlay waits on its flag with no timeout, as pre-audit); no primitive, no sweep; the wait_for property one Part F sentence. Basis: REPORT section 3 and section 6 point 3; C.md NP-5; owner (LN362): "it patches a rather hypothetical issue instead of cleanly and minimally implementing something clean" and "trying to debug the Micropython sources,which could not be more out of our scope". Changes: 5 lines; closing_ledger item 8 resolved.
- **closing_ledger.md:8** (process, L4 misfit). Taken: Ledger items 1-7 (LD+CM3, CRr2c, IN2, CRr2d, CMr1n, RF1, CM4). New: the ledger holds item 8 (as owner_report_items.md:232) and item 9 only. Basis: [Q2]; owner (LN364): "Not missing anything, but being smart and lean.". Changes: the seven paused lanes are not resumed; their patches stay as evidence.
- **LN196/b** (tests-unit, L4). Taken: F4e's +8 % accepted as a new check (LN25's ruling). Answer, basis and change as REG:795/c.
- **LN230** (ci-tooling, L4). Taken: N12 item 2 and N13: the repo scanner reads JS regex literals and comments inside template-literal substitutions. New: a stated blind spot; no reader work. Basis: E.md (b) "docs policing born in the audit ... `_repo_scan.py` plus 3 tests of the scanner"; the three new hits were type casts, not prose; [Q2]. Changes: the reader extensions and their ~50 tests.
- **LN281** (twin, L4). Taken: CO4/CO5: the conformance cells closed in-unit; twin chip knobs stick_next_wrdi and corrupt_next_write with four tests (LN290). New: no conformance cells; no new twin knobs. Basis: OR20: "Only if there is no alternative, and keep tiny anyway"; [Q2]; PICTURE M8. Changes: twin knobs, tests and records.
- **LN349** (docs-records, L4). Taken: IN2: a reverse map for 1,204 unreached test functions. New: none. Basis: as REDO.md:59. Changes: records only.

## 3. OBS rows

- **REG:750/b** (supervisor-reset-watchdog, L2). The entry coroutine built inside the bounded wait's try, its MemoryError arm printing through console(). Root: the 1,200 ms bounded entry write (S2-G1-6, SCAN2 section 7 item 4) and the memory-gate console lines (S2-G1-9).
- **REG:756/b** (supervisor-reset-watchdog, L2). A MemoryError at the escalation's bounded wait takes the timeout path to the reset. Root: the bounded entry write (S2-G1-6).
- **REG:757/f** (supervisor-reset-watchdog, L2). The escalation's entry wait 1200 ms, a fifth of a pass's 6 s (Part N system.escalation_entry_wait_ms). Root: the bounded entry write itself (S2-G1-6; SCAN2 section 7 item 4: "goes"; the record is written before the wait).
- **REG:757/g** (error-catalog, L5). E115 the lowest unbanded number, SYSTEM's second band 115-119 with the SGP40 band's width. Root: A-S16 (H), S2-G3-7; see REG:750/c.
- **REG:757/k** (memory-gc, L6 misfit). Quiet= never hides the MemoryError line (lane C1). Root: the memory-gate console lines (S2-G1-9, S2-G4-6); [Q5].
- **REG:771** (led-notification, L5). FX7: `_trigger_signal()`'s try narrowed, the W67 drop warning after it. Root: W67 itself (C.md NT-5, class C of NP-2; S2-G4-9; SCAN2 section 3: "the LED drop warning W67 ... go").
- **REG:787/a** (ntp-dns, L5 misfit). R-7: UDPSocket.write_and_recvfrom() and its tests removed as unused. Root: DNS-4 (H, B.md:75: "the retry loop moved here from UDPSocket.write_and_recvfrom"): reverting DNS-4 gives the method its caller back; the owner's later library rule also keeps a real feature (C8).
- **REG:789/b** (ntp-dns, L5). N1: `_ATTEMPT_TIMEOUT_MS`/`_EXHAUST_TIMEOUT_MS` and their tags out with the tests that read them. Root: as REG:787/a (DNS-4).
- **REG:807/a** (supervisor-reset-watchdog, L2). G1a: the escalation scenario's bound starts at the release so host pace no longer picks the path. Root: S2-G1-6.
- **REG:826** (led-notification, L5). SF-B2: request_signal()'s bool tested, W67 warned and counted. Root: the deadline's drop branch (NP-2; NT-5 class C; S2-G4-9; SCAN2 section 3): the drop happens only when the signal task never restarts (asy_neopixel_driver.py:33).
- **REG:828** (timing-waits, L2). SF-B4: mempause's aborted pause answers Failed. Root: the refused-timer arm family (S2-G1-7, S2-G4-7; trigger refuted, A.md V6).
- **REG:854** (memory-gc, L6 misfit). SF-A12: the UDP wrapper prints a caught MemoryError's text through console() at every level. Root: the memory-gate console lines (S2-G1-9, S2-G2-3; [Q5]); the row's source "owner, 2026-10-20: Option 1 is good" covers the unit tests' level only (REG:729); see C2.
- **REG:868** (timing-waits, L2). SF-M1-06: the re-arm loop reads uptime on each pass. Root: SF-B5's re-arm (S2-G4-7).
- **REG:871** (memory-gc, L6 misfit). SF-M3-06: RegionBuffer prints its MemoryError text; SGP40 tests the None buffer. Root: the memory-gate console lines (S2-G1-9); A-B18 and SGP-14 (H); see C2.
- **REDO.md:24/b** (led-notification, L2). OF-232: the age check outside the producer's try, plus an exact-age test. Root: the consumer age checks (S2-G4-10, S2-G1-18; REG:870).
- **REDO.md:28** (core-logging, L6 misfit). F3r: a caught MemoryError prints its text through console() at every level (LN146). Root: the memory-gate console lines (S2-G1-9: "`_line()`'s at-every-level arm (F3r)"); [Q5].
- **REDO.md:45** (supervisor-reset-watchdog, L2). T4r2: the escalation timeout scenario. Root: S2-G1-6.
- **REDO.md:104** (ntp-dns, L2). The synced cadence's one-tick lateness fixed in U35 (LN178). Root: OF-247's cadence chain (S2-G4-13; REPORT section 4 item 6, a fix of a fix).
- **REDO.md:105** (memory-gc, L6). Four now-redundant console() bypasses kept. Root: S2-G1-9.
- **owner_report_items.md:54** (bus-i2c-spi, L3). Two readers whose setups fail together each rebuild the controller once (`_init_failed()`'s own-episode design; CO1 Q1, LN262). Root: `_init_failed()` (H, S2-G1-4; SCAN2 section 7 item 9, with `_rungs = 0` and I2C-5's report kept).
- **owner_report_items.md:57** (tests-hardware, L4). Provocation sets gained the NTP mid-flight group and E NTP_RETRIES; the other set rulings (:74; LN234, 241, 244, 258, 271). Root: the bench log check (REDO.md:60).
- **d3r_rec2_items.md:48** (generated-code, L5). An F811 exemption for the generated boot entries (LN204, LN206; restructuring into a function not taken). Root: B7's pre-bound `ended` (S2-G3-6 chain 2, S2-G4-14).

## 4. FORM rows

- **REG:749** (process, L4). U31 review by five read-only agents; all 53 findings fixed in six fix blocks. Smaller: one reviewer on src/ and the docs; machinery findings listed, fixed only where a gate passes wrongly. Scan: G.md:114 (U31: +1,623 test lines, 19 commits) and REPORT section 9; [Q2].
- **REG:752** (timing-waits, L4). FX3: the loop-lag scenario's report windows, F.3's lag.loop cell, tests_scripts/test_timing_budget.py on the consumer export. Smaller: F.3 as knowledge; no test pinning the table; the consumer helper on the twin side. Scan: E.md:160 ("Excessive: ... U31 added the timing budget"); S2-G3-2.
- **REG:753** (twin, L4). FX4: the straddling window read through Twin.wait_lines(), bounds re-measured, the window held at its p99. Smaller: as REG:752. Scan: E.md:160; S2-G3-2.
- **REG:754/b** (tests-unit, L4). FX5: expected_rows() six rows and a baud check, a bite per RD-4 class. Smaller: the rows as docs; one structural check at most. Scan: E.md:141, :160 (the static-contract layer).
- **REG:757/h** (twin, L4). The loop-lag bound is the device's smallest hard consumer (dev 925 ms, the others 6000 ms). Smaller: the same bound, computed on the twin side; smallest_hard_consumer()/HardConsumer out of buildgen. Scan: S2-G3-2.
- **REG:764** (process, L4). U32 review by four agents, 26 findings, seven fix blocks. Smaller: as REG:749. Scan: G.md U32 row; REPORT section 9.
- **REG:768** (tests-unit, L4). FX4: test_task_tops/test_task_inventory tightened (no else/finally, no raise in the Exception arm, no generated module creates a task). Smaller: the rule in G.2 and review; at most one shallow check. Scan: E.md:160 ("Excessive: ... U32 the task tops").
- **REG:769** (tests-unit, L4). FX5: the fault-or-warning scan enters handlers; RECORD_FORMATTERS pinned to FIELD_FORMATS. Smaller: as REG:768. Scan: E.md:141, :160.
- **REG:773/f** (tests-unit, L4). RD-4: pairs 1-7 as reasoned `_ALLOWED` rows of the fault-or-warning scan (pair 8 is REG:771). Smaller: no allow-list for a scan nobody owes. Scan: E.md:141.
- **REG:773/h** (tests-unit, L4). The task-top check's scope: create_task() targets and start_server() callbacks. Smaller: as REG:768. Scan: E.md:160.
- **REG:783/b** (ntp-dns, L5). Question 7's form (LN11): a second clock flag ntp_clock_valid() beside utc_now()'s. Smaller: one flag for every reader (~5 lines; the two answers in one /status go). Scan: S2-G4-15.
- **REG:795/h** (supervisor-reset-watchdog, L1). LN56: each store reset takes the lowest free bit of a 29-bit set (overlapping resets). Smaller: one reset at a time. Scan: REPORT section 5 row "overlapping error resets".
- **REG:832** (webserver-rest, L5). SF-B8: the unavailable marker for chip-config read failures (BMP3XX, ISL29125, SCD30, the flat GET). Smaller: the base producer and one JS check. Scan: S2-G4-17; SCAN2 section 3 row "unavailable-marker producers beyond the base".
- **REG:843** (bus-i2c-spi, L1). SF-A01: a data-byte NACK is EIO (a confirmed gap). Smaller: ~4 lines instead of ~35. Scan: REPORT section 5 row "I2C short-ACK write path"; C.md I2C-6 (X).
- **REG:855** (generated-code, L1). SF-A14: one write_reset_record() on the boot entry's exit path (labels 21/22, a confirmed gap). Smaller: the labels stay; BaseException -> Exception and no pre-bound `ended`. Scan: S2-G4-14; SCAN2 section 7 item 6.
- **REG:879/b** (webserver-rest, L3). SF-M4-01: Microdot's print routed through our wrapper (WS-9). Smaller: a 3-4 line rebind that sets the C-stack flag and prints. Scan: S2-G4X-8, S2-G2-8.
- **REDO.md:16** (core-logging, L2). Seven narrowing comments on branches kept for the type checker. Smaller: a typing-side form (an assertion or cast), so the branches go. Scan: S2-G4-22; SCAN2 section 9.
- **owner_report_items.md:9** (twin, L4). The Unix-port idle-poll skip per file, its direct test and an E.6.6 allow-list row (:21-31; LN245, 250, 252). Smaller: OF-243's one toolchain override at the root, or the measured time accepted; no per-file helper or allow-list row. Scan: REPORT section 11 (the poll gap as knowledge); OR20: "Only if there is no alternative, and keep tiny anyway".
- **owner_report_items.md:80** (twin, L7). A booted task graph's traffic counts as reach, "the conservative reading of the device rule" (LN274). Smaller: the subject's own reach under the owner's dedup rule. Scan: REPORT section 11 (the per-wiring twin tests: 15 lanes); PICTURE L7 ("Conservative" means the smallest change).
- **owner_report_items.md:112** (uart, L1). B91: dev's echo streamed from the stored pieces through read_at() (agent). Smaller: the echo-only half goes (read_at(), -13 lines). Scan: SCAN2 section 6 and S2 chain 9 (scan2/G4.md:557); REPORT section 5 row "PieceBuffer".
- **owner_report_items.md:234** (ntp-dns, L1). The UDP wait ends at its own deadline (LC1's UDP part). Smaller: the pre-audit loop (it "never lost a cancel"; only the deadline's precision differs). Scan: B.md UDP-4 (C); scan2/G4.md:555 chain 8.

## 5. OWN rows

- **REG:109** (wifi, L7). A station on the hotspot gets its own LED pattern (1500/1500 ms). [Q7] (scan2/G2.md:369: R, form only); the hold question: OR150 "1: a, because the user may want to do other settings after setting the wifi". Built: follows; form only.
- **REG:754/a** (config, L6). The budget row `stall.flash_program` (the whole 2129 ms flush) accepted with each crossed consumer's outcome. owner, 2026-10-22 06:32 (REG:799): the stall finding "closed as an accepted degradation" among the steps answered "your suggested next steps are fine". Built: follows; pair C9 with the review note on uart-flash-erase-overrun.
- **REG:757/c** (docs-records, L5). RB-7: the tunables register pins the pattern literals. OR30: "Search the project globally for such parameters, make a list and document at an appropriate place. That list needs to be updated on changing parameters". Built: follows; the register's size is DR7's.
- **REG:757/e** (config, L6). RD-3's accepted degradation tagged in F.3. owner, 2026-10-22 06:32 (REG:799). Follows.
- **REG:762** (supervisor-reset-watchdog, L3). The task-top rule (blocks C4 and L1, SPEC G.2). owner, 2026-10-21: "The task logs shall then be handled by their creators in general and the caveats are okay as they are inevitable." Built: follows; its static check is REG:768 (FORM).
- **REG:763** (supervisor-reset-watchdog, L1). No level-0 death counter. owner, 2026-10-21: "Keep as is, no added complexity." Built: follows (no code).
- **REG:770** (docs-records, L5 misfit). FX6 docs, among them README.md's "a session never flashes `wozi`" (RC-3). review note wozi-move-owner-operation (2026-10-02): "For all normal builds, especially WoZi, there are no such specialties and they shall be removed from the docs." Built: partly: CLAUDE.md:191-199 still opens "WoZi is the exemplary/base variant ..."; SPEC:2013, devices/wozi.toml:1, tests_hardware/README.md:1234 still say "never physically flashed" (OF-235, routed to U36). Contradiction C1.
- **REG:778/a** (docs-records, L5 misfit). R-6: CLAUDE.md's two wozi sentences narrowed to sessions. Words as REG:770. Built: partly; gap as REG:770 (C1).
- **REG:783/a** (ntp-dns, L7). Question 7: timestamping kept once stale, TimeStale in /status and on the website. owner, 2026-10-21: "Clock time: Option b, but with a flag in /status showing it might be stale. Should be visible on the website as well". Follows.
- **REG:783/c** (supervisor-reset-watchdog, L2). Question 2: no reboot when no read timer starts. owner, 2026-10-21: "a - if the shortage came each boot, this would be a malformed firmware, which would already be seen in the tests". Built: follows (no code).
- **REG:783/d** (driver-scd30, L3). Question 4: the SCD30 soft reset at every start. owner, 2026-10-21: "a - the scd30 has its own processor and it should be rebooted along each restart". Built: follows (no code).
- **REG:783/e** (uart, L4). Question 5: dev's UART hazards proven under API load. owner, 2026-10-21: "b - system shall be proven stable unter max load allover"; form: "Do as you recommended, clever solution!" (LN176). Follows.
- **REG:784/a** (twin, L8). Question 1: the grkizi relaunch crash closed, its recurrence made visible. owner, 2026-10-21: "a - if not reproducible by what you already did, probably really a glitch. if you made sure it won't be overseen ... this is fine." Built: follows (a signal death fails Run 5c by name; no retry).
- **REG:784/b** (docs-records, L5). Question 6: the comment-length rule. owner, 2026-10-21: "c". Built: follows (_WRAP_WIDTH = 120).
- **REG:785** (tests-hardware, L6). Question 3: the extra-write flag's cap. owner, 2026-10-21: "option a". Built: follows (docs restated).
- **REG:787/b** (licensing, L7). R-11: captive DNS 2019, p-doyle, no NOTICE, Apache-2.0 AND MIT scoped to DNSQuery. review licence-notices "ok" (2026-10-02). Follows.
- **REG:795/a** (uart, L4). The hazard mode's form: dispatch-only, bounded, three of the set (LN12, 31). owner, 2026-10-26: "Do as you recommended, clever solution!" (LN176); the exception in REG:801. Follows.
- **REG:796** (config, L6). CHECKLIST 24: the five wear decisions (a)-(e) put as questions. owner, 2026-10-26: (a) "Yes, keep it" (LN168), (b) "Keep the entry." (LN169), (c) "Yes, correct the wording as proposed" (LN172), (d) "But yes keep them of course" (LN175), (e) "Do as you recommended, clever solution!" (LN176). Built: follows; the row still reads "For the owner as questions" (REC2 owes the answers).
- **REG:797** (process, L7). The 2026-10-21 answers landed; the arduino/ exclusion's words added. Words as REG:783-785; owner, 2026-09-30: "No, it stays fully out of the audit". Built: follows; question 7's form is REG:783/b.
- **REG:798** (docs-records, L6). The least-wear rule made central, with two guards. owner, 2026-10-22: "... a completely central important rule." and "a condition strictly to be avoided by rule and nothing you were allowed to decide without even asking". Built: follows (test_firmware_write_sites.py is on E.md's keep list).
- **REG:799** (config, L6). The config write back to one single write. owner, 2026-10-22 06:32: "your suggested next steps are fine (go back to the single write)"; "No need to do wear assessment". Built: follows (block Z).
- **REG:800** (process, L1). The pillar screening. owner, 2026-10-22: "Yes, go ahead with it, and prove your checks really find their targets." Built: follows; the three items it kept are REG:795/i-k.
- **REG:801** (uart, L6). The UART link's test code as a module exception. owner, 2026-10-22: "So this is a substantial exception from the usual scheme, but for good reasons." Built: follows (CLAUDE.md, SPEC, test_uart_link_bench_only.py).
- **REG:802** (process, L1). The cleanups Z, M, O, J under the owner's condition. owner, 2026-10-22: "the cleanups are fine as well, as long as their intended behavior and resilience are either unaffected or even improved." Built: follows; block O (the Unix-port int-address branch out of the product) also fits OR36.
- **REG:804** (webserver-rest, L3 misfit). G1b-G3: the refusal's FRAM trace bounded at one per-call timeout through the existing parameter; every pre-close trace under it; trace-before-close kept "as the pacing it is"; the FRAM chunk's write order fixed. [Q9]; the parameter "(the preferred option) and ideally set at one common place" (LN107). Built: follows; on the refusal arm the trace-before-close placement is obsolete with OF-254's root (SCAN2 section 7 item 7, S2-G2-7: close, then trace, as the pre-audit design). Pair C4.
- **REG:805** (webserver-rest, L7). The record row of REG:804 (agent decision accepted by the owner). [Q9]. Built: as REG:804.
- **REG:806** (process, L8). The order after U35 and the agent load. owner, 2026-10-22: "I will start the hardware session once U35 is done and defer U36"; owner, 2026-10-21: "Don't overdo it, don't interrupt them". Built: follows; the 2026-10-26 go on preparation ("preparing the next units is fine") is not yet in the row (d3r_rec2_items.md:86).
- **REG:819** (driver-scd30, L7). SCD30 temperature offset rounded (folded, already the end state). OR101: "My decision: Fix the bugs" (round-to-nearest in OR101.a's list). Follows.
- **REG:824** (uart, L3). UARTRSR OE overrun fails the frame. OR146: "if the ring buffer of the UART ever is filled / overflows, the sender must be aware that something went wrong. This must be always reliable". Follows.
- **REG:825** (storage-fram, L6). The per-owner CRC seed (SF-B1). owner, 2026-10-28: "The FRAM idea of yours is good, keep it!"; a confirmed gap (REPORT section 3, layout shift). Follows.
- **REG:831** (wifi, L7). SF-B7: an unknown WLAN state apart from disconnected (WF-17). [Q7] (scan2/G2.md:369: R, form only). Built: follows; form only.
- **REG:842** (buildgen-toml, L6). SF-B18: generator writes atomic (already covered). OR23.a: "yes to all three" (A.U20.17's "on error no partial output remains", D.md H2). Follows.
- **REG:857** (wifi, L7). SF-M2-01: an empty SSID returns to the hotspot directly (WF-5). owner, 2026-10-28: "WiFi stays valid." and "We thoroughly discussed the WiFi issues and I decided everything already." Follows.
- **REG:859** (wifi, L7). SF-M2-03: three persisted Wi-Fi warnings (WF-13, WF-14). [Q7] (scan2/G2.md:369: R, form only). Follows.
- **REG:860** (wifi, L7). SF-M2-04: the hotspot-client LED pattern; the hold question. OR150: "1: a ... it only must be sure that once no clients are connected to the hotspot anymore, the device will try to connect"; [Q7] (scan2/G2.md:369: R, form only). Follows.
- **REG:867** (config, L2). SF-M1-04: a directory at a config path listed in ConfigFaults. OR138: "Unreadable or damaged files should be visible in some status field, not silently swallowed." Follows.
- **REG:879/a** (core-logging, L3). SF-M4-01: one exception handler in start_tasks() through the level-gated logger. owner, 2026-10-26, Q6: "Option a" (report_unretrieved silent at level 0); S2-G4X-7 keeps it. Follows.
- **REG:888** (wifi, L7). OR150 folded at U19. OR150, owner, 2026-10-08: "1: a" and "So that 5s leave and connect is the correct behavior." Built: follows (an end-to-end test).
- **REG:889** (wifi, L7). OR151 folded at U22. OR151, owner, 2026-10-08: "Don't permanently switch WiFi off, only stop retrying to connect." Follows.
- **REG:890** (wifi, L7). OR152 folded at U22. OR152, owner, 2026-10-08: "Point 1: Unify it. Simplify it." and "yes, record it that way". Follows.
- **segfault-not-reproduced** (twin, L8). The relaunch crash to the question list. Words as REG:784/a. Follows.
- **end-of-execution-review** (process, L7 misfit). "Execution never stops to ask; it takes the more conservative, more reversible option and logs it for you.". OR2: "Once the audit is started, it should run self-contained and uninterrupted."; OR2.c: "yes, that matches". Built: gap: "conservative" was applied as most protective, not as the smallest change (PICTURE L7, DRIFT section 2.5), and a review only at U37 let 708 rows pile up; this decision review stands in for it.
- **REDO.md:9** (process, L7). All firmware lands in U35. owner, 2026-10-26: "2. Firmware really complete, don't push fixes to future units". Follows.
- **REDO.md:12** (core-logging, L5). SensorReader `logger=` restored with its test. owner, 2026-10-23: "Always regard the modules as libraries, not every feature must be immediately used, as long as it is a real feature". Follows.
- **REDO.md:26** (website, L7). OF-139: light-theme contrast >= 4.5:1. OR132: "2a". Follows.
- **REDO.md:31** (webserver-rest, L3). F4a: OF-122's listener-close guard and the third modlwip patch. owner, 2026-10-26: "fix in the patched version and monitor upstream for real fixes, as soon as upstream is fixed drop the patch." (all three patches, LN170). Built: follows (a confirmed gap, REPORT section 3).
- **REDO.md:31/b** (generated-code, L3). F4b: OF-107's loop-end record. owner, 2026-10-26: "Event loop fallback: option b is fine." Built: follows; form only: BaseException width and the pre-bind (S2-G4-14).
- **REDO.md:36** (twin, L4). Run 11's calibrated leak check (80 / 4.0 / 100 ms). owner, 2026-10-23, Q1: "This is okay, go ahead." Follows.
- **REDO.md:63** (tests-unit, L4). CFr: plants only for complex measurement checks. owner, 2026-10-23, Q2: "Planting faults is a good measure for complex measurement tests ... but not required for the straightforward tests". Built: follows (39 not planted, K.10 restated).
- **REDO.md:67** (twin, L5). CMr: tests run on every device whose wiring they reach, deduplicated. owner, 2026-10-23: "Single device tests with different wiring should actually be avoided, so these tests should go for all devices." and "matrix deduplication is something different!" Built: follows; its cost (REPORT section 11: 15 lanes) is the M8 point.
- **owner_report_items.md:88** (twin, L8). The stale task pointer left as is, a BACKLOG bundle of upstream findings. owner, 2026-10-27: "So we should report it later and bundled, if at all." and "Yes, let's do it like that". Follows.
- **owner_report_items.md:97** (config, L2). The runtime dict check on the write results removed. owner, 2026-10-27: "if the check you remove really solely covers typing breakages and nothing else it can go (option b)". Follows.
- **owner_report_items.md:111** (uart, L3). A PieceBuffer that cannot be built is a UART fault (A17, B90). owner, 2026-10-27: "Do option (c) as you recommended". Follows.
- **owner_report_items.md:122** (core-logging, L2). 14 typing-only checks removed, 12 int checks kept (MicroPython refuses a bool there). owner, 2026-10-27: "A strong hint for an unnecessary check is that it is proven to be fully covered by typing adherence alone, and that it is unreachable with today's code". Follows.
- **owner_report_items.md:157** (tests-unit, L5). The waits scanner and the real-wait tags (N10, N11, N11b-e). OR30: "for example, runtime and timeout parameters for test suites ... make a list and document at an appropriate place". Built: follows; its scale (REPORT section 11: 7 lanes) is DR7's.
- **owner_report_items.md:198** (ci-tooling, L8). The CI apt mirror check and cache, the pass rate derived (LN320, LN334). owner, 2026-10-27: "Maybe it actually would be good to investigate."; the fix proposed first and taken as "do it like you proposed" (LN334). Follows.
- **owner_report_items.md:246** (process, L8). A finite closing ledger. owner, 2026-10-28: "I just want to make sure that you set up the process such that it can finished and is not designed self-sustaining / will never end". Follows.
- **d3r_rec2_items.md:105** (docs-records, L8). Part F paragraphs and the BACKLOG upstream bundle. Words as owner_report_items.md:88. Built: follows (owed to D3r).
- **LN153** (process, L7). Complex topics asked in prose. owner, 2026-10-26: "STOP THOSE MULTIPLE CHOICE QUESTIONS FOR COMPLEX TOPICS!!" Follows.
- **LN163** (process, L7). CHECKLIST 1c: nothing starts on a question before an explicit answer. owner, 2026-10-26: "You are way too fast. You ask questions you flag as "decision needed" and don't even wait 5 minutes". Built: follows; broken once more at LN365 (named).
- **LN175** (process, L7). CHECKLIST 1d: a test-only change with no wear and added coverage is the lead's. owner, 2026-10-26: "That's actually a combination you don't need to ask me for." Built: follows; since 2026-10-28 bounded by the tiering ([Q3]).
- **LN188** (docs-records, L5). OF-186: `# @include` lines count as code. owner, 2026-10-26: "These lines are not comments, they count as productive code. Option B." Follows.
- **LN190** (supervisor-reset-watchdog, L7). Question 9: the boot-phase check after the record check. owner, 2026-10-26: "Option b, should be in line with the prior similar decision". Built: follows; the torn+phase consequence named (practically unreachable).
- **LN222** (twin, L4). CMr1b: one run per group of devices with identical read configuration. owner, 2026-10-23: "then it is a good thing as it saves time and is not actually device specific". Follows.
- **LN260** (process, L8). The budget measures, refined in LN261. owner, 2026-10-27: "same quality, same result, no major slowdown, but less budget usage. Remove unnecessary hogs and keep the good schemes." Follows.
- **LN278** (process, L8). The tool-call seam a goal, then no seam (LN280). owner, 2026-10-27: "so it should be a goal, but not a hard limit, I'd say" and "handing back if it's not closed is extra effort". Follows.
- **LN291** (process, L8). Intermediate snapshots as tree-only commits. owner, 2026-10-27: "Whenever there is a close good opportunity, commit and push intermediate results. I don't want to lose anything again." Follows.
- **LN381** (process, L7). A decided topic is never re-asked. [Q7]. Follows.
- **LN113** (webserver-rest, L3). "Connection task failed:" stays a direct, unbounded err_s. owner, 2026-10-22: "Fine, keep it." (LN115). Follows.

## 6. SUP and CHECK rows

### SUP

- **REG:748/b** (supervisor-reset-watchdog, L7). OF-36 moved to U32, the default standing. Superseded by: owner, 2026-10-21: "Keep as is, no added complexity." (REG:763). Later one: stands; no code, as the default was.
- **REG:748/c** (config, L1). OF-225 (a config flush stretch of 2129 ms) routed to U35, where it became R-9's yielded slices. Superseded by: owner, 2026-10-22 06:32: "your suggested next steps are fine (go back to the single write)" (REG:799). Later one: stands; the stall is an accepted degradation, the single write is back.
- **REG:765** (driver-sgp40, L7). FX1: the VOC backup gated on ntp_issynced again (legacy), _clock_was_set gone. Superseded by: owner, 2026-10-21, question 7: "Clock time: Option b, but with a flag in /status showing it might be stale." landed as SgpBackup(fram, ntp.ntp_clock_valid) (buildgen/codegen.py:492 at 11b66cd8). Later one: stands; LastTaskEnd's description follows OR128 "(a) Yes: publish it as `LastTaskEnd` in `/status`.".
- **REG:793/b** (config, L6). R-9: the config flush in yielded slices. Superseded by: owner, 2026-10-22 06:32 (REG:799). Later one: stands.
- **REG:830** (wifi, L7). SF-B6: a failed stations query is "unknown", the timer untouched. Superseded by: OR152's rule, owner, 2026-10-08: "yes, record it that way" (the stations check back to the legacy rule, REG:890). Later one: stands.
- **uart-chunking** (uart, L7). Parked on the owner's deferral (2026-09-26). Superseded by: the owner's go-ahead note (2026-10-05, "withheld"): "I want one parked item to be fixed: the UART chunking for large allocations.". Later one: stands; built: PieceBuffer (B.md UC-3, R), the ring allocated in the boot setup batch (B.md:1532), the owner's option (c) catches.
- **LN157** (process, L7). "And for sure test and verify it in both twin and real hardware" read as the go-ahead for OF-107. Superseded by: owner, 2026-10-26: "You are way too fast." and "You papered over the event loop fallback as well" (LN163, 165), then "Event loop fallback: option b is fine." (LN166). Later one: stands.
- **LN316** (ci-tooling, L8). A Playwright install red read as external, no action. Superseded by: owner, 2026-10-27 (LN320): "The CI failures are there for several days ... so there must be another reason.". Later one: stands (CI1 root-caused it).
- **LN357** (process, L4). CMr1n and RF1 kept in U35 ("I don't actually want to cut back or trade anything"). Superseded by: owner, 2026-10-28 06:37 (LN362): "The verification machinery never was the goal of "perfection". ... The audit verification machinery is just a temporary tool.". Later one: the later words set the tier (pair C6).
- **LN363** (process, L7). The read-only inventory started on the owner's agreement with the conclusions. Superseded by: owner, 2026-10-28: "Stop, I didn't give ANY go ahead yet" (LN365). Later one: stands.

### CHECK (needs verification; not decided here)

- **REG:793/a** (storage-fram, L2). R-8: an RDID probe on a blank read (landed with no bound, LN28). The one check: hardware-round item 2 (REPORT section 7): read the FRAM SO line with the chip absent on dev; 0x00 -> the lost-chip chain goes with the probe (S2-G4-5, ~60 lines); 0xFF -> keep only the status-bit-0 refusal (~4 lines).
- **REG:853** (supervisor-reset-watchdog, L2). SF-A11: the storage auto-unpause a deadline on the status pass, not a one-shot (A-S21, H). The one check: hardware-round item 6 (REPORT section 7): on dev, count queued soft callbacks across a config flush; 8 or more seen -> keep the deadline; never -> the pre-audit one-shot with its catch.
- **REDO.md:24** (storage-fram, L2). OF-250: erase_ready() and get_write_protected() in the chip-loss window. The one check: as REG:793/a: the window exists only with the lost-chip chain (S2-G4-5).
- **owner_report_items.md:62** (supervisor-reset-watchdog, L2). BR2's three fixes: an erase preflight raise wedging the shutdown gate, a raising auto-unpause, a raising boot-signature log line. The one check: at the parent of 7008730e, name the raising call at each of the three sites and read it in v1.29.0: anything but a MemoryError at call entry -> keep the fix; only that -> revert under F.2's restored rule (PICTURE M1).

## 7. Contradictions and counterparts

**Contradictions** (both sides, sources, which stands):

- **C1. wozi in the docs.** REG:770 (RC-3), REG:778/a (R-6) and REG:779 (OF-235 routed to U36) narrow "never physically
  flashed" to "no session flashes `wozi`". Owner, review note `wozi-move-owner-operation` (2026-10-02): "For all normal
  builds, especially WoZi, there are no such specialties and they shall be removed from the docs." The owner stands. At
  `11b66cd8`, CLAUDE.md:191 still opens "WoZi is the exemplary/base variant ..."; SPECIFICATION.md:2013,
  `devices/wozi.toml:1` and `tests_hardware/README.md:1234` still say "never physically flashed".
- **C2. Who chose the product console lines.** REG:854 and REG:871 record SPEC I.4(e)'s console() lines with the
  source "(owner, 2026-10-20: "Option 1 is good")". REG:729 records that option as "logging on, at error level or
  above, in the unit tests that can actually run out of memory": test side only. The owner's scope stands; the product
  lines are agent decisions (OBS, S2-G1-9). SCAN2 section 3 reads the option the same way.
- **C3. Silence as approval.** Owner step `review-and-go-ahead` ("silence on a routine batch counts as approval")
  against OR48.a ("recorded decisions I took (not the session agent)") and the owner, 2026-10-28 ("Decisions I really
  took are still valid."; "The OK in the review stay valid."). The owner stands.
- **C4. The refusal path.** REG:804/805 and LN106 keep the refusal's trace before its close, with the owner's "Solutions
  you proposed agreed.". The pre-audit design at `25caf528` `src/asy_webserver_service.py:697-698`: "Reject-when-full
  (decision 3): accepted by asyncio, then closed with no response ever written - cheapest, doesn't risk the rejection
  path itself becoming a resource consumer." SCAN2 section 7 item 7 (the lead) restores close-then-trace on that arm;
  the owner-agreed bound becomes obsolete there with OF-254's root and stays on the other arms. Facts for the lead: the
  agreement was given without the pre-audit rationale in view; no owner words for "decision 3" were found here.
- **C5. New checks and time.** REG:795/c and LN196/b ("a new check is not growth of existing work", LN20, 25, 66)
  against the owner: "Test duration going up like this is anyhow something to fix - not cutting back strictness, but
  making it more efficient" (rulings file, in force) and OR39. LN20 quotes the owner's direction in the same note that
  sets the exemption. The owner stands.
- **C6. Two owner statements, one morning (facts for the lead).** 2026-10-28 05:30 (LN357): "I don't actually want to
  cut back or trade anything, I just want to make sure that you set up the process such that it can finished and is
  not designed self-sustaining / will never end". 06:37 (LN362): "The verification machinery never was the goal of
  "perfection". ... The audit verification machinery is just a temporary tool." LN357 kept CMr1n and RF1 on the first;
  the second sets the effort tier for both (LN357 SUP, closing_ledger.md:8 DIFF).
- **C7. CONFIG_LOST.** REDO.md:18 (LN147, kept) against SCAN2 section 3 and S2-G4-21 (W69 goes; its false positive
  OF-184 is verified). Agent against scan; the scan stands. The owner's first-boot rule ("If things happen at first
  boot, they must be triggered by evidence (e.g. no config available ...)") allows such an entry, it does not ask for one.
- **C8. A removed library method.** REG:787/a (write_and_recvfrom() out, 2026-10-21) against the owner's later rule
  (2026-10-23): "Always regard the modules as libraries, not every feature must be immediately used, as long as it is a
  real feature" and "Dead code: Double check it's really dead code." The owner stands; the method was unused only
  through DNS-4 (H).
- **C9. Two owner statements on a lost UART frame (facts for the lead).** Review note `uart-flash-erase-overrun`
  (2026-10-02, "change"): "this should not happen as a random side effect. Either don't lose a frame in general
  (preferred, if achievable with adequate effort), or halt the UART in some way". Owner, 2026-10-22 06:32 (REG:799):
  the stall "closed as an accepted degradation", its consequences listed as including "on dev's bench link one failed
  and resynced transaction". The DMA ring (OR141) answered the first; the second accepts the flush's residual.
- **C10.** REG:765 (FX1 back to `ntp_issynced`) against question 7, "Option b" (REG:783/a). The owner stands; the head
  follows (`buildgen/codegen.py:492`).
- **C11.** REG:771 and REG:826 (W67 kept and refined) against SCAN2 section 3 (W67 goes). The scan stands. The 120 s
  deadline itself stays (SCAN2 section 7 item 2 over S2-G4-9's H), since the owner-answered text names "a deadline".
- **C12.** REG:795/i-j (the handler guard and `_shutdown_task` kept "under the owner's no-regression condition")
  against OR36. Both serve tests only, so removing them regresses no product behaviour and the condition does not
  hold them. OR36 stands.
- **C13.** REG:750/c (E115) against A-S16 and S2-G3-7. The scan stands.
- **C14.** REG:792 (13-15 lanes) against OR107 and OR145. The owner stands.
- **C15. "Conservative".** The bundles REG:757, :773, :780, :789, :795 call each decision "conservative and
  reversible". PICTURE L7 reads OR2.c ("yes, that matches") as "the smallest and most reversible change, which for
  solid code is usually none". The DIFF and OBS rows above are where the protective reading added code; the agent
  label does not make them the owner's.

Inside the set, no pair contradicts: REG:757/h (FORM) and REG:757/l (DIFF) both move `smallest_hard_consumer()` out of
buildgen; REG:793/a and REDO.md:24 are one CHECK (hardware item 2); REG:827 and REG:866 are one DIFF; REG:833 and
REG:847 are one DIFF; REG:878 and owner_report_items.md:232 give the same answer (revert NP-5).

**Likely counterparts in other parts' sets:**

- **DR1 (review page):** `float-sleep-everywhere` and REG:751; `task-names-required` and REG:773/a; `licence-notices`
  and REG:787/b; `licence-checks` and REG:787/c; `c-stack-reboot` and REG:750, REG:757/f, REG:807/a;
  `led-request-internal-queue` and REG:771, REG:826; `uart-flash-erase-overrun` and REG:754/a, REG:799 (C9);
  `wozi-move-owner-operation` and REG:770, REG:778/a (C1); `failed-push-no-flash-write` and REG:799; the 295 unanswered
  items and C3.
- **DR3 and DR4 (U11-U23):** each parked delta's landing rows. U11: SF-B3/SF-M1-07 (ConfigUnpersisted), SF-A10
  (ResetBits), SF-A11 (the unpause deadline), SF-B5 (the tick re-arm), SF-M1-01 (W69). U15: SF-B9/SF-A05 (BMP3XX),
  SF-A04 (SCD30 W73), SF-B11 and SF-M3-04 (ISL29125). U16: SF-M3-05, SF-M3-06 (SGP40), SF-B12/SF-M1-03 (E28). U18:
  SF-B15, SF-A12 (DNS, UDP), the SF-M2 Wi-Fi rows. U22: SF-B2, SF-B17, SF-M3-01, SF-M3-09 (notification, NeoPixel 300 s).
- **DR5 (U24-U30):** the memory-gate console lines (U30 lane X2), the C-stack escalation and its bounded write (U30),
  the I2C consumer rule (U20), DNS-4's move of the retry loop (U18 or later).
- **DR7 (Part N):** `system.escalation_entry_wait_ms`, `led.overlay_refresh_ms`, `led.signal_wait_ms`, the
  N10-N11e test-wait rows, the `l1.uart_comm_hazard_*` bounds, RB-7's pattern literals.
- **DR8 (agent-tagged text):** SPEC I.4(e)'s owner attribution (C2), the "conservative and reversible" tags (C15),
  CLAUDE.md:191's wozi rule (C1).

## 8. SAME rows (topics in the section 1 table)

- REG:748/a: OF-198 closed with the NTP retry's dropped fire as documented loss (knowledge, no code).
- REG:748/d: Routes only: OF-215 stage 3 to U35, OF-226 to U33, OF-227/228 to U36.
- REG:750/a: The reset record is written at the escalation's decision, before any entry wait (S2-G1-6 keeps it).
- REG:750/d: A supervisor fault resets with code 2, no new reset code.
- REG:751: One shared check_sleep_ms() makes every one-yield stand-in refuse a float as rp2's ticks_add() does (fake fidelity); counterpart DR1 float-sleep-everywhere.
- REG:755: FX6: scratch name in the scratch scheme, budget row, float-refusing clock fakes, T3's nested asyncio.run() fixed (CLAUDE.md segfault rule).
- REG:756/a: Feed-site bites re-anchored (test_watchdog_feed_sites.py is on E.md's keep list).
- REG:756/c: One shared wait recorder (ms_of()) replaces two local ones.
- REG:757/a: RA-6: `_frame_ms` stays the tests' seam; it is the product's own frame period (asy_neopixel_driver.py:74), tests adapt (OR36).
- REG:757/b: RA-7: ServingLimits keeps seconds and converts once.
- REG:757/d: RC-1: the settle sleep dropped with its tag (stricter, one wait fewer).
- REG:757/i: Load window 20 s derived from the storm and one report window; storm capped at the 5-read give-up streak.
- REG:757/j: A UART link's boot drain is the one wait a setup unit may take (lane C3).
- REG:757/m: The window after the load: one LED frame at p99, one DNS query at its maximum, on the owner's same-case precedent ("Then option b is fine", 2026-10-13).
- REG:757/n: Both machine fakes refuse a float timer argument (consistency with rp2).
- REG:758: Time growth accepted with causes (+13 % one file; dev's scenario job +88 s, then trimmed); its source is REG:752's scenarios; the general rule is REG:795/c.
- REG:760: Every CI job pinned to ubuntu-24.04; the installer takes either WebKit driver name.
- REG:761: U32 routes and re-points; OF-79 put to the owner (question 7, answered).
- REG:766: FX2: comment and silent-wording tests.
- REG:767: FX3: kill scenario waits one pass; task-top fakes raise RuntimeError; the firmware's name form at hand-built lists.
- REG:772: Block L1: `_serve()` ends in one top under the owner's rule, the slot released once; the refusal arm's order is REG:804.
- REG:773/a: R-2/R-3: task names required, no default (a default would exist for tests only); counterpart DR1 task-names-required.
- REG:773/b: R-5: the end record a name reference and an int, the dict built per read (OR110).
- REG:773/c: R-6: no runtime length check (the owner's typing rule, 2026-10-27).
- REG:773/d: R-7/R-8: lasttaskend in _FORMATS, one pin over the format sets.
- REG:773/e: R-9, R-12, R-18, R-19 (hardware parked); RA-1 to the owner; RA-2, RA-3, RD-6.
- REG:773/g: The shared UNEXPECTED code 23 for every new top, no catalog change.
- REG:773/i: U2's findings fixed in U32; B86 Class B; keyword start_tasks(); the killed task the FRAM chip watch (its escalation half stays, S2-G4-5); RECORD_FORMATTERS; D1/D2 wording; routes.
- REG:777: U33 two lanes; the whole tests_scripts tier once on the merge, not per lane.
- REG:778/b: R-1..R-5, R-7..R-24 and L-1..L-7: docs and bench wording (the M1 + S3b persistence flag, the SCD30 ambient-pressure row, the chroot list); R-8 cites an owner drop not re-verified here.
- REG:779: U33 closes and routes (OF-121, OF-230, OF-226, OF-234, OF-235 to U36: see C1).
- REG:780: U33 wording decisions; paraphrases marked as paraphrase.
- REG:782: Coverage-step growth routed as OF-236, closed as no regression (LN20).
- REG:786: U34 four lanes on disjoint files; tier once.
- REG:787/c: R-1..R-6, R-8..R-10, R-12..R-25 (Any sweep scope, Microdot pin text, Playwright keys, freezefs commit check, disallow_any_unimported to U37); counterpart DR1 licence-checks.
- REG:788: U34 closes OF-208, OF-96; routes OF-237..239.
- REG:789/a: A1/A2/T1/T2/C1 wording and the attribution test.
- REG:793/c: R-1..R-7, R-10..R-34: DrivenTime extended in place, the torn-write mapping by message identity, no code for OF-70/184/232/223/181, the UART wire untouched, hardware parked.
- REG:794: U35 closes and routes; OF-225 as accepted degradation (owner); U36 routes carry their route only (owner, LN108).
- REG:795/d: P1's items (:712 comment, B88, the codec sentence, step 118's poll unwritten, 128 in U35, 143's sentences, 67's file).
- REG:795/e: The LN23-LN104 block decisions not named apart (driven-clock forms, reader pacing, the mock's "Valid", virtual bounds, K's split headers): sound test design; the campaign's scale is M8.
- REG:795/f: LN31: no changelog row for the exerciser (not the protocol module); the stalled transmit left to the bench's raw script.
- REG:795/g: LN57: `_hazard_facts` in `_RUN_PHASE_ALLOWED` (follows the owner's hazard mode).
- REG:795/k: LN96: the captive DNS MemoryError re-raise kept (narrowing DNSQuery's handler would pause the server 3 s per bad datagram).
- REG:795/l: LN99: block M kept whole (the 2026-09-30 owner design's rule 3).
- REG:807/b: G1c: a 256 KiB chip-image copy taken in 4 KiB pieces with a size assert (the chunking technique, zero MemoryError rule).
- REG:821: A zero transmit timestamp rejected: a confirmed gap (REPORT section 3, 3 lines).
- REG:822: The chroot recipe gets Node (10 tests failed without it).
- REG:823: The chroot recipe uses a real clone.
- REG:834: SF-B10: the restamp kept as the owner's named exception, flag-first (the counter is REG:846).
- REG:837: SF-B13: the twin says so on a malformed state file and saves by rename (no silent false-blank evidence).
- REG:838: SF-B14: a capped ErrCount shown as 65535+ (a bound by construction, OR103).
- REG:844: SF-A02: a NACKed register byte is EIO (a confirmed gap, ~5 lines).
- REG:845: SF-A03: one SPEC sentence, no code.
- REG:848: SF-A06: the tested mask widened to OE|FE|BE, the same failure path (inside OR146).
- REG:849: SF-A07: no code unless the budget row shows the deadline crossed.
- REG:850: SF-A08: captive DNS drains per wake; with the confirmed one-yield-per-datagram fix (SCAN2 section 5).
- REG:851: SF-A09: the DHCP pool as a SPEC sentence.
- REG:858: SF-M2-02: cettime() gated on the clock being set (NTP-18, consistent with the owner's option b).
- REG:861: SF-M2-05: awrite() sets the pre-audit peer_gone flag (S2-G2-9 keeps it; HTTPDropped is the owner's).
- REG:862: SF-M2-06: a section refreshed before Apply (a stale form drops a field by construction).
- REG:863: SF-M1-02: a TypeError the work order would have introduced corrected before U16.
- REG:876: SF-M3-07: ResetErrors leaves `_valid_frames` (dev's diagnostic stays meaningful).
- REG:877: SF-M3-08: RP2040-E15 named in the README with a preflight version check.
- REG:880: SF-M4-06: the memory gate reads every attempt's log (no evidence lost).
- REG:881: SF-M4-08: the single-precision note and one scratch run.
- REG:882: SF-M4-07: the .uf2 copied atomically, the record written last.
- REG:883: SF-M4-09: the WLAN mode-switch row.
- REG:885: SF-M4-11: the README line for the 511-byte Ctrl-C trap.
- REG:886: SF-U0-07 (b): the pinned Node for the test.sh jobs.
- REG:887: SF-U0-08: one marker table for both conftests.
- REG:891: The bench reads the STA mode without a /networking field (the owner's "No STA-phase field is added to /networking").
- uart-streaming-get: Stays parked; needed only once a responder answers more than one buffer.
- uart-babbling-peer: Stays owed (no hardware for it); the cited owner decision of 2026-09-25 not re-verified here.
- held-sda-scope: Owed rows marked "needs a scope", never guessed.
- any-unimported-count: Measured and handed over with each site (REG:787 R-14).
- dependency-holdbacks: Conditional; an update never changes an owner-decided behaviour (OR129).
- firmware-pin-on-silicon: Conditional; holding the version back is the owner's choice.
- history-credentials: Conditional; the executor never rotates or rewrites history.
- send-stall-bound: Conditional to OR114 ("Do it this way"; "thoroughly test").
- twin-retry-question: Conditional; never triggered (Run 11's calibration found a window: owner Q1 "This is okay, go ahead.").
- citation-allowlist: Conditional.
- rollover-repeat: The owner decides on a repeat after a tick fix.
- hardware-rows-requeued: A red stops the round for the owner; never retried to green.
- datasheets-push-access: The owner's grant; access confirmed ("You have access to the datasheets repo", 2026-10-26).
- secret-scanning-setting: The owner's repository setting.
- hardware-go-aheads: A go-ahead per session conversation.
- bench-confirmations: Two facts only the owner can confirm.
- operator-round: The write budget stated and confirmed by the owner before the round; a step past it stops.
- close-and-merge: The merge and the tag only on the owner's agreement.
- session-1: Rounds R0-R6 in one conversation, wear stated per round, FRAM logs saved first.
- session-2: The release proof with and without the boot gc.threshold line.
- REDO.md:3: The redo builds on 656fc82 as is (the baseline reproduced, LN151).
- REDO.md:15: A dead reply bound removed with its proof.
- REDO.md:17: A test pins the hotspot-exit guard (a library guard; Wi-Fi settled).
- REDO.md:19: E51's uncovered lines classed feature/guard/dead under the owner's library rule.
- REDO.md:26/b: OF-245: six catalog codes named by biting tests.
- REDO.md:31/c: F4c: the silicon check prepared, read-only on silicon (LN185).
- REDO.md:38: TimeStale twin checks; the twin FRAM save limited to the used span (host wear); writes_at presized.
- REDO.md:48: T4r3: the 2**30 ticks runs (a planned step; confirmed an earlier proof, REPORT section 11).
- REDO.md:52: CE2r: a tracer death is reported (exit 3 with its reason), not silently undercounted.
- REDO.md:82: N4r: the probe holds NTP still; the tier order; host writes measured.
- REDO.md:84: N6: small test fixes found with no record.
- REDO.md:91: D3r, REC2, W10: docs to current state, records corrected, the close.
- owner_report_items.md:6: The per-file `_driven_modules` copies left; one shared helper later.
- owner_report_items.md:15: The CS settle fidelity gap left as is.
- owner_report_items.md:44: A wider skip declined: the interim helper's scope stays what was proven.
- owner_report_items.md:51: The rung counter steps on entry (a real double-clear fix, REPORT section 11); a rung cancelled in its lock wait counts as run.
- owner_report_items.md:60: `_set_dict_cfg`'s request-sized allocations accepted by reading (2048 B body cap).
- owner_report_items.md:106: The whole tier on every merge and every lane's final head (red tests reached int otherwise).
- owner_report_items.md:76: Overlap proofs that can no longer pass vacuously; the HTTP counterpart states what it proves (also :176, LN223, LN304).
- owner_report_items.md:83: The widening not dropped for time; a driven clock first (LN274).
- owner_report_items.md:137: The CRC16 red root-caused; no firmware change; the deadline on a driven clock; the silicon reading owed (LN289).
- owner_report_items.md:143: The FRAM read fault's log pair kept as it is (LN290 (a)).
- owner_report_items.md:150: Hazard tests at the shipped poll rates; a 1 s drain only on permanent stalls (LN297, 307, 313).
- owner_report_items.md:172: Port 53 isolated per process (a real cross-process test defect, reproduced).
- closing_ledger.md:21: Admission only for a firmware defect or a wrong deliverable; the rest routed; one follow-up lane; the load gate; the count in every report.
- d3r_rec2_items.md:78: D3r writes current state, never history bullets.
- d3r_rec2_items.md:86: REGISTER:806 gets the owner's 2026-10-26 go verbatim.
- LN150: No transcript reads by anyone (CHECKLIST 1b).
- LN170: No test.sh on a post-override head against the shared toolchain until one quiet rebuild.
- LN185: F4c re-briefed read-only: no writes to raw memory on silicon.
- LN196: N9: live reads through `resume exec` (every live read via sys.modules read nothing on silicon: a real test defect).
- LN207: `_restore_is_all_or_nothing` removed with the tests that exercised only it.
- LN219: The unreachable `return` guard kept under the library rule; a vacuous identity check dropped; no gc site added.
- LN224: The live tier's ~1000 leaked config files fixed and removed; N14's checkout-root leak and its guard (LN233).
- LN235: Pre-existing D.15 reorders reverted while the owner's question was open (then "Option d is fine").
- LN246: The coverage check's bound raised to CI's 95 min.
- LN286: ISL decode_status()/is_bus_fault_pattern() kept as declared API breadth (library rule).
- LN323: The factory-state hotspot test on the driven clock's default step, with its three conditions.
- LN329: TEST_TWIN_HOST dropped by host-run launchers (TH1); N15's extension (port-53 scenarios in test.sh) not taken.
- LN330: The runner's apt retry override left until a CI log shows its effect.
- LN335: No per-site comment at 65 mock-tier bus constructions.
- LN355: The NeoPixel overlay patch kept out of the tree, to the owner in prose.
- LN358: The lost cancel checked before acting, as the owner asked ("Check this first, especially if it is real at all").
- LN373: The hotspot default masked in the pushed paused-lane patch.
- LN112: OF-260 taken in: a dying thread is an error ("I just want to make sure no evidence to a bug ... is silently lost").

Facts (no verdict):
- REG:759: U31 gates and tiers.
- REG:774: U32 time growth.
- REG:775: U32 gates and tiers (FX8/FX9 loaded-host test fixes).
- REG:776: CI on U31's squash.
- REG:781: U33 gates.
- REG:790: U34 gate and CI.
- REG:791: U34 gate and CI.
- REG:803: U35 events (disk, restarts).
- REG:808: <G3> placeholder never filled (W10/REC2 owe it).
- REG:809: <GATE2> placeholder never filled (W10/REC2 owe it).
- REG:810: CI on U34 record.
- REG:811: <CI_U35> placeholder never filled (W10/REC2 owe it).
- owner_report_items.md:17, :32, :35, :40, :42, :69, :95, :104, :117, :136, :185, :219, :221, :228, :248 (lane and lead deviations, refusals, hygiene).
- owner_report_items.md:197 and LN329 (container restarts).
- LN370-LN372, LN374, LN377, LN384, LN385, LN388, LN390, LN391 (scan records, owner words recorded, launches).
