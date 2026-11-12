# Code review handover: snapshots 62-67 (2026-11-12)

The full hand-back of the `/code-review max` run (recall mode) over this branch, `claude/whole-project-audit-plan`,
at `e55eccf3`, in one file: the final report, then the deduplicated candidate list, the verifier verdicts and the raw
per-angle findings, each verbatim. The reviewed diff is `git diff e55eccf3~6..e55eccf3`, `audit/` excluded.

## 1. Final report

**Code review (max effort, recall mode): 15 findings below; none of the defects is in shipped firmware behaviour.**

**What I reviewed.** The literal "current diff" was empty: the branch matches `origin/claude/whole-project-audit-plan` and the tree is clean. `main...HEAD` is 814 commits and 15,773 files, too large to review. So I reviewed the "snapshot" commits 62–67 (`git diff HEAD~6..HEAD`, 57 files) and left out the `audit/` process records.

**How.** Eleven finder angles, then 36 deduplicated candidates, each given one independent verifier, then a gap sweep with its own verifier. Three candidates were refuted:
- **V13:** the reboot-persistence test kept its goal.
- **V27:** nothing overrides or patches `_FRAMBaseChunk._read`/`_write`.
- **S1:** the SGP40 "owed" exact count in the NTP-outage test; the code timeline and bench records both show the `(2, [W65, W35])` pair.

Most findings were reproduced on this aarch64 host with the pinned v1.29.0 Unix port, using scratch copies only. No repo file changed, no `build/` was left behind, and no hardware was touched.

**The main theme is arm64.** The new `build/portable_src` mechanism has gaps on the bench Pi, the Debian-trixie arm64 chroot leg, and arm64 generally. The worst one is that tests can pass against stale code: a deliberate CRC polynomial change in `src/` still passed 56/56. The remaining findings are tests that silently stopped checking what they claim, two sibling fixes left out, one latent `src/` contradiction with the spec, and decision-record breaches.

