# Falsification check of the audit's finishing plan (lead, 2026-10-28)

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad

## The job
The owner asked for the plan's claims to be falsified by an independent check: "The claim falsification check agent
scan seems reasonable, too. Add this as a final verification". The plan is `S/u35r/plan/PLAN.md`. You get one scope
of it (your prompt names it). For every assertion in your scope, try to prove it wrong from the primary sources. You
are not asked whether the plan is wise; you are asked whether what it states is true and whether carrying out a row as
written would break something: remove a behaviour an owner decision keeps, remove code something still uses, miss a
file or an item, cite a source that does not say it, or state a wrong number.

Do not read `S/u35r/plancheck/` (the lead's own evidence; reading it would anchor you). Do not read the lead's lane
plan or task outputs.

## The sources
- The current tree: `S/wt-u35int` (commit 497b3eda, read-only). Pre-audit tree: `git -C S/wt-u35int show
  25caf528:<path>`. Many src files gained an `asy_` prefix since then (print_log, base_classes, captive_dns,
  config_manager, crc_checks, system_service, api_response, framing_codecs).
- Owner words, primary: `PROJECT_AUDIT_PLAN.md` section 3.2 (the OR rows: the owner's quote, then an ".a" row that is
  the agent's integration of it); `S/u35r/recovered/owner_rulings_after_LN118.md` (verbatim, dated); `audit/review/
  answers.json` (the review page's answers); CLAUDE.md (rules tagged "(owner, date)").
- Platform: the pinned MicroPython v1.29.0 source at `/root/pico-toolchain/micropython` (ports/rp2, extmod, py, lib);
  Microdot is `ext/microdot.py` in the tree. Never answer from memory of an API.
- The scan reports under `S/u35r/scan_pub/` (A-G.md, REPORT.md, scan2/, decrev/) are secondary. Use them to find where
  something is; a verdict must rest on a primary source (code, git, an owner quote, the pinned source).

## Rules
- Read-only. Never edit, commit, push, or write outside `S/u35r/plancheck/falsify/`. No hardware, no mpremote,
  picotool, nmcli, iw or iptables; no test runs. `git grep`, `git show`, `git diff`, small read-only Python (AST,
  counting) are fine; run Python with `-I`.
- Never read `arduino/` (use `':!arduino'` in git grep and git log). Never open anything under `/root/.claude/`.
- Never write a credential's value; the hotspot fallback password is written as "<hotspot default>".
- Use they/them for the owner.

## Hand-back
Write `S/u35r/plancheck/falsify/<your file>.md`, first line "<file> falsification, written by the part (<date -u>)".
- First, the list of the assertions you found in your scope, numbered `<scope>.<n>`, one line each.
- Then one entry per assertion that does not fully hold: id; the claim (short); verdict REFUTED (wrong), PARTLY (true
  only in part, or true but carrying it out as written would break something), or CANNOT TELL (the sources do not
  settle it); the evidence with file:line and a short quote; the smallest correction.
- Then one line listing the ids that hold, with the source you checked each against (one or two words each).
Final message: the path, the counts (assertions, refuted, partly, cannot tell), and the three most significant
findings in one line each. Last line: "nothing of mine is running".
