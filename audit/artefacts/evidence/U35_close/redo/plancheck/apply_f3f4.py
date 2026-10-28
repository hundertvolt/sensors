"""Applies the verified F3/F4 falsification corrections to PLAN.md; every old text must occur exactly once."""
import sys

P = "/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35r/plan/PLAN.md"
t = open(P, encoding="utf-8").read()
E = []


def r(old, new):
    E.append((old, new))


# F3.7, F4.27: six clarifications
r("""  Four clarifications are asked later, each at the start of the batch it affects (section 7).""",
  """  Six clarifications are asked later, each at the start of the batch or checkpoint it affects (section 7).""")
# F3.10
r("""  its messages carry lane names, which no pushed text outside the evidence folder may. Its messages and changed files
  are kept in the evidence folder (`redo/int_history.txt.gz`).""",
  """  its messages carry lane names, which the redo keeps out of pushed commit messages (a practice of the redo, not an
  owner rule; ten earlier pushed subjects carry them). Its messages and changed files are kept in the evidence folder
  (`redo/int_history.txt.gz`).""")
# F3.11
r("""- CI on snapshots 16 and 17 was red only on `test_twin_record`'s two checks. All MicroPython tests pass at both GC
  stages.""",
  """- CI on snapshots 16-18 was red only on `test_twin_record`'s two checks. All 6,058 unit-tier MicroPython tests pass at
  both GC stages. The 24 twin end-to-end jobs and the coverage job are success-gated behind the red unit jobs and have
  not run in CI since 2026-10-21 (run 39665515089 on `49fde7b5`, green, 27 minutes).""")
# F3.13, F3.14, F3.15, F3.17, F3.20, units
r("""| free flash in the dev image | 107 KB (U0 baseline) | about 43 KB |
| `src/` bytecode | 164,566 B | 211,648 B (+29 %) |
| firmware lines changed | | about 3,900, of which about 1,640 are in doubt, plus about 230 newly in doubt (SCAN2) |""",
  """| free flash in the dev image | 107 KiB (U0 baseline) | about 42 KiB (a lane build of 2026-10-26; R0 re-measures it) |
| `src/` bytecode (bare source names) | 161,626 B | 208,708 B (+47,082 B, +29 %) |
| firmware lines in behavioural changes (`REPORT.md` 2's rows) | | about 3,900, of which about 1,640 are in doubt, plus about 230 newly in doubt (SCAN2); in git, 11,726 lines added in `src/`, net +2,649 |""")
r("""| CI unit-tier timeout | 45 min | 175 min, for a warm run of 9-10 min |""",
  """| CI unit-tier timeout | 45 min | 175 min, for a warm run of about 12 min (9-10 min on 2026-10-20) |""")
r("""| SPECIFICATION.md | 514 KB | 1,573 KB, of which 562 KB is the tunables register |
| `audit/` | | 14,052 files, 127 MB |""",
  """| SPECIFICATION.md | 514 KiB | 1,573 KiB, of which 562 KiB is the tunables register |
| `audit/` | | 14,052 files, 127 MiB at `497b3eda` (14,347 files, 131 MiB at the pushed head) |""")
# F3.21
r("""- 17 confirmed gaps in the pre-audit code, each closable in 1-14 lines (`REPORT.md` 3).""",
  """- 17 confirmed gaps in the pre-audit code, most closable in 1-14 lines (CRC32 about 22; the lwIP listener close a
  toolchain patch) (`REPORT.md` 3).""")
# F3.23
r("""- The removal closure: every dependent site of each root that goes, 2,131 rows (`scan2/G4_closure.tsv`,
  `G4b_closure.tsv`). It loses""",
  """- The removal closure: every dependent site of each root that goes, 2,129 rows from 173 roots
  (`scan2/G4_closure.tsv`, `G4b_closure.tsv`). It loses""")
# F3.38
r("""- The open findings list: 260 rows, about 80 of them open or partly closed.""",
  """- The open findings list (`audit/sweeps/open_findings.md`): 260 rows, 73 of them open or partly closed.""")