```json
[
  {"file": "scripts/micropypath.toml", "line": 4, "summary": "On arm64 the whole-module copies in build/portable_src/ come first on both MICROPYPATH layouts, but no freshness check covers them (no generator stamp, no tests/_generated_tree.py require_fresh(), no scripts/_run_checks.sh or _preflight.sh guard), so after an edit to src/crc_checks.py or src/asy_uart_driver.py the unit and twin runs silently test the old copy.", "failure_scenario": "Bench Pi (aarch64): after any generator run, change CRC8's default poly in src/crc_checks.py from 0x31 to 0x07 and run the documented single-file check (scripts/_run_checks.sh mpy:tests/test_crc_checks.py, unit layout). It reports 56/56 passed because crc_checks.__file__ is build/portable_src/crc_checks.py; only after regenerating does it report 2 failures (reproduced in a git-archive copy). py: selections, pytest tests_hardware --twin and record_twin_instrument_runs.py use the same stale copy. Because _sync_portable_copies() (scripts/_generate_sensortask_modules.py:317) also runs outside the stamp on every call, --if-stale included, it re-parses all 28 src/*.py on every host (~0.5 s), and on arm64 it rewrites both unchanged copies through tmp+rename about 7 times per npm run build:site."},
  {"file": "tests_scripts/test_fram_less_boot.py", "line": 83, "summary": "The arm64 support reaches only launchers that read scripts/micropypath.toml: this launcher, tests_scripts/test_microtest.py:62/:249 and tests_scripts/test_test_sh.py:1905 still hard-code a MICROPYPATH without build/portable_src (and fakes/), so on arm64 they still die importing src/crc_checks.py's @micropython.viper function, contrary to the new BACKLOG.md:375 claim.", "failure_scenario": "scripts/test.sh runs pytest tests_scripts unfiltered on every host. On the bench Pi or the Debian-trixie arm64 chroot leg, every fram-less device boot (tests/machine.py -> microtest -> asy_print_log -> crc_checks), about ten test_microtest tests and the per-file-timeout test exit with 'SyntaxError: invalid micropython decorator'. Reproduced for each launcher with the pinned build-standard binary; they pass once build/portable_src and fakes/ are added. digital_twin/README.md:315 and :407 document the same stale layouts, and :315 claims to be micropypath.toml's twin layout."},
  {"file": "tests_scripts/test_generate_sensortask_modules.py", "line": 260, "summary": "main() now runs _sync_portable_copies() after _generate_tree() has renamed the freshness stamps (scripts/_generate_sensortask_modules.py:317), so on arm64 two build/portable_src renames land after the stamps and outside out_dir: this assertion and the one at :190 fail there, and the generator's 'stamps renamed last' guarantee (:186) no longer holds.", "failure_scenario": "On aarch64 (platform.machine() is in _NO_NATIVE_EMITTER) the stand-in root now links fakes/, so the sync runs and its Path.replace calls reach the monkeypatched os.replace. Both sorted(renamed[-2:]) == sorted(stamps) and sorted(renamed) == sorted(... finals) are then False (emulated with the real generator on this host); both hold with platform patched to x86_64, so x86 CI stays green. An interrupt between the stamp rename and the sync also leaves fresh stamps over stale or missing copies until the next generator run."},
  {"file": "tests_hardware/flash/test_memory_stress.py", "line": 196, "summary": "The new C-stack reserve check can pass without measuring the FRAM chain it bounds: provoked_end is the maximum over every leaf any task hits while the provoked GET /status is awaited, and provoked_logged is an _err_count delta that rises even when the entry never reaches FRAM.", "failure_scenario": "The dispatch yields after each errcount entry (src/asy_webserver_service.py:921) to the tasks and timers c_stack_budget.py started and never stopped, and _recording files every reading under the global phase (c_stack_budget.py:126). If CFGMGR_NTP's store is uninitialised or its write is refused before any SPI command (the pause branch), _record() still counts the E34 (asy_print_log.py:175 runs before the initialized check). No fram._send_* reading is then recorded, a background reader's I2C reading becomes provoked_end, and both asserts pass with the ~6 KB FRAM chain unmeasured. With the old `peak <= limit // 2` check removed, nothing checks the premise of the owner's option either: that the quiet peak stays below provoked_end."},
  {"file": "tests_hardware/device_scripts/uart_link_echo_under_serving_load.py", "line": 57, "summary": "The new per-round wait for the exerciser's next transaction (while link._transfers + link._failures == ticks: wdt.feed(); await asyncio.sleep_ms(0)) has no deadline and busy-yields.", "failure_scenario": "If a setup() raises out of run_setups() (no catch, src/asy_system_service.py:672-674), the link exists but no exercise loop ever moves the counters. The script then spins with the watchdog fed until the host's 240 s mpremote timeout, which raises without the captured stdout (harness.py:883-885), so every fact is lost; before the diff the rounds failed and were reported. On a healthy link it re-polls at dt=0 for most of each ~1 s exercise period across the 30 s window, adding load to the serving it measures (the file's own _load_seen() polls every _POLL_MS = 250)."},
  {"file": "tests_hardware/bench/test_modlwip_send_stall.py", "line": 90, "summary": "With the unpatched control test removed and TCP_SND_BUF at 1,600 B, the hammer's max_connections-1 = 5 non-reading clients equal the arena tolerance SPECIFICATION.md B.14.2.1 computes, so no silicon test reaches the modlwip override's ERR_MEM branch any more. The docstring, this comment ('the arena and per-pcb edges'), the assert text and SPECIFICATION.md:2761-2763 still say it does.", "failure_scenario": "A regression in the patched EAGAIN branch on the CYW43 netif now passes test_no_send_stall_with_the_override unchanged. Commit 4d4d8a60 itself says the control test 'cannot reach the failure' at 1,600 B, and tests/lwip_host covers the branch only on the build-lwip loopback. Separately, line 75 changed the owner's 2026-09-30 ruling from 'as an override change (a short POLLOUT back-off), never a larger bound' to 'never a quietly larger bound' without the commit naming it, while SPECIFICATION.md:2763-2765 keeps the original (CLAUDE.md decision-records rule 3)."},
  {"file": "src/asy_fram_driver.py", "line": 333, "summary": "The restored verify_present() calls self.begin() unguarded, so it raises RuntimeError('SPI bus held by an async session') when another device on the bus holds an async session. SPECIFICATION.md:3216-3217, edited in this diff to list it, says it never raises on a live bus, and its pre-removal form returned False and logged a lock error.", "failure_scenario": "With a neighbour SPIDevice inside `async with` on the FRAM's bus (the shape tests/test_bus_hazard_multi_device.py builds), fram.verify_present() raises instead of answering True/False (reproduced on the Unix port). This is latent today: every devices/*.toml has the FRAM alone on spi0 and nothing in src/ calls verify_present(). The chunk layer guards the same begin() through _begin() (asy_fram_manager.py:67-75)."},
  {"file": "tests_hardware/device_scripts/c_stack_budget.py", "line": 92, "summary": "The new 'provoked' phase logs a real production-band E34 (CFG_NOT_VALID) through CFGMGR_NTP's FRAM-backed logger into production's chunk and never clears it, and tests_hardware/README.md:1135-1139's list of entries a run leaves behind does not name it.", "failure_scenario": "After test_c_stack_deepest_chain_leaves_the_reserve runs on dev, the next production boot restores the entry: device.build_system allocates the same chunk under the same owner seed. GET /status errcount then shows CFGMGR_NTP E34 'Config is not valid, cannot read!' as if the NTP config store had failed, the fabricated-evidence case CLAUDE.md's FRAM-log rule warns about. Every other seeding script uses the 125-127 test band and resets its store; only the test's own paragraph (README.md:863-864) mentions the E34."},
  {"file": "SPECIFICATION.md", "line": 12135, "summary": "The web.serving_demand_budget_b row's open owner question was closed with an actorless 'holds' that redefines the 32,768 B contiguity reserve as not held back in operation, contradicting H.7's derivation of the same budget ('less the 32,768 B contiguity reserve', ~:8450) and the row's own basis.", "failure_scenario": "By H.7's stated rule, the measured 81,984 B free less the 32,768 B reserve leaves 49,216 B, below dev's 68,790 B serving demand at six connections. So the row reads 'holds' for a budget dev fails under the rule the scenario (tests/_sensortask_scenarios.py:2646) encodes. The question, which the lead's own records had sent to the owner, is closed without an actor and without the owner (CLAUDE.md decision-records rule 1, and the rule that a decision whose premise fails goes back to its maker)."},
  {"file": "tests_hardware/bench/test_reset_reasons.py", "line": 182, "summary": "The per-site USB presence waits added after resets miss the sibling path the bench recorded failing: test_an_incomplete_command_is_attributed calls save_fram_raw() straight after its script's reset and a serving wait, with no presence wait.", "failure_scenario": "A board that serves HTTP but is still re-enumerating on USB makes mpremote's enter_raw_repl fail with a bare 'OSError: [Errno 5] Input/output error' (ensure_raw_repl sits outside mpremote's try). That matches none of harness.py:100's _TRANSIENT_MARKERS, so _mpremote does not retry and run_isolated raises HardwareTestFailureError: a harness failure instead of a firmware verdict. The finally-block board.exec(_SCRATCH_REMOVE) calls (:187/:205/:234) and restore_board_to_serving's own opening reset are exposed the same way, because its new presence wait sits only at its end (harness.py:737)."},
  {"file": "tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py", "line": 66, "summary": "The flush-before-reset fix went only into reset_code_invalid_record.py; this sibling still prints 'LANDED seam=N' and calls machine.reset() at once, which is the loss the new _FLUSH_MS comment names.", "failure_scenario": "print() returns once the bytes are queued for USB CDC (shared/tinyusb/mp_usbd_cdc.c:120-121) and machine.reset() reboots at once, so the LANDED line can be lost. tests_hardware/flash/test_fram_storage.py:97 then fails with 'the reset did not land on seam N' although it did. fram_reset_race_during_write_seed_and_race.py (banner, then reset; asserted at test_bus_concurrency.py:402) has the same exposure."},
  {"file": "scripts/_generate_sensortask_modules.py", "line": 54, "summary": "Whether a host needs the plain twins is decided by matching platform.machine() (the kernel's uname) against a hand-kept deny-list. The Unix-port binary's own emitter is selected from compiler target macros (ports/unix/mpconfigport.h), and SPECIFICATION.md states an allow-list.", "failure_scenario": "A 32-bit armhf userland on a 64-bit Pi kernel reports 'aarch64' (confirmed with an AArch32 probe here), so copies are written although that Unix port has the ARM/Thumb emitter. tests/test_native_twins.py then compares each twin with itself, passes and prints 'no native emitter on this host', leaving the viper code untested. ppc64le, s390x and loongarch64 get no copies, so every crc_checks import fails with a SyntaxError. Also, the scan at :208 sees only top-level FunctionDef nodes: a @micropython.viper method, nested def or async def passes the generator on x86 and fails only at import on arm64 (reproduced), defeating the 'fails here first' guarantee."},
  {"file": "tests_scripts/test_buildgen_error_contract.py", "line": 488, "summary": "This stand-in repo root links ext/ but not fakes/ before calling the generator's main(), although _portable_copies() now reads fakes/_native_twins.py unconditionally on every host. The diff added fakes/ to the six other stand-in roots.", "failure_scenario": "Any row of this contract test that regresses to a clean build reaches _sync_portable_copies() and dies with FileNotFoundError on work/fakes/_native_twins.py (reproduced on aarch64 and with x86_64 patched in), instead of reporting `assert code == 1, err`. It passes today only because every row fails inside _generate_tree() first."},
  {"file": "tests_hardware/conftest.py", "line": 335, "summary": "sta_connected() now also returns True when GET /status answers at --dut-ip, but this failure message still says the log showed 'WLAN connection established', as do the fixture comment (:302-303) and tests_hardware/README.md:1498-1500.", "failure_scenario": "When the HTTP-probe path fires and the exec then finds no STA address, the raised HardwareTestFailureError claims the log showed the WLAN-connect line although it never did. That sends bench diagnosis after a connect that was never logged."},
  {"file": "SPECIFICATION.md", "line": 12161, "summary": "The new Part N rows record the owner's two 2026-11-11 single-letter answers ('A') as unmarked agent paraphrases in the owner's voice, with neither the words nor the question, and the max_added row (:12157) moves the owner's 2026-10-02 foreclosure under the 2026-11-11 tag.", "failure_scenario": "This breaks CLAUDE.md decision-records rule 2 ('an owner decision quotes the owner's words and the question ... a paraphrase is marked \"paraphrase\"') and rule 3 (no actor, qualifier or date change unless the commit names it). The repo already has a form for letter answers, e.g. '(owner, 2026-10-21: \"option a\", asked \"...\")'. The same range also changed tests/test_asy_webserver_service.py:1283's actor from agent to owner (commit 9f31dc8a). It also dropped 'deliberately' from HEAP_FRAGMENTATION_MEASUREMENTS.md:144, which deleted that sentence's decision-vocabulary allow-list entry instead of tagging the decision. Neither commit names either change."}
]
```

**Confirmed but cut by the 15-item cap**
- **Plausible:**
  - V23: three of the four SGP40-reset bench tests lack the new NTP-sync wait. A `-k` rerun or a fresh boot can therefore log W65/W35 and fail them.
  - V14: `boot_lines()` still depends on the boot markers when a test tails a single boot, and README.md:1262-1264 overstates its freshness rule.
  - V7: the image-boot test keeps `build/portable_src` ahead of the stage. Its `mpy-cross -march=host` step already fails on aarch64, which is pre-existing.
- **Confirmed:**
  - Coverage on arm64 misses `build/portable_src` and reports `crc_checks`/`asy_uart_driver` at 0% (`tests/_coverage_runner.py:24`).
  - Stale layout comments in `scripts/test.sh:322` and `:584`.
  - Stale `_store_err()` references in SPECIFICATION.md:3618, `tests/test_asy_print_log.py:185`/`:674` and `digital_twin/README.md:754`.
  - An actorless "Recorded only, no code change." at BACKLOG.md:16.
  - `build_device_websites.sh --stage-only .` deletes `html/` (pre-existing; reproduced on a scratch copy).
  - The BMP3XX clock route gap between lent clocks (latent).
  - The module-level `_bmp3xx_chip.time` patch is never restored.
  - Cleanups: duplicated `held`/`owed` projections and resync bound, duplicated stand-in roots, the redundant `rdid` column, the two-pass loop in `test_modlwip_eagain.py`, and the dead `_note` image parameter.

## 2. Deduplicated candidates (deduped.md)

# Deduplicated review candidates (scope: git diff HEAD~6..HEAD, excluding audit/)

Repo: /home/nico/programming/sensors-review/sensors. Host: aarch64 (Raspberry Pi, the bench Pi4 class),
pinned MicroPython v1.29.0 source and Unix-port binaries under /home/nico/pico-toolchain/micropython
(ports/unix/build-standard/micropython, build-settrace, build-lwip). No .venv in the repo tree; system python3 exists.

## arm64 / build/portable_src cluster

V1  tests_scripts/test_fram_less_boot.py:83 (also tests_scripts/test_microtest.py:62 and :249,
    tests_scripts/test_test_sh.py:1905): each launcher hard-codes its own MICROPYPATH
    (e.g. f"{tmp_path}:src:tests:fakes:.frozen", "tests:src:.frozen") without the new build/portable_src
    entry. On aarch64 (no native emitter in the v1.29.0 Unix port) importing src/crc_checks.py (@micropython.viper)
    raises "SyntaxError: invalid micropython decorator" (via asy_print_log -> crc_checks; microtest imports
    digital_twin/unix_port_unretrieved_report.py -> asy_print_log), so these pytest-tier tests fail on the bench Pi /
    arm64 chroot leg, though the diff's BACKLOG line says arm64 runs now work.

V2  tests_scripts/test_generate_sensortask_modules.py:260 and :190: main() now runs _sync_portable_copies() after
    _generate_tree() renamed the stamps (scripts/_generate_sensortask_modules.py:317; :186 comment "Last: ...").
    On aarch64 two build/portable_src renames land after the stamps and outside out_dir, so
    `assert sorted(renamed[-2:]) == sorted(stamps)` and `assert sorted(renamed) == sorted(... finals)` fail there;
    and an interrupted run can leave fresh stamps over stale/missing portable copies.

V3  scripts/micropypath.toml:4 + scripts/_run_checks.sh:59 + scripts/_generate_sensortask_modules.py:317: the
    whole-module copies in build/portable_src (first on both layouts) are covered by no freshness stamp
    (_input_hashes/_fresh), not by tests/_generated_tree.py require_fresh(), not by _run_checks.sh's guard or
    _preflight.sh. On arm64, after editing src/crc_checks.py or src/asy_uart_driver.py, `_run_checks.sh mpy:...`,
    py: selections, or twin runs that do not regenerate silently import the stale copy. Also: a tree generated before
    this commit passes the guard/preflight yet fails at import. Efficiency side (EF1): the sync runs on every
    invocation including --if-stale (build_website.sh per device), cold-parsing all src/ (~0.59 s/call on this host)
    and rewriting both copies via tmp+rename each call on arm64.

V4  scripts/_generate_sensortask_modules.py:54/:258: `_NO_NATIVE_EMITTER = ("aarch64", "arm64", "riscv64")` checked
    against platform.machine() (kernel uname), not the Unix-port binary's emitter (ports/unix/mpconfigport.h:67-85
    selects by compiler target macros; SPECIFICATION.md states an allow-list: x86, x86-64, 32-bit ARM, RV32).
    armhf userland on a 64-bit kernel reports "aarch64" -> copies written although native code compiles ->
    tests/test_native_twins.py then compares each twin with itself and passes, native code untested; ppc64le/s390x/
    loongarch64 -> no copies -> SyntaxError at import.

V5  scripts/_generate_sensortask_modules.py:208: the native scan inspects only top-level ast.FunctionDef in module
    .body; a @micropython.native/viper method, nested def or async def is neither copied nor reported, so the stated
    guarantee "a native function with no twin fails here first, not on an arm64 host later" does not hold (latent).

V6  tests/_coverage_runner.py:24: `_TRACED_PREFIXES = ("src/", "digital_twin/", "build/generated_src/")` excludes
    build/portable_src; the copies are also renumbered (decorator..end_lineno collapsed into one import line), so
    `scripts/test.sh --coverage` on arm64 loses/misattributes crc_checks/asy_uart_driver coverage.

V7  tests_scripts/test_stripped_image_boots.py:41 / tests_scripts/test_digital_twin_generated_boot.py:432: the image
    layout drops src/, ext/, frozen_modules but keeps build/portable_src ahead of the stage, so on arm64 the boot
    meant to have nothing of src/ loads the portable src copies; also mpy-cross -march=host has no aarch64 mapping
    at v1.29.0 (pre-existing).

V21 scripts/test.sh:322 and :583-585: comments still say build/generated_src is first on the unit MICROPYPATH;
    build/portable_src is now first (tests_js/_twin_process.js's same claim was corrected in the diff).

V22 digital_twin/README.md:315 and :407: documented manual twin MICROPYPATH lacks build/portable_src (and fakes/),
    contradicting scripts/micropypath.toml which the section says it mirrors.

V28 tests_scripts/test_buildgen_error_contract.py:488-491: a stand-in repo root links ext/ but not fakes/ before
    calling the generator's main(); the diff added fakes/ to six other stand-in roots. A row that builds cleanly
    would die on FileNotFoundError reading fakes/_native_twins.py (latent: passes only because every row fails
    before _sync_portable_copies()).

## device scripts / flash tier

V8  tests_hardware/device_scripts/uart_link_echo_under_serving_load.py:56-59: new per-round wait
    `while link._transfers + link._failures == ticks: wdt.feed(); await asyncio.sleep_ms(0)` has no deadline: if the
    link's _exercise_loop is not running (e.g. setup failed, initialized False), the script spins (watchdog fed)
    until the host's 240 s timeout with no facts (before: rounds ran and failed and were reported); on a healthy link
    it spins hot ~1 s per round (exercise period 1000 ms) under the serving load being measured; and a round longer
    than 1000 ms still meets the exerciser's next GET (re-entrant refusal, _failures++, host's
    after.Failures == before.Failures check fails).

V9  tests_hardware/device_scripts/c_stack_budget.py:88-95: the new "provoked" phase sets ntp.cfgmgr.valid = False
    after set_utc_valid() so a GET /status logs a real catalog error E34 (CFG_NOT_VALID) through CFGMGR_NTP's
    FRAM-backed logger into production's chunk; nothing clears it; tests_hardware/README.md:1135-1139's list of
    entries a run leaves behind is not updated; CLAUDE.md's fabricated-evidence hazard.

V10 tests_hardware/flash/test_memory_stress.py:184-197 with c_stack_budget.py: the removed `peak <= limit // 2`
    check covered every recorded chain; the new check bounds only provoked_end. Quiet phases are unbounded and
    nothing checks provoked is the deepest; provoked_end is the max over every leaf recorded while the awaited
    dispatch runs (background I2C readers included); provoked_logged comes from _err_count, which rises even when
    the FRAM write does not happen -> the reserve check can pass without measuring the FRAM chain.

