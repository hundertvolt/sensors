# A-C gap pass, group G1: SPEC, DOCS, PROC, GEN (2026-10-01)

Inputs read: every "Gaps for other clusters" section of the 16 `M_*.md`, AC_NOTES 1-45 (45 in full), OR126-OR133, and
the three late SPEC gaps of `gap_prompt.md`. For every item, I read the body of its carrying change, not only the ledger.
Each row is one gap item, or one lettered sub-item where the source letters them. "Carried" means the change already
holds the item. "Amended" means this pass edited that change's body, and its ledger row where the action set changed.

## Items

### Target SPEC (`M_SPEC.md`)

| # | Source item | Gist | Carrying M-ID | Result |
|---|---|---|---|---|
| S1 | M_DOCS gap 1 (a) | F.2: the timeout mechanism is built (`wait_for_ms`); A.U14.16's "not yet built (BACKLOG)" not written | M.SPEC.094 (3), Resolved (a) | carried |
| S2 | M_DOCS gap 1 (b) | C.7's BACKLOG item-32 pointer becomes the owed row at U33 | M.SPEC.058 (4) | carried |
| S3 | M_DOCS gap 1 (c) item 3 | the legacy-version decision goes to F.1, the no-tree-edits fact to the Part F intro | M.SPEC.087 (2), M.SPEC.088 (1) | carried |
| S4 | M_DOCS gap 1 (c) item 2 | the config-repair fact goes to L.7 | M.SPEC.150 (5) | carried |
| S5 | M_DOCS gap 1 (c) SPI RX | the no-retry reason joins F.5.2 | M.SPEC.101 | carried |
| S6 | M_DOCS gap 1 (c) UART fakes + four findings | homes for the BACKLOG UART entries | M.SPEC.050 (5), M.SPEC.137 (2), M.SPEC.138 (3), M.SPEC.111 | carried. SPEC lands them in C.3.2/J.7/J.8/G.2, not C.3.2/J.9/G.2 (M.SPEC.137 (b)). **M.DOCS.065 amended** to name the landed homes |
| S7 | M_DOCS gap 1 (c) mypy `Timer()` | the standalone-mypy note goes to B.15 | M.SPEC.043 (7) | carried |
| S8 | M_DOCS gap 1 (d) | the Part F checklist names the Workarounds table | M.SPEC.087 (1) item (9) | carried |
| S9 | M_DOCS gap 1 (e) | I.4(f.1): run-phase 80 %/12 % figure as A.U30.10 dates it | M.SPEC.130 (4) | carried |
| S10 | M_DOCS gap 1 (f) | B.17: owner tag on "Two targets"; A.U21.16's trixie wording | M.SPEC.045 | carried |
| S11 | M_DOCS gap 1 (g) | `@web` grammar has one home | M.SPEC.118, M.SPEC.149 | carried (L.6.4 holds the rows; the DOCS half is D2) |
| S12 | M_DOCS gap 1 (h) | J.7 tier map names the L2 twin UART files | M.SPEC.137 (3), Resolved (c) | carried |
| S13 | M_DOCS gap 1 (i) | J.7 and F.7 row 12 cite CLAUDE.md's "known hang cause" | M.SPEC.107, M.SPEC.137 (6) | carried |
| S14 | M_GEN gap 10 | the SPEC blast items in M_GEN's "Blast carried by" lines (A.7, H, L, C.7, F.1, F.3, L.2-L.7) | 33 A-IDs, each with an M_SPEC ledger row and change (e.g. A.U25.69 → M.SPEC.020; A.U36.514 → M.SPEC.118/.149) | carried |
| S15 | M_HW_BENCH GAP-B4 | F.1's named `exec()` exception moves to `digital_twin/run_device_script.py` | M.SPEC.089 (1), Resolved (b) | carried |
| S16 | M_HW_BENCH GAP-B7 | Part N rows no tagging action writes (l4 margins, lwIP stall bounds, console load) | M.SPEC.156 (2) | carried |
| S17 | M_HW_DEV GAP-D2 | one `l3.device_script_feed_step_ms` row replaces the per-script feed rows | M.SPEC.156 (1), (4) | carried |
| S18 | M_HW_DEV GAP-D4 | `loop.uart_call_span_max_us` "Checked by" names the flash driver test | M.SPEC.156 (5) | carried |
| S19 | M_PROC gap 1 | Part N Dependants at their end state (drops, the one feed-step row) | M.SPEC.156 (1) | carried |
| S20 | M_PROC gap 2 | F.7 diff rows and their sentence; F.1 wrap-run sentence; Part N bases; E.6 rows; conditional F texts; U37 second F.5 record | M.SPEC.107 (4), .092, .157, .083, .093/.094/.100/.108, .099/.109 | carried |
| S21 | M_SCR gap 5 | Part N rows; exit 2 (OR133); E.1 lock directory; E.6.1/E.9 port-53 deselection; H.7 smoke through `_twin_process.js` | M.SPEC.156 (2); .078/.079/.086; .076/.022; .076/.077/.085; .121/.123 | carried |
| S22 | M_SRC_CORE GAP-G7 | A.7's FRAM list: `CFGMGR_SCD30` RAM-only | M.SPEC.020 (step 8, step 9, Resolved (a)) | carried |
| S23 | M_SRC_CORE GAP-G8 | `report_if_fatal()` lives in `asy_print_log` | M.SPEC.058 (11), M.SPEC.111 Resolved (b) | carried |
| S24 | M_SRC_CORE GAP-G9 | I.2 long-lived catalog gains `FRAMManager._chunks` | M.SPEC.126 (e) | carried |
| S25 | M_SRC_CORE GAP-G13 | C.10's per-kind validator sentence | M.SPEC.068 (+ .021/.052/.054/.111) | carried |
| S26 | M_SRC_SENS GAP-1 | D.5 names the two `sleep` exceptions; `loop.sync_wait_max_us` check and Dependant | M.SPEC.074, M.SPEC.156 (5) | carried |
| S27 | M_SRC_SENS GAP-4 | `led.refresh_hz`, `led.overlay_brightness` renames | M.SPEC.156 (3) | carried |
| S28 | M_SRC_SENS GAP-8 | G.2 names `_trigger_loop()` | M.SPEC.111 Resolved (a) | carried |
| S29 | M_SRC_SENS GAP-10 | A.7 chunk layout has no `CFGMGR_SCD30` | M.SPEC.020 | carried |
| S30 | M_SRC_SENS GAP-13 | C.8 lock table `_threshold_lock`; resolver reads `self._i2c_<chip>` | M.SPEC.064 (c) | carried |
| S31 | M_SRC_SENS GAP-15 | C.7 `_error_check()`: each reader passes `condition=results[0] is None` | M.SPEC.058 (8), M.SPEC.052 | carried (AC_NOTES 38 form) |
| S32 | M_SRC_SENS GAP-16 | M.1.2 restart table gains the INT re-arm flag | M.SPEC.154 | carried |
| S33 | M_TEST_HELP GAP-H5 | L.2 equal-rank order; E.8 platform-print; H.7.1 citer list drops the deleted file | M.SPEC.145 (5), M.SPEC.084 (4) | carried. The citer part needs no edit, because A.U36.532 (3) repoints no H.7.1 citer ("none changes") |
| S34 | M_TEST_UNIT GAP-U9 | `l1.asy_notification_service_next_sleep_min_ms = 59000` | M.SPEC.156 (2) | carried |
| S35 | M_TEST_UNIT GAP-U10 | E.8 hazard-check counts at landing; "the dev wiring selects" | M.SPEC.084 (5) | carried |
| S36 | M_TOOL gap 8 | Part N tool and CI rows; B.10.1 composite actions, `devices` job, `env` | M.SPEC.156 (2), (6); M.SPEC.033/.034 | carried |
| S37 | M_TWIN SPEC item | build-chain proof names the harness; Part N renames, withdrawals and new row; E.2.1/J.7 name existing files | M.SPEC.035/.121; .156 (3)/(4)/(2); .137; **M.SPEC.077** | carried, except E.2.1, which is **amended**: A.U36.016's "like the wrapper files above" names no existing file after A.U24.65's `PER_DEVICE` dispatch, so it now names the marker (M.TWIN.144 (d)) |
| S38 | M_WEB gap 4 (a)-(e) | H.6.1 member and row fixes; H.4 `ForceCalRef`/dispatch text; H.2/H.8.1 `_expected_display.js`; `LastTaskEnd` display | M.SPEC.120; M.SPEC.116; M.SPEC.114/.124; M.SPEC.116 | carried |
| S39 | M_WEB gap 7 | Part N rows for the new `tests_js` tags | M.SPEC.156 (2) | carried |
| S40 | M_PROC gap 7 / M_TWIN LEAD gap (SPEC side) | `.gitignore` is PROC's | M.SPEC.089 Blast | **amended**: the sentinel parenthesis → M.PROC.019 (6) (PROC), not "TOOL" |

