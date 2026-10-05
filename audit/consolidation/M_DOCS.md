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
- **Review-answer tags (A-C review fold, 2026-10-05)**: where a change below writes the permanent tag of one of the 68
  decisions the owner answered on 2026-10-02 (`audit/actions/FOLD_ANSWERS.md`), a decision answered "fine" reads
  "(agent, <its date>; owner-reviewed, 2026-10-02)" (an existing owner tag stays as it is); one answered with a change or
  a question carries the owner's ruling in place of the proposed text, tagged "(owner, 2026-10-02)"; the 2026-10-05
  rulings (OR141-OR143) are "(owner, 2026-10-05)". This holds also inside an action's text quoted "verbatim". Which
  change carries which decision's tag: the F21 table in "A-C review fold (2026-10-05)" at the end.

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
- **Blast carried by**: README licence paragraph → M.DOCS.060 (README licence bullet); the same exclusion in
  CLAUDE.md/SPEC A.1/J.1/BACKLOG/README → M.DOCS.076, A.U0.38 (SPEC); A.U34.07's check reads entries
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
- **Blast carried by**: CLAUDE.md vendoring bullet → M.DOCS.075; SPEC A.1/A.5 tag →
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
  hash test → A.U34.08 (4) (TSC); BACKLOG chroot line → M.DOCS.066
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
- **Blast carried by**: one-entry check → A.U34.07 (TSC); DEVICE_REFERENCE's ISL29125 procedure → M.DOCS.031
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
- **From**: A.U34.04; AC3_O O-23 (actor-tag form)
- **Site**: `THIRD_PARTY_LICENSES.md:93-105`
- **Change**: → A.U34.04's text verbatim ("- `src/voc_algorithm.py` — a literal port of the Python translation in
  [`DFRobot/DFRobot_SGP40`](…)'s `Python/raspberrypi/DFRobot_SGP40_VOCAlgorithm.py`, © 2010 DFRobot Co.Ltd
  (http://www.dfrobot.com), author yangfeng, MIT (that repo's `LICENCE`: "Copyright 2010 DFRobot Co.Ltd", matching this
  file's header). That translation ports Sensirion's Gas Index Algorithm (VOC variant) from
  [`Sensirion/embedded-sgp`](…) (`sgp40_voc_index/sensirion_voc_algorithm.c/.h`; archived April 2024, BSD-3-Clause); the
  maintained successor is [`Sensirion/gas-index-algorithm`](…) (BSD-3-Clause, © 2021 Sensirion AG). Because this file
  ports DFRobot's Python rather than Sensirion's C, DFRobot's MIT terms are treated as the ones governing what was copied
  (agent, 2026-08-20; not a verified legal conclusion); Sensirion's BSD-3-Clause is recorded for the full chain,
  and a published image carries its notice too (below). `tests/voc_reference_vectors.py` holds output values computed by
  Sensirion's C (the gas-index-algorithm fixed-point helpers and the archived embedded-sgp algorithm) and contains no
  Sensirion code."). `:90-91`'s section intro unchanged.
- **Resolved**: —
- **Unit**: U34
- **Depends**: A.U12.12 (the data file named; M_TEST_UNIT), M.DOCS.011 (the image notice it refers to)
  A-C2: M.DOCS.008 and M.DOCS.011 refer to each other and land in one U34 commit.
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
- **From**: A.U34.09 (1); F21 tag form (licence-notices) (A-C review fold)
- **Site**: new section "## What the firmware image and the website contain" before "## Not third-party (built into
  MicroPython itself)" (`:157`)
- **Change**: A.U34.09 (1)'s section text verbatim (compiled-in components with their licences, frozen micropython-lib
  packages and port modules, this repo's frozen modules, "No license text is frozen", the website bundles no npm
  package, and "**Publishing an image** (agent, 2026-09-30; owner-reviewed, 2026-10-02; public MIT repository, owner,
  2026-09-26): …" with its notice list). The executor reads each submodule licence at the commit named and each in-tree component's source headers,
  corrects any licence the file contradicts, records which of mbedTLS's two licences the image uses and any Apache-2.0
  `NOTICE`; the component list and commits are those of the pin B0's refresh leaves (re-derived if it moved).
- **Resolved**: —
- **Unit**: U34
- **Depends**: A.U0.03 (corpus, submodules initialised), A.SDEP.08 (pin), M.DOCS.003, M.DOCS.008
  A-C2: M.DOCS.008 and M.DOCS.011 refer to each other and land in one U34 commit.
- **Blast carried by**: README licence bullet → M.DOCS.060; no check (prose; a published image is outside CI)
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
- **Unit**: U34 (after A.U28.35's move in U28). Precondition (AC_NOTES 37) satisfied: the owner gave standing push
  permission to `hundertvolt/datasheets` (owner, 2026-10-05; OR144.a), so A.U28.35's move runs and this section is
  written (A-C review fold, lead ruling).
- **Depends**: A.U28.35
- **Blast carried by**: README/CLAUDE.md/SPEC A.6 location text → M.DOCS.047, M.DOCS.068, A.U36.545 (SPEC)
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
- **Blast carried by**: CLAUDE.md UART bullet "(a temporary file …)" → M.DOCS.076; SPEC J.1 `:5346-5347`
  → A.U17.08 (SPEC); README "Temporary docs" → M.DOCS.060; A.U37.03/A.U37.04 (4) keep the file at close (audit
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
- **Blast carried by**: the same V01 sentence in CLAUDE.md/SPEC/BACKLOG/README → M.DOCS.076, M.DOCS.065, M.DOCS.060, A.U0.38
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
- **Blast carried by**: CLAUDE.md `:131-137` → M.DOCS.076; no test pins either text
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
- **Blast carried by**: CLAUDE.md UART bullet's entry clause → M.DOCS.076
- **Kind**: doc

### M.DOCS.019 One closed status set; rows in number order; a Status column for Class B
- **From**: A.U17.09; OR143.a (3) (row A15 joins the order) (A-C review fold)
- **Site**: `UART_C_PORT_CHANGELOG.md:48-49` (status line), `:53-66` (Class A table), `:70-103` (Class B table)
- **Change**: `:48-49` → "Status values, a closed set: `proposed` (agreed in principle, not yet implemented),
  `applied-python` (live in `src/`; pending the C side for Class A, final for Class B), `recorded` (nothing to change on
  either side — an existing rule written down so the C side is checked against it), `reconciled` (done on both sides —
  the entry can be removed). A qualifier goes into the entry's own text, never into the Status cell." Class A rows
  ordered A1 … A15 (A13/A14/A15 from M.DOCS.022); Status cells: A4 `recorded`, A8 `recorded`, A6 `applied-python`, A7
  `applied-python`, A11 `proposed`; A1-A3, A5, A9, A10, A12 unchanged. Class B gains a trailing `Status` column, every
  row `applied-python`.
- **Resolved**: —
- **Unit**: U17
- **Depends**: M.DOCS.021 (A7/A8/A11 cells, same rows), M.DOCS.024 (rows B33-B52 already present)
- **Blast carried by**: set and order checked → M.TSC.152 (A.U17.11 (2) (d)(e))
- **Kind**: doc

### M.DOCS.020 A constants table the check reads
- **From**: A.U17.11 (1); OR143.a (1)-(2), OR141.a (4) (the constants the fold adds) (A-C review fold)
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
  rule at execution (a wire value or recovery timing is A) and reported in the unit's commit. (A-C review fold) A
  `const()` the receive chunking, the receive cap or the ring floor adds to the module (OR143.a, OR141.a (4)) joins the
  table in its landing commit: a default or bound that decides which train is accepted (the `max_transfer_bytes`
  default) is Class A, a memory-only one (the `chunk_bytes` default, a ring-floor term) Class B; `Last entry` names the
  row that introduced it (M.DOCS.022 A15, M.DOCS.024 B65-B69).
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

### M.DOCS.022 Three new Class A rows: GET is one chunk; a validated command resets the backoff; the receive cap
- **From**: A.U17.16, A.U17.17, A.U17.30; OR143.a (2)-(3) (the oversize-train refusal, Class A, receiver-only) (A-C
  review fold)
- **Site**: Class A table, after A12
- **Change**: "| A13 | Reject a GET frame whose `CHUNKS` is not 1 | J.4 defines a GET as a one-chunk train, and a GET
  declaring more chunks was answered as though it were one | That the C sender always emits `CHUNKS = 1` on a GET. A
  receiver-only tightening: a conforming peer is unaffected | applied-python |" and "| A14 | A responder re-listens at
  once after any transaction whose command frame validated and was then answered, declined or aborted mid-train
  (`ListenResult.cmd` set); a listen that returns no command kind backs off (`timeout/2` doubling to `5 × timeout`) | A
  declined command used to send the loop into that backoff, so an initiator retrying after its own resync (about
  `4 × timeout`) could transmit while the responder slept and fail again | That the C responder does not back off after a
  declined or aborted command beyond the initiator's retry window | applied-python |" and (A-C review fold) "| A15 |
  Refuse, before anything is allocated, a train whose declared size — its `CHUNKS`, or the size the local caller
  expects — exceeds the receiver's `max_transfer_bytes` (a constructor argument with a default, declared per link in the
  device TOML): the ACK is withheld, as for any rejected frame, and the refusal is logged once | A peer could declare up
  to 64,770 bytes at `payload_size = 255` and the receiver allocated it, so a large or hostile transmission could flood
  the heap (owner, 2026-10-05) | That the C sender never declares more than the receiver's cap, and whether the C
  receiver refuses the same way. A receiver-only tightening: a conforming peer within the cap is unaffected |
  applied-python |".
- **Resolved**: —
- **Unit**: U17 (A15 with `max_transfer_bytes` and its refusal)
- **Depends**: M.SRC_NET.159, M.SRC_NET.170, M.DOCS.019; M.SRC_NET.220 (the refusal)
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
- **From**: GAPS_G2 H-6 (the attributes G2 made private, into B39); A.U2.26 (+A.U2.20), A.U3.13 (+A.U3.02, A.U3.08; gap M_SRC_NET 6: `_note_valid_frame()`), A.U5.12 (+A.U5.02),
  A.U10.04, A.U10.18, A.U10.29, A.U10.35 (+`set_callback`, M_SRC_NET gap 6), A.U10.37 + A.U10.38, A.U10.44 + A.U32.06,
  A.U10.45, A.U11.31, A.U12.02, A.U12.03, A.U12.16, A.U13.12, A.U13.13, A.U13.14, A.U13.17, A.U13.18, A.U16.05, A.U17.01,
  A.U17.06, A.U17.10, A.U17.14, A.U17.20, A.U17.22, A.U17.26, A.U17.28, A.S0930.07, A.U24.67, A.U30.19, A.U35.44, A.U17.30
  (the numbering rule); OR141.a (4) (f) (the DMA receive ring, "no C impact"), OR143.a (1)-(2) (the chunked assembly,
  the readline cap, the TOML keys) (A-C review fold)
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
  - **B39** (U10): "`UARTComm`'s `get_callback`, `set_callback`, `message_callback`, `frame_size`, `uart`, `role`,
    `payload_size`, `timeout` and `uid`, `asy_uart_driver.UART`'s `cancel` and `txbuf`, and `UARTLinkDriver.role` become
    private (`_`-prefixed; none is read outside its class) | Python-internal; no C impact".
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
  - (A-C review fold) Five rows, numbered at landing in landing order with the rows above (B65/B66 after B51, B67/B68
    after B60, B69 after B61), each "no C impact":
  - **B65** (U13): "Each link receives through a DMA ring: after every init the driver clears the UART's RX and
    RX-timeout interrupt masks and enables its RX DMA request; a DMA channel paced by that request fills a
    power-of-two ring held for the program's life, a chained channel reloads its count, and reads copy from the ring by
    index; `machine.UART`'s receive calls are no longer made and its receive buffer drops to its minimum; a lap of the
    ring is detected and handled as a receive overrun | No byte on the wire changes and no accept/reject rule moves;
    bytes arriving while a flash write holds interrupts off are no longer lost (owner, 2026-10-05)".
  - **B66** (U13): "`readline_until_complete()` is capped and no longer grows by concatenation: a line over the cap is
    discarded and the call returns `None` | No protocol path uses readline (B47); no wire effect".
  - **B67** (U17): "`UARTComm` refuses a receive ring below its floor — the larger of one framed frame, one poll
    interval's arrivals and what the peer can send during the longest synchronous flash write under stop-and-wait,
    rounded up to a power of two — and resyncs on a lap like any receive overrun | A local refusal and the existing
    recovery; no byte, acceptance rule or timing on the wire changes".
  - **B68** (U17): "A train with no caller destination is assembled in pieces of at most `chunk_bytes` (a constructor
    argument with a reasoned default) instead of one peer-sized allocation, and the caught `MemoryError` at those
    allocations goes | Memory only: the bytes acknowledged and delivered are identical".
  - **B69** (U20): "Each `uart_link` end declares its receive-ring size and `max_transfer_bytes` in the device TOML, and
    the build checks the two together | Wiring only; the cap's refusal is A15".
- **Resolved**: A.U32.06's own row ("`start_listen`, `start_exercise`") and A.U10.44's are one row with the U10 names
  (M.SRC_NET.170, M_SRC_NET gap 6). A.U10.35's row adds `set_callback` (M.SRC_NET.155 makes it private; gap 6). A.U3.13's row
  adds the synchronous `_note_valid_frame()` (M.SRC_NET.164; gap 6 — no constituent carried it). A.U10.37/A.U10.38's two
  rows are one "names only" row also naming the CRC and codec classes A.U10.38 renames (agent, one row per change kind).
  B39 also carries the attributes gap pass G2 makes private (M.SRC_NET.155/.192/.213; GAPS_G2 hand-off H-6): one Class B
  row per change kind, landing with the U10 privatisation, so the later stages that touch `txbuf` (U13) or
  `UARTLinkDriver` (U17) write the private names (gap pass G1).
  A.U35.44's text follows M.SRC_CORE.116 (the guard became a parameter). No row: A.U10.21 (its condition — a changed
  `setup()` docstring — does not occur, M.SRC_NET.169), A.U10.33 (member order is not recorded, its own text and
  M.SRC_NET.173, overriding A.U17.30's list), A.U13.19 (its own slot: no entry), A.U12.01 (bytes unchanged, its own slot),
  A.U17.21/A.U20.18 (build-side refusal, no module change), A.U35.47/A.U0.49/A.U8.06 (comments only), A.U35.48 (no UART
  path changed by its merge).
- **Unit**: per row as listed (U2 … U35); the merged change is complete at U35.
- **Depends**: each row's code change (M.SRC_NET.150-.216, M.SRC_CORE.115-.122; for B65-B69 M.SRC_NET.221, M.SRC_NET.222,
  M.SRC_NET.202, M.SRC_NET.220, M.GEN.066); M.DOCS.019 (Status column from U17)
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
- **From**: A.U36.531; A.U26.84 (the readiness defaults cited; M.HW_BENCH.085's Blast, gap pass G1); A.U14.R01 / A.U14.17 (the power-cycle item), A.U15.11/A.U15.12 (operator procedure handed here),
  A.U32.01 (the runbook pointer), A.U19.14 (linked section); OR138.a (1)-(2) (`ConfigFaults` and the reset that deletes
  damaged files), OR136.a (1) (each file written once with its defaults), F21 tag form (operator-actions-one-place) (A-C
  review fold)
- **Site**: `DEVICE_REFERENCE.md`, new "## Commissioning and operating: what needs a person" after the header (`:1-5`),
  before "## Neopixel LED"
- **Change**: A.U36.531's section verbatim, its decision tag in the review form "(agent, 2026-09-27; owner-reviewed,
  2026-10-02)" (A-C review fold, F21) (items 1-8: Wi-Fi setup through the hotspot; `AmbPres` once; `ForceCalRef`
  with **FRC Readiness**; `SelfCal`; ISL29125 calibration; read **Last Reset Reason** and save `GET /status` before
  clearing; power-cycle a unit whose I2C sensors stay unreadable after a reboot; the reflash runbook in README.md
  "Moving a legacy unit to this firmware"), with the labels as the definitions carry them at landing; and (A-C review
  fold) after the Last Reset Reason item, one more: "**Config Faults** (Status) names a module whose config file existed
  at this boot but could not be read or was damaged (unparseable, not a JSON object, or holding a value the schema
  refuses). An unreadable file is never overwritten and its module runs on its defaults; a damaged one was rewritten
  at this boot, its lost values back at their defaults, and stays listed until the next boot. **Reset to defaults**
  deletes every config file, unreadable ones included, after which each is written once with its defaults (owner,
  2026-10-01)." The `ForceCalRef`
  item cites the FRC readiness defaults by their SPECIFICATION.md Part N rows (`sens.scd30_frc_*`), not by value; the
  bench measures them in phase C (M.HW_BENCH.085, R5), and that round's delta (A.C.10) restates any figure this file
  gives (A.U26.84's docs slot; gap pass G1).
- **Resolved**: —
- **Unit**: U36
- **Depends**: A.U6.18, A.U6.23 (labels; GEN/WEB), A.U15.12 (`FRCState`, SRC_SENS), A.U14.17 (SPEC F.2 text), A.U32.01 (README
  runbook, M.DOCS.048), A.U36.530 (SPEC A.4), M.DOCS.032; M.GEN.014 (the Config Faults row's label), M.SPEC.021
  (A.8's `ConfigFaults`)
- **Blast carried by**: README runbook links here → M.DOCS.048; SPEC F.2 → A.U14.17 (SPEC)
- **Kind**: doc

### M.DOCS.027 The Neopixel section states the Wi-Fi LED patterns, the window and the refusal
- **From**: A.U36.546 (4) (the overlay bullet checked against the firmware), A.U18.30 (deactivated pattern), A.U10.40
  (`LedWifiOn` → `LEDWifiOn`), A.U9.01 (window bullet), A.U9.03 (manual flash refusal); OR140.a (17) (the Wi-Fi-off pattern
  follows the Wi-Fi LED setting), OR140.a (5) (the refusal tells the caller to retry later) (A-C review fold)
- **Site**: `DEVICE_REFERENCE.md:7-25`
- **Change**: `:11-14` (WiFi status overlay bullet; "on/off only … not a live connectivity signal" contradicts the
  service, which blinks the overlay per link state) → "- **Wi-Fi status overlay** — a dim white glow showing the Wi-Fi
  state while `/networking`'s `LEDWifiOn` is on (off: the overlay stays dark): searching for the network — toggling
  every half second; connected — on; disconnected — off; serving the fallback hotspot — on with a short gap every 3 s,
  steadily on once a client has joined; Wi-Fi switched off (a second failure streak after the hotspot ran, or no
  readable Wi-Fi configuration) — off with a short blink every 3 s, until a power cycle. Every one of these patterns
  follows `LEDWifiOn`, the switched-off one included: dark while it is off, shown as soon as it is switched on (owner,
  2026-10-02)." The notification bullet `:15-19` gains, after the brightness/duration sentence: "It flashes only inside
  the notification window `OnH:OnM`–`OffH:OffM`; an On time later than Off spans midnight (e.g. 22:00–06:00). A manual
  flash (`LightCmdLED`) is refused ("Failed") while another flash is still playing — try again later; a notification the
  unit raises itself waits for the playing flash and then queues, since the unit's own notifications are few and spaced
  (owner, 2026-10-02)." Table unchanged.
- **Resolved**: the pattern list is read from the service at landing (A.U36.546 (4): the executor checks the text against
  `asy_wifi_service.py`/`asy_neopixel_driver.py` and corrects any mismatch); `LightCmdLED` per A.U10.40.
- **Unit**: U36. Stages: U9 (window and refusal sentences, old key names), U10 (`LEDWifiOn`, `LightCmdLED`), U18 (the
  deactivated pattern clause and the fold's "follows `LEDWifiOn`" sentence, with M.SRC_NET.077/.100), U36 (the bullet's
  full rewrite, the fold's retry/queue sentence with it).
- **Depends**: M.SRC_NET (WiFi LED patterns, `_LED_DEACTIVATED_*_MS`; M.SRC_NET.077/.100 as the fold amends them),
  A.U9.01/A.U9.03 (SRC_SENS/GEN); M.SRC_NET.122 (the refusal's retry wording)
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
- **From**: A.U19.14 (1); A.U36.503 (H.4 points here); OR137.a (2) (`ResetErrors` clears the dropped-connection count),
  OR140.a (3) (the website asks before clearing) (A-C review fold)
- **Site**: `DEVICE_REFERENCE.md`, new "## Clearing the error logs" at the end
- **Change**: A.U19.14 (1)'s text verbatim ("The Status page's error-log reset (`PUT /status {"ResetErrors": true}`) clears
  every module's log at once. It must finish within the device's 15-second request limit, the same limit the web page
  waits; on a busy device it can take several seconds. A reset that reports "Failed" means one module's log could not be
  written; the other logs are cleared. Read and save the logs before clearing them: the reset cannot be undone."), with
  (A-C review fold) "clears every module's log at once" → "clears every module's log and the dropped-connection count
  (`HTTPDropped`) at once" and a closing sentence "The page asks for confirmation before it sends the reset (owner,
  2026-10-02)."
- **Resolved**: —
- **Unit**: U19 (the `HTTPDropped` clause with the window counter, U19); stage U23 (the confirmation sentence, with the
  website's confirm dialog)
- **Depends**: M.SRC_NET (A.U11.31's concurrent reset, U11); M.SRC_NET.129 (`ResetErrors` clears the window),
  M.WEB.021 (the confirm dialog)
- **Blast carried by**: SPEC H.4/C.7 → A.U11.31, A.U36.503 (SPEC); BACKLOG item 24 → M.DOCS.063
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
- **Blast carried by**: README map → M.DOCS.060; check exclusions → A.U37.15 (TSC)
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
- **From**: A.U36.547 (2), A.U0.24, A.U1.13 (`:17-20` HTML-source paths); OR140.a (18) (no build but `dev` is special;
  WoZi-specific wording goes) (A-C review fold)
- **Site**: `README.md:10-20`
- **Change**: end state → "## Devices\n\nThe firmware is generated per device from `devices/<device>.toml` (SPECIFICATION.md
  Part L); today six:" then `| Device | Unit |` rows — `wozi` and `arzi`: room units; `klkizi`, `grkizi`, `schlafzi`:
  the three units the legacy firmware calls `neu`, each its own file; `dev`: the bench rig, the only unit a session
  flashes — then "Every device but `dev` is built and tested alike; `dev`'s bench role is the one exception (owner,
  2026-10-02)." (A-C review fold: the `wozi` row's "verified through the tests and the twin, never flashed by a session"
  goes) — then "Which sensors,
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
  A.SDEP.04 (`:208-209`), A.U36.512 (5) (wording); OR140.a (1) (the bench AP password is a throwaway passed plainly; no
  interactive-mode route) (A-C review fold)
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
  SSID and password unless `BENCH_AP_PASSWORD` (and `--ssid`) is set — a throwaway password, used once and passed to
  `nmcli` on its command line; a generated one is shown once, and none is ever committed (owner, 2026-10-02)." (A-C
  review fold: "never on a command line or in a log" goes with the interactive-mode route.) Then A.U36.522's sentence ("Once a bridge exists, re-running `env --tier bench` (with or without these
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
- **Depends**: M.TOOL (U21 installer changes: `--password` gone, `BENCH_AP_PASSWORD` passed plainly to `nmcli` as the
  fold amends A.U21.19's change, `_TIER_COMMANDS`, record, resolver, `build-lwip`), A.U28.35 (submodule; the owner's
  push-access step, AC_NOTES 37, satisfied: standing push permission, owner, 2026-10-05, OR144.a)
- **Blast carried by**: `setup_toolchain.py --help` ↔ README → `test_readme_reference.py` (TSC); `tests_hardware/README.md`
  Prerequisites/host network → M.HW_BENCH (HW_BENCH); SPEC A.6/B.5/B.12/B.13 → A.U36.545/A.U21.03/A.U21.24/A.U36.523
  (SPEC)
- **Kind**: doc

### M.DOCS.048 Recipe "Build and flash", the flashing rule, and the reflash runbook
- **From**: A.U36.547 (4)(5); A.U36.010; A.U32.01 (runbook and `:299` clause); A.U27.35 (work dirs); A.U27.36
  (`--no-autostart`); A.U26.02 (image record); A.U20.05; A.U6.03/A.U6.04 (`<device>` no longer an `html/definitions`
  file); adherence: CLAUDE.md credential rule (the runbook's legacy hotspot password); OR140.a (18) (no device but `dev`
  is special: the WoZi wording of the flashing rule and the runbook lead goes; A.U32 open point 3 superseded), F21 tag
  form (reflash-runbook-erase) (A-C review fold)
- **Site**: `README.md:263-327` ("Building real firmware", "Flashing a real board"), new `#### Moving a legacy unit to this
  firmware (reflash runbook)` after it
- **Change**: build: `uv run scripts/build_firmware.py <device>` (→ `build/firmware-<device>.uf2` and its image record
  beside it, SPECIFICATION.md B.11); "`<device>` names a `devices/<device>.toml`; every device there builds."; "Build
  intermediates stay under `build/` for inspection (the firmware stage, the website stage and the frozen-HTML step each
  in its own work dir per device) and are wiped at the next build of the same device."; "`--no-autostart` builds
  `build/firmware-<device>-noautostart.uf2`, which boots to the REPL instead of running `main()` (to start it by hand, e.g.
  in Thonny); it needs an empty filesystem, as any flash does after a legacy firmware (runbook below)."; the website-only
  step `scripts/build_website.sh <device>`. Flash: the two picotool recipes (`:303-321`) unchanged except that the image
  is `build/firmware-dev.uf2` built as above; the rule (`:299-301`) → (A-C review fold, the WoZi wording gone) "A
  session flashes only `dev` images, onto the bench board: only the `dev` board is flashed and bench-tested (owner,
  2026-09-03), and another device's image does not match the bench wiring — see CLAUDE.md's `dev` rule. Every other
  device is built and tested alike (owner, 2026-10-02); moving one of the owner's own units is their operation (see
  "Moving a legacy unit to this firmware")."; `:323-327` names the tests as M.HW_DEV/M.HW_BENCH leave
  them (`flash/test_toolchain_flash_boot.py`'s reflash test behind `--allow-flash-cycle`; `manual/manual_toolchain.py`)
  and "see 'Real hardware: levels L3 (flash) and L4 (bench)' below". Runbook: A.U32.01's subsection verbatim (lead,
  Before (1)-(3), Flash (4)-(6), First boot (7)-(12), Back to legacy (13)-(15); no `[src: …]` note written), with
  (A-C review fold) its lead's "and nothing here flashes `wozi` from a session (CLAUDE.md)" dropped — the lead reads
  "The owner's operation on his own units; no session runs it." — and its erase-on-move reading tagged "(agent,
  2026-09-30; owner-reviewed, 2026-10-02)" (C9-form tag of the reflash-runbook-erase decision), and
  DEVICE_REFERENCE's pointer ("see DEVICE_REFERENCE.md's commissioning list for what follows the flash") after step 10,
  and step (14)'s "(SSID `SensorNode`, password `12345678`)" → "(SSID `SensorNode`, the legacy firmware's built-in
  hotspot password, `legacy/firmware/python/CommonDrivers/async_connect.py`)". Where the runbook names the test that pins the TOML hostname rule, it cites it by name,
  `tests_scripts/test_device_tomls.py::test_hostname_is_sensorstation_plus_name` (M.TSC.079 rewrites the file; a line
  number does not survive — M_TSC gap 2).
