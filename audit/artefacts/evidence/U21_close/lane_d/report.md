# U21 lane D: final report (SPECIFICATION.md)

Branch `audit/u21-d`, worktree `scratchpad/wt-u21d`. Commits:
- e9c4fd7: WIP D1 (phase 1).
- 20c85cb: merge of `audit/u21-api` at 1b43482 (T final).
- **16ecb04**: phase 2.

Only `SPECIFICATION.md` was edited. Nothing is pushed. At 16ecb04 the code is byte-identical to 1b43482 (`git diff 1b43482 HEAD` touches only SPECIFICATION.md), and every fact below was written from that code. Facts were checked against:
- the pinned checkout `/root/pico-toolchain/micropython` (v1.29.0, pico-sdk 2.3.0, picotool 2.3.1, lwIP and mbedtls as vendored);
- the RP2040 datasheet in `datasheets/pico w/`.

## Parts and sections changed

| Section | Plan row | State | What changed |
|---|---|---|---|
| A.1 tree line | B2 | applied | `setup_toolchain.py` "setup/test/env/board - … the three Unix-port builds" |
| A.5 recovery ladder | A-20 | applied | The `ERR_MEM` sentence now gives the override's `EAGAIN` (B.14.4; owner, 2026-09-30) and the cooperative busy-wait cost. |
| B.1 item 1 | 3 | applied | picotool's real rule: pico-sdk's major version, and at least the version pico-sdk requires. |
| B.2 | 32 | applied (U21 stage) | Code-block comments now use the help-text wording, plus the path-character limit and a `board` line. "three Unix-port interpreters", with both owner tags. The timing is stated as measured at the split. The exclusive flags are noted. |
| B.3 | 33, 3 | applied (no `[stubs]`, U27) | Step 1: the pin line, the checked-copy writer and its refusals. Step 3 appends "(narrower than pico-sdk's own rule, B.1)". Step 6: the readbacks. New step 7: the record. Also the typed-table paragraph and the lock/record/carry-over/leftovers/notices paragraph. Clones: incomplete ones are refused, and a retry removes its own partial clone. |
| B.4 | 34 | applied | `--preserve-env`. Budgets, streaming, sessions and signals, including the SIGKILL limitation the lead asked for. Retries, secrets, and the three-step apt sequence. The locale pointer is now B.7. |
| B.5 | 35 | applied | Tree gains `toolchain-record.json`, `.toolchain.lock`, `build-lwip`, `build_overrides/`, `node/`, and "picotool … only when its tag changed". New paragraphs: the lock; picotool skip/USB/shadow; Node; leftovers (including A-4's no-record case). |
| B.6 | 67 | applied | Step 2 "zero errors and warnings". Steps 4 and 6 name their readbacks. Step 8 is (a)-(c), citing B.14.4. Closing line: three kept Unix ports, the record after them. |
| B.7 | 36 | applied (2) | A "Every build is warning-free" paragraph. The host build's two `modlwip.o` flags are listed with their reasons (A.U21.12 gate). (1) already landed at `:1230`; (3) is U36. |
| B.7.1 | 36, A-3 | partly (2b corrections only, per ruling 3) | The two false sentences are corrected: the pin vendors mbedtls 3.6.6 `0bebf8b`, which contains `292b96c0a`; the suppression is one file in the generated build files. Reason text: "not yet re-checked on a GCC ≥ 14 host … (agent, 2026-10-08)". The GCC bug's status is "unread here". The full branch text waits for a GCC ≥ 14 build (phase C or the owner's trixie leg). |
| B.10 | 5 | applied (U21 stage) | The cache key hashes the three files. The runner identity is U28's. |
| B.11 | 37 | applied (U21 stage) | (1) "then run the platform re-check …" (A-25); "the Unix ports". (3) The lock, the record refusal and print. The generator's rename (OF-41). |
| B.12 | 38 | applied (U21 stage) | (2) the board resolver and `board`; (3) `$BENCH_AP_PASSWORD` (owner, 2026-10-02); (4) the command table, the sudo probe and `sudo tee`. (1) landed; (5) is U36. |
| B.13 | 39 | applied (3) | New paragraph: the installer arms its own recovery timer. Covers the restore profile read at run time, verified armed, the poll, disarming only after success, and leaving it armed on failure. (1) and (4) landed; the rest is U36. |
| B.14 intro, general shape, first test | 70 | applied (U21 stage) | Count: "four implemented, one of them a test-only override, and one documented and not built". Covers the `_embeddable` refusal, the fresh directories with their five names, "proven in the built artefact", the test-only clause (without "build information names it", U27), and "one diagnostics check, B.7". |
| B.14.1 | 41 | applied (3) | The Verified paragraph: every Unix build re-proves the override through the `.pp` readback, for all three builds; "all six devices then defined"; "every Unix-port build applies this". The fix bullet gains the sentinel and the mbedtls rule. |
| B.14.2 | (blast) | applied | The board cmake's quoted include, the `include('…')` relay, the mbedtls rule, and the tick-only extra include line. |
| B.14.2.1 | 68 | applied (U21 stage) | The stall sentence names the override "(B.14.4, the `modlwip_eagain` override; owner, 2026-09-30)". The cite is now `:801-813`. "Not yet reproduced on silicon" stays until phase C. |
| **B.14.4** (new) | 66 | applied | `modlwip_eagain`: the problem, the change, the mechanism, the anchors, the post-build proof, and the host build `build-lwip` (its files, make variables, anchors and proof). Also S's host measurements, the sensitivity record, the cost, and the removal trigger. |
| **B.14.5** (new) | 69 | applied (U21 stage) | `tick_offset_test`: what it does (datasheet §4.6.2 verified), why ('Test build with a starting offset', owner, 2026-10-01), mechanism, anchor, release refusal, the one `dev` proof, cost and trigger. It has no "build information" clause (that is U27's). |
| B.15 | B2 | applied | A bullet on `typings/.stub-spec`, the print line, the wipe, and dropping the record before install. |
| E.1 | 45 | applied (U21 stage) | (3) The lock sentence. (6) The lwIP host files paragraph: `run_test_file`'s third argument, L1, no host port, not under `--coverage`, and the basename/non-empty check. |
| E.3 | B2 | applied | The rebuild conditions (record, `build-lwip`) and the second L1 set. |
| E.5.2 | B2 | applied | "builds the two as separate binaries"; the third build carries no settrace; the cache key's two files; `build-lwip`'s plain probe. |
| E.6.1 L1 row | (sentence U21 made incomplete) | applied | Adds `tests/lwip_host/test_*.py` on `build-lwip`, not under `--coverage`. |
| E.10 | B2 | applied | The `Skipped:` line for the lwIP files under `--coverage`. |
| Part F intro | 43 | applied (Stage 1) | Two paragraphs: the opening checklist, items 1-10 (10 is the dynamic-import item), without the Workarounds-table clause (U26); and the out-of-tree paragraph. F.1's closing paragraph is deleted. |
| F.1 | 2 | applied (Stage 5) | The picotool clause. Cites: pico-sdk `tools/CMakeLists.txt:146, :165-169` and picotool 2.3.1 `CMakeLists.txt:380`. |
| F.7 | 46 | applied (Stage 2) | Row 14 "every Unix build". Rows 23-30 for `build-lwip`: loopback netif with 4 pairs, 10,400 B, arena copy and `ENOMEM`; struct sizes and `MEM_ALIGNMENT`; `IPV6_FRAG_COPYHEADER`; the event hook against PendSV; asserts, with the listener close as one factual sentence; lwIP start and `LWIP_RAND`; the `modlwip.o` flags and backlog; select's 1 ms sleep. |
| F.9 | 42 | applied (Stage 2) | New `modlwip_eagain` row. The mbedtls row's "Where" follows A-3. The SIGINT row's "Where" is now every Unix build. "Two Unix binaries" → "A settrace-free test rig beside the `sys.settrace` binary". New row for the host build's two `modlwip.o` flags. |
| H.7 | B2 | applied | One send-path sentence in "The PCB count is the small part." |
| Part N | §3 all → D | applied | See below. `test_tunables_register.py` is green. |

**Nothing at U21:**
- B.10 (2)/(4)/(5): U28.
- B.11 (2)/(4)-(8): U1/U26/U27/U36.
- B.12 (5) and B.13 (1)/(2)/(5): U36.
- B.14.1 (1)/(2): U25/U36.
- E.1 (4)/(5)/(7): U24/U27.
- F.7 (2)/(4)/(6)/(8): U14/U24/U35/U36.
- M.SPEC.088's other stages are landed or later.

## Part N

**Tags added, 15 rows:**
- `l1.lwip_host_*` ×7: write_bound_ms 250, connect_bound_ms 200, recovery_s 15, rounds 20, spin_rounds 1000, spin_round_max_us 20000, spin_round_alloc_max_b 64.
  - Site: `tests/lwip_host/test_modlwip_eagain.py`.
  - Basis: "estimated (agent, `a2d7ee2`) — measurement owed: … on CI at `TEST_PARALLELISM=4` and on the bench Pi4, L1", with S's measured worst cases in the basis or margin.
- `tool.*` ×8, all with site `toolchain/setup_toolchain.py`:
  - remote_query_timeout_s 120, network_step_timeout_s 1800, build_step_timeout_s 3600, node_shasums_timeout_s 60, node_tarball_timeout_s 600: basis estimated (agent, `8c38f9d`).
  - apt_step_timeout_s 150, bench_bridge_recovery_arm_s 300, bench_bridge_up_poll_s 90: basis estimated (agent, `5b6dc1b`).
  - These commits come from `git log -S`.

**Rows updated:**
- `tool.uv_sync_attempts` names every retried network step, as the code calls `run_retried()` at 1b43482.
- `tool.uv_sync_backoff_step_s`.
- `tool.apt_acquire_timeout_s`: the download is the retried step; `update` runs once, non-fatal.
- `tool.preprocess_timeout_s` (O's site): its dependants are now the four proofs.

**Not done:**
- No tag was renamed or withdrawn.
- No `l4.lwip_spin_concurrent_request_max_s` row (A-19). B.14.4 names the bound in words.
- The untagged constants T listed (`_STOP_GRACE_S`, `_CURL_SLACK_S`, `_BRIDGE_POLL_STEP_S`) stay untagged as mechanism constants. B.4 and B.13 state their values in prose.

## Checks (foreground, `nice -n 19`, `/home/user/sensors/.venv/bin/python -m pytest`, at 16ecb04)

| check | result | wall |
|---|---|---|
| test_decision_vocabulary | 6 passed | 10.8 s |
| test_citations | 15 passed | 8.4 s |
| test_comment_block_cap | 452 passed | 3.5 s |
| test_tunables_register | 15 passed | 3.6 s |
| test_legacy_paths | 3 passed | 1.6 s |
| test_import_placement | 7 passed | 6.1 s |
| test_code_conventions | 23 passed | 2.5 s |
| test_host_annotations | 12 passed | 1.6 s |
| test_tool_help | 19 passed | 4.4 s |
| test_lint_ceilings | 19 passed | 8.9 s |
| test_mypy_any_baseline | 7 passed | 0.4 s |
| ruff (8 scopes) | All checks passed | — |

**mypy was not run:** no Python file changed in this lane.

**History of red checks:**
- `test_tunables_register` was red before Part N (5, then 8 `tool.*` rows missing).
- `test_citations` failed once on my own `src/extmod/modlwip.c` (B.14.4's file list). I fixed it to `<variant>/src/extmod/modlwip.c`.

**Tests and runs:**
- I grew no test file, so there are no GC stages or L0 times to report.
- Allow-lists unchanged: both "only shrinks" tests pass, so no allow-listed sentence was touched.
- No toolchain, MicroPython, background or port-binding run was started, and no RUNS.md entry was needed. Every run was a foreground pytest of a few seconds, plus ruff. Nothing of mine is running.

## Differences between the reports and the code (the SPEC follows the code)

**T's budget table (T.md §5) against `setup_toolchain.py` at 1b43482:**
1. **Node tarball unpack (`tar -xJf`).** T lists it under `tool.remote_query_timeout_s`. The code runs it on `_BUILD_STEP_TIMEOUT_S` (`setup_toolchain.py:1128`). B.4 and Part N say build budget.
2. **The frozen-verify run** (`run_frozen_verify_on_unix()`). T lists it under `tool.build_step_timeout_s`. The code runs it on `_REMOTE_QUERY_TIMEOUT_S` (`:1520-1524`). B.4 and Part N list it with the probes.

**Packet against code:**
- A.U21.09's copy header "at <pinned ref>": the code writes "of MicroPython 1.29.0", read from `py/mpconfig.h`. The SPEC says "naming the MicroPython version it came from".
- The `.c.obj` readback: the code uses `.o` (the lead's note). The SPEC states `.o` and cites pico-sdk.

## Deviations

Each is conservative and reversible, decided on the owner's behalf (agent, 2026-10-08).

1. **B.14 "why not `CFLAGS_EXTRA`":** I wrote the 2a form "the way `MICROPY_PY_SYS_SETTRACE=1` does it", not 2b's "… and the one-file mbedtls flag do it". Under branch 2b the mbedtls flag left `CFLAGS_EXTRA` for generated per-file rules, so the 2b sentence would be false on the code.
2. **F.1:** "2.3.0 or a later 2.x builds". The merged change's `<v>` is `picotool_VERSION_REQUIRED` 2.3.0; the action's "2.3.1" would wrongly exclude 2.3.0. The picotool cite names 2.3.1, the derived tag actually cloned, not the action's "picotool 2.3.0".
3. **Part F intro:**
   - The dynamic-import item is numbered (10).
   - The out-of-tree paragraph reads "whose generated build files also carry the GCC ≥ 14 array-bounds workaround", which is the 2b fact, instead of "and the GCC ≥ 14 array-bounds workaround".
4. **B.7.1, branch 2b:** the reason reads "not yet re-checked" (ruling 3: nothing was measured), not "persists on GCC <version>". GCC bug #121044 "unread here": gcc.gnu.org answered 403 through the proxy on 2026-10-08.
5. **B.14.5:** the title uses the code's name `tick_offset_test`. "How the test build is requested" is decided as: only a direct `build_firmware(..., tick_offset_test=True)` call, with no command line at U21, since the rollover runner is unwritten (agent, 2026-10-08). "Cost" reads as one flash cycle inside the round's budget, with no claim about a runner.
6. **F.9:** one row beyond the packet, for the host build's two `modlwip.o` flags, so that F.9's "every workaround" stays true. Two existing rows reworded (SIGINT "Where", the settrace title).
7. **Sections no step named, made incomplete by U21:**
   - E.6.1's L1 row;
   - B.14.1's fix bullet;
   - B.14.2's generated-file sentence;
   - B.4's locale pointer (B.7.1 → B.7).
8. **B.2:** a `board` quick-start line. B.3's record step is numbered 7 (merged change; A.U21.03 says 8).
9. **Wrapping:** paragraphs were rewrapped to 100 columns where my edits overflowed. E.1's first paragraph was rewrapped whole, which adds line churn only.

## Facts for the lead and E

**Headings E can cite:**
- B.14.4 (`modlwip_eagain`) and B.14.5 (`tick_offset_test`);
- B.13's installer paragraph;
- B.5's leftovers and lock;
- B.12's resolver;
- Part F's opening checklist (Part F's first paragraph; no heading ID of its own).

No SPEC heading was renamed or removed. B.14.3 (littlefs) is still in place until U36.

**For the lead:**
- Allow-lists: no lines to add or retire.
- No new raises and no Any-baseline lines.
- Files to run on the merged tree with E: `test_citations.py`, `test_decision_vocabulary.py`, `test_tunables_register.py` and `test_comment_block_cap.py`.

## Findings for the scan record

1. **B.10.1 quotes a message the code does not print** (pre-existing, not U21-made). B.10.1 (and `ci.yml:651`'s comment) say a cache miss fails on `build_firmware.py`'s "no toolchain found". The script prints "error: no MicroPython checkout at <dir> - run `uv run toolchain/setup_toolchain.py setup` first", and since U21 also "the toolchain at <dir> is incomplete or predates the build record …".
   - Not silent: the build still fails loudly.
   - Left unedited so that the SPEC and `ci.yml` do not diverge. Proposal for U28 (the `ci.yml` owner): correct both together.
2. **S-1 (listener close writes past the LISTEN pcb on rp2):** stated in F.7 row 27 as one fact about the host build, with no fix or decision (lead's instruction).
3. **S-5 (`input_sha256` never compared locally):**
   - The SPEC claims no local detection. B.3 says the record holds the hashes, and E.5.2 says CI is covered by the cache key and that `scripts/test.sh` asks each binary its variant.
   - Still open for U27/the register, as S proposed.
4. **T #1 (SIGKILL leaves the own-session child running):** documented in B.4, as T proposed and the lead asked.
5. **T #4 (`scripts/test.sh` reads `build-standard` unlocked while setup rebuilds it):** B.5 describes the lock exactly as the code takes it (setup/test/env and `build_firmware.py`, not `test.sh`'s binary use). It does not claim the readers are covered. Still open for the register.

**Scan of my file:** for each tooling mode (a killed run, a stale record, offline, a dirty re-run, a stalled mirror, a concurrent run, a bridge cut mid-change, and EAGAIN and the tick refusal for the firmware), the SPEC's description matches the code's behaviour. No SPEC sentence claims a detection or recovery the code lacks.
