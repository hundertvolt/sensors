"""Lane X edits, part 2: Part H (exact replacements, each found exactly once)."""
import sys
from pathlib import Path

SPEC = Path(sys.argv[1])
text = SPEC.read_text(encoding="utf-8")
EDITS = []


def edit(old: str, new: str) -> None:
    EDITS.append((old, new))


# X9, X52: H.1, the accessibility baseline (its own paragraph: the list above it is the 2026-08-21 brief's).
edit(
    """mount on startup → served via Microdot as gzip-compressed HTML (A.9).

**Predecessor**:""",
    """mount on startup → served via Microdot as gzip-compressed HTML (A.9).

**Accessibility baseline** (agent, 2026-09-27; owner-reviewed, 2026-10-01): unique ids, every label
bound to its control, the closed drawer inert with focus handled, WCAG 2.1 AA contrast in both
themes — text and status colours 4.5:1 on every background they sit on, control borders 3:1
through `--color-control-border`, pinned by `tests_scripts/test_website_tokens.py` — and reduced
motion honoured (the drawer's transition off); `color-scheme: light dark` lets native controls
follow the theme. The baseline is checked, not stated: `tests_js/accessibility.test.js` (pure DOM
rules in `tests_js/_a11y_checks.js`) runs the real `html/index.html` shell through `startApp`
against the composed mock for every device and every section — unique ids, every `label[for]` and
`aria-labelledby` naming a real element, a name on every input, select and button,
`autocomplete="new-password"` on every masked input, and the drawer inert when closed, focus on its
first link when opened and back on the hamburger when closed; three fixture cases prove each rule
bites.

**Predecessor**:""",
)

# X10, X34 (shell), the shared isRecord(): H.2's module map.
edit(
    """**JS modules**: `app.js` (prototype-only: the device manifest, the mock install), `main.js` (real
production entry — no mock, staged as `app.js` in the real build), `definitions.js` (loader +
validator, no DOM), `field-format.js` (pure formatting, split so Node-context tests can reuse it
without DOM types, H.8.1), `render.js` (controller, delegates DOM to `templates.js`),""",
    """**JS modules**: `app.js` (prototype-only: the device manifest, the mock install), `main.js` (real
production entry — no mock, staged as `app.js` in the real build), `shell.js` (the one page shell
both entries start: the nav, section switching with `#<key>` history, the device watch, one stop
handle; `startShell()`, `historyOf()`, `visibilityOf()`), `definitions.js` (loader + validator, no
DOM; it also exports the shared plain-object check `isRecord()`), `api-contract.js` (the wire facts
mirrored from `src/`, G.2, imported by the mock and the production modules), `field-format.js` (pure
formatting, split so Node-context tests can reuse it without DOM types, H.8.1), `render.js`
(controller, delegates DOM to `templates.js`),""",
)

# X11: H.2's build-script paragraph.
edit(
    """**`scripts/build_website.sh <device>`** generates the device's definitions from
`devices/<device>.toml` (H.5) and stages its real site: `index.html` (with
`style.css` and `definitions.json` inlined, H.7), the production `js/` modules concatenated into
one `js/app.js` bundle, `main.js` renamed `app.js`. Staging the production entry under the name
`app.js` means `index.html`'s import path never needs a build-time rewrite. `js/mock-server.js` is
deliberately never staged at all — its `fetch` patching has no business near production. That same
path also stays identical under `npm run preview`, which serves the repo layout where `js/app.js` is
the prototype-only entry file. Cross-checked against `html/`/`js/`'s real contents by
`tests_scripts/test_build_website_sh.py`. `scripts/build_device_websites.sh` builds every device's
site into `build/generated_html/<device>/`.""",
    """**`scripts/build_website.sh [--stage-only] <device> [output]`** generates the device's
definitions from `devices/<device>.toml` (H.5) and stages its real site through
`scripts/_stage_website.py` (CPython stdlib only): `index.html` with the stylesheet, the icon and
`definitions.json` inlined (H.7), and `js/main.js`'s import closure bundled into one `js/app.js` (a
three-line banner naming the derived order, then each module under `// ---- js/<file> ----`);
`--stage-only` stages into `output` and freezes nothing. Staging the production entry under the
name `app.js` means `index.html`'s import path never needs a build-time rewrite.
`js/mock-server.js` is deliberately never staged at all — its `fetch` patching has no business near
production. That same path also stays identical under `npm run preview`, which serves the repo
layout where `js/app.js` is the prototype-only entry file. The drift rule: every file under `html/`
and `js/` is `index.html`, a file it links, or a module of `js/main.js`'s or `js/app.js`'s import
closure, else the build fails; it and every other refusal are pinned by
`tests_scripts/test_stage_website.py`. `scripts/build_device_websites.sh [--stage-only] [out_root]`
builds every device's site into `build/generated_html/<device>/`, or with `--stage-only` stages
each page and bundle into `build/staged_html/<device>/`.""",
)

