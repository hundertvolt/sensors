B8 falsification, written by the agent (Wed Nov  4 09:10:56 UTC 2026)

Subject: `3d0e36bb` (6f24e171 + 3d0e36bb on `d5c90b71`), worktree `S/wt-b8f`, read-only apart from the plants
named below; every plant restored, `git status --porcelain` shows only `?? node_modules` at hand-back.
Pinned sources: MicroPython `v1.29.0` at `/root/pico-toolchain/micropython`, its `lib/pico-sdk` at `2.3.0`.
I read the code, the tests, the docs and git history. I did not read the unit's hand-back or action list.

Runs (5 of 10, one at a time, all through `S/u35/lead/run.sh`): `b8f_rebuild` (rc 0), `b8f_probe` (rc 0),
`b8f_probe2` (rc 0), `b8f_fw` (rc 1: only my reader of the image-record `.json` used the wrong path; both builds
printed their `== Image` line), `b8f_shelljs` (rc 0, 15/15). Outside run.sh I used system `python3` twice: once to
parse the six device TOMLs and print their bus/instance map, once to make text edits to my own probe files. Neither
ran repo code. The probes were `probe_build.py` (CPython: device-TOML variants through `generate_device()`, the setup
scan, the definitions mirror), `probe_defs.mjs` (node: `js/definitions.js`) and `probe_uart.py` (Unix port with the
`tests/` fakes). I wrote them under `S/u35r/r1/B8/f/ftmp/` and deleted that folder before writing this.

## Per claim

**1. REFUTED.** At least one removed check's violation loops the boot. Two more fail silently at run time, with
no logged error.
- **I2C frequency, boot loop.** `bus.i2c-frequency-range` (1..1,000,000) is gone. `buildgen/validate.py:535` now checks
  only that the value is an int. The only remaining bounds are the drivers' `@requires bus.frequency<=` tags
  (`src/asy_scd30_driver.py:178`, `src/asy_sgp40_driver.py:136`), and BMP3XX and ISL29125 carry none. dev's `i2c0`
  holds only the BMP3XX.
  - Probe `b8f_probe`, variant `freq_2pow31`: setting `frequency = 2147483648` on dev's `i2c0` BUILT. The generated
    line is `asy_i2c_driver.I2C(0, 13, 12, frequency=2147483648)` (`buildgen/codegen.py:175`).
  - At boot `build_system()` runs `I2C.__init__` → `init()` → `_I2C(..., freq=frequency)` (`src/asy_i2c_driver.py:100`,
    `:285`). rp2's `freq` is `MP_ARG_INT` (`ports/rp2/machine_i2c.c:68`), converted by `mp_obj_get_int()`
    (`py/argcheck.c:109` → `py/obj.c:366` → `py/objint_mpz.c:438`). A value that is no 32-bit machine word raises
    `OverflowError`. The same conversion raises on the Unix port (`b8f_probe2`: "OverflowError overflow converting
    long int to machine word").
  - Nothing catches it in `build_system()`. The boot entry's `record_loop_end()` writes nothing during boot
    (`src/asy_system_service.py:161-168`), and the armed watchdog resets the unit. The next boot reads 10 + phase and
    fails the same way, every boot, with no web server ever up.
  - A frequency of 0 or a negative one is harmless: libgcc's `__aeabi_idiv0` just returns (`firmware.dis` symbol at
    `0x20003ba0` is a bare `bx lr`; `pico_divider/divider_hardware.S:221-232`), and the bus runs very slowly.
- **UART txbuf at or below 0, silent livelock.** The floor half of `bus.uart-rxbuf/txbuf-range` is gone. Only
  `txbuf > 32766` is refused now (`buildgen/validate.py:822`).
  - Probe `b8f_probe2`: variants `txbuf_0` and `txbuf_m1` BUILT, rendering `asy_uart_driver.UART(0, ..., txbuf=0, ...)`.
  - The port keeps its own 256 for a value ≤ 0 (`ports/rp2/machine_uart.c:385`). The driver's own copy stays 0, and
    `_write_all()` sends `chunk = min(total - sent, self._txbuf)` (`src/asy_uart_driver.py:379`).
  - A zero-length write returns 0 (`py/stream.c:59`, `:266`), so `sent` never advances. `ready()` yields, so the
    watchdog stays fed, and nothing logs.
  - Unix port with the `tests/` fakes (`b8f_probe2`): with txbuf 32, `writefrom()` returns True after 2 writes (32 + 21
    bytes). With txbuf 0 or -1 it never returns in 200 ms: 4,096 logged zero-length writes, 0 bytes sent. On dev the
    link would hang, holding its session lock, with no error entry.
  - The rxbuf half of the floor stays covered: `rxbuf_31` → refused by `bus.uart-rxbuf-floor`.
