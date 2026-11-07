Lane E hand-back. Commit 26fb9be on audit/u25-e (worktree S/wt-u25sh, base 7803de8). Not pushed.

**What changed**
- **E0, Run 13's erase setup:**
  - The check now requires the planted chip's own entry. A timed-out wait, or a twin that exits, fails and names the chip and the fault. A device with no chip fails outright.
  - At base on wozi Run 13 passed, carried by BMP3XX 2 (the planted fault) plus SYSTEM 1. SH's `{'CFGMGR_NTP': 4}` log came from a launch with no fault at all (its launch line reads `faults=[]`).
  - The plant lands on wozi and dev (bmp3xx:readfrom_mem:1) and on arzi (scd30:writeto:1).
- **E1, shared boots:**
  - `shared=`/`moves=` on `@scenario`. The scenarios that may share run first, each part in D.15 order, so they run as one group on one twin.
  - The idle check after each one: twin alive, slots drained, kernel accept queue at 0 (read from /proc/net/tcp), error counts read after the drain, memory gate.
  - A failure names the scenario and the next one boots fresh. A sharing boot may only add `--test-conn-status-interval-ms` (the slot lines the idle check needs). That is my reading of "no extra runner arguments".
  - S1 race found at base (dev -1: "S1: the device reset although the step hung"): the command beat the supervisor's next pass. Fixed by waiting `_TASK_CHECK_TIME + _COMMANDED_RESET_MARGIN_S` (12 s) before the command.
- **E3, families:** required literal `family=`. webserver_concurrency 20, sensortask_integration 10, real_website_integration 9, bus_hazard_concurrency 1. New: system_commands 6, webserver_requests 3, uart_load 1.
- **E2, one CI job per stage:** `run_digital_twin_ci.sh <device> [--gc-threshold -1|32768]` runs the suite, CRC16 Run 3 and the harness at that stage only; without it, both stages as before. ci.yml matrix is device × `gc_threshold: [-1, 32768]`, the run line passes the stage, the artifact is `digital-twin-ci-logs-<device>-gc<stage>`. 20-minute limit and its tag unchanged.

**Share vs own boot:** 30 share (webserver_concurrency 16, real_website_integration 8, sensortask_integration 3, webserver_requests 2, bus_hazard_concurrency 1). 20 keep their own boot (sensortask_integration 7, system_commands 6, webserver_concurrency 4, real_website_integration 1, webserver_requests 1, uart_load 1). The 30 now take 68 s on dev instead of 170 s.

**Seen failing first:**
- 14 L0 tests (new or changed) failed on the base harness.
- Planted defects, each failing and naming the scenario: a stored write marked shared, a non-literal family, a `_still_serving` caller not stating WEBSERVER.
- On a real twin, scratch-copy scenarios: one holding a connection failed "slot still held after 10.0s"; one moving WEBSERVER unstated failed naming itself; the scenario after each booted fresh.
- Run 13 with a plant that never lands: generic failure at base, now names BMP3XX.
- The idle check found a real misattribution once (a late entry blamed on the next scenario). Counts are now read after the drain.

**Harness times, base → now (all green, zero MemoryError / "memory allocation failed"):**
| Device | Stage | Base | Now |
|---|---|---|---|
| dev | -1 | 471 s (stopped at S1) | 580 s |
| dev | 32768 | 706 s | 604 s |
| wozi | -1 | 607 s | 527 s |
| wozi | 32768 | 615 s | 534 s |
| arzi, grkizi, klkizi, schlafzi | -1 | – | 515–517 s |

**CI job estimate per device and stage, on this host:** the 15-minute target is not met, and dev is over the 20-minute limit.
- dev (measured through the script, -1): setup about 1.5 min + suite 624 s + CRC16 9 s + harness 580/604 s ≈ 21.7 / 22.1 min.
- wozi: suite 542 s (-1, measured) + harness 527/534 s ≈ 19.3 / 19.4 min.
- The four others: at most about 19.1 min. Their suites were not measured; their instances are a subset of wozi's.

**Red checks, all identical at base, none mine:**
- test_device_tomls: missing tests/_webserver_concurrency_scenarios.py.
- test_port_lock: 3 run_digital_twin_ci.sh cases ("usage: ... one of: fixture_device").
- test_no_variant_literals: stale `_NOT_YET_CLEANED` entries, including run_digital_twin_ci.sh.
- test_port_bands: `tests/test_... unknown row None`.
- test_decision_vocabulary, test_citations, test_import_placement, test_mypy_any_baseline: stale allow-list entries.
- test_tunables_register: `l2.twin_test_stdin_poll_ms` has no Part N row.

ruff, host mypy (cold), shellcheck, actionlint and zizmor are clean. My L0 file passes 34/34.

**Scan findings:**
- Class 3, twin and tooling: a ceiling refusal's warning is written after its slot is released (src/asy_webserver_service.py:880-883). Covered: a refused client sees the close only after the warning lands. A rare late entry is blamed on the next scenario, never lost.
- Class 4: `_accept_queue` ignores only a missing table file, and fails closed when nothing is listening.
- Fixed: the old Run 13 check could pass on another source's counter.
- Fixed: the two stage jobs would otherwise have uploaded under the same artifact name.

**Owed to D:**
- The script's `--gc-threshold` argument and the new job shape.
- `l2.scenario_commanded_reset_margin_s` gains a site (S1's wait). No new `@tunable`.

**Owed to the lead:**
- The watchdog's engagement can't be seen while the twin runs: the runner builds its WDT without `on_would_trigger` (run_generic_integration.py:674). A line from it would end each hung step at about 16 s instead of 24.5 s, roughly 68 s per stage. A "HUNG S1" line would replace S1's 12 s wait.
- Suite savings (not mine): Run 11 soak 190 s on fixed cycle counts, Run 9's fixed 90 s watch, Run 10 five × `--duration 15` (75 s).

**Runs:** 27 in total, each with its two RUNS.md lines.
- Exit 0: harness before ×3 (dev 32768, both wozi); after-runs; four-device harness; E0 new-check Run 13 on wozi, dev, arzi; committed-code smoke; wozi suite; the dev CI-script run.
- Exit 1, all expected: dev -1 before (S1), the first dev -1 after (misattribution, since fixed), E0 bites ×2, E1 bites ×2, diagnostic runs ×3.
- Nothing of mine is running.
