# Round 1 on the bench (2026-11-05)

Round 1's run sheet (rows 1-16b) as one runner, `round1.sh`, beside its helper `round1.py`. It reuses October's
runner (`../hw_handover/`: its functions, `handback.py`'s filter, `aggregate.py`, the `mp/` scripts). The owner's words:
"The bench test may go into detail, running a timed script is fine, especially the option to roughly define
breakpoints was great. It cannot run truly over night. It should live in the branch it was running past time."
(2026-11-05); "interruptible anytime without losses (max 10 minutes wait time)" and "The sessions shall push regularly
and dump all details into a single hand back file" (2026-10-28).

## Before anything

- **Session and gate.** Start a fresh session on the bench Pi4 and check out `claude/u35-bench-campaign`, which carries
  this folder. Get the owner's go-ahead in that session's own conversation (CLAUDE.md). This document is not it.
- **Environment.**
  - `DUT_IP`: the board's address on the bench network, the one the harness's `--dut-ip` takes. Every pytest step
    gets it, so each session saves `/status` before it resets the board. Step 1's `/status`, the `/status` read after
    every step (row 16), the BuildDate checks (3, 15), 12d and 12f need it. Unset, those reads say "DUT_IP unset".
  - `GC_CONTROL_IMAGE`: steps 3g-5g's image; `LWIP_CONTROL_IMAGE`: step 8's (both below). `CH13=1`: step 13.
    `FRAM_HOURS`: step 11, whole hours, default 2. `FORCE_WEAR=<id>`: below. `MPREMOTE_DEVICE`: optional.
- **The two control images.** The bench session builds each in a throwaway worktree, never committed, with
  `uv run scripts/build_firmware.py dev --output <abs>/<name>.uf2`; the owner need not be there.
  - **GC (OR40.a (3), the owner's release proof):** the boot entry's `gc.threshold(32768)` line removed
    (`buildgen/codegen.py:835`), as `gc_control.uf2`. Build it after step 2 and as the last rp2 build before 3g: `env`
    removes the toolchain's rp2 build directory, and `flash/test_modlwip_listener_close.py` compares that build with
    the record it is given. 3g-5g pass `--image-record <abs>/gc_control.json` (the harness's "Verify the image").
    Unset, 3g, 4g and 5g each print a NOTE and are owed.
  - **lwIP (BACKLOG's send-stall protocol, owner 2026-09-30):** the `apply_modlwip_eagain_override()` call removed
    (`toolchain/setup_toolchain.py:671`), as `control.uf2`; its record must read `"overrides": []`. Step 8b refuses
    without it, since a pass is never run again.
- **Opt-in wear** (steps 7f, 7b, 8f, 8b, 10b, 15; `WEAR.txt`; 7 and 8 split per tier). The owner, 2026-11-05: "As this is the final verification,
  option a with full test coverage is fine. The only restriction I want to have: the tests causing wear shall be
  conducted when the associated code behind is as final as possible, and if the wear related tests pass does not have
  to be touched again. I want to run these tests now, but still avoid having to re-run wear causing tests for
  unrelated reasons."
  - A wear step refuses until `WEAR.txt` has a line starting `cleared:`. The audit session writes it, with no run
    active, once it has read every non-wear result and judged the code behind the wear tests as final as it can be.
  - A pass (rc 0, every `Result:` PASS, or NOT CLEAN for the lower levels run in 4a) appends `passed: <id> <UTC>`;
    the hand-back commit carries `WEAR.txt`. A passed step is skipped with a NOTE unless `FORCE_WEAR=<id>`.
  - A failed wear step, once fixed, reruns only its failed tests: `PYTEST_K='<their names>' run <id>` (lead,
    2026-11-05), so its passed tests are not spent again.
  - The code each one exercises:
    - 7f, 7b: `src/asy_config_manager.py`, `src/asy_webserver_service.py`, `src/asy_scd30_driver.py`,
      `src/asy_neopixel_driver.py`;
    - 8f, 8b: `scripts/build_firmware.py`, `toolchain/setup_toolchain.py`, `toolchain/micropython_overrides.py`,
      `buildgen/`, `devices/dev.toml`, `src/asy_uart_comm.py`, `src/asy_uart_link_driver.py`, `src/asy_crc_checks.py`;
    - 10b: `src/asy_wifi_service.py`, `src/asy_captive_dns.py`, `src/asy_udp_socket.py`,
      `src/asy_webserver_service.py`, `src/asy_config_manager.py`;
    - 15: `toolchain/micropython_overrides.py`, `scripts/build_firmware.py`, `src/asy_system_service.py`, and every
      `src/` module using `ticks_diff()`/`ticks_add()`.
  - A later change that alters the bytecode or built image of those is the only reason to re-run a passed wear step,
    and the owner decides it.
- **Never:** `nmcli`, `iw` or `iptables` by hand; `mpremote cp`, `rm` or `mkdir`; a `ResetErrors` PUT outside 12d;
  printing a config file; another device's image.

## Commands (from the repository root)

```bash
H=audit/artefacts/evidence/U35_close/redo/hw_round1
bash $H/round1.sh list                      # steps: time, wear, how a STOP ends each, what each needs
DUT_IP=<addr> nohup bash $H/round1.sh run 4a 5g > /dev/null 2>&1 &  # one day's range; TO defaults to FROM
bash $H/round1.sh summary                   # the hand-back's verdict table, wear line and aggregate
touch $H/STOP                               # end after the running step
```

`run` first continues the fetched bench branch. After every step it reads `/status` and rebuilds `HANDBACK.md`, then
commits it `[skip ci]` and pushes it. The logs stay in `$H/logs/` (git-ignored, they hold the LAN address).

## Stopping

- **`touch $H/STOP`, Ctrl-C, `kill`:** the run ends after the running step. A signal also pushes the partial log at
  once. `kill -9` pushes nothing, but the logs stay, so the next launch's push carries them.
- **How the running step ends:**
  - pytest steps (4g, 5g, 4b, 5, 7f, 7b, 9, 10a-10h, 10m): SIGINT to their pytest within about 10 s; pytest prints its end.
  - 4a (host only): SIGINT to the whole step.
  - 11: after its 9-minute slice.
  - 3g, 3, 8f, 8b and 15 hold a flash cycle and always run to their end (8b and 15: up to about 1.2 h and 3 h).
- **A rerun.** A stopped step reruns from its start (`run <id>`). Its log keeps every run; the verdict is the newest.
- **A standard-state stop.** If a session stops on a standard-state deviation after an interrupt, repair it by hand
  as `tests_hardware/README.md` says, then rerun.

## Day plan (each launch at most about 10 h; the times are estimates, none measured on the Pi4)

| day | launch | about | needs |
|---|---|---|---|
| 1 | `run 1 2`, build the GC control image, `run 4a 5g` (= 1-5g) | 9 h | `DUT_IP`, `GC_CONTROL_IMAGE` |
| 2 | `run 3 10m` | 7 h 30 | - |
| 3 | `run 11 16b`; `CH13=1 run 13` once the owner has the channel-13 AP | 2 h 50 | the optional scope (12f) |
| opt. | `run 10c`, then 10d, 10e, 10f, 10g, 10h: one a day (10m ran all six at mid) | 6 h 20 each | - |
| - | the audit session reads and fixes; affected non-wear steps rerun on the fixed image; then `cleared:` | | |
| wear 1 | `run 7f 10b` | 4 h 30 | `LWIP_CONTROL_IMAGE`, the NeoPixel rig |
| wear 2 | `run 15`, then item 14 and 16b's power cycle | 4 h | the owner at the bench |

Wear in the round: FC 9 (3g 1, 3 1, 8f 1, 8b 4, 15 2), FS owned 126 (7f 72, 7b 50, 10b 4), NVM 14 (7f 6, 7b 7, and the SCD30 start in 4g),
prerequisite file writes up to 422 (the tiers twice, 136 + 66 each, then 10a, 10m and 10b).

## What each step expects, where it differs from the sheet

- **3g-5g, the GC control image** (no threshold). No node is known to fail on 4g or 5g. No hardware test checks the board's own threshold: every device script sets its GC stage itself
  ("never inherited"), and the image check compares device, BuildDate, lwIP, `maxConnections` and the tick offset.
  The production-mode scripts (`loop_lag_under_combined_load.py`, `boot_stretch_final.py`) do inherit it: on this
  image they run at -1, which is the proof's point, not a known failure. `test_heap_layout.py`'s note names
  `build/firmware-dev.json`, not the record given, so on 4g it names the wrong image.
- **4b, the flash tier.** No node is known to fail. `test_no_frame_is_lost_while_interrupts_are_off[none]` and
  `[crc16]` now run their windows: dev's responder ring is 8192 B (snapshot 37, `ecca7f3b`), above the 4,608 B of
  the 400 ms window; the test reports the ring's heap cost. The loop-lag skip no longer reads "unexpected
  skip": `scripts/_hardware_verdict.py`'s `PERMANENT_SKIPS` lists it since `d6bd2d45`.
- **5 and 5g, the bench tier.** `run_bench_hardware_suite.sh` re-runs L3 under `set -e`, so any L3 FAIL would
  stop it before `tests_hardware/bench`, after 17 more scratch builds. The steps run the runner's own bench line
  instead (`_require_clean_hardware_run.sh --runner run_bench_hardware_suite`); a pass reads NOT CLEAN, naming 4a.
- **Rows 6 and 16 are no steps.** They are the `/status` read after every step: `ResetReason` in the verdict table,
  and every logger's `errcount` (SGP40's after 4b and 5 is row 6) in that step's log.
- **7f, 7b, gated.** Both tiers run `-m "persistence_write or scd30_extra_write or neopixel_sweep"`. The hotspot module is
  deselected here: case (b) needs the module whole, so it runs once, whole, in 10b, with its 4 owned writes.
- **9.** The crc16 mode is the parametrize id `[crc16]`, rendered into `uart_comm_hazards.py` as `CRC_MODE`:
  `-k "test_comm_hazards_are_serialised_refused_or_recovered and crc16"`.
- **10, the soaks: the true hours.**
  - 10a, short: six tests of 60 s, plus the SGP40 cadence's fixed 600 s: about 30 min with set-up.
  - 10b, hotspot case (b): `--soak-duration long` only opens (b)'s gate, two 8-minute windows. About 1 h.
  - The long soak: `--duration long` runs each of its six tests for 6 h, 36 h in one invocation. So 10c-10h run one
    test each, 6 h 20 with set-up. S4's named test is 10g. 10m runs all six at `mid` (600 s each, about 1 h 15)
    first, so each long day is the owner's choice (lead, 2026-11-05).
- **11.** `../hw_handover/mp/long_fram.py` already runs at 8 MHz and feeds the watchdog every 64 rounds (`d6bd2d45`).
  So the sheet's blocker is gone: neither the logs copy nor the script needed the feed, and the copy only sets `DUR_S`.
- **12a, 12b, 12f** set `CONFIRM` by sed, and only once step 1's FRAM dump finished (`DONE` in `logs/1.log`).
  **12d** answers "wipe" under the same condition, after a `/status` read, and clears every FRAM log 15 times.
- **16b** reads the soft-reset half (`C02`). The power-on half cannot come from a rerun after a power cycle: the probe
  soft-resets first, and the product's boot sets the OSR before `mpremote` can attach. It needs a read before any
  reset on an image that does not boot the product, which this runner does not have.
- **15** comes last. The rollover image costs FC 1. The final image is then flashed back (FC 1) unless `/system`
  already shows its BuildDate.

## Manual items (the owner, not in the runner)

- **Item 14**, on wear day 2 after `run 15`:
  - `scripts/run_manual_hardware_tests.sh --dut-ip <addr> --only <name>` with
    `isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry` (M1, about 30 min);
  - `real_fram_persistence_across_power_cycle`: the power cut that reads SCD30 `AmbPres`; FRAM writes only;
  - `run_pin_reset_keeps_or_clears_the_record`: B2's RUN pin.
  - REPORT 7 item 12's heap in hotspot mode has no registered manual test: the owner's own reading, if wanted.
- **The bridge under its own recovery timer** (BACKLOG). Delete the old bridge as `tests_hardware/README.md` "Host
  network" says, with a second B.13 recovery timer armed by hand. Then run
  `uv run toolchain/setup_toolchain.py env --tier bench`. Never while the runner runs.
- **13's access point on channel 13, 12f's scope (optional), and 16b's power cycle**, as above.

## What comes back

`HANDBACK.md` in this folder, on `claude/u35-bench-campaign`, pushed after every step. It holds:
- the verdict table: per step its verdict, `ResetReason` after it, start time, duration, the host's 1-minute load at
  its end (the owner may use the Pi meanwhile; both step lines carry `/proc/loadavg`) and wear;
- the wear started against the round's budget;
- October's aggregate (the FRAM slices summed);
- every step's log, LAN addresses and credentials filtered; step 1's FRAM dump comes last.

These stay on the Pi: `logs/`, `logs/status_before.json` (the verbatim `/status`, with networking) and the
harness's own `build/archive/` evidence.

## The precheck of 2026-11-05: answers (lead, 2026-11-05)

`PRECHECK_20261105.md`'s findings, in its numbering. 1-3 are fixed in `round1.sh`, 4 in the tree:
1. **uv.** `run` puts `.uvpin/bin` first on PATH when it exists, and refuses any uv other than `pyproject.toml`'s
   `required-version`, naming the fix. Launch from the checkout that holds `claude/u35-bench-campaign` (`sensors-bench`):
   `run` pulls it there, and a `git checkout -B` elsewhere fails while that worktree holds the branch.
2. **A failed wear step ends the range.** Its fix may touch code a later wear step exercises. A failed non-wear step
   does not end the range: the later steps' data is still wanted.
3. **The pass record** reads its log to the end (`grep` without `-q`), so a `Result: FAIL` line always blocks it.
4. **The ring.** `devices/dev.toml`'s uart1 (the responder) ring is 8192 B in snapshot 37, which this branch carries.
   **Tree ready: no.** Build no image (3g's control image, step 3, the lwIP control image) until this line reads
   "Tree ready: yes", once snapshot 37's CI is green. Steps 1, 2 and 4a may run before that.
5. **`stall.flash_program`.** October's figure stays out of SPECIFICATION.md (the owner, 2026-11-05: "Nothing from
   the old campaign remains. It's all new now"). Step 7f records the final firmware's figure. It does not bear on
   `cleared:`, which judges code, not a measurement.

The unchecked items:
- **Round 1's scripts** (12a-12f, 13) entered the tree in snapshot 35 (`d6bd2d45`), the snapshot of `src/`'s last
  change, and were written against it. `long_fram.py` uses `machine.SPI` alone.
- **The board's image** is whatever is on it. Step 1 tolerates a board that does not answer `/status`.
- **The flash bound.** SPECIFICATION's 2,129 ms is the worst case for the largest config file (5 erases). Two erases
  for a 700 B file fit inside it.
- **Part N's owed rows** are mapped after round 1, from its results (R5), not before.
- **October's files** stay as evidence. They go with `audit/` at the audit's end.