# X12: H.2's splitting rule.
edit(
    """(`field-format.js`) must never be *re-exported*. Concatenation order is fixed so every file follows
the local files it imports from, which matters only for the handful of top-level `const`s
(`DEFAULT_TIMEOUT_MS`/`pollManager`, `SUPPORTED_SCHEMA_MAJOR`, `MAX_DECIMALS`) since function and
class declarations hoist anyway; `scripts/build_website.sh` re-checks that mechanically on every build. **`index.html`'s inline bootstrap `<script
type="module">`**""",
    """(`field-format.js`) must never be *re-exported*. The order is derived, a depth-first post-order
from `js/main.js` that puts each module after the ones it imports, which matters only for the
handful of top-level `const`s (`DEFAULT_TIMEOUT_MS`/`pollManager`, `SUPPORTED_SCHEMA_MAJOR`,
`MAX_DECIMALS`) since function and class declarations hoist anyway. The stager refuses, naming file
and line, every import outside the one-line `import { a, b } from "./x.js";` form (multi-line,
namespace, default, bare, dynamic, `import.meta`, a non-relative specifier), an import of a missing
module, a default export, a re-export, an import cycle, a top-level name declared twice across the
bundle (exported or not) and a top-level destructuring declaration; it also checks the inline
bootstrap's element ids against `index.html` and its `startApp` keys against `js/main.js`'s JSDoc.
**`index.html`'s inline bootstrap `<script type="module">`**""",
)

# H.3's mechanics layer names the shell beside the other controllers.
edit(
    """  `poll-manager.js`/`mock-server.js`/`definitions.js` (pure) and the non-presentational parts of
  `render.js`/`nav.js`. None build DOM elements.""",
    """  `poll-manager.js`/`mock-server.js`/`definitions.js` (pure) and the non-presentational parts of
  `render.js`/`nav.js`/`shell.js`. None build DOM elements.""",
)