# F3.35, F4.77: the runner stays
r("""- **The twin record goes** (2.4), so that CI is green from the start: `tests_hardware/twin_record.json`,
  `tests_scripts/test_twin_record.py` and `scripts/record_twin_instrument_runs.py` (about 1,835 lines), with their
  references in BACKLOG.md, HEAP_FRAGMENTATION_MEASUREMENTS.md, `digital_twin/README.md`,
  `digital_twin/run_device_script.py`, `pyproject.toml`, `tests_hardware/README.md` and Part N.
  `tests_hardware/twin_board.py`, which runs the hardware tests on the twin (`--twin`), stays with its test.""",
  """- **The twin record's committed copy goes** (2.4): `tests_hardware/twin_record.json` and its staleness test
  `tests_scripts/test_twin_record.py` (about 1,600 lines), with their references in BACKLOG.md,
  HEAP_FRAGMENTATION_MEASUREMENTS.md, `digital_twin/README.md`, `digital_twin/run_device_script.py`, `pyproject.toml`,
  `tests_hardware/README.md` and Part N. The runner `scripts/record_twin_instrument_runs.py` stays: it is the committed
  runner of the owner's `twin-first-for-instruments` "ok" and the only path to the twin hardware run at 32768. R3 runs
  it once on the final tree at both stages and commits the record and its test again, exceptions listed. The record's
  exception reasons (about 36) become the first knowledge-list lines before the copy goes. `twin_board.py` and `--twin`
  stay.""")
# F3.36, F4.19
r("""- **DECREV 9's three checks** run before B1: the logger-side C-stack check at a near-exhausted C stack, a Unix-port run
  (item 3; its board half is REPORT 7's item 1, not run, 3.2); the three BR2 fixes, read at the parent of `7008730e`
  against v1.29.0 (item 5); and the 2026-10-07 proposal behind the exception-handler guard (item 6). Each decides its
  batch item before the batch starts.""",
  """- **DECREV 9's three checks** run before B1: the logger-side C-stack check at a near-exhausted C stack, a Unix-port run
  (item 3; this half decides B1's form, and its board half, REPORT 7's item 1, checks that form in round 1); the three
  BR2 fixes, read at the parent of `7008730e` against v1.29.0 (item 5); and the 2026-10-07 proposal behind the
  exception-handler guard (item 6). Each decides its batch item before the batch starts.""")
# F3.14 baseline method, F3.39 first full CI run
r("""- **The baseline numbers** are recorded as the "before" column: per-module lines and bytecode against `25caf528`, the
  image size and free flash per device, test and tool lines, CI time per job.""",
  """- **The baseline numbers** are recorded as the "before" column: per-module lines and bytecode against `25caf528`
  (compiled with `-s`, bare source names), the image size and free flash per device, test and tool lines, CI time per
  job.
- **The first full CI run** after R0 is the first run of the 24 twin jobs and the coverage job since 2026-10-21. Its
  result is part of R0's close: a red job is root-caused in R0, and its fix goes to the batch that owns the code.""")
# F3.38
r("""- **The section 4 rules** go into the lead's checklist. The knowledge list and the findings list start empty.""",
  """- **The section 4 rules** go into the lead's checklist. A new findings list (4.2) starts empty; the knowledge list
  starts with the twin record's exception reasons. `audit/sweeps/open_findings.md` keeps its 73 open or partly closed
  rows, as input to R1's ledgers and as R5's OR5.a list.""")
# F3.39
r("""- **Retired first, in R0:** the twin record (2.2, about 1,835 lines; `twin_board.py` and `--twin` stay). It is audit
  machinery and the only red in CI. With it gone, every later push is judged on green CI.""",
  """- **Retired first, in R0:** the twin record's committed copy and its staleness test (2.2, about 1,600 lines; the
  runner, `twin_board.py` and `--twin` stay). The copy is the only red in CI; with it gone the whole CI runs again, and
  the first run after R0 shows whether every later push starts from green (2.2).""")
