# Mutation testing pilot: the brief for a fresh session

**Status: on hold.** Do nothing until the owner gives the go in this session. Before the go: no runs, no reads
beyond this file, no agents, no scheduled check-ins. After the go, follow this brief to its stop point and report.

## The owner's words, verbatim (owner, 2026-11-18)

- 09:15: "Select and use a fitting, common CI tool for mutation runs. Add it to our pyproject.toml" - "measure how
  long our suite currently runs, ... identify and fix time hogs, inefficiencies, unnecessary work, potential speedups
  like preloading, reusing, caching etc. and speed up our pipeline with zero reduction of the test depth" - "Identify
  if there are tests like error planting or related, which might become obsolete with mutation tests ... and if they
  can be removed with zero loss of test depth" - "the framework supports immediate return at the first failed tests,
  so that already killed mutants do not consume any time" - order: four runtime quartiles, "within each quartile
  individually, we sort the tests by "the one with the highest killing rate first"" - "adaptive order - ... The tool
  remembers which file killed the last mutant of each function and tries that file first, then the rest by time" -
  "Once we have the figures about these tests, we decide if we add it as a regular or optional step to the Git CI,
  come back at me then."
- 09:17: "if the timespan evaluation is badly scaled if linear, you can also use a log scale"
- 09:27: "It will be part of the 2.0 release. But the implementation shall be in a new branch off the audit branch,
  with a PR to the audit branch." - "Real gaps only, and if there are mutants which you can rate as equivalent without
  further consequences (like your 1000 vs 1001 ms example), they do not need a test to be killed but will be
  whitelisted as allowed. Any surviving mutant shall be checked for this, every surviving mutant is a hint for a gap,
  not a proof, and only those which turned up a real, proven, reproducible gap get a test." - "I already experienced
  mutation tests turning up more efficient equivalents in their survivors. That may also be a chance for improvement,
  keep eyes open for this."
- 09:36: "I switched back to "Max" plan, so the available budget is cut by half!"
- 09:39: "KEEP IT ON HOLD that it does not use budget yet, and everything I need to do when the time has come is to
  give it a go."
- 09:52: "if you identified and proved a mutant being a true, harmless equivalent which will always run to the end,
  never reporting any failure and not being an issue, add it to the allowlist so it does not consume time without
  added value."

The standing rules apply in full: CLAUDE.md, SPECIFICATION.md Part 0's "Restraint in practice" paragraph, and the
skills in `.claude/skills/`. In short: real, verified findings only; root causes, no runaway chains; no drift into
fixing tests beyond what this brief asks; keep good working tests; ask before removing anything that could be a
feature; a later clear owner decision supersedes an earlier rule.

## Facts already established (do not re-derive)

- Tool: Cosmic Ray (PyPI `cosmic-ray`, 8.9.0 on 2026-11-10). mutmut was ruled out: it runs pytest inside CPython
  only, and the firmware tests run under the MicroPython Unix port. Cosmic Ray runs any `test-command` per mutant
  (exit 0 survived, anything else killed, a timeout killed), mutates the file in place and restores it, keeps a
  resumable session database, runs in parallel through HTTP workers (one git clone each), and skips mutants through
  filters (`cr-filter-operators`, `cr-filter-git` for changed lines, and small custom filter programs). Its docs
  host, cosmic-ray.readthedocs.io, is allowed in this environment.
- The test command learns nothing about the active mutant from Cosmic Ray; read it from `git diff -U0` (one file, one
  changed line), then map the line to its function.
- Size (scan only, release tree): `src/` 31,502 mutants, of which 17,182 swap every binary operator for every other;
  `buildgen/` 5,260. Pilot modules: `src/asy_config_manager.py` (1,059 mutants with the full operator set) and
  `buildgen/schema_ast.py` (232).
- Per-test-file line coverage already exists: `tests/_coverage_runner.py` traces one test file per run and writes the
  lines it ran (`scripts/_render_coverage.py` merges them; SPECIFICATION.md Part E.5). `tests/microtest.py` has no
  stop-at-first-failure yet. `scripts/test.sh` reports no per-file wall times. The machine has 4 cores.
- Budget yardstick: the 2026-11-13 scan and fix round used about 5.1 million agent tokens. The pilot target is 1.2 to
  2.2 million, the low end by the choices below.

## Work, in order

1. **Set up.** `uv sync`; build the toolchain the way `scripts/test.sh` does on a first run (`PICO_TOOLCHAIN_DIR` as
   in its usage text). Add `cosmic-ray` pinned exactly to `pyproject.toml`'s dev group, run `uv lock`, `uv sync`, and
   add the change to BACKLOG.md's list of build-environment changes for the owner's next chroot run.
