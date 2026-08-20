# Third-party code and licenses

This project is MIT-licensed (see `LICENSE`). It also vendors or is partly derived from other
MIT-licensed code, listed here in one place rather than only in scattered per-file headers.

## Vendored, unmodified

- **Microdot** (`ext/microdot.py`, pinned `v2.6.2`; a legacy, unmodified copy of the same version
  also ships as `python/CommonDrivers/microdot.py`) — © 2019 Miguel Grinberg, MIT. License text:
  `ext/LICENSE-microdot`. See `CLAUDE.md`/`SPECIFICATION.md` Part A.5 for this project's
  hands-off vendoring policy for this file.
- **freezefs** (`ext/freezefs/`) — © 2022 bixb922, MIT. License text: `ext/freezefs/LICENSE`.

## Restructured/rewritten, attribution retained (SPDX headers in the files themselves)

Per `SPECIFICATION.md` Part F.4, Adafruit-derived driver code is fair game to restructure for
asyncio/MicroPython while keeping attribution. The following `src/` files are derived this way:

- `src/asy_bmp3xx_driver.py` — from Adafruit's `adafruit_bmp3xx` (CircuitPython), © 2018 Carter
  Nelson for Adafruit Industries, MIT.
- `src/asy_scd30_driver.py` — from Adafruit's `adafruit_scd30` (CircuitPython), © 2020 Bryan
  Siepert for Adafruit Industries, MIT.
- `src/asy_sgp40_driver.py` — from Adafruit's `adafruit_sgp40` (CircuitPython), © 2020 Bryan
  Siepert for Adafruit Industries, MIT.

## Ported, kept literal (SPDX header in the file itself)

Per `SPECIFICATION.md` Part F.4, `voc_algorithm.py` stays a literal, structurally-unchanged port
rather than a restructure, so that it stays diffable against its reference:

- `src/voc_algorithm.py` — Sensirion's Gas Index Algorithm (VOC-only variant) originates with
  Sensirion (`embedded-sgp`'s `sgp40_voc_index/sensirion_voc_algorithm.c/.h`, no separate license
  file located for that repository). This file is a direct port of the intermediate Python
  translation of that C reference, © 2010 DFRobot Co.Ltd (http://www.dfrobot.com), author
  yangfeng, MIT.

## Shipped but not promoted (`python/IndividualDrivers/`, pre-refactor, dev-rig-only sensors)

These still carry their own correct SPDX/MIT headers in place and need no change:

- `asy_mprls_driver.py` — © 2018 ladyada for Adafruit Industries, MIT.
- `asy_shtc3_driver.py` — © 2017 Scott Shawcroft / © 2020 Bryan Siepert for Adafruit Industries, MIT.
- `asy_isl29125_driver.py` — © 2023 Jose D. Montoya, MIT.

## Provenance not established

- `src/captive_dns.py`, `src/asy_ntp_client.py`, `src/asy_udp_socket.py` (and their pre-refactor
  `python/CommonDrivers/` ancestors) carry no header, source comment, or other fingerprint in
  either version, and no specific origin could be identified. Treated as original/adapted code;
  flagged here as a known, accepted residual risk rather than a certified clean-room origin.
- Parts of this codebase were written with AI assistance (Claude). No specific reuse of another
  project's code is known, but this is disclosed rather than assumed away.
