# A-C merge SCR (HEAD 263cd06)

Scope: CLUSTERS.md "## SCR" — the 39 `scripts/` files listed there (16 at HEAD, 23 created by actions), plus the new files
actions name beside them: `scripts/_twin_process.py`, `scripts/_cross_browser_probe.mjs` and the CPython lock reader
`scripts/_port_lock.py`. `git diff c4b6bf6 263cd06 -- scripts/` is empty, so every action's `scripts/` line citation holds
at this HEAD. Inputs read: every action whose Site, Change or Blast names one of these files (308 action IDs, from
`site_index.json` plus a slot-aware grep of `audit/actions/*.md`), AC_NOTES 1-40, the finished merges' gaps naming SCR
(M_GEN 1, M_SRC_NET 3, M_TEST_HELP GAP-H2, M_TWIN "SCR", M_WEB 6, M_HW_BENCH GAP-B6) and the end states of M_TWIN
(runner flags M.TWIN.051, paths M.TWIN.060), M_HW_BENCH (options M.HW_BENCH.001, image record M.HW_BENCH.060, evidence
M.HW_BENCH.055, twin board M.HW_BENCH.091), M_WEB (`package.json` M.WEB.071), M_GEN (M.GEN.019), M_SRC_CORE
(M.SRC_CORE.015/.016). In-progress TEST_UNIT/HW_DEV/TSC/TOOL: no gap naming SCR at this HEAD.
GEN Q1/Q2 are answered (a) (OR131, OR132; AC_NOTES 41) and written as firm; the one SCR site they touch is
`build_firmware.py`'s staging, which freezes named modules only, so `ext/typings/microdot/` (OR131) is never staged
(M.SCR.066, holds); M_HW_DEV is finished and names no SCR gap.

Conventions used below (each defined once, then cited):
- **Shell convention** (A.U27.33): `#!/usr/bin/env bash`; `set -euo pipefail` (the one exception states its reason in
  place); `cd "$(dirname "${BASH_SOURCE[0]}")/.."`; `-h`/`--help` checked first, usage to stdout, exit 0, no side effect
  (A.U7.19); a usage or argument error exits 2 with the usage line on stderr (E.10, A.U7.02); every variable and array
  expansion quoted (`"${arr[@]}"`, `while IFS= read -r` instead of `for x in $(…)`); one `EXIT` trap, armed before the
  first temporary resource is created (variables initialised empty first); device arguments through `require_device`
  (`_devices.sh`). Header ≤ 3 prose lines (CLAUDE.md cap, shell included since 2026-09-22).
- **Python script convention**: header docstring ≤ 3 lines; `def main(argv: list[str] | None = None) -> int`, ending
  `raise SystemExit(main())` (A.U27.29); errors print `error: <what> - <where> - fix: <how>` to stderr and return
  nonzero, never a traceback (OR23.a (3)); no explicit `Any` (A.U27.27); no `from __future__ import annotations`
  (A.U20.33); imports at module top (A.U28.28); stdlib only unless a `uv run` PEP 723 block pins its dependency exactly.
- **Summary block**: SPEC E.10 (A.U7.02), emitted through `_summary_block.sh`/`.py`; exit codes 0 pass, 1 failed, 2
  usage, 3 `test.sh` coverage-render-only (E.5.3), 4 NOT CLEAN.
- **`uv` calls**: runners that must not re-resolve run `scripts/uv_sync_retried.sh` once, then `uv run --no-sync …`
  (A.U26.75, A.U28.01); `lint.sh`/`typecheck.sh` require the active synced venv (A.U27.26) and call tools directly.

## scripts/_summary_block.sh (new)

