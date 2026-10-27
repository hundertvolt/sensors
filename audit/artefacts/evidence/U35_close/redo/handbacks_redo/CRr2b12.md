CRr2b12 hand-back, written by the lane (2026-10-27 18:46 UTC)

U35 lane CRr2b12. Branch audit/u35-crr2b in S/wt-u35crr2b. Head 36387112, tree clean, nothing uncommitted.
S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad. Logs and bite scripts: S/u35/laneC/crr2b12/.
Every run went through that folder's run.sh (namespace, nice 19, disk check, RUNS.md lines naming "U35 lane CRr2b12"): 22 RUNNING lines, 22 done lines.
- The 18:11 harness restart cut one run, readers_i3. I wrote its done line by hand ("done 18:11 rc=killed (harness restart 18:11)") and ran it again in full.
- Nothing was refused. No stash, no push.
- The scratch copies are deleted: the plant tree and the three mypy caches.

## Commits (on 34cd5235)
| Commit | Item | What it does |
|---|---|---|
| 5931527f | 1 | `_wait_for_ntp_quiet()` moves to `_load.wait_for_ntp_quiet()` with its helpers, and the bus flapping test calls it. |
| 4a876ada | 2 | The blocked-port test in test_wifi_networking.py waits for NTPSynced before its NTP read and clear. The stale comment is fixed. |
| f9f75390 | 3 | The SCD30 sibling script: windows, `overlapped_reads`, the gated assertion, and the writer's round-head wait. |
| 36387112 | 4 | The ISL29125 bench write test's claim (section comment and README) now names what it proves. |

## Item 1: the NTP end wait (5931527f)
- **The move.** `wait_for_ntp_quiet()` and its helpers (`_ntp_retry_chain_s`, `_ntp_view`, plus `ntp_attempt_s()` and `ntp_fetch_timeout_s()`, now public) are in tests_hardware/bench/_load.py.
  - Callers: test_network_resilience.py's `_assert_recovered()` and the bus flapping test, which calls it after `recover_by_reset`. The spoof test now calls `_load.ntp_fetch_timeout_s()`.
- **Part N.**
  - The two rows moved: `l4.network_resilience_ntp_retry_chain_margin_s` and `l4.network_resilience_sync_age_slack_s` now name `_load.py` as their site. Their IDs are kept, so there is no meaning change. The margin row's Dependants now name the three tests the wait ends.
  - Two rows gained `_load.py` as a second site, same values: `l4.network_resilience_ntp_resync_after_reset_timeout_s` and `l4.network_resilience_wait_poll_s`.
