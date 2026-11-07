# Harvest H09 — host build chain and config: scripts/, toolchain/, buildgen/, .github/, devices/, pyproject.toml, host_typecheck.ini, .gitignore (snapshot 2a88cc8)

## scripts/test.sh
- SETTLED | scripts/test.sh:20-23 | "Not a production bug; CLAUDE.md's \"Local test runs pin $TZ\" has the account." | Unix-port `time.mktime()` reads host `$TZ`, so every local/CI unit run is pinned to `TZ=UTC`; results under any other TZ are not meaningful. | area: TEST | related: XCUT.T18
- PLATFORM | scripts/test.sh:20-21 | "The Unix port's time.mktime() calls the host's real libc, which reads $TZ - unlike the rp2 firmware's TZ-agnostic override" | Unix-port vs rp2 `mktime` divergence (ports/unix/modtime.c vs ports/rp2/datetime_patch.c) is a version-specific fact the test tier depends on. | area: PLAT | related: XCUT.T18
- INVAR | scripts/test.sh:25-27 | "a rejected invocation must leave the live tree exactly as it found it" | Argument/GC_THRESHOLD validation must stay ahead of the `rm -rf tests/_tmp`/`rm -f devices/zz_test_*.toml` sweeps because tests_scripts runs a nested test.sh concurrently with the live suite. | area: SCR | related: SCR.T14
- DRIFT | scripts/test.sh:27 | "concurrently with 85 files holding tests/_tmp scratch" | Stale count: 87 `tests/test_*.py` exist at 2a88cc8 (CLAUDE.md:350 says 86/86). (low) | area: SCR | -
- MIRROR | scripts/test.sh:47, 54 | "32768 is what the firmware ships, -1 the reactive default" | The GC_THRESHOLD value tested in stage (f) is a hand copy of the generated boot entry's `gc.threshold(32768)`; nothing ties the two. | area: SCR | related: SCR.S10
- LIMIT | scripts/test.sh:57-61 | "--coverage uses its own runner, so GC_THRESHOLD=$GC_THRESHOLD is ignored for this run" | A coverage run never exercises the (f) threshold stage; the settrace binary only ever runs at the reactive default. | area: SCR | related: SCR.T01
- RISK | scripts/test.sh:64-72 | "rm -rf tests/_tmp" / "rm -f devices/zz_test_*.toml" | Every test.sh run mutates the live tree (scratch sweep and reserved `zz_test_` device-TOML namespace deletion); correctness depends on Part E.1's reserved-namespace convention. | area: SCR | covered-by: SCR.T14
- ASSUME | scripts/test.sh:75-77 | "compiling MICROPY_PY_SYS_SETTRACE in allocates a frame and a code object per call ... inflating every allocation figure 4-5x" | Single measured figure (Part E.5.2) justifying the two-binary split. | area: TOOL | related: TOOL.T05
- INVAR | scripts/test.sh:92-102 | "Asks the binary which variant it is instead of trusting its path ... Always exits 0" | Variant detection relies on `hasattr(sys,"settrace")` plus a frozen `asyncio` import; the probe exists only in test.sh (not the twin/web runners). | area: SCR | covered-by: SCR.S05
- RISK | scripts/test.sh:104-113 | "MicroPython Unix port not found at $micropython_bin - building it now" | test.sh auto-runs a full `setup_toolchain.py setup` (sudo apt, picotool `sudo make install`) when the binary is missing or the wrong variant. | area: SCR | covered-by: TOOL.S08
- LIMIT | scripts/test.sh:129-131 | "One hazard is NOT closed: a twin test asserting a real background transition inside a fixed budget measures host speed" | Declared open hazard: CPU starvation fails a healthy twin test; only the speed probe mitigates it. | area: TEST | related: TEST.T04
- ASSUME | scripts/test.sh:133-143 | "(391ms against 131-141ms idle)" / "wall clock dropped 8m27s -> 3m45s" | Parallelism design rests on single dated measurements (probe timings, user-CPU flat across 4/8/16). | area: SCR | related: SCR.T01
- INVAR | scripts/test.sh:137-139 | "THIS BLOCK'S PLACEMENT IS LOAD-BEARING: it must stay ahead of the tests_scripts/ background launch" | Probe must run before the backgrounded pytest tier; enforced by `tests_scripts/test_test_sh.py`. | area: SCR | related: SCR.T01
- ASSUME | scripts/test.sh:145-147 | "the whole run writes ~46MB and spends ~8.7s of system time today" | Single dated host-wear measurement tied to CLAUDE.md's no-avoidable-wear rule; "sleep-bound" claim must be kept true. | area: SCR | -
- LIMIT | scripts/test.sh:151-152 | "cgroup v2; v1 and \"max\" both fall through to the nproc value unchanged" | Container CPU quota is honoured only under cgroup v2. | area: SCR | related: SCR.T01
- RISK | scripts/test.sh:160-161, 178-180 | "Speed probe. Never allowed to fail the run: any error, and we fall through to the fast-host multiplier" | A broken probe deliberately picks the most oversubscribed (4x) setting, which is the setting known to starve slow hosts. | area: SCR | related: SCR.T01
- ASSUME | scripts/test.sh:181-186 | "multiplier=4 # fast host (measured: 131-141ms on this project's own x86 sandbox)" | 250/900 ms band thresholds derived from one x86 sandbox and "the bench Pi4's class". | area: SCR | -
- INVAR | scripts/test.sh:197-203 | "0 or negative ... spins `wait -n` forever without dispatching anything" | `max_parallel` clamp >= 1 is the only guard against a hang from a bad TEST_PARALLELISM. | area: SCR | related: SCR.T14
- INVAR | scripts/test.sh:205-210, 229-231 | "MUST stay behind the generation step above, which globs devices/*.toml" | Generation must run before the pytest tier is backgrounded (Part E.1 `zz_test_` race); ordering-only guarantee. | area: SCR | related: SCR.S07
- ASSUME | scripts/test.sh:214-216, 229-231 | "never this repo's real build/generated_src/ or frozen_modules/" / "build_website.sh resolves devices/<device>.toml from the repo root, so that one test cannot be handed a tmp_path tree" | The pytest tier's isolation from the live tree is by convention, with one acknowledged exception that touches real `devices/`. | area: TEST | related: TEST.T13
- ASSUME | scripts/test.sh:218-224 | "1200s is ~5x its measured ~248s" | pytest-tier timeout derived from one measured runtime; CI timeout-minutes is the outer backstop. | area: SCR | related: TEST.T13
- SETTLED | scripts/test.sh:226-227 | "No retry, unlike the per-file loop" | Whole-suite pytest timeout is deliberately never retried. | area: SCR | -
- INVAR | scripts/test.sh:233-234 | "Nothing else in the foreground re-globs devices/ once generation is done" | Convention-only; a later foreground glob of `devices/` would reopen the zz_test_ race. | area: SCR | related: SCR.T06
- INVAR | scripts/test.sh:239-244, 251-253 | "bash does not kill background jobs when the parent exits" / "no dependency on pkill/procps that a --variant=minbase chroot lacks" | EXIT trap must be armed before the background job and kill both subshell and inner `timeout` pid via a pidfile. | area: SCR | related: SCR.T08
- SUPPRESS | scripts/test.sh:249 | "# shellcheck disable=SC2329  # invoked indirectly, by the `trap _cleanup EXIT` below" | shellcheck suppression on `_cleanup`. | area: SCR | related: SCR.T08
- SUPPRESS | scripts/test.sh:97, 154, 165, 255, 257, 259, 437, 442, 522, 532 | "`|| true` because a job body always returns 0 ... a nonzero `wait -n` can only mean \"no jobs left\"" | Ten `|| true` sites: variant probe (97), cgroup read (154), speed probe (165), trap cleanup kills/cat (255/257/259), `wait -n`/`wait` reaping (437/442, justified by run_test_file never returning nonzero), annotation tail/cat (522/532). | area: SCR | related: SCR.T08
- RISK | scripts/test.sh:280-288 | "Granted fresh every invocation, for the reason run_digital_twin_ci.sh's identical grant gives (xattrs)" | `setcap cap_net_bind_service=+ep` (via sudo when non-root) on the Unix-port interpreter every run. | area: SEC | covered-by: SCR.S06
- DRIFT | scripts/test.sh:296 | "tests_scripts/ is already running in the background, launched right after the toolchain check" | It is launched after the generation step (line 212/265), not right after the toolchain check. | area: SCR | covered-by: SCR.S03
- SETTLED | scripts/test.sh:297-298 | "RUN_SLOW_FIRMWARE_BUILD stays unset for it, keeping the one real ARM firmware compile opt-in for local iteration" | Real firmware build test runs only in CI's firmware-build-verify, never in a local test.sh run. | area: SCR | covered-by: SCR.T13
- INVAR | scripts/test.sh:303-307 | "bash replaces an EXIT handler rather than stacking, so every cleanup has to live in that one trap" | Single-trap rule by convention. | area: SCR | related: SCR.T08
- SETTLED | scripts/test.sh:311-313 | "the heap value is a measured floor that must never be RAISED as a fix" | `-X heapsize=16M`, per-file timeout+retry and stdbuf are standing backstops (CLAUDE.md), not fixes. | area: TEST | related: SCR.T01
- SETTLED | scripts/test.sh:315-318 | "deliberately empty since the per-device splits, and deliberately not solved by raising everyone's default" | Per-file timeout overrides map intentionally empty; default 240 s. | area: SCR | related: SCR.S03
- MIRROR | scripts/test.sh:321-333 | "Both spellings, because src/'s degrade handlers log str(e) and not the class" | Unit-tier MemoryError gate pattern must match the twin and two hardware gates; enforced by `tests_scripts/test_memory_error_gate_agreement.py`. | area: TEST | related: TEST.T18
- PLATFORM | scripts/test.sh:327 | "prints \"memory allocation failed, ...\" (py/runtime.c:1692/1696)" | Gate wording and line citation are tied to the pinned MicroPython source; re-check on a pin move. | area: PLAT | related: TEST.T18
- RISK | scripts/test.sh:363-364 | "only the attempt that decided this file's verdict is searched for a MemoryError, so a timed-out earlier attempt's partial output cannot fail a passing file" | Deliberate: a MemoryError printed during a timed-out attempt is discarded if a retry passes. | area: SCR | related: SCR.T01
- RISK | scripts/test.sh:378-380 | "retrying in case of transient runner contention" | Timeout (exit 124) retried up to 3 times, so an intermittent hang passes if any attempt completes. (low) | area: SCR | related: SCR.T01
- INVAR | scripts/test.sh:345-351 | "Every segment of MICROPYPATH below is load-bearing. \".frozen\" explicitly, because MICROPYPATH REPLACES the default sys.path" | Path order `build/generated_src:src:tests:frozen_modules:.frozen` is convention; generated modules first. | area: SCR | related: SCR.T12
- ASSUME | scripts/test.sh:392-398 | "Hand-curated from one measurement run, so re-measure and update it if a new heavy file lands" | Heavy-file dispatch list; silently drops missing files (all 15 exist at 2a88cc8). | area: SCR | covered-by: SCR.S11
- INVAR | scripts/test.sh:445-451 | "a missing or empty read here is a bug rather than a legitimate \"still running\" - never treated as PASS by omission" | Fail-closed status-file read. | area: SCR | related: SCR.T01
- SETTLED | scripts/test.sh:473-475, 551-553 | "Coverage is a report and never gates, but the test result under this binary must (exit 3 below)" | Exit 0/1/3 contract; CI gates on 1 and tolerates 3 (Part E.5.3). | area: CI | related: CI.T11
- PLATFORM | scripts/test.sh:509-510 | "GitHub keeps only 10 error annotations per step" | Annotation budget (1 pytest + 8 files + 1 overflow) depends on a GitHub platform limit. | area: CI | -
- RISK | scripts/test.sh:505-507, 522-523 | "A workflow-command annotation is the only channel that carries a failing file's own output off the runner" | Last 40 log lines of a failing file are emitted into public PR annotations. | area: CI | covered-by: CI.T15

## scripts/lint.sh
- SETTLED | scripts/lint.sh:2-4 | "All stay fully clean. Lint only - `ruff format` is deliberately unused" | All lint scopes must be zero-finding; `ruff format` is never run. | area: SCR | related: SCR.T02
- ASSUME | scripts/lint.sh:6-7 | "Assumes `uv sync` has been run and its venv is active" | Tools resolve from PATH; an inactive/stale venv runs whatever ruff/shellcheck is on PATH, bypassing the pins. | area: SCR | related: CI.T04
- LIMIT | scripts/lint.sh:13 | "ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts" | ruff never sees `build/generated_src/` (the generated, frozen `sensortask_<device>.py`). | area: GEN | covered-by: GEN.S17
- SETTLED | scripts/lint.sh:15-17 | "deliberately NOT the four legacy build-*.sh at the repo root" | Legacy build scripts are out of lint scope by standing decision. | area: SCR | -
- DRIFT | scripts/lint.sh:17 | "they carry 28 findings of their own, including no shebang at all - see BACKLOG.md" | BACKLOG.md at 2a88cc8 contains no "28 findings"/"no shebang" entry: dangling reference (and a dated count). | area: DOC | covered-by: DOC.S05
- SUPPRESS | scripts/lint.sh:24-26 | "--offline drops the two audits needing the GitHub API" | zizmor runs with two online audits permanently disabled, in every environment. | area: CI | related: CI.T06
- INVAR | scripts/lint.sh:28-34 | "tests/ and digital_twin/ legitimately monkeypatch methods, shipped src/ never may" | No `type: ignore[...method-assign...]` in `src/`; enforced by this grep (it matches only the coded form of the suppression). | area: SCR | related: SCR.T02
- INVAR | scripts/lint.sh:36-49 | "`gc.collect()` is confined to the two one-time boot lists" | Grep is file-granular (any site in `src/system_service.py` or `buildgen/codegen.py` passes); structural check is `tests_scripts/test_gc_collect_sites.py`; tests/ and digital_twin/ are out of scope by I.4(e)/F.6. | area: MEM | related: SCR.T02

## scripts/typecheck.sh
- ASSUME | scripts/typecheck.sh:7 | "Assumes mypy is on PATH" | Pinned mypy only if the synced venv is active. | area: SCR | related: CI.T04
- SETTLED | scripts/typecheck.sh:10-11 | "The firmware version lives in exactly one place, toolchain/versions.toml's [micropython] ref; the stub version below is derived from it" | Stub version must never be pinned separately. | area: SCR | related: SCR.T02
- PLATFORM | scripts/typecheck.sh:12, 17 | "Requires python3 >= 3.11 for tomllib" | The version derivation runs under a bare host `python3`, not the venv/uv interpreter. | area: SCR | covered-by: SCR.T09
- LIMIT | scripts/typecheck.sh:65-67 | "micropython-rp2-rpi_pico_w-stubs==${firmware_version}.*" | Stubs float across `.postN` releases and are fetched from the network on every run. | area: CI | covered-by: CI.T04
- SETTLED | scripts/typecheck.sh:76-78 | "This needs a manual decision ... there is no automatic fallback." | Missing upstream stubs for a new pin block typecheck until the owner decides. | area: SCR | -
- WORKAROUND | scripts/typecheck.sh:83-97 | "Two verified regressions in micropython-stdlib-stubs 1.29.0.post1/.post2, repaired at the stub tree" | Recreates `asyncio/futures.pyi` and un-comments `NotImplemented` in `builtins.pyi`; removal trigger: upstream re-ships the fix (repair then no-ops). Must not be replaced with `type: ignore` in src/ (CLAUDE.md). | area: PLAT | covered-by: PLAT.T05
- LIMIT | scripts/typecheck.sh:87-89 | "a fixed upstream or a restructured tree makes it a silent no-op rather than a failure" | If the stub tree moves, the repair silently stops applying; the NotImplemented stub ships CRLF. (low) | area: SCR | related: PLAT.T05
- INVAR | scripts/typecheck.sh:99-103 | "heap_headroom_after_full_system_build.py is the main pass's sole static `import sensortask_dev`" | `build/generated_src/` must be regenerated before mypy; the main pass resolves generated modules silently. | area: SCR | related: GEN.S17
- DRIFT | scripts/typecheck.sh:105-107 | "CI's lint-and-typecheck job passes `src tests`" | ci.yml passes `src tests tests_hardware/device_scripts`. | area: CI | covered-by: CI.S03
- SETTLED | scripts/typecheck.sh:111-116, 123-130 | "The twin is a fully-reviewed scope like src/ and tests/, so a finding here is real" | The twin and host passes always run and fail the script, regardless of narrowing args. | area: SCR | related: SCR.T15

