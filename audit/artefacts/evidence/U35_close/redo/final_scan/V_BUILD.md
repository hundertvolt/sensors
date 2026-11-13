# V_BUILD: verification of BUILD-1 to BUILD-12 (with TESTS-3 and TESTS-5 for the two overlaps)

Scope: `S/wt-final` (590cffcf) against `25caf528`; owner sources: `S/u35r/recovered/owner_rulings_after_LN118.md`,
`S/u35r/decrev/inputs/owner_words_lane_plan.md`, `S/u35r/decrev/inputs/DR1_review_decisions.tsv`, `S/u35r/picture/`,
and filtered reads of the archive branch's PROJECT_AUDIT_PLAN.md and redo evidence. All reads were filtered. Nothing
in any repo was changed.

## Summary table

| id | verdict | one-line reason | fix size (lines) | touches device behaviour? |
|---|---|---|---|---|
| BUILD-2 (= TESTS-5) | CONFIRMED-OWNER | 175/175 come from an agent sizing rule that no owner word set; the 45-70 target is out of reach without cutting the owner's timeout retries; coverage's 95 is already at its floor | ~6-10 (value only) or ~20 (CI-only knob) | n |
| BUILD-3 (= TESTS-3) | CONFIRMED (TESTS-3's form) | stale "commit the record" rule and "its twin record" citations; deleting the writer is REFUTED (owner "ok" + OR29.a (4)); "last run never happened" is false | ~6-10 | n |
| BUILD-1 | MINOR | true, but the namespace predates the audit, the build filters are one line each, and removing it means changing about 25 mostly-test files, which goes against the 11-11 "don't drift into fixing tests" | ~150-250 removed, ~25 files | n |
| BUILD-4 | CONFIRMED-OWNER | the gate's test half enforces the owner's own OR39.a rule for tests; whether a 757-line gate stays or review takes it back is his call | ~550 removed | n |
| BUILD-5 | CONFIRMED (narrowed) | three helpers that only tests call sit in buildgen; the generator script, which bench_facts already imports, is a test-side home that already exists | ~45 moved, ~8 import edits | n |
| BUILD-6 | MINOR (partly refuted) | baseline already had 10 identical "internal:" guards; by the owner's own two-part test of 10-27, narrowing an Optional is not a "typing-only" guard; only the audit-era narrowers in validate (raise) duplicate codegen's (cast) | ~20 if done | n |
| BUILD-7 | CONFIRMED | the bound-derived rate never decides (Part N's own row: 0.98 MB/s, under the 1 MB/s floor); no observed trigger; an idle mechanism inside an owner-approved feature | ~80-120 removed | n |
| BUILD-8 | MINOR | the ruling's checks hold (no trace without the TOML entry; routes come from the module); carrying the form in the module needs new tag support in buildgen; `uartCrc` is not hazard code | n/a | n |
| BUILD-9 | CONFIRMED | max-timeout build check reads only src constants (no TOML timeout key); src's `_max_timeout()` already refuses at runtime; B8's own rule removes such checks | ~25 | n |
| BUILD-10 | REFUTED | the restated dev.toml values are read by the bench device scripts through bench_facts (a key the TOML omits stays out); the CRC width table is 2 entries, guarded by a test | 1 (comment) | n |
| BUILD-11 | MINOR | the three writers have different contracts (BuildError, bool+print, bytes); the two CLIs are not duplicates (different output sets; buildgen.generate's CLI predates the audit) | ~15 | n |
| BUILD-12 | REFUTED (as proposed) | the shared/exclusive lock closes a recorded failure (OF-126, the 2026-10-08 incident); "one exclusive lock" would reopen it; only `_signals_held` (15 lines) is hypothetical | 15 (MINOR remainder) | n |

## Per finding

### BUILD-2 = TESTS-5: CI unit-test caps 175/175/95 (one verdict: CONFIRMED-OWNER)
- **Fact: VERIFIED.**
  - `ci.yml:384-385` and `:410-411` set 175; `:435-436` sets 95. The baseline set 45 for all three (`25caf528`
    ci.yml :430, :461, :484).
  - `scripts/test.sh:464-465` sets `per_file_timeout_overrides_s[scenarios]=2555`.
  - The B.10.1 sentence is at SPECIFICATION.md:1885-1891, and the Part N rows are at :12189-12191 and :12199-12202.
- **Where the values and their reasoning come from:**
  - The sizing rule is agent-written and attributed that way: SPECIFICATION.md:1986-1989 "Every job's `timeout-minutes` ... the warm wall clock plus the job's largest single retry budget, plus 25 % ... (agent, 2026-09-30) ... (agent, 2026-10-20)".
  - 2,555 s is 5 × CI's 511 s (SPEC:5432), now kept as 2.5 × the bench Pi4's 1,003 s (Part N :12201, measured 2026-11-05).
  - 175 = (warm ~10 min + 3 × 2,555 s ≈ 128 min) × 1.25.
  - 95 = (14.2 + 3 × 1,200 s = 60 min) × 1.25 (Part N :12191).
- **Owner words:** none set or approved any of the three values.
  - The owner's own words cover only the retries. OR37.a (2026-09-26, "yes, all exactly like this"): "the two settled mechanisms stay: `test.sh`'s per-file timeout-and-retry (hang backstop) and the three-attempt `uv sync` retry".
  - Owner 2026-10-20 (SPEC:5418-5420): "The retry logic is for tests running into timeout." / "Simply put, do the consistent rule adaptation to tests only and only for those running into timeout."
  - So "3 retries" means three attempts in all (two retries), on a timeout only, per file, per scenario job and per pytest tier, plus the CI `uv sync`'s three attempts. Nothing in those words sizes the job caps.
  - Owner 2026-11-04 (rulings :588-593) only keeps the CI rows in the register.
  - R2 (archive `redo/r2/LIST.md` 4.1) proposed 95/95 by lowering the scenario bound to 1,050 s "measure in phase B before the change". The bench then measured 1,003 s on the Pi4 (2026-11-05), so 1,050 s cannot serve that host. That is why 2,555 s stayed.
- **The fix as proposed does not hold:**
  - With the owner's retries kept, a hung or slow scenario job's first attempt alone takes 42.6 min (2,555 s). A 45-70 min cap ("drop the full-retry clause") would cancel it before its first retry, so on CI it reverses the owner's 10-20 rule for scenario jobs.
  - The conforming route is a lower bound for scenario jobs, as one of two options:
    - (a) lower the one value, e.g. 1,500 s, 1.5× the Pi4. No new code, but a thin margin on the Pi4.
    - (b) a CI-only env override beside `PER_FILE_TIMEOUT_S`, which is a new knob.
  - With either option unit-tests falls only to about 95 (the pytest tier's 60-min retry budget then decides; R2's own figure), and gc-threshold falls to about 85 (that job has no host tier).
  - Coverage's 95 already sits at its floor: it has no scenario job, and a tighter cap once cancelled a passed suite (ci.yml:427-428; CLAUDE.md run 34755468619). TESTS-5's "toward 45" is wrong for it.
- **Worth it:**
  - It saves minutes only when a job hangs.
  - Option (b) grows code.
  - GitHub Actions is blocked until 2026-12-01 (owner 2026-11-13), and `timeout-minutes` does not apply to local CI runs.
- **Question for the owner:** "Keep the 175-minute unit-test caps (a hung scenario still gets its two retries and a FAIL summary), or lower the scenario bound (one value, or a CI-only setting) so the two caps fall to about 95/85?"

### BUILD-3 = TESTS-3: twin-record writer (one verdict: CONFIRMED in TESTS-3's form)
- **Fact: VERIFIED.**
  - `scripts/record_twin_instrument_runs.py:33` writes `tests_hardware/twin_record.json`, and `.gitignore` does not cover it.
  - No record is tracked.
  - `tests_hardware/README.md:588` ends with "Then commit the record | review (the committed record returns on the final tree)".
  - `digital_twin/README.md:647-649` and `BACKLOG.md:102` and `:160` cite "its twin record".
- **What refutes BUILD-3's version:**
  - The runner is owner-approved. Review `twin-first-for-instruments` = "ok" (`DR1_review_decisions.tsv:69`: "A committed runner runs every device script and hardware test once against the twin ... exceptions are listed"; the rejected alternative was "The twin pre-run stays a scratch tool").
  - OR29.a (4), owner "yes, that's right": every hardware test "is run once against the digital twin before entering the queue".
  - PLAN R0, under the owner's "Go ahead with R0" (rulings :405-407): "The twin record's committed copy and its staleness test go ... The runner, `twin_board.py` and `--twin` stay; R3 re-records once."
  - Deleting the writer would drop an owner-approved feature.
  - BUILD-3's "That last run never happened" is false. R3's M lane ran it at both stages: `redo/r3/HANDBACK_M.md:33` reads "r3m_twinrec | 0 | 2,097 s ... Its JSON moved to m/twin_record.json".
  - R3 `ACTION_LIST.md:7` kept it out of the tree. That was a lead decision taken on the owner's behalf, in line with R0.
- **Smallest fix, about 6-10 lines:**
  - README.md:588 drops "Then commit the record" and the "returns on the final tree" clause.
  - BACKLOG.md:102/160 and digital_twin/README.md:647-649 stop citing a committed record.
  - Optionally, `RECORD` moves under the ignored `build/` (one line plus the test's `RECORD` patch).
  - Nothing a firmware or buildgen verdict depends on changes.

### BUILD-1: `zz_test_` namespace (MINOR)
- **Fact: VERIFIED.**
  - The filters are at the cited sites (`_devices.sh:16`, `_generate_sensortask_modules.py:168`, `_check_gc_collect_sites.py:250,268`, `build_device_websites.sh`, `cross_browser_smoke.mjs:86`, plus the test-side copies).
  - Only two tests still plant files in the live `devices/`: `test_test_sh.py:330` and `test_build_device_websites_sh.py:64`. Both test the namespace itself, so the arrangement feeds itself.
  - The sandbox approach exists (`test_build_website_sh.py:115-124`).
- **But:**
  - The namespace is pre-audit: baseline SPEC:2756-2758, `test.sh:72`, `conftest.py:23-26`, `_devices.py:18` and the `test_test_sh` sentinel at baseline `:531-549`.
  - OR36 covers the firmware image ("production code which is built for the real hardware"), not build scripts.
  - The firmware build path (`build_firmware.py` → `buildgen.generate`) carries no filter.
  - The cut is a deletion chain of about 25 files, mostly tests (count from the grep in this check).
  - Owner 2026-11-11: "don't drift into fixing tests".
- **If done:** sandbox the two planters, then delete the filters, the sweep, the reclaim and the tests of them.

### BUILD-4: gc-site gate over the test tiers (CONFIRMED-OWNER)
- **Fact: VERIFIED.**
  - The gate is 368 + 389 lines.
  - `ALLOWED` has 40 rows: 19 tests/, 4 digital_twin/ and 17 tests_hardware/device_scripts. None is in src/.
  - The baseline was a 10-line grep in lint.sh plus a 74-line structural test, scoped to src/ and buildgen/.
  - src/ and buildgen/ contain no `gc.collect(` today.
- **Correction:** "No owner words extend the gate to the tests" is too strong.
  - OR39.a (owner, 2026-09-26) sets a rule for tests in the owner's own text: "gc.collect is allowed IN TESTS for getting a clean baseline for memory measurement tests (but it takes time to complete, don't call and measure in the next line of code)".
  - Its recorded reading names `tests_scripts/test_gc_collect_sites.py` as the check that states and enforces exactly this.
  - OR54.a (integrated, agent) extended it to digital_twin.
- **What is the agent's own:** the machine form (an AST allow-list with 5 categories).
- **Smallest fix:** keep a product-scope check (src/, generated modules, one threshold per boot entry), drop the test allow-list, and leave the OR39.a rule to review. That removes about 550 lines.
- **Question for the owner:** "Should your OR39.a rule on gc.collect() in tests stay machine-enforced by the 40-row allow-list, or go back to review as at the baseline?"

### BUILD-5: test-only helpers in `buildgen.validate` (CONFIRMED, narrowed)
- **Fact: VERIFIED by `git grep`.**
  - `smallest_hard_consumer` is read only by `_digital_twin_scenarios.py:1268`, `tests_hardware/flash/test_memory_stress.py:173`, `tests_hardware/bench/test_memory_stress_bench.py:222` and `test_digital_twin_scenarios.py`.
  - `device_max_connections_by_name` is read by `_digital_twin_ci_suite.py:469` and `harness.py:463`.
  - `_owns_config_store` and `_declares_config_store` are read only by `_generate_sensortask_modules.py:116`, the expected-facts oracle.
  - `HardConsumer` has one field.
  - Their build caller was removed in 44892a2b (2026-11-04, "build checks no device file can trip removed"), and the helpers stayed.
- **Smallest fix:**
  - Move the config-store pair (~20 lines) into the generator script, its only consumer.
  - `smallest_hard_consumer` can move there too: `tests_hardware/bench_facts.py:20` already imports from that module, so a shared test-side home exists.
  - Return an int instead of `HardConsumer`.
  - Inline or move the `_by_name` wrapper.
- No generated output changes.

### BUILD-6: `BuildInternalError` guards (MINOR, partly refuted)
- **Fact:**
  - The 24 raise sites exist as listed. VERIFIED.
  - "Where the baseline had none" is false. The baseline had 10 of the same kind, raised as `BuildError(..., "internal: ...")`: codegen:220, 316, 419; definitions:266, 316, 465; validate:435, 569, 599, 638. It also had a `type: ignore[union-attr]` at codegen:262.
  - `twin_wiring.py:114-117` is pre-audit (baseline twin_wiring:59). It guards a future bus-attached driver, a P10 extension check, not a typing guard.
- **Ruling test:** the owner's two conditions (2026-10-27, rulings :88-95): "fully covered by typing adherence alone, and ... unreachable with today's code". `driver_info`/`resolved_name` are `X | None` in model.py, so typing requires the narrowing; it does not cover it. Those guards fail the owner's first condition.
- **What is true:** two shapes for one job.
  - validate's audit-era `_checked_int`, `_checked_str` and `_device_table` (validate:1078-1110) raise.
  - codegen's `_table` and `_text` (codegen:790-797) cast.
  - If touched, merge those ~20 lines onto the cast shape and leave the rest.

### BUILD-7: apt mirror bound plumbing (CONFIRMED)
- **Fact: VERIFIED.**
  - `ci.yml:579-598` regex-reads its own `@tunable` and passes `bound-s`/`bound-from`.
  - `apt-cache-restore/action.yml:27-34` and `:114-121` carry them on.
  - In `ci_apt_cache.py`, `required = floor if bound_s is None else max(floor, margin × to_fetch / bound_s)` (:236).
  - Part N's own rows (:12183-12184) state that the firmware set's 588 MB over 1,200 s needs 0.98 MB/s, under the floor. Playwright passes no bound.
  - The derived rate would decide only if the firmware job's 20-min limit dropped below about 19.6 min, or if the set grew past about 600 MB. Neither has been observed.
- **Decision:**
  - The owner approved the probe and the cache (2026-10-27, "Yes do it like you proposed").
  - The derived rate was the lead's call ("the lead's call ... covers making the mechanism work", lane plan item 47; the Part N row says "(agent, 2026-10-28)").
- **Fix:** delete the inputs, the self-parse, `Rule.bound_s/bound_from/margin`, the `ci.apt_mirror_rate_margin` row and tag, and the four rate tests that exercise the bound (test_ci_apt_cache.py:147-182, test_ci_workflow.py:416). The floor keeps deciding, as it does now. CI only.

### BUILD-8: hazard specifics in buildgen (MINOR)
- **Fact: VERIFIED** for `definitions.py:749-762` (the hand-written "UART Hazard Run" section), `:820-823` and `codegen.py:231-234`.
- **Not hazard code:**
  - `build_firmware.py:142` and `:237-239` (`uartCrc`) record the link's CRC mode.
  - `MAINTENANCE_NAMES`/UARTLINK and its link-status entry predate the audit (baseline codegen:634, definitions:435-442).
- **Ruling:**
  - Owner, 2026-11-06 09:08: "all hazard code goes into that module ... If the module is not imported ... not a single trace ... the only switch for that being its inclusion in the toml file."
  - Every check that sentence states holds: definitions:806 and codegen:221-234 emit nothing without a `uart_link` instance, and the routes come from the module's own `ROUTES` via `add_routes`.
  - The lead applied it as "its form a dev-only website section posting there" (archive `redo/r5/U14_ANSWERS.md` Q3).
- **Why not worth it:**
  - REST-pathed sections are hand-written in buildgen for every system section (definitions:42-49), and tags express only groups and fields.
  - Moving this one would need new section-level tag support in buildgen: more code, and no behaviour change.

### BUILD-9: max-timeout build check from src constants only (CONFIRMED)
- **Fact: VERIFIED.**
  - `validate.py:972-980` compares `_DEFAULT_TIMEOUT_MS` with `horizon × den // (num × mult)`, all of them src constants.
  - `codegen.py:555-558` says "the protocol's defaults read from its source (no TOML key)".
  - The only trips are src edits: test_buildgen_error_contract.py:369 and test_buildgen_validate.py:1686 both edit asy_uart_comm.py.
  - `src/asy_uart_comm.py:566-568` and `:922` refuse the same case at runtime, as a library check.
- **Decision record:** B8's own rule removes such checks (44892a2b: "build checks no device file can trip ... go").
- **Fix:**
  - Delete :972-980 and the `num`/`den`/`mult` read at :949. `horizon` stays, for the idle-poll check.
  - Delete the error-contract row and the one validate test.
  - Delete one token in SPEC:11205.

### BUILD-10: hand copies (REFUTED)
- **dev.toml:**
  - The values have a live consumer, the bench device scripts. `tests_hardware/bench_facts.py:35-48` renders each bus table "as the TOML states it ... a key the TOML leaves out stays out".
  - These scripts read the keys directly:
    - `uart_crossover_exchange.py:62-63, :143` (`bus["rx_ring"]`, `bus["poll_wait_ms"]`, `bus["poll_idle_ms"]`, `bus1["max_transfer_bytes"]`);
    - `uart_idle_poll_rate.py:55-56, :98-107`;
    - `uart_comm_hazards.py:97`;
    - `uart_driver_read_never_blocks_the_loop.py:192`.
  - Deleting the lines would break them, or would require fallback code in bench_facts.
  - Also, the generated text is not identical: codegen:181 emits the kwargs only when stated.
  - The dev.toml:43 comment is the only wrong part; it should say "so the bench scripts read them here" (1 line).
- **`UART_CRC_MODES`:** a 2-entry table that maps TOML modes to classes (buildgen's own choice), guarded by `test_buildgen_validate.py:1861-1865`. Reading only the width by AST would save nothing.

### BUILD-11: three atomic writes, two CLIs (MINOR)
- **Fact: VERIFIED** for the three helpers. But they have three contracts: `BuildError` (generate.py:34-50), bool plus a printed error (_generate_sensortask_modules.py:277-292), and 3-line bytes (build_firmware.py:224-228).
- **The CLIs are not duplicates:**
  - The generator's `--device-toml` writes the full output set (expected facts, wiring plan, definitions, API reference) that the twin's CRC16 pass needs (`_digital_twin_ci_suite.py:574`).
  - buildgen.generate's `--out-dir` CLI is pre-audit (baseline generate.py:51-57) and is used by tests and the SPEC checklist.
- Merging the writers saves about 15 lines across 3 files. That is marginal.

### BUILD-12: installer process control (REFUTED as proposed)
- **The two-mode lock answers a recorded failure.** Archive `audit/sweeps/open_findings.md` OF-126: a test run that read the Unix-port binaries while setup rebuilt them failed. That is "the 2026-10-08 incident's damage mode (a run in the window failed loudly on the frozen-verify build)", closed at U27 by the shared hold.
- "Reduce the rest to one exclusive lock" would drop the shared mode and reopen OF-126.
- **The bounded, streamed run in its own session** answers the observed apt stalls. The session exists so a timeout stops the whole command tree, and it in turn needs Ctrl-C and SIGHUP forwarding: a dropped SSH session to the bench Pi4 during a long build is an everyday trigger.
- **Only `_signals_held()`** (setup_toolchain.py:475-489, a signal landing during Popen start) is a refinement with no trigger on record. It is 15 lines plus its test; not worth it alone.

## Duplicates and notes
- **Duplicates:**
  - BUILD-2 = TESTS-5. The root is B.10.1's agent budget rule combined with a scenario bound sized for the Pi4. One verdict, above.
  - BUILD-3 = TESTS-3. Keep TESTS-3's form as the root, since BUILD-3's deletion fix and its "never re-recorded" claim are both wrong.
- **Interactions:**
  - BUILD-1 and BUILD-4 meet at `_check_gc_collect_sites.py:250,268` (the `zz_test_` filter inside the gc gate). Shrinking BUILD-4 removes two of BUILD-1's sites.
  - BUILD-5's config-store pair serves the expected-facts oracle that BUILD's Notes call by design.
- **BUILD's Notes, checked:**
  - Note 1 is wrong for the release. `wt-final/CLAUDE.md:312-315` says "the firmware calls no `gc.collect()`" and no longer describes the placement reset. The reviewer seems to have read the main checkout's CLAUDE.md.
  - Note 2 is wrong for the release. `wt-final/CLAUDE.md:535` already says "Scope is nine directories", with fakes/.
  - Note 5 is true: `micropython_overrides.py:157` "(agent, 2026-10-26)" against SPEC:2643 "(owner, 2026-10-26)" for the third modlwip patch. A provenance mismatch; the owner record should decide.
  - Note 6 is true: `micropython_overrides.py:29` "not yet re-checked on a GCC >= 14 host".
  - Note 8 is true: `setup-micropython-toolchain/action.yml:1` says "nine CI jobs", while its description lists eight.
  - Notes 7 (version.py) and 9 to 13 were not refuted. Each is a one-line doc or tooling nit.
- **Boot-confined reset:** the release has no `gc.collect()` in src/ or buildgen/. I found no owner word on its removal in the rulings file (searched for gc, collect and placement). That stays the open question the verify brief names.
