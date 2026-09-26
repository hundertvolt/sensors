# Harvest H11 — website and its tests/config: js/, html/, tests_js/, package.json, eslint.config.js, tsconfig*.json, vitest.config.js, .htmlvalidate.json, .stylelintrc.json, .nvmrc (snapshot 2a88cc8)

## js/app.js
- SETTLED | js/app.js:2-4 | "The `?device=` switch below is prototype-only (real firmware ships exactly one device's definitions.json, never branches on a query param)" | js/app.js is the prototype-only entry; production entry is js/main.js; any audit of the real build must look at main.js, not app.js | area: WEB | related: WEB.S18
- LIMIT | js/app.js:15-16 | "const KNOWN_DEVICES = [\"wozi\", \"dev\"];" | prototype only knows two of the six devices; an unknown `?device=` silently falls back to wozi (:29) rather than erroring | area: WEB | covered-by: WEB.S22
- LIMIT | js/app.js:46 | "fetchWithTimeout(`../mockdata/${device}.json`)" | prototype depends on a `mockdata/` fixture existing per device outside `html/`; only wozi/dev have one, so the other four devices cannot run in the prototype at all | area: WEB | related: WEB.T12
- ASSUME | js/app.js:53 | "response was not valid JSON (likely a corrupted or truncated transmission)" | a JSON parse failure is presumed to be a transmission error, not a malformed fixture (low) | area: WEB | -
- MIRROR | js/app.js:72-84 vs js/main.js:45-57 | "selectSection" | `selectSection()` and the startup/error-banner logic are duplicated verbatim between the prototype and production entry points; a fix to one must be copied to the other | area: WEB | covered-by: WEB.S18
- ASSUME | js/app.js:76-78 | "Defensive only: every real sectionKey traces back to defs.sections itself ... so this can't currently fire." | relies on validateDefinitions() rejecting a landingSection that matches no section key (it does, definitions.js:183-185); unreachable branch by stated assumption (same text at js/main.js:49-51) | area: WEB | -

## js/field-format.js
- INVAR | js/field-format.js:2-3 | "split out of js/templates.js so a Node-context test harness can reuse it with no DOM dependency" | this module must stay DOM-free because the Node-context live-matrix harness imports it (tests_js/_live_matrix_command.js); convention only, no lint rule enforces it (low) | area: WEB | -
- SETTLED | js/field-format.js:6-7 | "Deliberately a narrow local shape, not `import(\"./definitions.js\").FieldDef` - see SPECIFICATION.md Part H.8.1 for why." | deliberate narrow local type instead of FieldDef; not to be "tidied" into the shared typedef | area: WEB | -
- DRIFT | js/field-format.js:27-28 | "Real shape: src/sensortask_wozi.py's _gmtimestruct_to_dict()" | src/sensortask_wozi.py no longer exists; the helper is generated from buildgen/codegen.py:518 | area: WEB | covered-by: WEB.S21
- MIRROR | js/field-format.js:27-31 vs buildgen/codegen.py:518,588 | "{year, month, mday, hour, minute, second, weekday} (weekday unused here), never a pre-formatted string" | the JS `gmtimestruct` formatter hard-codes the key names of the generated `_gmtimestruct_to_dict()` output; a key rename on the Python side breaks rendering silently (NaN-free but "undefined" text) | area: WEB | -
- ASSUME | js/field-format.js:33-35 | "the one place in the stack that rounds an emitted value: no driver in src/ rounds anything, so without this a declared precision is an aspiration." | states that no src/ driver rounds values and that JS `decimals` is the sole rounding point; a cross-tree claim an auditor should verify | area: WEB | -
- LIMIT | js/field-format.js:29-31 | "const t = /** @type {...} */ (value);" | gmtimestruct branch casts without checking the value is an object; a scalar or partial struct renders as "undefined-undefined..." rather than "—" (low) | area: WEB | -

## js/main.js
- SETTLED | js/main.js:1-5 | "Real production entry point - no mock, one build-fixed device, no `?device=` switch. Staged into the frozen build as `app.js`" | production entry is renamed to app.js at staging time; auditors reading "app.js" in build artifacts must map it to js/main.js, not js/app.js | area: WEB | related: WEB.T06
- MIRROR | js/main.js:26 | "loadDefinitions(\"definitions.json\", inlinedDefinitionsEl)" | production relies on scripts/build_website.sh inlining definitions into index.html (the `inlinedDefinitionsEl`), with a fetch fallback to a staged definitions.json | area: WEB | related: WEB.T06
- ASSUME | js/main.js:49-51 | "Defensive only: ... so this can't currently fire." | same unreachable-branch assumption as js/app.js:76-78 | area: WEB | covered-by: WEB.S18

