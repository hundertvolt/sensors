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

Two more real findings from re-running after the above fixes landed:
- `harness.py`'s `tail_log()` fix above was too narrow - it only retried the initial `open()`,
  but the same transient error can also hit the very first `readline()` on an already-opened port
  (a real `hard_reset()`'s DTR pulse returns before the USB CDC-ACM device has actually finished
  re-enumerating). Widened to retry the whole open+read attempt within a bounded 10s grace window
  from when `tail_log()` was first called, confirmed fixed (`test_boot_import_mechanism_actually_
  boots_the_real_system` now passes reliably).
- `bmp3xx_plausibility_read.py` had the exact same missing-`cfgmgr`-initialization bug as
  `sgp40_fram_backup_restore.py` (`BMP3xx_Reader._init_bmp()` also reads its own config via
  `cfgmgr.get_int_values()` as its first step) - confirmed reproducible 3/3 in isolation
  (not the intermittent flakiness it first looked like), then confirmed root cause directly with
  `debug=5` diagnostics ("Error reading config data!" every cycle). This one was masked for
  longer than the SGP40 case: the script's own final `task.cancel()` cleanup ran unconditionally
  either way, so the CancelledError-swallowing bug (fixed in the same earlier pass) produced an
  identical-looking test failure that hid this real root cause underneath it until that first bug
  was fixed and this one became visible on its own. Fixed the same way: prime `cfgmgr.valid`/
  `_cache` directly instead of calling `setup()`.

**Status: GREEN.** Full flash suite: 15 passed, 4 skipped (2 long-soaks + the flash-cycle test,
correctly gated behind opt-in flags; the memory-stress soak also gated behind --run-long-soak).
0 failed. Confirmed via a clean full re-run after all fixes above landed together.

## Phase 2 - bench tier (minus hotspot role-reversal)

First run (before fixes): 20 failed, 17 passed, 5 skipped. Two distinct root causes, both now
addressed:

1. **`iptables` not installed on this bench Pi4** (`sudo: iptables: command not found`) - a real
   gap in `env --tier bench` provisioning, never previously exercised on a Raspberry Pi OS bench
   host. Fixed: added `ensure_iptables()` to `toolchain/setup_toolchain.py`, matching the existing
   `ensure_network_manager()`/`ensure_iproute2()` pattern exactly, called from the same bench-tier
   branch of `run_env()`. Installed directly on this bench machine to unblock testing rather than
   re-running the full (~8min) `env --tier bench` provisioning flow just for one package.
2. **The WiFi reconnection flakiness (see tests_hardware/README.md's "First real run" list, now
   substantially updated) cascaded into a long chain of unrelated-looking failures** once the DUT
   fell back to hotspot mode mid-run: every subsequent bench test depending on the session-scoped
   `dut_ip` fixture then failed with `ConnectionRefusedError`/`OSError: No route to host`, since
   that IP no longer routed to the DUT once it left STA mode. Not a test bug - a real consequence
   of the underlying flakiness. Spent focused effort here (see tests_hardware/README.md) since the
   project owner explicitly asked for this to be chased down this session:
   - Reproduced via 8 fresh `hard_reset()` trials with concurrent `iw dev wlan0 station dump`
     polling: **6/8 fell back to hotspot** (worse than the previously documented 2/5).
   - A live `tcpdump port 67 or port 68` capture spanning a full failure cycle showed **zero DHCP
     packets** - directly overturning the prior "DHCP/L3-timing" hypothesis.
   - AP-side station entry stays present throughout (never removed) with flat `rx bytes` but a
     periodically-resetting `inactive time`, consistent with management-frame-only activity that
     never reaches DHCP - revised hypothesis: a WPA2 association/handshake-adjacent issue on rapid
     reconnects, in the same problem area as the already-fixed `wifi-sec.pmf disable` fragility
     (`dev_legacy/README.md`), not a new `src/` bug. Full account and reasoning for not touching
     `src/asy_wifi_service.py` blind: `tests_hardware/README.md`'s updated "First real run" list.
   - Recovered a stable connection this session by cycling the bench AP profile
     (`nmcli connection down/up br0-wifi-ap`) before the next `hard_reset()` - one data point, not
     confirmed reliable.

Also added a bounded `hard_reset()` retry to the `dut_ip` fixture itself (mirroring `joined_hotspot`'s
own established recovery pattern) - a single unlucky boot was cascading into ~15 unrelated bench
tests failing/erroring, which has nothing to do with what any of them actually check.

**Further WiFi investigation, prompted directly by the project owner** ("I don't remember ever
seeing this on real WiFi - check legacy, check if this is new, check docs/forums"): confirmed the
legacy deployed code (`python/CommonDrivers/async_connect.py`) has the exact same connect/poll/
streak shape - not a refactor-introduced bug. Checked the pinned MicroPython C source directly:
a **soft** reset never re-touches the CYW43 chip at all (`cyw43_init()` runs once, before the
soft-reset loop in `ports/rp2/main.c`) - real, but not what this tier's `hard_reset()` uses, which
does genuinely power-cycle the chip via `WL_REG_ON` (confirmed in `cyw43_ctrl.c`). Web research
found this is a recognized *class* of upstream Pico W/cyw43 issue, including a maintainer-fixed
timing bug in `cyw43_do_ioctl()`'s own polling (`raspberrypi/pico-sdk#2186`) triggered by rapid
repeated connect attempts. Left open as a concrete, testable next step: this bench's own chatty
per-cycle debug logging under a single-threaded asyncio scheduler, contending with
`_poll_sta_connect_status()`'s tight ~5s budget, is a plausible jitter source matching that known
driver sensitivity - worth an A/B test at lower debug verbosity, not confirmed. Full account:
tests_hardware/README.md's "First real run" list.

Status: re-running the bench suite (minus hotspot role-reversal) now that both root causes are
addressed, to see what genuinely remains.

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
