# R5 unit D: the owner's closing rulings in the docs, and the website tier's twin stop (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `r5d_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then SPECIFICATION.md F.6.1 in
your worktree (why a twin is ended through its stop file, not SIGINT).

## Owner rulings behind this unit (2026-11-06, UTC, verbatim)
- 06:16, on BACKLOG's item "R13 + N3, UART `wrnno` 54 ... against a real babbling peer": "Defer, that can be done once
  the UART C implementation is done and can go into both directions. But this is out of the audit scope."
- 06:43, on the I2C bus-recovery line levels and the FRAM CS level at power-off: "Option A, I have no oscilloscope at
  hand" (both recorded as limitations; the functional outcome is proven on silicon, the electrical detail is not).
- 06:47, on BACKLOG's manual Safari / mobile spot check: "Option B" (a limitation at Part H.1; the item comes out).
- 06:58, on BACKLOG's numbering paragraph: "Option A" (it goes; item 2 becomes a plain bullet).

## Your work (worktree `S/wt-r5d`, branch `audit/r5d`, at int `2a1deb42`; create it; commit locally, never push)
1. BACKLOG.md's babbling-peer item: deferred until the C implementation can play the peer in both directions,
   outside the audit's scope, with the owner's words; keep its expected results, drop the "needs hardware" framing.
2. Limitations, one sentence each: the I2C line levels through a bus clear (SPECIFICATION.md F.5.1); the FRAM CS level
   at power-off (the FRAM section that states the CS rule). Do not touch BACKLOG.md's bus-recovery item or
   `tests_hardware/` (another unit owns them).
3. Part H.1: the cross-browser goal is verified by automation on Linux browsers only (no real Safari or phone pass);
   BACKLOG.md's spot-check item comes out.
4. BACKLOG.md:11-15's numbering paragraph goes; item 2 becomes a plain bullet like the rest;
   `PROJECT_AUDIT_PLAN.md`'s "BACKLOG #2" names the item instead.
5. `tests_js/_twin_process.js`'s `stopProcess()` ends a twin through the runner's `--stop-file`, as
   `scripts/_twin_process.py` does, SIGKILL past the bound as today, and its comment says why (F.6.1). The launch
   gives each twin its own stop file and removes a stale one. No SIGINT is left in the file.

## Rules for the text
Text outside `audit/` cites no audit IDs, unit names or finding numbers. An owner ruling is quoted with "(owner,
2026-11-06)"; a fact carries its source. Comment-block and line rules as CLAUDE.md states them. The smallest form: one
sentence where one does.

## Checks
`S/u35/lead/lint_direct.sh` (eslint included if it runs there; otherwise `npm run lint` and `npm run typecheck`); the
tests_scripts files that read the docs (`test_citations.py`, `test_decision_vocabulary.py`, `test_code_conventions.py`,
and any other that reads BACKLOG.md, SPECIFICATION.md or PROJECT_AUDIT_PLAN.md); the website tier's live-twin tests,
once, under `S/u35/lead/heavy.lock` as common_r1 says (they bind real ports: never beside another heavy run).

## Limits
Write only BACKLOG.md, SPECIFICATION.md, PROJECT_AUDIT_PLAN.md and `tests_js/_twin_process.js`. One commit. Net growth
at most 10 lines. Budget about 0.6 % of the week; hand back by 10:00 UTC.

## Hand-back
`S/u35r/r5/HANDBACK_R5D.md`, at most 15 lines, and return its path: per item where it went (file:line), lines in and
out, each check with its result. Last line: "nothing of mine is running".