## js/definitions.js
- ASSUME | js/definitions.js:1-4 | "strictly validates a device's definitions.json ... A shape/version mismatch surfaces a visible error rather than ... skipping unknown fields" | claims strict validation, yet validateDefinitions() never checks field kind, key, label or unknown properties (only path/decimals hints), so an unknown kind renders as a text input | area: WEB | covered-by: WEB.S18
- MIRROR | js/definitions.js:44-46 | "float?: true marks a \"number\"-kind field whose real server-side type is Python float, not the int default (SPECIFICATION.md Part A.8)" | the `float` flag must match each src/ FieldSchema's "float"/"int" type; mismatch makes the client accept or reject fractional values differently from the server | area: WEB | related: WEB.T04
- MIRROR | js/definitions.js:48-49 | "errcount history shape matches print_log.py/asy_webserver_service.py exactly: no per-entry timestamp exists" | the errcount history typedef mirrors src/print_log.py + src/asy_webserver_service.py; "type" only colours, never shown as text | area: WEB | related: WEB.S08
- INVAR | js/definitions.js:51-53 | "collectGroupBody() must always resubmit it, unlike an ordinary sparse-omitted-when-unchanged persisted field" | `dispatch: true` fields must mirror SPECIFICATION.md Part H.6's dispatch-only list, and render.js must always resubmit them | area: WEB | covered-by: WEB.S02
- ASSUME | js/definitions.js:55-56 | "defaultValue is a field's safe synthetic baseline for when GET never reports a real value (a command with no persisted state, e.g. SCD30's ContMeas)" | a synthetic baseline stands in for a value the device never reports; interacts with baseline movement after Apply | area: WEB | related: WEB.S01
- MIRROR | js/definitions.js:58-59 | "The only schema major version this build of the renderer understands." | `SUPPORTED_SCHEMA_MAJOR = 1` must agree with the schemaVersion buildgen emits and the hand-written html/definitions/*.json declare (buildgen `SCHEMA_VERSION`) | area: WEB | covered-by: GEN.T15
- RISK | js/definitions.js:61-63 | "so it is unvalidated too, and a bad value costs provenance, not rendering" | websiteVersion is accepted unvalidated and rendered nowhere; accepted as costing provenance only | area: WEB | related: WEB.S20
- INVAR | js/definitions.js:66-68 | "Callers use this instead of reading `currentValues[field.key]` directly, so rendering and change-comparison never drift apart." | caller-discipline rule, not enforced; the plan already found a caller that bypasses it | area: WEB | covered-by: WEB.S10
- ASSUME | js/definitions.js:70-72 | "readonly fields only, a PUT body being always flat" | `path` is restricted to readonly fields on the stated assumption that PUT bodies are always flat; enforced by validateFieldHints (:207-211) | area: WEB | -
- LIMIT | js/definitions.js:164-165 | "if (typeof g.key !== \"string\" || typeof g.label !== \"string\")" | a group entry is dereferenced before any object/null check (a `null` group throws instead of reporting a problem); duplicate section/group/field keys are not detected | area: WEB | covered-by: WEB.S23
- DRIFT | js/definitions.js:201 | "return problems; // the group-level shape checks above already own this case" | the group-level loop only checks `Array.isArray(g.fields)` (:174), never that each field is a non-null object, so a `null`/scalar field produces no problem at all (low) | area: WEB | related: WEB.S23
- MIRROR | js/definitions.js:213-216 | "f.decimals > 100" | the 0-100 `decimals` bound must match buildgen `web_tag._MAX_DECIMALS` (and tests_js/definitions.test.js:196-198's 101 probe) | area: WEB | covered-by: GEN.T15
- PLATFORM | js/definitions.js:213-214 | "100 is Number#toFixed's own ceiling, above which it throws a RangeError" | depends on the ES2018+ `toFixed` range (0-100); engines predating that throw above 20, so this is a browser-floor dependency | area: WEB | related: WEB.T09
- INVAR | js/definitions.js:223-225 | "Never queried from `document` here - callers pass the element down, matching this module's usual convention." | the H.3 layering convention (no `document` queries in non-entry modules) is upheld by convention only | area: WEB | related: WEB.T11
- MIRROR | js/definitions.js:231-233 | "A real device build inlines definitions.json straight into index.html (cuts one connection per page load); dev/preview mode never has this element" | depends on scripts/build_website.sh producing the inlined `<script type="application/json">` element; dev/preview never exercises the inlined path | area: WEB | related: WEB.T06
- MIRROR | js/definitions.js:231-238 | "data = JSON.parse(inlinedEl.textContent ?? \"\");" | the inlined path depends on scripts/build_website.sh escaping `<` inside the embedded JSON so a literal `</script` cannot close the tag early (SPECIFICATION.md:4538-4539) | area: SEC | related: WEB.T06
- ASSUME | js/definitions.js:247-249 | "A genuine transmission error (truncated/corrupted response)" | any JSON parse failure of a fetched definitions.json is attributed to transmission, not to a bad build (low) | area: WEB | -

## js/mock-server.js
- SETTLED | js/mock-server.js:1-4 | "Prototype-only fake backend ... Replaced by the digital twin's real server per SPECIFICATION.md Part H.7 - everything outside this file targets the real API." | the mock is confined to the prototype; all other JS must target the real API contract | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:7-14 | "const REST_PATHS = ... \"/measurements\", \"/sensors\", \"/networking\", \"/system\", \"/notification\", \"/status\"" | the six intercepted paths must match src/asy_webserver_service.py's REST routes; a new route is silently passed through to the real fetch | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:16 | "const SYSTEM_CMDS = [\"reboot\", \"bootloader\", \"mempause\"];" | copied constant; other end is src/asy_webserver_service.py:95 `_SYSTEM_CMDS` | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:17 | "const PAUSE_TIME_MAX = 3600; // matches src/asy_webserver_service.py's own _PAUSE_TIME_MAX" | copied constant; other end is src/asy_webserver_service.py:98 | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:19-22 | "The /sensors fields with documented hardware quirks (Part H.4): each is a hardware dispatch re-run on every submit" | hard-coded `SENSOR_QUIRK_FIELDS` (ForceCalRef, ContMeas, SGPResetVOC, ISLCalibrate) must track every dispatch-only sensor field in src/ drivers; a new one would be store-and-echoed wrongly | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:31-32 | "the real backend does a strict type() check before ever looking at magnitude, so a JSON string (even \"42\") is rejected outright" | number-kind strictness mirrors src/ config validation | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:36-38 | "Mirrors the real int<->float policy (SPECIFICATION.md Part A.8)" | int-typed fields reject fractional values, float-typed accept any finite; must match src/ validation | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:43-46 | "specialValues.some((special) => special.value === value)" | a special value bypasses min/max; must match server-side special-value handling (low) | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:52-54 | "the real backend's type_or_range_error() rejects a non-str JSON value outright" | string strictness mirrors src/ `type_or_range_error()` | area: WEB | related: WEB.T04
- LIMIT | js/mock-server.js:59-61 | "value.length >= minLength && value.length <= maxLength" | mock counts UTF-16 code units, the server counts UTF-8 bytes | area: WEB | covered-by: WEB.S12
- MIRROR | js/mock-server.js:64-66 | "an enum's real value can be numeric (e.g. BMP3XX's PressOvers), and needs the same int-only strictness as an ordinary int field" | enum strictness mirrors src/ | area: WEB | related: WEB.T04
- LIMIT | js/mock-server.js:76 | "return { valid: true, value: rawValue };" | any other kind (e.g. a `readonly` key sent in a PUT) is accepted as valid and stored by the mock; server behaviour for such keys is not modelled (low) | area: WEB | related: WEB.T04
- LIMIT | js/mock-server.js:131 | "unknown field - silently ignored, matches ConfigManager's own convention" | parity claim the plan found false (server reports Invalid + errno 10 for an unknown /sensors sub-key) | area: WEB | covered-by: WEB.S12
- LIMIT | js/mock-server.js:133-142 | "results[key] = allValid ? \"Valid\" : \"Invalid\";" | composite fields are validated but never stored and never report "Unchanged" (low) | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:159-162 | "matching a real dispatched action (PauseTime) that never reports \"Unchanged\" the way a genuine persisted setting does" | PauseTime dispatch semantics mirror src/ | area: WEB | related: WEB.T04
- DRIFT | js/mock-server.js:178-180 | "Legacy's own led_cmd() bounds (modules/sensortask-wozi.py), now enforced server-side too (src/sensortask_wozi.py's _notification_led_callback()" | src/sensortask_wozi.py no longer exists (buildgen-generated) | area: WEB | covered-by: WEB.S21
- MIRROR | js/mock-server.js:181-184 | "LIGHT_CMD_LED_RGB_MAX = 255; ... LIGHT_CMD_LED_T_MIN = 0.5; LIGHT_CMD_LED_T_MAX = 60.0;" | copied lightCmdLED bounds; other end is the generated notification LED callback's FieldSchema records (buildgen) and legacy led_cmd() | area: WEB | related: REST.S10
- MIRROR | js/mock-server.js:186-189 | "\"Invalid\" only when the payload isn't an object; \"Failed\" when r/g/b (int, 0-255) or t (float, 0.5-60.0) is missing/wrong-typed/out-of-range" | the Invalid/Failed split for lightCmdLED is a mirrored contract | area: WEB | related: REST.S10
- LIMIT | js/mock-server.js:217-220 | "\"Valid\"/\"Invalid\" only (no real I2C bus to fail)" | mock never returns "Failed" for sensor dispatch fields, so client handling of a hardware-failed dispatch is not exercised by the mock | area: WEB | related: WEB.T15
- MIRROR | js/mock-server.js:232-235 | "`ForceCalRef` always reports 400 (SCD30's volatile register), and the three command-only triggers are omitted entirely as the real schema omits them" | GET readback quirks mirror the SCD30 driver and the real schema; 400 is also src/asy_scd30_driver.py:61's range floor | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:244 | "key !== \"ContMeas\" && key !== \"SGPResetVOC\" && key !== \"ISLCalibrate\"" | a second hard-coded list of command-only triggers, duplicating SENSOR_QUIRK_FIELDS minus ForceCalRef; the two must be kept in sync (low) | area: WEB | -
- LIMIT | js/mock-server.js:251-254 | "Simulates the backend's known gap (Part H.6): a settings group's post-write hook raising drops that group's fields from `result`" | the `partial-result` injection models a server gap the plan says is already fixed | area: WEB | covered-by: WEB.S12
- LIMIT | js/mock-server.js:263-266 | "const [key] = Object.keys(results);" | partial-result drops only the first key, not a whole settings group as the docstring describes (low) | area: WEB | related: WEB.S12
- MIRROR | js/mock-server.js:273-275 | "return { res: \"OK\", code: 0, descr: \"OK\", result };" | response envelope mirrors src/api_response.py | area: WEB | related: WEB.T04
- LIMIT | js/mock-server.js:277-280 | "Timestamp-looking keys (ending \"TS\" or named \"Timestamp\") always increment instead of jittering." | recursive jitter random-walks non-measurement values and corrupts nested time structs | area: WEB | covered-by: WEB.S12
- DRIFT | js/mock-server.js:279-280 vs :296 | "key.endsWith(\"TS\") || key === \"Timestamp\" || key.endsWith(\"Uptime\")" | the docstring omits the third `Uptime` rule the code applies (low) | area: WEB | -
- LIMIT | js/mock-server.js:299-301 | "Spread and rounding were sized for readings of order hundreds (CO2 ~600)." | jitter amplitude/rounding is a heuristic tuned per magnitude, not a model of real sensor noise (low) | area: WEB | related: WEB.T15
- LIMIT | js/mock-server.js:338-341 | "REST_PATHS.find((candidate) => url === candidate || url.startsWith(`${candidate}?`))" | only exact relative paths are intercepted; an absolute URL or trailing slash passes through to the real fetch (low) | area: WEB | -
- MIRROR | js/mock-server.js:353-356 | "Matches the backend's own make_response(1) (Part A.8/A.5): a body Request.json cannot parse ... is a clean HTTP 200 with res:\"ERR\"" | malformed-body injection mirrors the server; the mock's own un-injected handling of a malformed body differs (JSON.parse throws) | area: WEB | covered-by: WEB.S12
- LIMIT | js/mock-server.js:366 | "jsonResponse({ res: \"ERR\", code: 5, descr: \"Simulated failure\" }, failure)" | a numeric injected failure returns an envelope with no `result` key and fixed code 5 regardless of status (low) | area: WEB | related: WEB.T04
- LIMIT | js/mock-server.js:369-371 | "setTimeout(resolve, 80 + Math.random() * 120);" | random 80-200 ms latency per request makes mock-backed tests timing-nondeterministic | area: WEB | covered-by: WEB.T15
- LIMIT | js/mock-server.js:373-375 | "const rawBodyText = String(init?.body ?? \"{}\"); ... JSON.parse(rawBodyText)" | an absent body is treated as `{}`; an unparseable or non-object body throws inside fetch instead of the server's clean res:"ERR" | area: WEB | covered-by: WEB.S12
- LIMIT | js/mock-server.js:383-387 | "if (sensorDefs === undefined) { continue; }" | unknown sensor key in a /sensors PUT is silently dropped from the result | area: WEB | covered-by: WEB.S12
- LIMIT | js/mock-server.js:415-418 | "const { SystemCmd, PauseTime, lightCmdLED, ...persistableBody } = rawBody;" | the three action keys are stripped on all three endpoints, so e.g. `SystemCmd` sent to /networking vanishes from the result instead of being reported (low) | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:415-418 | "which is what keeps a later GET matching _get_settings_flat()." | mock GET shape for settings endpoints mirrors src/asy_webserver_service.py:436 `_get_settings_flat()` | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:436-438 | "Real reset() (src/print_log.py) refills the fixed-length history with \"no error\" placeholders, it never shrinks/empties the array." | ResetErrors semantics mirror src/print_log.py reset() | area: WEB | related: WEB.T04
- LIMIT | js/mock-server.js:432-441 | "if (body().ResetErrors === true) { ... } return jsonResponse({ res: \"OK\", code: 0, descr: \"OK\" });" | /status PUT returns no per-field `result` map and ignores every other key (including a non-true ResetErrors) (low) | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:443 | "jsonResponse({ res: \"ERR\", code: 4, descr: \"Method not allowed\" }, 405)" | 405 envelope and code 4 mirror the server (low) | area: WEB | related: WEB.T04
- MIRROR | js/mock-server.js:459-461 | "Mirrors src/asy_wifi_service.py's _mask_pw() callback overlay: PW is a real credential, never returned in plaintext over GET" | the mock masks only PW; the real `_mask_pw()` (src/asy_wifi_service.py:197-201) masks PW and HotspotPW (HotspotPW is not in any definitions/mockdata, so no visible gap today) | area: WEB | related: NET.S16
- DRIFT | js/mock-server.js:480-482 | "jitterInPlace mutates numeric leaves of a flat object" | stale: jitterInPlace now recurses into nested objects (:289-291) | area: WEB | covered-by: WEB.S12

## js/nav.js
- INVAR | js/nav.js:2-3 | "Builds no DOM itself - see SPECIFICATION.md Part H.3 for the full mechanics/visual split this file follows." | H.3 layering (controllers build no DOM) upheld by convention only; no lint rule | area: WEB | related: WEB.T11
- ASSUME | js/nav.js:36 | "defensive only: buildNavDrawer() always sets this on every link it builds" | unreachable branch by stated assumption (low) | area: WEB | -
- LIMIT | js/nav.js:24-31 | "appShellEl.classList.remove(\"nav-open\"); hamburgerEl.setAttribute(\"aria-expanded\", \"false\");" | drawer state is only a class + aria-expanded: no `inert`, no focus move/trap, static aria-label | area: WEB | covered-by: WEB.S16
- LIMIT | js/nav.js:52-56 | "document.addEventListener(\"keydown\", ..." | a document-level Escape listener is added per initNav() call and never removed; safe only because initNav runs once per page load (low) | area: WEB | -

## js/poll-manager.js
- DRIFT | js/poll-manager.js:1-3 vs :11-13 | "every fetch in the app goes through the one shared instance below rather than calling fetch() directly" | the header says every fetch goes through the single-flight queue, while :12-13 and js/app.js:46 / js/definitions.js:240 use fetchWithTimeout() outside it (low) | area: WEB | related: WEB.T03
- MIRROR | js/poll-manager.js:7-8 | "export const DEFAULT_TIMEOUT_MS = 15000;" | client timeout mirrors the server's `outer_cap_s` 15.0 per H.4; the two start at different moments so the client nearly always aborts first | area: WEB | covered-by: WEB.S06
- ASSUME | js/poll-manager.js:10-13 | "so a hung connection is freed and rejected rather than waited on ... need the same never-hang guarantee" | the never-hang guarantee covers headers only: the timer is cleared in `finally` once fetch resolves, and `response.text()` (:63) is unbounded | area: WEB | covered-by: WEB.S05
- PLATFORM | js/poll-manager.js:38,41 | "#queue = Promise.resolve(); ... #activeCount = 0;" | class private fields are a browser-floor dependency | area: WEB | covered-by: WEB.T09
- LIMIT | js/poll-manager.js:43-46 | "get isBusy()" | used only by tests | area: WEB | covered-by: WEB.S18
- ASSUME | js/poll-manager.js:65-66 | "The connection dropped mid-stream, after headers but before the full body arrived" | any body-read rejection is presumed to be a dropped connection (low) | area: WEB | -
- ASSUME | js/poll-manager.js:73-74 | "a truncated/corrupted transmission, or a non-JSON response from something other than this app's own backend" | JSON parse failure attributed to transmission or a foreign responder (e.g. captive-portal/proxy page) (low) | area: WEB | -
- LIMIT | js/poll-manager.js:71 | "body = text.length > 0 ? JSON.parse(text) : null;" | an empty 2xx body resolves as `{ok: true, body: null}` rather than an error; callers must check for null themselves (low) | area: WEB | -
- LIMIT | js/poll-manager.js:83-88 | "const scheduled = this.#queue.then(run, run);" | one global queue for every section: a stalled request blocks all sections; nothing aborts queued requests on a section switch | area: WEB | covered-by: WEB.S07
- ASSUME | js/poll-manager.js:109-111 | "Defensive only: ... kept in case a future caller invokes tick() directly." | unreachable guard by stated assumption (low) | area: WEB | -
- LIMIT | js/poll-manager.js:116-117 | "console.error(\"Poll failed:\", error);" | the loop's only diagnostic is dead because render.js's fetchOnce() never rejects | area: WEB | covered-by: WEB.S11
- LIMIT | js/poll-manager.js:102-131 | "export function startPolling(pollOnce, intervalMs)" | no visibility (hidden-tab) pause and no backoff on repeated failure | area: WEB | covered-by: WEB.S07

## js/render.js
- INVAR | js/render.js:1-3 | "Section controller - the mechanics half of the visual/mechanics split. Builds no DOM itself" | H.3 layering by convention only | area: WEB | related: WEB.T11
- DRIFT | js/render.js:27-29 | "a server-side Number(null) === 0 would turn garbage into a plausible in-range value ... so the backend's own Number() rejects it" | the comment reasons with JavaScript `Number()` semantics for a Python backend that does strict `type()` checks (low) | area: WEB | related: WEB.S03
- LIMIT | js/render.js:26-30 | "const num = Number(rawInputValue); ... return Number.isFinite(num) ? num : rawInputValue;" | whitespace-only input becomes 0; hex and exponent strings pass as numbers; a decimal comma goes as a string | area: WEB | covered-by: WEB.S03
- PLATFORM | js/render.js:33-35 | "A <select>'s own .value is always a string (DOM behavior), even when the option's real value is numeric" | enum values are recovered via `String(option.value) === rawInputValue`; two options whose values stringify equally (e.g. 1 and "1") would be ambiguous (low) | area: WEB | -
- MIRROR | js/render.js:42-45 | "the server's own shaped-error `descr` when present (SPECIFICATION.md Part A.5's `_ERROR_SHAPES`/`_shaped_error_handler` - every 400/404/405/413/500 carries one)" | GET error text relies on the server's shaped-error envelope for exactly those statuses | area: WEB | related: WEB.T04
- DRIFT | js/render.js:61-64 | "Every field kind is sparse-omitted when it matches its resolveFieldValue() baseline and carries no `dispatch` flag." | number/string fields are omitted only when the input is empty (:115-117), never compared to the baseline; a re-typed identical value is sent (low) | area: WEB | related: WEB.T01
- ASSUME | js/render.js:98-100 | "every real subField today is numeric (e.g. lightCmdLED's r/g/b/t), so this doesn't yet need readInputValue()'s own per-kind dispatch" | composite sub-fields are assumed numeric; a future string/enum sub-field would be mistyped. Deferred ("doesn't yet need") | area: WEB | -
- LIMIT | js/render.js:127-130,159 | "const STATUS_SEVERITY = { Invalid: 0, Failed: 1, Valid: 2, Unchanged: 3 };" | any status string outside these four ranks as 4 (least severe), so an unexpected server status can never make a card worse than Unchanged (low) | area: WEB | -
- LIMIT | js/render.js:132-135 | "A submitted-but-unanswered field is treated as Failed ... a known real server-side gap where a settings group's post-write hook raising drops that group's fields" | reconciliation guards a server gap the plan says is fixed; the H.6 citation may be stale | area: WEB | related: WEB.S12
- ASSUME | js/render.js:160-161 | "an empty `result` map on a successful envelope still means the action completed, not that \"nothing changed\" - default to success." | an empty result map is read as success | area: WEB | related: WEB.S02
- LIMIT | js/render.js:164-169 | "for (const [key, status] of Object.entries(results)) {" | per-field colours are set only for fields in the latest result; others keep a previous Apply's colour | area: WEB | covered-by: WEB.S04
- LIMIT | js/render.js:197-200 | "if (putPath === undefined) { return; }" | an Apply on a submit group whose section has no `rest.put` silently does nothing; validateDefinitions() doesn't require it | area: WEB | covered-by: WEB.S10
- LIMIT | js/render.js:202-209 | "Every field kind is sparse-omitted when untouched; only a `dispatch` field always resubmits." | because dispatch toggles in Off are always sent, a card containing one can never reach "Nothing to submit" | area: WEB | covered-by: WEB.S02
- MIRROR | js/render.js:211-213 | "/sensors is the one endpoint whose PUT body nests fields under the sensor's own group key" | body shape and the hard-coded section key "sensors" must mirror the server's /sensors PUT contract and the definitions' section keys | area: WEB | related: WEB.T04
- MIRROR | js/render.js:216-218 | "the backend accepts a JSON int for a float-typed field and coerces it (coerce_numeric(), Part A.8)" | the client relies on server-side int->float coercion | area: WEB | related: WEB.T02
- MIRROR | js/render.js:225-229 | "a malformed body is a clean 200 with res:\"ERR\", a route-level failure a non-2xx carrying the same envelope" | failure detection mirrors src/ envelope conventions | area: WEB | related: WEB.T04
- MIRROR | js/render.js:235-244 | "/status's PUT returns no per-field result for any submit group" | every submitted /status field is shown Valid on any OK envelope, including ResetErrors=false (dispatch Off), which the server treats as a no-op | area: WEB | related: WEB.S02
- LIMIT | js/render.js:247-254 | "a field the server really stored (Valid or Unchanged) becomes the new baseline immediately." | baseline moves to the submitted value, including dispatch toggles, so the next Apply resends them | area: WEB | covered-by: WEB.S01
- SUPPRESS | js/render.js:260-263 | "// eslint-disable-next-line require-atomic-updates" | shipped-code suppression; justified as "`card` is a const DOM reference, never reassigned - no real race" plus the button's `disabled` re-entry guard | area: WEB | -
- LIMIT | js/render.js:219-223 | "pollManager.request(putPath, { method: \"PUT\", headers: { \"Content-Type\": \"application/json\" }, ..." | state-changing PUTs (incl. SystemCmd reboot/bootloader, ResetErrors) carry no authentication or CSRF token; the posture rests on the server side | area: SEC | related: WEB.T08
- SETTLED | js/render.js:264-266 | "legacy only console.error'd here, and this is a deliberate change." | a deliberate divergence from legacy: a failed Apply marks every submitted field failed | area: WEB | -
- LIMIT | js/render.js:296,311,320,325,329 | "grid.querySelector(`[data-group-key=\"${group.key}\"]`)" | selectors interpolate definition keys without `CSS.escape` | area: WEB | covered-by: WEB.S17
- LIMIT | js/render.js:299-312 | "A live poll rebuilds this card from scratch every tick" | the errcount card is rebuilt each poll; expand state is restored but keyboard focus is lost | area: WEB | covered-by: WEB.S08
- LIMIT | js/render.js:321-335 | "Writable groups only refresh their read-only captions/spans in place" | in-place caption refresh reads `groupValues[field.key]` directly, bypassing resolveFieldValue(); baselines stay frozen at first render | area: WEB | covered-by: WEB.S10
- LIMIT | js/render.js:345-349 | "Never rejects - the one place that catches every fetch failure for this section." | swallowing all errors here makes startPolling's console.error dead | area: WEB | covered-by: WEB.S11
- MIRROR | js/render.js:357-368 | "PauseTime is live data under GET /status's \"notification\" sub-key, not in GET /notification's settings-only response (Part A.8)" | the notification section issues a second /status GET per refresh and relies on that server layout and the hard-coded section key "notification" | area: WEB | related: WEB.T04
- LIMIT | js/render.js:377-383 | "if (section.pollGroup === \"live\") {" | "settings" and "none" poll groups behave identically (fetch once) | area: WEB | covered-by: WEB.S18
- ASSUME | js/render.js:386-389 | "Errcount-only groups never reach this helper." | stated precondition of groupValuesFrom() (low) | area: WEB | -
- MIRROR | js/render.js:399-411 | "flatten one level so field keys can address it directly (e.g. \"SGP40_BackupTS\")" | the `${sensorKey}_${fieldKey}` convention and the hard-coded status group key "sensors" must match definitions (wozi `SGP40_*`, dev `UARTLINK_*`) and buildgen/definitions.py; a sensor name containing `_` makes keys ambiguous (low) | area: WEB | related: WEB.T05

## js/templates.js
- INVAR | js/templates.js:1-3 | "Every DOM element this app ever creates is built here, and only here" | H.3 layering by convention only | area: WEB | related: WEB.T11
- INVAR | js/templates.js:6-8 | "never re-exported: the bundler keeps every `export` as written, so a second one would collide once concatenated (SPECIFICATION.md Part H.7's splitting rule)" | no module may re-export another's symbol because scripts/build_website.sh concatenates files; convention only | area: WEB | related: WEB.S14
- LIMIT | js/templates.js:27-28 | "`Length: ${field.minLength ?? 0} to ${field.maxLength ?? \"∞\"} characters`" | the hint says "characters" while server bounds (e.g. WiFi SSID/PW) are UTF-8 bytes (low) | area: WEB | related: WEB.S12
- INVAR | js/templates.js:54-56 | "data-field-key below (which must keep pointing at the specific control - collectGroupBody()/paint() rely on that exact element)" | the data-* hook contract between templates.js and render.js | area: WEB | related: WEB.T11
- LIMIT | js/templates.js:61,85,105,161 | "label.htmlFor = `field-${field.key}`;" | ids not namespaced by group (dev's SampleInterv/FiltCoeff duplicated); labels for readonly/composite fields point at no element | area: WEB | covered-by: WEB.S15
- SETTLED | js/templates.js:91 | "Purely cosmetic self-flip - no network call, safe to wire directly here." | the one behaviour wired in the presentation layer, a stated H.3 exception (low) | area: WEB | related: WEB.T11
- ASSUME | js/templates.js:109-114 | "No value to preselect (SystemCmd is write-only, never returned by GET /system)." | the "Select…" placeholder prevents accidentally submitting the first command; relies on SystemCmd never appearing in GET | area: WEB | -
- LIMIT | js/templates.js:158-164 | "input.type = field.mask === true ? \"password\" : \"text\";" | number fields use a text input; masked inputs lack `autocomplete` | area: WEB | covered-by: WEB.S17
- LIMIT | js/templates.js:215-224, 283 | "function worstErrcountType(entry)" | rollup uses history types, while row colour uses `counter > 0`; the two can disagree | area: WEB | covered-by: WEB.S08
- LIMIT | js/templates.js:245-246 | "entry: errcount[moduleInfo.key] ?? { counter: 0 }," | a module missing from /status errcount (unwired, or a degraded source) renders as a healthy zero row, indistinguishable from "no errors"; SPECIFICATION.md:4502-4504 (H.6) documents this "permanent, reassuring `0`" and makes the per-instance key list the only guard | area: WEB | related: WEB.S09
- SETTLED | js/templates.js:292-293 | "Always rendered, never independently hidden ... (project owner, session 2 follow-up)." | owner decision on history visibility | area: WEB | -
- ASSUME | js/templates.js:303-304 | "No pagination or truncation - realistic history depth is well under 20 entries (project owner, session 2)" | unbounded render justified by an owner-stated history depth | area: WEB | -
- SETTLED | js/templates.js:338-341 | "See SPECIFICATION.md Part H.3's \"One deliberate exception\" note for why this returns `{grid, errorBanner}` directly." | a stated exception to the H.3 contract | area: WEB | related: WEB.S18
- PLATFORM | js/templates.js:347,380 | "mainEl.replaceChildren();" | `replaceChildren` is a browser-floor dependency | area: WEB | covered-by: WEB.T09

## html/index.html
- MIRROR | html/index.html:29-30 | "import { startApp } from \"../js/app.js\";" | source page loads the prototype entry; the build must rewrite this import to the staged production `app.js` (js/main.js) | area: WEB | related: WEB.T06
- DRIFT | html/index.html:40-43 | "scripts/build_website.sh's own \"Inlining\" comment inlines this element straight into index.html" | 4-line `//` block (over the 3-line cap) citing a comment that no longer exists | area: WEB | covered-by: WEB.S19
- MIRROR | html/index.html:44 | "document.getElementById(\"inlined-definitions\")" | the id must match scripts/build_website.sh:64's `id="inlined-definitions"` | area: WEB | related: WEB.T06
- LIMIT | html/index.html:7 | "<link rel=\"icon\" href=\"data:,\">" | empty data-URI favicon hack to suppress a /favicon.ico request; interacts with any future CSP `img-src` (low) | area: WEB | related: WEB.T13
- LIMIT | html/index.html:3-9 | "<head> ... </head>" | no CSP meta tag and no other security headers at page level; the inline `<script type="module">` bootstrap (:29-46) would need a hash/nonce or `unsafe-inline` under any CSP | area: WEB | related: WEB.T13
- LIMIT | html/index.html:13 | "aria-label=\"Open navigation\" aria-expanded=\"false\"" | static aria-label regardless of state | area: WEB | covered-by: WEB.S16
- LIMIT | html/index.html:21 | "<div class=\"nav-backdrop\" id=\"nav-backdrop\"></div>" | clickable backdrop with no role/keyboard affordance (Escape is handled at document level) (low) | area: WEB | related: WEB.S16

## html/style.css
- SETTLED | html/style.css:3 | "dark only redefines tokens under prefers-color-scheme, no manual toggle." | no manual theme toggle, by design; no `color-scheme` declared, so native controls stay light in dark mode | area: WEB | covered-by: WEB.S16
- LIMIT | html/style.css:16,20,22,11 | "--color-success: #1f9d55; ... --color-danger: #d64545; ... --color-warn: #9457c7;" | light-mode status colours/borders below 4.5:1 contrast | area: WEB | covered-by: WEB.S16
- LIMIT | html/style.css:122,141 | "transition: opacity 0.18s ease;" | transitions with no `prefers-reduced-motion` override | area: WEB | related: WEB.T07
- ASSUME | html/style.css:234-237 | ".field:first-of-type {" | relies on the card heading being an `h3` (not a `div`) so the first `.field` div matches `:first-of-type` (low) | area: WEB | -
- LIMIT | html/style.css:261-263 | ".field input[type=\"text\"], .field input[type=\"number\"], .field select {" | `input[type=password]` (masked PW) is unstyled | area: WEB | covered-by: WEB.S16
- ASSUME | html/style.css:273-277 | "grid-template-columns: repeat(4, 1fr);" | the composite grid assumes four sub-fields (lightCmdLED r/g/b/t) (low) | area: WEB | -
- SETTLED | html/style.css:314-316 | "a left accent stripe rather than legacy's full background recolor ... Two levels, as legacy had" | deliberate visual divergence from legacy, keeping legacy's two-level granularity (low) | area: WEB | -
- ASSUME | html/style.css:351-353 | "a device can have 15+ registered modules" | undated module-count figure (wozi has 17, dev 21 errcount modules) (low) | area: WEB | -
- ASSUME | html/style.css:411-413 | "a module can carry 10+ entries" | history-depth figure; compare templates.js:303-304's "well under 20 entries" (low) | area: WEB | -
- LIMIT | html/style.css:427-428 | "\"N\"/\"E\"/\"W\" (no error/error/warning) never render as text, they only pick this pill's color" | colour-only information by design | area: WEB | covered-by: WEB.S16
- SUPPRESS | html/style.css:472-474 | ".hidden { display: none !important; }" | the stylesheet's only `!important`: a utility override that beats every other display rule (low) | area: WEB | -
- PLATFORM | html/style.css:476 | "@media (width >= 640px) {" | media-query range syntax is a browser-floor dependency (stylelint-config-standard enforces this notation) | area: WEB | covered-by: WEB.T09
- PLATFORM | html/style.css:136 | "width: min(280px, 80vw);" | CSS `min()` and `inset` (:117) are browser-floor dependencies (low) | area: WEB | related: WEB.T09

## html/definitions/wozi.json
- DRIFT | html/definitions/wozi.json:1 (whole file) | "wozi/dev keep their hand-written html/definitions/<device>.json" (scripts/build_website.sh:26) | provenance is stated three ways: hand-written (build_website.sh:26-27, SPECIFICATION.md:4405-4406), "generated at build time ... never hand-maintained" (SPECIFICATION.md:5785-5786), "generated *and committed*" (BACKLOG.md:439-440) | area: WEB | covered-by: WEB.S13
- TODO | html/definitions/wozi.json:1 (whole file) | "retiring them is deferred work (SPECIFICATION.md Part L.4)" (scripts/build_website.sh:27) | retiring the hand-written wozi/dev files in favour of generated ones is deferred; tests_js reads them as fixtures | area: WEB | related: WEB.S13
- MIRROR | html/definitions/wozi.json:60-130,147-168,184-186,311-346 | "\"min\": 2, \"max\": 1800" etc. | every hand-written min/max/float/maxLength must match src/ FieldSchema tuples (e.g. NTP_Host maxLength 1024 — BACKLOG.md:439-441; SPECIFICATION.md:2331 "Also update html/definitions/<device>.json") | area: WEB | related: WEB.S13
- LIMIT | html/definitions/wozi.json:72-75 | "\"key\": \"ContMeas\" ... \"defaultValue\": true" | ContMeas is dispatch-only server-side (mock SENSOR_QUIRK_FIELDS) but carries no `dispatch` flag, and GET never reports it, so after a reload the toggle always shows On even when measurement was stopped; H.6 (SPECIFICATION.md:4508-4510) lists ContMeas as dispatch-only while H.4 (:4361) does not — see the cross-list item under tests_js/_put_field_cases.js (low) | area: WEB | related: WEB.S01
- MIRROR | html/definitions/wozi.json:197 | "{ \"value\": \"mempause\", \"label\": \"Pause backups for 5 minutes\" }" | the label hard-codes mempause's fixed 300 s, which lives in src/ system_cmd() (src/asy_webserver_service.py:95-97) | area: WEB | -
- LIMIT | html/definitions/wozi.json:290-293 | "\"description\": \"... Absent/No is a no-op.\", \"dispatch\": true" | with dispatch, "No" is always sent and render.js marks it Valid, so an Apply with the toggle at No reports success while doing nothing | area: WEB | related: WEB.S02
- MIRROR | html/definitions/wozi.json:264-282 | "\"modules\": [ { \"key\": \"WIFI\" ... { \"key\": \"WEBSERVER\" ..." | hand-kept errcount module list must match the loggers the device registers (buildgen/definitions.py:97-115,365-387 generates it; SCD30 has no CFGMGR_ by design) | area: WEB | related: WEB.S13
- MIRROR | html/definitions/wozi.json:6,209 | "\"defaultPollIntervalMs\": 3000 ... \"pollIntervalMs\": 3000" | poll cadence vs the server's measured throughput (~2.2 requests/s) | area: WEB | related: WEB.S07

## html/definitions/dev.json
- DRIFT | html/definitions/dev.json:1 (whole file) | 2-space indent and `—` escapes (Python `json.dump` style) | dev.json is formatted like generator output while wozi.json is hand-formatted; consistent with BACKLOG.md:439-440's "generated *and committed*" and inconsistent with "hand-written" (build_website.sh:26) (low) | area: WEB | covered-by: WEB.S13
- LIMIT | html/definitions/dev.json:194 | "Relative and uncalibrated - a documented placeholder RGB->XYZ matrix, so repeatable and monotonic rather than a colorimeter reading." | ISL29125 CCT is a stated approximation surfaced to users | area: SENS | -
- ASSUME | html/definitions/dev.json:583 | "The switch-back-down point is derived from this - 1/53.3 of it" | user-facing text encodes a driver constant (hysteresis ratio); MIRROR with src/asy_isl29125_driver.py | area: SENS | -
- ASSUME | html/definitions/dev.json:648 | "Nominally 26.667; every real part differs, and the error shows as a step at each range change." | user-facing text encodes the nominal 375/10000 lx range ratio (low) | area: SENS | -
- ASSUME | html/definitions/dev.json:209 | "Not an error - a transient, harmless, always-current status." | Overrange declared harmless (low) | area: SENS | -
- LIMIT | html/definitions/dev.json:548 | "12 bit is ~16x faster and rejects none." | 12-bit resolution rejects no mains flicker, stated limitation (low) | area: SENS | -
- MIRROR | html/definitions/dev.json:964-970 | "UARTLINK_Transfers ... Bench-only - a deployed unit has no such link." | status/sensors key `UARTLINK` must match the server's /status sensors sub-key via render.js's flatten convention | area: WEB | related: WEB.T05
- LIMIT | html/definitions/dev.json (sensors section) | "SampleInterv" and "FiltCoeff" in both BMP3XX and ISL29125 groups | duplicate DOM ids `field-SampleInterv`/`field-FiltCoeff` | area: WEB | covered-by: WEB.S15
- LIMIT | html/definitions/dev.json:305-306 | "Setting this to Off stops continuous measurement ... \"defaultValue\": true" | same ContMeas no-`dispatch` / always-On-after-reload issue as wozi (low) | area: WEB | related: WEB.S01

## package.json
- LIMIT | package.json:10-11 | "\"build:site\": \"scripts/build_website.sh wozi && uv run scripts/_generate_sensortask_modules.py\"" | every `pretest*` hook builds the wozi site only and needs `uv` (Python) on PATH; the other five devices' sites are never built by the web tier | area: WEB | covered-by: WEB.T12
- SUPPRESS | package.json:14,18 | "--exclude \"tests_js/live-backend-put-matrix.test.js\"" | `test:unit` and `test:coverage` deselect the live PUT matrix (it runs only via `test`/`test:put-matrix`); coverage never includes it | area: CI | related: CI.S12
- RISK | package.json:21 | "\"preview\": \"python3 -m http.server 8000\"" | fixed port 8000, serving the repo root on all interfaces | area: SEC | covered-by: CI.S16
- ASSUME | package.json:23-37 | "\"eslint\": \"^10.10.0\", ... \"typescript\": \"^7.0.2\", \"vitest\": \"^5.0.0\"" | every devDependency is a caret range; reproducibility rests on package-lock.json + `npm ci`, unlike pyproject's exact pins for tools with opt-in-to-everything configs | area: CI | related: CI.T04
- PLATFORM | package.json:35 | "\"typescript\": \"^7.0.2\"" | TypeScript 7 (a major line); tests_js/vitest-commands.d.ts's module-vs-script augmentation behaviour was "confirmed directly" against some tsc version and must be re-checked on a TS bump (low) | area: CI | related: CI.T04
- LIMIT | package.json:1-38 | (no `engines` field) | Node version is constrained only by .nvmrc; `@types/node ^26` disagrees with it (low) | area: CI | covered-by: CI.S07

## eslint.config.js
- SETTLED | eslint.config.js:10-12 | "the curated counterpart of ruff's select = [\"ALL\"] - every core rule that catches a real defect or enforces a decision, style-preference bans left out" | deliberate curated rule set, not ALL | area: CI | -
- LIMIT | eslint.config.js:13-119 | "const BUG_CATCHING_RULES = {" | no rule (e.g. `no-restricted-properties`/`no-restricted-syntax`) enforces H.4's "`textContent` only, never `innerHTML`" | area: SEC | covered-by: WEB.S17
- PLATFORM | eslint.config.js:126,138,152,165,178,194 | "ecmaVersion: \"latest\"" | lint accepts any syntax level, so nothing mechanically bounds shipped js/ to a browser floor | area: WEB | related: WEB.T09
- DRIFT | eslint.config.js:108-111 | "poll-manager's \"Poll failed:\" and the live-backend test's skip warning are real signal" | the cited `console.error("Poll failed:")` is unreachable | area: WEB | covered-by: WEB.S11
- INVAR | eslint.config.js:113-118 | "complexity ceilings at the measured maximum, so they gate regression: ratchet DOWN only" | `complexity: 41`, `max-depth: 4`, `max-nested-callbacks: 4`, `max-classes-per-file: 2` are measured maxima; "ratchet down only" is a convention nothing enforces | area: CI | -
- SUPPRESS | eslint.config.js:184-186 | "rules: { ...BUG_CATCHING_RULES, \"no-console\": \"off\" }," | `no-console` disabled for scripts/**/*.mjs (CLI output channel) | area: CI | -
- MIRROR | eslint.config.js:189-190 | "build_website.sh relies on its literal \"../js/app.js\" import (H.8)" | the inline bootstrap's import string in html/index.html:30 is a contract with scripts/build_website.sh's rewrite | area: WEB | related: WEB.T06

