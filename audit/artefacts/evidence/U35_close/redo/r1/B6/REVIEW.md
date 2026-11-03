# B6 review (lead, 2026-11-03)

Every hunk of `src/` and `buildgen/` in `90691b6d..1b4caa17` read against `ACTION_LIST.md` (`review_hunks.py`: 27
hunks, 1 marked mechanically, 26 read; `review_hunks_lead.out`). Every hunk maps to an item: 1 (`_rx_stop()`, its two
`const()`s, `_arm_rx()` and `deinit()`), 2 (the header and the `_RSR_ERRORS` comment), 3 (the four zero-length guards),
4 (the write deadline in the driver, the comm's two passers and the link's), 5 (the closed-channel catches, the
post-yield checks, `ready()`'s `return True`), 6 (typed locals with one suppression each, the pieces branch one line),
7 (`_check_cap()`, `_chunks_for()` folded back), 8 (`_peek_discarded()` folded into `_take_discarded()`, the pre-audit
texts), 9 (W57 and its catalog row), 10 (`_call()`), 11 (the link's `setup()`), 12 (`copy_into()`). The twin and the
test DMA fakes carry the same setter and raise. No module grows; the fix inside the driver is +64 B.

Checked while reading:
- The pieces copy in `_send_train()` drops its fault branch: a GET answer's `total` is `len(payload)`, the
  `PieceBuffer`'s own size, and each chunk's `sent + size` stays within it, so `read_at()` cannot refuse; a refused TX
  buffer refuses construction. The branch was unreachable, as row 6 says.
- `_write_all()` without a deadline calls `ready(POLLOUT)` with no timeout, which polls at `poll_idle_ms`, as at
  `25caf528`. It writes only into an empty TX ring (after `txdone()`), so the first check before any sleep finds the
  free byte; the idle rate does not pace a transaction's writes.
- `_rx_stop()` is the bench branch's order (unchain the data channel, abort the reload, abort the data channel); the
  `ctrl` write goes through the non-triggering alias (`rp2_dma.c` v1.29.0). `deinit()` keeps its catch around it.

Decisions on the points the hand-back named (agent, 2026-11-03):
- **Row 10's suppression stays:** `Callable[..., object]` trips the strict pass's explicit-Any check; the one ignore on
  the signature is the typing side's cost of dropping the per-call keyword dict.
- **`writefrom()`'s `crcsize is None` check keeps its pre-audit text:** with the zero guard gone, a zero size reaches
  `add_into()`, which answers `None`; the check is reachable again and the old "Unreachable" comment would be false.
- **The changelog rows B94-B96 stand:** one Class B row per mechanism kind, as the list asked; no Class A row.

The agent's session ended at the container restart (14:05 UTC) during its gate, before it filled the gate, the dev
image figure and its findings; the lead re-ran its gate unchanged (`b6_gate`, the first run kept as
`b6_gate_killed_1405.log`) and fills those sections, marked as the lead's.
