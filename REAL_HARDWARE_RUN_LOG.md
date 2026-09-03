# REAL_HARDWARE_RUN_LOG.md

Live progress log for the first real-hardware run of `tests_hardware/` (see
`REAL_HARDWARE_HANDOFF.md`, `tests_hardware/README.md`). Temporary, same lifecycle as the other
hardware-tier planning docs — fold anything permanently true into `SPECIFICATION.md`/`BACKLOG.md`/
`tests_hardware/README.md` and delete this once the real-hardware pass is done and verified. This
file intentionally does not re-narrate resolved findings — every permanent fact that came out of
this run (root causes, fixes, gotchas, open architectural questions) has already been migrated to
the durable doc that owns it; see the pointers below rather than this file's own git history.

## Status: IN PROGRESS

Running locally on the bench Pi4 against `br0-wifi-ap`. Scope: flash tier + bench tier (including
hotspot role-reversal) + a bounded soak window + a global lint/typecheck/unit-test regression pass.
Manual tests and the flash-cycle re-provisioning test are out of scope.

## What's done, and where the durable facts live now

- **Flash tier: GREEN.** 15 passed, 4 skipped (opt-in soaks/flash-cycle tests), 0 failed. Bugs found
  along the way (wrong bench pin wiring in several `device_scripts/*.py`, a swallowed
  `CancelledError` in cleanup code, missing `cfgmgr` initialization masking two sensor tests) were
  all in test-only code and are fixed — see git history if the specific fixes matter, nothing
  permanent to carry forward from them.
- **Bench tier WiFi reconnection flakiness — root-caused, fixed, and documented in
  `tests_hardware/README.md`'s "Known assumptions and open findings"**: a hard-reset-then-reconnect
  cycle used to fall back to hotspot mode intermittently. Two distinct real mechanisms, both now
  captured there in full (evidence, fix, and remaining caveats) rather than here:
  1. AP-side stale station-table entries — fixed with `BenchBridge.kick_all_stations()`, wired into
     every `hard_reset()` call site expecting a real reconnect.
  2. The CYW43 firmware/lwIP stack silently masking a real link disruption from
     `wlan.isconnected()` — a real, upstream, not-project-specific characteristic. Whether
     `asy_wifi_service.py` should gain an independent reachability check is now tracked as
     **BACKLOG.md's open questions list, item 6** (not decided).
- **`Board.is_reachable()`/`exec()` self-resetting a live system while being polled — fixed,
  documented in `tests_hardware/README.md`**: `mpremote`'s `enter_raw_repl()` sends a real Ctrl-D by
  default, wiping the very state a poll was trying to observe. `Board.is_device_present()` is now
  the passive alternative for liveness polling.
- **`test_garbage_ssid_via_rest_config_is_handled_gracefully`'s months-long-feeling flakiness —
  root-caused as a test bug, not hardware**: it read a `"Mode"` field from the wrong endpoint.
  Fixed; full lesson (verify the check before chasing a hardware explanation) is now in
  `tests_hardware/README.md` as standing practice.