## tsconfig.json
- PLATFORM | tsconfig.json:3-6 | "\"target\": \"ES2022\", ... \"lib\": [\"ES2022\", \"DOM\"]," | type-checking assumes an ES2022 + current-DOM runtime (Error `cause`, private fields, `structuredClone`, `replaceChildren`), the de facto browser floor | area: WEB | related: WEB.T09
- ASSUME | tsconfig.json:11-13 | "All of these were verified to hold before being switched on" | undated verification claim for the beyond-strict flags | area: CI | -
- DRIFT | tsconfig.json:14-15 | "skipLibCheck stays TRUE deliberately: the only findings it hides are inside third-party .d.ts files this project does not own." | deliberate setting, but `skipLibCheck` skips every `.d.ts`, including the project's own tests_js/vitest-commands.d.ts that `include` names (:28), so the claim is broader than true (low) | area: CI | -
- DRIFT | tsconfig.json:11-15, 29-35 | "// Everything TypeScript offers beyond `strict`..." | comment blocks of 5 and 7 lines exceed the 3-line cap | area: DOC | covered-by: CI.S10
- MIRROR | tsconfig.json:10-26 vs tsconfig.node.json:16-32 | "\"noUncheckedIndexedAccess\": true, ... \"skipLibCheck\": true" | the strict flag set and its comment are duplicated verbatim across the two configs; kept in sync by hand | area: CI | -
- LIMIT | tsconfig.json:28 | "\"include\": [\"js/**/*.js\", \"tests_js/**/*.js\", \"tests_js/**/*.d.ts\"]" | html/index.html's inline module bootstrap is never type-checked (it passes `HTMLElement | null` values to startApp) (low) | area: WEB | related: WEB.T06