# F3.41
r("""  - it is a tool test covered by an owner row (OR23.a's build chain, `setup_toolchain.py` and
    `micropython_overrides.py` included; OR15.a's summary block; the repo scanner's own tests, which test the reader
    the owner's comment-cap gate runs on): kept, slimmed where it repeats itself;""",
  """  - it is a tool test covered by an owner row or an owner word in the rulings file (OR23.a's build chain,
    `setup_toolchain.py` and `micropython_overrides.py` included; OR15.a's summary block; the CI apt mirror check and
    cache, 2026-10-27; the repo scanner's own tests, which test the reader the owner's comment-cap gate runs on): kept,
    slimmed where it repeats itself;""")
# F3.43
r("""  - it is audit machinery born in the audit (the bite self-tests of the tests, which OR21.a (2) did not adopt; the
    files that pin SPECIFICATION.md tables, about 1,700 lines, each classified with its owner basis checked, since the
    UART changelog rule and Part N's OR30.a scope are owner rows): removed;""",
  """  - it is audit machinery born in the audit (the bite self-tests of the tests, which OR21.a (2) did not adopt):
    removed;
  - the eight files that pin SPECIFICATION.md tables (about 1,700 lines) are classified one by one by what they check:
    those that check a product property through the table (lock order, run-phase allocation, task inventory, timing
    bounds) or carry an owner row (OR30.a (2)'s tunables check, the owner-signed A.11, OR23.a's key table, OR45's
    levels) fall under the first two classes, and only their restatement of the table is slimmed;""")
# F3.53
r("""  - not included: the about 860 rows for numbers inside test bodies;""",
  """  - not included: the rows for numbers inside test bodies (about 860 by the plan's count; R2's checkpoint list states
    the split from the hardware-tier budgets row by row before the cut);""")
# F3.55
r("""  OR21.a, OR25.a) are met in R3 on the final tree.""",
  """  OR21.a, OR25.a) are met in R3 on the final tree. LD+CM3's patch also holds two L2 load tests that OR49.a (1) names
  (the full soft-callback queue, the DNS flood at the hotspot); R3's OR49.a takes them from the patch.""")
# F3.58
r("""  - the twin record re-record falls away with the record;""",
  """  - the twin record re-record becomes R3's one runner run on the final tree (2.2);
  - the twin CI on the integration head becomes R1's twin done-criterion and the first full CI run after R0;""")
# F4.6
r("""- **OR19.a.** Every test reviewed. An unchanged test keeps the verdict it already has in `review.md`, matched by name
  and body, not line. Changed and new tests are reviewed fresh.""",
  """- **OR19.a.** Every test reviewed. A test keeps the verdict it already has in `review.md` only where neither it nor the
  code it targets changed in R1 or R2 (decision 4), matched by name and body, not line. Others are reviewed fresh.""")
r("""| R3, OR19.a: verdicts carry over by name and body; changed and new tests reviewed |""",
  """| R3, OR19.a: verdicts carry over where neither the test nor its target changed; the rest reviewed |""")
# F4.77
r("""- **OR21.a.** Each check-style test whose subject changed is triggered once. No new permanent control arms.""",
  """- **OR21.a and OR29.a (4).** Each check-style test whose subject changed is triggered once. No new permanent control
  arms. The twin runner runs every device script and hardware test once at both GC stages on the final tree, and the
  record and its test are committed again with the exceptions listed (the owner's `twin-first-for-instruments`).""")
# F4.10
r("""- **OR37.a and OR38.a.** One pass over the tests changed since the audit start, for harmful constructs, races and
  hygiene.""",
  """- **OR37.a and OR38.a.** One pass over the tests, scripts, runners, tools and `src/` modules changed since the audit
  start, for harmful constructs, races, leaked resources and hygiene.""")
