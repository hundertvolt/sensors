# REAL_HARDWARE_RUN_LOG.md

Live progress log for the first real-hardware run of `tests_hardware/` (see
`REAL_HARDWARE_HANDOFF.md`, `tests_hardware/README.md`). Temporary, same lifecycle as the other
hardware-tier planning docs - fold anything permanently true into `SPECIFICATION.md`/`BACKLOG.md`/
`tests_hardware/README.md` and delete this once the real-hardware pass is done and verified.

Go-ahead given directly by the project owner in-conversation on 2026-09-01. Session running
locally on the bench Pi4, board already flashed with production firmware, `br0-wifi-ap` bench
bridge already provisioned. Scope this session: flash tier + bench tier (including hotspot
role-reversal) + a bounded soak window + a global lint/typecheck/unit-test regression pass. Manual
tests and the flash-cycle re-provisioning test are explicitly out of scope this session.

## Status: IN PROGRESS

## Phase 1 - flash tier

First real run surfaced a systemic root cause, not scattered unrelated bugs: `tests_hardware/`
was written by a cloud session with zero hardware attached, and its `device_scripts/*.py`
hardcoded the *deployed wozi production* pin wiring (I2C1=GPIO19/18, SCD30 on I2C0/GPIO8, BMP3xx
on I2C1, FRAM SPI0 CS=GPIO1/MB85RS64V/8KB) instead of *this specific dev bench's* real wiring,
which is different and fully documented in `dev_legacy/README.md`'s own wiring table (verified
against the physical board by the project owner previously). Confirmed directly against the
board's own live `main.py` (already correctly bench-wired) and real `i2c.scan()`/SPI RDID probes
before touching anything. Fixed every affected device script (bmp3xx/scd30/sgp40 pin numbers,
FRAM CS=GPIO5 + MB85RS2MTA/256KB).

Also found and fixed, all in test-only code (`tests_hardware/`), none in `src/`:
- `harness.py`'s `run_isolated()`/`exec()` error messages only included `stderr`, dropping the
  real MicroPython traceback (which lands on `stdout` over the raw-REPL channel) - every real
  failure was showing up as "failed (exit 1):" with nothing after it. Fixed to include both.
- Several device scripts' own `task.cancel(); await task; except Exception: pass` cleanup never
  actually caught the CancelledError it was written for - confirmed directly that MicroPython's
  `asyncio.CancelledError` subclasses `BaseException`, not `Exception` (matching CPython 3.8+,
  and already documented in SPECIFICATION.md Part F.2 - just missed when these scripts were
  written blind). Fixed 5 device scripts (bmp3xx/scd30 x2/sgp40 x2) to catch
  `(asyncio.CancelledError, Exception)`.
- `float_boundary_2pow24.py`'s own precision-loss assertion compared `coerced == float(above)`,
  but `float(above)` is itself recomputed on the same real single-precision hardware, so it can
  never distinguish "precision lost" from "not lost." Fixed to compare against the exact
  mathematical integer instead.
- `sgp40_fram_backup_restore.py` never initialized `reader.cfgmgr` at all (no `setup()`, no
  primed cache) - confirmed directly (real hardware printed "SGP40 Error reading config data!"
  every cycle) that this made a backup structurally impossible to ever trigger, regardless of
  wait time; the original ~90s timeout was never actually the bottleneck. Fixed by priming
  `cfgmgr.valid`/`_cache` directly (dev_legacy/README.md's own documented no-real-flash-write
  pattern), not by calling the real `setup()`.
- `test_toolchain_flash_boot.py`'s idempotency test used a 300s timeout for `env --tier flash`;
  confirmed directly that a real re-run on this bench's Pi4 takes ~481s (`run_setup()` always
  does a full re-verify: fresh git fetch + full picotool rebuild-from-scratch + full
  mpy-cross/Unix-port/firmware freeze-verify, never a fast no-op short-circuit - worth knowing
  generally, not just for this test). Bumped to 1200s.
- **Flagged, not fixed** (a real `src/asy_fram_manager.py` interaction, needs a project-owner
  call): a chunk `read()` cannot complete while the real chip is write-protected, because
  `_AsyBaseFramChunk._read_chunk()`'s own busy/idle status-byte protocol needs to *write* a
  transient busy marker before reading - which the hardware write-protect blocks too. Confirmed
  directly on real hardware. `fram_write_protect_roundtrip.py` now only reads back the
  blocked-write's data after clearing protection again (which cannot itself alter stored bytes),
  preserving the test's intent without depending on this behavior either way.

Status once these fixes land: re-running the full flash suite to confirm - see below.

## Phase 2 - bench tier (minus hotspot role-reversal)
(pending)

## Phase 3 - hotspot role-reversal
(pending)

## Phase 4 - WiFi reconnection flakiness investigation
(pending)

## Phase 5 - bounded soak window
(pending)

## Phase 6 - global lint/typecheck/unit-test regression pass
(pending)

## Phase 7 - wrap-up
(pending)
