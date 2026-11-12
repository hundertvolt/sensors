# D's check: the do-not-reopen decisions at their doc sites, 51c9c75f (W3a, agent, 2026-11-10)

The list is `audit/do_not_reopen.md` (8fcc6c5f, 2026-10-06): 271 decision rows in nine sections, plus section 10's
seven left-out bullets. Doc sites: SPECIFICATION.md, CLAUDE.md, BACKLOG.md, README.md, tests_hardware/README.md,
digital_twin/README.md, UART_C_PORT_CHANGELOG.md, DEVICE_REFERENCE.md, HEAP_FRAGMENTATION_MEASUREMENTS.md.

## Method (read-only, all output through the repo-text filter)
1. Each row's backticked identifiers and quoted owner words looked up verbatim at 51c9c75f: 67 rows, every key found.
2. The other 200: their distinctive tokens co-occurring in one passage (+-700 chars): 103 placed.
3. The remaining 97 read one by one with a targeted search each (`ftmp_w3a/bin/kw.sh`).
4. Currency: every row scanned for subjects a later ruling changed (FRAM hold and lock, lost chip, LED, NTP timers,
   tick timers, CRC yield, boot collects, verify_present, twin record); each hit read at its site.
Limits: "present" means the decision's text sits at a doc site; the 221 "correction owed" cells of 10-06 were not
re-checked one by one. Four rows hold a filtered word and were not read (A43, A47, B01, D03).

## Result
| state | rows | which |
|---|---|---|
| present and current | 244 | 67 (step 1) + 103 (step 2) + 78 of step 3's 97, less steps 1-2's four currency hits (L02, V40, A50, V14) |
| superseded: the docs carry the later ruling, nothing owed | 6 | A05 (wozi: now "the only unit a session flashes", CLAUDE.md:127); L02 (FRAM whole-block hold: synchronous operations, SPECIFICATION.md:4053); L30 (CRC per-byte yield, "don't touch": the owner's 2026-11-09 words dropped the incremental CRC, SPECIFICATION.md:51, UART_C_PORT_CHANGELOG.md:222); L38 (explicit Any deferred: owner 2026-09-28 "do it in this audit", done b5f2978c); V40 (boot-confined collects: "the firmware calls no gc.collect()", CLAUDE.md:312-313, e1958815); A50 (uptime timer degrades on ENOMEM: no uptime Timer since 39e18d2a) |
| moot: the subject left the tree | 5 | L07 (`DEV_UNIQUE_GROUPS`: no hit outside audit/); V27 (hand-written html/definitions retired, nothing to state); V46 (the catalog holds no reserved range); V77 (cfg_schema's legacy-REST reason: no hit); V80 (`segfault_stress_repro.py` gone) |
| CONTRADICTED | 1 | V14 "FRAM `verify_present()`/`set_write_protected()` stay" (owner, 2026-09-26, OR36.a (3): "These are functions of the hardware items … So they remain as they are."). `verify_present()` was removed by 1547690d (2026-11-09); SPECIFICATION.md:3187-3188 records it as "(agent, 2026-11-09)" under the 20:43:39 direction, "nothing in src/ called it". The owner's 18:30:08 rule of the same day asks before removing an unused function. Needs the lead, then the owner: restore it (its pre-audit form) or the owner accepts the removal. `set_write_protected()` stays (src/asy_fram_driver.py:288) |
| not located by search | 11 | A24 (the UI cannot set an empty string); A51 (recombination timing tests); E09 (twin FRAM state persists by default for the manual entry point); V54 (the two device-script loose ends); V61 (hazard-test latency blindness corrected or justified); L11 (dynamic imports banned: held by tests_scripts/test_import_graph.py:174, no doc line); L21 (no int-to-float round-trip check below 2**24); L24 (mock simulated a backend gap fixed in 323a1a7); L27 (rejected heap remedies stay rejected; HEAP_FRAGMENTATION_MEASUREMENTS.md:394 "M8. Research gaps, closed as not pursued" is the nearest); L61 (no forced further mock/twin sharing); L70 (unknown-length pull transfers outside the wire format, J.3) |
| not read (filter) | 4 | A43, A47, B01, D03 |

The 11: each is either an engineering-local agent row (L11, L21, L24, L27, L61, L70: section 9, "kept") or an owner
row whose words may sit in other phrasing (A24, A51, E09, V54, V61). Smallest step: one reading of the 11 against
SPECIFICATION.md before D; a row with forward value and no site gets one line, the rest go with audit/ (tagged).

## Section 10 (left out at 10-06), at 51c9c75f
B06 re-decided (OR70.a (4)); OR62.a overtaken (OR64.a); C09 overtaken (OR79.a: the last round's off-subnet DNS
item, L07); C12/C13 `readline_until_complete()` kept with no caller (O2's list); E04 unpinned Firefox: not
re-checked here; L31/L54 decided in the dead-code pass; L67 hand version bump: the release is 2.0 (owner,
2026-11-10, 5b8c3446).
