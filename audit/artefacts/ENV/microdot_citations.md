# Microdot citations across the pin move (M.PROC.013 (1))

Microdot moved `v2.6.2` → `v2.7.0` (family (d), `6ca1d7f`); MicroPython, its submodules, freezefs and the stubs did not move,
so this is the whole list. Method: every `…microdot.py:N` citation in `audit/actions/*.md` (with `SUPP_lwip.md`, `AC_NOTES.md`)
and `audit/consolidation/M_*.md`, plus each bare `:N` continuing a sentence whose last named file is `ext/microdot.py`,
mapped through a line diff of `git show 798e5a7:ext/microdot.py` against `6ca1d7f:ext/microdot.py` (unchanged lines only).
Result: 75 line citations; **none cites changed text**; 17 cite shifted lines (new numbers below);
63 `v2.6.2` literals (the version the action was written against). 12 continuations past the file's end are
SPECIFICATION.md lines in the same sentences, not Microdot lines (excluded). No permanent text outside `audit/` cites
Microdot line numbers. Step (2) of M.PROC.013 runs per unit: each action below updates its numbers when its unit starts.

| action | citations (old → v2.7.0) |
|---|---|
| A.C.13 | `C.md:505` 425-430→425-430; `C.md:506` 1443-1445→1461-1463 (shifted) |
| A.C.19 | `C.md:845` 425-430→425-430; `C.md:845` 1443-1445→1461-1463 (shifted); `C.md:849` 411-415→411-415 |
| REGISTER_FIXES_wave3.md | `REGISTER_FIXES_wave3.md:72` 1399-1408→1417-1426 (shifted) |
| A.SDEP.06 | `SUPP_deps.md:246` 567→567; `SUPP_deps.md:246` 746→746; `SUPP_deps.md:247` 397→397; `SUPP_deps.md:248` 400→400; `SUPP_deps.md:263` 666→666 |
| A.SDEP.18 | `SUPP_deps.md:667` 567→567; `SUPP_deps.md:667` 746→746 |
| A.SDEP.25 | `SUPP_deps.md:911` 567→567; `SUPP_deps.md:911` 746→746 |
| A.U0.44 | `U0.md:1465` 1330→1348 (shifted); `U0.md:1465` 1037→1037; `U0.md:1466` 1037→1037 |
| A.U14.03 | `U14.md:84` 56-61→56-61 |
| A.U18.43 | `U18.md:1307` 567→567; `U18.md:1307` 746→746 |
| A.U19.06 | `U19.md:190` 684→684; `U19.md:191` 1562→1580 (shifted); `U19.md:192` 692-696→692-696; `U19.md:192` 700-705→700-705; `U19.md:198` 380→380; `U19.md:198` 434→434; `U19.md:216` 433-434→433-434; `U19.md:218` 636-663→636-663 |
| A.U19.07 | `U19.md:236` 420-426→420-426; `U19.md:241` 533-537→533-537; `U19.md:241` 412-421→412-421; `U19.md:249` 317→317; `U19.md:261` 423-430→423-430; `U19.md:264` 56-61→56-61; `U19.md:264` 1402-1405→1420-1423 (shifted); `U19.md:265` 1548-1549→1566-1567 (shifted); `U19.md:276` 403-426→403-426 |
| A.U19.08 | `U19.md:322` 1402-1405→1420-1423 (shifted); `U19.md:326` 1399-1408→1417-1426 (shifted); `U19.md:328` 725→725 |
| A.U19.18 | `U19.md:678` 16-18→16-18 |
| A.U19.19 | `U19.md:699` 292-294→292-294 |
| A.U19.23 | `U19.md:787` 1407-1408→1425-1426 (shifted); `U19.md:798` 1407-1408→1425-1426 (shifted); `U19.md:798` 1518→1536 (shifted) |
| A.U19.24 | `U19.md:878` 824-826→824-826; `U19.md:878` 650-651→650-651; `U19.md:878` 813-816→813-816; `U19.md:879` 217→217; `U19.md:919` 1399-1408→1417-1426 (shifted) |
| A.U30.19 | `U30.md:644` 1515-1545→1533-1563 (shifted); `U30.md:645` 1540-1543→1558-1561 (shifted); `U30.md:660` 1515-1545→1533-1563 (shifted) |
| A.U34.12 | `U34.md:409` 15-20→15-20; `U34.md:415` 16-18→16-18 |
| A.U36.030 | `U36a.md:763` 16-18→16-18 |
| A.U36.544 | `U36b.md:2072` 1397-1408→1415-1426 (shifted) |
| A.U36.548 | `U36b.md:2385` 190-192→190-192; `U36b.md:2389` 884-889→884-889 |
| A.U8.23 | `U8.md:211` 359→359; `U8.md:211` 360-363→360-363; `U8.md:212` 61-62→61-62 |
| M.DOCS.075 | `M_DOCS.md:1898` 116-118→116-118; `M_DOCS.md:1901` 110-111→110-111 |
| M.SPEC.005 | `M_SPEC.md:195` 64→64; `M_SPEC.md:196` 85→85; `M_SPEC.md:197` 81-82→81-82 |
| M.SPEC.107 | `M_SPEC.md:4007` 691→691 |
| M.SRC_NET.118 | `M_SRC_NET.md:2080` 56-61→56-61; `M_SRC_NET.md:2110` 56-61→56-61; `M_SRC_NET.md:2110` 689-703→689-703; `M_SRC_NET.md:2113` 256-258→256-258 |
| M.SRC_NET.124 | `M_SRC_NET.md:2323` 567→567; `M_SRC_NET.md:2323` 746→746 |

`v2.6.2` literals per action: A.SDEP.25 (8), A.SDEP.06 (6), A.U34.12 (5), A.U8.23 (4), M.SPEC.018 (3), A.SDEP.23 (2), A.SDEP.24 (2), U19.md (2), A.U19.18 (2), A.U8C.121 (2), M.DOCS.041 (2), M.PROC.013 (2), SUPP_deps.md (1), A.SDEP.18 (1), A.U0.03 (1), A.U0.60 (1), A.U18.43 (1), A.U27.07 (1), U36a.md (1), A.U36.030 (1), A.U36.046 (1), A.U36.544 (1), M.DOCS.002 (1), M.DOCS.108 (1), M.GEN.051 (1), M.PROC.004 (1), M.SPEC.005 (1), M.SPEC.043 (1), M.SPEC.132 (1), M.SRC_CORE.071 (1), M.SRC_NET.104 (1), M.SRC_NET.111 (1), M.SRC_NET.124 (1), M.TEST_UNIT.295 (1), M.TSC.154 (1).