# F4.11
r("""- **OR39.a and OR40.a.** Speed and footprint are measured. Both GC stages run in every tier that runs MicroPython
  (this exists).""",
  """- **OR39.a and OR40.a.** Speed and footprint are measured. Both GC stages run in the unit and twin tiers (this
  exists); the hardware tiers by OR40.a (3).""")
# F4.78
r("""  defect counts only with a reproduction.""",
  """  defect counts only with a reproduction.
- **U35's 37 and 52.** The normal situations that accept a logged code (the owner's 2026-09-12 startup-jitter rule), and
  every recovery rung that stays, tested at every level that can reach it (OR113.a (2)).""")
# F4.17
r("""**R3 is done when:** every group-B3 owner row (`PROJECT_AUDIT_PLAN.md` 3.2) has its outcome on the final tree (met and
where, or one stated limit for the owner), and round 1 is fully prepared.""",
  """**R3 is done when:** every group-B3 owner row (`audit/CONSOLIDATION.md` 2, with section 4's B3 additions OR20/OR36,
OR45, OR55 and OR77/OR79) has its outcome on the final tree (met and where, or one stated limit for the owner), and
round 1 is fully prepared.""")
# F4.18, F4.19, F4.74
r("""- `REPORT.md` 7's items 3, 4, 5, 7, 8 and 10, with the optional 12;
- item 11, the owner's owed rows (the DMA ring proof, reset reasons 21, 22 and 10+phase, the first unfed watchdog
  stretch, dev's receive-ring peak);
- the FRAM log's W29 history, read before anything is flashed (decision 3, item 4: knowledge only).
Items 1, 2, 6 and 9 are not run: the owner's decisions of 2026-10-28 settled what they were to decide (the C-stack
reboot stays; the lost-FRAM chain goes and the mempause deadline stays, "No measurement"; NP-5 is reverted).""",
  """- `REPORT.md` 7's items 1, 3, 4, 5, 7, 8 and 10, with the optional 12 (item 1, the C-stack peak, is the bench reading
  of the owner's `c-stack-reboot` "ok" and checks B1's logger-side form);
- item 11, the owner's owed rows (the DMA ring proof, reset reasons 21, 22 and 10+phase, the first unfed watchdog
  stretch, dev's receive-ring peak);
- the queue R3 prepares (OR8.a: the hardware phase "works through the queue"), the lone-BMP3xx general call among it;
- the actions of `audit/actions/C.md` that survive R1 (OR47.a's boot log and trigger stamps, OR60.a (4)'s reset codes
  0, 9, 10+p and 20, OR50.a (3)(b)'s bench packages, OR79.a's off-subnet DNS attempt);
- the review "ok"s that name the bench: the SGP40 chip identity and serial read, the SCD30 readiness limits;
- B2's RUN-pin and HAD_POR checks, re-planned;
- the FRAM log's W29 history, read before anything is flashed (decision 3, item 4: knowledge only).
What the session on the bare MicroPython image before R1 answers (owner, 2026-10-28) is not repeated. Items 2, 6 and 9
are not run: the owner's decisions of 2026-10-28 settled what they were to decide (the lost-FRAM chain goes and the
mempause deadline stays, without a measurement; NP-5 is reverted).""")
# F4.21, F4.83
r("""- **OR68.a.** Provenance, plus DECREV 4's WoZi wording and section 5's seven misattributed texts fixed.""",
  """- **OR68.a.** Provenance, plus DECREV 4's WoZi wording and section 5's seven misattributed texts fixed.
- **OR51.a (4).** The quality bar and test standard in SPECIFICATION.md (Part D, D.12, Part E); session practice in
  CLAUDE.md's working agreements.""")
