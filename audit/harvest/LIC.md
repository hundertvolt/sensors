# Harvest — LIC: Licensing and attribution

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 2, MIRROR 9, LIMIT 3, RISK 2, ASSUME 11, SUPPRESS 2, TODO 3, OPENQ 1, DRIFT 14, NOTE 10 — 57 items.


## src/LICENSE-captive_dns

- **LIC.N001** NOTE(LIC) · `src/LICENSE-captive_dns:1-3` — "This license covers the DNS
  query-parsing/response-building logic in src/captive_dns.py's DNSQuery class (and its unpromoted
  ancestor..." — Apache-2.0 scope is declared as the `DNSQuery` class only (plus legacy
  `python/CommonDrivers/captive_dns.py`), not the whole file; the file's own SPDX header
  (`src/captive_dns.py:1-2`) is file-level. · covered-by: LIC.S04 · [H01]
- **LIC.N002** NOTE(LIC) · `src/LICENSE-captive_dns:5-6` — "Micropython-DNSServer-Captive-Portal
  https://github.com/p-doyle/Micropython-DNSServer-Captive-Portal" — Upstream provenance named:
  p-doyle's repo, Apache-2.0. · related: LIC.T03 · [H01]
- **LIC.N003** ASSUME · `src/LICENSE-captive_dns:8-10` — "ships the Apache License 2.0 boilerplate with
  the copyright-holder line unfilled; \"p-doyle\" ... is the only identity available" — Attributed
  copyright holder is inferred from the GitHub account name, not stated upstream. · related: LIC.T03 ·
  [H01]
- **LIC.N004** ASSUME · `src/LICENSE-captive_dns:201` — "Copyright 2019 p-doyle
  (Micropython-DNSServer-Captive-Portal contributors)" — The appendix line fills in a year (2019) and
  holder that l.8-10 says upstream left unfilled; the year's source is not stated here or in
  THIRD_PARTY_LICENSES.md:128-145 (low). · related: LIC.T03 · [H01]
- **LIC.N005** MIRROR · `src/LICENSE-captive_dns:10-11` — "See THIRD_PARTY_LICENSES.md for the full
  derivation chain and what was changed in this project's version." — Derivation chain and Apache §4(b)
  change notice live in THIRD_PARTY_LICENSES.md:128-155, the header in `src/captive_dns.py:1-3`; three
  places must agree. · related: LIC.T03, LIC.T08 · [H01]
- **LIC.N006** DRIFT · `THIRD_PARTY_LICENSES.md:149-151 (read for the l.10 cross-reference)` — "three of
  the other candidates the project owner asked to check -" — Says three ruled-out candidates but lists
  two (MicroDNSSrv, tinydns) (low, noticed incidentally). · [H01]
- **LIC.N007** OPENQ · `src/LICENSE-captive_dns (whole file)` — licence text file placed in `src/`,
  which CLAUDE.md says is "copied flat ... and frozen" — Whether this non-.py file ships in / is
  excluded from the frozen image is not stated here (low). · related: LIC.T05 · [H01]

## src/asy_bmp3xx_driver.py

