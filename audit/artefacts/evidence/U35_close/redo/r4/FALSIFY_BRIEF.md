# R4 falsification brief (lead, 2026-11-05)

Your job: try to REFUTE the claims below about `837697e9` (R4, the documentation round: lanes A, A2, A3, B, C, C2 and
lead commits on base `33974760`; pre-audit `25caf528`). You get the claims, not the reasoning behind them. A claim
stands only if you could not break it; say how hard you tried. Also look for a lost rule or feature, a weakened check,
or a fact now stated wrongly, in the changed files (`git diff --stat 33974760 837697e9 -- ':!arduino'`: 27 files,
+2,374/-2,813). Chip facts: datasheets at `/home/user/datasheets/` (document, page, table); MicroPython and pico-sdk
under `/root/pico-toolchain` (file:line); say where you took any other fact from.

- Read-only worktree `S/wt-r4f` (detached at `837697e9`, `node_modules` linked); S =
  `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. You may plant a temporary
  break there to test a claim, then restore it (`git -C S/wt-r4f checkout -- <path>`). Never commit, never push, never
  touch any other worktree.
- `S/u35r/r1/common_r1.md` gives the environment, the run wrapper (`S/u35/lead/run.sh`, labels `r4f_`), the one-file
  test commands and `S/u23/rebuild.sh <worktree>`; its binding rules apply. Single test files only, at most eight runs,
  one after another. Never open `/root/.claude/`. Never read `arduino/` (`':!arduino'` in every git grep and git log).
  Keep any extract out of `S/u35r/` except under `S/u35r/r4/f/ftmp/`, deleted before you hand back.
- The owner's words: `PROJECT_AUDIT_PLAN.md` (owner rows) and `S/u35r/recovered/owner_rulings_after_LN118.md`.

## Claims
1. **No rule lost.** Every rule CLAUDE.md held at `33974760` still holds at `837697e9`, in CLAUDE.md or by a pointer to
   where it now stands, with its meaning unchanged (`S/u35r/r4/LEDGER_B.md` maps them). Pick the ten rules you judge
   most likely lost or weakened (hard rules first: hardware go-ahead, dead-man's switch, br0 MAC, FRAM logs before
   clearing, credentials, loop blocking, the memory gates, wear, `_boot.py`, vendoring, hazard tiers) and try to show
   one gone or changed in meaning.
2. **Owner words.** Every changed line carrying "(owner, <date>)" either quotes the owner verbatim or states what the
   owner decided; text that is not the owner's is marked "(agent, <date>)" or "(lead, <date>)". Sample twenty such
   lines in SPECIFICATION.md, CLAUDE.md, README.md and tests_hardware/README.md and check each against its source.
3. **Facts.** Every file:line, constant name, number and path in the added doc lines matches the tree. Pick the
   thirty you judge most likely wrong (moved lines, renamed constants, counts) and check each.
4. **No history.** The changed docs hold facts, rules and agreements: no incident story, "used to"/"no longer" outside
   a current fact, who-found-what, run IDs or test counts over time. Find the ten worst remaining instances in the
   changed regions (unchanged regions only as a listed note).
5. **README CLI reference.** Each `<details>` section lists exactly the options its tool's `--help` gives;
   `tests_scripts/test_tool_help.py` fails on a removed option row and on an option added to a tool but not to README
   (plant both).
6. **The one checklist.** SPECIFICATION.md Part K is one ordered checklist opening with K.0 (the owner-discussion
   stage and its record), every step marked "every module" or "a sensor driver"; `.claude/skills/integrate-module/
   SKILL.md` is at most 30 lines, names the inputs, points into Part K and restates none of its steps; no doc outside
   `audit/` still calls Part D "the checklist" for adding a module.
7. **Headings.** SPECIFICATION.md's heading changes are only: Part 0 added, K.0 added, I.6 moved to the end of Part I
   with its number and title, E.2.1-E.2.3 under E.2 with the new E.2.2. tests_hardware/README.md's renamed sections
   are cited nowhere outside `audit/` by an old title. Every in-repo citation of a SPEC Part or section number outside
   `audit/` resolves to a heading that exists.
8. **Code untouched.** `src/` changed one comment block (`src/asy_uart_driver.py`) and its frozen bytecode equals
   `33974760`'s; `js/templates.js` and `html/style.css` changed comments only; every other `.py` change is a comment;
   the UART wire format is untouched; no comment block exceeds 3 lines.
9. **Allow-lists.** `tests_scripts/_citation_allowlist.txt` and `_decision_vocab_allowlist.txt` only lost entries
   (66 and 24) and every removed entry's sentence is gone from the tree.
10. **Nothing else.** Text outside `audit/` cites no audit IDs, lanes or unit names.

## Hand-back
Write `S/u35r/r4/FALSIFY.md`, first line "R4 falsification, written by the agent (<date -u>)": per claim STANDS or
REFUTED, with file:line evidence (and the planted break or run label where you used one). Then any defect found
outside the claims. Your final message: the path, one line per REFUTED claim, last "nothing of mine is running".
Budget: about 1 % of the week.
