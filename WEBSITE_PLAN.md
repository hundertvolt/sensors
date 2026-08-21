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
  four states the real backend's `PUT` envelope reports, `api_response.py`) now shows as a left
  accent stripe + inline per-field text on the card, not legacy's whole-card background flash.
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