r("""  The substance they carry is the owner's rows OR27.a, OR13, OR14, OR15.a, OR44.a, OR10.b and OR68.a, which R4 meets
  directly. The rule actions add CLAUDE.md rules; each is shown to the owner at R4's checkpoint, and only those with an
  owner row behind them are adopted.""",
  """  The substance they carry is the owner's rows OR27.a, OR13, OR14, OR15.a, OR44.a, OR10.b, OR51.a (4) and OR68.a,
  which R4 meets directly. The rule actions add CLAUDE.md or SPECIFICATION.md rules; each is shown to the owner at R4's
  checkpoint, and only those with an owner row behind them are adopted. The one code action, A.U36.038, goes to R5.""")
# F4.24, F4.25
r("""- **The build-environment list.** The chroot list covers every build-environment change since the legs were last run.""",
  """- **The build-environment list.** The chroot list covers every build-environment change since the legs were last run.
- **The D.15 order beyond `src/`** (A.U36.038; OR96: "2. a but not the unit tests themselves"; "Option d is fine",
  2026-10-27): the sweep and its all-scope check.
- **U37's 01 (2), 02, 04, 05 and 17.** The second dependency check (A.SDEP.25, OR129.a (1)), the allow-lists removed once
  empty, the knowledge base and the twin fidelity table made final, BACKLOG's owed-hardware list from phase C's
  inventory, and the owner-row trace.""")
# F4.27, F4.28
r("""- the Stull paper moves to the datasheets;""",
  """- the Stull paper moves to the datasheets repository, after clarification (j);""")
r("""- one merge into `main`, tagged as the release (OR11.a, OR52.a (4)).""",
  """- one merge into `main`, tagged v2.0 as the release with the owner's agreement (OR11.a, OR52.a (4); the review's
  `release-version-2-0` and `release-defined-point`).""")
# F4.29
r("""- Inside a phase, batches run one after the other without waiting. Each batch ends with a short report of numbers and
  carries no question.""",
  """- Inside a phase, batches run one after the other without waiting, except for a batch's clarification (section 7).
  Each batch ends with a short report of numbers and carries no question.""")
# F4.33
r("""6. No hardcoded delay checks, in the product or in tests. A new wait uses an event, an order, or the driven clock.""",
  """6. No new hardcoded delay check of the NP-5 kind, in the product or in tests; a new wait uses an event, an order, or
   the driven clock. The owner-decided deadlines (the mempause deadline, the LED request's deadline, the NTP stale
   interval) and the hang backstop stay.""")
# F4.37
r("""- At most two lanes run at a time, on disjoint files. The lead does small items directly.""",
  """- At most two lanes run at a time, on disjoint `src/` files; the three shared files as in 2.3. The lead does small
  items directly.""")
# F4.44
r("""- Every push follows the local gate (lint, typecheck, the unit tier at both GC stages, the twin suite where the batch
  touches it). CI is followed""",
  """- Every push follows the local gate (lint, typecheck, the unit tier and dev's twin suite at both GC stages; the other
  devices' twins run in CI). CI is followed""")
# F4.41, F4.42, F4.44
r("""- the full local unit tier takes about 10-11 minutes per GC stage on a quiet host (2026-10-26 17:31-17:53), and 17-20
  minutes under load (2026-10-27);
- one CI run takes about 16 minutes (run 40678957431).""",
  """- the full local unit tier takes about 10-11 minutes per GC stage on a quiet host (2026-10-26 17:31-17:53), and 17-35
  minutes under load (2026-10-27, four lead gates, all with failures);
- dev's local twin suite takes about 21-22 minutes per GC stage (2026-10-26);
- one CI run takes about 16 minutes with the twin and coverage jobs skipped (run 40678957431), and took 27 minutes with
  them (run 39665515089, 2026-10-21).""")
