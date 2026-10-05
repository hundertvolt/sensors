# A-C merge WEB (HEAD dd06040)

Scope: CLUSTERS.md "## WEB" — `js/` (9 files at HEAD plus `js/api-contract.js`, `js/shell.js` born by actions),
`tests_js/` (16 files at HEAD plus the files actions create), `eslint.config.js`, `package.json`, `package-lock.json`,
`tsconfig.json`, `.nvmrc`. Taken here because no cluster lists them and every action on them is a website action
(GEN's precedent with `buildgen/limits.py`): `mockdata/` (`dev.json`, `wozi.json`, new `samples.json`),
`vitest.config.js`, `tsconfig.node.json` and the new `tsconfig.base.json` (Gaps, item 1). Read at HEAD dd06040: every `js/` module,
the config files, `mockdata/`, the two command modules, `_put_field_cases.js`, `vitest-commands.d.ts` and five test files
(`live-backend*.test.js`, `poll-manager.test.js`, `definitions-mockdata-coverage.test.js`, `mock-server-put-matrix.test.js`)
in full; the other six test files in full for every site an action names and their fixtures, plus a grep of each for
every name, key, pointer and comment form a merged change touches (results folded into M.WEB.052-.059);
`package-lock.json` is generated and was not read line by line. M-ID numbers are grouped by file and leave gaps.

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
  minutes"), `resetconfig` "Reset to defaults", `erasefram` "Erase FRAM"; the `SystemCmd` and `ResetErrors` fields carry
  `"confirm": true` — the page asks before it sends either, the API stays one command per request (OR140.a (3), A-C
  review fold; M.GEN.015).
- **`/status` keys** (M.GEN.008/.014): networking `IPv4` (no `IP`: routine settlement "status-ip-and-ipv4", A-C
  review fold), `Subnet`, `Gateway`, `DNS`, `RSSI`, `NTPSynced`,
  `NTPLastSyncAge`, `NTPLastSync` (epoch), `HTTPDropped` (the last 24 hours, hourly resolution), `WifiTS` (epoch),
  `Connected`, `Mode`, `WifiUptime`; system `SysUptime`, `BootSignature`, `ConfigFaults` (a list of module names, empty
  when none; A-C review fold), `ResetReason` (codes 0-10, 20; M.SRC_CORE `_RR_*`: 1 power-on, 7 config reset, 8 FRAM
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
- **Blast carried by**: callers `js/definitions.js` (M.WEB.007), `js/app.js` (M.WEB.031), `js/render.js` (M.WEB.020),
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
  goes) and the count increments only while `intervalMs * 2 ** (k - 1) < POLL_BACKOFF_MAX_MS` (a bounded counter, OR103); afterwards, unless stopped, a timer is armed only when `!visibility.isHidden()`; a
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
  (`defaultValue` also on `Calibrate`; goes with the grammar key); OR140.a (3) (`confirm`), (16) (`defaultDecimals`)
  (A-C review fold).
- **Site**: `js/definitions.js:1-56` (header typedef block, the four inline comments).
- **Change**: header prose `:2-4` unchanged. Typedefs: `SpecialValue` → `{value: number|string|null, meaning:
  string}`; `FieldDef` → `{key, label, unit?, kind: "readonly"|"number"|"string"|"enum"|"toggle"|"composite",
  description?, min?, max?, minLength?, maxLength?, mask?, options?, specialValues?, subFields?, onLabel?, offLabel?,
  format?: "gmtimestruct"|"epoch"|"lasttaskend", float?, resolution?: number, dispatch?: boolean, alwaysExecuted?:
  boolean, path?: string[], statusPath?: string[], decimals?, byteLength?: boolean, shape?:
  "hostLabel"|"countryCode"|"hostName"|"ipv4List", clearable?: boolean, ignoredWhenSet?: string, codes?: Record<string,
  string>, codeTones?: Record<string, "good"|"neutral"|"warn">, confirm?: boolean}` (no `defaultValue`); `SiteDefinitions`
  gains `defaultDecimals?: number` (the page's decimals for a non-integer number whose field carries none, M.GEN.018); `ErrcountGroup` gains `codes?: {E:
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
  (`lasttaskend`); U23 also `confirm` and `defaultDecimals` (A-C review fold).
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
  (M.WEB.060), `tests_js/live-backend-put-matrix.test.js` (M.WEB.063); `resolveFieldValue()` callers `js/render.js`
  (M.WEB.020), `js/templates.js` (M.WEB.014), `tests_js/definitions-mockdata-coverage.test.js` (M.WEB.057),
  `tests_js/definitions.test.js:242-253` (M.WEB.053); `tests_scripts/test_definitions_js_mirrors.py` regexes
  (A.U6.16/A.U23.37, TSC); the no-`defaultValue` grammar (M.GEN.046, M.SRC_SENS.072, SCD30 tag A.U23.16 — SRC_SENS).
- **Kind**: code

### M.WEB.006 The validator rejects every malformed shape, naming where
- **From**: A.U23.10 (non-object groups/fields, key/label/kind, composite, duplicates, writable-without-put, split for
  the ceiling), A.U23.09 (upper bound on both poll intervals), A.U6.16 (3) (`decimals` via `MAX_DECIMALS`), A.U6.19 (4)
  (`format`), A.U6.27 (3) (`codes` blocks), A.U23.20 (`codeTones`), A.U6.28 (2) (`byteLength`), A.U6.29 (3)/A.U6.30
  (`shape`), A.U23.17 (`clearable`), A.U23.18 (`statusPath`), A.U23.23 (`ignoredWhenSet`), A.U23.49 (`resolution`),
  A.U5.18 (ceiling pinned), A.U6.08 (read: every device's generated definitions must pass); OR140.a (3), (16) (A-C review fold).
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
  field, `alwaysExecuted` a boolean, `confirm` a boolean on an `enum` or `toggle` field; at the top level
  `defaultDecimals`, when present, an integer `0..MAX_DECIMALS`. Each message names its `where` path. No function exceeds the ESLint `complexity`
  ceiling (M.WEB.070).
- **Resolved**: A.U23.10 lists the U23 hint keys and A.U6.27-.30 the U6 ones in the same `validateFieldHints()` — one
  function holds them; A.U10.41/A.U18.10 add `hostName`/`ipv4List` to A.U6.29's mechanism (no separate validator change
  named; the value set follows the tags, M.SRC_NET.043).
- **Unit**: U32 (`lasttaskend` joins the `format` set, A.U32.06). Stages: U6 (A.U6.16/.19/.27/.28/.29/.30), U18
  (`hostName`, `ipv4List`), U23 (A.U23.09/.10/.17/.18/.20/.23/.49 and the split; `confirm`, `defaultDecimals`, A-C review fold).
- **Depends**: M.WEB.004, M.WEB.005; A.U6.16's shared corpus file (TSC).
- **Blast carried by**: `loadDefinitions()` (M.WEB.007); every device's generated definitions pass (A.U6.08,
  M.WEB.056); `tests_js/definitions.test.js` (M.WEB.053); `tests_js/definitions-shape-corpus.test.js` and
  `tests_scripts/definitions_shape_cases.json` gain one case per rejection (A.U6.16/A.U23.10, M.WEB.055 and TSC);
  `_shape_problems()` mirror (A.U6.16/A.U23.09/.10, TSC); `js/templates.js:158` "number or string" fallthrough sees no
  unknown kind (M.WEB.014); SPEC H.4 "Definitions validation" row (A.U36.510 (2), SPEC); complexity ceiling
  (M.WEB.070); the Python shape mirror accepts the two keys → M.TSC.039.
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
  keys), A.U23.22 (read: `UnixTime` has no `format`), A.U23.32 (read: the live matrix stops importing this module); OR140.a (16) (the site default), OR138.a (1)
  (`ConfigFaults`, a list) (A-C review fold).
- **Site**: `js/field-format.js:1-40`.
- **Change**: header → "Pure field-value formatting with no DOM dependency: templates.js puts its text into the page.
  / See SPECIFICATION.md Part H.8.1." (2 lines; the Node-harness reason goes, below). `:5-7` comment → "// A narrow
  local shape: the formatter reads only these members; a real FieldDef satisfies it structurally." and the typedef
  gains `specialValues?: {value: unknown, meaning: string}[]`. `import { GMTIME_KEYS } from "./api-contract.js";`.
  `export function formatFieldValue(field, value, context = { deviceNowS: null })` with `@param {{deviceNowS: number |
  null, defaultDecimals?: number}} [context]`, in this order: (1) `field.format === "epoch"` and `(field.specialValues ?? []).find((s) => s.value
  === value)` → that special's `meaning` (so `null` → "None since boot" and the shared no-timestamp value → "No
  timestamp", A.U6.20/A.U15.18); (2) `undefined`/`null` → "—"; (3) `mask` → eight "•"; (4) `enum` → option label or
  `String(value)`; (5) `gmtimestruct` → when `value` is a non-null object and each `GMTIME_KEYS` member is a finite
  integer, `Y-MM-DD hh:mm:ss` read through `GMTIME_KEYS` (comment "// Real shape: the generated module's
  _gmtimestruct_to_dict() (buildgen/codegen.py); Weekday/Yearday unused."), else "invalid time value"; (6)
  `lasttaskend` → when `value` is an object with a string `Task` and a finite integer `Uptime`, `` `${Task} at uptime
  ${Uptime} s` ``, else "invalid value"; (7) `epoch` → a non-number passes to (9); `context.deviceNowS === null` →
  "age unknown"; `age = deviceNowS - value`; `age < -5` → "clock mismatch"; else with `a = Math.max(age, 0)`: `a < 120`
  → `` `${a} s ago` ``, `a < 7200` → `` `${Math.floor(a / 60)} min ago` ``, `a < 172800` → `` `${Math.floor(a / 3600)} h
  ago` ``, else `` `${Math.floor(a / 86400)} d ago` ``; (8) `decimals` (unchanged, its 3-line comment kept); (8a) a
  finite non-integer number with no field `decimals` → `value.toFixed(context.defaultDecimals)` when the context carries
  it (the site default from the definitions: 2-3 decimals on the page, full resolution in the API, owner, 2026-10-02);
  (8b) an array → its items joined with ", ", an empty one "none" (`ConfigFaults`); (9) `String(value)`.
- **Resolved**: A.U6.13 (`sensortask_<device>` wording) and A.U36.544 (1) ("the function's current home, grep in
  `src/`") rewrite the same comment; the function is emitted by `buildgen/codegen.py` (M.GEN.008), not in `src/` —
  that home is named. The header's "so a Node-context test harness can reuse it" is no longer true once A.U23.32 moves
  `_live_matrix_command.js` and the live matrix test to the independent `_expected_display.js` (adherence: comments
  state the current state, CLAUDE.md). The `lasttaskend` display text is not worded by A.U32.06 ("in the existing
  style") — agent decision D2.
- **Unit**: U32 (A.U32.06). Stages: U6 (A.U6.13 comment — superseded by this text at U23), U23 (everything but (6); (8a)
  and (8b) with M.GEN.018 and the `ConfigFaults` row, A-C review fold).
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
  as text in place), M_SRC_SENS GAP-12 (`Calibrate` dispatch toggle with no GET value); OR140.a (8) (reset-reason codes clickable (A-C review fold)).
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
  decision D4). The code-value button's look is CSS's (M.GEN.062). OR140.a (8) (owner, 2026-10-02): the reset-reason numbers are
  clickable like errno/wrnno — `ResetReason` carries `codes` and no `codeTones` (M.GEN.014/.034), so it renders as
  this code-value button with its description; no further code (A-C review fold).
- **Unit**: U23. Stage U6: the byte and host-label hint parts (A.U6.28/.29).
- **Depends**: M.WEB.012; M.GEN.062 (CSS for `.code-description`, `[data-code-tone]`, `.field-warning`; the
  `.field-value.code-value` button reset and the muted `.code-number` are Gaps item 5).
- **Blast carried by**: callers `buildFieldGroupCard()` (M.WEB.015); `tests_js/templates.test.js` (M.WEB.058) and
  `tests_js/accessibility.test.js` (M.WEB.080); SPEC H.3 hook list (A.U23.42 Docs, SPEC).
- **Kind**: code

### M.WEB.015 Cards build once, update in place, and reset after Apply
- **From**: OR140.a (16) (the display context carries `defaultDecimals` to `formatFieldValue()` (A-C review fold)), A.U23.08
  (`updateFieldGroupValues()`), A.U23.15 (`resetControl()`), A.U23.40 (`groupIndex`), A.U23.21
  (context through the update functions), A.U23.11 (unavailable), A.U23.23 (sibling label), A.U6.18 (read:
  `submitLabel` rendered at `:201` — holds), A.U23.16 (reset to unset).
- **Site**: `js/templates.js:176-209` `buildFieldGroupCard()`; new functions after it.
- **Change**: `export function buildFieldGroupCard(group, currentValues, groupIndex, display)` — `display`:
  `{deviceNowS: number | null, defaultDecimals?: number, isUnavailable: (field: FieldDef) => boolean}`; each field built by `buildField(field,
  resolveFieldValue(field, currentValues), Boolean(group.submit), \`field-${groupIndex}-${fieldIndex}\`, {deviceNowS,
  defaultDecimals: display.defaultDecimals, unavailable: display.isUnavailable(field), siblingLabel})`, `siblingLabel` = the label of the group field whose key
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
- **Blast carried by**: `showBanner()`/`hideBanner()` (M.WEB.022; pointer fixed, gap pass G2); `tests_js/templates.test.js`, `render.test.js` banner
  assertions (M.WEB.058/.054).
- **Kind**: code

## js/render.js

### M.WEB.018 Collect a sparse PUT exactly
- **From**: A.U23.14 (strict number parse, collection rules, JSDoc), A.U23.16 (unset always-executed toggle), A.U23.40
  (`CSS.escape` in selectors), A.U6.17 (read: the flags; "render.js consults the flag only for toggle/enum"), A.U23.30
  (read: JSON numbers sent as `JSON.stringify` writes them — holds), A.U10.40 (read: composite member keys come from the
  definitions).
- **Site**: `js/render.js:16-40` `readInputValue()`, `:61-125` `collectGroupBody()`.
- **Change**: new private `parseNumberInput(text)` — `text.trim()` matching `/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/u` (non-capturing groups: ESLint's
  `prefer-named-capture-group` is on) → `Number(trimmed)`,
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
  `tests_js/live-backend-put-matrix.test.js` `willRoundTrip` (M.WEB.063); SPEC H.4 sparse-PUT row (A.U36.505, SPEC).
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
  resolves against the whole body); OR140.a (16) (`defaultDecimals` in the display context) (A-C review fold).
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
  `display = {deviceNowS: context.deviceClock?.nowS() ?? null, defaultDecimals: defs.defaultDecimals, isUnavailable}` where `isUnavailable(field)` is true when
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
  M_SRC_CORE GAP-G13 (read: `coerce_numeric()` no longer exists); OR140.a (3) (confirmation before every system command
  and the error-history clear (A-C review fold)).
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
  the `:203-205` comment → "// Nothing changed: skip the round trip rather than PUT an empty body."); else, for every
  key of `body` whose field carries `confirm: true` (definitions-driven, never a key list), `window.confirm(\`${what}?\`)`
  first — `what` the chosen option's label for an enum ("Reset to defaults?", "Reboot?"), the group's `submitLabel` for
  a toggle ("Reset All Errors?") — and a declined one sends nothing (the controls stay as set; the API stays one command
  per request, owner, 2026-10-02); then `await send(body)`. Clear: for each `[data-clear-for]` button of the card, a click → `if (!window.confirm(\`Clear
  ${field.label}?\`)) return;` → `await send({[field.key]: ""})` (never merged with the card's body). Warning: for each
  field with `ignoredWhenSet`, an `input` listener on the field's and the sibling's controls sets the warning's
  `dataset.shown` to `"true"` exactly when the field's input is non-empty and the sibling's effective value — its typed
  input through `parseNumberInput()` when non-empty and a finite number, else `resolveFieldValue(sibling,
  baselines.get(card))` — is a non-zero number, else `"false"`.
- **Resolved**: A.U0.53 (U0) relabels `:264-266`; A.U23.45 (U23, same lines) shortens it to one line ending "(SPECIFICATION.md
  Part H.4)" — the later text stands, its provenance moves to H.4's divergence row (A.U23.45). A.U24.48's `-- <reason>`
  makes the `:260-261` comment a duplicate, so the reason lives once, in the disable comment. GAP-G13's rename makes
  `coerce_numeric()` a stale name (adherence: a comment names the current fact). OR121/OR122: the two new commands use
  the existing dropdown and Apply; OR140.a (3) (owner, 2026-10-02, the most recent) adds the browser's confirmation
  before every system command and before clearing the error history, beside the DNS fallback Clear's (A.U23.17, owner
  OR56.a (2)) — A.S0930.20 (5)'s zero-dialog pin inverts (M.WEB.054; A-C review fold).
- **Unit**: U24 (A.U24.48's reason). Stages: U0 (A.U0.53's relabel — superseded at U23), U23 (everything else, the
  `confirm` dialogs with M.GEN.015's flags).
- **Depends**: M.WEB.015, M.WEB.018, M.WEB.019, M.WEB.020; A.U24.48's plugin (M.WEB.070/.071).
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
  seam); OR140.a (15) and the owner's `website-accessibility` note (the Back button walks the sections (A-C review fold)).
