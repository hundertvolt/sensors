REC hand-back (U34 records). Commit `7023cd2` "U34 int: the close records" on audit/u34-int in S/wt-u34c, on top of `b00a288`. It changes 3 files (213 insertions, 3 deletions). Nothing is pushed, nothing is uncommitted, nothing of mine is running. I used about 45 tool calls.

Files written:
- audit/sweeps/scan_runs/20261021_U34_close.md (new). It has all 42 steps by P1's number: 26 applied, 2 partly applied (27, 28, their remaining modules routed), 9 landed, 5 check-only, none parked. It also has the rulings, the silent-failure scan per class (lane N's removal and its rewritten tests, plus the new attribution test; the rest is configuration and documents), the effect per mode, and the working economy (harness counts, 459 calls in all; the tier run once on `1dd6dd5`). "## Gates" holds only `<GATES>: the lead fills this section.` "## CI" holds `<CI_U33>` and the sentence that U34's own run is recorded in U35's record.
- audit/REGISTER.md: the unit row at :60 is set to done. Six U34 rows are at :786-791. The gates row (:790) carries `<GATES>` and the CI row (:791) carries `<CI_U33>`.
- audit/sweeps/open_findings.md: OF-208 closed at lane C `0f55912`, with the expected one-time browser download. Three new rows:
  - OF-237 to U35: the 13 modules U35's R-15 names, each with its T1 sites, baseline line, ANN401 entry and `_RESIDUAL` row.
  - OF-238 to U36: `_boot_contiguity_probe` and `_uart_link_contract`.
  - OF-239 to U37: `scripts._hardware_verdict` plus R-14's four `no-any-unimported` sites from the bare `_summary_block` imports.
- Outside the tree:
  - S/u34/close/assemble.sh, evidence_README.md (with `<GATE>` and `<EVCHECK>`), squash_msg.txt (subject 95 characters, no line over 100, no audit IDs in the body, the two trailers);
  - records_edit.py, the helper that made the register and findings edits;
  - doc_checks.log.

Checks: test_citations, test_decision_vocabulary and test_legacy_paths on the head, with the files staged: 24 passed, rc 0, 0 memory markers. The one warning is the uninitialised datasheets submodule, as at base.

Evidence: 347 files staged, 1.9 MB, in S/u34/close/evidence. 0 files masked, 0 copies of tracked files. Not copied into the tree.
- assemble.sh ran twice. The first run's tracked-copy guard (my own addition) also compared against earlier units' evidence under `audit/`. It removed 90 genuine logs and CHECKLIST.md, because logs that repeat exactly look the same as those copies. I limited the guard to paths outside `audit/` and ran it again. The first run's output is kept as S/u34/close/assemble_first_overbroad.out.
- REC_final.md and any gate*/ folders are picked up only if they exist. Re-run assemble.sh after saving my hand-back and adding the gates.

What I settled on my own (agent, 2026-10-21), and other points:
- The brief said U33's rows end with its CI row. Three owner-answer rows follow it (:783-785), so U34's rows go after :785, U33's last row.
- I also closed OF-96 with no edit (R-9). It targeted U34; the closure cites the pin at test_vendored_freezefs.py:9-17 and lane A's `5c21b2d`, which adds the check that the licence file records the pinned commit.
- Every other point raised in the hand-backs is already settled; the record's Findings lists them, so no further row was needed.
- `_sensortask_scenarios` has 77 sites in T1's list, where P1's grep said 79. OF-237 uses T1's 77.
- N1 removed two test-only `@tunable` tags, which goes against R-21's "no tunable change". N2 removed their Part N rows by your ruling. Both are logged in the decisions row.

Left open: only your placeholders (`<GATES>`, `<CI_U33>`, `<GATE>`, `<EVCHECK>`).
