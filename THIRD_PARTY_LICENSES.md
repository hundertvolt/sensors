# Third-party code and licenses

This project is MIT-licensed (see `LICENSE`). It also vendors or is partly derived from other
MIT-licensed code, listed here in one place rather than only in scattered per-file headers. One
file (`src/captive_dns.py`'s `DNSQuery` class) is derived from an Apache-2.0-licensed project and
stays under Apache-2.0 for that portion - see "Apache License 2.0" below - so this repo is MIT
overall with that one documented exception, not purely MIT top to bottom.

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

## Apache License 2.0 (derived, kept as a separate license within this MIT repo)

Per `SPECIFICATION.md` Part F.4, this project's own MIT license does not override the terms
attached to code derived from an Apache-2.0 project - the derived portion stays under Apache-2.0.

- `src/captive_dns.py`'s `DNSQuery` class (and its pre-refactor `python/CommonDrivers/`
  ancestor) - the packet parsing/building logic (variable names `tipo`/`ini`/`lon`, the exact
  `\x81\x80` header/`\xC0\x0C` pointer/`0x3C` TTL byte layout, and matching inline comments) is a
  near-verbatim derivative of
  [`p-doyle/Micropython-DNSServer-Captive-Portal`](https://github.com/p-doyle/Micropython-DNSServer-Captive-Portal)'s
  `main.py`, licensed Apache License 2.0. That upstream repo's own `LICENSE` file ships the
  Apache-2.0 boilerplate with the copyright-holder line unfilled; "p-doyle" (the GitHub account
  the project is published under) is the only identity available, and is used as the attributed
  name here and in `src/LICENSE-captive_dns` (a sibling file, not embedded in `captive_dns.py`
  itself, matching the `ext/LICENSE-microdot` pattern). Corroborating evidence:
  [`metachris/micropython-captiveportal`](https://github.com/metachris/micropython-captiveportal)
  (MIT-licensed) carries the identical `DNSQuery` class and states in its own README that it's
  "based on" p-doyle's repo - confirming the Apache-2.0 origin isn't erased by a later MIT
  relicensing of a fork. p-doyle's README in turn credits two earlier, older repos
  (`Matt4/micropython-captive-portal-network-setup`, `amora-labs/micropython-captive-portal`) as
  its own basis; the trail wasn't traced further back than p-doyle's repo, the closest
  well-identified link.
  Changes made in this project's version (Apache-2.0 §4(b) notice): ported from a raw blocking
  `socket` to `AsyUDPSocket`/`asyncio`; in the `src/` version, also added type hints,
  `PrintLogHistory`-backed logging/errno reporting, off-subnet request filtering, recv-failure
  backoff, and a root-domain-query parsing fix.
  Ruled out as *not* the source for this file, despite superficial DNS-server similarity: three
  of the other candidates the project owner asked to check -
  [`jczic/MicroDNSSrv`](https://github.com/jczic/MicroDNSSrv) (MIT, thread-based, unrelated
  packet-building code/header bytes) and
  [`belyalov/tinydns`](https://github.com/belyalov/tinydns) (MIT, `int.from_bytes`-based parsing,
  different header/pointer bytes) - neither matches this file's structure or byte layout; the
  shared DNS-protocol bytes they do have in common come from RFC 1035 itself, not copying.

## Not applicable

- [`urg/micropython-captive-dhcp-server`](https://github.com/urg/micropython-captive-dhcp-server)
  (MIT, also on PyPI as `micropython-captive-dhcp-server`) - a DHCP *server* implementation. This
  project has no DHCP server of its own (only client-side `network.dhcp` usage of MicroPython's
  built-in WiFi stack in `asy_wifi_service.py`/`asy_ntp_client.py`), so there is nothing in this
  repo to compare it against.

## Provenance not established

- `src/asy_ntp_client.py`, `src/asy_udp_socket.py` (and their pre-refactor
  `python/CommonDrivers/` ancestors) carry no header, source comment, or other fingerprint in
  either version, and no specific origin could be identified. Treated as original/adapted code;
  flagged here as a known, accepted residual risk rather than a certified clean-room origin.
- Parts of this codebase were written with AI assistance (Claude). No specific reuse of another
  project's code is known, but this is disclosed rather than assumed away.
