# A-L wave 2 — register fixes applied to `audit/pass2/`

Input: the "Register fixes" sections of `audit/actions/U9.md` … `U14.md` as corrected by their verifications
(`audit/actions/verify/U9.md` … `U14.md`), the notes at the end of `U12.md`, `U13.md` and `U14.md`, and
`PROJECT_AUDIT_PLAN.md` 3.2 OR112-OR115. Each applied fix carries "A-L: <unit> register fix <k>." on its block's
Pass 2 line. Fixes are numbered in the order their section was first written (U11's withdrawn fix 2 keeps its number,
as the verification cites it; U9, U10, U12-U14 are numbered as their sections stand). Source lines re-checked at HEAD
(`src/`, `buildgen/` unchanged since the units' own HEADs).

- U9 fix 1 → G3/R62: applied
- U9 fix 2 → G3/R64: applied (form of V.U9.19)
- U9 fix 3 → G9/R36: applied
- U9 fix 4 → G4/R56: applied (form of V.U9.17)
- U9 fix 5 → —: not applied — no register target: V.U9.18 turned it into an A-C note (A.U0.25's routing
  parenthesis and Blast → A.U9.01), left to A-C
- U10 fix 1 → G5/R49: applied
- U10 fix 2 → G5/R50: applied (44 of 63, V.U10.05)
- U10 fix 3 → G5/R12: applied
- U10 fix 4 → G10/R17: applied
- U10 fix 5 → LEAD/R17: applied (the unit clause goes into State, where the register keeps units)
- U10 fix 6 → G9/R38: not applied — the conflicting "L19 (U18)", "L57 (U18)" are in `audit/actions/U0.md`'s G9/R38
  ledger row (`:1623`), not in the register block, whose State names no unit for L19/L57; A-C corrects U0's row to
  U10 (A.U10.18/A.U10.19)
- U10 fix 7 → G5/R32: applied (doc item moved to U0, A.U0.29)
- U10 fix 8 → G5/R15: applied (doc item moved to U0, A.U0.38)
- U10 fix 9 → REF/R03: applied
- U10 fix 9 → LEAD/R24: applied
- U10 fix 10 → G5/R07: applied (current line: `_timer_sequencer()` starts at `:148`, `:147` is blank; cited
  `:148-175`)
- U10 fix 11 → REF/R04: applied (`:146` holds as the expression line; `_now()` `:144-148`, RTC `:263` and
  `_handle_ntp_sync_success()` `:310-316` added beside it)
- U10 fix 12 → —: not applied — no register target (A-C note on the no-audit-ID rule at A.U0.25/A.U0.38/A.U0.29)
- U10 fix 13 → G5/R50: applied (added by V.U10.40)
- U10 fix 14 → G5/R14: applied (16 `async def setup` in `src/`, 13 `None`, 3 `bool`, re-counted at HEAD)
- U10 fix 15 → G10/R14: applied (added by V.U10.40)
- U11 fix 1 → G5/R02: applied
- U11 fix 2 (as drafted) → G4/R11: not applied — withdrawn by V.U11.09 (the VOC half is U12 fix 8); removed from
  U11.md
- U11 fix 3 → G5/R24: applied (form of V.U11.12; the clause is in State, not Req, and is replaced there)
- U11 fix 4 → G5/R47: applied
- U11 fix 5 → G5/R38: applied
- U11 fix 6 → G5/R45: applied (U33's README clause replaced by a pointer to G7/R44's U11 clause)
- U11 fix 7 → G10/R19: applied
- U11 fix 8 → LEAD/R20: applied
- U11 fix 9 → G5/R03: applied
- U11 fix 10 → —: not applied — catalog edits to A.U2.01, not the register (AC_NOTES item 7)
- U12 fix 1 → G3/R09: applied
- U12 fix 2 → G3/R10: applied (10223 s, V.U12.19)
- U12 fix 2 → LEAD/R24: applied
- U12 fix 3 → G3/R06: applied
- U12 fix 4 → G3/R06: applied (Home)
- U12 fix 5 → G3/R05: applied (`b131169`, V.U12.18)
- U12 fix 6 → G3/R04: applied
- U12 fix 7 → G3/R03: applied
- U12 fix 8 → G4/R11: applied
- U12 fix 8 → G3/R12: already applied (its State already gives the `"<"` prefix to U12; no edit, no tag)
- U12 fix 9 → G3/R06: applied (added by V.U12.20; the lead's Q1 (c) note at the end of U12.md)
- U13 fix 1 → G3/R20: applied
- U13 fix 2 → G6/R16: applied (form of V.U13.17)
- U13 fix 3 → G3/R15: applied
- U13 fix 4 → G4/R41: applied
- U13 fix 5 → G3/R16: applied as reworded by the lead's note (end of U13.md, AC_NOTES 11): the CS pad state and the
  power-on hold time met by boot timing are a documented fact for SPEC C.3.1; no pull-up check or board change is
  written (the verified form's "checked for both FRAM parts … board change for the owner" is withdrawn). State's
  "hardware in C — scope CS … board schematic checked for a CS pull-up" is left unchanged: the note does not say
  whether phase C still scopes CS; it follows A-C's rewrite of A.U13.04. U13.md's own fix 5 text is A-C's to reword.
- U14 fix 1 → G4/R30: applied (settimeout dropped; bound-method identity and `asyncio.core` moved out of the
  divergence list as shared harness rules; `getsockname()` stated absent on both ports; Rank cites `:1924-1925` for
  the tick period beside `:1892-1893`, POSIX select)
- U14 fix 2 → G4/R44: applied in U14.md's OR114 form (V.U14.R2's OR112 sizing form overtaken by OR114.a): Req's
  static-proof sentence replaced by the floor-not-proof text, State's U14 proof item withdrawn; the OR114.a/OR115.a
  text the block already carried is unchanged
- U14 fix 3 → G5/R09: applied (Req only, as the fix names; State's "pool size 16" wording unchanged)
- U14 fix 4 → G4/R15: applied (with V.U14.R4's `test_asy_fram_manager.py:1940-1974`)
- U14 fix 5 → G6/R28: applied
- U14 fix 6 → G1/R15: applied
- U14 fix 7 → G5/R10: applied
- U14 fix 8 → G3/R03: applied (current line: `_probe_for_device()` is `asy_i2c_driver.py:261-269`, `:260` is blank)
- U14 fix 9 → G4/R48: applied
- U14 fix 10 → G4/R03: applied
- U14 fix 11 → G4/R21: applied (added by V.U14.R11)

No other wave-2 fix is overtaken by OR112-OR115: only U14 fix 2 cites the lwIP sizing, and OR113 changes none of
these targets.

## U8C → U8.md

Input: `audit/actions/U8C.md` "Register fixes" (verified 2026-09-30, `verify/U8C_tests.md`,
`verify/U8C_tests_hardware.md`: all six right), with `audit/actions/U8C2.md`'s register fixes where they amend the
same U8.md target (verified by the same two files and `verify/U8C2_G16-G18.md` V.08).

- U8C fix 1 → U8.md A.U8.11 Blast: applied (`:1067` a Dependant of `dns_server.recv_backoff_max_s`, not a mirror);
  C.0.2's mirror list, which restated the same claim, corrected with it
- U8C fix 2 → U8.md A.U8.08 Blast: applied
- U8C fix 3 → U8.md Ledger G4/R54 row and register fix 6: applied — the row's result names A.U8C.01-A.U8C.121 and
  A.U8C2.01-A.U8C2.51; register fix 6 is marked withdrawn (number kept, wave 1 cites U8's fixes by number). AC_NOTES
  item 10 resolved with it: Appendix C's title and Status and the G7/R23 ledger row no longer say NOT-DONE
- U8C fix 4 → U8.md A.U8.05 Site/Change: applied, with U8C2's same-target amendment (`:62, :78, :100, :101`,
  `harness.py:278, :284`); IDs as created by A.U8C.47, A.U8C.112, A.U8C2.18, A.U8C2.47
- U8C fix 5 → U8.md Appendix C.0.1 counts: applied (2,265 as the counted figure; the reference script's 2,286 and
  its keying stated)
- U8C fix 6 → U8.md Appendix C.0.1 families: applied in U8C2's extended form (19 families, 2,265 + 931 = 3,196
  sites; U8C2 named as C.0.1's supplement)

Left (outside this pass): U8C2's other register fixes — U8.md A.U8.04 Blast (`test_asy_webserver_service.py:2569`),
A.U8.13 (`isl29125_lighting_scenarios.py:335`), A.U8.09 (no change, recorded), and U8C.md search-gap 7 lines,
A.U8C.04, A.U8C.84 (with V.U8C_tests_hardware's drop of its sibling-rows sentence).