## scripts/_require_clean_hardware_run.sh
- SETTLED | scripts/_require_clean_hardware_run.sh:5 | "deliberately not -e: the verdict comes from pytest's own output, not its exit code" | Verdict is derived from parsing pytest output. | area: SCR | covered-by: SCR.T08
- SETTLED | scripts/_require_clean_hardware_run.sh:7-10 | "The one permanent skip: off-subnet source-address spoofing on the bench host is unconfirmed" | `test_spoofed_off_subnet_source_address_is_ignored` is permanently whitelisted as a skip; the underlying capability is unconfirmed. | area: HW | related: SCR.T05
- INVAR | scripts/_require_clean_hardware_run.sh:8-9 | "Add a name here only for an equally deliberate, documented, permanent skip - never to silence a real one." | Whitelist growth is policed by review only. | area: HW | related: SCR.T05
- MIRROR | scripts/_require_clean_hardware_run.sh:12-47 | "The opt-in gates (tests_hardware/conftest.py's pytest_addoption()) are an EXPECTED skip only while their own flag is absent" | Hard-coded flag names and 9 test names mirror `tests_hardware/conftest.py` options and real test function names; a rename silently changes what is whitelisted. | area: HW | related: SCR.T05
- LIMIT | scripts/_require_clean_hardware_run.sh:19-24 | "[ \"$arg\" = \"--soak-tier\" ] && soak_tier=1" | Flags matched by exact token only; `--soak-tier=x` form not recognised. | area: SCR | covered-by: SCR.S01
- LIMIT | scripts/_require_clean_hardware_run.sh:71-74 | "*\"$name\"*) known=1 ;;" | Whitelist match is a substring match on the node id, so any test whose id contains a whitelisted name (e.g. parametrized variants) is also accepted as a skip. (low) | area: SCR | related: SCR.T05
- ASSUME | scripts/_require_clean_hardware_run.sh:79, 93, 101 | "grep -oE '^tests_hardware/\S+ SKIPPED'" | Skip/pass/deselect accounting depends on pytest `-v` output format (pytest is unpinned). | area: SCR | related: CI.S05
- LIMIT | scripts/_require_clean_hardware_run.sh:61-66 | "--collect-only never actually runs anything - the skip/pass accounting below doesn't apply." | A `--collect-only` run returns 0 after only pytest's exit code. | area: SCR | related: SCR.T05
- ASSUME | scripts/_require_clean_hardware_run.sh:91-92 | "pytest omits the word entirely today, so this is defensive, not observed" | Unverified claim about pytest's summary wording. | area: SCR | -
- LIMIT | scripts/_require_clean_hardware_run.sh:99-106 | "Deselected tests are invisible to every check above" | "Clean" means everything that ran passed, not everything ran (CLAUDE.md wear-gate rule). | area: HW | related: SCR.S01
- DRIFT | scripts/_require_clean_hardware_run.sh:106 | "Add --allow-persistence-writes (and/or the other --allow-* flags) to." | Truncated sentence in the user-facing verdict. | area: SCR | covered-by: SCR.S01

## scripts/mpremote_connect.sh
- INVAR | scripts/mpremote_connect.sh:2-4 | "`cp`/`rm`/`mkdir`/`rmdir` do write flash - be deliberate before passing those" | Flash wear/real-hardware discipline left to the caller; any use needs the owner's in-session go-ahead (CLAUDE.md). | area: HW | -
- ASSUME | scripts/mpremote_connect.sh:8 | "device=\"${MPREMOTE_DEVICE:-/dev/ttyACM0}\"" | Fixed default serial path. (low) | area: HW | -

## scripts/run_bench_hardware_suite.sh
- SETTLED | scripts/run_bench_hardware_suite.sh:2-3 | "bench is a strict superset of flash (SPECIFICATION.md Part E.6)" | Tier-structure claim. | area: HW | -
- SETTLED | scripts/run_bench_hardware_suite.sh:5-7, 11 | "excludes the soak markers unconditionally - they need their own deliberate invocation" | Relies on `-m` before `"$@"`; a caller's own `-m` replaces it (pytest last-wins). | area: SCR | covered-by: SCR.S01

## scripts/run_bench_soak_tests.sh
- SETTLED | scripts/run_bench_soak_tests.sh:2-4 | "a deliberate, dedicated invocation (owner's direction, 2026-09-04) that the two general suite runners never bundle" | Soak tests only run through this runner. | area: HW | -
- SETTLED | scripts/run_bench_soak_tests.sh:8-10 | "The ~12.4-day ticks_ms() rollover wait is NOT a long_soak test and no tier here runs it" | The 2^30 ms rollover test runs only via its own flag. | area: HW | -
- PLATFORM | scripts/run_bench_soak_tests.sh:8 | "The ~12.4-day ticks_ms() rollover" | Depends on rp2 `ticks_ms` period (`MICROPY_PY_TIME_TICKS_PERIOD` = 2^30). | area: PLAT | related: PLAT.T13
- LIMIT | scripts/run_bench_soak_tests.sh:14-20 | "if [ \"${1:-}\" != \"--tier\" ] || [ -z \"${2:-}\" ]" | Tier value is not validated here (delegated to conftest). (low) | area: SCR | related: SCR.T05

## scripts/run_flash_hardware_suite.sh
- SETTLED | scripts/run_flash_hardware_suite.sh:5-7, 11 | "excludes the soak markers unconditionally" | Same `-m` last-wins caveat as the bench runner. | area: SCR | covered-by: SCR.S01

## scripts/run_manual_hardware_tests.sh
- SETTLED | scripts/run_manual_hardware_tests.sh:2-3 | "interactive, never invoked by pytest, structurally separate from the automated suites" | Manual tier has no automated gate. | area: HW | -

## scripts/run_digital_twin_ci.sh
- DRIFT | scripts/run_digital_twin_ci.sh:10-11 | "Clean wipes leftover digital_twin/*.json state and digital_twin/config/ ... deliberately redundant with _digital_twin_ci_suite.py's own identical clean" | The script body (lines 20-59) contains no clean step at all; the only clean is the suite's own `_clean_state()`, so the claimed redundancy does not exist. | area: SCR | related: SCR.S09
- ASSUME | scripts/run_digital_twin_ci.sh:8 | "so each device's 14-run suite is attributable on its own" | Run count stated as 14; the suite now has numbered sub-runs (e.g. 11, 11b). (low) | area: SCR | related: SCR.T04
- MIRROR | scripts/run_digital_twin_ci.sh:25 | "export TZ=UTC  # same reasoning as scripts/test.sh's own identical export." | TZ pin duplicated in three scripts (test.sh, this, run_unix_port_integration.sh). | area: SCR | related: XCUT.T18
- LIMIT | scripts/run_digital_twin_ci.sh:28-37 | "if [ ! -x \"$micropython_bin\" ]" | Existence check only; no variant/staleness probe (unlike test.sh). | area: SCR | covered-by: SCR.S05
- RISK | scripts/run_digital_twin_ci.sh:39-47 | "Granted fresh every invocation because a cached toolchain archive does not carry xattrs" | `setcap` (sudo when non-root) on the interpreter for Run 7's port-53 DNS server. | area: SEC | covered-by: SCR.S06
- LIMIT | scripts/run_digital_twin_ci.sh:23, 50, 59 | "device=\"${1:-wozi}\"" | Device name is unvalidated and flows into paths; logs go to the fixed repo path `digital_twin_ci_logs`. | area: SCR | covered-by: SCR.T14

## scripts/run_unix_port_integration.sh
- SETTLED | scripts/run_unix_port_integration.sh:6-8 | "the twin needs its own MICROPYPATH with no \"tests\" segment (digital_twin/README.md's \"never together\" rule)" | The twin must never share test.sh's module path. | area: TWIN | related: SCR.T04
- MIRROR | scripts/run_unix_port_integration.sh:10-12 | "a test file works around the ext-less path with its own sys.path.insert, the real entry point needs the real fix" | test.sh's MICROPYPATH lacks `ext`, so a test file hand-inserts it; the real entry point adds `ext` here. | area: SCR | related: SCR.T12
- LIMIT | scripts/run_unix_port_integration.sh:24-26 | "There is no --soak flag any more: the HTTP+memory-trend soak check moved host-side" | Soak only exists as the suite's Run 11. | area: TWIN | -
- LIMIT | scripts/run_unix_port_integration.sh:36-38 | "device=\"$2\"" | `--device` with no value aborts under `set -u`; value unvalidated. | area: SCR | covered-by: SCR.T14
- RISK | scripts/run_unix_port_integration.sh:18, 24 | "--host 0.0.0.0 --port 8080 (reachable from outside)" | Documented way to expose the twin on all interfaces; default fixed port 8080. (low) | area: SEC | -
- LIMIT | scripts/run_unix_port_integration.sh:50-57 | "if [ ! -x \"$micropython_bin\" ]" | Existence check only. | area: SCR | covered-by: SCR.S05
- RISK | scripts/run_unix_port_integration.sh:59-67 | "Granted fresh every invocation" | Third `setcap` site. | area: SEC | covered-by: SCR.S06

## scripts/build_frozen_html.sh
- SETTLED | scripts/build_frozen_html.sh:2-4 | "why never --compress, and why the output goes to frozen_modules/ rather than the .frozen/ import sentinel" | Pipeline choices owned by Part A.9. | area: SCR | related: SCR.T03
- SETTLED | scripts/build_frozen_html.sh:10-11 | "ext/freezefs is vendored and unmodified. Don't copy build-wozi.sh's literal invocation" | Legacy `-s` flag gone in freezefs 2.4. | area: SCR | -
- PLATFORM | scripts/build_frozen_html.sh:30-32 | "ext/freezefs has no __init__.py (freezefs 2.4 upstream ships it as an implicit namespace package)" | Build depends on vendored freezefs 2.4 layout and CLI flags (`--on-import mount --target --overwrite always --silent`). | area: SCR | related: SCR.T03
- LIMIT | scripts/build_frozen_html.sh:7, 22 | "a space-separated list merged recursively into one build tree" / "for src_dir in $src_dirs" | Unquoted word-split loop; a directory with spaces breaks. | area: SCR | covered-by: SCR.S08
- LIMIT | scripts/build_frozen_html.sh:25 | "find \"$tmp_dir\" -type f -exec gzip -9 {} +" | No `-n`: embedded mtime makes the frozen image non-deterministic. | area: SCR | covered-by: SCR.S04
- RISK | scripts/build_frozen_html.sh:17 | "mount_target=\"/html\"" | Generated module mounts at `/html` on import; freezefs raises EEXIST if `/html` exists on the device FS. | area: XCUT | covered-by: XCUT.S14
- PLATFORM | scripts/build_frozen_html.sh:33 | "python3 -m freezefs" | Runs under bare host `python3`. | area: SCR | covered-by: SCR.T09

## scripts/build_website.sh
- DRIFT | scripts/build_website.sh:11 | "<device>     matches an html/definitions/<device>.json file, e.g. \"wozi\"." | Only wozi/dev have one; lines 26-38 generate the rest from `devices/<device>.toml`. | area: DOC | covered-by: DOC.S18
- TODO | scripts/build_website.sh:26-27 | "retiring them is deferred work (SPECIFICATION.md Part L.4)" | wozi/dev keep hand-written `html/definitions/<device>.json` because tests_js fixtures load them from disk. | area: WEB | related: WEB.S13
- INVAR | scripts/build_website.sh:20-22 | "a generated definitions.json written there would be frozen as an extra /definitions.json.gz and defeat H.7's inlining" | Generated definitions must stay in `scratch_dir`, never `stage_dir`. | area: WEB | related: WEB.T06
- PLATFORM | scripts/build_website.sh:37, 40 | "python3 -m buildgen.definitions" | buildgen and the inliner run under bare host `python3`, not uv/venv. | area: SCR | covered-by: SCR.T09
- INVAR | scripts/build_website.sh:53-57 | "escaping every one of them is what stops a field value containing \"</script\" from closing the tag early" | Inlined definitions JSON must have every `<` escaped. | area: WEB | related: WEB.T06
- MIRROR | scripts/build_website.sh:59-67 | "html/index.html's stylesheet <link> tag not found - update build_website.sh" | Exact-string contract with `html/index.html` (`<link rel=\"stylesheet\" href=\"style.css\">`, `</head>`); fails loudly on drift. | area: WEB | related: WEB.T06
- MIRROR | scripts/build_website.sh:75-78 | "concatenation of js/field-format.js, poll-manager.js, templates.js, definitions.js, render.js, nav.js, main.js (in that dependency order)" | Hand-kept bundle order duplicated in the banner and the loop; the banner points to "this script's own header comment for why", which now just defers to Part H.2. | area: WEB | covered-by: WEB.S14
- LIMIT | scripts/build_website.sh:81 | "grep -v -E '^import .* from \"\./[^\"]+\.js\";$'" | Import stripping matches only single-line, double-quoted, semicolon-terminated relative imports. (low) | area: WEB | related: WEB.T06

## scripts/setup_cross_browser_toolchain.sh
- SETTLED | scripts/setup_cross_browser_toolchain.sh:6-7 | "None of the three channels below is the obvious one for its engine" | Channel choice per engine is deliberate (Part H.7). | area: CI | -
- SUPPRESS | scripts/setup_cross_browser_toolchain.sh:10-14 | "Non-fatal, like toolchain/setup_toolchain.py's own ensure_apt_packages()" | `apt-get update` failures swallowed via `|| echo`; only installs gate. | area: CI | related: CI.T14
- RISK | scripts/setup_cross_browser_toolchain.sh:29 | "curl -sS https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor" | Apt key imported without fingerprint check. | area: CI | covered-by: CI.S18
- PLATFORM | scripts/setup_cross_browser_toolchain.sh:30 | "deb [arch=amd64 signed-by=...]" | Edge repo hardcoded to amd64. | area: CI | covered-by: CI.S06
- SETTLED | scripts/setup_cross_browser_toolchain.sh:39-40 | "Deliberately unpinned, unlike toolchain/versions.toml's MicroPython pin (Part H.7)" | Firefox/geckodriver float; `latest` micromamba fetched with no checksum (:50). | area: CI | covered-by: CI.S06
- LIMIT | scripts/setup_cross_browser_toolchain.sh:18, 27, 45 | "if ! command -v WebKitWebDriver >/dev/null 2>&1" | Idempotency by presence only; an installed but outdated engine is never refreshed. (low) | area: CI | -

## scripts/_generate_sensortask_modules.py
- SUPPRESS | scripts/_generate_sensortask_modules.py:21-24 | "from buildgen.errors import BuildError  # noqa: E402" | Four E402 suppressions (a non-sys.path statement, `REPO_ROOT = ...`, precedes the imports). | area: SCR | -
- DRIFT | scripts/_generate_sensortask_modules.py:10-12 | "Called by test.sh, typecheck.sh, run_unix_port_integration.sh and run_digital_twin_ci.sh" | Caller list omits `package.json:10` (`build:site`) and `.github/workflows/ci.yml:298`. (low) | area: SCR | related: SCR.S07
- LIMIT | scripts/_generate_sensortask_modules.py:28-51 | "(out_dir / f\"sensortask_{device}.py\").write_text(generated.module_source)" | Never prunes stale modules/plans from `build/generated_src/` and writes non-atomically while other tiers read it. | area: SCR | covered-by: SCR.S07
- ASSUME | scripts/_generate_sensortask_modules.py:30 | "Every real device, not just the two tests consume today" | Dated claim about how many devices tests consume (per-device test files now exist for all six). (low) | area: SCR | -
- MIRROR | scripts/_generate_sensortask_modules.py:47-50 | "\"instances\" is this script's addition, outside compute_twin_wiring()'s I2C/SPI-only contract" | Wiring-plan JSON schema is extended here, not in buildgen; consumers depend on both producers. | area: GEN | related: GEN.T15
- LIMIT | scripts/_generate_sensortask_modules.py:40-44 | "except BuildError as e:" | Only `BuildError` is converted to exit 1; an `OSError` on write ends as a traceback. | area: GEN | covered-by: GEN.T16

## scripts/_render_coverage.py
- SUPPRESS | scripts/_render_coverage.py:17 | "import coverage  # type: ignore[import-not-found]" | coverage is not a dev dependency, so mypy cannot see it. | area: SCR | -
- LIMIT | scripts/_render_coverage.py:4 | "# dependencies = [\"coverage\"]" | PEP 723 dependency is unpinned. | area: CI | covered-by: CI.T04
- SETTLED | scripts/_render_coverage.py:7 | "Self-contained via `uv run` ... rather than a pyproject.toml dev dependency" | Deliberate packaging choice. | area: SCR | -
- ASSUME | scripts/_render_coverage.py:56-59 | "confirmed against coverage.py's own morfs= handling" | 0%-row behaviour relies on coverage.py internals of an unpinned version; anchor glob is non-recursive (`<src_dir>/*.py`) and generated modules are never in scope. | area: TEST | related: TEST.T09
- ASSUME | scripts/_render_coverage.py:46 | "repo_root = os.getcwd()" | Must be run from the repo root; relative paths in the raw dumps are joined to cwd. (low) | area: SCR | -

## scripts/_strip_type_checking.py
- PLATFORM | scripts/_strip_type_checking.py:1-3 | "`mpy-cross` doesn't dead-code-eliminate these (SPECIFICATION.md Part B.11)" | mpy-cross optimisation behaviour at the pinned version is the reason the stripper exists. | area: PLAT | related: SCR.T03
- DRIFT | scripts/_strip_type_checking.py:11-13 | "left untouched rather than guessed at, per BACKLOG.md's original prototype note" | BACKLOG.md has no such note: dangling citation. | area: DOC | covered-by: DOC.S05
- LIMIT | scripts/_strip_type_checking.py:52-64 | "if not node.orelse and _is_bare_type_checking_test(node.test)" | `if TYPE_CHECKING: ... else:` and compound tests are kept while the import guard is removed unconditionally. | area: SCR | covered-by: GEN.S12
- PLATFORM | scripts/_strip_type_checking.py:77 | "output: str = ast.unparse(stripped_tree)" | What ships is the host-CPython-version-dependent `ast.unparse` output (comments dropped). | area: SCR | covered-by: SCR.T09
- LIMIT | scripts/_strip_type_checking.py:78 | "validity check: raises SyntaxError if the transform produced garbage" | Validated by CPython `ast.parse` only, never compiled by mpy-cross or executed by any tier. | area: SCR | covered-by: SCR.T10