# X13, X39, X53: H.3's contract, the in-place refresh, the template API and the guard.
edit(
    """`[data-apply-status]` (written only by the controller; appearance decided entirely by CSS),
`.apply-button`, `[data-section-key]` (nav). Controllers only ever set the semantic
`data-apply-status` value, never a color/class directly. **In-place refresh only ever touches a
number/string field's caption** — a toggle/enum field's round-trip needs a genuine full remount
(a nav-drawer click), never an in-place poll.""",
    """`[data-apply-status]` (written only by the controller; its appearance set entirely by CSS),
`.apply-button`, `[data-section-key]` (nav), `[data-clear-for]` (a field's Clear button). The
controllers (`render.js`, `nav.js`, `shell.js` and the two entries) write only four dataset hooks,
each a semantic value whose look CSS sets — `data-apply-status`, `data-shown` (the section banner,
the field warning), `data-nav-open` (the app shell) and `data-source-state` (`"unavailable"` on a
card whose source sent the unavailable marker) — never a color/class directly; `.hidden` stays a
templates-only utility. The templates write the rest: ids `field-<group index>-<field index>` and
the span label `<id>-label`, a toggle's `data-value` (`true`/`false`/`unset`, an unset one showing
"—" with `aria-pressed="mixed"`), `p.field-warning`, `button.field-value.code-value[aria-expanded]`
with its `p.code-description`, `[data-code-tone]` with `.code-number`, `button.history-entry-num`,
`.errcount-module-list[data-filter]`, `[data-rollup="nodata"]` and an errcount row's `data-worst`
(`E`/`W`/`N`/`none`, the row's one severity). **Each poll updates every card in place** — values,
captions, toggles, selects and the errcount card, through `updateFieldGroupValues()`/
`updateErrcountGroup()`, keeping the nodes and the focus; after an Apply a toggle or enum takes the
baseline the post-write GET reports.

The template API, `js/templates.js`: `buildErrcountGroup(group, errcount|null)`,
`buildFieldGroupCard(group, currentValues, groupIndex, display)`, `buildNavDrawer(defs, drawerEl)`,
`buildSectionShell(section, mainEl)`, `resetControl(wrapper, field, value)`,
`updateErrcountGroup(card, group, errcount|null)` and `updateFieldGroupValues(card, group,
currentValues, display)`, with `CardDisplay = {deviceNowS, defaultDecimals?, isUnavailable(field)}`.
The controller `js/render.js` exports `showBanner`, `hideBanner` and `renderSection(defs, section,
mainEl, context = {})`; the shell `js/shell.js` holds the `DeviceClock`; the request path
`js/poll-manager.js` exports `pollManager.request(url, init, timeoutMs, signal)` and
`startPolling(pollOnce, intervalMs, {visibility?, onError?, stopAfterSuccess?})` with the
`Visibility` typedef. The split is guarded: `tests_scripts/test_website_layering.py` fails on an
element built, or a class or style written, outside `templates.js`, `document` read outside the
entries, a controller writing any other `data-*` hook, an unescaped key selector, or a dropped HTML
sink rule (H.4), each rule biting on a planted copy; it is text-based, so an aliased or computed
call evades it.""",
)

# X57: H.4 Page model, the section history.
edit(
    """| Page model | Single-page shell, JS-driven view switching | One HTML skeleton; menu swaps sections via JS, no reload — makes the poll-manager's single-active-poll rule trivial. |""",
    """| Page model | Single-page shell, JS-driven view switching | One HTML skeleton; menu swaps sections via JS, no reload — makes the poll-manager's single-active-poll rule trivial. Each menu selection is a `#<key>` history entry, so Back and Forward walk the sections and a `#<key>` URL opens its section (owner, 2026-10-01, asked about "The website meets an accessibility baseline": 'I want "back" to move backwards through the sensor subpages openend through the menu as well (actually the most intuitive way)'). |""",
)

# X31: H.4 Poll coordination (its first sentence kept word for word).
edit(
    """by design; every fetch has a shared `AbortController` timeout — `DEFAULT_TIMEOUT_MS = 15000`, see the row below for why that exact value. The poll interval""",
    """by design; every request, the definitions fetch at startup included, goes through the one queue (`pollManager.request(url, init, timeoutMs, signal)`), and its shared `AbortController` timeout covers the whole request, the body read included — `DEFAULT_TIMEOUT_MS = 15000`, see the row below for why that exact value. A section that is left aborts its queued and in-flight GETs, and polling pauses while the tab is hidden. The poll interval""",
)

# X14: H.4 Rendering safety, the sink rule.
edit(
    """| Rendering safety | `textContent` only, never `innerHTML` | XSS-safe by construction. |""",
    """| Rendering safety | `textContent` only, never `innerHTML` | XSS-safe by construction: ESLint's `no-restricted-properties` refuses `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write` and `document.writeln` in `js/` and `html/` (`tests_js/` exempt), and `tests_scripts/test_website_layering.py` fails when that rule is dropped. |""",
)

