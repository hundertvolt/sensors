# A-L wave 3 — register fixes applied to `audit/pass2/`

Input: the "Register fixes" sections of `audit/actions/U15.md` … `U34.md`, `SUPP_recovery.md`, `SUPP_owner_0930.md` and
`SUPP_deps.md` (`SUPP_lwip.md` has none), each as corrected by its verification (`audit/actions/verify/<unit>.md`; a
verifier item that corrects, adds or rejects a fix wins over the author's text, and most corrections already stand in
the action files), plus `AC_NOTES.md` item 22 (G6/R49 "rate-limited trace" → one trace per event) and item 36 (OR130:
G5/R02 Req rewrite and OR31.a (3)'s two-call-site test), and `PROJECT_AUDIT_PLAN.md` 3.2 up to OR130. Each applied fix
carries "A-L: <unit> register fix <k>." (or "A-L: AC_NOTES item <n>.") on its block's Pass 2 line; a fix already
carried by an earlier unit's identical edit is tagged without a second edit. Source lines re-checked at HEAD `98065fb`
(`src/`, `buildgen/`, tests, SPEC, BACKLOG unchanged through `b50ba73`); MicroPython citations against the v1.29.0
checkout. U35, U36a, U36b, U37 and C are not processed (still being written or verified). After the edits
`audit/sweeps/pass2_check.py` reports 0 missing in every category and `audit/sweeps/pass2_index.py` regenerated
`audit/pass2/INDEX.md`.

- U15 fix 1 → —: not applied — withdrawn (V.U15.28; resolved by `8a70891`), A-C carries SUPP's LEAD/R30 row
- U15 fix 2 → G3/R36: applied
- U15 fix 3 → G3/R22: applied (`_store_isl()` `asy_isl29125_driver.py:497-498` holds at HEAD)
- U15 fix 3 → G7/R45: applied (State's "ISL29125 publishes `None`" clause and "code in U15" → test in U15)
- U15 fix 4 → G3/R43: applied (`:553` poll step, `setup()`'s `wait_time` passed by no production caller, at HEAD)
- U15 fix 5 → G3/R56: applied
- U15 fix 6 → G5/R28: applied in the reversed form (V.U15.09)
- U15 fix 7 → G5/R10: applied (`_cal_until_ms` added as bounded, A.U15.35)
- U15 fix 8 → G3/R26: applied (`asy_sgp40_driver.py:543`, `asy_scd30_driver.py:445` hold)
- U15 fix 9 → G7/R41: applied in V.U15.27's amended form (`asy_scd30_driver.py:68` holds the first half)
- U15 fix 10 → G3/R42: applied (current lines `:158`, `:508`)
- U15 fix 11 → G5/R21: applied (legacy `:71, 101-107` checked)
- U15 fix 12 → G3/R44: applied (the pointer named as HR080's, per `G3.md` cross-check)
- U15 fix 13 → —: not applied — A-C note on A.U2.01's catalog and A.U4.03/04, not a register line
- U15 fix 14 → REF/R06: applied (V.U15.29; 1.4.5 at `:654`, FRC text `:982-990` checked)
- U16 fix 1 → G5/R25: applied (`asy_fram_manager.py:672, 716` `logger=self.pr` at HEAD)
- U16 fix 2 → G5/R29: applied (`SPECIFICATION.md:1552-1555` is under C.3; no `_send_opcode()` in `src/`)
- U16 fix 3 → G5/R32: applied (`buildgen/codegen.py:664`)
- U16 fix 4 → G3/R21: applied (the `initialized` guards at `asy_fram_driver.py:272-362`)
- U16 fix 5 → G4/R64: applied (18,089-23,148 µs at `SPECIFICATION.md:4014`)
- U16 fix 6 → REF/R02: applied (`asy_fram_manager.py:381-382`, `codegen.py:587`, test `:2000` hold)
- U16 fix 7 → G5/R26: applied
- U16 fix 8 → G4/R61: applied in V.U16.17's form (`codegen.py:502-503` holds; "U16/U36" → U0)
- U16 fix 9 → G3/R12: applied with V.U16.18's `SPECIFICATION.md:418-420` (all six sites checked)
- U16 fix 10 → G5/R29: applied (added by V.U16.19)
- U16 fix 11 → G5/R27: applied (added by V.U16.20)
- U17 fix 1 → LEAD/R24: applied in V.U17.16's form (against the State as `8943507` left it)
- U17 fix 2 → G6/R21: applied in V.U17.17's form (`asy_uart_driver.py:415` holds the growth comment)
- U17 fix 3 → G6/R21: applied (`asy_uart_comm.py:1062-1063, 937-938, 796-804` hold)
- U17 fix 3 → G4/R40: applied
- U17 fix 4 → G4/R40: applied (`:5645-5647` "Paired transfer APIs", `:5650-5652` "Preallocate" at HEAD)
- U17 fix 5 → G7/R01: applied
- U17 fix 6 → G6/R11: applied
- U17 fix 7 → G6/R15: applied
- U17 fix 8 → G6/R01: applied (changelog rows B7 `:78`, B26 `:97`)
- U17 fix 9 → G4/R55: applied (all three clauses → U13; changelog entries to U17)
- U17 fix 10 → LEAD/R28: applied
- U18 fix 1 → G6/R24: applied (`captive_dns.py:161-165, 186, 198` `_parsed_ok` at HEAD)
- U18 fix 2 → G6/R24: applied
- U18 fix 3 → G6/R26: applied
- U18 fix 4 → REF/R02: applied in V.U18.05's form (four test sites `:758, 919, 1571, 1605`; product calls `:156, 164, 172` pass none)
- U18 fix 5 → G4/R23: applied with V.U18's line set (`modlwip.c:843-844, 505-507, 732-737, 751-760` at v1.29.0; `tcp_sndbuf()` is `:760`)
- U18 fix 6 → G1/R29: applied (tests `:990-1068`, README `:893-895` hold)
- U18 fix 7 → G7/R01: applied (`resolve_ipv4(port=)`, V.U18.A1, A.U18.45)
- U18 fix 7 → REF/R02: applied (`__aenter__`/`__aexit__`, V.U18.A2, A.U18.46; `asy_udp_socket.py:61-71`)
- U18 fix 8 → G6/R34: applied (no "legacy REST" in the five NET files)
- U18 fix 9 → —: not applied — catalog edits to A.U2.01, not the register (A-C)
- U18 fix 10 → G5/R16: applied (the register half; the A.U10.06/A.U14.26 text in V.U18.R10's form is A-C's)
- U18 fix 11 → LEAD/R24: applied
- U18 fix 12 → G4/R15: applied
- U19 fix 1 → G4/R45: applied (`asy_webserver_service.py:113, 123, 387, 698` at HEAD)
- U19 fix 2 → G6/R49: applied with V.U19.L3's H.7 sentence (`stream.py:160-164`, `modlwip.c:1157-1167` at v1.29.0)
- AC_NOTES item 22 → G6/R49: applied — "rate-limited trace" → one trace per event (OR35.a (2), OR35.b; V.U19.08/23); tagged "A-L: AC_NOTES item 22."
- U19 fix 3 → LEAD/R08: applied in V.U19.R3's form (fifteen sites, each grep-checked; route block `:372-382`)
- U19 fix 4 → G6/R52: applied in V.U19.R4's form (`print_log.py:111-117`)
- U19 fix 5 → G4/R43: applied (`SPECIFICATION.md:4944-4957`, `:4926`)
- U19 fix 6 → G4/R62: applied (`:4371`, `:1859-1863` hold at HEAD `98065fb`)
- U19 fix 7 → G5/R54: applied (`asy_webserver_service.py:711-715`, `ext/microdot.py:1399-1408`)
- U19 fix 8 → G1/R11: applied
- U19 fix 9 → G6/R39: applied
- U14 follow-ups of AC_NOTES item 22 (A.U14.30, A.U14.28 row 15) → —: not applied — action-file edits, not the register
- U20 fix 1 → G2/R11: applied (AST re-count at HEAD: 30 no-assert tests at the listed lines)
- U20 fix 1 → G2/R21: applied
- U20 fix 2 → —: not applied — the "banner rule lengths differ per file (cosmetic)" truth is in `audit/hreq/G10.md:603` (pass-1 candidate G10.066), not in any `audit/pass2/` block; G10/R33 carries no banner-length statement (A-C decides whether G10/R33's State takes the fact)
- U20 fix 3 → G8/R06: applied (`codegen.py:382, :489` index `model.doc["bus"]`)
- U20 fix 4 → G4/R25: applied (v1.29.0 `machine_uart.c:76` `IS_VALID_TX`: GP28 & 3 == 0, periph 0)
- U20 fix 5 → LEAD/R07: applied
- U20 fix 6 → G8/R04: applied (the seven names emitted in `codegen.py:501-693`)
- U20 fix 7 → G8/R18: applied
- U20 fix 8 → LEAD/R17: applied
- U20 fix 9 → G1/R36: applied
- U20 fix 10 → G5/R01: applied (added by V.U20.46)
- U21 fix 1 → —: not applied — no register text changes (INDEX/input note; the ledger carries G4/R44)
- U21 fix 2 → G8/R19: applied
- U21 fix 3 → G4/R44: not applied — withdrawn (V.U21.05: register and U19's A.U19.24 already carry it)
- U21 fix 4 → G8/R22: applied (`setup_toolchain.py:228, 240, 309, 318, 945` hold)
- U21 fix 5 → G8/R21: applied
- U21 fix 6 → G5/R59: applied
- U21 fix 7 → G8/R28: applied (`bench_control.py:132` runs `sudo timeout 60 tcpdump`)
- U21 fix 8 → —: not applied — no register text changes (noted for A-C)
- U22 fix 1 → G9/R36: not applied — already applied in wave 2 (U9 fix 3; V.U22.07)
- U22 fix 2 → G4/R56: not applied — dropped: A.U22.03 declined by the owner (OR126.a (4))
- U22 fix 3 → G10/R07: applied (`asy_notification_service.py:131-132` hold the two attributes)
- U22 fix 4 → G3/R65: applied (State; the Req's "guards `neopixel_freq = 0`" left for A-C with A.U9.07)
- U23 fix 1 → G6/R28: applied in V.U23.07's reason (no bound check in `js/render.js`)
- U23 fix 2 → G2/R11: applied (V.U23.06: `live-backend.test.js:20-23` right as the register has it)
- U23 fix 3 → G7/R01: applied (`asy_notification_service.py:131-132, 205-220`). Note for A-C: U22 fix 3 (G10/R07) names A.U22.02 for the same two removals — two actions, one change
- U23 fix 4 → G7/R29: applied
- U23 fix 5 → G7/R27: applied
- U23 fix 6 → G7/R37: applied (`templates.js:91` a comment, `nav.js:52` the one non-entry query, at HEAD)
- U23 fix 7 → G9/R05: applied
- U23 fix 8 → G7/R37: applied (added by V.U23.08)
- U24 fix 1 → G2/R03: applied (eight `except OSError:` at `tests/_tmp_scratch.py:15, 23, 28, 32, 50, 54, 65, 76`)
- U24 fix 2 → G2/R04: applied (v1.29.0 `modselect.c:252-266` GET_FILENO, `machine_uart.c:696-698` EINVAL; twin `machine.py:675-677` returns 0)
- U24 fix 3 → G8/R46: applied (207 re-counted at HEAD `98065fb`, unchanged since `6b19da7`)
- U24 fix 4 → —: not applied — A-C note (A.U24.80 / A.U25.04 co-land), no register text
- U24 fix 5 → G2/R11: applied (after U20 fix 1's 38/30 counts)
- U24 fix 6 → G2/R11: already applied by U23 fix 2 (same clause, "test in U23 (A.U23.32)"); tagged, no further edit
- U24 fix 7 → G8/R01: applied
- U24 fix 8 → G2/R11: applied
- U24 fix 9 → G9/R34: applied in V.U24.51's form
- U24 fix 10 → LEAD/R28: already applied by U17 fix 10 (U17 and U26, no U24 part); tagged, no further edit
- U24 fix 11 → G2/R02: applied
- U24 fix 12 → G1/R41: applied (RF136 half stays U24's)
- U24 fix 13 → G2/R10: applied
- U25 fix 1 → G1/R11: applied (`_clean_state()` `:238-248`, nine references incl. the def; `run_digital_twin_ci.sh:10-11` comment)
- U25 fix 2 → G4/R51: applied (`:18-22` probe, `:32-35` starter-loop constants at HEAD)
- U25 fix 3 → G7/R05: applied (no "keeps serving" in `digital_twin/README.md`)
- U25 fix 3 → G7/R17: applied (`:447-449`, `:466-471`)
- U25 fix 4 → G7/R18: applied (`_digital_twin_ci_suite.py:999, 1019, 1028`)
- U25 fix 5 → G7/R16: applied (`_fault_injection.py:16` `[exc] * times`)
- U25 fix 6 → G2/R07: applied (`test_digital_twin_sgp40.py:35`)
- U25 fix 7 → G8/R01: already applied by U24 fix 7 (RF111 → U24 per V.U25.50); tagged, no further edit
- U25 fix 7 → G2/R11: already applied by U24 fix 8; tagged, no further edit
- U25 fix 8 → G7/R12: applied (`run_generic_integration.py:332` prewarms first)
- U25 fix 9 → G1/R41: applied (`_ADDR_ID` at `:10`)
- U25 fix 10 → LEAD/R24: applied (`machine.py:669` `UART.superseded += 1`)
- U25 fix 11 → —: not applied — edits an action file (`SUPP_recovery.md` A.U15.R02 Blast), not the register (AC_NOTES 31, A-C)
- U25 fix 12 → G4/R51: applied (added by V.U25.51; `:59-61`, `:76-77`, `:183-184` hold)
- U25 fix 13 → G7/R21: applied (added by V.U25.20; `:156` membership check)
- U26 fix 1 → G1/R06: applied in V.U26.02's form (markers at `:23, 31, 38, 44, 68, 76, 85` + `:86` at HEAD); OR90.a (1)'s "seven" is not register text (AC_NOTES 35/37, owner-accepted)
- U26 fix 2 → G1/R03: applied (`:170` at HEAD)
- U26 fix 2 → G2/R27: applied (`:334-351`)
- U26 fix 3 → G6/R36: applied (the only register site naming the CYW43 firmware as DHCP server)
- U26 fix 4 → G1/R07: applied (`:150-177` seven pushes, `:193` dispatch-only)
- U26 fix 5 → G4/R60: applied in V.U26.03's form (`README.md:383-386`)
- U26 fix 6 → G1/R32: applied (added by V.U26.12; `asy_fram_manager.py:244, 259, 262, 277, 280` hold)
- U27 fix 1 → G4/R36: applied
- U27 fix 2 → G9/R16: applied with V.U27.15's `html/index.html`
- U27 fix 3 → G8/R01: applied (the `scripts/` literals checked at HEAD)
- U27 fix 4 → G8/R31: applied (87 `tests/test_*.py`; `test.sh:43`, `SPECIFICATION.md:2931` hold)
- U27 fix 5 → G8/R24: applied with V.U27.10's four CI steps and `isl29125_conformance.py:39-42`
- U27 fix 6 → LEAD/R08: applied — `:121` was already listed by U19 fix 3 (V.U19.R3); the fix adds its `_SOAK_ENDPOINTS` label only
- U27 fix 7 → G7/R19: applied
- U27 fix 8 → —: not applied — dropped by the author, rejected by V.U27.01
- U27 fix 9 → G4/R36: applied (added by V.U27.18)
- U27 fix 10 → G8/R61: applied (V.U27.13)
- U27 fix 11 → G8/R47: applied (V.U27.13)
- U27 fix 12 → LEAD/R13: applied (V.U27.16)
- U28 fix 1 → G5/R32: already applied by U16 fix 3 (same correction); tagged, no further edit
- U28 fix 2 → G7/R32: applied (`grep WEBSITE_PLAN`: none at HEAD)
- U28 fix 3 → G7/R14: applied (`.gitignore:75-79`)
- U28 fix 4 → G8/R63: applied
- U28 fix 5 → G8/R51: applied as State evidence (`setup_toolchain.py:258, 263, 276`)
- U28 fix 6 → G8/R50: applied (`filters:` `:42`, list `:43-57`)
- U28 fix 7 → G8/R55: applied
- U28 fix 8 → G9/R23: applied
- U28 fix 9 → G5/R51: applied (76 = 39 E402 + 37 re-counted at HEAD)
- U28 fix 10 → G8/R51: applied (added by V.U28.21)
- U29 fix 1 → G5/R57: applied in V.U29.08's form (Sources gain OR117.a (3), OR122.a (2), OR126.a (3), OR42.a (3); `@web` dispatch tags at `asy_sgp40_driver.py:65`, `asy_isl29125_driver.py:159`)
- U29 fix 2 → G5/R57: applied (State and Home)
- U29 fix 3 → G5/R60: applied (`pyproject.toml:233-235, :252`; `_VAL_HOTSPOT_PW` tuple `asy_wifi_service.py:53`)
- U29 fix 4 → G5/R59: applied in V.U29.07's form (OR127)
- U30 fix 1 → G4/R42: applied in V.U30.01's form (v1.29.0 `ports/unix/modtime.c:138` 9-tuple, `extmod/modtime.c:203` gmtime = localtime)
- U30 fix 2 → G4/R42: applied (`asy_isl29125_driver.py:1113`, `py/objstr.c:357-359`)
- U30 fix 3 → G4/R50: applied in V.U30.09's form (lines re-read at HEAD)
- U30 fix 4 → G4/R57: applied (archive `12640c2`:2657-2667 checked)
- U30 fix 5 → G4/R49: applied with V.U30.02's 39 calls (42 matches, 3 comments); the Req's "`GC_THRESHOLD` is validated" sentence kept, State records it holds (`scripts/test.sh:46-55`)
- U30 fix 6 → G4/R47: applied (`SPECIFICATION.md:4601-4602, 4855-4857` carry "20-30 %")
- U30 fix 7 → LEAD/R06: applied with V.U30.04's reset reason 20
- U31 fix 1 → G10/R23: applied with V.U31.14's 22 (the 22 lines re-grepped at HEAD; every other `asyncio.sleep(` in `src/` takes an int)
- U31 fix 2 → G10/R23: applied in V.U31.15's form (the A.U30.02 (3) row is A-C's)
- U31 fix 3 → G4/R58: applied (`SPECIFICATION.md:544` "Setup costs on silicon")
- U31 fix 4 → G4/R64: applied
- U31 fix 5 → G4/R64: applied with V.U31.01's 110-700 ms
- U31 fix 6 → G4/R64: applied
- U31 fix 7 → G5/R02: applied (OR130/OR130.a)
- AC_NOTES item 36 → G5/R02: the same Req rewrite as U31 fix 7 (one edit, both tags)
- AC_NOTES item 36 → G5/R01: applied — State's "single runtime feed site" test → the two supervisor-loop call sites pinned by one test (OR130.a refining OR31.a (3))
- U31 fix 8 → G5/R01: applied
- U32 fix 1 → G4/R04: applied (Home)
- U32 fix 1 → G4/R05: applied (Home)
- U32 fix 2 → G9/R04: applied (`SPECIFICATION.md:1795-1796` carry the post-write hook sentence)
- U32 fix 3 → G9/R05: already applied by U23 fix 7; tagged, no further edit
- U32 fix 4 → G9/R05: applied in V.U32.01's form (OR128; `system_service.py:238-240` holds)
- U32 fix 5 → G4/R05: applied in V.U32.08's form (`harness.py:441-444`)
- U33 fix 1 → G9/R31: applied (the A.U10.09/A.U26.86 disagreement is decided by the Req; A-C drops A.U10.09's THR half)
- U33 fix 2 → G1/R09: applied
- U33 fix 3 → G9/R31: applied in V.U33.06's form (`BACKLOG.md:465-469` pointer checked)
- U33 fix 4 → G8/R12: applied (`BACKLOG.md:638-658`)
- U33 fix 5 → G8/R30: applied
- U33 fix 6 → G8/R57: applied in V.U33.07's form (B.16); State's same pointer "B.15/H.8" moved with it
- U33 fix 7 → G9/R12: applied (the twelve changelog-entry citations re-grepped at HEAD)
- U34 fix 1 → G9/R20: applied (Req's karfas sentence and SPDX exception; State; `THIRD_PARTY_LICENSES.md:203-205` holds)
- U34 fix 2 → G9/R20: applied (the three headers wrap before the licence line at HEAD)
- U34 fix 3 → G9/R20: applied
- U34 fix 4 → G9/R22: applied — the "Truth gains" half is written into State as a verified fact (pass-2 blocks carry no Truth line); `build_frozen_html.sh:10-11, 30` hold
- U34 fix 5 → G9/R23: applied in V.U34.08's list
- SUPP_recovery fix 1 → G4/R22: applied with V.SUPP_recovery.21's State and title (`asy_i2c_driver.py:163-178`, v1.29.0 `extmod/machine_i2c.c:320-326` hold)
- SUPP_recovery fix 2 → G3/R38: applied (Req boundary, Rank)
- SUPP_recovery fix 3 → G4/R19: applied (v1.29.0 `ports/rp2/machine_i2c.c:50-53, 87`; twin `machine.py:238-247`)
- SUPP_recovery fix 4 → G5/R27: applied (beside U16 fix 11's clause; no overlap)
- SUPP_recovery fix 5 → G5/R32: applied (beside U16 fix 3; no overlap)
- SUPP_recovery fix 6 → LEAD/R29: applied (`system_service.py:229-253`)
- SUPP_recovery fix 7 → G6/R27: applied
- SUPP_recovery fix 8 → G4/R22: applied
- SUPP_lwip → —: no "Register fixes" section; nothing to apply
- SUPP_owner_0930 fix 1 → LEAD/R31: applied (`asy_uart_driver.py:58, 76` take the CRC; exerciser `:65-78` passes the bus on)
- SUPP_owner_0930 fix 2 → LEAD/R32: applied (HEAD writes defaults at `config_manager.py:459-460, 474-478`; A.U11.19 implements OR71.a (2))
- SUPP_owner_0930 fix 3 → LEAD/R32: applied
- SUPP_owner_0930 fix 4 → LEAD/R32: applied
- SUPP_owner_0930 fix 5 → LEAD/R32: applied (`_SYSTEM_COMMAND_GROUP` spans `definitions.py:55-62`)
- SUPP_deps fix 1 → LEAD/R33: applied with V.SDEP.21's five added blocks (Sources is `LEAD.md:349`)
- SUPP_deps fix 2 → LEAD/R33: applied (V.SDEP.22: State is `:351`)
- SUPP_deps fix 3 → INDEX.md: DONE at `d6557c5` (V.SDEP.23); regenerated again by this pass
- SUPP_deps fix 4 → —: not applied — targets `PROJECT_AUDIT_PLAN.md:775-777`, not the register (A.SDEP.24 carries it)
- SUPP_deps fix 5 → G6/R53: applied (Req and Sources, V.SDEP.24); its `PROJECT_AUDIT_PLAN.md:143` and `audit/CONSOLIDATION.md:48, 53, 230-232` halves not applied — outside the register (A-C / lead)

## Conflicts and notes for A-C

No two units' fixes conflict on one block. Where two fixes change the same clause they agree, and the second is tagged
without a second edit: U16 fix 3 / U28 fix 1 (G5/R32), U17 fix 10 / U24 fix 10 (LEAD/R28), U23 fix 2 / U24 fix 6
(G2/R11), U24 fixes 7-8 / U25 fix 7 (G8/R01, G2/R11), U23 fix 7 / U32 fix 3 (G9/R05), U31 fix 7 / AC_NOTES 36 (G5/R02);
U19 fix 3 and U27 fix 6 both add `_digital_twin_ci_suite.py:121` to LEAD/R08 (listed once). For A-C:
- U22 fix 3 (G10/R07) and U23 fix 3 (G7/R01) name two actions, A.U22.02 and A.U23.37, for the one removal of
  `NotificationSignal.triggered`/`last_value`: one lands, the other becomes its co-land.
- U33 fix 1 (G9/R31): A.U10.09 (rewrite the THR bullet) against A.U26.86 (remove it) — the Req decides for removal;
  A-C drops A.U10.09's THR half.
- U20 fix 2: whether G10/R33's State takes the per-kind banner-length fact (the text it corrects lives only in
  `audit/hreq/G10.md:603`).
- Two edits go one step past a fix's literal target, for consistency: G8/R57's State pointer moves with its Home
  (U33 fix 6), and G9/R22's "Truth gains" fact is written into State (U34 fix 4; pass-2 blocks have no Truth line).

## Left (outside this pass)

- Action-file edits named as register-fix neighbours: U25 fix 11 (`SUPP_recovery.md` A.U15.R02 Blast, AC_NOTES 31);
  AC_NOTES 22's U14 follow-ups (A.U14.30, A.U14.28 row 15); U8C2's own fixes on `U8.md` (A.U8.04/09/13 and the
  `U8C.md` items listed at the end of `REGISTER_FIXES_wave2.md`, AC_NOTES 23).
- Catalog notes for A.U2.01: U15 fix 13, U18 fix 9.
- Plan and consolidation texts: SUPP_deps fix 4 (`PROJECT_AUDIT_PLAN.md:775-777`, A.SDEP.24) and fix 5's
  `PROJECT_AUDIT_PLAN.md:143` / `audit/CONSOLIDATION.md:48, 53, 230-232` halves.
