# OF-24: why `from asyncio import core` passed mypy locally until about 08:29 and failed afterwards

## Root cause (reproduced)

The passing and failing runs checked **different sets of files**. Nothing on disk changed at 08:29.

1. **Every pass with a cold cache ran `scripts/typecheck.sh` with no arguments.** That covers the
   07:17 gate in wt-u8 and the 08:27:33 run in the fresh wt-ci. With no arguments, the main pass checks
   pyproject's `files = ["src", "tests", "digital_twin", "tests_hardware/device_scripts"]`, 170 files.
   **`digital_twin/` is in that set.** CI (`src tests tests_hardware/device_scripts`, 158 files) and
   p2b's `mypy src tests` at 06:59 both leave it out. Both of those failed. p2b's report at 07:03
   already records the error: "It occurs at HEAD too…".
2. `digital_twin/unix_port_poll_prewarm.py:7` has
   `import asyncio.core as _core  # type: ignore[import-not-found]` (present at 798cc44, 41b47f1 and
   ddec66e). In mypy, a plain `import a.b` makes `asyncio.core` a dependency of the build. The module
   lookup then fails, and `State.__init__` records it in `manager.missing_modules`
   (mypy/build.py ~2730). The error at that line is suppressed by its own `type: ignore`.
3. In `tests/test_asy_udp_socket.py`, `from asyncio import core` adds `asyncio.core` as a dependency
   only if it exists on disk (`all_imported_modules_in_file`, build.py ~1217–1225). Semantic analysis
   (`visit_import_from`, mypy/semanal.py ~3043–3101) then looks for the name: `core` is not a name in
   `asyncio`, and no `asyncio.core` module is loaded. The outcome depends on `missing_modules`:
   - **If `asyncio.core` is in `missing_modules`** (only when the prewarm module is in the same build),
     `missing_submodule = True`. mypy calls `add_unknown_imported_symbol()`, so `asyncio_core` becomes
     `Any`, with **no error**. That `Any` also covers `asyncio_core._task_queue.peek()` at line 620.
   - **Otherwise** it calls `report_missing_module_attribute()`, which gives
     `Module "asyncio" has no attribute "core" [attr-defined]`, the CI error.
4. **The warm `.mypy_cache` then carried the pass into narrowed runs.** The 08:27:52 run (CI args)
   and the 08:28:42 run (CI args, py3.12 venv) reused wt-ci's `.mypy_cache` from the 08:27:33
   full-scope run. `test_asy_udp_socket`'s metadata was fresh, so mypy never rechecked the module.
   Those two "passes" add no new evidence.
