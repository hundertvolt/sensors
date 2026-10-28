D1 hand-back (lane D, U35). Branch `audit/u35-d`, worktree `S/wt-u35d`, head `31dc860`. Nothing is uncommitted and nothing of mine is running.
**Commits:** `5f97080` <PARTN> (Part N rows only); `31dc860` (tests_hardware/README.md and the SPEC sentences).
**Applied:**
- <PARTN>: the `l1.asy_notification_service_override_bound_ms` row is withdrawn and the `notify.loop_tick_s` row no longer names it. The `override_secs` row now states the pause's end in virtual time: no L1 measurement owed, margin one round, trigger the pause loop or the override API (agent, 2026-10-21). New row `l1.bus_fault_isolation_bound_s` = 5 s, site `tests/test_bus_hazard_multi_device.py` — `5`. Its basis is estimated (agent, 2026-10-21), measurement owed: the gather's L1 elapsed at both stages.
- Step 4: torn-write bullet after the chunk-reset-race bullet. It names `E FRAM_STATUS_BYTE` and `W FRAM_BLOCK_INVALID`, then save and clear, tagged (owner, 2026-09-13, paraphrase).
- Step 8: the lone-BMP3xx sub-bullet in the eighth pass now names `bmp3xx_alone_survives_a_general_call.py` and its flash test (L3, ungated, no write, no flash cycle) and the E.6.6 row. I kept the topology script's self-hazard reads, which still exist at `bus_topology_autodetect_and_hazard_sweep.py:105`.
- Step 9 (3) C.5, step 10 (1) C.8, step 116 (7) C.7, step 145 (b) (N.4 `loop.uart_call_span_max_us` "checked by" now names the flash test `test_uart_crossover.py`), the E.1 heavy-list clause from step 161, and :3794 changed to "(owner, 2026-09-18)", no meaning change.
**Landed already, no edit:** R-23. SPEC :8851-8865 already states Option 1. I checked it against `tests/_generated_module.py:36,93,120`, `tests/_uart_comm_harness.py:68`, `tests/test_asy_webserver_service.py:138` and the runner's `--debug-level`. The packet's "(6)" wording ("the memory-gated tiers run at ≥1") is overtaken by the owner's 2026-10-20 answer.
**Check-only on base, all landed:**
- 11: E.6.6 `flash-only-bus-checks` row, :5522.
- 13: C.14.1 "before `make_logger()`", :4301-4302; no `logger=` branch remains.
- 110: the response-writing-gap bullet, A.5 :522-532.
- 135: README :522-541, 12 habits each with its check; twin-first at :538.
**Deviations (agent, 2026-10-21):**
- Step 9's packet sentence, word for word, would have been false. `src/asy_config_manager.py` also catches an unknown key (:369, :443, `E CONTRACT`) and its flush task's end (:416, `E UNEXPECTED`), so the sentence names both.
- Step 116: the 8a45060 message gives the owner's direction in the agent's own words, so the quote is marked paraphrase. Step 4 had no quote source either (`audit/actions/SUPP_recovery.md:111`), so it is marked paraphrase too.
- Step 4's bullet is true only once H1's step 3 lands the allowed codes in `test_end_to_end_timing.py`; both merge at W6.
**Proof and expected red:** `test_tunables_register.py:253` (`test_the_tags_and_the_part_n_rows_agree`) holds exactly two lines:
- `tests/test_asy_notification_service.py:40: l1.asy_notification_service_override_bound_ms is tagged but has no SPECIFICATION.md Part N row` — waits on N2 (step 48);
- `SPECIFICATION.md:11865: l1.bus_fault_isolation_bound_s is a tuned row, but no file carries its @tunable tag` — waits on Y2 (step 76).
In a scratch copy of the tree with both tag changes planted, `check_tree()` returns `[]` (`S/u35/laneD/partn_proof.log`). Nothing was committed from it. No new tests in this block, so no seen-failing cases.
**Other checks:** citations, decision_vocabulary, legacy_paths, timing_budget, memory_catalog, lock_order, task_inventory and the README reader device_script_bench_facts are all green on `31dc860`. No allowlist row is orphaned. test_citations warns "datasheets/ submodule not initialised" in the worktree; that comes from the environment, not my change.
**Relay:** `<PARTN> 5f97080` under `## D`.
**Times** (pure-parse checks, nice 19, shared host): tunables_register 3.6 s, citations 11.0-18.8 s (still over the 10 s target W's OF-206 sets), decision_vocabulary 8.1-13.7 s, lock_order 4.4 s, the others 1.1-2.0 s. I changed no test file, so there are no paired times.
**Modes:** documentation only, so no effect in STA, AP, Silent, Off or USB on any device; the README entries concern dev's bench. Silent-failure scan: each new claim checked against code; nothing new found.
**Left for D2/D3, with what each waits on:**
- 34: Y4's planted-failure scenarios (the codec sentence too, if the tree holds it);
- 37 item 5: C's sweeps;
- 111: P1's relay line for E.5.1's register (steps 20/21) and the A.U35.41 table;
- 112: B1's step-108 run; 126: T's 125 (g); 128: 143, then its tests; 142: the A.U35.54 instruments;
- 143: <CORE> for "time at L1 is driven"; 144: U2's plant;
- 146, 147, 105's Basis cells, 162, 163: B2's measurements; 159: B2's sampler verdict (conditional);
- 158: every lane's build-environment changes (unit end);
- R-28's E.1: C2's guard outcome; R-9's J.6: P3's figures; R-8's FRAM sentence: P2.
**Defects found in other lanes' files:** none. Small note: P1d cites test_uart_crossover.py:135-136 for the verdict; at f3fff0e it is at :140-142.
**Logs and helper scripts:** `S/u35/laneD/` (steps_d1.txt, partn_*, c2_*, c3_*, end_*, end2_*, partn_proof.log; partn.py, readme48.py, spec_d1.py, reflow.py).