r("""- the line-by-line review: 0.3-0.5 h;
- the push and CI: 0.3 h.
That is about 3.1-4.2 h per batch.""",
  """- dev's twin suite at both GC stages, once: about 0.7 h;
- the line-by-line review: 0.3-0.5 h;
- the push and CI: 0.5 h.
That is about 4.0-5.1 h per batch.""")
r("""| P the plan check, before R0 (2026-10-28) | 5 (its falsification agents) | about 2 |
| R0 settling | 0 | 1.5-2 |
| R1 firmware and build chain, 8 batches, test first | 12 (8 + 4 follow-ups) | 19-25 |""",
  """| P the plan check, before R0 (2026-10-28) | 5 (its falsification agents) | 12-22 at its go-ahead; about 2.5 used |
| R0 settling | 0 | 2-2.5 |
| R1 firmware and build chain, 8 batches, test first | 12 (8 + 4 follow-ups) | 24-31 |""")
r("""| R3 test campaign once, round 1 preparation (decision 4's lean form) | 8 | 6-10 |
| round 1 | (the owner's bench time) | 1-2 sessions |""",
  """| R3 test campaign once, round 1 preparation (decision 4's lean form) | 8 | 9-15 |
| round 1 | (the owner's bench time) | 2-3 sessions |""")
r("""| R5 close of execution | 4 | 3-5 |""", """| R5 close of execution | 6 | 6-10 |""")
r("""| **total before round 1** | **31** | **33-47** |
| **total after round 1** | **14** | **13-21** |""",
  """| **total before round 1** | **31** | **about 43-59** |
| **total after round 1** | **16** | **16-26** |""")
r("""the runaway pace. The softest numbers are the number of fix rounds per batch and R3, which depends on decision 4.""",
  """the runaway pace. The falsification added the twin suite and the full CI time to each batch, R0's first full CI run,
R3's wider OR37.a/OR38.a pass and its twin runner run, and R5's D.15 sweep and U37 items. The softest numbers are the
number of fix rounds per batch, R3 (the twin runner's run time is not measured) and R5's D.15 sweep.""")
# F4.59 and the rule applied
r("""   - Applied by the same rule after the plan check: R0 2 h (its estimate is now 1.5-2 h); the plan check 22 h and 5
     runs, the runs added for its falsification agents (owner, 2026-10-28: "adapt the run counts accordingly").""",
  """   - Applied by the same rule after the plan check and its falsification: R0 2.5 h; R1 31 h; R3 15 h; R5 10 h and 6
     runs; the plan check 22 h (its estimate at the go-ahead was 12-22 h; about 2.5 h used) and 5 runs, the runs added
     for its falsification agents (owner, 2026-10-28: "adapt the run counts accordingly").""")
# F4.50
r("""     put the firmware first ("The goal for the first hardware round after U35 was to have the firmware final. That's
     still in place.").""",
  """     put the firmware first ("The goal for the first hardware round after U35 was to have the firmware final. That's
     still in place."), and on 2026-10-26: "there is no need to restrict on "firmware first" alone".""")
# F4.56
r("""     your OR113's first rung ("retry the transaction")""", """     OR113.a's first rung ("retry the transaction")""")
# F4.57
r("""   - **Decision 3 is closed.**
   - (a) Remove their code in R1 and verify them in round 1. A confirmed one comes back as a minimal fix, on
     evidence.
   - (b) A short measurement session before R1. This needs the bench and at least one flash cycle, and it delays R1.
   - The pre-audit code these items replace ran without an observed failure.
   - Recommendation: (a).
""", """   - **Decision 3 is closed.**
""")
# F4.60
r("""   - Facts: the never-reuse rule is agent text, and it would leave about 20 tombstone rows. Its stated reason is FRAM
     history across reflashes, which the owner does not require (OR47.a: "no requirement for the fram to stay
     consistent through firmware re-flashes"). The refactored firmware has only ever run on the dev bench.""",
  """   - Facts: the never-reuse rule is agent text, and it would leave about 20 tombstone rows. The tree states no reason;
     the scan gives FRAM history across reflashes (DECREV.md), which the owner does not require (OR47.a: "no
     requirement for the fram to stay consistent through firmware re-flashes"). The refactored firmware has only ever
     run on the dev bench.""")
