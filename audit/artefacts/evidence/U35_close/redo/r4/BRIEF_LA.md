# R4 phase B, lane A: SPECIFICATION.md and the integrate-module skill (lead, 2026-11-05)

## Read first
1. `S/u35r/r1/common_r1.md`. It is binding. Your labels start with `r4A_`.
2. `S/u35r/r4/ROWS.md`, all of it. It is your row table. Section 5 item 1 is your lane.
3. PLAN.md's R4 row (`S/u35r/plan/PLAN.md`) and decision 7.
4. Owner words: `PROJECT_AUDIT_PLAN.md` 3.2 and `S/u35r/recovered/owner_rulings_after_LN118.md`.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## Setup
- Your worktree is `S/wt-r4a`, branch `audit/r4a`, at `c78bbcf1`.
- You may write only `SPECIFICATION.md` and the new `.claude/skills/integrate-module/SKILL.md`.
- Commit locally on `audit/r4a` with clear messages. Never push.

## Your rows
- **Rows 1 and 2, the SPEC part:** the history pass and the plain facts. This includes Codecov at `:5493`; CI has no
  upload, so state what CI does.
- **Rows 6, 7 and 19:**
  - Part 0 "Design principles".
  - Part K becomes the one ordered checklist. It gets K.0, the owner-discussion stage and its record, and every step
    is marked "every module" or "a sensor driver".
  - The skill file: thin, at most 30 lines. It names the inputs and points into Part K; it restates nothing.
- **Rows 14, 15, 22 (the SPEC part), 26, 27, 32 and 33.**
- **Row 23:** only the facts its table says to "place now".
- **Row 29:** the first half only.
- **Row 11:** the SPEC sites only.
- **U36's checklist actions** whose site is SPEC.
- **The adopted rule proposals' SPEC sites**, from the 12 with an owner row (section 2), including 017's new E.2.2.
- **Not adopted, so do not write them:** 528, 536 and 539 (no owner row), and the test halves of 514, 532 and 537.
- **Rows that wait on round 1** (23's five facts and the three crossings, 29's second half, 30): leave them as they
  are.
- **The F.3 crossings:** a cell over its consumer stays as it is now. Do not decide a crossing.

## The heading map (fixed; lanes B and C cite it)
- **New:**
  - "Part 0 Design principles", before Part A.
  - "K.0 The owner-discussion stage", before K.1.
- **I.6:** keeps its number and title, and moves to the end of Part I.
- **E.2:** E.2.1, a new E.2.2 ("A test changes only mechanically", U36 017) and E.2.3 become `###` under E.2. Their
  titles stay as they are.
- **No other renumbering.** U36 532's F.5 renumbering is not taken. No other heading moves or is renamed.

## Rules (binding)
- **OR27.a:**
  - The docs hold facts, rules and agreements, never history. Each rule keeps one short reason and its
    "(owner, date)".
  - Every rewrite keeps its meaning. When a rule looks drifted, do not reword it: list it for the owner (OR13.a).
  - Quote owner words verbatim. Text that is not the owner's is marked "(agent, date)", never credited to the owner.
- **Facts:**
  - Check every fact you keep or move against the final tree (file:line).
  - Chip facts come from `/home/user/datasheets/` (document, page, table).
- **Allow-lists:** never write the two allow-lists. A citation or vocabulary failure caused only by an allow-listed
  sentence you rewrote is expected: list it. Fix any other failure.
- **Runs:**
  - Through `S/u35/lead/run.sh S/wt-r4a r4A_<label> <cmd>`, one at a time, at most eight in all.
  - Run section 3's `tests_scripts` checks that read SPEC: comment cap, citations, decision vocabulary, tunables,
    memory catalog, timing budget, threat model, level containment, the four SPEC table tests and THR facts.
  - Run `S/u23/rebuild.sh S/wt-r4a` once first, if a test needs generated inputs.
- **Hands off:**
  - Never read `arduino/`; put `':!arduino'` in every git grep and git log.
  - Never open `/root/.claude/`. No hardware. Never edit `ext/`.
  - Use `rm` only with literal paths, as its own call.
- **Size:**
  - Aim at ROWS' estimate: SPEC about +270/−580, the skill about +30.
  - If you exceed it by more than half, stop and say why.
  - Comment blocks are at most 3 lines.
- **Budget:** your share is about 2 % of the week. If you reach it, stop at a clean commit and report.

## Report, at most 40 lines
- The commits, and the lines in and out.
- Each row: done, left, or listed for the owner.
- For rows 6, 7, 11, 14, 15 and each adopted rule, the new text's first line, quoted with its line number.
- Every drifted rule you listed.
- The checks' results, with the expected allow-list failures counted.
- Last: "nothing of mine is running".
