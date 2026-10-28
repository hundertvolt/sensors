CRr2b4 hand-back, saved by the lead from the message it sent (2026-10-27). No commit; uncommitted work in S/wt-u35crr2b (audit/u35-crr2b at 575f8c22). Stopped on a refused command.

U35 lane CRr2b4 hand-back. I stopped early because a command was refused. Branch audit/u35-crr2b in S/wt-u35crr2b is still at 575f8c22. I made no commits and pushed nothing. The working tree is dirty: item 1's mechanism and its tests are uncommitted. Items 2 and 3 are not started. I used about 40 tool calls.

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad. Logs are in S/u35/laneC/crr2b4/.

**The refused command (I did not retry it)**
It was one Bash call doing two things:
- an inline python3 edit of tests_scripts/test_bench_log_check.py (to sharpen one test) and of S/u35/laneC/crr2b4/plants_i1.py (one plant's expected list);
- then `[ -d "$P" ] && rm -r "$P"`, which would delete my own plant tree S/u35/laneC/crr2b4/plant_i1.

The auto-mode classifier denied it as irreversible local destruction. Putting the deletion in a compound command was my mistake: the shell rule says a deletion is its own command. I believe nothing in that call ran, but I did not check. The plant tree S/u35/laneC/crr2b4/plant_i1 is still there. It holds a copy of tests_hardware, four tests_scripts files, and symlinks to the worktree.

**Uncommitted tree state, for whoever continues**
Three files changed (`git diff --stat`: 97 insertions, 20 deletions).

1. tests_hardware/error_log_helpers.py
   - `_CLEARS` is now a list of the parsed GET /status that `reset_all_error_logs()` reads before each PUT.
   - That read goes through a new `_saved_status()`, which `save_errcount` shares. So a clear still sends exactly one GET and one PUT.
   - The read is added to `_CLEARS` only after the PUT answers Valid.
   - `clears_made()` returns `len(_CLEARS)`. A new `reads_before_clears(since)` returns the reads after that point.
   - `assert_no_unprovoked_entry(before, after, test, *, pre_clear=(), expected=...)` checks each segment: before to the first pre-clear read as a continuing history, then each later segment as all-new. Each entry is named once.
   - One behaviour change: a /status without errcount now fails the clear before the PUT. The evidence is still saved first.
2. tests_hardware/bench/conftest.py: `_check` passes `reads_before_clears(window.clears)`, and the fixture's comment says so.
3. tests_scripts/test_bench_log_check.py: six new tests.
   - An entry logged then cleared inside an unmarked test fails it.
   - A clear with nothing before it passes.
   - A marked test's entry before its clear, inside its set, passes.
   - An entry before a clear but outside the set fails.
   - Every segment between two clears is checked, and each entry is named once.
   - A clear keeps the read it takes before its PUT, with exactly one GET and one PUT and one evidence file.

**Evidence so far**
- Red on 575f8c22: 4 failed, 39 passed (`i1_red.log`). The failures are the unmarked-cleared test, the outside-set test, the two-clear test and the keeps-the-read test. The two pass cases pass on base, as the brief requires.
- Green with the change: 43 passed (`i1_green.log`).
- Plants (`plants_i1.out`, `plants_i1.py`, `run_plants_i1.sh`): 7 of 9 checks caught, so the run ended rc=1.
  - Caught: plant 0 (575f8c22's fixture and helpers), pre-clear reads ignored, first segment read as cleared, no dedupe, read not kept, a second read for the check, read kept before the PUT answered.
  - Missed, "later segments read as continuing": an existing test does catch it (test_a_clear_through_the_helper_then_the_same_history_is_caught), but the expected list I gave the plant was wrong.
  - Missed, "only the last clear's segment": a real gap in my two-clear test, whose second pre-clear read still carried the first segment's entry.
  - The refused edit fixed both: an entry erased by the first clear (WIFI WLAN_TO_HOTSPOT in the first pre-clear read only), plus the corrected expected list.
- Not run yet: lint, mypy, the readers, collect-only.

**Item 1's sets: research done, none applied**
Do not commit the mechanism without these sets. Line numbers are on 575f8c22's src.

Tests that clear only at their start are already checked over their body today and need nothing new. These are the hotspot :198/:287/:304 tests, light congestion, the PUT size tests, full ceiling, page load, OpenHAB, the sensor config pushes, uart check_link/transfers, and http_soak.

Tests that log before a later clear:

*Bus load (test_bus_concurrency_under_api_load)*
The CEIL group below is WEBSERVER W HTTP_REFUSED (asy_webserver_service.py:925) plus W HTTP_PEER_RESET (:953). These arms run _GET_WORKERS+1 or +2 clients, two under the ceiling, and the module's own retrying fetch counts ceiling refusals.

| Test | Set |
|---|---|
| plain :90, ISL :226, BMP :273, SCD30 :323 | CEIL |
| light degradation :115 | CEIL + W HTTP_CALL_TIMEOUT (:348/:942) + W HTTP_REQUEST_CAP (:942) |
| NTP outage :143 | CEIL + NTP E NTP_NO_REPLY (asy_ntp_client.py:277) |
| WiFi flapping :184 | CEIL + CALL_TIMEOUT + REQUEST_CAP + W HTTP_SOCKET_ERROR (:945, a write after the link drops) + OUTAGE + the NTP mid-flight group |

*Other files*
- end_to_end :144: FRAM W FRAM_BLOCK_INVALID (asy_fram_manager.py:224) and E FRAM_STATUS_BYTE (:137). This is exactly the test's own allow-list.
- memory_stress :65: CEIL. It runs one reader per connection slot plus a VOC thread, and its comment calls the resets "reject-when-full".
- memory_stress :79 (extended): stays unmarked. It asserts every FRAM-backed logger empty itself. See finding 3.
- network_resilience :200, :228, :237: unmarked. `_impaired` asserts WEBSERVER empty, the section header establishes that no NTP exchange falls in these windows, and netem leaves the association alone.
- network_resilience :245: NTP E NTP_NO_REPLY.
- network_resilience :283: NTP W NTP_UNSYNC_REPLY (:324). See finding 2.
- network_resilience :297: NTP E NTP_DNS (:424).
- network_resilience :323: NTP E NTP_NO_REPLY.
- network_resilience :361: NTP E NTP_DNS_NXDOMAIN (:422).
- network_resilience :401: the OUTAGE group (WLAN_NO_AP :623, WLAN_AUTH_FAILED :620) + WIFI W WLAN_TO_HOTSPOT (:700) + W WLAN_SILENT (:697), the restore path's second streak. No NTP entries: an SSID change reconnects under wifi_mode_lock, and the AP goes down only while the DUT is in its hotspot.
- network_resilience :667: CFGMGR_BMP3XX E BAD_ARG (asy_config_manager.py:640) + WIFI E BAD_ARG (asy_wifi_service.py:300).
- network_resilience :708: WEBSERVER W HTTP_REQUEST_CAP (:942) only. The 3 s trickle stays 2 s under the per-call timeout by design.
- network_resilience :735: WEBSERVER W HTTP_PEER_RESET (:953) + W HTTP_SOCKET_ERROR (:945). The test itself names this race.

*The NTP mid-flight group (your ruling)*
- In: NTP E NTP_DNS_NOT_SENT (:420), E NTP_DNS (:424), E NTP_NOT_SENT (:270), E NTP_NO_REPLY (:277).
- Out, each with its reason:
  - NXDOMAIN :422, UNSYNC_REPLY, MALFORMED, IMPLAUSIBLE and ALLOC each need a reply.
  - NTP_RETRIES :301 needs four failed attempts 15 s apart, and the longest window is 18 s.
  - TIMER :298 is alarm-pool exhaustion.
  - SOCKET_TEARDOWN :275 and asy_dns_client.py:176 come from close/unregister, which do not depend on the link.
- It applies where a bench.ap_down() lands on a running STA link: network_resilience's two outage tests and the bus flapping test.
- It does not apply to the hotspot tests. Their OUTAGE entries come from connect attempts against a down AP, when network_available_locked() is already false.

Not yet re-derived: test_an_incomplete_command, the UART hazard run, serving_heap per-source, escalation, and stack exhaustion.

**Findings for the lead (nothing changed)**
1. test_wifi_networking.py:97 (test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing) is unmarked. It clears only at its start, then provokes and asserts NTP E NTP_NO_REPLY. It therefore already fails the existing after-read check, because CRr2b2 classed it as clearing at its end. It needs provokes_log with NTP E NTP_NO_REPLY.
2. network_resilience's NTP garbage test: _GARBAGE_PAYLOAD's first byte 0xff gives LI=3. So the client always logs W NTP_UNSYNC_REPLY (:324), and never the E NTP_MALFORMED/NTP_IMPLAUSIBLE its assertion names. The assertion passes only through its "Invalid NTP time received!" console-line alternative.
3. memory_stress's extended hammer runs one reader per connection slot plus a VOC thread, so one client more than the ceiling. Yet it asserts every FRAM-backed logger empty, and WEBSERVER is FRAM-backed on dev ([device.wiring] fram_target). HTTP_REFUSED (:925) is reachable there. I did not weaken it.

**Runs**
- i1_red rc=1 (expected red) and i1_green rc=0, both through run.sh, with RUNS.md lines.
- Deviation: the plant run (run_plants_i1.sh, copied from CRr2b3's) ran outside run.sh. It has no RUNS.md line and no namespace or session. It finished at once with rc=1, as reported above.
- Deletions: none.

**Not done**
- Item 1's sets and markers, the two plant fixes, the README "The bench log check" text (it still says a clear hides what came before it), the checks, and the commit.
- Items 2 and 3 entirely.
- There are no review_rows.py counts, since nothing was re-rendered. No twin-record file changed in a commit.

nothing of mine is running
