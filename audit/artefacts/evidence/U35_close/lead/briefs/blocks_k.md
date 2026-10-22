# U35 block K: comment blocks fit the 120-character count (lead, 2026-10-22)

Read `S/CHECKLIST.md` and `S/u35/briefs/common_u35.md` (Rules, Hand-back, Same-device runs; K has no packet steps, so skip
its Reading part's plan and `steps.py` items), then your section. About 60-80 tool calls: past 80, commit what is done and
hand back the rest (CHECKLIST 21). CHECKLIST 22 (disk) is binding. Batch independent edits as parallel calls (CHECKLIST 17).

## The decision
Owner, 2026-10-21: "6: c", asked "Count a long comment line as several?", option (c): a comment or docstring line counts
its stripped length over 120 characters, rounded up, so a block's weight is the sum (`_block_weight()` in
tests_scripts/test_comment_block_cap.py once `_WRAP_WIDTH` is 120). The cap stays 3. 163 blocks in 147 files go over on the
integration head `bc0d77b`; K brings them to the cap with no meaning change. The lead sets `_WRAP_WIDTH = 120` at the
merge: never edit that constant or the comment above it.

## Start (every K block)
Branch `audit/u35-k<n>` at `bc0d77b`, worktree `S/wt-u35k<n>`
(`git -C /home/user/sensors worktree add -b audit/u35-k<n> S/wt-u35k<n> bc0d77b`), then `S/u23/rebuild.sh S/wt-u35k<n>`.
Logs in `S/u35/laneK/k<n>/`. Files: exactly those in `S/u35/lead/k/k<n>.txt` (path, over-cap block count). Every other
file belongs to someone else, `tests/_sensortask_scenarios.py` included (lane V's, the lead's after its merge).

## Tools (run from your worktree with `/home/user/sensors/.venv/bin/python -I`)
- `S/u35/lead/k/show.py 120 <files>`: each over-cap block in full, every line numbered with its stripped length, then
  `TOTAL`. Your files are done when it prints `TOTAL 0`.
- `S/u35/lead/k/verify.py bc0d77b <files>`: proves a comment-only change. A Python file's AST with docstrings blanked
  must equal the base's; any other file's non-comment lines must equal the base's. It prints every docstring whose text
  changed. It must end `CODE-CHANGED FILES: 0`; save its output as `S/u35/laneK/k<n>/verify.txt`.
- `S/u35/lead/k/measure.py` (`python -I -c "import sys; sys.argv=['m','120']; exec(open('<path>').read())"`): the whole
  tree and the generated modules at 120. None of your files may appear in it.

## How a block is brought under the cap, in this order
1. Rewrap: the prose fits 3 lines of at most 120 characters. Words unchanged, line breaks only.
2. Tighten: shorter wording with no meaning change. Every fact, number, citation (file:line, Part, commit) and owner
   quote stays verbatim. Every actor, date, qualifier ("for now", "until ..."), scope and foreclosure stays too.
   Reworded text with decision vocabulary keeps its actor tag (test_decision_vocabulary.py).
3. Split: only where one block holds two separate topics, a paragraph break between them (a bare `#` line, or a blank
   docstring line). Never one thought cut in two to pass the count. Name each split and its two topics in the hand-back.
4. Move, never drop. Load-bearing detail that still does not fit goes beside the code line it explains, as its own short
   comment, in the same file. Architectural detail reused elsewhere (CLAUDE.md: a SPECIFICATION.md Part, or
   digital_twin/README.md for the twin) is not edited by K. Keep it in the comment by 2 or 3, or write a line under
   `## D` in `S/u35/relay.md`: `<CAPMOVE file:line: the detail verbatim; the Part it belongs in>`. The comment keeps it
   until D2 lands it.
- Never reword or move a directive line: `#!`, `# noqa`, `# type:`, `# pragma`, `# shellcheck`, the `# /// script`
  block, `# @<tag>` lines, `// eslint-...`, `/* eslint ... */`, `// @ts-...`, and JSDoc `@` lines.
