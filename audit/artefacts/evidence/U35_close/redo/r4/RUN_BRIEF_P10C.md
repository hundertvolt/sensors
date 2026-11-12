# OR10.b proof run 3: build the SGP40 module from the datasheet and the owner record (lead, 2026-11-05)

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## What this is
The repository's new-module procedure is SPECIFICATION.md Part K (with K.0, the owner-discussion stage) and the skill
`.claude/skills/integrate-module/SKILL.md`. This run proves it: you build a complete module by that procedure, in a
throwaway tree that does not contain it. The tree is `S/p10/sgp40/tree` (its own git repository, one commit; it is
this project with the SGP40 module removed). K.0's output is already written: `S/p10/sgp40/BRIEF.md`, the
record of the owner discussion. The datasheet is `/home/user/datasheets/sgp40/`. The wiring device is `dev`.

Build the module the way the procedure says, through every tier it names and the firmware build. The tree's own
`CLAUDE.md` binds you as it binds any session in this repository.

## Isolation (binding; the result is worthless without it)
- Read only: the tree, `/home/user/datasheets/` (the chip's folder, and any other folder the procedure sends you to),
  `S/p10/sgp40/BRIEF.md`, this file, and the logs of your own runs.
- Never read anything else under S, `/home/user/sensors/`, any other worktree or repository, or any git history but
  the tree's own. No web search for driver code; only MicroPython's and Microdot's own documentation.
- Where the procedure is silent, unclear or wrong, or the brief does not answer a question: decide as the procedure's
  smallest form suggests, record it in your procedure log, and go on. Nobody is available to ask.
- Nothing leaves the tree. Commit in its own git as you go; never push, never copy into another tree.

## Environment
- Every shell: `export PATH=S/uvenv/bin:/root/pico-toolchain/node/node-v24.22.1-linux-x64/bin:$PATH UV_OFFLINE=1
  UV_PROJECT_ENVIRONMENT=S/wt-base/.venv; source S/wt-base/.venv/bin/activate` (with S spelled out).
- Every run goes through `S/u35/lead/run.sh S/p10/sgp40/tree p10c_<label> "<command>"`; its output is
  `S/u35/lead/p10c_<label>.log`.
- After any `src/`, `buildgen/` or device TOML edit: `S/u23/rebuild.sh S/p10/sgp40/tree`.
- One MicroPython test file: `TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen
  S/tc-int/micropython/ports/unix/build-standard/micropython -X heapsize=16M tests/test_x.py` (and with
  `tests/_threshold_runner.py tests/test_x.py 32768` as arguments for the second GC stage; `TEST_DEVICE=dev` for a
  per-device file). Lint: `S/u35/lead/lint_direct.sh` from the tree. Typecheck: `ln -s S/shared/typings typings`,
  the three mypy passes with `--cache-dir=/dev/null` (plain, `--config-file host_typecheck.ini`,
  `--config-file digital_twin/typecheck.ini`), then remove the link.
- The fast gate: `S/p10/gate_proof.sh dev S/p10/sgp40/g<N>` from the tree (lint, mypy, the unit tier at both GC
  stages, tests_scripts, the dev firmware with its `imageFreeBytes`, the web unit tests). The formal end: the fast
  gate once more, then `PICO_TOOLCHAIN_DIR=S/tc-int scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part suite`,
  the same with `--part harness`, both again with `--gc-threshold 32768`, and `tests_hardware` with `--collect-only`.
- **The host's heavy slot:** before the fast gate, a twin-tier run or a firmware build, check that
  `S/u35/lead/heavy.lock` does not exist; then create it, run, and remove it (`rm` with the literal path, its own
  command). While someone else holds it, work on with single-file runs.
- A test that fails in the baseline before your first change: record it in your log, leave it, report its state at
  the end. The tree's `datasheets/` is a plain folder standing in for a private submodule: never commit a PDF there.

## Hard rules
No real hardware, and no mpremote, picotool, nmcli, iw or iptables. Never edit `ext/`; never read `arduino/` (put
`':!arduino'` in any git grep). Never open `/root/.claude/`. No `git stash`; `rm` only with literal paths, each as its
own command. Never write a credential. Never regenerate an allow-list: your new text passes the checks as written.

## Budget
About 2 % of the week, roughly four hours of your own work. At 80 % of it, stop at a clean commit and report what you
have: a partial run with its procedure log still counts.

## Report: `S/p10/sgp40/HANDBACK.md` (at most 60 lines), and return its path
1. The tree's commits and the files written or changed, per tier.
2. The gate results, step by step, and dev's `imageFreeBytes`.
3. **The procedure log (the main product):** every place where Part K, K.0 or the skill was missing, unclear,
   contradictory or wrong, or made you guess or look beyond it. For each: the Part K item or skill step, what happened,
   and the sentence that would have prevented it.
4. The questions BRIEF.md left open, and what you decided.
Last line: "nothing of mine is running".
