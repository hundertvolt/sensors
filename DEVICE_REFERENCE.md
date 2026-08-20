# Device Reference

End-user notes for configuring/operating a deployed unit — not an AI-session or architecture doc
(see README.md/CLAUDE.md/SPECIFICATION.md for those). Add to this file, don't duplicate it
elsewhere, when a new user-facing behavior needs explaining.

## Neopixel LED

One physical LED serves two independent purposes, arbitrated by `asy_neopixel_driver.py`:

- **WiFi status overlay** — a dim white glow, on/off only, driven by `/networking`'s `WifiLED`
  config field. This is a static preference ("is the indicator enabled"), not a live connectivity
  signal — it's (re)applied whenever the WiFi service (re)establishes its state, not continuously
  tied to connection health.
- **Notification signal** — a colored ramp-up/ramp-down flash, triggered per sensor threshold and
  fully overriding the WiFi overlay while it plays (the overlay's own value is restored once the
  flash finishes). Brightness (`FlashBri`, 1–255) and duration (`FlashDur`, 0.5–10s) are
  configurable via `/notification`; each threshold's own **color** is fixed at build time, not
  user-configurable:

  | Threshold | Color |
  |---|---|
  | `WarnCO2` | red |
  | `WarnVOC` | green |
  | `WarnHum` | blue |

## SGP40 VOC baseline FRAM backup

`/sensors`' SGP40 config has two related but independently-meaning "0" values — easy to conflate:

- **`BackupPeriod`** (minutes, 0–1440): how often the VOC baseline/humidity-compensation state is
  written to FRAM. **`0` disables periodic backup entirely** — nothing is ever written.
- **`BackupMaxAge`** (minutes, 0–10080): on boot, how old a restored FRAM backup is allowed to be
  before it's rejected as stale (falls back to a fresh VOC init instead). **`0` disables this
  staleness check** — a restored backup is accepted no matter how old it is.

The two `0`s point in opposite directions: one turns a feature off, the other turns a limit off.