- **LIC.N008** NOTE(LIC) · `src/asy_bmp3xx_driver.py:1-3` — "SPDX-FileCopyrightText: 2018 Carter Nelson
  for Adafruit Industries (original adafruit_bmp3xx ... restructured/rewritten" — Adafruit MIT
  provenance; must match THIRD_PARTY_LICENSES.md entry. · related: LIC.T01 · [H01]

## src/asy_dns_client.py

- **LIC.N009** NOTE(LIC) · `src/asy_dns_client.py:1-3` — "SPDX-FileCopyrightText: Copyright (c) 2024
  Volodymyr Shymanskyy ... Inspired by github.com/vshymanskyy/aiodns, not a port" — File-level
  third-party copyright/MIT header on a file declared "not a port"; scope of the attribution vs the doc
  entry (THIRD_PARTY_LICENSES.md:76-84). · related: LIC.T08 · [H01]
- **LIC.N010** DRIFT · `THIRD_PARTY_LICENSES.md:76-77 vs src/asy_dns_client.py:3` — "its own module
  docstring already states \"Inspired by ... not a port\"" — The statement is a `#` comment at :3, not
  the module docstring (:5) (low). · related: LIC.T08 · [H01]

## src/asy_fram_driver.py

- **LIC.N011** NOTE(LIC) · `src/asy_fram_driver.py:1-3, 6` — "2018 Michael Schroeder for Adafruit
  Industries (original adafruit_fram ...)" / "RDID handling and dual-chip detection are this project's
  own addition" — Adafruit MIT provenance with a declared split of own vs derived parts. · related:
  LIC.T01 · [H01]

## src/asy_isl29125_driver.py

- **LIC.N012** NOTE(LIC) · `src/asy_isl29125_driver.py:1-3` — "Copyright (c) 2023 Jose D. Montoya
  (original MicroPython_ISL29125) - restructured/rewritten" — MIT provenance; THIRD_PARTY_LICENSES.md
  carries two entries for this file. · related: LIC.S01, LIC.T01 · [H01]

## src/asy_ntp_client.py

- **LIC.N013** NOTE(LIC) · `src/asy_ntp_client.py:1-3` — "Copyright (c) 2013, 2014 micropython-lib
  contributors ... Overlaps ntptime.py in the query byte, timestamp read and epoch delta" — Names only
  micropython-lib; THIRD_PARTY_LICENSES.md says karfas attribution was added to both files. ·
  covered-by: LIC.S05 · [H01]

## src/asy_scd30_driver.py

- **LIC.N014** NOTE(LIC) · `src/asy_scd30_driver.py:1-3` — "Copyright (c) 2020 Bryan Siepert for
  Adafruit Industries ... From adafruit_scd30, restructured" — Adafruit MIT provenance. · related:
  LIC.T01 · [H01]

## src/asy_sgp40_driver.py

- **LIC.N015** NOTE(LIC) · `src/asy_sgp40_driver.py:1-3` — "Copyright (c) 2020 Bryan Siepert for
  Adafruit Industries ... From adafruit_sgp40, restructured" — Adafruit MIT provenance. · related:
  LIC.T01 · [H01]

## src/asy_udp_socket.py

- **LIC.N016** MIRROR · `src/asy_udp_socket.py:1-3` — "Attribution, no formal SPDX identifier: this
  class's shape is close to karfas's AsyUDPClient... offered publicly by its author for exactly this
  reuse." — Reuse without a formal licence; must match THIRD_PARTY_LICENSES.md's account · related:
  LIC.S05 · [H02]

## src/captive_dns.py

- **LIC.N017** MIRROR · `src/captive_dns.py:1-3` — "SPDX-License-Identifier: Apache-2.0 / DNSQuery
  derives from its main.py - changes per Apache-2.0 SS4(b): THIRD_PARTY_LICENSES.md." — File-level SPDX
  header vs doc scoping Apache-2.0 to `DNSQuery` only · covered-by: LIC.S04 · [H02] ⟨quote not matched
  at the anchor⟩

## src/voc_algorithm.py

- **LIC.N018** MIRROR · `src/voc_algorithm.py:1-3` — "SPDX-License-Identifier: MIT / Ported from
  DFRobot's Python translation, not Sensirion's C - provenance: THIRD_PARTY_LICENSES.md." —
  Attribution/provenance header must match the licence doc · related: LIC.T01 · [H02] ⟨quote not matched
  at the anchor⟩

## ext/LICENSE-microdot

- **LIC.N019** MIRROR · `ext/LICENSE-microdot:1-3` — "MIT License / Copyright (c) 2019 Miguel Grinberg"
  — Licence text for vendored Microdot; matches THIRD_PARTY_LICENSES.md:15-20 ("© 2019 Miguel Grinberg,
  MIT") · covered-by: LIC.T02 · [H02]

## ext/microdot.py

- **LIC.N020** MIRROR · `ext/microdot.py:1-7` — "The ``microdot`` module defines a few classes that help
  implement HTTP-based servers" — No version, licence or provenance marker in the file itself; the
  `v2.6.2` pin and "byte-identical, 2026-09-10" claim live only in THIRD_PARTY_LICENSES.md:15-20,
  SPECIFICATION.md:62/289 and CLAUDE.md · covered-by: LIC.T02 · [H02]

## ext/freezefs/LICENSE

- **LIC.N021** DRIFT · `ext/freezefs/LICENSE:3` — "Copyright (c) 2022 bixb922" — Each
  `ext/freezefs/*.py` header says "(c) 2023 Hermann Paul von Borries"; THIRD_PARTY_LICENSES.md:21-23
  cites "© 2022 bixb922" (same author presumably; name/year differ) (low) · related: LIC.T02 · [H02]
- **LIC.N022** DRIFT · `ext/freezefs/LICENSE:1` — "MIT License" — Version identity: SPECIFICATION.md:63
  and `scripts/build_frozen_html.sh:11,30` say "freezefs 2.4"; THIRD_PARTY_LICENSES.md:22-23 says
  upstream has no release tags and the copy is `main` synced 2026-09-10 (low) · related: LIC.T02 · [H02]

## ext/freezefs/archive.py

- **LIC.N023** MIRROR · `ext/freezefs/archive.py:1-2` — "# (c) 2023 Hermann Paul von Borries / # MIT
  License" — Per-file attribution (see LICENSE drift above) · related: LIC.T02 · [H02] ⟨quote not
  matched at the anchor⟩

## ext/freezefs/ffsextract.py

- **LIC.N024** MIRROR · `ext/freezefs/ffsextract.py:1-3` — "# (c) 2023 Hermann Paul von Borries / # MIT
  License / # freezefs file extract driver for MicroPython" — Attribution header; extract mode unused by
  the project (`--on-import mount`) · related: LIC.T02 · [H02] ⟨quote not matched at the anchor⟩

## ext/freezefs/ffsmount.py

- **LIC.N025** MIRROR · `ext/freezefs/ffsmount.py:1-3` — "# (c) 2023 Hermann Paul von Borries / # MIT
  License / # MicroPython VFS mount driver for freezefs" — Attribution header; this driver is copied
  into the frozen website module · related: LIC.T02 · [H02] ⟨quote not matched at the anchor⟩

## pyproject.toml

- **LIC.N026** SUPPRESS · `pyproject.toml:186-194` — "src/ and ext/ are frozen flat into one directory"
  / "no file carries a copyright notice by design" — Ignore INP001, CPY001 (attribution in
  THIRD_PARTY_LICENSES.md). · [H09]

## SPECIFICATION.md Part F.4 — Vendor-derived code

- **LIC.N027** SETTLED · `SPECIFICATION.md:3657-3658` — "Adafruit-derived driver code is fair game to
  restructure/rewrite (keeping attribution)" — Policy (dup of CLAUDE.md hard rule). · related: LIC.T01 ·
  [H13]

## README.md

- **LIC.N028** DRIFT · `README.md:732-736` — "every piece of vendored or attribution-derived third-party
  code in one place ... the one area where a specific source couldn't be established" —
  THIRD_PARTY_LICENSES.md now names sources, and the settled `arduino/` exclusion is not stated. ·
  covered-by: LIC.S06 (related LIC.S03) · [H14]

## THIRD_PARTY_LICENSES.md (205 lines; owning area LIC). `arduino/` not read.

- **LIC.N029** DRIFT · `THIRD_PARTY_LICENSES.md:3-7` — "this repo is MIT overall with that one
  documented exception" — The same doc also records a BSD-3 provenance (:93-105) and a reuse with no
  formal licence (:175-205). · covered-by: LIC.S07 · [H15]
- **LIC.N030** ASSUME · `THIRD_PARTY_LICENSES.md:9-11` — "No specific reuse of another project's code
  beyond what's documented below is known" — AI-assistance disclosure. The absence of other reuse is
  unverified. · [H15]
- **LIC.N031** ASSUME · `THIRD_PARTY_LICENSES.md:15-20` — "pinned v2.6.2 — verified byte-identical to
  that tag" — Microdot. `ext/LICENSE-microdot:3` holds the copyright line "Copyright (c) 2019 Miguel
  Grinberg". · covered-by: LIC.T02 · [H15]
- **LIC.N032** LIMIT · `THIRD_PARTY_LICENSES.md:17-18` — "a legacy copy ... also ships as
  python/CommonDrivers/microdot.py" — The legacy copy has no licence text or header beside it and relies
  on `ext/LICENSE-microdot`. (low) · related: LIC.T02 · [H15]
- **LIC.N033** DRIFT · `THIRD_PARTY_LICENSES.md:21-23 vs ext/freezefs/archive.py:1, ext/freezefs/ffsmount.py:1`
  — "© 2022 bixb922, MIT" — The file headers say "(c) 2023 Hermann Paul von Borries", while
  `ext/freezefs/LICENSE:3` says 2022 bixb922. Holder and year differ. (low) · related: LIC.T02 · [H15]
- **LIC.N034** ASSUME · `THIRD_PARTY_LICENSES.md:22-23` — "Upstream publishes no release tags, so
  'current' here means main" — freezefs is vendored with no tag or SHA recorded (synced 2026-09-10). ·
  related: LIC.T02 · [H15] ⟨quote not matched at the anchor⟩
- **LIC.N035** DRIFT · `THIRD_PARTY_LICENSES.md:34-39 vs :46-53` — "src/asy_isl29125_driver.py —
  restructured for asyncio/buildgen from" — The same file has two entries. · covered-by: LIC.S01 · [H15]
- **LIC.N036** DRIFT · `THIRD_PARTY_LICENSES.md:28-29` — "applies to the one non-Adafruit file below" —
  The section lists three non-Adafruit sources (ISL29125, micropython-lib NTP, aiodns). (low) · related:
  LIC.S01 · [H15]
- **LIC.N037** DRIFT · `THIRD_PARTY_LICENSES.md:52-53` — "its FRAM-persisted gain-ratio
  self-calibration" — The code says calibration is RAM-only. · covered-by: LIC.S02 · [H15]
- **LIC.N038** ASSUME · `THIRD_PARTY_LICENSES.md:62-72` — "that repo's default license for files without
  their own metadata.txt-declared license" — The licence of `ntptime.py` is inferred from
  micropython-lib's default. The header is `src/asy_ntp_client.py:1-3`. · related: LIC.T03 · [H15]
- **LIC.N039** ASSUME · `THIRD_PARTY_LICENSES.md:76-86` — "'inspired by, not a port' is an accurate
  description" — `src/asy_dns_client.py:1-2` nevertheless carries Shymanskyy's SPDX copyright line and
  MIT for the whole file. The scope is unclear. (low) · related: LIC.T08 · [H15] ⟨quote not matched at
  the anchor⟩
- **LIC.N040** ASSUME · `THIRD_PARTY_LICENSES.md:102-105` — "DFRobot's MIT terms are the operative ones
  ... not because this project owes it a separate notice" — voc_algorithm: a legal reading of the chain
  from Sensirion's BSD-3 source. · related: LIC.S07 · [H15]
- **LIC.N041** DRIFT · `THIRD_PARTY_LICENSES.md:107-121` — "These still carry their own correct SPDX/MIT
  headers" (only mprls/shtc3 listed) — Legacy derived copies are not listed anywhere:
  `python/IndividualDrivers/asy_bmp3xx_driver.py`, `asy_scd30_driver.py`, `asy_sgp40_driver/__init__.py`
  and `asy_sgp40_driver/voc_algorithm.py` (each has an SPDX header). (low) · related: LIC.T01 · [H15]
- **LIC.N042** DRIFT · `THIRD_PARTY_LICENSES.md:5-7, 128 vs src/captive_dns.py:1-3` — "the derived
  portion stays under Apache-2.0" — The file-level SPDX says Apache-2.0 for the whole file. ·
  covered-by: LIC.S04 · [H15]
- **LIC.N043** ASSUME · `src/captive_dns.py:1 vs THIRD_PARTY_LICENSES.md:133-137` — "Copyright 2019
  p-doyle" — The header states a year, while the doc and `src/LICENSE-captive_dns:8-11` say the upstream
  copyright line is unfilled. The year's source is not documented. (low) · related: LIC.T03 · [H15]
- **LIC.N044** ASSUME · `THIRD_PARTY_LICENSES.md:141-144` — "the trail wasn't traced further back than
  p-doyle's repo" — The provenance chain is incomplete (Matt4, amora-labs). · related: LIC.T03 · [H15]
- **LIC.N045** DRIFT · `THIRD_PARTY_LICENSES.md:149-151` — "three of the other candidates the project
  owner asked to check" — Only two are named (MicroDNSSrv, tinydns). (low) · [H15]
- **LIC.N046** ASSUME · `THIRD_PARTY_LICENSES.md:159-173` — "This project has no DHCP server of its own
  anywhere" — The AP DHCP server comes from MicroPython's `dhcpserver.c` (UF2 content). · related:
  LIC.T06 · [H15]
- **LIC.N047** RISK · `THIRD_PARTY_LICENSES.md:194-203` — "Treated as the author's own public offer of
  the code for this kind of reuse" — karfas code has no licence file. Permission is inferred from a
  forum thread. · related: LIC.S07 · [H15]
- **LIC.N048** DRIFT · `THIRD_PARTY_LICENSES.md:203-205` — "Attribution notes were added to both files
  ... with a link to the discussion thread and a list of what changed" — `src/asy_udp_socket.py:1-3`
  points at the doc with no link or change list. `src/asy_ntp_client.py:1-3` names only micropython-lib.
  Only `python/CommonDrivers/asy_udp_socket.py:2-3` has the link. · covered-by: LIC.S05 · [H15]
- **LIC.N049** LIMIT · `python/CommonDrivers/async_connect.py:426 (absent from the doc)` —
  "struct.unpack("!I", msg[40:44])[0]) - 2208988800" — The legacy NTP code uses the same ntptime idiom,
  with no attribution and no doc entry. (low) · related: LIC.T01 · [H15]
- **LIC.N050** LIMIT · `THIRD_PARTY_LICENSES.md (whole)` — (absent) — The doc does not cover
  `datasheets/` vendor PDFs, UF2 contents (MicroPython, pico-sdk, lwIP, mbedTLS, cyw43) or the
  `arduino/` exclusion. · covered-by: LIC.T07, LIC.T06, LIC.T04 · [H15]

## LICENSE (21 lines)

- **LIC.N051** SETTLED · `LICENSE:1-3` — "MIT License ... Copyright (c) 2026 hundertvolt" — The project
  licence. It gives a single year (2026), while the legacy tree predates the refactor. The scope of year
  and holder is unverified. (low) · related: LIC.S07 · [H15]

## Commit messages (chronological)

- **LIC.N052** NOTE(LIC) · `commit a6abe13` — "Inspired by github.com/vshymanskyy/aiodns (MIT-licensed,
  attributed in the new file's own module docstring) ... not a port of its code" — asy_dns_client
  derivation claim. · related: LIC.T* · [H17 (also H17)]
- **LIC.N053** TODO · `commit 3558647` — "The dropped Adafruit/DFRobot vendor attribution and
  improved-quality/sensortask-wozi.py's task-narrative comment problem were both ... explicitly deferred
  by the project owner" — Attribution deferral. · status: done (THIRD_PARTY_LICENSES.md:27-31 lists
  Adafruit-derived files; improved-quality/ deleted) | related: LIC.T* · [H17]
- **LIC.N054** RISK · `commit 7e6e31f / 383d17b` — "Treated as the author's own public offer of the code
  for this kind of reuse, even without a formal license file" — AsyUDPSocket derived from karfas code
  with no license file; permission inferred from a forum thread. Also the AI-assistance disclosure in
  THIRD_PARTY_LICENSES.md. · related: LIC.S05 · [H17]
- **LIC.N055** TODO · `commit 349ba1e` — "Remaining findings (a systemic
  code-comment-length/narrative-block violation across ~68 new files, dangling references to deleted
  HARDWARE_TEST_PLAN.md/DEV_HARDWARE_BASELINE_PLAN.md section numbers ..., and one licensing-doc
  judgment call) are reported separately" — Comment-length done later (CLAUDE.md: every scope measures
  zero); the "licensing-doc judgment call" is not identified in any later commit. · status: comment part
  done; licensing judgment call UNTRACKED (low) | related: LIC.T* · [H17]
- **LIC.N056** TODO · `commit 90e8c17` — "ext/freezefs/archive.py synced to upstream main (no release
  tags exist)" — Vendored freezefs pinned to an untagged upstream commit; no tag-level provenance. ·
  status: not found as an explicit plan topic (plan treats ext/freezefs as reliance-only) — UNTRACKED
  (low) | related: LIC.T*, WEB · [H17]
- **LIC.N057** SUPPRESS · `commit 1323053` — "Ruff 0.16.6 stabilises CPY001 out of preview (174
  findings); ignored centrally with a reason, since this repo carries no per-file copyright notices by
  design" — CPY001 globally ignored although several src/ files do carry SPDX headers. · tracked:
  pyproject.toml ignore list | related: LIC.T* · [H17]