# F4.62, F4.63, F4.64, F4.27 (j)
r("""Each is a pair of the owner's statements that pull apart (DECREV 6; (i) found by the plan check). Each is asked once, in
prose, when its batch begins, and never before:""",
  """Each sets an owner statement against another owner statement or a code fact (DECREV 6; (i) and (j) found by the plan
check). Each is asked once, in prose, when its batch or checkpoint begins, and never before:""")
r("""  that prints a caught exception, which no owner word covers (batch B1);""",
  """  that prints a caught exception, weighed against the owner's "no evidence to a bug ... is silently lost" and the
  memory gates, which see a caught MemoryError only through a printed line (batch B1);""")
r("""- **(h)** the wet bulb's cold-dry corner against "Adapt the humidity to the verified range" (batch B2; the
  `rel_humidity()` clamp is not part of it);""",
  """- **(h)** whether the owner's "Adapt the humidity to the verified range" (said of the Magnus pair) extends to the wet
  bulb's cold-dry corner, an agent-added exclusion (batch B2; the `rel_humidity()` clamp is not part of it);""")
r("""  against "The audit verification machinery is just a temporary tool" (2026-10-28) (R2's checkpoint).""",
  """  against "The audit verification machinery is just a temporary tool" (2026-10-28) (R2's checkpoint);
- **(j)** the Stull paper's move: write access to the `datasheets` repository (the owner's grant names fetching only)
  and the paper's redistribution terms (OR52.a (7)) (at D).""")
# F4.68
r("""- (a) and (b) are settled by decisions 4 and 5.""",
  """- (b) is settled by decision 4; (a), OR30.a's scope of the tunables register, by R2's Part N scope, shown at R2's
  checkpoint.""")
# F4.70
r("""- (g), the hazard row added to A.11 after the owner signed it off, is a records fix: the signed-off table is restored
  in R4, and the added row's content moves to the Part it concerns, as agent text.""",
  """- (g), the hazard clause added to A.11's row 2 after the owner signed it off, is a records fix: the signed-off table
  is restored in R4, and since B6 keeps the hazard mode, row 2 keeps naming the `UartHazards` dispatch field (A.11's
  own rule, `test_a11_names_every_dispatch_field`), marked as agent text.""")
# F4.72
r("""Later lanes advanced 07, 22, 36 and 52 without finishing them.""",
  """Later lanes advanced 03, 07, 08, 22, 36, 37, 41 and 52 without finishing them.""")
# F4.74, F4.76, F4.77, F4.80
r("""| done | its silicon run is in round 1 |""", """| done | its silicon run is in round 1, through the queue R3 prepares |""")
r("""| done (45 reversed: the owner kept `logger=`) | consistent with R1; B1-B3 re-check them |""",
  """| done (45 reversed: `logger=` kept under the owner's library rule) | consistent with R1; the batches of their files re-check them (B2, B3, B6, B8) |""")
r("""| partly | the twin record retires in R0 (`twin_board.py` and `--twin` stay); OR21.a's twin pointing goes to R3 |""",
  """| partly | the record's committed copy retires in R0 and the runner stays; R3 runs it once on the final tree (OR21.a, OR29.a (4)) |""")
r("""| retired; OR21.a's hardware-test twin check in R3, in its lean form |""",
  """| retired; R3's twin runner run (OR21.a, OR29.a (4)) |""")
# F4.18: C.md mapping
r("""| 9 the serial close | replaced, as in 3.1 |
""", """| 9 the serial close | replaced, as in 3.1 |

Phase C's action list (`audit/actions/C.md`, A.C.01-A.C.19): each action that survives R1 goes to round 1's list (3.2);
the rest is dropped at R3's preparation, each with its reason.
""")

bad = [(i, t.count(o)) for i, (o, _) in enumerate(E) if t.count(o) != 1]
if bad:
    for i, c in bad:
        print("EDIT", i, "count", c, repr(E[i][0][:90]))
    sys.exit(1)
for o, n in E:
    t = t.replace(o, n)
open(P, "w", encoding="utf-8").write(t)
print("applied", len(E))
