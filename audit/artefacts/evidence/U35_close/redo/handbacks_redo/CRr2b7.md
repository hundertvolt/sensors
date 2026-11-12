CRr2b7 hand-back, saved by the lead from the message it sent (2026-10-27). Commits 1a2226c6, 7e7451f5 on audit/u35-crr2b (on 4a2e3ddf).

U35 lane CRr2b7 hand-back. Items 1 and 2 are done, in two commits on audit/u35-crr2b. I stopped at a seam at about 80 tool calls. Items 3 and 4 are not started, so I have no bleed list and made no redflags.py change. Nothing is pushed and the tree is clean.

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad. Logs are in S/u35/laneC/crr2b7/. The before, after and source lines for each set are in S/u35/laneC/crr2b7/sets_map.txt. Every run went through S/u35/laneC/crr2b7/run.sh, a copy of CRr2b6's wrapper (own session, `timeout -k`, namespace, nice 19, disk check). Its RUNS.md lines read "U35 lane CRr2b7": 20 runs, each with a done line.

**Commits** (on 4a2e3ddf)
- 1a2226c6: the per-source heap test's set admits the entries a sieved config read and history write can persist.
- 7e7451f5: the UART hazard set no longer admits a responder size mismatch the run cannot produce.

**Item 1: serving_heap's set (1a2226c6)**

LOG_RAM_ONLY can land, so it joins the set:
- **The sieve:** every free run is at most k blocks while a probe runs (allocation_need_per_source.py:64-82, :110-126).
- **The entry itself:** its path only allocates frames (err_s, then `_store_err` asy_print_log.py:209-224, then `_write_through` :229-233), and RAM keeps the entry at :219 before any write.
- **The write allocates afresh inside `PrintLogHistoryStore._write`'s try (:344-357):**
  - a new chunk buffer on every call (asy_fram_manager.py:476-477);
  - its `bytearray`, whose failure is caught to None (asy_base_classes.py:155-163), so the write returns False at :347-348;
  - its memoryview (:171) and the `pack_into` star-call (:351);
  - the frames of `write_into` (fm :510-515), `_write` (:365-394) and `_write_chunk` (:396-427).
  - A MemoryError in any of these is caught at :355-357 and returns False. `_write_through` then keeps one LOG_RAM_ONLY (:236-239).
- **Why it can't be excluded:** nothing makes these allocations smaller than the entry's own frames. `_write_chunk`'s frame holds more state than err_s's, so a rung that fits the entry but not its write is possible.
- **How it persists:** rungs ascend and every probe runs at every rung, so the next WEBSERVER write that fits packs the whole ring, LOG_RAM_ONLY included (:232-233, :350-351).

**Find: the set CRr2b6 committed in 4a2e3ddf was missing entries the run actually leaves.**
- I ran the real script through TwinBoard, plus a scratch copy that dumps every module's ring after `_measure`, at gc.threshold -1 and 32768.
- Both stages leave BMP3XX E CHIP_GET (counter 4), ISL29125 E CHIP_GET (9) and SCD30 E CHIP_GET (10). All three loggers are FRAM-backed on dev (fram_names.log).
- **Where they come from:** a sieve's MemoryError inside the chip snapshot read, caught by `except Exception` at asy_bmp3xx_driver.py:311-316, asy_isl29125_driver.py:779-784 and asy_scd30_driver.py:340-345. They are reached through the cfg: probes and the /sensors route.
- **What else the twin showed:** no WEBSERVER entry at either stage. route:/status fails at rungs 1-8 before any guarded source, and passes from rung 10 on.
- Logs: twin_ramonly_c.log, twin_out_{-1,32768}_*.txt.

**Also added: src can produce these, the twin did not.**
- E CFG_GET_RAISED for BMP3XX, ISL29125, SCD30, SGP40, WIFI, NTP and NOTIFY (asy_base_classes.py:457-459).
  - The trigger is a MemoryError from `cfgmgr.get_dict`'s comprehension (asy_config_manager.py:448-451 catches KeyError only), or from SCD30's own `_get_mgr_cfg` (:247-259).
- E CFG_CALLBACK_RAISED for BMP3XX, ISL29125 and WIFI, the three that pass a callback (:472-474).
- These modules are probed through cfg: and through settings:networking/notification (build/generated_src/sensortask_dev.py:165-174). SYSTEM's `get_dict_cfg` (asy_system_service.py:650-654) catches nothing, so it logs no entry.
- **Your call:** these two codes are the wide side of the rule. Narrow them if you want only observed entries in the set.
- **Residual:** I did not enumerate the status:, data: and maintenance: probes' guarded sites line by line. The twin shows none of them logging at either stage.