- **Site**: new `js/shell.js`.
- **Change**: header (3 lines) "The page shell both entries share: the nav, section switching, the device watch and
  one stop handle. / Takes every document-derived input from its entry (SPECIFICATION.md Part H.2, H.3)." Imports
  `initNav` (`./nav.js`), `pollManager`, `startPolling` (`./poll-manager.js`), `renderSection` (`./render.js`). Typedef
  `DeviceClock` = `{nowS: () => number | null, observe: (statusBody: unknown) => void}` (JSDoc, imported by
  `render.js`). `/** Device watch cadence: the clock and the build compare. */` / `// @tunable
  web.device_watch_interval_ms = 60000` / `const DEVICE_WATCH_INTERVAL_MS = 60000;`. `export function visibilityOf(doc)`
  → `{isHidden: () => doc.visibilityState === "hidden", onChange: (cb) => { doc.addEventListener("visibilitychange",
  cb); return () => doc.removeEventListener("visibilitychange", cb); }}` (`@param {Document} doc`, `@returns
  {Visibility}`). `export function historyOf(win)` → `{current: () => <the section key in win.location.hash, "#<key>", or null>,
  push: (key) => win.history.pushState({section: key}, "", "#" + key), onPop: (cb) => { listener on "popstate" calling
  cb(current()); returns its removal }}` (`@param {Window} win`); `export function startShell({defs, elements,
  keyTarget, visibility, history, reload})` (`elements` =
  `{appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl}`, `keyTarget: EventTarget`, `reload: () => void`; `@returns
  {() => void}`): the clock — `offsetS = null`; `observe(body)` sets `offsetS = UnixTime - Date.now() / 1000` when
  `body.system.UnixTime` is a number; `nowS()` → `null` before that, else `Math.floor(Date.now() / 1000 + offsetS)`; the
  Apply count — `applyTracker.begin()` increments, `end()` decrements and calls `reload()` when a reload is pending and the
  count is 0; `nav = initNav({...elements minus mainEl, defs, keyTarget, onSelect: (key) => selectSection(key, {push: true})})`;
  a menu selection of another section pushes one history entry (`history.push(key)`), and `history.onPop` selects the
  popped section without pushing, so the browser's Back and Forward walk the sections opened from the menu (owner,
  2026-10-02); `selectSection(key)`
  finds the section (`if (section === undefined) { return; // unreachable - narrows the type for tsc: keys come from
  defs.sections }`), stops the current one, `nav.setCurrent(key)`, `stopSection = renderSection(defs, section,
  elements.mainEl, {visibility, deviceClock, onRecovered: watchOnce, applyTracker})`; `watchOnce()` — `GET /status`
  through `pollManager.request()` → `deviceClock.observe(body)`; `GET /system` → when `body.build` is an object, its
  `JSON.stringify()` is compared with the first one seen; a difference marks a reload pending and calls `reload()` at
  once when no Apply is pending; no `build` object, a failed request or a stopped shell → nothing; `stopWatch =
  startPolling(watchOnce, DEVICE_WATCH_INTERVAL_MS, {visibility, onError: () => { /* silent: the section's own GET owns
  the banner */ }})`; then `selectSection(history.current() ?? defs.landingSection)` — a deep link (`#<key>`) opens its section, an
  unknown or absent one the landing section, with no entry pushed. The returned `stop()` sets `stopped`, stops the
  section and the watch (each releases its visibility subscription) and calls `nav.dispose()` and the `onPop` removal.
- **Resolved**: A.U23.07's `fetchImpl?` parameter has no production caller (every request goes through `pollManager`)
  — a test-only seam, so it goes (OR36.a (1); agent decision D7). The visibility source is built by one shell helper over
  the `Document` the entry passes, instead of a copy in each entry (G7/R35 "logic both entries need lives once"; the
  layering guard's rule — no `document.` query outside the entries — holds; agent decision D7). A.U35.46 (2)'s one-line
  comment lands here since A.U23.07 moves `selectSection()`.
- **Unit**: U23 (A.U35.46 (2)'s comment folded in; the section history with M.WEB.030/.031/.064, A-C review fold).
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
  with its comment); OR140.a (15) (the entry passes `historyOf(window)` (A-C review fold)).
- **Site**: `js/main.js:1-60`.
- **Change**: header `:1-5` unchanged. Imports: `loadDefinitions` (`./definitions.js`), `showBanner` (`./render.js`),
  `startShell`, `visibilityOf` (`./shell.js`). `export async function startApp(elements)` — the `@param` key list
  unchanged (A.U23.38's bootstrap check reads it), `@returns {Promise<() => void>}`: definitions load failure →
  `showBanner(errorBannerEl, \`Could not load definitions: ${String(error)}\`)` and `return () => { /* nothing was
  started */ };`; then `deviceNameEl.textContent = defs.device.displayName;` and `return startShell({defs, elements:
  {appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl}, keyTarget: document, visibility: visibilityOf(document), history: historyOf(window),
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
  A.U35.46 (2) (duplicate `selectSection()` goes), A.U28.24 (read: the preview serves `build/generated_src/definitions/`),
  A.U23.04 (the entry passes the document-derived visibility through the shared shell, as M.WEB.030 does for `main.js`;
  AC3_S section 4); OR140.a (15) (the same `historyOf(window)` (A-C review fold)).
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
  installMockFetch(defs, composeMockData(defs, samples))`; (7) `stopShell = startShell({...same as main.js, history: historyOf(window)})` (the hash carries the section; the
  `?device=` query stays the device's); returns
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
  `ResetErrors` leaves `UARTLINK_*` alone — holds), A.U10.40 (member and key names from the definitions); OR140.a (5) (the busy refusal's retry hint (A-C review fold)).
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
  `Date.now() < busyUntil` (the response then carries the server's `descr` "LED busy - retry later", M.SRC_NET.122), else `VALID` with `busyUntil = Date.now() + T * 1000` (`T` the duration member, its name
  pinned to `_LIGHT_CMD_FIELDS` by A.U23.27's mirror check); a `toggle` is validated as a boolean; a field with
  `alwaysExecuted` → validated, answered `VALID` (never `UNCHANGED`), and stored only when the device's composed data
  already carries the key (so `AmbPres` and `ForceCalRef` read back what was applied and `ContMeas`, which GET cannot
  report, never appears); every other field: invalid → `INVALID`; with `field.resolution = r` the stored and new values
  are compared as `Math.round(v / r)` and the stored value is `Number((Math.round(value / r) * r).toPrecision(15))` (the
  `toPrecision` drops binary noise such as `1235 * 0.01 = 12.350000000000001`); equal → `UNCHANGED`, else
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
  `accessibility.test.js`, `site-functions.test.js` (M.WEB.056/.057/.060/.080/.066); SPEC H.2 `mockdata/` line, K.8
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
  (read: accept-shaped sample values), A.U17.19 (read: `UARTLINK` counts); gap pass G2 (pointer sweep): A.U6.26 (the
  `networkingConfig` `DNSFallback` sample, its mock half), A.U18.33 (read: the networking status keys `IPv4`,
  `Subnet`, `Gateway`, `DNS` are kept; `IP` goes by the routine settlement "status-ip-and-ipv4"), OR138.a (1)
  (`ConfigFaults`) (A-C review fold), A.U2.20 (the `UART` errcount sample takes UART catalog codes — HEAD's fixtures
  have no UART row).
- **Site**: `mockdata/dev.json`, `mockdata/wozi.json` (deleted); new `mockdata/samples.json`.
- **Change**: `mockdata/samples.json` — `{measurements, sensorsConfig, networkingConfig, systemConfig,
  notificationConfig, status: {networking, system, sensors, notification}, errcount}` per M.WEB.004's `MockSamples`:
  measurements and sensor configs keyed by driver logger name (`SCD30`, `SGP40`, `BMP3XX`, `ISL29125`), seeded from today's
  two files (the `SHTC3`/`MPRLS` rows dropped), every key in the A.U10.40 scheme, plus `SCD30.FRCState` 4,
  `SCD30.FRCWait` null, `SGP40.VOCState` 2, `ISL29125.CalLight` 1, sensor settings `FRCNoise` 20.0, `FRCRate` 10.0,
  `FRCWindow` 60, `ForceCalRef` 400; networking `SSID`, `PW`, `HotspotPW` "12345678", `Country` "DE", `Hostname`
  "SensorNode", `LEDWifiOn`, `NTPHost` "pool.ntp.org", `NTPOffset`, `NTPInterval`, `DNSFallback` "8.8.8.8,1.1.1.1";
  system `DebugLevel`, `GMTOffset`, `DSTOffset`, `build` `{FirmwareVersion, WebsiteVersion, BuildDate}`; status networking
  adds `HTTPDropped` 0 and `WifiTS` (a number) and carries no `IP` key, system adds `ConfigFaults` `[]`, `ResetReason` 1, `MemFree`, `LastTaskEnd` null, `UnixTime`
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
  U18 (`DNSFallback`, `HotspotPW`; the `IP` key out), U19 (`HTTPDropped`, `WifiTS`), U20 (`ConfigFaults` with its
  definitions row, M.GEN.014), U25 (`ForceCalRef` 400 confirmed), U32.
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
  outcome, GET masks and time values, and the composed data." Fixture definitions `:5-135` (data `:137-153`) carry the options, bounds,
  `dispatch` and `alwaysExecuted` flags the tests rely on, keys per A.U10.40 (`LightCmdLED` `R/G/B/T`); `Hostname`
  `"fixture-host"`. `:178-195` hold; new resolution cases (stored 12.35, PUT 12.345 → "Unchanged", 12.36 → "Valid");
  `:196-212` `ResetErrors` assert the result, plus `ResetErrors: false` → "Invalid"; `:224-244` (`SystemCmd`): both new
  words → "Valid", never persisted, a repeat "Valid", and the near-miss list of A.S0930.20 (4) each "Invalid"; a fixture
  with a fourth option is accepted (derived); `SystemCmd` sent to `/networking` → "Invalid"; `:272-314` (`LightCmdLED`):
  malformed/out-of-range/missing/extra member → "Invalid", back-to-back accepted commands → "Valid" then "Failed", and
  "Valid" again after `vi.setSystemTime` passes `T`; every other accepted `LightCmdLED` case in `:272-314` (`:293`,
  `:302`, `:304`, `:312`) advances the mock clock past the previous accepted command's `T` (`vi.setSystemTime`) before
  it is sent, so each still reads "Valid" (A.U9.03's Blast); the never-"Unchanged" repeat at `:312` keeps its point
  that an identical later command is dispatched again; SCD30 cases: `AmbPres` never "Unchanged", `ForceCalRef` reads back
  900 after a 900 PUT and 400 on a fresh install, `ContMeas` never appears on GET; `:316-340` per A.U25.12; `:372-383`
  masks gain `HotspotPW`; `:385-445`: `TS` equals the mock clock, `SysUptime` seeded at `COUNTER_CAP - 1` gives
  `COUNTER_CAP` on two GETs, `LocalTime` unchanged over ten GETs, nested measurement jitter holds; two GETs with
  `delayMs` unset resolve with no timer advanced; `:469-480` → an unknown sensor answers "Invalid" and the real ones
  still apply; `:481-486` → code 405; `:498-508` → the catalog's text; `:510-519` hold, plus bodies `"[1,2]"` and
  `"nope"` → HTTP 200 code 1; `group-failure` → every attempted key "Failed"; `:539-549` (`partial-result`) goes;
  float field `50` → Valid and stored 50, int field `5.5` → Invalid, `5` → Valid, `true` → Invalid; one
  corpus-driven `it.each` per shape over `tests/_radio_shape_cases.json` (accept → "Valid", reject → "Invalid"); a
  32-character SSID of 2-byte characters → "Invalid", 16 → "Valid". The trailing restore `:403` goes (`restoreMocks`, A.U24.14); `:419-444`'s `finally`
  restore may stay. Fixture and case
  keys follow A.U10.40's map, synthetic ones included (`SGPResetVOC`/`ISLCalibrate` → `ResetVOC`/`Calibrate`, the
  `:354-369`, `:447-465` names following); the
  `:249` comment's `coerce_numeric()` → "the server's per-kind validation" (the function is private after M_SRC_CORE
  GAP-G13 / M.SRC_CORE.047); `:273-275` → "// Mirrors _dispatch_notification_led(): a malformed payload, a missing or
  extra member or a value outside // its schema answers "Invalid"; a well-formed command while a signal still runs
  answers "Failed"."; `:287-288` → "// A fractional R/G/B is rejected, never truncated."; `:296` → "// Out-of-range
  members are rejected (legacy led_cmd()'s bounds)." Titles and comments follow the end state (AC3_O O-03): `:316` →
  "dispatches PUT /sensors' ForceCalRef: range-validated, never Unchanged, and GET reads back the last reference
  applied (400 on a fresh mock)", `:325-327` → "// The chip reports the most recently used reference within one
  power-up and 400 after power-up (Interface Description 1.4.6)."; `:336` → "dispatches PUT /sensors' ContMeas as a
  command: bool-only, never persisted or reported by GET"; `:372` → "masks PW (and HotspotPW) on every GET /networking,
  whatever was applied"; every other title naming a `src/` function names one that exists at the end state (grep at
  landing). Fold (A-C review): the busy `LightCmdLED` answer also carries the `descr` "LED busy -
  retry later" (M.WEB.041).
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
  DEFINITIONS])("accepts the generated %s definitions", …)` replaces `:205-213` (comment and `it.each`); the `:2-3`
  comment → "// Every device's generated definitions come from tests_js/_generated_definitions.js (a real browser run:
  no node:fs)."; `MINIMAL_VALID`'s id and the stub paths
  use `"fixture-device"`; `SUPPORTED_SCHEMA_MAJOR` and the `:295` timeout come from `_source_constants.js` (`readConst
  ("../js/definitions.js?raw", "SUPPORTED_SCHEMA_MAJOR")`, likewise `DEFAULT_TIMEOUT_MS` from `poll-manager.js`); `:81-95`
  gain the upper bound (2**31 rejected, 2**31 − 1 accepted, for both intervals); `:242-246` (the `defaultValue` fallback
  case) goes; `:248-252` (null pass-through) stays with `defaultValue: 5000` removed from its field and its comment →
  "// CCT is legitimately null in a dark room; the renderer shows an em dash for it."; new: while a `pollManager.request()` is
  pending, `loadDefinitions()` issues no fetch until it settles (a stub counting concurrent fetches never sees 2). The
  hang test's stub and assertion hold. Trailing `vi.useRealTimers()` go. Fold (A-C review): `confirm` accepted on an enum or toggle and refused elsewhere or
  non-boolean; `defaultDecimals` accepted as an integer `0..100` and refused otherwise.
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
  delay before rechecking" (its comment line above goes). Fixtures: every key A.U10.40's map renames, synthetic fixture keys included (its grep rule: no old key outside
  `legacy/`/`audit/`) — `MeasInt` → `MeasInterval` throughout, `lightCmdLED` → `LightCmdLED` with `R/G/B/T`; `:84-86`
  comment → "// A plain toggle: no dispatch or alwaysExecuted flag, so the mock stores and echoes it (SPECIFICATION.md
  Part H.4)."; the status fixture's sections carry what each test needs. Changed expectations: `:323` → "Command executed
  — MeasInterval: Valid"; `:382-415` comment "rebuild" → "update"; the latency comment at `:403-405` → "// Fake timers from
  here on: the live poll tick is driven deterministically."; `:417-466` → the mock answers `{"ResetErrors": "Valid"}` and it is read; a local stub answering
  `{"ResetErrors": "Failed"}` shows Failed; the second click of `:458-466` → the toggle is Off after the first Apply,
  so "Nothing to submit"; `:468-535` (describe "… defaultValue") → an always-executed toggle with no GET value renders
  "—", is not submitted until set, is submitted `false` once set Off, returns to "—" after Apply; `:540-600` hold plus a
  dispatch toggle left Off gives "Nothing to submit"; `:583-620` gain: choosing "Erase FRAM" and Apply sends one PUT
  `/system` with body exactly `{"SystemCmd":"erasefram"}` after one `window.confirm` (spy answering `true`) asking
  "Erase FRAM?", and sends nothing when the spy answers `false` (A-C review fold, OR140.a (3), inverting A.S0930.20 (5)'s
  zero-call pin), the same for "Reset to defaults", the select returns to "Select…"; `:647-666` hold with `data-shown`; `:668-676` gains "and a later
  tick recovers it"; `:678-722` hold plus `"  "`, `"0x10"`, `"1e3"`, `"1,5"` each PUT the raw string and show Invalid,
  `" 12 "` PUTs 12; `:698-744` both cases expect "Invalid" and are renamed "… reports Invalid for …"; `:746-764` gains
  sub-inputs cleared after Valid; `:783-812` → "reads maintenance data by path" (`path: ["SGP40", "BackupTS"]`) plus two
  instances `SGP40` and `SGP40_x` each showing their own value; `:845-880` hold through the generic `/status` sub-fetch
  (`:851` code 4 → 404); `:882-930` in-place refresh holds; `:958` pointer → "(SPECIFICATION.md C.5.3)"; `:1015-1037`
  builds its response with a local fetch stub and is renamed "… (defensive fallback)", its `:1016-1017` comment → "// Defensive
  only: the server answers every submitted key (SPECIFICATION.md A.8)."; `:727`'s comment ("Invalid" only for a
  non-dict) is rewritten to the A.U19.02 rule with the `:698-744` change. Banner assertions read
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
  Comments and titles follow the end state (AC3_O O-08): `:702-704` → "// A non-numeric member is refused by the
  dispatcher's per-member validation (SPECIFICATION.md A.8)."; `:417` → "shows Valid after a successful Reset All Errors
  submission, read from /status's per-field result" and `:418-420` deleted; `:458-460` → "// The toggle is Off after
  the first Apply, so a second click has nothing to submit."; `:409-410` → "// The poll update keeps the chosen
  filter."; `:584-586` → "// SystemCmd is never returned by GET /system (A.8), so the select starts on its placeholder
  and an untouched Apply sends nothing."; `:679-680` → "// JSON.stringify(NaN) is "null"; the raw text is sent instead
  so the server can refuse it."; `:864` names the section's status sub-request as M.WEB.020 names it (no `fetchOnce()`
  if that function is gone). Fold (A-C review): "Reset All Errors" asks "Reset All Errors?" before its PUT and
  sends nothing on cancel; a measurement float without `decimals` renders with the definitions' `defaultDecimals`.
- **Resolved**: A.U23.14 says `:458-466` (second ResetErrors) holds and A.U23.15 (later in the same unit, and the
  behaviour it adds) turns it into "Nothing to submit" — A.U23.15's expectation stands. A.U23.05's "console.error once"
  case lands here (M.WEB.051's note). A.U36.544 (4) ":86 H.7 → H.4" applies to the comment A.U6.17 makes false (the mock
  no longer special-cases a name): the comment is rewritten with the H.4 pointer.
- **Found while merging (no action names them; consequences of A.U23.26 and M.WEB.020)**: the banner test at
  `:647-666` expects `/simulated failure/`, but an injected 500 now answers through `makeResponse(500)` with the
  catalog text, so it expects "Internal server error". The one-shot settings banner test at `:668-676` asserts the
  banner after the failure, but the one-shot section now retries on its failing-episode interval and hides the banner
  on recovery; it runs under fake timers (`vi.useFakeTimers()`, advanced only past the first attempt) so the assertion
  sees the failure state, not a later retry. The same holds for `:995` (the PUT 500 case): it expects "Internal server
  error" (AC3_O O-07).
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
  unchanged in substance; `:73-74` comment → "// Only readonly fields: a command-only trigger is never echoed in a
  GET."; the two per-variant `it`s become one `it.each(DEVICE_IDS)("every readonly field %s's definitions name
  resolves in its composed mock data", …)`; the two self-checks `:107-125` stay; `:96-98` → "// A blank row is not a
  defect the renderer reports, so an unresolvable readonly field fails here."
- **Resolved**: —
- **Unit**: U23. Stage U6 (per-device rewrite).
- **Depends**: M.WEB.043, M.WEB.050.
- **Blast carried by**: —
- **Kind**: test

## tests_js/templates.test.js

### M.WEB.058 Template tests go through the exported card and cover every new cue
- **From**: A.U23.37 (`buildField` tests through `buildFieldGroupCard()`), A.U23.43 (1) (label expectations), A.U23.11
  (`:382-389`, `:343-347`), A.U23.12 (`:375`, `:388` → `data-worst`), A.U23.20 (pill click, code field, `CalLight`
  tone, hostile description), A.U23.21 (age boundaries, specials), A.U23.24 (struct missing a member), A.U23.49
  (resolution hint), A.U23.40 (read: `:502-570` XSS tests hold), A.U6.28/A.U6.29 (hint text), A.U6.13 (`:41`, `:142`,
  `:478`, `:489`), A.U0.28 and A.U24.56 (`:399-401` tag), A.U10.40 (time-struct and LED keys), A.U32.06
  (`lasttaskend` case), A.U27.28 (header), A.U20.27 (read: self-contained BMP fixtures hold).
- **Site**: `tests_js/templates.test.js:1-570`.
- **Change**: header (≤ 3 lines) "Tests js/templates.js and js/field-format.js: field markup and hints, cards and their
  in-place update, the errcount card, the shell and nav builders, and text-only rendering." Imports drop `buildField`, add
  `updateFieldGroupValues`, `updateErrcountGroup`, `resetControl`. Formatter (`:19-87`): `:40-48` uses `Year…Second` keys,
  its comment → "// Real shape: the generated module's _gmtimestruct_to_dict() (buildgen/codegen.py)."; new cases — ages
  at 0, 119, 120, 7199, 7200, 172799, 172800 s give "0 s ago", "119 s ago", "2 min ago", "119 min ago", "2 h ago", "47 h
  ago", "2 d ago" (hand-written); `deviceNowS` null → "age unknown"; age −6 → "clock mismatch"; `BackupTS` null → "None
  since boot", 0 → "No timestamp"; a struct missing `Hour` → "invalid time value"; `lasttaskend` `{Task: "SCD30.start_asy_read",
  Uptime: 3600}` → "SCD30.start_asy_read at uptime 3600 s", `null` → "—". Field markup (`:89-279`): each case builds a
  one-field group card (`submit` = the old `editable`) and reads `[data-field-wrapper-key]`; `htmlFor` expectations follow
  the index ids and `span.field-label` rule; `:141-143` hold with `"fixture-host"`, plus a `byteLength` field shows ", at
  most 32 bytes (UTF-8)" and a `hostLabel` field "letters, digits and '-' only"; a number field with `resolution` 0.01
  and unit °C shows "Resolution: 0.01 °C", one without shows none; an always-executed toggle with no value renders "—"
  and `aria-pressed="mixed"`; a masked input has `autocomplete="new-password"`. Errcount: `:343-347` count the no-data rows;
  `:370-380` and `:382-389` move to the wrapper's `data-worst` ("renders an absent module as no data, never a zero");
  a module with counter 3 and only `W` history colours as warning and counts under warnings; `:398-428` hold (the type
  only colours), `:399-401` comment tag "(owner, 2026-08-21, `9fd2a28`)"; a pill click shows the catalog text, Enter
  works, a code with no entry shows "No description for code <n>"; a `CalLight` 2 renders "<text> (2)" with
  `data-code-tone="warn"`; `updateErrcountGroup()` keeps the "Show all" button node and focus; `updateFieldGroupValues()`
  keeps the same `.field-value` node; `resetControl()` clears an input, a composite and selects the placeholder.
  `buildSectionShell` (`:438-462`) expects `data-shown="false"`. `:478`, `:489` → `"fixture-device"`/"Fixture Device".
  XSS (`:502-570`) hold, `:512-523` building its hostile field through a one-field `buildFieldGroupCard()` like the
  field-markup cases, plus a hostile code description rendered as text. `:399` → `src/asy_print_log.py's get_log()`
  (A.U10.37); `:328`'s title → "tags the card with data-group-key itself, like buildFieldGroupCard() (SPECIFICATION.md
  Part H.3: js/templates.js owns the hook)" (AC3_O O-10). Fold (A-C review): `ResetReason` renders as a code button whose click shows "<n>:
  <description>" (OR140.a (8)); a non-integer number renders through `defaultDecimals`, an integer unchanged, a field's
  own `decimals` wins; an array renders joined, an empty one "none" (`ConfigFaults`).
