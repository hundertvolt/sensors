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
ending — don't leave it only in that session's own transcript. **Entries here are settled facts,
conventions, and current state — never a narrated log of who found or asked what, when, or why.**
State the rule/decision itself, generically enough that it reads the same whether it was reached on
the first try or the fifth; the "how we got here" belongs in git/PR history, not in this file.

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
  nesting, fixed light-grey/white palette. No media queries at all — "works in light and dark" in
  practice means a fixed-light page that simply doesn't break under a dark OS theme, not real
  `prefers-color-scheme` adaptation (the redesign's own dark-mode support is settled in §4).
- **Legacy REST shape (still targeted by `functions.js` today) differs from the new backend**:
  `/sensors/status`, `/sensors/config`, `/sensors/cmd`, `/net/config`, `/net/cmd`, `/led/cmd`,
  `/led/config`, `/system/cmd`, `/system/status`, etc. — PUT-with-`cmd`-envelope, `Led`-prefixed
  field names (`LedWarnCO2`, `LedAutoOn`, ...). This is **not** what `src/asy_webserver_service.py`
  (SPECIFICATION.md A.8) already exposes — see §4's REST-target decision.
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
| Definitions file | One single JSON per device, fetched once | Covers nav, page/field labels, units, valid ranges, special values, etc. Concrete schema in §4.1. |
| Definitions generation stage | Build-time, static JSON | A build script parses the tagged schema comments from the real `.py` source **before** `mpy-cross` strips comments, emits a static JSON frozen alongside the HTML in the same `freezefs` pipeline. Never computed/served at runtime — zero device RAM/CPU cost. Tag grammar not yet decided — see §8/§11. |
| REST target | `src/asy_webserver_service.py` API (SPECIFICATION.md A.8) | Six endpoints (`/measurements`, `/sensors`, `/networking`, `/system`, `/status`, `/notification`), sparse-body PUT, no `cmd` envelope, no `Led`-prefixed fields. **Not** the legacy shape §2 describes — this website targets the refactored backend from day one. |
| Nav grouping | Mirrors the 6 REST endpoints 1:1 | Sections: Measurements, Sensors, Networking, System, Status, Notification. |
| History depth/pagination | Counts always visible; full history on demand; **no pagination/truncation** | Per-module error-count/last-error always shown. Clicking a module's error-count entry expands its full `history` array as-is — a realistic history depth stays well under 20 entries, so chunked loading would be overkill. History rides along in the same `/status` response (fetch-once-per-poll), not a separate paginated endpoint. |
| Poll coordination | One shared JS poll-manager module (single-flight queue) | Single source of truth for "is a request in flight." The measurements group and the status/settings group are never polled concurrently by design (a page only ever needs one or the other); if that ever becomes unavoidable, a new poll must wait until the pending request has resolved **and its connection has fully closed** before starting — the device has very few available sockets. Every fetch (recurring polls and one-time startup loads alike) goes through a shared `AbortController`-based timeout so nothing can hang forever. |
| API reachability | No dedicated API-browser page | Every endpoint's functionality just needs to be reachable somewhere in the ordinary GUI (satisfied by the nav-mirrors-endpoints decision above) — not a Swagger-style reference/try-it tool. |
| Definitions validation | Strict — visible error state on mismatch | The JS checks the fetched definitions file's shape/version before rendering, including `pollGroup` (must be `"live"`/`"settings"`/`"none"`) and both poll-interval fields (must be a positive number) — a mismatch surfaces a visible error banner rather than silently rendering something broken or skipping unknown fields. |
| Landing page | Measurements page | Matches legacy's default landing page. |
| Dark mode | Automatic only, via `prefers-color-scheme` | No manual toggle, no stored preference. CSS custom-property tokens on `:root`, redefined under `@media (prefers-color-scheme: dark)` (`html/style.css`). Keeps the page "small, lean, fully self-contained" (§3) with zero added JS/state for it. |
| Card/nav visual treatment | Modernized flat cards; slide-in drawer nav | Cards: soft border/shadow (not legacy's flat grey fill), real light/dark tokens. Nav: a slide-in drawer opened by a hamburger button, listing the six section links plus the device name, no other global actions in it. |
| Rendering safety | Server-supplied text via `textContent` only, never `innerHTML` | Standing coding guideline for all new JS — keeps the page XSS-safe by construction. |
| Visual/mechanics separation | Hard layering: `html/style.css` + `js/templates.js` vs. everything else | A future redesign (visual restyle, or reordering/regrouping what's on a page) must never require touching data-fetching/validation/submission code. **Standing requirement — see §12** for the full contract and the data-attribute hooks between the two layers. |
| Numeric int/float coercion & validation | `config_manager.py`'s `type_or_range_error()`/`coerce_numeric()`, mirrored in `js/mock-server.js` | Canonical policy for every numeric field, schema-backed or dispatch-only alike — see SPECIFICATION.md Part A.8 (backend) and Part G (the reuse pattern this establishes for any new numeric field). A float-typed field's `definitions.json` entry sets `"float": true`; `js/render.js`'s `serializePutBody()` forces a decimal point onto an outgoing whole-number float value so the wire body preserves the int/float distinction JSON itself can't carry. |
| Dispatch-only PUT fields | `SystemCmd`, `PauseTime`, `lightCmdLED`, `ResetErrors` — the complete set | None of these are persisted settings: each re-dispatches fresh on every submission (never reports `"Unchanged"`), and each has its own validation shape (see §4.2). `js/mock-server.js` excludes all four from its generic sparse-PUT persistence path. An enum field with no value matching the current GET-reflected state (true for every dispatch-only enum, since these are never returned by GET) renders with a blank placeholder option selected by default — never silently defaulting to the first real option — so an untouched Apply click submits nothing rather than an unintended command. |
| PUT-result coloring | 4-state vocabulary (`Valid`/`Unchanged`/`Invalid`/`Failed`), colored at two levels | Matches the real backend's own vocabulary (`base_classes.py`/`api_response.py`). Colored on the group card as a whole (worst status across the group — `Invalid`/`Failed` always outrank `Valid`/`Unchanged`; between the two non-problem outcomes, `Valid` outranks `Unchanged`) **and** on each individual field's own wrapper (only for fields actually present in the response's `result`; an untouched, sparse-omitted field keeps no stripe). A whole-request failure (network/communication error) marks every field in that submission `Failed` individually, not just the card border. |
| PUT/GET error handling | Every fetch treats a non-2xx status, a null body, or `res:"ERR"` as a whole-request failure, surfacing the server's own `descr` text | Applies uniformly to polls and submissions. A field the visitor submitted but that doesn't come back in the response's `result` is shown `"Failed"` (client-side defense; the matching server-side contract — a failing settings-group hook never silently drops fields either — is stated in §4.2). A GET failure shows a per-section error banner without clearing the stale-but-still-useful data already on screen, clearing again on the next successful poll. `/status`'s own PUT (`ResetErrors`) never returns a per-field `result` at all — every submitted field there is marked `Valid` directly once a request-level failure has been ruled out, not run through the generic per-field reconciliation above. |
| Per-device page-scheme mechanism | The definitions file itself | `js/render.js`/`js/nav.js` contain zero device-specific branching — every card, field, and nav entry comes from the fetched `definitions.json`. All devices share the same `html/index.html` + `js/` tree, pointed at different definitions files. |
| Known accepted gap: empty-string fields | Cannot currently be set to an empty string via this UI, for any field | The sparse-PUT convention (a blank input means "untouched, omit from the body") makes an explicit empty-string submission structurally impossible — affects `PW`'s real "configure an open network" sentinel (`asy_wifi_service.py`'s `_VAL_PW`). Accepted as-is; not planned to change. |

### 4.1 Definitions JSON schema

One JSON file per device (`html/definitions/<device>.json`), shipped and frozen alongside `html/`
by the build pipeline (§4's "Definitions generation stage"). `js/definitions.js` documents this
shape via JSDoc typedefs and strictly validates it at load time (§4's "Definitions validation" row).

- **Top level**: `{schemaVersion, device, landingSection, defaultPollIntervalMs, sections[]}`.
- **`section`**: mirrors one of the six REST endpoints — `key` matches the endpoint name,
  `rest: {get, put?}`, `pollGroup: "live"|"settings"|"none"` — and holds `groups[]`.
- **`group`**: normally a `FieldGroup` (`key`, `label`, optional `submit`/`submitLabel`,
  `fields[]`). Status's error section is instead the distinct `ErrcountGroup`
  (`kind: "errcount"`, `modules[]`), since its shape (per-module counter + optional history)
  doesn't fit the field-list model.
- **`FieldDef`**: a `kind` (`readonly | number | string | enum | toggle | composite`) plus
  kind-specific metadata (`min`/`max`, `minLength`/`maxLength`, `mask`, `options`, `specialValues`,
  `subFields`, `onLabel`/`offLabel`, `float`).
- See `html/definitions/wozi.json` and `html/definitions/dev.json` for the two worked, real
  examples (wozi's SCD30/SGP40/BMP388 vs. dev's SCD30/SGP40/SHTC3/MPRLS/ISL29125 — deliberately
  different sensor sets, field kinds, and value ranges). `dev.json`'s SHTC3/MPRLS/ISL29125 entries
  are a projection from the same pattern every promoted sensor follows, not confirmed against real
  driver code — these sensors have no real driver under `src/` yet (see §8).

### 4.2 Errcount (Status section) and dispatch-only field conventions

- **Errcount module list**: `{key, label}` per entry — one per registered module, plus each
  module's own `CFGMGR_<name>` config-store instance (except SCD30, which persists to the sensor's
  own NVM, not a `ConfigManager`, so it has no config-store error source), plus the webserver's own
  `WEBSERVER` entry — matching `asy_webserver_service.py`'s `_build_errcount()` shape exactly.
  Looked up directly in `/status`'s `errcount[key]` response at render time, no transformation
  beyond the key lookup.
- **History entry shape**: `{"num": <raw errno>, "type": "N"|"E"|"W"}` per slot, always a fixed
  `history_length`-long list (never shorter — a healthy module's history is all `"N"` placeholders,
  not an empty array). No per-entry timestamp anywhere in the system. `type` is never rendered as
  text — its only job is to color `num` (green/yellow/red for no-error/warning/error) via
  `data-err-type`, styled entirely by `html/style.css`.
- **Errcount UX**: rendered in the same `.card` shell every other field group uses. Starts fully
  collapsed to a rollup ("N modules with errors" / "M modules with warnings") plus two filter
  buttons ("Show flagged"/"Show all"); revealing a module row shows its history immediately, no
  further per-row click needed. Wired entirely inside `js/templates.js` (purely cosmetic
  expand/collapse, no controller/network involvement).
- **Dispatch-only field semantics** — `SystemCmd`, `PauseTime`, `lightCmdLED` (r/g/b/t composite,
  bounds 0-255/0-255/0-255/0.5-60.0, matching legacy's own bounds exactly and rejecting — never
  clamping — a value outside them), `ResetErrors`: `"Invalid"` only for a structurally wrong
  payload (non-dict for `lightCmdLED`, not in the allowed set for `SystemCmd`, out of type/range
  for `PauseTime`); anything else wrong (missing/non-numeric/out-of-range subfield) reports
  `"Failed"`; a well-formed submission always reports `"Valid"`, including on an identical repeat
  (never `"Unchanged"` — these re-dispatch fresh every call). `js/mock-server.js` mirrors this
  exactly via `dispatchRangedAction()` (`PauseTime`) and `dispatchLightCmdLed()`, writing straight
  to each field's real destination state and never persisting into the generic settings store.
- **Server-side settings-group failure**: if a `SettingsGroup`'s post-write hook raises, every
  field that group actually attempted is reported `"Failed"` in the PUT response — never silently
  dropped — while the overall envelope still reports success (per-field detail carries the
  failure, matching every other endpoint's own convention of never failing the overall request for
  per-field detail).

## 5. Folder structure

New source lives in **top-level siblings** of `src/`/`tests/` (matching the repo's existing flat
convention — `html_raw/`, `html_stub/`, `ext/`, `digital_twin/` are all top-level too, not nested):

```
html/               Hand-written HTML skeleton(s) + CSS - the new real website source
html/definitions/   Per-device definitions.json (schemaVersion/device/sections - see §4.1) - shipped,
                     frozen alongside html/ by the same pipeline (§4's "Definitions generation stage")
js/                 Hand-written ES module JS source (poll-manager, mock backend, definitions
                     loader/validator, generic renderer, templates, nav) - see §6
tests_js/           JS unit tests (Vitest, see §6)
mockdata/           Prototype-only mock backend fixtures - NOT shipped, NOT part of the frozen-HTML
                     pipeline; consumed only by js/mock-server.js for local viewing until a real
                     backend/digital-twin exists (§7)
```

`package.json`/`package-lock.json` at repo root (dev-tooling only, `node_modules/` gitignored) —
mirrors `pyproject.toml`'s existing role: shipped code stays hand-written plain files, never
restructured into a build/bundle output. `html_raw/` (legacy, still deployed) and `html_stub/`
(placeholder, still wired into `src/sensortask_wozi.py` until this effort's output replaces it) are
untouched by this restructuring. `npm run preview` serves the repo root via
`python3 -m http.server 8000` — open `http://localhost:8000/html/index.html?device=wozi` (or
`?device=dev`) to click through the live prototype locally.

Current `js/` modules: `app.js` (**prototype-only** entry point: mock fetch, `?device=` switch,
dev-server-relative paths — never shipped), `main.js` (the **real production** entry point — no
mock install, single build-fixed device via a plain `definitions.json` fetch, no `?device=`
branching; see §10 item 4 for why it's staged as `app.js` in the real build rather than requiring
an `html/index.html` edit), `definitions.js` (loader + strict validator + JSDoc type definitions
for the whole schema, no DOM code), `render.js` (section/group/field controller — fetch/validate/
submit logic, delegates all DOM building to `templates.js`), `templates.js` (the DOM/markup-building
layer — owns every element/class/order choice, see §12), `nav.js` (drawer wiring), `poll-manager.js`
(single-flight request queue + shared fetch-timeout helper), `mock-server.js` (**prototype-only**
fetch-intercepting fake backend, answers the same six REST paths/shapes A.8 documents — an explicit
placeholder for §7's real digital-twin backend, never shipped).

## 6. CI / tooling stack

Mirrors the Python side's actual roles (ruff/mypy/pytest), not just "any linter/tester":

| Python role | JS/HTML/CSS equivalent | Notes |
|---|---|---|
| ruff (lint) | **ESLint** (flat config, `eslint.config.js`) | Chosen over Biome for ecosystem maturity/rule coverage. Beyond `eslint:recommended`: `array-callback-return`, `no-await-in-loop`, `no-constructor-return`, `no-duplicate-imports`, `no-promise-executor-return`, `no-self-compare`, `no-template-curly-in-string`, `no-unmodified-loop-condition`, `no-unreachable-loop`, `no-use-before-define`, `require-atomic-updates` — the JS-side equivalent of ruff's stricter-than-default selection. |
| mypy (type-check) | **TypeScript `checkJS` mode** (`tsc --noEmit`) reading JSDoc annotations in plain `.js` | Pure dev-time checker, zero transpilation — shipped JS stays exactly as written, same "dev-tooling only" split as `pyproject.toml`. `tsconfig.json`: `ES2022` target/module, `checkJs`/`allowJs`, `strict`. |
| MicroPython Unix-port interpreter for tests (real environment, not CPython+stubs) | **Vitest in real-browser mode** (`@vitest/browser-playwright`'s `playwright()` provider, against real Chromium) | Deliberately not jsdom — same "real engine over a DOM/interpreter shim" principle SPECIFICATION.md Part E.1 already argues for the Python side. `vitest.config.js` conditionally passes `launchOptions.executablePath` pointing at a Claude Code sandbox's pre-installed `/opt/pw-browsers/chromium` when that path exists; CI runners instead run `npx playwright install --with-deps chromium` first. `testTimeout: 20000` is an explicit hang-avoidance backstop, mirroring the Python side's own standing "hanging tests are never allowed" practice. |
| `scripts/test.sh --coverage` (non-gating) | `@vitest/coverage-v8` + non-gating `npm run test:coverage` | Report-only, no threshold enforced anywhere — mirrors the Python side's "report, never gate, never chase 100%" philosophy. Wired into `.github/workflows/ci.yml`'s `web-unit-tests` job as a second, `continue-on-error` instrumented run after the real (gating) `npm test` step; summary in the GitHub Actions Job Summary, HTML report as a `coverage-html-js` build artifact. No Codecov upload (the Python side's own upload is itself still a no-op pending repo registration). |
| — | **html-validate** for `html/`'s skeleton(s); **Stylelint** for the CSS | Lightweight npm packages, no JVM dependency (ruled out the W3C Nu Html Checker for that reason). |

**CI mechanism**: the existing single `.github/workflows/ci.yml` (not a separate workflow file)
carries a `web-changes` `dorny/paths-filter` gate job whose output feeds `if:` conditions on
`web-lint-and-typecheck` (ESLint + `tsc --noEmit` + html-validate + Stylelint) and `web-unit-tests`
(Vitest browser mode, `needs` both prior jobs) — deliberately not a second workflow file with its
own trigger-level `paths:` filter, which can leave a PR stuck on a required status check that never
fires because the whole workflow never triggered. Python CI keeps running only against its existing
paths (`src/`, `tests/`, `digital_twin/`, `pyproject.toml`, `scripts/`, `toolchain/`); web CI runs
only against `html/`, `js/`, `tests_js/`, plus its own config files (`package.json`,
ESLint/TS/Vitest/html-validate/Stylelint configs, `.nvmrc`). Root `.nvmrc` pins Node 22, read by
`actions/setup-node`'s `node-version-file` in CI.

Manual local-trigger instructions for the whole web-CI tier live in **README.md's "Website tooling
(JS/HTML/CSS)" section** (`npm ci` + `npm run lint`/`typecheck`/`lint:html`/`lint:css`/`test`) — the
JS-side equivalent of that same README's existing "Code quality tooling" section for Python.

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

- **Exact schema comment-tag grammar** — §11 is a worked *sketch* of the tag syntax against real
  `src/` driver schemas, documentation only, no parser built. It is a proposal to start from, not a
  final decision — actually settling it is reserved for a dedicated session, ideally paired with
  whichever driver session first touches a schema definition under this convention.
- **Build pipeline wiring** — see §10 item 4 for the confirmed current state of
  `scripts/build_frozen_html.sh`/`build-wozi.sh`/the toolchain's RP2 build, and the concrete gaps
  between that state and a real `html/`+`js/` build chain. Session 4's job (§10).
- **`dev.json`'s SHTC3/MPRLS/ISL29125 fields remain an unconfirmed projection** — these sensors
  have no real driver under `src/` yet. Resolves naturally once a future session promotes those
  drivers.

## 9. Sub-session working process

Each spun-off sub-session should follow CLAUDE.md's existing "Step-session workflow" working
agreement (refine scope → ask clarifying questions → tests first (TDD) → implementation →
more tests/coverage → stop and report before merging/starting the next unit) — this file supplies
the settled architecture/goals that step (1)'s scope-refinement can build on directly instead of
re-deriving, and step (2) only needs to raise what's still genuinely open (§8), not the questions
already answered in §4.

**Any decision that's a matter of taste/preference rather than derivable from §1–§4's settled
architecture** (visual/UX choices, color/typography/layout, and the like) needs the project owner's
interactive input, not a unilateral pick reported after the fact: present 2–4 concrete options via
`AskUserQuestion` at the point the decision is actually reached, rather than batching every such
question into the upfront round or guessing.

## 10. Sub-session breakdown (execution order)

**Standing instructions for every sub-session below** (in addition to §9's step-session workflow):
start with a detailed description of what it will do; ask 10 clarifying questions before starting
actual work; update this file before ending if anything settled changes or a new decision is made,
so the next sub-session reads current state, not stale state; **never touch `src/` files** —
website work stays confined to `html/`/`js/`/`tests_js/`/this plan/`SPECIFICATION.md`; a genuine
exception requires being raised and confirmed with the project owner first, every time, and is
never assumed from a past exception having been granted; do not build the schema-comment
autocreation tooling itself in this effort — only prepare hand-written example definitions file(s)
shaped as if they were auto-creatable. This effort's own local verification is JS-only (`npm run
lint`/`typecheck`/`lint:html`/`lint:css`/`test`) unless a confirmed `src/`-touching exception is
active for that session.

**Branching/PR requirement — applies to every sub-session, including the sessions spun off from
each of the five below:** each sub-session branches off **this base session's branch**,
`claude/sensor-website-redesign-w2juw6` (PR #42) — **never off `main`**. Its own pull request
targets `claude/sensor-website-redesign-w2juw6` as the base, not `main`; that PR only merges into
`main` once the whole multi-session effort is complete. Each session in the chain (2 off 1's
branch, 3 off 2's, etc.) follows the same rule against its immediate parent session's branch, not
against `main` or against this base branch directly, keeping the sessions stacked in execution
order.

1. **Folder structure + CI.** Create `html/`, `js/`, `tests_js/`, root `package.json`/tool configs,
   and the `changes`-gated web-CI tier in `ci.yml` (§5/§6). **Done** — `claude/website-s1-folder-ci`
   (PR #43).
2. **Layout & functionality definition, with a locally-viewable prototype.** Page/section design
   (nav, per-endpoint sections, history UI), the definitions JSON schema, hand-written example
   definitions file(s) against static/mocked fixture data for two differing devices (proving the
   "one skeleton/JS, content from definitions file" claim generalizes, not just for wozi), plus a
   documentation-only sketch of the eventual schema-comment tag grammar. **Done** —
   `claude/website-s2-layout-prototype` (PR #44). Settled decisions from this phase are recorded in
   §4; the tag-grammar sketch is §11.
3. **Real implementation, TDD.** A spec/goal/action list derived from the prototype; tests-first JS
   unit tests against that spec; then the implementation, hardening the prototype until the CI
   pipeline is fully green and coverage is maximized — mirroring this repo's own
   `improved-quality/` → `src/` two-phase precedent (prototype/sketch, then a from-spec,
   test-driven hardened build). **Done** — `claude/website-s3-tdd-implementation` (PR #45).
   Behavioral/architectural outcomes from this phase are recorded in §4/§4.2; current test/coverage
   state is verifiable directly (`npm test`/`npm run test:coverage`), not restated here.

   **Two confirmed `src/` exceptions occurred in this phase, both closed.** PR #47 (stacked on
   PR #45) fixed a numeric type-fidelity gap in `config_manager.py`'s `type_or_range_error()` that
   couldn't be fixed on the website side alone, since JSON/JS carry no int/float type distinction
   to preserve — the resulting policy is documented in SPECIFICATION.md Part A.8 (backend) and this
   file's §4 (the JS mirror); the reuse pattern it establishes is SPECIFICATION.md Part G. A second,
   separate change (on this base branch directly) fixed the settings-group result-swallow and
   `lightCmdLED` range-clamping gaps now recorded as current behavior in §4.2. Both were raised and
   confirmed with the project owner before being made. §10's standing "never touch `src/`"
   instruction applies to every session from here on exactly as written, with no expectation of a
   repeat.
4. **Full build chain.** **Done** — `claude/website-s4-build-chain`. Wires `html/`+`js/`+the
   definitions file(s) into a real gzip → `freezefs` → frozen bytecode → mount → serve pipeline,
   generic/parameterized per device, verified end-to-end for the `wozi` variant (the only one
   `src/` currently assembles — SPECIFICATION.md A.3). Its own project-owner-confirmed scope also
   grew to include a real `src/`-based `firmware.uf2` assembly script (originally an open scoping
   question this item itself raised — resolved "include it" before implementation started), so both
   pieces below landed in this one session.

   **What shipped:**
   - `scripts/build_frozen_html.sh`'s source-merge step is now a recursive `cp -r "$src_dir"/.
     "$tmp_dir"/` (was a flat, non-recursive `cp "$src_dir"/*`) plus a recursive `find ... -exec gzip
     -9`, so nested subdirectories (`html/definitions/`) survive the merge. Default behavior against
     `html_stub/` is unchanged — confirmed identical output, `tests/test_frozen_html_integration.py`
     still passes as-is.
   - `js/main.js` — the real production entry point (no mock install, no `?device=` switch; fetches
     a fixed `definitions.json` with no device segment, so no device string is baked into checked-in
     JS at all). `js/app.js` stays exactly as it was (prototype-only, used by `npm run preview`).
   - `scripts/build_website.sh <device> [output_path]` — stages exactly one device's real site
     (`html/index.html`, `html/style.css`, `html/definitions/<device>.json` renamed to
     `definitions.json`, and the production `js/` module set: `definitions.js`, `poll-manager.js`,
     `render.js`, `templates.js`, `nav.js`, plus `js/main.js` **renamed to `app.js`**) into a temp
     dir, then calls `build_frozen_html.sh` via `HTML_SRC_DIRS`. The `main.js` → `app.js` rename at
     staging time is deliberate: `html/index.html`'s one `<script>` tag imports `"../js/app.js"`
     unconditionally, and relative-URL resolution (browsers clamp `../` at the document root, and
     `fetch()`/inline-module-specifier resolution both key off the *document's* URL, not the
     importing module's own URL — confirmed by reasoning through the spec, not assumed) makes that
     exact same reference resolve correctly under both `npm run preview` (repo-root dev server,
     `js/app.js` is really the prototype) and the real frozen mount (`/js/app.js` is really
     `main.js`'s content) with **zero changes to `html/index.html`** either way.
     `js/mock-server.js` and `js/app.js` itself are deliberately never staged — dead weight against
     §3's "stays small, lean" goal, confirmed absent by `tests/test_website_build_integration.py`.
   - `tests/test_website_build_integration.py` — a new MicroPython Unix-port integration test
     (mirrors `test_frozen_html_integration.py`'s own pattern) proving the staged, real content
     mounts and serves correctly end to end: nested `js/*.js` paths, `definitions.json` at the root
     (not `definitions/<device>.json`), the real `main.js` content (not the prototype) at
     `/js/app.js`, and every prototype-only path (`/js/mock-server.js`, `/definitions/*.json`)
     404ing. `scripts/test.sh` now builds a second frozen module,
     `frozen_modules/frozen_website_wozi.py` (via `scripts/build_website.sh wozi ...`), alongside its
     existing `frozen_modules/frozen_html.py` (still built from `html_stub/`, unchanged) — the two
     never conflict since only this one new test file ever imports the website one.
   - `scripts/build_firmware.py <device> [--output PATH]` — a self-contained `uv run` script
     assembling a real `firmware.uf2` from `src/` + `ext/microdot.py` + the real website for one
     device. **Verified directly, not just written**: `uv run scripts/build_firmware.py wozi`
     produced a genuine, valid UF2 image (RP2040, 2078720 bytes, 4060 blocks) with zero
     errors/warnings against the toolchain this same session installed via `uv run
     toolchain/setup_toolchain.py setup`. Build-only, matching every other RP2 build this repo's
     tooling produces — nothing here flashes or tests real hardware.
     - **Why it needs its own `manifest.py`** rather than including the board's default one
       (`boards/RPI_PICO_W/manifest.py` → `boards/manifest.py`): that default manifest's own
       `freeze("$(PORT_DIR)/modules")` line freezes `ports/rp2/modules/_boot.py` under the exact
       frozen name `shared/runtime/pyexec.c`'s rp2 `main.c` looks up via
       `pyexec_frozen_module("_boot.py", ...)` at every boot (confirmed directly against the pinned
       v1.28.0 source). `src/`'s own real entry point needs a different `_boot.py` — one that mounts
       the filesystem (identical to the port's own stock logic) and then imports `wozi_boot`
       (`boot_entry/wozi_boot.py`) instead of anything from `ports/rp2/modules`. Freezing a second file
       under that same name would collide with/shadow the default manifest's own copy, so
       `build_firmware.py` skips including the board's default manifest entirely and re-states its
       other `require()`s verbatim (`bundle-networking`, `aioble`, `asyncio`, `onewire`, `ds18x20`,
       `dht`, `neopixel`) alongside its own single `freeze()` of a self-built staging directory
       (`src/*.py` flattened + `ext/microdot.py` + the real website frozen as `frozen_html.py`, so
       `src/sensortask_wozi.py`'s existing `import frozen_html` resolves with no code change + the new
       `_boot.py` + `boot_entry/wozi_boot.py` copied in unmodified).
     - **This repo's own top-level `modules/_boot.py` is never read, copied from, or touched** by
       this script — the new `_boot.py`'s content is the *port's own stock* content (from the
       toolchain's own MicroPython checkout) plus one added `import wozi_boot` line (no literal
       `.py` — unlike BACKLOG.md #1's still-unresolved legacy case, this is new code, free to do it
       the documented way). Fully consistent with CLAUDE.md's hard rule; no exception needed or
       raised, since the protected file itself is never in this script's path.
   - No `src/` files were touched or needed an exception — the whole build-chain effort (website
     wiring + firmware assembly) stayed within `html/`, `js/`, `tests_js/`, `scripts/`,
     `tests/test_website_build_integration.py`, and this plan.

   **Verification performed this session**: `npm run lint`/`typecheck`/`lint:html`/`lint:css`/`test`
   (607/607 Vitest tests across 9 files, including the new `main.test.js`) all clean; the full
   `scripts/test.sh` Python suite (real MicroPython Unix-port interpreter) run end to end including
   the two new/changed test files; a real `uv run scripts/build_firmware.py wozi` firmware build
   producing a valid `.uf2`. Pre-push verification (CLAUDE.md's clean-chroot recipe) was not run for
   this branch — nothing here touches `pyproject.toml`/`scripts/lint.sh`/`scripts/typecheck.sh`/
   `toolchain/versions.toml`'s own dev-tooling/build-environment setup in the sense that recipe
   gates; `scripts/build_frozen_html.sh`/`build_website.sh`/`build_firmware.py` are new/changed
   *build* scripts, not changes to the dev-tooling install path itself, and were verified directly
   against a real, freshly-installed toolchain in this session's own sandbox instead.
5. **Digital twin integration.** Replace `html_stub/` in `digital_twin/`'s wiring per §7; add real
   API-endpoint-driven tests (the website's actual JS/pages exercised against the twin's live
   server, likely via the same Playwright/Chromium foundation session 3 already set up, now against
   a live backend instead of static fixtures). **Tail of this session**: a manual cross-browser/
   cross-device spot check by the project owner (Safari, Firefox, real mobile) — automated CI only
   ever exercises Chromium via Playwright, so §1/§3's "stable and good-looking on all major
   browsers" goal needs at least one real human pass somewhere, and this is the first point the
   website is running end-to-end against a real live backend.

## 11. Schema comment-tag grammar — sketch (documentation only, not yet decided)

**Status: a worked proposal, not a decision.** §8 reserves actually settling this for a dedicated
future session, ideally paired with whichever driver session first touches a schema definition
under this convention. This section is a concrete, already-checked-against-real-code starting
sketch — no parser has been built and no `src/` file has been changed to produce it.

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

Project owner's explicit, standing requirement: the REST API and the overall concept are expected
to stay stable for a long time; the visual design is expected to be revisited — restyled,
reordered, regrouped — independently of that, more than once. **A purely visual/layout redesign
must never require editing data-fetching, validation, submission, or poll-coordination code.**

### The two layers

- **Visual layer** — owns colors, spacing, typography, dark-mode tokens (`html/style.css`) **and**
  DOM structure/order/nesting/CSS-class choices (`js/templates.js`). `js/templates.js` also owns
  any interactivity that's purely cosmetic and never touches the network or app state — a toggle
  button flipping its own On/Off label, an errcount rollup expanding/collapsing its own filtered
  module list. A redesign touches these two files (plus, for a schema/labeling change, the
  `definitions.json` content itself — §4.1) and nothing else.
- **Mechanics layer** — owns data fetching, polling coordination, input validation, PUT submission,
  and anything that calls the REST API or the poll-manager: `js/poll-manager.js`,
  `js/mock-server.js`, `js/definitions.js` (pure — no DOM code at all), and the non-presentational
  parts of `js/render.js`/`js/nav.js` (the controllers). None of these files build DOM elements,
  choose CSS classes, or decide element order/nesting.

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
| `[data-group-key]` | a field-group's card (both `buildFieldGroupCard()` and `buildErrcountGroup()` set it themselves) | `render.js` locates the card to re-render/restyle |
| `[data-field-wrapper-key]` | each field's own wrapper (distinct from `[data-field-key]`, which must keep pointing at the control itself) | `render.js` colors each field's own per-result outcome independently of the group card's own status |
| `[data-apply-status]` | *(unset by templates.js; only ever written by the controller)* | CSS alone decides what each status value looks like (`html/style.css`'s `[data-apply-status="…"]` rules), on both the group card and each field wrapper |
| `.apply-button` | the submit button | `render.js` attaches the real (networked) click handler |
| `.errcount-rollup .action-button` ("Show flagged"/"Show all") | `buildErrcountGroup()`'s two filter buttons | *(no controller involvement — purely cosmetic expand/collapse, wired entirely inside `js/templates.js` itself)* |
| `[data-section-key]` | each nav-drawer link | `nav.js` attaches the section-select click handler |

Controllers only ever set the semantic `data-apply-status` value (`"valid"`/`"invalid"`/
`"unchanged"`/`"failed"`) — never a color, class, or style directly. What that status *looks like*
is entirely `html/style.css`'s decision, so restyling what "invalid" means visually is a pure CSS
change.

**One deliberate exception to the "hooks are `data-*` attributes" rule**: `buildSectionShell()`
returns `{grid, errorBanner}` directly to its one caller (`render.js`'s `renderSection()`) rather
than making the controller look `errorBanner` up by attribute — there's only ever one error banner
per rendered section and it's handed back at the exact point it's created, so a lookup hook would
add indirection with no reuse benefit. The controller still only ever touches it the same two ways
`app.js`'s own app-level error banner does: toggling the `.hidden` utility class and setting
`.textContent` — never a color or custom style. Restyling what a fetch-error banner looks like is
still a pure `html/style.css` change (`.error-banner`), same as every other hook in this table.
