# U23 (WEB: the website, its build and the web test tier) lane plan, v1 (against `wt-u22api`, HEAD `8386afa` = U0..U22)

Source: `u23/pk/U23_steps.md` (82 numbered steps, step 21 a co-landing group of 31 merged changes: 112; register
deltas `:156-161`, fold parts `:160-225`; carried action texts `:4949-6466`), `u23/pk/U23.md` (auditor packet; owner
record OR140/OR140.a `:558-559`), `wt-u22api/audit/actions/U23.md` (A.U23.01-.49, recovery ladder `:1197-1216`, earlier
actions `:1218-1289`, ledger `:1291-1339`, register fixes `:1341-1371`), `u23/pk/lanes.txt` (57 overlap groups, 0-56,
not 40), `wt-u21close/audit/sweeps/open_findings.md` rows naming U23 (OF-84, -85, -93, -94, -99, -106, -111, -115, -128,
-135, lines `:92-143`), `wt-u21close/audit/REGISTER.md` rows naming U23 (`:176`, `:177`, `:184`, `:476`, `:533`, `:534`,
`:548`, `:551`, `:618`, `:624`, `:648`) and U22's rows (`:582-597`), the owner's verbatim review notes
`wt-u21close/audit/review/answers.json` (keys `dns-fallback-clear-confirm`, `reset-reason-codes`,
`website-accessibility`, `website-display-details`), `u22/lane_plan.md` and `u22/rulings.md` (form). **Every
`file:line` below is `wt-u22api`'s** (U22's squash carries this tree outside `audit/`) unless it says "A-L HEAD" or names
the pinned checkout (`/root/pico-toolchain/micropython`, `v1.29.0`, read-only). `<U22>` is U22's squash hash, known at
U23's start. Facts marked **(unverified)** could not be checked by reading.