## tsconfig.node.json
- DRIFT | tsconfig.node.json:2-6 vs :34 | "Second, separate tsc invocation for tests_js/_live_twin_command.js and tests_js/_live_matrix_command.js" | `include` also lists scripts/cross_browser_smoke.mjs, which the header does not mention (low) | area: CI | -
- DRIFT | tsconfig.node.json:2-6, 17-21 | "// Second, separate tsc invocation ..." | over-cap comment blocks | area: DOC | covered-by: CI.S10
- PLATFORM | tsconfig.node.json:12 | "\"types\": [\"node\"]," | Node typings come from @types/node ^26 while .nvmrc pins Node 22 | area: CI | covered-by: CI.S07

## vitest.config.js
- WORKAROUND | vitest.config.js:15-19 | "The dev sandbox pre-installs Chromium at this fixed path; CI runners lack it" | uses /opt/pw-browsers/chromium when present instead of the lock-pinned Playwright build; removal trigger: none stated | area: CI | covered-by: CI.S15
- ASSUME | vitest.config.js:29-31 | "covers the longest explicit wait (5000ms, render.test.js) with margin." | the 20000 ms backstop is sized against one test's wait (tests_js/render.test.js:665); a longer wait elsewhere would need it re-sized (low) | area: TEST | related: TEST.T16
- WORKAROUND | vitest.config.js:33-36 | "A `coverage/` directory at the repo root is importable as a namespace package and shadows the real `coverage` distribution" | coverage output renamed to htmlcov_js to avoid shadowing Python's `coverage` in scripts/_render_coverage.py; removal trigger: none stated | area: CI | -
- WORKAROUND | vitest.config.js:37-40 | "The v8 provider re-parses every file V8 reported coverage for as JavaScript, so the JSON ... threw a rolldown parse stack per file" | `exclude: ["**/*.json"]` works around v8/rolldown parse noise; guarded by tests_scripts/test_js_coverage_excludes_json.py; removal trigger: none stated | area: CI | -
- LIMIT | vitest.config.js:42-46 | "instances: [{ browser: \"chromium\" }]," | the unit and live tiers run Chromium only; other engines only via the separate cross-browser smoke | area: WEB | related: WEB.T09
- LIMIT | vitest.config.js:32-41 | "coverage: {" | no coverage thresholds; JS coverage is advisory | area: CI | related: CI.S12