- A docstring with a runtime reader changes only as far as the cap needs, and its reader runs after. Module docstrings
  feed `argparse(description=__doc__)` (git grep `description=__doc__` -- ':!arduino'): run that script's `--help`.
  Scenario docstrings are read as goals: scripts/_digital_twin_scenarios.py:209 and
  tests_scripts/test_digital_twin_scenarios.py:371.
- `src/` (LEAD NOTES 7 in `S/u35/lane_plan.md`): keep each block's line count, so the plain mpy-cross output is
  byte-identical. Compile `git show bc0d77b:<path>` saved under `S/u35/laneK/k<n>/base/<path>` and your file, each from
  its own tree root with the same relative path, using `/root/pico-toolchain/micropython/mpy-cross/build/mpy-cross`
  (run it, never write there); outputs go under `S/u35/laneK/k<n>/`; `cmp`. Where a block's line count must change,
  state the moved range, and show `-O3` byte-identical instead: `-O3` stores no line numbers (py/emitbc.c:429-432 of the
  pinned source).

## Checks (on your head, logs under your folder)
- `show.py 120` on your files: `TOTAL 0`; `verify.py`: `CODE-CHANGED FILES: 0`; measure.py: none of your files.
- ruff on your `.py` files; `shellcheck` on your `.sh` files; the 12 commit checks (`S/u24/briefs/common.md`, "Before every
  commit"); the 17 repo-wide scans (`S/u32/briefs/common_u32.md`, "Before your lane's final") once on your final head.
  Plus the reader of each runtime-read docstring you changed.
- Decision (lead, 2026-10-22): K runs no unit, twin or timing files. verify.py's proof that no code changed stands in
  for the file runs, and the W6 gate runs every file on the merged head.
- Commit: subject `U35 lane K<n>: comment blocks fit the 120-character count, no meaning change`. If a block's meaning
  had to change, the body names the change instead (CLAUDE.md's decision-record rule 3).

## Hand-back (at most 35 lines)
The commit. Blocks by kind (rewrapped, tightened, split, moved), with each split and each move named. The verify.txt
path. Any CAPMOVE line. Each check with its exit. Anything you could not bring under the cap, with why. Last: "nothing
of mine is running".

## K1: src/, buildgen/, toolchain/ (24 files, 30 blocks)
The `src/` mpy-cross compare above, every file. toolchain/setup_toolchain.py's change is a comment only (verify.py), so
the installer run CLAUDE.md asks of toolchain changes does not apply; say so in the hand-back.

## K2: digital_twin/, scripts/, tests_hardware/ (37 files, 43 blocks)
`tests_hardware/` only with `pytest --collect-only` on the files you changed. Shell files: `bash -n` as well.

## K3: tests/ (38 files, 39 blocks)
Not `tests/_sensortask_scenarios.py`.

## K4: tests_scripts/ (47 files, 50 blocks)
In tests_scripts/test_comment_block_cap.py, only its module docstring is yours: `_WRAP_WIDTH` and its comment are the
lead's.

## K5: the review-enforced files: JS, CSS, HTML and config (27 files)
Comment content here is held to the cap by review, not by the gate. Same rule and same weight: each comment block's prose
lines (JSDoc `@` lines are not prose), each line weighing its stripped length over 120, rounded up. Your start is the 61
comment lines over 120 characters in `S/u35/lead/k/js_long.txt`; judge each line's block by hand, and list every block you
found over the cap in the hand-back. Checks besides verify.py: `npm run lint`, `npm run typecheck` and
`npx vitest run tests_js/lint-ceilings.test.js`, each in `unshare -n S/u24/ns_xdg.sh`; `actionlint` and
`zizmor --offline` on the changed workflow and action files; `ruff check` on the eight scopes for pyproject.toml.
