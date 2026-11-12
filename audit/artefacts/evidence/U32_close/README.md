# U32 close evidence

What each folder proves (the scan record `audit/sweeps/scan_runs/20261021_U32_close.md` cites them). Logs only:
`assemble.sh` copies each lane's, block's and fix's `*.log`, `*.txt`, `*.out`, `*.tsv` and `*.time` files two levels
deep with the hand-backs, and then deletes every code file it picked up (`*.py`, `*.sh`, `*.js`, `*.mjs`, `*.toml`,
`*.ini`, `*.yml`, `*.diff`, `*.pid`), every empty file and every empty folder. So the lanes' base copies of the files
they changed, their bite trees and their run scripts are not here, nor is any JSON (the twin record's before-image, the
reasons file, the base sweep's raw tables); the record names what each shows. `final_evcheck.py` over `a1bee25` and every commit of `72b1281..a1bee25` (68 revisions, 914 blobs) flags one file, this README by its name, as in every earlier unit; its 151 credential-pattern hits are all names (test names, the word "tokens"), no value. The withheld-value check (two sha256[:8] prefixes against every token of 13391 files: this evidence, `audit/` and BACKLOG.md): 0 hits; its control prefix hits 60 times in `audit/`, so the scan reads them. No credential value: the hotspot
default reads `<row-8-default>` and the bench LAN's third octet `<bench>` in every file here. Files over 20 KB are
gzipped.

- `gates/gate1/`: the gate on `c6b8a07` (U32's integration head before FX8 and FX9): `gate.out` phase A and the first
  phase B, `gate_phaseB2.out` the legs a container restart cut off at 13:34 UTC, re-run on the same commit; the partial logs
  of the cut-off runs in `killed_1334/`, kept unread; generation, lint, ruff and typecheck logs, the collect-only count,
  `gc_default.log` (PASS) and `gc_32768.log` (one red, FX8's), the six `twin_*.log` (all PASS), `npm_test.log`,
  `npm_coverage.log` (one red, FX9's), `npm_static/`, `coverage.log` (PASS) and the `vmstat` samples of both phases.
- `lane_C/`: the supervisor's task names, the end record and `LastTaskEnd` (C1), the generator's collector, `main()`,
  the status field and the catalog row (C2), the per-device scenarios' names, null and kill-one-task assertions (C3),
  the reset and shutdown tasks' tops and the task-top check (C4): each change seen failing, the bites (`bites/`), the
  runs per device at both stages, the JS corpus, definitions and render runs, the readers and scans; the C1 to C4
  hand-backs.
- `lane_U/`: the UART link's three waits naming a dropped frame apart from a silence and the cap's refusal (U1), the
  padding sweep at both stages (U2), the lane's checks (U3): `before`/`after` runs, the bites on the old and new code
  (`bite*_old`, `bite*_new`), the mypy passes; the U1 to U3 hand-backs.
- `lane_W/`: the `lasttaskend` format in the format sets, the renderer, the mock data's compose, coverage and validator
  checks (`after_*`, the bites `bite_*`), the web tier in its own network namespace; the W1 and W2 hand-backs.
- `lane_D/`: README.md's reflash runbook and wording (D1) and SPECIFICATION.md's task names, `LastTaskEnd` and the
  task-top rule (D2): the doc checks per step, the pre-commit checks, the merges, the whole tier on D2's head; the D1
  and D2 hand-backs.
- `lane_T/`: the device scripts' task names and the bench stub (T1), the seven test files and the generic integration
  runner (T2), the lane's checks (T3): the mypy passes before and after, the bench facts, the runs at both stages; the T1
  to T3 hand-backs.
- `lane_L/`: the lead's block L1, the connection task's own top and `start_server()` callbacks in the task-top check:
  the old and new runs (`old/`, `new/`), the bites, the mypy passes, the readers, a profile (`prof.out`); the hand-back.
- `x39/`: the legacy re-check of step 39 (15 functions held, 2 fixed, 2 recorded, 0 unsettled); its trace is the
  hand-back.
- `review/`: the four readers' hand-backs (`RA.md` to `RD.md`) and the lead's rulings (`rulings.md`).
- `fix/`: one folder per fix with its hand-back and logs: `fx1/` (the VOC backup's gate back on the NTP sync and
  `LastTaskEnd`'s text: before and after, seen failing, the bite), `fx2/` (the waits' silence wording and the cap
  comment: the UART comm and link files at both stages), `fx3/` (the kill scenario's restart, the fakes' faults, one
  task-name form, the probes' list order: `before.tsv`/`after.tsv` the 36 timed rows, the bites), `fx4/` (the task-top
  check tightened: base and after runs of the check and the inventory, the generated boot), `fx5/` (the fault-or-warning
  scan's nested try and the renderer's format pin: seen failing, after), `fx6/` (the documents' corrections: the scans),
  `fx7/` (the notification dispatch's try: before and after at both stages, the bite on the old source, the scan before
  and after); the gate's two: `fx8/` (the neopixel tests on the driven clock: the slack probes under load and idle, the
  injected lateness, the bites, the file at both stages), `fx9/` (the shell tests' read wait: the 10 plain and 10 coverage
  runs before and after, the probes, the delayed-read variants, the whole npm suites).
- `lead/`: the checklist, concurrency rules and run record, the lane plan, the relay, the lead's log for the unit
  (`lead_todo.md`, from U31's push entry on), `harness_counts.txt` (the harness's tool-call count per agent, the burn
  the record cites), `base_times.tsv` and `base/` the base sweep on `72b1281`; `plan/` the two planning blocks'
  hand-backs; `ci/` U31's CI job minutes; `tier_889cb5e/` the whole `tests_scripts` tier before the review's fixes;
  `tier_1528dd2/` the whole tier after them (3678, 965, 899 and 1149 passed in its four groups, 9 skipped, each with
  its reason, only `tests_scripts/test_twin_record.py` red before the re-record, 0 memory markers);
  `twin_record/` the re-record on `1528dd2` (`run.log` rc 0; `trace.txt`: 122 results and reasons unchanged, 23
  entries' hashes moved, each traced to a file changed since `72b1281`, 0 untraced, no runner file changed);
  `review_rebuilds/` the generated modules rebuilt on the integration heads; `records/` the records block's hand-back;
  `tier_a1bee25/` the whole tier on the final code head (3678, 965, 899 and 1150 passed, 9 skipped, 0 memory markers).
