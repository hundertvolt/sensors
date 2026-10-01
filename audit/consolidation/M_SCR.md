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
- **Blast carried by**: L0 `tests_scripts/test_summary_block.py` (A.U7.02, TSC); users M.SCR.005, M.SCR.044, M.SCR.059,
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
- **Blast carried by**: callers `test.sh` (M.SCR.047), `run_digital_twin_ci.sh` (M.SCR.064), hardware wrapper (M.SCR.035),
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
- **Blast carried by**: users `test.sh` (M.SCR.040), hardware wrapper (M.SCR.035), `tests_hardware/conftest.py`
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
- **Depends**: M.SCR.007 (U27 stage), M.SCR.037 (the test.sh exit codes it reads).
- **Blast carried by**: callers M.SCR.032/.033; L0 `tests_scripts/test_hardware_runners.py` (stubbed callees: order,
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
- **Blast carried by**: users M.SCR.006, .043, .045, .064, .069, .085, .092; L0 `tests_scripts/test_devices_sh.py`
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
- **Blast carried by**: users M.SCR.038 (test.sh), .064, .069, .071 (smoke), .018 (harness via `_twin_process.py`), .022;
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
- **Depends**: M.TWIN.017/.060.
- **Blast carried by**: readers M.SCR.008, .038, .053 (suite), .069, .071, .022, `tests_js/_micropypath.js` and
  `tests_js/_twin_process.js` (A.U27.15/M.WEB.082, WEB), `tests_scripts/test_coverage_runner.py`,
  `test_digital_twin_boot_contiguity.py`, `test_digital_twin_generated_boot.py` (A.U27.15, TSC),
  `tests_hardware/twin_board.py` (M.HW_BENCH.091); L0 check that no other file holds either literal (A.U27.15, TSC);
  `digital_twin/README.md` copies → A.U27.15 docs slot (TWIN/DOCS); `.gitignore` sentence → LEAD gap 1.
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
- **Blast carried by**: callers `lint.sh` (M.SCR.025), `typecheck.sh` (M.SCR.027), `build_website.sh` (M.SCR.090),
  `build_frozen_html.sh` (M.SCR.093), `ci.yml`/composite action (A.U27.10/A.U28.01, TOOL); `pyproject.toml:8-11` comment
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
- **Blast carried by**: callers M.SCR.024, M.SCR.027; L0 `tests_scripts/test_require_venv_sh.py` → A.U27.26 (TSC);
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
- **Blast carried by**: users M.SCR.016/.018 (harness, 53 for DNS scenarios; 18080 when it binds it), M.SCR.050
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
- **Blast carried by**: callers M.SCR.031, .035, .036, the composite actions (A.U28.01, TOOL); L0
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
  hardware rows A.U30.16 lists, re-derived from the end-state tree at landing (the `digital_twin/unix_port_gc_unwedge.py`
  row absent — the file is retired, M.TWIN; the twin's `_mem_sampler` row present only while A.U35.25 keeps its
  collection). `gc.threshold` — exactly one module-level `gc.threshold(<int literal>)` in each generated boot entry
  (`sensortask_<device>_main.py` and `_main_noautostart.py`), plus A.U30.14's callers `tests/_threshold_runner.py`,
  `tests/microtest.py`, `digital_twin/run_generic_integration.py`, `digital_twin/run_device_script.py` (M.TWIN, new),
  and `tests_hardware/device_scripts/*`; `gc.disable`/`gc.enable` nowhere. A finding prints `path:line: <call> in
  <qualname> is not an allowed site (SPECIFICATION.md I.4(e)/(f.1))`; exit 1 on any finding, 2 on a parse error
  naming the file.
- **Resolved**: A.U11.10 and A.U10.37 rewrite `lint.sh`'s grep path/message (`system_service.py` →
  `asy_system_service.py`); A.U27.21 removes those greps — the rename lands only as this table's module name (dropped
  as separate edits). The generated module carries no `gc.collect()` (M.SRC_CORE.015 moves it into `run_setups`), so
  A.U27.21's "codegen's emitted boot batch" row is not written.
- **Unit**: U30 (A.U30.14/.16 extend the U27 checker). Stage U27: A.U27.21's checker with the sites then in force.
  Stage U30: threshold rows and the test/twin/hardware rows.
