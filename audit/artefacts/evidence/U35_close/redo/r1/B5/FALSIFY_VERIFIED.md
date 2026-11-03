# B5 falsification, verified at the source (lead, 2026-11-03)

Each refutation in `FALSIFY.md` read against `21e12c76`, `3129bf21`, `25caf528` and `ACTION_LIST.md`.

- Claim 5 holds as the brief meant it: the LI/stratum check before the length and zero checks is the pre-audit order
  (`25caf528:src/asy_ntp_client.py:245-252`), restored by item 5; a short reply with LI 3 or stratum 0 logs W40 and sets
  nothing, as before the audit. The brief's wording was too wide. No change.
- Claim 6 (a) CONFIRMED: `_refresh_loop()` (`asy_ntp_client.py:318-327`) counts ticks while an attempt runs with
  `_retry_wait_s` still 10 (after `_reset_backoff()`), sets the trigger, and `_sync_loop()` (:404) raises the wait to 60
  only after the failure, so the next attempt runs at once. Against item 19 (owner, 06:54): fix (F2).
- Claim 6 (b) CONFIRMED: SPECIFICATION.md:11188-11189 lists three removed rule ids. Fix (F3).
- Claim 11 holds as the brief meant it: `ready()` awaits `_connect()` before `t0` at `25caf528` too (`:130-133`), and
  no shipped caller passes a deadline under 500 ms. No change.
- Claim 14: the WS-20 weakening is CONFIRMED (REVIEW.md had it: revert, F1). The other removed tests follow action-list
  items the claims did not name: captive `:183`/`:254` and NTP `:1113`/`:1121`, DNS `:338`/`:344` are item 8's listed
  tests; the two W12 teardown tests follow item 7 (W12 stays at captive DNS only); `_NTP_REQUEST`'s test follows item
  18's NTP-7 (`3129bf21:src/asy_ntp_client.py:87`). No change.
- Outside 1 (twin README Run 9), 2 (`_ntp_responder.py:20`) and 3 (SPECIFICATION.md:4054's per-setup cost): stale docs,
  fix (F4-F6). Outside 4 and 5 follow items 8 and 7; 6 is the pre-audit catch of items 4 and 13; 7 is pre-audit (one
  `start_server()`, as `25caf528`); 8 is unreachable (generated `_DNS_TRIES` 1). Accepted, no change.
