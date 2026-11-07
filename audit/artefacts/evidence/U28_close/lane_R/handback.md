U28 lane R hand-back: R1 5adc25c (merged as 5c363c5); final b03356b on audit/u28-r (worktree S/wt-u28r; merge of <API> cf00454 is 7a372a5; rebuild.sh rc 0). Every file I touched is in files_R.txt.

**Steps by verdict**
- **Applied in R1:** 2, 6, 20, 21, 34, 73, 74, 101, 102, 106, the host fixes and the two R1 checks.
- **Applied after R1:**
  - 48/49: `[tool.uv] required-version = "==0.8.17"`, `pytest==9.1.1`, `mpremote==1.29.0`. uv's docs at the 0.8.17 tag confirm any other uv exits with an error.
  - 121: `tests_scripts/test_tool_pins.py`.
  - 136: `tests_scripts/test_config_paths_resolve.py`.
  - OF-194: `scripts/build_firmware.py` turns an --output it cannot create or write into a `firmware.output-unwritable` BuildError: one line, exit 1.
  - OF-195: the slow firmware test's skip reason now says "run it alone".
  - OF-28: both gaps still stood at b1fecfb, so both are fixed. The schema check now reads a path built as `cfg_path +` a literal, `config_filename(...)` or a directory path. `_is_store` now sees a store built by a same-file helper or by a dotted `ConfigManager` call.
  - 94: a typed loop replaces the `attr-defined` ignore.
  - 84: A002 moved to pyproject in R1, the tag was already there, and the shared path list is now a `ClassVar`, so RUF012's "no host site" holds.
- **Nothing written:** 4 and 5 (ruff finds no RUF005 in buildgen/). 60 is the lead's verify row; a planted finding in build/generated_src is reported, so no `--no-respect-gitignore` line is needed.

**Deviations**
- Both new test files read every dependency group instead of naming `"dev"`. The variant-literal check flags `"dev"` as a device name.
- The pin test also checks the lock's manifest specifier. Its uv-literal reader does not catch a setup-uv `version:` input.

**Seen failing first** (logs in S/u28/laneR)
- test_tool_pins at the base: red on the unpinned pytest/mpremote and the missing required-version (red_pins.txt).
- A planted resolved-version mismatch and a planted Node major mismatch are both caught (bite_pins.txt).
- The config-paths check is a guard, green on the real tree. Six planted dead paths are all reported: a ruff glob, a mypy files entry, a host ini entry, a tsconfig include, a ci.yml script and a vitest import (bite_paths.txt).
- OF-194: 3 cases raised tracebacks before the fix (red_of194.txt); green after.
- OF-28: red_of28a.txt (4 cases) and red_of28b.txt; green after.
- OF-195: the reason before the change is in red_of195.txt.
- Step 94: mypy attr-defined error without the ignore (red_s94.txt); clean after.

**Red checks and who they wait on**
- test_tool_pins: the lock manifest has no `==` for pytest and mpremote. Waits on the lead's `uv lock` and `uv sync`.
- test_suppression_form: 4 tests, all on 41 of P's files.
- test_twin_record.py::test_every_entrys_hashes_are_the_current_files: red since R1, missed by the API checks. Every entry's runner_sha256 changed because `tests_hardware/twin_board.py` (a runner file) lost its noqa, and the sha256 of five bench/flash files changed too. P's `run_device_script.py` edit will change the runner hash again. Waits on one lead run of `scripts/record_twin_instrument_runs.py` after all merges.
- C's and W's PTH lines from the R1 list still apply.

**Scan findings**
- Covered only in part (class 3, paths a check cannot evaluate): a config path whose name is computed, and a store built by a helper in another module.
- The firmware work-dir OSErrors are not silent: they raise a traceback naming the path.
- The test_lint_ceilings PATH-ruff finding is already routed by the lead.

**Facts owed:** written to relay.md under ## R: the uv pin, the BACKLOG line, doc lines for SPEC D.6/F.5.5/L.5/B.15, CLAUDE.md and README, and no new @tunable.

**Checks and runs** (each test file alone in its own namespace at nice 19; RUNS.md lines appended)
- Host mypy cold: clean (289 files).
- ruff on my files: clean.
- The 12 doc and convention checks: green.
- Whole tests_scripts tier, four groups, run before the pin edit:
  - g0: rc 0, 132 s.
  - g1: rc 0, 139 s.
  - g2: rc 1, 132 s. Its one failure was a device-name literal in my new files, since fixed (test_no_variant_literals now passes 19/19).
  - g3: rc 1, 177 s. Its seven failures are the four form tests (P) plus two pin tests and test_twin_record (all three above).
- After-times:
  - test_stored_config_golden: 10.0 s against a base of 8.0 s. Its b1fecfb version, timed beside it under the same load, took 10.1 s, so my change adds nothing.
  - Every other file is within its base. New files: test_ruff_exemptions_live 5.5–7.7 s, test_config_paths_resolve 3–5 s, test_tool_pins 0.3 s.
- Nothing of mine is running.
