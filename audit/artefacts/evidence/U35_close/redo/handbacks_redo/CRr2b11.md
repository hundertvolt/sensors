CRr2b11 hand-back, written by the lane (2026-10-27 09:05 UTC)

U35 lane CRr2b11. Branch audit/u35-crr2b in S/wt-u35crr2b. It is still at 93c2dcbb and the tree is clean.

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad. Logs are in S/u35/laneC/crr2b11/.
- Every run went through run.sh (CRr2b10's wrapper with this lane's name): 6 runs, 12 RUNS.md lines naming "U35 lane CRr2b11", each with its done line.
- Nothing was refused. No stash, no nohup, S/u35/laneC/crr2b4/plant_i1 not touched.
- About 70 tool calls.

## Commits
None.
- Item 1 is proofs and set proposals; the sets are the lead's to edit.
- Item 2 found no defect, so nothing changes.
- Item 3 is not implemented, because both halves need a design call first (below).

## Item 1: the NTP sets

### The rerun on 93c2dcbb
Script: bites_ntp_rerun.py, log bites_ntp_rerun.log, 32/32 ok. It is CRr2b10's bites_ntp.py with each variant pinned to its commit:
- head = d8dfde93;
- newset = fc6f42a6 without the wait;
- new = fc6f42a6;
- lead = 93c2dcbb, added.

Results:
- The head, newset and new rows are byte-identical to CRr2b10's bites_ntp.log (diff in the run's own check), so nothing moved.
- lead equals new in every case but one. In case 8 ("false positive runs the chain to NTP_RETRIES") the own window now passes: "test=pass own=pass next=pass".

### The other sets naming NTP

**test_bus_concurrency_under_api_load.py, the flapping test (decorator :202-216): one entry missing, E NTP_RETRIES.**
- Source: src/asy_ntp_client.py:300-301, "Maximum retries reached, cancelling sync!", errno=_ERR_NTP_RETRIES.
- Path: this is the same path the set's mid-flight group already rests on.
  - A synced client's due resync (the NTPInterval cadence, asy_ntp_client.py:386-406) is under way at an ap_down() and fails.
  - That failure arms retry 1 (`_handle_ntp_sync_failure`, :283-296; synced only).
  - On the CYW43 false positive, `network_available_locked()` reads STAT_GOT_IP (asy_wifi_service.py:985-986), so retries 1-3 each run and fail. Their entries are all in the set already.
  - The fourth failure logs NTP_RETRIES at most 3 × (15 s `_NTP_RETRY_INTERV` + 14 s worst attempt) = 87 s after the first.
- Window against that bound:
  - On the false-positive path the link is dead, so `recover_by_reset` waits the full `_FLAP_RECOVERY_TIMEOUT_S` = 150 s (test file :77) before its reset.
  - The 18 s of flaps and the readers come on top of that.
  - 87 < 150, so the entry lands inside the window.
- Bite: bites_busflap.py, log bites_busflap.log, 8/8 ok.
  - Setup: the test's real body (`_flap`, `recover_by_reset`, `assert_no_task_ended`) on the same fake board in virtual time, with readers, SGP40 resets and the load floor stubbed.
  - Case 2 under HEAD: "own=FAIL(t logged NTP E70 NTP_RETRIES …)". Its entries are E71 at 1.1 s, E67 at 18/35/52 s and E70 at 52 s.
  - With the proposed set (HEAD plus the entry): own=pass, next=pass.
- Proposal: add `("NTP", "E", "NTP_RETRIES"),` after :215. Extend the reason the way 93c2dcbb did: "…, or its whole retry chain where the link still reads as up".

**No NTP entry missing in these four:**
- test_bus_concurrency_under_api_load.py's outage test (:155-160);
- test_network_resilience.py's blocked-port test (:262) and spoof test (:342);
- test_wifi_networking.py's blocked-port test (:97).

Why:
- **NTP_RETRIES is unreachable.**
  - Each test resets the board under its fault, inside `kick_then_reset` (harness.py:545-548), via reset_and_wait for :155 and :262 and the capture loop for :342 (:1093-1104).
  - Every boot starts unsynced (`_sync_loop`, asy_ntp_client.py:478), and an unsynced failure arms no retry (:283). The unsynced backoff (:395-398, :489-492) never logs NTP_RETRIES.
  - The window's one sync comes after the block lifts, and nothing fails after it.
  - The only synced stretch is the gap between `block_udp_ports` and the reset, which is one host call. A due resync there can only time out as NTP_NO_REPLY (named), and the reset kills any chain it arms.