- **`claude/captive-portal-hotspot-redirect` (PR #53) merged**, CI green first. Adds
  `AsyConnTime.is_hotspot_active()` wired into `WebserverService`'s static-route fallback
  (`SPECIFICATION.md` Part A.5).
- **First real flash+boot of `scripts/build_firmware.py`'s own output — a real build bug found and
  fixed, now documented in `SPECIFICATION.md` Part B.11**: the custom manifest silently dropped
  `ports/rp2/modules/rp2.py`, which `_boot.py` needs to mount the filesystem at all. Fixed
  (`rp2.py` is now copied into the staging directory); also added an `mpy-cross` build-dir clean
  before every build so a build never depends on stale artifacts.
- A transient I2C/SPI hiccup (all sensors + FRAM briefly unresponsive right after a reflash,
  triggering a WDT boot-loop) self-resolved on a later flash and was never reproduced again — not
  chased further, no permanent fact to record.
- **A stale, undocumented `/main.py` was found on the device's real flash filesystem and deleted**
  (full `picotool erase -a` at the project owner's explicit direction) — it had been auto-starting
  via MicroPython's filesystem-fallback boot path, confusing an earlier session's "no-autostart"
  diagnostic build into looking like it had no effect. Full account: `dev_legacy/README.md`'s
  "Current bench state".
- **Real-hardware verification status for the captive-portal redirect and for
  `scripts/build_firmware.py`'s autostart chain on this bench — cleaned up 2026-09-03, see
  `BACKLOG.md`'s "per-variant `sensortask-*.py` generator" item for the full account.** Two earlier
  findings (a 404 instead of the expected 302 on `GET /generate_204`; a real `errno=11` I2C failure
  under the full system) both traced back to the same invalid test: `scripts/build_firmware.py`
  only ever encodes `wozi`'s hardcoded production pins, and no per-variant equivalent exists yet, so
  an earlier session worked around that by scratch-patching wozi's own `sensortask_wozi.py` with
  this bench's pin numbers and flashing it through wozi's own autostart chain anyway — never a valid
  test of either target. Both findings are dropped as noise, not tracked as bugs. The captive-portal
  redirect itself remains genuinely unverified on real hardware (this bench's own working
  mounted-entry-script recipe doesn't wire up `frozen_html`/`static_mount` at all, so it's never
  actually exercised that path) — closing that gap needs extending the entry script with those two
  things and testing on this bench, not a re-run of the mismatched build. Per CLAUDE.md's hard rule,
  wozi is never physically flashed — a passing dev-bench result is the real, complete verification
  for this, not a stand-in for one.

**Update, same day: both real findings this cleanup pointed at (`DEV_HARDWARE_BASELINE_PLAN.md`'s
own §4b) are now closed for real.** `src/sensortask_dev.py` (the real, hand-written dev-native
variant this cleanup named as the actual gap) exists, and a real flash+boot found and fixed one
more genuine bug along the way: `scripts/build_firmware.py`'s frozen `_boot.py`→`<device>_boot.py`
chain never returns, so rp2 never reaches `mp_usbd_init()` — USB never enumerated after any real
hard reset, for any device, confirmed against the pinned v1.28.0 source and independently via
`micropython/micropython#15230`. Fixed by freezing each device's boot entry under the literal name
`"main.py"` instead (`SPECIFICATION.md` Part B.11/F.1). With that fixed, a real flash of
`scripts/build_firmware.py dev` came up clean: USB reachable immediately, 6.5 minutes of real
stability with zero errors, all three sensors reading plausible real values, and a real
`GET /generate_204` → genuine `302`/`Location: /`. See "Current physical board state" below for the
board's current, real state.

## Current physical board state (as of 2026-09-03)

**Not a resting/idle state — read before touching the board.** The device is currently running
`build/firmware-dev.uf2` — the real, promoted `src/sensortask_dev.py` via
`boot_entry/dev_boot.py`, **flashed for real** (`scripts/build_firmware.py dev` + `picotool load`),
watchdog armed, same as a real deployed unit. WiFi has no saved credentials (fresh erase) and is
running its own hotspot, SSID `SensorNode`. Confirmed clean over a real 6.5-minute stability window
(`SysUptime` climbing monotonically, zero real errors on any module), all three sensors reading
plausible real values, and the captive-portal redirect confirmed working (`GET /generate_204` → real
`302`). Left running rather than torn down, so the next session can inspect it live if useful.

## Open, not yet resolved

- **`tests_hardware/`'s flash + bench pytest tiers have not yet been re-run against this corrected
  build.** Expected to already pass (independent of which application is flashed — that tier drives
  sensors via its own scripts), but worth confirming rather than assuming
  (`DEV_HARDWARE_BASELINE_PLAN.md` §4b item 4).
- **Hotspot role-reversal test + a bounded soak window** — both still outstanding
  (`DEV_HARDWARE_BASELINE_PLAN.md` §4b item 5).

## Next session should start here

**`scripts/build_firmware.py dev` is now the real, confirmed-working way to build/flash for this
bench** (2026-09-03) — `wozi` is never physically flashed (CLAUDE.md's hard rule); don't re-flash
`wozi` here. The board is already running this build (see "Current physical board state" above), so
bench-tier work can proceed without re-flashing first.

1. Re-run the full bench suite (`scripts/run_bench_hardware_suite.sh -v -k "not
   hotspot_role_reversal"`) — the bench tier is not yet closed out with a clean run since the WiFi
   fixes landed.
2. Remaining work, in order:
   - Hotspot role-reversal (`bench/test_hotspot_role_reversal.py`), run alone and watched closely
     per `REAL_HARDWARE_HANDOFF.md`'s suggested order — highest-risk file in this tier (can strand
     the board in `_PHASE_DEACTIVATED` until a real `hard_reset()`, though `joined_hotspot`'s own
     fixture teardown already recovers from that automatically). `BENCH_AP_PASSWORD` will need to be
     re-obtained from the project owner (not persisted anywhere, per the credential-handling hard
     rule) if the real-credential-handoff test's coverage is wanted.
   - A bounded soak window (`--run-long-soak --long-soak-seconds 1200 -k "not
     ticks_ms_real_2pow30_rollover"` — the rollover test can't honor a short window at all).
   - ~~A global regression pass (`scripts/lint.sh`, `scripts/typecheck.sh`, `scripts/test.sh`) to
     confirm none of this branch's `tests_hardware/`/`toolchain/setup_toolchain.py` changes broke
     the existing mock/twin suite.~~ **Done** by a follow-up cloud session (2026-09-02): all three
     clean (`lint.sh`/`typecheck.sh` zero findings, `scripts/test.sh` full MicroPython Unix-port
     suite + `tests_scripts` all passing). Not a substitute for the bench-tier `pytest` run above —
     this only confirms the mock/twin suite, which has no bench dependency.
   - Wrap-up: update `tests_hardware/README.md`/`REAL_HARDWARE_HANDOFF.md`'s status once a
     genuinely clean pass exists, but don't unilaterally delete/migrate the temporary planning docs
     without the project owner's sign-off.
3. All fixes so far are committed and pushed to `claude/digital-twin-oserror-7y00lb`. No PR opened
   yet — better to open one once the bench tier is genuinely closed out with a clean run.
