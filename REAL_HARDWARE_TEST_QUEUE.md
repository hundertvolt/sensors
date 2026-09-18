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

## 1. Suite runs

| # | Run | Notes | Status |
| --- | --- | --- | --- |
| S1 | `scripts/run_flash_hardware_suite.sh` | **DONE 2026-09-18, on BOTH arms.** Tip: `3 failed, 33 passed, 3 skipped, 12 deselected` (864.67 s). Before arm: `2 failed, 34 passed, 3 skipped, 12 deselected` (844.84 s). Failure attribution in §1A-R. | DONE |
| S2 | `scripts/run_bench_hardware_suite.sh` | **DONE 2026-09-18 (tip): `3 failed, 90 passed, 4 skipped, 27 deselected`** (2,288.40 s) — the same three failures as S1, no bench-only ones. The heap reading was 28,864 B again, byte-identical to S1. | DONE |
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
| R10 | **Two `tests_hardware/device_scripts/` bugs are fixed in source but have never been executed since.** **DONE 2026-09-18, split result.** `fram_write_protect_roundtrip.py`: **PASS** — the keyword-only fix is good, and it exercised A's self-acquiring-the-bus path (A9). `wifi_service_reconnect_repro.py`: the `task.data` fix is confirmed (it now runs deep into the real CYW43 reconnect, reaching `EPERM`, where it used to die at first contact) but the script **does not complete** — the board drops the USB CDC mid-run and mpremote ends in `OSError: [Errno 5]`. It likely needs `run_isolated_expect_reset()`. **It also left the bench stranded — see §2A.** | DONE (finding) |
| R7 | **`SPECIFICATION.md` Part A.7's FRAM setup-cost figures are twin-only.** `digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time, so every number there excludes the real per-transaction cost. Re-measure on silicon. Largely the same instrumentation as R6. **Premise corrected by A6 (2026-09-18):** the omitted term is *not* mainly SPI wire time — at 1 MHz six transactions are ~300 us of the measured 2,849 us, so ~90 % is MicroPython interpreter / `machine.SPI` call overhead. Frame the re-measurement that way. | SPECIFICATION.md Part A.7 | OPEN |

---

## 2A. Findings opened by the 2026-09-18 session

| # | Finding | Status |
| --- | --- | --- |
| F1 | **`wifi_service_reconnect_repro.py` persists a garbage SSID and never restores it.** Its own step "overwriting SSID with a garbage value via the real `_set_dict_cfg()` path" writes `SSID = "wozi-diag2-net-does-not-exist"` into `config_WIFI.cfg` on the RP2040 **flash filesystem**. Because the script then dies on the reset (R10), the restore never runs. Observed directly: the DUT went unreachable and the REPL showed the garbage value. Recovered by writing the real SSID (`sensors-bench-fa9707`) back over the serial REPL and hard-resetting; stored password was untouched. **This is the exact class of incident CLAUDE.md's stage-0 trap warns about, via a script no warning covers** — `test_hotspot_role_reversal.py` got a stage-7 restore after the 2026-09-17 incident; this script never did. It also is **not** `@pytest.mark.persistence_write`-marked although the write is test-owned, which `tests_scripts/test_persistence_write_marker_completeness.py` cannot catch because it pins pytest tests, not `device_scripts/` invoked directly. | OPEN — needs a restore (read the real SSID first, restore in a `finally`) and a marker decision |
| F2 | **The two FRAM fault injectors need a new injection technique.** `fram_cs_hijack_fault_injection_and_recovery.py` and the reset-race script both rely on `await asyncio.sleep(0)` scheduling the injector *inside* the victim's command envelope. Measure A replaced that awaited settle with a blocking `time.sleep_us(2)`, so the window no longer exists and neither can inject. They fail honestly rather than mis-measure, but they cover nothing. Needs a timer IRQ or second-core injector. | OPEN — belongs to the PR #105 session (§6's carve-out) |
| F3 | **A standalone heap reading measures the wrong thing.** `Board.run_isolated()` interrupts the already-running firmware instead of resetting, so a device script builds inside `main.py`'s aged heap. Freshly flashed, the heap test reads 95,104 B and passes; deep in a suite the same firmware reads 28,864 B and fails, with `free` unchanged. Any future heap row must state its suite position or it is not comparable. | OPEN — record in SPECIFICATION.md when §7D migrates |
| F4 | **Row A4's marker count was wrong** (three `persistence_write`, not two). Corrected in place. A reminder that these counts drift; read the deselected number from the run. | DONE |

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

- **Heap fragmentation, beyond §1A.** §1A's rows are **all run as of 2026-09-18** — results in
  the rows themselves, §1A-R, and `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7D, which is the first
  [HW] section on this branch. Everything else on PR #105 still belongs to the
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
