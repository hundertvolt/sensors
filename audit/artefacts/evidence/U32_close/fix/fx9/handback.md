FX9 hand-back. Commit 438e8fa "U32 fix: let the shell tests wait for a watch to settle before advancing time" is on audit/u32-fx9 (from c6b8a07) in S/wt-u8. The tree is clean, nothing is pushed, nothing uncommitted, and nothing of mine is running.

Root cause: the test was wrong; js/shell.js and js/poll-manager.js do what their contract says. Your hypothesis holds, and the thing fake timers do not drive is the Response body read.
- startPolling's tick() schedules the next watch only in `finally`, after `await pollOnce()` (js/poll-manager.js:155, :169). watchOnce ends with the /system read (js/shell.js:100), whose body read is `response.text()` (js/poll-manager.js:88).
- A probe showed that in this Chromium `Response.text()` resolves in a task of its own: a 20000-hop microtask chain finished before it did (probe2_1.log:88).
- vitest's tickAsync waits one real setTimeout (node_modules/vitest/dist/chunks/index.C4tKZ0yW.js:6047), then fires the fake timers in range (:5812-5840). A watch still reading at that point has no timer in range. The first timer that fires is its request's 15 s timeout (poll-manager.js:75), so the aborted watch backs off to +75 s; otherwise the watch settles after the advance and lands at +120 s. waitFor then advances only 50 ms per check, at most 1 s in all (:7160), so it never gets there: "expected 1 to be 2".
- The target test advanced straight after start(), with three chained reads (/status, /measurements, /system) still to go. Under load the real setTimeout's deadline passes between those read tasks, and the advance wins.
- The sibling's pattern (waitFor count("/system")) only waits for the request to be sent, so one read task is still open. It is the same race, just narrower.
- One natural failure in plain mode as well, on the unmodified test, same message: probe2_1.log:112. So it is not specific to coverage.

Deterministic proof (throwaway, reverted; variants in S/u32/fx9/variants/): I delayed every /system body read by 100 ms of real time.
- Old file: 5/5 runs (3 plain, 2 coverage) fail the same 4 tests. The target fails at :316 with the gate's exact message; "reloads once…" at :300 (reload called 0 times); "shows ages…" at :375 (1 to be 2); "defers a reload…" at :416 (statusCalls 1 to be 2).
- Fixed file with the same delay: 5/5 runs, 15/15 passed.

Fix (tests_js/shell.test.js only):
- installFetchStub gains `read(path)`, which counts the /status and /system answers whose body the shell has read. It only observes; the shell still gets the original promise.
- Each affected test now waits for `read("/system")` before relying on the next watch: line 315 ("reloads once…"); lines 334, 337 and 341 (target: before both advances and before `not.toHaveBeenCalled`, whose no-build half could pass before the third answer was ever read); 395 ("shows ages…"); 438 ("defers…").
- Line 351 ("pauses…") never failed, but it hid the page mid-read, so which pause path it tested varied from run to run. It now always tests the pending-timer path.
- Every assertion is kept; no timeout, retry or bound was changed.

Sweep (all 38 timer advances in tests_js/): the only instances are the ones above, all in shell.test.js. The rest are safe because their timers are set synchronously or in microtasks:
- shell :266 (stop's abort settles in microtasks), :345 (a rejected /system settles in microtasks), :379 (every read is done by then), :444 (the retry timer is set in the same microtask drain that sends /system);
- poll-manager.test.js :188/:208/:227/:243 (227 stops at 999 ms, before the timeout) and startPolling's 20 advances;
- mock-server.test.js :754/:756 (its delay timer is set synchronously, js/mock-server.js:653);
- definitions.test.js :376.

Runs (all inside `unshare -n` with ns_xdg.sh and nice -n 19; logs in S/u32/fx9/; zero memory markers):
- shell.test.js alone, before the fix: 10 plain and 10 coverage, all rc=0, 15/15. After: the same, all rc=0, 15/15.
- lint-ceilings.test.js: rc=0, 4/4.
- On 438e8fa: whole `npm test` rc=0, 1655 passed and 6 skipped (the same live-PUT-matrix skips as the gate). Whole `npm run test:coverage` rc=0, 1307/1307. `npm run lint` rc=0, `npm run typecheck` rc=0.
- The 12 tests_scripts checks: 792 passed. The one warning is environmental: the datasheets submodule is not initialised in this worktree.
- shell.test.js wall time: 11–16 s before, 10–13 s after.

Deviations: one lint/typecheck pair before the commit ran outside unshare (both rc=0); I repeated them inside unshare on the head. I removed build/generated_html before the whole-suite runs (checklist item 13).

Silent-failure scan: nothing found. The rejection handler on the read counter swallows only its own observer branch, and a counter that never counts fails its waitFor loudly.

Facts owed, to the lead: in tests_js, a count of /system requests means the request was sent, not that the watch has settled. Before advancing fake time, wait for the read. Nothing owed to X or Y.