## scripts/build_firmware.py
- LIMIT | scripts/build_firmware.py:7-8 | "A clean build is necessary, not sufficient, for a device to boot." | CI's firmware build proves compilation only. | area: SCR | related: SCR.T10
- SUPPRESS | scripts/build_firmware.py:27, 30, 36, 37 | "from _strip_type_checking import strip_type_checking_blocks  # type: ignore[import-not-found]  # noqa: E402" | Four E402 suppressions plus one `import-not-found`. | area: SCR | -
- MIRROR | scripts/build_firmware.py:39-45 | "Mirrors the two stock manifests combined: their require()s and freeze(\"$(PORT_DIR)/modules\") are reused unchanged" | Depends on the pinned MicroPython's stock `boards/{board}/manifest.py` layout. | area: TOOL | related: TOOL.T04
- INVAR | scripts/build_firmware.py:53-55 | "Strips this build's staged copy only, never the real src/ or ext/ file (CLAUDE.md's hard rule" | Vendored/`src` files must never be rewritten in place. | area: SCR | related: SCR.T03
- LIMIT | scripts/build_firmware.py:72-90 | "a future src/ file sharing one of those names would silently overwrite it" | Only the three reserved names are collision-checked; a module present in both `src/` and `ext/` silently resolves to `src/`. (low) | area: SCR | related: GEN.T05
- DRIFT | scripts/build_firmware.py:95-99 | "freshly generated text, never read off disk, so nothing to strip" | The generated module has its own `TYPE_CHECKING` block, frozen unstripped. | area: GEN | covered-by: GEN.S07
- PLATFORM | scripts/build_firmware.py:96-97 | "Frozen as \"main.py\" rather than \"<device>_boot.py\" ... a custom _boot.py would cost USB entirely" | Source-confirmed rp2 boot fact at the pinned version. | area: PLAT | related: PLAT.T10
- LIMIT | scripts/build_firmware.py:99 | "(stage_dir / \"main.py\").write_text(generated.boot_entry_source)" | The shipped boot entry is executed by no tier. | area: SCR | covered-by: SCR.S10
- RISK | scripts/build_firmware.py:151-158 | "mpy-cross's build/ does not self-clean per build ... so it is wiped here" | Wipes a shared toolchain build dir; unsafe under concurrent builds. | area: TOOL | covered-by: TOOL.T08
- PLATFORM | scripts/build_firmware.py:152-153 | "the rp2 port's own implicit sub-build fails from a freshly wiped directory (Part B.11)" | Version-specific build-system behaviour. | area: TOOL | -
- LIMIT | scripts/build_firmware.py:118 | "default=Path(os.environ.get(\"PICO_TOOLCHAIN_DIR\", ...))" | `--toolchain-dir` not resolved to absolute. | area: TOOL | covered-by: TOOL.S05
- LIMIT | scripts/build_firmware.py:169-173 | "except (subprocess.CalledProcessError, st.SetupError, RuntimeError)" | Other exceptions (OSError) end as tracebacks. (low) | area: SCR | related: GEN.T16

