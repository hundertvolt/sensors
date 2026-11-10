# R5 unit CS: what the R5 close still owes, item by item, on the current tree (lead, 2026-11-10; read-only)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `cs_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Tree `S/wt-u35int` at 651af010,
read only (the lead's gate runs in it: never write there, never run tests). The plan: `S/u35r/plan/PLAN.md` section
"R5, the close of execution; the last round; D" and its rules 4.1. The items: `S/u35r/r5/INVENTORY.md` (11-05: 85 OR5.a
rows, 12 OR11 rows, 6 owner rows). What happened since: FINDINGS (`S/u35r/findings/FINDINGS.md`) 12.100-12.170 (grep by
row id and topic; never read it whole), the hand-backs `S/u35r/r5/HANDBACK_*.md` ("not done", "reported", "left"
lines), `S/u35r/r5/NEXT.md`, the owner's record `S/u35r/recovered/owner_rulings_after_LN118.md` (grep by topic).
The two-image proof's procedure: `git show origin/claude/u35-bench-campaign:audit/actions/C.md` lines 396-416 (A.C.09).

## Owner (verbatim)
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"
- 2026-10-28: "... make sure that you set up the process such that it can finished and is not designed
  self-sustaining / will never end".

## Your work (one table, one summary)
1. Every R5 item on 651af010: PLAN's R5 bullet (OR9.a re-verification, OR11 stray files, OR5.a terminal states,
   OR52.a (2) golden fixtures, version and release note, final report with OR49.a (3), build-environment list, D.15
   beyond `src/`, U37 01 (2)/02/04/05/14/17), each INVENTORY row, and each hand-back leftover. State per item: DONE
   (the commit or file:line that shows it), OPEN (the smallest change that closes it, its kind: firmware / test / docs
   / build / bench-last-round / final-report, and its size in lines), or OWNER (one line in operational terms: what it
   protects, the options, what each changes). An INVENTORY "N" row the record has since answered is DONE or OPEN, citing
   the answer. Do not re-decide anything decided; where two records conflict, say so.
2. The last round's list for the bench (the two-image proof per A.C.09, what round 1 left, OR17.a's twin corrections,
   the settle removal's re-measure, the heap load pattern of 12.169 on both images): what each needs from the tree
   before the image is built (a script, an instrument), present or missing.
3. Your recommended order for the OPEN items, grouped into at most three writing units by file ownership, each
   with its done-criterion; the final-report items last.

## Never
Never edit any tree or branch; never run tests or builds; git, grep and read-only text tools only. Never read `arduino/`
(`':!arduino'` in every git grep and git log); never view SPECIFICATION.md, CLAUDE.md, BACKLOG.md, README.md,
PROJECT_AUDIT_PLAN.md, `devices/`, `audit/` or `src/asy_wifi_service.py` unfiltered; where a claim depends on a filtered
line, print only identifier matches. Never open `/root/.claude/`. No hardware. Scratch only under `S/u35r/r5/ftmp_cs/`.

## Hand-back
`S/u35r/r5/CLOSE_STATUS.md` (at most 60 lines; first line "cs hand-back, written by the agent (<date -u>)": counts by
state, every OWNER item, the last round's needs, the recommended units) and `S/u35r/r5/CLOSE_STATUS.tsv` (one row per
item: id, source, state, evidence or change, kind, size). Budget about 1.5 % of the week; due 16:00 UTC. Your last line:
"nothing of mine is running".
