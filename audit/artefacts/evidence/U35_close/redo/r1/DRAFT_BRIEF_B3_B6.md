# Action-list draft for B3 or B6 (lead, 2026-11-03)

You draft one R1 unit's action list; the lead finalises it and a fresh agent does the unit later. Read-only work: no
test runs, no commits, no edits outside your unit's folder (`S/u35r/r1/B3/` or `S/u35r/r1/B6/`).
S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

Read first: `S/u35r/r1/common_r1.md` (binding), `S/u35r/plan/PLAN.md` sections 0, 2, 4 and your unit's R1 row, your
row in `S/u35r/plan/PLAN_before_rewrite.md` 2.3, `S/u35r/plancheck/R1.md`'s rows for your unit, `S/u35r/r1/CARRY_LATER.md`
(your unit's lines) and the owner's words in `S/u35r/recovered/owner_rulings_after_LN118.md`. Then the sources the
B4/B5 lists cite for their rows, for your files: `S/u35r/scan/C.md` and `REPORT.md`, `S/u35r/scan2/G1-G4*.md` and the
closure tables, `S/u35r/decrev/DECREV.md`, `S/u35r/bench/READING_20261029.md`. Model your list on
`S/u35r/r1/B4/ACTION_LIST.md` and `S/u35r/r1/B5/ACTION_LIST.md` (same columns, the same one-page discipline), and see
`B4/FALSIFY_VERIFIED.md`/`B5/FALSIFY_VERIFIED.md` for what their lists missed.

- Base: worktree `S/wt-b3` or `S/wt-b6` (branch `audit/r1-b3`/`audit/r1-b6`) at `90691b6d`, the integration head with
  B1, B2, B4 and B5 merged; line numbers are that tree's. Pre-audit: `25caf528` (`git show 25caf528:<path>`). Never
  read `arduino/` (`':!arduino'` in every git grep and git log); never open anything under `/root/.claude/`.
- Every hunk of your files between `25caf528` and `90691b6d` is judged: an item names it, or it is restored.
  `S/u35r/tools/review_hunks.py 25caf528 90691b6d src buildgen` lists them (run it with `python3`; it only reads git).
- Per item: what (file:line), decision (keep, shrink, remove, restore, change), basis (owner word with date, a gap, a
  reproduction, a scan row), and the test that shows it (the pinning tests that go first, by file:line).
- Mark every item removing something a user sees (a REST or `/status` key, a website element, a catalog row the site
  shows) with no recorded owner agreement: those go to the owner. A legacy function lost or changed without a recorded
  reason goes to the lead, with its legacy file:line.
- B3 adds: the SPI "no bus" consumers B4 left (`SPI.available` and its five FRAM-driver readers), the FRAM SPI clock
  1 to 8 MHz (owner, 2026-11-02), the CARRY_LATER E19 check, the `setup()` bools except the FRAM driver's (read at
  `asy_fram_manager.py`), the shared catalog/emitter/definitions rows. Clarification (e) is decided: ask nothing.
- B6 adds: the receive-ring teardown fix carried in from `916fb878` (on `origin/claude/u35-bench-campaign`; read it with
  `git show`), the comment at `asy_uart_driver.py:80`, the `cobs` crossover mode (test-side), the UART changelog entry
  each change needs (CLAUDE.md), the `setup()` bools except `UARTComm.setup()`, `UARTDriver.deinit()` keeping its bool.
  Clarification (c) is decided: ask nothing. The wire format stays untouched.

Write `ACTION_LIST_DRAFT.md` in your unit's folder, first line "<unit> <name>: action list draft (agent, <date -u>)".
Your final message: the path, the number of items, the items needing the owner (one line each), last "nothing of mine
is running".
