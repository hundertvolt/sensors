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
  - `LWIP_CONTROL_IMAGE`: step 8's control image (below). `CH13=1`: step 13. `FRAM_HOURS`: step 11, whole hours,
    default 2. `MPREMOTE_DEVICE`: optional, as in `tests_hardware/README.md`.
- **The control image, before day 2** (BACKLOG's send-stall protocol, owner 2026-09-30). The bench session builds it;
  the owner need not be there. In a throwaway worktree, never committed, delete the `apply_modlwip_eagain_override()`
  call (`toolchain/setup_toolchain.py:671`), then run `uv run scripts/build_firmware.py dev --output <abs>/control.uf2`.
  Its record must read `"overrides": []`. Pass `LWIP_CONTROL_IMAGE=<abs>/control.uf2`. Without it, step 8 deselects
  `test_send_stall_on_the_unpatched_image` and spends 3 flash cycles instead of 5.
- **Opt-in wear.** Steps 7, 8 and 15 spend the round's opt-in wear (FS 122, NVM 13, FC 7). Run them only once the
  owner's choice is recorded on this line. Owner's choice: not yet given (lead, 2026-11-05).
- **Never:** `nmcli`, `iw` or `iptables` by hand; `mpremote cp`, `rm` or `mkdir`; a `ResetErrors` PUT outside 12d;
  printing a config file; another device's image.

## Commands (from the repository root)

```bash
H=audit/artefacts/evidence/U35_close/redo/hw_round1
bash $H/round1.sh list                      # steps: time, wear, how a STOP ends each, what each needs
DUT_IP=<addr> nohup bash $H/round1.sh run 1 5 > /dev/null 2>&1 &    # one day's range; TO defaults to FROM
bash $H/round1.sh summary                   # the hand-back's verdict table, wear line and aggregate
touch $H/STOP                               # end after the running step
```

`run` first continues the fetched bench branch. After every step it reads `/status` and rebuilds `HANDBACK.md`, then
commits it `[skip ci]` and pushes it. The logs stay in `$H/logs/` (git-ignored, they hold the LAN address).

## Stopping

- **`touch $H/STOP`, Ctrl-C, `kill`:** the run ends after the running step. A signal also pushes the partial log at
  once. `kill -9` pushes nothing, but the logs stay, so the next launch's push carries them.
- **How the running step ends:**
  - pytest steps (4b, 5, 7, 9, 10a-10h, 10m): SIGINT to their pytest within about 10 s, so pytest prints what finished.
  - 4a (host only): SIGINT to the whole step.
  - 11: after its 9-minute slice.
  - 3, 8 and 15 hold a flash cycle and always run to their end (up to about 1.5 h and 3 h). The rest take minutes.
- **A rerun.** A stopped step reruns from its start (`run <id>`). Its log keeps every run; the verdict is the newest.
- **A standard-state stop.** If a session stops on a standard-state deviation after an interrupt, repair it by hand
  as `tests_hardware/README.md` says, then rerun.

## Day plan (each launch at most about 10 h; the times are estimates, none measured on the Pi4)

| day | launch | about | needs |
|---|---|---|---|
| 1 | `run 1 5` | 9 h 10 | `DUT_IP` |
| 2 | `run 7 10m` | 6 h 25 | day 1's verdicts read first (D1: writes after a clean default run); the control image |
| 3-8 | `run 10c`, then 10d, 10e, 10f, 10g, 10h: one a day, each optional (10m ran all six at mid) | 6 h 20 each | - |
| 9 | `CH13=1 run 11 15` | 5 h 40 | the owner: the channel-13 AP (13), the optional scope (12f); afterwards 16b and 14 |

## What each step expects, where it differs from the sheet

- **4b, the flash tier.** Its verdict is FAIL from exactly two nodes, marked "(known)":
  `test_no_frame_is_lost_while_interrupts_are_off[none]` and `[crc16]`. They fail up front: `rx_ring` 512 B is less
  than the 4,608 B of the 400 ms window (`devices/dev.toml:55, :65`). The loop-lag skip no longer reads "unexpected
  skip": `scripts/_hardware_verdict.py`'s `PERMANENT_SKIPS` lists it since `d6bd2d45`.
- **5, the bench tier.** `run_bench_hardware_suite.sh` re-runs L3 under `set -e`, so 4b's two FAILs would stop it
  before `tests_hardware/bench`, after 17 more scratch builds. The step runs the runner's own bench line instead
  (`_require_clean_hardware_run.sh --runner run_bench_hardware_suite`); a pass reads NOT CLEAN, naming 4a and 4b.
- **Rows 6 and 16 are no steps.** They are the `/status` read after every step: `ResetReason` in the verdict table,
  and every logger's `errcount` (SGP40's after 4b and 5 is row 6) in that step's log.
- **7, gated.** Both tiers run `-m "persistence_write or scd30_extra_write or neopixel_sweep"`. The hotspot module is
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

- **Item 14**, after day 9's launch:
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
- the verdict table: per step its verdict, `ResetReason` after it, start time, duration and wear;
- the wear started against the round's budget;
- October's aggregate (the FRAM slices summed);
- every step's log, LAN addresses and credentials filtered; step 1's FRAM dump comes last.

These stay on the Pi: `logs/`, `logs/status_before.json` (the verbatim `/status`, with networking) and the
harness's own `build/archive/` evidence.
