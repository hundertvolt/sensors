# The FRAM log store's write order (U14, lane L)

What failed: `PrintLogHistoryStore._write()` (`src/asy_print_log.py`).
- `fail_first_test70.txt`: `test_concurrent_writes_land_newest_last` on U11's `_write()`, where each concurrent call
  packed and wrote its own snapshot: three payloads were written (`AssertionError: [b'\x01...', b'\x02...',
  b'\x03...']`), so which state landed last rested on the lock's hand-off order. 66/67.
- `fail_first_cancel.txt`, `fail_first_failedwrite.txt`: the two tests planting a cancelled newest call and a failed
  write, on the merged step form that skipped every superseded call with `True`. Cancelled: only the first payload
  reached FRAM (`[b'\x01\x00\x00\x00\x01']`), entries 2 and 3 never did, though their calls had answered `True`.
  Failed write: the payloads were the first and the full state while the calls answered `[True, True, False]`
  (lane L's report).

Why: the merged design counted on the newer call to write; that call can be cancelled while it waits for the lock
(WEBSERVER's logger runs inside the connection's outer `wait_for()` cap) or fail its write.

Fix: commit `26fd655` (U14 lane L): one `asyncio.Lock`, the live state packed and written under it; a call skips only
once an earlier successful write carried its state (`_written_gen == _write_gen`, advanced only on success).

What proves it: `after_test_asy_print_log_gc-1.log` and `after_test_asy_print_log_gc32768.log`, 69/69 at both GC
stages with zero memory-error lines, all three tests passing (the step's own test kept as specified).
