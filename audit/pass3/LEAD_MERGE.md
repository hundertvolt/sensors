# Pass 3 merge — lead resolutions of the owner's answers (2026-09-29)

Input: `MERGE_INPUT.md` (P001-P137, the ten scans' register lines) and the owner's answers OR101-OR108.
This file says which scan lines are overridden and adds the lines the answers create (L01-L24).
Everything else in `MERGE_INPUT.md` is applied as written.

## 1 Overrides of scan lines

| Scan line | Treatment | Reason |
|---|---|---|
| P042 (D2, G9/R03 "after owner question 1") | replaced by L12 | answered, OR104.a (2) |
| P043 (D3, G6/R30) | applied, with "pass-3 D3 question 1" replaced by "restored by the owner (owner, 2026-09-29, OR102.a (3))" | answered |
| P044 (D3, G6/R29 "mask-as-Unchanged is a divergence") | not applied; replaced by L08 | overtaken, OR104.a (1) drops the mask rule |
| P064 (D4, G5/R08) | applied without "(the reset-timer half waits for question 2)" | the reset-timer half is settled by P049 (owner, 2026-07-18, `af24a01`) |
| P073 (D4, "after the answers") | not applied; replaced by L01-L11 | answered |
| P083 (H1, new req) | becomes LEAD/R29 (lead) | new requirement |
| P084 (H1, new req) | merged with P100 into L14 (G9/R19) | same owner source date (2026-07-13), one principles-Part carrier |
| P100 (H2, new req) | merged into L14 (G9/R19) | as P084 |
| P101 (H2, new req) | becomes L15 (G3/R03) | the scan names G3/R03 as its neighbour; one CRC carrier |
| P102-P105 (H2, new reqs) | become LEAD/R25-R28 (lead) | no existing carrier |
| P106 (N, G2/R17) | applied, with "RETIRE-CANDIDATE" → "retires once the migration below is done (owner, 2026-09-29, OR102.a (10))" | answered |

## 2 Lines created by the answers

Each line is applied to the named block like a scan line. Owner rows are cited as "(owner, 2026-09-29, ORnnn.a (k))".

- **L01 G5/R02** Rank, add: "the two supervisor-reboot fixes (D4.04 flush skipped; D4.11 `main()` returns 4 s early) approved (owner, 2026-09-29, OR101.a), each with a regression test and a changelog line".
- **L02 G5/R04** Rank: "agent — …" → "owner — fix approved (owner, 2026-09-29, OR101.a) of the agent-documented contract (comment `system_service.py:92`, tests); …" (keep the rest); State, add: "regression test: an uptime-task restart mid-boot keeps uptime and signature (D4.20)".
- **L03 G3/R09, G3/R38, G3/R40, G3/R23, G3/R06, G3/R51** Rank, add to each: "fix approved (owner, 2026-09-29, OR101.a), with a regression test and a changelog line" — for D4.37 (R09), D4.53 (R38), D4.55 (R40), D4.62 and D4.65 (R23), D4.64 (R06), D4.66 (R51).
- **L04 G3/R36** Req, add: "TempOffs converts to 0.01 °C ticks by rounding to nearest, not truncating (`asy_scd30_driver.py:570` `int(offset * 100)`; in float32, 130 of the 2,001 two-decimal inputs are stored one tick low), and the compare-before-write uses the same conversion (owner, 2026-09-29, OR101.a; D4.61)"; State, add: "test in U15 — every two-decimal input of the field's range is stored as typed".
- **L05 G5/R03** Req, add: "A boot-phase crash leaves a record too: `SystemService` writes the current boot-phase index to `machine.mem_backup()` region 1 (`scratch[5..7]`, 12 B; `ports/rp2/machine_mem_backup.c:38-41`, v1.29.0) at each boot-phase transition only, never per tick, and marks the boot complete; a watchdog reset with no record and an incomplete phase reads as a 'boot failure' code carrying the phase index. No flash, no FRAM (owner, 2026-09-29, OR102.a (6))"; State, add: "doc in U14 — SPEC F.5.4's 2026-09-11 'not adopted' note narrowed to per-tick breadcrumbs; the code table gains 'boot failure'; test in U11 — a driven crash in each phase; hardware in C".
- **L06 G3/R64** Title → "A signal request answers at once"; Req: "`request_signal()` returns once queued …" → "An LED command arriving while a signal runs is refused at once and answered `\"Failed\"` in the per-field result (legacy's 'LED is busy' in the new envelope, owner, 2026-09-29, OR102.a (5)); otherwise `request_signal()` returns once the request is queued …" (keep the rest); State, add: "code+test in U9 — the handler's spin past the 15 s cap goes (D4.117)".
- **L07 G6/R24** Req: "answers other QTYPEs without an A record" → "answers an A (1) or ANY (255) query with the A record and every other QTYPE with NOERROR and zero answers (NODATA, RFC 1035, RFC 2308 2.2): one QTYPE check in `response()`, nothing else changes (owner, 2026-09-29, OR102.a (7))"; Rank, add that owner row.
- **L08 G6/R29** Title → "WiFi password never disclosed; nothing excluded on PUT"; Req → "GET returns a fixed mask for `PW` and `HotspotPW` whatever is stored, open network included (legacy parity). No value is excluded on PUT: any valid 8-63 character string, `********` included, is stored like any other password. The page shows the dots as the current value and leaves the entry field empty; an empty field is omitted from the PUT and means 'unchanged' (both hold today: `js/field-format.js:19-20`, `js/templates.js:160-170`). An echoing non-page client can store the mask string, accepted (owner, 2026-09-29, OR104.a (1); legacy showed the value beside an empty field, `html_raw/general/nettimeconfig.html:45-47`, OR102)"; Rank → "owner — OR104.a (1)"; State: "mask-as-Unchanged decided on the owner's behalf" goes; "work: test in U18/U23 — a PUT of `********` stores it; the page never sends a mask (`tests_js/live-backend-put-matrix.test.js:134-137` already treats a resubmitted mask as a new password)".
- **L09 G6/R27** Req: "and AP mode does not count `WifiUptime`/`Connected`" → "and `WifiUptime`/`Connected` count while the link is up, hotspot included, as legacy, documented as 'link up, hotspot included' (owner, 2026-09-29, OR102.a (8))"; State, add: "doc in U18 — the field help text and DEVICE_REFERENCE.md say so".
- **L10 G6/R30** Rank: S06 → "owner — restored (owner, 2026-09-29, OR102.a (3))"; State: "S06 goes on the pass-3 legacy-loss question list … unless OR57.a alone covers it" goes.
- **L11 G4/R22** State, add: "doc in U14 — SPEC F.2 states that rp2's I2C construction clocks nothing out, so a slave held mid-byte survives an MCU reset and needs a power cycle (operator action, LEAD/R14); hardware in C — one row measures it; no boot-time bus clear (settled by the lead, harmonization 38, OR64.a; D4.217, pass-3 SUMMARY)".
- **L12 G9/R03** State, add (with P066): "fix option (a): the verify period is `max(1, …)` over the existing formula, written once through REF/R05's single helper; only `BackupPeriod` 67-1440 changes (every save verified), every other period keeps today's cadence; regression tests at p = 1, 7, 32, 60, 66, 67, 1440 (owner, 2026-09-29, OR104.a (2))".
- **L13 G6/R49** State, add: "code+test in U19 — a connection the server drops before the handler runs (admission refusal, accept failure, early reset) leaves a persisted, rate-limited trace, so a recurrence of BACKLOG 30 (ISL29125 PUT + 2 readers reset, 6/18 on 2026-09-17, nothing in FRAM or errcount) leaves evidence; BACKLOG 30 stays closed (owner, 2026-09-29, OR102.a (9); H2.99)".
- **L14 G9/R19** Req, add: "The Part also carries the owner's 2026-07-13 structural patterns, each tagged '(owner, 2026-07-13)' and checked against later owner rows (the most recent wins): config and behaviour defined once; per-sensor config storage; inheritance; generalised startup and error recovery; an FRAM error trace surviving reboot; errors printed and persisted, never persisted instead of printed; generic FRAM handling; similar behaviour in classes; long or deep flows split into subfunctions with early returns; duplicated code consolidated with hard-coded constants turned into parameters (`7c653fe`, `2421948`, `07c7896`, `144873f`; H1.16, H1.17, H2.01)"; State, add: "doc in U0/U36 — BACKLOG.md:74-76's 'structural patterns above … robustness items above' pointers go".
- **L15 G3/R03** Req, add: "CRC integrity is an intentional, evolving standing feature, applied wherever data integrity matters; UART CRC stays optional per J.3 (owner-confirmed, 2026-07-13, `144873f`; H2.04)".
- **L16 G2/R17** State, add: "the Unix-port `modselect.c` residual is a known limitation; nobody files it upstream (owner, 2026-09-29, OR102.a (10))".
- **L17 G7/R12** Req: "(an upstream issue is filed; the fix at the pinned tag is the removal trigger)" → "(a known limitation, not reported upstream; removal trigger: the fix seen at a pin re-check)" (owner, 2026-09-29, OR102.a (10)); State, add: "doc in U25 — `digital_twin/README.md:916-919`'s 'worth filing one upstream' becomes that limitation (O.75)".

## 3 Lead-written requirements (LEAD.md, REF.md)

- **LEAD/R24** No counter allocates or runs unbounded (OR103.a, OR105.a).
- **LEAD/R25** Config values have an explicit scope (P102).
- **LEAD/R26** Logs and comments are English (P103).
- **LEAD/R27** Hardware sessions do not wait passively for rare events (P104).
- **LEAD/R28** UART comm-hazard coverage at every tier (P105).
- **LEAD/R29** A reconnected sensor or FRAM recovers without a reboot (P083).
- **REF/R03** extended: one never-UTC elapsed-time primitive for all four values (OR101.a, OR104.a (3), D4.36).
- Scan lines on LEAD and REF blocks (P047, P048, P053, P057, P058 and any other) are applied by the lead.

## 4 Owner-row corrections

- OR102.a (6): "region 1 (RP2040 watchdog scratch registers `scratch[0..3]`" was wrong — region 0 is `scratch[0..3]` (16 B, G5/R03's reset-reason record), region 1 is `scratch[5..7]` (12 B) (`ports/rp2/machine_mem_backup.c:38-41`, v1.29.0). Corrected in place; the owner's condition (no flash, no FRAM) is unaffected.
