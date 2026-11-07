D2b hand-back (lane D, U35). Branch `audit/u35-d2` in S/wt-u35d2. One commit, `8fa324f`, on top of `5d0e16f`. It changes only SPECIFICATION.md and BACKLOG.md. Nothing is uncommitted and nothing is pushed.

**What landed:** every `## D` relay line that was D2b's, each fact checked against the tree first.
- **C4:** A.8 now has `UTCTime` per `ntp_clock_valid()`, plus `TimeStale` with the owner's words, the question and option (b). The flag's form is logged as (agent, 2026-10-21). F.1's gate sentence is rewritten. The `SgpBackup` clock is fixed in A.7, in the dependency graph, and in the C.14.3 and L.6.3 field notes. BACKLOG.md question 7 is removed.
- **P1 and the lead's P1 line:** E.5.1 loses the masked-CRC guard and `_crc()`'s `poly is None` entries. Its uart paragraph now lists all six statements (the `_read_answer_header()`/`_recv_train()` rx-None halves added). `math_helpers` is noted as reached by `test_residual_math_errors_return_none`.
- **U2:** J.7's trade-off sentence now names `_check_a_clean_transaction_completes_within_its_virtual_time_bound` as the latency check.
- **P2b:** A.4's chip-fault text gains the `verify_present()` probe on a blank read and why it needs no bound (MB85RS64V p10, checked in the PDF).
- **Q2:** E.1 says no deterministic guard exists and the held-responder audit is the check, with its 2026-10-21 result.
- **P3 and P4:** covered in A.4, C.7.3 (new paragraph on the sibling file and rename), F.3 `stall.flash_program`, J.6 (the "without yielding" sentence) and Part N's `uart.flash_hold_max_ms` basis. The longest stretch is now 1720 ms. 2129 is kept as an upper bound. I checked the littlefs lines (4062-4070, 3125-3128, 3146-3149, 3434) in the pinned checkout. The "| 2129 ms" cell opening that test_timing_budget needs is kept.
- **U3e/U3f:** J.7's "not written" sentence is replaced by the hazard mode and its L2/L4 tests, with the None verdict. A.8 gains the `UartHazards` sentence (answers, report, modes, dev only) and the hazard report in the `sensors` list. G.2 names `_run_status_cmd()`. BACKLOG.md question 5 is removed.
  - Attribution follows `5d0e16f`: the owner is credited with the requirement, quoted with its question; the agent with the mode, "decided on the owner's behalf for review (agent, 2026-10-21)".
- **R2:** J.5 now says a `clear()` of a healthy parked listener persists one E22 on `UART_resp`.
- **T2b:** E.9's sampler sentence says lines are placed in the window by byte offset. F.3's `rate.persisted_log` names Run 3 as its reader.

**Where the tree overrode the relay:**
- The `fault_storm` scenario now bounds writes by its events and no longer uses 627. So Run 3 is the only reader of `rate.persisted_log`.
- Run 3 checks two counts (landed plus silent writes, and WRENs/2), not just `fram_writes`.
- The clean-transaction bound is 4, not U2's 14, so I cite no red figures.
- `buildgen/graph.py:65` already says `ntp_clock_valid`.
- No doc besides SPEC lists the /status keys, so DEVICE_REFERENCE.md needs nothing.
- E.5.1 had three 2026-09-22 entries that are no longer in the tree: the config-manager except, the wifi `return None`, and sgp40's `readlen`. I dropped them as a consistency fix (agent, 2026-10-22).

**Left for D2c:** `tests_hardware/README.md:1090`, the "not written" sentence (U3e's README item); H3's README and twin-record texts; block K; owner questions 1, 2, 3, 4 and 6; D1's open steps.

**Open, for the lead:**
- (a) An interrupted config write is finished by `_finish_write()` with no yield. That stretch is untraced, and I marked it so in F.3 and J.6 (agent, 2026-10-22). It may exceed 1720 ms; I have not checked whether it exceeds 2129 ms. That is lane P's question.
- (b) The E.5.1 register may be missing `src/asy_wifi_service.py:651` and `src/asy_isl29125_driver.py:1494`, both marked unreachable in code. I did not add them because confirming needs a coverage run.
- (c) `scripts/_digital_twin_scenarios.py:143` has a comment ("rate.persisted_log: Run 3's one source") stranded above `_OUTER_CAP_S`. Not my file.
- (d) P3's twin `_flash_stall` fact is not landed, because the relay names no section for it.

**Checks:**
- First run (14 files): two decision-vocabulary reds from my own rewording of an allow-listed sentence; I restored "a third variant". The comment-cap red at `tests/_sensortask_scenarios.py:477` is the expected one (lane V's).
- Final run (13 files: citations, decision_vocabulary, legacy_paths, tunables_register, threat_model_statement, level_containment, timing_budget, import_placement, lock_order, memory_catalog, task_inventory, toml_schema_contract, task_tops): 159 passed, rc 0, 43 s, zero memory markers.

**Modes:** documentation only, so nothing changes in STA, AP, Silent, Off or USB on any device.

Logs and the edit script are in S/u35/laneD/d2b/. All runs were pure-parse pytest and all have exited.

nothing of mine is running