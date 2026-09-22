# Real-hardware test queue

The single list of everything waiting on the dev bench, so one go-ahead session can run it all in
one go instead of rediscovering it from five documents. Temporary, like every other queue doc here:
each row is deleted once its result is migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`,
and the file goes when the last row does.

**Nothing here authorizes anything.** CLAUDE.md's standing gate still applies: a session needs the
project owner's go-ahead, given in that session's own conversation, before any `mpremote`, `nmcli`,
`picotool` or `tests_hardware/` run. `tests_hardware/README.md` remains the technical reference for
prerequisites, flags and safety facts; this file only says *what* is owed and *why*.

Status values: **OPEN** (owed), **BLOCKED** (waiting on a decision or another row), **DONE**
(result migrated — row deleted at that point), **EXCLUDED** (belongs to another effort).

## The finalisation checklist — everything still owed, in one place

Grouped by what each row *needs*, not by which effort opened it. **43 rows owed**, plus D1 and D2,
which the owner answered standingly on 2026-09-22 and no sitting re-asks. One row is blocked on
something the project does not have (G10's C source); nothing else waits on a decision any more.
This table is an index; the row's own entry below is what to read before running it.

| Group | Rows | What it needs |
| --- | --- | --- |
| **Per-sitting confirmation** | D3 | Which image. Always this branch's own tip; never a `wozi` build |
| **The suite runs** | S1, S2, then S3, S3b | One sitting. S1/S2 at default flags first, **then** S3 with `--allow-persistence-writes` (D1's ordering) and S3b with `--allow-neopixel-sweep`. **S1/S2 are owed again**: `tests_hardware/harness.py`, both wrapper scripts, `_require_clean_hardware_run.sh`, five tier files and `src/` itself have all changed since the last run |
| **Heap placement readings** | E1-E4, T1, T7 | The same sitting. No wear, no reflash, both arms from one image — the cheapest work on this list |
| **Measure A's leftovers** | T2, T3, T4 | The same sitting. T3 is 14 existing device scripts; T4 is one to write |
| **Memory gates and the (e) stage** | G7, G8, T6 | G7 and T6 ride along on S1/S2. G8 is a script to write first |
| **New features, and records that need no run** | N1-N4, R16 | N1/N4/R16 are one line in `SPECIFICATION.md` each, no bench time. N2/N3 are one look each |
| **Targeted investigations** | R1-R9, R13 | Bench time. R1, R4, R5 and R8's reboot arm ride on S3 |
| **Tests still to write** | G1, G3, G4, G6, G9, G10 | Code first, bench second. G6 is adapt-now-measure-later by decision; G10 waits on the C source |
| **The bench host itself** | H1, H2 | No board needed — they can run while it is busy |
| **Long soak and the light rig** | S4, M1 | Deliberately separate sittings. M1 is interactive and records the rig geometry S3b depends on |
| **Findings still open** | F1 | The script that stranded the bench once. Read its row in full before running it |

**What "finished on real hardware" means**: every row above DONE or explicitly EXCLUDED, each
result migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`, and this file deleted. Since
2026-09-22 that is reachable by one bench sitting plus the writing work — no row is waiting on an
owner decision any more.

## Where things stand (2026-09-22)

