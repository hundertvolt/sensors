# BACKLOG

Open questions and explicitly deferred work, with reasoning, so nothing here gets re-litigated
from scratch in a future session. See README.md for orientation and CLAUDE.md for operating
constraints.

## Decided for the refactor

- **`modules/_boot.py`'s `import sensortask.py`** (see open question #1 below) will be addressed
  as part of the `improved-quality/` refactor, not before. Until then it stays as-is on the
  current codebase — don't "fix" it on deployed units' code path.
- **The refactor targets the most recent *stable* releases**, not a re-pin of today's versions.
  This means MicroPython, pico-sdk, picotool, and Microdot should all move forward to their
  current stable releases as of whenever the refactor is actually done, and the refactor should
  actively adopt relevant improvements/new features those releases introduced (e.g. newer
  `machine`/`asyncio` capabilities, manifest/freeze changes, Microdot v2 features) rather than
  just reproducing today's 1.26-era behavior on newer version numbers. Re-verify current docs at
  that time rather than relying on this file's version notes, which will have aged.
- **Adafruit-derived driver code is fair game for the refactor.** Unlike `microdot.py` (genuinely
  vendored, hands-off), the low-level chip drivers carrying Adafruit CircuitPython headers have
  already been substantially modified (adapted to async) and can be freely restructured/rewritten,
  keeping attribution where due.
