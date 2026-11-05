# Action-list draft for B7 or B8 (lead, 2026-11-03)

You draft one R1 unit's action list; the lead finalises it and a fresh agent does the unit later. Read-only work: no
test runs, no commits, no edits outside your unit's folder (`S/u35r/r1/B7/` or `S/u35r/r1/B8/`).
S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

Read first: `S/u35r/r1/common_r1.md` (binding), `S/u35r/plan/PLAN.md` sections 0, 2, 4 and your unit's R1 row, your row
in `S/u35r/plan/PLAN_before_rewrite.md` 2.3, `S/u35r/plancheck/R1.md`'s rows for your unit, `S/u35r/r1/CARRY_LATER.md`
(your unit's lines) and the owner's words in `S/u35r/recovered/owner_rulings_after_LN118.md`. Where PLAN.md's row and an
earlier row differ, PLAN.md's row wins (it is the checked, final one). Then the sources the B3/B6 lists cite for their
rows, for your files: `S/u35r/scan/C.md`, `D.md` and `REPORT.md`, `S/u35r/scan2/G1-G4*.md` and the closure tables,
`S/u35r/decrev/DECREV.md`, `S/u35r/picture/PICTURE.md`. Model your list on `S/u35r/r1/B3/ACTION_LIST.md` and
`S/u35r/r1/B6/ACTION_LIST.md` (same columns, the same one-page discipline), and see `B3/FALSIFY_VERIFIED.md`,
`B6/FALSIFY_VERIFIED.md` and `MERGE_B3B6_NOTES.md` for what their lists and fixes missed.

- Base: worktree `S/wt-b7` or `S/wt-b8` (branch `audit/r1-b7`/`audit/r1-b8`) at `d6bc7617`, the integration head with
  B1-B6 merged; line numbers are that tree's. Pre-audit: `25caf528` (`git show 25caf528:<path>`). Never read
  `arduino/` (`':!arduino'` in every git grep and git log); never open anything under `/root/.claude/`.
- Every hunk of your files between `25caf528` and `d6bc7617` is judged: an item names it, or it is restored.
  `S/u35r/tools/review_hunks.py 25caf528 d6bc7617 <paths>` lists them (run it with `python3` from your worktree; it
  only reads git).
- Per item: what (file:line), decision (keep, shrink, remove, restore, change), basis (owner word with date, a gap, a
  reproduction, a scan row), and the test that shows it (the pinning tests that go first, by file:line).
- Mark every item removing something a user sees (a REST or `/status` key, a website element, a catalog row the site
  shows) and say whether an owner agreement is recorded for it (quote it with its date) or not: those without go to
  the owner. A legacy function lost or changed without a recorded reason goes to the lead, with its legacy file:line.
- B7 (`asy_neopixel_driver.py`, `asy_notification_service.py`, the `State` field's buildgen, catalog and website
  sites): the PLAN row and plancheck B7.1-B7.K, with B7.3's fix (the entry sanitiser goes back to the pre-audit
  per-channel clamp with its NaN/inf catch and 0.1 s floor, `25caf528 asy_neopixel_driver.py:29-39`; the 60 s cap and
  the move to the entry go). The internal request's change is a behaviour change: its test goes red first. Settle
  NP-4's end state in the list. The owner's words on the five minutes (rulings file, 05:58 LN358 and 06:37 LN362) bind
  the overlay item. The `setup()` bools of your files (CARRY_LATER), B2's edit to the notification `setup()` override.
  No clarification is open for B7.
- B8 (`buildgen/`, the generated modules, `devices/*.toml`, `js/` and `html/` frozen into the image, the website stager
  in `scripts/`): the PLAN row and plancheck B8.1-B8.K (B8.5's bus-spread order: PLAN keeps it, OR47), `S/u35r/r1/B8/
  CARRY.md` (judge the boot entry's level-0 prints against the owner's "There must be a mode which is really silent on
  the console, ever. That's level 0."), CARRY_LATER's `SetupFct` line. B7 runs first and removes its own rows and keys
  in the three shared files (`buildgen/error_catalog.json`, the status emitter in `buildgen/codegen.py`,
  `definitions.py`): leave the `State` field, W67 and the NP/NT rows to B7 and say so in one line; the lead re-bases
  your line numbers after B7 merges. List the website items with no recorded agreement (the page build-date stamp, the
  `BuildDate` field, the website rows of `ResetBits` and `ConfigUnpersisted`, and any other you find) one by one, each
  with what it shows, where (file:line), when it came in (commit) and what removing it would change for a user.

Write `ACTION_LIST_DRAFT.md` in your unit's folder, first line "<unit> <name>: action list draft (agent, <date -u>)".
Record lines at most 120 characters. Your final message: the path, the number of items, the items needing the owner
(one line each), last "nothing of mine is running".
