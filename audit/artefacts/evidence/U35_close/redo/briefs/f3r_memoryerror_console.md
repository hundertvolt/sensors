# F3r: a caught MemoryError reaches the memory gates at every DebugLevel; the NTP retry wait on elapsed time
(lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Worktree `S/wt-u35f3r`, branch `audit/u35-f3r` at `bc3bed11` (656fc82 plus
F1r and F2r merged; rebuild it before the first run); logs in `S/u35/laneR/f3r/`. Your brief is the "F3" section of
`S/u35r/recovered/briefs/blocks_f.md` (the lost block's; its line numbers are from an older head, re-locate them), with
the changes below. The decision behind it: `S/u35r/recovered/lead_notes_119_148.md` "## 146" (agent, 2026-10-23).

## Changes to the recovered F3 brief
- Its base and branch are replaced by the ones above.
- Items 1 and 2 (the tests first, then the fix in `src/asy_print_log.py`) as written; grep every level-gated method a
  `src/` call site hands a caught error and cover each.
- Item 3 (the whole tier at both stages and the dev and wozi twin CI) does NOT run in this pass: other blocks are
  running and a whole-tier run is allowed only with at most three of them. Stop at the seam after items 1, 2 and the
  NTP item below with every changed and importing test file run at both stages (every device for a PER_DEVICE file),
  commit, and hand back. The lead resumes you for item 3 with a message when it may start.
- Item 4 (effect per device and mode, the stale sentences for D3) in your hand-back.

## Added: the NTP unsynced retry wait (F2r's finding, `S/u35r/handbacks_redo/F2r.md`)
`src/asy_ntp_client.py` (about :385): `_unsynced_wait_s += _NTP_CHECK_INTERV` still counts delivered ticks, so the
unsynced retry is one check interval late per dropped tick. F2r moved the synced resync cadence onto elapsed time
(`self._cadence`, a TickSeconds; read F2r's change in `git show c56b366b -- src/asy_ntp_client.py` and the two tests it
adjusted). Do the same for the unsynced wait, test first: a dropped tick must not delay the retry, red on the current
tree at both stages. Keep every existing behaviour the tests pin; name any test you change and prove it also passes on
the old source, as F2r did. Effect per device: every device with NTP, STA mode. Its row in
`tests_scripts/test_counter_steps.py` `_EXEMPT` (`NTPClient._unsynced_wait_s`) may become orphaned: do not edit it (the
lead edits allow-lists), hand it back.

## Not yours
toolchain/ (F4a); `src/asy_system_service.py`, `buildgen/` and the boot entry (F4b); the twin suite and
`digital_twin/_fram_chip.py` (T4r1); audit/ records. Commit subject `U35 lane F3r: <summary>`, the two trailers; do not
push. Hand-back: commits, each test's red and green with log paths, the call sites covered, item 4, anything that
surprised you; last line "nothing of mine is running".
