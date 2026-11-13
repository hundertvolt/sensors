# BUILD: the build chain (buildgen/, toolchain/, devices/*.toml, pyproject.toml, package.json, .github/, build-side scripts/)

## Verdict
Mostly yes. The owner-approved pieces are in place and in their decided form: the apt cache and mirror check (owner
2026-10-27), the frozen REST API reference ("ok" review tick), the errcount catalog (owner 2026-10-28), the tick-offset
test image (owner 2026-10-01), the modlwip patches, the tunables register (owner 2026-11-04 (a)) and the decision-record
gates (owner 2026-09-26). No file in scope still refers to the removed audit/ folder or to PROJECT_AUDIT_PLAN.md, and a
non-dev build carries no uart_link trace.

Drift leftovers are still there, though. CI's test caps are still the M8 figure (175 min). Test machinery sits inside the
build chain: a fixture namespace filtered in six build scripts, a gc gate grown over the tests, test-only helpers in
buildgen.validate, and a twin-record writer whose record is gone. buildgen has 24 typing-only guards (M4). None of these
is a product gap, and each fix is a deletion or a move.

## Shape since the baseline
- **buildgen: 3,681 to about 5,800 lines.**
  - New: api_reference.py (owner tick), error_catalog.json (owner), signals.py (moved out of codegen; the catalog is
    agent 2026-09-09, before the baseline), source_ast.py (a shared parse cache) and jsontypes.py.
  - validate.py grew about 1,000 lines: datasheet pin and peripheral role checks, I2C and UART bus bounds, eight UART-link
    checks, narrowing helpers, and test-facing helpers.
  - codegen.py was rewritten: settings groups as a table, collectors, typed globals, isort-ordered imports.
- **toolchain: 1,689 to 3,017 lines.**
  - U21 (2026-10-08) added installer machinery: bounded, streamed and retried run(), a lock, a build record and signal
    handling.
  - New overrides: modlwip_eagain (three patches), unix_lwip_host, tick_offset_test, unix_gc_stack and the Unix qstr
    length.
- **CI: the job count is unchanged (27 against 27).**
  - web-coverage was folded into web-unit-tests. The device matrices now come from the `devices` job: four hardware
    families, and the twin runs once per GC stage.
  - Four composite actions and ci_apt_cache.py were added for the owner-approved apt fix.
  - Every timeout carries an `@tunable` tag. unit-tests went from 45 to 175 min, gc-threshold from 45 to 175 and
    coverage from 45 to 95.
- **Scripts in scope.**
  - The generator grew from 57 to 332 lines: the expected-facts oracle, freshness stamps, aarch64 portable copies (owner
    2026-11-12) and the API reference.
  - New: the gc-site checker (368 lines), the evidence archive (owner, keep 3), the twin-record writer, preflight and tidy
    (owner skill, 2026-11-06), and website staging and bundling.

## Findings

### BUILD-1 [L] [VERIFIED] A test-fixture namespace (`devices/zz_test_*.toml`) leaks into the product's devices/ and is filtered throughout the build chain
- **Where:**
  - The filters: scripts/_devices.sh:16; scripts/_generate_sensortask_modules.py:166-168;
    scripts/_check_gc_collect_sites.py:250,268; scripts/build_device_websites.sh:2,18; scripts/cross_browser_smoke.mjs:86.
  - The sweep and its ordering constraint: scripts/test.sh:212.
  - Copies of the filter on the test side: tests/_generated_tree.py:49,68; tests_hardware/harness.py:437;
    tests_js/_generated_definitions.js:46.
  - The rule itself: SPECIFICATION.md:4952-4968.
- **What:** two tests_scripts tests write throwaway TOMLs into the live `devices/`:
  - test_test_sh.py:330 (a nested-run sentinel);
  - test_build_device_websites_sh.py:64. This one exists to prove that the build skips such a fixture, so it is itself a
    product of the cascade.

  Because of them, every device-discovering build script re-implements the reserved-prefix filter, test.sh sweeps the
  prefix and orders steps around the backgrounded tier, and conftest reclaims leftovers. It is a cascade: a test need
  that entered the product's own input directory, and then the protections around it. The namespace was already in
  test.sh at the baseline. The build-chain filters came in U6 (1b59a05d) and U27 (15b8633c).
