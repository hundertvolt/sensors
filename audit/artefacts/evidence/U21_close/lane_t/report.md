# U21 lane T: final report

Files: `toolchain/setup_toolchain.py`, `tests_scripts/test_setup_toolchain_env.py`, `toolchain/versions.toml` (header),
`pyproject.toml`, `host_typecheck.ini`.

Branch `audit/u21-t`, final HEAD **a1cfee1**. My commits:
- 8c38f9d: T1 WIP.
- 5b6dc1b: network, host and bench steps, and the L0 guard.
- c28ae01: three silent-failure fixes, and D.15 order.
- fd85e05: `host_typecheck.ini` section removed.
- a1cfee1: lane O's final items.

Merges, all clean with no conflict and no resolution edits:
- 4076be6 (api 76b6990)
- 61e3a65 (api 2f7543c)
- e4783af (api 5797124)
- f083bf7 (api ef88e8f, lane O's final work)

Every one of my commits touched only my five files (`git show --name-only`). Nothing is pushed. The worktree is clean.

## 1. Step table

Every step below is **applied**. Parts owned by other units are named in the row.

| row | M-id | what landed |
|---|---|---|
| 7 | M.TOOL.047 | `MicropythonPin`, `ToolchainPin`, `Versions`. `load_versions()` validates in the order micropython, toolchain, lwip, raising `SetupError` "`{path}: [table] key is missing / must be …` - see SPECIFICATION.md B.3" or "`{path}` cannot be read (…)". `load_lwip_macros()` reads `load_versions()["lwip"]`. The runners take `Versions`. No `StubPins` (U27). |
| 8 | M.TOOL.048 | `write_micropython_ref()` uses `re.subn`. It refuses n==0 and n>1. It then writes a `versions.toml.tmp` candidate, re-reads it through `load_versions()` (which refuses a ref outside `[micropython]`) and `os.replace`s it. On any refusal the file is untouched. |
| 9 | M.TOOL.053 | `_fail_on_build_diagnostics(out, what)` runs for mpy-cross (which gains `error:`), every Unix flavour and the rp2 build. |
| 10 | M.TOOL.059 | `ls-remote` goes through `run_retried()` on the remote-query budget. The comment is not edited (A-18). The `[stubs]` part waits for U27. |
| 11 | M.TOOL.064 | `BOARD_BY_ID_GLOB = "usb-MicroPython_Board_in_FS_mode_*-if00"` and `resolve_board_serial(by_id_dir, sys_tty_dir, dev_dir)`. `resolve_pico_device()` tries `--device`, then `$MPREMOTE_DEVICE`, then exactly one detected board; none or several is an error. `_read_usb_id_vendor()` and `detect_pico_serial_devices()` are kept (A-7). An L0 test pins the glob equal to `tests_hardware/harness.py`'s `_BOARD_BY_ID_GLOB` (A-6). |
| 14 | M.TOOL.070 | U21 stage. Budgets on `uv sync` (network, `env=None`), `npm ci` and both Playwright calls. "Node in use: <node> <version>" is logged. The Playwright raise is U28. |
| 15k | M.TOOL.043 | `Any` → TypedDicts; no `Any` is left in `setup_toolchain.py`. New imports are in. Already landed: docstrings → comments (U10), the future import (U20). |
| 15l | M.TOOL.046 | `run()` and `run_retried()` rewritten (deviations 1-4). Three budgets with tags. `NETWORK_ATTEMPTS` keeps the tag `tool.uv_sync_attempts`. Every call site passes a budget. `node_on_path_matches()` is bounded. curl `--max-time` is tagged. Output streams line by line, flushed. |
| 15m | M.TOOL.049 + OF-57 U21 half | `_sudo_prefix(env)` passes `--preserve-env=DEBIAN_FRONTEND` plus whichever `NETWORK_ENV_EXTRA` names are set (so no proxy URL appears in argv). The apt sequence is in three steps: (1) `update`, one bounded, non-fatal attempt; (2) `install --download-only` through `run_retried()`, at 150 s per attempt; (3) one `install` from the cache on the build budget. Failures carry `_APT_SUDO_HINT`. `apt_options()` is kept. |
| 15n | M.TOOL.050 | `clone_full()` refuses an existing destination and retries, clearing only its own partial attempt (`before_retry`). Fetches are retried. `ensure_repo_at_ref()` requires `.git` plus `git rev-parse --verify HEAD`, else "`{dest}` is not a complete clone (an interrupted clone?) - remove it and re-run setup". |
| 15o | M.TOOL.051 | `derive_picotool_ref()` returns `(tag, described)`. Its comment states the real rule, re-verified at pico-sdk `tools/CMakeLists.txt:146,165-169` and picotool `CMakeLists.txt:380`. Budgets added. |
| 15p | M.TOOL.052 | No rebuild when the record's `picotool_tag` matches and `picotool version` matches `picotool v<tag>\b`. A USB-less picotool is a `SetupError` in flash/bench and a warning otherwise. A different `picotool` first on `BUILD_ENV_PATH` gets a warning. The function takes `tier` and returns the version line. |
| 15q | M.TOOL.054 | `fetch_rp2_submodules()` is retried. `fetch_unix_submodules()` runs `make submodules MICROPY_PY_LWIP=1`, retried. |
| 15r | M.TOOL.055 | modlwip apply; `_merge_make_vars()` refuses a duplicate key; no `CFLAGS_EXTRA`; diagnostics; `tick_offset_test=False` with `board=board`. The build dir is `make_vars.get("BUILD", f"build-{board}")`. A tick image is refused in `build-<board>`. Three readbacks run after every build: lwIP macros, modlwip copy (now `MODLWIP_COPY_NAME`) and tick. **The label now names the manifest** (lane O's finding). |
| 15s | M.TOOL.056 | `UNIX_LWIP_BUILD_DIR`. `_build_unix_variant()` runs the kbd readback after every flavour. `build_unix_port()` keeps its signature, with `CFLAGS_EXTRA` for settrace only. `build_unix_lwip_port()` runs the host readback. |
| 15t | M.TOOL.057 | `CURRENT_UNIX_BUILD_DIRS`; `clean_build_dirs()` now covers build-lwip. |
| 15u | M.TOOL.058 | The sequence builds build-lwip after settrace. It keeps the literal `build_unix_port(micropython_dir, toolchain_dir, jobs, settrace=True)`. The summary names all three. The `:461` repath was already landed (U1). |
| 15v | M.TOOL.060 | `run_setup()`: pinned/moved/off-pin handling, the exclusive flags, the record deleted at start and written last, leftovers, the notice, `tier`. `run_test()`: the record and leftovers. The pico-sdk `submodule update` is retried. |
| 15w | M.TOOL.061 | Record API: `TOOLCHAIN_RECORD`, `read_toolchain_record`, `write_toolchain_record` (temp file + `os.replace`), `delete_toolchain_record`, 13 keys. Also `node/node-record.json`. |
| 15x | M.TOOL.062 | `toolchain_lock()`: mkdir, then `flock LOCK_EX\|LOCK_NB`, then the pid written. It is taken in `main()` around `load_versions()` and the runners. |
| 15y | M.TOOL.065 | `_TIER_COMMANDS` and `ensure_commands(pairs, *, skip_apt)` replace the three `ensure_*` helpers. `_BENCH_SUDO_COMMANDS` and `check_passwordless_sudo()` probe `sudo -k -n <abs path> <version arg>`; root passes. |
| 15z | M.TOOL.067 | `ensure_br_netfilter()` uses `sudo tee` with `stdin_text` and `chmod 644`; no temp files. The B.13 pointer is replaced by the reason in place. |
| 15aa | M.TOOL.068 | `_armed_recovery()` arms, checks `is-active`, and disarms only after success. The post-up poll uses `_wait_for_bridge_route()`. The channel self-heal is armed. The MAC remedy says to arm B.13's timer first. The PSK goes plainly in the one `modify`, with `secrets=(password,)`. |
| 15ab | M.TOOL.069 | `_node_release()` makes one SHASUMS fetch with strict parsing. In `ensure_node()`, curl is checked first and the hash is checked with hashlib; the tree is unpacked aside and renamed; the record is written, also on reuse. `SystemExit` → `SetupError`. |
| 15ac | M.TOOL.071 | `run_env()`, bench tier: `ensure_commands(bench)`, then the sudo probe, then the bridge, which takes its password from `$BENCH_AP_PASSWORD`. |
| 15ad | M.TOOL.072 | Help texts updated; `--clean` help names the three builds; `--password` removed. New `board` subparser: it prints only the path and takes no lock and reads no versions file. `board` is added to the bare-argv list; the lock is taken in dispatch. HEAD's `__main__` handler is kept (U27). |
| 51 | M.TOOL.030 | FBT trial (A-16) passed: the `tests_scripts/test_setup_toolchain_env.py` FBT001/FBT002 entry is gone, and the two bool-parametrized tests were reparametrized. The S603 reason for `micropython_overrides.py` now uses lane O's final text, fitted to 3 lines. |
| 53 | M.TOOL.044 (T half) | `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND` and both uses are gone (T1). |
| 54 | M.TOOL.063 | `remove_outdated_leftovers(toolchain_dir)` (deviation 5). |
| 56 | M.TOOL.074 | U21 stage, `versions.toml` header: the picotool clause and "A move is the owner's call (owner, 2026-09-26) and the platform re-check follows (SPECIFICATION.md Part F) …". The `[stubs]` clause waits for U27. |
| 58 | M.TOOL.079 | `host_typecheck.ini` sections removed: `[mypy-setup_toolchain]`, `[mypy-test_setup_toolchain_env]` (A-15) and `[mypy-test_micropython_overrides]` (A-15; U24's part, landed early on the lead's word). The host pass is clean without them. |
| 73 | M.TSC.125 | Tests for the ref writer, notice, record, diagnostics, leftovers and fakes. |
| 74 | M.TSC.126 | U21 parts: documentation MAC `00:00:5e:00:53:01`, password, armed switch, netfilter, command table, Node, resolver, sudo probe, picotool. The U1 comment was already landed; U24 literals and U28 Playwright are not touched. |
| OF-57 | open finding | U21 half as in 15m. The row stays open, re-targeted to U28 (the Playwright `install-deps` steps and `ci.firmware_build_verify_timeout_min`). |

The A-2 man-page check came before the apt split. The man pages are not installed on this minimized host, so I checked the installed binaries instead. None of the evidence contradicts the plan:
- libapt-pkg carries "dpkg was interrupted, you must manually run '%s' to correct the problem."
- The http(s) method carries `Range: bytes=` and `If-Range:`, so a partial download resumes.
- libapt-private carries "Download complete and in download only mode".
- **Not verified:** the man-page wording itself, and `sudo -k`'s exact semantics (only the `ignore_ticket` setting was seen in the binary). Phase C should read these on the Pi.

## 2. Deviations

Each is conservative and reversible, decided on the owner's behalf for review (agent, 2026-10-08).

1. **`run(..., terminal: bool = False)`.** A command whose `argv[0]` is `sudo` (or that passes `terminal=True`) runs in the caller's session. sudo needs the controlling terminal to ask for a password; the binary carries "a terminal is required to read the password". Every other command gets its own session, so a timeout's `killpg` stops the whole tree. The default keeps the §3 contract.
2. **`_stop_commands_on_termination()` in `main()`.** It turns SIGTERM and SIGHUP into `SystemExit(128+n)`, so `run()` stops its own-session child on the way out. A signal sent to the installer's group no longer reaches that child. Tested for SIGTERM, SIGHUP and SIGINT.
3. **Generalized timeout message**: "timed out after N s: <cmd> - a stalled download, mirror or build; check connectivity and any proxy, then re-run (limits: SPECIFICATION.md Part N)". The last failed retry reads "… - all N attempts failed: check connectivity and any proxy, then re-run".
4. **`run_retried(..., before_retry=None)`.** `clone_full()` clears its own partial clone before a retry. After the last attempt the partial clone stays, and the next run names it.
5. **Two dropped arguments.** `_build_unix_variant()` takes no `toolchain_dir`: the overrides dir arrives in `make_vars`. `remove_outdated_leftovers()` takes no `board`: `ports/rp2/build-*` is never touched, so the board is never read.
6. **`run_setup()` deletes the record at its start**, before anything changes. An interrupted setup then leaves no record claiming the old state.
7. **`run_test()` keeps fields only on a commit match.** It carries `built_ref`, `pico_sdk_*` and `picotool_*` over from the previous record only when `micropython_commit` matches.
8. **`build_firmware()`'s build dir comes from the merged `BUILD`**, which lets the tick image get its own directory. The tick refusal is a guard on that dir.
9. **picotool's USB check reads `picotool version`, not `--help`.** At the pinned picotool, `main.cpp:1720-1726` prints the "compiled without USB support" line in version mode; help mode prints it at `:2008-2011`.
10. **The ref writer goes through a candidate copy**, so a misplaced line is caught by the same `load_versions()` that reads the pin.
11. **The sudo probe is `sudo -k -n`**, so a cached credential cannot pass it. The unattended bench run comes later, when that cache may have expired.
12. **The pin-moved notice prints twice**: at write time and again at the end, so a build that fails after the write still says the pin moved.
13. **Node is unpacked into `.{tarball}.partial`** and renamed into place with `os.replace`. The hash check uses hashlib, so there is no `sha256sum` dependency.
14. **`resolve_pico_device()` logs nothing**, because `board`'s stdout must be only the path. An explicit `--ssid` is kept when only the password is generated.
15. **`ensure_node(..., *, skip_apt)`**, so the generic `ensure_commands()` can install curl. The Node log lives in `run_project_dependency_install()`.
16. **`--latest` with `--micropython-ref` raises `SetupError`** "--latest and --micropython-ref are exclusive", which reaches `main()`'s one error line. It is not an argparse group.
17. **D.15 order applied to `setup_toolchain.py` only.**
    - The test file's helpers and fixtures stay beside the tests that use them, which matches the tree: 76 of the 96 `tests_scripts/test_*.py` files do not have D.15-ordered helpers.
    - D.15's scope sentence covers non-test members of test files, but its machine check covers `src/` only.
    - **Question for the lead:** apply D.15 to all test-file helpers at a later unit, or record the exception.
18. **The six-device build ran pinned to two cores.** `test_build_firmware.py`'s real build passes no `--jobs`, so I ran it under `taskset -c 0,1` to stay inside the two-core budget.

**Files outside my set:** none edited. I read `scripts/build_firmware.py`, `scripts/test.sh` and `tests_hardware/harness.py`, read-only.

## 3. Incident (17:17:33 to about 17:20, 2026-10-08)

**Timeline:**
- 17:17:28: I ran my test file. It held a new test, `test_cli_env_has_no_password_option`, written test-first, which ran `setup_toolchain.py env --tier bench --password x` **as a subprocess**.
- On the unchanged code argparse accepted `--password`. pid 21907 started the real `env` path at 17:17:33 on the default dir `/root/pico-toolchain`, outside `/tmp/sensors-audit-toolchain.lock`, at -j4.
- 17:19:37: I found it in `ps`. It was running the rp2 `make` at 2:05 elapsed.
- 17:19:44: I sent `kill -TERM 21907`.
- 17:19:51: `ps` showed none of pids 21786, 21907, 28790, 28912, 28913, 28917, 29555 left.
- 17:20:15-17:20:22: I assessed the damage, read-only.
- 17:20:40: I reported to the lead.
- 17:21:17-17:21:38: the lead verified and restored.

**What changed on the host.** The lead verified every item except the mpy-cross one; full record in `u21/incident_T_1717.md`.
- `.toolchain.lock` created; the lead removed it.
- `sudo apt-get update` ran (lists 17:17:37). No package changed: dpkg.log has no 2026-10-08 entry.
- `git fetch` ran in all three checkouts. They are unchanged at v1.29.0, 2.3.0 and 2.3.1.
- picotool was rebuilt and `/usr/local/bin/picotool` reinstalled at 17:18:42 (same 2.3.1).
- mpy-cross was re-made at 17:18:45. This is my own account; the lead did not verify it.
- `ports/unix/build-standard` was removed at 17:18:46 and rebuilt by 17:19:02 as the frozen-verify variant. The lead restored the plain binary from `pretc` at 17:21:38.
- `build_overrides/unix_kbd_intr_variant` was rewritten and `modlwip_eagain` created.
- `ports/rp2/build-RPI_PICO_W` was removed and partly rebuilt.
- `build-settrace` is untouched. No bench, bridge or sudoers step was reached.

**Cause.** A CLI test spawned the real installer and relied on the code under test to refuse the command line. This broke the brief (no `setup`/`env`, apt, sudo, or write into `/root/pico-toolchain`) and plan §8 (`--toolchain-dir <tmp_path>`).

**Fix: no test spawns the installer CLI any more.**
- All CLI tests call `main()` in-process through `_main_refusing_to_run()`. It monkeypatches `run_env`, `run_setup`, `run_test` and `toolchain_lock` to `pytest.fail("the command line was accepted")` and passes `--toolchain-dir <tmp_path>` for `env`/`setup`.

**Guard (structural): the autouse fixture `_no_real_side_effects`.**
- It sets `HOME` and `PICO_TOOLCHAIN_DIR` to a tmp dir and `PICOTOOL_INSTALL_PREFIX` to tmp.
- It puts first on `PATH` **and** on `setup_toolchain.BUILD_ENV_PATH` (the installer's own fixed PATH) a directory of shims. Each shim exits 97 with "<test id>: <cmd> is shimmed out of the L0 tier".
- Shimmed commands: sudo, apt-get, apt, dpkg, git, make, cmake, curl, npm, npx, uv, picotool, nmcli, systemd-run, systemctl, usermod, modprobe, sysctl, iptables, tc, iw, ip, arm-none-eabi-gcc, gcc.
- Child processes inherit both PATHs.
- A permanent self-test, `test_the_guard_stops_a_real_step_on_every_path`, reaches a shim through each PATH.

**Proof (17:23:54).**
- I appended a temporary test that runs the incident's exact path in-process: `main()` with `env --tier bench`, no runner patched.
- It ended on the shim: `SetupError: command failed (exit 97): sudo --preserve-env=… apt-get … install --download-only … - all 3 attempts failed …`.
- HOME and PICO_TOOLCHAIN_DIR were `/tmp/pytest-of-root/pytest-7204/home1[/pico-toolchain]`.
- Unchanged: `stat` of `/root/pico-toolchain`, `micropython/`, `/var/lib/apt/lists` and `/usr/local/bin/picotool`, and the listing of `/root/pico-toolchain`. `find … -newer marker` over those trees found nothing.
- The temporary test was removed, verified by `grep -c` = 0.
- A later check of `test_the_current_names_are_the_ones_the_builds_write`, the one test that reads the real checkout, found nothing newer under `/root/pico-toolchain`.

**Every test that calls `main()` or spawns a process (condition 3), with its cover:**
- `main()` through `_main_refusing_to_run`: `test_cli_env_help_lists_all_three_tiers`, `test_cli_env_requires_tier`, `test_cli_env_rejects_unknown_tier`, `test_cli_env_has_no_password_option`, `test_cli_help_names_the_pin_rules_and_every_build_flavour`.
  - Cover: runners and lock fail, tmp toolchain dir, guard.
- `main()` directly:
  - `test_board_prints_the_resolved_path_without_a_lock_or_a_versions_read`: the lock and `load_versions` patched to fail; `resolve_board_serial` faked.
  - `test_main_runs_a_test_under_the_lock`: `run_test` faked, `--toolchain-dir tmp`.
  - `test_main_env_holds_one_lock_across_setup_and_the_node_install`: `run_setup` and `ensure_node` faked, `--toolchain-dir tmp`, `--skip-apt`.
- Python children, never the installer CLI:
  - `test_only_a_terminal_command_shares_the_callers_process_group` prints its pgrp.
  - `test_a_signalled_installer_takes_its_running_command_down_with_it[SIGTERM/SIGHUP/SIGINT]` imports the module and runs `sh -c 'sleep 30'`.
  - `test_a_second_run_on_one_toolchain_fails_at_once_naming_the_first` holds the lock on a tmp dir.
  - All three run under the guard's PATH and HOME.
- Every direct runner test (`run_setup`, `run_test`, `run_env`, `ensure_node`, `ensure_apt_packages`, `ensure_bench_bridge`) fakes `run()` and/or passes `tmp_path`, and the guard backs all of them.

**Condition 4:** the whole file was re-run only after conditions 1-3 were in place (guard added 17:23:28, proof 17:23:54). The re-run at 17:25:56 gave 143 items: 139 passed, and 4 failed by design (failing-first tests for work then in progress). It has been green since; today it stands at 146 passed.

**Your question: did any of my MicroPython runs use `/root/pico-toolchain`'s build-standard between 17:18:46 and 17:21:38?**
- **No.** Lane T ran no MicroPython-interpreter test file at any time; my tests are host pytest only.
- In that window my commands were `ps`, `kill -TERM 21907`, read-only `ls`/`grep`/`tail`, the message to you, and edits in my worktree.
- The only use of that binary in the window was by the incident process itself, before I stopped it. By sequence order it ran the frozen-verify import (`run_frozen_verify_on_unix`) on the frozen-verify build between 17:19:02 and 17:19:11, then the rp2 build seen in `ps`.
- All my real builds ran on `u21tc-t`, starting 17:30.

## 4. `built_ref` (lead item b), for S's print in `scripts/build_firmware.py`

`built_ref` is **never None**:
- **`setup`** writes the ref it was asked to build: the pin, `--micropython-ref`, or `--latest`'s tag.
- **`test`, previous record with the same `micropython_commit`:** keeps that record's `built_ref`.
- **`test`, no previous record or a different commit:** writes `git describe --tags --always`. On a tagged commit that is the tag (`v1.29.0`). Past a tag it is `<tag>-<n>-g<sha>`. With no reachable tag it is a short sha.

The same carry-over rule covers `pico_sdk_commit`, `pico_sdk_describe`, `picotool_tag` and `picotool_version`. A directory that only ever ran `test` keeps them `null`, as `u21tc-t`'s record shows now: `built_ref` `v1.29.0`, commit `0fd6c573…`, `unix_binaries` `[build-standard, build-settrace, build-lwip]`.

`read_toolchain_record()` returns None when the file is missing, unparseable, or its key set differs.

## 5. Facts for D (SPECIFICATION.md)

**Part N, eight tags added** (none renamed or withdrawn; none of them has a row yet):

| tag | value | site (`toolchain/setup_toolchain.py`) | bounds | basis |
|---|---|---|---|---|
| `tool.remote_query_timeout_s` | 120 s | `120` | every short query or probe: git rev-parse/describe/ls-tree/ls-remote, `--version` probes, `picotool version`, nmcli/ip/systemctl queries, the sudo probe, the tar unpack | estimated (agent, 8c38f9d) - measurement owed: the longest probe on a loaded CI runner and on the bench Pi4 |
| `tool.network_step_timeout_s` | 1800 s | `1800` | clones, fetches, submodule updates, `uv sync`, `npm ci`, the Playwright download | estimated (agent, 8c38f9d) - measurement owed: a cold micropython/pico-sdk clone with submodules on CI and over the bench Pi4's uplink |
| `tool.build_step_timeout_s` | 3600 s | `3600` | every make/cmake build, `sudo make install`, the apt install from cache, the frozen-verify run | estimated (agent, 8c38f9d) - measurement owed: the longest build step on the bench Pi4. Here a whole `test` run is 161-169 s at `-j2` |
| `tool.apt_step_timeout_s` | 150 s | `150` | one apt attempt: `update` (once, non-fatal) and each `install --download-only` attempt | estimated (agent, 5b6dc1b) - measurement owed: the download share of the apt step on CI (the whole step took 27-66 s on run 37799699030), the sandbox and the bench Pi4. Worst case 150 + 3×150 + 10 + 20 = 630 s |
| `tool.bench_bridge_recovery_arm_s` | 300 s | `300` | the systemd recovery timer's window around a bridge change (creation and the channel self-heal) | estimated (agent, 5b6dc1b) - measurement owed: a real bridge creation on the bench Pi4 (B.13 measured about 30 s to a DHCP lease) |
| `tool.bench_bridge_up_poll_s` | 90 s | `90` | how long br0 may take to get an address and a default route after `up` before the change counts as failed (the timer stays armed) | estimated (agent, 5b6dc1b) - measurement owed: as above, on the bench Pi4 |
| `tool.node_shasums_timeout_s` | 60 s | `60` | curl's `--max-time` for `SHASUMS256.txt`; `run()` allows the same plus `_CURL_SLACK_S` | estimated (agent, 8c38f9d) - measurement owed: the fetch on CI and the bench Pi4 |
| `tool.node_tarball_timeout_s` | 600 s | `600` | curl's `--max-time` for the Node tarball (plus slack, as above) | estimated (agent, 8c38f9d) - measurement owed: as above |

**Existing rows that need updating:**
- `tool.uv_sync_attempts` (site `NETWORK_ATTEMPTS = 3`) and `tool.uv_sync_backoff_step_s` (site `backoff_s: float = 10.0` in `run_retried()`) now cover every retried network step: clones, fetches, both ls-remotes, submodules, `uv sync`, apt `--download-only` and both Node curls.
- `tool.apt_acquire_timeout_s` (30, unchanged): its row should say the **download** step is the one retried, and the list `update` runs once, non-fatal.

**Other tags:**
- `tool.preprocess_timeout_s = 120` is **O's site**, not mine. I neither set nor read it. Per lane O it now bounds four proofs, including the host probe that sleeps 2.5 s.
- Untagged mechanism constants, which I judge not tunable (D decides): `_STOP_GRACE_S = 5.0` (SIGTERM→SIGKILL grace), `_CURL_SLACK_S = 30`, `_BRIDGE_POLL_STEP_S = 2`.

**Spec text owed:**
- **B.3:**
  - versions.toml validation and its messages.
  - The ref writer's three refusals, through a checked copy.
  - `--latest`/`--micropython-ref` are exclusive; `--latest` on the current pin writes nothing.
  - The pin-moved notice, at write and at the end: "versions.toml now pins {new}: the pin moves only on the owner's call (owner, 2026-09-26) - revert it unless that call was made."
  - The record: file, 13 keys, deleted at start, written last, the carry-over rule in §4.
  - The lock: `.toolchain.lock`, fail-fast, with its message.
- **B.4:**
  - `run()` streams flushed lines, redacts secrets, gives every command but sudo its own session, and stops it on timeout or on SIGTERM/SIGHUP.
  - The three budgets.
  - `NETWORK_ATTEMPTS` retries.
  - The apt split and `sudo --preserve-env` with the list above.
  - picotool: rebuilt only when its tag changed; refused when USB-less in flash/bench, a warning otherwise; a warning when a different binary is first on the PATH.
  - Node: one SHASUMS fetch, hashlib check, staging plus rename, `node/node-record.json`.
- **B.5 (leftovers):**
  - Removed: unix `build-*` not in `CURRENT_UNIX_BUILD_DIRS`, `build_overrides/*` not in `CURRENT_OVERRIDE_DIRS`, and Node trees other than the recorded one.
  - With no Node record, no Node tree is removed.
  - `ports/rp2/build-*` is never touched; a path resolving outside the dir is skipped with a warning.
- **B.12:** the resolver (vendor 2e8a plus the MicroPython by-id link) and its order (`--device`, `$MPREMOTE_DEVICE`, exactly one board). `setup_toolchain.py board` prints the path.
- **B.13:** the installer arms `sensors-bench-recovery-<pid>` (`systemd-run --on-active=300`) and verifies it `active` before any bridge change. It disarms only after success, and leaves it armed on failure. The channel self-heal also runs armed.
- **B.7/B.7.1:**
  - `SPECIFICATION.md:1241` still names `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND`, which is gone.
  - The bench tier's command table is in `_TIER_COMMANDS` (curl; nmcli/network-manager, ip and tc/iproute2, iptables, sysctl/procps, modprobe/kmod, iw, tcpdump, timeout/coreutils).
  - The sudo list is in `_BENCH_SUDO_COMMANDS` (nmcli, iw, iptables, tc, tee, picotool, timeout, systemd-run, systemctl).
  - Package mapping confirmed here with `dpkg -S`: sysctl→procps, timeout/tee→coreutils, ip/tc→iproute2, curl, iptables, systemctl/systemd-run→systemd. modprobe, iw, tcpdump and nmcli are not installed on this host. **Not checked against the noble or trixie archives.**
- **API end states:** see §3 of the plan, plus deviations 1, 4, 5 and 15.
- **New raises:** see §8.

## 6. Facts for E

- **README.md:**
  - `:91` (`--password PW` row), `:96` and the example at `:102-103` should use `BENCH_AP_PASSWORD`.
  - The `--device PATH` row (`:87`) should describe the new resolver order.
  - The `:49-50` rows should use the new help texts, and `:52` (`--clean`) should name the three Unix builds.
  - Help texts as landed: `--micropython-ref` "an off-pin build: the platform re-check applies before trusting it"; `--latest` "a pin move: the owner's call, and the platform re-check follows"; `--clean` names `ports/unix/build-standard, build-settrace, build-lwip`.
  - Add the `board` subcommand.
- **CLAUDE.md:1053** names the removed mbedtls constant (row 20).
- **tests_hardware/README.md:**
  - Item 1 should point to the command table.
  - New passwordless-sudo item, with the nine commands above. The installer writes no sudoers file; it names the refused commands and points to "Prerequisites".
  - Item 3 (`:31-42`): the installer now refuses a USB-less picotool in flash/bench (read from `picotool version`) and warns in generic.
  - The `BENCH_AP_PASSWORD` bullet: `env --tier bench` reads the same variable when it creates a bridge.
- **BACKLOG chroot paragraph (§7 text):**
  - `<FBT outcome>` = the `tests_scripts/test_setup_toolchain_env.py` FBT001/FBT002 entry is removed.
  - `<its sections>` = `[mypy-setup_toolchain]`, `[mypy-test_setup_toolchain_env]`, `[mypy-test_micropython_overrides]`.
  - The installer leg (`setup`) is still owed: no lane ran `setup`. `test` ran three times on `u21tc-t`.

## 7. For the lead

- **Allow-lists:** I add no line. `_decision_vocab_allowlist.txt:594-596` (three `setup_toolchain.py` "Deliberately …" comments) still match. There is no citation row for my files.
- **Any-baseline:** the three `host_typecheck.ini` sections above are removed. Host mypy is clean: "no issues found in 199 source files". `test_mypy_any_baseline.py` passes (7).
- **Lane O items (your message), all done at a1cfee1:**
  1. `board=board` was already in place (`setup_toolchain.py:643`). O's `[test]` case and host mypy are green on the merged tree.
  2. `MODLWIP_COPY_NAME` is used in the readback path. No removed name is referenced; `TICK_OFFSET_BUILD_DIR_NAME` and `TICK_OFFSET_BUILD_SUFFIX` both have zero hits in my files.
  3. O's S603 text is accurate against the three `subprocess.run` sites (`micropython_overrides.py:831, :912, :962`). I fitted it to 3 lines at most 107 chars, with no meaning change:
     - "the real build's flags.make" → "the build's flags.make"
     - "make variables" → "variables"
     - "resolved on" → "from"
     - "comes from … and" → "is … plus"
  4. Done at fd85e05 and re-checked clean after the f083bf7 merge.
  5. The label is in my step row 15r, so I fixed it. It now reads "frozen manifest <path>", with a failing-first test. `build_unix_port()`'s label (`:709`) still says "with the frozen verification module", which is accurate: its only frozen-manifest caller is the verification sequence.
  6. Not my site (see §5).
- **Still red, for D:** `test_tunables_register.py`, 1 failed / 14 passed. The exact lines are `toolchain/setup_toolchain.py:93, :95, :97, :130, :240, :242, :249, :251`, each "… is tagged but has no SPECIFICATION.md Part N row", for the eight tags above.
- **Ruff ceilings** were re-measured last. `test_lint_ceilings.py` passes (19), so every ceiling sits at the tree's measured maximum. My files peak at complexity 8, args 8 (`run` and `run_retried`, at the ceiling and not over), branches 8, statements 55 and returns 7. Nothing could go down because of my files alone.

## 8. New raises (`SetupError` unless noted)

**Process control:**
- the timeout and "command failed (exit N)" messages in `run()`;
- the last-attempt message in `run_retried()`;
- `SystemExit(128+signum)` in `_stop_commands_on_termination()`;
- the lock-held message.

**versions.toml and the CLI:**
- the four `load_versions()` and `write_micropython_ref()` messages (missing or wrong key, unreadable file, ref n==0 / n>1 / misplaced);
- `--latest`/`--micropython-ref` exclusive.

**Builds:**
- `_fail_on_build_diagnostics()`, with "`{what}` reported an error" and "`{what}` produced warnings … every build is warning-free; see SPECIFICATION.md B.7";
- duplicate make variable;
- tick image in `build-<board>`.

**Clones:**
- `clone_full()` on an existing destination;
- incomplete clone.

**apt and tools:**
- apt failures carrying `_APT_SUDO_HINT`;
- `ensure_commands()`: "… not on PATH and --skip-apt is set - install … by hand" and "… still not on PATH after installing …";
- USB-less picotool (flash/bench).

**Bench:**
- passwordless sudo missing or restricted;
- recovery timer did not arm, or is still armed;
- br0 got no address or route within 90 s.

**Node:**
- no build for this architecture;
- no linux-{arch} line;
- malformed sha256;
- checksum mismatch, with nothing unpacked;
- install did not produce bin/node. All of these were `SystemExit` before.

**Board resolver:**
- no MicroPython board / several boards.

**Removed raises:**
- the separate ip / iptables / nmcli "still not found" messages (now one `ensure_commands()` message);
- the per-build "warnings / reported an error" strings (now the shared helper);
- the old Raspberry-Pi-vendor "multiple … devices";
- the old `[lwip]`-missing message (now `load_versions()`'s).

## 9. Tests

My file is host CPython pytest, so GC stages do not apply. I ran no MicroPython test file.

**`tests_scripts/test_setup_toolchain_env.py`:**
- Before: 50 tests, 0.65 s at f76385a.
- After: 127 test functions, 146 items, **146 passed in 2.16-2.23 s** (wall about 2.1-2.4 s at `nice -n 19`).
- 88 new functions. 11 base tests were replaced by rewritten ones:
  - the `ensure_iproute2` / `ensure_network_manager` six → the command-table tests;
  - the bridge-creation two → the armed-timer and PSK tests;
  - netfilter → the tee test;
  - get_interface_mac → the documentation-MAC version;
  - prefers_explicit_override → takes_device_then_mpremote_device.

**Seen failing first:**
- 16:44: 39 failed (T1: run, retry, lock, record, versions, diagnostics, summary).
- 17:11-17:12: 18 failed, then 1 (apt, clones, network-step retry, pin writer, `--latest`/off-pin).
- 17:25-17:26: 4, then 52 (bench, resolver, board, command table, sudo, netfilter, bridge, Node, picotool, leftovers, CLI). The 52 were observed in the run that caused the incident.
- 17:33: 4 (sudo `-k`, Node staging, pin announced on failure).
- 18:05: 1 (`test_a_firmware_build_names_the_manifest_it_was_given`).
- 11 base tests were seen failing on their changed behaviour (the bridge self-heal, MAC warning, three `ensure_node`, apt, three resolver, npm-ci, uv-sync tests).
- The streaming test was mutation-checked: a buffered reader fails on its timeout.

**Guards (passed at once):**
- `test_the_guard_stops_a_real_step_on_every_path`
- `test_a_generated_bench_password_is_printed_once`
- `test_a_test_run_on_a_moved_checkout_claims_nothing_it_did_not_derive`
- `test_build_mpy_cross_returns_its_binary_after_a_clean_build`
- `test_get_interface_mac_parses_ip_link_show_output`
- `test_the_pin_writer_changes_the_one_ref_line_and_nothing_else`
- `test_the_pinned_versions_file_loads_as_tomllib_reads_it`

**Whole-tree gates at a1cfee1** (`nice -n 19`):

| file | result |
|---|---|
| `test_micropython_overrides` | 256 passed |
| `test_comment_block_cap` | 451 passed |
| `test_lint_ceilings` | 19 passed |
| `test_decision_vocabulary` | 6 passed |
| `test_citations` | 15 passed |
| `test_mypy_any_baseline` | 7 passed |
| `test_tool_help` | 19 passed |
| `test_host_annotations` | 12 passed |
| `test_code_conventions` | 23 passed |
| `test_legacy_paths` | 3 passed |
| `test_build_firmware` | 17 passed, 6 skipped |
| `test_tunables_register` | 1 failed (D's rows), 14 passed |

**Other checks:**
- `ruff check` over all eight scopes: "All checks passed!"
- `mypy --config-file host_typecheck.ini`: clean.
- `pytest --collect-only tests_hardware -q`: 120/143 collected, 23 deselected by the default-off markers, no error.

## 10. Runs (each entered in RUNS.md, each exited)

| RUNS.md | run | result |
|---|---|---|
| line 27 | `cp -a u21tc-base u21tc-t` | rc 0 |
| line 28 | flock + nice19 `setup_toolchain.py test --toolchain-dir u21tc-t --jobs 2` @5b6dc1b | **rc 0, 169 s**, 0 warnings, three flavours and every readback, record written |
| line 41 | flock + nice19 + `taskset -c 0,1` `RUN_SLOW_FIRMWARE_BUILD=1 PICO_TOOLCHAIN_DIR=u21tc-t pytest test_build_firmware.py -k real` @fd85e05 | **rc 0**, 8 passed, 15 deselected, 509 s (671 s including the flock wait); all six devices, each with the modlwip and tick-refusal readbacks |
| new | `test` @fd85e05 (O3 merged) | **rc 0, 167 s**, 0 warnings, "All verification checks passed" |
| new | `test` @a1cfee1 (O's final merged) | **rc 0, 161 s**, 0 warnings; the firmware step logs "frozen manifest /tmp/…/manifest_rp2.py" |

- The incident run (pid 21907) was stopped by me with SIGTERM. Its parent, my pytest 21786, then ended too.
- `ps` now shows no process naming `u21tc-t` or `wt-u21t`.
- Logs: `scratchpad/u21t_runs/{tc_test,fw6,tc_test2,tc_test3}.log`.
- **Not run by any lane:** a real `setup` or `env`, which is forbidden here. Their first real run is CI's cold cache after U21 (§7) and the owner's chroot leg.

## 11. Files the lead must run

**pytest (`tests_scripts/`):**
- `test_setup_toolchain_env.py` and `test_micropython_overrides.py` (cross-lane);
- `test_build_firmware.py` and `test_test_sh.py` (S; both use my lock, record and `build_firmware`);
- `test_tool_help.py`, `test_mypy_any_baseline.py`, `test_lint_ceilings.py`, `test_comment_block_cap.py`, `test_decision_vocabulary.py`, `test_citations.py`, `test_host_annotations.py`;
- `test_tunables_register.py`, after D's rows.

**Also:**
- `ruff` over all scopes;
- `mypy --config-file host_typecheck.ini`;
- `pytest --collect-only tests_hardware -q`.

## 12. Silent-failure scan (my files; tooling modes first)

**Fixed in this lane (covered):**
- **Stalled mirror (OF-57), classes 3 and 5:** apt bounded, retried and streamed (15m).
- **Killed mid-way:** the record is deleted at start and written last (class 4, 15v/15w). A partial clone is named, never fetched into (class 6, 15n). The lock dies with its holder, since flock is released by the OS (15x).
- **Concurrent second run:** fails at once, naming the first (15x).
- **Re-run over a dirty toolchain:** leftovers (54); O's `_fresh_dir` empties each override dir.
- **Stale record:** `test` keeps fields only on a commit match (15v).
- **Offline:** `test` touches no network; `update` failure is non-fatal and logged.
- **Bridge cut mid-change (class 6):** every change runs under a verified-armed timer, which stays armed on failure (15aa).
- **Built firmware:** the modlwip `EAGAIN` copy is proven in every rp2 image, and the tick override is refused by every release build's readback (15r, both real-proven).
- **Three found by this scan and fixed in c28ae01, each with a failing-first test:**
  - A moved pin was only announced at the end, so it was lost when the build failed (class 7, `run_setup()` `:1579`, after `write_micropython_ref()` `:1765`).
  - A killed Node unpack left a half tree under the final name (class 4, `:1134`).
  - The sudo probe passed on a cached credential that would expire before the unattended run (class 3, `check_passwordless_sudo`).

**New, not fixed. Each site is mine unless noted; I propose these for the lead's register.**
1. **`run()` at `:1459`, `_stop_commands_on_termination()` at `:459` (class 5/6).** A SIGKILL to the installer cannot be caught, so its own-session child keeps running, unlocked once the flock dies with the installer. **Low**: SIGKILL is the operator's own last resort.
   - Proposal: document it in B.4.
   - A smaller fix does not exist without a supervisor process (PR_SET_PDEATHSIG is per-child and needs ctypes).
2. **`write_micropython_ref()` `:1774` and `_write_json()` `:549` (class 4).** A kill between the write and the `os.replace` leaves `versions.toml.tmp` (it shows as untracked in git) or `toolchain-record.json.tmp`. **Harmless**: neither is ever read.
   - Proposal: the leftover sweep removes `toolchain-record.json.tmp`.
3. **The record's `input_sha256` (`:505`) is never compared by `scripts/test.sh`** (S's site; class 3). A local edit to `micropython_overrides.py` or `setup_toolchain.py` leaves stale binaries in use until `--clean`/`setup`. CI is safe, because its cache key hashes the overrides file.
   - Proposal for S/U27: test.sh re-runs `setup` when a hash differs.
4. **Readers of `build-standard` are not locked while `setup`/`test` rebuilds it** (`_build_unix_variant()` `:285` `rmtree`; reader `scripts/test.sh`; class 5). This is **the incident's damage mode**: about 16 s with no binary, then a frozen-verify binary.
   - Proposal: `scripts/test.sh` takes a shared `flock` on `.toolchain.lock` around its binary use, and setup's exclusive lock already excludes it.
5. **`run()` `:1481` (class 4).** After a forced stop the daemon reader is joined for only `_STOP_GRACE_S`, so trailing output may be lost. **Low**: the timeout error still names the command and the limit.
6. **A foreground sudo command (`_keeps_terminal`, `:328`) whose child ignores SIGTERM survives the SIGKILL sent to sudo**, because sudo is not its own session (class 6). **Low**: only nmcli, systemd-run and similar run there, all bounded quick calls.

Inherently safe by construction, per the code above:
- the lock released on death (flock);
- the record never half-written (temp file + `os.replace`);
- no record left after an interruption (deleted at start);
- the PSK never in output (`secrets=` redaction; tested);
- a proxy URL never in argv (`--preserve-env` by name).
