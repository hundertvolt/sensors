W1 hand-back (lane W, block 1). Commit `1b638f1` on `audit/u35-w` (worktree S/wt-u35w, from `f3fff0e`, rebuilt). Nothing is uncommitted. Nothing of mine is running. About 67 tool calls.

**Steps 174-179** were check-only, and all are already landed as P1d says: poll-manager.js:12-13, nav.js:38-50, shell.js historyOf/visibilityOf, main.js:39, app.js:92, poll-manager.test.js:8 and :191.

**Findings by verdict**
- OF-144, partly. js/shell.js `startShell()` takes `pageBuildDate` (null for a site built on its own). It reloads when GET /system's `build.BuildDate` differs from it, so a reflash between page load and the first watch is now seen. `buildDateOf(doc)` reads `<meta name="build-date">` and treats an empty stamp as none.
  - The change does nothing in production until the entries pass `pageBuildDate: buildDateOf(document)`: js/main.js:34-41 and js/app.js:87-94, plus the import. No lane holds those two files, so the lead must route them.
  - A reload loop cannot happen: build_firmware.py stamps one date into both page and module (test_build_firmware.py:79-82), `Cache-Control: no-cache` is set (src/asy_webserver_service.py:537), and the stager refuses a bad stamp (_stage_website.py:474-475).
  - Device behaviour is unchanged in every mode (STA, AP, Silent, Off, USB); only the page changes.
- OF-231, applied. In mock-data-compose.test.js the per-format checks are now one table (`FORMAT_PROBLEMS`). A test holds the table equal to js/definitions.js's `FIELD_FORMATS`, read as text. `epoch` gets its own check: a number or one of its special values.
- OF-214, partly. Every skip a run reaches is recorded. The file's last hook compares them with `EXPECTED_SKIPS`, which lists the six skips of a full run by case and reason. A new skip, or a listed case that ran, fails the file.
  - Not done: seeding the twin's config dir with offline-safe SSID and DNSFallback values. That code is tests_js/_live_matrix_command.js:60-62, in no lane. Seeding SSID would switch the matrix twin's boot from hotspot to STA for every case.
  - Once seeding lands, the two arzi rows come out; the hook's second check names them.
- UartHazards: the put matrix collects no status-section field except the ACTION_PROBES keys. So after the merge UartHazards gets no row and no skip; it is just not driven. I named it in the action-probe comment as bench-only and not driven here.
- OF-197, -199, -206, -207, -212: W2's (tests_scripts files).

**Seen failing first, and bites** (nothing planted was committed)
- shell.test.js:359: no reload with the compare switched off.
- No-reload cases: bitten twice (null guards dropped; the stamp always treated as stale).
- Meta reader: bitten by a wrong selector, and by `??` in place of `||` for the empty stamp.
- Compose: a format `planted` added to FIELD_FORMATS is named in the failure ("formats the compose check has no check for: [ 'planted' ]"). The epoch test fails with the old fall-through.
- Put matrix: run 1 with an empty list failed at :201, naming all six skips.

**Runs** (exits; RUNS.md lines for the put-matrix runs and the rebuild)
- rebuild 0.
- shell.test.js 20/20; compose 32/32.
- put-matrix: run 1 exit 1 (expected), 723 s; run 2 exit 0, 348 passed, 6 skipped, 726 s.
- `npm run lint` 0, `npm run typecheck` 0, lint-ceilings 4/4.
- The 12 commit checks plus website_layering and definitions_js_mirrors: 824 passed, 68 s.

**Times** (vitest duration, base to head, alternated): shell 3.07 → 3.28 s (+7 %), compose 1.05 → 1.11 s. Both are within the bars. Put-matrix has no base pair: each run takes 12 min. It is over 10 s and must not grow, so W2 should pair it in its web-tier run.

**Decisions (agent, 2026-10-21)**
- `pageBuildDate` is optional, so the entries' typecheck stays green.
- OF-231 is pinned on the JS side; test_definitions_js_mirrors.py needs no change for it.
- The skip hook judges only the decisions a run reaches (sharding, `-t`), with no floor.
- UartHazards is listed as not driven rather than probed.

**Scan** (all classes, the brief's modes)
- shell's swallowing `ignoreWatchFailure`: already covered.
- Stale cached site after a firmware change: this is OF-144, see above.
- Reload loop (class 6): bounded by construction; the empty stamp is fixed.
- The hook raising: seen working in run 1.

**Defects outside my set**
- tests_js/_put_field_cases.js:56: the comment "status's only field (ResetErrors) is dispatch-only" goes stale on dev after lane U merges.
- `readStringSetConst` (mock-data-compose.test.js) belongs in tests_js/_source_constants.js (Part G reuse).
- The put matrix's not-driven action list is only a comment; a checked map would catch a new dispatch key.

**Facts owed**
- X: no @tunable added or changed.
- Y: none.
- Lead: the main.js and app.js line above. ESLint maxima unchanged. No allow-list rows orphaned.

**W2's start state:** branch `audit/u35-w` at `1b638f1`. node_modules is a symlink to S/wt-u8/node_modules (lock hashes match). Its files are the seven tests_scripts files. Then: the web tier, the readers and the 17 scans.

**Logs:** S/u35/laneW/ (w1_shell_bite*.log, w1_compose_*.log, w1_putmatrix_first.log, w1_putmatrix_after.log, w1_checks.log, w1_time_*.log).