- **Resolved**: A.U0.28 (U0) writes `:399-400` "(owner, 2026-08-21, `9fd2a28`)"; A.U24.56 (U24) lists the same A28 site
  as "residue other units leave" with the text "(owner, 2026-08-21)" — A.U0.28 already carries it, so A.U24.56's A28
  bullet is void (its own scope is what other units leave) and A.U0.28's text stands.
- **Unit**: U32 (`lasttaskend`). Stages: U0 (tag), U6 (A.U6.13 ids, A.U6.28/.29 hints), U10 (keys), U23 (the rest), U27
  (header).
- **Depends**: M.WEB.012-.017.
- **Blast carried by**: —
- **Kind**: test

## tests_js/main.test.js, tests_js/app.test.js, tests_js/nav.test.js

### M.WEB.059 Entry and nav tests: stop handles, neutral ids, data attributes, inert drawer
- **From**: A.U23.07 (stop handle in `afterEach`, `initNav` returns `{setCurrent, dispose}`, `keyTarget`), A.U23.06 (stubs
  answer `/status` and `/system`), A.U23.42 (`data-shown`, `data-nav-open`), A.U23.43 (2) (inert and focus asserts),
  A.U6.07 (`app.test.js` manifest stubs, neutral ids), A.U6.13 (`main.test.js:7, :90, :138, :166`, `nav.test.js:7`),
  A.U35.46 (read: hold), A.U27.28 (headers).
- **Site**: `tests_js/main.test.js:1-168`, `tests_js/app.test.js:1-152`, `tests_js/nav.test.js:1-109`.
- **Change**: each file gains a ≤ 3-line header naming what it tests. `main.test.js`: fixture id `"fixture-device"`,
  displayName "Fixture Device" (the three `toBe("Wozi Test")` follow); every `startApp()` result is kept and called in
  `afterEach`, so a live landing section can be tested; the fetch stub answers `/status` (`{system: {UnixTime: …}}`) and
  `/system` (`{build: {…}}`); banner asserts (`:38, :91, :111, :121, :139, :154`) read `dataset.shown`. `app.test.js`:
  the stub serves `../build/generated_src/definitions/index.json` `{"devices": ["fixture-a", "fixture-b"]}`, the two
  definitions files and `../mockdata/samples.json`; cases: the first manifest id is the default, an unknown `?device=`
  falls back to it, a known one is used, a manifest 404 shows "Could not load the device list", a definitions failure and
  a torn `samples.json` show their banners and render no section; the landing section is marked `aria-current` in the
  drawer; a `samples.json` answered with HTTP 500 shows its banner and renders no section (AC3_O O-12); stop handles called; the `:11-12` "no stop handle"
  comment goes (sections may be live now). `nav.test.js`: `initNav` gets `keyTarget` (a counting `EventTarget`) and
  returns `{setCurrent, dispose}`; `:38-92` assert `appShellEl.dataset.navOpen`; new: closed drawer `inert`, open not,
  opening focuses the first link and sets `aria-label` "Close navigation", closing with focus inside returns it to the
  hamburger, `dispose()` leaves no listener on `keyTarget`; fixture id `"fixture-device"`. `main.test.js:11-12` ("no stop handle") goes as in `app.test.js`; `:47-49` JSDoc names
  `scripts/_stage_website.py` in place of "build_website.sh's "Inlining" note"; `nav.test.js`'s `afterEach` calls the returned
  `dispose()`. `main.test.js:127-128` comment → "// The point of inlining
  (SPECIFICATION.md H.2: the stager inlines definitions.json): a device build never fetches it." (the build script
  that inlines moves to `scripts/_stage_website.py`, A.U23.38; "H.7's follow-up round" is a process label, G9/R12);
  `main.test.js:144` "scripts/build_website.sh" → "scripts/_stage_website.py" (AC3_O O-11). Fold (A-C review): every `startApp()` stub passes no real history — the entries build
  `historyOf(window)` over the test's `window` (jsdom), the hash cleared in `afterEach`.
- **Resolved**: —
- **Unit**: U23. Stages: U6 (A.U6.07/.13), U27 (headers).
- **Depends**: M.WEB.025, M.WEB.026, M.WEB.030, M.WEB.031.
- **Blast carried by**: —
- **Kind**: test

## tests_js/mock-server-put-matrix.test.js, tests_js/_put_field_cases.js

### M.WEB.060 The mock PUT matrix runs every device, deduplicated, with derived classes
- **From**: A.U6.09 (all devices, `dedupePutFieldCases()`, `DEV_UNIQUE_GROUPS` goes, shard tests), A.U6.17 (6)
  (`DISPATCH_ONLY_KEYS` goes; never-"Unchanged" category), A.U0.20 (header owner tag), A.U0.40 (L07 — carried by A.U6.09's
  deletion), A.U23.33 (`:11-13` comment), A.U18.38 (read: `HotspotPW` picked up from definitions), A.U6.24 (read: readonly
  skipped), A.U27.28 (header present).
- **Site**: `tests_js/mock-server-put-matrix.test.js:1-21, :40-43, :118-121, :183-185, :290-310`;
  `tests_js/_put_field_cases.js:1-83`.