# X54: H.4 PUT/GET error handling, the Apply path's texts.
edit(
    """| A field missing from `result` shows `"Failed"`. A GET failure shows a per-section banner without clearing stale data. |""",
    """| A field missing from `result` shows `"Failed"`. A GET failure shows a per-section banner without clearing stale data. Apply first re-reads the section (one GET before the PUT, so a value another client changed is the baseline), then asks the confirmations (A.8); a declined or suppressed confirmation sends nothing and reads "Not sent - the confirmation was declined.". A GET whose body is not a JSON object raises the section banner (`"GET <url> returned no JSON object"`, or `"returned an empty body"`); a non-ok GET reads `"GET <url> failed: <descr>"`, or `"... HTTP <n>"` without a `descr`. |""",
)

# X30, X15, X36: H.4's gap row and the new divergence row.
edit(
    """| Known accepted gap | An empty string can't be set via this UI for any field | The sparse-PUT "blank = untouched" convention makes it structurally impossible (`PW`'s "open network" sentinel). Accepted (owner, 2026-08-22, `cc999c1`: leave as-is). |""",
    """| Known accepted gap | An empty string can't be set via this UI for any field but one, the DNS fallback list, whose Clear button sends `""` (owner, 2026-09-26) | The sparse-PUT "blank = untouched" convention makes it structurally impossible (`PW`'s "open network" sentinel, which `PW`'s hint states as `"" = Open network`: a number or string field's hint lists its special values). Accepted (owner, 2026-08-22, `cc999c1`: leave as-is). |
| Divergences from the legacy site | A whole-request Apply failure, which legacy only logged to the console, marks every submitted field Failed (agent, 2026-08-22; owner-reviewed, 2026-10-01). The Apply result is a left stripe on the card and on each field rather than legacy's full background recolour, keeping legacy's two levels (owner, 2026-08-21), drawn double for Invalid and Failed so the state does not rest on colour alone (agent, 2026-09-27). The legacy favicon is inlined as a 16×16 image, so a page load still opens two connections (agent, 2026-09-30; owner-reviewed, 2026-10-02). The Altitude warning `"Ignored: <label> is set."` replaces legacy's "turn off continuous measurement" note (owner, 2026-09-29). `ContMeas` shows no state until it is set (agent, 2026-09-30; owner-reviewed, 2026-10-02). Inputs clear after an Apply as legacy's did, a rejected one keeping its value (owner, 2026-09-29). A failed GET is retried with a capped back-off (agent, 2026-09-30; owner-reviewed, 2026-10-01), and a changed build reloads the page (agent, 2026-09-30; owner-reviewed, 2026-10-01). Timestamps show as an age against the device clock (owner, 2026-09-29). The error and warning numbers are clickable for their description (owner, 2026-09-29: '... don't change the current look of the website, make the codes clickable and show the description on click'), and so are the status codes, `ResetReason` first (owner, 2026-10-02, asked about "The reset-reason and boot-phase numbers": 'Good, and make the numbers clickable in the website like the errno and wrnno numbers.'). The DNS fallback list has an explicit Clear (owner, 2026-09-26). | Every behaviour that departs from the legacy pages is listed here with its decider and date. |""",
)

# X16: H.4's mock paragraph.
edit(
    """**`js/mock-server.js` mirrors every real backend quirk, not just the happy path**: `PW` masked on
every GET; SCD30's `ForceCalRef` always reports `400` on GET (a real register limitation);
`ContMeas`/`ResetVOC` never reported by GET (command-only triggers, C.5.2.1) — each dispatched
separately from the generic sparse-PUT path, covered explicitly by `tests_js/mock-server.test.js`.
One known gap: the browser has doubles only, so the mock compares a float as sent, while the board
compares the single-precision form its config file reloads as (A.8).""",
    """**`js/mock-server.js` mirrors every real backend quirk, not just the happy path**: it answers the
routes the definitions declare, from data composed per device out of `mockdata/samples.json`, and
takes its dispatch rules, masks (`mask: true`: `PW` and `HotspotPW` on every GET) and bounds from
the definitions; every envelope goes through `makeResponse()` with the server's code table, and
"Unknown error" for a code it lacks. `ForceCalRef` reads back the last applied value (400 fresh),
as `AmbPres` does, while `ContMeas`/`ResetVOC` are never reported by GET (command-only triggers,
C.5.2.1): an always-executed field is stored only where the composed data carries its key, a
dispatch field never. `UnixTime`, `WifiTS` and every measurement `TS` read the browser clock
(`Math.floor(Date.now() / 1000)`) on each GET, the measurements jitter around their samples, and
the uptimes step once per GET, saturating at `COUNTER_CAP`. Failures are injected one at a time
(`controls.nextFailure`: a network error, an HTTP status, a malformed, torn or empty body, a group
failure) and `controls.delayMs` delays every answer by a fixed time; there is no random latency and
no partial-result injection. `tests_js/mock-server.test.js` covers each. One known gap: the browser
has doubles only, so the mock compares a float at the field's `resolution` when it has one (agent,
2026-09-30), else as sent, while the board compares the single-precision form its config file
reloads as (A.8).""",
)

