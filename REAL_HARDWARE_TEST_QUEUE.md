# Real-hardware test queue

The single list of everything waiting on the dev bench, so one go-ahead session can run it all in
one go instead of rediscovering it from five documents. Temporary, like every other queue doc here:
each row is deleted once its result is migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`,
and the file goes when the last row does.

**Nothing here authorizes anything.** CLAUDE.md's standing gate still applies: a session needs the
project owner's go-ahead, given in that session's own conversation, before any `mpremote`, `nmcli`,
`picotool` or `tests_hardware/` run. `tests_hardware/README.md` remains the technical reference for
prerequisites, flags and safety facts; this file only says *what* is owed and *why*.

A `§7…` reference below is to `HEAP_FRAGMENTATION_MEASUREMENTS.md`'s archived measurement record
("archive §7…", the file at commit `12640c2`); a `§M…` one is to its current how-to-measure text.

Status values: **OPEN** (owed), **BLOCKED** (waiting on a decision or another row), **DONE**
(result migrated — row deleted at that point), **EXCLUDED** (belongs to another effort).

## The finalisation checklist — everything still owed, in one place

Grouped by what each row *needs*, not by which effort opened it. **29 rows owed.** D1 and D2 are the
owner's standing answers and no sitting re-asks them. G10 is excluded (section 5).
This table is an index; the row's own entry below is what to read before running it.

| Group | Rows | What it needs |
| --- | --- | --- |
| **Per-sitting confirmation** | D3 | Which image. Always a `dev` build of the tree under test; never a `wozi` build |
| **The suite runs** | S3b | `--allow-neopixel-sweep`, with M1 first |
| **Heap placement readings** | T1 | The in-suite AFTER `largest_block` |
| **Measure A's leftovers** | T2, T4 | T4 is a script to write first |
| **Memory gates and the (e) stage** | G8 | A script to write first |
| **New features** | N2, N3 | One look each; N3 rides on R13 |
| **Targeted investigations** | R1, R2, R4-R7, R9, R13 | Bench time. R4 needs its own run with `--allow-persistence-writes`; R1's first answer is read off Step 6's |
| **Tests still to write** | G1, G3, G4, G6, G12 | Code first, bench second. G6 is adapt-now-measure-later by decision |
| **The bench host itself** | H1 | Owner-run; needs no board |
| **Long soak and the light rig** | S4, M1 | Deliberately separate sittings. M1 is interactive and records the rig geometry S3b depends on |
| **Findings still open** | F1, F17, F18 | F1: the script that stranded the bench once; read its row in full before running it. F17 rides along with W4. F18 is the owner's call first |
| **The connection limit of 6** (§4A) | W3, W5 | The next regular bench run; the limit itself is settled. W5 needs `--allow-persistence-writes` |

**What "finished on real hardware" means**: every row above DONE or explicitly EXCLUDED, each
result migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`, and this file deleted. That takes
one bench sitting, the writing work and the owner's own H1 run.

## If there is time for one sitting only

**Board state**: `dev` image of tree `851e816`, `buildDate 2026-09-25T12:54:13Z`, `max_connections
= 6`, `DebugLevel` 5 — current with `src/`. A sitting is in progress: `HARDWARE_TEST_HANDOVER.md`
section 5 has its results so far. Check `buildDate` against the tree every time.

1. **Run sheet Step 1** — the `errcount` reading, before anything writes.
2. **§4A's W4** — the whole bench tier on the tree under test at the limit of 6, default flags; then W3.
3. **M1, then S3b** — the light rig is in place (D2), and M1 is what writes the geometry down so
   the next sitting does not have to re-establish it. ~10 minutes together.
4. **F1's SSID script** — read §2A F1 in full first: this is the script that stranded the bench,
   and the fix is structural but still unverified on silicon.
5. **T4's per-command timing**, then T1's in-suite AFTER `largest_block`.

Everything else in this file can wait for another sitting.

---

## 0. Decide before the run

These change what gets run, so settle them first.

- **D1 and D2 are the owner's standing answers (2026-09-22)**; a sitting does not re-ask them.
- **D1 is sequenced**: the gated rows run only once the default run is green, so a gated failure is
  the gated test's own.
- **D3** is confirmed every sitting; the answer is always a `dev` build of the tree under test.

