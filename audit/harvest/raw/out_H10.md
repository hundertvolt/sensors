# Harvest H10 — tests_scripts/ host-side pytest tier (snapshot 2a88cc8)

## tests_scripts/_devices.py
- INVAR | tests_scripts/_devices.py:1-3 | "Six test modules carried their own copy of the same six names; a seventh device would have been generated" | The device set for every device-parametrized host suite is discovered from `devices/*.toml`, not listed; any suite that still hardcodes the six names (CI matrices, JS) is outside this guard | area: TEST | related: CI.T07
- INVAR | tests_scripts/_devices.py:15-18 | "A leaked live-tree fixture ... must never be mistaken for a real device" | Device discovery filters `zz_test_*` because the pytest tier runs concurrently and `devices/` can hold a live-tree fixture mid-test; filter is by name prefix only | area: TEST | related: TEST.T13
- INVAR | tests_scripts/_devices.py:20 | "every device-parametrized suite would silently collect nothing" | Import-time assert fails the whole tier if `devices/` has no TOML (guards vacuous parametrization) | area: TEST | -
- DRIFT | tests_scripts/_devices.py:1-3 | "Six test modules carried their own copy" | Historic count/narrative in a header (current-state rule); count not re-verified | area: DOC | related: DOC.T05 (low)

## tests_scripts/_script_loader.py
- INVAR | tests_scripts/_script_loader.py:2-3 | "Split out of conftest.py so this bare import cannot collide with tests_hardware/'s own bare \"conftest\"" | Module split exists only because mypy resolves one bare name to one file per run (host_typecheck pass covers both tiers) | area: TEST | related: SCR.T15
- ASSUME | tests_scripts/_script_loader.py:19-22 | "Registered in sys.modules BEFORE exec_module()" | Loader registers every script under a bare name in `sys.modules` (needed for `@dataclass` + future annotations); a name collision between two loaded scripts or a real module would silently shadow (low) | area: TEST | -

## tests_scripts/_toml_fixtures.py
- LIMIT | tests_scripts/_toml_fixtures.py:5-6 | "dump_toml() is not a general TOML writer - it covers only the shape buildgen/'s own schema uses" | Fixture serializer cannot emit inline tables, arrays of tables beyond `[[instance]]`, or nesting deeper than `[instance.wiring.X]`; negative-path tests needing those shapes skip (see test_buildgen_validate.py:1208) | area: TEST | -
- MIRROR | tests_scripts/_toml_fixtures.py:13-16 | "matches buildgen.model.TomlDoc's own shape; kept as a local alias" | Local `TomlDoc` alias duplicates `buildgen.model.TomlDoc` by hand | area: TEST | -
- DRIFT | tests_scripts/_toml_fixtures.py:14-15 | "deliberately import-independent from buildgen/ - see the module docstring" | The module docstring (:1-3) says nothing about import independence — dangling pointer (low) | area: DOC | -
- RISK | tests_scripts/_toml_fixtures.py:27 | "\"hotspot_password\": \"12345678\"" | Base fixture carries the same literal as the shared default hotspot password (test data, not a secret; recorded for credential-consistency sweeps) (low) | area: SEC | related: HW.T11

