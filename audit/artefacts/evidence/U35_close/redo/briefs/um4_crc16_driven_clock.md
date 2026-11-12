# UM4: the twin's UART link tests off the host's clock, and the poll step recorded (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back), then UM3's hand-back `S/u35r/handbacks_redo/UM3.md` (section 3: the reproduction, its probe and loop
`S/u35/laneB/um3/crc_loop.sh`, the numbers), then CMr1j's hand-back `S/u35r/handbacks_redo/CMr1j.md` items 1 and 4
(the technique: the booted graph driven on DrivenTime, `release()` for real-clock work). Worktree `S/wt-u35um1`,
branch `audit/u35-um1` at c570ba76 (UM3's head; clean). Logs in `S/u35/laneB/um4/`.

## The lead's review of UM3 (binding)
- Its four commits are kept. The CRC16 red is reproduced with its signature, and the base reproduces it: UM2 did not
  bring it. The settle() fix stands on its own red-first test.
- Its cause holds for the twin; its silicon extrapolation does not. The lead measured the pinned Unix port
  (`S/u35/lead/probe/tsf_poll.py`, `S/u35/lead/tsf_poll.log`): one scheduler step costs 6.9 us with nothing in
  asyncio's IO queue and 1160 us while a non-fd pollable is registered (a waiting ThreadSafeFlag). extmod/modselect.c
  (v1.29.0): on Unix (MICROPY_PY_SELECT_POSIX_OPTIMISATIONS 1) every step's poll() waits
  MICROPY_PY_SELECT_IOCTL_CALL_PERIOD_MS (1 ms), even for a zero timeout, while any registered pollable is not an fd;
  rp2 (0) polls once and returns. So a CRC16 frame and its ACK cost about 220 steps of about 1 ms on the twin only.
- No product change: (a) is not taken (it would trade the owner's per-byte yield for a twin artefact); (b) is not taken
  (it narrows a check). The silicon round trip under API load is a hardware-round reading (c), recorded by the lead.
- The defect lies in the tests: a protocol deadline counted on the host's clock makes the verdict depend on host load
  (SPECIFICATION.md J.7 already says so for the mock tier, whose checks run on the poll-round clock).

## Items, in order (each committed green on its own)
1. Put the CRC16 dev-link test (test_digital_twin_generated_boot) on a driven clock so the protocol's ACK timeout
   counts virtual time; every assertion stays as it is. Then find every other twin test whose verdict hangs on a UART
   protocol deadline counted on the real clock (test_digital_twin_uart_link.py first: it passed only on retry past
   the 240 s per-file bound in the lead's gate at 32768) and do the same; list each test you leave on the real clock
   with the reason. Prove it: the loop that reproduced the red (32768, K=3) red 0 of at least 75 on the fix, and the
   same loop on the unfixed test still red (the red-first evidence). Bite: a planted ACK delay past the timeout, in
   virtual time, still fails the test. Formal pair per changed file.
2. A comment at each changed test (at most 3 lines) naming why it runs on the driven clock. The doc text (the
   mechanism above, for digital_twin/README.md and SPECIFICATION.md J.7) goes into your hand-back for the lead's D3r.
3. `audit/trace/UART_PART_J.md:20` still says the PieceBuffer MemoryError goes uncaught: correct it to the owner's
   2026-10-27 catch, in that file's conventions.
- Lane N11d measures test_digital_twin_uart_link.py and test_sensortask.py [dev] meanwhile and changes neither file.
- Checks: every changed file at both stages (PER_DEVICE files on all six devices), zero memory markers; on the final
  head the whole tests_scripts tier; lint_direct, the six mypy passes, the three audit checks; review rows.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
Commits; per test its clock, the loop counts red-first and fixed, and its bite; the tests left on the real clock with
their reasons; the doc text; the checks; last line "nothing of mine is running".

## Added by the lead (2026-10-27, after launch)
4. Last, once items 1-3 are committed and no run of yours uses the worktree: merge the integration head 111129f4
   (D2S, CO5 and CMr1j merged) into your branch, a merge commit, never a rebase. The lead's trial merge of c570ba76
   into int conflicted in UART_C_PORT_CHANGELOG.md (unite both sides' entries in the file's order), audit/b3/
   conformance.md, queue_c.md, raising.md, raising_verdicts/asy_base_classes.json, review.md, e51.md, and audit/
   sweeps/e51_hits.json, e51_verdicts.json; src/ merged cleanly. Resolve as UM3's item 1 did: rendered files by their
   tools, data files by the side that changed each entry or a fresh coverage run, verdicts and cites re-checked on
   the merged tree; where both sides changed code, keep both behaviours. Rebuild. Then this brief's checks again on
   the merged head (the importers of every module either side changed, both stages, PER_DEVICE files on all six;
   the whole tier; lint_direct; the six mypy passes; the three audit checks).
