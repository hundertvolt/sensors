G2 hand-back: refusal bound (p1) and FRAM cancel safety. Commit 43d1a6b on audit/u35-g1b, not pushed. Steps 1-5 are done; step 6 is partly done (twin runs and the full reader set remain); one FRAM defect is handed back unfixed. Logs: S/u35/laneG/g2/b/.

**Step 1, premises (all hold)**
- `wrn_s()` → `_store_err()` counts and keeps the entry before its first await (asy_print_log.py:205-211, await at :217).
- `_write()` packs the whole live ring under `_write_lock`, and a cancelled write never sets `_written_gen` (:334-353), so the logger's next write by any caller lands the entry.
- After the trace, `_serve()` only returns, closes the writer and skips the decrement (asy_webserver_service.py:965-969). Nothing else depends on the trace having landed.

**Step 2, cancellation sweep** (new test in test_asy_fram_manager.py, `cancel_at_each_await` over `PrintLogHistoryStore.wrn_s`)
- After every cancel: CS deasserted, all four locks free, the entry in RAM, at most one block BUSY.
- A relaunch restores the old or the new state, logs the BUSY block and repairs it. The next write lands the entry.
- The test passed on 069b9fe at once, so I bit it with four scratch plants:
  - PA (block 1 marked BUSY up front): "blocks [0, 1] both left BUSY"
  - PB (bus lock kept on a cancel): "bus is still locked"
  - PC (a yield with CS asserted): "CS left asserted"
  - PD (entry kept only after a yield): "the entry cut short left RAM"
- **DEFECT, not fixed (firmware, asy_fram_manager.py:373-382):** `_write()` always writes block 0 and then block 1, whatever state the blocks are in. If one cut leaves block 1 BUSY and the next write is cut inside block 0, both blocks are BUSY. The relaunch's `_read()` then returns False and `setup()` overwrites the stored history.
  - Scratch sweep of every pair of cut points (`tools/two_cut.py`): 196 of 784 pairs lose the history on 069b9fe.
  - Proposed patch: a new `_first_block()` reads block 1's two status bytes (FRAM reads only, no wear) and writes block 1 first while it is not IDLE. Patched file: `S/u35/laneG/g2/b/plant_FIX/asy_fram_manager.py`. With it: 0 of 784 lost, and the sweep test passes.
  - p1 adds a cancel source to this path; the escalation bound and the outer cap already reach it. Whether to land the patch with or before p1 is yours.

**Step 3, p1** (test first)
- tests/test_asy_webserver_connections.py:633 failed on 069b9fe: (False, False, True), i.e. the socket was still open while the trace waited on the FRAM.
- p1 is in `_serve()`, bounded by `self._per_call_timeout_ms` (no new number), with the 2-line A.8 comment. The cut arm's comment says the entry survives in RAM.
- Bite: closing before the trace fails the "not sooner" bound (6 ms against 300).

**Step 4:** the escalation message now reads "its entry write did not finish within N ms and was cancelled". No test matched the old text; test_asy_system_service.py:3722 still passes.

**Step 5:** the client timeout sat below what the device owes an admitted connection (outer cap 15 s plus one flash hold, more than 10 s). New `_UART_LOAD_REQUEST_S = _OUTER_CAP_S + _FLASH_HOLD_MAX_MS/1000`, used only by the UART load's hammer, flusher and join. A refused connection is owed 5 s + 2.129 s.

**Step 6, proofs run** (all rc=0, zero memory markers)
- test_asy_fram_manager and test_asy_webserver_connections at -1, 32768 and settrace.
- test_asy_webserver_service and test_asy_system_service at both stages.
- 16 tests_scripts checks: the 12 standard ones plus scenarios, level_containment, timing_budget, request_timeout_ceiling.
- ruff and all four mypy passes are clean.
- mpy-cross: system_service is byte-identical to base once the old string is put back; webserver is +59 B.
- Times against 069b9fe: fram_manager went from 6.26 to 7.02 s at -1 and from 7.16 to 8.27 s at 32768, which is +12 to +15 %, **over the bar and open**. The cost is the fresh 8 KB fake chip in every fixture. A 256-byte part failed the chip's identification, so it was reverted. connections grew 1.28 to 1.68 s (+0.4 s, under the 0.5 s bar).

**Owed to the next block**
- test_sensortask on all 6 devices at both stages. The first runs died at import because build/generated_src was stale; I regenerated it, but they have not been re-run.
- The settrace run of the final connections file.
- The dev twin batch (`S/u35/laneG/g2/b/tools/twin_batch.sh`, ready, not started): uart_ring 3× per stage beside 4 burners, the webserver_concurrency family at both stages (test_digital_twin_webserver_concurrency.py no longer exists; the family replaced it), and the 4x plant once with p1 (`tools/plant4x.py` on a tree copy).
- The remaining tests_scripts readers (`git grep -l` gives 42 files).

**For D3**
- SPEC 6588 `con.http_call` and the `web.per_call_timeout_s` row (~11773) now also bound the refusal's trace.
- G1b's stale lines are still stale: SPEC 12216, 9785, 6588.

**Firmware question:** after an outer-cap or write timeout (asy_webserver_service.py around :944-950), the reclaim trace still waits with no bound before the close.

**Effect:** webserver in STA and AP on every device; Silent, Off and USB are unchanged. No flash or NVM write is added or changed.

nothing of mine is running