- **Ruling/pillar it meets:** OR36 "zero artifacts specifically added for testing"; DRIFT 2.9 (cascades); P8.
- **Decision record:** none found. The rule at SPECIFICATION.md:4958 is agent text, and the owner rulings say nothing on
  `zz_test`.
- **Smallest fix:** give those two tests the sandbox-copy approach test_build_website_sh.py already uses. Then delete the
  prefix filters, the sweep, its ordering constraint, the conftest reclaim, and the skip-case test.

### BUILD-2 [R] [VERIFIED] CI's unit-test caps are still the 45 to 175-minute growth: an agent budget rule multiplied by a Pi4-sized scenario bound
- **Where:**
  - .github/workflows/ci.yml:377-385 (unit-tests, 175), :411 (gc-threshold, 175), :426-436 (coverage, 95);
    scripts/test.sh:464-465 (`runner.scenarios_timeout_s = 2555`).
  - The baseline: ci.yml at 25caf528, :430/:461/:484, all 45.
  - The rule: SPECIFICATION.md:1886-1891 (B.10.1).
- **What:**
  - A warm unit-tests run takes 9-10 min (Part N row `ci.unit_tests_timeout_min`).
  - The cap must hold "a warm run plus one hung scenario job's full retry budget". B.10.1 requires this so that "the
    summary block [is] printed" before CI cancels, and it is agent text with no owner attribution.
  - That budget is 2,555 s × 3 attempts, about 128 min. 2,555 s is 2.5× the bench Pi4's time but 4.5× CI's own 563 s
    (Part N `runner.scenarios_timeout_s`).
  - So one hung scenario holds two CI jobs for about 3 h each. GitHub Actions is out of minutes until 2026-12-01 (owner,
    2026-11-13).
- **Ruling/pillar it meets:**
  - PICTURE M8: "CI went from 45 to 175 minutes, against OR39"; OR39 "speeding up".
  - 2026-11-11: no runaway chains; fix the root.
- **Decision record:**
  - Owner 2026-09-26 and 2026-10-20: a per-file timeout with retries as the backstop. This is kept.
  - Owner 2026-11-04: CI values stay in the register.
  - No owner words on the "full retry budget plus summary" sizing.
- **Smallest fix (owner must decide the values):** size CI's per-attempt scenario bound on CI's own measurement, for
  example an env override set in ci.yml beside test.sh's existing PER_FILE_TIMEOUT_S, or drop the "full retry budget
  fits" clause. Either way both caps return to about 45-70 min.

### BUILD-3 [L] [VERIFIED] A twin-record writer and the rule to commit its record survive, but the record does not
- **Where:**
  - scripts/record_twin_instrument_runs.py (230 lines), tests_scripts/test_record_twin_instrument_runs.py (101), and
    pyproject.toml:300-308.
  - tests_hardware/README.md:588, whose row ends "Then commit the record | review (the committed record returns on the
    final tree)".
  - BACKLOG.md:102,160, which cite "its twin record".
