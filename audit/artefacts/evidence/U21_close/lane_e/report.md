# U21 lane E: final report

**Where it is.** Branch `audit/u21-e`, worktree `scratchpad/wt-u21e`, final HEAD **89fd6c4**:
- dd8202a merges `audit/u21-api` at 1b43482, so T, O and S final are all in. The merge was clean.
- 89fd6c4 is the one lane-E commit, "U21 lane E phase 2". There was no separate WIP E1 commit: the phase-2 instruction arrived before any edit.

**What was touched.** The commit touches only my five files. Nothing is pushed or stashed, and no other file was edited. Every fact below was read from the code at 1b43482, never from the packet alone.

## Step table

| row | M-id | state | where (line on 89fd6c4) |
|---|---|---|---|
| 1 | M.DOCS.065 | applied (U21 stage) | BACKLOG.md:907, "Deferred": the modlwip watch item. Issue 19704, PRs 19705/19708. Upstream `6e79dcf9c` is **verified in the pinned checkout's object store**: it comes after v1.29.0, swaps `mp_hal_delay_ms(50)` for `poll_sockets()` and keeps a ticks-based 10 s limit. The override stays until the pin carries a real fix; the anchor check fails the build when upstream changes the loop. Tagged (owner, 2026-09-30). |
| 16 | M.DOCS.035 | applied | HEAP_FRAGMENTATION_MEASUREMENTS.md:284, §M5.2: the three builds, cited as SPEC B.14.4. The outcome-(c) parts are void (A.SDEP.11 (a)), so `VARIANT_DIR` stays in both recipes and in §M4.4. Added: every `setup`/`test` removes other `ports/unix/build-*` dirs (`_outdated_leftovers()`), and both twins are among them. |
| 17 | M.DOCS.047 | applied (U21 stage) | README.md. See "README.md" below. |
| B3 | blast | applied | README.md:62-67: the record line and the picotool line. |
| 18 | M.DOCS.064 | applied (U21 rows) | BACKLOG.md:340, the modlwip send stall: a control image, then the override. Per A-19 there is no `l4.lwip_spin_concurrent_request_max_s`; the bound is named in words. BACKLOG.md:358, the bridge created under the installer's own timer, with a manual B.13 timer as outer safety. Each row names its test, expected outcome, wear and twin row, and cites no audit ID. |
| 19 | M.DOCS.070 | applied (U21 stage) | CLAUDE.md:51-54: the anchor-check sentence gains the modlwip_eagain/19704 clause (owner, 2026-09-30). The pointer rewrite is U36's. |
| 20 | M.DOCS.106 | applied (A-3, branch 2b) | CLAUDE.md:1064: "worked around by `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND` in setup_toolchain.py" becomes "suppressed for `ctr_drbg.c` alone by the build files `toolchain/micropython_overrides.py` generates". "is a GCC >= 14 diagnostic" stays true under 2b. |
| 21 | M.DOCS.066 | applied | BACKLOG.md:614. See "The BACKLOG chroot paragraph" below. |
| B1 | blast | applied | CLAUDE.md:342 (dead-man's switch: the installer arms its own); :635 (three binaries); :893-895 (stub version printed and recorded in `typings/.stub-spec`). |
| 23 | M.HW_BENCH.125 | applied (U21 stage) | tests_hardware/README.md:20-56, Prerequisites. Item 1 points to `_TIER_COMMANDS` (A-13). New item 2: passwordless sudo, with a placeholder sudoers line and each command's reason. Item 4: picotool refused when USB-less in flash/bench, a warning otherwise, the skip, the shadow warning, plus A.U1.07's version-mismatch sentence; the "this sandbox" narrative is gone. Items 2-4 renumbered 3-5, and the one citation is updated (:214 "Prerequisites item 3"). uv, DebugLevel and E15 are U26/U28's. |
| 24 | M.HW_BENCH.126 | applied (U21 stage) | tests_hardware/README.md:261-262: the `BENCH_AP_PASSWORD` bullet gains "`env --tier bench` reads the same variable when it creates a bridge". **Already landed:** A.U8C.119, cited at :279 (`l4.soak_duration_*`). The `/dev/ttyACM0` sentence goes at U27. |
| 76 | M.HW_BENCH.112 | applied (U21 stage) | tests_hardware/README.md:145-149: the installer's own recovery timer. :183-187: the PSK lines (throwaway, from `$BENCH_AP_PASSWORD`, passed plainly to the one `nmcli connection modify`; owner, 2026-10-02). |

**README.md (row 17).**
- `:42` the `board` subcommand.
- `:50-51` the help texts for `--micropython-ref`/`--latest`; `--latest` is exclusive with `--micropython-ref`.
- `:53` `--clean` lists the three builds.
- `:57-60` `test`: what it rebuilds, now "a few minutes".
- `:62-67` the record, picotool, the lock.
- The flash and bench tier rows.
- The command-check sentence.
- The `--device` row gives the resolver order.
- The `--password` row is removed, with a `BENCH_AP_PASSWORD` line at `:102`.
- The resolver and credentials paragraph (owner, 2026-10-02), and the example with `BENCH_AP_PASSWORD=<psk>`.
- The armed-timer bridge paragraph.
- Node: one SHASUMS fetch, the tarball checked before unpacking, staging and rename, `node/node-record.json` (`:243`).
- build_firmware: the lock, the record refusal, the record line (`:308`).
- The serial-access paragraph gives the resolver and `board` (`:388`).
- The recipe form is U36's, the flavour names U27's, Playwright U28's.

**The BACKLOG chroot paragraph (row 21).** It sits before "Kept here as the running list…" and is dated 2026-10-08. It follows §7's draft, with every clause checked against the code. The placeholders are filled from T's report and `git diff f76385a -- pyproject.toml host_typecheck.ini`:
- `<FBT outcome>`: the `FBT001`/`FBT002` entry for `tests_scripts/test_setup_toolchain_env.py` is removed, and the overrides' `S603` reason is restated.
- `<its sections>`: `[mypy-setup_toolchain]`, `[mypy-test_setup_toolchain_env]` and `[mypy-test_micropython_overrides]`.

Added beyond the draft, each from the code or a lane report:
- `toolchain/versions.toml` changes in its header comment only.
- Every command is stopped on a timeout, SIGTERM or SIGHUP.
- The ref writer's three refusals.
- The `sudo -k -n` probe.
- Node staging plus rename.
- Override directories emptied first.
- The host lwIP build is proven to run lwIP's timers.
- Both chroot legs are the host lwIP build's first compilers other than this host's GCC 13.3 on x86-64, where it is warning-free with `-Wno-sign-compare` and `SOMAXCONN=2` on `modlwip.o` only.
- The installer leg is owed: `setup` and `env` have never run to completion on this code, only `test`.
- Also owed, from T: the apt-get(8)/apt.conf(5)/dpkg(1) reading and `sudo -k`'s exact semantics. This host has no man pages, so only the binaries' strings were read.

**Other sentences U21 made false, fixed in my files:**
- CLAUDE.md:645-648: test.sh also rebuilds on a missing `toolchain-record.json`, or, on a plain run, a missing or non-plain `build-lwip`.
- tests_hardware/README.md:241-253: "so the two cannot disagree" was false. The harness resolves by vendor ID; the installer requires vendor plus the MicroPython by-id name. Now stated, with the debug-probe difference.
- README.md: "~30 s" for `test` was already stale before U21. The base baseline was 70-78 s, and T measured 161-169 s at -j2. It now reads "a few minutes", in two places.

**Grep for removed or renamed names** (`--password`, "both Unix", "builds both", `_MBEDTLS_…`, `ensure_iproute2`/`…network_manager`/`…iptables`, `node_tarball_name`, `UV_SYNC_ATTEMPTS`, "all four artifacts", `generate_bench_ap_credentials`, vendor-ID detection) across my five files: every hit is fixed. The one left is BACKLOG.md:399, the dated 2026-09-21 chroot paragraph ("builds the Unix port twice"), which is history the U36 prune owns. `generate_bench_ap_credentials()` still exists, so its mentions stay.

## Deviations (each decided on the owner's behalf, conservative and reversible; agent, 2026-10-08)

1. **No WIP E1 commit.** The lead's phase-2 go arrived before my first edit, so everything is in one commit after merging 1b43482.
2. **README Node sentence.** My first wording rewrote an allow-listed sentence ("Node comes from nodejs.org (checksum-verified … deliberately **not** from apt"), which made `test_decision_vocabulary` red twice: one new finding, one stale allow-list line. I restored that sentence's first 80 characters exactly and put the new facts (one SHASUMS fetch, the check before unpacking, staging plus rename, the node record) in a separate following sentence. The allow-list is untouched.
3. **The passwordless-sudo item is item 2.** The later items are renumbered, and the one in-repo citation is updated. `git grep "Prerequisites item"` shows only that one.
4. **Placeholders in the sudoers line** (`<nmcli>` …), not guessed absolute paths. The Pi's `which` output was not available here.
5. **CLAUDE.md three-binary sentence.** The heading is now "Three Unix-port binaries are built, not one." The 2026-09-21 owner tag moves onto the sentence about the settrace split it decided; its scope is unchanged. The third binary carries "(owner, 2026-09-30)" (A-26). The commit names this.
6. **The owner tags (owner, 2026-09-30) and (owner, 2026-10-02) are written without quoted owner words**, as the packet gives them. Rule 2 asks for the words; no step supplied them.
7. **Additions beyond the plan rows**, each a sentence U21 made false or a new behaviour in a section I own:
   - the CLAUDE.md test.sh rebuild clause;
   - the HEAP leftover-removal sentence;
   - the tests_hardware MPREMOTE_DEVICE resolver note;
   - the README serial-access paragraph;
   - the README build_firmware lock and record sentence;
   - the README "~30 s".

## Facts owed to other lanes

- **D:** my files cite "SPECIFICATION.md B.14.4" (CLAUDE.md:640, BACKLOG.md:910, HEAP:287), the plan's `modlwip_eagain` subsection. They resolve once D's heading `### B.14.4 …` lands. They also cite B.12, B.13, B.5 and Part E.5.2, all of which exist.
- **D:** I add, rename and withdraw no `@tunable` tag. The BACKLOG rows name `web.per_call_timeout_s`, `tool.bench_bridge_up_poll_s` and `tool.bench_bridge_recovery_arm_s` as Part N IDs. `test_tunables_register` does not scan BACKLOG.
- **Lead:** no allow-list lines added or retired. The README sentence above keeps its allow-list key. No API changes, raises or Any-baseline lines: docs only.

## Checks (foreground, `nice -n 19`, `/home/user/sensors/.venv/bin/python -m pytest -q -p no:cacheprovider`, one file at a time, 19:34:54-19:35:47 plus re-runs; entered in RUNS.md and marked done)

| file | result |
|---|---|
| test_decision_vocabulary | first run 2 failed (my Node sentence, deviation 2); after the fix **6 passed** |
| test_citations | **1 failed / 14 passed**, expected red only (below) |
| test_comment_block_cap | 452 passed |
| test_tunables_register | **1 failed / 14 passed**, expected red only (below) |
| test_legacy_paths | 3 passed (also after the fix) |
| test_import_placement | 7 passed |
| test_code_conventions | 23 passed |
| test_host_annotations | 12 passed |
| test_tool_help | 19 passed (run after "A-21 done") |
| test_lint_ceilings | 19 passed |
| test_mypy_any_baseline | 7 passed |

Ruff and mypy were not run: no `.py` file was touched. Baseline before any edit: decision_vocabulary 6, citations 15, legacy_paths 3, all passed. No GC stages apply (host pytest only), and no test file was grown. No MicroPython, toolchain or port-binding run was made.

**Expected reds, itemised. Every failing item is of the expected kind.**
- **test_citations** (`test_no_unresolved_citations`): exactly three unresolved tokens, all D's heading: `BACKLOG.md: SPEC B.14.4`, `CLAUDE.md: SPEC B.14.4`, `HEAP_FRAGMENTATION_MEASUREMENTS.md: SPEC B.14.4`.
- **test_tunables_register**: exactly fifteen "is tagged but has no SPECIFICATION.md Part N row" lines, all D's rows:
  - `tests/lwip_host/test_modlwip_eagain.py:14, :17, :20, :22, :24, :28, :30`: the seven `l1.lwip_host_*` (write_bound_ms, connect_bound_ms, recovery_s, rounds, spin_rounds, spin_round_max_us, spin_round_alloc_max_b);
  - `toolchain/setup_toolchain.py:93, :95, :97, :130, :240, :242, :249, :251`: `tool.remote_query_timeout_s`, `network_step_timeout_s`, `build_step_timeout_s`, `apt_step_timeout_s`, `bench_bridge_recovery_arm_s`, `bench_bridge_up_poll_s`, `node_shasums_timeout_s`, `node_tarball_timeout_s`.

## Findings (out of scope, not fixed)

1. **CLAUDE.md:1024-1026**, the chroot-recipe comment, says `apt_packages` is "used by both its `setup`/`test` subcommands". `run_test()` runs no apt (`setup_toolchain.py:1654-1690`, its own comment: "Deliberately touches neither apt …"), and the base's `run_test` did not either. The sentence was false before U21, so I left it, rather than make a CLAUDE.md edit outside a named step. Owner: whichever unit next edits that recipe; U36 moves it to B.17.
2. **HEAP_FRAGMENTATION_MEASUREMENTS.md:290-292**: the two twin recipes still pass a global `-Wno-array-bounds` in `CFLAGS_EXTRA`. The kbd variant mk they name now carries the one-file `ctr_drbg.o` rule (O), so the global flag is redundant but not false. Left; a candidate for the A-3 follow-up.
3. **Security note on the documented sudoers line** (tests_hardware/README.md:34). NOPASSWD for `timeout`, `tee` and `systemd-run` grants root for any command or file, not just the bench's own calls: `sudo timeout 1 <anything>`, `sudo tee /etc/…`, `sudo systemd-run <anything>`. That follows from `_BENCH_SUDO_COMMANDS` and the probe's whole-command rule (A.U21.26), and is acceptable under the trusted-home-LAN model. Argument-restricted rules (e.g. `tee /sys/bus/usb/drivers/usb/unbind`) would fail the probe by design. Owner-review item; any change is U26's (bench) or the next installer unit's.

## Silent-failure scan (my five files; tooling modes first)

These files are docs, so each mode was checked as "does the text claim a detection or recovery the code does not have, or hide a loss".

| # | mode | class | finding | status |
|---|---|---|---|---|
| E-1 | run killed mid-way (partial clone, no record, held lock) | 4/6 | The docs state the record is deleted first and written last, test.sh reruns setup on a missing record, build_firmware refuses one, and a second run fails naming the first pid. All match `run_setup()`/`run_test()`/`toolchain_lock()`. Nothing is claimed about a SIGKILLed installer's child (T finding 1). | covered (T 15v/15x); the doc is accurate |
| E-2 | stale record | 3 | The README describes the record as "what was built from what … input hashes" and **does not** claim the hashes are compared. Nothing compares `input_sha256` (S-5 / T finding 3). | partly covered: U27 (S's proposal); no doc over-claim |
| E-3 | re-run over a dirty toolchain | 6 | `setup`/`test` remove every `ports/unix/build-*` they do not build, including the HEAP twins, and print each removal. HEAP §M5.2 now says so, so an ad-hoc twin silently gone after a setup is no longer a surprise. | new, fixed here (doc), with the line |
| E-4 | offline run | - | `test` runs no network and no apt. The README says so; the CLAUDE.md recipe comment says otherwise (finding 1). | covered; finding 1 is pre-U21 |
| E-5 | stalled mirror (OF-57) | 3/5 | The BACKLOG paragraph names the bounded, retried, streamed apt split. The man-page reading is listed as owed, not claimed. S-6, stub install and `uv run` with no bound of their own, is not in my files. | covered (T 15m); S-6 is U27/U28 |
| E-6 | concurrent second run | 5 | The lock is documented. Readers of `build-standard` are not locked while `setup` rebuilds it (T finding 4); my files make no claim either way. | not covered: T's proposal for S/U27 |
| E-7 | bench bridge cut mid-change | 6 | CLAUDE.md, README and tests_hardware state: armed and verified before, disarmed only after address and route, left armed on failure with the fire time logged. This matches `_armed_recovery()` and `_wait_for_bridge_route()`. The tests_hardware text says the restore profile is used only around a creation, as in the code (self-heal passes `None`). | covered (T 15aa); first real proof is the owed BACKLOG row (:358) |
| E-8 | built firmware, send path under `EAGAIN` | 5 | The cooperative-retry busy wait and its bound are an owed BACKLOG row (:340), with the bound named in words (A-19). The S-1 listener-close NULL stores (silent on rp2) are **not** in my files; the lead registers them. | covered as an owed measurement; S-1 is the lead's |
| E-9 | release build carrying the tick offset | 7 | Not described in my files: B.14.5 is D's. The BACKLOG paragraph says only "a release build refuses" it, which matches `verify_tick_offset_in_build(expected=False)`. | covered (O/T) |
| E-10 | bench sudo probe | 7 | The doc states that a rule limited to other arguments fails the probe though the real call would run, so a false "missing" is explained, not silent. | covered (T 15y) |

Modes checked with no finding: first boot and factory state, boot, flash and FRAM writes, and network and time modes. None is described or changed by my edits.

## Runs started

Only the foreground pytest files above, entered in RUNS.md as one line and marked done. No background process, no toolchain, MicroPython or port-binding run, nothing reading `/root/pico-toolchain` during the A-21 freeze (acknowledged). The one helper I wrote, `scratchpad/u21/e_rewrap.py`, re-wraps text and runs nothing. `ps` shows no lane-E process.

## Files the lead must run on the merged tree (after D lands)

- `test_citations.py`: the three B.14.4 tokens must resolve.
- `test_tunables_register.py`: D's fifteen rows.
- `test_decision_vocabulary.py`: my README restoration keeps its allow-list key; D's edits are D's.
- `test_legacy_paths.py` and `test_comment_block_cap.py`, as a whole-tree sanity pass.