- **The other codes are unreachable.** The fault is UDP 123 only:
  - the lookup answers, so no NTP_DNS*;
  - the request leaves the board (the DROP is on the bridge host), so no NTP_NOT_SENT;
  - no reply reaches the socket, so no UNSYNC_REPLY, MALFORMED or IMPLAUSIBLE.
  - The spoof is refused by the connected socket. Were it taken, it is a valid, plausible reply and the test fails on the year.
- **None ends with an attempt in flight, except the one reading below.** :155, :262 and :342 wait for ntp_synced after the unblock. Attempts are serial, so none is in flight once synced reads true.

Also checked, though outside the brief's list: the garbage-NTP test (:301), the garbage-DNS test (:315) and the NXDOMAIN test (:381). Nothing is missing, for the same unsynced-after-reset reason. :381 starts with `ntp_force_sync`, which clears Synced first (asy_ntp_client.py:575-579).
- That makes the section comment at test_network_resilience.py:371-374 stale. It says "Starting synced reaches _handle_ntp_sync_failure()'s ntp_issynced() branch, which nothing else does", but since the 2026-09-29 owner ruling, a settings change clears Synced before the attempt. Not edited.

### Spills, not set gaps (for the lead)
**The bus flapping test ends without CRr2b10's NTP wait.** Two bites show the next window failing under HEAD's set and the proposed set alike (bites_busflap.log):
- Case 3, the reset path: the boot sync fails once after serving, and the next window fails on E67.
- Case 4, the healthy path: a due resync's retry fails 5 s after the test's end, and the next window fails on E67.

The fix is the end wait test_network_resilience.py already has (`_wait_for_ntp_quiet`, from 950c3a83). Applying it here means moving it into `_load.py` with its two Part N rows. That is a test change, not a set change, so I did not make it unasked.

**One reading, not bitten: test_wifi_networking.py:97.**
- It unblocks after the 90 s tail and ends within about a second, without waiting for a sync.
- An attempt sent in the 5 s (`_NTP_FETCH_TIMEOUT_MS`, codegen.py:31-32) before the unblock logs NO_REPLY after the test's final clear.
- After the reset, the attempts come at T0, T0+20, T0+60 and T0+140 s. So this needs T0 between 25 and 30 s: narrow, but reachable on a slow association.
- Its siblings' `wait_until(ntp_synced)` would close it, at the cost of up to one backoff step of bench time.

## Item 2: E FRAM_STATUS_BYTE and W FRAM_BLOCK_INVALID

**Fresh state dirs, both stages (twin_drain_fresh.log, rc 0):**
- CRr2b10's twin_drain.py ran unchanged.
- The FRAM ring is counter 0 at -1 and at 32768.
- Every window passed. 0 memory markers.
- Both saved images decode all-IDLE (40 IDLE pairs and 2 blank).

**Boot over a run stopped mid-flight (twin_tear.py, twin_tear.log, rc 0; state in tear_state/):**
- Each try runs on a fresh dir: boot, run the console adversary load, join, then stop the twin at once. That is how CRr2b10's first run stopped: its script raised at the first request after the join, and its finally shut the twin down.
- The saved image is then decoded with the dev layout. The layout comes from tests/_sensortask_scenarios.py's own chunk walk (dump_layout.py, layout.json): 21 chunks, allocated 1140, which equals the twin image's `used`.
- Then the twin is booted again over that image, idle, and every ring is dumped.

| Try | Torn block in the saved image | Boot over it |
|---|---|---|
| -1, try 1 | WEBSERVER block 0 @1110, status pair (2, 2) = BUSY; its data equals block 1's | FRAM ring [E46, W63]. After that boot's own stop, every block is IDLE (repaired) |
| 32768, try 1 (the control) | none | FRAM ring empty |
| 32768, try 2 | WEBSERVER block 0, (2, 2) | FRAM ring [E46, W63] |

The entries appear if and only if a block was torn.

**Mechanism, from the code:**
- **The torn write** is the WEBSERVER logger's history write.
  - Chain: `PrintLogHistoryStore._write` (asy_print_log.py:333-354) → chunk `write_into` → `_write` (asy_fram_manager.py:365-394) → `_write_chunk(addr=-1)`. Block 1's pair read IDLE, so the first block written is block 0 (:400-408).
  - That call writes the BUSY pair (:410) and then yields (:411) before its payload.
