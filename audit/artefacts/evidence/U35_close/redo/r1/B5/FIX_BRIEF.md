# B5 fix round (lead, 2026-11-03)

Read `S/u35r/r1/common_r1.md` (binding), `B5/ACTION_LIST.md`, `B5/REVIEW.md`, `B5/FALSIFY.md` and
`B5/FALSIFY_VERIFIED.md`. Worktree `S/wt-b5`, branch `audit/r1-b5` at `21e12c76`; labels `b5x_`. Test first as
common_r1 says; one commit per fix or one for all, your choice. No gate: the lead runs one on the merged head. Run only
the test files you touch or that pin what you touch, both GC stages, plus lint and the three typechecks at the end.

- F1 WS-20 is not restored (REVIEW.md): the pieces writer counts and holds bytes again, as at `3129bf21`: the bytes
  `_PieceWriter`, `list[bytes]` pieces, `_pieces_response()` with no re-encode, the serving-demand scenario's identity
  check (`all(sent[i] is pieces[i] ...)`, its "uncopied" name), `test_h2_piece_writer_counts_bytes_not_characters`, the
  multibyte-SSID test bounding bytes, SPECIFICATION.md I.3 saying bytes. Show it: the falsifier's planted copying
  `_pieces_response()` (`B5/probe/probe_b5f.py`, run `b5f_probe5`) fails the restored scenario.
- F2 the unsynced NTP retry (item 19, owner 06:54: one attempt every 60 s after a failed one): a check tick that lands
  while an attempt runs must not trigger the next attempt at once. Test first, red at `21e12c76`: one tick during a
  failing attempt, none after, so no second attempt until 60 s of ticks have passed. A forced resync or a settings change
  during an attempt still tries at once after it. Smallest form; re-read SPECIFICATION.md's `l2.ntp_unreachable_failures`
  row and twin Run 9's bound against the fixed schedule.
- F3 SPECIFICATION.md:11188-11189: drop the three removed `device.ntp-retry-*` rule ids.
- F4 `digital_twin/README.md:800-808`: Run 9 described with the 60 s retry, not the doubling backoff.
- F5 `digital_twin/unixport/_ntp_responder.py:20`: the `_NTP_REQUEST` citation names what the product sends now.
- F6 SPECIFICATION.md:4054: the resolver ignores `write()`'s answer (item 7), so a failed socket setup costs two 500 ms
  backoffs; the row says what really happens and its total follows.

Hand-back: append "## Fix round" to `S/u35r/r1/B5/HANDBACK.md` (per fix: outcome, test seen red then green, runs).
Your final message: the commit(s), one line per fix, last "nothing of mine is running".