- **Bite** (bites_item1.py, log bites_item1.log, 26/26 ok). It uses CRr2b11's fake board, run on 34cd5235's files ("head") and on the new tree ("new"), each module with its own `_load`.
  - The bus flapping cases 3 and 4 (CRr2b11's numbering) bite: under head the next window fails on E67; under new it passes.
  - The other bus cases and CRr2b11's 8 outage and flap cases: new gives the same result as head.
  - One case fails the test by design in both variants: "NTP never syncs" ends in a TimeoutError at the 120 s bound.

## Item 2: test_wifi_networking.py's blocked-port test (4a876ada)
- **Bite first, on HEAD's test** (bites_item2.py, logs bites_item2_head.log and bites_item2.log). The model: attempts at T0, then backoff steps of 20, 40, 80 s; a request sent while blocked logs NO_REPLY 5 s later.
  - With T0 = 27 s and 29.9 s, the next window fails on NTP E71.
  - Further reading: with T0 = 86 s (a slow association), HEAD's test fails itself, because `assert_module_logged_one_code` finds no entry yet.
- **The fix.** `wait_until(ntp_synced)` after `recover_by_reset`, before the NTP read.
  - Its bound is derived: the backoff step after the last attempt the 90 s tail can hold (80 s for dev, from src) + `ntp_attempt_s()` (14 s) + the new row `l4.wifi_networking_ntp_resync_margin_s` (10 s). That makes 104 s.
  - The retry period that both bench siblings carried moved into `_load.ntp_retry_period_s()`, which this bound reads too. No meaning change for the siblings.
- **Result: 12/12.** Under new, every case passes its own and the next window. The new bound case (the server stays unreachable) fails as designed, with a TimeoutError at 104 s.
- **The stale comment** above the garbage-NTPHost test at test_network_resilience.py:367-369 now says that `ntp_force_sync()` clears Synced first, so no retry timer is armed.

## Item 3: the SCD30 sibling script (f9f75390)
- **Shared code.**
  - `read_loop()` marks `Record.in_flight`.
  - `overlapped()` is in `_shared/bus_reader_loops.py`, and the ISL29125 script uses it.
- **The SCD30 script.**
  - Windows on all three Records.
  - The write's window is recorded and `overlapped_reads` is reported.
  - The fact `isl_windows` (a read count) is renamed `isl_reads`. The ISL29125 script uses `isl_windows` for its write windows.
  - The writer waits until both siblings have read, then for the head of an SGP40 round. Both waits share the existing 1000 ms deadline, now ticks-based.
- **The flash test** asserts `overlapped_reads > 0`. It stays gated by `persistence_write` and `scd30_extra_write`.
- **NVM writes: 2 before, 2 after**, at the same sites: `set_temperature_offset(_WRITE_OFFSET_C)` and its restore.
- **TwinBoard runs, both GC stages** (plants.log, twin_writers_*.log, twin_file_*.log):
  - Healthy: pass, `overlapped_reads` 2. The write starts in the same ms as an SGP40 round.
  - Siblings stopped before the write: FAIL at the new assertion (`overlapped_reads` 0). With that assertion removed it passes, so the check bites.
  - The whole flash file: 17 passed at each stage. The 3 failures are the twin record's silicon-only cases (INT edge, held SDA, FRAM CS hijack).
  - 0 memory markers in every log.
- **FINDING for the lead: the bite the brief names cannot exist.** A writer that does not wait still passes the check when it starts in a gap.
  - Gap plant: the write starts as an SGP40 round ends. Result: pass, `overlapped_reads` 2, at both stages.
  - Why: `set_temperature_offset()` holds the bus for `_CMD_RESPONSE_WAIT_MS` = 50 ms inside its session (`asy_scd30_driver.py` `_send_dev_command`). That is longer than the 15 ms sibling step, so the siblings' next rounds start inside the write's window.
  - So CRr2b11's estimate (about one run in eight with no overlap) treated the write as instant. The wait does not change the check's verdict.
- **What the wait does.** The SGP40's CRC staging yields per byte (`asy_crc_checks.py` `_crc()`), so the write begins inside the SGP40 session, ahead of its command. The command then waits on the bus. It does not land between command and read-back. The comment says so.
- **No check binds the wait.** Options, all test-only with no wear (CHECKLIST 1d, the lead's call):
  - (a) keep it as is;
  - (b) add a fact and an assertion that the write began inside an SGP40 round (the gap plant read False there);
  - (c) land it between command and read-back (a round start tick plus a delay longer than the staging);
  - (d) drop it.

## Item 4: the ISL29125 HTTP bench test (36387112)
- **What the text now says.** The section comment and the README entry say what the test proves: the REST path under load while PUT /sensors writes, with every write Valid, the readers' floor met with schema-sane bodies and the bus logs clean.
  - They point to the flash test's `overlapped_reads` for the overlap proof.
  - No assertion changed.
- **FINDING: "GET /sensors does no I2C" (CRr2b11, quoted in the lead's review) is wrong.**
  - ISL29125 and BMP3XX `_read_sensor_dict()` read chip registers.
  - SCD30 `_get_mgr_cfg()` reads its chip snapshot.
  - So the readers do put real i2c1 sibling reads (from the SCD30) beside the writes.
  - The conclusion still holds, because no host-side view shows an overlap. The text states the true mechanism.

## Checks on the final head 36387112
- Lint: `lint_direct.sh` is clean (ruff over the eight scopes and the generated tree, shellcheck, actionlint, zizmor, the method-assign guard, the gc sites).
- Typecheck: the mypy main and host passes were run per item and are clean.
- Readers: the tests_scripts readers were run per item.
- The whole tests_scripts tier: 6958 passed, 9 skipped, 3 failed (tier_final.log).
  - **test_host_text_encoding: pre-existing, not my file.** tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:318, `(SRC_DIR / _SGP40_SRC).read_text()`, has no `encoding="utf-8"`. It came from d8dfde93 (CRr2b9) and waits on that file's owner.
  - **test_twin_record ×2: expected.** The device scripts changed, and the record was already stale. twin_record.json was not edited.
- Silent-failure scan, all classes:
  - The NTP waits, `_ntp_view` and `ntp_synced` turn errors into a bounded TimeoutError (covered).
  - A failed sibling round is not counted in `overlapped()`, but `_no_errors` fails the test (covered).
  - New: the writer goes ahead unreported when its round-head wait meets the deadline. This is tied to the item 3 finding.

## Other notes
- **Latent: the retry period reads the src default.** `_load.ntp_retry_period_s()` (moved unchanged) reads src's `_DEFAULT_RETRY_S`, not the device's effective `ntp_retry_s` (`buildgen.validate.ntp_backoff`). dev states none, so the values agree today.
- **Modes and devices.** These are test-only changes for dev's bench (STA) and flash tiers. Firmware is untouched, so there is no product effect in AP, Silent, Off or USB.
- **Added bench time:**
  - The bus flapping test: one GET /status when NTP logged nothing; otherwise up to 97 s after serving (less once a newer sync shows), and up to 120 s on the reset path. In the bites: 0 s, 4 s, 14 s and 23 s.
  - The blocked-port test: the wait after the unblock is up to 80 s with dev's backoff, about 55 s when the first request goes out early. Its bound is 104 s.
  - The SCD30 flash test: at most one SGP40 round (about 115 ms) more. Its twin call took 6.3 s, with about 3 other heavy processes on the 4-core host.
- **Process.** The first date tags were written before my `date -u` call (17:59). The call confirmed 2026-10-27, so every tag is correct.

nothing of mine is running
