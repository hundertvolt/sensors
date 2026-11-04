# R2 brief, phase A: the classification list (lead, 2026-11-04)

Read first, in order: `S/u35r/r1/common_r1.md` (binding, R1's environment and rules apply to R2 unchanged; labels
start with `r2_`), PLAN.md sections 0, 2 and 4 and its R2 row (`S/u35r/plan/PLAN.md` "R2, tests, tooling, CI and the
register"), then `S/u35r/r2/CARRY.md`. The owner rows are in `PROJECT_AUDIT_PLAN.md` 3.2 (OR30.a, OR37.a, OR23.a, OR15.a,
OR21.a among them); the owner's later words in `S/u35r/recovered/owner_rulings_after_LN118.md`. The scan of these areas
is `S/u35r/scan/E.md` (classes (a)-(d), the runaway chains): start from it, do not redo it.

- Worktree `S/wt-r2`, branch `audit/r2`, at the integration head 8a32d826 (R1 complete). Hand-back:
  `S/u35r/r2/LIST.md`. This phase is read-only: no source edit, no commit, no test run (git, grep and reading only; a
  timing you need comes from CI's own job times, `gh` is not available, so take them from the records or mark them
  "measure in phase B").
- The owner, 2026-11-04 06:11 UTC: "take extra care that we are not currently creating a runaway, self-inflicted
  complexity increase." The list is one Markdown file, no script, no new tool. Budget: R2's share is 5 % of the week
  for both phases; this phase is the smaller half.

## What the list holds
1. **Every file** in `tests/`, `tests_scripts/`, `tests_js/`, `tests_hardware/`, `digital_twin/`, `scripts/`,
   `toolchain/`, `mockdata/` and `.github/`, in one of PLAN R2's five classes: (P) pins a product property, kept;
   (O) a tool test covered by an owner row or word, kept, slimmed where it repeats itself; (A) audit machinery born in
   the audit, removed; (T) one of the eight SPECIFICATION.md table pins, kept where it checks a product property
   through the table or carries an owner row, its restatement of the table slimmed; (H) harness, kept unless a lighter
   form does the same. Files that exist at `25caf528` and stay unchanged in purpose may go in one grouped row per
   directory and class (path pattern, count, lines). Every file proposed to go or be slimmed gets its own row: path,
   lines, class, the basis (owner row or word with its date, or "none found"), the proof for (A) (no reader outside
   audit machinery: the `git grep` you ran), and what is left once it goes.
2. **Kept in full by owner rule** (do not propose touching): the comment-cap gate, the gc-site checker, the memory-gate
   agreement, the persistence-marker completeness, the four-tier bus-hazard files, the two decision-records checks
   (their allow-lists may only shrink).
3. **The seven fixed-sleep tests** (OR37.a (3)), each with the condition it should wait for; the shared twin's 89 s
   retirement and its idle event; the launcher stop file and the rig override (what reads them).
4. **CI**: each job's `timeout-minutes` against its measured need where a record has it, the margin you would state,
   the two retries kept; the twin matrix (devices x stages) against what it must cover, the per-device rule kept.
5. **Part N**: each register row in or out of OR30.a's scope (the row's own words), the `@tunable` tags outside it,
   and the heap-floor row's "measurement owed".
6. The CARRY items: for each, keep, change or out of R2, in one line.

Head the list with the totals: files and lines per class and per directory, and what the proposals would remove.
Anything that removes something a user can see, or touches a product test's goal, is marked "owner" and not proposed
as a removal. A legacy or pre-audit function found lost goes to the lead.

Your final message: the path, the totals in five lines, the number of "owner" rows, and last "nothing of mine is
running". The lead shows the list to the owner; phase B (the removals, the waits, CI, Part N) follows on their word.
