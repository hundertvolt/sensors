# R4 brief, phase A: the row table (lead, 2026-11-05)

## Read first, in order
1. `S/u35r/r1/common_r1.md`. It is binding: R1's environment and rules apply unchanged. Your labels start with
   `r4a_`.
2. From PLAN.md (`S/u35r/plan/PLAN.md`): sections 0 and 2, section 4's R4 row (with its round 1 and R5 rows for the
   edges), and section 5.
3. `audit/CONSOLIDATION.md`, section 4: the requirement homes.

Then the rest:
- **The owner's words:** the owner rows in `PROJECT_AUDIT_PLAN.md` 3.2, and their later words in
  `S/u35r/recovered/owner_rulings_after_LN118.md`.
- **What R3 left:** `S/u35r/r3/CARRY_R4.md`, `S/u35r/r3/ACTION_LIST.md` and `S/u35r/findings/FINDINGS.md`.
- **The knowledge lines:** `S/u35r/knowledge/`.
- **U36's inventory:** `S/u36prep/inventory.tsv` and `scope_draft.md`.

## Setup
- Worktree `S/wt-r4`, branch `audit/r4`, at the integration head `c78bbcf1` (R3 merged). S =
  `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
- This phase is read-only: git, grep and reading only. No edit, no commit, no run.
- **The owner's direction:**
  - 2026-11-03: "Generally target low complexity".
  - 2026-11-04: "take extra care that we are not currently creating a runaway, self-inflicted complexity increase."
- **R4's rule:** the docs are written once, from the final state. They hold facts, rules and agreements, never
  history.
- **Budget:** R4's share is about 6 % of the week for both phases; this phase is the smaller part.
- **Round 1:** the bench session runs separately and later. Mark every row whose text depends on a bench fact
  "waits on round 1", and name the fact.

## What the table holds (one Markdown file, `S/u35r/r4/ROWS.md`)
1. **The rows.** Cover:
   - every R4 row PLAN names: OR27.a, OR13, OR14, OR15.a, OR44.a, OR51.a (4), OR68.a with DECREV 4's WoZi wording
     and the seven misattributed texts, OR10 and OR10.b, the Parts that describe only removed mechanisms, the
     knowledge lines and the bench's facts as decision 7 places them, U36's 96 actions,
     `src/LICENSE-captive_dns`'s path and holder line, and (g) A.11's owner-signed table;
   - CARRY_R4's three items;
   - every FINDINGS line that names R4.

   For each row give its own words in short, then one of:
   - **met:** where (file:line) and the evidence;
   - **remaining:** the doc and section, the work, and what it changes (lines added and removed, and any file added
     or removed);
   - **a limit for the owner:** one sentence on what cannot be met and why.
2. **U36's 96 actions.** Give each one in one line:
   - dropped (its subject is gone: say what is gone);
   - checklist input (the doc it lands in);
   - or a rule proposal for the owner, which is adopted only with an owner row behind it.

   Count each class.
3. **The docs' own checks:** every check that gates a doc (the comment cap, link checks, the CLI reference check,
   any `tests_scripts` doc test). Give the command, its run time from the records or CI, and whether R4's edits can
   trip it.
4. **OR10 and OR10.b's proof:** the new-module procedure built fresh against two baselines, in at most three runs.
   Give which runs, their estimated machine time, and what each shows.
5. **The remaining work in order.** Split it into at most three lanes that touch disjoint files, and give each lane
   its files.
   - Mark "owner" anything that removes something a user can see, changes a rule, or touches a product test's goal.
   - Mark "adds" anything that would add a file, a test or a mechanism, with the row that demands it.

## Head and final message
- **Head the table with the totals:** rows met, remaining and limits; the lines expected in and out per doc; the
  runs and their machine hours; the "owner" and "adds" counts.
- **Your final message:** the path, the totals in five lines, the "owner" and "adds" counts, and last "nothing of
  mine is running". The lead reads the table for complexity before phase B starts.