- **Resolved**: A.U36.010 and A.U32.01 both rewrite `:299-301` — combined (A.U36.010's reasons, A.U32.01's closing
  clause); OR140.a (18) (owner, 2026-10-02) removes their WoZi-specific reasons: the rule is stated for `dev` alone. The literal legacy hotspot password is not copied into README: it is the one accepted credential (CLAUDE.md
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
  hand); A.U27.08 (test.sh builds the first derived device's site); M.HW_BENCH.089 (rollover test); M.SCR.074 (the
  rollover runner; GAPS_G4 hand-off 1 (a), gap pass G1); OR139.a (3) (the runner flashes the tick-offset image and
  polls about two hours) (A-C review fold)
- **Site**: `README.md:124-135`, `:376-412`, `:517-520`
- **Change**: one block per level, each with one comment line: L0/L1 `scripts/test.sh` and `GC_THRESHOLD=32768
  scripts/test.sh` ("the suite passes at both GC stages; each builds what it lacks, the first derived device's website
  included"); a standalone `uv run pytest tests_scripts` "needs the toolchain built first (`scripts/test.sh` or
  `setup_toolchain.py setup`)"; one PER_DEVICE file by hand: `TEST_DEVICE=<device> <build-standard micropython> …
  tests/<file>` as A.U24.65 leaves it; L2 `scripts/run_digital_twin_ci.sh <device>   # a device of devices/*.toml
  (required)`; website `npm test` ("its live tier needs the toolchain built"); L3 `scripts/run_flash_hardware_suite.sh`,
  L4 `scripts/run_bench_hardware_suite.sh` ("each runs L0-L2 first"; a `-m` you pass narrows the selection;
  `--allow-flash-cycle`, `--allow-persistence-write` and the other `--allow-<marker>` gates as `tests_hardware/README.md`
  lists them); the rollover round `scripts/run_bench_rollover_test.sh` (A-C review fold: "flashes the `dev`
  tick-offset test image — one flash cycle — and polls about two hours across the tick and 32-bit wraps; on top of a
  clean bench run; the next round flashes its own image" — M.SCR.074 as the fold amends it, its flags as its `--help`
  prints them); soak durations "`scripts/run_bench_soak_tests.sh --duration
  short|mid|long` — liveness only, after a clean L4 run, never bundled into a runner"; manual mode
  `scripts/run_manual_hardware_tests.sh [--list|--only <name>]`; board-free `uv run pytest tests_hardware --collect-only`.
- **Resolved**: A.U36.008's recipe-block wording and A.U36.547's "each once" placement combined: the commands live here,
  the hardware section keeps its table and explanation (M.DOCS.057). The rollover line was a bare `uv run pytest …
  --allow-multi-day-rollover -k …`, which bypasses the run record, the verdict and the evidence archive; M.SCR.074 (AC_NOTES
  45, agent decision AD-19) gives the marker its own runner, so the recipe names it (gap pass G1).
- **Unit**: U36. Stages: U7 (`:376-392` runners' lower levels), U26 (flag names `:390-396`, U26.74's rename lands with its
  users), U27 (`--duration`, `-m`; the rollover runner line with M.SCR.074), U36 (the block).
- **Depends**: M.SCR (runner end states: `--skip-lower-levels`, `--duration`, `-m`; M.SCR.074), M.HW_BENCH.089, A.U25.48 (TWIN/SCR)
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
- **From**: A.U36.547 (6)(7); A.U7.19 (the tool set); OR139.a (3) (the rollover runner's two-hour run on the test
  image) (A-C review fold); the existing flag tables (`:45-52`, `:80-89`, `:455-472`, `:493-502`);
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
  `--password`); `--clean` "wipes every build-artifact directory, every Unix-port build flavour included". The
  `scripts/run_bench_rollover_test.sh` block (M.SCR.074) is its `--help` as written: synopsis
  `scripts/run_bench_rollover_test.sh [pytest args]`, no option of its own ("other arguments go to pytest; a -m you pass
  narrows the selection") — or the options M.SCR.074's fold amendment gives it — and (A-C review fold) "flashes the
  tick-offset test image (one flash cycle) and runs about two hours (tests_hardware/README.md)" in place of "the run
  takes ~12.4 days: start it detached". The test
  `tests_scripts/test_readme_reference.py` (A.U36.547 (7)) compares option and variable names with each tool's `--help`.
- **Resolved**: the exit-2 sentence is firm (OR133, AC_NOTES 43; no "pending" marker). The rollover runner joins the tool
  set with M.SCR.074 (GAPS_G4 hand-off 1 (b), gap pass G1).
- **Unit**: U36
- **Depends**: M.SCR (every runner's usage, M.SCR.074 included), M.TOOL (`setup_toolchain.py` subcommands and options), M.TWIN
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
  count, each prefixed with its tag in brackets — the file's name, plus the device for a PER_DEVICE file (e.g.
  `[test_microtest]`, `[test_sensortask[wozi]]`); a file collecting no test fails. The run ends with the summary block every runner
  prints (SPECIFICATION.md E.10): units, levels, the GC stage, counts, the failures named, and any file whose output
  contained a `MemoryError` or `memory allocation failed` — which fails the run even when its tests passed (`src/` logs the
  message, not the class)." and the sample block (`:166-173`) → the E.10 block as `scripts/test.sh` prints it, counts as
  `<n>/<m>`; `:175-184` keeps the CI sentence with "`lint.sh`/`typecheck.sh`/`test.sh` run in CI on every push/PR, plus
  `unit-tests-coverage` (its number advisory, its test result gating, SPECIFICATION.md E.5.3) and the gating
  `unit-tests-gc-threshold`" and "Config lives in the root `pyproject.toml`; every tool is pinned there, uv itself by
  `[tool.uv] required-version`; `lint.sh` and `typecheck.sh` refuse a venv `uv sync --locked` would change." The Pi4 probe
  figure (`:145`) leaves README (A.U8.16 records it as a Part N basis).
- **Resolved**: A.U36.548 (6) asks for "the summary block A.U7's runner contract prints"; A.U7.03 owns the block —
  one text. HEAD's tag example `[test_sensortask_dev]` names a wrapper A.U24.65 deletes; the example names surviving
  files and the `<file>[<device>]` tag of M.SCR.040-.042/M.TEST_UNIT.337 (GAPS_G3 hand-off 5, gap pass G1).
- **Unit**: U36. Stages: U1 (`:115-117`), U7 (summary paragraph and block, with A.U7.03), U27 (venv), U28 (pin), U36
  (moves, wording).
- **Depends**: M.SCR (summary block, exit codes, the per-device tag M.SCR.040-.042), A.U7.02 (SPEC E.10), M.TEST_UNIT.337
- **Blast carried by**: CLAUDE.md tooling bullets → M.DOCS.094-.098
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
- **From**: A.U37.11 (3); A.U37.12; A.SDEP.25 (pins named); F21 tag form (release-version-2-0, release-defined-point)
  (A-C review fold)
- **Site**: new `## Release` before `## Further reading`
- **Change**: "The current release is `2.0` (`buildgen/version.py`; SPECIFICATION.md L.7). A release is the merge into
  `main`, tagged `v<version>` on that merge commit with the owner's agreement. Legacy units move to it by the owner's
  reflash ("Moving a legacy unit to this firmware")." then "### Changes from the legacy firmware" — A.U37.12's grouped
  text (API; behaviour; corrected behaviour, one line each, the lines the units hand over plus the seven A.U37.12 writes;
  moving a legacy unit; the pinned MicroPython, lwIP, cyw43 and Microdot versions), current-state wording, no audit ID,
  DEVICE_REFERENCE's operator notes linked, not copied.
- **Resolved**: the version `2.0` is the agent decision under review (A.U37.11, OR2.c list; brief: "U37 sets release
  version 2.0"), answered "fine" on 2026-10-02 with the release's defined point: where the section writes either
  decision's tag it reads "(agent, <date>; owner-reviewed, 2026-10-02)" (C9-form, A-C review fold).
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


## BACKLOG.md

End state (U37): four kinds of content only — real-hardware work still owed, UART C-port items, owner-deferred goals
each with the owner's reason, and the owner-question list (A.U37.06, harmonization 3). Every other item ends in one of
the four closure states, its permanent content first moved to SPECIFICATION.md (facts), CLAUDE.md (rules) or README.md
(orientation). The changes below are grouped by the section an item sits in at HEAD; each names the unit that removes it.
Before any item number is removed, every citer is repointed (A.U36.544 (5); the citation check A.U0.08 fails otherwise).

### M.DOCS.061 The header states the four kinds and the item-number rule
- **From**: A.U37.06 (1); A.U36.546 (3); A.U36.544 (`:13-17`); A.U0.12 (the owner-question list named in the header);
  A.U33.09 (the "Everything that needs the dev bench" paragraph); A.SDEP.21 (no audit ID in written text)
- **Site**: `BACKLOG.md:3-17`
- **Change**: end state: `:3-8` → "Working memory with four kinds of content only: real-hardware work still owed; UART
  C-port items (the C side's reconciliation is outside this project, `UART_C_PORT_CHANGELOG.md` carries the protocol
  changes); owner-deferred goals, each with the owner's reason; and the owner-question list. Anything resolved leaves:
  fixed, verified stale, settled and documented where it belongs (facts in SPECIFICATION.md, rules in CLAUDE.md,
  orientation in README.md), or out of scope by the owner's decision and documented as a known limitation (owner,
  2026-09-25). See README.md for orientation, CLAUDE.md for operating constraints." `:10-11` kept ("Everything that
  needs the dev bench is gathered in 'Real-hardware work still owed' below …"). `:13-17` → "**Item numbers are never
  reused or renumbered.** A resolved item leaves, its permanent content migrated first; one whose number is still cited
  stays as a one-line closed stub only while it is cited. A gap means resolved and removed." (A.U36.544's text; with
  every citer repointed, no stub remains at U36's end.)
- **Resolved**: A.U36.546 (3) amends A.U37.06 (1)'s sentence with the parenthesis — both true, combined. A.U36.544's
  `:13-17` text lands at U36 and A.U37.06 keeps it, as it says.
- **Unit**: U37. Stages: U36 (`:13-17` per A.U36.544; header gains SPECIFICATION.md as the fact target per A.U36.546 (3)
  in HEAD's sentence shape), U37 (the four-kinds header).
- **Depends**: M.DOCS.062-067 (the sections the header describes must be in their end state when it lands)
- **Blast carried by**: citation check (A.U0.08, TSC) resolves every `BACKLOG.md` pointer; README "Further reading"
  BACKLOG line (M.DOCS.060) states the same four kinds; CLAUDE.md decision-records and change-class agreements (M.DOCS.091) name the same list
- **Kind**: doc

### M.DOCS.062 "Refactor targets not yet done" dissolves; the section heading goes
- **From**: A.U2.23 (`:20-35`); A.U36.527 (2) (`:36-51`); A.U0.37 (`:52` tag), A.U16.04 (`:52-57`); A.U0.22 (`:63-65`),
  A.U14.16 (`:60-61`), A.U10.26 (`:58-67`), A.U37.06 (3); A.U0.34 (`:68-69`), A.U10.23 (`:68-72`); A.U0.13 and A.U1.19
  (`:73-79`); A.U0.21 (`:81-82`), A.U10.09 (`:89-90`), A.U0.38 (V33, `:90-92`), A.U7.25 (`:92` repoint), A.U36.028
  (`:89-92`)
- **Site**: `BACKLOG.md:19-95`
- **Change**: end state: the section and its heading are gone; nothing in it is one of the four kinds. Per item:
  (a) `:21-35` (four modules numbering inside the reserved range) — removed at U2 by A.U2.23 (done by the renumbering).
  (b) `:36-51` (mypy `Any`) — removed at U36 by A.U36.527 (2): the deferral is overtaken (owner, 2026-09-28) and the
  work is done by A.U8.24/A.U34.11. (c) `:52-57` (FRAM `verify_present()`/`set_write_protected()`) — A.U0.37 tags it at
  U0; A.U16.04 deletes it at U16, the owner tag travelling into SPEC C.3.1's new `FRAM_SPI` bullet. (d) `:58-67` (the
  timeout/cancellation mechanism) — at U0 A.U0.22 rewrites `:63-65` ("for why that case is different)"); A.U14.16's
  `:60-61` wording (U14) applies only while the item exists; A.U10.26 removes the item at U10 as done (the mechanism is
  `asyncio.wait_for_ms` around the one awaitable that can wait). A.U10 lands before U14, so A.U14.16's BACKLOG edit is
  void; its wording lives on in M.DOCS.065's non-blocking goal. A.U37.06 (3) confirms the removal at U37. (e) `:68-72`
  (supervisor error budget) — A.U0.34 re-tags `:68-69` at U0; A.U10.23 removes the item at U10 (resolved). (f) `:73-79`
  ("Rough sequencing") — A.U0.13 deletes clauses (2)-(3) and moves the "every new file joins ruff/mypy" sentence to
  CLAUDE.md (M.DOCS.094) at U0; A.U1.19 rewrites clause (1) as current state at U1; the remaining sentence, a sequencing
  note of none of the four kinds, is deleted at U37 (A.U37.06 (2)). (g) `:81-95` (tier-parity sweep and follow-ons) —
  A.U0.21 re-tags `:81-82` at U0 ("(owner, 2026-09-15; important to apply, no ordering — owner, 2026-09-29: 'It has no
  priority in terms of order now, it's only highly important to be applied.')"); A.U10.09 drops the `_reboot()`
  follow-on at U10; A.U7.25 repoints `:92`'s "fourth item" to the E.6.6 row ID at U7; A.U36.028 deletes the mock-only
  UART fault-catalog clause at U36 (its fact is E.6.6 row `uart-fault-catalog`). The rest is the tier-parity rule, a
  rule with its owner tag: it moves at U37 to the place `tests_hardware/README.md` already states it (A.U0.21's
  `:1188` heading, whose words are the same) and the BACKLOG bullet goes.
- **Resolved**: A.U0.38 (V33) rewrites `:90-92` as "until injection hardware exists"; A.U36.028 deletes the clause
  instead, its wording being the overtaken one — A.U36.028 wins, A.U0.38's V33 BACKLOG text is dropped. A.U14.16's
  BACKLOG clause targets an item A.U10.26 already removed — void (its wording is carried by M.DOCS.065). (g)'s
  remainder: the owner's rule is not open work, so it leaves (A.U37.06 (2)); `tests_hardware/README.md` holds it with the
  same owner tag (agent decision for OR2.c, below).
- **Unit**: U37. Stages: U0 (A.U0.13, A.U0.21, A.U0.22, A.U0.34, A.U0.37), U1 (A.U1.19), U2 (a), U7 (A.U7.25), U10 (d),
  (e), A.U10.09, U16 (c), U36 (b), A.U36.028, U37 (f), (g) remainder, heading.
  A-C2 step order: A.U10.09's part lands in U11, not U10 (it needs A.U11.03, which lands in U11).
- **Depends**: A.U16.04's SPEC C.3.1 bullet, A.U10.26's SPEC F.2 text (SPEC), A.U7.25's E.6.6 table (SPEC)
- **Blast carried by**: SPEC F.2 states the built mechanism (Gaps: SPEC); `tests_hardware/README.md` tier-parity
  heading (HW_BENCH, A.U0.21); citation check for `BACKLOG.md:92`/`:196` "fourth item" citers (A.U7.25, SPEC/HW)
- **Kind**: doc

### M.DOCS.063 The numbered open questions leave; each answer goes to its permanent home
- **From**: A.U0.26, A.U2.12, A.U6.06 (ISL29125 items `:99-141`); A.U1.19, A.U36.544 (item 1 `:142-153`); A.U1.19,
  A.U14.23 (item 3 `:160-166`); A.U0.34, A.U36.035 (item 4 `:167-173`); A.U36.544 (items 5, 6, 9, 12, 29); A.U0.26,
  A.U7.25, A.U14.R01 (c) (item 8 `:192-203`); A.U2.23, A.U19.14 (item 24 `:227-292`); A.U0.34, A.U19.14, A.U33.09
  (item 32 `:302-327`); A.U2.14, A.U14.01, A.U33.09 (item 44 `:329-343`); A.U0.38 (V56, item 2)
- **Site**: `BACKLOG.md:97-343`
- **Change**: end state: the section "Open questions (need owner input or further investigation)" and its heading are
  gone — an open question for the owner lives only in the owner-question list (M.DOCS.067), and bench work only in the
  owed list (M.DOCS.064). Per item: ISL29125 configuration divergence (`:99-127`) and `W12` (`:128-141`) — A.U0.26 tags
  at U0, A.U2.12 renumbers the cited codes at U2, A.U6.06 edits `:140` at U6; both are resolved findings and leave at
  U37. Item 1 — A.U1.19 updates the `_boot.py` path at U1; A.U36.544 repoints its two citers (CLAUDE.md `_boot.py` rule,
  `flash/test_reboot_persistence.py:45`) and deletes it at U36. Item 2 — A.U0.38 (V56) tags it at U0; it leaves at U37,
  its fact living in SPEC L.7. Item 3 — A.U1.19 (1.26 → 1.24.1, new `_boot.py` path) at U1, A.U14.23 at U14; it leaves at
  U37, its facts to SPEC F.1 and the Part F intro (Gaps: SPEC). Item 4 — deleted at U36 by A.U36.035 (its decision is in
  SPEC F.2); A.U0.34's U0 rewrite of `:167-170` stands until then. Items 5, 6, 9, 12, 29 — A.U36.544 (5) repoints every
  citer to the permanent home (F.2, `tests_hardware/README.md` "Known assumptions and open findings", F.1, C.7.1) and
  deletes the stubs at U36. Item 8 (bench-rig capabilities) — A.U0.26 tags at U0, A.U7.25 repoints `:196` at U7,
  A.U14.R01 (c) at U14; it leaves at U37 (the rig capabilities are owed-list rows where they need the bench, M.DOCS.064).
  Item 24 (`ResetErrors` cost) — A.U2.23 renumbers its codes at U2; A.U19.14 moves its design to SPEC C.7 and deletes
  it at U19. Item 32 (bench `ResetErrors` budget) — A.U0.34 rewrites `:325-326` at U0 ("The owner chose the concurrent
  reset (owner, 2026-09-26); the bench budget is set once it lands."); A.U19.14 at U19; A.U33.09 dissolves it into the
  owed row "bench `ResetErrors` budget" at U33. Item 44 (board anomalies) — A.U2.14 renumbers at U2, A.U14.01 at U14;
  A.U33.09 turns it into the F17 owed row at U33.
- **Resolved**: A.U33.09 keeps item 12's stub "only while `test_bus_electrical_timing.py` cites it"; A.U36.544 repoints
  that citer to SPEC F.1 at U36, so the stub goes at U36 — both hold, in order. Item 24's other citers
  (`tests_scripts/test_request_timeout_ceiling.py:88`, `tests_scripts/test_digital_twin_ci_suite_errcount.py:259`,
  `scripts/_digital_twin_ci_suite.py:110`, `digital_twin/README.md:669`) repoint to SPEC C.7 at U19, when A.U19.14 deletes
  the item (Gaps: TSC, SCR, TWIN).
- **Unit**: U37. Stages: U0, U1, U2, U6, U7, U14, U19 (item 24), U33 (items 32, 44), U36 (items 1, 4, 5, 6, 9, 12, 29),
  U37 (ISL items, items 2, 3, 8, heading).
  A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3); A.U2.14's part lands in U3, not U2 (it follows A.U2.14's own change, which lands in U3); A.U14.R01's part lands in U18, not U14 (it follows A.U14.R01's own change, which lands in U18).
- **Depends**: SPEC C.7 (A.U19.14), F.1, F.2, C.7.1, L.7 texts (SPEC); `tests_hardware/README.md` "Known assumptions"
  (A.U36.544, HW_BENCH)
- **Blast carried by**: citation check (A.U0.08) on every `BACKLOG.md #N`/"open question N" citer; the U19 repoints
  (Gaps); `tests_hardware/README.md` citers handled by HW_BENCH
- **Kind**: doc

### M.DOCS.064 "Real-hardware work still owed": one row per measurement, in round order
- **From**: A.U37.05; A.U33.09; A.U33.07; A.U0.01; A.U0.34 (F18, T4, W3, T1); A.U0.38 (`:469-470`); A.U2.23 (`:362-364`,
  `:374-376`, `:384-385`); A.U3.06; A.U16.07 (the T4 script block); A.U26.79 (board-state line); A.U36.001 (procedure
  moves to `tests_hardware/README.md`); A.U36.548 (5); A.U36.532; A.U36.544 (row labels in permanent text); A.SDEP.21 (4),
  A.SDEP.08 (6), A.SDEP.07 (the pin-move row); A.C.10 (phase-C removal of delivered rows; AC3_S section 4); rows added
  by A.U10.07, A.U13.R02, A.U14.12, A.U14.17,
  A.U15.08, A.U15.20, A.U18.43, A.U21.14, A.U21.23, A.U25.01, A.U25.08, A.U25.10, A.U25.12, A.U25.14, A.U26.28, A.U26.35,
  A.U26.36, A.U26.72, A.U26.85, A.U28.02, A.U28.20, A.U31.03, A.U31.05, A.U31.06, A.U35.54; A.C.04 (6) (the manual
  cross-browser check); OR139.a (R6 on the tick-offset image), OR141.a (4)-(5) (the receive-ring rows; the hand-run rows
  kept and dropped; the idle-rate measurement owed), OR143.a (4) (the maximum-size transfer), OR140.a (2) (the gated
  console test); A.U18.43's no-settle row dropped (OR141.a (5)) (A-C review fold)
