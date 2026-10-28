# Bench campaign on a bare MicroPython image (2026-10-28)

The owner asked for this before the repair starts (owner, 2026-10-28: "prepare a handover for real hardware tests and
measurements which can be done without using any existing firmware ... Prefer timing and script heavy work (but no
hours long stuff, no soaks) so we can use the remaining 1...2% weekly budget for low token, longer duration
measurements"; and: "Using the current firmware in the tests is allowed, for sure.  As long as upcoming changes won't
make another result, this is fine. As I said, for simpler parts, minimal test scripts are an option as well.").
Everything runs from one runner, `run_all.sh`, with short scripts in `mp/`. The board's output goes to `logs/`. The
session reads only the summary (about 60 lines); every detail goes into one pushed hand-back file.

## Current firmware or minimal script

The rule for each item is the owner's: a result is taken on the current firmware only where R1 leaves it unchanged.
- **On the current firmware, before the flash:**
  - the FRAM's raw contents (`fram_raw_dump.py`). This is history R1 cannot change. From the dump, the audit session
    decodes round 1's planned W29 read (whether the FRAM's ID retries ever logged), so round 1 no longer owes it.
- **On minimal scripts and the bare image:**
  - the reset and timing facts. The product boot clears the `mem_backup()` record at every start, so a reset probe
    needs an image that does not boot the product.
  - the platform and chip facts, which no firmware change can alter.
- **Left for round 1 on the final tree:**
  - the queue's product-level rows: the boot stretches, the loop lag, the FRAM block hold, the hazard run, the reset
    codes through `/status`, the cadence and the recovery rungs. Each tests code that an R1 batch changes, so a
    result now would not hold.

## Before anything

- **Gate.** The owner's go-ahead for real hardware, given in the bench session's own conversation (CLAUDE.md). This
  document is not that go-ahead.
- **Wear.**
  - One flash cycle: the bare image replaces the dev firmware. The board then stays on the bare image until round 1
    flashes the repaired build, so there is no flash back.
  - FRAM: writes go only to the scratch block 0x3FF00-0x3FFFF, and the bytes found there are put back. FRAM writes
    are not wear.
  - None: no SCD30 NVM write and no flash-filesystem write. The register writes (BMP384, SGP40, general call) are
    volatile.
- **Network load.** `long_neopixel.py` sends 5 s bursts of 1 KiB UDP packets to the gateway's discard port once a
  minute, a few Mbit/s on the bench LAN while a burst lasts.
- **Never:**
  - `nmcli`, `iw` or `iptables`;
  - `mpremote cp`, `rm` or `mkdir`;
  - a `ResetErrors` PUT;
  - printing a config file. `net_timing.py` reads the stored Wi-Fi config on the board and never prints it. `logs/`
    holds the board's LAN address, so only the filtered `HANDBACK.md` leaves the Pi.
- **Image.** The build phase builds the pinned MicroPython v1.29.0 for RPI_PICO_W with the project's two lwIP
  overrides, through `toolchain/setup_toolchain.py`'s own `build_firmware()`, with no frozen manifest. It holds no
  project code. Networking behaves as in the product image. Nothing autostarts unless the filesystem holds a `main.py`
  or `boot.py`, and the flash phase prints the filesystem root to show it does not. If either is there, stop and ask
  the owner.

## The campaign: one launch per 12-hour stretch (owner, 2026-10-28: "We have several days (aka 12h stretches)")

Tokens are the scarce part and machine time is not. So each day is one launch and one look at the result, and the
hours in between go into long runs that count rare events.

From a checkout of the audit branch's head (this folder is `audit/artefacts/evidence/U35_close/redo/hw_handover/`):

```bash
H=audit/artefacts/evidence/U35_close/redo/hw_handover
# day 1: about 60 min of setup and short runs, then HOURS of long runs
HOURS=10 nohup bash $H/run_all.sh all > /dev/null 2>&1 &
# every later day, in the same checkout or a fresh one: no flash, the long runs only
HOURS=11 nohup bash $H/run_all.sh day > /dev/null 2>&1 &
# at any time: the aggregate and the short results, about 60 lines
bash $H/run_all.sh summary
```

