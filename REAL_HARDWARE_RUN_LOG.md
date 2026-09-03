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

## Current physical board state (as of 2026-09-02, end of this session)

**Not a resting/idle state — read before touching the board.** The device is currently running
`build/firmware-dev-bench.uf2` (a scratch build from `dev_legacy/README.md`'s own recipe, not
committed — trivially rebuildable from that doc), with the dev-bench entry script (embedded in full
in `dev_legacy/README.md`) running **mounted** via `mpremote run` (per that doc's own intent), not
flashed. No watchdog is armed. WiFi has no saved credentials (fresh erase) and is running its own
hotspot, SSID `SensorNode`. This is the state that confirmed the mounted-entry-script recipe itself
runs cleanly — left running rather than torn down, so the next session can inspect it live if
useful, but it is a debug/scratch state, not anything to build on directly. Re-flash real `wozi`
production firmware (`uv run scripts/build_firmware.py wozi` + the normal flash procedure) before
resuming any bench-tier `pytest` work that expects the real production system.

## Open, not yet resolved

- **Real per-variant pin/module support for `scripts/build_firmware.py`** (`BACKLOG.md`'s
  "per-variant `sensortask-*.py` generator" item) — until this exists, `scripts/build_firmware.py`
  can't be validly used against this bench at all; use `dev_legacy/README.md`'s mounted-entry-script
  recipe instead. Not new work created by this session — an existing, already-tracked gap that this
  session's cleanup traced two false "bugs" back to.
- **Captive-portal redirect on real hardware — never actually verified under a valid
  configuration.** Full detail and next steps are the durable record at `BACKLOG.md`'s open
  questions list and `tests_hardware/README.md`'s corresponding entry. Closing it needs extending
  the dev bench's own entry script with `frozen_html`/`static_mount` so the redirect can be
  exercised on this bench — wozi is never physically flashed, so this is the real verification, not
  a placeholder for one.

## Next session should start here

**Current priority, per the project owner: `DEV_HARDWARE_BASELINE_PLAN.md`** (repo root) — building
and physically flashing one real, fully-reviewed dev-native firmware variant, the named prerequisite
for the per-variant generator work. Read that plan first; it supersedes item 1 below for whichever
firmware actually gets flashed next (its own §4a is code work doable ahead of the physical session,
§4b is the real-hardware sequence). The bench-tier `pytest` re-run items 2-4 below are a separate,
still-valid track (that tier drives sensors via its own scripts, independent of which application is
flashed — see the plan's own §2) and can proceed on whatever firmware is currently on the board.

1. Before any bench-tier `pytest` work *on the existing tier* (separate from the plan above): re-flash
   real `wozi` production firmware (see "Current physical board state" above — the board is
   currently running dev-bench scratch firmware, not production).
2. Re-run the full bench suite (`scripts/run_bench_hardware_suite.sh -v -k "not
   hotspot_role_reversal"`) — the bench tier is not yet closed out with a clean run since the WiFi
   fixes landed.
3. Remaining work, in order:
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
4. All fixes so far are committed and pushed to `claude/digital-twin-oserror-7y00lb`. No PR opened
   yet — better to open one once the bench tier is genuinely closed out with a clean run.
