# R5 unit specfund: every level and viewpoint into the general specifications (lead, 2026-11-07)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `specfund_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. In the integration tree
`S/wt-u35int` (18e9d59c): SPECIFICATION.md Part 0 (whole), Part D (whole), Part K.1-K.2, CLAUDE.md's "Working
agreements" and wherever P9's decision records are carried out; PROJECT_AUDIT_PLAN.md:373 (OR51) and :340 (OR36).
Then `S/u35r/findings/FINDINGS.md` 12.99-12.101 and the owner's entries from 17:02:19 on in
`S/u35r/recovered/owner_rulings_after_LN118.md`.

## Owner rulings behind this unit (2026-11-07, verbatim)
- 17:21:06: "I wonder if the same happened to other agreements as well. The agreements apply on function, module,
  import, integration and upstream and downstream, and full system - the specs (not just that one statement, in
  general!) apply to micro, medium and macro level!"
- 17:31:00: "Yes, probably I was not specific enough about the different viewpoints applying to the specs. Maybe that
  would have prevented part of the runaway as well. [...] These findings are fundamental. They must flow into and be
  applied to the general specs, as well as the consequences about the ruling."

## Your work (worktree `S/wt-specfund`, branch `audit/specfund` from int `18e9d59c`; create it; commit locally, never push)
1. Part 0.1: every principle, agreement and part of the specification binds at every level - function, module, import,
   integration with its upstream and downstream, full system - and is checked from each of those viewpoints (the
   owner's 17:21:06 words, quoted). Next to the existing breadth sentence ("binds the whole tree").
2. Part D: OR51's design questions as recorded (structure good, understandable, lean; setup reasonable, resilient,
   reliable; inheritance correct and complete; integration coherent; module specialties; simplification; anything
   missing; purpose fully met) as one item, with the check that makes them answerable: per operation, its physical need
   against its worst-case cost (largest input, under load, on silicon) and who waits meanwhile, at each level. A cost
   far beyond its need is a defect, never a fact to document. Fold D.8 into it (its "not a mandate to rewrite" goes
   where it contradicts). Part K.2 points to it.
3. Decision records (P9 and where it is carried out): a decision names its actor, date and the facts it rests on; when
   a fact is shown false the decision goes back to its maker with the new facts, never kept or overridden silently. A
   measurement names its condition (idle or loaded, which case, silicon or Unix port); a budget row names its real
   consumers from the code.
4. Owner questions (CLAUDE.md's working agreements, one bullet or the "Prefer flagging" one extended): asked only after
   the principles are checked at every level; a cost is stated with its context (which lock or bus it holds, under
   which load, who waits), never as an isolated figure. CLAUDE.md cites the specification rather than repeating it.
5. Current state and rules only, no history; owner quotes dated; no audit IDs outside `audit/`; the fewest lines that
   hold. Unit bfix edits SPECIFICATION.md Parts C.7.1, F.3, G, I and J and the UART changelog at the same time: touch
   none of those.

## Never
No hardware. Never read `arduino/`; never edit `ext/`; never open `/root/.claude/`. Never print, copy or write any
Wi-Fi credential or the hotspot fallback password.

## Checks
The `tests_scripts/` tests that read SPECIFICATION.md or CLAUDE.md (find them by grep), and `lint_direct.sh`. Docs
only: no full gate; a test needing a heavy run takes `S/u35/lead/heavy.lock` (line `specfund`) as common_r1 says.

## Limits
Write only SPECIFICATION.md Parts 0, D, K and CLAUDE.md. One commit. Budget about 0.5 % of the week. Hand back by
20:30 UTC.

## Hand-back
`S/u35r/r5/HANDBACK_SPECFUND.md`, at most 20 lines, plus the diff stat.