# X17: H.5 top level.
edit(
    """level**: `{schemaVersion, websiteVersion, device, landingSection, defaultPollIntervalMs,
sections[]}`. `websiteVersion`""",
    """level**: `{schemaVersion, websiteVersion, device, landingSection, defaultPollIntervalMs,
defaultDecimals, sections[]}`; `defaultDecimals` (H.5.1) is optional in the validator and always
emitted. `websiteVersion`""",
)

# X18, X55, X30: H.5 FieldDef metadata.
edit(
    """kind-specific metadata (`min`/`max`, `mask`, `options`, `specialValues`, `subFields`,
`onLabel`/`offLabel`, `float`, `decimals`, `path`, `byteLength` (a byte-bounded radio string,
C.7.4), `shape` (`hostLabel`, `countryCode`, `hostName` or `ipv4List`: a host label, a country code,
a host name, a list of up to three IPv4 addresses; C.7.2, C.7.4), `format` (`epoch`/`gmtimestruct`,
readonly only), `codes` (a readonly code's descriptions), `dispatch`, `alwaysExecuted`,
`defaultValue`).""",
    """kind-specific metadata (`min`/`max`, `mask`, `options`, `specialValues` (on a number or string
field listed in its hint), `subFields`, `onLabel`/`offLabel`, `float`, `decimals`, `path`,
`byteLength` (a byte-bounded radio string, C.7.4), `shape` (`hostLabel`, `countryCode`, `hostName`
or `ipv4List`: a host label, a country code, a host name, a list of up to three IPv4 addresses;
C.7.2, C.7.4; the page's hint: `hostLabel` "letters, digits and '-' only", `hostName` "a host name
(letters, digits, '-' and '.') or an IPv4 address", `ipv4List` "up to 3 IPv4 addresses,
comma-separated, no spaces", its 3 read from `src/asy_ntp_client.py`'s `_DNS_FALLBACK_MAX` by
`tests_js/templates.test.js`; `countryCode` none, its description states the form), `format`
(`epoch`/`gmtimestruct`, readonly only), `codes` (a readonly code's descriptions), `codeTones` (a
code's tone from the catalog: `good`, `neutral` or `warn`), `dispatch`, `alwaysExecuted`,
`resolution` (a number's step the device rounds to), `ignoredWhenSet` (the sibling whose non-zero
value overrides the field), `statusPath` (where `GET /status` carries the field's live value),
`clearable` (a string the page may empty with its own Clear button), `confirm` (the page asks before
it sends)). Every maintenance field of the Status section carries a `path` (`[source, field]`, set
by the generator, A.8).""",
)

# X19: H.5's defaultValue paragraph, the key being gone.
edit(
    """readable from the definitions alone. `defaultValue` marks a field's safe synthetic baseline when GET
never reports a real value — `ContMeas`'s `defaultValue` is `true` since `false` ("Off") actually
stops measurement, not a no-op (matching the legacy synthetic reference), not the toggle's naive
`false` default.""",
    """readable from the definitions alone. No field carries a synthetic baseline: an always-executed
toggle a GET never reports (`ContMeas`, which the device runs on every write) has no current value,
so the page shows no state for it — "—" with `aria-pressed="mixed"` — and sends it only once it is
set (agent, 2026-09-30; owner-reviewed, 2026-10-02).""",
)

