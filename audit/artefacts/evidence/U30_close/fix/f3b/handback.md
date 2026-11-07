U30 fix F3b FINAL
Commit 862ab61 on audit/u30-f3b (S/wt-u30f3b, from 763f469): SPECIFICATION.md, CLAUDE.md, DEVICE_REFERENCE.md, digital_twin/README.md only. Not pushed, nothing uncommitted. Lines at 862ab61.
Relay lines applied (each found by text): F1a 4 (SPEC:920, :1045, :1050, :1052-1057; vs codegen.py:722-723, webserver:850, system_service:660-665); F1c 3 (SPEC:3112, :3454-3455, :9442-9445; vs notification:268-272, dns:147-150, uart_comm_hazard:1118/:1199/:1213); F1d 2 (SPEC:3313-3322 C.7, :3475-3476 C.7.1; vs print_log:348-372); F3a 3 (SPEC:6002-6004, :8753-8757, :8761-8763); F3a2 1 (SPEC:5991-5999).
Deviation (agent, 2026-10-20): F1d's C.7 mid-write sentence carries the owner tag (owner, 2026-10-20, asked, paraphrase, whether to fix it now or later: "I would like it to be fixed now").
Review items, confirmed at 763f469 and fixed:
- RA-5 SPEC:8687-8691: the shutdown line collects once per process, from main()'s finally or the interrupt handler, just before mem_info() (run_generic_integration.py:400-408; checker row :69 "baseline").
- RA-6 SPEC:7156-7161: a codec MemoryError fails the whole read: sample dropped, "Read failed:" under _ERR_READ, counts toward the give-up streak (sgp40 :466-476, :384); interrupted restore retries next cycle (:472); interrupted backup waits a full period (counter reset at the trigger, :286).
- RA-8 CLAUDE.md:237-245: owner's 2026-09-25 words quoted in full (PROJECT_AUDIT_PLAN.md OR26.a, 8aea0e9); the question marked paraphrase (never recorded word for word).
- RA-8 CLAUDE.md:410-421: rule marked paraphrase; quotes the owner's 2026-09-26 and 2026-09-29 words each with a paraphrased question, and the 2026-09-26 words on gc.collect() completing before it returns (OR39.a, OR91, OR55).
- RC-7 CLAUDE.md:415-417: loop_stretch_timing.py's measured collection named as the one collection inside a timed window (SPEC:8748, checker row :76).
- RC-2 digital_twin/README.md:826-828: SPEC:8648-8650's paraphrased question added.
- RC-4 SPEC:6920 (F.7 row 32), digital_twin/README.md:1172-1175: a module path over 255 bytes fails at import with `RuntimeError: name too long` (py/builtinimport.c:242, py/qstr.c:319-321).
- RD-2 SPEC:3434-3438 (C.7): as F1b's brief states (broad = can catch RuntimeError, by name or in a tuple; Lockable.__aexit__() and FRAM_SPI.__aexit__() report first); code still `except RuntimeError: pass` at base_classes:123-126, fram_driver:167-170 until F1b.
- DEVICE_REFERENCE.md:159-164: refused up front (dropped-connection count included); a pause beginning mid-reset leaves each FRAM log not yet cleared as it was, answer "Failed".
Consistency fix (agent, 2026-10-20): SPEC:3327 "clears the in-RAM ring before attempting the write" false after F1d -> "once that write returns" (print_log:362-366).
F1b relay lines: none arrived, none applied. RA-7's sentence (SPEC C.7/A.5) is F1b's to relay.
Checks: 16 scans + every tests_scripts file reading these docs (113 files): 5151 passed, 9 skipped, 2 failed: test_decision_vocabulary on "settled" (SPEC:8690) reworded, rerun green; test_counter_steps::test_no_min_step at src/asy_print_log.py:191 (F1d 9d40e64, red at 763f469 already; no src touched by F3b). 12 pre-commit checks after git add: 787 passed rc 0. 0 memory markers. ruff/mypy n/a.
Runs (RUNS.md): rebuild rc 0; 113-file run rc 1 (the two reds), 7m21s; doc-scan rerun rc 1 (counter_steps only); 12 commit checks rc 0. Logs S/u30/f3b/. Nothing of mine is running.
