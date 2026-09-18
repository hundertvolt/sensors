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

---

## 0. Decide before the run

These change what gets run, so settle them first.

| # | Decision | Why it matters | Status |
| --- | --- | --- | --- |
| D1 | **Does the bench spend flash/NVM writes this round?** A default run deselects 13 of the bench tier's 73 tests and 9 of the flash tier's 51; `--allow-persistence-writes` runs them and spends real cycles. `--allow-scd30-extra-write` is AND-gated on top for one further SCD30 NVM write. | Several rows below are *only* reachable with the flag — R1 and R4 in particular. Deselection is invisible to the pass/fail check, so this must be a knowing choice (CLAUDE.md's wear rule). | OPEN |
| D2 | **Is the NeoPixel-aimed-at-the-ISL29125 rig set up?** The gating question is **settled** — `main`'s `@pytest.mark.neopixel_sweep` + `--allow-neopixel-sweep` has been adopted here (2026-09-18), so `test_isl29125_survives_recombined_realistic_lighting_scenarios` (~8.5 min) and `test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration` (~99 s) now skip by default instead of failing on a bench without the rig. What remains is the physical question: decide whether to pass the flag this round. | The 2026-09-17 bench session ran both ungated and they passed after the `_park()` fix, which suggests the rig *is* in place — confirm rather than assume, and record the geometry via the manual tier's `isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry` (M1) so the next session does not have to. Opting in costs ~10 min. | OPEN |
| D3 | **Which firmware image.** Every row below assumes a `dev` build from this branch's own tip via `scripts/build_firmware.py dev`. | CLAUDE.md's hard rule: a `wozi` build flashed onto the dev bench "tests nothing at all" and has produced false bugs before. | OPEN |
| D4 | **Is §1A's before/after pair being run this sitting?** It needs **two** `dev` images — the merge base and this branch's tip — so two build+flash cycles, in that order. | Only relevant if A0/A1 are in scope. Every other row needs one image (the tip). Reusing an older `largest_block` reading from a previous session as the "before" arm is not a before/after: the board's provisioning, the base branch and the firmware have all moved since 2026-09-17. | OPEN |

---

## 1. Suite runs

| # | Run | Notes | Status |
| --- | --- | --- | --- |
| S1 | `scripts/run_flash_hardware_suite.sh` | Full flash tier. Read the verdict's **deselected** count, not just "clean" (`scripts/_require_clean_hardware_run.sh`). | OPEN |
| S2 | `scripts/run_bench_hardware_suite.sh` | Full bench tier (strict superset of flash). Same deselected-count caveat. | OPEN |
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
| A0 | **The "before" heap reading.** Build and flash `dev` from the merge base (`claude/automated-build-chain-nuzumw`), then run `uv run pytest tests_hardware/flash/test_memory_stress.py -k test_real_gc_heap_headroom -v` **five times**, recording the `HEAP after_build_system: free=… alloc=… largest_block=…` line from each. | **Expect this arm to FAIL** — the 80,000 B floor is the defect this branch addresses (board read 20,592 B on 2026-09-17). The failure message includes the full device output, so every `HEAP` line still comes back. Five runs because one reading cannot separate the level from the spread. | OPEN |
| A1 | **The "after" heap reading.** Same five runs on a `dev` build from this branch's tip. | Same command, same five-times rule. Both arms must be the same board, same sitting, same ambient state — a reading taken weeks apart against a differently-provisioned board is not a before/after. | OPEN |
| A2 | **FRAM functionality, flash tier**: `uv run pytest tests_hardware/flash/test_fram_storage.py -v` | All 9 tests. Drives 10 of the 13 `device_scripts/fram_*.py` plus `sgp40_fram_backup_restore.py`: manager roundtrip, SGP40 VOC backup/restore, error-log roundtrip, the error-log reset race (seed+verify), the boot-window reset, write-protect, pause/unpause gating, busy-status lockout, capacity after a full build. This is the row that says the restructure kept every safety measure. | OPEN |
| A3 | **FRAM bus hazards, flash tier** (tier 3 of CLAUDE.md's four): `uv run pytest tests_hardware/flash/test_bus_concurrency.py -v -k "fram or deinit"` | `test_fram_same_device_read_write_concurrency`, `test_fram_cs_pin_hijack_fault_injection_and_recovery`, `test_fram_hard_reset_race_during_write_and_recovery` (the remaining 3 `fram_*.py` scripts), plus `test_i2c_and_spi_deinit_are_silent_noops_and_each_bus_id_is_a_singleton` — included because A touched `asy_spi_driver.py`, not because FRAM needs it. | OPEN |
| A4 | **Bus hazards under real API load, bench tier** (tier 4): `uv run pytest tests_hardware/bench/test_bus_concurrency_under_api_load.py -v` | 6 tests, each of which asserts FRAM stays initialized and responsive while real HTTP clients hammer the API. Two of the six are `@pytest.mark.persistence_write`. | 4 of 6: OPEN / 2: BLOCKED on D1 |
| A5 | **The second-SPI-device question is NOT testable here — do not report it as verified.** The bus lock's scope widened from one command (~5 CS, ~100 µs) to a whole block operation (~25 CS, ~600 µs), so a second SPI device would wait ~6x longer. No `devices/*.toml` wires a second SPI device, so nothing on this bench can contend with the FRAM for SPI0. | Record as structurally untestable on the current rig, the same way `tests/test_bus_hazard_multi_device.py` covers the shape no generated TOML can produce. A6's hold-time number is the closest real evidence available. | OPEN (record, do not run) |
| A6 | **Hold time, measured on real wire** (plan T.4, sharpened by the per-block-operation scope). The twin cannot answer this at all: `digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time (this queue's own R7 already says so). Script below. | Two distinct numbers, and conflating them is the trap: **(a)** the longest *synchronous, non-yielding* stretch, which is what blocks the asyncio loop — one command envelope; **(b)** the *bus-lock hold*, which is the whole block operation including the yields inside it, and is what a second SPI device would wait. (a) is the F.3 number; (b) is the A5 number. | OPEN |
| A7 | **Boot cost, for the record only** (plan T.5): `time.ticks_ms()` across `build_system()`, median of 5, on both arms. | Boot latency is explicitly not a metric to optimise (CLAUDE.md, WP6) — this exists to confirm nothing approaches the 8,388 ms watchdog cap, and to feed this queue's R7, whose whole point is that Part A.7's FRAM setup-cost figures are twin-only. If R6/R7 are run in the same sitting, fold this into them rather than booting separately. | OPEN |
| A8 | **Re-read `GET /status`'s `errcount` after A2-A4 and check for anything the restructured path could have logged**: errno 90/91/92/93/99/100 (the byte-level read/write guards) and wrnno 81/82/84 (write-protect/WEL). | Every one of these numbers and messages was preserved verbatim through the restructure and is asserted by the mock tier, but only the real chip can produce the status bits that trigger them. A clean run here is the functional result; a *new* entry is the most valuable thing this whole block could produce. | OPEN |
| A9 | R10's `fram_write_protect_roundtrip.py` (fixed-in-source, never executed) now also exercises A's `set_write_protected()` self-acquiring-the-bus path. | Cross-reference only — the run itself is R10's, and A2 covers it. Do not run it twice. | see R10 |

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

## 2. Targeted investigations

| # | Investigation | Source | Status |
| --- | --- | --- | --- |
| R1 | **BACKLOG item 30 — the ISL29125 HTTP connection reset under concurrent API load.** Owner's direction is to root-cause and resolve, not re-measure. Shape is established: needs **both** a config-persisting PUT **and** ≥2 concurrent readers (PUT alone 0/10, PUT+1 reader 0/6, PUT+2 readers **6/18**, plain GET+2 readers 0/6); failures land at 21–72 ms against 0.5–2.2 s for successes, and `WEBSERVER`'s counter stays 0 so FRAM forensics will not help. **Do the no-code bisection first**: `PUT /sensors {"ISL29125": {"RangeAuto": false}}` drops `_switch_range()` from the three-step push, leaving only `configure()` + `_reapply_persist()`. Rate falls → the threshold re-arm is implicated; unchanged → it is the first two. Restore `RangeAuto` afterwards. | `REAL_HARDWARE_HANDOVER_PR103.md` §1; BACKLOG 30 | BLOCKED on D1 |
| R2 | **BACKLOG item 32 — the `ResetErrors` reader-count curve.** Elapsed time at **0, 1, 2, 3, 4, 6** concurrent `GET /status` readers. Two points exist (6.32 s idle, 11.58 s at 3 readers = 77 % of the 15 s server cap); two points cannot say whether the curve flattens. | `REAL_HARDWARE_HANDOVER_PR103.md` §2.1; BACKLOG 32 | OPEN |
| R3 | **BACKLOG item 29 — the spurious `W4`.** A real outage logged `W4` ("WLAN wrong password") twice alongside the expected `W5`, on a network whose password never changed. One look at whether CYW43 genuinely reports that mid-transition (making `_assert_wifi_log_has_only_benign_ap_not_found_warning()` wrong) or whether `_poll_sta_connect_status()` mis-maps it. Do not chase far. | `REAL_HARDWARE_HANDOVER_PR103.md` §2.3; BACKLOG 29 | OPEN |
| R4 | **`ResetErrors` completeness under contention.** Pre-populate the FRAM error logs on several modules, then sweep under R2's reader load and confirm every counter reads back 0. All previous correctness checks were made at idle or with the logs already empty; a silently skipped chunk is invisible today because the call still answers `200`. | `REAL_HARDWARE_HANDOVER_PR103.md` §3 | BLOCKED on D1 |
| R5 | **BACKLOG "Refactor targets" — the WP5 deferred-config-write re-confirmation.** The BMP3XX arm passed on 2026-09-17 on WP5 firmware; make that durable rather than one run. The ISL29125 arm is R1, not this row. | BACKLOG, first entry | BLOCKED on D1 |
| R6 | **Boot latency for WP1–WP8.** Already measured (pre-WP **7.74 s** → WP1+WP2 **9.80 s** → WP1–WP8 **9.76 s** → +`CFGMGR_SYSTEM` fix **10.66 s**, medians of 5, spread ±0.06 s; 23 reboots, no `WDT_RESET`) — but **only inside unmerged PR #102**. Re-run only if that PR is abandoned rather than landed. The open sub-question either way: the `CFGMGR_SYSTEM` setup-order fix costs **+0.90 s**, far more than one extra FRAM-backed logger's `setup()` should, and is unexplained. | PR #102; `REAL_HARDWARE_HANDOVER.md` | BLOCKED on the PR #102 decision |
| R8 | **Two newly adopted bench tests, never yet run on silicon** (ported from `main` 2026-09-18, see BACKLOG item 33). `test_isl29125_calibrate_command_push_over_real_rest` pins that a calibration run never moves the *applied* `GainRatio` and that `GainMeas` reaches `/measurements`; `test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value` pins that ratio across a real hard reset. The second is `@pytest.mark.persistence_write`-marked here (it owns two persisting PUTs) where `main` left it unmarked, so it needs D1. Both were written against `main`'s API shape and adapted to this branch's nested `PUT /sensors {"ISL29125": {...}}` body — expect the adaptation to be where a first run goes wrong, if anywhere. | BACKLOG 33 | calibrate: OPEN / reboot: BLOCKED on D1 |
| R9 | **The ISL29125 shadow-divergence fix, and the `Overrange` field that replaced `W12`, have never run on silicon.** `configure()`'s device-session lock was widened to span the whole validate-mutate-write(-rollback) sequence (WP-era fix, unit-tested by `test_configure_never_exposes_the_shadow_ahead_of_a_write_still_in_flight`), but the false `wrnno=11` it fixes only ever manifested under real concurrent bench load - so only real load re-confirms it. Same run covers the `Overrange` half: `device_scripts/isl29125_mechanism_envelope.py` now reads the live field instead of the retired `W12` log entry. | BACKLOG, "Open questions" first entry | OPEN |
| R10 | **Two `tests_hardware/device_scripts/` bugs are fixed in source but have never been executed since.** `fram_write_protect_roundtrip.py` called `set_write_protected(False)` positionally at four sites after the parameter became keyword-only (`TypeError` on its first call, on every run since); `wifi_service_reconnect_repro.py` called `task.exception()`, which MicroPython's `Task` does not have (`AttributeError` at exactly the moment it was reporting why a task died, now `task.data`). Both grounded in source, neither re-run. A flash-tier session confirms both. | BACKLOG, "Deferred" | OPEN |
| R7 | **`SPECIFICATION.md` Part A.7's FRAM setup-cost figures are twin-only.** `digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time, so every number there excludes the dominant real term (SPI wire time under lock contention). Re-measure on silicon. Largely the same instrumentation as R6. | SPECIFICATION.md Part A.7 | OPEN |

---

## 3. Coverage gaps that need a bench session to close

From `tests_hardware/README.md`'s "Tenth pass", which names these as owed rather than fixed. Each is
a test to *write* against real hardware, not just a run.

| # | Gap | Status |
| --- | --- | --- |
| C1 | **F.5.8's "UART never blocks the loop" is only proven against a hand-rolled clamp, never the shipped driver.** `device_scripts/uart_read_never_blocks_the_loop.py` uses raw `machine.UART` deliberately, so no real-hardware run ever exercises `asy_uart_driver`'s own `ready()`/`_buffered()`. F.5.9 already has its real-driver-object proof (`uart_idle_poll_rate.py`); F.5.8 needs the analogue. | OPEN |
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
| H1 | **The two-chroot pre-push gate, unsatisfied since 2026-09-12.** Everything this branch changed in `scripts/`, `pyproject.toml` and — the highest-risk part, which the lint/typecheck recipe never exercises — `toolchain/setup_toolchain.py` + the new `toolchain/micropython_overrides.py`. The bench Pi4 already runs trixie/GCC 14.2, so it is the right host for the leg that has never run. Full account and what changed: BACKLOG.md's own entry. | OPEN |
| H2 | **`scripts/test.sh`'s parallelism probe on the Pi4.** Report the `== Test parallelism: N (C usable cores x M, interpreter speed probe Xms)` line verbatim. Thresholds (4x ≤250 ms, 2x ≤900 ms, 1x beyond) were calibrated from an x86 sandbox plus a *simulated* slow host, never the real Pi4. Confirm it lands on 2x and that the previously-starved twin test (`test_digital_twin_sensortask_integration.py`'s hotspot/DNS case) passes. If it still starves at 2x, say so — the next step is 1x for that class, not re-tuning the probe. | OPEN |
| H3 | **Two bench-rig capabilities are not provisioned**, each of which would move one `[MANUAL]` test candidate to `[AUTO]`: a programmable GPIO fault-injection harness, and a second WiFi test client (BACKLOG item 8). Provisioning is a hardware decision, not a test run. | BLOCKED on owner |

---

## 5. Excluded on purpose

- **Heap fragmentation, beyond §1A.** §1A now carries measure A's own rows, because the owner
  reported the branch on the bench (2026-09-18). Everything else on PR #105 still belongs to the
  session working it (`HANDOVER_HARNESS_AND_HEAP_FRAGMENTATION.md` is its handover): measure B (the
  boot-confined `gc.collect()`) is not built, so its rows — plan T.1's A+B column, T.5's collect
  timing — cannot be run yet. The one failure left at PR #103's close is that defect.
- **PR #84's three bench passes** (`reactive` full suite 95 passed/2 skipped; `reactive` + churn
  pressure tests 3 passed; `threshold` full suite 95 passed/2 skipped) are already run, on that PR's
  own branch. They do not need repeating — but note **none of PR #84 is on this branch**, so its
  `--gc-policy` / `--memory-pressure` machinery is not available to any run listed above.