- **The hand-back** (owner, 2026-10-28: "The sessions shall push regularly and dump all details into a single hand back
  file").
  - `HANDBACK.md` in this folder is rebuilt after every step and every third long run. Each rebuild commits it and
    pushes it to `claude/u35-bench-campaign`. The commit is marked `[skip ci]`, so no CI runs.
  - It holds:
    - the aggregate over all days;
    - the short results;
    - one section per day with every run's output;
    - the FRAM dump.
  - LAN addresses are filtered out. No credential is ever printed.
  - Earlier days' sections are kept from the pushed file. A later day in a fresh checkout continues the branch,
    because `run_all.sh` fetches it first.
- **Stopping** (owner, 2026-10-28: "interruptible anytime without losses (max 10 minutes wait time)").
  - Every step lasts at most about 10 minutes: a long run is 9 minutes (`SLICE_S=540`).
  - `touch $H/STOP` ends the run after the current step, then pushes the hand-back: nothing is lost.
  - A Ctrl-C or a kill also pushes what is finished. Only the step running at that moment is lost.
- **Day 1's steps, in order.**
  - `evidence`: the FRAM's raw contents, read with the established `fram_raw_dump.py` on the image already on the
    board (CLAUDE.md's rule: read before anything else touches the board).
  - `build`.
  - `flash`.
  - `resets`: needs `sudo picotool reboot` once, for the bootloader round trip.
  - The five short timing scripts.
  - The eight probes.
  - `quick`.
  - The long runs.
  - Every later day is `quick` and the long runs.
- **The long runs.**
  - The six `long_*` scripts rotate, about 1 h per round.
  - The GC threshold alternates by round (-1, then 32768) for the UART and runtime runs.
  - Each run is a fresh `mpremote run`. A board that does not come back after a run is reset once; if it still does
    not answer, the run stops and the hand-back says that the board needs a power cycle.
- **When something fails.** The hand-back has the full output; the session does not need to open the logs.
- **Optional, at the owner's bench only, before a launch.** A power cut and a RUN-pin reset:

  ```bash
  sed 's/^MODE = .*/MODE = "arm_power"/' $H/mp/reset_probe.py > $H/logs/arm.py
  scripts/mpremote_connect.sh run $H/logs/arm.py
  ```

  Then cut the power, or pull RUN low. Once the board is back, run
  `scripts/mpremote_connect.sh run $H/mp/reset_probe.py`. Use `arm_run_pin` for the RUN pin.

## What each script answers, and for which part of the plan

| script | facts | plan item |
|---|---|---|
| `reset_probe.py` | `reset_cause()`, WATCHDOG REASON and CHIP_RESET bits, and whether both `mem_backup()` regions survive `machine.reset()`, a soft reset, a watchdog reset at 1, 4 and 8.388 s (the measured time to the reset), the BOOTSEL round trip, and optionally power and RUN; whether 8389 ms is refused | B2: the reset reason's decode, the RUN-pin and HAD_POR checks; BACKLOG "`mem_backup()` and `reset_cause()` after a BOOTSEL round trip" |
| `runtime_timing.py` | `gc.collect()` pause by heap fill; event-loop lag, histogram and worst, beside allocation churn at both GC stages; soft Timer drops and jitter at 1 s and 100 ms; recursion depth plain and in a task; the cost of a C-stack test per call | B1's logger-side check (its board half stays round 1's); Part F.3/I.4 budgets; the SGP40 cadence's timer basis |
| `uart_timing.py` | `read()`'s wait for missing bytes per `timeout_char`; a 53-byte frame read whole against reads clamped to `any()`; `any()`'s latency; both directions streaming beside churn, every byte checked, worst backlog of 512 | B6: the read path, the ring, the never-block rule (F.5.8's 4.4 ms) |
| `i2c_timing.py` | the addresses each bus answers on (a bench-facts row); BMP384 forced conversion per OSR; the SGP40's time from measure to ready, and its answer after one unknown command; the SCD30's reads at timeouts from 200 ms down to 1 ms; the general call's ACK or NAK per bus, and who answers after it | B4 and B8 (the I2C timeout range, the conversion wait); BACKLOG's general-call, SGP40-command and lone-BMP rows |
| `fram_spi_timing.py` | RDID over 1,000 reads (a bench-facts row); each command's worst duration at 1 MHz; 256-byte reads at 1, 4, 10 and 20 MHz, counting OSError (F.5.2's EIO) and wrong bytes | B3: the ID retries with W29, E52; T4's per-command figure |
| `net_timing.py` | connect time three times; `getaddrinfo()` wall time and whether a 10 ms soft Timer advanced during it (resolvable, NXDOMAIN, an unreachable DNS server); an immediate TCP rebind on 8080 after a served connection, and a UDP rebind on 53, each with and without SO_REUSEADDR; ten NTP round trips | B5: start retries and W62 against SO_REUSEADDR, the resolver, the NTP cadence; F.2's getaddrinfo fact |
| `long_i2c.py` | per chip and phase (register pointer, data read, register write): transactions, EIO, ETIMEDOUT, wrong values, bad CRCs, the worst duration, over millions of transactions; the SGP40 at 1 Hz with its first measure after an idle minute apart | REPORT 7 items 3 and 4 (chip half); B4's I2C retry and short-ACK path, OR113's ladder; B8's timeout values |
| `long_fram.py` | RDID mismatches, 256-byte read errors and wrong bytes, 1-byte write read-back failures, with worst durations, at dev's 1 MHz | B3: whether the ID retries (W29) and E52 ever have work to do |
| `long_uart.py` | both directions streaming for hours at each GC stage: bytes, mismatches, worst backlog of 512, worst reader gap | B6: the ring and the read path under real GC pauses |
| `long_runtime.py` | loop-lag histogram and worst, soft Timer drops and jitter, MemoryErrors under churn, at each GC stage | F.1's soft-callback drop; Part F.3 and N timing rows for R2's accuracy check |
| `long_net.py` | link drops per second of watching, getaddrinfo failures, worst time and how often it held the VM, NTP failures and RTT, a forced reconnect every 15 min | B5: the resolver, the NTP cadence, start retries; Wi-Fi knowledge (decided, not reopened) |
| `long_neopixel.py` | the pixel watched through the ISL29125 rig while 5 s UDP bursts go out each minute: deviations in and outside bursts, windows ending deviated, windows where the rig cannot see the pixel | REPORT 7 item 9, the NeoPixel rewrite's premise (B7's revert stands either way; knowledge) |
| `quick_platform.py` | config-like floats through json; the MemoryError text for a big allocation, an exhausted heap, and an allocation in a soft and in a hard IRQ, without and with the emergency buffer | REPORT 7 items 5 and 7; clarification (d) and the memory gates' matched text |
| the probes | the five chip conformance probes (KEY=VALUE, diffed later against the twin's fake), the free alarm count, the soft-callback drop | BACKLOG's BMP3XX calibration block, ISL29125 CONFIG1, SCD30/SGP40 fidelity rows, the free alarm count |

## Expected, where the specification states it

These are what to check first. Everything else is recorded, not judged.
- **`machine.reset()` and the watchdog resets.** `cause=3`, and both regions kept (F.5.4). A watchdog reset's
  `elapsed_ms` is close to its timeout.
- **Power and RUN.** `cause=1`, and both regions cleared (F.5.4).
- **The 8389 ms watchdog.** Refused with "timeout exceeds 8388" (`machine_wdt.c`).
- **A whole 53-byte frame read.** About 4.5 ms (F.5.8 measured 4.4 ms). A read clamped to `any()`
  stays far under 1 ms.
- **The SGP40.** Ready within its 30 ms datasheet maximum.

## What comes back

The bench branch's `HANDBACK.md`, pushed by the runner itself. The audit session reads it from there:
- it diffs the probes against the twin;
- it decodes the FRAM dump (round 1's W29 read);
- it files every figure under its plan item.

The local `logs/` stay on the Pi.

## Not in this session

- **The product firmware's own tests and soaks.** They test code an R1 batch changes, so they are round 1's, on the
  final tree.
- **The owner's two-chroot run.** It is host-only and can fill a day when the board runs nothing, never alongside the
  long runs, since CPU load skews their timing. Its toolchain and installer legs stay valid through R1 and R2; its
  suite leg is re-run after R2 anyway.
- **`env --tier bench`.** It is host-only and reuses an existing bridge ("an existing br0-wifi-ap is reported, never
  recreated"). It is listed in BACKLOG and can run in the same sitting if the owner wants it. It is not part of
  `run_all.sh`, because it is SPECIFICATION.md B.13's territory if it ever touches the bridge.
