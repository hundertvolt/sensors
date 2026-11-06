---
name: work-routines
description: Everyday checks and log reading in this repository, for a code session and a bench session alike. Use it whenever you run or read any check here (lint, the three mypy passes, the unit tier at both GC stages, one MicroPython test file, a tests_scripts selection, the twin CI, npm, tests_hardware collect-only, the firmware size), whenever you need the verdict of a long test, twin, bench or board-console log or a saved GET /status errcount, and before you diagnose any failing run. It runs checks with one-line verdicts (scripts/_run_checks.sh), reads any log down to its deciding lines (scripts/_log_verdict.py), digests and diffs errcount saves (scripts/_errcount_digest.py), builds rerun selections (scripts/_failed_tests.py), and holds the known-symptom table and the rules that keep coming back. Bench work is bench-routines; setup and cleanup are tree-care.
---

# Work routines

A check here prints up to 25,000 lines; its answer is a dozen. Keep the dozen in front of you and the rest in log
files, and reuse what earlier sessions already found instead of deriving it again. The four helpers live in
`scripts/`, under the same lint, type and comment gates as every script there; `references/` is beside this file.
Run everything from the repository root with its venv active; `scripts/_preflight.sh` (the `tree-care` skill) says in
seconds whether this tree can run its checks at all.

## Run checks: `scripts/_run_checks.sh`

`scripts/_run_checks.sh [-d LOGDIR] STEP...` runs the steps one after another. Each step's whole output goes to its own
log (default `${TMPDIR:-/tmp}/sensors-checks/<UTC stamp>/`); the terminal gets one line per step and the step's
verdict:

```
fw:dev rc=0 43s log=/tmp/sensors-checks/20261106T221500Z/04_fw_dev.log
  == Image: 1169260 B of 1228800 B before the filesystem (95.2 %), 59540 B free
```

| Step | What it runs | Wall time measured on 4 x86 cores |
|---|---|---|
| `lint` | `scripts/lint.sh`: ruff, shellcheck, actionlint, zizmor, the two grep guards | under 1 min |
| `typecheck` | `scripts/typecheck.sh`: the main, twin and host mypy passes | 1-2 min |
| `unit` / `unit-gc` | `scripts/test.sh` at gc -1 / `GC_THRESHOLD=32768`; each includes `tests_scripts` and the scenarios | 12 min each |
| `cover` | `scripts/test.sh --coverage`: its test result gates, its coverage figure does not | about 15 min |
| `twin[:DEV]` | `scripts/run_digital_twin_ci.sh DEV` (default `dev`), both GC stages, both parts | 25 min |
| `npm` | `npm run lint`, `typecheck`, `test:unit` | 3 min |
| `collect` | `pytest tests_hardware --collect-only`: no board contact | seconds |
| `fw[:DEV]` | `scripts/build_firmware.py DEV` and its `== Image:` free-bytes line | 1 min |
| `mpy:FILE` | one `tests/test_*.py` under the Unix port at gc -1, then 32768, as test.sh runs it | seconds |
| `py:ARGS` | `python -m pytest -q ARGS`, e.g. `'py:tests_scripts/test_citations.py -k readme'` | seconds |

Pick by what changed, cheapest first, and run the full set once before anything is merged:

- Any change: `lint typecheck`.
- A file under `src/` or `tests/`: `mpy:tests/test_<module>.py` at once; `unit unit-gc fw` before merging.
- Anything a twin boots (`src/`, `digital_twin/`, `buildgen/`, `devices/`): add `twin`.
- `js/`, `html/`, `tests_js/`: `npm`. `tests_hardware/`: `collect`.
- `scripts/`, `toolchain/`, `buildgen/`, `tests_scripts/`: the matching `py:tests_scripts/...` file first, then `unit`.
- Docs only: `py:tests_scripts/test_citations.py py:tests_scripts/test_comment_block_cap.py
  py:tests_scripts/test_decision_vocabulary.py`.
- Full local gate: `lint typecheck unit unit-gc twin npm collect fw`, about 55 minutes; a Pi 4 takes longer. CI
  adds `cover` and runs `twin` and `fw` for all six devices: a change is green only on its head commit's CI.

While checks run:

- Start long runs in the background and read only the runner's lines; open a log at the line the verdict names.
  To act on the first failure rather than at the end, follow the step's log with a monitor tool:
  `tail -n0 -F LOG | grep --line-buffered -E 'FAIL|ABORT|Result: FAIL|memory allocation failed|MemoryError'`.
- `unit`, `unit-gc`, `cover`, `twin` and `npm` bind fixed ports. Another session's run makes them refuse with
  `port <p> is held by <runner> (pid <pid>)`: wait for that run to end, do not retry in a loop.
- Do not edit tracked files while a gate runs; its verdict would describe a tree that no longer exists.
- A red test is a regression until a root cause says otherwise. `Passed only on retry` is a finding, not a pass.

## Read logs: `scripts/_log_verdict.py`

