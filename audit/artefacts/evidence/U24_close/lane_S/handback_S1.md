
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
