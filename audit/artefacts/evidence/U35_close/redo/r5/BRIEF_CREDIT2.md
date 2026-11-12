# R5 unit cr2: the 117 pre-audit-dated owner credits resolved by the owner's rule (lead, 2026-11-10; read-only)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `cr2_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. `S/u35r/r5/CREDIT.md` (how the
credits were found and matched) and your input `S/u35r/r5/CREDIT2_input.tsv` (117 rows of `CREDIT_ledger.tsv`:
STRETCHED or UNBACKED, dated before 2026-09-25 or undated). Tree `S/wt-u35int` (head c4fc72ac), read only; the audit
started at `25caf528`. The record: `S/u35r/recovered/owner_rulings_after_LN118.md` (verbatim since 2026-10-26), before
it PROJECT_AUDIT_PLAN.md's OR rows and decision lines quoting the owner, `audit/review/answers.json` and
`decisions.json` (`jq`), `audit/REGISTER.md` rows quoting the owner, `audit/DECISION_PROVENANCE.md`, the owner's
own commits (author, not trailer). Grep by topic and date; never read a record file whole.

## Owner (verbatim, 2026-11-10 06:26:36)
"They surely come from the promotion sessions. They might really be mine, or they might be an agent's. In addition,
even if they were mine, there is some uncertainty if they actually were understood correctly by the session. They
should mostly be in line with our agreements. Some may also rather apply to a promotion session only and slipped
inside there. Generally, experience grew over progress and time, and if there are decisions into a different
direction which are clear and  came in later, the more recent ones sopersede the older ones. So probably you can
resolve these items with rule based like that. Check this, and tell me in case there are leftovers you cannot resolve."
Also binding: 2026-11-09 22:27:31 "don't drop real features and don't introduce or reintroduce gaps".

## The rules, applied in this order; the first that fits decides
- R0 GREW: the thing the credit protects (a number, a mechanism, a rule) is absent from `25caf528`, or grew there
  since (a new branch, bound, step or scope). The growth is an audit addition: its credit is "(agent, date)" and it
  answers to common_r1's two source rules. Do not judge it; name the growth and the unit it goes to.
- R1 LATER: a later, clear owner decision on the same matter goes another way (record line, date). The later one
  governs: the text states it with its credit, the old credit goes. Say whether the code already follows it.
- R2 AGREES: a record line says the same thing by content, not topic alone. The credit cites that line. Where the
  credit claims more than the line (a misreading), it shrinks to the line; the rest is "(agent, date)".
- R3 SESSION: an instruction for one promotion session (its scope, order, process, a "for now", a deliverable) that
  slipped into lasting text. The credit goes; what is still true stays as a plain current fact, nothing else.
- R4 FITS: no record and nothing later against it; consistent with the agreements (CLAUDE.md's standing rules, the
  record). The protected thing stays as it was at `25caf528` (a real feature or baseline behaviour); the credit
  becomes "(agent, date)" - or names its real source if the repository shows one (datasheet page, legacy value,
  measurement record): cite it. A number with neither: say so.
- R5 AGAINST: no specific later decision, but the credit contradicts a standing agreement. The agreement governs, as
  R1; name the code or text consequence.
- LEFT: none of R0-R5 resolves it - two record lines conflict with no clear order, or the outcome would remove or
  change something user-visible or feature-like. One line each for the owner: what it protects, the two readings,
  what each changes.

## Output
Ledger `S/u35r/r5/CREDIT2_ledger.tsv`: path:line, credit date, rule, record citation(s) or none, the credit's new
plain form (your words, no source text), consequence (text only / code: what, which unit - G firmware, C build chain
and website, T tests, P9 docs). Rows = 117. Hand-back `S/u35r/r5/CREDIT2.md` (at most 40 lines; first line "cr2
hand-back, written by the agent (<date -u>)"): counts by rule; every code consequence; every LEFT in operational
terms; what you could not check.

## Never
Never edit any tree. No runs but git, grep, `jq` and read-only text tools. No hardware. Never read `arduino/` (put
`':!arduino'` in every git grep and git log); never view `devices/*.toml`, SPECIFICATION.md, CLAUDE.md,
PROJECT_AUDIT_PLAN.md, `audit/` or `src/asy_wifi_service.py` unfiltered; print only identifier matches where a claim
depends on a filtered line. Never open `/root/.claude/`. Scratch only under `S/u35r/r5/ftmp_cr2/`, masked as common_r1
says. Do not re-ask the owner anything: an open case is a LEFT row.

## Limits and hand-back
Budget about 1 % of the week. Hand back by 09:30 UTC: the path, one line per headline result, and last "nothing of
mine is running".