- **Site**: `BACKLOG.md:345-471`
- **Change**: end state (A.U37.05): one intro sentence — "Everything the dev bench still owes, in round order; how a
  round runs is `tests_hardware/README.md`'s 'How a round runs'; nothing here authorizes anything (CLAUDE.md's go-ahead
  gate). Row labels (T4, S4, …) are kept because commits cite them." — then one bullet per round R0-R7, each naming its
  rows by what they measure, never by an audit ID, with per row: the command or test, the expected outcome, the wear it
  spends and the twin parameter or fidelity row it confirms ("none" where none). Rows the planned tests run
  automatically are one line per round ("the default flash and bench tiers", "the `--allow-persistence-write` run").
  HEAD's labels T4, S4, G6, F17, M1, S3b, R13 + N3 stay; new rows get none. The "UART `wrnno` 11 against a real babbling
  peer" row keeps its owner reason (2026-09-25), with the code renumbered (`wrnno` 54, A.U2.23). The manual
  cross-browser/cross-device spot check (`:834-838` at HEAD) is a row needing the owner (A.C.04 (6)). There is no row
  for the FRAM CS power-on state (a datasheet fact, AC_NOTES 11; A.U13.04 dropped as a measurement). The pin-move row is
  A.SDEP.08 (6)'s text with A.SDEP.07's frozen-website check when freezefs's format moved, written with "(agent,
  <date>)" and no audit ID. Earlier stages, each overwritten by the next: U0 — A.U0.01 relabels "How a sitting runs"
  (D1/D2 owner, the run sheet agent); A.U0.34 deletes F18, W3 and T1 and re-words T4's decision; A.U0.38 rewrites
  `:469-470`; the U0 refresh adds the pin-move row. U2/U3 — the cited codes renumbered. U16 — A.U16.07 handles the T4
  script block (its home is a committed device script). U33 — A.U33.07 turns T4 into the "FRAM command hold on silicon"
  row, deletes the kick-then-reset bullet (`:462-464`) and the two device-script loose ends (`:721-728`); A.U33.09
  folds items 12/32/44 and the soak entry into rows with three slots each, keeping `:465-470` only for H1 (the owner's
  chroot run) and the out-of-scope sentence. U36 — A.U36.001 moves "How a sitting runs" to `tests_hardware/README.md`
  "How a round runs"; A.U36.548 (5) deletes "Folded in from the retired `REAL_HARDWARE_TEST_QUEUE.md` and
  `HARDWARE_TEST_HANDOVER.md` after the 2026-09-24/25 sitting;"; A.U36.532 restates the F.8 pointers; A.U36.544 drops
  queue labels (R2, R4, F1) from the surviving rows. Each listed adding action's row lands in this list (A.U33.09 (2)),
  never elsewhere in BACKLOG. (A-C review fold) The rows follow the owner's 2026-10-01/-05 answers: (a) the G6 row
  (tick rollover) reads "on the `dev` tick-offset test image, whose tick and 32-bit millisecond counts wrap about 15
  minutes after boot: one flash cycle, about two hours of polling with the standard health verdicts, round R6 in
  session 1 after R5 and before R4 (owner, 2026-10-01)" — no 12.4-day window; (b) of the five hand-run rows, three stay
  as one-time measurements — read time per driver over 100 reads, the longest LED ramp, the recovery-step failure
  counts read from the default run — and two leave: the NTP-outage watch of the SGP40 log (HEAD `:362-364`'s first
  "not yet confirmed on silicon" item; the twin's local NTP responder covers it) and the image without the 100 ms
  hotspot settle (the settle stays) (owner, 2026-10-05); (c) a new row "idle poll rate: the event-loop share an idle
  captive-DNS listener's 100 ms poll takes and its first-query latency, on the twin and on the bench — Part N
  `udp.poll_idle_ms`, zero wear" (owner, 2026-10-05: kept, its measurement owed), landing with the idle-rate change
  (U18); (d) new R1-type rows for the UART receive ring, session 1: the interrupts-off sweep without a flash write
  (3 ms, 45 ms, 400 ms and one window past the ring bound, the other UART streaming from its own DREQ-paced transmit
  DMA over the crossover jumper — every in-bound frame intact with the overrun bit clear, the over-bound window read as
  an overrun), a soft reset during traffic, the ring's heap cost and largest free block before and after, one one-time
  run of the old interrupt-driven receive path showing its byte loss (not a standing control), a maximum-size transfer
  over the jumper, and one optional real config write during traffic behind `--allow-persistence-write` (owner,
  2026-10-05) — each landing with its device script or test (U26); (e) the console-starvation row runs only behind
  `--allow-persistence-write` (2 flash writes; owner, 2026-10-02).
- **Resolved**: A.U37.05 rewrites the section from the phase-C inventory and supersedes the earlier stages' wording;
  their row content is its input. A.U33.09 (3) deletes the board-state line once A.U26.79's fixtures exist (U26 lands
  first, so the line goes at U33). `audit/b3/queue_c.md` rows missing from the inventory are reported by A.U37.05's
  executor, not here.
- **Unit**: U37. Stages: U0, U2, U3, U16, U33, U36 as listed; each adding action's own unit for its row; then phase C —
  each round's delta (A.C.10, M.PROC.036 (2)) removes every row it delivered, with every citation of it (G9/R31; e.g.
  G6 after R6, M.PROC.041), and A.C.11 leaves only rows the owner re-queued (gap pass G1).
- **Depends**: A.U36.001 (`tests_hardware/README.md` "How a round runs", HW_BENCH); the phase-C inventory (PROC,
  M.PROC.036-.043, M.PROC.038/.041 as the fold amends them); A.C.10, A.C.11 (the phase-C removals); M.HW_DEV.159, M.HW_DEV.160
  and M.PROC.049 [follows] (the receive-ring rows and their round), M.HW_DEV.046, M.HW_DEV.045 (the maximum-size transfer)
- **Blast carried by**: no test cites these bullets (grep `Real-hardware work` in `tests*/`: none); twin parameters
  named per row (TWIN); CLAUDE.md go-ahead rule (M.DOCS.087) unchanged
- **Kind**: doc

### M.DOCS.065 "Deferred": only owner-deferred goals with their reason, and the C-port item
- **From**: A.U0.39, A.U2.09 (SPI RX `:474-477`; A.U3.04 dropped, OR140.a (7)); A.U0.34, A.U15.42 (`FiltCoeff` `:478-480`); A.U0.38 (V01,
  `arduino/` `:481-483`); A.U0.34, A.U1.19 (`:493`), A.U10.41 (`NTP_Host` `:484-514`); A.U13.06 (`SPIDevice`
  `:614-625`); A.U0.58, A.U36.544 (max-args `:626-637`); A.U0.34, A.U33.03 (buildspec `:638-658`); device-name entry
  (`:659-677`); A.U36.042 (soak trap `:678-683`); A.U0.12 (UART fakes `:684-697` relabel, four UART findings
  `:698-720`); A.U33.07 (`:721-728`); mypy standalone (`:730-739`); A.U0.37, A.SDEP.19 (`:749`), A.U15.02, A.U33.05
  (checkers `:740-777`); A.SDEP.16 (`:787`), A.U33.09 (segfault/soak `:778-812`); A.U36.516 (definitions `:813-833`);
  A.U0.26, A.U36.027 (UART sensor integration `:839-847`); A.U0.37, A.U37.06 (4) (final wiring `:848-859`);
  config duplication (`:860-864`); A.U0.34 (dev quirks `:865-866`); A.U23.07 (JS items `:867-875`); A.U1.19 (dev/build
  env `:876-883`); A.U10.18, A.U36.548 (4) (Wi-Fi locking `:884-889`); A.U13.01 (I2C scratch `:890-908`); A.U15.06
  (SCD30 NVM `:910-913`); A.U35.09 (network fault injection `:914-924`); A.U30.02 (9) (I.2 placement `:925-935`); new
  goals A.U0.14, A.U0.22 with A.U14.16 and A.U14.R01, A.U0.34/A.U36.521 (littlefs resize), A.U21.09 (modlwip watch);
  OR143.a (the parked UART chunking becomes work; the sub-bullet no longer points at an owner question) (A-C review
  fold)
