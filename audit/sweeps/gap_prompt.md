# A-C gap pass brief

All 16 cluster merges (`audit/consolidation/M_*.md`) are done. Each one ends with a "Gaps for other clusters" section:
items one merge found that another cluster's file must carry. This pass makes sure every such item is carried exactly once,
in the right file, before the A-C2 dependency ordering.

## Inputs

- `audit/sweeps/ac_prompt.md`: the merge format and its rules. New or amended changes follow it exactly.
- Every `audit/consolidation/M_*.md`, both its "Gaps for other clusters" section and the change bodies.
- `audit/actions/AC_NOTES.md`, especially item 45, and `PROJECT_AUDIT_PLAN.md` 3.2 (OR1-OR133). The most recent owner
  decision wins. A rule that settles a question means it is not an owner question.
- Three late SPEC gaps (from the SPEC merge hand-back):
  1. DOCS: CLAUDE.md's "F.5.10" pointer → "F.9".
  2. DOCS: M.DOCS.092 drops its H.5.1 half.
  3. TEST_UNIT: the A.U13.19 idle-wait test cannot hit its degrade path on the Unix rig (2**29 is within its 2**62
     tick period).

## Method

You own a set of target clusters (given in your task). Collect every gap item, from all 16 files plus the inputs above,
that names one of your targets. For each item:

1. Find the change in the target file that already carries it. Read its body; a mention in the ledger alone is not enough.
2. If no change carries it:
   - amend the closest existing change in that file (body plus ledger row);
   - or, when none fits, add a new `### M.<CLUSTER>.nnn` after the file's highest number, in full ac_prompt format.
3. If the item is wrong, obsolete or already settled elsewhere, record the disposition and the rule or ID that settles it.
4. If carrying it also needs a change in a cluster you do not own, record a hand-off. Do not edit that file.

Edit only your own target M files and your own `audit/consolidation/GAPS_<GROUP>.md`. Do not touch repository code, docs
or any other audit file.

## Output: `audit/consolidation/GAPS_<GROUP>.md`

- A table with one row per item: source file and item number, target cluster, a short gist, the carrying M-ID (or "new",
  "amended" or "disposed"), and a reason when it was disposed.
- Hand-offs: items another group must carry.
- Owner questions, only if no rule settles them, in the owner's format: a top-level decision in max 10 words, then
  options and consequences.
- Counts: items read, carried as found, amended, new, disposed, handed off.

Accuracy before speed. Hand back a short summary: the counts, any hand-offs and any owner questions.