# X20, X21: H.5.1 decimals.
edit(
    """`RangeError` ceiling), checked at generation time in `buildgen/web_tag.py` and again in
`js/definitions.js`'s `validateFieldHints()`, the two bounds pinned equal by
`tests_scripts/test_definitions_js_mirrors.py` (G.2). Unlike `path`, `decimals` applies to any
numeric field regardless of `kind` — `GainRatio` (an ordinary flat `sensors` field) carries one too.""",
    """`RangeError` ceiling), checked at generation time in `buildgen/web_tag.py` and again in
`js/definitions.js`'s `validateNumberHints()`, the two bounds pinned equal by
`tests_scripts/test_definitions_js_mirrors.py` (G.2). Unlike `path`, `decimals` applies to any
numeric field regardless of `kind` — `GainRatio` (an ordinary flat `sensors` field) carries one too.
Every numeric value the website shows takes its decimals from its source: the `@web` tag's
`decimals`, else the digits its `resolution` needs (`0.01` → 2), else the site's `defaultDecimals`
(2, Part N `web.default_decimals`); only the website rounds, the API keeps full resolution (owner,
2026-10-02, asked about "How timestamps, codes and numbers show on the website": 'Fine, and maintain
a reasonable number of digits per value (e.g. limit to 2 or 3 digits behind the decimal point, don't
print full floats). But only for the website, the API delivers full resolution. Configured in the
website config file, derived or defined from the value sourcing modules (e.g. Schema or inside the
commented configs).'). The counts the build carries (agent, 2026-10-13): SCD30 `CO2` 0 and
`Temp`/`Hum`/`WetBulb`/`DewPoint` 1, from the datasheet's repeatability (10 ppm, 0.1 °C, 0.1 %RH;
Tables 1-3), and `TempOffset` 2 from its 0.01 °C tick (Interface Description 1.4.7); BMP3XX none,
the default 2 sitting at or above the chip's resolution; SGP40's values are integers; ISL29125
keeps its own tags (0 to 4). A derived or default count lies in 0..3; a tag's explicit count
stands as its source states it.""",
)

# X56: H.5.1 generator-owned, D's status rows.
edit(
    """owning file (`SystemCmd`, `PauseTime`, `LightCmdLED`, `ResetErrors`, the Status section's own
live-readonly field lists); and the""",
    """owning file (`SystemCmd`, `PauseTime`, `LightCmdLED`, `ResetErrors`, the Status section's own
live-readonly field lists — among them the Device Clock row (`UnixTime`, which every age on the site
is computed against), the notification `TS` row "Last Cycle Time", and `ResetReason`'s description
"Why the device last restarted, as a numeric code; click it for its meaning."); and the""",
)

# X33: H.6, no invented zero.
edit(
    """wrong fails in both directions and neither is visible — a published source with no row is never
rendered at all, and a row with no published source renders a permanent, reassuring `0` from
`templates.js`'s own `?? {counter: 0}` fallback. **History""",
    """wrong fails in both directions — a published source with no row is never rendered at all, which
nothing shows, and a row with no published source reads "no data" (one whose source sent the
unavailable marker, "unavailable"), counted in the rollup's `"<n> module(s) without data"`, a line
shown only when there are some; no fallback paints a healthy zero. **History""",
)

# X40: H.6 errcount UX.
edit(
    """groups, starts collapsed to a rollup + two filter buttons, wired entirely inside `templates.js`
(no controller involvement).""",
    """groups, starts collapsed to a rollup + two filter buttons; the buttons and the rollup are wired
inside `templates.js`, and the controller only hands each poll's `errcount` to
`updateErrcountGroup()`.""",
)