- **Why the stop cuts it there.** The twin's stop file ends `_serve_until`. main()'s finally then cancels only the runner's tasks and main_task, and `_shutdown_cleanup()` → `flush_fram()` snapshots the chip synchronously (digital_twin/run_generic_integration.py:1166-1186, launch.py:346-349, machine.py:1354-1358). The product's connection tasks are never resumed, so a trace write suspended at that yield is saved as BUSY.
- **Where it was cut.** The torn block's payload equals the other copy's (counter 0x3c/0x3d in both). A history write always changes the counter (a call whose state already landed is skipped, asy_print_log.py:339-342), so the cut came before the payload, not after it.
- **Which check logs each code**, both on the next boot's `setup()` read through `_read` (:207):
  - E46 comes from `_set_check_sb` (:134-138), reached through `_read_chunk`'s `_handle_status_bytes(…, _STATUS_BUSY, check_idle=True)` (:272): status 2 is not IDLE.
  - `_read_into` then reports not valid, not blank and no fault (the status path sets no fault flag), so `_read` logs W63, "Invalid data in block 0, reading block 1" (:226).
  - It then repairs block 0 from block 1 (:239-243).
  - Both codes are logged by the manager's own RAM-only FRAM logger.

**Verdict: not a defect.** This is the firmware's correct report of a torn write.
- Every entry has a torn write behind it, and the control with none logged nothing.
- The tear is one the design says can happen. `_write_chunk` states that "one cut leaves at most one block not IDLE" (:397-398). Exactly one block was BUSY, its sibling was whole, and the read repaired from it, as W63's catalog text says.
- The twin's flush is a snapshot at an arbitrary instant. FRAM is non-volatile and the command sequence is the same on silicon, so a power cut, reset or watchdog at that instant would leave the same image, and the next boot would log the same pair.
- CRr2b10's 32768 entries were exactly this. Its crashed first run tore WEBSERVER's block, and the second run booted over the same dir. Its -1 dir happened not to be torn.

**Consequence for ad-hoc twin scripts:** a state dir reused after a stop under load can carry this pair into the next boot. Use a fresh dir per run, or read E46 plus W63 after a reused dir as this mechanism.

## Item 3: not implemented, two design findings
1. **The SCD30 sibling script (bus_concurrency_scd30_write_vs_siblings.py).**
   - Write sites: one owned NVM write among the reads, `set_temperature_offset(_WRITE_OFFSET_C)` (:75), and its restore after the gather (:88). These would stay unchanged.
   - b63be1b6's check transcribed as is (windows on all three Records, `overlapped_reads` > 0) would make the flash test fail on a healthy board whenever the one write starts in a sibling gap:
     - an SGP40 read holds its bus session for `_MEASURE_WAIT_MS` = 100 ms (asy_sgp40_driver.py:78, :708-711), and the loop then sleeps `_SIBLING_STEP_MS` = 15 ms (script :31);
     - the ISL reads are a few ms each;
     - so roughly 15 in 115 start instants meet no read: about one run in eight, from the src timings (silicon would give the exact rate).
   - The ISL test survives because it makes ten writes.
   - A sound fix needs the write's start aligned to a sibling round in flight, for example `read_loop` marking a round in flight and the writer waiting for an SGP40 round. That keeps the two NVM writes and their sites, but changes the shared `read_loop`.
   - `_overlapped()` would then move into `_shared/bus_reader_loops.py`, since two scripts would use it.
   - "Its two sibling scripts": the other two cross-device scripts already record windows and gate on `interleaved()` (flash test :124 and :187). Only this one lacks a check.
2. **The HTTP counterpart.**
   - The test is `test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load` (bench file :264).
   - Its readers GET /sensors, which answers `get_dict_cfg()` from each module (asy_webserver_service.py:644-649) with no I2C at all.
   - The ISL write's bus siblings are the DUT's own periodic reader tasks, whose windows no API exposes. Host-side request windows prove nothing about bus overlap, so b63be1b6's fix cannot be transcribed.

**Question for the owner (recommendation included):**
- For the SCD30 script, may the writer wait for an SGP40 round in flight, through a small change to the shared `read_loop`?
  - Recommendation: yes. It makes the overlap certain without adding NVM writes.
- For the HTTP counterpart, should the overlap proof stay with the flash tier, documented as such, while the bench tier proves the REST path's concurrency?
  - Recommendation: yes, rather than exposing reader timing from the firmware for a test.

## Checks
- No repo file changed, so no lint, typecheck or readers run was needed.
- The bites ran under the shared venv: rc 0, 32/32 and 8/8.
- The twin runs: both stages, rc 0, 0 memory markers.

nothing of mine is running
