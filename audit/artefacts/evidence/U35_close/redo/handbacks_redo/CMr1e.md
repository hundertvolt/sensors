CMr1e hand-back, saved by the lead from the message it sent (2026-10-27). Commit 02506cc5 on audit/u35-cmr1b (on f2fd7565).

CMr1e hand-back. Branch audit/u35-cmr1b in S/wt-u35cmr1b, one commit on f2fd7565, not pushed, nothing uncommitted. I stopped at a seam near 85 tool calls. Logs and scripts are in S/u35/laneC/cmr1e/.

**Commit 02506cc5: hot_replug made efficient (item 1, part)**
- **Cause, measured with per-function call counts and inclusive µs.** It is neither the twin's FRAM chip model (5-9 µs per transaction) nor its SPI fake (14-18 µs). Two costs dominate each ~2 s ladder:
  - **About 1.4 s in `poll()`.** With a ThreadSafeFlag registered, the Unix port waits 1 ms per scheduler round even for a zero timeout: `MICROPY_PY_SELECT_POSIX_OPTIMISATIONS (1)` (unix `mpconfigvariant_common.h:110`) leads to `modselect.c:353-370` with t = 1 ms (`:58`). rp2 keeps 0 (`py/mpconfig.h:1892`), polls once and returns (`:400-412`). Each round costs ~0.5-1.2 ms while a flag waits, against 2 µs for a bare poll.
  - **About 0.37 s in the CS settle.** `time.sleep_us(2)` (`src/asy_spi_driver.py:186,196`) costs ~95 µs on this host, ~4000 calls per run.
  - The round count comes from src: `src/asy_crc_checks.py:49` yields once per CRC byte. On silicon a yield is one cheap loop round, so I see no silicon finding.
- **Change.** New `digital_twin/unix_port_idle_poll.py`: `skip_idle_flag_polls()` skips only a zero-timeout round in which every registered stream is a clear ThreadSafeFlag. That is the one round whose poll can report nothing; every other round takes the real poll. hot_replug calls it at module level after the prewarm and the shim. digital_twin/README.md has the module's entry, its removal trigger, and the Known-gaps sentence updated.
  - Keeps: every wiring (8 replug runs, 2 power-cycle), every assertion, the real ladder and the real FRAM writes.
  - Skips: only the 1 ms waits of polls that find nothing.
  - The CS settle is left as is; it is not needed to reach base.
- **Equivalence**, at both stages:
  - A verifier ran the real C poll on every skipped round and asserted it woke nothing and left the IO map unchanged: 47,426 skipped rounds, 588 that took the poll.
  - FRAM bytes, write counters and the full SPI transaction log hash identical to runs without the skip.
  - The I2C log differs between two runs without the skip too, because the chips' random source is unseeded (`machine.py:367`), so it cannot serve as evidence.
- **Bite:** a copy that also skips when a flag is set fails 0/2 ("dev's BMP3XX never read - run_until ... 40000 ms").
- **Checks:** lint_direct rc=0; the three mypy passes clean from a cold cache; 26 readers, 1205 passed; hot_replug 2/2 at both stages, zero memory markers.

**Times in s, -1 / 32768.** No formal base/head/after pair was taken: the lead's mc_cov was still RUNNING throughout (RUNS.md:7590, no done line). These are lever checks at load ~2:
| File | base52 (CMr1d) | head (CMr1d) | after (mine, under load) | Status |
|---|---|---|---|---|
| hot_replug | 8.9 / 9.5 | 17.8 / 19.6 | 5.0 / 6.4 | ~44 % below base |
| ntp | 34.7 / 34.0 | 62.0 / 64.3 | unchanged | open |
| bus_hazard | 95.2 / 97.6 | 124.4 / 131.7 | unchanged | open |
- Owed: the formal back-to-back pair once mc_cov is done.

**Not done; state for the next block**
- **ntp.** The skip measured no gain (61.9 vs 62.5 s): the time is real product waits.
  - Growth: restore 14.2 -> 36.7 s (4 wirings), lost-sync 6.0 -> 10.6 s (2 wirings).
  - Per boot: first sync 1.3-1.9 s, SCD30 first reading 2.4-3.1 s, backup 0.93 s, failed attempt 2.2-2.9 s, restore 1.0-1.2 s (`until_ntp_skip.log`).
  - Lever found but not built: a driven clock over main(), the generated module, `digital_twin/unixport/_ntp_responder.py` (ipoll(0) plus a 10 ms sleep) and `asy_udp_socket` (ipoll(0) plus 20 ms sleeps under wait_for_ms). Loopback UDP is delivered inside sendto(), so the exchange should be deterministic in driven time.
  - Needs: clock_jump's `_DrivenWall` idiom (a third copy, a D.10 question for the lead), and `_until` on `clock.elapse`.
- **bus_hazard.** The skip measured no gain, per test within noise (`skip_bh_m1.log`). The brief's levers are still open: the start_tasks stagger on the driven clock (SCD30 test 23 s), the erase race (6 s), and the timed pause (7 s, not probed).
- **cmr1d items 3-5** not reached.

**Findings for the lead**
- The 1 ms tax hits every twin test with a waiting flag. Applying the skip suite-wide, or the C fix in `toolchain/micropython_overrides.py` (bound t by the timeout), is yours to decide.
- SPECIFICATION F.7 may want a row for this Unix-port gap; I did not edit SPEC.
- No unit test pins `_poll_unless_idle` on its own; the hot_replug bite is its only guard.

**Runs:** every CMr1e RUNS.md line has its done line (29/29). The lead's mc_cov is not mine.

nothing of mine is running
