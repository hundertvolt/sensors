# Device Reference

End-user notes for configuring/operating a deployed unit — not an AI-session or architecture doc
(see README.md/CLAUDE.md/SPECIFICATION.md for those). Add to this file, don't duplicate it
elsewhere, when a new user-facing behavior needs explaining.

## Neopixel LED

One physical LED serves two independent purposes, arbitrated by `asy_neopixel_driver.py`:

- **WiFi status overlay** — a dim white glow, on/off only, driven by `/networking`'s `LedWifiOn`
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

## ISL29125 colour sensor (dev units only)

Four things about this sensor read as bugs if you don't know them.

**Its RGB is not a colour you can trust as a colour.** The three channels are the raw response of
three filters on one silicon die, normalised to 0–1. They are *not* sRGB, not colorimetric, and not
white-balanced. Two lamps a person would call the same white will give visibly different R/G/B
here, and pasting these numbers into anything expecting sRGB produces a wrong colour. What they are
good for is *relative* work: comparing the same scene over time, or detecting that the light
changed. `Hue`/`Sat`/`Bri` are derived from those same three numbers and inherit the same caveat.
`CCT` is a relative indicator computed with McCamy's approximation; it is reported only inside
2000–12500 K and is `—` (nothing) in light too dim to say anything meaningful about. A missing CCT
is normal in a dark room, not a fault.

**The IR-compensation settings move the brightness, not just the colour.** `IrCompOffset` and
`IrCompAdjust` exist because the sensor's filters also see infrared, which indoor lighting and
sunlight carry in very different amounts. Changing either one changes the reported **lux** as well
as the colour balance — they are not a colour-only tint control. Change them deliberately, one at a
time, and expect the lux scale to shift with them; the defaults (offset off, adjust 40) are a
reasonable indoor starting point.

**`RangeAct` tells you which of the two ranges the reading came from**, and it changes on its own.
The chip has a sensitive range (375 lx) and a bright one (10000 lx), and the unit switches between
them automatically while `RangeAuto` is on. The reported lux is corrected so that the two agree,
and RGB/HSB are normalised over the whole span, so **nothing should visibly jump when `RangeAct`
changes**. If it does, that is worth reporting. The `AutoRange*` settings tune when the switch
happens (how full the reading gets before going up, how empty before coming down, how long to
settle, and a minimum dwell time so it cannot chatter) — the defaults are fine for ordinary use.

**The unit learns its own calibration, and it is meant to.** Every real chip's two ranges differ
slightly from the nominal 26.67× ratio between them. When a reading lands in the band where both
ranges work, the unit measures the real ratio on *this* chip and keeps a running average of it in
FRAM, with a timestamp — `/status` shows both as `GainRatio` and `CalTS`. That is why readings
across a range switch line up better after the unit has been running a while. `ISLResetCal` throws
the learned value away and starts over; use it after changing the optics in front of the sensor,
not as routine maintenance. A `CalTS` of 0 simply means nothing has been learned yet.