## tests_scripts/conftest.py
- INVAR | tests_scripts/conftest.py:15-18 | "pytest's rootless import mode puts only tests_scripts/ on sys.path, never the repo root" | conftest prepends REPO_ROOT to `sys.path` at import; every `import buildgen` in the tier depends on this side effect | area: TEST | -
- INVAR | tests_scripts/conftest.py:22-28 | "Reclaims any `devices/zz_test_*.toml` a KILLED earlier run left behind ... race-free by construction" | Session-start autouse fixture unlinks files in the real `devices/` tree; "race-free" assumes no concurrent pytest session (e.g. two local runs, or test.sh's own sweep) is mid-test | area: TEST | covered-by: TEST.T13
- ASSUME | tests_scripts/conftest.py:46-48 | "Mirrors scripts/build_firmware.py's own main()'s --toolchain-dir default resolution exactly" | `micropython_dir` fixture hand-mirrors build_firmware.py's PICO_TOOLCHAIN_DIR/~/pico-toolchain default; "scripts/test.sh/CI always provisions a real checkout here before this suite runs" | area: TEST | -
- MIRROR | tests_scripts/conftest.py:46-48,55 | "Same path scripts/run_digital_twin_ci.sh's own $micropython_bin resolves to" | Unix-port binary path (`ports/unix/build-standard/micropython`) is duplicated from build_firmware.py and run_digital_twin_ci.sh by hand | area: TEST | related: SCR.S05
- SUPPRESS | tests_scripts/conftest.py:55-60 | "pytest.skip(f\"MicroPython Unix port not built at {path}" | Every test using `micropython_bin` SKIPS (not fails) when the standard Unix port is absent; a bare `pytest tests_scripts` on an unprovisioned box passes with those tests silently skipped | area: TEST | related: TEST.T13
- LIMIT | tests_scripts/conftest.py:60 | "build-standard" | The fixture never checks which variant the binary is (settrace vs standard), unlike test.sh's `hasattr(sys, "settrace")` probe (low) | area: TEST | related: SCR.S05

## tests_scripts/buildgen_fixtures/malformed_missing_device_table.toml
- INVAR | tests_scripts/buildgen_fixtures/malformed_missing_device_table.toml:1-5 | "copied into devices/ under a test-only name for the duration of that one test, then removed" | Fixture is placed into the live `devices/` tree (not tmp) because build_website.sh always cd's to the repo root | area: TEST | covered-by: TEST.T13

## tests_scripts/buildgen_fixtures/multi_instance.toml
- PLATFORM | tests_scripts/buildgen_fixtures/multi_instance.toml:6-8 | "sgp40 has no address-select pin, so the two instances must sit on different buses - a real hardware constraint" | Datasheet fact (SGP40 fixed address) the fixture shape depends on | area: SENS | -
- DRIFT | tests_scripts/buildgen_fixtures/multi_instance.toml:16-17 | "Not a real device - never flashed, never referenced outside tests_scripts/test_buildgen_*.py" | Both synthetic fixtures are also booted by tests_scripts/test_digital_twin_generated_boot.py:57 (globs buildgen_fixtures/) and used in digital_twin/README.md:247-273; same claim at novel_combo.toml:4-5 | area: DOC | -

## tests_scripts/buildgen_fixtures/novel_combo.toml
- ASSUME | tests_scripts/buildgen_fixtures/novel_combo.toml:2-5 | "existing drivers mixed in a pin/bus layout none of the 6 real devices/*.toml use" | Novelty claims (two SCD30s, BMP3xx at 0x76, one warn_* signal, uart on GP16/17) are relative to the current six TOMLs and are not machine-checked; a device TOML adopting the same layout would silently make the fixture non-novel | area: GEN | related: GEN.T06
- PLATFORM | tests_scripts/buildgen_fixtures/novel_combo.toml:44-48 | "uart1 has only two legal pairs at all (GP4/5, GP8/9 - buildgen.pico_gpio.UART_ROLE)" | RP2040 pin-mux claim embedded in a fixture comment; correctness owned by pico_gpio's table | area: GEN | related: GEN.T07
- PLATFORM | tests_scripts/buildgen_fixtures/novel_combo.toml:10-11 | "BMP3xx at the alternate hardwired-address-select value (0x76, every real device uses 0x77)" | Chip address fact and a claim about all real devices | area: SENS | -
- ASSUME | tests_scripts/buildgen_fixtures/novel_combo.toml:107-109 | "dev.toml's own instance always wires fram_target, so this fixture is what exercises the \"no fram_target\" branch" | The only coverage of ISL29125's no-FRAM branch is this synthetic fixture | area: GEN | -

## tests_scripts/test_bench_harness_helpers.py
- SUPPRESS | tests_scripts/test_bench_harness_helpers.py:22-24 | "# noqa: E402  (the sys.path line above is what makes these importable)" | Three E402 suppressions; needed because a non-sys.path statement (`TESTS_HARDWARE = ...`, `if TYPE_CHECKING:`) precedes the imports (CLAUDE.md's E402 rule) | area: TEST | -
- SUPPRESS | tests_scripts/test_bench_harness_helpers.py:78 | "# type: ignore[arg-type]" | Duck-typed FakeBoard/FakeBench passed where real harness types are declared | area: TEST | -
- LIMIT | tests_scripts/test_bench_harness_helpers.py:98-112,123-125 | "Thread-target functions whose try around http_client.fetch() names OSError but not HTTP_ERROR" | Structural guard over `tests_hardware/bench/test_*.py` only; flags a `try` that catches OSError but not HTTP_ERROR/Exception/BaseException. Does NOT flag a worker with no `try` at all around `fetch()`, a fetch reached via a helper, a Thread target passed positionally or defined in another module, or anything in flash/ or device_scripts/ | area: HW | related: HW.T12
- ASSUME | tests_scripts/test_bench_harness_helpers.py:99-100 | "a cut-off answer is an HTTPException, which then kills the thread and silently stops its load" | Load-generator threads that die silently make a bench load test under-load without failing; the guard is the only protection | area: HW | related: HW.T05
- LIMIT | tests_scripts/test_bench_harness_helpers.py:44,52,59,135 | "assert 0.4 < time.monotonic() - started < 2.0" | Wall-clock bounds (0.5 s, 0.4-2.0 s, 2.0 s) on host timing; sensitive to a loaded CI runner (the tier runs concurrently with the MicroPython tier) | area: TEST | related: TEST.T04
- LIMIT | tests_scripts/test_bench_harness_helpers.py:138-143 | "for toml in sorted((harness.REPO_ROOT / \"devices\").glob(\"*.toml\"))" | Globs the live `devices/` without `_devices.py`'s `zz_test_*` filter; would pick up a live-tree fixture if one existed at that moment (low) | area: TEST | related: TEST.T13
- MIRROR | tests_scripts/test_bench_harness_helpers.py:138-143 | "configured_max_connections_is_the_builds_own_ceiling" | Pins `tests_hardware/harness.configured_max_connections()` == `buildgen.validate.device_max_connections()` for every device (host harness ↔ build) | area: HW | -

## tests_scripts/test_bench_no_task_ended_completeness.py
- INVAR | tests_scripts/test_bench_no_task_ended_completeness.py:1-3 | "\"no Traceback\" alone passed the NTP give-up that restarted a task a minute and rebooted every four" | Standing rule: every fault-injecting bench test must assert no task ended (SPEC C.7.2); enforced by this AST guard | area: HW | related: HW.T05
- LIMIT | tests_scripts/test_bench_no_task_ended_completeness.py:15-19,27-38 | "_FAULT_INJECTORS = frozenset({\"ap_down\", \"inject_network_degradation\", \"block_udp_ports\"," | Pinned sets: 5 fault injectors, checkers `assert_no_task_ended`/`_restore_ssid_over`. Scans only module-level `def test_*` in `tests_hardware/bench/`; does NOT see class methods, fixtures, faults injected through helper functions, a new BenchBridge fault method not in the set, call ORDER (checker before fault passes), or flash/ tier | area: HW | related: HW.T05
- SETTLED | tests_scripts/test_bench_no_task_ended_completeness.py:15-16 | "kick_all_stations() is absent on purpose: it is the reconnect nudge every hard_reset() test uses, not a fault" | Deliberate exclusion from the fault set | area: HW | -
- SUPPRESS | tests_scripts/test_bench_no_task_ended_completeness.py:20-24 | "\"ap_down() is join mechanics, not a fault\"" | Two named exemptions (DHCP churn and station-management churn tests); staleness is checked (:54-56) but not whether the exemption reason still holds | area: HW | -
- LIMIT | tests_scripts/test_bench_no_task_ended_completeness.py:41-46 | "assert len(names) >= 15" | Vacuity floor: two named tests plus a count floor of 15 fault tests | area: HW | -
- MIRROR | tests_scripts/test_bench_no_task_ended_completeness.py:62-66 | "{\"num\": 1, \"type\": \"W\"}]}, False),  # \"Task ended - attempting restart\"" | Pins SYSTEM log codes W1 (task ended/restart), E5 (task ended with exception), E4 (budget reboot) as the task-ended signal — must match `src/system_service.py`'s errno/wrnno assignment and C.7.1 | area: HW | related: XCUT.T07
- ASSUME | tests_scripts/test_bench_no_task_ended_completeness.py:63 | "a board whose SYSTEM never logged anything reports no entry at all" | Helper treats a missing SYSTEM key in `/status` errcount as a pass; a /status that omits SYSTEM for another reason (degraded source) also passes | area: HW | related: WEB.S09 (low)
- SUPPRESS | tests_scripts/test_bench_no_task_ended_completeness.py:13,69 | "# noqa: E402" / "# noqa: FBT001" | E402 after `_TESTS_HARDWARE =` statement; FBT001 on a bool parametrize argument | area: TEST | -

## tests_scripts/test_bench_restores_serving.py
- INVAR | tests_scripts/test_bench_restores_serving.py:1-3 | "run_isolated() leaves main.py stopped, and the one bench test that did not restore it failed every network test after it" | Rule: every bench test calling `run_isolated()` must reach `restore_board_to_serving()` in a `finally` or a same-module fixture teardown | area: HW | related: HW.T05
- LIMIT | tests_scripts/test_bench_restores_serving.py:34-65 | "sorted(p for p in BENCH.glob(\"test_*.py\") if f\".{_RUNS}(\" in p.read_text())" | Scans only `tests_hardware/bench/`; flash-tier tests that run device scripts are NOT checked; only attribute calls `.run_isolated(` count; fixtures from conftest.py are not recognised as restoring (false positive, not false negative) | area: HW | -
- LIMIT | tests_scripts/test_bench_restores_serving.py:68-70 | "Guards the detector: an empty set would pass the test below vacuously." | Vacuity floor pins two named files (`test_heap_under_connection_ceiling.py`, `test_serving_heap_at_default_gc.py`) | area: HW | -

## tests_scripts/test_build_firmware.py
- SUPPRESS | tests_scripts/test_build_firmware.py:196-201 | "os.environ.get(\"RUN_SLOW_FIRMWARE_BUILD\") != \"1\"" | The only real ARM firmware build is skipped unless opted in; CI's `firmware-build-verify` sets it; a plain local `scripts/test.sh` never builds a UF2 | area: SCR | covered-by: SCR.T13
- LIMIT | tests_scripts/test_build_firmware.py:213-216 | "assert data[:4] == b\"UF2\\n\"" | UF2 "validity" = magic bytes + length multiple of 512; frozen content, boot entry, board family ID are not checked | area: SCR | related: SCR.T10
- LIMIT | tests_scripts/test_build_firmware.py:90,124,149,160 | "@pytest.mark.parametrize(\"device\", [\"wozi\", \"dev\"])" | Staging-logic tests hardcode two devices instead of `_devices.DEVICE_NAMES`; the four other devices' staging is exercised only by the opt-in real build | area: TEST | related: CI.T07
- ASSUME | tests_scripts/test_build_firmware.py:114-116 | "\"dev\" legitimately wires every driver in src/, so its unrelated set is empty" | Non-vacuity of the "no unrelated module staged" check rests on wozi alone (never wired to uart_link) | area: TEST | -
- ASSUME | tests_scripts/test_build_firmware.py:36-38 | "a contract mismatch buildgen's guarantees should prevent ... build_stage_dir reading only four attributes" | Fake GeneratedDevice fidelity rests on build_stage_dir reading exactly four attributes | area: SCR | -
- ASSUME | tests_scripts/test_build_firmware.py:55-56 | "No src/ file is called \"main.py\" today" | Reserved-name collision guard is reached only through a patched fake tree | area: SCR | -
- INVAR | tests_scripts/test_build_firmware.py:151-157 | "config_manager.py is a known if TYPE_CHECKING: user ... CLAUDE.md's hard rule against editing src/ for a build-only concern" | Pins that staged copies are TYPE_CHECKING-stripped while src/ keeps the guard; only config_manager.py is checked | area: SCR | related: SCR.T10
- LIMIT | tests_scripts/test_build_firmware.py:77-87 | "Each device's boot module is frozen as \"main.py\", so the default board manifest is reused unchanged" | Manifest test checks two substrings only; PLATFORM history: the old custom `_boot.py` skipping the board manifest "broke USB entirely (Part F.1)" | area: SCR | -
- LIMIT | tests_scripts/test_build_firmware.py:192 | "assert \"no-toolchain-here\" in result.stderr or \"toolchain\" in result.stderr.lower()" | Loose oracle for the missing-toolchain CLI path (any stderr mentioning "toolchain" passes) (low) | area: SCR | -
- DRIFT | tests_scripts/test_build_firmware.py:207 | "Parametrized over all six real devices" | Parametrization is now discovered (`DEVICE_NAMES`), so "six" is a hardcoded count that will go stale on a seventh device (low) | area: DOC | related: DOC.T08
- ASSUME | tests_scripts/test_build_firmware.py:204-205 | "Needs the toolchain already installed, which test.sh and the unit-tests job both provision first" | Opt-in test does not itself skip on a missing toolchain | area: SCR | -

## tests_scripts/test_build_frozen_html_sh.py
- LIMIT | tests_scripts/test_build_frozen_html_sh.py:9-11 | "Grepping the generated text for those literals checks what was archived without running it" | Oracle is substring presence of mount paths in freezefs output; archived content, gzip validity and runtime mount are not checked here (content is `tests/test_website_build_integration.py`'s job) | area: SCR | -
- LIMIT | tests_scripts/test_build_frozen_html_sh.py:73-76 | "test_missing_source_dir_fails_instead_of_silently_producing_an_empty_archive" | Missing-dir case asserts only nonzero exit and no output; an empty-but-existing source dir, and paths with spaces (unquoted loop, SCR.S08), are untested | area: SCR | related: SCR.S08
- SETTLED | tests_scripts/test_build_frozen_html_sh.py:29 | "No default source since html_stub/ was retired" | build_frozen_html.sh must refuse without HTML_SRC_DIRS | area: SCR | -

## tests_scripts/test_build_website_sh.py
- DRIFT | tests_scripts/test_build_website_sh.py:26-29 | "see scripts/build_website.sh's own \"Bundling\" comment for why" | Points at a comment the plan records as removed | area: DOC | covered-by: WEB.S21
- LIMIT | tests_scripts/test_build_website_sh.py:113-127 | "build_website.sh's cp lists are hand-kept ... Cross-checking the directories against the script's source makes that loud." | Guard is a substring match of each html/ root file and js/*.js name anywhere in the script text (a comment mention passes); html/ subdirectories and non-.js files under js/ are not checked | area: WEB | covered-by: WEB.S14
- LIMIT | tests_scripts/test_build_website_sh.py:71-73 | "Four devices have no hand-written definitions.json ... \"arzi\" stands in for all four." | Only arzi exercises the buildgen-fallback path here; the count "four" is a dated claim | area: WEB | related: WEB.T12
- INVAR | tests_scripts/test_build_website_sh.py:93-110 | "copied into devices/ under a test-only name, removed again in `finally`" | Test writes `devices/zz_test_malformed_buildgen_fixture.toml` into the live tree; a KILLED run leaks it (reclaimed at next session start by conftest.py) | area: TEST | covered-by: TEST.T13
- LIMIT | tests_scripts/test_build_website_sh.py:49-55 | "test_prototype_only_files_are_never_staged" | Negative list is four hand-named paths (mock-server.js, definitions/*.json); a new prototype-only file is caught only by the :113 guard | area: WEB | -

## tests_scripts/test_buildgen_defaults.py
- ASSUME | tests_scripts/test_buildgen_defaults.py:55-56 | "only the two required=True wiring fields need this mechanism" | Pins that only temperature_source/humidity_source/signal_sink have `_Default<Field>` providers; fram_target is not defaultable | area: GEN | -
- LIMIT | tests_scripts/test_buildgen_defaults.py:62-68 | "def __init__(self, required_one, optional_one=5)" | Parameter extraction is tested for positional args only; keyword-only args are never exercised (the plan records `default_init_params` ignoring them) | area: GEN | covered-by: GEN.S10

## tests_scripts/test_buildgen_definitions.py
- MIRROR | tests_scripts/test_buildgen_definitions.py:19-20 | "BMP3XX_DEVICES = {\"dev\", \"wozi\"}" / "ISL29125_DEVICES = {\"dev\"}" | Hand-kept per-driver device sets must match `devices/*.toml` while the parametrization itself is discovered; a new device carrying BMP3xx/ISL29125 fails until edited | area: TEST | related: GEN.T06
- LIMIT | tests_scripts/test_buildgen_definitions.py:39-41,62-67 | "comparison is insensitive to this generator's own field/group declaration order" | Golden comparison only for wozi/dev and order-insensitive, so field-order differences between generated and hand-written definitions pass | area: WEB | covered-by: WEB.S13
- MIRROR | tests_scripts/test_buildgen_definitions.py:126-129,132-170 | "mirrors js/definitions.js's validateDefinitions() closely enough to prove a generated file would load" | Python re-implementation of the JS loader's shape check; no Node round trip, and drift between `_shape_problems` and `validateDefinitions()` is not detected | area: WEB | related: GEN.T15
- LIMIT | tests_scripts/test_buildgen_definitions.py:248-249 | "Dropping one @web tag doesn't break the build - it just means that field never reaches the website" | Known, pinned behaviour: a schema field missing its `@web` tag silently disappears from the UI | area: GEN | related: GEN.T03
- ASSUME | tests_scripts/test_buildgen_definitions.py:271-273 | "asy_ntp_client.py deliberately never declares its own @web-group for section=system submitGroup=settings (system_service.py is the sole owner)" | Ownership convention for the system settings group | area: GEN | -
- ASSUME | tests_scripts/test_buildgen_definitions.py:379-380,389-390,400 | "buildgen.validate._resolve_instances() always sets resolved_name before definitions generation ever runs" | Three "internal:" invariant guards reached only by hand-built models; relies on validate.py always resolving first (the CLI path is noted as differing in GEN.S08) | area: GEN | related: GEN.S08
- DRIFT | tests_scripts/test_buildgen_definitions.py:178 | "proving generality beyond the 6 real, hand-verified devices" | Hardcoded device count (low) | area: DOC | related: DOC.T08

## tests_scripts/test_buildgen_driver_registry.py
- INVAR | tests_scripts/test_buildgen_driver_registry.py:73,80-81 | "assert {\"fram\", \"neopixel\", \"notification\", \"uart_link\"} == SERVICE_DRIVERS" | Pins the override/service driver set and that `uart_link` is excluded from `SINGLETON_SERVICE_DRIVERS` (CLAUDE.md UART rule) | area: GEN | related: GEN.T13
- ASSUME | tests_scripts/test_buildgen_driver_registry.py:77-79 | "a device wires exactly two instances (initiator/responder)" | Stated uart_link cardinality; not enforced by this test | area: GEN | related: UART.T05
- ASSUME | tests_scripts/test_buildgen_driver_registry.py:94-96 | "NotificationCoordinator's _NAME is \"NOTIFY\", not \"NOTIFICATION\"" | Pins a confirmed-real naming mismatch (L.3) between log name space and TOML driver identity | area: GEN | -

## tests_scripts/test_buildgen_frozen_modules.py
- LIMIT | tests_scripts/test_buildgen_frozen_modules.py:108-111 | "one with no .py file anywhere in the roots contributes nothing rather than raising, so a stale seed name can't break a build" | A stale/misspelled seed name is silently tolerated at closure time (caught later only by build_stage_dir's missing-file check) | area: GEN | related: GEN.S11
- MIRROR | tests_scripts/test_buildgen_frozen_modules.py:51-63,79-91 | "(tmp_path / \"config_manager.py\").write_text(\"\")" | Two synthetic trees hand-list the 13 `CORE_MODULES` names; a change to CORE_MODULES needs both lists edited | area: GEN | related: GEN.S11
- LIMIT | tests_scripts/test_buildgen_frozen_modules.py:49-50,64-66 | "A module only reachable through an `if TYPE_CHECKING:` block never executes on-device" | Only the `try: from typing import TYPE_CHECKING / except ImportError` + plain `if TYPE_CHECKING:` shape is tested; `else:` branches are not (GEN.S11 notes the whole `If` incl. orelse is skipped) | area: GEN | related: GEN.S11
- LIMIT | tests_scripts/test_buildgen_frozen_modules.py:23-26 | "for driver_module in (\"asy_scd30_driver\", ... \"asy_notification_service\")" | Real-device closure checks run on wozi only | area: GEN | -

## tests_scripts/test_buildgen_generate.py
- LIMIT | tests_scripts/test_buildgen_generate.py:5-7 | "never executed under a real interpreter - booting a generated module is Session 5's digital-twin work" | This file proves only `ast.parse` + structure; runtime is the twin tier's job; "Session 5" is an undefined historic label | area: GEN | covered-by: GEN.T10
- DRIFT | tests_scripts/test_buildgen_generate.py:1 | "against all 6 real devices/*.toml" | Parametrization is discovered; "6" is a stale-prone count (low) | area: DOC | related: DOC.T08
- INVAR | tests_scripts/test_buildgen_generate.py:48-53 | "The generated module's single WDT() site needs its own proof." | Pins exactly one `WDT(` substring per generated module; the src/-side check in `test_reset_call_site_invariant.py` "is now vacuous" for sensortask_*.py | area: GEN | covered-by: TEST.S17
- LIMIT | tests_scripts/test_buildgen_generate.py:57-66 | "a feed after every await X.setup() - never inside a loop - is what guarantees" | Feed check matches only lines of the exact form `await <name>.setup()`; a setup call with arguments or another shape escapes it, and "never inside a loop" is not asserted | area: GEN | related: XCUT.T03
- INVAR | tests_scripts/test_buildgen_generate.py:69-97 | "The \"nowhere else\" half is the load-bearing one - this is a boot-only exception to I.4" | Pins the boot-confined `gc.collect()` exception: one collect before the first setup and one after each, total = setups+1, none in `main()` (Measure B, I.4(f.1)); "PLAN B.1.1" is a reference to a retired plan | area: MEM | related: TEST.T03
- SETTLED | tests_scripts/test_buildgen_generate.py:108-121 | "the build date is explicitly injected rather than computed on-device" / "the version no longer lives on GET /status's \"system\" section" | Regression pins for L.7's version placement (`/system` build_info) | area: GEN | related: GEN.T14
- RISK | tests_scripts/test_buildgen_generate.py:405-411 | "assert \"hotspot_password='12345678'\" in result.module_source" | Test pins the shared default hotspot password literal in wozi's generated module (accepted-risk credential; SEC consistency sweep) | area: SEC | related: SEC.T04
- LIMIT | tests_scripts/test_buildgen_generate.py:416-418 | "trigger_sec is declared only on scd30 in every real device and fixture, so bmp3xx's own trigger_sec rendering had never been exercised" | Coverage gap found by a sweep; now covered by a base_doc-mutation test only | area: GEN | -
- ASSUME | tests_scripts/test_buildgen_generate.py:470-472 | "No real bus id or instance label can reach this today (both are drawn from closed sets)" | Identifier guard is the "one guard standing between a bad name and generated source that would not parse"; reached only directly | area: GEN | related: GEN.T02
- ASSUME | tests_scripts/test_buildgen_generate.py:487-489,498-500,512-514,527-529 | "_check_required_fields() rejects a driver with no buildspec.py entry long before codegen sees it" | Four codegen "internal invariant" guards are reachable only by mutating already-validated models | area: GEN | -
- MIRROR | tests_scripts/test_buildgen_generate.py:589-590 | "validate.py checks the stated values against the firmware's lwIP pools; that check is only worth anything if the same values are the ones the device is then built with" | Pins TOML max_connections/backlog → WebserverService kwargs; absent values are left to the class default | area: GEN | related: GEN.T15
- LIMIT | tests_scripts/test_buildgen_generate.py:569-575 | "assert \"Traceback\" not in result.stderr" | CLI error path tested only for a BuildError-producing TOML; non-BuildError failures (e.g. OSError on write) are untested | area: GEN | covered-by: GEN.T16

## tests_scripts/test_buildgen_graph.py
- ASSUME | tests_scripts/test_buildgen_graph.py:28-30 | "The hand-verified construction order (Part A.7): fram before conn/ntp/sysfunct" | Test pins construction order fram→conn→ntp→sysfunct; the plan records A.7 stating a different setup order | area: GEN | related: DOC.S09
- ASSUME | tests_scripts/test_buildgen_graph.py:62-64 | "No real driver's _WIRING requires SGP40_Reader as a producer, so a genuine cycle is not expressible with the actual driver set" | Cycle rejection tested only on a synthetic model | area: GEN | -
- ASSUME | tests_scripts/test_buildgen_graph.py:77-79 | "Only AsyConnTime declares one today, and it is mandatory infra" | Setter-mode wiring on an instance is exercised only synthetically | area: GEN | related: GEN.S09

## tests_scripts/test_buildgen_limits.py
- INVAR | tests_scripts/test_buildgen_limits.py:185-203 | "assert tagged == {\"asy_bmp3xx_driver.py\", \"asy_isl29125_driver.py\"}" | Pinned set of src/ modules carrying `@limits` (BMP3xx address {0x76,0x77} + trigger_sec 1..3600; ISL29125 trigger_sec 1..3600); a new tag elsewhere fails until recorded | area: GEN | related: GEN.T03
- PLATFORM | tests_scripts/test_buildgen_limits.py:196-197 | "0x44 is hard-wired with no address-select pin at all" | ISL29125 fixed I2C address fact | area: SENS | -
- LIMIT | tests_scripts/test_buildgen_limits.py:97 | "One domain per field: two tags would silently let the second win." | Duplicate-domain rejection exists because of a silent-override hazard | area: GEN | -

## tests_scripts/test_buildgen_requires_tag.py
- INVAR | tests_scripts/test_buildgen_requires_tag.py:174-189 | "Every real tag any src/ driver declares today ... assert tagged == {\"asy_scd30_driver.py\", \"asy_sgp40_driver.py\"}" | Pinned `@requires` set: SCD30 timeout>=200000 and frequency<=100000, SGP40 frequency<=400000; ISL29125, BMP3xx and FRAM declare none | area: GEN | related: SENS.T17
- ASSUME | tests_scripts/test_buildgen_requires_tag.py:174-175 | "each traced to its own datasheet citation in the driver file itself" | Datasheet provenance of the bus limits is asserted in comments, not checked | area: SENS | related: SENS.T17
- LIMIT | tests_scripts/test_buildgen_requires_tag.py:319-321 | "A None value is indistinguishable from an absent key here, and reports as the missing field it effectively is." | Known behaviour pinned | area: GEN | -
- ASSUME | tests_scripts/test_buildgen_requires_tag.py:258-262 | "mirrors the real near-collision in buildgen/validate.py ... \"# @requires tag, not here).\"" | False-positive guard modelled on a specific wrapped comment in validate.py; "edit distance 3 - outside the typo tolerance" pins the near-miss threshold | area: GEN | related: GEN.T03

## tests_scripts/test_buildgen_schema_ast.py
- LIMIT | tests_scripts/test_buildgen_schema_ast.py:1-3,66-67,90-92 | "the silent-skip behavior for anything else" / "a real gap this best-effort pass must not crash on" | Schema extraction is best-effort: unresolvable names and unsupported literal shapes are silently skipped, so a driver schema that stops resolving silently drops out (no error) | area: GEN | related: GEN.S10
- ASSUME | tests_scripts/test_buildgen_schema_ast.py:132-133 | "consts resolution walks tree.body in source order, so the later one must be the one used" | Last-assignment-wins semantics for reassigned module constants (ignores conditional/nested assignment) | area: GEN | -
- ASSUME | tests_scripts/test_buildgen_schema_ast.py:156-157 | "ContMeas is deliberately freestanding (no _VAL_* constant at all" | Pinned: SCD30 ContMeas has no schema; AmbPres schema = ("int", None, 700, 1400, 0) | area: SENS | -

## tests_scripts/test_buildgen_tag_comments.py
- DRIFT | tests_scripts/test_buildgen_tag_comments.py:2,345-347 | "and the planned `# @web`/`# @web-group` tags" / "a short tag name (the planned \"@web\")" | `@web`/`@web-group` are implemented (test_buildgen_web_tag.py); the test file repeats the stale "planned" wording the plan records in tag_comments.py | area: DOC | related: GEN.S14
- INVAR | tests_scripts/test_buildgen_tag_comments.py:1-3 | "a typo'd or misplaced attempt must fail loud, never read as \"no tag here\"" | Standing rule for every tag family; pins typo tolerance at edit distance 2 (1 for short names like "web"), case-folded exact match | area: GEN | related: GEN.T03
- RISK | tests_scripts/test_buildgen_tag_comments.py:364-366 | "at the accepted cost of flagging the prose nobody writes (\"@wiring is what this module needs\")" | Accepted false-positive: a sigil + bare-word payload in prose fails the build | area: GEN | related: GEN.T03
- ASSUME | tests_scripts/test_buildgen_tag_comments.py:308-310 | "Mirrors a real near-collision in this repo, where a wrapped comment line began with the tag's own name" | False-positive guard modelled on one real comment; comment-reflow elsewhere could create new collisions | area: GEN | -
- LIMIT | tests_scripts/test_buildgen_tag_comments.py:378-379 | "A single shared heuristic would go blind on whichever shape it wasn't written for" | Near-miss detection is per-family shape predicates; a new tag family needs its own predicate or its typos go undetected | area: GEN | related: GEN.T03

## tests_scripts/test_buildgen_twin_wiring.py
- ASSUME | tests_scripts/test_buildgen_twin_wiring.py:29-31 | "digital_twin/machine.py has no MicroPython-only import at module scope (only individual method bodies do)" | Importing the twin's `machine` under CPython depends on this convention; nothing enforces it | area: TWIN | related: TWIN.T12
- LIMIT | tests_scripts/test_buildgen_twin_wiring.py:26-40 | "import machine  # type: ignore[import-not-found]" | Fixture removes digital_twin/ from sys.path afterwards but leaves `sys.modules["machine"]` (the twin fake) in the shared pytest process for every later test (low) | area: TEST | -
- SUPPRESS | tests_scripts/test_buildgen_twin_wiring.py:36 | "# type: ignore[import-not-found]  # only resolvable once digital_twin_dir is on sys.path" | Type-check suppression for a runtime path import | area: TEST | -
- MIRROR | tests_scripts/test_buildgen_twin_wiring.py:96-98 | "src/asy_scd30_driver.py's own _SCD30_DEFAULT_ADDR, src/asy_sgp40_driver.py's own address=0x59 default, and src/asy_isl29125_driver.py's own hard-wired 0x44" | `buildgen/twin_wiring.FIXED_ADDRESSES` mirrors three driver constants by hand | area: GEN | covered-by: GEN.T06
- MIRROR | tests_scripts/test_buildgen_twin_wiring.py:103-105 | "the two sides are hand-kept in sync for one fixed driver set" | Twin chip fakes (`_build_i2c_chip()`) and `BUS_ATTACHED_DRIVERS` are hand-synced; mismatch fails loud only when reached | area: TWIN | related: TWIN.T12
- ASSUME | tests_scripts/test_buildgen_twin_wiring.py:114-116 | "Unreachable through any real TOML, buildspec.py's three classification sets partitioning BUS_ATTACHED_DRIVERS exhaustively" | Defensive fallback reached only by monkeypatch | area: GEN | -
- LIMIT | tests_scripts/test_buildgen_twin_wiring.py:50 | "@pytest.mark.parametrize(\"device\", [\"wozi\", \"dev\"])" | Load-and-apply end-to-end check covers wozi/dev only | area: TWIN | -
- DRIFT | tests_scripts/test_buildgen_twin_wiring.py:1,125 | "proving generality beyond the 6 real, hand-verified devices" | Hardcoded device count (low) | area: DOC | related: DOC.T08

## tests_scripts/test_buildgen_validate.py
- RISK | tests_scripts/test_buildgen_validate.py:92-94 | "dropped at boot back to the password published in src/ - silently, on every device at once" | Out-of-bounds TOML hotspot password would silently fall back to src/'s shared default at boot; the build-time 8..63 check is the only guard | area: GEN | related: SEC.T04
- PLATFORM | tests_scripts/test_buildgen_validate.py:84 | "8 characters is WPA2-PSK's own minimum - below it the CYW43 can't bring the hotspot up at all" | CYW43/WPA2 bound the validator relies on | area: NET | related: NET.S16
- RISK | tests_scripts/test_buildgen_validate.py:160-165 | "an over-long one would be dropped back to the shared \"SensorNode\" default at boot instead of failing" | Silent boot fallback for an over-long hostname; build caps `SensorStation<Name>` at 32 ("one over network.hostname()'s cap" = 33) | area: GEN | related: NET.S17
- PLATFORM | tests_scripts/test_buildgen_validate.py:164 | "\"SensorStation\" (13) + 20 = 33, one over network.hostname()'s cap" | network.hostname() 32-char cap is a MicroPython/CYW43 fact to re-check on version moves | area: PLAT | related: NET.T07
- LIMIT | tests_scripts/test_buildgen_validate.py:181-198 | "An empty/absent [bus.*] is not rejected on its own" / "is a logically valid, simplest-possible shape" | Validate accepts a device with no buses/instances; the plan records codegen crashing on a missing [bus] table | area: GEN | related: GEN.S03
- SUPPRESS | tests_scripts/test_buildgen_validate.py:1203-1208 | "pytest.skip(\"an inline table can't be produced by this fixture writer\")" | The dict-valued `led_target` case of a parametrized test always skips (fixture-writer limitation), so an inline-table wiring value is never exercised here | area: TEST | -
- PLATFORM | tests_scripts/test_buildgen_validate.py:254,280,289,296-297 | "GP22 is a real, usable GPIO (not wireless-reserved) that simply has no I2C function" | RP2040/Pico W pin-function facts pinned by tests (GP2/3 I2C1, GP22 no I2C, ADC2-only, GP23/24/25/29 wireless-reserved) | area: GEN | related: GEN.T07
- LIMIT | tests_scripts/test_buildgen_validate.py:242-244 | "spi1 is legal but unexercised by any real device: fram is the only SPI-attached driver and is a forced singleton" | spi1 path exercised only synthetically | area: GEN | -
- ASSUME | tests_scripts/test_buildgen_validate.py:549-551,634-636,648-650 | "No real driver's _NAME collides this way" / "unreachable with today's driver names" / "no real TOML can produce two" | Several uniqueness/collision checks reachable only via synthetic models; claims rest on today's driver set | area: GEN | -
- ASSUME | tests_scripts/test_buildgen_validate.py:563-565,576-578,594-595,608-609,620-621 | "_resolve_instances() always sets resolved_name before this check ever runs" | Five "internal:" invariant guards driven only by hand-built specs/monkeypatch | area: GEN | -
- PLATFORM | tests_scripts/test_buildgen_validate.py:1051-1053,1061-1063,1071 | "Interface Description p.2's hard datasheet maximum ... an over-clocked SCD30 bus built cleanly and only misbehaved on real hardware" | SCD30 100 kHz and SGP40 400 kHz (Table 3) bus limits; shared bus held to the stricter tag | area: SENS | related: SENS.T17
- ASSUME | tests_scripts/test_buildgen_validate.py:1096-1098 | "Error-path coverage sweep (2026-09-10): every abort below was reachable but had no test of its own" | Dated one-time sweep; completeness after later validate.py changes is not re-checked | area: GEN | related: GEN.T01
- LIMIT | tests_scripts/test_buildgen_validate.py:1181-1182 | "No driver in src/ declares one today, so the tag is staged onto sgp40." | The optional `@value-wiring` path exists only in staged copies | area: GEN | -
- MIRROR | tests_scripts/test_buildgen_validate.py:1241-1246 | "Mirrors dev.toml's uart0/uart1 initiator/responder shape ... dev.toml's bus knobs too" | Fixture copies dev.toml's UART knobs (115200, rxbuf/txbuf 512, poll_wait 2, poll_idle 50) by hand | area: UART | -
- MIRROR | tests_scripts/test_buildgen_validate.py:1256-1257,1268,1279,1290-1291,1302 | "2 x 2 + poll_idle_ms + 21ms GC pause against UartLinkExerciser's 1000ms timeout: 975 is the last idle poll that fits" | Build-time UART arithmetic pins the measured 21 ms GC pause, 53-byte frame (5 header + 48 payload), UART defaults (rxbuf 256, poll 20 ms) and errno 11/15 of `UART_Comm.setup()`; build and runtime checks must agree | area: UART | related: UART.T10
- INVAR | tests_scripts/test_buildgen_validate.py:1327-1332 | "dev is the only device with a link; this pins that its bench tuning really boots the link" | Globs every devices/*.toml without the `zz_test_*` filter used at :1735 (low) | area: GEN | related: TEST.T13
- PLATFORM | tests_scripts/test_buildgen_validate.py:1499-1500 | "a closing connection's FIN_WAIT pcb outlives its slot, and lwIP never reclaims one at equal priority" | lwIP PCB fact behind the "max_connections + 3 spare PCBs" rule (SPARE_TCP_PCBS) | area: PLAT | related: PLAT.T04
- ASSUME | tests_scripts/test_buildgen_validate.py:1515-1516,1532-1533 | "a queue shallower than the ceiling lets lwIP reset part of a burst" / "a deeper queue buys nothing but pcbs held" | backlog must be in [max_connections, max_connections+1]; rationale is lwIP/_serve behaviour not proven here | area: REST | related: REST.T06
- MIRROR | tests_scripts/test_buildgen_validate.py:1642-1647 | "assert init_int_default(src_dir, \"asy_ntp_client.py\", \"AsyNtpClient\", \"retry_s\") == 10" | Pins NTP backoff defaults 10/600 read by AST from src; build-time check ↔ src constants | area: NET | related: NET.T03
- ASSUME | tests_scripts/test_buildgen_validate.py:1682 | "AsyNtpClient would silently round it up to its 10s tick" | Runtime rounding behaviour that the build check pre-empts | area: NET | -
- SETTLED | tests_scripts/test_buildgen_validate.py:1729-1730 | "The owner's decision (2026-09-22) is that the recommended setting ships on every device" | Every shipped device TOML must state `[device].max_connections` | area: GEN | -
- MIRROR | tests_scripts/test_buildgen_validate.py:1718 | "The one reader every host-side instrument sizes its load with, so it must agree with the build." | `device_max_connections()` is the shared source for host load tools | area: HW | -

## tests_scripts/test_buildgen_value_wiring.py
- INVAR | tests_scripts/test_buildgen_value_wiring.py:133-142 | "assert tagged == {\"asy_sgp40_driver.py\"}" | Pinned: SGP40 is the only `@value-wiring` declarer (temperature_source/humidity_source, both required) | area: GEN | related: GEN.T03
- ASSUME | tests_scripts/test_buildgen_value_wiring.py:36-37 | "The three names are independent by design - nothing requires the TOML field and the constructor kwarg to be spelled the same, they just happen to be in src/ today" | Coincidental same-spelling of TOML field/kwarg in src/ | area: GEN | -

## tests_scripts/test_buildgen_version.py
- DRIFT | tests_scripts/test_buildgen_version.py:10-13 | "PEP 440-style release[.dev|a|b|rc][N] segment" | `_VERSION_RE` (`^\d+\.\d+(?:(?:a|b|rc)\d+)?$`) accepts no `.dev` and no patch component, contrary to the comment (low) | area: GEN | -
- DRIFT | tests_scripts/test_buildgen_version.py:2-3 | "no bump mechanism is assumed to exist (see that session's own account for why)" | Dangling pointer to an unnamed "session's own account" | area: DOC | related: DOC.T02
- TODO | tests_scripts/test_buildgen_version.py:24-27 | "SPECIFICATION.md Part L.7: \"firmware + website, both starting at 2.0b0\"." | Test pins both versions at 2.0b0; any hand bump must also edit this test (no bump mechanism exists) | area: GEN | related: GEN.T14
- LIMIT | tests_scripts/test_buildgen_version.py:34-38 | "before - timedelta(seconds=1) <= parsed <= after + timedelta(seconds=1)" | Wall-clock test with 1 s slack (second-truncated timestamp) (low) | area: TEST | related: TEST.T04

## tests_scripts/test_buildgen_web_tag.py
- INVAR | tests_scripts/test_buildgen_web_tag.py:533-538 | "assert tagged == {\"asy_scd30_driver.py\", \"asy_sgp40_driver.py\", ... \"asy_notification_service.py\"," | Pinned set of 8 `@web`-tagged src/ modules plus per-driver field-name sets (SCD30, BMP3xx, ISL29125, SGP40, WiFi, NTP, System, Notification); neopixel, webserver and uart_link carry no @web tags | area: GEN | related: WEB.T05
- MIRROR | tests_scripts/test_buildgen_web_tag.py:127-128 | "js/definitions.js's own validateFieldHints() enforces the identical rule" | `path` only on readonly fields — enforced in both buildgen/web_tag.py and js/definitions.js | area: WEB | related: GEN.T15
- SETTLED | tests_scripts/test_buildgen_web_tag.py:500-501 | "GMTOffset/DSTOffset ... render on the System page instead (a deliberate cross-file section/group assignment, not a mistake to \"fix\")" | Deliberate placement of NTP timezone fields | area: WEB | -
- ASSUME | tests_scripts/test_buildgen_web_tag.py:459-461 | "R/G/B/H/S/Bri are the first (and, at the time of writing, only) fields in src/ whose measurement body is nested" | Nested `path` capability exercised by ISL29125 only; dated claim | area: GEN | -
- LIMIT | tests_scripts/test_buildgen_web_tag.py:477-479 | "each of these three fields has a documented \"0 means X\" meaning despite an ordinary (special=None) schema tuple" | SGP40 BackupPeriod/BackupMaxAge/WaitTimeNTP "0 means" semantics live only in the @web tag, not in the schema (the "real generator-behavior finding" Part L flags) | area: SENS | related: PAR.S01
- LIMIT | tests_scripts/test_buildgen_web_tag.py:515-530 | "assert any((t.section, t.submit_group) == expected_key for t in tags)" | @web-group real-driver check asserts presence of one expected group, not the full group set per file (low) | area: GEN | -

## tests_scripts/test_buildgen_wiring.py
- INVAR | tests_scripts/test_buildgen_wiring.py:225-272 | "A new tag appearing in a module nobody expected it in should fail this test, not go unnoticed." | Pinned `@wiring` table for 11 src/ modules (fram_target kwarg everywhere; SGP40's target is `fram_storage`; WiFi `led_target` setter `set_ext_led`; notification `signal_sink` attr `request_signal`, required) | area: GEN | related: GEN.S09
- SETTLED | tests_scripts/test_buildgen_wiring.py:185-187 | "The one deletion that does NOT abort, deliberately and consistently with @requires" | A comment consisting only of the tag name is tolerated as prose (all tag families) | area: GEN | -
- RISK | tests_scripts/test_buildgen_wiring.py:146-148 | "(\"warning\"/\"writing\"/\"winning\" are all only two edits away and DO get flagged, which is the intended trade" | Accepted false-positive class for `@wiring` near-miss detection | area: GEN | related: GEN.T03
- LIMIT | tests_scripts/test_buildgen_wiring.py:119 | "Two tags for one field is ambiguous, not additive - the second would silently win." | Duplicate-tag rejection guards a silent-override hazard | area: GEN | -

## tests_scripts/test_ceiling_probe.py
- LIMIT | tests_scripts/test_ceiling_probe.py:1-3,21-24 | "against a loopback server shaped like _serve(): reject-when-full, an idle-read timeout, a whole-request cap" | The ceiling probe is validated only against a threaded Linux-TCP loopback model of `_serve()` (options mimic serve-after-EOF, answer, RST refusal); lwIP accept/backlog/PCB behaviour is not modelled | area: HW | related: TEST.T17
- ASSUME | tests_scripts/test_ceiling_probe.py:106-107 | "Nothing listening: the stack refuses the connect itself, as a PCB-exhausted board does." | Board behaviour at PCB exhaustion assumed equal to a closed-port connect refusal | area: HW | related: PLAT.T04
- ASSUME | tests_scripts/test_ceiling_probe.py:204 | "The board refuses with an RST once a refused client's request bytes have arrived." | Observed board refusal mode encoded as a fake option; provenance not cited | area: HW | related: HW.T16
- LIMIT | tests_scripts/test_ceiling_probe.py:58,99-101,115-126,146 | "time.sleep(0.1)  # long enough for a refusal to land" | Many sub-second timing assumptions (0.05 s poll, 0.1 s dwell, 0.6 s idle, 0.8 s drain timeout); CI-load sensitive | area: TEST | related: TEST.T04
- MIRROR | tests_scripts/test_ceiling_probe.py:22-24,66 | "EOF ends microdot's headers: it serves, slot held" | Fake encodes Microdot/_serve slot-release semantics (slot held while serving an EOF-ended request); must track asy_webserver_service.py's real behaviour (H.7.1) | area: REST | related: REST.T06

## tests_scripts/test_comment_block_cap.py
- INVAR | tests_scripts/test_comment_block_cap.py:1-3,14 | "Python and shell only - JS/CSS keep their own syntax and stay review-enforced." | Machine gate for CLAUDE.md's 3-line cap covers `*.py`/`*.sh` in exactly 8 SCOPES (src, buildgen, digital_twin, toolchain, scripts, tests, tests_scripts, tests_hardware); JS, CSS, HTML, config files (TOML/YAML/INI), `devices/`, `.github/` are review-only | area: DOC | related: CI.T08
- LIMIT | tests_scripts/test_comment_block_cap.py:59 | "if not any(tag in line for line in lines[s - 1 : s - 1 + n] for tag in _TAGS)" | An over-cap comment block is exempted wholesale if ANY line contains a tag substring ("@web", "@requires", ...), so prose that merely mentions a tag, or prose around a tag line, is never measured — weaker than CLAUDE.md's "the prose introducing them is not exempt" | area: DOC | -
- LIMIT | tests_scripts/test_comment_block_cap.py:20,34 | "_PEP723 = re.compile(r\"^#\\s*(///|requires-python\\s*=|dependencies\\s*=)\")" | PEP 723 exemption treats matching lines as punctuation anywhere in a file (not only inside a `# /// script` block); multi-line dependency list entries inside a block count as prose | area: DOC | -
- LIMIT | tests_scripts/test_comment_block_cap.py:62-85 | "if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))" | Only real docstrings are measured; physical lines only (E501 ignored), so a paragraph packed on one long line passes | area: DOC | covered-by: TEST.S22
- LIMIT | tests_scripts/test_comment_block_cap.py:27-29 | "return stripped.startswith(\"#\") and not stripped.startswith(\"#!\")" | Comment detection is line-textual: `#` lines inside multi-line strings or shell heredocs are counted as comments (possible false positives, not misses) (low) | area: DOC | -
- LIMIT | tests_scripts/test_comment_block_cap.py:105-109 | "Guards the detector: a glob that silently matched nothing would pass everything vacuously." | Vacuity floor: every scope non-empty and > 200 files total | area: DOC | -

## tests_scripts/test_coverage_runner.py
- SUPPRESS | tests_scripts/test_coverage_runner.py:20-28 | "pytest.skip(f\"the --coverage variant is not built at {path}" | All runner tests skip when `build-settrace` is absent; they also transitively skip when `build-standard` is absent (fixture depends on `micropython_bin`) even though only settrace is used | area: TEST | related: TEST.T13
- PLATFORM | tests_scripts/test_coverage_runner.py:52 | "MicroPython's SystemExit carries .args, not CPython's .code" | Runtime difference the runner's exit propagation depends on | area: PLAT | -
- PLATFORM | tests_scripts/test_coverage_runner.py:71-72 | "the Unix port prints an uncaught traceback to STDOUT (verified directly)" | test.sh must merge 2>&1 before scanning; single verification | area: PLAT | related: SCR.T01
- MIRROR | tests_scripts/test_coverage_runner.py:35 | "\"MICROPYPATH\": \"build/generated_src:src:tests:frozen_modules:.frozen\", \"TZ\": \"UTC\"" | Hand copy of test.sh's MICROPYPATH order and TZ pin | area: TEST | related: SCR.S07
- LIMIT | tests_scripts/test_coverage_runner.py:77-86 | "the report describes src/ and digital_twin/ and nothing else" | Coverage traces src/ and digital_twin/ only; generated modules and staged/stripped copies are never traced | area: TEST | covered-by: TEST.S13

## tests_scripts/test_device_script_config_flush.py
- INVAR | tests_scripts/test_device_script_config_flush.py:1-3 | "write_config() only stages - an unflushed manager lets asyncio.run() discard the flash write" | Device scripts must `flush_pending()` every manager they stage on; enforced here for `tests_hardware/device_scripts/*.py` only (MEASUREMENTS archive 7O) | area: HW | related: HW.T01
- LIMIT | tests_scripts/test_device_script_config_flush.py:20-22,48-65 | "_DELEGATES_TO_CFGMGR = \"_set_dict_cfg\"" | Only `write_config()` and `_set_dict_cfg()` calls count as writes; other staging paths (driver setters, `_set_mgr_cfg` direct, REST) are not seen; matching is by source spelling, so aliases give false positives and a flush on an unreached path is a false negative | area: HW | -
- SETTLED | tests_scripts/test_device_script_config_flush.py:69-71 | "So no call ORDER is asserted: across two functions there is no order to read." | Deliberate: flush-after-write order is not checked | area: HW | -
- SUPPRESS | tests_scripts/test_device_script_config_flush.py:26-28 | "\"isl29125_mechanism_envelope.py\": \"awaits between pushes, so its flushes are scheduled, and nothing it writes has to survive a reset\"" | One allowlisted unflushed script; the re-derivation (:81-87) only checks that ANY `.sleep*()` call exists anywhere in the file, not "between writes" as the helper's name says | area: HW | related: HW.S05
- MIRROR | tests_scripts/test_device_script_config_flush.py:130-137 | "The `.cfgmgr` hop above is only correct while _set_mgr_cfg persists through that attribute." | Guard pins `src/base_classes.py::_set_mgr_cfg` writing through `self.cfgmgr` | area: CORE | -

## tests_scripts/test_device_script_gc_threshold.py
- PLATFORM | tests_scripts/test_device_script_gc_threshold.py:2-3 | "mpremote's raw-REPL soft reset keeps the boot entry's threshold (rp2 runs gc_init() once, outside that loop)" | rp2/mpremote fact; heap results not naming their threshold are void (MEASUREMENTS M3.8) | area: PLAT | related: HW.T16
- ASSUME | tests_scripts/test_device_script_gc_threshold.py:62-63 | "the reason the pre-2026-09-24 flash-tier readings' threshold is unknown (MEASUREMENTS M3.8)" | Every flash-tier heap figure measured before 2026-09-24 has an unknown GC threshold | area: MEM | related: HW.T16
- LIMIT | tests_scripts/test_device_script_gc_threshold.py:14-25,68-69 | "_MEASURES = {(\"gc\", \"mem_free\"), (\"gc\", \"mem_alloc\"), (\"micropython\", \"mem_info\")}" | A script is "measuring" only via plain `gc.mem_free/mem_alloc` or `micropython.mem_info` calls; `from gc import ...`, aliases, or heap reads through helper modules are not detected; "set before report" uses first line numbers, not control flow | area: HW | -
- LIMIT | tests_scripts/test_device_script_gc_threshold.py:72-75 | "Guards the detector itself: an empty or shrunken set would pass everything below vacuously." | Floor of five named heap-measuring scripts | area: HW | -

## tests_scripts/test_device_tomls.py
- DRIFT | tests_scripts/test_device_tomls.py:3 | "Hand-implements the collision checks until Session 3's generator/validator exists." | The validator exists (buildgen/validate.py); this file keeps a second, hand-written subset of the same checks with the stale "until" rationale | area: GEN | -
- MIRROR | tests_scripts/test_device_tomls.py:66-67,441-486 | "reusable collision/shape checks ... Standalone functions so the negative-path tests below can exercise the same logic" | Duplicate implementation of GPIO/address/instance-name/wiring checks alongside buildgen.validate, with its own `_BASE_DOC` (a second base fixture besides `_toml_fixtures.base_doc()`; its `hotspot_password = "x"` would fail validate's 8..63 bound) — the two can drift | area: TEST | related: TEST.T08
- MIRROR | tests_scripts/test_device_tomls.py:18-40 | "_DEVICES_WITH_BMP3XX = {\"wozi\", \"dev\"}" | Hand-kept facts: always-present drivers, BMP3xx on wozi/dev only, UART link and ISL29125 on dev only, multi-instance/singleton/mandatory-infra/FRAM-wirable sets — parallel to buildgen/driver_registry and test_buildgen_definitions.py:19-20 | area: TEST | related: GEN.T06
- INVAR | tests_scripts/test_device_tomls.py:247-269 | "Each scenario library's `_DEVICES` tuple stays hand-written deliberately: its ORDER assigns the twin's TCP port bases." | Enforces that `tests/test_{sensortask,digital_twin_construction,digital_twin_webserver_concurrency}_<device>.py` and three scenario `_DEVICES` tuples equal DEVICE_NAMES; does NOT cover other device-specific lists (e.g. js/app.js KNOWN_DEVICES, tests_js) | area: TEST | related: WEB.S22
- INVAR | tests_scripts/test_device_tomls.py:271-282 | "A GitHub Actions matrix is a literal - no expression can glob devices/ at parse time" | Enforces both ci.yml `device: [...]` matrices equal DEVICE_NAMES via regex (expects exactly 2 one-line flow sequences; pyyaml deliberately not a dependency) | area: CI | covered-by: CI.T07
- ASSUME | tests_scripts/test_device_tomls.py:373,383 | "Fact about the 6 real devices, not a schema requirement" | Pins that every real device wires fram_target on every wirable instance and all three warn_* signals | area: GEN | -
- INVAR | tests_scripts/test_device_tomls.py:428-436 | "Only device identity (name/hostname) may differ; everything else must be byte-for-byte identical." | klkizi/grkizi/schlafzi must be identical apart from name/hostname (hardcoded names) | area: GEN | related: PAR.T13
- DRIFT | tests_scripts/test_device_tomls.py:575-577 | "any source exposing a matching attribute name is structurally valid class to check against)" | Garbled comment (a clause is missing) (low) | area: DOC | -
- ASSUME | tests_scripts/test_device_tomls.py:575-577 | "this smoke suite instead checks the real devices' own convention (temperature_source always reads \"Temp\")" | Convention check narrower than the L.6.3 schema | area: GEN | -
- MIRROR | tests_scripts/test_device_tomls.py:808-813 | "The on-target sweep keeps its own copy deliberately, being MicroPython on the board and unable to import host test code." | I2C reserved ranges 0x00-0x07/0x78-0x7F duplicated here and in the on-target bus sweep script | area: HW | related: TEST.S05
- LIMIT | tests_scripts/test_device_tomls.py:835-848 | "only bmp3xx carries a TOML address field today" | Reserved-range sweep sees TOML addresses only; fixed-address drivers are checked via `buildgen.twin_wiring.FIXED_ADDRESSES` (itself a hand mirror of driver constants) | area: GEN | related: GEN.T06
- DRIFT | tests_scripts/test_device_tomls.py:244 | "shape/parse tests, run against the 6 real files" | Hardcoded count (low) | area: DOC | related: DOC.T08

## tests_scripts/test_digital_twin_boot_contiguity.py
- INVAR | tests_scripts/test_digital_twin_boot_contiguity.py:1-3 | "The regression guard for SPECIFICATION.md Part I.4(f.1)'s boot-confined placement reset" | The effect-side guard of the only sanctioned `gc.collect()` exception (site-side: test_gc_collect_sites.py, lint.sh) | area: MEM | related: TEST.T03
- ASSUME | tests_scripts/test_digital_twin_boot_contiguity.py:46-80 | "worst live 452,832 (1.47x); best suppressed 218,528 (1.41x under)" | All bounds are single-campaign twin measurements times a thin margin ("the ARMS are only 2.07x apart here"); ratios 2.36x/4.64x and 12.96x/13.93x; retention drift 0.05% vs 1% tolerance (MEASUREMENTS archive §7L.7/§7L.3/7A.1) | area: MEM | related: HW.T16
- LIMIT | tests_scripts/test_digital_twin_boot_contiguity.py:46-48 | "Twin units (32 B blocks, x86-64) and twin-only - the board's own tripwire stays the hardware test." | 64-bit Unix-port heap, not rp2; results do not transfer numerically to silicon | area: TWIN | covered-by: TWIN.T06
- ASSUME | tests_scripts/test_digital_twin_boot_contiguity.py:28-30 | "those proved heap-size independent at 8M and 16M" | Heap-size independence measured at two sizes only | area: MEM | -
- LIMIT | tests_scripts/test_digital_twin_boot_contiguity.py:59-61 | "The batch's own reach and band count no longer separate the arms (8,160 B and 0 in BOTH)" | Since the settrace-free re-derivation, two of the bounds are tripwires only, not proof the collects work | area: MEM | -
- LIMIT | tests_scripts/test_digital_twin_boot_contiguity.py:39-42,203-205 | "Running it for all six would double the subprocess count" / "so this UNDERSTATES" | Control (suppressed) arm runs on wozi/dev only and still keeps the anchor collect | area: MEM | -
- ASSUME | tests_scripts/test_digital_twin_boot_contiguity.py:189-191 | "the run phase undoes most of the gain within ~2 s and the position stops discriminating (MEASUREMENTS M3.9)" | Placement benefit is transient at the reactive default; measurement taken at the starter loop's end only | area: MEM | related: MEM.T02
- SUPPRESS | tests_scripts/test_digital_twin_boot_contiguity.py:101-109 | "Skipped rather than failed when absent" | Whole file skips when `build/generated_src/` or the standard Unix port is absent (plain `pytest tests_scripts` without test.sh) | area: TEST | related: TEST.T13
- LIMIT | tests_scripts/test_digital_twin_boot_contiguity.py:127-140 | "assert completed.returncode == 0" / "assert \"RESULT: PASS\" in completed.stdout" | Probe stdout is not scanned for `MemoryError`/`memory allocation failed` (not one of the four gates) | area: MEM | covered-by: TEST.T18
- MIRROR | tests_scripts/test_digital_twin_boot_contiguity.py:31-32,279-285 | "scripts/test.sh's own MICROPYPATH, heap size and interpreter, so this measures what the suite measures" | `_MICROPYPATH`/`_HEAPSIZE="16M"` pinned against test.sh by substring presence | area: TEST | -
- MIRROR | tests_scripts/test_digital_twin_boot_contiguity.py:260-297 | "The probe's header claims it mirrors the board script's bounds ... Nothing pinned that claim." | `_STARTER_LOOP_TIMEOUT_MS`, `_STARTER_LOOP_GRACE_MS`, `_TIMERS_TIMEOUT_S` must match between tests/_boot_contiguity_probe.py and tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py (now enforced) | area: HW | -
- LIMIT | tests_scripts/test_digital_twin_boot_contiguity.py:246-252 | "setup_calls = len(re.findall(r\"^\\s*await \\w+\\.setup\\(\\)\\s*$\"" | Collect-count parity uses the same exact-shape `await X.setup()` regex as test_buildgen_generate.py | area: GEN | -
- LIMIT | tests_scripts/test_digital_twin_boot_contiguity.py:34 | "_PROBE_TIMEOUT_S = 120" | Per-probe subprocess timeout; up to 6 devices + 2 control arms boot sequentially in the pytest tier | area: TEST | related: TEST.T16

## tests_scripts/test_digital_twin_ci_suite_ceiling.py
- LIMIT | tests_scripts/test_digital_twin_ci_suite_ceiling.py:19-42 | "read the request, answer nothing - the reject-when-full shape" | Run 11b is tested against CPython `http.server` fakes and fully stubbed spawn/wait/shutdown; the real twin/Microdot refusal is exercised only by the live CI suite | area: TWIN | related: SCR.T04
- SUPPRESS | tests_scripts/test_digital_twin_ci_suite_ceiling.py:30 | "# noqa: A002 - the base class's own signature" | Builtin-shadowing `format` parameter required by BaseHTTPRequestHandler | area: TEST | -
- ASSUME | tests_scripts/test_digital_twin_ci_suite_ceiling.py:113 | "assert all(\"RemoteDisconnected\" in r for r in results)" | Pins CPython http.client's exception name for a hang-up (host-Python-version dependent) (low) | area: TEST | -
- INVAR | tests_scripts/test_digital_twin_ci_suite_ceiling.py:126-127 | "The README's bar is \"served 200 with a parsed body\"" | Run 11b must fail a 200 without parseable JSON | area: TWIN | -
- INVAR | tests_scripts/test_digital_twin_ci_suite_ceiling.py:149-150 | "never an escape that skips the shutdown and leaves a twin holding the port for every later run" | Run functions must catch their own crash and still shut the twin down (fixed port reuse across runs) | area: SCR | related: SCR.T04

## tests_scripts/test_digital_twin_ci_suite_errcount.py
- MIRROR | tests_scripts/test_digital_twin_ci_suite_errcount.py:100-134 | "the two tables are hand-kept separately, and a driver present in one but not the other raises mid-run" | Twin CI suite tables `_BUS_FAULT_OPS`, `_DRIVER_ERRCOUNT_NAME`, `_NO_PERSIST_WHEN_FRAM_FAULTED`, `_MEASUREMENT_DRIVERS`, `_IN_MEMORY_ONLY_ERROR_SOURCES`, `_PERSISTED_ERROR_MODULES` are hand-kept; cross-checked here and outward against i2c/spi drivers of the real device set | area: TWIN | covered-by: GEN.T06
- LIMIT | tests_scripts/test_digital_twin_ci_suite_errcount.py:125-127 | "which let the ISL29125 be absent from all of them and silently skipped from the day it shipped" | Past silent coverage gap; the outward check is scoped to i2c/spi only | area: TWIN | -
- LIMIT | tests_scripts/test_digital_twin_ci_suite_errcount.py:129-130 | "uart_link's peer is a second UART_Comm rather than a faultable fake, so it is out by mechanism" | UART link is outside the twin's bus-fault matrix (Runs 3/4/5c) | area: UART | related: TWIN.T05
- SETTLED | tests_scripts/test_digital_twin_ci_suite_errcount.py:117-119 | "AsyFramManager cannot persist its own history through the store that failed, the one legitimate exemption" | FRAM is the only in-memory-only error source (also pinned in tests/_sensortask_scenarios.py) | area: STOR | related: STOR.S08
- SETTLED | tests_scripts/test_digital_twin_ci_suite_errcount.py:328-333 | "SGP40 is the one measurement driver outside the reset-to-0-with-FRAM-faulted set ... two halves of one decision" | Deliberate SGP40 asymmetry in the twin suite's persistence assertions | area: TWIN | -
- MIRROR | tests_scripts/test_digital_twin_ci_suite_errcount.py:24-26,44-46 | "\"counter\" bumps on errors AND warnings alike" / "print_log.py pre-fills the history deque with its own \"nothing recorded\" sentinel, published as type \"N\"" | Host parser encodes src/print_log.py's publication semantics (shared counter, ten-slot ring, "N" sentinel) | area: CORE | related: CORE.T05
- INVAR | tests_scripts/test_digital_twin_ci_suite_errcount.py:140-142,172-173 | "{} for an unreadable /status reads as counter 0 with an empty history ... as Runs 4, 5c and 8 all did" | Vacuous-pass class: tolerant `_errcount()` for polling vs strict `_errcount_required()`/`_errcount_all()` for assertions | area: TWIN | related: TEST.T01
- ASSUME | tests_scripts/test_digital_twin_ci_suite_errcount.py:180-181 | "Every registered error source appears in errcount whether or not it ever logged" | /status contract the strict helper relies on | area: REST | -
- INVAR | tests_scripts/test_digital_twin_ci_suite_errcount.py:251-252 | "Run 4 keeps `entry.get(\"counter\", -1) == 0` rather than a bare `== 0`" | Fail-closed default pinned because it looks like a typo | area: TWIN | -
- ASSUME | tests_scripts/test_digital_twin_ci_suite_errcount.py:277,300-302 | "the twin's worst observed dev sweep is 8.91s and real hardware is 6.32s idle / 11.58s under three concurrent readers" | `_RESET_ERRORS_BUDGET_S` sized from dated measurements; must sit between 8.91 s and the 15.0 s server cap (BACKLOG item 24) | area: PERF | related: PERF.T03
- DRIFT | tests_scripts/test_digital_twin_ci_suite_errcount.py:277 | "elapsed_s=8.28)  # the worst real twin sample" | Conflicts with :300's "the twin's worst observed dev sweep is 8.91s" (low) | area: DOC | -
- LIMIT | tests_scripts/test_digital_twin_ci_suite_errcount.py:307-314 | "a second raw _http(\"PUT\", \"/status\", {\"ResetErrors\": ...}) is exactly how the gap would reappear" | Single-site guard matches only lines containing both `"ResetErrors"` and `_http(` — a call split across lines or built from a variable escapes it | area: SCR | -
- INVAR | tests_scripts/test_digital_twin_ci_suite_errcount.py:336-377 | "matching \"MemoryError\" alone only ever caught an uncaught traceback" | Pins the twin gate's `memory allocation failed` half; a missing log is deliberately not a MemoryError failure | area: MEM | related: TEST.T18

## tests_scripts/test_digital_twin_ci_suite_soak.py
- LIMIT | tests_scripts/test_digital_twin_ci_suite_soak.py:2-3 | "Host-driven request cycling itself is exercised end to end by scripts/run_digital_twin_ci.sh ... not re-mocked here" | Only the parsing/trend arithmetic is unit-tested | area: TWIN | -
- LIMIT | tests_scripts/test_digital_twin_ci_suite_soak.py:94-96,81-83 | "the SAME 200-byte decline gets a tighter tolerance from a quiet quarter than a noisy one" | Leak tolerance is derived from each run's own within-quarter spread (no fixed floor); a slow leak smaller than the run's noise passes by design; needs >= 4 samples | area: MEM | related: HW.S14
- ASSUME | tests_scripts/test_digital_twin_ci_suite_soak.py:8-10 | "the \"gc.mem_free() has no other source\" exception (Part I.4(e))" | Soak relies on a sanctioned `gc.mem_free()` sampler exception in the twin | area: MEM | -

## tests_scripts/test_digital_twin_generated_boot.py
- DRIFT | tests_scripts/test_digital_twin_generated_boot.py:1-2,150-152 | "the same pattern scripts/_digital_twin_ci_suite.py already uses for the hand-written sensortask_wozi.py; wiring this into scripts/run_digital_twin_ci.sh stays Session 6's job" | Hand-written sensortask modules are retired (L.2) and the CI suite already boots generated modules; "Session 3/6" labels are undefined | area: DOC | related: TEST.S24
- LIMIT | tests_scripts/test_digital_twin_generated_boot.py:163-190 | "output = proc.stdout.read() if proc.stdout else \"\"" | Twin output is read only on a nonzero exit; no `MemoryError`/`memory allocation failed` scan of a passing boot | area: MEM | covered-by: TEST.T18
- LIMIT | tests_scripts/test_digital_twin_generated_boot.py:43-47 | "No real static content is needed - this suite never requests \"/\"" | Boots with a stub `frozen_html`; smoke = 5 GETs expecting 200 + JSON object; no PUT, no static route | area: TWIN | -
- ASSUME | tests_scripts/test_digital_twin_generated_boot.py:31-41 | "boot-to-first-200 lands between ~4.5s and ~6.3s across the six real devices, dev slowest" | `_TWIN_DURATION_S = 15`/`_BOOT_TIMEOUT_S = 30` sized from a dated measurement | area: TWIN | related: PERF.T06
- MIRROR | tests_scripts/test_digital_twin_generated_boot.py:113-133 | "The API derives itself from the live object graph; buildgen/definitions.py's catalog is hand-kept. Both drift directions are silent in the product" | Enforces /status errcount keys == website errcount rows at twin boot (per logger instance since 2026-09-18) | area: WEB | related: GEN.T06
- MIRROR | tests_scripts/test_digital_twin_generated_boot.py:153 | "env[\"MICROPYPATH\"] = f\"{tmp_path}:src:digital_twin:ext:.frozen\"" | Uses a different MICROPYPATH than test.sh (`build/generated_src:src:tests:frozen_modules:.frozen`) — intended, but a second resolution layout (low) | area: TEST | -
- RISK | tests_scripts/test_digital_twin_generated_boot.py:73-76 | "s.bind((_HOST, 0))" | `_free_port()` releases the port before the twin binds it (small TOCTOU window; accepted per CLAUDE.md's concurrency note) (low) | area: TEST | related: SCR.T06
- LIMIT | tests_scripts/test_digital_twin_generated_boot.py:53-57 | "this is the one suite that would actually BOOT that deliberately malformed fixture" | Fixture discovery excludes files prefixed `malformed_` by name only | area: TEST | -

## tests_scripts/test_gc_collect_sites.py
- INVAR | tests_scripts/test_gc_collect_sites.py:8-12 | "_ALLOWED_SRC_SITES = {(\"system_service.py\", \"start_and_check_tasks\")}" | Pinned allowance for I.4(f.1): src/ only in `system_service.start_and_check_tasks`, buildgen/ only in `codegen.py` (textual); also grepped by scripts/lint.sh | area: MEM | related: TEST.T03
- LIMIT | tests_scripts/test_gc_collect_sites.py:15-22,44-59 | "and node.func.value.id == \"gc\"" | Detects only `gc.collect()` spelled through the name `gc` in src/*.py (flat, non-recursive glob); `from gc import collect`, aliases, and every other scope (tests/, digital_twin/, tests_hardware/) are unchecked here; buildgen check is presence-per-file, not count or placement | area: MEM | related: TEST.S11

## tests_scripts/test_generate_sensortask_modules.py
- MIRROR | tests_scripts/test_generate_sensortask_modules.py:41-46 | "\"instances\" is main()'s addition on top of compute_twin_wiring()'s shape, an independent pre-construction driver-presence oracle" | Wiring-plan JSON carries an extra `instances` key only the pre-generation script adds; consumers (twin `configure_wiring()`) depend on it | area: GEN | related: GEN.T15
- LIMIT | tests_scripts/test_generate_sensortask_modules.py:49-67 | "Never left holding a half-written module (or wiring plan) for the device that failed." | Failure path tested with a monkeypatched generator only; stale outputs from earlier runs and non-atomic writes are not tested | area: SCR | covered-by: SCR.S07

## tests_scripts/test_heap_map_parser.py
- INVAR | tests_scripts/test_heap_map_parser.py:1-3 | "its dangerous failure mode is silent: a truncated capture reads as a heap with an enormous free run at the end, turning a regression into a pass" | heap_map.py gates real-hardware assertions; must fail closed on damaged captures (pinned here) | area: HW | related: TEST.T17
- PLATFORM | tests_scripts/test_heap_map_parser.py:18-27 | "32 B per block (the Unix port's size; the rp2 port's is 16, and the parser derives it rather than assuming either)" | Depends on the exact `micropython.mem_info(1)`/`gc_dump_info` text format (header lines, 64 blocks per line, map glyphs); a format change upstream breaks every heap-map assertion | area: PLAT | related: PLAT.T07
- DRIFT | tests_scripts/test_heap_map_parser.py:194-203 | "a contract between ONE parser regex and THREE independent emitters - two device scripts and the twin probe" | `_EMITTERS` lists five emitters (four device scripts + the twin probe) | area: DOC | -
- MIRROR | tests_scripts/test_heap_map_parser.py:194-222 | "=== MAP {label} ===" | MAP/ENDMAP envelope contract between heap_map.parse_labelled() and five emitters (now enforced); allocation_need_per_source.py's SIEVE/TRY/RES/BLOCK= line shapes are mirrored by a hand-built fixture only | area: HW | -
- INVAR | tests_scripts/test_heap_map_parser.py:271-274 | "a probe that degrades internally still returns normally, so RES says ok - only the log between its TRY and RES shows it" | `parse_allocation_need` must treat a logged `memory allocation failed` as a failure (I.4(e)); this file itself carries that literal string in fixture text | area: MEM | related: TEST.T18
- SUPPRESS | tests_scripts/test_heap_map_parser.py:16 | "# noqa: E402  (the sys.path line above is what makes this importable)" | E402 after `REPO_ROOT = ...` statement | area: TEST | -

## tests_scripts/test_http_client_ceiling_close.py
- ASSUME | tests_scripts/test_http_client_ceiling_close.py:18-27 | "F10/F11 measured the reset and the empty-read forms on real silicon." | Only ECONNRESET and empty-read were observed on silicon; ECONNABORTED/EPIPE are accepted as ceiling closes by reasoning; cites queue row IDs F10/F11 | area: HW | related: DOC.T03
- ASSUME | tests_scripts/test_http_client_ceiling_close.py:31-36 | "ConnectionRefusedError(errno.ECONNREFUSED, \"Connection refused\")," | `is_ceiling_close()` classes a refused connect as a real failure, while test_ceiling_probe.py:106-107 treats a refused connect as how "a PCB-exhausted board" refuses — the two host oracles read the same symptom differently (context-dependent) (low) | area: HW | related: TEST.T17
- LIMIT | tests_scripts/test_http_client_ceiling_close.py:59-63 | "RemoteDisconnected subclasses ConnectionResetError and BadStatusLine ... but only while that holds" | Depends on CPython's http.client class hierarchy (host-Python-version dependent) | area: HW | -
- SUPPRESS | tests_scripts/test_http_client_ceiling_close.py:69 | "# type: ignore[arg-type]" | HTTPError constructed with `{}` headers | area: TEST | -
- LIMIT | tests_scripts/test_http_client_ceiling_close.py:80-84 | "import test_bus_concurrency_under_api_load as bench" | Host tier imports a real bench test module (and leaves tests_hardware/bench on sys.path) to test its retry wrapper; BACKLOG 30 discriminator | area: TEST | -

## tests_scripts/test_js_coverage_excludes_json.py
- WORKAROUND | tests_scripts/test_js_coverage_excludes_json.py:1-3 | "a JSON file left in the coverage set throws a rolldown parse stack per run before being dropped anyway" | Pins vitest.config.js `coverage.exclude` globs covering every repo JSON, working around the v8 coverage provider re-parsing JSON as JS; removal trigger: none stated | area: CI | -
- LIMIT | tests_scripts/test_js_coverage_excludes_json.py:16-22,25-38 | "re.search(r\"exclude:\\s*\\[([^\\]]*)\\]\", text[block:])" | Reads vitest.config.js by regex (first `exclude: [...]` after `coverage: {`) and re-implements glob semantics by hand (low) | area: CI | -

## tests_scripts/test_js_coverage_report_dir.py
- WORKAROUND | tests_scripts/test_js_coverage_report_dir.py:1-3 | "its default name - `coverage` - is importable as a namespace package, shadowing the real `coverage` distribution and turning scripts/typecheck.sh red" | Report dir must not be named like any top-level module the repo imports; removal trigger: none stated | area: CI | -
- MIRROR | tests_scripts/test_js_coverage_report_dir.py:101-111 | "ci.yml gates the JS coverage upload on a directory vitest no longer writes" | vitest.config.js `reportsDirectory` ↔ ci.yml `hashFiles(...)`/`path:` ↔ .gitignore entry (enforced) | area: CI | -

## tests_scripts/test_lint_sh.py
- INVAR | tests_scripts/test_lint_sh.py:1-3 | "their own failure mode is silent: a drifted pattern stops matching and the gate goes green on a real violation" | lint.sh's three grep guards (method-assign in src/, gc.collect in src/, gc.collect in buildgen/) are extracted from the live script and run against fabricated trees and the live tree | area: SCR | related: SCR.T02
- LIMIT | tests_scripts/test_lint_sh.py:86-98 | "the exclusion is `grep -v \"^src/system_service.py:\"`, anchored and with the colon" | lint.sh's gc.collect allowance is file-granular (any function in system_service.py / codegen.py passes); function-level attribution exists only in test_gc_collect_sites.py | area: MEM | -
- ASSUME | tests_scripts/test_lint_sh.py:72 | "tests/ and digital_twin/ carry ~157 of these deliberately - that IS the mocking mechanism" | Dated approximate count of `type: ignore[method-assign]` suppressions outside src/ | area: TEST | related: DOC.T08
- LIMIT | tests_scripts/test_lint_sh.py:16-21 | "The one `if grep ...; then ... fi` block of scripts/lint.sh whose message contains `needle`" | Extraction assumes each guard is one `if grep ... fi` block at column 0 keyed by its message text; a restructured guard fails loudly (not silently) | area: SCR | -

## tests_scripts/test_live_twin_ceiling_parser.py
- MIRROR | tests_scripts/test_live_twin_ceiling_parser.py:1-3 | "configuredMaxConnections() sizes the browser tier's tab count, so it must resolve every device's ceiling exactly as buildgen does" | JS line-matching TOML reader in tests_js/_live_twin_command.js ↔ buildgen.validate.device_max_connections (enforced for real TOMLs + 4 synthetic shapes) | area: WEB | related: GEN.T15
- LIMIT | tests_scripts/test_live_twin_ceiling_parser.py:20-25 | "assert node is not None, \"node is not on PATH - the browser tier this pins cannot run without it either\"" | Hard dependency: the pytest tier FAILS (does not skip) without `node` on PATH | area: TEST | related: SCR.T13

## tests_scripts/test_measurement_field_tuple_agreement.py
- SETTLED | tests_scripts/test_measurement_field_tuple_agreement.py:5-7 | "It stays deliberately: mypy's namedtuple plugin infers field names only from a literal at the call site" | Hand-duplicated `_FIELDS` + NamedTuple in seven src/ modules is a deliberate choice | area: SENS | -
- MIRROR | tests_scripts/test_measurement_field_tuple_agreement.py:9-11,60-75 | "Drift here is silent and reaches the wire" | `_FIELDS` (make_dict → /measurements keys) must equal the module's measurement NamedTuple; guard passes if `_FIELDS` equals ANY public NamedTuple in the module, and only literal-tuple declarations are recognised (floor >= 7 modules) | area: SENS | -

## tests_scripts/test_memory_error_gate_agreement.py
- PLATFORM | tests_scripts/test_memory_error_gate_agreement.py:12-15 | "The interpreter's own MemoryError messages, from py/runtime.c:1692/1696 - the only two in the pinned source." | Gate wording depends on the pinned MicroPython source's messages/line numbers; re-check on a version move | area: PLAT | related: PLAT.T07
- MIRROR | tests_scripts/test_memory_error_gate_agreement.py:28-39 | "each holding its own copy of the pattern. This keeps all four agreeing" | harness.MEMORY_ERROR_MARKERS ↔ ci_suite._MEMORY_ERROR_MARKERS ↔ test.sh `local pattern="MemoryError|memory allocation failed"` (substring-presence check only, not how the grep uses it) | area: MEM | related: TEST.T18
- LIMIT | tests_scripts/test_memory_error_gate_agreement.py:17-20,42-49 | "_HARDWARE_TIER_FILES = (\"tests_hardware/flash/test_memory_stress.py\", \"tests_hardware/bench/test_memory_stress_bench.py\"," | Only two hardware files are checked for routing through the shared constant; other hardware tests carry no MemoryError gate at all | area: HW | covered-by: TEST.T18
- LIMIT | tests_scripts/test_memory_error_gate_agreement.py:54,63-83 | "_INJECTION_SCOPES = (\"tests\", \"digital_twin\")" | Injection-wording scan covers tests/ and digital_twin/ only (not tests_hardware/), sees only literal string args of `MemoryError(...)` or raises through a non-*Error/*Exception callee; f-strings/variables are invisible (floor >= 12) | area: MEM | -
- ASSUME | tests_scripts/test_memory_error_gate_agreement.py:69-71 | "it is per-test scratch that 85 concurrently running test files create and delete" | Dated count of MicroPython-tier test files | area: DOC | related: DOC.S08

## tests_scripts/test_micropython_overrides.py
- DRIFT | tests_scripts/test_micropython_overrides.py:1-3 | "Tests toolchain/micropython_overrides.py's unix_kbd_intr override in isolation" | The file also covers the lwip_connection_counts override, the lwIP ensemble arithmetic, the preprocessor readback and build_firmware wiring; header describes only the first (low) | area: DOC | -
- PLATFORM | tests_scripts/test_micropython_overrides.py:16,60-65 | "_REAL_ANCHOR_LINE = \"#define MICROPY_ASYNC_KBD_INTR         (!MICROPY_PY_THREAD_GIL)\"" | Exact v1.29.0 source line the SIGINT override is anchored to; any textual drift is "unverified", never fuzzy-matched; only the anchor text is checked, not the mechanism | area: TOOL | covered-by: TOOL.S07
- SUPPRESS | tests_scripts/test_micropython_overrides.py:44-49,346-350 | "pytest.skip(f\"no real toolchain checkout at {micropython_dir} - build it first (scripts/test.sh does)\")" | The only two checks against the REAL pinned source (kbd-intr anchor, 21 lwIP anchors) skip without a provisioned toolchain; everything else runs on synthetic trees | area: TOOL | related: TEST.T13
- INVAR | tests_scripts/test_micropython_overrides.py:135-138,237-252 | "must fail a test rather than silently ship an unpatched binary again" | Pins build_unix_port() applying the override and raising before `make` when the anchor is unverifiable ("again" implies a past unpatched ship) | area: TOOL | related: TOOL.T04
- INVAR | tests_scripts/test_micropython_overrides.py:197-224 | "compiled in, the flag allocates a frame and a code object per call, inflating every figure the memory work measures 4-5x" | Rig binary must be settrace-free, coverage binary settrace-enabled in its own build dir (2026-09-21 split, E.5.2); test.sh and conftest.py must spell both dir names (enforced by substring) | area: TOOL | related: TOOL.T05
- LIMIT | tests_scripts/test_micropython_overrides.py:226-232 | "assert \"build_unix_port(micropython_dir, toolchain_dir, jobs, settrace=True)\" in source" | "setup builds both variants" is proven by an exact source-substring match, not by exercising `setup` (low) | area: TOOL | -
- PLATFORM | tests_scripts/test_micropython_overrides.py:320-344 | "18 text anchors plus the three relayed board files" | 21 pinned lwIP/rp2/board-cmake anchor strings from the v1.29.0 tree (incl. "trap B" plain `MEMP_NUM_UDP_PCB` define, `LWIP_NETCONN 0` making MEMP_NUM_NETCONN a no-op); each proven load-bearing and the list pinned equal to the code's | area: TOOL | related: TOOL.T04
- MIRROR | tests_scripts/test_micropython_overrides.py:447-481,563-568 | "lib/lwip/src/core/init.c turns each of these into a compile-time #error, and opt.h derives four more values from them" | `derive_lwip_dependents`/`check_lwip_ensemble` restate lwIP's opt.h formulas and init.c checks in Python; must be re-derived when lwIP moves | area: TOOL | related: PLAT.T04
- PLATFORM | tests_scripts/test_micropython_overrides.py:464-477 | "876, not 856: pbuf.h's PBUF_IP_HLEN is 40 under LWIP_IPV6, which the rp2 port enables" | rp2 enables LWIP_IPV6; a constant in the Python restatement was previously wrong | area: PLAT | -
- ASSUME | tests_scripts/test_micropython_overrides.py:480-481,454-458 | "the pinned block sits exactly on lwIP's own MEMP_NUM_TCP_SEG >= TCP_SND_QUEUELEN boundary, 32 against 32" | MicroPython's own lwIP defaults (PCB 5, MEM_SIZE 8000, MSS 800, WND/SND_BUF 6400, SEG 32) hand-copied into `_pinned()` | area: TOOL | -
- ASSUME | tests_scripts/test_micropython_overrides.py:627-647 | "The shipped pattern at 6 (PCB 9, SEG 48, MEM_SIZE 12000) is clean" / "8000 / 4 = 2000. A relationship, not a tuning target" | Project rules beyond lwIP's own checks: shared pools must serve every admitted connection, 3 spare PCBs, MEM_SIZE >= 2000 B per connection (from the fielded design's share) | area: PERF | related: REST.T06
- INVAR | tests_scripts/test_micropython_overrides.py:649-652 | "Values alone cannot prove the shim was REACHED" | Generated lwipopts.h carries a sentinel that the build readback must find | area: TOOL | covered-by: TOOL.T11
- LIMIT | tests_scripts/test_micropython_overrides.py:658-660 | "Driven through a stub compiler, so every outcome of the real `-E` run is reachable without an ARM toolchain." | Readback logic is tested only with a stub compiler here; the real `-E` run happens only in a real firmware build | area: TOOL | -
- LIMIT | tests_scripts/test_micropython_overrides.py:792-793 | "(\"800U\", \"cannot parse\"),  # the options set here never carry a suffix - refuse, not guess" | Macro evaluator refuses casts and integer suffixes by design | area: TOOL | -

## tests_scripts/test_persistence_write_marker_completeness.py
- SETTLED | tests_scripts/test_persistence_write_marker_completeness.py:5-7 | "The gate covers the write a test OWNS, not one it is merely reached through ... Owner's rule, 2026-09-18" | Prerequisite writes stay unmarked; "not spend zero" | area: HW | related: HW.T01
- INVAR | tests_scripts/test_persistence_write_marker_completeness.py:1-3,171-183 | "a test that PUTs a config-persisting field but forgets @pytest.mark.persistence_write spends real RP2040 flash wear on every routine run, silently" | Enforced wear guard over tests_hardware/ (excluding device_scripts/) | area: HW | related: HW.T01
- LIMIT | tests_scripts/test_persistence_write_marker_completeness.py:50-53 | "device_scripts/ is real MicroPython pushed to the board - it has no http_client and no markers." | Board-side scripts that write config (`_set_dict_cfg`/`write_config`) are outside this guard | area: HW | covered-by: HW.S05
- LIMIT | tests_scripts/test_persistence_write_marker_completeness.py:99-106,116-121 | "(enclosing function name, call) for every call named `fetch` in the module." | Detector sees only calls named `fetch` with a literal "PUT" method and a literal dict body; non-PUT writes, mpremote/`run_isolated` config writes, raw sockets ("deliberately out of scope", :272-274) and FRAM writes are not seen | area: HW | related: HW.T01
- MIRROR | tests_scripts/test_persistence_write_marker_completeness.py:19-22,56-62 | "_ROUTE_DISPATCH_FIELDS = frozenset({\"SystemCmd\", \"PauseTime\", \"lightCmdLED\", \"ResetErrors\"})" | Four route-level dispatch-only fields hand-listed vs asy_webserver_service.py; the rest derived from `# @web ... dispatch=true` tags by regex (a field wrongly counted dispatch-only fails SILENTLY — :336-338) | area: REST | -
- ASSUME | tests_scripts/test_persistence_write_marker_completeness.py:24-29 | "config_manager.py's write_config() short-circuits on `if not changed` BEFORE staging anything" | Two exempt tests rest on this src behaviour; one on `_VAL_NH`'s exact 3..1024 bound ("at exactly 1024 it would be valid and this would be a real flash write") | area: CORE | related: CORE.T02
- LIMIT | tests_scripts/test_persistence_write_marker_completeness.py:285-304 | "Checked per entry and per FIELD rather than against a fixed count" | Exemption re-derivation searches only tests_hardware/bench/test_network_resilience.py and counts `== "Invalid"` / `not in body["result"]` substrings in the function text, not which field each assertion is about | area: HW | -
- INVAR | tests_scripts/test_persistence_write_marker_completeness.py:32-47 | "Pinned by name so a NEW one has to be triaged deliberately" | `_KNOWN_PERSISTING_HELPERS` = {isl29125_write_worker, bmp3xx_write_worker, joined_hotspot, _restore_ssid_over, _recover_stale_dut_credentials}; whether each helper's callers carry the marker is NOT verified ("this file cannot verify by name resolution", :307) | area: HW | related: HW.T01
- DRIFT | tests_scripts/test_persistence_write_marker_completeness.py:194-196 | "Exactly one exists today and it provably persists nothing" | `_JUSTIFIED_UNREADABLE_BODIES` (:186-190) holds two entries (the 413 test and `_put_sized`) | area: DOC | -
- ASSUME | tests_scripts/test_persistence_write_marker_completeness.py:186-190 | "vendored ext/microdot.py rejects it with 413 before this project's route handler" / "it pads an UNKNOWN sensor key, which PUT /sensors ignores silently" | Exemptions rest on Microdot's body cap and `_put_sensors` silently dropping unknown sensor keys (itself a seed) | area: REST | related: REST.S13
- SUPPRESS | tests_scripts/test_persistence_write_marker_completeness.py:202-206 | "a ceiling-close retry wrapper that forwards every argument unchanged" | One allowlisted forwarding wrapper (`bench/test_bus_concurrency_under_api_load.py::fetch`); its signature parity with http_client.fetch is re-derived | area: HW | -
- LIMIT | tests_scripts/test_persistence_write_marker_completeness.py:161-168 | "if \"persistence_write\" in ast.dump(dec)" | "Marked" = any decorator whose AST dump contains the string; class-level/module `pytestmark` markers are not recognised | area: HW | -
- INVAR | tests_scripts/test_persistence_write_marker_completeness.py:367-376 | "--strict-markers is off, so an unregistered marker - a typo, or one left by a rename - is silently inert" | Mitigation for CI.S13; built-in allowlist includes "timeout" (a plugin marker, inert unless pytest-timeout is installed) | area: HW | covered-by: CI.S13
- INVAR | tests_scripts/test_persistence_write_marker_completeness.py:379-384 | "scd30_extra_write only NARROWS, and nothing makes it imply the global gate" | Enforced: `scd30_extra_write` never carried without `persistence_write` | area: HW | related: HW.T13
- DRIFT | tests_scripts/test_persistence_write_marker_completeness.py:230-232,243 | "F15's residual, closed." / "F14's first draft is replayed verbatim" | Cites temporary queue row IDs from permanent code (low) | area: DOC | related: DOC.T03

## tests_scripts/test_request_body_cap_headroom.py
- INVAR | tests_scripts/test_request_body_cap_headroom.py:1-3,111-120 | "the largest body any device's own schema can legitimately produce must still fit under `max_content_length`. Nothing else checks this" | Enforced per device and per PUT route, cap read from src/ via ast (SPEC I.6); the hardware tier's "W3" checks it on silicon but not in CI | area: REST | related: REST.T01
- LIMIT | tests_scripts/test_request_body_cap_headroom.py:79-107 | "_put_sections ... generate_definitions(model, ...)" | Bound is computed from the website definitions (only `@web`-tagged writable fields), compact JSON (no whitespace), and string `maxLength` as characters; a PUT-able field without an `@web` tag, pretty-printed bodies and multi-byte UTF-8 are not counted | area: REST | related: WEB.T02
- ASSUME | tests_scripts/test_request_body_cap_headroom.py:23-26 | "_MAX_JSON_NUMBER = len(\"-1.2345678901234567e+308\")" | "Legitimate" numbers are assumed to be at most 24 characters; a client may send longer numeric literals (trailing zeros) that the cap then refuses | area: REST | -
- ASSUME | tests_scripts/test_request_body_cap_headroom.py:28-29 | "Only /sensors nests its body per group ({\"SCD30\": {...}}); asy_webserver_service.py's own comment calls the rest \"flat settings endpoints\"" | Route-shape knowledge copied from a src comment | area: REST | -
- INVAR | tests_scripts/test_request_body_cap_headroom.py:32-41 | "_EXPECTED_LARGEST = {\"arzi\": 1312, \"dev\": 1312, ..." | Pinned per-device largest legitimate body (all 1312 B); growth must be deliberate and SPEC I.6's quoted figure updated with it | area: REST | -
- DRIFT | tests_scripts/test_request_body_cap_headroom.py:2-3 | "every new driver grows it - dev's `/sensors` is 338 B larger than wozi's purely for carrying one more sensor" | All six devices pin the same 1312 B largest body, so the binding route is not driver-dependent today; "every new driver grows it" does not describe the pinned maximum (low) | area: DOC | -

## tests_scripts/test_request_timeout_ceiling.py
- MIRROR | tests_scripts/test_request_timeout_ceiling.py:62-70 | "CLAUDE.md's src/<->js/ cross-language mirror obligation (SPECIFICATION.md Part G) applied to the one number" | js/poll-manager.js `DEFAULT_TIMEOUT_MS` must equal src `outer_cap_s` (enforced); the plan notes the client clock starts before connect while the server's starts at accept | area: WEB | related: WEB.S06
- MIRROR | tests_scripts/test_request_timeout_ceiling.py:72-97 | "_SERVER_OUTER_CAP_S carries a \"keep in sync\" comment and nothing enforced it" | Enforced: twin suite `_SERVER_OUTER_CAP_S == outer_cap_s`, its `_RESET_ERRORS_TIMEOUT_S` in (cap, cap+5]; tests_hardware/error_log_helpers.py's hardcoded copy only bounded below ("extra slack for real WiFi latency") | area: SCR | related: PERF.T03
- MIRROR | tests_scripts/test_request_timeout_ceiling.py:100-133 | "Both failed silently on silicon when they outlived the firmware's own timeouts (SPECIFICATION.md H.7.1)" | harness `dwell_s < per_call_timeout_s`, `probe_limit*dwell_s < outer_cap_s`, `probe_limit >` largest shipped ceiling; holder `_DRIP_INTERVAL_S < per_call_timeout_s`, `_RECYCLE_S < outer_cap_s` | area: HW | -
- ASSUME | tests_scripts/test_request_timeout_ceiling.py:262-263 | "The board refuses by closing ~6 ms after connect, after the request is already sent." | Measured board refusal timing encoded in a test rationale | area: HW | related: HW.T16
- MIRROR | tests_scripts/test_request_timeout_ceiling.py:296-297 | "A held socket silent past per_call_timeout_s is answered and logs wrnno=2" | Host test relies on the webserver's wrnno=2 meaning; structural check keyed to local names (`extra`, `_pad`, `HELD_REQUEST_LINE`) in one bench test | area: REST | related: XCUT.T07
- SUPPRESS | tests_scripts/test_request_timeout_ceiling.py:199-204 | "warnings.simplefilter(\"ignore\", pytest.PytestUnknownMarkWarning)" | Loads a real bench test module into the host process with unknown-marker warnings silenced | area: TEST | -
- LIMIT | tests_scripts/test_request_timeout_ceiling.py:211-238,280-291 | "window_s: float = 0.6" | Loopback thread timing (0.6 s windows, 2 ms sampling, 0.2 s sleeps) — CI-load sensitive | area: TEST | related: TEST.T04

## tests_scripts/test_require_clean_hardware_run_sh.py
- SETTLED | tests_scripts/test_require_clean_hardware_run_sh.py:13-21 | "persistence_write/scd30_extra_write are deliberately absent: they DESELECT rather than skip, which is invisible to this script by design" | Pinned marker→flag map for skip gates: flash_cycle, long_soak (`--soak-tier`), multi_day_rollover, neopixel_sweep | area: SCR | related: HW.T13
- LIMIT | tests_scripts/test_require_clean_hardware_run_sh.py:136-155 | "if _SKIP_GATES[target.attr] not in body:" | "Really checks its own flag" = the flag string appears anywhere in the function's source text (a comment or docstring mention satisfies it); only function decorators are scanned (class/module markers not) | area: HW | related: HW.T13
- LIMIT | tests_scripts/test_require_clean_hardware_run_sh.py:78-81,161 | "test_spoofed_off_subnet_source_address_is_ignored SKIPPED (unconfirmed)" | One bench test is a known permanent, unconditional skip accepted by the verdict script | area: HW | -
- ASSUME | tests_scripts/test_require_clean_hardware_run_sh.py:175-177 | "pytest does not print \"0 passed\" today, but a plugin or a future summary format that did" | Verdict parsing depends on pytest's summary-line format (`tail -1` of "N deselected") | area: SCR | related: SCR.T05
- LIMIT | tests_scripts/test_require_clean_hardware_run_sh.py:24-34 | "The script's own contextual whitelist, parsed back out of it" | Whitelist parsed from the shell script by regex (`[ "$arg" = "--flag" ] && var=1` / `if [ "$var" = 0 ]; then`); `--flag=value` forms are not modelled | area: SCR | related: SCR.S01

## tests_scripts/test_resolve_board_device.py
- PLATFORM | tests_scripts/test_resolve_board_device.py:14-15,45-46 | "_PICO_VENDOR = \"2e8a\"" / "usb-MicroPython_Board_in_FS_mode_{serial_no}-if00" | Board identification depends on the RP2040/MicroPython USB vendor ID and by-id naming; Arduino peer vendor 2341 | area: HW | related: HW.T06
- INVAR | tests_scripts/test_resolve_board_device.py:83-88 | "The `board` fixture skips on an unreachable device, so this tier stays collectible with nothing attached" | `_NO_BOARD_DEVICE` must be a path that cannot exist; two boards is a hard error naming MPREMOTE_DEVICE | area: HW | related: HW.T14

## tests_scripts/test_setup_cross_browser_toolchain_sh.py
- WORKAROUND | tests_scripts/test_setup_cross_browser_toolchain_sh.py:1-3,11 | "_TOLERANCE = ' || echo \"== apt-get update reported errors - continuing, the install below still gates\"'" | `apt-get update` failures are deliberately swallowed (third-party source breakage) while every `apt-get install` stays fatal (enforced); removal trigger: none stated | area: SCR | -
- LIMIT | tests_scripts/test_setup_cross_browser_toolchain_sh.py:15-16,31-36 | "present so only the WebKit block, the one that reaches apt, actually runs" | Only the WebKit/apt block is exercised; Edge/Firefox install paths (external downloads, micromamba) are stubbed out | area: SCR | related: CI.S06

## tests_scripts/test_setup_toolchain_env.py
- LIMIT | tests_scripts/test_setup_toolchain_env.py:1-7 | "never real hardware, sudo, or network" / "End-to-end behavior - USB detection, the bridge and AP working - is proven on the real bench unit instead" | `env` tiers are tested only against a recording fake `run()` and fake /sys; the real bridge/AP path is verified manually on the bench, not in CI | area: TOOL | related: TOOL.T13
- LIMIT | tests_scripts/test_setup_toolchain_env.py:269-271 | "`nmcli -g`'s own ':' escaping modelled - without either, the MAC check passes here while never matching on hardware" | Fake fidelity explicitly limited to the nmcli/ip output shapes it models | area: TOOL | -
- SETTLED | tests_scripts/test_setup_toolchain_env.py:335-337 | "must be flagged and never auto-repaired - cycling a live bridge's MAC risks the same SSH-drop" | Pins CLAUDE.md's 2026-09-04 lockout rule: MAC mismatch warns only; on creation the MAC pin precedes `connection up br0-eth0` (enforced by ordering assert, :403-416) | area: TOOL | related: TOOL.T03
- PLATFORM | tests_scripts/test_setup_toolchain_env.py:409,314 | "assert any(\"wifi-sec.pmf disable\" in c for c in joined)  # load-bearing cyw43439 tuning" | Bench AP must disable PMF for the CYW43439 and pin channel 6 (a pre-fix bridge on channel 13 is self-healed) | area: TOOL | related: HW.T07
- MIRROR | tests_scripts/test_setup_toolchain_env.py:433-445 | "must READ them from here rather than carry its own literals ... its skip gate deselects rather than fails" | harness.BENCH_BRIDGE_CONN/ETH_CONN/AP_CONN must be read from setup_toolchain (enforced by source substring) | area: HW | -
- WORKAROUND | tests_scripts/test_setup_toolchain_env.py:480-514 | "run() failing its first `failures` calls the way a 502 from a release download does" | `uv sync` retried UV_SYNC_ATTEMPTS=3 with 10 s/20 s pauses for transient upstream download failures; removal trigger: none stated | area: TOOL | related: CI.S17
- LIMIT | tests_scripts/test_setup_toolchain_env.py:464-465 | "the soft skip is still the right outcome - it is only the *silent* skip on a pinned repo that was wrong" | npm install is silently skipped when neither .nvmrc nor npm exists (deliberate) | area: TOOL | -
- ASSUME | tests_scripts/test_setup_toolchain_env.py:533-534 | "never to override a correct Node the caller already manages (nvm, a system install, CI's own setup-node)" | ensure_node defers to any PATH node whose major matches; only the major is compared | area: TOOL | related: TOOL.S02

## tests_scripts/test_strip_type_checking.py
- DRIFT | tests_scripts/test_strip_type_checking.py:51-52 | "BACKLOG.md's prototype note says leave any compound condition untouched rather than guess" | Dangling named citation | area: DOC | covered-by: DOC.S05
- LIMIT | tests_scripts/test_strip_type_checking.py:50-62 | "if TYPE_CHECKING and extra_check():" / "if TYPE_CHECKING:\n    W = 1\nelse:" | Pinned known behaviour: compound conditions and `if/else` forms are left in the shipped copy unstripped | area: SCR | related: GEN.S12
- LIMIT | tests_scripts/test_strip_type_checking.py:91-104 | "Some files extend the except handler with a runtime cast() fallback ... the transform correctly leaves it alone" | Real-src check asserts only that no `if TYPE_CHECKING:` remains and the output parses; runtime behaviour of stripped copies is never executed | area: SCR | covered-by: SCR.T10

## tests_scripts/test_test_sh.py
- INVAR | tests_scripts/test_test_sh.py:31-44,47-53 | "The race this ordering closes: the generator globs devices/*.toml, while the malformed-TOML test writes a throwaway one into the live tree" | test.sh must sweep `devices/zz_test_*.toml`, then generate, then background the pytest tier (source-order substring checks) | area: SCR | related: TEST.T13
- LIMIT | tests_scripts/test_test_sh.py:56-72 | "text = (repo_root / \"tests_scripts\" / \"test_build_website_sh.py\").read_text()" | The reserved-prefix guard inspects only test_build_website_sh.py; a live-tree writer added in any other file is not checked | area: TEST | related: TEST.T13
- INVAR | tests_scripts/test_test_sh.py:142-153,180-190,214-223 | "250/900 are the boundaries scripts/test.sh compares with -le" | Parallelism probe bands, cgroup-v2 quota clamp, `TEST_PARALLELISM=0` hang guard ("`wait -n || true` spin forever") pinned; bench Pi4 is the 2x class | area: SCR | related: SCR.T01
- ASSUME | tests_scripts/test_test_sh.py:106-108,244-246 | "a mid-band 0.7s stub read 919-963ms under 96 spinners on 2026-09-22" / "131-141ms idle against 391ms in situ, 8 jobs where 16 was warranted" | Dated single measurements behind the stubbed-clock design and the probe-placement rule | area: SCR | related: TEST.T04
- INVAR | tests_scripts/test_test_sh.py:269-271,330-331 | "bash does not kill background jobs when the parent exits, so an abort before the final `wait` orphaned it for up to 1200s" | `_cleanup()` EXIT trap must signal recorded pids, never `pkill` ("procps is absent from a --variant=minbase chroot") | area: SCR | related: TEST.T16
- INVAR | tests_scripts/test_test_sh.py:384-437 | "a ~/pico-toolchain predating the split holds an executable build-standard that still carries the flag, which an existence check accepts" | unix_port_variant() must report plain/settrace/unusable (incl. missing frozen asyncio) and a mismatch must rebuild then exit if still wrong | area: SCR | covered-by: SCR.S05
- SUPPRESS | tests_scripts/test_test_sh.py:405-408 | "pytest.skip(f\"the --coverage variant is not built at {settrace_bin}" | Settrace-variant self-report test skips without that binary | area: TEST | -
- PLATFORM | tests_scripts/test_test_sh.py:494-506 | "gc.threshold() raises OverflowError only near 2^63 (measured) - so the bound asserted here is the rp2040's" / "py/modgc.c maps every one of them to (size_t)-1" | GC_THRESHOLD validated to the rp2040's 32-bit range; any negative = reactive default | area: PLAT | -
- INVAR | tests_scripts/test_test_sh.py:513-555 | "a real race until 2026-09-22: the rejection tests above run a nested test.sh ... a nested run that swept before validating deleted them mid-test" | Argument/GC_THRESHOLD validation must precede `rm -rf tests/_tmp` and the devices sweep; these tests run the REAL test.sh nested inside the tier | area: SCR | related: SCR.T14
- INVAR | tests_scripts/test_test_sh.py:558-629 | "a degrade-and-pass went by in silence" | Unit-tier MemoryError gate: both PASS and FAIL exits flagged, flag sets failed=1 and is named in the summary (structural substring checks); injections worded "simulated allocation failure" (15 sites) | area: MEM | related: TEST.T18
- ASSUME | tests_scripts/test_test_sh.py:602-603 | "measured over a full 85-file run, the suite's own output contains neither pattern once" | Dated measurement justifying the gate's false-positive rate; "85 files" is a dated count | area: MEM | related: DOC.S08
- INVAR | tests_scripts/test_test_sh.py:742-743 | "GitHub drops every error annotation past the tenth in a step" | Annotation ordering/cap behaviour depends on a GitHub limit | area: CI | -
- INVAR | tests_scripts/test_test_sh.py:791-839 | "while its whole run was continue-on-error a failure there was invisible. One really was." | --coverage exit codes 0/1/3 (test failure outranks renderer failure); ci.yml's unit-tests-coverage step must not be continue-on-error, tolerate exit 3, and six report steps use `always() &&` (enforced) | area: CI | related: CI.T11

## tests_scripts/test_tests_hardware_conftest_constants.py
- MIRROR | tests_scripts/test_tests_hardware_conftest_constants.py:1-3,50-81 | "Drift here is silent and only shows up as a bench recovery that scans for an SSID no board is broadcasting" | tests_hardware/conftest.py `_DUT_HOSTNAME_CANDIDATES` (first = dev.toml hostname, last = `_VAL_HOST` default, each 1..32) and `_DUT_HOTSPOT_PASSWORD` must equal both dev.toml's `hotspot_password` and `_VAL_HOTSPOT_PW`'s default (enforced) | area: HW | related: HW.T11
- RISK | tests_scripts/test_tests_hardware_conftest_constants.py:72-81 | "Both must agree or the join just fails." | Enforces that the bench's hardcoded hotspot password equals the shared src default and dev's TOML value — the accepted-risk shared credential is pinned in three places | area: SEC | related: SEC.T07
- ASSUME | tests_scripts/test_tests_hardware_conftest_constants.py:13 | "_BENCH_DEVICE = \"dev\"  # the only unit ever bench-flashed (CLAUDE.md's hard rule)" | Hardcoded bench device | area: HW | -

## tests_scripts/test_tests_hardware_persistence_write_gating.py
- INVAR | tests_scripts/test_tests_hardware_persistence_write_gating.py:1-3,27-54 | "--allow-persistence-writes is the single global permission ... --allow-scd30-extra-write only narrows further" | Verified by real `pytest --collect-only` runs of tests_hardware/ (no hardware); board-free check executed in the host tier | area: HW | related: HW.T14
- LIMIT | tests_scripts/test_tests_hardware_persistence_write_gating.py:32,39,47 | "assert \"7 deselected\" in output" | Exact deselect counts pinned for one file (flash/test_bus_concurrency.py); bench tier only checks "some" deselected; flash tier checks two named tests | area: HW | -
- ASSUME | tests_scripts/test_tests_hardware_persistence_write_gating.py:74-78 | "SGPResetVOC/ISLCalibrate carry `dispatch=true` ... never in ConfigManager's cache" | The bench memory-stress hammer stays ungated because its only PUT is dispatch-only | area: HW | related: HW.S23

## tests_scripts/test_threshold_runner.py
- INVAR | tests_scripts/test_threshold_runner.py:1-3 | "a runner that quietly stopped applying the threshold would leave CI's unit-tests-gc-threshold job just as green while measuring the (e) stage twice" | Pins tests/_threshold_runner.py: applies the threshold before the file imports, runs `microtest.run()` under `__main__`, propagates SystemExit only | area: TEST | related: SCR.T01
- MIRROR | tests_scripts/test_threshold_runner.py:11 | "_SHIPPED_THRESHOLD = 32768  # what buildgen emits into the generated boot entry (codegen.py)" | Hand copy of the firmware's gc.threshold value; not cross-checked against codegen here | area: MEM | related: SCR.S10
- PLATFORM | tests_scripts/test_threshold_runner.py:76-77,90-92 | "MicroPython's SystemExit carries .args, not CPython's .code" / "the Unix port prints an uncaught traceback to STDOUT, not stderr (verified directly)" | Runtime facts the runner and gate depend on | area: PLAT | -

## tests_scripts/test_timer_stagger_no_coincidence.py
- LIMIT | tests_scripts/test_timer_stagger_no_coincidence.py:7,11-18 | "An exact replica of _timer_sequencer()'s arithmetic ... rather than the real recursive implementation" | Proof re-implements `1000 // (n+1)` and hand-copies `_TIMER_BASE_PERIOD`; the real sequencer is never read | area: XCUT | covered-by: TEST.S06
- ASSUME | tests_scripts/test_timer_stagger_no_coincidence.py:28-30,90-92 | "every real period being a whole-second multiple makes every pairwise gcd one too" | Proof holds only for software-counter sensors with whole-second trigger periods and offsets relative to one common start | area: XCUT | related: XCUT.S06

## tests_scripts/test_twin_never_needs_tests_on_its_path.py
- INVAR | tests_scripts/test_twin_never_needs_tests_on_its_path.py:1-3,17-20 | "_http_client.HttpResponse.json() imports tests/_strict_json lazily, and the twin's own MICROPYPATH carries no tests/" | Only digital_twin/_http_client.py may import `_strict_json`, lazily; no twin module may call `.json()` | area: TWIN | -
- LIMIT | tests_scripts/test_twin_never_needs_tests_on_its_path.py:27-31,24-25 | "Every MICROPYPATH the twin is started with, from the two places that set one." | Only scripts/_digital_twin_ci_suite.py and run_unix_port_integration.sh are scanned; test_digital_twin_generated_boot.py's and tests_js' twin launches set their own MICROPYPATH unscanned; only top-level digital_twin/*.py; `.json()` detection is by method name with no args | area: TWIN | related: TWIN.T11
- SETTLED | tests_scripts/test_twin_never_needs_tests_on_its_path.py:51-52 | "If tests/ is ever added to it, this guard is obsolete rather than failing - delete it then, do not widen it." | Stated removal condition for the guard | area: TWIN | -

## Coverage
| file | comment/doc lines read | items |
|---|---|---|
| tests_scripts/_devices.py | 9 | 4 |
| tests_scripts/_script_loader.py | 9 | 2 |
| tests_scripts/_toml_fixtures.py | 10 | 4 |
| tests_scripts/buildgen_fixtures/malformed_missing_device_table.toml | 5 | 1 |
| tests_scripts/buildgen_fixtures/multi_instance.toml | 17 | 2 |
| tests_scripts/buildgen_fixtures/novel_combo.toml | 25 | 4 |
| tests_scripts/conftest.py | 18 | 6 |
| tests_scripts/test_bench_harness_helpers.py | 13 | 7 |
| tests_scripts/test_bench_no_task_ended_completeness.py | 15 | 8 |
| tests_scripts/test_bench_restores_serving.py | 8 | 3 |
| tests_scripts/test_build_firmware.py | 50 | 11 |
| tests_scripts/test_build_frozen_html_sh.py | 11 | 3 |
| tests_scripts/test_build_website_sh.py | 31 | 5 |
| tests_scripts/test_buildgen_defaults.py | 7 | 2 |
| tests_scripts/test_buildgen_definitions.py | 69 | 7 |
| tests_scripts/test_buildgen_driver_registry.py | 13 | 3 |
| tests_scripts/test_buildgen_frozen_modules.py | 12 | 4 |
| tests_scripts/test_buildgen_generate.py | 103 | 12 |
| tests_scripts/test_buildgen_graph.py | 18 | 3 |
| tests_scripts/test_buildgen_limits.py | 38 | 3 |
| tests_scripts/test_buildgen_requires_tag.py | 94 | 4 |
| tests_scripts/test_buildgen_schema_ast.py | 24 | 3 |
| tests_scripts/test_buildgen_tag_comments.py | 96 | 5 |
| tests_scripts/test_buildgen_twin_wiring.py | 35 | 8 |
| tests_scripts/test_buildgen_validate.py | 298 | 22 |
| tests_scripts/test_buildgen_value_wiring.py | 14 | 2 |
| tests_scripts/test_buildgen_version.py | 7 | 4 |
| tests_scripts/test_buildgen_web_tag.py | 80 | 6 |
| tests_scripts/test_buildgen_wiring.py | 49 | 4 |
| tests_scripts/test_ceiling_probe.py | 21 | 5 |
| tests_scripts/test_comment_block_cap.py | 14 | 6 |
| tests_scripts/test_coverage_runner.py | 16 | 5 |
| tests_scripts/test_device_script_config_flush.py | 24 | 5 |
| tests_scripts/test_device_script_gc_threshold.py | 14 | 4 |
| tests_scripts/test_device_tomls.py | 91 | 12 |
| tests_scripts/test_digital_twin_boot_contiguity.py | 78 | 13 |
| tests_scripts/test_digital_twin_ci_suite_ceiling.py | 12 | 5 |
| tests_scripts/test_digital_twin_ci_suite_errcount.py | 92 | 13 |
| tests_scripts/test_digital_twin_ci_suite_soak.py | 28 | 3 |
| tests_scripts/test_digital_twin_generated_boot.py | 42 | 8 |
| tests_scripts/test_gc_collect_sites.py | 12 | 2 |
| tests_scripts/test_generate_sensortask_modules.py | 13 | 2 |
| tests_scripts/test_heap_map_parser.py | 48 | 6 |
| tests_scripts/test_http_client_ceiling_close.py | 20 | 5 |
| tests_scripts/test_js_coverage_excludes_json.py | 6 | 2 |
| tests_scripts/test_js_coverage_report_dir.py | 7 | 2 |
| tests_scripts/test_lint_sh.py | 20 | 4 |
| tests_scripts/test_live_twin_ceiling_parser.py | 4 | 2 |
| tests_scripts/test_measurement_field_tuple_agreement.py | 18 | 2 |
| tests_scripts/test_memory_error_gate_agreement.py | 22 | 5 |
| tests_scripts/test_micropython_overrides.py | 110 | 14 |
| tests_scripts/test_persistence_write_marker_completeness.py | 89 | 15 |
| tests_scripts/test_request_body_cap_headroom.py | 25 | 6 |
| tests_scripts/test_request_timeout_ceiling.py | 68 | 7 |
| tests_scripts/test_require_clean_hardware_run_sh.py | 33 | 5 |
| tests_scripts/test_resolve_board_device.py | 14 | 2 |
| tests_scripts/test_setup_cross_browser_toolchain_sh.py | 12 | 2 |
| tests_scripts/test_setup_toolchain_env.py | 53 | 8 |
| tests_scripts/test_strip_type_checking.py | 12 | 3 |
| tests_scripts/test_test_sh.py | 180 | 13 |
| tests_scripts/test_tests_hardware_conftest_constants.py | 19 | 3 |
| tests_scripts/test_tests_hardware_persistence_write_gating.py | 15 | 3 |
| tests_scripts/test_threshold_runner.py | 21 | 3 |
| tests_scripts/test_timer_stagger_no_coincidence.py | 28 | 2 |
| tests_scripts/test_twin_never_needs_tests_on_its_path.py | 12 | 3 |

## Totals per kind
| kind | count |
|---|---|
| TODO | 1 |
| LIMIT | 100 |
| RISK | 8 |
| SETTLED | 14 |
| ASSUME | 65 |
| WORKAROUND | 4 |
| INVAR | 57 |
| MIRROR | 42 |
| SUPPRESS | 18 |
| PLATFORM | 21 |
| OPENQ | 0 |
| DRIFT | 22 |
| **total** | 352 |

## Top 10
1. LIMIT tests_scripts/test_comment_block_cap.py:59 — any tag substring exempts a whole over-cap comment block; the gate is weaker than CLAUDE.md's "prose introducing tags is not exempt"; JS/CSS/config remain review-only.
2. LIMIT tests_scripts/test_persistence_write_marker_completeness.py:99-121 — wear guard sees only literal-method/literal-body `fetch()` PUTs; device_scripts/, mpremote writes and non-fetch HTTP are outside it; helper callers' markers unverified (:307).
3. DRIFT tests_scripts/test_persistence_write_marker_completeness.py:194-196 — "Exactly one exists today" vs two `_JUSTIFIED_UNREADABLE_BODIES` entries.
4. LIMIT tests_scripts/test_request_body_cap_headroom.py:79-107 — body-cap headroom computed from @web-tagged fields only, compact JSON, chars not bytes; ASSUME 24-char number bound (:23-26).
5. ASSUME tests_scripts/test_digital_twin_boot_contiguity.py:46-80 — I.4(f.1) guard bounds are single-campaign twin measurements with thin (~1.4x) margins; no MemoryError scan of probe output (:127-140, TEST.T18).
6. LIMIT tests_scripts/test_gc_collect_sites.py:15-59 + test_lint_sh.py:86-98 — gc.collect guard covers src/ (name `gc` only) and buildgen presence; lint.sh allowance is file-granular; tests/ and digital_twin/ unchecked.
7. RISK tests_scripts/test_tests_hardware_conftest_constants.py:72-81 / test_buildgen_generate.py:405-411 / test_buildgen_validate.py:92-94 — shared hotspot password pinned in 3+ places; out-of-bounds TOML values silently fall back to src defaults at boot.
8. ASSUME tests_scripts/test_http_client_ceiling_close.py:31-36 vs test_ceiling_probe.py:106-107 — ECONNREFUSED is a real failure for one oracle and the PCB-exhausted wall for the other.
9. LIMIT tests_scripts/conftest.py:55-60 (+ boot_contiguity :101-109, coverage_runner :20-28, overrides :44-49/:346-350) — toolchain-dependent tests SKIP when unprovisioned, while test_live_twin_ceiling_parser.py:20-25 hard-FAILS without node.
10. DRIFT tests_scripts/test_device_tomls.py:3 — "until Session 3's generator/validator exists": a second hand-written set of collision checks (own `_BASE_DOC`) duplicates buildgen.validate.
