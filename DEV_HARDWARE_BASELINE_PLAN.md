# DEV_HARDWARE_BASELINE_PLAN.md

Temporary planning doc, same lifecycle as `HARDWARE_TEST_PLAN.md`/`REAL_HARDWARE_HANDOFF.md`/
`REAL_HARDWARE_RUN_LOG.md` (see README.md's "Further reading"): delete once the baseline this
describes is built, flashed, and verified — migrating anything still permanently true into
`SPECIFICATION.md`/`BACKLOG.md`/`dev_legacy/README.md`/`tests_hardware/README.md` first, per this
repo's standing "resolved items move into a permanent doc, not silently dropped" convention.

## 1. Goal

Produce one real, fully-reviewed, physically flashed and verified firmware build for the dev
bench — a proper `src/`-quality per-variant sibling of `sensortask_wozi.py`, using the bench's own
confirmed-correct wiring, not the scratch/mounted workaround or the wozi-pins-on-dev-hardware
mismatch that produced two false "bugs" earlier on this branch (see BACKLOG.md's git history
2026-09-02/03, and CLAUDE.md's new standing hard rule on the wozi/dev relationship).

**Why this, and why now**: per the project owner, this is the explicit prerequisite for the next
piece of work — a session building the automated per-config-file (per-variant `sensortask-*.py`)
generator already tracked in BACKLOG.md. That generator needs one concrete, real, hardware-verified
example to generalize from and test against; wozi itself can never be that example, since it is
never physically flashed (CLAUDE.md hard rule) — only the dev bench is. This plan's scope is
**one hand-written variant, reviewed and tested to the same bar wozi itself was promoted at**
(SPECIFICATION.md Part D's checklist) — not the generator. Building the generator is deliberately
out of scope here; see §6. **Everything this plan produces is an interim, hand-written baseline —
it gets replaced once the automated per-variant generator lands. Don't over-invest in permanence.**

**Scope, confirmed by the project owner**: at this stage, this variant carries **exactly the same
three sensors wozi has — SCD30, BMP3xx, SGP40 — wired differently, nothing added or removed.**

## 2. Facts already established — don't re-derive these

- **Dev bench's confirmed-correct wiring** (`dev_legacy/README.md`'s wiring table, verified via
  direct `machine.I2C.scan()` + chip-ID/address readback): `i2c0` = BMP390 alone, pins (13, 12),
  address 0x77, chip_id=0x50. `i2c1` = SCD30 (0x61) + SGP40 (0x59) sharing the bus, pins (15, 14).
  SCD30 IRQ/RDY = GPIO11. Neopixel = GPIO18. SPI0 = pins (2, 3, 4). FRAM = 256KB MB85RS2MTA chip,
  CS = GPIO5 (**not** wozi's 8KB MB85RS64V at CS=1 — different chip, different `max_size`).
- **`scripts/build_firmware.py`'s `device` CLI argument does not select which application boots.**
  Confirmed by reading `build_stage_dir()`/`main()` directly: `device` only controls (a) which
  `html/definitions/<device>.json` must exist, and (b) which website content
  `scripts/build_website.sh <device> ...` stages. Every `src/*.py` file is frozen unconditionally
  (a plain glob, no per-device filter), `boot_entry/wozi_boot.py` is staged **by hardcoded name**
  regardless of `device`, and the generated `_boot.py` does a hardcoded `import wozi_boot`. So
  `scripts/build_firmware.py <anything>` today always produces a UF2 that boots into
  `sensortask_wozi.main()` — this is the exact gap the earlier scratch-patch investigation stood in
  for, and the real, concrete thing this plan needs to fix.
- **There is only one "dev" device — no separate name, no separate fixture.**
  `html/definitions/dev.json` already exists today as a broad kitchen-sink projection (SCD30 +
  SGP40 + SHTC3 + MPRLS + ISL29125 — three of which have no real `src/` driver yet). Per the project
  owner: **that fixture is wrong and doesn't get kept alongside anything new — there is only "dev",
  and "dev" now means the real, limited, actually-wired sensor set.** `dev.json` gets rewritten in
  place to describe exactly SCD30/SGP40/BMP3xx, replacing its current kitchen-sink content, not
  supplemented by a second file under a different name.
- **The existing scratch bring-up script already proves the wiring/logic works, and stays as the
  separate debug-only path it always was.** The "bench bring-up adaptation" entry script embedded in
  full in `dev_legacy/README.md` is a hand-written, already-validated module with the bench's
  correct pins, run via `mpremote run` (mounted, not flashed) — 100+s clean, zero errors, confirmed
  multiple times, watchdog deliberately disarmed as a debugging aid. **This script is not being
  replaced** — it remains the dedicated-debug-run path (mounted, watchdog off). The new
  `src/sensortask_dev.py` this plan produces is a separate, real, flashable `src/` file (watchdog
  armed, same as wozi) for actual verification/soak use — the two coexist for different purposes,
  same relationship `sensortask_wozi.py` already has to any ad hoc REPL debugging on that side.
- **`tests_hardware/`'s flash/bench pytest tier is unaffected by any of this and stays as-is.** It
  drives sensors directly via its own pin-correct `device_scripts/*.py` over `mpremote`, independent
  of whichever application the flashed firmware boots into — confirmed by reading
  `tests_hardware/README.md`'s prerequisites directly. Not in scope to change; its own already-green
  results (flash tier 15 passed, bench-tier WiFi fixes) are not retroactively invalidated by
  anything in this plan.
- **CLAUDE.md's standing rule** (added this session): wozi is never physically flashed, only dev is,
  and a passing dev-bench result — on genuinely dev-native code — counts as valid for wozi too.

## 3. Resolved decisions (settled by the project owner 2026-09-03; corrected once after an initial
misreading — this is the current, authoritative version)

1. **Device id: `dev`. No second name, no kept-alongside kitchen-sink fixture.** File/module names,
   fixed: `src/sensortask_dev.py`, `boot_entry/dev_boot.py`, `html/definitions/dev.json` (rewritten
   in place — not a new file, the existing kitchen-sink content is replaced, not preserved).
2. **Wiring/entry-point baseline to build from: whichever configuration is confirmed to still
   enumerate over USB for `mpremote`.** Use `dev_legacy/README.md`'s own most recently confirmed-
   working wiring table + entry-script recipe (§2 above) as the starting point — it's already the
   one proven to keep the board reachable over USB serial. Don't introduce an untested wiring
   tweak while porting it into `src/sensortask_dev.py`. This is explicitly a temporary baseline that
   the automated per-variant generator will replace later — implement it straightforwardly, don't
   gold-plate it. (Separately, unrelated to wiring: `scripts/build_firmware.py`'s device→boot-module
   mechanism is still needed and still approved as scoped — require `boot_entry/<device>_boot.py` to
   exist, staging/generation picks it by name instead of the hardcoded `wozi_boot`.)
3. **FRAM chunk order: does not need to match wozi's.** The only real requirement is the existing
   FRAM chunk determinism rule (SPECIFICATION.md Part A.4/A.7): whatever order
   `sensortask_dev.py`'s own `build_system()` constructs modules in, that order must stay identical
   across every future rebuild of *this* variant (so on-chip FRAM offsets keep decoding correctly) —
   it does not need to reproduce wozi's own specific seven-chunk sequence. In practice, mirroring
   wozi's order is still the simplest choice (same sensor set, no reason to deviate) — just don't
   treat matching wozi as a hard requirement if there's a reason to differ. `max_size=0x40000` for
   the 256KB chip either way (not wozi's `0x2000`).
4. **Digital-twin equivalent: yes, exactly as originally planned.** Build
   `digital_twin/run_dev_integration.py`, mirroring `run_wozi_integration.py`.
5. **Watchdog: armed in `sensortask_dev.py`, same as wozi (hardcoded, no injection point) — this
   does not conflict with dedicated debug runs, because those use the separate scratch script, not
   this file.** The real, flashable `src/sensortask_dev.py` arms the watchdog unconditionally,
   matching wozi's own construction step 1 and CLAUDE.md's hard rule that it must be hardcoded so no
   code path can ever disable it. Debug runs needing the watchdog off keep using the existing
   mounted scratch-script path (§2 above), which is untouched by this plan and stays watchdog-free
   as it always has been — the two paths don't compete for the same file.
6. **Unit-test bar: full parity with `test_sensortask_wozi.py`, understood as an interim
   investment.** Construction order, FRAM chunk order/size, setup-batch order, task/timer starter
   collection, debug-level registry — adapted to `dev`'s own pins/FRAM size. This is what CLAUDE.md's
   hard rules and SPECIFICATION.md Part D already require for anything landing in `src/`; the project
   owner's own framing is that this hand-written test suite (like the rest of this plan) will
   eventually fold into whatever the automated generator produces — write it properly now regardless,
   don't skip it because it's provisional.

## 4. Action list

### 4a. Code work — no hardware needed, can be done ahead of the physical session

1. Write `src/sensortask_dev.py` — same shape as `sensortask_wozi.py`
   (SPECIFICATION.md Part A.7), with: the bench's own pins from §2 above, `max_size=0x40000` for
   FRAM, `import frozen_html` + `static_mount="/html"` + `is_hotspot_active=conn.is_hotspot_active`
   (the captive-portal wiring the current scratch script lacks), watchdog armed (decision 5).
   Construction/FRAM-chunk order per decision 3 (mirroring wozi's is fine; not a hard requirement).
   Full review pass against CLAUDE.md's hard rules and SPECIFICATION.md Part D's checklist —
   including D.9 (check against current MicroPython) and D.10/the "bird's-eye scan" hard rule (API
   consistency against every other file already in `src/`, run whenever a new file lands there).
2. Write `boot_entry/dev_boot.py`, mirroring `boot_entry/wozi_boot.py` exactly, importing from
   `sensortask_dev`.
3. Extend `scripts/build_firmware.py` per decision 2's mechanism; extend
   `tests_scripts/test_build_firmware.py` so both `wozi` and `dev` are covered by a regression test
   (each produces a UF2 whose staged `_boot.py` imports the *correct*, distinct boot module — this
   is exactly the class of bug that let the mismatch happen unnoticed the first time).
4. Rewrite `html/definitions/dev.json` in place, describing exactly the three sensors from §1's
   scope (SCD30/SGP40/BMP3xx) — replacing its current kitchen-sink content entirely, modeled on
   `html/definitions/wozi.json`'s shape.
5. Write `tests/test_sensortask_dev.py` per decision 6 — mirroring `test_sensortask_wozi.py`'s
   coverage, adapted to this variant's pins/FRAM size.
6. `digital_twin/run_dev_integration.py` per decision 4.
7. Full virtual regression chain, clean, before this ever goes near real hardware: `scripts/lint.sh`,
   `scripts/typecheck.sh`, `scripts/test.sh` — plus a bounded twin soak of `dev`'s `main()`.
8. Build-only real check (no flash): `uv run scripts/build_firmware.py dev` succeeds, and the
   staged output actually imports `dev_boot` — confirm via `tests_scripts/`'s own assembly
   tests plus a manual inspection of the staged files.
9. Commit, push, open a draft PR, confirm CI green, subscribe to its activity — standard workflow,
   nothing hardware-specific about this step.

### 4b. Real-hardware work — needs the physical session, cannot be done from a cloud sandbox

1. ~~Flash the new build for real...~~ **Done (2026-09-03).** `uv run scripts/build_firmware.py dev`
   + `picotool load -f -x -v` — but not before finding and fixing one more real bug this step's own
   criterion (11, USB reachability) was designed to catch: the frozen `_boot.py`→`<device>_boot.py`
   chain never returns, so rp2 never reaches `mp_usbd_init()` at all, meaning USB never enumerated
   after any real hard reset regardless of device (confirmed against the pinned v1.28.0 source,
   independently against `micropython/micropython#15230`). Fixed by freezing each device's boot
   entry under the literal name `"main.py"` instead of a custom `_boot.py` (`scripts/
   build_firmware.py`'s own docstring, `SPECIFICATION.md` Part B.11/F.1) — with that fix, this step
   passed cleanly.
2. ~~Confirm a clean boot with the watchdog armed...~~ **Done (2026-09-03).** Board reachable over
   USB immediately after flash; a 6.5-minute real stability window afterward (`SysUptime` climbing
   monotonically, watchdog armed throughout, no crash-triggered reset) showed zero real (type "E")
   errors on `SCD30`/`BMP3XX`/`WEBSERVER`/`WIFI`; `SGP40` only ever logged benign FRAM-backup-
   timestamp warnings. `GET /measurements` returned real, plausible values for all three sensors
   (BMP3xx, SCD30, SGP40) — this directly confirms the frozen_html/static_mount heap-fragmentation
   lead was never the real explanation; the actual root cause was the USB-boot-sequencing bug above,
   unrelated to heap footprint.
3. ~~Captive-portal hotspot-mode redirect...~~ **Done (2026-09-03).** A real `GET /generate_204` over
   the real hotspot link returned a genuine `302`/`Location: /`; `GET /` served the real site
   (`200`). Closes the gap `tests_hardware/README.md`'s own entry tracked as "never actually
   verified under a valid configuration."
4. Re-run the existing `tests_hardware/` flash + bench pytest tiers against this new build. Expected
   to already pass (§2's facts explain why), but worth confirming against the corrected build rather
   than assuming. **Not yet done.**
5. Hotspot role-reversal test + a bounded soak window — both already listed as outstanding in
   `REAL_HARDWARE_RUN_LOG.md`'s "Next session should start here," unchanged by this plan, just now
   run against the corrected build instead of production wozi-booting firmware. **Not yet done.**
6. ~~Once genuinely green: update `BACKLOG.md`/`REAL_HARDWARE_RUN_LOG.md`/`tests_hardware/README.md`/
   `dev_legacy/README.md`...~~ **Partially done (2026-09-03)**: `tests_hardware/README.md`'s
   precondition and its captive-portal entry, `HARDWARE_TEST_PLAN.md` §6.1/§6.2, and both
   `wozi`-flashing spots in `tests_hardware/manual/manual_toolchain.py`/`tests_hardware/flash/
   test_toolchain_flash_boot.py` are now repointed at `dev`. `BACKLOG.md`/`REAL_HARDWARE_RUN_LOG.md`
   still need a pass once items 4/5 above are also done — this plan itself should be deleted at that
   point, per its own header.

## 5. Test plan (three stages, this project's own standing practice)

1. **Plain functionality**: does the twin-driven or real-hardware `main()` boot, read every sensor
   correctly, serve the real website, and redirect hotspot-mode captive-portal probes?
2. **Stability / no crashes or raises**: a bounded twin soak first (action 7), then a real on-bench
   soak once flashed (action 14).
3. **Max coverage**: `tests/test_sensortask_dev.py` at the same bar as `test_sensortask_wozi.py`
   (action 5); the existing, already-built `tests_hardware/` flash+bench tiers re-run against the
   corrected build (action 13).

## 6. Deliberately out of scope here

- **The full per-variant `sensortask-*.py` generator** (BACKLOG's own tracked item). This plan
  produces one more hand-written variant, the same way wozi itself was hand-written — not the tool
  that would generate variants like this one automatically. That is the explicit next step *after*
  this baseline exists, per the project owner's own framing, not something to fold in here.
  Everything this plan builds is interim — expect it to be replaced once that generator lands.
- **Any sensor `dev` doesn't physically have** (SHTC3/MPRLS/ISL29125, or anything else). Scope is
  fixed at exactly wozi's three sensors, per the project owner's direction in §1 — adding more is a
  separate future decision, not something this plan opens the door to by default.
- **Re-litigating `tests_hardware/`'s already-accepted results.** Nothing here calls those into
  question; only the documentation pointer gets updated, once, at the very end (action 15).
- **BACKLOG.md's items 5 (real rp2/lwIP UDP-transport verification) and 6 (WiFi-reachability design
  question).** Unrelated to this plan, still separately tracked, not touched by it.
