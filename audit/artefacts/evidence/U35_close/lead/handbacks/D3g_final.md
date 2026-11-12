D3g hand-back. Commit dcf8ff1 on audit/u35-d3g (from c398332). Only SPECIFICATION.md changed, +73/-36. Not pushed, nothing uncommitted. Logs: S/u35/laneD/d3g/ (docs_checks.log, docs_checks2.log, commit_msg.txt, tools/).

**Per item**
- **1, landed** (A.4, SPEC :191-199 and :216-220):
  - A chunk write reads block 1's status pair first (one 2-byte READ, its own CS cycle, inside the first block's operation). Block 0 goes first only when both bytes read IDLE; otherwise block 1 goes first. So the write path never leaves both copies marked.
  - A failed status read logs the driver's entry and FRAM_STATUS_READ, and block 1 goes first.
  - The read adds one CS cycle and removes none, so "every CS cycle still stays".
  - Tags: the write order is "(agent, 2026-10-22), accepted by the owner on its report" with the quote "Solutions you proposed agreed." The failed-read pick is tagged (agent, 2026-10-22) only, because it was decided after 13:56.
  - Status cells: 3 operations per read; per write, 2 on block 0's and 3 on block 1's, so a read's block operation stays the worst case.
  - Endurance: about 144 years, computed from a read's 3 operations; the test pins a 100-year floor.
  - The owner's decisions are untouched: 2026-09-18 ×2, 2026-07-18, 2026-09-10 with its "don't fix it".
- **2, landed with one deviation** (SPEC :221-229):
  - New mechanism sentence: the loss arises when an abrupt reset lands in a read of one copy while the other is already marked.
  - The reason sits beside it, per LEAD NOTES 114: reads are destructive, the other copy must be read whole to be used, and that read can itself be torn. No ordering removes it.
  - The acceptance (owner, 2026-09-11; confirmed 2026-09-26) is unchanged.
  - Deviation: I left out "(or a read's repair write)". In the code, a repair write always follows a valid read of the other copy, and that read ends IDLE (asy_fram_manager.py:239-243 and :250-254, with `_read_chunk`'s IDLE write at :318). So a cut repair write never leaves both copies marked.
- **3, landed:**
  - A.8 (SPEC :1243-1259): the refusal closes once its trace lands or one per-call timeout passes; the trace stays before the close because it paces a refused client.
  - All six pre-close traces go through `_trace_before_close()`; an entry cut short stays in RAM until the next write.
  - The last-resort catch is tagged per the second addendum: (owner, 2026-10-22: "Fine, keep it.", with its question). Its reason, the open-a-little-longer cost and the `finally` close are stated beside it.
  - Also updated: H.7 refusal FIN (:8276), "already persisted" changed to "traced" (:8291-8294), H.7.1 15 s line (:8346), F.2 wait inventory (Five → Six, :6492-6503), F.3 `con.http_call`, Part N `web.per_call_timeout_s`.
- **4, landed:**
  - J.7 (:9818-9821): two rounds; a failed transfer is allowed only at the maximum stall (J.5); requests are bounded by the client timeout derived from src.
  - `l2.scenario_request_timeout_s`: the UART load is the exception (`_UART_LOAD_REQUEST_S` = outer cap + one flash hold; admitted requests took 6-8 s on dev).
  - `web.outer_cap_s` and `uart.flash_hold_max_ms` list it among their dependants.
- **5, nothing to change:** no SPEC sentence quoted the old escalation message or named FRAM_STATUS_READ's raise site. The :6470, :6600 and :11810 timeout descriptions still match the tree.

**For B2c and D3:** the 1-in-8 sentence is unchanged at SPECIFICATION.md:229 ("Measured in the digital twin at roughly 1 abrupt restart in 8.").

**Stale outside my items** (not my files):
- src/asy_webserver_service.py:951: the comment "no arm persisted this connection's one entry" should now say "traced", since an arm's trace can be cut short.
- scripts/_digital_twin_scenarios.py:144-146: `_UART_LOAD_REQUEST_S` leaves out the reclaim trace's extra per-call timeout for an admitted connection reclaimed at the outer cap.

**Checks:** test_citations, test_decision_vocabulary, test_legacy_paths, test_tunables_register and test_timing_budget (the F.3 and Part N reader): 62 passed, rc=0, run twice under nice 19, 21 s. Zero memory markers. One warning: datasheets submodule not initialised in the worktree. I grepped the other tests_scripts readers of SPEC; none reads a section I changed. Each run has a start and an exit line in RUNS.md.

nothing of mine is running