### Target DOCS (`M_DOCS.md`)

| # | Source item | Gist | Carrying M-ID | Result |
|---|---|---|---|---|
| D1 | M_SPEC gap 1 = late SPEC gap 1 | CLAUDE.md's refresh bullet cites "Part F.9", not "F.5.10" | M.DOCS.071 | **amended** (text, Resolved, Depends). Same fix in M.DOCS.070's Blast and in M.PROC.008/.031 (P7) |
| D2 | M_SPEC gap 2 = late SPEC gap 2 | the tag-line pointer names L.6.4 only | M.DOCS.092 | **amended**: the H.5.1 half dropped; Resolved cites M.SPEC.118/.149 |
| D3 | M_PROC gap 3 (a) | "Last run" re-dated at U37 even when nothing moved | M.DOCS.070 | carried |
| D4 | M_PROC gap 3 (b) | the practice line names the Workarounds table | M.DOCS.070 | carried |
| D5 | M_PROC gap 3 (c) | A.U25.65's BACKLOG pointer at `digital_twin/README.md:453-456` | — | disposed: M.DOCS.064's owed list holds no such row, so A.U25.65's own condition applies and the sentence goes. TWIN executes it (hand-off H3) |
| D6 | M_PROC gap 3 (d) | hold-back and parked entries in the owner-question list | M.DOCS.067 | carried |
| D7 | M_PROC gap 3 (e) | A.U1.02 is a parser hit, carried by M.PROC.014 | M_DOCS ledger row A.U1.02 | carried |
| D8 | M_PROC gap 3 (f) | README "Further reading" `legacy/README.md` entry is A.U1.13's | M.DOCS.060 | carried |
| D9 | M_SCR gap 6 | U27 chroot paragraph names the new sourced helpers | M.DOCS.066 | carried |
| D10 | M_SRC_CORE GAP-G7 | CLAUDE.md FRAM-log rule names `CFGMGR_SCD30` as RAM-only | M.DOCS.090 | carried |
| D11 | M_SRC_NET gap 6 | UART changelog Class B: synchronous `_note_valid_frame()`; `set_callback` with siblings; one starter-name row | M.DOCS.024 (B33ff., Resolved) | carried |
| D12 | M_SRC_SENS GAP-10 | CLAUDE.md FRAM-logger list exception | M.DOCS.090 | carried |
| D13 | M_TOOL gap 7 | one chroot line per unit U0-U36 | M.DOCS.066 | carried |
| D14 | M_TSC gap 2 | the README runbook cites the hostname test by name | M.DOCS.048 | carried |
| D15 | M_TWIN DOCS item | the two-suites bullet and the UART clause should name the L2 twin UART files | — | disposed: settled by M.DOCS.085 (CLAUDE.md names no file; C.8/J.7 is the one list, A.U36.014) and M.DOCS.101 (the UART pair binds no port) |
| D16 | M_WEB gap 8 | the two-suites bullet names the live twin, not the mock; the eslint-comments plugin goes in the U0 refresh line | M.DOCS.101, M.DOCS.066 | carried |