5. **The flip at about 08:29 came from the lead's own next commands.** At 08:29:05 the lead ran
   `mypy -v tests/test_asy_udp_socket.py` with that warm cache. In a single-file build, mypy marks the
   module stale because of its dependencies (`asy_udp_socket`, `microtest`). It rechecks it without the
   prewarm module, so the error appears and the error state is written to the cache. Every later
   run was narrowed: `--cache-dir=/dev/null`, `rm -rf .mypy_cache`, CI args or single files, including
   the fresh wt-ci2 run for `local_fail_fresh_wt_41b47f1.log`. No full-scope run of the *old* import
   happened after 08:29 (I checked the lead's transcript). So "fresh worktree or not, cold cache or not"
   fails, because every one of those runs used the narrowed scope.

## Reproduction (worktree S/wt-of24 at 41b47f1, mypy 2.4.0, a separate cold `--cache-dir` per run)

```
1) mypy                                       (default files)  -> Success: no issues found in 170 source files
2) mypy src tests tests_hardware/device_scripts (CI scope)     -> Found 1 error in 1 file (checked 158 source files)
3) same as 2 but with run 1's cache                            -> Success: no issues found in 158 source files
4) CI scope + digital_twin/unix_port_poll_prewarm.py           -> Success: no issues found in 159 source files
5) tests/test_asy_udp_socket.py + the prewarm module only      -> Success: no issues found in 2 source files
6) tests/test_asy_udp_socket.py alone                          -> Found 1 error in 1 file (checked 1 source file)
```

The lead's whole sequence, replayed in the worktree's own `.mypy_cache` after `rm -rf .mypy_cache`:

```
A) scripts/typecheck.sh                       -> main pass: Success ... 170 source files; Result: PASS   (= 07:17 gate / 08:27:33)
B) scripts/typecheck.sh src tests tests_hardware/device_scripts
                                              -> Success ... 158 source files; Result: PASS              (= 08:27:52 / 08:28:42)
C) mypy -v tests/test_asy_udp_socket.py       -> "Metadata fresh for test_asy_udp_socket" then
   "Scheduling SCC singleton (test_asy_udp_socket) as stale due to deps (asy_udp_socket microtest)"
   -> tests/test_asy_udp_socket.py:5:1: error: Module "asyncio" has no attribute "core"                 (= 08:29:05)
```

The fix (ddec66e's `import asyncio.core as asyncio_core  # type: ignore[import-not-found]`) is clean
with a cold cache in all three scopes: default (170), CI (158) and single file (1). That form reports
`import-not-found` in each importing module whatever else is in the build, so its ignore is used in
every scope.

## Hypotheses ruled out

- **A real `asyncio/core` file on a search path:** ruled out.
  - `strace -f -e trace=file` on a mypy run shows `asyncio/core*` probed only under
    `typings/stdlib/asyncio/`. mypy lists each base directory (worktree root, src, tests, typings,
    ext/typings, build/generated_src, typings/stdlib) and probes only those holding an `asyncio` entry,
    and only `typings/stdlib` has one.
  - A system-wide `find` shows no `asyncio/core.pyi` anywhere. The only `asyncio/core.py` files are
    MicroPython sources under `/root/pico-toolchain` and scratch copies, none of them on any mypy path.
  - Placing an `asyncio/core.pyi` in build/generated_src, ext/typings or typings does make mypy resolve
    it. It then fails at line 620 instead (`_task_queue`), so a stray stub would not even have given a
    clean pass.
- **Stub versions or contents differ:** ruled out.
  - The wheels for stdlib-stubs 1.29.0.post1, 1.29.0.post2 and 1.28.0.post6, downloaded from PyPI, carry
    no `asyncio/core.pyi`.
  - PyPI's newest uploads are 2026-08-30 and 2026-08-31, with nothing new today.
  - `diff -rq` of typings/ in wt-of24, the main checkout, wt-u8, wt-u7g and wt-u10int is empty.
  - The uv archive entries for both stub packages have no files modified after 2026-10-06 06:00, only
    ctime bumps from new hard links.
- **Venv/mypy drift:** ruled out. mypy 2.4.0 in every lock involved (c3df14e, 798cc44, 41b47f1,
  ddec66e). The main venv's mypy/librt were installed 2026-10-06 07:35 and are unchanged. The only new
  uv archive entries today (08:28:35/37) are the cp312 mypy and librt from the lead's own py3.12 venv.
- **Configuration and environment:** ruled out.
  - `no_site_packages = true` gives "Configured Executable: None", so no package path.
  - No `MYPYPATH`/`MYPY_*`/`PYTHONPATH` is set (here, and in the lead's check at 08:30:46).
  - No `cache_dir` is set anywhere, so the cache is per-worktree `.mypy_cache`.
- **Concurrent test/twin runs in wt-u8/wt-u7g** writing `build/`, `frozen_modules/` or `.frozen`:
  irrelevant. Those directories are per-worktree, and wt-ci was a fresh worktree. The mechanism above
  is deterministic and needs no outside state.
- **Clock/mtime effects:** not involved. The result depends only on the file set and the cache state,
  and reproduces at will.

## Consequences worth recording

- Local `scripts/typecheck.sh` (no arguments) and CI (`src tests tests_hardware/device_scripts`) do not
  type-check the same build. mypy's per-build `missing_modules` lets one module's ignored
  `import pkg.sub` silence `from pkg import sub` attribute errors in every other module of that build.
  The main pass's `files` includes `digital_twin/`, CI's narrowing excludes it, so a local no-argument
  pass is weaker than CI's for this whole class of error. A gate that wants CI's verdict should run the
  CI argument list, or both.
- A warm `.mypy_cache` from a wider-scope run can hide the narrowed-scope error (run 3 / step B).

Evidence files (scratch): `u10/of24_strace.txt`, `u10/of24_verbose.log`, `u10/of24_stepC.log`,
`u10/of24_cmds.txt` and `u10/of24_main_0820_0840.txt` (the lead's commands and results extracted
from the transcript).