- **`{source, field}` naming no field, silent None.** Probe variant `field_unknown` BUILT, rendering
  `ValueRef(scd30, "Tmp")`. The consumers read it with `getattr(..., None)` (`src/asy_notification_service.py:207`,
  `src/asy_sgp40_driver.py:303`). The warn signal then never evaluates, and the SGP40 skips every cycle
  (`src/asy_sgp40_driver.py:379-385`), with no log entry. That is neither a default kept nor a logged failure.
- **The other cases hold:**
  - UART baud 0 and -9600 build, and the port keeps its own baud (`machine_uart.c:285-287`).
  - Baud above 7,812,500 is clamped by the SDK (ibrd = 1). Up to about 54 M it builds only with a large rxbuf:
    `baud_10M` at rxbuf 512 and `baud_3G` are refused by `bus.uart-rxbuf-floor`, so no `OverflowError` is reachable
    on a UART.
  - An invalid hostname label builds, and `_with_default()` keeps "SensorNode" (`src/asy_wifi_service.py:122-133`).
  - Missing `name_ext` builds (`bmp_no_name_ext`).
  - Two instances on one UART are still refused, by `bus.fixed-address-collision` (`two_links_one_uart`).
  - `conn_fail_to_hotspot = 0` behaves like 1 (`src/asy_wifi_service.py:673`).
  - A `warn_*` key off the notification wires nothing (`buildgen/codegen.py:358-362`, `:724-731`).

**2. STANDS.** The check is still there (`buildgen/validate.py:589-597`). Variant `irq_str_checked` → refused by
`instance.irq-pull-up-type`. Planted break, in memory in `b8f_probe`: I skipped the check for `irq_pull_up` alone. The
same TOML then BUILT, rendering `irq_pull_up=false,` (`str("false")` at `buildgen/codegen.py:530`), which is an
undefined name inside `build_system()`. That is a `NameError` at every boot.

**3. STANDS.**
- `_check_instance_name_collisions()` (`buildgen/validate.py:632-646`) has the same logic as
  `25caf528:buildgen/validate.py:431-443`: instance against instance. Only the rule and fix fields and the internal
  error type differ.
- No accepted device can make two loggers share a name. `(driver, name_ext)` must be unique (`buildgen/model.py:137-154`).
  Every driver's base name (BMP3XX, ISL29125, NEOPIXEL, NOTIFY, SCD30, SGP40, UART, FRAM) is distinct and none is a
  prefix of another. A resolved name `base[_ext]` can never equal WIFI, DNSSRV, NTP, SYSTEM, WEBSERVER or any
  `CFGMGR_*` name.
- The uart_link's comm and driver share one logger (`src/asy_uart_link_driver.py:83`, `:95`).
- This rests on today's `src/` `_NAME` constants. A future driver named like a mandatory module would now build.

**4. REFUTED.** The single 1..200,000 µs check is real (`buildgen/validate.py:542-550`), and `smallest_hard_consumer()`
keeps every reader except the removed rule and that rule's test. But readers and docs still reference removed items:
- `tests_scripts/test_digital_twin_scenarios.py:252`: "the build rule, the twin scenario and the bench lag test all call
  buildgen's one export". The build rule is `bus.i2c-timeout-consumer`, which is gone.
- `tests_hardware/flash/test_memory_stress.py:172`: "# the build rule's and the twin scenario's one source".
- `SPECIFICATION.md:11938` (the `wdt.timeout_ms` row of the tunables register) still names "the boot bus clear's budget
  `_BOOT_CLEAR_BUDGET_MS` in `buildgen/validate.py`, three quarters of it ..., which every device's summed worst-case
  boot clear must fit". The constant is deleted.