## .htmlvalidate.json
- SUPPRESS | .htmlvalidate.json:7-9 | "\"require-sri\": [\"error\", { \"target\": \"crossorigin\" }]" | SRI required only for cross-origin resources (same-origin script/style exempt) — a narrowed rule (low) | area: WEB | related: WEB.T08
- LIMIT | .htmlvalidate.json:1-10 with package.json:19 | "\"lint:html\": \"html-validate \\\"html/**/*.html\\\"\"" | only the source page is validated, never the built index.html with inlined CSS/JSON/bundle (low) | area: WEB | related: WEB.T06

## .stylelintrc.json
- (no items: extends stylelint-config-standard with no overrides or disabled rules)

## .nvmrc
- PLATFORM | .nvmrc:1 | "22" | major-only Node pin; the exact 22.x installed floats (CLAUDE.md records v22.23.2 on 2026-09-12) | area: CI | related: CI.S07

## tests_js/_live_twin_command.js
- WORKAROUND | tests_js/_live_twin_command.js:1-3 | "Vitest's own browser-mode `page` has no API for navigating to an external origin - vitest-dev/vitest#7875" | live tests drive a raw Playwright page through the Commands API; removal trigger: none stated (upstream issue) | area: TEST | -
- MIRROR | tests_js/_live_twin_command.js:12-13 (and _live_matrix_command.js:15-16) | "\"ports\", \"unix\", \"build-standard\", \"micropython\"" | hard-coded Unix-port build directory must match toolchain/setup_toolchain.py's `build-standard` (the non-settrace binary, CLAUDE.md) (low) | area: TEST | -
- ASSUME | tests_js/_live_twin_command.js:14-17 | "package.json's own \"pretest\"/\"pretest:coverage\" hooks generate it fresh there, via buildgen, before this spawns." | a bare `vitest run` (no npm hook) boots whatever stale or missing build/generated_src exists | area: TEST | related: SCR.T01
- INVAR | tests_js/_live_twin_command.js:19-22 | "Clear of every fixed port and band tests/, tests_scripts/, scripts/ and digital_twin/ bind (the full map is in SPECIFICATION.md Part E.1)" | fixed port 19481 (19482 for the matrix) kept disjoint by convention only | area: TEST | covered-by: TEST.T14
- MIRROR | tests_js/_live_twin_command.js:67-70 | "\"\", // in-memory only - see digital_twin/README.md's \"FRAM persistence\" section for this convention" | empty state path = in-memory, a digital_twin/ CLI convention | area: TWIN | -
- WORKAROUND | tests_js/_live_twin_command.js:75-78 | "stdout ignored rather than piped: an unconsumed pipe keeps Node's event loop alive" | twin stdout is discarded, so nothing scans it for `MemoryError`/`memory allocation failed` | area: TEST | covered-by: TEST.T18
- SUPPRESS | tests_js/_live_twin_command.js:81-84 | "proc.on(\"error\", () => { /* no-op by design, per the comment above */ });" | spawn errors swallowed; failure surfaces only via the readiness timeout | area: TEST | -
- MIRROR | tests_js/_live_twin_command.js:93-95 | "run_generic_integration.py's own graceful-shutdown path (FRAM/SCD30 flush) only runs on KeyboardInterrupt ... same reasoning as scripts/_digital_twin_ci_suite.py's own _shutdown()" | SIGINT-based shutdown contract shared with the twin CI suite | area: TEST | -
- WORKAROUND | tests_js/_live_twin_command.js:97-99 | "a pending timer keeps Node's event loop alive - which showed up as Vitest's \"something prevents Vite server from exiting\"" | kill timer cleared explicitly | area: TEST | -
- ASSUME | tests_js/_live_twin_command.js:119-121 | "Delegated to buildgen rather than re-parsed here ... package.json's \"pretest\" hook already needs uv on PATH." | live tests shell out to `uv run python` for buildgen's max_connections | area: TEST | covered-by: GEN.T15
- LIMIT | tests_js/_live_twin_command.js:144-149, 225-230 | "skipped: true, reason: `MicroPython Unix port not built at ...`" | live tests return a skip result that the calling test turns into a pass | area: TEST | covered-by: TEST.S19
- RISK | tests_js/_live_twin_command.js:151-154, 231 | "config/ is the one thing that still persists to a fixed path by default (run_generic_integration.py exposes no --cfg-path flag)" | deletes the repo-level digital_twin/config before each live run | area: TEST | covered-by: SCR.S09
- LIMIT | tests_js/_live_twin_command.js:218-220 vs :233-235 | "the tier exercising the connection ceiling from a real browser" vs "Half the ceiling, so it is never exceeded" | the concurrent-tab test never reaches `max_connections`; it rests on the stated assumption that a tab holds one slot, two while releasing | area: TEST | related: WEB.T16
- SUPPRESS | tests_js/_live_twin_command.js:38,46,197,200,247 | "// eslint-disable-next-line no-await-in-loop -- deliberate sequential polling" | 5 no-await-in-loop disables, each with a reason | area: TEST | -
- SUPPRESS | tests_js/_live_twin_command.js:43-45, 212, 260 | "} catch { // Not up yet - keep polling. }" / "catch(() => { /* best-effort teardown ... */ })" | swallowed exceptions with a comment (readiness poll, page teardown) | area: TEST | -
- LIMIT | tests_js/_live_twin_command.js:56-62 | "\"--module\", \"sensortask_wozi\", ... \"--device\", \"wozi\"," | live tier boots wozi only | area: WEB | covered-by: WEB.T12

