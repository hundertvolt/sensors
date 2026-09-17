# scripts/test.sh speed findings — external cross-check on PR #104

Temporary file, same convention as `WP_RESTART_HANDOVER.md`/`TEST_SUITE_ECONOMY_HANDOVER.md`:
delete once its findings are either incorporated (into `PR #104`'s own commits/CLAUDE.md/
`scripts/test.sh` comments) or confirmed not worth pursuing. Written by a separate session that
pulled PR #104's branch to verify its own claimed wall-clock numbers and look for further
improvements, per the project owner's explicit direction — **not committed to
`claude/sensortask-test-economy` itself**, since another session owns that branch; this lives on
its own throwaway branch (`claude/test-suite-speed-findings`) so the PR #104 session can pull just
this one file in without any risk of conflicting with its own in-flight work. Nothing else in this
repo was touched by the session that wrote this.

## Method

Local 4-core sandbox (`nproc` = 4), matching a typical GitHub-hosted `ubuntu-latest` runner's core
count. Full end-to-end `scripts/test.sh` runs, real MicroPython Unix-port toolchain (cached, not
rebuilt), each timed with `time`. Baseline and the first three data points below were measured
against PR #104's branch at commit `90aece7` (`Fix dev digital-twin-e2e's real PUT /status
ResetErrors timeout, not a flake` — the tip at the time this session pulled the branch); the branch
has since moved to `a974244` (three more commits, including the session's own independent
`_heavy_files_priority` dispatch-order optimization in `scripts/test.sh` — see "Interaction with the
existing heavy-first dispatch order" below for why that doesn't invalidate these numbers). Every run
reported `77/77 files passed` and `tests_scripts/ (CPython/pytest): PASS` — **correctness was
identical in every configuration below; only wall-clock changed.**

## Finding 1: `tests_scripts/` runs sequentially in front of the parallel loop for no reason

`scripts/test.sh` currently runs `uv run pytest tests_scripts -q` (the CPython-side build-tooling
test suite — `buildgen/`, `scripts/build_firmware.py`, etc.) as a plain sequential step, **before**
the parallel `tests/test_*.py` job pool even starts. Measured standalone: **247.93s (~4m8s)**, of
which only 2m27s is real CPU time (`user`) — it's partly I/O-bound too, not just the MicroPython
suite.

This is pure waste: `tests_scripts/` is **provably independent** of everything the MicroPython loop
touches. Confirmed directly, not assumed:

- `tests_scripts/conftest.py`'s own docstring already states it's CPython-only, unrelated to
  `MICROPYPATH`/the Unix port.
- Every reference to `generated_src`/`frozen_modules`/`frozen_html` anywhere in `tests_scripts/`
  (grepped across all 20 real `.py` files) is scoped to pytest's own isolated `tmp_path` fixture —
  none of them read or write this repo's real `build/generated_src/` or `frozen_modules/`.
- `test_digital_twin_generated_boot.py` (the one file that spawns real Unix-port subprocesses and
  speaks HTTP) allocates its own port via `_free_port()` (OS-assigned, ephemeral) — never a fixed
  port that could collide with anything the MicroPython loop or `tests/
  test_digital_twin_webserver_concurrency_<device>.py`'s own fixed port-range convention uses.

So there's no reason it can't run **concurrently** with the toolchain-check/setcap/frozen-html/
buildgen prelude steps and the entire parallel `tests/test_*.py` loop — it just needs to finish
*before* the script prints its final summary.

**Fix** (patch below, already applied and verified against `90aece7` — lint-clean: `ruff`/
`shellcheck`/`mypy`/`zizmor` all pass): launch it in the background right after the toolchain-build
check (the earliest point it needs nothing else to exist), write its result to a status file the
same way `run_test_file()` already does for every other file, and read that status file after the
main loop's own `wait` (which reaps this job too, since it's backgrounded into the same shell — it
naturally counts against `max_parallel`/`TEST_PARALLELISM` like any other job, not an extra
unbounded process on top of that budget).

**Measured effect** (against `90aece7`, `TEST_PARALLELISM` left at its default of 4):

| Configuration | Wall-clock |
|---|---|
| Baseline (`tests_scripts` sequential, as committed) | **12m19.256s** |
| `tests_scripts` backgrounded (this fix) | **9m5.102s** |

**~26% faster, zero behavior change.**

<details>
<summary>Full patch (against commit <code>90aece7</code>)</summary>

```diff
diff --git a/scripts/test.sh b/scripts/test.sh
index 4edae8e..963a255 100755
--- a/scripts/test.sh
+++ b/scripts/test.sh
@@ -84,6 +84,29 @@ if [ ! -x "$micropython_bin" ]; then
     uv run toolchain/setup_toolchain.py setup --toolchain-dir "$toolchain_dir" "${skip_apt_flag[@]}"
 fi
 
