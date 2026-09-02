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
- **Selectively pulled in a concurrent session's fixes without its documentation.** A parallel
  session pushed three commits: two pure code/CI fixes (a `tests_scripts/test_build_firmware.py`
  call-site fix; a real `scripts/build_firmware.py` bug where wiping `mpy-cross/build/` without
  rebuilding it broke `firmware-build-verify` in CI) — both cherry-picked in directly — and one
  investigation finding (the digital-twin integration test proves `src/`'s `is_hotspot_active()`/
  `_serve_static()` logic is correct end-to-end, narrowing the captive-portal 404 to two candidates)
  that only added its findings to a pre-consolidation, now-superseded version of this file. That one
  was *not* cherry-picked as a commit — its substance was folded directly into `BACKLOG.md`'s open
  questions list, item 7, instead, to avoid reintroducing the bloat this file was just cleaned of.
- **A follow-up debugging session found and resolved the real cause of the earlier "boot loop"
  boot loop** (the one namedropped two bullets up as "self-resolved... never reproduced again") —
  it *did* recur, reproducibly, and got fully root-caused this time. Full account:
  `dev_legacy/README.md`'s "Current bench state" (2026-09-02) and `BACKLOG.md`'s open questions list,
  item 8. Short version: a stale, undocumented `/main.py` was found on the device's real flash
  filesystem (deleted, along with a full `picotool erase -a` at the project owner's explicit
  direction); `scripts/build_firmware.py` was then found to have zero awareness of this dev bench's
  own real pin wiring (it only ever encodes `wozi`'s production pins); once patched with this
  bench's own confirmed-correct wiring (verified directly via `machine.I2C.scan()` + chip-ID
  readback, matching `dev_legacy/README.md`'s existing wiring table exactly) it still reproducibly
  failed under `scripts/build_firmware.py`'s own autostart chain specifically (SCD30/SGP40 sharing
  i2c1 fail under the full 18-task system, though they work perfectly alone) — while the *identical*
  wiring via `dev_legacy/README.md`'s own documented mounted-entry-script recipe ran the full system
  cleanly for 100+s, zero errors. That discrepancy (frozen autostart chain vs. mounted-entry-script)
  is the one thing left unresolved — tracked as `BACKLOG.md` item 8.

## Current physical board state (as of 2026-09-02, end of this session)

**Not a resting/idle state — read before touching the board.** The device is currently running
`build/firmware-dev-bench.uf2` (a scratch build from `dev_legacy/README.md`'s own recipe, not
committed — trivially rebuildable from that doc), with the dev-bench entry script (embedded in full
in `dev_legacy/README.md`) running **mounted** via `mpremote run` (per that doc's own intent), not
flashed. No watchdog is armed. WiFi has no saved credentials (fresh erase) and is running its own
hotspot, SSID `SensorNode`. This is exactly the state that proved `BACKLOG.md` item 8's fix works —
left running rather than torn down, so the next session can inspect it live if useful, but it is a
debug/scratch state, not anything to build on directly. Re-flash real `wozi` production firmware
(`uv run scripts/build_firmware.py wozi` + the normal flash procedure) before resuming any bench-tier
`pytest` work that expects the real production system.

## Open, not yet resolved

- **`scripts/build_firmware.py`'s autostart chain vs. the mounted-entry-script recipe — see above
  and `BACKLOG.md` item 8.** This is now the top priority for whoever wants
  `scripts/build_firmware.py` usable for real dev-bench testing again (the mounted-script recipe is
  a full functional workaround in the meantime, just not what a real deployable image needs).
- **Captive-portal redirect returns 404 instead of the expected 302 in real hotspot mode** — full
  detail, investigation candidates, and the diagnostic pitfall already hit once (don't use
  `mpremote exec()` to inspect live state) are now the durable record at **BACKLOG.md's open
  questions list, item 7** and `tests_hardware/README.md`'s corresponding entry. Still open; not
  touched further this session.

## Next session should start here

1. Decide which is the priority: `BACKLOG.md` item 8 (`scripts/build_firmware.py`'s autostart-chain
   discrepancy) or item 7 (captive-portal 404) — both are real, both are open, neither blocks the
   other. Check both entries for whether either has been resolved by a concurrent session first.
2. Before any bench-tier `pytest` work: re-flash real `wozi` production firmware (see "Current
   physical board state" above — the board is currently running dev-bench scratch firmware, not
   production).
3. Re-run the full bench suite (`scripts/run_bench_hardware_suite.sh -v -k "not
   hotspot_role_reversal"`) — the bench tier is not yet closed out with a clean run since the WiFi
   fixes landed.
4. Remaining work, in order:
   - Hotspot role-reversal (`bench/test_hotspot_role_reversal.py`), run alone and watched closely
     per `REAL_HARDWARE_HANDOFF.md`'s suggested order — highest-risk file in this tier (can strand
     the board in `_PHASE_DEACTIVATED` until a real `hard_reset()`, though `joined_hotspot`'s own
     fixture teardown already recovers from that automatically). `BENCH_AP_PASSWORD` will need to be
     re-obtained from the project owner (not persisted anywhere, per the credential-handling hard
     rule) if the real-credential-handoff test's coverage is wanted.
   - A bounded soak window (`--run-long-soak --long-soak-seconds 1200 -k "not
     ticks_ms_real_2pow30_rollover"` — the rollover test can't honor a short window at all).
   - A global regression pass (`scripts/lint.sh`, `scripts/typecheck.sh`, `scripts/test.sh`) to
     confirm none of this branch's `tests_hardware/`/`toolchain/setup_toolchain.py` changes broke
     the existing mock/twin suite.
   - Wrap-up: update `tests_hardware/README.md`/`REAL_HARDWARE_HANDOFF.md`'s status once a
     genuinely clean pass exists, but don't unilaterally delete/migrate the temporary planning docs
     without the project owner's sign-off.
5. All fixes so far are committed and pushed to `claude/digital-twin-oserror-7y00lb`. No PR opened
   yet — better to open one once the bench tier is genuinely closed out with a clean run.