## tests_js/_live_matrix_command.js
- ASSUME | tests_js/_live_matrix_command.js:9-12 | "Reused (not hand-duplicated) so this module knows the *exact* expected caption text" | expected captions are computed with the same `formatFieldValue()` under test, so a formatting defect cannot fail the live matrix | area: TEST | related: TEST.T17
- MIRROR | tests_js/_live_matrix_command.js:14-116 vs tests_js/_live_twin_command.js:11-117 | "Same reasoning as tests_js/_live_twin_command.js's own stdio choice" | TOOLCHAIN_DIR/MICROPYTHON_BIN/MICROPYPATH/HOST, sleep, waitUntilServing, spawnTwin, stopTwin are copy-pasted between the two harnesses | area: TEST | related: TEST.T08
- RISK | tests_js/_live_matrix_command.js:22-23, 136 | "this harness's twin runs alongside that file's (19481) in one `npm test` run." | both harnesses `rmSync` the same digital_twin/config; if the two live files run concurrently one can delete the other twin's config mid-run | area: TEST | related: SCR.S09
- ASSUME | tests_js/_live_matrix_command.js:172-174 | "Vitest dispatches Commands API calls strictly sequentially from one file's await chain, so the race the rule guards cannot happen." | justification for four `require-atomic-updates` disables (:159,164,178,183) | area: TEST | -
- SUPPRESS | tests_js/_live_matrix_command.js:159,164,178,183 | "// eslint-disable-next-line require-atomic-updates -- see comment above" | 4 disables on module-level mutable state | area: TEST | -
- SUPPRESS | tests_js/_live_matrix_command.js:43,51,201,203,239,244,264,269 | "// eslint-disable-next-line no-await-in-loop" | 8 no-await-in-loop disables with reasons | area: TEST | -
- SUPPRESS | tests_js/_live_matrix_command.js:48-50, 158, 177 | "} catch { // Not up yet - keep polling. }" | swallowed exceptions (readiness poll, best-effort page close) | area: TEST | -
- LIMIT | tests_js/_live_matrix_command.js:202-204 | "out[p] = await res.json();" | baseline GETs don't check HTTP status or envelope before use (low) | area: TEST | -
- ASSUME | tests_js/_live_matrix_command.js:218-221 | "js/main.js's selectSection() always tears down and rebuilds fresh regardless" | remount proof depends on this main.js behaviour | area: TEST | -
- LIMIT | tests_js/_live_matrix_command.js:307-308 | "composite/readonly/dispatch-only fields aren't driven through this generic matrix (see SPECIFICATION.md Part H.7)" | lightCmdLED, SystemCmd, PauseTime, ResetErrors have no live-UI coverage | area: TEST | related: WEB.T10
- ASSUME | tests_js/_live_matrix_command.js:320-322 | "just worth a short event-loop beat." | fixed `sleep(50)` before reading toggle/select state (low) | area: TEST | related: TEST.T04
- MIRROR | tests_js/_live_matrix_command.js:356 | "\"Nothing to submit - no fields were changed.\"" | literal UI string duplicated from js/render.js:207 (also live-backend-put-matrix.test.js:166) (low) | area: TEST | -