**Set changed:**
- Before: WEBSERVER E CALLBACK, SYSTEM W CONFIG_LOST.
- After: those two, plus WEBSERVER E LOG_RAM_ONLY, CHIP_GET for 3 modules, CFG_GET_RAISED for 7 and CFG_CALLBACK_RAISED for 3 (16 entries).

**Bites** (bites_heapset.log, 7/7 ok, through the log check's own `assert_no_unprovoked_entry` on synthetic after-reads):
- The twin's three CHIP_GET entries, LOG_RAM_ONLY, and an SGP40 CFG_GET_RAISED each fail the old set and pass the new one.
- WEBSERVER E UNEXPECTED and an SGP40 CHIP_GET fail both.
- CALLBACK plus CONFIG_LOST, and an empty read, pass both.

**Item 2 (7e7451f5)**

**UART hazard set:** SIZE_MISMATCH cannot happen on the responder at any of its sites in asy_uart_comm.py, so I narrowed the set.
- :271 and :280 are in `_get_unlocked`, reached only from `_run_get` (:855). Its callers are gated to the initiator (:1104, :1115, :1128). The responder starts no exercise loop (asy_uart_link_driver.py:244-247) and refuses a hazard run (:284).
- :311 comes after the decline at :302-304. Every swept frame carries cmd id 0x07 (:47, :206), which `_set_callback` declines (:117-120). An accepted echo SET asks for no size (want -1, :305), and `_dest_size` returns the upper bound for want below 0 (:480-481), never None.
- :765 and :794 need an expected size of 0 or more (:763, :793). The responder's only train read (:314) passes -1.
- :784 writes into a buffer sized to the train's own bound (:313). The swept raw frames are first chunks only, never followed by data chunks.
- :1179 is `uart_set_into`, gated to the initiator (:1170).
- **Set changed:** I removed UART_resp E UART_SIZE_MISMATCH (17 entries became 16). The UART_init entry stays; I did not re-derive it.
- **Bites** (bites_uartset.log, 5/5 ok):
  - a responder SIZE_MISMATCH passes the old set and fails the new one;
  - the initiator's SIZE_MISMATCH, and the responder's frame, kind and decline codes, pass both;
  - WEBSERVER E UNEXPECTED fails both.

**test_an_incomplete_command:** I read `quiesce()` in full and CRr2b5's inference is confirmed. The set is unchanged (SYSTEM W CONFIG_LOST only).
- `quiesce` (fm :803-809) sets the pause (:764-767), then each chunk's `wait_idle` (:463-467) waits out the operation in flight.
- After that, every chunk write and clear is refused under the chunk's lock (:368-371, :440-443). Only `invalidate` (:451-461) skips the pause.
- The planted EIO raises out of `erase_chip`'s loop (:788-795, no try) into the shutdown handler (asy_system_service.py:494-497). That logs SYSTEM E UNEXPECTED, which stays RAM-only under the pause.
- Nothing reopens the pause before the watchdog reset:
  - the auto-unpause needs `_feed_owned` to be false (:523-527), and the shutdown sets it true (:405);
  - `pause_permanent_storage` refuses during a shutdown (:703-704).
- Every chunk was blanked before the failing unit (:776-781), so the production boot restores nothing and CONFIG_LOST (:753) cannot fire there. The set's CONFIG_LOST covers a failed invalidate, which leaves the scratch boot's entry in place.

**Checks** (checks_i1 and checks_i2 runs, the same result for both)
- lint_direct rc=0.
- mypy host rc=0. The main pass was not rerun: only host files changed.
- Readers: 1265 passed, 2 failed. Both failures are test_twin_record (the instruments with no entry, red at base, and the hash re-record).
- collect-only 201/232.
- review_rows `--check` rc=0.

**Times:** each twin run took 42-44 s (four runs per invocation). Each check pass took about 4.5 min. The bench gains no time, since only the markers changed.

**review_rows.py:** 8512 rows: CRr2 63, fixed 62, justified 128, biting 8259. The counts are unchanged; review.md was re-rendered for the shifted line numbers.

**Files whose twin record changes:** tests_hardware/bench/test_serving_heap_at_default_gc.py and tests_hardware/bench/test_uart_link_under_api_load.py.

**Not done:**
- Item 3: the calibration bleed (a bounded wait for W ISL_CAL_TIMEOUT or a published candidate, then the bleed scan), and redflags.py's decorator text.
- Item 4: the overlap fix in its two sibling scripts.

**Deletions:** the worktree's typings link, twice, each as its own literal-path rm. Nothing was refused, and I did not touch S/u35/laneC/crr2b4/plant_i1.

**Processes:** the pytest and twin processes still running when I finished have their working directory in S/wt-u35cmr1b, another lane's worktree, not mine.

nothing of mine is running
