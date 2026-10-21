# Third-party code and licenses

This project is public and MIT-licensed (see `LICENSE`). It vendors or derives from other code,
listed here in one place; most of it is MIT too. The exceptions to "MIT overall": the `DNSQuery`
class in `src/asy_captive_dns.py` derives from an Apache-2.0 project and stays under Apache-2.0
(see "Apache License 2.0"); the VOC algorithm port's provenance runs back to Sensirion's
BSD-3-Clause C source (see "Ported, kept literal"); and the `UDPSocket` class in
`src/asy_udp_socket.py` follows code its author offered publicly without a license (see
"Author-permitted, no formal license"). `arduino/` (the Arduino C implementation of the UART
protocol) is outside this file and every lint, test, license and secret review: post-audit only
(owner, 2026-09-25: 'the C port stays out of scope, anything there is post-audit only'; the
secret scan too, owner, 2026-09-30).

Parts of this codebase were written with AI assistance (Claude). No specific reuse of another
project's code beyond what's documented below is known, but this is disclosed rather than assumed
away.

## Vendored, unmodified

- **Microdot** ([`miguelgrinberg/microdot`](https://github.com/miguelgrinberg/microdot),
  `ext/microdot.py`, pinned `v2.7.0`, and three of upstream's type stubs of the same tag,
  `ext/typings/microdot/__init__.pyi`, `microdot.pyi` and `multipart.pyi` (type-checking only,
  never frozen) — verified byte-identical to that tag on 2026-10-06 (pinned by
  `tests_scripts/test_vendored_microdot.py`); a legacy copy, upstream commit `482ab6d`, an
  untagged snapshot four commits after `v2.0.6`, before `v2.0.7`, also ships as
  `legacy/firmware/python/CommonDrivers/microdot.py`) — © 2019 Miguel Grinberg, MIT. License
  text: `ext/LICENSE-microdot`. See `CLAUDE.md`/`SPECIFICATION.md` Part A.5 for this project's
  hands-off vendoring policy for this file.
- **freezefs** ([`bixb922/freezefs`](https://github.com/bixb922/freezefs), `ext/freezefs/`:
  `__main__.py`, `archive.py`, `ffsextract.py`, `ffsmount.py`, `LICENSE`) — upstream publishes no
  release tags; vendored from `main` at `26be9e339a25e71f506f06a33a2346d6a13a07b8` (2025-10-25),
  verified byte-identical on 2026-09-10 and pinned by `tests_scripts/test_vendored_freezefs.py`.
  MIT; upstream's `LICENSE` reads "Copyright (c) 2022 bixb922", and `archive.py`, `ffsextract.py`
  and `ffsmount.py` each open with "(c) 2023 Hermann Paul von Borries" and "MIT License" — both
  recorded as upstream states them. The frozen website carries `ffsmount.py`'s code with its
  comment lines stripped by freezefs itself (`archive.py:150-175`), so a published image carries
  this license (below).

## Restructured/rewritten, attribution retained (SPDX headers in the files themselves)

Per `SPECIFICATION.md` Part F.4, Adafruit-derived driver code is fair game to restructure for
asyncio/MicroPython while keeping attribution; the same restructure-with-attribution treatment
applies to the two non-Adafruit files below (`asy_isl29125_driver.py`, `asy_ntp_client.py`);
`asy_dns_client.py` is listed for the credit it gives, as an inspiration, not a derivative. The
following `src/` files are derived this way:

- `src/asy_bmp3xx_driver.py` — from Adafruit's
  [`Adafruit_CircuitPython_BMP3XX`](https://github.com/adafruit/Adafruit_CircuitPython_BMP3XX),
  © 2018 Carter Nelson for Adafruit Industries, MIT.
- `src/asy_scd30_driver.py` — from Adafruit's
  [`Adafruit_CircuitPython_SCD30`](https://github.com/adafruit/Adafruit_CircuitPython_SCD30),
  © 2020 Bryan Siepert for Adafruit Industries, MIT.
- `src/asy_sgp40_driver.py` — from Adafruit's
  [`Adafruit_CircuitPython_SGP40`](https://github.com/adafruit/Adafruit_CircuitPython_SGP40),
  © 2020 Bryan Siepert for Adafruit Industries, MIT.
- `src/asy_isl29125_driver.py` — from
  [`jposada202020/MicroPython_ISL29125`](https://github.com/jposada202020/MicroPython_ISL29125)
  (archived/deprecated December 2024), © 2023 Jose D. Montoya, MIT. What survives from upstream
  is the register map and the sense of the configuration bits; everything else is this project's
  own, written against FN8424 Rev 3.00 directly: the three-layer asyncio structure, the
  shadow-register single-write model, the destructive-status-read discipline, the auto-range state
  machine, the on-demand gain-ratio measurement (held in RAM and published for the user to apply,
  never adopted by the driver), and all of the config/logging/error machinery.
- `src/asy_fram_driver.py` — opcode/register-constant naming and the write-enable/write/
  write-disable method shape follow Adafruit's
  [`Adafruit_CircuitPython_FRAM`](https://github.com/adafruit/Adafruit_CircuitPython_FRAM),
  © 2018 Michael Schroeder for Adafruit Industries, MIT (its SPI variant, `adafruit_fram.FRAM`
  with an `spi` argument, not the I2C default). RDID-based dual-chip detection and the
  asyncio/MicroPython restructuring are this project's own addition, cross-checked against the
  Fujitsu MB85RS64V/MB85RS2MTA datasheets rather than Adafruit's driver (which targets a
  different, smaller Fujitsu part with no RDID check at all).
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
  async/`UDPSocket`/config/retry/timer machinery are this file's own additions, not present
  upstream. See "Author-permitted, no formal license" below for `karfas/upy-simple-app`'s
  `asy_ntp_time.py`, which the project owner separately flagged as a possible origin and which
  turned out to itself be a further wrapper around this same `micropython-lib` source.
- `src/asy_dns_client.py` — its header states "Inspired by github.com/vshymanskyy/aiodns, not a
  port" under that project's SPDX lines ([`vshymanskyy/aiodns`](https://github.com/vshymanskyy/aiodns),
  © 2024 Volodymyr Shymanskyy, MIT). Verified against `aiodns.py`'s real source: the header's
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

- `src/voc_algorithm.py` — a literal port of the Python translation in
  [`DFRobot/DFRobot_SGP40`](https://github.com/DFRobot/DFRobot_SGP40)'s
  `Python/raspberrypi/DFRobot_SGP40_VOCAlgorithm.py`, © 2010 DFRobot Co.Ltd
  (http://www.dfrobot.com), author yangfeng, MIT (that repo's `LICENCE`: "Copyright 2010 DFRobot
  Co.Ltd", matching this file's header). That translation ports Sensirion's Gas Index Algorithm
  (VOC variant) from [`Sensirion/embedded-sgp`](https://github.com/Sensirion/embedded-sgp)
  (`sgp40_voc_index/sensirion_voc_algorithm.c/.h`; archived April 2024, BSD-3-Clause); the
  maintained successor is
  [`Sensirion/gas-index-algorithm`](https://github.com/Sensirion/gas-index-algorithm)
  (BSD-3-Clause, © 2021 Sensirion AG). Because this file ports DFRobot's Python rather than
  Sensirion's C, DFRobot's MIT terms are treated as the ones governing what was copied (agent,
  2026-08-20; not a verified legal conclusion); Sensirion's BSD-3-Clause is recorded for the full
  chain, and a published image carries its notice too (below). `tests/voc_reference_vectors.py`
  holds output values computed by Sensirion's C (the gas-index-algorithm fixed-point helpers and
  the archived embedded-sgp algorithm) and contains no Sensirion code.

## Legacy tree (`legacy/`, reference-only, never edited)

- `legacy/firmware/python/IndividualDrivers/asy_bmp3xx_driver.py`, `asy_scd30_driver.py`,
  `asy_sgp40_driver/__init__.py`, `asy_isl29125_driver.py` — the pre-refactor versions of the
  drivers above, same origins, each with its own SPDX header.
- `legacy/firmware/python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py` — the DFRobot
  translation (VOC entry above), own header.
- `legacy/firmware/python/IndividualDrivers/asy_fram_driver.py` — the same Adafruit FRAM naming as
  the `src/` entry above; no header.
- `legacy/firmware/python/IndividualDrivers/asy_mprls_driver.py` — from Adafruit's
  [`Adafruit_CircuitPython_MPRLS`](https://github.com/adafruit/Adafruit_CircuitPython_MPRLS),
  © 2018 ladyada for Adafruit Industries, MIT.
- `legacy/firmware/python/IndividualDrivers/asy_shtc3_driver.py` — from Adafruit's
  [`Adafruit_CircuitPython_SHTC3`](https://github.com/adafruit/Adafruit_CircuitPython_SHTC3),
  © 2017 Scott Shawcroft / © 2020 Bryan Siepert for Adafruit Industries, MIT.
- `legacy/firmware/python/CommonDrivers/microdot.py`, `captive_dns.py`, `asy_udp_socket.py` —
  covered by the Microdot, Apache-2.0 and author-permitted entries.
- `legacy/firmware/python/CommonDrivers/async_connect.py` — its NTP reply parse and RTC idiom
  repeat micropython-lib's `ntptime.py` (NTP entry above); no header.
- `legacy/dev_drivers/` — the dev unit's filesystem as captured on 2026-08-27, kept
  byte-identical, so its copies carry no headers: `microdot.py` (Microdot, © 2019 Miguel
  Grinberg, MIT, an older snapshot), `voc_algorithm.py` (the DFRobot translation), and the
  device's versions of `asy_bmp3xx_driver.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py`,
  `asy_fram_driver.py`, `asy_udp_socket.py` and `async_connect.py`, whose origins are the legacy
  entries above.

## Apache License 2.0 (derived, kept as a separate license within this MIT repo)

Per `SPECIFICATION.md` Part F.4, this project's own MIT license does not override the terms
attached to code derived from an Apache-2.0 project - the derived portion stays under Apache-2.0.

- `src/asy_captive_dns.py`'s `DNSQuery` class (and its pre-refactor
  `legacy/firmware/python/CommonDrivers/` ancestor) - the packet parsing/building logic (variable
  names `tipo`/`ini`/`lon`, the exact `\x81\x80` header/`\xC0\x0C` pointer/`0x3C` TTL byte
  layout, and matching inline comments) is a near-verbatim derivative of
  [`p-doyle/Micropython-DNSServer-Captive-Portal`](https://github.com/p-doyle/Micropython-DNSServer-Captive-Portal)'s
  `main.py`, licensed Apache License 2.0. That upstream repo's own `LICENSE` file ships the
  Apache-2.0 boilerplate with the copyright-holder line unfilled; "p-doyle" (the GitHub account
  the project is published under) is the only identity available, and is used as the attributed
  name here and in `src/LICENSE-captive_dns` (a sibling file, not embedded in `asy_captive_dns.py`
  itself, matching the `ext/LICENSE-microdot` pattern). The file's SPDX header reads
  `Apache-2.0 AND MIT`: Apache-2.0 for `DNSQuery`, MIT for the rest (`CaptiveDNS` and the
  helpers). Holder: "p-doyle", the account the project is published under; year: 2019, from
  upstream's first commit of `main.py` (`110ce2f`, 2019-08-05; its `LICENSE` came later, in
  `27cc627`, 2021-04-17). Upstream ships no `NOTICE` file at any of its commits, so
  `src/LICENSE-captive_dns` appends none. Corroborating evidence:
  [`metachris/micropython-captiveportal`](https://github.com/metachris/micropython-captiveportal)
  (MIT-licensed) carries the identical `DNSQuery` class and states in its own README that it's
  "based on" p-doyle's repo - confirming the Apache-2.0 origin isn't erased by a later MIT
  relicensing of a fork. p-doyle's README in turn credits two earlier, older repos
  (`Matt4/micropython-captive-portal-network-setup`, `amora-labs/micropython-captive-portal`) as
  its own basis; the trail wasn't traced further back than p-doyle's repo, the closest
  well-identified link.
  Changes made in this project's version (Apache-2.0 §4(b) notice): ported from a raw blocking
  `socket` to `UDPSocket`/`asyncio`; in the `src/` version, also added type hints,
  `PrintLogHistory`-backed logging/errno reporting, off-subnet request filtering, recv-failure
  backoff, a root-domain-query parsing fix, QTYPE-dependent answers (the A record for A/ANY, an
  empty NOERROR reply otherwise), and a query must be a single-question query with plain labels
  and a name of at most 255 octets.
  Ruled out as *not* the source for this file, despite superficial DNS-server similarity: three
  of the other candidates the project owner asked to check -
  [`jczic/MicroDNSSrv`](https://github.com/jczic/MicroDNSSrv) (MIT, thread-based, unrelated
  packet-building code/header bytes) and
  [`belyalov/tinydns`](https://github.com/belyalov/tinydns) (MIT, `int.from_bytes`-based parsing,
  different header/pointer bytes) - neither matches this file's structure or byte layout; the
  shared DNS-protocol bytes they do have in common come from RFC 1035 itself, not copying.

## What the firmware image and the website contain

A device image (`scripts/build_firmware.py`) is MicroPython v1.29.0's `RPI_PICO_W` build with this
project's modules frozen in. Compiled in: MicroPython (MIT, its `LICENSE` summarising its `lib/`
tree) with rp2's `mutex_extra.c`/`clocks_extra.c` (BSD-3-Clause), pico-sdk, lwIP, littlefs,
re1.5 (BSD-3-Clause), oofatfs (BSD-1-Clause), uzlib (Zlib), `lib/libm` (newlib/fdlibm notices in
each file), TinyUSB (MIT), mbedTLS (its dual license, Apache-2.0 OR GPL-2.0-or-later; this image
uses it under Apache-2.0, and it ships no `NOTICE` file), BTstack (© BlueKitchen GmbH; its own
`LICENSE` permits non-commercial use only, so the image relies on Raspberry Pi's grant for its
Pico W products, `lib/pico-sdk/src/rp2_common/pico_btstack/LICENSE.RP`), and cyw43-driver with
the CYW43439 Wi-Fi/Bluetooth firmware and NVRAM blobs it carries (George Robotics; used under its
`LICENSE.RP`, which permits use and redistribution only with Raspberry Pi silicon such as the
RP2040 and requires a binary to reproduce its notice — its general `LICENSE` is non-commercial
only). Frozen from the board manifest: micropython-lib packages (`bundle-networking`, `aioble`,
`onewire`, `ds18x20`, `dht`, `neopixel`; MIT unless a package names otherwise) and the port's own
`ports/rp2/modules/`. Frozen from this repo: the device's own `src/` modules as buildgen resolves
them (MIT, with the attributed files above and the Apache-2.0 `DNSQuery`), `ext/microdot.py`
(MIT), the generated device module and boot entry, and `frozen_html`, which holds the website and
freezefs's `ffsmount.py` code (MIT). No license text is frozen: the build stages `.py` modules
only. The website is this project's own `html/`, `js/` and CSS; it bundles no npm package
(`package.json` holds development dependencies only).

**Publishing an image** (agent, 2026-09-30; owner-reviewed, 2026-10-02; public MIT repository,
owner, 2026-09-26): none is published today — CI builds one per device and uploads none. An image
that leaves the owner's hands ships with a notices file holding, from the pinned checkout:
MicroPython's `LICENSE`; the license text of every compiled `lib/` component above — the
submodule's license file (for BTstack also pico-sdk's `pico_btstack/LICENSE.RP`, for cyw43-driver
its `LICENSE.RP`), or for an in-tree component (littlefs, oofatfs, uzlib, re1.5, libm) the notice
in its source headers — plus any `NOTICE` file an Apache-2.0 component ships; micropython-lib's
`LICENSE`; `ext/LICENSE-microdot`; `ext/freezefs/LICENSE`; `src/LICENSE-captive_dns`; the MIT
notices of the Adafruit-, micropython-lib-, aiodns- and DFRobot-derived files, and Sensirion's
BSD-3-Clause notice for the VOC port's origin.

## Not third-party (built into MicroPython itself)

- The fallback hotspot AP's DHCP behavior (assigning an IP to a client that joins it) comes from
  MicroPython's own core `shared/netutils/dhcpserver.c` (MIT, © 2018-2019 Damien P. George) - part
  of the MicroPython project itself, not a separate third-party dependency this repo vendors or
  derives from, so it needs no license entry of its own beyond this note. Confirmed wired into the
  rp2/cyw43 `AP_IF` path via a live upstream report,
  [`micropython/micropython#17401`](https://github.com/micropython/micropython/issues/17401) (AP-mode
  DHCP server ignoring a custom `ifconfig()` subnet). This project has no DHCP server of its own
  anywhere in `src/`, `legacy/firmware/python/`, `legacy/firmware/modules/`, or `digital_twin/` -
  confirmed by exhaustive search (protocol bytes, ports, opcodes, class names) and by a full
  history scan, including for the specific "single fixed IP to one client" shape the project owner
  remembered possibly having built at some point (no match found in this repo's history either).
  Also checked and ruled out on this basis:
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
    `UDPSocket` (`src/asy_udp_socket.py`; `AsyUDPSocket` in
    `legacy/firmware/python/CommonDrivers/asy_udp_socket.py`): the same overall shape (lazy
    connect, a `ready()`/poll gate, explicit `disconnect()` teardown), though method names differ
    (`send`/`receive` vs. `write`/`recvfrom`). The `src/` class has no combined method: its
    callers pair `write()` with `recvfrom()` themselves; the legacy copy keeps one,
    `write_and_recvfrom()` against karfas's `send_and_receive`. This project's version is
    materially more built out (locking, input validation, `mode="server"` support karfas's
    client-only class doesn't have).
  - `karfas/upy-simple-app` carries no `LICENSE` file, license badge, `README.md`, or header
    comment in either file - confirmed directly. On its own, that would mean no permission granted
    under default copyright law (unlike the permissively-licensed Apache-2.0 `asy_captive_dns.py` case
    above). However, the project owner located and provided the actual context:
    [`micropython/discussions#12967`](https://github.com/orgs/micropython/discussions/12967) (Nov
    2023) shows karfas posting links to exactly these two files, in direct response to a public
    request for async NTP/UDP code, saying "it could be a starting point" - and a third party
    (`bulletmark`) replying that they'd use the files in their own app, with no objection from
    karfas. Treated as the author's own public offer of the code for this kind of reuse - a real,
    checkable basis for permission even without a formal license file. Both copies of the class
    carry an attribution note with the discussion link and no SPDX identifier, since no license is
    named: `src/asy_udp_socket.py` in its three-line header and
    `legacy/firmware/python/CommonDrivers/asy_udp_socket.py` in its own; what changed from
    karfas's `AsyUDPClient` is the comparison above. `src/asy_ntp_client.py` needs no karfas
    note: what reached it through karfas's `asy_ntp_time.py` is micropython-lib's code,
    attributed in its own header.

## Datasheets

`datasheets/` is a git submodule of the private repository `hundertvolt/datasheets`: the vendor
datasheets, the Raspberry Pi PDFs under CC BY-ND 4.0 among them, are not redistributed by this
public repository; commits made before the move still contain them (history not rewritten, owner,
2026-09-28). Nothing in the build, lint, test or CI needs them.
