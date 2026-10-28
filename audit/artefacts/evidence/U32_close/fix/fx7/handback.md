FX7 hand-back (n = 7). Commit 0a9608f on branch audit/u32-fx7, in worktree S/wt-u32fx7, based on 34afa43 (FX5). Nothing is pushed, nothing is uncommitted, nothing of mine is running.

Step (rulings "RD-4's eight pairs", pair 8): applied. In src/asy_notification_service.py, `_trigger_signal()`'s try now holds only the `request_signal_cb` await. Its handler runs `report_if_fatal`, logs E CALLBACK and returns. The `NOTIFY_SIGNAL_DROPPED` warning now comes after the try, the same shape as `_safe_local_time()`. Every other path writes the same entries in the same order.

New test: `test_a_drop_warning_whose_own_logging_call_raises_is_not_logged_as_the_callbacks_failure`. The fake `wrn_s` stores the entry first, then raises `RuntimeError("injected console failure")`. The test expects one warning, no CALLBACK entry, and the raise leaving `_trigger_signal()`.
- Seen failing on the old src: `AssertionError: one drop warning only, got (2, 14)`, where 14 is E CALLBACK. Run twice: once before the fix, and again with the final test file next to a scratch copy of the 34afa43 module.
- The existing dispatch tests stay green: 68/68 at both GC stages.

Fault-or-warning scan: on 34afa43 it failed on 8 pairs. After the fix it still fails, now on exactly these 7 (pair 8 is gone); they wait on your rows:
  src/asy_base_classes.py _get_dict_cfg(): W CFG_KEYS then E CFG_GET_RAISED
  src/asy_captive_dns.py run(): W DNS_RECV_FAILED then E UNEXPECTED
  src/asy_captive_dns.py run(): W DNS_REPLY_DROPPED then E UNEXPECTED
  src/asy_webserver_service.py _serve(): W HTTP_BAD_HEAD then E UNEXPECTED
  src/asy_webserver_service.py _serve(): W HTTP_PEER_RESET then E UNEXPECTED
  src/asy_webserver_service.py _serve(): W HTTP_SOCKET_ERROR then E UNEXPECTED
  src/asy_webserver_service.py _serve(): W _WRN_HTTP_CALL_TIMEOUT if timed_out[0] else _WRN_HTTP_REQUEST_CAP then E UNEXPECTED

Effect per mode:
- STA (synced): reached when AutoOn is set, the time is in the window, a threshold is crossed and the NeoPixel refuses the request. Only one case changes: the warning's own logging call raising after its entry was stored. Before, that logged NOTIFY E CALLBACK and blamed the LED sink. Now the monitor task ends; within one 2 s pass the supervisor logs SYSTEM E TASK_RAISED under the task's name, records LastTaskEnd, restarts the task and charges 100 of the 300 budget.
- AP, Silent and Off (DEACTIVATED): the same, but only if the clock was set earlier this boot. Otherwise `_safe_local_time()` returns None, `_trigger_signal()` is never reached, and nothing changes.
- USB: the console print (asy_print_log.py:262-263) is where the raise can come from. Below DebugLevel 2 nothing prints, so only `_store_err()` could raise, with the same effect.

Runs (exit codes):
- Notification file, base: rc 0 at -1 and at 32768. After the fix: rc 0 at both stages. Times 19.07 -> 19.06 s at -1 and 19.10 -> 19.09 s at 32768.
- tests/test_sensortask.py six devices at -1, rc 0, 91/91 each. arzi 36.89 -> 29.47, dev 46.32 -> 46.96, grkizi 28.91 -> 29.04, klkizi 28.40 -> 29.06, schlafzi 28.94 -> 29.26, wozi 32.31 -> 33.08 s; none over 10 %. First try rc 1 (stale build/generated_src/ after the src edit); re-ran S/u23/rebuild.sh, then the six passed.
- One pytest process (17 scans, 12 commit checks, 10 readers of asy_notification_service.py, fault-or-warning): 2279 passed, 2 failed. Fault-or-warning red is the expected one above. test_decision_vocabulary red from own "# deliberate monkeypatch" comment; word removed, re-run rc 0. One warning: test_citations reports datasheets/ submodule not initialised.
- Zero memory markers. ruff clean. Both main mypy passes clean (cold cache, temporary typings symlink, removed). RUNS.md has start and exit lines. No allow-list rows needed from this block.

Silent-failure scan of both files, all classes:
- Class 4 and class 7 (fault logged as something else), every mode above: fixed by this commit.
- Fact owed to the lead (new, outside scope): src/asy_notification_service.py:225 calls `utc_now()` inside `_check_one()`'s try. On rp2 that allocates: `time.gmtime()` builds a tuple, and an epoch above 2^30 needs a heap integer (MPZ). A MemoryError there is logged as E SOURCE "Value read failed", blaming the producer. Only once the clock is set (STA, or AP/Silent/Off after a sync this boot).
- Facts owed to X and Y: none.

Logs are in S/u32/laneFX7/.
