
######## SubagentHandback 2026-10-13T15:50:43.810Z
WIP J1 5d668f5 (branch audit/u24-j, base e75d363). audit/u24-api1 is absent, so I have stopped as the brief says. Resume me on <API> for the rest.

What is in 5d668f5:
- Restores (steps 80, 81, 86, 93, 346, 348): new `tests_js/_test_setup.js` (real timers after every test), and `vitest.config.js` now has `restoreMocks: true` and `setupFiles`. I removed 20 restore lines in 8 files (poll-manager 12, shell 2, definitions, render, mock-server, accessibility, generated-definitions-render, site-functions 1 each). Kept: the two mid-test `useRealTimers()` calls (poll-manager, shell), mock-server's afterEach (per brief) and the two `finally` restores. app, main, nav and templates carry no restore, so nothing came out of them.
- Lint (step 91, J1 half): `require-description` (`ignore: []`) and `no-unlimited-disable` are on in all six ESLint blocks. `render.test.js:24` now has its reason. All 37 disables in the linted scopes carry a reason.
  - Deviation: the `no-console` comment text and the Node-context entries `_port_lock.js` and `_twin_process.js` move to the post-API commit. The comment still names the live-backend skip warning, which only goes then, and neither file exists yet.
- OF-137: in the mock, a PUT without `Content-Type` `application/json` (exact type before `;`, case-sensitive, as in `ext/microdot.py:463-474`) now gets code 1 and changes nothing.
  - Header-less PUT count: 61 in mock-server.test.js (the `putJson()` helper plus 60 direct fetches), not the ~40 the plan estimated, plus 1 in render.test.js. That render.test.js helper, `anotherClientWrites()`, now also asserts code 0, because HTTP 200 alone also passes a refused body.