- **Depends**: M.SCR.010; M.SRC_CORE.015/.016.
- **Blast carried by**: caller `lint.sh` (M.SCR.025); `tests_scripts/test_gc_collect_sites.py` rewritten to call the
  checker on fixture trees (alias forms, threshold forms) → A.U27.21/A.U30.14/A.U30.16 (TSC); CLAUDE.md memory rule and
  SPEC I.4(e)/(f.1), E.9 name the file → A.U30.17 (DOCS, SPEC); CI runs it through `lint.sh`/the pytest tier (A.U28.43
  row, TOOL).
- **Kind**: code

## scripts/_twin_process.py (new)

### M.SCR.016 Shared twin-process helpers for the suite and the harness
- **From**: A.U25.46 (helpers move: `_spawn`/`_shutdown`/`_wait_until_serving`/`_wait_exit`/`_read_log`/`_http`/errcount
  readers), A.U27.01 (`_TwinRun`, fail closed), A.U25.64 (signal deaths), A.U25.36 (exit codes 3/4/5), A.U35.38/.39 (NTP
  tolerance constant), A.U27.27 (types), A.U27.37 (ceiling lookup import), A.U25.38 (polls), A.U27.39 (lock import).
- **Site**: new `scripts/_twin_process.py`.
- **Change**: Python script convention (library). `@dataclass class TwinRun` (proc, `log_path: Path`, `log_file`,
  `device`, `state_dir`), replacing `proc.ci_log_file` and its `type: ignore`; `spawn(device, *, micropython_bin,
  wiring_plan, port, state_dir, fram_state_path, scd30_state_path, mem_backup_state_path, config_dir, gc_threshold,
  fault=(), hang=(), wifi_outcome=(), seed=None, duration=None, mem_sample_interval_ms=None, test_flags=(), log_path)
  -> TwinRun` building the runner argv of M.TWIN.051 (`--module --wiring-plan --host --port --device
  --fram-state-path --scd30-state-path --mem-backup-state-path --config-dir --online-ntp --seed --fault --hang
  --wifi-outcome --duration --gc-threshold --mem-sample-interval-ms` plus `--test-…` flags) with
  `MICROPYPATH = micropypath("twin")` (tomllib read of `scripts/micropypath.toml`) and `TZ=UTC` (until A.SDEP.16's W15
  check retires it); `wait_until_serving(run, port, timeout_s)` (poll, never sleep-then-assume); `shutdown(run,
  timeout_s) -> int`; `wait_exit(run, timeout_s) -> int`; `read_log(run) -> str` and `log_from(run, offset) -> str`;
  `close_log_and_check_memory_safety(run)` failing closed on a missing, empty or unreadable log (A.U27.01) and on
  either marker of `MEMORY_ERROR_MARKERS` (imported from `tests_hardware/harness.py`'s shared tuple, CLAUDE.md four-gate
  rule); `exit_reason(code) -> str` naming 3 reset, 4 bootloader, 5 power loss and `-N` "killed by signal <name>"
  (A.U25.64); `http(method, port, path, body=None, timeout_s=…) -> tuple[int, JSONValue]`; errcount readers
  `errcount_entries(status) -> list[ErrcountEntry]`; `parse_shutdown_line(log)` for `… shutdown:
  would_have_triggered_count=<n> feed_count=<n> mem_backup: r0=<4 words> public_destinations_refused=<n>` and
  `parse_machine_reset_line(log)`; `NORMAL_BOOT_TOLERATED = {"NTP": (<catalog names A.U35.38 lists>,)}` with
  `NORMAL_BOOT_TOLERATED_CONDITION = "NTPSynced is false"` and its in-place reason (one line). Types: `JSONValue`,
  `JSONObject`, `ErrcountEntry` (TypedDict); no `Any`.
- **Resolved**: A.U27.01's `_TwinRun` and A.U25.46's move land as one shape here (A.U27.01's Depends names this merge).
- **Unit**: U27 (the last of U25/U27/U35's edits; stages: U25 moves the helpers with A.U25.46, U27 adds `TwinRun`
  fail-closed and types, U35 adds the tolerance constant).
- **Depends**: M.SCR.009, M.SCR.013; M.TWIN.051 (flags), M.HW_BENCH harness `MEMORY_ERROR_MARKERS`.
- **Blast carried by**: users M.SCR.050-.063 (suite), M.SCR.017/.018 (harness); `tests_scripts/test_digital_twin_generated_boot.py`
  reads the tolerance constant through `load_script_module` → A.U35.39 (TSC); `tests_scripts/test_memory_error_gate_agreement.py`
  counts this module as the twin gate's site → A.U27.01 (TSC); L0 `tests_scripts/test_digital_twin_ci_suite_*.py` move
  their helper imports → A.U25.46 (TSC).
- **Kind**: code