- **Change**: matrix header `:1-5` → "PUT-behaviour matrix over every real writable field of every device's generated
  definitions (deduplicated by derivation), against js/mock-server.js's fetch interception - six categories per field
  (owner, 2026-08-24) (valid, special, omitted, resubmit-unchanged, out-of-range, wrong-type), matching
  SPECIFICATION.md Part A.8." (≤ 3 lines when wrapped); the four JSON imports and `DEV_UNIQUE_GROUPS` with its comment go;
  `CASES = dedupePutFieldCases(DEVICE_IDS.flatMap((d) => collectMockPutFieldCases(d, GENERATED_DEFINITIONS.get(d),
  composeMockData(...))))`; the resubmit-unchanged expectations `:118-121`, `:183-185` apply to non-`neverUnchanged()`
  fields only; a field with `resolution` expects the stored value rounded to it
  (`Math.round(v / r) / Math.round(1 / r)`, the test's own arithmetic); `GET_READBACK_QUIRK_FIELDS` (`:23-26`, a hand list) goes: its SCD30/SGP40/ISL29125
  members are `neverUnchanged()` fields the generic cases now skip, and `PW` is derived as "a field with `mask: true`"
  (the GET masks it), comment one line naming that rule; the `:191`, `:203` test names cite "the server's per-kind
  validation (SPECIFICATION.md Part A.8)" instead of `config_manager.py's coerce_numeric()` (renamed module, private
  function, M.SRC_CORE.047); a new category asserts two identical valid sends of every `neverUnchanged()` field both answer "Valid";
  shard tests take `DEVICE_IDS[0]`; a dedupe case keeps a field differing in any attribute and drops an identical one
  from a later device. `_put_field_cases.js`: `DISPATCH_ONLY_KEYS` goes; `collectPutFieldCases()` skips readonly,
  composite and every `neverUnchanged(field)` field (`:63`); `:11-13` comment → "// Action fields (dispatch) and
  always-executed fields have their own categories: the matrices' never-"Unchanged" category and / // the live tier's
  action-field block." (2 lines); new `export function dedupePutFieldCases(cases)` — first case per `sectionKey + "|" +
  driverBase(groupKey) + "|" + JSON.stringify(field)`, `driverBase` = the key up to its first `_`. New `export function
  validStringValue(field, length)` used by both matrices' string "valid" probes: no `shape` → `"x".repeat(length)`;
  `hostLabel` → the same; `hostName` → labels of at most 63 `x` joined by `.` to `length`; `countryCode` → `"XX"`;
  `ipv4List` → the corpus accept values (`"8.8.8.8"`, `"8.8.8.8,1.1.1.1"`, `"1.1.1.1,8.8.4.4,9.9.9.9"`) instead of a
  length sweep. Without it the generic `"x".repeat(n)` probes fail the shape checks M.WEB.041 adds (`"xx"` is no
  country code, `"x"` no IPv4 list) — a blast of A.U6.29/A.U6.30/A.U10.41/A.U18.10 no constituent carries (gap closed
  here).
- **Resolved**: A.U0.20 (U0) tags the header's `:2` and A.U6.09 (U6) rewrites what `:2` describes — one header carrying
  both (A.U0.20's own Blast: "A-C merges both edits into one header"). A.U0.40's L07 is void: A.U6.09 deletes
  `DEV_UNIQUE_GROUPS` and its comment (A.U0.40 names this itself). A.U23.33's comment text ("action fields are covered by
  their own live block") is folded into A.U6.17's rewrite of the same comment.
- **Unit**: U23 (A.U23.33's comment). Stages: U0 (tag), U6 (the rest).
- **Depends**: M.WEB.043, M.WEB.050, M.WEB.005.
- **Blast carried by**: `collectPutFieldCases()` also feeds the live matrix (M.WEB.063); SPEC H.7/H.8 matrix text
  (A.U36.517, SPEC).
- **Kind**: test

## tests_js/_live_twin_command.js

### M.WEB.061 The live-twin commands: any device, own config dir, port lock, scanned output, fail on a missing build
- **From**: A.U6.10 (1)-(3) (`spawnTwin(device)`, `configuredMaxConnections(device, devicesDir)` with no default, both
  commands take the device), A.U7.21 (stdout drained, bounded buffer, memory markers), A.U8.21 (budget tags), A.U23.32 (4)
  (DebugLevel smoke: exact `valid` then `unchanged`), A.U23.34 (full ceiling, recovery by reload), A.U23.35 (restart
  recovery), A.U24.52 (missing interpreter throws), A.U24.53 / A.U25.32 (per-run `--config-dir`), A.U24.69 (port-53
  lock), A.U25.09 (`--mem-backup-state-path ""`), A.U27.12 (shared Unix-port probe), A.U27.15 (`MICROPYPATH` from
  `_micropypath.js`), A.SDEP.16 (W15) and A.SDEP.19 (W36) (conditional), A.U36.513/A.U6.10 (`:14` comment), A.U23.15
  (read: an Apply settles only when the button is enabled again), A.U25.44 (read: the guard reads this file's
  `MICROPYPATH` import).
- **Site**: `tests_js/_live_twin_command.js:1-263`.
- **Change**: header (3 lines) unchanged except "drives a real Playwright page against it directly" holds; imports gain
  `mkdtempSync`, `os.tmpdir`, `MEMORY_ERROR_MARKERS`/`memoryMarkerLines` (`./_memory_markers.js`), `MICROPYPATH`
  (`./_micropypath.js`, the `twin` layout of `scripts/micropypath.toml`), `acquirePortLock` (`./_port_lock.js`); the
  `TOOLCHAIN_DIR`/`MICROPYTHON_BIN` constants and every `existsSync(MICROPYTHON_BIN)` check go: the binary path comes
  from `execFileSync("bash", ["scripts/_unix_port.sh", "check", "standard"])` once at first use, and a failing check
  throws `Error("MicroPython Unix port not built … - run 'uv run toolchain/setup_toolchain.py setup' first")` (A.U24.52's
  text, the probe's own message appended); the `:14-16` comment goes with the local `MICROPYPATH` literal. Budgets:
  `// @tunable l0.live_twin_ready_timeout_ms = 20000` above `READY_TIMEOUT_MS`, `// @tunable
  l0.live_twin_shutdown_timeout_ms = 15000` above `SHUTDOWN_TIMEOUT_MS`, named constants with tags for the `:173`
  10000 (`l0.live_twin_section_wait_ms`), the `:252` 20000 (`l0.live_twin_tab_wait_ms`) and the 250/200 ms poll steps
  (`l0.live_twin_poll_ms`). `spawnTwin(device, configDir)`: `--module sensortask_${device}`, `--wiring-plan
  build/generated_src/sensortask_${device}_wiring_plan.json`, `--device ${device}`, `--host`, `--port`,
  `--fram-state-path ""`, `--scd30-state-path ""`, `--mem-backup-state-path ""`, `--config-dir ${configDir}`; env
  `{...process.env, MICROPYPATH: <the twin layout with its `frozen_modules` entry replaced by
  `build/generated_html/${device}`>, TZ: "UTC"}` (the device's own built site, A.U6.10 (1); one comment line says why;
  gap pass G2 — M_SCR gap 1(a); `TZ` goes only if A.SDEP.16 (W15) finds `mktime()` fixed); `stdio:
  ["ignore", "pipe", "pipe"]`, both streams drained into one buffer keeping the last 256 KiB, line-complete (the `:75-77`
  comment → "// Both streams are drained: an undrained pipe blocks the child; the drained text is scanned for the memory
  markers."). Each command: takes the port-53 lock before its first boot and releases it on every exit path (re-entrant within one
  process and honouring an inherited lock, M.WEB.078); makes `configDir
  = mkdtempSync(path.join(os.tmpdir(), "sensors-live-"))` and removes only it when the twin stops (the `:151-154`
  comment and the three `rmSync(<repo>/digital_twin/config)` go); after the twin stops throws, quoting the lines, when
  `memoryMarkerLines(output)` is non-empty. `runLiveBackendSmoke({context}, device)` → `{titleHasSensorStation,
  deviceName, firstStatus, resubmitStatus}`: reads `GET /system`'s `DebugLevel`, fills a different in-range value, Apply →
  waits until the Apply button is enabled again, reads `data-apply-status`; fills the same value again → the same wait,
  second status. `runLiveBackendConcurrentTabs({context}, device)` → `{tabs, loadedFirstPass, loadedAfterRetry, failures}`:
  `tabs = configuredMaxConnections(device)`; all navigate at once; each load either completes or fails at the connection
  level, none pending after `outer_cap_s` + 5 s; each tab that did not load is reloaded one at a time and must load; the
  `:233-234` comment goes. New `runLiveBackendRestartRecovery({context}, device)` → `{bannerShown, recovered, reloaded}`:
  boots, opens the page on Measurements, waits for one successful poll, sets a `window` marker, stops the twin, waits for
  the section banner, restarts the twin on the same port and config dir, and within `READY_TIMEOUT_MS` + 60 s (the back-off
  cap) sees the banner hide and a value refresh; `reloaded` is true when `page.url()` or the marker changed; both twin
  runs' output scanned. `configuredMaxConnections(device, devicesDir = path.join(REPO_ROOT, "devices"))` — `device` is
  required. If A.SDEP.19 (W36) finds Vitest's `page` can navigate to an external origin, the Commands-API detour is a
  delta for U23/U28 recorded there; otherwise unchanged.
- **Resolved**: A.U24.53 and A.U25.32 plan the same per-run config dir (A.U25.32's Blast: "co-lands with A.U24.53 — A-C
  merges") — one change. Gap pass G2 (M_SCR gap 1(a)): the merged text had dropped A.U6.10 (1)'s site swap — restored;
  `_micropypath.js` stays the plain reader of the `twin` value and the swap lives in the launch frame
  (`tests_js/_twin_process.js`, M.WEB.082), where M.TSC.202's text check looks for it. A.U24.52's thrown message and A.U27.12's probe both replace the `existsSync` check: the probe's
  `check` form decides, the message is A.U24.52's (the probe names the found flavour after it). A.U6.10, A.U7.21, A.U8.21,
  A.U23.32-.35, A.U24.52/.53/.69, A.U25.09, A.U27.12/.15 all edit `spawnTwin()` and the two commands — merged into the one
  text above. Reading `data-apply-status` only after the button is re-enabled is what A.U23.15 (button disabled until the
  post-write GET settles) and A.U23.14 (stale colours cleared) require of any reader (agent decision D9).
- **Unit**: U27 (A.U27.12/.15, the latest). Stages: U6 (A.U6.10), U7 (A.U7.21), U8 (tags), U23 (A.U23.32/.34/.35), U24
  (A.U24.52/.53/.69), U25 (A.U25.09), U27; U0 conditional (A.SDEP.16/.19 outcomes).
- **Depends**: M.WEB.075 (`_memory_markers.js`), M.WEB.078 (`_port_lock.js`), M.WEB.079 (`_micropypath.js`); A.U25.32
  `--config-dir`, A.U25.09 flag (TWIN); `scripts/_unix_port.sh` (A.U27.12, SCR); `scripts/micropypath.toml` (A.U27.15, SCR).
- **Blast carried by**: `tests_js/live-backend.test.js` (M.WEB.063); `tests_js/vitest-commands.d.ts` (M.WEB.076);
  `vitest.config.js` registrations (M.WEB.074); `tests_scripts/test_live_twin_ceiling_parser.py:23` (device passed —
  holds, TSC); `tests_scripts/test_live_command_device_args.py` (A.U6.10, TSC); the no-`rmSync`-outside-tmp text check
  (A.U24.53, TSC); `tests_scripts/test_twin_never_needs_tests_on_its_path.py` (A.U25.44/A.U27.15, TSC); A.U7.23's
  gate-agreement import check (TSC); Part N `l0.live_twin_*` rows (A.U8.21, SPEC); SPEC H.7 live tier (A.U36.517 (6),
  SPEC); `digital_twin/README.md` runner flags (A.U25.32, TWIN).
- **Kind**: test

## tests_js/_live_matrix_command.js

### M.WEB.062 The live-matrix commands: per device, checked baselines, independent expectations, action fields
- **From**: A.U6.10 (4) (`startLiveMatrix(device)` boots only, `getLiveMatrixConfig()`), A.U7.21, A.U8.21 (tags),
  A.U23.16 (`applyField()` clicks until the wanted value; `unset` read back), A.U23.32 (1)(2) (`getRealCurrentValues()`
  checks; `_expected_display.js`), A.U23.33 (`archiveErrcount`; composite kind), A.U23.14 (`:331` comment), A.U24.52,
  A.U24.53/A.U25.32, A.U24.69, A.U25.09, A.U27.12, A.U27.15, A.SDEP.16/.19 (conditional), A.U36.544 (4) (`:151`
  pointer), A.U23.15 (read: wait for the re-enabled button).
- **Site**: `tests_js/_live_matrix_command.js:1-388`.
- **Change**: header unchanged; the frame as M.WEB.061 (probe, `MICROPYPATH`, port-53 lock, per-run config dir, drained
  scanned output, `--mem-backup-state-path ""`, the missing-interpreter throw, tags `l0.live_twin_ready_timeout_ms`,
  `l0.live_twin_shutdown_timeout_ms`, `// @tunable l0.put_matrix_apply_status_timeout_ms = 5000`, `// @tunable
  l0.put_matrix_caption_poll_timeout_ms = 3000`, `l0.live_matrix_poll_ms` for the 250/50 ms steps); the `:9-12`
  `formatFieldValue` import and its comment go — `expectedDisplay` from `./_expected_display.js` replaces it at `:317`.
  `getLiveMatrixConfig()` → `{reason: string | null, shard: string}` without booting (`$PUT_MATRIX_SHARD`; the
  `:149-151` comment → "// The shard travels back through the Commands API: the test runs in the browser, where
  process.env does not exist; CI shards the file per B.10.1."). `startLiveMatrix({context}, device)` only boots and opens
  the page; `stopLiveMatrix()` tears down, scans, releases. `getRealCurrentValues(_context, paths)` throws `GET <path>
  -> HTTP <n>` on a non-ok status and `GET <path> did not answer a data object` when the body is not a plain object or
  carries `res`. `applyField()`: kinds `number`/`string` fill, `toggle` clicks until `data-value` equals the wanted value
  (at most two clicks, else throws), `enum` selects, `composite` fills each sub-input from `value`'s members; then Apply,
  waits until the Apply button is enabled again (the PUT and its post-write GET settled), reads `data-apply-status`, and
  for number/string polls the caption for `\`Current value: ${expectedDisplay(field, expectRenderedValue)}\``; the 50 ms
  sleep goes. `applyUnchangedFieldExpectNothingToSubmit()`'s JSDoc `:331` → "Leaves a non-dispatch toggle/enum at its
  current value and clicks Apply, expecting collectGroupBody() to sparse-omit it: no PUT fires, so no status is waited
  on." `remountAndReadField()` unchanged (an always-executed toggle reads back `"unset"`). New `archiveErrcount(_context,
  label)` — `GET /status`'s `errcount` written verbatim through `uv run scripts/_archive_evidence.py --runner live_twin`
  (A.U7.20's helper) and returns the archive path. Fold (A-C review, OR140.a (3)): `applyField()` accepts the browser dialog of a field
  carrying `confirm` (Playwright's dialog handler, `accept()`), asserting its message, and fails on a dialog it did not
  expect.
- **Resolved**: as M.WEB.061 for the shared frame. A.U23.16 "remountAndReadField() returns "unset" for ContMeas" needs no
  code: the remounted toggle's `data-value` is `"unset"` (M.WEB.014).
- **Unit**: U27. Stages: U6, U7, U8, U23 (A.U23.16/.32/.33), U24, U25, U36 (`:151` pointer — folded into this
  rewrite of the same comment); U0 conditional.
- **Depends**: M.WEB.061's helpers, M.WEB.069 (`_expected_display.js`); A.U7.20 (`scripts/_archive_evidence.py`, SCR).
- **Blast carried by**: `tests_js/live-backend-put-matrix.test.js` (M.WEB.063); `vitest-commands.d.ts` (M.WEB.076);
  `vitest.config.js` (M.WEB.074); Part N `l0.put_matrix_*` rows (A.U8.21, SPEC).
- **Kind**: test

## tests_js/live-backend.test.js, tests_js/live-backend-put-matrix.test.js

### M.WEB.063 The live tests run per device, expect exact words and cover the action fields
- **From**: A.U6.10 (3)(4) (`describe.each(DEVICE_IDS)`, device display name; the matrix per device with
  `beforeAll`/`afterAll`), A.U23.31 (`REAL_PATHS` goes), A.U23.32 (exact result words per class; independent display),
  A.U23.33 (action-field block), A.U23.34/.35 (assertions, timeouts), A.U23.46 (`test` → `it`), A.U23.14 (`willRoundTrip`),
  A.U23.16 + A.U25.12 + A.U6.17 (6) (`ALWAYS_REMOUNTS_AS` goes), A.U23.36 (the mask exclusion cites the page test),
  A.U24.52 (no skip branch, header), A.U8.21 (`CASE_TIMEOUT_MS` tag), A.U4.04/A.U4.05/A.U15.06 (`:80-93`, `:185-187`
  wording), A.S0930.27/.38 (the four restarting commands listed, not driven), A.U36.544 (1)(4) (`:2`, `:82` keep H.7;
  `:87` → H.4), A.U18.39 (read: `:134-137` holds).
- **Site**: `tests_js/live-backend.test.js:1-56`; `tests_js/live-backend-put-matrix.test.js:1-301`.
- **Change**: `live-backend.test.js`: header `:1-3` → "Exercises the real website's own JS in a real browser against a
  live digital-twin backend for every device (SPECIFICATION.md Part H.7). A missing interpreter or build fails the
  suite; it never skips."; `import { describe, expect, it } from "vitest";` and every `test(` → `it(`;
  `describe.each(DEVICE_IDS)`: the smoke asserts `titleHasSensorStation`, `deviceName` contains the device's generated
  `displayName`, `firstStatus` exactly `"valid"`, `resubmitStatus` exactly `"unchanged"` (the `:20-23` comment goes);
  "a full ceiling of browser tabs against one live twin all load, directly or on one reload" asserts `loadedFirstPass >=
  1` and `loadedAfterRetry === tabs`, its timeout a named constant under `// @tunable l0.live_concurrent_tabs_timeout_ms`
  (boot + `outer_cap_s` + 5 s + `tabs` × 20 s); new "the page recovers from a device restart without reloading" asserts
  `bannerShown`, `recovered` and `!reloaded`, timeout under `// @tunable l0.live_restart_recovery_timeout_ms` (boot +
  `READY_TIMEOUT_MS` + 60 s + margin); the `:332-334` quirk note stays; the skip branches go. `live-backend-put-matrix
  .test.js`: header → "Field-by-field PUT matrix through a real browser against a real twin, for every writable field of
  every device's generated definitions (SPECIFICATION.md Part H.7)."; `wozi.json` import, `REAL_PATHS`,
  `ALWAYS_REMOUNTS_AS` (its fields all leave the generic cases) and `groupHasDispatchField()` go; `const config = await
  commands.getLiveMatrixConfig()`; cases = `shardPutFieldCases(dedupePutFieldCases(DEVICE_IDS.flatMap(...)),
  config.shard)` from the definitions alone, `devicesWithCases` derived; `describe.each(devicesWithCases)` with
  `beforeAll(() => commands.startLiveMatrix(device))`/`afterAll(stopLiveMatrix)`; each case reads its `currentValue`
  through `getRealCurrentValues()` inside the test (the toggle split moves into the body); `willRoundTrip = field.kind ===
  "number" || field.kind === "string" || field.dispatch === true`; the resubmit expects exactly `"unchanged"` (the
  `"ValidOrUnchanged"` mode and its comment go; the special-value probe expects `"unchanged"` when the special equals the
  current value); every expected display through `expectedDisplay()`; the string "valid" probes take `validStringValue()`
  (M.WEB.060); `:185-187` "truncation" → "rounding to the nearest
  0.01"; `CASE_TIMEOUT_MS` under `// @tunable l0.put_matrix_case_timeout_ms = 15000`; `:87` → "(SPECIFICATION.md Part
  H.4)"; the mask exclusion `:134-137` stays and adds "(the page never sends a mask: render.test.js)". The derived
  never-"Unchanged" category (two identical valid sends both `"valid"`) runs for every `neverUnchanged()` non-composite
  field of the `sensors` section. New action-field block per device with the field: `PauseTime` 5 twice → `"valid"`
  both, the Status page's "Remaining Pause Time" shows 1-5 on its next poll, 3601 → `"invalid"`; `LightCmdLED` (devices
  with a `neopixel` instance) `{R: 10, G: 20, B: 30, T: 1}` → `"valid"`, the same at once → `"failed"`, `{R: 256, …}` →
  `"invalid"`; `SystemCmd` `mempause` → `"valid"` and `ResetErrors`: `archiveErrcount()` first, then Yes → `"valid"` — both
  through the page's confirmation, accepted by the command (M.WEB.062; OR140.a (3), A-C review fold) — and every
  row reads 0 on the next poll; one comment line: "reboot, bootloader, resetconfig and erasefram end the twin process:
  covered at L1 and L2 (Run 13) and on silicon, not driven here."; the skip branch goes.
- **Resolved**: A.U6.17 (6)'s derived category "two identical valid sends both Valid" would fail for `LightCmdLED`
  (busy refusal, A.U9.03, owner 2026-09-29) — the composite command keeps its own block (A.U23.33) and the mock's busy
  cases (M.WEB.052); `PauseTime`'s two-send check moves into A.U23.33's block (settled by A.U9.03/OR102.a (5); agent
  decision D10 for the placement). A.U23.16's `ContMeas: "unset"` remount entry and A.U25.12's `ForceCalRef` removal
  both edit `ALWAYS_REMOUNTS_AS`, which A.U6.17 (6) empties of every field (the generic cases skip `neverUnchanged()`
  fields) — the constant goes. A.S0930.27 adds the two new words to A.U23.33's not-driven list.
- **Unit**: U27 (shares the command files' latest stage; the test files' own latest constituent is A.U25.12, U25).
  Stages: U4 (wording), U6 (per device), U8 (tags), U23 (A.U23.14/.31-.36/.46), U24 (A.U24.52), U25 (A.U25.12).
- **Depends**: M.WEB.050, M.WEB.060, M.WEB.061, M.WEB.062, M.WEB.069.
- **Blast carried by**: CI `web-unit-tests`/`web-put-matrix` timeouts re-sized from per-device wall clock (A.U6.10/U28,
  TOOL); SPEC H.7 live tier sentences (A.U36.517 (6), SPEC); Part N `l0.*` rows (A.U8.21, A.U23.34/.35 Docs, SPEC).
- **Kind**: test

## tests_js/shell.test.js (new)

### M.WEB.064 The shell's lifecycle, clock, reload and watch are tested from outside
- **From**: A.U23.07 (no timer, listener or request after `stop()`; two starts leave one set of listeners), A.U23.06
  (build compare, clock, hidden pause, failing watch, reload after a pending Apply).
- **Site**: new `tests_js/shell.test.js`.
- **Change**: header (≤ 3 lines) "Tests js/shell.js: section switching, the stop handle, the device clock and the
  build watch's reload rule." Cases with a fake `visibility`, a counting `EventTarget` as `keyTarget`, an injected
  `reload` spy and `window.fetch` stubs answering `/status` and `/system`: after `stop()` no timer runs, no listener stays
  on `keyTarget`, no request follows; start-stop-start leaves one set of listeners; a changed `build` on the second watch
  calls `reload` once, an unchanged one never; `nowS()` is `null` until `UnixTime` is a number, then tracks fake time;
  hidden pauses the watch; a watch whose `/system` GET rejects neither reloads nor rejects unhandled (`unhandledrejection`
  spy); a changed build seen while an Apply is pending reloads only after that Apply settles. Fold (A-C review, OR140.a (15)): with a fake `history` (`current`/`push`/`onPop`): a menu
  selection pushes one entry, selecting the current section pushes none, a pop selects the popped section without
  pushing, Forward after Back re-selects, a deep-link key opens its section and an unknown one the landing section, and
  `stop()` removes the pop listener.
- **Resolved**: —
- **Unit**: U23.
- **Depends**: M.WEB.025.
- **Blast carried by**: —
- **Kind**: test

## tests_js/api-reference-agreement.test.js (new)

### M.WEB.065 The definitions, the mock and the REST reference agree
- **From**: A.U23.31.
- **Site**: new `tests_js/api-reference-agreement.test.js`.
- **Change**: header (≤ 3 lines); per device of `DEVICE_IDS`: the reference's (method, path) pairs equal the pairs the
  definitions sections declare (`rest.get` → GET, `rest.put` → PUT); the reference's result words equal
  `js/api-contract.js`'s four constants; the reference's code catalog equals the mock's `STANDARD_CODES`, read from
  `js/mock-server.js?raw` by `readObjectConst()` (M.WEB.068), so the mock gains no test-only export. No per-field comparison (A.U23.31: the reference's fields come from the
  definitions).
- **Resolved**: the mock keeps `STANDARD_CODES` module-private (OR36.a (1)); the test reads it as text (agent decision
  D11).
- **Unit**: U23.
- **Depends**: M.WEB.050 (`API_REFERENCES`), M.WEB.068; A.U19.20 (reference generated, GEN M.GEN.033).
- **Blast carried by**: SPEC H.8 test list (A.U36.517, SPEC).
- **Kind**: test

## tests_js/site-functions.test.js (new)

### M.WEB.066 Every legacy page function has its counterpart, per device
- **From**: A.U23.48, A.U23.39 (read: inlined favicon), A.U6.15 (read: no variant literal).
- **Site**: new `tests_js/site-functions.test.js`.
- **Change**: header (≤ 3 lines); per device from the generated definitions: a Measurements section with one group per
  sensor instance; a Sensors section with one writable group per sensor; Networking with identity, Wi-Fi LED and NTP
  groups; System settings and a command group whose options include `reboot`, `bootloader` and `mempause`; the
  notification section's LED flash, pause and auto-configuration groups where the device has them; every writable group
  shows per-field result colours after an Apply against the mock. The staged page's inlined favicon is pinned by
  `tests_scripts/test_stage_website.py` (A.U23.39), not here: the browser tier never sees a staged page.
- **Resolved**: A.U23.48 also asks "the staged page carries the inlined favicon" in this file; no staged page reaches
  `tests_js/` (staging is `scripts/_stage_website.py`'s, A.U23.38), and A.U23.39's L0 test pins exactly that fact —
  the clause is carried there (no second check).
- **Unit**: U23.
- **Depends**: M.WEB.050, M.WEB.043.
- **Blast carried by**: the audit's one-time legacy page ledger (A.U23.48 Change, execution step, PROC).
- **Kind**: test

## tests_js/_test_setup.js (new)

### M.WEB.067 Real timers and spies restored after every test
- **From**: A.U24.14.
- **Site**: new `tests_js/_test_setup.js`.
- **Change**: one-line header "Vitest setup: real timers after every test (spies are restored by restoreMocks in
  vitest.config.js)."; `afterEach(() => { vi.useRealTimers(); });`.
- **Resolved**: —
- **Unit**: U24.
- **Depends**: M.WEB.074 (`setupFiles`).
- **Blast carried by**: every test file's trailing restores (M.WEB.051-.054); SPEC H.8 test note (A.U24.14 Docs, SPEC).
- **Kind**: test

## tests_js/_source_constants.js (new), tests_js/source-constants.test.js (new)

### M.WEB.068 Tests read a module's constants from its source, not through test-only exports
- **From**: A.U23.37 (the reader; `definitions.test.js` and the timeout read through it), M.WEB.065 (object constant),
  M.WEB.051 (`POLL_BACKOFF_MAX_MS`).
- **Site**: new `tests_js/_source_constants.js`, new `tests_js/source-constants.test.js`.
- **Change**: `export function readIntConst(source, name)` — matches `^const <NAME> = (?<value>-?\d+);$` (multiline, a named group) in a module's
  raw text (imported with Vite's `?raw`) and returns the integer, throwing `Error(\`no const ${name} in source\`)` when
  absent; `export function readObjectConst(source, name)` — the `const <NAME> = {…};` literal of string values keyed by
  integers, parsed without `eval` (`/(?<code>\d+):\s*"(?<text>[^"]*)"/gu`; named groups, ESLint's
  `prefer-named-capture-group`). Header (≤ 3 lines) names the rule: "tests adapt to the
  code, not the code to the tests" (owner, 2026-09-26). The test: each reader finds `DEFAULT_TIMEOUT_MS`,
  `SUPPORTED_SCHEMA_MAJOR`, `POLL_BACKOFF_MAX_MS` and `STANDARD_CODES` in their real modules and throws on a missing
  name.
- **Resolved**: A.U23.37 names one numeric reader; the code-table read of M.WEB.065 needs the object form (agent
  decision D11).
- **Unit**: U23.
- **Depends**: `tsconfig.json` `vite/client` types for `?raw` (M.WEB.073).
- **Blast carried by**: —
- **Kind**: test

## tests_js/_expected_display.js (new), tests_js/expected-display.test.js (new)

### M.WEB.069 An independent expected-display oracle for the live tier
- **From**: A.U23.32 (2).
- **Site**: new `tests_js/_expected_display.js`, new `tests_js/expected-display.test.js`.
- **Change**: `export function expectedDisplay(field, value)`, written without `js/field-format.js`: "—" for
  null/undefined; eight "•" for a masked field; the option label for an enum; a number with `decimals` d built by integer
  arithmetic (`Math.round(Math.abs(v) * 10 ** d)` split into integer and zero-padded fraction digits, sign re-attached);
  otherwise `String(value)`. Pure, no Node or DOM API (it is imported by the Node command module and the browser test).
  The test's hand-written cases: 1.5 with decimals 3 → "1.500", −0.0005 with decimals 3 → "-0.001", a masked field, an
  enum label. Header (≤ 3 lines) names its independence (OR19.a (2)).
- **Resolved**: —
- **Unit**: U23.
- **Depends**: —
- **Blast carried by**: SPEC H.8.1 names this module as the Node- and browser-safe one (Gaps item 4).
- **Kind**: test

## eslint.config.js

### M.WEB.070 One lint config: header first, shipped-code floor and sinks, reasons on disables, pinned ceilings
- **From**: A.U28.42 (header block first), A.U36.544 (1) (`:7` pointer), A.U36.501 (2) (`ecmaVersion: 2022` for `js/`
  and `html/`), A.U23.40 (`PRODUCTION_ONLY_RULES`), A.U24.48 (`eslint-comments` plugin rules in every block), A.U23.05 +
  A.U24.52 (the `no-console` comment), A.U5.18 (ceilings at the measured maximum, pinned by a test), A.U23.10/.26/.28
  (ceilings follow the new measured maximum), A.U36.038 (1) (local D.15 order rule), A.U7.10 (`_summary_reporter.js`
  in the Node block), A.U24.69/A.U27.15 (read: two more Node-context helpers), A.SDEP.04 (new core rules decided at the
  refresh), A.SDEP.02 (read: suppressions go in the per-rule entries), A.U23.41 (read: the layering guard asserts the
  sink rule's globs).
- **Site**: `eslint.config.js:1-202`.
- **Change**: first block (before the imports) — `/** ESLint flat config for js/ and tests_js/ - the website's
  ruff-equivalent lint pass (SPECIFICATION.md H.8). Shipped JS stays plain, hand-written ES modules; this is dev-tooling
  only, mirroring pyproject.toml's [tool.ruff.lint] role. */` (3 prose lines); imports gain `comments from
  "@eslint-community/eslint-plugin-eslint-comments"`. `BUG_CATCHING_RULES`: the `:108-110` comment → "// --- console.log
  is debug residue; console.error/warn are real diagnostics --- / // a section's once-per-episode failure line
  (js/render.js) is real signal; scripts/*.mjs is exempt below (H.8)."; the four ceilings (`complexity`, `max-depth`,
  `max-nested-callbacks`, `max-classes-per-file`) each at the maximum measured over their globs at landing (only ever
  lowered; the comment `:113-114` → "// --- complexity ceilings at the measured maximum, so they gate regression:
  ratchet DOWN only, pinned by / // tests_js/lint-ceilings.test.js (H.8) ---"); any core rule the refresh adds is listed
  with a reason or left out (A.SDEP.04). New `const COMMENT_RULES = {"@eslint-community/eslint-comments/require-description":
  ["error", {ignore: []}], "@eslint-community/eslint-comments/no-unlimited-disable": "error"}` and `const
  PRODUCTION_ONLY_RULES = {"no-restricted-properties": ["error", {property: "innerHTML"}, {property: "outerHTML"},
  {property: "insertAdjacentHTML"}, {object: "document", property: "write"}, {object: "document", property:
  "writeln"}]}`, each preceded by one comment line naming its reason (every disable names its rule and reason; a server- or
  user-supplied string reaches the page as text only, SPECIFICATION.md H.4). New inline plugin `order` (no dependency,
  A.U36.038) with one rule checking top-level function declarations and `const` arrow-function bindings against D.15's
  key (private = not exported; roles `get*`/`is*`/`set*`; a binding an import-time statement needs is the named
  exception), comment ≤ 3 lines. Every block registers `plugins: {"@eslint-community/eslint-comments": comments, order}`
  and spreads `COMMENT_RULES` and the order rule into its rules. `js/**/*.js` and `html/**/*.html` blocks: `ecmaVersion:
  2022` (one comment line above the first: "// The shipped site's floor (SPECIFICATION.md H.1): ES2022, the same level
  tsconfig.json's target and lib pin.") and `PRODUCTION_ONLY_RULES`; the test, command, config and script blocks keep
  `"latest"`. The `tests_js/**/*.js` block's `ignores` and the Node block's `files` both list the Node-context files:
  `tests_js/_live_twin_command.js`, `tests_js/_live_matrix_command.js`, `tests_js/_summary_reporter.js`,
  `tests_js/_port_lock.js`, `tests_js/_micropypath.js`, `tests_js/_lint_command.js`, `tests_js/_twin_process.js` (one
  shared `const NODE_CONTEXT_TEST_FILES`); its comment →
  "// Node-context tests_js files (Vitest Commands API modules and their Node-only helpers, the summary reporter) run in
  the / // real Node process, not the browser every other tests_js/*.js file runs in (SPECIFICATION.md H.7)." `:189-190`
  comment holds.
- **Resolved**: A.U24.52 removes the live-backend skip warning A.U23.05's comment would name — the comment names only
  the remaining `console.error` user (settled by the later unit, U24). A.U24.69's `tests_js/_port_lock.js` and A.U27.15's
  `tests_js/_micropypath.js` use `node:fs`/`process`, so they join the Node-context lists here and in the tsconfigs
  (M.WEB.073), as A.U7.10 does for its reporter (gap closed here). A.U28.42 keeps the header text; A.U36.544's pointer
  edit lands in it.
- **Unit**: U36 (A.U36.038's order rule, A.U36.501, A.U36.544). Stages: U0 (A.SDEP.04 new core rules), U5 (ceilings,
  A.U5.18), U7 (reporter in the Node lists), U23 (`PRODUCTION_ONLY_RULES`, ceilings re-measured, comment), U24 (comment
  rules and the comment's final text; `_port_lock.js`), U27 (`_micropypath.js`), U28 (header).
- **Depends**: M.WEB.072 (the plugin installed by the refresh), M.WEB.081 (ceiling test).
- **Blast carried by**: `npm run lint` and CI's web lint job (TOOL); A.U23.41 guard (TSC); A.U36.038's planted-disorder
  fixture (TSC/WEB, M.WEB.081 sibling); SPEC H.8 lint paragraph, H.1 floor, H.4 "Rendering safety" (A.U24.48 Docs,
  A.U36.501, A.U36.510 (3), SPEC); BACKLOG chroot list gains the devDependency (A.U24.48 Docs, DOCS).
- **Kind**: code, rule

## package.json

### M.WEB.071 Scripts build every device, preview safely, lint the built pages; pins follow the refresh
- **From**: A.U6.03 (3) (`build:definitions`, `build:site`, `prepreview`), A.U7.20 (`pretest:coverage` archives the
  previous report), A.U23.38 (`lint:html:built`), A.U28.24 (`preview`), A.U28.23 (`engines`, `@types/node`), A.U24.48
  (new devDependency), A.SDEP.04 (ranges to the newest), A.U36.547 (read: the README npm table equals these scripts),
  A.U27.11 (read: `build:site` calls the generator), A.U6.15 (read: the lock is not scanned), A.U28.26 (read: `playwright`
  is a direct devDependency), A.U1.01 (read: no legacy path).
- **Site**: `package.json:1-38`.
- **Change**: `"engines": {"node": ">=<M> <<M+1>"}` after `"type"` (M = `.nvmrc`'s major); scripts: `"build:definitions":
  "uv run scripts/_generate_sensortask_modules.py"`, `"build:site": "npm run build:definitions &&
  scripts/build_device_websites.sh"`, `"pretest:coverage": "npm run build:site && uv run scripts/_archive_evidence.py
  --runner npm_coverage htmlcov_js"`, `"lint:html:built": "scripts/build_device_websites.sh --stage-only build/staged_html && html-validate
  \"build/staged_html/*/index.html\""` (the loop over every `devices/*.toml`, `zz_test_` skipped, is the script's,
  M.SCR.020/.071; gap pass G2, M_SCR gap 1(b)), `"preview": "uv run
  scripts/preview_server.py"`, `"prepreview": "npm run build:definitions"`; `lint`, `typecheck`, `test*`, `pretest*`
  (still `npm run build:site`), `lint:html`, `lint:css` unchanged. `devDependencies`: every range `^<newest at the
  refresh>`, `"@types/node": "^<M>.<newest patch>"`, plus `"@eslint-community/eslint-plugin-eslint-comments":
  "^<newest>"`.
- **Resolved**: AC_NOTES 38: A.U28.24's bare `python3` preview runner meets G8/R05 ("an explicit check wherever a script
  runs a bare python3") by running through `uv run` (the venv's Python satisfies `requires-python` ≥ 3.11), so no
  version check is added and no bare `python3` site remains (settled by G8/R05). A.SDEP.04 "co-lands A.U28.23 (A-C moves
  it into this commit or leaves it in U28)" — moved: the refresh writes `engines` and `@types/node`'s major so the lock is
  regenerated once; A.U28.23's L0 pin check lands in U28 with A.U28.03's file. The lead's rule "package-lock.json/.nvmrc
  change only through the dependency refresh" puts A.U24.48's new devDependency into the same refresh commit; U24 only
  enables it (M.WEB.070).
- **Unit**: U28 (A.U28.24, the latest script). Stages: U0 (A.SDEP.04 ranges, `engines`, `@types/node`, the
  `eslint-comments` plugin), U6 (A.U6.03), U7 (A.U7.20), U23 (A.U23.38).
- **Depends**: M.WEB.072; SCR: `scripts/build_device_websites.sh` (A.U6.03), `scripts/preview_server.py` (A.U28.24),
  `scripts/_archive_evidence.py` (A.U7.20), the stager's `--stage-only` mode (A.U23.38).
- **Blast carried by**: CI web jobs' `npm run build:site` and `lint:html:built` steps (A.U6.12/A.U28.43, TOOL);
  `tests_scripts/test_tool_pins.py` `.nvmrc`/`engines`/`@types/node` check (A.U28.23/A.U28.03, TSC); README npm table and
  preview text (A.U36.547, A.U28.24 Docs, DOCS); SPEC H.2/H.8 preview text (A.U36.517 (2), SPEC); BACKLOG chroot list
  (A.U28.38, A.SDEP.21, A.U33.04, DOCS).
- **Kind**: code

## package-lock.json, .nvmrc

### M.WEB.072 The lock and the Node pin change only in the dependency refresh
- **From**: A.SDEP.04 (newest Active LTS major in `.nvmrc`; `npm install` regenerates the lock; `npm audit` read;
  Playwright Chromium installed), A.U28.23 (lock's root `engines`/`@types/node`), A.U24.48 (lock gains the plugin),
  A.U6.15 (read: the lock is excluded from the variant scan), A.U37.04 (read: the closing check lists every commit touching
  them in BACKLOG's chroot list), A.SDEP.21 (read: BACKLOG entry).
- **Site**: `.nvmrc:1`; `package-lock.json` (generated).
- **Change**: `.nvmrc` → the major of the newest Active LTS line in `https://nodejs.org/dist/index.json` at the refresh
  (unchanged `22` when that is still it); `package-lock.json` regenerated by one `npm install` in the refresh commit after
  M.WEB.071's U0 stage, never edited by hand; its diff reviewed (root `engines`, `@types/node`, the new plugin, the
  refreshed versions); every `npm audit` advisory in a shipped-path or CI-path package resolved or recorded in the refresh
  record. No other commit of the audit changes either file except the U37 second check of the same refresh procedure
  (OR129.a).
- **Resolved**: the brief's lead rule (lock and `.nvmrc` only through the refresh) is met by folding A.U28.23's and
  A.U24.48's dependency edits into the refresh (M.WEB.071).
- **Unit**: U0 (dependency refresh, before every B1 action; AC_NOTES 34-second).
- **Depends**: A.SDEP.01/.02 (hold-back rule, per-family gate, PROC).
- **Blast carried by**: CI `setup-node` (`node-version-file: .nvmrc`) and `setup_toolchain.py` `ensure_node()` (read the
  major — unchanged, TOOL); README `:208-209` Node major (A.SDEP.04 Docs, DOCS); BACKLOG chroot entry (A.SDEP.21, DOCS).
- **Kind**: code

## tsconfig.json, tsconfig.node.json (taken here), tsconfig.base.json (new)

### M.WEB.073 One shared tsc base, two passes that differ only in lib, types and files
- **From**: A.U28.25 (base file, headers, `skipLibCheck` trial, further checks, `.d.ts` → `.ts` fallback), A.U6.05 (3)
  (`types: ["vite/client"]`), A.U23.37 (read: `?raw` needs those types), A.U7.10 (reporter in the node pass), A.U6.11
  (`scripts/_cross_browser_probe.mjs` in the node pass), A.U24.69/A.U27.15 (Node-only helpers, gap), A.U36.501 (read:
  `target`/`lib` ES2022 is the floor ESLint now matches), A.U28.39 (read: every path resolves), A.U28.18 (read: the smoke
  stays in the node pass), A.U7.21 (read: `_memory_markers.js` stays in the browser pass).
- **Site**: `tsconfig.json:1-37`, `tsconfig.node.json:1-35`, new `tsconfig.base.json`.
- **Change**: `tsconfig.base.json` holds `target`, `module`, `moduleResolution`, `allowJs`, `checkJs`, `noEmit`,
  `strict`, the ten further checks, `skipLibCheck`, with A.U28.25's header (≤ 3 lines); `skipLibCheck` is first tried
  `false` — clean → stays `false` ("every declaration file is checked, the project's own included"); findings inside
  `node_modules` → stays `true` and the command declarations become `tests_js/vitest-commands.ts` (M.WEB.076); every
  further strictness option the installed `tsc` offers is switched on after a clean trial or named in the header with its
  reason. `tsconfig.json`: `"extends": "./tsconfig.base.json"`, `lib: ["ES2022", "DOM"]`, `"types": ["vite/client"]`,
  `include` `["js/**/*.js", "tests_js/**/*.js", <the command declarations file>]`, `exclude` = the Node-context files
  (`_live_twin_command.js`, `_live_matrix_command.js`, `_summary_reporter.js`, `_port_lock.js`, `_micropypath.js`,
  `_lint_command.js`, `_twin_process.js`);
  header and exclude comment are A.U28.25's texts. `tsconfig.node.json`: `extends` the base, `lib: ["ES2022"]`,
  `types: ["node"]`, `include` = the seven Node-context files plus `scripts/cross_browser_smoke.mjs` and
  `scripts/_cross_browser_probe.mjs`; header "Node-context pass: <those files>." (A.U28.25's text with the list
  completed).
- **Resolved**: A.U28.25's node-pass header names three files plus "every file A.U6.11 and A.U7.10 add"; the two
  Node-only helpers of A.U24.69/A.U27.15 complete the list (as M.WEB.070). A.U6.05's alternative (a triple-slash
  reference in the helper) is not taken: the `?raw` imports of A.U23.37 need the same types in other files.
- **Unit**: U28. Stages: U6 (`types`, A.U6.05; the probe, A.U6.11), U7 (reporter), U24 (`_port_lock.js`), U27
  (`_micropypath.js`).
- **Depends**: M.WEB.072 (installed `tsc`).
- **Blast carried by**: `package.json` `typecheck` (both `-p` passes unchanged); CI web filter `'tsconfig*.json'`
  (A.U28.07, TOOL); `tests_scripts/test_config_paths_resolve.py` (A.U28.39, TSC); SPEC H.8 TypeScript paragraph (A.U28.37,
  SPEC); CLAUDE.md config-file header list gains `tsconfig*.json` (A.U28.25 Docs, DOCS); BACKLOG chroot list (A.U28.38,
  DOCS).
- **Kind**: code

## vitest.config.js (taken here)

### M.WEB.074 Vitest config: header first, pinned Chromium by default, setup, reporter, every command
- **From**: A.U28.42 (header first), A.U28.26 (Chromium preference), A.U24.14 (`restoreMocks`, `setupFiles`), A.U7.10
  (`reporters`), A.U6.10 (`getLiveMatrixConfig`), A.U23.33 (`archiveErrcount`), A.U23.35 (`runLiveBackendRestartRecovery`),
  A.U6.04 (`:37-39` comment), A.SDEP.19 (W34/W36, conditional), A.U8.02 (read: the file is scanned for tags), A.U24.52
  (read: command names unchanged), A.U8.15 (`:31` tag; AC3_S S-12).
- **Site**: `vitest.config.js:1-61`.
- **Change**: the `:21-25` JSDoc moves above the imports as the first block (text unchanged). Imports add `chromium` from
  `"playwright"`. `launchOptions = !existsSync(chromium.executablePath()) && existsSync(sandboxChromium) ? {executablePath:
  sandboxChromium} : {}`, comment → "// The lock-pinned Playwright Chromium runs whenever it is installed; a session
  sandbox that cannot download it / // pre-installs one here (agent, 2026-08-21). Remove this fallback once the sandbox
  can run `npx playwright install chromium`." `test`: `restoreMocks: true`, `setupFiles: ["tests_js/_test_setup.js"]`,
  `reporters: ["default", "./tests_js/_summary_reporter.js"]`; coverage comment `:37-39` "(html/definitions/,
  mockdata/)" → "(the generated definitions and mockdata/)" (the `exclude` and its comment go only if A.SDEP.19 W34 finds
  the re-parse fixed); `commands` registers `runLiveBackendSmoke`, `runLiveBackendConcurrentTabs`,
  `runLiveBackendRestartRecovery`, `getLiveMatrixConfig`, `startLiveMatrix`, `stopLiveMatrix`, `getRealCurrentValues`,
  `applyField`, `applyUnchangedFieldExpectNothingToSubmit`, `remountAndReadField`, `archiveErrcount`, `probeLintRule`,
  `lintFixture` (M.WEB.081). `// @tunable l0.vitest_test_timeout_ms = 20000` on its own line directly above
  `testTimeout: 20000` (A.U8.02's grammar); the backstop comment above it stays within the 3-line cap.
- **Resolved**: —
- **Unit**: U28 (A.U28.26/.42). Stages: U6 (A.U6.04 comment, A.U6.10 command), U7 (reporter), U23 (two commands), U24
  (setup); U0 conditional (A.SDEP.19).
- **Depends**: M.WEB.067, M.WEB.077, M.WEB.061/.062.
- **Blast carried by**: `tests_scripts/test_js_coverage_excludes_json.py`, `test_js_coverage_report_dir.py` (pin the
  coverage halves, TSC); A.U27.28's pending header set drops this file (TSC); SPEC H.8 Vitest paragraph (A.U28.37, SPEC).
- **Kind**: code

## tests_js/_memory_markers.js (new), tests_js/memory-markers.test.js (new)

### M.WEB.075 One marker pair for every JS gate
- **From**: A.U7.21, A.U7.23 (read: the agreement test parses this file).
- **Site**: new `tests_js/_memory_markers.js`, new `tests_js/memory-markers.test.js`.
- **Change**: `export const MEMORY_ERROR_MARKERS = ["MemoryError", "memory allocation failed"];` and `export function
  memoryMarkerLines(text)` (the lines containing either marker); no Node built-ins (checked by the browser `tsc` pass);
  header (≤ 3 lines) names the four gates' shared pair (CLAUDE.md memory rule). The test: both spellings found, "simulated
  allocation failure" ignored.
- **Resolved**: —
- **Unit**: U7.
- **Depends**: —
- **Blast carried by**: importers M.WEB.061/.062 and `scripts/cross_browser_smoke.mjs` (A.U7.21, SCR);
  `tests_scripts/test_memory_error_gate_agreement.py` (A.U7.23, TSC); CLAUDE.md gate list and SPEC I.4(e), H.8 (A.U7.21
  Docs, DOCS/SPEC).
- **Kind**: test

## tests_js/vitest-commands.d.ts

### M.WEB.076 The command declarations match the commands, within the comment cap
- **From**: A.U28.25 (6) (three comment blocks; `.ts` fallback), A.U6.10 (5) (`device` parameters,
  `getLiveMatrixConfig`), A.U23.32/.34/.35 (return shapes, new command), A.U23.33 (`archiveErrcount`), A.U24.52 (no
  `skipped` arm), A.U28.18 (read).
- **Site**: `tests_js/vitest-commands.d.ts:1-67`.
- **Change**: the comment blocks become A.U28.25's three texts (header ≤ 3 lines; "Written out, not `typeof` imports …";
  "`export {}` makes this a module …"). `BrowserCommands`: `runLiveBackendSmoke: (device: string) => Promise<{
  titleHasSensorStation: boolean; deviceName: string; firstStatus: string | null; resubmitStatus: string | null }>`;
  `runLiveBackendConcurrentTabs: (device: string) => Promise<{ tabs: number; loadedFirstPass: number; loadedAfterRetry:
  number; failures: string[] }>`; `runLiveBackendRestartRecovery: (device: string) => Promise<{ bannerShown: boolean;
  recovered: boolean; reloaded: boolean }>`; `getLiveMatrixConfig: () => Promise<{ reason: string | null; shard: string
  }>`; `startLiveMatrix: (device: string) => Promise<void>`; `stopLiveMatrix`, `getRealCurrentValues`,
  `applyUnchangedFieldExpectNothingToSubmit`, `remountAndReadField` as today; `applyField` args `field: FieldDef` and
  `value: unknown` (composite values included); `archiveErrcount: (label: string) => Promise<string>`; `probeLintRule: (args: { rule: string; value: number }) =>
  Promise<number>`; `lintFixture: (args: { source: string }) => Promise<string[]>` (M.WEB.081). If M.WEB.073's
  `skipLibCheck` trial keeps it `true`, the file is `tests_js/vitest-commands.ts` with the same content.
