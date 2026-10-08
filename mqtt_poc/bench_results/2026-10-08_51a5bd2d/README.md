# MQTT PoC bench results, 2026-10-08 on `51a5bd2d`

Run by the bench Pi4 session (`session_01HaBZru65HAV9qRRZWCG2ZY`) following `mqtt_poc/BENCH_HANDOVER.md`,
with the owner's go-ahead given in that session's conversation (owner, 2026-10-08: "read the bench handover
and start the MQTT bench run").

## Setup

| | |
|---|---|
| Commit | `51a5bd2d` (branch `claude/whole-project-audit-plan-followup`) |
| Image | `dev`, `BuildDate` 2026-10-08T09:47:36Z, firmware/website `2.0b0` (`system_after_flash.json`) |
| Image replaced | `dev`, `buildDate` 2026-09-25T12:54:13Z (`system_before_flash.json`) |
| Host | `Linux raspberrypi 6.18.50+rpt-rpi-v8 #1 SMP PREEMPT Debian 1:6.18.50-1+rpt1 (2026-09-11) aarch64`, Debian GNU/Linux 13 (trixie), 4 cores, 7.6 GiB |
| Broker | mosquitto 2.0.21-1 (Debian package), avahi-daemon 0.8-16 active |
| Session path | SSH from 192.168.85.42 over `eth0` (bridge FDB), default route via `br0`; the AP never carried it |

## Preparation

- `env --tier bench`: exit 0; bridge reused, `br0` presents `eth0`'s MAC `D8:3A:DD:28:EA:5A`.
- `fram_before_flash.json`: the old image's FRAM logs held WIFI W5 ×3 (counter 13), SGP40 W13/W11
  (counter 16) and NTP E21 (counter 3); every other module was empty.
- Flash: `machine.bootloader()` over mpremote, then `sudo picotool load -x -v build/firmware-dev.uf2`, loaded
  and verified on the first attempt. The session's one flash.
- **First boot fell back to hotspot.** After the flash the board did not join the bench AP within ~4 min;
  its console showed `WIFI Hotspot mode is active` with every task running. One station kick plus one hard
  reset (`dut_ip`'s own documented first recovery step, the bench's CYW43 reconnect behaviour) and it joined
  at 192.168.85.57 within ~25 s, NTP synced. No credential push was needed.
- `fram_after_flash.json` (taken after that reset) holds only first-boot-of-a-new-image entries: `CFGMGR_*`
  W10 `STORED_DEFAULT` / W23 `CFG_KEYS_REMOVED` (config migration), WIFI W38 `WLAN_CONNECT_FAILED` (the
  hotspot fallback above), SGP40 W33/W35 (baseline restored/written before NTP gave it a timestamp).
  `MQTTState` `disabled`; all 24 FRAM modules present, `MQTT` and `CFGMGR_MQTT` included.

## The run

```bash
scripts/run_bench_hardware_suite.sh --scope mqtt \
    --allow-persistence-writes-to=networking/identity,networking/mqtt,networking/ntp,notification/autoConfig \
    2>&1 | tee "$HOME/mqtt_bench_console.log"; echo "runner exit ${PIPESTATUS[0]}"
```

### Attempt 1: stopped at L0, no board touched

Started 2026-10-08 10:01 UTC, exit 1 at 10:21 UTC. `scripts/test.sh` (GC stage -1): every MicroPython
file passed (92 files, 4,586 tests), but the backgrounded `tests_scripts/` tier hit its 1200 s bound at 73%
(`== tests_scripts/ exceeded 1200s`), and the runner stopped before L3. Root cause, two host facts, no code
defect:

1. **The `tests_scripts/` tier is slower on the Pi4 than its bound assumes.** Run alone afterwards
   (`uv run pytest tests_scripts -q --durations=30`, nothing else running) it took **1848 s** (3195 passed,
   11 skipped). The bound is Part N `runner.tests_scripts_timeout_s` = 1200 s, set at ~5× a ~248 s
   measurement on a faster host; its row owes exactly this figure ("the pytest tier's wall clock on the
   bench Pi4").
2. **Node was not on `PATH`.** `env --tier bench` installs the `.nvmrc`-pinned Node 24.21.0 into
   `~/pico-toolchain/node/` but puts it on `PATH` only for its own subprocesses, and no shell profile on the
   Pi4 adds it. That standalone run therefore also showed 41 failures, all "node is not on PATH" (five
   files); with Node on `PATH` those five files pass, 112 of 112 in 30 s. `npm test` would have failed the
   same way.

The owner chose how to continue (owner, 2026-10-08, asked "How do I continue?": "Rerun, env overrides
(Recommended)"): rerun the whole scope with Node on `PATH` for the run and `TESTS_SCRIPTS_TIMEOUT_S=3600`
(the runner's own override), no code change.

### Attempt 2

```bash
export PATH="$HOME/pico-toolchain/node/node-v24.21.0-linux-arm64/bin:$PATH" TESTS_SCRIPTS_TIMEOUT_S=3600
scripts/run_bench_hardware_suite.sh --scope mqtt \
    --allow-persistence-writes-to=networking/identity,networking/mqtt,networking/ntp,notification/autoConfig
```

Started 2026-10-08 11:09 UTC. GC stage -1 passed in full (summary below: 92 files, 4,586 tests; the
`tests_scripts/` tier 3,236 passed, 11 skipped, now inside its raised bound). At stage 32768 one test outside
this branch failed: `tests/test_asy_uart_driver.py::test_thousands_of_back_to_back_frames_at_line_rate_lose_nothing`,
a `TimeoutError` at its 60 s wall-clock bound (Part N `l1.asy_uart_driver_hammer_bound_s`) while three other
files were overrunning their 240 s per-file bound on the loaded Pi4. Before the stage was stopped, every file
covering this branch had passed at both stages: `test_asy_mqtt_client` 43/43, `test_mqtt_codec` 22/22,
`test_asy_dns_client` 39/39, `test_asy_ntp_client` 151/151, `test_asy_captive_dns` 60/60,
`test_ntp_wifi_dns_integration` 9/9, `test_ntp_fram_system_integration` 12/12, `test_sensortask_dev` 70/70,
`test_digital_twin_webserver_concurrency_dev` 20/20. The owner directed (owner, 2026-10-08): "It is not your
task to test the UART. Your only task is to test everything around MQTT and ignore anything else so far which
does not come from your changes." The run was stopped (host processes only, no board touched) and the scope
continued with `--skip-lower-levels`.

```
== Summary: scripts/test.sh ==
Commit: 51a5bd2d (uncommitted changes)
Levels: L0 PASS · L1 PASS · L2 PASS (tests/test_digital_twin_*.py only; run_digital_twin_ci.sh not run)
GC stage: -1 (reactive default)
Counts (files): passed 92 · failed 0 · skipped 0 · deselected 0 · retried 0 · recovered 0 · vacuous 0
Counts (tests_scripts tests): passed 3236 · failed 0 · skipped 11 · deselected 0 · retried 0 · recovered 0 · vacuous 0
Counts (tests): passed 4586 · failed 0 · skipped 0 · deselected 0 · retried 0 · recovered 0 · vacuous 0
Result: PASS
Exit code: 0
```

("uncommitted changes": this results directory, untracked at the time.)

### Attempt 3: the flash step (`--skip-lower-levels`), 2 of 3 failed

Started 2026-10-08 12:00 UTC; evidence in `flash_step/`. `test_env_tier_flash_recurring_run_is_idempotent`
passed. Two failed:

1. **`test_real_gc_heap_headroom_survives_a_full_system_build`: this branch's finding.** "the built object
   graph holds more than it should: 113280 > 100000 B allocated". The bound
   (`l3.heap_headroom_after_full_system_build_max_used`) is ~14% over every pre-MQTT reading,
   87,760–87,968 B. An ad-hoc read-only board script (run from RAM via `run_isolated`, no flash write, no
   `setup()`) attributed the client's share:

   | On the board, `gc.mem_alloc()` deltas after a collect | Bytes |
   |---|---|
   | `mqtt_codec` import | 640 |
   | `asy_mqtt_client` import | 2,288 |
   | one `MQTTClient` construction | 8,432 |
   | **MQTT total** | **11,360** |

   DESIGN.md §5 estimated "about 5 KB plus the object"; the buffers are that, the rest is the client's
   `SensorReaderConfig` base, config manager and module objects. 87,968 + 11,360 = 99,328 B: MQTT alone
   takes the bound to its edge. The other ~14 KB of the +25.3 KB is not the client's and is unattributed
   (the audit base since the 2026-09-19 readings, or this branch's wiring); a second image to compare against
   would need a second flash. The bound changes only by a new derivation, never to fit a reading (audit G4),
   so it was left untouched.
2. **`test_every_fram_wired_module_gets_a_real_chunk_after_a_full_system_build`: not this branch's.** The
   device script aborts with "scd30.cfgmgr.pr is not a PrintLogHistoryStore at all (expected FRAM-backed -
   dev.toml wires fram_target everywhere)", but `CFGMGR_SCD30` is RAM-only by the owner's decision (owner,
   2026-09-29, on the FRC settings: 'no extra FRAM chunk'; CLAUDE.md). The script stops there, before the
   MQTT chunks; `fram_after_flash.json` shows `MQTT` and `CFGMGR_MQTT` served from FRAM on the running image.

The owner chose (owner, 2026-10-08, asked "How do I go on?": "Run bench step now (Recommended)"): run the
66 scoped bench tests on their own, both flash findings recorded for a later decision.

### Attempt 4: the bench step on its own

The runner's bench-step line with the scope's 66 selections (`tests_hardware/run_scopes.py mqtt bench`),
`--allow-persistence-writes-to=networking/identity,networking/mqtt,networking/ntp,notification/autoConfig`,
and a not-clean reason naming everything above. Started 2026-10-08 12:12 UTC.