### M.SCR.001 Bash emitter of the E.10 summary block
- **From**: A.U7.02 (definition, bash half), A.U7.11/A.U7.03/A.U7.12/A.U7.18 (callers' needs), A.U27.18 (no step summary).
- **Site**: new `scripts/_summary_block.sh` (sourced; refuses to run as a command: `return 0 2>/dev/null || { echo
  "error: source scripts/_summary_block.sh, do not run it" >&2; exit 2; }`).
- **Change**: header (3 lines): "Sourced emitter of the runner summary block (SPECIFICATION.md E.10); its Python twin
  scripts/_summary_block.py prints the same layout byte for byte." Functions: `summary_add <kind> <name> [<detail>]`
  (kind ∈ passed/failed/skipped/deselected/retried/recovered/vacuous; any other kind → stderr error, return 2),
  `summary_unit <unit>` (default `files`), `summary_counts_line <unit> <p> <f> <s> <d> <r> <v> <z>` (an extra
  `Counts (<unit>):` line, used by `test.sh`'s tests line), `summary_levels <text>`, `summary_gc_stage <text>` (line
  omitted when never called), `summary_result_reason <text>` (NOT CLEAN reason), `summary_print <runner> <exit>`: prints
  the E.10 block exactly (header, `Commit:` from `git rev-parse --short HEAD` plus ` (uncommitted changes)` when
  `git status --porcelain` is non-empty, `unknown` outside a work tree), `Result:` PASS only when exit is 0 and
  `failed`/`vacuous` are 0; FAIL for exit 1; `PASS (coverage report not rendered)` for 3; `NOT CLEAN (<reason>)` for 4;
  `USAGE ERROR` for 2. State is kept in shell arrays prefixed `_summary_`. Writes stdout only; the string
  `GITHUB_STEP_SUMMARY` appears nowhere in it.
- **Resolved**: —
- **Unit**: U7.
- **Depends**: —
- **Blast carried by**: byte-equality with the Python emitter and the rules (missing verdict = failed, vacuous → FAIL,
  `Exit code:` line) → L0 `tests_scripts/test_summary_block.py` (A.U7.02, TSC); no-step-summary pin → A.U27.18 (TSC);
  SPEC E.10 text → A.U7.02 doc slot (SPEC); `tests_js/_summary_reporter.js` same layout → A.U7.10 (WEB).
- **Kind**: code

## scripts/_summary_block.py (new)

### M.SCR.002 Python emitter of the summary block, run-record reader
- **From**: A.U7.02 (Python half), A.U7.08 (`--from-run-record`), A.U7.09, A.U7.14, A.U7.17 (callers), A.U27.18.
- **Site**: new `scripts/_summary_block.py`.
- **Change**: Python script convention. `@dataclass class Summary` (`runner: str`, `unit: str = "tests"`, lists per
  kind of `(name, detail)`, `levels: str | None`, `gc_stage: str | None`, `extra_counts: list[tuple[str, Counts]]`,
  `not_clean_reason: str | None`) with `add(kind, name, detail="")`, `render(exit_code) -> str`, `print(exit_code)`;
  `Counts` a frozen dataclass of the seven counters; `from_run_record(path: Path) -> Summary` reads the JSON written by
  `_pytest_run_record.py` (passed/failed/error→failed/skipped with reason/deselected with `by`); a missing or
  unparsable record yields one `failed` item "no verdict (run record missing or unreadable)". CLI:
  `--from-run-record PATH --counts-only` prints `P F S D` (four integers) for `test.sh`'s L0 line, and `--from-run-record
  PATH --list KIND` prints `name<TAB>detail` lines; usage errors exit 2. `render()` output equals the bash emitter's
  for the same input (same `Commit:` derivation through `git`).
- **Resolved**: —
- **Unit**: U7.
- **Depends**: M.SCR.004 (record format).
- **Blast carried by**: L0 `tests_scripts/test_summary_block.py` (A.U7.02, TSC); users M.SCR.005, M.SCR.045, M.SCR.048,
  `tests_hardware/manual/runner.py` (A.U7.17, HW_BENCH M.HW_BENCH manual runner entry).
- **Kind**: code

## scripts/_archive_evidence.py (new)

### M.SCR.003 Timestamped evidence archive, last three kept per runner
- **From**: A.U7.20 (helper), A.U27.16 (twin CI runner use), A.U26.22 + GAP-B6 (API use, M.HW_BENCH.055), A.U23.33
  (`--runner live_twin`), A.U27.18 (no step summary).
- **Site**: new `scripts/_archive_evidence.py`.
- **Change**: Python script convention, stdlib only; header "Moves a runner's evidence into
  build/archive/<runner>/<UTC timestamp>/ and keeps the newest three runs per runner (SSD wear; owner, 2026-09-26)."
  API: `new_run_dir(runner: str, *, keep: int = 3, root: Path = REPO_ROOT / "build" / "archive") -> Path` creates
  `<root>/<runner>/<YYYYmmddTHHMMSSZ>/` (a second call in the same second appends `-<n>`) and prunes the oldest
  directories beyond `keep`; `archive(runner, paths, *, keep=3) -> Path | None` moves every existing path into one new
  run dir (created only if at least one path exists; a missing path is skipped silently) and returns it. Runner names
  must match `^[a-z0-9_]+$` and `keep >= 1` (else `ValueError`, CLI exit 2). Nothing outside `<root>/<runner>/` is ever
  deleted; pruning only removes directories whose name parses as the timestamp form. CLI: `--runner NAME [--keep N]
  [--new-dir] [PATH ...]` — with `--new-dir` prints the created directory (for the hardware wrapper); else archives the
  paths and prints the directory or nothing. Import has no side effect (the namespace import
  `scripts._archive_evidence` from the repo root works for `tests_hardware/evidence.py`).
- **Resolved**: A.U26.22 and GAP-B6 need a programmatic directory API ("created once per process through
  `scripts/_archive_evidence.py`'s API") where A.U7.20 defines only the CLI — both kept, the CLI wrapping the API.
- **Unit**: U7.
- **Depends**: —
- **Blast carried by**: callers `test.sh` (M.SCR.044), `run_digital_twin_ci.sh` (M.SCR.061), hardware wrapper (M.SCR.034),
  `package.json` `pretest:coverage` `--runner npm_coverage htmlcov_js` (M.WEB.071, WEB), `tests_hardware/evidence.py`
  (M.HW_BENCH.055), JS live `archiveErrcount` `--runner live_twin` (A.U23.33, WEB); L0
  `tests_scripts/test_archive_evidence.py` (four archivings keep three; nothing outside `build/archive/<runner>`
  touched; missing path ignored; `--new-dir` prints an existing empty dir) → A.U7.20 (TSC); SPEC E.1 "Evidence archive"
  and E.5 → A.U7.20 doc slot (SPEC); `.gitignore` `build/` already ignored (no change).
- **Kind**: code

## scripts/_pytest_run_record.py (new)

### M.SCR.004 Pytest plugin writing one JSON run record
- **From**: A.U7.08, A.U7.13 (hardware use, `add_session_note`), A.U27.19 (effective `-m` recorded).
- **Site**: new `scripts/_pytest_run_record.py`.
- **Change**: as A.U7.08: option `--run-record=PATH`; per test `nodeid`, `outcome` (passed/failed/skipped/error),
  `when`, skip `reason`, marker names, report `user_properties`; collection-time skips/errors (`pytest_collectreport`);
  deselected nodeids with `by` = first `("deselected_by", flag)` in `item.user_properties` else `"runner selection"`
  (`pytest_deselected`); `options` = JSON-safe `vars(config.option)`; `markexpr` (the effective `-m`, A.U27.19);
  `collect_only` bool; `session_notes` from module function `add_session_note(config, text, *, recovery=False,
  source="")`; written in `pytest_sessionfinish` via tmp + `os.replace`. No explicit `Any`: values typed through a
  `JSONValue` alias.
- **Resolved**: —
- **Unit**: U7.
- **Depends**: —
- **Blast carried by**: users `test.sh` (M.SCR.038), hardware wrapper (M.SCR.034), `tests_hardware/conftest.py`
  `record_session_note()` (A.U7.13, HW_BENCH); L0 `tests_scripts/test_pytest_run_record.py` → A.U7.08 (TSC); SPEC E.1
  pytest-tier text → A.U7.08 doc slot (SPEC).
- **Kind**: code

## scripts/_hardware_verdict.py (new)

### M.SCR.005 The hardware verdict from the run record
- **From**: A.U7.14, A.U0.35 (permanent-skip comment, moved here from the bash whitelist), A.U26.74/A.U26.35/A.U26.14
  (marker and option names in force, M.HW_BENCH.001/.002), A.U7.13 (notes), A.U7.18 (`--levels`), A.U27.19.
- **Site**: new `scripts/_hardware_verdict.py`.
- **Change**: CLI `--run-record PATH --pytest-exit N --runner NAME --levels TEXT [--not-clean-reason TEXT]`, rules
  (a)-(g) of A.U7.14 with the end-state names: the gate map `{"flash_cycle": "allow_flash_cycle",
  "soak_duration": "soak_duration", "multi_day_rollover": "allow_multi_day_rollover", "neopixel_sweep":
  "allow_neopixel_sweep", "toolchain_reverify": "allow_toolchain_reverify"}` (`persistence_write`/`scd30_extra_write`
  deselect, they never skip, so they appear only in the deselection list with their flags `--allow-persistence-write`
  / `--allow-scd30-extra-write`); the one permanent skip
  `tests_hardware/bench/test_hotspot_role_reversal.py::test_spoofed_off_subnet_source_address_is_ignored` beside the
  comment "# A real rogue-NTP spoof needs an off-subnet host the bench lacks (owner, 2026-09-26; attempted on the bench
  first)." (A.U0.35's text, kept as long as the phase-C attempt (A.U26.56 (3)) has not removed the skip — C delta); the
  advice line names only the flags of the wear-gate deselections present; `recovered` and notes from `user_properties`
  and `session_notes`; `--collect-only` → `Result: NOT A RUN (collection only)`, exit 0; a nonzero pytest exit
  propagates unchanged; zero passed → FAIL; `--not-clean-reason` → NOT CLEAN, exit 4 when the run itself passed
  (A.U7.18). Prints the block through `Summary` (unit **tests**).
- **Resolved**: A.U7.14 names `long_soak`/`soak_tier`/`allow_multi_day_rollover_wait`; A.U26.35/A.U26.74 rename them
  later and A.U27.19 states "the names in force when this lands" — the end state uses the new names (M.HW_BENCH.001).
  `toolchain_reverify` joins the map (A.U26.14 (4), M.HW_BENCH.001's option list).
- **Unit**: U26 (the names; first written U7 with today's names, stage below).
  Stage U7: A.U7.14 with HEAD's names. Stage U26: the renames of A.U26.35/.74 and the `toolchain_reverify` entry
  (needed by M.HW_BENCH.001's option set).
- **Depends**: M.SCR.002, M.SCR.004.
- **Blast carried by**: L0 `tests_scripts/test_hardware_verdict.py` (A.U7.14's cases plus `toolchain_reverify`
  unset → accepted skip, set → fail) and `test_require_clean_hardware_run_sh.py` rewritten → A.U7.14/A.U26.74 (TSC);
  README hardware-verdict text, `tests_hardware/README.md` → A.U7.02 doc slot / M.HW_BENCH.126 (DOCS, HW_BENCH).
- **Kind**: code

## scripts/_run_lower_levels.sh (new)

### M.SCR.006 Lower levels first, on a recorded commit
- **From**: A.U7.18, A.C.01 (4) (procedure: a reported round never skips), A.U27.08 (`derived_devices`), A.U27.16 (the
  twin runner archives its own logs), A.U7.01 (E.6.1 ladder), A.U35.02 (`npm` web legs).
- **Site**: new `scripts/_run_lower_levels.sh <L3|L4>` (shell convention).
- **Change**: records `git rev-parse HEAD` and the dirty flag (printed, and exported as `LOWER_LEVELS_COMMIT` /
  `LOWER_LEVELS_DIRTY` for the caller's block); then in order, stopping at the first failure with exit 1 and no
  hardware touched: `scripts/test.sh`, `GC_THRESHOLD=32768 scripts/test.sh`, `npm test`, and `scripts/run_digital_twin_ci.sh
  "$d"` for each `d` of `derived_devices` (each runs both GC stages and the harness itself). Sequential only (CLAUDE.md
  port rule; each callee takes its own port locks, M.SCR.012). Prints one line per step with its exit code; the
  argument must be `L3` or `L4` (else exit 2).
- **Resolved**: —
- **Unit**: U7 (stage U7 runs `run_digital_twin_ci.sh "$device"` over `devices/*.toml` minus `zz_test_` inline; stage U27
  replaces that with `_devices.sh`'s `derived_devices`, A.U27.08).
- **Depends**: M.SCR.007 (U27 stage), M.SCR.045 (the test.sh exit codes it reads).
- **Blast carried by**: callers M.SCR.030/.031; L0 `tests_scripts/test_hardware_runners.py` (stubbed callees: order,
  stop at first failure, no wrapper call after a failure) → A.U7.18 (TSC); SPEC E.6.1 containment text → A.U7.01 (SPEC).
- **Kind**: code

## scripts/_devices.sh (new)

### M.SCR.007 One derived device list for every shell runner
- **From**: A.U27.08 (1), A.U27.33 (3) (`require_device` everywhere), A.U27.38 (test.sh harness jobs), A.U27.39 (row).
- **Site**: new `scripts/_devices.sh` (sourced).
- **Change**: `derived_devices` prints the sorted stems of `devices/*.toml` without the `zz_test_` prefix, one per
  line, and fails ("error: no devices/*.toml found") if none; `require_device NAME` exits 2 with "error: no
  devices/NAME.toml - valid devices: <space-joined derived list>" when `NAME` is empty, starts with `zz_test_`, or has
  no TOML. Header ≤ 3 lines naming `tests_scripts/_devices.py` as the Python statement of the same rule.
- **Resolved**: —
- **Unit**: U27.
- **Depends**: —
- **Blast carried by**: users M.SCR.006, .020, .039, .041, .061, .062, .071; L0 `tests_scripts/test_devices_sh.py`
  (equality with `tests_scripts/_devices.py`; unknown and `zz_test_` names exit 2) → A.U27.08 (TSC); A.U6.15's
  variant-literal allow-list shrinks → A.U6.15 (TSC).
- **Kind**: code

## scripts/_unix_port.sh (new)

### M.SCR.008 One Unix-port probe, by build flavour, with the record check
- **From**: A.U27.12, A.U27.15 (2) (`micropypath`), A.U21.22 (missing toolchain record = missing binary), A.U21.12
  (third flavour `lwip`), A.U28.04 (CI body `ensure standard`), A.U36.512 (term "build flavour").
- **Site**: new `scripts/_unix_port.sh` (sourced, and callable as a command).
- **Change**: as A.U27.12 (1)/(4): `unix_port_bin <standard|settrace|lwip>`; `unix_port_flavour <bin>` printing
  `standard`/`settrace`/`lwip`/`unusable`; `unix_port_ensure <flavour>` — missing binary, wrong flavour, or no toolchain
  record (A.U21.03's record absent, A.U21.22 (b)) → `uv run toolchain/setup_toolchain.py setup` (`SKIP_APT` passed
  through; the installer takes the toolchain lock, so a concurrent build fails fast with its message), re-probe, exit 1
  naming the found flavour; `micropypath <unit|twin>` reads `scripts/micropypath.toml` with `sed` over its two
  `key = "…"` lines. Command forms `check <flavour>`, `ensure <flavour>`, `micropypath <unit|twin>`, `unix_port_bin
  <flavour>` (unknown command or flavour → exit 2). `PICO_TOOLCHAIN_DIR` (default `$HOME/pico-toolchain`) is read only
  here.
- **Resolved**: A.U27.12 lists `micropypath` as A.U27.15's addition and `unix_port_bin` as a command form only through
  HW_BENCH's use (M.HW_BENCH.091 "`scripts/_unix_port.sh unix_port_bin standard`") — both command forms kept.
- **Unit**: U27.
- **Depends**: M.SCR.009; A.U21.12 (the `lwip` build exists, TOOL), A.U21.03 (record path, TOOL).
- **Blast carried by**: users M.SCR.036 (test.sh), .061, .062, .064 (smoke), .016/.017 (suite and harness via `_twin_process.py`), .022;
  `tests_scripts/conftest.py` `micropython_bin` (`check standard`), `tests_js/_live_*_command.js` / `_twin_process.js`
  (`execFileSync`), CI's build-if-missing steps (A.U28.04, TOOL), `tests_hardware/twin_board.py` (M.HW_BENCH.091); L0
  `tests_scripts/test_unix_port_sh.py` and retargeted `test_test_sh.py:384-440`, `test_coverage_runner.py:27` →
  A.U27.12 (TSC).
- **Kind**: code

## scripts/micropypath.toml (new)

### M.SCR.009 The two Unix-port MICROPYPATH layouts, once
- **From**: A.U27.15 (1), M_TWIN gap "SCR" (`digital_twin/unixport`, M.TWIN.017/.047/.053/.060), A.U28.33 (the
  `.gitignore` sentence — LEAD gap below).
- **Site**: new `scripts/micropypath.toml`.
- **Change**: header (3 lines): "# The Unix-port MICROPYPATH layouts, read by every launcher (scripts/_unix_port.sh,
  tomllib, tests_js/_micropypath.js). # unit has no ext/: a unit file exercising vendored Microdot inserts it itself
  (grep sys.path.insert(0, "ext")). # A derived launcher swaps frozen_modules for build/generated_html/<device> and says
  why." Then exactly `unit = "build/generated_src:src:tests:frozen_modules:.frozen"` and `twin =
  "build/generated_src:src:digital_twin:digital_twin/unixport:ext:frozen_modules:.frozen"`.
- **Resolved**: A.U27.15's twin value lacks `digital_twin/unixport`; M.TWIN.060 (later, the twin's end state) adds it —
  M.TWIN's value kept.
- **Unit**: U27 (the `unixport` element exists from U25, M.TWIN.017; the file is born in U27 with the U25 value).
- **Depends**: M.TWIN.017; M.TWIN.060 [follows] (its README names this file in U36).
- **Blast carried by**: readers M.SCR.008, .016 (suite and harness), .036, .062, .064, .022, `tests_js/_micropypath.js` and
  `tests_js/_twin_process.js` (A.U27.15/M.WEB.082, WEB), `tests_scripts/test_coverage_runner.py`,
  `test_digital_twin_boot_contiguity.py`, `test_digital_twin_generated_boot.py` (A.U27.15, TSC),
  `tests_hardware/twin_board.py` (M.HW_BENCH.091); L0 check that no other file holds either literal (A.U27.15, TSC);
  `digital_twin/README.md` copies → A.U27.15 docs slot (TWIN/DOCS); `.gitignore` sentence → M.PROC.019 (PROC carries
  `.gitignore`, M_PROC gap 7; gap pass).
- **Kind**: code

## scripts/_require_python.sh (new)

### M.SCR.010 One Python-version check before a bare `python3`
- **From**: A.U27.10, A.U28.01 (2) (composite action calls it), A.U28.43 (row).
- **Site**: new `scripts/_require_python.sh` (sourced).
- **Change**: `require_python311` as A.U27.10: `python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else
  1)'` else "error: <calling script> needs python3 >= 3.11 (tomllib, datetime.UTC) - the python3 on PATH is <X.Y>; fix:
  activate the uv venv (uv sync) or put a newer python3 first on PATH", return 1 (the caller's `set -e` exits).
- **Resolved**: —
- **Unit**: U27.
- **Depends**: —
- **Blast carried by**: callers `lint.sh` (M.SCR.024), `typecheck.sh` (M.SCR.026), `build_website.sh` (M.SCR.071),
  `build_frozen_html.sh` (M.SCR.072), `ci.yml`/composite action (A.U27.10/A.U28.01, TOOL); `pyproject.toml:8-11` comment
  → A.U27.10 (TOOL); L0 `tests_scripts/test_require_python.py` (stub `python3` reporting 3.10 → exit 1 with the
  message) → A.U27.10 (TSC); BACKLOG chroot entry → A.U27.10 (DOCS).
- **Kind**: code

## scripts/_require_venv.sh (new)

### M.SCR.011 Lint and typecheck refuse an inactive or stale venv
- **From**: A.U27.26.
- **Site**: new `scripts/_require_venv.sh` (sourced).
- **Change**: `require_project_venv` as A.U27.26: unless `VIRTUAL_ENV` resolves to `<repo>/.venv` → "error: activate
  the project venv first (uv sync && source .venv/bin/activate), or run through uv run", return 1; then `uv sync
  --locked --check --offline` must succeed, else "error: the venv does not match uv.lock - run uv sync".
- **Resolved**: —
- **Unit**: U27.
- **Depends**: —
- **Blast carried by**: callers M.SCR.024, M.SCR.026; L0 `tests_scripts/test_require_venv_sh.py` → A.U27.26 (TSC);
  CI `lint-and-typecheck` activates the venv before both (A.U28.01, TOOL).
- **Kind**: code

## scripts/_port_lock.sh (new)

### M.SCR.012 One lock per product-fixed port, inherited by children
- **From**: A.U24.69, A.U27.39 (callers).
- **Site**: new `scripts/_port_lock.sh` (sourced).
- **Change**: `port_lock_take <port> <runner>`: lock directory `${XDG_RUNTIME_DIR:-/tmp}/sensors-port-<port>.lock/`
  with files `pid` and `runner`; `mkdir` succeeds → record `$$` and the runner, append the port to the exported
  `SENSORS_PORT_LOCKS_HELD` (space list) and export `SENSORS_PORT_LOCK_OWNER=$$`; `mkdir` fails → if the recorded pid is
  alive (`kill -0`) and is neither `$$` nor the exported `SENSORS_PORT_LOCK_OWNER` of an ancestor that holds this port
  (port listed in the inherited `SENSORS_PORT_LOCKS_HELD`), exit 1 with "port <n> is held by <runner> (pid <p>) - run
  the suites one after the other (CLAUDE.md)"; a held lock of our own owner chain is accepted without retaking; a dead
  pid's lock is taken over (stale). `port_lock_release_all` removes only directories whose `pid` equals `$$`; called
  from the runner's one EXIT trap. Takers: `test.sh` (53), `run_digital_twin_ci.sh` (53, 18080), `run_unix_port_integration.sh` (53).
- **Resolved**: a runner calling another runner (`_run_lower_levels.sh` → `test.sh`; `run_digital_twin_ci.sh` → the
  harness) would refuse itself; inheritance through the exported owner pid settles it without weakening the lock across
  unrelated suites (agent decision AD-1; OR38.a (3) "one tier at a time").
- **Unit**: U24 (A.U24.69).
- **Depends**: —
- **Blast carried by**: CPython reader M.SCR.013; JS twin `tests_js/_port_lock.js` same directory, pid and env contract
  (A.U24.69/A.U27.39, WEB); L0 `tests_scripts/test_port_lock.py` (held by a live pid → exit 1 with the message; dead pid
  taken over; child of the owner accepted; release removes only own locks) → A.U24.69 (TSC); CLAUDE.md "two suites"
  bullet → A.U24.69 doc slot (DOCS).
- **Kind**: code

## scripts/_port_lock.py (new)

### M.SCR.013 The same port lock for the CPython harness and suite
- **From**: A.U27.39 ("a CPython reader of the same lock directory, a shared helper beside `scripts/_twin_process.py`"),
  A.U24.69.
- **Site**: new `scripts/_port_lock.py`.
- **Change**: `@contextlib.contextmanager def port_lock(port: int, runner: str) -> Iterator[None]` with the exact
  contract of M.SCR.012 (directory, `pid`/`runner` files, inherited `SENSORS_PORT_LOCK_OWNER`/`SENSORS_PORT_LOCKS_HELD`,
  stale takeover via `os.kill(pid, 0)`); a held lock raises `PortHeldError` whose message is M.SCR.012's text; the
  caller turns it into exit 1. Release in `finally` removes only its own directory. Python script convention (library:
  no `main`).
- **Resolved**: A.U27.39 does not name the file; `scripts/_port_lock.py` is the name (agent decision AD-2).
- **Unit**: U27.
- **Depends**: M.SCR.012.
- **Blast carried by**: users M.SCR.017 (harness: 53 for its whole run, 18080 when a scenario binds it), M.SCR.048
  (suite); L0 cases in `tests_scripts/test_port_lock.py` (bash and Python agree on one lock) → A.U27.39 (TSC).
- **Kind**: code

## scripts/uv_sync_retried.sh (new)

### M.SCR.014 One retried `uv sync --locked`
- **From**: A.U28.01 (1), A.U26.75 (callers), A.U8.14 (tags), A.U28.10/.37/.38 (doc texts naming it, blast).
- **Site**: new `scripts/uv_sync_retried.sh`.
- **Change**: shell convention; header (3 lines) as A.U28.01: "`uv sync --locked`, three attempts with 10 s and 20 s
  pauses: a third party's build-time download (actionlint-py fetches its binary) must not read as a red run (owner,
  2026-09-26). The one retry definition CI and the hardware runners share." Body: `# @tunable tool.uv_sync_attempts =
  3` `attempts=3`, `# @tunable tool.uv_sync_backoff_step_s = 10` `step=10`; loop `uv sync --locked "$@"`; between
  attempts `sleep $((step * n))` and "uv sync failed (attempt n/3) - retrying in <s> s" on stderr; after the last,
  "error: uv sync --locked failed 3 times - read the uv output above before any test output", exit 1.
- **Resolved**: —
- **Unit**: U28.
- **Depends**: —
- **Blast carried by**: callers M.SCR.029, .033, .034, the composite actions (A.U28.01, TOOL); L0
  `tests_scripts/test_uv_sync_retried_sh.py` (stub `uv` failing twice → 3 calls, pauses 10/20 via a stub `sleep`) →
  A.U28.01 (TSC); CLAUDE.md retry bullet → A.U28.10 (DOCS); SPEC B.10 → A.U28.37 (SPEC); BACKLOG list → A.U28.38 (DOCS);
  Part N rows → A.U8.14/A.U28.01 (SPEC).
- **Kind**: code

## scripts/_check_gc_collect_sites.py (new)

### M.SCR.015 One AST checker for `gc.collect()` and `gc.threshold()` sites
- **From**: A.U27.21 (checker), A.U30.14 (threshold confinement), A.U30.16 (tests/twin/hardware baseline rows), A.U30.17
  (doc names the file), A.U11.10/A.U10.37 (superseded site/message edits of the old greps), M.SRC_CORE.015/.016 (src
  sites), M.GEN (no generated site), M.TWIN.1608-1629 (sampler row, conditional), M.TWIN unwedge retirement.
- **Site**: new `scripts/_check_gc_collect_sites.py`.
- **Change**: Python script convention, stdlib only (run as `python3 scripts/_check_gc_collect_sites.py` after
  `require_python311`). Per module of `src/`, `buildgen/`, `build/generated_src/`, `tests/`, `digital_twin/`,
  `tests_hardware/`: resolves every name bound to `gc` (`import gc`, `import gc as g`) and to `gc.collect` /
  `gc.threshold` / `gc.disable` / `gc.enable` (`from gc import …`, aliases) and records each call with its enclosing
  function (`module`, `qualname`). Allowance table (module constant, one row per site, each with its one-line reason):
  `gc.collect` — `src/asy_system_service.py` `SystemService.start_tasks` and `SystemService.run_setups` (the
  boot-confined placement reset, SPEC I.4(f.1)); nothing in `buildgen/` or `build/generated_src/`; the tests/twin/
  hardware rows A.U30.16 lists by category (baseline, boot mirror, before a timed window, twin exception, measured
  collection pause), each function re-checked against its category at landing (the `digital_twin/unix_port_gc_unwedge.py`
  row absent — the file is retired, M.TWIN; the twin's `_mem_sampler` row present only while A.U35.25 keeps its
  collection); plus, from U31, the **measured collection pause** row `tests_hardware/device_scripts/loop_stretch_timing.py`
  (its timing function), reason "times gc.collect() itself: the pause SPECIFICATION.md F.3 bounds" (OR39.a (2), OR91.a
  (9); M.HW_DEV.122). `gc.threshold` — exactly one module-level `gc.threshold(<int literal>)` in each generated boot entry
  (`sensortask_<device>_main.py` and `_main_noautostart.py`), plus A.U30.14's callers `tests/_threshold_runner.py`,
  `tests/microtest.py`, `digital_twin/run_generic_integration.py`, `digital_twin/run_device_script.py` (M.TWIN, new),
  and `tests_hardware/device_scripts/*`; `gc.disable`/`gc.enable` nowhere. A finding prints `path:line: <call> in
  <qualname> is not an allowed site (SPECIFICATION.md I.4(e)/(f.1))`; exit 1 on any finding, 2 on a parse error
  naming the file.
- **Resolved**: A.U11.10 and A.U10.37 rewrite `lint.sh`'s grep path/message (`system_service.py` →
  `asy_system_service.py`); A.U27.21 removes those greps — the rename lands only as this table's module name (dropped
  as separate edits). The generated module carries no `gc.collect()` (M.SRC_CORE.015 moves it into `run_setups`), so
  A.U27.21's "codegen's emitted boot batch" row is not written.
- **Unit**: U31 (the measured-collection-pause row lands with `loop_stretch_timing.py`, M.HW_DEV.122; AC3_O O-27).
  Stage U27: A.U27.21's checker with the sites then in force. Stage U30: A.U30.14/.16 extend it — threshold rows and the
  test/twin/hardware rows.
- **Depends**: M.SCR.010; M.SRC_CORE.015/.016.
- **Blast carried by**: caller `lint.sh` (M.SCR.025); `tests_scripts/test_gc_collect_sites.py` rewritten to call the
  checker on fixture trees (alias forms, threshold forms) → A.U27.21/A.U30.14/A.U30.16 (TSC); CLAUDE.md memory rule and
  SPEC I.4(e)/(f.1), E.9 name the file → A.U30.17 (DOCS, SPEC); CI runs it through `lint.sh`/the pytest tier (A.U28.43
  row, TOOL).
- **Kind**: code

## scripts/_twin_process.py (new)

### M.SCR.016 Shared twin-process helpers for the suite and the harness
- **From**: A.U25.46 (helpers move: `_spawn`/`_shutdown`/`_wait_until_serving`/`_wait_exit`/`_read_log`/`_http`/errcount
  readers), A.U27.01 (`_TwinRun`, fail closed), A.U25.64 (signal deaths), A.U25.36 (exit codes 3/4/5), A.U35.38/.39
  dropped (OR140.a (13): the twin gets a local NTP responder instead of a log tolerance, A-C review fold), A.U27.27
  (types), A.U27.37 (ceiling lookup import), A.U25.38 (polls), A.U27.39 (lock import).
- **Site**: new `scripts/_twin_process.py`.
- **Change**: Python script convention (library). `@dataclass class TwinRun` (proc, `log_path: Path`, `log_file`,
  `device`, `state_dir`), replacing `proc.ci_log_file` and its `type: ignore`; `spawn(device, *, micropython_bin,
  wiring_plan, port, state_dir, fram_state_path, scd30_state_path, mem_backup_state_path, config_dir, gc_threshold,
  fault=(), hang=(), wifi_outcome=(), seed=None, duration=None, mem_sample_interval_ms=None, test_flags=(), log_path)
  -> TwinRun` building the runner argv of M.TWIN.051 (`--module --wiring-plan --host --port --device
  --fram-state-path --scd30-state-path --mem-backup-state-path --config-dir --online-ntp --seed --fault --hang
  --wifi-outcome --duration --gc-threshold --mem-sample-interval-ms` plus `--test-…` flags, and the local NTP
  responder the twin runner provides, on by default so a normal boot syncs [fold F16 M_TWIN]) with
  `MICROPYPATH = micropypath("twin")` (tomllib read of `scripts/micropypath.toml`) and `TZ=UTC` (until A.SDEP.16's W15
  check retires it); `wait_until_serving(run, port, timeout_s)` (poll, never sleep-then-assume); `shutdown(run,
  timeout_s) -> int`; `wait_exit(run, timeout_s) -> int`; `read_log(run) -> str` and `log_from(run, offset) -> str`;
  `close_log_and_check_memory_safety(run)` failing closed on a missing, empty or unreadable log (A.U27.01) and on
  either marker of its own `MEMORY_ERROR_MARKERS = ("MemoryError", "memory allocation failed")` (the twin gate's
  copy, kept equal to the other three gates by `tests_scripts/test_memory_error_gate_agreement.py`, CLAUDE.md four-gate
  rule; no import from `tests_hardware/`); `exit_reason(code) -> str` naming 3 reset, 4 bootloader, 5 power loss and `-N` "killed by signal <name>"
  (A.U25.64); `http(method, port, path, body=None, timeout_s=…) -> tuple[int, JSONValue]`; errcount readers
  `errcount_entries(status) -> list[ErrcountEntry]`; `parse_shutdown_line(log)` for `… shutdown:
  would_have_triggered_count=<n> feed_count=<n> mem_backup: r0=<4 words> public_destinations_refused=<n>`, plus the
  `uart=<instance>:transfers=<n>,failures=<n>,overruns=<n>;…` field M.TWIN.171 adds (A-C review fold; one dict per
  instance, required when the wiring plan declares a `uart_link`), and
  `parse_machine_reset_line(log)`; no normal-boot tolerance list: with the local NTP responder a normal boot logs no
  E or W entry at all (OR140.a (13)). Types: `JSONValue`,
  `JSONObject`, `ErrcountEntry` (TypedDict); no `Any`.
- **Resolved**: A.U27.01's `_TwinRun` and A.U25.46's move land as one shape here (A.U27.01's Depends names this merge).
- **Unit**: U27 (stages: U25 moves the helpers with A.U25.46 and passes the NTP responder once the twin has it, U27
  adds `TwinRun` fail-closed and types).
- **Depends**: M.SCR.009, M.SCR.013; M.TWIN.051 (flags); [fold F16 M_TWIN] (the twin's local NTP responder, U25);
  M.TWIN.171 (the `uart=` field, U25).
- **Blast carried by**: users M.SCR.046-.060 (suite), M.SCR.017/.018 (harness); `tests_scripts/test_digital_twin_generated_boot.py`
  checks a normal boot with no tolerance → M.TSC.086 (amended); `tests_scripts/test_memory_error_gate_agreement.py`
  counts this module as the twin gate's site → A.U27.01 (TSC); L0 `tests_scripts/test_digital_twin_ci_suite_*.py` move
  their helper imports → A.U25.46 (TSC); the tolerance constant's readers go → M.TSC.086, M.TSC.165.
- **Kind**: code

## scripts/_digital_twin_scenarios.py (new)

### M.SCR.017 Host-side L2 scenario harness: mechanism, CLI, selection
- **From**: A.U25.46 (1)/(4) (mechanism), A.U25.74 (scenarios move onto the `--test-…` flags), A.U27.38 (runner
  contract: `--device --micropython-bin --logs-dir`, GC stage forwarded), A.U27.39 (port-53 lock), A.U24.70 (port band),
  A.U25.48 (device from data), A.U35.57 (BACKLOG text names it, blast), A.U8.02 (tags).
- **Site**: new `scripts/_digital_twin_scenarios.py`.
- **Change**: Python script convention; header (3 lines): "Host-side L2 scenarios: each boots the device's generated
  graph in the twin (digital_twin/run_generic_integration.py) and drives it from this CPython process over HTTP, the
  runner's stdout lines and its named --test- flags only - no request is built inside the DUT heap." CLI: `--device
  NAME` (required; `require`-checked against the derived set), `--micropython-bin PATH`, `--logs-dir DIR`,
  `--gc-threshold N` (default -1; forwarded to every twin it boots), `--only NAME[,NAME…]`, `--exclusive-port-53` /
  `--shared-port-53` (default shared: scenarios marked `needs_exclusive_port_53` are deselected with reason "needs
  exclusive port 53 - run_digital_twin_ci.sh runs it"), `--run-record PATH` (JSON per scenario: name, outcome, reason,
  for `test.sh`'s collector). Registry: `@scenario(name, *, drivers=(), needs_exclusive_port_53=False,
  needs_site=False)`; a scenario whose `drivers` the device's wiring plan does not wire is skipped with "device wires
  no <driver>" (a named skip, counted), never silently. Each scenario boots its own twin through `_twin_process.spawn()`
  with fresh state under `<logs-dir>/<scenario>/state/`, `MICROPYPATH` = the twin layout with `frozen_modules` replaced
  by `build/generated_html/<device>` (the device's own built site; missing → the scenario fails naming
  `scripts/build_device_websites.sh`), ports from the harness's band (`tests/_port_bands.py` row, A.U24.70; each device a fixed sub-range by its index in
  the derived list, so per-device jobs running in parallel never share a port), and is
  shut down in `finally`; its log is checked by `close_log_and_check_memory_safety()` and for
  `public_destinations_refused=0` (A.U25.35). Fixed ports: when a scenario binds 53 (every boot does, the captive DNS) the
  harness holds `_port_lock.port_lock(53, "digital_twin_scenarios")` for its whole run — inherited when a runner above
  already holds it (M.SCR.012) — and 18080 likewise if a scenario binds it. Scenarios run one twin at a time. Exit 0 all
  passed or skipped-by-rule, 1 any failure, 2 usage; prints the E.10 block (unit **scenarios**, `Levels: L2 (<device>)`,
  `GC stage: <n>`).
- **Resolved**: A.U24.65 (a generic `PER_DEVICE` concurrency file) vs A.U25.46 (wrappers go, harness derives the device
  set) — A.U25.46 kept, as both name (M.TEST_HELP.033). Port 53 under `test.sh`: `test.sh` runs per-device harness jobs
  in parallel with in-process twin files that also bind 53 (`SO_REUSEADDR`), so a DNS answer cannot be attributed to one
  twin; the DNS-querying scenarios therefore run only under `run_digital_twin_ci.sh` (exclusive lock, one twin at a
  time) and are listed as deselected by `test.sh` — agent decision AD-3 (reported, never silent: OR21.a (3)).
- **Unit**: U27 (wired by A.U27.38; file born U25 by A.U25.46, scenarios added U31/U35/S0930).
- **Depends**: M.SCR.016, M.SCR.013, M.SCR.009, M.SCR.002; M.TWIN.051 (flags); `tests/_port_bands.py` (A.U24.70, TEST_HELP).
- **Blast carried by**: callers M.SCR.041 (test.sh jobs), M.SCR.061 (twin CI runner); L0
  `tests_scripts/test_digital_twin_scenarios.py` (registry: every scenario has a goal docstring line and a known
  device filter; `--only` unknown → exit 2; no scenario imports from `tests/`) → A.U25.46 (TSC); `test_twin_runner_test_flags.py`
  gains `--test-fault-status-interval-ms` → M_TWIN gap (TSC); SPEC E.9 (runner-only exception), E.2.1/H.7.1 citers →
  A.U25.74/A.U36.532 (SPEC); BACKLOG build-environment paragraph → A.U35.57 (DOCS); `.gitignore` logs dir under
  `digital_twin_ci_logs/` already ignored.
- **Kind**: test

### M.SCR.018 Harness content: every moved and new L2 scenario
- **From**: A.U25.46 (2) inventory; M.TEST_HELP GAP-H2 (with A.U24.47, A.U0.29, A.U20.28, A.U25.31, A.U24.34, A.U24.36,
  A.U19.20, A.U24.37, A.U8C.04, A.U8C2.01, A.U8.18, A.U0.28, A.U0.35, A.U19.21, A.U5.05, A.U25.45, A.U30.15, A.U36.004,
  A.U36.544, A.U14.28, A.U35.29); M_TWIN "SCR" gap (M.TWIN.144's 8 tests with A.U10.36, A.U25.33, A.U10.40, A.U10.11,
  A.U2.13, A.U9.09, A.U22.03 (withdrawn: AC_NOTES 37 — its comment edit drops), A.U19.03, A.U18.01, A.U18.03, A.U25.72,
  A.U10.15, A.S0930.27; M.TWIN.136's 9 website tests with A.U24.60, A.U8.18, A.U25.48; M.TWIN.102's API burst);
  A.U24.47 (`FAULT_PENDING`), A.U35.31 (three `--test-watchdog-fault` cases), A.U35.09 (two recombinations), A.U35.28
  (fault storm rides Run 3; non-rebooting bounded cell here), A.U35.29 (zero-think readers), A.U31.06 (loop lag),
  A.S0930.27 (2)/(4) and A.S0930.38 (3)/(4) (command states, hang per step); gap pass (GAPS_G3 hand-off 3, Table B
  B21): A.U19.07, A.U19.08/.10, A.U19.12 (their L2 cases, whose in-DUT carrier was retired), A.U35.28 (h)'s read of the
  per-logger `fram_writes_by=` field (2 × rate × window per logger; sum ≤ `fram_writes=`; `fram_writes_unattributed` > 0
  fails) (lead ruling; M.TWIN.011/.050 as G3 amends them); OR141.a (4) (g), OR143.a (4) (A-C review fold: (m), the host
  side of M.TWIN.170/.171's concurrent-load scenario).
- **Site**: `scripts/_digital_twin_scenarios.py` (the registry).
- **Change**: the registry holds, each with its source goal and assertions kept (OR19.a (4)): (a) the 22
  webserver-concurrency helpers/scenarios of `tests/_webserver_concurrency_scenarios.py` rewritten host-side
  (M.TEST_HELP.033): refusals classified as `CeilingRefusedError`-equivalent (a refused or reset connection, A.U25.31's
  rule) per A.U24.34's per-site rule; served bodies compared with an uncontended answer; the route set from
  `build/generated_src/api/<device>.json` (A.U19.20); the concurrent config write PUTs `/networking {"GMTOffset": 3600 +
  60*(i+1)}` (A.U24.37); slot counts through `--test-conn-status-interval-ms` `CONN_SLOTS` lines, the stalled burst
  through `--test-stall-loop-ms`, the closing slot through `--test-hold-closing-slot`; tags `web.connections_per_page_load`
  (A.U8.18) and A.U8C.04/A.U8C2.01's; owner tags of `:482` (A.U0.28), `:753` (A.U0.35), OpenHAB (A.U19.21);
  `_DEFAULT_OUTER_CAP_S`/`_DEFAULT_MAX_CONTENT_LENGTH` names (A.U5.05); readiness by polling (A.U25.45); the A.7 citation
  (A.U36.004) and A.U36.544's C.8 `config_lock` sentence; A.U14.28's F.7 row 1 text. (b) The 8 HTTP tests of
  M.TWIN.144 (M_TWIN Blast list), incl. the DNS answer (QTYPE A, 512-byte reply, source check) and captive redirect —
  `needs_exclusive_port_53=True` — and mempause asserting `MemPaused` true only; a host-side
  `assert_sensor_payload_not_self_wrapped` equivalent. (c) The 9 real-website tests (M.TWIN.136), `needs_site=True`,
  definitions read strictly (A.U24.60), the page-load connection figure tagged. (d) The bus-hazard API burst at the
  ceiling (M.TWIN.102, every GET route). (e) `bus_fault_degrades` per A.U24.47: sustained fault armed by `--fault`,
  consumption proven by `--test-fault-status-interval-ms` `FAULT_PENDING` lines reaching 0 before the GET, SGP40 fields
  `null`, SGP40 error count ≥ 1, "(owner, 2026-08-13)" tag (A.U0.29), addresses through `fixed_address()` (A.U20.28);
  and `measurements_and_sensors_shape` (A.U25.46 (2)). (f) `watchdog_fault_<case>` for `supervisor-raise`, `main-exit`,
  `block` (A.U35.31: `WDT_AT_FAULT <feed_count>` read; `would_have_triggered_count >= 1`; `feed_count` equality for the
  first two only). (g) A.U35.09 (a) `survives_bus_and_api_load_while_ntp_is_unreachable` (PUT `/networking {"NTPHost":
  "192.0.2.1"}` — the key A.U10.40 renames — then reboot) and (b) `…_with_concurrent_config_writes`. (h) A.U35.28's
  bounded-count storm below the escalation threshold (no reboot; per-module FRAM write count ≤ 2 × `rate.persisted_log`
  × window — one counted write is one landed copy write and a persisted entry writes both copies (M.TWIN.011/.050) —
  read from the shutdown line's `fram_writes_by=<LOGGER>:<n>,…` field (one entry per FRAM-backed logger that wrote,
  sorted by name; `-` when none wrote, a pass), each failing entry named with its count and the bound; cross-check: the
  entries' sum ≤ the line's `fram_writes=<total>`, which also counts non-logger writes (the SGP40 backup, clears, erase
  units); a `fram_writes_unattributed=<n>` field with n > 0 fails the scenario naming that field (the per-logger proof is
  incomplete); a missing `fram_writes_by` field fails, never skips. Lead ruling, gap pass: a check is never weakened to
  fit what a line carries — the twin line gains the fields, G3's M.TWIN.011/.050 amendment, GAPS_G3 row 96). (i) A.U35.29 `zero_think_time_readers_saturate_then_recover`. (j) A.U31.06
  `loop_lag_under_combined_load` (`--test-loop-lag-ms 10`, `LOOP_LAG` lines; bound from the device TOML). (k) The
  command states and hangs: A.S0930.27 (2) (`erasefram`/`resetconfig` in the timer-start window, during a delayed FRAM
  write `--hang fram:…`, with `mempause`, concurrent with `reboot`, both at once; lost-chip refusal vs `silent` chip;
  10 s of feeding after a refusal), A.S0930.27 (4) and A.S0930.38 (4) hang per step through `--test-shutdown-hang
  S1|S2|S3|S4|S5reset|S5erase|S6` (wait 8.5 s past `HANG <step>`, `would_have_triggered_count >= 1`, `feed_count`
  unchanged since the hang, no reset exit), A.S0930.38 (3)'s states (`reboot`+`bootloader` at once → exactly one Valid;
  reboot in the boot window; `mempause` then `reboot`). FRAM evidence first before every `erasefram` (GET `/status`
  errcount into the scenario's dir plus a copy of its `--fram-state-path`, A.S0930.27 (0)). No `gc.collect()` anywhere
  (A.U30.15); polls, not sleeps, except a hang's 8.5 s watchdog window, which is the property under test (tagged).
  (l) Webserver cases (gap pass, GAPS_G3 hand-off 3 (a)): `negative_content_length_is_refused` (A.U19.07: a raw socket
  sends `PUT /networking` with `Content-Length: -1` and a 3,000 B body; the answer is a 400, the log holds no allocation
  marker, and a following `GET /status` serves); `refusal_at_the_ceiling_is_counted` (A.U19.08/.10: `/status`
  `HTTPDropped` read, the ceiling filled with held connections from the one route table's limit, one further connection
  refused as A.U25.31 classifies it, the holders released, then `HTTPDropped` read again equals the first read plus the
  refusals the harness counted — one per forced refusal; exact because `HTTPDropped` sums the last 24 hours in hourly
  bins (OR137.a) and a scenario's twin has run far less than 23 hours, so no bin ages out between the reads); `isl29125_config_put_during_get_loops` (A.U19.12,
  `drivers=("isl29125",)`: `GET /sensors` loops on three connections while one `PUT /sensors` changes the ISL29125
  `Resolution`; every GET's ISL29125 block equals either the before or the after configuration, never a mix, and the
  PUT answers `Valid`). (m) The UART DMA ring under concurrent load (A-C review fold, OR141.a (4) (g), OR143.a (4); the
  host side of M.TWIN.170/.171): `uart_ring_under_concurrent_load`, run on every device whose wiring plan declares a
  `uart_link` pair (a device without one skips by name), launched twice — the twin's flash-write stall at its typical
  and at its maximum times (M.TWIN.170's runner flag) — at the harness's GC stage (the suite runs it at both); for the
  scenario's window the harness drives, concurrently: the webserver hammer (the ceiling-filling readers of (i)), config
  PUTs at a steady rate that each change a stored value (each a flash write, so each a stall), and a sustained
  FRAM-log fault through `--fault` (persisted writes), while both link instances exercise (the twin's exerciser,
  including its maximum-size and over-cap trains as M.TWIN.171 provides them); the verdict reads the shutdown line's
  `uart=` field (M.TWIN.171) and `/status`: no link failure and no overrun for every stall within the ring's bound,
  each over-cap train refused and logged exactly once, every config PUT answered, zero `MemoryError` and `memory
  allocation failed` in the run log (the twin gate), the largest free block at the end not below the boot-contiguity
  bound (read from `tests_scripts/test_digital_twin_boot_contiguity.py` by `ast`).
- **Resolved**: A.U22.03's `:377` comment edit dropped — A.U22.03 withdrawn (AC_NOTES 37). The in-process halves of
  A.S0930.27 (3)/(4)/(5) and A.S0930.38 (5) (wire-time knob, late-feed backstop, power loss) are TWIN's (M.TWIN.104) — no
  runner flag sets `wire_time_us_per_byte`, settled by M.TWIN.051's flag list.
- **Unit**: U35 (stages: U25 (a)-(e) and (l) with A.U25.46/.74 — (l)'s product side lands in U19, before the harness
  exists; U25 (m) with M.TWIN.170/.171; U31 (j); U35 (f)-(i); S0930's (k) lands with A.S0930.27/.38 after U25 — each
  scenario lands in the unit of its constituent).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.27 in U25, A.S0930.38 in U25.
- **Depends**: M.SCR.017; M.TWIN.051/.104/.136/.144; M.TWIN.050 (`fram_writes=` and `fram_writes_by=` on the shutdown
  line, G3's gap-pass amendment); A.U19.20 (route reference), A.U24.70 (band); M.TWIN.170, M.TWIN.171 ((m): the stall,
  the DUT side and the `uart=` field), M.SCR.016 (its `uart=` parse).
- **Blast carried by**: the deleted in-DUT files → M.TEST_HELP.033, M.TWIN.136, M.TWIN.144 (TEST_HELP, TWIN); Part N rows
  for the harness's tags → A.U8.02/A.U8C (SPEC); `audit/b3/load.md` entries → A.U35.28/.29 (procedure); SPEC H.7.1/C.8
  citers repoint → A.U36.532/A.U36.544 (SPEC).
- **Kind**: test

## scripts/_stage_website.py (new)

### M.SCR.019 The website stager: derived bundle, drift rule, favicon
- **From**: A.U23.38, A.U23.39, A.U27.35 (work-dir rule applies to its output dir), A.U36.517 (SPEC text, blast).
- **Site**: new `scripts/_stage_website.py`.
- **Change**: as A.U23.38 (1)-(5) and the bootstrap id/key check, CLI `scripts/_stage_website.py <definitions.json>
  <stage_dir>` (CPython, stdlib only, Python script convention); the bundle keeps HEAD's layout after the derived banner:
  per module in the derived order, one blank line, then `// ---- js/<file> ----`, then the module body with its import
  lines removed (`build_website.sh:78-81` today; M.TEST_UNIT.333 reads both banner and separators — M_TEST_UNIT GAP-U11,
  gap pass); plus A.U23.39: the exact tag `<link rel="icon"
  href="favicon.ico">` in `html/index.html` is replaced in the staged copy by a `data:image/x-icon;base64,…` URI of
  `html/favicon.ico`, the tag missing → error naming `html/index.html`. The stager writes only inside `<stage_dir>` and
  creates it if absent; the caller owns wiping it (A.U27.35).
- **Resolved**: M_WEB gap 6(b) asks for the `--stage-only` command: it is `build_website.sh`'s mode (M.SCR.071), not
  the stager's — the stager has one mode (it never builds definitions) — agent decision AD-4, stated to WEB in Gaps.
- **Unit**: U23.
- **Depends**: A.U6.04 (hand definitions deleted, so the drift rule passes); A.U23.07 (module closure).
- **Blast carried by**: caller M.SCR.071; L0 `tests_scripts/test_stage_website.py` (A.U23.38/.39 cases) → A.U23.38/.39
  (TSC); `tests/test_website_build_integration.py` reads the banner → A.U23.38 (TEST_UNIT); SPEC H.2/H.7 → A.U36.517
  (SPEC); A.U8.18's two connections per page load → M.SCR.063.
- **Kind**: code

## scripts/build_device_websites.sh (new)

### M.SCR.020 Build, or stage, every derived device's site
- **From**: A.U6.03 (2), A.U23.38 (`lint:html:built` stage-only), A.U27.08/.33 (devices, convention), A.U36.517 (blast).
- **Site**: new `scripts/build_device_websites.sh [--stage-only] [out_root]`.
- **Change**: shell convention; for each `d` of `derived_devices`: default mode runs `scripts/build_website.sh "$d"
  "$out_root/$d/frozen_html.py"` (default `out_root` = `build/generated_html`); `--stage-only` runs `scripts/build_website.sh
  --stage-only "$d" "$out_root/$d"` (default `out_root` = `build/staged_html`). Stops at the first failure naming the
  device.
- **Resolved**: —
- **Unit**: U23 (stage U6: A.U6.03's build loop; stage U23: `--stage-only`, needed by `package.json` `lint:html:built`,
  M.WEB.071).
- **Depends**: M.SCR.007 (U27 stage replaces the inline glob), M.SCR.071.
- **Blast carried by**: callers `package.json` `build:site`/`lint:html:built` (M.WEB.071, WEB), `test.sh` (M.SCR.039),
  CI web jobs (A.U6.12/A.U28.43, TOOL); L0 `tests_scripts/test_build_device_websites_sh.py` (stubbed `build_website.sh`:
  one call per derived device, `zz_test_` skipped, both modes) → A.U6.03 (TSC).
- **Kind**: code

## scripts/preview_server.py (new)

### M.SCR.021 `npm run preview` serves only the site, on localhost
- **From**: A.U28.24, A.U28.38 (BACKLOG text, blast), A.U28.43 (row).
- **Site**: new `scripts/preview_server.py`.
- **Change**: as A.U28.24 (header as written there; `SimpleHTTPRequestHandler` subclass restricted to the paths the
  page loads — `html/`, `js/`, `mockdata/`, `build/generated_src/definitions/` (M.WEB.070's four directories) — bound
  to `127.0.0.1`, `--port` (default as A.U28.24), a taken port → exit 1 naming `--port`). Run through `uv run`
  (`package.json` `"preview": "uv run scripts/preview_server.py"`), so no bare `python3` and no version check.
- **Resolved**: AC_NOTES 38 "A.U28.24's bare python3 preview script meets G8/R05's version check (decide at merge)" —
  settled by M.WEB.071 (runs through `uv run`).
- **Unit**: U28.
- **Depends**: —
- **Blast carried by**: `package.json` (M.WEB.071); L0 `tests_scripts/test_preview_server.py` → A.U28.24 (TSC); README
  `:224, :237`, SPEC `:4307, :4323, :4744` → A.U28.24 docs slot / A.U36.517 (DOCS, SPEC); BACKLOG list → A.U28.38.
- **Kind**: code

## scripts/record_twin_instrument_runs.py (new)

### M.SCR.022 Record every hardware instrument's twin run
- **From**: A.U26.05 (4), A.U35.49 (every instrument, both GC stages), A.U27.12/.15 (probe, path; A.U27.39 row).
- **Site**: new `scripts/record_twin_instrument_runs.py`.
- **Change**: as A.U26.05 (4): runs `uv run --no-sync pytest tests_hardware/flash --twin` and every
  `tests_hardware/device_scripts/*.py` not run by a flash test through `TwinBoard.run_isolated()`, at `gc_threshold=-1`
  and `32768` each (A.U35.49), and writes `tests_hardware/twin_record.json` (per path `sha256`, `runner_sha256`, per stage
  outcome, or the named reason a script cannot run in the twin) via tmp + `os.replace`. The binary comes from
  `scripts/_unix_port.sh check standard` (exit 1 with its message if absent; never builds), `MICROPYPATH` from
  `micropypath.toml`'s twin entry (through `TwinBoard`, M.HW_BENCH.091). Python script convention.
- **Resolved**: —
- **Unit**: U35 (stage U26 one stage; U35 adds the second stage and the full instrument set).
- **Depends**: M.SCR.008, M.SCR.009; M.HW_BENCH.091 (`TwinBoard`), M.TWIN `run_device_script.py`.
- **Blast carried by**: `tests_scripts/test_twin_record.py` (hashes current) → A.U26.05 (TSC); `tests_hardware/README.md`
  habit 5 → M.HW_BENCH README entry (HW_BENCH); twin README section → A.U26.05 (TWIN).
- **Kind**: code

## scripts/_cross_browser_probe.mjs (new)

### M.SCR.023 Probe-field picker and engine verdict, testable without browsers
- **From**: A.U6.11 (`pickProbe`), A.U28.17 (verdict function), A.U28.25 (`tsconfig.node.json` include).
- **Site**: new `scripts/_cross_browser_probe.mjs`.
- **Change**: ES module, header ≤ 3 lines, JSDoc-typed; `export function pickProbe(definitions)` as A.U6.11 (first
  `@web` int field, not `float`, finite `min`/`max` with `max - min >= 64`, in a `submit` group, definitions order;
  returns `{sectionKey, groupKey, fieldKey, min, max}`; none → throws naming the device); `export function
  engineVerdict(available, results, {requireAllEngines})` as A.U28.17 (missing engine → `FAIL` result with the binary
  path and "CI requires every engine (run scripts/setup_cross_browser_toolchain.sh)" when required, else `SKIP`; returns
  results plus `{passed, ran, skipped}`). No side effects at import.
- **Resolved**: —
- **Unit**: U28 (stage U6: `pickProbe`; stage U28: `engineVerdict`).
- **Depends**: —
- **Blast carried by**: caller M.SCR.063; `tsconfig.node.json` `include` → A.U28.25 (WEB/TOOL); L0
  `tests_scripts/test_cross_browser_smoke_probe.py` (every device yields a probe; none → throws; verdict cases) →
  A.U6.11/A.U28.17 (TSC).
- **Kind**: code

## scripts/lint.sh

### M.SCR.024 `lint.sh`: help, environment checks, summary block
- **From**: A.U7.19 (`--help`), A.U7.11 (block, reject arguments), A.U27.26 (venv first), A.U27.10 (Python check before
  the bare `python3`), A.U27.33 (convention), A.U0.57 (`:4` label), A.U0.06/A.U35.02/A.U37.07 (run as procedure — blast),
  A.SDEP.02 (check gate, blast).
- **Site**: `scripts/lint.sh:1-11`, `:51`.
- **Change**: header (3 lines): "Every non-type lint pass: ruff over the eight scopes plus the generated device modules,
  shellcheck over scripts/, actionlint + zizmor over the workflows, the method-assign guard and the gc-site checker - all
  stay fully clean. `ruff format` is unused (agent, 2026-07-13)." (the venv sentence `:6-7` goes: the check below states
  it). Then `-h`/`--help` → usage ("scripts/lint.sh - no arguments; needs the project venv active (uv sync && source
  .venv/bin/activate)"), exit 0; any other argument → usage on stderr, exit 2. `source scripts/_require_venv.sh;
  require_project_venv`; `source scripts/_require_python.sh; require_python311`; `source scripts/_summary_block.sh;
  summary_unit checks`. Each check below records `passed`/`failed` by name after its block; the end is `summary_print
  "scripts/lint.sh" "$status"; exit "$status"`.
- **Resolved**: —
- **Unit**: U27 (stages: U7 help and block; U27 venv/Python checks; U36's A.U0.57 label is written here, in the header
  rewrite U27 makes — the label text is A.U0.57's).
- **Depends**: M.SCR.001, M.SCR.010, M.SCR.011.
- **Blast carried by**: L0 `tests_scripts/test_lint_sh.py` (block extraction rewritten for `grep_guard`, `--help`,
  argument → exit 2) and `test_tool_help.py` → A.U7.11/A.U7.19/A.U27.20 (TSC); README CLI reference → A.U36.547 (DOCS);
  CI calls `lint.sh`'s tools directly per job (A.U28 jobs keep their own steps, TOOL).
- **Kind**: code

### M.SCR.025 `lint.sh` checks: generated scope, guard that fails closed, one gc checker
- **From**: A.U27.09 (1) (generate, ruff gains `build/generated_src`), A.U28.41 (`--no-respect-gitignore` if ruff skips
  the ignored path), A.U1.21 (`:15-17`), A.U27.20 (`grep_guard`), A.U0.39 (`:29-30` tag), A.U27.21 (gc greps → checker),
  A.U30.14/.16 (checker's scope), A.U10.37/A.U11.10 (superseded), A.U28.14 (zizmor comment text in its own file —
  blast), A.U27.24 (scope pin, blast), A.U33.05 (declined checkers stay out — blast).
- **Site**: `scripts/lint.sh:13-49`.
- **Change**: (1) `uv run --no-sync scripts/_generate_sensortask_modules.py || status=1` (recorded "generation"), then
  `ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts || status=1` and
  `ruff check --no-respect-gitignore build/generated_src || status=1` as two invocations only if a landing run shows ruff
  skips the ignored directory when named (A.U28.41's condition; otherwise one invocation with `build/generated_src`
  appended) — recorded together as "ruff". (2) `:15-17` → "# scripts/ only: the legacy tree (legacy/, its
  legacy/firmware/build-*.sh included) is never in a lint scope (CLAUDE.md legacy rule)." (3) shellcheck, actionlint,
  zizmor lines unchanged (their comments ≤ 3 lines already). (4) `grep_guard <rule> <message> <grep args…>` defined once
  (rc 0 → print hits and message, `status=1`; 1 → clean; ≥ 2 → "error: lint.sh could not search (<args>, grep exit
  <rc>) - the <rule> guard did not look", `status=1`); the method-assign guard → `grep_guard method-assign "error: src/
  must never suppress method-assign - reassigning a method on shipped firmware code is the defect, not the type error."
  -rn "type: ignore\[[^]]*method-assign" src/`, its comment `:28-30` "… tests/ and digital_twin/ legitimately
  monkeypatch methods, shipped src/ never may (owner, 2026-09-10), full reasoning in CLAUDE.md's "Code quality
  tooling"." (5) `:36-49` → `python3 scripts/_check_gc_collect_sites.py || status=1` (recorded "gc sites") with one
  comment line "gc.collect()/gc.threshold() sites: one AST checker, every allowed site named there (SPECIFICATION.md
  I.4(e)/(f.1))."
- **Resolved**: A.U10.37/A.U11.10 edit the grep path and message of `:42-43`, which A.U27.21 deletes — dropped (the
  rename lives in the checker's table, M.SCR.015). A.U0.39 tags `:29-30`; A.U27.20 keeps the comment with that tag —
  combined above.
- **Unit**: U30 (A.U30.14/.16 extend the checker it calls; the `lint.sh` text lands in U27). Stages: U0 (A.U0.39 tag on
  today's comment), U1 (A.U1.21 comment), U27 (generation, ruff scope, `grep_guard`, checker call).
- **Depends**: M.SCR.015; A.U20.14 (generated text clean, GEN), M.SCR.068 (generator `--no-sync` callable).
- **Blast carried by**: CI's ruff step gains `build/generated_src` after a generation step (A.U27.09 (4), TOOL);
  `tests_scripts/test_lint_type_scopes.py` pins the ruff list (A.U27.24, TSC); `pyproject.toml` per-file entries for
  generated modules (A.U28.41, TOOL); `.github/zizmor.yml` header (A.U28.14, TOOL); BACKLOG chroot entry "lint.sh
  generates and lints the device modules; one gc checker" → A.U27.09/A.U27.21 docs slot (DOCS).
- **Kind**: code

## scripts/typecheck.sh

### M.SCR.026 `typecheck.sh`: help, venv and Python checks, summary trap
- **From**: A.U7.19, A.U7.12, A.U27.26, A.U27.10 (the in-heredoc `tomllib` check goes), A.U27.25 (header text), A.U27.33,
  A.U36.534/A.U36.023/A.U21.02/A.U34.11/A.U10.35/A.U25.74 (docs/procedures naming the script — blast).
- **Site**: `scripts/typecheck.sh:1-14`, `:132-134`.
- **Change**: header (3 lines): "mypy in three passes - [tool.mypy]'s files, digital_twin/typecheck.ini,
  host_typecheck.ini - plus two single-file checks; why three: CLAUDE.md "Code quality tooling". Stubs install into
  typings/ at the exact pins of toolchain/versions.toml [stubs] (SPECIFICATION.md B.15)." `--help` (usage: "scripts/
  typecheck.sh [PATH ...] - extra paths narrow the main pass for a local run; CI passes exactly its files
  (tests_scripts/test_lint_type_scopes.py checks)"), exit 0. `source scripts/_require_venv.sh;
  require_project_venv` (mypy then runs from `$VIRTUAL_ENV`), `source scripts/_require_python.sh; require_python311`,
  `source scripts/_summary_block.sh; summary_unit checks`; a variable `stage` set before each step (`stub pins`, `stub
  install`, `stub repairs`, `module generation`, `main pass`, `twin pass`, `host pass`, `network check`, `conftest
  check`); one `EXIT` trap records a failure of the current `stage` when `$?` ≠ 0 and calls `summary_print
  "scripts/typecheck.sh" <code>`; the success path ends `exit 0` explicitly.
- **Resolved**: —
- **Unit**: U27 (stage U7: help and block).
- **Depends**: M.SCR.001, M.SCR.010, M.SCR.011.
- **Blast carried by**: L0 `tests_scripts/test_typecheck_sh.py` (stub `mypy`/`uv`: a failing pass names its stage; help)
  → A.U7.12/A.U27.26 (TSC); CI's mypy step "Mypy (all three passes; typecheck.sh)" → A.U27.25 (TOOL).
- **Kind**: code

### M.SCR.027 Exact stub pins, a recorded install, repairs that fail on a moved tree
- **From**: A.U27.02, A.U21.04, A.SDEP.08 (`:68-79` message names the hold-back choice — kept), A.SDEP.09 (U0
  procedure: install and record post-releases), A.SDEP.15 (repairs retired if fixed upstream — conditional), A.U27.03
  (doc removal triggers, blast), A.SDEP.25 (U37 re-check, procedure); OR140.a (11) (A-C review fold: the stub version
  moves with every MicroPython bump, enforced by this check; decision stub-versions-pinned, owner, 2026-10-02).
- **Site**: `scripts/typecheck.sh:16-97`.
- **Change**: `derive_stub_pins()` (one `python3` heredoc, no in-heredoc version check): reads `[micropython] ref` and
  `[stubs] board`/`stdlib` from `toolchain/versions.toml`, checks each pin against `^X\.Y\.Z(\.post\d+)?$` for the ref's
  `X.Y.Z` (else A.U27.02's error, naming both versions and "move [stubs] with every [micropython] ref change"), prints
  `<board> <stdlib>`. `stub_spec="micropython-rp2-rpi_pico_w-stubs==<board>
  micropython-stdlib-stubs==<stdlib>"`; when `typings/.stub-spec`'s first line differs from it (or is missing) `rm -rf
  typings` first; `uv pip install --quiet --target typings` of both exact pins (the `:68-79` no-release message kept,
  naming the pin that failed); after install exactly one `typings/micropython_rp2_rpi_pico_w_stubs-*.dist-info` and one
  `typings/micropython_stdlib_stubs-*.dist-info` must exist with versions equal to the pins (else "error: typings/ holds
  <found> where versions.toml pins <pin>"); print `== MicroPython stubs: board <v>, stdlib <v> (for firmware <X.Y.Z>)`
  and write `typings/.stub-spec` (line 1 the spec, line 2 the two resolved versions). Repairs as A.U27.02 (3): target
  existence checks with the moved-tree error naming SPECIFICATION.md F.5.5; Future re-export only when `class _Future`
  is in `_asyncio.pyi`; `NotImplemented` three states. Comment `:83-89` → "Two verified stub defects repaired in the stub
  tree, never by `type: ignore` in our code (CLAUDE.md "Code quality tooling"). A fixed upstream makes a repair a no-op;
  a moved tree fails it." Each repair block whose defect A.SDEP.15 finds fixed at the U0 refresh is deleted instead
  (with its F.5.5/CLAUDE.md text, A.SDEP.15).
- **Resolved**: A.U21.04 records the `==X.Y.Z.*` spec and the resolved version; A.U27.02 (later) pins exact versions —
  the spec file holds the exact pins and the resolved check becomes an equality (both kept, A.U27.02's pin wins).
- **Unit**: U27 (stages: U0 A.SDEP.09/.15 procedure — possible repair removal; U21 A.U21.04 spec file and record).
- **Depends**: `toolchain/versions.toml` `[stubs]` table and its `TypedDict` (A.U27.02 (1), A.U21.29, TOOL).
- **Blast carried by**: `versions.toml` `[stubs]` → A.U27.02 (TOOL); L0 `tests_scripts/test_typecheck_sh.py` (fixture
  stub trees: moved tree fails, fixed upstream no-op, spec change wipes `typings/`, two dist-info dirs fail) →
  A.U27.02/A.U21.04 (TSC); SPEC B.15/F.5.5, CLAUDE.md stub bullets → A.U27.03/A.SDEP.15 (SPEC, DOCS); BACKLOG chroot entry
  → A.U27.02 docs slot (DOCS).
- **Kind**: code

### M.SCR.028 Generation, three passes and two single-file checks
- **From**: A.U27.09 (2)-(3) (generated modules as sources; comment), A.U27.25 (comments), A.U27.23 (twin pass from its
  ini; single-file checks), A.U7.12 (pass statuses), A.U26.75 (`--no-sync`), A.U8.24/A.U10.46/A.U17.26/A.U18.44/A.U22.04/
  A.U23.47/A.U34.11/A.U20.33/A.U10.31/A.U6.02 (passes stay green by construction — blast), A.SDEP.08 (`:83` stamp —
  rewritten above).
- **Site**: `scripts/typecheck.sh:99-130`.
- **Change**: `:99-101` → "# The main pass checks the generated device modules and boot entries as sources, and the
  twin pass resolves sensortask_<device> from the same directory, so it is generated first."; `uv run --no-sync
  scripts/_generate_sensortask_modules.py`; `:105-107` → "# Extra args narrow the main pass for a local run; CI passes
  exactly `files` (tests_scripts/test_lint_type_scopes.py checks)."; `mypy "$@"` (main); `mypy --config-file
  digital_twin/typecheck.ini` (its `files` in the ini); `mypy --config-file host_typecheck.ini`; then `mypy
  tests/network.py` and `mypy --config-file host_typecheck.ini tests_scripts/conftest.py`, each failing like the
  passes with its own error line; the comments `:111-116`, `:123-125` kept within the 3-line cap. Exit 1 if any of the
  five failed.
- **Resolved**: —
- **Unit**: U27.
- **Depends**: M.SCR.068; `digital_twin/typecheck.ini` `files` (A.U27.23, TOOL); `pyproject.toml` `files` gains
  `build/generated_src` (A.U27.09 (2), TOOL).
- **Blast carried by**: CI step paths (A.U27.25, TOOL); `test_lint_type_scopes.py` (A.U27.24, TSC); `host_typecheck.ini`
  and `pyproject.toml` comments (A.U27.23, TOOL); SPEC B.10.1/B.15 (A.U27.25, SPEC); `mypy_path` gains `scripts`
  (A.U27.27, TOOL).
- **Kind**: code

## scripts/mpremote_connect.sh

### M.SCR.029 One board resolver, a retried sync, help
- **From**: A.U27.13 (resolver delegation), A.U21.28 (one resolver: vendor `2e8a` plus by-id name), A.U26.75/A.U28.01
  (retried sync, `--no-sync`), A.U7.19, A.U27.33, A.U1.06/A.U36.547/A.SDEP.03 (docs, mpremote pin — blast).
- **Site**: `scripts/mpremote_connect.sh:1-9`.
- **Change**: header (3 lines): "uv run mpremote connect <board> for a real RP2040: `exec`/`run`/`ls`/`cat` stay
  RAM-only; `cp`/`rm`/`mkdir`/`rmdir` write flash. The board comes from $MPREMOTE_DEVICE, else the one board
  toolchain/setup_toolchain.py's resolver finds (vendor 2e8a plus the MicroPython by-id name)." `--help` (usage,
  `MPREMOTE_DEVICE`, "other arguments go to mpremote"), exit 0; `scripts/uv_sync_retried.sh`; `device="${MPREMOTE_DEVICE:-$(uv
  run --no-sync toolchain/setup_toolchain.py board)}"` (the resolver's zero/several-match error propagates, `set -e`:
  its own stderr line, `setup_toolchain: no MicroPython board found …` or the several-match form, reaches the user
  unchanged and the script exits with the resolver's code, printing no message of its own); `uv run --no-sync mpremote
  connect "$device" "$@"`.
- **Resolved**: the `/dev/ttyACM0` default goes (A.U21.28: never a bare ttyACM scan). A.U27.13 quotes the resolver's
  line as `FAILED: no MicroPython board found …` (A.U21.28's form); A.U27.29's one error contract (U27) words it
  `setup_toolchain: …` — that form (M.TOOL.072, D7; M_TOOL gap 4, gap pass). The `board` subcommand takes no toolchain
  lock and reads no `versions.toml` (M.TOOL.072, D6), so the resolver call cannot wait on a running build.
- **Unit**: U27 (needs A.U21.28's `board` subcommand from U21).
- **Depends**: M.SCR.014; A.U21.28 (`setup_toolchain.py board`, TOOL).
- **Blast carried by**: `tests_scripts/test_mpremote_connect_sh.py` (stub `uv`: env wins; resolver called otherwise;
  `--help`) → A.U27.13 (TSC); `harness.py` delegation → M.HW_BENCH resolver entry (HW_BENCH); README/`tests_hardware/README.md`
  → A.U36.547/M.HW_BENCH.126.
- **Kind**: code

## scripts/run_flash_hardware_suite.sh

### M.SCR.030 Flash runner: lower levels first, a floor the caller narrows
- **From**: A.U7.18, A.U7.19, A.U27.19, A.U26.35/A.U26.74 (names), A.C.18/A.U33.07 (procedures naming it — blast),
  A.U36.008 (docs — blast), A.U7.14 (blast).
- **Site**: `scripts/run_flash_hardware_suite.sh:1-11`.
- **Change**: header (3 lines): "L3: runs every lower level (scripts/_run_lower_levels.sh L3), then tests_hardware/flash/
  on a real board through _require_clean_hardware_run.sh; soak and the rollover wait never run here, whatever -m a caller
  passes (it narrows). Provisioning: tests_hardware/README.md." Parse `--help` (usage listing `--skip-lower-levels`,
  "other arguments go to pytest", the env vars the wrapper reads) and `--skip-lower-levels` out of `"$@"`; unless
  skipping, `scripts/_run_lower_levels.sh L3` (failure → exit 1, no board touched); then
  `scripts/_require_clean_hardware_run.sh --runner run_flash_hardware_suite --levels "L0 L1 L2 L3" --marker-floor "not
  soak_duration and not multi_day_rollover" [--not-clean-reason "lower levels skipped: L0 L1 L2"] tests_hardware/flash
  "$@"`.
- **Resolved**: —
- **Unit**: U27 (stage U7: lower levels and help; U27: floor and names).
- **Depends**: M.SCR.006, M.SCR.034.
- **Blast carried by**: `tests_scripts/test_hardware_runners.py` (stubbed callees: order, skip flag → NOT CLEAN exit 4,
  `-m bus` → one combined `-m`) → A.U7.18/A.U27.19 (TSC); `tests_hardware/README.md` Running → M.HW_BENCH.126.
- **Kind**: code

## scripts/run_bench_hardware_suite.sh

### M.SCR.031 Bench runner: lower levels, then L3 as its own step, then L4
- **From**: A.U7.18, A.U7.19, A.U27.19, A.C.03/A.C.05 (round procedure: the bench runner as the round's entry — blast),
  A.U36.008, A.U7.24 (containment test — blast).
- **Site**: `scripts/run_bench_hardware_suite.sh:1-11`.
- **Change**: as M.SCR.030 with: `scripts/_run_lower_levels.sh L4`; step 1 the wrapper over `tests_hardware/flash`
  (`--levels "L3"`, its block printed, stop unless exit 0); step 2 over `tests_hardware/bench` (`--levels "L0 L1 L2 L3
  L4"`); both with `--marker-floor "not soak_duration and not multi_day_rollover"` and the caller's arguments; the final
  block is step 2's; header states "L4: lower levels, then L3 as its own clean step, then tests_hardware/bench/".
- **Resolved**: —
- **Unit**: U27 (stage U7).
- **Depends**: M.SCR.006, M.SCR.034.
- **Blast carried by**: as M.SCR.030 (TSC, HW_BENCH); A.C.03/A.C.05 run it (procedure, phase C).
- **Kind**: code

## scripts/run_bench_soak_tests.sh

### M.SCR.032 Soak runner: one duration, on top of a clean bench run
- **From**: A.U26.35 (`--tier` → `--duration`, `long_soak` → `soak_duration`), A.U27.19 (floor `soak_duration`), A.U7.18
  (no lower levels; block line), A.U7.19, A.U0.35 (`:3` owner tag), A.U26.74 (`--allow-multi-day-rollover`), A.C.07
  (procedure — blast), A.U33.04 (BACKLOG — blast).
- **Site**: `scripts/run_bench_soak_tests.sh:1-22`.
- **Change**: header (3 lines): "Runs only @pytest.mark.soak_duration tests at one named duration - an opt-in on top of
  the bench tier (owner, 2026-09-26) that the general runners never bundle (owner, 2026-09-04). Durations:
  tests_hardware/soak_durations.py; the tick-rollover round is not a soak: scripts/run_bench_rollover_test.sh."
  (gap pass: names the rollover's own runner, M.SCR.074; A-C review fold: OR139.a, the round is no longer 12.4 days) Usage `scripts/run_bench_soak_tests.sh --duration {short,mid,long} [pytest args]`;
  `--help` exit 0; a missing or unknown duration → usage, exit 2; then `scripts/_require_clean_hardware_run.sh --runner
  run_bench_soak_tests --levels "soak duration <d> (not a level)" --marker-floor "soak_duration" tests_hardware/flash
  tests_hardware/bench --soak-duration "<d>" "$@"`.
- **Resolved**: A.U0.35's tag "(owner, 2026-09-26)" and HEAD's "(owner's direction, 2026-09-04)" both stay (two owner
  decisions: the opt-in and the separation).
- **Unit**: U27 (stage U0: A.U0.35 tag on today's line; U26 names land here in U27 as A.U26.35 asks).
- **Depends**: M.SCR.034; M.HW_BENCH.040 (`soak_durations.py`).
- **Blast carried by**: `tests_scripts/test_hardware_runners.py` (unknown duration exit 2; `-m foo` → `(soak_duration)
  and (foo)`) → A.U27.19 (TSC); README soak section → M.HW_BENCH.126.
- **Kind**: code

## scripts/run_manual_hardware_tests.sh

### M.SCR.033 Manual runner: help, retried sync, `--no-sync`
- **From**: A.U26.75, A.U28.01, A.U7.19, A.C.04 (manual round — procedure), A.U7.17/A.U26.42 (runner's block and
  judgments — `tests_hardware/manual/`, blast), A.U27.37 (`harness` path insert — blast), A.U36.008.
- **Site**: `scripts/run_manual_hardware_tests.sh:1-8`.
- **Change**: header kept (≤ 3 lines; "manual" named an execution mode of L3/L4, harmonization 20); `--help` → its own
  usage plus "flags --list, --only <name>: see tests_hardware/README.md", exit 0 (the Python runner's own `--help`
  stays); `scripts/uv_sync_retried.sh`; `uv run --no-sync python tests_hardware/manual/__main__.py "$@"`.
- **Resolved**: —
- **Unit**: U27 (with A.U26.75's U26 stage: retried sync and `--no-sync`).
- **Depends**: M.SCR.014.
- **Blast carried by**: summary block of the manual runner (A.U7.17, HW_BENCH manual runner entry);
  `tests_scripts/test_tool_help.py` → A.U7.19 (TSC).
- **Kind**: code

## scripts/_require_clean_hardware_run.sh

### M.SCR.034 Hardware wrapper: run record, archive, `$EVIDENCE_DIR`, verdict in Python
- **From**: A.U7.13 (run record, `-v` after the caller), A.U7.14 (verdict moves out), A.U7.20 (log and record in the
  archive), GAP-B6 / M.HW_BENCH.055 (`export EVIDENCE_DIR`), A.U27.19 (`--marker-floor`), A.U26.74/A.U26.75 (names,
  retried sync, `--no-sync`), A.U0.35 (tag moves into `_hardware_verdict.py`), A.U27.33 (trap convention), A.U7.18
  (`--levels`, `--not-clean-reason`), A.U28.01/A.U26.35 (blast).
- **Site**: `scripts/_require_clean_hardware_run.sh:1-109`.
- **Change**: header (3 lines): "Runs a hardware pytest selection and judges it from its run record
  (scripts/_hardware_verdict.py): a plain exit code cannot see an unexpected skip or a gate deselection. Evidence (log,
  record) lands in build/archive/hardware/<ts>/, the newest three kept." `set -uo pipefail` with its one-line reason
  (pytest's exit code is captured, not fatal). Leading options consumed: `--runner NAME`, `--levels TEXT`,
  `--marker-floor EXPR`, `--not-clean-reason TEXT`, `--help`. Caller `-m EXPR`/`-mEXPR` removed from the forwarded
  arguments, the last kept; effective `-m "(<floor>) and (<caller>)"` or `-m "<floor>"`, printed. `scripts/uv_sync_retried.sh`;
  `EVIDENCE_DIR="$(uv run --no-sync scripts/_archive_evidence.py --runner hardware --new-dir)"`; `export EVIDENCE_DIR`
  (read by `tests_hardware/evidence.py`); `log="$EVIDENCE_DIR/pytest.log"`, `record="$EVIDENCE_DIR/run_record.json"`;
  `PYTHONPATH=scripts uv run --no-sync pytest -p _pytest_run_record --run-record="$record" "${args[@]}" -m "$expr" -v
  2>&1 | tee "$log"`; `pytest_exit=${PIPESTATUS[0]}`; `uv run --no-sync scripts/_hardware_verdict.py --run-record
  "$record" --pytest-exit "$pytest_exit" --runner "$runner" --levels "$levels" [--not-clean-reason …]`; exit with its
  code. The bash whitelist (`:10-47`), flag loop (`:19-24`), mktemp/rm log (`:49-50`), skip/pass greps and NOTE text go.
  No trap is needed (nothing temporary is created).
- **Resolved**: GAP-B6: A.U7.20 writes into the archive but exports nothing; A.U26.22 needs `$EVIDENCE_DIR` — export
  added (M.HW_BENCH.055).
- **Unit**: U27 (stages: U7 A.U7.13/.14/.20; U26 A.U26.74/.75 names and sync; U27 floor and export).
- **Depends**: M.SCR.003, M.SCR.004, M.SCR.005, M.SCR.014.
- **Blast carried by**: `tests_scripts/test_require_clean_hardware_run_sh.py` rewritten against run records (argv of the
  stubbed pytest, `EVIDENCE_DIR` exported and existing, log in the archive) → A.U7.14/A.U27.19/A.U26.74 (TSC);
  `tests_hardware/evidence.py` → M.HW_BENCH.055; `tests_hardware/conftest.py` notes → A.U7.13 (HW_BENCH); README
  verdict text → M.HW_BENCH.126 / A.U7.02 docs (HW_BENCH, DOCS).
- **Kind**: code

## scripts/test.sh

### M.SCR.035 `test.sh` header, help, argument and environment validation
- **From**: A.U7.19 (`--help` and its env list), A.U7.02 (usage error exits 2, OR133), A.U7.06 (two timeout
  variables validated up front), A.U27.14 (`:25-27`, `:43` texts), A.U27.08/A.U27.12/A.U24.72 (header facts: derived
  site device, build flavour, four coverage reports), A.U8.15 (tags on the two defaults), A.U27.33 (convention), A.SDEP.16
  (W15 `TZ=UTC` — kept unless the U37 refresh finds `ports/unix/modtime.c` TZ-agnostic, then it goes with its CLAUDE.md
  bullet), A.U30.21 (GC range check DONE-AT-HEAD — holds), A.U14.28 (F.7 row 6 names this export — blast).
- **Site**: `scripts/test.sh:1-62`.
- **Change**: header (3 lines): "Runs tests/ under the real MicroPython Unix port (one process per test file, per derived
  device for PER_DEVICE files), the lwIP host files, the host-side twin scenario harness per derived device, and the
  backgrounded tests_scripts/ pytest tier; ends with the SPECIFICATION.md E.10 summary block." Second paragraph (≤ 3
  lines): "--coverage runs the same files under build-settrace, the only build flavour compiled with
  MICROPY_PY_SYS_SETTRACE, and renders src/, digital_twin/, the generated modules and the host build chain (E.5, E.5.2)."
  Third: "Rebuilds frozen_modules/frozen_html.py from the first derived device every run (A.9 for why not .frozen/)."
  `export TZ=UTC` with its 3-line reason (kept). Argument loop: `-h|--help` → usage to stdout listing `--coverage`,
  `PICO_TOOLCHAIN_DIR`, `SKIP_APT`, `PER_FILE_TIMEOUT_S`, `TESTS_SCRIPTS_TIMEOUT_S`, `TEST_PARALLELISM`, `GC_THRESHOLD`
  with defaults, exit 0; unknown argument → "error: unknown argument <a> (scripts/test.sh --help)", exit 2 (pending
  Q1). The validation block, before any sweep: `GC_THRESHOLD` shape and 32-bit range (texts as HEAD, comment `:43` "85
  times" → "once per test file"), then `# @tunable runner.per_file_timeout_s = 240`
  `per_file_timeout_s="${PER_FILE_TIMEOUT_S:-240}"` and `# @tunable runner.tests_scripts_timeout_s = 1200`
  `tests_scripts_timeout_s="${TESTS_SCRIPTS_TIMEOUT_S:-1200}"`, each `[[ "$v" =~ ^[1-9][0-9]{0,5}$ ]]` else "error:
  <NAME> must be a positive integer number of seconds, not '<v>'"; every validation failure exits 2 (OR133). The
  `:25-27` comment → "…tests_scripts/ runs a nested test.sh to prove the rejection, concurrently with every test file
  holding tests/_tmp scratch." The two sweeps (`tests/_tmp`, `devices/zz_test_*.toml`) follow unchanged.
- **Resolved**: A.U7.02 sets "a usage error exits 2 in every runner" and flags `test.sh:34, :47, :53` (exit 1) to the
  lead; A.U7.06 writes its new checks with exit 1. Settled by the owner: Q1 answered (a), OR133.
- **Unit**: U27 (stages: U7 help, timeouts, block; U8 tags; U27 texts).
- **Depends**: — (Q1 answered, OR133).
- **Blast carried by**: `tests_scripts/test_test_sh.py:512-527` (rejected invocation leaves the tree untouched; exit code
  per Q1) and new timeout cases → A.U7.06 (TSC); `test_tool_help.py` → A.U7.19 (TSC); README env list (`:139-152`
  "positive integer") → A.U7.06 docs (DOCS); Part N rows → A.U8.15 (SPEC); E.10's exit-code list → A.U7.02 (SPEC).
- **Kind**: code

### M.SCR.036 Binaries by build flavour, the record check, the lwIP binary, one MICROPYPATH
- **From**: A.U27.12 (2), A.U21.22 (c) (missing record = missing binary; setup only through the installer's lock),
  A.U21.12 (`lwip_bin`, rebuild trigger), A.U27.15 (unit layout from `micropypath.toml`), A.U36.512 (term), A.U28.04
  (CI keeps test.sh's own rebuild — blast), A.SDEP.08/A.U21.31 (blast).
- **Site**: `scripts/test.sh:66-125` (paths, `unix_port_variant()`, rebuild and re-check), `:369` (MICROPYPATH literal).
- **Change**: `source scripts/_unix_port.sh`; `want_flavour=settrace` under `--coverage`, else `standard`;
  `unix_port_ensure "$want_flavour"` (missing binary, wrong flavour or missing toolchain record → `setup` through the
  installer, which holds the toolchain lock — a concurrent build fails fast with its message, never a wait);
  `micropython_bin="$(unix_port_bin "$want_flavour")"`; unless `--coverage`, `unix_port_ensure lwip` and
  `lwip_bin="$(unix_port_bin lwip)"`; `unit_micropypath="$(micropypath unit)"`. `unix_port_variant()`,
  `want_variant`/`got_variant` and the "plain" word go; comments say "build flavour".
- **Resolved**: —
- **Unit**: U27 (stages: U21 A.U21.12/.22 on HEAD's probe; U27 the shared probe).
- **Depends**: M.SCR.008, M.SCR.009; A.U21.12/A.U21.03 (TOOL).
- **Blast carried by**: `tests_scripts/test_test_sh.py:384-440` retargeted to `scripts/_unix_port.sh` → A.U27.12 (TSC);
  `tests_scripts/test_coverage_runner.py:27/:35` → A.U27.12/A.U27.15 (TSC).
- **Kind**: code

### M.SCR.037 Generation step: the one writer, before the pytest tier
- **From**: A.U27.11 (generator writes every output; test.sh calls it), A.U36.544 (`:214-216` reason in place),
  A.U24.46 (freshness stamp written by the generator; bare runs guarded — blast), A.U6.02/A.U24.54/A.U20.07 (outputs —
  blast).
- **Site**: `scripts/test.sh:206-212`.
- **Change**: `uv run scripts/_generate_sensortask_modules.py` unchanged in position; comment → "# Generated fresh into
  build/generated_src/ (SPECIFICATION.md L.2), which the unit MICROPYPATH puts first. # It runs before tests_scripts/ is
  backgrounded: that tier creates and deletes devices/zz_test_*.toml fixtures, and the generator globs devices/*.toml, so
  generating first keeps every fixture out of the generated tree." (A.U36.544: the reason stated, the "Part E.1 has" pointer
  goes).
- **Resolved**: —
- **Unit**: U36 (the text; the call is unchanged).
- **Depends**: M.SCR.068.
- **Blast carried by**: `tests_scripts/test_test_sh.py:31-46` (generation before the pytest launch) holds (TSC);
  `tests/_generated_tree.py` freshness guard → A.U24.46 (TEST_HELP).
- **Kind**: doc

### M.SCR.038 The pytest tier: run record, host coverage, trap first
- **From**: A.U7.08, A.U24.72 (2) (host coverage under `--coverage`), A.U27.33 (2) (temp files after the trap), A.U27.14
  (`:296-298` text), A.U8.15 (`runner.kill_after_s` tag), A.U28.15 (no XML), A.U7.26/A.U28.02/A.U28.03/A.U29.02/A.U30.03
  (new L0 files collected with no change — blast).
- **Site**: `scripts/test.sh:214-278`, `:296-298`.
- **Change**: `raw_dir=""`, `results_dir=""`, `tests_scripts_status_file=""`, `tests_scripts_inner_pidfile=""`,
  `tests_scripts_pid=""` declared; `trap _cleanup EXIT` armed; then the files created (`results_dir` first; the status and
  pidfile inside it). `_cleanup` additionally calls `port_lock_release_all` (M.SCR.039) and keeps its kill-exact-pids
  body. The job: plain run `PYTHONPATH=scripts timeout --kill-after=10 "$tests_scripts_timeout_s" uv run pytest
  tests_scripts -q -p _pytest_run_record --run-record="$results_dir/tests_scripts.json"` (`# @tunable runner.kill_after_s
  = 10` on its line); under `--coverage`: `COVERAGE_FILE="$results_dir/host.coverage" PYTHONPATH=scripts timeout … uv run
  coverage run --source=buildgen,scripts,toolchain -m pytest tests_scripts -q -p _pytest_run_record --run-record=…`.
  The status file still records PASS/FAIL (124 message kept). `:296-298` → "# tests_scripts/ was backgrounded after the
  generation step above; RUN_SLOW_FIRMWARE_BUILD stays unset for it, keeping the one real ARM firmware compile opt-in
  for local iteration; ci.yml's firmware-build-verify job sets it." The long comment block `:214-235` keeps only its
  load-bearing reasons (overlap, timeout as hang backstop, no retry, after generation), each paragraph ≤ 3 lines.
- **Resolved**: A.U24.72's `uv run coverage run …` and A.U7.08's plugin command combine into one command per mode; the
  anchor `uv run pytest tests_scripts -q` (`test_test_sh.py:24`) stays a substring of the plain form.
- **Unit**: U27 (stages: U7 run record; U24 host coverage; U27 trap order and texts).
- **Depends**: M.SCR.004, M.SCR.039; `coverage==<pin>` in the dev group (A.U24.72/A.U28.02, TOOL).
- **Blast carried by**: `tests_scripts/test_test_sh.py:31-46, :319-345` (launch text, trap/pid tests) → A.U7.08/A.U27.33
  (TSC); SPEC E.1 pytest tier, E.5 host report → A.U7.08/A.U24.72 (SPEC); `.gitignore` `htmlcov_host/`,
  `coverage_summary_*.md` → A.U24.72/A.U28.33 (TOOL).
- **Kind**: code

### M.SCR.039 Site builds, port-53 lock, capability grant
- **From**: A.U27.08 (2) (site device = first derived device), A.U6.03/A.U27.38 (every device's site for the harness —
  AD-5), A.U24.69 (port-53 lock), A.U23.38 (blast: `build_website.sh` interface unchanged), A.U24.82 (row — blast).
- **Site**: `scripts/test.sh:280-294`.
- **Change**: `source scripts/_devices.sh; source scripts/_port_lock.sh`; before the first twin can start (right after
  validation and the toolchain step): `port_lock_take 53 scripts/test.sh` (held → exit 1 with M.SCR.012's message),
  released by `_cleanup`. Capability block on `$micropython_bin` unchanged (comment ≤ 3 lines). Site: `site_device="$(derived_devices
  | head -n 1)"`; echo "== Building frozen_modules/frozen_html.py (the $site_device website, the first derived device)";
  `scripts/build_website.sh "$site_device"`; then, unless `--coverage`, `scripts/build_device_websites.sh` (every
  derived device into `build/generated_html/<device>/`, the sites the harness jobs boot). Comment `:290-292` → "Every
  generated sensortask_<device>.py imports frozen_html at module level, so the unit tier needs one site on its path; any
  derived device serves; no device is named here."
- **Resolved**: —
- **Unit**: U27 (stage U24: the lock).
- **Depends**: M.SCR.007, M.SCR.012, M.SCR.020.
- **Blast carried by**: `tests_scripts/test_test_sh.py` site-step test (no literal device name; `zz_test_` never chosen)
  → A.U27.08 (TSC); A.U6.15's variant-literal allow-list loses `test.sh` (TSC); CLAUDE.md "two suites" bullet →
  A.U24.69 (DOCS).
- **Kind**: code

### M.SCR.040 One job runner: retries reported, a log that fails closed, per-device tags
- **From**: A.U7.04 (`RETRIED-PASS k/n`), A.U7.05 (`.noverdict`), A.U24.65 (3) (device argument, `TEST_DEVICE`, tag
  `<file>[<device>]`), A.U21.12 (binary argument), A.U27.38 (harness job through the same loop), A.U27.15 (unit
  MICROPYPATH), A.U27.33 (loop and quoting), A.U8.15 (tags), A.U0.40 (`:311-313` text), A.U0.60 (actor label — blast,
  `:311-313` is A.U0.40's site), A.U19.24/A.U30.12/A.U30.13/A.S0930.26/.37 (files that run at both stages here — blast).
- **Site**: `scripts/test.sh:310-390`.
- **Change**: comment `:311-313` → "# Per-file timeout with two retries, stdbuf line buffering and -X heapsize=16M: standing
  backstops, not fixes for any one hang; the heap value is a measured floor, never raised as a fix (SPECIFICATION.md
  E.3.1)." `# @tunable runner.per_file_attempts = 3` `max_attempts=3`. `_flag_memory_errors` as A.U7.05 (unreadable
  log or grep exit ≥ 2 → `$results_dir/$tag.noverdict`; body self-contained). `_run_with_retries <tag> <status_file>
  <timeout_s> <cmd…>`: `for ((attempt = 1; attempt <= max_attempts; attempt++))`; the pipeline `stdbuf -oL -eL timeout
  --kill-after=10 "$timeout_s" "${cmd[@]}" 2>&1 | sed -u "s/^/[$tag] /" | tee -a "$log_file"` (`runner.kill_after_s`
  tag); exit 0 → `_flag_memory_errors "$tag" "$log_file"`, status `PASS` on attempt 1 else `RETRIED-PASS
  <attempt>/<max_attempts>`; 124 and attempts left → retry message; else `_flag_memory_errors "$tag" "$log_file"`,
  `FAIL` (two call sites, as today). `run_test_file <test_file> <status_file> [<device>] [<binary>]`: tag
  `<basename>` or `<basename>[<device>]`; `cmd` = `"$binary" -X heapsize=16M` (`# @tunable l1.unix_heapsize = 16M`) plus
  the coverage/threshold/plain runner selection as today; environment `MICROPYPATH="$unit_micropypath"` and, with a
  device, `TEST_DEVICE="$device"`; timeout from `per_file_timeout_overrides_s[<file>]` else the default. `run_scenarios_job
  <device> <status_file>`: tag `scenarios[<device>]`, command `uv run --no-sync scripts/_digital_twin_scenarios.py --device
  "$device" --micropython-bin "$micropython_bin" --logs-dir "$results_dir/scenarios_$device" --gc-threshold
  "${GC_THRESHOLD:--1}" --shared-port-53 --run-record "$results_dir/scenarios_$device.json"`, timeout
  `per_file_timeout_overrides_s[scenarios]` (`# @tunable runner.scenarios_timeout_s` — estimated at landing as 5× its first
  measured wall clock (agent), re-measured by A.U35.23); after the command, every twin log under its logs dir is appended to
  the job log before the gate, so the two `_flag_memory_errors` sites cover it.
- **Resolved**: the count of `_flag_memory_errors "$tag" "$log_file"` stays 2 (A.U7.05/A.U24.65 blast) by moving the loop
  into `_run_with_retries`; A.U0.40 and A.U0.60 both name `:311-313` — A.U0.60's actor label is A.U0.40's text (the
  measured floor is the owner's E.3.1 rule; no separate label).
- **Unit**: U27 (stages: U7 A.U7.04/.05; U8 tags; U21 binary argument; U24 device argument; U27 harness job, MICROPYPATH).
  A-C2 step order: A.U24.65's part lands in U25, not U24 (it needs A.U25.25, which lands in U25).
- **Depends**: M.SCR.036, M.SCR.017.
- **Blast carried by**: `tests_scripts/test_test_sh.py:564-628` (`_flag` extraction, `RETRIED-PASS`, noverdict, count == 2)
  → A.U7.04/A.U7.05 (TSC); SPEC E.3.1 retry text → A.U7.04 (SPEC); Part N rows `runner.*`, `l1.unix_heapsize`,
  `runner.scenarios_timeout_s` → A.U8.15 and GAP (SPEC, below).
- **Kind**: code

### M.SCR.041 Dispatch: per-device expansion, harness jobs, lwIP host files
- **From**: A.U24.65 (3) (`PER_DEVICE` expansion), A.U27.38 (harness jobs per derived device), A.U21.12 (`tests/lwip_host/`
  loop, excluded under `--coverage`), A.U27.33 (arrays), M.TWIN (`PER_DEVICE` marker on more twin files — unchanged rule).
- **Site**: `scripts/test.sh:416-441`.
- **Change**: job list built after the heavy-list check (M.SCR.042): for each `tests/test_*.py` in dispatch order, a file
  whose text matches `^PER_DEVICE = True$` adds one job per `derived_devices` entry, any other file one job; unless
  `--coverage`, one `scenarios[<device>]` job per derived device (dispatched first: each is the longest job) and one job per
  `tests/lwip_host/test_*.py` with `binary="$lwip_bin"` (dispatched last). Each job runs in the background bounded by
  `max_parallel` as today (`wait -n || true`), status file `$results_dir/<tag>.status`.
- **Resolved**: A.U25.46 says `test.sh`'s harness run is "for the local run"; A.U27.38 runs it in CI's unit lanes too (both
  GC stages) — A.U27.38 is the later, wiring action and A.U25.46 names U27 as its wirer; kept.
- **Unit**: U27 (stages: U21 lwIP loop; U24 expansion; U27 harness jobs).
  A-C2 step order: A.U24.65's part lands in U25, not U24 (it needs A.U25.25, which lands in U25).
- **Depends**: M.SCR.040, M.SCR.007, M.SCR.042.
- **Blast carried by**: CI `unit-tests`/`unit-tests-gc-threshold` carry the harness at both stages with no `ci.yml` change
  (A.U27.38, TOOL: job time re-measured, A.U8.15's `timeout-minutes` rows); `tests_scripts/test_test_sh.py` expansion
  case (one `PER_DEVICE` fixture file → one job per derived device, tags) → A.U24.65 (TSC).
- **Kind**: code

### M.SCR.042 The heavy-file list names existing files, else the run stops
- **From**: A.U35.24, A.U24.65 (names the per-device files), A.U35.23 (re-measured order), A.U8.24 (row — blast).
- **Site**: `scripts/test.sh:392-424`.
- **Change**: `_heavy_files_priority` holds the slowest files of the B3 measurement (A.U35.23), as many as that cut
  shows, among them the `PER_DEVICE` files (`tests/test_sensortask.py`, `tests/test_digital_twin_construction.py` and the
  twin files M.TWIN marks); the six `test_sensortask_<device>.py` and both `test_digital_twin_webserver_concurrency_*`
  names go. `_check_heavy_list` (a function, self-contained): every entry must be an existing `tests/test_*.py`, else
  "scripts/test.sh: heavy-file list names <file>, which does not exist - update _heavy_files_priority" and exit 2; the
  `[ -f ]` skip goes. Comment `:392-398` keeps the reason and drops the count word ("the heaviest files").
- **Resolved**: —
- **Unit**: U35.
  A-C2 step order: A.U24.65's part lands in U25, not U24 (it needs A.U25.25, which lands in U25).
- **Depends**: M.SCR.041.
- **Blast carried by**: `tests_scripts/test_test_sh.py` two new tests → A.U35.24 (TSC); `timing.md` → A.U35.23 (procedure);
  BACKLOG text → A.U35.57 (DOCS).
- **Kind**: code

### M.SCR.043 Speed probe on a monotonic clock, failing safe; tags
- **From**: A.U8.16, A.U8.15.
- **Site**: `scripts/test.sh:148-204` (`_detect_parallelism()`).
- **Change**: as A.U8.16: `/proc/uptime` before/after, integer `probe_ms`; failure → multiplier 1 and "== speed probe
  failed - running at 1x" on stderr; tags `runner.probe_iterations = 500000`, `runner.band_fast_ms = 250`,
  `runner.band_mid_ms = 900`, `runner.mult_fast = 4`, `runner.mult_mid = 2`, `runner.nproc_fallback = 4` on their literals;
  comments rewritten to the rule (≤ 3 lines each). The `max_parallel >= 1` clamp `:197-204` holds.
- **Resolved**: —
- **Unit**: U8.
- **Depends**: —
- **Blast carried by**: Part N rows and Pi4 calibration → A.U8.16/A.U35.23 (SPEC, procedure); `test_test_sh.py` probe
  extraction (stub `/proc/uptime` unreadable → 1x) → A.U8.16 (TSC).
- **Kind**: code

### M.SCR.044 Four coverage reports, no XML; evidence archived, never deleted
- **From**: A.U24.72 (third render), A.U28.15 (no `--xml-file`), A.U7.20 (archive previous coverage at start, failed logs
  and the block at the end), A.U36.526 (E.5 text — blast), A.U27.18 (no step summary), A.U28.02 (pinned coverage — blast).
- **Site**: `scripts/test.sh:261` (`_cleanup`), `:472-482`.
- **Change**: under `--coverage`, before `rm -rf tests/_tmp`: `uv run scripts/_archive_evidence.py --runner
  test_sh_coverage htmlcov htmlcov_digital_twin htmlcov_generated htmlcov_host coverage_summary.md
  coverage_summary_digital_twin.md coverage_summary_generated.md coverage_summary_host.md`. Renders: `src` →
  `htmlcov`/`coverage_summary.md`; `digital_twin` → `htmlcov_digital_twin`/`coverage_summary_digital_twin.md`;
  `build/generated_src` → `htmlcov_generated`/`coverage_summary_generated.md`; host: with `COVERAGE_FILE="$results_dir/host.coverage"`,
  `uv run coverage html -d htmlcov_host` and `uv run coverage report --format=markdown > coverage_summary_host.md` (the
  pinned version's option names re-checked at landing, CLAUDE.md docs rule); each `|| coverage_render_failed=1`; no XML anywhere. After the summary block is printed
  (M.SCR.045) and before exit: the deciding-attempt logs of every failed, no-verdict, memerr and retried job plus
  `$results_dir/summary.txt` (the block as printed) are moved by `uv run scripts/_archive_evidence.py --runner test_sh …`
  (a green run archives the block only); `_cleanup` then removes only scratch.
- **Resolved**: A.U7.20 lists `coverage.xml`/`coverage_digital_twin.xml` to archive; A.U28.15 removes them — dropped from
  the list. Host render form: `_render_coverage.py` renders Unix-port dumps; the host data is a native `coverage.py` file,
  rendered by `coverage` itself (agent decision AD-6).
- **Unit**: U28 (latest: A.U28.15; stages U7 archive, U24 renders).
- **Depends**: M.SCR.003, M.SCR.069, M.SCR.038.
- **Blast carried by**: CI `unit-tests-coverage` summaries/artifacts for the four reports, Codecov steps removed →
  A.U28.15 (TOOL); `tests_scripts/test_test_sh.py:826-842` render lines → A.U28.15 (TSC); SPEC E.5/E.5.3, README "Test
  coverage" → A.U36.526 (SPEC, DOCS); `.gitignore` → A.U28.33 (TOOL).
- **Kind**: code

### M.SCR.045 The E.10 summary block per level; exit codes
- **From**: A.U7.03, A.U7.04 (root-cause lines), A.U7.07 (microtest closing line), A.U7.08 (L0 from the record),
  A.U21.12 (lwIP files counted in L1), A.U27.38 (harness under L2), A.U27.18, A.U8C2.08/.12/.15, A.U17.11/.23/.25,
  A.U25.39 (files whose counts the block reads — blast).
- **Site**: `scripts/test.sh:453-557`.
- **Change**: `source scripts/_summary_block.sh`; collector per job: `PASS` → passed; `RETRIED-PASS k/n` → retried (and
  "root-cause item: <tag> needed attempt k/n - record it as a root-cause item"); `.noverdict` or `FAIL` or missing status
  → failed with reason; `.memerr` → failed "MemoryError seen" (the text `test_test_sh.py:620-628` reads); a MicroPython
  job whose log lacks the microtest closing line → failed "no test count (crashed or killed)". `Counts (files)` from
  that; a second `Counts (tests)` line sums each deciding log's `P/T passed, F failed, S skipped` and each harness run
  record. `summary_levels`: `L0 <verdict from _summary_block.py --from-run-record tests_scripts.json>` (missing record
  → FAIL "no verdict"), `L1 <tests/test_*.py except test_digital_twin_*, plus tests/lwip_host>`, `L2 <test_digital_twin_*
  and the scenario harness; run_digital_twin_ci.sh not run>`; the harness's deselected port-53 scenarios are listed under
  `Deselected:` "by runner selection: needs exclusive port 53 (run_digital_twin_ci.sh)"; under `--coverage` the lwIP and
  harness jobs are listed under `Skipped:` "not run under --coverage (the plain pass runs them)". `summary_gc_stage`:
  `-1 (reactive default)`, the `GC_THRESHOLD` value, or `coverage run (settrace)`. The GitHub annotation block
  (`:505-539`) stays unchanged before the block. Exit: 0 pass; 1 any failure; 3 tests passed but a coverage render failed
  (`Result: PASS (coverage report not rendered)`); 2 for usage/validation and the heavy-list check. The block is also
  written to `$results_dir/summary.txt` for the archive (M.SCR.044). Nothing writes `GITHUB_STEP_SUMMARY`.
- **Resolved**: A.U21.12's separate "tests/lwip_host (lwIP host build): N/M files passed" line folds into the block's L1
  level and its file list (E.10 forbids lines after the block) — A.U7.03/E.10 settle it.
- **Unit**: U27 (stages: U7 block; U21 lwIP counts; U27 harness).
  A-C2 step order: A.U17.25's part lands in U25, not U17 (it follows A.U17.25's own change, which lands in U25).
- **Depends**: M.SCR.001, M.SCR.002, M.SCR.040, M.SCR.041.
- **Blast carried by**: `tests_scripts/test_test_sh.py:764-813` `_verdict_block()` rewritten, fixture results dir case →
  A.U7.03 (TSC); README `:156-176`, SPEC E.3/E.5.3/B.10 quoted texts → A.U7.03 docs (DOCS, SPEC); `_run_lower_levels.sh`
  reads the exit codes (M.SCR.006); CI `unit-tests-coverage` reads exit 3 (holds).
- **Kind**: code

## scripts/_digital_twin_ci_suite.py

### M.SCR.046 Suite header, imports, types, constants and their tags
- **From**: A.U27.28 (header ≤ 3 lines), A.U25.48 (3) (`:5` text), A.U20.33 (no `from __future__`), A.U27.27 (no `Any`;
  JSON aliases), A.U28.28/A.U0.07 (no function-level import, `:207` noqa goes), A.U27.37 (ceiling lookup imported),
  A.U28.27 (no PLW0603/SIM105/PTH findings), A.U3.02 (`:103-105` comment), A.U5.05 (`:111` names
  `_DEFAULT_OUTER_CAP_S`), A.U8.04 (`web.outer_cap_s` tag on `:111`), A.U8.05 (`_CEILING_ROUNDS`, `_SLOT_RELEASE_WAIT_S`
  tags), A.U8.20 (durations and poll steps tagged; `:680`/`:904` not tagged — removed, M.SCR.050/.054), A.U8.14
  (`:1310` 32768 tag), A.U10.38 (class names in comments — read; its blast names no `scripts/` site, carried here),
  A.U27.08 (`:115`, `:122-124` texts), A.U25.35 (state constants go), A.U10.37 (module names in
  text), A.U2.03 (`_NTP_ERRNO_NO_REPLY = 21` goes), A.U10.34 (function comments, module docstring kept for argparse),
  A.U36.513 (generator, not hand-written, in comments), A.U35.25/.27 (sampler interval, window — measured values),
  A.U8.24 (`disallow_any_explicit` — blast); gap pass: A.U19.14 via M_DOCS gap 2 (item 24's citer), A.U11.31 (wording).
- **Site**: `scripts/_digital_twin_ci_suite.py:1-170`.
- **Change**: docstring (3 lines): "L2 system suite: boots one derived device's generated graph in the twin
  (digital_twin/run_generic_integration.py) as a subprocess and drives it over HTTP/UDP through real restarts, at
  gc.threshold -1 then 32768. The fault matrix comes from the device's wiring plan, never a driver list (a device without
  a driver never faults it). Run by scripts/run_digital_twin_ci.sh; reference: digital_twin/README.md "Automated CI
  suite"." No `from __future__`; imports at top, including `from _twin_process import …` (the script's own directory
  is `sys.path[0]`; `host_typecheck.ini`'s `mypy_path` gains `scripts`, A.U27.27) and `from buildgen.validate import
  device_max_connections_by_name` (repo root on `sys.path` before it, `# noqa: E402 - <reason>` if a path insert
  precedes it); `typing.Any` gone (JSON aliases from `_twin_process.py`). Constants: `STATE_DIR`/`FRAM_STATE_PATH`/
  `SCD30_STATE_PATH`/`CONFIG_DIR` go (per-pass state, M.SCR.048); `_NTP_ERRNO_NO_REPLY` goes (catalog lookup by name
  through `tests/_error_codes.py`'s helper, A.U2.03, loaded by path); `_BUS_FAULT_OPS` → `_SUSTAINED_FAULT` (M.SCR.051).
  Comments: `:99-101` → "each injected fault fails one SGP40 measure read; three exhaust the supervisor's restart budget"
  (A.U25.36 (5) with the corrected aim, M.SCR.053); `:103-105` → "…the central newest-entry rule (asy_print_log.py)
  spends one slot on them…" (value 1 kept); `:108-110` → the three lines "# ResetErrors resets every source at once,
  each FRAM-backed one still paying its own chunk write, so it far exceeds _http()'s 5s default. The value below is
  derived from the server's own _DEFAULT_OUTER_CAP_S; README.md has the derivation and SPECIFICATION.md Part C.7 the
  real-hardware measurements." (gap pass: "BACKLOG item 24" goes with the item at U19, M_DOCS gap 2; "in turn" is
  false once the reset is concurrent, A.U11.31), with `# @tunable web.outer_cap_s = 15.0` on `_SERVER_OUTER_CAP_S`; `:115` → "a device wiring the most FRAM-backed
  sources still leaves ~10 before the budget"; `:122-124` → "100, not the 40 once used: a device with more instances
  settles longer after boot (digital_twin/README.md has the measurement)" (and the "once used" history clause cut if the
  cap counter flags it — the fact is the measurement). Tags (A.U8.20/A.U8.05/A.U8.14): `l2.ntp_unreachable_watch_s`,
  `l2.bus_fault_error_count`, `l2.bounded_fault_count`, `l2.wifi_scripted_failures`, `l2.soak_warmup_cycles`,
  `l2.soak_cycles`, `l2.mem_sample_interval_ms`, `l2.mem_trend_tolerance_sd_multiplier`, the poll steps, `l2.ceiling_rounds`,
  `l2.slot_release_wait_s`, and `gc.threshold_bytes` on the 32768 in `main()` — each with the value A.U35.25/.27 measure
  where they re-derive it. `_CURRENT_PASS_LABEL` becomes an attribute of one module state object (`_STATE.pass_label`),
  so no `global` statement remains; `contextlib.suppress`/`Path` forms where ruff's SIM105/PTH rules name a site. Renamed names in comments and messages (A.U10.37/A.U10.38):
  `:40` "captive_dns.py's DNSServer" → "asy_captive_dns.py's CaptiveDNS", `:65` `NotificationCoordinator` →
  `NotificationService`, `:68` `AsyFramManager` → `FRAMManager`, `:139`/`:941`/`:956`/`:969` `DNSServer` → `CaptiveDNS`,
  `:348` `system_service.py` → `asy_system_service.py`.
- **Resolved**: A.U28.27 offers a per-file PLW0603 entry "unless U27 passes it explicitly first" — the state object
  removes the `global` (agent decision AD-7, no ignore needed). A.U8.20's tags on `:680` and `:904` are not written:
  A.U25.38 removes both sleeps (A.U25.74 conflict table row 1).
- **Unit**: U27 (stages: U8 tags; U19 the `:108-110` comment, in the commit where A.U19.14 deletes BACKLOG item 24; U20
  `from __future__`; U25 state, matrix names; U27 header, types, imports; U35 measured values).
- **Depends**: M.SCR.016; A.U27.37 (`device_max_connections_by_name`, GEN); A.U2.03 (`tests/_error_codes.py`, TEST_HELP);
  A.U19.14/M.DOCS.063 (item 24 removed, its design in SPEC C.7), A.U11.31 (the concurrent reset) — gap pass.
- **Blast carried by**: Part N rows → A.U8.20/A.U8.05/A.U8.04/A.U8.14 (SPEC); `tests_scripts/test_comment_block_cap.py`,
  `test_import_placement.py` (pending list drops this file) → A.U27.28/A.U0.07 (TSC); `pyproject.toml` per-file entries →
  A.U28.27 (TOOL, none needed here); `host_typecheck.ini` `mypy_path` gains `scripts` → A.U27.27 (TOOL).
- **Kind**: code

### M.SCR.047 Twin-process plumbing through the shared module; fail closed
- **From**: A.U25.46 (helpers move), A.U27.01 (`TwinRun`, memory gate fails closed), A.U25.64 (1) (signal deaths named),
  A.U25.66 (`get("counter", -1)` at assertion sites; strict readers), A.U25.36 (1) (exit codes, reset line), A.U25.35 (3)
  (`public_destinations_refused=0` per run log), A.U35.05 (the gate's trigger proof — blast), A.U25.44 (launch-site guard
  — blast), A.SDEP.16 (W15 `TZ=UTC` in the child env — conditional).
- **Site**: `scripts/_digital_twin_ci_suite.py:171-627` (`_fail`, `_check`, log check, `_configured_max_connections`,
  `_http`, errcount helpers, `_spawn`, `_close_log_and_check_memory_safety`, `_shutdown`, `_wait_exit`, `_read_log`,
  parsers, DNS helpers).
- **Change**: the spawn/shutdown/wait/log/HTTP/errcount/reset-line/shutdown-line helpers are imported from
  `scripts/_twin_process.py` (M.SCR.016) and deleted here; `_configured_max_connections()` → a call of
  `device_max_connections_by_name(ctx.device)`. Kept here: `_fail`/`_check` (recording into the `Summary`,
  M.SCR.048), `_concurrent_get`, DNS query helpers, `_failure_events(entry)`, `_error_codes(entry)`, `_parse_mem_samples`
  (by offset, M.SCR.057), the source-constant reader (`ast` over `src/asy_system_service.py`, `src/asy_print_log.py` —
  the A.U10.37 names). Every run's log check: no marker (fail closed on a missing/empty/unreadable log), and
  `public_destinations_refused=0` from the shutdown line. Every `.get("counter", 0)` at an assertion site (`:999`,
  `:1019`, `:1028` and the scan's others) → `.get("counter", -1)`; assertion paths read `entry["history"]` from the
  strict readers' entries. A negative exit code not caused by the suite's own SIGKILL fails "the interpreter was killed by
  signal N (NAME) - a crash, not a failed check" with the log tail; the suite's own timeout returns
  `_EXIT_SUITE_TIMEOUT`.
- **Resolved**: —
- **Unit**: U27 (stages: U25 moves and checks; U27 `TwinRun`, types).
- **Depends**: M.SCR.016.
- **Blast carried by**: `tests_scripts/test_digital_twin_ci_suite_errcount.py`, `_ceiling.py`, `_soak.py` import the moved
  helpers from `_twin_process.py` → A.U25.46 (TSC); `test_memory_error_gate_agreement.py` → A.U27.01 (TSC); A.U35.05's
  planted-marker proof → procedure (U35).
- **Kind**: code

### M.SCR.048 `main()`: required device, per-pass state, routes, options, summary
- **From**: A.U25.48 (3) (`--device` required), A.U27.16 (`--logs-dir` default `digital_twin_ci_logs/<device>`),
  A.U25.35 (1)-(2) (`state_dir` per pass, `_archive_state`), A.U27.32 (routes from `build/generated_src/api/<device>.json`),
  A.U25.64 (2) (`--only`, `--repeat`), A.S0930.04 (`--device-toml`), A.U7.09 (summary block), A.U27.29 (`raise
  SystemExit(main())`), A.U27.15/M.TWIN.060 (MICROPYPATH from `micropypath.toml`, site path), A.U27.39 (port locks held
  by the caller — inherited), A.U8.14 (32768 tag), A.U24.68 (the same required-argument rule — blast), A.U7.24
  (`run_suite()` call list read by AST — blast).
- **Site**: `scripts/_digital_twin_ci_suite.py:1239-1326` (`run_suite`, `_drivers_in_plan`, `main`), `:147-162`
  (`RunContext`).
- **Change**: `RunContext` gains `state_dir: Path`, `routes: tuple[str, ...]` (every `GET` route of the device's API
  reference), `site_dir: Path` (`build/generated_html/<device>`), `generated_dir: Path` (default `build/generated_src`),
  `micropypath: str` (the twin layout with `frozen_modules` → `site_dir`, and `generated_dir` in front when it is not
  the default). CLI: `--device NAME` (required), `--micropython-bin`, `--logs-dir` (default
  `digital_twin_ci_logs/<device>`), `--only RUN[,RUN…]` (names as `run_suite()` lists them: `1 … 13`, `5b`, `5c`, `11b`;
  unknown → exit 2), `--repeat N` (≥ 1), `--device-toml PATH` (generate that TOML's outputs into
  `<logs-dir>/generated/` through `scripts/_generate_sensortask_modules.py --device-toml PATH --out-dir …` and boot from
  there). A missing wiring plan, API reference or site → recorded `failed` with its build hint, block printed, exit 1.
  Two passes (`-1`, then `# @tunable gc.threshold_bytes = 32768` `32768`), each with `logs_dir/<pass label>/` and its own
  `state/`; `_archive_state(ctx, label)` moves a non-empty `state/` to `state_archive/NN_before_<label>/` and recreates
  it (the only clearing point; seven call sites with their labels). `_check()`/`_fail()` record into one `Summary`
  (unit **checks**, grouped by pass label); a pass with zero checks recorded is `vacuous`; `run_suite()` in
  `try/finally` records "suite aborted: <type>: <exc>" and re-raises; `main()` prints the block on every exit
  (`Levels: L2 (<device>)`, `GC stage: both`) and ends `raise SystemExit(main())`. The port locks (53, 18080) are taken by
  `run_digital_twin_ci.sh` and inherited; run directly, `main()` takes them through `_port_lock.port_lock()`.
- **Resolved**: A.U7.09's `retried` filing for Run 11's second attempt is dropped: A.U27.17 removes the attempt (one
  verdict) — settled by OR37.a (2).
- **Unit**: U27 (stages: U25 device, state, `--only/--repeat`; S0930 `--device-toml`; U7 block).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.04 in U25.
- **Depends**: M.SCR.002, M.SCR.013, M.SCR.016, M.SCR.068 (single-device generation mode), A.U19.20 (API reference, GEN).
- **Blast carried by**: `tests_scripts/test_digital_twin_ci_suite_state.py` (state archived not deleted, labels) →
  A.U25.35 (TSC); `test_level_containment.py` reads `run_suite()`'s calls → A.U7.24 (TSC); `tests_scripts/test_tool_help.py`
  (`--help` exit 0) → A.U7.19 (TSC); `digital_twin/README.md` "Automated CI suite" → A.U25.65/A.U36.513 (TWIN/DOCS).
- **Kind**: code

### M.SCR.049 Run 1: read and keep every log before the clear; nothing logged on a normal boot, NTP synced
- **From**: A.U35.38 dropped (OR140.a (13): no NTP tolerance, the twin's local NTP responder instead, A-C review fold),
  A.U35.37 (scan: tolerated codes only with an in-place reason), A.U6.21 (`UTCTime`/`LocalTime` null
  while unsynced — the gap its blast names), A.U25.35 (archive per run), A.U2.03, A.U10.40 (key names), A.U11.31
  (`ResetErrors` answers per field — blast: `Valid`), A.U36.004 (`:84, :983` keep their rule text — blast).
- **Site**: `scripts/_digital_twin_ci_suite.py:632-665` (`_run_1_baseline`).
- **Change**: after serving, one `GET /status` and one `GET /system` read together: `errcount` written to
  `<pass>/runs/run1_errcount.json`; every module's history has no E and no W entry (no tolerance list: the twin's
  local NTP responder answers, OR140.a (13)); while `NTPSynced` is false, `UTCTime` and `LocalTime` are `null`; then
  `/status` is polled (bounded by NTP's own first-sync deadline, read from the generated module) until `NTPSynced` is
  true, after which both are non-null; then the `ResetErrors` PUT as today (answer `Valid`, timed against
  `_RESET_ERRORS_BUDGET_S`). The `:663` state check reads `ctx.state_dir`.
- **Resolved**: A.U6.21's L2 clause ("existing twin CI boot log … U25 checks") was carried by no U25 action — added here
  (gap closed in-cluster, agent decision AD-8).
- **Unit**: U35 (after U25's NTP responder).
- **Depends**: M.SCR.016, M.SCR.048; [fold F16 M_TWIN] (the twin's local NTP responder); product fixes a clean boot needs
  (M.SRC_CORE.043: an absent file's one defaults write prints, never logs — SRC; A.U3.09 dropped with A.U3.04,
  OR140.a (7)).
- **Blast carried by**: `test_digital_twin_generated_boot.py` checks the same clean boot → M.TSC.086; `audit/b3/review.md`
  classification → A.U35.37 (procedure).
- **Kind**: test

### M.SCR.050 Run 2: wait for the verbose lines, not a fixed sleep
- **From**: A.U25.38 (`:680` → log poll), A.U10.40 (`MeasInt` → `MeasInterval` in the PUT bodies `:650-677`), A.U8.20
  (no tag on the removed sleep).
- **Site**: `scripts/_digital_twin_ci_suite.py:666-688`.
- **Change**: the persisted-settings PUTs use the renamed keys (`MeasInterval`, and every other key A.U10.40 renames that
  this run sends); `time.sleep()` at `:680` → poll the run log until `_count_verbose_log_lines() >=
  _MIN_VERBOSE_LOG_LINES` or the deadline (tagged poll step).
- **Resolved**: —
- **Unit**: U25 (stage U10: key names).
- **Depends**: M.SCR.047.
- **Blast carried by**: —
- **Kind**: test

### M.SCR.051 Run 3: the combined-fault escalation cell, per instance, in both CRC modes
- **From**: A.U25.36 (2) (escalation to a simulated reset), A.U25.37 (instances, `_SUSTAINED_FAULT`, `fram:silent`,
  `uart_link:silent`, `_LEFT_OUT`), A.U25.18 (`fram:write` gone), A.U35.28 (3) (persisted-log rate rides this cell),
  A.S0930.04 (4) (the `uart_link` cell rerun on a CRC16 TOML — run by the runner through `--device-toml`), A.U16.17
  (holds: RDID before the fault), A.U15.R01/R03/R04 (rung behaviour — blast, holds), A.U11.03/.05 (reset path — blast).
- **Site**: `scripts/_digital_twin_ci_suite.py:50-86`, `:614-629`, `:690-719`, `:1263-1273`.
- **Change**: `_SUSTAINED_FAULT = {"scd30": "writeto", "sgp40": "writeto", "bmp3xx": "writeto", "isl29125": "writeto",
  "fram": "silent", "uart_link": "silent"}` iterated over every instance key of the wiring plan (`<driver>_<name_ext>`);
  Run 3 boots with all of them; asserts every faulted module recorded an E entry while the process lived (polls stop once
  the process exits), then `exit == _EXIT_SIMULATED_RESET`, `reset_count == 1`, `would_have_triggered_count == 0`, no
  marker; the twin FRAM chip's write count at exit ≤ `rate.persisted_log` × the window (A.U35.28). `_LEFT_OUT` (module
  table, each with its reason, A.U25.37 (2)) is printed once per pass. `_drivers_in_plan()` → instance keys from
  `plan["instances"]`. When run with `--device-toml`, the run's outcome is asserted identically and the suite checks the
  generated module constructs every link bus with `crc=CRC16()` (source text of the generated module).
- **Resolved**: —
- **Unit**: U35 (stages: U25 the cell; S0930 the CRC16 rerun; U35 the rate assertion).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.04 in U25.
- **Depends**: M.SCR.047; M.TWIN (fault vocabulary, `fram:silent`, `uart_link:silent`, exit codes); A.U25.37's L0 matrix
  completeness test (TSC).
- **Blast carried by**: `tests_scripts/test_digital_twin_ci_suite_matrix.py` (every chip-fake op in the matrix or
  `_LEFT_OUT`) → A.U25.37 (TSC); `digital_twin/README.md:478-482` → A.U25.37 (TWIN); `audit/b3/load.md` → A.U35.28.
- **Kind**: test

### M.SCR.052 Run 4: the escalation's reset reason and the cleared record
- **From**: A.U25.36 (2) (Run 4 asserts `ResetReason` = supervisor-escalation code read by AST; `mem_backup: r0` all
  zero), A.U11.05 (blast), A.U36.004 (no CLAUDE.md citation — blast).
- **Site**: `scripts/_digital_twin_ci_suite.py:721-763`.
- **Change**: the fault-free relaunch keeps its persistence sweep and adds: `GET /status` `ResetReason` == the
  supervisor-escalation code (`ast` read from `src/asy_system_service.py`), and the relaunch's shutdown line shows
  `mem_backup: r0=0 0 0 0`.
- **Resolved**: —
- **Unit**: U25.
- **Depends**: M.SCR.051.
- **Blast carried by**: —
- **Kind**: test

### M.SCR.053 Run 5: the bounded fault aimed at measure reads, counts re-derived
- **From**: A.U25.36 (4) (failure-event counting), A.U15.R02 (corrected by AC_NOTES 31: setup probes and the heater-off
  rung consumed the faults), M.TWIN.014 (keyed faults: `sgp40:readfrom_into:3:0x260F`), A.U25.38 (`:779` → two observed
  read cycles), A.U36.544 (`:768` device-set claim goes), A.U2.03/A.U2.15 (codes by catalog name), the ladder's W codes
  (A.U10.R01 — blast).
- **Site**: `scripts/_digital_twin_ci_suite.py:765-791`.
- **Change**: boots with `--fault sgp40:readfrom_into:3:0x260F` (three faults on measure-raw reads only; setup's serial
  read and the heater-off rung untouched); waits until `_failure_events(SGP40) == _BOUNDED_FAULT_COUNT`; asserts the E
  codes are exactly SGP40's measure-read failure code and every W code is a ladder wrnno or one of SGP40's own storage
  warnings, each looked up by catalog name; then polls `GET /measurements` until the SGP40 timestamp has advanced twice and
  asserts `_failure_events` unchanged. The expected names are derived at landing from the end-state driver (A.U15.R02's
  ladder) and written as named constants with a one-line derivation each. `:768` "SGP40 is on every real device (Part
  L.3)" → "Run 5 runs where the device wires an SGP40 (C.8)"; a device without one records a named skip of Run 5/5b.
- **Resolved**: A.U15.R02's twin-CI blast (heater-off consumes one `writeto` fault) is wrong (AC_NOTES 31); the keyed
  read fault replaces it (M.TWIN.014, M_TWIN gap "SCR").
- **Unit**: U25 (latest of U15/U25 constituents).
  A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3).
- **Depends**: M.SCR.047; M.TWIN.014.
- **Blast carried by**: SPEC/README text of Run 5 → M.TWIN README entry (TWIN).
- **Kind**: test

### M.SCR.054 Runs 5b and 5c: the exact ring, the product reboot, nothing lost
- **From**: A.U25.36 (3)-(4) (5b exact ring; 5c `SystemCmd: reboot`, mempause/sleep go), A.S0930.38 (1)-(2)
  (`_commanded_reset_deadline_s()`, the shutdown sequence), A.U25.37 (5c chain per instance), A.U25.38 (`:869` goes,
  `:901-904` deleted), A.U27.08 (`:891` text), A.U25.64 (3) (repro of the grkizi SIGSEGV — execution step), A.U25.57
  (auto-unpause is its own run, TWIN — blast).
- **Site**: `scripts/_digital_twin_ci_suite.py:793-919`.
- **Change**: 5b asserts the restored SGP40 history is `[]` or equal to Run 5's final entry, counter 0 or ≥ Run 5's.
  5c: chain per bus-attached instance (`_healthy_store_fault_drivers` over instances); its commanded reboot is `PUT
  /system {"SystemCmd": "reboot"}` → `_wait_exit()` expects `_EXIT_SIMULATED_RESET` within `_commanded_reset_deadline_s()`
  (`_RESET_DELAY + _TASK_CHECK_TIME`, both read by `ast`, plus a tagged margin `l2.commanded_reset_margin_s`); 5c-b asserts
  `ResetReason` == the REST-reboot code (3) and the sweep (nothing lost); SGP40 counts in the `_failure_events` form. The
  `mempause` PUT, `_wait_for_mem_paused()`, the `:869` sleep and the `:901-904` settle go. `:891` → "every uart_link
  instance".
- **Resolved**: —
- **Unit**: U25 (SUPP_owner_0930's L2 half, after A.U25.36 and A.U25.55 in the same unit; LEAD/R32 'U25 (L2)').
- **Depends**: M.SCR.053, M.SCR.047.
- **Blast carried by**: A.U25.64 (3)'s 50 × 2 repro run → procedure (U25 execution); BACKLOG note if not reproduced →
  A.U25.64 (DOCS).
- **Kind**: test

### M.SCR.055 Runs 6-9: renamed keys, the capability check, strict counters
- **From**: A.U25.34 (2) (Run 7 capability check, bind-failure report), A.U10.40 (`NTP_Host` → `NTPHost`, `NtpSynced` →
  `NTPSynced` in `:1002-1003` and readers), A.U10.38 (class name in the bind-error text: `CaptiveDNS`), A.U25.66 (`:999`,
  `:1019`, `:1028`), A.U2.03/A.U2.15 (Run 9's NTP code by name), A.U36.004 (`:983` rule text stays — blast), A.U18.01/.03
  (DNS reply form — blast via `_try_dns_query`, holds).
- **Site**: `scripts/_digital_twin_ci_suite.py:921-1035`.
- **Change**: Run 7 first checks the binary's `CAP_NET_BIND_SERVICE` (`/sbin/getcap` when present, else
  `os.getxattr(bin, "security.capability")`) and fails "the interpreter lacks CAP_NET_BIND_SERVICE: Run 7's DNS server
  cannot bind port 53" instead of waiting; a missing answer reports whether the run log holds the captive DNS bind-error
  text. Runs 8/9 PUT `/networking {"NTPHost": …}` and read `NTPSynced`; Run 9 compares NTP's history with the
  no-reply code looked up by catalog name. Counter reads at `:999`, `:1019`, `:1028` default to -1.
- **Resolved**: —
- **Unit**: U25 (stage U10: key and class names).
  A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3).
- **Depends**: M.SCR.047.
- **Blast carried by**: `digital_twin/README.md:761-767` → A.U25.65 (TWIN).
- **Kind**: test

### M.SCR.056 Run 10: one bounded hang per bus-attached instance
- **From**: A.U25.37 (2) (`_HANG_MATRIX`), A.U25.13/.14 (new hang ops — TWIN, blast).
- **Site**: `scripts/_digital_twin_ci_suite.py:1037-1055`.
- **Change**: `_HANG_MATRIX` (driver → op) yields one process per bus-attached instance: `--hang <instance>:<op>:12
  --duration 15`, asserting `would_have_triggered_count >= 1` and no marker; each in fresh state (`_archive_state` label
  `run10 <instance>`).
- **Resolved**: —
- **Unit**: U25.
- **Depends**: M.SCR.047.
- **Blast carried by**: L0 matrix test → A.U25.37 (TSC).
- **Kind**: test

### M.SCR.057 Run 11: one verdict, samples by log position, calibrated window
- **From**: A.U27.17 (one attempt, `_SoakRun`), A.U35.26 (byte-offset window, `ticks_ms` stamps), A.U35.27 (window and
  multiplier calibrated against a planted leak), A.U35.25 (sampler interval decision), A.U27.32 (routes: every GET plus
  `/`), A.U7.09 (retried filing — dropped), A.U27.08 (`:122-124`, in M.SCR.046).
- **Site**: `scripts/_digital_twin_ci_suite.py:1110-1236`.
- **Change**: `_run_11_soak()` runs one attempt (`run11_soak.log`), prints today's diagnostics line, and decides with
  `_check(condition=trend <= tolerance, …)`; the attempt-2 block, `attempt_label` and every "retry" word go;
  `_SoakAttempt` → `_SoakRun` ("One boot's Run 11 raw results"). The cycle window is the log's byte size at start and end
  of the cycles; samples are `MEM_SAMPLE` lines starting in `[start, end)`; `_parse_mem_samples()` returns `(offset,
  free)`; fewer than one sample per quarter fails (holds). Endpoints = `ctx.routes` plus `/`. `_SOAK_CYCLES`,
  `_MEM_TREND_TOLERANCE_SD_MULTIPLIER`, `_MEM_SAMPLE_INTERVAL_MS` take the values A.U35.25/.27 measure (Part N rows); if no
  window separates leak from noise within the job budget, the verdict fails closed and the owner item enters BACKLOG
  (A.U27.17 docs).
- **Resolved**: A.U7.09 (attempt 2 filed `retried`) vs A.U27.17 (no attempt 2) — A.U27.17 settled by OR37.a (2).
- **Unit**: U35 (stage U27: one attempt; U35: offsets, calibration).
- **Depends**: M.SCR.047; M.TWIN `_mem_sampler` (`ticks_ms`, conditional `gc.collect()`).
- **Blast carried by**: `tests_scripts/test_digital_twin_ci_suite_soak.py` (offset join, one attempt) → A.U27.17/A.U35.26
  (TSC); SPEC E.9 → A.U27.17 (SPEC); `timing.md` → A.U35.25/.27 (procedure).
- **Kind**: test

### M.SCR.058 Run 11b: every GET route at the full ceiling
- **From**: A.U27.32 (routes derived), A.U25.38 (`:1079` kept, tagged, reason), A.U8.05 (`_SLOT_RELEASE_WAIT_S`),
  A.U36.532 (H.7.1 citation holds — blast), A.U24.36 (bodies vs uncontended — blast for the suite: its burst checks
  completeness), A.U19.24 (EAGAIN hammer is L1 — blast).
- **Site**: `scripts/_digital_twin_ci_suite.py:1058-1108`.
- **Change**: the burst uses `ctx.routes` (so `/notification` and `/system` join); comment "the heaviest real
  endpoints…" → "every GET route the device serves"; `time.sleep(_SLOT_RELEASE_WAIT_S)` (`# @tunable
  l2.slot_release_wait_s = 1.0`) with "# a readiness probe would occupy a max_connections slot, the property under test".
- **Resolved**: —
- **Unit**: U27.
- **Depends**: M.SCR.048.
- **Blast carried by**: —
- **Kind**: test

### M.SCR.059 Run 12: reset reasons reachable at L2
- **From**: A.U25.55, A.S0930.27 (1) (codes 7 and 8 join), A.S0930.38 (1) (bootloader wait uses the deadline helper);
  gap pass: A.U30.19 (code 20, GAPS_G3 hand-off 3 (a), Table B B11).
- **Site**: new `_run_12_reset_reasons` after Run 11b in `run_suite()`.
- **Change**: as A.U25.55 (a)-(c): power-on code; `bootloader` → `_EXIT_SIMULATED_BOOTLOADER` within
  `_commanded_reset_deadline_s()`, relaunch reads the bootloader code, region 0 zero, a SIGINT relaunch reads power-on;
  codes read by `ast` from `src/asy_system_service.py`, the list including 7 (config reset) and 8 (FRAM erase) asserted
  in Run 13; (d) code 20 (A.U30.19; gap pass, GAPS_G3 hand-off 3 (a)): a launch with `--fault <instance>:<op>:stack` on
  the first bus-attached instance of the device's wiring plan and one of its read ops (M.TWIN.044's form; a device
  wiring no bus driver skips the cell by name) exits `_EXIT_SIMULATED_RESET` (3) through the supervisor's escalation, and
  the relaunch reads `ResetReason` 20 (`_RR_STACK_EXHAUSTED`, read by `ast` like the others).
- **Resolved**: —
- **Unit**: U25 (SUPP_owner_0930's L2 half, after A.U25.36 and A.U25.55 in the same unit; LEAD/R32 'U25 (L2)'); cell (d) with U30 (A.U30.19), after M.TWIN.044's `stack` branch.
- **Depends**: M.SCR.054; M.TWIN.044/.045 (the `stack` fault).
- **Blast carried by**: twin fidelity row (bootloader carry-over) → M.TWIN README (TWIN).
- **Kind**: test

### M.SCR.060 Run 13: the system commands end to end
- **From**: A.S0930.27 (0)-(1), A.S0930.38 (3), A.U35.02 (both stages — procedure); OR136.a (1), OR138.a (1)-(2) (A-C
  review fold: the relaunch writes each file once; damaged files are listed and deleted unread).
- **Site**: new `_run_13_system_commands` after Run 12.
- **Change**: FRAM evidence first (errcount JSON and a copy of the pass's FRAM state file into the run's archive) before
  any `erasefram`; cells in fresh state: `resetconfig` → `Valid`, reset exit with no `config_*.cfg` left in the config
  dir; the relaunch writes each schema-backed file exactly once, holding its schema defaults (OR136.a (1): the
  config dir's files counted against the build's schema-backed stores, none for a command-only schema), Hostname
  from the TOML, `ResetReason` 7, `ConfigFaults` empty; a damaged-file cell: a launch whose config dir holds one module's
  file as bytes that are not JSON and another's with a key out of range → `/status` `ConfigFaults` names both, the
  corrupt file's bytes unchanged after the boot, the bad-key file repaired by one write (and still listed for that
  boot); then `resetconfig` deletes both without reading them, and the relaunch shows `ConfigFaults` empty and every
  file at its defaults (OR138.a (1), (2)); `erasefram` → `Valid`, reset exit, every FRAM-backed counter 0, `ResetReason` 8; the
  near-miss list → `Invalid`, serving continues; `PUT /system {"DebugLevel": 4}` then `reboot` → the S1-S4 step lines in
  order, no S5, `machine reset: kind=reset`, `ResetReason` 3, `DebugLevel` 4 kept, every FRAM history ⊇ before; the same
  for `bootloader` (`kind=bootloader`, code 4); `would_have_triggered_count == 0` on every launch. The states and hangs are
  the harness's (M.SCR.018 (k)).
- **Resolved**: —
- **Unit**: U25 (SUPP_owner_0930's L2 half, after A.U25.36 and A.U25.55 in the same unit; LEAD/R32 'U25 (L2)'); the
  first-write and damaged-file cells after U11's `ConfigManager` change and U20's `/status` field and delete path.
- **Depends**: M.SCR.059; M.SRC_CORE.043 (OR136.a), [fold F03 M_SRC_CORE] (the `ConfigFaults` state), [fold F03 M_GEN]
  (the generated `/status` field and the delete path that never reads).
- **Blast carried by**: product commands → A.S0930 SRC actions (SRC_CORE); `_LOG_EVENT` level read by `ast` from
  `src/asy_print_log.py`.
- **Kind**: test

## scripts/run_digital_twin_ci.sh

### M.SCR.061 Twin CI runner: required device, archive, locks, harness, CRC16 rerun
- **From**: A.U25.48 (required device, usage), A.U27.16 (archive per device; forward extra args), A.U27.12 (`unix_port_ensure
  standard`), A.U27.33 (`require_device`, convention), A.U27.38 (harness after the suite, both GC stages, worse exit),
  A.U24.69 (locks 53 and 18080), A.S0930.04 (4) (CRC16 rerun of Run 3's link cell), A.U25.35 (4) (stale clean comment
  goes), A.U25.55 ("14-run" goes), A.U7.19 (help), A.U7.01/.03/.18 (E.6.1 command, lower-levels caller — blast),
  A.U36.024/.511/.547 (docs — blast), A.SDEP.16 (W15 conditional), A.U28.06 (CI matrix from `devices` — blast), A.U28.08
  (no `continue-on-error` on its CI step — blast), A.U17.18/A.U8.20/A.U7.09/A.U6.02/A.U6.03/A.U27.11/A.U27.35/A.U21.22/
  A.U23.38/A.U24.53/A.U7.20 (interfaces it calls, unchanged — blast), A.SDEP.02/.25, A.U0.06, A.U37.07 (run as procedure).
- **Site**: `scripts/run_digital_twin_ci.sh:1-59`.
- **Change**: header (3 lines): "L2 for one device: archives that device's previous logs, builds its site and generated
  modules, runs scripts/_digital_twin_ci_suite.py at both GC stages, then the host-side scenario harness at both, and
  exits with the worse result. Reference: digital_twin/README.md "Automated CI suite"; ci.yml runs it once per device."
  Usage `scripts/run_digital_twin_ci.sh <device> [suite args…]`; `--help` exit 0; `require_device "$1"` (exit 2);
  `TZ=UTC` kept (W15 conditional). Trap (one, armed first) releases the port locks; `port_lock_take 53
  run_digital_twin_ci; port_lock_take 18080 run_digital_twin_ci`. `uv run --no-sync scripts/_archive_evidence.py
  --runner "digital_twin_ci_$device" "digital_twin_ci_logs/$device"`. `source scripts/_unix_port.sh; unix_port_ensure
  standard; micropython_bin="$(unix_port_bin standard)"`; capability grant unchanged (comment ≤ 3 lines; "Run 7's and the
  harness's port-53 DNS server"). `scripts/build_website.sh "$device" "build/generated_html/$device/frozen_html.py"`;
  `uv run --no-sync scripts/_generate_sensortask_modules.py`; suite `uv run --no-sync scripts/_digital_twin_ci_suite.py
  --micropython-bin "$micropython_bin" --device "$device" --logs-dir "digital_twin_ci_logs/$device" "$@"` (exit kept);
  then, when `devices/$device.toml` declares a `uart_link`, the CRC16 rerun: `derived="digital_twin_ci_logs/$device/crc16/$device.toml"`
  written by `sed` appending `crc = "crc16"` after every `driver = "uart_link"` line, checked to hold as many `crc =
  "crc16"` lines as `driver = "uart_link"` lines and no other `crc =` line (else exit 1 naming the TOML), then the suite
  with `--device-toml "$derived" --only 3 --logs-dir "digital_twin_ci_logs/$device/crc16"`; then the harness twice,
  `--gc-threshold -1` and `32768`, `--exclusive-port-53`, `--logs-dir "digital_twin_ci_logs/$device/scenarios/<stage>"`.
  Every step always runs once the build succeeded; the exit is the worst of the suite, the CRC16 rerun and the two harness
  runs. The `:10-11` clean comment and "14-run" go.
- **Resolved**: A.U27.16 names the archive runner `digital_twin_ci`; `_run_lower_levels.sh` runs every device in turn and a
  shared keep-3 would drop earlier devices' evidence — the runner name carries the device (agent decision AD-9). The
  derived CRC16 TOML is built by `sed` (A.S0930.04 leaves the method open; agent decision AD-10).
- **Unit**: U27 (A.S0930.04's CRC16 rerun on U27's runner; stages U24, U25 as listed). Stages: U24 (locks), U25 (device required, comment), U27 (archive, probe, harness, convention).
  A-C2 step order: A.U24.53's part lands in U25, not U24 (it follows A.U24.53's own change, which lands in U25).
- **Depends**: M.SCR.003, M.SCR.007, M.SCR.008, M.SCR.012, M.SCR.017, M.SCR.048, M.SCR.071, M.SCR.068.
- **Blast carried by**: CI `digital-twin-e2e` (one leg per device from the `devices` job; artifact path
  `digital_twin_ci_logs/` unchanged; no `continue-on-error`) → A.U28.06/A.U28.08 (TOOL); L0
  `tests_scripts/test_run_digital_twin_ci_sh.py` (archive keep-3 per device, extra args reach the suite, harness after
  the suite, worse exit, CRC16 rerun only for a `uart_link` device) → A.U27.16/A.U27.38/A.S0930.04 (TSC);
  `digital_twin/README.md:388-395`, root README → A.U36.024/.511 (DOCS, TWIN); SPEC E.6.1 command → A.U7.01 (SPEC).
- **Kind**: code

## scripts/run_unix_port_integration.sh

### M.SCR.062 Manual twin runner: required device, probe, own site path, port lock
- **From**: A.U24.68 (device required, usage, valid names), A.U27.08 (`:4` text), A.U27.12, A.U27.15/M.TWIN.060 (twin path
  from `micropypath.toml`, site swap), A.U27.33 (value check), A.U27.39 (port-53 lock), A.U0.31 (`:6`, `:24` owner tags),
  A.U25.32 (manual run persists by default — doc), A.U7.19, A.SDEP.16 (W15), A.U36.024/.511/.547 (docs — blast),
  A.U20.28/A.U25.44 (plan path passed on; launch guard — blast), A.U6.02/A.U6.03/A.U27.11/A.U27.35/A.U21.22/A.U23.38/
  A.SDEP.08 (interfaces — blast).
- **Site**: `scripts/run_unix_port_integration.sh:1-78`.
- **Change**: header (3 lines): "Manual twin launch of one device: digital_twin/run_generic_integration.py under the real
  Unix port, separate from scripts/test.sh (owner, 2026-08-13). With no further flags it serves on localhost:8080
  forever (owner, 2026-08-13: browser-reachable, escalation watchable), its chip state persisting in digital_twin/." A
  second paragraph (≤ 3 lines) states why its path needs `ext` and not `tests` (twin layout of `scripts/micropypath.toml`).
  Usage `scripts/run_unix_port_integration.sh --device <name> [flags forwarded to the twin]`; `--help` exit 0; parse loop
  `--device` without a value → "--device needs a device name", exit 2; `require_device "$device"` (exit 2, valid names
  listed). One trap; `port_lock_take 53 run_unix_port_integration`. `unix_port_ensure standard`; capability grant (its
  comment `:59` "The twin's DNSServer binds" → "The twin's captive DNS server binds", A.U10.38);
  `scripts/build_website.sh "$device" "build/generated_html/$device/frozen_html.py"`; generation (`uv run --no-sync`);
  launch with `MICROPYPATH` = `micropypath twin` with `frozen_modules` replaced by `build/generated_html/$device` (one
  comment line saying why: the device's own site, without touching `scripts/test.sh`'s `frozen_modules/`).
- **Resolved**: —
- **Unit**: U27 (stage U24: required device).
- **Depends**: M.SCR.007, M.SCR.008, M.SCR.009, M.SCR.012, M.SCR.071.
- **Blast carried by**: L0 `tests_scripts/test_tool_help.py` and a device-argument test (missing value, unknown device →
  exit 2) → A.U24.68/A.U27.33 (TSC); `digital_twin/README.md:158-163` → A.U36.024 (TWIN/DOCS); README `:425-439` →
  A.U36.511 (DOCS); A.U25.44's launch-site guard reads the `micropypath` call (TSC).
- **Kind**: code

## scripts/cross_browser_smoke.mjs

### M.SCR.063 Smoke over every device, a probe per device, engines required in CI
- **From**: A.U6.11 (device loop, probe, scoped selectors, labels), A.U28.17 (`--require-all-engines`, verdict in the probe
  module), A.U8.18 (counting proxy, `CONNECTIONS_PER_PAGE_LOAD`), A.U8.21 (tags), A.U7.19 (`--help`), A.U36.038 (D.15
  function order), A.U10.40 (`MeasInt` probe literal goes with the picker), A.U23.15/A.U23.42 (Apply re-enabled,
  `aria-expanded` — blast, hold), A.U23.49/A.U6.30 (comment literal `:15` — placed in A.U6.11), A.U24.48 (disable reasons
  present — DONE-AT-HEAD), A.U25.74/A.U33.04/A.U33.09/A.U28.43/A.U8.24 (rows — blast).
- **Site**: `scripts/cross_browser_smoke.mjs:1-60`, `:205-236`, `:390-505`.
- **Change**: header (3 lines): "Boots the twin of every device of devices/*.toml in turn and drives that device's real site
  through WebKitGTK, Firefox, Edge and Playwright's Chromium at two viewports: nav, drawer, the probe field, Apply, the
  applied value read back. --require-all-engines (CI) fails a missing engine; without it a missing engine is a warning."
  `--help` exit 0; any other argument exit 2. Devices from `devices/*.toml` minus `zz_test_` (sorted); per device the
  probe from `pickProbe()` over `build/generated_src/definitions/<device>.json`; probe scripts scoped
  `[data-group-key="<g>"] [data-field-key="<f>"]`; values `min + 1 + (counter % (max - min - 1))` with one counter across
  all checks; labels `${device} ${engine} (${viewport})`. Each engine's page load goes through a counting TCP proxy
  (`net` server in front of the twin's port) printing `connections per page load (<device> <engine>): <n>`; `// @tunable
  web.connections_per_page_load = 2` above `const CONNECTIONS_PER_PAGE_LOAD = 2`; a higher count fails. The verdict comes
  from `engineVerdict()`; the closing line counts `passed/ran` plus `skipped: N`. Budgets tagged
  (`l0.live_twin_ready_timeout_ms`, `l0.live_twin_shutdown_timeout_ms`, `l0.smoke_h1_wait_ms = 10000`, one
  `l0.cross_browser_smoke_poll_ms` per poll step). Top-level functions in D.15 order (pure move, last in its unit).
- **Resolved**: A.U6.11's per-device MICROPYPATH and A.U27.15's shared path meet in M.SCR.064's launch.
- **Unit**: U36 (A.U36.038's reorder lands last). Stages: U6 (device loop, probe), U8 (proxy, tags), U28 (engine flag).
- **Depends**: M.SCR.023, M.SCR.064; `build/generated_html/<device>` from `npm run build:site` (M.WEB.071).
- **Blast carried by**: `ci.yml:309` → `node scripts/cross_browser_smoke.mjs --require-all-engines` → A.U28.17 (TOOL);
  `tsconfig.node.json` include → A.U28.25 (WEB/TOOL); L0 `test_cross_browser_smoke_probe.py` → A.U6.11/A.U28.17 (TSC); the
  ESLint order rule covers `scripts/*.mjs` → A.U36.038 (WEB/TOOL); SPEC H.7 "Cross-browser coverage" → A.U36.517 (SPEC);
  Part N rows → A.U8.18/A.U8.21 (SPEC).
- **Kind**: code

### M.SCR.064 Smoke twin launch: the shared JS twin module, per-run state, port lock, own display
- **From**: A.U7.21/A.U7.23 (markers, drained output), A.U25.32 (own `--config-dir`, three `""` state paths, no
  `rmSync` of `digital_twin/config`), A.U27.12 (binary via `_unix_port.sh check standard`), A.U27.15 (twin path), A.U27.39
  (port-53 lock via `tests_js/_port_lock.js`), A.U28.18 (`startVirtualDisplay` with `-displayfd 3`), A.U28.26
  (lock-pinned Chromium first, sandbox fallback), A.U25.44 (launch-site guard — blast), A.U20.28 (plan path — blast),
  A.SDEP.16 (W15 conditional), A.SDEP.04/.19 (refreshed engines — blast), A.U28.08/.21/.25 (rows — blast), M_WEB gap 6(c).
- **Site**: `scripts/cross_browser_smoke.mjs:10-49`, `:60-200` (`spawnTwin`, `stopTwin`, display helpers), `:390-397`,
  `:445-456`.
- **Change**: the smoke imports `spawnTwin`, `stopTwin`, `waitUntilServing` from `tests_js/_twin_process.js` (M.WEB.082, the
  one twin-launch frame: binary probe, twin `MICROPYPATH` with the device's site, drained output, marker scan, port-53
  lock, per-run config dir) and deletes its own copies, `TOOLCHAIN_DIR`, `MICROPYTHON_BIN`, the `existsSync` check, the
  local `MICROPYPATH` literal and the `rmSync` of `digital_twin/config`. `main()` takes the port-53 lock once before the
  device loop (released on `process.on("exit")`) and passes it to the frame (or the frame's own acquisition is
  re-entrant for the same process). `startVirtualDisplay(timeoutMs)` replaces `nextDisplayNumber`/`spawnVirtualDisplay`/
  `waitForVirtualDisplay` as A.U28.18 states (fallback `:<n>` from 90 with `-displayfd 3` only if the first run shows Xvfb
  needs a display argument). Chromium leg: the lock-pinned Playwright Chromium unless absent and the sandbox path exists
  (comment "same fallback rule as vitest.config.js").
- **Resolved**: M_WEB gap 6(c) leaves reuse of `_twin_process.js` to SCR — reused (OR24 "one material"; agent decision
  AD-11). That module must swap `frozen_modules` for `build/generated_html/<device>` (A.U6.10 (1)); M.WEB.061 omits it —
  gap to WEB below.
- **Unit**: U28 (stages: U7 markers, U25 config dir, U27 probe/path/lock).
- **Depends**: M.WEB.082, M.WEB.061 (+ WEB gap 1), M.WEB.075/.078/.079.
- **Blast carried by**: `tests_scripts/test_memory_error_gate_agreement.py` (the smoke reaches the markers through
  `_twin_process.js`) → A.U7.23 (TSC); `test_twin_never_needs_tests_on_its_path.py` → A.U25.44/A.U27.15 (TSC); the
  no-`rmSync`-outside-tmp check → A.U24.53 (TSC); SPEC H.7 Xvfb text → A.U28.37 (SPEC).
- **Kind**: code

## scripts/build_firmware.py

### M.SCR.065 Firmware CLI: device TOML, no-autostart, lock, kept work dir, one error contract
- **From**: A.U27.08 (usage, help), A.S0930.06 (1) (`--device-toml`), A.U27.36 (`--no-autostart`, default output),
  A.U21.08 (`--toolchain-dir` resolved), A.U21.22 (toolchain lock; refuse a dir without a toolchain record), A.U21.03
  (print the record's `built_ref`/`micropython_commit`), A.U27.35 (persistent `build/firmware/<device>/`, wiped at start),
  A.U27.29 (`BuildError` propagates; one catch in `main()`; `raise SystemExit(main())`), A.U27.27 (no `type: ignore`
  on the stripper import), A.U28.28 (E402 reasons), A.U20.33 (no `from __future__`), A.U7.19 (`--help`), A.U21.29 (typed
  versions table), A.U10.34 (module docstring kept for argparse), A.U36.513 (comments cite the generator), A.U1.04/.16,
  A.U32.01, A.U36.547 (docs naming the command — blast), A.C.01 (5) (round image — procedure), A.U26.14 (reflash test
  calls it — blast), A.U8C.121 (test timeouts — blast), A.U37.07 (every device built — procedure); OR139.a (1)-(2)
  (A-C review fold: the tick-offset test image is built by a flag, never by default).
- **Site**: `scripts/build_firmware.py:1-47`, `:111-173`.
- **Change**: docstring (3 lines) as HEAD, naming `--no-autostart` and the work dir; usage lines `uv run
  scripts/build_firmware.py <device>` / `… <device> --output build/firmware-<device>.uf2`. No `from __future__`; the three
  `sys.path` inserts stay, each import after them `# noqa: E402 - <the insert above makes it importable>`; `from
  _strip_type_checking import StripError, strip_type_checking_blocks` with no `type: ignore` (`host_typecheck.ini`
  `mypy_path` gains `scripts`). Arguments: `device` ("a devices/<device>.toml stem"), `--device-toml PATH` (default
  `devices/<device>.toml`; a missing file → `BuildError` naming it), `--output` (default
  `build/firmware-<device>.uf2`, or `build/firmware-<device>-noautostart.uf2` with `--no-autostart`), `--no-autostart`
  (A.U27.36's help text), `--tick-offset-test` ("build the rollover round's test image: MicroPython's millisecond count
  starts 2**32 ms minus 15 minutes after boot (SPECIFICATION.md B.14); never a release image"; default output
  `build/firmware-<device>-tickoffset.uf2`, work dir suffix `-tickoffset`; passes `tick_offset_test=True` to
  `st.build_firmware()`, M.TOOL.055/.080), `--toolchain-dir` (`.resolve()`d), `--jobs`. `main()`: under `st.toolchain_lock(toolchain_dir)`
  (held from before the `mpy-cross` wipe until the record is written); a toolchain dir without the toolchain record →
  "the toolchain at <dir> is incomplete or predates the build record - run `uv run toolchain/setup_toolchain.py setup`
  first"; prints the record's `built_ref` and `micropython_commit`; `work = build/firmware/<device>[-noautostart]`
  removed at start then recreated, `stage/` and `manifest.py` inside, never removed at the end, its path printed before
  the build and on failure; catches `BuildError`, `StripError`, `st.SetupError`, `OverrideError`,
  `subprocess.CalledProcessError` → one line `build_firmware: <message>` on stderr, return 1;
  `BuildInternalError` and anything else propagate with a traceback. `if __name__ == "__main__": raise SystemExit(main())`.
- **Resolved**: A.U27.35's work dir per device collides between the normal and no-autostart builds of one device — the
  `-noautostart` suffix keeps them apart (agent decision AD-13). `RuntimeError` conversions (`:64-67`) go (A.U27.29).
  `--tick-offset-test` gets its own suffix for the same reason.
- **Unit**: U27 (stages: U21 lock/record/resolve; S0930 `--device-toml` lands after U27 on top; the
  `--tick-offset-test` flag in U27, after U21's override M.TOOL.080).
  A-C2 step order: A.U8C.121's part lands in U8C2, not U8C (it needs A.U8C2.22, which lands in U8C2).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.06 in U26.
- **Depends**: A.U21.22 (`toolchain_lock`), A.U21.03 (record), A.U27.29/A.U20.17 (`SetupError`/`OverrideError` derive
  from `Exception`, `BuildInternalError`) (TOOL, GEN); M.SCR.070 (`StripError`).
- **Blast carried by**: `tests_scripts/test_build_firmware.py` (work dir kept and wiped next time; `--no-autostart`
  output; `--device-toml`; lock contention message; error lines without traceback; `--tick-offset-test` output, work dir
  and the keyword passed) → A.U27.35/A.U27.36/A.S0930.06/A.U21.22/A.U27.29 (TSC, M.TSC.032); README build section, flash runbook → A.U27.35 docs/A.U32.01 (DOCS); `.gitignore`
  `build/` covers the work dir (A.U28.33, TOOL); `ci.yml` `firmware-build-verify` per device (A.U28.06, TOOL).
- **Kind**: code

### M.SCR.066 Staging: stripped modules, generated module and boot entry, sorted manifest
- **From**: A.U27.05 (1) (`stage_python_modules(stage_dir, generated, *, autostart=True)` + website step), A.U20.14 (5)
  (generated module through `_stage_stripped()`), A.U27.04 (path passed for messages), A.U27.34 (sorted file-list
  manifest), A.U27.36 (noautostart entry staged as `main.py`), A.U27.29 (3) (`:81`, `:90` → `BuildInternalError`), A.U36.544
  (`:52-53` reason in place), A.U20.13 (frozen set from the module's own imports — blast, `generated.frozen_modules`
  unchanged), A.U20.05/A.U24.54/A.U1.23 (boot entry source — blast), A.U8.23/A.U34.12/A.U34.09/A.SDEP.06 (named modules
  only: `ext/typings/microdot/` never staged, OR131 — holds), A.U21.10 (every rp2 build carries the override — blast),
  A.U20.36 (buildgen's reproducibility half — blast); OR141.a (5) (A-C review fold: the build date is a build input,
  the reproducibility check builds twice with one fixed date — decision reproducible-image), OR139.a (2) (the build info
  names a test override).
- **Site**: `scripts/build_firmware.py:39-108`.
- **Change**: `_MANIFEST_TEMPLATE` = the expanded board manifest (below) followed by `freeze({stage_dir!r},
  {files!r})\n`, `files = tuple(sorted(p.name for p in stage_dir.glob("*.py")))`, comment "listed sorted, so the image is
  independent of the host filesystem's order". The board manifest is not included as a file: `_MANIFEST_TEMPLATE` writes,
  at build time, the pinned checkout's `ports/rp2/boards/{board}/manifest.py` and every port manifest it includes, with
  each directory `freeze(path)` among their lines replaced by `freeze(path, <sorted file names of that directory in the
  checkout>)`, so the stock modules (`_boot.py`, `_boot_fat.py`, `rp2.py` at v1.29.0) are frozen in sorted order too; a
  line that does not freeze a directory is kept as written. The executor reads the board manifests and
  `tools/manifestfile.py` at the refreshed pin (OR129) before writing the replacement, and extends the expansion to any
  other directory walk it finds there. `_stage_stripped(src_file, dest)`: comment → "Strips this build's staged
  copy only, never src/ or ext/; the stripper is line-preserving, so a field traceback's line numbers equal the
  source's."; passes `str(src_file)` as `path`. `stage_python_modules(stage_dir, generated, *, autostart=True)`: resolve
  the frozen set (a computed module with no file → `BuildInternalError`), collision check (→ `BuildInternalError`),
  strip-and-write each module, the generated device module through the same `_stage_stripped()` path (from its text,
  path `build/generated_src/sensortask_<device>.py` for messages), and `main.py` = `generated.boot_entry_source` or
  `generated.boot_entry_noautostart_source`; the "nothing to strip" comment goes. `build_stage_dir(stage_dir, device_toml,
  *, autostart=True, build_date=None, test_overrides=())` = `generate_device(device_toml, src, ext,
  build_date=build_date, test_overrides=test_overrides)` → `stage_python_modules()` → the website step
  (`scripts/build_website.sh <device> <stage>/frozen_html.py`); `test_overrides` names a test-only firmware override in
  the generated build info (`("tick_offset_test",)` for the rollover image, OR139.a (2); [fold F04 M_GEN]). The build
  date is the build's one time input: `main()` passes the current UTC time (M.SCR.067), a reproducibility check one
  fixed date, and nothing else staged depends on when the build runs; comment above `build_stage_dir()`: "build_date is
  an input: real builds stamp their UTC build time, the reproducibility check passes a fixed one (owner, 2026-10-05).".
- **Resolved**: LEAD/R13's residual (A.U27.34, "parked for A-C"): closed by expanding the board manifest's directory
  freeze into a sorted explicit list, as the Req's one-order rule demands (AC3_R R-05).
- **Unit**: U27.
- **Depends**: M.SCR.070, M.SCR.071; A.U20.05/A.U20.14 (generated sources, GEN); A.U26.02 (`build_date` keyword).
- **Blast carried by**: `tests_scripts/test_stripped_image_boots.py` (compiled stage boots in the twin) → A.U27.05 (TSC);
  `tests_scripts/test_frozen_inputs_reproducible.py` → M.TSC.094 (A.U27.34), which also asserts the rendered manifest has
  no bare directory `freeze()` (AC3_R R-05; hand-off to TSC, M.TSC.094's Change) and that changing only the date
  changes only the date's line (OR141.a (5)); SPEC B.11 → A.U27.34/A.U36.534 docs (SPEC).
- **Kind**: code

### M.SCR.067 Image record and size report beside every `.uf2`
- **From**: A.U26.02 (record), A.U26.85 (`overrides`), A.S0930.06 (1) (`deviceToml`, `uartCrc`), A.U27.31 (size report),
  A.U27.36 (`autostart: false`), A.U10.40 (`buildDate` → `BuildDate`), A.U36.521 (resize trigger names the report —
  blast), M.HW_BENCH.060/.075/.094 (readers); OR139.a (2) (A-C review fold: the record names the tick-offset test
  override), OR141.a (5) (the build date a real build stamps).
- **Site**: `scripts/build_firmware.py:158-165` (after `st.build_firmware()`).
- **Change**: `build_date = current_build_date()` (the current UTC time: a real build stamps when it was built)
  computed once and passed down, with `test_overrides=("tick_offset_test",)` under `--tick-offset-test`; after the `.uf2` copy, `image_report(build_dir)
  -> ImageReport` (`used = __flash_binary_end - 0x10000000`, `fs_base = __micropy_flash_size__ -
  __micropy_flash_storage_bytes__ - __micropy_romfs_bytes__`, read with the toolchain's `arm-none-eabi-nm` from the
  `firmware.elf` beside the `.uf2`; `used > fs_base` → `BuildInternalError`), printed `== Image: <used> B of <fs_base> B
  before the filesystem (<pct> %), <free> B free`. Record `output.with_suffix(".json")` via a same-dir tmp +
  `os.replace`, sorted keys: `device`, `BuildDate`, `firmwareVersion`, `websiteVersion`, `commit` (or null), `dirty`,
  `maxConnections` (`device_max_connections(toml, src)`), `lwip` (`micropython_overrides.read_lwip_macros_from_build(
  uf2.parent, lwip_macros)` — `uf2` the path `st.build_firmware()` returned, in the port's build dir, not the copied
  output; `lwip_macros` from `st.load_lwip_macros()`), `overrides` (the optional overrides the build proves compiled in, re-read the same way:
  `["modlwip_eagain"]` when `micropython_overrides.verify_modlwip_eagain_in_build(uf2.parent, micropython_dir,
  copy_path)` passes with the `micropython_dir` and copy path `st.build_firmware()` used — `<overrides dir>/
  modlwip_eagain/modlwip.c`, `MODLWIP_OVERRIDE_DIR_NAME` — `[]` when it raises `OverrideError`, as for the round's
  control image built with the override call removed; `[]` throughout under A.SDEP.13 (a), where the section does not
  exist; plus `"tick_offset_test"` when `micropython_overrides.tick_offset_in_build(uf2.parent)`
  is true, M.TOOL.080 — a record naming it is the rollover image, which every bench run but the rollover runner's
  refuses, M.HW_BENCH.060), `deviceToml` (repo-relative path built from), `uartCrc` (per UART bus mode),
  `imageUsedBytes`, `filesystemBaseBytes`, `imageFreeBytes`, `autostart` (bool). Final line for `--no-autostart`: "Built
  without autostart: start with the line the board prints at boot".
- **Resolved**: A.U26.02's key `buildDate` follows A.U10.40's rename to `BuildDate` (A.U26.02 states it; M.HW_BENCH.060
  reads `record["BuildDate"]`). A.U26.02 offers the lwIP dict "returned from it or re-read from its build dir" and
  A.U26.85 reads `overrides` as "the list `st.build_firmware()` applied"; M.TOOL.055 (D3) keeps `build_firmware()`
  returning the uf2 `Path`, so both keys are re-read from the build dir by the two public readers M.TOOL.041 keeps
  (M_TOOL gap 3; M_SCR gap 2 (d) withdrawn, gap pass, agent decision AD-20). Only the modlwip override is optional: the
  lwIP-options override is in every rp2 build and its effect is the `lwip` key, so a control image reads `[]`.
- **Unit**: U27 (stages: U26 record and `overrides`; S0930 `deviceToml`/`uartCrc` after U27; the tick-offset entry in
  U27 after U21's M.TOOL.080).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.06 in U26.
- **Depends**: M.SCR.065; M.TOOL.041 (`read_lwip_macros_from_build()`, `verify_modlwip_eagain_in_build()` public),
  M.TOOL.055 (D3: the uf2 path returned, the build dir beside it), M.TOOL.039 (`MODLWIP_OVERRIDE_DIR_NAME`), M.TOOL.080
  (`tick_offset_in_build()`) (TOOL); [fold F04 M_GEN] (`generate_device(test_overrides=…)` names the override in
  the build info).
- **Blast carried by**: `bench/conftest.py` image check → M.HW_BENCH.060; lwIP control image (built in a throwaway worktree,
  record `overrides: []`) → M.HW_BENCH.075/A.C.06; CRC16 image → M.HW_BENCH.094; the rollover image → M.HW_BENCH.089,
  M.SCR.074; L0 `tests_scripts/test_build_firmware.py` record keys, the tick-offset entry and report parse (fake `nm`) →
  A.U26.02/A.U27.31 (TSC, M.TSC.032); BACKLOG resize item → A.U36.521 (DOCS); CI
  `firmware-build-verify` prints the size line → A.U28.43 (TOOL).
- **Kind**: code

## scripts/_generate_sensortask_modules.py

### M.SCR.068 The one writer of `build/generated_src/`: all or nothing, pruned, stamped
- **From**: A.U27.11 (merging A.U6.02, A.U20.05/.07/.15/.17/.28, A.U24.46 (1), A.U24.54), M.GEN.019 (boot entry names),
  M_WEB gap 6(a) (JS stamp path), A.U19.20 (`api/<device>.json` beside the definitions), A.U27.29 (idiom, kept),
  A.U28.28 (E402 reasons), A.U27.09/A.U27.39 (callers — blast), A.S0930.04 (single-device mode for the suite's
  `--device-toml`), A.U33.04/A.U33.09/A.U36.515/.518 (docs naming it — blast), A.U24.43/A.U25.25/A.U23.31/A.U6.05/A.U6.10/
  A.U6.12 (readers — blast).
- **Site**: `scripts/_generate_sensortask_modules.py:1-57`.
- **Change**: docstring (A.U27.11 (4) plus "definitions, API references and freshness stamps"); usage comment names the
  outputs. Default mode: for every derived device (`devices/*.toml` minus `zz_test_`), build in memory
  `sensortask_<d>.py`, `sensortask_<d>_wiring_plan.json` (= `compute_twin_wiring()`, `instances` included by it; the
  `:46-50` addition goes), `sensortask_<d>_expected.json` (`expected_facts()`), `sensortask_<d>_main.py` and
  `sensortask_<d>_main_noautostart.py`, `definitions/<d>.json`, `api/<d>.json` (`generate_api_reference(model, src)`); plus
  `definitions/index.json` `{"devices": [...]}`. Any `BuildError` → `error: <message>`, return 1, nothing written. Then
  every file through tmp + `os.replace()`; prune every file under `build/generated_src/`, `definitions/` and `api/`
  matching an output pattern whose device stem is not current ("Pruned N stale output(s): …"); stamps last:
  `build/generated_src/.inputs_stamp.json` (`{"inputs": {path: int(st_mtime)}}` over `devices/*.toml`, `buildgen/*.py`,
  `buildgen/error_catalog.json`, `src/*.py`) and `build/generated_src/definitions/inputs_stamp.json` (`{"tomls": {name:
  sha256}}`). Single-device mode `--device-toml PATH --out-dir DIR`: the same outputs for that TOML only, written into DIR
  (no stamps, no pruning, `index.json` naming the one device). Imports at top (repo-root insert with `# noqa: E402 - …`
  reasons); `raise SystemExit(main())`.
- **Resolved**: A.U24.46 (3) writes the JS stamp to `html/definitions/.inputs_stamp.json`; M.WEB.050 deletes
  `html/definitions/` and the stager forbids other `html/` files — the stamp moves beside the generated definitions
  (M_WEB gap 6(a)). A.U24.54's file name `build/generated_src/<device>_boot.py` → M.GEN.019's
  `sensortask_<device>_main.py` (M_GEN gap 1). A.U27.11 leaves `api/` outside the writer; A.U19.20 places it beside the
  generated definitions — written and pruned here as part of the one set (agent decision AD-12).
- **Unit**: U27 (stages: U6 definitions; U19 api; U20 expected facts and boot entries; U24 stamps; S0930 single-device mode).
  A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.04 in U25.
- **Depends**: M.GEN.019 (both boot-entry texts), M.GEN.018/.033 (`generate_api_reference`), A.U20.07
  (`expected_facts`), A.U20.28 (`instances` in `compute_twin_wiring`), A.U20.17 (atomic writer) (GEN).
- **Blast carried by**: `tests/test_reset_call_site_invariant.py` glob → M_GEN gap 1 (TEST_UNIT); `tests/_generated_tree.py`
  (A.U24.46, TEST_HELP); `tests_js/_generated_definitions.js` stamp path (M.WEB, WEB); L0
  `tests_scripts/test_generate_sensortask_modules.py` (all-or-nothing on a failing fixture, prune, stamps last,
  single-device mode writes only DIR) → A.U27.11 (TSC); callers M.SCR.025, .028, .037, .048, .061, .062, `package.json`
  `build:definitions` (M.WEB.071).
- **Kind**: code

## scripts/_render_coverage.py

### M.SCR.069 Coverage renderer: pinned, HTML and markdown only
- **From**: A.U28.02 (`coverage==<dev-group pin>` in the PEP 723 block), A.U28.15 (XML goes), A.U27.27 (no `type: ignore` on
  `coverage`), A.U27.28 (docstring ≤ 3 lines), A.U27.29 (idiom), A.U20.33 (no `from __future__`), A.U28.27 (PTH fixes),
  A.U24.72 (third render — caller), A.U10.34, A.U28.03 (pin check — blast), A.SDEP.03 (refresh — blast), A.U33.04,
  A.U36.526 (docs — blast).
- **Site**: `scripts/_render_coverage.py:1-76`.
- **Change**: PEP 723 `dependencies = ["coverage==<the dev group's pin>"]`; docstring (3 lines): "Renders the Unix-port
  coverage dumps (tests/_coverage_runner.py's JSON) into coverage.py data, then HTML and a markdown summary for one
  traced directory (SPECIFICATION.md E.5)." `--xml-file`, `xml_report()` and its print go; `os.path` uses → `pathlib`;
  no `from __future__`; `raise SystemExit(main())`; the `coverage` import untyped-ignore goes (mypy finds the dev-group
  package).
- **Resolved**: —
- **Unit**: U28.
- **Depends**: A.U28.02 (`coverage` pinned in the dev group, TOOL).
- **Blast carried by**: `tests_scripts/test_tool_pins.py` (PEP 723 pin equals the dev group's) → A.U28.03 (TSC);
  `test_test_sh.py` render lines → A.U28.15 (TSC).
- **Kind**: code

## scripts/_strip_type_checking.py

### M.SCR.070 Line-preserving stripper, no `ast.unparse`
- **From**: A.U27.04, A.U20.33, A.U20.14 (generated module strips the same way — blast), A.U20.36 (buildgen half —
  blast), A.U28.27 (N802 entry not needed — gap to TOOL), A.U34.05 (comments kept for `mpy-cross` — blast, holds).
- **Site**: `scripts/_strip_type_checking.py:1-79`.
- **Change**: as A.U27.04: AST-driven line edits (bare `if TYPE_CHECKING:` blanked, `pass` when it was the suite's only
  statement; every other load replaced by `False` in place; the import guard blanked; re-parse check raising
  `StripError(f"{path}:{line}: TYPE_CHECKING still read after stripping")`); `strip_type_checking_blocks(source: str,
  path: str = "<source>") -> str`; identity when nothing matches; the walk uses `ast.walk`/a plain visitor function, no
  `NodeTransformer` `visit_*` methods; docstring "Blanks `TYPE_CHECKING` blocks and their import guard in a staged copy,
  line for line (SPECIFICATION.md Part B.11)."
- **Resolved**: —
- **Unit**: U27.
- **Depends**: —
- **Blast carried by**: `tests_scripts/test_strip_type_checking.py:50-62` rewritten (compound/else forms) → A.U27.04 (TSC);
  `pyproject.toml` N802 entry for this file not added → TOOL gap 2.
- **Kind**: code

## scripts/build_website.sh

### M.SCR.071 One device's site: generated definitions, the stager, a kept work dir
- **From**: A.U6.03 (1) (definitions always generated; usage), A.U23.38 (stager replaces heredoc and loop;
  `--stage-only`), A.U27.08 (usage), A.U27.10 (Python check), A.U27.33 (`require_device`, convention), A.U27.35 (work
  dir, flock, no removal trap), A.U7.19 (`--help`), A.U36.544 (reason in place), A.U36.511/.515/.516/.517/.547/.549/A.U33.04/
  A.U33.09 (docs — blast), A.U6.04/.06/.27/A.U2.21/A.U19.20/A.U23.49/A.U24.82/A.U28.43/A.U6.12/A.U6.30/A.U27.06/A.U27.16
  (callers and outputs — blast).
- **Site**: `scripts/build_website.sh:1-85`.
- **Change**: header (3 lines): "Builds one device's website: generates its definitions (SPECIFICATION.md H.5), stages
  html/ and js/ through scripts/_stage_website.py (H.2) and freezes the stage with build_frozen_html.sh. Intermediates stay
  in build/website/<device>/ until that device's next build." Usage `scripts/build_website.sh [--stage-only] <device>
  [output]` — `<device>` names a `devices/<device>.toml`; `output` is the frozen module (default
  `frozen_modules/frozen_html.py`) or, with `--stage-only`, the stage directory to fill; `--help` exit 0; `require_device`
  (exit 2); `require_python311`. `work="${WEBSITE_WORK_DIR:-build/website/$device}"`, `flock "$work.lock"` held for the
  build, `rm -rf "$work"; mkdir -p "$work"`, path echoed; `python3 -m buildgen.definitions "devices/$device.toml"
  --src-dir src --out "$work/scratch/definitions.json"` (the `html/definitions/` branch and its comment go);
  `python3 scripts/_stage_website.py "$work/scratch/definitions.json" "$stage"` with `$stage` = `$work/stage`, or the
  given directory under `--stage-only` (created; nothing frozen; exit); else
  `HTML_SRC_DIRS="$stage" FROZEN_HTML_WORK_DIR="$work/gzipped" scripts/build_frozen_html.sh "$out_file"`.
- **Resolved**: M_WEB gap 6(b) "the stager's `--stage-only` mode": the mode lives here, where definitions are generated;
  `build_device_websites.sh --stage-only` drives it (AD-4).
- **Unit**: U27 (stages: U6 definitions; U23 stager and `--stage-only`; U27 work dir, checks).
- **Depends**: M.SCR.007, M.SCR.010, M.SCR.019, M.SCR.072; A.U6.01's CLI (`buildgen.definitions`, GEN).
- **Blast carried by**: callers M.SCR.020, .039, .061, .062, .066; `tests_scripts/test_build_website_sh.py` (`:98-115`
  replaced by the stager's tests; work dir kept and wiped; `--stage-only` writes no frozen file) → A.U23.38/A.U27.35 (TSC);
  `tests/test_website_build_integration.py` → A.U23.38 (TEST_UNIT).
- **Kind**: code

## scripts/build_frozen_html.sh

### M.SCR.072 Frozen website: quoted inputs, reproducible archive, kept work dir
- **From**: A.U27.06, A.U1.21 (superseded: `:10-11` goes), A.U34.08 (`:30` vendored-freezefs comment), A.U27.10, A.U27.33,
  A.U27.35, A.U27.34 (reproducibility test — blast), A.SDEP.07 (freezefs refresh — conditional), A.U7.19, A.U36.547,
  A.U1.27/A.U23.38/A.U27.08/A.U28.33/A.U34.12 (blast).
- **Site**: `scripts/build_frozen_html.sh:1-36`.
- **Change**: header (3 lines) states inputs (`HTML_SRC_DIRS`, space-separated), output, that `ext/freezefs` is vendored and
  unmodified, and that the build time lives only in `buildgen/version.py`; `--help` exit 0; `require_python311`;
  `read -r -a src_dirs <<<"${HTML_SRC_DIRS:?…}"`, each checked to be a directory (error text of A.U27.06 (1));
  `work="${FROZEN_HTML_WORK_DIR:-build/frozen_html/$(basename "$out_file" .py)}"` wiped at start, kept, echoed (no trap);
  `find "$work" -type f -exec gzip -9 -n {} +`; the 254-character archive-path check; freezefs through the pinned clock
  (`python3 -c 'import sys, time; time.localtime = lambda *a: time.gmtime(0); from freezefs.archive import main;
  sys.argv[0] = "freezefs"; sys.exit(main())' "$work" "$out_file" --on-import mount …` with `PYTHONPATH=ext`); the `:30`
  comment carries A.U34.08's provenance text; `:10-11` goes.
- **Resolved**: A.U1.21 repaths `:10-11`'s legacy reference; A.U27.06 (4) deletes the lines — dropped (site removed).
  A.SDEP.07 (U0): a freezefs re-vendor that changes `archive.py`'s clock or CLI re-checks the pinned-clock call (conditional).
- **Unit**: U27.
- **Depends**: M.SCR.010.
- **Blast carried by**: `tests_scripts/test_build_frozen_html_sh.py` (two builds byte-identical, a 255-char path fails, a
  missing dir fails) → A.U27.06 (TSC); `THIRD_PARTY_LICENSES.md` freezefs entry → A.U34.08 (DOCS).
- **Kind**: code

## scripts/setup_cross_browser_toolchain.sh

### M.SCR.073 Cross-browser installer: Xvfb on its own check, verified downloads
- **From**: A.U28.21 (Xvfb own block, summary line), A.U28.22 (Edge key fingerprint, micromamba pinned and sha256-checked,
  mktemp after the trap), A.U0.29 (`:39` label), A.U7.19, A.U27.33, A.SDEP.04/.19 (refresh, W35 channel re-check —
  conditional), A.U28.17/.19/.38 (CI and BACKLOG texts — blast), A.U21.24 (installer table excludes it — blast),
  A.U36.547.
- **Site**: `scripts/setup_cross_browser_toolchain.sh:1-62`.
- **Change**: as A.U28.21/A.U28.22: a separate `command -v Xvfb || apt-get install xvfb` block, the WebKit block installing
  only `webkit2gtk-driver`; the summary line names Xvfb; Microsoft's key checked against its fingerprint before use;
  micromamba at a pinned version with its sha256 checked; temporary files created after the one trap; `:39`
  "Deliberately unpinned" → "Unpinned (agent, 2026-08-26)" (Firefox floats by design, its CI cache rolls monthly);
  `--help` exit 0; header ≤ 3 lines.
- **Resolved**: —
- **Unit**: U28 (stage U0: A.U0.29 label).
- **Depends**: —
- **Blast carried by**: `tests_scripts/test_setup_cross_browser_toolchain_sh.py` (Xvfb installed without WebKitWebDriver;
  bad checksum fails) → A.U28.21/.22 (TSC); CI Firefox cache key → A.U28.19 (TOOL); BACKLOG list → A.U28.38 (DOCS).
- **Kind**: code

## scripts/run_bench_rollover_test.sh (new, A-C gap pass)

### M.SCR.074 Rollover runner: builds the tick-offset test image, the one documented path to `multi_day_rollover`
- **From**: AC_NOTES 45 / M_PROC gap 5 (no runner selects `multi_day_rollover`: M.SCR.030/.031 floors exclude it,
  M.SCR.032's floor is `soak_duration`), A.C.08/M.PROC.041 (R6 starts the rollover through the clean-run wrapper with a
  `multi_day_rollover` floor, agent decision D8 there), A.U26.36/M.HW_BENCH.089 (the bench test, its in-test skip on
  `--allow-multi-day-rollover`), A.U27.19 (`--marker-floor`; "a caller's `-m` narrows"), A.U26.74 (flag name), A.U7.13/
  A.U7.14 (run record, verdict), A.U7.18 (a long opt-in runs on top of a clean bench run, no lower levels — as the soak
  runner), A.U7.19 (`--help`), A.U26.75/A.U28.01 (one retried sync, then `--no-sync`, inside the wrapper), A.U27.33
  (shell convention), OR133 (exit codes); OR139.a (1)-(3) (A-C review fold: the runner builds the bench board's
  tick-offset test image, the rollover test flashes it once and polls about two hours).
- **Site**: new `scripts/run_bench_rollover_test.sh`.
- **Change**: shell convention; header (3 lines): "Builds the bench board's tick-offset test image (ticks wrap about 15
  minutes after boot; owner, 2026-10-01) and runs only @pytest.mark.multi_day_rollover tests on it for about two hours,
  on top of a clean bench run. Never a soak, never bundled with a suite runner (owner, 2026-09-26); one flash cycle."
  `--help` → "Usage: scripts/run_bench_rollover_test.sh [pytest args]", "other arguments go to pytest; a -m you pass
  narrows the selection", "builds and flashes the tick-offset test image, then about two hours of polls: start it
  detached (tests_hardware/README.md)", exit 0, no side effect; no option of its own, so no usage error of its own
  (every other argument reaches pytest, whose own usage errors the wrapper reports). Body: the bench device from data
  (the one TOML with `[device] bench = true`, found as the other bench runners find it); the image built with `uv run --no-sync scripts/build_firmware.py "$device" --tick-offset-test`
  (output `build/firmware-<device>-tickoffset.uf2` and its record, M.SCR.065/.067) after the run's one retried sync —
  a failed build exits 1 with the build's message before anything reaches the board; then
  `scripts/_require_clean_hardware_run.sh --runner run_bench_rollover_test --levels "rollover (not a level)"
  --marker-floor "multi_day_rollover" tests_hardware/bench --allow-multi-day-rollover --allow-flash-cycle
  --rollover-image "build/firmware-$device-tickoffset.uf2" "$@"`, exiting with its code (E.10: 0, 1, 2, 4). No lower
  levels, no trap (the image stays under `build/`). Where the one sync sits (before the build, the wrapper then not
  syncing again, or the build moved after the wrapper's own sync) is decided at execution against M.SCR.034, with its
  reason recorded; the run syncs once either way.
- **Resolved**: AC_NOTES 45 leaves the path open: a soak-runner mode (M_PROC gap 5's example) or a README recipe naming
  the wrapper call. A soak-runner mode is ruled out by G1/R23 ("runs only behind `multi_day_rollover`, never in a soak
  tier", owner, 2026-09-26) and M.SCR.032's own header ("not a soak"). The README recipe at HEAD and in M.DOCS.049
  (`uv run pytest tests_hardware/bench --allow-multi-day-rollover -k …`) bypasses the wrapper: no run record, no
  verdict, no evidence archive, and a `uv run` that re-resolves (A.U26.75: nothing inside a run syncs); a recipe naming
  `_require_clean_hardware_run.sh` with four internal options is not the copy-paste command OR15 asks for. A runner
  per opt-in long run, like the soak runner, is the one shape (OR24 "one material"; OR15 "an automated summary at the
  end") — agent decision AD-19 (gap pass). Its owner tag is G1/R23's rank line ("(owner, 2026-09-26)", OR33.a (1)).
  A-C review fold: OR139.a's test image is built here and flashed by the test through the one `reflash()` helper, so
  the flash sits behind `flash_cycle` like every other reflash; the owner tag of the test image is OR139's
  "(owner, 2026-10-01)".
- **Unit**: U27 (with the other runners' floors, A.U27.19; the bench test exists from U26; the override from U21).
- **Depends**: M.SCR.034 (`--marker-floor`, the verdict), M.SCR.014, M.SCR.065 (`--tick-offset-test`), M.SCR.067 (the
  record naming the override); M.HW_BENCH.089 (the test), M.HW_BENCH.001/.002 (the flags, `--rollover-image`, the
  marker); M.TOOL.080 (the override).
- **Blast carried by**: `tests_scripts/test_hardware_runners.py` (no lower-levels call; the block reads `Levels: rollover
  (not a level)`; the build runs before the wrapper with `--tick-offset-test`, a failing build exits 1 before it;
  `--allow-flash-cycle` and `--rollover-image` forwarded), `test_require_clean_hardware_run_sh.py` (`-m foo` →
  `(multi_day_rollover) and (foo)`; `--allow-multi-day-rollover` forwarded), `test_tool_help.py`'s `TOOLS` → hand-off TSC (M.TSC.196, M.TSC.122,
  M.TSC.217, GAPS_G4); README.md Recipes rollover line and the CLI reference entry → hand-off DOCS (M.DOCS.049,
  M.DOCS.052, GAPS_G4); R6's start command → hand-off PROC (M.PROC.041, GAPS_G4); `tests_hardware/README.md` Running
  → M.HW_BENCH.126 (amended); M.SCR.032's header names it (amended); shellcheck and the comment-cap gate cover it by
  glob (`scripts/*.sh`); BACKLOG chroot list (CLAUDE.md: anything touching `scripts/`) — one clause in M_SCR gap 6's U27
  paragraph, "new hardware runner, shellcheck-linted, no environment change" → hand-off DOCS (M.DOCS.066, GAPS_G4).
- **Kind**: code

## scripts/_strip_type_checking.py (function docstrings, A-C3 Part S)

### M.SCR.075 Function docstrings become comment blocks
- **From**: A.U10.34 (A-C3 Part S: no carrier in this cluster).
- **Site**: `scripts/_strip_type_checking.py` (:10, :21, :67).
- **Change**: each function, method and class docstring becomes a `#` comment block directly under the `def`/`class`
  line, same text, ≤ 3 prose lines (overflow to the owning doc per CLAUDE.md's comment rule); module docstrings stay
  (the five argparse readers included). A file a later change rewrites carries the form forward (here M.SCR.070, U27).
- **Resolved**: —
- **Unit**: U10.
- **Depends**: —
- **Blast carried by**: `tests_scripts/test_comment_block_cap.py` stays green → M.TSC.065.
- **Kind**: code

## Gaps for other clusters

1. **WEB** — (a) `tests_js/_twin_process.js` (M.WEB.082) / M.WEB.061's `spawnTwin`: `MICROPYPATH` must be the twin layout
   with `frozen_modules` replaced by `build/generated_html/<device>` (A.U6.10 (1)); M.WEB.061 dropped the swap, and the
   smoke now launches through that module (M.SCR.064). Its port-53 acquisition must be re-entrant within one process
   (the smoke holds the lock across its device loop) and honour the inherited `SENSORS_PORT_LOCK_OWNER` /
   `SENSORS_PORT_LOCKS_HELD` contract of `scripts/_port_lock.sh` (M.SCR.012) in `tests_js/_port_lock.js`. (b)
   `package.json` `lint:html:built` (M.WEB.071 left the command to SCR) = `scripts/build_device_websites.sh --stage-only
   build/staged_html && html-validate "build/staged_html/*/index.html"` (M.SCR.020/.071). (c) The JS freshness stamp is
   `build/generated_src/definitions/inputs_stamp.json` `{"tomls": {name: sha256}}`, written by
   `scripts/_generate_sensortask_modules.py` (M.SCR.068), as M_WEB gap 6(a) asks.
2. **TOOL** — (a) `host_typecheck.ini` `mypy_path` gains `scripts` (A.U27.27; M.SCR.046/.065 drop their import ignores).
   (b) No `N802` per-file entry for `scripts/_strip_type_checking.py`: the rewritten stripper defines no `visit_*`
   method (M.SCR.070; A.U28.27 lists it). (c) `toolchain/versions.toml` `[stubs] board/stdlib` and their `TypedDict`
   rows (A.U27.02/A.U21.29), read by M.SCR.027. (d) `setup_toolchain.py board` (A.U21.28), `toolchain_lock()` (A.U21.22)
   and `build_firmware()` returning the applied overrides and read-back lwIP macros (A.U26.02/A.U26.85) — consumed by
   M.SCR.029/.065/.067. (e) `ci.yml`: ruff step generates first and lints `build/generated_src` (A.U27.09 (4)); mypy step
   paths = main-pass `files` (A.U27.25); smoke `--require-all-engines` (A.U28.17); every build-if-missing step
   `scripts/_unix_port.sh ensure standard` (A.U28.04); `unit-tests`/`unit-tests-gc-threshold` now carry the scenario
   harness at both stages — `timeout-minutes` re-measured (A.U8.15 rows). (f) `.gitignore` MICROPYPATH sentence: keep
   A.U28.33's capped text, pointing at `scripts/micropypath.toml` if the sentence stays (AC_NOTES 38 "keep one").
3. **TSC** — tests the merged SCR end state needs beyond those its constituents already name: `test_port_lock.py` gains
   the inherited-owner cases (child of the holder accepted; unrelated holder refused) (M.SCR.012/.013); `test_digital_twin_scenarios.py`
   gains `--shared-port-53` deselection reported, a device lacking a scenario's driver skipped by name, `--run-record`
   written (M.SCR.017); `test_run_digital_twin_ci_sh.py` gains the per-device archive runner name, the CRC16 rerun only
   for a `uart_link` device and its line-count check, the harness at both stages and the worst exit (M.SCR.061);
   `test_generate_sensortask_modules.py` gains `api/` written and pruned and the single-device `--device-toml --out-dir`
   mode (M.SCR.068); `test_archive_evidence.py` gains `new_run_dir()`/`--new-dir` and the per-runner keep (M.SCR.003);
   `test_require_clean_hardware_run_sh.py` asserts `EVIDENCE_DIR` exported and pointing at the archive dir (M.SCR.034,
   GAP-B6); `test_build_firmware.py` the `-noautostart` work dir (M.SCR.065); `test_test_sh.py` the harness jobs, their
   timeout key, `--coverage` skipping lwIP and harness jobs, exit 2 per OR133 (M.SCR.035/.040/.041/.045); `test_digital_twin_ci_suite_*`
   Run 1's `UTCTime`/`LocalTime` null check (M.SCR.049). M_SRC_NET gap 3 (labelled SCR: A.U6.28, A.U10.05, A.U30.03,
   A.U10.22 checks) concerns `tests_scripts/` checks, not `scripts/` files — passed to TSC.