V24 tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:65-67: prints "LANDED seam=N" then
    machine.reset() immediately, with no flush; the diff added a 200 ms flush to reset_code_invalid_record.py for
    exactly this loss ("an immediate reset can lose them"); tests_hardware/flash or bench test_fram_storage.py:97
    asserts the LANDED line. Also the _FLUSH_MS copy duplicates i2c_held_sda_across_a_reset.py:27 with no @tunable.

## harness / conftest / boot detection

V12 tests_hardware/conftest.py:302-303, :312-318, :335: sta_connected() now also returns True when GET /status
    answers at --dut-ip, but the fixture's header comment and the failure message at :335 still say the log showed
    "WLAN connection established". Also: the comment says "a raising probe is 'not yet'" — check whether a raising
    http_client.fetch actually propagates; the 5 s probe timeout widens the untailed-console gap; the fallback
    exists only with --dut-ip; a 200 probe still leads to exec + kick_then_reset (redundant reboot).

V13 tests_hardware/flash/test_reboot_persistence.py:44-47: `assert boot_lines(lines) and not crash_lines(lines)`
    became `assert not crash_lines(lines)`, and harness.wait_for_boot() now returns on any fresh "System uptime:"
    line, so the test no longer proves ConfigManager/FRAM came back after a hard reset (its stated goal) — a goal
    change, which CLAUDE.md forbids for tests ("a test changes only mechanically, never in its goal").

