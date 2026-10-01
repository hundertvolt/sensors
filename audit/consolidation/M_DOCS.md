# A-C merge DOCS (HEAD 546cdd8)

Files: `THIRD_PARTY_LICENSES.md`, `UART_C_PORT_CHANGELOG.md`, `DEVICE_REFERENCE.md`, `HEAP_FRAGMENTATION_MEASUREMENTS.md`,
`PROJECT_AUDIT_PLAN.md` (project-doc edits only), `README.md`, `BACKLOG.md`, `CLAUDE.md`. Inputs: `site_index.json` `by_file`
plus a scan of every action's Site/Change/Blast slots for each file name (extra hits read in their actions), AC_NOTES 1-43
(43: OR133, SCR Q1 answered (a) — every runner, `test.sh` included, exits 2 on a usage or setting error; written firm
here), and the "Gaps for other clusters" of every finished `M_*.md`.

Standing conventions for every merged change below:
- **End-state names.** Text written here uses the names the other merges leave: modules `asy_api_response`,
  `asy_base_classes`, `asy_captive_dns`, `asy_config_manager`, `asy_crc_checks`, `asy_framing_codecs`, `asy_print_log`,
  `asy_system_service` (A.U10.37); classes `WifiService`, `NotificationService`, `UARTLinkDriver`, `NTPClient`,
  `UDPSocket`, `FRAMManager` (and the `FRAM*Chunk*` family), `CaptiveDNS`, `CRCBase`/`CRCPass`, `FramingBase`/
  `FramingPass`/`FramingCOBS`, `UARTComm`, `BMP3XX_Reader` (A.U10.38); `LockableBuffer` → `RegionBuffer` (A.U16.05);
  `Lockable.asy_lock` → `session_lock` (A.U10.18); legacy paths `legacy/firmware/{python,modules,html_raw}/…`,
  `legacy/firmware/build-<device>.sh`, `legacy/dev_drivers/` (A.U1.01/A.U1.02); SPEC F.5.7/F.5.8/F.5.9 → F.8.1/F.8.2/F.8.3
  (A.U36.532). A text written in an earlier unit than the rename uses the name current then; the rename's own merged
  change (U1/U10/U16/U36) moves every mention in these files in the same commit.
- **No temporary audit ID in permanent text** (G9/R12; AC_NOTES 4): every quoted end-state text below is free of A-/M-/OR-/
  U-numbers; provenance is "(owner, date)" / "(agent, date)", per AC_NOTES 6's normalised form.
- **Arduino wording, one form** (A.U34.01 Blast, G6/R02 V01): "post-audit only (owner, 2026-09-25: 'the C port stays out
  of scope, anything there is post-audit only')"; where a doc also names the secret scan: "(the secret scan too, owner,
  2026-09-30)".
- **MicroPython pin text**: wherever a doc below names "v1.29.0" as the pin or as the version a fact was verified at, the
  text follows the pin B0's dependency refresh leaves (A.SDEP.08 (4), A.SDEP.21), re-stamped in the same SDEP commit.

## THIRD_PARTY_LICENSES.md

### M.DOCS.001 The opening paragraph names every exception and arduino/
- **From**: A.U34.01; A.U10.37/A.U10.38 (names it uses)
- **Site**: `THIRD_PARTY_LICENSES.md:3-7` (`:9-11`, the AI-assistance disclosure, unchanged)
- **Change**: `:3-7` → "This project is public and MIT-licensed (see `LICENSE`). It vendors or derives from other code,
  listed here in one place; most of it is MIT too. The exceptions to "MIT overall": the `DNSQuery` class in
  `src/asy_captive_dns.py` derives from an Apache-2.0 project and stays under Apache-2.0 (see "Apache License 2.0");
  the VOC algorithm port's provenance runs back to Sensirion's BSD-3-Clause C source (see "Ported, kept literal"); and
  the `UDPSocket` class in `src/asy_udp_socket.py` follows code its author offered publicly without a license (see
  "Author-permitted, no formal license"). `arduino/` (the Arduino C implementation of the UART protocol) is outside this
  file and every lint, test, license and secret review: post-audit only (owner, 2026-09-25: 'the C port stays out of
  scope, anything there is post-audit only'; the secret scan too, owner, 2026-09-30)."
- **Resolved**: A.U34.01's own "until the C side is reconciled" clause and the V01 wording of A.U0.38/A.U36.025 elsewhere
  are written in the one form of the conventions above (A.U34.01 Blast "A-C keeps one wording").
- **Unit**: U34
- **Depends**: A.U10.37, A.U10.38 (names)
- **Blast carried by**: README licence paragraph → M.DOCS.(README licence bullet, below); the same exclusion in
  CLAUDE.md/SPEC A.1/J.1/BACKLOG/README → M.DOCS (CLAUDE.md UART bullet), A.U0.38 (SPEC); A.U34.07's check reads entries
  only → TSC
- **Kind**: doc

### M.DOCS.002 The Microdot entry: tag, stubs, hash pin, legacy commit
- **From**: A.SDEP.06 (re-vendored tag), A.SDEP.21 (6), A.U1.20 (`:18` path), A.U19.18 (pin sentence), A.U34.12 (stubs),
  A.U36.030 (legacy copy named exactly)
- **Site**: `THIRD_PARTY_LICENSES.md:15-20`
- **Change**: end state → "- **Microdot** ([`miguelgrinberg/microdot`](https://github.com/miguelgrinberg/microdot),
  `ext/microdot.py` and upstream's type stubs of the same tag, `ext/typings/microdot/__init__.pyi`, `microdot.pyi`,
  `multipart.pyi` (type-checking only, never frozen), pinned `<tag>` — verified byte-identical to that tag on `<date>`
  (pinned by `tests_scripts/test_vendored_microdot.py`); a legacy copy, upstream commit `482ab6d` (between `v2.0.6` and
  `v2.0.7`), also ships as `legacy/firmware/python/CommonDrivers/microdot.py`) — © 2019 Miguel Grinberg, MIT. License
  text: `ext/LICENSE-microdot`. See `CLAUDE.md`/`SPECIFICATION.md` Part A.5 for this project's hands-off vendoring policy
  for this file." `<tag>`/`<date>` are the tag and verification date B0's refresh leaves (`v2.6.2`/2026-09-10 if it held
  the pin back); the stub file set is the one that tag ships under `typings/microdot/`.
- **Resolved**: A.SDEP.06, A.U19.18, A.U34.12 and A.U36.030 each edit this one entry (A.U34.12 "A-C merges into one
  edit") — combined above; the legacy-copy wording is A.U36.030's (the "between `v2.0.1` and `v2.1.0`" text is wrong at
  HEAD, verified there against upstream).
- **Unit**: U36. Stages: U0 (A.SDEP.06: the tag and date follow the re-vendored file — the entry must not name a tag the
  vendored file no longer matches); U1 (A.U1.20: `python/CommonDrivers/microdot.py` → `legacy/firmware/python/
  CommonDrivers/microdot.py`, needed by A.U1.09's old-path check from U1 on); U19 (A.U19.18: "(pinned by
  `tests_scripts/test_vendored_microdot.py`)", with the test); U34 (A.U34.12: the three stub files, which exist since
  A.U8.23 in U8); U36 (A.U36.030: the legacy copy's commit description).
- **Depends**: A.SDEP.06, A.U1.01, A.U8.23, A.U19.18
- **Blast carried by**: CLAUDE.md vendoring bullet → M.DOCS (CLAUDE.md "Hard rules" Microdot bullet); SPEC A.1/A.5 tag →
  A.SDEP.06/A.U8.23 (SPEC); hash table → A.U19.18 (TSC)
- **Kind**: doc

### M.DOCS.003 freezefs is recorded by commit, holder and year
- **From**: A.U34.08 (1), A.SDEP.07, A.SDEP.21 (6)
- **Site**: `THIRD_PARTY_LICENSES.md:21-23`
- **Change**: → A.U34.08 (1)'s entry verbatim: "- **freezefs** ([`bixb922/freezefs`](https://github.com/bixb922/freezefs),
  `ext/freezefs/`: `__main__.py`, `archive.py`, `ffsextract.py`, `ffsmount.py`, `LICENSE`) — upstream publishes no
  release tags; vendored from `main` at `<sha>` (`<date of that commit>`), verified byte-identical on `<date>` and pinned
  by `tests_scripts/test_vendored_freezefs.py`. MIT; upstream's `LICENSE` reads "Copyright (c) 2022 bixb922", and
  `archive.py`, `ffsextract.py` and `ffsmount.py` each open with "(c) 2023 Hermann Paul von Borries, MIT License" — both
  recorded as upstream states them. The frozen website carries `ffsmount.py`'s code with its comment lines stripped by
  freezefs itself (`archive.py:150-175`), so a published image carries this license (below)." `<sha>`/dates: the commit
  A.SDEP.07 leaves (`26be9e339a25e71f506f06a33a2346d6a13a07b8`, 2025-10-25, verified 2026-09-10, if upstream did not move).
- **Resolved**: —
- **Unit**: U34. Stage U0 (A.SDEP.07): if freezefs was re-vendored, `:21-23` names the new commit and date in its HEAD
  wording ("synced and verified byte-identical to it on <date>" → "… at `<sha>` on <date>").
- **Depends**: A.SDEP.07; the hash test (A.U34.08 (4), TSC)
- **Blast carried by**: SPEC `:63` → A.U34.08 (2) (SPEC); `scripts/build_frozen_html.sh:30` → A.U34.08 (3) (SCR, M_SCR);
  hash test → A.U34.08 (4) (TSC); BACKLOG chroot line → M.DOCS (BACKLOG chroot list)
- **Kind**: doc

### M.DOCS.004 The derived-file section intro counts the files it lists
- **From**: A.U34.03 (1)
- **Site**: `THIRD_PARTY_LICENSES.md:27-29`
- **Change**: `:28-29` "applies to the one non-Adafruit file below" → "applies to the two non-Adafruit files below
  (`asy_isl29125_driver.py`, `asy_ntp_client.py`); `asy_dns_client.py` is listed for the credit it gives, as an
  inspiration, not a derivative". "Per `SPECIFICATION.md` Part F.4" kept (F.4 keeps its number; A.U36.532 moves F.5.7-.9
  only).
- **Resolved**: —
- **Unit**: U34
- **Depends**: —
- **Blast carried by**: A.U34.07's one-entry check → TSC
- **Kind**: doc

### M.DOCS.005 One ISL29125 entry, with the calibration as it is
- **From**: A.U34.03 (2)(3); A.U1.20 (`:37` repath, superseded at U34 by the deletion)
- **Site**: `THIRD_PARTY_LICENSES.md:34-39` (first entry), `:46-53` (second)
- **Change**: `:34-39` deleted. `:46-53` → "- `src/asy_isl29125_driver.py` — from
  [`jposada202020/MicroPython_ISL29125`](https://github.com/jposada202020/MicroPython_ISL29125) (archived/deprecated
  December 2024), © 2023 Jose D. Montoya, MIT. What survives from upstream is the register map and the sense of the
  configuration bits; everything else is this project's own, written against FN8424 Rev 3.00 directly: the three-layer
  asyncio structure, the shadow-register single-write model, the destructive-status-read discipline, the auto-range state
  machine, the on-demand gain-ratio measurement (held in RAM and published for the user to apply, never adopted by the
  driver), and all of the config/logging/error machinery."
- **Resolved**: A.U1.20's `:37` repath lands in U1 (A.U1.09's old-path check) and its line goes in U34.
- **Unit**: U34. Stage U1: `:37` `python/IndividualDrivers/…` → `legacy/firmware/python/IndividualDrivers/…`.
- **Depends**: M.DOCS.009 (the legacy entry the deleted paragraph pointed to)
- **Blast carried by**: one-entry check → A.U34.07 (TSC); DEVICE_REFERENCE's ISL29125 procedure → M.DOCS (DEVICE_REFERENCE)
- **Kind**: doc

### M.DOCS.006 The NTP entry names the renamed socket class
- **From**: A.U10.38 (`AsyUDPSocket` → `UDPSocket`)
- **Site**: `THIRD_PARTY_LICENSES.md:72`
- **Change**: "async/`AsyUDPSocket`/config/retry/timer machinery" → "async/`UDPSocket`/config/retry/timer machinery";
  the rest of the entry unchanged (its "See 'Author-permitted …'" pointer holds).
- **Resolved**: —
- **Unit**: U10
- **Depends**: A.U10.38
- **Blast carried by**: —
- **Kind**: doc

### M.DOCS.007 The aiodns entry says where the credit sits
- **From**: A.U34.03 (4)
- **Site**: `THIRD_PARTY_LICENSES.md:76-79`
- **Change**: "its own module docstring already states '…' (© 2024 Volodymyr Shymanskyy) - this attribution predates this
  licensing review and was found already in place, not added by it. Verified directly against …" → "its header states
  '…' (© 2024 Volodymyr Shymanskyy). Verified against …"; the rest of the entry unchanged.
