
######## SubagentHandback 2026-10-13T15:55:37.541Z
WIP f5c6db2 (audit/u24-s, base e75d363). Files: new scripts/_port_lock.sh (100644, sourced), new tests_scripts/test_port_lock.py (20 tests), scripts/_render_coverage.py (one line). Steps: 2 M.SCR.012 applied as the library only; the takers come after <API>. 351 M.TSC.206 partly: its U24 stage is the bash cases. The CPython reader is U27, the JS cases are J's, and the runner case comes with step 73.
I could not write the record to S/u24/laneS/report.md because the harness blocks subagent report files. The evidence logs are in S/u24/laneS/: sff_*.log, bites_s1.log, host_mypy_{before,after}.log, precommit_s1*.log and s1_*.log.

Lock contract as landed (for J):
- Path: `${XDG_RUNTIME_DIR:-/tmp}/sensors-port-<port>.lock/`, made by `mkdir`. The taker writes the `runner` file first, then `pid`, each as `text\n`, and re-reads `pid` to confirm it is its own.
- Refusal: if the recorded pid is alive (`kill -0`, or `/proc/<pid>` exists when kill gets EPERM), the taker exits 1 with stderr `port <n> is held by <runner> (pid <p>) - run the suites one after the other (CLAUDE.md)`.
- Exceptions: the taker passes if the pid is its own (re-entrant), or if the pid is in SENSORS_PORT_LOCK_OWNER and <n> is in SENSORS_PORT_LOCKS_HELD.
- Env: on a fresh take, the port is appended once to SENSORS_PORT_LOCKS_HELD and the taker's pid once to SENSORS_PORT_LOCK_OWNER. Both are exported space-separated lists (the owner chain, not a single `$$`; otherwise a grandchild is refused, which a test pins).
- A missing, empty or non-numeric pid file is waited for (20 × 50 ms), then treated as dead.
- Stale takeover: only the process whose `mkdir <lock>/takeover` succeeds clears the lock. It re-reads the pid with the same wait and backs off with `rmdir` if the holder is alive. Otherwise it renames the lock to `<lock>.stale.<pid>`, removes that, and everyone retries `mkdir`.
- After 10 failed attempts the taker exits 1: "port <n>: its lock <dir> could not be taken in 10 attempts - if no runner holds the port, remove that directory".
- Release: `port_lock_release_all` runs from the runner's one EXIT trap. It renames each lock whose pid equals `$$` to `<lock>.released.<pid>` and removes it; bash runs that trap on SIGTERM too.
- Usage errors exit 2: a port outside 1-65535, an empty runner name, or a lock root that is not a writable directory.

Seen failing first:
- Module absent: 20/20 fail ("No such file or directory").
- No-op stub, modelling today's tree with no lock: 16/20 fail. `test_a_second_runner_on_a_held_port_exits_1_naming_the_holder` fails at `assert second.returncode == 1`: it got 0 and stdout 'proceeded', so both runners proceed. Four tests pass against the stub and are guards.
- Nine planted bites (scratch copies, nothing committed) each turned 1-4 tests red. They cover: the chain ignored, the HELD check dropped, the owner overwritten, release removing everything, a dead pid read as alive, no pid wait, no takeover claim (caught by the FIFO swap test), and no re-check after the claim.
- The lead's start-commit consequence: the host pass was red with `scripts/_render_coverage.py:15: error: Unused "type: ignore" comment [unused-ignore]`; after the fix it reports "no issues found in 205 source files".

Checks, all green:
- `test_port_lock.py`: 20 passed in 3.3 s (own namespace, nice 19).
- Before-times, both files unchanged: `test_test_sh.py` 113 passed in 27.0 s, `test_render_coverage_anchors.py` 0.04 s. These are pytest files, so no GC stages apply.
- The 12-file pre-commit set: 618 passed. After the ignore removal, the five checks that could move (Any baseline, lint ceilings, render anchors, host annotations, import placement): 46 passed.
- ruff, shellcheck and the host mypy pass are clean.

Red checks: none.

Runs: rebuild rc 0 (pid 25369; its done line is RUNS.md:657, appended at 15:34 as soon as it exited), pre-commit pid 17818 rc 0, the 5-file check rc 0, and the three timed files rc 0. Nothing of mine is running.

Facts owed:
- J: the contract above.
- X and Y: none at S1 (no taker yet). No @tunable added.
- Lead: no allow-list, `_NOT_YET_CLEANED`, Any-baseline, ANN401 or `host_typecheck.ini` line retired.
- Lead, docstring: `_render_coverage.py`'s docstring still says "rather than a pyproject.toml dev dependency", which has been false since the coverage pin. I will fix it at step 114.
- Lead, new scan finding (port held by another suite / load): XDG_RUNTIME_DIR is unset here, so every `unshare -n` run shares `/tmp/sensors-port-*.lock`. Once the takers land, netns-isolated parallel runs (the gate layout, single-file test.sh runs) will refuse each other even though their ports cannot collide. Fix options, both outside my set: each namespace wrapper exports its own `XDG_RUNTIME_DIR=$(mktemp -d)`, or the lock key includes the netns, which changes the contract J consumes.
- Other scan items need no fix: a failed release leaves a dead pid that the next taker takes over; a leftover takeover claim or a reused pid fails visibly, naming the directory or pid; a holder stalled over 1 s between its mkdir and its pid write is the one bound, stated in the library comment.

STOPPED; waiting for `<API>`.

######## SubagentHandback 2026-10-13T17:30:13.366Z
FINAL 0e59e52 (audit/u24-s: merge of api1 876bc9e = a56e7a8, then the lane S final on top). No WIP S2 was needed: coverage 7.16.2 imports from the shared venv.

