# DECISIONS: "all gaps closed, (really) agreed features implemented", checked from the decision side

Release head `S/wt-final` (`590cffcf`), against baseline `25caf528`. I read the inputs and the release through the
filter only. Every file:line below is in `S/wt-final` unless it names a branch.

## Verdict

- **The firmware and build chain hold the owner's decisions.** I located 65 owner-decided features or behaviours and 21
  confirmed gaps at the release head. All 86 are present (gaps closed, features in place), and none is reversed. Two
  owner-agreed record items are missing (DECISIONS-2 and DECISIONS-3).
- **Superseded rulings do not linger in code, the website or docs.** I checked 4 MHz, `TimeStale`, `ResetBits`,
  `ConfigUnpersisted`, the notification block, reset code 4, the NTP doubling, `err_nomem`, the 8 KB ring, the 6,400 B
  send buffer, the 100,000 B heap bound, the half-limit C-stack bound, the double stripes, the build-date stamp, the
  demo launcher and the 300 s and 120 s timed checks.
- **The exceptions are all in the records, not the product:**
  - BACKLOG.md and `tests_hardware/README.md` were never reconciled with the last bench round, and one D-step item was
    left in BACKLOG.
  - The owner's late general rulings (10-28, 10-23/11-09, 11-11) are not written into the standing rules.
  - One small BACKLOG entry the owner agreed to on 10-27 was never written.

## Shape since the baseline (decision view)

- **Removed on the owner's word, and gone:**
  - `/status` keys `ResetBits`, `ConfigUnpersisted`, `TimeStale` and the notification block (`PauseTime` kept);
  - reset code 4; the wet-bulb cold-dry corner; `err_nomem()`;
  - the boot entry's traceback print; the page's build-date stamp and its no-JSON banner;
  - the double stripes; the incremental CRC and the >32-bit widths; the demo launcher;
  - the NeoPixel 300 s rewrite and the LED's 120 s give-up; the NTP doubling with its two device settings;
  - the Stull PDF.
- **Added on the owner's word, and present:**
  - reset codes 20, 21 and 22, with `machine.reset()` after a loop end;
  - a fixed 60 s NTP retry while unsynced; WLAN console lines on each state change;
  - SCD30 values marked unavailable while it is stopped; the `/status` piece-writer yield with the flat rule;
  - FRAM at 8 MHz, each status byte its own write, no CS settle pauses; the native CRC engine;
  - `TCP_SND_BUF` 1,600 B (chosen on measurement); the Country help text; release 2.0;
  - every website item (`65535+`, solid stripes, Back history, decimals, tones, inert drawer, reload, confirmations).
- **Kept on the owner's word:**
  - the FRAM owner seed, the RDID retry, the code-9 scheme and the newest-entry rule;
  - the C-stack reboot in its small form (12 `report_if_fatal` references in 6 modules, down from ~120 sites);
  - the no-caller library functions (the O2 list) and the default-value helpers;
  - the UART link as a dev-only module that is the only switch for its hazard code.

## Findings (most important first)