- OF-138: `composeErrcountGroup()` now throws "mock samples: no sample for module ...". I checked all six devices first: none is missing a sample, so no `mockdata/samples.json` row was added.
- OF-143: `handleGet()` no longer writes `UnixTime` or `WifiTS` into a source that `isUnavailable()` reports.
- Step 64 is a guard: a new test drops each `_SYSTEM_CMDS` word in turn and checks that the mirror check fails. It passed at once, and it does go red when I weaken the check to a subset compare in a scratch copy.
- Verify-only steps:
  - in end form: 87 (`package.json:37`), 88 (all 9 `cross_browser_smoke.mjs` disables have a reason), 90 (`package-lock.json:11, 305`; `.nvmrc` is 24), 92 (`js/render.js` has no disable);
  - nothing at U24: 72 (`build_website.sh` untouched);
  - void: 82 (A.U24.56's site; `templates.test.js:1027-1028` already reads "(owner, 2026-08-21, `9fd2a28`)").

Step counts so far: 10 applied (one of them, step 91, partly), 1 guard (step 64), 5 confirmed in end form or void, 1 nothing at U24.

Seen failing first (logs in `S/u24/laneJ/`):
- Scratch restore test: "expected true to be false" on `vi.isFakeTimers()`, and the same failure on `vi.isMockFunction(console.error)` with HEAD's config.
- Planted bare disables: ESLint exited 0 (warnings only) on the current config; with the new rules, 9 errors.
- `render.test.js:24:0`: red under `require-description`, green once it has its reason.
- OF-137 (3 cases): `{res:'OK',code:0}` where `{res:'ERR',code:1}` was expected.
- OF-138: "expected [Function] to throw an error".
- OF-143 (2 cases): `{error:'unavailable', …(1)}` where exactly `{error:'unavailable'}` was expected.

Red check, not mine: the mypy host pass fails on the base itself. `scripts/_render_coverage.py:15: Unused "type: ignore" comment [unused-ignore]` on `import coverage`, because the coverage pin now installs it. That is lane S's file.

Facts owed:
- To X: H.8 (every disable names its rule and reason, enforced; restores after every test); H.4 mock paragraph (code 1 without the JSON type; no clock value in an unavailable marker); K.8 (the composer throws for an errcount module too).
- To Y: none yet.
- To the lead: PUT count 61+1; no samples row; ESLint maxima unchanged (a `max-depth` 5 was fixed by extracting a function, no ceiling raised); website input changed: `js/mock-server.js` (prototype-only, never staged).

Runs (all exited, nothing of mine is running):
- `rebuild.sh` twice: rc 0.
- 4 scratch vitest runs: results as above.
- Batch pid 1732, the 23 non-live vitest files one per process: all rc 0, 0 MemoryError lines, 3-17 s each.
- `npm run lint` and `npm run typecheck`: rc 0.
- Pre-commit pytest: 647 passed in 97 s. I wrote its RUNS.md line only at exit, which I've noted in that line.
- mypy host pass: rc 1, only the line above.

Record: the Write tool refused `S/u24/laneJ/report.md` (subagents may not write report files). Its content is in this hand-back; the evidence logs (`j1_vitest/results.tsv`, `*_seenfail.log`, `lint_*.log`, `precommit_j1.log`, `mypy_host_j1.log`) are in that folder.

Scan findings:
- Closed: OF-137, OF-138 and OF-143, plus a new one in `render.test.js`: `anotherClientWrites()` asserted HTTP 200 only (class 4, a check that matches too little).
- Checked, no finding: the mock's `putStatus()` refusal behaviour (OF-111 mode) is stateless by design.
- Not mine, reported only: comment blocks over the 3-line cap in `tsconfig.json:14-18`, `tsconfig.node.json:51-55` and `vitest-commands.d.ts:1-23`.

I have the lead's message about the live-backend fix: J1 did not touch `runLiveBackendConcurrentTabs`, `runLiveBackendRestartRecovery`, their describe blocks or their types.

######## SubagentHandback 2026-10-13T17:40:12.198Z
Lane J final: c6b9ea1 on audit/u24-j. It builds on WIP J1 5d668f5 and two merges: e5b29fc (api1 876bc9e) and 032eb4c (U23 fix 2ad4747). All of the U23 fix's guarantees are kept as written. Every run I started has exited; nothing of mine is running. Not pushed.

Steps: 21 applied (one of them a guard), 5 confirmed in end form or void, 1 nothing at U24.
- J1 (5d668f5), as handed back before: the restores, OF-137, OF-138 and OF-143, and the step 64 guard.
- Step 91: done in every ESLint block. The `no-console` comment now names only `js/render.js`, and both Node lists gain `_port_lock.js` and `_twin_process.js`.
- Steps 83, 85, 347, 349: `requireInterpreter()` throws `MISSING_INTERPRETER` from the three twin commands and from `getLiveMatrixConfig()`, which now returns `{shard}`. The `skipped` arm is gone from the types, from `live-backend.test.js` (header now says "...fails the suite; it never skips.") and from the put-matrix test, `it.skip` included.
- Steps 350 and 94: `tests_js/_port_lock.js` follows S1's contract verbatim, plus a per-process count for re-entry and a release at process exit.
  - `spawnTwin()` takes the 53 lock and `stopTwin()` releases it after the twin exits. The restart check holds it across both boots (`holdTwinPorts()`).
  - Deviation: `probePortLock` (the Commands API probe behind `port-lock.test.js`) lives in `_port_lock.js`, because the browser test reaches Node only through a command and no other Node-context file is in my set.
- Step 352: new `tests_js/_twin_process.js` holds the shared launch frame and the two tunable tags; it uses the U23 fix's `stopTwin()` for both modules. New `tests_js/_dom_helpers.js` is imported by render, templates, app and main.
  - The matrix's teardown and start-failure messages now go through `twinVerdict()`, so their wording changed slightly.
  - Left as their own copies because they behave differently: `accessibility.test.js`'s `mustQuery()` (it also checks `instanceof HTMLElement`) and `shell.test.js`'s `buildElements()` (five elements). `cross_browser_smoke.mjs` keeps its copies (U27).
- Step 354: re-pointed at `_twin_process.js`; its bite case is kept.
- Step 95: the loader's `staleAgainst()` checks the generator's TOML stamp, plus an L0 test that the loader and H1's stamp agree.
- Steps 353 and 109: `_pinned_node()` checks the Node major, and the three `unit-tests*` jobs get `setup-node@v7` with `node-version-file: .nvmrc` and no cache. actionlint and zizmor are clean.
- Lead item 2: the three comment blocks are cut to three lines. The actorless "deliberately" was dropped from the tsconfig sentence.
- Verify-only, as in WIP J1: 72 nothing at U24; 87, 88, 90, 92 in end form; 82 void.

Seen failing first:
- Port lock: missing module, then a no-lock stub made 11 of 14 cases fail (3 guards). Planted bites, each red: owner chain overwritten, a dead pid read as alive, no count. A dropped HELD check was silent until I added the "descendant whose chain lost the port" case; that case then went red.
- Missing interpreter (`PICO_TOOLCHAIN_DIR` pointed at a missing dir): live-backend 18 passed and the put-matrix file 1 skipped, both rc 0. After the change: 18 failed / the file fails, both with "MicroPython Unix port not built".
- Planted stale hash (`arzi`): the loader loaded it. After: "generated definitions missing or stale: run npm run build:site (arzi: changed since the tree was generated)".
- Node 22 first on PATH: the ceiling tests passed 10/10. After: "node v22.22.2 on PATH, .nvmrc pins 24 - run toolchain/setup_toolchain.py env or put the pinned Node first".
- Device-args check: red after the move ("no spawnTwin() definition - the twin launch moved, re-point this check", twice), green once re-pointed.

Red checks, both waiting on others:
- `test_decision_vocabulary.py::test_the_allowlist_only_shrinks` (lead): `_decision_vocab_allowlist.txt` rows 515 (one of the two identical matrix rows), 517, 526, 577, 578 are retired.
- `test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree` (X): `SPECIFICATION.md:10356` and `:10357` Sites change to `tests_js/_twin_process.js` (20000 and 15000 respectively) plus `scripts/cross_browser_smoke.mjs`.

Runs, all at nice 19, each vitest file in its own `ns_xdg` namespace:
- 24 non-live vitest files: all rc 0, 0 MemoryError lines. `port-lock.test.js` 15 passed in 7.0 s.
- `live-backend.test.js`: 18 passed in 222.2 s (U23: 167.6 s). Two other heavy runs were up; the per-tab cases took about 23 s each.
- Put-matrix shards: 242.1 s, 251.4 s and 242.7 s, all passed. The 2/2/1 skips are the file's own `ctx.skip` cases, not the interpreter skip.
- One shard loop I started while 4 other heavy runs were up was killed by pid and restarted behind a load gate; RUNS.md has both lines.
- Pre-commit pytest: 682 passed, 2 failed (the red checks above). mypy host pass: no issues in 206 files. npm lint and typecheck: rc 0.

Facts owed:
- X:
  - H.7: the live tier needs the built toolchain, all four commands throw, every twin holds the 53 lock and the restart check holds it across both boots.
  - E.1: the JS lock uses the same directory, files, message and owner chain; it is re-entrant with a count and released after the twin exits and at process exit. A node holder killed by a signal leaves a dead pid that the next taker takes over.
  - H.8, H.4 and K.8 as in WIP J1, plus the two Part N Sites changes above.
- Y: README's website-tooling section should say the live tier needs the toolchain built and fails, never skips. BACKLOG's chroot paragraph should say `unit-tests`, `-gc-threshold` and `-coverage` now set up .nvmrc's Node.
- Lead:
  - Allow-list rows above.
  - Header-less PUTs: 61 in `mock-server.test.js` plus 1 in `render.test.js`.
  - No samples row was needed, and the ESLint maxima did not move.
  - `tsconfig.node.json` `include` and `tsconfig.json` `exclude` gain `tests_js/_port_lock.js` and `tests_js/_twin_process.js`.
  - The only website-input change is J1's `js/mock-server.js`.

Silent-failure scan, closed in this lane:
- A missing build skipped the live tier green.
- A port another suite held was never checked.
- The loader accepted a stale tree.
- The ceiling tests ran on a Node of another major.
- `anotherClientWrites()` checked only HTTP 200.
- OF-137, OF-138 and OF-143.

Nothing else needs a fix. The mock's ResetErrors handling (`putStatus()`) is stateless by design, so the OF-111 mode does not apply. A signal-killed holder leaves a dead pid that the stale takeover handles.

The full record is this hand-back (the Write tool refused `report.md`); the logs are in `S/u24/laneJ/`.
