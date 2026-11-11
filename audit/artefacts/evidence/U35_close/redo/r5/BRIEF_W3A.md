# R5 unit W3a: the close's records and the final report's draft, the part no bench figure feeds (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `w3a_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Tree: int `S/wt-u35int` at 51c9c75f,
read only (never write there, never run anything in it). Your rows: `S/u35r/r5/CLOSE_STATUS.tsv` N01, N02, P03, P07,
O4 (in CLOSE_STATUS.md), and PLAN's D bullet (`S/u35r/plan/PLAN.md`, "### R5, the close"). What happened since
651af010: FINDINGS (`S/u35r/findings/FINDINGS.md`) 12.173-12.185 (grep, never whole); the owner's record
`S/u35r/recovered/owner_rulings_after_LN118.md` (grep by topic).

## Owner (verbatim)
- 2026-11-07 (the yardstick): "all gaps closed, (really) agreed on features implemented, and from there on minimal,
  efficient and lean changes."
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"

## Your work (read-only; everything you write goes under `S/u35r/r5/W3A/`)
1. N01 + N02 (`N01.tsv`): each row of `audit/sweeps/open_findings.md` still open or partly closed (73), plus OF-16's
   record (`open_findings.md:24`, `audit/REGISTER.md:243`) and DECREV 4's ninth place: its terminal state at 51c9c75f -
   DONE (commit or file:line), PLACED (its forward value already in SPEC/BACKLOG/README: where), TO PLACE (the
   smallest doc line that keeps its forward value, and where), DROPPED (no forward value: why, one line), BENCH (the
   last round's step that answers it), OWNER (one line in operational terms). No decided topic re-decided.
2. O4 (`O4.tsv`): every "(agent, 2026-11-06)" to "(agent, 2026-11-10)" credit outside `audit/` at 51c9c75f (git grep,
   ':!arduino'): file:line, topic, what it decided in one line. Group by topic; give the counts. These go to the owner
   at the phase stop (rule 4.1.9) as a list to accept or overrule.
3. The load entries (`LOAD.md`): `audit/b3/load.md`'s cells and OR49.a (3)'s entries re-read against 51c9c75f (tests
   moved, renamed or removed since 10-22): per cell, still right or the one-line correction.
4. D's check (`DNR.md`): the do-not-reopen decisions (PLAN's D bullet; find their list in `audit/` by grep) each at
   its doc site at 51c9c75f: present and current, or what is missing.
5. The final report's draft (`REPORT_DRAFT.md`, at most 150 lines): what the audit changed against the pre-audit tree
   25caf528 (by area, current fact, no path narrative), the terminal-state counts (from 1), the owner items O1-O6 and
   how each closed (FINDINGS and the record), the O4 list's counts, the load entries, the build-environment list, and
   placeholders marked `<BENCH>` for what the last round fills (the two-image proof, the heap figures, the twin
   corrections) and `<D>` for the tag of the last commit holding `audit/`.

## Never
Never edit any tree, branch or doc; never run tests or builds; git, grep and read-only text tools only. Never read
`arduino/` (`':!arduino'` in every git grep and git log); never view SPECIFICATION.md, CLAUDE.md, BACKLOG.md,
README.md, PROJECT_AUDIT_PLAN.md, `devices/`, `audit/` or `src/asy_wifi_service.py` unfiltered; where a claim depends
on a filtered line, print only identifier matches. Never write a credential or the hotspot literal anywhere. Never
open `/root/.claude/`. No hardware. Scratch only under `S/u35r/r5/ftmp_w3a/`.

## Hand-back
`S/u35r/r5/HANDBACK_W3A.md` (at most 40 lines: per item its counts and anything that needs the lead or the owner),
the files above, one line per headline result, and last "nothing of mine is running". Budget about 2 % of the week.
