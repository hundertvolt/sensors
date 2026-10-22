Lane C hand-back. Commit `52a840c` on `audit/u28-c` (base b1fecfb, not pushed). The relay entry is under "## C" in S/u28/relay.md. Logs are in S/u28/laneC/.

**Steps:**
- **Applied (29):** 22, 42, 44, 50-59, 61 (all four parts), 62, 69-72, 98, 117, 118, 123, 124, 126, 131, 132, 137, 146.
- **Open findings closed in code:** OF-24, OF-57, OF-141, OF-191, OF-193 (CI half), OF-199 (test_test_sh.py reorder: same top-level statements and comments by AST, d15_test_test_sh_ast.txt), OF-204.
- **OF-125:** no code. Closed by the installed uv 0.8.17's own bounds (docs/reference/environment.md:124-130 and base_client.rs:301-313, :431; of125_uv_timeouts.txt).
- **Verify rows:** left to you. dorny `ceb8a2b8` is still the newest v4 tag (v4.0.3, dorny_ls_remote.txt).

**Deviations:**
1. All four runners turn a failed sync into exit 1 with a named message. uv's own failure code is 2, which E.10 reserves for usage errors. The sync script itself still `exec`s, as the brief says.
2. Rollover and bench runs sync twice: once in the runner and once in each wrapper call. The second is a no-op on the synced venv. I followed the brief's "the four call it once" over M.SCR.074's "the run syncs once".
3. New scan fix: a bounded base lookup, `ci.last_green_lookup_timeout_s` = 60. A hung GitHub API now falls back to running the whole web tier instead of failing web-changes.
4. `_unix_port.sh` stops on a missing `timeout` and says so, rather than reading the binary as unusable. When the probe is killed, `check`'s error names the kill.
5. One Playwright step bound covers all eight install steps: `ci.playwright_install_timeout_min` = 5, set at 10x the longest measured CI install (30 s).
6. `.gitignore` says "must not" instead of the M text's "must never", which trips the decision-vocabulary check. The Firefox comment is tagged (owner, 2026-09-26, paraphrase) and (agent, 2026-09-30).
7. Smaller choices:
   - twin matrix values go through `env:` as TWIN_GC_THRESHOLD/TWIN_PART, because GC_THRESHOLD is read by test.sh.
   - `gh api` uses `-X GET -f` so the branch name is encoded.
   - typecheck.sh's usage text and comment now say CI passes no paths.
   - per your message, `scripts/preview_server.py` is now in TOOLS.

**Seen failing first:**
- **test_ci_workflow.py:** 13 of 15 red at b1fecfb (red_ci_workflow.txt). The two guards that passed there, plus the later floor and bound checks, each failed on a planted bite.
- **test_uv_sync_retried_sh.py:** red with no script.
- **Runner tests** (mpremote ×3, wrapper sync-first, flash, rollover, manual): red at b1fecfb. The sync-failure cases were red on the pre-fix scripts (exit 2).
- **Coverage rendering:** `--xml-file` refused with exit 2; ruff PTH (16 lines).
- **test_test_sh.py:** red on the render lines, the archive set, the report count (6 at b1fecfb) and the helper-start count (6). The step-summary rule failed on a bite.
- **Others:** the three new probe cases in test_unix_port_sh.py, and test_lint_type_scopes.py's CI case on b1fecfb's ci.yml.

**Red checks that wait on others:**
- **You (R-10 rows):**
  - `test_comment_block_cap.py` `test_each_pending_header_is_still_missing`: delete `_HEADER_PENDING` ci.yml and setup-micropython-toolchain/action.yml.
  - `test_no_variant_literals.py` `test_every_not_yet_cleaned_entry_still_carries_a_literal`: delete `_NOT_YET_CLEANED` ci.yml.
  - `test_decision_vocabulary.py` `test_the_allowlist_only_shrinks`: delete the `tests_scripts/test_test_sh.py	Anchored inside the unit-tests-coverage JOB…` row.
- **X:** `test_tunables_register.py` `test_the_tags_and_the_part_n_rows_agree` needs the Part N rows from the relay.
- **W at `<W1>`:** `test_tool_help.py` `test_every_listed_tool_exists` and the `[scripts/preview_server.py]` case. W's file answers `--help` cleanly.

**Silent-failure scan (all eight modes):**
- **New, fixed:** the runner exit-2 issue; the hung lookup; the devices glob, which emitted `["*"]` when nothing matched (now nullglob plus an empty check); vacuous rule parsing in test_ci_workflow.py, now floored.
- **New, not fixed (low):** the Playwright Chromium cache key names no runner image, so an ubuntu-latest move reuses a browser cached on the old image.
- **Covered by the steps:** continue-on-error, matrix-value interpolation, the probe hang, a stale binary under a restored cache (`ensure` checks the record), and the six summary starts. The toolchain key is complete: only three toolchain/ files are build inputs.
- **Safe as is:** the sync retries are bounded (3 attempts, each inside uv's HTTP timeouts).

**Facts owed:**
- **X:** everything is in the relay (tunables, doc lines, CI-only proofs).
- **You:** `toolchain/setup_toolchain.py:104`'s comment should point at `scripts/uv_sync_retried.sh`.
- **R:** the uv-sync action strips a leading `==` from `required-version`; a range (`>=`) would break the install.
- **W and P:** none.

**After-times:** nothing ends above 10%. test_mpremote_connect_sh.py was 0.62 s against 0.45; I moved its stub to bash and it is now 0.40. test_test_sh.py is 31.2 s against 45.5.

**Runs:**
- gh api timing loop, rc 0.
- Per-file timed runs, rc 0.
- First tier run killed by pid: the pinned Node was missing from PATH, which caused 10 Node-version reds in test_live_twin_ceiling_parser.py.
- Tier rerun with the pinned Node: 210 + 150 + 121 + 84 s, rc 1. Its only failures are the reds listed above; group 01 also had 6 skips I did not look into.
- Nothing of mine is still running.