- `SPECIFICATION.md:831` and `:13227` still say the build refuses the summed boot clear above three quarters of
  `wdt.timeout_ms`. That is the removed `bus.boot-clear-budget`.

**5. REFUTED (narrowly, on "prints nothing").** The rest holds:
- `_fatal` is RAM-only (`src/asy_print_log.py:80`). Its one reader is the supervisor (`src/asy_system_service.py:521`),
  which has stopped once the loop has ended.
- `record_loop_end()` still runs in the `except BaseException` arm (`buildgen/codegen.py:862-866`).
- `supervise_tasks()` never returns (`src/asy_system_service.py:746-753`), so a normal loop end does not exist.
- The start line is untouched.

But the console is not silent at a loop end. Once the entry returns, rp2 enters the friendly REPL
(`ports/rp2/main.c:246-259`), which prints the MicroPython banner and "Type help()" (`shared/runtime/pyexec.c:626-631`)
at every DebugLevel. The handler prints nothing; the device does. This is the port's behaviour and predates this
change, but it is a console print at level 0. See also finding A below.

**6. STANDS.** Generator bugs are still caught:
- `build_firmware.py` strips (AST-parses) the device module (`scripts/build_firmware.py:104`) and freezes the boot entry
  as `main.py`, which mpy-cross compiles.
- `tests/test_generated_boot_entry.py` `compile()`s both entries of every device.
- `tests_scripts/test_buildgen_generate.py:177` compiles both variants and parses every module.
- ruff and mypy cover `build/generated_src` (`scripts/lint.sh:49`, `pyproject.toml:367`).
- The tests_js tier compiles no Python, so "every test tier" holds only for the Python tiers. The doc is stale here,
  see claim 12.

