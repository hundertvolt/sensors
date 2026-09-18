# Real-hardware handover — bench round 2, `claude/digital-twin-wifi-fram-persistence-fix`

Temporary file, same convention as its predecessors: delete once its findings are confirmed-and-
migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`, or confirmed not to apply. Written by a
session with **no real-hardware access**, for one that has the project owner's go-ahead. Nothing
here authorizes skipping CLAUDE.md's standing gate.

Round 1's three requests are answered and already migrated (SPECIFICATION.md Part A.7, BACKLOG item
24) — don't repeat them. **You are running the full bench suite anyway; this file is only about what
to focus on within it, what to measure on top, and the one special test worth adding.**

## 0. Read first — the harness changed under you since round 1

**Your old command lines will silently run less than you think.**

- `--allow-scd30-writes` **no longer exists**. It is now `--allow-persistence-writes`, and it gates
  *any* limited-endurance write, not just the SCD30's NVM: the RP2040's flash filesystem counts,
  because every accepted config-persisting `PUT` goes through `config_manager.py`'s own
  `json.dump()`. `--allow-scd30-extra-write` is unchanged and still AND-gated on the global flag.
- **Without the flag, 23 of the bench tier's 71 tests and 9 of the flash tier's 51 are deselected.**
  Deselection is invisible to `scripts/_require_clean_hardware_run.sh`'s skip check, so that script
  now prints the deselected count in its own verdict — read it. "Clean" means "everything that ran,
  passed", not "everything ran".
- A **dispatch-only** PUT is deliberately outside the gate (`SystemCmd`, `PauseTime`, `lightCmdLED`,
  `ResetErrors`, plus any field with `dispatch=true` in its `@web` tag — `SGPResetVOC`,
  `ISLCalibrate` today). Those persist nothing. FRAM is also out of scope: effectively unbounded
  endurance at our write rates.
- So: **a full bench run needs `--allow-persistence-writes`**, and opting in spends real flash
  cycles on those 23 + 9 tests. That is the intended trade, not an accident — but decide it
  knowingly rather than discovering it from the deselected count afterwards.

## 1. Primary focus — BACKLOG item 30, the ISL29125 connection reset

This is the one open item with a real product consequence, and the owner's direction is to
root-cause and resolve it rather than re-measure it. Round 1 established the *shape*: it needs
**both** a config-persisting PUT **and** >= 2 concurrent readers (PUT alone 0/10, PUT + 1 reader
0/6, PUT + 2 readers **6/18**, plain GET + 2 readers 0/6). Failures land at 21-72ms against
0.5-2.2s for successful writes, the connection dies before reaching the handler, and **the DUT logs
nothing** — `WEBSERVER`'s counter stays 0, so FRAM forensics will not help you.

**The lead round 1 did not have.** The BMP3XX arm of the same file now passes, and comparing the two
properly is what narrows this. They are the *same* test shape — 2 GET workers on `/sensors`, one
writer alternating between two valid values, same endpoint, same flash path. Identical setup,
opposite outcome, so the flash write they share cannot be the discriminator. What differs is the
driver's own push:

| | `BMP3XX` `PressOvers` | `ISL29125` `Resolution` |
|---|---|---|
| bus work per push | one `set_*` write | **three steps** |
| | | `isl.configure(resolution=…)` |
| | | `_reapply_persist()` — the derived persistence counter changes with the cycle length |
| | | `_switch_range()` — re-arms threshold registers scaled to the *old* resolution |

`RangeAuto` defaults to `True` and `dev` leaves it there, so all three legs run on your board. That
is a much longer critical section against two concurrent readers than BMP3XX's single write.

**Do this bisection first — it needs no code change.** `RangeAuto` is a plain REST bool:

1. Reproduce the failure as-is (arm B: PUT + 2 readers, >= 18 reps to get a usable rate).
2. `PUT /sensors {"ISL29125": {"RangeAuto": false}}`, repeat. `set_resolution()` then skips
   `_switch_range()` entirely.
3. If the rate drops materially → the threshold re-arm is implicated. If it does not → it is
   `configure()` + `_reapply_persist()`.
4. Restore `RangeAuto` afterwards (the bench rig is shared).

Only then instrument. Worth capturing while you are in there: whether the reset correlates with the
*flash write* or with the *I2C sequence* — those are separable in time, and round 1 proved only that
the persisting write is necessary, never that the interrupt-disable window is the mechanism.
SPECIFICATION.md Part F.2's accepted residual risk is the hypothesis, not an established finding.

## 2. Parameters to measure on top of the suite

All cheap, all things the suite does not currently record.

**2.1 `ResetErrors` scaling with reader count.** Round 1 gave two points: 6.32s idle, 11.58s with 3
concurrent `GET /status` workers (77% of the 15s ceiling). Two points do not tell us whether that
curve flattens or keeps climbing. Take **0, 1, 2, 3, 4, 6 readers** and report the elapsed time for
each. If it is still rising at 6, `dev` has less headroom than BACKLOG 24 currently claims and the
sequential sweep becomes a design question rather than a watch item. The twin now asserts an
elapsed-time budget of 80% of the cap (12.0s) and measures 8.2-8.9s there; a real-hardware analogue
only makes sense once the curve's shape is known.

**2.2 The host's own parallelism probe.** `scripts/test.sh` now autodetects how many test processes
to run from a timed loop in the Unix-port interpreter, because core *count* cannot tell a fast
4-core x86 runner from the 4-core Pi4 (BACKLOG item 28). It prints one line at startup:

```
== Test parallelism: N (C usable cores x M, interpreter speed probe Xms)
```

**Run `scripts/test.sh` on the Pi4 and report that line verbatim.** Thresholds are 4x at <=250ms, 2x
at <=900ms, 1x beyond, calibrated from an x86 sandbox (117-135ms) plus a *simulated* slow host —
never from the real Pi4. Two things to confirm: that it lands on 2x, and that the twin test which
previously starved (`test_digital_twin_sensortask_integration.py`'s hotspot/DNS case) now passes.
If it still starves at 2x, say so — the next step is 1x for that class, not re-tuning the probe.

**2.3 The `W4` question (BACKLOG item 29).** During
`test_real_wifi_outage_and_recovery_while_in_normal_sta_mode`, a real outage logged `W4` ("WLAN
wrong password") twice alongside the expected `W5`, on a network whose password never changed. One
look at whether the CYW43 driver genuinely reports that status mid-transition (making the test's
`_assert_wifi_log_has_only_benign_ap_not_found_warning()` wrong) or whether
`asy_wifi_service.py`'s `_poll_sta_connect_status()` mis-maps it. Don't chase it far.

## 3. The special test worth adding

**A chip-healthy persistence sweep (BACKLOG item 25) is a twin task, not yours** — noted only so you
don't spend bench time on it.

What *is* worth a purpose-built run: **`ResetErrors` under the reader load from 2.1, with the FRAM
error logs pre-populated on several modules**, confirming every counter reads back 0 afterwards. All
of round 1's correctness checks were made at idle or with the logs already empty; nothing has yet
proven the sweep is *complete* while the webserver is genuinely contended. If a chunk is silently
skipped under load, that is invisible today — the call still answers `200`.

## 4. What not to do

- **Don't re-measure round 1's three requests.** `ResetErrors` idle timing, WIFI's all-or-nothing
  log across an abrupt restart, and the two `uart_link` instances through the reset path are all
  answered and migrated (SPECIFICATION.md Part A.7, BACKLOG item 24).
- **Don't read a FRAM-backed error log as field evidence without checking what has run against the
  board.** An isolated-driver device script builds its own `AsyFramManager` over the same chip and
  the allocator is deterministic, so a flash/bench-tier run overwrites production's own first chunk
  and can leave a plausible-looking fabricated entry behind (CLAUDE.md's 2026-09-11 caveat;
  `tests_hardware/README.md` has the mechanism).
- **Don't chase `asy_fram_manager.py`/`asy_fram_driver.py` internals** from anything found here —
  vendored-adjacent, heavily audited (SPECIFICATION.md Part C.3.1). Any real change there needs its
  own scoped review.
- **Don't run `scripts/build_firmware.py wozi` on the dev board.** CLAUDE.md: that combination
  "tests nothing at all" and has produced false bugs before.
- `bench.kick_all_stations()` (deauth) generates **no** WIFI log entries — a persistence check built
  on it passes vacuously `0 -> 0`. Use a real `bench.ap_down()` outage, with a recovery dead-man's
  switch armed for the whole window (SPECIFICATION.md Part B.13).
