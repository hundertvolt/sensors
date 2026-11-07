# Q35: U35's completion inventory, read-only (lead, 2026-10-27)
The lead gave the owner an estimate of what is left of U35. It left out several U35 records that are still largely
open on the integration head: raising.md, conformance.md, load.md and matrices.md. This block checks independently what
U35 still owes, so that nothing else is missed. Do not trust the lead's lists; build the picture from the head and the
plan.

Read first: the repository's CLAUDE.md, `audit/actions/U35.md` (every A.U35.* action, its completion criteria, and its
depends lines), `audit/actions/verify/U35.md`, the headers of the `audit/b3/*.md` records, and then the lead's plan
`S/u35r/REDO.md` (lanes F, T, E, C, B, N, D/R, W10) and `S/u35r/d3r_rec2_items.md`.

Trees, all read-only: never write, check out, merge or run anything in any worktree.
- The integration head: `S/wt-u35int`. Use `git -C S/wt-u35int show HEAD:<path>`, and `git grep ... HEAD -- . ':!arduino'`.
- Lane branches not merged yet, same commands with their refs: `audit/u35-crr2b`, `audit/u35-cmr1b`, `audit/u35-n11`.

## Items
1. One row per A.U35.* action. Give:
   - its id and title;
   - its completion criteria, in one line;
   - its state on the int head (done, partly done, or open), with the line or record that shows it;
   - work on an unmerged lane branch that changes that state (branch and commit);
   - which block of REDO.md covers what remains (cite REDO.md's line). Write "NOT IN THE PLAN" where none does.
2. One row per `audit/b3/*.md` record. Give:
   - its completion rule;
   - its rows by state (count them; never estimate);
   - what is left, and which block covers it.
3. Every "NOT IN THE PLAN" item, with what it would take: the kind of work, the files involved, whether it needs runs
   (and which tier), and whether it can touch `src/` (a firmware fix). That last point matters most: the owner's rule is
   "Firmware really complete, don't push fixes to future units".
4. Size each open item in agent blocks of about 60-80 tool calls, with your basis (rows per block from earlier hand-backs
   in `S/u35r/handbacks_redo/`, where one exists). Say which items can run in parallel, and which need the host quiet
   (timing measurements) or need a full tier.

## Output
- Write `S/u35r/q35/actions.tsv`, `S/u35r/q35/records.tsv` and `S/u35r/q35/summary.md` (items 3-4 and the totals), in
  your own words. Never copy source or doc text beyond a short phrase that locates a line.
- No repo edits, no commits, no runs. Never read arduino/. Never open anything under /root/.claude/. No model
  identifiers. Shell: read-only commands only; file writes use the Write or Edit tool, under S/u35r/q35/ only.
- At 80 tool calls, write what you have, mark the rest unchecked, and hand back.
- Hand-back:
  - the counts by state;
  - every "NOT IN THE PLAN" item;
  - the open items that can touch src/;
  - the block-size total and the parallelism;
  - anything where the head contradicts a record;
  - last line "nothing of mine is running".