# X22, X35: H.7 bundling and inlining.
edit(
    """**bundling** (seven modules concatenated into one `js/app.js`, plain text concatenation, safe since
none use default exports/dynamic imports/re-exports) and **inlining** (`style.css` and the device's
`definitions.json` embedded directly into the staged `index.html`, with `<` escaped to avoid a
literal `</script` closing the tag early) — 2 connections per page load (down from ~9),""",
    """**bundling** (`js/main.js`'s import closure, nine modules, bundled into one `js/app.js` in its
derived order, the stager refusing whatever would break their one shared scope, H.2) and
**inlining** (the stylesheet, the device's `definitions.json` with every `<` written `\\u003c` so no
literal `</script` closes its block early, and the icon as a `data:image/x-icon;base64,` link, all
embedded in the staged `index.html`) — 2 connections per page load (down from ~9),""",
)

# X23: H.8 html-validate over the staged pages.
edit(
    """for `--coverage`; **html-validate** for `html/`, **Stylelint** for CSS.""",
    """for `--coverage`; **html-validate** for `html/` and, through `npm run lint:html:built`, for every
device's staged `index.html` (`scripts/build_device_websites.sh --stage-only build/staged_html`; a
local check until CI runs it), **Stylelint** for CSS.""",
)

# X24: H.8 the loader and the agreement checks.
edit(
    """Vitest reads every device's generated definitions from `build/generated_src/definitions/` through
one loader, `tests_js/_generated_definitions.js`, which fails at import when that tree is missing or
its device set differs from `devices/*.toml`; per device it runs the validator and the renderer over
every section, and the mock PUT matrix over data composed from `mockdata/samples.json`
(deduplicated by definition, as the live one).""",
    """Vitest reads every device's generated definitions from `build/generated_src/definitions/` and its
REST reference from `build/generated_src/api/` (`API_REFERENCES`) through one loader,
`tests_js/_generated_definitions.js`, which fails at import when either tree is missing or its
device set differs from `devices/*.toml`; per device it runs the validator and the renderer over
every section, and the mock PUT matrix over data composed from `mockdata/samples.json`
(deduplicated by definition, as the live one). `tests_js/api-reference-agreement.test.js` checks
each reference's routes against the definitions, its result words against `js/api-contract.js` and
its code table against the mock's; `tests_scripts/test_js_api_mirrors.py` pins every JS copy of a
`src/` wire fact (G.2).""",
)

# X27, X25: H.8's console rule and the sink rule.
edit(
    """`no-console` bans `console.log` and friends but allows `error`/`warn`:
`js/poll-manager.js`'s "Poll failed:" is the poll loop's only failure diagnostic and is asserted
by a test, as is a live-backend test's skip warning; `scripts/*.mjs` (a CLI, where console is the
output) is exempt in its own block.""",
    """`no-console` bans `console.log` and friends but allows `error`/`warn`, the real diagnostics: a
section's failing GET shows the section's banner and is logged once per failure episode
(`js/render.js`'s `"Could not refresh <section>:"`), then retried with a capped back-off (Part N
`web.poll_backoff_max_ms`; a PUT is never retried), and a live-backend test warns when it skips;
`scripts/*.mjs` (a CLI, where console is the output) is exempt in its own block. Over the shipped
page (`js/`, `html/`), `no-restricted-properties` refuses the HTML sinks (H.4's "Rendering safety"
row).""",
)

# X26: H.8 the bootstrap's literal import.
edit(
    """`eslint-plugin-html`: `scripts/build_website.sh` relies on it importing the literal
`../js/app.js`, which resolves both under `npm run preview` and in a device build.""",
    """`eslint-plugin-html`: `scripts/_stage_website.py` checks that it imports the literal
`../js/app.js` (and its element ids and `startApp` keys, H.2), which resolves both under
`npm run preview` and in a device build.""",
)

for old, new in EDITS:
    count = text.count(old)
    if count != 1:
        sys.exit(f"found {count} times:\n{old[:300]}")
    text = text.replace(old, new)
SPEC.write_text(text, encoding="utf-8")
print(f"applied {len(EDITS)} edits")