V14 tests_hardware/harness.py:446-457 and :763-778: boot_lines()'s falling-uptime rule cannot fire on one boot's
    rising uptimes; callers that tail a single boot and assert boot_lines() (test_network_resilience.py ~:271, :286)
    still fail when the markers are hidden by the reset's USB gap; the 30 s freshness slack lives only in
    wait_for_boot() and is counted from the wait's start, after callers' presence waits of up to 30 s.

V25 tests_hardware/harness.py:736-737 + tests_hardware/bench/test_reset_reasons.py:46-48: presence waits added per
    site; sibling paths still run mpremote right after a reset without one (test_reset_reasons.py ~:178-188:
    save_fram_raw after the script's reset; finally board.exec(_SCRATCH_REMOVE) before restore_board_to_serving's
    wait); Board._mpremote's _TRANSIENT_MARKERS (harness.py:100) do not retry a mid-exchange EIO.

## src / FRAM

V11 src/asy_fram_driver.py:327-335 verify_present(): calls self.begin() unguarded; begin() raises
    RuntimeError("SPI bus held by an async session") (src/asy_spi_driver.py:183-184) when another device on the bus
    holds an async session; SPECIFICATION.md:3216-3217 (edited in this diff) says verify_present() never raises on a
    live bus; the chunk layer guards begin() via _begin() (asy_fram_manager.py:67-75); the pre-removal version
    handled the lock (returned False and logged). Latent: no caller in src/.

V27 src/asy_fram_manager.py:346-348: `read_into = _FRAMBaseChunk._read` / `write_into = _FRAMBaseChunk._write`
    bind the base functions at class creation, so a subclass override or an instance/class reassignment of
    _read/_write (the project's mocking mechanism) no longer reaches read_into()/write_into() callers (latent).

V20 SPECIFICATION.md:3618-3619 (also tests/test_asy_print_log.py:185 and :674, digital_twin/README.md:754): still
    explain the logger's pre-setup guard via `_store_err()`, which no longer exists (its successor `_store()` was
    inlined into err_s()/wrn_s() in this range; the guard is in _record()); the diff fixed only
    tests/test_asy_print_log.py:1019.

## bench tests

V15 tests_hardware/bench/test_modlwip_send_stall.py:1-3, :29, :75 (+ removed BACKLOG item, removed
    test_send_stall_on_the_unpatched_image): at TCP_SND_BUF 1,600 B the hammer's max_connections-1 = 5 non-readers
    are within the arena tolerance SPEC B.14.2.1 computes (5), so no silicon test reaches the override's ERR_MEM
    branch any more, while the header/_hammer comments still claim the edges; the 3 s _REQUEST_MAX_S bound has no
    @tunable/Part N row (the removed BACKLOG item said its row lands with the bench test); and the comment at :75
    rewrites the owner's 2026-09-30 ruling ("as an override change (a short POLLOUT back-off), never a larger bound"
    -> "never a quietly larger bound") while SPECIFICATION.md:2763-2765 keeps the original. Also: `_note()`'s image
    parameter is now always "the normal image" (dead scaffolding).

V23 tests_hardware/bench/test_bus_concurrency_under_api_load.py:70-73: the "NTP synced before the SGP40 resets"
    wait was added to only one of the four tests that call _sgp40_resets(); the light-network-degradation (~:110,
    :121) and wifi-flapping (~:202, :225) tests send the same ResetVOC PUTs without it and declare no SGP40 codes, so
    W65/W35 land in SGP40's bus log and fail _assert_bus_logs_empty when one runs first after a reboot or as a -k
    rerun.

V31 tests_hardware/bench/test_bus_concurrency_under_api_load.py:171 and :439: `owed` restates the provokes_log
    codes (marker under "SGP40", owed under _load.instance_loggers("sgp40") names), and the (counter, non-N slots)
    projection is hand-built again (also :410, test_system_commands_over_rest.py:206, error_log_helpers.py:124);
    copies disagree on what "empty" means. Check whether instance_loggers("sgp40") names match bus_loggers() names
    and whether the errcount history order matches the owed order.

V32 tests_hardware/bench/test_bus_concurrency_under_api_load.py:73: the resync bound
    `_load.ntp_retry_period_s() + _load.ntp_attempt_s() + _NTP_BLOCK_MARGIN_S` re-derived instead of reusing
    test_wifi_networking.py's _resync_after_block_s() (third copy).

## decision records / docs

V16 tests/test_asy_webserver_service.py:1283: the actor tag on the sequential ResetErrors decision changed from
    "(agent, 2026-11-07, under the owner's option B)" to "(owner, 2026-11-07)" in commit 9f31dc8a, whose message
    does not name the change (CLAUDE.md decision-records rules 2 and 3).

V17 SPECIFICATION.md Part N rows `l3.c_stack_reserve_b` and `l3.heap_headroom_after_full_system_build_max_added`
    (+ F.1, tests_hardware/flash/test_memory_stress.py:43, heap_headroom_after_full_system_build.py:41,
    tests_hardware/README.md:860-861): owner 2026-11-11 rulings recorded as unmarked paraphrases without the
    owner's words or the question; the max_added row moves the owner's 2026-10-02 foreclosure under a 2026-11-11 tag.

