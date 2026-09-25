# Harvest — SCR: Scripts and test orchestration

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 24, INVAR 41, MIRROR 12, LIMIT 48, RISK 8, ASSUME 25, PLATFORM 7, WORKAROUND 9, SUPPRESS 24, TODO 9, DRIFT 10, NOTE 3 — 220 items.


## ext/freezefs/archive.py

- **SCR.N001** DRIFT · `ext/freezefs/archive.py:235-239` — "parser.add_argument(\"--silent\", \"-s\"," —
  `scripts/build_frozen_html.sh:10-11` says freezefs's current CLI dropped the "-s" flag; the vendored
  CLI still has `-s` (low) · [H02]

## tests/_coverage_runner.py

- **SCR.N002** SETTLED · `tests/_coverage_runner.py:5-7` — "It runs under build-settrace, its OWN
  binary: the flag is not inert when unused" — two-binary decision (owner 2026-09-21, Part E.5.2) ·
  related: TEST.T09 · [H03]

## tests/neopixel.py

- **SCR.N003** INVAR · `tests/neopixel.py:2` — "Resolved ahead of any real module because tests/
  precedes .frozen on MICROPYPATH" — fake resolution depends on MICROPYPATH order in `scripts/test.sh` ·
  [H03]

## digital_twin/README.md

- **SCR.N004** LIMIT · `digital_twin/README.md:193-195` — "`scripts/run_unix_port_integration.sh` is not
  part of `scripts/test.sh`'s own default `tests/test_*.py` glob loop" — Manual entry point is untested
  by the default loop · related: SCR.T04 · [H06]
- **SCR.N005** LIMIT · `digital_twin/README.md:408-411` — "on a fixed port (`18080`, distinct from the
  manual entry point's `8080` default" — Fixed ports; concurrent suites collide · covered-by: SCR.T04 ·
  [H06]
- **SCR.N006** WORKAROUND · `digital_twin/README.md:519-527` — "`scripts/run_digital_twin_ci.sh` grants
  the built interpreter binary `CAP_NET_BIND_SERVICE` (via `setcap`, fresh on every invocation" —
  Privileged port 53 on a non-root host; removal trigger: none stated · covered-by: SCR.T07 · [H06]

## digital_twin/typecheck.ini

- **SCR.N007** MIRROR · `digital_twin/typecheck.ini:23-24` — "Same strictness as the root [tool.mypy],
  synced by hand (INI has no include)" — Hand-synced config · covered-by: SCR.T15 · [H06]
- **SCR.N008** ASSUME · `digital_twin/typecheck.ini:5-6` — "Confirmed empirically: excluding
  digital_twin from the main pass alone did not fix its attribute resolution" — Single empirical claim ·
  [H06]
- **SCR.N009** ASSUME · `digital_twin/typecheck.ini:8-10` — "digital_twin first so the twin's modules
  win ... No name collides (B.15)" — `mypy_path` also carries `tests` (for `_strict_json`), relying on
  path order to keep `tests/machine.py` shadowed · related: SCR.T15 · [H06]
- **SCR.N010** INVAR · `digital_twin/typecheck.ini:9` — "typecheck.sh generates it first" — Pass depends
  on `build/generated_src/` existing · [H06]

## tests_hardware/README.md

- **SCR.N011** SUPPRESS · `tests_hardware/README.md:127-148` — "fails on any skip beyond three
  deliberate classes" — `_require_clean_hardware_run.sh` whitelists KNOWN_PERMANENT_SKIPS, per-flag
  opt-in skips, and cannot see collection-time deselection at all. · covered-by: HW.T13 · [H08]

## scripts/test.sh

- **SCR.N012** INVAR · `scripts/test.sh:25-27` — "a rejected invocation must leave the live tree exactly
  as it found it" — Argument/GC_THRESHOLD validation must stay ahead of the `rm -rf tests/_tmp`/`rm -f devices/zz_test_*.toml`
  sweeps because tests_scripts runs a nested test.sh concurrently with the live suite. · related:
  SCR.T14 · [H09]
- **SCR.N013** DRIFT · `scripts/test.sh:27` — "concurrently with 85 files holding tests/_tmp scratch" —
  Stale count: 87 `tests/test_*.py` exist at 2a88cc8 (CLAUDE.md:350 says 86/86). (low) · [H09]
- **SCR.N014** MIRROR · `scripts/test.sh:47, 54` — "32768 is what the firmware ships, -1 the reactive
  default" — The GC_THRESHOLD value tested in stage (f) is a hand copy of the generated boot entry's
  `gc.threshold(32768)`; nothing ties the two. · related: SCR.S10 · [H09]
- **SCR.N015** LIMIT · `scripts/test.sh:57-61` — "--coverage uses its own runner, so
  GC_THRESHOLD=$GC_THRESHOLD is ignored for this run" — A coverage run never exercises the (f) threshold
  stage; the settrace binary only ever runs at the reactive default. · related: SCR.T01 · [H09]
- **SCR.N016** RISK · `scripts/test.sh:64-72` — "rm -rf tests/_tmp" / "rm -f devices/zz_test_*.toml" —
  Every test.sh run mutates the live tree (scratch sweep and reserved `zz_test_` device-TOML namespace
  deletion); correctness depends on Part E.1's reserved-namespace convention. · covered-by: SCR.T14 ·
  [H09]
- **SCR.N017** INVAR · `scripts/test.sh:92-102` — "Asks the binary which variant it is instead of
  trusting its path ... Always exits 0" — Variant detection relies on `hasattr(sys,"settrace")` plus a
  frozen `asyncio` import; the probe exists only in test.sh (not the twin/web runners). · covered-by:
  SCR.S05 · [H09]
- **SCR.N018** RISK · `scripts/test.sh:104-113` — "MicroPython Unix port not found at $micropython_bin -
  building it now" — test.sh auto-runs a full `setup_toolchain.py setup` (sudo apt, picotool `sudo make install`)
  when the binary is missing or the wrong variant. · covered-by: TOOL.S08 · [H09]
- **SCR.N019** ASSUME · `scripts/test.sh:133-143` — "(391ms against 131-141ms idle)" / "wall clock
  dropped 8m27s -> 3m45s" — Parallelism design rests on single dated measurements (probe timings,
  user-CPU flat across 4/8/16). · related: SCR.T01 · [H09]
- **SCR.N020** INVAR · `scripts/test.sh:137-139` — "THIS BLOCK'S PLACEMENT IS LOAD-BEARING: it must stay
  ahead of the tests_scripts/ background launch" — Probe must run before the backgrounded pytest tier;
  enforced by `tests_scripts/test_test_sh.py`. · related: SCR.T01 · [H09]
- **SCR.N021** ASSUME · `scripts/test.sh:145-147` — "the whole run writes ~46MB and spends ~8.7s of
  system time today" — Single dated host-wear measurement tied to CLAUDE.md's no-avoidable-wear rule;
  "sleep-bound" claim must be kept true. · [H09]
- **SCR.N022** LIMIT · `scripts/test.sh:151-152` — "cgroup v2; v1 and \"max\" both fall through to the
  nproc value unchanged" — Container CPU quota is honoured only under cgroup v2. · related: SCR.T01 ·
  [H09]
- **SCR.N023** RISK · `scripts/test.sh:160-161, 178-180` — "Speed probe. Never allowed to fail the run:
  any error, and we fall through to the fast-host multiplier" — A broken probe deliberately picks the
  most oversubscribed (4x) setting, which is the setting known to starve slow hosts. · related: SCR.T01
  · [H09]
- **SCR.N024** ASSUME · `scripts/test.sh:181-186` — "multiplier=4 # fast host (measured: 131-141ms on
  this project's own x86 sandbox)" — 250/900 ms band thresholds derived from one x86 sandbox and "the
  bench Pi4's class". · [H09]
- **SCR.N025** INVAR · `scripts/test.sh:197-203` — "0 or negative ... spins `wait -n` forever without
  dispatching anything" — `max_parallel` clamp >= 1 is the only guard against a hang from a bad
  TEST_PARALLELISM. · related: SCR.T14 · [H09]