| # | Decision | Why it matters | Status |
| --- | --- | --- | --- |
| D1 | **Does the bench spend flash/NVM writes this round?** A default run deselects 13 of the bench tier's 85 tests and 9 of the flash tier's 51; `--allow-persistence-writes` runs them and spends real cycles. `--allow-scd30-extra-write` is AND-gated on top for one further SCD30 NVM write. | Several rows below are *only* reachable with the flag — R1 and R4 in particular. Deselection is invisible to the pass/fail check, so this must be a knowing choice (CLAUDE.md's wear rule). | **ANSWERED 2026-09-22: yes, after a clean default run.** Not a per-sitting question any more; the ordering is the condition |
| D2 | **Is the NeoPixel-aimed-at-the-ISL29125 rig set up?** | Gates `--allow-neopixel-sweep` (S3b, ~10 min). | **ANSWERED 2026-09-22: yes.** Pass `--allow-neopixel-sweep`; run M1 first, which records the rig geometry |
| D3 | **Which firmware image.** Every row below assumes a `dev` build of the tree under test via `scripts/build_firmware.py dev`. | CLAUDE.md's hard rule: a `wozi` build flashed onto the dev bench "tests nothing at all" and has produced false bugs before. | OPEN |

---

## 1. Run sheet - the order to work in

Every step below is a real command against real hardware, so **do not start any of them without
the go-ahead rule at the top of this file being satisfied**. Work top to bottom: each step assumes
the ones above it. `tests_hardware/README.md` stays the reference for *how* a step works
(prerequisites, environment variables, what each marker gates); this sheet is only the order, the
command, and what to write down.

**Step 1 - record the board's current state, before touching anything.**
`GET /status` and save the whole `errcount` table verbatim into the sitting's notes. It is the one
diagnostic a reboot does not erase and `ResetErrors` destroys irreversibly (CLAUDE.md). Then ask
what was last run against this board: an isolated-driver device script builds its own
`AsyFramManager` over the same chip and can leave a plausible-looking fabricated entry behind
(`tests_hardware/README.md` has the mechanism). An unexplained entry is evidence only if the
board's recent history allows it to be.

**Step 2 - answer D1, D2 and D3 (section 0) and write the answers down.** They decide which of the
steps below run at all. Nothing later re-asks.

**Step 3 - build and flash the `dev` image of the tree under test.**
`scripts/build_firmware.py dev`, then flash it. Never a `wozi` build (CLAUDE.md: it "tests nothing
at all" and has produced false bugs).

**Step 4 - the flash tier.** `scripts/run_flash_hardware_suite.sh`
Read the verdict's **deselected** count, not just the word "clean": the wear gates deselect rather
than skip, so "everything that ran, passed" is not "everything ran". Both device-script fixes and
the watchdog-starvation banner passed here on 2026-09-19, so a new failure in either is this
image's, not a known-broken test.

**Step 5 - the bench tier.** `scripts/run_bench_hardware_suite.sh`
A strict superset of step 4; same deselected-count caveat. R9 and R13's observations ride along
here.

**Step 6 - the wear-gated run, only once steps 4 and 5 are green** (D1's condition).
`scripts/run_bench_hardware_suite.sh --allow-persistence-writes -s` — a strict superset of the flash
one. R1 and R4 need it; without it they are deselected. `-s` makes the two config-write arms'
`CEILING_RETRIES` lines visible, which is R1's first answer. The last gated run (2026-09-23, clean,
archive §7R.2) was image A, not the current tree. Add `--allow-scd30-extra-write` only if a second SCD30 NVM write is
genuinely wanted on top.

**Step 7 - the NeoPixel light programs.** D2 is a standing yes: the rig is in place.
`scripts/run_manual_hardware_tests.sh --only isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry`
first (it is what records the rig geometry), then
`scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep`. ~10 minutes combined.

**Step 8 - the targeted investigations** in section 2, in this order: R1 (start with its no-code
`RangeAuto=false` bisection, and restore `RangeAuto` afterwards), R2's reader-count curve at 0, 1,
2, 3, 4 and 6 readers, then R6/R7 and R13.

**Step 9 - the long soak, deliberately and separately.** `scripts/run_bench_soak_tests.sh --tier
{short,mid,long}`, chosen on purpose (60 s / 600 s / 6 h). Never bundled into steps 4-6; the suite
runners exclude it unconditionally.

**Step 10 - the bench host itself** (section 4): H1's two chroot legs. They do not touch the board,
so they can run while it is busy.

**Step 11 - close out.** For each row answered: migrate the result into `SPECIFICATION.md`,
`CLAUDE.md` or `BACKLOG.md` as the row says, then delete the row. **When the last row goes, delete
this file** - it is a queue, not a record.

| # | Suite run | Notes | Status |
| --- | --- | --- | --- |
| S3b | `scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep` | Only if D2 says the rig is in place. Runs the two long ISL29125 light programs (~10 min combined); they skip otherwise. | OPEN — D2 answered yes, 2026-09-22: the rig is in place |
| M1 | `scripts/run_manual_hardware_tests.sh --only isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry` | Interactive. Repeatability on an unchanged scene, continuity across the range switch, **and** setting up and writing down the rig geometry S3b depends on. Worth doing before S3b, not after. | OPEN |
| S4 | Long memory soak (`long_soak` tier), never bundled into the suite runs (Steps 4-6) | A real long-duration memory-soak run has still never been executed (README.md's own "Further reading" note, carried from the retired hardware-planning docs). Pick the tier deliberately: short=60 s / mid=600 s / long=6 h. | OPEN |

---

## 1A. A6's FRAM timing script — the input to T4

Measure A's results are `HEAP_FRAGMENTATION_MEASUREMENTS.md` archive §7D.

**A6's timing script is not committed and this is the only copy.** T4 is the row that decides
whether it becomes a device script. Run it with
`scripts/mpremote_connect.sh exec "import machine; machine.WDT(timeout=8000)"` then
`scripts/mpremote_connect.sh run /tmp/fram_hold_time.py`, mirroring what `Board.run_isolated()`
does. Unlike every other FRAM device script it writes at the **top** of the address space and never
calls `get_chunk()`, so it does not overwrite production's error logs.

```python
"""Times the real SPI wire cost of one command envelope and one whole block operation."""

import asyncio
import time

import asy_spi_driver
from asy_fram_manager import AsyFramManager


async def _main() -> None:
    spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
    fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=None)
    if not await fram.setup():
        print("RESULT: FAIL fram.setup() failed - real chip not responding on spi0/cs5")
        return
    chip = fram.fram
    addr = 0x3FF00  # top of the address space, clear of every production chunk
    one = bytearray(1)
    eight = bytearray(8)

    # (a) the synchronous, non-yielding stretches, bus already held.
    async with chip:
        t0 = time.ticks_us()
        w_status = chip.set_values_sync(one, addr)
        t1 = time.ticks_us()
        r_status = chip.get_values_sync(eight, addr)
        t2 = time.ticks_us()
    write_us = time.ticks_diff(t1, t0)
    read_us = time.ticks_diff(t2, t1)
    if not await chip.report_set_values(w_status):
        print("RESULT: FAIL the 1-byte write reported a failure status")
        return
    if not await chip.report_get_values(r_status):
        print("RESULT: FAIL the 8-byte read reported a failure status")
        return

    # (b) the bus-lock hold: entry to exit, yields inside it included.
    t3 = time.ticks_us()
    async with chip:
        for _ in range(4):  # a block operation's own command count
            chip.set_values_sync(one, addr)
            await asyncio.sleep(0)
            chip.get_values_sync(eight, addr)
            await asyncio.sleep(0)
    hold_us = time.ticks_diff(time.ticks_us(), t3)

    print(f"HOLD write_5cs={write_us}us read_1cs={read_us}us block_operation={hold_us}us")
    print(f"RESULT: PASS longest non-yielding stretch {max(write_us, read_us)}us, bus held {hold_us}us")


asyncio.run(_main())
```

---

## 1C. Added features no measurement row covered, and the records they need

| # | Item | Notes | Status |
| --- | --- | --- | --- |
| N2 | **`asy_wifi_service._with_default()`** substitutes a build-time per-device default into the one-field hostname/SSID schema, dropping a value outside the field's own bounds rather than installing it — an unsatisfiable default makes `ConfigManager` answer `None` to every read, which would cost a device its networking config entirely. | **Looked at 2026-09-22, and the failure mode is absent**: after a clean boot `GET /networking` returns a full, sane config with `Hostname` = `SensorStationDev`, matching `devices/dev.toml` exactly. **Partial, not closed** — this board carries a persisted `config_WIFI.cfg` whose own `Hostname` is already `SensorStationDev` (written 2026-09-19, archive §7J.6), and a persisted value pre-empts the default, so the substitution path itself is still unproven on silicon. Closing it needs a boot with that key absent from the persisted config | PARTIAL |
| N3 | **`asy_uart_comm.py` reclassified which warning takes the episode's single persisted slot** — `_WRN_DRAIN_BOUND` (11) now wins over `_WRN_RESYNC` (10) when the drain bound was hit, because 11 separates a babbling peer from ordinary line noise. The boot drain persists nothing. | **Receiver-side only, no emitted bytes change**, so it is the preferred class of protocol change and a mixed-version pair still works — but it still needs a `UART_C_PORT_CHANGELOG.md` entry, which should be confirmed. `dev`'s two `uart_link` instances make it observable: check `errcount`'s `UART_init`/`UART_resp` history after a run that forces a resync. | OPEN — **checked 2026-09-22 and there is nothing to read yet**: after a full clean bench tier, `errcount` carries no `UART_init`/`UART_resp` entry at all (`UARTLINK` 363 transfers, 0 failures), because nothing in the default suite forces a resync. This row needs R13's babbling-peer setup to produce the entry it wants to inspect; the two are one piece of work, not two |

---

## 1F. Measure A/B's remaining silicon rows

| # | Run (plan row) | Notes | Status |
| --- | --- | --- | --- |
| T1 | **The exact in-suite AFTER `largest_block`** (T.1) | A alone measured 20,592 → 28,864 B in-suite, +40.2% (archive §7D.3), and A + B **passes in-suite** against a BEFORE arm that fails — the first image ever to. What is still owed is only the precise AFTER figure: the test discarded it on a passing run, fixed host-side (archive §7F.6), so the next in-suite run yields it. Record it as §2.1's third and fourth [HW] columns. **Only like suite positions are comparable** (archive §7D.2) — a standalone reading does not answer this. **Changed 2026-09-24**: the script now sets `gc.threshold(-1)` itself, where it used to run at whatever threshold the attach left in force — 32768, or `-1` when the attach interrupted `main.py` before its threshold line (§M3.8, answered from source). So this AFTER figure is comparable with the pre-2026-09-24 corpus only as far as those runs inherited `-1`, which is unrecoverable per run; read `GC_THRESHOLD=` in the output. **Optional, zero-wear confirmation of §M3.8's race**: `board.hard_reset()`, then `mpremote exec "import gc; print(gc.threshold())"` as soon as the port reappears, and the same read again after ≥ 30 s of normal running. The second must print 32768; the first printing `-1` confirms the race (32768 there only means that attach lost it). Each attach stops `main.py`, so the watchdog resets the board ~8 s later — BACKLOG item 12, expected | **MEASURED 2026-09-25**, owner to close: in-suite `after_build_system` `largest_block` **84,112 B** (baseline 122,016 B, free 97,280 B, `retained` 0; the control and production-threshold arms identical). The race check is done too: `-1` at 0.8 s after reset, `32768` at 38 s. The archive figures this row compares against are no longer in the tree and look like a different position — `HARDWARE_TEST_HANDOVER.md` 5.2 |
| T2 | **Bus-hazard tier 4 on the A + B arm** (T.2) | Tier 3 is done: archive §7F's AFTER arm ran the full flash suite with zero failures, covering all three FRAM tests, and archive §7F.7 calls out the two rewritten injectors passing on *both* arms — the first real-chip proof the hijacked payload is refused. `tests_hardware/bench/test_bus_concurrency_under_api_load.py`'s six were last run on the **A-only** arm (archive §7D.5). Three of the six are `persistence_write`-marked, so they need `--allow-persistence-writes` | PARTIAL |
| T4 | **Per-command hold time, measured** (T.4) | A device script timing one byte-level write (5 CS) and one `check_length` read slice with `time.ticks_us()` around the synchronous stretch, reported in its own `RESULT:` line; the number goes into `SPECIFICATION.md` F.5.8 beside the UART 4.4 ms frame. A6's aggregate is already there (2,849 us non-yielding, 21,269 us bus hold) — this is the per-command figure F.5.8 says is still owed. **If it is above ~1 ms the per-command yield policy is already the finest the chip allows**, and the finding is recorded, not "fixed". A6's own script is saved but not committed; T4 decides whether it becomes a committed device script | **MEASURED 2026-09-25**, three runs of section 1A's script on image `05:21:43Z`: 1-byte write (`write_5cs`) **2,833 / 3,334 / 3,395 us** non-yielding, i.e. ~0.6–0.7 ms per CS command; one-CS 8-byte read **783 / 881 / 881 us**; whole block operation's bus hold **18,089 / 20,930 / 23,148 us**. Figures are in SPECIFICATION.md F.5.8. **Owner decisions left**: a single command is *below* the row's ~1 ms mark, so yielding between the CS commands of one write would be finer than today's ~3 ms stretch — worth it or not; and whether the script becomes a committed device script |

No flash cycle and no reflash; T2's three `persistence_write` tests spend a config write each.

---

## 2. Targeted investigations

R1, R2 and R5 are confirmed as owed by the owner (2026-09-18); they wait on bench time, not on a
decision.

| # | Investigation | Source | Status |
| --- | --- | --- | --- |
| R1 | **BACKLOG item 30 — the ISL29125 HTTP connection reset under concurrent API load.** Owner's direction is to root-cause and resolve, not re-measure. Shape is established: needs **both** a config-persisting PUT **and** ≥2 concurrent readers (PUT alone 0/10, PUT+1 reader 0/6, PUT+2 readers **6/18**, plain GET+2 readers 0/6); failures land at 21–72 ms against 0.5–2.2 s for successes, and `WEBSERVER`'s counter stays 0 so FRAM forensics will not help. **First read the two config-write arms' `CEILING_RETRIES` lines** from Step 6's gated run (`-s`): the connection ceiling is a second candidate with the same signature (BACKLOG 30), and the test's retry now hides it. ISL29125 retries well above BMP3XX's with no other failure → the ceiling, close BACKLOG 30 with no bisection. Otherwise **do the no-code bisection**: `PUT /sensors {"ISL29125": {"RangeAuto": false}}` drops `_switch_range()` from the three-step push, leaving only `configure()` + `_reapply_persist()`. Rate falls → the threshold re-arm is implicated; unchanged → it is the first two. Restore `RangeAuto` afterwards. | BACKLOG 30 | OPEN — S3 ran (archive §7R.2) without answering it, behind the retry. Its first answer rides Step 6's gated run (the `CEILING_RETRIES` lines); a bisection run only if those point at the driver |
| R2 | **BACKLOG item 32 — the `ResetErrors` reader-count curve.** Elapsed time at **0, 1, 2, 3, 4, 6** concurrent `GET /status` readers. Two points exist (6.32 s idle, 11.58 s at 3 readers = 77 % of the 15 s server cap); two points cannot say whether the curve flattens. | BACKLOG 32 | **MEASURED 2026-09-25** (image `05:21:43Z`, 21 FRAM chunks, three sweeps per point, readers re-requesting with zero think time): 0 → 2.31 / 2.43 / 2.43 s; 1 → 5.53 / 5.61 / 5.76 s; 2 → 8.80 / 10.57 / 11.03 s; 3 → 13.16 / 13.24 / 14.69 s; 4 → no result (refused 20× at the ceiling, then no answer within 30 s — F18); 6 not run, since 4 already exceeds the cap. **The curve does not flatten**: ~+3.5 s per reader, so 3 readers reach 88–98 % of the 15 s cap. Every completed sweep but one read all 21 counters back at 0; the exception (2 readers, run 2) showed `UART_init`/`UART_resp` entries afterwards, most likely logged under load after the sweep (F18's mechanism) rather than skipped by it — the next sweep cleared them, and R4 is what settles it. Results are in BACKLOG 24 and 32; the budget and the design fix are the owner's decision |
| R4 | **`ResetErrors` completeness under contention.** Pre-populate the FRAM error logs on several modules, then sweep under R2's reader load and confirm every counter reads back 0. All previous correctness checks were made at idle or with the logs already empty; a silently skipped chunk is invisible today because the call still answers `200`. | CLAUDE.md's FRAM `errcount` rule | OPEN — S3 ran (archive §7R.2) without answering it; needs its own run with `--allow-persistence-writes` |
| R5 | **BACKLOG "Refactor targets" — the WP5 deferred-config-write re-confirmation.** The BMP3XX arm passed on 2026-09-17 on WP5 firmware; make that durable rather than one run. The ISL29125 arm is R1, not this row. | BACKLOG, first entry | OPEN — **second green run 2026-09-23** in S3 (both BMP3XX config-write arms passed). Owner, 2026-09-24: run it once more in the next bench sitting for extra evidence; a third pass closes it |
| R6 | **The `CFGMGR_SYSTEM` setup-order fix's unexplained +0.90 s of boot latency.** Boot latency itself is measured and needs no re-run: pre-WP **7.74 s** → WP1+WP2 **9.80 s** → WP1–WP8 **9.76 s** → +`CFGMGR_SYSTEM` fix **10.66 s** (medians of 5, spread ±0.06 s; 23 reboots, no `WDT_RESET`). Those figures were taken by PR #102, which the owner closed unmerged on 2026-09-18 — they are migrated into `SPECIFICATION.md` Part A.7's boot-latency note, so nothing is lost with the PR. What remains open is only the sub-question: **+0.90 s** is far more than one extra FRAM-backed logger's `setup()` should cost, and is unexplained. Worth understanding before the same reorder is assumed free elsewhere; it does not threaten the watchdog budget, so it is not a reason to revert. | SPECIFICATION.md Part A.7| OPEN |
| R9 | **Half closed: the shadow-divergence fix RAN and passed on silicon (archive §7H.6, the first fully clean bench tier); the `Overrange` field that replaced `W12` has still never run.** `configure()`'s device-session lock was widened to span the whole validate-mutate-write(-rollback) sequence (WP-era fix, unit-tested by `test_configure_never_exposes_the_shadow_ahead_of_a_write_still_in_flight`), but the false `wrnno=11` it fixes only ever manifested under real concurrent bench load - so only real load re-confirms it. Same run covers the `Overrange` half: `device_scripts/isl29125_mechanism_envelope.py` now reads the live field instead of the retired `W12` log entry. | BACKLOG, "Open questions" first entry | OPEN |
| R7 | **`SPECIFICATION.md` Part A.7's FRAM setup-cost figures are twin-only.** `digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time, so every number there excludes the real per-transaction cost. Re-measure on silicon. Largely the same instrumentation as R6. **Premise corrected by A6 (2026-09-18):** the omitted term is *not* mainly SPI wire time — at 1 MHz six transactions are ~300 us of the measured 2,849 us, so ~90 % is MicroPython interpreter / `machine.SPI` call overhead. Frame the re-measurement that way. | SPECIFICATION.md Part A.7 | OPEN |
| R13 | **UART `wrnno` 11 now takes the fault episode's one persisted slot when the drain hits its bound** (SPECIFICATION.md C.7.1, 2026-09-18). The bench exerciser drives the real crossover jumper, so a deliberately babbling peer is reproducible there in a way no mock is: confirm `GET /status` shows `W11` rather than `W10` for `UART_init`/`UART_resp` after one, and that a *boot* drain against the same babbling peer persists nothing at all. Low urgency - the mock tier covers the logic; this confirms it against a real UART's own timing. | SPECIFICATION.md C.7.1 | OPEN |

---

## 2A. Findings still open from the two bench sittings

F2-F16 are closed (`HEAP_FRAGMENTATION_MEASUREMENTS.md` archive §7I-§7K; lasting lessons in section 6 and
`tests_hardware/README.md`). F1 needs one careful invocation, not a suite run; F17 rides along with W4.

| # | Finding | Status |
| --- | --- | --- |
| F1 | **`tests_hardware/device_scripts/wifi_service_reconnect_repro.py` once stranded the bench** by persisting a garbage SSID it never restored. The script now reads the live SSID first, diverts every persist to a scratch `config_HWTEST_WIFI.cfg`, restores the cache in a `finally` and removes the scratch file after `flush_pending()` (its own comments carry the mechanism). Run it once on silicon to verify. | **FIXED 2026-09-18, unverified on silicon.** Residual, the owner's to weigh: the scratch write still spends one flash cycle, gated only by CLAUDE.md's go-ahead rule |
| F17 | **Board anomalies of the connection-limit sittings** (BACKLOG item 44, `HEAP_FRAGMENTATION_MEASUREMENTS.md` archive §7R.5): a silent reset and hotspot fallbacks. The third, the watchdog reset at `mpremote` attach, is closed off silicon (item 12's own measurement). During W4, read `machine.reset_cause()` after any unexpected reset and note every hotspot fallback; no sitting of its own | OPEN — **two observations, 2026-09-24/25.** (1) During W4 the USB serial disconnected mid-upload of `uart_idle_poll_rate.py`; later resets overwrote `reset_cause()`, so it is recorded, not explained; an isolated re-run passed. (2) **One hotspot fallback, explained**: after T4's three device-script runs (each a watchdog reset ~8 s after the script, with no `kick_all_stations()` before it) the board came up in hotspot mode. `reset_cause()` = `WDT_RESET`, `errcount` WIFI `W6` ×5 (`STAT_CONNECT_FAIL`, one slot, counter 5) = five failed connects, then `conn_fail_to_hotspot = 5`. This is the stale-AP-station mechanism `tests_hardware/README.md` records; a kick recovered it at once. SGP40 `W13` ×4 + `W11` (backup written/loaded without a timestamp) followed, since hotspot mode has no NTP. It fits BACKLOG 44's hotspot bullet: the earlier three fallbacks may well be the same mechanism. (3) Two more fallbacks the same way on 2026-09-25, both from this session's own resets without a kick *immediately* before them; the second one also proved the `PERIODIC` hotspot timer, which returned the board to STA after 8 min with no reboot |
| F18 | **Four back-to-back `/status` readers saturate the board** (found by R2, 2026-09-25, image `05:21:43Z`). Four host threads, each re-requesting `/status` the moment the last answer arrives (zero think time): each `/status` took a median of 4.8 s. **A `PUT /status {"ResetErrors": true}` was refused at the connection ceiling 20 times in a row** (the readers retake every freed slot; admission has no fairness), and when admitted it gave no answer within 30 s. `errcount` afterwards: WEBSERVER `W2` ×20 ("Connection reclaimed (timed out)" — the designed per-call reclaim), and **UART_init/UART_resp `E20` (no ACK), `E22` (read timeout), `W10` (resync)** — the UART exerciser misses its deadlines while the loop is saturated with HTTP work. No reboot (uptime continued), no task ended, no `MemoryError`. At 3 readers the same load produced none of the UART entries but 1–8 ceiling refusals. Open for the owner: whether zero-think-time readers are inside the product's contract (the web UI polls, it does not hammer), and whether the UART link degrading under that load is acceptable for a bench-only exerciser | OPEN — owner decision |

---

## 3. Coverage gaps that need a bench session to close

Each is a test to *write* or a method to settle against real hardware, not just a run.

| # | Gap | Status |
| --- | --- | --- |
| G1 | **The bench UART exerciser never issues a multi-chunk SET**, so "bench ⊇ flash" does not hold for the SET train the flash tier proves. Wire a periodic SET into `UartLinkExerciser._exercise_loop()`'s live load. | OPEN |
| G3 | **`_reboot()`'s alarm-pool-exhaustion fallback (`_force_watchdog_starve = True`) is mock-only.** | OPEN |
| G4 | **NOTIFY's own FRAM chunk has no hard-reset-recovery bench test**, unlike SGP40's. Needs an observable-write signal analogous to SGP40's `BackupTS` first. | OPEN |
| G6 | **`test_ticks_ms_real_2pow30_rollover` needs a measurement method that does not poll with `board.exec()`.** BACKLOG item 12 established on real hardware that every `exec` starves the watchdog and hard-resets the board ~8 s later, zeroing the counter — so the hour-by-hour poll can never climb toward 2**30, and a later read landing below an earlier one is the reboot, not a wrap. The vacuous-pass hole is closed (a drop now only counts as a wrap when the previous read was already within two hours of 2**30, so the ambiguity fails honestly), but that makes the test *fail* rather than measure. A real method has to leave the board running: feed or disable the watchdog from inside the polled code, or observe passively via `tail_log()`. Design decision, then a genuine ~12.4-day run behind `--allow-multi-day-rollover-wait`. | **DECIDED 2026-09-22: adapt the method, defer the measurement.** Do not drop the test — the chosen answer is a method that leaves the board running (feed or disable the watchdog from inside the polled code, or observe passively via `tail_log()`). The ~12.4-day run itself is deliberately not scheduled: we do not measure it yet, and the test is deselected by default behind `--allow-multi-day-rollover-wait`, so deferring costs nothing today |
| G8 | **CLAUDE.md's (e) stage has never been asserted on silicon.** I.4(e)/(f) says the suite must pass at `gc.threshold(-1)` with zero allocation failures *before* it is run at the shipped `gc.threshold(32768)`, and both halves are machine-checked — but only on the host and twin tiers. `scripts/build_firmware.py` stages the generated boot entry as `main.py`, and it sets `gc.threshold(32768)` before `asyncio.run(main())` — so **every flash- and bench-tier run, which all drive the live firmware over REST, is an (f)-stage run.** The device scripts are the other way round: importing `sensortask_dev` never executes `main.py`, and every heap-measuring one sets its own threshold (HFM §M3.8; `heap_layout_after_full_boot_sequence.py` sets 32768 explicitly when it wants the production arm) — but they only ever measure **boot placement**, never the run phase under load. So the (e) bar itself, zero allocation failures under real load, has no silicon arm. It needs no second image either: boot the full system by importing it, drive host-side API load against it for a bounded window, and assert `harness.MEMORY_ERROR_MARKERS` never appears in the log. Zero wear: no flash cycle, no persistence write, no reflash. | OPEN — script to write |
| G12 | **UART's F.5.8 "never blocks" invariant has no real-hardware run against the shipped driver.** `device_scripts/uart_read_never_blocks_the_loop.py` deliberately uses raw `machine.UART`, so no silicon run calls `asy_uart_driver`'s own `ready()`/`_buffered()` clamp; F.5.9 already has the real-driver analogue (`uart_idle_poll_rate.py`). Write the same shape for F.5.8 over the crossover jumper (tests_hardware/README.md's "Tenth pass") | OPEN — script to write |

## 4. Bench-host tasks (not the board)

| # | Task | Status |
| --- | --- | --- |
| H1 | **The two-chroot verification, unsatisfied since 2026-09-12** — an owner-run periodic check since 2026-09-18, not a gate that blocks anything. Everything changed since 2026-09-12 in `scripts/`, `pyproject.toml` and — the highest-risk part, which the lint/typecheck recipe never exercises — `toolchain/setup_toolchain.py` + the new `toolchain/micropython_overrides.py`. The bench Pi4 already runs trixie/GCC 14.2, so it is the right host for the leg that has never run. **Two things make this run heavier than the last one**: `build_unix_port()` now builds **two** Unix ports (`build-standard` and `build-settrace`, Part E.5.2), so that step costs roughly twice the time and disk it used to; and `scripts/test.sh` was rewritten around them, so the chroot leg's `scripts/test.sh` invocation is exercising a different script than the recipe was last satisfied against. Also worth running once there: `GC_THRESHOLD=32768 scripts/test.sh`, the (f) stage, which no chroot leg has ever executed. Full account and the running list of what the next manual run has to cover: BACKLOG.md's own entry. | OPEN |

---

## 4A. The connection limit of 6 — what silicon still owes

The limit itself is settled and confirmed on the committed image (SPECIFICATION.md H.7, evidence
`HEAP_FRAGMENTATION_MEASUREMENTS.md` archive §7R); every row that measured it is closed and deleted. By owner
decision (2026-09-24) these two get no dedicated sitting; they run with the next regular bench run:

| Row | What | Status |
| --- | --- | --- |
| W3 | `/status` wall-clock at 256 B pieces (`dev`'s `/status` is 29 pieces, 11 at the old 1,024 B): `tests_hardware/bench/test_end_to_end_timing.py` on the tree under test. F.1's +53 % was per *character*; this is per ~250 B | **MEASURED 2026-09-25** (image `05:21:43Z`), measured directly rather than through `test_end_to_end_timing.py`, which times no `/status`: 20 sequential idle `GET`s, 1 s apart. `/status` 6,859–6,865 B in **median 1.36 s** (min 1.30, p90 1.39, max 1.43 s); `/networking` 170 B in 0.34 s; `/measurements` ~510 B in 0.28 s. No 1,024 B silicon figure exists to compare with; the only earlier `/status` time is BACKLOG 24's 0.56–0.76 s during a sweep on 2026-09-17, a different image and not like-for-like. Owner to judge whether 1.36 s is acceptable, or whether one 1,024 B-piece build is worth measuring for the comparison |
| W5 | **The one response piece the 256 B cap does not bound, under the load the limit was measured at.** `_PieceWriter` never splits a fragment, so a single scalar longer than `chunk_bytes` is one over-cap piece, and `NTP_Host`'s settled 1,024-character bound makes a ~1,026 B piece reachable on `/networking` and in `/status`'s networking section (SPECIFICATION.md Part I.3). Every figure behind the limit of 6 was taken at the 12-character default, and the peak measurement leaves ~1.5 KB of largest free block — so this fits by argument, never by measurement, and would not fit the 528 B measured at 7. Set `NTP_Host` to its bound through the REST path, then run `test_network_resilience.py`'s peak arm and confirm both routes still come back complete and parseable. Costs one flash cycle for the config write, so it rides a run that already has `--allow-persistence-writes`; restore the old value afterwards | OPEN |

## 5. Excluded on purpose

- **G10, the UART protocol run against its C implementation** on the Arduino peer: `arduino/` is
  outside this project's scope (owner, 2026-09-24), reconciliation included, so the pairing test
  is too.
- **Nothing about the heap remediation is excluded.** Measures A, B, the placement guard and
  section D are closed (`HEAP_FRAGMENTATION_MEASUREMENTS.md` archive §7D-§7M); what the board still owes
  from that work is §1F.
- **PR #84's three bench passes** (`reactive` full suite 95 passed/2 skipped; `reactive` + churn
  pressure tests 3 passed; `threshold` full suite 95 passed/2 skipped) are already run, on that PR's
  own branch, and do not need repeating. **The PR itself was closed unmerged on 2026-09-18 by owner
  decision**, so its `--gc-policy` / `--memory-pressure` machinery is not available to
  any run listed above and is not coming — none of PR #84 is in the tree, and the tooling is
  unshipped by decision rather than pending.
- **The two unprovisioned bench-rig capabilities** (was H3): a programmable GPIO fault-injection
  harness and a second WiFi test client, each of which would move one `[MANUAL]` candidate to
  `[AUTO]`. **Owner, 2026-09-22: no hardware will be bought for this, so the rig stays as it is** —
  both candidates are permanently manual, which is a decision rather than a gap. The
  fault-injection half is worth re-opening as a new row if the hardware Part E.6.6's fourth
  exception mentions ever arrives.
- **Round 1's three answered requests** — `ResetErrors` idle timing, WIFI's all-or-nothing log
  across an abrupt restart, and the two `uart_link` instances through the reset path. Answered and
  migrated (SPECIFICATION.md Part A.7, BACKLOG 24). Do not re-measure.

---

## 6. Standing traps for whoever runs this

Condensed from CLAUDE.md and SPECIFICATION.md, because they are the ones that have actually cost
something:

- **The board's FRAM error logs are not a clean production record.** Every sitting since 2026-09-22
  ran isolated-driver device scripts, which overwrite production's first chunks. Read `errcount`
  before anything writes (Run sheet Step 1) and judge older entries by what has run since.
- **`bench.kick_all_stations()` (deauth) generates no WIFI log entries** — a persistence check built
  on it passes vacuously `0 → 0`. Use a real `bench.ap_down()` outage.
- **Any destructive test of the bench host's own network config keeps a recovery dead-man's-switch
  armed for the whole risk window.** A one-shot timer consumed by an earlier dry run gave zero
  protection to the real run that followed, and cost the Pi4 its own SSH access (SPECIFICATION.md
  Part B.13).
- **The hotspot role reversal's stage 0 clears the DUT's persisted SSID.** Stage 7 now restores it
  over the hotspot, but a failure between them used to leave the board permanently in hotspot mode
  with no STA config, recoverable only over the serial REPL. It has happened.
- **A `largest_block` figure that is exactly 192 KB / 2, / 4, / 8 … is the probe, not the heap.**
  98,304 / 49,152 / 24,576 / 12,288 are the values it takes when it pins its own buffer, and the
  reading is then an understatement. The `retained=` field on the same line says so outright — it
  equals `largest_block` in that case, and the scripts reread on their own (MEASUREMENTS §M2.2).
- **"After the starter list" and "after boot" are not the same position, and the gap is seconds.**
  Judge measure B by `after_starter_loop_end`; `after_starter_list` is taken seconds into the run
  phase, where the twin says most of B's gain is already gone on both arms (MEASUREMENTS §M3.9).
- **A DUT that has gone unreachable is usually your own `mpremote` call, not a fault — and every
  serial check you make to diagnose it re-causes it.** `exec` and `run` interrupt the running
  firmware into the REPL, so `main.py` stops and the board leaves the network; `run_isolated()`'s
  armed `WDT(timeout=8000)` then resets it ~8 s after the command ends. Cost real time twice
  (2026-09-18 and 2026-09-19), each time as a loop: curl fails → `exec` to look at the config →
  the look itself strands `main.py` again → curl still fails. **The config was intact every time.**
  Diagnose it *passively*: `hard_reset()`, then `Board.tail_log()` with no `exec`/`run` at all, and
  only then curl. Note `tail_log()` replays buffered history, so several identical
  "WLAN connection established" blocks are not a reboot loop — confirm that by polling `SysUptime`
  and watching it advance, which is the cheap discriminator.
- **A bench-tier test that opens as many concurrent connections as `max_connections` (6 today; 4
  when this was measured) cannot expect a definitive status from all of them.** Measured 2026-09-19
  with tiny bodies, so nothing to do with body size: concurrency 2 → 0% reset, 4 → 25%, 8 → 12%,
  24 → 25%. Resets start **at** the ceiling, not beyond it — a slot is held until its close has
  finished, and back-to-back clients at the limit see ~70 % refused (SPECIFICATION.md H.7). Before calling such a reset a defect, run the all-small-bodies control
  — it is two minutes and it separates "the feature under test" from "the connection ceiling"
  (SPECIFICATION.md Part I.6).
- **The connection-slot lag cuts both ways — a check made immediately *after* a burst is as
  exposed as one made immediately before it.** Part I.6 explains the *pre*-load half (the
  `reset_all_error_logs()` PUT still holding a slot); the same mechanism bites *after* the load too,
  where 24 workers' slots drain through `_serve()`'s `finally`. A single-shot
  `http_client.fetch()` there gets `ConnectionResetError` about two runs in three, and the very
  same request succeeds **75 ms** later. **Before reading such a reset as "the server is
  unresponsive", poll it** — the drain window is tens of milliseconds, not seconds. The idiom for
  this is `wait_until()`, which retries a raising check but still raises `TimeoutError` on a
  genuinely dead server, so polling here costs no strictness: a post-burst health check written as
  a bare `assert fetch(...) == 200` is the bug, not the server.
- **A REST reboot issued by hand strands the DUT in hotspot mode; the fixtures kick the AP's
  station table and you have to too.** `PUT /system {"SystemCmd": "reboot"}` on its own leaves a
  stale station entry on the bench AP, and the board comes back healthy but never re-associates —
  serial shows `WIFI Hotspot mode is active / Connected stations: []` and `NTP Network not
  available`, indefinitely. `conftest.py`'s `dut_ip` calls `bench.kick_all_stations()` before every
  `hard_reset()` and `test_real_reboot_sequencing_via_rest_completes_cleanly` calls it right after
  the same REST reboot, for exactly this. By hand: kick stations first, and expect to need a
  `hard_reset()` afterwards (which recovered it in ~40 s).
- **Don't chase `asy_fram_manager.py`/`asy_fram_driver.py` internals** from anything found here —
  heavily audited, and any real change there needs its own scoped review (SPECIFICATION.md C.3.1).
  **§1A is the one carve-out**: those two files plus `asy_spi_driver.py` are what measure A rewrote
  under an owner-granted scoped exception, so a failure in A6's script or §1F's rows is a finding *about* that change
  and belongs back to the PR #105 session — still not a drive-by fix here.