**7. STANDS.** `src/asy_base_classes.py:50` reads `SetupFct = Callable[[], Awaitable[None]]`. The `b8f_probe` setup scan
covered every `async def setup` in `src/`: the only one answering a value is `UARTComm.setup -> bool`. Every device's
`_collect_setups()` lists only these, all `-> None` with no valued return: FRAMManager, SystemService, WifiService,
NTPClient, NeopixelDriver, SCD30/SGP40/BMP3XX/ISL29125 readers, NotificationService, UARTLinkDriver (it awaits the
comm's answer and answers None, `src/asy_uart_link_driver.py:287-289`) and WebserverService. The doc is stale here, see
claim 12.

**8. STANDS.**
- The blob ids of `js/shell.js`, `js/main.js`, `js/app.js` and `tests_js/shell.test.js` equal `656fc82f^`'s.
- No `build-date`, `pageBuildDate` or `buildDateOf` remains in js, html, scripts, tests or docs. The one BACKLOG mention
  (`BACKLOG.md:1119-1121`) records the change for the chroot run.
- `firstBuild` logic is intact (`js/shell.js:105-110`). `b8f_shelljs`: 15/15, including the different-build reload.

**9. STANDS.**
- The GET check is `!response.ok || response.body === null` (`js/render.js:619`), the same condition as
  `25caf528:js/render.js:353`.
- The non-object test now asserts a paint with no banner (`tests_js/render.test.js:1549-1557`).
- The `.card`/`.field` apply rules (`html/style.css:379-409`) are byte-identical to `25caf528:html/style.css:317-347`.
  The comment above them is 1 line where 25caf528 had 3, so "one comment line" is loose but the substance holds.

**10. REFUTED, on the mirror.**
- What holds:
  - `js/definitions.js` makes the same checks as `41b47f1d` (U10's form of U6), with today's sets: formats
    + `lasttaskend`; shapes + `hostName` and `ipv4List`. The post-U10 checks are gone.
  - Every device's definitions validate in both validators (`b8f_probe`: `[]` from both for all six).
  - The corpus is U10's 70 cases plus 5 for today's sets and the U10-era `alwaysExecuted` rule.
- What breaks: the Python mirror ("js/definitions.js's validateDefinitions(), rule for rule",
  `tests_scripts/test_buildgen_definitions.py:885-886`) now skips any group that is not a dict (`:802`).
  - The JS still sends every group through `validateGroup()` (`js/definitions.js:204`).
  - `b8f_probe`, for a group that is `"x"`, `5` or `null`:
    - Python mirror: `[]` for all three (accepted).
    - JS: two problems each for `"x"` and `5`; a TypeError on `null`.
  - U10's mirror rejected all three ("is not an object  # validateDefinitions() throws on it",
    `41b47f1d:tests_scripts/test_buildgen_definitions.py:348-349`).
  - The corpus cases that would have shown the split, "a group that is null" and "a group that is a string"
    (`d5c90b71:tests_scripts/definitions_shape_cases.json:87-88`), were removed. The JS still rejects the string group.

**11. REFUTED.**
- (a) The mirror weakening in claim 10 is not the mechanical consequence of any JS removal.
- (b) `tests_scripts/test_fatal_report_sites.py:165-173` dropped both boot entries from the scan entirely. The file
  already has a per-site exemption mechanism (`_EXEMPT`, `:21`), which could have exempted the one post-loop handler.
  Now any future broad handler in a boot entry, such as a pre-loop one, whose record the supervisor would read, goes
  unchecked.
- Smaller narrowing: the removed `test_settings_groups_are_the_generated_webserver_groups` compared every emitted
  settings section with `SETTINGS_GROUPS` (`d5c90b71:tests_scripts/test_buildgen_validate.py:955-979`). The kept
  `test_real_device_serves_the_settings_groups_of_the_one_table` (`tests_scripts/test_buildgen_generate.py:466-471`)
  checks only `networking` and `system`, so an extra emitted section would no longer be seen.
- These changes are mechanical:
  - the generator-bug tests (`_compiled()` gone);
  - the two stamp tests;
  - `test_host_cli_exit_idiom.py:106`: a missing definitions file still exercises a StageError, one line and exit 1
    (`scripts/_stage_website.py:374-379`).

**12. REFUTED.** Stale text describing a removed check, or the code before this change:
- `SPECIFICATION.md:10881-10883`: "It compiles all three sources, so a generator bug emitting invalid Python is a
  `BuildInternalError` naming the device, never a written file". `_compiled()` is removed.
- `SPECIFICATION.md:831`, `:11938` and `:13227`: the boot-clear budget (claim 4).
- `SPECIFICATION.md:4392`: "`SetupFct` (`Callable[[], Awaitable[bool]]`)". The code says `Awaitable[None]` (claim 7).

The stamp is gone from README, SPEC and BACKLOG.

**13. STANDS.**
- `b8f_probe2` (`S/u35r/r0/module_sizes.sh` at both revisions): `src/` bytecode is 194,887 B → 194,883 B. Only
  `asy_base_classes.py` changed, 10,219 → 10,215 B; no module grew.
- `git diff --numstat d5c90b71 3d0e36bb`: buildgen +39 -306, js +44 -235, scripts +8 -31, tests_scripts +65 -664.
- `b8f_fw`, `build_firmware.py dev`: head prints "60492 B free". With d5c90b71's 38 files planted it prints
  "58708 B free". Plant: `git checkout d5c90b71 -- <the 38 files>`, then restored with `git checkout 3d0e36bb -- <the
  same 38>` by a trap; porcelain was clean afterwards.

## Outside the claims

- **A.** The owner decision recorded at 2026-11-03 20:40 (`S/u35r/recovered/owner_rulings_after_LN118.md:534-536`)
  reads: "reset reason 22 stays the record, with its pre-bind, comment and F811 exemption". The change removed all
  three, along with `report_if_fatal(ended)` and its import (`buildgen/codegen.py:853-866`, `pyproject.toml:195`).
  Functionally harmless, since the handler now binds no name, but it departs from the recorded decision; it is for the
  lead to put to the owner if needed.
- **B.** The level-0 console-silence rule (owner, 2026-11-02, in `UART_C_PORT_CHANGELOG.md:217`) is not met at a loop
  end, because of rp2's REPL banner (claim 5). This predates the change: I am flagging it, not tracing it.
- **C.** The hostname length check stays (`device.hostname-length`, `buildgen/validate.py:398-405`) with the same
  consequence as the removed label check. Both drop to the shared "SensorNode" default without refusing a boot. This is
  an inconsistency in the removal criterion, not a defect.
