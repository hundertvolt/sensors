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
out of scope here; see §6.

**Scope, confirmed by the project owner**: at this stage, this variant carries **exactly the same
three sensors wozi has — SCD30, BMP3xx, SGP40 — wired differently, nothing added or removed.** No
SHTC3/MPRLS/ISL29125 (those belong to the unrelated `dev.json` kitchen-sink fixture, see §2) and no
new sensor drivers. This keeps the variant a pure "same logic, different pins/FRAM" exercise, which
is exactly what makes it a valid stand-in for wozi under CLAUDE.md's hard rule.

**Done when**: a real UF2 built for the dev bench boots cleanly with the watchdog armed, every
sensor reads correctly on its actual wiring, the real website serves and the captive-portal
redirect works over a real hotspot link, and this has survived a real on-bench soak — plus the
existing `tests_hardware/` flash/bench pytest tiers re-run cleanly against it. At that point CLAUDE.md's
rule applies in full: this result stands for wozi too, and BACKLOG's still-open real-hardware items
(captive-portal verification, the per-variant generator's blocking dependency) close out for real.

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
- **`html/definitions/dev.json` already exists but describes something else.** Read directly: it's
  a broad kitchen-sink fixture (SCD30 + SGP40 + SHTC3 + MPRLS + ISL29125 — three of which have no
  real `src/` driver yet per BACKLOG's "unconfirmed projection" entry), used for exercising the
  website/definitions system generically. It is **not** a description of the physical dev bench's
  real, currently-wired sensor set. Using the device id `dev` for this variant would collide with
  this existing file's own meaning — resolved as decision 1 below by using a different id.
- **The existing scratch bring-up script already proves the wiring/logic works.** The "bench
  bring-up adaptation" entry script embedded in full in `dev_legacy/README.md` is a hand-written,
  already-validated module with the bench's correct pins, run via `mpremote run` (mounted, not
  flashed) — 100+s clean, zero errors, confirmed multiple times. It is **not** a real `src/` file
  (never reviewed/tested to Part D's bar, not wired into `scripts/build_firmware.py`), has **no
  watchdog armed** (deliberately, "a debugging aid"), and has **no `import frozen_html`/
  `static_mount`** — so it never serves the real website and has never exercised the captive-portal
  redirect at all. Promoting it into a real `src/sensortask_devbench.py` is most of this plan's
  actual work, not a from-scratch design exercise.
- **`tests_hardware/`'s flash/bench pytest tier is unaffected by any of this and stays as-is.** It
  drives sensors directly via its own pin-correct `device_scripts/*.py` over `mpremote`, independent
  of whichever application the flashed firmware boots into — confirmed by reading
  `tests_hardware/README.md`'s prerequisites directly. Not in scope to change; its own already-green
  results (flash tier 15 passed, bench-tier WiFi fixes) are not retroactively invalidated by
  anything in this plan.
- **CLAUDE.md's standing rule** (added this session): wozi is never physically flashed, only dev is,
  and a passing dev-bench result — on genuinely dev-native code — counts as valid for wozi too.

## 3. Resolved decisions (were open questions; settled by the project owner 2026-09-03)

1. **Device id / definitions-file naming: `devbench`.** Not `dev` (already taken by the
   kitchen-sink projection fixture, left untouched) and not `bench` (too close to `tests_hardware/`'s
   own "bench tier" terminology, which means something else). Matches the terminology already used
   throughout `dev_legacy/README.md`/`REAL_HARDWARE_RUN_LOG.md`. File/module names, fixed:
   `src/sensortask_devbench.py`, `boot_entry/devbench_boot.py`, `html/definitions/devbench.json`.
2. **`scripts/build_firmware.py`'s device→boot-module mechanism: approved as scoped.** Require
   `boot_entry/<device>_boot.py` to exist; `build_stage_dir()`/`_BOOT_PY` generation picks it by
   name (`import {device}_boot`) instead of the hardcoded `import wozi_boot`. An explicit,
   minimal convention — not the full per-variant generator, which stays out of scope (§6).
3. **FRAM chunk order: same order as wozi, only `max_size` changes.** Confirmed by the "exactly
   wozi's sensors, different wiring" scope above — same modules constructed, same relative order,
   same seven chunks (`SystemService` → `SGP40_Reader` ×2 → `BMP3xx_Reader` → `SCD30_Reader` →
   `NeopixelDriver` → `NotificationCoordinator`). Only `max_size=0x40000` (256KB chip) differs from
   wozi's `0x2000`.
4. **Digital-twin equivalent: yes.** Build `digital_twin/run_devbench_integration.py`, mirroring
   `run_wozi_integration.py`. Keeps this variant on the same "prove it virtually first" footing every
   future change to it should get, rather than a real flash cycle being the only way to test it.
5. **Watchdog: armed.** `WDT(timeout=8000)`, matching wozi's own construction step 1. A baseline
   meant to stand in for production shouldn't ship with the scratch script's debugging-only
   leniency — a wedged bus should produce a real, observable reboot during the soak, not a silent
   hang that only a human watching the REPL would notice.
6. **Unit-test bar: full parity with `test_sensortask_wozi.py`.** Construction order, FRAM chunk
   order/size, setup-batch order, task/timer starter collection, debug-level registry — adapted to
   `devbench`'s own pins/FRAM size. Not optional; this is what CLAUDE.md's hard rules and
   SPECIFICATION.md Part D already require for anything landing in `src/`.

## 4. Action list

### 4a. Code work — no hardware needed, can be done ahead of the physical session

1. Write `src/sensortask_devbench.py` — same shape and construction order as `sensortask_wozi.py`
   (SPECIFICATION.md Part A.7), with: the bench's own pins from §2 above, `max_size=0x40000` for
   FRAM, `import frozen_html` + `static_mount="/html"` + `is_hotspot_active=conn.is_hotspot_active`
   (the captive-portal wiring the current scratch script lacks), watchdog armed. Full review pass
   against CLAUDE.md's hard rules and SPECIFICATION.md Part D's checklist — including D.9 (check
   against current MicroPython) and D.10/the "bird's-eye scan" hard rule (API consistency against
   every other file already in `src/`, run whenever a new file lands there).
2. Write `boot_entry/devbench_boot.py`, mirroring `boot_entry/wozi_boot.py` exactly, importing from
   `sensortask_devbench`.
3. Extend `scripts/build_firmware.py` per decision 2; extend `tests_scripts/test_build_firmware.py`
   so both `wozi` and `devbench` are covered by a regression test (each produces a UF2 whose staged
   `_boot.py` imports the *correct*, distinct boot module — this is exactly the class of bug that let
   the mismatch happen unnoticed the first time).
4. Add `html/definitions/devbench.json`, describing exactly the three sensors from §1's scope
   (SCD30/SGP40/BMP3xx) — not a copy of the existing kitchen-sink `dev.json`.
5. Write `tests/test_sensortask_devbench.py` per decision 6 — mirroring `test_sensortask_wozi.py`'s
   coverage, adapted to this variant's pins/FRAM size.
6. `digital_twin/run_devbench_integration.py` per decision 4.
7. Full virtual regression chain, clean, before this ever goes near real hardware: `scripts/lint.sh`,
   `scripts/typecheck.sh`, `scripts/test.sh` — plus a bounded twin soak of `devbench`'s `main()`.
8. Build-only real check (no flash): `uv run scripts/build_firmware.py devbench` succeeds, and the
   staged output actually imports `devbench_boot` — confirm via `tests_scripts/`'s own assembly
   tests plus a manual inspection of the staged files.
9. Commit, push, open a draft PR, confirm CI green, subscribe to its activity — standard workflow,
   nothing hardware-specific about this step.

### 4b. Real-hardware work — needs the physical session, cannot be done from a cloud sandbox

10. Flash the new build for real (`picotool load`, one real flash cycle — not the mount-and-run
    scratch workaround) onto the dev bench.
11. Confirm a clean boot with the watchdog armed: every sensor reads correctly
    (`GET /measurements`/REPL), no I2C errors on the shared i2c1 bus specifically — this is the
    concrete test that finally confirms or refutes the frozen_html/static_mount heap-fragmentation
    lead already on record (see BACKLOG.md's "per-variant `sensortask-*.py` generator" entry), now
    under a build that's actually correct for this hardware instead of the earlier mismatched one.
12. Captive-portal hotspot-mode redirect over a real hotspot link (`GET /generate_204` → real
    `302`/`Location: /`) — this is the concrete step that closes the gap BACKLOG.md's open questions
    list currently records as "never actually verified under a valid configuration."
13. Re-run the existing `tests_hardware/` flash + bench pytest tiers against this new build. Expected
    to already pass (§2's facts explain why), but worth confirming against the corrected build rather
    than assuming.
14. Hotspot role-reversal test + a bounded soak window — both already listed as outstanding in
    `REAL_HARDWARE_RUN_LOG.md`'s "Next session should start here," unchanged by this plan, just now
    run against the corrected build instead of production wozi-booting firmware.
15. Once genuinely green: update `BACKLOG.md`/`REAL_HARDWARE_RUN_LOG.md`/`tests_hardware/README.md`/
    `dev_legacy/README.md` to record this as the project's one standing physically-verified
    baseline. Specifically: `tests_hardware/README.md` line ~26 and `HARDWARE_TEST_PLAN.md` §6.1
    currently document "the one allowed flash" as `scripts/build_firmware.py wozi` — repoint that at
    `devbench` once it exists (a real doc fix this plan deliberately defers to this step, since the
    *existing* flash/bench tier's already-accepted results don't need to be re-earned first — see
    §2's facts on why that tier is unaffected).

## 5. Test plan (three stages, this project's own standing practice)

1. **Plain functionality**: does the twin-driven or real-hardware `main()` boot, read every sensor
   correctly, serve the real website, and redirect hotspot-mode captive-portal probes?
2. **Stability / no crashes or raises**: a bounded twin soak first (action 7), then a real on-bench
   soak once flashed (action 14).
3. **Max coverage**: `tests/test_sensortask_devbench.py` at the same bar as `test_sensortask_wozi.py`
   (action 5); the existing, already-built `tests_hardware/` flash+bench tiers re-run against the
   corrected build (action 13).

## 6. Deliberately out of scope here

- **The full per-variant `sensortask-*.py` generator** (BACKLOG's own tracked item). This plan
  produces one more hand-written variant, the same way wozi itself was hand-written — not the tool
  that would generate variants like this one automatically. That is the explicit next step *after*
  this baseline exists, per the project owner's own framing, not something to fold in here.
- **Any sensor devbench doesn't physically have** (SHTC3/MPRLS/ISL29125, or anything else). Scope is
  fixed at exactly wozi's three sensors, per the project owner's direction in §1 — adding more is a
  separate future decision, not something this plan opens the door to by default.
- **Re-litigating `tests_hardware/`'s already-accepted results.** Nothing here calls those into
  question; only the documentation pointer gets updated, once, at the very end (action 15).
- **BACKLOG.md's items 5 (real rp2/lwIP UDP-transport verification) and 6 (WiFi-reachability design
  question).** Unrelated to this plan, still separately tracked, not touched by it.