- **Resolved**: —
- **Unit**: U28. Stages: U6, U23, U24.
- **Depends**: M.WEB.061, M.WEB.062, M.WEB.073.
- **Blast carried by**: `npm run typecheck` (both passes).
- **Kind**: test

## tests_js/_summary_reporter.js, tests_js/_summary_layout.js, tests_js/summary-reporter.test.js (new)

### M.WEB.077 `npm test` ends with the shared summary block
- **From**: A.U7.10, A.U7.02 (read: the layout), A.U28.25 (node pass includes the reporter).
- **Site**: new `tests_js/_summary_reporter.js`, `tests_js/_summary_layout.js`, `tests_js/summary-reporter.test.js`.
- **Change**: as A.U7.10: the reporter counts cases (todo as skipped), lists failed and skipped names with reasons and
  prints A.U7.02's block (`== Summary: npm test ==`, `Levels: L0`, `Exit code:` the code vitest exits with) through the
  pure `_summary_layout.js` (no Node built-ins); the reporter hooks are confirmed against the installed vitest at
  execution. The test imports the layout only.
- **Resolved**: —
- **Unit**: U7.
- **Depends**: M.WEB.074 (`reporters`), M.WEB.070/.073 (Node lists).
- **Blast carried by**: CI `web-coverage` job-summary step reads the coverage table by its header (A.U7.10, TOOL);
  `tests_scripts/test_summary_block.py` byte equality via `node tests_js/_summary_layout.js` (A.U7.10, TSC); SPEC H.8,
  E.10 (A.U7.10 Docs, SPEC).
