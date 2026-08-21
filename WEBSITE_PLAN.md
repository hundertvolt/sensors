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

## 5. Folder structure

New source lives in **top-level siblings** of `src/`/`tests/` (matching the repo's existing flat
convention — `html_raw/`, `html_stub/`, `ext/`, `digital_twin/` are all top-level too, not nested):

```
html/            Hand-written HTML skeleton(s) + CSS - the new real website source
js/              Hand-written ES module JS source (poll-manager, API client, view renderers, ...)
tests_js/        JS unit tests (Vitest, see §6)
```

`package.json`/`package-lock.json` at repo root (dev-tooling only, `node_modules/` gitignored) —
mirrors `pyproject.toml`'s existing role: shipped code stays hand-written plain files, never
restructured into a build/bundle output. `html_raw/` (legacy, still deployed) and `html_stub/`
(placeholder, still wired into `src/sensortask_wozi.py` until this effort's output replaces it) are
untouched by this restructuring.

**Session 1 status: done, merged.** All three folders, `package.json`/`package-lock.json`, and
every tool config (§6) landed via `claude/website-s1-folder-ci` (PR #43, merged into this base
branch) — each folder holding only trivial "Hello world"-shaped placeholder content (mirroring
`html_stub/`'s own bootstrap role): `html/index.html`+`style.css`, one `js/hello.js` ES module, one
`tests_js/hello.test.js` Vitest browser-mode test. Confirmed via a real GitHub Actions run on the
PR (not just local): `web-changes`/`web-lint-and-typecheck`/`web-unit-tests` all green, existing
Python jobs unaffected. Manual local-trigger instructions for the whole web-CI tier now live in
**README.md's "Website tooling (JS/HTML/CSS)" section** (`npm ci` + `npm run lint`/`typecheck`/
`lint:html`/`lint:css`/`test`) — the JS-side equivalent of that same README's existing "Code
quality tooling" section for Python. Real layout/functionality is still session 2's job.

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

- **Exact schema comment-tag grammar** — §4 settled "lightweight inline tag syntax" in principle;
  the actual tag names/fields (label, unit, description, min/max, special values, category/grouping,
  ...) and precise syntax still need a dedicated session, ideally paired with whichever driver
  session first touches a schema definition under this convention.
- **Definitions JSON's actual schema/shape** — the concrete structure the build script emits and the
  JS consumes.
- **Real dark-mode support** — not explicitly settled; legacy has no `prefers-color-scheme` handling
  at all (see §2). Whether the redesign adds genuine adaptive theming or stays fixed-light is open.
- **Visual/interaction design specifics** — actual layout, the hamburger/three-dot menu's concrete
  behavior, card vs. other UI treatment, etc.
- **History pagination/truncation mechanism** — history size "may vary" (project owner's note); no
  mechanism chosen yet for bounding what's fetched/rendered.
- **Build pipeline wiring** — how `scripts/build_frozen_html.sh`/`HTML_SRC_DIRS` picks up `html/`
  (and the JS build/definitions-generation step) instead of/alongside `html_stub/`; whether the
  existing mechanism already covers this or needs extending.
- **Per-device page-scheme variation mechanism** — how the definitions file expresses "predefined
  page schemes, since sensor sets differ device to device" (arzi/neu vs dev vs wozi today).
- **Error/history endpoint-to-UI field mapping** — exact mapping from `/status`'s `errcount`
  sub-structure (SPECIFICATION.md A.8) into the history UI's counts/history-log split.

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
2. **Layout & functionality definition, with a locally-viewable prototype.** Detailed page/section
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
