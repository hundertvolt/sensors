# Diagnosis unit: the bench's day-2 failures still open (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `dx5_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. The bench's log is the bench branch's
`audit/artefacts/evidence/U35_close/redo/hw_round1/HANDBACK.md` at commit `2745af2f` (read it with
`git -C S/wt-u35int show 2745af2f:<path>`; 26,985 lines: its table at the top, `### 5 bench_tier` from line 16758 is
the bench tier's newest run, image `c8887b35`). The current code is the integration tree `S/wt-u35int` (head
`c4f56186`). The bench ran on a Raspberry Pi 4; the board is the dev unit (RP2040, MicroPython 1.29.0).

## The bench's report (2026-11-06 09:20 UTC, relayed by the owner; its reading, not traced)
2. Teardown log check, 7 of 9 errors: SGP40 W65 SGP_NO_BACKUP, once with W35 SGP_WRITTEN_NO_TS and once with NTP E71
   ("likely each boot after an erase logs W65 until a backup exists, as 4b and run 5 erase FRAM"); W35 alone (socket
   limit test); WIFI W81 WLAN_NO_VERDICT (role flip back).
3. Possibly product: `test_loop_lag_under_http_load...` 967,405 us against 925,000 us (p99 64,000 us, 208 FRAM
   writes); `test_openhab_case` 7 IncompleteRead (/status and /measurements cut mid-body, e.g. 291 of 7,318 B), no
   reboot; `test_serving_sweep` at -1, N=8: 72 served, 11 refused, 13 ConnectionResetError (clean refusals expected),
   `test_concurrent_mixed_body_sizes` 2 ConnectionResetError; packet-fault tests: REST not back 30 s after corrupt 5 %
   cleared, not reachable within 60 s under delay 20 / duplicate 10 / reorder 25, packet loss logged WEBSERVER W49;
   the WEBSERVER log held 23 entries at session end, W60 among them, no E.
4. Likely test-side or downstream: `test_an_oversized_body` MemFree moved 10,624 B across a refused body; hotspot
   `test_malformed_http_request` expected W61, counter 0; `test_spoofed_off_subnet` tcpdump "never started";
   `test_ntp_recovers` mpremote reset failed (raw REPL), the three after it (rogue NTP, rogue DNS, UTCTime null)
   possibly downstream.

## What to answer (read-only)
For each failure: what the check expects, what the board did instead (from the log), and the root cause from the log
and the code: (a) a product defect, (b) a test assumption, (c) the bench environment, or (d) not decidable from what is
committed. Weigh item 3 first: whether the cut bodies and the resets are one mechanism, and whether the product's
serving path or the bench's network is it. Then for each: the smallest fix (test side: say it, file:line; `src/`:
propose it, never write it), or for (d) the one measurement or log the bench should take, worded so the owner can relay
it. Item 2 also against the owner's rule that an expected situation logs no error code, only a console line
(SPECIFICATION.md's logging rules): is a missing SGP40 backup right after an FRAM erase an expected situation?

## Never
Never edit any tree; never read `arduino/`; never open `/root/.claude/`. No hardware. Never weaken a check. At most four
runs, light ones, or heavy under `S/u35/lead/heavy.lock` one at a time (another unit uses the lock too: wait while it
exists). Never print, copy or write any Wi-Fi credential or the hotspot fallback password.

## Limits
Write only `S/u35r/r5/DX5.md` (and scratch under your own `ftmp/`). Budget about 0.8 % of the week. Hand back by
12:30 UTC.

## Hand-back
`S/u35r/r5/DX5.md`, at most 40 lines, and return its path: one line or two per failure (class, cause with file:line or
log line, fix or the measurement wanted). Last line: "nothing of mine is running".
