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

**Where things stand (2026-09-19, after the evening sitting).** §1A (measure A) **closed** — §7D.
§1B (measure B) **closed** — §7F and **§7H**: P1, P2, P3, P4 and P5 all confirmed on silicon, B7's
replacement checks pass with 5.5x margin, and the bench tier is fully clean for the first time.
§1C's C1 is **closed** by the same runs; C2/C3/C4 remain. One §7D claim was **overturned** — see
§2A F7. §1D's body-cap mirrors have since run: **W1-W4 pass**, W5 failed for a reason that was not
the body cap and has been **rewritten** (§2A F10). What is still owed is **W5's first run in its
rewritten form**, D1-gated work, R-rows independent of measure B, and F1's SSID script.

**The next sitting's runnable form is `REAL_HARDWARE_HANDOVER_POST_MERGE_BENCH_RUN.md`** — one full
bench-tier run at default flags (**no** `--allow-persistence-writes`, **no** soak), which is the
owner's instruction of 2026-09-19 and covers every §1D row including W5's rewrite.
`REAL_HARDWARE_HANDOVER_WEBSERVER_BODY_CAP.md` stays open alongside it on W5 alone, and goes when
W5 comes back green. `REAL_HARDWARE_HANDOVER_MEASURE_B.md` is **deleted** — §7H migrated every
result it owed, which is that file's own stated condition for going.

**What changed since the 2026-09-18 bench sitting, host-side, and why it matters to the next one.**
Two of §7F's own readings turned out not to mean what they said, both found without hardware and
both fixed in the instrument rather than argued around:

- **The 49,152 B row is an instrument artefact** (§7F.8). The largest-block probe can pin its own
  buffer and then return the first size that succeeded, always `_PROBE_MAX >> k`. Both device
  scripts now print `retained=` on every `HEAP` line and reread automatically while it is non-zero.
  The same artefact could have produced a **false tripwire FAIL** on a good image; it never did, but
  it was reachable, and that guard is now in place.
- **`after_starter_list` is a run-phase reading, not a starter-list one** (§7F.9). It is taken a few
  seconds after the list ends, and the twin loses most of measure B's gain within ~2 s of the run
  phase starting. `heap_layout_after_full_boot_sequence.py` now also reports **`after_starter_loop_end`**,
  detected by counting starters rather than by waiting a guessed interval — that is the reading P2
  turns on. **It has since been taken** (§7H.2): A-only 5%, A + B 80%.

Both measure-B rows are now **DONE** — the 2026-09-19 sitting ran them and P2 is settled. The
paragraph above is kept only because it explains why the two readings differ.

**And the tripwire itself changed (owner, 2026-09-19).** The 80,000 B floor is retired — it was
never the owner's, and it demanded a third of physical memory contiguously free. What
`test_real_gc_heap_headroom_survives_a_full_system_build` now asserts is three things, each derived
from §7A.9's *measured* worst reachable allocation (16,384 B) rather than from a board reading:
survivor volume (`used <= 100,000 B`), survivor **placement** — now in two forms, the owner's
"zero survivors in the long heap" asked as a **delta** (the boot must place none in the top
16,384 B, independent of what the suite left on the heap) and the absolute form (nothing at all up
there, whoever put it there) — and contiguity (`>= 32,768 B`, twice the worst case).
Both device scripts also print `micropython.mem_info(1)`'s block map now, which gives the exact
largest free run without allocating anything, and the host side cross-checks it against the probe.
Full derivation: MEASUREMENTS §7G. **The placement check has since run on silicon and passes with
5.5x margin** (§7H.4) — row B7, closed on its first run.

**If there is time for one sitting only, in this order (revised 2026-09-19, after §7H).** Measure A
and B are both settled on silicon, so the old A-only arm is no longer needed and **one image
suffices** — this branch's own tip.

1. **P5 first, before anything writes**: read `GET /status`'s `errcount` and record it verbatim.
   CLAUDE.md's rule, and it has cost real evidence twice now (§2A F9).
2. **One full bench-tier run at default flags** — `scripts/run_bench_hardware_suite.sh`, no
   arguments. Owner's instruction, 2026-09-19. It covers the flash tier too, excludes the soak
   unconditionally, and leaves every wear gate off. **This alone is the sitting's mandate**;
   `REAL_HARDWARE_HANDOVER_POST_MERGE_BENCH_RUN.md` is its runnable form and says how to read W5.
3. **F1's SSID script** (`wifi_service_reconnect_repro.py`), fixed but never run since. Read §2A F1
   in full first: this is the script that stranded the bench, and the fix is structural.
4. **R9 / R13 / R15** — independent of everything above, and none of them needs D1.