## tests_js/_put_field_cases.js
- MIRROR | tests_js/_put_field_cases.js:11-14 | "export const DISPATCH_ONLY_KEYS = new Set([\"SystemCmd\", \"PauseTime\", \"lightCmdLED\", \"ResetErrors\"]);" | yet another hand-kept "special field" list; the lists disagree: H.4 (SPECIFICATION.md:4361) = SystemCmd/PauseTime/lightCmdLED/ResetErrors + `dispatch=true` tags (SGPResetVOC, ISLCalibrate), "derive the set from the tags, never from this list alone"; H.6 (:4508-4510) adds ContMeas, omits ISLCalibrate; definitions `dispatch: true` = SystemCmd, SGPResetVOC, ISLCalibrate, ResetErrors; js/mock-server.js:22 SENSOR_QUIRK_FIELDS = ForceCalRef/ContMeas/SGPResetVOC/ISLCalibrate (+ :244's own list); tests_js/mock-server-put-matrix.test.js:26 adds PW; tests_js/live-backend-put-matrix.test.js:21 = ForceCalRef/ContMeas/SGPResetVOC | area: WEB | related: WEB.S01
- ASSUME | tests_js/_put_field_cases.js:11-12 | "covered by dedicated tests in mock-server.test.js and render.test.js" | dispatch-only keys are covered by the mock tier only, never by the live twin | area: TEST | related: WEB.T10
- ASSUME | tests_js/_put_field_cases.js:55-56 | "measurements has no PUT; status's only field (ResetErrors) is dispatch-only" | section list hard-coded; a new writable status field would be silently skipped (low) | area: TEST | -

## tests_js/vitest-commands.d.ts
- DRIFT | tests_js/vitest-commands.d.ts:1-6, 8-17, 19-23 | "// Ambient module augmentation for the custom Vitest browser commands ..." | three `//` paragraphs of 6, 10 and 5 prose lines exceed CLAUDE.md's 3-line cap, which applies to all code incl. tests_js; not in the plan's cap findings | area: DOC | related: CI.T08
- MIRROR | tests_js/vitest-commands.d.ts:16-17 | "These return types are kept in sync by hand with each file's own `@returns` JSDoc" | command signatures duplicated by hand from the two harness files | area: TEST | -
- PLATFORM | tests_js/vitest-commands.d.ts:19-24 | "without at least one top-level import/export of its own, TS treats this file as an ambient *script* ... (confirmed directly ...)" | relies on tsc's module-vs-script augmentation semantics; re-check on a TypeScript major bump | area: CI | -

## tests_js/live-backend.test.js
- LIMIT | tests_js/live-backend.test.js:1-3, 13-16, 41-44 | "Skips itself with a clear message if the MicroPython toolchain/frozen website aren't built yet, rather than failing the suite." | skip-and-pass via `console.warn` + `return` | area: TEST | covered-by: TEST.S19
- ASSUME | tests_js/live-backend.test.js:20-23 | "\"Valid\" or \"Unchanged\" both mean the backend accepted the write" | tolerance for either result | area: TEST | -
- RISK | tests_js/live-backend.test.js:31-33 | "Known harmless quirk: this file prints \"close timed out after 10000ms\" ... appears to miss Vitest's fast path" | accepted teardown warning; cause stated as "appears to", unverified | area: TEST | -
- LIMIT | tests_js/live-backend.test.js:46-48 | "The tab count is derived from the build's own max_connections, so this bites harder the moment that ceiling is raised." | tabs = floor(ceiling/2) (_live_twin_command.js:235), so the ceiling itself is never exercised | area: TEST | related: WEB.T16
- LIMIT | tests_js/live-backend.test.js:19, 50 | "expect(result.deviceName).toContain(\"wozi\");" | wozi only | area: WEB | covered-by: WEB.T12

## tests_js/live-backend-put-matrix.test.js
- DRIFT | tests_js/live-backend-put-matrix.test.js:17-21 | "Three documented backend quirks ... Part H.7 has the full account." | H.7 (SPECIFICATION.md:4517-4630) has no such account; the quirks note is H.4 (:4367-4370). ISLCalibrate is absent from the list (wozi-only matrix) (low) | area: DOC | -
- ASSUME | tests_js/live-backend-put-matrix.test.js:55-56 | "this one file is 567s of the web tier's 578s" | single dated measurement (SPECIFICATION.md:880-881, 2026-09-19) | area: CI | -
- LIMIT | tests_js/live-backend-put-matrix.test.js:58 | "collectPutFieldCases(\"wozi\", ..." | live PUT matrix covers wozi only | area: TEST | covered-by: TEST.S19
- SUPPRESS | tests_js/live-backend-put-matrix.test.js:65-66 | "it.skip(`live-backend PUT matrix (skipped: ${boot.reason})`" | the whole matrix collapses to one skipped placeholder without the toolchain | area: TEST | covered-by: TEST.S19
- LIMIT | tests_js/live-backend-put-matrix.test.js:80-83 | "the real backend's \"Unchanged\" detection doesn't reliably fire (SPECIFICATION.md Part H.7)" | a stated real-backend unreliability tolerated by the test; the cited H.7 contains no such statement | area: REST | related: WEB.T01
- SETTLED | tests_js/live-backend-put-matrix.test.js:131-132 | "An empty-string current value has no \"resubmit\" gesture" | consequence of H.4's accepted gap "An empty string can't be set via this UI for any field" (SPECIFICATION.md:4365) | area: WEB | -
- LIMIT | tests_js/live-backend-put-matrix.test.js:134-137 | "PW reads back as the fixed \"********\" overlay ... resubmitting it is not a no-op probe but a new password the backend would persist" | masked fields are never resubmit-probed; confirms a PUT of the mask would be stored | area: NET | related: NET.S16
- PLATFORM | tests_js/live-backend-put-matrix.test.js:185-187 | "SCD30's TempOffs has a real 0.01° hardware truncation (SPECIFICATION.md, near the ForceCalRef/AmbPres notes)" | probe values rounded to 2 dp because of a chip resolution fact (SPECIFICATION.md:243); vague pointer | area: SENS | -
- LIMIT | tests_js/live-backend-put-matrix.test.js:252-253 | "minLength === 1's own \"too short\" probe is the empty string ... so only minLength 2+ has a real probe" | too-short rejection untested for minLength-1 fields | area: TEST | -
- WORKAROUND | tests_js/live-backend-put-matrix.test.js:271-273 | "vitest derives a screenshot filename - and NTP_Host's maxLength 1024 made that ENAMETOOLONG, wedging a run" | tests parametrised over lengths to keep names short; removal trigger: none stated | area: TEST | -
- LIMIT | tests_js/live-backend-put-matrix.test.js:283-299 | "flipping to the opposite state renders Valid" / "selecting option %s renders Valid" | no live rejection probes for toggle/enum (wrong type, unknown option) (low) | area: TEST | related: WEB.T10

## tests_js/mock-server-put-matrix.test.js
- DRIFT | tests_js/mock-server-put-matrix.test.js:18-21 | "This matches none of dev's real groups today ... stays for a future dev-unique sensor (owner, 2026-09-08)." | ISL29125 in DEV_UNIQUE_GROUPS is a real dev-only group now; SHTC3/MPRLS name no driver in src/ | area: TEST | -
- MIRROR | tests_js/mock-server-put-matrix.test.js:23-26 | "const GET_READBACK_QUIRK_FIELDS = new Set([\"ForceCalRef\", \"ContMeas\", \"SGPResetVOC\", \"ISLCalibrate\", \"PW\"]);" | part of the disagreeing special-field lists (see tests_js/_put_field_cases.js) | area: TEST | -
- DRIFT | tests_js/mock-server-put-matrix.test.js:153-154 | "e.g. FiltCoeff's min 0 and special -1" | dev's ISL29125 FiltCoeff is min -1.0 with special -1.0; BMP3XX FiltCoeff is an enum (low) | area: TEST | -
- ASSUME | tests_js/mock-server-put-matrix.test.js:269-271 | "Every currently-declared numeric enum's own real options are whole numbers" | still true (BMP3XX, ISL29125 Resolution/Range/IrCompOffset) but unchecked (low) | area: TEST | -

## tests_js/mock-server.test.js
- MIRROR | tests_js/mock-server.test.js:247-249 | "Mirrors _dispatch_notification_pause(): PauseTime is a runtime action, checked 0-3600 ... follows coerce_numeric()" | mock contract pinned to src/asy_webserver_service.py:530 | area: WEB | related: WEB.T04
- DRIFT | tests_js/mock-server.test.js:273-275 vs tests_js/render.test.js:702-704, 725-727 | "reports \"Failed\" through coerce_numeric()" vs "fails inside the callback's own cast" / "a missing one raises KeyError there" | two different stated server mechanisms for lightCmdLED's "Failed"; one relies on a KeyError from the callback (low) | area: REST | related: REST.S10
- MIRROR | tests_js/mock-server.test.js:325-327 | "this readback always reports 400, never whatever was just applied." | stronger than src/asy_scd30_driver.py:506's "always returns 400 after a power cycle"; mock and live matrix (ALWAYS_REMOUNTS_AS) both assume always-400 (low) | area: SENS | -
- LIMIT | tests_js/mock-server.test.js:342-343 | "there's no real I2C bus here to ever produce the real driver's \"Failed\"" | ContMeas "Failed" path untested in the mock tier | area: WEB | related: WEB.T15
- MIRROR | tests_js/mock-server.test.js:349-350, 360-361, 367-368 | "ContMeas has no schema entry on the real backend" / "A command-only, repeatable trigger (SPECIFICATION.md C.5.2.1)" / "SGPResetVOC is a special-alone schema field, deliberately excluded from get_dict_cfg()" | mock GET omissions pinned to src/ schema facts | area: WEB | related: WEB.T04
- LIMIT | tests_js/mock-server.test.js:545-546 | "the real backend's own gap: overall envelope still reports OK" | asserts a gap H.6 (SPECIFICATION.md:4513-4515) says is closed | area: WEB | covered-by: WEB.S12
- SUPPRESS | tests_js/mock-server.test.js:462,464 | "// eslint-disable-next-line no-await-in-loop -- see the comment above" | 2 disables | area: TEST | -

## tests_js/render.test.js
- LIMIT | tests_js/render.test.js:5-6 | "the mock server's fetch has randomized latency (js/mock-server.js)" | render tests poll against a nondeterministic mock | area: TEST | covered-by: TEST.T14
- SUPPRESS | tests_js/render.test.js:17-18 | "// eslint-disable-next-line no-await-in-loop" | 1 disable (reason on the line above) | area: TEST | -
- LIMIT | tests_js/render.test.js:85-87, 469-471 | "Deliberately not the real SCD30 key \"ContMeas\": mock-server.js special-cases that exact name" | the mock's behaviour is keyed on literal field names, so fixtures must avoid them; also cites "Part H.7" where the quirks note is H.4 (low) | area: TEST | -
- ASSUME | tests_js/render.test.js:403-405 | "switching earlier would hang waitFor's own real-timer polling loop." | fake-timer ordering constraint (low) | area: TEST | related: TEST.T04
- MIRROR | tests_js/render.test.js:418-420 | "_put_status() never builds a `result` dict, so /status's PUT structurally cannot report a per-field outcome" | pinned to src/asy_webserver_service.py:380 `_put_status` | area: WEB | -
- DRIFT | tests_js/render.test.js:679-681 | "a server-side Number(null) === 0 made it look like a deliberate in-range value." | same JS-semantics-for-a-Python-server reasoning as js/render.js:27-29 (low) | area: WEB | related: WEB.S03
- ASSUME | tests_js/render.test.js:883-885 | "No real definitions file nests a readonly field inside a submit:true group in a \"live\" section today" | path exercised by a synthetic fixture only | area: TEST | -
- LIMIT | tests_js/render.test.js:1016-1018 | "A real server-side gap (Part H.6): a settings group's post-write hook raising drops that group's fields" | contradicts H.6's current text | area: WEB | covered-by: WEB.S12

## tests_js/templates.test.js
- DRIFT | tests_js/templates.test.js:41-42 | "Real shape (src/sensortask_wozi.py's _gmtimestruct_to_dict())" | cites a removed file | area: WEB | covered-by: WEB.S21
- ASSUME | tests_js/templates.test.js:48-49 | "no driver in src/ rounds any output" | same cross-tree claim as js/field-format.js:33-35 | area: WEB | -
- MIRROR | tests_js/templates.test.js:399-401 | "Real backend shape (src/print_log.py's get_log()): no per-entry timestamp exists ... (project owner, session 2 follow-up)" | pinned to src/print_log.py:180; owner decision that type is never shown as text | area: WEB | -
- INVAR | tests_js/templates.test.js:502-570 | "XSS safety (standing guideline: textContent only, never innerHTML)" | test covers hostile labels/values/names only, not keys that reach selectors/ids/dataset | area: SEC | covered-by: WEB.S17

## tests_js/definitions.test.js
- MIRROR | tests_js/definitions.test.js:295 | "await vi.advanceTimersByTimeAsync(15000); // fetchWithTimeout()'s own DEFAULT_TIMEOUT_MS" | literal copy of js/poll-manager.js:8 (low) | area: TEST | -

## tests_js/definitions-mockdata-coverage.test.js
- DRIFT | tests_js/definitions-mockdata-coverage.test.js:14-16 | "Mirrors js/render.js's own groupValuesFrom(), duplicated deliberately ... If the two ever disagree this test goes red" | a private copy does not follow render.js changes, so a disagreement would not turn this test red (low) | area: TEST | related: TEST.T08
- LIMIT | tests_js/definitions-mockdata-coverage.test.js:73-74 | "Only readonly fields: a writable one legitimately falls back to defaultValue" | writable fields' presence in mockdata is not checked | area: TEST | related: WEB.T15
- LIMIT | tests_js/definitions-mockdata-coverage.test.js:6-7 | "import wozi ... import dev" | wozi/dev only; generated devices have no mockdata | area: WEB | covered-by: WEB.T12

## tests_js/main.test.js
- DRIFT | tests_js/main.test.js:47-50, 127-129 | "build_website.sh's \"Inlining\" note" / "scripts/build_website.sh's own \"Inlining\" comment" | cites a comment that no longer exists (same dangling pointer as html/index.html:40-41) | area: DOC | related: WEB.S21
- ASSUME | tests_js/main.test.js:144-145 | "scripts/build_website.sh always writes valid JSON" | stated build guarantee (low) | area: WEB | -
- LIMIT | tests_js/main.test.js:11-12 (and tests_js/app.test.js:11-12) | "startApp() has no stop handle exposed to callers, so a \"live\" section here would keep polling" | startApp() cannot be stopped; entry-point tests avoid live sections (low) | area: WEB | -

## tests_js/app.test.js
- LIMIT | tests_js/app.test.js:11-12 | "startApp() has no stop handle exposed to callers" | see main.test.js item (low) | area: WEB | -

## tests_js/poll-manager.test.js
- ASSUME | tests_js/poll-manager.test.js:108-110 | "the device has very few available sockets, SPECIFICATION.md Part H.4" | rationale for the hung-connection timeout (low) | area: WEB | -

## tests_js/nav.test.js
- (no items)

## Coverage
| file | comment/doc lines read | items |
| --- | --- | --- |
| js/app.js | 21 (full file read) | 6 |
| js/definitions.js | 108 (full file read) | 18 |
| js/field-format.js | 19 (full file read) | 6 |
| js/main.js | 20 (full file read) | 3 |
| js/mock-server.js | 164 (full file read) | 41 |
| js/nav.js | 19 (full file read) | 4 |
| js/poll-manager.js | 42 (full file read) | 12 |
| js/render.js | 152 (full file read) | 30 |
| js/templates.js | 76 (full file read) | 14 |
| html/definitions/dev.json | 0 comments; full structure + every `description` string read | 9 |
| html/definitions/wozi.json | 0 comments; full file read | 8 |
| html/index.html | 4 (`//` block :40-43; full file read) | 7 |
| html/style.css | 24 (full file read) | 13 |
| tests_js/_live_matrix_command.js | 126 (full file read) | 12 |
| tests_js/_live_twin_command.js | 65 (full file read) | 16 |
| tests_js/_put_field_cases.js | 35 (full file read) | 3 |
| tests_js/app.test.js | 10 | 1 |
| tests_js/definitions-mockdata-coverage.test.js | 43 | 3 |
| tests_js/definitions.test.js | 23 (+ :1-30, :200-300 code) | 1 |
| tests_js/live-backend-put-matrix.test.js | 83 (full file read) | 11 |
| tests_js/live-backend.test.js | 16 (full file read) | 5 |
| tests_js/main.test.js | 20 | 3 |
| tests_js/mock-server-put-matrix.test.js | 87 (+ :1-45 code) | 4 |
| tests_js/mock-server.test.js | 77 | 7 |
| tests_js/nav.test.js | 9 | 0 |
| tests_js/poll-manager.test.js | 25 | 1 |
| tests_js/render.test.js | 191 (+ :1-25 code) | 8 |
| tests_js/templates.test.js | 94 (+ :495-570 code) | 4 |
| tests_js/vitest-commands.d.ts | 67 (full file read) | 3 |
| package.json | 0 (full file read) | 6 |
| eslint.config.js | 68 (full file read) | 7 |
| tsconfig.json | 12 (`//` blocks; full file read) | 6 |
| tsconfig.node.json | 10 (`//` blocks; full file read) | 3 |
| vitest.config.js | 39 (full file read) | 6 |
| .htmlvalidate.json | 0 (full file read) | 2 |
| .stylelintrc.json | 0 (full file read) | 0 |
| .nvmrc | 0 (full file read) | 1 |

Notes: the helper misses `//` comments in .html and .json(c) files, so html/index.html and both tsconfigs were read in full by hand. Suppression sweep: shipped code (js/, html/) carries exactly one lint suppression (js/render.js:262 `require-atomic-updates`) and one CSS `!important` (html/style.css:473); no `@ts-ignore`/`@ts-expect-error` anywhere in the partition; no `innerHTML`/`eval`/`new Function` in js/ (tests_js/templates.test.js:440 sets `innerHTML` only as test setup). tests_js/ carries 20 `eslint-disable-next-line` directives (no-await-in-loop ×16, require-atomic-updates ×4; by file: _live_twin_command 5, _live_matrix_command 12, mock-server.test 2, render.test 1) and one `it.skip` placeholder.

## Totals per kind
| kind | count |
| --- | --- |
| LIMIT | 88 |
| MIRROR | 60 |
| ASSUME | 44 |
| DRIFT | 25 |
| SUPPRESS | 14 |
| PLATFORM | 13 |
| SETTLED | 12 |
| INVAR | 12 |
| WORKAROUND | 7 |
| RISK | 5 |
| TODO | 1 |
| OPENQ | 0 |
| **total** | **281** (77 covered-by, 113 related, 91 new) |

## Top 10
1. tests_js/_put_field_cases.js:11-14 (MIRROR) — six hand-kept "special field" lists (H.4, H.6, definitions `dispatch` flags, mock SENSOR_QUIRK_FIELDS, mock-matrix GET_READBACK_QUIRK_FIELDS, live ALWAYS_REMOUNTS_AS) disagree on ContMeas/ISLCalibrate/ForceCalRef/PauseTime; H.4 says derive from tags.
2. tests_js/live-backend-put-matrix.test.js:80-83 (LIMIT) — test tolerates "the real backend's Unchanged detection doesn't reliably fire", citing an H.7 statement that doesn't exist.
3. js/render.js:235-244 + html/definitions/wozi.json:290-293 (MIRROR/LIMIT) — every /status submit shows Valid, including ResetErrors="No" (dispatch always sent) which the server treats as a no-op.
4. js/render.js:219-223 (LIMIT, SEC) — reboot/bootloader/ResetErrors PUTs carry no auth or CSRF token.
5. tests_js/_live_matrix_command.js:9-12 (ASSUME) — live matrix computes expected captions with the formatter under test (oracle = SUT).
6. html/definitions/wozi.json + dev.json provenance (DRIFT) — "hand-written" vs "generated, never hand-maintained" vs "generated and committed"; dev.json is formatted like generator output (covered-by WEB.S13).
7. js/mock-server.js:251-254, js/render.js:132-135, tests_js/render.test.js:1016-1018, tests_js/mock-server.test.js:545-546 — client and tests still model the dropped-result server gap that H.6 (SPECIFICATION.md:4513-4515) says is fixed (covered-by WEB.S12).
8. tests_js/_live_twin_command.js:218-235 + tests_js/live-backend.test.js:46-48 (LIMIT) — the "connection ceiling" browser test runs half the ceiling by design, so it never reaches the ceiling.
9. html/definitions/wozi.json:72-75 (LIMIT) — ContMeas has no `dispatch` flag and no GET readback, so after a reload the UI shows On even after measurement was stopped.
10. tests_js/mock-server.test.js:325-327 vs src/asy_scd30_driver.py:506 (MIRROR) — mock and live matrix assume ForceCalRef always reads 400; the driver comment says only "after a power cycle".