- **SCR.N026** INVAR · `scripts/test.sh:205-210, 229-231` — "MUST stay behind the generation step above,
  which globs devices/*.toml" — Generation must run before the pytest tier is backgrounded (Part E.1
  `zz_test_` race); ordering-only guarantee. · related: SCR.S07 · [H09]
- **SCR.N027** ASSUME · `scripts/test.sh:218-224` — "1200s is ~5x its measured ~248s" — pytest-tier
  timeout derived from one measured runtime; CI timeout-minutes is the outer backstop. · related:
  TEST.T13 · [H09]
- **SCR.N028** SETTLED · `scripts/test.sh:226-227` — "No retry, unlike the per-file loop" — Whole-suite
  pytest timeout is deliberately never retried. · [H09]
- **SCR.N029** INVAR · `scripts/test.sh:233-234` — "Nothing else in the foreground re-globs devices/
  once generation is done" — Convention-only; a later foreground glob of `devices/` would reopen the
  zz_test_ race. · related: SCR.T06 · [H09]
- **SCR.N030** INVAR · `scripts/test.sh:239-244, 251-253` — "bash does not kill background jobs when the
  parent exits" / "no dependency on pkill/procps that a --variant=minbase chroot lacks" — EXIT trap must
  be armed before the background job and kill both subshell and inner `timeout` pid via a pidfile. ·
  related: SCR.T08 · [H09]
- **SCR.N031** SUPPRESS · `scripts/test.sh:249` — "# shellcheck disable=SC2329 # invoked indirectly, by
  the `trap _cleanup EXIT` below" — shellcheck suppression on `_cleanup`. · related: SCR.T08 · [H09]
- **SCR.N032** SUPPRESS · `scripts/test.sh:97, 154, 165, 255, 257, 259, 437, 442, 522, 532` — "`|| true`
  because a job body always returns 0 ... a nonzero `wait -n` can only mean \"no jobs left\"" — Ten `|| true`
  sites: variant probe (97), cgroup read (154), speed probe (165), trap cleanup kills/cat (255/257/259),
  `wait -n`/`wait` reaping (437/442, justified by run_test_file never returning nonzero), annotation
  tail/cat (522/532). · related: SCR.T08 · [H09]
- **SCR.N033** DRIFT · `scripts/test.sh:296` — "tests_scripts/ is already running in the background,
  launched right after the toolchain check" — It is launched after the generation step (line 212/265),
  not right after the toolchain check. · covered-by: SCR.S03 · [H09]
- **SCR.N034** SETTLED · `scripts/test.sh:297-298` — "RUN_SLOW_FIRMWARE_BUILD stays unset for it,
  keeping the one real ARM firmware compile opt-in for local iteration" — Real firmware build test runs
  only in CI's firmware-build-verify, never in a local test.sh run. · covered-by: SCR.T13 · [H09]
- **SCR.N035** INVAR · `scripts/test.sh:303-307` — "bash replaces an EXIT handler rather than stacking,
  so every cleanup has to live in that one trap" — Single-trap rule by convention. · related: SCR.T08 ·
  [H09]
- **SCR.N036** SETTLED · `scripts/test.sh:315-318` — "deliberately empty since the per-device splits,
  and deliberately not solved by raising everyone's default" — Per-file timeout overrides map
  intentionally empty; default 240 s. · related: SCR.S03 · [H09]
- **SCR.N037** RISK · `scripts/test.sh:363-364` — "only the attempt that decided this file's verdict is
  searched for a MemoryError, so a timed-out earlier attempt's partial output cannot fail a passing
  file" — Deliberate: a MemoryError printed during a timed-out attempt is discarded if a retry passes. ·
  related: SCR.T01 · [H09]
- **SCR.N038** RISK · `scripts/test.sh:378-380` — "retrying in case of transient runner contention" —
  Timeout (exit 124) retried up to 3 times, so an intermittent hang passes if any attempt completes.
  (low) · related: SCR.T01 · [H09]
- **SCR.N039** INVAR · `scripts/test.sh:345-351` — "Every segment of MICROPYPATH below is load-bearing.
  \".frozen\" explicitly, because MICROPYPATH REPLACES the default sys.path" — Path order
  `build/generated_src:src:tests:frozen_modules:.frozen` is convention; generated modules first. ·
  related: SCR.T12 · [H09]
- **SCR.N040** ASSUME · `scripts/test.sh:392-398` — "Hand-curated from one measurement run, so
  re-measure and update it if a new heavy file lands" — Heavy-file dispatch list; silently drops missing
  files (all 15 exist at 2a88cc8). · covered-by: SCR.S11 · [H09]
- **SCR.N041** INVAR · `scripts/test.sh:445-451` — "a missing or empty read here is a bug rather than a
  legitimate \"still running\" - never treated as PASS by omission" — Fail-closed status-file read. ·
  related: SCR.T01 · [H09]

## scripts/lint.sh

- **SCR.N042** SETTLED · `scripts/lint.sh:2-4` — "All stay fully clean. Lint only - `ruff format` is
  deliberately unused" — All lint scopes must be zero-finding; `ruff format` is never run. · related:
  SCR.T02 · [H09]
- **SCR.N043** ASSUME · `scripts/lint.sh:6-7` — "Assumes `uv sync` has been run and its venv is active"
  — Tools resolve from PATH; an inactive/stale venv runs whatever ruff/shellcheck is on PATH, bypassing
  the pins. · related: CI.T04 · [H09]
- **SCR.N044** SETTLED · `scripts/lint.sh:15-17` — "deliberately NOT the four legacy build-*.sh at the
  repo root" — Legacy build scripts are out of lint scope by standing decision. · [H09]
- **SCR.N045** INVAR · `scripts/lint.sh:28-34` — "tests/ and digital_twin/ legitimately monkeypatch
  methods, shipped src/ never may" — No `type: ignore[...method-assign...]` in `src/`; enforced by this
  grep (it matches only the coded form of the suppression). · related: SCR.T02 · [H09]

## scripts/typecheck.sh

- **SCR.N046** ASSUME · `scripts/typecheck.sh:7` — "Assumes mypy is on PATH" — Pinned mypy only if the
  synced venv is active. · related: CI.T04 · [H09]
- **SCR.N047** SETTLED · `scripts/typecheck.sh:10-11` — "The firmware version lives in exactly one
  place, toolchain/versions.toml's [micropython] ref; the stub version below is derived from it" — Stub
  version must never be pinned separately. · related: SCR.T02 · [H09]
- **SCR.N048** PLATFORM · `scripts/typecheck.sh:12, 17` — "Requires python3 >= 3.11 for tomllib" — The
  version derivation runs under a bare host `python3`, not the venv/uv interpreter. · covered-by:
  SCR.T09 · [H09]
- **SCR.N049** SETTLED · `scripts/typecheck.sh:76-78` — "This needs a manual decision ... there is no
  automatic fallback." — Missing upstream stubs for a new pin block typecheck until the owner decides. ·
  [H09]
- **SCR.N050** LIMIT · `scripts/typecheck.sh:87-89` — "a fixed upstream or a restructured tree makes it
  a silent no-op rather than a failure" — If the stub tree moves, the repair silently stops applying;
  the NotImplemented stub ships CRLF. (low) · related: PLAT.T05 · [H09]
- **SCR.N051** INVAR · `scripts/typecheck.sh:99-103` — "heap_headroom_after_full_system_build.py is the
  main pass's sole static `import sensortask_dev`" — `build/generated_src/` must be regenerated before
  mypy; the main pass resolves generated modules silently. · related: GEN.S17 · [H09]
- **SCR.N052** SETTLED · `scripts/typecheck.sh:111-116, 123-130` — "The twin is a fully-reviewed scope
  like src/ and tests/, so a finding here is real" — The twin and host passes always run and fail the
  script, regardless of narrowing args. · related: SCR.T15 · [H09]

## scripts/_require_clean_hardware_run.sh

- **SCR.N053** SETTLED · `scripts/_require_clean_hardware_run.sh:5` — "deliberately not -e: the verdict
  comes from pytest's own output, not its exit code" — Verdict is derived from parsing pytest output. ·
  covered-by: SCR.T08 · [H09]
- **SCR.N054** LIMIT · `scripts/_require_clean_hardware_run.sh:19-24` — "[ \"$arg\" = \"--soak-tier\" ]
  && soak_tier=1" — Flags matched by exact token only; `--soak-tier=x` form not recognised. ·
  covered-by: SCR.S01 · [H09]
- **SCR.N055** LIMIT · `scripts/_require_clean_hardware_run.sh:71-74` — "*\"$name\"*) known=1 ;;" —
  Whitelist match is a substring match on the node id, so any test whose id contains a whitelisted name
  (e.g. parametrized variants) is also accepted as a skip. (low) · related: SCR.T05 · [H09]
- **SCR.N056** ASSUME · `scripts/_require_clean_hardware_run.sh:79, 93, 101` — "grep -oE
  '^tests_hardware/\S+ SKIPPED'" — Skip/pass/deselect accounting depends on pytest `-v` output format
  (pytest is unpinned). · related: CI.S05 · [H09]
- **SCR.N057** LIMIT · `scripts/_require_clean_hardware_run.sh:61-66` — "--collect-only never actually
  runs anything - the skip/pass accounting below doesn't apply." — A `--collect-only` run returns 0
  after only pytest's exit code. · related: SCR.T05 · [H09]
- **SCR.N058** ASSUME · `scripts/_require_clean_hardware_run.sh:91-92` — "pytest omits the word entirely
  today, so this is defensive, not observed" — Unverified claim about pytest's summary wording. · [H09]
- **SCR.N059** DRIFT · `scripts/_require_clean_hardware_run.sh:106` — "Add --allow-persistence-writes
  (and/or the other --allow-* flags) to." — Truncated sentence in the user-facing verdict. · covered-by:
  SCR.S01 · [H09]

## scripts/run_bench_hardware_suite.sh

- **SCR.N060** SETTLED · `scripts/run_bench_hardware_suite.sh:5-7, 11` — "excludes the soak markers
  unconditionally - they need their own deliberate invocation" — Relies on `-m` before `"$@"`; a
  caller's own `-m` replaces it (pytest last-wins). · covered-by: SCR.S01 · [H09]

## scripts/run_bench_soak_tests.sh

- **SCR.N061** LIMIT · `scripts/run_bench_soak_tests.sh:14-20` — "if [ \"${1:-}\" != \"--tier\" ] || [
  -z \"${2:-}\" ]" — Tier value is not validated here (delegated to conftest). (low) · related: SCR.T05
  · [H09]

## scripts/run_flash_hardware_suite.sh

- **SCR.N062** SETTLED · `scripts/run_flash_hardware_suite.sh:5-7, 11` — "excludes the soak markers
  unconditionally" — Same `-m` last-wins caveat as the bench runner. · covered-by: SCR.S01 · [H09]

## scripts/run_digital_twin_ci.sh

- **SCR.N063** DRIFT · `scripts/run_digital_twin_ci.sh:10-11` — "Clean wipes leftover
  digital_twin/*.json state and digital_twin/config/ ... deliberately redundant with
  _digital_twin_ci_suite.py's own identical clean" — The script body (lines 20-59) contains no clean
  step at all; the only clean is the suite's own `_clean_state()`, so the claimed redundancy does not
  exist. · related: SCR.S09 · [H09]
- **SCR.N064** ASSUME · `scripts/run_digital_twin_ci.sh:8` — "so each device's 14-run suite is
  attributable on its own" — Run count stated as 14; the suite now has numbered sub-runs (e.g. 11, 11b).
  (low) · related: SCR.T04 · [H09]
- **SCR.N065** MIRROR · `scripts/run_digital_twin_ci.sh:25` — "export TZ=UTC # same reasoning as
  scripts/test.sh's own identical export." — TZ pin duplicated in three scripts (test.sh, this,
  run_unix_port_integration.sh). · related: XCUT.T18 · [H09]
- **SCR.N066** LIMIT · `scripts/run_digital_twin_ci.sh:28-37` — "if [ ! -x \"$micropython_bin\" ]" —
  Existence check only; no variant/staleness probe (unlike test.sh). · covered-by: SCR.S05 · [H09]
- **SCR.N067** LIMIT · `scripts/run_digital_twin_ci.sh:23, 50, 59` — "device=\"${1:-wozi}\"" — Device
  name is unvalidated and flows into paths; logs go to the fixed repo path `digital_twin_ci_logs`. ·
  covered-by: SCR.T14 · [H09]

## scripts/run_unix_port_integration.sh

- **SCR.N068** MIRROR · `scripts/run_unix_port_integration.sh:10-12` — "a test file works around the
  ext-less path with its own sys.path.insert, the real entry point needs the real fix" — test.sh's
  MICROPYPATH lacks `ext`, so a test file hand-inserts it; the real entry point adds `ext` here. ·
  related: SCR.T12 · [H09]
- **SCR.N069** LIMIT · `scripts/run_unix_port_integration.sh:36-38` — "device=\"$2\"" — `--device` with
  no value aborts under `set -u`; value unvalidated. · covered-by: SCR.T14 · [H09]
- **SCR.N070** LIMIT · `scripts/run_unix_port_integration.sh:50-57` — "if [ ! -x \"$micropython_bin\" ]"
  — Existence check only. · covered-by: SCR.S05 · [H09]

## scripts/build_frozen_html.sh

- **SCR.N071** SETTLED · `scripts/build_frozen_html.sh:2-4` — "why never --compress, and why the output
  goes to frozen_modules/ rather than the .frozen/ import sentinel" — Pipeline choices owned by Part
  A.9. · related: SCR.T03 · [H09]
- **SCR.N072** SETTLED · `scripts/build_frozen_html.sh:10-11` — "ext/freezefs is vendored and
  unmodified. Don't copy build-wozi.sh's literal invocation" — Legacy `-s` flag gone in freezefs 2.4. ·
  [H09]
- **SCR.N073** PLATFORM · `scripts/build_frozen_html.sh:30-32` — "ext/freezefs has no __init__.py
  (freezefs 2.4 upstream ships it as an implicit namespace package)" — Build depends on vendored
  freezefs 2.4 layout and CLI flags (`--on-import mount --target --overwrite always --silent`). ·
  related: SCR.T03 · [H09]
- **SCR.N074** LIMIT · `scripts/build_frozen_html.sh:7, 22` — "a space-separated list merged recursively
  into one build tree" / "for src_dir in $src_dirs" — Unquoted word-split loop; a directory with spaces
  breaks. · covered-by: SCR.S08 · [H09]
- **SCR.N075** LIMIT · `scripts/build_frozen_html.sh:25` — "find \"$tmp_dir\" -type f -exec gzip -9 {}
  +" — No `-n`: embedded mtime makes the frozen image non-deterministic. · covered-by: SCR.S04 · [H09]
- **SCR.N076** PLATFORM · `scripts/build_frozen_html.sh:33` — "python3 -m freezefs" — Runs under bare
  host `python3`. · covered-by: SCR.T09 · [H09]

## scripts/build_website.sh

- **SCR.N077** PLATFORM · `scripts/build_website.sh:37, 40` — "python3 -m buildgen.definitions" —
  buildgen and the inliner run under bare host `python3`, not uv/venv. · covered-by: SCR.T09 · [H09]

## scripts/_generate_sensortask_modules.py

- **SCR.N078** SUPPRESS · `scripts/_generate_sensortask_modules.py:21-24` — "from buildgen.errors import
  BuildError # noqa: E402" — Four E402 suppressions (a non-sys.path statement, `REPO_ROOT = ...`,
  precedes the imports). · [H09]
- **SCR.N079** DRIFT · `scripts/_generate_sensortask_modules.py:10-12` — "Called by test.sh,
  typecheck.sh, run_unix_port_integration.sh and run_digital_twin_ci.sh" — Caller list omits
  `package.json:10` (`build:site`) and `.github/workflows/ci.yml:298`. (low) · related: SCR.S07 · [H09]
- **SCR.N080** LIMIT · `scripts/_generate_sensortask_modules.py:28-51` — "(out_dir /
  f\"sensortask_{device}.py\").write_text(generated.module_source)" — Never prunes stale modules/plans
  from `build/generated_src/` and writes non-atomically while other tiers read it. · covered-by: SCR.S07
  · [H09]
- **SCR.N081** ASSUME · `scripts/_generate_sensortask_modules.py:30` — "Every real device, not just the
  two tests consume today" — Dated claim about how many devices tests consume (per-device test files now
  exist for all six). (low) · [H09]

## scripts/_render_coverage.py

- **SCR.N082** SUPPRESS · `scripts/_render_coverage.py:17` — "import coverage # type:
  ignore[import-not-found]" — coverage is not a dev dependency, so mypy cannot see it. · [H09]
- **SCR.N083** SETTLED · `scripts/_render_coverage.py:7` — "Self-contained via `uv run` ... rather than
  a pyproject.toml dev dependency" — Deliberate packaging choice. · [H09]
- **SCR.N084** ASSUME · `scripts/_render_coverage.py:46` — "repo_root = os.getcwd()" — Must be run from
  the repo root; relative paths in the raw dumps are joined to cwd. (low) · [H09]

## scripts/_strip_type_checking.py

- **SCR.N085** LIMIT · `scripts/_strip_type_checking.py:52-64` — "if not node.orelse and
  _is_bare_type_checking_test(node.test)" — `if TYPE_CHECKING: ... else:` and compound tests are kept
  while the import guard is removed unconditionally. · covered-by: GEN.S12 · [H09]
- **SCR.N086** PLATFORM · `scripts/_strip_type_checking.py:77` — "output: str =
  ast.unparse(stripped_tree)" — What ships is the host-CPython-version-dependent `ast.unparse` output
  (comments dropped). · covered-by: SCR.T09 · [H09]
- **SCR.N087** LIMIT · `scripts/_strip_type_checking.py:78` — "validity check: raises SyntaxError if the
  transform produced garbage" — Validated by CPython `ast.parse` only, never compiled by mpy-cross or
  executed by any tier. · covered-by: SCR.T10 · [H09]

## scripts/build_firmware.py

- **SCR.N088** LIMIT · `scripts/build_firmware.py:7-8` — "A clean build is necessary, not sufficient,
  for a device to boot." — CI's firmware build proves compilation only. · related: SCR.T10 · [H09]
- **SCR.N089** SUPPRESS · `scripts/build_firmware.py:27, 30, 36, 37` — "from _strip_type_checking import
  strip_type_checking_blocks # type: ignore[import-not-found] # noqa: E402" — Four E402 suppressions
  plus one `import-not-found`. · [H09]
- **SCR.N090** INVAR · `scripts/build_firmware.py:53-55` — "Strips this build's staged copy only, never
  the real src/ or ext/ file (CLAUDE.md's hard rule" — Vendored/`src` files must never be rewritten in
  place. · related: SCR.T03 · [H09]
- **SCR.N091** LIMIT · `scripts/build_firmware.py:72-90` — "a future src/ file sharing one of those
  names would silently overwrite it" — Only the three reserved names are collision-checked; a module
  present in both `src/` and `ext/` silently resolves to `src/`. (low) · related: GEN.T05 · [H09]
- **SCR.N092** LIMIT · `scripts/build_firmware.py:99` — "(stage_dir /
  \"main.py\").write_text(generated.boot_entry_source)" — The shipped boot entry is executed by no tier.
  · covered-by: SCR.S10 · [H09]
- **SCR.N093** LIMIT · `scripts/build_firmware.py:169-173` — "except (subprocess.CalledProcessError,
  st.SetupError, RuntimeError)" — Other exceptions (OSError) end as tracebacks. (low) · related: GEN.T16
  · [H09]

## scripts/_digital_twin_ci_suite.py

- **SCR.N094** INVAR · `scripts/_digital_twin_ci_suite.py:33-36` — "MICROPYPATH =
  \"build/generated_src:src:digital_twin:ext:frozen_modules:.frozen\"" — Suite depends on
  run_digital_twin_ci.sh having regenerated `build/generated_src/` first; path duplicated in
  run_unix_port_integration.sh:78. · related: SCR.T12 · [H09]
- **SCR.N095** ASSUME · `scripts/_digital_twin_ci_suite.py:38-40` — "PORT = 18080 # a fixed,
  non-privileged, non-8080-default port" / "DNS_PORT = 53 ... real port only" — Fixed ports: collides
  with any other listener on 18080/53 (CLAUDE.md "two suites that bind real ports"). · covered-by:
  SCR.T04 · [H09]
- **SCR.N096** SUPPRESS · `scripts/_digital_twin_ci_suite.py:207` — "# noqa: PLC0415 - needs the path
  entry above" — Deferred import suppression. · [H09]
- **SCR.N097** SUPPRESS · `scripts/_digital_twin_ci_suite.py:446` — "# type: ignore[attr-defined] #
  stashed only so _shutdown() below can close it" — Ad-hoc attribute on `Popen`. · [H09]
- **SCR.N098** SUPPRESS · `scripts/_digital_twin_ci_suite.py:658, 681, 712, 758, 786, 822, 873, 914, 932, 972, 1004, 1030, 1051, 1065, 1091, 1145`
  — "except Exception as exc: # CI orchestration: surface any failure as a suite failure, not a crash" —
  16 broad catches convert every run's exception into `_fail()`; correctness depends on each calling
  `_fail`. · related: SCR.T04 · [H09]
- **SCR.N099** SUPPRESS · `scripts/_digital_twin_ci_suite.py:405, 477, 481` — "except OSError: pass" —
  Swallowed during readiness polling and best-effort /proc diagnostics ("Never allowed to raise -
  diagnostic only"). · [H09]
- **SCR.N100** LIMIT · `scripts/_digital_twin_ci_suite.py:519-527` — "For bounded (--duration N) runs
  that exit on their own" — A timeout in `_wait_exit` kills with no diagnostics (only `_shutdown`
  captures /proc and log tail). (low) · [H09]
- **SCR.N101** LIMIT · `scripts/_digital_twin_ci_suite.py:463-465` — "Linux-only, which every runner
  here is." — Diagnostics assume Linux /proc. (low) · [H09]
- **SCR.N102** DRIFT · `scripts/_digital_twin_ci_suite.py:6` — "invoked by
  `scripts/run_digital_twin_ci.sh` (which owns \"clean\"/\"build\" ...)" — run_digital_twin_ci.sh
  performs no clean; the suite's own `_clean_state()` (:238-249) is the only one, and it removes only
  two named JSON files plus `config/`. · related: SCR.S09 · [H09]

## scripts/cross_browser_smoke.mjs

- **SCR.N103** LIMIT · `scripts/cross_browser_smoke.mjs:13-14, 441-444` — "MicroPython Unix port not
  built at ${MICROPYTHON_BIN}" — Existence check only, on `build-standard`; no variant/staleness probe.
  · covered-by: SCR.S05 · [H09]
- **SCR.N104** INVAR · `scripts/cross_browser_smoke.mjs:15-18` — "web-cross-browser-smoke job generates
  it fresh there, via buildgen, before this spawns" — Relies on the caller having regenerated
  `build/generated_src/`; running it alone uses whatever is there. · related: SCR.T12 · [H09]
- **SCR.N105** WORKAROUND · `scripts/cross_browser_smoke.mjs:134-139` — "Xvfb is spawned directly rather
  than through `xvfb-run`, which is a layer this file cannot reliably tear down" — Leaked Xvfb/driver
  processes observed with xvfb-run. · [H09]
- **SCR.N106** SUPPRESS · `scripts/cross_browser_smoke.mjs:63, 71, 158, 253, 258, 378, 383, 482` —
  "eslint-disable-next-line no-await-in-loop -- deliberate sequential polling" — Eight eslint
  suppressions. · [H09]
- **SCR.N107** SUPPRESS · `scripts/cross_browser_smoke.mjs:179, 428` — "teardown is best-effort - a dead
  driver is not a smoke-check failure" — Teardown errors swallowed. · [H09]
- **SCR.N108** RISK · `scripts/cross_browser_smoke.mjs:448` — "rmSync(path.join(REPO_ROOT,
  \"digital_twin\", \"config\"), { recursive: true, force: true });" — Wipes the shared repo-level twin
  config also used by the CI suite and Vitest live twins. · covered-by: SCR.S09 · [H09]
- **SCR.N109** LIMIT · `scripts/cross_browser_smoke.mjs:432-434` — "Harmless in CI, where the VM is
  reclaimed anyway, and a real leak for local development." — Signal cleanup exists only for
  SIGINT/SIGTERM. · related: TEST.T16 · [H09] ⟨quote not matched at the anchor⟩

## buildgen/version.py

- **SCR.N110** PLATFORM · `buildgen/version.py:5` — "from datetime import UTC, datetime" — Requires host
  CPython >= 3.11. · covered-by: SCR.T09 · [H09]

## pyproject.toml

- **SCR.N111** SUPPRESS · `pyproject.toml:311-323` — "S603 (untrusted subprocess input) has no
  satisfiable form for a build driver" — scripts/build_firmware.py, scripts/_digital_twin_ci_suite.py,
  toolchain/setup_toolchain.py, toolchain/micropython_overrides.py: S603. · related: TOOL.T01 · [H09]
- **SCR.N112** SUPPRESS · `pyproject.toml:373-391` — "Excluded, each for a reason B.15 states" — Main
  mypy pass excludes tests/network.py, five digital_twin files, tests/test_digital_twin_*.py and two
  scenario libraries (checked by digital_twin/typecheck.ini instead). · covered-by: SCR.T15 · [H09]

## host_typecheck.ini

- **SCR.N113** PLATFORM · `host_typecheck.ini:1-8` — "ordinary CPython 3.11 programs that need mypy's
  real typeshed" — `python_version = 3.11` for all host tooling. · related: SCR.T09 · [H09]
- **SCR.N114** SUPPRESS · `host_typecheck.ini:11-17` — "device_scripts/ is MicroPython code run on the
  board (121 errors here, 99 artifacts)" / "tests_scripts/conftest.py ... an accepted gap (B.15)" — Two
  exclusions; conftest.py is never type-checked (accepted). · covered-by: SCR.T15 · [H09]
- **SCR.N115** MIRROR · `host_typecheck.ini:19-25` — "The other entries mirror the sys.path pytest
  builds at runtime (harness, dns_probe, runner, _toml_fixtures, micropython_overrides), without which
  the harness API types as Any" — `mypy_path` hand-mirrors pytest's runtime sys.path; drift silently
  degrades to `Any`. · covered-by: SCR.T15 · [H09]
- **SCR.N116** SETTLED · `host_typecheck.ini:31-36` — "Full --strict, no exemptions ...
  no_implicit_reexport is enforced here too" — Strictness of the host pass. · related: SCR.T15 · [H09]

## tests_scripts/test_build_firmware.py

- **SCR.N117** SUPPRESS · `tests_scripts/test_build_firmware.py:196-201` —
  "os.environ.get(\"RUN_SLOW_FIRMWARE_BUILD\") != \"1\"" — The only real ARM firmware build is skipped
  unless opted in; CI's `firmware-build-verify` sets it; a plain local `scripts/test.sh` never builds a
  UF2 · covered-by: SCR.T13 · [H10]
- **SCR.N118** LIMIT · `tests_scripts/test_build_firmware.py:213-216` — "assert data[:4] == b\"UF2\\n\""
  — UF2 "validity" = magic bytes + length multiple of 512; frozen content, boot entry, board family ID
  are not checked · related: SCR.T10 · [H10]
- **SCR.N119** ASSUME · `tests_scripts/test_build_firmware.py:36-38` — "a contract mismatch buildgen's
  guarantees should prevent ... build_stage_dir reading only four attributes" — Fake GeneratedDevice
  fidelity rests on build_stage_dir reading exactly four attributes · [H10]
- **SCR.N120** ASSUME · `tests_scripts/test_build_firmware.py:55-56` — "No src/ file is called
  \"main.py\" today" — Reserved-name collision guard is reached only through a patched fake tree · [H10]
- **SCR.N121** INVAR · `tests_scripts/test_build_firmware.py:151-157` — "config_manager.py is a known if
  TYPE_CHECKING: user ... CLAUDE.md's hard rule against editing src/ for a build-only concern" — Pins
  that staged copies are TYPE_CHECKING-stripped while src/ keeps the guard; only config_manager.py is
  checked · related: SCR.T10 · [H10]
- **SCR.N122** LIMIT · `tests_scripts/test_build_firmware.py:77-87` — "Each device's boot module is
  frozen as \"main.py\", so the default board manifest is reused unchanged" — Manifest test checks two
  substrings only; PLATFORM history: the old custom `_boot.py` skipping the board manifest "broke USB
  entirely (Part F.1)" · [H10]
- **SCR.N123** LIMIT · `tests_scripts/test_build_firmware.py:192` — "assert \"no-toolchain-here\" in
  result.stderr or \"toolchain\" in result.stderr.lower()" — Loose oracle for the missing-toolchain CLI
  path (any stderr mentioning "toolchain" passes) (low) · [H10]
- **SCR.N124** ASSUME · `tests_scripts/test_build_firmware.py:204-205` — "Needs the toolchain already
  installed, which test.sh and the unit-tests job both provision first" — Opt-in test does not itself
  skip on a missing toolchain · [H10]

## tests_scripts/test_build_frozen_html_sh.py

- **SCR.N125** LIMIT · `tests_scripts/test_build_frozen_html_sh.py:9-11` — "Grepping the generated text
  for those literals checks what was archived without running it" — Oracle is substring presence of
  mount paths in freezefs output; archived content, gzip validity and runtime mount are not checked here
  (content is `tests/test_website_build_integration.py`'s job) · [H10]
- **SCR.N126** LIMIT · `tests_scripts/test_build_frozen_html_sh.py:73-76` —
  "test_missing_source_dir_fails_instead_of_silently_producing_an_empty_archive" — Missing-dir case
  asserts only nonzero exit and no output; an empty-but-existing source dir, and paths with spaces
  (unquoted loop, SCR.S08), are untested · related: SCR.S08 · [H10]
- **SCR.N127** SETTLED · `tests_scripts/test_build_frozen_html_sh.py:29` — "No default source since
  html_stub/ was retired" — build_frozen_html.sh must refuse without HTML_SRC_DIRS · [H10]

## tests_scripts/test_digital_twin_ci_suite_ceiling.py

- **SCR.N128** INVAR · `tests_scripts/test_digital_twin_ci_suite_ceiling.py:149-150` — "never an escape
  that skips the shutdown and leaves a twin holding the port for every later run" — Run functions must
  catch their own crash and still shut the twin down (fixed port reuse across runs) · related: SCR.T04 ·
  [H10]

## tests_scripts/test_digital_twin_ci_suite_errcount.py

- **SCR.N129** LIMIT · `tests_scripts/test_digital_twin_ci_suite_errcount.py:307-314` — "a second raw
  _http(\"PUT\", \"/status\", {\"ResetErrors\": ...}) is exactly how the gap would reappear" —
  Single-site guard matches only lines containing both `"ResetErrors"` and `_http(` — a call split
  across lines or built from a variable escapes it · [H10]

## tests_scripts/test_generate_sensortask_modules.py

- **SCR.N130** LIMIT · `tests_scripts/test_generate_sensortask_modules.py:49-67` — "Never left holding a
  half-written module (or wiring plan) for the device that failed." — Failure path tested with a
  monkeypatched generator only; stale outputs from earlier runs and non-atomic writes are not tested ·
  covered-by: SCR.S07 · [H10]

## tests_scripts/test_lint_sh.py

- **SCR.N131** INVAR · `tests_scripts/test_lint_sh.py:1-3` — "their own failure mode is silent: a
  drifted pattern stops matching and the gate goes green on a real violation" — lint.sh's three grep
  guards (method-assign in src/, gc.collect in src/, gc.collect in buildgen/) are extracted from the
  live script and run against fabricated trees and the live tree · related: SCR.T02 · [H10]
- **SCR.N132** LIMIT · `tests_scripts/test_lint_sh.py:16-21` — "The one `if grep ...; then ... fi` block
  of scripts/lint.sh whose message contains `needle`" — Extraction assumes each guard is one `if grep ... fi`
  block at column 0 keyed by its message text; a restructured guard fails loudly (not silently) · [H10]

## tests_scripts/test_request_timeout_ceiling.py

- **SCR.N133** MIRROR · `tests_scripts/test_request_timeout_ceiling.py:72-97` — "_SERVER_OUTER_CAP_S
  carries a \"keep in sync\" comment and nothing enforced it" — Enforced: twin suite
  `_SERVER_OUTER_CAP_S == outer_cap_s`, its `_RESET_ERRORS_TIMEOUT_S` in (cap, cap+5];
  tests_hardware/error_log_helpers.py's hardcoded copy only bounded below ("extra slack for real WiFi
  latency") · related: PERF.T03 · [H10]

## tests_scripts/test_require_clean_hardware_run_sh.py

- **SCR.N134** SETTLED · `tests_scripts/test_require_clean_hardware_run_sh.py:13-21` —
  "persistence_write/scd30_extra_write are deliberately absent: they DESELECT rather than skip, which is
  invisible to this script by design" — Pinned marker→flag map for skip gates: flash_cycle, long_soak
  (`--soak-tier`), multi_day_rollover, neopixel_sweep · related: HW.T13 · [H10]
- **SCR.N135** ASSUME · `tests_scripts/test_require_clean_hardware_run_sh.py:175-177` — "pytest does not
  print \"0 passed\" today, but a plugin or a future summary format that did" — Verdict parsing depends
  on pytest's summary-line format (`tail -1` of "N deselected") · related: SCR.T05 · [H10]
- **SCR.N136** LIMIT · `tests_scripts/test_require_clean_hardware_run_sh.py:24-34` — "The script's own
  contextual whitelist, parsed back out of it" — Whitelist parsed from the shell script by regex (`[ "$arg" = "--flag" ] && var=1`
  / `if [ "$var" = 0 ]; then`); `--flag=value` forms are not modelled · related: SCR.S01 · [H10]

## tests_scripts/test_setup_cross_browser_toolchain_sh.py

- **SCR.N137** WORKAROUND · `tests_scripts/test_setup_cross_browser_toolchain_sh.py:1-3,11` —
  "_TOLERANCE = ' || echo \"== apt-get update reported errors - continuing, the install below still
  gates\"'" — `apt-get update` failures are deliberately swallowed (third-party source breakage) while
  every `apt-get install` stays fatal (enforced); removal trigger: none stated · [H10]
- **SCR.N138** LIMIT · `tests_scripts/test_setup_cross_browser_toolchain_sh.py:15-16,31-36` — "present
  so only the WebKit block, the one that reaches apt, actually runs" — Only the WebKit/apt block is
  exercised; Edge/Firefox install paths (external downloads, micromamba) are stubbed out · related:
  CI.S06 · [H10]

## tests_scripts/test_strip_type_checking.py

- **SCR.N139** LIMIT · `tests_scripts/test_strip_type_checking.py:50-62` — "if TYPE_CHECKING and
  extra_check():" / "if TYPE_CHECKING:\n W = 1\nelse:" — Pinned known behaviour: compound conditions and
  `if/else` forms are left in the shipped copy unstripped · related: GEN.S12 · [H10]
- **SCR.N140** LIMIT · `tests_scripts/test_strip_type_checking.py:91-104` — "Some files extend the
  except handler with a runtime cast() fallback ... the transform correctly leaves it alone" — Real-src
  check asserts only that no `if TYPE_CHECKING:` remains and the output parses; runtime behaviour of
  stripped copies is never executed · covered-by: SCR.T10 · [H10]

## tests_scripts/test_test_sh.py

- **SCR.N141** INVAR · `tests_scripts/test_test_sh.py:31-44,47-53` — "The race this ordering closes: the
  generator globs devices/*.toml, while the malformed-TOML test writes a throwaway one into the live
  tree" — test.sh must sweep `devices/zz_test_*.toml`, then generate, then background the pytest tier
  (source-order substring checks) · related: TEST.T13 · [H10]
- **SCR.N142** INVAR · `tests_scripts/test_test_sh.py:142-153,180-190,214-223` — "250/900 are the
  boundaries scripts/test.sh compares with -le" — Parallelism probe bands, cgroup-v2 quota clamp,
  `TEST_PARALLELISM=0` hang guard ("`wait -n || true` spin forever") pinned; bench Pi4 is the 2x class ·
  related: SCR.T01 · [H10]
- **SCR.N143** ASSUME · `tests_scripts/test_test_sh.py:106-108,244-246` — "a mid-band 0.7s stub read
  919-963ms under 96 spinners on 2026-09-22" / "131-141ms idle against 391ms in situ, 8 jobs where 16
  was warranted" — Dated single measurements behind the stubbed-clock design and the probe-placement
  rule · related: TEST.T04 · [H10]
- **SCR.N144** INVAR · `tests_scripts/test_test_sh.py:269-271,330-331` — "bash does not kill background
  jobs when the parent exits, so an abort before the final `wait` orphaned it for up to 1200s" —
  `_cleanup()` EXIT trap must signal recorded pids, never `pkill` ("procps is absent from a
  --variant=minbase chroot") · related: TEST.T16 · [H10]
- **SCR.N145** INVAR · `tests_scripts/test_test_sh.py:384-437` — "a ~/pico-toolchain predating the split
  holds an executable build-standard that still carries the flag, which an existence check accepts" —
  unix_port_variant() must report plain/settrace/unusable (incl. missing frozen asyncio) and a mismatch
  must rebuild then exit if still wrong · covered-by: SCR.S05 · [H10]
- **SCR.N146** INVAR · `tests_scripts/test_test_sh.py:513-555` — "a real race until 2026-09-22: the
  rejection tests above run a nested test.sh ... a nested run that swept before validating deleted them
  mid-test" — Argument/GC_THRESHOLD validation must precede `rm -rf tests/_tmp` and the devices sweep;
  these tests run the REAL test.sh nested inside the tier · related: SCR.T14 · [H10]

## SPECIFICATION.md Part A.9 (The frozen-HTML pipeline, 627-653)

- **SCR.N147** INVAR · `SPECIFICATION.md:652-653` — "The two suites still must not run concurrently, for
  their ports (CLAUDE.md)" — Review-only rule; nothing prevents concurrent runs. · related: SCR.T06 ·
  [H12]

## SPECIFICATION.md Part B intro, B.1-B.3 (688-753)

- **SCR.N148** INVAR · `SPECIFICATION.md:730-732` — "Because a build directory's name no longer tells
  you which variant is in it, `scripts/test.sh` verifies the binary rather than the path" — Only test.sh
  probes the variant; twin/web runners hardcode `build-standard` and check existence only. · covered-by:
  SCR.S05 · [H12]

## SPECIFICATION.md Part B.10 / B.10.1 (CI perspective, 828-929)

- **SCR.N149** DRIFT · `SPECIFICATION.md:906-908` — "a ~17-minute warm run plus one file's full 9-minute
  retry budget (180 s x 3)" — test.sh default is 240 s. · covered-by: SCR.S03 · [H12]

## SPECIFICATION.md Part B.11 (Building this project's firmware, 931-984)

- **SCR.N150** ASSUME · `SPECIFICATION.md:963-965` — "`mpy-cross` doesn't dead-code-eliminate `if TYPE_CHECKING:`
  ... dead weight (~3.6KB measured)" — Compiler behaviour + single measurement. · related: SCR.T03 ·
  [H12]
- **SCR.N151** LIMIT · `SPECIFICATION.md:966-970` — "Side effect: strips every comment from the file ...
  an on-device traceback's line numbers won't match checked-in `src/`" — Shipped bytecode differs from
  source line-for-line. · related: SCR.T10 · [H12]
- **SCR.N152** SUPPRESS · `SPECIFICATION.md:974` — "gated behind `RUN_SLOW_FIRMWARE_BUILD=1`" — Real
  firmware build skipped locally unless opted in (`tests_scripts/test_build_firmware.py:198-199`). ·
  covered-by: SCR.T13 · [H12]
- **SCR.N153** LIMIT · `SPECIFICATION.md:978-984` — "still build-only, not an on-device functional check
  ... This script's success is necessary, not sufficient, for a real device to boot." — Build pipeline
  proves assembly only. · related: SCR.T10 · [H12]

## SPECIFICATION.md Part B.14.1 (`unix_kbd_intr`, 1116-1213)

- **SCR.N154** MIRROR · `SPECIFICATION.md:1181-1185` — "would ... rename `BUILD ?= build-$(VARIANT)`
  away from `build-standard`, which every other script in this repo hardcodes" — `build-standard` path
  hardcoded in `scripts/run_digital_twin_ci.sh:28`, `run_unix_port_integration.sh:48`,
  `cross_browser_smoke.mjs:14`, `tests_js/_live_*_command.js`. · related: SCR.S05 · [H12]

## SPECIFICATION.md Part B.15 (The three mypy passes, 1413-1473)

- **SCR.N155** RISK · `SPECIFICATION.md:1425-1426` — "`follow_imports_for_stubs` extends that to the
  (upstream-Beta) stub package itself" — Type-check correctness rests on a Beta third-party stub package
  (two repaired defects, CLAUDE.md). · related: PLAT.T05 · [H12]
- **SCR.N156** INVAR · `SPECIFICATION.md:1429-1430` — "`files` names directories, never globs: a glob is
  pre-expanded into a file list that `exclude` can no longer prune." — Config convention. · [H12]
- **SCR.N157** SUPPRESS · `SPECIFICATION.md:1434-1445` — "Excluded, and why. `tests/network.py` ...
  `digital_twin/machine.py`, `network.py`, `neopixel.py` ... `launch.py`, `run_generic_integration.py`,
  `segfault_stress_repro.py`, every `tests/test_digital_twin_*.py` and the two shared scenario
  libraries" — Main-pass mypy exclusions (checked by the twin pass instead). · related: SCR.T15 · [H12]
- **SCR.N158** LIMIT · `SPECIFICATION.md:1443-1445` — "Their apparent cleanliness in this pass was
  accidental: a real `no-any-return` in `test_digital_twin_bmp3xx.py` appeared only once `digital_twin`
  was in scope." — Exclusions can hide findings. · related: TEST.T19 · [H12]
- **SCR.N159** SUPPRESS · `SPECIFICATION.md:1446-1449` — "The one exemption, `no_implicit_reexport = false`,
  and the `disallow_untyped_decorators` override for `test_setter_microdot_integration`" — Main-pass
  strictness exemptions. · related: SCR.T15 · [H12]
- **SCR.N160** MIRROR · `SPECIFICATION.md:1454-1455` — "its strictness is kept in sync with the main
  pass by hand (INI has no include directive)" — Three configs hand-synced; no check. · covered-by:
  SCR.T15 · [H12]
- **SCR.N161** SUPPRESS · `SPECIFICATION.md:1460-1461` — "`tests_hardware/device_scripts/` is excluded
  here (MicroPython code: 121 errors, 99 artifacts)" — Host-pass exclusion; dated counts. · [H12]
- **SCR.N162** SUPPRESS · `SPECIFICATION.md:1462-1466` — "`tests_scripts/conftest.py` is excluded ... an
  accepted gap against re-laying out either tier" — Accepted type-check gap. · covered-by: SCR.T15 ·
  [H12]
- **SCR.N163** MIRROR · `SPECIFICATION.md:1469-1473` — "The other `mypy_path` entries mirror the
  `sys.path` pytest builds at runtime" — mypy_path ↔ pytest sys.path hand mirror. · [H12]

## SPECIFICATION.md Part E intro, E.1 (2732-2788)

- **SCR.N164** INVAR · `SPECIFICATION.md:2753-2756` — "every step that globs `devices/*.toml` must run
  before the background launch, because one `tests_scripts/` test necessarily writes a throwaway
  `devices/zz_test_*.toml` into the live tree" — Enforced by `tests_scripts/test_test_sh.py`. · related:
  SCR.T14 · [H12]
- **SCR.N165** RISK · `SPECIFICATION.md:2758-2764` — "removes its own file in `finally`, which a SIGKILL
  ... defeats ... A leaked one ... aborts that script, `scripts/typecheck.sh` and both twin runners
  outright" — Test writes into the live tree; mitigated by an up-front sweep. · covered-by: TEST.T13 ·
  [H12]

## SPECIFICATION.md Part E.3 / E.3.1 (Running; heap and timeouts, 2828-2921)

- **SCR.N166** INVAR · `SPECIFICATION.md:2864-2866` — "Never write the verdict to
  `$GITHUB_STEP_SUMMARY`" — Pinned by `tests_scripts/test_test_sh.py`. · [H12]
- **SCR.N167** SETTLED · `SPECIFICATION.md:2892-2896` — "`PER_FILE_TIMEOUT_S` (default 240) plus two
  retries is a standing backstop" — Keep even after hangs are fixed. · [H12]
- **SCR.N168** ASSUME · `SPECIFICATION.md:2900-2907` — "Per-file overrides exist but the table is empty
  ... 114.8s/59.5s ... Re-measure and re-add an entry if a future device pushes one past the default." —
  Dated timings; manual re-measure trigger. · [H12]
- **SCR.N169** LIMIT · `SPECIFICATION.md:2920-2921` — "`--coverage` has its own runner and says so out
  loud when both are given, rather than silently ignoring the threshold" — Coverage run never applies
  `GC_THRESHOLD`. · [H12]

## SPECIFICATION.md Part E.5 / E.5.1-E.5.3 (Coverage, 2951-3088)

- **SCR.N170** LIMIT · `SPECIFICATION.md:3053-3060` — "The build directory's path no longer identifies
  its variant ... locally, `scripts/test.sh` asks the binary itself" — Only test.sh probes; other
  runners check `-x`. · covered-by: SCR.S05 · [H12]
- **SCR.N171** SETTLED · `SPECIFICATION.md:3067-3088` — "`scripts/test.sh` now exits: 0 / 1 / 3 ... the
  owner's decision of 2026-09-22 chose this split" — Exit-code contract; renderer `|| coverage_render_failed=1`
  guards. · covered-by: SCR.T01 · [H12]
- **SCR.N172** SUPPRESS · `SPECIFICATION.md:3084` — "Both `_render_coverage.py` invocations are `|| coverage_render_failed=1`-guarded"
  — Deliberate failure capture (exit 3 tolerated in CI). · [H12]

## SPECIFICATION.md Part E.9 (Driver/DUT process separation, 3364-3421)

- **SCR.N173** WORKAROUND · `SPECIFICATION.md:3403-3417` — "`_mem_trend()` ... now derives the tolerance
  from each attempt's own observed noise ... `_run_11_soak()` also retries once" — CI-noise workaround
  (autocorrelated samples); retry only on the trend check. Removal trigger none stated. · [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **SCR.N174** LIMIT · `SPECIFICATION.md:3550-3553` — "`scripts/build_firmware.py`'s type-checking strip
  removes every comment ... an on-device traceback's line numbers won't match checked-in `src/`" —
  Shipped code differs from reviewed/tested text; tracebacks need re-derivation. · related: SCR.T10 ·
  [H13]

## SPECIFICATION.md Part F.5.5 — Stub defects repaired at install

- **SCR.N175** WORKAROUND · `SPECIFICATION.md:3801-3812` — "`stdlib/_asyncio.pyi` privatised `Future` to
  `_Future` and `stdlib/asyncio/futures.pyi` ... was dropped from the wheel" — Stub repair in
  `scripts/typecheck.sh`; removal trigger: guarded, no-ops "once upstream re-ships". · covered-by:
  PLAT.T05 · [H13]
- **SCR.N176** WORKAROUND · `SPECIFICATION.md:3813-3816` — "**`NotImplemented` is commented out** of
  `stdlib/builtins.pyi`" — Second stub repair; same removal trigger. · covered-by: PLAT.T05 · [H13]
- **SCR.N177** SETTLED · `SPECIFICATION.md:3818-3821` — "Repairing the stubs is deliberate, and
  preferred over `type: ignore` comments in `src/`/`digital_twin/`" — Do-not-replace-with-ignores rule
  (dup of CLAUDE.md). · related: DOC.T14 · [H13]

## SPECIFICATION.md Part I.4 — Multi-stage memory-error scheme, (a)-(e)

- **SCR.N178** INVAR · `SPECIFICATION.md:5010-5014` — "`scripts/test.sh` (added 2026-09-22, having been
  the gap) searches each test file's own captured output and fails the run ... checked on a passing file
  too" — Enforced gate; plan lists processes outside the four gates. · related: TEST.T18 · [H13]

## SPECIFICATION.md Part K.10-K.11 — Verification and certification

- **SCR.N179** ASSUME · `SPECIFICATION.md:5935-5939` — "`scripts/run_digital_twin_ci.sh <device>` ...
  already runs the whole suite **twice**, once at `gc.threshold(-1)` and once at the shipped
  `gc.threshold(32768)`" — Claim about the twin runner's two passes. · related: TEST.T18 · [H13]

## CLAUDE.md

- **SCR.N180** INVAR · `CLAUDE.md:116-118` — "`src/` and `ext/` are copied flat into one directory and
  frozen together" — The flat merge requires that no module name collides across `src/` and `ext/`.
  Convention only (low). · related: GEN.T05 · [H14]
- **SCR.N181** INVAR · `CLAUDE.md:501-513` — "Scope is eight directories" — ruff scope matches
  (scripts/lint.sh:13); mypy split across three passes. · covered-by: SCR.T02 · [H14]
- **SCR.N182** DRIFT · `CLAUDE.md:522-531` — excluded list names only
  `digital_twin/machine|network|neopixel|launch|run_generic_integration|segfault_stress_repro` and
  `tests/test_digital_twin_*` — pyproject.toml:389-393 also excludes
  tests/_webserver_concurrency_scenarios.py and tests/_digital_twin_construction_scenarios.py (low). ·
  related: SCR.T15 · [H14] ⟨quote not matched at the anchor⟩
- **SCR.N183** SUPPRESS · `CLAUDE.md:520-531 (pyproject.toml:376-394)` — "are therefore excluded from
  the main `[tool.mypy]` pass and checked correctly by the dedicated pass instead" — Main-pass mypy
  excludes for the twin fakes, runners and twin tests. · related: SCR.T15 · [H14]
- **SCR.N184** MIRROR · `CLAUDE.md:516-531, 551-555` — "`digital_twin/typecheck.ini` ...
  `host_typecheck.ini`'s dedicated mypy pass" — Three mypy configs whose strictness is "synced by hand
  (INI has no include)" (digital_twin/typecheck.ini:23). · covered-by: SCR.T15 · [H14]
- **SCR.N185** LIMIT · `CLAUDE.md:544-548` — "launches first but backgrounds ... including the
  `devices/*.toml` ordering constraint that concurrency creates" — The backgrounded pytest tier mutates
  the tree (devices/zz_test_*) while the MicroPython tier runs. · related: SCR.T06, TEST.T13 · [H14]
- **SCR.N186** DRIFT · `CLAUDE.md:556-557` — "`tests_scripts/`, `scripts/` and `toolchain/` carry the
  same `per-file-ignores` block `tests/` does." — Only `tests_scripts/**` carries it (plus S603), and
  `tests_hardware/**` too (pyproject.toml:223-229). `scripts/` and `toolchain/` have only single-file
  S603 entries (:314-323). · [H14]
- **SCR.N187** SETTLED · `CLAUDE.md:572-575` — "don't re-diagnose a long-lived toolchain dir rebuilding
  its Unix ports once as a bug" — test.sh probes `hasattr(sys, "settrace")` (scripts/test.sh:97). Other
  runners check only `-x`. · related: TOOL.T07, SCR.S05 · [H14]
- **SCR.N188** INVAR · `CLAUDE.md:601-604` — "hanging tests are never allowed ... keep all three even
  after a specific hang is fixed" — Per-file timeout plus retry and stdbuf (scripts/test.sh:311-379),
  and the `needs:` edge. · related: TEST.T16 · [H14]
- **SCR.N189** SETTLED · `CLAUDE.md:696-708` — "don't raise it as the fix, which that history is a
  standing example against" — `-X heapsize=16M` (scripts/test.sh:369) is a Unix-port-only harness
  setting. · related: DOC.T14 · [H14]
- **SCR.N190** WORKAROUND · `CLAUDE.md:709-717` — "`scripts/test.sh` exports `TZ=UTC` before invoking
  the Unix-port binary" — The Unix port uses host libc `mktime()` (scripts/test.sh:23). "Don't diagnose
  a consistent ... failure ... before checking the runner's `$TZ`". Removal trigger: none (host-only). ·
  related: TWIN.T09 · [H14]
- **SCR.N191** INVAR · `CLAUDE.md:805-820` — "Keep this isolation if you touch the stub setup — it's
  load-bearing" — Stubs go into `typings/`, not a dependency group. The version is derived from
  versions.toml `ref` as `==X.Y.Z.*`, so post-releases float. · related: SCR.T15, CI.T04 · [H14]
- **SCR.N192** LIMIT · `CLAUDE.md:811-813` — "failing with a clear, actionable error ... if ... no
  matching stub release exists upstream yet (stub releases can lag)" — A pin move can block typechecking
  until stubs are published (scripts/typecheck.sh:67-77). · related: TOOL.T12 · [H14]
- **SCR.N193** WORKAROUND · `CLAUDE.md:841-854` — "`scripts/typecheck.sh` repairs two verified defects
  in the MicroPython stub package after installing it" — `futures.pyi` and `NotImplemented` in
  micropython-stdlib-stubs 1.29.0.post1/.post2 (scripts/typecheck.sh:83-96). Removal trigger:
  conditional no-op once upstream re-ships. "don't replace them with `type: ignore`". Accounted for "all
  26" findings. · covered-by: PLAT.T05 · [H14]

## README.md

- **SCR.N194** INVAR · `README.md:120-122` — "Needs Python 3.11+ (`tomllib` ...) — `uv sync` enforces
  this automatically via `pyproject.toml`'s `requires-python`" — Enforced by pyproject.toml:11. Host
  CPython is otherwise unpinned (no `.python-version`). · related: SCR.T09 · [H14] ⟨quote not matched at
  the anchor⟩
- **SCR.N195** INVAR · `README.md:137-155` — "six environment variables tune it" — Defaults match
  scripts/test.sh: PER_FILE_TIMEOUT_S 240 (:314), TESTS_SCRIPTS_TIMEOUT_S 1200 (:238), parallelism
  4x/2x/1x at ≤250/≤900 ms (:181-201), GC_THRESHOLD int32 validation (:46-55). · covered-by: SCR.T01 ·
  [H14]
- **SCR.N196** ASSUME · `README.md:144-145` — "(the bench Pi4 probes at ~139 ms: 4x, 16 jobs, green)" —
  Single measurement. · [H14]
- **SCR.N197** MIRROR · `README.md:150-152` — "`GC_THRESHOLD=32768 scripts/test.sh` is the value the
  firmware's boot entry ships" — Mirror between the generated boot entry's `gc.threshold(32768)`,
  test.sh and the twin's default (digital_twin/run_generic_integration.py:39). · covered-by: SCR.S10 ·
  [H14]
- **SCR.N198** INVAR · `README.md:158-164` — "any file whose output contained a `MemoryError` or the
  interpreter's own `memory allocation failed` wording — caught-and-logged counts, and fails the run" —
  Enforced by scripts/test.sh:321-329. · related: TEST.T18 · [H14]
- **SCR.N199** SUPPRESS · `README.md:290-294` — "see `tests_scripts/test_build_firmware.py`'s
  `RUN_SLOW_FIRMWARE_BUILD=1` opt-in" — The real compile is skipif-gated locally
  (tests_scripts/test_build_firmware.py:198-199) and runs only in CI's `firmware-build-verify`. ·
  covered-by: SCR.T13 · [H14]
- **SCR.N200** INVAR · `README.md:414-422` — "a plain skip (hardware unreachable) is treated as a
  failure here, not a silent pass" — Enforced by scripts/_require_clean_hardware_run.sh (skip
  whitelist). Deselected gates stay invisible (CLAUDE.md:260-263). · covered-by: SCR.T05 (related
  HW.T13) · [H14]

## BACKLOG.md

- **SCR.N201** MIRROR · `BACKLOG.md:302-305` — "the CI suite derives _RESET_ERRORS_TIMEOUT_S from a
  mirrored _SERVER_OUTER_CAP_S" — Hand-mirrored cap (`scripts/_digital_twin_ci_suite.py:111` "keep in
  sync"); enforced by `tests_scripts/test_request_timeout_ceiling.py`. · related: GEN.T06 · [H15]
- **SCR.N202** WORKAROUND · `BACKLOG.md:679-688` — "construct a bare machine.Timer(), which is valid
  runtime usage the third-party board stub does not model" — Standalone mypy over `device_scripts/`
  reports 2 false findings; gates pass only because `tests/machine.py` wins resolution. Removal trigger:
  none stated. · covered-by: TEST.T19 · [H15]
- **SCR.N203** TODO · `BACKLOG.md:454-457` — "scripts/test.sh (+520 lines - parallelism autodetection,
  the backgrounded tests_scripts/ job and its timeout, the heap-size and port-base moves)" — Also
  `typecheck.sh`, `lint.sh`, `build_firmware.py`, `_require_clean_hardware_run.sh`,
  `run_digital_twin_ci.sh`, `run_unix_port_integration.sh`. · [H15]
- **SCR.N204** TODO · `BACKLOG.md:458-460` — "scripts/_digital_twin_ci_suite.py (test orchestration only
  - no build step" — 2026-09-22 widened the `MemoryError` check. · [H15]
- **SCR.N205** TODO · `BACKLOG.md:492-498` — "the MemoryError gate matches memory allocation failed as
  well as the class name" — Plus argument/`GC_THRESHOLD` validation moved before the sweeps;
  out-of-range message text. · related: SCR.T01 · [H15]
- **SCR.N206** TODO · `BACKLOG.md:502-504` — "the two _render_coverage.py calls are ||-guarded and the
  verdict block maps a renderer-only failure onto exit 3" — · related: SCR.T01 · [H15]
- **SCR.N207** TODO · `BACKLOG.md:505-511` — "go through an apt_update() helper that tolerates their own
  failure" — `setup_cross_browser_toolchain.sh`; the chroot recipe never runs it. · related: CI.S06 ·
  [H15]
- **SCR.N208** TODO · `BACKLOG.md:526-531` — "_digital_twin_ci_suite.py's Run 11b (full-ceiling burst
  per SPECIFICATION.md Part E.9" — Plus `test.sh` GitHub annotations. · related: SCR.T01 · [H15]
- **SCR.N209** TODO · `BACKLOG.md:535-538` — "html_stub/ is retired, so build_frozen_html.sh now
  requires HTML_SRC_DIRS" — `test.sh` builds the real wozi site; variant probe imports `asyncio`. ·
  [H15]

## Commit messages (chronological)

- **SCR.N210** TODO · `commit 4e5c77e` — "running under the project's real MicroPython Unix-port test
  runner currently needs a scripts/test.sh fix (MICROPYPATH dropping frozen modules like asyncio) that's
  a separate, pending change" — Pending test.sh MICROPYPATH fix. · status: done (tests run under Unix
  port since; low) | - · [H17]
- **SCR.N211** TODO · `commit 577940b` — "mpy-cross does not eliminate if TYPE_CHECKING: blocks ...
  (~3.6KB ...) so it's directly actionable when the firmware build script is built" — TYPE_CHECKING
  stripping. · status: done (scripts/build_firmware.py:30-56 strip_type_checking_blocks;
  SPECIFICATION.md:964-965) | - · [H17]
- **SCR.N212** ASSUME · `commit 6a91514 → 7079757` — "Widen the errcount wait to 90s and the DNS wait to
  90s (from 30s)" — Run 7 budgets were widened on a disproven timing hypothesis (real cause:
  CAP_NET_BIND_SERVICE) and remain at 90 s (scripts/_digital_twin_ci_suite.py:958,968). · status:
  UNTRACKED (low; budgets never narrowed back) | related: SCR.T* · [H17]
- **SCR.N213** INVAR · `commit 9b5b7df` — "build_website.sh's html/ and js/ staging lists are hand-kept,
  not derived from directory contents ... Added a drift-detection test" — Staging list vs directory
  contents; enforced by a tests_scripts drift test. · tracked: tests_scripts drift test (per commit) | -
  · [H17]
- **SCR.N214** INVAR · `commit c3278d5 / da5be43` — "pytest's own exit code can't distinguish
  \"everything passed\" from \"hardware was unreachable and everything skipped\" ... hard-fails on any
  unexpected skip (one documented permanent exception)" — Clean-run guard with a whitelist of opt-in
  skips; deselected tests are invisible to it (CLAUDE.md). · tracked:
  scripts/_require_clean_hardware_run.sh, CLAUDE.md wear rule | related: SCR.T*, HW.T* · [H17]
- **SCR.N215** LIMIT · `commit d967013` — "scripts/build_firmware.py's comment-stripping side effect
  (ast.unparse() drops every comment ... explains why on-device traceback line numbers never match src/
  1:1)" — Field tracebacks cannot be mapped to src/ lines directly. · tracked: SPECIFICATION Part F.1 |
  related: SCR.T* · [H17]
- **SCR.N216** SETTLED · `commit 770cf13 / e5474ab` — "The 4 legacy build-*.sh carry all 28 findings
  (including no shebang at all) and stay out of scope alongside python//modules/" — Legacy scripts
  excluded from shellcheck. · tracked: CLAUDE.md legacy-tree rule | - · [H17]
- **SCR.N217** LIMIT · `commit 7c400bc` — "Run 4 has the same root cause but is left alone deliberately:
  resolving it means changing either the `fram:write:500` budget or Run 3's shutdown condition" —
  Host-speed assumption left in Run 4. · status: later reworked (scripts/_digital_twin_ci_suite.py:703
  notes "the host-speed assumption that made the old Run 4 flaky") — likely done (low) | related: SCR.T*
  · [H17]
- **SCR.N218** NOTE(KNOWN-GAP) · `commit c486553` — "One known remaining gap, deliberately not closed
  here: scripts/build_website.sh's buildgen-fallback branch has no test for a devices/*.toml that exists
  but fails buildgen.definitions" — Test gap. · status: done-in 7e446f9 | - · [H17]
- **SCR.N219** NOTE(RACE-FIX) · `commit 5506f44 / 09c77e2 / d370413` — devices/zz_test_*.toml live-tree
  fixture races with the devices/*.toml glob; fixed by ordering, reserved namespace, session-start
  reclamation — Test writes into the live tree by necessity. · status: done (by construction, d370413) |
  - · [H17]
- **SCR.N220** NOTE(LEFT-STANDING) · `commit 9cfb3b3 / ca5275a / b4cda1a` —
  "scripts/mpremote_connect.sh's hardcoded ttyACM0, which owes the two-chroot pre-push gate" — One entry
  point still strandable by re-enumeration. · tracked: tests_hardware/README.md:62 (documented,
  workaround MPREMOTE_DEVICE); no BACKLOG entry and the chroot gate is no longer blocking (owner,
  2026-09-18) so the stated blocker is gone | related: SCR.T* · [H17]
