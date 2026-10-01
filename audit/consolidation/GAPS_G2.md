# A-C gap pass, group G2 (targets SRC_CORE, SRC_NET, SRC_SENS, WEB), 2026-10-01

Inputs read: the "Gaps for other clusters" section of all 16 `M_*.md` files; `AC_NOTES.md` (items 38-45 in full, the
earlier items that name a target cluster); the three late SPEC gaps (none names a G2 target: they go to DOCS and
TEST_UNIT); the two G1 hand-offs H1 and H2. For each item, the carrying change's body was read in the target file; a
ledger mention alone was not taken as carried. Every amendment is marked "gap pass G2" in its change body, and each
target file ends with a "Gap pass G2 rows" ledger table and new numbered entries in its "Agent decisions" list.

## Items

| # | Source and item | Target | Gist | Carrying M-ID | Reason (if disposed) |
|---|---|---|---|---|---|
| 1 | M_GEN gap 4 | SRC_CORE | A.U11.30's `config_manager.py:126-127` comment names the generated LED dispatch | amended M.SRC_CORE.047 (also M.SRC_NET.122 blast) | — |
| 2 | M_GEN gap 5 | SRC_CORE | `SystemService` API the template calls | carried as found: M.SRC_CORE.006, .008, .011, .012, .015, .016 | The "reads FRAM's `bool`" clause is obsolete: `run_setups()` discards results, and FRAM reaches the supervisor through its watch starter (M.SRC_CORE.015/.092, A.U16.R03) |
| 3 | M_GEN gap 6 | SRC_NET, SRC_SENS | Webserver/WiFi/NTP/NeoPixel APIs the template calls | carried as found: M.SRC_NET.044, .074, .078, .098, .112, .119, .129; M.SRC_SENS.026 | Snapshot field is `RSSI` (A.U10.40, M.SRC_NET.074), not `Rssi` → hand-off H-1 |
| 4 | M_GEN gap 10 | WEB | `js/` and `tests_js/` blast named in M_GEN | carried as found: every named A-ID has its M_WEB ledger row | — |
| 5 | M_HW_DEV GAP-D9 | SRC_CORE, SRC_NET | The two WiFi repro scripts are deleted at U26, so no edit is owed | SRC_CORE: carried as found (no change lists them); SRC_NET: amended M.SRC_NET.078 blast | — |
| 6 | M_SCR gap 1(a) | WEB | Twin `MICROPYPATH` uses the device's built site; port-53 lock is re-entrant and inherited | amended M.WEB.061, .078, .082 | — |
| 7 | M_SCR gap 1(b) | WEB | Exact `lint:html:built` command | amended M.WEB.071 | — |
| 8 | M_SCR gap 1(c) | WEB | JS freshness stamp `build/generated_src/definitions/inputs_stamp.json` | carried as found: M.WEB.050 | — |
| 9 | M_SRC_CORE GAP-G7 | SRC_SENS | `SCD30_Reader._CFG_LOG_FRAM = False` | amended M.SRC_SENS.052 | — |
| 10 | M_SRC_CORE GAP-G8 | SRC_NET | Import `report_if_fatal` from `asy_print_log` | amended M.SRC_NET.011, .060, .104, .110, .121, .150 | — |
| 11 | M_SRC_CORE GAP-G8 | SRC_SENS | Same import fix | amended: conventions bullet, M.SRC_SENS.017, .030, .039, .049, .058, .070, .087 | — |
| 12 | M_SRC_CORE GAP-G12 | SRC_NET (and the rest of `src/`) | Attributes with no reader outside their class become private | amended M.SRC_NET.008, .009, .044, .046, .048, .050, .078, .155, .156, .192, .195, .213, .215; SRC_CORE leftovers M.SRC_CORE.008, .009, .013, .036, .037, .044, .049, .081 | — |
| 13 | M_SRC_CORE GAP-G13 | SRC_NET | Webserver uses `checked_int()`/`checked_float()` | amended M.SRC_NET.110, .112, .122 | — |
| 14 | M_SRC_CORE GAP-G13 | SRC_SENS | ISL29125 `_checked_cfg()` uses `checked_numeric()` | amended M.SRC_SENS.070, .082; the same ruling extended to M.SRC_SENS.039/.045 (BMP3XX) and .058/.064 (SGP40) | — |
| 15 | M_SRC_NET gap 3 (SRC_CORE half) | SRC_CORE, SRC_NET | Readiness flag: `SensorReaderConfig` lacks `initialized`; `WifiService` overrides `setup()` | amended M.SRC_CORE.008, .017, .036, .039, .040, .091, .092; M.SRC_NET.079, .119 (`setup() -> bool`) | — |
| 16 | M_SRC_NET gap 4 (U19 A-C note 2) | SRC_CORE (+ SRC_NET, SRC_SENS overrides) | `_set_dict_cfg(data: JsonMapping)` implementers | amended M.SRC_CORE.003, .017, .038, .040, .044, .047, .049, .072; M.SRC_NET.041, .045, .071, .096, .111; M.SRC_SENS.049, .053 | — |
| 17 | M_SRC_NET gap 4 (U19 A-C note 1) | SRC_CORE, SRC_NET | `handle_set_cmd()` envelope against the caller's never-false `isinstance` | amended M.SRC_CORE.070, .072; M.SRC_NET.120 (and its agent decision 5) | Settled by the lead's L1 ruling: `handle_set_cmd()` returns `WriteValidity`. No wire change |
| 18 | M_SRC_NET gap 4 (names exist before importers) | SRC_CORE | `report_if_fatal`, `COUNTER_CAP`, `RegionBuffer`, the aliases, `LogConfig`/`DEFAULT_LOG`, `session_lock` | carried as found: M.SRC_CORE.034 (U30), .031 (U10), .027 (U16), .030 (U10/U11), .061 (U5), .033 (U10 stage) | — |
| 19 | M_SRC_SENS GAP-7 | SRC_NET | `SOCKET_TEARDOWN` is W12 | amended M.SRC_NET.004, .007, .023, .047 | — |
| 20 | M_SRC_SENS GAP-8 | SRC_CORE | Shared divider is `_trigger_loop()` | amended M.SRC_CORE.039 | — |
| 21 | M_SRC_SENS GAP-9 | SRC_CORE | A new `cfg_log` constructor parameter | disposed | Settled by M.SRC_CORE.040's `_CFG_LOG_FRAM` and the G10/R15 `…, cfg_path, log` tail rule (OR46.b). TEST_HELP (M.TEST_HELP.036) and DOCS already read the attribute. M.SRC_SENS.052 is amended to use it (item 9) |
| 22 | M_SRC_SENS GAP-12 | WEB | `Calibrate` dispatch toggle without `defaultValue` | carried as found: M.WEB.004, .014, .054 | — |
| 23 | M_SRC_SENS GAP-14 | SRC_CORE, SRC_NET | No narrowing check that can never fire; the fix is at the type level | SRC_CORE carried as found: M.SRC_CORE.047 (AC_NOTES 38); SRC_NET via item 13 | — |
| 24 | M_SRC_SENS GAP-15 | SRC_CORE | Before the first sync, `TS` is `None` | carried as found: M.SRC_CORE.037 (`_error_check()` unchanged; AC_NOTES 38) | — |
| 25 | M_SRC_SENS GAP-17 | SRC_CORE | Readiness gates | disposed for the exemption question | Settled by AC_NOTES 38/42/44 (TSC carries the exemptions, M.TSC.112). The SRC_CORE classes get the flag through item 15 |
| 26 | M_TEST_UNIT GAP-U1 | SRC_SENS | Backup age: `limit > 0 and (age < 0 or age > 60·limit)` | amended M.SRC_SENS.063 | — |
| 27 | M_TEST_UNIT GAP-U3 | SRC_SENS | `NeopixelDriver.initialized` | carried as found: M.SRC_SENS.023, .024 | — |
| 28 | M_TEST_UNIT GAP-U4 | SRC_SENS | A stale stored value makes `_apply_stored_config()` return code 2 | disposed | Unreachable: `ConfigManager.setup()` checks each stored value against the schema, whose special set is the chip's domain (`_OSR_SETTINGS`/`_IIR_SETTINGS` with no min/max), and repairs it. So code 2 means a chip I/O failure only, and OR113's ladder is right as written (M.SRC_SENS.044) |
| 29 | M_TEST_UNIT GAP-U5 | SRC_NET | DNS server's `_WRN_SOCKET_TEARDOWN` follows the catalog (12) | amended (= item 19) | — |
| 30 | M_TEST_UNIT GAP-U6 | SRC_NET | Networking modules import `report_if_fatal` from `asy_print_log` | amended (= item 10) | — |
| 31 | M_TEST_UNIT GAP-U11 | WEB/SCR | Stager writes one separator per module | disposed for WEB | The stager is SCR's file, carried by M.SCR.019. No WEB site |
| 32 | M_TSC gap 1 | SRC_SENS | `NeopixelDriver.initialized` for M.TSC.112 | carried as found: M.SRC_SENS.023, .024 (AC_NOTES 44/45) | — |
| 33 | M_WEB gap 1 | orchestrator (WEB-named) | `mockdata/`, `vitest.config.js`, the tsconfigs named under WEB | carried as found: M.WEB.045, .073, .074 | The CLUSTERS.md line is the lead's file |
| 34 | M_WEB gap 3 | SRC_NET (+ GEN) | `PW` tag `special:""="Open network"` | amended M.SRC_NET.073 | GEN half already carried by M.GEN.017/.046 (G1) |
| 35 | G1 hand-off H1 | SRC_NET | `_WRN_SOCKET_TEARDOWN = const(12)` in .004/.023/.047 | amended (= item 19; .007's From also) | — |
| 36 | G1 hand-off H2 | SRC_NET | `PW` tag `special:` | amended (= item 34) | — |
| 37 | AC_NOTES 38 | SRC_CORE, SRC_NET, SRC_SENS | Lead rulings on GAP-14/15/17 | applied in items 13-14, 23-25 | — |
| 38 | AC_NOTES 39 | SRC_CORE | `CRCBase` out-of-range polynomial passes through | carried as found: M.SRC_CORE.131 | — |
| 39 | AC_NOTES 40 | WEB | End-state check reads six `tests_js` files in full against M.WEB.052-.059 | not carried in this pass | The item gives this to the end-state check. It is not a gap: no site is missing a carrier. The A.U10.40 key renames in those files run by script and grep (A.U10.40), and the end-state check still owes the full reads |
| 40 | AC_NOTES 41 | all four | GEN Q1/Q2 written as firm | carried as found (no "pending" in any G2 file); M_WEB owner-questions text amended to cite OR132 | — |
| 41 | AC_NOTES 42 | SRC_SENS | `NotificationService.initialized`, no method guards | carried as found: M.SRC_SENS.033 | — |
| 42 | AC_NOTES 43 | WEB | OR133: usage errors exit 2 | disposed | No WEB file is a runner that parses arguments. `package.json` scripts call SCR's runners |
| 43 | AC_NOTES 44 / 45 (TSC gap) | SRC_SENS | `NeopixelDriver.initialized` | carried as found: M.SRC_SENS.023, .024 | — |
| 44 | AC_NOTES 28 | WEB | `js/render.js:382`'s third `fetchOnce()` caller | carried as found: M.WEB.020 (the one-shot GET runs through the poll loop) | — |

Items 29, 30, 35 and 36 repeat earlier rows (the same change carries both). Item 4's check covered A.U6.05-.07, .17, .19,
.27-.29; A.U23.12, .16, .17, .20, .22, .23, .42, .43, .44, .49; A.U32.06; A.S0930.20. Each one has an M_WEB ledger row,
or an explicit "no WEB site" row (A.U23.44, CSS/TSC).

### How item 12 was run

The sweep was an AST scan of every `self.<public> = …` assignment per class at HEAD, with readers searched in `src/` and
`buildgen/` (the generated-code templates). Readers in tests, the twin and device scripts do not keep an attribute public
(G10/R07; S09's rule). Same-name members of other classes were checked by hand. The following were left as they are:
- locks (R17's names, e.g. `wifi_mode_lock`);
- `initialized`, `name` and `pr` (cross-module conventions);
- methods: setters, getters, starters, teardown and general driver API, because GAP-G12 is about attributes;
- `UDPSocket.connected`, kept public by its own earlier resolution;
- `UART` attributes that `UARTComm` reads.

SRC_SENS had no leftovers: every hit was already private in M_SRC_SENS.

## Hand-offs (another group carries these)

- **H-1 (GEN)**: M.GEN.008's `_networking_status()` reads `wifi.Rssi`. The snapshot namedtuple's field is `RSSI`
  (M.SRC_NET.074, A.U10.40), so this must read `"RSSI": wifi.RSSI`. GAP-G13's clause "the emitted
  `_notification_led_callback()` calls `checked_int()`" is void: after A.U19.02 the callback only delegates (M.GEN.008),
  and the webserver validates (M.SRC_NET.122). Nothing is owed there.
- **H-2 (TEST_UNIT)**: four changes:
  - (a) `handle_set_cmd()` returns the per-field `WriteValidity`, and `ok_descr` is gone (M.SRC_CORE.072). In
    `tests/test_api_response.py:195-332` (M.TEST_UNIT.004/.005), assert the returned dict, e.g. `{"SampleInterv":
    "Failed"}` rather than the envelope. `test_handle_set_cmd_ok_descr_override` goes. The section header's "and the
    envelope" wording follows.
  - (b) `type_or_range_error()` answers `(True, None)` on refusal, and every validator takes an `object`
    (M.SRC_CORE.047). New L1 cases: the refusal's second slot is `None`. A list or dict value is refused by
    `checked_int`/`checked_float`/`checked_numeric`/`type_or_range_error()`. `compare_before_write()` answers "Invalid"
    for a list value.
  - (c) Readers of the attributes made private follow the new names (lists in item 12):
    - `tests/test_system_service.py` and the twin tests (`sysfunct.watchdog`);
    - `tests/test_asy_wifi_service.py` (`max_module_error`, `conn_fail_to_hotspot`);
    - `tests/test_captive_dns.py` (`data`);
    - `tests/test_asy_ntp_client.py` and `tests/test_ntp_wifi_dns_integration.py` (`ntp_fetch_timeout_ms`, `retry_s`,
      `retry_max_s`);
    - `tests/test_asy_uart_comm.py` and `tests/test_digital_twin_uart_link.py` (`payload_size`, `uart`);
    - `tests/test_asy_fram_manager.py` (`block_addr`, `verify_counter`).
  - (d) The readiness L1 (M.TEST_UNIT.293) covers `SystemService`, `SensorReader` (and, inherited, every
    `SensorReaderConfig` subclass), `FRAMManager` (`initialized` replaces `_was_up`), and `WifiService`/`WebserverService`,
    whose `setup()` returns `bool`.
- **H-3 (TEST_HELP, TWIN, HW_DEV)**: readers of the private names in item 12 follow:
  - `tests/_sensortask_scenarios.py` and the twin tests (`watchdog`, if read from `sysfunct`);
  - the device scripts that address raw FRAM through `chunk.block_addr` (now `chunk._block_addr`; SLF001 is already
    ignored under `tests_hardware/**`);
  - `tests/_uart_comm_harness.py` (UARTComm attributes).
- **H-4 (TSC)**: four changes:
  - (a) M.TSC.112 should count a `setup()` that awaits `super().setup()` of a base that sets `initialized` as inheriting
    it (`SensorReaderConfig`, `WifiService`, `NotificationService`). `SystemService`, `SensorReader` and `FRAMManager`
    now carry the flag.
  - (b) M_HW_DEV GAP-D7's region check (A.U26.24) reads `chunk._block_addr`.
  - (c) `tests_scripts/test_port_lock.py` also drives `tests_js/_port_lock.js` for the same-process and
    child-of-holder cases, so the shell and JS sides keep one contract (M.WEB.078).
  - (d) A.U35.41's E.5.1 "narrowing" row for `_apply_settings_groups()` is not written, because no narrowing is left
    (M.SRC_NET.120).
- **H-5 (SPEC)**: four changes:
  - (a) C.5.3 (M_SPEC, the `handle_set_cmd(reader, data, cfg_vals, post_fct=None, post_asy_fct=None, ok_descr=None)`
    sentence) reads `handle_set_cmd(reader, data, cfg_vals, post_fct=None, post_asy_fct=None)`. It returns the per-field
    result, a failing hook's group "Failed", and the endpoint's OK envelope carries it (M.SRC_CORE.070/.072).
  - (b) C.10's per-kind validator sentence adds that a validator takes the REST value as `object` and that
    `type_or_range_error()` refuses with `(True, None)`. Its consumer list adds the SGP40 compensation read and BMP3XX
    `set_trigger_s()` (M.SRC_CORE.047).
  - (c) E.5.1 gets no webserver narrowing entry.
  - (d) C.13's readiness text names `SystemService`, `SensorReader` and `FRAMManager` among the classes carrying
    `initialized`.
- **H-6 (DOCS)**: `UART_C_PORT_CHANGELOG.md` gets one Class B line ("no C impact"). The line says that `UARTComm`'s
  `uart`, `role`, `payload_size`, `timeout`, `uid`, `UART`'s `cancel`, `txbuf` and `UARTLinkDriver.role` are made private
  (M.SRC_NET.155/.192/.213, gap pass G2).

## Owner questions

None. Every item is settled by one of these:
- an owner row (OR46.b tail rule, OR81 through G8/R61, OR113);
- the register (G5/R14, G5/R31, G10/R07);
- a lead ruling (L1/AC_NOTES 38, 42, 44);
- a G1 hand-off.

Agent decisions are listed for the OR2.c review in each target file:
- M_SRC_CORE 14-17;
- M_SRC_NET 15-16;
- M_SRC_SENS 22-23.

## Counts

- Items read: 44 rows. Rows 29, 30, 35 and 36 repeat rows 19, 10, 19 and 34, so there are 40 distinct items.
- Carried as found: 17 (rows 2, 3, 4, 8, 18, 22, 23, 24, 27, 32, 33, 37, 38, 40, 41, 43, 44).
- Amended: 17 (rows 1, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19, 20, 26, 34). These are amendments to existing
  changes in all four target files; each change body and its file's "Gap pass G2 rows" ledger table were updated.
- New changes: 0.
- Disposed: 5 (rows 21, 25, 28, 31, 42), plus row 3's obsolete FRAM-`bool` clause.
- Not carried, by the item's own assignment: 1 (row 39, AC_NOTES 40 → the end-state check).
- Handed off: 6 blocks (H-1 GEN, H-2 TEST_UNIT, H-3 TEST_HELP/TWIN/HW_DEV, H-4 TSC, H-5 SPEC, H-6 DOCS).