### Target PROC (`M_PROC.md`)

| # | Source item | Gist | Carrying M-ID | Result |
|---|---|---|---|---|
| P1 | M_TOOL gap 11 | W32's outcome fixes the local `uses:` form; A.U28.13 runs in U0 | M.PROC.008 (2)(c), (2)(f) | carried |
| P2 | M_HW_BENCH GAP-B8 | hand-run rows H78-H82: instruments and records | M.PROC.038 | carried |
| P3 | M_HW_BENCH GAP-B9 | R2's plan states its write budget first | M.PROC.039 | carried |
| P4 | M_TWIN LEAD gap | `.gitignore` ignores `digital_twin/mem_backup_state.json` | M.PROC.019 (9) | carried |
| P5 | M_SCR gap 2 (f) | `.gitignore` MICROPYPATH sentence: keep one | M.PROC.019 (6), Resolved | carried (the sentence goes; `scripts/micropypath.toml` is its one home) |
| P6 | M_DOCS gap 5 | lists what DOCS carried for PROC | — | disposed: informational, nothing for PROC to add |
| P7 | M_SPEC gap 1 (PROC side) | the standing-workaround list is SPEC F.9 | M.PROC.008, M.PROC.031 | **amended** ("F.5.10" → F.9 in Resolved, Change and Blast) |

