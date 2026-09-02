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
2. **The WiFi reconnection flakiness (see tests_hardware/README.md's "Known assumptions and open findings" list, now
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
     `src/asy_wifi_service.py` blind: `tests_hardware/README.md`'s "Known assumptions and open
     findings" list.
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
tests_hardware/README.md's "Known assumptions and open findings" list.

**Fifth, foundational real finding** (found after the project owner directly pushed back on the
WiFi writeup above - "are you sure you didn't miss something", then asked for legacy/forum
comparison, which led here): `dut_ip`'s own `hard_reset()`-retry fix (above) was itself built on a
single `board.exec()` call, which is **not safe either**. Confirmed empirically on real hardware
(an A/B test: bare `exec`, `exec ... soft-reset`, and `run <script> soft-reset` all left the board
completely silent afterward) and against the pinned MicroPython C source: entering raw REPL sets
`pyexec_mode_kind` to `RAW_REPL`; the soft-reset boot path only re-runs `main.py` when that's
`FRIENDLY_REPL`. A trailing `soft-reset` returns to an idle friendly-REPL *prompt* - it does not
retroactively make the already-completed soft-reset's boot sequence re-check that condition, so
`main.py` stays stopped. **This directly answers, the wrong way, this tier's own long-standing
open question** (`harness.py`'s `run_isolated()` docstring's "NEEDS VERIFICATION ON FIRST REAL
RUN" note, and tests_hardware/README.md's corresponding list item) - both assumed a trailing soft-reset
"hands the board back to its normal auto-booted state"; it does not. Harmless everywhere else in
this tier (every isolated-driver test builds its own driver objects directly, never depending on
`main.py` staying up afterward) but exactly wrong for `dut_ip`'s own purpose. Only a genuine
`hard_reset()` (a real `machine.reset()`, confirmed throughout this session to reliably resume
normal auto-boot) is safe. Rewrote `dut_ip` to never call `board.exec()`/`run_isolated()` while
expecting `main.py` to keep running: it passively watches (`board.tail_log()`) for the real
"WLAN connection established"/hotspot-fallback log lines, and the one `board.exec()` call still
needed to actually read the IP back out is now always immediately followed by a real
`hard_reset()` to resume operation, never left dangling. See `tests_hardware/conftest.py`'s own
`dut_ip` docstring for the full, current account (now four documented real findings deep).

**Session paused here at the project owner's request, mid-verification of this fifth fix** - the
corrected `dut_ip` design has NOT yet been confirmed working end-to-end on real hardware (the
verification run in progress when the pause was requested was stopped, not completed). The board
was left on a clean, real `hard_reset()` (confirmed exit 0, no leftover mpremote/pytest processes)
before ending the session - a safe, known-good resting state for whoever resumes next, not a
mid-test or mid-diagnostic state.

## Phase 4 - WiFi reconnection investigation - RESOLVED (mostly)

Session resumed, `dut_ip` fixture fix confirmed working (Step 1 of the resume plan below), then
ran `WIFI_RECONNECT_INVESTIGATION.md`'s own Step 3 A/B test exactly as designed: 10 control trials
(plain `hard_reset()`) vs. 10 treatment trials (`bench.kick_all_stations()` first). **Result: 10/10
control fell back to hotspot; 10/10 treatment connected cleanly.** Decisive confirmation of the
AP-side stale-station-table hypothesis. Fixed: `BenchBridge.kick_all_stations()` wired into every
`hard_reset()` call site expecting a real reconnect (`dut_ip`, `joined_hotspot`'s recovery
fallback, `test_real_sta_connect_reaches_established_after_a_hard_reset`).

While confirming this at scale, found a second, genuinely different mechanism: `test_network_
resilience.py`'s `ap_down()`/`ap_up()`-based outage/flap tests still failed even with a clean
AP-side station table. Root cause, confirmed both by direct real-hardware evidence (`arping`
getting zero responses while `iw station dump` showed continuous "associated: yes" for hundreds of
seconds) and by the project owner's own prior field observation ("the WiFi module rather tries to
resolve connectivity internally... isconnected stays True for long"): the CYW43 firmware/lwIP
stack can silently mask a real link disruption from `wlan.isconnected()`/`wlan.status()` entirely -
confirmed as a well-documented, long-standing (open since MicroPython v1.19.1, 2022), not
project-specific upstream characteristic (`micropython/micropython#9455`/`#9505`/`#18797`, an
independent field account at alanedwardes.com). `asy_wifi_service.py`'s own `_wlan_isconnected_
or_false()` has no independent reachability check, so `_on_sta_disconnected()`'s retry cannot fire
if the firmware never reports the disconnect. **Not fixed in `src/`** - flagged as a real
architectural question for the project owner (whether to add an independent reachability check).
Mitigated at the test level only, per the project owner's own explicit choice: both tests now
recover via a real `hard_reset()` if the graceful wait times out (matching `joined_hotspot`'s own
established pattern), but still re-raise afterward so the real limitation stays visible as a test
failure - confirmed working exactly as designed on real hardware.

Full evidence trail for both findings: `WIFI_RECONNECT_INVESTIGATION.md`'s own "RESOLVED" section
at the top of that file.

## Phase 4b - is_reachable() harness bug, malicious-value REST tests, captive-portal merge

A later session found and fixed a genuinely serious harness bug while chasing an unrelated
`test_real_reboot_sequencing_via_rest_completes_cleanly` failure: `Board.is_reachable()` is built on
`mpremote exec`, and mpremote's own `enter_raw_repl()` unconditionally sends Ctrl-C plus, by
default, a real Ctrl-D `machine.soft_reset()` before running anything - polling it against a live,
already-running system (as that test's own `wait_until(lambda: not board.is_reachable(), ...)` did)
was self-resetting the board's live heap on every single poll, wiping the very `reset_timer` state
being waited on. Fixed with a new, genuinely passive `Board.is_device_present()` (opens/closes the
serial port, sends nothing) for any future poll against a live system - `is_reachable()` stays
`mpremote`-based deliberately, since some callers (flash tier's own connection-stability test) are
specifically testing that mechanism.

Added `test_garbage_ssid_via_rest_config_is_handled_gracefully` (a real, unreachable SSID pushed via
REST) plus an isolated device script confirming `network.country()`/`network.hostname()` degrade
gracefully on bogus values. Building the SSID test's own hotspot-fallback recovery path surfaced
several real `bench_control.py` bugs, all fixed: `ap_down()` wasn't idempotent (broke retries),
`join_dut_hotspot()` left a stale connection profile behind on a failed attempt (broke retries
differently and more confusingly on the next try), and joining a just-activated hotspot could race
its own beacon interval (fixed with a new `is_ssid_visible()` real-scan check). The test's own
final check then went through a long, expensive false trail (see `WIFI_RECONNECT_INVESTIGATION.md`'s
own new top section for the full account) before the real bug was found: it read a `"Mode"` field
from `GET /networking`, which never has that field - `"Mode"` only exists under `GET /status`'s
nested object. Fixed; the test now passes in ~150s consistently, not 15+ minutes then a failure.

Also merged `claude/captive-portal-hotspot-redirect` (PR #53, per the project owner's own request,
gated on that PR's CI being green first - confirmed green before merging): adds
`AsyConnTime.is_hotspot_active()` and wires it into `WebserverService`'s static-route fallback so a
captive-portal OS probe gets a 302 redirect instead of a 404 while the DUT is its own hotspot. No
file overlap with this branch's own `tests_hardware/` work; merged cleanly. `scripts/lint.sh`/
`scripts/typecheck.sh` confirmed clean post-merge; `scripts/test.sh` (full mock suite) and the PR's
own two new real-hardware bench tests (`test_hotspot_role_reversal.py`'s
`test_nonsense_path_redirects_to_root_over_the_hotspot_link`/`test_put_to_nonsense_path_is_405_
not_a_redirect_over_the_hotspot_link`, never run on real hardware before this) still pending -
continue at "Next session should start here" below.

## Next session should start here

1. Re-run the full bench suite (`scripts/run_bench_hardware_suite.sh -v -k "not
   hotspot_role_reversal"`) now that the WiFi fixes are in, and update this log with the real
   pass/fail result - Phase 2 is not yet closed out with a clean run (it was last attempted before
   these fixes landed).
2. Remaining phases, still fully pending, in the order the original plan set out:
   - Phase 3: hotspot role-reversal (`bench/test_hotspot_role_reversal.py`), run alone and watched
     closely per `REAL_HARDWARE_HANDOFF.md`'s own suggested order - highest-risk file this tier
     has (can strand the board in `_PHASE_DEACTIVATED` until a real hard_reset(), though
     `joined_hotspot`'s own fixture teardown already recovers from that automatically).
     `BENCH_AP_PASSWORD` was obtained and used earlier this session but not persisted anywhere
     (per the credential-handling hard rule) - it will need to be re-obtained from the project
     owner again if the real-credential-handoff test's own coverage is wanted.
   - Phase 5: a bounded soak window (`--run-long-soak --long-soak-seconds 1200 -k "not
     ticks_ms_real_2pow30_rollover"` per the plan agreed at the start of this session - the
     rollover test can't honor a short window at all, see that plan for why).
   - Phase 6: a global regression pass (`scripts/lint.sh`, `scripts/typecheck.sh`, `scripts/
     test.sh`) to confirm none of this session's `tests_hardware/`/`toolchain/setup_toolchain.py`
     changes broke anything in the existing mock/twin suite.
   - Phase 7: wrap-up - update `tests_hardware/README.md`/`REAL_HARDWARE_HANDOFF.md`'s own status
     once a genuinely clean pass exists, but do not unilaterally delete/migrate the temporary
     planning docs (`HARDWARE_TEST_PLAN.md` etc.) without the project owner's sign-off, per
     `REAL_HARDWARE_HANDOFF.md`'s own close-out instructions. `WIFI_RECONNECT_INVESTIGATION.md`
     itself can very likely be folded into `tests_hardware/README.md`/deleted at that point too,
     now that its own questions are resolved - confirm with the project owner first.
3. All fixes so far are committed and pushed to `claude/digital-twin-oserror-7y00lb`. No PR opened
   yet - better to open one once Phase 2 is genuinely closed out with a clean bench-tier run, not
   before.
