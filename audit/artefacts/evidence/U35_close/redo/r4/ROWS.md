# R4 phase A: the row table (agent, 2026-11-05)

Read at `c78bbcf1` (S/wt-r4, `audit/r4`), git, grep and reading only; nothing ran, nothing changed but this file.
Paths are repository paths unless they start with `S/`. Line counts are estimates (about ±50 %) for phase B's
complexity read, not commitments. "Waits on round 1" names the bench fact the row's final text needs.

## Head: the totals

- **Rows (section 1): 33.** Met 8, remaining 25, limits for the owner 2 (rows 10 and 20, each also remaining for
  its other part). Of the remaining, 3 wait on round 1 in part or whole (rows 23, 29, 30).
- **U36's 96 actions (section 2):** dropped 0 (one in part: 510's "Stale bundle" row); checklist inputs 82 (8 met
  at head, 1 belongs to R5, 73 open); rule proposals 14 (12 with an owner row behind them, 2 without).
- **Lines expected, in / out (estimates):**

  | doc | lines now | in | out | net |
  |---|---|---|---|---|
  | SPECIFICATION.md | 12,144 | +270 | −580 | −310 |
  | CLAUDE.md | 1,276 | +30 | −470 | −440 |
  | README.md | 988 | +300 | −250 | +50 |
  | BACKLOG.md | 1,286 | +5 | −55 | −50 |
  | tests_hardware/README.md | 2,089 | +20 | −45 | −25 |
  | digital_twin/README.md | 1,257 | +2 | −20 | −18 |
  | DEVICE_REFERENCE.md | 174 | +25 | −5 | +20 |
  | HEAP_FRAGMENTATION_MEASUREMENTS.md, UART_C_PORT_CHANGELOG.md | 401, 245 | +4 | −2 | +2 |
  | code and config comments (13 files), two audit records | — | ±20 changed | | 0 |
  | `tests_scripts/test_tool_help.py` (adds, OR15.a (1)) | — | +30 | | +30 |
  | `.claude/skills/integrate-module/SKILL.md` (adds, new file, OR10.a (1)) | — | +30 | | +30 |
  | **docs and files, total** | | **≈ +716** | **≈ −1,427** | **≈ −711** |

  Optional, not in the totals: the chroot recipe's move (A.U36.524) is CLAUDE.md −150 / SPEC +150, net 0. The two
  allow-lists lose about 190 entries (about 120 vocabulary and 70 citation entries in rewritten doc text).
- **Runs (section 4 and 5): 1 gate (6 parts) + 3 OR10.b builds + the doc-check probes ≈ 4.0 machine hours** (gate
  ≈ 0.8 h, OR10.b ≈ 3.0 h, probes ≈ 0.2 h).
- **"owner": 23** (rows 6, 7, 8, 11, 14, 15, the F.3 crossings of row 23, the 14 rule proposals, U36 002 and 539).
  **"adds": 2** demanded by owner rows (the CLI-reference check, OR15.a (1); the integrate-module skill, OR10.a (1));
  3 more test halves of U36 actions (514, 532, 537) have no owner row and are not recommended.

## 1. The rows

### 1.1 PLAN's R4 rows