### Target GEN (`M_GEN.md`)

| # | Source item | Gist | Carrying M-ID | Result |
|---|---|---|---|---|
| G1 | M_SRC_CORE GAP-G1 | `_collect_setups()` typed `list[SetupFct]` | M.GEN.010, M.GEN.003 | **amended**; the starter collectors also use `TaskStarter`/`TimerStarter`, the types `start_tasks()`/`start_timers()` take |
| G2 | M_SRC_CORE GAP-G2 | catalog gains shared errno 25 `STACK_EXHAUSTED`, with its mirror | M.GEN.034 | **amended**: 25, not "SYSTEM band"; `ResetReason` 20 (A.U30.19 (5)). The mirror is the generated definitions (M.GEN.016) |
| G3 | M_SRC_CORE GAP-G8 (GEN) | A.U30.19 import lines in generated code | — | disposed: the generated module emits no broad handler (M.GEN.001-.013), so it imports nothing. Ledger row A.U30.19 says so |
| G4 | M_SRC_CORE GAP-G10 | `CRCPass` / `asy_crc_checks` in `UART_CRC_MODES`, its comment and the generated import | M.GEN.024, M.GEN.003 | **amended** (with `asy_print_log`/`asy_base_classes` in the same import list) |
| G5 | M_SRC_CORE GAP-G13 (GEN) | the generated LED callback calls `checked_int`/`checked_float` | — | disposed: since A.U19.02 the callback validates nothing (M.GEN.008 Resolved (b)); the R/G/B/T checks are the webserver's `_LIGHT_CMD_FIELDS` (SRC_NET, M.SRC_NET.122). AC_NOTES 38 GAP-14: no never-true runtime check is written |
| G6 | M_SRC_NET gap 1 | catalog rows 16, 69, W48/W60-62, DNSSRV 42/43, shared W11/W12, owner lists, UART 91/92 | M.GEN.034 | **amended**. SOCKET_TEARDOWN is W12 (M_SRC_SENS GAP-7, M.SRC_SENS.043, later than M_SRC_NET's 11); errno 72 named too |
| G7 | M_SRC_NET gap 2 | `IP`/`IPv4` match the snapshot field; task names read `start_asy_*`; twin plan and `UARTLinkDriver(…, log=…)` | M.GEN.008, M.GEN.010, M.GEN.012, M.GEN.043 | `IP`/`IPv4`, plan and constructor carried. **Amended**: `wifi.Rssi` → `wifi.RSSI` (M.SRC_NET.074), and the task-name form is spelled out (A.U32.06 (1) with A.U10.44's names) |
| G8 | M_SRC_SENS GAP-7 | catalog: W11 `DERIVED_DOMAIN`, W12 `SOCKET_TEARDOWN` | M.GEN.034 | **amended** (with W14/W15 `DEVICE_RECOVERY`/`BUS_RECOVERY`) |
| G9 | M_SRC_SENS GAP-14 (GEN) | no never-true type check in generated code | — | disposed: settled by AC_NOTES 38 GAP-14 and A.U19.02 (same as G5) |
| G10 | M_TEST_HELP GAP-H7 | scenarios read `_expected.json`; `fram_wired` is labels only; no per-logger exemption list | M.GEN.019 | **amended**: `fram_backed_loggers` adds `CFGMGR_<name>` only where the class keeps `_CFG_LOG_FRAM` true, read from the driver source. No hand list, so no device names `CFGMGR_SCD30` (agent decision, OR2.c review) |
| G11 | M_WEB gap 2 | `shape` takes `hostLabel`, `countryCode`, `hostName`, `ipv4List` | M.GEN.046, M.GEN.017 | **amended** |
| G12 | M_WEB gap 3 | a string field's schema special (`PW` `""`) is emitted as `specialValues` | M.GEN.017, M.GEN.046 | **amended**. The `PW` tag edit is SRC_NET's (H2) |
| G13 | M_WEB gap 5 | CSS: `.field-value.code-value` button reset, muted `.code-number` | M.GEN.062 | **amended** |
| G14 | AC_NOTES 41 | OR131/OR132 written firm in GEN | M.GEN.050, M.GEN.062, GEN Q1/Q2 | carried (answered, no "pending") |

## Hand-offs (items another group must carry)

- **H1 → SRC_NET**: the catalog (M.GEN.034) numbers `SOCKET_TEARDOWN` W12. The constants
  `_WRN_SOCKET_TEARDOWN = const(11)` in M.SRC_NET.004, .023 and .047 must read 12. This is already asked by M_SRC_SENS
  GAP-7 and M_TEST_UNIT GAP-U5, and is repeated here because the catalog row now depends on it.
- **H2 → SRC_NET**: the `PW` `@web` tag gains `special:""="Open network"` (M_WEB gap 3's SRC_NET half). M.GEN.017/.046
  now emit and accept it.
- **H3 → TWIN**: the change that carries A.U25.65 at `digital_twin/README.md:453-456` (M_TWIN, the CI-suite section,
  From A.U25.65) should state the end state outright. "(BACKLOG.md)" names no item, and M.DOCS.064 holds no owed row
  "SCD30/BMP3XX history against a healthy chip after a faulted run". So A.U25.65's fallback applies: the clause "and one
  nothing re-checks against a *healthy* chip (BACKLOG.md)" goes (Run 5c checks every driver against a healthy chip,
  A.U25.36).

## Owner questions

None. Every item was settled by a carrying change, a lead ruling (AC_NOTES 13, 38, 41) or a later merge's resolution
(M.SRC_SENS.043 over M.SRC_NET.004/.023/.047 on W12). M.GEN.019's derivation is an agent decision for the OR2.c review,
not an owner question.

## Incidental fix

- M.DOCS.048: "moving one of the owner's own units is his operation" → "their operation" (the owner is they/them).

## Not G1 targets (read; left to their groups)

- Late SPEC gap 3 (TEST_UNIT, the idle-wait degrade test): the SPEC side needs no change (M.SPEC.108's F.8.2 sentence
  states the rp2 behaviour, as the gap says).
- AC_NOTES 45 / M_PROC gap 5 (SCR, HW_BENCH: no runner selects `multi_day_rollover`). M.PROC.041 already starts R6 through
  the clean-run wrapper directly and stays valid with either fix.
- M_GEN gap 9, M_WEB gap 1, M_PROC gap 7 (CLUSTERS.md): these are orchestrator items.

## Counts

- Items read that target G1: 77 (SPEC 40, DOCS 16, PROC 7, GEN 14).
- Carried as found: 56 (SPEC 38, DOCS 12, PROC 5, GEN 1).
- Amended: 15 (SPEC S37, S40; DOCS D1, D2; PROC P7; GEN G1, G2, G4, G6, G7, G8, G10, G11, G12, G13). S6 is counted
  as carried; its DOCS-side follow-up (M.DOCS.065) and D1's M.DOCS.070 Blast fix are edits made under those rows.
- New merged changes: 0.
- Disposed: 6 (D5, D15, P6, G3, G5, G9).
- Handed off: 3 (H1 SRC_NET, H2 SRC_NET, H3 TWIN).
- Changes edited: M.SPEC.077, .089; M.DOCS.048, .065, .070, .071, .092; M.PROC.008, .031; M.GEN.003, .008, .010, .017,
  .019, .024, .034, .046, .062. Each of the four files gained an "Incoming gaps, gap pass G1" note before its Adherence
  section.