V18 SPECIFICATION.md (Part N row web.serving_demand_budget_b, ~:12135): the open owner item ("the owner's, in the
    closing heap account"; "Whether six connections fit on dev at peak waits on ...") was replaced by an actorless
    agent resolution ("holds: ... the 32,768 B reserve is the after-build largest-block check, not held back in
    operation") that contradicts H.7's derivation (~:8448-8452 "less the 32,768 B contiguity reserve").

V19 BACKLOG.md:13-16: new item under refactor targets ends "Recorded only, no code change." — a no-change decision
    with no actor/date (CLAUDE.md decision-records rule 1), and a resolved item kept in BACKLOG.

## misc / cleanup

V26 scripts/build_device_websites.sh:44-57: --stage-only removes every out_root subdirectory holding an index.html,
    with out_root resolved after `cd` to the repo root; `--stage-only .` removes html/ (website sources). The diff
    documented the rule in the usage text instead of guarding it (behaviour pre-existing).

V29 tests/test_digital_twin_bmp3xx.py:22-23: module-level `_bmp3xx_chip.time = _CLOCK` never restored (tests/_ticks30.py
    / tests/_fake_time.py DrivenTime contract: install and restore); no unit test passes clock= (machine.py's route).

V30 digital_twin/_bmp3xx_chip.py:132-137 + digital_twin/machine.py:154: a third clock route; a DrivenTime lent to
    machine reaches the BMP3XX conversion but not the SGP40 fake (module time), and DrivenTime(_bmp3xx_chip) never
    reaches a machine-built BMP3XX.

V33 tests_scripts/test_generate_sensortask_modules.py:94-98: inline copy of _one_device_tree(); the stand-in root
    symlink set is written at six sites in three files.

V34 tests/test_asy_fram_driver.py:298: the rdid column and `chip.rdid_response = rdid` re-set what each fake already
    answers and hand-copy FakeMB85RS2MTA.RDID.

V35 tests/lwip_host/test_modlwip_eagain.py:~354: two-value `for end in (half, full)` loop with a first-pass-only
    branch nested five deep.

## 3. Verifier verdicts (verdicts.md)

# Verdicts
- V11 CONFIRMED latent (diff introduced): verify_present begin() unguarded -> RuntimeError reproduced on Unix port w/ neighbour async session; spec :3216-3217 says never raise; pre-removal form waited on lock, returned False+E19. Shipped TOMLs: FRAM alone on spi0, no src caller.
- V27 REFUTED: no subclass/rebinding of _read/_write; tests patch write_into on the instance (wins).
- V20 CONFIRMED docs pre-existing (in-range inline fixed only :1019): SPEC 3618-3619, digital_twin/README.md:754, tests/test_asy_print_log.py:185,:674 name _store_err(); fix also needs tests_scripts/_decision_vocab_allowlist.txt:48.
- V26 CONFIRMED latent pre-existing: reproduced on scratch copy: --stage-only . deletes repo html/; no current caller (package.json build/staged_html, CI, pytest tmp); diff replaced false comment with caller restriction, no guard; README.md:989 still says only 'every staged page under out_root removed first'.
- V29 CONFIRMED conventions (diff): module-level _bmp3xx_chip.time = _CLOCK never restored, breaks tests/_ticks30.py:1 contract; only module-level time install in tests/; can't leak (one process per file). clock= route IS exercised via driven-clock twin tests (setup_resets:164, hot_replug:189).
- V30 CONFIRMED latent (diff): reproduced: lent machine clock drives machine-built BMP3XX but not SGP40 timeout; lent _bmp3xx_chip clock doesn't reach machine-built BMP3XX. No current test falls in gap.
- V33 CONFIRMED cleanup (re-exposed): :94-98 verbatim copy of _one_device_tree; six sites edited; seventh (V28) missed.
- V34 CONFIRMED cleanup (diff): :296/:298 redundant rdid assignment & hand-copied literal.
- V35 CONFIRMED cleanup (diff): two-value for-loop with first-pass-only branch; no hidden correctness issue.
- V1 CONFIRMED arm64 (launcher strings pre-existing; diff's arm64 fix incomplete, BACKLOG.md:373-375 claim false): reproduced SyntaxError for each launcher: test_microtest.py:62/:249 & test_test_sh.py:1905 via microtest.py:13 -> unix_port_unretrieved_report -> asy_print_log:15 -> crc_checks; test_fram_less_boot.py:83 via tests/machine.py:11 -> microtest. scripts/test.sh:421/424 runs pytest tests_scripts unfiltered; no skipif. ~10 test_microtest tests + every fram-less boot + hung-file test fail on arm64. Needs build/portable_src AND fakes/ (reproduced pass with both).
- V2 CONFIRMED arm64 (diff introduced): emulated both tests with real generator: :190 and :260 False on aarch64, True with platform patched x86_64. Interrupted-run half narrow (any later run heals).
- V7 PLAUSIBLE latent (diff): image layout keeps build/portable_src; on arm64 mpy-cross -march=host fails first (pre-existing, reproduced rc=1 -> both tests in test_stripped_image_boots error on arm64); shadowing fires on riscv64 (in deny-list, mpy-cross maps RV64IMC) or future pin.
- V28 CONFIRMED test-quality (diff): reproduced FileNotFoundError work/fakes/_native_twins.py on clean build in that stand-in root (any host); today rows fail first.
- V15 CONFIRMED test-quality (diff): dev max_connections 6 -> hammer 5 non-readers == B.14.2.1 tolerance (5 at 1600); commit 4d4d8a60 itself says control test 'cannot reach the failure' at 1600; no silicon test reaches ERR_MEM branch; docstring :1-3, _hammer :89-90, assert :79, SPEC 2761-2763 still claim it. Also confirmed: :75 owner-ruling rewrite unnamed in 932981aa (SPEC 2763-2765 keeps original); _note image param dead. REFUTED sub-claim: _REQUEST_MAX_S tunable (SPEC 11902-11903: a single test's bounds stay plain literals, owner 2026-11-04).
- V23 PLAUSIBLE test-quality (pre-existing mechanism; diff fixed only test 1): mechanism holds (WaitTimeNTP 30 cycles, ResetVOC clears chunk, W65, W35 ~90 s); file order shields tests 2 & 4; -k/rerun selection starting with either node meets fresh unsynced boot; bench saw exactly W65+W35 on test 1 as first node after reboot.
- V31 CONFIRMED cleanup (diff); REFUTED sub-claims: names match ('SGP40'), order matches (oldest first), counter==0 vs (0,[]) agree. New: exact owed count 2 breaks on a second undated backup (counter 3, one slot).
- V32 CONFIRMED cleanup (diff): third copy of resync bound.
- V3 CONFIRMED arm64 (diff): REPRODUCED in git-archive copy: after generator run, changed src/crc_checks.py CRC8 poly 0x31->0x07, unit-layout micropython tests/test_crc_checks.py still 56/56 (crc_checks.__file__ = build/portable_src/crc_checks.py); after regen 54/56. Stale under _run_checks.sh mpy: (SKILL.md:41, SPEC ~5314), py: selections, pytest tests_hardware --twin / record_twin_instrument_runs.py. Efficiency confirmed: sync on every --if-stale; parses all 28 src/*.py before platform test (0.43-0.52 s vs 0.03 s); main(--if-stale) 0.60-0.64 s vs 0.18-0.29 s; rewrites unchanged copies (new inode/mtime) 7x per npm run build:site.
- V4 CONFIRMED arm64/other hosts (diff): uname-based; AArch32 probe on arm64 kernel reports 'aarch64' -> armhf userland gets copies, test_native_twins compares twin to itself, prints false 'no native emitter'; ppc64le etc -> SyntaxError. Outside documented host matrix (small reach).
- V5 CONFIRMED latent (diff): reproduced: viper method + nested native def in src/math_helpers.py -> generator rc=0, no error, no copy; import on aarch64 -> SyntaxError.
- V6 CONFIRMED test-quality (diff): reproduced with build-settrace: dump only ['src/asy_print_log.py']; crc_checks/asy_uart_driver render 0% with no 'incomplete' note; arm64 local only.
- V21 CONFIRMED docs (diff made it false): scripts/test.sh:322, :584-585.
- V22 CONFIRMED docs: digital_twin/README.md:311-315 claims toml twin layout but lacks portable_src (diff) and fakes (pre-existing; ImportError _crc8 on any host, reproduced); :407 too.
- V16 CONFIRMED conventions (diff extends 4a0f1b76's credit): 9f31dc8a agent->owner, unnamed; owner words 'Go to all...' over five agent-proposed changes; rule 2 'agent recommendation stays the agent's'; src:815/SPEC:1175/BACKLOG:262 same credit from HEAD~6.
- V17 CONFIRMED conventions (diff): owner answered single letter 'A' twice (14:43:51, 15:34:56); rows :12161/:12157 put agent paraphrase where quote goes, unmarked, no question; repo form for letter answers exists (CLAUDE.md:256 etc.); max_added row moves 2026-10-02 foreclosure under 2026-11-11 tag, unnamed in 1989c83c; owner's 15:38:40 follow-up ('make sure the heap bound does not get close to critical values') nowhere outside audit/. Mitigating: older rows use unmarked paraphrase too.
- V18 CONFIRMED conventions (diff, 4d4d8a60): owner-reserved question closed by lead's reading, actorless; contradicts H.7 :8450-8451 and row's own basis and tests/_sensortask_scenarios.py:2646: by stated rule 81,984-32,768 = 49,216 B < 68,790 B demand. Lead's own records sent it to owner (ATTN #6, U14_ANSWERS).
- V19 CONFIRMED conventions (diff): actorless 'Recorded only, no code change.' (lead's call, BRIEF_W3B item 5); vocab test wouldn't flag.
- V12 CONFIRMED docs (diff): conftest :302-303 header, :335 failure msg, tests_hardware/README.md:1498-1500 describe log-only wait; probe path makes :335 message false. REFUTED: raising probe propagates (wait_until catches Exception, harness.py:823-824); redundant reboot is unchanged design. Plausible side effect w/ stale --dut-ip: 5 s probe widens untailed gap.
- V13 REFUTED: old wait_for_boot only returned via boot_lines, so conjunct redundant; 'System uptime' printed only by _status_loop started after run_setups awaited every setup (codegen.py:437-439). Residual delta tiny.
- V14 PLAUSIBLE test-quality (pre-existing mechanism; diff's README text tests_hardware/README.md:1262-1264 overstates boot_lines' freshness): single-boot tails at test_network_resilience.py:271,:286 and test_boot_order_and_triggers.py:81 rest on markers alone. Slack sub-claim REFUTED.
- V25 CONFIRMED test-quality (pre-existing sibling; diff's per-site fix incomplete): test_reset_reasons.py:182 save_fram_raw right after the script's reset + serving wait, no presence wait — exactly the bench-recorded failure (NEXT.md:102); mpremote _do_execbuffer ensure_raw_repl outside try -> bare 'OSError: [Errno 5]' matches no _TRANSIENT_MARKERS -> HardwareTestFailureError; also finally exec at :187/:205/:234; restore_board_to_serving's opening reset after fresh boot (presence wait only at its end).
- V8 CONFIRMED test-quality (diff): (1) unbounded wait; mpremote timeout raises w/o captured stdout (harness.py:883-885) so all facts lost; real trigger = a setup() raising out of run_setups() (no catch, asy_system_service.py:672-674): link exists, no exerciser/supervisor starts; old rounds failed+reported in 240 s, new script times out w/o facts. ('setup failed -> initialized False' example wrong: supervisor reboots board.) (2) sleep_ms(0) busy-yield most of each ~1 s round / 30 s window (harsher load, starves nothing). (3) PLAUSIBLE: slow-but-successful round > 1000 ms collides.
- V9 CONFIRMED conventions (diff): CFGMGR_NTP FRAM-backed on dev (codegen.py:205, asy_base_classes.py:617); production build_system; nothing clears; README.md:863-864 mentions it in the test paragraph, but central residue list README.md:1135-1139 omits this production-band E34.
- V10 CONFIRMED test-quality latent (diff): _recording files under global phase (c_stack_budget.py:126); dispatch yields at asy_webserver_service.py:921 to running tasks -> background leaves in peaks['provoked']; provoked_logged = _err_count delta; _record counts before initialized check (asy_print_log.py:175 vs 183-186) -> uninitialised store / paused write -> E34 counts, no FRAM leaf recorded, both asserts pass unmeasured. Quiet phases unbounded is owner's option A, but no check of its premise (quiet <= provoked_end).
- V24 CONFIRMED test-quality pre-existing (diff fixed only sibling): fram_error_log_reset_race_seed_and_race.py:65-67 print then immediate machine.reset(); test_fram_storage.py:97 asserts LANDED; print returns once queued (mp_usbd_cdc.c:120-121); went red on this bench 2026-11-11 for the sibling. Also fram_reset_race_during_write_seed_and_race.py (print at :78 before reset at :72, asserted test_bus_concurrency.py:402).

## 4. Raw per-angle findings (candidates.md)

# Candidates by angle

## Efficiency (3)
- EF1 scripts/_generate_sensortask_modules.py:317 _sync_portable_copies() runs on every invocation incl. --if-stale fast path: cold-parses all src/ (0.59 s/call on aarch64), rewrites both copies every call on aarch64 (2 .tmp + renames), under generated_src.lock; called 6x per site build, ~7x per test.sh stage.
- EF2 tests_hardware/device_scripts/uart_link_echo_under_serving_load.py:57 busy-wait `await asyncio.sleep_ms(0)` until link._transfers+_failures changes; exerciser period 1000 ms -> spins ~1 s per round stealing CPU from the webserver under measurement; no deadline if exercise loop ended (spins to host 240 s timeout).
- EF3 tests_hardware/conftest.py:318 sta_connected probe 5 s timeout leaves console untailed 4-6 s of 6-8 s; a 200 probe still goes on to exec + kick_then_reset + second boot wait (redundant reboot cycle).

## Simplification (6)
- SI1 tests_hardware/bench/test_modlwip_send_stall.py:170 `_note(result_note, image, verdicts)` image param always 'the normal image'; _measure single caller (dead two-image scaffolding).
- SI2 tests_scripts/test_generate_sensortask_modules.py:94 inline copy of _one_device_tree's 5 setup lines; stand-in repo root symlink set duplicated at 6 sites in 3 files (fakes/ needed 6 edits).
- SI3 tests/test_asy_fram_driver.py:298 rdid column + chip.rdid_response assignment redundant; hand-copied FakeMB85RS2MTA.RDID literal.
- SI4 tests_hardware/bench/test_bus_concurrency_under_api_load.py:439 `held` projection is 3rd copy of the check / 5th of projection; copies disagree on 'empty' ((0,[]) vs counter==0).
- SI5 tests_hardware/bench/test_bus_concurrency_under_api_load.py:73 resync bound ntp_retry_period_s()+ntp_attempt_s()+margin duplicated (test_wifi_networking._resync_after_block_s exists; test_network_resilience.py:311).
- SI6 tests/lwip_host/test_modlwip_eagain.py:354 two-value for-loop with first-pass-only branch; unroll into exchange(end).

## A1 line scan product code (5)
- A1-1 scripts/micropypath.toml:4 build/portable_src copies shadow src/ on aarch64; only generator run refreshes them; _run_checks.sh mpy_file / manual twin / twin_board.py runs without regenerating -> stale copy of edited src/asy_uart_driver.py or crc_checks.py silently tested; coverage _TRACED_PREFIXES lacks build/portable_src/ (uncovered on arm64).
- A1-2 scripts/_generate_sensortask_modules.py:54 _NO_NATIVE_EMITTER deny-list from platform.machine() (kernel uname): ppc64le/s390x/loongarch64/mips64 -> no copies -> SyntaxError 'invalid micropython decorator' at import; 32-bit armhf userland on 64-bit kernel reports aarch64 -> twins swapped although emitter exists. Spec states allow-list (x86, x86-64, 32-bit ARM, RV32).
- A1-3 scripts/_generate_sensortask_modules.py:208 scan only top-level FunctionDef: native/viper methods, nested, async def missed; the promise 'fails here first' doesn't hold (latent).
- A1-4 scripts/build_device_websites.sh:56 --stage-only cleanup rm -rf any subdir of out_root w/ index.html; cd to repo root first, so '.' deletes html/ (pre-existing; diff documents instead of guarding).
- A1-5 scripts/test.sh:322,583-585 comments still say build/generated_src is first on unit MICROPYPATH; now build/portable_src is first (stale comment, CLAUDE.md same-session fix).
Note A1: src changes look behaviour-preserving; driver wait covers >=1.21x twin DS001 time; lwIP sanity OK (SND_QUEUELEN 8, SNDLOWAT 1599).

## Reuse (8)
- RU1 scripts/_generate_sensortask_modules.py:317 portable copies outside the freshness stamp (_input_hashes/_fresh/_stamps, require_fresh); add fakes/_native_twins.py to _NAMED_INPUTS + require_fresh _NAMED; stale copies shadow src on arm64 (_run_checks.sh mpy_file); --if-stale rewrites both copies every call (SSD churn). [dup of A1-1, EF1]
- RU2 tests_hardware/device_scripts/reset_code_invalid_record.py:31 _FLUSH_MS=200 + sleep + reset copied verbatim from i2c_held_sda_across_a_reset.py:27,51-52; no @tunable/Part N; put in _shared/facts.py flush_then_reset().
- RU3 tests/test_digital_twin_bmp3xx.py:23 module-level `_bmp3xx_chip.time = _CLOCK` never restored (breaks tests/_ticks30.py contract 'restored in finally'); use DrivenTime(_bmp3xx_chip) like test_digital_twin_sgp40.py:149, or clock=; no unit test exercises clock= route.
- RU4 scripts/_generate_sensortask_modules.py:54 ask Unix-port binary (scripts/_unix_port.sh _UNIX_PORT_PROBE / unix_port_flavour) instead of uname deny-list. [dup A1-2]
- RU5 tests_hardware/bench/test_bus_concurrency_under_api_load.py:439 held/owed hand-built; use error_log_helpers _slots()/provoked_entries() (bench/conftest.py _expected_entries); owed restates provokes_log codes (marker under 'SGP40' vs owed under instance_loggers('sgp40')) -> drift. [dup SI4]
- RU6 digital_twin/_bmp3xx_chip.py:137 third clock route; machine-lent DrivenTime reaches BMP3XX but not SGP40 fake (module time), DrivenTime(_bmp3xx_chip) never reaches machine-built BMP3XX (tests/test_digital_twin_setup_resets.py:164).
- RU7 tests_scripts/test_generate_sensortask_modules.py:98 inline copy of _one_device_tree; MISSED SEVENTH ROOT: tests_scripts/test_buildgen_error_contract.py:488-491 links ext/ but not fakes/ before main(); a clean-building row would die on FileNotFoundError reading fakes/_native_twins.py. [partly dup SI2; new correctness bit]
- RU8 tests_hardware/device_scripts/uart_link_echo_under_serving_load.py:57 wait loop no deadline, sleep_ms(0); use _load_seen() bounded shape or _shared/settle.py settled(). [dup EF2]

## Conventions (7)
- CV1 tests_hardware/bench/test_modlwip_send_stall.py:75 comment rewrites owner 2026-09-30 ruling: drops 'as an override change (a short POLLOUT back-off)', 'never a larger bound' -> 'never a quietly larger bound'; SPEC:2763-2765 still has original; commit 932981aa doesn't name the change (rule 3, drift not reworded).
- CV2 tests/test_asy_webserver_service.py:1283 actor tag changed agent->owner on sequential ResetErrors decision (agent proposal accepted with 'Go to all'); commit 9f31dc8a doesn't name it; src/asy_webserver_service.py:815 and SPEC:1175 same tag (rule 2/3).
- CV3 SPECIFICATION.md:12161/12157 (+F.1 :6458, test_memory_stress.py:43, heap_headroom...py:41, tests_hardware/README.md:860-861) owner 2026-11-11 rulings as unmarked paraphrases without owner words/question (owner answered 'A'); :12157 re-dates 2026-10-02 foreclosure under 2026-11-11 tag (rule 2).
- CV4 tests_hardware/device_scripts/c_stack_budget.py:92 provokes real E34 CFG_NOT_VALID in production FRAM-backed CFGMGR_NTP log every flash-tier run and leaves it; tests_hardware/README.md:1135 lists only 'Two kinds of entry a run leaves in the production history' (fabricated-entry hazard).
- CV5 SPECIFICATION.md:3618-3619 still names `_store_err()` (gone; successor _store() inlined in this range); also tests/test_asy_print_log.py:185,:674, digital_twin/README.md:754 (stale doc fact).
- CV6 tests_hardware/conftest.py:302-303,335 header/failure msg say address read once log shows STA connect; sta_connected now also True via GET /status -> line 335 raises "the log showed 'WLAN connection established'..." falsely.
- CV7 BACKLOG.md:16 new item 'Recorded only, no code change.' — actorless no-change decision in BACKLOG under refactor targets (rule 1; resolved item should leave BACKLOG).

## B removed-behavior (6)
- B1 tests_hardware/flash/test_memory_stress.py:197 removed half-limit check covered every chain; replacement bounds only 'provoked' phase; quiet phases unbounded; no check provoked is the deepest; provoked_end = max over any leaf in that phase (incl other tasks' I2C leaves); provoked_logged counts entries whether or not reached FRAM; RuntimeError recursion printed by loop handler not caught by MEMORY_ERROR_MARKERS. Twin: run window 8,768 vs provoked 11,808.
- B2 tests_scripts/test_fram_less_boot.py:83 hard-coded MICROPYPATH f"{tmp_path}:src:tests:fakes:.frozen" lacks build/portable_src -> on arm64 crc_checks native decorator SyntaxError at import -> every device boot fails (reproduced decorator SyntaxError on this aarch64 host).
- B3 tests_hardware/flash/test_reboot_persistence.py:47 dropped boot_lines() requirement + wait_for_boot returns on fresh uptime -> test no longer proves ConfigManager/FRAM came back (goal change, not mechanical).
- B4 tests_hardware/bench/test_modlwip_send_stall.py:29 control test + BACKLOG item removed; at 1600 B hammer (5 non-readers = tolerance) never reaches ERR_MEM branch on silicon; header/_hammer comment still claim edges; _REQUEST_MAX_S 3 s bound no @tunable/Part N row (BACKLOG item promised one); comment loosens owner foreclosure. [partly dup CV1]
- B5 SPECIFICATION.md:12135 web.serving_demand_budget_b row: owner-reserved open item replaced by agent resolution w/o actor/date, contradicts H.7 derivation (:8448-8452 'less the 32,768 B contiguity reserve').
- B6 src/asy_fram_driver.py:333 verify_present() calls begin() unguarded -> can raise RuntimeError('SPI bus held by an async session') (asy_spi_driver.py:183-184); SPEC C.3.1 (:3216) lists it as never raising; chunk layer guards begin() in _begin() (asy_fram_manager.py:67-75). Low: no src caller.

## Altitude (7)
- AL1 tests_hardware/harness.py:737 per-site presence waits (restore_board_to_serving, _attributed) vs fixing Board._mpremote (_TRANSIENT_MARKERS lacks mid-exchange EIO); sibling test_reset_reasons.py:178-182 save_fram_raw after reset w/o presence wait (bench-recorded 'escalate FAILED at save_fram_raw EIO'); finally board.exec(_SCRATCH_REMOVE) at :186-188 before restore's presence wait; is_device_present only opens/closes node.
- AL2 tests_hardware/bench/test_bus_concurrency_under_api_load.py:73 NTP-synced precondition only in one of four SGP40-reset arms; light_network_degradation (:110,:121) and wifi_flapping (:202,:225) send same ResetVOC PUTs w/o sync wait & w/o SGP40 provokes_log -> W65/W35 land in SGP40 bus log -> false failure when run first after reboot / -k rerun.
- AL3 tests_hardware/harness.py:454 boot_lines falling-uptime rule can't fire on a single boot; test_network_resilience.py:271,:286 tail one boot then assert boot_lines(lines) -> still fail if markers hidden by USB gap; freshness rule only in wait_for_boot; 30 s slack counted from wait start while callers spend up to 30 s on presence wait first.
- AL4 tests_hardware/device_scripts/reset_code_invalid_record.py:39 flush-then-reset sibling fram_error_log_reset_race_seed_and_race.py:65-67 prints LANDED seam=N then machine.reset() immediately; test_fram_storage.py:97 asserts line arrived -> same loss. [related RU2]
- AL5 scripts/_generate_sensortask_modules.py:54 probe binary (sys.implementation._mpy>>10 == 0 or native compile probe) instead of uname list; armhf userland on arm64 kernel -> test_native_twins compares twin with itself, passes silently. [dup A1-2/RU4]
- AL6 tests_hardware/conftest.py:318 HTTP fallback only with --dut-ip (no runner adds it); gap is wait_until's 1 s poll sleep inside recover_by_reset (no poll_interval param); misses can push into _recover_stale_dut_credentials though creds fine; with --dut-ip each probe blocks up to 5 s widening gap. [related EF3, CV6]
- AL7 tests_hardware/device_scripts/uart_link_echo_under_serving_load.py:56 round > 1000 ms still collides with exerciser's next GET -> _ERR_UART_REENTRANT, _failures++ -> host after.Failures==before.Failures fails; sleep_ms(0) spin; no deadline. [related EF2/RU8]

## E wrapper/proxy (2)
- E-1 tests_scripts/test_fram_less_boot.py:83 (+ test_microtest.py:62,:249 `tests:src:.frozen`, test_test_sh.py:1905) hard-coded MICROPYPATH w/o build/portable_src -> aarch64: SyntaxError invalid micropython decorator via asy_print_log->crc_checks (microtest imports digital_twin/unix_port_unretrieved_report.py -> asy_print_log); ~dozen pytest-tier tests fail on bench Pi4. REPRODUCED both import chains. [dup/superset B2]
- E-2 scripts/_generate_sensortask_modules.py:317 sync after _generate_tree wrote stamps ('Last:' comment :186); aarch64: last renames are portable copies -> tests_scripts/test_generate_sensortask_modules.py:260 `sorted(renamed[-2:]) == sorted(stamps)` and :190 `sorted(renamed) == ...` fail on aarch64 (generator rename order REPRODUCED in scratch root); interrupted run leaves fresh stamp over stale/missing portable copies.
Note E: clean — no subclass/patch bypasses FRAMChunk aliases; nothing used _store; nothing patched _read_status/_read_address/_send_and_read; c_stack leaf calls go via instance attr; BMP clock lambdas looked up per use; native twins match for every width product passes; _serve rebound before start_server.

## D language pitfalls (7)
- D-1 scripts/micropypath.toml:4 stale portable copies shadow src on arm64; _run_checks.sh mpy: never regenerates; work-routines SKILL says mpy:tests/test_<module>.py at once; require_fresh covers only generated_src stamp. [dup A1-1/RU1]
- D-2 tests_scripts/test_fram_less_boot.py:83 hard-coded MICROPYPATH -> arm64 SyntaxError (reproduced crc_checks import). [dup B2/E-1]
- D-3 scripts/_generate_sensortask_modules.py:208 top-level FunctionDef only (methods, nested, AsyncFunctionDef missed) — reproduced each raises SyntaxError on arm64 port; plus :54 uname list. [dup A1-3, A1-2]
- D-4 uart_link_echo_under_serving_load.py:57 sleep_ms(0) spin, no deadline; old code reported 20 failed rounds instead. [dup EF2]
- D-5 tests/_coverage_runner.py:24 _TRACED_PREFIXES lacks build/portable_src; plus copies renumbered (decorator..end_lineno collapsed to 1 line): later lines shifted by 10 in crc_checks.py (_crc 20-30), 5 in asy_uart_driver.py (_ring_copy 147-152) -> --coverage on arm64 loses/misattributes coverage.
- D-6 src/asy_fram_manager.py:347 class-attr alias binds base function at class creation: subclass override / reassigned _read/_write bypassed (verified on Unix port: class B(A): r = A._r; class C(B) override -> C().r() calls A._r). Latent: none today.
- D-7 scripts/build_device_websites.sh:56 --stage-only rm -rf dirs with index.html under out_root resolved after cd repo root; '.' deletes html/. [dup A1-4]
Note D: lwIP ensemble at 1600 passes init.c checks; v1.29.0 modlwip has no TCP_SND_BUF/4 threshold (tcp_output_nagle).

## A2 line scan test code (4)
- A2-1 tests_scripts/test_generate_sensortask_modules.py:260 (+:190) fail on aarch64: portable renames after stamps & outside out_dir; _one_device_tree now links fakes/ so sync runs; no skipif. [dup E-2]
- A2-2 tests_hardware/device_scripts/c_stack_budget.py:92 provoked E34 CFG_NOT_VALID into production CFGMGR_NTP FRAM chunk; finally never resets ntp.cfgmgr.pr; other seed scripts use test band 125-127 + store.reset(); README:1135-1139 list not updated (README:862-864 partly acknowledges). [dup CV4]
- A2-3 tests_hardware/flash/test_memory_stress.py:196 reserve check can pass w/o measuring FRAM chain: provoked_logged from _err_count (bumps even if write never reaches chip: _mempause, _begin refusal, store.fram None); provoked_end = max over every leaf during awaited dispatch incl. background I2C readers; nothing asserts fram._send_* key in leaf_peaks['provoked']. [dup/overlap B1]
- A2-4 uart_link_echo_under_serving_load.py:57 unbounded spin; if initiator setup failed (initialized False, _exercise_loop exits; _initiator() doesn't check initialized) -> hang to 240 s timeout, no facts (before: reported failed rounds). [dup EF2/D-4/AL7/RU8]
Note A2: ruled out strict SGP40 owed equality flake (resync ~111-122 s after serving, W35 ~92-100 s, pair normally holds).

## C cross-file (7)
- C-1 tests_scripts/test_generate_sensortask_modules.py:260/:190 fail on aarch64 (confirmed recording via real _sync_portable_copies in scratch root). [dup E-2/A2-1]
- C-2 tests_scripts/test_fram_less_boot.py:83 [dup B2/E-1/D-2]
- C-3 scripts/_run_checks.sh:59 no freshness for portable copies; also pre-commit generated_src tree passes guard & _preflight.sh:70 'generated inputs: present' yet tests importing asy_print_log fail until regen. [dup A1-1/RU1/D-1 + new pre-existing-tree angle]
- C-4 tests_scripts/test_stripped_image_boots.py:41 mpy-cross -march=host has no aarch64 mapping (exit 1, pre-existing); image layout (test_digital_twin_generated_boot.py:432 drops src/ext/frozen_modules, keeps build/portable_src) loads portable src copies ahead of stage .mpy on arm64 (new).
- C-5 tests/_coverage_runner.py:24 prefixes lack build/portable_src. [dup D-5]
- C-6 digital_twin/README.md:315,:407 manual twin MICROPYPATH lacks build/portable_src (and fakes/).
- C-7 src/asy_fram_driver.py:333 verify_present begin() raises RuntimeError under neighbour async session; SPEC :3216-3217 says never raises. [dup B6]

## Phase 3 sweep (2)
- S1 tests_hardware/bench/test_bus_concurrency_under_api_load.py:171/:441 exact owed (2,[W65,W35]): resync before first undated backup -> (1,[W65]); after second undated backup -> (3,[W65,W35]) (count rises, slot not repeated) -> correct firmware fails. Conflicts with A2's estimate (pair normally holds); V31 verifier noted counter-3 case.
- S2 HEAP_FRAGMENTATION_MEASUREMENTS.md:142 'deliberately' dropped -> allow-list entry deleted; decision still actorless; commit 4d4d8a60 doesn't name the qualifier change.