- **Round 1's three answered requests** — `ResetErrors` idle timing, WIFI's all-or-nothing log
  across an abrupt restart, and the two `uart_link` instances through the reset path. Answered and
  migrated (SPECIFICATION.md Part A.7, BACKLOG 24). Do not re-measure.

---

## 6. Standing traps for whoever runs this

Condensed from `REAL_HARDWARE_HANDOVER_PR103.md` §4 and CLAUDE.md, because they are the ones that
have actually cost something:

- **`bench.kick_all_stations()` (deauth) generates no WIFI log entries** — a persistence check built
  on it passes vacuously `0 → 0`. Use a real `bench.ap_down()` outage.
- **Any destructive test of the bench host's own network config keeps a recovery dead-man's-switch
  armed for the whole risk window.** A one-shot timer consumed by an earlier dry run gave zero
  protection to the real run that followed, and cost the Pi4 its own SSH access (SPECIFICATION.md
  Part B.13).
- **The hotspot role reversal's stage 0 clears the DUT's persisted SSID.** Stage 7 now restores it
  over the hotspot, but a failure between them used to leave the board permanently in hotspot mode
  with no STA config, recoverable only over the serial REPL. It has happened.
- **Don't chase `asy_fram_manager.py`/`asy_fram_driver.py` internals** from anything found here —
  heavily audited, and any real change there needs its own scoped review (SPECIFICATION.md C.3.1).
  **§1A is the one carve-out**: those two files plus `asy_spi_driver.py` are what measure A rewrote
  under an owner-granted scoped exception, so a failure in A2-A8 is a finding *about* that change
  and belongs back to the PR #105 session — still not a drive-by fix here.
