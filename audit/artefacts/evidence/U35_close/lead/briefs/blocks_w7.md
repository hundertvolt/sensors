# U35 lanes H, W and B (lead, 2026-10-21)

Each block reads `S/u35/briefs/common_u35.md` first, then its own section here, then its lane in the plan's P2.2 (lane
H, W or B; `S/u35/lane_plan.md`), the rulings its steps name (P2.4) and the LEAD NOTES (numbered items under
"## LEAD NOTES"). Step texts: `python3 -I S/u35/tools/steps.py --standing <numbers>`. About 60-80 tool calls each: at
70, finish the step in hand, commit, and hand back the rest (CHECKLIST 21). CHECKLIST 22 (disk) is binding.
A lane's first block creates its branch `audit/u35-<l>` from `f3fff0e` and its worktree `S/wt-u35<l>`
(`git -C /home/user/sensors worktree add -b audit/u35-<l> S/wt-u35<l> f3fff0e`), then runs `S/u23/rebuild.sh` on it.
Every device-script, flash, bench and runner edit lands before W6 (LEAD NOTES 7): these lanes run now for that reason.

## H1 (lane H: the tests_hardware edits and run_device_script)
Start: new lane, from `f3fff0e`. Files: lane H's (lanes.py "H"), the record script, its test and twin_record.json
excepted (H2's).
- Steps written: 3 (R-7), 5 with OF-02 and OF-05, OF-226 (R-14), 122's citation (R-25). Steps checked: 1, 2, 7, 101,
  103, 127, 129-133 (P1's rows: their evidence is your start; a "landed" part is not redone).
- Seen failing first (P2.2's lane H list): the host check requires at least one sent broadcast
  (tests_hardware/flash/test_bus_concurrency.py:232-245), bitten by an all-NAK twin; an out-of-bounds SCD30 reading is
  caught (tests_hardware/device_scripts/_shared/bus_reader_loops.py:79-81); OF-226's twin HTTP load in the bench
  loop-lag run asserts its evidence the way the twin does (R-14; collected only, its silicon run is R1's H83).
- Real hardware never: `pytest --collect-only tests_hardware` and the twin (`digital_twin/run_device_script.py`) only.
- Runs: no GC-stage files. The collect-only pass; each changed device script on the twin at both stages; the
  device-script mypy pass; the readers P2.2 names for lane H.
- Hand-back: steps by verdict; the per-device and per-mode effect of each device-script edit; H2's start state.

## H2 (lane H: OF-226's bench load, the probe's timeout, the held-SDA twin result)
Start: audit/u35-h at `76b2d7f` in S/wt-u35h (rebuilt); H1's hand-back `S/u35/handbacks/H1_final.md`; LEAD NOTES 48.
Files: lane H's, which now include tests_hardware/device_scripts/bench_facts.pyi and
tests_hardware/flash/test_memory_stress.py (lanes.py).
- OF-226 (R-14), H1's proposed form: an extra in bench_facts.pyi that runs main() on the production config; then a
  bench test in tests_hardware/bench/test_memory_stress_bench.py waits with `wait_for_script_server`, runs
  `_load.readers` at `configured_max_connections()` over `get_routes()`, and asserts every route answered (the twin's
  `_lag_load` evidence, scripts/_digital_twin_scenarios.py:989-1013) plus the lag, `main_running` and FRAM checks. The
  loop-lag host test (tests_hardware/flash/test_memory_stress.py:103-112) takes the same evidence. Collected only; its
  silicon run is R1's H83. Seen failing first through the twin where the script runs there.
- H1's class 4/1 finding: the sweep's `_probe()` (bus_topology_autodetect_and_hazard_sweep.py:72-75) treats ETIMEDOUT as
  an absent device in the reserved-address sweep. A timeout is reported as a bus fault, distinct from a NAK, seen
  failing first on a planted timeout in the twin.
- The held-SDA script's twin rc=1 ("the bit-banged read left SDA high", H1's r7/r8): match it to its entry in
  tests_hardware/twin_record.json (the recorded outcome and text at `f3fff0e`). If it matches, cite the entry; if not,
  root-cause it at line level. No failure is called known without that.
- Runs: the collect-only pass; each changed script on the twin at both stages; the device-script mypy pass.
- Hand-back: steps by verdict; the per-device and per-mode effect; H3's start state.

## H3 (lane H: the record script, test_twin_record and the shape proof; H's checks; H's last block)
Start: audit/u35-h at `50e22ab` in S/wt-u35h (H2's `e9fd1c7` plus the lead's prerequisite triage, LEAD NOTES 53);
H2's hand-back `S/u35/handbacks/H2_final.md`. Files: scripts/record_twin_instrument_runs.py,
tests_scripts/test_twin_record.py, tests_hardware/twin_record.json (shape proof only), and H's for the checks.
- H2's class-4 thread (test side): in tests_hardware/flash/test_memory_stress.py a `_lag_load` reader that dies of an
  unexpected exception leaves only a pytest thread warning. A reader's death fails the test naming its exception,
  seen failing first on a planted raising reader in the twin.
- Relay under `## D` H2's two doc facts: tests_hardware/README.md:826-834 ("the bench round only", "skipped unless the
  bench bridge is configured") is stale, and SPECIFICATION.md:12629's row also names the bench script timeout.
- Step 140 with OF-229 (R-20). Seen failing first: a sibling test broken in a scratch copy is charged only to its own
  scripts.
- twin_record.json: commit only a record that your changed script produced for step 140's new shape, never a hand edit
  (LEAD NOTES 8); the lead re-records it on the merged head at W6. test_twin_record goes red on any lane's `src/` edit
  until then, which is expected.
- H's complete checks: the readers P2.2 names, every device_scripts reader (U32 lane T's list), the 17 scans, the
  silent-failure scan of every file lane H changed.
- Hand-back: steps by verdict; the checks.

## W1 (lane W: the web files)
Start: new lane, from `f3fff0e`. Files: js/shell.js, tests_js/shell.test.js, tests_js/mock-data-compose.test.js,
tests_js/live-backend-put-matrix.test.js. LEAD NOTES 1: shell.test.js moved at `f3fff0e`; re-locate its sites.
- R-29's findings in these four files (OF-144 and the others it assigns there; steps 174-179 are check-only). Seen
  failing first: a reflash between page load and the first watch is seen; a planted format the compose branches miss is
  named; a new put-matrix skip fails until listed.
- Lane U adds a dev-only dispatch key, `UartHazards`, to PUT /status and to js/mock-server.js (U's head `962602d`, read
  only; LEAD NOTES 33 and 41). State whether the put-matrix test needs a row or a listed skip for it once the lanes
  merge, and write the row now if it reads from a file in your set.
- Runs: every npm run in `unshare -n S/u24/ns_xdg.sh` (it binds ports; CHECKLIST 12), each changed test file's suite
  and the JS lint and typecheck.
- Hand-back: findings by verdict; W2's start state.

## W2 (lane W: the tests_scripts hygiene)
Start: audit/u35-w at `1b638f1` in S/wt-u35w (rebuilt; node_modules links to S/wt-u8's, lock hashes equal); W1's
hand-back `S/u35/handbacks/W1_final.md`. Files: tests_scripts/test_definitions_js_mirrors.py, test_host_text_encoding.py,
test_port_lock.py, test_tool_help.py, _repo_scan.py, test_lint_ceilings.py, test_device_script_config_schemas.py.
- R-29's findings in these files (OF-197, -199, -206, -207, -212). Seen failing first: a planted non-literal
  `encoding=` fails; a stray ruff ahead on PATH fails; a skipped schema site is named.
- OF-206: test_citations (U34 13.3 s) comes under 10 s through the shared scan, every check kept; timed paired against
  `f3fff0e`.
- Runs: each changed file and its readers (readers.py's list for these files), the 12 commit checks.
- Hand-back: findings by verdict; the times; W3's start state.

## W3 (lane W: W1's remainder, then the web tier; W's last block)
Start: audit/u35-w at `0d33534` in S/wt-u35w; W2's and W1's hand-backs; LEAD NOTES 51 and 54. First, W2's red:
test_no_variant_literals fails on `'arzi'` at tests_js/live-backend-put-matrix.test.js:34-35 (W1's `EXPECTED_SKIPS`
keys); key the expected skips by what the device wires, as the rest of the suite does, every skip still checked. Files: lane W's JS files (lanes.py), which now include
js/main.js, js/app.js, tests_js/_live_matrix_command.js and tests_js/_source_constants.js.
- OF-144's wiring: js/main.js (:34-41) and js/app.js (:87-94) pass `pageBuildDate: buildDateOf(document)` to
  `startShell()`, so a reflash between page load and the first watch reloads the page in production too; seen failing
  first in a test that drives each entry.
- The put matrix's not-driven status actions become a checked map (each status dispatch key is probed or listed as not
  driven with its reason), seen failing first on a planted new key. After the merge, lane U's `UartHazards` (dev only)
  must appear in it; W1 named it in a comment.
- `readStringSetConst` (tests_js/mock-data-compose.test.js) moves into tests_js/_source_constants.js beside its kind
  (SPECIFICATION.md G's reuse rule), no behaviour change.
- OF-214's seeding (tests_js/_live_matrix_command.js:60-62, offline-safe SSID and DNSFallback in the matrix twin's
  config dir): seeding SSID switches the twin's boot from hotspot to STA for every case. Take it only in a form that
  loses no case's mode coverage (the hotspot cases keep running in AP), stating each case's mode before and after; else
  leave the two arzi skips listed with that reason and stop the item.
- The web tier in its own namespace (`unshare -n S/u24/ns_xdg.sh`), the put matrix paired against `f3fff0e` (about 12
  min each run, so one pair); the 28 readers readers.py lists, plus the 17 scans.
- Hand-back: steps by verdict; the times; the checks.

## B1 (lane B: the B3 documents and the 2**30 build)
Start: new lane, from `f3fff0e`. Files: audit/b3/* (new), audit/sweeps/ticks30_build.sh (new); scripts/test.sh is
B2's.
- A.U35.01 first: it opens `audit/b3/`, before 137, 138, 141 and 153. Then steps 102 (PROC.022), 104, 137, 138, 141,
  153 and 108 (P1's rows; their texts by steps.py). Hardware cells are parked, as the rows say.
- 108, the 2**30 build: `audit/sweeps/ticks30_build.sh` builds a scratch Unix port with a 2**30 ticks period from a
  scratch copy of the pinned checkout, never the shared toolchain build, which other runs use (lead rule: a shared
  binary is never rebuilt while in use). Seen failing first: it trips OF-32 at base (`f3fff0e`) and passes on lane Y's final head `5cf361c` (R-30's
  fix). Also run the wrap tests V1 and Y3 wrote against it on lane V's head (read only, `S/wt-u35v`; V1's flash-stall
  fix and Y3's UART link fix), and state each verdict. Relay `<T30> <hash>` under `## B` with the result.
- Runs: the readers P2.2 names for lane B that your files reach; test_citations and test_decision_vocabulary on your
  head (audit/ files carry audit IDs, as everywhere in audit/).
- Hand-back: steps by verdict; the 2**30 results; B2's start state.

## R2 (root cause only: the idle listener that outlives `comm.clear()`; nothing committed)
Start: read only. Run from `S/wt-u35base` (detached at `f3fff0e`, rebuilt; never edit it) and from lane H's head
`S/wt-u35h` (`7a7d01a`, read only); planted or probe copies go under `S/u35/laneR2/` and run from there. H3's hand-back
`S/u35/handbacks/H3_final.md`; LEAD NOTES 58. A red is never called a flake or "known": it ends in a root cause at line
level, or in the exact runs and probes that leave it open.
- The failure: tests_hardware/flash/test_uart_crossover.py
  `test_an_idle_listener_polls_at_the_idle_rate_not_the_transaction_rate`, which runs
  tests_hardware/device_scripts/uart_idle_poll_rate.py on the twin, fails at both GC stages: "a listener outlived
  comm.clear() and was cancelled (fast, idle, fast, idle): [True, True, True, True]" (test_uart_crossover.py:156).
  It was hidden behind the script's file-wide record reason (tests_hardware/twin_record.json, the script's entry).
- The script (:73-77) expects `uart_listen()` to end after `comm.clear()`; `clear()` (src/asy_uart_comm.py:1053-1066 at
  `f3fff0e`) cancels only the pending read. Trace, at line level: what `clear()` does to a listener parked at each of
  `uart_listen()`'s awaits, on the pinned asyncio (`extmod/asyncio/` under `/root/pico-toolchain`, read only) and
  through the twin's UART (digital_twin/machine.py); whether silicon differs at that await (ports/rp2's machine UART and
  the driver's `ready()` path); what SPECIFICATION.md Part J says `clear()` does to a listener; and since which commit
  the script and `clear()` disagree (`git log -S` on both, `-- . ':!arduino'`).
- Run the one test through the twin (H3's `S/u35/laneH/h3/record.sh` and `record.log` show the invocation) at both
  stages; one heavy process at a time.
- Verdict, one of: a product defect (its file and line, the fix, its class, the effect on dev in each mode, and whether
  the change is Class A or B for UART_C_PORT_CHANGELOG.md, since the UART module is a two-implementation contract and
  its wire format is not touched); a twin fidelity gap (the twin file and line); or a stale test expectation (the line,
  the corrected expectation, with Part J's text).
- Hand-back (at most 30 lines): the root cause, the evidence paths, the fix with its file and lane (lanes.py), and the
  per-mode effect.