Facts read for this plan: `gather()` without `return_exceptions` re-raises a sub-task's exception at once and leaves
the other sub-tasks running unawaited (`extmod/asyncio/funcs.py:65-145`, the `ts[i].state = True` hand-back `:121-124`);
with it the exception object is the result entry (`:131-133`), and an exception instance is truthy, so HEAD's
`all(ok)` would read it as success. A public `NAME = const(v)` keeps its module assignment and is importable; an
`_`-prefixed one is folded away (`py/parse.c:855-866`). The legacy icon `legacy/firmware/html_raw/general/favicon.ico`
is 15,406 B, ICONDIR `(0, 1, 3)`, its 16×16 32-bpp entry 1128 B at offset 54 (so A.U23.39's 1150 B file holds).
SCD30 datasheet (`datasheets/scd30/Sensirion_CO2_Sensors_SCD30_Datasheet.pdf`, text read for this plan): CO2
repeatability ±10 ppm, accuracy ±(30 ppm + 3 %); humidity repeatability ±0.1 %RH; temperature repeatability ±0.1 °C.
The BMP3xx datasheets' text could not be extracted with this host's tools **(unverified)**. Every real device sets
`max_connections = 6` (`devices/*.toml:14-15`). At U22's gate `npm test` took 684 s wall: `live-backend-put-matrix`
682 s, `mock-server-put-matrix` 120 s, `mock-server.test.js` 21.6 s, `live-backend.test.js` 50 s
(`u22/gate2/npm_test.log`).

Lanes: wave 1 — **D** (the definitions contract and the server's wire facts: `buildgen/`, the `src/` tags, the
server-side marker and `ResetErrors`, `js/definitions.js`, both shape validators and their corpus), **M** (the mock and
the JS wire-fact mirror), **B** (the build: the stager, the site scripts, the page shell and stylesheet, the
website-build tests); wave 2 — **T** (templates, formatting and the accessibility check), **C** (the section controller
`js/render.js` and the layering guard), **S** (the request path, the shell, the nav and both entries, then the live
tier); wave 3 — **X** (SPECIFICATION.md) and **Y** (every other doc), last. At most three agents at once (owner,
2026-10-08).

Standing rules for every lane (as U16-U22): locate each site by its quoted text (packet lines are A-L HEAD); drop any
part already in end form and report it with its line (§6); a later unit's stage is not written (A-24); a sentence U23
makes false is corrected at U23 by its owner lane, the smallest true correction (A-25); every new or rewritten comment
block is at most 3 prose lines, in JS and CSS too (review-enforced there; `test_comment_block_cap.py` gates Python and
shell); no audit ID or undefined label in permanent text outside `audit/`; decision tags "(owner|agent, YYYY-MM-DD)",
quoting the owner's words from `audit/review/answers.json` where a text states their decision, or marked "paraphrase";
a check is never weakened; allow-lists and pending lists only shrink; no device literal outside `devices/`
(`tests_scripts/test_no_variant_literals.py`; `js/`, `html/`, `tests_js/`, `mockdata/` are clean today and must stay
so). `ext/`, `legacy/` (read-only; C reads the legacy pages for A-28, B the legacy icon) and `arduino/` (never read;
every grep `-- ':!arduino'`) are not touched. The UART wire format is untouched (no U23 step names a UART file).

## 0. Deviations (from the packet's literal staging and its 57 overlap groups), and why

| change | reason |
|---|---|
| packet group 1 (40 steps over 24 files, the co-landing group's core) is split by module: generator and definitions module → D; mock → M; stager, build scripts, page shell, stylesheet, `package.json` → B; templates/formatting → T; `js/render.js` → C; request path, shell, nav, entries → S | one owner per file, each module with its test; the unit still lands as one squash commit, so the packet's "one commit" holds |
| `js/api-contract.js` and `tests_scripts/test_js_api_mirrors.py` → M, not with the renderer | the stager's drift rule (B) refuses a `js/` module nothing imports; in wave 1 only the mock imports the contract (A-29); the mirror test pins the contract and the mock's own copies, one owner |
| `poll-manager.js`, `shell.js`, `nav.js`, `main.js`, `app.js` and the live tier → one lane S in wave 2, beside C | the entries import `showBanner`/`hideBanner` from `js/render.js` (M.WEB.022's acyclic graph, A-20) and `render.js` calls `startPolling()`'s new options, so S and C exchange their WIPs on one API base; the live tier proves S's back-off and watch (A.U23.35) and runs last on the merged page |
| files no packet step names, taken here: `buildgen/api_reference.py`, `tests_scripts/test_api_reference.py`, `tests_scripts/test_error_catalog.py`, `tests_scripts/test_buildgen_generate.py`, `src/asy_webserver_service.py`, `src/asy_base_classes.py`, `src/asy_system_service.py`, `src/asy_api_response.py` and their three unit tests → D; `mockdata/samples.json`, `tests_scripts/test_js_generated_definitions_loader.py` → M; `scripts/build_device_websites.sh`, `tests_scripts/test_build_device_websites_sh.py`, `html/favicon.ico` → B; `tests_js/generated-definitions-render.test.js` → C; `tests_js/_memory_markers.js`, `tests_js/memory-markers.test.js` → S; `README.md` → Y | each is a blast the unit's own changes turn red or false (A-4, A-8, A-9, A-12, §1 rows X1-X12), or an open finding's site |
| packet groups with no U23 edit: 11, 12, 18-21, 23, 28, 29, 33, 34, 37, 49-51 | each step there is in end form or a later unit's (§1 "none @U23", with the line or the unit) |
| OF-135 (the three U22 lane hashes in Part N) is the lead's start commit, not lane X's | the finding says "first step"; no lane edits `SPECIFICATION.md` until wave 3 (A-2) |
| the H.4 "Divergences from the legacy site" row is written at U23 by X (M.SPEC.116 stages the table at U36) | A.U23.45 moves the actor tags out of `js/render.js:266` and `html/style.css:314-316` into that row; shortening the comments without the row would drop decision records (decision-records rule (3)) (A-25) |

## 1. Step table

"landed" = in end form on this tree, line given; "none @U23" = the step's U23 part is empty (reason or unit given);
"(D1)" etc. = the part lands in that lane's WIP commit (§3). Lines are `wt-u22api`'s.

| # | M-id | U23 part (one line) | files edited at U23 | lane |
|---|---|---|---|---|
| 1 | M.GEN.003 | the emitted `asy_base_classes` import names `utc_now` on every device (today `ValueRef` only, when wired, `buildgen/codegen.py:384`); the rest landed (U5-U20) or is U28's (`_HOTSPOT_PW_DEFAULT`) | `buildgen/codegen.py` | D (D1) |
| 2 | M.GEN.008 | `"UnixTime": utc_now()` after `"UTCTime"` in the emitted `_system_status()` (`codegen.py:643`); `LastTaskEnd` is U32's | `buildgen/codegen.py` | D (D1) |
| 3 | M.GEN.015 | `"statusPath": ["notification", "PauseTime"]` on `_NOTIFICATION_PAUSE_GROUP`'s field (`buildgen/definitions.py:74-79`); `"confirm": True` on `SystemCmd` (`:57`) and `ResetErrors` (`:84`); options, labels, DNS and build groups landed (U6-U20); `:22`'s citation is U36's | `buildgen/definitions.py` | D (D1) |
| 4 | M.GEN.018 | `_DEFAULT_DECIMALS = 2` under `# @tunable web.default_decimals = 2`, emitted as top-level `defaultDecimals` beside `defaultPollIntervalMs` (`:768`); `_POLL_INTERVAL_MS` with its tag (`:34-36`), `definitions_for_toml()` (`:773`) and the CLI landed | `buildgen/definitions.py` | D (D1) |
| 5 | M.GEN.034 | `status.CalLight`'s four rows gain `"tone"` (0 neutral, 1 good, 2 warn, 3 warn); `_StatusRow` (`definitions.py:138-139`) gains an optional `tone`; the catalog shape check accepts `tone` in `CalLight` only (A.U23.20 Blast) | `buildgen/error_catalog.json`, `buildgen/definitions.py`, `tests_scripts/test_error_catalog.py` | D (D1) |
| 6 | M.GEN.014 | `UnixTime` row ("Device Clock", unit s, A.U23.22's description) after `UTCTime` (`:667`); maintenance fields gain `path`: SGP40 (`:612-617`) `[<resolved name>, <field>]`, UARTLINK (`:683`, `:687`) `["UARTLINK", "Transfers"\|"Failures"]`; no status-section table carries tones, so no status row gets `codeTones`; every other row landed (U6-U22) | `buildgen/definitions.py` | D (D1) |
| 7 | M.TEST_HELP.041 | (4)'s U23 part: `/status` carries `UnixTime`, `None` before `set_utc_valid()`, then equal to `time.mktime(time.gmtime())` within 1 s — added to the existing UTC scenario (`tests/_sensortask_scenarios.py:2561-2575`) and the key list (`:2339-2341`), no new build; (8)'s `State` landed at U22 on `/status` (A-3) | `tests/_sensortask_scenarios.py` | D |
| 8 | M.TEST_UNIT.332 | A.U23.47's typing only: the local `run()` `"Coroutine[Any, Any, T]"` → `"Coroutine[object, None, T]"`, the `Any` import goes (`tests/test_website_build_integration.py:27-38`); the shared harness (`tests/_async_harness.py`, absent) and the rest are U24/U27's | `tests/test_website_build_integration.py` | B |
| 9 | M.TOOL.033 | `test_website_build_integration` leaves the explicit-`Any` baseline (`pyproject.toml:488`) once row 8 clears it | `pyproject.toml` | B |
| 10 | M.TSC.017 | appends one invalid case per rejection U23 adds and one valid case per new key (§9.2) to the corpus (73 cases at HEAD) | `tests_scripts/definitions_shape_cases.json` | D (D1) |
| 11 | M.TSC.039 | `_shape_problems()` (`tests_scripts/test_buildgen_definitions.py:689`) gains `_MAX_POLL_INTERVAL_MS = 2**31 - 1` on both intervals and every U23 rejection of row 21.13; `test_shape_corpus_agrees` (`:711`) landed (U6) | `tests_scripts/test_buildgen_definitions.py` | D (D1) |
| 12 | M.TSC.100 | new `tests_scripts/test_js_api_mirrors.py`: result words, `COUNTER_CAP`, the unavailable marker (through A-8's constant), the first six `_gmtimestruct_to_dict()` keys (`codegen.py:593`), `STANDARD_CODES`, (1) `ERR_COUNT_CAP` vs `_MAX_CNT` (`src/asy_print_log.py:65`), per device `SystemCmd`/`PauseTime`/`LightCmdLED` vs `_SYSTEM_CMDS`/`_PAUSE_TIME_FIELD`/`_LIGHT_CMD_FIELDS` (`src/asy_webserver_service.py:121, :130, :135`); A-35's busy text and A-8's unknown-code text and spelling scan; planted-mismatch bites; the "drop erasefram" bite is A.S0930.20's (U24) | `tests_scripts/test_js_api_mirrors.py` | M |
| 13 | M.SPEC.111 | Stage 11's U23 half: G.2 item 12, the mirror catalog (A.U23.25, A.U6.16, A.U20.27 pairs, each with its check) | `SPECIFICATION.md` | X |
| 14 | M.TSC.170 | A.U23.47's typing only: `Mapping[str, Any]` → `Mapping[str, JsonValue]` (`tests_scripts/test_request_body_cap_headroom.py:12, :56, :75`); the per-device parametrisation is A.U24.66's | `tests_scripts/test_request_body_cap_headroom.py` | B |
| 15 | M.TSC.202 | none @U23: landed (U6, `tests_scripts/test_live_command_device_args.py:58`); S's new command takes and passes its device, so the check holds; U24 re-points it | - | (S verifies) |
| 16 | M.TWIN.136 | none @U23: U25 deletes the file; it holds if the bundle keeps the literal `definitions.json` and lacks `installMockFetch` (`tests/test_digital_twin_real_website_integration.py:174-178`, A-36) | - | (S, lead verify) |
| 17 | M.WEB.007 | `loadDefinitions()` fetches through `pollManager.request(path)`; the import (`js/definitions.js:58`) follows; the JSON-error message comes from `request()` | `js/definitions.js` | D (D1) |
| 18 | M.WEB.070 | `PRODUCTION_ONLY_RULES` merged into the `js/**/*.js` (`eslint.config.js:128`) and `html/**/*.html` (`:193`) blocks with one comment line; the `:109-110` comment names the section's once-per-episode line (the live-backend skip warning stays named until U24 removes it); the four ceilings are re-measured by the lead at the final merge (A-26); header, order plugin, comment rules, `ecmaVersion` are U24/U28/U36's | `eslint.config.js` | B (+ lead, ceilings) |
| 19 | M.SRC_NET.043 | the `@web DNSFallback` tag (`src/asy_ntp_client.py:124`) gains `clearable=true` and the description "Asked after the DHCP-provided server fails, in order. Empty = none; the Clear button empties it."; tuples, names and groups landed (U10, U18) | `src/asy_ntp_client.py` | D (D1) |
| 20 | M.WEB.018 | `parseNumberInput()`, the collection rules, the JSDoc, `CSS.escape` in every key selector (`js/render.js:21-125`) | `js/render.js` | C |
| 21.1 | M.GEN.017 | `_build_field_def()` (`definitions.py:370-412`) emits `codeTones` (from the catalog table's tones), `clearable`, `ignoredWhenSet` (a sibling of the same group, else `BuildError`), `resolution`, the resolution-derived `decimals` (A-17); the `defaultValue` emission (`:400-401`) goes; format, specials, codes, bytes, shape, alwaysExecuted, string specials, hidden landed (U6-U20) | `buildgen/definitions.py` | D (D1) |
| 21.2 | M.GEN.046 | `_FIELD_KNOWN_KEYS` (`buildgen/web_tag.py:25-29`) adds `clearable`, `ignoredWhenSet`, `resolution` with their kind checks and drops `defaultValue` (`WebFieldTag.default_value` `:65`, `_coerce_default_value`'s default path `:140-160`, `:351`); docstring and citations are U36's | `buildgen/web_tag.py` | D (D1) |
| 21.3 | M.GEN.060 | `html/index.html`: `:7` → `<link rel="icon" href="favicon.ico">`; nav `:22` gains `inert`; banner `:24` drops `hidden`, gains `data-shown="false"`; bootstrap comment `:40-43` → the packet's two lines; the header comment is U27's | `html/index.html` | B (B1) |
| 21.4 | M.GEN.062 | `html/style.css`: tokens, `color-scheme`, `--color-control-border`, `[data-nav-open]`, banner `[data-shown]`, password selector, reduced motion, double stripes, `data-worst` colours, the two unavailable/no-data rules, `.history-entry-num`/`.code-value` button resets, `.code-number`, `.code-description`, `[data-code-tone]`, `.field-warning`, `:314-316` one line (A-25); `:3` tag landed (U0); `:411-413` is U36's | `html/style.css` | B (B1) |
| 21.5 | M.SCR.019 | new `scripts/_stage_website.py` (A.U23.38 (1)-(5), the bootstrap id/key check, A.U23.39's favicon swap, HEAD's `// ---- js/<file> ----` separators kept) | `scripts/_stage_website.py` | B (B1) |
| 21.6 | M.SCR.071 | `scripts/build_website.sh`: the heredoc and the concatenation loop go for the stager call; `--stage-only` (stage into the given directory, freeze nothing); usage and `--help` follow; the kept work dir, flock, `require_device`/`require_python311` are U27's | `scripts/build_website.sh` | B (B1) |
| 21.7 | M.SRC_SENS.051 | `ContMeas`'s tag (`src/asy_scd30_driver.py:135`) loses `defaultValue=true`; `Altitude` (`:128`) gains `ignoredWhenSet=AmbPres`; plus A-15's `TempOffset` `resolution=0.01` (`:125`) and row 37's decimals; tuples, descriptions, FRC tags landed (U10, U15) | `src/asy_scd30_driver.py` | D (D1) |
| 21.8 | M.TSC.036 | `test_every_real_js_and_html_file_is_accounted_for_by_the_staging_script` (`tests_scripts/test_build_website_sh.py:116-131`) goes; its job is the stager's drift tests | `tests_scripts/test_build_website_sh.py` | B |
| 21.9 | M.WEB.001 | new `js/api-contract.js` with (1) `ERR_COUNT_CAP` | `js/api-contract.js` | M (M1) |
| 21.10 | M.WEB.002 | `js/poll-manager.js:1-92`: non-exported `DEFAULT_TIMEOUT_MS` (tag kept, `:8`), private `fetchTextWithTimeout()`, `request(..., signal)`, `isBusy`/`#activeCount` go | `js/poll-manager.js` | S (S1) |
| 21.11 | M.WEB.003 | `startPolling(pollOnce, intervalMs, {visibility, onError, stopAfterSuccess})`, `POLL_BACKOFF_MAX_MS` tagged `web.poll_backoff_max_ms`, the `Visibility` typedef; `"Poll failed:"` (`:118`) goes | `js/poll-manager.js` | S (S1) |
| 21.12 | M.WEB.004 | the typedef block (`js/definitions.js:1-56`) gains the U23 keys, `confirm`, `SiteDefinitions.defaultDecimals`; `defaultValue` and its comment (`:70-71`) go; `lasttaskend` is U32's | `js/definitions.js` | D (D1) |
| 21.13 | M.WEB.006 | `validateDefinitions()` split into private `validateSection()`/`validateGroup()`/`validateField()`/`validateHints()` with every U23 rejection and the two poll bounds | `js/definitions.js` | D (D1) |
| 21.14 | M.WEB.012 | `js/field-format.js`: `GMTIME_KEYS` import, specials first, epoch ages against `context.deviceNowS`, "invalid time value", (8a) `defaultDecimals`, (8b) arrays; (6) `lasttaskend` is U32's | `js/field-format.js` | T (T1) |
| 21.15 | M.WEB.014 | `buildFieldDescription()`/`buildField()` (`js/templates.js:22-187`): index ids, bound labels, unset toggle, code button and description, `CalLight` tone text, `title` instant, Clear button, warning, `autocomplete`, (1) "unavailable", resolution hint; plus OF-84's string specials and OF-85's shape hints (A-6, A-7); byte and host-label hints landed (U6) | `js/templates.js` | T (T1) |
| 21.16 | M.WEB.015 | `buildFieldGroupCard(group, values, groupIndex, display)` (`:189`), new `updateFieldGroupValues()` with (1), new `resetControl()` | `js/templates.js` | T (T1) |
| 21.17 | M.WEB.016 | `buildErrcountGroup(group, errcount \| null)` (`:239`): no data/unavailable rows, `data-worst` the one severity, clickable `E`/`W` pills, the filter in `dataset.filter`, (1) `ERR_COUNT_CAP+`; new `updateErrcountGroup()`; `:292-293` tag landed (U0); `:303-304` text is U36's | `js/templates.js` | T (T1) |
| 21.18 | M.WEB.017 | `buildSectionShell()` (`:351`) sets `dataset.shown = "false"` on the banner | `js/templates.js` | T (T1) |
| 21.19 | M.WEB.019 | `describeGetFailure()` JSDoc, `STATUS_SEVERITY` (`js/render.js:130`) from the contract with `severity()`, `reconcileResults()`/`applyResultStyling()` rules | `js/render.js` | C |
| 21.20 | M.WEB.020 | `renderSection(defs, section, mainEl, context)` (`:287`): one controller, one loop for every section, `onError`/`onSuccess`, `refreshAfterApply()`, build-once/update-in-place, generic `/status` sub-fetch (the `:357-368` special case goes), `groupValuesFrom()` by path (`:411-420` flattening goes) | `js/render.js` | C (C1) |
| 21.21 | M.WEB.021 | `buildAndWireFieldGroup(group, groupIndex, section, values, ctx)` (`:188`): `send()`, results, resets, refresh awaited, Clear, warning, `confirm` dialogs, (1) the refresh before collecting; `:264-266` → one line (A-25); `:260-262`'s disable keeps HEAD's form (A.U24.48's is U24, A-24) | `js/render.js` | C |
| 21.22 | M.WEB.025 | new `js/shell.js` (`startShell`, `visibilityOf`, `historyOf`, the device watch tagged `web.device_watch_interval_ms`, the clock, the Apply count, Back/Forward) | `js/shell.js` | S (S1) |
| 21.23 | M.WEB.026 | `initNav({..., keyTarget, onSelect})` (`js/nav.js:21`) → `{setCurrent, dispose}`, `data-nav-open`, `inert`, focus, `aria-label` | `js/nav.js` | S (S1) |
| 21.24 | M.WEB.030 | `js/main.js` keeps load, name and `startShell(...)`, returns the stop handle; `@param` keys and the `definitions.json` literal kept (A-36) | `js/main.js` | S (S1) |
| 21.25 | M.WEB.031 | `js/app.js`: every startup fetch through `pollManager.request()`; `fetchWithTimeout` (`:10`, `:23`) and `selectSection()` (`:100-117`) go; manifest and `composeMockData` landed (U6) | `js/app.js` | S (S1) |
| 21.26 | M.WEB.040 | the mock's frame (`js/mock-server.js:9-25, :331-357, :410-411, :546-726`): `STANDARD_CODES` (A-5), `makeResponse()`, `COUNTER_CAP`, derived routes, `handleGet()`/`handlePut()`, `delayMs`, the random latency (`:590`) and `"Simulated failure"` (`:586`) go | `js/mock-server.js` | M (M1) |
| 21.27 | M.WEB.041 | PUT semantics: shapes, unknown/readonly keys "Invalid" (OF-93), `/status` result, `group-failure`, generic dispatch and always-executed rules (A-14), resolution compare; the quirk functions (`:232`, `:256`, `:297`, `:312`) go | `js/mock-server.js` | M |
| 21.28 | M.WEB.042 | GET answers: `UnixTime`/`WifiTS`/measurement `TS` from the clock, uptimes saturating, masks from `mask: true` (today hard-coded, `:684-686`); `HotspotPW` mask landed (U18) | `js/mock-server.js` | M |
| 21.29 | M.WEB.054 | `tests_js/render.test.js`: every U23 case (A.U23.03-.42, (1), (2), the confirm fold, `defaultDecimals`); U8 tags landed (`:5-9`); restores (A.U24.14), header (U27), `:958` pointer (U36) not written | `tests_js/render.test.js` | C |
| 21.30 | M.WEB.058 | `tests_js/templates.test.js`: every U23 case, (1), (2), the fold; header U27, `lasttaskend` U32 not written | `tests_js/templates.test.js` | T |
| 21.31 | M.WEB.071 | `package.json` gains `"lint:html:built": "scripts/build_device_websites.sh --stage-only build/staged_html && html-validate \"build/staged_html/*/index.html\""`; `engines`, ranges, plugin landed (U0); `preview` is U28's | `package.json` | B |
| 22 | M.DOCS.032 | U23 stage: the closing sentence "The page asks for confirmation before it sends the reset (owner, 2026-10-02)." in "## Clearing the error logs" (`DEVICE_REFERENCE.md:148-154`, the rest landed U19) | `DEVICE_REFERENCE.md` | Y |
| 23 | M.DOCS.065 | U23 stage: the two JS items (`BACKLOG.md:881-889`, the `keydown` listener and the duplicated `selectSection()`) leave as done | `BACKLOG.md` | Y |
| 24 | M.GEN.061 | new `html/favicon.ico`, 1150 B, from the legacy icon's 16×16 entry (read only) | `html/favicon.ico` | B (B1) |
| 25 | M.SCR.020 | `scripts/build_device_websites.sh` gains `--stage-only [out_root]` (default `build/staged_html`), the U6 loop landed | `scripts/build_device_websites.sh` | B (B1) |
| 26 | M.SCR.039 | none @U23: `build_website.sh`'s interface is unchanged for `scripts/test.sh:394`; lock and device derivation are U24/U27's | - | - |
| 27 | M.SCR.062 | none @U23 (interface unchanged; U24/U27) | - | - |
| 28 | M.SCR.063 | none @U23: the smoke opens the drawer by `#hamburger-button`, polls `data-apply-status` and the caption (`scripts/cross_browser_smoke.mjs:390-401, :457-516`) and counts 2 connections per page load — all hold (inlined icon, Apply re-enabled after the refresh) | - | (lead verifies) |
| 29 | M.SCR.072 | none @U23 (U27) | - | - |
| 30 | M.SPEC.021 | U23 stage: item 6's website-confirmation clause beside "asks no confirmation (owner, 2026-09-30)" (`SPECIFICATION.md:1044`); plus A-25's corrections of the A.8 reference paragraph (`:887-895`) | `SPECIFICATION.md` | X |
| 31 | M.SPEC.117 | none @U23 (U36); A-25's correction of H.5's `defaultValue` paragraph (`:6658-6670`) and the top-level key list (`:6644`) | `SPECIFICATION.md` | X |
| 32 | M.SPEC.118 | Stage 3b: (4)'s fold sentence (every numeric value's `decimals` from its source, the build's default, the API keeps full resolution), with the derivation D records (A-17) | `SPECIFICATION.md` | X |
| 33 | M.SPEC.119 | none @U23 (U36); A-25's correction of H.6's "permanent, reassuring `0`" (`:6782`) | `SPECIFICATION.md` | X |
| 34 | M.SPEC.120 | none @U23 (U36) | - | - |
| 35 | M.SPEC.149 | none @U23 (U36 writes the `@web` rows "as U23 leaves them") | - | - |
| 36 | M.SRC_SENS.072 | the `@web Calibrate` tag (`src/asy_isl29125_driver.py:182`) loses ` defaultValue=false` (the grammar key goes, else the build fails); the rest landed (U10, U15) | `src/asy_isl29125_driver.py` | D (D1) |
| 37 | M.SRC_SENS.094 | `decimals=` on the float measurement tags whose sensible count differs from 2 (A-16: SCD30 `CO2` 0, `Temp`/`Hum`/`WetBulb`/`DewPoint` 1, `:161-165`; BMP3XX `:135-137` none by default; SGP40 `:124-125` integers, no key; ISL29125 keeps its keys) | `src/asy_scd30_driver.py` (and `src/asy_bmp3xx_driver.py` only if D's datasheet read finds 2 wrong) | D (D1) |
| 38 | M.TEST_UNIT.333 | `_bundle_modules(body)` reads the derived list from the bundle banner; `:127-136`'s hand list → every banner module but `main.js` is 404 at `/js/<name>`; `:139-163`'s markers → one non-empty `// ---- js/<name> ----` section per banner module, the import/re-export loop kept; comments `:5-7` (device name kept, A-23) and `:144` follow the stager; `:98-103`/`:124` variant sites and strict loads are U24's | `tests/test_website_build_integration.py` | B |
| 39 | M.TOOL.006 | none @U23: U28 wires `npm run lint:html:built` into CI; B and the lead run it | - | - |
| 40 | M.TOOL.019 | none @U23: tags landed (U8, 15 in `ci.yml`); U28 re-measures; §7 reports U23's time | - | - |
| 41 | M.TSC.040 | (b) `codeTones` equals the catalog's tones, (g) `PauseTime`'s `statusPath` resolves in the generated `_notification_status()` keys, (h) `float: true` ⇔ `extract_field_schemas()` float, (m) A-17's decimals rule, (k)'s U23 half: `confirm: true` on `SystemCmd` and `ResetErrors` (A-18); (a), (c)-(f), (i), (j), (l) and (k)'s options landed (`:395`, `:427`, `:502`, `:518`, `:552`, `:560`, `:577`, `:403`, `:327`) | `tests_scripts/test_buildgen_definitions.py` | D |
| 42 | M.TSC.156 | new `tests_scripts/test_website_layering.py` | `tests_scripts/test_website_layering.py` | C |
| 43 | M.TSC.159 | accept/reject rows for `clearable`, `ignoredWhenSet` (an unknown sibling rejected), `resolution`; `defaultValue` rejected as retired (replacing `:69`, `:77`); `test_parse_web_tags_real_scd30_contmeas_is_freestanding` (`:552`) follows; the inventory test landed (`:679`, U20); the L.6.4-table test is U36's (A-22) | `tests_scripts/test_buildgen_web_tag.py` | D |
| 44 | M.TSC.214 | new `tests_scripts/test_stage_website.py` | `tests_scripts/test_stage_website.py` | B |
| 45 | M.TSC.224 | new `tests_scripts/test_website_tokens.py` | `tests_scripts/test_website_tokens.py` | B |
| 46 | M.WEB.005 | `SUPPORTED_SCHEMA_MAJOR` (`js/definitions.js:74`) loses `export`; new `MAX_POLL_INTERVAL_MS`; `resolveFieldValue()` returns the raw value (`:124`); `MAX_DECIMALS` (`:77`) and `neverUnchanged()` (`:88`) landed (U6) | `js/definitions.js` | D (D1) |
| 47 | M.SRC_SENS.033 | landed (U22, A.U22.02): `NotificationSignal` holds no `last_value`/`triggered` (`src/asy_notification_service.py:145-171`) | - | - |
| 48 | M.SRC_SENS.035 | landed (U22): `_check_one() -> bool \| None` (`:215`); `report_if_fatal` is U30's | - | - |
| 49 | M.TEST_UNIT.086 | landed (U22): the threshold-read case asserts `None`; `:682`'s attribute read gone | - | - |
| 50 | M.TEST_UNIT.087 | landed (U22): `test_check_one_returns_the_most_recent_trigger_state` (`tests/test_asy_notification_service.py:889`), `test_a_stale_producer_sample_is_not_evaluated` (`:940`) | - | - |
| 51 | M.TSC.072 | pins `const MAX_POLL_INTERVAL_MS = 2 ** 31 - 1;` against `_MAX_POLL_INTERVAL_MS` read by `ast` from `test_buildgen_definitions.py`; the reader taking `const`/`export const` landed (`tests_scripts/test_definitions_js_mirrors.py:15-19`) | `tests_scripts/test_definitions_js_mirrors.py` | D |
| 52 | M.TSC.121 | U23 stage: the JS regex (`tests_scripts/test_request_timeout_ceiling.py:79`) → `(?:export )?const DEFAULT_TIMEOUT_MS = (\d+);`, in S1 with the export drop | `tests_scripts/test_request_timeout_ceiling.py` | S (S1) |
| 53 | M.WEB.013 | `js/templates.js:6-8` → the packet's two lines; `buildField` (`:56`) loses `export` | `js/templates.js` | T (T1) |
| 54 | M.WEB.022 | `showBanner()`/`hideBanner()` exported from `js/render.js` after the imports; the import list follows | `js/render.js` | C (C1) |
| 55 | M.WEB.050 | U23 stage: `API_REFERENCES` from `build/generated_src/api/*.json`, every device must have one (`tests_js/_generated_definitions.js`); the TOML stamp is U24's | `tests_js/_generated_definitions.js` | M |
| 56 | M.SCR.068 | none @U23: the generator writes `api/<d>.json` since U19 (`scripts/_generate_sensortask_modules.py:54-71`); stamps U24 | - | - |
| 57 | M.SCR.028 | none @U23 (U27; the passes stay green by construction) | - | - |
| 58 | M.SPEC.124 | Stage 3: H.8's "Poll failed:" sentence (`:7064-7065`) → A.U23.05's; the ceilings sentence (`:7067-7069`) takes the lead's re-measured figures | `SPECIFICATION.md` | X |
| 59 | M.TOOL.079 | `[mypy-test_request_body_cap_headroom]` (`host_typecheck.ini:86`) goes once row 14 clears it | `host_typecheck.ini` | B |
| 60 | M.WEB.052 | `tests_js/mock-server.test.js`: A.U23.26-.30/.49's cases and the fold's busy `descr`; A-14's `ForceCalRef`/`ContMeas` cases; U19/U20 parts landed (`:313`, `:337`); restores U24, header U27 | `tests_js/mock-server.test.js` | M |
| 61 | M.WEB.055 | none in the file (landed U6, `tests_js/definitions-shape-corpus.test.js:1-9`); its U23 cases are row 10's | - | (D) |
| 62 | M.WEB.057 | the local `groupValuesFrom()` mirrors row 21.20's rules (maintenance by `path`, `statusPath` from the status data, no flattening `:32`); per-device `it.each` landed (`:104`) | `tests_js/definitions-mockdata-coverage.test.js` | C |
| 63 | M.WEB.059 | `main.test.js`, `app.test.js`, `nav.test.js`: stop handles in `afterEach`, `/status` and `/system` stubs, `dataset.shown`/`navOpen`, `inert` and focus, `keyTarget`, the history fold (A-21); neutral ids and manifest stubs landed (U6) | `tests_js/main.test.js`, `tests_js/app.test.js`, `tests_js/nav.test.js` | S |
| 64 | M.WEB.061 | U23 parts: A.U23.32 (4) DebugLevel smoke (exact `valid`, then `unchanged`), A.U23.34 full ceiling with reload recovery, A.U23.35 `runLiveBackendRestartRecovery`, plus OF-115 (A-12); U8 tags landed (`tests_js/_live_twin_command.js:21-27`); the U24/U25/U27 frame not written | `tests_js/_live_twin_command.js` | S |
| 65 | M.WEB.064 | new `tests_js/shell.test.js` | `tests_js/shell.test.js` | S |
| 66 | M.WEB.066 | new `tests_js/site-functions.test.js` (the favicon clause is `test_stage_website.py`'s) | `tests_js/site-functions.test.js` | C |
| 67 | M.PROC.045 | the one-time legacy page check, listed by C in its hand-back, recorded by the lead in `audit/` (A-28) | `audit/` (lead) | C + lead |
| 68 | M.WEB.068 | new `tests_js/_source_constants.js` (`readIntConst`, `readObjectConst`) and `tests_js/source-constants.test.js` (A-19) | `tests_js/_source_constants.js`, `tests_js/source-constants.test.js` | D (D1) |
| 69 | M.WEB.051 | `tests_js/poll-manager.test.js`: every U23 case; `:126-143` (`isBusy`) goes; tag landed (`:4`); restores U24, header U27 | `tests_js/poll-manager.test.js` | S (S1) |
| 70 | M.WEB.053 | `tests_js/definitions.test.js`: the single-flight loader case, both poll bounds, `defaultValue` cases go (`:234-243`), major and timeout through `_source_constants.js`, the `confirm`/`defaultDecimals` fold; generated imports landed (U6) | `tests_js/definitions.test.js` | D (D1) |
| 71 | M.WEB.065 | new `tests_js/api-reference-agreement.test.js` | `tests_js/api-reference-agreement.test.js` | M |
| 72 | M.WEB.069 | new `tests_js/_expected_display.js` and `tests_js/expected-display.test.js` | both | S |
| 73 | M.SPEC.114 | none @U23 (U36); A-25's corrections of H.2's module map, `field-format.js` reason and "re-checks that mechanically" (`:6552-6575`) | `SPECIFICATION.md` | X |
| 74 | M.WEB.062 | U23 parts: `applyField()` (toggle clicks to the wanted value, `composite`, the `confirm` dialog accepted and asserted, waits for the re-enabled button), `getRealCurrentValues()` checks, `expectedDisplay` replaces `formatFieldValue` (`tests_js/_live_matrix_command.js:12`, `:360`), `archiveErrcount()`, `:331` JSDoc, (1); OF-115 (A-12); frame parts not written | `tests_js/_live_matrix_command.js` | S |
| 75 | M.SCR.003 | landed (U7, `scripts/_archive_evidence.py`); `--runner live_twin` matches `^[a-z0-9_]+$` | - | - |
| 76 | M.SCR.061 | none @U23 (U24/U25/U27) | - | - |
| 77 | M.TWIN.034 | none @U23: `reboot`/`bootloader` stay undriven live (the twin raises, `digital_twin/machine.py:1357-1376`) | - | - |
| 78 | M.WEB.060 | the `_put_field_cases.js:13-14` comment gains "and the live tier's action-field block"; the matrix's resolution expectation (rounded to `r`) for `TempOffset` if a probe value is off the 0.01 grid; the rest landed (U6) | `tests_js/_put_field_cases.js`, `tests_js/mock-server-put-matrix.test.js` | M |
| 79 | M.WEB.063 | `live-backend.test.js`: `it`, exact `valid`/`unchanged`, the full-ceiling and restart-recovery cases with their tagged timeouts; `live-backend-put-matrix.test.js`: `groupHasDispatchField()` (`:37`) and `"ValidOrUnchanged"` go, `willRoundTrip`, `expectedDisplay`, the action-field block, the mask exclusion's citation; skip branches stay (A.U24.52, A-24); `REAL_PATHS`/`ALWAYS_REMOUNTS_AS` already gone | both | S |
| 80 | M.WEB.074 | registers `runLiveBackendRestartRecovery` and `archiveErrcount` in `vitest.config.js`; the rest landed (U6-U8) or is U24/U28's | `vitest.config.js` | S |
| 81 | M.WEB.076 | `tests_js/vitest-commands.d.ts`: the two new commands, the new return shapes (smoke, tabs), `applyField`'s `value: unknown` | `tests_js/vitest-commands.d.ts` | S |
| 82 | M.WEB.080 | new `tests_js/_a11y_checks.js` and `tests_js/accessibility.test.js` | both | T |
| X1 | (A-4) | `buildgen/api_reference.py`: classify the new definitions keys (`_FIELD_FACTS`/`_PAGE_ONLY`, `:23-27`), `defaultValue` leaves `_PAGE_ONLY`, the GET rule (`:142-153`) excludes dispatch fields and always-executed toggles, A-8's `unavailableMarker`/`unknownCodeText`; `tests_scripts/test_api_reference.py` follows (`:61` comment, the GET and classification tests) | `buildgen/api_reference.py`, `tests_scripts/test_api_reference.py` | D (D1) |
| X2 | (A-8, OF-94) | `UNAVAILABLE = const("unavailable")` in `src/asy_base_classes.py`; the sites `:445`, `:447`, `:453`, `:459`, `src/asy_system_service.py:576`, `src/asy_webserver_service.py:936`, `:946` use it; `_UNKNOWN_DESCR = const("Unknown error")` in `src/asy_api_response.py` used by `make_response()` (`:80-81`); unit tests follow | the four `src/` files, `tests/test_asy_base_classes.py`, `tests/test_asy_system_service.py`, `tests/test_asy_webserver_service.py`, `tests/test_asy_api_response.py` | D (D1) |
| X3 | (A-9, OF-99) | `_put_status()` (`src/asy_webserver_service.py:835`): `return_exceptions=True`; a raised or `False` entry answers "Failed", each raise persisted once; every reset awaited | `src/asy_webserver_service.py`, `tests/test_asy_webserver_service.py` | D |
| X4 | (A-13, OF-128) | the notification `TS` row (`buildgen/definitions.py:701`) → "Last Cycle Time" with a description | `buildgen/definitions.py` | D (D1) |
| X5 | (register `:551`) | `ResetReason`'s description (`:646`) gains "click the code for its meaning" | `buildgen/definitions.py` | D (D1) |
| X6 | (row 2 blast) | `tests_scripts/test_buildgen_generate.py:334`'s system key list and `test_buildgen_definitions.py:292`'s `_SYSTEM_STATUS_KEYS` gain `UnixTime` | both | D (D1) |
| X7 | (A.U23.22/.29) | `mockdata/samples.json` `status.system.UnixTime` (a number) after `UTCTime` (`:19`), so the coverage check resolves the new row | `mockdata/samples.json` | M (M1) |
| X8 | (row 55 blast) | `tests_scripts/test_js_generated_definitions_loader.py` also pins the `api/` glob | that file | M |
| X9 | (A.U23.42 blast) | `tests_js/generated-definitions-render.test.js`: banner asserts read `dataset.shown`; the "randomised latency" comment (`:15`) goes with the latency | that file | C |
| X10 | (A-12, OF-115) | `tests_js/_memory_markers.js` scans `TWIN_RESET_MARKERS` in the same drain; `tests_js/memory-markers.test.js` cases | both | S |
| X11 | (row 25 blast) | `tests_scripts/test_build_device_websites_sh.py`: `--stage-only` stages every derived device into the given root, freezes nothing, skips `zz_test_` | that file | B |
| X12 | (A-25) | Part H/A.8/G.2/Part N sentences U23 makes false or leaves without their rows (§2 X) | `SPECIFICATION.md` | X |
| X13 | (docs blast) | DEVICE_REFERENCE's `DNSFallback` sentence (`:55-58`, "the website cannot send an empty value") → the Clear button; BACKLOG's chroot list (before `:672`) gains U23's entry; README's npm table (`:255-260`) gains `npm run lint:html:built` | `DEVICE_REFERENCE.md`, `BACKLOG.md`, `README.md` | Y |

Open findings naming U23: OF-84 → row 21.15 (hint half; the send half is the owner's accepted gap, A-6); OF-85 → row
21.15 (A-7); OF-93 → row 21.27; OF-94 → X2, X1, row 12, row 21.9 (A-8); OF-99 → X3 (A-9); OF-106 → C's page test, mock
stateless (A-10); OF-111 → not taken, owner-review row unanswered (A-11); OF-115 → X10, rows 64, 74 (A-12); OF-128 → X4
(A-13); OF-135 → the lead's start commit (A-2).

Register rows naming U23: `:176` (U6's `/status` sub-fetch for an errcount group elsewhere) → row 21.20 makes it the
generic `needsStatus` path; `:177` (specials in the hint for number fields only) → row 21.15 widens it to string fields
(OF-84); `:184` (the mock's legacy-bounds comment) → row 21.26 deletes the site; `:476` (`defaultValue` U23) → rows 21.2,
21.7, 36; `:533` (`code: 5`, "Simulated failure") → row 21.26; `:534` (two mock cases landed at U19) → landed
(`tests_js/mock-server.test.js` U19 cases); `:548` (list joined with ", " and "none") → row 21.14 (8b); `:551` (the
"click the code" clause) → X5; `:618` SF-B8 → rows 21.15, 21.16, 21.20, 21.29 (2), 21.30 (2); `:624` SF-B14 → rows 21.9
(1), 21.17 (1), 12 (1), 21.30 (1); `:648` SF-M2-06 → rows 21.21 (1), 21.29 (1), 74 (1). U22's rows `:582-597`: `:596`'s
"the definitions test maps the `State` row to its `NotifyState` table" holds for row 41 (c); `:590`/`:591` (device picked
from the generated plans, no literal) set the rule every U23 file follows; `:597` (the pre-gate runs the whole
`tests_scripts/` tier) is §9.3 step 3.

## 2. Lanes

Sizes are step parts and rough lines touched. Wave 2 depends on wave 1's merged tree; within a wave the lanes trade WIPs
through an API base (§3). R ≈ the biggest single job (the controller and its ~40 new cases) is split C/T so no lane is
far bigger than the rest.

### D — the definitions contract and the server's wire facts (wave 1; ~32 rows; ~1300 lines)
Files: `buildgen/definitions.py`, `buildgen/web_tag.py`, `buildgen/codegen.py`, `buildgen/api_reference.py`,
`buildgen/error_catalog.json`, `src/asy_scd30_driver.py`, `src/asy_isl29125_driver.py`, `src/asy_ntp_client.py`,
`src/asy_bmp3xx_driver.py` (only if A-16's read moves it), `src/asy_base_classes.py`, `src/asy_system_service.py`,
`src/asy_webserver_service.py`, `src/asy_api_response.py`, `js/definitions.js`, `tests_scripts/definitions_shape_cases.json`,
`tests_scripts/test_buildgen_definitions.py`, `tests_scripts/test_buildgen_web_tag.py`, `tests_scripts/test_api_reference.py`,
`tests_scripts/test_error_catalog.py`, `tests_scripts/test_buildgen_generate.py`, `tests_scripts/test_definitions_js_mirrors.py`,
`tests/_sensortask_scenarios.py`, `tests/test_asy_base_classes.py`, `tests/test_asy_system_service.py`,
`tests/test_asy_webserver_service.py`, `tests/test_asy_api_response.py`, `tests_js/definitions.test.js`,
`tests_js/_source_constants.js`, `tests_js/source-constants.test.js`. Rows 1-7, 10, 11, 17, 19, 21.1, 21.2, 21.7, 21.12,
21.13, 36, 37, 41, 43, 46, 51, 68, 70, X1-X6.
- D1 (WIP, first): tests first (the accept/reject and emission cases of §9.2 seen failing), then the grammar keys, the
  emission (every new key, `defaultDecimals`, `UnixTime`, paths, tones, the `TS` label, the `ResetReason` clause), the
  `src/` tags, `codegen`'s `UnixTime`, the reference's classification and GET rule, the `UNAVAILABLE` and
  `_UNKNOWN_DESCR` constants with their sites, `js/definitions.js` (typedefs, constants, `resolveFieldValue()`, the split
  validator, the loader), the corpus with `_shape_problems()`, `_source_constants.js`; every test the change turns red
  rewritten in place, so `test_buildgen_*`, `test_api_reference.py`, `test_error_catalog.py` and `definitions.test.js`
  are green.
- Then: row 41's properties, row 7's scenario, X3 (`_put_status()`), the reference's failure shapes, the server files'
  runs at both GC stages, the six `tests/test_sensortask_<device>.py` at both stages.

### M — the mock and the JS wire-fact mirror (wave 1; ~12 rows; ~1400 lines)
Files: `js/mock-server.js`, `js/api-contract.js`, `mockdata/samples.json`, `tests_js/mock-server.test.js`,
`tests_js/mock-server-put-matrix.test.js`, `tests_js/_put_field_cases.js`, `tests_js/api-reference-agreement.test.js`,
`tests_js/_generated_definitions.js`, `tests_scripts/test_js_api_mirrors.py`,
`tests_scripts/test_js_generated_definitions_loader.py`. Rows 12, 21.9, 21.26-21.28, 55, 60, 71, 78, X7, X8.
- M1 (WIP, first): `js/api-contract.js`; the mock's frame (`STANDARD_CODES`, `makeResponse()`, `COUNTER_CAP`, derived
  routes, the `handleGet()`/`handlePut()` split, `delayMs`, no random latency, no `partial-result`); `samples.json`'s
  `UnixTime`; the HEAD mock cases this turns red rewritten (injected status text, 405, malformed body).
- Then: row 21.27's PUT semantics with A-14, row 21.28's GET answers, row 60's cases, the mirror test (needs D1's
  constants), the reference agreement and loader (need D1's generated references), row 78.

### B — the build, the page shell and stylesheet (wave 1; ~16 rows; ~950 lines)
Files: `scripts/_stage_website.py`, `scripts/build_website.sh`, `scripts/build_device_websites.sh`, `package.json`,
`html/favicon.ico`, `html/index.html`, `html/style.css`, `eslint.config.js`, `pyproject.toml`, `host_typecheck.ini`,
`tests_scripts/test_stage_website.py`, `tests_scripts/test_build_website_sh.py`, `tests_scripts/test_build_device_websites_sh.py`,
`tests_scripts/test_website_tokens.py`, `tests_scripts/test_request_body_cap_headroom.py`, `tests/test_website_build_integration.py`.
Rows 8, 9, 14, 18, 21.3-21.6, 21.8, 21.31, 24, 25, 38, 44, 45, 59, X11.
- B1 (WIP, first): the stager and its refusal tests (temp trees, seen failing), the two scripts' `--stage-only`, the
  icon, `index.html` — so the lead's first rebuild after wave 1 stages through the stager.
- Then: `style.css` with the tokens test, `package.json`, `eslint.config.js`'s rule, row 38's banner-derived checks,
  rows 8/14 typing and the two baselines, `npm run lint:html:built` over every device's staged page.

### T — templates, formatting and the accessibility check (wave 2; ~10 rows; ~1200 lines)
Files: `js/templates.js`, `js/field-format.js`, `tests_js/templates.test.js`, `tests_js/_a11y_checks.js`,
`tests_js/accessibility.test.js`. Rows 21.14-21.18, 21.30, 53, 82, OF-84/OF-85 hints.
- T1 (WIP, first): the templates API of §3 (signatures, DOM hooks, update functions, `resetControl()`,
  `buildErrcountGroup(group, null)`, the banner attribute) and `formatFieldValue(field, value, context)`, with the
  HEAD template cases rewritten through `buildFieldGroupCard()`.
- Then: every new template and formatter case, the accessibility check over every device and section.

### C — the section controller and the layering guard (wave 2; ~11 rows; ~1400 lines)
Files: `js/render.js`, `tests_js/render.test.js`, `tests_js/generated-definitions-render.test.js`,
`tests_js/definitions-mockdata-coverage.test.js`, `tests_js/site-functions.test.js`, `tests_scripts/test_website_layering.py`.
Rows 20, 21.19-21.21, 21.29, 42, 54, 62, 66, 67, X9, OF-106's page test.
- C1 (WIP, first): `showBanner()`/`hideBanner()`, `renderSection(defs, section, mainEl, context)` with the default
  context, `groupValuesFrom()` — the exports S and T's tests consume.
- Then: the Apply path (rows 20, 21.19, 21.21), every render case, the coverage mirror, site functions, the guard
  (red until T and S finish, §3), the legacy page ledger (A-28).

### S — the request path, the shell, the entries, then the live tier (wave 2; ~17 rows; ~1600 lines)
Files: `js/poll-manager.js`, `js/shell.js`, `js/nav.js`, `js/main.js`, `js/app.js`, `tests_js/poll-manager.test.js`,
`tests_js/shell.test.js`, `tests_js/main.test.js`, `tests_js/app.test.js`, `tests_js/nav.test.js`,
`tests_scripts/test_request_timeout_ceiling.py`, `tests_js/_live_twin_command.js`, `tests_js/_live_matrix_command.js`,
`tests_js/live-backend.test.js`, `tests_js/live-backend-put-matrix.test.js`, `tests_js/_expected_display.js`,
`tests_js/expected-display.test.js`, `vitest.config.js`, `tests_js/vitest-commands.d.ts`, `tests_js/_memory_markers.js`,
`tests_js/memory-markers.test.js`. Rows 21.10, 21.11, 21.22-21.25, 52, 63-65, 69, 72, 74, 79-81, X10.
- S1 (WIP, first): `poll-manager.js` whole with its tests and row 52; the shell, nav and entries (C1's banner pair from
  the API base).
- S2: every shell/entry/nav case on the API base.
- S3 (on the merged T, C, S finals): the live tier — the oracle, the commands, the live tests, OF-115, the two config
  files — each live file run once per device set under `unshare -n`.

### X — SPECIFICATION.md (wave 3; ~8 rows)
Rows 13, 30, 31 (corrections), 32, 33 (correction), 58, 73 (corrections), X12; Part N rows for every tag of §3 (D:
`web.default_decimals`; S: `web.poll_backoff_max_ms`, `web.device_watch_interval_ms`, `l0.live_concurrent_tabs_timeout_ms`,
`l0.live_restart_recovery_timeout_ms`; any other tag a lane reports), each in the N.1 basis form; the H.4 divergence row
(A-25); `SPECIFICATION.md:892`'s GET rule and the reference's new keys (X1).

### Y — every other doc (wave 3; 4 rows)
`DEVICE_REFERENCE.md` (row 22, X13), `BACKLOG.md` (row 23, X13's chroot entry), `README.md` (X13), `CLAUDE.md` (no edit
expected; Y confirms none of its sentences turns false). Y also enters any owner question A-28 raises in BACKLOG's
owner-question list (decision-records rule (4)).

## 3. Cross-lane contract and WIP-commit order

What a lane may rely on before the publishing WIP lands is exactly the table below, nothing else. Consumer tests
written against it run only on the API base; until then they are listed red (end of section), never worked around.

### Wave 1 publishes (D1, M1, B1)

| from → to | what the consumer must assume |
|---|---|
| D → all (D1) | **generated definitions**: `defaultDecimals: 2` (top level); field keys `clearable: true` (`DNSFallback`), `ignoredWhenSet: "AmbPres"` (`Altitude`), `resolution: 0.01` (`TempOffset`), `codeTones: {"0": "neutral", "1": "good", "2": "warn", "3": "warn"}` (`CalLight`), `statusPath: ["notification", "PauseTime"]` (notification section's `PauseTime`), `confirm: true` (`SystemCmd`, `ResetErrors`), `path` on every maintenance field (`["SGP40", "BackupTS"]`-shaped, `["UARTLINK", "Transfers"]`), `decimals` per A-16/A-17 (`TempOffset` 2 derived; SCD30 `CO2` 0, `Temp`/`Hum`/`WetBulb`/`DewPoint` 1); no `defaultValue` anywhere; status system row `UnixTime` (label "Device Clock", unit "s", no `format`) after `UTCTime`; notification row `TS` labelled "Last Cycle Time"; `State` keeps U22's `codes` (NotifyState) and no `codeTones` |
| D → M, S, lead (D1) | **wire**: `GET /status` `system.UnixTime` = Unix seconds or `null` (before `set_utc_valid()`); the unavailable marker stays exactly `{"error": "unavailable"}` on the wire (its spelling in `src/` is `asy_base_classes.UNAVAILABLE`); `asy_api_response._UNKNOWN_DESCR = const("Unknown error")`; `_STANDARD_CODES` unchanged (`0, 1, 2, 3, 400, 404, 405, 413, 500`, `src/asy_api_response.py:41-51`); `PUT /status` answers `{"ResetErrors": "Failed"}` when a reset raised (every other reset awaited) |
| D → M, T, C, S (D1) | **`js/definitions.js`**: exports `validateDefinitions`, `resolveFieldValue` (returns the raw walk, `undefined` when absent), `neverUnchanged`, `loadDefinitions(path, inlinedEl)` (through `pollManager.request()`); typedefs `FieldDef` (with every key above, `confirm`, no `defaultValue`), `SiteDefinitions` (`defaultDecimals?`), `Section`, `FieldGroup`, `ErrcountGroup`, `MockSamples`, `MockDeviceData`; `SUPPORTED_SCHEMA_MAJOR`, `MAX_DECIMALS`, `MAX_POLL_INTERVAL_MS` module-private |
| D → M, S (D1) | **`tests_js/_source_constants.js`**: `readIntConst(source, name)` (`^const <NAME> = (?<value>-?\d+);$`, multiline) and `readObjectConst(source, name)` (`{<int>: "<text>", …}`), each throwing `no const <name> in source` |
| D → B (D1) | the generator CLI and `definitions_for_toml()` unchanged; every device's definitions valid under the new validator |
| M → T, C, S, B (M1) | **`js/api-contract.js`**: `VALID`, `UNCHANGED`, `INVALID`, `FAILED`, `ERR_COUNT_CAP = 65535`, `GMTIME_KEYS = ["Year", "Month", "MDay", "Hour", "Minute", "Second"]`, `isUnavailable(value)` (exact one-key object); imports nothing |
| M → C, S (M1) | **mock behaviour**: every envelope via `makeResponse()` (code 0 "Command executed", 1 "Invalid JSON request", 404 "Not found", 405 "Method not allowed", 500 "Internal server error"); `controls.nextFailure` ∈ `"network"`, a number, `"malformed-body"`, `"torn-json"`, `"empty-body"`, `"group-failure"` (`"partial-result"` gone); `controls.delayMs` (default none: no timer, no random latency); `PUT /status` → `{"ResetErrors": "Valid"}` for `true`, `"Invalid"` otherwise; unknown or readonly keys `"Invalid"`; `LightCmdLED` busy → `"Failed"` with `descr` "LED busy - retry later"; `GET /status` sets `system.UnixTime`, `networking.WifiTS` to `Math.floor(Date.now() / 1000)`; masks from `mask: true`; `ForceCalRef` reads back the last applied value (400 fresh); `ContMeas` never on GET (A-14) |
| B → S, T, C, lead (B1) | **page shell**: `<nav ... inert>`, banner `data-shown="false"` (no `hidden` class), `<link rel="icon" href="favicon.ico">`, the bootstrap ids and `startApp({...})` keys unchanged; **bundle**: line 1-3 banner naming the derived module order, then per module `// ---- js/<file> ----` and its body (A-23's test reads both); **scripts**: `build_website.sh [--stage-only] <device> [output]`, `build_device_websites.sh [--stage-only] [out_root]` |
| B → T, C (B1/B) | **stylesheet hooks** (T and C must produce exactly these): `.error-banner:not([data-shown="true"])`, `.app-shell[data-nav-open="true"]`, `.errcount-row-wrapper[data-worst="E"\|"W"\|"none"] .errcount-row-count`, `[data-source-state="unavailable"] .field-value`, `button.history-entry-num`, `button.field-value.code-value`, `.code-number`, `p.code-description`, `[data-code-tone="good"\|"neutral"\|"warn"]`, `p.field-warning` (shown by `[data-shown="true"]`), `button.action-button.clear-button`, `input[type="password"]`, `[data-apply-status="invalid"\|"failed"]` stripes; `.hidden` stays a templates-only utility |

### Wave 2 publishes (T1, C1, S1)

| from → to | what the consumer must assume |
|---|---|
| T → C, S (T1) | `buildFieldGroupCard(group, currentValues, groupIndex, display)` with `display = {deviceNowS: number \| null, defaultDecimals?: number, isUnavailable: (field) => boolean}`; `updateFieldGroupValues(card, group, currentValues, display)`; `resetControl(wrapper, field, value)`; `buildErrcountGroup(group, errcount \| null)`; `updateErrcountGroup(card, group, errcount \| null)`; `buildSectionShell(section, mainEl)` returning the same parts, banner `data-shown="false"`; `buildNavDrawer(defs, drawerEl)` unchanged; hooks: `[data-field-wrapper-key]`, `[data-field-key]` on each value element and control, ids `field-<groupIndex>-<fieldIndex>`, toggle `data-value` ∈ `"true"`/`"false"`/`"unset"`, `[data-clear-for]`, the warning `p.field-warning` after the caption; `formatFieldValue(field, value, context = {deviceNowS: null})` |
| C → S, T (C1) | `export function showBanner(el, message)` / `hideBanner(el)` in `js/render.js`; `renderSection(defs, section, mainEl, context = {})` with `context = {visibility?, deviceClock?, onRecovered?, applyTracker?: {begin, end}}`, returns `stop()`; Apply asks `window.confirm()` for a `confirm` field (enum: "<option label>?", toggle: "<group submitLabel>?") and Clear asks "Clear <label>?"; the Apply button is disabled from the click through the post-write GET |
| S → C, T (S1) | `pollManager.request(url, init, timeoutMs, signal)` (a queued aborted request rejects `AbortError` unfetched); `startPolling(pollOnce, intervalMs, {visibility, onError, stopAfterSuccess})`; typedef `Visibility` (`import("./poll-manager.js").Visibility`); `DeviceClock` typedef in `js/shell.js` (`{nowS, observe}`); `POLL_BACKOFF_MAX_MS = 60000` readable by `readIntConst` |
| S → B, lead | `js/main.js` keeps the literal `definitions.json` and the `startApp` `@param` keys; `js/app.js` stays prototype-only (never staged); new production module `js/shell.js` |
| T, C, S → lead | the bundle's closure grows by `js/shell.js` and `js/api-contract.js` (B's stager derives it); every new or renamed tag (§2 X); allow-list lines their rewrites retire (§8) |
| S3 → X, lead | live-tier measured times (per device: smoke, tabs, restart; the put matrix per shard); the two new `l0.*` tags with values and bases |

**WIP order:** (0) the lead's start commit on `<U22>`: OF-135's five Part N rows (`SPECIFICATION.md:10183`, `:10474`,
`:10475`, `:10476`, `:10577`) cite `<U22>` (A-2). (1) Wave 1: D, M, B start together; each hands back "WIP <hash>"
(D1, M1, B1). The lead merges them into `audit/u23-api1`, regenerates the device modules
(`scripts/_generate_sensortask_modules.py`), rebuilds the frozen website and every device's site in each lane worktree
(`scripts/build_website.sh`, `scripts/build_device_websites.sh`), runs ruff, the three mypy passes, `npm run lint`,
`npm run typecheck` and the files D1/M1/B1 touched, then resumes D, M, B on it. Their finals merge into
`audit/u23-w1`. (2) Wave 2 on `audit/u23-w1`: T1, C1, S1 merge into `audit/u23-api2` (the lead rebuilds the site),
lanes resume; T and C finish; S2 finishes; T, C, S2 finals merge into `audit/u23-api3`; S resumes for S3 (the live
tier). (3) Wave 3: X and Y on the merged code tree with every fact relayed. **Squash group** (the lead): the unit lands
as one commit.

**What each lane may rely on before a WIP lands.** Wave 1 lanes rely only on HEAD plus the table rows of their own
wave; M's mirror and agreement tests and D's scenario need each other's WIP (D1 ↔ M1). Wave 2 lanes rely on the whole
wave-1 tree, the lead's rebuilt site, and the wave-2 rows above. There is no twin lane: the twin tier sees U23 only
through the generated module (`UnixTime`, D) and the frozen website (B's stager, every JS lane), which the lead rebuilds;
`tests/test_digital_twin_real_website_integration.py` holds as long as row 16's two literals hold. The test lanes are
the code lanes' own (each module with its test); the live tier (S3) relies on T, C and S2 finals.

**Which `src/` edits are U23's and why**: `asy_scd30_driver.py` (comment tags only: `ContMeas` loses `defaultValue`, or
the build fails once the key leaves the grammar; `Altitude`'s `ignoredWhenSet`, the owner's warning, OR100.a;
`TempOffset`'s `resolution`, A.U23.49; the measurement `decimals`, OR140.a (16)); `asy_isl29125_driver.py` (comment tag:
`Calibrate` loses `defaultValue`, same build reason); `asy_ntp_client.py` (comment tag: `DNSFallback` `clearable`, the
owner's Clear, OR56.a (2)); `asy_bmp3xx_driver.py` (only if A-16's datasheet read finds 2 decimals wrong); not
`asy_sgp40_driver.py` (integer values, row 37 checked) and not `asy_notification_service.py` (A.U23.37's part landed at
U22, rows 47-50). Runtime `src/` changes: `asy_base_classes.py`, `asy_system_service.py`, `asy_webserver_service.py`,
`asy_api_response.py` (OF-94, OF-99: their target is U23) and the generated module's `UnixTime` (A.U23.22).

**Red checks on a lane's worktree before its base merges (report the exact line; never work around):**
`test_js_api_mirrors.py` (M) until D1 (the constants); `api-reference-agreement.test.js`, the loader test (M) until the
lead regenerates after D1; `source-constants.test.js`'s `POLL_BACKOFF_MAX_MS` case (D) until S1 (A-19);
`test_stage_website.py`'s real-tree drift case (B) until M1 (`js/api-contract.js` has an importer); `lint-ceilings.test.js`
whenever a lane's split moves a measured maximum (the lead sets the ceilings at the end, A-26);
`test_website_layering.py` (C) until T and S finish; `accessibility.test.js` (T) until C1 and S1;
`test_tunables_register.py` until X writes the Part N rows; `test_decision_vocabulary.py`/`test_citations.py` until the
lead re-keys or drops the retired allow-list rows (§8); `test_mypy_any_baseline.py` while B has removed a module its file
has not cleared; every port-binding run outside its own namespace.

## 4. Shared files: single owner

| file | owner | others report to it |
|---|---|---|
| `SPECIFICATION.md` | X (after the lead's OF-135 start commit) | all |
| `BACKLOG.md`, `DEVICE_REFERENCE.md`, `README.md`, `CLAUDE.md` | Y | all |
| the generated definitions (`buildgen/definitions.py`, `web_tag.py`, `codegen.py`, `api_reference.py`) | D | M, T, C, S (keys they need) |
| the catalog (`buildgen/error_catalog.json`) | D | T (tone names) |
| `js/definitions.js` and the shape corpus | D | T, C, M (typedef needs) |
| `js/api-contract.js`, `tests_scripts/test_js_api_mirrors.py` | M | D (constant names), C, T |
| `package.json` | B (one script; no dependency moves, so `package-lock.json` and `.nvmrc` are nobody's) | - |
| `pyproject.toml`, `host_typecheck.ini` | B (one baseline entry each) | - |
| `eslint.config.js` | B (the rule and comment); the lead (the four ceiling values, at the final merge, A-26) | every JS lane reports its measured maxima |
| `vitest.config.js`, `tests_js/vitest-commands.d.ts`, `tsconfig.json`, `tsconfig.node.json` | S (the tsconfigs need no edit: new files fall under `tests_js/**/*.js`; S confirms) | - |
| `.github/workflows/ci.yml` | nobody (U28 wires `lint:html:built` and re-measures) | lead reports times |
| `html/index.html`, `html/style.css`, `html/favicon.ico` | B | T, C, S (hooks, §3) |
| allow-lists (`tests_scripts/_decision_vocab_allowlist.txt`, `_citation_allowlist.txt`), `test_no_variant_literals.py`'s pending list | lead (shrink only) | all |
| `frozen_modules/`, `build/` (the frozen website, `build/generated_src/`, `build/generated_html/`, `build/staged_html/`) | lead (rebuilt in each worktree before any full-graph or browser run) | D, M, B report every input change |
| `tests/test_digital_twin_*.py`, `digital_twin/`, `scripts/test.sh`, `scripts/run_*.sh`, `scripts/cross_browser_smoke.mjs`, `scripts/_generate_sensortask_modules.py`, `scripts/typecheck.sh`, `scripts/build_frozen_html.sh` | nobody (§1 "none") | lead verifies |
| `tests_hardware/` | nobody (no U23 step; `pytest --collect-only` only) | - |
| `/root/pico-toolchain` | nobody (read-only; no C, override or Unix variant change) | - |
| `ext/`, `legacy/`, `arduino/` | nobody | - |

## 5. Rulings needed (default given; conservative, reversible)

1. **A-1 the cut.** Default: D, M, B (wave 1); T, C, S (wave 2); X, Y (wave 3). Alternatives: (a) the controller as one
   lane R (T+C, ~2600 lines, twice the next lane) with S and the live tier split; (b) the live tier as its own lane L in
   a third code wave before the docs (one more wave, S smaller).
2. **A-2 OF-135.** Default: the lead's U23 start commit rewrites `45f5c23`, `7b548af`, `85c82b9` to `<U22>` in the
   five rows (`SPECIFICATION.md:10183`, `:10474-10476`, `:10577`) before any lane starts; OF-135 closed with that
   commit, and from then on each unit rewrites the previous unit's. Alternative: X does it in wave 3.
3. **A-3 what U22 moved.** U22 published `State` on `/status` with `codes` from `status.NotifyState`
   (`buildgen/definitions.py:695-700`, `codegen.py:650`) and removed the notification attributes (rows 47-50 landed).
   Default: `State` renders as A.U23.20 (2)'s code-value button by the generic rule (a readonly field with `codes` and
   no `codeTones`), no special case; row 41 (c) keeps U22's `State` → `NotifyState` mapping; M.TEST_HELP.041 (8)'s
   "`/measurements`" is U22's `/status` assertion (landed); OF-128's site is the moved `:701`.
4. **A-4 `buildgen/api_reference.py` (no step names it).** `_field_facts()` refuses an unclassified key
   (`api.field-key-unclassified`, `:33-40`) and the GET rule reads `defaultValue` (`:153`), so U23 must edit it.
   Default: `_FIELD_FACTS` gains `resolution` (the device rounds to it), `ignoredWhenSet` (the chip ignores the field
   then) and `statusPath` (where the state is read); `_PAGE_ONLY` gains `clearable`, `codeTones`, `confirm` (the API asks
   no confirmation, owner, 2026-10-01: 'The API stays single command.') and loses `defaultValue`; the GET rule excludes
   dispatch fields and always-executed toggles (`ContMeas`, the one command GET cannot report, `src/asy_scd30_driver.py:105-108`),
   the page's own unset rule (A.U23.16). Alternative: every new key page-only; a GET rule reading the module's schema by
   `ast`.
5. **A-5 `STANDARD_CODES` at U23.** M.WEB.040 lists the table without 2 and 3, but the tree's `_STANDARD_CODES` still
   has them (`src/asy_api_response.py:44-45`; `parse_cmd_request()` goes at U27, A.U27.07), and the mirror test asserts
   equality. Default: the mock's table equals the tree's (2, 3 included); U27 removes both sides in one commit.
6. **A-6 OF-84.** Default: the hint lists a string field's specials too (`"" = Open network`), closing the half
   `js/templates.js:35` names; sending `""` for `PW` stays the owner's accepted gap ("Accepted (owner, 2026-08-22,
   `cc999c1`: leave as-is)", `SPECIFICATION.md:6627`), now with one exception, the DNS fallback's Clear (OR56.a (2)).
   OF-84 closes with both stated. Alternative: `PW` gets `clearable=true` (a Clear that opens the network).
7. **A-7 OF-85.** Default: `buildFieldDescription()` gives one hint per shape: `hostLabel` as today, `hostName`
   "a host name (letters, digits, '-' and '.') or an IPv4 address", `ipv4List` "up to 3 IPv4 addresses, comma-separated,
   no spaces"; `countryCode` none (its tag description states the form, M.WEB.014 Resolved). The rules are
   `_ntp_host_ok()`/`_dns_fallback_ok()`'s (`src/asy_ntp_client.py`).
8. **A-8 OF-94.** Default: `UNAVAILABLE = const("unavailable")` in `src/asy_base_classes.py` (public, so importable,
   `py/parse.c:855-866`); the four dict sites and `asy_system_service.py:576` build `{"error": UNAVAILABLE}`; the
   webserver's two text writes (`:936`, `:946`) write one module string built once at import from it (no per-failure
   concatenation); `_UNKNOWN_DESCR = const("Unknown error")` beside `_STANDARD_CODES`; the reference gains
   `unavailableMarker` and `unknownCodeText` read by `ast`; `test_js_api_mirrors.py` pins `isUnavailable()` and the
   mock's "Unknown error" against them and scans `src/` for any other string literal `"unavailable"` used as a marker
   (bite: a planted second spelling fails). Alternative: the constant only, the reference unchanged.
9. **A-9 OF-99.** Default: `asyncio.gather(..., return_exceptions=True)`; an entry that is an exception or `False`
   answers "Failed"; each raised entry is persisted once (`err_s(... errno=_ERR_CALLBACK)`, the webserver's existing code
   for a failed source, no new catalog row); every reset is awaited before the answer. The injected exception's text stays
   clear of both memory markers (`test_memory_error_gate_agreement.py:109-119`).
10. **A-10 OF-106.** M.WEB.041 keeps the mock stateless for commands (A.S0930.31); OF-106 asks for a command-in-progress
    state. Default (minimal, OR149): C adds the page test the finding misses — a local fetch stub answering `{"result":
    {"SystemCmd": "Failed"}}` shows Failed on the field and card — and the mock stays stateless, the gap listed in H.4's
    mock paragraph at U36. Alternative: the mock keeps a `commandArmed` state after a restarting command.
11. **A-11 OF-111.** Not taken: its target is "on the owner's yes", the owner-review row (`REGISTER.md:547`) is
    unanswered and BACKLOG's owner list is empty (`BACKLOG.md:934-937`). The lead asks it in session or enters it in that
    list (decision-records rule (4)); the finding stays open.
12. **A-12 OF-115.** Default: `tests_js/_memory_markers.js` gains `TWIN_RESET_MARKERS = ["SimulatedResetError", "reboot
    triggered"]` scanned in the same drain before the tail is trimmed, with its own accessor; `twinVerdict()` and the
    matrix's stop fail on either list; `MEMORY_ERROR_MARKERS` untouched (the agreement test pins it).
13. **A-13 OF-128.** Default: the notification `TS` row "Last Cycle Time", description "When the last notification
    cycle ran, whether or not it evaluated a signal (see Evaluation State)."
14. **A-14 the mock's always-executed rule lands at U23.** M.WEB.040 (U23) deletes `SENSOR_QUIRK_FIELDS` and the quirk
    functions; M.WEB.041's generic rule (stored only when the composed data carries the key) is what replaces them, and
    makes `ForceCalRef` read back the last applied value, which A.U25.12 (7) stages at U25 and the chip does
    (Interface Description 1.4.6, cited in M.WEB.052). Default: the generic rule and its two cases at U23; U25 finds
    A.U25.12 (7) landed; X corrects H.4's "`ForceCalRef` always reports `400`" (`SPECIFICATION.md:6630`).
15. **A-15 `TempOffset`'s `resolution=0.01`.** A.U23.49's tag change has no carrier: M.SRC_SENS.051 lists every other
    SCD30 tag. Default: D adds it to `src/asy_scd30_driver.py:125` with row 21.7.
16. **A-16 the decimals values (M.SRC_SENS.094, "decided at execution").** Default from the datasheet read: SCD30
    `CO2` `decimals=0` (repeatability ±10 ppm), `Temp`, `Hum`, `WetBulb`, `DewPoint` `decimals=1` (±0.1 °C, ±0.1 %RH);
    BMP3XX none (2 fits hPa and °C) **(unverified: D reads `datasheets/bmp3xx/` and records the reason)**; SGP40 none;
    ISL29125 keeps HEAD's keys. Each reason goes into the commit message.
17. **A-17 the derivation and M.TSC.040 (m).** M.GEN.017 emits `decimals` from the tag, else from `resolution` (0.01 → 2);
    M.GEN.018/M.WEB.012 (8a) give every other non-integer the site default; (m) asks "every … fractional value has a
    `decimals` hint from 0 to 3", but ISL29125's tags carry 4 (`R`, `G`, `B`, `Bri`, `src/asy_isl29125_driver.py:197-202`),
    kept by M.SRC_SENS.094. Default: (m) asserts the effective decimals (field `decimals`, else `defaultDecimals`) of
    every displayed float field equals its source (tag, else resolution, else the site default), and that a derived or
    default value lies in 0..3; a tag's explicit value is its source's decision. Alternative: ISL29125 to 3.
18. **A-18 (k)'s confirmation check.** The definitions carry a flag, not a text; the page builds the question from the
    option label or the group's `submitLabel` (M.WEB.021). Default: (k) asserts `confirm: true` on `SystemCmd` and
    `ResetErrors` for every device; the texts are pinned by C's render cases.
19. **A-19 `_source_constants.js` in wave 1.** D drops `SUPPORTED_SCHEMA_MAJOR`'s export, so its test needs the reader in
    D1. Default: D owns the reader and `source-constants.test.js` with M.WEB.068's four names; the
    `POLL_BACKOFF_MAX_MS` case is red until S1 merges (listed). Alternative: three names in D, the fourth read by S's
    poll-manager test only.
20. **A-20 the banner pair stays in `js/render.js`** (M.WEB.022: main/app → shell → render keeps the graph acyclic; the
    stager refuses a cycle). Hence C and S share wave 2.
21. **A-21 the browser tier is real Chromium, not jsdom.** M.WEB.059's fold says "jsdom"; `vitest.config.js:47-51` runs
    Playwright's Chromium. Default: `historyOf(window)` runs on the test frame's real history; each test's `afterEach`
    restores the URL with `history.replaceState(null, "", <original>)` and calls the stop handle.
22. **A-22 M.TSC.159's L.6.4-table test is U36's**: `SPECIFICATION.md` L.6.4 (`:9329-9363`) holds no `@web` key table
    until A.U36.514 (2).
23. **A-23 `tests/test_website_build_integration.py` keeps its device name** at `:5` (true while `scripts/test.sh:394`
    builds that site); the file stays in `_NOT_YET_CLEANED`; the derived-device text is U24/U27's.
24. **A-24 later stages not written at U23**: A.U24.48's disable-reason form, A.U24.52's skip branches, A.U24.14's
    restores, A.U24.46's stamp, A.U24.08's shared harness, the U24/U25/U27 live-command frame (probe, `MICROPYPATH`, port
    lock, per-run config dir, `--mem-backup-state-path`), A.U27.28's headers, U28's CI wiring and Chromium preference,
    U32's `lasttaskend`, U36's citations, order plugin and rewrites.
25. **A-25 SPEC sentences U23 makes false.** Default: X corrects each with the smallest true text at U23 (A.8 `:892`'s GET
    rule and `:890`'s key list; H.2 `:6552`, `:6560`, `:6571-6575`; H.3 `:6595-6601`'s hook list; H.4 `:6614`'s startup
    loads, `:6627`'s gap (DNS fallback exception), `:6629-6632`'s mock quirks; H.5 `:6644`, `:6658-6670`; H.6 `:6782`;
    H.7 `:6819`, `:7014-7015`; H.8 `:7064-7069`) and writes the H.4 divergence row (A.U23.45's list with its actors),
    because the comments C and B shorten move their actor tags there; Part H's rewrite stays U36's. Alternative: keep the
    two comments' tags inline until U36.
26. **A-26 lint ceilings.** `tests_js/lint-ceilings.test.js` pins each ESLint ceiling at the exact measured maximum and
    `tests_scripts/test_lint_ceilings.py` does the same for ruff. Default: no lane raises one (a function over the ceiling
    is split); the lead re-measures the four ESLint values (and any ruff value U23 lowers) on the merged tree and sets them
    in the final merge commit; X writes the figures.
27. **A-27 the extra GET of SF-M2-06.** Default: allowed by every request count (M.WEB.062 (1)); the smoke's
    connection count is per page load (`scripts/cross_browser_smoke.mjs:44-51`) and unaffected.
28. **A-28 M.PROC.045.** Default: C lists each legacy page's controls (`legacy/firmware/html_raw/{general,wozi,arzi,dev}/*.html`,
    read only) against the matching generated site in its hand-back; the lead records it under `audit/`; a function
    with no counterpart becomes an owner question (Y enters it, decision-records rule (4)); no permanent file names a
    legacy page.
29. **A-29 `js/api-contract.js` belongs to M** (the drift rule needs an importer in wave 1; only the mock imports it then).
30. **A-30 OF-93.** Default: the mock's PUT field maps hold writable fields only, so a readonly key (`FirmwareVersion`)
    is an unknown key and answers "Invalid", stored nowhere.
31. **A-31 the confirmation texts.** Default: enum → "<chosen option label>?" ("Reboot?", "Erase FRAM?"), toggle →
    "<group submitLabel>?" ("Reset All Errors?"), Clear → "Clear <field label>?"; the live matrix's dialog handler
    asserts the message and fails on an unexpected dialog.
32. **A-32 the live tier's time.** Restart recovery and the full ceiling run per device (every device's site). Default:
    S triggers the restart as soon as the banner shows and waits by condition, never by fixed sleep; S measures
    `live-backend.test.js` and the put-matrix shards; above 15 of `web-unit-tests`' 20 minutes the lead decides (a
    shared boot per device is U27's frame). Alternative: restart recovery on one device.
33. **A-33 `ResetReason`'s description** (`REGISTER.md:551`): "Why the device last restarted, as a numeric code; click it
    for its meaning." (D, X5); `VOCState`/`FRCState`/`State` keep their texts.
34. **A-34 the mock's busy text is a mirrored `src/` fact** (`js/mock-server.js:246` copies `_LED_BUSY_DESCR`,
    `src/asy_webserver_service.py:141`); no step pins it. Default: `test_js_api_mirrors.py` pins it (G.2's mirror rule).
35. **A-35 build scripts in lane worktrees.** Default: B runs `build_website.sh`, `--stage-only` and
    `build_device_websites.sh` only into `tmp_path` or a `/tmp` directory it removes; never into `frozen_modules/`,
    `build/generated_html/` or `build/staged_html/` of a worktree (the lead's).
36. **A-36 the twin's website file.** Default: untouched; `js/main.js` keeps the literal `definitions.json` and the
    production bundle never carries `installMockFetch`.

## 6. What U13-U22 changed in U23's files, and parts already landed

`git -C wt-u22api log --oneline 1cff5a2..HEAD -- <file>` (`5689e2f` U15, `2977c4e` U16, `c11ca0a` U17, `f1f800e` U18,
`f5c8255` U19, `8742393` U19 fix, `f76385a` U20, `65088de` U21, `247cc03`/`e262800`/`7b548af`/`4f8264c` U22 lanes):
- buildgen: `codegen.py` `5689e2f 2977c4e f1f800e f5c8255 f76385a 7b548af`; `definitions.py` `5689e2f f1f800e f5c8255
  f76385a 7b548af`; `web_tag.py` `f1f800e f76385a`; `api_reference.py` `f5c8255 f76385a`; `error_catalog.json` `5689e2f
  2977c4e c11ca0a f1f800e f5c8255 f76385a 247cc03`.
- src: `asy_scd30_driver.py`, `asy_isl29125_driver.py` `5689e2f f5c8255`; `asy_ntp_client.py` `f1f800e f5c8255`;
  `asy_bmp3xx_driver.py` `5689e2f f5c8255 f76385a`; `asy_sgp40_driver.py` `5689e2f 2977c4e f76385a`;
  `asy_notification_service.py` `e262800`; `asy_webserver_service.py` `f1f800e f5c8255 f76385a`; `asy_base_classes.py`
  `5689e2f 2977c4e c11ca0a f1f800e f5c8255 f76385a`; `asy_system_service.py` `f5c8255 f76385a`.
- web: `js/definitions.js` `f1f800e`; `js/mock-server.js` `f1f800e f5c8255 f76385a`; `js/render.js` `f5c8255`; every
  other `js/`, `html/`, `package.json`, `eslint.config.js`, `vitest.config.js`, tsconfigs: none. `mockdata/samples.json`
  `5689e2f f1f800e f5c8255 f76385a 7b548af`.
- tests: `tests_js/mock-server.test.js` `f1f800e f5c8255 f76385a`; `render.test.js` `f5c8255 f76385a`; `templates.test.js`,
  `definitions-mockdata-coverage.test.js` `f76385a`; `_put_field_cases.js` `f1f800e`; every other `tests_js/` file none.
  `tests_scripts/test_buildgen_definitions.py` `5689e2f f1f800e f5c8255 f76385a 7b548af`; `test_buildgen_web_tag.py`
  `5689e2f f1f800e f76385a`; `test_api_reference.py` `f5c8255 f76385a`; `test_request_body_cap_headroom.py` `5689e2f
  f1f800e f76385a`; `test_request_timeout_ceiling.py` `f5c8255`; `definitions_shape_cases.json` `f1f800e`;
  `test_buildgen_generate.py` `5689e2f 2977c4e f1f800e f5c8255 f76385a`; `test_error_catalog.py` `f76385a`.
  `tests/_sensortask_scenarios.py` `5689e2f 2977c4e f1f800e f5c8255 f76385a 7b548af`;
  `tests/test_website_build_integration.py` `f5c8255 f76385a`; `tests/test_asy_notification_service.py` `2977c4e f76385a
  e262800`.
- config: `pyproject.toml` `5689e2f c11ca0a f1f800e f5c8255 f76385a 65088de 7b548af`; `host_typecheck.ini` `f76385a
  65088de`; `scripts/cross_browser_smoke.mjs` `8742393`; `scripts/test.sh` `8618e7f cfd92e4 65088de`.
- docs: `SPECIFICATION.md` (16 commits), `BACKLOG.md` (10), `DEVICE_REFERENCE.md` (6), `README.md` `8618e7f c11ca0a
  65088de 14dc7cd`, `CLAUDE.md` (7).

Landed (report the line, do not redo): rows 47-50 (U22); A.U23.37's notification half (`src/asy_notification_service.py:145-171`);
the U8 tags in `js/poll-manager.js:8`, `tests_js/render.test.js:5-9`, `poll-manager.test.js:4`,
`_live_twin_command.js:21-27`, `_live_matrix_command.js:23-32`, `live-backend-put-matrix.test.js:25`, `vitest.config.js:35`
and `ci.yml`'s 15 timeouts; U6's `/status` sub-fetch for an errcount group on another page (`js/render.js:369-377`), the
corpus with its vitest reader (`tests_js/definitions-shape-corpus.test.js:1-9`), `_shape_problems()` (`:689`), the
per-device coverage test (`:104`), the generated-definitions loader (`tests_js/_generated_definitions.js`), the manifest
entry (`js/app.js:15`), `build_device_websites.sh`, the byte and host-label hints, `neverUnchanged()` (`js/definitions.js:88`),
`MAX_DECIMALS` (`:77`), `dedupePutFieldCases()`/`validStringValue()` (`tests_js/_put_field_cases.js:102`, `:120`);
U18's `HotspotPW` mask (`js/mock-server.js:684-686`) and string specials (`buildgen/definitions.py:286`); U19's mock
`SystemCmd`/`PauseTime` cross-endpoint cases, the reference generator (`scripts/_generate_sensortask_modules.py:54-71`);
U20's `SystemCmd` words and near misses (`tests_js/mock-server.test.js:313`, `:337`; `test_buildgen_definitions.py:327`),
the `@web-group` inventory (`test_buildgen_web_tag.py:679`), M.TSC.040 (a), (c)-(f), (i), (j), (l); U7's
`scripts/_archive_evidence.py` and the JS marker gate (`tests_js/_memory_markers.js`); the `ContMeas` `alwaysExecuted`
flag and `Altitude`'s help (`src/asy_scd30_driver.py:128`, `:135`); `CalLight`'s tag with `codes=CalLight`
(`src/asy_isl29125_driver.py:207`); the DNS fallback group (`src/asy_ntp_client.py:124`).

## 7. Deferred-in items; build environment; what CI runs and the time it adds

Deferred into U23: U6's two early pieces (register `:176`, `:177`); U6's mock comment (`:184`); U15's `defaultValue`
(`:476`); U19's injected failure text (`:533`); U20's list formatter and the `ResetReason` click clause (`:548`, `:551`);
the folded SF-B8, SF-B14, SF-M2-06 page halves; OF-84, -85, -93, -94, -99, -106, -115, -128, -135.

Build environment: `scripts/_stage_website.py` (new, CPython stdlib only, run by `build_website.sh` under the bare
`python3` it already uses), `build_website.sh`/`build_device_websites.sh` gain `--stage-only`, `package.json` gains one
script, `pyproject.toml` and `host_typecheck.ini` lose one baseline entry each. No dependency, pin, lock or toolchain
change; no Unix-port or firmware toolchain rebuild (`/root/pico-toolchain` read-only for everyone). Y writes the chroot
list entry (X13). The firmware image grows by the frozen website (two new modules, larger templates and renderer, the
inlined icon ~1.5 KB of base64, a few definitions keys): est. +5-10 KB gzipped **(unverified)**; the lead reads the
six-device build's size line against the filesystem boundary.

Steps → CI jobs (no `ci.yml` edit at U23):
- `web-lint-and-typecheck`: rows 18 (the sink rule over `js/` and `html/`), 21.3 (`lint:html`), 21.4 (`lint:css`), every
  new JS file (`lint`, `typecheck`); `lint:html:built` runs only locally until U28. Time ≈ 0.
- `web-unit-tests`, `web-coverage` (`test:unit`): every JS lane's file; the mock's random latency goes (80-200 ms per mock
  request today, `js/mock-server.js:590`), so `mock-server.test.js` (21.6 s), `render.test.js` and
  `generated-definitions-render.test.js` get faster (est. −15-30 s); new browser files (shell, source constants, reference
  agreement, expected display, site functions over 6 devices, accessibility over 6 devices × 6 sections) est. +30-60 s;
  `live-backend.test.js` gains restart recovery and the full ceiling on 6 devices, est. 50 s → 160-220 s. Net est. +2-4 min
  against the 20-min budget (`ci.web_unit_tests_timeout_min`, measurement owed, U28).
- `web-put-matrix`: exact words, one more GET per Apply (331 cases × ~0.1 s), the action-field block (~8 cases × 6
  devices × 2-3 s); est. 682 s → 800-870 s in one process, +40-60 s per CI shard of three. `mock-server-put-matrix`
  (in `test:unit`) est. 120 s → 20-40 s without the random latency — the unit's main efficiency gain, no case removed.
- `web-cross-browser-smoke`: holds (row 28); time ≈ 0; the two-connection count is the check that the inlined icon added
  none.
- `lint-and-typecheck`: ruff/mypy over the stager, the new `tests_scripts/` files and D's `src/` edits; two baselines
  shrink. ≈ 0.
- `unit-tests`, `unit-tests-gc-threshold`, `unit-tests-coverage`: L0 (backgrounded pytest) gains the stager's temp-tree
  cases (est. 3-5 s), one real staging per device (6-10 s), `--stage-only` in the existing build fixture (6-10 s), the
  mirror, layering, tokens and buildgen cases (3-6 s): est. +20-30 s against the 1200 s bound; L1 MicroPython: row 7's
  asserts in an existing scenario (no new build, ≈ +0.1 s per device file), X2/X3's cases (≈ +1 s), row 38 (≈ 0).
- `digital-twin-e2e`: the generated module and the frozen website change; scenarios unchanged; ≈ 0.
- `firmware-build-verify`: rebuilds every image with the new frozen modules; ≈ 0 time.
- Docs rows change only the L0 doc checks.

## 8. Pitfalls specific to U23

- **Two port-binding tiers never run at once** (CLAUDE.md): `npm test`'s browser server and twins and `scripts/test.sh`'s
  HTTP/DNS servers. Every lane runs its browser files with `npx vitest run tests_js/<file>` inside its own `unshare -n
  bash -c "ip link set lo up; ..."`, never beside another run in that namespace; the lead's gate keeps `gate_v10.sh`'s
  layout. Never `npm test`/`npm run test:*`: their `pretest` hook runs `build:site`, a rebuild that is the lead's.
- **Playwright's Chromium is pre-installed** (`/opt/pw-browsers`, `vitest.config.js:17-20`); never `playwright install`,
  never `npm install`/`npm ci` (the lead copies a verified `node_modules/` into each worktree, `cp -a`, lock hash checked);
  Node is `/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin` (`.nvmrc` 24).
- **The frozen website and generated modules are the lead's** (`scripts/build_website.sh`,
  `scripts/build_device_websites.sh`, `scripts/_generate_sensortask_modules.py`): D, M and B report every input change;
  the lead rebuilds `build/generated_src/`, `build/generated_html/`, `frozen_modules/` in each worktree before any browser
  or full-graph run; B runs its scripts only into temp outputs (A-35).
- **The `src/`↔`js/` mirror obligation** (SPEC G.2/H): every JS copy of a `src/` fact is pinned by a test that reads the
  source (`test_js_api_mirrors.py`, `test_definitions_js_mirrors.py`, `test_request_timeout_ceiling.py`, the shape
  corpora); a `src/` change and its JS mirror land in one commit; the mock's busy text and unknown-code text join the
  pinned set (A-8, A-34).
- **Every device's site, not only one**: every per-device test iterates `DEVICE_IDS`/`DEVICE_NAMES`; every manual check
  (the staged-page lint, the a11y and site-function checks, the live tier) covers all six devices.
- **No device literal outside `devices/`** (U22's gate failed on exactly this): no new file names a device; fixtures use
  `"fixture-device"`; `tests/test_website_build_integration.py` keeps only its pending literals (A-23); the legacy page
  paths A-28 reads stay out of permanent text.
- **The comment cap in JS and CSS** (≤ 3 prose lines; JSDoc `@param`/`@returns`/`@typedef` exempt) is review-enforced;
  `html/style.css`'s blocks too.
- **No audit ID in permanent text** ("OF-94", "SF-M2-06", "A.U23.20", "OR140" never appear outside `audit/`); decision
  tags quote `audit/review/answers.json` or say "paraphrase"; the owner is "they".
- **A check is never weakened; allow-lists only shrink.** Rows the rewrites retire (the lead re-keys or drops them):
  `_decision_vocab_allowlist.txt:173` (`build_website.sh` header), `:531` (`main.test.js` inlining comment), `:530`
  (`live-backend.test.js` "Valid or Unchanged"), `:535-537`, `:541` (`render.test.js` comments the rewrite changes),
  `:158` (`field-format.js`'s narrow shape), `:549` (`test_build_website_sh.py`'s hand-kept list), `:527` if its
  comment moves; `_citation_allowlist.txt:113` (`test_build_website_sh.py` `js/app.js.gz`) — each lane reports the exact
  rows its text changes.
- **The memory discipline for `src/` changes** (X2, X3, rows 1-2): the touched server files and the six
  `tests/test_sensortask_<device>.py` at both GC stages with zero `MemoryError`/"memory allocation failed" lines; no
  `gc.collect()` prop; `_put_status()` allocates the exception list only on failure; `utc_now()` returns a heap int on
  rp2 per `/status` poll (a transient, SF-M4-08's unit-rig caveat); `tests_scripts/test_digital_twin_boot_contiguity.py`
  re-runs on the merged tree.
- **The whole `tests_scripts/` tier is the pre-gate check**, never a hand-picked subset (U22, `REGISTER.md:597`).
- **ESLint and ruff ceilings are exact** (A-26): never raise one; report your file's maximum; `validateDefinitions` and
  `installMockFetch` are split so no function grows past `complexity` 41, `max-depth` 4, `max-nested-callbacks` 4; the
  stager fits ruff's `max-complexity = 20`, `max-branches = 20`, `max-statements = 75`, `max-args = 8`
  (`pyproject.toml:207-213`).
- **`buildgen/api_reference.py` refuses an unclassified key** (A-4): a definitions key added without its classification
  fails every device's generation.
- **`tests_scripts/test_build_device_websites_sh.py` writes a `zz_test_` TOML into `devices/`** for its run window; B's
  `--stage-only` case shares that one fixture window, so the backgrounded pytest tier's `devices/*.toml` ordering
  constraint (SPEC E.1) stays as it is.
- **Confirmation dialogs** (A-31): every test that applies `SystemCmd` or `ResetErrors` stubs `window.confirm` (render,
  site functions) or accepts the dialog (live matrix); the smoke never applies a command.
- **Real Chromium history** (A-21): a test that selects a section pushes a history entry; restore it in `afterEach`.
- **Vitest fake timers**: the back-off, visibility and watch cases run under `vi.useFakeTimers()`; a test that ends with
  fake timers restores them (until U24's `restoreMocks`).
- **The bundle separators** `// ---- js/<file> ----` are kept by the stager; row 38's test reads them.
- **The silent-failure scan** (standing) over the changed files, in these modes, each named in the record: first load
  (inlined and fetched definitions, a malformed definitions file), a section switch with a GET in flight, a hidden tab,
  a device reboot and a reflash with a new build (the watch), a stalled body read, a failing GET episode and its
  recovery, a PUT with every result shape (word in place of a map, unknown word, missing key, whole-request failure),
  an unavailable source and a missing errcount, a saturated counter, the full connection ceiling, a second client
  changing values (SF-M2-06), a stopped page, the mock's injected failures, a raising `ResetErrors` source, the
  unavailable marker on each GET; the pairs: an Apply during a section switch, a watch reload during a pending Apply, a
  restart during a back-off wait.

## 9. Test plan, timing, and the checks the lead re-runs on the merged tree

### 9.1 Tiers per behaviour ("+" added at U23)

| behaviour | L0 pytest | L0 vitest (mock, stubs) | L1 MicroPython | L2 live twin |
|---|---|---|---|---|
| definitions keys, validator, corpus | + rows 10, 11, 41, 43, X1 | + rows 70, 10 (corpus reader) | - | - |
| `UnixTime`, unavailable marker, `ResetErrors` raise | + row 12, X1 | - | + row 7, X2, X3 | via the page (S3) |
| request path, loop, shell, watch, Back | + row 52 | + rows 69, 65, 63 | - | + row 79 restart recovery |
| render: in place, abort, failures, results, Apply/Clear/confirm | - | + rows 21.29, 62, 66, X9 | - | + rows 74, 79 (matrix, action fields) |
| templates, formats, codes, a11y | + row 45 (tokens) | + rows 21.30, 82 | - | - |
| mock parity | + row 12 | + rows 60, 71, 78 | - | - |
| build: stager, drift, icon, staged pages | + rows 44, X11, 21.8 | - | + row 38 | - |
| layering | + row 42 | - | - | - |
| live commands' own gates | - | + X10, row 72 | - | + rows 64, 74 |

### 9.2 Tests by lane and how each is seen failing first

Every new test is written before its product change and run once on the tree; the failing line is in the hand-back. A
test that passes at once is a guard and is named as one.
- **D**: `test_buildgen_web_tag.py` — `clearable`/`ignoredWhenSet`/`resolution` accept rows fail on the tree (unknown
  key); the retired `defaultValue` row fails (accepted today); an unknown sibling and `resolution` on a string are
  rejected. `test_buildgen_definitions.py` — the `UnixTime` row and key parity, maintenance `path`, `TS` label, (b), (g),
  (k)-confirm, (m) fail (absent); (h) is a guard on the tree; each new corpus case fails `test_shape_corpus_agrees` before
  `_shape_problems()` learns it. Corpus additions: both poll bounds (2**31 rejected, 2**31-1 accepted), `groups: [null]`,
  `fields: [null]`, `kind: "slider"`, missing `key`/`label`/`kind`, `subFields` not an array and a bad sub-field,
  duplicate section/group/field keys, `submit: true` without `rest.put`, `clearable` non-boolean and on a number,
  `statusPath` empty and on a writable kind, `codeTones` key outside `codes` and an unknown tone, `ignoredWhenSet`
  naming no sibling, `resolution` 0/−1/on a string, `alwaysExecuted` non-boolean, `confirm` non-boolean and on a number,
  `defaultDecimals` 1.5/−1/101; one valid case per new key. `test_api_reference.py` — the GET rule (fails once
  `defaultValue` goes: `ContMeas` on GET), the classification, the two failure-shape keys. `test_error_catalog.py` —
  `tone` accepted in `CalLight` (fails: the shape check rejects it), refused elsewhere (bite). `test_buildgen_generate.py`
  — `UnixTime` in the system keys (fails). `test_definitions_js_mirrors.py` — `MAX_POLL_INTERVAL_MS` (fails: absent).
  `definitions.test.js` — the single-flight loader (fails: two concurrent fetches today), both bounds, `confirm`,
  `defaultDecimals`; the `defaultValue` cases go. `source-constants.test.js` (new: fails on the missing module, then on a
  missing name). `_sensortask_scenarios.py` — `UnixTime` (fails: key absent), at both GC stages ×6 devices.
  `test_asy_webserver_service.py` — a raising reset answers "Failed", every other reset ran, one persisted entry (fails:
  500 and an unawaited reset today); `test_asy_base_classes.py`, `test_asy_system_service.py`, `test_asy_api_response.py`
  — the constant-built marker and text equal the wire strings (guards: the wire is unchanged), the import of the new
  constants fails first.
- **M**: `mock-server.test.js` — 405 text, injected status text "Internal server error", `"[1,2]"`/`"nope"` → code 1,
  `group-failure`, `ResetErrors: false` → Invalid, a readonly key → Invalid (OF-93: Valid today), masks from a fixture's
  third `mask: true` field, `UnixTime`/`WifiTS`/`TS` from the clock, uptime saturating at `COUNTER_CAP`, `LocalTime`
  stable over ten GETs, no timer with `delayMs` unset (fails: random latency), resolution (12.345 → Unchanged), a fourth
  `SystemCmd` option accepted (fails: hard list), `ForceCalRef` 900 read back (fails: 400), `ContMeas` never on GET
  (guard), the busy `descr`; the `partial-result` case goes. `api-reference-agreement.test.js` and
  `test_js_api_mirrors.py` (new) fail on the missing table and module, then each bite on a temp copy.
  `test_js_generated_definitions_loader.py` — the `api/` glob (fails). Matrix: row 78 (fails only if a probe is off the
  0.01 grid).
- **B**: `test_stage_website.py` — every refusal (multi-line import, default export, re-export, dynamic import, cycle,
  duplicate export, stray `html/` file, unreferenced module, `</script` in a label escaped and parsed back, the bootstrap
  id/key check on a renamed id, a missing icon tag naming `html/index.html`, writes only inside the stage) fails before
  the stager exists; the derived order on the real tree; the icon decodes to `html/favicon.ico`, one 16×16 image whose
  offset plus size is the file length. `test_build_website_sh.py`/`test_build_device_websites_sh.py` — `--stage-only`
  (fails: unknown option today). `test_website_tokens.py` — fails on the tree (light success 3.13, danger 3.74, warn
  4.01, no `color-scheme`, no reduced-motion rule). Row 38 — the banner reader fails on HEAD's banner format. Typing — the
  main and host mypy passes fail with the module out of the baseline until `Any` is cleared. `npm run lint:html:built` —
  green over six staged pages; a planted invalid attribute in a temp stage fails it (bite).
- **T**: `templates.test.js` — ages at 0, 119, 120, 7199, 7200, 172799, 172800 s ("0 s ago" … "2 d ago"), `null`
  deviceNowS → "age unknown", −6 → "clock mismatch", `BackupTS` specials, a struct missing `Hour`, the code button and
  "No description for code <n>", `ResetReason`/`State` as code buttons, `CalLight` 2 → "<text> (2)" with
  `data-code-tone="warn"`, resolution hint, string-special hint (OF-84) and shape hints (OF-85), unset toggle
  `aria-pressed="mixed"`, `autocomplete="new-password"`, index ids and labels, "unavailable" captions, `65535+`, no-data
  rows, `data-worst` warning colour, pill click and Enter, update functions keep nodes and focus, `resetControl()`,
  `defaultDecimals`, arrays joined/"none" — each fails on the tree; the XSS cases and A28's colour-only rule are guards.
  `accessibility.test.js` — fails on the tree (duplicate `field-<key>` ids on a device with two sensors sharing a key,
  a `label[for]` with no labelable target, the drawer not `inert`, no `autocomplete`).
- **C**: `render.test.js` — stop during a pending GET (fails: card appended), node identity over three polls (fails:
  `replaceWith`), focus kept, path caption, "unavailable" and "no data", unknown word ranks worst, a sensor's word in
  place of its map, stale colours cleared, Invalid keeps its text, toggle/enum baseline follows the GET, button disabled
  until the refresh, refresh 500 keeps "valid" with no unhandled rejection, Clear after confirm only, Altitude warning
  (five cases), float `50`, hostile keys (fails: unescaped selectors throw), `console.error` once per episode (fails:
  "Poll failed:" per tick), SF-M2-06's GET before PUT and its four variants (fail: no refresh), confirm before
  `SystemCmd`/`ResetErrors` and nothing on cancel (fail), `defaultDecimals`, OF-106's local-stub Failed (guard), the
  masked-field cases (guards, A.U23.36: holds at HEAD). `generated-definitions-render.test.js` — every device renders
  with `data-shown="false"` and resolves every path (guard plus the attribute). `definitions-mockdata-coverage.test.js`
  — by path (its self-checks bite). `site-functions.test.js` — per device (a guard over today's functions, new
  coverage). `test_website_layering.py` — fails on the tree (controller `.hidden` writes, `nav.js`'s `document`
  listener, unescaped selectors, no sink rule) and bites on planted copies.
- **S**: `poll-manager.test.js` — body-read timeout, aborted queued request, in-flight abort, hidden pause and visible
  resume, back-off 3000/6000/12000…cap, `stopAfterSuccess`, stop during a tick, visibility after stop, `onError` — each
  fails on the tree; `isBusy`'s test goes. `shell.test.js` (new) — every case of row 65 incl. the history fold.
  `main/app/nav.test.js` — stop handles, `dataset.shown`, `navOpen`, `inert`, focus, `dispose()`, history (fail on the
  tree). Row 52's regex fails the moment the export drops (seen in S1). `expected-display.test.js` (new) and
  `memory-markers.test.js`'s reset-marker cases (fail: not scanned). Live (`unshare -n`, one file at a time):
  the smoke's exact `valid` then `unchanged` (fails on the tree: the identical resubmit is sparse-omitted), the full
  ceiling with reload recovery (6 tabs per device; guard or fail recorded), restart recovery (a guard on HEAD's
  fixed-interval polling, recorded as such), the matrix's exact words and the action-field block (fail: no
  `composite` gesture, no dialog), `archiveErrcount` writing under `build/archive/live_twin/`.
- **X, Y**: no tests; `test_citations.py`, `test_decision_vocabulary.py`, `test_comment_block_cap.py`,
  `test_tunables_register.py`, `test_error_catalog.py` (the SPEC catalog markers) on the merged tree.

### 9.3 Checks the lead re-runs on the merged tree

1. `scripts/lint.sh` (ruff on the eight scopes) and `scripts/typecheck.sh` (three passes); `npm run lint`, `npm run
   typecheck`, `npm run lint:html`, `npm run lint:css`, `npm run lint:html:built`; `test_mypy_any_baseline.py`.
2. Regenerate the device modules; rebuild the frozen website and every device's site.
3. The whole `tests_scripts/` tier once (never a subset); the ESLint ceilings re-measured and set (A-26); the
   allow-lists regenerated (shrink only); tier time against the 1200 s bound.
4. `scripts/test.sh` and `GC_THRESHOLD=32768 scripts/test.sh` (each in its own worktree and `unshare -n`), and
   `scripts/test.sh --coverage`: zero `MemoryError`/"memory allocation failed".
5. `npm test` per `gate_v10.sh`'s layout (its own namespace, never beside a `test.sh` run): per-file times for
   `live-backend.test.js`, both put matrices, the new files; the six twins (`run_digital_twin_ci.sh <device>`).
6. The cross-browser smoke once (two connections per page load on every device).
7. The six-device firmware build (the frozen modules changed; the size line).
8. `uv run pytest --collect-only tests_hardware -q` (board-free).
9. No audit ID in the touched permanent text; every new comment block ≤ 3 lines (JS and CSS by review); OF-84, -85, -93,
   -94, -99, -106, -115, -128, -135 closed with their lines; OF-111 left open with A-11's reason; the register's U23 rows
   marked landed; the scan record names every mode of §8's last bullet; the legacy page ledger (A-28) recorded.
10. CI after push: the web jobs' times (`web-unit-tests`, `web-put-matrix` shards, `web-coverage`), `unit-tests*` for the
    L0 tier, `firmware-build-verify` for every image.
