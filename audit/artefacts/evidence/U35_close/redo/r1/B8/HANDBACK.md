B8 hand-back, written by the agent (2026-11-04)

Worktree `S/wt-b8`, branch `audit/r1-b8`, from d5c90b71. Source, tests and docs in one commit, **6f24e171**, and
**3d0e36bb**, the one fix round (a docstring line past 120 columns). Nothing pushed or merged. Run logs are
`S/u35/lead/b8_*.log`; the red runs (`b8_red`, `b8_red2`) ran the changed tests against an untouched d5c90b71 checkout (a throwaway worktree, removed),
`b8_red_setupfct` against a planted bool setup. Line numbers are the action list's (d6bc7617, re-based) unless named.

## Items

1. **I2C timeout: changed.** One `bus.i2c-timeout-range` check, 1..200,000 us; `bus.i2c-timeout-max`,
   `_BOOT_CLEAR_BUDGET_MS`/`_check_boot_clear_budget` (`bus.boot-clear-budget`) and `_check_i2c_timeout_consumer`
   (`bus.i2c-timeout-consumer`) go; `smallest_hard_consumer()`/`HardConsumer` stay (comment now names its two readers).
   The constant's comment states 2 buses x 11 x 200 ms = 4.4 s under the 8 s watchdog and rp2's `uint32_t`
   (`machine_i2c.c:47`, v1.29.0). Went first: TV `:668`, `:677`, `:699` (`_bmp3xx_alone_on_i2c0`), `:708`, `:720`,
   `:732`, `:742`; EC rows `:352`, `:353`, `:369-373`. TV `:633`+`:642` became
   `test_a_bus_timeout_outside_one_to_the_bound_is_rejected_and_both_bounds_build` (0 and 200,001 refused, 1 and
   200,000 build): red (old messages), green. TV `:685` keeps its bound half (renamed), `:751` stays (renamed off
   "budget"). SPEC C (the clear's sentence), F.3's stall row, L.3's key table, Part N's `i2c.timeout_max_us` row
   (budget words), `i2c.timeout_consumer_us` row removed.
2. **Build checks no TOML trips: removed, one kept.** Gone: `bus.i2c-frequency-range` (+`_I2C_FREQUENCY_MAX_HZ`),
   `bus.uart-baudrate-range` (+`_UART_BAUDRATE_MAX`), the rxbuf/txbuf floor (`_UART_BUFFER_MIN`; the upper bound
   stays, message and fix now "at most 32766"), `bus.uart-shared` (`_check_uart_bus_single_owner`),
   `instance.uart-baud-mismatch` (`_check_uart_link_roles` loses its `buses` parameter), `device.conn-fail-to-hotspot-range`,
   `device.hostname-label` (+`_host_label_ok`), `instance.name-ext-missing`, `names.settings-key-collision`,
   `source.field-unknown` with `driver_registry.data_fields()` and helpers and `source.fields-unreadable`. Restored:
   `names.logger-collision` to the pre-audit instance-against-instance check (`rule=`/`fix=` kept,
   `BuildInternalError` kept for the unset name), `_MANDATORY_MODULE_FILES` gone; `wiring.warn-outside-notification`
   gone (a warn_* off the notification is shape- and catalog-checked as before and wires nothing). Went first: TV
   `:229`, `:237` (space/dot names, same rule), `:248`, `:283`, `:543`, `:650`, `:660`, `:899`, `:909`, `:919`
   (missing mandatory file: the check no longer reads those files), `:929`, `:946`, `:1432`, `:1449`
   (fields-unreadable), `:1914`, `:1963`, `:2096`, plus the settings-group guard `:747-771` whose stated reason was the
   collision check (TG `:467`'s copy of it stays, comment reworded); `test_buildgen_driver_registry.py` `:163-209`
   and the `data_fields` parts of `:214` and the locale probe; EC rows `:248`, `:330`, `:333`, `:350`, `:354`, `:363`,
   `:376`, `:389`, `:411` (+`_settings_key_served_twice`), `:428`, `:439`. EC `:356` moved to 32,767; EC `:407-410`
   now plants `_NAME = "SCD30"` in bmp3xx (an instance-vs-instance clash). TV `:1414` changed first (a warn_* on scd30
   builds and the generated module equals the one without it): red, green. TV `:871`, `:886` call the restored
   signature: red (TypeError), green. TV `:1972` (now upper bound only) red on the fix text, green; `:1983` keeps its
   upper edges. Contract test `test_toml_schema_contract.py`: `name_ext` no longer required; SPEC L.3 rows follow.
   **Kept by proof, not removed: `instance.irq-pull-up-type`** (EC `:385`, TV `:559`, `:567` stay). codegen renders the
   value with `str()` (`codegen.py:530`, as at 25caf528 `:195`), so `irq_pull_up = "false"` emits the bare name
   `false`: a NameError in `build_system()` at every boot, a boot loop by reading, which is PLAN B8's keep condition.
3. **Kept**: the UART timing ranges, ring, cap and CRC checks, rxbuf/txbuf above 32,766, `hotspot-time-min-range`,
   `_Default` keyword-only, `@limits` non-finite. Their tests stayed green.
4. **Compile check: removed.** `_compiled()` and its three calls. Went first: EC `:600-612`; also TG
   `test_a_generator_bug_emitting_invalid_python_is_an_internal_error` (a second pin, found by the green run; its
   `generate_module` import went too). EC's docstring loses the BuildInternalError clause.
5. **The boot entry's `report_if_fatal(ended)`: removed** with its import. Changed first: TG `:151`, `:160`,
   `_shared_head` `:629`: red, green. BE: the stub no longer stands in for `asy_print_log` (on the old entry the real
   module's `const` import then fails: red). `tests_scripts/test_fatal_report_sites.py` no longer scans the two boot
   entries (their handler runs after the loop; nothing reads the record): a pin of this call, not on the list.
6. **The loop-end print: removed** (owner, O1). `except BaseException:` with `record_loop_end()` alone; the `ended`
   pre-bind and its comment and `pyproject.toml`'s F811 go. Changed first: TG `:154`, `:159-160`; BE's stub now also
   stands in for `sys` and records `print_exception`, asserting none: red (`[RuntimeError('stub')]`), green.
   `test_ruff_exemptions_live.py` green. SPEC A.7: "neither printed (at every `DebugLevel`) nor re-raised".
7-10. **Kept**: the start line (BE `:138` green), the boot entry otherwise, the bus-spread order, the device module.
11. **SetupFct: `Callable[[], Awaitable[None]]`.** `test_asy_system_service.py`'s `_setup_unit` answers None
   (mechanical). A planted `-> bool` neopixel setup fails the main mypy pass on all six devices (`b8_red_setupfct`).
12. **Page build-date stamp: removed** (owner, O2a). `js/shell.js`, `js/main.js`, `js/app.js` and
   `tests_js/shell.test.js` are now byte-identical to 656fc82f^ (before the stamp); the stager, `build_website.sh` and
   `build_firmware.py` take/pass no `--build-date`. Went first: `shell.test.js` `:358-386`, `:603-618`, `:653-706` (the
   entries' describe and its `vi.mock` came with the stamp); `test_build_website_sh.py` `:148` (usage text), `:164-169`;
   `test_build_firmware.py` `:81-82`; `test_stage_website.py`'s two stamp tests (not on the list);
   `test_host_cli_exit_idiom.py` drops the stager's `--build-date yesterday` (its missing definitions file is the
   malformed input now). The watch's first-build reload cases green. SPEC B (1948) and L.7 (11396), README.
13. **Non-object GET banner: restored** (owner, O2b): `body === null` and the typing cast; `describeGetFailure()`'s
   ok branch is the empty-body wording alone. `render.test.js:1557` changed first (paints with no banner): red
   (`b8_red2`, waitFor timed out), green. SPEC H's row.
14. **Kept** ("65535+"). 15. **Solid stripes: restored** (owner, O2d); the two rules' diff against 25caf528 is the
   comment line alone; SPEC H's divergences row loses the double-stripe clause.
16. **Kept.**
17. **Browser validator: restored, in the foundations' scope (agent, 2026-11-04; for the lead).** The per-hint
   additions after U10 go: field key/label/kind, composite sub-fields, duplicate keys, errcount module entries,
   submit-without-put, statusPath, clearable, codeTones, specialValues, ignoredWhenSet, resolution, confirm,
   defaultDecimals, the setTimeout ceiling, the group non-object guard (a typing cast now). Kept as U6 (an owner
   foundation, PLAN 0) left them: version/major, shape, pollGroup, intervals (positive), path, decimals, format,
   codes, alwaysExecuted, byteLength, shape hints and the errcount codes block, with today's format and shape sets
   (the generator emits `lasttaskend`, `hostName`, `ipv4List`). `js/definitions.js` 530 to 355 lines. The Python
   mirror (`test_buildgen_definitions.py`) follows rule for rule; the shared corpus keeps U10's 70 cases plus the
   three new set members and the two alwaysExecuted cases (134 to 75); `test_definitions_js_mirrors.py` loses the
   poll-ceiling pin and its expression readers. Went first: `definitions.test.js` ceiling, defaultDecimals and
   confirm cases. Every device's generated definitions validate (both sides). Complexity ceilings hold
   (`lint-ceilings.test.js` green). SPEC G's mirror list.
18-21. **Kept** / B7's.
22. Hunks: no further hunk changed beyond the rows' own consequences named above.

## Removed items (knowledge lines; code at d5c90b71)

Each: what it refused or did / why it went; its code is at d5c90b71 (`buildgen/validate.py` unless named).
- `bus.i2c-timeout-max`: refused a timeout above 200,000 us / merged into the one range check, same bound.
- `bus.boot-clear-budget`: refused I2C buses whose summed worst boot clear passed 3/4 of the watchdog / dominated:
  two buses at the bound clear in 4.4 s, under it.
- `bus.i2c-timeout-consumer`: refused 2 x timeout above the smallest hard consumer (a link's reply slack, the
  watchdog beside one supervisor sleep) / the watchdog branch never binds; no device TOML reaches the link branch.
- `bus.i2c-frequency-range` (`_I2C_FREQUENCY_MAX_HZ`): refused a frequency outside 1..1,000,000 Hz / no boot refusal
  or loop (lead decision 1: 0 divides to a wrong rate, logged read errors).
- `bus.uart-baudrate-range` (`_UART_BAUDRATE_MAX`): refused a baud outside 1..7,812,500 / the port keeps its default
  for 0 or less (`machine_uart.c:285-287`).
- `_UART_BUFFER_MIN`: refused rxbuf/txbuf below 32 / the port raises a smaller one to 32 itself.
- `bus.uart-shared` (`_check_uart_bus_single_owner`): refused two instances on one UART / a TOML edit only; dev uses
  uart0 and uart1.
- `instance.uart-baud-mismatch` (in `_check_uart_link_roles`): refused a link pair at two bauds / a dead link,
  diagnosed and never negotiated (CLAUDE.md).
- `device.conn-fail-to-hotspot-range`: refused `conn_fail_to_hotspot` below 1 / the hotspot opens at the first
  failure, no loop.
- `device.hostname-label` (`_host_label_ok`): refused a name making the hostname no RFC 1123 label / Wi-Fi's own
  schema check drops such a default at boot.
- `instance.name-ext-missing`: refused a repeatable driver without `name_ext` / absent reads as "" (model.py).
- `names.logger-collision`'s mandatory-module and CFGMGR claims (`_MANDATORY_MODULE_FILES`): refused an instance
  named like a mandatory module or a config store's logger / errcount's last registration wins, no boot effect;
  the pre-audit instance-against-instance check is back.
- `names.settings-key-collision`: refused a key two SETTINGS_GROUPS rows serve / only a buildgen edit repeats one.
- `source.field-unknown`, `source.fields-unreadable`, `driver_registry.data_fields()` and helpers
  (`buildgen/driver_registry.py:193-244`): refused a `{source, field}` naming no namedtuple field / the consumer
  reads it with `getattr(..., None)` (`asy_notification_service.py:207`, `asy_sgp40_driver.py:303`).
- `wiring.warn-outside-notification`: refused a warn_* key off the notification / codegen and the graph read the
  notification's alone, so it wires nothing.
- `generate._compiled()` (`buildgen/generate.py:45-51`): compiled each generated text, a SyntaxError a
  BuildInternalError / a generator bug never a TOML's; mpy-cross, ruff, mypy and every importing test compile it.
- The boot entry's `report_if_fatal(ended)` (`buildgen/codegen.py:853`, `:868`): recorded a C-stack overflow ending
  the loop / after `asyncio.run()` has raised nothing reads the flag.
- The boot entry's `sys.print_exception(ended)`, the `ended` pre-bind and F811 (`codegen.py:854-870`,
  `pyproject.toml:192-195`): printed the loop's ending exception at every level / owner O1 (level 0 silent).
- The page build-date stamp (`js/shell.js:19-26`, `:118-121`, `buildDateOf()`; the stager's `--build-date`,
  `_BUILD_DATE`; `build_website.sh`'s and `build_firmware.py`'s stamp lines): reloaded a page whose stamp differed
  from the device's BuildDate / owner O2a; the first-build watch stays.
- The non-object GET banner (`js/render.js:322`, `:619`): refused a GET answering JSON that is no object / owner
  O2b; every GET route answers an object.
- Double Apply stripes (`html/style.css:378-411`): Invalid/Failed drawn double / owner O2d.
- The browser validator's post-foundation per-hint checks (`js/definitions.js:77-393`, `:482-530`; the Python mirror,
  corpus rows and the poll-ceiling pin with them): refused malformed hints a build cannot emit / buildgen's `web.*`
  rules, the stager's `_check_inlined` and two test tiers check the same generated file (no proof under PLAN 0).

## Gate

Run once on 6f24e171, every stage through `run.sh` (`S/u35r/r1/B8/ftmp` held the driver; logs `b8_gate_*.log`):
- `scripts/test.sh` (b8_gate_unit) and `GC_THRESHOLD=32768 scripts/test.sh` (b8_gate_unit_32768): **one failure each,
  the same**: `test_comment_block_cap.py[tests_scripts/test_fatal_report_sites.py]`, a 4-line docstring (my edited first
  line ran to 127 columns, which the cap counts as two). Class (b), my deliverable. Everything else green: files 137
  passed, 1 failed; tests_scripts 6,951 passed, 1 failed; MicroPython tests 5,836 passed, 0 failed; zero `MemoryError`
  or "memory allocation failed" at both stages. Skips are the suite's own per-device "runs on" ones (84 files'
  worth, 4 more than B7's gate log: `test_digital_twin_sensortask_integration.py` on grkizi, klkizi, schlafzi and wozi,
  from B7's fix-round commits, not this change); the six real-firmware builds are the suite's opt-in skips.
- Fix round (the one allowed): the docstring rewrapped, then only the failing files (`b8_fix1`):
  `test_comment_block_cap.py` and `test_fatal_report_sites.py` 689 passed; ruff clean. Committed as 3d0e36bb.
- Twin, dev: suite and harness at -1 and at 32768 all PASS (suite 15/15 checks each; harness 65 scenarios passed,
  2 skipped by the suite's own device rules, each); every run's log "carries none of ('MemoryError', 'memory
  allocation failed')".
- npm (b8_gate_npm): `lint` and `typecheck` clean, `test:unit` 1,271 passed, 0 failed.
- Before the gate, on the changed tree: lint_direct clean (ruff, shellcheck, actionlint, zizmor, guards), the three
  mypy passes clean (276, 314, 59 files), the changed pytest files 1,434 + 738 passed, BE 5/5, system service 187/187,
  the changed vitest files 249 passed (lint ceilings included).

## Sizes

`module_sizes.sh` (`S/u35r/r1/B8/sizes/`): `src/` 194,887 B at d5c90b71 to **194,883 B at 3d0e36bb (-4 B,
`asy_base_classes.py`'s `SetupFct`)**, 15,532 lines unchanged; against R0's 208,708 B, -13,825 B. No module grew.
FW: `scripts/build_firmware.py dev` (b8_fw, after the gate) gives `imageFreeBytes` **60,492 B** (B7's head had 58,956 B,
so about +1.5 KB, the frozen website's smaller validator and shell); R0 had 43,068 B. The record says `dirty` only for
the untracked `node_modules` link.
Net lines against d5c90b71: `buildgen/` +39 -306; `src/` +1 -1; `js/` +44 -235; `html/` +3 -5; `scripts/` +8 -31;
`devices/` none; `tests/` +12 -14; `tests_js/` +9 -163; `tests_scripts/` +65 -664; SPECIFICATION/README/BACKLOG +54 -68;
`pyproject.toml` +3 -3. Against 25caf528, `buildgen/` went from +4,471 -1,783 to +4,210 -1,789 and `js/` from +3,034
-1,198 to +2,846 -1,201: no row grew the code.

## Decisions taken (agent, 2026-11-04)

- Row 2's `instance.irq-pull-up-type` kept (above): its violation is a boot loop by reading.
- Row 17 restored to the U6/U10 foundation scope rather than 25caf528's two hints: U6's hints are an owner
  foundation (PLAN 0, "plus the owner's foundations (U1-U8 ...)"); the pre-audit text would drop them. To the lead.
- The removed rules' further pins (fatal-sites boot-entry scan, TG's second compile test, TV's settings guard, the
  stager's stamp tests, the corpus and mirror rows) went with them; the listed tests were not all of them.

## Findings

- `_UART_BUFFER_MAX`'s comment cites `ports/rp2/machine_uart.c:68, :376-377`; at v1.29.0 `MAX_BUFFER_SIZE` is `:69` and
  the ValueError `:374-375` (rx) and `:389-390` (tx). A stale comment beside my edit; not changed (the gate stands).
- `SETTINGS_GROUPS` stays in `validate.py` though no check there reads it any more (codegen and the tests do), and
  `_owns_config_store()` is read by `generate.py` alone: a home question for R2, no row of mine.
- `HardConsumer.what`/`.relief` now have no reader (every caller reads `.ms`): row 20's, R2.
- `instance.uart-crc-mismatch` stays (row 3, owner) while the baud mismatch went: both are a dead link the same way.
  Named only.
- A slip before the go-ahead: two one-second local `python3` reads of a JSON test data file (the corpus listing) ran
  outside `run.sh` at about 06:38 UTC, before the lead's 06:42 message. No test, build or port-binding run.
- Records: `S/u35r/r1/B8/ftmp/` held source copies, edit scripts and the gate driver; deleted before this hand-back.

## Fix round

Lead decisions 9-12 on `B8/FALSIFY.md` (claims 1, 10, 12; decision 7). One commit, **8a32d826**, on 3d0e36bb, the
same rules. It supersedes items 2 (the frequency range and the buffer floor are back) and the CRC line of 3 above.

- **F1, `bus.i2c-frequency-range` restored** as at d5c90b71: `_I2C_FREQUENCY_MAX_HZ` (`buildgen/validate.py:84`), the
  check in `_check_i2c_bus()` (`:537-546`), TV `test_an_i2c_frequency_outside_the_silicon_range_is_rejected` and
  `..._at_the_silicon_edges_builds` (`tests_scripts/test_buildgen_validate.py:584-599`), and EC row `:340`. Each restored
  function is the same text as at d5c90b71 (compared by AST). Red on 3d0e36bb (`b8_fx_red`: TV 3 cases, EC's
  one-row-per-rule test and the row), green.
- **F2, `_UART_BUFFER_MIN` restored** (`:85`) with the 32..32,766 rxbuf/txbuf checks (`:822-839`), TV
  `test_a_uart_buffer_outside_the_port_range_is_rejected` at `[31, 0, 32767]` and `test_the_uart_buffer_edges_pass_the_range_check`
  with its txbuf-32 edge (`:1713-1733`), both as at d5c90b71, and EC txbuf back to 31 (`:343`). Red on 3d0e36bb
  (6 TV cases, the EC row), green. `_check_uart_bus()` differs from d5c90b71 only by the baud range, which stays out.
- **F3, the mirror rejects a non-object group** again: U10's line at `tests_scripts/test_buildgen_definitions.py:150-152`
  (`g: object`, "is not an object"), no `isinstance(g, dict)` filter at `_section_problems()`'s call. The corpus
  case "a group that is a string" is back (`definitions_shape_cases.json:50`, 76 cases): red on 3d0e36bb's mirror
  (`b8_fx_red2`), green on both sides. "A group that is null" stays out: the JS runner asserts
  `validateDefinitions(definitions).length === 0` (`tests_js/definitions-shape-corpus.test.js:8`), so a throw fails
  the case; it is not counted as a rejection.
- **F4, stale text**: SPEC `:831` and `:13227` say "at most 4.4 s on two buses at" the bound in place of the build's
  three-quarter refusal; `:11938` loses the `_BOOT_CLEAR_BUDGET_MS` clause; `:10881-10883` loses the compile sentence;
  `:4392` reads `Awaitable[None]`. Comments: `tests_scripts/test_digital_twin_scenarios.py:252` and
  `tests_hardware/flash/test_memory_stress.py:172` no longer name a build rule. Nothing added.
- **F5, `instance.uart-crc-mismatch` removed**: the check in `_check_uart_link_roles()`, its EC row, TV
  `test_a_uart_pair_whose_crc_modes_differ_is_rejected`, SPEC `:11138`, and the four other places stating the
  build holds both ends' CRC equal (SPEC C.7.2's refusal list `:3826`, the L.3 `crc` row, L.4's check list, L.5's
  summary: "agreed on both ends out of band" where a row needs it). **`instance.uart-crc-mode` kept** (agent,
  2026-11-04; for the lead). Its violation never reaches construction: codegen renders only a known mode's class
  (`crc=CRC16()`, `buildgen/codegen.py:185`). Without the check an unknown mode crashes the build with a raw
  traceback, a `KeyError` at `_uart_crc_width()` (`buildgen/validate.py:1211`, called from the rxbuf floor `:886`;
  codegen's own guard at `codegen.py:116-117` is a BuildInternalError). That breaks the kept error contract (row 18,
  H1/H2: every TOML error one line, no traceback). By decision 7's letter it would go, so it goes to the lead.

Gate on 8a32d826, one step at a time:
- `rebuild.sh` (b8_fx_rebuild) ok.
- `checks.sh` (b8_fx_checks): lint_direct rc=0; mypy main 276, host 314 and twin 59 files, no issues. Readers
  (TV, EC, definitions, digital_twin_scenarios, timing_budget, toml_schema_contract, comment_block_cap,
  buildgen_generate): 2,046 passed.
- npm (b8_fx_npm): lint and typecheck clean; `test:unit` 1,272 passed, 0 failed (one more: the restored case).
- `tests/test_generated_boot_entry.py` (b8_fx_be): 5/5 at -1 and 5/5 at 32768.
- Dev firmware (b8_fx_fw, commit 8a32d826): `imageFreeBytes` **60,492 B**, unchanged from 3d0e36bb. `src/` is
  unchanged by this round: 194,883 B, 15,532 lines (`sizes/head_fix1.tsv`).

Net lines, against d5c90b71 and against 3d0e36bb:
- `buildgen/`: +33 -300; +17 -17.
- `tests_scripts/`: +61 -648; +36 -24.
- `tests_hardware/`: +1 -1; +1 -1.
- docs: +61 -77; SPECIFICATION.md +10 -12.
- `src/` +1 -1, `js/` +44 -235, `html/` +3 -5, `scripts/` +8 -31, `tests/` +12 -14, `tests_js/` +9 -163: all unchanged
  by this round.
- F1 and F2 restore d5c90b71's text exactly, so nothing grows past its d5c90b71 form.
