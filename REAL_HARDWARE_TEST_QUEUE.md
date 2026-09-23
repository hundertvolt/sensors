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

Grouped by what each row *needs*, not by which effort opened it. **28 rows owed** — fifteen closed in
the 2026-09-22 sitting (S1, S2, T3, T6, G7, E1-E4, T7, N1, N4, R16, G9, H2), whose results are in
`HEAP_FRAGMENTATION_MEASUREMENTS.md` §7M and §7N, `SPECIFICATION.md` I.2/F.5.8/I.3, and BACKLOG 28. D1 and D2 are the owner's standing answers and no
sitting re-asks them. One row is blocked on something the project does not have (G10's C source);
**S3 is blocked on nothing technical** — it was denied by the running session's own permission
classifier, since it opts into spending real flash/NVM endurance, and needs the owner to allow it.
This table is an index; the row's own entry below is what to read before running it.

| Group | Rows | What it needs |
| --- | --- | --- |
| **Per-sitting confirmation** | D3 | Which image. Always this branch's own tip; never a `wozi` build |
| **The suite runs** | S3, S3b | **S1 and S2 are DONE** (2026-09-22, both clean — §7N), which satisfies D1's ordering condition, so S3 (`--allow-persistence-writes`) is now owed rather than conditional. S3b needs `--allow-neopixel-sweep` and M1 first |
| **Heap placement readings** | T1 | **E1-E4 and T7 are DONE** (2026-09-22 — §7M), and the finding is that the twin's ratios do not transfer at the board's fill. T1 still wants the in-suite AFTER `largest_block` |
| **Measure A's leftovers** | T2, T4 | **T3 is DONE**: all 14 FRAM device scripts are driven by flash-tier tests that passed in S1 and S2, so it needed no separate run. T4 is one to write |
| **Memory gates and the (e) stage** | G8 | **G7 and T6 are DONE** — both memory-gate files ran and passed on this image (§7N). G8 is still a script to write first |
| **New features, and records that need no run** | N1-N4, R16 | N1/N4/R16 are one line in `SPECIFICATION.md` each, no bench time. N2/N3 are one look each |
| **Targeted investigations** | R1-R9, R13 | Bench time. R1, R4, R5 and R8's reboot arm ride on S3 |
| **Tests still to write** | G1, G3, G4, G6, G10 | Code first, bench second. **G9 is DONE** (2026-09-22): `tests_hardware/website_identity.py` derives the expected names from `devices/dev.toml` through buildgen and both website tests now use it. G6 is adapt-now-measure-later by decision; G10 waits on the C source |
| **The bench host itself** | H1 | **H2 is DONE** (2026-09-22): the Pi4 reports 4x, not the predicted 2x, and the suite is green there — migrated to BACKLOG item 28, which is now closed. H1 needs no board either |
| **Long soak and the light rig** | S4, M1 | Deliberately separate sittings. M1 is interactive and records the rig geometry S3b depends on |
| **Findings still open** | F1 | The script that stranded the bench once. Read its row in full before running it |

**What "finished on real hardware" means**: every row above DONE or explicitly EXCLUDED, each
result migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`, and this file deleted. Since
2026-09-22 that is reachable by one bench sitting plus the writing work — no row is waiting on an
owner decision any more.

## Where things stand (2026-09-22, after the evening sitting)

Every measurement row that opened this file is closed. **Measure A** (§1A) and **measure B** (§1B)
both ran on silicon on 2026-09-18/19, the **request-body cap** (§1D) closed green three times over,
the replaced tripwire passes with 5.5x margin, and the bench tier has now been fully clean on four
consecutive runs. All of it is written up in `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7D-§7N.

**The 2026-09-22 sitting closed fifteen rows and produced one real finding.** Ten of them came off
the bench runs: S1 (36 passed) and S2 (98 passed) are both clean on a freshly built and flashed
image from this branch's tip; T3, T6 and G7 close on those same runs; E1-E4 and T7 took the board's
first placement reading. The other five needed no board — G9, H2, N1, N4 and R16. **The finding is
§7M**: the twin's two transferable ratios — 2.07x on batch median depth, 8.66x on cumulative reach —
come out **0.69x (inverted) and 0.91x (no separation)** on silicon, with tight repeats and the
obvious confound ruled out. What transfers is the batch's own reach (1.5x) and the sign of the
whole-sequence median. It changes no threshold and impugns no shipped collect; it bounds what the
host guard's numbers are a statement *about*. Read §7M before using any of §7L's figures as a claim
about the board.

**The board now runs this branch's tip at `DebugLevel = 5`**, not the 2026-09-19 production image at
0. It was rebuilt (`buildDate 2026-09-22T16:11:57Z`), reflashed with `picotool load -x -v`, and the
`DebugLevel` restored over the serial REPL before any tier ran. If the board is wanted back as an
ordinary quiet device, MEASUREMENTS §7J.6 is still the recipe — it has to be re-applied.

**One caution for the next reader of the FRAM error logs**: this sitting ran ten isolated-driver boot
scripts, which build their own `AsyFramManager` over the same chip, so production's first chunks are
overwritten. §7N records the clean pre-sitting `errcount` reading, which is the trustworthy one.

**Every handover file this queue used to point at is now deleted.**
`REAL_HARDWARE_HANDOVER_BOOT_CONTIGUITY.md` went with E1-E4, which is the condition its own "Done
when" set; the `_ProbeGc` port it carried lives in
`tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py` now.

## If there is time for one sitting only (revised 2026-09-22, after the evening sitting)

Steps 1-5 of the previous version are done and are not repeated. The board already carries this
branch's tip at `DebugLevel = 5`, so a sitting that follows soon can skip the rebuild — but **check
`buildDate` against the tree before trusting that**, and reflash if `src/` has moved.

1. **Read `GET /status`'s `errcount` and write it down verbatim, before anything writes.**
   CLAUDE.md's rule, and it has cost real evidence twice now (MEASUREMENTS §7I.1).
2. **The wear-gated re-run (S3)** — `--allow-persistence-writes` on the bench wrapper, which is a
   strict superset of the flash one. D1's ordering condition is **satisfied**: S1 and S2 came back
   clean on 2026-09-22. This unlocks R1, R4, R5 and R8's reboot arm, none of which is reachable
   without it. It is the single highest-value thing left on this list.
3. **M1, then S3b** — the light rig is in place (D2), and M1 is what writes the geometry down so
   the next sitting does not have to re-establish it. ~10 minutes together.
4. **F1's SSID script** — read §2A F1 in full first: this is the script that stranded the bench,
   and the fix is structural but still unverified on silicon.
5. **T4's per-command timing**, then T1's in-suite AFTER `largest_block`.

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
| S3 | The same two with `--allow-persistence-writes` (the bench wrapper alone suffices — it is a strict superset of the flash one) | **RUN ONCE, 2026-09-22: `1 failed, 118 passed, 4 skipped, 6 deselected`, 49:40.** The failure was real and is fixed — `write_config()` only stages, and three `device_scripts/` files never flushed, so two of them were passing tests while writing defaults (MEASUREMENTS §7O). Re-verified on the two affected tests only (`2 passed`) plus the board's own files; a guard now pins it. **Not re-run green end to end, by owner decision** — a second gated pass was stopped mid-run, because permission to spend wear covers one run and "re-run to confirm" is the loop the gate exists to prevent. The 2026-09-23 re-run (Status column) answered R8 and advanced R5; R1 and R4 still need their own investigation | **DONE 2026-09-23 — `124 passed, 4 skipped, 6 deselected`, 53:55, clean end to end** on image A (pre-fix `src/`, `max_connections = 7`), so a baseline for that image rather than a validation of the tip. Closed R8, advanced R5; R1/R4 still need their own investigation. `BENCH_SITTING_2026-09-23_HANDOVER.md` §7 |
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
| N2 | **`asy_wifi_service._with_default()`** substitutes a build-time per-device default into the one-field hostname/SSID schema, dropping a value outside the field's own bounds rather than installing it — an unsatisfiable default makes `ConfigManager` answer `None` to every read, which would cost a device its networking config entirely. | **Looked at 2026-09-22, and the failure mode is absent**: after a clean boot `GET /networking` returns a full, sane config with `Hostname` = `SensorStationDev`, matching `devices/dev.toml` exactly. **Partial, not closed** — this board carries a persisted `config_WIFI.cfg` whose own `Hostname` is already `SensorStationDev` (written 2026-09-19, §7J.6), and a persisted value pre-empts the default, so the substitution path itself is still unproven on silicon. Closing it needs a boot with that key absent from the persisted config | PARTIAL |
| N3 | **`asy_uart_comm.py` reclassified which warning takes the episode's single persisted slot** — `_WRN_DRAIN_BOUND` (11) now wins over `_WRN_RESYNC` (10) when the drain bound was hit, because 11 separates a babbling peer from ordinary line noise. The boot drain persists nothing. | **Receiver-side only, no emitted bytes change**, so it is the preferred class of protocol change and a mixed-version pair still works — but it still needs a `UART_C_PORT_CHANGELOG.md` entry, which should be confirmed. `dev`'s two `uart_link` instances make it observable: check `errcount`'s `UART_init`/`UART_resp` history after a run that forces a resync. | OPEN — **checked 2026-09-22 and there is nothing to read yet**: after a full clean bench tier, `errcount` carries no `UART_init`/`UART_resp` entry at all (`UARTLINK` 363 transfers, 0 failures), because nothing in the default suite forces a resync. This row needs R13's babbling-peer setup to produce the entry it wants to inspect; the two are one piece of work, not two |

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

## 1E. The boot placement reset, measured as placement — CLOSED 2026-09-22, and it did not confirm

E1-E4 ran on `dev` on 2026-09-22, both arms from one image with no reflash, and **T7 closed with the
same runs**. The full write-up is `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7M; the short version is that
the board does **not** reproduce the twin's transferable ratios.

| metric | twin (§7L.7) | board (median of 3 per arm) |
|---|---|---|
| batch median depth below seam | 2.07x live | **0.69x — inverted** |
| whole sequence reach above seam | 8.66x live | **0.91x — no separation** |
| batch reach above seam | no discrimination | **1.53x, correct direction** |
| whole sequence median | 3.3x live | **sign discriminates** (live 976 B below the seam, suppressed 1,840 B above) |
| retention (`used_bytes`) | arm-independent to 0.05% | **0.05% — matches** |

Repeats are tight, and the one credible confound — the script's own pre-batch probe, which allocates
132,672 B of a 135,008 B pool on a 192,832 B heap and so defragments the heap immediately before the
measurement — was tested with a variant that removes it. Every magnitude moved; no direction did.

**The likely reason is fill, and §7M states it as interpretation rather than measurement**: the
twin's own absolute figures are each larger than this board's entire heap, which is already 51%
allocated at the seam. **No threshold was fitted to any of this** (§7G's rule), and measure B's
silicon confirmation is untouched — that was §7F's contiguity evidence, a different metric.

**Every run's figures are in §7M.5**, in board units (16 B blocks, 12,052 blocks, 192,832 B total),
including both band counts the handover named — `>128 KiB` and `>512 KiB` are **0 in every run of
both arms**, structurally, since 128 KiB above a seam at ~98,700 B already exceeds the whole heap.
The raw `mem_info(1)` block maps (8,370 lines) were not committed — this repo gitignores run logs —
and §7M.5 carries the exact command to regenerate them.

The instrument change is committed: `heap_layout_after_full_boot_sequence.py` now carries the
`_ProbeGc` port and dumps a seam map, with the arm selected by
`exec "_ARM_OVERRIDE='suppressed'"` in the same raw-REPL session (assigning `sys.argv` raises on
this board — verified, not assumed). `REAL_HARDWARE_HANDOVER_BOOT_CONTIGUITY.md` is deleted, which
is what its own "Done when" required.

---

## 1F. Measure A/B's own leftover rows, carried over when the remediation plan closed

The (now deleted) remediation plan's section T held seven real-hardware rows. **Four are now
closed** — T.5's boot cost (§7F.7), plus T3, T6 and T7 in the 2026-09-22 sitting (§7M, §7N) — and
the three below are what is left, two of them partly answered. The plan was deleted once its other
53 boxes were closed — documentation holds current state, not the path that got there (CLAUDE.md) —
so those rows live here now, which is where a bench session looks for them. T4 is listed because A6
above answers only its aggregate half, not the per-command figure Part F.5.8 still asks for.

| # | Run (plan row) | Notes | Status |
| --- | --- | --- | --- |
| T1 | **The exact in-suite AFTER `largest_block`** (T.1) | A alone measured 20,592 → 28,864 B in-suite, +40.2% (§7D.3), and A + B **passes in-suite** against a BEFORE arm that fails — the first image ever to. What is still owed is only the precise AFTER figure: the test discarded it on a passing run, fixed host-side (§7F.6), so the next in-suite run yields it. Record it as §2.1's third and fourth [HW] columns. **Only like suite positions are comparable** (§7D.2) — a standalone reading does not answer this | PARTIAL |
| T2 | **Bus-hazard tier 4 on the A + B arm** (T.2) | Tier 3 is done: §7F's AFTER arm ran the full flash suite with zero failures, covering all three FRAM tests, and §7F.7 calls out the two rewritten injectors passing on *both* arms — the first real-chip proof the hijacked payload is refused. `tests_hardware/bench/test_bus_concurrency_under_api_load.py`'s six were last run on the **A-only** arm (§7D.5). No wear marker is needed by any of them; FRAM is outside the wear gate | PARTIAL |
| T4 | **Per-command hold time, measured** (T.4) | A device script timing one byte-level write (5 CS) and one `check_length` read slice with `time.ticks_us()` around the synchronous stretch, reported in its own `RESULT:` line; the number goes into `SPECIFICATION.md` F.5.8 beside the UART 4.4 ms frame. A6's aggregate is already there (2,849 us non-yielding, 21,269 us bus hold) — this is the per-command figure F.5.8 says is still owed. **If it is above ~1 ms the per-command yield policy is already the finest the chip allows**, and the finding is recorded, not "fixed". A6's own script is saved but not committed; T4 decides whether it becomes a committed device script | OPEN |

**Zero wear on all three.** No flash cycle, no persistence write, no reflash.

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
| R5 | **BACKLOG "Refactor targets" — the WP5 deferred-config-write re-confirmation.** The BMP3XX arm passed on 2026-09-17 on WP5 firmware; make that durable rather than one run. The ISL29125 arm is R1, not this row. | BACKLOG, first entry | OPEN — **second green run 2026-09-23** in S3 (both BMP3XX config-write arms passed); whether two runs is durable is the owner's call |
| R6 | **The `CFGMGR_SYSTEM` setup-order fix's unexplained +0.90 s of boot latency.** Boot latency itself is measured and needs no re-run: pre-WP **7.74 s** → WP1+WP2 **9.80 s** → WP1–WP8 **9.76 s** → +`CFGMGR_SYSTEM` fix **10.66 s** (medians of 5, spread ±0.06 s; 23 reboots, no `WDT_RESET`). Those figures were taken by PR #102, which the owner closed unmerged on 2026-09-18 — they are migrated into `SPECIFICATION.md` Part A.7's boot-latency note, so nothing is lost with the PR. What remains open is only the sub-question: **+0.90 s** is far more than one extra FRAM-backed logger's `setup()` should cost, and is unexplained. Worth understanding before the same reorder is assumed free elsewhere; it does not threaten the watchdog budget, so it is not a reason to revert. | SPECIFICATION.md Part A.7; BACKLOG 33 | OPEN |
| R8 | **Two newly adopted bench tests, never yet run on silicon** (ported from `main` 2026-09-18, see BACKLOG item 33). `test_isl29125_calibrate_command_push_over_real_rest` pins that a calibration run never moves the *applied* `GainRatio` and that `GainMeas` reaches `/measurements`; `test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value` pins that ratio across a real hard reset. The second is `@pytest.mark.persistence_write`-marked here (it owns two persisting PUTs) where `main` left it unmarked, so it needs D1. Both were written against `main`'s API shape and adapted to this branch's nested `PUT /sensors {"ISL29125": {...}}` body — expect the adaptation to be where a first run goes wrong, if anywhere. | BACKLOG 33 | **DONE 2026-09-23** — both tests passed on silicon in S3's gated run, the first time either ran. `BENCH_SITTING_2026-09-23_HANDOVER.md` §7 |
| R9 | **Half closed: the shadow-divergence fix RAN and passed on silicon (§7H.6, the first fully clean bench tier); the `Overrange` field that replaced `W12` has still never run.** `configure()`'s device-session lock was widened to span the whole validate-mutate-write(-rollback) sequence (WP-era fix, unit-tested by `test_configure_never_exposes_the_shadow_ahead_of_a_write_still_in_flight`), but the false `wrnno=11` it fixes only ever manifested under real concurrent bench load - so only real load re-confirms it. Same run covers the `Overrange` half: `device_scripts/isl29125_mechanism_envelope.py` now reads the live field instead of the retired `W12` log entry. | BACKLOG, "Open questions" first entry | OPEN |
| R7 | **`SPECIFICATION.md` Part A.7's FRAM setup-cost figures are twin-only.** `digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time, so every number there excludes the real per-transaction cost. Re-measure on silicon. Largely the same instrumentation as R6. **Premise corrected by A6 (2026-09-18):** the omitted term is *not* mainly SPI wire time — at 1 MHz six transactions are ~300 us of the measured 2,849 us, so ~90 % is MicroPython interpreter / `machine.SPI` call overhead. Frame the re-measurement that way. | SPECIFICATION.md Part A.7 | OPEN |

| R13 | **UART `wrnno` 11 now takes the fault episode's one persisted slot when the drain hits its bound** (BACKLOG item 23, 2026-09-18). The bench exerciser drives the real crossover jumper, so a deliberately babbling peer is reproducible there in a way no mock is: confirm `GET /status` shows `W11` rather than `W10` for `UART_init`/`UART_resp` after one, and that a *boot* drain against the same babbling peer persists nothing at all. Low urgency - the mock tier covers the logic; this confirms it against a real UART's own timing. | BACKLOG item 23 | OPEN |
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
| G8 | **CLAUDE.md's (e) stage has never been asserted on silicon.** I.4(e)/(f) says the suite must pass at `gc.threshold(-1)` with zero allocation failures *before* it is run at the shipped `gc.threshold(32768)`, and both halves are machine-checked — but only on the host and twin tiers. `scripts/build_firmware.py` stages the generated boot entry as `main.py`, and it sets `gc.threshold(32768)` before `asyncio.run(main())` — so **every flash- and bench-tier run, which all drive the live firmware over REST, is an (f)-stage run.** The device scripts are the other way round: importing `sensortask_dev` never executes `main.py`, so they read at the reactive default (`heap_layout_after_full_boot_sequence.py` sets 32768 explicitly when it wants the production arm) — but they only ever measure **boot placement**, never the run phase under load. So the (e) bar itself, zero allocation failures under real load, has no silicon arm. It needs no second image either: boot the full system by importing it, drive host-side API load against it for a bounded window, and assert `harness.MEMORY_ERROR_MARKERS` never appears in the log. Zero wear: no flash cycle, no persistence write, no reflash. | OPEN — script to write |
| G10 | **The UART protocol's second implementation has never been exercised against this one.** `UART_C_PORT_CHANGELOG.md`'s Class A entries each say "re-verify against the real C source when it lands", and the owner has confirmed real hardware running the C side exists and can be connected to the dev board — which would test `asy_uart_comm.py` against a genuine second implementation rather than against itself over the crossover jumper. Until the C source is in this repo the reconciliation cannot be checked, so this is listed for completeness, not as owed work. | BLOCKED on the C implementation landing |

## 4. Bench-host tasks (not the board)

| # | Task | Status |
| --- | --- | --- |
| H1 | **The two-chroot verification, unsatisfied since 2026-09-12** — an owner-run periodic check since 2026-09-18, not a gate that blocks anything. Everything this branch changed in `scripts/`, `pyproject.toml` and — the highest-risk part, which the lint/typecheck recipe never exercises — `toolchain/setup_toolchain.py` + the new `toolchain/micropython_overrides.py`. The bench Pi4 already runs trixie/GCC 14.2, so it is the right host for the leg that has never run. **Two things make this run heavier than the last one**: `build_unix_port()` now builds **two** Unix ports (`build-standard` and `build-settrace`, Part E.5.2), so that step costs roughly twice the time and disk it used to; and `scripts/test.sh` was rewritten around them, so the chroot leg's `scripts/test.sh` invocation is exercising a different script than the recipe was last satisfied against. Also worth running once there: `GC_THRESHOLD=32768 scripts/test.sh`, the (f) stage, which no chroot leg has ever executed. Full account and the running list of what the next manual run has to cover: BACKLOG.md's own entry. | OPEN |

---

## 4A. Connection scaling (the raised TCP ceiling) — never run

**RUN 2026-09-23. C1, C2, C5, C5b, C5c and C6 are all closed** — see
`BENCH_SITTING_2026-09-23_HANDOVER.md`, which is the full record of that sitting and also carries
the one finding it opened: at `gc.threshold(-1)` the board serves at most **4** concurrent requests
without an allocation failure, so the shipped ceiling of 7 depends on the threshold being set.

Opened 2026-09-22 by the connection-scaling branch. **`REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md`
is the runnable form of all of this** — it is written standalone, for a session with no prior
knowledge, and carries the full method, the traps and the recording table. These rows are the index.

| Row | What | Status |
| --- | --- | --- |
| C1 | Flash this tree's own `dev` image and confirm the build's own lwIP-macro verification passes on the real build | **DONE 2026-09-23** — all 11 macros read back out of the real firmware translation unit equal what `versions.toml` asks. PLAN §8.7.1 |
| C2 | `test_the_board_holds_exactly_the_connection_ceiling_this_tree_configures` — the board must admit exactly 7 | **DONE 2026-09-23** — exactly 7, five probes for five; refusal is a clean FIN 6 ms after connect. Needed a probe fix first (SPEC H.7.1). PLAN §8.7.1 |
| C3 | The rest of the bench tier at the shipped setting: `test_network_resilience.py`, `test_end_to_end_timing.py`, `test_bus_concurrency_under_api_load.py`, `test_memory_stress_bench.py`. All now scale their bursts with the configured ceiling | OPEN |
| C4 | Record §7's full table for the shipped setting — contiguity after boot and under load, `.bss`/`.data`, latency, every `MemoryError`/`memory allocation failed` spelling, any watchdog reset | OPEN |
| C5 | The wall, in **two images not a bisection** | **DONE 2026-09-23** — image B admitted all 16, five for five: **no admission wall below 16**, so the shipped 7 has >=2.3x margin and image C was not built. But admission is not service: image B serves only 13/16 and its first 500 lands at N=7. PLAN §8.7.2 |
| C5b | Every admitted connection actually **served** | **DONE 2026-09-23** — both rows pass on image A at the shipped 7; both fail on image B at 16 (bodies truncated to 3,072 B or empty). PLAN §8.7.2 |
| C5d | Rows 7/8 of the handover's decision table: the board's heap AT PEAK with a full ceiling genuinely held open - `test_heap_under_connection_ceiling.py` plus its device script | **DONE 2026-09-23** — held at the ceiling 98% of samples, 15 placeable 2 KB blocks at worst against a demand of 7, after four instrument defects were fixed. `BENCH_SITTING_2026-09-23_HANDOVER.md` §3.4 (this row was left OPEN by that sitting's commit and is closed here from its own record) |
| C5c | Whether `PBUF_POOL_SIZE` really can stay at 16 | **DONE 2026-09-23 — yes.** At an 8x advertised inbound over-commit (16 x TCP_WND against 12,832 B of pool) the pbuf pool never surfaced; the GC heap bound first in both images. PLAN §8.7.3 |
| C6 | A `LWIP_STATS = 1` image, only if C5 fails for a reason that cannot be named | **DONE 2026-09-23 without building it** — the reason was nameable directly: `MemoryError` tracebacks captured off the serial console show MicroPython's **GC heap**, not any lwIP pool, allocating 296-862 B inside `_stream_dict_response()`. PLAN §8.7.2 |

**Why none of it could be done in the session that wrote it**: no real hardware was reachable, and
the digital twin runs on the Unix port, which has no lwIP at all. Everything above the transport is
already measured and green (`CONNECTION_SCALING_PLAN.md` §8.3/§8.4); the PCB and pbuf ceilings are
structurally outside what the twin can see.

## 4B. Serving at `gc.threshold(-1)` — the 2026-09-23 finding, fixed, and the limit raised to 8

Opened by the sitting's §4 (at most 4 concurrent requests without a `MemoryError` at MicroPython's
own default). **Root-caused and fixed in the twin the same day** — `HEAP_FRAGMENTATION_MEASUREMENTS.md`
§7Q is the full account, `SPECIFICATION.md` I.3 the rule it produced. In one line: a loaded heap at
`-1` keeps ~100 KB free as small holes and no large run, and the routes assembled their JSON in
pieces of up to ~870 B; every route now writes through a bounded writer whose largest allocation is
one 256 B piece. The owner then set `max_connections = 8`, targeting 10 stable (SPECIFICATION.md
H.7). **`REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md` §0 is the runnable procedure for all of it.**

The instrument is `tests_hardware/bench/test_serving_heap_at_default_gc.py` — about 10 minutes, part
of the routine bench tier, the board restored once at the end. Both device scripts it drives, and
the test's own functions, host driver and assertions, were run against the twin before this row was
written — the sweep passed there in 155 s, and it caught three instrument defects first (§7Q.13).

| Row | What | Status |
| --- | --- | --- |
| W1 | **The fix on silicon, at the shipped limit**: flash this branch's tip (image F), run the file. `test_every_source_and_route_fits_a_small_free_run` — twin prediction: no route or source needs a free run above 320 B (as shipped, `/status` needed 1,024). `test_serving_sweep_at_the_reactive_default` — N = 4, 6, 8, 10 at `gc.threshold(-1)` on one boot: **zero allocation failures**, 8 served per round at N = 10 and 2 refused cleanly. It also answers the recovery question the twin could not: its `pre`/`post` dumps are the idle heap before and after the load | **RUN 2026-09-23 — FAILED on the static page** (11 × 1,025 B, bodies cut off behind a `200`); the JSON routes matched the twin. Fixed; re-run is W5 |
| W2 | **10 served, and the board's real ceiling**: image G, `max_connections = 16` with image B's ensemble (§0 has the exact edit), the same file — levels 4..18. Twin prediction: **clean through 12 at the board's harsher calibration, through 18 at its gentler one** — the sweep's 4-18 spans exactly that bracket. Image G carries 18,592 B more `.bss` than F, so its wall is if anything a little lower than a right-sized image's | **RUN 2026-09-23 — FAILED below 10**: first failure N = 6, the static page (1,025 B); JSON failures from N = 10. `BENCH_SITTING_2026-09-23_HANDOVER.md` §10.4/10.6 |
| W3 | `/status` wall-clock with 29 pieces instead of 11: `test_end_to_end_timing.py` on image F against the sitting's own figures. F.1's +53% was per *character*; this is per ~250 B | OPEN |
| W4 | The whole bench tier on image F, default flags — the new file included | OPEN — held back by §0's stop rule; now §00.3 step 4 |
| W5 | **The static-file fix on silicon** (image F′, the tip): the same file, now probing `route:/` and checking every body against its `Content-Length`. Twin, `dev`'s own site: `route:/` needs 320 B (1,536 B before), sweep 4/6/8/10 clean with every body complete. `REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md` §00 | OPEN |
| W6 | Per-boot combined load on image F′ at N = 2/4/5/6/7/8 (5 and 6 repeated), bodies checked — the sitting's §10.6 definition. Twin: all complete, zero failures | OPEN |

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
