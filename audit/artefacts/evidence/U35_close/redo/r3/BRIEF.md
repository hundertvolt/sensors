# R3 brief, phase A: the row table (lead, 2026-11-04 16:00 UTC)

Read first, in order: `S/u35r/r1/common_r1.md` (binding; R1's environment and rules apply unchanged; labels start
with `r3_`), PLAN.md sections 0, 2, 4's R3 row and its round 1 row, and 5 (`S/u35r/plan/PLAN.md`), then
`audit/CONSOLIDATION.md` section 2's B3 row and section 4 (the requirement homes, with the B3 additions OR20/OR36,
OR45, OR55 and OR77/OR79). The owner rows are in `PROJECT_AUDIT_PLAN.md` 3.2; the owner's later words in
`S/u35r/recovered/owner_rulings_after_LN118.md`. What R1 and R2 left: `S/u35r/r2/HANDBACK.md`, its `ACTION_LIST.md`
and `LIST.md` section 6 (the carries not done); `S/u35r/r1/CARRY_LATER.md`.

- Worktree `S/wt-r3`, branch `audit/r3`, at the integration head `17688315` (R2 merged). This phase is read-only: git,
  grep and reading only; no source edit, no commit, no run. A timing comes from the records or CI's job times, else
  "measure in phase B".
- The owner, 2026-11-04 06:11 UTC: "take extra care that we are not currently creating a runaway, self-inflicted
  complexity increase." R3 proves; it does not build. Budget: R3's share is 5 % of the week for both phases; this
  phase is the smaller half.

## What the table holds (one Markdown file, `S/u35r/r3/ROWS.md`)
1. **Every group-B3 owner row** (OR16, OR19, OR20, OR21, OR22, OR23, OR25, OR29.a (4), OR36, OR37-OR41, OR45, OR49,
   OR55, OR77, OR79, with PLAN's R3 bullets for each), U35's items 09, 37 and 52, the bus hazard rule and the wear
   table: the row's own words in short; **met** (where: the file, test, record or commit, with the evidence) or
   **remaining** (the work, the runs it needs and their estimated machine time, what it would add: lines, files,
   tests, records) or **a limit for the owner** (one sentence: what cannot be met and why).
2. **Round 1's preparation** as PLAN lists it: what exists already and what remains, with the bench's two corrections
   and the bench loop-end test R2 changed (its first bench run is owed).
3. **The remaining work in order**, each item with its runs and hours; every item that would add a test, a file, a
   committed record or a mechanism is marked "adds" with the row that demands it. A new test only for a real gap or
   interaction with none (OR39.a-OR41.a's own rule); a working record stays under `S/u35r/r3/` unless the row asks
   for a committed one.

Head the table with the totals: rows met, remaining, limits; the remaining work's runs and machine hours; what it
adds. Anything that removes something a user can see, or touches a product test's goal, is marked "owner".

Your final message: the path, the totals in five lines, the number of "owner" and "adds" items, and last "nothing of
mine is running". The lead reads the table for complexity before phase B starts.
