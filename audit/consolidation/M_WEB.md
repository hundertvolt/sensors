# A-C merge WEB (HEAD dd06040)

Scope: CLUSTERS.md "## WEB" — `js/` (9 files at HEAD plus `js/api-contract.js`, `js/shell.js` born by actions),
`tests_js/` (16 files at HEAD plus the files actions create), `eslint.config.js`, `package.json`, `package-lock.json`,
`tsconfig.json`, `.nvmrc`. Taken here because no cluster lists them and every action on them is a website action
(GEN's precedent with `buildgen/limits.py`): `mockdata/` (`dev.json`, `wozi.json`, new `samples.json`),
`vitest.config.js`, `tsconfig.node.json` and the new `tsconfig.base.json` (Gaps, item 1). Every file was read whole at
HEAD dd06040 (the `tests_js/*.test.js` files read whole for the sites actions name and their fixtures; the
`package-lock.json` diff is generated, never hand-written).

Inputs merged: the site index (85 action IDs), a grep of every `audit/actions/*.md` Site/Change/Blast/Why slot for these
paths (116 further IDs, 67 of them blast-only), AC_NOTES 1-39, the finished merges M_SRC_CORE, M_SRC_SENS, M_SRC_NET,
M_GEN and M_TEST_UNIT, and their "Gaps for other clusters".

Unit order used for staging: U0 < U1 < … < U8 < U9 < U10 < … < U37 (numeric); a SUPP_owner_0930 action lands in the
unit it supplements (A.S0930.20's website half with U23, its Depends); SDEP actions in U0's dependency refresh, before
every B1 action (AC_NOTES 34-second).

## Product end state the website matches (from the finished merges)

- **Routes** (M.SRC_NET.112 `ROUTES`): GET `/measurements`, `/sensors`, `/networking`, `/system`, `/status`,
  `/notification`; PUT `/sensors`, `/networking`, `/system`, `/status`, `/notification`. Anything else: 404/405
  shaped envelope (M.SRC_NET.112 `_ERROR_STATUSES`).
- **Envelope codes** (M.SRC_CORE.073, `src/asy_api_response.py` `_STANDARD_CODES`): 0 "Command executed", 1 "Invalid
  JSON request", 400 "Bad request", 404 "Not found", 405 "Method not allowed", 413 "Payload too large", 500 "Internal
  server error"; `res` "OK" for code 0, else "ERR"; an uncatalogued code's `descr` is "Unknown error".
- **Result words** (M.SRC_CORE.045, `src/asy_config_manager.py`): `VALID`/`UNCHANGED`/`INVALID`/`FAILED` =
  "Valid"/"Unchanged"/"Invalid"/"Failed".
- **PUT outcomes**: an unknown key, an unknown sensor or a non-object sensor entry answers "Invalid" (for a sensor: the
  word in place of its field map) (M.SRC_NET.120); `PUT /status`: `ResetErrors: true` → "Valid" (all sources reset) or
  "Failed", any other `ResetErrors` value → "Invalid", every other key → "Invalid" (M.SRC_NET.123); `SystemCmd`: exactly
  the five words `reboot`, `bootloader`, `mempause`, `resetconfig`, `erasefram` (whole-value equality; "Failed" when the
  command is refused) (M.SRC_NET.121/.112); `LightCmdLED` (members `R`,`G`,`B` int 0-255, `T` float 0.5-60.0): a
  non-object, a missing or extra member, or a value outside its schema → "Invalid", a busy LED → "Failed"
  (M.SRC_NET.122); `PauseTime` 0-3600 int, out of range "Invalid" (M.SRC_NET.122).
- **Options and labels** (M.GEN.015): `SystemCmd` options `reboot`, `bootloader`, `mempause` ("Pause backups for 5
  minutes"), `resetconfig` "Reset to defaults", `erasefram` "Erase FRAM"; no confirmation key (OR121.a (2), OR122).
- **`/status` keys** (M.GEN.008/.014): networking `IP`, `IPv4`, `Subnet`, `Gateway`, `DNS`, `RSSI`, `NTPSynced`,
  `NTPLastSyncAge`, `NTPLastSync` (epoch), `HTTPDropped`, `WifiTS` (epoch), `Connected`, `Mode`, `WifiUptime`; system
  `SysUptime`, `BootSignature`, `ResetReason` (codes 0-10, 20; M.SRC_CORE `_RR_*`: 1 power-on, 7 config reset, 8 FRAM
  erased), `MemFree`, `MemPaused`, `LastTaskEnd` (`null` or `{"Task": "<logger>.<starter>", "Uptime": <s>}`),
  `LocalTime`, `UTCTime` (`null` until NTP sync), `UnixTime` (`null` until NTP sync); time structs keyed `Year`,
  `Month`, `MDay`, `Hour`, `Minute`, `Second`, `Weekday`, `Yearday`; maintenance `sensors.<INSTANCE>.<Field>`; a guarded
  source that failed is `{"error":"unavailable"}` (M.SRC_NET.123).
- **Definitions** (M.GEN.014-.018, .046): every device's `definitions.json` generated; field keys renamed per A.U10.40
  (`LightCmdLED`, `NTPHost`, `NTPOffset`, `NTPInterval`, `TempOffset`, `MeasInterval`, `SampleInterval`, `ResetVOC`,
  `Calibrate`, `LEDWifiOn`, …); new FieldDef keys `format` (`epoch`, `gmtimestruct`, `lasttaskend`), `codes`,
  `codeTones`, `byteLength`, `shape`, `clearable`, `ignoredWhenSet`, `resolution`, `alwaysExecuted`, `statusPath`,
  `specialValues` with `null`; no `defaultValue`; errcount groups carry `codes: {E, W}`; `DNSSRV` sits in a Networking
  errcount group; `PauseTime` carries `dispatch` and `statusPath`; the System section carries a Build group
  (`FirmwareVersion`, `WebsiteVersion`, `BuildDate`, `path: ["build", <key>]`). Shape values on tags:
  `hostLabel` (Hostname), `countryCode` (Country), `hostName` (NTPHost), `ipv4List` (DNSFallback) (M.SRC_NET.043/.073;
  Gaps item 2 for M.GEN.046's value set).

## js/api-contract.js (new)

### M.WEB.001 One JS module mirrors src/'s wire facts
- **From**: A.U23.25 (module, result words, `isUnavailable()`), A.U23.24 (`GMTIME_KEYS`), A.U23.11 (`isUnavailable()`
  semantics), A.U19.16 (JS half of the shared result words), A.U10.40 (time-struct key names), A.U36.044 (read: the H.6.1
  wire table names this module).
- **Site**: new `js/api-contract.js`.
- **Change**: header (3 lines) "Wire facts mirrored from src/ (SPECIFICATION.md Part G's mirror obligation): the four
  PUT result words, the degraded-source marker and the time-struct keys. tests_scripts/test_js_api_mirrors.py pins each
  against its Python source." Exports, each with a one-line `//` comment citing its live source: `export const VALID =
  "Valid";`, `UNCHANGED = "Unchanged"`, `INVALID = "Invalid"`, `FAILED = "Failed"` (`src/asy_config_manager.py`'s
  constants of the same names); `export const GMTIME_KEYS = ["Year", "Month", "MDay", "Hour", "Minute", "Second"];`
  (`_gmtimestruct_to_dict()` in the generated module, emitted by `buildgen/codegen.py`); `export function
  isUnavailable(value)` — `true` exactly when `value` is a non-null, non-array object whose only own key is `error` with
  the value `"unavailable"` (`src/asy_webserver_service.py` `_write_guarded()`/`_write_errcount_entry()`); JSDoc `@param
  {unknown} value` / `@returns {boolean}`. No other export; `COUNTER_CAP` is not here (M.WEB.040: the mock is its only
  user and is never staged). The module imports nothing.
- **Resolved**: A.U23.24 wrote the lowercase keys "renamed with A.U10.40 in the same change"; A.U10.40 is U10, earlier
  than U23, so the keys are born PascalCase.
- **Unit**: U23.
- **Depends**: A.U19.16 / M.SRC_CORE.045 (constants exist in `src/asy_config_manager.py`), A.U10.37 (module names),
  A.U10.40 (keys).
- **Blast carried by**: importers `js/render.js` (M.WEB.020), `js/field-format.js` (M.WEB.012), `js/mock-server.js`
  (M.WEB.040); production bundle closure gains the module (A.U23.38, SCR — derived from imports); L0
  `tests_scripts/test_js_api_mirrors.py` (A.U23.25/.24/.26/.27, TSC); SPEC G.2 mirror catalog and H.2 module list
  (A.U23.25 Docs, A.U36.517 (3), SPEC); H.6.1 row 1 key casing (Gaps item 4, SPEC).
- **Kind**: code

## js/poll-manager.js

### M.WEB.002 One bounded, abortable, single-flight request path
- **From**: A.U23.01 (startup loads through the queue; `fetchWithTimeout` export goes), A.U23.02 (body read inside the
  timeout), A.U23.03 (abort signal), A.U23.37 (`isBusy`/`#activeCount` and the `DEFAULT_TIMEOUT_MS` export go), A.U8.04
  (`web.outer_cap_s` tag), A.U5.05 (read: the value equals `_DEFAULT_OUTER_CAP_S`), A.U36.503 (4) (header/JSDoc
  pointers), A.U19.06 (read: unaffected).
- **Site**: `js/poll-manager.js:1-92` (header, `DEFAULT_TIMEOUT_MS`, `fetchWithTimeout()`, `class PollManager`,
  `pollManager`).
- **Change**: header `:1-5` keeps its three lines ("Single-flight request coordinator - every fetch in the app goes
  through the one shared instance below … See SPECIFICATION.md Part H.4's "Poll coordination" row for why, and for the
  per-request timeout's own rationale."). `:7-8` → `/** Per-request timeout; see the "Per-request timeout value" row of
  SPECIFICATION.md Part H.4. */` / `// @tunable web.outer_cap_s = 15000` / `const DEFAULT_TIMEOUT_MS = 15000;` (no
  `export`). `fetchWithTimeout()` → module-private `async function fetchTextWithTimeout(url, init, timeoutMs, signal)`
  returning `{ok, status, text}`, JSDoc one prose line "fetch() bounded by one timeout covering the whole request, body
  included." plus `@param {string} url`, `@param {RequestInit | undefined} init`, `@param {number} timeoutMs`, `@param
  {AbortSignal | undefined} signal`, `@returns {Promise<{ok: boolean, status: number, text: string}>}`: one
  `AbortController` for the timeout; the fetch signal is `signal === undefined ? controller.signal :
  AbortSignal.any([controller.signal, signal])`; `fetch()` and `response.text()` are awaited inside one `try` whose
  `finally` clears the timer; a timeout abort rejects `Error("Request to <url> timed out after <n>ms")`, a caller abort
  rethrows the `AbortError` unchanged, any other failure during the body read rejects `Error("Connection to <url> was
  interrupted while reading the response", {cause})` (today's text). `class PollManager` keeps only `#queue`;
  `request(url, init, timeoutMs = DEFAULT_TIMEOUT_MS, signal = undefined)` JSDoc gains `@param {AbortSignal}
  [signal]`; its queued `run` first checks `signal?.aborted` and then rejects `new DOMException("Aborted",
  "AbortError")` without fetching; else awaits `fetchTextWithTimeout(...)` and parses the text exactly as `:69-76` today
  (same two comments, same "was not valid JSON (likely a corrupted or truncated transmission)" message). The queue
  advance (`:83-88`) is unchanged. `export const pollManager = new PollManager();` stays.
- **Resolved**: A.U23.01's one-line JSDoc text is A.U23.02's (the function is renamed there); A.U36.503 (4)'s two
  pointer edits are folded into this rewrite (the "Per-request timeout value" row exists at HEAD, SPEC:4371), so no U36
  stage remains. A.U8.04 tags `export const`; A.U23.37 drops `export` — end state carries the tag on the non-exported
  constant.
- **Unit**: U23. Stage U8: A.U8.04 adds the `// @tunable web.outer_cap_s = 15000` line above `:8` (needed by U8's
  register check, A.U8.02); U23 writes the rest.
- **Depends**: A.U8.01/A.U8.02 (tag grammar).
- **Blast carried by**: callers `js/definitions.js` (M.WEB.010), `js/app.js` (M.WEB.031), `js/render.js` (M.WEB.020),
  `js/shell.js` (M.WEB.025); `tests_js/poll-manager.test.js` (M.WEB.051), `tests_js/definitions.test.js` (M.WEB.053);
  `tests/test_website_build_integration.py:123` bundle marker `function fetchWithTimeout` → `function
  fetchTextWithTimeout` or derived from the banner (A.U23.02/A.U23.38, TEST_UNIT/SCR);
  `tests_scripts/test_request_timeout_ceiling.py:67` regex `export const` → `const` (A.U23.37, TSC); Part N row
  `web.outer_cap_s` site `js/poll-manager.js — 15000` (A.U8.04, SPEC); SPEC H.4 rows (A.U36.503, SPEC).
- **Kind**: code

### M.WEB.003 One poll loop: visibility pause, capped back-off, one failure path
- **From**: A.U23.04 (visibility), A.U23.05 (`onError`, back-off, one-shot sections), A.U35.46 (1) (no guard in
  `tick()`), A.U23.06 (read: the shell's device watch uses the same loop), A.U8.18 (read: callers
  pass `web.poll_interval_ms`), A.U8.21 (read: no harness budget lives here).
- **Site**: `js/poll-manager.js:94-132` `startPolling()`.
- **Change**: new module constant after `DEFAULT_TIMEOUT_MS`: `/** Longest wait between retries of a failing poll. */`
  / `// @tunable web.poll_backoff_max_ms = 60000` / `const POLL_BACKOFF_MAX_MS = 60000;`. Typedef in the module:
  `@typedef {{isHidden: () => boolean, onChange: (cb: () => void) => () => void}} Visibility` (exported for JSDoc
  importers only through `import("./poll-manager.js").Visibility`). `export function startPolling(pollOnce, intervalMs,
  options = {})` with `@param {() => Promise<void>} pollOnce`, `@param {number} intervalMs`, `@param {{visibility?:
  Visibility, onError?: (error: unknown) => void, stopAfterSuccess?: boolean}} [options]`,
  `@returns {() => void}`; JSDoc prose (≤ 3 lines): "Self-scheduling poll loop: the next tick is scheduled only after
  pollOnce() settles, `intervalMs` later, or after a failure min(intervalMs * 2^(k-1), POLL_BACKOFF_MAX_MS) for the
  k-th consecutive failure; nothing runs while the page is hidden, and one tick runs on becoming visible." Behaviour:
  `visibility` defaults to an always-visible source (`isHidden: () => false`, `onChange: () => () => {}`); `tick()` has
  no `stopped` guard at its head (A.U35.46 (1): every caller of `tick()` is the first call, the scheduled timeout or the
  visibility resume, each cancelled by `stop()`); `await pollOnce()` inside `try`: on success the failure count resets
  to 0 and `stopAfterSuccess` ends the loop (no further timer, the
  visibility subscription released); on a rejection `onError?.(error)` runs (no `console.error` here — `"Poll failed:"`
  goes) and the count increments; afterwards, unless stopped, a timer is armed only when `!visibility.isHidden()`; a
  `visibility.onChange` listener arms one immediate tick when the page becomes visible and no tick is in flight or
  scheduled, and clears the pending timer when it becomes hidden. The returned stop function sets `stopped`, clears the
  timer and calls the unsubscribe function `onChange` returned.
- **Resolved**: A.U23.04 adds `visibility` as the third positional parameter and A.U23.05 `onError` as the fourth;
  A.U23.05's one-shot sections need a third input — the three are merged into one options object (the end of a failure
  episode, which A.U23.06's watch needs, is tracked by the section itself, M.WEB.020, since the post-Apply refresh runs
  outside this loop) (agent decision D1; D.10 "config objects over long parameter lists"). A.U23.05's
  "n-th consecutive failure" is pinned to its own test sequence 3000, 6000, 12000, …: the first failure keeps
  `intervalMs` (k = 1 → 2^0). A.U35.46 (1) co-lands with A.U23.04/.05 (its own Depends: "A-C merges into their final
  text").
- **Unit**: U23 (A.U35.46 (1) folded in; no U35 stage).
- **Depends**: M.WEB.002; A.U8.01/A.U8.02 (tag grammar).
- **Blast carried by**: callers `js/render.js` (M.WEB.020), `js/shell.js` (M.WEB.025); `tests_js/poll-manager.test.js`
  (M.WEB.051); `eslint.config.js:108-111` comment (M.WEB.070); Part N row `web.poll_backoff_max_ms` (A.U23.05 Docs,
  SPEC); SPEC H.8 `:4735-4737` "Poll failed:" sentence (A.U23.05 doc, SPEC); H.4 rows (A.U36.503, SPEC).
- **Kind**: code

## js/definitions.js

### M.WEB.004 Typedefs carry every generated key; comments name the flag classes
- **From**: A.U6.17 (4) (`alwaysExecuted`, flag comment), A.U6.19 (4) (`format` epoch), A.U32.06 (`lasttaskend`
  member), A.U6.20 (3) (`SpecialValue.value` null), A.U6.27 (3) (`codes` on FieldDef and ErrcountGroup), A.U23.20
  (`codeTones`), A.U6.28 (2) (`byteLength`), A.U6.29 (3)/A.U6.30/A.U10.41/A.U18.10 (`shape` values), A.U23.17
  (`clearable`), A.U23.18 (`statusPath`), A.U23.23 (`ignoredWhenSet`), A.U23.49 (`resolution`), A.U23.16
  (`defaultValue` goes), A.U6.06 (`MockSamples` typedef), A.U10.40 (read: typedefs name no renamed key), M_SRC_SENS GAP-12
  (`defaultValue` also on `Calibrate`; goes with the grammar key).
- **Site**: `js/definitions.js:1-56` (header typedef block, the four inline comments).
- **Change**: header prose `:2-4` unchanged. Typedefs: `SpecialValue` → `{value: number|string|null, meaning:
  string}`; `FieldDef` → `{key, label, unit?, kind: "readonly"|"number"|"string"|"enum"|"toggle"|"composite",
  description?, min?, max?, minLength?, maxLength?, mask?, options?, specialValues?, subFields?, onLabel?, offLabel?,
  format?: "gmtimestruct"|"epoch"|"lasttaskend", float?, resolution?: number, dispatch?: boolean, alwaysExecuted?:
  boolean, path?: string[], statusPath?: string[], decimals?, byteLength?: boolean, shape?:
  "hostLabel"|"countryCode"|"hostName"|"ipv4List", clearable?: boolean, ignoredWhenSet?: string, codes?: Record<string,
  string>, codeTones?: Record<string, "good"|"neutral"|"warn">}` (no `defaultValue`); `ErrcountGroup` gains `codes?: {E:
  Record<string, string>, W: Record<string, string>}`; `MockDeviceData` unchanged in shape; new `MockSamples` =
  `{measurements: Record<string, Record<string, unknown>>, sensorsConfig: Record<string, Record<string, unknown>>,
  networkingConfig: Record<string, unknown>, systemConfig: Record<string, unknown>, notificationConfig: Record<string,
  unknown>, status: {networking: Record<string, unknown>, system: Record<string, unknown>, sensors: Record<string,
  Record<string, unknown>>, notification: Record<string, unknown>}, errcount: Record<string, {counter: number, history:
  {num: number, type: "N"|"E"|"W"}[]}>}`. Inline comments: `:44-46` (`float`) unchanged; `:48-49` (errcount history)
  unchanged; `:51-53` → "// dispatch?: true and alwaysExecuted?: true mark the two never-"Unchanged" classes
  (SPECIFICATION.md Part H.4); / // neverUnchanged() below reads them - never a key list."; `:55-56` (`defaultValue`)
  deleted.
- **Resolved**: A.U23.16 removes `defaultValue` while A.U6.17/.19/.27/.28/.29 extend the same typedef — all applied
  (same resolution as M.GEN.046). `SpecialValue.value` gains `string` beyond A.U6.20's `number|null` because the schema's
  string special (`PW` `""`, `src/asy_wifi_service.py:46`) is what A.U6.28 asks the mock to keep accepting; the
  definitions carry it only once GEN emits string specials (Gaps item 3). `lasttaskend` joins the union per A.U32.06
  ("the `format` union in `js/definitions.js:13`").
- **Unit**: U32 (A.U32.06 latest). Stages: U6 (A.U6.06/.17/.19/.20/.27/.28/.29/.30), U18 (`hostName`/`ipv4List` with
  A.U10.41's PUT check landing in U18, M.SRC_NET.045, and A.U18.10), U23 (A.U23.16/.17/.18/.20/.23/.49), U32
  (`lasttaskend`).
- **Depends**: M.GEN.046/.017 (the generator emits these keys).
- **Blast carried by**: every consumer of the types (`tsc` both passes, M.WEB.073); `tests_scripts/test_definitions_js_mirrors.py`
  and the shape corpus (A.U6.16, TSC); SPEC H.5 FieldDef list (A.U36.515, SPEC).
- **Kind**: code

### M.WEB.005 Constants, the flag predicate and the value resolver
- **From**: A.U23.37 (`SUPPORTED_SCHEMA_MAJOR` loses `export`), A.U6.16 (1) (`MAX_DECIMALS`), A.U23.09
  (`MAX_POLL_INTERVAL_MS`), A.U6.17 (4) (`neverUnchanged()`), A.U23.16 (`resolveFieldValue()` without the default),
  A.U23.19 (read: maintenance fields resolve through `path`), A.U23.18 (read: `statusPath` resolved by the renderer,
  M.WEB.020).
- **Site**: `js/definitions.js:58-94` (`SUPPORTED_SCHEMA_MAJOR`, the `websiteVersion` comment, `resolveFieldValue()`).
- **Change**: `/** The only schema major version this build of the renderer understands. */` / `const
  SUPPORTED_SCHEMA_MAJOR = 1;`; new `// Number#toFixed's own ceiling: a larger value would throw a RangeError in the
  card.` / `const MAX_DECIMALS = 100;` (the `:213-214` comment's content moves here) and `// setTimeout's own ceiling; a
  larger delay fires at once.` / `const MAX_POLL_INTERVAL_MS = 2 ** 31 - 1;` (unique top-level names, SPEC H.2's
  splitting rule). `:61-63` (`websiteVersion`) unchanged. New `export function neverUnchanged(field)` — `return
  field.dispatch === true || field.alwaysExecuted === true;` — JSDoc "True for the two classes the server never answers
  "Unchanged" (SPECIFICATION.md Part H.4)." with `@param {FieldDef} field` / `@returns {boolean}`.
  `resolveFieldValue(field, currentValues)`: the `path` walk is unchanged; the last line → `return value;`; JSDoc first
  paragraph → "A field's current value: the `path` walk for a nested body, else `currentValues[field.key]`; `undefined`
  when GET reported none. Callers use this instead of reading `currentValues[field.key]` directly, so rendering and
  change-comparison never drift apart." (the second paragraph `:70-72` stays).
- **Resolved**: A.U6.16 (2) pins `export const SUPPORTED_SCHEMA_MAJOR` by regex; A.U23.37 (later) drops the `export`
  and moves that regex to `const` (its own Change) — end state non-exported.
- **Unit**: U23. Stage U6: `MAX_DECIMALS` hoisted (A.U6.16), `neverUnchanged()` (A.U6.17).
- **Depends**: A.U6.17's flags in the generated definitions (M.GEN.015/.017).
- **Blast carried by**: `neverUnchanged()` importers `js/mock-server.js` (M.WEB.040), `tests_js/_put_field_cases.js`
  (M.WEB.060), `tests_js/live-backend-put-matrix.test.js` (M.WEB.062); `resolveFieldValue()` callers `js/render.js`
  (M.WEB.020), `js/templates.js` (M.WEB.014), `tests_js/definitions-mockdata-coverage.test.js` (M.WEB.057),
  `tests_js/definitions.test.js:242-253` (M.WEB.053); `tests_scripts/test_definitions_js_mirrors.py` regexes
  (A.U6.16/A.U23.37, TSC); the no-`defaultValue` grammar (M.GEN.046, M.SRC_SENS.072, SCD30 tag A.U23.16 — SRC_SENS).
- **Kind**: code

### M.WEB.006 The validator rejects every malformed shape, naming where
- **From**: A.U23.10 (non-object groups/fields, key/label/kind, composite, duplicates, writable-without-put, split for
  the ceiling), A.U23.09 (upper bound on both poll intervals), A.U6.16 (3) (`decimals` via `MAX_DECIMALS`), A.U6.19 (4)
  (`format`), A.U6.27 (3) (`codes` blocks), A.U23.20 (`codeTones`), A.U6.28 (2) (`byteLength`), A.U6.29 (3)/A.U6.30
  (`shape`), A.U23.17 (`clearable`), A.U23.18 (`statusPath`), A.U23.23 (`ignoredWhenSet`), A.U23.49 (`resolution`),
  A.U5.18 (ceiling pinned), A.U6.08 (read: every device's generated definitions must pass).
- **Site**: `js/definitions.js:96-219` `validateDefinitions()`, `validateFieldHints()`.
- **Change**: `export function validateDefinitions(data)` keeps the top-level checks (`schemaVersion` semver + major,
  `device.id`, `landingSection` string, `sections` non-empty array, `landingSection` matches a key) and gains: every poll
  interval (`defaultPollIntervalMs`, a section's `pollIntervalMs`) "must be a positive number of at most 2147483647 ms"
  (`0 < v <= MAX_POLL_INTERVAL_MS`; the `:124-125` comment keeps its reason); duplicate section keys → "`<where>`.key
  "<k>" duplicates sections[<i>]"; it delegates per section to new private `validateSection(section, where,
  problems)`: today's key/label/`rest.get`/`pollGroup`/`pollIntervalMs` checks, then per group `validateGroup(group,
  where, section, problems)`: a group that is not a non-null object → "`<where>` is not an object" and skip; key/label
  strings; duplicate group keys within the section, naming both indices; `kind: "errcount"` → `modules` array of
  `{key: string, label: string}`, `codes` (when present) an object with `E` and `W` objects mapping strings to strings,
  else "`<where>`.codes must map E and W to code descriptions"; a field group → `fields` array, `submit: true` while
  `section.rest.put` is not a string → "`<where>` is writable but its section has no rest.put", duplicate field keys
  naming both indices, and per field `validateField(field, where, group, problems)`: not a non-null object → "is not an
  object"; `key` string, `label` string, `kind` one of the six (each missing/unknown one its own problem); `composite` →
  `subFields` an array, each validated by `validateField`; then the hint checks of `validateFieldHints()` (renamed
  `validateHints`, kept private): `path` (unchanged rule), `decimals` (`0..MAX_DECIMALS` integer), `format` ∈
  {`gmtimestruct`, `epoch`, `lasttaskend`} on `readonly` only, `specialValues` an array of `{value, meaning: string}`,
  `codes` an object of string → string, `codeTones` keys ⊆ `codes` keys and values ∈ {`good`, `neutral`, `warn`},
  `byteLength`/`clearable` booleans on a `string` field, `shape` ∈ {`hostLabel`, `countryCode`, `hostName`, `ipv4List`}
  on a `string` field, `statusPath` a non-empty array of non-empty strings on a `readonly` or `number` field,
  `ignoredWhenSet` a string naming another field of the same group, `resolution` a positive finite number on a `number`
  field, `alwaysExecuted` a boolean. Each message names its `where` path. No function exceeds the ESLint `complexity`
  ceiling (M.WEB.070).
- **Resolved**: A.U23.10 lists the U23 hint keys and A.U6.27-.30 the U6 ones in the same `validateFieldHints()` — one
  function holds them; A.U10.41/A.U18.10 add `hostName`/`ipv4List` to A.U6.29's mechanism (no separate validator change
  named; the value set follows the tags, M.SRC_NET.043).
- **Unit**: U32 (`lasttaskend` joins the `format` set, A.U32.06). Stages: U6 (A.U6.16/.19/.27/.28/.29/.30), U18
  (`hostName`, `ipv4List`), U23 (A.U23.09/.10/.17/.18/.20/.23/.49 and the split).
- **Depends**: M.WEB.004, M.WEB.005; A.U6.16's shared corpus file (TSC).
- **Blast carried by**: `loadDefinitions()` (M.WEB.007); every device's generated definitions pass (A.U6.08,
  M.WEB.056); `tests_js/definitions.test.js` (M.WEB.053); `tests_js/definitions-shape-corpus.test.js` and
  `tests_scripts/definitions_shape_cases.json` gain one case per rejection (A.U6.16/A.U23.10, M.WEB.055 and TSC);
  `_shape_problems()` mirror (A.U6.16/A.U23.09/.10, TSC); `js/templates.js:158` "number or string" fallthrough sees no
  unknown kind (M.WEB.014); SPEC H.4 "Definitions validation" row (A.U36.510 (2), SPEC); complexity ceiling
  (M.WEB.070).
- **Kind**: code

### M.WEB.007 Definitions load through the queue
- **From**: A.U23.01 (`loadDefinitions()` through `pollManager.request()`), A.U6.05/A.U6.07 (read: callers' paths).
- **Site**: `js/definitions.js:42, :221-257` (import, `loadDefinitions()`).
- **Change**: `:42` → `import { pollManager } from "./poll-manager.js";`. The fetch branch `:239-251` → `const
  response = await pollManager.request(path);` / `if (!response.ok) { throw new Error(\`Failed to fetch ${path}: HTTP
  ${response.status}\`); }` / `data = response.body;` — the "was not valid JSON (likely a corrupted or truncated
  transmission)" message now comes from `request()`'s parse branch (M.WEB.002), so `:244-250` and its comment go. The
  inlined branch, its comment and the validation tail are unchanged.
- **Resolved**: —
- **Unit**: U23.
- **Depends**: M.WEB.002.
- **Blast carried by**: callers `js/main.js` (M.WEB.030), `js/app.js` (M.WEB.031); `tests_js/definitions.test.js:255-297`
  (M.WEB.053).
- **Kind**: code

## js/field-format.js

### M.WEB.012 Timestamps as ages, special values as text, checked time structs, the task-end format
- **From**: A.U23.21 (epoch ages, special-value text, `context.deviceNowS`), A.U23.24 (`GMTIME_KEYS`, "invalid time
  value"), A.U32.06 (`lasttaskend` handler), A.U6.19 (read: until U23 `epoch` falls through to `String(value)`), A.U6.13
  and A.U36.544 (1) (the `:27` comment), A.U10.06 (read: `TS` `null` before NTP sync renders "—"), A.U10.40 (time-struct
  keys), A.U23.22 (read: `UnixTime` has no `format`), A.U23.32 (read: the live matrix stops importing this module).
- **Site**: `js/field-format.js:1-40`.
- **Change**: header → "Pure field-value formatting with no DOM dependency: templates.js puts its text into the page.
  / See SPECIFICATION.md Part H.8.1." (2 lines; the Node-harness reason goes, below). `:5-7` comment → "// A narrow
  local shape: the formatter reads only these members; a real FieldDef satisfies it structurally." and the typedef
  gains `specialValues?: {value: unknown, meaning: string}[]`. `import { GMTIME_KEYS } from "./api-contract.js";`.
  `export function formatFieldValue(field, value, context = { deviceNowS: null })` with `@param {{deviceNowS: number |
  null}} [context]`, in this order: (1) `field.format === "epoch"` and `(field.specialValues ?? []).find((s) => s.value
  === value)` → that special's `meaning` (so `null` → "None since boot" and the shared no-timestamp value → "No
  timestamp", A.U6.20/A.U15.18); (2) `undefined`/`null` → "—"; (3) `mask` → eight "•"; (4) `enum` → option label or
  `String(value)`; (5) `gmtimestruct` → when `value` is a non-null object and each `GMTIME_KEYS` member is a finite
  integer, `Y-MM-DD hh:mm:ss` read through `GMTIME_KEYS` (comment "// Real shape: the generated module's
  _gmtimestruct_to_dict() (buildgen/codegen.py); Weekday/Yearday unused."), else "invalid time value"; (6)
  `lasttaskend` → when `value` is an object with a string `Task` and a finite integer `Uptime`, `` `${Task} at uptime
  ${Uptime} s` ``, else "invalid value"; (7) `epoch` → a non-number passes to (9); `context.deviceNowS === null` →
  "age unknown"; `age = deviceNowS - value`; `age < -5` → "clock mismatch"; else with `a = Math.max(age, 0)`: `a < 120`
  → `` `${a} s ago` ``, `a < 7200` → `` `${Math.floor(a / 60)} min ago` ``, `a < 172800` → `` `${Math.floor(a / 3600)} h
  ago` ``, else `` `${Math.floor(a / 86400)} d ago` ``; (8) `decimals` (unchanged, its 3-line comment kept); (9)
  `String(value)`.
- **Resolved**: A.U6.13 (`sensortask_<device>` wording) and A.U36.544 (1) ("the function's current home, grep in
  `src/`") rewrite the same comment; the function is emitted by `buildgen/codegen.py` (M.GEN.008), not in `src/` —
  that home is named. The header's "so a Node-context test harness can reuse it" is no longer true once A.U23.32 moves
  `_live_matrix_command.js` and the live matrix test to the independent `_expected_display.js` (adherence: comments
  state the current state, CLAUDE.md). The `lasttaskend` display text is not worded by A.U32.06 ("in the existing
  style") — agent decision D2.
- **Unit**: U32 (A.U32.06). Stages: U6 (A.U6.13 comment — superseded by this text at U23), U23 (everything but (6)).
- **Depends**: M.WEB.001; M.GEN.014 (`format` values, specials in the definitions).
- **Blast carried by**: callers `js/templates.js` (M.WEB.014/.015, passes `context`); `tests_js/templates.test.js`
  formatter cases (M.WEB.058); SPEC H.2 module list and H.8.1 (the Node-reuse reason goes; Gaps item 4); SPEC H.4
  "Timestamps" row (A.U23.21 Docs, SPEC).
- **Kind**: code

## js/templates.js

### M.WEB.013 Header and import comment state the current bundling rule
- **From**: A.U23.37 (`buildField` loses `export`; read), A.U23.38 (read: the stager rejects re-exports and duplicate
  exports), A.U36.544 (6) (manual pass: a Part pointer must hold its claim).
- **Site**: `js/templates.js:1-16`.
- **Change**: header `:1-4` unchanged. `:6-8` → "// formatFieldValue() is imported for internal use only, never
  re-exported: the stager rejects `export … from` and a name / // exported twice (SPECIFICATION.md Part H.2's splitting
  rule). Callers import it from ./field-format.js." (2 lines). Imports: `resolveFieldValue` from `./definitions.js`,
  `formatFieldValue` from `./field-format.js`. Typedef lines unchanged.
- **Resolved**: HEAD cites "Part H.7's splitting rule"; the rule is H.2's ("Splitting a module", SPEC:4325), which
  A.U36.517 (5) rewrites to the stager's rejection list — the pointer and the reason follow (adherence: a pointer says
  what it claims, G9/R12).
- **Unit**: U23 (the stager, A.U23.38, lands there).
- **Depends**: A.U23.38 (SCR).
- **Blast carried by**: SPEC H.2 "Splitting a module" (A.U36.517 (5), SPEC).
- **Kind**: code

### M.WEB.014 Field markup: index ids, bound labels, unset toggles, codes, clear and warning cues
- **From**: A.U23.40 (index ids, `CSS.escape`), A.U23.43 (1)(3) (labels, `aria-labelledby`, composite group,
  `autocomplete`), A.U23.16 (unset toggle), A.U23.17 (Clear button), A.U23.23 (warning), A.U23.20 (2)(3) (code value
  button, `CalLight` tone text), A.U23.21 (`title` instant, context), A.U23.11 (unavailable text), A.U23.37 (`buildField`
  private), A.U23.36 (read: masked input starts empty — holds), A.U6.28 (4) (byte hint), A.U6.29 (3) (host-label hint),
  A.U6.30 (read: the Country hint is its tag description), A.U23.49 (resolution hint), A.U6.20/A.U23.21 (specials shown
  as text in place), M_SRC_SENS GAP-12 (`Calibrate` dispatch toggle with no GET value).
- **Site**: `js/templates.js:18-174` (`buildFieldDescription()`, `buildField()`).
- **Change**: `buildFieldDescription(field)` joins with " · ", in this order: number range (unchanged text); string
  length "Length: <min> to <max> characters" plus ", at most <max> bytes (UTF-8)" when `field.byteLength`; "Resolution:
  <resolution>" plus " <unit>" when `field.resolution` is set; "letters, digits and '-' only" when `field.shape ===
  "hostLabel"`; the `specialValues` entries "<value> = <meaning>" for a `number` field only (a readonly field shows the
  meaning in place, M.WEB.012); the description. `function buildField(field, currentValue, editable, fieldId, display)`
  (no `export`; `fieldId` = `field-<groupIndex>-<fieldIndex>`, `display` = `{deviceNowS: number | null, unavailable:
  boolean, siblingLabel: string | undefined}`): wrapper as today (`data-field-wrapper-key` = the key, its 3-line
  comment kept). Labels: a control with an id (number/string input, select, toggle button) gets `label.field-label`
  with `htmlFor = fieldId`; a readonly value and a composite get `span.field-label` with id `${fieldId}-label`, the unit
  span inside it as today. Readonly/non-editable: the value element carries `data-field-key` and `aria-labelledby`;
  `display.unavailable` → text "unavailable"; a field with `codes` and no `codeTones` → `button.field-value.code-value`
  (`type="button"`, `aria-expanded="false"`, text = the number), whose click shows/hides one `p.code-description`
  after it with "<n>: <codes[n]>" or "No description for code <n>"; a field with `codeTones` → `span.field-value` with
  text "<codes[n]> " and a `span.code-number` "(<n>)", and `data-code-tone` = `codeTones[n]` (no tone attribute for an
  unknown code, which shows "(<n>)" alone); `format: "epoch"` with a finite number that is no special → `title` =
  `new Date(value * 1000).toISOString()`; otherwise `formatFieldValue(field, currentValue, display)`. Toggle: `id =
  fieldId`; `field.alwaysExecuted === true` with `currentValue === undefined` → `data-value="unset"`,
  `aria-pressed="mixed"`, text "—"; else as today (`Boolean(currentValue)`, so a dispatch toggle with no GET value, e.g.
  `Calibrate`, shows Off exactly as with HEAD's `defaultValue=false`); the click cycles unset → true → false → true …
  and keeps its comment. Enum: `id = fieldId`, placeholder rule and its two comments unchanged. Composite: the grid gets
  `role="group"` and `aria-labelledby`; sub-inputs keep their wrapping `label`. Number/string: `id = fieldId`; a masked
  field gets `type="password"` and `autocomplete="new-password"`; placeholder and caption through
  `formatFieldValue(field, currentValue, display)`; a writable string field with `clearable` gets
  a `button` with classes `action-button clear-button` (the existing button look, no new CSS) "Clear"
  (`type="button"`, `data-clear-for = fieldId`) after the input; a field with
  `ignoredWhenSet` gets `p.field-warning` with `data-shown="false"` and text "Ignored: <display.siblingLabel> is set."
  after the caption. Every DOM element is created here only.
- **Resolved**: A.U6.30 "hint mirrors it" is met by the tag description it rewrites ("Two uppercase letters (ISO 3166-1
  alpha-2), e.g. DE.", M.SRC_NET.073), which the hint already shows — no second text. GAP-12 (M_SRC_SENS): the owner
  question it suggests needs none — A.U23.14/A.U23.15 already settle a dispatch toggle as "Off, sent only when On" and
  OR94 keeps the look, so `Calibrate` (and `ResetVOC`) render Off with no `defaultValue` (settled by A.U23.14/.15,
  OR94). Specials in the hint for number fields only: an epoch readonly field shows its special's meaning in place
  (A.U23.21) and a "null = …" hint would add text the page never showed (OR94 "don't change the current look"; agent
  decision D4). The code-value button's look is CSS's (M.GEN.062).
- **Unit**: U23. Stage U6: the byte and host-label hint parts (A.U6.28/.29).
- **Depends**: M.WEB.012; M.GEN.062 (CSS for `.code-description`, `[data-code-tone]`, `.field-warning`; the
  `.field-value.code-value` button reset and the muted `.code-number` are Gaps item 5).
- **Blast carried by**: callers `buildFieldGroupCard()` (M.WEB.015); `tests_js/templates.test.js` (M.WEB.058) and
  `tests_js/accessibility.test.js` (M.WEB.063); SPEC H.3 hook list (A.U23.42 Docs, SPEC).
- **Kind**: code

### M.WEB.015 Cards build once, update in place, and reset after Apply
- **From**: A.U23.08 (`updateFieldGroupValues()`), A.U23.15 (`resetControl()`), A.U23.40 (`groupIndex`), A.U23.21
  (context through the update functions), A.U23.11 (unavailable), A.U23.23 (sibling label), A.U6.18 (read:
  `submitLabel` rendered at `:201` — holds), A.U23.16 (reset to unset).
- **Site**: `js/templates.js:176-209` `buildFieldGroupCard()`; new functions after it.
- **Change**: `export function buildFieldGroupCard(group, currentValues, groupIndex, display)` — `display`:
  `{deviceNowS: number | null, isUnavailable: (field: FieldDef) => boolean}`; each field built by `buildField(field,
  resolveFieldValue(field, currentValues), Boolean(group.submit), \`field-${groupIndex}-${fieldIndex}\`, {deviceNowS,
  unavailable: display.isUnavailable(field), siblingLabel})`, `siblingLabel` = the label of the group field whose key
  is `field.ignoredWhenSet`; the Apply button/result pair as today. New `export function updateFieldGroupValues(card,
  group, currentValues, display)` (JSDoc ≤ 3 lines: "Refreshes a built card in place from new values: every readonly
  value, and every number/string caption and placeholder; a toggle or select changes only by the user or by
  resetControl()."): per field, a readonly value element gets the same text/`title`/tone `buildField()` would give it
  (a code button keeps its open description), a writable number/string field's caption and input placeholder get
  `formatFieldValue(field, resolveFieldValue(field, currentValues), display)`; elements are found with
  `card.querySelector(\`[data-field-key="${CSS.escape(key)}"]\`)`. New `export function resetControl(wrapper, field,
  value)` (JSDoc: "Shows `value` in a field's control: clears a text input and every composite sub-input, sets a toggle
  (unset for an always-executed toggle given undefined) with its label and aria-pressed, selects the matching option or
  the placeholder."): input → `value = ""`; composite → every sub-input `""`; toggle → as its build would render
  `value`; select → the option whose value equals `value`, else the `""` placeholder option when present.
- **Resolved**: A.U23.08 names captions only; A.U23.15 clears accepted inputs, which reveals the placeholder — so the
  placeholder is refreshed with the caption, else it would show the pre-Apply value under a cleared input (agent
  decision D5).
- **Unit**: U23.
- **Depends**: M.WEB.014.
- **Blast carried by**: caller `js/render.js` (M.WEB.020/.021); `tests_js/templates.test.js` (M.WEB.058);
  `tests_js/render.test.js` in-place refresh cases (M.WEB.054); SPEC H.3 contract names `resetControl` (A.U23.15 Docs,
  SPEC).
- **Kind**: code

### M.WEB.016 Errcount card: one severity, no invented zero, clickable codes, update in place
- **From**: A.U23.11 (no data / unavailable rows, rollup count), A.U23.12 (`data-worst` is the one severity;
  `data-has-errors` goes), A.U23.20 (1) (clickable history numbers), A.U23.08 (`updateErrcountGroup()`, focus kept),
  A.U0.28 (`:293`, `:304` tags), A.U36.507 (`:303-304` text), A.U2.05 (read: entry shape unchanged), A.U23.43 (6) as
  narrowed by AC_NOTES 26/37 (no pill border cue).
- **Site**: `js/templates.js:211-336` (`worstErrcountType()`, `buildErrcountGroup()`).
- **Change**: `export function buildErrcountGroup(group, errcount)` with `errcount: Record<string, unknown> | null`
  (`null` = the `/status` body carried no errcount object). Per module row: `entry = errcount?.[key]`; absent (or
  `errcount` null) → count text "no data", `data-worst="none"`; `isUnavailable(entry)` → "unavailable",
  `data-worst="none"`; else count `String(counter)` and `data-worst` = `worstErrcountType(entry)` (E/W/N from history,
  unchanged rule). The `.errcount-row` loses `data-has-errors`; the row count's colour follows the wrapper's
  `data-worst` (CSS, M.GEN.062). Rollup: the errors and warnings spans count `data-worst` E and W (unchanged texts); a
  third span `data-rollup="nodata"` "<n> module(s) without data" is shown only when n > 0. "Show flagged" reveals every
  row whose `data-worst` is not `N` (`none` included); the list's current filter is kept in `moduleList.dataset.filter`
  (`collapsed`/`flagged`/`all`). History: `:292-293` comment → "// Always rendered, never independently hidden - a
  shown row's history is meant to be visible right away, not gated / // behind a second click (owner, 2026-08-21)."; the
  `:303-304` comment → "// No pagination or truncation (owner, 2026-08-21: a history stays well under 20 entries,
  paraphrase); / // each logger holds history_length (10) entries, so the whole array renders."; an `E` or `W` entry's
  number is a `button.history-entry-num` (`type="button"`, `aria-expanded`, same class, so it looks as today); clicking
  it shows one `p.code-description` below that row's history with "<num>: <group.codes[type][num]>" or "No description
  for code <num>"; a second click on it, or a click on another pill of the row, hides or updates it; an `N` entry stays a
  plain `span.history-entry-num`. New `export function updateErrcountGroup(card, group, errcount)`: updates the rollup
  texts, each row's count and `data-worst`, re-applies the list's current filter, and rebuilds a row's history items only
  when its `num`/`type` sequence differs from what is shown (closing that row's open description); buttons and the list
  element are never replaced, so focus stays.
- **Resolved**: A.U0.28 (U0) tags `:304` "(owner, 2026-08-21)"; A.U36.507 (U36, same block, "one edit") rewrites it —
  A.U36.507's text stands with the tag inside it. A.U23.43 (6)'s pill border cue is dropped (AC_NOTES 26, owner-accepted
  OR126.a / AC_NOTES 37). An `N` pill stays a span: the catalog's `codes` block has only `E` and `W` tables (A.U2.21), so
  a button on every "no error" placeholder would only ever say "No description" (agent decision D3; look unchanged,
  OR94). The nodata rollup span appears only when needed (look unchanged on a healthy device, OR94; agent decision D3).
- **Unit**: U36 (A.U36.507's comment). Stages: U0 (A.U0.28's `:293` tag), U23 (everything else).
- **Depends**: M.WEB.001 (`isUnavailable`), M.GEN.016 (`codes` block); M.GEN.062 (CSS).
- **Blast carried by**: callers `js/render.js` (M.WEB.020); `tests_js/templates.test.js:343-428` and new cases
  (M.WEB.058); `tests_js/render.test.js` errcount cases (M.WEB.054); SPEC H.6 "Errcount UX"/"History entry" (A.U23.11/.12/
  .20 Docs, A.U36.508, SPEC); H.4 "History depth" (A.U36.507, SPEC).
- **Kind**: code

### M.WEB.017 The section banner starts hidden through its data attribute
- **From**: A.U23.42 (`data-shown`, `js/templates.js:362`).
- **Site**: `js/templates.js:338-370` `buildSectionShell()`.
- **Change**: `errorBanner.className = "error-banner";` and `errorBanner.dataset.shown = "false";` (role `alert`
  unchanged); JSDoc unchanged. `buildNavDrawer()` (`:372-395`) unchanged.
- **Resolved**: —
- **Unit**: U23.
- **Depends**: M.GEN.062 (`.error-banner:not([data-shown="true"])`).
- **Blast carried by**: `showBanner()`/`hideBanner()` (M.WEB.021); `tests_js/templates.test.js`, `render.test.js` banner
  assertions (M.WEB.058/.054).
- **Kind**: code

## js/render.js

### M.WEB.018 Collect a sparse PUT exactly
- **From**: A.U23.14 (strict number parse, collection rules, JSDoc), A.U23.16 (unset always-executed toggle), A.U23.40
  (`CSS.escape` in selectors), A.U6.17 (read: the flags; "render.js consults the flag only for toggle/enum"), A.U23.30
  (read: JSON numbers sent as `JSON.stringify` writes them — holds), A.U10.40 (read: composite member keys come from the
  definitions).
- **Site**: `js/render.js:16-40` `readInputValue()`, `:61-125` `collectGroupBody()`.
- **Change**: new private `parseNumberInput(text)` — `text.trim()` matching `/^[+-]?(\d+(\.\d*)?|\.\d+)$/` → `Number(trimmed)`,
  anything else → the raw `text` (the device answers "Invalid"); JSDoc one line "A number only for plain decimal text;
  anything else is sent raw for the device to reject." `readInputValue()` uses it for `number` (empty → `undefined`;
  the `:27-29` comment → "// Text that is not a plain decimal is sent as typed: the device rejects it, so garbage never
  becomes a / // plausible number."); the `enum` branch unchanged. `collectGroupBody(card, group, currentValues)` JSDoc
  (≤ 3 lines): "Reads the card's controls into a sparse PUT body: a number/string input is sent whenever non-empty, a
  composite when any sub-input is, an enum/toggle when it differs from its resolveFieldValue() baseline; a dispatch toggle
  only when On, a dispatch enum when an option is chosen, an always-executed toggle whenever it is set." Rules: `toggle` —
  `data-value` `"unset"` → not sent; `field.dispatch` → sent only when `"true"`; `field.alwaysExecuted` → sent whenever
  set (`true`/`false`); otherwise sent when `value !== Boolean(resolveFieldValue(...))`; `composite` — every non-empty
  sub-input through `parseNumberInput()` (the `:98-100` comment goes), sent when any is filled; `enum` — `""` (the
  placeholder) → not sent; `field.dispatch` → sent; else sent when different from the baseline; `number`/`string` —
  sent whenever non-empty, whatever its value. Every selector interpolating a key uses `CSS.escape(key)`.
- **Resolved**: —
- **Unit**: U23.
- **Depends**: M.WEB.014 (unset state), M.WEB.005.
- **Blast carried by**: `tests_js/render.test.js:307-342, :540-600, :678-722` hold, new parse/dispatch cases (M.WEB.054);
  `tests_js/live-backend-put-matrix.test.js` `willRoundTrip` (M.WEB.062); SPEC H.4 sparse-PUT row (A.U36.505, SPEC).
- **Kind**: code

### M.WEB.019 Read every PUT's per-field result; one severity order
- **From**: A.U23.13 (result read the same way for every section; word in place of a map; empty-result default
  goes), A.U23.12 (unknown word ranks worst), A.U23.14 (stale colours cleared), A.U23.25 (constants), A.U11.26 and
  A.U11.31 (the `:132-135`, `:160` "gap" comments), A.U23.29 (read: the comment is A.U23.13's), A.U36.544 (4)
  (`:44`, `:127` pointers), A.U19.15 (read: `_ERROR_SHAPES` became `_ERROR_STATUSES`).
- **Site**: `js/render.js:42-59` `describeGetFailure()`, `:127-177` (`STATUS_SEVERITY`, `reconcileResults()`,
  `applyResultStyling()`).
- **Change**: `describeGetFailure()` JSDoc → "A GET's non-ok/empty response, worded with the server's shaped-error
  `descr` when present (every 400/404/405/413/500 envelope carries one, SPECIFICATION.md C.5.3) rather than a bare status
  code." (body unchanged). `/** Worst-first severity of the four result words; an unknown word ranks below Invalid. */` /
  `const STATUS_SEVERITY = { [INVALID]: 0, [FAILED]: 1, [VALID]: 2, [UNCHANGED]: 3 };` and a private `severity(word)` =
  `STATUS_SEVERITY[word] ?? -1`. `reconcileResults(submitted, received)`: mechanics unchanged, JSDoc → "Defensive only:
  the server answers every submitted key (SPECIFICATION.md A.8); a missing one is shown Failed rather than dropped."
  `applyResultStyling(card, results, descr)`: first removes `data-apply-status` from every `[data-field-wrapper-key]` of
  the card; the card status is the lowest-severity word of `results` (no `"Valid"` seed: `results` is never empty, every
  submitted key is reconciled), lower-cased when known and `"failed"` when unknown; each wrapper gets its own word the
  same way; the `.apply-result` text keeps the raw words (`"<descr> — <key>: <word>, …"`). The `:160-161` comment goes.
- **Resolved**: A.U11.26/A.U11.31 hand both comments to U23 (A.U23.13/A.U23.29 write them, here). The empty-result
  "Valid" default goes because `/status`'s PUT now answers `ResetErrors` per field (M.SRC_NET.123), so every section is
  read the same way.
- **Unit**: U23.
- **Depends**: M.WEB.001; M.SRC_NET.120/.123 (per-field results, word in place of a map).
- **Blast carried by**: `tests_js/render.test.js:417-466, :1015-1037` and new cases (M.WEB.054); SPEC H.4 "PUT/GET error
  handling", H.6 "Server-side settings-group failure" (A.U23.13 Docs, SPEC); H.6.1 rows 3/5 (A.U36.044, SPEC).
- **Kind**: code

### M.WEB.020 A section renders once, updates in place, aborts on leave and recovers by itself
- **From**: A.U23.03 (one `AbortController`, no paint once stopped), A.U23.04 (visibility through the context),
  A.U23.05 (`fetchOnce()` throws; banner path; once-per-episode log; one-shot sections in the loop; AC_NOTES 28),
  A.U23.06 (clock fed by `/status` bodies; `onRecovered` after an episode), A.U23.08 (build once, update in place; the
  expand-state restore goes), A.U23.11 (unavailable sources, missing errcount), A.U23.18 (errcount groups and `statusPath`
  fields on any page; the notification special case goes), A.U23.19 (maintenance by `path`; flattening goes), A.U23.21
  (clock passed to the templates), A.U23.40 (`groupIndex`, `CSS.escape`), A.U23.42 (banner through
  `showBanner()`/`hideBanner()`; the `.hidden` reads go), A.U35.46 (read: `startPolling()`'s only caller), A.U8.18 (read:
  the interval `section.pollIntervalMs ?? defs.defaultPollIntervalMs`), A.U6.24 (read: `path` on the System section
  resolves against the whole body).
- **Site**: `js/render.js:280-417` (`renderSection()`, `paint()`, `fetchOnce()`, `groupValuesFrom()`).
- **Change**: `export function renderSection(defs, section, mainEl, context = {})` — `@param {{visibility?: Visibility,
  deviceClock?: DeviceClock, onRecovered?: () => void, applyTracker?: {begin: () => void, end: () => void}}} [context]`
  (`DeviceClock` = `{nowS: () => number | null, observe: (statusBody: unknown) => void}`, typedef exported from
  `js/shell.js`, M.WEB.025); `@returns {() => void}`. State: `const controller = new AbortController();`, `let stopped
  = false;`, `let failing = false;`, `const baselines = new WeakMap()` (card → its values object), `needsStatus =
  section.rest.get !== "/status"` and some group is an errcount group or carries a `statusPath` field. `fetchOnce()`:
  `pollManager.request(section.rest.get, undefined, undefined, controller.signal)`; a non-ok or empty response throws
  `describeGetFailure(...)`; the status body is the section's own body when its GET is `/status`, else (when
  `needsStatus`) a second request `"/status"` in the same queue with the same signal, its failure thrown the same way;
  every status body read goes to `context.deviceClock?.observe(body)`; `if (stopped) return;` before `paint(data,
  statusBody)`. `onError(error)`: returns at once when `stopped` or `error.name === "AbortError"`; else
  `showBanner(errorBanner, \`Could not refresh ${section.label}: ${String(error)}\`)` and, only when `!failing`, sets
  `failing = true` and logs `console.error(\`Could not refresh ${section.label}:\`, error)`. `onSuccess()`:
  `hideBanner(errorBanner)`; when `failing`, `failing = false` and `context.onRecovered?.()`. The loop:
  `startPolling(async () => { await fetchOnce(); onSuccess(); }, section.pollIntervalMs ?? defs.defaultPollIntervalMs,
  {visibility: context.visibility, onError, stopAfterSuccess: section.pollGroup !== "live"})` — every section, live or
  not, runs its GET through this one loop (the HEAD `:382` direct `fetchOnce()` call goes, AC_NOTES 28). `refreshAfterApply()`
  = `fetchOnce().then(onSuccess, onError)` (never rejects). The returned stop function sets `stopped`, aborts the
  controller and stops the loop. `paint(data, statusBody)` per `[groupIndex, group]`: an errcount group reads
  `statusBody.errcount` (an object, else `null`) and calls `updateErrcountGroup()` on its existing card or appends
  `buildErrcountGroup()`; a field group computes `values = groupValuesFrom(section, group, data, statusBody)` and
  `display = {deviceNowS: context.deviceClock?.nowS() ?? null, isUnavailable}` where `isUnavailable(field)` is true when
  the group's source object is `isUnavailable()` or the walk of `field.path` (or of `field.statusPath` over the status
  body) meets an unavailable object before its leaf; an existing card (found with `CSS.escape(group.key)`) gets
  `baselines.set(card, values)` and `updateFieldGroupValues(card, group, values, display)`, a new one is built by
  `buildAndWireFieldGroup()` (M.WEB.021) and appended; either way `card.dataset.sourceState = "unavailable"` when the
  source is unavailable, else the attribute is removed. No `replaceWith`, no expand-state restore (`:296-316` go).
  `groupValuesFrom(section, group, data, statusBody)`: `measurements`/`sensors` → `data[group.key] ?? {}`; `status` →
  `data[group.key] ?? {}` (the maintenance group, key `sensors`, therefore gets `data.sensors`, read through each field's
  `path`); every other section → `data`; then, when the group has `statusPath` fields, a copy of that object with each
  such field's key set to the walk of its `statusPath` over `statusBody`. The `:399-411` flattening and the `:357-368`
  notification special case go. JSDoc of `groupValuesFrom()` (≤ 3 lines) states these rules.
- **Resolved**: AC_NOTES 28: `render.js:382`'s third direct `fetchOnce()` caller is covered — A.U23.05's "a one-shot
  section runs its GET through the same loop" replaces it (settled; no extra site). A.U23.03's "fetchOnce() returns
  silently on an AbortError" and A.U23.05's "fetchOnce() throws instead of catching" are combined: `fetchOnce()` throws,
  `onError` drops an abort or a stopped section. The failure episode is tracked here, not in `startPolling()`, because the
  post-Apply refresh (A.U23.05) runs outside the loop (agent decision D1). The pending-Apply count A.U23.06 needs reaches
  the shell through `context.applyTracker` (agent decision D6).
- **Unit**: U23.
- **Depends**: M.WEB.002, M.WEB.003, M.WEB.015, M.WEB.016, M.WEB.001; M.GEN.014/.015 (`path`, `statusPath`, the
  Networking errcount group).
- **Blast carried by**: caller `js/shell.js` (M.WEB.025); `tests_js/render.test.js` (M.WEB.054),
  `tests_js/generated-definitions-render.test.js` (M.WEB.056), `tests_js/shell.test.js` (M.WEB.064); SPEC H.3 "In-place
  refresh", H.4 "Poll coordination"/"PUT/GET error handling", H.6 errcount placement and `statusPath` (A.U23.08/.05/.18
  Docs, A.U36.503, SPEC); SPEC H.8 `:4735-4737` (A.U23.05 doc, SPEC).
- **Kind**: code

### M.WEB.021 Apply and Clear: send once, show per field, reset, follow the server
- **From**: A.U23.13 (result reading), A.U23.15 (after-Apply resets, optimistic baseline goes, refresh awaited, button
  disabled until it settles), A.U23.16 (unset after every Apply), A.U23.17 (Clear action), A.U23.23 (Altitude warning),
  A.U23.06 (pending-Apply count), A.U23.40 (`groupIndex`), A.U0.53 + A.U23.45 (`:264-266` comment), A.U24.48 (`:262`
  disable reason), A.U36.544 (4) (`:225` pointer), A.U23.30 (read: the `:216-218` JSON-number fact), A.S0930.10 (read:
  the two new `SystemCmd` options need no code — the dropdown renders definitions' options and Apply sends the value),
  M_SRC_CORE GAP-G13 (read: `coerce_numeric()` no longer exists).
- **Site**: `js/render.js:179-278` `buildAndWireFieldGroup()`.
- **Change**: `function buildAndWireFieldGroup(group, groupIndex, section, values, ctx)` — `ctx` = `{baselines,
  display, refreshAfterApply, isStopped, applyTracker}`: builds `buildFieldGroupCard(group, values, groupIndex, display)`,
  `baselines.set(card, values)`, returns the card unwired when `!group.submit`. One private `async function send(body)`:
  `applyTracker?.begin()`; `button.disabled = true`; PUT through `pollManager.request(putPath, {method: "PUT", headers,
  body: JSON.stringify(section.key === "sensors" ? {[group.key]: body} : body)})` with no abort signal (a sent write is
  never aborted); the `:216-218` comment → "// No decimal-point forcing: the backend accepts a JSON int for a float-typed
  field and coerces it / // (SPECIFICATION.md Part A.8), so JSON.stringify() is enough." and `:225-227` → "(SPECIFICATION.md
  C.5.3)" in place of "(Part A.8/A.5)"; a non-ok response, a null body or `res === "ERR"` throws as today; `rawResult` =
  `result[group.key]` for `/sensors`, else `result`; a string `rawResult` gives every submitted key that word; else
  `reconcileResults(body, rawResult ?? {})`; `applyResultStyling(card, results, descr ?? "Done")`. The `catch` keeps
  today's text and card/field `failed` marking, and counts every submitted key as Failed for the resets below; `:260-262` → one line `// eslint-disable-next-line
  require-atomic-updates -- card is a const reference and the disabled button rules out re-entry` (the 2-line comment
  above it goes: it is the reason); `:264-266` → "// No per-field breakdown came back, so every submitted field shows
  Failed (SPECIFICATION.md Part H.4)." After the `try`: every dispatch field of the group → `resetControl(..., false)`
  for a toggle, `(…, undefined)` for an enum; every always-executed toggle → `resetControl(..., undefined)` (unset);
  every submitted number/string/composite whose word is Valid/Unchanged → `resetControl(..., undefined)` (cleared; an
  Invalid/Failed one keeps what was typed). Then `if (!isStopped()) await refreshAfterApply();`, then every submitted
  non-dispatch, non-always-executed toggle/enum whose word is Valid/Unchanged → `resetControl(wrapper, field,
  resolveFieldValue(field, baselines.get(card)))`; the warnings are re-evaluated; `finally` → `button.disabled = false`,
  `applyTracker?.end()`. The optimistic `currentValues[key] = value` block (`:247-254`) goes. Apply click: `body =
  collectGroupBody(card, group, baselines.get(card))`; empty → "Nothing to submit - no fields were changed." (today's text;
  the `:203-205` comment → "// Nothing changed: skip the round trip rather than PUT an empty body."); else `await
  send(body)`. Clear: for each `[data-clear-for]` button of the card, a click → `if (!window.confirm(\`Clear
  ${field.label}?\`)) return;` → `await send({[field.key]: ""})` (never merged with the card's body). Warning: for each
  field with `ignoredWhenSet`, an `input` listener on the field's and the sibling's controls sets the warning's
  `dataset.shown` to `"true"` exactly when the field's input is non-empty and the sibling's effective value — its typed
  input through `parseNumberInput()` when non-empty and a finite number, else `resolveFieldValue(sibling,
  baselines.get(card))` — is a non-zero number, else `"false"`.
- **Resolved**: A.U0.53 (U0) relabels `:264-266`; A.U23.45 (U23, same lines) shortens it to one line ending "(SPECIFICATION.md
  Part H.4)" — the later text stands, its provenance moves to H.4's divergence row (A.U23.45). A.U24.48's `-- <reason>`
  makes the `:260-261` comment a duplicate, so the reason lives once, in the disable comment. GAP-G13's rename makes
  `coerce_numeric()` a stale name (adherence: a comment names the current fact). OR121/OR122: the two new commands use
  the existing dropdown and Apply with no dialog — `window.confirm` is reached only by the DNS fallback Clear (A.U23.17,
  owner OR56.a (2)); A.S0930.20 (5) pins both facts.
- **Unit**: U24 (A.U24.48's reason). Stages: U0 (A.U0.53's relabel — superseded at U23), U23 (everything else).
- **Depends**: M.WEB.015, M.WEB.018, M.WEB.019, M.WEB.020; A.U24.48's plugin (M.WEB.070/.080).
- **Blast carried by**: `tests_js/render.test.js` (M.WEB.054); live matrix commands read state after the refresh
  (M.WEB.061); SPEC H.4 "After Apply", "Known accepted gap", legacy-divergence row (A.U23.15/.17/.45 Docs, SPEC).
- **Kind**: code

### M.WEB.022 One banner pair for every entry and section
- **From**: A.U23.07 (exported pair in `render.js`, acyclic graph), A.U23.42 (`data-shown`).
- **Site**: `js/render.js` (new exports after the imports).
- **Change**: `export function showBanner(el, message)` — `el.textContent = message; el.dataset.shown = "true";`;
  `export function hideBanner(el)` — `el.dataset.shown = "false";` (text kept, as today's self-healing banner); JSDoc
  one line each. Imports of the file: `VALID`, `UNCHANGED`, `INVALID`, `FAILED`, `isUnavailable` from
  `./api-contract.js`; `resolveFieldValue` from `./definitions.js`; `pollManager`, `startPolling` from
  `./poll-manager.js`; `buildErrcountGroup`, `buildFieldGroupCard`, `buildSectionShell`, `resetControl`,
  `updateErrcountGroup`, `updateFieldGroupValues` from `./templates.js` (`formatFieldValue` is no longer imported here).
  Header `:1-4` unchanged.
- **Resolved**: —
- **Unit**: U23.
- **Depends**: M.WEB.017.
- **Blast carried by**: importers `js/shell.js`, `js/main.js`, `js/app.js` (M.WEB.025/.030/.031); A.U23.41's layering
  guard allows `dataset.shown` (TSC).
- **Kind**: code

## js/shell.js (new)

### M.WEB.025 One shell for both entries: nav, sections, device watch, stop handle
- **From**: A.U23.07 (shell, `startShell()`, stop handle, `selectSection()` once), A.U23.06 (device clock, build
  watch, reload after pending Applies), A.U23.04 (visibility built once by the entry), A.U35.46 (2) (`selectSection()`'s
  narrowing comment, now here), A.U23.41 (read: non-entry modules never query `document`), OR36.a (1) (no test-only
  seam).
- **Site**: new `js/shell.js`.
- **Change**: header (3 lines) "The page shell both entries share: the nav, section switching, the device watch and
  one stop handle. / Takes every document-derived input from its entry (SPECIFICATION.md Part H.2, H.3)." Imports
  `initNav` (`./nav.js`), `pollManager`, `startPolling` (`./poll-manager.js`), `renderSection` (`./render.js`). Typedef
  `DeviceClock` = `{nowS: () => number | null, observe: (statusBody: unknown) => void}` (JSDoc, imported by
  `render.js`). `/** Device watch cadence: the clock and the build compare. */` / `// @tunable
  web.device_watch_interval_ms = 60000` / `const DEVICE_WATCH_INTERVAL_MS = 60000;`. `export function visibilityOf(doc)`
  → `{isHidden: () => doc.visibilityState === "hidden", onChange: (cb) => { doc.addEventListener("visibilitychange",
  cb); return () => doc.removeEventListener("visibilitychange", cb); }}` (`@param {Document} doc`, `@returns
  {Visibility}`). `export function startShell({defs, elements, keyTarget, visibility, reload})` (`elements` =
  `{appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl}`, `keyTarget: EventTarget`, `reload: () => void`; `@returns
  {() => void}`): the clock — `offsetS = null`; `observe(body)` sets `offsetS = UnixTime - Date.now() / 1000` when
  `body.system.UnixTime` is a number; `nowS()` → `null` before that, else `Math.floor(Date.now() / 1000 + offsetS)`; the
  Apply count — `applyTracker.begin()` increments, `end()` decrements and calls `reload()` when a reload is pending and the
  count is 0; `nav = initNav({...elements minus mainEl, defs, keyTarget, onSelect: selectSection})`; `selectSection(key)`
  finds the section (`if (section === undefined) { return; // unreachable - narrows the type for tsc: keys come from
  defs.sections }`), stops the current one, `nav.setCurrent(key)`, `stopSection = renderSection(defs, section,
  elements.mainEl, {visibility, deviceClock, onRecovered: watchOnce, applyTracker})`; `watchOnce()` — `GET /status`
  through `pollManager.request()` → `deviceClock.observe(body)`; `GET /system` → when `body.build` is an object, its
  `JSON.stringify()` is compared with the first one seen; a difference marks a reload pending and calls `reload()` at
  once when no Apply is pending; no `build` object, a failed request or a stopped shell → nothing; `stopWatch =
  startPolling(watchOnce, DEVICE_WATCH_INTERVAL_MS, {visibility, onError: () => { /* silent: the section's own GET owns
  the banner */ }})`; then `selectSection(defs.landingSection)`. The returned `stop()` sets `stopped`, stops the
  section and the watch (each releases its visibility subscription) and calls `nav.dispose()`.
- **Resolved**: A.U23.07's `fetchImpl?` parameter has no production caller (every request goes through `pollManager`)
  — a test-only seam, so it goes (OR36.a (1); agent decision D7). The visibility source is built by one shell helper over
  the `Document` the entry passes, instead of a copy in each entry (G7/R35 "logic both entries need lives once"; the
  layering guard's rule — no `document.` query outside the entries — holds; agent decision D7). A.U35.46 (2)'s one-line
  comment lands here since A.U23.07 moves `selectSection()`.
- **Unit**: U23 (A.U35.46 (2)'s comment folded in).
- **Depends**: M.WEB.003, M.WEB.020, M.WEB.026; A.U19.06 (static files revalidate, so a reload fetches the new
  bundle; SRC_NET); A.U10.40 (`build` keys).
- **Blast carried by**: entries `js/main.js`, `js/app.js` (M.WEB.030/.031); new `tests_js/shell.test.js` (M.WEB.064);
  production closure gains the module (A.U23.38, SCR); A.U23.41 guard (TSC); SPEC H.2 module list (A.U36.517 (3)), H.4
  "Stale bundle" row (A.U36.510 (4)), Part N `web.device_watch_interval_ms` row (A.U23.06 Docs) (SPEC); BACKLOG
  `:867-875` items removed (A.U23.07 Docs, DOCS).
- **Kind**: code

## js/nav.js

### M.WEB.026 The nav: data-attribute state, inert drawer with focus, one dispose
- **From**: A.U23.07 (`{setCurrent, dispose}`, `keyTarget`), A.U23.42 (`data-nav-open`), A.U23.43 (2) (`inert`, focus,
  `aria-label`), A.U35.46 (2) (`:35-37` narrowing comment), A.U23.41 (read: no `document.` query here).
- **Site**: `js/nav.js:1-67`.
- **Change**: header unchanged. `export function initNav({defs, appShellEl, drawerEl, hamburgerEl, backdropEl,
  keyTarget, onSelect})` (`keyTarget: EventTarget`), `@returns {{setCurrent: (sectionKey: string) => void, dispose: () =>
  void}}`. `closeDrawer()`: when `drawerEl.matches(":focus-within")` it moves focus to `hamburgerEl` first; then
  `appShellEl.dataset.navOpen = "false"`, `aria-expanded="false"`, hamburger `aria-label` "Open navigation", `drawerEl.inert
  = true`. `openDrawer()`: `navOpen = "true"`, `aria-expanded="true"`, `aria-label` "Close navigation", `drawerEl.inert =
  false`, focus the first `[data-section-key]` link. The hamburger toggles on `appShellEl.dataset.navOpen === "true"`.
  Every listener (each link's click, hamburger, backdrop, `keyTarget` keydown Escape) is registered through one local
  helper that records its removal, and `dispose()` removes them all. The link loop's `continue;` comment → "// unreachable
  - narrows the type for tsc: buildNavDrawer() sets it on every link". `setCurrent` is today's returned function.
- **Resolved**: A.U23.43's "moves focus back to the hamburger when focus was inside the drawer" reads the focus through
  `drawerEl.matches(":focus-within")`, not `document.activeElement`, so the layering guard (A.U23.41: no `document.`
  query outside the entries) holds; the check runs before `inert` is set, which would drop the focus.
- **Unit**: U23 (A.U35.46 (2) folded in).
- **Depends**: M.GEN.060 (`html/index.html:22` starts `inert`), M.GEN.062 (`[data-nav-open]` CSS).
- **Blast carried by**: caller `js/shell.js` (M.WEB.025); `tests_js/nav.test.js` (M.WEB.059); live commands and the
  smoke open the drawer by `#hamburger-button` and read `aria-expanded` (hold; A.U23.42 Blast); BACKLOG `:867-871`
  (A.U23.07 Docs, DOCS).
- **Kind**: code

## js/main.js

### M.WEB.030 The production entry: load, name, start the shell
- **From**: A.U23.07 (keeps only load/name/shell; returns the stop handle), A.U23.04 (document-derived visibility),
  A.U23.06 (`reload`), A.U23.42 (banner through `showBanner()`), A.U35.46 (2) (the duplicated `selectSection()` goes
  with its comment).
- **Site**: `js/main.js:1-60`.
- **Change**: header `:1-5` unchanged. Imports: `loadDefinitions` (`./definitions.js`), `showBanner` (`./render.js`),
  `startShell`, `visibilityOf` (`./shell.js`). `export async function startApp(elements)` — the `@param` key list
  unchanged (A.U23.38's bootstrap check reads it), `@returns {Promise<() => void>}`: definitions load failure →
  `showBanner(errorBannerEl, \`Could not load definitions: ${String(error)}\`)` and `return () => { /* nothing was
  started */ };`; then `deviceNameEl.textContent = defs.device.displayName;` and `return startShell({defs, elements:
  {appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl}, keyTarget: document, visibility: visibilityOf(document),
  reload: () => window.location.reload()});`. `initNav`/`renderSection` imports and `selectSection()` go.
- **Resolved**: —
- **Unit**: U23.
- **Depends**: M.WEB.025, M.WEB.022.
- **Blast carried by**: `html/index.html:30-45` bootstrap (unchanged call; M.GEN.060); `tests_js/main.test.js`
  (M.WEB.059); A.U23.38's staging check of the bootstrap keys (SCR).
- **Kind**: code

## js/app.js

### M.WEB.031 The prototype entry: manifest, generated definitions, composed mock, shared shell
- **From**: A.U6.07 (manifest, generated definitions, `samples.json`, no variant literal), A.U6.06 (3)
  (`composeMockData()`), A.U23.01 (startup loads through the queue), A.U23.07 (shell, stop handle), A.U23.42 (banner),
  A.U35.46 (2) (duplicate `selectSection()` goes), A.U28.24 (read: the preview serves `build/generated_src/definitions/`).
- **Site**: `js/app.js:1-87`.
- **Change**: header (3 lines) "Prototype entry point: picks a device from the build's definitions manifest
  (`?device=` overrides it), installs the / mock backend and starts the shared shell. Never staged (SPECIFICATION.md Part
  H.2)." Imports: `loadDefinitions`; `composeMockData`, `installMockFetch` (`./mock-server.js`); `pollManager`;
  `showBanner`; `startShell`, `visibilityOf`. `const DEFINITIONS_DIR = "../build/generated_src/definitions";`.
  `startApp(elements)` (`@returns {Promise<() => void>}`): (1) `pollManager.request(\`${DEFINITIONS_DIR}/index.json\`)`;
  a non-ok status or a body whose `devices` is not a non-empty string array → banner "Could not load the device list:
  <error>" and a no-op stop; (2) `device` = the `?device=` value when it is in `devices`, else `devices[0]` (the manifest
  is sorted); (3) `loadDefinitions(\`${DEFINITIONS_DIR}/${device}.json\`)` → on failure the banner "Could not load
  definitions for "<device>": <error>"; (4) `deviceNameEl.textContent`; (5) `pollManager.request("../mockdata/samples.json")`
  → on a non-ok status or failure the banner "Could not load mock fixture data for "<device>": <error>"; (6) `uninstall =
  installMockFetch(defs, composeMockData(defs, samples))`; (7) `stopShell = startShell({...same as main.js})`; returns
  `() => { stopShell(); uninstall(); }`. `DEFAULT_DEVICE`, `KNOWN_DEVICES`, `fetchWithTimeout` and `selectSection()` go.
- **Resolved**: A.U6.07 fetches the manifest "via `fetchWithTimeout`"; A.U23.01 (later) moves every startup fetch into
  the queue and removes that export — `pollManager.request()` stands.
- **Unit**: U23. Stage U6: A.U6.07 (manifest, generated definitions, `samples.json`, `composeMockData`) on today's
  structure, so the hand definitions can be deleted in U6 (A.U6.04).
- **Depends**: M.WEB.025, M.WEB.040 (`composeMockData`), A.U6.02 (manifest written, SCR), M.WEB.045 (`samples.json`).
- **Blast carried by**: `html/index.html` bootstrap under `npm run preview` (M.GEN.060); `tests_js/app.test.js`
  (M.WEB.059); `scripts/preview_server.py` serves the four directories (A.U28.24, SCR); SPEC H.2 `:4309-4310`, README
  `:236-237` (A.U36.516/.517, SPEC/DOCS).
- **Kind**: code

## js/mock-server.js

### M.WEB.040 The mock's frame: derived routes, one envelope mirror, parsed bodies, fixed delays
- **From**: A.U23.26 (`STANDARD_CODES`, `makeResponse()`, every envelope through it, handler split), A.U23.27 (route set
  from the definitions; constants and their comments go), A.U23.28 (body parsed in `try`; `group-failure`), A.U23.29
  (`partial-result` goes; no random latency; `controls.delayMs`), A.U23.25 (`COUNTER_CAP` here, result-word constants),
  A.U19.15 (codes 4/5 go), A.U19.20 (read: route set equals the REST reference, pinned by A.U23.31), A.U8.21 (its
  `l0.mock_latency_*` half — dropped, below), A.U1.25 and A.U6.13 (the `:178-179` comment — dropped, below), A.U36.544 (4)
  (`:353` pointer), A.U6.06 (read: `composeMockData()` export, M.WEB.043).
- **Site**: `js/mock-server.js:1-22, :251-275, :310-379, :443-501` (header, `REST_PATHS`/`SYSTEM_CMDS`/`PAUSE_TIME_MAX`/
  `SENSOR_QUIRK_FIELDS`, `dropOneResultForPartialFailure()`, `envelope()`, the `MockFailure` typedefs,
  `installMockFetch()`'s frame, `jsonResponse()`).
- **Change**: header (3 lines) "Prototype-only fake backend: intercepts window.fetch() for the routes the definitions
  declare and answers / exactly as the real server does, from data composed per device (SPECIFICATION.md Part H.4). Never
  staged; / everything outside this file targets the real API." Imports `VALID`, `UNCHANGED`, `INVALID`, `FAILED`
  from `./api-contract.js` and `neverUnchanged` from `./definitions.js`. Constants: `// src/asy_base_classes.py's COUNTER_CAP: 2**30 - 1, no counter exceeds it.` / `const
  COUNTER_CAP = 2 ** 30 - 1;`; `// src/asy_api_response.py's _STANDARD_CODES (SPECIFICATION.md C.5.3).` / `const
  STANDARD_CODES = {0: "Command executed", 1: "Invalid JSON request", 400: "Bad request", 404: "Not found", 405: "Method
  not allowed", 413: "Payload too large", 500: "Internal server error"};`. `REST_PATHS`, `SYSTEM_CMDS`,
  `PAUSE_TIME_MAX`, `SENSOR_QUIRK_FIELDS`, the LED constants and their comments go. `function makeResponse(code, {descr,
  result} = {})` → `{res: code === 0 ? "OK" : "ERR", code, descr: descr ?? STANDARD_CODES[code] ?? "Unknown error",
  result: result ?? {}}` (JSDoc: "The envelope src/asy_api_response.py's make_response() builds."). `MockFailure` =
  `"network" | number | "malformed-body" | "torn-json" | "empty-body" | "group-failure"`; `MockFetchControls` =
  `{nextFailure?: MockFailure | undefined, delayMs?: number}`; their JSDoc prose (≤ 3 lines): "One-shot failure for the
  next intercepted request, consumed once; `delayMs` delays every answer by a fixed time." `installMockFetch(defs,
  initialData, controls)`: the route sets are derived once — GET = every section's `rest.get`, PUT = every section's
  `rest.put`; a request whose URL is no route of either set passes through to the real `fetch()`. Injected failures
  (except `group-failure`, which `handlePut()` consumes): `network` throws as today; `malformed-body` → `makeResponse(1)`
  HTTP 200 (its comment → "(SPECIFICATION.md C.5.3)" in place of "(Part A.8/A.5)"); `torn-json`, `empty-body` as today;
  a number → `makeResponse(n)` with HTTP status n. Then `if (controls?.delayMs) await` a timer of `delayMs`; with
  `delayMs` unset no timer runs. GET on a GET route → `handleGet(path)`; PUT on a PUT route → `handlePut(path,
  rawBodyText)`; any other method on a known route → `makeResponse(405)` with HTTP 405. `jsonResponse()` unchanged.
  `dropOneResultForPartialFailure()` and `envelope()` go. No function exceeds the ESLint ceilings (M.WEB.070).
- **Resolved**: A.U8.21 tags the random latency (`MOCK_LATENCY_*`, U8) that A.U23.29 (U23, later) removes — the mock half
  of A.U8.21 is dropped as obsolete (no site left; the harness-budget half lands, M.WEB.061/.062). A.U1.25 (legacy path)
  and A.U6.13 (generated-module wording) rewrite the `:178-179` comment that A.U23.27 deletes with the LED constants —
  both dropped (no site left; A.U19.02's comment rewrite of the same lines likewise). A.U23.28's malformed-body
  `makeResponse(1)` replaces today's literal envelope (same values).
- **Unit**: U23. No earlier stage: A.U6.06's `composeMockData()` (M.WEB.043) and A.U6.17's routing (M.WEB.041) are
  separate merged changes in the same file.
- **Depends**: M.WEB.001, M.WEB.005; M.SRC_CORE.073 (code table).
- **Blast carried by**: callers `js/app.js` (M.WEB.031), `tests_js/mock-server.test.js`, `render.test.js`,
  `mock-server-put-matrix.test.js`, the new render/compose tests (M.WEB.052/.054/.056/.060); L0
  `tests_scripts/test_js_api_mirrors.py` (code table and `COUNTER_CAP`; A.U23.25/.26, TSC);
  `tests_js/api-reference-agreement.test.js` (M.WEB.065); SPEC H.4 mock paragraph (A.U36.510 (5), SPEC); Part N
  `l0.mock_latency_*` rows never written (A.U8.21, SPEC).
- **Kind**: code

### M.WEB.041 PUT semantics mirror the server field for field
- **From**: A.U23.28 (unknown keys/sensors, non-object sensor entry, `/status` PUT, `group-failure`), A.U23.27 (action
  fields from `dispatch: true`; options, bounds and LED members from the definitions), A.U6.17 (5) (`neverUnchanged()`
  routing; always-executed stored), A.U9.03 (busy refusal), A.U19.02 (LED malformed → "Invalid"), A.U19.03 (pause: same
  outcome), A.U19.04 (read: membership by equality), A.U19.01 (mirror), A.U11.31 (mirror), A.U6.28 (3) (byte bound),
  A.U6.29 (3)/A.U6.30/A.U10.41/A.U18.10 (shape mirrors), A.U23.49 (resolution compare), A.U4.01 (read: the raw compare
  this replaces), A.U11.21 (the float32 gap is listed, not mirrored), A.U23.30 (int/float policy holds), A.U25.12 (7)
  (`ForceCalRef` reads back the last value applied), A.S0930.09/.20 (4) (the two new words, never persisted, near misses
  "Invalid"), A.S0930.31 (read: the mock stays stateless "Valid"/"Invalid" for commands), A.U17.19 (read:
  `ResetErrors` leaves `UARTLINK_*` alone — holds), A.U10.40 (member and key names from the definitions).
- **Site**: `js/mock-server.js:24-249, :380-442` (`coerceAndValidate()`, the field-def maps, `applySparsePut()`,
  `dispatchRangedAction()`, `dispatchLightCmdLed()`, `dispatchSensorQuirkField()`, `applySensorQuirksForGet()`, the PUT
  branches).
- **Change**: `coerceAndValidate(field, rawValue)`: number branch unchanged (the int/float policy, its comments kept);
  string branch: a value equal to one of `field.specialValues` is valid first; else length bounds as today, then, when
  `field.byteLength`, `new TextEncoder().encode(value).length <= maxLength`, then the `field.shape` rule —
  `hostLabel` (1+ ASCII letters/digits/`-`, not starting or ending with `-`), `countryCode` (exactly two `A`-`Z`),
  `hostName` (a dotted IPv4 literal, or dot-separated labels of 1-63 characters each a host label), `ipv4List` (`""`, or 1
  to 3 comma-separated dotted IPv4 literals with no spaces) — the same rules as `src/` (`host_label_ok()`,
  `_country_ok()`, `_ntp_host_ok()`, `_dns_fallback_ok()`, M.SRC_NET.018/.045/.075), one private function per shape;
  enum and toggle branches unchanged. `handlePut(path, rawBodyText)`: the body is `JSON.parse`d in `try`; unparseable or
  not a plain object → `makeResponse(1)` HTTP 200; `nextFailure === "group-failure"` → every attempted key (per sensor
  for `/sensors`) answers `FAILED` in a `makeResponse(0, {result})`, consumed. `/sensors`: an unknown sensor key or a
  non-object entry → `results[name] = INVALID`; else `applySparsePut(fields, sensorFieldDefs, stored)`. `/status`:
  `ResetErrors === true` → the errcount refill (today's `:434-439`, its comment kept) and `"Valid"`; any other
  `ResetErrors` value → `"Invalid"`; every other key → `"Invalid"`. A flat route → `applySparsePut(body,
  flatFieldDefs, stored)`. Every PUT answers `makeResponse(0, {result: results})`. `applySparsePut()`: an unknown key →
  `INVALID`; a field with `dispatch: true` → `dispatchField(field, raw)`, never stored: an `enum` is `VALID` exactly when
  an option's `value === raw`; a `number` is range-checked by `coerceAndValidate()` and, when it carries `statusPath`,
  written into the status data at that path (`PauseTime`); a `composite` (the LED command) is `INVALID` for a non-object,
  a missing member or one not in `subFields`, or a member failing `coerceAndValidate()`, `FAILED` while
  `Date.now() < busyUntil`, else `VALID` with `busyUntil = Date.now() + T * 1000` (`T` the duration member, its name
  pinned to `_LIGHT_CMD_FIELDS` by A.U23.27's mirror check); a `toggle` is validated as a boolean; a field with
  `alwaysExecuted` → validated, answered `VALID` (never `UNCHANGED`), and stored only when the device's composed data
  already carries the key (so `AmbPres` and `ForceCalRef` read back what was applied and `ContMeas`, which GET cannot
  report, never appears); every other field: invalid → `INVALID`; with `field.resolution = r` the stored and new values
  are compared as `Math.round(v / r)` and the stored value is `Math.round(value / r) * r`; equal → `UNCHANGED`, else
  stored → `VALID`. `composite` non-dispatch fields keep today's all-sub-fields rule. `dispatchRangedAction()`,
  `dispatchLightCmdLed()`, `dispatchSensorQuirkField()`, `applySensorQuirksForGet()` go (their behaviour is the rules
  above); each remaining function's JSDoc states its rule in ≤ 3 lines.
- **Resolved**: A.U9.03 (busy → "Failed") and A.U19.02 (malformed/out-of-range → "Invalid", not "Failed") edit the same
  function; both apply (A.U19.02 names A.U9.03's refusal as kept; M.SRC_NET.122). A.U6.17 (5) keeps "a readback quirk list
  U23 owns" for `ForceCalRef` (400) and `ContMeas` (omitted); A.U25.12 (7) (later) makes `ForceCalRef` read back the last
  applied value, 400 on a fresh mock — with the sample at 400 (M.WEB.045) the generic "always-executed is stored when the
  data carries the key" rule gives both readbacks with no key list (agent decision D8; A.U36.510 (5)'s "reports 400 on
  GET" sentence follows A.U25.12 — Gaps item 4). `SystemCmd`'s whole-value equality mirrors OR122.a (2); the mock answers
  no "Failed" for a refused command (A.S0930.31: stateless).
- **Unit**: U25 (A.U25.12 (7)). Stages: U6 (A.U6.17 routing; A.U6.28/.29/.30 byte and shape checks), U18 (`hostName`,
  `ipv4List`), U23 (A.U23.27/.28/.49 and the rest).
- **Depends**: M.WEB.040, M.WEB.005; M.SRC_NET.018/.045/.075 (the shape rules), M.SRC_NET.120-.123 (outcomes).
- **Blast carried by**: `tests_js/mock-server.test.js` (M.WEB.052), `mock-server-put-matrix.test.js` (M.WEB.060),
  `render.test.js:698-744` (M.WEB.054); shared corpus `tests/_radio_shape_cases.json` read by the vitest
  (A.U6.29/A.U10.41/A.U18.10, TEST_HELP); `tests_scripts/test_js_api_mirrors.py` definitions-vs-`src/` check (A.U23.27,
  TSC); SPEC H.4 mock paragraph and H.6 never-"Unchanged" paragraph (A.U36.510 (5), A.U36.504 (2), SPEC); the float32
  gap sentence (A.U23.49 / A.U11.21 Docs, SPEC).
- **Kind**: code

### M.WEB.042 GET answers: no jitter on time, saturating counters, every mask
- **From**: A.U23.29 (no status jitter; uptimes step and saturate; `UnixTime`; measurement and `WifiTS` stamps; no
  `jitterInPlace()` on time keys), A.U23.28 (every `mask: true` field masked), A.U18.38 (`HotspotPW`), A.U18.37 (read:
  masks only), A.U23.22 (`UnixTime` from the clock), A.U19.10 (`WifiTS`), A.U10.40 (`SysUptime`/`WifiUptime` names).
- **Site**: `js/mock-server.js:277-308` (`jitterInPlace()`), `:446-489` (`handleGet()`, `jitterEachSensorGroup()`).
- **Change**: `handleGet(path)`: `unixTime = Math.floor(Date.now() / 1000)`; `/measurements` → each sensor body's numeric
  leaves jitter as today (nested included, the `:299-301` comment kept) except keys ending `TS` or `Uptime`, and each
  body's `TS` is set to `unixTime`; `/sensors` → the stored sensor config (no override, no filter: dispatch fields are
  never stored, M.WEB.041); `/networking` → the stored config with every field of the section that has `mask: true` set
  to `"********"` (comment "// Mirrors the server's masked GET: a credential is never returned (SPECIFICATION.md A.8)."); `/system`,
  `/notification` → stored; `/status` → `status.system.SysUptime` and `status.networking.WifiUptime` each `+1` per GET only
  while below `COUNTER_CAP`, `status.system.UnixTime = unixTime`, `status.networking.WifiTS = unixTime`, everything else
  served as stored. `jitterInPlace()` JSDoc → "Nudges every numeric measurement leaf by a small random jitter so polled
  values move; a time key (ending TS or Uptime) never jitters." `jitterEachSensorGroup()` stays.
- **Resolved**: —
- **Unit**: U23. Stage U18: A.U18.38's `HotspotPW` mask (with the field's tag) on today's `:461` line.
- **Depends**: M.WEB.040.
- **Blast carried by**: `tests_js/mock-server.test.js:372-445` (M.WEB.052); `tests_js/render.test.js:198-210` (jitter
  window holds); SPEC H.4 mock paragraph (A.U36.510 (5), SPEC).
- **Kind**: code

### M.WEB.043 Compose each device's mock data from one driver-keyed sample table
- **From**: A.U6.06 (2) (`composeMockData()`), A.U6.25 (read: iterates every errcount group), A.U23.18/A.U23.19 (read:
  `statusPath` and maintenance `path` fields), A.U20.16 (read: the default instance key only).
- **Site**: `js/mock-server.js` (new export).
- **Change**: `export function composeMockData(defs, samples)` (`@param {SiteDefinitions} defs`, `@param {MockSamples}
  samples`, `@returns {MockDeviceData}`; JSDoc ≤ 3 lines "Builds one device's mock data: each group takes the sample
  of the driver whose logger name its key equals or prefixes with `_`, filtered to the group's fields."): for each
  measurements/sensors group key K the sample S with `K === S || K.startsWith(\`${S}_\`)`; only the keys that group's
  fields name are copied (a readonly `path` field copies its top-level parent); networking/system/notification configs
  are the samples filtered to the section's fields that carry neither `dispatch` nor `statusPath` (the `build` object
  through its `path`); status groups are filtered to their field keys, a maintenance field read through its `path`
  (`<INSTANCE>` matched to a sample by the same prefix rule); `status.notification.PauseTime` comes from the sample;
  errcount: one entry per module key of every errcount group, from the sample with the longest name S such that `K === S
  || K.startsWith(\`${S}_\`)`, else `{counter: 0, history: []}`; a group with no matching sample throws
  `Error(\`mock samples: no sample for group "<section>/<group>"\`)`.
- **Resolved**: A.U6.06's "copy only the keys that group's fields name" would copy `PauseTime`/`SystemCmd` into GET
  bodies the server never returns them in (H.6.1 row 9; `PauseTime` is read from `/status`, A.U23.18) — dispatch and
  `statusPath` fields are excluded from the config copies (agent decision D8).
- **Unit**: U6.
- **Depends**: M.WEB.045 (`samples.json`), M.WEB.004 (`MockSamples`).
- **Blast carried by**: callers `js/app.js` (M.WEB.031), `tests_js/mock-data-compose.test.js`,
  `definitions-mockdata-coverage.test.js`, `generated-definitions-render.test.js`, `mock-server-put-matrix.test.js`,
  `accessibility.test.js`, `site-functions.test.js` (M.WEB.056/.057/.060/.063/.066); SPEC H.2 `mockdata/` line, K.8
  (A.U36.516/.517, SPEC).
- **Kind**: code

## mockdata/samples.json (new), mockdata/dev.json, mockdata/wozi.json (taken here, Gaps item 1)

### M.WEB.045 One driver-keyed sample table replaces the two per-variant fixtures
- **From**: A.U6.06 (1) (`samples.json`; the two files go), A.U2.25 (catalogued history codes), A.U3.15 (newest-entry
  rule, no SYSTEM warning), A.U15.12 (`FRCState`/`FRCWait`, the three FRC settings, `CFGMGR_SCD30` row), A.U15.18 /
  A.U6.20 (`RestoreTS` 0 = "No timestamp"), A.U15.19 (`VOCState`), A.U15.36/M.SRC_SENS.072 (`CalLight`), A.U18.10
  (`DNSFallback`), A.U18.38 (`HotspotPW`), A.U19.10/A.U23.29 (`HTTPDropped`, `WifiTS`), A.U6.22 (`MemFree`), A.U6.23
  (`ResetReason` = 1, power-on), A.U32.06 (`LastTaskEnd` null), A.U6.24 + A.U10.40 (`build` keys `FirmwareVersion`,
  `WebsiteVersion`, `BuildDate`; every renamed key), A.U25.12 (7) (`ForceCalRef` 400), A.U6.15 (no variant literal), A.U6.29
  (read: accept-shaped sample values), A.U17.19 (read: `UARTLINK` counts).
- **Site**: `mockdata/dev.json`, `mockdata/wozi.json` (deleted); new `mockdata/samples.json`.
- **Change**: `mockdata/samples.json` — `{measurements, sensorsConfig, networkingConfig, systemConfig,
  notificationConfig, status: {networking, system, sensors, notification}, errcount}` per M.WEB.004's `MockSamples`:
  measurements and sensor configs keyed by driver logger name (`SCD30`, `SGP40`, `BMP3XX`, `ISL29125`), seeded from today's
  two files (the `SHTC3`/`MPRLS` rows dropped), every key in the A.U10.40 scheme, plus `SCD30.FRCState` 4,
  `SCD30.FRCWait` null, `SGP40.VOCState` 2, `ISL29125.CalLight` 1, sensor settings `FRCNoise` 20.0, `FRCRate` 10.0,
  `FRCWindow` 60, `ForceCalRef` 400; networking `SSID`, `PW`, `HotspotPW` "12345678", `Country` "DE", `Hostname`
  "SensorNode", `LEDWifiOn`, `NTPHost` "pool.ntp.org", `NTPOffset`, `NTPInterval`, `DNSFallback` "8.8.8.8,1.1.1.1";
  system `DebugLevel`, `GMTOffset`, `DSTOffset`, `build` `{FirmwareVersion, WebsiteVersion, BuildDate}`; status networking
  adds `HTTPDropped` 0 and `WifiTS` (a number), system adds `ResetReason` 1, `MemFree`, `LastTaskEnd` null, `UnixTime`
  null (served from the clock, M.WEB.042), `UTCTime`/`LocalTime` structs with `Year … Yearday`; `status.sensors` `SGP40`
  `{BackupTS: <epoch>, RestoreTS: 0}` and `UARTLINK` `{Transfers, Failures}`; `errcount.<logger base name>` samples
  (`WIFI`, `CFGMGR_WIFI`, `DNSSRV`, `NTP`, `CFGMGR_NTP`, `FRAM`, `SYSTEM`, `CFGMGR_SYSTEM`, `SCD30`, `CFGMGR_SCD30`,
  `SGP40`, `CFGMGR_SGP40`, `BMP3XX`, `CFGMGR_BMP3XX`, `ISL29125`, `CFGMGR_ISL29125`, `NEOPIXEL`, `NOTIFY`,
  `CFGMGR_NOTIFY`, `UART`, `WEBSERVER`) each `{counter, history}` with ten entries, every non-`N` `num` a non-retired
  catalog code of that logger's owner (A.U2.01's table), no two adjacent identical non-`N` entries, `counter` ≥ the
  non-`N` slots, no SYSTEM warning. No value names a device (`Hostname` "SensorNode", not a variant). Every field of every
  device's generated definitions resolves (pinned by M.WEB.056).
- **Resolved**: A.U2.25 and A.U3.15 site the retired files (U2/U3 precede U6); their rules move to `samples.json`
  (A.U6.06 "A-C merges A.U2.25's edit of the retired files into samples.json"). A.U15.12's blast puts FRC fields in
  `mockdata/{dev,wozi}.json` (U15 > U6, after their deletion) — they land in `samples.json`. `CFGMGR_SCD30` gets a sample
  row (it is listed in the definitions whether FRAM-backed or not, M.GEN.016; AC_NOTES 13).
- **Unit**: U32 (`LastTaskEnd`, the latest). Stages: U6 (the file, seeded; the two files deleted), U10 (key renames,
  A.U10.40's script), U11 (`ResetReason`, `MemFree` with A.U6.22/.23), U15 (FRC, `VOCState`, `CalLight`, `RestoreTS`),
  U18 (`DNSFallback`, `HotspotPW`), U19 (`HTTPDropped`, `WifiTS`), U25 (`ForceCalRef` 400 confirmed), U32.
- **Depends**: A.U2.01 (catalog codes, GEN M.GEN.034).
- **Blast carried by**: reader `composeMockData()` (M.WEB.043) via `js/app.js` (M.WEB.031); L0
  `tests_scripts/test_error_catalog.py` mockdata pass (A.U2.25/A.U3.15, TSC); `tests_scripts/test_js_coverage_excludes_json.py:13`
  `("mockdata",)` (A.U6.04, TSC); `tests_js/mock-data-compose.test.js` (M.WEB.056); SPEC H.2 `mockdata/` line, K.8, K.11
  (A.U36.516/.517, SPEC); README `:236-240` (A.U36.516 (7), DOCS).
- **Kind**: code

## tests_js/_generated_definitions.js (new)

### M.WEB.050 One loader for generated definitions and REST references, refusing a stale tree
- **From**: A.U6.05 (1) (helper, id-set guard), A.U24.46 (3) (TOML-hash freshness guard), A.U23.31 (`API_REFERENCES`).
- **Site**: new `tests_js/_generated_definitions.js`.
- **Change**: header (≤ 3 lines) "The one tests_js loader for every device's generated definitions and REST reference
  (build/generated_src/); throws at import when the tree is missing or older than devices/*.toml." Exports
  `GENERATED_DEFINITIONS: Map<deviceId, SiteDefinitions>` from `import.meta.glob("../build/generated_src/definitions/*.json",
  {eager: true, import: "default"})` minus `index.json` and the stamp; `DEVICE_IDS` (sorted `devices/*.toml` stems
  from `import.meta.glob("../devices/*.toml", {query: "?raw", eager: true, import: "default"})`, `zz_test_*` dropped as
  `tests_scripts/_devices.py:18` does); `API_REFERENCES: Map<deviceId, object>` from
  `import.meta.glob("../build/generated_src/api/*.json", …)`. At import: the definitions id set must equal `DEVICE_IDS`
  and be non-empty, every device must have an API reference, and the stamp `build/generated_src/definitions/inputs_stamp.json`
  `{"tomls": {<name>: <sha256 hex>}}` must name exactly the TOMLs and match each one's
  `crypto.subtle.digest("SHA-256", …)` (a top-level `await`); else `throw new Error("generated definitions missing or
  stale: run npm run build:site")`.
- **Resolved**: A.U24.46 (3) places the stamp at `html/definitions/.inputs_stamp.json`; A.U6.04 deletes
  `html/definitions/` and A.U23.38's drift rule fails the build on any other file under `html/` — the stamp lives beside
  the definitions it describes, under gitignored `build/` (settled by A.U6.04/A.U23.38; its writer is SCR's, Gaps item
  6). The stamp has no leading dot so the glob exclusion is explicit, not a dotfile accident.
- **Unit**: U24. Stages: U6 (A.U6.05 helper with the id-set guard), U19/U23 (A.U23.31's `API_REFERENCES` once A.U19.20
  generates them).
- **Depends**: A.U6.02, A.U19.20, A.U24.46 (1)'s generator writes (SCR); `tsconfig.json` `vite/client` types
  (M.WEB.073).
- **Blast carried by**: importers `definitions.test.js`, `mock-data-compose.test.js`,
  `generated-definitions-render.test.js`, `definitions-mockdata-coverage.test.js`, `mock-server-put-matrix.test.js`,
  `live-backend*.test.js`, `api-reference-agreement.test.js`, `accessibility.test.js`, `site-functions.test.js` (this
  cluster's merged test changes); L0 `tests_scripts/test_js_generated_definitions_loader.py` (A.U6.05, TSC); SPEC H.8, E.3
  (A.U36.517 (9), A.U24.46 Docs, SPEC).
- **Kind**: test

## tests_js/poll-manager.test.js

### M.WEB.051 The queue and loop tests follow the new request path and loop
- **From**: A.U23.02 (body-read timeout), A.U23.03 (aborted/queued request), A.U23.04 (visibility), A.U23.05 (back-off,
  `onError`), A.U23.37 (`isBusy` test goes), A.U35.46 (1) (stop during a poll; visibility after stop), A.U24.14
  (trailing restores go), A.U8.21 (`:21` poll step), A.U27.28 (header).
- **Site**: `tests_js/poll-manager.test.js:1-217`.
- **Change**: a ≤ 3-line header "Tests js/poll-manager.js: the single-flight queue, its whole-request timeout and abort,
  and the poll loop's visibility pause and capped back-off." `:61-80`, `:106-124`, `:145-162` hold (the hang test now
  passes `/hangs` through `request()` unchanged). `:126-143` ("isBusy reflects …") goes. `:196-217` → "reports each
  failure through onError and keeps polling at the doubled interval": `onError` spy called once per rejection, ticks at
  10, 20, 40 ms. New: a fetch stub whose headers resolve at once and whose `text()` never settles rejects "timed out"
  after the timeout (fake timers) and the next queued request runs; a body settling one tick before the timeout
  succeeds; a queued request with an already-aborted signal never reaches `fetch` (rejects `AbortError`), an in-flight one
  rejects `AbortError` and the queue advances; hidden source → no tick after the interval, visible again → one immediate
  tick, stop → the fake source's listener count is 0; back-off with interval 3000: 3000, 6000, 12000, … capped at the
  value `_source_constants.js` reads for `POLL_BACKOFF_MAX_MS`, back to 3000 after one success; `stopAfterSuccess` ends
  the loop after the first success; `stop()` while a `pollOnce()` is in flight → after it resolves no further call (two
  intervals advanced); a visibility change after `stop()` runs none. The trailing `vi.useRealTimers()` lines go
  (`:121`'s mid-test one stays: the test then issues a real request). `:21`'s stub delay becomes a named constant
  under `// @tunable l0.poll_manager_poll_ms = 20`.
- **Resolved**: A.U23.05 places "console.error once per episode" in the poll loop's test; the log moves to the section
  (M.WEB.020), so that case is `render.test.js`'s (M.WEB.054).
- **Unit**: U24 (A.U24.14). Stages: U8 (the tag), U23 (everything else), U27 (header, A.U27.28).
- **Depends**: M.WEB.002, M.WEB.003, M.WEB.068 (`_source_constants.js`), M.WEB.067 (`_test_setup.js`).
- **Blast carried by**: Part N row `l0.poll_manager_poll_ms` (A.U8.21, SPEC); `tests_scripts/test_tunables_register.py`
  (A.U8.02, TSC).
- **Kind**: test

## tests_js/mock-server.test.js

### M.WEB.052 The mock tests pin every quirk the server has
- **From**: A.U23.26 (405 code, injected status text, `render.test.js` text), A.U23.27 (derived options), A.U23.28
  (unknown keys, malformed bodies, `ResetErrors`, masks, `group-failure`), A.U23.29 (time stamps, saturating uptimes, no
  timer, `partial-result` test goes), A.U23.30 (int/float policy), A.U23.49 (resolution), A.U9.03 (busy refusal and
  the mock clock), A.U19.02 ("Failed" → "Invalid"), A.U18.38 (`HotspotPW` mask), A.U6.13 (`:143` `Hostname`), A.U6.17
  (SCD30 quirk cases), A.U6.28/A.U6.29/A.U6.30/A.U10.41/A.U18.10 (byte and shape corpus), A.U10.40 (keys), A.U25.12
  (7) (`ForceCalRef` readback), A.S0930.20 (4) (two words, near misses), A.U24.14 (restores), A.U27.28 (header).
- **Site**: `tests_js/mock-server.test.js:1-549`.
- **Change**: header (≤ 3 lines) "Tests js/mock-server.js against the real server's answers: envelopes, every PUT
  outcome, GET masks and time values, and the composed data." Fixture definitions `:40-150` carry the options, bounds,
  `dispatch` and `alwaysExecuted` flags the tests rely on, keys per A.U10.40 (`LightCmdLED` `R/G/B/T`); `Hostname`
  `"fixture-host"`. `:178-195` hold; new resolution cases (stored 12.35, PUT 12.345 → "Unchanged", 12.36 → "Valid");
  `:196-212` `ResetErrors` assert the result, plus `ResetErrors: false` → "Invalid"; `:224-244` (`SystemCmd`): both new
  words → "Valid", never persisted, a repeat "Valid", and the near-miss list of A.S0930.20 (4) each "Invalid"; a fixture
  with a fourth option is accepted (derived); `SystemCmd` sent to `/networking` → "Invalid"; `:272-314` (`LightCmdLED`):
  malformed/out-of-range/missing/extra member → "Invalid", back-to-back accepted commands → "Valid" then "Failed", and
  "Valid" again after `vi.setSystemTime` passes `T`; SCD30 cases: `AmbPres` never "Unchanged", `ForceCalRef` reads back
  900 after a 900 PUT and 400 on a fresh install, `ContMeas` never appears on GET; `:316-340` per A.U25.12; `:372-383`
  masks gain `HotspotPW`; `:385-445`: `TS` equals the mock clock, `SysUptime` seeded at `COUNTER_CAP - 1` gives
  `COUNTER_CAP` on two GETs, `LocalTime` unchanged over ten GETs, nested measurement jitter holds; two GETs with
  `delayMs` unset resolve with no timer advanced; `:469-480` → an unknown sensor answers "Invalid" and the real ones
  still apply; `:481-486` → code 405; `:498-508` → the catalog's text; `:510-519` hold, plus bodies `"[1,2]"` and
  `"nope"` → HTTP 200 code 1; `group-failure` → every attempted key "Failed"; `:539-549` (`partial-result`) goes;
  float field `50` → Valid and stored 50, int field `5.5` → Invalid, `5` → Valid, `true` → Invalid; one
  corpus-driven `it.each` per shape over `tests/_radio_shape_cases.json` (accept → "Valid", reject → "Invalid"); a
  32-character SSID of 2-byte characters → "Invalid", 16 → "Valid". Trailing restores (`:400-403`) go.
- **Resolved**: A.U9.03's "Failed for out-of-range" expectations at `:272-314` are A.U19.02's "Invalid" (A.U19.02 keeps
  only the busy refusal "Failed", M.SRC_NET.122).
- **Unit**: U25 (A.U25.12). Stages: U6 (A.U6.13/.17/.28/.29/.30), U9 (busy), U10 (keys), U18 (`HotspotPW`, shapes), U19
  (LED "Invalid"), U23 (A.U23.26-.30/.49, A.S0930.20 (4)), U24 (restores), U27 (header).
- **Depends**: M.WEB.040-.042.
- **Blast carried by**: the shape corpus file `tests/_radio_shape_cases.json` (A.U6.29/A.U10.41/A.U18.10, TEST_HELP).
- **Kind**: test

## tests_js/definitions.test.js

### M.WEB.053 Definitions tests read generated files and the source, not copies
- **From**: A.U6.05 (2) (generated definitions, neutral id), A.U6.08 (read: the per-device render half is its own
  file), A.U23.01 (new single-flight case), A.U23.09 (upper bound), A.U23.10 (cases hold), A.U23.16 (`defaultValue`
  cases go), A.U23.37 (major and timeout from the source reader), A.U24.14 (restores), A.U27.28 (header).
- **Site**: `tests_js/definitions.test.js:1-300`.
- **Change**: header (≤ 3 lines) "Tests js/definitions.js: the validator's rejections, the value resolver and the
  loader, against fixtures and every device's generated definitions." The two JSON imports go; `it.each([...GENERATED_
  DEFINITIONS])("accepts the generated %s definitions", …)` replaces `:209-210`; `MINIMAL_VALID`'s id and the stub paths
  use `"fixture-device"`; `SUPPORTED_SCHEMA_MAJOR` and the `:295` timeout come from `_source_constants.js` (`readConst
  ("../js/definitions.js?raw", "SUPPORTED_SCHEMA_MAJOR")`, likewise `DEFAULT_TIMEOUT_MS` from `poll-manager.js`); `:81-95`
  gain the upper bound (2**31 rejected, 2**31 − 1 accepted, for both intervals); `:242-253` and the `defaultValue` half of
  `:254-258` go (the null pass-through case stays, without `defaultValue`); new: while a `pollManager.request()` is
  pending, `loadDefinitions()` issues no fetch until it settles (a stub counting concurrent fetches never sees 2). The
  hang test's stub and assertion hold. Trailing `vi.useRealTimers()` go.
- **Resolved**: —
- **Unit**: U24 (restores). Stages: U6 (generated imports), U23 (A.U23.01/.09/.16/.37), U27 (header).
- **Depends**: M.WEB.050, M.WEB.068, M.WEB.005-.007.
- **Blast carried by**: —
- **Kind**: test

## tests_js/render.test.js

### M.WEB.054 Render tests follow every renderer change and add the new behaviours
- **From**: A.U23.03, .05, .08, .11, .12, .13, .14, .15, .16, .17, .18, .19, .23, .26 (`:323`, `:851`), .27
  (`:698-744`), .29 (`:1015-1037`), .30, .36, .40, .42 (banner asserts), A.U19.15 (`:851`), A.U10.40 (`:129`,
  `:708-775`), A.U24.14 (`:406-414`, `:886-929`), A.U24.48 (`:18` disable reason), A.U36.544 (4) (`:86`, `:958`
  pointers), A.U8.21 (`:11`, `:20`, `:665` waits), A.S0930.20 (5), A.S0930.34 (read: `:583-640` hold), A.U6.17 and
  A.U9.03 (read: dispatch and `:746-764` cases hold), A.U27.28 (header).
- **Site**: `tests_js/render.test.js:1-1038`.
- **Change**: header (≤ 3 lines) "Tests js/render.js against js/mock-server.js and local fetch stubs: rendering,
  in-place refresh, every Apply outcome and the section's failure path." `:5-6` comment → "// Polls `check` instead of a
  fixed sleep: some flows chain two requests, so a fixed wait would be flaky or slow."; `:11` `2000` → a named constant
  under `// @tunable l0.render_wait_timeout_ms = 2000`, `:20`'s `10` under `// @tunable l0.render_poll_ms = 10`, `:665`'s
  `5000` under `// @tunable l0.render_banner_wait_ms = 5000`; `:18` disable gains "-- each retry waits out the previous
  delay before rechecking" (its comment line above goes). Fixtures: `lightCmdLED` → `LightCmdLED` with `R/G/B/T`; `:84-86`
  comment → "// A plain toggle: no dispatch or alwaysExecuted flag, so the mock stores and echoes it (SPECIFICATION.md
  Part H.4)."; the status fixture's sections carry what each test needs. Changed expectations: `:323` → "Command executed
  — MeasInt: Valid"; `:382-415` comment "rebuild" → "update"; the latency comment `:399-401` → the fake-timer switch's
  plain reason; `:417-466` → the mock answers `{"ResetErrors": "Valid"}` and it is read; a local stub answering
  `{"ResetErrors": "Failed"}` shows Failed; the second click of `:458-466` → the toggle is Off after the first Apply,
  so "Nothing to submit"; `:468-535` (describe "… defaultValue") → an always-executed toggle with no GET value renders
  "—", is not submitted until set, is submitted `false` once set Off, returns to "—" after Apply; `:540-600` hold plus a
  dispatch toggle left Off gives "Nothing to submit"; `:583-620` gain: choosing "Erase FRAM" and Apply sends one PUT
  `/system` with body exactly `{"SystemCmd":"erasefram"}` and calls `window.confirm` zero times (spy), the same for
  "Reset to defaults", the select returns to "Select…"; `:647-666` hold with `data-shown`; `:668-676` gains "and a later
  tick recovers it"; `:678-722` hold plus `"  "`, `"0x10"`, `"1e3"`, `"1,5"` each PUT the raw string and show Invalid,
  `" 12 "` PUTs 12; `:698-744` both cases expect "Invalid" and are renamed "… reports Invalid for …"; `:746-764` gains
  sub-inputs cleared after Valid; `:783-812` → "reads maintenance data by path" (`path: ["SGP40", "BackupTS"]`) plus two
  instances `SGP40` and `SGP40_x` each showing their own value; `:845-880` hold through the generic `/status` sub-fetch
  (`:851` code 4 → 404); `:882-930` in-place refresh holds; `:958` pointer → "(SPECIFICATION.md C.5.3)"; `:1015-1037`
  builds its response with a local fetch stub and is renamed "… (defensive fallback)". Banner assertions read
  `dataset.shown`. New: stop during a pending GET → no banner, no card appended after it settles, the next section's
  first GET is not queued behind the old one's timeout; the same readonly `.field-value` node survives three polls; focus
  on "Show all" survives a poll; a writable field's caption refreshes through its `path`; `/status` with `system:
  {"error":"unavailable"}` renders "unavailable" in every System Status field and the card's `data-source-state`; a body
  without `errcount` renders every row "no data"; an `{"error":"unavailable"}` entry renders that row "unavailable"; a
  PUT result `{"X": "Weird"}` marks the card `failed` and shows "X: Weird"; `PUT /sensors` answered `{"result": {"SCD30":
  "Invalid"}}` marks every submitted SCD30 field Invalid; a second Apply whose result omits a field clears that field's
  previous colour; an Invalid field keeps its text while a Valid sibling is cleared; a toggle/enum baseline follows the
  post-write GET; the Apply button stays disabled until the post-write GET settles; PUT `{"MeasInterval":"Valid"}` then
  refresh HTTP 500 → the field keeps `data-apply-status="valid"`, the banner shows, the button is enabled again, no
  `unhandledrejection` (spy); Clear sends exactly `{"DNSFallback": ""}` after confirm and nothing on cancel, and an Apply
  with the input blank never sends the key; a networking section with an errcount group renders the `DNSSRV` row from
  `/status`; the Altitude warning cases of A.U23.23 (baseline 1013 → shown; 0 → hidden; cleared → hidden; typed `0` →
  hidden; baseline 0 and typed `1000` → shown); typing `50` into a float field PUTs the JSON number `50`; the masked-
  field cases of A.U23.36 (`PW` and `HotspotPW`: input `""`, placeholder and caption the eight dots, an SSID-only Apply
  sends no `PW`, a typed password is sent exactly); the hostile-key fixture of A.U23.40 (group `g"]`, fields `a"] [x="`,
  `b\\c`, `d e`) renders, collects, PUTs all three keys and colours each wrapper; three consecutive failing ticks log
  `console.error` once, and a success then a failure logs again. Trailing restores (`:406-414`, `:886-929`) go.
- **Resolved**: A.U23.14 says `:458-466` (second ResetErrors) holds and A.U23.15 (later in the same unit, and the
  behaviour it adds) turns it into "Nothing to submit" — A.U23.15's expectation stands. A.U23.05's "console.error once"
  case lands here (M.WEB.051's note). A.U36.544 (4) ":86 H.7 → H.4" applies to the comment A.U6.17 makes false (the mock
  no longer special-cases a name): the comment is rewritten with the H.4 pointer.
- **Unit**: U24 (A.U24.14/.48). Stages: U8 (tags), U10 (keys), U19 (`:851`), U23 (behaviour cases and A.S0930.20 (5)),
  U27 (header), U36 (pointers — folded into the U23 rewrite of the same lines where those lines change; `:958` alone
  lands in U36).
- **Depends**: M.WEB.018-.022, M.WEB.040-.042, M.WEB.067.
- **Blast carried by**: Part N rows `l0.render_*` (A.U8.21, SPEC).
- **Kind**: test

## tests_js/definitions-shape-corpus.test.js (new)

### M.WEB.055 Both validators read one shape corpus
- **From**: A.U6.16 (3) (vitest half), A.U23.09 (two bound cases), A.U23.10 (one case per rejection), A.U6.19/.27/.28/
  .29/.30, A.U23.17/.18/.20/.23/.49 (hint-key cases via A.U23.10).
- **Site**: new `tests_js/definitions-shape-corpus.test.js`.
- **Change**: header (≤ 3 lines) "Runs js/definitions.js's validator over tests_scripts/definitions_shape_cases.json, the
  corpus tests_scripts' Python shape check reads too, so the two agree."; `import cases from
  "../tests_scripts/definitions_shape_cases.json"`; `it.each(cases)("$name", ({definitions, valid}) =>
  expect(validateDefinitions(definitions).length === 0).toBe(valid))`.
- **Resolved**: —
- **Unit**: U23 (the last cases). Stage U6: the file and HEAD's rejections.
- **Depends**: the corpus file (A.U6.16, TSC).
- **Blast carried by**: `tests_scripts/test_buildgen_definitions.py`'s pytest half (TSC).
- **Kind**: test

## tests_js/generated-definitions-render.test.js (new), tests_js/mock-data-compose.test.js (new)

### M.WEB.056 Every device's definitions validate and render; composed data covers every field
- **From**: A.U6.08 (render test), A.U6.06 (compose test), A.U6.25 (read: union of errcount groups), A.U23.04/.07
  (read: render takes a context; stop handles called).
- **Site**: new `tests_js/generated-definitions-render.test.js`, new `tests_js/mock-data-compose.test.js`.
- **Change**: render test (header ≤ 3 lines) — `describe.each(DEVICE_IDS)`: `validateDefinitions(defs)` is `[]`;
  `loadDefinitions()` accepts it through an inlined `<script type="application/json">` element; for every section,
  `renderSection(defs, section, mainEl)` against `installMockFetch(defs, composeMockData(defs, samples))` renders one
  `[data-group-key]` per group and one `[data-field-wrapper-key]` or errcount row per field/module, with no
  `console.error` (spy) and the banner's `data-shown` not `"true"`; each stop handle and uninstall called. Compose test
  (header ≤ 3 lines) — for every device: every field of every group resolves to a value of its kind (number, boolean,
  string, an enum member, readonly present, `gmtimestruct` a struct, `lasttaskend` null or the `{Task, Uptime}` object),
  no composed key is outside the definitions, every errcount module key has an entry, every sample history `num` is a key
  of the definitions' `codes` E/W tables; a group with no matching sample throws.
- **Resolved**: A.U6.06 checks history codes against "U2's catalog" — the browser reads the catalog's non-retired codes
  through the generated `codes` block (A.U2.21) instead of importing `buildgen/error_catalog.json`.
- **Unit**: U32 (`lasttaskend` kind). Stage U6 (both files).
- **Depends**: M.WEB.043, M.WEB.045, M.WEB.050.
- **Blast carried by**: SPEC H.8 test list (A.U36.517 (9), SPEC).
- **Kind**: test

## tests_js/definitions-mockdata-coverage.test.js

### M.WEB.057 The coverage check runs per device over composed data, by path
- **From**: A.U6.06 (`it.each(DEVICE_IDS)` over `composeMockData()`), A.U23.19 (the mirrored resolver uses the path),
  A.U23.18 (read: `statusPath` fields), A.U23.16 (read: no `defaultValue` fallback), A.U15.12 (read: SCD30 FRC fields
  resolve).
- **Site**: `tests_js/definitions-mockdata-coverage.test.js:1-126`.
- **Change**: header (3 lines) "Every readonly field a device's generated definitions name must resolve against that
  device's composed mock data, through the site's own resolver." The four JSON imports go;
  `GENERATED_DEFINITIONS`/`DEVICE_IDS` and `samples.json` are imported; the local `groupValuesFrom()` mirrors
  M.WEB.020's rules (no flattening; maintenance by `path`; `statusPath` from the status data) with its comment
  unchanged in substance; `:223-224` comment → "// Only readonly fields: a command-only trigger is never echoed in a
  GET."; the two per-variant `it`s become one `it.each(DEVICE_IDS)("every readonly field %s's definitions name
  resolves in its composed mock data", …)`; the two self-checks `:257-275` stay.
- **Resolved**: —
- **Unit**: U23. Stage U6 (per-device rewrite).
- **Depends**: M.WEB.043, M.WEB.050.
- **Blast carried by**: —
- **Kind**: test