- **Config-schema data-loss risk is a non-issue in the refactor by design**, not something that
  needs a migration/merge fix bolted onto the current global-JSON `ConfigManager`: the refactor's
  config model is already per-sensor rather than one global file, which structurally avoids the
  "one missing key wipes everything" failure mode. The current deployed codebase's behavior is
  left as-is (see open question #8) — this isn't being patched pre-refactor.
- **Event-loop blocking convention**: any future long-running/blocking operation must not stall
  timing-sensitive work (e.g. Neopixel animation timing) — either avoid blocking the loop for a
  noticeable time in the first place, or have the blocking operation coordinate (e.g. via a shared
  lock, following the existing `get_long_block_lock()` pattern in `async_connect.py`) so
  timing-sensitive code gets to run before/around it rather than stalling alongside it. This is now
  a standing convention for new code, not just the original NTP/Neopixel case — see CLAUDE.md.

## Open questions (need the project owner's input or further investigation)

1. **`modules/_boot.py` — `import sensortask.py`** (literal `.py` in the import statement).
   Confirmed working reliably on real hardware for a long time (that's how the task autostarts),
   but MicroPython's documented freeze/import behavior (`freeze()`/`module()` strip the `.py`
   extension from the import name — reconfirmed against current `manifest.rst`) says the module
   should be named `sensortask`, so `import sensortask.py` looks like it should raise
   `ModuleNotFoundError` under standard dotted-import semantics. Mechanism is genuinely unclear —
   not yet root-caused against MicroPython's import source. **Do not "fix" this without testing on
   real hardware first** — it works today. **Resolution timing decided:** addressed during the
   `improved-quality/` refactor, not before (see "Decided for the refactor" above).
2. ~~**SGP40 FRAM backup/restore semantics**~~ — **RESOLVED** by reading
   `asy_sgp40_driver/__init__.py` and `voc_algorithm.py` in full. Confirmed: the FRAM timestamped
   chunk holds the VOC algorithm's serialized internal state
   (`vocalgorithm_proc_ser_des()` → `self.params.pack()`/`.unpack()`), restored on startup via
   `read_sgp()`'s `deserialize` path. A restored backup is discarded if it has no timestamp beyond
   one wait cycle, or if its age exceeds `backup_maxage` minutes; loading also waits up to
   `wait_ntp` seconds for NTP sync before trusting a timestamped backup. Periodic writes happen
   every `backup_period` minutes. Working assumption from the original notes was correct.
3. ~~**Physical wiring / schematics**~~ — **RESOLVED**: no external schematic/PCB design exists.
   Pin assignments encoded in each `sensortask-*.py` are the sole source of truth for wiring.
4. ~~**Ambient-pressure compensation on arzi/neu**~~ — **RESOLVED**: accepted limitation. wozi has
   a live BMP388; arzi/neu intentionally rely on a manually-set static `AmbPres` config value
   instead, and that's fine as-is — not something to address.
5. ~~**Treatment of Adafruit-derived driver code**~~ — **DECIDED**: fair game for the refactor to
   rewrite/restructure (see "Decided for the refactor" above). Only `microdot.py` remains
   genuinely hands-off/vendored.
6. ~~**Scope of `asy_long_block_lock`**~~ — **DECIDED**: this is now a general convention, not an
   ad hoc one-off (see "Decided for the refactor" above and CLAUDE.md) — long-blocking operations
   must not stall timing-sensitive work like Neopixel animation; new code should coordinate around
   that rather than just accepting simultaneous stalls.
7. ~~**`neu` reuses `arzi`'s HTML**~~ — **RESOLVED**: confirmed fine as-is. arzi's pages are
   generic/hostname-driven enough that reuse on neu units is intentional and correct, not a gap.
8. **Config-schema migration is a real data-loss risk on the current deployed codebase** —
   `ConfigManager` overwrites the *entire* config file with hardcoded defaults the moment even one
   key is missing relative to the current firmware's `_DEFAULT_CONFIG`, meaning a firmware update
   that adds a new config key onto a unit with an older `config.json` would silently wipe WiFi
   credentials and tuned calibration values. **Decided**: not being patched on the current
   codebase — accepted as today's workflow (reconfigure via the web UI after a key-adding update).
   The refactor avoids this class of bug entirely by moving to per-sensor config files instead of
   one global file (see "Decided for the refactor" above), so no migration-logic fix is planned
   there either — it just won't be a global-overwrite risk anymore.
9. ~~**Hardcoded fallback-hotspot password**~~ — **DECIDED**: accept the risk for now. Identical
   hardcoded AP-fallback password (`async_connect.py`, and duplicated in
   `improved-quality/async_connect.py`) stays as-is on the current codebase; only exploitable by
   someone in physical WiFi range of a unit that has already lost its real WiFi. Any fix (making it
   configurable/randomized) is deferred to the refactor, not applied now.
10. ~~**No `.gitignore` exists at all**~~ — **RESOLVED**: added (see repo root `.gitignore`).
11. **MicroPython version target vs. upstream drift** — deployed units run 1.26; upstream stable
    is now 1.28.0 (as of the last verification pass). **Decided:** the currently-deployed code
    stays pinned to 1.26 until a deliberate reflash campaign; the refactor is where the version
    target actually moves forward (see "Decided for the refactor" above) — this item now just
    tracks that the move hasn't happened yet, not whether it should. 1.27→1.28 rp2-port changes
    checked so far look RP2350-specific (DMA/PIO/pin-alt-function fixes), not RP2040-breaking, but
    this hasn't been exhaustively checked against every module in this codebase, and will need
    re-checking again at whatever point the refactor actually picks a version to land on.

## Deferred / explicitly out-of-scope work (with reasoning)

- **HTML/frontend automation & consistency** — known to be hand-written, inefficient, and brittle
  by the project owner. Not a priority. Revisit *after* the Python-side refactor is done, then aim
  for automatic/consistent generation.
- **UART sensor integration** (`asy_uart.py`/`asy_uart_comm.py`, currently unused by any deployed
  config) — address only after the refactor of already-deployed features is complete. Not before.
- **Config-duplication centralization** (the same config keys currently have to be kept in sync by
  hand across `_DEFAULT_CONFIG`, the REST handler, and the HTML form) — acknowledged as a real
  weakness, explicitly owned by the `improved-quality/` refactor. Not a concern for the current
  codebase.
- **`dev` config quirks** (e.g. LED/Neopixel REST routes referencing an object that's never
  instantiated since Neopixel task starters are commented out) — explicitly told to ignore, it's a
  bench rig only.
- **Unit tests** — not to be written against the current codebase. The plan is: fully understand
  how the current system works first, confirm what's already been well-transferred into
  `improved-quality/`, and write tests as part of that refactor, not before.
- **Dev/build environment setup (venv, pinned toolchain versions)** — deliberately not started yet.
  General direction when it does happen: track the most recent *stable* releases of
  MicroPython/pico-sdk/picotool rather than pinning to what's in the current handwritten notes;
  MicroPython's rp2 port depends on specific pico-sdk submodules (e.g. `lib/mbedtls`), which
  `update_and_install.txt` already gestures at.

## Security notes

- A real WiFi SSID/password (and a device hostname revealing its physical location) were committed
  in `modules/config.json` in the repo's original initial commit (in a previous copy of this
  project, before it was reimported into this repo). The password was confirmed already
  stale/rotated by the project owner. The history was scrubbed in that prior repo; this repo was
  imported fresh specifically to leave that incident behind. Full sweep of this repo's working
  tree turned up no API keys, tokens, private keys, or email addresses beyond the one item below.
- The one other real credential is the hardcoded hotspot fallback password (item #9 above,
  accepted-for-now) — still present in both `python/CommonDrivers/async_connect.py` and
  `improved-quality/async_connect.py`.
