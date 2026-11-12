UM2 hand-back, written by the lane (2026-10-27)

**Commits** on audit/u35-um1 in S/wt-u35um1, on top of ad624cca. Not pushed. Nothing is uncommitted except the linked node_modules.
- 1d2b3cca: item 1, the three catches (owner's option C).
- 3a24c773: item 2, the dev echo answers a GET from its stored pieces.
- d57ad57b: fixes found by item 3's checks: read_at() moved to its member-order slot; one frame write shared by both answer forms; the e51 sweep's hits and verdicts carried across the shifted lines.

Logs are in S/u35/laneB/um2/. Item 3 on the 3a24c773 tree is in at_3a24c773/. Wrappers: one.sh, run.sh, batch.sh, cov.sh, checks3.sh, remap_hits.py. Every run has its RUNS.md lines.

## 1. The catches (owner, 2026-10-27)
Each site catches `MemoryError` from `PieceBuffer(...)` and handles it like any other fault:
- **SET, responder** (`_accept_set`): `_fault(device, _ERR_ALLOC, "could not allocate", room, "bytes for the incoming train:", e)`, then returns `ListenResult(None, CMD_SET, None)`. The resync drains the stranded data chunk. Because `cmd` is set, the loop re-listens at once (A15).
- **GET answer, initiator** (`_get_unlocked`): the same `_fault(..., "bytes for the answer:", e)`, which resyncs and holds off. `uart_get()` returns None.
- **`readline_until_complete()`**: `console(_NAME, "line pieces allocation failed:", e)`, returns None. The line stays in the ring, the same shape as `readline()`'s own catch.

The caught text is printed in every case (err_s at error level, or console()), so the memory gates see it (the B80/B81 precedent).

**Red and green.** UM1's three tests were flipped. Red means run against ad624cca's src (stashed), both files at -1:

| Test | Red on ad624cca | Green on the fix |
|---|---|---|
| tests/test_asy_uart_comm.py `test_a_refused_piece_at_a_received_set_faults_as_alloc_and_the_responder_re_listens_at_once` | failed: persisted read [UNEXPECTED, UART_FRAME_INVALID] | responder [ALLOC], initiator [UART_NO_ACK]; link alive and recovered; caught text printed |
| tests/test_asy_uart_comm.py `test_a_refused_piece_at_a_dont_care_get_faults_as_alloc_and_uart_get_answers_none` | failed: the raise escaped `uart_get()` | None; initiator [ALLOC]; (busy, hold-off) = (False, True); responder [UART_NO_ACK]; next GET "banner"; text printed |
| tests/test_asy_uart_driver.py `test_a_refused_line_piece_answers_none_prints_its_text_and_consumes_nothing` | failed: the raise escaped | None; discarded 0; one console line `("UART", "line pieces allocation failed:", <text>)`; next read whole |

Logs: red_comm.log, red_drv.log, green_comm.log, green_drv.log. The injected text is still "simulated allocation failure", worded clear of the gates.

**Changelog (UART_C_PORT_CHANGELOG.md)**
- **A17 (Class A).** The two protocol sites: an ALLOC fault with the text, the resync and hold-off, the failure result, and an immediate re-listen. The change is receiver-side only and emits no byte differently; the recovery timing is that of every other fault. C to verify: whether the C receiver's train allocation can fail, and if so that it withholds the ACK, resyncs and re-listens the same way.
- **B90 (Class B).** The readline catch (no protocol path, B50).
- **Notes.** B64 ends "(the caught `MemoryError` at the pieces restored by A17)". B62 ends "(caught since B90)". B62 is the readline row, so its "not caught" claim needed the same note. That goes beyond the brief's "a note at B64".

**Docs**
- SPECIFICATION.md:
  - G.2's PieceBuffer bullet: a MemoryError goes to the caller, which catches it.
  - C.3.2: two places, the readline text and the sentinel sentence ("aside" → "included").
  - I.2: the asy_uart_comm and asy_uart_driver rows.
  - J.8's bullet, rewritten as the fault flow: "(owner, 2026-10-27; I.2, I.4(a))", re-listen per J.5's backoff rule.
- asy_base_classes.py: the module docstring (:7-8) and PieceBuffer's comment.
- asy_uart_driver.py: the header comment (:7-8), which said readline lets the MemoryError through.
- asy_uart_link_driver.py: the exercise loop's comment. "A failed transfer never raises out (uart_get() answers None, a failed piece allocation included)" is now true. It no longer claims anything about the hazard run's own small allocations.
- Decision tags: "(owner, 2026-10-27)" on everything owner-decided.

## 2. The dev echo (asy_uart_link_driver.py `_get_callback`, formerly `bytearray(len(stored))` + `copy_into`)
**Measurement** (red test, both stages): one GET 0x02 served with a stored echo at the receive cap allocated exactly one bytearray of 12,192 B, at gc.threshold -1 and at 32768 (`AssertionError: [12192]`; red2b_link_m1.log, red2b_link_32768.log).
- **When:** every GET 0x02 the responder serves while it holds a stored SET.
- **How often on dev's own firmware: never.** dev's initiator only GETs the banner. Its hazard run only SETs the echo (≤ 103 B), and its raw frames are a banner GET and SET first chunks. Only a peer in the jumper's place (the C peer) can SET a large train and GET it back. At the cap that is one peer-sized block per request.

**The twin's largest free block was not taken.** The twin runs on the Unix port's default heap: nothing in scripts/ or digital_twin/ passes `-X heapsize`, and the dev twin's own shutdown line reads max free sz 26763 blocks, about 428 KB. A reading there says nothing about placeability on the 192,488 B silicon heap.
- The figures that bear on placeability are silicon ones: a largest free block of about 1.5 KB at the shipped web peak (archive §7R; I.6).
- Against those, a 12,192 B block is not placeable under load.
- So it is not a "bounded, placeable one-off". Under the memory rule its only outcome there was `_call`'s caught MemoryError (E CALLBACK), a caught-and-degraded design defect.

**Verdict and fix:** a design-level fix, streaming, with no threshold and no catch.
- A responder's `get_callback` may answer with a PieceBuffer.
- `_send_train()` sends it from its pieces: each chunk is copied by index into the TX frame's data region through the new `PieceBuffer.read_at(offset, dest)` (write_at()'s mirror). The frame write is shared with the buffer form.
- The echo returns the stored train itself. No byte, framing or timing changes.
- Changelog **B91** (Class B), "(agent, 2026-10-27)".
- Docs: G.2 (read_at in the API list), I.2 (base_classes' slice views; the link row "Per GET served: no copy"), J.8's paired-API bullet.

**Tests, each red on the previous source:**
- tests/test_asy_uart_link_driver.py `test_the_echo_answers_a_get_from_its_stored_pieces_without_a_copy`: structural, a shadowed `bytearray`. Red [12192]; green: no allocation, and the payload is the stored train.
- tests/test_asy_uart_comm.py `test_a_get_answered_with_a_piece_buffer_is_sent_from_its_pieces`: 1,000 B in 256-B pieces with chunk ends inside pieces. It arrives whole, no comm bytearray is allocated, and nothing is persisted. Red: refused as a non-buffer payload.
- tests/test_asy_base_classes.py `test_piecebuffer_read_at_copies_exactly_its_range_across_piece_ends`. Red: AttributeError.

No owner question arose.

## 3. Checks on the final head d57ad57b
- **Test files.** Every test file importing asy_uart_comm, asy_uart_driver or asy_uart_link_driver, or their harnesses (14 files), plus the PER_DEVICE files test_digital_twin_sensortask_integration.py and test_sensortask.py on all six devices, at -1 and 32768: **52/52 rc 0, zero memory markers** (batch.out, h_*.log). Device skips in the integration file match its device split (0 failed). test_sensortask is 105/105 on every device.
- **lint_direct:** clean (lint5.log).
- **The six mypy passes** (typecheck.sh with its venv guard bypassed in a temporary copy, since deleted): 10/10 checks pass (mypy5.log).
- **The tests_scripts readers** of every changed file, including SPECIFICATION.md and the changelog (104 files): 4599 passed, 0 failed, 6 skipped, 1 warning (the uninitialised datasheets submodule) (readers_final.log). On 3a24c773 the same run had two failures, both closed:
  - member_order: read_at was out of D.15's order. Fixed in d57ad57b.
  - test_digital_twin_generated_boot's CRC16 dev link: "Transfers (0, 0), Failures (0, 1)", seen once. It passed 7/7 alone on the head (readers_fix.log, twin_link_x6.log).
    - Cause not established. It reads as one failed round followed by the fault's resync and hold-off (about 3 s at the defaults) outlasting the test's 3 s `_LINK_POLL_GAP_S`.
    - By code reading it is unrelated to these changes: the banner path's bytes are unchanged, and the catches fire only on a MemoryError.
    - It may recur under machine load.
- **e51** (`--check`, `--render`, `--self-test`): green, 64 sites (base 63; +1 is the new type-narrowing guard in `_send_train`, verdict class c). How e51_hits.json was kept current:
  - The lines of the four changed src files were carried across the diff (equal blocks only).
  - Their new or changed lines took a coverage dump of those files' own four test files on this tree (build-settrace, cov/).
  - Every other file is untouched.
  - Seven line references inside verdict texts that the edits moved were re-pointed by content (:934→:948, :665/:669/:680→:669/:673/:684, :166→:164).
  - The rendered e51.md diff is line shifts plus the one new row.
- **review_rows:** red on the same six rows as ad624cca, the BR4 rows: five setup_credit_only (test_digital_twin_clock_jump ×2, test_digital_twin_hot_replug ×1, test_digital_twin_ntp ×2) and test_twin_wiring_contract's same_callee.
- **The walk.** This base's audit/b3/raising_walk.py has no `--check`: the BR lanes' version is not on this base. Its own render already differs from the committed raising.md by 845 lines at ad624cca and 847 at the head. Between base and head, the only difference is asy_base_classes.py: +7 call rows ("open" 413→420), read_at()'s calls, the same as write_at()'s, plus shifted line numbers. raising.md is not regenerated here; the lead's integration walk renders it.

## Notes
- The SET test's red failed at its persisted check. UM1's committed version passed at that point, so the test was red for the right reason.
- J.8's new text first named "J.7's backoff rule"; that is corrected to J.5, where the rule lives.

nothing of mine is running
