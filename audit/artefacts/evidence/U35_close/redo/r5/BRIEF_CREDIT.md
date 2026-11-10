# R5 unit credit: every owner credit in the repository checked against the owner's record (lead, 2026-11-09; read-only)

## Read first
`S/u35r/r1/common_r1.md` (binding; the bound and "nothing new without a source" rules, the tag sentence, the filter
rule; label `credit_`). S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
Tree `S/wt-u35int` (head 6aec784f), read only; the audit's start is `25caf528`. FINDINGS 12.137 (the webserver's LED
credit with no ruling behind it), 12.139, 12.142 (one of two checked credits unbacked); `S/u35r/r5/CONSENT_1.md`-
`CONSENT_4.md`. The record: `S/u35r/recovered/owner_rulings_after_LN118.md` (verbatim since 2026-10-26), before it
PROJECT_AUDIT_PLAN.md's OR rows and decision lines quoting the owner, `audit/review/answers.json` (read with `jq`),
and the owner's words quoted in commit messages of the owner's own commits (author, not trailer). Grep by topic and
date; never read a record file whole.

## Owner (verbatim)
- 2026-11-09 22:27:31: "... similar patterns of what happened in the audit and was added without my consent and kept
  growing ..."
- 2026-11-06 06:53: "Single decision is by far to fine grained, that's micro management."

## The question
Every place the repository credits the owner - "(owner, <date>)", "owner decision", "the owner's direction", "project
owner", "owner-reviewed", "decided on the owner's behalf", "owner-confirmed", "per the owner", a quoted owner phrase -
in code comments, tests, the twin, scripts, CI, buildgen, js, html, devices, SPECIFICATION.md, CLAUDE.md, README.md,
BACKLOG.md, UART_C_PORT_CHANGELOG.md, DEVICE_REFERENCE.md, `.claude/skills/`. Excluded: `audit/` (the records
themselves), `arduino/`, `ext/`, `legacy/`, `python/`. For each credit: BACKED (a record line says this: cite it),
TOPIC (only a topic-level acceptance such as the 11-06 review covers it), STRETCHED (a record exists but says less, or
something else, than the credit claims: say what), UNBACKED (no record at all). Pre-audit credits (present at
`25caf528`) are checked the same way but listed apart.

## Completeness
Enumerate mechanically (`git grep -n -i -E` on the phrase list above plus `owner` in comment and prose lines; print
only `path:line` and the credit's date and topic words, never a filtered line whole). Ledger
`S/u35r/r5/CREDIT_ledger.tsv`: path:line, the credit's date, verdict, record citation or none - no source text.
Hand-back: the commands, the hit count, ledger rows = hits = the sum by verdict; the STRETCHED and UNBACKED ones
ranked by what they protect (a number, a mechanism, a rule that forced growth), each with the plain form it takes
("(agent, date)", or the backed quote).

## Never
Never edit any tree. No runs but git, grep, `jq` and read-only text tools. No hardware. Never read `arduino/`; never
open `/root/.claude/`. Credential filter on every view or grep of `src/asy_wifi_service.py`, generated modules,
`devices/`, SPECIFICATION.md, CLAUDE.md, PROJECT_AUDIT_PLAN.md and `audit/`; print only identifier matches where a
hidden line decides a claim; never print, copy or write any Wi-Fi credential, the hotspot password, or a
credential-scan pattern. Scratch only under `S/u35r/r5/ftmp_credit/`.

## Limits and hand-back
Write only `S/u35r/r5/CREDIT.md` (at most 50 lines; first line "credit hand-back, written by the agent (<date -u>)")
and its ledger. Budget about 1 % of the week. Hand back by 03:30 UTC: its path, one line per headline result, and
last "nothing of mine is running".