`python3 scripts/_log_verdict.py LOG...` prints, per log: every runner summary block (SPECIFICATION.md E.10) as one line
when it passed clean, in full when it did not (skip and deselect lists folded to counts, long lists cut); the
`== Test parallelism:` and `== Image:` lines; mypy, ruff and collect totals; the pytest total and its `FAILED`/`ERROR`
lines; failing test-file closing lines; every unquoted `MemoryError` or `memory allocation failed` with its line
number; and the twin shutdown lines: the largest feed gap among runs whose watchdog never fired against the 75 %
share, the line of each run past it, and how many runs' watchdog would have fired (on purpose in a starvation run).
In a log with no summary block, such as a board console, it also counts `Unhandled exception`, `Traceback`, `UART
error` and `Resync` lines. Given a directory it reads every `*.log`, `*.out` and `*.txt` below it and shows only the
notable files, with a count line (`--all` shows all); given `-` it reads standard input, so a bench log is read
straight from its branch: `git show <ref>:<path> | python3 scripts/_log_verdict.py -`. Exit 0 when nothing is
notable, 1 when something is.

```
PASS scripts/test.sh | L0 PASS · L1 PASS · L2 PASS (...) | -1 (reactive default) | files: passed 137, skipped 80, deselected 6; ...
== Test parallelism: 16 (4 usable cores x 4, interpreter speed probe 50ms)
twin shutdown lines: 6; largest feed gap 30 of 8000 ms (0%) where the watchdog never fired; above 75%: 0; ...
```

After it names a line, read around that line only (`sed -n 'A,Bp' LOG`), never the whole log. A memory-marker hit
can be a test's own fixture text: read the line before you call it a failure.

## Read error logs and rerun failures: `scripts/_errcount_digest.py`, `scripts/_failed_tests.py`

- `python3 scripts/_errcount_digest.py STATUS.json` prints one line per error source that logged anything, from a saved
  `GET /status` body: `UART_init counter=28 history=E22,E81,...`. With a second, later save it prints only the
  sources that changed between the two and marks a table cleared in between: the way to tell what a run added
  from what was already there. A repeated code raises the counter without a new history entry, so read both; a
  `ResetErrors` clears every source at once. The harness's exact gain rule is `tests_hardware/error_log_helpers.py`'s
  `gained_entries()`.
- `python3 scripts/_failed_tests.py RECORD` turns a pytest run record (a hardware runner's lands in
  `build/archive/<runner>/<UTC>/run_record.json`) into the `-k` that reruns its failed and errored tests;
  `--nodeids` lists them exactly. Never type a rerun selection by hand.

## Before diagnosing a failure

Read `references/symptoms.md` first. Most failures that look new here were met before; each row has the one check
that confirms the known cause. On real hardware or in the twin, read and save `GET /status`'s `errcount` (the
FRAM-backed error logs) before anything clears it: a reset of the logs cannot be undone.

## Rules that keep coming back

Each is enforced by the named gate unless it says none; the full text is in CLAUDE.md.

- Comments: one header block per file, every block at most 3 prose lines (`test_comment_block_cap.py`). No
  `ruff format`; line breaks are hand-chosen.
- Types: `X | Y`, never `Union` (ruff UP007). No `type: ignore[method-assign]` in `src/` (lint.sh). `# noqa: E402`
  only after a statement other than `sys.path` setup (RUF100).
- Memory: zero `MemoryError` and zero `memory allocation failed`, caught-and-logged included, at gc -1 first and
  then at 32768 (test.sh, the twin CI, the hardware gates). `gc.collect()` only at the boot placement reset (lint.sh).
- asyncio: a test helper that calls `asyncio.run()` is called from the synchronous test body, never from a coroutine.
- Hardware: only with the owner's go-ahead given in this session's own conversation. Without it: `collect` and
  `pytest tests_hardware/flash --twin` only; no `mpremote`, `picotool`, `nmcli`, `iw` or `iptables`.
- Wear gates deselect rather than skip: `--allow-flash-cycle`, `--allow-persistence-write`,
  `--allow-scd30-extra-write`, `--soak-duration`, `--allow-multi-day-rollover`, `--allow-neopixel-sweep`,
  `--allow-toolchain-reverify`. A clean verdict means everything that ran passed; read the deselected count.
- Decisions are written "(owner, YYYY-MM-DD)" with the owner's own words quoted (`test_decision_vocabulary.py`).
  Docs hold the current state, not the path to it; a resolved BACKLOG item moves out (no gate).
- The UART wire format is a contract with a C peer: every change gets an entry in `UART_C_PORT_CHANGELOG.md`.
- Never edit `ext/microdot.py` or anything under `legacy/`. Never commit a credential or copy the hotspot fallback
  literal anywhere.
- A change to the build environment gets a line in BACKLOG.md's clean-chroot list.

## Bench work, setup and cleanup

The `bench-routines` skill holds the bench's order of work, its board-control index and the hand-back format; a code
session reads it before writing a relay or reading a hand-back. The `tree-care` skill sets a tree up, checks it
(`scripts/_preflight.sh`) and reports and clears space (`scripts/_tidy.sh`).

## Working with the owner

- Take every clock time from a real `date -u` reading, never from memory or an estimate.
- Record the owner's words verbatim, with that time and the topic, wherever the session keeps its rulings.
- Ask one question at a time, in prose: the facts, the options with their consequences, what each touches, and a
  recommendation. No multiple-choice question tool for complex topics.
- Bring only what shows in operation, in operational terms. Say when a figure is near a critical margin. Do not
  offer a technical necessity as a choice.
- Show any message meant for another session to the owner in a copy-paste code block.
- No scheduled check-ins or wake-up loops unless the owner asks for them.
