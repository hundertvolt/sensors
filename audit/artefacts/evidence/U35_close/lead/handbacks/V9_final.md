V9 hand-back (lane V, last block). Branch audit/u35-v9 in S/wt-u35v9, built on 0485607. One commit: 6b296df. Nothing pushed, nothing uncommitted, no typings link, nothing of mine running. About 64 tool calls, counted across the reboot. Only tests/_sensortask_scenarios.py changed.

**Verdict: the NTP no-reply part is applied on all six devices. The paired times ran. Growth is over 10 % on dev at 32768 and on wozi, so that item stays open.**
- New scenario `an_ntp_server_that_never_replies_spends_one_slot_and_a_reply_syncs_once_it_answers`. `_SilentNtpPeer` replaces `asy_ntp_client.UDPSocket` and is restored in finally, together with the RTC and utc_valid. The offline config's literal host means no DNS. The real `_sync_loop` runs 7 attempts. The scenario asserts:
  - each attempt logs exactly ("E", NTP_NO_REPLY), taken from `code()`;
  - ErrCount grows by the number of attempts, the code sits in one slot, chunk writes are above 0 and at most one per attempt;
  - the backoff doubles 20…600 and stays at the cap;
  - every attempt opens and closes its own socket to (host, 123);
  - once replies return, the next attempt syncs: Synced, age 0, the backoff reset, the RTC at 2026-01-01, and nothing more persisted.
  - The resync count stays out.
- Seen failing first: the scenario passed at once, so it is a guard. I bit it with scratch copies of src on the path (all deleted):
  - b1, no-reply log dropped: red at :2590 on dev and arzi;
  - b3, the backoff adds instead of doubling: red at :2593;
  - b2, `_reset_backoff()` dropped on success: red at :2595;
  - b4, the newest-entry rule off: red at :2591 (the one-slot check).
- **NAK storm made faster (V8's scenario; my file).** Each pass used to run a fixed 200 yields. It now waits on `_CountedFlag`, a ThreadSafeFlag subclass that counts its wait() calls, until every live loop is back at its wait. The loop driver moved into `_ReadLoops`, so the function stays under PLR0915's 73. The assertions are unchanged. V8's bite p2 is still red, at :2494.

**Times (s), base 2360470's scenarios file (vbase) against the head, alternating:**
- arzi 38.88→40.90 (+5.2 %) / 44.26→47.18 (+6.6 %).
- dev 60.11→65.47 (+8.9 %) / 72.97→80.98 (+11.0 %); the repeat was 68.28→76.29 (+11.7 %).
- grkizi 38.38→40.71 (+6.1 %) / 43.79→46.07 (+5.2 %).
- klkizi 38.54→40.57 (+5.3 %) / 44.26→46.57 (+5.2 %).
- schlafzi 38.25→39.94 (+4.4 %) / 43.54→46.21 (+6.1 %).
- wozi 42.45→46.70 (+10.0 %) / 47.91→52.91 (+10.4 %).
- Base dev is red at its own :3125 at both stages (the known LEAD NOTES 49 base red), so its status_get stops early.
- Per scenario on the head (ms, -1/32768):
  - NAK storm: 1580-1600/1700-1745 on arzi, grkizi, klkizi and schlafzi; 4121/4490 on dev; 2966/3189 on wozi. It was 4600-6500 before the change.
  - Refused storm: 159-245/196-344.
  - NTP no-reply: 197-284/238-375.
  - status_get's change: within noise.
- **Open, for the next block or the lead:**
  - On dev the NAK storm's storm phase alone takes about 3.2 s. That is real work in the readers' failure path, not yields: 7 passes × 4 readers, with SCD30 doing a soft reset.
  - dev at 32768 grows about 8 s, more than the scenario sum of about 5.2 s.
  - Neither is root-caused yet. Making it efficient means finding that cost. Cutting passes would weaken the check.

**Checks on 6b296df (c3b, re-run after the reboot):**
- ruff clean; all three mypy passes rc=0 (cold cache); D.15 shows only the known `@_register` line.
- The 12 checks, the 17 scans and the readers (device_tomls, digital_twin_ci_suite_errcount, import_placement, mypy_any_baseline, test_sh) ran in one pytest process: 1729 passed, 17 red. None names a file of mine: tunables_register, level_containment (D2), task_inventory ×4, lock_order ×9, twin_record ×2 (expected).
- c1 caught one red of mine: error_catalog :2550, a code compared through a literal. Fixed with `code()`.
- Zero MemoryError and zero "memory allocation failed" in every log.

**Decisions (agent, 2026-10-22):**
- The NTP attempts go through the real sync loop's trigger, not the refresh ticks, so the resync cadence stays out.
- The storm waits on a counted trigger instead of a fixed number of yields.

**Effect per mode:** tests only. STA, AP, Silent, Off and USB are unchanged on every device.

**Runs:** n1, the bites, e1-e4, t.sh, v.sh, v3.sh, c3b, p.sh and p2.sh, all with RUNS.md lines. The reboot cut off checks c3 and v3.sh; both have "terminated by the machine reboot" done lines. Logs are in S/u35/laneV/v9/: bite_*.log, p[bh]*_*.log, t[hbvw]_*.log, c3b_*.log, p.out, p2.out.