**Steps:**
- **Applied (8):**
  - 71: test.sh takes port 53.
  - 132: run_digital_twin_ci.sh takes 53 and 18080.
  - 73: run_unix_port_integration.sh requires `--device`, exits 2 naming the derived devices, and takes 53. New test file `test_run_unix_port_integration_sh.py`.
  - 113: under `--coverage` the pytest tier runs as `coverage run --data-file=<results_dir>/host.coverage --source=buildgen,scripts,toolchain -m pytest tests_scripts …`.
  - 114: `_render_coverage.py` writes XML only when `--xml-file` is given. Its false docstring clause is fixed. Member order follows D.15.
  - 115 and 307: a third render for `build/generated_src` and the host report (`coverage html` / `coverage report --format=markdown`). Every render is guarded, so any render failure means exit 3. The archive list gains the four new outputs.
  - 256: the four `.gitignore` entries.
- **Partly (1):** 305. A.U24.66's fixture is now `fixture_device.toml`. A.U24.40 is applied at its quoted site, which is the reclamation no-op test, now with a listing check (deviation below).
- **Nothing at U24 (5), read only:**
  - 4 (A.S0930.26/.37 are blast only).
  - 5 and 306 (their stage is deferred to U25).
  - 110 (only the `--coverage` header paragraph changed to stay true).
  - 129 (generation still runs before the pytest launch; `test_test_sh.py`'s ordering test passes).

**Seen failing first (on api1, before the product edits):**
- `test_each_runner_refuses_a_port_a_live_process_holds_before_touching_anything` [4 cases]: each runner ran past a held port to its toolchain step.
- `test_run_unix_port_integration_sh.py`: with no argument it exits 0 and stdout shows "(device: wozi)". `--device` with no value stops on `$2: unbound variable`, exit 1.
- `test_a_coverage_run_traces_the_host_build_chain_through_the_pytest_tier`: index 2 was 'pytest', expected 'coverage'.
- The four-reports test, the 5-render guard check (`2 == 5`) and three exit-3 cases failed.
- `test_the_exit_trap_releases_the_port_lock_on_an_aborted_run`: the lock was left behind.
- `test_a_render_given_no_xml_file…`: `coverage.xml` was written.
- Reclamation listing: the old test passes a planted conftest that writes into the tree; the new test fails on it.
- Seven product bites (scratch, nothing committed) were each caught.

**Red checks:**
- `test_no_variant_literals.py::test_every_not_yet_cleaned_entry_still_carries_a_literal` fails until the lead removes `:45` `"scripts/run_unix_port_integration.sh": _REASON_RUNNER,` and `:127` `"tests_scripts/test_test_sh.py": _REASON_PYTEST,`.
- The generated report reads 0% until H adds `"build/generated_src/"` to `_TRACED_PREFIXES`. It is missing from api1 (`tests/_coverage_runner.py:25`).

**Deviations:**
- The lock is taken right after validation, before the archive, sweeps and toolchain step. M.SCR.039 says after the toolchain step; earlier is stricter. test.sh arms a `trap port_lock_release_all EXIT` that `_cleanup`'s trap later replaces, and `_cleanup` releases the lock too.
- Runner names are the script paths in all three runners, for consistency.
- `--data-file` is used instead of the `COVERAGE_FILE` env, so the variable stays out of the tier's test environment.
- Step 305: the brief describes a rejection test, but A.U24.40's quoted site (`:373` → now 427) is the reclamation no-op test.

**Checks:**
- ruff, shellcheck (4 scripts) and the host mypy pass (207 files) are clean.
- The pre-commit set plus tool-help ran 671 passed, 1 failed (the red check above).
- Times before → after, nice 19, own namespace: `test_port_lock` 3.3 → 3.75 s (one run took 8.4 s under host load), `test_test_sh` 27.0 → 26.4–29.7 s, `test_render_coverage_anchors` 0.04 → 0.09 s, `test_run_unix_port_integration_sh` new at 0.2 s.

**A-37:**
- The traced tier ran once: 964.6 s wall (pytest 937.9 s), 4580 passed, 1 failed (the red check), 11 expected skips.
- It started with 1 heavy process on the host; during the run 3–6 were running.
- Verdict: under 1000 s, so the single run stands. The margin is thin: +66 % over the plain 579 s, 235 s left under the 1200 s bound, and CI runs it beside the settrace tier.
- The host report rendered from that data: 38 files, 83 % total.

**Scan, new finding:** an aborted test.sh kills only the pytest job. Its `run_test_file &` jobs keep running, and can keep port 53 bound after the trap has released the lock (class: a port held by another suite / abort).

**Facts owed:**
- **X:** E.1: the three runners, their ports, the refusal message, release on exit, descendants passing through the owner chain, and a per-namespace `XDG_RUNTIME_DIR` (as the lead ruled). E.5/E.5.3: four reports (the generated one without XML; host data in `results_dir`); any render failure means exit 3; host coverage is report-only; `--xml-file` is optional. No `@tunable` added.
- **Y:** CLAUDE.md "Two suites" gains the per-port lock. README's manual-runner example passes `--device <name>`. BACKLOG's chroot list names the `coverage==7.16.2` pin and the host-coverage step.
- **Lead:** A-37's time and verdict above; the two retired lines above; the coverage need is met.

**Runs:** two rebuilds rc 0; the A-37 run (pid 18327) rc 1, the expected red; pre-commit sets rc 0 and rc 1 (red as above); timed file runs rc 0; host mypy rc 0. All exited. RUNS.md has 13 start lines and 13 done lines for lane S.

**Record:** these notes and the `S/u24/laneS/` logs. The harness blocks report files, so there is no separate record file.
