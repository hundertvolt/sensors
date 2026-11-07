# Known symptoms: check here before re-diagnosing

Each row is a cause this repository already found and fixed or fenced. Run the confirming check first; only if it
fails is the symptom new. The full account is where the last column points.

## Test and twin tiers

| Symptom | Known cause | Confirming check | Full account |
|---|---|---|---|
| 200/404 mix (`[200, 404, 200, 404, 'rejected', ...]`), empty body, 404 for a real page | Two port-binding suites at once | Another runner holds a port: `port <p> is held by <runner> (pid <pid>)`, or `ls ${XDG_RUNTIME_DIR:-/tmp}/sensors-port-*.lock/` | CLAUDE.md "Two suites that both bind real ports"; `scripts/_port_lock.sh` |
| A test awaiting a stream read with `timeout_ms=-1` hangs (GitHub runners only) | A fake stream behind a real `select.poll()` | The double is a bounded `_StepPoller`-style fake | CLAUDE.md "Known hang cause"; SPECIFICATION.md F.7 |
| The process hangs after its closing `P/T passed, F failed, S skipped` line | Sibling tasks stay parked; `microtest.run()` must exit | `tests/microtest.py`'s `run()` still ends in `sys.exit()` | CLAUDE.md "Known hang cause #2" |
| A file dies mid-run, `Segmentation fault`, no closing line | A nested `asyncio.run()` called from inside a coroutine | The helper is called from the synchronous test body | CLAUDE.md "Known segfault cause"; SPECIFICATION.md F.1 |
| `MemoryError: ... heap is locked` at twin shutdown | SIGINT inside `gc_collect()` | The `unix_kbd_intr` override is applied (`uv run toolchain/setup_toolchain.py test`) | CLAUDE.md "intermittent-MemoryError cause #2"; SPECIFICATION.md F.6 |
| Shutdown-only exit 1 at gc 32768, maybe `TypeError: 'frame' object isn't iterable` | Unsafe asynchronous SIGINT delivery | The same override (`MICROPY_ASYNC_KBD_INTR=0`) | SPECIFICATION.md B.14.1 |
| A flaky `MemoryError` in a heavy test file | `-X heapsize` missing on a direct run (2 MB default) | `scripts/_run_checks.sh mpy:FILE` passes scripts/test.sh's own size; never raise it as the fix | SPECIFICATION.md E.3.1 |
| A consistent live-clock assertion failure | `$TZ` is not UTC on the Unix port | Run with `TZ=UTC` (scripts/test.sh exports it; `_run_checks.sh mpy:` sets it) | CLAUDE.md "Local test runs pin $TZ=UTC" |
| `ImportError: no module named 'sensortask_<d>'`, `frozen_html` missing | Generated inputs absent or stale | One `scripts/test.sh` run rebuilds both; alone: `uv run scripts/_generate_sensortask_modules.py`, `scripts/build_website.sh <device>` | SPECIFICATION.md E.3 |
| Twin feed gaps above 75 % of 8,000 ms, or real-time budgets missed, on several devices at once | Host starvation: a wall-clock budget measures host speed (open, not closed) | The log's `== Test parallelism:` line (jobs against cores, probe ms); rerun with `TEST_PARALLELISM=<cores>` | scripts/test.sh's TEST_PARALLELISM comment; SPECIFICATION.md J.7 |
| `only N-1/N hammered transactions completed`, UART scheduling flake | Host scheduling stall under oversubscription | Reproduce with `taskset -c 0,1 uv run bash scripts/test.sh`, `TEST_PARALLELISM=32` | SPECIFICATION.md J.7 |
| Twin exits 1 before serving: `FATAL: uncaught NLR` | A launch string over 255 bytes | The launchers refuse and name the sizes | digital_twin/README.md |
| test.sh: `no verdict (git status could not list the checkout...)` | A copied tree whose `.git` points elsewhere | Use a real checkout or `git worktree` | BACKLOG.md (chroot list); scripts/test.sh |
| A device glob or generation picks up a stray `zz_test_` device TOML | A killed `tests_scripts` fixture | test.sh sweeps the pattern first; delete the stray file | SPECIFICATION.md E.1 |
| Shutdown-line memory hits that read `log carries none of ('MemoryError', ...)` | A gate naming what it searches for | `scripts/_log_verdict.py` skips quoted mentions and counts them apart | this skill |

## Tooling

| Symptom | Known cause | Confirming check | Full account |
|---|---|---|---|
| Unchosen ruff or mypy findings after a merge | `uv.lock` merged line by line | `uv sync`, then `ruff --version` and `mypy --version` against `pyproject.toml`'s pins | CLAUDE.md "A merge that touches uv.lock" |
| A test lane red with no test named; `HTTP Error 500` from uv | A third party's outage during `uv sync` | Read the uv output before the test output; `scripts/uv_sync_retried.sh` | CLAUDE.md "A third party's momentary outage" |
| A long-lived toolchain rebuilds its Unix ports once | The probe saw a flavour or input-hash mismatch | `scripts/_unix_port.sh check standard` | CLAUDE.md (two Unix-port binaries) |
| Allocation figures 4-5x too high | Measured under `--coverage` (the settrace binary) | Measure on `build-standard` | SPECIFICATION.md E.5.2 |
| `call-overload` at a bare `Timer()` | A gap in the board stub, seen only in a src-only mypy run | Run the full `scripts/typecheck.sh` | CLAUDE.md (typecheck notes); SPECIFICATION.md B.15 |
| `lint.sh` or `typecheck.sh` refuses to start | No venv, or another tree's venv (`_require_venv.sh`) | `uv sync && source .venv/bin/activate` in this tree | CLAUDE.md "Code quality tooling" |
| The clean-chroot leg fails 60+ host tests with `node is not on PATH` | A recipe older than 2026-11-07 ran `uv sync` alone and installed no Node | Follow the current recipe: `env --tier generic`, then its Node on PATH | README.md (clean-chroot recipe) |