2. **Measure.** One run of `scripts/test.sh` at the default and one with `GC_THRESHOLD=32768`, with a wall time per
   test file (a wrapper or the runner's own output, no product change), and `pytest --durations` for
   `tests_scripts/`. Read the CI job times of run 43441593022 (27 jobs, green). Write a short table: total, top 15.
3. **Speed hogs.** Fix the top three to five only, with the same tests and the same assertions, both GC stages
   green before and after, times measured. Report each hog's saving. Anything larger goes to the owner as a proposal.
4. **The runner.** One small test command plus Cosmic Ray's configuration, in the repo's existing style:
   - the mutated file and line from `git diff -U0`, the function from the module's AST;
   - candidate test files: those whose per-file coverage contains the line (a mutant on an uncovered line costs no
     run and is reported as untested code);
   - order: log-scale runtime quartiles (fastest first), within each the highest kill rate first, and the file that
     killed the last mutant of the same function before all others; kill counts and the last killer live in one
     local, git-ignored state file;
   - stop at the first failing file, and inside a file at the first failing test (a small opt-in switch in
     `tests/microtest.py`); a per-file timeout derived from its measured runtime;
   - the stripped copy the unit tier imports (`build/portable_src`) refreshed for the mutated file only;
   - the allowlist of equivalents: one file read by a small custom filter that marks its entries skipped right
     after `cosmic-ray init`, so a proven equivalent never runs again; each entry keyed by module, function,
     operator and the mutated text (never a line number), each with a one-line reason;
   - a reduced operator set (for example `+`/`-`, `*`/`/`, `&`/`|`, comparison boundaries and negation) through
     `cr-filter-operators`, kept only if the pilot shows it finds every gap the full set finds.
   Port-binding test files must not run at the same time in parallel workers: reuse the repo's port lock
   (`scripts/_port_lock.sh`).
5. **Pilot.** Run both pilot modules; run the config manager with the full and with the reduced operator set. Replay
   the recorded results to compare the owner's order with a runtime-divided-by-kill-rate order. Long runs go in the
   background; read summaries only.
6. **Triage every survivor.** A true, harmless equivalent, proven (it always runs through every candidate test
   without a failure and is no issue): an allowlist entry with its reason, so later runs skip it (a class of them,
   such as plus or minus one on a timing constant, may be one rule). A hint of a gap: reproduce it. Only a real,
   proven, reproducible gap gets the smallest test, in an existing test file. A survivor that shows a simpler or
   cheaper equivalent form of the code: list it as an improvement candidate for the owner, do not change it.
   Also list tests that plant faults into product code only to show another test catches them (mutation testing
   replaces those); tests that inject a hardware fault test real error handling and stay. The owner decides removals.
7. **Stop and report** in the PR body and to the owner, in plain lines: hours of machine time, mutants run, kills by
   position in the order, survivors, gaps found and tested, equivalents allowlisted, improvement candidates, planting
   tests found, the speed-hog savings, this session's agent tokens if visible, and an estimate of time and budget
   for the full run. Then wait. The full run, the docs and the skill update, and the CI question come after the
   owner's word.

## How to work

- Branch `claude/mutation-testing` (off `claude/whole-project-audit-plan`); its PR into the audit branch is a draft.
  Commit with the attribution trailers your system prompt gives; never merge; never push to another branch except
  the owner-words record below.
- Lean on budget: work yourself, at most one agent (for the runner, if at all); no parallel lanes; background runs,
  summaries only; no polling loops and no scheduled check-ins.
- Questions to the owner: one at a time, in a few plain lines, with one recommendation; never the question tool.
  Record every owner word verbatim with its real `date -u` time (taken in a separate call first) in
  `audit/artefacts/evidence/U35_close/redo/recovered/owner_rulings_after_LN118.md` on branch
  `claude/u35-audit-archive` (a fast-forward commit).
- Secrets: filter every view or grep of repo text through
  `grep -v -i -E "hotspot|passw|psk|ssid|wificonfig|credential"`; never view whole `devices/*.toml`, the generated
  modules, SPECIFICATION.md, CLAUDE.md, BACKLOG.md, README.md or `src/asy_wifi_service.py`; a line the filter hides
  is unread, never evidence of absence. Before each push, no added line of the diff may contain one of those
  words (a quoted copy of this filter aside); if one does, stop and ask.
- Never read `arduino/` (add `':!arduino'` to every `git grep`, `git diff` and `git log`), never edit `ext/` or the
  legacy tree, no real hardware or hardware tools from this session. Comment blocks at most three lines; no review or
  audit IDs in repo text; product checks never weakened; the UART wire format untouched.
- A red in a test you did not touch: record it and rerun it once; do not fix it unless it blocks a verdict on the
  firmware or the build generator.
- Delete this brief in the commit that delivers the pilot report; its content then lives in the PR and the report.