- **What:** tests_hardware/twin_record.json was deleted on 2026-11-02 (c901f111: "the runner stays and records once more
  on the final tree"). That last run never happened, and the release carries no record. What is left is audit evidence
  machinery with a dangling rule and dangling citations. `pytest --twin` (tests_hardware/conftest.py:395) does not need
  the writer.
- **Ruling/pillar it meets:** 2026-10-28 "The audit verification machinery is just a temporary tool"; OR48.a "no list or
  permanent record".
- **Decision record:** the R0 go-ahead (owner, 2026-11-02) covered the plan that kept the writer for one more run. There
  is no standing owner decision on the record itself.
- **Smallest fix (owner must decide):** delete the writer, its test, the pyproject ignores, the README row and the BACKLOG
  mentions, and keep `--twin`. Or run it once and commit the record.

### BUILD-4 [L] [VERIFIED] The gc-site gate grew from a 10-line src/buildgen grep into a 757-line AST gate over the test tiers
- **Where:**
  - scripts/_check_gc_collect_sites.py (368 lines; ALLOWED has 40 rows, every one a tests/, digital_twin/ or
    tests_hardware/ site), tests_scripts/test_gc_collect_sites.py (389) and scripts/lint.sh:92-95.
  - The baseline lint.sh:35-48: src/ and buildgen/ only, with "digital_twin/ and tests/ are out of scope there, per
    I.4(e)".
- **What:**
  - Since 512bb0dc (2026-11-10), the product half needs nothing but "none in src/ or a generated module, one threshold
    per boot entry". SPECIFICATION.md:874 says "no collect between them".
  - The growth is an allow-list of named test functions (U27, 15b8633c): the "expanding rule became a machine gate"
    pattern, applied to the tests.
- **Ruling/pillar it meets:**
  - DRIFT 2.2 and 2.7.
  - 2026-10-28: the unit tests "don't need deep dives".
  - 2026-11-11: "don't drift into fixing tests".
- **Decision record:**
  - Owner 2026-09-18 approved the boot-confined reset and its src-side confinement, at the baseline's scope.
  - No owner words extend the gate to the tests.
- **Smallest fix:** go back to the product-scope check (src/, generated modules, boot entries), drop the test allow-list
  and the pinning test's test-scope cases, and leave test-side gc use to review under CLAUDE.md's memory rule.

### BUILD-5 [L] [VERIFIED] Test-only helpers live in buildgen.validate, the product generator
- **Where:**
  - buildgen/validate.py:113-114 (`HardConsumer`, a one-field NamedTuple) and :1332-1344 (`smallest_hard_consumer`).
  - buildgen/validate.py:1281-1285 (`device_max_connections_by_name`).
  - buildgen/validate.py:1094-1102 and :1163-1170 (`_declares_config_store`/`_owns_config_store`).
- **What:**
  - None of these has a build caller. `smallest_hard_consumer` (agent, 2026-10-21) is read only by
    scripts/_digital_twin_scenarios.py:1268, the flash and bench memory-stress tests, and a test that greps the other
    readers to make sure they do not compute it themselves.
  - `device_max_connections_by_name` is read only by the twin CI suite and tests_hardware/harness.py.
  - `_owns_config_store` is read only by the test generator's `expected_facts()` oracle
    (_generate_sensortask_modules.py:116). buildgen's own definitions use the hand catalog's bool instead.
- **Ruling/pillar it meets:** OR36; P4; L5 ("extra machinery in a module is a cost carried by every future module").
- **Decision record:** none found; the attribution reads "(agent, 2026-10-21)".
- **Smallest fix:** move the three helpers beside their consumers (the shared test-side import), and return an int
  instead of the one-field NamedTuple.

### BUILD-6 [L] [VERIFIED] Typing-only guards in buildgen: 24 internal-invariant raises where the baseline had none, and two shapes for one job
- **Where:**
  - `BuildInternalError(` raise sites: codegen.py ×9 (e.g. :115, :213, :390, :548, :658, :663, :724, :771),
    validate.py ×8 (:310, :367, :457, :639, :1067, :1082, :1089, :1108), definitions.py ×4 (:476, :528, :539, :543),
    api_reference.py:54,61 and tag_comments.py:317.
  - twin_wiring.py:114-117 is an explicit "Unreachable for today's driver set" branch.
  - Against those, codegen.py:790-797 narrows the same TOML values with `cast` (`_table`/`_text`).
- **What:**
  - Each site re-checks a fact that an earlier pass or the typing already guarantees:
    - `driver_info` and `resolved_name` resolved;
    - a TOML value already validated;
    - a crc mode already checked by validate.py:860.
  - validate.py narrows by raising (`_checked_int`/`_checked_str`), while codegen narrows the same values by cast.
  - These came in U20 (f76385a6, 2026-10-08).
- **Ruling/pillar it meets:**
  - PICTURE M4.
  - 2026-10-27: catching errors "which can only happen for the reason of unfulfilled typing are overkill".
  - "One shape per job".
- **Decision record:** none found.
- **Smallest fix:** one shape. Use `cast` (codegen's `_table`/`_text`), or one resolved-instance accessor that raises
  once. Then delete the per-site raises and the twin_wiring unreachable branch.

### BUILD-7 [E] [VERIFIED] The apt mirror check's step-bound plumbing never decides, because the floor always wins
- **Where:**
  - .github/workflows/ci.yml:574-598. A heredoc regex-reads ci.yml's own `@tunable ci.firmware_build_verify_timeout_min`
    comment (:588) to pass `bound-s`/`bound-from`.
  - .github/actions/apt-cache-restore/action.yml:27-34 and :114-121.
  - scripts/ci_apt_cache.py:40-41 and :222-236 (`Rule.bound_s/bound_from/margin`), plus :455.
- **What:** required = max(floor 1 MB/s, 2 × to_fetch / 1200 s). The whole firmware set is 588 MB, which needs 0.98 MB/s,
  under the floor. Part N's own row for `ci.apt_mirror_min_bytes_per_s` says so. The only caller passing a bound
  therefore always gets the floor, and Playwright passes none. So the self-parse, the two inputs, the margin and its
  register row buy nothing today.
- **Ruling/pillar it meets:** 11-07 and 11-09 ("could the same outcome be implemented leaner"); L2 (no mechanism for an
  unobserved trigger).
- **Decision record:** the owner approved the probe plus cache (2026-10-27, "Yes do it like you proposed", brief CI1).
  The bound-derived rate is agent sizing (agent, 2026-10-28).
- **Smallest fix:** drop `bound-s`/`bound-from`, the ci.yml self-parse, `Rule.bound_s/margin` and the
  `ci.apt_mirror_rate_margin` row and tag. The floor alone decides, as it already does.

### BUILD-8 [R] [SUSPECTED] Hazard-run and link specifics are hand-written in buildgen and build_firmware, not carried by the uart_link module
- **Where:**
  - buildgen/definitions.py:749-762 (`_uart_section`: the "UART Hazard Run" section, its labels, description and the
    `/uart` paths), :806 and :820-823 (`uart_initiator_name`).
  - buildgen/codegen.py:226-235 (the `get_hazard_report` maintenance entry and `add_routes`).
  - buildgen/model.py:28 (`MAINTENANCE_NAMES = {"uart_link": "UARTLINK"}`).
  - scripts/build_firmware.py:142 and :237-239 (`uartCrc` in every image record).
- **What:** the owner wrote (2026-11-06, 09:08): "all hazard code goes into that module ... If it is selected, in brings
  in everything it needs, the only switch for that being its inclusion in the toml file." The generated-output half
  holds: non-dev builds carry nothing. The first half does not: the hazard section's text and its wiring are buildgen
  special cases. SPECIFICATION.md:1151-1157 records only the agent's reading.
- **Ruling/pillar it meets:** the owner ruling of 2026-11-06; P10.
- **Decision record:** the owner ruling of 2026-11-06 (quoted above). Then "The rest of the Q3 topics stay as they are
  (A)", which covers the other topics, not this one.
- **Smallest fix (owner must decide whether buildgen-resident text counts as "hazard code"):** let the module carry its
  section through the existing `@web`/`@web-group` tags, or through module constants read by AST as `_HAZARDS_KEY`
  already is.

### BUILD-9 [L] [VERIFIED] A build check compares only src constants, guarding a state no TOML can reach
- **Where:** buildgen/validate.py:974-982, the max-timeout half of `_check_uart_link_timing`.
- **What:**
  - `timeout` is `_DEFAULT_TIMEOUT_MS` (1000 ms), and horizon, num, den and mult are src constants too. So the check is
    1000 > 89,478,485 ms, and no device TOML takes part.
  - It can only fire on an src edit. That case is already refused at runtime by `asy_uart_comm._max_timeout()`
    (src/asy_uart_comm.py:566-568, :922), the module's own library-level check.
- **Ruling/pillar it meets:** L2; 2026-10-28 "building upon hypothetical findings is a clear no-go".
- **Decision record:** none found. The neighbouring check is the owner's "config mismatch out of runtime scope"
  (2026-09-24), which concerns TOML values.
- **Smallest fix:** delete these 9 lines, and the three constants read only for them.

### BUILD-10 [L] [VERIFIED] Hand copies of src facts, where buildgen elsewhere reads src by AST
- **Where:**
  - buildgen/buildspec.py:77 (`UART_CRC_MODES`, a hand copy of crc_checks' class names and widths). It is kept equal by
    tests_scripts/test_buildgen_validate.py:1861-1865, which AST-parses crc_checks itself.
  - devices/dev.toml:50-54 and :62-66 (`poll_wait_ms = 2`, `poll_idle_ms = 50`, `rx_ring = 512`) and :168, :178
    (`max_transfer_bytes = 12192`). All of these equal the src defaults (src/asy_uart_driver.py:173-177;
    `_DEFAULT_MAX_TRANSFER_BYTES`).
  - devices/dev.toml:43 justifies them with "stated so the build checks read them here".
- **What:** the justification is wrong. `_uart_bus_value` (validate.py:1214-1218), validate.py:914 and
  codegen.py:181 and :559 all fall back to the src defaults, so the generated code is the same without these lines.
  The copies can only drift.
- **Ruling/pillar it meets:** P8 "one source of truth, generated not copied".
- **Decision record:** none found. The `rx_ring` reason (J.6) is agent text.
- **Smallest fix:**
  - Read the widths with the existing AST helpers and drop the copy and its sync test.
  - Delete the eight restated lines and the wrong comment from dev.toml.

### BUILD-11 [E] [VERIFIED] Three copies of the atomic write, and two CLIs that generate one TOML's module
- **Where:**
  - The atomic writes: buildgen/generate.py:34-50 (`_write_outputs`), scripts/_generate_sensortask_modules.py:277-292
    (`_write_through_rename`) and scripts/build_firmware.py:224-228 (`_replace_written`).
  - The two CLIs: buildgen/generate.py:67-90 (`main --out-dir`) and _generate_sensortask_modules.py's
    `--device-toml --out-dir` (:145-156).
- **What:** at the baseline both CLIs used plain `write_text`. Each later gained its own tmp-and-rename with cleanup. The
  second single-TOML mode duplicates the first, and the first is used only by tests and by the SPEC's new-driver
  checklist (SPECIFICATION.md:10261, :10476).
- **Ruling/pillar it meets:** "One shape per job"; 11-09 micro and macro leanness.
- **Decision record:** none found.
- **Smallest fix:** one write helper, shared by the three. Whether buildgen.generate's CLI stays is a feature question:
  owner must decide.

### BUILD-12 [E] [SUSPECTED] The installer's process-control machinery is sized for parallel agent lanes, with no observed trigger on record
- **Where:**
  - toolchain/setup_toolchain.py: :410-530 (`_raise_terminated`, `_refuse_held_lock`, `_signals_held`,
    `_stop_commands_on_termination`, `_stream_output`) and :1774-1830 (`toolchain_lock`, the exclusive/shared flock with
    pid naming).
  - scripts/_unix_port.sh's shared hold.
  - SPECIFICATION.md:1517-1529 and :1584-1597.
- **What:** U21 (65088dec, 2026-10-08) added several mechanisms:
  - signals deferred while a command starts;
  - SIGTERM and SIGHUP turned into an exit;
  - a session per command;
  - a two-mode lock that names its holder.

  B.4 and B.5 cite no failure they answered. The concurrency they serve is the audit's many parallel lanes on one
  toolchain dir (PICTURE M9).
- **Ruling/pillar it meets:** L2 (a mechanism needs an observed trigger); M9; 11-07 proportionality.
- **Decision record:** none found.
- **Smallest fix (owner must decide):** keep the bounded and retried network steps, which answer the observed apt
  stalls. Then reduce the rest to one exclusive lock, or check whether any of it answers a recorded failure first.

## Checked and clean
- buildgen pipeline shape (model to validate, graph, codegen, frozen closure): unchanged. Its hand tables (buildspec, and
  the errcount catalog in definitions) are owner-approved (2026-09-18).
- No reference in scope to the removed audit/ folder, PROJECT_AUDIT_PLAN.md, unit or round labels, or snapshots.
- api_reference.py and its frozen-at-release fixtures match the owner's review tick "rest-api-frozen-at-release: ok".
- error_catalog.json and the errcount codes on the device page match owner 2026-10-28 (decisions 4 and 6).
- tick_offset_test image and `TestOverrides` in build info: owner 2026-10-01. Release builds refuse it (B.14.5).
- micropython_overrides: kbd_intr (pre-baseline), lwip ensemble, modlwip_eagain (owner 2026-09-30, 2026-10-26) and
  unix_lwip_host (owner 2026-09-30) all have owner-backed reasons.
- apt cache, mirror probe and playwright action: owner-approved design (2026-10-27). Only its bound plumbing is surplus
  (BUILD-7).
- CI job set: 27 jobs, as at the baseline. web-coverage was merged away. The device matrices come from `hardware_family`
  per owner 2026-10-23 (matrix dedup).
- Each job's `needs` and `if: !cancelled()` match CLAUDE.md. The uv-sync retry is decided.
- devices/*.toml: `hardware_family` and `bench` fit OR78 and the 10-23 dedup ruling. Nothing board-specific is hardcoded
  outside the TOMLs in the build scripts.
- pyproject.toml: every path named in the ruff and mypy config exists. The tools are pinned. disallow_any_explicit follows
  the owner's (A) of 2026-11-10.
- typecheck.sh stub repairs, the method-assign guard and zizmor config: standing CLAUDE.md rules.
- _archive_evidence.py (keep 3, owner 2026-09-26). _preflight.sh and _tidy.sh are the owner-requested skills
  (2026-11-06).
- The decision-vocabulary and citation gates in CI are the owner's five prevention rules (2026-09-26, "4. yes").

## Notes
- CLAUDE.md still describes the boot-confined `gc.collect()` reset as live and confined by lint.sh. src/ has had none
  since 512bb0dc (2026-11-10), and SPECIFICATION.md:874 says "no collect between them". The docs look stale (a decided
  item, not raised).
- CLAUDE.md says the lint scope is "eight directories". lint.sh and pyproject name nine: fakes/ joined.
- scripts/_generate_sensortask_modules.py's `expected_facts()` restates codegen's setup and FRAM-wiring rules as an
  independent oracle. That is by design (SPECIFICATION.md:10806-10809, "the test generator's").
- graph.py:64-65 hardcodes sgp40/notification to ntp, matching codegen's per-driver build-args. A new driver that takes
  ntp edits both (the pre-baseline shape; P10).
- micropython_overrides.py:157 attributes the listen-alloc patch to "(agent, 2026-10-26)", while SPECIFICATION.md B.14.4
  says "(owner, 2026-10-26)".
- The mbedtls GCC 14 workaround still says "not yet re-checked on a GCC >= 14 host", although the trixie leg (GCC 14.2)
  ran on 2026-11-12.
- buildgen/version.py:5 points to "that session's own account", which no longer exists.
- setup-micropython-toolchain/action.yml:1 says "nine CI jobs" but lists eight.
- build_frozen_html.sh:53-61 guards a served path of 255 or more characters, for which no trigger exists (the site's few
  short paths). It is tiny, but it is a hypothetical guard.
- The ruff scope list exists twice, in lint.sh:49 and ci.yml (lint-and-typecheck), and a test keeps the two equal. CI
  runs the gc and method-assign guards only through pytest.
- The apt options (`tool.uv_sync_attempts`, `tool.apt_acquire_timeout_s`) are restated in setup_toolchain.apt_options(),
  apt-cache-restore and playwright-chromium, held equal by tunable tags rather than read from one place.
- web-lint-and-typecheck's `HTML_VALIDATE_REQUIRED` step is a planted-misspelling negative test of a linter config. The
  owner warned on 2026-11-11 that such tests are "prone to become overkill".
