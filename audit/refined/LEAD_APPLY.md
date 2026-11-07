# Lead cross-file placements (refined harvest)

| RF | from | target | applied / not applied — reason |
|---|---|---|---|
| RF062 | I1 | G9/R12 | applied — State, Sources, Pass 2 |
| RF135 | I1 | G5/R19 | applied — State, Sources, Pass 2 |
| RF101 | I1 | G7/R09 | applied — State, Sources, Pass 2 |
| RF278 | I1 | G3/R13 | applied — State, Sources, Pass 2 |
| RF316 | I5 | G5/R59 | applied — State, Sources, Pass 2 |
| RF078 | I6 | G8/R01 | applied — State, Sources, Pass 2 |
| RF013 | I7 (restore) | G6/R34 | applied — Req, Rank (owner tag `a6abe13`, 2026-07-28; rank stays owner/agent as given), Sources, Pass 2 |
| RF014 | I7 (restore) | G4/R54 | applied — Req, Rank (owner, 2026-07-28, `5ddbcd3`), State (rule in U8), Sources, Pass 2 |
| RF015 | I7 (restore) | G2/R16 | applied — Rank (owner, 2026-07-27, `dd22d43`), Sources, Pass 2 |
| RF018 | I7 | G9/R33 | applied — State, Sources, Pass 2; the routing it names to G6/R28 and G6/R24 is recorded in G9/R33 only (no register text given for those blocks) |
| RF020 | I7 | G7/R30 | applied — State, Sources, Pass 2 |
| RF021 | I7 | G2/R13 | applied — State, Sources, Pass 2 |
| RF023 | I7 | G9/R33 | applied — State (prefixed "history trace in U0", matching RF018), Sources, Pass 2 |
| RF035 | I7 (restore) | G1/R06 | applied — State (owner direction quoted, dropped by `3da4e17`, 2026-09-09), Sources, Pass 2 |
| RF038 | I7 (restore) | G9/R18 | applied — State, Sources, Pass 2 |
| RF040 | I7 (restore) | G5/R18 | applied — State (prefixed "rule in U36", the block's existing D.2 unit), Sources, Pass 2 |
| RF048 | I7 (restore) | G5/R54 | applied — State (prefixed "code in U35", the block's per-line-verdict unit), Sources, Pass 2 |
| RF150 | I7 | G8/R47 | applied — State, Sources, Pass 2 |
| RF182 | I7 | G6/R40; G3/R66 | applied — G6/R40 State; G3/R66 State "holds" → "work: verdict in U5 under OR46.b's scope (G6/R40)"; Sources and Pass 2 on both. G3/R63 not edited: the ledger names it ("late `set_ext_led()` follows") but gives no register text |
| RF185 | I7 | G5/R19 | applied — State, Sources, Pass 2 (sits beside RF169's U2 entry on the same wrnno 10, no contradiction) |
| RF258 | I7 | G4/R41 | applied — State, Sources, Pass 2 |
| RF275 | I7 | G4/R54 | applied — State, Sources, Pass 2 |
| RF331 | I7 | G7/R32 | applied — State, Sources, Pass 2 |
| RF351 | I7 | G7/R29 | applied — State, Sources, Pass 2 |
| RF027 | I7 (question) | G6/R49 | applied — Req correction (OpenHAB case back to 2 + 2 = 4, `5d47a8b`, 2026-08-25), State open question, Sources, Pass 2 |
| RF029 | I7 (question) | G5/R25 | applied — Rank correction ("(agent)" → owner-confirmed tag found, open — owner question; no rank upgrade), State (doc in U16), Sources, Pass 2 |
| RF043 | I7 (question) | G4/R43 | applied — Rank add (owner claim unverified, open — owner question), Sources, Pass 2 |
| RF343 | I7 (question) | G3/R22 | applied — State open question, Sources, Pass 2 |
| RF348 | I7 (question) | G7/R41 | applied — State open question, Sources, Pass 2 |
| RF349 | I7 (question) | G7/R41 | applied — State open question, Sources, Pass 2 |

Notes: State additions whose ledger text carried no RF tag got "(RFnnn)" appended, as in the target blocks. Not applied: none. `pass2_check.py`: no missing IDs, no duplicate requirement IDs (535 requirements in 12 files); `pass2_index.py` regenerated `audit/pass2/INDEX.md` (535 written, 529 live), missing OR none.