Every measurement row that opened this file is closed. **Measure A** (§1A) and **measure B** (§1B)
both ran on silicon on 2026-09-18/19, the **request-body cap** (§1D) closed green three times over,
the replaced tripwire passes with 5.5x margin, and the bench tier has now been fully clean on three
consecutive runs. All of it is written up in `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7D-§7L. What is
left is the checklist above: readings nobody has taken, scripts nobody has run, and tests that
still have to be written.

**The bench board carries a production image, not a test one.** On the owner's instruction
(2026-09-19) it was reflashed with a clean production `dev` image at `DebugLevel = 0` and joined to
the local network as an ordinary device. **Set `DebugLevel` back to 5 before any bench-tier run** —
several tests parse the serial log and fail silently at 0. MEASUREMENTS §7J.6 lists everything that
was changed and how to undo it.

**Every handover file this queue used to point at is deleted except one.**
`REAL_HARDWARE_HANDOVER_BOOT_CONTIGUITY.md` is still live: it is E1-E4's runnable form and carries
the 23-line port of `tests/_boot_contiguity_probe.py` the board needs.

## If there is time for one sitting only (revised 2026-09-22)

1. **Read `GET /status`'s `errcount` and write it down verbatim, before anything writes.**
   CLAUDE.md's rule, and it has cost real evidence twice now (MEASUREMENTS §7I.1).
2. **Build and flash this branch's own `dev` image** (D3). `src/` has changed since the last bench
   run, so no older image is this tree.
3. **One full bench-tier run at default flags** — `scripts/run_bench_hardware_suite.sh`, no
   arguments. It covers the flash tier, excludes the soak, leaves every wear gate off, and it is
   what re-establishes S1/S2 against the current harness. G7 and T6 close with it; R9 and R13's
   observations ride along.
4. **E1-E4 and T7 in one invocation pair** — one image, both arms, no wear, no reflash.
5. **T3's 14 FRAM device scripts**, then T4's per-command timing.
6. **F1's SSID script** — read §2A F1 in full first: this is the script that stranded the bench,
   and the fix is structural.
7. **Then, and only once 3 came back clean, the wear-gated re-run** — `--allow-persistence-writes`
   on both suites (S3), which is what makes R1, R4, R5 and R8's reboot arm reachable. D1 is a
   standing yes with exactly that ordering as its condition.
8. **M1, then S3b** — the light rig is in place (D2), and M1 is what writes the geometry down so
   the next sitting does not have to re-establish it. ~10 minutes together.

Everything else in this file can wait for another sitting.

---

## 0. Decide before the run

These change what gets run, so settle them first.

**D1 and D2 are answered standingly by the owner (2026-09-22), so a sitting does not re-ask them.**
**D1 yes, but sequenced**: the wear-gated rows run *once the suite is already green without them* —
a default run first, then the same two suites with `--allow-persistence-writes`, never both
questions open at the same time. So a failure in the gated set is the gated test's own, not
something the default run would also have shown. **D2 yes** — the NeoPixel-aimed-at-the-ISL29125
rig is in place, so `--allow-neopixel-sweep` may be passed; M1 records the geometry once, which
nothing has yet. **D3** stays a per-sitting confirmation, and its answer is always this branch's own
tip. **D4 is retired** — it asked whether §1A's before/after pair was being run, and §1A is closed;
one image suffices now.

| # | Decision | Why it matters | Status |
| --- | --- | --- | --- |
| D1 | **Does the bench spend flash/NVM writes this round?** A default run deselects 13 of the bench tier's 73 tests and 9 of the flash tier's 51; `--allow-persistence-writes` runs them and spends real cycles. `--allow-scd30-extra-write` is AND-gated on top for one further SCD30 NVM write. | Several rows below are *only* reachable with the flag — R1 and R4 in particular. Deselection is invisible to the pass/fail check, so this must be a knowing choice (CLAUDE.md's wear rule). | **ANSWERED 2026-09-22: yes, after a clean default run.** Not a per-sitting question any more; the ordering is the condition |
| D2 | **Is the NeoPixel-aimed-at-the-ISL29125 rig set up?** The gating question is **settled** — `main`'s `@pytest.mark.neopixel_sweep` + `--allow-neopixel-sweep` has been adopted here (2026-09-18), so `test_isl29125_survives_recombined_realistic_lighting_scenarios` (~8.5 min) and `test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration` (~99 s) now skip by default instead of failing on a bench without the rig. What remains is the physical question: decide whether to pass the flag this round. | The 2026-09-17 bench session ran both ungated and they passed after the `_park()` fix, which suggests the rig *is* in place — confirm rather than assume, and record the geometry via the manual tier's `isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry` (M1) so the next session does not have to. Opting in costs ~10 min. | **ANSWERED 2026-09-22: yes, the rig is in place.** Pass the flag; run M1 first, which is what records the geometry |
| D3 | **Which firmware image.** Every row below assumes a `dev` build from this branch's own tip via `scripts/build_firmware.py dev`. | CLAUDE.md's hard rule: a `wozi` build flashed onto the dev bench "tests nothing at all" and has produced false bugs before. | OPEN |

---

## 1. Run sheet - the order to work in

Every step below is a real command against real hardware, so **do not start any of them without
the go-ahead rule at the top of this file being satisfied**. Work top to bottom: each step assumes
the ones above it. `tests_hardware/README.md` stays the reference for *how* a step works
(prerequisites, environment variables, what each marker gates); this sheet is only the order, the
command, and what to write down.

**Step 1 - record the board's current state, before touching anything.**
`GET /status` and save the whole `errcount` table verbatim into this session's notes. It is the one
diagnostic a reboot does not erase and `ResetErrors` destroys irreversibly (CLAUDE.md). Then ask
what was last run against this board: an isolated-driver device script builds its own
`AsyFramManager` over the same chip and can leave a plausible-looking fabricated entry behind
(`tests_hardware/README.md` has the mechanism). An unexplained entry is evidence only if the
board's recent history allows it to be.

**Step 2 - answer D1, D2 and D3 (section 0) and write the answers down.** They decide which of the
steps below run at all. Nothing later re-asks.

**Step 3 - build and flash this branch's own `dev` image.**
`scripts/build_firmware.py dev`, then flash it. Never a `wozi` build (CLAUDE.md: it "tests nothing
at all" and has produced false bugs).

**Step 4 - the flash tier.** `scripts/run_flash_hardware_suite.sh`
Read the verdict's **deselected** count, not just the word "clean": the wear gates deselect rather
than skip, so "everything that ran, passed" is not "everything ran". Both device-script fixes and
the watchdog-starvation banner passed here on 2026-09-19, so a new failure in either is this
image's, not a known-broken test.

**Step 5 - the bench tier.** `scripts/run_bench_hardware_suite.sh`
A strict superset of step 4; same deselected-count caveat. G7, T6, R9 and R13's observations all
ride along here.

**Step 6 - the wear-gated re-run, once steps 4 and 5 are green.** D1 is a standing yes with that
ordering as its condition (section 0), so this is owed rather than optional — but never before the
default run is clean.
`scripts/run_flash_hardware_suite.sh --allow-persistence-writes` and the same for the bench script.
This is what makes R1, R4, R5 and R8's reboot arm reachable at all; without it they are deselected
and answered by nothing. Add `--allow-scd30-extra-write` only if a second SCD30 NVM write is
genuinely wanted on top.

**Step 7 - the NeoPixel light programs.** D2 is a standing yes: the rig is in place.
`scripts/run_manual_hardware_tests.sh --only isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry`
first (it is what records the rig geometry), then
`scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep`. ~10 minutes combined.

**Step 8 - the targeted investigations** in section 2, in this order: R1 (start with its no-code
`RangeAuto=false` bisection, and restore `RangeAuto` afterwards), R2's reader-count curve at 0, 1,
2, 3, 4 and 6 readers, then R3, R6/R7 and R13.

**Step 9 - the long soak, deliberately and separately.** `scripts/run_bench_soak_tests.sh`, tier
chosen on purpose (short 60 s / mid 600 s / long 6 h). Never bundled into steps 4-6; the suite
runners exclude it unconditionally.

**Step 10 - the bench host itself** (section 4): H1's two chroot legs and H2's parallelism probe.
Neither touches the board, so they can run while it is busy.

**Step 11 - close out.** For each row answered: migrate the result into `SPECIFICATION.md`,
`CLAUDE.md` or `BACKLOG.md` as the row says, then delete the row. **When the last row goes, delete
this file** - it is a queue, not a record.

| # | Suite run | Notes | Status |
| --- | --- | --- | --- |
| S1 | `scripts/run_flash_hardware_suite.sh` | **OWED AGAIN on the current tree.** Last run 2026-09-18 on both arms (tip: `3 failed, 33 passed, 3 skipped, 12 deselected`, 864.67 s) and the three failures have since been fixed and re-confirmed — but `tests_hardware/harness.py`, this wrapper, `_require_clean_hardware_run.sh`, `flash/test_memory_stress.py` and `src/` itself have all changed since, so that run does not speak for this image. Compare against `36 passed, 3 skipped, 12 deselected` | OPEN |
| S2 | `scripts/run_bench_hardware_suite.sh` | **OWED AGAIN, same reason.** Last run 2026-09-19 (A+B): `93 passed, 4 skipped, 27 deselected` — zero failures, the first fully clean bench run on any image, and the totals to compare against. Three bench files changed since (`test_memory_stress_bench.py`, `test_network_resilience.py`, `test_wifi_networking.py`) | OPEN |
| S3 | The same two with `--allow-persistence-writes` | Only if D1 says yes. This is what makes R1/R4 reachable at all. | OPEN — after step 5 is green (D1 answered yes, 2026-09-22) |
| S3b | `scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep` | Only if D2 says the rig is in place. Runs the two long ISL29125 light programs (~10 min combined); they skip otherwise. | OPEN — D2 answered yes, 2026-09-22: the rig is in place |
| M1 | `scripts/run_manual_hardware_tests.sh --only isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry` | Interactive. Repeatability on an unchanged scene, continuity across the range switch, **and** setting up and writing down the rig geometry S3b depends on. Worth doing before S3b, not after. | OPEN |
| S4 | Long memory soak (`long_soak` tier), never bundled into S1/S2 | A real long-duration memory-soak run has still never been executed (README.md's own "Further reading" note, carried from the retired hardware-planning docs). Pick the tier deliberately: short=60 s / mid=600 s / long=6 h. | OPEN |

**Before any of this**: read `GET /status`'s `errcount` and record it. CLAUDE.md's rule — the
FRAM-persisted per-module logs are the one piece of diagnostic evidence a reboot does not erase, and
`ResetErrors` destroys them irreversibly. Also check what has already been run against the board: an
isolated-driver device script builds its own `AsyFramManager` over the same chip and can leave a
plausible-looking fabricated entry behind (`tests_hardware/README.md` has the mechanism).

---

## 1A. Measure A — the FRAM path restructure — CLOSED, with one script that outlived it

Every row (A0-A9) ran on 2026-09-18 and is written up in `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7D:
the matched in-suite pair, the hold time on real wire, the boot cost, and the two fault injectors A
broke and §7F.7 then confirmed fixed on both arms. Three residuals outlived the table and are rows
of their own now — **N4** (the second-SPI-device question, structurally untestable, owed a line in
`SPECIFICATION.md`), **T2** (three of `test_bus_concurrency_under_api_load.py`'s six need D1) and
**F3** (a standalone heap reading measures the wrong thing — now recorded in
`tests_hardware/README.md`, so closed).

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

## 1B. Measure B — the boot-confined placement reset — CLOSED

Every row (B1-B7) ran on 2026-09-18/19: P1 to P5 all confirmed on silicon, the threshold-first
reading established that the shipped `gc.threshold(32768)` is what carries B's placement gain into
the run phase rather than merely adding to it, and the replaced tripwire passed with 5.5x margin on
its first silicon run. Written up in `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7F and §7H.

What measure B still owes is **placement rather than contiguity** — §1E — and the starter list's
own reading, **T7**. Neither needs a second image.

---

## 1C. Added features no measurement row covered, and the records they need

**The I2C shared scratch buffer is closed** (was C1): `asy_i2c_driver.py`'s one long-lived 32-byte
`bytearray` per bus is a bus-facing change, so CLAUDE.md's four-tier rule applied — tier 3 green
across two full flash suites and tier 4 green in the bench tier, 2026-09-19, §7H.6. The rows below
are what that run did not speak to.

| # | Item | Notes | Status |
| --- | --- | --- | --- |
| N1 | **The oversized-read fallback** (`nbytes > 32` allocates instead of sharing) is never taken on this hardware — BMP3XX's 21-byte calibration block is the largest read and stays under the threshold. | Record as structurally unexercised on `dev`, the same treatment A5 got for the second-SPI-device question. | OPEN (record) |
| N2 | **`asy_wifi_service._with_default()`** substitutes a build-time per-device default into the one-field hostname/SSID schema, dropping a value outside the field's own bounds rather than installing it — an unsatisfiable default makes `ConfigManager` answer `None` to every read, which would cost a device its networking config entirely. | The failure mode is "device boots with no networking config", so one look on the one board that can show it: `GET /networking`'s `Hostname` against `devices/dev.toml` after a clean boot. | OPEN |
| N3 | **`asy_uart_comm.py` reclassified which warning takes the episode's single persisted slot** — `_WRN_DRAIN_BOUND` (11) now wins over `_WRN_RESYNC` (10) when the drain bound was hit, because 11 separates a babbling peer from ordinary line noise. The boot drain persists nothing. | **Receiver-side only, no emitted bytes change**, so it is the preferred class of protocol change and a mixed-version pair still works — but it still needs a `UART_C_PORT_CHANGELOG.md` entry, which should be confirmed. `dev`'s two `uart_link` instances make it observable: check `errcount`'s `UART_init`/`UART_resp` history after a run that forces a resync. | OPEN |
| N4 | **The second-SPI-device question is structurally untestable on this hardware** (was A5): no `devices/*.toml` wires a second SPI device, so nothing can observe FRAM's whole-block bus hold from another device's point of view. A6 supplies the closest evidence — a second device would wait **21,269 us**, not the ~600 us the original row assumed. | Record it in `SPECIFICATION.md` Part F.5.8 beside A6's figures, the same treatment N1 gets. No run. | OPEN (record) |

---

## 1D. The request-body cap (Part I.6) — CLOSED

All five bench mirrors (W1-W5) ran on 2026-09-19 and pass: the boundary is exact at 2047/2048/2049,
the 3072-4096 band that used to be accepted now answers 413, the largest body any schema can
produce still fits (on the corrected 1312 B figure `tests_scripts/test_request_body_cap_headroom.py`
derives rather than quotes), a mixed stream is answered per request, and the concurrency row has
been green three times running since its post-load health check was fixed. Write-up:
MEASUREMENTS §7I.2 and §7J.2. **W2 is the row that told this firmware from the previous one**; the
mock tier, not the wire, is what proves the body is never *read* (Part I.6).

**Zero wear, and it must stay that way.** Every one pads an *unknown* sensor key, which
`PUT /sensors` ignores silently — so nothing validates, nothing persists and no `CFGMGR_*` logger
fires. None of them is `@pytest.mark.persistence_write`-marked and none should become so; if one
ever needs an *accepted* config write to make its point, that is the moment to add the marker.

---

## 1E. The boot placement reset, measured as placement (the host guard's board half) — never run

`HEAP_FRAGMENTATION_MEASUREMENTS.md` §7L built the host guard
(`tests_scripts/test_digital_twin_boot_contiguity.py`, 27 tests, all six devices) and measures
`gc.collect()`'s boot-confined reset **directly**: where each boot list's newly allocated blocks
land relative to its own seam, rather than a contiguity fraction. **Read §7L.7's figures, not
§7L.3's** — the bounds were re-derived on the settrace-free interpreter, which changed both the
metric and every number. Live against suppressed, as shipped: the **median's depth below the seam**
across the batch, 452,832 B against 218,528 B (**2.07x**, and 2.36x/4.64x arm-against-arm on
wozi/dev), and the whole sequence's **reach above the seam**, 16,352 B against 141,632 B
(**8.66x**, 12.96x/13.93x arm-against-arm). Retention is arm-independent to 0.05%. The setup
batch's own *reach* does **not** discriminate on this binary — 8,160 B in both arms on four of the
six devices — so do not look for a batch-reach separation on the board either.

**The board has taken no such reading, and cannot as it stands.**
`tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py` dumps no map at the seam —
`baseline` is a probe reading, not a `mem_info(1)` dump — so `heap_map.py`'s `delta()` has no
`before` for the batch. `REAL_HARDWARE_HANDOVER_BOOT_CONTIGUITY.md` is the runnable form and carries
the port (23 lines from `tests/_boot_contiguity_probe.py`).

**Both arms run from one image, no reflash.** The emitted collects resolve `gc` as a module global
in the generated module and in `system_service`, so a device script can suppress every one of them
at runtime. This removes the second firmware image §7D's arm comparison needed.

| # | Run | Notes | Status |
| --- | --- | --- | --- |
| E1 | Seam map + board reach, live arm | Extended `heap_layout_after_full_boot_sequence.py` on `dev`; compute `delta(seam, after_batch)` and `delta(seam, after_starter_loop_end)` host-side. Board units (16 B blocks) — the parser derives the block size, never convert by hand | OPEN |
| E2 | The same run, `--arm suppressed` | One invocation, same image, straight after E1 so the heap is aged alike. The board's first controlled A/B of the collects | OPEN |
| E3 | The ratio, which is the transferable claim | Host says **2.07x** on batch median depth and **8.66x** on cumulative reach (§7L.7). Same direction and order of magnitude confirms the mechanism on silicon; a ratio near 1.0 is a finding to record before anything else | OPEN |
| E4 | Does the board put the median at or below the seam top? | The host's live arm does, on all six devices — the strongest unit-free statement the metric makes | OPEN |

**No absolute host bound may be copied to the board.** §7L's bytes are twin units (32 B blocks,
x86-64). The ratio, the sign of the median and the zero count above the band transfer; the
300 KiB, 256 KiB and 64 KiB bounds do not. No new floor is asserted by any row here (§7G's rule).

**Zero wear.** No flash write, no persistence write, no marker, no reflash. Read the FRAM-backed
`errcount` before any `ResetErrors`, and remember an isolated-driver script overwrites production's
first FRAM chunks.

---

## 1F. Measure A/B's own leftover rows, carried over when the remediation plan closed

The (now deleted) remediation plan's section T held seven real-hardware rows. One is closed — T.5's
boot cost, §7F.7 — two are partly answered, and four never ran; the six that are not closed are the
table below. The plan was deleted once its other 53 boxes were closed — documentation holds current
state, not the path that got there (CLAUDE.md) — so those rows live here now, which is where a bench
session looks for them. **T.5 is not repeated**; T4 is listed because A6 above answers only its
aggregate half, not the per-command figure Part F.5.8 still asks for.

| # | Run (plan row) | Notes | Status |
| --- | --- | --- | --- |
| T1 | **The exact in-suite AFTER `largest_block`** (T.1) | A alone measured 20,592 → 28,864 B in-suite, +40.2% (§7D.3), and A + B **passes in-suite** against a BEFORE arm that fails — the first image ever to. What is still owed is only the precise AFTER figure: the test discarded it on a passing run, fixed host-side (§7F.6), so the next in-suite run yields it. Record it as §2.1's third and fourth [HW] columns. **Only like suite positions are comparable** (§7D.2) — a standalone reading does not answer this | PARTIAL |
| T2 | **Bus-hazard tier 4 on the A + B arm** (T.2) | Tier 3 is done: §7F's AFTER arm ran the full flash suite with zero failures, covering all three FRAM tests, and §7F.7 calls out the two rewritten injectors passing on *both* arms — the first real-chip proof the hijacked payload is refused. `tests_hardware/bench/test_bus_concurrency_under_api_load.py`'s six were last run on the **A-only** arm (§7D.5). No wear marker is needed by any of them; FRAM is outside the wear gate | PARTIAL |
| T3 | **Every FRAM device script green** (T.3) | All **13** under `tests_hardware/device_scripts/fram_*.py` — roundtrip, capacity, CS hijack, busy-status lockout, pause gating, write-protect, the two reset-race pairs and the error-log reset-race trio — plus `sgp40_fram_backup_restore.py`, which is not `fram_*`-named but is the same proof. They are the real-chip evidence that every safety measure survived the restructure. **Read the FRAM-backed `errcount` before any `ResetErrors`** (CLAUDE.md), and remember these scripts overwrite production's first chunks | OPEN |
| T4 | **Per-command hold time, measured** (T.4) | A device script timing one byte-level write (5 CS) and one `check_length` read slice with `time.ticks_us()` around the synchronous stretch, reported in its own `RESULT:` line; the number goes into `SPECIFICATION.md` F.5.8 beside the UART 4.4 ms frame. A6's aggregate is already there (2,849 us non-yielding, 21,269 us bus hold) — this is the per-command figure F.5.8 says is still owed. **If it is above ~1 ms the per-command yield policy is already the finest the chip allows**, and the finding is recorded, not "fixed". A6's own script is saved but not committed; T4 decides whether it becomes a committed device script | OPEN |
| T6 | **The run-phase memory check on silicon** (T.6) | `tests_hardware/flash/test_memory_stress.py`'s second test and `tests_hardware/bench/test_memory_stress_bench.py` green on the A + B image. Distinct from G7 below, which is about those two files' *gate* never having executed since it was widened — run them once and both rows close together | OPEN |
| T7 | **The starter list's own reading, which no run has taken** (T.7) | §7F.2's `after_starter_list` figures are taken 4 s into the run phase, and the twin loses most of B's gain inside the first ~2 s there (§7F.9) — so measure B's second site has never been measured on silicon at all. `heap_layout_after_full_boot_sequence.py` now reports `after_starter_loop_end`, detected by counting starters rather than waiting a constant. Two invocations, one per arm, each straight after that arm's suite run so the heap is aged. It also replaces the row §7F.8 withdrew and confirms `retained=0` on the probe | OPEN |

**Zero wear on all of them.** No flash cycle, no persistence write, no reflash; T3's scripts write
FRAM, which is outside the wear gate's scope by endurance. T7 shares B7/B8's invocation shape, so
run it in the same sitting as §1E.

---

## 2. Targeted investigations

**Owner confirmation, 2026-09-18**: R1 (item 30), R2 (item 32's reader-count curve), R3 (item 29's
spurious `W4`) and R5 (WP5's BMP3XX arm) are all confirmed as owed for the next go-ahead run - they
were put to the owner as open decisions and the answer was "record for the real-hardware run", not
"drop". Nothing about them is waiting on a further decision; they are waiting on bench time.

| # | Investigation | Source | Status |
| --- | --- | --- | --- |
| R1 | **BACKLOG item 30 — the ISL29125 HTTP connection reset under concurrent API load.** Owner's direction is to root-cause and resolve, not re-measure. Shape is established: needs **both** a config-persisting PUT **and** ≥2 concurrent readers (PUT alone 0/10, PUT+1 reader 0/6, PUT+2 readers **6/18**, plain GET+2 readers 0/6); failures land at 21–72 ms against 0.5–2.2 s for successes, and `WEBSERVER`'s counter stays 0 so FRAM forensics will not help. **Do the no-code bisection first**: `PUT /sensors {"ISL29125": {"RangeAuto": false}}` drops `_switch_range()` from the three-step push, leaving only `configure()` + `_reapply_persist()`. Rate falls → the threshold re-arm is implicated; unchanged → it is the first two. Restore `RangeAuto` afterwards. | BACKLOG 30 | OPEN — needs S3's wear-gated run, which is now owed rather than blocked |
| R2 | **BACKLOG item 32 — the `ResetErrors` reader-count curve.** Elapsed time at **0, 1, 2, 3, 4, 6** concurrent `GET /status` readers. Two points exist (6.32 s idle, 11.58 s at 3 readers = 77 % of the 15 s server cap); two points cannot say whether the curve flattens. | BACKLOG 32 | OPEN |
| R3 | **BACKLOG item 29 — the spurious `W4`.** A real outage logged `W4` ("WLAN wrong password") twice alongside the expected `W5`, on a network whose password never changed. One look at whether CYW43 genuinely reports that mid-transition (making `_assert_wifi_log_has_only_benign_ap_not_found_warning()` wrong) or whether `_poll_sta_connect_status()` mis-maps it. Do not chase far. | BACKLOG 29 | OPEN |
| R4 | **`ResetErrors` completeness under contention.** Pre-populate the FRAM error logs on several modules, then sweep under R2's reader load and confirm every counter reads back 0. All previous correctness checks were made at idle or with the logs already empty; a silently skipped chunk is invisible today because the call still answers `200`. | CLAUDE.md's FRAM `errcount` rule | OPEN — needs S3's wear-gated run |
| R5 | **BACKLOG "Refactor targets" — the WP5 deferred-config-write re-confirmation.** The BMP3XX arm passed on 2026-09-17 on WP5 firmware; make that durable rather than one run. The ISL29125 arm is R1, not this row. | BACKLOG, first entry | OPEN — needs S3's wear-gated run |
| R6 | **The `CFGMGR_SYSTEM` setup-order fix's unexplained +0.90 s of boot latency.** Boot latency itself is measured and needs no re-run: pre-WP **7.74 s** → WP1+WP2 **9.80 s** → WP1–WP8 **9.76 s** → +`CFGMGR_SYSTEM` fix **10.66 s** (medians of 5, spread ±0.06 s; 23 reboots, no `WDT_RESET`). Those figures were taken by PR #102, which the owner closed unmerged on 2026-09-18 — they are migrated into `SPECIFICATION.md` Part A.7's boot-latency note, so nothing is lost with the PR. What remains open is only the sub-question: **+0.90 s** is far more than one extra FRAM-backed logger's `setup()` should cost, and is unexplained. Worth understanding before the same reorder is assumed free elsewhere; it does not threaten the watchdog budget, so it is not a reason to revert. | SPECIFICATION.md Part A.7; BACKLOG 33 | OPEN |
| R8 | **Two newly adopted bench tests, never yet run on silicon** (ported from `main` 2026-09-18, see BACKLOG item 33). `test_isl29125_calibrate_command_push_over_real_rest` pins that a calibration run never moves the *applied* `GainRatio` and that `GainMeas` reaches `/measurements`; `test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value` pins that ratio across a real hard reset. The second is `@pytest.mark.persistence_write`-marked here (it owns two persisting PUTs) where `main` left it unmarked, so it needs D1. Both were written against `main`'s API shape and adapted to this branch's nested `PUT /sensors {"ISL29125": {...}}` body — expect the adaptation to be where a first run goes wrong, if anywhere. | BACKLOG 33 | OPEN — the reboot arm needs S3's wear-gated run |
| R9 | **Half closed: the shadow-divergence fix RAN and passed on silicon (§7H.6, the first fully clean bench tier); the `Overrange` field that replaced `W12` has still never run.** `configure()`'s device-session lock was widened to span the whole validate-mutate-write(-rollback) sequence (WP-era fix, unit-tested by `test_configure_never_exposes_the_shadow_ahead_of_a_write_still_in_flight`), but the false `wrnno=11` it fixes only ever manifested under real concurrent bench load - so only real load re-confirms it. Same run covers the `Overrange` half: `device_scripts/isl29125_mechanism_envelope.py` now reads the live field instead of the retired `W12` log entry. | BACKLOG, "Open questions" first entry | OPEN |
| R7 | **`SPECIFICATION.md` Part A.7's FRAM setup-cost figures are twin-only.** `digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time, so every number there excludes the real per-transaction cost. Re-measure on silicon. Largely the same instrumentation as R6. **Premise corrected by A6 (2026-09-18):** the omitted term is *not* mainly SPI wire time — at 1 MHz six transactions are ~300 us of the measured 2,849 us, so ~90 % is MicroPython interpreter / `machine.SPI` call overhead. Frame the re-measurement that way. | SPECIFICATION.md Part A.7 | OPEN |

| R13 | **UART `wrnno` 11 now takes the fault episode's one persisted slot when the drain hits its bound** (BACKLOG item 23, 2026-09-18). The bench exerciser drives the real crossover jumper, so a deliberately babbling peer is reproducible there in a way no mock is: confirm `GET /status` shows `W11` rather than `W10` for `UART_init`/`UART_resp` after one, and that a *boot* drain against the same babbling peer persists nothing at all. Low urgency - the mock tier covers the logic; this confirms it against a real UART's own timing. | BACKLOG item 23 | OPEN |
| R16 | **`SPECIFICATION.md` I.3's "smallest largest-allocatable-contiguous-block under real hammer load was 49152 bytes" may be the §7F.8 probe artefact, not a heap figure.** 49152 is exactly `192 KB / 4`, the value the binary-search probe returns when it pins its own buffer, and 192 KB is the ceiling both committed probes use. The instrument behind it came in with a merge from `main` and is not in this tree, so it cannot be checked host-side. **Low urgency and not alarming**: the artefact only ever understates, so `_MAX_STATUS_PIECE_BYTES = 1024`'s headroom is 48x or better either way — this is about not reusing the number as a heap measurement. Re-measure by running `heap_headroom_after_full_system_build.py` during a bench hammer run and reading `retained=`. | SPECIFICATION.md I.3 | OPEN (record) |
---

## 2A. Findings still open from the two bench sittings

Sixteen findings (F1-F16) were opened by the 2026-09-18 and 2026-09-19 sittings. **Fifteen are
closed**, written up in `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7I, §7J and §7K, and the ones whose
lesson outlives the fix are section 6's standing traps or, for F3's standalone-versus-in-suite heap
trap, `tests_hardware/README.md`'s own list. One is still open, and it needs one careful
invocation rather than a suite run.

| # | Finding | Status |
| --- | --- | --- |
| F1 | **`wifi_service_reconnect_repro.py` persists a garbage SSID and never restores it.** Its own step "overwriting SSID with a garbage value via the real `_set_dict_cfg()` path" writes `SSID = "wozi-diag2-net-does-not-exist"` into `config_WIFI.cfg` on the RP2040 **flash filesystem**. Because the script then dies on the reset — the board drops the USB CDC mid-run and `mpremote` ends in `OSError: [Errno 5]`, which is why it likely needs `run_isolated_expect_reset()` — the restore never runs. Observed directly: the DUT went unreachable and the REPL showed the garbage value. Recovered by writing the real SSID (`sensors-bench-fa9707`) back over the serial REPL and hard-resetting; stored password was untouched. **This is the exact class of incident CLAUDE.md's stage-0 trap warns about, via a script no warning covers** — `test_hotspot_role_reversal.py` got a stage-7 restore after the 2026-09-17 incident; this script never did. It also is **not** `@pytest.mark.persistence_write`-marked although the write is test-owned, which `tests_scripts/test_persistence_write_marker_completeness.py` cannot catch because it pins pytest tests, not `device_scripts/` invoked directly. | **FIXED 2026-09-18** (PR #105 session), still unverified on silicon — §1B's session decided B-D3 as *no* and deliberately did not run it, this being the script that stranded the bench. Both halves were wrong, not just the missing restore: `REAL_SSID` was hardcoded to `"sensors-bench-ap"` while the bench's own is `sensors-bench-fa9707`, so the restore would have written a *second* wrong SSID had it run at all. It now reads the live value through `_get_dict_cfg()` before overwriting, **aborts** rather than overwriting if it cannot read it back, and restores in a `finally` that re-reads instead of trusting a flag — so it is correct on both early returns and on any exception inside the repro. The snapshot also carries the real password, so it is never logged. **Marker decision: answered 2026-09-19, and the answer is that no marker is needed, because the production write is gone.** The script now points `conn.cfgmgr.config_file` at a scratch `config_HWTEST_WIFI.cfg` immediately after reading the real SSID, so `config_WIFI.cfg` is never opened for writing at all — the repro is driven by the in-memory cache, which is unchanged. That closes the hazard *structurally* rather than relying on a restore that a crash, a reset or a racing deferred flush can skip (`write_config()` stages and a separate task commits, so the old form could strand the board even on a clean exit path). Same convention as `reboot_persist_write.py`'s `config_HWTEST_REBOOT.cfg` and `isl29125_mechanism_envelope.py`'s `config_HWTEST_ISL29125.cfg` — those two were the only other `device_scripts/` files that own a persisting write, checked by grep, so the convention now covers all three. The scratch file is removed in a `finally` after `flush_pending()`, because it holds a full WIFI config including the real password. **Residual, and it is the owner's to weigh, not a blocker**: one scratch-file write still spends a flash cycle, and a directly-invoked device script has no pytest marker to gate that — CLAUDE.md's go-ahead rule is what gates it, and the script's own log line now says what it is about to do. |

---

## 3. Coverage gaps that need a bench session to close

From `tests_hardware/README.md`'s "Tenth pass" plus this branch's own additions. Each is a test to
*write* or a method to settle against real hardware, not just a run — except G7, which is written
and simply has never executed. **G1's predecessor is closed**: F.5.8's real-driver proof landed with
the 2026-09-19 tier-3/tier-4 runs (§7H.6).

| # | Gap | Status |
| --- | --- | --- |
| G1 | **The bench UART exerciser never issues a multi-chunk SET**, so "bench ⊇ flash" does not hold for the SET train the flash tier proves. Wire a periodic SET into `UartLinkExerciser._exercise_loop()`'s live load. | OPEN |
| G3 | **`_reboot()`'s alarm-pool-exhaustion fallback (`_force_watchdog_starve = True`) is mock-only.** | OPEN |
| G4 | **NOTIFY's own FRAM chunk has no hard-reset-recovery bench test**, unlike SGP40's. Needs an observable-write signal analogous to SGP40's `BackupTS` first. | OPEN |
| G6 | **`test_ticks_ms_real_2pow30_rollover` needs a measurement method that does not poll with `board.exec()`.** BACKLOG item 12 established on real hardware that every `exec` starves the watchdog and hard-resets the board ~8 s later, zeroing the counter — so the hour-by-hour poll can never climb toward 2**30, and a later read landing below an earlier one is the reboot, not a wrap. The vacuous-pass hole is closed (a drop now only counts as a wrap when the previous read was already within two hours of 2**30, so the ambiguity fails honestly), but that makes the test *fail* rather than measure. A real method has to leave the board running: feed or disable the watchdog from inside the polled code, or observe passively via `tail_log()`. Design decision, then a genuine ~12.4-day run behind `--allow-multi-day-rollover-wait`. | **DECIDED 2026-09-22: adapt the method, defer the measurement.** Do not drop the test — the chosen answer is a method that leaves the board running (feed or disable the watchdog from inside the polled code, or observe passively via `tail_log()`). The ~12.4-day run itself is deliberately not scheduled: we do not measure it yet, and the test is deselected by default behind `--allow-multi-day-rollover-wait`, so deferring costs nothing today |
| G7 | **The two real-hardware memory gates were widened on 2026-09-22 and have never executed.** `flash/test_memory_stress.py` and `bench/test_memory_stress_bench.py` matched `"Traceback"` or the bare string `"MemoryError"`, which catches a crash but never a caught-and-logged allocation failure — `src/` logs `str(e)`, and the board prints `"memory allocation failed, ..."` with no class name (SPECIFICATION.md Part I.4(e)). Both now read `harness.MEMORY_ERROR_MARKERS`. The change is text-matching only and cannot false-positive on a healthy log by construction (proven on the twin and unit tiers: zero hits across a full 85-file run), but **this session had no real-hardware go-ahead, so neither file has been run since.** First bench/flash sitting re-runs both; a new failure there is a genuine degrade the old gate was hiding, not a regression in the test. | OPEN — needs a bench sitting |
| G8 | **CLAUDE.md's (e) stage has never been asserted on silicon.** I.4(e)/(f) says the suite must pass at `gc.threshold(-1)` with zero allocation failures *before* it is run at the shipped `gc.threshold(32768)`, and both halves are machine-checked — but only on the host and twin tiers. `scripts/build_firmware.py` stages the generated boot entry as `main.py`, and it sets `gc.threshold(32768)` before `asyncio.run(main())` — so **every flash- and bench-tier run, which all drive the live firmware over REST, is an (f)-stage run.** The device scripts are the other way round: importing `sensortask_dev` never executes `main.py`, so they read at the reactive default (`heap_layout_after_full_boot_sequence.py` sets 32768 explicitly when it wants the production arm) — but they only ever measure **boot placement**, never the run phase under load. So the (e) bar itself, zero allocation failures under real load, has no silicon arm. It needs no second image either: boot the full system by importing it, drive host-side API load against it for a bounded window, and assert `harness.MEMORY_ERROR_MARKERS` never appears in the log. Zero wear: no flash cycle, no persistence write, no reflash. | OPEN — script to write |
| G9 | **The served website is asserted non-empty, never asserted to be this device's.** `test_real_static_website_content_serves_over_the_normal_bridge_network` and its hotspot twin check `200` and `len(body) > 0` and nothing else, so a frozen build carrying another device's definitions — or a stale one from before `buildgen/definitions.py` generated them (Part H.5.1) — passes both. `scripts/build_website.sh` inlines the definitions into the served tree rather than serving `definitions/<device>.json`, so the assertion is on the page body: it must name `dev`'s own instances and must *not* name an instance `devices/dev.toml` does not declare. One GET, zero wear, and it is the only check that the image's website half matches the image's firmware half. | OPEN — assertion to add |
| G10 | **The UART protocol's second implementation has never been exercised against this one.** `UART_C_PORT_CHANGELOG.md`'s Class A entries each say "re-verify against the real C source when it lands", and the owner has confirmed real hardware running the C side exists and can be connected to the dev board — which would test `asy_uart_comm.py` against a genuine second implementation rather than against itself over the crossover jumper. Until the C source is in this repo the reconciliation cannot be checked, so this is listed for completeness, not as owed work. | BLOCKED on the C implementation landing |

## 4. Bench-host tasks (not the board)

| # | Task | Status |
| --- | --- | --- |
| H1 | **The two-chroot verification, unsatisfied since 2026-09-12** — an owner-run periodic check since 2026-09-18, not a gate that blocks anything. Everything this branch changed in `scripts/`, `pyproject.toml` and — the highest-risk part, which the lint/typecheck recipe never exercises — `toolchain/setup_toolchain.py` + the new `toolchain/micropython_overrides.py`. The bench Pi4 already runs trixie/GCC 14.2, so it is the right host for the leg that has never run. **Two things make this run heavier than the last one**: `build_unix_port()` now builds **two** Unix ports (`build-standard` and `build-settrace`, Part E.5.2), so that step costs roughly twice the time and disk it used to; and `scripts/test.sh` was rewritten around them, so the chroot leg's `scripts/test.sh` invocation is exercising a different script than the recipe was last satisfied against. Also worth running once there: `GC_THRESHOLD=32768 scripts/test.sh`, the (f) stage, which no chroot leg has ever executed. Full account and the running list of what the next manual run has to cover: BACKLOG.md's own entry. | OPEN |
| H2 | **`scripts/test.sh`'s parallelism probe on the Pi4.** Report the `== Test parallelism: N (C usable cores x M, interpreter speed probe Xms)` line verbatim. Thresholds (4x ≤250 ms, 2x ≤900 ms, 1x beyond) were calibrated from an x86 sandbox plus a *simulated* slow host, never the real Pi4. Confirm it lands on 2x and that the previously-starved twin test (`test_digital_twin_sensortask_integration.py`'s hotspot/DNS case) passes. If it still starves at 2x, say so — the next step is 1x for that class, not re-tuning the probe. The band tests themselves were fixed on 2026-09-22 so they no longer measure the suite's own load, so a band the Pi4 reports now is the host's, not the run's. | OPEN |

---

## 5. Excluded on purpose

- **Nothing about the heap remediation is excluded any more.** Every measure — A, B, the placement
  guard (the old plan's section C) and section D — is built, closed and written up in
  `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7D-§7L; the plan itself was deleted on 2026-09-22 once its
  last box closed, its open real-hardware rows carried into §1F. What the board still owes from that
  work is §1E, §1F and T1 — listed as owed, not excluded.
- **PR #84's three bench passes** (`reactive` full suite 95 passed/2 skipped; `reactive` + churn
  pressure tests 3 passed; `threshold` full suite 95 passed/2 skipped) are already run, on that PR's
  own branch, and do not need repeating. **The PR itself was closed unmerged on 2026-09-18 by owner
  decision** (BACKLOG 33), so its `--gc-policy` / `--memory-pressure` machinery is not available to
  any run listed above and is not coming — none of PR #84 is on this branch, and the tooling is
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
  equals `largest_block` in that case, and the scripts reread on their own (MEASUREMENTS §7F.8).
- **"After the starter list" and "after boot" are not the same position, and the gap is seconds.**
  Judge measure B by `after_starter_loop_end`; `after_starter_list` is taken seconds into the run
  phase, where the twin says most of B's gain is already gone on both arms (MEASUREMENTS §7F.9).
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
- **A bench-tier test that opens more concurrent connections than `max_connections = 4` cannot
  expect a definitive status from all of them.** Measured 2026-09-19 with tiny bodies, so nothing
  to do with body size: concurrency 2 → 0% reset, 4 → 25%, 8 → 12%, 24 → 25%. Resets start **at**
  the ceiling, not beyond it. Before calling such a reset a defect, run the all-small-bodies control
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
  under an owner-granted scoped exception, so a failure in §1A's or §1F's rows is a finding *about* that change
  and belongs back to the PR #105 session — still not a drive-by fix here.
