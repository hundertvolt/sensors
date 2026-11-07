F1 hand-back (lane F, its only block; 58 tool calls). Commit 1d77560 on audit/u35-f (on 0547def), S/wt-u35f; touches only tests/_fake_time.py and tests/test_driven_time.py. Relay: `<SHIMFIX> 1d77560` under `## C` (relay.md:8). Nothing uncommitted; nothing of mine is running. Logs: S/u35/laneF/.

**Root cause** (read in the pinned v1.29.0 source)
- The shim's runner (tests/_fake_time.py:256 at 0547def, `if not wake.resumed and waiter.cancel():`) stood in for funcs.py:14 `if waiter.data is None:`. The two disagree in one window: after an external cancel, before the waiter resumes.
- In that window, `Task.cancel()` has taken the waiter off the wake's event queue (where event.py:31-33 parks it), pushed it onto the run queue (modasyncio.c:217-225) and set its data to `CancelledError` (:236).
  - funcs.py's runner sees data that is not None and leaves the waiter alone.
  - The shim's runner still saw `resumed` False. `waiter.cancel()` returned True a second time (:200, :226), and :257 overwrote the pending cancel with `CancelledError(True, result)`. `_wait_ms` :169 then returned the result, and the cancelled task ran on.
- Precondition: the awaited coroutine ends in the runner's first step, which runs between the cancel and the waiter's resume. Equal ticks pop in push order (py/pairheap.h:89, a stable heap).
- N1's case: `_overlay_loop` sets its flag (src/asy_neopixel_driver.py:87), so its `wait_for_ms(ThreadSafeFlag.wait())` (:92) ends at once (event.py:61-63). A probe showed the runner seeing `resumed False, data <class CancelledError>`.
  - The overlay swallowed the cancel and parked again, and its second flag wait went on the IO queue (event.py:62).
  - With the run queue empty and an IO wait listed, the loop blocks in `ipoll(-1)` (core.py:159-177): the idle hang.
  - Reproducer, old shim: with N1's 3 s bound, a TimeoutError at 3.09 s; unbounded, rc 124 at 10 s with 0.18 s of CPU. Fixed shim: True in 0.07 s and 0.08 s.

**Fix**
- The runner now cancels the waiter only while it still sleeps on its own wake: `data is None` (released; a push resets data, modasyncio.c:118) or `data is wake.event.waiting` (parked).
- The `_wait_ms` comment is restated (3 lines). One `# type: ignore[attr-defined]` with a reason, since no stub declares `Event.waiting`.
- Test-only: no effect on any device or mode (STA, AP, Silent, Off, USB).

**Seen failing and bites** (all rc 1, memory markers 0, at both stages)
- New test `test_a_cancel_landing_before_the_runner_runs_still_cancels_the_wait` (real asyncio and driven): failed on the old shim at test_driven_time.py:245, "AssertionError: returned 7".
- Guard `test_a_result_ready_before_its_released_bound_has_run_still_wins`: dropping `data is None` gives TimeoutError.
- Dropping the parked clause: `test_wait_for_hands_back...` fails with TimeoutError.
- C1's seven plants (elapse ±1, jump ms-1, run_until limit+1 and >=limit, wait_for_ms ±1): each still caught.
- My first 32768 bite pass was invalid: the threshold runner loaded tests/ ahead of the bite. Re-run with the runner copied beside each bite: all caught.

**Decisions (agent, 2026-10-21)**
- The positive "still asleep" test, rather than "no cancel pending": the same over every reachable state, and it never cancels a waiter in an unforeseen state.
- `not wake.resumed` is kept. It leaves the shim stricter than funcs.py:14 for a waiter that caught its own cancel and moved into a sleep, where the real runner would cancel it again. No src site does that; asy_system_service.py:305/432/450 each catch an awaited child's ending.
- A draft 1 ms real sleep in the new test was dropped: the order rests on the stable heap.

**Sites with the shape** (git grep on audit/u35-*, read only): a driven wait_for whose awaited coroutine can end in its first step. Only N1's site actually hung; the others need nothing but the `<SHIMFIX>` merge.
- n: src/asy_neopixel_driver.py:92, on every start, via tests/test_asy_neopixel_driver.py:46 `_driven()`. The window is `_start_all_tasks` (:1088-1092) followed by `cancel_all`. N1's setup test (:880-886) stayed on the real asyncio and can move to the driven clock after the merge.
- c, e, f, g, q: src/asy_udp_socket.py:132. `_poll` returns at once when ipoll(0) already reports the mask (:110-112) or the poller is None (:108-109). It is reached by tests/_cancel_sweep.py:84-88's per-turn cancels: test_asy_udp_socket.py on all five, plus the test_asy_dns_client.py and test_asy_ntp_client.py sweeps on c.
- c, e, f, g, q: src/asy_webserver_service.py:333 and :342 (stream calls on buffered data), :734 (`wait_closed`) and :917 (`handle_request`), via tests/test_asy_webserver_connections.py. Its one cancel (:885) comes after a settled wait, outside the window.
- d, p, t: no driven module. u, v, y: only test_driven_time.py and test_shared_helpers.py:476 (`tick()` over a flag waiter, no wait_for): no site.

**Silent-failure scan** (all classes; modes "a fake that answers where silicon raises" and "a swallow that hides an early raise")
- tests/_fake_time.py:256 at 0547def: class 4, fixed by 1d77560.
- The `resumed` strictness above: class 4, new, kept by decision.

**Checks**
- ruff 0.16.10 clean. mypy 2.4.0 clean in both passes (264 and 230 files); the temporary typings link is removed.
- One pytest over the 17 final scans, the 12 pre-commit checks, microtest and ticks_wrap_scan: 1014 passed. Its one warning: the datasheets submodule is not initialised.
- After the last edit (a comment only), citations, decision_vocabulary, comment_block_cap, suppression_form and code_conventions: 698 passed.
- No red checks, no orphaned allowlist rows, no tags.

**Runs** (RUNS.md lines written; no retries)
- All 22 `_fake_time` importers on the head at -1 and 32768 (pid 7169): 44/44 rc 0, zero memory markers. The wall-time-bound files each started at no more than 3 heavy processes.
- Head times, -1/32768: system 25.3/26.8, wifi 24.5/25.0, ntp 24.1/24.4, scd30 22.2/29.2, notification 19.1/19.1, bmp3xx 13.9/14.0, sgp40 8.5/9.3, ntp_fram_system 7.6/7.7, neopixel 7.3/7.3, fram_manager 5.5/6.6, udp 5.9/6.0; the rest 4.5 s or less.
- test_driven_time after-only: 0.06/0.06 s, 19/19.
