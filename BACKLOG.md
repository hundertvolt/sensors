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
2. **SGP40 FRAM backup/restore semantics** — `asy_sgp40_driver/__init__.py` has not been read in
   depth yet (only signatures grepped). Working assumption: the FRAM timestamped chunk persists
   the VOC algorithm's baseline/humidity-compensation state across power loss/reboot so gas-sensor
   calibration doesn't restart cold every time, and `SGPBackupMaxAge` discards a too-stale backup.
   Needs verification by actually reading the driver before documenting it as fact.
3. **Physical wiring / schematics** — pin assignments (I2C/SPI buses, reset/eoc/irq pins) only
   exist encoded in each `sensortask-*.py`. Unknown whether a schematic/PCB design/wiring diagram
   exists anywhere outside this repo, or whether the code is the sole source of truth.
4. **Ambient-pressure compensation on arzi/neu** — `wozi` has a BMP388 for live pressure; arzi/neu
   have no barometric sensor, so SCD30's `AmbPres` compensation on those units can presumably only
   ever come from a manually-set static config value. Not yet confirmed as an accepted limitation
   vs. something to address.
5. **Treatment of Adafruit-derived driver code** — `I2CDevice`/`SPIDevice` and several low-level
   chip drivers still carry Adafruit CircuitPython docstrings/copyright headers, adapted to async.
   Unclear whether this should be treated as vendored/hands-off (like `microdot.py`) or as
   already-modified-enough to be fair game for the refactor.
6. **Scope of `asy_long_block_lock`** — currently shares one lock between NTP DNS resolution and
   the Neopixel animation. Unclear whether this is meant as a general "anything that blocks the
   event loop for a noticeable time must acquire this lock" convention to extend to future
   sensors/features, or was an ad hoc fix for that one interaction.
7. **`neu` reuses `arzi`'s HTML** (`build-neu.sh` copies `html_raw/arzi/*`, and no `html_raw/neu/`
   folder exists). Unconfirmed whether arzi's pages are generic/hostname-driven enough that this is
   fine, or whether they contain arzi-specific text that's technically wrong on a neu unit.
8. **Config-schema migration is a real data-loss risk, not just a design quirk**: `ConfigManager`
   overwrites the *entire* config file with hardcoded defaults the moment even one key is missing
   relative to the current firmware's `_DEFAULT_CONFIG` — meaning flashing a firmware update that
   adds a new config key (e.g. wozi's BMP settings) onto a unit with an older `config.json` would
   silently wipe WiFi credentials and all tuned calibration values. Not yet confirmed whether this
   is an accepted "always reconfigure via the web UI after a key-adding update" workflow, or an
   actual bug to fix.
9. **Hardcoded fallback-hotspot password** — `async_connect.py:241` (and duplicated in
   `improved-quality/async_connect.py:332`): `self.wlan.config(essid=hostname, password='12345678')`.
   Identical, hardcoded, real credential on every deployed unit's AP fallback mode. Flagged to the
   project owner; not yet decided whether to fix now (make configurable / randomize) or accept
   (only exploitable by someone in physical WiFi range of a unit that has already lost real WiFi).
10. **No `.gitignore` exists at all** in the repo. Worth adding one (config.json patterns, build
    output, etc.) to reduce the chance of another device-config backup getting committed by
    accident.
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
- The one other real credential is the hardcoded hotspot fallback password (open question #9
  above) — still present in both `python/CommonDrivers/async_connect.py` and
  `improved-quality/async_connect.py`.