+# tests_scripts/ is genuinely independent of everything below this point - real CPython/pytest code
+# (never MICROPYPATH/build/generated_src/frozen_modules-dependent, see tests_scripts/conftest.py's
+# own docstring) that only ever touches pytest's own isolated tmp_path fixtures or OS-assigned free
+# ports (test_digital_twin_generated_boot.py's own _free_port()), never this repo's real
+# build/generated_src/ or frozen_modules/ - confirmed directly, no test file in tests_scripts/
+# references either outside a tmp_path. So it needs nothing from the setcap/frozen_html/
+# frozen_website/buildgen steps below, and backgrounding it here - instead of the old placement
+# right before the MicroPython test-file loop - overlaps its own real ~4-minute wall-clock (measured
+# directly: 247.93s under pytest's own timer) with essentially the *entire* rest of this script
+# rather than serializing in front of it. Counted the same as any other job against
+# max_parallel/TEST_PARALLELISM below (it backgrounds itself the same way, into the same shell), not
+# an extra unbounded process on top of that budget - same "everything here is a fully isolated OS
+# process" reasoning the job-pool comment below already gives, just applied one job earlier.
+echo "== Running tests_scripts/ (CPython-side build-tooling tests)"
+tests_scripts_status_file="$(mktemp)"
+(
+    if uv run pytest tests_scripts -q; then
+        echo "PASS" >"$tests_scripts_status_file"
+    else
+        echo "FAIL" >"$tests_scripts_status_file"
+    fi
+) &
+
 # tests/test_digital_twin_sensortask_integration.py's own hotspot/DNS test binds the real
 # privileged port 53 (src/captive_dns.py's DNSServer) from a genuine, organically-triggered hotspot
 # scenario - a GitHub Actions runner (or any non-root dev environment) can't bind that port without
@@ -124,20 +147,14 @@ scripts/build_website.sh wozi frozen_modules/frozen_website_wozi.py
 echo "== Generating buildgen device modules into build/generated_src/"
 uv run scripts/_generate_sensortask_modules.py
 
-# CPython-side tests for the build tooling itself (scripts/build_frozen_html.sh, scripts/
+# tests_scripts/ itself (CPython-side build-tooling tests: scripts/build_frozen_html.sh, scripts/
 # build_website.sh, scripts/build_firmware.py - SPECIFICATION.md Part B.11's "fully verified"
-# follow-up) - see tests_scripts/conftest.py's own docstring for why these run under CPython/
-# pytest rather than the MicroPython Unix port loop below: none of these scripts are MicroPython-
-# target code. RUN_SLOW_FIRMWARE_BUILD is deliberately left unset here, so the one real (but cheap,
-# ~1 minute with a warm toolchain) ARM firmware compile it gates stays opt-in for fast local
-# iteration - .github/workflows/ci.yml's firmware-build-verify job is what actually sets it.
-echo "== Running tests_scripts/ (CPython-side build-tooling tests)"
-# Captured rather than left to `set -e` so a failure here still lets the (much slower) MicroPython
-# suite below run to completion - one full-run summary beats an early abort mid-report.
-tests_scripts_result="PASS"
-if ! uv run pytest tests_scripts -q; then
-    tests_scripts_result="FAIL"
-fi
+# follow-up; see tests_scripts/conftest.py's own docstring for why these run under CPython/pytest
+# rather than the MicroPython Unix port loop below) is already running in the background, launched
+# right after the toolchain check above - nothing here. RUN_SLOW_FIRMWARE_BUILD is deliberately left
+# unset for that run, so the one real (but cheap, ~1 minute with a warm toolchain) ARM firmware
+# compile it gates stays opt-in for fast local iteration - .github/workflows/ci.yml's
+# firmware-build-verify job is what actually sets it.
 
 raw_dir=""
 if [ "$coverage" = "1" ]; then
@@ -151,7 +168,7 @@ fi
 # cleanups must live in one trap. `rm -rf ""` (raw_dir when --coverage was never passed) is a
 # harmless no-op, not an error.
 results_dir="$(mktemp -d)"
-trap 'rm -rf "$raw_dir" "$results_dir"' EXIT
+trap 'rm -rf "$raw_dir" "$results_dir" "$tests_scripts_status_file"' EXIT
 
 failed=0
 # Per-file timeout with two retries (three attempts total), not just the job-level
@@ -324,6 +341,15 @@ for test_file in "${test_files[@]}"; do
 done
 wait || true
 
+# The tests_scripts/ background job (started before this loop, see the toolchain-check block
+# above) is reaped by the same unqualified `wait` just above like any other job; its own status
+# file is written unconditionally in both its PASS and FAIL branches, so a missing/empty read here
+# would itself be a bug, not a legitimate "still running" state - never treated as PASS by omission.
+tests_scripts_result="$(cat "$tests_scripts_status_file" 2>/dev/null)"
+if [ "$tests_scripts_result" != "PASS" ]; then
+    tests_scripts_result="FAIL"
+fi
+
 failed_files=()
 passed_count=0
 for test_file in "${test_files[@]}"; do
