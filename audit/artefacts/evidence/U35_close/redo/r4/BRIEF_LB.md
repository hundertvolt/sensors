# R4 phase B, lane B: CLAUDE.md, README.md, BACKLOG.md, the CLI-reference check (lead, 2026-11-05)

Read first, in order:

1. `S/u35r/r1/common_r1.md`. It is binding. Your labels start with `r4B_`.
2. `S/u35r/r4/ROWS.md`, all of it. It is your row table; section 5 item 2 is your lane.
3. PLAN.md's R4 row (`S/u35r/plan/PLAN.md`) and its decision 7.
4. The owner's words: `PROJECT_AUDIT_PLAN.md` 3.2, and `S/u35r/recovered/owner_rulings_after_LN118.md`.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## Where you work
- **Worktree:** `S/wt-r4b`, branch `audit/r4b`, at `c78bbcf1`.
- **You write only these files:**
  - `CLAUDE.md`
  - `README.md`
  - `BACKLOG.md`
  - `UART_C_PORT_CHANGELOG.md`
  - `tests_scripts/test_tool_help.py`
- **Another lane writes `SPECIFICATION.md` at the same time.** Never edit it. Something that would have to move into
  SPEC, and is not there yet, stays where it is: list it.
- **Commit locally** on `audit/r4b`, with clear messages. Never push.

## Your rows
- **Rows 1 and 2, the parts in your files:**
  - CLAUDE.md gets one role per document (U36 546) and the history pass.
  - The Codecov line at `CLAUDE.md:760` states what CI does today.
- **Row 4, README:**
  - Reorder README task-first: install, build and flash, tests per tier, everyday variants.
  - Add a complete CLI reference with one `<details>` section per tool, giving every option.
  - Add its check (**adds**, OR15.a (1)): one test in `tests_scripts/test_tool_help.py`, in the smallest form that
    ROWS row 4 describes. It compares option names, not a byte copy.
- **Row 8:** the one working-agreement bullet, citing D and E, with OR51.a (4)'s owner line.
- **Row 11:** the WoZi sites in CLAUDE.md and README. Keep the general rule that row 11 states.
- **The adopted rule proposals' sites in your files.** These are the 12 that have an owner row (ROWS section 2).
- **U36's checklist actions** whose site is one of your files. Two of them are decided:
  - **002:** the FRAM rule keeps its meaning. Only its logger list becomes a pointer to A.7.
  - **524:** the chroot recipe moves from CLAUDE.md into README, as the owner's periodic build-environment check.
    CLAUDE.md keeps the rule and a pointer to it (lead, 2026-11-05).
- **Not adopted:**
  - 528, 536 and 539: they have no owner row, so CLAUDE.md's merge bullets and the hazard rule stand.
  - The test halves of 514, 532 and 537.

## The heading map
Fixed, and lane A creates it. Cite these SPEC headings:
- **New:** "Part 0 Design principles", before Part A, and "K.0 The owner-discussion stage".
- **Moved:** I.6 keeps its number and goes to the end of Part I.
- **E.2.1-E.2.3:** these become `###` under E.2, with a new E.2.2 ("A test changes only mechanically").
- **Nothing else** is renamed or renumbered.
- **Pointers:** CLAUDE.md's bird's-eye scan and README's "Further reading" each gain one pointer to Part 0. Where
  CLAUDE.md cites "Part D's checklist", it now cites Part K, the one checklist.

## Rules (binding)
- **OR27.a:**
  - The docs hold facts, rules and agreements, never history.
  - Each rule keeps one short reason and its "(owner, date)".
  - Every rewrite keeps its meaning. A rule that looks drifted is not reworded: list it for the owner (OR13.a).
  - Quote owner words verbatim. Text that is not the owner's is marked "(agent, date)".
- **CLAUDE.md is every session's operating instructions.** Every rule it holds now must still hold after your
  rewrite: kept, or a pointer to where it now stands. Keep a ledger in `S/u35r/r4/LEDGER_B.md`, one line per CLAUDE.md
  rule: the old line, then its new line, or its pointer target. No rule may vanish.
- **Facts:** check every fact you keep or move against the final tree (file:line).
- **Allow-lists:**
  - Never write either of the two allow-lists.
  - A citation or vocabulary failure caused only by an allow-listed sentence you rewrote is expected: list it.
  - Fix any other failure.
- **Runs:**
  - Run through `S/u35/lead/run.sh S/wt-r4b r4B_<label> <cmd>`, one at a time, at most ten runs in all.
  - First run `S/u23/rebuild.sh S/wt-r4b` once.
  - Then run section 3's checks for your files: comment cap, citations, decision vocabulary, tool help (your new
    test), THR facts, the UART changelog.
  - For the test file, also run `S/u35/lead/lint_direct.sh` and the host mypy pass.
- **Hands off:**
  - Never read `arduino/`; put `':!arduino'` in every git grep and git log.
  - Never open anything under `/root/.claude/`.
  - No hardware. Never edit `ext/`.
  - Use `rm` only with literal paths, as its own call.
- **Size:**
  - Aim at ROWS' estimate: CLAUDE.md about +30/−470, README about +300/−250, BACKLOG about +5/−55, the test about +30.
  - If you exceed any of these by more than half, stop and say why.
  - Comment blocks are at most 3 lines.
- **Budget:** your share is about 2 % of the week. If you reach it, stop at a clean commit and report.

## Report (at most 40 lines)
- The commits, and the lines in and out per file.
- Each row: done, left, or listed for the owner.
- For row 8, row 11's CLAUDE.md site and each adopted rule: the new text's first line, quoted with its line number.
- The ledger's counts: kept, pointed, and vanished (which must be 0).
- Every drifted rule you listed.
- The checks' results, with the expected allow-list failures counted.
- Last line: "nothing of mine is running".
