# U20 lane D report (SPECIFICATION.md)

Branch `audit/u20-d`, final commit `FINAL_HASH` (not pushed). One file edited: `SPECIFICATION.md`. Lane commits:
`bdd93f9` (WIP L.3), `0a23cf9`, `3d56b52`, `4fc4aa1`, `937592c`, `88947af`, LATER_COMMITS; `audit/u20-int` merged in at
`3cbe67b`, `8df1528`, `426e964`, LATER_MERGES. Every fact is written as the code on the merged tree states it; where a
report or the packet worded it differently, the difference is under "Deviations".

## Step table

| step | M-id | status | where / why |
|---|---|---|---|
| 88 | M.SPEC.010 | applied (U20 parts) | A.4 FRAM bullet: every intended reset pauses FRAM first (the sequence's close-FRAM step, A.8); `erasefram` runs the whole-chip erase; the WDT-site sentence names `test_real_device_module_constructs_no_watchdog_and_its_boot_entry_exactly_one` and `test_real_device_boot_entry_arms_the_watchdog_as_its_first_statement`. The "20/20" figure went with the old commanded-reset text |
| 89 | M.SPEC.015 | applied | A.4 supervisor bullet names `start_tasks()`, `start_timers()`, `supervise_tasks()` |
| 90 | M.SPEC.018 | applied (7) | A.5: the server task is one of the supervised tasks (`start_tasks()`/`supervise_tasks()`); other parts are other units' |
| 91 | M.SPEC.060 | applied (5) | C.7.2's build refusals: `rx_ring` floor, `max_transfer_bytes`, the CRC-mode mismatch |
| 92 | M.SPEC.089 | applied (A.U20.03 sentence) | F.1: `.frozen` first on `sys.path` in the boot entry; extensible built-ins cited to `py/builtinimport.c:404-416` (pinned v1.29.0, read); the exception-handler sentence names `start_tasks()`. The shadowing proof file is U25's and is not cited |
| 93 | M.SPEC.096 | applied (U20 part) | F.2's commanded-reset sentence: the command answered "Valid" before the sequence runs |
| 94 | M.SPEC.061 | applied (5), (7) fold | C.7.3: ConfigFaults clause, ConfigUnpersisted, a directory in the file's place → ConfigFaults, third write-site bullet `delete_file()` ("trying twice and then leaving it") |
| 95 | M.SPEC.108 | applied (3)(d) | F.5.9: the build bound for `poll_idle_ms` |
| 96 | M.SPEC.111 | applied (items 12, 16) | G.2: the mirror entry gains `test_buildgen_source_agreement.py`; the watchdog entry gains `run_setups()`, `_own_feed()` ownership and the feed-site guard |
| 97 | M.SPEC.118 | applied (3), (6) | H.5.1: `schema_ast` selection rules (tuple-of-`FieldSchema` constants included), the hidden/untagged rule, the warn catalog `buildgen/signals.py` `WARN_SIGNALS` |
| 98 | M.SPEC.128 | (2) applied, (3) already landed | (2) I.4 (c) names `supervise_tasks()`'s task; (3) already in end form at `SPECIFICATION.md:6867-6868` ("escalates past repeated restarts to the reset path (`_reboot()`)") |
| 99 | M.SPEC.129 | applied (3) with F.7 row 11 | I.4 (e): message placement and the boot entry's 100 B emergency buffer; F.7 row 11's workaround cell names the boot entry's reservation and the Unix port's lack of the function (`py/modmicropython.c:146-148, 210-212`, read) |
| 100 | M.SPEC.130 | applied (1), (2) | I.4 (f.1): the two lists are `run_setups()`/`start_tasks()`; the gc-sites guard text; the probe's dead-task check and order sentence |
| 101 | M.SPEC.141 | applied | K.3 items 1, 4, 6 (two hand-kept tables, no `_SENSOR_DRIVERS`, Table 279) and K.11's checklist line |
| 102 | M.SPEC.145 | applied (3), (4), (6) | L.2: owner tags (owner, 2026-09-09), the emitted-functions list, the annotation-only globals sentence, the frozen-set seed |
| 103 | M.SPEC.148 | applied (2), (4), (6) + rule ids | L.5: collisions (UART bus, settings group, logger), the standing-rule mechanism (`KNOWN_TAGS`, `specs_for`, column 0, `nan`/`inf`), `@value-wiring`/`@limits` dimensions, the BuildError message form, the error-contract and fuzz tests, and every rule id grouped by what it guards (174 ids, generated from the tree) |
| 116 | M.SPEC.020 | applied (items 3, 4, 7, fold 16, the stretch table) | A.7: the boot entry (reset reason 21 on KeyboardInterrupt), `main()`'s order with the expected JSON and `boot_sequence_matches_the_generated_expectation`, step 1 `reset_reason = begin_boot()`, step 8 providers, step 15 rewritten as the `run_setups()` batch, the unfed-stretch table in the new order |
| 150 | M.SPEC.035 | applied (3) | B.11: boot entry names and the no-autostart variant |
| 151 | M.SPEC.147 | applied (2), (5), (7) | L.4: `generate_device`'s return, compile step, determinism; the validation list; construction; the signal catalog; twin wiring via `fixed_address()`/`TwinWiringPlan`/contract test; the twin runner's own WDT |
| 158 | M.SPEC.136 | applied (8) + ring sentence | J.6: TOML sentence on cap and ring; dev's 512 B ring (agent, 2026-10-08, ruling 12) |
| 159 | M.SPEC.138 | applied (3)'s TOML clause | J.8 |
| 160 | M.SPEC.149 | applied | L.6.2 keyword-only parameters, L.6.3 `data_fields`, L.6.4 `specs_for`/`hidden`, L.6.5 rewritten from Table 279 (I2C/SPI/UART/wireless bullets), L.6.6 coverage additions |
| 165 | M.SPEC.054 | applied (6) | C.5 schema-lint paragraph |
| 173 | M.SPEC.049 | applied (2) | C.3.1: every device TOML names its FRAM part |
| 174 | M.SPEC.146 | applied | L.3: checked key table between `<!-- toml-schema-table -->` markers (75 rows, V's contract test green), banner order/form, `name_ext`, the example's comments as the TOMLs have them, the smoke-test sentence (A.U20.19) |
| 198 | M.SPEC.021 | applied (with folds (10)-(13)) | A.8: status fields `ResetReason`/`ResetBits`/`MemFree`/`ConfigFaults`/`ConfigUnpersisted`, the marked `status.ResetReason` code table (0-9, 11-15, 21, texts from the catalog), the five `SystemCmd` words, the controlled shutdown paragraph, `resetconfig`/`erasefram`, the no-SCD30-write paragraph, the step table with "Why here", hang and power-loss sentences |
| F1 | (plan row) | applied | every `start_and_check_tasks()` mention in SPEC (A.4, A.5, C.9, C.9.1, F.1, I.4) rewritten to `run_setups()`/`start_tasks()`/`supervise_tasks()`; grep now finds none |

Also, outside a numbered step (plan section 2 lane D): the `boot.unfed_stretch_1_ms`/`_2_ms` rows follow the new boot
order (N.4); Part I's ring sentence (I.2) at dev's 512 B per ruling 12; C.6 (a store on defaults answers the marker,
SensorReaderConfig stores included), C.5.2 (closed-store refusal through `_writes_closed()` and `owner_lock`), C.8 rows
(`ConfigManager.owner_lock` beside `SensorReader._set_lock`; `SystemService._command_lock`), C.9 rows (Supervisor
names `supervise_tasks()`; Shutdown names `_request_shutdown()`), E.3 (generated files), F.5.4 (code 21; every generated
device calls `begin_boot()`; "The chip keeps what `reset_cause()` collapses", from RP2040 datasheet 2.12.7), A.1.

Part N rows (`test_tunables_register.py` green): `wdt.timeout_ms` Sites rebuilt from the tags (codegen site removed;
`digital_twin/run_generic_integration.py` and seven device scripts added); new `gc.emergency_exc_buf_bytes` (100 B),
`dev.uart_rx_ring` (512, `devices/dev.toml:56`, `:71`), `dev.uart_max_transfer_bytes` (12192, `:177`, `:188`),
`l0.buildgen_reproducible_timeout_s` (120); `ntp.check_interval_s` loses its `buildgen/validate.py` site; withdrawn:
`l3.heap_layout_after_full_boot_sequence_starter_loop_grace_ms` and `..._starter_poll_ms`; the
`..._starter_loop_timeout_ms`/`..._starter_settle_ms` dependants updated. PARTN_S

## Deviations

DEVIATIONS

## Files outside my set

OUTSIDE

## Facts owed to others

OWED

## Tests run

TESTS

## OF-71 figures

None: lane D edited no `tests/` file, so no file was grown and no MicroPython run is owed. No L0 file was added or
grown.

## Files the lead must run on the merged tree

LEADRUN

## Silent-failure scan

SCAN