## scripts/_digital_twin_ci_suite.py
- INVAR | scripts/_digital_twin_ci_suite.py:33-36 | "MICROPYPATH = \"build/generated_src:src:digital_twin:ext:frozen_modules:.frozen\"" | Suite depends on run_digital_twin_ci.sh having regenerated `build/generated_src/` first; path duplicated in run_unix_port_integration.sh:78. | area: SCR | related: SCR.T12
- ASSUME | scripts/_digital_twin_ci_suite.py:38-40 | "PORT = 18080  # a fixed, non-privileged, non-8080-default port" / "DNS_PORT = 53 ... real port only" | Fixed ports: collides with any other listener on 18080/53 (CLAUDE.md "two suites that bind real ports"). | area: SCR | covered-by: SCR.T04
- LIMIT | scripts/_digital_twin_ci_suite.py:45-48 | "A loose set on purpose - some modules are not guaranteed to log at all in these short runs" | Verbose-log check only confirms logging flows, pins no module's output. | area: TWIN | -
- MIRROR | scripts/_digital_twin_ci_suite.py:50-60 | "the real bus-level call each driver's own bus access goes through - confirmed directly against each driver's own read/write call sites" | `_BUS_FAULT_OPS` hand-mirrors each driver's bus call in `src/`; a driver change silently misdirects the fault. | area: GEN | covered-by: GEN.T06
- MIRROR | scripts/_digital_twin_ci_suite.py:61-62 | "_NTP_ERRNO_NO_REPLY = 21  # asy_ntp_client.py's own no-reply errno" | Hand copy of an `src/` errno. | area: TWIN | related: GEN.T06
- MIRROR | scripts/_digital_twin_ci_suite.py:64-67 | "They all happen to equal driver.upper() here, which is NOT a general rule" | `_DRIVER_ERRCOUNT_NAME` is a verified narrow hand table. | area: GEN | covered-by: GEN.T06
- SETTLED | scripts/_digital_twin_ci_suite.py:68-71 | "The one registered error source deliberately not FRAM-backed: AsyFramManager builds a plain PrintLogHistory" | FRAM's own log is in-memory only by design; set pinned by `_sensortask_scenarios.py`. | area: STOR | related: XCUT.S08
- MIRROR | scripts/_digital_twin_ci_suite.py:72-82 | "_NO_PERSIST_WHEN_FRAM_FAULTED = frozenset({\"scd30\", \"bmp3xx\", \"isl29125\"})" | Hand-kept driver sets (`_MEASUREMENT_DRIVERS`, `_NO_PERSIST_WHEN_FRAM_FAULTED`, `_PERSISTED_ERROR_MODULES`) whose reasons live in digital_twin/README.md. | area: TWIN | related: GEN.T06
- MIRROR | scripts/_digital_twin_ci_suite.py:99-106 | "_WIFI_SCRIPTED_FAILURES = 5  # asy_wifi_service.py's conn_fail_to_hotspot" | Hand copies of `src/` thresholds (hotspot fallback count, supervisor 3-restart budget, episode rule's 1 slot). | area: TWIN | related: GEN.T06
- MIRROR | scripts/_digital_twin_ci_suite.py:111 | "_SERVER_OUTER_CAP_S = 15.0  # mirrors asy_webserver_service.py's own outer_cap_s default - keep in sync" | Hand-mirrored constant. | area: GEN | covered-by: GEN.T06
- ASSUME | scripts/_digital_twin_ci_suite.py:108-116 | "twin 8.259s worst, hardware 6.32s idle and 11.58s under load ... dev needs ~10 more sources to breach it" | ResetErrors budget (80% of cap) sized from dated measurements (BACKLOG item 24). | area: PERF | related: PERF.T03
- ASSUME | scripts/_digital_twin_ci_suite.py:122-125 | "100, not wozi's original 40: dev's two extra uart_link instances mean more one-time post-boot settling" | Soak warmup length from one measurement. | area: TWIN | -
- RISK | scripts/_digital_twin_ci_suite.py:127-133 | "one gc.collect()+print() per interval costs nothing measurable" | The soak's memory sampler runs `gc.collect()` inside the DUT every 25 ms, so the soak measures a heap collected far more often than either GC stage it claims to test. | area: MEM | related: TEST.T03
- ASSUME | scripts/_digital_twin_ci_suite.py:134-137 | "consecutive 25ms gc.mem_free() samples are heavily autocorrelated" | Trend tolerance (3 x quarter pstdev) grounded in a README measurement. | area: TWIN | -
- SETTLED | scripts/_digital_twin_ci_suite.py:159-162, 1304-1313 | "main() therefore runs run_suite() twice, once per value, never once with one hardcoded." | Whole suite runs at -1 then 32768 (Part I.4(e)). | area: MEM | -
- MIRROR | scripts/_digital_twin_ci_suite.py:184-187 | "_MEMORY_ERROR_MARKERS = (\"MemoryError\", \"memory allocation failed\")" | Twin-tier gate markers; must agree with test.sh and `tests_hardware/harness.py` (`tests_scripts/test_memory_error_gate_agreement.py`). | area: TEST | related: TEST.T18
- PLATFORM | scripts/_digital_twin_ci_suite.py:185 | "(py/runtime.c:1692/1696)" | Line citation into pinned MicroPython source. | area: PLAT | -
- SUPPRESS | scripts/_digital_twin_ci_suite.py:207 | "# noqa: PLC0415 - needs the path entry above" | Deferred import suppression. | area: SCR | -
- SUPPRESS | scripts/_digital_twin_ci_suite.py:446 | "# type: ignore[attr-defined]  # stashed only so _shutdown() below can close it" | Ad-hoc attribute on `Popen`. | area: SCR | -
- SUPPRESS | scripts/_digital_twin_ci_suite.py:658, 681, 712, 758, 786, 822, 873, 914, 932, 972, 1004, 1030, 1051, 1065, 1091, 1145 | "except Exception as exc:  # CI orchestration: surface any failure as a suite failure, not a crash" | 16 broad catches convert every run's exception into `_fail()`; correctness depends on each calling `_fail`. | area: SCR | related: SCR.T04
- SUPPRESS | scripts/_digital_twin_ci_suite.py:405, 477, 481 | "except OSError: pass" | Swallowed during readiness polling and best-effort /proc diagnostics ("Never allowed to raise - diagnostic only"). | area: SCR | -
- SETTLED | scripts/_digital_twin_ci_suite.py:436-437 | "S603 exemption is central, see pyproject.toml." | subprocess-without-shell exemption lives in pyproject. | area: CI | -
- INVAR | scripts/_digital_twin_ci_suite.py:295-308 | "TOLERANT: answers {} for a /status it could not parse" / "STRICT, for assertion sites: raises" | Assertions must use the strict reader; convention only. | area: TWIN | related: TEST.T17
- ASSUME | scripts/_digital_twin_ci_suite.py:383-385 | "the bench Pi4 needs ~8s where an x86 runner needs ~2s" | Host-speed figures motivating poll-not-sleep. | area: TWIN | related: TEST.T04
- INVAR | scripts/_digital_twin_ci_suite.py:487-489 | "SIGINT, not SIGTERM/terminate(): run_generic_integration.py's own graceful-shutdown path (FRAM/SCD30 flush) only runs on KeyboardInterrupt" | Shutdown contract with the twin runner. | area: TWIN | related: SCR.T04
- LIMIT | scripts/_digital_twin_ci_suite.py:519-527 | "For bounded (--duration N) runs that exit on their own" | A timeout in `_wait_exit` kills with no diagnostics (only `_shutdown` captures /proc and log tail). (low) | area: SCR | -
- LIMIT | scripts/_digital_twin_ci_suite.py:463-465 | "Linux-only, which every runner here is." | Diagnostics assume Linux /proc. (low) | area: SCR | -
- RISK | scripts/_digital_twin_ci_suite.py:615-621 | "That skip is SILENT, and it has cost real coverage: the ISL29125 ... sat outside every run here until 2026-09-18." | A new bus-attached driver is silently excluded from the fault matrix unless added to three hand tables in the same change. | area: GEN | covered-by: GEN.T06
- SETTLED | scripts/_digital_twin_ci_suite.py:726-728 | "Losing history when the chip was unavailable is accepted (owner, 2026-09-11)" | Error-history loss while FRAM is faulted is accepted. | area: STOR | -
- ASSUME | scripts/_digital_twin_ci_suite.py:734-736 | "Run 3's fault can leave a chunk torn, and the self-healing read correctly logs that as a fresh FRAM entry" | FRAM's own log excluded from Run 4's reset-to-0 sweep. | area: STOR | -
- RISK | scripts/_digital_twin_ci_suite.py:798-804 | "the restore read fails and its fallback stores the empty ring. Roughly 1 restart in 8. That loss is accepted (owner, 2026-09-11)" | Abrupt shutdown loses the whole error ring ~1 in 8; only all-or-nothing is asserted. | area: STOR | -
- ASSUME | scripts/_digital_twin_ci_suite.py:830-832 | "so no status byte is left busy and the restore is deterministic, 20/20 measured" | Commanded-reboot no-loss claim rests on a 20-trial measurement. | area: STOR | -
- LIMIT | scripts/_digital_twin_ci_suite.py:840-842 | "three at once exhaust the task-restart budget and the device reboots itself mid-run" | Faults must be applied one per process; simultaneous multi-driver faults are not tested in Run 5c. | area: TWIN | -
- ASSUME | scripts/_digital_twin_ci_suite.py:901-903 | "a read racing SCD30's cold start used to log a spurious E18/W14 pair (Part C.14.2, fixed 2026-09-12). Now only a settle window" | A settle wait remains for a fixed race. (low) | area: SENS | -
- WORKAROUND | scripts/_digital_twin_ci_suite.py:944-946 | "Only possible because of _unix_port_udp_addr_shim.py, which works around three Unix-port socket quirks" | Twin-side shim for Unix-port UDP quirks; removal trigger: none stated. | area: TWIN | related: TWIN.T07
- ASSUME | scripts/_digital_twin_ci_suite.py:962-967 | "the interpreter lacked CAP_NET_BIND_SERVICE, so the bind to port 53 silently failed" | Run 7 depends on setcap; a failed bind is silent. Timeout left at 90 s. | area: TWIN | related: SCR.S06
- ASSUME | scripts/_digital_twin_ci_suite.py:987-988 | "This once asserted counter==0, under a pre-WP1 in-memory-only assumption real CI never exercised" | Record of a stale assertion corrected. (low) | area: TWIN | -
- SETTLED | scripts/_digital_twin_ci_suite.py:1000-1001 | "192.0.2.1: RFC 5737 TEST-NET-1, guaranteed non-routable" | NTP-unreachable scenario relies on TEST-NET-1 staying non-routable on the runner. | area: TWIN | -
- ASSUME | scripts/_digital_twin_ci_suite.py:1042-1044 | "--duration 15, not 0: SGP40's first bus access now queues behind BMP3xx's and SCD30's own FRAM startup I/O" | Run 10's duration tuned to boot ordering. | area: TWIN | -
- ASSUME | scripts/_digital_twin_ci_suite.py:1076-1078 | "the readiness probe's own connection is still counted right after _wait_until_serving(), refusing one of a full burst" | Ceiling test depends on slot-release timing (Part H.7.1). | area: REST | related: REST.T06
- RISK | scripts/_digital_twin_ci_suite.py:1176-1182 | "One retry, a second fully independent boot, separates a residual bad draw from a real leak" | Soak memory-trend verdict is retried once; HTTP/WDT/shutdown failures are never retried. | area: TWIN | related: SCR.T04
- LIMIT | scripts/_digital_twin_ci_suite.py:1264-1266 | "Neopixel and notification never appear, being GPIO-only" | Fault matrix covers only bus-attached drivers; uart_link instances are not fault-injected. | area: TWIN | related: TWIN.T05
- DRIFT | scripts/_digital_twin_ci_suite.py:6 | "invoked by `scripts/run_digital_twin_ci.sh` (which owns \"clean\"/\"build\" ...)" | run_digital_twin_ci.sh performs no clean; the suite's own `_clean_state()` (:238-249) is the only one, and it removes only two named JSON files plus `config/`. | area: SCR | related: SCR.S09

## scripts/cross_browser_smoke.mjs
- LIMIT | scripts/cross_browser_smoke.mjs:13-14, 441-444 | "MicroPython Unix port not built at ${MICROPYTHON_BIN}" | Existence check only, on `build-standard`; no variant/staleness probe. | area: SCR | covered-by: SCR.S05
- INVAR | scripts/cross_browser_smoke.mjs:15-18 | "web-cross-browser-smoke job generates it fresh there, via buildgen, before this spawns" | Relies on the caller having regenerated `build/generated_src/`; running it alone uses whatever is there. | area: SCR | related: SCR.T12
- MIRROR | scripts/cross_browser_smoke.mjs:20-23, 35-36 | "see tests_js/_live_twin_command.js's own comment for the full enumeration this continues (19481, 19482 already taken" | Fixed ports 19420/4444/4445; port uniqueness is a hand-kept enumeration across files. | area: TEST | related: TEST.T14
- WORKAROUND | scripts/cross_browser_smoke.mjs:33 | "same dev-sandbox path vitest.config.js already special-cases" | Hard-coded `/opt/pw-browsers/chromium` sandbox fallback; removal trigger: none stated. | area: CI | related: CI.S15
- LIMIT | scripts/cross_browser_smoke.mjs:38-44 | "WebKit and Firefox have no device-emulation API over plain WebDriver ... MOBILE_VIEWPORT is a request, not a guarantee" | Mobile check on WebKit/Firefox is a window resize only (no touch/UA), and the width lands at ~447-500 px. | area: WEB | -
- WORKAROUND | scripts/cross_browser_smoke.mjs:134-139 | "Xvfb is spawned directly rather than through `xvfb-run`, which is a layer this file cannot reliably tear down" | Leaked Xvfb/driver processes observed with xvfb-run. | area: SCR | -
- SUPPRESS | scripts/cross_browser_smoke.mjs:63, 71, 158, 253, 258, 378, 383, 482 | "eslint-disable-next-line no-await-in-loop -- deliberate sequential polling" | Eight eslint suppressions. | area: SCR | -
- SUPPRESS | scripts/cross_browser_smoke.mjs:179, 428 | "teardown is best-effort - a dead driver is not a smoke-check failure" | Teardown errors swallowed. | area: SCR | -
- LIMIT | scripts/cross_browser_smoke.mjs:102-105, 110 | "stdio: [\"ignore\", \"ignore\", \"pipe\"]" | Twin stdout discarded, state paths empty (in-memory); no MemoryError gate on this twin launch. | area: TEST | covered-by: TEST.T18
- RISK | scripts/cross_browser_smoke.mjs:448 | "rmSync(path.join(REPO_ROOT, \"digital_twin\", \"config\"), { recursive: true, force: true });" | Wipes the shared repo-level twin config also used by the CI suite and Vitest live twins. | area: SCR | covered-by: SCR.S09
- RISK | scripts/cross_browser_smoke.mjs:476-479, 498-501 | "SKIP ${engine.name}: binary not found (run scripts/setup_cross_browser_toolchain.sh)" | A missing engine is a warning; the run passes if any engine (Chromium is always "available") ran. | area: CI | related: TEST.T16
- ASSUME | scripts/cross_browser_smoke.mjs:304-306 | "Polling only the attribute raced ahead of the caption during this file's own development" | Wait condition derived from an observed race. | area: WEB | -
- ASSUME | scripts/cross_browser_smoke.mjs:354-356 | "Given a real DISPLAY, `-headless` Firefox still uses it ... confirmed directly" | Engine behaviour claim. (low) | area: WEB | -
- LIMIT | scripts/cross_browser_smoke.mjs:432-434 | "Harmless in CI, where the VM is reclaimed anyway, and a real leak for local development." | Signal cleanup exists only for SIGINT/SIGTERM. | area: SCR | related: TEST.T16
- ASSUME | scripts/cross_browser_smoke.mjs:471-473 | "an earlier version reused one and briefly masked a real timing bug" | Unique probe values per check are load-bearing. | area: WEB | -

## toolchain/versions.toml
- PLATFORM | toolchain/versions.toml:9-10 | "ref = \"v1.29.0\"" | The single MicroPython pin; every move triggers CLAUDE.md's standing full re-check (Part F.5), stub re-derivation and the overrides' anchor checks. | area: PLAT | related: TOOL.T12
- ASSUME | toolchain/versions.toml:3-5 | "pico-sdk is derived from MicroPython's own lib/pico-sdk submodule at this ref, picotool as the newest tag matching its major.minor" | picotool floats within major.minor; only the MicroPython ref is pinned by hand. | area: TOOL | covered-by: TOOL.T02
- LIMIT | toolchain/versions.toml:7-8 | "or run the installer with --latest to write back the newest stable tag" | `--latest` moves the pin without prompting the mandatory re-check. | area: TOOL | covered-by: TOOL.S09
- LIMIT | toolchain/versions.toml:14-29 | "\"gcc-arm-none-eabi\"," | apt packages (including the ARM compiler) are distro-versioned and unpinned. | area: TOOL | covered-by: TOOL.T12
- MIRROR | toolchain/versions.toml:26-28 | "setcap, for the port-53 DNS-server test's CAP_NET_BIND_SERVICE grant: absent from a minimal image" | `libcap2-bin` is also listed by hand in CLAUDE.md's chroot recipe for reused chroots. | area: TOOL | -
- INVAR | toolchain/versions.toml:31-40 | "AN ENSEMBLE, NOT INDEPENDENT KNOBS ... three per-connection relationships lwIP does not check are all re-stated by check_lwip_ensemble()" | lwIP option set must stay coherent; enforced by `check_lwip_ensemble()`. | area: TOOL | covered-by: TOOL.T04
- MIRROR | toolchain/versions.toml:38-40 | "Sized for max_connections = 6 (Part H.7), 2,324 B of GC heap per connection" | lwIP sizing is derived from every device TOML's `max_connections = 6`; the `[lwip]` table is read by both `buildgen.model.lwip_macros` and `setup_toolchain.load_lwip_macros`. | area: GEN | related: GEN.T15
- ASSUME | toolchain/versions.toml:38 | "2,324 B of GC heap per connection" | Single measured figure behind the connection budget. | area: PERF | related: PERF.T02
- PLATFORM | toolchain/versions.toml:41-52 | "MEMP_NUM_TCP_PCB = 9" | lwIP limits apply to the firmware only; the twin runs on the host Linux stack and models none of them. | area: TWIN | related: TWIN.T08

## toolchain/micropython_overrides.py
- SETTLED | toolchain/micropython_overrides.py:1-3, 15-18 | "Re-verify against the new source and update the override's anchor/generated content (SPECIFICATION.md Part B.14) - never silence this by removing the check." | Every override fails loudly on anchor drift; re-verification trigger is any MicroPython ref move (CLAUDE.md standing practice, B.14 checklist). | area: TOOL | covered-by: TOOL.T04
- PLATFORM | toolchain/micropython_overrides.py:37-40 | "_UNIX_KBD_INTR_ANCHOR = \"#define MICROPY_ASYNC_KBD_INTR         (!MICROPY_PY_THREAD_GIL)\"" | Anchor 1 (unix_kbd_intr): exact unguarded line in `ports/unix/variants/mpconfigvariant_common.h`; re-verify on every ref move. | area: TOOL | covered-by: TOOL.T04
- PLATFORM | toolchain/micropython_overrides.py:38-39 | "a later plain #define always wins over an earlier -D (verified 2026-09-15), and the redefinition warning is a hard failure here anyway" | Preprocessor/build-flag fact the override design depends on (dated verification). | area: TOOL | -
- LIMIT | toolchain/micropython_overrides.py:43-57 | "the async/immediate nlr_raise()-from-signal-handler mechanism itself was restructured in ports/unix/unix_mphal.c's sighandler()" | The check verifies only the header line text, not the `sighandler()` mechanism, and no post-build proof shows `MICROPY_ASYNC_KBD_INTR == 0` in the binary. | area: TOOL | covered-by: TOOL.S07
- SETTLED | toolchain/micropython_overrides.py:53-55 | "Do NOT remove this check and build unpatched: the whole point is that an interrupt-mid-critical-section can corrupt VM state" | Standing rule tied to CLAUDE.md's shutdown-flake entry (Part F.6/B.14.1). | area: TOOL | -
- ASSUME | toolchain/micropython_overrides.py:75-77, 338-342 | "relay to the real files rather than copying their content, so neither can silently drift" | Relay-by-include design assumed drift-proof; `manifest.py` relayed only if it exists (:81-83). | area: TOOL | related: TOOL.T04
- PLATFORM | toolchain/micropython_overrides.py:98-103 | "Split by how the PINNED source defines each macro, because that is what decides whether a plain -D could ever be trusted for it" | Guarded vs predefined macro classification is pinned-source specific. | area: TOOL | covered-by: TOOL.T04
- PLATFORM | toolchain/micropython_overrides.py:105-118 | "The MEM_SIZE group is ONE atomic `#ifndef MEM_SIZE` block upstream, so a -D of any of it would drop TCP_MSS to lwIP's 536" | Anchor 2 set (`_LWIP_COMMON_ANCHORS`): exact default lines of `extmod/lwip-include/lwipopts_common.h`; re-verify on a ref move. | area: TOOL | covered-by: TOOL.T04
- INVAR | toolchain/micropython_overrides.py:119-125 | "lwip_inc must stay a PLAIN target-level include dir: a BEFORE form there would beat the directory-scope one this override prepends" | Anchor 3 set (`_RP2_CMAKE_ANCHORS`) guards rp2 CMake include ordering; `_RP2_LWIPOPTS_ANCHOR` (:126) and `_BOARD_CMAKE_ANCHOR` (:127) are anchors 4-5. | area: TOOL | covered-by: TOOL.T04
- SETTLED | toolchain/micropython_overrides.py:129-134 | "Do NOT remove the check and build anyway: an lwIP option that silently keeps its old value produces a firmware that accepts fewer connections" | Standing rule. | area: TOOL | -
- INVAR | toolchain/micropython_overrides.py:166-168 | "for name in (\"mpconfigboard.h\", \"manifest.py\", \"pins.csv\"):" | Board dir shape anchor: generated board dir relays exactly these three files. | area: TOOL | covered-by: TOOL.T04
- MIRROR | toolchain/micropython_overrides.py:171-173, 190-202, 214-247 | "Mirrored here to fail before the build, naming the relationship" | Python re-statement of `lib/lwip/src/core/init.c` #errors and `opt.h`'s four derived formulas; must be re-checked against lwIP whenever the pin moves. | area: TOOL | covered-by: TOOL.T04
- ASSUME | toolchain/micropython_overrides.py:175-178 | "2,000 B = the pre-branch design's own MEM_SIZE 8000 over max_connections 4 ... the configuration this project already ran in the field" | MEM_SIZE per-connection floor anchored to a prior configuration; the fielded units run legacy 1.26 firmware. | area: PERF | related: PERF.T02
- PLATFORM | toolchain/micropython_overrides.py:179-182 | "tcp_alloc() never reclaims one at equal priority; modlwip aborts it after 10 s ... The pattern every limit ever measured on silicon ran at" | SPARE_TCP_PCBS = 3 rests on lwIP/modlwip behaviour and silicon measurements. | area: PLAT | related: PLAT.T04
- PLATFORM | toolchain/micropython_overrides.py:183-186 | "IP_HLEN is 40, not 20: pbuf.h picks it on LWIP_IPV6, which ports/rp2/lwip_inc/lwipopts.h enables" | Header-size constant (74) and `_MEM_ALIGNMENT = 4` hand-copied from pinned sources. | area: PLAT | covered-by: TOOL.T04
- PLATFORM | toolchain/micropython_overrides.py:214-215 | "The port leaves MEMP_MEM_MALLOC, LWIP_WND_SCALE and LWIP_DISABLE_*_SANITY_CHECKS at 0 and LWIP_TCP/LWIP_UDP at 1" | Unverified-at-runtime assumption about port config that makes every check live. | area: PLAT | covered-by: TOOL.T04
- SUPPRESS | toolchain/micropython_overrides.py:224 | "# noqa: PLR2004 - init.c's own literal" | Magic-number suppression. | area: TOOL | -
- MIRROR | toolchain/micropython_overrides.py:248-253, 293-296 | "The N-connection ones are checked per device by buildgen, which knows N." | Per-connection lwIP relationships are validated only through buildgen's per-device call, not at toolchain build time. | area: GEN | related: GEN.T15
- PLATFORM | toolchain/micropython_overrides.py:269-271 | "modlwip.c's tcp_write() always sets TCP_WRITE_FLAG_COPY" | Pinned-source fact behind the MEM_SIZE floor. | area: PLAT | related: PLAT.T04
- INVAR | toolchain/micropython_overrides.py:318-321, 448-458 | "The sentinel closes the one hole a value comparison cannot" | Post-build proof for lwIP (sentinel + preprocessor readback); none exists for unix_kbd_intr. | area: TOOL | covered-by: TOOL.T11
- LIMIT | toolchain/micropython_overrides.py:329-336 | "include_directories(BEFORE \"{include_dir}\")" | Generated CMake/make include paths are unquoted in `include(...)`; relative paths or spaces break. | area: TOOL | covered-by: TOOL.S05
- LIMIT | toolchain/micropython_overrides.py:355-388 | "lwIP options are arithmetic over literals, and anything else must fail loudly, not guess" | Readback evaluator supports only + - * / << >>; any cast/ternary in a future lwIP option fails the build. | area: TOOL | -
- ASSUME | toolchain/micropython_overrides.py:391-402 | "else the toolchain's usual name on PATH" | Falls back to `arm-none-eabi-gcc` on PATH if CMake's record is missing. (low) | area: TOOL | -
- PLATFORM | toolchain/micropython_overrides.py:409, 417-420 | "flags.make ... has no {key} line - CMake's generated layout has changed" | Readback depends on CMake's `CMakeFiles/firmware.dir/flags.make` layout (C_DEFINES/C_INCLUDES/C_FLAGS). | area: TOOL | related: TOOL.T11

## toolchain/setup_toolchain.py
- WORKAROUND | toolchain/setup_toolchain.py:33-36, 335, 379 | "Confirmed GCC >=14 false positive in mbedtls_xor(), not a real bug ... See Part B.7.1 for the periodic-recheck instructions before ever removing this." | `-Wno-array-bounds` is passed via CFLAGS_EXTRA to the whole rp2 firmware and both Unix-port builds, not only mbedtls; removal trigger: B.7.1's periodic recheck. | area: TOOL | related: CI.T10
- SUPPRESS | toolchain/setup_toolchain.py:36 | "_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND = \"-Wno-array-bounds\"" | Compiler-warning class disabled build-wide (every translation unit), while any other warning fails the build. | area: TOOL | related: TOOL.T10
- INVAR | toolchain/setup_toolchain.py:73-82 | "never the caller's raw environment ... build failure detection greps build output for literal English \"error:\"/\"warning:\"" | Fixed PATH/locale allowlist; failure detection is an English-text grep (Part B.4/B.7). | area: TOOL | covered-by: TOOL.T10
- INVAR | toolchain/setup_toolchain.py:84-91 | "Named explicitly rather than inherited wholesale, so it stays only ever these variables." | Proxy/CA allowlist for network steps; `PIP_CERT` and others are not in it. | area: TOOL | related: TOOL.T01
- RISK | toolchain/setup_toolchain.py:110-118 | "print(f\"$ {' '.join(cmd)}\"" | Every command, including the bench AP password (:916-921), is echoed with full argv; output is buffered until exit and there is no timeout. | area: SEC | covered-by: TOOL.S01
- MIRROR | toolchain/setup_toolchain.py:121 | "UV_SYNC_ATTEMPTS = 3  # mirrors ci.yml's unit-tests job" | Retry count hand-mirrored from CI. | area: CI | related: CI.S17
- WORKAROUND | toolchain/setup_toolchain.py:124-133 | "uv sync builds actionlint-py, which fetches its binary from a release URL; a 502 there once failed a clean install" | Retry around a third-party download; removal trigger: none stated. | area: CI | related: CI.T04
- LIMIT | toolchain/setup_toolchain.py:154-157 | "new_text = re.sub(r'(?m)^ref = \".*\"$', f'ref = \"{ref}\"', text, count=1)" | Rewrites the first `ref = ` line; silent no-op if nothing matches. | area: TOOL | covered-by: TOOL.S09
- SUPPRESS | toolchain/setup_toolchain.py:166-168 | "Non-fatal: unrelated third-party sources some environments have configured (PPAs etc.)" | `apt-get update` failure ignored (`check=False`). | area: TOOL | covered-by: TOOL.T10
- RISK | toolchain/setup_toolchain.py:169-172 | "[\"sudo\", \"env\", \"DEBIAN_FRONTEND=noninteractive\", \"apt-get\", \"install\"" | `sudo env` likely drops proxy variables set in `network_env()`. | area: TOOL | covered-by: TOOL.S04
- SETTLED | toolchain/setup_toolchain.py:184-186 | "Deliberately a full clone, not `--depth 1`" | In-place update is a first-class requirement. | area: TOOL | -
- SUPPRESS | toolchain/setup_toolchain.py:195-200 | "except SetupError: # The commit wasn't already present locally ... fetch it directly by hash. pass" | Checkout failure swallowed then retried via fetch-by-hash. | area: TOOL | related: TOOL.T02
- LIMIT | toolchain/setup_toolchain.py:193 | "[\"git\", \"fetch\", \"--quiet\", \"--tags\", \"--force\", \"origin\"]" | Tags are force-fetched (a moved upstream tag is silently accepted); pin is a tag, not a SHA. | area: TOOL | covered-by: TOOL.T02
- ASSUME | toolchain/setup_toolchain.py:224-233 | "read straight out of MicroPython's own submodule pin at lib/pico-sdk" | pico-sdk derivation parses `git ls-tree` output shape. | area: TOOL | -
- PLATFORM | toolchain/setup_toolchain.py:236-255 | "(\"Incompatible picotool installation found\" since pico-sdk 2.0.0)" | picotool = newest tag matching pico-sdk major.minor, from a live `ls-remote` (floats). | area: TOOL | covered-by: TOOL.T02
- RISK | toolchain/setup_toolchain.py:258, 276 | "run([\"sudo\", \"make\", \"install\"], cwd=build_dir, env=env)" | Every `setup` (including test.sh's auto-build) installs picotool into `/usr/local` as root. | area: TOOL | covered-by: TOOL.S08
- LIMIT | toolchain/setup_toolchain.py:292-294 | "if re.search(r\"\bwarning:\", out, re.IGNORECASE):" | mpy-cross build checks warnings but not `error:` text (relies on exit code). (low) | area: TOOL | related: TOOL.T10
- INVAR | toolchain/setup_toolchain.py:321-350 | "Always applies and then verifies the lwip_connection_counts override" | Every firmware build (incl. the verification chain) goes through the override and its post-build readback. | area: TOOL | covered-by: TOOL.T04
- PLATFORM | toolchain/setup_toolchain.py:353-357, 375 | "settrace_flag = \"-DMICROPY_PY_SYS_SETTRACE=1 \" if settrace else \"\"" | The settrace variant is the same `standard` variant plus a `-D`, which works only because `MICROPY_PY_SYS_SETTRACE` is `#ifndef`-guarded upstream (unlike `MICROPY_ASYNC_KBD_INTR`). | area: PLAT | related: TOOL.T05
- ASSUME | toolchain/setup_toolchain.py:373-374 | "the Makefile's own `BUILD ?= build-$(VARIANT)` already lands the settrace-free rig in build-standard, which every other script resolves" | Build dir naming relies on upstream Makefile default; five scripts hard-code `build-standard`. | area: TOOL | related: SCR.S05
- DRIFT | toolchain/setup_toolchain.py:491-493, 540-547 | "The 8-step frozen-bytecode verification chain" / "8. Vanilla Unix port rebuilt as the standing test rig" | The settrace build (:517) is an unlisted extra step; the printed summary never mentions it. (low) | area: TOOL | related: TOOL.T11
- LIMIT | toolchain/setup_toolchain.py:458-469 | "the only way this can succeed is if the module was actually baked into the binary" | The chain proves freezing works with a probe module, not that the project's own frozen set or overrides landed. | area: TOOL | covered-by: TOOL.T11
- LIMIT | toolchain/setup_toolchain.py:479-481 | "the verification chain builds the default variant, never the settrace one" | Frozen-bytecode verification is never run against the settrace binary. (low) | area: TOOL | -
- LIMIT | toolchain/setup_toolchain.py:554-560 | "mpy_ref = args.micropython_ref" | `--micropython-ref` builds a ref recorded nowhere; `--latest` rewrites the pin without the re-check. | area: TOOL | covered-by: TOOL.S06
- ASSUME | toolchain/setup_toolchain.py:619-621 | "Submodules are assumed already fetched." | `test` subcommand is offline and trusts the existing checkout. | area: TOOL | -
- ASSUME | toolchain/setup_toolchain.py:629-632 | "matching on vendor ID alone is enough to find \"some Pico-family board\"" | Any Raspberry Pi vendor-ID device (e.g. a debug probe) counts as a Pico. (low) | area: HW | -
- LIMIT | toolchain/setup_toolchain.py:686-691 | "log(\"Skipping dialout group check (--skip-apt)\")" | `--skip-apt` also skips the dialout group step. | area: TOOL | covered-by: TOOL.S04
- ASSUME | toolchain/setup_toolchain.py:734-736 | "Raspberry Pi OS does not install by default - confirmed on the real bench Pi4" | Bench-host package fact. | area: HW | -
- MIRROR | toolchain/setup_toolchain.py:790-794 | "Connection names match dev_legacy/README.md's manual nmcli recipe exactly" | `br0`/`br0-eth0`/`br0-wifi-ap` must stay identical to the manual recipe. | area: TOOL | related: TOOL.T03
- RISK | toolchain/setup_toolchain.py:815-840 | "Idempotent: loads br_netfilter and enables net.bridge.bridge-nf-call-iptables=1" | Persistent host-wide kernel/sysctl files written as root; temp file leaks if `sudo cp` fails. | area: TOOL | covered-by: TOOL.S04
- SETTLED | toolchain/setup_toolchain.py:843-846, 860-862 | "A bridge MAC mismatch is flagged, never auto-repaired" | Repairing a live bridge's MAC needs a human decision (SSH-loss risk). | area: TOOL | related: TOOL.T03
- RISK | toolchain/setup_toolchain.py:852-859 | "Self-heal a bridge created before the channel-pinning fix" | Re-runs `nmcli connection modify/up` on an existing live AP with no dead-man's switch armed. | area: TOOL | related: TOOL.T03
- INVAR | toolchain/setup_toolchain.py:868-871 | "`--escape no` is load-bearing" | Without it the MAC comparison always mismatches and prints a remedy that cycles a live bridge. | area: TOOL | related: TOOL.T03
- RISK | toolchain/setup_toolchain.py:893-925 | "run([\"sudo\", \"nmcli\", \"connection\", \"up\", BENCH_ETH_CONN], env=env)" | Bridge creation enslaves the uplink with no dead-man's switch (the 2026-09-04 lockout operation). | area: TOOL | covered-by: TOOL.S03
- PLATFORM | toolchain/setup_toolchain.py:906-908 | "NetworkManager picked channel 13, which the Pico W's cyw43439 did not associate with reliably" | AP pinned to channel 6 / band bg based on a bench finding. | area: HW | -
- RISK | toolchain/setup_toolchain.py:915-921 | "\"wifi-sec.pmf\", \"disable\"" | Bench AP runs WPA2-PSK with PMF disabled; password passed and printed in argv (:924). | area: SEC | covered-by: TOOL.S01
- SETTLED | toolchain/setup_toolchain.py:929-931 | "so there is exactly one pin rather than a second one living here" | Node major is taken from `.nvmrc` only. | area: CI | -
- LIMIT | toolchain/setup_toolchain.py:951-966, 992 | "Resolved rather than assembled: the patch version moves" | Node floats within the major (`latest-vNN.x`); arch map covers aarch64/x86_64 only. | area: CI | covered-by: TOOL.T13
- RISK | toolchain/setup_toolchain.py:996-1003 | "Verified against the same SHASUMS the filename came from" | Checksum from the same origin, no signature; `next(...)` without default raises a raw StopIteration. | area: CI | covered-by: TOOL.S02
- LIMIT | toolchain/setup_toolchain.py:1014-1019 | "run_retried([\"uv\", \"sync\"], cwd=repo_root)" | `uv sync` without `--locked`/`--frozen`; inherits caller env. | area: CI | related: CI.S04
- RISK | toolchain/setup_toolchain.py:1042-1060 | "non-fatal throughout, so a Python-only machine still finishes `env`" | Playwright install failure is logged and `env` still reports the tier "ready". | area: CI | covered-by: TOOL.T13
- LIMIT | toolchain/setup_toolchain.py:1063-1068 | "run_setup(args, versions_path, versions)" | Every `env` tier always runs a full `setup` (sudo apt, picotool install). | area: TOOL | covered-by: TOOL.T13
- SETTLED | toolchain/setup_toolchain.py:1147-1153 | "Backward/convenience compat: `setup_toolchain.py [--some-setup-flag ...]` (no subcommand) still means \"setup\"" | Implicit default subcommand kept deliberately. | area: TOOL | -

## buildgen/__init__.py
- INVAR | buildgen/__init__.py:1-3 | "Never imports `src/`; everything is derived by parsing TOML and AST-parsing driver source." | The never-import rule forces every src/ fact buildgen needs to be AST-read or hand-duplicated (see validate.py/codegen.py mirrors). | area: GEN | related: GEN.T06

## buildgen/buildspec.py
- SETTLED | buildgen/buildspec.py:5-7 | "The one hand-maintained per-driver table here ... It cannot be derived ... Adding a driver adds a row (Part L.6)." | Hand-maintained per-driver catalog, settled as such. | area: GEN | covered-by: GEN.T06
- ASSUME | buildgen/buildspec.py:1-3 | "datasheet-checked by Session 2, not re-derived here" | Address facts rest on an earlier session's datasheet check; "Session 2" is an undefined historical label. (low) | area: GEN | related: DOC.S16
- PLATFORM | buildgen/buildspec.py:29-31 | "0x44 is hard-wired (no address-select pin, datasheet p15) ... the INT line is open-drain (p6)" | ISL29125 datasheet facts behind the schema. | area: SENS | -
- INVAR | buildgen/buildspec.py:49-51 | "Every BUS_ATTACHED_DRIVERS member belongs here." | `BUS_KIND_BY_DRIVER` must cover every bus-attached driver; convention only. | area: GEN | related: GEN.T13
- PLATFORM | buildgen/buildspec.py:61-63 | "BMP388/390: SDO pin selects 0x76/0x77" | Only bmp3xx is address-capable; datasheet fact. | area: SENS | -

## buildgen/defaults.py
- LIMIT | buildgen/defaults.py:36-45 | "positional = (item.args.posonlyargs + item.args.args)[1:]  # drop \"self\"" | `_Default*` schema reads positional parameters only; keyword-only args are ignored. | area: GEN | covered-by: GEN.S10
- LIMIT | buildgen/defaults.py:36-38 | "_path/_device/_driver are unused while this has no error path" | Unused context params kept for shape. (low) | area: GEN | -

## buildgen/driver_registry.py
- SETTLED | buildgen/driver_registry.py:13-21 | "Drivers that cannot follow the asy_<name>_driver.py/*_Reader convention" | `_OVERRIDES` hand table (fram/neopixel/notification/uart_link). | area: GEN | covered-by: GEN.T13
- SETTLED | buildgen/driver_registry.py:28-31 | "uart_link is excluded on purpose - it needs the same override, but a device wires two instances" | `SINGLETON_SERVICE_DRIVERS` excludes uart_link (CLAUDE.md UART rule). | area: GEN | covered-by: GEN.T13
- ASSUME | buildgen/driver_registry.py:62-64 | "SensorReaderConfig subclasses always need it ... bare SensorReader subclasses never do" | `needs_setup` inference from the base class, or `async def setup` for services. | area: GEN | related: GEN.T13
- INVAR | buildgen/driver_registry.py:108-110 | "`_NAME = const(\"SCD30\")` (or a plain `_NAME = \"SCD30\"`) - the instance_name()/REST-key identity space" | Two naming spaces (TOML driver/name_ext vs `_NAME`) must never be conflated. | area: GEN | -

## buildgen/errors.py
- INVAR | buildgen/errors.py:1-3 | "every abort names exactly what's wrong and where - device, instance/bus, field - never a raw traceback" | Fail-loud contract; several raw-exception paths are already seeded. | area: GEN | covered-by: GEN.T01

## buildgen/frozen_modules.py
- MIRROR | buildgen/frozen_modules.py:10-30 | "mandatory infra plus the modules build_system() itself always imports directly" | `CORE_MODULES` is a hand mirror of codegen's emitted imports; no test ties them. | area: GEN | covered-by: GEN.S11
- LIMIT | buildgen/frozen_modules.py:41-42 | "continue  # never executes on-device - not a real frozen-module dependency" | Skips a whole `if TYPE_CHECKING:` node including its `else:` branch. | area: GEN | covered-by: GEN.S11
- ASSUME | buildgen/frozen_modules.py:47 | "level>0 (relative) doesn't occur in this flat layout" | Relative imports silently ignored. (low) | area: GEN | -
- LIMIT | buildgen/frozen_modules.py:53-61 | "tree = ast.parse(path.read_text(), filename=str(path))" | No `SyntaxError -> BuildError`; a module present in both roots resolves to `src/`. | area: GEN | covered-by: GEN.S11
- DRIFT | buildgen/frozen_modules.py:3 | "feeding them to freeze() is Session 6's job" | Retired session label; the job is `scripts/build_firmware.py`. (low) | area: DOC | related: DOC.S16

## buildgen/generate.py
- DRIFT | buildgen/generate.py:2-3 | "callers decide where to write them (Session 6 owns the real `build/<device>/` tree)" | No `build/<device>/` tree exists (outputs are `build/generated_src/` and `build/firmware-<device>.uf2`); SPECIFICATION.md L.2 (:6027) states the same layout. | area: DOC | related: DOC.S16
- DRIFT | buildgen/generate.py:42, 57 | "write sensortask_<device>.py/<device>_boot.py here" | CLI names the boot entry `<device>_boot.py`, but firmware freezes it as `main.py` because a custom boot module "would cost USB entirely" (build_firmware.py:96-97). (low) | area: GEN | related: GEN.T16
- LIMIT | buildgen/generate.py:45-49 | "except BuildError as e:" | Only BuildError is caught; write errors end as tracebacks. | area: GEN | covered-by: GEN.T16

## buildgen/graph.py
- SUPPRESS | buildgen/graph.py:16 | "# type: ignore[arg-type]" | Host-side type suppression. | area: GEN | -
- INVAR | buildgen/graph.py:30-32 | "sysfunct/conn/ntp are mandatory infra that inherit the device's FRAM chip implicitly ... webserver needs no entry ... codegen always emitting it last" | Ordering assumptions shared with codegen. | area: GEN | related: XCUT.T01
- LIMIT | buildgen/graph.py:47-52 | "warn_* ... and Part L.6.3's generalized per-value measurement wiring share this exact shape, so one loop covers both" | Any `{source}` sub-table adds an edge, including stray `warn_*` keys on non-notification instances. | area: GEN | covered-by: GEN.S05
- SETTLED | buildgen/graph.py:54-56 | "Stable priority tie-break: mandatory infra first ... then original TOML declaration order" | Determinism of construction order. | area: GEN | related: GEN.T11

## buildgen/limits.py
- INVAR | buildgen/limits.py:14-16 | "It must still carry range or choice-set punctuation, or prose beginning \"@limits\" would read as a tag" | Tag-vs-prose heuristic. | area: GEN | covered-by: GEN.T03

## buildgen/model.py
- INVAR | buildgen/model.py:26-28 | "The TOML's own driver/name_ext identity, never instance_name()/_NAME ... NotificationCoordinator's _NAME is \"NOTIFY\"" | Identity-space separation. | area: GEN | -
- ASSUME | buildgen/model.py:70-81 | "splitting the last \"_\"-group off as name_ext - which only a synthetic fixture needs today" | Wiring resolution fallback; unresolved keys returned for the caller to reject. | area: GEN | related: GEN.T04
- MIRROR | buildgen/model.py:127-140 | "versions.toml's whole [lwip] table" | Second reader of `[lwip]` (the other is `setup_toolchain.load_lwip_macros`). | area: GEN | covered-by: GEN.T15

## buildgen/pico_gpio.py
- PLATFORM | buildgen/pico_gpio.py:1-3 | "transcribed from RP-008312-DS-2-pico-w-datasheet.pdf Figure 2 (printed p.4)" | GPIO legality derived from the board figure, not RP2040 silicon function tables. | area: GEN | covered-by: GEN.T07
- LIMIT | buildgen/pico_gpio.py:9-10, 26-27, 31-37 | "GP22/GP28 have no I2C function at all" / "GP20-22/GP26-28 have no SPI function" | Conservative tables (e.g. no UART1 on GP20/21, no SPI on GP20-22/26-28) reject pins silicon supports. | area: GEN | covered-by: GEN.T07
- PLATFORM | buildgen/pico_gpio.py:5, 36-37 | "WIRELESS_RESERVED_GPIOS = frozenset({23, 24, 25, 29})" | Pico W wireless-reserved GPIOs (datasheet p.7). | area: PLAT | covered-by: GEN.T07
- MIRROR | buildgen/pico_gpio.py:39-41 | "asy_uart_driver.py's module comment names GPIO24/25 and GPIO28/29 - a true claim about the RP2040 die's silicon mux" | Cross-file claim reconciled by comment only. | area: GEN | related: GEN.T07

## buildgen/requires_tag.py
- DRIFT | buildgen/requires_tag.py:2, 59 | "placed at module level near `_WIRING`/`_VAL_*`" | Stale reference to `_VAL_*` placement. | area: GEN | covered-by: GEN.S14
- LIMIT | buildgen/requires_tag.py:79-81 | "_check_bus_tables() validates only the bus fields it knows by name, not every field an @requires tag might name" | Coercion must handle arbitrary TOML types; `nan`/`inf` accepted. | area: GEN | covered-by: GEN.S10

## buildgen/schema_ast.py
- LIMIT | buildgen/schema_ast.py:1-3, 44-46 | "Best-effort, never-imported AST extraction ... Anything else is silently skipped" | A schema constant in an unexpected shape silently drops out of the generated website definitions. | area: GEN | related: GEN.S10
- MIRROR | buildgen/schema_ast.py:12, 36-37 | "config_manager.py's own FieldSchema width: (name, type, default, min, max, special)" | 6-tuple shape hand-mirrored from `src/config_manager.py`. | area: GEN | related: GEN.T15

## buildgen/tag_comments.py
- SETTLED | buildgen/tag_comments.py:1-3, 238-240 | "a driver signature change once silently broke two tests_hardware/device_scripts/ call sites for a full day" | Near-miss tags must fail the build (L.5 standing rule). | area: GEN | covered-by: GEN.T03
- INVAR | buildgen/tag_comments.py:21 | "A new family goes here, plus its own strict-grammar module beside requires_tag.py." | Registration of new tag families is by convention. | area: GEN | related: GEN.T03
- DRIFT | buildgen/tag_comments.py:121-126, 142-143 | "3-4 letters (the planned \"@web\")" / "the planned \"@web-group\" shape" | `@web`/`@web-group` are implemented (web_tag.py), not planned. | area: GEN | covered-by: GEN.S14
- DRIFT | buildgen/tag_comments.py:142-149 | "A tag name is a word, optionally hyphenated ... anything after the first non-word character is payload" | Comment appears to sit above the wrong regex. | area: GEN | covered-by: GEN.S15
- LIMIT | buildgen/tag_comments.py:161-164, 188-200 | "inside a class/function body, i.e. NOT module level" | Module-level detection heuristic (column-0 comment inside a function body reads as module level). | area: GEN | covered-by: GEN.S10
- ASSUME | buildgen/tag_comments.py:260-262 | "\"required\"/\"require\" are within edit distance 2 of \"requires\" but are also ordinary English" | Typo detection requires the `@` sigil; a sigil-less typo is invisible by design. | area: GEN | covered-by: GEN.T03

## buildgen/twin_wiring.py
- MIRROR | buildgen/twin_wiring.py:9-12 | "FIXED_ADDRESSES: \"dict[str, int]\" = {\"scd30\": 0x61, \"sgp40\": 0x59, \"isl29125\": 0x44}" | Hand copy of each driver's default I2C address. | area: GEN | covered-by: GEN.T06
- MIRROR | buildgen/twin_wiring.py:35-36 | "the same shape `digital_twin/machine.py`'s `configure_wiring()` consumes" | Unversioned JSON contract with the twin. | area: GEN | covered-by: GEN.T15
- LIMIT | buildgen/twin_wiring.py:56-59 | "raise ValueError(f\"digital twin twin_wiring has no address rule" | Raw `ValueError`, not `BuildError`, for a future driver. | area: GEN | covered-by: GEN.S10
- ASSUME | buildgen/twin_wiring.py:16-18 | "None on every device but \"dev\" today." | Only dev wires a UART pair. | area: GEN | -

## buildgen/value_wiring.py
- INVAR | buildgen/value_wiring.py:1-3 | "the per-value measurement wiring that generalizes `warn_*`'s `{source, field}` shape" | `field` existence on the source's data is not checked at build time. | area: GEN | covered-by: GEN.S06

## buildgen/version.py
- SETTLED | buildgen/version.py:1-3 | "bump FIRMWARE_VERSION/WEBSITE_VERSION by hand; no automation exists or is planned" | Hand-bumped versions (`2.0b0`). | area: GEN | covered-by: GEN.T14
- DRIFT | buildgen/version.py:3 | "(see that session's own account for the full consumer list/reasoning)" | Dangling reference to an unnamed session. (low) | area: DOC | related: DOC.S05
- PLATFORM | buildgen/version.py:5 | "from datetime import UTC, datetime" | Requires host CPython >= 3.11. | area: SCR | covered-by: SCR.T09

## buildgen/web_tag.py
- DRIFT | buildgen/web_tag.py:19-21 | "Escaping a literal '\"' inside a quoted value is deliberately unsupported (see module docstring)." | The module docstring does not discuss it. | area: GEN | covered-by: GEN.S14
- MIRROR | buildgen/web_tag.py:30-32 | "js/definitions.js's own validateFieldHints() ceiling ... kept in step by hand" | `_MAX_DECIMALS` Python↔JS hand mirror. | area: GEN | covered-by: GEN.T15
- MIRROR | buildgen/web_tag.py:186-187 | "Mirrors js/definitions.js's own validateFieldHints() rule: a PUT body is always flat" | Writable-field path rule duplicated in JS. | area: GEN | related: GEN.T15
- LIMIT | buildgen/web_tag.py:100-102 | "Dot-joined rather than a JSON array" | Array-valued hints encoded as dot-joined strings. (low) | area: GEN | -

## buildgen/wiring.py
- INVAR | buildgen/wiring.py:15-17 | "dropping any one of the five leaves the line matching no tag at all - which check_for_near_miss_tags() then reports" | Tag grammar relies on near-miss detection to catch partial tags. | area: GEN | covered-by: GEN.T03

## buildgen/codegen.py
- MIRROR | buildgen/codegen.py:17-21 | "_MAX_MODULE_ERROR = 5" | Hard-coded `_MAX_MODULE_ERROR`/`_DNS_TIMEOUT_MS`/`_DNS_TRIES`/`_NTP_FETCH_TIMEOUT_MS` emitted identically into every device. (low) | area: GEN | related: GEN.T06
- SETTLED | buildgen/codegen.py:23-31 | "Every real device TOML uses identical threshold and colour values with no per-device override, so this hardcodes what the hand-written modules already did" | `_KNOWN_SIGNALS` catalog; mirrored by `definitions._WARN_SIGNAL_WEB_CATALOG`. | area: GEN | covered-by: GEN.T06
- TODO | buildgen/codegen.py:280-281 | "only knows {sorted(_KNOWN_SIGNALS)} for now - ... or flag it as a future TOML-schema extension" | A new warn_* signal needs a code change; per-device thresholds are future work. | area: GEN | -
- SUPPRESS | buildgen/codegen.py:262 | "# type: ignore[union-attr]" | Host-side suppression. | area: GEN | -
- SUPPRESS | buildgen/codegen.py:301 | "import frozen_html  # type: ignore[import-not-found]  # noqa: F401" | Emitted into every generated (shipped) module. | area: GEN | related: GEN.S17
- SUPPRESS | buildgen/codegen.py:303 | "from microdot import Microdot  # type: ignore[import-not-found]" | Emitted into every generated module. | area: GEN | related: GEN.S17
- SUPPRESS | buildgen/codegen.py:604, 607, 608, 609, 612, 613, 616 | "SettingsGroup(conn, (\"LedWifiOn\",)),  # type: ignore[arg-type]" | Seven `arg-type` ignores emitted into generated firmware code (never checked: generated output is outside mypy reporting). | area: GEN | related: GEN.S17
- DRIFT | buildgen/codegen.py:360-361, 375-376 | "mirrors build_system()'s documented shape in every hand-written sensortask_*.py" | No hand-written module exists since L.2. | area: GEN | covered-by: GEN.S16
- LIMIT | buildgen/codegen.py:336-343 | "lines.append(\"if TYPE_CHECKING:\")" | Generated module's own TYPE_CHECKING block ships unstripped. | area: GEN | covered-by: GEN.S07
- PLATFORM | buildgen/codegen.py:348-350 | "lines.append(f\"_FIRMWARE_VERSION = const({FIRMWARE_VERSION!r})\")" | Emits `const('<str>')`; depends on MicroPython 1.29 accepting string consts. | area: PLAT | covered-by: GEN.T14
- RISK | buildgen/codegen.py:381 | "lines.append(\"    watchdog = WDT(timeout=8000)\")" | Hard-coded 8000 ms WDT (CLAUDE.md: fixed, never per-device) created before every constructor. | area: XCUT | covered-by: XCUT.S13
- LIMIT | buildgen/codegen.py:383-396, 405-411 | "timeout_kw = f\", timeout={bus_table['timeout']}\"" | TOML values emitted into source via `str()`/f-strings; safety depends entirely on validate.py type checks. | area: GEN | covered-by: GEN.T02
- LIMIT | buildgen/codegen.py:426-429 | "lines.append(f\"    conn.set_ext_led(" | Hard-coded consumer for `led_target`, not the tag's target. | area: GEN | covered-by: GEN.S09
- SETTLED | buildgen/codegen.py:405-407 | "hostname/hotspot_password are [device]'s values, passed as the DEFAULTS of the two ConfigManager-persisted fields" | Device identity/hotspot password injected as defaults (shared hotspot password accepted-risk rule). | area: GEN | related: GEN.T08
- LIMIT | buildgen/codegen.py:438 | "lines.append(\"    timers_running = ThreadSafeFlag()\")" | Dead generated global. | area: GEN | covered-by: GEN.S13
- INVAR | buildgen/codegen.py:441-443 | "fram must precede sysfunct ... The other order left CFGMGR_SYSTEM degrading every boot, 0ms against ~170ms" | Setup-order invariant with a single measurement. | area: XCUT | related: XCUT.T01
- SETTLED | buildgen/codegen.py:456-458, 466 | "Measure B (SPECIFICATION.md Part I.4(f.1)): one collect before the batch and one after each module, nowhere else." | The owner-approved boot-confined `gc.collect()` exception; enforced by lint.sh:46-49, `test_gc_collect_sites.py`, `test_digital_twin_boot_contiguity.py`. | area: MEM | -
- INVAR | buildgen/codegen.py:462-465 | "fed after every one-time setup() call, never inside a loop" | Watchdog feed placement; `setup()` return values are ignored. | area: XCUT | related: XCUT.T01
- RISK | buildgen/codegen.py:502-504 | "the accepted residual risk is power loss between response and write (Part F.2)" | Accepted risk for staged config writes. | area: XCUT | related: XCUT.T10
- MIRROR | buildgen/codegen.py:547-548 | "sysfunct.pause_permanent_storage(300)" | 300 s mempause duration mirrored as "Pause backups for 5 minutes" in `definitions.py:59`. (low) | area: GEN | -
- LIMIT | buildgen/codegen.py:563-567 | "lines.append(\"    assert sgp40 is not None\")" | Bare global `sgp40` for any sgp40 instance; breaks under name_ext. | area: GEN | covered-by: GEN.S01
- SETTLED | buildgen/codegen.py:631-633 | "Only the initiator side owns real transfer/failure counts" | Responder reports no link status. | area: UART | -
- INVAR | buildgen/codegen.py:644-645 | "validate.py has already checked THAT value against the firmware's lwIP PCB count" | Emitted `max_connections`/`backlog` rely on validate.py's lwIP cross-check. | area: GEN | covered-by: GEN.T15
- ASSUME | buildgen/codegen.py:660-662 | "Getting it wrong was AttributeError on every FRAM-wired device, caught only by Part L.4" | fram excluded from task/timer collectors by hand. | area: GEN | -
- PLATFORM | buildgen/codegen.py:696-709 | "matching how a real deployed unit boots today (see modules/_boot.py)" | Boot entry: `gc.threshold(32768)`, import outside `try`, `asyncio.new_event_loop()` in `finally`; executed by no tier. | area: GEN | covered-by: GEN.T14
- RISK | buildgen/codegen.py:703 | "f\"from {module} import main\\n\\n\"" | Import (and frozen_html mount) runs before any WDT exists. | area: XCUT | covered-by: XCUT.S14

## buildgen/validate.py
- PLATFORM | buildgen/validate.py:31-34 | "Pico W exposes exactly two I2C, two SPI and two UART peripheral indices" | RP2040 peripheral count fact. | area: GEN | -
- MIRROR | buildgen/validate.py:50-52 | "uart's optional fields mirror asy_uart_driver.UART's kwargs of the same name" | Allowed UART bus fields hand-mirror `src/asy_uart_driver.py`. | area: GEN | related: GEN.T15
- MIRROR | buildgen/validate.py:58-61 | "asy_uart_comm.ROLE_INITIATOR/ROLE_RESPONDER's own literal values, duplicated here rather than imported" | String literals are the contract between buildgen and src/. | area: GEN | related: GEN.T06
- MIRROR | buildgen/validate.py:64 | "_HOSTNAME_MAX_LEN = 32  # network.hostname()'s real cap; asy_wifi_service._VAL_HOST carries the same number" | Python↔src hand mirror; also a platform fact. | area: GEN | covered-by: GEN.T15
- MIRROR | buildgen/validate.py:71 | "_NTP_CHECK_TICK_S = 10  # asy_ntp_client._NTP_CHECK_INTERV" | Hand-mirrored src constant. | area: GEN | covered-by: GEN.T06
- MIRROR | buildgen/validate.py:72-73 | "_WPA2_MAX_PASSWORD_LEN = 63  # its maximum too; asy_wifi_service._VAL_HOTSPOT_PW carries the same pair" | WPA2 bounds mirrored with src. | area: GEN | covered-by: GEN.T15
- SETTLED | buildgen/validate.py:66-67 | "the checks below run against that EFFECTIVE value - so no device can outrun its firmware by simply saying nothing" | Absent optional fields validated at their class defaults (AST-read). | area: GEN | -
- RISK | buildgen/validate.py:111-119 | "one outside _VAL_HOTSPOT_PW's own bounds is dropped at boot back to the shared default - which for this field is the password published in src/, on every device at once" | Shared hardcoded hotspot password is the fallback (accepted risk per CLAUDE.md). | area: SEC | related: GEN.T08
- PLATFORM | buildgen/validate.py:112-113 | "below it the CYW43 cannot bring the hotspot up at all" | CYW43 WPA2 minimum. | area: PLAT | -
- ASSUME | buildgen/validate.py:124-126 | "an over-long one would be dropped back to \"SensorNode\" by _with_default()" | Runtime fallback identity. | area: GEN | -
- MIRROR | buildgen/validate.py:191-193 | "toolchain/micropython_overrides.py owns the relationships ... Loaded by path" | buildgen imports toolchain code by file path. | area: GEN | covered-by: GEN.T15
- ASSUME | buildgen/validate.py:222-227 | "past it lwIP resets them, where nothing in src/ sees it" | backlog-vs-ceiling rationale; lwIP behaviour claim. | area: REST | related: REST.T06
- MIRROR | buildgen/validate.py:236, 246-247 | "the shipped defaults, pinned coherent by tests_scripts/test_buildgen_validate.py" / "poll_idle_ms's None default means \"poll_wait_ms\", mirrored here rather than read" | Default semantics hand-mirrored from `asy_uart_driver.UART`. | area: GEN | related: GEN.T06
- SETTLED | buildgen/validate.py:256-258 | "a config mismatch the owner puts out of runtime scope (Part C.7.2), so the build refuses it instead" | UART link timing/buffer floors enforced at build time only; "generated code wires no CRC or framing, so both add 0". | area: UART | -
- DRIFT | buildgen/validate.py:280-282 | "[bus.*] may be absent entirely" | Declared legal, but codegen crashes with a raw KeyError on a TOML with no `[bus]`. | area: GEN | covered-by: GEN.S03
- LIMIT | buildgen/validate.py:383-386 | "These three reach codegen's hex()/str() argument-building unvalidated otherwise" | Only three fields are type-guarded here; `irq_pull_up` is not. | area: GEN | covered-by: GEN.S02
- ASSUME | buildgen/validate.py:447-449 | "Unreachable with today's six driver names ... but latent for a future one" | Latent identity-collision gap. | area: GEN | related: GEN.T04
- INVAR | buildgen/validate.py:539-544 | "RP2040 has two UART peripherals, so a device wires at most one crossover pair" | Enforced here; `compute_twin_wiring()` relies on it. | area: GEN | -
- LIMIT | buildgen/validate.py:580-591 | "resolved by attribute name alone rather than a fixed producer_class" | `{source, field}` never checks `field` exists. | area: GEN | covered-by: GEN.S06
- LIMIT | buildgen/validate.py:645-672 | "per-signal getters (source/field pairs) - checked separately below" | `warn_*` accepted on any instance. | area: GEN | covered-by: GEN.S05
- INVAR | buildgen/validate.py:707-709 | "Both device-wiring fields are optional today, so this never fires yet; kept in sync" | Required-field enforcement path untested by real devices. | area: GEN | -
- INVAR | buildgen/validate.py:747-749 | "it is the only stage that reads toolchain/versions.toml at all" | lwIP coherence is the last validation stage. | area: GEN | -

## buildgen/definitions.py
- SETTLED | buildgen/definitions.py:20-23 | "SCHEMA_VERSION is this file's wire-format shape version ... never conflate the two (Part L.7)" | `SCHEMA_VERSION = "1.0.0"` pairs with js `SUPPORTED_SCHEMA_MAJOR`. | area: GEN | covered-by: GEN.T15
- MIRROR | buildgen/definitions.py:25-37 | "Fixed, generator-owned REST-endpoint skeleton (H.4: \"Nav grouping: Mirrors the 6 REST endpoints 1:1\")" | Section skeleton (incl. `pollIntervalMs: 3000`) hand-mirrors the REST surface. | area: WEB | related: WEB.T05
- MIRROR | buildgen/definitions.py:39-41 | "_SENSOR_DRIVERS = (\"scd30\", \"sgp40\", \"bmp3xx\", \"isl29125\")" | Hand catalog; a new sensor driver needs a row. | area: GEN | covered-by: GEN.T06
- MIRROR | buildgen/definitions.py:43-50 | "buildgen.codegen._KNOWN_SIGNALS' own parallel ... Min/max match that catalog's own field-schema literals exactly" | Two hand catalogs must agree. | area: GEN | covered-by: GEN.T06
- MIRROR | buildgen/definitions.py:52-85 | "Each mirrors its own source in asy_webserver_service.py - lightCmdLED's bounds from _dispatch_notification_led(), SystemCmd from _SYSTEM_CMDS" | Dispatch-group bounds/options hand-mirrored from `src/asy_webserver_service.py` (and codegen's `_FIELD_LED_*`). | area: WEB | related: WEB.T04
- MIRROR | buildgen/definitions.py:87-121 | "Generator-owned like the catalogs above: cosmetic labels, owned by no source file." | `_ERRCOUNT_CATALOG`, `_ERRCOUNT_NAME`, `_CFGMGR_LABEL`, `_NAME_EXT_LABEL` hand tables mirroring src `_NAME`s and CFGMGR companions. | area: GEN | covered-by: GEN.T06
- MIRROR | buildgen/definitions.py:373-375, 468-473 | "matching every hand-written definitions.json's own fixed ordering" | Generated order must match the hand-written wozi/dev definitions. | area: WEB | covered-by: WEB.S13
- LIMIT | buildgen/definitions.py:512-531 | "model = build_model(args.device_toml, args.src_dir)" | CLI path never builds `construction_order` (ordering can differ from codegen) and only catches BuildError. | area: GEN | covered-by: GEN.S08

## .github/actions/setup-micropython-toolchain/action.yml
- DRIFT | .github/actions/setup-micropython-toolchain/action.yml:4-7 | "(web-unit-tests, web-coverage, web-cross-browser-smoke, unit-tests, digital-twin-e2e, firmware-build-verify) ... all six" | Nine jobs use the action (also web-put-matrix, unit-tests-gc-threshold, unit-tests-coverage). | area: CI | covered-by: CI.S08
- LIMIT | .github/actions/setup-micropython-toolchain/action.yml:8-11 | "this action only restores the cache, it never runs setup_toolchain.py itself" | Each caller hand-copies an `-x`-only build-if-missing step (no variant/staleness probe). | area: CI | related: CI.T12
- LIMIT | .github/actions/setup-micropython-toolchain/action.yml:16-18 | "run: pip install uv" | uv itself unpinned. | area: CI | covered-by: CI.S04
- WORKAROUND | .github/actions/setup-micropython-toolchain/action.yml:19-30 | "actionlint-py fetches its binary at build time, so one bad response fails a healthy lane" | Retried `uv sync` (3 attempts, no `--locked`); removal trigger: none stated. | area: CI | related: CI.S17
- LIMIT | .github/actions/setup-micropython-toolchain/action.yml:35-38 | "Hashes setup_toolchain.py too, not just versions.toml ... a versions.toml-only key once kept a stale binary alive" | Key omits `toolchain/micropython_overrides.py` and any runner image/compiler identity. | area: CI | covered-by: CI.S01
- ASSUME | .github/actions/setup-micropython-toolchain/action.yml:36-37 | "Shared by every caller: first job builds, later ones hit." | Cache is saved only on job success. | area: CI | covered-by: CI.S09

## .github/zizmor.yml
- SETTLED | .github/zizmor.yml:1-3 | "Only unpinned-uses is configured; every other audit stays at its default, so a new release surfaces new checks to triage" | Default-on audits by policy. | area: CI | related: CI.T06
- SETTLED | .github/zizmor.yml:8-10 | "First-party actions: a tag is enough - a compromised actions/* org compromises the platform itself" | `actions/*` ref-pinned (no Dependabot). | area: CI | covered-by: CI.T06
- SETTLED | .github/zizmor.yml:11-13 | "Everything third-party (codecov/, dorny/) is SHA-pinned" | SHA bumps are manual. | area: CI | covered-by: CI.T06
- SUPPRESS | .github/zizmor.yml:14-18 | "Disabled, not fixed: it wants `uses: $/.github/...`, which actionlint 1.7.12 rejects" | `self-repository` audit disabled; removal trigger: actionlint accepts the syntax. | area: CI | related: CI.T06

## .github/workflows/ci.yml
- SETTLED | .github/workflows/ci.yml:3-9 | "`push` is the load-bearing one: a PR conflicted with its base has no merge ref ... (128 commits once" | Dual trigger by design; `branches: ['**']` excludes tag pushes. | area: CI | related: CI.T09
- RISK | .github/workflows/ci.yml:11-15 | "cancel-in-progress keeps exactly one run per push; which survives does not matter" | Combined with the per-push filter base, a cancelled run's web change may never be re-filtered. | area: CI | covered-by: CI.S11
- SETTLED | .github/workflows/ci.yml:17-19 | "Deny-by-default GITHUB_TOKEN; each job grants itself contents: read" | Enforced by zizmor. | area: CI | covered-by: CI.T06
- LIMIT | .github/workflows/ci.yml:22-57 | "Gates the web tier on whether THIS PUSH touched the website or its tooling" | Filter omits `src/**`, `buildgen/**`, `devices/**`, `digital_twin/**`, `toolchain/**` though web/live-twin tests depend on them. | area: CI | covered-by: CI.S02
- ASSUME | .github/workflows/ci.yml:38-41 | "naming the pushed branch compares against the commit before the push" | dorny/paths-filter push semantics (first push of a branch, force-push). | area: CI | covered-by: CI.T09
- RISK | .github/workflows/ci.yml:59-64, 88-93 | "needs: [web-changes, web-lint-and-typecheck]" | Web tests are success-gated on web lint (no `!cancelled()`), unlike CLAUDE.md's sequencing-not-gating rule for the Python lanes. | area: CI | related: CI.T01
- ASSUME | .github/workflows/ci.yml:124-129, 174-179, 218-223, 291-296 | "if [ ! -x \"$bin\" ]; then uv run toolchain/setup_toolchain.py setup" | Four copies of an existence-only build-if-missing step. | area: CI | covered-by: CI.T12
- SETTLED | .github/workflows/ci.yml:135-147 | "one runner per shard, so the twin's fixed port never collides" / "fail-fast: false" | PUT matrix sharding relies on one runner per shard for port isolation. | area: CI | related: TEST.T14
- SUPPRESS | .github/workflows/ci.yml:224-228 | "A report, not a gate ... continue-on-error: true" | web-coverage's test step is advisory, unlike the Python coverage job. | area: CI | covered-by: CI.S12
- SUPPRESS | .github/workflows/ci.yml:229-252 | "continue-on-error: true" | Web coverage summary and artifact upload steps advisory. | area: CI | related: CI.T11
- LIMIT | .github/workflows/ci.yml:299-305 | "cached under a fixed key - bump the suffix to force a refresh" | Firefox cache key `cross-browser-firefox-v1-<os>` never invalidates on its own. | area: CI | covered-by: CI.S06
- DRIFT | .github/workflows/ci.yml:311-314, 338-339 | "mypy names only the main pass's" / "Mypy (src/, tests/, digital_twin/, tests_hardware/device_scripts/, and the whole host build chain)" | CI narrows the main pass to `src tests tests_hardware/device_scripts` while typecheck.sh:105-107 says CI passes `src tests`. | area: CI | covered-by: CI.S03
- WORKAROUND | .github/workflows/ci.yml:325-335, 354-362, 380-388, 405-413, 437-447, 491-501 | "`actionlint-py` ships no wheel and fetches its binary inside its own build backend ... HTTP 500 on 2026-09-13, 504 on 2026-09-14" | Six hand copies of the retried `uv sync` (plus the composite action's); CLAUDE.md forbids removing the unit-tests one. | area: CI | covered-by: CI.S17
- LIMIT | .github/workflows/ci.yml:323-324, 352-353, 378-379, 403-404 | "run: pip install uv" | uv unpinned in every lint lane. | area: CI | covered-by: CI.S04
- SETTLED | .github/workflows/ci.yml:341-343 | "scripts/ only: the legacy build-*.sh are out of scope forever (CLAUDE.md)" | shellcheck scope. | area: CI | -
- SETTLED | .github/workflows/ci.yml:392-394, 415 | "--offline skips the two API audits, so it behaves the same everywhere" | Two zizmor audits never run. | area: CI | related: CI.T06
- SETTLED | .github/workflows/ci.yml:417-426 | "needs: lint-and-typecheck is sequencing only, the standing hang backstop; `if: !cancelled()` drops the success gating" | unit-tests runs even if lint fails (CLAUDE.md). | area: CI | covered-by: CI.T01
- ASSUME | .github/workflows/ci.yml:423-424, 430 | "45 minutes: a ~17-minute warm run plus one hung file's full retry budget" | Timeout sized from a measured warm run. | area: CI | related: CI.T01
- LIMIT | .github/workflows/ci.yml:451-469 | "Run unit tests at the shipped gc.threshold" | `unit-tests-gc-threshold` has no job-level retried sync of its own (relies on the composite action's). (low) | area: CI | related: CI.S17
- ASSUME | .github/workflows/ci.yml:471-475 | "45 minutes over the measured 14m01s/16m56s instrumented reruns; a 30-minute cap once cancelled a passed suite" | Timeout from dated measurements. | area: CI | -
- SETTLED | .github/workflows/ci.yml:476-480 | "Success-gated on purpose (no `if: !cancelled()`, unlike unit-tests' own edge above)" | Coverage job gated on the plain suite passing. | area: CI | covered-by: CI.T01
- SETTLED | .github/workflows/ci.yml:502-516 | "This step is NOT advisory: build-settrace is the only interpreter no other job runs. Exit 1 ... goes red; exit 3 ... stays advisory (Part E.5.3)" | Owner decision 2026-09-22. | area: CI | related: CI.T11
- SUPPRESS | .github/workflows/ci.yml:517-556 | "continue-on-error: true" | Six report/upload steps (`always()`) advisory. | area: CI | related: CI.T11
- LIMIT | .github/workflows/ci.yml:525-534, 535-542 | "needs a CODECOV_TOKEN repo secret ... once this repo is registered at codecov.io ... fail_ci_if_error keeps a missing/invalid token from ever failing the job" | Codecov uploads currently no-op (CLAUDE.md). | area: CI | related: CI.T11
- SETTLED | .github/workflows/ci.yml:559-569 | "needs: unit-tests, success-gated on purpose: fail-fast is the intent" | digital-twin-e2e is the deliberate gated exception (CLAUDE.md). | area: CI | covered-by: CI.T01
- LIMIT | .github/workflows/ci.yml:577, 610 | "device: [wozi, dev, arzi, klkizi, grkizi, schlafzi]" | Hand-kept 6-device matrices (twice). | area: CI | covered-by: CI.T07
- SUPPRESS | .github/workflows/ci.yml:586-593 | "if-no-files-found: ignore ... continue-on-error: true" | Twin log upload advisory. | area: CI | related: CI.T15
- SETTLED | .github/workflows/ci.yml:595-602 | "needs: unit-tests for the toolchain cache only, so `if: !cancelled()`" | Firmware build runs even when unit-tests fails. | area: CI | covered-by: CI.T01
- ASSUME | .github/workflows/ci.yml:617-618 | "A cache miss fails on build_firmware.py's own \"no toolchain found\" rather than skipping the build." | Cold-cache failure mode documented as intended. | area: CI | covered-by: CI.S09
- PLATFORM | .github/workflows/ci.yml:620-632 | "python3 - <<'PYEOF' ... st.ensure_apt_packages(" | Runs the installer module under the runner's bare `python3` (needs >= 3.11 for tomllib); ARM GCC is the distro's (`ubuntu-latest` floats). | area: CI | covered-by: SCR.T09
- ASSUME | .github/workflows/ci.yml:595-634 | "Builds a real firmware.uf2 per device (B.11)" | The job installs apt packages only; picotool (installed to `/usr/local` by `setup`) is not in the cached `~/pico-toolchain`. (low) | area: CI | related: CI.T03

## devices/dev.toml
- SETTLED | devices/dev.toml:1-2 | "the bench rig, the only unit ever flashed; always built from this file, never from wozi's pins (CLAUDE.md's WoZi rule)" | dev-bench quirks are out of scope as bugs (CLAUDE.md). | area: GEN | -
- RISK | devices/dev.toml:7 | "hotspot_password = \"12345678\"" | Shared hardcoded hotspot password, identical in all six TOMLs (accepted risk; not to be changed without the owner). | area: SEC | related: GEN.T08
- MIRROR | devices/dev.toml:11-14 | "kept below the firmware's own lwIP MEMP_NUM_TCP_PCB (toolchain/versions.toml) with margin ... backlog is omitted, so it derives max_connections + 1" | `max_connections = 6` must stay coherent with `[lwip]`; enforced by validate.py's lwIP check. Same comment in all six TOMLs. | area: GEN | covered-by: GEN.T15
- PLATFORM | devices/dev.toml:26-31 | "SCD30 clock-stretch headroom (datasheet: up to 150ms/day, past rp2's 50ms default)." | `timeout = 200000` on the SCD30 bus rests on a datasheet figure and the rp2 default I2C timeout. | area: BUS | related: GEN.T08
- ASSUME | devices/dev.toml:38-40 | "Buffers and poll rates are sized from the real 53-byte frame and this bench's poll rate, not the driver defaults (J.6)." | UART rxbuf/txbuf/poll values bench-tuned; the crossover jumper (GP0<->GP9, GP1<->GP8) is physical. | area: UART | -
- INVAR | devices/dev.toml:96-98 | "Last among the sensor drivers for FRAM chunk order (Part A.7); wozi has no such instance, so no byte-identity constraint applies." | TOML declaration order determines FRAM chunk layout; the "byte-identity constraint" referred to is not defined here. | area: STOR | related: XCUT.T09
- SETTLED | devices/dev.toml:100-101 | "irq_pull_up = false: the board carries its own external pull-up on GPIO6" | Bench-board hardware fact. | area: SENS | -
- PLATFORM | devices/dev.toml:118-119 | "# MB85RS2MTA, 256KB." | dev FRAM part and size (`max_size = 0x40000`). | area: STOR | related: XCUT.T09
- SETTLED | devices/dev.toml:150-154 | "wozi never gets a UART instance: it is never flashed, so the peripheral would be untestable (CLAUDE.md)" | Per-end FRAM chunk for each uart_link (WP3). | area: UART | -

## devices/wozi.toml
- SETTLED | devices/wozi.toml:1-2 | "the exemplary/base device; never physically flashed, its correctness comes from tests/" | CLAUDE.md WoZi rule. | area: GEN | -
- RISK | devices/wozi.toml:7 | "hotspot_password = \"12345678\"" | Shared hotspot password. | area: SEC | related: GEN.T08
- PLATFORM | devices/wozi.toml:21-26 | "SCD30 clock-stretch headroom (datasheet: up to 150ms/day, past rp2's 50ms default)." | Same datasheet-derived timeout. | area: BUS | related: GEN.T08
- PLATFORM | devices/wozi.toml:81-82 | "# MB85RS64V, 8KB." | wozi FRAM part/size. | area: STOR | related: XCUT.T09
- ASSUME | devices/wozi.toml:1-3 | "The source of truth buildgen reads" | Unlike the four field TOMLs, no legacy wiring source is cited for wozi's pins. (low) | area: PAR | related: PAR.T02

## devices/arzi.toml
- MIRROR | devices/arzi.toml:1-2 | "distinct wiring from the \"neu\" family ... Wiring sourced from modules/sensortask-arzi.py (legacy, read-only reference)." | Pin parity with the legacy module. | area: PAR | covered-by: PAR.T02
- RISK | devices/arzi.toml:7 | "hotspot_password = \"12345678\"" | Shared hotspot password. | area: SEC | related: GEN.T08
- ASSUME | devices/arzi.toml:70-72 | "max_size = 0x2000" | FRAM size stated without a part number (8 KB assumed). (low) | area: STOR | related: XCUT.T09

## devices/klkizi.toml
- ASSUME | devices/klkizi.toml:1-3 | "one of three \"ArZi neu\" units (own file for expected future hardware divergence from grkizi/schlafzi) ... Wiring sourced from modules/sensortask-neu.py" | Three byte-identical-except-name files anticipate divergence; pins mirror legacy `sensortask-neu.py`. | area: PAR | covered-by: PAR.T13
- RISK | devices/klkizi.toml:8 | "hotspot_password = \"12345678\"" | Shared hotspot password. | area: SEC | related: GEN.T08
- ASSUME | devices/klkizi.toml:70-73 | "max_size = 0x2000" | FRAM size without part number. (low) | area: STOR | related: XCUT.T09

## devices/grkizi.toml
- ASSUME | devices/grkizi.toml:1-3 | "one of three \"ArZi neu\" units (own file for expected future hardware divergence from klkizi/schlafzi)" | Identical to klkizi except name/hostname. | area: PAR | covered-by: PAR.T13
- RISK | devices/grkizi.toml:8 | "hotspot_password = \"12345678\"" | Shared hotspot password. | area: SEC | related: GEN.T08

## devices/schlafzi.toml
- ASSUME | devices/schlafzi.toml:1-3 | "one of three \"ArZi neu\" units (own file for expected future hardware divergence from klkizi/grkizi)" | Identical to klkizi except name/hostname. | area: PAR | covered-by: PAR.T13
- RISK | devices/schlafzi.toml:8 | "hotspot_password = \"12345678\"" | Shared hotspot password. | area: SEC | related: GEN.T08

## pyproject.toml
- PLATFORM | pyproject.toml:8-11 | ">=3.11: scripts/typecheck.sh needs tomllib. At 3.10, `uv sync` once built a venv without it" | Host Python floor; the chroot recipe exists partly because of this. | area: CI | related: SCR.T09
- DRIFT | pyproject.toml:18-24 | "PINNED, like every tool here ... \"pytest\", \"mpremote\"," | `pytest` and `mpremote` are unpinned despite the comment; hardware harness depends on mpremote behaviour and the skip gate on pytest output format. | area: CI | covered-by: CI.S05
- SETTLED | pyproject.toml:18-20 | "select = [\"ALL\"] and a zero-findings gate turn an unpinned upgrade's new rule into a hard CI failure ... Bump deliberately" | Update obligation for mypy 2.3.1 / ruff 0.16.6: bump deliberately and re-run lint.sh + typecheck.sh; after any `uv.lock` merge, verify installed versions (CLAUDE.md). | area: CI | covered-by: CI.T04
- ASSUME | pyproject.toml:25-27 | "\"types-pyserial==3.5.0.20260712\"" | Stub pin; update obligation same as tools. | area: CI | covered-by: CI.T04
- LIMIT | pyproject.toml:28-32 | "actionlint-py downloads its binary at install time, so a fully offline sync lacks it" | Offline `uv sync` cannot provide actionlint; root cause of the retried syncs. | area: CI | covered-by: CI.T04
- ASSUME | pyproject.toml:33-35 | "\"zizmor==1.30.1\"" | Pinned; a bump may surface new default-on audits (zizmor.yml policy). | area: CI | related: CI.T06
- SETTLED | pyproject.toml:38-40 | "The RPI_PICO_W MicroPython stubs are deliberately NOT a dependency group" | Load-bearing isolation (CLAUDE.md). | area: CI | -
- SETTLED | pyproject.toml:42-44 | "the legacy tree (python/, modules/) is never in scope" | Scope rule; device_scripts joined after a signature-change incident. | area: CI | -
- PLATFORM | pyproject.toml:46-49, 357-358 | "target-version = \"py310\"" / "python_version = \"3.10\"" | Checked-code syntax floor set to 3.10 as a proxy for MicroPython. | area: PLAT | -
- SETTLED | pyproject.toml:50-52 | "ruff format is never used - line breaks are hand-chosen (CLAUDE.md); 320 is ruff's own ceiling" | line-length 320 + E501 ignore. | area: CI | -
- SUPPRESS | pyproject.toml:58-60 | "allowed-confusables = [\"×\"]" | RUF003 allowance for bmp3xx oversampling labels. | area: CI | -
- SUPPRESS | pyproject.toml:63-64 | "\"E501\",  # line length - not enforced" | Ignore: hand-chosen line breaks. | area: CI | -
- SUPPRESS | pyproject.toml:66-69 | "only the docstring-PRESENCE rules are off" | Ignore D100-D107 (one header block per module). | area: CI | -
- SUPPRESS | pyproject.toml:71-78 | "No `pathlib` in the rp2 port at all" / "No async file I/O either ... every real flash write is reachable only through the REST PUT path" | Ignore PTH, ASYNC230 (target impossibility; blocking flash writes accepted, Part F.3). | area: CI | -
- SUPPRESS | pyproject.toml:80-85 | "tests/ runs under the real MicroPython interpreter with microtest.py, not pytest" / "`print()` is the log transport" | Ignore PT, T20. | area: CI | -
- SUPPRESS | pyproject.toml:87-93 | "an Event would change the protocol" / "`global` is how tests/ keeps its per-process port and scratch counters" | Ignore ASYNC110 (neopixel yield handshake), PLW0603. | area: CI | -
- SUPPRESS | pyproject.toml:95-98 | "Part G.2 REQUIRES `except Exception` -> err_s() -> \"Failed\" around a caller-supplied callback" | Ignore BLE001 globally, including src/. | area: CI | -
- SUPPRESS | pyproject.toml:100-106 | "Cost without a defect caught, on a 264KB-SRAM target" | Ignore TRY003, EM101, EM102, SIM105 (contextlib not frozen). | area: CI | -
- SUPPRESS | pyproject.toml:108-114 | "PERF203: ... hoisting aborts the loop" / "S110 wants a log call at sites that are deliberately silent" | Ignore PERF203, S110 (silent `try/except/pass` allowed globally). | area: CI | -
- SUPPRESS | pyproject.toml:116-129 | "MicroPython has no PEP 448 unpacking in displays ... (verified)" / "deque takes no keyword arguments (TypeError, verified)" | Ignore RUF005, RUF037, RUF012, PYI024; platform facts verified on the pinned interpreter. | area: PLAT | related: PLAT.T02
- SUPPRESS | pyproject.toml:131-137 | "`int | float` is load-bearing" / "typing.Self is gated behind 3.11" | Ignore PYI041, PYI034. | area: CI | -
- SUPPRESS | pyproject.toml:139-148 | "TRY301: an inner raise function is a closure allocation" / "SIM115: `with open(...)` would newly swallow an OSError" / "PLW1641 would make RunConfig hashable" | Ignore TRY301, SIM115, PLW1641. | area: CI | -
- SUPPRESS | pyproject.toml:150-153 | "FURB122's `f.writelines()` does not exist on MicroPython file objects (AttributeError, verified on the pinned interpreter)." | Ignore FURB122; platform fact. | area: PLAT | related: PLAT.T02
- SUPPRESS | pyproject.toml:155-158 | "FBT003's remaining calls are into C entry points that reject keywords" | Ignore FBT003; FBT001/002 stay on. | area: CI | -
- SUPPRESS | pyproject.toml:160-163 | "`x != x` is asy_scd30_driver.py's NaN test in its two setters" | Ignore PLR0124. | area: CI | -
- SUPPRESS | pyproject.toml:165-167 | "Documented accepted risk, decided by the project owner ... The webserver binds 0.0.0.0 deliberately." | Ignore S104 globally. | area: SEC | -
- DRIFT | pyproject.toml:168-169, 233-235 | "The three known, accepted sites are exempted per file below." | S105/S106 are exempted in eight files (src/asy_wifi_service.py, digital_twin/launch.py, tests/test_digital_twin_network_neopixel.py, four tests_hardware files, tests_scripts/test_buildgen_validate.py); CLAUDE.md names two real credential sites; all six device TOMLs also carry the password. | area: SEC | covered-by: CI.S08
- SUPPRESS | pyproject.toml:171-179 | "Identifiers deliberately mirror the datasheet / reference algorithm" | Ignore N801, N802, N803, N806, N811, N814. | area: CI | -
- SUPPRESS | pyproject.toml:181-184 | "D205/D209 each ADD a line to a header already at the cap" | Ignore D205, D209 (3-line cap). | area: CI | -
- SUPPRESS | pyproject.toml:186-194 | "src/ and ext/ are frozen flat into one directory" / "no file carries a copyright notice by design" | Ignore INP001, CPY001 (attribution in THIRD_PARTY_LICENSES.md). | area: LIC | -
- INVAR | pyproject.toml:202-212 | "Ceilings sit at the measured maximum, so they gate regression without forcing a rewrite; ratchet DOWN only." | max-complexity 20, max-args 24, max-branches 20, max-statements 80, max-returns 12; ratchet-down by convention. | area: CI | -
- DRIFT | pyproject.toml:214-215 | "Per-file exemptions live HERE, centrally and with a reason, never as scattered `# noqa`" | Line-level `# noqa` exist in scripts/ (E402 x8, PLC0415), toolchain/ (PLR2004) and generated code (F401). (low) | area: CI | -
- SUPPRESS | pyproject.toml:217-229 | "Test code asserts, reaches into privates under test, imports lazily after sys.path setup" | tests/**, tests_scripts/** (+S603), tests_hardware/**: S101, SLF001, PLC0415, PLR2004, ARG001/002/004/005; digital_twin/**: S101, SLF001, PLC0415, PLR2004. | area: TEST | related: TEST.T11
- SUPPRESS | pyproject.toml:230-232 | "api_response.py calls a reader's `_set_dict_cfg` across objects by design" | src/api_response.py: SLF001. | area: CORE | -
- SUPPRESS | pyproject.toml:237-243 | "The machine fakes mirror MicroPython's own constructors" | tests/machine.py and digital_twin/machine.py: A002, FBT001, FBT002, ANN401. | area: TEST | related: TEST.T05
- SUPPRESS | pyproject.toml:244-247 | "fake_run() doubles must accept setup_toolchain.run()'s signature exactly" | tests_scripts/test_setup_toolchain_env.py: FBT001, FBT002. | area: TEST | -
- SUPPRESS | pyproject.toml:248-252 | "The `_push_*` dispatch family takes the config-VALUE union, where bool is a JSON value" | src/asy_bmp3xx_driver.py, src/asy_scd30_driver.py: FBT001; src/asy_wifi_service.py: S106 (accepted hotspot password), FBT001. | area: SENS | -
- SUPPRESS | pyproject.toml:253-263 | "ANN401, category 1 - heterogeneous **kwargs ... PEP 692's Unpack[TypedDict] is the real fix and unavailable" | src/print_log.py and four tests files: ANN401; removal trigger: stubs declare TypedDict properly. | area: CORE | related: PLAT.T05
- SUPPRESS | pyproject.toml:264-276 | "ANN401, category 2 - the asyncio.start_server() callback seam" / "category 3 - `_wlan` bridges the real WLAN board stub" / "category 4 - ... deliberately passes a TYPE-INVALID value" | ANN401 on test_asy_wifi_service.py, two integration tests, test_asy_udp_socket.py; category 3 is a three-file family to change together. | area: TEST | -
- SUPPRESS | pyproject.toml:277-290 | "ANN401, category 5 - driver-agnostic fan-in seams" / "ARG002: _DefaultSignalSink.request_signal() is a no-op sink" | src/asy_notification_service.py: ANN401, ARG002; src/asy_sgp40_driver.py: ANN401, FBT001; five tests files: ANN401. | area: LED | -
- SUPPRESS | pyproject.toml:291-303 | "ANN401, category 6 - a dynamically __import__()ed module ... has no static type" | digital_twin/run_generic_integration.py, tests_scripts/test_buildgen_twin_wiring.py, three tests scenario libraries: ANN401. | area: TWIN | -
- SUPPRESS | pyproject.toml:304-305 | "\"digital_twin/launch.py\" = [\"S105\"]" | Credential-rule exemptions with no stated reason on these two lines (covered by the "copies of an accepted risk" framing below). (low) | area: SEC | covered-by: CI.S08
- SUPPRESS | pyproject.toml:306-310 | "asserts its static mount is non-None purely to narrow the type for mypy" | src/asy_webserver_service.py: SLF001, S101, ANN401 (an `assert` in shipped code); digital_twin/_http_client.py: ANN401. | area: REST | -
- SUPPRESS | pyproject.toml:311-323 | "S603 (untrusted subprocess input) has no satisfiable form for a build driver" | scripts/build_firmware.py, scripts/_digital_twin_ci_suite.py, toolchain/setup_toolchain.py, toolchain/micropython_overrides.py: S603. | area: SCR | related: TOOL.T01
- SUPPRESS | pyproject.toml:324-330 | "S603/S607: shelling out to mpremote/picotool/nmcli/iw/iptables/tc IS this tier's job ... tools resolve from PATH" | Four tests_hardware files: S603, S607. | area: HW | -
- SUPPRESS | pyproject.toml:331-337 | "S310: a fixed `http://` URL this module builds itself" / "S112: injected packet loss makes individual request failures the fault itself" | tests_hardware/http_client.py: S310; test_bus_concurrency_under_api_load.py: S112. | area: HW | -
- SUPPRESS | pyproject.toml:338-347 | "copies of an accepted risk, exempted per file" | S105/S106 on four tests_hardware files and tests_scripts/test_buildgen_validate.py. | area: SEC | covered-by: CI.S08
- SUPPRESS | pyproject.toml:348-351 | "`itertools` does not exist in the rp2 port at all" | tests_hardware/device_scripts/**: RUF007; platform fact. | area: PLAT | -
- LIMIT | pyproject.toml:359-365 | "follow_imports = \"silent\"" / "build/generated_src for device_scripts' one static `import sensortask_dev`" | Errors inside generated modules and the stub package are never reported. | area: GEN | covered-by: GEN.S17
- SUPPRESS | pyproject.toml:360-362 | "Extends `silent` to the (upstream-Beta) stub package itself: its types are used, its own issues not reported." | Stub-package errors hidden. | area: CI | related: PLAT.T05
- SUPPRESS | pyproject.toml:373-391 | "Excluded, each for a reason B.15 states" | Main mypy pass excludes tests/network.py, five digital_twin files, tests/test_digital_twin_*.py and two scenario libraries (checked by digital_twin/typecheck.ini instead). | area: SCR | covered-by: SCR.T15
- SUPPRESS | pyproject.toml:403-406 | "no_implicit_reexport stays off here only ... which would need 175 inline ignores" | The one strict-flag exemption in the main pass; count dated. | area: CI | related: SCR.T15
- SUPPRESS | pyproject.toml:408-413 | "Vendored, unannotated microdot's @app.get()/@app.put() make every handler \"untyped\" ... Revisit if Microdot ships hints." | `disallow_untyped_decorators = false` for test_setter_microdot_integration; removal trigger: Microdot ships type hints. | area: TEST | -
- LIMIT | pyproject.toml:415-418 | "testpaths = [\"tests_scripts\"]" | No `--strict-markers`/`xfail_strict`; a misspelled wear-gate marker would be a silent no-op. | area: CI | covered-by: CI.S13

## host_typecheck.ini
- PLATFORM | host_typecheck.ini:1-8 | "ordinary CPython 3.11 programs that need mypy's real typeshed" | `python_version = 3.11` for all host tooling. | area: SCR | related: SCR.T09
- SUPPRESS | host_typecheck.ini:11-17 | "device_scripts/ is MicroPython code run on the board (121 errors here, 99 artifacts)" / "tests_scripts/conftest.py ... an accepted gap (B.15)" | Two exclusions; conftest.py is never type-checked (accepted). | area: SCR | covered-by: SCR.T15
- MIRROR | host_typecheck.ini:19-25 | "The other entries mirror the sys.path pytest builds at runtime (harness, dns_probe, runner, _toml_fixtures, micropython_overrides), without which the harness API types as Any" | `mypy_path` hand-mirrors pytest's runtime sys.path; drift silently degrades to `Any`. | area: SCR | covered-by: SCR.T15
- SETTLED | host_typecheck.ini:31-36 | "Full --strict, no exemptions ... no_implicit_reexport is enforced here too" | Strictness of the host pass. | area: SCR | related: SCR.T15

## .gitignore
- DRIFT | .gitignore:5-6 | "same \"dev-tooling only\" split as .venv/ above" | `.venv/` is at line 59, below. | area: CI | covered-by: CI.S19
- INVAR | .gitignore:1-3, 84-89 | "never commit a real one" / "config_WIFI.cfg carries SSID/PW on a tree that has real ones - ignored so a `git add -A` after a validation run cannot commit one" | Only future commits are guarded; device scripts run host-side spill credential-bearing `config_*.cfg` into the repo root. | area: SEC | covered-by: SCR.S09
- DRIFT | .gitignore:22-25 | "Build output (see build-*.sh)" | Legacy-tree reference for `*.uf2`, which `scripts/build_firmware.py` now also writes under `build/`. (low) | area: CI | -
- DRIFT | .gitignore:27-31 | "the natural home for any future build/<device>/{py,html,frozen,firmware} staging tree" | Same unrealised `build/<device>/` layout as generate.py:3 and SPECIFICATION.md L.2. (low) | area: DOC | -
- DRIFT | .gitignore:33-41 | "confirmed directly against the pinned v1.28.0 source" / "scripts/test.sh's own \"src:tests:.frozen\" MICROPYPATH" | Pin is v1.29.0 and test.sh's MICROPYPATH is `build/generated_src:src:tests:frozen_modules:.frozen`. | area: CI | covered-by: CI.S19
- PLATFORM | .gitignore:35-38 | "py/builtinimport.c's MP_FROZEN_PATH_PREFIX \".frozen/\" ... routes straight to the compiled-in frozen-module table" | Import-sentinel fact that forces `frozen_modules/`; re-check on pin moves. | area: PLAT | -
- DRIFT | .gitignore:27, 33, 75, 84 | "# digital_twin/run_wozi_integration.py's own persistent run state -" | Comment blocks over the 3-line cap; `:75` names the retired `run_wozi_integration.py`. | area: CI | covered-by: CI.S10
- RISK | .gitignore:9-14 | "Vitest 5 moved these ... both are listed so a checkout still ignores whatever an older local install leaves behind" | Two attachment paths kept for version drift. (low) | area: CI | -

## Coverage
| file | comment/doc lines read | items |
|---|---|---|
| scripts/_digital_twin_ci_suite.py | 351 | 43 |
| scripts/_generate_sensortask_modules.py | 24 | 6 |
| scripts/_render_coverage.py | 11 | 5 |
| scripts/_require_clean_hardware_run.sh | 18 | 11 |
| scripts/_strip_type_checking.py | 13 | 5 |
| scripts/build_firmware.py | 44 | 12 |
| scripts/build_frozen_html.sh | 13 | 7 |
| scripts/build_website.sh | 20 | 8 |
| scripts/cross_browser_smoke.mjs | 108 | 15 |
| scripts/lint.sh | 22 | 8 |
| scripts/mpremote_connect.sh | 3 | 2 |
| scripts/run_bench_hardware_suite.sh | 6 | 2 |
| scripts/run_bench_soak_tests.sh | 9 | 4 |
| scripts/run_digital_twin_ci.sh | 25 | 6 |
| scripts/run_flash_hardware_suite.sh | 6 | 1 |
| scripts/run_manual_hardware_tests.sh | 3 | 1 |
| scripts/run_unix_port_integration.sh | 29 | 7 |
| scripts/setup_cross_browser_toolchain.sh | 14 | 6 |
| scripts/test.sh | 200 | 42 |
| scripts/typecheck.sh | 33 | 10 |
| toolchain/micropython_overrides.py | 101 | 24 |
| toolchain/setup_toolchain.py | 206 | 43 |
| toolchain/versions.toml | 22 | 9 |
| buildgen/__init__.py | 3 | 1 |
| buildgen/buildspec.py | 26 | 5 |
| buildgen/codegen.py | 75 | 26 |
| buildgen/defaults.py | 8 | 2 |
| buildgen/definitions.py | 53 | 8 |
| buildgen/driver_registry.py | 23 | 4 |
| buildgen/errors.py | 3 | 1 |
| buildgen/frozen_modules.py | 8 | 5 |
| buildgen/generate.py | 3 | 3 |
| buildgen/graph.py | 16 | 4 |
| buildgen/limits.py | 9 | 1 |
| buildgen/model.py | 25 | 3 |
| buildgen/pico_gpio.py | 18 | 4 |
| buildgen/requires_tag.py | 9 | 2 |
| buildgen/schema_ast.py | 11 | 2 |
| buildgen/tag_comments.py | 80 | 6 |
| buildgen/twin_wiring.py | 17 | 4 |
| buildgen/validate.py | 143 | 22 |
| buildgen/value_wiring.py | 3 | 1 |
| buildgen/version.py | 6 | 3 |
| buildgen/web_tag.py | 17 | 4 |
| buildgen/wiring.py | 11 | 1 |
| .github/actions/setup-micropython-toolchain/action.yml | 6 | 6 |
| .github/workflows/ci.yml | 116 | 31 |
| .github/zizmor.yml | 10 | 4 |
| devices/arzi.toml | 11 | 3 |
| devices/dev.toml | 28 | 9 |
| devices/grkizi.toml | 12 | 2 |
| devices/klkizi.toml | 12 | 3 |
| devices/schlafzi.toml | 12 | 2 |
| devices/wozi.toml | 12 | 5 |
| pyproject.toml | 238 | 54 |
| host_typecheck.ini | 19 | 4 |
| .gitignore | 45 | 8 |

(Shell/TOML/YAML/INI files were also read in full, not only via the dump; `c_*.txt` dumps plus full reads for the large Python files' code context.)

## Totals per kind
| kind | count |
|---|---|
| LIMIT | 87 |
| SETTLED | 72 |
| ASSUME | 67 |
| SUPPRESS | 67 |
| INVAR | 49 |
| MIRROR | 49 |
| PLATFORM | 46 |
| RISK | 41 |
| DRIFT | 32 |
| WORKAROUND | 8 |
| TODO | 2 |
| OPENQ | 0 |
| **total** | **520** |

## Top 10
1. scripts/_digital_twin_ci_suite.py:127-133 — the soak's mem sampler runs `gc.collect()` in the DUT every 25 ms, so Run 11 measures a heap collected far more often than either GC stage it claims to test (MEM; related TEST.T03, new).
2. scripts/run_digital_twin_ci.sh:10-11 + _digital_twin_ci_suite.py:6 — both claim the shell script "owns clean" and is "deliberately redundant"; no shell-level clean exists (new DRIFT).
3. toolchain/setup_toolchain.py:33-36/335/379 — `-Wno-array-bounds` applied to every translation unit of firmware and both Unix ports, not just mbedtls, while every other warning fails the build.
4. scripts/test.sh:363-364 + :378-380 — a MemoryError printed in a timed-out attempt is discarded if a retry passes; intermittent hangs pass if any of 3 attempts completes.
5. .github/workflows/ci.yml:59-64/88-93 — web tests are success-gated on web lint, contrary to CLAUDE.md's sequencing-not-gating rule for the Python lanes.
6. buildgen/codegen.py:301/303/604-616 — `type: ignore`/`noqa` emitted into shipped generated modules that no lint/type pass reports (with GEN.S17).
7. scripts/cross_browser_smoke.mjs:476-501 — missing WebKit/Firefox/Edge is a warning only; the run passes as long as Chromium ran.
8. devices/dev.toml:96-98 — TOML declaration order fixes the FRAM chunk layout; the "byte-identity constraint" it cites is undefined (XCUT.T09).
9. pyproject.toml:18-24 / 168-169 / 214-215 — "PINNED like every tool" (pytest/mpremote unpinned), "three known credential sites" (eight exempted files plus six TOMLs), "never scattered # noqa" (several exist).
10. toolchain/micropython_overrides.py:37-57/105-127/166 — the anchor set (unix_kbd_intr line; lwipopts_common defaults; rp2 CMake include order; lwipopts include; board cmake line; board-dir shape) that must be re-verified on every pin move; unix_kbd_intr has no post-build proof (TOOL.S07).