```

</details>

**Interaction with the existing heavy-first dispatch order** (`_heavy_files_priority`, landed in
`1e2c001`/`874e3da`/`a974244` after this session pulled the branch): this patch's only edit inside
the `test_files=(...)`-adjacent region is reading `tests_scripts_result` right after the main loop's
`wait || true` — it does not touch the `test_files=(...)` declaration or the dispatch loop itself,
which is exactly where `_heavy_files_priority` lives. The two changes are in disjoint regions of the
file (this patch: the toolchain-check block near the top, the `trap`, and the post-`wait` summary
read; theirs: the `test_files=(...)` construction) and should apply cleanly together in either
order — not verified by actually merging both in this session (see "What this session did not do"
below), so re-verify before relying on that.

## Finding 2: the suite is wall-clock-sleep-bound, not CPU-bound — `TEST_PARALLELISM` can go well past `nproc`

Building on Finding 1 (both measured together, same `90aece7` base), tried raising
`TEST_PARALLELISM` past its default (`nproc`, i.e. 4 in this sandbox):

| `TEST_PARALLELISM` | Wall-clock | `user` CPU time |
|---|---|---|
| 4 (default) | 9m5.102s | 4m57.583s |
| 8 | **5m1.602s** | 4m56.911s |
| 16 | **4m12.204s** | 4m58.854s |

Total `user` CPU time is **flat across all three** (~4m57s-4m59s) while wall-clock keeps dropping —
direct confirmation of the theory `scripts/test.sh`'s own comments already state (real SPI CS-settle
sleeping in `asy_spi_driver.py` dominates each build's cost, not CPU work): oversubscribing well
past the physical core count is close to "free" concurrency here, since most concurrent processes
spend most of their time asleep, not competing for CPU.

**At `TEST_PARALLELISM=16`, the bottleneck shifts entirely to `tests_scripts/` itself**: that run's
own `tests_scripts` pytest invocation took 251.33s (4m11s) — matching the *total* wall-clock
(4m12.204s) almost exactly. Every one of the 77 MicroPython files finished within that same window.
Going further than 16 would need `tests_scripts/` itself to be parallelized (e.g. `pytest-xdist`) to
see any more benefit — not attempted here, out of scope for this pass.

**Combined effect**: **12m19s → 4m12s, ~3x faster**, entirely from two changes that touch nothing
about *what* runs or *what* it asserts — only *when* things start relative to each other.

**Caveat, stated plainly**: this is a 4-core *sandbox* measurement. Real GitHub Actions
`ubuntu-latest` runners are also nominally 4-core, but may have different CPU quota/throttling under
cgroups, different disk I/O characteristics, and different noisy-neighbor behavior than this
sandbox. Treat the *qualitative* finding (oversubscription helps a lot, since the workload is
sleep-bound) as strong and directly actionable; treat the *exact* numbers as directional, not a
guarantee that real CI will land on precisely 4m12s at `TEST_PARALLELISM=16` — worth confirming with
a real CI run (e.g. a one-off `TEST_PARALLELISM=16` override in a throwaway workflow dispatch, or
just trying it as the new default and watching the next few CI runs' actual `unit-tests` job
duration) before committing to a specific number as `scripts/test.sh`'s new default.

## Recommendation

1. **Port Finding 1's patch as-is.** It's small, already lint-clean, changes nothing about
   correctness (verified: 77/77 files + `tests_scripts` still PASS), and is a pure win independent
   of the `TEST_PARALLELISM` question.
2. **Try raising `TEST_PARALLELISM`'s default past `nproc`** (e.g. `nproc * 4`, or a flat value like
   16) in real CI and confirm the `unit-tests` job's actual wall-clock drops the way this sandbox's
   numbers suggest, before locking in a specific number. Given real CI runners may have tighter
   memory or CPU-quota limits than assumed here, verify there's no `MemoryError`/timeout regression
   at the chosen value under the project's real `-X heapsize=32M`-per-process budget (16 concurrent
   processes × 32M heap each is 512M virtual, worth a sanity check on a real runner even though
   virtual reservation isn't the same as resident memory).
3. Once `tests_scripts/`'s own ~4-minute single-process runtime becomes the binding constraint (as
   it already does at `TEST_PARALLELISM=16` against the `90aece7` baseline), the next lever is
   parallelizing `tests_scripts/` itself — flagged here as a real further opportunity, not pursued.

## What this session did not do

- Did not modify, commit to, or push anything on `claude/sensortask-test-economy` itself — this
  file lives on its own throwaway branch (`claude/test-suite-speed-findings`), per explicit
  instruction that another session owns that branch.
- Did not re-run the full 4/8/16 `TEST_PARALLELISM` sweep against the branch's current tip
  (`a974244`, which added the `_heavy_files_priority` dispatch-order optimization on top of
  `90aece7`) — the numbers above are against `90aece7`. The qualitative findings (tests_scripts
  independence, sleep-bound oversubscription) don't depend on file dispatch order and should still
  hold, but the exact wall-clock numbers on the current tip haven't been directly re-measured.
- Did not attempt parallelizing `tests_scripts/` itself (e.g. `pytest-xdist`) — flagged as a further
  opportunity in the Recommendation section, not investigated.