- **Resolved**: —
- **Unit**: U34
- **Depends**: M.SRC_NET (the resolver header text it quotes, unchanged by SRC_NET's merges beyond the SPDX order)
- **Blast carried by**: —
- **Kind**: doc

### M.DOCS.008 The VOC entry records the chain, the successor, the labelled reading
- **From**: A.U34.04
- **Site**: `THIRD_PARTY_LICENSES.md:93-105`
- **Change**: → A.U34.04's text verbatim ("- `src/voc_algorithm.py` — a literal port of the Python translation in
  [`DFRobot/DFRobot_SGP40`](…)'s `Python/raspberrypi/DFRobot_SGP40_VOCAlgorithm.py`, © 2010 DFRobot Co.Ltd
  (http://www.dfrobot.com), author yangfeng, MIT (that repo's `LICENCE`: "Copyright 2010 DFRobot Co.Ltd", matching this
  file's header). That translation ports Sensirion's Gas Index Algorithm (VOC variant) from
  [`Sensirion/embedded-sgp`](…) (`sgp40_voc_index/sensirion_voc_algorithm.c/.h`; archived April 2024, BSD-3-Clause); the
  maintained successor is [`Sensirion/gas-index-algorithm`](…) (BSD-3-Clause, © 2021 Sensirion AG). Because this file
  ports DFRobot's Python rather than Sensirion's C, DFRobot's MIT terms are treated as the ones governing what was copied
  (agent reading, 2026-08-20; not a verified legal conclusion); Sensirion's BSD-3-Clause is recorded for the full chain,
  and a published image carries its notice too (below). `tests/voc_reference_vectors.py` holds output values computed by
  Sensirion's C (the gas-index-algorithm fixed-point helpers and the archived embedded-sgp algorithm) and contains no
  Sensirion code."). `:90-91`'s section intro unchanged.
- **Resolved**: —
- **Unit**: U34
- **Depends**: A.U12.12 (the data file named; M_TEST_UNIT), M.DOCS.011 (the image notice it refers to)
- **Blast carried by**: SPEC F.4 successor/name map → A.U12.15 (SPEC); `src/voc_algorithm.py:1-3` unchanged
- **Kind**: doc

### M.DOCS.009 The legacy section lists every legacy and snapshot copy
- **From**: A.U34.10, A.U34.03 (5), A.U1.20 (`:107`, `:118`)
- **Site**: `THIRD_PARTY_LICENSES.md:107-121`
- **Change**: section → A.U34.10's text verbatim, heading "## Legacy tree (`legacy/`, reference-only, never edited)" with
  the seven bullets (the pre-refactor driver versions with their own SPDX headers; the DFRobot translation; the header-less
  `asy_fram_driver.py`; mprls and shtc3, text unchanged; `CommonDrivers/microdot.py`, `captive_dns.py`,
  `asy_udp_socket.py` covered by their entries; `async_connect.py`'s `ntptime.py` idiom; `legacy/dev_drivers/` as
  captured on 2026-08-27, byte-identical, header-less). `:118-121` ("… used to be listed here too …") goes.
- **Resolved**: A.U1.20 repaths `:107, :118` inside the section A.U34.10 rewrites — A.U34.10's text wins, with A.U1.20's
  paths (U34 conflicts note).
- **Unit**: U34. Stage U1: `:107` heading path and `:118` path → `legacy/firmware/python/IndividualDrivers/` (A.U1.09).
- **Depends**: A.U1.01, A.U1.02
- **Blast carried by**: none checked (legacy outside every check, CLAUDE.md legacy rule; A.U34.07 reads `src/` entries)
- **Kind**: doc

### M.DOCS.010 The Apache-2.0 entry: scope, holder, year, §4(b) list
- **From**: A.U34.05 (4), A.U1.20 (`:128`), A.U10.37/A.U10.38 (`:128`, `:136`, `:146`), A.U18.01, A.U18.02 (§4(b) list)
- **Site**: `THIRD_PARTY_LICENSES.md:128-148`
- **Change**: `:128` "`src/captive_dns.py`'s `DNSQuery` class (and its pre-refactor `python/CommonDrivers/` ancestor)" →
  "`src/asy_captive_dns.py`'s `DNSQuery` class (and its pre-refactor `legacy/firmware/python/CommonDrivers/` ancestor)";
  `:136-137` "embedded in `captive_dns.py` itself" → "embedded in `asy_captive_dns.py` itself"; after the
  upstream-`LICENSE` sentence (`:133-137`) the sentence "The file's SPDX header reads `Apache-2.0 AND MIT`: Apache-2.0 for
  `DNSQuery`, MIT for the rest (`CaptiveDNS` and the helpers). Holder: "p-doyle", the account the project is published
  under; year: upstream's first commit of `main.py` (`<sha>`)." (or "no year: upstream states none" if unreachable) and
  "upstream ships a `NOTICE` file, appended to `src/LICENSE-captive_dns`" / "upstream ships no NOTICE file" per A.U34.05
  (1); `:146` "to `AsyUDPSocket`/`asyncio`" → "to `UDPSocket`/`asyncio`"; the §4(b) list `:145-148` ends "…, recv-failure
  backoff, a root-domain-query parsing fix, QTYPE-dependent answers (the A record for A/ANY, an empty NOERROR reply
  otherwise), and a query must be a single-question query with plain labels and a name of at most 255 octets."
- **Resolved**: A.U18.01/A.U18.02 and A.U34.05 edit independent sentences (U34 conflicts note) — written as one end state.
- **Unit**: U34. Stages: U1 (`:128` path), U10 (file/class names), U18 (the two §4(b) items, with M.SRC_NET.003/.008),
  U34 (scope/holder/year, NOTICE).
- **Depends**: M.SRC_NET.002, M.SRC_NET.005 (header and licence file carry the same holder/year)
- **Blast carried by**: SPDX header → M.SRC_NET.002; `LICENSE-captive_dns:201` → M.SRC_NET.005; check accepting
  `Apache-2.0 AND MIT` → A.U34.07 (TSC); egress-list entry if unreachable → A.U34.05 (1) (audit record)
- **Kind**: doc

### M.DOCS.011 A section states what the image and website contain
- **From**: A.U34.09 (1)
- **Site**: new section "## What the firmware image and the website contain" before "## Not third-party (built into
  MicroPython itself)" (`:157`)
- **Change**: A.U34.09 (1)'s section text verbatim (compiled-in components with their licences, frozen micropython-lib
  packages and port modules, this repo's frozen modules, "No license text is frozen", the website bundles no npm
  package, and "**Publishing an image** (agent, 2026-09-30; public MIT repository, owner, 2026-09-26): …" with its notice
  list). The executor reads each submodule licence at the commit named and each in-tree component's source headers,
  corrects any licence the file contradicts, records which of mbedTLS's two licences the image uses and any Apache-2.0
  `NOTICE`; the component list and commits are those of the pin B0's refresh leaves (re-derived if it moved).
- **Resolved**: —
- **Unit**: U34
- **Depends**: A.U0.03 (corpus, submodules initialised), A.SDEP.08 (pin), M.DOCS.003, M.DOCS.008
- **Blast carried by**: README licence bullet → M.DOCS (README); no check (prose; a published image is outside CI)
- **Kind**: rule, doc

### M.DOCS.012 The DHCP note names the legacy paths
- **From**: A.U1.20 (`:166`); A.SDEP.08 (4) (re-read only)
- **Site**: `THIRD_PARTY_LICENSES.md:157-173`
- **Change**: `:166` "anywhere in `src/`, `python/`, `modules/`, or `digital_twin/`" → "anywhere in `src/`,
  `legacy/firmware/python/`, `legacy/firmware/modules/`, or `digital_twin/`". The `dhcpserver.c` note is re-read at the
  refreshed pin (A.SDEP.08 (4)); it changes only if the fact moved. A.U14.22's related upstream issue (`:162-165`) is
  unchanged.
- **Resolved**: —
- **Unit**: U1 (the conditional SDEP re-stamp lands at U0 if needed)
- **Depends**: A.U1.01
- **Blast carried by**: A.U1.09 (TSC)
- **Kind**: doc

### M.DOCS.013 The author-permitted entry: current class, current paths, who carries what
- **From**: A.U34.06 (2), A.U18.13 ("retries" drops), A.U18.46 ("context-manager support" drops), A.U10.37/A.U10.38
  (`:188`, `:196`), A.U1.20 (`:188`)
- **Site**: `THIRD_PARTY_LICENSES.md:175-205`
- **Change**: `:188` "`AsyUDPSocket` (`src/asy_udp_socket.py`, `python/CommonDrivers/asy_udp_socket.py`)" → "`UDPSocket`
  (`src/asy_udp_socket.py`, `legacy/firmware/python/CommonDrivers/asy_udp_socket.py`)"; `:191-193` "materially more
  built out (locking, retries, context-manager support, input validation, `mode="server"` support …)" → "materially more
  built out (locking, input validation, `mode="server"` support …)"; `:196` "Apache-2.0 `captive_dns.py` case" →
  "Apache-2.0 `asy_captive_dns.py` case"; `:203-205` → A.U34.06 (2)'s text ("Both copies of the class carry an attribution
  note with the discussion link and no SPDX identifier, since no license is named: `src/asy_udp_socket.py` in its
  three-line header and `legacy/firmware/python/CommonDrivers/asy_udp_socket.py` in its own; what changed from karfas's
  `AsyUDPClient` is the comparison above. `src/asy_ntp_client.py` needs no karfas note: what reached it through karfas's
  `asy_ntp_time.py` is micropython-lib's code, attributed in its own header.").
- **Resolved**: independent sentences (U34 conflicts note) — one end state.
- **Unit**: U34. Stages: U1 (`:188` legacy path), U10 (names), U18 (the two dropped features, with M.SRC_NET.026/.031).
- **Depends**: M.SRC_NET.025 (the header A.U34.06 (1) writes), M.SRC_NET.031
- **Blast carried by**: header form check → A.U34.07 (TSC)
- **Kind**: doc

### M.DOCS.014 A datasheets section states the private submodule
- **From**: A.U34.09 (2)
- **Site**: new section "## Datasheets" at the end
- **Change**: "`datasheets/` is a git submodule of the private repository `hundertvolt/datasheets`: the vendor datasheets,
  the Raspberry Pi PDFs under CC BY-ND 4.0 among them, are not redistributed by this public repository; commits made
  before the move still contain them (history not rewritten, owner, 2026-09-28). Nothing in the build, lint, test or CI
  needs them."