- **Kind**: code, test

## tests_js/_port_lock.js (new)

### M.WEB.078 The JS side of the per-port lock
- **From**: A.U24.69, A.U27.39 (read: the smoke imports it).
- **Site**: new `tests_js/_port_lock.js`.
- **Change**: `export function acquirePortLock(port, runner)` — atomic `mkdirSync(\`${process.env.XDG_RUNTIME_DIR ??
  "/tmp"}/sensors-port-${port}.lock\`)` holding `{pid, runner}`; on success it records the port in
  `process.env.SENSORS_PORT_LOCKS_HELD` (space list) and sets `process.env.SENSORS_PORT_LOCK_OWNER = String(process.pid)`, so
  children inherit both (`scripts/_port_lock.sh`'s contract, M.SCR.012). On `EEXIST`: a recorded PID equal to
  `process.pid` is accepted without retaking (re-entrant: the smoke holds the lock across its device loop while each
  launch acquires again); a recorded PID equal to the inherited `SENSORS_PORT_LOCK_OWNER` with the port listed in the
  inherited `SENSORS_PORT_LOCKS_HELD` is accepted (a child of the holder); any other live recorded PID (`process.kill(pid,
  0)`) throws `Error(\`port ${port} is held by ${runner} (pid ${pid}) - run the suites one after the other (CLAUDE.md)\`)`;
  a dead PID's lock is taken over. Returns a release function — a no-op for an accepted (not taken) lock — removing only
  a directory whose recorded PID is `process.pid`, also registered on `process.on("exit")`. Header (≤ 3
  lines). Node-context (M.WEB.070/.073).
- **Resolved**: gap pass G2 (M_SCR gap 1(a)): the shell side gained inheritance by children (M.SCR.012, agent decision
  AD-1) and the smoke takes the lock once before its device loop (M.SCR.064), so the JS side keeps the same contract —
  one lock directory, one message, the same two environment variables — and is re-entrant within its own process.
- **Unit**: U24.
- **Depends**: `scripts/_port_lock.sh` (A.U24.69, SCR; M.SCR.012) — same directory, message and environment contract.
- **Blast carried by**: importers M.WEB.061/.062/.082 and `scripts/cross_browser_smoke.mjs` (A.U27.39, SCR);
  `tests_scripts/test_port_lock.py` (A.U24.69, TSC; its inherited-owner and same-process cases also driven against this
  module — hand-off TSC, `GAPS_G2.md`); CLAUDE.md "Two suites that both bind real ports" (A.U24.69 Docs,
  DOCS).
- **Kind**: test

## tests_js/_micropypath.js (new)

### M.WEB.079 The JS reader of the one MICROPYPATH definition
- **From**: A.U27.15.
- **Site**: new `tests_js/_micropypath.js`.
- **Change**: `export const MICROPYPATH` = the `twin` value of `scripts/micropypath.toml`, read with `node:fs` and the
  regex `/^twin = "(?<path>[^"]+)"$/mu` (a named group) (throws naming the file when absent). Header (≤ 3 lines). Node-context (M.WEB.070/.073).
- **Resolved**: —
- **Unit**: U27.
- **Depends**: `scripts/micropypath.toml` (A.U27.15, SCR).
- **Blast carried by**: importers M.WEB.061/.062 and `scripts/cross_browser_smoke.mjs` (A.U27.15, SCR);
  `tests_scripts/test_twin_never_needs_tests_on_its_path.py` (A.U25.44/A.U27.15, TSC).
- **Kind**: test

## tests_js/_a11y_checks.js (new), tests_js/accessibility.test.js (new)

### M.WEB.080 An automated accessibility check over every device and section
- **From**: A.U23.43 (7), A.U36.510 (read: H.1 names the test).
- **Site**: new `tests_js/_a11y_checks.js`, new `tests_js/accessibility.test.js`.
- **Change**: pure DOM functions and, for every device (`GENERATED_DEFINITIONS`) and every section rendered against
  the composed mock: ids unique; every `label[for]` names an existing labelable element; every input/select/button has an
  accessible name (label, `aria-label`, `aria-labelledby` or text); every masked input has
  `autocomplete="new-password"`; the drawer is `inert` when closed and not when open, and focus moves as M.WEB.026
  states. No npm dependency. Headers (≤ 3 lines).
- **Resolved**: —
- **Unit**: U23.
- **Depends**: M.WEB.014, M.WEB.026, M.WEB.043, M.WEB.050.
- **Blast carried by**: SPEC H.1 accessibility sentence (A.U36.510 (1), SPEC).
- **Kind**: test

## tests_js/lint-ceilings.test.js (new)

### M.WEB.081 The four ESLint ceilings sit at the measured maximum
- **From**: A.U5.18 (JS half), A.U36.038 (read: the order rule's planted-disorder check lives with it).
- **Site**: new `tests_js/lint-ceilings.test.js`, new `tests_js/_lint_command.js`.
- **Change**: `tests_js/_lint_command.js` (Node-context, header ≤ 3 lines) exports the Commands API command
  `probeLintRule(_context, {rule, value})`, which runs ESLint's Node API (`new ESLint({overrideConfig})`) over every glob
  the ceilings apply to with the rule at `value` and returns the finding count; `lintFixture(_context, {source})` lints
  a source string under the `js/` block and returns the rule ids reported. `tests_js/lint-ceilings.test.js` (header ≤ 3
  lines): each of `complexity`, `max-depth`, `max-nested-callbacks`, `max-classes-per-file` has at least one finding at
  `<value - 1>` and none at `<value>` (the values read from `eslint.config.js?raw`); the order rule (M.WEB.070) reports
  on a planted out-of-order fixture.
- **Resolved**: A.U5.18 runs ESLint's Node API from `tests_js/`; vitest's browser mode has no Node API in the page, so
  the probe is a Commands API command like the live-twin ones (agent decision D12).
- **Unit**: U36 (the order-rule case). Stage U5 (the ceilings).
- **Depends**: M.WEB.070; M.WEB.073/.074/.076 (`_lint_command.js` in the Node lists, registered, declared).
- **Blast carried by**: SPEC D.10, Part E, H.8 name the check (A.U5.18 Docs, SPEC).
- **Kind**: test

## tests_js/_twin_process.js (new), tests_js/_dom_helpers.js (new)

### M.WEB.082 One copy of each shared JS test helper
- **From**: A.U24.49 (G2/R26 "one copy of each shared test double", OR24 "one material"; its Blast leaves the `tests_js`
  clone groups to U23, where no action takes them — gap closed here), A.U6.10/A.U7.21/A.U24.53/A.U24.69/A.U25.09/A.U27.12/
  A.U27.15 (read: the frame both command modules now share, M.WEB.061/.062).
- **Site**: `tests_js/_live_twin_command.js:26-117` and `tests_js/_live_matrix_command.js:31-116` (`sleep`,
  `waitUntilServing`, `spawnTwin`, `stopTwin`); `tests_js/render.test.js:25-39` and `tests_js/templates.test.js`
  (`mustQuery`); `tests_js/app.test.js:45-58` and `tests_js/main.test.js` (`buildElements`); new `tests_js/_twin_process.js`,
  new `tests_js/_dom_helpers.js`.
- **Change**: `tests_js/_twin_process.js` (Node-context, header ≤ 3 lines) exports `sleep(ms)`, `waitUntilServing(port,
  timeoutMs)`, `spawnTwin({device, port, configDir})` (M.WEB.061's argument list, the drained bounded output buffer and
  the `error` listener with its comment) returning `{proc, output()}`, and `stopTwin(proc)` (today's SIGINT/SIGKILL logic
  with its two comments), plus the frame M.WEB.061 states once: the binary probe, the twin `MICROPYPATH` with `frozen_modules` replaced by
  `build/generated_html/<device>` (A.U6.10 (1)), the per-run config dir, the port-53 lock (re-entrant for the same
  process, M.WEB.078) and the post-stop marker scan. `scripts/cross_browser_smoke.mjs` imports the same frame
  (M.SCR.064; gap pass G2, M_SCR gap 1(a)). Both command modules import them and keep only their own commands and port
  constants. `tests_js/_dom_helpers.js` (header ≤ 3 lines) exports `mustQuery(root, selector)` (today's JSDoc and body)
  and `buildElements()` (the entry element set), imported by `render.test.js`, `templates.test.js`, `app.test.js`,
  `main.test.js`; `buildFetchStub()` stays per file (the two differ in what they serve).
- **Resolved**: the gap is a G2/R26 requirement with no carrying action (A.U24.49 names U23, U23 has none); the split
  follows A.U24.49's own rule ("a clone whose copies differ in behaviour keeps one shared shape with a parameter for the
  difference") — `buildFetchStub()`'s copies serve different routes, so they are not one clone (agent decision D13).
- **Unit**: U24 (A.U24.49's unit; lands after M.WEB.061/.062's U24 stages, before their U27 stage, which then edits the
  shared module).
- **Depends**: M.WEB.061, M.WEB.062; M.WEB.070/.073 (Node lists).
- **Blast carried by**: A.U25.44's guard finds the twin launch in `_twin_process.js` through its `MICROPYPATH` import
  (TSC); A.U7.23's import check names `_twin_process.js` as the importer of `_memory_markers.js` (Gaps item 7); SPEC G.1/E.2.1
  helper list (A.U24.49 Docs, SPEC).
- **Kind**: test

## Gaps for other clusters

1. **CLUSTERS.md / orchestrator**: `mockdata/` (`dev.json`, `wozi.json`, new `samples.json`), `vitest.config.js`,
   `tsconfig.node.json` and the new `tsconfig.base.json` are named by no cluster; WEB took them (M.WEB.045, .073, .074),
   as GEN took `buildgen/limits.py`. CLUSTERS.md should list them under WEB.
2. **GEN (M.GEN.046/.017)**: the `@web` `shape` value set is written as `hostLabel|countryCode`; the tags M.SRC_NET.043 and
   .073 settle use four values — `hostName` (`NTPHost`, A.U10.41) and `ipv4List` (`DNSFallback`, A.U18.10) as well. The
   grammar check, `_string_field()`'s emission and `tests_scripts/test_buildgen_web_tag.py`'s accept cases must take all
   four (the website validator and the mock already do, M.WEB.006/.041).
3. **GEN + SRC_NET**: `PW`'s schema special `""` (open network, `src/asy_wifi_service.py:46`) never reaches the
   definitions — `_string_field()` emits no `specialValues` — so the mock rejects a `""` the server accepts (OR43.a (2)
   "field for field"; A.U6.28 assumed it was carried). The generator emits a string field's schema special as
   `specialValues` with the tag's label (the `PW` tag gains `special:""="Open network"`, SRC_NET); the mock's string branch
   already accepts a special first (M.WEB.041).
4. **SPEC**: (a) H.6.1 row 1 (A.U36.044) lists the lowercase time-struct members; after A.U10.40 they are `Year`, `Month`,
   `MDay`, `Hour`, `Minute`, `Second`, `Weekday`, `Yearday` (M.WEB.001); (b) H.6.1 row 8 states the client flattens sensor
   fields to `<sensor>_<field>` in `groupValuesFrom()` — false after A.U23.19 (maintenance fields read by `path`, no
   flattening, M.WEB.020); row 7 "js/render.js status merge" → the `statusPath` read; row 9's client cell → the
   definitions' options (the mock derives them, M.WEB.041); (c) A.U36.510 (5)'s mock paragraph "SCD30's `ForceCalRef`
   reports `400` on GET" → "reads back the last value applied, 400 on a fresh mock (A.U25.12)", and "`ContMeas`/
   `SGPResetVOC` are never reported by GET" → "dispatch fields and `ContMeas` are never reported by GET" (`SGPResetVOC` is
   `ResetVOC` after A.U10.40); (d) H.2 `:4312` ("`field-format.js` … split so Node-context tests can reuse it") and H.8.1
   name `tests_js/_expected_display.js` as the Node- and browser-safe module; `field-format.js` is pure formatting with no
   DOM dependency (M.WEB.012/.069); (e) H.4/H.6 mention the `lasttaskend` display "<Task> at uptime <n> s" with A.U32.06's
   `/status` row (M.WEB.012, D2).
5. **GEN (M.GEN.062, CSS)**: A.U23.20 (2)(3) also need a button-chrome reset for `.field-value.code-value` (a readonly
   code field shown as its plain value) and a muted `.code-number` for `CalLight`'s "(n)"; M.GEN.062 lists only the history
   pill reset, `.code-description` and `[data-code-tone]`. The Clear button needs no CSS (it carries `action-button`,
   M.WEB.014). No WEB change depends on GEN Q2: the JS only sets `data-code-tone`; the colours and the token test are CSS
   and TSC.
6. **SCR**: (a) `npm run build:site`'s generator writes the JS freshness stamp to
   `build/generated_src/definitions/inputs_stamp.json` (`{"tomls": {<name>: <sha256>}}`), not
   `html/definitions/.inputs_stamp.json` (A.U24.46 (3); M.WEB.050 — `html/definitions/` is deleted and the stager's drift
   rule forbids other `html/` files); (b) `lint:html:built` (M.WEB.071) calls the stager's `--stage-only` mode — its exact
   CLI is SCR's A.U23.38 merge; (c) `scripts/cross_browser_smoke.mjs` boots the twin with its own copy of
   spawn/stop/wait and now could import `tests_js/_twin_process.js` (M.WEB.082) — one material (OR24), SCR's decision
   whether to reuse it.
7. **TSC**: after M.WEB.082 the twin launch, its `MICROPYPATH` import, the `_memory_markers.js` import and the per-run
   config-dir removal live in `tests_js/_twin_process.js`: A.U7.23's import check, A.U25.44/A.U27.15's launch-site guard,
   A.U6.10's `test_live_command_device_args.py` and A.U24.53's no-`rmSync` text check read that file (the command modules
   import it); A.U8.02's tunables scan covers the new `tests_js` tags (`l0.poll_manager_poll_ms`, `l0.render_*`,
   `l0.live_twin_*`, `l0.live_matrix_poll_ms`, `l0.put_matrix_*`, `l0.live_concurrent_tabs_timeout_ms`,
   `l0.live_restart_recovery_timeout_ms`, `web.poll_backoff_max_ms`, `web.device_watch_interval_ms`) with Part N rows
   (SPEC).
8. **DOCS**: CLAUDE.md "Two suites that both bind real ports" says "`npm test`'s mock server" binds ports — the mock
   intercepts `fetch` and binds none; the port-binding part of `npm test` is the live twin (port 53, 19481/19482), now
   under the per-port lock (A.U24.69, M.WEB.078); A.U24.69's CLAUDE.md edit should name it. BACKLOG's chroot entry for the
   dependency refresh (A.SDEP.21) names `@eslint-community/eslint-plugin-eslint-comments` (moved into the refresh,
   M.WEB.071) instead of A.U24.48's own line.

## Adherence findings (end state of each file, after every merged change)

- **`js/` (all modules)**: comment cap — every header and inline block written above is ≤ 3 prose lines; typedef and
  JSDoc `@param`/`@returns` runs are type data (`npm run typecheck`), not counted. Pointers — HEAD's wrong ones fixed in
  place: `templates.js:8` "Part H.7's splitting rule" → H.2 (M.WEB.013); `render.js:44`, `:127`, `:225` (M.WEB.019/.021,
  with A.U36.544); `field-format.js:27` the gone `src/sensortask_wozi.py` (M.WEB.012); `field-format.js:1-3`'s
  Node-reuse reason, false once A.U23.32 lands (M.WEB.012; SPEC follow-up Gaps 4 (d)); `render.js:216-218` named
  `coerce_numeric()`, which M_SRC_CORE GAP-G13 makes private (M.WEB.021). No temporary audit ID in any written text
  (G9/R12): actor tags only. `src/`↔`js/` mirror (SPEC Part G): result words, the unavailable marker, time-struct keys
  (M.WEB.001), the envelope code table and `COUNTER_CAP` (M.WEB.040), the dispatch fields, `SystemCmd` options,
  `PauseTime` bounds and `LightCmdLED` members (derived from the definitions, M.WEB.041), the four shape rules (one corpus,
  M.WEB.052) — each pinned by an L0 check (A.U23.24-.27, TSC) or the shared corpus; error numbers (including M_SRC_CORE
  GAP-G2's new errno 25) reach the page only through the generated `codes` blocks, so no JS literal mirrors them. Layering
  (A.U23.41): DOM creation only in `templates.js`; `document.` only in `main.js`/`app.js` (the shell takes `Document` and
  `keyTarget` from the entry; nav reads focus through `:focus-within`, M.WEB.026); controllers write only `applyStatus`,
  `shown`, `navOpen`, `sourceState` — checked. OR36.a (1): no test-only export or seam — `buildField`,
  `SUPPORTED_SCHEMA_MAJOR`, `DEFAULT_TIMEOUT_MS` lose `export`, `isBusy` goes, A.U23.07's `fetchImpl?` goes (M.WEB.025),
  `STANDARD_CODES` stays private (M.WEB.065). OR78.a (1): no variant literal (`app.js` defaults to the manifest's first
  device, M.WEB.031). OR94 / A28: the look is unchanged — the history pills keep their look and the type only colours the
  number (no border cue, AC_NOTES 26/37), `N` placeholders stay spans and the no-data rollup appears only when needed
  (D3), the specials hint stays on number fields (D4); the code descriptions appear only on click (OR94 "14 b"). OR121/
  OR122: "Reset to defaults"/"Erase FRAM" come from the definitions' options with the existing dropdown and Apply;
  OR140.a (3) (owner, 2026-10-02): every system command and the error-history clear ask the browser's confirmation
  first, beside the DNS fallback Clear's (owner OR56.a (2)); the API stays one command per request — A.S0930.20 (5)'s
  zero-call spy inverts to one call (M.WEB.021, .054; A-C review fold). OR42.a (3): a PUT is never retried or repeated, and a sent PUT is never aborted
  (M.WEB.021). OR103 "no unbounded counters": the mock's uptimes saturate at `COUNTER_CAP` (M.WEB.042); the page's own
  failure count is bounded (finding below, fixed in M.WEB.003). ESLint rules the new code must pass: `prefer-named-capture-group` (regexes written
  non-capturing or named, M.WEB.018/.068/.079), `no-console` (only `console.error`, M.WEB.020), the sink ban (M.WEB.070).
  D.15 order: every new function is placed by A.U36.038's reorder, which lands last in U36.
- **`mockdata/samples.json`**: no variant literal (`Hostname` "SensorNode"); codes catalogued, newest-entry rule;
  credentials are fake test values (CLAUDE.md "no real credentials": `PW`/`HotspotPW` samples are placeholders, the one
  real credential stays in `src/`).
- **`tests_js/`**: every file has a ≤ 3-line header (A.U27.28's eight plus every new file); fake timers and spies are
  restored on every path (M.WEB.067); no test reads a product-private value through an export (M.WEB.068); expected values
  in the live tier come from an independent oracle (M.WEB.069, OR19.a (2)); a missing interpreter fails, never skips
  (M.WEB.061-.063, OR21.a (3)); every live twin run is scanned for both memory markers (M.WEB.061, CLAUDE.md memory
  rule); "two port-binding suites never concurrently" (CLAUDE.md, the brief's special care) is enforced by the port-53 lock
  every JS twin launch takes (M.WEB.061/.078); live runs keep their twin state in a per-run temp dir and never delete
  `digital_twin/config/` (G8/R33); the shared helpers are one copy each (M.WEB.082, G2/R26). Wear: no `tests_js` test
  writes real hardware; the live tier's `ResetErrors` archives the errcount first (A.U23.33, OR38.a (2)).
- **Config files** (`eslint.config.js`, `package.json`, `tsconfig*.json`, `vitest.config.js`): each opens with one
  header block (A.U28.42/A.U28.25; JSON-with-comments files through their first comment); `package-lock.json` and
  `.nvmrc` change only in the dependency refresh (the brief's rule; M.WEB.071/.072); every path a config names resolves
  (A.U28.39); every Node-context `tests_js` file is in both Node lists (M.WEB.070/.073 — the gap for `_port_lock.js`,
  `_micropypath.js`, `_lint_command.js`, `_twin_process.js` closed); every tool stays pinned through the lock.
- **Finding fixed — the back-off counter**: as A.U23.05 wrote it, the consecutive-failure count grows for as long as a
  section fails (OR103 "no unbounded counters anywhere"; `2 ** k` would also reach `Infinity`). M.WEB.003 stops the
  increment once `intervalMs * 2 ** (k - 1)` reaches `POLL_BACKOFF_MAX_MS`.
- **Brief "special care" items**: AC_NOTES 28 — confirmed, settled in M.WEB.020 (no extra site). OR94/A28, OR121/OR122,
  the mirror obligation, JSDoc as type data, the mock/MicroPython concurrency rule, the lock/`.nvmrc` rule — as above. Every
  other AC_NOTES item naming `js/`: 26/37 (border cue dropped, M.WEB.016), 38 (A.U28.24's `python3` → `uv run`, M.WEB.071),
  34-second (dependency refresh before B1, M.WEB.072); items 33/36/27 reach the website only through definitions
  (`SystemCmd` words, M.GEN.015).

## Owner questions

None. Every conflict at a WEB site is settled by an owner row, the register, AC_NOTES, the brief's lead rules or a later
constituent (each named in its change's **Resolved** slot); M_SRC_SENS GAP-12's suggested question is settled by
A.U23.14/A.U23.15 and OR94 (M.WEB.014). GEN Q2 is answered (a) (OR132, AC_NOTES 41) and no WEB change depends on it
  (Gaps item 5).

## Agent decisions for the OR2.c review

Taken in this merge (the constituents' own agent decisions — back-off cap and watch interval, reload on a changed build,
`ContMeas`'s unset state, the `CalLight` tones, the age breakpoints, the accepted number syntax, `window.confirm` before
Clear, index-based ids, `autocomplete="new-password"`, recovery by one reload — stay as `audit/actions/U23.md` "Open
points" lists them):

- **D1** `startPolling()` takes one options object (`visibility`, `onError`, `stopAfterSuccess`) instead of four
  positional parameters, and the end of a section's failure episode is tracked by the section, where the post-Apply
  refresh also reports (M.WEB.003, .020).
- **D2** `LastTaskEnd`'s display: "<Task> at uptime <Uptime> s", "invalid value" for a malformed one, "—" for `null`
  (M.WEB.012).
- **D3** history `N` placeholders stay plain spans (the catalog has no `N` table); the "<n> modules without data" rollup
  span appears only when n > 0 (M.WEB.016).
- **D4** special-value meanings appear in the hint for number fields only; a readonly field shows its special's meaning
  in place (M.WEB.014).
- **D5** the card update refreshes a cleared input's placeholder with its caption (M.WEB.015).
- **D6** the section reports Apply start/end to the shell through `context.applyTracker` (M.WEB.020, .025).
- **D7** A.U23.07's `fetchImpl?` parameter is dropped as a test-only seam; one `visibilityOf(document)` helper in the
  shell serves both entries (M.WEB.025).
- **D8** the mock stores an always-executed field only when the device's composed data carries it, and its config copies
  exclude dispatch and `statusPath` fields — no readback key list (M.WEB.041, .043).
- **D9** every live-tier reader waits for the re-enabled Apply button before reading `data-apply-status` (M.WEB.061,
  .062).
- **D10** the live matrix's two-identical-sends check covers the sensors section's non-composite never-"Unchanged"
  fields; `PauseTime`'s twin-send check sits in the action-field block; `LightCmdLED` keeps its own busy cases
  (M.WEB.063).
- **D11** the mock's code table stays private; tests read it as text with a second source reader (M.WEB.065, .068).
- **D12** the ESLint ceiling probe runs as a Commands API command in a Node-context module (M.WEB.081).
- **D13** the duplicated live-twin process helpers and `mustQuery`/`buildElements` become one shared copy each;
  `buildFetchStub()` stays per file (M.WEB.082).

## Ledger
| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.S0930.09 | read: `SystemCmd` options derived from the definitions, no JS literal (M.WEB.041); the tuple is SRC_NET's |
| A.S0930.10 | read: no JS change, the dropdown renders the options (M.WEB.021); GEN M.GEN.015 |
| A.S0930.20 | M.WEB.052 ((4) mock), M.WEB.054 ((5) website); (1)-(3), (6), (7) TSC |
| A.S0930.27 | M.WEB.063 (the two words listed as not driven live); the rest TWIN/SCR |
| A.S0930.31 | read: the mock stays stateless (M.WEB.041); SRC_CORE |
| A.S0930.34 | read: website cases hold (M.WEB.054); (2)-(4) TSC |
| A.S0930.38 | read: "reboot/bootloader not driven live" holds (M.WEB.063); TWIN/SCR |
| A.SDEP.02 | read: suppression placement applied in M.WEB.070; the gate is PROC |
| A.SDEP.04 | M.WEB.072, M.WEB.071 (ranges, `engines`, `@types/node`), M.WEB.070 (new core rules), M.WEB.073 (tsc options) |
| A.SDEP.16 | M.WEB.061, M.WEB.062 (W15 `TZ`, conditional); the rest SCR/TWIN/TEST_UNIT |
| A.SDEP.19 | M.WEB.061, M.WEB.074 (W34/W36, conditional); the rest TOOL/SCR |
| A.SDEP.21 | DOCS (BACKLOG entry; Gaps item 8) |
| A.U0.06 | PROC (records the pins; no file change here) |
| A.U0.08 | read: the citation check scans `js/`/`tests_js/` text (TSC) |
| A.U0.20 | M.WEB.060 (one header with A.U6.09) |
| A.U0.28 | M.WEB.016 (stage U0), M.WEB.058; `html/style.css` GEN |
| A.U0.40 | dropped for its L07 site: A.U6.09 deletes it (M.WEB.060); the rest SPEC/TEST_UNIT/DOCS |
| A.U0.53 | M.WEB.021 (stage U0, superseded at U23 by A.U23.45's text) |
| A.U1.01 | read: no legacy path in `package.json`/`tsconfig.json` |
| A.U1.25 | dropped for `js/mock-server.js:178`: A.U23.27 deletes the comment (M.WEB.040); other sites other clusters |
| A.U10.06 | read: `TS` null renders "—" (M.WEB.012) |
| A.U10.32 | read: D.15 binds `js/`; applied through A.U36.038 (M.WEB.070); SPEC |
| A.U10.37 | read: module names cited by M.WEB.001/.040 |
| A.U10.40 | M.WEB.001, .012, .040-.045, .052, .054, .058, .063 (stage U10); the rest other clusters |
| A.U10.41 | M.WEB.004, .006, .041, .052 (`hostName` shape); `src/` SRC_NET |
| A.U11.21 | M.WEB.041 (gap listed, not mirrored); SPEC sentence |
| A.U11.26 | M.WEB.019 |
| A.U11.31 | M.WEB.019, M.WEB.041 |
| A.U15.06 | read: the wording is A.U4.05's (M.WEB.063) |
| A.U15.11 | read: no `tests_js` assertion |
| A.U15.12 | M.WEB.045 (mock rows); read M.WEB.057; `src/` SRC_SENS |
| A.U15.18 | M.WEB.045, M.WEB.012 |
| A.U15.19 | M.WEB.045 (`VOCState` sample); SRC_SENS |
| A.U15.36 | M.WEB.045 (`CalLight` sample); SRC_SENS |
| A.U17.19 | read: the mock reset leaves `UARTLINK` alone (M.WEB.041) |
| A.U18.10 | M.WEB.041, M.WEB.045, M.WEB.052; `src/` SRC_NET |
| A.U18.37 | read: masks only (M.WEB.042) |
| A.U18.38 | M.WEB.042, M.WEB.045, M.WEB.052 |
| A.U18.39 | read: page half is A.U23.36 (M.WEB.054) |
| A.U19.01 | M.WEB.041 |
| A.U19.02 | M.WEB.041, M.WEB.052 (its comment rewrite dropped with the comment) |
| A.U19.03 | M.WEB.041 |
| A.U19.04 | read: equality membership (M.WEB.041) |
| A.U19.06 | read: relied on by M.WEB.025 |
| A.U19.10 | M.WEB.042, M.WEB.045 |
| A.U19.15 | M.WEB.040, M.WEB.054 |
| A.U19.16 | M.WEB.001 |
| A.U19.20 | read: output consumed by M.WEB.050, M.WEB.065; GEN |
| A.U2.05 | read: entry shape unchanged |
| A.U2.21 | read: `codes` block consumed by M.WEB.016; GEN |
| A.U2.25 | M.WEB.045 |
| A.U20.16 | read: default instance key (M.WEB.043) |
| A.U20.27 | read |
| A.U23.01 | M.WEB.002, .007, .031, .053 |
| A.U23.02 | M.WEB.002, .051 |
| A.U23.03 | M.WEB.002, .020, .051, .054 |
| A.U23.04 | M.WEB.003, .020, .025, .030, .031 (the shared shell in `app.js`; AC3 S section 4), .051 |
| A.U23.05 | M.WEB.003, .020, .021, .051, .054, .070 |
| A.U23.06 | M.WEB.020, .025, .059, .064 |
| A.U23.07 | M.WEB.022, .025, .026, .030, .031, .059, .064 (`fetchImpl?` dropped, D7) |
| A.U23.08 | M.WEB.015, .016, .020, .054 |
| A.U23.09 | M.WEB.005, .006, .053, .055; `_shape_problems()` TSC |
| A.U23.10 | M.WEB.006, .055, .070 |
| A.U23.11 | M.WEB.001, .016, .020, .054, .058; CSS GEN |
| A.U23.12 | M.WEB.016, .019, .058; CSS GEN |
| A.U23.13 | M.WEB.019, .021, .054 |
| A.U23.14 | M.WEB.018, .019, .054, .063 |
| A.U23.15 | M.WEB.015, .021, .054 |
| A.U23.16 | M.WEB.004, .005, .014, .018, .021, .053, .054, .062; tag/grammar SRC_SENS/GEN |
| A.U23.17 | M.WEB.004, .006, .014, .021, .054; tag/grammar SRC_NET/GEN |
| A.U23.18 | M.WEB.004, .006, .020; generator GEN |
| A.U23.19 | M.WEB.020, .054, .057; generator GEN |
| A.U23.20 | M.WEB.004, .006, .014, .016, .058; CSS and catalog GEN |
| A.U23.21 | M.WEB.012, .014, .058 |
| A.U23.22 | GEN (template, catalog); its mock half M.WEB.042, .045 |
| A.U23.23 | M.WEB.004, .006, .014, .021, .054; tag SRC_SENS, grammar and CSS GEN |
| A.U23.24 | M.WEB.001, .012, .058; mirror test TSC |
| A.U23.25 | M.WEB.001, .040; mirror test TSC |
| A.U23.26 | M.WEB.040, .052, .054, .070 |
| A.U23.27 | M.WEB.040, .041, .052, .054; mirror test TSC |
| A.U23.28 | M.WEB.040, .041, .042, .052, .070 |
| A.U23.29 | M.WEB.040, .042, .045, .052, .054 |
| A.U23.30 | M.WEB.041 (holds), .052, .054; the definitions pytest TSC |
| A.U23.31 | M.WEB.050, .063, .065 |
| A.U23.32 | M.WEB.061, .062, .063, .069 |
| A.U23.33 | M.WEB.060, .062, .063, .074, .076 |
| A.U23.34 | M.WEB.061, .063, .076 |
| A.U23.35 | M.WEB.061, .063, .074, .076 |
| A.U23.36 | M.WEB.054 (already in its From as `.36`; AC3 S section 4 needs no edit), .063 |
| A.U23.37 | M.WEB.002, .005, .014, .051, .053, .058, .068; the notification half SRC_SENS; regexes TSC |
| A.U23.38 | SCR (stager); `package.json` script M.WEB.071; read M.WEB.013 |
| A.U23.39 | GEN/SCR (favicon, staging); M.WEB.066 note |
| A.U23.40 | M.WEB.014, .015, .018, .020, .054, .070 |
| A.U23.41 | read: TSC guard; the end state passes it (Adherence) |
| A.U23.42 | M.WEB.017, .020, .022, .026, .054, .059; CSS/markup GEN |
| A.U23.43 | M.WEB.014, .026, .058, .059, .080; CSS/markup GEN; (6) pill border cue dropped (AC_NOTES 26/37) |
| A.U23.44 | GEN M.GEN.062 / TSC token test (GEN Q2 answered (a), OR132); no WEB site |
| A.U23.45 | M.WEB.021 (`render.js:264-266`); SPEC row, `style.css` GEN |
| A.U23.46 | M.WEB.063 |
| A.U23.47 | TSC/TEST_UNIT (Python files); no WEB site |
| A.U23.48 | M.WEB.066; the legacy-page ledger step PROC |
| A.U23.49 | M.WEB.004, .006, .014, .041, .052, .058; tag SRC_SENS, grammar GEN |
| A.U24.14 | M.WEB.051, .053, .054, .067, .074 |
| A.U24.46 | M.WEB.050 (stamp path settled); writer SCR (Gaps item 6) |
| A.U24.48 | M.WEB.021, .054, .070, .071 (dependency moved into the refresh) |
| A.U24.49 | M.WEB.082 (the `tests_js` clone groups); Python helpers TEST_HELP |
| A.U24.52 | M.WEB.061, .062, .063, .076 |
| A.U24.53 | M.WEB.061, .062; the runner flag TWIN |
| A.U24.56 | A28 bullet void — A.U0.28 carries it (M.WEB.058); the rest other clusters |
| A.U24.69 | M.WEB.061, .062, .078; the bash half SCR |
| A.U25.09 | M.WEB.061, .062 |
| A.U25.12 | M.WEB.041, .052, .063; the SCD30 fake TWIN |
| A.U25.32 | M.WEB.061, .062 (one change with A.U24.53) |
| A.U25.44 | read: TSC guard (Gaps item 7) |
| A.U26.64 | read: an L4 test reads `js/poll-manager.js` (HW_BENCH) |
| A.U27.11 | read |
| A.U27.12 | M.WEB.061, .062 |
| A.U27.15 | M.WEB.061, .062, .079 |
| A.U27.28 | headers in M.WEB.051-.059, .063 and every new file; the gate TSC |
| A.U27.30 | read: no `=`/`~`/`*` rule in `js/`/`tests_js/` (its grep) |
| A.U27.39 | read: the smoke imports M.WEB.078 (SCR) |
| A.U28.18 | read: the smoke stays in the node pass (M.WEB.073) |
| A.U28.23 | M.WEB.071, .072 (moved into the refresh); the pin test TSC |
| A.U28.24 | M.WEB.071 (`uv run`, AC_NOTES 38); the server SCR |
| A.U28.25 | M.WEB.073, .076 |
| A.U28.26 | M.WEB.074; the smoke half SCR |
| A.U28.37 | read: SPEC |
| A.U28.38 | read: DOCS |
| A.U28.39 | read: TSC |
| A.U28.42 | M.WEB.070, .074; YAML files TOOL |
| A.U3.15 | M.WEB.045 |
| A.U32.05 | read: audit trace; displays in M.WEB.012 |
| A.U32.06 | M.WEB.004, .006, .012, .045, .056, .058; the rest SRC_CORE/GEN/SRC_NET |
| A.U33.04 | read: DOCS |
| A.U33.05 | read: SPEC/DOCS (`npm audit` stays out of lint; no runtime dependency holds) |
| A.U34.09 | read: DOCS (the website bundles no npm package — holds) |
| A.U35.03 | read: U35's whole-suite review covers `tests_js/` (PROC) |
| A.U35.46 | M.WEB.003, .025, .026, .030, .031, .051 |
| A.U36.038 | M.WEB.070, .081 (rule); the JS pure reorder lands last in U36; Python other clusters |
| A.U36.044 | SPEC (Gaps item 4 (a)(b)) |
| A.U36.500 | read: SPEC |
| A.U36.501 | M.WEB.070; H.1 SPEC |
| A.U36.503 | M.WEB.002 (comments folded); rows SPEC |
| A.U36.504 | read: SPEC (`neverUnchanged()` M.WEB.005) |
| A.U36.505 | read: SPEC |
| A.U36.507 | M.WEB.016; CSS GEN, H.4 SPEC |
| A.U36.510 | read: SPEC (Gaps item 4 (c)) |
| A.U36.513 | read: the `js/` comments are A.U6.10/A.U6.13's (M.WEB.012, .061) |
| A.U36.515 | read: SPEC |
| A.U36.516 | read: SPEC/DOCS |
| A.U36.517 | read: SPEC |
| A.U36.524 | read: DOCS |
| A.U36.542 | read: SPEC |
| A.U36.544 | M.WEB.012, .019, .021, .054, .062, .063, .070 (pointers); other sites other clusters |
| A.U36.547 | read: DOCS/TSC (README npm table = M.WEB.071's scripts) |
| A.U37.04 | read: PROC |
| A.U4.01 | M.WEB.041 (superseded by the resolution compare of A.U23.49) |
| A.U4.04 | M.WEB.063 |
| A.U4.05 | M.WEB.063 |
| A.U5.05 | read: the value (M.WEB.002) |
| A.U5.18 | M.WEB.070, .081; Python half TSC |
| A.U6.02 | read: SCR; consumed by M.WEB.031, .050 |
| A.U6.03 | M.WEB.071; scripts SCR |
| A.U6.04 | read: import moves in M.WEB.053, .057, .060, .063; comment M.WEB.074; files GEN |
| A.U6.05 | M.WEB.050, .053, .073 |
| A.U6.06 | M.WEB.004, .031, .043, .045, .056, .057 |
| A.U6.07 | M.WEB.031, .059 |
| A.U6.08 | M.WEB.056 |
| A.U6.09 | M.WEB.060 |
| A.U6.10 | M.WEB.061, .062, .063, .074, .076 |
| A.U6.11 | read: smoke SCR; include M.WEB.073 |
| A.U6.12 | read: CI TOOL |
| A.U6.13 | M.WEB.052, .058, .059; its `js/` comments superseded (M.WEB.012) or dropped with the site (M.WEB.040) |
| A.U6.15 | read: TSC check; the WEB end state is literal-free |
| A.U6.16 | M.WEB.005, .006, .055; corpus and pytest TSC |
| A.U6.17 | M.WEB.004, .005, .041, .060, .063; tags/generator other clusters |
| A.U6.18 | read: `submitLabel` rendered (holds) |
| A.U6.19 | M.WEB.004, .006, .012 |
| A.U6.20 | M.WEB.004, .012, .014 |
| A.U6.21 | read: no website change |
| A.U6.22 | M.WEB.045 (`MemFree` sample); GEN |
| A.U6.23 | M.WEB.045 (`ResetReason` sample); GEN |
| A.U6.24 | read: `path` resolves (M.WEB.020) |
| A.U6.25 | read: M.WEB.020, .043 |
| A.U6.27 | M.WEB.004, .006 |
| A.U6.28 | M.WEB.004, .006, .014, .041, .052 |
| A.U6.29 | M.WEB.004, .006, .014, .041, .052 |
| A.U6.30 | M.WEB.004, .006, .041, .052 (hint = tag description) |
| A.U7.01 | read: SPEC |
| A.U7.02 | read: layout used by M.WEB.077 |
| A.U7.10 | M.WEB.070, .073, .074, .077 |
| A.U7.20 | M.WEB.071; helper SCR; used by M.WEB.062 |
| A.U7.21 | M.WEB.061, .062, .075 |
| A.U7.23 | read: TSC (Gaps item 7) |
| A.U8.01 | read: SPEC |
| A.U8.02 | read: TSC scan covers `js/`/`tests_js/` |
| A.U8.04 | M.WEB.002 |
| A.U8.18 | read: `js/render.js` reads the interval (M.WEB.020); the smoke SCR |
| A.U8.21 | M.WEB.051, .054, .061, .062, .063; the mock-latency half dropped (M.WEB.040: A.U23.29 removes the site) |
| A.U9.01 | read |
| A.U9.03 | M.WEB.041, .052 |



Gap pass G2 rows (2026-10-01; `GAPS_G2.md` lists each item and its source):

| action ID / gap item | merged into M-ID / dropped (reason) |
|---|---|
| M_SCR gap 1(a) (twin `MICROPYPATH` site swap; re-entrant, inherited port lock) | M.WEB.061, .078, .082 (amended) |
| M_SCR gap 1(b) (`lint:html:built` command) | M.WEB.071 (amended) |
| M_SCR gap 1(c) (JS freshness stamp path) | carried as found: M.WEB.050 |
| M_SRC_SENS GAP-12 (`Calibrate` dispatch toggle without `defaultValue`) | carried as found: M.WEB.004, .014, .054 |
| M_GEN gap 10 (`js/`, `tests_js/` blast of M_GEN's changes) | carried as found: every A-ID named has its M_WEB row (A.U6.05-.07, .17, .19, .27-.29; A.U23.12, .16, .17, .20, .22, .23, .42, .43, .49; A.U32.06; A.S0930.20) |
| M_TEST_UNIT GAP-U11 (stager separators) | not WEB's: carried by M.SCR.019 |
| M_WEB gap 1 (CLUSTERS.md naming `mockdata/` etc.) | carried as found: M.WEB.045, .073, .074; the CLUSTERS.md line is the lead's |
| AC_NOTES 40 (six `tests_js` files read in full against M.WEB.052-.059) | see `GAPS_G2.md` (end-state check result) |
| AC_NOTES 41 (GEN Q1/Q2 firm) | Owner-questions text amended (OR132) |
| A.U8.15 | M.WEB.074 (`:31` `@tunable l0.vitest_test_timeout_ms` tag; AC3 S-12; lands with M.WEB.074's U28, its Part N row with it per M.SPEC.156) |
| AC3 O-01 | M.WEB.052 (accepted `LightCmdLED` cases advance the mock clock past `T`) |
| AC3 O-02 | M.WEB.052 (`:273-275`, `:287-288`, `:296` comments) |
| AC3 O-03 | M.WEB.052 (`:316`, `:325-327`, `:336`, `:372` titles and comments) |
| AC3 O-04 | M.WEB.052 (fixture `:5-135`/`:137-153`; restore `:403`) |
| AC3 O-05 | M.WEB.053 (`:242-246` goes, `:248-252` stays; `:205-213`; `:2-3` comment) |
| AC3 O-06 | M.WEB.054 (`:323` → `MeasInterval`) |
| AC3 O-07 | M.WEB.054 ("Found while merging": `:995` expects "Internal server error") |
| AC3 O-08 | M.WEB.054 (comments/titles `:702-704`, `:417-420`, `:458-460`, `:403-405`, `:409-410`, `:584-586`, `:679-680`, `:864`) |
| AC3 O-09 | M.WEB.058 (`:512-523` through `buildFieldGroupCard()`) |
| AC3 O-10 | M.WEB.058 (`:399` module path, `:328` title) |
| AC3 O-11 | M.WEB.059 (`main.test.js:144`) |
| AC3 O-12 | M.WEB.059 (`app.test.js` keeps the `aria-current` and HTTP-500 cases) |
| AC3 O-13 | M.WEB.057 (`:73-74`, `:107-125`, `:96-98`) |
| AC3 O-23 | M.WEB.060 (actor tag "(owner, 2026-08-24)") |

## A-C review fold (2026-10-05)

Folded per `audit/actions/FOLD_BRIEF.md` (OR136-OR143, FOLD_ANSWERS, `routine_merge.json` `outcome`, AC_NOTES 52).
`[fold Fnn M_FILE]` tokens name a change another fold agent adds; the lead replaces them.

| Fnn | M-ID(s) | action |
|---|---|---|
| F01 | — | none in this file |
| F02 | product end state (`HTTPDropped` description) | amended |
| F03 | M.WEB.012, .045, .058; product end state (`ConfigFaults`) | amended |
| F04 | — | none in this file |
| F05 | — | none in this file |
| F06 | — | none in this file |
| F07 | M.WEB.004, .006, .021, .053, .054, .062, .063; product end state; rules checklist | amended |
| F08 | — | none in this file |
| F09 | M.WEB.041, .052 | amended |
| F10 | — | none in this file |
| F11 | — | none in this file |
| F12 | M.WEB.014, .058 | amended (no code beyond the existing code-value button) |
| F13 | — | none in this file |
| F14 | — | none in this file |
| F15 | — | none in this file |
| F16 | — | none in this file |
| F17 | M.WEB.025, .030, .031, .059, .064 | amended |
| F18 | M.WEB.004, .006, .012, .015, .020, .053, .054, .058 | amended |
| F19 | — | none in this file |
| F20 | — | none in this file |
| F21 | — | none in this file (no change here writes a permanent tag for a reviewed decision) |
| F22 | — | none in this file |
| F23 | — | none in this file |
| F24 | — | none in this file |
| F25 | — | none in this file |
| F26 | — | none in this file |
| F27 | — | none in this file |
| F28 | — | none in this file |
| F29 | — | none in this file |
| F30 | M.WEB.045; product end state (no `IP`) | amended |
| F31 | — | none in this file |
| F32 | — | none in this file |
| F33 | — | none in this file |
