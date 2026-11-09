# R5 unit B: the drivers and services - each cost at its source, nothing lost (lead, 2026-11-09)

## Read first
`S/u35r/r1/common_r1.md` (binding: "Standing direction" - every level, cost against need, the platform first, the
goal, ask before removing a feature - and the new filter rule; labels `ub_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then FINDINGS 12.105, 12.107,
12.108 (2), 12.115, 12.125, 12.129-12.133 and `S/u35r/r5/SIMPLER_2.md`, `CPRIM.md` (polls), `STRETCH.md` section 2.
Code: int `S/wt-u35int` at 8f04f2f1. Unit fsync writes at the same time: it owns `asy_print_log`, `asy_fram_*`,
`asy_spi_driver`, `asy_crc_checks` and the form of every log call - never change a log call's form, only move or
delete whole calls your change needs to.

## Owner (verbatim, all 2026-11-09)
- 21:27:06: "if the LED never has anything to report, it probably also does not need RAM loging? So either it gets
  FRAM if it has something to log, or it should get no logger at all. ..."
- 21:36:14: "... find a solution without that many magic numbers and which generalizes cleanly."
- 20:43:39: "... finding objectively optimized solutions." 19:17:45: simpler at every level, no function dropped.

## Your work (worktree `S/wt-ub`, branch `audit/ub` from int 8f04f2f1; create it; commit locally, never push)
1. LED (`asy_neopixel_driver.py`, 12.131, 12.133): one LED lock held for whatever drives the pixel; an internal
   request waits its turn on it (FIFO, no poll, no deadline, never dropped); an external command is refused while it
   is held or one is pending (owner 2026-10-02); `_SIGNAL_WAIT_MS`, its tunable row and the polling go; the overlay
   writes directly when the lock is free, else the ramp's end restores it (12.105 #7: the overlay task and
   `_overlay_lock` go); the ramp allocates nothing per frame (integer steps into one reused list; same frames). Then
   the LED has no failure path: no logger - its FRAM chunk, history, `/status` errcount entry, ResetErrors source and
   its buildgen wiring go; its event lines print through the plain console printer. Say the FRAM layout shift.
2. SCD30: releases the bus across its 50 ms waits (12.107 (3); flag it for the bench before shipping); its 12 chip
   wrappers through one helper pair, all 12 kept (12.125 (6)); the six single-field getters stay (OR36.a (3)).
3. BMP3XX: one wait of the datasheet's computed conversion time, then one read, at every oversampling setting (CPRIM:
   30-73 STATUS reads per sample at x32/x32; U15's computed sleep was right, b4341646 restored the 2 ms poll); the
   `_push_*` re-check of a schema-coerced int goes (12.125 (12)).
4. SGP40/VOC: STRETCH section 2's fold (constants to ints, exact int products with libfixmath rounding): bit-identical
   on its vectors, measured; the three VOC port functions stay (owner).
5. ISL29125/math_helpers: the five colour functions and their constants move beside their only caller (12.125 (4)).
6. Waits (12.129): the two uptime ticks and NTP's check and retry wait by deadline sleeps (start tick + k x period;
   the retry keeps 15 s); NTP's 1 Hz sync-age loop and notification's pause loop go (12.105 #3); the boot stagger by
   plain deadline sleeps (12.107 (4)); `arm_tick_timer()` goes with its last callers; `stop_uptime_timer()`,
   `stop_check_timer()` and `get_last_ntp_sync()` go (only tests call them: OR36.a (1)); the reset timer stays (owner
   2026-07-18).
7. Notification (12.129): a build-time check on buildgen's fixed signal catalog replaces the runtime refusal; codes
   44 and 45 retired, kept reserved in the catalog, never reused.
8. Lean (12.107 (5)): await-free `_data_lock` holds and the lock-less async Locked* classes (12.105 #4); PieceBuffer
   out of the five production images (#5); captive DNS strings only debug prints read (#10); identical overrides
   (12.125 (5)); the 22 starters as `asyncio.create_task(...)` (12.125 (12)).
9. D.8 re-read of every 2026-11-03 "back to pre-audit" rollback (b4341646, 6c00e98e and the rest of that batch, git
   log): per rollback, its operations' cost against need on silicon; fix what exceeds need (items 1 and 3 are two).
10. Tests first (seen red where they pin a change; rounds, never wall clock); the four-tier bus-hazard rule stands for
   SCD30 and BMP3XX. Docs: the parts that state these behaviours, current state, fewest lines; the LED's "no failure
   path" reason as one spec line; UART changelog untouched (no UART change).

## Never
Never remove a feature beyond the items above (common_r1); never change a wire byte, a stored format (beyond the LED
chunk's removal) or a `/status` byte (beyond the LED errcount entry). Never edit `ext/`; never read `arduino/`; never
open `/root/.claude/`; no hardware. No `gc.collect()`, no new delay. Credential filter as common_r1 says (Wi-Fi code:
print only identifier matches). Scratch only under `S/u35r/r5/ftmp_ub/`.

## Checks and hand-back
Touched test files at both GC stages while fixing; `lint_direct.sh`; three mypy passes; then the gate under
`S/u35/lead/heavy.lock` holding `ub` (fsync may hold it: wait while it exists; `rm` it, literal path, own command).
Sizes and `imageFreeBytes` against 8f04f2f1. One commit; budget about 3 % of the week. Hand back by 06:00 UTC:
`S/u35r/r5/HANDBACK_UB.md` (at most 40 lines, as common_r1 says, need against cost per changed operation), your
commit, one line per headline result, and last "nothing of mine is running".
