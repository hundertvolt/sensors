# Seam review: fold parts citing a later-landing M entry (2026-10-06)

Worktree `wt-fold` (branch audit/sf-fold), uncommitted. Input: `scan/seamcheck.out` (129 cases from `scan/seamcheck.py`). Verdicts: a = MENTION (no edit), b = STAGE-OK (the referenced part lands at or before the citing part; missing explicit stage words added), c = NEEDS-STAGE (citing part moved later). Edits touch only fold parts labelled "(A-C fold, silent-failure scan ...)"; no Unit or Depends slot was changed.

## 1. The 129 cases

`citing (part) -> REF | verdict | reason | edit made`

- `M.SRC_NET.023 (1) -> M.GEN.034` | a | numbering at execution with the catalog as the numbering source; GEN.034's standing rule lands each row with its constant | none
- `M.SRC_NET.028 (1) -> M.SRC_NET.027` | b | .027 (1) is the U18 stage of its U31 entry; .028 (1) lands U18 | .027 (1): "(U18 stage)" -> "Stage U18." after the header
- `M.SRC_NET.030 (1) -> M.SRC_NET.027` | b | .030 (1) said "Lands in the U18 stage" (entry completes U28); .027 (1) U18 | .030 (1) -> "Stage U18."; .027 (1) as above
- `M.SRC_NET.077 (1) -> M.GEN.034` | a | numbering at execution with the catalog as the numbering source; GEN.034's standing rule lands each row with its constant | .077 (1) "All land in the U18 stage" -> "All land in Stage U18"
- `M.SRC_NET.078 (1) -> M.SRC_NET.087` | b | .087 (1) is "U18 stage" of its U31 entry; .078 (1) lands U18 | .087 (1), .078 (1) "U18 stage." -> "Stage U18."
- `M.SRC_NET.119 (1) -> M.SRC_NET.125` | a | the execution check reads HEAD's catch-all handler, which already persists the exception (src/asy_webserver_service.py:671-676); .125 changes it later | none
- `M.SRC_NET.221 (7) -> M.HW_DEV.160` | a | pointer to the phase-C bench case | none
- `M.HW_BENCH.071 (1) -> M.SPEC.097` | a | the test records at phase C; SPEC.097 (v) writes the row "owed" in its Stage 3 U31 and fills it at phase C | none
- `M.HW_BENCH.130 (1) -> M.HW_DEV.160` | b | the citing part lands U26 by its own trailing "U26." (Unit slot U4/U7/U26, no completing unit; the crude script took U4); HW_DEV.160 (5) U26 | HW_BENCH.130 (1) "U26." -> "Stage U26."
- `M.HW_BENCH.130 (1) -> M.HW_BENCH.082` | b | same; HW_BENCH.082 (4) U26 | as above
- `M.HW_BENCH.130 (1) -> M.HW_BENCH.102` | b | same; HW_BENCH.102 (6) is the entry's stage 2 U26 | as above; HW_BENCH.102 (6) "Stage U26." added
- `M.HW_BENCH.131 (1) -> M.HW_DEV.160` | b | the citing part lands U26 by its own trailing "U26." (Unit slot U0..U36 with no completing unit; crude script took U0); HW_DEV.160 (4) U26 | HW_BENCH.131 (1) "U26." -> "Stage U26."
- `M.HW_BENCH.131 (1) -> M.HW_DEV.132` | b | same; HW_DEV.132 (1) U26 | as above
- `M.HW_BENCH.131 (1) -> M.HW_BENCH.083` | b | same; HW_BENCH.083 (3) U26 | as above
- `M.HW_BENCH.131 (1) -> M.HW_BENCH.082` | b | same; HW_BENCH.082 (4) U26 | as above
- `M.HW_BENCH.131 (1) -> M.HW_BENCH.102` | b | same; HW_BENCH.102 (6), (7) stage 2 U26 | as above; HW_BENCH.102 (6), (7) "Stage U26." added
- `M.HW_BENCH.131 (1) -> M.HW_BENCH.101` | b | same; HW_BENCH.101 (6) U26 | as above
- `M.HW_BENCH.131 (1) -> M.HW_DEV.156` | b | same; HW_DEV.156 (1) phase C in U26 form | as above
- `M.TEST_HELP.013 (1) -> M.SRC_SENS.012` | b | both parts say stage U13 (the crude script takes max(stage, entry unit) = U24) | none
- `M.TEST_HELP.015 (1) -> M.SRC_SENS.011` | b | both stage U13 | none
- `M.TEST_HELP.026 (11) -> M.SRC_SENS.048` | b | SRC_SENS.048 (1) placed in U15: the device-session stage, where all five tests pinning it (TEST_HELP.026 (11), TWIN.010 (1), TWIN.100 (1), TEST_UNIT.010 (1), TEST_UNIT.234 (1)) already put the burst move; HEAD's 6-byte burst read exists, so U30's buffer is not needed | SRC_SENS.048 (1): "Stage U15, with the device session (...)" added
- `M.TEST_HELP.041 (8) -> M.SRC_SENS.037` | b | the State claim is the part's U22 claim; SRC_SENS.037 (1) placed in U22 with .035 (2) and its tests (TEST_UNIT.088 (1), SPEC.014 (1)) | TEST_HELP.041 (8) per-claim "(U20)/(U19)/(U22)" -> "(Stage U20)/(Stage U19)/(Stage U22)"; SRC_SENS.037 (1) "Stage U22, with M.SRC_SENS.035 (2)." added
- `M.TEST_HELP.041 (8) -> M.GEN.008` | b | GEN.008 (1), (2) are Stage U20, the part's U20 claim | as above
- `M.TWIN.010 (1) -> M.SRC_SENS.048` | b | both stage U15 once SRC_SENS.048 (1) is U15 | SRC_SENS.048 (1) (see above)
- `M.TWIN.024 (1) -> M.SRC_SENS.012` | b | both stage U13 | none
- `M.TWIN.100 (1) -> M.SRC_SENS.048` | b | both stage U15 | SRC_SENS.048 (1)
- `M.TWIN.116 (1) -> M.SRC_SENS.043` | b | SRC_SENS.043 (1) placed in U15 (with .048 (1), .044's re-apply helper and its unit pin TEST_UNIT.017 (1)); the twin case at U25 follows it | SRC_SENS.043 (1) "Stage U15, with M.SRC_SENS.048 (1)." added
- `M.TWIN.126 (1) -> M.SRC_SENS.012` | b | both stage U13 | none
- `M.TWIN.102 (1) -> M.SRC_SENS.012` | b | per-claim stages U13/U15/U16; SRC_SENS.012 (1) stage U13 | TWIN.102 (1) "(U13:"/"(U15:"/"(U16)" -> "(Stage U13:"/"(Stage U15:"/"(Stage U16)"
- `M.SRC_CORE.005 (1) -> M.GEN.034` | a | numbering at execution with the catalog as the numbering source; GEN.034's standing rule lands each row with its constant | SRC_CORE.005 (1) "Stage U11, with M.SRC_CORE.017 (1)." added (multi-stage entry)
- `M.SRC_CORE.005 (1) -> M.SRC_CORE.017` | b | the part already said it lands in U11 with its user (Unit slot U2/U3/U10/U30, no completing unit; crude script took U2); .017 (1) U11 | as above
- `M.SRC_CORE.006 (1) -> M.GEN.008` | a | the getter lands at U13; the /status key is GEN.008 (2), Stage U20 — a pointer | none
- `M.SRC_CORE.006 (1) -> M.GEN.001` | a | SCRATCH4/WDT() fact already true of HEAD's boot entry | none
- `M.SRC_CORE.006 (2) -> M.GEN.034` | a | numbering source; the RR 21 row lands Stage U20 in GEN.034 (1) | GEN.034 (1) per-row stages made explicit (U16, U16, U11, U20, U11)
- `M.SRC_CORE.008 (1) -> M.SRC_CORE.013` | b | .008 (1) said "U11 stage" (Unit slot stages U5/U10/U11/U32/U20); .013 (1) U11 | SRC_CORE.008 (1) "U11 stage." -> "Stage U11."
- `M.SRC_CORE.008 (1) -> M.SRC_CORE.012` | b | same; .012 (1) U11 | as above
- `M.SRC_CORE.013 (1) -> M.SRC_NET.054` | a | contrast pointer to NTP's behaviour | none
- `M.SRC_CORE.015 (1) -> M.GEN.008` | b | GEN.008 (1) is Stage U20, with .015 (1) | none
- `M.SRC_CORE.017 (1) -> M.SCR.049` | a | keeps the twin's clean first boot; no dependency on SCR.049's U35 change | none
- `M.SRC_CORE.017 (1) -> M.SRC_CORE.065` | b | SRC_CORE.065 (2) is explicitly "Stage U11 on HEAD's setup()" | none
- `M.SRC_CORE.017 (2) -> M.SRC_CORE.038` | a | SYSTEM builds its own marker dict; the same shape is a mirror; pinned at U11 by TEST_UNIT.311 (2), and SPEC.057 (1) places the SYSTEM half in U11 | none
- `M.SRC_CORE.038 (1) -> M.SRC_NET.123` | a | the /status marker is already sent at HEAD (src/asy_webserver_service.py:618, 627) | none
- `M.SRC_CORE.038 (1) -> M.WEB.001` | a | the page reader is described; the firmware change needs nothing from it | none
- `M.SRC_CORE.044 (1) -> M.SRC_CORE.015` | a | the flag stands alone at U11; its reporters land in U20, and the part itself lets U11's check cancel them | none
- `M.SRC_CORE.044 (1) -> M.GEN.008` | a | same | none
- `M.SRC_CORE.044 (1) -> M.GEN.014` | a | same | none
- `M.SRC_CORE.043 (2) -> M.SRC_CORE.015` | a | same (.043 (2) sets the U11 flag; reporting in U20) | none
- `M.SRC_CORE.043 (3) -> M.SCR.049` | a | keeps the twin's clean first boot | none
- `M.SRC_CORE.063 (2) -> M.WEB.001` | a | no behaviour change; pointer to the page's mirror | none
- `M.SRC_CORE.063 (2) -> M.WEB.016` | a | same | none
- `M.SRC_CORE.065 (1) -> M.GEN.034` | a | numbering at execution with the catalog as the numbering source; GEN.034's standing rule lands each row with its constant; FRAM_FULL/LOG_RAM_ONLY rows Stage U16 in GEN.034 (1) | GEN.034 (1) (above)
- `M.SRC_CORE.092 (1) -> M.GEN.034` | a | numbering at execution with the catalog as the numbering source; GEN.034's standing rule lands each row with its constant | none
- `M.TSC.092 (1) -> M.TEST_HELP.036` | b | TEST_HELP.036's owner list (its main (1)) is staged in U16 by its Unit slot | none
- `M.TSC.111 (1) -> M.SRC_SENS.043` | b | SRC_SENS.043 (1), (2) placed in U15 with SRC_SENS.055 (1), (2) | SRC_SENS.043 (1), (2) Stage U15 added
- `M.TSC.147 (1) -> M.SRC_SENS.025` | a | no new check; the U8 tag/Part N check covers each tag in its own landing | SRC_SENS.025 (1) "Stage U22 (...)" added (multi-stage entry)
- `M.HW_DEV.160 (5) -> M.SPEC.097` | a | the row is filled at phase C | none
- `M.HW_DEV.080 (9) -> M.HW_BENCH.064` | b | HW_BENCH.064 (1) is the entry's stage 1 U26 | HW_BENCH.064 (1) "Stage U26 (written; run in phase C)." added
- `M.HW_DEV.080 (9) -> M.SRC_SENS.011` | b | SRC_SENS.011 (1), (2) stage U13 | none
- `M.HW_DEV.090 (1) -> M.SRC_SENS.011` | b | same | none
- `M.WEB.001 (1) -> M.WEB.016` | b | WEB.016 (1) said "U23 stage" (entry completes U36) | WEB.016 (1) "U23 stage." -> "Stage U23."
- `M.WEB.058 (1) -> M.WEB.016` | b | both U23 (WEB.058 (1) says stage U23) | as above
- `M.TEST_UNIT.017 (1) -> M.SRC_SENS.043` | b | SRC_SENS.043 (1) Stage U15 | SRC_SENS.043 (1)
- `M.TEST_UNIT.017 (1) -> M.TEST_HELP.015` | b | TEST_HELP.015 (1) stage U13 | none
- `M.TEST_UNIT.017 (2) -> M.SRC_SENS.043` | b | SRC_SENS.043 (2) Stage U15 | SRC_SENS.043 (2) "Stage U15, with M.SRC_SENS.055 (2)." added
- `M.TEST_UNIT.019 (1) -> M.SRC_SENS.011` | b | both stage U13 | none
- `M.TEST_UNIT.053 (1) -> M.TEST_UNIT.127` | a | pointer: the existing general-call test keeps holding | none
- `M.TEST_UNIT.053 (1) -> M.TEST_HELP.013` | b | stage U13 both | none
- `M.TEST_UNIT.053 (1) -> M.SRC_SENS.012` | b | stage U13 both | none
- `M.TEST_UNIT.059 (1) -> M.SRC_SENS.011` | b | stage U13 both | none
- `M.TEST_UNIT.059 (1) -> M.TEST_HELP.015` | b | stage U13 both | none
- `M.TEST_UNIT.086 (1) -> M.SRC_SENS.035` | b | SRC_SENS.035 (2) placed in U22 (entry stage U22, with its tests) | SRC_SENS.035 (1), (2) "Stage U22." added
- `M.TEST_UNIT.087 (1) -> M.SRC_SENS.035` | b | same | as above
- `M.TEST_UNIT.087 (2) -> M.SRC_SENS.035` | b | SRC_SENS.035 (1) Stage U22 | as above
- `M.TEST_UNIT.122 (1) -> M.PROC.035` | a | owner-review list pointer (M.PROC.035) | none
- `M.TEST_UNIT.189 (1) -> M.SRC_NET.007` | b | SRC_NET.007 (1) was "Lands in the U18 stage" | SRC_NET.007 (1) -> "Stage U18."
- `M.TEST_UNIT.191 (1) -> M.SRC_NET.027` | b | SRC_NET.027/.028/.030 (1) all U18 | (.027/.030 above)
- `M.TEST_UNIT.202 (1) -> M.SRC_NET.118` | b | SRC_NET.118 (1) was "U19 stage"; .127 (1) (abbreviated, missed by the crude script) had no stage | SRC_NET.118 (1) -> "Stage U19."; SRC_NET.127 (1) "Stage U19, with M.SRC_NET.118 (1)." added
- `M.TEST_UNIT.213 (1) -> M.SRC_NET.087` | b | SRC_NET.087 (1) U18 | (above)
- `M.TEST_UNIT.216 (1) -> M.SRC_NET.081` | b | SRC_NET.081 (1) was "U18 stage" | SRC_NET.081 (1) -> "Stage U18."
- `M.TEST_UNIT.244 (1) -> M.SRC_NET.007` | b | SRC_NET.007 (1) U18 | (above)
- `M.TEST_UNIT.277 (1) -> M.SRC_SENS.034` | b | SRC_SENS.034 (1) placed in U9: its pinning tests TEST_UNIT.277 (1) and .088 (2) are U9 and it needs only SRC_SENS.027's U9 busy refusal (constructor, `_DefaultSignalSink`, `_trigger_signal` exist at HEAD); earliest unit with everything | SRC_SENS.034 (1) "Stage U9, with M.TEST_UNIT.277 (1) and .088 (2) (...)" added; SPEC.014 (2) reworded (below)
- `M.TEST_UNIT.303 (1) -> M.SRC_NET.119` | a | pointer (the value HTTPDropped's window reads) | none
- `M.SPEC.011 (5) -> M.PROC.035` | a | owner-review list pointer (M.PROC.035) | none
- `M.SPEC.013 (1) -> M.SRC_SENS.043` | b | both Stage U15 | SRC_SENS.043 (1), .048 (1)
- `M.SPEC.014 (1) -> M.SRC_SENS.037` | b | both Stage U22 | SRC_SENS.037 (1)
- `M.SPEC.014 (2) -> M.SRC_SENS.034` | b | SRC_SENS.034 (1) now U9, before the U22 SPEC sentence | SPEC.014 (2) "Stage U22, with M.SRC_SENS.034 (1)." -> "Stage U22; the code lands earlier, in U9 (M.SRC_SENS.034 (1))."
- `M.SPEC.014 (4) -> M.SRC_SENS.035` | b | SRC_SENS.035 (1) Stage U22 | SRC_SENS.035 (1)
- `M.SPEC.017 (3) -> M.SRC_NET.087` | b | SRC_NET.087 (1) Stage U18 | (above)
- `M.SPEC.018 (12) -> M.SRC_NET.119` | b | both U19; the part's "Stage U19" is wrapped across a line, which the crude regex misses | none
- `M.SPEC.018 (13) -> M.SRC_NET.118` | b | SRC_NET.118 (1) Stage U19 | (above)
- `M.SPEC.021 (10) -> M.GEN.034` | b | the marker test (TSC.088 check (11)) needs the catalog's RR 21 row in U20; GEN.034 (1) places it there | GEN.034 (1) "Stage U20" explicit
- `M.SPEC.021 (11) -> M.GEN.008` | b | GEN.008 (2) Stage U20 | none
- `M.SPEC.021 (11) -> M.GEN.014` | b | GEN.014 (2) Stage U20 | none
- `M.SPEC.021 (12) -> M.GEN.008` | b | GEN.008 (1) Stage U20 | none
- `M.SPEC.021 (14) -> M.SRC_NET.118` | b | SRC_NET.118 (1), .127 (1) Stage U19 | (above)
- `M.SPEC.049 (5) -> M.HW_BENCH.101` | a | the phase-C bench result replaces a word later | none
- `M.SPEC.057 (1) -> M.SRC_SENS.047` | b | SRC_SENS.047 (1) is Stage U19, as are .053 (1), .082 (1) | SPEC.057 (1) stale "the drivers' in U15/U30" -> "the drivers' in this same U19 stage"
- `M.SPEC.058 (12) -> M.SRC_CORE.091` | b | "Stage 7 U16" (numbered form, missed by the crude regex); SRC_CORE.091 (1) U16 | none
- `M.SPEC.059 (3) -> M.GEN.034` | a | numbering at execution with the catalog as the numbering source; GEN.034's standing rule lands each row with its constant; C.7.1 takes no rows | none
- `M.SPEC.059 (3) -> M.SRC_NET.027` | b | SRC_NET.027/.028/.030 (1) Stage U18 | (above)
- `M.SPEC.063 (1) -> M.SRC_NET.007` | b | SRC_NET.007 (1) Stage U18 | (above)
- `M.SPEC.079 (5) -> M.SCR.040` | b | "Stage 5 U27"; SCR.040 (1) lands U27 | none
- `M.SPEC.100 (1) -> M.SRC_SENS.011` | b | "Stage 1 U13"; SRC_SENS.011 (1), .012 (1) stage U13 | none
- `M.SPEC.100 (2) -> M.SRC_SENS.011` | b | same; SRC_SENS.011 (2) stage U13 | none
- `M.SPEC.100 (3) -> M.SRC_SENS.012` | b | same; SRC_SENS.012 (2) (no code) given Stage U13 | SRC_SENS.012 (2) "Stage U13, with (1)." added
- `M.SPEC.103 (2) -> M.HW_BENCH.083` | a | phase-C outcome sentence after the bench case | none
- `M.SPEC.103 (3) -> M.HW_BENCH.102` | a | same | none
- `M.SPEC.121 (12) -> M.SRC_NET.118` | b | SRC_NET.118 (1), .127 (1) Stage U19 | (above)
- `M.SPEC.137 (8) -> M.HW_DEV.160` | b | split part: its L3 half is "Stage 3c U26", with HW_DEV.160 (4) U26 | none
- `M.SPEC.156 (9) -> M.SRC_NET.077` | b | the hotspot-pair row lands with SRC_NET.077 (1), Stage U18 | SPEC.156 (9) per-row "; U15)/U22)/U22)/U18)" -> "; Stage U15)" etc.
- `M.SRC_SENS.012 (1) -> M.SRC_SENS.007` | b | SRC_SENS.007's U13 stage (import) in its Unit slot | none
- `M.SRC_SENS.034 (1) -> M.GEN.034` | a | numbering at execution with the catalog as the numbering source; GEN.034's standing rule lands each row with its constant | none
- `M.SRC_SENS.034 (1) -> M.PROC.035` | a | owner-review list pointer (M.PROC.035) | none
- `M.SRC_SENS.035 (1) -> M.SRC_SENS.031` | a | the module constants block exists at HEAD | none
- `M.SRC_SENS.035 (2) -> M.SRC_SENS.037` | b | both Stage U22 | SRC_SENS.035 (2), .037 (1)
- `M.SRC_SENS.043 (1) -> M.SRC_SENS.048` | b | both Stage U15 | SRC_SENS.043 (1), .048 (1)
- `M.SRC_SENS.043 (1) -> M.GEN.034` | a | numbering at execution with the catalog as the numbering source; GEN.034's standing rule lands each row with its constant | none
- `M.SRC_SENS.043 (2) -> M.PROC.035` | a | owner-review list pointer (M.PROC.035) | none
- `M.SRC_SENS.053 (1) -> M.WEB.001` | a | the page reader is described | none
- `M.SRC_SENS.055 (1) -> M.SRC_SENS.050` | a | the constants block exists at HEAD | none
- `M.SRC_SENS.055 (1) -> M.GEN.034` | a | numbering at execution with the catalog as the numbering source; GEN.034's standing rule lands each row with its constant | none
- `M.SRC_SENS.055 (1) -> M.PROC.035` | a | owner-review list pointer (M.PROC.035) | none
- `M.SRC_SENS.055 (2) -> M.SRC_SENS.043` | b | SRC_SENS.043 (2) Stage U15 (the shared READ_RANGE code lands once, with whichever lands first in U15) | SRC_SENS.043 (2)
- `M.SRC_SENS.055 (2) -> M.SRC_SENS.050` | a | the constants block exists at HEAD | none
- `M.SRC_SENS.055 (2) -> M.GEN.034` | a | numbering at execution with the catalog as the numbering source; GEN.034's standing rule lands each row with its constant | none
- `M.SRC_SENS.055 (2) -> M.PROC.035` | a | owner-review list pointer (M.PROC.035) | none
- `M.SRC_SENS.055 (2) -> M.SRC_SENS.057` | b | SRC_SENS.057's U15 stage (range gate) in its Unit slot | none
- `M.SRC_SENS.081 (1) -> M.GEN.034` | a | numbering at execution with the catalog as the numbering source; GEN.034's standing rule lands each row with its constant | none
- `M.SRC_SENS.082 (1) -> M.WEB.001` | a | the page reader is described | none

Counts: a (MENTION) 47, b (STAGE-OK) 82, c (NEEDS-STAGE) 0.

## 2. Cases `seamcheck.py` cannot see (found by `scan/seamcheck2.py`)

The crude script skips abbreviated references (`M.X.118 (1), .127 (1)`), the four fold parts outside the standard
`  (n) (A-C fold, silent-failure` layout (M.SRC_CORE.016 `  - (1)` under "Change (end state)", M.DOCS.064 `(f)`,
M.SPEC.097 `(iv)`, `(v)`), and the ref part's own stage. Extra cases it found, all resolved:

- `M.TEST_UNIT.202 (1) -> M.SRC_NET.127 (1)` | b | the drops/flags are .127's U19 stage; (1) had no stage and so landed in U31 | SRC_NET.127 (1) "Stage U19, with M.SRC_NET.118 (1)." added
- `M.SPEC.021 (14) -> M.SRC_NET.127 (1)`, `M.SPEC.121 (12) -> M.SRC_NET.127 (1)` | b | same | same
- `M.HW_BENCH.083 (4)`, `M.HW_DEV.025 (1)`, `M.HW_DEV.026 (1)`, `M.SPEC.093 (6)`, `M.SPEC.129 (6)`, `M.TEST_UNIT.309 (2)`, `M.TSC.108 (1)` `-> M.SRC_CORE.016 (1)` | b | .016 has no completing unit; (1) said "(U11 in start_and_check_tasks()'s start loop, carried into start_tasks() in U20)" | SRC_CORE.016 (1) -> "(Stage U11, in ...; carried into `start_tasks()` with the U20 split)"
- `M.SRC_CORE.012 (1) -> M.SRC_CORE.011 (7)`, `M.TEST_UNIT.307 (1) -> M.SRC_CORE.011 (7)` | b | .011 has no completing unit (stages U11, U16, fold U20); (7) removes the timer U11's .012 (1) removes | SRC_CORE.011 (7) "Stage U11, with M.SRC_CORE.012 (1)." added
- `M.SPEC.100 (3) -> M.SRC_SENS.012 (2)` | b | (2) is a no-code part of the U13 choke point | SRC_SENS.012 (2) "Stage U13, with (1)." added
- `M.DOCS.019 (1) -> M.DOCS.022 (1)` | b | both U13 ("Unit U13" was not a stage form) | DOCS.022 (1) "Unit U13" -> "Stage U13"; DOCS.019 (1) "U13 stage" -> "Stage U13"
- `M.TEST_UNIT.010 (1)`, `M.TEST_UNIT.234 (1) -> M.SRC_SENS.048 (1)`; `M.TEST_UNIT.234 (1) -> M.SRC_SENS.043 (1)` | b | all stage U15 | SRC_SENS.048 (1), .043 (1) (section 1)
- `M.TEST_UNIT.088 (1) -> M.SRC_SENS.037 (1)` | b | both U22 | SRC_SENS.037 (1)
- `M.TEST_UNIT.088 (2) -> M.SRC_SENS.034 (1)` | b | both U9 (this test, with TEST_UNIT.277 (1), is why .034 (1) is U9) | SRC_SENS.034 (1)
- `M.SPEC.014 (1) -> M.SRC_SENS.035 (2)` | b | both U22 | SRC_SENS.035 (2)
- `M.TSC.147 (1) -> M.SRC_SENS.035 (1)`, `-> M.SRC_SENS.064 (1)` | a | no new check; the U8 check covers each tag as it lands | none
- `M.SPEC.011 (6) -> M.HW_BENCH.131 (1)` | a | pointer (the bench cannot settle it) | none
- `M.SRC_SENS.012 (1) -> M.SRC_SENS.013` | b | .013's U13 stage (bools) | none; `-> M.SRC_SENS.069` | a | HEAD fact (`_reset()` catches `OSError`) | none
- `M.SRC_SENS.034 (1) -> M.SRC_SENS.027` | b | .027's U9 stage | none; `-> M.SRC_SENS.031`, `-> M.SRC_SENS.033` | a | HEAD block and constructor | none
- `M.SRC_SENS.043 (1)`, `(2)`, `M.SRC_SENS.048 (1) -> M.SRC_SENS.040`; `M.SRC_SENS.047 (1) -> M.WEB.001` | a | HEAD constants block; page reader described | none
- `M.TWIN.132 (1) -> M.TEST_HELP.065` | **c** | the driver case advances the overlay's wait "through the driven clock the L1 tier installs (M.TEST_HELP.065)", which is created in U35; the part said stage U25 for both cases | "stage U25." -> "stage U25 for the fake case; the driver case Stage U35, with M.TEST_HELP.065 (the driven clock; until then M.TEST_UNIT.079 (1) carries the driver half)." (U35 is TWIN.132's completing unit)

## 3. Placements decided here (the parts that had none or a contradictory one)

- **M.SRC_SENS.048 (1) -> U15** (entry completes U31; stages U2-U30). It needs `get_register_bytes` (U13) and the device session (U15); HEAD already reads a 6-byte burst under `_PT_BURST_LEN` (src/asy_bmp3xx_driver.py:54, 445), so U30's own buffer is not a prerequisite. Every test that pins it (TEST_HELP.026 (11), TWIN.010 (1), TWIN.100 (1), TEST_UNIT.010 (1), TEST_UNIT.234 (1), HW_DEV.080 (9)/.090 (1)) and SPEC.013 (1) already said U15. Left at U31 it would have landed after M.SRC_SENS.043 (1), which calls its `take_por_detected()`.
- **M.SRC_SENS.043 (1), (2) -> U15** (stages U2, U10, U12, U15, U30; no completing unit): (1) with .048 (1) and .044's `_apply_stored_config()` (U15); (2) with .055 (2), the other half of the shared `READ_RANGE` code (HEAD's range gate exists, src/asy_bmp3xx_driver.py:487).
- **M.SRC_SENS.034 (1) -> U9** (stages U2, U10, U30, U31; no completing unit). Its two pinning tests say U9 (TEST_UNIT.277 (1), .088 (2)) while SPEC.014 (2) said "Stage U22, with" it. U9 is the earliest unit with everything it needs (.027's U9 busy refusal; HEAD has `_DefaultSignalSink`, `_trigger_signal`, the constructor). SPEC.014 (2) reworded; DOCS.027 (3)'s "(the code lands in U18/U22)" -> "U9/U18/U22".
- **M.SRC_SENS.035 (1), (2), .037 (1), .025 (1) -> U22** (the notification/overlay unit; .035 and .025 list U22 as a stage, .037 does not), matching SPEC.014 (1), (3), (4), TEST_UNIT.079 (1), .086 (1), .087 (1)-(2), .088 (1), TEST_HELP.041 (8)'s State claim and SPEC.156 (9)'s rows.
- **M.SRC_CORE.017 (2) stays U11** (verdict a): self-contained, pinned at U11 by TEST_UNIT.311 (2), and SPEC.057 (1) places the SYSTEM half there. SPEC.057 (1)'s other parenthetical, "the drivers' in U15/U30", contradicted the drivers' own parts (all "Stage U19, with M.SRC_CORE.038 (1)") and now reads "in this same U19 stage".
- **M.SPEC.021 (15), (16) -> U36**: "Lands with item 3/5" named no unit; the `BootSignature` and `mempause` sentences they extend exist only in SPEC.021's own main change (not in SPECIFICATION.md at HEAD), whose whole section is its Stage 2 U36.

## 4. Fold parts in multi-stage entries given an explicit stage

Entries whose Unit slot names no single completing unit, or parts whose stage word was in a form the checkers did not read:

- M.SRC_CORE.005 (1) Stage U11 (was "lands in U11 with that user"); M.SRC_CORE.008 (1) Stage U11 (was "U11 stage"); M.SRC_CORE.011 (7) Stage U11 (new); M.SRC_CORE.016 (1) Stage U11 (was "(U11 in ...)")
- M.SRC_SENS.012 (2) Stage U13; .025 (1) Stage U22; .034 (1) Stage U9; .035 (1), (2) Stage U22; .037 (1) Stage U22; .043 (1), (2) Stage U15 (all new); .048 (1) Stage U15 (new; entry completes U31)
- M.SRC_NET.007 (1), .030 (1) "Lands in the U18 stage" -> Stage U18; .027 (1) "(U18 stage)" -> Stage U18; .077 (1) "All land in the U18 stage" -> "All land in Stage U18"; .078 (1), .081 (1), .087 (1), .089 (1) "U18 stage" -> Stage U18; .118 (1) "U19 stage" -> Stage U19; .127 (1) Stage U19 (new)
- M.HW_BENCH.064 (1) Stage U26 (new); .102 (5), (6), (7) Stage U26 (new); .125 (1), .127 (1), (2), .130 (1), .131 (1) trailing "U26" -> Stage U26
- M.GEN.034 (1): per-row "Stage U16" (FRAM_FULL, LOG_RAM_ONLY), "Stage U11" (CONFIG_LOST, the E17 TIMER site), "Stage U20" (ResetReason 21)
- M.DOCS.019 (1), .022 (1) Stage U13; M.DOCS.024 (1) Stage U11 (was "U11, with"); M.DOCS.027 (3) Stage U36
- M.SPEC.021 (15), (16) Stage U36; M.SPEC.136 (9) Stage U17 (was "Lands with (2) (U17)"); M.SPEC.156 (9) per-row Stage U15/U22/U22/U18
- M.TEST_HELP.041 (8) per-claim (Stage U20)/(Stage U19)/(Stage U22); M.TWIN.102 (1) per-claim Stage U13/U15/U16; M.TWIN.132 (1) driver case Stage U35
- M.WEB.016 (1) "U23 stage" -> Stage U23

After the edits, `scan/seam/msweep.py` finds no fold part in such an entry without a stage word, except M.HW_DEV.154 (5), .156 (1), (2), whose Unit slot is one landing ("phase C (U26 form)") and whose parts say "phase C".
Backup of the pre-edit M files: `scan/seam/backup/`; every edit: `scan/seam/edits.json` (58).

## 5. Check results

- `python3 scan/seamcheck.py`: 321 parts, 116 lines (was 129). Remaining = the 47 a cases plus 69 b cases. It cannot clear a b case: it compares the citing part with the *entry's* computed unit of the reference, never the referenced part's stage, takes max(stage word, entry unit) so a stage earlier than the entry's unit (stage U13 in a U24 entry) still reads as the entry's unit, and misses "Stage\nU19" wrapped across a line, "Stage 7 U16" and "Uxx stage".
- `python3 scan/seamcheck2.py scan/seam/allow.txt` (refined: wrapped and numbered stage words, "Uxx stage", abbreviated refs, the four non-standard parts, the ref part's own stage): 328 parts, 61 lines, every one reviewed: 53 a, 8 b resting on a main-change stage in the referenced entry's Unit slot (no fold part to mark), listed in `scan/seam/allow.txt`.
- `python3 audit/sweeps/ac_order.py --write`: violations_remaining 0, unknown_action_refs 1, changes 1909, steps 6571 (as expected); WORK_ORDER.md unchanged.

## 6. Unresolved, for the lead

1. **Helpers used before they exist** (no M-ID cited, so neither checker sees it): `src_const()` (M.TEST_HELP.044, U24) in TEST_UNIT.079 (1) U22, .087 (2) U22, .130 (1) U15, .189 (1) U18, .213 (1) U18, .310 (2) U20; `record_prints()` (M.TEST_HELP.050, U24) in TEST_UNIT.191 (1) U18, .223 (1) U16, .290 (1) U11, .309 (2) U11; the driven clock (M.TEST_HELP.065, U35) in TEST_UNIT.079 (1) U22, .088 (1) U22, .307 (1) U11 (TEST_UNIT.303's entry already carries the "HEAD form until U35" rule; .161's the same for `src_const`). Needs one rule (HEAD-form local double until the helper's unit, as M.TEST_UNIT.161/.303) or per-part stages; not edited.
2. **48 fold parts name a stage their entry's Unit slot does not list** (`scan/seam/unitgap.out`), so `ac_order.py`, which reads only Unit slots, schedules no step for that entry in that unit; e.g. TEST_HELP.013 (1)/.015 (1) and TWIN.024 (1)/.126 (1) at U13 and TWIN.010 (1)/.100 (1) at U15 sit before their entries' only unit (U24/U25). Two are new from this review (SRC_SENS.034 (1) U9, SRC_SENS.037 (1) U22); the rest were written that way by the fold. Unit slots were out of scope here.
3. M.SRC_SENS.050 (1) carries a third label, "(A-C fold, register row ... (refresh family (g), no SF number))", in an entry with no completing unit; it is a no-change part, so it was left unstaged.
