# R4 phase B, lane C2: tests_hardware/README.md's history pass (lead, 2026-11-05)

## Read first
- `S/u35r/r1/common_r1.md` (binding; your labels start with `r4C2_`).
- `S/u35r/r4/ROWS.md` row 1 (OR27.a) and lane A's brief `S/u35r/r4/BRIEF_LA.md` (its OR27.a rules and runs bind you).
- `S/u35r/r5/INVENTORY.md`: the rows citing `tests_hardware/README.md` (open findings R5 will close).

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## Where you work
- Worktree `S/wt-r4c2`, branch `audit/r4c2`, at `74c7b21b`. Commit locally, never push.
- You write `tests_hardware/README.md`; plus, only where you rename a heading they cite, the citing words at
  `BACKLOG.md:36`, `BACKLOG.md:140` and `SPECIFICATION.md:5674` (nothing else in those files).

## The job
Lines 1088-1990: "Known assumptions and open findings" and the eight sections "Third pass" to "Tenth pass". R4's
marker grep missed them; they narrate audit passes ("Asked directly ...", "Answer at the time", "Fixed this pass",
test counts over time, who found what).
- **Keep:** what each test covers and its file; every standing rule with one short reason and its "(owner, date)";
  owner words verbatim; bench facts that are still true (check each against the tree, file:line); every open finding,
  its substance unchanged (R5 closes them, not you).
- **Go:** the narrative, the per-pass framing, superseded counts, run IDs, "used to", and any fact this file or
  SPECIFICATION.md already states elsewhere (point to it instead).
- **Headings:** a pass heading becomes a topic heading, or its content folds into an existing section of this file.
  "Known assumptions and open findings" keeps its title (cited from code and audit records).
- A rule that looks drifted is not reworded: list it.

## Checks, size, budget
- At most five runs through `S/u35/lead/run.sh S/wt-r4c2 r4C2_<label> <cmd>`: the citations, decision-vocabulary and
  THR-facts tests in `tests_scripts/` (allow-list-only failures expected: list them), and a link check of the
  headings you renamed (`git grep` for each old title).
- Size: aim at -300 or more; stop and say why if your additions pass +80.
- Budget: about 0.8 % of the week. Stop at a clean commit when you reach it.
- Never read `arduino/` (`':!arduino'` in every git grep/log); never open `/root/.claude/`; no hardware; `rm` only with
  literal paths, as its own call.

## Report
At most 20 lines: commits, lines in/out, each old section's fate (kept as / folded into / removed because), facts
checked, drifted rules listed, checks with expected failures. Last line: "nothing of mine is running".
