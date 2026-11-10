# R1 units: what every unit brief shares (lead, 2026-11-02)

## The idea
You do one unit of `S/u35r/plan/PLAN.md` (read sections 0, 2 and 4; they bind). The unit's action list is your work
list; what is not on it does not change. Work the way the audit's first units worked: tests first, the smallest change,
source, tests and docs in one commit, one gate, a short hand-back. No machinery: no ledgers, inventories or matrices.

## Standing direction
Target low complexity (owner, 2026-11-03: "Generally target low complexity"): of two forms that both hold, take the
one with fewer lines, branches and states. PLAN 0 still holds: nothing proven good goes.
One entry per fault per level (owner, 2026-11-03: "Either it's a warning or a fault applies to the same level / the same
module"): a downstream fault is an error at its level; the level above that handles it and degrades logs a warning.
Every level (owner, 2026-11-07 17:21:06; SPECIFICATION.md Part 0.1): each principle and part of the specification binds
at function, module, import, integration up- and downstream, and full system; check your work from each. Cost against
need (Part D.8): per operation you touch or judge, its physical need against its worst-case cost (largest input, under
load, on silicon) and who waits meanwhile; a cost far beyond its need is a defect at its source, never a fact to
document. A measurement names its condition; a decision names actor, date and its facts, and goes back to its maker
when one fails (P9). Your hand-back states that figure for each operation you changed.
The platform first (owner, 2026-09-26 "perfectly suited for the target hardware"; 2026-11-09): before a Python loop
does byte, bit or arithmetic work, check what MicroPython 1.29 already does in C (binascii, struct, json, deflate,
hashlib, array, bytes/memoryview methods, ...) and its native emitter (viper); a Python loop doing that work is a cost
to justify, never a default. A yield is no fix for a slow step: first ask why the step is slow. The goal (owner,
2026-11-09 19:11:51: "solutions which are minimal and optimal at the same time through smart design"): remove the
cause, so the mitigation built around it (a yield, a lock split, a budget row, a retry) can go with it. And it is
general (owner, 2026-11-09 19:17:45): at micro, intermediate and macro level, for everything, not only CRC, locks or
timing, ask whether a simpler or more efficient solution keeps every gap closed (ideally never opened) and drops no
functionality - it is possible, and it is the default question before any change and in any review.
Ask before removing a feature (owner, 2026-11-09 18:30:08: "Before removing any function which could be a feature
which is just unused, ask me"): a function, method, mode, option or codec with no caller is kept and reported with its
record (git, specification, owner rulings), never removed by a unit; internal mechanism a change replaces may go.
A bound needs a source (owner, 2026-11-09 21:57:36: the LED's give-up "was just one more example of how overkill grew
into the audit"): a timeout, deadline, retry cap, attempt count, expiry or drop exists only where a party outside the
code can fail to answer (network peer, UART peer, a chip the datasheet bounds), the original firmware had it, or the
owner ruled it; a wait on the device's own lock, task or queue gets no deadline (FIFO, never dropped); every bound's
number is derived from its source or named with it, and a give-up is never silent. The tag "owner-reviewed, 2026-11-06" marks an agent decision inside a topic
the owner reviewed at big-picture level ("Single decision is by far to fine grained"): it is no ruling on a number.
Nothing new without a source (owner, 2026-11-09 22:27:31: "what happened in the audit and was added without my consent
and kept growing"): a mechanism you add (a state, code, counter, tunable, check, task, test layer or rule) names the
owner's words for it or its demonstrated need (a reproduced failure, an incident, a datasheet line, legacy behaviour);
without either it is not added. Real features stay, no gap opens or reopens, and the form is lean for the rp2.

## Environment
- S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Your worktree and branch are
  named in your brief; it starts at the integration head.
- Shell setup for every command: `export PATH=S/uvenv/bin:/root/pico-toolchain/node/node-v24.22.1-linux-x64/bin:$PATH
  UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=S/wt-base/.venv; source S/wt-base/.venv/bin/activate` (the run wrapper does it).
- Datasheets: the private repository `hundertvolt/datasheets`, cloned read-only at `/home/user/datasheets/` (every
  chip, the RP2040, W25Q16JV and CYW43439 included, under `pico w/`). A worktree's `datasheets/` submodule is not
  initialised and `/home/user/sensors/datasheets/` is a stale plain folder: never conclude from either that a
  datasheet is missing (owner, 2026-11-04 16:30 UTC: "They are all in the private subrepo and you have access.").
- Every run, a short probe included, goes through `S/u35/lead/run.sh <worktree> <label> "<command>"` (network
  namespace, nice 19, run log lines, a disk check; output in `S/u35/lead/<label>.log`). Prefix labels with your unit.
- One MicroPython test file, both GC stages: `TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen
  S/tc-c/micropython/ports/unix/build-standard/micropython -X heapsize=16M tests/test_x.py`, and the same with
  `tests/_threshold_runner.py tests/test_x.py 32768` as its arguments (`TEST_DEVICE=<device>` for a per-device file).
- Every test file you add or change also runs once under the coverage build (its result gates in CI, owner 2026-09-22):
  the same command with `S/tc-c/micropython/ports/unix/build-settrace/micropython ... tests/_coverage_runner.py
  tests/test_x.py S/u35r/r5/ftmp_<label>/cov.json`; it allocates 4-5x, so a test that needs scale there needs an invariant.
  The settrace binary is `build-settrace` beside it. Whole-tier runs set `PICO_TOOLCHAIN_DIR=S/tc-c`.
- After any `src/`, `buildgen/` or device TOML edit: `S/u23/rebuild.sh <worktree>` before running a test file.
- Lint: `S/u35/lead/lint_direct.sh` from your worktree (after the rebuild). Typecheck: `ln -s S/shared/typings
  <worktree>/typings`, then `mypy --cache-dir=/dev/null`, `mypy --cache-dir=/dev/null --config-file host_typecheck.ini`
  and `mypy --cache-dir=/dev/null --config-file digital_twin/typecheck.ini`; remove the link afterwards (`rm` with the
  literal path, as its own command). `scripts/lint.sh` and `scripts/typecheck.sh` refuse the shared venv.
- The gate (once, on the finished change, in the background, and only when the lead says the host is free: two
  gates at once on this 4-core host fail wall-clock bounds, 2026-11-03):
  `PICO_TOOLCHAIN_DIR=S/tc-c scripts/test.sh` and `PICO_TOOLCHAIN_DIR=S/tc-c GC_THRESHOLD=32768 scripts/test.sh`
  (one after the other, never at the same time as another port-binding run), then
  `scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part suite`, the same with `--part harness`, and both again
  with `--gc-threshold 32768`. A change the website reads
  (`buildgen/error_catalog.json`, an emitter, `js/`, `html/`) also runs `npm run lint`, `npm run typecheck`
  and `npm run test:unit`.
- Sizes for the hand-back: `S/u35r/r0/module_sizes.sh <worktree> <your head> <out .tsv>` (per-module lines and bytecode;
  compare with `S/u35r/r0/mpy/now.tsv`), and `scripts/build_firmware.py dev` (its `.json` record's `imageFreeBytes`; R0:
  43,068 B).

## Rules (with CLAUDE.md, all of it binding)
- Only the owner's words bind; `S/u35r/recovered/owner_rulings_after_LN118.md` holds them since 2026-10-26, verbatim.
- Test first: a behaviour that changes gets its test changed first and seen red; a mechanism that goes loses its pinning
  tests first (list them); a kept behaviour without a test gets one, seen red on a planted break. A failure on a kept
  behaviour is fixed in the code, never in the test (OR12). A test reproducing a failure the device can really meet
  keeps its fix in the smallest form: say so in the hand-back.
- The smallest change; no new hardcoded delay check; no module's bytecode grows except by an admitted fix, stated.
- A catalog code removed before the release leaves no row: no `retired` or reserved entry (owner, 2026-10-28 14:23,
  "third option accepted"); from the release on a removed code keeps its number unused.
- Never open anything under `/root/.claude/`. Never read `arduino/` (`':!arduino'` in every git grep and git log). Never
  edit `ext/`. No real hardware, no `mpremote`, `picotool`, `nmcli`, `iw`, `iptables`; `tests_hardware` only with
  `--collect-only` or `--twin`. Never commit credentials; never write the hotspot fallback password's literal; filter every view or grep of repo text (`devices/*.toml`, generated modules, SPECIFICATION.md, `audit/`, `src/asy_wifi_service.py` included) through `grep -v -i -E "hotspot|passw|psk|ssid|wificonfig|credential"`; never view those whole.
- The credential filter hides every line naming a Wi-Fi field: a hidden line is unread, never evidence of absence.
  Where a claim ("unused", "no caller", "absent") depends on such a line, print only the match of a pattern for the
  identifier (`grep -n -o 'post_fct=[A-Za-z_.]*'`), never the whole line, and say how the claim was checked.
- Never copy source into an evidence or records folder: a scratch copy of any repo file goes only under your own
  `S/u35r/r5/ftmp_<label>/` (the snapshot excludes ftmp_ folders and refuses a credential anywhere else).
- Commit on your branch only, never push. Subject `U35: <summary>`; trailers `Co-Authored-By: Claude Opus 5.5
  <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01BWfjT6GSD7bxCP57j86vB8`. Text outside
  `audit/` cites no audit ID (OR/OF/SF), no lane, unit or plan name. A decision you take gets "(agent, YYYY-MM-DD)".
- Comment blocks at most 3 prose lines (CLAUDE.md); docs: the unit's own lines only (current state, not history).
- Kill by pid only; no `git stash`; `rm` only with literal paths or `"${var:?}"`, as its own command. Keep 3 GB free.
- No failure is called a flake without a root cause. A reproduced failure outside your unit goes to the hand-back,
  marked (a) firmware defect, (b) a defect in your deliverable, or (c) other; you never pursue it.
- Efficiency: read the anchor, then the range; logs by summary and failing block; while fixing, only the failing file
  runs; long runs in the background, waiting for their notice, no polling; the gate once.
- Hand-back: write it yourself to the path your brief names (first line "<unit> hand-back, written by the agent (<date
  -u>)"): per action-list item the outcome and its test (seen red, then green); each removed item's knowledge line (what
  it was, why it went, the commit holding its code); the gate's results; the sizes; decisions you took; findings. Your
  final message: that path, your commits, one line per headline result, and last "nothing of mine is running".