### DECISIONS-1 [class R] [VERIFIED] The bench "owed" list and the reset-code table still show the last round's passed runs as not done
- **Where:**
  - `BACKLOG.md:15-309`, the "Real-hardware work still owed" section: its item list is identical to the one at
    `37216f41` (2026-11-10, before the last round), except that the modlwip item is gone;
  - `BACKLOG.md:31-44` (M1 + S3b), `:268-277` (S4), `:278-288` (G6), `:23-30` (flash tier, "no full flash-tier run
    since"), `:368-380` (the final-wiring requirement);
  - `tests_hardware/README.md:957-972`: every reset code's "on silicon" column reads `not yet run`.
- **What:**
  - **S4, the six-hour soak:** BACKLOG says "last run 2026-09-08 at the 10-minute `--duration mid`". But
    `SPECIFICATION.md:2509-2510` records the six-hour HTTP soak of 2026-11-12 (6 of 39,132 GETs failed), and the
    bench's "10g PASS" entry agrees.
  - **G6, the tick rollover:** owed in BACKLOG. Bench commit `4bc80014` on `origin/claude/u35-bench-campaign` reads
    "15 PASS on the rerun" (2026-11-12).
  - **M1 + S3b:** "needs the owner at the bench". M1 passed on 2026-11-13 (`157613c4`). S3b's sweep run 7f ran on
    2026-11-12 with 11 passed, and its envelope test is not among the 5 failures (`074df619`).
  - **The flash tier:** it ran in full on the final image (`1a656af7`, 4b on `840a2213`).
  - **Reset codes:** code 7 passed alone (`c2c68b35`), and code 1's power-cycle run passed (`33530e2e`), yet the
    table still reads `not yet run`.
  - **The final-wiring entry:** it says "Comes out when that audit closes". It was the D step's B60
    (`S/u35r/r5/CLOSE_STATUS.tsv`: "comes out when that audit closes: at D"). D ran (`590cffcf`) and the entry stayed.
  - **Consequence:** BACKLOG.md:8 sends the next go-ahead session to this list "in one pass". That session would
    re-run passed runs that wear the board (G6 is a flash cycle and 2 h; S4 is 6 h on top of a clean round).
- **Ruling or pillar it meets:**
  - the owner, 2026-11-05 06:27: "a passed wear test is not re-run unless a later change alters the code it
    exercises", and 2026-11-10 21:23, wear steps last and once;
  - BACKLOG's own rule (`BACKLOG.md:3-6`): a resolved item comes out;
  - P8 (least wear) and P9 (traceable).
- **Decision record:** none found that keeps these rows open on purpose. The owner left out only the bridge rebuild
  (2026-11-13 08:57, `BACKLOG.md:122`, correctly still open). The owner closed the bench campaign with "There are no
  more tests to be done" (2026-11-13 09:15).
- **Smallest fix (a doc deletion):**
  - delete the rows the last round settled, and put each result in its home (SPEC already holds S4, the send stall and
    BMP3XX);
  - fill the reset-code column from the runs;
  - delete the final-wiring entry (B60);
  - keep the bridge, F17 if still open, and H1 (the owner's periodic chroot check).

### DECISIONS-2 [class R] [VERIFIED] The owner's late general rulings never reached the standing rules
- **Where:** `SPECIFICATION.md:32-131` (Part 0), `:4885-4903` (D.8) and the working agreements in `CLAUDE.md`. None of
  them carries:
  - the owner, 2026-10-28: "building upon hypothetical findings is a clear no-go", "Hypothetical findings which are
    suspicious to be real need to be verified", and the hardcoded-timed-check pattern rejected as "very bad, very
    awkward";
  - the owner, 2026-10-23: "Always regard the modules as libraries, not every feature must be immediately used";
  - the owner, 2026-11-09 18:30: "Before removing any function which could be a feature which is just unused, ask me";
  - the owner, 2026-11-09 19:11 and 19:17: "minimal and optimal at the same time through smart design" as a general
    principle at every level;
  - the owner, 2026-11-11: root causes, "no runaway fixing chains", and "be careful with such negative tests".
  - A grep for "hypothet", "smart design", "librar", "just unused" or "runaway" finds none of these rulings. The only
    hit for "hypothetical" is `SPECIFICATION.md:8491`, a 09-26 quote about one test.
- **What:**
  - Only the 11-07 lens (D.8, Part 0 at every level) and the 11-03 "target low complexity" landed (`SPECIFICATION.md:48-51`,
    `:76-80`, `:4891-4893`).
  - The pre-audit F.2 sentence ("only worth closing for a concrete, non-hypothetical threat",
    `25caf528:SPECIFICATION.md:3601`) was deleted in the drift. PICTURE M1 marked it "belongs back", and it is still
    absent; `CLAUDE.md:180-187` keeps only the OR26.a criterion.
  - The lead's own plan (`S/u35r/r5/NEXT.md`, the "P9 doc unit") named the 11-09 ask rule and the smart-design goal
    "in Part 0 or D.8"; neither landed.
  - These are the rules that keep the target state from drifting again. The next session sees D.8's lens but not the
    ban on hypothesis-driven mechanisms, nor the ask-before-removing rule that protects the O2 library features.
- **Ruling or pillar it meets:** those rulings themselves; the owner's 2026-11-02 "no knowledge may be lost"; and the
  owner's 2026-11-07 17:31: "They must flow into and be applied to the general specs".
- **Decision record:** none found that places them elsewhere. `.claude/skills/*` does not carry them either; only "a
  red test is a regression until a root cause says otherwise" is close (`work-routines/SKILL.md:59`).
- **Smallest fix:** add three to five lines, with the quotes and dates, to `SPECIFICATION.md` 0.2's "P4 in practice"
  paragraph or to D.8, plus restore the F.2 sentence. No code changes.

### DECISIONS-3 [class F] [VERIFIED] The agreed BACKLOG entry "upstream findings, report later as one bundle" was never written
- **Where:** `BACKLOG.md`, which has no such entry. A pickaxe search of BACKLOG.md's history finds none ever: for
  "bundle", only unrelated text; for "child_last", nothing.
- **What:** on HP2 (the stale asyncio `child_last`), the lead proposed three things and the owner agreed on 2026-10-27
  12:41 ("Yes, let's do it like that"):
  - leave the code as it is: done;
  - add a Part F paragraph: done, at `SPECIFICATION.md:6564-6565`;
  - add "a BACKLOG.md entry of upstream findings to report later as one bundle, if at all": missing.

  F.9 (`SPECIFICATION.md:7544-7575`) lists the upstream workarounds and what retires each. It holds no "report later"
  list and no defect without a workaround, such as `child_last` or the second await of an ended task (`:6559-6565`).
- **Ruling or pillar it meets:** the owner, 2026-10-27 12:30: "we should report it later and bundled, if at all".
- **Decision record:** the owner, 2026-10-27 12:41. I found no later ruling that withdraws it.
- **Smallest fix:** one BACKLOG bullet under "Deferred" naming the upstream findings to bundle, with pointers to
  F.1/F.9. Low priority.

## Checked and clean
- 65 owner-decided features or behaviours located (table below):
  - all present, none reversed;
  - every later ruling holds over its earlier one in code, website and docs (16 superseded items grepped: 0 stale hits
    in `src/`, `buildgen/`, `js/`, `html/`, `mockdata/`, `*.md`).
- 21 confirmed gaps checked: REPORT section 3's 16 (it says 17 but lists 16), its NeoPixel reverse case, and 4 from
  the bench rounds. Each is closed at a located site, and none was reopened by the cleanups.
- PICTURE M2-M7 (the drift's code leftovers):
  - no hardcoded timed checks (only Sensirion's own VOC constant and the pre-audit ISL29125 calibration window);
  - no per-episode log flags;
  - one "I2C bus not initialized" site (`src/asy_i2c_driver.py:376`) instead of 26;
  - no product console line for the test gates: the only `print(` calls are in the logger (`src/asy_print_log.py:92`,
    `:121`, `:163`).
- The UART hazard code exists only when the TOML includes the link:
  - routes in `src/asy_uart_link_driver.py:58-63`;
  - every buildgen emission gated on `uart_link` (`buildgen/codegen.py:223-235`, `:405-406`;
    `buildgen/definitions.py:648-663`);
  - `uart_link` appears only in `devices/dev.toml:161-177`.
- **BACKLOG open items outside DECISIONS-1 are all knowingly open:**
  - the `arduino/` C reconciliation (owner, 09-25);
  - R13 + N3 (deferred by the owner, 11-06);
  - the chroot change list (the owner's periodic check, 09-18);
  - the non-blocking-call goal (owner, 07-24/09-29);
  - the littlefs resize (owner, 09-26);
  - both modlwip watches (owner, 09-30/10-26);
  - the bridge item (left out by the owner, 11-13);
  - the "Owner questions" section is empty, and "Refactor targets" reads "None open".
- **No owner question is parked outside BACKLOG.** "owner's call" appears only in standing rules: the pin move and
  `TCP_NODELAY`.

## Notes
- **The brief lists the boot-confined `gc.collect()` as already decided, but the release no longer has it.** The lead
  removed it on 2026-11-10 "with the churn they swept" (`SPECIFICATION.md:9324-9332`, `CLAUDE.md:313`), under the
  owner's 11-06 rule that a fix whose reason is gone is obsolete. It was measured on the twin and on `dev`, and the
  last round's heap figures cover it. I found no owner word on the removal itself. It fits the later rulings; it is
  for the owner's information only.
- **`buildgen.definitions`' CLI `main()` went on 11-10, after the 11-09 18:30 ask rule.** It was settled by evidence
  under the owner's 11-09 20:43 direction. The capability stays through `_generate_sensortask_modules.py`, so nothing
  is lost (FINDINGS 12.156).
- **Negative tests pin keys that no longer exist** (tests, not my scope; the 11-11 caution):
  - `tests_scripts/test_buildgen_validate.py:2218-2225` (the `ntp_retry_*` keys);
  - `tests_scripts/test_buildgen_generate.py:363` and `tests/_sensortask_scenarios.py:3378` (`TimeStale`).
- **`.claude/skills/bench-routines/SKILL.md:18-38` still describes the audit campaign's workflow:** the lead's relays
  on a bench branch, the merge-relays commit, the hand-back. The skills are the owner's request (11-06), so they
  stay; whether these parts still fit after the audit is for the repo lane.
- **`src/asy_bmp3xx_driver.py:433` is a stale comment:** it says the cycle includes a "poll", which the 11-09 change
  removed. Trivial.
- **The filter hid one line I did not read:** `SPECIFICATION.md:61` (pillar P3's row). It is not evidence of anything.
- **Not traced:**
  - OF-246, OF-127 and OF-186 (10-26): tooling and test items, not features;
  - the 10-23 test-matrix ruling, 11-06 Q4's board-gap tests, Q5's twin fidelity and the read-trigger and granularity
    answers: all test-side, and out of this scope.

## Items checked (item | owner date | location or status)

| item | owner date | file:line or status |
|---|---|---|
| ResetBits, ConfigUnpersisted gone; ResetReason and internal flag kept | 11-02 | no hits; `buildgen/codegen.py:290`; `src/asy_config_manager.py:328` |
| Notification block gone, PauseTime kept | 11-03 | `buildgen/definitions.py:667-670` |
| TimeStale gone, NTPSynced is the flag | 11-06 | `buildgen/codegen.py:280`; `buildgen/definitions.py:602` |
| UnixTime / Device Clock | OR94 "15 a" | `buildgen/codegen.py:296`; `buildgen/definitions.py:634` |
| LastTaskEnd | 09-30 | `buildgen/codegen.py:295`; `SPECIFICATION.md:1083-1089` |
| Reset code 4 removed | 11-02 | `src/asy_system_service.py:86-101` |
| Code 20 in `_log_dead_task()` | 11-06 | `src/asy_system_service.py:290-303` |
| Loop end: record, then `machine.reset()`; no traceback; start line kept | 11-03, 11-04 | `buildgen/codegen.py:833-866` |
| Boot-phase marker / soft-reset record (Q4, Q9) | 10-26 | `SPECIFICATION.md:7045-7047` |
| Level 0 silent; loggers passed through | 11-02 | `src/asy_print_log.py:86-128`, `:161-163` |
| report_unretrieved silent at 0 | 10-07, 10-21 | `src/asy_print_log.py:114-127` |
| err_nomem gone | 11-03 | no hits |
| Newest-entry slot rule | 11-03 | `src/asy_print_log.py:165` |
| No placeholders for retired numbers; rule from release | 10-28 | `SPECIFICATION.md:3675-3677`; catalog 0 "retired" |
| NTP unsynced: fixed 60 s | 11-03 | `src/asy_ntp_client.py:58-59`, `:377-379` |
| NTP stale after 3 intervals, 10 s slack | 09-29, 10-27 | `src/asy_ntp_client.py:288-292` |
| FRAM SPI 8 MHz | 11-02 15:51 | `src/asy_fram_driver.py:110` |
| FRAM RDID up to 3 with W29 | 10-28 | `src/asy_fram_driver.py:75-77`, `:95` |
| FRAM E/W pair unchanged | 11-03 | unchanged (no edit) |
| FRAM status byte: own write, CS deselect | 11-10 | `src/asy_fram_manager.py:104` |
| FRAM CS settle pauses removed | 11-10 | no `sleep_us` in the FRAM path |
| FRAM per-owner CRC seed | 10-28 | `src/asy_fram_manager.py:78-87` |
| Native CRC engine, ≤32 bit, no run_inc/check_inc | 11-09 | `src/crc_checks.py:1`, `:20-21`, `:33-126` |
| Default-value helpers kept | 11-09 | `src/asy_sgp40_driver.py:140-149` |
| Post-write hook kept (pre-audit) | 11-09 (4) | `src/asy_api_response.py:57-69` |
| Demo launcher removed | 11-09 (5) | `digital_twin/launch.py` gone |
| No-caller library functions kept (O2) | 11-09 18:30 | `src/asy_spi_driver.py:179-233`; `src/asy_uart_driver.py:408`, `:678`, `:698`; `src/asy_fram_driver.py:339`; `src/asy_scd30_driver.py:564-591`; twin `--seed` |
| NeoPixel: no timed rewrite or give-up, one lock, no error logger | 10-28, 11-09 | `src/asy_neopixel_driver.py:47`, `:53`, `:95-104`, `:115-127` |
| BMP3XX: one datasheet wait, one burst | 11-09 | `src/asy_bmp3xx_driver.py:443-450` |
| SCD30 stopped: values unavailable | 11-04 | `src/asy_scd30_driver.py:397-400`, `:461` |
| SGP40 pauses without compensation | 11-04 | `src/asy_sgp40_driver.py:288-294` |
| SCD30 commands execute when present | 10-26 | `src/asy_scd30_driver.py:277` |
| SCD30 power-cut persistence stated as fact | 11-10 | `SPECIFICATION.md:11799-11800` |
| Wet-bulb corner removed, range check kept | 11-02 | `src/math_helpers.py:111-117` |
| Stull PDF out of the repo | 11-03 (j) | no PDF tracked; `datasheets` submodule |
| WLAN lines on each state change | 11-06 | `src/asy_wifi_service.py:574-582`, `:778-783` |
| Country help text (channels 12-13) | 11-13 | `src/asy_wifi_service.py:82` |
| `/status` yield in the shared writer, flat rule | 11-06 | `src/asy_webserver_service.py:146`, `:223-245` |
| Content-Length once; head limits | 10-28 | `src/asy_webserver_service.py:162-165`, `:349-370` |
| Connection-task trace, direct `err_s` | 10-22 | `src/asy_webserver_service.py:888` |
| Mempause: a deadline, no one-shot timer | 10-28 | `src/asy_system_service.py:236`, `:482-487`, `:650` |
| Code 9 scheme | 11-06 | `src/asy_system_service.py:97`, `:100` |
| UART link: TOML is the only switch | 10-22, 11-06, O4 I | `src/asy_uart_link_driver.py:58-63`; `buildgen/codegen.py:223-235` |
| UART timeout 1,000 ms unchanged | 11-03 | `src/asy_uart_comm.py:108` |
| UART MemoryError catches (GET/SET/readline) | 10-27 | `src/asy_uart_comm.py:274`, `:313`; `src/asy_uart_driver.py:694`, `:708` |
| UART independent of FRAM timing (synchronous entry) | 11-07 B, O4 B | `src/asy_uart_comm.py:496-499`; `SPECIFICATION.md:3818-3826` |
| dev rx_ring 512 B | 11-05 | `devices/dev.toml:54`, `:66` |
| TCP_SND_BUF 1,600 B by measurement | 11-11 | `toolchain/versions.toml:63-64`; `SPECIFICATION.md:2494-2510` |
| lwIP EAGAIN and listener-close patches | 09-30, 10-26 | `toolchain/micropython_overrides.py:156-207` |
| C-stack reboot ("ok") in its small form | 10-28 | `src/asy_print_log.py:343-364` (12 refs in 6 modules) |
| Single config write, serialised first | 10-22 | `src/asy_config_manager.py:398`, `:421-423`, `:564` |
| Website `65535+` | 11-03 | `js/templates.js:430` |
| Banner back to the pre-audit form | 11-03 | no "no JSON object" banner in `js/` |
| Solid stripes | 11-03 | `html/style.css:378-410` |
| Build-date stamp gone, BuildDate kept | 11-03 | `buildgen/definitions.py:103`; `buildgen/codegen.py:605` |
| Back history, decimals, tones, inert drawer, reload, confirmations, section-switch wait | review notes, OR94/OR132 | `js/shell.js:25-31`, `:138`; `buildgen/definitions.py:33-35`; `js/templates.js:599`; `html/index.html:24`; `js/render.js:238`; `js/poll-manager.js:34` |
| Contrast fix | OR132 "2a" | `html/style.css` tokens (diff vs `25caf528`) |
| Release 2.0 | 11-10 | `buildgen/version.py:9-10` |
| Serving reserve = after-build check | 11-12 | `SPECIFICATION.md:8455-8456` |
| Archive branches | 11-10 (i) | `origin/claude/u35-audit-archive`, `-bench-campaign`, `-int-backup` |
| CI apt cache and mirror check (O1 kept) | 10-27 | `.github/actions/apt-cache-restore/action.yml` |
| Decision-records checks kept permanently | 11-03 (i) | `tests_scripts/test_decision_vocabulary.py`, `tests_scripts/test_citations.py` |
| COBS mode in the crossover tests | 11-02 | `tests_hardware/device_scripts/uart_crossover_exchange.py` |
| Work-practice skills | 11-06, 11-07 | `.claude/skills/*` (see Notes) |
| No first-boot special case | 10-23 | no hits in `src/` |
| Upstream "report later as one bundle" entry | 10-27 | MISSING (DECISIONS-3) |
| Late general rulings in the standing rules | 10-23, 10-28, 11-09, 11-11 | MISSING (DECISIONS-2) |
| Gap: ISL29125 settle deadline | REPORT 3 | `src/asy_isl29125_driver.py:1545-1548` |
| Gap: FRAM blank chunk | REPORT 3 | `src/asy_fram_manager.py:117` |
| Gap: I2C register-byte NACK | REPORT 3 | `src/asy_i2c_driver.py:120-124` |
| Gap: I2C data-byte NACK | REPORT 3 | `src/asy_i2c_driver.py:146-151` |
| Gap: SGP40 restore cycle | REPORT 3 | `src/asy_sgp40_driver.py:280` |
| Gap: NTP zero timestamp | REPORT 3 | `src/asy_ntp_client.py:256` |
| Gap: config write cut part-way | REPORT 3 | `src/asy_config_manager.py:398`, `:564` |
| Gap: log store after a failed read | REPORT 3 | `src/asy_print_log.py:313-316` |
| Gap: FRAM layout shift | REPORT 3, owner 10-28 | `src/asy_fram_manager.py:78-87` |
| Gap: captive DNS flood | REPORT 3 | `src/asy_captive_dns.py:83-85` |
| Gap: config staged before its task | REPORT 3 | `src/asy_config_manager.py:619-628` |
| Gap: emergency exception buffer | REPORT 3 | `buildgen/codegen.py:822` |
| Gap: loop-end reset label | REPORT 3 | `src/asy_system_service.py:97-98`; `buildgen/codegen.py:851-861` |
| Gap: lwIP listener close | REPORT 3 | `toolchain/micropython_overrides.py:156-207` |
| Gap: CRC32 per-bit allocation | REPORT 3 | `src/crc_checks.py:20-21` |
| Gap: light-theme contrast | REPORT 3 | `html/style.css` (`--color-*` tokens) |
| Gap: `/status` build stalls the loop | bench 11-05/06 | `src/asy_webserver_service.py:242-245` |
| Gap: C-stack overflow while SYSTEM's FRAM lock held | owner 11-06 | `src/asy_system_service.py:303`; no lock across an entry (`SPECIFICATION.md:3818-3821`) |
| Gap: UART misses behind FRAM holds | owner 11-07 B | synchronous FRAM entry; native CRC |
| Gap: send pool filled by stalled clients | owner 11-11 | `toolchain/versions.toml:64` |
| Gap: NeoPixel lost shutdown cancel | REPORT 3 | the 300 s rewrite reverted, `src/asy_neopixel_driver.py:95-104` |
| BACKLOG owed-hardware list and reset-code table | 11-05, 11-10, 11-13 | STALE (DECISIONS-1) |