Everything D1-gated (R1, R4, R5, R8's reboot arm, R12, S3) stays **blocked** this sitting by that
same instruction — the intended outcome, not an omission.

Everything else in this file can wait for another sitting.

---

## 0. Decide before the run

These change what gets run, so settle them first.

**Answered for the 2026-09-18 session (owner gave the go-ahead but not the decisions, so the
session took them and recorded them): D1 no** — no `--allow-persistence-writes`, per CLAUDE.md's
wear rule; every D1-blocked row below is still owed. **D2 no** — sweep left gated. **D3** `dev`
from this branch's tip. **D4 yes** — the pair was run, see §1A.

| # | Decision | Why it matters | Status |
| --- | --- | --- | --- |
| D1 | **Does the bench spend flash/NVM writes this round?** A default run deselects 13 of the bench tier's 73 tests and 9 of the flash tier's 51; `--allow-persistence-writes` runs them and spends real cycles. `--allow-scd30-extra-write` is AND-gated on top for one further SCD30 NVM write. | Several rows below are *only* reachable with the flag — R1 and R4 in particular. Deselection is invisible to the pass/fail check, so this must be a knowing choice (CLAUDE.md's wear rule). | OPEN |
| D2 | **Is the NeoPixel-aimed-at-the-ISL29125 rig set up?** The gating question is **settled** — `main`'s `@pytest.mark.neopixel_sweep` + `--allow-neopixel-sweep` has been adopted here (2026-09-18), so `test_isl29125_survives_recombined_realistic_lighting_scenarios` (~8.5 min) and `test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration` (~99 s) now skip by default instead of failing on a bench without the rig. What remains is the physical question: decide whether to pass the flag this round. | The 2026-09-17 bench session ran both ungated and they passed after the `_park()` fix, which suggests the rig *is* in place — confirm rather than assume, and record the geometry via the manual tier's `isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry` (M1) so the next session does not have to. Opting in costs ~10 min. | OPEN |
| D3 | **Which firmware image.** Every row below assumes a `dev` build from this branch's own tip via `scripts/build_firmware.py dev`. | CLAUDE.md's hard rule: a `wozi` build flashed onto the dev bench "tests nothing at all" and has produced false bugs before. | OPEN |
| D4 | **Is §1A's before/after pair being run this sitting?** It needs **two** `dev` images — the merge base and this branch's tip — so two build+flash cycles, in that order. | Only relevant if A0/A1 are in scope. Every other row needs one image (the tip). Reusing an older `largest_block` reading from a previous session as the "before" arm is not a before/after: the board's provisioning, the base branch and the firmware have all moved since 2026-09-17. | OPEN |

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
at all" and has produced false bugs). For R12 specifically the board needs a *clean filesystem* -
a persisted config wins over the new per-device hostname, so a stale `SensorNode` there would
prove nothing.

**Step 4 - the flash tier.** `scripts/run_flash_hardware_suite.sh`
Read the verdict's **deselected** count, not just the word "clean": the wear gates deselect rather
than skip, so "everything that ran, passed" is not "everything ran". Expect R10's two fixed device
scripts and R14's watchdog banner to be exercised here - if R14 fails, read *which* case before
concluding anything (its row says how to tell the two apart).

**Step 5 - the bench tier.** `scripts/run_bench_hardware_suite.sh`
A strict superset of step 4; same deselected-count caveat. R9 and R11 ride along here.

**Step 6 - the wear-gated re-run, only if D1 said yes.**
`scripts/run_flash_hardware_suite.sh --allow-persistence-writes` and the same for the bench script.
This is what makes R1, R4, R5 and R8's reboot arm reachable at all; without it they are deselected
and answered by nothing. Add `--allow-scd30-extra-write` only if a second SCD30 NVM write is
genuinely wanted on top.

**Step 7 - the NeoPixel light programs, only if D2 said yes.**
`scripts/run_manual_hardware_tests.sh --only isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry`
first (it is what records the rig geometry), then
`scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep`. ~10 minutes combined.

**Step 8 - the targeted investigations** in section 2, in this order: R1 (start with its no-code
`RangeAuto=false` bisection, and restore `RangeAuto` afterwards), R2's reader-count curve at 0, 1,
2, 3, 4 and 6 readers, then R3, R6/R7, R13 and R15. R15 needs no fault injection - whatever the
board has already logged is its subject, so it pairs naturally with step 1's recording.

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
| S1 | `scripts/run_flash_hardware_suite.sh` | **DONE 2026-09-18, on BOTH arms.** Tip: `3 failed, 33 passed, 3 skipped, 12 deselected` (864.67 s). Before arm: `2 failed, 34 passed, 3 skipped, 12 deselected` (844.84 s). Failure attribution in §1A-R. | DONE |
| S2 | `scripts/run_bench_hardware_suite.sh` | **DONE 2026-09-19 (A+B): `93 passed, 4 skipped, 27 deselected` — ZERO failures**, the first fully clean bench run on any image. Closes T.2's bench tier, C1's tier-4 run and R9. §7H.6 | DONE |
| S3 | The same two with `--allow-persistence-writes` | Only if D1 says yes. This is what makes R1/R4 reachable at all. | BLOCKED on D1 |
| S3b | `scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep` | Only if D2 says the rig is in place. Runs the two long ISL29125 light programs (~10 min combined); they skip otherwise. | BLOCKED on D2 |
| M1 | `scripts/run_manual_hardware_tests.sh --only isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry` | Interactive. Repeatability on an unchanged scene, continuity across the range switch, **and** setting up and writing down the rig geometry S3b depends on. Worth doing before S3b, not after. | OPEN |
| S4 | Long memory soak (`long_soak` tier), never bundled into S1/S2 | A real long-duration memory-soak run has still never been executed (README.md's own "Further reading" note, carried from the retired hardware-planning docs). Pick the tier deliberately: short=60 s / mid=600 s / long=6 h. | OPEN |

**Before any of this**: read `GET /status`'s `errcount` and record it. CLAUDE.md's rule — the
FRAM-persisted per-module logs are the one piece of diagnostic evidence a reboot does not erase, and
`ResetErrors` destroys them irreversibly. Also check what has already been run against the board: an
isolated-driver device script builds its own `AsyFramManager` over the same chip and can leave a
plausible-looking fabricated entry behind (`tests_hardware/README.md` has the mechanism).

---

## 1A. Measure A — the FRAM path restructure (PR #105, branch `claude/heap-fragmentation-remediation`)

Added 2026-09-18: the owner reports the branch is on the bench in another session. Until then this
work was §5-excluded; that exclusion is lifted for the rows below and nothing else on PR #105.

**All rows below were run on 2026-09-18** against a real `dev` bench board with the owner's
go-ahead. Results are in each row; the analysis is §1A-R and `HEAP_FRAGMENTATION_MEASUREMENTS.md`
§7D. Three rows produced findings rather than clean results — see §2A.

Two separable questions, and they want different runs: **does the restructured FRAM path still do
everything the old one did on real silicon** (A2-A5, A8), and **what did it actually buy** (A0-A1,
A6-A7). The functional rows can run on their own; the gain rows only mean anything as a matched
before/after pair on the same board in the same sitting.

**What changed, so a failure can be read.** `SPIDevice` gained a synchronous session
(`session_begin()`/`session_end()` + `write_sync()`/`readinto_sync()`/`write_readinto_sync()`) with
a blocking `time.sleep_us(2)` settle in place of two awaited 1 ms settles; `FRAM_SPI` drives the
chip through plain functions over it and now **holds the bus for a whole block operation** rather
than per byte-level command; the chunk layer allocates its scratch buffers once in `__init__`
instead of per call. The wire protocol is asserted byte-identical by
`tests/test_asy_fram_wire_trace.py`'s goldens, so **any** real-chip behaviour change is a finding,
not an expected consequence.

| # | Run | Notes | Status |
| --- | --- | --- | --- |
| A0 | **The "before" heap reading.** | **DONE 2026-09-18.** Standalone: 108,528-108,768 free / 85,696-86,736 largest, 5/5 **PASS** — the arm did NOT fail as predicted. In-suite: free 108,736, **largest 20,592** — reproduces 2026-09-17 to the byte. See §1A-R below. | DONE |
| A1 | **The "after" heap reading.** | **DONE 2026-09-18.** Standalone: 104,864-105,008 free / 94,704-95,104 largest, 5/5 PASS. In-suite: free 105,216, **largest 28,864**. | DONE |
| A2 | **FRAM functionality, flash tier** | **DONE 2026-09-18: 9 passed** in 108.9 s. The restructure kept every safety measure. | DONE |
| A3 | **FRAM bus hazards, flash tier** | **DONE 2026-09-18: 2 passed, 2 FAILED.** `test_fram_cs_pin_hijack_fault_injection_and_recovery` and `test_fram_hard_reset_race_during_write_and_recovery` fail on the tip and **pass on the before arm** — attributed to A. They are broken *tests*, not a broken driver (§1A-R). | DONE (finding) |
| A4 | **Bus hazards under real API load, bench tier** | **DONE 2026-09-18: 3 passed, 3 deselected.** Note the row's own count was wrong: **three** of the six carry `@pytest.mark.persistence_write` (`...ntp_transient_outage_and_retry`, `...isl29125_config_write...`, `...bmp3xx_config_write...`), not two. | DONE (4th/5th/6th still owed under D1) |
| A5 | **The second-SPI-device question is NOT testable here.** | **RECORDED 2026-09-18, not run.** Structurally untestable: no `devices/*.toml` wires a second SPI device. A6 supplies the closest evidence — a second device would now wait **21.3 ms**, not the ~600 us this row assumed. | DONE (recorded) |
| A6 | **Hold time, measured on real wire** | **DONE 2026-09-18.** `write_5cs=2849us read_1cs=772us block_operation=21269us`. Both ~28-35x the estimates in this row. (a) non-yielding stretch **2,849 us**; (b) bus hold **21,269 us**. ~2,550 us of (a) is interpreter overhead, not wire time — which inverts this row's and R7's stated premise. | DONE |
| A7 | **Boot cost, for the record only** | **DONE 2026-09-18 (AFTER arm):** 912/910/957/926/919 ms, **median 919 ms**. Far clear of the 8,388 ms cap. | DONE |
| A8 | **Re-read `GET /status`'s `errcount`** | **DONE 2026-09-18: clean.** No errno 90/91/92/93/99/100, no wrnno 81/82/84, `FRAM` counter still 0 across A2/A3/A4 and two full flash suites. (Counters for NTP/SYSTEM/UART went to 0 — the `fram_*.py` scripts overwrote production's chunks, the documented hazard observed live.) | DONE |
| A9 | R10's `fram_write_protect_roundtrip.py` | **DONE via R10: PASS.** A's `set_write_protected()` self-acquiring-the-bus path confirmed on silicon. | DONE |

### §1A-R — what the pair actually showed

Full write-up is **`HEAP_FRAGMENTATION_MEASUREMENTS.md` §7D** (the first [HW] section on this
branch). The three things that matter here:

1. **The defect is position-dependent and a cold build cannot see it.** Same firmware, same board,
   same sitting: standalone `largest_block=95,104`, in-suite `28,864`, with `free`/`alloc`
   identical to 0.2 %. `Board.run_isolated()` interrupts the already-running firmware rather than
   resetting, so the script builds inside `main.py`'s aged heap. **Every standalone heap reading
   measures the wrong thing** — including A0/A1's own five-run pairs.
2. **A buys ~40 % of the in-suite contiguity** (20,592 -> 28,864 B), reproducibly (the bench tier
   returned 28,864 again, byte-identical). It does not clear the tripwire and was never expected
   to. This contradicts §7B.1/§7C.2's "no layout gain" — the twin was measuring the cold
   configuration, in which the defect does not exist.
3. **A fixed one real failure and broke two tests.**
   `test_the_link_keeps_transferring_while_every_other_subsystem_is_busy` fails on the before arm
   (`heap grew 3584 bytes ... under parallel load`) and passes on the tip. The two A3 injectors
   fail on the tip because `cs_yanker()` needs an await point inside the command envelope, and A
   replaced that awaited settle with a blocking `time.sleep_us(2)`. They need a new injection
   technique (timer IRQ, or the second core); they currently cover nothing.

**A6's script.** Not committed as a test (T.4 decides whether it becomes one) — save it and run it
with `scripts/mpremote_connect.sh exec "import machine; machine.WDT(timeout=8000)"` then
`scripts/mpremote_connect.sh run /tmp/fram_hold_time.py`, mirroring what `Board.run_isolated()`
does. Unlike every other FRAM device script it writes at the **top** of the address space and never
calls `get_chunk()`, so it does not overwrite production's error logs. **Already executed against
the digital twin** (2026-09-18), so it reaches both `print()` lines rather than dying on a renamed
method at first contact — the twin's own numbers are meaningless (its fake chip answers in memory
with zero wire time, which is precisely why this row exists):

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

**How to read A0/A1 — the prediction, written down before the run so a surprise is recognisable.**
The twin's own perturbation ensemble was run on the restructured code (settrace-free frozen binary,
`gc.threshold(-1)`, calibrated heap, 15 + 6 perturbations, `HEAP_FRAGMENTATION_MEASUREMENTS.md`
§7A.8's protocol):

- After `build_system()`: A gives **31,328 B largest in all 15 runs**, ratio 12.4-12.5%. Base swung
  **30,752-60,800 B**, 11.9-23.4%, median 14.3%. A removed the *variance*, not the fragmentation.
- After the whole boot sequence: A **7.3-7.4%** against base's **8.1-8.5%** — marginally worse.
- A **retains 7,232 B more** than base, measured at the construction seam. 3,200 B of that is the 20
  hoisted per-chunk buffers (20 x 160 B, confirmed directly by nulling them and collecting) and
  1,024 B is import residue from the new methods.

So the honest expectation on silicon is **`free` slightly lower, `largest_block` roughly unchanged,
and the 80,000 B tripwire still failing** — A is a churn/allocation-count fix (9.0x per logger
`setup()`), and §7B.1 predicted no layout gain from it alone. **A large `largest_block` improvement
would contradict the twin and must be investigated before it is believed**, not reported as success;
the likeliest explanations would be a different `gc.threshold()` in play or an arm built from the
wrong tree, both of which the twin cannot reproduce.

---

## 1B. Measure B — the boot-confined placement reset (PR #105, same branch)

**CLOSED 2026-09-19 — every row below is DONE.** The handover that drove it
(`REAL_HARDWARE_HANDOVER_MEASURE_B.md`) has been **deleted**, its results migrated into
`HEAP_FRAGMENTATION_MEASUREMENTS.md` §7F and §7H. This section is kept only until its rows are
migrated too; it is not work.

Measure B is built, tested and green in the twin (`HEAP_FRAGMENTATION_MEASUREMENTS.md` §7E: A + B
takes largest-block-over-free from 14.2 % to 86.3 % after `build_system()` and from 8.4 % to 88.7 %
over the whole boot sequence, both [TWIN]). **None of it has run on silicon**, so §7E is the
unconfirmed half of this branch exactly as §7B.1 was before §7D refuted it.

| # | Run | Notes | Status |
| --- | --- | --- | --- |
| B1 | **The matched in-suite pair**, A-only against A + B. | **DONE 2026-09-19 — the owed figure is in.** BEFORE `largest_block=27,968`; AFTER **91,008** (`retained=0` both). 3.25x. §7H.1 | DONE |
| B2 | **The whole boot sequence, not just `build_system()`.** `device_scripts/heap_layout_after_full_boot_sequence.py`. | **SUPERSEDED by B6**, run 2026-09-19 with the fixed instrument. §7H.2 | DONE |
| B3 | **Boot cost with the collects in.** | **DONE 2026-09-18 — P4 CONFIRMED.** `build_system_ms` 943 → **1,402**, i.e. ~455 ms for B's 11 batch collects (~41 ms each). Under the ~2,000 ms falsifier and the 8,388 ms cap; no `WDT_RESET`. First measured RP2040 collect cost — ~85x the twin's 300-490 us, as §7A.7 predicted would not transfer | DONE |
| B4 | **The threshold-first reading** — the firmware's own boot path under its own `gc.threshold(32768)` from the start. | **DONE 2026-09-19, and it is the sitting's biggest secondary finding.** AFTER threshold-first holds **74,896 / 80%** through the 4 s settle where the reactive default falls to **11,952 / 12%** — the threshold is what carries B's gain into the run phase. Also faster (build_system 1,033 vs 1,404 ms). One reading per condition; repeat before concluding. §7H.3 | DONE |
| B6 | **Rerun B2's script on both arms with the 2026-09-19 instrument.** Two invocations of one script, one per arm, each immediately after that arm's suite run so the heap is aged. Same command as the handover §4.3. | **DONE 2026-09-19 — P2 CONFIRMED.** At `after_starter_loop_end`: A-only **5,024 / 5%**, A+B **75,104 / 80%**. Twin predicted 5-11% vs 20-59%; A+B beat its upper bound. F6's run-phase decay also confirmed (A+B 80% -> 12% over the settle). §7H.2 | DONE |
| B7 | **The replaced tripwire's first run** (owner retired the 80,000 B floor 2026-09-19). No new invocation — it is what S1 already runs. | **DONE 2026-09-19 — PASSES, with margin, first silicon run.** `used=89,040` (<=100,000); `largest_free_run=90,688` (>=32,768, 2.77x); **`free_above_top_survivor=90,688` (>=16,384, 5.53x)**; probe vs map **delta 0**. Deciles `[1163,1177,1177,1079,806,163,0,0,0,0]` — **the top four deciles hold zero allocated blocks**. Full suite 36 passed, 0 failed. §7H.4 | DONE |
| B5 | **F1/F2's fixes on silicon** — the two FRAM fault injectors and the SSID script. | **F2 DONE** (both injectors pass on both arms, re-confirmed 2026-09-19). **F1's SSID script still not run** — B-D3; it is now structurally safe (persists diverted to a scratch config) but unrun on silicon | F2 DONE / F1 OPEN |

---

## 1C. Added features the measure-B handover does not cover

Changes that landed with `b0f755c`/`debff43`'s merge and have real-hardware implications of their
own. None is part of measure A or B, so neither §1A's nor §1B's runs speak to them.

| # | Item | Notes | Status |
| --- | --- | --- | --- |
| C1 | **The I2C shared scratch buffer is a bus-facing change, so CLAUDE.md's four-tier rule applies.** `asy_i2c_driver.py` gained one long-lived 32-byte `bytearray` **per bus**, reused by every register read; `_read_into_scratch()` returns a `memoryview` over it valid **only until the next read on that bus**. The safety argument is that every method fills and decodes it with no `await` in between and that no `Timer`/`Pin.irq` callback touches I2C. | Verified structurally (`_read_into_scratch` is synchronous and its callers decode before returning), but it has never had a real concurrent hardware run, and the buffer is shared **across every device on the bus** — the cross-device interleaving hazard the standing rule names. `dev` has four I2C devices across two buses, so it is reachable here. **Tier 3**: `test_bus_concurrency.py` in full, not just the FRAM subset. **Tier 4**: `test_bus_concurrency_under_api_load.py` — §1A ran these clean but **before** this change landed. A torn read would surface as an out-of-range sensor value, not an exception, so read the values, not just the exit code. **DONE 2026-09-19**: tier 3 green across two full flash suites, tier 4 green in the bench tier (93 passed, 0 failed). §7H.6 | DONE 2026-09-19 |
| C2 | **The oversized-read fallback** (`nbytes > 32` allocates instead of sharing) is never taken on this hardware — BMP3XX's 21-byte calibration block is the largest read and stays under the threshold. | Record as structurally unexercised on `dev`, the same treatment A5 got for the second-SPI-device question. | OPEN (record) |
| C3 | **`asy_wifi_service._with_default()`** substitutes a build-time per-device default into the one-field hostname/SSID schema, dropping a value outside the field's own bounds rather than installing it — an unsatisfiable default makes `ConfigManager` answer `None` to every read, which would cost a device its networking config entirely. | The failure mode is "device boots with no networking config", so one look on the one board that can show it: `GET /networking`'s `Hostname` against `devices/dev.toml` after a clean boot. | OPEN |
| C4 | **`asy_uart_comm.py` reclassified which warning takes the episode's single persisted slot** — `_WRN_DRAIN_BOUND` (11) now wins over `_WRN_RESYNC` (10) when the drain bound was hit, because 11 separates a babbling peer from ordinary line noise. The boot drain persists nothing. | **Receiver-side only, no emitted bytes change**, so it is the preferred class of protocol change and a mixed-version pair still works — but it still needs a `UART_C_PORT_CHANGELOG.md` entry, which should be confirmed. `dev`'s two `uart_link` instances make it observable: check `errcount`'s `UART_init`/`UART_resp` history after a run that forces a resync. | OPEN |

---

## 1D. The request-body cap (Part I.6) — new, never run on silicon

`src/asy_webserver_service.py`'s `max_content_length` moved 4096 -> **2048** and `max_body_length`
is now **bound to it** instead of keeping microdot's own 16 KB default, closing the band where a
body was buffered in full and only then answered 413 (SPECIFICATION.md Part I.6). Six mock tests
pin it at `tests/test_asy_webserver_service.py` §F.2b; **five bench-tier mirrors were added
2026-09-19 and have never run against real hardware or real WiFi.**

**What the wire can and cannot show.** The mock tier proves "the body is never READ" directly, by
counting the `readexactly()` sizes the server asks for. That is not observable over a socket: both
the old and the new firmware answer 413, just at different sizes. So the bench mirrors prove the
**cap value** moved, not the binding — W2 is the row that can tell the two firmwares apart, and
nothing here should be reported as having confirmed the binding itself.

| # | Run | Notes | Status |
| --- | --- | --- | --- |
| W1 | `test_put_body_cap_boundary_is_exact_over_the_normal_network` | **DONE 2026-09-19: PASS.** 2047 -> 200, 2048 -> 200, 2049 -> 413. Microdot's `<=` honoured, no off-by-one | DONE |
| W2 | `test_put_the_band_that_used_to_be_accepted_is_now_rejected_over_the_normal_network` | **DONE 2026-09-19: PASS.** 3072 and 4096 both answer 413. The image is confirmed right and the cap value has moved — this is the row that tells this firmware from the previous one | DONE |
| W3 | `test_the_largest_body_any_schema_can_produce_still_fits_under_the_cap` | **DONE 2026-09-19: PASS.** The schema maximum still fits, and the 1025-char `NTP_Host` is answered `Invalid` with nothing written. **The figure it sends was corrected 2026-09-19 from 1132 to 1312 B** — the old one understated the numeric fields; `tests_scripts/test_request_body_cap_headroom.py` now derives it rather than quoting it. Re-run is cheap and worth having on the corrected size. | DONE (size corrected) |
| W4 | `test_put_a_mixed_stream_of_body_sizes_is_handled_each_on_its_own_merits` | **DONE 2026-09-19: PASS.** Interleaved sizes each answered on their own merits; no 413 left a following request mis-parsed | DONE |
| W5 | `test_concurrent_mixed_body_sizes_never_destabilise_the_real_server` | **FAILS 2026-09-19, reproducibly (5/5) — but NOT for the reason the handover predicted, and its prescribed fix would be wrong.** The handover said a red W5 showing exception strings *only on the oversized arm* should be relaxed on that arm. **Half the resets are on bodies well under the cap** (64, 512, 900, 2048 B). Controls settle it: 24 concurrent PUTs with *every* body under the cap, and again with *all* bodies at 64 B, reset at the same rate — so this is **concurrency against `max_connections = 4`, not the body cap**. Rate vs concurrency (tiny bodies): 2 -> 0%, 4 -> 25%, 6 -> 16%, 8 -> 12%, 12 -> 33%, 16 -> 25%, 24 -> 25% — resets begin **at** the ceiling, not beyond it. Server stayed responsive, no reboot, `WEBSERVER` log empty. **Rewritten 2026-09-19** around the invariant the cap actually owns, once F10's raw data showed **zero wrong answers across 96 requests**: a ceiling refusal is now counted rather than failed, while a wrong status, a non-ceiling exception, too few answers, or a missing verdict all still fail it. Replays PASS against all four recorded runs. Renamed to `test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status`. **Re-run to confirm on silicon** — the only §1D row not yet green there. See §2A F10 | REWRITTEN — re-run |

**Zero wear, deliberately.** Every one pads an **unknown** sensor key, which `PUT /sensors` ignores
silently — so nothing validates, nothing persists and no `CFGMGR_*` logger fires. None of these is
`@pytest.mark.persistence_write`-marked and none should become so; if one ever needs an *accepted*
config write to make its point, that is the moment to add the marker, not before.

---

## 2. Targeted investigations

**Owner confirmation, 2026-09-18**: R1 (item 30), R2 (item 32's reader-count curve), R3 (item 29's
spurious `W4`) and R5 (WP5's BMP3XX arm) are all confirmed as owed for the next go-ahead run - they
were put to the owner as open decisions and the answer was "record for the real-hardware run", not
"drop". Nothing about them is waiting on a further decision; they are waiting on bench time.

| # | Investigation | Source | Status |
| --- | --- | --- | --- |
| R1 | **BACKLOG item 30 — the ISL29125 HTTP connection reset under concurrent API load.** Owner's direction is to root-cause and resolve, not re-measure. Shape is established: needs **both** a config-persisting PUT **and** ≥2 concurrent readers (PUT alone 0/10, PUT+1 reader 0/6, PUT+2 readers **6/18**, plain GET+2 readers 0/6); failures land at 21–72 ms against 0.5–2.2 s for successes, and `WEBSERVER`'s counter stays 0 so FRAM forensics will not help. **Do the no-code bisection first**: `PUT /sensors {"ISL29125": {"RangeAuto": false}}` drops `_switch_range()` from the three-step push, leaving only `configure()` + `_reapply_persist()`. Rate falls → the threshold re-arm is implicated; unchanged → it is the first two. Restore `RangeAuto` afterwards. | BACKLOG 30 | BLOCKED on D1 |
| R2 | **BACKLOG item 32 — the `ResetErrors` reader-count curve.** Elapsed time at **0, 1, 2, 3, 4, 6** concurrent `GET /status` readers. Two points exist (6.32 s idle, 11.58 s at 3 readers = 77 % of the 15 s server cap); two points cannot say whether the curve flattens. | BACKLOG 32 | OPEN |
| R3 | **BACKLOG item 29 — the spurious `W4`.** A real outage logged `W4` ("WLAN wrong password") twice alongside the expected `W5`, on a network whose password never changed. One look at whether CYW43 genuinely reports that mid-transition (making `_assert_wifi_log_has_only_benign_ap_not_found_warning()` wrong) or whether `_poll_sta_connect_status()` mis-maps it. Do not chase far. | BACKLOG 29 | OPEN |
| R4 | **`ResetErrors` completeness under contention.** Pre-populate the FRAM error logs on several modules, then sweep under R2's reader load and confirm every counter reads back 0. All previous correctness checks were made at idle or with the logs already empty; a silently skipped chunk is invisible today because the call still answers `200`. | CLAUDE.md's FRAM `errcount` rule | BLOCKED on D1 |
| R5 | **BACKLOG "Refactor targets" — the WP5 deferred-config-write re-confirmation.** The BMP3XX arm passed on 2026-09-17 on WP5 firmware; make that durable rather than one run. The ISL29125 arm is R1, not this row. | BACKLOG, first entry | BLOCKED on D1 |
| R6 | **The `CFGMGR_SYSTEM` setup-order fix's unexplained +0.90 s of boot latency.** Boot latency itself is measured and needs no re-run: pre-WP **7.74 s** → WP1+WP2 **9.80 s** → WP1–WP8 **9.76 s** → +`CFGMGR_SYSTEM` fix **10.66 s** (medians of 5, spread ±0.06 s; 23 reboots, no `WDT_RESET`). Those figures were taken by PR #102, which the owner closed unmerged on 2026-09-18 — they are migrated into `SPECIFICATION.md` Part A.7's boot-latency note, so nothing is lost with the PR. What remains open is only the sub-question: **+0.90 s** is far more than one extra FRAM-backed logger's `setup()` should cost, and is unexplained. Worth understanding before the same reorder is assumed free elsewhere; it does not threaten the watchdog budget, so it is not a reason to revert. | SPECIFICATION.md Part A.7; BACKLOG 33 | OPEN |
| R8 | **Two newly adopted bench tests, never yet run on silicon** (ported from `main` 2026-09-18, see BACKLOG item 33). `test_isl29125_calibrate_command_push_over_real_rest` pins that a calibration run never moves the *applied* `GainRatio` and that `GainMeas` reaches `/measurements`; `test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value` pins that ratio across a real hard reset. The second is `@pytest.mark.persistence_write`-marked here (it owns two persisting PUTs) where `main` left it unmarked, so it needs D1. Both were written against `main`'s API shape and adapted to this branch's nested `PUT /sensors {"ISL29125": {...}}` body — expect the adaptation to be where a first run goes wrong, if anywhere. | BACKLOG 33 | calibrate: OPEN / reboot: BLOCKED on D1 |
| R9 | **The ISL29125 shadow-divergence fix, and the `Overrange` field that replaced `W12`, have never run on silicon.** `configure()`'s device-session lock was widened to span the whole validate-mutate-write(-rollback) sequence (WP-era fix, unit-tested by `test_configure_never_exposes_the_shadow_ahead_of_a_write_still_in_flight`), but the false `wrnno=11` it fixes only ever manifested under real concurrent bench load - so only real load re-confirms it. Same run covers the `Overrange` half: `device_scripts/isl29125_mechanism_envelope.py` now reads the live field instead of the retired `W12` log entry. | BACKLOG, "Open questions" first entry | OPEN |
| R10 | **Two `tests_hardware/device_scripts/` bugs are fixed in source but have never been executed since.** **DONE 2026-09-18, split result.** `fram_write_protect_roundtrip.py`: **PASS** — the keyword-only fix is good, and it exercised A's self-acquiring-the-bus path (A9). `wifi_service_reconnect_repro.py`: the `task.data` fix is confirmed (it now runs deep into the real CYW43 reconnect, reaching `EPERM`, where it used to die at first contact) but the script **does not complete** — the board drops the USB CDC mid-run and mpremote ends in `OSError: [Errno 5]`. It likely needs `run_isolated_expect_reset()`. **It also left the bench stranded — see §2A.** | DONE (finding) |
| R7 | **`SPECIFICATION.md` Part A.7's FRAM setup-cost figures are twin-only.** `digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time, so every number there excludes the real per-transaction cost. Re-measure on silicon. Largely the same instrumentation as R6. **Premise corrected by A6 (2026-09-18):** the omitted term is *not* mainly SPI wire time — at 1 MHz six transactions are ~300 us of the measured 2,849 us, so ~90 % is MicroPython interpreter / `machine.SPI` call overhead. Frame the re-measurement that way. | SPECIFICATION.md Part A.7 | OPEN |

| R11 | **Every I2C register read now goes through `readfrom_mem_into()` into one shared per-bus scratch buffer**, instead of allocating a fresh `bytes` per read (BACKLOG, 2026-09-18). Verified against the pinned 1.29.0 source (same `read_mem()` path, same `OSError` semantics) and green at the mock and twin tiers, but it changes the read path of *every* I2C driver, so it deserves one real-silicon confirmation: run S1/S2 and check that SCD30/SGP40/BMP3XX/ISL29125 all still read plausible values, and specifically that BMP3XX's 21-byte calibration block (the largest read, once per setup) still yields correct compensated pressure/temperature. | **DONE 2026-09-19.** Tier 3 and tier 4 green across two full flash suites and the bench tier; `test_isl29125_same_device_read_write_concurrency` and the deinit/singleton check pass. §7H.6 | DONE |
| R12 | **Each device now boots under its own `[device].hostname`** (`SensorStationDev` on the bench) rather than the shared `SensorNode` (BACKLOG, 2026-09-18). One-line check on a freshly flashed board with **no pre-existing config file**: `GET /status` reports the per-device hostname, and the unit is reachable under it on the bench LAN. Note the persisted value wins on a board that already has a config, so a stale `SensorNode` there is correct behaviour, not a failure - flash a clean filesystem or delete the config first, or the check proves nothing. | **NOT CHECKABLE on this board as it stands**, and that is R12's own documented case: `GET /networking` reports `SensorNode` while `devices/dev.toml` says `SensorStationDev`, because the persisted `config_WIFI.cfg` wins. Confirming it needs a board with no config file — a deliberate wipe, i.e. a flash write, outside D1. §7H.7 | BLOCKED on D1 |
| R13 | **UART `wrnno` 11 now takes the fault episode's one persisted slot when the drain hits its bound** (BACKLOG item 23, 2026-09-18). The bench exerciser drives the real crossover jumper, so a deliberately babbling peer is reproducible there in a way no mock is: confirm `GET /status` shows `W11` rather than `W10` for `UART_init`/`UART_resp` after one, and that a *boot* drain against the same babbling peer persists nothing at all. Low urgency - the mock tier covers the logic; this confirms it against a real UART's own timing. | BACKLOG item 23 | OPEN |
| R14 | **`test_watchdog_starvation`'s new banner assertion has never run on silicon, and it is the one host-side fix that can turn a previously green test red** (2026-09-18). It now requires the device script's own `"WDT armed, starving now"` banner in the failure text, so a transient `"may be in use by another program"` at connect can no longer clear the `< 10.0 s` bound and pass as a watchdog reset. If it fails on the next S1, read *which* case: a genuinely absent banner is the fix working (a real connect failure that used to pass silently), while a banner that is merely not captured means mpremote dropped buffered device stdout as the link died - and then the marker is the wrong instrument and the reset needs proving another way. The other four fixes from the same host-side review are settled: `_usb_reset_device()`'s by-id path was confirmed on the bench host, the rest are source-grounded. | **DONE 2026-09-19: PASS** on silicon, first run of the banner assertion. §7H.6 | DONE |
| R16 | **`SPECIFICATION.md` I.3's "smallest largest-allocatable-contiguous-block under real hammer load was 49152 bytes" may be the §7F.8 probe artefact, not a heap figure.** 49152 is exactly `192 KB / 4`, the value the binary-search probe returns when it pins its own buffer, and 192 KB is the ceiling both committed probes use. The instrument behind it came in with a merge from `main` and is not in this tree, so it cannot be checked host-side. **Low urgency and not alarming**: the artefact only ever understates, so `_MAX_STATUS_PIECE_BYTES = 1024`'s headroom is 48x or better either way — this is about not reusing the number as a heap measurement. Re-measure by running `heap_headroom_after_full_system_build.py` during a bench hammer run and reading `retained=`. | SPECIFICATION.md I.3 | OPEN (record) |
| R15 | **The twin now proves chip-healthy reboot persistence for every FRAM-backed error source; real hardware proves it for none of them by name** (2026-09-18). `scripts/_digital_twin_ci_suite.py`'s Run 5c faults each bus-attached driver in its own process against a HEALTHY chip, then verifies the whole `errcount` table across a storage-paused reboot. The flash tier's `test_error_log_history_persists_in_the_real_chip_across_a_simulated_reboot` covers the *mechanism* through an isolated-driver script's own manager, never the production object graph's per-module wiring across a real reset. One run closes the parity gap (SPECIFICATION.md Part E.6.6): note `GET /status`'s `errcount` before a `PUT /system {"SystemCmd": "reboot"}`, and confirm every non-zero row comes back — `FRAM`'s own row excepted, in-memory by design. Needs no fault injection: whatever the board has already logged is the subject. | SPECIFICATION.md Part E.6.6; digital_twin/README.md's Run 5c | OPEN |
---

## 2A. Findings opened by the 2026-09-18 bench run, and by the 2026-09-19 host-side follow-up

| # | Finding | Status |
| --- | --- | --- |
| F1 | **`wifi_service_reconnect_repro.py` persists a garbage SSID and never restores it.** Its own step "overwriting SSID with a garbage value via the real `_set_dict_cfg()` path" writes `SSID = "wozi-diag2-net-does-not-exist"` into `config_WIFI.cfg` on the RP2040 **flash filesystem**. Because the script then dies on the reset (R10), the restore never runs. Observed directly: the DUT went unreachable and the REPL showed the garbage value. Recovered by writing the real SSID (`sensors-bench-fa9707`) back over the serial REPL and hard-resetting; stored password was untouched. **This is the exact class of incident CLAUDE.md's stage-0 trap warns about, via a script no warning covers** — `test_hotspot_role_reversal.py` got a stage-7 restore after the 2026-09-17 incident; this script never did. It also is **not** `@pytest.mark.persistence_write`-marked although the write is test-owned, which `tests_scripts/test_persistence_write_marker_completeness.py` cannot catch because it pins pytest tests, not `device_scripts/` invoked directly. | **FIXED 2026-09-18** (PR #105 session), still unverified on silicon — §1B's session decided B-D3 as *no* and deliberately did not run it, this being the script that stranded the bench. Both halves were wrong, not just the missing restore: `REAL_SSID` was hardcoded to `"sensors-bench-ap"` while the bench's own is `sensors-bench-fa9707`, so the restore would have written a *second* wrong SSID had it run at all. It now reads the live value through `_get_dict_cfg()` before overwriting, **aborts** rather than overwriting if it cannot read it back, and restores in a `finally` that re-reads instead of trusting a flag — so it is correct on both early returns and on any exception inside the repro. The snapshot also carries the real password, so it is never logged. **Marker decision: answered 2026-09-19, and the answer is that no marker is needed, because the production write is gone.** The script now points `conn.cfgmgr.config_file` at a scratch `config_HWTEST_WIFI.cfg` immediately after reading the real SSID, so `config_WIFI.cfg` is never opened for writing at all — the repro is driven by the in-memory cache, which is unchanged. That closes the hazard *structurally* rather than relying on a restore that a crash, a reset or a racing deferred flush can skip (`write_config()` stages and a separate task commits, so the old form could strand the board even on a clean exit path). Same convention as `reboot_persist_write.py`'s `config_HWTEST_REBOOT.cfg` and `isl29125_mechanism_envelope.py`'s `config_HWTEST_ISL29125.cfg` — those two were the only other `device_scripts/` files that own a persisting write, checked by grep, so the convention now covers all three. The scratch file is removed in a `finally` after `flush_pending()`, because it holds a full WIFI config including the real password. **Residual, and it is the owner's to weigh, not a blocker**: one scratch-file write still spends a flash cycle, and a directly-invoked device script has no pytest marker to gate that — CLAUDE.md's go-ahead rule is what gates it, and the script's own log line now says what it is about to do. |
| F2 | **The two FRAM fault injectors need a new injection technique.** `fram_cs_hijack_fault_injection_and_recovery.py` and the reset-race script both rely on `await asyncio.sleep(0)` scheduling the injector *inside* the victim's command envelope. Measure A replaced that awaited settle with a blocking `time.sleep_us(2)`, so the window no longer exists and neither can inject. They fail honestly rather than mis-measure, but they cover nothing. Needs a timer IRQ or second-core injector. | **FIXED and CONFIRMED ON SILICON 2026-09-18** — both tests pass on *both* arms of §1B's pair (§7F.7), which is also the first real-chip proof that the hijacked payload is actually *refused*; neither run tripped the "nothing was injected" guard. Not re-raced: both now inject **deterministically at the driver's own synchronous transfer seam**, wrapping `SPIDevice.write_sync`/`readinto_sync` so the CS deassertion (or the `machine.reset()`) happens immediately before the payload transfer reaches the chip. No scheduling point inside the envelope is needed, so measure A's blocking session cannot defeat it, and it targets the payload envelope rather than whichever of the ~6 CS cycles a timer happened to hit. The CS-hijack script also now *proves* it landed: it reads the CS pin back at injection time (an rp2 output pin reads its driven level) and reports "nothing was injected, so nothing was tested" instead of a misleading driver failure — the old `cs_forced_high_early` flag only proved the coroutine ran, never that it ran inside the window, which is exactly why the breakage read as a driver fault. Validated against the twin's fakes: the injection fires with CS asserted on both the write and read arms and the driver is fully usable after removal; the twin's fake chip ignores CS, so *that* the payload is refused can only be confirmed on silicon. |
| F3 | **A standalone heap reading measures the wrong thing.** `Board.run_isolated()` interrupts the already-running firmware instead of resetting, so a device script builds inside `main.py`'s aged heap. Freshly flashed, the heap test reads 95,104 B and passes; deep in a suite the same firmware reads 28,864 B and fails, with `free` unchanged. Any future heap row must state its suite position or it is not comparable. | OPEN — record in SPECIFICATION.md when §7D migrates |
| F4 | **Row A4's marker count was wrong** (three `persistence_write`, not two). Corrected in place. A reminder that these counts drift; read the deselected number from the run. | DONE |
| F5 | **The largest-block probe can pin its own buffer and report a false, round, *low* figure** — always `_PROBE_MAX >> k`, e.g. 49,152 = 192 KB / 4. Found 2026-09-19 by reproducing it deterministically on the Unix port; it is what §7F.2's unexplained row was, and the threshold had nothing to do with it (MEASUREMENTS §7F.8). It is not confined to the reporting script: `heap_headroom_after_full_system_build.py` asserts an 80,000 B floor on the same probe, so a pin at 49,152 would have been a **false tripwire FAIL on a healthy image**. No recorded failure has the signature (every one is off-node), so nothing already measured is affected. | **FIXED 2026-09-19, unverified on silicon.** Both scripts print `retained=` (the exact tell: it equals `largest_block` when pinned) and reread automatically while it is non-zero; on the twin one reread has always sufficed and lands on its clean neighbours. **What a bench run owes: nothing extra** — just read the `retained=` fields in B1's and B6's output. Any non-zero one on a non-retry line is expected and handled; a non-zero one on a `_retryN` line means three rereads failed and the figure must not be used. |
| F6 | **Measure B's placement gain decays in the run phase, within about two seconds** (twin, MEASUREMENTS §7F.9). At the starter loop's end A+B holds 20-59 % of free against A-only's 5-11 %; 4 s later both arms are in single digits, A+B roughly 2x A-only. This is not a defect in B — I.4(f.1) confines the exception to the two boot lists on purpose — but it does mean every figure taken "after boot" has to say **how long after**. | **OPEN as a silicon question, and B6 is the run that answers it.** Two consequences for whoever runs the bench: read `after_starter_loop_end`, not `after_starter_list`, when judging measure B; and do not report a drop between those two lines as a regression — the twin predicts it on both arms. |
| F7 | **§7D.5's "A fixed the UART crossover heap-growth test" is overturned.** It was drawn from one observation per arm. Five further runs: A-only **FAIL** (grew 4,192 B), A+B **FAIL** (4,752 B) in the flash suite, then A+B **PASS** in the bench tier and **PASS** in the B7 re-run — the same image both ways. The test is marginal around its own threshold, not a stable signal. Corrected in place in §7D.5 and recorded in §7H.5. **Worth deciding**: either widen its bound against a measured spread, or treat it as advisory; as it stands a green/red result from it carries no information. | **ROOT-CAUSED 2026-09-19, host-side, and it is a SAMPLING defect rather than a mis-calibrated threshold — so neither of the two options the row offers is the right one.** `uart_link_under_concurrent_system_load.py` computes `heap_growth = gc.mem_alloc()_end - gc.mem_alloc()_at_third`, both after a `gc.collect()`, and fails over 2048 B. `gc.mem_alloc()` after a collect measures **live** bytes — but both samples are taken while **five concurrent loops are still running** (`_scd_load_loop`, `_sgp_load_loop`, `_fram_read_loop`, `_memory_churn_loop`, `responder._listen_loop`), and the end sample is taken in the `finally` **before** `load.stop = True`, so the loads are live at that instant too. The churn loop's own comment says its block is "held briefly, then dropped" — so whether a multi-KB block happens to be held at either sampling instant is a coin flip, and that is the whole observed 3,584/4,192/4,752 B spread. The bound is not wrong about leaks (a real 53-B-per-transaction retention over thousands of transactions would be tens of KB and still caught); the **measurement** is contaminated. A third option, and the only one that makes the row informative again: quiesce before sampling — set `load.stop = True`, cancel the tasks, await a beat, *then* `gc.collect()` and read — or sample repeatedly near each point and take the minimum, which is the live floor with transients excluded. **Not changed here**: it is a real-hardware test this session cannot run, and CLAUDE.md's "flag, don't silently change" applies. Owner's call on which form to take. |
| F8 | **A malformed file exists on the bench board's flash**: `config_HWTEST_ISL29125.cfgconfig_ISL29125.cfg`, two config filenames concatenated with no separator. Harmless where it sits (nothing reads it). | **ANSWERED 2026-09-19, host-side, and it is NOT a live defect in this tree.** The grep the row asked for was run across `HEAD`, `origin/main` and the base branch. The only concatenation site anywhere is `base_classes.py:278`/`system_service.py:102`'s `cfg_path + "config_" + name + ".cfg"`, and **no `tests_hardware/` caller passes a `.cfg` value as `cfg_path`** — every scratch-config override in the tree assigns `cfgmgr.config_file` directly (`isl29125_mechanism_envelope.py`, `reboot_persist_write.py`/`_read.py`, `wifi_service_reconnect_repro.py`, the two debug-level scripts), which is the correct form and the only form the history ever had (`47af5bb`, `75d222e`). The filename is a **stale artefact of an older script generation or another tree**, not something this code can produce. Residual: a leftover file on the board's flash. Deleting it is a flash write, so it is D1-gated and not worth a cycle on its own — fold it into the next run that already spends one. |
| F9 | **The pre-flight `errcount` carried `FRAM: E31, W73`.** `W73` is a real FRAM-manager warning; **`errno=31` is `asy_isl29125_driver.py`'s "Status read failed"**, a foreign code under FRAM's own logger — CLAUDE.md's chunk-contamination hazard from an earlier isolated-driver script, not a FRAM fault. Recorded before this sitting's own scripts overwrote it, which they did (FRAM went 2 -> 0). | RECORDED |
| F10 | **W5's assertion cannot be satisfied by this server, and the handover's prescribed fix would not have fixed it.** Measured 2026-09-19: 24 concurrent PUTs reset ~25% of clients **regardless of body size** — an all-64-byte control resets at the same rate as the mixed one, and resets begin **at** `max_connections = 4` (2 -> 0%, 4 -> 25%, 8 -> 12%, 24 -> 25%). So W5 is measuring the connection ceiling, not the body cap, and relaxing only its oversized arm (the handover's §4 note) would leave it failing on the undersized one. Nothing in `src/` is implicated: the server stayed responsive, did not reboot under load, and `WEBSERVER`'s error log stayed empty throughout. ~~**Three options, owner's call**~~ — **RESOLVED 2026-09-19 with a fourth, and F10's own data is what picks it.** None of the three is right: dropping to concurrency 2 abandons the multi-buffer shape the row exists to exercise, accepting a reset on any arm makes the test assert nearly nothing, and a retried request is no longer concurrent with the others. **What the raw data below shows is that across 96 concurrent requests, ZERO were answered with the WRONG status** — every failure is a *refusal*, never a mis-answer. The body cap held perfectly under concurrency; the test asserted the wrong thing. W5 now asserts what the cap actually owns: **every client that IS answered is answered correctly**, with a refusal at the ceiling counted rather than failed — which is `src/`'s own documented behaviour, since `_serve()`'s reject-when-full branch closes without writing a response and does not choose FIN vs RST, exactly what `test_connections_at_and_above_the_real_socket_limit_degrade_cleanly` already accepts either of. Three guards stop it going vacuous: only a *ceiling close* is tolerated (any other exception, a timeout included, still fails, so a real hang cannot hide), at least `max_connections` requests must be answered, and both a 200 and a 413 must appear. Replayed against all four recorded runs: **PASS on every one** (18-20 answered, 0 wrong). Renamed to `test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status`. **Unverified on silicon.** | RESOLVED — re-run to confirm |


**F10's raw data, 2026-09-19** — kept so the spread is inspectable without spending bench time.
Sizes are `[512, 4096, 2048, 4096, 64, 2049, 900, 4096] * 3`; **bold** indices are bodies *under*
the cap, which should have answered 200:

| run | resets | indices (size) |
| --- | --- | --- |
| bench suite | 6/24 | **4 (64)**, 9 (4096), 11 (4096), **14 (900)**, 15 (4096), 17 (4096) |
| repeat 1 | 4/24 | 3 (4096), **6 (900)**, **12 (64)**, 23 (4096) |
| repeat 2 | 4/24 | **4 (64)**, **8 (512)**, 19 (4096), 23 (4096) |
| repeat 3 | 6/24 | **4 (64)**, **8 (512)**, 9 (4096), **10 (2048)**, 15 (4096), **18 (2048)** |

**10 undersized against 10 oversized across the four runs**, and the undersized set includes
2048 B — exactly the cap, which W1 proves is served when it is the only request in flight.
Controls: all-bodies-under-cap 4/24, 6/24, 5/24, 6/24; all-bodies-64-B 6/24, 5/24. Same rate,
no oversized body present at all.

**Why the rate is non-zero AT concurrency 4, which the table above leaves looking odd** — answered
host-side 2026-09-19 from `src/`, no bench time. A slot is released in `_serve()`'s `finally`,
*after* `_close_writer(writer)` awaits the close — so it outlives the response the client already
has. Four concurrent clients therefore need four slots that are genuinely free, and the
`reset_all_error_logs()` PUT each of these tests makes immediately beforehand can still be holding
one: 3 free slots, 4 clients, **1 refusal = the measured 25%**. This is not new behaviour —
`test_connections_at_and_above_the_real_socket_limit_degrade_cleanly` documents the same lag in its
own comment ("confirmed directly") and takes a `time.sleep(1.0)` settle for it. W5 now takes the
same settle. So "resets begin *at* the ceiling rather than beyond it" is the slot-release lag, not
a ceiling that is really 3.

---

## 3. Coverage gaps that need a bench session to close

From `tests_hardware/README.md`'s "Tenth pass", which names these as owed rather than fixed. Each is
a test to *write* against real hardware, not just a run.

| # | Gap | Status |
| --- | --- | --- |
| C1 | **F.5.8's "UART never blocks the loop" is only proven against a hand-rolled clamp, never the shipped driver.** `device_scripts/uart_read_never_blocks_the_loop.py` uses raw `machine.UART` deliberately, so no real-hardware run ever exercises `asy_uart_driver`'s own `ready()`/`_buffered()`. F.5.9 already has its real-driver-object proof (`uart_idle_poll_rate.py`); F.5.8 needs the analogue. **DONE 2026-09-19**: tier 3 green across two full flash suites, tier 4 green in the bench tier (93 passed, 0 failed). §7H.6 | DONE 2026-09-19 |
| C2 | **The bench UART exerciser never issues a multi-chunk SET**, so "bench ⊇ flash" does not hold for the SET train the flash tier proves. Wire a periodic SET into `UartLinkExerciser._exercise_loop()`'s live load. | OPEN |
| C3 | **Decide whether the mock tier's ~20-scenario UART fault-injection catalog is a genuine structural exception** or needs a raw-second-UART injection technique on the bench. | OPEN |
| C4 | **`_reboot()`'s alarm-pool-exhaustion fallback (`_force_watchdog_starve = True`) is mock-only.** | OPEN |
| C5 | **NOTIFY's own FRAM chunk has no hard-reset-recovery bench test**, unlike SGP40's. Needs an observable-write signal analogous to SGP40's `BackupTS` first. | OPEN |
| C6 | **`BenchBridge.rotate_ap_password()` is built (real `nmcli`) but has zero call sites.** Needs a project-owner design review before any bench test — it rotates real AP credentials on the shared rig. | BLOCKED on owner |
| C7 | **`test_ticks_ms_real_2pow30_rollover` needs a measurement method that does not poll with `board.exec()`.** BACKLOG item 12 established on real hardware that every `exec` starves the watchdog and hard-resets the board ~8 s later, zeroing the counter — so the hour-by-hour poll can never climb toward 2**30, and a later read landing below an earlier one is the reboot, not a wrap. The vacuous-pass hole is closed (a drop now only counts as a wrap when the previous read was already within two hours of 2**30, so the ambiguity fails honestly), but that makes the test *fail* rather than measure. A real method has to leave the board running: feed or disable the watchdog from inside the polled code, or observe passively via `tail_log()`. Design decision, then a genuine ~12.4-day run behind `--allow-multi-day-rollover-wait`. | OPEN |

---

## 4. Bench-host tasks (not the board)

| # | Task | Status |
| --- | --- | --- |
| H1 | **The two-chroot verification, unsatisfied since 2026-09-12** — an owner-run periodic check since 2026-09-18, not a gate that blocks anything. Everything this branch changed in `scripts/`, `pyproject.toml` and — the highest-risk part, which the lint/typecheck recipe never exercises — `toolchain/setup_toolchain.py` + the new `toolchain/micropython_overrides.py`. The bench Pi4 already runs trixie/GCC 14.2, so it is the right host for the leg that has never run. Full account and what changed: BACKLOG.md's own entry. | OPEN |
| H2 | **`scripts/test.sh`'s parallelism probe on the Pi4.** Report the `== Test parallelism: N (C usable cores x M, interpreter speed probe Xms)` line verbatim. Thresholds (4x ≤250 ms, 2x ≤900 ms, 1x beyond) were calibrated from an x86 sandbox plus a *simulated* slow host, never the real Pi4. Confirm it lands on 2x and that the previously-starved twin test (`test_digital_twin_sensortask_integration.py`'s hotspot/DNS case) passes. If it still starves at 2x, say so — the next step is 1x for that class, not re-tuning the probe. | OPEN |
| H3 | **Two bench-rig capabilities are not provisioned**, each of which would move one `[MANUAL]` test candidate to `[AUTO]`: a programmable GPIO fault-injection harness, and a second WiFi test client (BACKLOG item 8). Provisioning is a hardware decision, not a test run. | BLOCKED on owner |

---

## 5. Excluded on purpose

- **Heap fragmentation, beyond §1A.** §1A's rows are **all run as of 2026-09-18** — results in
  the rows themselves, §1A-R, and `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7D, which is the first
  [HW] section on this branch. **Measure B is no longer excluded** — it was
  built on 2026-09-18 (`7ccbe8d`), so plan T.1's A+B column and T.5's collect timing are now
  runnable and live in §1B above — and, as of 2026-09-19, **run and closed** (§7H).
  What stays excluded on PR #105 is plan section C (the seam + contiguity guard) and section D, both
  of which need the owner's go-ahead and neither of which is built. The one failure left at PR #103's
  close is that defect.
- **PR #84's three bench passes** (`reactive` full suite 95 passed/2 skipped; `reactive` + churn
  pressure tests 3 passed; `threshold` full suite 95 passed/2 skipped) are already run, on that PR's
  own branch, and do not need repeating. **The PR itself was closed unmerged on 2026-09-18 by owner
  decision** (BACKLOG 33), so its `--gc-policy` / `--memory-pressure` machinery is not available to
  any run listed above and is not coming — none of PR #84 is on this branch, and the tooling is
  unshipped by decision rather than pending.
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
  equals `largest_block` in that case, and the scripts reread on their own (§2A F5).
- **"After the starter list" and "after boot" are not the same position, and the gap is seconds.**
  Judge measure B by `after_starter_loop_end`; `after_starter_list` is taken seconds into the run
  phase, where the twin says most of B's gain is already gone on both arms (§2A F6).
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
  (§2A F10).
- **Don't chase `asy_fram_manager.py`/`asy_fram_driver.py` internals** from anything found here —
  heavily audited, and any real change there needs its own scoped review (SPECIFICATION.md C.3.1).
  **§1A is the one carve-out**: those two files plus `asy_spi_driver.py` are what measure A rewrote
  under an owner-granted scoped exception, so a failure in A2-A8 is a finding *about* that change
  and belongs back to the PR #105 session — still not a drive-by fix here.