- **Site**: `BACKLOG.md:472-935`
- **Change**: end state: heading "## Deferred goals" (HEAD's "Deferred / explicitly out-of-scope work" — out-of-scope
  facts move to their permanent home as known limitations, A.U37.06 (2)); entries, each with its owner reason:
  (1) "**`arduino/` is out of this project's scope** — the C port stays out of scope, anything there is post-audit only
  (owner, 2026-09-25: 'the C port stays out of scope, anything there is post-audit only'); that covers the UART C
  reconciliation `UART_C_PORT_CHANGELOG.md` tracks and the secret scan (owner, 2026-09-30)." (the C-port item; A.U0.38
  V01 tag). (2) A.U0.14's "**SystemService's settings store grows with device-wide settings** — …" with its module and
  file names as U10's renames leave them (`asy_system_service.py`, `NTPClient`). (3) A.U0.22's "**Adopt a genuine
  non-blocking alternative to every currently-unavoidable blocking call as soon as one reliably exists** (owner,
  2026-07-24, `cc911be`: 'Don't treat the current state as permanently accepted risk'; confirmed by the owner,
  2026-09-29). Today's list, each backstopped by the hardware watchdog after the recovery ladder (SPECIFICATION.md F.2):
  a `machine.I2C` transfer on a wedged bus; a single `machine.SPI` transfer (synchronous, `ports/rp2/machine_spi.c`,
  at the pin). `socket.getaddrinfo()` is not called from `src/`; its one call is `asyncio.start_server()`'s, on the
  numeric bind host. Re-checked at each MicroPython version re-check (CLAUDE.md 'Platform target')." (A.U14.16's
  getaddrinfo wording and A.U14.R01's ladder replace A.U0.22's "is unused" sentence.) (4) "**Resize the rp2 littlefs
  reservation** — only once flash space is actually short (owner, 2026-09-26); trigger: the per-build image report
  (`scripts/build_firmware.py` prints the image against the filesystem boundary). Mechanism at the pin: …" (A.U36.521
  (3)'s text in full, replacing A.U0.34's "mechanism SPEC B.14.3" pointer, B.14.3 being deleted at U36). (5) A.U21.09's
  "modlwip non-blocking send stall — watched upstream: micropython issue 19704, PRs 19705 and 19708 … The
  `modlwip_eagain` build override stays until the pin carries a real fix … (owner, 2026-09-30)". (6) the chroot list
  (M.DOCS.066). Every other HEAD entry leaves, at the unit named: SPI RX overrun — tagged at U0 (A.U0.39), numbers at
  U2 (A.U2.09; A.U3.04's U3 edit dropped with the one-entry rule, A-C review fold), a settled fact moved to SPEC F.5.2
  at U37 (Gaps: SPEC); `FiltCoeff` — A.U0.34 re-words
  at U0, deleted at U15 by A.U15.42; `NTP_Host` — A.U0.34 re-words at U0, A.U1.19 edits `:493` at U1, deleted at U10
  by A.U10.41 (the key renamed `NTPHost` with its bound); `SPIDevice` — deleted at U13 (A.U13.06, SPEC G.2); max-args —
  the max-args ratchet is folded into the chroot list at U36 (A.U0.58's tag, A.U36.544's label removal); buildspec —
  A.U0.34 at U0, deleted at U33 (A.U33.03, SPEC L.6.6); device-name entry — done, removed at U37; soak trap — deleted
  at U36 (A.U36.042, E.7 holds it); UART fakes and four UART findings — A.U0.12 relabels `:698-705` at U0 ("left as they
  are (agent, 2026-09-11)"; the first sub-bullet → (A-C review fold) "the peer-sized `_accept_set()` allocation is to be
  chunked and capped (owner, 2026-10-05)" — no owner question exists for it any more, M.DOCS.067), that sub-bullet leaving
  when the chunking and the cap land (U17, J.8 its home); the rest removed at U37 with homes SPEC C.3.2 (the two
  out-of-contract calls), J.7 (the fakes' facts), J.8 (the peer-sized allocation, chunked and capped) and G.2 (the
  shared codec) — as M.SPEC.050/.137/.138/.111 land them (gap pass G1); loose ends — deleted at U33 (A.U33.07); mypy
  standalone — removed at U37 (A.U27.02's stub repair and the `Timer()` stub fact are SPEC B.15's); checkers — tagged
  at U0 (A.U0.37), actionlint version per A.SDEP.19 (`:749`) at U0, A.U15.02's vulture clause at U15, deleted at U33
  (A.U33.05, SPEC B.16/H.8); segfault/soak — A.SDEP.16 edits `:787` at U0, deleted at U33 (A.U33.09: its silicon rows
  join the owed list), so A.U36.544's `:793` repoint is void; definitions — deleted at U36 (A.U36.516 (8)); UART sensor
  integration — A.U0.26 tags at U0, deleted at U36 (A.U36.027, J.1 known limitation); final wiring — A.U0.37 tags at U0,
  deleted at U37 (A.U37.06 (4), SPEC A.10 rule); config duplication — removed at U37 (stale: each reader's `_VAL_*`
  schema and the generated definitions are the single source, SPEC L; `sensortask-wozi.py` no longer exists); dev
  quirks — deleted at U0 (A.U0.34, C19; CLAUDE.md's `dev` rule holds it); JS items — removed at U23 (A.U23.07, done);
  dev/build env — deleted at U1 (A.U1.19); Wi-Fi locking rename — removed at U10, done by A.U10.18's
  `network_available_locked` rename (M.GEN.005), so A.U36.548 (4)'s U36 re-wording of `:884-889` is void; I2C scratch —
  deleted at U13 (A.U13.01, SPEC G.2); SCD30 NVM — removed at U15 (A.U15.06, a standing rule in SPEC A.4); network fault
  injection — removed at U35 (its open NTP-outage × bus-load recombination is A.U35.09's twin recombination; the rest
  is the bench test's current state); I.2 placement — removed at U30 (A.U30.02 (9) answers it).
- **Resolved**: A.U0.22's getaddrinfo sentence ("is unused") vs A.U14.16 (the one traced call) — A.U14.16's fact wins
  (later, traced at the pin); A.U14.R01 adds the ladder. A.U0.34's littlefs pointer vs A.U36.521 — A.U36.521's full
  text wins (B.14.3 deleted). A.U36.548 (4) vs A.U10.18 — the rename is done at U10, the item leaves then, A.U36.548
  (4) is dropped. A.U36.544's `:793` vs A.U33.09 — deletion at U33 wins. A.U0.38's V33 text: see M.DOCS.062.
  `arduino/` wording follows the one form fixed at the top of this file.
- **Unit**: U37. Stages: U0 (A.U0.12, A.U0.14, A.U0.22, A.U0.26, A.U0.34, A.U0.37, A.U0.38, A.U0.39, A.U0.58, A.SDEP.16,
  A.SDEP.19), U1, U2/U3, U10, U13, U15, U17 (the UART allocation sub-bullet leaves with the chunking and the cap; A-C
  review fold), U21 (modlwip entry), U23, U30, U33, U35, U36 (A.U36.027/.042/.516/.521, the max-args fold), U37.
  A-C2 step order: A.U14.R01's part lands in U18, not U15 (it follows A.U14.R01's own change, which lands in U18).
- **Depends**: SPEC homes named above (SPEC); A.U10.18 (GEN M.GEN.005)
- **Blast carried by**: SPEC F.2 / F.5.2 / G.2 / L.6.6 / B.16 / H.8 / J.1 / A.10 / E.7 texts (SPEC); CLAUDE.md wedged-I2C
  rule (M.DOCS.081) names "BACKLOG deferred goal"; citation check (A.U0.08)
- **Kind**: doc

### M.DOCS.066 The chroot list: one paragraph per landing unit, every build-environment change named
- **From**: A.U36.524 (5) (head); A.U33.04 (the 2026-09-13 to 2026-09-24 paragraph and the history query); A.U0.58
  (`:633-634` tag); A.U5.17; A.U11.10, A.U11.38, A.U11.S03; A.U19.05, A.U19.17; A.U20.14, A.U20.33; A.U21.09, A.U21.16;
  OR139.a (the tick-offset override, U21), OR141.a (5) (the build-date input, U27), OR140.a (1) (the bench AP
  password, U21) (A-C review fold);
  A.U24.72; A.U27.* (per-action "BACKLOG chroot entry" slots); A.U28.38; A.U30.14, A.U30.16; A.U34.08, A.U34.11;
  A.U35.57; A.SDEP.21 (3); A.SDEP.11 (c); A.U36.512 ("variant" → "build flavour" at `:528`, `:531`, `:604`); A.U36.544
  (the "Session 7" label); A.U26.74 (`addopts`); M_TOOL gap 7, M_SCR gap 6, M_WEB gap 8
- **Site**: `BACKLOG.md:515-613` (the "CLAUDE.md's two-target clean-chroot verification …" entry)
- **Change**: end state: head per A.U36.524 (5) — "- **Build-environment changes since the clean-chroot legs were last
  satisfied (2026-09-12: trixie on the bench Pi4, GCC 14.2.0 — lint and typecheck clean, `env --tier generic` end to
  end; noble the same day in the `--arch=arm64` ports form).** The owner's next run (SPECIFICATION.md B.17) covers:"
  (HEAD's "periodic, not a gate … settled" sentences go; the rule is CLAUDE.md's, M.DOCS.106). Then the paragraphs, in
  landing order, each "<date>, <what changed> — <leg it touches>", "comments only, no build impact" where so, and no
  audit ID: the existing dated paragraphs kept (U36 prunes only what a completed owner run covers, A.U33.04 (2));
  A.U33.04's paragraph ("**Not named above, changed 2026-09-13 to 2026-09-24:** …", its text, after `:609`); the
  max-args ratchet item (`:626-637`, A.U0.58's "(agent, 2026-09-12)" tag, A.U36.544's label removal: "Session 7's"
  → "The") folded in as one paragraph; then one paragraph per unit — U0: the dependency refresh (A.SDEP.21 (3)'s text,
  only the parts that moved, naming `@eslint-community/eslint-plugin-eslint-comments` in this refresh line, not under
  U24, per M.WEB.071), A.SDEP.11 (c)'s override line, and the comment edits of A.U0.35/.37/.39/.40 ("comments only, no
  build impact"); U1 (A.U1.21, A.U1.22: comments only); U5 (A.U5.17's "**Lint config only**: `pyproject.toml` `max-args`
  24 → 8, PLR0913 per-file ignores … — no build impact"); U8 (A.U8.14 tags in `versions.toml`, `ci.yml`,
  `setup_toolchain.py`, `micropython_overrides.py`; A.U8.15; A.U8.23 `mypy_path`; A.U8.24 `disallow_any_explicit` and
  its baseline); U9 (A.U9.02: comment); U10 (A.U10.34 toolchain comments; A.U10.37/.38 per-file keys); U11 (A.U11.10's
  `scripts/lint.sh` guard; A.U11.38 T20; A.U11.S03 `pyproject.toml`); U15 (A.U15.43); U18 (A.U18.12 `mypy_path`); U19
  (A.U19.05, A.U19.17 `pyproject.toml`); U20 (A.U20.14 two config entries; A.U20.33); U21 (the installer leg for
  A.U21.01-.08, .10, .12, .15, .17-.30, worded by A.U21.09 and A.U21.16: timeouts and streaming, the lock, the record,
  `sudo --preserve-env`, picotool skip, the command table and sudo probe, the armed bridge, the Node record, leftovers,
  the third Unix binary; "the GCC ≥ 14 leg is the one that decides the mbedtls flag"; `micropython_overrides.py` gains
  `modlwip_eagain` and (A-C review fold) the test-only tick-offset override with its anchor check and the refusal of a
  release build that carries it — "an override a release build never carries; the installer leg builds no test image";
  the bench AP password passed to `nmcli` on its command line, A.U21.19 as the fold amends it); U22 (A.U22.04); U24 (A.U24.72 the `coverage` pin; A.U24.73); U25 (A.U25.40, A.U25.63, the deleted
  concurrency library's two entries); U26 (A.U26.19, A.U26.49, A.U26.54, A.U26.74 `addopts = ["--strict-markers"]`);
  U27 (A.U27.07 override removal, A.U27.12 composite-action body, A.U27.25, A.U27.29 CLI, every other A.U27 action's
  slot, and the new sourced helpers and generated inputs of the lint/typecheck/test legs not named by
  A.U27.08/.10/.33: `scripts/_require_venv.sh`, `scripts/_unix_port.sh`, `scripts/micropypath.toml`,
  `scripts/_port_lock.sh`, `scripts/_summary_block.sh`/`.py`, `scripts/_archive_evidence.py`,
  `scripts/_check_gc_collect_sites.py`, `scripts/build_device_websites.sh`, `scripts/_stage_website.py` — `test.sh` now
  builds every device's site; and "`scripts/run_bench_rollover_test.sh` (new hardware runner, shellcheck-linted, no
  environment change)", M.SCR.074 — (A-C review fold) the runner flashes the tick-offset test image; the build-date input
  and the two-build reproducibility check of `scripts/build_firmware.py` (M.SCR.066 as the fold amends it): "a real
  build stamps its UTC build time; the check builds twice with one fixed date — no environment change"; the stub
  version check against the MicroPython ref (A.U27.02, already listed)); U28 (A.U28.38's paragraph); U30 (A.U30.14, A.U30.16: `scripts/` checker changes); U34
  (A.U34.08's "`build_frozen_html.sh`: comment only; new L0 freezefs hash test — no leg affected"; A.U34.11); U35
  (A.U35.57's paragraph); U36 (A.U36.512, A.U36.544: comments only). "variant" in the Unix-port sense at `:528`, `:531`,
  `:604` → "build flavour" (A.U36.512). At U37 (A.U37.04 (3)) the history query of A.U33.04 (2) is re-run from `c82149f`
  and any file it lists that no paragraph names is added under its leg.
- **Resolved**: M.SCR.074's new runner is a `scripts/` change the lint leg covers, so the U27 paragraph names it (GAPS_G4
  hand-off 1 (c), gap pass G1). A.U0.58 is not void: A.U5.17 keeps `:626-630` until the owner's run covers them, so the item survives
  and is relabelled (U36). A.U24.48's own line no longer names the eslint-comments plugin (moved into the U0 refresh,
  M.WEB.071, M_WEB gap 8). M_TOOL gap 7's per-unit list and M_SCR gap 6's helper list are carried as written.
- **Unit**: U37 (close check). Stages: each listed unit appends its own paragraph at its landing commit; U33 (A.U33.04
  paragraph); U36 (head per A.U36.524, labels, "build flavour").
- **Depends**: A.U36.524 (SPEC B.17 exists, SPEC); M.PROC.008 (the refresh record the U0 line summarises)
- **Blast carried by**: CLAUDE.md "Build-environment verification" and PR-workflow bullet (M.DOCS.106, M.DOCS.107) point here; no
  test reads the list
- **Kind**: doc

### M.DOCS.067 The owner-question list: one dated entry per question, nothing parked elsewhere
- **From**: A.U0.12 (the list; its entry 1 dropped, OR143.a); A.U17.03 (both allocation sites named — void with entry 1);
  A.U30.02 (I.2's UART row cited the entry — no longer, M.SPEC.126); A.U36.548 (3) (the streaming GET item); A.SDEP.21
  (5), A.SDEP.08 (1), M.PROC.008 (4)-(5) (hold-backs and parked owner-decided behaviour); A.U25.64 (the grkizi Run 5c
  record); A.U27.17, A.U35.27 (Run 11 retry, conditional); A.U36.544 (allow-list entries needing an owner decision);
  M_PROC gap 3(d); OR143/OR143.a (owner, 2026-10-05: the parked UART chunking becomes work and its question is dropped)
  (A-C review fold)
- **Site**: `BACKLOG.md` new final section `## Owner questions` (after "Deferred", `:472-`)
- **Change**: end state: "## Owner questions\n\nQuestions for the project owner, each dated, in the owner's format;
  nothing else in the repo parks a question." Entries are numbered in the order they are entered, from 1, and numbers
  are never reused (M.DOCS.061's rule). (A-C review fold) The planned entry "Chunk peer-sized UART allocations?" is not
  written: the owner made the chunking and a receive cap work (owner, 2026-10-05; SPECIFICATION.md J.8, M.SPEC.138), so
  the U0 list holds only its heading and sentence until a first entry is entered. Entries: "**<n>. A streaming GET
  answer for `UARTComm`'s responder?** (entered 2026-09-30, agent) — a pull callback like SET's; needed only once a
  responder answers more than one buffer (the only responder, `UARTLinkDriver`, answers a banner or the last echo). (a)
  build it now; (b) defer until a responder needs it." (U36). Conditional entries, each written only when its condition
  occurs, dated, with the decision taken on the owner's behalf stated: a held-back dependency (A.SDEP.21 (5), A.SDEP.08
  (1) "stubs not yet published", M.PROC.008 (4): the dependency, the failing release, the reason, "re-checked at the
  next refresh"); a refresh change parked because it would alter an owner-decided behaviour (M.PROC.008 (5)); the
  grkizi Run 5c relaunch SIGSEGV "not reproduced" record (A.U25.64, U25: count, HEAD, binary); Run 11's retry question
  if the planted-leak calibration finds no separating window (A.U27.17, A.U35.27, U35); any citation allow-list entry
  that cannot be fixed without an owner decision (A.U36.544, U36).
- **Resolved**: A.U36.548 (3) adds the streaming-GET item to BACKLOG as an agent-deferred goal; the four kinds admit
  only owner-deferred goals, so it is entered as an owner question with the agent's recommendation (agent decision for
  OR2.c, below); its names follow the U10 class renames (`UARTComm`, `UARTLinkDriver`). OR143.a supersedes OR69.a (7)'s
  deferral: entry 1 (A.U0.12's text, A.U17.03's second allocation site) is dropped, and the streaming-GET entry takes
  the next free number when it is entered (A-C review fold).
- **Unit**: U0 (the list, heading and sentence only). Stages: U25, U35, U36 (the streaming-GET entry and allow-list
  entries) and U0/U37 (refresh hold-backs) as their conditions occur.
- **Depends**: —
- **Blast carried by**: SPEC J.8 and I.2's UART row no longer cite an owner question (M.SPEC.138, M.SPEC.126, as the
  fold amends them); BACKLOG's UART-findings sub-bullet (M.DOCS.065); CLAUDE.md decision-records rule (4) (M.DOCS.091);
  `UART_C_PORT_CHANGELOG.md` rows for the chunking and the cap (M.DOCS.022 A15, M.DOCS.024 B65-B69)
- **Kind**: doc

## CLAUDE.md

CLAUDE.md holds session rules and working agreements, each with one short reason and a pointer; facts, incident
accounts, measurements and recipes live in SPECIFICATION.md or a README (A.U36.546, owner, 2026-09-26). Changes are
merged per bullet; a bullet edited by several actions gets one block naming every stage. Line numbers are HEAD's.

### M.DOCS.068 Intro and "Datasheets": the submodule, the cite-the-page rule
- **From**: A.U36.019 (2); A.U36.545 (2); M.PROC.018 (owner push-access step, AC_NOTES 37; satisfied by OR144.a); agent (intro clause)
- **Site**: `CLAUDE.md:3-6`, `:8-13`
- **Change**: `:10-12` end state: "Short version: `datasheets/` is the private submodule `hundertvolt/datasheets` (`git
  submodule update --init datasheets`; SPECIFICATION.md A.6). Read the datasheet in `datasheets/` first for any
  hardware-interaction claim and cite the page; training memory is never a source; a missing one is named and work
  continues from the next-best primary source, marked open until the owner supplies it (SPECIFICATION.md A.6)." `:3-6`
  "(BACKLOG.md's open-questions/deferred-work list included)" → "(BACKLOG.md included)" — BACKLOG's end-state content
  (M.DOCS.061) is not an open-questions/deferred-work list.
- **Resolved**: A.U36.545 (2) prefixes A.U36.019's text — both kept, in that order. The submodule sentence is written
  only once the move happened (M.PROC.018, the owner's push-access step; M.DOCS.014 the same condition) — that step is
  satisfied: the owner gave standing push permission (owner, 2026-10-05; OR144.a), so the move and this text land (A-C
  review fold, lead ruling).
- **Unit**: U36 (after A.U28.35's move, U28)
- **Depends**: A.U28.35 (TOOL), M.PROC.018
- **Blast carried by**: SPEC A.6 (A.U36.019 (1), A.U36.545 (1), SPEC); README install recipe (M.DOCS.047)
- **Kind**: doc

### M.DOCS.069 "Platform target": the pinned version named, three practices
- **From**: A.U1.12 (`:17`); A.SDEP.21 (1) (`:17`); A.SDEP.22 (`:26`); A.SDEP.17 (`:17-20` re-read)
- **Site**: `CLAUDE.md:15-27`
- **Change**: `:17` "MicroPython 1.26/RP2040 specifics, what the 1.29 pin changed (Part F.5)" → "MicroPython <pin>/RP2040
  specifics (the legacy units run 1.24.1), what the pin's audit found (Part F.5)" with `<pin>` the current
  `toolchain/versions.toml` ref (A.SDEP.21 (1): named at each refresh). `:26` "Two standing AI-session practices" →
  "Three standing AI-session practices". The facts list `:16-22` keeps its items, each re-read against the refreshed pin
  (A.SDEP.17); an item that no longer holds there is corrected in place, Part F being the fact's home.
- **Resolved**: A.U1.12 writes "1.29.0" at U1; A.SDEP.21 (U0, earlier) renames the pin — the U1 text takes the
  refreshed pin's value, never "1.29.0" if U0 moved it.
- **Unit**: U0 (refresh), U1 (legacy version clause); U0 again at the U37 re-check (M.PROC.031)
- **Depends**: M.PROC.008 (e)
- **Blast carried by**: SPEC F.5 heading (A.SDEP.21 (2), SPEC)
- **Kind**: doc

### M.DOCS.070 The version re-check practice points to Part F; "Last run" re-dated
- **From**: A.U0.32 (`:32`); A.U36.023 (2); A.SDEP.21 (1) (`:42-45`); M.PROC.031 (U37 re-date, M_PROC gap 3(a));
  A.U26.65 (Workarounds table, M_PROC gap 3(b)); A.U21.09 (the `modlwip_eagain` clause); A.SDEP.19 (W-checks)
- **Site**: `CLAUDE.md:32-49`
- **Change**: end state: head (A.U0.32) "**Whenever the owner moves the pinned MicroPython version (owner, 2026-09-26:
  the pin moves only on the owner's call), and periodically otherwise, re-check every MicroPython-facing code
  construct …**" — the first sentence `:31-35` kept to "missing out on"; `:35-47` replaced (A.U36.023 (2)) by "The full
  checklist — Part F facts and citations, override anchors (B.14), the heap-map parser, the stubs, the harness
  workarounds in `tests_hardware/README.md`'s Workarounds table, ruled-out items — is SPECIFICATION.md Part F's opening
  paragraph; its last run is recorded in SPECIFICATION.md F.5. For the `modlwip_eagain` override it asks whether the
  new pin carries a real upstream fix for micropython issue 19704 (PRs 19705/19708) — if so the override is removed,
  not re-anchored (owner, 2026-09-30)." then `:42-45` as A.SDEP.21 (1) writes it: "**Last run: <old> → <new>, <date>;
  results in SPECIFICATION.md Part F.5** — including what it found (<one clause per finding>) and what it ruled out
  (<one clause>)", or "**Last run: <date>, no newer stable MicroPython release than <pin>**". At U37 M.PROC.031 re-dates
  this line even when nothing moved.
- **Resolved**: A.U36.023 (2) deletes `:35-47`, which holds the "Last run" sentence; A.SDEP.21 keeps the dated record "in
  one place" — A.U36.023 itself says the dated record stays A.SDEP.21's, so the "Last run" line survives after the
  pointer sentence. A.U21.09's modlwip clause was written into the anchor-check sentence A.U36.023 deletes; it moves
  into the pointer sentence (owner's rule kept, its sentence gone). A.U26.65's "U36 carries the CLAUDE.md line" is the
  Workarounds item in the checklist sentence (M_PROC gap 3(b)). The getaddrinfo example goes (A.U36.023: nothing in
  `src/` calls it).
- **Unit**: U36. Stages: U0 (A.U0.32 head; A.SDEP.21 "Last run" for the U0 refresh), U21 (A.U21.09 clause into the HEAD
  sentence), U36 (pointer sentence), U37 (M.PROC.031 re-date).
- **Depends**: SPEC Part F intro checklist (A.U36.023 (1), SPEC) names the Workarounds table too (Gaps: SPEC);
  `tests_hardware/README.md` Workarounds table (A.U26.65, HW_BENCH)
- **Blast carried by**: SPEC F.5/F.9 (A.SDEP.21 (2), M.SPEC.099/.109; A.SDEP.21's "F.5.10" lands as F.9); M.PROC.031 (PROC)
- **Kind**: rule, doc

### M.DOCS.071 A third practice: every external dependency is refreshed as one step
- **From**: A.SDEP.22; M_SPEC gap 1 (the section is F.9, M.SPEC.109; gap pass G1); A.U19.19 (A.5 pointer; M.SPEC.018's
  Blast, gap pass G1)
- **Site**: `CLAUDE.md` after `:49`
- **Change**: new bullet, A.SDEP.22's text verbatim: "- **Every external dependency is refreshed as one step, not only
  MicroPython** (owner, 2026-09-30: "Check all external dependencies for updates - both modules, repos and tooling,
  just everything."): the vendored `ext/` code (only as an unmodified upstream tag or commit), the stub packages, every
  Python and npm tool with its lock, Node, the GitHub Actions pins and every other fetched source. Read each update's
  changelog and the diff of the parts this repo uses; fix what breaks with no regression at every level and both GC
  stages; take the fixes the project profits from; and re-check every standing workaround in SPECIFICATION.md Part
  F.9, removing it for the clean form where upstream fixed it. Pins stay pinned; the bullet above runs whenever the
  MicroPython ref moves." — and, at U36, after "only as an unmodified upstream tag or commit": "(a Microdot move runs
  SPECIFICATION.md A.5's re-check list)" (A.U19.19's Blast: the standing practice points to A.5's list).
- **Resolved**: A.SDEP.22 cites "Part F.5.10"; the section lands as F.9 (M.SPEC.003/.109: standing facts are filed by
  topic, not under F.5's per-pin record), so the bullet cites F.9 (M_SPEC gap 1; gap pass G1).
- **Unit**: U0 (with the refresh record, M.PROC.008); stage U36 (the A.5 pointer, once A.U19.19's list exists, U19)
- **Depends**: SPEC F.9 (A.SDEP.21 (2), M.SPEC.109; created at U0)
- **Blast carried by**: —
- **Kind**: rule

### M.DOCS.072 The retired-directory bullet becomes the owner-authorised exception rule
- **From**: A.U36.540 (1); A.U1.12 (`:66-67` paths, U1 stage)
- **Site**: `CLAUDE.md:53-67`
- **Change**: end state, A.U36.540 (1)'s text: "- **An owner-authorised exception to a hands-off rule** (owner, 2026-07-30,
  `1e4cdfe`): for a severity-justified fix the owner can authorise a scoped exception to a "don't touch" rule in this
  file — the precedent is the `ConfigManager`/`LockedValue` wrong-module-import fix, which would have crash-looped every
  deployed unit's boot. It needs the owner's explicit authorization each time, scoped narrowly to the specific fix,
  never a general license. It never reaches the legacy tree, whose later rule admits no work of any kind (owner,
  2026-09-11)." The `improved-quality/` history goes; the generated-entry fact is SPEC L.2's.
- **Resolved**: A.U1.12 repaths `:66-67` at U1; A.U36.540 replaces the bullet at U36.
- **Unit**: U36. Stage U1.
- **Depends**: —
- **Blast carried by**: legacy-path check (A.U1.09, `test_legacy_paths.py`, TSC) between U1 and U36
- **Kind**: rule

### M.DOCS.073 The `src/` rule and the bird's-eye scan cite Part K, Part 0 and Part G
- **From**: A.U36.542 (2)-(3); A.U0.38 (V68, `:88-91`); A.U36.540 (7)
- **Site**: `CLAUDE.md:68-91`
- **Change**: `:68-77` → "- **`src/` holds reviewed and tested code** — code lands there by walking SPECIFICATION.md Part
  K's ordered checklist (its reference Parts: C for a driver's shape, D for the quality bar, G for shared primitives).
  `src/` files are ordinary, freely editable code." `:78-87` → "- **Whenever a file is added to `src/`, run a bird's-eye
  scan over the whole tree it joins**, not only the new file: against SPECIFICATION.md Part 0 (principles and 0.4's
  conventions catalog) and Part G's shared-primitive catalog, re-running G.3's shape grep in the same pass." followed by
  `:88-91` → "A consistency discrepancy (naming, ordering, signatures, uniform behaviour) is fixed directly and logged
  (owner, 2026-09-25: 'Change, don't flag, if not according.'); a formula or behaviour discrepancy follows D.1".
- **Resolved**: A.U0.38's V68 text ends "follows Part D.1's flag-first path"; A.U36.540 (7) amends it to "follows D.1"
  (D.1 is no longer flag-first) — applied.
- **Unit**: U36. Stage U0 (A.U0.38's V68 sentence, with "Part D.1's flag-first path" until U36).
- **Depends**: SPEC Part 0, 0.4, Part K (A.U36.541/.542/.543, SPEC)
- **Blast carried by**: SPEC D.1 (A.U36.540 (4), SPEC)
- **Kind**: rule

### M.DOCS.074 The `_boot.py` rule: legacy path, 1.24.1, the trace stated in place
- **From**: A.U1.11; A.U36.544 (5) (item 1)
- **Site**: `CLAUDE.md:92-101`
- **Change**: `modules/_boot.py` → `legacy/firmware/modules/_boot.py`; `:97-99` → "while the legacy units run 1.24.1, whose
  import machinery was never separately verified"; added "The dev bench never flashes the legacy build, so any such test
  runs on one of the owner's own legacy units, as the owner's operation (owner, 2026-09-26)."; `:96` "(BACKLOG.md #1 has
  the trace)" → "(traced through `tools/mpy-tool.py`'s frozen-name generation, `py/frozenmod.c`'s exact-match lookup and
  `py/builtinimport.c`'s `stat_module()`/`process_import_at_level()`)". Meaning otherwise unchanged.
- **Resolved**: —
- **Unit**: U36. Stage U1 (A.U1.11).
- **Depends**: M.DOCS.063 (item 1 deleted after this repoint)
- **Blast carried by**: `flash/test_reboot_persistence.py:45` citer (A.U36.544, HW_DEV)
- **Kind**: rule

### M.DOCS.075 The Microdot vendoring rule: legacy commit named, upstream stubs included
- **From**: A.U1.12 (`:102-104`, `:110-111`); A.U36.030; A.U36.544 (1); A.SDEP.06; A.U0.37 (`:115` tag); A.U8.23 and
  AC_NOTES 41 (stubs); A.U36.548 (4) (`:114-115`)
- **Site**: `CLAUDE.md:102-118`
- **Change**: end state: "- **`legacy/firmware/python/CommonDrivers/microdot.py` is vendored third-party code.** Part of
  the reference-only legacy tree: never edited (legacy rule below). It is upstream commit `482ab6d` (#251),
  byte-identical to it: an untagged snapshot four commits after `v2.0.6`, before `v2.0.7` — unmodified, just old (agent,
  2026-09-30, compared against the upstream repository). **`ext/microdot.py` is the same policy applied to the refactor
  target**: a plain, unmodified vendored copy of upstream Microdot (pinned to the upstream tag
  `THIRD_PARTY_LICENSES.md` records; `tests_scripts/test_vendored_microdot.py` checks its hash), with upstream's own
  stubs vendored byte-identical at `ext/typings/microdot/` under the same policy (owner, 2026-10-01). No edits, no
  restyling, ever (owner, 2026-09-25) — any behavior change needed is handled by wrapping/calling it from our own code
  (see "Microdot / REST layer" below), never by touching these files. `src/` and `ext/` are copied flat …" (the rest of
  `:116-118` unchanged). Gone: "Don't restyle … routine editing" (A.U1.12), "an earlier note here claimed …" and the
  "~441 lines" count (A.U36.030), the reflash-campaign sentence (A.U36.544 (1)), "replacing the
  `improved-quality/microdot.py` copy …" (A.U36.548 (4)).
- **Resolved**: A.U1.12 rewrites `:110-111` to a reflash-runbook sentence (U1); A.U36.544 (1) deletes it at U36, the
  legacy tree getting no work and the runbook being README's — deletion wins at U36. A.SDEP.06 re-measures the
  "~441 lines" at U0; A.U36.030 deletes the count — the re-measure is dropped and the U0 stage deletes the count clause
  with the tag move (a dated count, G9/R11), so no stale figure stands between U0 and U36. AC_NOTES 41 (OR131, firm):
  A.U8.23's "its upstream stub is vendored at `ext/typings/microdot/`, same policy" written with the owner tag.
- **Unit**: U36. Stages: U0 (A.SDEP.06 tag; count clause out; A.U0.37 tag), U1 (paths), U8 (stub sentence, A.U8.23 — the
  stub arrives in U0's re-vendor per OR131), U36.
- **Depends**: A.U19.18 (`test_vendored_microdot.py`, TSC) before the U36 text cites it
- **Blast carried by**: THIRD_PARTY Microdot entry (M.DOCS.002); SPEC A.1/A.5 (SPEC)
- **Kind**: rule

### M.DOCS.076 The UART contract bullet: post-audit wording, owner tags, the owner holds every unit
- **From**: A.U0.38 (V01, `:123-125`); A.U17.08 and M.DOCS.015/.018 (changelog lifecycle and scope); A.U0.23 (`:128-129`,
  `:141`, `:144-146`); A.U0.32 (`:138-140`); A.U36.025 (`:131-137`); A.U10.37/.38 names; OR140.a (18) (the WoZi clause
  goes), OR141.a (4) (the DMA receive ring) (A-C review fold)
- **Site**: `CLAUDE.md:119-155`
- **Change**: `:122-125` → "**every change made to it gets an entry in `UART_C_PORT_CHANGELOG.md`** (kept until the
  post-audit C reconciliation, and deleted there; its source is in the repo since 2026-09-13,
  `arduino/libraries/Async_UART_Comm/`, and reconciling it is post-audit only (owner, 2026-09-25: 'the C port stays
  out of scope, anything there is post-audit only')), classified as protocol-level ("must be mirrored in C") or
  Python-internal ("no C impact"); the protocol module and the layers below it where a change could reach the wire are
  in scope, and a changed `const()` wire constant or recovery timing is Class A by definition"; `:128-129` per A.U0.23
  ("… a coordinated flag-day, which the Python side may lead (owner, 2026-09-11, `6a2d43e`, paraphrase); until the C
  reconciliation the wire format is not touched (owner, 2026-09-25: 'the UART wire format is not touched')"); `:131-137` per
  A.U36.025 ("**It is, however, prototypical — exactly like this repo's legacy Python — and the owner holds every
  unit** (owner, 2026-09-11; 2026-09-26: 'I build all sensors and still own all of them') … so until then the hardware
  tests prove Python-to-Python interoperation over the bench crossover jumper only."); `:138-140` per A.U0.32 ("— no
  version or capability negotiation, now or at the C reconciliation (owner, 2026-09-11; reconciliation clause confirmed
  2026-09-26)"); `:141` gains "(owner, 2026-08-20, `b6cb852`; 2026-09-11, `32b136f`)"; `:144-146` per A.U0.23 without
  its WoZi clause (A-C review fold) ("**`dev` carries two instances across its permanent crossover jumper** (owner,
  2026-09-11, UART promotion 'Target variant. dev, two instances') — the bench rig's, one of `dev`'s contained
  exceptions; another device carries a link only where its TOML declares one" — "**and `wozi` carries none** — wozi is
  never flashed, so the peripheral would be untestable there (agent, 2026-09-11)" goes: no device but `dev` has a role
  of its own, owner, 2026-10-02); and (A-C review fold) after the no-block clause, the receive path's end state is named
  where this bullet states the module's shape: "each link receives through a DMA ring, so a flash write holding
  interrupts off loses no frame (owner, 2026-10-05; SPECIFICATION.md F.8.2)"; `:147-155` class and module names per the U10 renames (`UARTLinkDriver` in
  `asy_uart_link_driver.py`, `UARTComm`), and "the protocol's own wire constants … in `src/asy_uart_comm.py` as
  `const()` values; a change to any of them is Class A by definition" stays (now also stated in the entry clause above
  — the duplicate in `:147-149` is cut to the location clause).
- **Resolved**: A.U0.38's V01 sentence and A.U17.08's lifecycle wording both land in the parenthesis — combined (the
  file's header carries the same words, M.DOCS.015). The duplicated Class-A clause appears once (agent, consistency).
  A.U0.23's "during this audit" → "until the C reconciliation": after phase D deletes `audit/`, "this audit" names
  nothing (G9/R12; AC3_O O-22).
- **Unit**: U36. Stages: U0 (A.U0.23, A.U0.32, A.U0.38), U10 (names), U13 (the DMA-ring clause, with the receive path),
  U17 (lifecycle and scope clause), U36 (A.U36.025; the WoZi clause of `:144-146` removed).
- **Depends**: M.DOCS.015, M.DOCS.016, M.DOCS.017, M.DOCS.018; M.SPEC.108 (F.8.2's receive-path paragraph, U13)
- **Blast carried by**: changelog header/intro/deployment status (M.DOCS.015-.017); SPEC J.1 (A.U17.08, A.U0.38, SPEC)
- **Kind**: rule

### M.DOCS.077 The `dev` bullet: `dev` meets every device's bar
- **From**: A.U0.32 (`:156-158`); A.U0.34 (C19, the BACKLOG twin, M.DOCS.065)
- **Site**: `CLAUDE.md:156-158`
- **Change**: → "- **`dev` meets every device's bar**: its generated config is held to the same standard as every
  device's; a quirk is a defect (owner, 2026-09-26)."
- **Resolved**: —
- **Unit**: U0
- **Depends**: —
- **Blast carried by**: BACKLOG dev-quirks bullet deleted the same unit (M.DOCS.065)
- **Kind**: rule

### M.DOCS.078 The `dev`-exception rule replaces the WoZi rule
- **From**: A.U0.23 (`:159-160`); A.U0.32 (`:166-169`); A.U36.512 (4) (`:159`); OR78.a (2)-(3) (AC3_O O-28); OR140.a (18)
  (owner, 2026-10-02: no build has anything special apart from `dev`'s contained exceptions; the WoZi-specific wording
  of the promotion is removed) (A-C review fold)
- **Site**: `CLAUDE.md:159-169`
- **Change**: the whole bullet `:159-169` → "- **Every device but `dev` is built and tested alike; `dev` is the bench rig
  and the one contained exception** (owner, 2026-10-02: 'There is nothing special for any of the builds (apart from
  some well contained exceptions for dev, which is somewhat special)'). Only the `dev` board is flashed and
  bench-tested by a session (owner, 2026-09-03, `a19691c`); every device's correctness rests on L0-L2, and a bench proof
  of a shared mechanism on `dev`'s own image holds for every device. A session never flashes another device's image
  onto the bench board: its pins do not match the bench wiring, so such a run tests nothing (owner, 2026-09-03,
  `5730e72`, paraphrase) and must not be repeated." The HEAD text's "WoZi is the exemplary/base variant … never
  physically flashed", its `scripts/build_firmware.py wozi` example and "dev is different hardware, wozi cannot run on it
  and never will" go.
- **Resolved**: OR78.a (2)-(3) (2026-09-28, later than the 2026-09-03 rule) withdrew wozi's default and golden-reference
  role; OR140.a (18) (2026-10-02) goes further — no WoZi-specific rule remains: the facts that stay are `dev`'s (the one
  flashed board) and the general invalid-test rule (A-C review fold; the earlier "`wozi` is never physically flashed or
  bench-tested" sentence of A.U0.23 is replaced). The replaced span runs to `:169` so no fragment of the old bullet
  dangles.
- **Unit**: U36 (the docs pass that removes the WoZi wording). Stage U0: A.U0.23/A.U0.32's tags on HEAD's text
  (`:159-160`, `:166-169`), which U36 replaces whole, carrying the two owner tags of 2026-09-03 into the new text.
- **Depends**: —
- **Blast carried by**: SPEC term table (A.U36.512 (1), SPEC); SPEC A.3, B.11, E.6.6, L.1 (M.SPEC.007, M.SPEC.035,
  M.SPEC.083, M.SPEC.144: their pointers name "CLAUDE.md's `dev` rule"); README flashing rule and Devices table
  (M.DOCS.048, M.DOCS.045); `tests_hardware/README.md`'s WoZi wording → M.HW_BENCH.104, M.HW_BENCH.125
- **Kind**: rule

### M.DOCS.079 The legacy rule names `legacy/` and what it may be used for
- **From**: A.U1.10
- **Site**: `CLAUDE.md:170-183`
- **Change**: A.U1.10's text: the path list → "`legacy/firmware/` (the legacy units' firmware tree:
  `legacy/firmware/python/`, `legacy/firmware/modules/`, `legacy/firmware/html_raw/`, the four
  `legacy/firmware/build-*.sh`, `legacy/firmware/update_and_install.txt`) and `legacy/dev_drivers/` (the dev unit's
  2026-08-27 snapshot), described in `legacy/README.md`"; actor tag "(owner, 2026-09-11)"; "to check what the deployed
  system actually does" → "what the owner's legacy units (MicroPython 1.24.1) actually do"; added "The one change it
  ever got is its byte-identical move into `legacy/` (owner, 2026-09-25). It may run in a scratch directory as a
  published-value reference, nothing committed (owner, 2026-09-26)." and "`tests_scripts/test_legacy_paths.py` fails on
  any current file naming a pre-move path."; `:176` path; `:183` → "never test the legacy code (`legacy/`)".
- **Resolved**: —
- **Unit**: U1
- **Depends**: M.PROC.014 (the move), A.U1.09 (the check, TSC)
- **Blast carried by**: `legacy/README.md` (M.PROC.015)
- **Kind**: rule

### M.DOCS.080 The credentials rule names every place of the hotspot default
- **From**: A.U1.12 (`:187`); A.U0.32 (`:188-190`); A.U29.03 (1); A.U36.548 (4) (`:190-192`)
- **Site**: `CLAUDE.md:184-192`
- **Change**: end state: first sentence unchanged; the second → A.U29.03's text: "**The one real credential in this
  repo** is the hotspot fallback password: the default of `HotspotPW` in `src/asy_wifi_service.py` and of every
  `devices/*.toml`'s `hotspot_password`, copied into the reference-only legacy tree and into tests pinned to that
  default; accepted permanently as a known limitation under the trusted-home-LAN threat model (owner, 2026-09-26; first
  accepted 'for now', owner 2026-07-13, `b64857d`). SPECIFICATION.md A.11 …" (as A.U29.03 continues); the
  `improved-quality/async_connect.py` sentence goes (A.U36.548 (4)).
- **Resolved**: A.U1.12 (U1 path) and A.U0.32 (U0 tag) are stages A.U29.03 rewrites from, as it states.
- **Unit**: U36. Stages: U0, U1, U29.
- **Depends**: SPEC A.11 (A.U29.03, SPEC)
- **Blast carried by**: `pyproject.toml` credential comment (A.U28.29, TOOL); `asy_wifi_service.py:50-52` (SRC_NET)
- **Kind**: rule

### M.DOCS.081 The wedged-bus rule states the recovery ladder
- **From**: A.U0.22 (`:193-196`); A.U14.R01 (4); A.U36.549
- **Site**: `CLAUDE.md:193-196`
- **Change**: end state, A.U14.R01 (4)'s text: "- **A wedged I2C bus or sensor recovers through the recovery ladder,
  smallest blast radius first — retry, the participant's own reset, bus clear and controller re-init, task restart,
  reboot, the hardware watchdog last** (owner, 2026-09-30); a transfer in flight cannot be interrupted, so the ladder
  acts after it returns an error, and a call that never returns is the watchdog's — the current state, until a genuine
  non-blocking alternative reliably exists (owner, 2026-07-24; BACKLOG deferred goal). Full ladder and which waits can
  be timeout-wrapped: SPECIFICATION.md Part F.2."
- **Resolved**: A.U0.22's U0 rewrite ("the watchdog is the backstop … the current state, backstopped, until …") is the
  stage A.U14.R01 builds on; A.U36.549's "settled, don't re-propose" case is already gone after U0 — no further edit.
- **Unit**: U14. Stage U0.
  A-C2 step order: A.U14.R01's part lands in U18, not U14 (it needs A.U18.R01, which lands in U18).
- **Depends**: SPEC F.2 (A.U14.R01 (1)-(3), SPEC); BACKLOG non-blocking goal (M.DOCS.065)
- **Blast carried by**: —
- **Kind**: rule

### M.DOCS.082 The Wi-Fi backstop names both write paths; a new limited-endurance write rule
- **From**: A.U0.32 (`:197-203`); A.U36.034 (1)-(2); A.U36.544 (5) (item 6 pointer); OR136.a (1)-(3) (an absent config
  file is written once with its defaults), OR138.a (1)-(2) (a damaged file is listed in `ConfigFaults`; the reset
  deletes it unread) (A-C review fold)
- **Site**: `CLAUDE.md:197-203`, new bullet after it
- **Change**: head (A.U0.32) "— a power cycle/`hard_reset()` stays the recovery, because the owner judged an independent
  reachability probe not worth its complexity (owner, 2026-09-04, `655e4f9`, paraphrase; confirmed 2026-09-26).**";
  the "Confirmed inherently safe" sentence → A.U36.034 (1)'s sentence with its write list amended (A-C review fold):
  "Safe: the flash is written only on an API action — an accepted, value-changing PUT or the `SystemCmd`
  `"resetconfig"` — or once per boot when a config file is absent or needs repair (next rule), and a deferred write
  resolves long before a sustained outage triggers a power cycle; the one residual window — a power loss between a
  PUT's response and its deferred write — loses that change silently and never corrupts (owner, 2026-09-26;
  SPECIFICATION.md F.2)."; the foreclosure sentence and "(BACKLOG.md keeps only a closed pointer, open question 6)" go.
  New bullet: A.U36.034 (2)'s text with its flash-filesystem sentences amended (A-C review fold): "- **The firmware
  writes a limited-endurance store only on a user or API action, or once to create or repair a config file** (owner,
  2026-09-26: 'never write without user / api interaction as a standing rule'). The flash filesystem is written only
  through `ConfigManager`: on an accepted PUT that changed a value; at boot, once with the schema defaults when a config
  file is genuinely absent — after a fresh flash, a filesystem erase or "Reset to defaults" (owner, 2026-10-01: 'if the
  file is genuinely missing, it shall be written once with defaults') — or in at most one repair per boot of an
  existing, readable file with a bad, missing or unknown key (owner, 2026-09-26) or that is damaged — unparseable or
  not a JSON object (owner, 2026-10-01); or by the `SystemCmd`
  `"resetconfig"`, which deletes every config file without reading it (owner, 2026-09-30; unread, owner, 2026-10-01).
  The SCD30's NVM is written only on an accepted PUT that changed a value or by a command the PUT names (`AmbPres` and
  `ForceCalRef` always send; `ContMeas` false stops measurement, whose status the chip keeps in NVM). A file that cannot
  be read is never overwritten; it and a damaged file (unparseable, not an object, a refused value — repaired by the
  boot's one write) are listed in `/status` `ConfigFaults` for that boot. A command-only schema has no
  file, and nothing re-runs a write on its own: no timer, retry or cross-boot flag. FRAM is outside this rule. Full
  account: SPECIFICATION.md C.7.3 and F.2."
- **Resolved**: A.U0.32 rewrites the head and drops the foreclosure (U0); A.U36.034 rewrites the safety sentence (U36);
  A.U36.544 removes the item-6 pointer (U36) — merged. A.U36.034 (2)'s "A missing config file creates nothing" is
  superseded by OR136.a (owner, 2026-10-01), its "an unreadable one is never overwritten" kept and joined by OR138.a's
  fault list (A-C review fold); a damaged file (unparseable, non-object, refused value) is repaired by the boot's one
  write and still listed, a missing or unknown key is a repair only (lead ruling 2026-10-05 on OR138.a (1)).
- **Unit**: U36. Stage U0.
- **Depends**: SPEC C.7.3, F.2 (SPEC; M.SPEC.061, M.SPEC.096 as the fold amends them)
- **Blast carried by**: M.DOCS.063 (item 6 stub deleted); the wear rule's fresh-filesystem sentence → M.DOCS.086
- **Kind**: rule

### M.DOCS.083 `MemoryError` handling follows one criterion
- **From**: A.U0.38 (V09, `:204-206`); A.U30.01 (3)
- **Site**: `CLAUDE.md:204-206`
- **Change**: end state (A.U30.01): "- **`MemoryError` handling follows one criterion** — a function with a true
  graceful-degradation alternative catches and degrades; one that is doomed without memory lets the task end for the
  supervisor to restart; `asyncio` primitives are never blanket-wrapped (owner, 2026-09-25). SPECIFICATION.md Part
  I.4(a)."
- **Resolved**: A.U0.38's U0 clause is superseded by A.U30.01's rewrite (both state the owner's 2026-09-25 rule).
- **Unit**: U30. Stage U0.
- **Depends**: SPEC I.4(a) (A.U30.01 (1), SPEC)
- **Blast carried by**: —
- **Kind**: rule

### M.DOCS.084 Adafruit, long-blocking, boot latency, UART no-block: tags, paths, pointers
- **From**: A.U0.23 (`:207`, `:213`, `:231`); A.U1.12 (`:208`); A.U36.541 (3) (`:214`); A.U31.03 (boot-latency last
  sentence); A.U36.532 (`:233-234`); A.U31.01 (`:210-212` unchanged); A.SDEP.17 W25 via M.PROC.011 (conditional; gap pass G1);
  OR141.a (4) (b), (f) (the receive side reads a DMA ring; the clamp is its fill level) (A-C review fold)
- **Site**: `CLAUDE.md:207-236`
- **Change**: `:207` "(keeping attribution)" gains "(owner, 2026-07-13, `b64857d`)"; `:208` the Microdot path →
  `legacy/firmware/python/CommonDrivers/microdot.py`; `:210-212` unchanged; `:213` "(WP6, owner-established
  requirement)" → "(owner, 2026-09-16, the owner's background as migrated by `abe4009f`, paraphrase)"; `:214` "These
  devices run for months between reboots" → "These devices run indefinitely between reboots (SPECIFICATION.md 0.1)";
  the bullet's last sentence ends "; each inter-feed boot stretch and its margin are rows of SPECIFICATION.md Part F.3's
  timing budget table" (A.U31.03); `:231` "**The mirror-image failure is just as forbidden**" gains "(agent, 2026-09-11,
  extending the owner's rule)"; `:233-234` "SPECIFICATION.md Parts F.5.8 and F.5.9 — F.5.8 also states" → "Parts F.8.2
  and F.8.3 — F.8.2 also states" (and "(Part F.5.9)" at `:231` → "(Part F.8.3)"). Conditional (M.PROC.011, W25): if
  the U0 re-read finds `machine.UART.read()/readinto()`'s per-byte wait changed at the refreshed pin, the bullet's
  mechanism sentence ("wait out `timeout_char` for every byte … measured: 4.4ms per 53-byte frame") follows the source
  and F.8.2; the rule (clamp to `uart.any()`, a real yield in `ready()`) stays as the owner set it. (A-C review fold, U13)
  The clamp's object follows the receive path: "a clamp to `uart.any()` on every read" → "a clamp to the bytes already
  received on every read — the DMA receive ring's fill level, since the driver never calls `machine.UART`'s receive
  side (owner, 2026-10-05)", and the mechanism sentence is kept as the reason the driver bypasses `machine.UART.read()`;
  the yield in `ready()` and both poll rates stay.
- **Resolved**: —
- **Unit**: U36. Stages U0, U1, U13 (the clamp's object, with the DMA receive path), U31.
- **Depends**: SPEC 0.1 (A.U36.541), F.3 table (A.U31.01), F.8 renumbering (A.U36.532) — SPEC; M.SPEC.108 (F.8.2's receive
  path, U13); M.SRC_NET.221
- **Blast carried by**: —
- **Kind**: rule

### M.DOCS.085 The hazard rule: every shared resource, C.8's one list, the UART clause in both CRC modes
- **From**: A.U0.37 (`:237-240` head); A.U36.014; A.U36.539 (1); A.S0930.08; A.U36.512 (4) (`:239`); A.U7.01 (levels);
  A.U17.25 (UART clause handoff); M_TWIN gap (twin UART files)
- **Site**: `CLAUDE.md:237-248`
- **Change**: end state: A.U0.37's head ("**A new device on a shared resource — an I2C/SPI bus and every other shared
  resource (locks, FRAM, the config file, sockets, the heap) — gets hazard test coverage across all four test tiers that
  apply to it — never forget this** (owner, 2026-09-03, `da3a5b5`: 'note down to never forget this'; every shared
  resource, owner, 2026-09-26)"), the three coverage kinds ("same-device read-vs-write concurrency, cross-device
  interleaving if it shares a bus on any device, and an address/command sweep"), then A.U36.014's "at every level that
  applies (L1, L2, L3, L4). The files per level, the promotion checklist and the two real-hardware write-safety
  constraints are SPECIFICATION.md C.8's standing rule — the one list; this rule does not restate it." then A.U36.539
  (1)'s "The UART link gets the same coverage in its two-participant shape, in both CRC modes: concurrent use of one
  instance serialised or refused, both ends transmitting detected and recovered, a frame and field sweep — its files per
  level are SPECIFICATION.md J.7's tier map (owner, 2026-09-11; both CRC modes, owner, 2026-09-30)."
- **Resolved**: A.S0930.08's "in both CRC modes" is already in A.U36.539's sentence — once. M_TWIN asks that the clause
  name `tests/test_digital_twin_uart_{comm_hazard,field_sweep}.py`; A.U36.014 makes C.8/J.7 the one list and CLAUDE.md
  names no file, so the two L2 files are named in J.7's tier map (A.U36.539 (2), SPEC), which this clause points to —
  settled by the one-list rule. `:239` "in either variant" → "on any device" (A.U36.512) survives in the kinds clause.
- **Unit**: U36. Stage U0 (head).
- **Depends**: SPEC C.8 and J.7 tier map (A.U36.539 (2), SPEC)
- **Blast carried by**: J.7's L2 cells name the two twin files (M.TWIN.154/.156 → SPEC)
- **Kind**: rule

### M.DOCS.086 The wear rule: FRAM is not wear, the flag names, `resetconfig`, the invariant sentence
- **From**: A.U0.37 (`:249-251`); A.U26.74 (5); A.S0930.30, A.S0930.19 (dispatch-only exception); A.U36.546 (1)
  (`:272-283`); OR136.a (4) (the fresh-filesystem default writes are prerequisites), OR140.a (2) (the console-starvation
  test is gated) (A-C review fold)
- **Site**: `CLAUDE.md:249-283`
- **Change**: after "(project owner's explicit, standing direction, 2026-09-17)" add "FRAM writes are not wear (owner,
  2026-09-26: 'FRAM writes do not count as wear.')"; flags and markers as A.U26.74 renames them —
  `--allow-persistence-writes` → `--allow-persistence-write`, `long_soak` → `soak_duration` (with `--soak-duration`),
  `--allow-multi-day-rollover-wait` → `--allow-multi-day-rollover`; "a *dispatch-only* PUT persists nothing and is
  deliberately outside the gate" → "… deliberately outside the gate, except `SystemCmd` `"resetconfig"`, whose purpose
  deletes every config file (owner, 2026-09-30)"; after the prerequisite sentence ("…stays unmarked and allowed …")
  (A-C review fold): "A boot on a fresh filesystem writes each config file once with its defaults; a test that boots one
  reaches those writes as a prerequisite, never as the write under test, so they stay unmarked (owner, 2026-10-01). The
  console-starvation bench test spends two flash writes it owns and runs only behind the persistence-write flag (owner,
  2026-10-02)."; `:272-283` ("Found the hard way: `tests/test_tmp_scratch.py` created
  400,000 … find the invariant instead.") → "When a test seems to need brute-force scale, it proves the invariant
  instead (SPECIFICATION.md E.3)."
- **Resolved**: —
- **Unit**: U36. Stages: U0 (FRAM sentence), U11 (the fresh-filesystem sentence, with the absent-file write), U26 (flag
  names land with the rename; the console-test sentence with its gate), U36.
- **Depends**: SPEC E.3 gains the account (A.U36.546, SPEC); SPEC H dispatch-only row (A.S0930.30, SPEC); M.SRC_CORE.043
  (the absent-file write), M.HW_BENCH.082 (the gated console test)
- **Blast carried by**: `tests_scripts/test_persistence_write_marker_completeness.py` (A.S0930.19, TSC)
- **Kind**: rule

### M.DOCS.087 The go-ahead rule carries its owner tag
- **From**: A.U0.37 (`:284-285`)
- **Site**: `CLAUDE.md:284-294`
- **Change**: "A session needs the project owner's go-ahead, given directly in that session's own conversation" gains
  "(owner, 2026-09-25)". The rest unchanged.
- **Resolved**: —
- **Unit**: U0
- **Depends**: —
- **Blast carried by**: `tests_hardware/README.md` "How a round runs" cites it (A.U36.001, HW_BENCH)
- **Kind**: rule

### M.DOCS.088 The two bench-network rules: rule, one reason, B.13
- **From**: A.U0.32 (`:295`); A.U36.546 (1) (`:298-301`, `:304-306`); A.U0.45 (`:302-304`); A.U1.12 (`:306`)
- **Site**: `CLAUDE.md:295-306`
- **Change**: `:295` "… must keep a recovery dead-man's-switch continuously armed" gains "(owner, 2026-09-26)";
  `:298-301` → "A one-shot timer already spent by an earlier dry run protects nothing, so the switch is armed and
  verified for each risk window (SPECIFICATION.md B.13: the recovery script and the arm, verify, disarm pattern).";
  `:302-304` head gains "(agent, 2026-09-04, `28c5d8e`: MAC drift observed on the bench)"; `:304-306` → "`ensure_bench_bridge()`
  and the manual recipe in `tests_hardware/README.md` both pin it (SPECIFICATION.md B.13)."
- **Resolved**: A.U1.12's U1 repath of `:306` is subsumed by A.U36.546's sentence (same target file).
- **Unit**: U36. Stages U0, U1.
- **Depends**: SPEC B.13 (SPEC); A.U1.05 (the recipe's move to `tests_hardware/README.md`, HW_BENCH)
- **Blast carried by**: —
- **Kind**: rule

### M.DOCS.089 The memory rule: owner's words, the boot reset in `run_setups()`, the test collect rule
- **From**: A.U0.43 (`:307-308`, `:320`); A.U11.10 (`:340-342`); A.U27.21 (aliases); A.U30.10; A.U30.14; A.U30.17 (1);
  A.U36.546 (1) (`:349-356`); A.U7.21/A.U7.22/A.U7.23 (the gate list by name; M_TSC/M_SPEC Blast pointers, gap pass G1)
- **Site**: `CLAUDE.md:307-366`
- **Change**: `:320` "**Standing rule, every test, …**:" gains "(owner, 2026-09-26: 'The firmware must be rock solid
  without the threshold, and the threshold is finally applied to move it even further into the stable region, but must
  be tested and verified by itself.')"; `:340-342` the boot-confined placement reset is "`gc.collect()` between the units
  of the two one-time lists, both run by `SystemService` (`run_setups()` and `start_tasks()`'s starter loop),
  and nowhere else, mechanically confined by `scripts/_check_gc_collect_sites.py` (aliases included) and
  `tests_scripts/test_gc_collect_sites.py` on the *sites* …"; `:329-337` "**There are FOUR such gates — the unit tier,
  the twin tier and the flash/bench real-hardware soak gates — and all four match …**" → "**Every memory gate — the unit
  tier, the twin tier, the `tests_scripts` twin boots, the JS live twins and cross-browser smoke, and the flash and bench
  real-hardware gates — matches `MemoryError` OR `memory allocation failed`, the second being the half that matters**"
  (names, no count, so it cannot drift: A.U7.21), and "keeps all four agreeing" → "keeps them all agreeing" (the JS gate
  reads `tests_js/_memory_markers.js`, A.U7.23); after "…Full account and its measured effect:
  `SPECIFICATION.md` Part I.4(f.1)." A.U30.17's paragraph "**Outside the firmware** — tests, the twin, device scripts and
  tools — `gc.collect()` sets a baseline … `scripts/_check_gc_collect_sites.py` names every allowed site."; "the value
  the firmware's boot entry sets" gains "(set once, checked)"; "(86/86 on 2026-09-24)" deleted; "on silicon it is what
  carries the boot placement gain into the run phase (80% held against 12% at the reactive default) — but that is a
  layout benefit, not what makes the system stable" → "it carries the boot placement gain into the run phase
  (SPECIFICATION.md I.4(f.1)) — a layout benefit, not what makes the system stable".
- **Resolved**: A.U30.10 (U30) names the figure's image in CLAUDE.md; A.U36.546 (U36) moves the figure to I.4(f.1) and
  leaves a pointer. The pointer is the end state; A.U30.10's description (largest free block 80 % of free four seconds
  after the task-starter list at `gc.threshold(32768)`, against 12 % at the reactive default — `dev`, v1.29.0,
  2026-09-19; archive §7H.3) is the I.4(f.1) sentence's content, replacing A.U36.546's "recorded 2026-09-21" placeholder
  (A.U30.10 located the figure; Gaps: SPEC). A.U27.21 replaces `lint.sh`'s greps by the AST checker, so the confinement
  sentence names the checker.
- **Unit**: U36. Stages: U0 (A.U0.43), U7 (the gate list, with A.U7.21-.23), U11 (A.U11.10), U20 (`start_tasks()`), U27
  (checker name), U30 (A.U30.10/.14/.17), U36.
- **Depends**: SPEC I.4(e)/(f)/(f.1) (A.U30.14/.17, A.U36.546, SPEC)
- **Blast carried by**: `tests_scripts/test_gc_collect_sites.py` (TSC)
- **Kind**: rule

### M.DOCS.090 The FRAM-log rule: save then clear; the logger set derived per device
- **From**: A.U0.37 (`:367-370` tag); A.U36.002 (1)-(2); A.S0930.30; GAP-G7 / GAP-10 (M.SRC_CORE.040, M.SRC_SENS.052);
  A.U2.08 (`:391`, M.SPEC.058's Blast pointer; gap pass G1)
- **Site**: `CLAUDE.md:367-394`
- **Change**: `:367-377` → A.U36.002 (1)'s text with A.U0.37's tag after the bold head: "- **When investigating any
  unexpected real-hardware error or reset — read and save, verbatim, the FRAM-persisted per-module error logs (`GET
  /status`'s `errcount`) and, after an unexpected reset, `GET /status`'s `ResetReason`, BEFORE issuing any `PUT /status
  {"ResetErrors": true}` call (it clears every registered module) or a `SystemCmd` `"erasefram"` (it zeroes the whole
  chip), reflashing, rebooting or otherwise clearing state; "clear it first" always means save, then clear.** (owner,
  2026-09-25 and 2026-09-26) Which loggers are FRAM-backed is one fact per device, derived from its TOML: every module
  except the FRAM module itself, whenever its instance is wired to FRAM, and except the SCD30 reader's config-store
  logger (`CFGMGR_SCD30`), which stays RAM-only (SPECIFICATION.md Part A.7 states the rule and its derivation)."
  `:377-385` unchanged; `:386-394` gains A.U36.002 (2)'s "A reflash may also re-initialise the chunks: the layout is
  fixed within one build only (owner, 2026-09-26)." and, at `:391`, A.U2.08's "(a seeded `errno=5` read back as SYSTEM's
  `"Task N ended with exception"`, …)" → "(a seeded entry read back as a plausible SYSTEM task end (test data, not
  firmware evidence), …)", with no number — the per-task code is gone (U2)
- **Resolved**: A.S0930.30's "a `SystemCmd` `"erasefram"`" clause is already in A.U36.002's text — once. GAP-G7: the
  derivation sentence names the one exception the code makes (`_CFG_LOG_FRAM = False`, M.SRC_CORE.040).
- **Unit**: U36. Stage U0 (tag); stage U2 (the `:391` example, with A.U2.08).
- **Depends**: SPEC A.7 FRAM list names the same exception (GAP-G7, SPEC)
- **Blast carried by**: `tests/_sensortask_scenarios.py` chunk list (TEST_HELP, M.SRC_SENS.052)
- **Kind**: rule

### M.DOCS.091 Working agreements: features kept; change classes; decision records; the gate verdict
- **From**: A.U0.37 (`:399-401`); A.U36.540 (2) (`:401-403`); A.U0.10; A.U36.536 (1); A.U36.525
- **Site**: `CLAUDE.md:396-411`, new bullets after `:411`
- **Change**: `:399-401` "The refactor should end up with the same top-level features" gains "(owner, 2026-07-13;
  restated 2026-09-25: 'My expectation is that the current features remains across the changes done here')";
  `:401-403` ("When a fact in this file or BACKLOG.md turns out to be stale …") → A.U36.540 (2)'s "**Change classes**"
  bullet verbatim; `:404-411` (documentation holds current state) unchanged; after it A.U0.10's "**Decision records
  (owner, 2026-09-26: the five prevention rules, answered '4. yes')**" bullet with its five rules and the "No owner
  trace …" sentence, rule (1) followed by A.U36.536 (1)'s reviewed-decision tag form ("(agent, YYYY-MM-DD;
  owner-reviewed, YYYY-MM-DD)"); then A.U36.525's "**A gate's verdict is its exit status or its own summary block,
  never a truncated view of its output** …" bullet.
- **Resolved**: A.U0.10 rule (5) states the citation and vocabulary checks with "existing text allow-listed until
  rewritten; the list only shrinks"; A.U36.549 empties the allow-list at U36 and A.U37.02 removes the mechanism — at
  U37 that clause reads "the checks fail on any such text" (the allow-list being gone). A.U36.540 (2) supersedes the
  stale-fact bullet's wording (its "update the doc in the same session" is the third sentence of the new text).
- **Unit**: U36. Stages: U0 (A.U0.37 tag; A.U0.10 bullet), U36, U37 (allow-list clause).
- **Depends**: A.U0.08/A.U0.09 checks (TSC); BACKLOG owner-question list (M.DOCS.067)
- **Blast carried by**: `tests_scripts/test_decision_vocabulary.py`, `tests_scripts/test_citations.py` (TSC)
- **Kind**: rule

### M.DOCS.092 The comment rule: one header, the cap, one form, English
- **From**: A.U36.533 (1); AC_NOTES 9 (tag-line pointer); AC_NOTES 42 (headers everywhere); M_SPEC gap 2 (the grammar's one
  home is L.6.4, M.SPEC.118/.149; gap pass G1)
- **Site**: `CLAUDE.md:412-443`
- **Change**: A.U36.533 (1)'s bullet verbatim ("- **Every file opens with exactly one header comment block, and every
  comment block — header or inline — keeps to three prose lines, prefer fewer** (owner, 2026-09-14, re-confirmed
  2026-09-18; every file of every language, owner, 2026-09-26) …"), its tag-line pointer kept as A.U36.533 writes it:
  "(…, `// @tunable`; SPECIFICATION.md L.6.4)" — L.6.4 only.
- **Resolved**: AC_NOTES 9 leaves the choice (rows into L.6.4, or the pointer to H.5.1) to U36. SPEC took the first
  option: A.U36.514 (2) puts the `@web`/`@web-group` rows into L.6.4's table and H.5.1 points there for the grammar
  (M.SPEC.118, M.SPEC.149), so the pointer names L.6.4 alone and the earlier "H.5.1" half is dropped (M_SPEC gap 2;
  gap pass G1). `// @tunable` stays only if A.U8.02's grammar lands,
  as A.U36.533 says.
- **Unit**: U36
- **Depends**: SPEC D.11 (A.U36.533 (2), SPEC); `tests_scripts/test_comment_block_cap.py` header-presence check (U27,
  AC_NOTES 42, TSC)
- **Blast carried by**: SPEC 0.4 conventions table cites this rule (A.U36.542, SPEC)
- **Kind**: rule

### M.DOCS.093 Workflow, parity, test changes, recorded failures, close-out, agents, re-verification
- **From**: A.U0.11 (`:444-446`, `:449-464`); A.U36.529, A.U36.021 (`:447-448`); A.U36.017 (2); A.U36.018; A.U37.08;
  OR140.a (6) (the old work-in-progress folder's code is a reference for the owner's intent unless stated otherwise;
  G9/R02 wording) (A-C review fold)
- **Site**: `CLAUDE.md:444-464`, bullets appended before `## Code quality tooling` (`:466`)
- **Change**: end state, in this order: A.U36.529's "- **Legacy parity means no lost function.** …" bullet, its list
  entry reading "the ISL29125 legacy driver" (no parenthesis), its `improved-quality/` sentence replaced by the owner's
  ruling (A-C review fold): "Code the owner committed into the retired `improved-quality/` work-in-progress folder
  (`8c4a73d`), since promoted into `src/`, counts as a reference for the owner's intent unless something states
  otherwise (owner, 2026-10-02)." — then A.U36.021's sentence "Where a legacy driver proved
  nothing in service — the ISL29125's only ran a smoke test — parity is with its evident intent wherever the owner's
  list does not decide (SPECIFICATION.md M.1)."; A.U0.11's "**Workflow for substantial work** (owner, 2026-09-26: …)"
  bullet replacing `:444-446` and `:449-464`; A.U36.017's "- **A failing test is a regression to fix; a test changes
  only mechanically, never in its goal** (owner, 2026-09-25). The full rule, including when an expectation may be
  corrected: SPECIFICATION.md E.2.2."; A.U36.018's "- **An unrelated issue or CI failure met along the way is recorded**
  — fixed, or entered in BACKLOG.md's owner-question list or owed list with its reason — and never passed over
  (owner, 2026-09-16, `9894e85`, paraphrase)."; A.U37.08's three bullets ("**Temporary files migrate, then go**", "**Parallel agents converge under one
  lead**", "**Re-verify until one pass is all green**") verbatim.
- **Resolved**: A.U36.529 asks A-C to keep one ISL29125 statement: A.U36.021's sentence is kept and the list's
  "(smoke-tested only, SPECIFICATION.md M.1)" dropped. A.U36.018's "entered in BACKLOG.md with its reason": BACKLOG's
  end state admits such an entry only as an owner question or owed hardware (M.DOCS.061) — the sentence reads "entered
  in BACKLOG.md's owner-question list or owed list" (agent decision, below).
- **Unit**: U37. Stages: U0 (A.U0.11), U36 (A.U36.017/.018/.021/.529), U37 (A.U37.08).
- **Depends**: SPEC E.2.2 (A.U36.017 (1), SPEC), M.1 (SPEC)
- **Blast carried by**: —
- **Kind**: rule

### M.DOCS.094 "Code quality tooling": the venv check, the scope with generated output, the new-file rule
- **From**: A.U27.26 (`:468-477`); A.U0.13 (scope sentence); A.U1.12 (`:511-513`); A.U36.548 (4) (`:515-517`); A.U36.043
  (`:525-526`); A.U27.09 (generated scope); A.U27.23, A.U27.25 (exclusion list); A.U27.24 (the clean-scope test)
- **Site**: `CLAUDE.md:468-477`, `:501-531`
- **Change**: `:468-477` "`lint.sh`/`typecheck.sh` assume those tools are already on `PATH` (e.g. an activated `uv
  sync`-created venv)" → "`lint.sh`/`typecheck.sh` refuse to run outside the synced project venv"; `:501` "**Scope is
  eight directories**: …" gains "plus the generated `build/generated_src/`"; the scope bullet gains A.U0.13's sentence
  "A new file in a scope joins ruff and mypy (and, if MicroPython-target, the Unix-port tests) from its first commit
  (agent, 2026-07-22), and so does every new generator, validator or host module (owner, 2026-09-10, `fc6afbe`: 'add
  all build scripts to the full CI')"; `:511-513` → "The legacy tree (`legacy/`) is never in any lint, type or CI scope
  (legacy rule above)."; `:515-517` "there's no tracked-debt scope left … deleted (see 'Hard rules' above)" deleted;
  "All eight are expected to stay fully clean" gains "(`tests_scripts/test_lint_type_scopes.py` checks the scopes)";
  `:525-526` the exclusion list without `segfault_stress_repro.py`, and stating what A.U27.23 made true: the twin pass's
  `files` list in `digital_twin/typecheck.ini`, and `tests/network.py` and `tests_scripts/conftest.py` each checked
  alone by `typecheck.sh`.
- **Resolved**: A.U36.043 drops the retired file; A.U27.25 hands the list's wording to U36 — merged. "eight directories"
  stays the count of directories, the generated tree being named apart.
- **Unit**: U36. Stages: U0 (A.U0.13 sentence), U1 (A.U1.12), U27 (venv clause, generated scope), U36.
- **Depends**: SPEC B.15 (A.U27.23/.25, SPEC)
- **Blast carried by**: `tests_scripts/test_lint_type_scopes.py` (A.U27.24, TSC); BACKLOG "Rough sequencing" deletion
  (M.DOCS.062)
- **Kind**: rule

### M.DOCS.095 CI and zizmor bullets: the pin form, the `self-repository` outcome, B.17
- **From**: A.U28.40 (`:492-495`); A.U0.40 (L42, `:497-499`); A.SDEP.19 (W32, `:496-499`, `:498`); A.U36.524 (4) (`:496`)
- **Site**: `CLAUDE.md:478-500`
- **Change**: `:492-495` → A.U28.40's "Policy config is `.github/zizmor.yml`: `unpinned-uses` has a policy — `actions/*`
  may be tag-pinned, everything third-party is pinned to a commit SHA (never a tag object) with an exact-version comment
  — and `self-repository` is disabled (below); every other audit runs at its default."; `:496` "and in the clean-chroot
  recipe below" → "and in the clean-chroot recipe (SPECIFICATION.md B.17)"; `:497-499`: if A.SDEP.19's W32 finds that
  actionlint accepts `uses: $/…` (U0), the `self-repository` sentence goes and A.U28.40's "— and `self-repository` is
  disabled (below)" clause goes with it; otherwise the sentence names the refreshed actionlint version and ends with
  A.U0.40's "(agent, 2026-09-10, `bfaf4c6`): re-enable when actionlint accepts `uses: $/…` (checked at each actionlint
  pin bump)". The CI bullet `:478-490`'s job list is read against `ci.yml` at U36 and corrected in place (A.U36.540 (2)'s
  factual-correction rule; U28 adds jobs, M_TOOL).
- **Resolved**: A.SDEP.19's U0 outcome fixes which branch A.U0.40's tag (U0) and A.U28.40's text (U28) take; both are
  written for either outcome. The job-list check is an agent decision (no constituent rewrites that list).
- **Unit**: U36. Stages: U0 (W32 outcome, tag), U28 (policy sentence).
- **Depends**: M.PROC.008 (f) W32 record; SPEC B.17 (A.U36.524, SPEC)
- **Blast carried by**: `.github/zizmor.yml` header (A.U28.14, TOOL)
- **Kind**: rule

### M.DOCS.096 The unit-test bullet: runner probe, per-file exemptions, E.2
- **From**: A.U0.23 (`:550`); A.U28.34 (`:556-557`); A.U36.544 (4) (`:538` E.3 → E.2)
- **Site**: `CLAUDE.md:532-557`
- **Change**: `:538` "SPECIFICATION.md Part E.3" (the "minimal runner" pointer) → "E.2"; `:550` "(project owner's
  direction: 'add all build scripts to the full CI')" → "(owner, 2026-09-10, `fc6afbe`: 'add all build scripts to the
  full CI')"; `:556-557` → A.U28.34's "`pyproject.toml`'s per-file block is the list, each entry with its reason: the
  test suites (`tests/`, `tests_scripts/`, `tests_hardware/`) share one set, MicroPython-run code and host code each
  carry the rules whose reasons hold only there, and `tests_scripts/test_ruff_exemptions_live.py` fails on an entry that
  no longer fires."
- **Resolved**: —
- **Unit**: U36. Stages U0, U28.
- **Depends**: —
- **Blast carried by**: —
- **Kind**: rule

### M.DOCS.097 The coverage bullet: three traced sets, never a gate, the probe through `_unix_port.sh`
- **From**: A.U36.526 (4); A.U36.546 (1) (coverage sentences); A.U36.512 (4) (`:572`); A.U27.12 (the probe)
- **Site**: `CLAUDE.md:558-587`
- **Change**: `:558-560` → "**`scripts/test.sh --coverage` reports line coverage and never gates** — no threshold exists
  anywhere (owner, 2026-09-25; its test result does gate, SPECIFICATION.md E.5.3)."; `:560-566` → "The pipeline and what
  it traces: SPECIFICATION.md Part E.5."; the two-binary sentences stay with "`scripts/test.sh` asks the binary itself"
  → "every runner asks the binary through `scripts/_unix_port.sh`" and "identifies its variant" → "identifies its build
  flavour"; "**That was HEAP_FRAGMENTATION_MEASUREMENTS.md archive §11 item 0, now decided and done** … unchanged." and
  "(it did, on run `34755468619`)" deleted; `:582-588` (Job Summary, artifact, Codecov, local paths) deleted.
- **Resolved**: —
- **Unit**: U36. Stage U27 (probe sentence).
- **Depends**: SPEC E.5, E.5.2, E.5.3 (SPEC)
- **Blast carried by**: README coverage section (M.DOCS.054)
- **Kind**: rule

### M.DOCS.098 The retry and hang-backstop bullets
- **From**: A.U28.10; A.U0.37 (`:597-598`); A.SDEP.19 (W33); A.U0.55; A.U28.11 (1)
- **Site**: `CLAUDE.md:588-612`
- **Change**: `:588-600` → A.U28.10's text ("**A third party's momentary outage must never read as a red test result**
  (owner, 2026-09-26). … Don't simplify the retry away; a test lane red with no test named in its summary is read from
  the `uv`/build output first."), its `actionlint-py` example kept unless A.SDEP.19's W33 finds a wheel now carries the
  binary, then naming whichever dependency still downloads at build time; `:604-606` → A.U28.11 (1)'s carrier list with
  A.U0.55's "(agent, 2026-09-10, `6564ccd`)" after the bold sentence; `:611-612` → A.U28.11 (1)'s "`digital-twin-e2e`,
  `unit-tests-coverage`, `web-put-matrix`, `web-coverage` and `web-cross-browser-smoke` stay success-gated, each job's
  comment stating why; `tests_scripts/test_ci_workflow.py` fails on an edge that has neither."
- **Resolved**: A.U0.37's tag "(owner, 2026-09-26)" is in A.U28.10's head — once. A.U0.55's `:611` "is the exception"
  wording is replaced by A.U28.11's list.
- **Unit**: U28. Stages U0.
- **Depends**: SPEC B.10 (A.U28.37, SPEC)
- **Blast carried by**: `tests_scripts/test_ci_workflow.py` (TSC)
- **Kind**: rule

### M.DOCS.099 The known hang and segfault bullets: rule, mechanism, pointer
- **From**: A.U36.546 (1) (`:613-664`); A.U24.15 (CLAUDE half) and AC_NOTES 29; A.U14.12 (3) (superseded); A.U14.18;
  A.SDEP.16 (W14); A.SDEP.17 (W18)
- **Site**: `CLAUDE.md:613-664`
- **Change**: hang #1 `:613-621` → "**A test double for `uart.poller`, or any fake stream, is a bounded fake like
  `_StepPoller`, never a real `select.poll()`** (the known hang cause): a real `select.poll()` asks each registered
  stream object for a file descriptor (`MP_STREAM_GET_FILENO`) and, on any non-error answer, polls that descriptor
  instead of ever calling the object's own `ioctl()` (`extmod/modselect.c`, at the pin). `tests/machine.py`'s fake UART
  answered 0, so a real poll over it watched fd 0, the test process's stdin, and a test awaiting a stream read/write
  with `timeout_ms=-1` through that path hung on GitHub Actions (not reproducible locally); both machine fakes now
  answer `EINVAL` as rp2 does. Don't re-diagnose that hang as a code bug (SPECIFICATION.md F.7)." Hang #2 `:622-649` →
  A.U36.546's "**`tests/microtest.py`'s `run()` always ends with `sys.exit()`** … Keep the forced exit." Segfault
  `:650-664` → the rule sentence ("a test helper that calls `asyncio.run()` … only from synchronous test-function
  scope"), then A.U14.18's mechanism sentence ("`run()` is `run_until_complete(create_task(coro))` on the same task queue
  — no fresh loop is installed (mechanism: SPECIFICATION.md Part F.1) — so the nested call re-enters the scheduler under
  the task that is still running."), then "Don't re-diagnose a file that dies mid-run with no summary line as a memory
  bug (SPECIFICATION.md F.1)."; if A.SDEP.17's W18 finds the pin now raises instead of crashing, the symptom words follow
  (the sync-scope rule stays).
- **Resolved**: AC_NOTES 29 (owner-accepted 2026-09-30, AC_NOTES 37): A.U24.15's corrected mechanism replaces "never
  detects readiness"; A.U36.546's rule head replaces the "Known hang cause, fixed" label, and "(the known hang cause)"
  keeps the phrase the one-line fake comments cite (M.TEST_HELP.017, SPEC J.7) resolvable — agent decision, below. The
  `test_asy_uart_driver.py` story goes (A.U36.546). A.U14.12 (3)'s rewording of the "Surfaced by the Timer-GC fix"
  sentence is superseded: A.U36.546 deletes that sentence (the Timer fact is F.1's). Line numbers in the
  `extmod/modselect.c` citation are left to SPEC F.7, CLAUDE.md naming the file only.
- **Unit**: U36. Stages: U14 (A.U14.18 mechanism; A.U14.12 void), U24 (A.U24.15 mechanism into the HEAD bullet).
- **Depends**: SPEC F.1, F.7, E.3 (SPEC)
- **Blast carried by**: fake comments citing "Known hang cause" (M.TEST_HELP.017, TEST_UNIT)
- **Kind**: rule

### M.DOCS.100 Heap-lock, shutdown flake, heapsize, `TZ`: rule, one reason, pointer
- **From**: A.U36.037 (3); A.SDEP.11; A.U36.546 (1) (`:681-708`); A.U0.40 (L10, `:703-708`); A.SDEP.16 (W15)
- **Site**: `CLAUDE.md:665-717`
- **Change**: `:665-680` → A.U36.037 (3)'s "- **A "heap is locked" `MemoryError` at twin shutdown**: … SPECIFICATION.md F.6
  keeps the mechanism and the one right recovery, `gc.collect()`, not `micropython.heap_unlock()`."; `:681-695` →
  "**Don't re-diagnose a shutdown-only exit code 1 at `gc.threshold=32768`, garbled traceback or not, as a project bug
  before confirming the SIGINT-delivery override is applied** (SPECIFICATION.md B.14.1)" — if A.SDEP.11's outcome (c)
  retires the override (upstream default since a tag), this bullet goes and `:665-680`'s sentence names upstream's
  default instead of the override; `:696-708` → "**Each test file runs with an explicit `-X heapsize`**, a Unix-port
  harness setting (SPECIFICATION.md E.3.1): a flaky `MemoryError` in a heavy file is checked against it first, and
  raising it is never the fix (agent, 2026-09-17); a per-file heap override hiding a symptom is never used (owner,
  2026-09-17, `1e2c001`, paraphrase)."; `:709-717` (`TZ=UTC`) kept unless A.SDEP.16's W15 finds `mktime()` fixed at the
  pin, then deleted with the nine settings.
- **Resolved**: A.U0.40's L10 split lands in A.U36.546's heapsize sentence. A.U36.037 and A.SDEP.11 both touch `:677`;
  A.U36.037's text is the end state, conditioned on A.SDEP.11's U0 outcome.
- **Unit**: U36. Stages: U0 (A.U0.40; A.SDEP.11/.16 outcomes), U25 (helper retired, A.U25.39).
- **Depends**: SPEC F.6, B.14.1, E.3.1 (SPEC)
- **Blast carried by**: twin README (A.U25.39, TWIN)
- **Kind**: rule

### M.DOCS.101 Two suites binding fixed ports: the live twin, the per-port lock
- **From**: A.U36.546 (1) (`:718-731`); A.U24.69; M_WEB gap 8 (M.WEB.078); M_TWIN gap
- **Site**: `CLAUDE.md:718-731`
- **Change**: "`scripts/test.sh`'s MicroPython tier serves real HTTP and a real port-53 DNS server, and so does `npm
  test`'s mock server" → "… and so does `npm test`'s live twin (port 53, 19481/19482; the mock server intercepts `fetch`
  and binds none)"; the bullet gains "Enforced by a per-port lock: the second suite fails at once, naming the port and
  its holder." (A.U24.69); "Confirmed 2026-09-13: nine failures … with nothing else running." deleted; "Run the two
  tiers one after the other; don't re-diagnose this pattern as a code or merge defect." kept.
- **Resolved**: M_TWIN asks the bullet to name the twin UART files; they bind no port (the UART pair is in-process), so
  this bullet does not name them — settled (their home is J.7, M.DOCS.085).
- **Unit**: U36. Stage U24 (lock sentence may land with A.U24.69).
- **Depends**: A.U24.69 (`scripts/_port_lock.sh`, SCR/WEB)
- **Blast carried by**: `tests_scripts/test_port_lock.py` (TSC)
- **Kind**: rule

### M.DOCS.102 `ruff format`, E722, typing: tags and one pointer
- **From**: A.U0.57 (`:732`); A.U0.39 (`:739-741`); A.U33.06; A.U0.38 (RF073, `:743`); A.U1.12 (`:752-753`); A.U36.534 (3)
- **Site**: `CLAUDE.md:732-754`
- **Change**: `:732` → "**`ruff format` is not used anywhere** (agent, 2026-07-13)"; `:739-741` → A.U33.06's "- **Bare
  `except:` (E722) stays enabled** (owner, 2026-07-13, `c0dfd20`, paraphrase: flag bare excepts rather than silence
  them): every one it flagged has been fixed, none remains in any lint scope, and the rule keeps it that way."; `:742-754`
  → A.U36.534's "- **Typing follows SPECIFICATION.md C.10**: PEP 604 `X | Y`, never `typing.Union` (ruff `UP007`),
  typing-only imports under the guarded `TYPE_CHECKING`."
- **Resolved**: A.U0.39's tag (U0) is carried into A.U33.06's text (same owner date); A.U0.38's RF073 (U0) and A.U1.12's
  path (U1) are stages A.U36.534 replaces.
- **Unit**: U36. Stages U0, U1, U33.
- **Depends**: SPEC C.10 (A.U36.534 (1), SPEC)
- **Blast carried by**: —
- **Kind**: rule

### M.DOCS.103 mypy, `method-assign`, E402
- **From**: A.U36.527 (1); A.U27.22; A.U8.23, A.U8.24 (handoffs); A.U0.39 (`:771-772`); A.U24.71; A.U27.20; A.SDEP.16
  (W12/W13, `:780-787`)
- **Site**: `CLAUDE.md:755-787`
- **Change**: `:755-770` → A.U36.527 (1)'s bullet, its flag list "`no_implicit_optional`, `warn_unreachable`,
  `disallow_any_explicit` and the `ignore-without-code` error code" (A.U27.22); `:771-772` "(project owner's direction)"
  → "(owner, 2026-09-10)"; "each of those ~157 sites carries its own inline" → "each such site carries its own inline";
  "`scripts/lint.sh` enforces it with a grep guard that fails the lint gate" gains "and fails when it cannot search";
  `:780-787`: the example file named there is re-pointed to a remaining case if A.SDEP.16 removes the
  `patch_asy_udp_socket_for_unix_port()` call (W13), else unchanged.
- **Resolved**: A.U27.22 adds a flag to the same sentence A.U36.527 rewrites — one list.
- **Unit**: U36. Stages U0, U24, U27.
- **Depends**: SPEC C.10, B.15 (SPEC)
- **Blast carried by**: `tests_scripts/test_mypy_any_baseline.py` (TSC)
- **Kind**: rule

### M.DOCS.104 Merge rules: the discarded side read; the lock contradiction tested
- **From**: A.U36.528 (1)-(2); A.SDEP.03
- **Site**: `CLAUDE.md:788-804`
- **Change**: A.U36.528's two bullets verbatim (`:788-790` "- **A merge resolved by taking one side wholesale is checked
  before and after the commit.** …"; `:791-804` "- **A merge that touches `uv.lock` can silently bypass the tool pins.**
  … (agent, 2026-09-10).").
- **Resolved**: A.SDEP.03 runs the same check on every lock rewrite during the refresh (a procedure, not a doc edit);
  `tests_scripts/test_tool_pins.py` (A.U28.03) is the standing form both texts cite.
- **Unit**: U36
- **Depends**: A.U28.03 (TSC)
- **Blast carried by**: —
- **Kind**: rule

### M.DOCS.105 Stub bullets, the retired-fork bullet, and the tunables rule
- **From**: A.U27.02 (`:805-820`, `:841-854`); A.U27.03 (`:821-840`); A.U36.546 (1); A.SDEP.15 (W08-W10); A.U36.548 (4)
  (`:855-857`); A.U8.01 (new bullet); OR140.a (11) (the stub version moves with every MicroPython bump, enforced by a
  check) (A-C review fold)
- **Site**: `CLAUDE.md:805-857`, new bullet
- **Change**: `:805-820` "Version is auto-derived, not a separate hand-kept pin" → "The post-releases are pinned in
  `toolchain/versions.toml`'s `[stubs]` and move with every MicroPython bump: a check fails while their X.Y.Z differs
  from the ref (owner, 2026-10-02)" (A.U27.02; A-C review fold: the owner's ruling and tag), the rest kept; `:821-840` →
  "**`mypy src tests` resolves `from machine import X` to `tests/machine.py`'s fake**, not the board stub; the board
  stub's missing zero-argument `Timer()` is a stub gap listed in SPECIFICATION.md B.15, and `I2C.deinit()`/`SPI.deinit()`
  are no-ops on rp2 (F.5.1)." — deleted if A.SDEP.15's W10 finds the gap fixed; `:841-854` → "**`scripts/typecheck.sh`
  repairs the stub package's verified defects after installing it, each only while the defect is present
  (SPECIFICATION.md B.15); don't replace a repair with `type: ignore` in `src/` or `digital_twin/`**: the code is correct
  on the board, and `warn_unused_ignores` would fail the day the stubs are fixed." — deleted if W08/W09 retire every
  repair; `:855-857` deleted. New bullet (A.U8.01): "- **Tuned values carry `@tunable` and a Part N row, both changed in
  the same change** (owner, 2026-09-25: 'updated on changing parameters or whenever such parameter is added')." (no
  audit ID in the text).
- **Resolved**: A.U27.02/.03 hand their CLAUDE wording to U36; A.U36.546's shapes take it. F.5.1 stays F.5.1 (A.U36.532
  renumbers only F.5.7-F.5.9).
- **Unit**: U36. Stages: U0 (A.SDEP.15 outcomes), U8 (tunables bullet), U27.
- **Depends**: SPEC B.15 stub list (A.U27.03, SPEC); SPEC Part N (A.U8.01, SPEC); M.SCR.027 (the X.Y.Z check)
- **Blast carried by**: `tests_scripts/test_typecheck_sh.py` (TSC)
- **Kind**: rule

### M.DOCS.106 "Build-environment verification": the periodic-check rule; the recipe moves to B.17
- **From**: A.U36.524 (2); A.U0.39 (L37, `:873`); A.U21.16 (`:979-983`); A.U0.23 (A45 done at HEAD)
- **Site**: `CLAUDE.md:859-1033`
- **Change**: end state: "## Build-environment verification\n\nEvery build-environment change (`pyproject.toml`,
  `uv.lock`, `scripts/`, `toolchain/`, `.github/`, `package.json`) gets a line in BACKLOG.md's running list of changes
  since the clean-chroot legs were last satisfied. The owner runs the verification — noble and trixie, plus the
  full-installer leg for `toolchain/` changes — periodically, by hand; it is not a pre-push gate (owner, 2026-09-18). A
  session whose sandbox can build a chroot runs it too. The recipe and what counts as passing: SPECIFICATION.md B.17."
- **Resolved**: A.U0.39's `:873` tag "(owner, 2026-09-11)" and A.U21.16's `:979-983` rewrite land in CLAUDE.md at U0/U21
  and move with the recipe into SPEC B.17 at U36 (Gaps: SPEC).
- **Unit**: U36. Stages U0, U21.
- **Depends**: SPEC B.17 (A.U36.524 (1), SPEC); BACKLOG chroot list (M.DOCS.066)
- **Blast carried by**: SPEC `:6-7`, `:812`, README `:649-650` pointers (A.U36.524 (6), SPEC and M.DOCS.060)
- **Kind**: rule

### M.DOCS.107 "Pull request workflow": commit messages, the chroot line, head-commit CI
- **From**: A.U36.536 (2); A.U36.524 (3); A.U28.11 (2); A.U0.23 (`:1045-1046`)
- **Site**: `CLAUDE.md:1036-1051`
- **Change**: end state, in order: A.U36.536 (2)'s "- **Commit messages**: …" bullet; A.U36.524 (3)'s "- **When
  pushing anything touching the build environment**, add its line to BACKLOG.md's chroot list ("Build-environment
  verification" above)."; the authorization bullet with `:1045-1046` → "(owner, 2026-07-13, `dddaafa`); don't
  re-ask."; "Always create a pull request …"; A.U28.11 (2)'s "**A branch counts green only when CI ran on its head
  commit** (agent, 2026-09-18): …"; "Automatically subscribe …" unchanged.
- **Resolved**: —
- **Unit**: U36. Stages U0, U28.
- **Depends**: —
- **Blast carried by**: —
- **Kind**: rule

### M.DOCS.108 "Architecture reference" names Part 0; the Microdot section names no version
- **From**: A.U36.541 (4); A.SDEP.06 (`:1063`); A.U36.030 (the tag lives in THIRD_PARTY)
- **Site**: `CLAUDE.md:1052-1067`
- **Change**: "Architecture reference" gains first: "**Design principles: SPECIFICATION.md Part 0** — the concept, the
  pillars, the structural patterns and the conventions catalog every change is checked against."; `:1063` "(vendored,
  v2.6.2, see 'Hard rules' above …)" → "(vendored, see 'Hard rules' above …)".
- **Resolved**: A.SDEP.06 re-stamps `:1063` with the new tag (U0); A.U36.030 names the Microdot tag only in
  THIRD_PARTY_LICENSES.md — applied to this second mention too at U36 (agent decision, consistency).
- **Unit**: U36. Stage U0.
- **Depends**: SPEC Part 0 (A.U36.541, SPEC)
- **Blast carried by**: —
- **Kind**: doc

## .claude/skills/integrate-module/SKILL.md (new)

### M.DOCS.109 The integrate-module skill points into Part K
- **From**: A.U36.543 (9), (11) (AC3_R R-04 and AC3_S S-13: no change created the file; M.DOCS.060 only maps it).
- **Site**: new `.claude/skills/integrate-module/SKILL.md`.
- **Change**: front matter `name: integrate-module`, `description: Add a module, service or sensor driver to this repo by
  walking SPECIFICATION.md Part K in order.`; body ≤ 10 lines, as A.U36.543 (9) writes it: read Part 0 and Part K in
  full; the inputs are the datasheet and the owner brief (K.1 item 0); walk K.1-K.11 in order, reporting per step what
  was done or why it does not apply; never merge a baseline run's worktree. No audit ID in the file. Before landing,
  every file, function, table and test name Part K names is grepped and fixed if it does not exist under that name
  (A.U36.543 (11)).
- **Resolved**: AC3_S S-13 summarises the body as "read Part 0 and Part K in order, then apply Part D"; A.U36.543 (9)'s
  own text (AC3_R R-04's wording) is written — Part K's steps already apply Part D (A.U36.543's K rewrite), so the skill
  adds no separate Part D step.
- **Unit**: U36 (after M.SPEC.142).
- **Depends**: M.SPEC.142, M.SPEC.046.
- **Blast carried by**: README map entry → M.DOCS.060; the two baseline runs → M.PROC.048.
- **Kind**: doc

## Gaps for other clusters

1. **SPEC** — (a) F.2 states the built timeout mechanism (`asyncio.wait_for_ms` around the one awaitable that can wait,
   A.U10.26, U10); A.U14.16's later F.2 sentence "are to share one mechanism, not yet built (BACKLOG)" is stale by its own
   landing (U14 > U10) and its BACKLOG pointer has no target (M.DOCS.062). (b) C.7's pointer to BACKLOG item 32 (A.U19.14)
   goes at U33, when the item becomes an owed row (M.DOCS.063). (c) BACKLOG facts that leave at U37 need their SPEC homes
   in place first: item 3 → F.1 and the Part F intro; item 2 → L.7; SPI RX overrun → F.5.2; the UART-fakes entry and the
   four UART findings → C.3.2, J.9, G.2; the standalone-mypy `Timer()` note → B.15 (M.DOCS.063, M.DOCS.065). (d) The Part F
   intro checklist (A.U36.023 (1)) names `tests_hardware/README.md`'s Workarounds table, as CLAUDE.md's pointer does
   (A.U26.65; M.DOCS.070). (e) I.4(f.1)'s run-phase figure sentence takes A.U30.10's description (largest free block 80 %
   of free four seconds after the task-starter list at `gc.threshold(32768)`, 12 % at the reactive default; `dev`,
   v1.29.0, 2026-09-19; archive §7H.3) in place of A.U36.546's "recorded 2026-09-21" (M.DOCS.089). (f) B.17 receives the
   recipe with A.U0.39's "(owner, 2026-09-11)" on "Two targets, both required" and A.U21.16's trixie-paragraph wording
   (M.DOCS.106). (g) CLAUDE.md's tag-line pointer names L.6.4 and H.5.1 (AC_NOTES 9, M.DOCS.092): SPEC adds no duplicate
   `@web` rows to L.6.4, or tells DOCS to drop the H.5.1 half. (h) J.7's tier map names the two L2 twin UART files
   (M_TWIN gap; CLAUDE.md points there, M.DOCS.085). (i) SPEC J.7 and F.7 row 12 cite CLAUDE.md's "Known hang cause"; the
   bullet keeps the phrase "(the known hang cause)" (M.DOCS.099).
2. **TSC, SCR, TWIN** — BACKLOG item 24 is deleted at U19 (A.U19.14); its citers repoint to SPEC C.7 in the same unit:
   `tests_scripts/test_request_timeout_ceiling.py:88`, `tests_scripts/test_digital_twin_ci_suite_errcount.py:259` (TSC);
   `scripts/_digital_twin_ci_suite.py:110` (SCR); `digital_twin/README.md:669` (TWIN, which names the item by title).
3. **HW_BENCH** — the tier-parity rule leaves BACKLOG at U37 (M.DOCS.062 (g)); `tests_hardware/README.md`'s `:1188`
   section must state the rule itself with its tags (A.U0.21), not only its heading. The owed-list intro cites
   "How a round runs" (A.U36.001) and the Workarounds table needs its "last checked" column (A.U26.65).
4. **TOOL** — CLAUDE.md's CI bullet job list is read against U28's final `ci.yml` at U36 (M.DOCS.095); M_TOOL gap 7's
   per-unit chroot lines are carried (M.DOCS.066).
5. **PROC** — carried: the "Last run" re-date (M.PROC.031 → M.DOCS.070), the hold-back and parked entries (M.PROC.008
   (4)-(5) → M.DOCS.067), A.U1.02 → M.PROC.014 (ledger). A.U25.65's BACKLOG pointer (M_PROC gap 3(c)): no BACKLOG owed row
   matches the item `digital_twin/README.md:453-456` cites, so that sentence goes (TWIN).

**Incoming gaps, gap pass G1 (2026-10-01, `audit/consolidation/GAPS_G1.md`)**: every item naming DOCS re-read in its
carrying change. Amended: M.DOCS.071 and M.DOCS.070's Blast ("F.5.10" → "F.9", M_SPEC gap 1), M.DOCS.092 (the H.5.1
half dropped, M_SPEC gap 2), M.DOCS.065 (the UART findings' SPEC homes as M.SPEC.050/.137/.138/.111 land them), and
M.DOCS.048 (the owner's pronoun). Carried as found: M_SRC_CORE GAP-G7 / M_SRC_SENS GAP-10 (M.DOCS.090), M_SRC_NET gap 6
(M.DOCS.024), M_TOOL gap 7, M_SCR gap 6 and M_WEB gap 8 (M.DOCS.066, M.DOCS.101), M_TSC gap 2 (M.DOCS.048), M_PROC gap
3 (M.DOCS.060/.067/.070; (c) disposed above). M_TWIN's DOCS item is settled by M.DOCS.085/.101.
GAPS_G4 hand-off 1 (the rollover runner, M.SCR.074): M.DOCS.049, M.DOCS.052 and M.DOCS.066 amended.
GAPS_G2 H-6: the UART attributes G2 made private join B39 (M.DOCS.024). GAPS_G3 hand-off 5: M.DOCS.053's tag example.
Pointer sweep (GAPS_G1 table B): M.DOCS.026, .064, .071, .084, .089 and .090 amended.

## Adherence findings

- README runbook (M.DOCS.048): the legacy hotspot password literal is not copied into a doc; the runbook points to the
  legacy file (CLAUDE.md credentials rule) — breach avoided, recorded.
- UART changelog A7 (M.DOCS.021): a "Status as merged" sentence would state a dead mechanism once the CRC mode is a TOML
  key (A.S0930.01) — rewritten as "Status as built" (docs hold current state).
- HEAP_FRAGMENTATION §M5.2 (M.DOCS.035): the build list lacked the third Unix build — added (current state).
- HEAP_FRAGMENTATION front matter (M.DOCS.040): named I.2 by its HEAD title, which A.U30.02 changes — renamed.
- README twin section (M.DOCS.058): dated counts ("fourteen sequential runs", "any of the other 5") cut (G9/R11).
- BACKLOG streaming-GET item (A.U36.548 (3)): an agent-deferred goal breaks the four-kinds rule — entered as owner
  question 2 (M.DOCS.067).
- BACKLOG Wi-Fi locking item: its rename is done at U10, so the item leaves then, not at U36 (M.DOCS.065).
- CLAUDE.md intro (M.DOCS.068): "BACKLOG.md's open-questions/deferred-work list" contradicts BACKLOG's end state —
  corrected.
- CLAUDE.md UART bullet (M.DOCS.076): the Class-A-by-definition clause would appear twice — once.
- CLAUDE.md tunables bullet (M.DOCS.105): A.U8.01's text cites an owner-row ID — written with the owner's date instead
  (G9/R12).

## Owner questions

None raised. Every conflict in this cluster was settled from an owner row, AC_NOTES, a later action or the standing
rules; the decisions taken on the owner's behalf are listed below for the OR2.c review.

## Agent decisions for the OR2.c review

1. M.DOCS.014 / M.DOCS.068: the datasheets-location text is written only after the owner's push-access step
   (AC_NOTES 37, M.PROC.018). Satisfied: standing push permission (owner, 2026-10-05; OR144.a; A-C review fold).
2. M.DOCS.021: A7's "Status as built" sentence for the TOML `crc` key (adherence above).
3. M.DOCS.035: the third Unix build named in HEAP_FRAGMENTATION's build list.
4. M.DOCS.048: the legacy hotspot password replaced by a pointer.
5. M.DOCS.059: release version `2.0` (A.U37.11; the brief's "agent decision under review").
6. M.DOCS.062 (g): the tier-parity rule leaves BACKLOG for `tests_hardware/README.md`, which already carries it with
   the same owner tags.
7. M.DOCS.065: config-duplication item removed at U37 as stale (single source: each reader's schema and the generated
   definitions); network-fault-injection item removed at U35 (its open recombination is A.U35.09's); the chroot list kept
   under "Deferred goals" as the owner-run periodic check (owner, 2026-09-18).
8. M.DOCS.067: the streaming-GET item entered as owner question 2 with options, not as a deferred goal.
9. M.DOCS.068: CLAUDE.md intro clause corrected to "(BACKLOG.md included)".
10. M.DOCS.075: the "~441 lines" count deleted at U0 instead of re-measured (A.SDEP.06), so no stale figure stands until U36.
11. M.DOCS.076: the duplicated Class-A clause kept once.
12. M.DOCS.093: A.U36.018's "entered in BACKLOG.md with its reason" → "entered in BACKLOG.md's owner-question list or
    owed list with its reason" (BACKLOG's four kinds).
13. M.DOCS.095: CLAUDE.md's CI job list checked against `ci.yml` at U36.
14. M.DOCS.099: "(the known hang cause)" kept in the bounded-fake bullet so the fake comments' citation resolves.
15. M.DOCS.108: the Microdot section's version removed, the tag named only in THIRD_PARTY_LICENSES.md (A.U36.030's rule
    applied to the second mention).

## Ledger

Every action indexed to a DOCS file (`site_index.json` `by_file`; BL BACKLOG, CL CLAUDE, DR DEVICE_REFERENCE, HF
HEAP_FRAGMENTATION_MEASUREMENTS, PAP PROJECT_AUDIT_PLAN, RM README, TPL THIRD_PARTY_LICENSES, UCL UART_C_PORT_CHANGELOG), and
every extra action the slot scan found and merged ("extra"). Indexed: 168, each with a merged block or a recorded
disposition. The merged-in column lists the blocks whose From line names the action.

| Action | File(s) | Merged in | Note |
|---|---|---|---|
| A.C.04 | extra | M.DOCS.064 | merged |
| A.U2.08 | extra (gap pass G1) | M.DOCS.090 | merged (`:391` example) |
| A.U7.21 | extra (gap pass G1) | M.DOCS.089 | merged (gate list by name) |
| A.U7.22 | extra (gap pass G1) | M.DOCS.089 | merged |
| A.U7.23 | extra (gap pass G1) | M.DOCS.089 | merged |
| A.U19.19 | extra (gap pass G1) | M.DOCS.071 | merged (A.5 pointer) |
| A.U26.84 | extra (gap pass G1) | M.DOCS.026 | merged (readiness defaults cited) |
| A.C.10 | extra (gap pass G1) | M.DOCS.064 | merged (phase-C removals) |
| A.S0930.01 | extra | M.DOCS.021 | merged |
| A.S0930.07 | UCL | M.DOCS.024 | merged |
| A.S0930.08 | extra | M.DOCS.085 | merged |
| A.S0930.19 | extra | M.DOCS.086 | merged |
| A.S0930.30 | CL | M.DOCS.086, M.DOCS.090 | merged |
| A.SDEP.03 | extra | M.DOCS.104 | merged |
| A.SDEP.04 | extra | M.DOCS.047 | merged |
| A.SDEP.06 | TPL | M.DOCS.002, M.DOCS.075, M.DOCS.108 | CLAUDE.md "~441 lines" re-measure dropped (count deleted, A.U36.030) |
| A.SDEP.07 | TPL | M.DOCS.003, M.DOCS.064 | merged |
| A.SDEP.08 | HF | M.DOCS.012, M.DOCS.034, M.DOCS.064, M.DOCS.067 | merged |
| A.SDEP.11 | extra | M.DOCS.035, M.DOCS.066, M.DOCS.100 | merged |
| A.SDEP.15 | extra | M.DOCS.105 | merged |
| A.SDEP.16 | extra | M.DOCS.065, M.DOCS.099, M.DOCS.100, M.DOCS.103 | merged |
| A.SDEP.17 | extra | M.DOCS.069, M.DOCS.084, M.DOCS.099 | merged |
| A.SDEP.19 | extra | M.DOCS.065, M.DOCS.070, M.DOCS.095, M.DOCS.098 | merged |
| A.SDEP.21 | CL, TPL | M.DOCS.002, M.DOCS.003, M.DOCS.061, M.DOCS.064, M.DOCS.066, M.DOCS.067, M.DOCS.069, M.DOCS.070 | merged |
| A.SDEP.22 | CL | M.DOCS.069, M.DOCS.071 | merged |
| A.SDEP.24 | PAP | M.DOCS.041 | merged |
| A.SDEP.25 | extra | M.DOCS.059 | merged |
| A.U0.01 | BL | M.DOCS.064 | merged |
| A.U0.02 | PAP | M.DOCS.042 | merged |
| A.U0.06 | PAP | M.DOCS.041 | merged |
| A.U0.10 | CL | M.DOCS.091 | merged |
| A.U0.11 | CL | M.DOCS.093 | merged |
| A.U0.12 | BL | M.DOCS.061, M.DOCS.065, M.DOCS.067 | merged |
| A.U0.13 | BL, CL | M.DOCS.062, M.DOCS.094 | merged |
| A.U0.14 | BL | M.DOCS.065 | merged |
| A.U0.21 | BL | M.DOCS.062 | merged |
| A.U0.22 | BL, CL | M.DOCS.062, M.DOCS.065, M.DOCS.081 | getaddrinfo sentence replaced by A.U14.16 wording |
| A.U0.23 | CL | M.DOCS.076, M.DOCS.078, M.DOCS.084, M.DOCS.096, M.DOCS.106, M.DOCS.107 | merged |
| A.U0.24 | RM | M.DOCS.045 | merged |
| A.U0.26 | BL | M.DOCS.063, M.DOCS.065 | merged |
| A.U0.27 | HF | M.DOCS.036 | merged |
| A.U0.30 | UCL | M.DOCS.016, M.DOCS.021 | merged |
| A.U0.32 | CL | M.DOCS.070, M.DOCS.076, M.DOCS.077, M.DOCS.078, M.DOCS.080, M.DOCS.082, M.DOCS.088 | merged |
| A.U0.34 | BL | M.DOCS.062, M.DOCS.063, M.DOCS.064, M.DOCS.065, M.DOCS.077 | merged |
| A.U0.36 | DR, RM | M.DOCS.031, M.DOCS.051 | merged |
| A.U0.37 | BL, CL | M.DOCS.062, M.DOCS.065, M.DOCS.075, M.DOCS.085, M.DOCS.086, M.DOCS.087, M.DOCS.090, M.DOCS.091, M.DOCS.098 | merged |
| A.U0.38 | UCL | M.DOCS.016, M.DOCS.060, M.DOCS.062, M.DOCS.063, M.DOCS.064, M.DOCS.065, M.DOCS.073, M.DOCS.076, M.DOCS.083, M.DOCS.102 | V33 BACKLOG text dropped (A.U36.028 deletes the clause); other parts merged |
| A.U0.39 | BL, CL, UCL | M.DOCS.021, M.DOCS.065, M.DOCS.102, M.DOCS.103, M.DOCS.106 | merged |
| A.U0.40 | CL | M.DOCS.095, M.DOCS.100 | merged |
| A.U0.42 | RM | M.DOCS.060 | merged |
| A.U0.43 | CL | M.DOCS.089 | merged |
| A.U0.45 | CL | M.DOCS.088 | merged |
| A.U0.46 | HF | M.DOCS.038 | merged |
| A.U0.47 | UCL | M.DOCS.025 | merged |
| A.U0.55 | CL | M.DOCS.098 | merged |
| A.U0.57 | CL | M.DOCS.102 | merged |
| A.U0.58 | BL | M.DOCS.065, M.DOCS.066 | not void: A.U5.17 keeps the max-args item until the owner run |
| A.U1.02 | RM | — | no README edit (parser hit on its Site text); carried by M.PROC.014 (M_PROC gap 3(e)) |
| A.U1.05 | RM | M.DOCS.047 | merged |
| A.U1.06 | RM | M.DOCS.056 | merged |
| A.U1.10 | CL | M.DOCS.079 | merged |
| A.U1.11 | CL | M.DOCS.074 | merged |
| A.U1.12 | CL | M.DOCS.069, M.DOCS.072, M.DOCS.075, M.DOCS.080, M.DOCS.084, M.DOCS.088, M.DOCS.094, M.DOCS.102 | merged |
| A.U1.13 | RM | M.DOCS.045, M.DOCS.047, M.DOCS.053, M.DOCS.056, M.DOCS.060 | merged |
| A.U1.19 | BL | M.DOCS.062, M.DOCS.063, M.DOCS.065 | merged |
| A.U1.20 | extra | M.DOCS.002, M.DOCS.005, M.DOCS.009, M.DOCS.010, M.DOCS.012, M.DOCS.013 | merged |
| A.U10.04 | extra | M.DOCS.024 | merged |
| A.U10.07 | extra | M.DOCS.064 | merged |
| A.U10.09 | BL | M.DOCS.062 | merged |
| A.U10.18 | extra | M.DOCS.023, M.DOCS.024, M.DOCS.065 | merged |
| A.U10.23 | BL | M.DOCS.062 | merged |
| A.U10.26 | BL | M.DOCS.062 | merged |
| A.U10.29 | extra | M.DOCS.024 | merged |
| A.U10.35 | extra | M.DOCS.024 | merged |
| A.U10.37 | extra | M.DOCS.001, M.DOCS.010, M.DOCS.013, M.DOCS.021, M.DOCS.023, M.DOCS.024, M.DOCS.051, M.DOCS.076 | merged |
| A.U10.38 | extra | M.DOCS.001, M.DOCS.006, M.DOCS.010, M.DOCS.013, M.DOCS.021, M.DOCS.023, M.DOCS.024, M.DOCS.076 | merged |
| A.U10.40 | extra | M.DOCS.027, M.DOCS.029, M.DOCS.031, M.DOCS.051 | merged |
| A.U10.41 | BL | M.DOCS.065 | merged |
| A.U10.44 | extra | M.DOCS.024 | merged |
| A.U10.45 | extra | M.DOCS.024 | merged |
| A.U11.10 | CL | M.DOCS.066, M.DOCS.089 | merged |
| A.U11.19 | extra | M.DOCS.051 | merged |
| A.U11.31 | extra | M.DOCS.024 | merged |
| A.U11.36 | RM | M.DOCS.051 | merged |
| A.U11.38 | extra | M.DOCS.066 | merged |
| A.U11.S03 | extra | M.DOCS.066 | merged |
| A.U12.02 | extra | M.DOCS.024 | merged |
| A.U12.03 | extra | M.DOCS.024 | merged |
| A.U12.16 | extra | M.DOCS.024 | merged |
| A.U13.01 | BL | M.DOCS.065 | merged |
| A.U13.04 | extra | — | dropped from M.DOCS.064 (withdrawn as a measurement, AC_NOTES 11; AC3 R-03): no BACKLOG row |
| A.U13.06 | BL | M.DOCS.065 | merged |
| A.U13.12 | extra | M.DOCS.024 | merged |
| A.U13.13 | extra | M.DOCS.024 | merged |
| A.U13.14 | extra | M.DOCS.024 | merged |
| A.U13.17 | extra | M.DOCS.024 | merged |
| A.U13.18 | extra | M.DOCS.024 | merged |
| A.U13.R02 | extra | M.DOCS.064 | merged |
| A.U14.01 | extra | M.DOCS.063 | merged |
| A.U14.12 | CL | M.DOCS.064, M.DOCS.099 | (3) CLAUDE.md `:647` re-wording superseded (sentence deleted, A.U36.546) |
| A.U14.16 | BL | M.DOCS.062, M.DOCS.065 | BACKLOG `:60-61` edit void (item removed at U10, A.U10.26); wording carried into the deferred goal, M.DOCS.065 |
| A.U14.17 | extra | M.DOCS.026, M.DOCS.064 | merged |
| A.U14.18 | CL | M.DOCS.099 | merged |
| A.U14.23 | BL | M.DOCS.063 | merged |
| A.U14.R01 | CL | M.DOCS.026, M.DOCS.063, M.DOCS.065, M.DOCS.081 | merged |
| A.U15.02 | extra | M.DOCS.065 | merged |
| A.U15.06 | BL | M.DOCS.065 | merged |
| A.U15.08 | extra | M.DOCS.064 | merged |
| A.U15.11 | extra | M.DOCS.026 | merged |
| A.U15.12 | extra | M.DOCS.026 | merged |
| A.U15.17 | DR | M.DOCS.030 | merged |
| A.U15.20 | extra | M.DOCS.064 | merged |
| A.U15.36 | extra | M.DOCS.031 | merged |
| A.U15.39 | DR | M.DOCS.031 | merged |
| A.U15.42 | BL | M.DOCS.065 | merged |
| A.U16.04 | BL | M.DOCS.062 | merged |
| A.U16.05 | extra | M.DOCS.023, M.DOCS.024 | merged |
| A.U16.07 | BL | M.DOCS.064 | merged |
| A.U16.18 | DR | M.DOCS.030 | merged |
| A.U17.01 | extra | M.DOCS.024 | merged |
| A.U17.03 | extra | M.DOCS.067 | merged |
| A.U17.06 | extra | M.DOCS.024 | merged |
| A.U17.08 | UCL | M.DOCS.015, M.DOCS.018, M.DOCS.060, M.DOCS.076 | merged |
| A.U17.09 | UCL | M.DOCS.019, M.DOCS.021 | merged |
| A.U17.10 | UCL | M.DOCS.024 | merged |
| A.U17.11 | UCL | M.DOCS.020 | merged |
| A.U17.13 | extra | M.DOCS.023 | merged |
| A.U17.14 | extra | M.DOCS.024 | merged |
| A.U17.15 | UCL | M.DOCS.023 | merged |
| A.U17.16 | extra | M.DOCS.022 | merged |
| A.U17.17 | extra | M.DOCS.022 | merged |
| A.U17.20 | extra | M.DOCS.024 | merged |
| A.U17.22 | extra | M.DOCS.024 | merged |
| A.U17.25 | extra | M.DOCS.085 | merged |
| A.U17.26 | extra | M.DOCS.024 | merged |
| A.U17.28 | extra | M.DOCS.024 | merged |
| A.U17.30 | UCL | M.DOCS.022, M.DOCS.024 | merged |
| A.U18.01 | extra | M.DOCS.010 | merged |
| A.U18.02 | extra | M.DOCS.010 | merged |
| A.U18.10 | extra | M.DOCS.028 | merged |
| A.U18.13 | extra | M.DOCS.013 | merged |
| A.U18.20 | extra | M.DOCS.028 | merged |
| A.U18.21 | extra | M.DOCS.028 | merged |
| A.U18.30 | extra | M.DOCS.027 | merged |
| A.U18.35 | DR | M.DOCS.028 | merged |
| A.U18.43 | extra | M.DOCS.064 | merged |
| A.U18.46 | extra | M.DOCS.013 | merged |
| A.U19.05 | extra | M.DOCS.066 | merged |
| A.U19.14 | BL, DR | M.DOCS.026, M.DOCS.032, M.DOCS.063 | merged |
| A.U19.17 | extra | M.DOCS.066 | merged |
| A.U19.18 | TPL | M.DOCS.002 | merged |
| A.U2.09 | extra | M.DOCS.065 | merged |
| A.U2.12 | extra | M.DOCS.063 | merged |
| A.U2.14 | extra | M.DOCS.063 | merged |
| A.U2.20 | extra | M.DOCS.024 | merged |
| A.U2.23 | extra | M.DOCS.062, M.DOCS.063, M.DOCS.064 | merged |
| A.U2.26 | UCL | M.DOCS.024 | merged |
| A.U20.05 | extra | M.DOCS.048 | merged |
| A.U20.14 | extra | M.DOCS.066 | merged |
| A.U20.33 | extra | M.DOCS.066 | merged |
| A.U21.02 | extra | M.DOCS.052 | merged |
| A.U21.03 | extra | M.DOCS.047 | merged |
| A.U21.09 | extra | M.DOCS.065, M.DOCS.066, M.DOCS.070 | merged |
| A.U21.12 | extra | M.DOCS.047 | merged |
| A.U21.14 | BL | M.DOCS.064 | merged |
| A.U21.16 | CL | M.DOCS.066, M.DOCS.106 | merged |
| A.U21.19 | extra | M.DOCS.047, M.DOCS.052 | merged |
| A.U21.21 | extra | M.DOCS.047 | merged |
| A.U21.23 | extra | M.DOCS.064 | merged |
| A.U21.24 | extra | M.DOCS.047 | merged |
| A.U21.26 | extra | M.DOCS.047 | merged |
| A.U21.27 | extra | M.DOCS.047 | merged |
| A.U21.28 | extra | M.DOCS.047, M.DOCS.056 | merged |
| A.U23.07 | extra | M.DOCS.065 | merged |
| A.U24.15 | extra | M.DOCS.099 | merged |
| A.U24.52 | extra | M.DOCS.049, M.DOCS.055 | merged |
| A.U24.65 | extra | M.DOCS.049 | merged |
| A.U24.67 | extra | M.DOCS.024 | merged |
| A.U24.68 | extra | M.DOCS.050, M.DOCS.051, M.DOCS.052, M.DOCS.058 | merged |
| A.U24.69 | extra | M.DOCS.101 | merged |
| A.U24.71 | CL | M.DOCS.103 | merged |
| A.U24.72 | extra | M.DOCS.050, M.DOCS.054, M.DOCS.066 | merged |
| A.U25.01 | extra | M.DOCS.064 | merged |
| A.U25.08 | extra | M.DOCS.064 | merged |
| A.U25.09 | extra | M.DOCS.051 | merged |
| A.U25.10 | extra | M.DOCS.064 | merged |
| A.U25.12 | extra | M.DOCS.064 | merged |
| A.U25.14 | extra | M.DOCS.064 | merged |
| A.U25.32 | extra | M.DOCS.051 | merged |
| A.U25.46 | extra | M.DOCS.058 | merged |
| A.U25.48 | extra | M.DOCS.049, M.DOCS.058 | merged |
| A.U25.64 | extra | M.DOCS.067 | merged |
| A.U26.02 | extra | M.DOCS.048 | merged |
| A.U26.05 | extra | M.DOCS.037 | merged |
| A.U26.19 | BL | — | no BACKLOG edit of its own: the loose-ends entry it cites is deleted at U33 by A.U33.07 (M.DOCS.064); its U26 line in the chroot list, M.DOCS.066 |
| A.U26.28 | extra | M.DOCS.064 | merged |
| A.U26.35 | extra | M.DOCS.049, M.DOCS.052, M.DOCS.057, M.DOCS.064 | merged |
| A.U26.36 | extra | M.DOCS.064 | merged |
| A.U26.65 | extra | M.DOCS.070 | merged |
| A.U26.72 | extra | M.DOCS.064 | merged |
| A.U26.74 | BL, CL, RM | M.DOCS.049, M.DOCS.052, M.DOCS.057, M.DOCS.066, M.DOCS.086 | merged |
| A.U26.79 | BL | M.DOCS.064 | merged |
| A.U26.85 | extra | M.DOCS.064 | merged |
| A.U27.02 | extra | M.DOCS.105 | merged |
| A.U27.03 | extra | M.DOCS.105 | merged |
| A.U27.08 | extra | M.DOCS.049, M.DOCS.050, M.DOCS.055 | merged |
| A.U27.09 | extra | M.DOCS.094 | merged |
| A.U27.12 | extra | M.DOCS.047, M.DOCS.097 | merged |
| A.U27.13 | extra | M.DOCS.056 | merged |
| A.U27.17 | extra | M.DOCS.067 | merged |
| A.U27.19 | extra | M.DOCS.049 | merged |
| A.U27.20 | extra | M.DOCS.103 | merged |
| A.U27.21 | extra | M.DOCS.089 | merged |
| A.U27.22 | extra | M.DOCS.103 | merged |
| A.U27.23 | extra | M.DOCS.094 | merged |
| A.U27.24 | extra | M.DOCS.094 | merged |
| A.U27.25 | extra | M.DOCS.094 | merged |
| A.U27.26 | extra | M.DOCS.050, M.DOCS.053, M.DOCS.094 | merged |
| A.U27.35 | extra | M.DOCS.048 | merged |
| A.U27.36 | extra | M.DOCS.048, M.DOCS.052 | merged |
| A.U27.39 | extra | M.DOCS.050 | merged |
| A.U28.02 | extra | M.DOCS.047, M.DOCS.053, M.DOCS.064 | merged |
| A.U28.06 | extra | M.DOCS.053, M.DOCS.055 | merged |
| A.U28.10 | CL | M.DOCS.098 | merged |
| A.U28.11 | CL | M.DOCS.098, M.DOCS.107 | merged |
| A.U28.15 | extra | M.DOCS.050, M.DOCS.054 | merged |
| A.U28.16 | extra | M.DOCS.050, M.DOCS.054 | merged |
| A.U28.17 | extra | M.DOCS.050, M.DOCS.055 | merged |
| A.U28.20 | extra | M.DOCS.047, M.DOCS.064 | merged |
| A.U28.24 | extra | M.DOCS.050, M.DOCS.055 | merged |
| A.U28.34 | CL | M.DOCS.096 | merged |
| A.U28.38 | BL | M.DOCS.066 | merged |
| A.U28.40 | CL | M.DOCS.095 | merged |
| A.U29.01 | extra | M.DOCS.044 | merged |
| A.U29.03 | CL | M.DOCS.080 | merged |
| A.U3.02 | extra | M.DOCS.024 | merged |
| A.U3.04 | extra | M.DOCS.065 | merged |
| A.U3.06 | extra | M.DOCS.064 | merged |
| A.U3.08 | extra | M.DOCS.024 | merged |
| A.U3.13 | UCL | M.DOCS.024 | merged |
| A.U30.01 | CL | M.DOCS.083 | merged |
| A.U30.02 | BL | M.DOCS.040, M.DOCS.065, M.DOCS.067 | merged |
| A.U30.10 | CL | M.DOCS.089 | merged |
| A.U30.14 | extra | M.DOCS.066, M.DOCS.089 | merged |
| A.U30.16 | extra | M.DOCS.066 | merged |
| A.U30.17 | CL | M.DOCS.089 | merged |
| A.U30.19 | extra | M.DOCS.024 | merged |
| A.U31.01 | extra | M.DOCS.084 | merged |
| A.U31.03 | extra | M.DOCS.064, M.DOCS.084 | merged |
| A.U31.05 | extra | M.DOCS.064 | merged |
| A.U31.06 | BL | M.DOCS.064 | merged |
| A.U32.01 | RM | M.DOCS.026, M.DOCS.048, M.DOCS.060 | merged |
| A.U32.02 | RM | M.DOCS.044 | merged |
| A.U32.06 | extra | M.DOCS.024 | merged |
| A.U33.03 | BL | M.DOCS.065 | merged |
| A.U33.04 | BL | M.DOCS.066 | merged |
| A.U33.05 | BL | M.DOCS.065 | merged |
| A.U33.06 | CL | M.DOCS.102 | merged |
| A.U33.07 | BL | M.DOCS.064, M.DOCS.065 | merged |
| A.U33.09 | BL | M.DOCS.061, M.DOCS.063, M.DOCS.064, M.DOCS.065 | merged |
| A.U34.01 | TPL | M.DOCS.001 | merged |
| A.U34.02 | RM, TPL | M.DOCS.060 | merged |
| A.U34.03 | TPL | M.DOCS.004, M.DOCS.005, M.DOCS.007, M.DOCS.009 | merged |
| A.U34.04 | TPL | M.DOCS.008 | merged |
| A.U34.05 | TPL | M.DOCS.010 | merged |
| A.U34.06 | TPL | M.DOCS.013 | merged |
| A.U34.07 | TPL | — | no THIRD_PARTY edit; its one-entry check constrains M.DOCS.005/.013 entry form (TSC) |
| A.U34.08 | TPL | M.DOCS.003, M.DOCS.066 | merged |
| A.U34.09 | TPL | M.DOCS.011, M.DOCS.014 | merged |
| A.U34.10 | TPL | M.DOCS.009 | merged |
| A.U34.11 | extra | M.DOCS.066 | merged |
| A.U34.12 | TPL | M.DOCS.002 | merged |
| A.U35.09 | extra | M.DOCS.065 | merged |
| A.U35.27 | extra | M.DOCS.067 | merged |
| A.U35.44 | extra | M.DOCS.024 | merged |
| A.U35.54 | extra | M.DOCS.064 | merged |
| A.U35.57 | BL | M.DOCS.066 | merged |
| A.U36.001 | BL | M.DOCS.064 | merged |
| A.U36.002 | CL | M.DOCS.090 | merged |
| A.U36.008 | RM | M.DOCS.049, M.DOCS.057 | merged |
| A.U36.010 | RM | M.DOCS.048 | merged |
| A.U36.013 | HF | M.DOCS.039 | merged |
| A.U36.014 | CL | M.DOCS.085 | merged |
| A.U36.017 | CL | M.DOCS.093 | merged |
| A.U36.018 | CL | M.DOCS.093 | merged |
| A.U36.019 | CL | M.DOCS.068 | merged |
| A.U36.021 | CL | M.DOCS.093 | merged |
| A.U36.023 | CL | M.DOCS.070 | merged |
| A.U36.024 | RM | M.DOCS.049, M.DOCS.050, M.DOCS.058 | merged |
| A.U36.025 | CL, UCL | M.DOCS.017, M.DOCS.076 | merged |
| A.U36.027 | BL | M.DOCS.065 | merged |
| A.U36.028 | BL | M.DOCS.062 | merged; supersedes A.U0.38 V33 |
| A.U36.029 | DR | M.DOCS.029 | merged |
| A.U36.030 | CL, TPL | M.DOCS.002, M.DOCS.075, M.DOCS.108 | merged |
| A.U36.034 | CL | M.DOCS.082 | merged |
| A.U36.035 | BL | M.DOCS.063 | merged |
| A.U36.037 | CL | M.DOCS.100 | merged |
| A.U36.042 | BL | M.DOCS.065 | merged |
| A.U36.043 | CL | M.DOCS.094 | merged |
| A.U36.503 | extra | M.DOCS.032 | merged |
| A.U36.511 | DR, RM | M.DOCS.031, M.DOCS.050, M.DOCS.051, M.DOCS.058 | merged |
| A.U36.512 | CL, RM | M.DOCS.047, M.DOCS.052, M.DOCS.066, M.DOCS.078, M.DOCS.085, M.DOCS.097 | merged |
| A.U36.516 | BL, RM | M.DOCS.050, M.DOCS.055, M.DOCS.065 | merged |
| A.U36.517 | extra | M.DOCS.055 | merged |
| A.U36.521 | BL | M.DOCS.065 | merged |
| A.U36.522 | RM | M.DOCS.047 | merged |
| A.U36.524 | BL, CL, RM | M.DOCS.060, M.DOCS.066, M.DOCS.095, M.DOCS.106, M.DOCS.107 | merged |
| A.U36.525 | CL | M.DOCS.091 | merged |
| A.U36.526 | CL, RM | M.DOCS.050, M.DOCS.053, M.DOCS.054, M.DOCS.097 | merged |
| A.U36.527 | BL, CL | M.DOCS.062, M.DOCS.103 | merged |
| A.U36.528 | CL | M.DOCS.104 | merged |
| A.U36.529 | CL | M.DOCS.093 | merged |
| A.U36.531 | DR | M.DOCS.026 | merged |
| A.U36.532 | extra | M.DOCS.023, M.DOCS.064, M.DOCS.084 | merged |
| A.U36.533 | CL | M.DOCS.092 | merged |
| A.U36.534 | CL | M.DOCS.102 | merged |
| A.U36.536 | CL | M.DOCS.091, M.DOCS.107 | merged |
| A.U36.537 | extra | M.DOCS.030 | merged |
| A.U36.539 | CL | M.DOCS.085 | merged |
| A.U36.540 | CL | M.DOCS.072, M.DOCS.073, M.DOCS.091 | merged |
| A.U36.541 | CL, RM | M.DOCS.060, M.DOCS.084, M.DOCS.108 | merged |
| A.U36.542 | CL | M.DOCS.073 | merged |
| A.U36.543 | RM | M.DOCS.060, M.DOCS.109 | merged; (9), (11) → M.DOCS.109 (AC3 R-04, S-13); (10) → M.PROC.048 |
| A.U36.544 | extra | M.DOCS.023, M.DOCS.061, M.DOCS.063, M.DOCS.064, M.DOCS.065, M.DOCS.066, M.DOCS.067, M.DOCS.074, M.DOCS.075, M.DOCS.082, M.DOCS.096 | `BACKLOG.md:793` repoint void (entry deleted at U33, A.U33.09); rest merged |
| A.U36.545 | CL, RM | M.DOCS.047, M.DOCS.060, M.DOCS.068 | merged |
| A.U36.546 | BL, CL, DR, RM | M.DOCS.027, M.DOCS.030, M.DOCS.033, M.DOCS.060, M.DOCS.061, M.DOCS.086, M.DOCS.088, M.DOCS.089, M.DOCS.097, M.DOCS.099, M.DOCS.100, M.DOCS.101, M.DOCS.105 | merged |
| A.U36.547 | RM | M.DOCS.045, M.DOCS.046, M.DOCS.047, M.DOCS.048, M.DOCS.049, M.DOCS.050, M.DOCS.052, M.DOCS.060 | merged |
| A.U36.548 | BL, CL, RM | M.DOCS.053, M.DOCS.064, M.DOCS.065, M.DOCS.067, M.DOCS.075, M.DOCS.080, M.DOCS.094, M.DOCS.105 | (4) BACKLOG `:884-889` re-wording void (item removed at U10); (5) and CLAUDE parts merged |
| A.U36.549 | extra | M.DOCS.023, M.DOCS.081 | merged |
| A.U37.03 | PAP, UCL | M.DOCS.043, M.DOCS.060 | merged |
| A.U37.04 | BL, UCL | M.DOCS.060 | merged |
| A.U37.05 | BL | M.DOCS.064 | merged |
| A.U37.06 | BL | M.DOCS.060, M.DOCS.061, M.DOCS.062, M.DOCS.065 | merged |
| A.U37.08 | CL | M.DOCS.093 | merged |
| A.U37.11 | RM | M.DOCS.059 | merged |
| A.U37.12 | RM | M.DOCS.059 | merged |
| A.U37.15 | PAP, RM | M.DOCS.043, M.DOCS.060 | merged |
| A.U5.02 | extra | M.DOCS.024 | merged |
| A.U5.12 | extra | M.DOCS.024 | merged |
| A.U5.17 | extra | M.DOCS.066 | merged |
| A.U6.03 | extra | M.DOCS.048 | merged |
| A.U6.04 | extra | M.DOCS.048, M.DOCS.055 | merged |
| A.U6.06 | extra | M.DOCS.055, M.DOCS.063 | merged |
| A.U6.07 | extra | M.DOCS.050, M.DOCS.055 | merged |
| A.U7.01 | extra | M.DOCS.085 | merged |
| A.U7.02 | extra | M.DOCS.053 | merged |
| A.U7.03 | extra | M.DOCS.053 | merged |
| A.U7.06 | extra | M.DOCS.052 | merged |
| A.U7.07 | extra | M.DOCS.053 | merged |
| A.U7.09 | extra | M.DOCS.058 | merged |
| A.U7.11 | extra | M.DOCS.053 | merged |
| A.U7.12 | extra | M.DOCS.053 | merged |
| A.U7.14 | extra | M.DOCS.057 | merged |
| A.U7.17 | extra | M.DOCS.057 | merged |
| A.U7.18 | extra | M.DOCS.049, M.DOCS.057 | merged |
| A.U7.19 | extra | M.DOCS.052 | merged |
| A.U7.25 | extra | M.DOCS.062, M.DOCS.063 | merged |
| A.U7.26 | extra | M.DOCS.049 | merged |
| A.U8.01 | extra | M.DOCS.060, M.DOCS.105 | merged |
| A.U8.16 | extra | M.DOCS.052, M.DOCS.053 | merged |
| A.U8.23 | extra | M.DOCS.075, M.DOCS.103 | merged |
| A.U8.24 | extra | M.DOCS.103 | merged |
| A.U9.01 | extra | M.DOCS.027 | merged |
| A.U9.03 | extra | M.DOCS.027 | merged |
| A.C.01 | CL (extra) | — | cites CLAUDE.md rules (round frame); no edit |
| A.U26.01 | CL (extra) | — | "may cite" the bench-device key in the WoZi rule: not applied (optional), M.DOCS.078 unchanged |
| A.U27.14 | CL (extra) | — | "names no number (holds)"; no edit |
| AC3 O-22 | CL | M.DOCS.076 | "during this audit" → "until the C reconciliation" |
| AC3 O-22 (lead) | CL | M.DOCS.076, M.DOCS.060 | "post-audit" stays: it is the owner's own wording, fixed as the one Arduino form (A.U34.01, G6/R02 V01, this file's convention); it names a time, not the deleted `audit/` |
| AC3 O-23 | TPL | M.DOCS.008 | actor tag "(agent, 2026-08-20; …)" |
| AC3 O-28 | CL, RM | M.DOCS.078, M.DOCS.045 | "exemplary/base" role dropped (OR78.a); M.GEN.055 header carries the TOML half |
| AC3 R-03 | BL | M.DOCS.064 | A.U13.04 out of From; no FRAM-CS row |
| AC3 S section 4 | BL | M.DOCS.064 | From gains A.C.10 |
| AC3 S section 5 | CL | M.DOCS.085 | Blast pointer M.TWIN.153/.154 → M.TWIN.154/.156 |

## A-C2 order notes (2026-10-01)

Unit and Depends edits made by the A-C2 work order (`audit/order/WORK_ORDER.md`); one row per edit.

| M-ID | slot | edit | reason |
|---|---|---|---|
| M.DOCS.008 | Depends | appended: A-C2: M.DOCS.008 and M.DOCS.011 refer to each other and land in one U34 commit. | change-level cycle M.DOCS.008<->.011 settled as one co-landing commit |
| M.DOCS.011 | Depends | appended: A-C2: M.DOCS.008 and M.DOCS.011 refer to each other and land in one U34 commit. | change-level cycle M.DOCS.008<->.011 settled as one co-landing commit |
| M.DOCS.062 | Unit | appended: A-C2 step order: A.U10.09's part lands in U11, not U10 (it needs A.U11.03, which lands in U11). | dependency deferral (an edge ran from a later step) |
| M.DOCS.063 | Unit | appended: A-C2 step order: A.U2.12's part lands in U3, not U2 (it follows A.U2.12's own change, which lands in U3); A.U2.14's part lands in U3, not U2 (it follows A.U2.14's own change, which lands in U3); A.U14.R01's part lands in U18, not U14 (it follows A.U14.R01's own change, which lands in U18). | dependency deferral (an edge ran from a later step) |
| M.DOCS.065 | Unit | appended: A-C2 step order: A.U14.R01's part lands in U18, not U15 (it follows A.U14.R01's own change, which lands in U18). | dependency deferral (an edge ran from a later step) |
| M.DOCS.081 | Unit | appended: A-C2 step order: A.U14.R01's part lands in U18, not U14 (it needs A.U18.R01, which lands in U18). | dependency deferral (an edge ran from a later step) |

## A-C review fold (2026-10-05)

Folds the owner's review answers (OR136-OR143, `audit/actions/FOLD_ANSWERS.md`, the routine settlements of
`audit/review/routine_merge.json`, AC_NOTES 52) into the changes above, per `audit/actions/FOLD_BRIEF.md`. Every amended
change names its source in From with "(A-C review fold)"; no change is added. The standing convention "Review-answer
tags" (top of this file) fixes the tag form. `tests_hardware/README.md` and `digital_twin/README.md` are not this
file's (M_HW_BENCH, M_TWIN): their F01/F04/F13/F16/F20 wording is those agents'.

| Fnn | M-ID(s) | action |
|---|---|---|
| F01 | M.DOCS.082 (CLAUDE.md flash-write rule and Wi-Fi safety sentence), M.DOCS.086 (wear rule: the fresh-filesystem writes are prerequisites), M.DOCS.026 (DEVICE_REFERENCE: each file written once after "Reset to defaults") | amended |
| F02 | M.DOCS.032 (DEVICE_REFERENCE: the reset clears `HTTPDropped`) | amended |
| F03 | M.DOCS.026 (DEVICE_REFERENCE "Config Faults" item), M.DOCS.082 (CLAUDE.md: a damaged file is listed, deleted unread) | amended |
| F04 | M.DOCS.049 (README recipe: the rollover runner flashes the test image, ~2 h), M.DOCS.052 (command-line reference), M.DOCS.064 (BACKLOG G6 row), M.DOCS.066 (chroot list: the override at U21) | amended |
| F05 | M.DOCS.047 (README: throwaway password, passed plainly), M.DOCS.066 (chroot list) | amended |
| F06 | M.DOCS.064 (owed row gated), M.DOCS.086 (wear rule) | amended |
| F07 | M.DOCS.032 (the page confirms before the reset) | amended |
| F08 | — | none in this file |
| F09 | M.DOCS.027 (DEVICE_REFERENCE: try again later; internal notifications queue) | amended |
| F10 | M.DOCS.093 (CLAUDE.md parity bullet: the old work-in-progress folder as reference for the owner's intent) | amended |
| F11 | M.DOCS.065 (BACKLOG SPI RX entry: A.U3.04's U3 edit dropped) | amended |
| F12 | — | none in this file (A.U36.531's item in M.DOCS.026 already says "click the code for its meaning") |
| F13 | — | none in this file (`tests_hardware/README.md`, M_HW_BENCH) |
| F14 | M.DOCS.105 (CLAUDE.md stub bullet), M.DOCS.066 (chroot list names the check) | amended |
| F15 | — | none in this file |
| F16 | M.DOCS.064 (the NTP-outage hand-run row dropped: the twin's responder covers it) | amended |
| F17 | — | none in this file |
| F18 | — | none in this file |
| F19 | M.DOCS.027 (every Wi-Fi pattern follows `LEDWifiOn`) | amended |
| F20 | M.DOCS.078 (CLAUDE.md: the `dev`-exception rule replaces the WoZi rule), M.DOCS.076 (UART bullet's WoZi clause), M.DOCS.045 (README Devices), M.DOCS.048 (README flashing rule and runbook lead) | amended |
| F21 | the "Review-answer tags" convention; explicit in M.DOCS.011, .026, .048, .059 and the owner-ruling tags of F01-F27; the full map is the table below | tag |
| F22 | — | none in this file |
| F23 | — | none in this file (no doc here names dynamic imports) |
| F24 | — | none in this file |
| F25 | M.DOCS.024 (Class B rows B65, B67), M.DOCS.020 (constants table), M.DOCS.084 (CLAUDE.md no-block rule: clamp to the ring's fill level), M.DOCS.076 (UART bullet: DMA ring), M.DOCS.064 (receive-ring owed rows) | amended |
| F26 | M.DOCS.064 (hand-run rows: three kept, two dropped; idle-rate measurement row), M.DOCS.066 (chroot list: build-date input) | amended |
| F27 | M.DOCS.067 (owner question entry 1 removed), M.DOCS.022 (Class A row A15), M.DOCS.024 (Class B rows B66, B68, B69), M.DOCS.019 (A15 in the order), M.DOCS.020 (constants), M.DOCS.065 (UART-findings sub-bullet), M.DOCS.064 (maximum-size transfer row) | amended |
| F28 | — | none in this file |
| F29 | — | none in this file |
| F30 | — | none in this file |
| F31 | — | none in this file |
| F32 | — | none in this file |
| F33 | — | none in this file |
| R54 | M.DOCS.026 (Config Faults item: unreadable never overwritten, damaged repaired and listed), M.DOCS.082 (write list gains the damaged-file repair; the never-overwritten sentence narrowed to unreadable files) | amended |

**F21 map** — where this file writes each answered decision's tag. "explicit": written in the change; "conv.": the tag
sits in an action's text the change quotes and takes the convention's form at landing; "—": no tag written here.

| Decision (FOLD_ANSWERS) | status | M-ID | form |
|---|---|---|---|
| release-version-2-0 | ok | M.DOCS.059 | explicit (Resolved names the form) |
| release-defined-point | ok | M.DOCS.059 | explicit (as above) |
| reflash-runbook-erase | ok | M.DOCS.048 | explicit |
| scd30-calibration-readiness | ok | M.DOCS.026 (cites Part N rows) | — |
| ntp-synced-goes-stale | ok | M.DOCS.028 | — (owner tag stands) |
| dns-fallback-setting | ok | M.DOCS.028 | — |
| negative-backup-age | ok | M.DOCS.030 | — |
| state-code-values | ok | M.DOCS.030 | — |
| comment-cap-long-lines | ok | M.DOCS.092 | conv. |
| bench-sudo-checked | ok | M.DOCS.047 (points to `tests_hardware/README.md`) | — |
| licence-notices | ok | M.DOCS.011 | explicit |
| operator-actions-one-place | ok | M.DOCS.026 | explicit |
| twin-first-for-instruments | ok | M.DOCS.037 | conv. |
| no-gcc14-ci-leg | ok | M.DOCS.106 | conv. |
| unreadable-config-file | ask | M.DOCS.082, M.DOCS.026 | explicit (owner, 2026-10-01: the ruling is OR138) |
| wifi-off-led-pattern | ask | M.DOCS.027 | explicit (owner, 2026-10-02) |
| status-fields-added-and-left-out | ask | M.DOCS.032 | explicit via OR137 (`HTTPDropped`) |
| dns-fallback-clear-confirm | ask | M.DOCS.032 | explicit (owner, 2026-10-02) |
| led-request-internal-queue | ask | M.DOCS.027 | explicit (owner, 2026-10-02) |
| legacy-wip-as-intent | ask | M.DOCS.093 | explicit (owner, 2026-10-02) |
| console-starvation-bench-test | ask | M.DOCS.086, M.DOCS.064 | explicit (owner, 2026-10-02) |
| hand-run-hardware-rows | ask | M.DOCS.064 | explicit (owner, 2026-10-05) |
| idle-poll-rate | ask | M.DOCS.064 | explicit (owner, 2026-10-05) |
| uart-flash-erase-overrun | change | M.DOCS.084, M.DOCS.076, M.DOCS.024 | explicit (owner, 2026-10-05) |
| stub-versions-pinned | ask | M.DOCS.105 | explicit (owner, 2026-10-02) |
| bench-psk-fallback | change | M.DOCS.047 | explicit (owner, 2026-10-02) |
| wozi-move-owner-operation | ask | M.DOCS.078, M.DOCS.076, M.DOCS.045, M.DOCS.048 | explicit (owner, 2026-10-02) |
| twin-tolerates-ntp-offline | change | M.DOCS.064 | explicit via the dropped row |
| reproducible-image | ask | M.DOCS.066 | — (no tag in the chroot list) |
| one-entry-per-fault | change | M.DOCS.065 | — (no permanent text) |
| every other decision | — | — | no tag written in this file |

**OR144 (lead ruling):** OR144.a (owner, 2026-10-05: standing push permission to `hundertvolt/datasheets`) satisfies
the owner precondition of M.DOCS.014's Unit and M.DOCS.047's and M.DOCS.068's slots (and M.SPEC.005/.019); each now
states it as satisfied.
