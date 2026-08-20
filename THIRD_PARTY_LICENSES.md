# Third-party code and licenses

This project is MIT-licensed (see `LICENSE`). It also vendors or is partly derived from other
MIT-licensed code, listed here in one place rather than only in scattered per-file headers. One
file (`src/captive_dns.py`'s `DNSQuery` class) is derived from an Apache-2.0-licensed project and
stays under Apache-2.0 for that portion - see "Apache License 2.0" below - so this repo is MIT
overall with that one documented exception, not purely MIT top to bottom.

Parts of this codebase were written with AI assistance (Claude). No specific reuse of another
project's code beyond what's documented below is known, but this is disclosed rather than assumed
away.

## Vendored, unmodified

- **Microdot** ([`miguelgrinberg/microdot`](https://github.com/miguelgrinberg/microdot),
  `ext/microdot.py`, pinned `v2.6.2`; a legacy, unmodified copy of the same version also ships as
  `python/CommonDrivers/microdot.py`) — © 2019 Miguel Grinberg, MIT. License text:
  `ext/LICENSE-microdot`. See `CLAUDE.md`/`SPECIFICATION.md` Part A.5 for this project's
  hands-off vendoring policy for this file.
- **freezefs** ([`bixb922/freezefs`](https://github.com/bixb922/freezefs), `ext/freezefs/`) — ©
  2022 bixb922, MIT. License text: `ext/freezefs/LICENSE`.

## Restructured/rewritten, attribution retained (SPDX headers in the files themselves)

Per `SPECIFICATION.md` Part F.4, Adafruit-derived driver code is fair game to restructure for
asyncio/MicroPython while keeping attribution; the same restructure-with-attribution treatment
applies to the one non-Adafruit file below. The following `src/` files are derived this way:

- `src/asy_bmp3xx_driver.py` — from Adafruit's
  [`Adafruit_CircuitPython_BMP3XX`](https://github.com/adafruit/Adafruit_CircuitPython_BMP3XX),
  © 2018 Carter Nelson for Adafruit Industries, MIT.
- `src/asy_scd30_driver.py` — from Adafruit's
  [`Adafruit_CircuitPython_SCD30`](https://github.com/adafruit/Adafruit_CircuitPython_SCD30),
  © 2020 Bryan Siepert for Adafruit Industries, MIT.
- `src/asy_sgp40_driver.py` — from Adafruit's
  [`Adafruit_CircuitPython_SGP40`](https://github.com/adafruit/Adafruit_CircuitPython_SGP40),
  © 2020 Bryan Siepert for Adafruit Industries, MIT.
- `src/asy_ntp_client.py` — the core NTP protocol handling (the `0x1B`-first-byte 48-byte query,
  `struct.unpack("!I", msg[40:44])` timestamp read, NTP/Unix epoch-delta subtraction, and
  critically the `RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))` idiom
  in `_parse_ntp_reply()`) matches
  [`micropython/micropython-lib`](https://github.com/micropython/micropython-lib)'s own
  `micropython/net/ntptime/ntptime.py` module byte-for-byte in the parts that overlap - ©
  2013, 2014 micropython-lib contributors, MIT (that repo's default license for files without
  their own `metadata.txt`-declared license, which `ntptime.py` doesn't have). The leap-indicator/
  stratum rejection, the min/max plausibility window (this file's own answer to the Y2036 wraparound,
  differently shaped from `ntptime.py`'s own newer `MIN_NTP_TIMESTAMP` fix), and all of the
  async/`AsyUDPSocket`/config/retry/timer machinery are this file's own additions, not present
  upstream. See "Author-permitted, no formal license" below for `karfas/upy-simple-app`'s
  `asy_ntp_time.py`, which the project owner separately flagged as a possible origin and which
  turned out to itself be a further wrapper around this same `micropython-lib` source.
- `src/asy_dns_client.py` — its own module docstring already states "Inspired by
  [`vshymanskyy/aiodns`](https://github.com/vshymanskyy/aiodns) (MIT), not a port" (© 2024
  Volodymyr Shymanskyy) - this attribution predates this licensing review and was found already in
  place, not added by it. Verified directly against `aiodns.py`'s real source: the docstring's
  characterization holds up - both build a raw DNS query bytearray and walk the answer section by
  hand, but function names differ (`_build_query`/`_parse_response` vs. `_build_dns_query`/
  `_parse_dns_rsp`), the compression-pointer handling differs (this file assumes the answer
  section starts exactly after the echoed question and requires a bare `0xC0`-masked pointer;
  `aiodns.py` scans for `\xc0` anywhere), and this file has none of `aiodns.py`'s caching, IPv6,
  mDNS/`.local`, or parallel-multi-server-send support - "inspired by, not a port" is an accurate
  description, not an understatement.

## Ported, kept literal (SPDX header in the file itself)

Per `SPECIFICATION.md` Part F.4, `voc_algorithm.py` stays a literal, structurally-unchanged port
rather than a restructure, so that it stays diffable against its reference:

- `src/voc_algorithm.py` — Sensirion's Gas Index Algorithm (VOC-only variant) originates with
  Sensirion's [`embedded-sgp`](https://github.com/Sensirion/embedded-sgp) (`sgp40_voc_index/
  sensirion_voc_algorithm.c/.h`; archived April 2024, BSD-3-Clause). This file is a direct port of
  the intermediate Python translation of that C reference, found in
  [`DFRobot/DFRobot_SGP40`](https://github.com/DFRobot/DFRobot_SGP40)'s `Python/raspberrypi/
  DFRobot_SGP40_VOCAlgorithm.py` (a different filename than this project's `voc_algorithm.py`, but
  matching copyright/class-name fingerprints - see below), © 2010 DFRobot Co.Ltd
  (http://www.dfrobot.com), author yangfeng, MIT (confirmed directly against that repo's own
  `LICENCE` file: "Copyright 2010 DFRobot Co.Ltd", matching this project's own header exactly).
  Since this file ports DFRobot's Python translation rather than Sensirion's C source directly,
  DFRobot's MIT terms are the operative ones for what this project actually copied; Sensirion's
  BSD-3-Clause is noted here for completeness of the full provenance chain, not because this
  project owes it a separate notice.

## Shipped but not promoted (`python/IndividualDrivers/`, pre-refactor, dev-rig-only sensors)

These still carry their own correct SPDX/MIT headers in place and need no change:

- `asy_mprls_driver.py` — from Adafruit's
  [`Adafruit_CircuitPython_MPRLS`](https://github.com/adafruit/Adafruit_CircuitPython_MPRLS),
  © 2018 ladyada for Adafruit Industries, MIT.
- `asy_shtc3_driver.py` — from Adafruit's
  [`Adafruit_CircuitPython_SHTC3`](https://github.com/adafruit/Adafruit_CircuitPython_SHTC3),
  © 2017 Scott Shawcroft / © 2020 Bryan Siepert for Adafruit Industries, MIT.
- `asy_isl29125_driver.py` — from
  [`jposada202020/MicroPython_ISL29125`](https://github.com/jposada202020/MicroPython_ISL29125)
  (archived/deprecated December 2024), © 2023 Jose D. Montoya, MIT.

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

## Not third-party (built into MicroPython itself)

- The fallback hotspot AP's DHCP behavior (assigning an IP to a client that joins it) comes from
  MicroPython's own core `shared/netutils/dhcpserver.c` (MIT, © 2018-2019 Damien P. George) - part
  of the MicroPython project itself, not a separate third-party dependency this repo vendors or
  derives from, so it needs no license entry of its own beyond this note. Confirmed wired into the
  rp2/cyw43 `AP_IF` path via a live upstream report,
  [`micropython/micropython#17401`](https://github.com/micropython/micropython/issues/17401) (AP-mode
  DHCP server ignoring a custom `ifconfig()` subnet). This project has no DHCP server of its own
  anywhere in `src/`, `python/`, `improved-quality/`, `modules/`, or `digital_twin/` - confirmed by
  exhaustive search (protocol bytes, ports, opcodes, class names) and by a full history scan, including
  for the specific "single fixed IP to one client" shape the project owner remembered possibly having
  built at some point (no match found in this repo's history either). Also checked and ruled out on
  this basis:
  [`urg/micropython-captive-dhcp-server`](https://github.com/urg/micropython-captive-dhcp-server)
  (MIT, also on PyPI as `micropython-captive-dhcp-server`) - nothing in this repo to compare it
  against.

## Author-permitted, no formal license (public forum offer)

- [`karfas/upy-simple-app`](https://github.com/karfas/upy-simple-app) (`lib/asy_udp_client.py`,
  `lib/asy_ntp_time.py`) — the project owner flagged this repo from memory as a possible origin
  for `src/asy_udp_socket.py`/`src/asy_ntp_client.py`. Checked directly:
  - `asy_ntp_time.py`'s NTP-parsing logic is itself already a fairly direct copy of
    micropython-lib's own `ntptime.py` (see the MIT entry above), wrapped in an async task around
    karfas's own `AsyUDPClient`. That part's real origin is micropython-lib, independent of
    whether this project's code passed through karfas's file along the way - already covered
    above.
  - `asy_udp_client.py`'s `AsyUDPClient` class — a `select.poll()`-based async UDP wrapper with a
    lazy `_connect()`, a `ready(mask, timeout_ms)` poll-and-wait helper, and a combined
    send-then-receive-with-retries method — is structurally close to this project's own
    `AsyUDPSocket` (`src/asy_udp_socket.py`, `python/CommonDrivers/asy_udp_socket.py`): the same
    overall shape (lazy connect, a `ready()`/poll gate, a paired write+read convenience method,
    explicit `disconnect()` teardown), though method names differ (`send`/`receive` vs.
    `write`/`recvfrom`, `send_and_receive` vs. `write_and_recvfrom`) and this project's version is
    materially more built out (locking, retries, context-manager support, input validation,
    `mode="server"` support karfas's client-only class doesn't have).
  - `karfas/upy-simple-app` carries no `LICENSE` file, license badge, `README.md`, or header
    comment in either file - confirmed directly. On its own, that would mean no permission granted
    under default copyright law (unlike the permissively-licensed Apache-2.0 `captive_dns.py` case
    above). However, the project owner located and provided the actual context:
    [`micropython/discussions#12967`](https://github.com/orgs/micropython/discussions/12967) (Nov
    2023) shows karfas posting links to exactly these two files, in direct response to a public
    request for async NTP/UDP code, saying "it could be a starting point" - and a third party
    (`bulletmark`) replying that they'd use the files in their own app, with no objection from
    karfas. Treated as the author's own public offer of the code for this kind of reuse - a real,
    checkable basis for permission even without a formal license file. Attribution notes were
    added to both files (no formal SPDX identifier is used, since this isn't a named license) with
    a link to the discussion thread and a list of what changed from karfas's originals.
