# Website Redesign — Plan & Definitions

Temporary planning doc for the multi-sub-session website-redesign effort, in the same spirit as
this repo's earlier `WIRING_CONTRACT.md`/`FINAL_WIRING_PLAN.md` (see README.md's "Further reading"
for that precedent): a living, updatable reference every spun-off sub-session reads first and adds
to when it settles something new, so decisions aren't re-litigated or lost between sessions. Once
this effort merges back, everything permanent here migrates into `SPECIFICATION.md` (most likely a
new Part, alongside A.9's frozen-HTML pipeline) and this file is deleted — same lifecycle as its
predecessors.

**How to use this file**: read it in full before starting a sub-session. If your session settles an
open item, a new architecture decision, or a new goal, update the relevant section here before
ending — don't leave it only in that session's own transcript. Keep entries as settled facts/current
state, not a narrated log of who asked what (matches CLAUDE.md's own documentation philosophy).

---

## 1. Purpose of the website (goals, unchanged from the project owner's brief)

- Show current measurement values.
- Show current configuration parameters.
- Set configuration parameters.
- Issue commands.
- Show system and error state / history.
- Every REST endpoint's functionality must be reachable somewhere in the GUI — not necessarily as a
  dedicated API-browser page, just reachable.

## 2. Legacy / current state (what exists today, confirmed by direct scan)

- `html_raw/{general,arzi,dev,wozi}` — per-device folders (`arzi/`, `dev/`, `wozi/`; `neu` reuses
  `arzi`'s), each with `index.html` (measurements), `sensorconfig.html`, `systemledconfig.html`;
  `general/` holds the shared `style.css`, `functions.js`, `favicon.ico`, and the one shared
  `nettimeconfig.html`. Four pages per device, cross-linked via a bottom `.links` bar. Devices
  differ only in which sensor cards/fields exist — same skeleton/JS/CSS otherwise.
- `functions.js` (113 lines, 4 functions, no framework): `updateCurrentValues()` (GET-polls one
  endpoint, keys DOM elements by `sensor_property` for multi-value responses), `putSensorCfg()`
  (PUT with a `cmd` envelope, colorizes the parent `.card` green/grey/red/lavender by
  `data.result[field]`, re-polls after 2s), `getColorForValue`/`getColorForCode`,
  `toggleButtonSwitch` (On/Off state kept in button `textContent`, not a real checkbox).
- `style.css` (98 lines): `.container` > `.group` (flexbox, `flex-wrap: wrap`) > `.card`/`.card.sub`
  nesting, fixed light-grey/white palette. **No media queries at all** — "works in light and dark"
  in practice means a fixed-light page that simply doesn't break under a dark OS theme, not real
  `prefers-color-scheme` adaptation. Whether the redesign adds real dark-mode support is still open
  (see §8).
- **Legacy REST shape (important, still targeted by `functions.js` today) differs from the new
  backend**: `/sensors/status`, `/sensors/config`, `/sensors/cmd`, `/net/config`, `/net/cmd`,
  `/led/cmd`, `/led/config`, `/system/cmd`, `/system/status`, etc. — PUT-with-`cmd`-envelope,
  `Led`-prefixed field names (`LedWarnCO2`, `LedAutoOn`, ...). This is **not** what
  `src/asy_webserver_service.py` (SPECIFICATION.md A.8) already exposes — see §4's REST-target
  decision.
- `html_stub/` (7 flat files) — deliberate "Hello world"-shaped placeholder standing in for real
  content in the refactored build (SPECIFICATION.md A.9). The gzip → `freezefs` →
  `frozen_modules/frozen_html.py` → mount-at-`/html` → Microdot `send_file(..., compressed=True)`
  pipeline (`scripts/build_frozen_html.sh`, `HTML_SRC_DIRS` env var) is already fully built and
  proven against this placeholder — the new website's build output is meant to replace `html_stub/`
  in that same pipeline, not build a new one.

## 3. Future design goals (project owner's brief, unchanged)

- No boilerplate — small HTML skeletons only, full look/content generated dynamically by JS.
- Ready for future autogeneration, alongside the planned per-variant `sensortask-*.py` generator
  (SPECIFICATION.md A.3/A.8 already note this direction).
- Same skeleton(s)/JS for every device; one definitions file (pulled by JS before rendering) defines
  layout/content/naming per device — written by hand once in this effort as the worked example, but
  shaped for later autogeneration.
- Predefined page schemes, since sensor sets differ per device.
- Full existing functionality/API coverage retained, nothing dropped.
- Stays small, lean, fully self-contained — no external dependencies at runtime.
- Polling similar to legacy in spirit, but coordinated (see §4's poll-manager decision).
- Modern nav — hamburger/three-dot menu — replacing the legacy bottom link list.
- Stable and good-looking on (ideally all) major mobile/desktop browsers, light and dark schemes.
- Build process stays exactly as today (unchanged, confirmed by the project owner): build the
  folder structure → gzip each file individually at highest compression → wrap with `freezefs` →
  include in the cross-compile/frozen-bytecode build → mount on startup → serve via Microdot as
  gzip-compressed HTML.
- Once promoted, this replaces the `html_stub/` placeholder currently wired into
  `src/sensortask_wozi.py`.

## 4. Settled architecture decisions

| Topic | Decision | Rationale / notes |
|---|---|---|
| Page model | Single-page shell, JS-driven view switching | One HTML skeleton; hamburger/three-dot menu swaps sections via JS, no page reload. Makes the poll-manager's single-active-poll rule trivial to enforce globally. |
| Definitions file | One single JSON, fetched once | Covers nav, page/field labels, units, valid ranges, special values, etc. |
| Definitions generation stage | Build-time, static JSON | A build script parses the tagged schema comments from the real `.py` source **before** `mpy-cross` strips comments, emits a static JSON frozen alongside the HTML in the same `freezefs` pipeline. Never computed/served at runtime — zero device RAM/CPU cost. |
| REST target | New `src/asy_webserver_service.py` API (SPECIFICATION.md A.8) | Six endpoints (`/measurements`, `/sensors`, `/networking`, `/system`, `/status`, `/notification`), sparse-body PUT, no `cmd` envelope, no `Led`-prefixed fields. **Not** the legacy shape §2 describes — this website assumes the refactored backend from day one. |
| Schema comment-tag scheme | Lightweight inline tag syntax | One tagged comment line per schema field (key=value-style), placed close to that field's definition in the driver's schema. Exact tag grammar/field set (label/unit/description/range/special values/category/...) is **not yet decided** — reserved for a dedicated sub-session (see §8). |
| Nav grouping | Mirrors the 6 REST endpoints 1:1 | Sections: Measurements, Sensors, Networking, System, Status, Notification. |
| History depth | Both — counts always visible, expandable to full history | Per-module counts/last-error always shown; full `PrintLogHistory` log available on demand. History size can vary — needs a pagination/truncation mechanism (open, see §8). |
| Poll coordination | One shared JS poll-manager module | Single source of truth for "is a request in flight." Enforces the project owner's explicit rule: **the measurements group and the status/config group are never polled concurrently by design** (a page only ever needs one or the other); if that ever becomes unavoidable, a new poll must wait until the pending request has resolved **and its connection has fully closed** before starting — the device has very few available sockets. |
| API reachability | No dedicated API-browser page | Every endpoint's functionality just needs to be reachable somewhere in the ordinary GUI (satisfied by the nav-mirrors-endpoints decision above) — not a Swagger-style reference/try-it tool. |
| Definitions validation | Strict — visible error state on mismatch | The JS checks the fetched definitions file's shape/version before rendering; a mismatch surfaces a visible error rather than silently rendering something broken or skipping unknown fields. |
| Landing page | Measurements page | Matches legacy's default landing page. |
| Visual/mechanics separation | Hard layering: `html/style.css` + `js/templates.js` vs. everything else | A future redesign (visual restyle, or reordering/regrouping what's on a page) must never require touching data-fetching/validation/submission code. **Standing requirement, not just this session's — see §12** for the full rule and the data-attribute contract between the two layers. |

## 5. Folder structure

New source lives in **top-level siblings** of `src/`/`tests/` (matching the repo's existing flat
convention — `html_raw/`, `html_stub/`, `ext/`, `digital_twin/` are all top-level too, not nested):

```
html/               Hand-written HTML skeleton(s) + CSS - the new real website source
html/definitions/   Per-device definitions.json (schemaVersion/device/sections - see §8) - shipped,
                     frozen alongside html/ by the same pipeline (§4's "Definitions generation stage")
js/                 Hand-written ES module JS source (poll-manager, mock backend, definitions
                     loader/validator, generic renderer, nav) - see §6
tests_js/           JS unit tests (Vitest, see §6)
mockdata/           Prototype-only mock backend fixtures (session 2) - NOT shipped, NOT part of the
                     frozen-HTML pipeline; consumed only by js/mock-server.js for local viewing
                     until a real backend/digital-twin exists (§7)
```

`package.json`/`package-lock.json` at repo root (dev-tooling only, `node_modules/` gitignored) —
mirrors `pyproject.toml`'s existing role: shipped code stays hand-written plain files, never
restructured into a build/bundle output. `html_raw/` (legacy, still deployed) and `html_stub/`
(placeholder, still wired into `src/sensortask_wozi.py` until this effort's output replaces it) are
untouched by this restructuring. `npm run preview` (added session 2) serves the repo root via
`python3 -m http.server 8000` — open `http://localhost:8000/html/index.html?device=wozi` (or
`?device=dev`) to click through the live prototype locally; see §10 item 2.

**Session 1 status: done, merged.** All three folders, `package.json`/`package-lock.json`, and
every tool config (§6) landed via `claude/website-s1-folder-ci` (PR #43, merged into this base
branch) — each folder holding only trivial "Hello world"-shaped placeholder content (mirroring
`html_stub/`'s own bootstrap role): `html/index.html`+`style.css`, one `js/hello.js` ES module, one
`tests_js/hello.test.js` Vitest browser-mode test. Confirmed via a real GitHub Actions run on the
PR (not just local): `web-changes`/`web-lint-and-typecheck`/`web-unit-tests` all green, existing
Python jobs unaffected. Manual local-trigger instructions for the whole web-CI tier now live in
**README.md's "Website tooling (JS/HTML/CSS)" section** (`npm ci` + `npm run lint`/`typecheck`/
`lint:html`/`lint:css`/`test`) — the JS-side equivalent of that same README's existing "Code
quality tooling" section for Python. The `js/hello.js`/`tests_js/hello.test.js` bootstrap placeholder
was removed in session 2 once real content replaced it (its job — proving the pipeline red→green —
was already done and recorded here).

## 6. CI / tooling stack

Mirrors the Python side's actual roles (ruff/mypy/pytest), not just "any linter/tester":

| Python role | JS/HTML/CSS equivalent | Notes |
|---|---|---|
| ruff (lint) | **ESLint** | Chosen over Biome for ecosystem maturity/rule coverage. |
| mypy (type-check) | **TypeScript `checkJS` mode** (`tsc --noEmit`) reading JSDoc annotations in plain `.js` | Pure dev-time checker, zero transpilation — shipped JS stays exactly as written, same "dev-tooling only" split as `pyproject.toml`. |
| MicroPython Unix-port interpreter for tests (real environment, not CPython+stubs) | **Vitest in real-browser mode** (Playwright provider, against Chromium) | Deliberately not jsdom — same "real engine over a DOM/interpreter shim" principle SPECIFICATION.md Part E.1 already argues for the Python side. |
| — | **html-validate** for `html/`'s skeleton(s); **Stylelint** for the CSS | Lightweight npm packages, no JVM dependency (ruled out the W3C Nu Html Checker for that reason). |

**CI mechanism**: extend the existing single `.github/workflows/ci.yml` (not a new workflow file)
with a `changes`-detection job (e.g. via `dorny/paths-filter`) whose output gates both the existing
Python jobs and the new web-CI jobs via `if:` conditions. The workflow itself always triggers and
always reports a status for every job (irrelevant jobs just skip) — deliberately not two separate
workflow files with independent trigger-level `paths:` filters, which can leave a PR stuck on a
required status check that never fires because the whole workflow never triggered. Python CI keeps
running only against its existing paths (`src/`, `tests/`, `digital_twin/`, `pyproject.toml`,
`scripts/`, `toolchain/`); web CI runs only against `html/`, `js/`, `tests_js/`, plus its own config
files (`package.json`, ESLint/TS/Vitest/html-validate/Stylelint configs).

**Implemented in session 1** (`claude/website-s1-folder-ci`) — confirmed against current package
docs, not assumed from training memory, per this repo's standing "check current docs" practice:
Vitest 4 split its browser-mode provider out of `@vitest/browser` into a separate
**`@vitest/browser-playwright`** package (`playwright()` provider function passed to
`test.browser.provider`, plus the `playwright` package itself as its peer dependency) — the
settled *decision* (real-browser mode via Playwright + Chromium, not jsdom) is unchanged, only the
package name that implements it. `typescript` is now major version 7 (the Go-based rewrite);
`tsc --noEmit` with `checkJs`/`allowJs` works the same as before. Root `.nvmrc` pins Node 22,
read by `actions/setup-node`'s `node-version-file` in CI. The three new CI jobs are named
`web-changes` (the `dorny/paths-filter` gate), `web-lint-and-typecheck` (ESLint + `tsc --noEmit` +
html-validate + Stylelint), and `web-unit-tests` (Vitest browser mode, `needs` both prior jobs).
`vitest.config.js` conditionally passes `launchOptions.executablePath` pointing at this Claude Code
environment's pre-installed `/opt/pw-browsers/chromium` when that path exists (so local runs in
*this* sandbox don't hit a Playwright browser-revision mismatch and don't re-download); real CI
runners have no such path, so `web-unit-tests` instead runs `npx playwright install --with-deps
chromium` before the test step. All three new jobs were proven red (run against no `html/`/`js/`/
`tests_js/` content at all — every one of ESLint/tsc/html-validate/Stylelint/Vitest fails
appropriately) then green (against the trivial placeholder content) locally before pushing.

## 7. Digital twin integration (future requirement, not yet actionable)

Once the website prototype (built from the decisions above) is functionally complete, it must be
wired into `digital_twin/` alongside every sensor/module that already has a real REST/API
connection there — the same generalized "any new module joins the twin once it can complete a
real, observable chain" rule SPECIFICATION.md A.10 already states for drivers and common modules,
applied here to the website itself. This must stay a **living** integration: whenever a new
sensor/module gains an API connection in the twin afterward, the website's own twin wiring has to
be kept in step automatically — via the same definitions-file mechanism (new nav sections/fields
just appear from the regenerated definitions JSON), not a hand-maintained parallel list. No website
prototype exists yet, so this isn't actionable yet — tracked here so it isn't forgotten once one
does.

## 8. Open items — reserved for dedicated future sub-sessions

**Resolved by session 2** (`claude/website-s2-layout-prototype`, interactively with the project
owner — see §10 item 2's own notes for the concrete prototype these produced):

- **Definitions JSON's actual schema/shape** — settled and built. One JSON per device
  (`html/definitions/<device>.json`), top-level `{schemaVersion, device, landingSection,
  defaultPollIntervalMs, sections[]}`. Each `section` mirrors one of the six REST endpoints
  (`key` matches the endpoint name, `rest: {get, put?}`, `pollGroup: "live"|"settings"|"none"`) and
  holds `groups[]` — normally a `FieldGroup` (`key`, `label`, optional `submit`/`submitLabel`,
  `fields[]`), except Status's error section which is a distinct `ErrcountGroup`
  (`kind: "errcount"`, `modules[]`) since its shape (per-module counter + optional history) doesn't
  fit the field-list model. Each `FieldDef` has a `kind` (`readonly | number | string | enum |
  toggle | composite`) plus kind-specific metadata (`min`/`max`, `minLength`/`maxLength`, `mask`,
  `options`, `specialValues`, `subFields`, `onLabel`/`offLabel`). `js/definitions.js` both documents
  this shape (JSDoc typedefs) and strictly validates it (§4's "Definitions validation" decision) —
  a `schemaVersion` major-version mismatch or a missing required field surfaces a visible error
  banner rather than a silent partial render. See `html/definitions/wozi.json` and
  `html/definitions/dev.json` for two fully worked, real examples (wozi's SCD30/SGP40/BMP388 vs.
  dev's SCD30/SGP40/SHTC3/MPRLS/ISL29125 — deliberately different sensor sets, field kinds, and
  value ranges, to prove the schema/renderer generalize rather than fitting only wozi).
- **Real dark-mode support** — settled: automatic only, via `prefers-color-scheme`. No manual
  toggle/override and no stored preference — CSS custom-property tokens on `:root`, redefined
  under `@media (prefers-color-scheme: dark)` (`html/style.css`). Chosen over a manual toggle to
  keep the page "small, lean, fully self-contained" (§3) with zero added JS/state for it.
- **Visual/interaction design specifics** — settled interactively (project owner picked the
  recommended option at each `AskUserQuestion` round): modernized flat cards (legacy's
  `.card`/`.card.sub` nesting kept as the mental model, refreshed with a soft border/shadow instead
  of flat grey fill, real light/dark tokens); a slide-in drawer nav opened by a hamburger button,
  listing the six section links plus the device name, with no other global actions in it; single-
  page shell with JS view-switching (matches §4's already-settled decision, now built:
  `js/nav.js`/`js/render.js`). A per-field-result "Valid/Unchanged/Invalid/Failed" outcome (same
  four states the real backend's `PUT` envelope reports, `api_response.py`) shows as a left accent
  stripe + inline per-field text, not legacy's whole-card background flash — at **two** levels: the
  group card as a whole (worst status across the group) and, restored to match legacy's own
  per-field granularity (session 3 follow-up 3, §10 item 3), each individual field's own box, colored
  by its own result via a new `data-field-wrapper-key` hook.
- **History pagination/truncation mechanism** — settled: **no pagination/truncation**. The project
  owner's own expectation is that a module's error history realistically stays well under 20
  entries, so building chunked "show more" loading would be overkill for the real data volume;
  clicking a module's error-count tile just expands and renders its full `history` array as-is
  (`js/render.js`'s `renderErrcountGroup()`). Counts stay always-visible per §4; history is
  fetch-once-per-poll (it rides along in the same `/status` response), not a separate paginated
  endpoint — A.8's REST shape has no such endpoint to page through in the first place.
- **Per-device page-scheme variation mechanism** — resolved by construction: the definitions file
  itself *is* the per-device page scheme (§4's decision already implied this; session 2 is the
  first time it's actually built two ways). `js/render.js`/`js/nav.js` contain zero device-specific
  branching — every card, field, and nav entry comes from the fetched `definitions.json`. wozi's
  and dev's prototypes are the same `html/index.html` + same `js/` tree, pointed at different
  definitions files (see §10 item 2 below for how the prototype picks one locally).
- **Error/history endpoint-to-UI field mapping** — resolved: the Status section's `errcount` group
  lists the module keys it expects (`{key, label}`, one entry per registered module +
  `CFGMGR_<name>` config-store instances + the webserver's own `WEBSERVER` entry, matching A.8's
  `_build_errcount()` shape exactly), and looks each one up directly in `/status`'s `errcount[key]`
  response at render time — no transformation beyond that direct key lookup. **Corrected in a
  session-2 follow-up audit** (before this branch merged): the first cut of both device definitions
  files only listed 5 of wozi's real ~17 registered error sources (`src/sensortask_wozi.py`'s
  `_collect_error_sources()` — every module *and* every `ConfigManager` instance, not just the three
  sensor readers) and included one name that isn't real (`CFGMGR_SCD30` — SCD30 persists to the
  sensor's own NVM, not a `ConfigManager`, so it has no config-store error source at all). Both
  `html/definitions/{wozi,dev}.json` now list the full real set (`WIFI`, `CFGMGR_WIFI`, `DNSSRV`,
  `NTP`, `CFGMGR_NTP`, `FRAM`, `SYSTEM`, `CFGMGR_SYSTEM`, plus each sensor and, except SCD30, its own
  `CFGMGR_<name>`, plus `NEOPIXEL`/`NOTIFY`/`CFGMGR_NOTIFY`/`WEBSERVER`). dev.json's own SHTC3/MPRLS/
  ISL29125 aren't promoted to `src/` yet, so their `CFGMGR_<name>` entries are a projection from the
  same pattern every promoted sensor already follows, not confirmed against real code — flagged here
  for whichever session first promotes them.
- **Error-history entry shape** — the same follow-up audit found the prototype had invented a shape
  (`{TS, ErrType: "I2CTimeout", ErrNum}`) that doesn't exist anywhere on the real device:
  `src/print_log.py`'s `get_log()` / `src/asy_webserver_service.py`'s `_shape_errcount_entry()`
  return `{"num": <raw errno>, "type": "N"|"E"|"W"}` per slot, always a fixed `history_length`-long
  list (never shorter — a healthy module's history is all `"N"` placeholders, not an empty array),
  with **no per-entry timestamp anywhere in the system**. Resolved interactively with the project
  owner: `type` is never rendered as text at all — its only job is to color `num` (green/yellow/red
  for no-error/warning/error), the same "controller/template sets a semantic value, CSS alone
  decides what it looks like" contract §12 already uses for `data-apply-status`. Implemented as
  `js/templates.js`'s `buildErrcountGroup()` setting `data-err-type` per entry, styled by
  `html/style.css`'s `.history-entry[data-err-type]` rules; `js/definitions.js`'s `MockDeviceData`
  typedef and both mock fixture files now use the real shape.
- **Errcount rollup/collapse UX** — the same `.card` shell every other field group uses (project
  owner, session 2 follow-up: the rollup/buttons were originally floating loose on the page,
  unlike every other displayed value), starting fully collapsed to just a rollup ("N modules with
  errors" / "M modules with warnings") plus two filter buttons ("Show flagged"/"Show all") — a
  device can have 15+ registered modules, and showing every one by default was too much vertical
  space for a page a visitor mostly just needs to glance at. Once a module row is revealed by
  either filter, its history is shown immediately alongside it — no further per-row click needed
  (project owner: a collapsed history on an already-revealed, already-flagged module read as
  broken, not as a second layer of hiding). Implemented in `js/templates.js`'s
  `buildErrcountGroup()`.
- **Other invented-vs-real mismatches found by the same audit, corrected**: `/status.networking`
  was missing `Mode`/`Connected`/`IP`/`NtpLastSync` (real fields per
  `sensortask_wozi.py`'s `_networking_status()`); `LocalTime`/`UtcTime` are real
  `{year, month, mday, hour, minute, second, weekday}` dicts (`_gmtimestruct_to_dict()`), not
  pre-formatted strings — `formatFieldValue()` now special-cases the (already-reserved but
  previously unimplemented) `field.format: "gmtimestruct"`; `BootSignature` is a real `int | None`
  (opaque, meaningful only by comparing across polls), not a descriptive string like `"POWERON"` —
  the mock fixtures invented that; SGP40's `"ticks"` unit was on the wrong field (`VOC` is a
  dimensionless index, `Raw` is the actual tick count); dev.json's `InterruptAutoClear` declared
  `min: 0` while also declaring a `-1` special value, self-contradictory — the real legacy range is
  `-1`–3600000. dev.json's unprefixed sensor-config field names for SHTC3/MPRLS/ISL29125 were
  checked against this same audit and are **not** a bug — they intentionally follow `src/`'s
  sparse-PUT contract per this file's own already-settled REST-target decision (§4), not the legacy
  `modules/sensortask-dev.py` `cmd`-envelope/prefixed-field shape those sensors are actually served
  under today.

**Still open / deferred to a future sub-session:**

- **Exact schema comment-tag grammar** — §11 below is a first concrete *sketch* of the tag syntax
  and worked examples against the real `src/asy_scd30_driver.py`/`asy_bmp3xx_driver.py`/
  `asy_sgp40_driver.py` schemas, written during session 2 per its own scope (documentation only,
  no parser). It is a proposal to start from, **not** a final decision — per the original plan,
  actually settling it is still reserved for a dedicated session, ideally paired with whichever
  driver session first touches a schema definition under this convention, since that session will
  be the first to feel where the sketch is awkward in practice.
- **Build pipeline wiring** — how `scripts/build_frozen_html.sh`/`HTML_SRC_DIRS` picks up `html/`
  (and the JS build/definitions-generation step) instead of/alongside `html_stub/`; whether the
  existing mechanism already covers this or needs extending. Session 4's job (§10).

## 9. Sub-session working process

Each spun-off sub-session should follow CLAUDE.md's existing "Step-session workflow" working
agreement (refine scope → ask clarifying questions → tests first (TDD) → implementation →
more tests/coverage → stop and report before merging/starting the next unit) — this file supplies
the settled architecture/goals that step (1)'s scope-refinement can build on directly instead of
re-deriving, and step (2) only needs to raise what's still genuinely open (§8), not the questions
already answered in §4.

## 10. Sub-session breakdown (execution order)

**Standing instructions for every sub-session below** (in addition to §9's step-session workflow):
start with a detailed description of what it will do; ask 10 clarifying questions before starting
actual work; update this file before ending if anything settled changes or a new decision is made,
so the next sub-session reads current state, not stale state; never touch `src/` files; do not
build the schema-comment autocreation tooling itself in this effort — only prepare hand-written
example definitions file(s) shaped as if they were auto-creatable.

**Branching/PR requirement — applies to every sub-session, including the sessions spun off from
each of the five below:** each sub-session branches off **this base session's branch**,
`claude/sensor-website-redesign-w2juw6` (PR #42) — **never off `main`**. Its own pull request
targets `claude/sensor-website-redesign-w2juw6` as the base, not `main`; that PR only merges into
`main` once the whole multi-session effort is complete. Each session in the chain (2 off 1's
branch, 3 off 2's, etc.) follows the same rule against its immediate parent session's branch, not
against `main` or against this base branch directly, keeping the sessions stacked in execution
order.

1. **Folder structure + CI. Done** — `claude/website-s1-folder-ci` (PR #43), see §5/§6 for what landed.
   Created `html/`, `js/`, `tests_js/`, root `package.json`/tool configs
   (ESLint, TypeScript `checkJS`, Vitest+Playwright, html-validate, Stylelint), and the
   `changes`-gated web-CI tier in `ci.yml` (§6). Included trivial placeholder content (mirroring
   `html_stub/`'s own "Hello world"-shaped bootstrap role) so the pipeline was proven red→green
   before any real content existed, not just configured and left unexercised.
2. **Layout & functionality definition, with a locally-viewable prototype. Done** —
   `claude/website-s2-layout-prototype`. Detailed page/section
   design (nav, per-endpoint sections, history UI, ...); resolve the still-open §8 decisions that
   naturally belong here — real dark-mode support or not, the history pagination/truncation
   mechanism, and the definitions JSON's concrete schema; then hand-write example definitions
   file(s) against static/mocked fixture data (no live backend yet) so the resulting pages are
   genuinely open-able and clickable in a local browser. **Cover two differing devices** (e.g.
   wozi's real sensor set + a second device's very different one), not just wozi, to actually prove
   the "one skeleton/JS, content from definitions file" claim generalizes rather than hiding
   wozi-specific assumptions. Also sketch — documentation only, not implemented — what the eventual
   schema-comment tag grammar in driver files would need to look like to auto-produce this
   definitions shape later, keeping the example honestly "auto-creatable in principle" without
   building that parser.

   **This session's process must be genuinely interactive, beyond §9/§10's standard upfront
   10-question gate.** Every §8 item this session resolves (dark mode extent, hamburger/three-dot
   menu concrete behavior, card vs. other visual treatment, history pagination/truncation UX, color/
   typography/layout choices, and any other decision that's a matter of taste/preference rather than
   something derivable from §1–§4's already-settled architecture) is a design-taste call the project
   owner should weigh in on, not something this session decides unilaterally and only reports
   afterward. Concretely: the initial 10 questions should surface whatever blocks starting, but as
   each visual/UX decision point is actually reached during the design work, pause and ask again —
   present 2–4 concrete options (sketches/descriptions of each, with tradeoffs) via `AskUserQuestion`
   rather than batching every open question into the start or silently picking based on internal
   judgment. Iterate on the prototype with the project owner's feedback before treating a layout/
   functionality decision as settled enough to write into this file or hand off to session 3.

   **Session 2 status: done.** Every design-taste decision was resolved interactively via
   `AskUserQuestion` before being built (device choice, prototype-only multi-device UX, mock-data
   liveness, history-fixture variety, dark-mode extent, nav-menu shape, card visual treatment —
   the project owner picked the recommended option at every round); the history
   pagination/truncation question came back with real information (error history realistically
   stays under 20 entries) that settled §8's item outright rather than needing a UX mechanism at
   all. All §8 resolutions are recorded above; §11 below is the schema-comment tag grammar sketch.
   Built: `html/index.html` + `html/style.css` (single-page shell, light/dark tokens, slide-in nav
   drawer, modernized cards), `js/poll-manager.js` (single-flight request queue enforcing §4's
   measurements/status-vs-settings mutual exclusion), `js/definitions.js` (loader + strict
   validator + JSDoc type definitions for the whole schema), `js/render.js` (generic section/group/
   field renderer — zero device-specific code, delegates DOM building to `js/templates.js`),
   `js/templates.js` (the DOM/markup-building layer extracted per §12's pre-merge amendment —
   owns every element/class/order choice `render.js`/`nav.js` used to build inline), `js/nav.js`
   (drawer wiring), `js/app.js` (entry point, `?device=` prototype switch), `js/mock-server.js`
   (fetch-intercepting fake backend, answers the same six REST paths/shapes A.8 documents,
   validates PUTs against the definitions' own min/max/enum/length constraints, jitters live
   values so polling visibly does something — explicitly a placeholder for session 5's real
   digital-twin backend, not a permanent fixture), `html/definitions/wozi.json` +
   `html/definitions/dev.json` (the two worked example definitions files), `mockdata/wozi.json` +
   `mockdata/dev.json` (their fixture data, deliberately varied error histories per device). 45
   Vitest unit tests across `tests_js/poll-manager.test.js`, `definitions.test.js`,
   `mock-server.test.js`, `render.test.js`, `templates.test.js` (the last two split by §12's
   amendment); `lint`/`typecheck`/`lint:html`/`lint:css`/`test` all green — reconfirmed directly
   against this branch's current head (`b48d6f2`), not just taken on session 2's own word.
   Manually verified end-to-end in real Chromium (Playwright, this
   session's own pre-installed browser): both devices' full nav → section → live-poll → Apply
   (including an out-of-range value correctly rendering "Invalid") → errcount-expand flow, in both
   color schemes and at a mobile viewport width, zero console/page errors. `npm run preview` (added
   this session) serves the prototype locally — see §5.
3. **Real implementation, TDD.** Write a spec/goal/action list derived from session 2's prototype;
   then tests-first JS unit tests (Vitest) against that spec; then the real implementation —
   mirroring this repo's own `improved-quality/` → `src/` two-phase precedent (prototype/sketch,
   then a from-spec, test-driven hardened build, not just polish of the sketch) — until session 1's
   pipeline is fully green and coverage is maximized. Standing coding guideline: render any
   server-supplied text via `textContent`, never `innerHTML`, so the page stays XSS-safe by
   construction.

   **Session 3 status: done** — `claude/website-s3-tdd-implementation`. Session 2's prototype
   turned out to already be close to production-grade on code quality (zero `innerHTML` anywhere,
   careful edge-case handling in `mock-server.js`, a fully strict `definitions.js` validator) — so
   this session's real spec, derived from reading every `js/` file end to end against
   SPECIFICATION.md A.8's REST contract, turned out to be a **hardening/gap-closing** pass rather
   than a rewrite: five concrete, confirmed-real correctness gaps, plus full test coverage for the
   two files that had none.

   Gaps found and fixed, each TDD (a failing test proving the gap, then the fix):
   - **`js/poll-manager.js` had no client-side request timeout.** The single-flight queue (§4
     "Poll coordination") would wait forever on one hung connection, permanently wedging every
     future poll — the device has very few available sockets, so this was a real, not
     hypothetical, failure mode. Fixed with an `AbortController`-based per-request timeout
     (`DEFAULT_TIMEOUT_MS = 15000`, overridable per call), which also frees the underlying browser
     connection, not just this app's own bookkeeping.
   - **`js/render.js`'s `fetchOnce()` silently swallowed GET failures.** A non-ok response just
     `return`ed with no visible effect; a thrown error (network failure, or the new timeout above)
     was uncaught for every non-`"live"` section, becoming an unhandled promise rejection. Fixed:
     `fetchOnce()` now throws uniformly on any failure and catches centrally, showing a per-section
     error banner (`js/templates.js`'s `buildSectionShell()` now returns `{grid, errorBanner}`,
     reusing the same `.error-banner`/`.hidden` treatment `html/index.html`'s app-level banner
     already established) without clearing the stale-but-still-useful data already on screen, and
     clearing the banner again on the next successful poll (self-healing, matches the existing
     retry-forever polling design — no behavior change to *when* polling continues, only to
     whether a failure is visible).
   - **`js/app.js`'s mock-fixture-data fetch had no error handling at all** (unlike the
     `loadDefinitions()` call immediately above it) — a failed/malformed response crashed
     `startApp()` outright with an uncaught `SyntaxError`. Fixed to match the existing
     definitions-load pattern: checks `.ok`, catches, shows the same error banner.
   - **`js/mock-server.js`** gained a minimal, explicitly prototype-only failure-injection hook
     (`installMockFetch(defs, data, controls)` — `controls.nextFailure` is `"network"` or an HTTP
     status, one-shot) so the three gaps above could be exercised through the real mock-backed
     integration tests (`render.test.js`/`app.test.js`), not just synthetic `window.fetch` stubs.
     Session 5's real digital-twin backend supersedes this; kept intentionally thin.

   Test coverage: `js/nav.js` and `js/app.js` had **zero** dedicated test files before
   this session (both existing behavior turned out correct — `nav.test.js`'s 5 tests all passed on
   the first run, no bugs found there); `tests_js/nav.test.js` (5 tests) and `tests_js/app.test.js`
   (5 tests) added. Also added: an XSS-safe-by-construction regression suite (asserts a hostile
   `<img onerror=...>` field label/value never becomes a real DOM element anywhere `js/templates.js`
   builds one — locks in the standing `textContent`-only guideline against future regressions);
   edge-case coverage for a composite field submitted with only some subfields filled (reports
   `Invalid`, doesn't silently apply a half-specified command) and for a PUT that fails at the
   network level (`Request failed`, `failed` apply-status, Apply button re-enabled afterward); and
   several `definitions.js`/`mock-server.js`/`templates.js` validation-branch tests closing
   coverage gaps surfaced by the new `test:coverage` script (below). Went from 45 tests (session 2)
   to 82; a stray dead-code candidate (`PollManager.isBusy`, previously unused anywhere) was kept
   and given a test rather than deleted, since it's a plausible future UI affordance (a "syncing"
   indicator) and this session's scope was hardening existing behavior, not pruning speculative
   public API.
   - **Coverage tooling**: added `@vitest/coverage-v8` + non-gating `npm run test:coverage`,
     mirroring the Python side's own non-gating `scripts/test.sh --coverage` (CLAUDE.md's "Code
     quality tooling") — report-only, no threshold enforced anywhere. Wired into
     `.github/workflows/ci.yml`'s `web-unit-tests` job the same way: a second, `continue-on-error`
     instrumented test run after the real (gating) `npm test` step, its summary appended to the
     GitHub Actions Job Summary and its HTML report uploaded as a `coverage-html-js` build
     artifact — no Codecov upload (the Python side's own Codecov upload is itself still a no-op
     pending repo registration; not worth wiring twice for the same not-yet-usable destination).
     Coverage tooling didn't exist before this session, so there's no session-2 baseline number to
     compare against; final coverage after this session's TDD additions: **96% statements / 80.9%
     branches / 97.4% functions / 96% lines** across `js/`. The remaining uncovered lines are
     genuinely defensive/unreachable
     branches (e.g. a nav link somehow missing its own `data-section-key`, a `selectSection()` call
     for a section key that isn't in the loaded definitions) — deliberately not chased further,
     matching the Python side's own "report, never gate, never chase 100%" philosophy.
   - Manually verified end-to-end in real Chromium (Playwright, this session's own pre-installed
     browser, same as session 2's own verification method): both devices' full nav → section
     click-through with zero console/page errors; the new error banner triggered against a live
     (simulated) network failure mid-poll, confirmed correct in both light and dark color schemes,
     confirmed the stale data underneath stays on screen, confirmed it self-clears on the next
     successful poll.
   - Nothing in §4/§8's settled architecture changed; §12's visual/mechanics separation held
     throughout — every fix above lives entirely in the mechanics layer (`render.js`/`app.js`/
     `poll-manager.js`/`mock-server.js`) except the one new visual element (`buildSectionShell()`'s
     `errorBanner`), which `js/templates.js` builds and only `.hidden`/`.textContent` ever get
     toggled on it by a controller — the same pattern `html/index.html`'s app-level banner already
     used, not a new one. `src/` was never touched; §11's schema-comment tooling was not built.

   **Session 3 follow-up: Python-parity quality/stability/testing pass (same branch/PR).** Applied
   CLAUDE.md's Python-side rules (Hard rules, Working agreements, Code quality tooling) and
   SPECIFICATION.md Parts D/E to `js/`/`tests_js/`, finding a JS-side equivalent for each and either
   confirming it already held or fixing it:
   - **Real bug, found and fixed via TDD**: a number field's text `<input>` coerced non-numeric text
     to `Number("garbage") === NaN`, and `JSON.stringify(NaN)` is `"null"` — server-side,
     `Number(null) === 0`, so garbage typed into a field whose valid range included 0 (e.g. a
     composite subfield's `min: 0`) silently PUT a deliberate-looking `0` instead of failing
     validation, with no visible error. Fixed in `render.js`'s `readInputValue()` and
     `collectGroupBody()`'s composite branch: non-finite input is now sent through as the raw string
     so the backend's own `Number(value)` recreates the same failure and correctly rejects it.
     Regression tests added in `render.test.js`; also verified live against the real running
     prototype in Chromium (Playwright), not just the unit tests.
   - **D.2/D.3-equivalent (stability)**: audited every `catch` block for silent swallowing (none
     found — every one either surfaces a visible banner or is itself documented as defense-in-depth,
     see below) and every event-listener/timer lifecycle for leaks on repeated polls/section
     switches (none found — `PollManager`'s `AbortController`+timeout and `startPolling()`'s
     resolve-before-reschedule design were already correct, confirmed empirically in real Chromium
     that an aborted `fetch()` rejects promptly and the underlying connection actually closes).
   - **D.6-equivalent (typing)**: replaced every remaining `@type {any}` cast (4 in `definitions.js`/
     `render.js`, plus one `@returns {Record<string, any>}` in `mock-server.js` found only by the
     broader D.10 sweep below) with the actual precise type, fixing two now-real type errors this
     surfaced (an `unknown` PUT-body value flowing into `Array.prototype.includes()` and into
     `applySparsePut()`) rather than papering over them.
   - **D.10-equivalent (cross-file consistency)**: a bird's-eye pass over all of `js/` found and
     fixed missing `@returns` tags on `collectGroupBody()`/`envelope()`/`jsonResponse()`/
     `handleGet()` (every sibling helper in the same files already had one) and reordered
     `PollManager`'s two methods (getter before the request method, matching D.15's
     Getters-before-Others convention) — both mechanical, no behavior change.
   - **E.5.1-equivalent (branch coverage)**: raised branch coverage 80.91% → 84.21% (94 tests, up
     from 82) by adding real, previously-unexercised cases — `definitions.js`'s missing section
     key/label, `templates.js`'s `field.description` hint and a module absent from `errcount`
     entirely, `mock-server.js`'s `jitterInPlace()` non-number/timestamp branches and an unknown PUT
     sensor key, `poll-manager.js`'s `startPolling()` catch branch, `render.js`'s empty-GET-body and
     `/status` sub-fetch-failure error paths and a readonly field refreshed in place inside a
     writable live-polled group. Three genuinely defensive/unreachable branches found along the way
     (`app.js`'s unknown-section-key guard, `nav.js`'s missing-`data-section-key` guard,
     `poll-manager.js`'s `tick()`'s redundant top-of-function `stopped` check) were left as-is and
     documented inline with why, matching Part E.5.1's own "document, don't chase" precedent, rather
     than force-testing them via contrived internals access.
   - **Docstring cap (Working agreements)**: every `js/`/`tests_js/` JSDoc module/function header
     was over CLAUDE.md's 3-line docstring cap (a rule already stated as applying to new code, not
     yet actually applied here). Trimmed all of them to ≤3 lines; load-bearing detail that wasn't
     already documented elsewhere moved into this file (the errcount rollup/collapse UX rationale
     and the apply-status worst-first severity ordering, both added above/nearby) rather than being
     dropped, mirroring the Python side's own "moved to SPECIFICATION.md Part X" pattern.
   - **Lint stringency parity**: `eslint.config.js` gained 11 core ESLint rules beyond
     `eslint:recommended` (`array-callback-return`, `no-await-in-loop`, `no-constructor-return`,
     `no-duplicate-imports`, `no-promise-executor-return`, `no-self-compare`,
     `no-template-curly-in-string`, `no-unmodified-loop-condition`, `no-unreachable-loop`,
     `no-use-before-define`, `require-atomic-updates`) — the JS-side equivalent of ruff's
     stricter-than-default selection, verified current/non-deprecated directly against the installed
     `eslint` package's own rule metadata rather than assumed. Fixed the two real findings this
     surfaced (a `paint()`/`fetchOnce()` mutual-reference in `render.js`, converted to hoisted
     function declarations rather than suppressed) plus three idiomatic `new Promise(resolve =>
     setTimeout(resolve, ms))` sleeps rewritten with a block body (harmless either way, but now
     clean under `no-promise-executor-return`); one narrowly-scoped `no-await-in-loop` suppression
     remains in `render.test.js`'s intentionally-sequential polling helper, with a comment
     explaining why.
   - **Hang-avoidance backstop (Code quality tooling)**: `vitest.config.js` now sets an explicit
     `testTimeout: 20000` — not a fix for any observed hang, but an explicit backstop mirroring the
     Python side's own standing "hanging tests are never allowed" practice, generous enough to cover
     this suite's own longest internal wait (5000ms) with real-browser/CI margin.
   - No lint/typecheck/test-count regression anywhere in this pass: `lint`/`typecheck`/`lint:html`/
     `lint:css`/`test` all still green throughout, re-verified after every change, not just at the
     end. `src/` was never touched.

   **Session 3 follow-up 2: robustness against the real backend's full error/transmission
   surface (same branch/PR).** Read `src/asy_webserver_service.py`/`src/api_response.py` end to
   end plus `tests/test_asy_webserver_service.py`'s ~110 tests (SPECIFICATION.md Part A.5/A.8) to
   enumerate every shape a real response can actually take, then made `js/` handle each one —
   never crashing, never permanently blocking, always self-healing on the next poll/retry.
   - **Real bug, found and fixed**: `render.js`'s PUT handler never checked the response envelope's
     `res`/`code` — only a malformed request body (`_body_as_dict()` returning `None`) makes the
     real backend reply `res:"ERR"`, and it does so as a **plain HTTP 200** (`ar.make_response(1)`),
     never a shaped HTTP error status. Since that response's `result` is always `{}`,
     `applyResultStyling()`'s own "empty result still means success" fallback (added for
     `/status`'s `ResetErrors`, see §12 above) silently painted a rejected PUT as **Valid**. Same
     silent-Valid outcome for a shaped HTTP error (400/404/405/413/500) reaching the PUT path,
     since that also carries `result:{}`. Fixed: the PUT handler now treats a non-2xx status, a
     null body, or `res:"ERR"` as a whole-request failure, surfacing the server's own `descr` text
     (e.g. "Invalid JSON request") instead of a bare status code.
   - **Real server-side gap found, flagged not fixed** (`src/` is out of scope for this effort):
     `WebserverService._apply_settings_groups()` merges each `SettingsGroup`'s own
     `ar.handle_set_cmd()` result into the overall `results` dict via `.update()`. If a group's
     `post_fct`/`post_asy_fct` hook raises, `handle_set_cmd()`'s own except-block returns
     `ar.make_response(100)` with `result:{}` — and that empty dict silently overwrites nothing,
     so every field in that one group simply **vanishes from the response** with no signal at any
     level (the top-level envelope still reports `res:"OK"`). `js/render.js`'s new
     `reconcileResults()` defends against this from the client side: any field the visitor actually
     submitted but that doesn't come back in `result` is now shown as `Failed` rather than silently
     omitted. The underlying server-side swallow itself is unchanged — flagging it here per
     CLAUDE.md's "flag, don't silently change" working agreement, for whichever session next
     touches `asy_webserver_service.py`/`api_response.py`.
   - **Transmission-error hardening**: `js/poll-manager.js`'s `PollManager.request()` now
     separately catches a stream read failure (`response.text()` throwing — connection dropped
     mid-body) and a JSON parse failure (a non-empty but unparseable body — a truncated/corrupted
     transmission), each rethrown with a clear message and the original error preserved as
     `Error.cause` (see below) rather than surfacing a raw `SyntaxError`/opaque stream error.
   - **Two more startup fetches hardened to the same bar**: `definitions.js`'s `loadDefinitions()`
     and `app.js`'s mock-fixture-data load had no timeout at all (a hung connection would leave the
     page stuck loading forever) and no clear handling for a torn/non-JSON response. Both now go
     through a new shared `poll-manager.js` export, `fetchWithTimeout()` (the same
     `AbortController`-based timeout `PollManager.request()` already used, extracted so it's usable
     outside the single-flight queue — these are one-time startup loads, not recurring REST polls,
     so they don't need queuing, but do need the same never-hang guarantee). `PollManager.request()`
     itself now calls this shared helper too, rather than duplicating the timeout logic.
   - **`preserve-caught-error` (new to this session)**: fixing the two throw-sites above surfaced
     that `eslint:recommended` itself (not one of session 3 follow-up 1's own added rules) now
     includes this rule in the installed `eslint` 10.8.1 — confirmed directly against the
     installed rule's own metadata, not assumed. Adopted its intended fix throughout (`new
     Error(message, { cause: originalError })`) rather than suppressing it, since attaching the
     real cause is a genuine improvement or debuggability, not just a lint-satisfying formality.
   - **Test coverage**: 94 → 110 tests, covering every new failure mode via `mock-server.js`'s
     extended `MockFetchControls` (`"malformed-body"`, `"torn-json"`, `"empty-body"`,
     `"partial-result"` — each modeled on the real backend's own documented behavior, not invented)
     plus direct unit tests of `poll-manager.js`'s own stream/JSON-failure handling and
     `definitions.js`'s never-hangs-forever guarantee. Manually verified end-to-end in real
     Chromium (Playwright): a rejected PUT correctly shows Failed with the server's real descr
     text (not silently Valid), and the app remains fully responsive immediately afterward — the
     next Apply on the same card succeeds normally, confirming self-healing rather than a stuck
     state.
   - Nothing in §4/§8/§12's settled architecture changed; `src/` was never touched beyond reading
     it. `lint`/`typecheck`/`lint:html`/`lint:css`/`test` all green throughout.

   **Session 3 follow-up 3: per-field PUT-result coloring granularity, restored to match legacy
   (same branch/PR).** Project owner asked whether the green/red/purple PUT-result color scheme
   from the legacy site (`html_raw/general/functions.js`'s `getColorForValue()`: light green
   Valid, light red Invalid, light lavender/purple Failed, light grey Unchanged) had been carried
   through end-to-end. It had, semantically — `src/base_classes.py`/`src/api_response.py` return
   exactly that four-value vocabulary, `js/render.js` already used it, and `html/style.css`'s
   `--color-warn` token is already a real purple (not the orange/yellow the name might suggest) —
   but a real granularity gap turned up on inspection: legacy colors **each field's own nearest
   card** (its own DOM ancestor walk from that specific input), so a group with one Invalid field
   among several Valid ones shows exactly that field boxed in red while the others stay their own
   color. The already-shipped stripe redesign (§12, session 2) only ever colored the **whole group
   card once**, at the group's worst status, with per-field detail as plain text only — confirmed
   not to have been a deliberate part of that redesign decision, just an unaddressed narrowing.
   Fixed, TDD: `js/templates.js`'s `buildField()` now tags each field's own `.field` wrapper with a
   new `data-field-wrapper-key` (kept deliberately distinct from the existing `data-field-key`,
   which must keep pointing at the specific control — `collectGroupBody()`/`paint()` rely on that
   exact element, so reusing the same attribute on the wrapper would have broken both). `js/render.js`'s
   `applyResultStyling()` now sets `data-apply-status` on each field's own wrapper (only for fields
   actually present in the response's `result`, matching legacy's own "only color what the result
   mentions" behavior — an untouched, sparse-omitted field keeps no stripe at all) in addition to
   the existing group-card-level worst-of-group status; the whole-request-failure `catch` block
   (network/communication errors) now also marks every field that was part of that submission as
   `failed` individually, not just the card border — a deliberate improvement over legacy, whose own
   PUT `.catch()` never colored anything at all (console.error only). `html/style.css` gained a
   `.field` baseline transparent 3px left border (matching the existing `.nav-link` "transparent
   until active" accent-stripe idiom) plus `valid`/`unchanged`/`invalid`/`failed` color rules
   mirroring the existing `.card[data-apply-status]` block.
   - **Test coverage**: 110 → 113 tests (2 new `templates.test.js` cases confirming the new
     attribute is distinct from `data-field-key` for both a plain and a composite field; 1 new
     `render.test.js` case submitting a mixed invalid+valid+untouched group and asserting each
     field's own box independently, plus 3 existing Apply-status tests extended with a per-field
     assertion). Manually verified end-to-end in real Chromium (Playwright) against the wozi
     prototype's real SCD30 sensor-settings card: submitting an out-of-range `MeasInt` alongside an
     in-range `TempOffs`, with `AmbPres`/`Altitude`/`ForceCalRef` left untouched, correctly rendered
     `MeasInt` red, `TempOffs` green, the two always-resubmitted toggles (`ContMeas`/`SelfCal`) grey
     ("Unchanged"), the three untouched fields with no stripe at all, and the card's own border red
     (worst-first) — screenshot confirmed, then discarded along with the scratch verification
     script. The network/communication-failure ("purple") per-field path is covered by the Vitest
     suite only (`installMockFetch()`'s in-page `fetch` override can't be intercepted by Playwright's
     `page.route()`, which only sees real network traffic).
   - Nothing in §4/§8's settled architecture changed. `lint`/`typecheck`/`lint:html`/`lint:css`/
     `test`/`test:coverage` all green throughout; coverage held steady (97.19% → 97.37% statements).

   **Session 3 follow-up 4: full-surface audit (structure, error handling, races, REST
   coherence/completeness, simplification) (same branch/PR).** Project owner asked for a
   bird's-eye review of both `html/`/`js/` against nine angles (structure/leanness, setup
   sanity, error/corner-case handling, race conditions, REST interfacing coherence/correctness/
   completeness, whether every GET/PUT value has a real UI representation, simplification
   room, anything missing, and overall correctness of purpose). Structure/setup/race-condition
   review found nothing to fix (the `pollManager` single-flight queue, `startPolling()`'s
   resolve-before-reschedule loop, and the visual/mechanics split all held up); two real,
   confirmed correctness bugs were found and fixed, TDD, plus three real `definitions.json`
   inaccuracies found via a fresh line-by-line cross-check against the actual `src/` driver/
   service schemas (not re-trusting session 2's own earlier audit):
   - **Real bug, found and fixed**: clicking "Reset All Errors" (`/status`'s only submit group)
     always rendered **Failed** (purple), even on a genuine success. `src/asy_webserver_service.py`'s
     `_put_status()` never returns a per-field `result` at all (`ar.make_response(0)`, no `result`
     kwarg) — unlike every other writable endpoint. `reconcileResults()` (added in follow-up 2 to
     catch a real, different server-side gap: a settings group's post-write hook silently dropping
     fields from `result`) treats any submitted-but-unreturned key as `"Failed"`, so `ResetErrors`
     — always present in `groupBody` since a toggle always resubmits its current value — was always
     marked Failed regardless of outcome. Fixed: `js/render.js`'s PUT handler now special-cases
     `section.key === "status"` (the only section with this structural shape), marking every
     submitted field `"Valid"` directly once a non-2xx/`res:"ERR"` response has already been ruled
     out, instead of running it through `reconcileResults()`. Regression test added
     (`tests_js/render.test.js`), confirmed failing (`"failed"` !== `"valid"`) before the fix.
   - **Real bug, found and fixed**: clicking Apply on a group made only of number/string fields
     (no toggle/enum, which always resubmit) while every field is left blank submits a genuinely
     empty PUT body — the real backend accepts it (`_apply_settings_groups()`'s per-group `subset`
     is always empty, so nothing is touched) and returns `result: {}`, which
     `applyResultStyling()`'s own empty-result-means-success fallback then painted as a misleading
     green **Valid**, even though nothing was submitted or changed. Affects Networking's `identity`/
     `ntp` groups, System's `settings` group, and Notification's `flash` (composite-only) and
     `pause` groups — every submit group with no toggle/enum field. Fixed: `buildAndWireFieldGroup()`'s
     click handler now checks `collectGroupBody()`'s result before doing anything else; an empty
     body skips the network round trip entirely and shows "Nothing to submit - no fields were
     changed." instead of touching `data-apply-status` at all. Regression test added.
   - **`html/definitions/{wozi,dev}.json` — 3 real value-schema mismatches, found via a fresh
     cross-check against `src/asy_wifi_service.py`/`asy_sgp40_driver.py`/`sensortask_wozi.py`
     (not just re-confirming session 2's own earlier audit)**: `SSID`'s `minLength` was `2`,
     the real schema (`_VAL_SSID`) allows `0` — the client-side validation would have rejected a
     legitimately backend-accepted 0/1-character SSID edit. `Hostname`'s `maxLength` was `63`, the
     real cap (`_VAL_HOST`'s own comment: "32 = `network.hostname()`'s real cap") is `32`.
     `WarnVOC`'s `unit` was `"ticks"` (SGP40's `Raw` field's unit) but `voc_value_callback()`
     (`sensortask_wozi.py`) feeds it from `sgp_data.VOC`, the unitless VOC Index — same mismatch
     `measurements`'s own `VOC`/`Raw` fields already correctly avoid, just missed on this
     unrelated `notification`-section field referencing the same underlying value. All three fixed
     directly (plain data corrections, not a judgment call) in both device files.
   - **Two more findings, flagged per CLAUDE.md's "flag, don't silently change" convention and
     resolved interactively with the project owner rather than guessed at**:
     - Notification's "Pause Notifications" submit card PUTs a `PauseTime` field the real backend
       never processed at all: `notify_service`'s registered PUT schema didn't include it, and
       `NotificationCoordinator.set_override_led()` — the only method that could ever act on it —
       was never called anywhere in `src/` outside its own definition (confirmed by grepping the
       whole tree). Submitting it silently did nothing server-side and, thanks to
       `reconcileResults()`, rendered as **Failed** — reading as a mistake rather than "not wired up
       yet." **Project owner's decision at the time: leave the website as-is; `src/` wiring would be
       handled separately, outside this effort.** **Now resolved directly on `main`**
       (`309b364`, "Restore LED-notification pause countdown REST wiring" — merged to `main`, then
       this branch's whole history rebased onto it): `asy_webserver_service.py` gained a
       `notification_pause` callback (mirroring `notification_led`/`system_cmd`'s own dispatch
       pattern exactly — `_dispatch_notification_pause()`, errno=5), wired in
       `sensortask_wozi.py` to `NotificationCoordinator.set_override_led()`, with unit +
       real-object-graph + real-HTTP digital-twin integration coverage (the last confirming the
       countdown actually decrements over real wall-clock time, not just that the value is stored).
       **One gap found in that fix and closed in a follow-up commit on this branch**: the new
       `_dispatch_notification_pause()` checked `payload`'s type but not its range — `LockedCounter.
       set_value()` (which `set_override_led()` calls) silently clamps an out-of-range value into
       `[0, 3600]` rather than rejecting it, so a `PauseTime` outside that range came back `"Valid"`
       (clamped) instead of `"Invalid"`, unlike legacy's own `pauseAutoLED` command
       (`update_valid_json(..., 0, 3600, ...)`, which rejects out-of-range as `"Invalid"` — the same
       convention every other numeric field in this codebase already follows server-side via
       `config_manager.py`'s `type_or_range_error()`, regardless of what a client sends). Fixed with
       an explicit `0 <= payload <= 3600` check before ever calling the callback, TDD (a failing
       test confirming the pre-fix "Valid"-on-clamp behavior, then the fix). The website side
       needed no changes — `js/render.js` already expected exactly this `result.PauseTime` shape.
     - The real `PW` (Wi-Fi password) field explicitly allows an empty string as a deliberate
       "configure an open network" sentinel (`asy_wifi_service.py`'s `_VAL_PW`'s `special=""`), but
       the website's sparse-PUT convention (`collectGroupBody()`: a blank input is "untouched,
       omit from the body," not "submit empty") makes it structurally impossible to ever send an
       empty string for *any* field through this UI, PW included. **Project owner's decision: leave
       as-is** — configuring an open network is a narrow case, and the blank-always-means-omit
       convention is simple and well understood; not worth a special-case "clear this field"
       affordance for one field. Not changed here.
   - **Every other angle checked clean, nothing to fix**: `js/measurements`/`/sensors` (SCD30/
     SGP40/BMP3XX) field sets, ranges, enums, and special values all matched their real `_VAL_*`
     schema tuples exactly; `/status`'s `networking`/`system` sub-object fields matched
     `_networking_status()`/`_system_status()` exactly; the `errcount` module list (17 entries)
     matched `_collect_error_sources()` + the webserver's own `WEBSERVER` entry exactly;
     `dev.json`'s SHTC3/MPRLS/ISL29125 sensors have no real driver under `src/` yet to check
     against (unchanged from session 2's own note — still a projection, not confirmed). No race
     conditions found in `PollManager`'s single-flight queue or `startPolling()`'s
     resolve-before-reschedule design (re-confirmed, not just taken on faith from follow-up 1's
     earlier pass); the one identified inefficiency (an in-flight GET for a section the visitor has
     already navigated away from still completes and repaints an already-detached DOM subtree, since
     `stopCurrentSection()` only cancels *future* poll ticks, not the in-flight request) is harmless
     — the stale repaint never reaches the visible DOM — and was left as-is rather than adding
     `AbortController` plumbing for a purely cosmetic/performance concern with no correctness impact.
   - **Test coverage**: 113 → 115 tests (both new regression tests TDD — written failing against
     the pre-fix code, confirmed, then made to pass). `lint`/`typecheck`/`lint:html`/`lint:css`/
     `test` all green throughout.
   - Nothing in §4/§8/§12's settled architecture changed. `src/` was never touched beyond reading it.

4. **Full build chain.** Wire `html/`+`js/`+the definitions file(s) into a
   `scripts/build_frozen_html.sh`-equivalent pipeline: gzip → `freezefs` → frozen bytecode → mount
   → serve, ending with the real thing bound into an actual firmware build. Keep the mechanism
   generic/parameterized per device (matching `build-wozi.sh`'s existing `HTML_SRC_DIRS` pattern)
   even though only the `wozi` variant can be verified end-to-end today (`src/` doesn't assemble the
   other variants yet — SPECIFICATION.md A.3).
5. **Digital twin integration.** Replace `html_stub/` in `digital_twin/`'s wiring per §7; add real
   API-endpoint-driven tests (the website's actual JS/pages exercised against the twin's live
   server, likely via the same Playwright/Chromium foundation session 3 already set up, now against
   a live backend instead of static fixtures). **Tail of this session**: a manual cross-browser/
   cross-device spot check by the project owner (Safari, Firefox, real mobile) — automated CI only
   ever exercises Chromium via Playwright, so §1/§3's "stable and good-looking on all major
   browsers" goal needs at least one real human pass somewhere, and this is the first point the
   website is running end-to-end against a real live backend.

## 11. Schema comment-tag grammar — sketch (documentation only, session 2)

**Status: a worked proposal, not a decision.** §8 still reserves actually settling this for a
dedicated future session, ideally paired with whichever driver session first touches a schema
definition under this convention. This section exists so that session is starting from a concrete,
already-checked-against-real-code sketch instead of a blank page — session 2 wrote no parser and
changed no `src/` file to produce it (per its own standing instructions).

### What actually needs a tag, vs. what the schema already encodes

Every `src/` driver's config schema is already a tuple of `(name, pytype, default, min, max,
special)` (`ConfigSchema`, see e.g. `src/asy_scd30_driver.py`'s `_VAL_MI = const((("MeasInt",
"int", None, 2, 1800, None),))`). A real future parser can derive most of `html/definitions/*.json`
straight from that tuple, with **no tag needed**:

| definitions.json field | Derived from |
|---|---|
| `min` / `max` | tuple elements 4/5, verbatim |
| `kind: "toggle"` | `pytype == "bool"` |
| `kind: "string"` | `pytype == "str"` |
| `kind: "enum"`, `min`/`max` dropped | tuple element 6 is itself a tuple/list of allowed values (e.g. BMP3XX's `_OSR_SETTINGS`/`_IIR_SETTINGS`) |
| `specialValues: [{value: <N>}]` (meaning still missing) | tuple element 6 is a single scalar sentinel (e.g. SCD30's `AmbPres` → `0`) |
| `kind: "number"` (the fallback) | `pytype in ("int", "float")` and none of the above apply |

What's genuinely invisible to the schema tuple — and so is exactly what a tag needs to supply — is
human-facing text and cross-cutting grouping: **label**, **unit**, **description**, the **meaning**
of a special/sentinel value, the **label** of each enum option, an occasional **kind override**
(for constants that aren't a `ConfigSchema` tuple at all, e.g. `asy_webserver_service.py`'s
`_SYSTEM_CMDS`), and which **module/REST-section/submit-group** a field belongs to.

### Grammar

A tag is a `#`-prefixed comment line placed immediately above the schema-tuple line (or above the
constant it annotates, for non-`ConfigSchema` values like `_SYSTEM_CMDS`) it describes — never a
trailing same-line comment, so the parser only ever has to look one line back:

```
# @web <key>=<value> <key>="<quoted value>" ...
```

- `@web` marks a per-**field** tag. Keys are space-separated `key=value` pairs; a value containing
  a space must be double-quoted (`label="Ambient Pressure"`); an unquoted value is any run of
  non-whitespace characters.
- Recognized keys: `label` (required — the one thing every field needs and the schema can never
  supply), `unit`, `description`, `kind` (only to *override* the auto-derived kind — see the
  `SystemCmd` example below; omit it whenever inference already gets it right), `mask=true` (for a
  password-shaped string field), `onLabel`/`offLabel` (toggle button text, defaults to "On"/"Off"
  if omitted).
- `special:<value>="<meaning>"` is a repeatable key of the form `special:` + the literal value +
  `=` + its human meaning. It's the same tag form for two different JSON targets, disambiguated by
  what the schema tuple's 6th element already says: a single-sentinel field (`AmbPres`) puts it
  under `specialValues`; an enumerated field (`PressOvers`) puts every `special:` entry under
  `options` instead (one per allowed value — an enum with any unlabeled allowed value is a parser
  error, not a silently-blank option).
- `@web-group` marks a **module-level** tag, placed above the class/schema-declaration that owns a
  whole set of `@web`-tagged fields (e.g. above a driver's `ConfigSchema` construction): `label`
  (the group's own display heading, e.g. `"SCD30 — CO2, Temperature, Humidity"`), `endpoint` (which
  of the six REST sections it belongs to — `sensors`/`networking`/`system`/`notification`/`status`),
  `submitGroup` (an optional key when a module's fields split into more than one independent-PUT
  card, matching A.8's "one `SettingsGroup` per field subset" note — e.g. `/networking`'s Wi-Fi
  credentials vs. its `LedWifiOn` toggle vs. its NTP fields are three separate `submitGroup`s within
  one module).

### Worked examples, against real `src/` schema code

A sentinel special value (`src/asy_scd30_driver.py`):

```python
# @web label="Ambient Pressure" unit=hPa description="Starts continuous measurement." special:0="Compensation off / use Altitude"
_VAL_AP = const((("AmbPres", "int", None, 700, 1400, 0),))
```

→ `{"key": "AmbPres", "label": "Ambient Pressure", "unit": "hPa", "kind": "number", "min": 700,
"max": 1400, "specialValues": [{"value": 0, "meaning": "Compensation off / use Altitude"}],
"description": "Starts continuous measurement."}`

A toggle (`src/asy_scd30_driver.py`) — `kind` needs no tag at all, `pytype: "bool"` already says it:

```python
# @web label="Automatic Self-Calibration"
_VAL_SC = const((("SelfCal", "bool", None, None, None, None),))
```

→ `{"key": "SelfCal", "label": "Automatic Self-Calibration", "kind": "toggle", "onLabel": "On",
"offLabel": "Off"}`

An enumerated field (`src/asy_bmp3xx_driver.py`) — six `special:` entries, one per allowed
oversampling value, become the enum's six labeled `options`:

```python
# @web label="Pressure Oversampling" special:1="×1" special:2="×2" special:4="×4" special:8="×8" special:16="×16" special:32="×32"
_VAL_POV = const((("PressOvers", "int", 1, None, None, _OSR_SETTINGS),))
```

→ `{"key": "PressOvers", "label": "Pressure Oversampling", "kind": "enum", "options": [{"value": 1,
"label": "×1"}, {"value": 2, "label": "×2"}, ...]}`

A value with no `ConfigSchema` tuple behind it at all (`src/asy_webserver_service.py`) — this is
the one case that genuinely needs `kind=` on the tag itself, since there's no `pytype` to infer
from:

```python
# @web label="Command" kind=enum special:reboot="Reboot" special:bootloader="Reboot into bootloader" special:mempause="Pause backups for 5 minutes"
_SYSTEM_CMDS = const(("reboot", "bootloader", "mempause"))
```

→ `{"key": "SystemCmd", "label": "Command", "kind": "enum", "options": [{"value": "reboot", "label":
"Reboot"}, ...]}` (note: the field's own JSON `key` is `SystemCmd`, not the Python constant's name
`_SYSTEM_CMDS` — the real future parser would need its own rule for that mapping, e.g. reading it
off the webserver's own `body.get("SystemCmd")` call site rather than the tuple; left for the
dedicated session, flagged here rather than silently assumed).

### What this sketch deliberately leaves open

- The composite `lightCmdLED` shape (r/g/b/t) and other webserver-level, non-driver-schema values
  don't have an obvious single "tuple line" to anchor a tag above — the `SystemCmd` example already
  shows the parser needs *some* per-value-shape judgment, not a fully mechanical one-tag-per-line
  rule. A dedicated session should decide this case by case rather than this sketch guessing.
- Whether `@web-group`'s `endpoint`/`submitGroup` really belong on the schema declaration, or read
  better off `src/sensortask_wozi.py`'s own construction-step wiring (`SettingsGroup(...)` calls,
  A.7/A.8) instead — the wiring site already states this same grouping today, so tagging it a
  second time in the driver file risks the two silently drifting apart. Worth deciding before
  building the real parser, not assumed here.
- This sketch does not attempt a full formal grammar (EBNF, escaping rules for a `"` inside a
  quoted value, etc.) — deliberately, since it's meant to prove the *shape* of the idea against
  real code, not to be implementation-ready.

## 12. Visual design / functional mechanics separation (standing requirement)

Project owner's explicit, standing requirement (not just for this session): the REST API and the
overall concept are expected to stay stable for a long time; the visual design is expected to be
revisited — restyled, reordered, regrouped — independently of that, more than once. **A purely
visual/layout redesign must never require editing data-fetching, validation, submission, or poll-
coordination code.**

### The two layers

- **Visual layer** — owns colors, spacing, typography, dark-mode tokens (`html/style.css`,
  unchanged from §4), **and** DOM structure/order/nesting/CSS-class choices (`js/templates.js`,
  new). `js/templates.js` also owns any interactivity that's purely cosmetic and never touches the
  network or app state — a toggle button flipping its own On/Off label, an errcount tile
  expanding/collapsing its own history list. A redesign session touches these two files (plus, for
  a schema/labeling change, the `definitions.json` content itself — see §8) and nothing else.
- **Mechanics layer** — owns data fetching, polling coordination, input validation, PUT submission,
  and anything that calls the REST API or the poll-manager: `js/poll-manager.js`,
  `js/mock-server.js`, `js/definitions.js` (already pure — no DOM code at all), and the
  non-presentational parts of `js/render.js`/`js/nav.js` (now "controllers" — see below). None of
  these files build DOM elements, choose CSS classes, or decide element order/nesting.

### The contract between them

Controllers never reach into a template's internals by structure (no "third child of the second
div") — only by the same `data-*` attributes and CSS classes the templates already expose, which is
the one thing a redesign must keep stable (renaming a hook needs a matching one-line change on the
controller side, same as renaming a REST field needs a matching change in `definitions.json` — a
small, obvious edit, not a redesign blocker):

| Hook | Set by (`js/templates.js`) | Read by (controller) |
|---|---|---|
| `[data-field-key]` | every field's input/select/toggle-button/readonly span | `render.js` collects submitted values, updates readonly text/current-value captions on poll |
| `[data-sub-field-key]` | a composite field's per-subfield input | `render.js` collects the composite's nested PUT body |
| `[data-current-value-for]` | a writable field's "Current value: …" caption | `render.js` refreshes it after a poll/Apply |
| `[data-group-key]` | a field-group's card | `render.js` locates the card to re-render/restyle |
| `[data-apply-status]` | *(unset by templates.js; only ever written by the controller)* | CSS alone decides what each status value looks like (`html/style.css`'s `.card[data-apply-status="…"]` rules) |
| `.apply-button` / `.errcount-tile` | the submit button / an errcount module tile | `render.js` attaches the real (networked) click handler |
| `[data-section-key]` | each nav-drawer link | `nav.js` attaches the section-select click handler |

Controllers only ever set the semantic `data-apply-status` value (`"valid"`/`"invalid"`/
`"unchanged"`/`"failed"`) — never a color, class, or style directly. What that status *looks like*
is entirely `html/style.css`'s decision, so restyling what "invalid" means visually is a pure CSS
change.

A card can hold several fields, each with its own per-field result, but `data-apply-status` is one
value for the whole card — `js/render.js`'s `STATUS_SEVERITY` picks the worst one, worst-first:
`Invalid`/`Failed` (a real problem) always win; between the two non-problem outcomes, a genuine
`Valid` change outranks a no-op `Unchanged`, so one changed field + one resubmitted-as-is field
reads as "valid" (something happened), not "unchanged" (nothing did).

**One deliberate exception to the "hooks are `data-*` attributes" rule (session 3):**
`buildSectionShell()` returns `{grid, errorBanner}` directly to its one caller (`render.js`'s
`renderSection()`) rather than making the controller look `errorBanner` up by attribute — there's
only ever one error banner per rendered section and it's handed back at the exact point it's
created, so a lookup hook would add indirection with no reuse benefit. The controller still only
ever touches it the same two ways `app.js`'s pre-existing app-level error banner already
established: toggling the `.hidden` utility class and setting `.textContent` — never a color or
custom style. Restyling what a fetch-error banner looks like is still a pure `html/style.css`
change (`.error-banner`), same as every other hook in this table.

### Where this stood before this note, and what changed

Session 2 already got this partially right by accident: `html/style.css` was already fully
visual-only, and controllers already queried the DOM by `data-*` attribute rather than by
structural position. What wasn't separated: `js/render.js` and `js/nav.js` built DOM elements,
picked CSS classes, and decided element order **inline**, interleaved with the fetch/validate/
submit logic in the same functions — so reordering a card's internal fields, or restyling the nav
drawer's markup, meant editing the same file that talks to the REST API, and risked touching that
logic by accident. Session 2 was amended, before merging, to extract that DOM-building half into
`js/templates.js` — see that file's own module docstring, and `render.js`/`nav.js`'s updated
docstrings, for the concrete split. No behavior changed; the JS unit tests and the manual browser
verification were re-run to confirm.