| # | row, in its own words (short) | state | where / the work / the limit | lines | marks |
|---|---|---|---|---|---|
| 1 | OR27.a: facts, rules, agreements; one short reason and "(owner, date)" per rule; incident stories, "this used to be", who-found-what go; every markdown file plus comments | remaining | Every doc. Lines with history markers at head (`the hard way`, `used to`, `no longer`, `previously`, `incident`, `PR #`, `WP<n>`, `was removed/replaced`, `Not hypothetical`...): SPEC 101, CLAUDE.md 29, THR 15, BACKLOG 11, README 4, DTR 4, DR 1, HFM 1. Whole archival blocks: SPEC E.6.5 (the 2026-09-04 overlap scan, `:5769-5781`), B.7's evidence narrative, E.7's in-process soak account (`:5847-5852`, the soak itself lives on host-side), B.13's incident (`:2069-2085`). Each rule keeps one reason; a figure stays only as a rule's evidence. Prevention rule (3): each rewrite says "no meaning change" | SPEC −450, CLAUDE −120 (inside its −470), others −90 | — |
| 2 | OR13 (+ OR13.a): docs match the implementation; drifted rules go to the owner with their history, plain facts are fixed | remaining | Read every Part against the final tree during row 1's pass. Found already: Codecov is named as a live upload at `CLAUDE.md:760` and `SPECIFICATION.md:5493`, while `.github/` carries none; I.6 sits inside Part J (`SPECIFICATION.md:9397`); E.2.1/E.2.3 are `##` at the E.2 level and E.2.2 is missing (`:5155`, `:5201`); `(×1, no IIR)` at `:364` (row 29). The removed-name sweep (row 21) found no stale reference. A drifted rule found on the way is not reworded but listed for the owner (OR13.a) | inside row 1 | — |
| 3 | OR14 (+ OR14.a): the docs' history traced for lost or drifted topics | met | The S02 history trace in phase A (`audit/CONSOLIDATION.md:293-296`; permanent home "none (findings only)", `:172`); its lost and drifted items were routed into U36's actions (section 2), which R4 works as checklist inputs | 0 | — |
| 4 | OR15.a (1): README task-first (install, build and flash, tests per tier, everyday variants), then a complete CLI reference, one collapsible section per tool, every option described; a `tests_scripts/` check compares each tool's `--help` with it and fails CI on a mismatch | remaining | README.md: reorder the existing recipes (`:78-846`) into the task order; add `<details>` per tool for the 21 tools `tests_scripts/test_tool_help.py:12-33` already lists. The check does not exist: `test_tool_help.py` only asserts that `--help` answers and touches nothing. Smallest form (agent, 2026-11-05): one test in that file that reads each tool's `--help` once and requires every option it names in that tool's README section, and no option there that `--help` lacks (option names, not a byte copy, so the reference stays prose) | README +300/−250; test +30 | **adds** (OR15.a (1)) |
| 5 | OR15.a (2): every runner ends with the same summary block | met | SPEC E.10 (`SPECIFICATION.md:6082`), `scripts/_summary_block.py`/`.sh`; R2 held it | 0 | — |
| 6 | OR44.a (1)-(3): a "Design principles" Part near SPEC's front (P1-P6 and gaps filled), current state only, pointing to the rules and Parts that carry each; pointers from CLAUDE.md and README; CLAUDE.md's bird's-eye scan checks against it | remaining | No such Part at head (`SPECIFICATION.md:11-26` lists A-N). New Part 0 (about 70 lines): P1-P6 from OR44.a (1), each with its pointers; P4 carries the owner's "Generally target low complexity" (2026-11-03) and "nothing proven good shall be removed, but checked if it can be leaner" (2026-11-02); A.U36.031/541/542 are its inputs (F.9, `:7496`, already holds "a workaround names its defect and its end"). CLAUDE.md `:96` (the bird's-eye scan) and README "Further reading" gain one pointer each | SPEC +70; CLAUDE +2; README +1 | **owner** (changes the scan rule) |
| 7 | OR44.a (3) with OR10.a (1): one ordered checklist that supersedes the overlapping ones (C, D, G, the new-module procedure), no parallel list; proven by walking one real addition through it | remaining | Part K (`:10162-10476`, 315 lines) becomes the one path: its steps cite C/D/G for content instead of restating; D's process steps (D.0 `:4701`, D.13, D.14, D.16) move into K; CLAUDE.md's citations of "Part D's checklist" (`:96-100` and Hard rules) point to K. The proof walk is row 20's runs | SPEC +40/−70 | **owner** (changes which checklist binds) |
| 8 | OR51.a (4): the quality bar and test standard in SPEC (Part D, D.12, Part E); session practice (close-out cleanup, closure, deferral sweep, question format) in CLAUDE.md's working agreements, citing the spec | remaining | Met in part: the bar in D.1-D.12 and E.2.3 ("A test bites", `:5203`), the planting rule in K.10 (`:10412`); the question format in CLAUDE.md's decision-records rule (4) (`:530-533`). Missing: one working-agreement bullet for close-out cleanup (temporary files persisted to their single source, crosslinked, then removed), closure of every opened issue, and the deferral sweep (trigger met, work not done), citing D and E. Old plan's U37 08 (close-out agreements) is the same text | CLAUDE +5 | **owner** (the bullet's wording) |
| 9 | OR68.a (1)-(4): every decision names actor and date; the five prevention rules in CLAUDE.md; the two checks | met | CLAUDE.md `:524-537`; `tests_scripts/test_decision_vocabulary.py`, `test_citations.py` (kept, owner 2026-11-03 (i)). List A's 52 texts were not re-walked here: the vocabulary check holds every sentence off its allow-list | 0 | — |
| 10 | OR68.a (4): "existing text on an allow-list until the audit rewrites it" | remaining, and a limit | Vocabulary allow-list 392 entries: 120 in docs (SPEC 63, THR 15, CLAUDE 13, BACKLOG 8, DTR 7, UCL 6, README 4, HFM 2, DR 2), 272 in code comments (tests 157, tests_scripts 40, tests_hardware 27, src 26, digital_twin 14, tests_js 9). Citation allow-list 89: README 29, SPEC 26, CLAUDE 14, BACKLOG 3, THR 2, code 6. R4 rewrites the docs' entries with rows 1 and 2. **Limit:** the 272 comment sentences in about 150 code files stay allow-listed; the owner's (i) ruling keeps the shrinking list as a permanent rule, and emptying it would be about 270 comment edits outside the docs | −190 entries | — |
| 11 | DECREV 4.1 with OR68.a: the WoZi specialties "shall be removed from the docs" (owner's review note, 2026-10-02, `wozi-move-owner-operation`) | remaining | `CLAUDE.md:191-206` (the WoZi hard rule: keep only the general rule that a device's result counts from its own build on its own hardware, and that dev is the bench with its contained exceptions), `README.md:408-411`, `SPECIFICATION.md:1971` and `:10489`, `devices/wozi.toml:1`, `tests_hardware/README.md:1233`, `tests/test_digital_twin_bus_hazard_concurrency.py:491`, the allow-listed SPEC sentence ("never physically flashed"). U36 010, 011 and 520 fold into this row | CLAUDE −12, others ±8 | **owner** (changes a hard rule; the owner's word exists, the wording is shown) |
| 12 | DECREV 5: OR21.a (2) "existing control arms ... are left as they are", owner wrote "the control arms are overkill" | remaining | `PROJECT_AUDIT_PLAN.md:311`: mark the clause as the lead's integrated text (an audit record, deleted at D, kept by D's tag) | ±1 | — |
| 13 | DECREV 5: OR140.a (4) "and the helpers with the no-clamp rule" | remaining | `PROJECT_AUDIT_PLAN.md:551`: the same mark | ±1 | — |
| 14 | DECREV 5: Part N's scope "(owner, 2026-09-25, paraphrase)" | remaining | `SPECIFICATION.md:11805-11809`: the scope sentence is agent text; keep the owner's own 2026-11-04 words that follow it, re-attribute the rest "(agent, ...)" | ±2 | **owner** (the rule's standing changes) |
| 15 | DECREV 5: "An expected condition prints only", generalised from a paraphrase about startup jitter | remaining | `SPECIFICATION.md:3616-3619`: scope it to the owner's words (no entry for expected startup jitter, any boot, any module) or mark the general form as agent text | ±2 | **owner** (as 14) |
| 16 | DECREV 5: OR143.a "catches go", the lead's integrated text, not the owner's | remaining | `audit/REGISTER.md:494` credits it "(owner, 2026-10-05)"; superseded by the owner's 2026-10-27 option (c) (callers catch with the protocol's own fault flow). Mark as the lead's text, superseded | ±1 | — |
| 17 | DECREV 5: REG "(owner, 2026-10-08)" for "at most three agents" | met | `audit/REGISTER.md:564` now reads "(agent, 2026-10-08): at most three agents", the owner's quote beside it | 0 | — |
| 18 | DECREV 5: SPEC I.4(e) credits "Option 1" to the product console lines | met | `SPECIFICATION.md:9195-9205`: "Level 0 prints nothing, ever (owner, 2026-11-02)" for the product; "Option 1 is good" now covers the unit tests' log level only, the WARN change marked "(agent, 2026-11-03)" | 0 | — |
| 19 | OR10 with OR10.a (1)(2): Part K is the single source of the procedure, extended with the owner-discussion stage (features, API, website) and its output record; modules the general case, sensors a specific one; a thin repo skill as the entry point, pointing into Part K | remaining | Part K has neither the discussion stage nor the module/sensor split (its title and K.1 speak of sensors only). Add K.0 (the discussion stage and its record, about 15 lines) and mark each step "every module" or "a sensor driver" (about 15 lines). No `.claude/` in the repo (`git ls-files .claude` empty): one `SKILL.md` that names the inputs and points into Part K | SPEC +30; skill +30 | **adds** (OR10.a (1), new file) |
| 20 | OR10.b: a fresh agent builds the module from the datasheet and the brief alone, every tier and the build, against ISL29125 and BMP3xx; divergences caused by the procedure close into Part K or the skill; repeat until one full run against both shows no gaps; nothing merged | remaining, and a limit | Section 4: three runs. **Limit:** within PLAN's three runs the last, confirming run covers one baseline, not both, so "one full run against both baselines shows no gaps" stays unproven for the other; three fresh builds also likely exceed R4's 6 % share (two agents planned), so the lead holds them to the unit stop | — | — |
| 21 | Parts that describe only removed mechanisms go as whole blocks | met | No Part or `##` section describes only removed code: every removed name of the nine knowledge lists (B1-B8, R0) grepped over the eight docs; the 9 hits (`report_if_fatal`, `LOG_RAM_ONLY`, `set_utc_valid`, `erase_ready`, `_body_as_dict`, `copy_into`, `--build-date` in BACKLOG's build list, `twin_record`, `--skip-lower-levels`) all name code that is still there. The units removed their paragraphs with their code. Archival blocks are row 1's | 0 | — |
| 22 | The knowledge lines, placed as decision 7 says (one line at the module's Part where a reader might rebuild it; platform facts in Part F; unverified ones as owed-hardware rows; trivial ones only in the evidence) | remaining | Section 1.5: 112 lines; 36 already placed by their units, 9 to place in a module's Part, 2 Part F facts, 65 evidence only | SPEC +11 | — |
| 23 | The bench's facts (READING_20261029, RESEARCH_20261102), placed by decision 7 and checked against the final tree: Part F for platform facts, F.3 for the stall rows, F.2 naming the watchdog as the LAN storm's only recovery | remaining; part waits on round 1 | Section 1.6: 23 facts; 7 placed, 11 to place now, 5 wait on round 1 (sheet items 4, 5 and 12a of `S/u35r/r3/d2/round1_sheet.md`; items 13 and 16b are rows 29 and 30). Three F.3 rows would cross a consumer (VOC 31.9 ms over `con.routine_stall` 21 ms; the Wi-Fi switch's 0.97 s over `con.uart_reply` 925 ms on dev; `gc.collect()` 25.5 ms over the 21 ms `uart.gc_pause_worst_ms` the UART floors budget): each is a fix or an accepted degradation, and not R4's to choose | SPEC +25 | **owner** (if round 1 confirms a crossing) |
| 24 | U36's 96 actions: checklist inputs, dropped where their subject is gone; rule actions are proposals, adopted only with an owner row | remaining | Section 2 | inside rows 1-23 | 14 **owner** |
| 25 | `src/LICENSE-captive_dns`'s path and holder line | met | Both hunks against `25caf528` are current facts: the paths name `src/asy_captive_dns.py` and `legacy/firmware/python/CommonDrivers/captive_dns.py` (both exist, U10's names and the legacy move); the holder line equals the SPDX header `src/asy_captive_dns.py:1` and `THIRD_PARTY_LICENSES.md:150-164`. Kept as is (agent, 2026-11-05) | 0 | — |
| 26 | (g) A.11's owner-signed table restored; row 2 keeps naming `UartHazards`, marked as agent text | remaining | Word diff of A.11 between the sign-off (`5ba138ca`, 2026-10-20) and head: identical except row 2's `UartHazards` clause (added in `656fc82f`, 2026-10-22), which already carries "(agent, 2026-10-21)" and "(agent, 2026-10-22)". Left: the closing sentence (`SPECIFICATION.md:1351-1353`, "signed off as it stands") says row 2's clause came after the sign-off. `test_a11_names_every_dispatch_field` keeps the clause required | ±1 | — |

### 1.2 CARRY_R4's three items

| # | row | state | where / the work | lines |
|---|---|---|---|---|
| 27 | E.6.6 `ntp-unreachable-under-load`: "the outage under load is a gap until written" is stale for the first recombination | remaining | `SPECIFICATION.md:5831`: name the bench test that resets under the NTP block with load (since `0c0ad52c`); keep the write variant's `persistence_write` clause. `test_level_containment.py` reads the row | ±1 |
| 28 | `src/asy_uart_driver.py:76-78`: Table 427 ties BE/PE/FE to the character at the top of the FIFO, all four bits write-to-clear; "the byte the DMA read last" is the bench's reading | remaining | Reword the 3-line comment: the table's words, then the bench's reading marked as such (dev bench, 2026-10-29); comment cap holds at 3 lines; no bytecode change | ±3 |
| 29 | P8's two facts with no datasheet: the SGP40 restore is the algorithm's; the CYW43439 documents no country readback | remaining; the second half waits on round 1 | M.3 (`:11743`): one line, "the restore is Sensirion's algorithm state, not a chip fact"; F.1 or C.7.4 (`:3897`): the datasheet documents no country interface, `network.country()` only stores the code (RESEARCH 8). Which domain the chip applies waits on round 1 item 13 (the channel scan under "DE" and "XX") | +3 |

### 1.3 Other R2 and R3 records that name R4

| # | row | state | where / the work | lines |
|---|---|---|---|---|
| 30 | D2 (R3): "x1, no IIR" after a BMP3XX POR; BMP388 Table 24 resets pressure to x4 | remaining; waits on round 1 | `SPECIFICATION.md:364`. Round 1 item 16b reads the bench part's OSR after 0xB6 and after a power-on (the part read 0x00 where the datasheet and the twin say 0x02); the text follows the reading. `tests/test_digital_twin_hot_replug.py` names no value (only "the chip defaults", `:237`), so it needs nothing | ±1 |
| 31 | D2 (R3): `src/asy_scd30_driver.py:171` cites `Datasheets/` with a capital D | met | Fixed in `6378bb60`; the line reads `datasheets/scd30/...` | 0 |
| 32 | R2 LIST 6: `machine.UART.deinit()` waits out the TX FIFO (`machine_uart.c:484`, v1.29.0), one Part F line | remaining | F.5.7 (`:7111`) or F.1: one line | +1 |

FINDINGS.md: none of its five lines names R4 (two are R2 carries for the owner, three are R3 falsification
observations); no row.

### 1.4 Owner words found missing from the docs while reading

| # | row | state | where / the work | lines |
|---|---|---|---|---|
| 33 | "Either it's a warning or a fault applies to the same level / the same module ... If that propagates up, is handled and degraded to a warning, that's a valuable traceback" (owner, 2026-11-03) | remaining | C.7's never-both sentence (`SPECIFICATION.md:3612-3616`) states OR56 without this reading; add it, quoted. The owner's bench decisions are row 23's (power save "is not an option": `:6564-6566` states the setting without the owner's word; LAN storm accepted; GPIO storms "are not really an issue") | +2 |

### 1.5 The knowledge lines (row 22), per source

Classed by reading each line against its unit's doc note and a grep of the docs (agent, 2026-11-05); phase B checks
each placement against the final tree.

| source | lines | placed by the unit | to place: module Part | to place: Part F | evidence only |
|---|---|---|---|---|---|
| R0 (`S/u35r/knowledge/KNOWLEDGE.md`) | 1 | 0 | 0 | 0 | 1 (the 35 exception reasons stay in `twin_record_exceptions.md`) |
| B1 | 10 | 5 (level 0 silent `:9195`; the logger's fatal record `:3677`; no pre-setup entry `:896`; retired codes) | 1: C.7.1, a FRAM write failing after boot is counted by the FRAM layer's own entries, not by an E28 run | 0 | 4 |
| B2 | 9 | 1 (code 4: F.5.4 `:7043`) | 1: C.5, a missing settings file beside surviving FRAM history logs nothing (W69 went) | 1: the timer pool, 16 `Timer()` per program, dev about 12, so alarm-pool exhaustion is refuted (shared with B4's and B5's re-arm lines) | 6 |
| B3 | 11 | 5 (A.4 lost chip and erase gate; C.3 dropped bus; C.8 setups' lock; C.13) | 0 | 0 | 6 |
| B4 | 14 | 8 (C.3, C.13, D.4, A.4, G.2, Part I, M.1, the BMP3XX wait table) | 0 | (the timer pool, above) | 6 |
| B5 | 19 | 4 (`_body_as_dict()` `:542`; the 60 s NTP retry `:3778`; WS-20 in I.3; DTR Run 9) | 1: A.5, a cut or HEAD response's file closes at the next collection, not at the connection's end | (the timer pool) | 14 |
| B6 | 10 | 1 (G.2) | 2: J.5, no write deadline (without flow control the TX ring drains at the baud rate); J.4, the receiver's header refusal is the one size refusal | 0 | 7 |
| B7 | 11 | 3 (A.8 the notification's pause-only block `:396`; A.4 the stopped SCD30's None values `:11718`; the age bound closed at its source) | 2: A.4, an internal LED request queues at its deadline (a ramp over 120 s clears a request queued behind it); a shutdown mid-ramp leaves the last frame until the next boot | 1: the WS2812 kept its state through 794,560 Wi-Fi burst packets (the overlay rewrite's refuted premise) | 5 |
| B8 | 22 | 4 (A.7 boot entry at level 0; L.7 and B.11 build date; H's banner and stripes) | 2: L.6.6, a rule no device TOML can trip is not written; H.5.1, the browser does not re-validate hints, the build's `web.*` rules and the stager do | 0 | 16 |
| R2 | 5 | 5 (its own hand-back, "Where the removed items' knowledge lives") | 0 | 0 | 0 |
| **total** | **112** | **36** | **9** | **2** | **65** |

### 1.6 The bench's facts (row 23)

| fact (source) | home | state |
|---|---|---|
| a failed I2C transfer returns at the timeout (50.9 / 200.9 ms); the controller then fails exactly one more; re-construction fixes it, `clear()` and `scan()` do not (READING, I2C faults) | F.3 `stall.i2c_transfer` measured cell (`:6740`); F.2 ladder | place now |
| flash write: 70-207 ms of blocked loop, 35-39 ms interrupts off per sector erase (W25Q16JV tSE typ 45, max 400 ms, P8) | F.3 `stall.flash_program` (`:6739`) | place now |
| LAN receive load: an unbounded stall, 5.9-7.97 s, one watchdog reset; the CYW43's PendSV packet loop starves thread mode (RESEARCH 5); accepted, watchdog the backstop (owner, 2026-10-29; "Live with the udp storm", 2026-11-02) | F.3 new row `stall.lan_receive`, marked crossed for `con.watchdog`; F.2 one line: the watchdog is its only recovery | place now |
| a flag-woken task behind a 20 ms hog waits about 1.6 slices | F.3 `lag.loop` measured cell (`:6759`) | place now |
| 16 `Timer()` per program, dev builds about 12; an orphaned soft Timer stops at the next collection (silicon) | F.1 | place now |
| UDP sockets: 4 with the station, 2 with the hotspot up (captive DNS plus one client); TCP 9 sockets, 8 listeners, a vanished client's pcb reclaimed in about 15 s | F.1 | place now |
| Pin IRQs lose nothing at 200 Hz through a busy loop or a collection; storms are "not really an issue" (owner) | F.1 | place now |
| SPI requests round down (20 MHz runs at 12, 40 at 24; 48/2 ceiling, P8) | F.1 or C.3 | place now |
| C-stack: about 200 B per await level; at depth 28 three plain calls of headroom; 32 fails | F.1 (beside the static chain's budget 28) | place now |
| heap 187,904 B on the bench image | F.1 | place now |
| `reset_cause()`, WATCHDOG REASON and HAD_POR per reset kind; BOOTSEL loses both regions | F.5.4 (`:6988-7043`) | placed |
| the MemoryError text "memory allocation failed, allocating N bytes" | I.4 (`:9161`) | placed |
| `ThreadSafeFlag` sets coalesce | C.9 / F.1 (`:4023`, `:7536`) | placed |
| `I2C`/`SPI` `deinit()` are no-ops on silicon too | F.5.1 (`:6807`) | placed (add "confirmed on silicon": ±0) |
| `scan()` is soft-I2C on rp2, an accidental bus clear | F.1 (`:6295`) | placed |
| the general call: only the SGP40 names it (RESEARCH 9) | C.8 (`:4046`) | placed |
| VOC `vocalgorithm_process()`: 352 B per sample | Part I (`:7430`) | placed |
| VOC step 16.2 ms average, 31.9 ms worst | F.3 `stall.voc_process` (`:6744`, "owed") | waits on round 1 (item 4, the no-yield stretches on the final image); crosses `con.routine_stall` |
| CRC 462-497 µs per byte on rp2 | F.3 `stall.crc_byte` (`:6745`, "owed") | waits on round 1 (item 4) |
| `gc.collect()` 9.6-25.5 ms, about 7 µs per live object | F.3 `stall.gc` (`:6743`, 21 ms) and I.1 | waits on round 1 (item 4); 25.5 ms exceeds the UART floor's 21 ms term |
| Wi-Fi `active()` up to 0.58 s, about 0.97 s after `deinit()` | F.3 `stall.wlan_switch` (`:6749`, "owed") | waits on round 1 (item 5, the role-reversal switch); crosses dev's `con.uart_reply` |
| the first unfed watchdog stretch, each setup unit's stretch | F.3 `feed.*` measured cells | waits on round 1 (item 12a) |
| the SCD30's 2,143 ms median rhythm at 2 s, 150 ms clock stretch once a day (RESEARCH 6); the SGP40's ETIMEDOUT for about 0.5 s after an unknown command, back in 528 ms; one WS2812 `write()` 129 µs | M.2, M.3, A.4 | place now (3 lines) |

## 2. U36's 96 actions

Classed against the head (agent, 2026-11-05): "checklist" is a checklist input for the doc named; "rule" is a rule
proposal for the owner, with the owner row behind it or "no owner row". No action's subject is gone.

- 001 checklist: `tests_hardware/README.md` (new "How a round runs"); `BACKLOG.md:202`'s sitting procedure leaves
- 002 checklist: CLAUDE.md FRAM rule (save, then clear; the logger list a pointer to A.7) — **owner** (narrows a hard rule)
- 003 checklist: SPEC A.7 (the implicit FRAM-wiring rule)
- 004 checklist: SPEC, THR, test comments cite A.7 (partly done)
- 005 checklist: THR device-script chunk rule
- 006 checklist: SPEC F.1, which stores wear (W25Q16JV 100K cycles, P8)
- 007 checklist: SPEC E.6.1 (`env --tier` and soak durations are not levels)
- 008 checklist: README hardware section (L3/L4, soak as durations)
- 009 checklist: SPEC E.6.3 (no GC-instrumented hardware image)
- 010 checklist: README flashing note, folded into row 11
- 011 checklist: SPEC B.11 `:1971`, folded into row 11
- 012 checklist: SPEC E.8 (when a heap figure counts), HFM keeps the method
- 013 checklist: HFM §M8 (`:395`)
- 014 checklist: CLAUDE.md hazard rule points to C.8's file list
- 015 checklist: SPEC C.8 per-device shared-bus set
- 016 checklist: SPEC E.2.1 (partly done)
- 017 rule: a test changes only mechanically; CLAUDE.md and a new E.2.2 — owner row OR12, OR12.a
- 018 rule: failures met on the way are recorded, never passed — owner row 2026-09-16 (`9894e85`), OR4, OR6
- 019 rule: datasheet rule cites the page, next-best source when missing — owner row OR4, OR4.a (the location half met at `CLAUDE.md:10-14`, A.6 `:607-613`)
- 020 checklist: met at head (`tests/test_digital_twin_isl29125_autorange.py:66`)
- 021 checklist: CLAUDE.md parity agreement points to M.1
- 022 checklist: SPEC Part M (new M.5 WS2812), A.6 keeps the file
- 023 rule: Part F opens with the pin-move re-check, CLAUDE.md points to it — owner row OR69.a (9) (the practice text is agent, 2026-08-06)
- 024 checklist: met at head (`digital_twin/README.md:6`)
- 025 checklist: CLAUDE.md UART rule and UCL (the C side outside this project's scope, owner 2026-09-24)
- 026 checklist: SPEC, I.6 (`:9397`) back into Part I
- 027 checklist: SPEC J.1 (BSEC scope as a known limitation), BACKLOG item leaves
- 028 checklist: SPEC E.6.6, `BACKLOG.md:40` (partly done)
- 029 checklist: DEVICE_REFERENCE.md local time (EU rule, `src/asy_ntp_client.py:484-488`)
- 030 checklist: met at head (`THIRD_PARTY_LICENSES.md:25`)
- 031 checklist: SPEC Part 0 (row 6; F.9 already states it)
- 032 rule: D.2's typed-call-site qualifier — owner row 2026-08-06 (`b5502c8`)
- 033 checklist: SPEC F.2 (both write paths, the deferred flush, the power-loss window)
- 034 rule: CLAUDE.md flash-write rule — owner row OR70.a (3)
- 035 checklist: `BACKLOG.md:125` question 4 into F.2
- 036 checklist: SPEC F.1, the `.frozen` sentinel stated once
- 037 checklist: met at head (no retired helper named)
- 038 checklist: R5, not R4 (code: the D.15 order beyond `src/`, PLAN R5)
- 039 checklist: SPEC C.11 and K.5 (partly done)
- 040 checklist: DTR copies of F.7's row (F.7 met)
- 041 checklist: SPEC L.4 (`:10966`)
- 042 checklist: `BACKLOG.md:1155` bullet leaves (E.7 holds it)
- 043 checklist: met at head
- 044 checklist: SPEC H (new H.6.1 wire-contract table)
- 045 checklist: SPEC E.6.6 (partly: C.8 `:4057` names the L3 check)
- 046 checklist: SPEC F.2 ladder names each rung's test (B2/B4 removed rungs: re-derive)
- 500 checklist: SPEC H.1, H.4
- 501 checklist: SPEC H.1 browser floor; its eslint half is a setting under owner row PQ10 (`ecmaVersion "latest"` today)
- 502 checklist: met at head (`SPECIFICATION.md` L.7)
- 503 checklist: SPEC H.4 poll rows
- 504 checklist: SPEC H.4/H.6 never-"Unchanged" fields
- 505 checklist: SPEC H.4 sparse-PUT rules
- 506 checklist: SPEC H.4, M.1.1 item 16 (the stopped SCD30's None values, owner 2026-11-04, are the newer word)
- 507 checklist: `js/templates.js`, `html/style.css` comments, SPEC H.4 (npm checks)
- 508 checklist: SPEC H.6
- 509 checklist: SPEC H.3 (`tests_scripts/test_website_layering.py` is the guard)
- 510 checklist: SPEC H.1/H.4; its "Stale bundle" row is dropped (the page build-date stamp went, owner 2026-11-03)
- 511 checklist: SPEC, DR, README device set as today's fact
- 512 checklist: SPEC front-matter term table; its code and CLI-help renames are product code, not R4's
- 513 checklist: test comments cite the generator (partly done)
- 514 checklist: SPEC L.6.4; its test half has no owner row (not recommended)
- 515 checklist: SPEC H.5/H.5.1 (after B8's validator cut)
- 516 checklist: `README.md:322`, `BACKLOG.md:671` (partly done)
- 517 checklist: SPEC H.2, H.7, H.8
- 518 checklist: SPEC L.4 twin wiring
- 519 checklist: SPEC L.7 versioning as agent design
- 520 checklist: `devices/wozi.toml:1`, folded into row 11
- 521 checklist: SPEC B.14.3 (`:2498`) leaves, one BACKLOG item
- 522 checklist: met at head (`README.md:136-146`)
- 523 checklist: SPEC B.13 (row 1)
- 524 checklist: CLAUDE.md recipe to SPEC B.17, optional, net 0
- 525 rule: a gate's verdict is its exit status or its own summary — owner row OR15.a (2) (the "never `| tail`" half is agent text)
- 526 checklist: SPEC E.5 `:5493`, `CLAUDE.md:760`, README (Codecov gone from CI)
- 527 checklist: CLAUDE.md mypy bullet, `BACKLOG.md:22-25`
- 528 rule: merge rules — no owner row (CLAUDE.md's two merge bullets stand)
- 529 rule: parity agreement (no lost function, legacy's intent) — owner row OR48.a, OR57, OR61.a (2)
- 530 rule: A.4 names the static `AmbPres` limitation — owner row 2026-07-13 (`b64857d`)
- 531 checklist: DEVICE_REFERENCE.md commissioning-and-operating section
- 532 checklist: SPEC structure (numbering); its heading-check test has no owner row (not recommended)
- 533 rule: CLAUDE.md comment rule in one form — owner row 2026-09-14/18, PQ6
- 534 checklist: SPEC C.10 typing idiom once
- 535 checklist: SPEC A.2, C.1 name the generated modules
- 536 rule: reviewed-decision tag and commit-message form — no owner row (agent, 2026-09-27)
- 537 checklist: SPEC M.3 VOCState table, M.1.5 tones; test half not recommended; DECREV 4.2 ("settled" vs "learned") is the owner-text check here
- 538 rule: C.5 states each config value's scope — owner row 2026-07-13 (`144873f`, recorded, not quoted)
- 539 checklist: CLAUDE.md hazard rule gains a UART clause, SPEC J.7 tier map — **owner** (widens a hard rule)
- 540 rule: change classes and the exception precedent's limit — owner row OR12.a (precedent `1e4cdfe`)
- 541 checklist: SPEC Part 0 (row 6)
- 542 checklist: SPEC 0.4 convention catalog (row 6)
- 543 checklist: SPEC Part K (row 7)
- 544 checklist: every doc, citations (row 10)
- 545 checklist: met at head (datasheet location)
- 546 checklist: one role per document; the main lever for CLAUDE.md's −470
- 547 checklist: README (row 4)
- 548 checklist: every doc (row 1)
- 549 checklist: the vocabulary allow-list (row 10)

Counts: dropped 0 (one row of 510 in part); checklist 82 (met at head 8: 020, 024, 030, 037, 043, 502, 522, 545;
R5's 1: 038; open 73); rule 14 (owner row behind it 12: 017, 018, 019, 023, 032, 034, 525, 529, 530, 533, 538, 540;
none 2: 528, 536).

## 3. The docs' own checks

Every check that reads the docs, or the comments R4 edits. Times from the records (`S/u35/lead/runs.txt`, the log
tails) or CI run 41863187064 (`S/u35r/r2/ci_jobs.tsv`); all run inside `scripts/test.sh`'s `tests_scripts` tier
(690 s for 7,111 tests, R0's gate) and CI's `unit-tests` job (12:29).

| check | command | time | R4's edits can trip it |
|---|---|---|---|
| comment cap | `python -m pytest -q -p no:cacheprovider tests_scripts/test_comment_block_cap.py` | 4 s, 655 tests (`r3f_comment_cap`) | yes: rows 11, 28 and U36 507/513 edit comments; the new test (row 4) |
| citations | `tests_scripts/test_citations.py`, then `--regenerate` | with the next three: 23 s, 57 tests (`b4x_pytests`) | yes: every heading moved or added (Part 0, K.0, I.6, E.2.x, F.5.7-F.5.9), every cited path; a fixed allow-listed citation fails as stale until regenerated |
| decision vocabulary | `tests_scripts/test_decision_vocabulary.py`, then `--regenerate` | in the 23 s | yes: any new decision word without its actor; rewritten allow-listed sentences go stale |
| tunables register | `tests_scripts/test_tunables_register.py` | in the 23 s (also `r3m_fx_checks`, 25 s with three others) | if row 14 touches the register block or row 23 a `Part N` cell |
| memory catalog | `tests_scripts/test_memory_catalog.py` | in the 23 s | if Part I moves (U36 026 moves I.6 into it) |
| timing budget | `tests_scripts/test_timing_budget.py` | not timed alone (inside the tier) | yes: row 23's F.3 cells; a value over a consumer must carry its crossed mark |
| threat model | `tests_scripts/test_threat_model_statement.py` | inside the tier | yes, if row 26 drops the `UartHazards` clause (it must stay) |
| level containment | `tests_scripts/test_level_containment.py` | inside the tier | row 27 edits an E.6.6 row's text (trips only on the row's id or columns) |
| SPEC tables | `test_lock_order.py`, `test_task_inventory.py`, `test_import_placement.py`, `test_toml_schema_contract.py` | inside the tier | only if R4 edits C.8's lock table, the task table, the import rows or L.3 |
| THR facts | `tests_scripts/test_device_script_bench_facts.py` | in `b4x_pytests2` (787 tests, 18 s) | yes, for THR edits (rows 1, 11, U36 001/005) |
| UART changelog | `tests_scripts/test_uart_changelog.py` | inside the tier | U36 025 edits UCL's header text |
| tool help | `tests_scripts/test_tool_help.py` | inside the tier | only if row 4's check makes a tool's `--help` change |
| CLI reference vs `--help` | does not exist (row 4 adds it) | — | — |
| licence and vendor files | `test_third_party_attribution.py`, `test_vendored_microdot.py`, `test_vendored_freezefs.py` | inside the tier | no (R4 leaves THIRD_PARTY_LICENSES.md alone) |
| website | `npm run lint`, `npm run typecheck`, `npm run test:unit` | 207 s together (R2's gate) | only U36 507's comments in `js/templates.js` and `html/style.css` |
| lint and types | `S/u35/lead/lint_direct.sh`; the three mypy passes | about 2-5 min | the new test function (row 4); comment edits in `src/` |

No link checker exists beyond `test_citations.py`; no check reads SPEC's heading numbering (532's would add one).

## 4. OR10 and OR10.b's proof

Prepared once (a throwaway script in `S/`, never committed, rule 4.1 (4)): a worktree at the final tree with the
baseline module and every trace of it removed (driver, its tests at every tier, twin chip model, `buildspec`/
`definitions` rows, TOML entries, generated hints, Part M section); the agent gets that worktree, the datasheet from
`/home/user/datasheets/` and a one-page brief of the owner-discussion stage's output (features, API, website), and
follows Part K and the skill only. Each run goes through every tier the procedure names: lint and the three mypy
passes, its unit files at both GC stages, the `tests_scripts` buildgen tests, one wiring device's twin suite at both
stages, the bus-hazard four tiers' software part, and `scripts/build_firmware.py` for that device.

| run | baseline | machine time (est.) | what it shows |
|---|---|---|---|
| 1 | ISL29125 (I2C, `SensorReaderConfig`, an interrupt pin with its pull-up, auto-range, user calibration, an owner list M.1.1) | ≈ 1.0 h (lint and types 5 min, unit files 5 min, buildgen tests 5 min, twin suite at two stages 20 min, firmware 5 min, fix loops 20 min) | where Part K's ordered path leaves a fully featured sensor short: the discussion record's carry into `@web` tags, the twin model, the hazard rows, the wiring; the result is compared field by field with `src/asy_isl29125_driver.py`, `digital_twin/`'s chip model, its tests and M.1 |
| 2 | BMP3xx (I2C, Bosch-derived compensation under F.4's policy, forced mode, no IRQ) | ≈ 1.0 h | the plain-sensor and vendor-code path: formula tests against the datasheet, the derived fields, the readiness gate; its gaps join run 1's in one Part K and skill fix |
| 3 | the baseline with more procedure-caused gaps (ISL29125 expected) | ≈ 1.0 h | that the fixed procedure leads straight to fitting code; any gap left is a stated limit (row 20) |

Runs 1 and 2 may be drafted in parallel, but their test parts run one at a time (two gates at once break this
host's wall-clock bounds, common rules). Nothing from the worktrees is merged.

## 5. The remaining work, in order

Three lanes on disjoint files. Neither lane writes the two allow-lists (`tests_scripts/_citation_allowlist.txt`,
`_decision_vocab_allowlist.txt`): each lane runs the two checks with `--regenerate` locally and discards the
result, and the lead regenerates both once on the merged tree. Lanes B and C cite SPEC headings that lane A creates or
moves, so the lead fixes a heading map (Part 0, K.0, I.6's new place, E.2.1-E.2.3, and F.5.7-F.5.9 if U36 532's
renumbering is taken) in the briefs first.

0. **The lead, first:** one owner round with the "owner" items, each with its wording: rows 6, 7, 8, 11, 14, 15; the
   14 rule proposals (12 adoptable on their rows, 528 and 536 not); U36 002 and 539. Nothing else waits on it.
1. **Lane A — `SPECIFICATION.md`, `.claude/skills/integrate-module/SKILL.md` (new).** Part 0 (row 6, **owner**);
   Part K as the one checklist with K.0 and the module/sensor split (rows 7 and 19, **owner**; the skill **adds**,
   OR10.a (1)); the history pass over SPEC (row 1); OR13's facts (row 2: Codecov `:5493`, I.6 into Part I, E.2.x
   levels); rows 14, 15 (**owner**), 22 (SPEC part), 23 (the "place now" facts), 26, 27, 29 (first half), 32, 33;
   the SPEC sites of row 11 (**owner**) and of the U36 checklist (section 2). About +300/−580 (the skill's 30
   included).
2. **Lane B — `CLAUDE.md`, `README.md`, `BACKLOG.md`, `tests_scripts/test_tool_help.py`, `UART_C_PORT_CHANGELOG.md`.**
   CLAUDE.md's one role per document and history pass (U36 546, row 1); row 8's bullet (**owner**); the adopted rule
   proposals (**owner**); row 11's CLAUDE.md and README sites (**owner**); Codecov `CLAUDE.md:760`; README's task-first
   order and CLI reference with its check (row 4, **adds**, OR15.a (1)); the BACKLOG and UCL actions of section 2.
   About +365/−775.
3. **Lane C — the other docs and the comments:** `tests_hardware/README.md`, `digital_twin/README.md`,
   `DEVICE_REFERENCE.md`, `HEAP_FRAGMENTATION_MEASUREMENTS.md`, `devices/wozi.toml`, `src/asy_uart_driver.py`,
   `tests/test_digital_twin_bus_hazard_concurrency.py`, the test comments of U36 004 and 513, `js/templates.js`,
   `html/style.css`, `PROJECT_AUDIT_PLAN.md`, `audit/REGISTER.md`. Rows 12, 13, 16, 28; row 11's comment and TOML
   sites (**owner**); THR's "How a round runs" (U36 001); DR's local time and commissioning (029, 531). About
   +50/−75; runs after A or B ends (at most two writing units at once, PLAN 4.3).
4. **OR10.b's runs (section 4)**, after lane A: runs 1 and 2, then their fixes in lane A's two files, then run 3.
5. **After round 1:** rows 23 (the five round-1 facts and the three crossings, **owner** if confirmed), 29 (the
   from-the-air half), 30, in lane A's file.
6. **The lead:** both allow-lists regenerated; the gate once (section 3's checks are inside it; npm for lane C's two
   website files); the falsification check; the merge.

Marks: **owner** 23 (rows 6, 7, 8, 11, 14, 15, the F.3 crossings of row 23, the 14 rule proposals, U36 002 and 539);
**adds** 2 (the CLI-reference check, row 4, OR15.a (1); the skill file, row 19, OR10.a (1)). Not recommended, no
owner row: the test halves of U36 514, 532 and 537.