4. **TWIN** — the runner's shutdown line must carry the twin FRAM chip's write count (e.g. `fram_writes=<n>`, or per
   chunk), which A.U35.28 (3)'s Run 3 rate assertion and the harness's bounded storm read (M.SCR.051, M.SCR.018 (h));
   M_TWIN names no carrier for A.U35.28.
5. **SPEC** — Part N rows no tagging action writes: `runner.scenarios_timeout_s` (M.SCR.040), `l2.commanded_reset_margin_s`
   (M.SCR.054), `l0.cross_browser_smoke_poll_ms` (M.SCR.063); E.10/E.3 exit code 2 for `test.sh`'s usage and validation
   errors (OR133); E.1 "Fixed ports" paragraph states the lock directory and its inheritance by child runners
   (M.SCR.012); E.6.1/E.9 state that `test.sh` runs the scenario harness with the exclusive-port-53 scenarios deselected
   and `run_digital_twin_ci.sh` runs them (M.SCR.017); H.7 states the smoke launches through `tests_js/_twin_process.js`.
6. **DOCS** — BACKLOG's build-environment list (CLAUDE.md PR workflow) needs one U27 paragraph naming every new sourced
   helper and generated input of the lint/typecheck/test legs not already listed by A.U27.08/.10/.33, A.U28.38 or
   A.U35.57: `scripts/_require_venv.sh`, `scripts/_unix_port.sh`, `scripts/micropypath.toml`, `scripts/_port_lock.sh`,
   `scripts/_summary_block.sh/.py`, `scripts/_archive_evidence.py`, `scripts/_check_gc_collect_sites.py`,
   `scripts/build_device_websites.sh`, `scripts/_stage_website.py` (test.sh now builds every device's site).

## Adherence findings

Per file, end state read against CLAUDE.md's hard rules and working agreements, the owner rows and the register:
- **3-line comment cap (shell included)** — breaches at HEAD: `_digital_twin_ci_suite.py:5-7` and `_render_coverage.py:6-7`
  one-line-packed docstrings (A.U27.28) → fixed by M.SCR.046/.069; every header and comment this merge writes is ≤ 3
  prose lines (checked per entry). Pass.
- **No variant literal (OR78.a)** — HEAD: `test.sh:14-16, :290-294`, `build_firmware.py:11-12, :113`,
  `run_digital_twin_ci.sh:6, :23`, `run_unix_port_integration.sh:4, :32`, `cross_browser_smoke.mjs:15, :93-117`,
  `_digital_twin_ci_suite.py:5, :115, :122-124, :891, :1279` → fixed by M.SCR.035/.039/.065/.061/.062/.063/.046/.048/.054.
- **`ext/` never edited** — the pinned-clock freezefs call wraps the vendored module from outside (M.SCR.072); OR131's
  stubs in `ext/typings/microdot/` are never staged (M.SCR.066). Pass.
- **Legacy tree never worked on** — only `lint.sh`'s comment names it (M.SCR.025). Pass.
- **No real credentials; nothing temporary cited** — no secret in any script; no audit ID in any proposed permanent text or
  comment (IDs appear only in this file's metadata). Pass.
- **Memory gates fail closed (CLAUDE.md four gates)** — HEAD's `test.sh` grep passed on an unreadable log and the twin
  gate on a missing one → fixed (M.SCR.040, M.SCR.016/.047); markers `MemoryError` OR `memory allocation failed` in both.
- **Hanging tests never allowed** — every new job (harness, lwIP files) runs under the per-file timeout and retry
  (M.SCR.040); no new unbounded wait. Pass.
- **Two suites never bind one port at once** — the per-port lock in every binder (M.SCR.012/.013/.039/.061/.062/.064);
  HEAD had none → fixed.
- **Evidence archived, never deleted (OR38.a)** — HEAD's `test.sh` cleanup, coverage overwrite, hardware log removal and
  twin logs overwrite → fixed (M.SCR.044, .034, .061, .048).
- **Hardware only with the owner's go-ahead; wear gates** — runners touch no board before the lower levels pass; the
  gate map keeps every `--allow-…` deselection reported; nothing here runs hardware. Pass.
- **No new permanent CI control arm (OR21.a (2))** — the CRC16 rerun is OR116's second mode, not a control arm; no
  planted-fault arm added to CI. Pass.
- **Docs hold current state** — "14-run", "85 files", stale clean comment, "default wozi" removed (M.SCR.061/.035/.046).
- **Usage errors exit 2 (E.10)** — `test.sh` exits 1 at HEAD → raised as Q1, answered (a) (OR133).
- **One material (OR24)** — twin-process helpers shared by suite and harness (M.SCR.016), the smoke on the JS twin module
  (M.SCR.064), one Unix-port probe, one MICROPYPATH source, one device list, one retry script. Pass.

## Owner questions

**Q1. `test.sh` usage and setting errors: exit 2 like every runner?** — answered (a), owner, 2026-10-01 (OR133). (A.U7.02's E.10 rule "a usage error exits 2 in
every runner" against HEAD's `test.sh:34, :47, :53` and A.U7.06's new checks, which exit 1; A.U7.02 flagged it to the lead,
no owner row settles it; M.SCR.035/.045 written with (a), pending Q1.)
- (a) **Recommended**: exit 2 for an unknown argument, a bad `GC_THRESHOLD`, a bad timeout variable and a bad heavy-file
  list — one rule across all runners, so a caller (`_run_lower_levels.sh`, CI) tells "you called it wrong" from "tests
  failed"; `tests_scripts/test_test_sh.py`'s rejection tests change their expected code.
- (b) keep exit 1 in `test.sh` and name it in E.10 as the one exception — no test change; a misconfigured run reads as a
  test failure to every caller.

## Agent decisions for the OR2.c review

- AD-1 Port locks are inherited by child runners through `SENSORS_PORT_LOCK_OWNER`/`SENSORS_PORT_LOCKS_HELD` (M.SCR.012).
- AD-2 The CPython lock reader is `scripts/_port_lock.py` (M.SCR.013).
- AD-3 Under `test.sh` the harness deselects its exclusive-port-53 scenarios (reported); `run_digital_twin_ci.sh` runs
  them (M.SCR.017/.045).
- AD-4 `--stage-only` is `build_website.sh`'s mode, driven by `build_device_websites.sh --stage-only` (M.SCR.019/.020/.071).
- AD-5 `test.sh` builds every derived device's site (`build_device_websites.sh`) for the per-device harness jobs, besides
  the first device's `frozen_modules/` site for the unit tier (M.SCR.039); the website scenarios thus run on every device,
  wider than M.TWIN.136's one-device narrowing (OR22.a (2)).
- AD-6 The host-chain coverage report is rendered by `coverage` itself from `$results_dir/host.coverage` (M.SCR.044).
- AD-7 The suite's pass label lives on a module state object, so no `global`/PLW0603 entry (M.SCR.046).
- AD-8 Run 1 asserts `UTCTime`/`LocalTime` null while `NTPSynced` is false — A.U6.21's L2 clause had no carrier (M.SCR.049).
- AD-9 The twin CI archive runner is `digital_twin_ci_<device>`, so keep-3 applies per device (M.SCR.061).
- AD-10 The CRC16 TOML for Run 3's rerun is derived by `sed` with a line-count check (M.SCR.061).
- AD-11 The cross-browser smoke launches through `tests_js/_twin_process.js` (M.SCR.064; M_WEB gap 6(c)).
- AD-12 The generator writes and prunes `build/generated_src/api/` as part of its one all-or-nothing set (M.SCR.068).
- AD-13 `build_firmware.py --no-autostart` uses `build/firmware/<device>-noautostart/` as its work dir (M.SCR.065).
- AD-14 Harness jobs dispatch first in `test.sh`, lwIP files last; neither runs under `--coverage` (M.SCR.041).
- AD-15 The harness job timeout `runner.scenarios_timeout_s` starts at 5× its first measured run, re-measured in B3 (M.SCR.040).
- AD-16 `_archive_evidence.py` exposes `new_run_dir()`/`archive()` plus `--new-dir`, serving both CLI and Python users (M.SCR.003).
- AD-17 The generator's single-device `--device-toml --out-dir` mode serves the suite's `--device-toml` (M.SCR.048/.068).
- AD-18 The harness keeps its own `MEMORY_ERROR_MARKERS` copy in `_twin_process.py`, held equal by the agreement test,
  instead of importing `tests_hardware/harness.py` (M.SCR.016).
- AD-19 (A-C gap pass) The `multi_day_rollover` observation gets its own runner, `scripts/run_bench_rollover_test.sh`,
  rather than a soak-runner mode or a README recipe naming the wrapper (M.SCR.074; AC_NOTES 45).
- AD-20 (A-C gap pass) The image record re-reads `lwip` and `overrides` from the build dir through
  `micropython_overrides`' public readers, since `st.build_firmware()` keeps returning the uf2 path (M.SCR.067; M.TOOL.055 D3).

## Ledger

Every action whose Site, Change or Blast names a file of this cluster: 308, from the site index plus a slot-aware grep
of `audit/actions/*.md`. A second table lists actions read into a merged change that name no `scripts/` path.

| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.C.01 | M.SCR.006, M.SCR.065 |
| A.C.03 | M.SCR.031 |
| A.C.04 | M.SCR.033 |
| A.C.05 | M.SCR.031 |
| A.C.07 | M.SCR.032 |
| A.C.18 | M.SCR.030 |
| A.S0930.04 | M.SCR.048, M.SCR.051, M.SCR.061, M.SCR.068 |
| A.S0930.06 | M.SCR.065, M.SCR.067 |
| A.S0930.26 | M.SCR.040 |
| A.S0930.27 | M.SCR.018, M.SCR.059, M.SCR.060 |
| A.S0930.37 | M.SCR.040 |
| A.S0930.38 | M.SCR.018, M.SCR.054, M.SCR.059, M.SCR.060 |
| A.SDEP.02 | M.SCR.024, M.SCR.061 |
| A.SDEP.03 | M.SCR.029, M.SCR.069 |
| A.SDEP.04 | M.SCR.064, M.SCR.073 |
| A.SDEP.06 | M.SCR.066 |
| A.SDEP.07 | M.SCR.072 |
| A.SDEP.08 | M.SCR.027, M.SCR.028, M.SCR.036, M.SCR.062 |
| A.SDEP.09 | M.SCR.027 |
| A.SDEP.15 | M.SCR.027 |
| A.SDEP.16 | M.SCR.035, M.SCR.047, M.SCR.061, M.SCR.062, M.SCR.064 |
| A.SDEP.19 | M.SCR.064, M.SCR.073 |
| A.SDEP.25 | M.SCR.027, M.SCR.061 |
| A.U0.03 | blast-only, holds: U0 procedure confirms both Unix ports with HEAD's probe before A.U27.12 renames it |
| A.U0.04 | blast-only, holds: U0 execution agreement (flock around port-binding commands); coexists with M.SCR.012 |
| A.U0.06 | M.SCR.024, M.SCR.061 |
| A.U0.07 | M.SCR.046 |
| A.U0.29 | M.SCR.018, M.SCR.073 |
| A.U0.31 | M.SCR.062 |
| A.U0.35 | M.SCR.005, M.SCR.018, M.SCR.032, M.SCR.034 |
| A.U0.39 | M.SCR.025 |
| A.U0.40 | M.SCR.040 |
| A.U0.57 | M.SCR.024 |
| A.U0.60 | M.SCR.040 |
| A.U1.01 | blast-only, holds: no script scope names a legacy path (`lint.sh:13, :18` explicit lists) |
| A.U1.04 | M.SCR.065 |
| A.U1.06 | M.SCR.029 |
| A.U1.09 | blast-only, holds: its new L0 file runs in `test.sh`'s pytest tier unchanged |
| A.U1.16 | M.SCR.065 |
| A.U1.21 | M.SCR.025, M.SCR.072; `build_frozen_html.sh:10-11` repath dropped (lines deleted by A.U27.06) |
| A.U1.23 | M.SCR.066 |
| A.U1.27 | M.SCR.072 |
| A.U10.31 | M.SCR.028 |
| A.U10.34 | M.SCR.046, M.SCR.065, M.SCR.069, M.SCR.075 (`_strip_type_checking.py`; AC3_S S-05) |
| A.U10.35 | M.SCR.026 |
| A.U10.37 | M.SCR.015, M.SCR.025, M.SCR.046; its `lint.sh` grep path/message edit dropped (greps removed by A.U27.21) |
| A.U10.46 | M.SCR.028 |
| A.U11.03 | M.SCR.051 |
| A.U11.05 | M.SCR.051, M.SCR.052 |
| A.U11.10 | M.SCR.015, M.SCR.025; `lint.sh` grep edit dropped (greps removed by A.U27.21) |
| A.U11.31 | M.SCR.049, M.SCR.046 (the concurrent reset's wording in the `:108-110` comment; gap pass) |
| A.U14.28 | M.SCR.018, M.SCR.035 |
| A.U15.R01 | M.SCR.051 |
| A.U15.R02 | M.SCR.053; its twin-CI blast corrected (AC_NOTES 31): keyed read fault |
| A.U15.R03 | M.SCR.051 |
| A.U15.R04 | M.SCR.051 |
| A.U16.17 | M.SCR.051 |
| A.U17.11 | M.SCR.045 |
| A.U17.18 | M.SCR.061 |
| A.U17.23 | M.SCR.045 |
| A.U17.25 | M.SCR.045 |
| A.U17.26 | M.SCR.028 |
| A.U18.44 | M.SCR.028 |
| A.U18.47 | blast-only: ledger mention of `test.sh:335-390` (DONE-AT-HEAD) |
| A.U19.20 | M.SCR.018, M.SCR.068, M.SCR.071 |
| A.U19.24 | M.SCR.040, M.SCR.058 |
| A.U2.03 | M.SCR.046, M.SCR.049, M.SCR.053, M.SCR.055 |
| A.U2.15 | M.SCR.053, M.SCR.055 |
| A.U2.21 | M.SCR.071 |
| A.U20.05 | M.SCR.066, M.SCR.068 |
| A.U20.07 | M.SCR.037, M.SCR.068 |
| A.U20.13 | M.SCR.066 |
| A.U20.14 | M.SCR.066, M.SCR.070 |
| A.U20.15 | M.SCR.068 |
| A.U20.17 | M.SCR.068 |
| A.U20.28 | M.SCR.018, M.SCR.062, M.SCR.064, M.SCR.068 |
| A.U20.33 | M.SCR.028, M.SCR.046, M.SCR.065, M.SCR.069, M.SCR.070 |
| A.U20.36 | M.SCR.066, M.SCR.070 |
| A.U20.42 | blast-only: ledger row naming the image report as U27's → M.SCR.067 |
| A.U21.02 | M.SCR.026 |
| A.U21.03 | M.SCR.065 |
| A.U21.04 | M.SCR.027; its `==X.Y.Z.*` spec superseded by A.U27.02's exact pins |
| A.U21.08 | M.SCR.065 |
| A.U21.09 | blast-only, holds: no manifest of `build_firmware.py` uses `c_module()` (M.SCR.066 keeps none) |
| A.U21.10 | M.SCR.066 |
| A.U21.12 | M.SCR.008, M.SCR.036, M.SCR.040, M.SCR.041, M.SCR.045 |
| A.U21.17 | blast-only, holds: `build_firmware.py` calls only `st.build_mpy_cross`/`st.build_firmware` |
| A.U21.22 | M.SCR.008, M.SCR.036, M.SCR.061, M.SCR.062, M.SCR.065 |
| A.U21.24 | M.SCR.073 |
| A.U21.28 | M.SCR.029 |
| A.U21.29 | M.SCR.065 |
| A.U21.31 | M.SCR.036 |
| A.U22.04 | M.SCR.028 |
| A.U23.15 | M.SCR.063 |
| A.U23.31 | M.SCR.068 |
| A.U23.33 | M.SCR.003 |
| A.U23.38 | M.SCR.019, M.SCR.020, M.SCR.039, M.SCR.061, M.SCR.062, M.SCR.071, M.SCR.072 |
| A.U23.39 | M.SCR.019 |
| A.U23.42 | M.SCR.063 |
| A.U23.47 | M.SCR.028 |
| A.U23.49 | M.SCR.063, M.SCR.071 |
| A.U24.05 | blast-only, holds: runner exit codes; `test.sh`'s runner selection unchanged (M.SCR.040) |
| A.U24.36 | M.SCR.018, M.SCR.058 |
| A.U24.42 | blast-only: a `tests/` header naming the build flavours, consistent with M.SCR.036 (TEST_UNIT) |
| A.U24.43 | M.SCR.068 |
| A.U24.46 | M.SCR.037, M.SCR.068; JS stamp path moved to `build/generated_src/definitions/` (M_WEB gap 6(a)) |
| A.U24.48 | M.SCR.063 |
| A.U24.53 | M.SCR.061 |
| A.U24.54 | M.SCR.037, M.SCR.066, M.SCR.068; file name superseded by M.GEN.019 |
| A.U24.64 | blast-only: measurement collects in `tests/` are baseline rows of the checker (M.SCR.015) |
| A.U24.65 | M.SCR.040, M.SCR.041, M.SCR.042; the generic concurrency wrapper not created (A.U25.46 kept) |
| A.U24.68 | M.SCR.048, M.SCR.062 |
| A.U24.69 | M.SCR.012, M.SCR.013, M.SCR.039, M.SCR.061 |
| A.U24.71 | blast-only: CLAUDE.md count text (DOCS); the guard itself is M.SCR.025 |
| A.U24.72 | M.SCR.035, M.SCR.038, M.SCR.044, M.SCR.069 |
| A.U24.82 | M.SCR.039, M.SCR.071 |
| A.U25.18 | M.SCR.051 |
| A.U25.25 | M.SCR.068 |
| A.U25.32 | M.SCR.062, M.SCR.064 |
| A.U25.34 | M.SCR.055 |
| A.U25.35 | M.SCR.046, M.SCR.047, M.SCR.048, M.SCR.049, M.SCR.061 |
| A.U25.36 | M.SCR.016, M.SCR.047, M.SCR.051, M.SCR.052, M.SCR.053, M.SCR.054 |
| A.U25.37 | M.SCR.051, M.SCR.054, M.SCR.056 |
| A.U25.38 | M.SCR.016, M.SCR.050, M.SCR.053, M.SCR.054, M.SCR.058 |
| A.U25.39 | M.SCR.045 |
| A.U25.44 | M.SCR.047, M.SCR.062, M.SCR.064 |
| A.U25.46 | M.SCR.016, M.SCR.017, M.SCR.018, M.SCR.047 |
| A.U25.48 | M.SCR.017, M.SCR.018, M.SCR.046, M.SCR.048, M.SCR.061 |
| A.U25.55 | M.SCR.059, M.SCR.061 |
| A.U25.62 | blast-only, holds: the suite names no chip-fake class; `:67`'s `_NAME` table is cited as fact |
| A.U25.64 | M.SCR.016, M.SCR.047, M.SCR.048, M.SCR.054 |
| A.U25.65 | blast-only: `digital_twin/README.md` text (TWIN); the strict readers it names stay (M.SCR.047) |
| A.U25.66 | M.SCR.047, M.SCR.055 |
| A.U25.74 | M.SCR.017, M.SCR.026, M.SCR.063 |
| A.U26.02 | M.SCR.067 |
| A.U26.03 | blast-only: reads the image record → M.SCR.067 (M.HW_BENCH.060) |
| A.U26.05 | M.SCR.022 |
| A.U26.14 | M.SCR.005, M.SCR.065 |
| A.U26.22 | M.SCR.003 |
| A.U26.35 | M.SCR.005, M.SCR.030, M.SCR.032, M.SCR.034 |
| A.U26.42 | M.SCR.033 |
| A.U26.66 | blast-only: conformance probes reach the binary through `TwinBoard`/`_unix_port.sh` (M.SCR.008, M.HW_BENCH.091) |
| A.U26.74 | M.SCR.005, M.SCR.030, M.SCR.032, M.SCR.034, M.SCR.074 |
| A.U26.75 | M.SCR.014, M.SCR.028, M.SCR.029, M.SCR.033, M.SCR.034 |
| A.U26.85 | M.SCR.067 |
| A.U27.01 | M.SCR.016, M.SCR.047 |
| A.U27.02 | M.SCR.027 |
| A.U27.03 | M.SCR.027 |
| A.U27.04 | M.SCR.066, M.SCR.070 |
| A.U27.05 | M.SCR.066 |
| A.U27.06 | M.SCR.071, M.SCR.072 |
| A.U27.08 | M.SCR.006, M.SCR.007, M.SCR.020, M.SCR.035, M.SCR.039, M.SCR.046, M.SCR.054, M.SCR.057, M.SCR.062, M.SCR.065, M.SCR.071, M.SCR.072 |
| A.U27.09 | M.SCR.025, M.SCR.028, M.SCR.068 |
| A.U27.10 | M.SCR.010, M.SCR.024, M.SCR.026, M.SCR.071, M.SCR.072 |
| A.U27.11 | M.SCR.037, M.SCR.061, M.SCR.062, M.SCR.068 |
| A.U27.12 | M.SCR.008, M.SCR.022, M.SCR.035, M.SCR.036, M.SCR.061, M.SCR.062, M.SCR.064 |
| A.U27.13 | M.SCR.029 |
| A.U27.14 | M.SCR.035, M.SCR.038 |
| A.U27.15 | M.SCR.008, M.SCR.009, M.SCR.022, M.SCR.036, M.SCR.040, M.SCR.048, M.SCR.062, M.SCR.064 |
| A.U27.16 | M.SCR.003, M.SCR.006, M.SCR.048, M.SCR.061, M.SCR.071 |
| A.U27.17 | M.SCR.057 |
| A.U27.18 | M.SCR.001, M.SCR.002, M.SCR.003, M.SCR.044, M.SCR.045 |
| A.U27.19 | M.SCR.004, M.SCR.005, M.SCR.030, M.SCR.031, M.SCR.032, M.SCR.034, M.SCR.074 |
| A.U27.20 | M.SCR.025 |
| A.U27.21 | M.SCR.015, M.SCR.025 |
| A.U27.23 | M.SCR.028 |
| A.U27.25 | M.SCR.026, M.SCR.028 |
| A.U27.26 | M.SCR.011, M.SCR.024, M.SCR.026 |
| A.U27.27 | M.SCR.016, M.SCR.046, M.SCR.065, M.SCR.069 |
| A.U27.28 | M.SCR.046, M.SCR.069 |
| A.U27.29 | M.SCR.048, M.SCR.065, M.SCR.066, M.SCR.068, M.SCR.069 |
| A.U27.31 | M.SCR.067 |
| A.U27.32 | M.SCR.048, M.SCR.057, M.SCR.058 |
| A.U27.33 | M.SCR.007, M.SCR.020, M.SCR.024, M.SCR.026, M.SCR.029, M.SCR.034, M.SCR.035, M.SCR.038, M.SCR.040, M.SCR.041, M.SCR.061, M.SCR.062, M.SCR.071, M.SCR.072, M.SCR.073 |
| A.U27.34 | M.SCR.066, M.SCR.072 |
| A.U27.35 | M.SCR.019, M.SCR.061, M.SCR.062, M.SCR.065, M.SCR.071, M.SCR.072 |
| A.U27.36 | M.SCR.065, M.SCR.066, M.SCR.067 |
| A.U27.37 | M.SCR.016, M.SCR.033, M.SCR.046 |
| A.U27.38 | M.SCR.007, M.SCR.017, M.SCR.039, M.SCR.040, M.SCR.041, M.SCR.045, M.SCR.061 |
| A.U27.39 | M.SCR.007, M.SCR.012, M.SCR.013, M.SCR.016, M.SCR.017, M.SCR.022, M.SCR.048, M.SCR.062, M.SCR.064, M.SCR.068 |
| A.U28.01 | M.SCR.010, M.SCR.014, M.SCR.029, M.SCR.033, M.SCR.034 |
| A.U28.02 | M.SCR.038, M.SCR.044, M.SCR.069 |
| A.U28.03 | M.SCR.038, M.SCR.069 |
| A.U28.04 | M.SCR.008, M.SCR.036 |
| A.U28.05 | blast-only: `ci.yml` comment (TOOL); `build_firmware.py`'s cold-cache failure unchanged (M.SCR.065) |
| A.U28.06 | M.SCR.061 |
| A.U28.08 | M.SCR.061, M.SCR.064 |
| A.U28.10 | M.SCR.014 |
| A.U28.14 | M.SCR.025 |
| A.U28.15 | M.SCR.038, M.SCR.044, M.SCR.069 |
| A.U28.17 | M.SCR.023, M.SCR.063, M.SCR.073 |
| A.U28.18 | M.SCR.064 |
| A.U28.19 | M.SCR.073 |
| A.U28.21 | M.SCR.064, M.SCR.073 |
| A.U28.22 | M.SCR.073 |
| A.U28.24 | M.SCR.021 |
| A.U28.25 | M.SCR.023, M.SCR.064 |
| A.U28.26 | M.SCR.064 |
| A.U28.27 | M.SCR.046, M.SCR.069, M.SCR.070; PLW0603 per-file entry not needed (AD-7); N802 entry for the stripper not needed (TOOL gap) |
| A.U28.28 | M.SCR.046, M.SCR.065, M.SCR.068 |
| A.U28.33 | M.SCR.009, M.SCR.072 |
| A.U28.37 | M.SCR.014 |
| A.U28.38 | M.SCR.014, M.SCR.021, M.SCR.073 |
| A.U28.41 | M.SCR.025 |
| A.U28.43 | M.SCR.010, M.SCR.021, M.SCR.063, M.SCR.071 |
| A.U29.02 | M.SCR.038 |
| A.U3.02 | M.SCR.046 |
| A.U30.03 | M.SCR.038 |
| A.U30.12 | M.SCR.040 |
| A.U30.13 | M.SCR.040 |
| A.U30.14 | M.SCR.015, M.SCR.025 |
| A.U30.16 | M.SCR.015, M.SCR.025 |
| A.U30.17 | M.SCR.015 |
| A.U30.21 | M.SCR.035 |
| A.U31.06 | M.SCR.018 |
| A.U32.01 | M.SCR.065 |
| A.U33.04 | M.SCR.032, M.SCR.063, M.SCR.068, M.SCR.069, M.SCR.071 |
| A.U33.05 | M.SCR.025 |
| A.U33.07 | M.SCR.030 |
| A.U33.09 | M.SCR.063, M.SCR.068, M.SCR.071 |
| A.U34.05 | M.SCR.070 |
| A.U34.08 | M.SCR.072 |
| A.U34.09 | M.SCR.066 |
| A.U34.11 | M.SCR.026, M.SCR.028 |
| A.U34.12 | M.SCR.066, M.SCR.072 |
| A.U35.02 | M.SCR.006, M.SCR.024, M.SCR.060 |
| A.U35.05 | M.SCR.047 |
| A.U35.09 | M.SCR.018 |
| A.U35.15 | blast-only: a `tests/` root cause citing `test.sh`'s parallelism (J.7); no script change |
| A.U35.23 | M.SCR.042 |
| A.U35.24 | M.SCR.042 |
| A.U35.25 | M.SCR.046, M.SCR.057 |
| A.U35.26 | M.SCR.057 |
| A.U35.27 | M.SCR.046, M.SCR.057 |
| A.U35.28 | M.SCR.018, M.SCR.051 |
| A.U35.29 | M.SCR.018 |
| A.U35.37 | M.SCR.049 |
| A.U35.38 | M.SCR.016, M.SCR.049 |
| A.U35.39 | M.SCR.016 |
| A.U35.49 | M.SCR.022 |
| A.U35.57 | M.SCR.017 |
| A.U36.004 | M.SCR.018, M.SCR.049, M.SCR.052, M.SCR.055 |
| A.U36.008 | M.SCR.030, M.SCR.031, M.SCR.033 |
| A.U36.023 | M.SCR.026 |
| A.U36.024 | M.SCR.061, M.SCR.062 |
| A.U36.038 | M.SCR.063 |
| A.U36.511 | M.SCR.061, M.SCR.062, M.SCR.071 |
| A.U36.512 | M.SCR.008, M.SCR.036 |
| A.U36.513 | M.SCR.046, M.SCR.065 |
| A.U36.515 | M.SCR.068, M.SCR.071 |
| A.U36.516 | M.SCR.071 |
| A.U36.517 | M.SCR.019, M.SCR.020, M.SCR.071 |
| A.U36.518 | M.SCR.068 |
| A.U36.521 | M.SCR.067 |
| A.U36.524 | blast-only: CLAUDE.md/SPEC chroot-recipe comment naming `test.sh`; no script change |
| A.U36.526 | M.SCR.044, M.SCR.069 |
| A.U36.532 | M.SCR.058 |
| A.U36.534 | M.SCR.026 |
| A.U36.544 | M.SCR.018, M.SCR.037, M.SCR.053, M.SCR.066, M.SCR.071 |
| A.U36.547 | M.SCR.029, M.SCR.061, M.SCR.062, M.SCR.065, M.SCR.071, M.SCR.072, M.SCR.073 |
| A.U36.549 | M.SCR.071 |
| A.U37.07 | M.SCR.024, M.SCR.061, M.SCR.065 |
| A.U5.05 | M.SCR.018, M.SCR.046 |
| A.U6.02 | M.SCR.028, M.SCR.037, M.SCR.061, M.SCR.062, M.SCR.068 |
| A.U6.03 | M.SCR.020, M.SCR.039, M.SCR.061, M.SCR.062, M.SCR.071 |
| A.U6.04 | M.SCR.071 |
| A.U6.05 | M.SCR.068 |
| A.U6.06 | M.SCR.071 |
| A.U6.10 | M.SCR.068 |
| A.U6.11 | M.SCR.023, M.SCR.063 |
| A.U6.12 | M.SCR.068, M.SCR.071 |
| A.U6.21 | M.SCR.049; its unowned L2 clause carried (AD-8) |
| A.U6.27 | M.SCR.071 |
| A.U6.30 | M.SCR.063, M.SCR.071 |
| A.U7.01 | M.SCR.006, M.SCR.061 |
| A.U7.02 | M.SCR.001, M.SCR.002, M.SCR.035; exit-2 rule for `test.sh` per OR133 |
| A.U7.03 | M.SCR.001, M.SCR.045, M.SCR.061 |
| A.U7.04 | M.SCR.040, M.SCR.045 |
| A.U7.05 | M.SCR.040 |
| A.U7.06 | M.SCR.035; its checks exit 2 per OR133 |
| A.U7.08 | M.SCR.002, M.SCR.004, M.SCR.038, M.SCR.045 |
| A.U7.09 | M.SCR.002, M.SCR.048, M.SCR.057, M.SCR.061; the attempt-2 `retried` filing dropped (A.U27.17, OR37.a (2)) |
| A.U7.11 | M.SCR.001, M.SCR.024 |
| A.U7.12 | M.SCR.001, M.SCR.026, M.SCR.028 |
| A.U7.13 | M.SCR.004, M.SCR.005, M.SCR.034 |
| A.U7.14 | M.SCR.002, M.SCR.005, M.SCR.030, M.SCR.034 |
| A.U7.17 | M.SCR.002, M.SCR.033 |
| A.U7.18 | M.SCR.001, M.SCR.005, M.SCR.006, M.SCR.030, M.SCR.031, M.SCR.032, M.SCR.034, M.SCR.061 |
| A.U7.19 | M.SCR.024, M.SCR.026, M.SCR.029, M.SCR.030, M.SCR.031, M.SCR.032, M.SCR.033, M.SCR.035, M.SCR.061, M.SCR.062, M.SCR.063, M.SCR.065, M.SCR.071, M.SCR.072, M.SCR.073 |
| A.U7.20 | M.SCR.003, M.SCR.034, M.SCR.044, M.SCR.061; the two XML archive entries dropped (A.U28.15) |
| A.U7.21 | M.SCR.064 |
| A.U7.23 | M.SCR.064 |
| A.U7.24 | M.SCR.031, M.SCR.048 |
| A.U7.26 | M.SCR.038 |
| A.U8.04 | M.SCR.046 |
| A.U8.05 | M.SCR.046, M.SCR.058 |
| A.U8.14 | M.SCR.014, M.SCR.046, M.SCR.048 |
| A.U8.15 | M.SCR.035, M.SCR.038, M.SCR.040, M.SCR.043 |
| A.U8.16 | M.SCR.043 |
| A.U8.18 | M.SCR.018, M.SCR.063 |
| A.U8.20 | M.SCR.046, M.SCR.050, M.SCR.061; tags on `:680`/`:904` dropped (sleeps removed by A.U25.38) |
| A.U8.21 | M.SCR.063 |
| A.U8.23 | M.SCR.066 |
| A.U8.24 | M.SCR.028, M.SCR.042, M.SCR.046, M.SCR.063 |
| A.U8C.121 | M.SCR.065 |
| A.U8C2.08 | M.SCR.045 |
| A.U8C2.12 | M.SCR.045 |
| A.U8C2.15 | M.SCR.045 |

| action ID (read; names no `scripts/` path) | merged into M-ID |
|---|---|
| A.U0.28 | M.SCR.018 |
| A.U10.11 | M.SCR.018 |
| A.U10.15 | M.SCR.018 |
| A.U10.36 | M.SCR.018 |
| A.U10.38 | M.SCR.046, M.SCR.055 (its blast names no `scripts/` path; carried as an in-cluster gap) |
| A.U10.40 | M.SCR.018, M.SCR.049, M.SCR.050, M.SCR.055, M.SCR.063, M.SCR.067 |
| A.U10.R01 | M.SCR.053 |
| A.U18.01 | M.SCR.018, M.SCR.055 |
| A.U18.03 | M.SCR.018, M.SCR.055 |
| A.U19.03 | M.SCR.018 |
| A.U19.21 | M.SCR.018 |
| A.U2.13 | M.SCR.018 |
| A.U22.03 | M.SCR.018; withdrawn (AC_NOTES 37) — its comment edit dropped |
| A.U24.34 | M.SCR.018 |
| A.U24.37 | M.SCR.018 |
| A.U24.47 | M.SCR.018 |
| A.U24.60 | M.SCR.018 |
| A.U24.70 | M.SCR.017 |
| A.U25.13 | M.SCR.056 |
| A.U25.14 | M.SCR.056 |
| A.U25.31 | M.SCR.018 |
| A.U25.33 | M.SCR.018 |
| A.U25.45 | M.SCR.018 |
| A.U25.57 | M.SCR.054 |
| A.U25.72 | M.SCR.018 |
| A.U27.24 | M.SCR.025 |
| A.U30.15 | M.SCR.018 |
| A.U35.31 | M.SCR.018 |
| A.U7.07 | M.SCR.045 |
| A.U8.02 | M.SCR.017 |
| A.U8C.04 | M.SCR.018 |
| A.U8C2.01 | M.SCR.018 |
| A.U9.09 | M.SCR.018 |
| A.U19.14 | M.SCR.046 (the `:108-110` comment's BACKLOG item 24 pointer → SPEC C.7 at U19; gap pass, M_DOCS gap 2) |
| A.C.08 | M.SCR.074 (R6 runs through the rollover runner; gap pass, AC_NOTES 45) |
| A.U26.36 | M.SCR.074 (the runner's selection; gap pass) |
| A.U19.07 | M.SCR.018 (l) (L2 case; gap pass, GAPS_G3 hand-off 3 (a)) |
| A.U19.08 | M.SCR.018 (l) (gap pass) |
| A.U19.10 | M.SCR.018 (l) (gap pass) |
| A.U19.12 | M.SCR.018 (l) (gap pass) |
| A.U30.19 | M.SCR.059 (d) (gap pass) |
| AC3_O O-14 | M.SCR.039: "(OR78: no device named here)" → "; no device is named here" |
| AC3_O O-27 | M.SCR.015: rows by category, each re-checked at landing; the U31 measured-collection-pause row for `loop_stretch_timing.py` and a U31 stage (adapted: "OR91.a (9)" kept outside the quoted reason, which is permanent text) |
| AC3_R R-05 | M.SCR.066: the board manifest's directory freezes expanded to sorted lists; Resolved, Blast (the no-bare-`freeze()` assertion) |
| AC3_S S-05 | M.SCR.075 (new, U10): `scripts/_strip_type_checking.py`'s three function docstrings → comment blocks |

## A-C2 order notes (2026-10-01)

Unit and Depends edits made by the A-C2 work order (`audit/order/WORK_ORDER.md`); one row per edit.

| M-ID | slot | edit | reason |
|---|---|---|---|
| M.SCR.009 | Depends | `M.TWIN.017/.060` → `M.TWIN.017; M.TWIN.060 [follows] (its README names this file in U36)` | M.TWIN.060 is the README pointer to this file, written after it |
| M.SCR.018 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.27 in U25, A.S0930.38 in U25. | AC3_R R-08 (h) |
| M.SCR.040 | Unit | appended: A-C2 step order: A.U24.65's part lands in U25, not U24 (it needs A.U25.25, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.SCR.041 | Unit | appended: A-C2 step order: A.U24.65's part lands in U25, not U24 (it needs A.U25.25, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.SCR.042 | Unit | appended: A-C2 step order: A.U24.65's part lands in U25, not U24 (it needs A.U25.25, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.SCR.045 | Unit | appended: A-C2 step order: A.U17.25's part lands in U25, not U17 (it follows A.U17.25's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.SCR.048 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.04 in U25. | AC3_R R-08 (h) |
| M.SCR.051 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.04 in U25. | AC3_R R-08 (h) |
| M.SCR.053 | Unit | appended: A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.SCR.054 | Unit | was: S0930 lands after U25 (A.S0930.38 is the latest constituent). → now: U25 (SUPP_owner_0930's L2 half, after A.U25.36 and A.U25.55 in the same unit; LEAD/R32 'U25 (L2)'). | AC3_R R-08 (h): "S0930" is not a unit of the sequence |
| M.SCR.055 | Unit | appended: A-C2 step order: A.U2.15's part lands in U3, not U2 (it follows A.U2.15's own change, which lands in U3). | dependency deferral (an edge ran from a later step) |
| M.SCR.059 | Unit | was: S0930 (after U25); cell (d) with U30 (A.U30.19), after M.TWIN.044's `stack` branch. → now: U25 (SUPP_owner_0930's L2 half, after A.U25.36 and A.U25.55 in the same unit; LEAD/R32 'U25 (L2)'); cell (d) with U30 (A.U30.19), after M.TWIN.044's `stack` branch. | AC3_R R-08 (h): "S0930" is not a unit of the sequence |
| M.SCR.060 | Unit | was: S0930. → now: U25 (SUPP_owner_0930's L2 half, after A.U25.36 and A.U25.55 in the same unit; LEAD/R32 'U25 (L2)'). | AC3_R R-08 (h): "S0930" is not a unit of the sequence |
| M.SCR.061 | Unit | appended: A-C2 step order: A.U24.53's part lands in U25, not U24 (it follows A.U24.53's own change, which lands in U25). | dependency deferral (an edge ran from a later step) |
| M.SCR.061 | Unit | was: S0930 (A.S0930.04 lands after U27). Stages: U24 (locks), U25 (device required, comment), U27 (archive, probe, harness, convention). A-C2 step order: A.U24.53's part lands in U25, not U24 (it follows A.U24.53's own change, which lands in U25). → now: U27 (A.S0930.04's CRC16 rerun on U27's runner; stages U24, U25 as listed). Stages: U24 (locks), U25 (device required, comment), U27 (archive, probe, harness, convention). | AC3_R R-08 (h): "S0930" is not a unit of the sequence |
| M.SCR.065 | Unit | appended: A-C2 step order: A.U8C.121's part lands in U8C2, not U8C (it needs A.U8C2.22, which lands in U8C2). | dependency deferral (an edge ran from a later step) |
| M.SCR.065 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.06 in U26. | AC3_R R-08 (h) |
| M.SCR.067 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.06 in U26. | AC3_R R-08 (h) |
| M.SCR.068 | Unit | appended: A-C2: "S0930" is not a unit; its parts land in the units SUPP_owner_0930 states: A.S0930.04 in U25. | AC3_R R-08 (h) |

## A-C review fold (2026-10-05)

Folds the owner's A-C review answers (OR136-OR143, FOLD_ANSWERS, the routine settlements, AC_NOTES 52) per
`audit/actions/FOLD_BRIEF.md`. Cross-file dependencies on changes other fold agents add are written as
`[fold Fnn M_FILE]` tokens.

| Fnn | M-ID(s) | action |
|---|---|---|
| F01 | M.SCR.049, M.SCR.060 | amended (the relaunch writes each file once; Depends follow M.SRC_CORE.043) |
| F02 | M.SCR.018 | amended ((l): the 24-hour window, exact within a scenario) |
| F03 | M.SCR.060 | amended (ConfigFaults and the unread delete cells) |
| F04 | M.SCR.074, M.SCR.065, M.SCR.066, M.SCR.067, M.SCR.032 | amended (test-image build, `--tick-offset-test`, record and build-info marker, header) |
| F05 | — | none in this file |
| F06 | — | none in this file |
| F07 | — | none in this file |
| F08 | — | none in this file |
| F09 | — | none in this file |
| F10 | — | none in this file |
| F11 | M.SCR.049 | amended (A.U3.09 out of Depends) |
| F12 | — | none in this file |
| F13 | — | none in this file |
| F14 | M.SCR.027 | amended (From; the mismatch message names the rule) |
| F15 | — | none in this file |
| F16 | M.SCR.016, M.SCR.049 | amended (tolerance constant gone; the twin's NTP responder; Run 1 expects NTP synced) |
| F17 | — | none in this file |
| F18 | — | none in this file |
| F19 | — | none in this file |
| F20 | — | none in this file |
| F21 | M.SCR.066, M.SCR.074 | tag (build-date comment "(owner, 2026-10-05)"; runner header names OR139's "(owner, 2026-10-01)") |
| F22 | — | none in this file |
| F23 | — | none in this file |
| F24 | — | none in this file |
| F25 | M.SCR.018, M.SCR.016 | amended (lead ruling: (m) the host-side driver of M.TWIN.170/.171's concurrent-load scenario, U25; the shutdown line's `uart=` parse) |
| F26 | M.SCR.066, M.SCR.067 | amended (the build date is a build input; real builds stamp UTC) |
| F27 | — | none in this file |
| F28 | — | none in this file |
| F29 | — | none in this file |
| F30 | — | none in this file |
| F31 | — | none in this file |
| F32 | — | none in this file |
| F33 | — | none in this file |