- **Resolved**: —
- **Unit**: U34 (after A.U28.35's move in U28). Precondition (AC_NOTES 37): the owner confirms push access to
  `hundertvolt/datasheets` before A.U28.35 runs; if the move does not happen, this section is not written.
- **Depends**: A.U28.35
- **Blast carried by**: README/CLAUDE.md/SPEC A.6 location text → M.DOCS (README, CLAUDE.md "Datasheets"), A.U36.545 (SPEC)
- **Kind**: doc

## UART_C_PORT_CHANGELOG.md

Entry policy for this file (CLAUDE.md UART rule; A.U17.30): every merged change to `src/asy_uart_comm.py` — and to the
layers below it where a change could reach the wire (A.U17.08's scope line) — has one row; one row may carry several
constituents of one kind. Row numbers below are the planned landing order (U2 → U35, within a unit by action number); the
executor takes the next free number at landing, so a different landing order renumbers a row without changing its text.
Every row from M.DOCS.024 on carries the `Status` cell `applied-python` (A.U17.09; Class B rows landing before U17 gain the
column with the rest at U17). Row texts are written in end-state names; a row landing before U10 uses the names current
then and follows the U10/U16 renames with the rest of the file (M.DOCS.023).

### M.DOCS.015 The header says when the file goes
- **From**: A.U17.08 (`:3-4`)
- **Site**: `UART_C_PORT_CHANGELOG.md:3-4`
- **Change**: "**Temporary file. Delete it once the C implementation has been reconciled** — it exists only to carry
  protocol decisions across the gap until then, and has no value afterwards." → "**Kept until the post-audit C
  reconciliation, and deleted there** (owner, 2026-09-25) — it carries every protocol change across the gap until then
  and has no value afterwards. Deleting it deletes `tests_scripts/test_uart_changelog.py` with it."
- **Resolved**: —
- **Unit**: U17 (with the test it names, M.TSC.152)
- **Depends**: M.TSC.152 (A.U17.11's test)
- **Blast carried by**: CLAUDE.md UART bullet "(a temporary file …)" → M.DOCS (CLAUDE.md UART bullet); SPEC J.1 `:5346-5347`
  → A.U17.08 (SPEC); README "Temporary docs" → M.DOCS (README map); A.U37.03/A.U37.04 (4) keep the file at close (audit
  record)
- **Kind**: doc

### M.DOCS.016 The intro: post-audit wording, owner-validation tag
- **From**: A.U0.38 (V01, `:8-9`), A.U0.30 (`:10`)
- **Site**: `UART_C_PORT_CHANGELOG.md:6-13`
- **Change**: `:8-9` "that reconciliation is outside this project's scope (owner, 2026-09-24), so this file waits for
  whoever takes it up" → "that reconciliation is post-audit only (owner, 2026-09-25: 'the C port stays out of scope,
  anything there is post-audit only'), so this file waits for whoever takes it up"; `:10` "is owner-validated over many
  real transmissions" → "is owner-validated over many real transmissions (owner, 2026-09-11)". The rest unchanged.
- **Resolved**: one arduino wording (conventions).
- **Unit**: U0
- **Depends**: —
- **Blast carried by**: the same V01 sentence in CLAUDE.md/SPEC/BACKLOG/README → M.DOCS (CLAUDE.md, BACKLOG, README), A.U0.38
  (SPEC)
- **Kind**: doc

### M.DOCS.017 Deployment status: the owner holds every unit; C tests are post-audit
- **From**: A.U36.025 (UCL half)
- **Site**: `UART_C_PORT_CHANGELOG.md:14-22`
- **Change**: two sentence edits, the rest unchanged: `:15-16` "There is no device in the field running it, so **no pair
  can be broken by" → "The owner holds every unit (owner, 2026-09-26), so **no pair can be broken by"; `:18-21` "Real
  hardware running the C side exists and can be connected to the dev board, so the promoted module is testable against
  the genuine second implementation rather than only against itself over the crossover jumper." → "Real hardware running
  the C side exists; testing the Python module against it is part of that post-audit reconciliation (owner, 2026-09-25),
  so until then the hardware tests prove Python-to-Python interoperation over the crossover jumper only."
- **Resolved**: —
- **Unit**: U36
- **Depends**: M.DOCS.016
- **Blast carried by**: CLAUDE.md `:131-137` → M.DOCS (CLAUDE.md UART bullet); no test pins either text
- **Kind**: doc

### M.DOCS.018 The scope line covers the protocol and the layers below it
- **From**: A.U17.08 (`:27`)
- **Site**: `UART_C_PORT_CHANGELOG.md:27`
- **Change**: "Every change to the module during its `src/` promotion gets an entry, in one of two classes:" → "Every
  change to the protocol module (`src/asy_uart_comm.py`, and the layers below it where a change could reach the wire)
  gets an entry, in one of two classes; a changed `const()` wire constant or recovery timing is Class A by definition:"
- **Resolved**: —
- **Unit**: U17
- **Depends**: —
- **Blast carried by**: CLAUDE.md UART bullet's entry clause → M.DOCS (CLAUDE.md UART bullet)
- **Kind**: doc

### M.DOCS.019 One closed status set; rows in number order; a Status column for Class B
- **From**: A.U17.09
- **Site**: `UART_C_PORT_CHANGELOG.md:48-49` (status line), `:53-66` (Class A table), `:70-103` (Class B table)
- **Change**: `:48-49` → "Status values, a closed set: `proposed` (agreed in principle, not yet implemented),
  `applied-python` (live in `src/`; pending the C side for Class A, final for Class B), `recorded` (nothing to change on
  either side — an existing rule written down so the C side is checked against it), `reconciled` (done on both sides —
  the entry can be removed). A qualifier goes into the entry's own text, never into the Status cell." Class A rows
  ordered A1 … A14 (A13/A14 from M.DOCS.022); Status cells: A4 `recorded`, A8 `recorded`, A6 `applied-python`, A7
  `applied-python`, A11 `proposed`; A1-A3, A5, A9, A10, A12 unchanged. Class B gains a trailing `Status` column, every
  row `applied-python`.
- **Resolved**: —
- **Unit**: U17
- **Depends**: M.DOCS.021 (A7/A8/A11 cells, same rows), M.DOCS.024 (rows B33-B52 already present)
- **Blast carried by**: set and order checked → M.TSC.152 (A.U17.11 (2) (d)(e))
- **Kind**: doc

### M.DOCS.020 A constants table the check reads
- **From**: A.U17.11 (1)
- **Site**: new section "## Constants the check reads" after "## How to use this file"
- **Change**: one sentence "Every integer `const()` of `src/asy_uart_comm.py` except the log codes, with its value, its
  class and the entry that last changed it; `tests_scripts/test_uart_changelog.py` fails when this table and the module
  disagree." and a table `| Name | Value | Class | Last entry |`, one row per module-level `NAME = const(<int>)` whose
  name does not start with `_ERR_`/`_WRN_`, written from the module as it stands after M.SRC_NET.151/.152/.153 (no
  `_REJECT_MAP_LEN`; `_CMD_ACK`/`_CMD_GET`/`CMD_SET` under their U10 names; `_TICKS_HORIZON_MS`, `_POLL_WAIT_MAX_MS`
  present); `Last entry` `baseline` for every row. Class A: `_CMD_ACK`, `_CMD_GET`, `CMD_SET`, `_HEADER_LEN`, the
  `_MSG_*` offsets, `_UID_MAX`, `_CHUNKS_MAX`, `_PAYLOAD_MIN`, `_PAYLOAD_MAX`, `_RESYNC_NUM`, `_RESYNC_DEN`,
  `_DRAIN_BOUND_MULT`, `_MIN_CHUNKS`, `_BACKOFF_MULT`, `_BACKOFF_MAX_MULT`; Class B: `_GATE_STEP_MS`,
  `_GC_PAUSE_WORST_MS`, `_POLL_JITTER_MS`, `_DIAG_RESYNC_STREAK`, `_CALLBACK_PAIR_LEN`, `_CMD_ID_MAX`,
  `_TICKS_HORIZON_MS`, `_POLL_WAIT_MAX_MS`. A constant present in the module but in neither list is classed by the same
  rule at execution (a wire value or recovery timing is A) and reported in the unit's commit.
- **Resolved**: —
- **Unit**: U17 (after A.U17.20's two constants; every constant-changing action — A.U2.20, A.U3.02, A.U10.29, A.U17.20 —
  lands at or before U17)
- **Depends**: M.SRC_NET.151, M.SRC_NET.152, M.SRC_NET.153, M.DOCS.019
- **Blast carried by**: the check → M.TSC.152; SPEC J.1 changelog bullet → A.U17.11 (SPEC)
- **Kind**: doc

### M.DOCS.021 Class A rows A4-A11: provenance, current names, the CRC selection as built
- **From**: A.U0.30 (A7 why-cell, A8), A.U0.39 (L17: A11 decision cell), A.U17.09 (statuses, M.DOCS.019), A.U10.37/A.U10.38
  (names), adherence (A.S0930.01 makes the CRC a TOML key: A7's "Status as merged" sentence would state a dead mechanism)
- **Site**: `UART_C_PORT_CHANGELOG.md:58` (A4), `:60` (A8), `:61` (A7), `:64` (A11)
- **Change**: A7 why-cell "Not a deliberate change — inherited from `asy_uart_driver.py`'s own promotion, which had no
  callers, so nobody noticed." → "A deliberate swap (agent, 2026-07-23, `7f4ebc3`: the embedded, non-standard CRC16
  replaced by `asy_crc_checks.py`'s `CRCBase` family); its result, the standard CRC-16/CCITT-FALSE, is the correct state
  (owner, 2026-09-29: 'adhering to the standards, using the CRC functions module - is the correct one')."; A7 change
  cell "→ `crc_checks.py`'s MSB-first" → "→ `asy_crc_checks.py`'s MSB-first"; A7 verify cell "run the link with
  `CRC_Pass`" → "with `CRCPass`", and its last two sentences ("**Status as merged: the promoted module leaves the bus
  driver's `crc=` unset, …** … not something the promotion did") → "**Status as built: each `uart_link` end's TOML `crc`
  key selects its CRC (`"none"`, the default, is `CRCPass`; `"crc16"` is `CRC16`) and the build refuses a pair whose
  ends differ; `dev` keeps `"none"`, so no CRC bytes reach the wire on the bench link.** The flag day is therefore
  *recorded and not yet triggered* — selecting `"crc16"` at both ends of a Python↔C pair is what triggers it."; A8
  "an author-confirmed invariant" → "an owner-confirmed invariant (owner, 2026-09-11, `7e8cf44`)"; A11 decision cell
  "**Design question resolved (owner decision, 2026-09-11): …**" gains "(owner, 2026-09-11, `b131169`)" in place of
  "(owner decision, 2026-09-11)", and "`UART_Comm` stays CRC-agnostic" → "`UARTComm` stays CRC-agnostic"; Status cells per
  M.DOCS.019.
- **Resolved**: A.U0.30 keeps "the rest of the row … unchanged"; the A7 "Status as merged" rewrite is an agent addition
  (adherence: docs hold current state, A.S0930.01's TOML key; OR123 "CRC mode by TOML key", owner, 2026-09-30) — OR2.c list.
- **Unit**: U20 (the "as built" sentence lands with A.S0930.01's key). Stages: U0 (A7 why-cell, A8, A11 tag), U10 (names),
  U17 (statuses), U20 (A7's selection sentence).
- **Depends**: A.S0930.01 (GEN, M.GEN's U20 changes)
- **Blast carried by**: SPEC J/E.8 "the dev wiring selects" → A.U0.40 (SPEC); twin/unit both-mode runs → A.S0930.03 (TWIN,
  TEST_UNIT)
- **Kind**: doc

### M.DOCS.022 Two new Class A rows: GET is one chunk; a validated command resets the backoff
- **From**: A.U17.16, A.U17.17, A.U17.30
- **Site**: Class A table, after A12
- **Change**: "| A13 | Reject a GET frame whose `CHUNKS` is not 1 | J.4 defines a GET as a one-chunk train, and a GET
  declaring more chunks was answered as though it were one | That the C sender always emits `CHUNKS = 1` on a GET. A
  receiver-only tightening: a conforming peer is unaffected | applied-python |" and "| A14 | A responder re-listens at
  once after any transaction whose command frame validated and was then answered, declined or aborted mid-train
  (`ListenResult.cmd` set); a listen that returns no command kind backs off (`timeout/2` doubling to `5 × timeout`) | A
  declined command used to send the loop into that backoff, so an initiator retrying after its own resync (about
  `4 × timeout`) could transmit while the responder slept and fail again | That the C responder does not back off after a
  declined or aborted command beyond the initiator's retry window | applied-python |".
- **Resolved**: —
- **Unit**: U17
- **Depends**: M.SRC_NET.159, M.SRC_NET.170, M.DOCS.019
- **Blast carried by**: SPEC J.4/J.5 → A.U17.16/A.U17.17 (SPEC); tests → M_TEST_UNIT (A.U17.16/.17)
- **Kind**: doc

### M.DOCS.023 Existing Class B rows: current names, a resolving pointer, no step label, B26 rewritten
- **From**: A.U10.37/A.U10.38/A.U16.05/A.U10.18 (names in rows B4-B32), A.U36.532 (B24's "F.5.8"), A.U36.544 (3) (B31's
  "WP3"), A.U17.15 + A.U17.13 (B26), A.U36.549 (decision sentences)
- **Site**: `UART_C_PORT_CHANGELOG.md:72-103`
- **Change**: (1) every mention of a renamed symbol follows the rename in its rename's commit: `print_log.py` →
  `asy_print_log.py`, `base_classes.py` → `asy_base_classes.py`, `framing_codecs.py` → `asy_framing_codecs.py`,
  `crc_checks` → `asy_crc_checks`, `UART_Comm` → `UARTComm`, `UartLinkExerciser` → `UARTLinkDriver`, `Framing_COBS`/
  `Framing_Pass` → `FramingCOBS`/`FramingPass`, `AsyFramManager` → `FRAMManager` (U10); `LockableBuffer` → `RegionBuffer`
  (B9, U16); errno/wrnno numbers in B10-B32 stay as written and read through B33's old→new table (A.U2.26). (2) B24
  "(SPECIFICATION.md Part F.5.8)" → "(SPECIFICATION.md Part F.8.2)" (U36, with the move). (3) B31 "WP3 - reverses an
  earlier, incorrect "never" decision …" → "Reverses an earlier, incorrect "never" decision …" (U36). (4) B26 → "| B26 |
  `_resync()` counts the bytes a failed frame read consumed and dropped — a short frame at the inter-part timeout, a CRC
  failure — toward its drained total, through the driver's cumulative `discarded_bytes`; `errno` 89 (`UART_LINK_UNINTELLIGIBLE`)
  now fires for a speak-when-spoken-to peer with a mismatched `payload_size` or CRC, which used to show only repeated
  `errno` 22 and resyncs (owner, 2026-09-26) | A receiver-side diagnostic: nothing on the wire changes and no
  accept/reject rule moves. Worth the C side's attention: a C version of this diagnostic gated on its own drain has the
  same blind spot | applied-python |" (U17). (5) every decision sentence carries its actor and date or loses the
  vocabulary (A.U36.549's three outcomes; e.g. B10's "(owner direction)" gets its date from the trail) (U36).
- **Resolved**: A.U17.15's B26 text says "`errno` 32" and "`errno` 22 plus resync warnings"; it lands in U17, after the U2
  renumbering (errno 32 → 89, 22 → shared 22) and U3 (resyncs print) — written in the numbers current at its landing.
- **Unit**: U36. Stages: U10 (names), U16 (`RegionBuffer`), U17 (B26), U36 (pointer, label, tags).
- **Depends**: A.U36.532 (F.8 exists), M.DOCS.024 (B33's table)
- **Blast carried by**: A.U0.08's citation check resolves F.8.2 → TSC; A.U0.09's vocabulary allow-list empties → TSC
- **Kind**: doc

### M.DOCS.024 New Class B rows B33-B64, in landing order
- **From**: A.U2.26 (+A.U2.20), A.U3.13 (+A.U3.02, A.U3.08; gap M_SRC_NET 6: `_note_valid_frame()`), A.U5.12 (+A.U5.02),
  A.U10.04, A.U10.18, A.U10.29, A.U10.35 (+`set_callback`, M_SRC_NET gap 6), A.U10.37 + A.U10.38, A.U10.44 + A.U32.06,
  A.U10.45, A.U11.31, A.U12.02, A.U12.03, A.U12.16, A.U13.12, A.U13.13, A.U13.14, A.U13.17, A.U13.18, A.U16.05, A.U17.01,
  A.U17.06, A.U17.10, A.U17.14, A.U17.20, A.U17.22, A.U17.26, A.U17.28, A.S0930.07, A.U24.67, A.U30.19, A.U35.44, A.U17.30
  (the numbering rule)
- **Site**: Class B table, after B32
- **Change**: rows (Change | Why no wire effect), each with Status `applied-python` once the column exists:
  - **B33** (U2): "`errno`/`wrnno` values move into the project's global catalog and their constants take the catalog
    names; old → new: errno 10→75, 11→76, 12→21, 13→77, 14→20, 15→78, 16→21, 17→18, 18→79, 19→80, 20→81, 21→82, 22→22,
    23→83, 24→20, 25→84, 26→14, 27→85, 28→86, 29→87, 30→23, 31→88, 32→89, 33→90, 34→21; wrnno 11→54, 13→55, 14→56. The
    numbers in B10-B32 read through this table; B10's numbering sentence is superseded | Logging only: no byte,
    acceptance rule or timing changes".
  - **B34** (U3): A.U3.13's text, completed: "The per-module episode rules of B20/B28/B30/B32 are replaced by the
    project-wide newest-entry rule in `asy_print_log.py`: a repeated identical errno is counted and written through (one
    FRAM history write per fault on a FRAM-backed logger) and spends no new slot. A resync prints instead of persisting;
    a drain that hit its bound still persists `wrnno` 54; a declined command persists `wrnno` 56 each time. The
    fault-cleared warning and the 32-byte declined-id map go, and `_note_valid_frame()` becomes synchronous (one
    coroutine allocation per validated frame removed) | Logging and allocation only: no byte, acceptance or timing change".
  - **B35** (U5): "Constructor: `get_callback`/`set_callback`/`message_callback` become one `callbacks` object
    (`ResponderCallbacks`) and `fram`/`history_length`/`debug` one `log` object (`LogConfig`); `logger=` stays | Python
    API only, no C impact".
  - **B36** (U10): "`_valid_frames` saturates at 2**30 − 1 instead of growing without bound | Only its zero test is read;
    wire unchanged".
  - **B37** (U10): "`UART.asy_lock` (from `Lockable`) renamed `session_lock` | Names only".
  - **B38** (U10): "`CMD_ACK`/`CMD_GET` become module-private (`_CMD_ACK`/`_CMD_GET`); `CMD_SET` stays public | Values and
    wire unchanged".
  - **B39** (U10): "`UARTComm`'s `get_callback`, `set_callback`, `message_callback` and `frame_size` become private
    (`_get_callback`, `_set_callback`, `_message_callback`, `_frame_size`) | Python-internal; no C impact".
  - **B40** (U10): "Modules `framing_codecs`/`crc_checks`/`base_classes`/`print_log` renamed `asy_framing_codecs`/
    `asy_crc_checks`/`asy_base_classes`/`asy_print_log`; classes `UART_Comm` → `UARTComm`, `UartLinkExerciser` →
    `UARTLinkDriver`, `CRC_Base`/`CRC_Pass` → `CRCBase`/`CRCPass`, `Framing_Base`/`Framing_Pass`/`Framing_COBS` →
    `FramingBase`/`FramingPass`/`FramingCOBS`; earlier entries name the current symbols | Names only".
  - **B41** (U10): "`UARTComm`'s listen starter and `UARTLinkDriver`'s exercise starter are named methods
    (`start_asy_listen`, `start_asy_exercise`) instead of lambdas, so a task's end names it | No wire change".
  - **B42** (U10): "Except tuples in alphabetical order and one raise-message case in `asy_uart_driver.py`/
    `asy_uart_comm.py` | No wire change".
  - **B43** (U11): "`reset_error_counter()` returns the history write's success (`bool`) | Nothing on the wire changes".
  - **B44** (U12): "`CRCPass.add_into()`/`check_from()` refuse a zero, negative or overrunning size like the real CRCs, so
    a delimited frame decoding to zero bytes is a failed read, not an empty payload | No emitted byte changes; the dev
    wiring's `CRCPass` link sends fixed non-empty frames".
  - **B45** (U12): A.U12.03's text ("`UART.write()`/`writefrom()` send nothing and report success for a zero-length
    payload in every CRC and codec mode … the `*_until_complete()` reads return an empty result for `nbytes == 0` without
    reading | the protocol always sends non-empty fixed frames, so no protocol byte changes").
  - **B46** (U12): "`FramingBase.allocations` removed (a test-only counter) | No wire effect".
  - **B47** (U13): A.U13.12's text ("`readline()`/`readline_until_complete()` read at most what `any()` reports … corrects
    B25 | identical bytes, identical order; no protocol path uses readline").
  - **B48** (U13): A.U13.13's text (writes only into an empty TX ring, at most `txbuf` bytes per call; back-to-back frames
    separated by the first frame's wire time | identical bytes, identical order, well inside every `timeout`).
  - **B49** (U13): "`_read_delimited()` yields every 16 consumed bytes, delimiters and skipped fragment bytes included |
    Identical bytes, identical order".
  - **B50** (U13): "`asy_uart_driver.UART` defaults become `poll_wait_ms=2`, `poll_idle_ms=50` (the bench-measured pair
    J.6 requires); `dev` sets both explicitly | No wire change".
  - **B51** (U13): "`ready()` reports `False` when the bus was deinitialised during its closing yield, and
    `_read_delimited()` re-checks after its periodic yield | No byte on the wire changes".
  - **B52** (U16): "`LockableBuffer` renamed `RegionBuffer` and no longer carries an unused lock; TX/RX frame buffers
    unchanged in size and use | No wire effect".
  - **B53** (U17): A.U17.01's text (the six initiator entry points check in one order — readiness and role gate, command
    id, buffer or callback, size | which refusal is logged for a doubly wrong call changes; no byte, acceptance rule or
    timing).
  - **B54** (U17): A.U17.06's text (a hold-off deadline more than one resync window away is expired … worth the C side's
    attention if it stores the deadline in a wrapping tick).
  - **B55** (U17): "`_drain()` clears `_drain_bound_hit` before its own early return, so a resync never reads the verdict
    of an earlier drain (agent, 2026-09-18) | Logging only: the flag decides which warning a resync persists; unreachable
    at the time (a failed RX buffer is refused at construction). No byte, acceptance rule or timing changes".
  - **B56** (U17): "`_blind_resyncs` stops at `_DIAG_RESYNC_STREAK` instead of counting on | Only the threshold test reads
    it; logging unchanged, no wire effect".
  - **B57** (U17): A.U17.20's text, codes named: "Two construction refusals: `poll_wait_ms` outside 1 … 9 (`errno` 91,
    `UART_POLL_RATE`) and `timeout` above 89,478,485 ms (`errno` 76, `UART_TIMEOUT_PARAM`) — its drain bound, backoff cap
    and hold-off would leave rp2's `ticks_add()`/`ticks_diff()` range | Local refusals; no byte, acceptance rule or timing
    changes".
  - **B58** (U17): "`FramingCOBS.decode_from()` bounds its encoded input by the encoded worst case of `max_frame`, not by
    `max_frame` itself, which refused every full-length frame from a codec sized exactly to the frame; `UARTComm` refuses
    a delimited codec sized below one frame (`errno` 92, `UART_CODEC_SIZE`) | `FramingPass`, the selected codec, is
    unaffected: no byte on the wire changes. Relevant to A11 only".
  - **B59** (U17): "Type annotations only (`Any` replaced by the shared aliases) | No runtime change".
  - **B60** (U17): "`asy_uart_driver`'s cancel request/acknowledge numbers and `cancel_unacknowledged` wrap at 2**30 − 1 by
    a conditional step and are compared by distance or equality, so they never grow into heap integers | Same handshake
    (B15), no wire effect".
  - **B61** (U20): A.S0930.07's text in current names ("Each `uart_link` end declares its CRC mode in the device TOML
    (`crc`: "none", the default, or "crc16"); the build refuses a pair whose ends differ and sizes `rxbuf` with the CRC
    width; the generated module passes the CRC to the end's `asy_uart_driver.UART` bus. `dev` keeps no CRC; the test
    levels run both modes | Wiring only: `asy_uart_comm.py` is unchanged and CRC-agnostic (Part J.3), `UARTComm` reads the
    CRC from its bus as before, and no default changes. A link built with "crc16" uses `asy_crc_checks.CRC16`
    (CRC-16/CCITT-FALSE, big-endian), whose wire difference from the legacy C CRC is already entry A7 — a Python↔C pair
    selecting it is that flag day, not a new one").
  - **B62** (U24): "The bench `UARTLinkDriver`'s banner is renamed `uart-crossover` | Application payload of the bench-only
    driver, not the protocol; the C side has no such banner".
  - **B63** (U30): "Every broad handler in `asy_uart_comm.py` records a C-stack overflow for the supervisor
    (`report_if_fatal()`) | No wire change".
  - **B64** (U35): "`CRCBase._crc()` takes the polynomial its caller has already checked instead of re-testing pass mode,
    and `add()`/`add_into()` no longer wrap `pack_into` in an unreachable `ValueError` catch | No emitted byte changes".
- **Resolved**: A.U32.06's own row ("`start_listen`, `start_exercise`") and A.U10.44's are one row with the U10 names
  (M.SRC_NET.170, M_SRC_NET gap 6). A.U10.35's row adds `set_callback` (M.SRC_NET.155 makes it private; gap 6). A.U3.13's row
  adds the synchronous `_note_valid_frame()` (M.SRC_NET.164; gap 6 — no constituent carried it). A.U10.37/A.U10.38's two
  rows are one "names only" row also naming the CRC and codec classes A.U10.38 renames (agent, one row per change kind).
  A.U35.44's text follows M.SRC_CORE.116 (the guard became a parameter). No row: A.U10.21 (its condition — a changed
  `setup()` docstring — does not occur, M.SRC_NET.169), A.U10.33 (member order is not recorded, its own text and
  M.SRC_NET.173, overriding A.U17.30's list), A.U13.19 (its own slot: no entry), A.U12.01 (bytes unchanged, its own slot),
  A.U17.21/A.U20.18 (build-side refusal, no module change), A.U35.47/A.U0.49/A.U8.06 (comments only), A.U35.48 (no UART
  path changed by its merge).
- **Unit**: per row as listed (U2 … U35); the merged change is complete at U35.
- **Depends**: each row's code change (M.SRC_NET.150-.216, M.SRC_CORE.115-.122); M.DOCS.019 (Status column from U17)
- **Blast carried by**: order and status → M.TSC.152; A.U37.04 (4)'s close check (every commit touching
  `src/asy_uart_comm.py` has its row) → audit record
- **Kind**: doc

### M.DOCS.025 The "Settled questions" heading names its basis
- **From**: A.U0.47
- **Site**: `UART_C_PORT_CHANGELOG.md:105`
- **Change**: "## Settled questions" → "## Questions answered by construction (agent, 2026-09-11; verified over 20,010
  cases, below)".
- **Resolved**: —
- **Unit**: U0
- **Depends**: —
- **Blast carried by**: —
- **Kind**: doc

## DEVICE_REFERENCE.md

End-state section order: header; Commissioning and operating; Neopixel LED; Networking status; Local time; SGP40 VOC
baseline FRAM backup; ISL29125 colour sensor; Clearing the error logs. Key names are A.U10.40's scheme from U10 on; field
labels are the ones the definitions carry when the text lands (A.U36.531 Blast).

### M.DOCS.026 A commissioning-and-operating section lists what needs a person
- **From**: A.U36.531; A.U14.R01 / A.U14.17 (the power-cycle item), A.U15.11/A.U15.12 (operator procedure handed here),
  A.U32.01 (the runbook pointer), A.U19.14 (linked section)
- **Site**: `DEVICE_REFERENCE.md`, new "## Commissioning and operating: what needs a person" after the header (`:1-5`),
  before "## Neopixel LED"
- **Change**: A.U36.531's section verbatim (items 1-8: Wi-Fi setup through the hotspot; `AmbPres` once; `ForceCalRef`
  with **FRC Readiness**; `SelfCal`; ISL29125 calibration; read **Last Reset Reason** and save `GET /status` before
  clearing; power-cycle a unit whose I2C sensors stay unreadable after a reboot; the reflash runbook in README.md
  "Moving a legacy unit to this firmware"), with the labels as the definitions carry them at landing.
- **Resolved**: —
- **Unit**: U36
- **Depends**: A.U6.18, A.U6.23 (labels; GEN/WEB), A.U15.12 (`FRCState`, SRC_SENS), A.U14.17 (SPEC F.2 text), A.U32.01 (README
  runbook, M.DOCS README runbook), A.U36.530 (SPEC A.4), M.DOCS.032
- **Blast carried by**: README runbook links here → M.DOCS (README runbook section); SPEC F.2 → A.U14.17 (SPEC)
- **Kind**: doc

### M.DOCS.027 The Neopixel section states the Wi-Fi LED patterns, the window and the refusal
- **From**: A.U36.546 (4) (the overlay bullet checked against the firmware), A.U18.30 (deactivated pattern), A.U10.40
  (`LedWifiOn` → `LEDWifiOn`), A.U9.01 (window bullet), A.U9.03 (manual flash refusal)
- **Site**: `DEVICE_REFERENCE.md:7-25`
- **Change**: `:11-14` (WiFi status overlay bullet; "on/off only … not a live connectivity signal" contradicts the
  service, which blinks the overlay per link state) → "- **Wi-Fi status overlay** — a dim white glow showing the Wi-Fi
  state while `/networking`'s `LEDWifiOn` is on (off: the overlay stays dark): searching for the network — toggling
  every half second; connected — on; disconnected — off; serving the fallback hotspot — on with a short gap every 3 s,
  steadily on once a client has joined; Wi-Fi switched off (a second failure streak after the hotspot ran, or no
  readable Wi-Fi configuration) — off with a short blink every 3 s, until a power cycle." The notification bullet
  `:15-19` gains, after the brightness/duration sentence: "It flashes only inside the notification window
  `OnH:OnM`–`OffH:OffM`; an On time later than Off spans midnight (e.g. 22:00–06:00). A manual flash (`LightCmdLED`) is
  refused ("Failed") while another flash is still playing." Table unchanged.
- **Resolved**: the pattern list is read from the service at landing (A.U36.546 (4): the executor checks the text against
  `asy_wifi_service.py`/`asy_neopixel_driver.py` and corrects any mismatch); `LightCmdLED` per A.U10.40.
- **Unit**: U36. Stages: U9 (window and refusal sentences, old key names), U10 (`LEDWifiOn`, `LightCmdLED`), U18 (the
  deactivated pattern clause), U36 (the bullet's full rewrite).
- **Depends**: M.SRC_NET (WiFi LED patterns, `_LED_DEACTIVATED_*_MS`), A.U9.01/A.U9.03 (SRC_SENS/GEN)
- **Blast carried by**: SPEC A.4 WiFi, H, A.8 → A.U18.30, A.U9.03 (SPEC); field help → A.U9.01 (GEN)
- **Kind**: doc

### M.DOCS.028 A networking-status section: link fields, NTP sync, DNS fallback
- **From**: A.U18.35, A.U18.20, A.U18.21, A.U18.10
- **Site**: `DEVICE_REFERENCE.md`, new "## Networking status" after "## Neopixel LED"
- **Change**: "`Connected` and `WifiUptime` (`/status`, networking) describe the Wi-Fi link, not internet reachability:
  they count while the unit is joined to a network **or** serving its fallback hotspot (owner, 2026-09-29).
  `NTPSynced` is true only while the last successful time sync is less than three sync intervals old (`NTPInterval`); a
  failed resync does not extend it, and a change to an NTP setting clears it until the next successful sync (owner,
  2026-09-29). `DNSFallback` (Networking) lists up to three IPv4 DNS servers, comma-separated, tried in order after the
  one the network hands out; empty means none (default `8.8.8.8,1.1.1.1`)."
- **Resolved**: A.U18.20's text is "(agent, 2026-09-27)" in its code comment (legacy intent) — the DR sentence states the
  behaviour without a tag for the three-interval rule and the owner tag for the settings clear (OR102.a (3)).
- **Unit**: U18
- **Depends**: M.SRC_NET (U18 NTP/WiFi changes), A.U10.40 (`NTPSynced`, `NTPInterval`)
- **Blast carried by**: status catalog descriptions → A.U18.35 (GEN); SPEC C.7.2 → A.U18.20/A.U18.21/A.U18.10 (SPEC)
- **Kind**: doc

### M.DOCS.029 A local-time section states the offsets and the EU switch rule
- **From**: A.U36.029; A.U10.40 (`NTP_Offset_S` → `NTPOffset`)
- **Site**: `DEVICE_REFERENCE.md`, new "## Local time" after "## Networking status"
- **Change**: A.U36.029's section with `NTPOffset` for `NTP_Offset_S`: "The unit keeps UTC from NTP. `NTPOffset`
  (Networking) is added to that time itself — the clock and every timestamp the unit stores or reports move with it. The
  local time (`/system`'s `LocalTime`, and the notification window) adds `GMTOffset` all year and `DSTOffset` on top
  between 01:00 UTC on the last Sunday of March and 01:00 UTC on the last Sunday of October — the EU rule, as the legacy
  firmware applied it (both offsets default to 3600 s, System page). **Known limitation**: no other region's switch
  dates are built in; elsewhere set `DSTOffset` to 0 and change `GMTOffset` by hand at your local switch (agent,
  2026-09-30)."
- **Resolved**: —
- **Unit**: U36
- **Depends**: A.U18.25 (switch-date test, TEST_UNIT)
- **Blast carried by**: —
- **Kind**: doc

### M.DOCS.030 The SGP40 section: every "0", the age rule, the verify cadence, the VOC state
- **From**: A.U15.17 (6), A.U16.18, A.U36.537 (Blast sentence), M_TEST_UNIT GAP-U1 (age condition), A.U36.546 (4)
- **Site**: `DEVICE_REFERENCE.md:27-37`
- **Change**: `:31-32` `BackupPeriod` bullet gains "; a backup is verified about once an hour, and every backup when they
  are more than an hour apart"; `:33-35` `BackupMaxAge` bullet → "- **`BackupMaxAge`** (minutes, 0–10080): on boot, how
  old a restored FRAM backup is allowed to be before it's rejected as stale (falls back to a fresh VOC init instead). A
  backup stamped later than the unit's clock (the clock was set back) counts as too old. **`0` disables this staleness
  check** — a restored backup is accepted whatever its age."; new bullet "- **`WaitTimeNTP`** (seconds, 0–600): how long
  a boot waits for NTP before restoring a timestamped backup (so its age can be checked). **`0` means never wait**: the
  backup is restored at once, without an age check."; `:37` keeps its sentence ("The two `0`s …" → "The `0`s point in
  different directions: `BackupPeriod` turns a feature off, `BackupMaxAge` turns a limit off, `WaitTimeNTP` skips a
  wait."); a closing sentence: "**VOC Algorithm** tells what the VOC index means right now: 0 while it starts up, 1 while
  it is learning (the first day after a fresh start), 2 once settled, 3 while it runs on a restored backup."
- **Resolved**: A.U15.17 writes "rejects a backup dated in the future" unconditionally; A.U16.18 and the register (G5/R31,
  M_TEST_UNIT GAP-U1, M.TEST_UNIT.138) settle "a limit of 0 accepts any age; a negative age expires under a nonzero
  limit" — the text says so. The "two `0`s" sentence becomes three (WaitTimeNTP joins the list; agent wording).
- **Unit**: U36. Stages: U15 (`BackupPeriod` cadence, `WaitTimeNTP`), U16 (the future-stamp sentence with M.SRC_SENS.063's
  condition), U36 (VOC state sentence, the "0s" sentence).
- **Depends**: M.SRC_SENS.063 (age condition), A.U15.19 (`VOCState`, SRC_SENS), A.U36.537 (SPEC M.3)
- **Blast carried by**: SPEC C.5/H.5/M.3 → A.U15.17, A.U36.537 (SPEC)
- **Kind**: doc

### M.DOCS.031 The ISL29125 section: key names, the operator procedure, the wiring fact
- **From**: A.U0.36 (B11 `:67-68` tag; C06 `:100-101`), A.U10.40 (`IrCompOffset`/`IrCompAdjust` → `IRCompOffset`/
  `IRCompAdjust`), A.U15.39 (`:87-88` procedure), A.U15.36 (the field the procedure names), A.U36.511 (10) (`:100-101`
  final text)
- **Site**: `DEVICE_REFERENCE.md:39-101`
- **Change**: `:53-54` `IrCompOffset`/`IrCompAdjust` → `IRCompOffset`/`IRCompAdjust`; `:67-68` "It is gone from the
  settings on purpose" → "It is gone from the settings (owner, 2026-09-13)"; `:87-88` → "Start with the scene dark, let
  the unit settle on its sensitive range, then raise the light until **Calibration Light** reads suitable —
  mid-brightness, neither dark nor near saturation — and switch **Calibrate Gain Ratio** on. (A strongly coloured light
  can hold the unit on its bright range, where its green is too small to calibrate from; starting dark avoids that.)";
  `:100-101` → "The sensor is present on every device whose TOML declares an `isl29125` instance — today only `dev`;
  its bus and IRQ pin are that TOML's."
- **Resolved**: A.U0.36's C06 text ("`wozi` carries no colour sensor; a device's TOML decides its sensors.") is
  overtaken by A.U36.511 (10), which finishes the same G8/R01 clause (no copied TOML fact) — the U36 text stands.
- **Unit**: U36. Stages: U0 (B11 tag; C06 interim), U10 (key names), U15 (procedure).
- **Depends**: A.U15.36 (`CalLight` field, SRC_SENS)
- **Blast carried by**: SPEC M.1/M.1.1/M.1.3 → A.U15.39 (SPEC)
- **Kind**: doc

### M.DOCS.032 A section on clearing the error logs
- **From**: A.U19.14 (1); A.U36.503 (H.4 points here)
- **Site**: `DEVICE_REFERENCE.md`, new "## Clearing the error logs" at the end
- **Change**: A.U19.14 (1)'s text verbatim ("The Status page's error-log reset (`PUT /status {"ResetErrors": true}`) clears
  every module's log at once. It must finish within the device's 15-second request limit, the same limit the web page
  waits; on a busy device it can take several seconds. A reset that reports "Failed" means one module's log could not be
  written; the other logs are cleared. Read and save the logs before clearing them: the reset cannot be undone.")
- **Resolved**: —
- **Unit**: U19
- **Depends**: M.SRC_NET (A.U11.31's concurrent reset, U11)
- **Blast carried by**: SPEC H.4/C.7 → A.U11.31, A.U36.503 (SPEC); BACKLOG item 24 → M.DOCS (BACKLOG)
- **Kind**: doc

### M.DOCS.033 The whole file is checked against the refactored firmware
- **From**: A.U36.546 (4)
- **Site**: `DEVICE_REFERENCE.md` (whole)
- **Change**: after M.DOCS.026-.032, the executor reads the file against the firmware as built (the LED legend against
  `asy_neopixel_driver.py` and the notification catalog, the SGP40 backup semantics against `asy_sgp40_driver.py`, every
  REST key against SPEC A.8) and fixes each mismatch in place; the commit message lists what was checked. The header
  (`:3-5`) keeps its role sentence.
- **Resolved**: —
- **Unit**: U36 (last DEVICE_REFERENCE edit)
- **Depends**: M.DOCS.026-.032
- **Blast carried by**: —
- **Kind**: doc

## HEAP_FRAGMENTATION_MEASUREMENTS.md

### M.DOCS.034 Version-stamped claims follow the refreshed pin
- **From**: A.SDEP.08 (4)
- **Site**: `HEAP_FRAGMENTATION_MEASUREMENTS.md:18` ("pinned MicroPython v1.29.0 source"), `:24` ("`py/gc.c` at v1.29.0"),
  `:166`, `:286` ("1.29's Makefile silently ignores `MICROPY_FORCE_32BIT`")
- **Change**: each claim is re-read at the pin B0's refresh leaves and re-stamped to it, or corrected where the source
  changed (the allocator facts of §M1 against `py/gc.c`; the 32-bit build pitfall against `ports/unix/Makefile`). No
  change if the pin did not move.
- **Resolved**: —
- **Unit**: U0 (the SDEP bump)
- **Depends**: A.SDEP.08
- **Blast carried by**: —
- **Kind**: doc

### M.DOCS.035 The interpreter-build list names the three builds and the variant as built
- **From**: A.SDEP.11 (outcome (c) only: `:284`, `:286` drop `VARIANT_DIR=`); adherence: M.TOOL.040 adds a third Unix
  binary (`build-lwip`), so §M5.2's "builds both" goes stale and no constituent carries it
- **Site**: `HEAP_FRAGMENTATION_MEASUREMENTS.md:251-252` (§M4.4 variant bullet), `:280-286` (§M5.2)
- **Change**: `:281-282` "**`build-standard` / `build-settrace`** — `toolchain/setup_toolchain.py` builds both; plain
  `scripts/test.sh` uses the flag-free one." → "**`build-standard` / `build-settrace` / `build-lwip`** —
  `toolchain/setup_toolchain.py` builds all three; plain `scripts/test.sh` uses `build-standard`, `--coverage`
  `build-settrace`, and `build-lwip` runs the real patched lwIP stack over loopback (SPECIFICATION.md <the Part B section M.TOOL.040's SPEC text names>)." Under A.SDEP.11
  outcome (c) only: the two recipes drop `VARIANT_DIR=<toolchain>/build_overrides/unix_kbd_intr_variant` and `:251-252`
  "(`variants/standard/manifest.py`, or the kbd-intr override variant's)" → "(`variants/standard/manifest.py`)".
- **Resolved**: the `build-lwip` clause is an agent addition (adherence: docs hold current state) — OR2.c list.
- **Unit**: U21 (with M.TOOL.040); the (c) stage at U0 if the SDEP re-check finds (c).
- **Depends**: M.TOOL.040, A.SDEP.11
- **Blast carried by**: SPEC B.14.2/E.5.2 → A.U21 (SPEC)
- **Kind**: doc

### M.DOCS.036 The frozen-twin rule carries the owner's words
- **From**: A.U0.27 (A33)
- **Site**: `HEAP_FRAGMENTATION_MEASUREMENTS.md:295-296`
- **Change**: "(owner, 2026-09-23)" → "(owner, 2026-09-23, `bbb2306`: 'no twin32 to be kept at all'; both twins, owner,
  2026-09-29)".
- **Resolved**: —
- **Unit**: U0
- **Depends**: —
- **Blast carried by**: SPEC `:4620-4622` → A.U0.25 (SPEC)
- **Kind**: doc

### M.DOCS.037 The twin-first instrument row names the committed runner
- **From**: A.U26.05 (Docs slot)
- **Site**: `HEAP_FRAGMENTATION_MEASUREMENTS.md:310` (§M5.3 "device scripts in the twin" row) and §M5.1's table
- **Change**: the §M5.3 row leaves the ad-hoc table; §M5.1 gains "| `digital_twin/run_device_script.py` +
  `scripts/record_twin_instrument_runs.py` (+ `tests_hardware/twin_board.py`) | runs a device script unchanged in the
  twin, and a bench test's own functions against `TwinBoard`; the committed record lists every instrument's twin run.
  **Always do this before silicon**: it found three instrument defects the board would otherwise have |".
- **Resolved**: A.U26.05 says "U36's placement"; placed in U26 with the runner, so the doc never names a removed ad-hoc
  tool after the committed one exists (agent).
- **Unit**: U26
- **Depends**: A.U26.05 (TWIN/SCR/HW_BENCH)
- **Blast carried by**: `tests_hardware/README.md` habit 5 → A.U26.05 (HW_BENCH)
- **Kind**: doc

### M.DOCS.038 The ruled-out remedies are the agent's measured findings
- **From**: A.U0.46
- **Site**: `HEAP_FRAGMENTATION_MEASUREMENTS.md:361-362` (§M7)
- **Change**: "Measured, not argued; don't re-spend time on them without a new mechanism." → "Measured, not argued
  (agent, 2026-09-24, `17b4354`); each reopens with a new mechanism."
- **Resolved**: —
- **Unit**: U0
- **Depends**: —
- **Blast carried by**: SPEC `:4622` → A.U0.25 (SPEC)
- **Kind**: doc

### M.DOCS.039 §M8 lists the two uncarried research gaps as closed
- **From**: A.U36.013
- **Site**: `HEAP_FRAGMENTATION_MEASUREMENTS.md:387-393` (§M8)
- **Change**: after the owner's four: "Two further gaps from the archive are closed on the same terms (agent,
  2026-09-30, applying that closure): the placement law's positive branch at a real survivor's birth position (confirmed
  only synthetically; archive §0B.4, §0B.7), and whether the survivors' own size class, rather than the churn's, sets
  their vulnerability (archive §0A.7 item 4). Neither gated anything; both reopen only with a new layout symptom."
- **Resolved**: —
- **Unit**: U36
- **Depends**: —
- **Blast carried by**: —
- **Kind**: doc

### M.DOCS.040 The front matter names Part I's sections as they stand
- **From**: adherence (A.U30.02 rewrites I.2 as the allocation-site catalog; its Blast leaves this file "unchanged", but
  `:7` describes I.2 as "settled decisions")
- **Site**: `HEAP_FRAGMENTATION_MEASUREMENTS.md:6-7`
- **Change**: "Part I (I.2's settled decisions, I.3's bounded assembly, I.4(e)/(f)/(f.1)/(g))" → "Part I (I.2's
  allocation-site catalog with its recorded decisions, I.3's bounded assembly, I.4(e)/(f)/(f.1)/(g))".
- **Resolved**: agent addition, OR2.c list.
- **Unit**: U30
- **Depends**: A.U30.02 (SPEC)
- **Blast carried by**: —
- **Kind**: doc

## PROJECT_AUDIT_PLAN.md

Audit-process edits only (the 3.2 owner rows are input). The file is deleted in phase D; until then its edits are
audit-record changes, not permanent text, so the G9/R12 ID rule does not bind them.

### M.DOCS.041 ENV topics: the baseline record, the corpus at the refreshed pins, the refresh topic
- **From**: A.U0.06 (ENV.T02 text), A.SDEP.24 (ENV.T03, ENV.T11, 4.6 intro)
- **Site**: `PROJECT_AUDIT_PLAN.md:731-734` (ENV.T02), `:760-797` (4.6 ENV topics; ENV.T03 `:775-777`; intro `:762-763`)
- **Change**: ENV.T02 gains "host peak RAM, host SSD writes (`/proc/diskstats`) and the environment record"; ENV.T03
  "(already at `v1.29.0` with the rp2 submodules …) read-only; clone only Microdot `v2.6.2` into the scratchpad" → "at the
  pinned ref (`toolchain/versions.toml`) with the rp2 submodules (`lib/lwip`, `lib/cyw43-driver`, `lib/pico-sdk`,
  `lib/micropython-lib`) read-only; Microdot at the vendored tag; after the dependency refresh the previous pins
  (MicroPython `v1.29.0` with its submodules, Microdot `v2.6.2`) stay in the scratchpad read-only for the citation
  re-check."; new "**ENV.T11** (once) Dependency refresh after T02 and before B1 (LEAD/R33): every external dependency
  updated against the baseline, workarounds re-checked, the post-refresh baseline recorded; a short second check at B5.";
  intro "T02, T05-T10" → "T02, T05-T11".
- **Resolved**: —
- **Unit**: U0 (before the baseline run, A.U0.06, and before the refresh, AC_NOTES 34 (OR129) "the U0 step … ordered before
  every B1 action")
- **Depends**: —
- **Blast carried by**: `audit/sweeps/validate_plan.py` V1/V3/V4 over the edited plan (audit tooling)
- **Kind**: rule (audit file)

### M.DOCS.042 The plan's anchors move to the recorded baseline
- **From**: A.U0.02
- **Site**: `PROJECT_AUDIT_PLAN.md` anchors (with `audit/` anchors, audit files)
- **Change**: at the go-ahead the baseline SHA (`origin/main`) is recorded in the register header and every plan anchor
  is moved to it with `audit/sweeps/reanchor.py`, `harvest_check.py`, `baseline_fates.py`, plus the delta harvest over
  `4dc80ef..<baseline>` (A.U0.02's text).
- **Resolved**: —
- **Unit**: U0 (first)
- **Depends**: —
- **Blast carried by**: —
- **Kind**: rule (audit file)

### M.DOCS.043 Phase D deletes the plan and every pointer to it
- **From**: A.U37.15; A.U37.03 (the plan is a pattern hit and stays to phase D)
- **Site**: `PROJECT_AUDIT_PLAN.md`, `audit/`
- **Change**: after A.C.11 (4)'s agreement, one commit `git rm -r audit PROJECT_AUDIT_PLAN.md`; README's two map entries go
  (M.DOCS README map); each check's `audit/`/`PROJECT_AUDIT_PLAN.md` exclusion goes (A.U0.08, A.U0.09, A.U1.09, A.U6.15,
  A.U10.40's grep — TSC/SCR); `git grep -n "PROJECT_AUDIT_PLAN\|audit/"` outside `.git` is then empty. The audit branch is
  not deleted (U37 rule).
- **Resolved**: —
- **Unit**: U37 (phase D)
- **Depends**: A.C.11, A.U37.05, A.U37.14
- **Blast carried by**: README map → M.DOCS (README map); check exclusions → A.U37.15 (TSC)
- **Kind**: doc, test (phase D)

## README.md

End state (A.U36.547 (1)): intro → **Devices** → **Recipes** → **Command-line reference** → the explanatory sections
(Code quality tooling, Website tooling, Real hardware access, Real hardware: levels L3 and L4, Digital twin), each keeping
its explanation with its commands replaced by a pointer to its recipe or reference block → **Release** (A.U37.11; placed
before the map) → **Further reading**. Recipe names other files cite: "twin launch" (M.TWIN.060), and the
`(README.md, Recipes: <name>)` pointers of `tests_hardware/README.md` (M.HW_BENCH.126) take the names written here. Text
written by a U0-U35 stage lands in HEAD's section of the time; A.U36.547's restructure (U36) carries it into its end-state
place unchanged.

### M.DOCS.044 The intro states the frozen-code guarantee and the no-auth premise
- **From**: A.U32.02, A.U29.01 (Docs slot)
- **Site**: `README.md:3-8`
- **Change**: `:7-8` "Code ships as frozen bytecode compiled into the MicroPython firmware, not loaded from the device
  filesystem at runtime." → "Code ships as frozen bytecode compiled into the MicroPython firmware, and the boot entry puts
  the frozen modules ahead of the device filesystem on the import path, so no file there replaces them; a filesystem
  `boot.py` still runs before the frozen `main.py`, which is why a legacy unit's move to this firmware erases its flash
  (see "Moving a legacy unit to this firmware")."; after the paragraph: "The REST API and web UI have no authentication:
  the firmware is built for a trusted home LAN, and SPECIFICATION.md A.11 lists what that accepts."
- **Resolved**: —
- **Unit**: U32. Stages: U29 (the no-auth sentence, with SPEC A.11), U32 (frozen sentence, with the runbook).
- **Depends**: A.U20.03 (the `.frozen`-first guarantee, GEN), M.DOCS.048 (the runbook heading), A.U29.01 (SPEC A.11)
- **Blast carried by**: SPEC F.1/L → A.U20.03 (SPEC)
- **Kind**: doc

### M.DOCS.045 The Devices section derives from the TOMLs and names the legacy units
- **From**: A.U36.547 (2), A.U0.24, A.U1.13 (`:17-20` HTML-source paths)
- **Site**: `README.md:10-20`
- **Change**: end state → "## Devices\n\nThe firmware is generated per device from `devices/<device>.toml` (SPECIFICATION.md
  Part L); today six:" then `| Device | Unit |` rows — `wozi`: the exemplary device, verified through the tests and the
  twin, never flashed by a session; `arzi`: a room unit; `klkizi`, `grkizi`, `schlafzi`: the three units the legacy
  firmware calls `neu`, each its own file; `dev`: the bench rig, the only unit a session flashes — then "Which sensors,
  buses and options a device has is its `devices/<device>.toml`'s alone (SPECIFICATION.md L.1)." then "**Five legacy
  units are in service**, all the owner's own and within reach at any time (owner, 2026-09-26: 'I build all sensors and
  still own all of them - full access anytime'): `arzi`, `wozi` and three arzi-identical units sharing the `neu` build,
  running the legacy firmware on MicroPython 1.24.1. Each moves to this firmware only by the owner's own reflash
  ("Moving a legacy unit to this firmware")." then "The legacy firmware tree is kept for reference only
  (`legacy/README.md`)." No Sensors or HTML-source column.
- **Resolved**: A.U0.24's sentence also carries the dev/wozi flashing roles, which the U36 table now states — its last
  sentence ("`dev` is the bench rig … (owner, 2026-09-03, CLAUDE.md).") is dropped at U36 as a duplicate (A.U36.547 (2)
  "A.U0.24's sentence on the legacy units"); "(different GPIO wiring)" dropped with it (a copied TOML fact, G8/R01).
- **Unit**: U36. Stages: U0 (A.U0.24's full sentence replaces `:10-13`), U1 (`:17-20` `html_raw/<x>` →
  `legacy/firmware/html_raw/<x>`, A.U1.09's old-path check), U36 (the section).
- **Depends**: A.U1.03 (`legacy/README.md`), M.DOCS.048
- **Blast carried by**: A.U6.15's variant-literal check exempts docs → TSC; `test_readme_reference.py` (A.U36.547 (7)) → TSC
- **Kind**: doc

### M.DOCS.046 One line replaces the "moved to SPECIFICATION.md" narrative
- **From**: A.U36.547 (3)
- **Site**: `README.md:22-30`
- **Change**: the heading and its paragraph → "Repository layout, architecture and the build: SPECIFICATION.md Parts A and
  B." (the command block `:33-40` and the flag table `:45-56` move to Recipes (M.DOCS.047) and the reference
  (M.DOCS.052)).
- **Resolved**: —
- **Unit**: U36
- **Depends**: —
- **Blast carried by**: —
- **Kind**: doc

### M.DOCS.047 Recipe "Install from scratch": tiers, datasheets, bench bridge, Node, pins
- **From**: A.U36.547 (4); A.U36.545 (3); A.U36.522; A.U1.13 (`:73-75`, `:108-111`); A.U1.05 (the recipe's move);
  A.U21.19, A.U21.24, A.U21.26, A.U21.27, A.U21.28 (`:62-63`), A.U21.21, A.U21.03, A.U21.12, A.U27.12, A.U28.02, A.U28.20,
  A.SDEP.04 (`:208-209`), A.U36.512 (5) (wording)
- **Site**: `README.md:31-111` (everyday build commands, "Dev environment setup"), `:205-217` (website setup)
- **Change**: one recipe block, in order: `uv sync` (the uv version is `pyproject.toml`'s `[tool.uv] required-version`;
  another uv refuses with its own message); `uv run toolchain/setup_toolchain.py env --tier generic|flash|bench` (one tier,
  each a superset of the one before); `git submodule update --init datasheets`; `source .venv/bin/activate`. The tier
  table (`:63-67`) stays as the recipe's explanation with: generic "Python (`uv sync`) and website (`npm ci`)
  dependencies and Playwright's Chromium, or `env` fails; the toolchain: firmware, `mpy-cross`, and the Unix-port build
  flavours `standard`, `settrace` and `lwip`"; flash "non-root USB serial access (`dialout`) and a board resolved by
  vendor ID `2e8a` and its MicroPython by-id name (SPECIFICATION.md B.12)"; bench "a real Wi-Fi bridge/AP on this host
  (NetworkManager); the commands it installs and the passwordless-sudo rules it checks: `tests_hardware/README.md`
  Prerequisites". Below the table: "Every tier installs what it lacks (apt packages, `dialout`, NetworkManager) via
  `sudo`; `--skip-apt` skips each step needing it. picotool is built and installed only when its tag changed. Each run
  writes `toolchain-record.json` in the toolchain directory: what was built from what (SPECIFICATION.md B.5)."; "The
  datasheets are a private submodule (`datasheets/`, access by the owner's grant): `git submodule update --init
  datasheets` fetches them; nothing else needs them (SPECIFICATION.md A.6)."; bench bridge: "A new bridge gets a random
  SSID and password unless `BENCH_AP_PASSWORD` (and `--ssid`) is set; the password is shown once, never on a command line
  or in a log." Then A.U36.522's sentence ("Once a bridge exists, re-running `env --tier bench` (with or without these
  flags) never recreates or re-randomizes it or its AP: it reports the existing SSID, re-pins a drifted AP channel with
  the recovery dead-man's switch armed, and reports a bridge MAC that is not `eth0`'s real one with the manual remedy —
  never repairing it live, since that cycles the interface the session depends on (SPECIFICATION.md Part B.13).") and
  A.U1.13's pointer ("To force a new bridge, follow the delete-and-recreate recipe in `tests_hardware/README.md`'s 'Host
  network' section (dead-man's switch first).") — the `nmcli … delete` command itself lives only there (A.U1.05). The
  explicit-interface example (`:99-102`) → `BENCH_AP_PASSWORD=<psk> uv run toolchain/setup_toolchain.py env --tier bench
  --uplink-iface eth0 --wifi-iface wlan1 --ssid bench-ap`. Website setup (`:205-211`): "`env --tier generic` installs the
  `.nvmrc`-pinned Node into `$PICO_TOOLCHAIN_DIR/node` when the host has none — from nodejs.org, checked against the
  release's SHASUMS256.txt, fetched once — never from apt: Debian trixie ships Node <trixie major> while this repo pins
  <.nvmrc major> (re-stated whenever `.nvmrc` moves); a Node on `PATH` matching the pin is used as is."
- **Resolved**: A.U21.19 removes `--password` (`:89` row and the example) — the reference block follows the new `--help`
  (M.DOCS.052); the bench-row install/sudo texts of A.U21.24/A.U21.26 point to `tests_hardware/README.md`
  Prerequisites rather than copying the command list (one home, G9/R15).
- **Unit**: U36. Stages: U0 (A.SDEP.04: Node majors if `.nvmrc` moved), U1 (`:73-75`, `:108-111` pointers; the recipe
  moves out, A.U1.05), U21 (`--password` row and example, A.U21.19; bench row; picotool line; record line; USB rule;
  Node SHASUMS; third build), U27 (build flavour names), U28 (Playwright clause; uv pin line), U36 (recipe form, datasheet
  line, bridge sentence).
- **Depends**: M.TOOL (U21 installer changes: `--password` gone, `BENCH_AP_PASSWORD`, `_TIER_COMMANDS`, record,
  resolver, `build-lwip`), A.U28.35 (submodule; owner push-access step, AC_NOTES 37)
- **Blast carried by**: `setup_toolchain.py --help` ↔ README → `test_readme_reference.py` (TSC); `tests_hardware/README.md`
  Prerequisites/host network → M.HW_BENCH (HW_BENCH); SPEC A.6/B.5/B.12/B.13 → A.U36.545/A.U21.03/A.U21.24/A.U36.523
  (SPEC)
- **Kind**: doc

### M.DOCS.048 Recipe "Build and flash", the flashing rule, and the reflash runbook
- **From**: A.U36.547 (4)(5); A.U36.010; A.U32.01 (runbook and `:299` clause); A.U27.35 (work dirs); A.U27.36
  (`--no-autostart`); A.U26.02 (image record); A.U20.05; A.U6.03/A.U6.04 (`<device>` no longer an `html/definitions`
  file); adherence: CLAUDE.md credential rule (the runbook's legacy hotspot password)
- **Site**: `README.md:263-327` ("Building real firmware", "Flashing a real board"), new `#### Moving a legacy unit to this
  firmware (reflash runbook)` after it
- **Change**: build: `uv run scripts/build_firmware.py <device>` (→ `build/firmware-<device>.uf2` and its image record
  beside it, SPECIFICATION.md B.11); "`<device>` names a `devices/<device>.toml`; every device there builds."; "Build
  intermediates stay under `build/` for inspection (the firmware stage, the website stage and the frozen-HTML step each
  in its own work dir per device) and are wiped at the next build of the same device."; "`--no-autostart` builds
  `build/firmware-<device>-noautostart.uf2`, which boots to the REPL instead of running `main()` (to start it by hand, e.g.
  in Thonny); it needs an empty filesystem, as any flash does after a legacy firmware (runbook below)."; the website-only
  step `scripts/build_website.sh <device>`. Flash: the two picotool recipes (`:303-321`) unchanged except that the image
  is `build/firmware-dev.uf2` built as above; the rule (`:299-301`) → "A session always flashes a `dev` image, never
  `wozi`: only the `dev` board is flashed and bench-tested (owner, 2026-09-03), and `dev` is different hardware that
  wozi's firmware cannot run on (owner, 2026-09-26) — see CLAUDE.md's WoZi rule; moving one of the owner's own units is
  his operation (see "Moving a legacy unit to this firmware")."; `:323-327` names the tests as M.HW_DEV/M.HW_BENCH leave
  them (`flash/test_toolchain_flash_boot.py`'s reflash test behind `--allow-flash-cycle`; `manual/manual_toolchain.py`)
  and "see 'Real hardware: levels L3 (flash) and L4 (bench)' below". Runbook: A.U32.01's subsection verbatim (lead,
  Before (1)-(3), Flash (4)-(6), First boot (7)-(12), Back to legacy (13)-(15); no `[src: …]` note written), with
  DEVICE_REFERENCE's pointer ("see DEVICE_REFERENCE.md's commissioning list for what follows the flash") after step 10,
  and step (14)'s "(SSID `SensorNode`, password `12345678`)" → "(SSID `SensorNode`, the legacy firmware's built-in
  hotspot password, `legacy/firmware/python/CommonDrivers/async_connect.py`)". Where the runbook names the test that pins the TOML hostname rule, it cites it by name,
  `tests_scripts/test_device_tomls.py::test_hostname_is_sensorstation_plus_name` (M.TSC.079 rewrites the file; a line
  number does not survive — M_TSC gap 2).
- **Resolved**: A.U36.010 and A.U32.01 both rewrite `:299-301` — combined (A.U36.010's reasons, A.U32.01's closing
  clause). The literal legacy hotspot password is not copied into README: it is the one accepted credential (CLAUDE.md
  credentials rule), and a new copy in a doc is a new commit of it (agent, adherence — OR2.c list).
- **Unit**: U36. Stages: U26 (record line, with A.U26.02), U27 (work dirs, `--no-autostart`, U27 owns the build section),
  U32 (runbook and the `:299` clause), U36 (A.U36.010's reasons, `<device>` sentence, recipe form).
- **Depends**: A.U27.35, A.U27.36, A.U26.02 (SCR), A.U20.05 (GEN), A.U18.30 (deactivated pattern the runbook names),
  A.U6.03 (any TOML builds)
- **Blast carried by**: SPEC F.1 runbook pointer → A.U1.17/A.U32.01 (SPEC); DEVICE_REFERENCE item 8 → M.DOCS.026;
  `build_firmware.py --help` ↔ README → TSC
- **Kind**: doc

### M.DOCS.049 Recipe "Tests per level": L0-L4, both GC stages, per device
- **From**: A.U36.547 (4); A.U36.008 (hardware levels, soak durations); A.U7.18 (runners run lower levels); A.U26.74
  (flags), A.U26.35/A.U27.19 (`--duration`, `-m` narrows); A.U36.024/A.U25.48 (`run_digital_twin_ci.sh <device>`); A.U7.26
  (standalone pytest needs the toolchain); A.U24.52 (live JS tier needs the toolchain); A.U24.65 (a PER_DEVICE file by
  hand); A.U27.08 (test.sh builds the first derived device's site); M.HW_BENCH.089 (rollover test)
- **Site**: `README.md:124-135`, `:376-412`, `:517-520`
- **Change**: one block per level, each with one comment line: L0/L1 `scripts/test.sh` and `GC_THRESHOLD=32768
  scripts/test.sh` ("the suite passes at both GC stages; each builds what it lacks, the first derived device's website
  included"); a standalone `uv run pytest tests_scripts` "needs the toolchain built first (`scripts/test.sh` or
  `setup_toolchain.py setup`)"; one PER_DEVICE file by hand: `TEST_DEVICE=<device> <build-standard micropython> …
  tests/<file>` as A.U24.65 leaves it; L2 `scripts/run_digital_twin_ci.sh <device>   # a device of devices/*.toml
  (required)`; website `npm test` ("its live tier needs the toolchain built"); L3 `scripts/run_flash_hardware_suite.sh`,
  L4 `scripts/run_bench_hardware_suite.sh` ("each runs L0-L2 first"; a `-m` you pass narrows the selection;
  `--allow-flash-cycle`, `--allow-persistence-write` and the other `--allow-<marker>` gates as `tests_hardware/README.md`
  lists them); the ~12.4-day rollover observation `uv run pytest tests_hardware/bench --allow-multi-day-rollover -k
  test_ticks_ms_rollover_is_survived` (M.HW_BENCH.089's name); soak durations "`scripts/run_bench_soak_tests.sh --duration
  short|mid|long` — liveness only, after a clean L4 run, never bundled into a runner"; manual mode
  `scripts/run_manual_hardware_tests.sh [--list|--only <name>]`; board-free `uv run pytest tests_hardware --collect-only`.
- **Resolved**: A.U36.008's recipe-block wording and A.U36.547's "each once" placement combined: the commands live here,
  the hardware section keeps its table and explanation (M.DOCS.057).
- **Unit**: U36. Stages: U7 (`:376-392` runners' lower levels), U26 (flag names `:390-396`, U26.74's rename lands with its
  users), U27 (`--duration`, `-m`), U36 (the block).
- **Depends**: M.SCR (runner end states: `--skip-lower-levels`, `--duration`, `-m`), M.HW_BENCH.089, A.U25.48 (TWIN/SCR)
- **Blast carried by**: `tests_hardware/README.md` Running → M.HW_BENCH.126; `digital_twin/README.md:388-389` →
  A.U36.024 (TWIN); CLI blocks → M.DOCS.052
- **Kind**: doc

### M.DOCS.050 Recipes for everyday variants: lint, typecheck, coverage, twin launch, preview, smoke
- **From**: A.U36.547 (4); A.U27.26 (venv refusal); A.U36.526/A.U24.72/A.U28.15/A.U28.16 (coverage); A.U24.68,
  A.U36.511 (11), A.U36.024 (twin launch); A.U36.516 (7), A.U28.24, A.U6.07 (preview); A.U28.17, A.U27.08 (smoke);
  A.U27.39 (port-53 lock)
- **Site**: `README.md:124-135`, `:215-235`, `:435-453`, `:483-486`
- **Change**: blocks: **Lint and type-check** `scripts/lint.sh`, `scripts/typecheck.sh` ("each refuses to run outside the
  synced project venv"); **Coverage** `scripts/test.sh --coverage`; **Twin launch** `scripts/run_unix_port_integration.sh
  --device <device>` (launch and serve forever), `… --device <device> --fault sgp40:writeto`, `… --device <device> --host
  0.0.0.0 --port 8080` ("builds the Unix port and the device's website if missing; then open http://127.0.0.1:8080/"),
  and the twin-only demo `<build-standard micropython> digital_twin/launch.py --seed 42 --duration 3 --no-wdt-feed
  --wifi-outcome success --fault scd30:writeto:1`; **Website preview** `npm run preview` ("generates every device's
  definitions, then serves the prototype on 127.0.0.1:8000 — `html/`, `js/`, `mockdata/` and the generated definitions
  only"), then `http://localhost:8000/html/index.html` ("the first device of the generated manifest; `?device=<name>`
  picks another"); **Cross-browser smoke** `scripts/setup_cross_browser_toolchain.sh` once, then `node
  scripts/cross_browser_smoke.mjs` ("it builds what it lacks; in CI a missing engine fails").
- **Resolved**: —
- **Unit**: U36. Stages: U24 (device argument in the twin examples, A.U24.68), U27 (venv sentence), U28 (preview line
  `:224`, smoke), U36 (recipe form).
- **Depends**: M.SCR (the runner usages), M.WEB (preview server, manifest)
- **Blast carried by**: `--help` ↔ README → TSC
- **Kind**: doc

### M.DOCS.051 Recipe "Walk a device by hand": current keys, current reset behaviour
- **From**: A.U11.36 + A.U0.36 (C16), A.U10.40 (keys in the curl bodies), A.U10.37 (module names), A.U25.09 (a simulated
  reset ends the run), A.U25.32 (manual state persists by default), A.U24.68/A.U36.511 (device argument), A.U11.19 (read:
  `:614-618` holds after a PUT)
- **Site**: `README.md:531-639` ("Manual baseline verification walkthrough"), placed under Recipes
- **Change**: every run line passes `--device <device>`; `:547-549` "builds and serves the real `wozi` site by default" →
  "builds and serves that device's real site"; the PUT bodies use the A.U10.40 keys (`{"SCD30": {"MeasInterval": 4},
  "SGP40": {"BackupPeriod": 2}, "BMP3XX": {"SampleInterval": 3}}`; `WarnHum` etc. unchanged); `:611-614` → A.U11.36's
  text ("Every field is checked against its schema: a JSON integer for a `"float"` field (`60` for `WarnHum`) is accepted
  and stored as `60.0`; a float for an `"int"` field is accepted only without a fractional part (`5.0` → `5`, `5.7` is
  `"Invalid"`); `true`/`false` is never a number."), the `TempOffs` mentions → `TempOffset`; `print_log.py`/
  `config_manager.py`/`system_service.py` → their `asy_` names, and the level-registry sentence names the mechanism the
  merged `SystemService` has (its `level_setters` constructor argument, M.SRC_CORE); `:635-639` (a reboot request leaves
  the twin serving) → "on real hardware this restarts the unit; the twin run ends instead, with exit code 3 (a reset) or 4
  (the bootloader) after writing its state, and the next launch boots from that state (digital_twin/README.md)".
- **Resolved**: C16 is written by A.U0.36 (U0) and A.U11.36 (U11) on the same lines; A.U11.36's fuller text is the end
  state (its own "A-C keeps this one"); A.U0.36's U0 text is the interim (both true at their units).
- **Unit**: U36. Stages: U0 (C16 interim), U10 (keys, module names), U11 (C16 final), U24/U25 (device argument, reset
  exit), U36 (placement).
- **Depends**: M.TWIN.050 (exit 3/4), M.SRC_CORE (level setters), A.U10.40 (GEN/SRC)
- **Blast carried by**: SPEC A.8 coercion → A.U0.36 (SPEC); twin README reset text → M.TWIN
- **Kind**: doc

### M.DOCS.052 A command-line reference, one block per tool, checked against `--help`
- **From**: A.U36.547 (6)(7); A.U7.19 (the tool set); the existing flag tables (`:45-52`, `:80-89`, `:455-472`, `:493-502`);
  A.U21.02 (help wording for `--latest`/`--micropython-ref`); A.U21.19 (`--password` gone, `BENCH_AP_PASSWORD`);
  A.U7.06 (positive-integer timeouts); A.U8.16 (`TEST_PARALLELISM`); A.U36.512 (5) ("build flavour"); OR133 (usage errors
  exit 2); A.U26.74/A.U26.35 (hardware flags); A.U27.36 (`--no-autostart`); A.U24.68 (`--device` required)
- **Site**: new `## Command-line reference` after Recipes
- **Change**: one `<details><summary><code>TOOL</code></summary>` block per tool of `tests_scripts/test_tool_help.py`'s set
  (A.U7.19) plus `buildgen/generate.py` and the `package.json` scripts: a synopsis line; `| Option | Meaning | Default |`
  for exactly the options the tool's `--help` prints after the SCR/TOOL/TWIN/HW merges (e.g. `scripts/test.sh`: `--coverage`;
  env `PICO_TOOLCHAIN_DIR`, `SKIP_APT`, `PER_FILE_TIMEOUT_S` (a positive integer of seconds, default 240),
  `TESTS_SCRIPTS_TIMEOUT_S` (positive integer, default 1200), `TEST_PARALLELISM` (default: the speed probe's band — 4×, 2×
  or 1× usable cores, honouring a cgroup quota; 1× when the probe cannot run), `GC_THRESHOLD` (an integer in the rp2040's
  32-bit range; the firmware's value is 32768), per M.SCR.035); its environment variables; one sentence for every tool:
  "A usage or setting error exits 2 before the tool touches anything (owner, 2026-10-01)." The `setup_toolchain.py`
  block lists each subcommand (`setup`, `test`, `env`, `board`) with its options as `--help` prints them (no
  `--password`); `--clean` "wipes every build-artifact directory, every Unix-port build flavour included". The test
  `tests_scripts/test_readme_reference.py` (A.U36.547 (7)) compares option and variable names with each tool's `--help`.
- **Resolved**: the exit-2 sentence is firm (OR133, AC_NOTES 43; no "pending" marker).
- **Unit**: U36
- **Depends**: M.SCR (every runner's usage), M.TOOL (`setup_toolchain.py` subcommands and options), M.TWIN
  (`launch.py`), M.WEB (`package.json` scripts), A.U7.19 (TSC)
- **Blast carried by**: `test_readme_reference.py` and `test_tool_help.py` → TSC
- **Kind**: doc, test

### M.DOCS.053 The code-quality section: scope, summary block, CI, venv
- **From**: A.U1.13 (`:115-117`); A.U7.11/A.U7.12 (lint/typecheck summary); A.U7.02/A.U7.03/A.U7.07 + A.U36.548 (6)
  (`:156-176` summary paragraph and sample block); A.U27.26 (venv); A.U28.02 (pin location); A.U36.526 (3) (CI paragraph
  holds); A.U28.06 (no device count in CI mentions); A.U8.16 (`:143-145` Pi4 figure); OR133
- **Site**: `README.md:113-184`
- **Change**: `:115-117` "(the pre-refactor codebase — `python/`, `modules/` — isn't covered yet)" → "(the legacy tree,
  `legacy/`, is never covered)"; `:120-122` "Needs Python 3.11+ …" kept; the recipe block (`:124-135`) moves to
  Recipes (M.DOCS.050/.049); `:137-155` (test.sh arguments and environment) moves to the reference (M.DOCS.052) and the
  section keeps one sentence: "Every runner validates its arguments and settings first; a usage or setting error exits 2
  before anything is touched (owner, 2026-10-01)."; `:155-164` → "Every `tests/test_*.py` file runs as its own
  interpreter process (per derived device for a PER_DEVICE file) and prints its `PASS`/`FAIL`/`SKIP` lines and its
  count, prefixed with its own name; a file collecting no test fails. The run ends with the summary block every runner
  prints (SPECIFICATION.md E.10): units, levels, the GC stage, counts, the failures named, and any file whose output
  contained a `MemoryError` or `memory allocation failed` — which fails the run even when its tests passed (`src/` logs the
  message, not the class)." and the sample block (`:166-173`) → the E.10 block as `scripts/test.sh` prints it, counts as
  `<n>/<m>`; `:175-184` keeps the CI sentence with "`lint.sh`/`typecheck.sh`/`test.sh` run in CI on every push/PR, plus
  `unit-tests-coverage` (its number advisory, its test result gating, SPECIFICATION.md E.5.3) and the gating
  `unit-tests-gc-threshold`" and "Config lives in the root `pyproject.toml`; every tool is pinned there, uv itself by
  `[tool.uv] required-version`; `lint.sh` and `typecheck.sh` refuse a venv `uv sync --locked` would change." The Pi4 probe
  figure (`:145`) leaves README (A.U8.16 records it as a Part N basis).
- **Resolved**: A.U36.548 (6) asks for "the summary block A.U7's runner contract prints"; A.U7.03 owns the block —
  one text.
- **Unit**: U36. Stages: U1 (`:115-117`), U7 (summary paragraph and block, with A.U7.03), U27 (venv), U28 (pin), U36
  (moves, wording).
- **Depends**: M.SCR (summary block, exit codes), A.U7.02 (SPEC E.10)
- **Blast carried by**: CLAUDE.md tooling bullets → M.DOCS (CLAUDE.md "Code quality tooling")
- **Kind**: doc

### M.DOCS.054 "Test coverage": three traced sets, never a gate
- **From**: A.U36.526 (2); A.U24.72; A.U28.15 (Codecov gone); A.U28.16 (web coverage run gates)
- **Site**: `README.md:186-194`
- **Change**: → "### Test coverage\n\n(Recipes: Coverage)\n\nReports line coverage of `src/`, `digital_twin/`, the generated
  modules and the host build chain; it never gates and has no threshold. A failing test still fails the run (exit 1); a
  failed report alone exits 3. Outputs and CI behaviour: `SPECIFICATION.md` Part E.5."
- **Resolved**: —
- **Unit**: U36. Stage U28 (A.U28.15: the Codecov words at `:193` go with the upload).
- **Depends**: M.SCR (`--coverage` exit codes), M.TOOL (`ci.yml` coverage jobs)
- **Blast carried by**: SPEC E.5/E.5.3 → A.U36.526 (SPEC)
- **Kind**: doc

### M.DOCS.055 The website-tooling section: per-device site, preview, live tier, smoke
- **From**: A.U36.516 (7); A.U36.517 (README web section); A.U6.04/A.U6.06/A.U6.07 (`:236-244`); A.U28.24 (`:224`, `:237`);
  A.U28.17 (CI smoke); A.U24.52; A.U27.08; A.U28.06 (no device count)
- **Site**: `README.md:196-261`
- **Change**: explanation kept (the tool stack, "real engine over a shim", CI jobs and the paths filter, the smoke job's
  reason); commands → recipes (M.DOCS.047/.049/.050); `:237-242` → A.U36.516 (7)'s text ("`npm run preview` (it generates
  every device's definitions first), then open `http://localhost:8000/html/index.html` — the real `html/`+`js/` tree
  against a fake in-browser backend (`js/mock-server.js`, data composed from `mockdata/samples.json`), for the first device
  of the generated manifest; `?device=<name>` picks another device of `devices/*.toml`."); `:232` "build the real website
  into frozen_modules/frozen_html.py" → "builds what it lacks"; the CI sentence gains "in CI a missing browser engine
  fails the smoke"; no "wozi"/"dev" literal or device count remains in the section.
- **Resolved**: —
- **Unit**: U36. Stages: U6 (`:236-244` worked-example files gone, with A.U6.04), U24, U28.
- **Depends**: M.WEB (preview, manifest, samples)
- **Blast carried by**: SPEC H.2/H.7/H.8 → A.U36.517 (SPEC)
- **Kind**: doc

### M.DOCS.056 The mpremote section points to the write table and the resolver
- **From**: A.U1.06/A.U1.13 (`:329-335`, `:352-358`); A.U21.28/A.U27.13 (`:334-347`)
- **Site**: `README.md:329-359`
- **Change**: `:331-333` (write sentence) → "What each `mpremote` operation writes to the board, and what it stops:
  `tests_hardware/README.md` 'What each tool writes to the board'."; `:333-335` → "`scripts/mpremote_connect.sh` runs `uv
  run mpremote connect <board>`, where the board is the one `setup_toolchain.py board` resolves (USB vendor `2e8a` and
  its MicroPython by-id name); `MPREMOTE_DEVICE` overrides it."; the examples (`:337-342`) → recipe pointer;
  `:344-348` keeps the `dialout` note, its "pass it as `MPREMOTE_DEVICE` yourself" clause goes; `:352-358` → A.U1.13's
  text ("documented in `tests_hardware/README.md` (bench wiring, host network, tool writes, by-hand workflow)").
- **Resolved**: —
- **Unit**: U27. Stages: U1 (pointers), U27 (resolver, with A.U27.13).
- **Depends**: A.U1.04-A.U1.06 (HW_BENCH), M.SCR (`mpremote_connect.sh`), M.TOOL (`board`)
- **Blast carried by**: A.U1.09 → TSC
- **Kind**: doc

### M.DOCS.057 Real hardware: levels L3 and L4, soak as durations, the verdict text
- **From**: A.U36.008; A.U7.18; A.U7.14/A.U7.17 (`:413-422` verdict and manual summary); A.U26.74/A.U26.35
- **Site**: `README.md:361-422`
- **Change**: A.U36.008's heading, intro and table verbatim ("## Real hardware: levels L3 (flash) and L4 (bench)"; the
  intro naming SPECIFICATION.md E.6.1, manual mode and soak durations as not levels, the owner go-ahead rule; the three
  rows; the soak line with `--duration`); the recipe block → pointer to Recipes "Tests per level" (M.DOCS.049); `:414-422`
  → "Every runner, the manual one included, ends with the summary block (SPECIFICATION.md E.10), its verdict read from
  the run record: a test skipped for an unreachable board is not clean, and a deselected gate is named, not hidden."
  `:326`'s cross-reference follows the new heading.
- **Resolved**: A.U36.008's recipe-block edits (`:377`, `:380`, `:398-403`) land in the recipe M.DOCS.049 holds.
- **Unit**: U36. Stages: U7 (verdict text), U26 (flags).
- **Depends**: A.U36.007 (SPEC E.6.1), M.HW_BENCH (run record verdict)
- **Blast carried by**: `tests_hardware/README.md:93`, `:425` and SPEC `:3685` "soak duration" → A.U36.008 (HW_BENCH, SPEC)
- **Kind**: doc

### M.DOCS.058 The digital-twin section: any device, no default, no counts
- **From**: A.U36.511 (11); A.U36.024; A.U25.48; A.U24.68; A.U7.09 (`:522-523` quoted lines); A.U25.46 (soak host-side,
  holds); adherence: G9/R11 dated counts ("fourteen sequential runs" `:510`, "any of the other 5" `:514`)
- **Site**: `README.md:424-529`
- **Change**: `:429-433` → "Every device of `devices/*.toml` runs end-to-end; each runner takes the device as a required
  argument (`--device <name>` or a positional name) — see `digital_twin/README.md`. A run serves that device's real,
  production website (`scripts/build_website.sh <device>`) — see `SPECIFICATION.md` Part H.7."; the quick-start and flag
  lists → recipe "Twin launch" (M.DOCS.050) and the reference blocks (M.DOCS.052); `:474-478` (soak host-side) kept;
  `:509-515` → "**Automated CI suite** — the walkthrough below turned into an unattended, CI-gating check: it drives
  `digital_twin/run_generic_integration.py` through its runs and asserts every step (`digital_twin/README.md`'s
  'Automated CI suite' lists each run); it runs against the device named by its required argument and builds the Unix
  port and that device's website if missing."; `:522-523` → "It ends with the summary block (SPECIFICATION.md E.10)";
  `:528-529` kept.
- **Resolved**: —
- **Unit**: U36. Stages: U7 (summary text), U24/U25 (device argument; `:518-519` example → `scripts/run_digital_twin_ci.sh
  <device>   # a device of devices/*.toml (required)`, A.U36.024 text), U36.
- **Depends**: M.SCR (runner usages), M.TWIN
- **Blast carried by**: `digital_twin/README.md` → M.TWIN.060 (TWIN)
- **Kind**: doc

### M.DOCS.059 A Release section with the version and the release note
- **From**: A.U37.11 (3); A.U37.12; A.SDEP.25 (pins named)
- **Site**: new `## Release` before `## Further reading`
- **Change**: "The current release is `2.0` (`buildgen/version.py`; SPECIFICATION.md L.7). A release is the merge into
  `main`, tagged `v<version>` on that merge commit with the owner's agreement. Legacy units move to it by the owner's
  reflash ("Moving a legacy unit to this firmware")." then "### Changes from the legacy firmware" — A.U37.12's grouped
  text (API; behaviour; corrected behaviour, one line each, the lines the units hand over plus the seven A.U37.12 writes;
  moving a legacy unit; the pinned MicroPython, lwIP, cyw43 and Microdot versions), current-state wording, no audit ID,
  DEVICE_REFERENCE's operator notes linked, not copied.
- **Resolved**: the version `2.0` is the agent decision under review (A.U37.11, OR2.c list; brief: "U37 sets release
  version 2.0").
- **Unit**: U37
- **Depends**: A.U37.10, A.SDEP.25, every action carrying a release-note line
- **Blast carried by**: tag message, PR description → A.U37.13/A.U37.16 (U37); citation check → TSC
- **Kind**: doc

### M.DOCS.060 "Further reading" becomes the one complete map
- **From**: A.U36.547 (8); A.U17.08 (changelog note); A.U0.38 (V01 `:697-698`); A.U34.02 (licence bullet); A.U0.42 and
  A.U36.546 (3) (`:734-735` "open option" deleted; `:655-657` BACKLOG line); A.U37.06 (BACKLOG line); A.U36.541 (5) (Part 0);
  A.U36.524 (`:649-650` "pre-push verification" goes); A.U8.01 (Part N named); A.U1.13 (`tests_hardware/README.md` and
  `legacy/README.md` entries); A.U36.543 (`.claude/skills/integrate-module/`); A.U36.545 (4) (`datasheets/`); A.U37.15
  (plan and `audit/` entries go); A.U37.03/A.U37.04 (6) (every doc listed; close check); A.U32.01 (runbook named under
  README's own recipes, no separate map entry)
- **Site**: `README.md:641-782`
- **Change**: end state: "## Further reading\n\nEvery supporting document, licence file and reference text; a new one joins
  this map in the same change (`tests_scripts/test_readme_reference.py` checks it)." then, one line per entry —
  **Standing docs**: CLAUDE.md ("AI-session operating constraints: hard rules, working agreements, PR workflow,
  code-quality tooling"); SPECIFICATION.md ("the central specification; Part 0 states the design principles, Part N the
  tunable-parameter register"); BACKLOG.md ("the four kinds of open content its header names; a resolved item leaves, its
  facts going to SPECIFICATION.md and its rules to CLAUDE.md"); DEVICE_REFERENCE.md ("user-facing notes for configuring
  and operating a unit"); HEAP_FRAGMENTATION_MEASUREMENTS.md ("how to take a heap figure worth believing; method, not
  results"); `digital_twin/README.md` ("the hardware simulator: what's there, running it, adding a chip fake; SPECIFICATION.md
  A.10 places it"); `tests_hardware/README.md` ("the real-hardware reference: the dev bench's wiring, chips,
  host-network recipe and dated state, how a round runs, the gates and their wear"); `legacy/README.md` ("the legacy tree:
  `legacy/firmware/` — what the owner's legacy units run, MicroPython 1.24.1, `legacy/firmware/update_and_install.txt`
  included — and `legacy/dev_drivers/`, the dev unit's 2026-08-27 snapshot; reference-only"); `.claude/skills/integrate-module/`
  ("starts an agent on SPECIFICATION.md Part K's checklist"). **Licences**: LICENSE; THIRD_PARTY_LICENSES.md (A.U34.02's
  text: "every vendored or derived third-party file with its source, holder and license (…), what the firmware image and
  the website contain and the notices a published image carries, and a disclosure that parts of this codebase were
  written with AI assistance. `arduino/` is outside it and every other review (lint, test, license, secret scan):
  post-audit only (owner, 2026-09-25; the secret scan too, owner, 2026-09-30)."); `ext/LICENSE-microdot`;
  `ext/freezefs/LICENSE`; `src/LICENSE-captive_dns`. **Reference material**: `datasheets/` ("the private submodule
  `hundertvolt/datasheets`; `git submodule update --init datasheets`"). **Temporary**: UART_C_PORT_CHANGELOG.md ("the UART
  protocol changes the Arduino C implementation must take; kept until the post-audit C reconciliation deletes it (owner,
  2026-09-25); the protocol itself is SPECIFICATION.md Part J"); PROJECT_AUDIT_PLAN.md and `audit/` while they exist. Then
  the handover sentence (`:710-712`) kept. Every provenance paragraph goes (`:643-645`, `:651-654`, `:672-690`, `:760-776`,
  `:778-782`).
- **Resolved**: A.U17.08 moves the changelog out of "Temporary docs" to a note; A.U36.547 (U36, later) and A.U37.15 keep
  it under **Temporary** — the map lists it there, with A.U17.08's lifecycle words. A.U36.546 (3)'s and A.U37.06's
  BACKLOG lines are combined (both true). `legacy/README.md`'s entry is A.U1.13's, with A.U36.547's mention of
  `update_and_install.txt`.
- **Unit**: U37. Stages: U0 (`:697-698` V01 wording; `:734-735` sentence deleted, A.U0.42), U1 (A.U1.13's two entries;
  `dev_legacy/README.md` entry replaced), U8 (Part N named in the SPEC line), U17 (changelog lifecycle wording in place),
  U34 (licence bullet), U36 (the map rewrite with every U36 constituent), U37 (BACKLOG line per A.U37.06; phase D drops
  the plan and `audit/` entries, A.U37.15).
- **Depends**: A.U1.03 (`legacy/README.md`), A.U36.543 (skill), A.U28.35 (submodule), M.DOCS.001
- **Blast carried by**: map completeness → `test_readme_reference.py` (TSC); CLAUDE.md `:3-6` pointer stays true
- **Kind**: doc

