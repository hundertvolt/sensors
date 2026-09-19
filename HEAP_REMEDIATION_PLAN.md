# Heap fragmentation remediation — implementation plan

The complete to-do list for the two measures the project owner approved on 2026-09-18, on the
evidence in `HEAP_FRAGMENTATION_MEASUREMENTS.md` (§3B, §7A, §7B): **A**, the wire-identical
restructure of the FRAM path, and **B**, `gc.collect()` confined to the two boot lists. Every item
below is a checkbox; the plan is done when all of them are, and the file is then deleted (its
durable parts migrate into `SPECIFICATION.md`, CLAUDE.md and BACKLOG.md — documentation holds
current state and rules, not the path that got there). Nothing here is started until the owner
says so; this file is the scope, the order and the done-criteria, written before any code.

**Owner's go-ahead (2026-09-18), verbatim in substance**: remove the architectural inefficiency
from the FRAM setup without losing any of its top-level features, potential future multi-device
SPI compatibility, or safety measures; combine it with the tight `gc.collect()` inside the startup
loops. `gc.threshold(32768)` stays enabled in production but is not the one tool that makes the
system functional — the system must also be stable without it. **The go-ahead covers the design;
it is not a real-hardware go-ahead** (CLAUDE.md: that is given separately, in the session that
runs the hardware).

## 0. What is fixed before a line is written

- **The wire protocol is byte-identical.** Same 74 CS cycles for a blank chunk `setup()`, 47 for a
  valid one, same opcodes, addresses and data in the same order, same `machine.SPI.init` calls
  (§3B.2). The status-byte lock with its two *separately written* bytes, the two copies, the CRC,
  the per-write WREN/RDSR-verify/WRITE/WRDI/RDSR-verify envelope, the `check_length` compare and
  every error path's meaning are integrity features (§3B.1, owner's account) and stay. This is
  asserted by a trace-equality test (item A.2), not promised.
- **The public API is unchanged.** `AsyFramManager.get_chunk()`/`get_timestamped_chunk()`,
  `AsyFramChunk`/`AsyFramTimestampedChunk`'s `write`/`write_into`/`read`/`read_into`/`clear`/
  `get_buffer`/`get_size`/`get_verify`/`set_verify`/`get_pause`, `FRAM_SPI`'s `setup`/
  `verify_present`/`get_values`/`set_values`/`get_size`/`get_write_protected`/
  `set_write_protected`, and `SPIDevice`'s async `__aenter__`/`__aexit__`/`write`/`readinto`/
  `write_readinto`. `print_log.py`'s `_FramChunk`/`_FramManager` `Protocol`s and
  `asy_sgp40_driver.py`'s `ts_storage` use are the consumers that pin this.
- **Every `errno`/`wrnno` keeps its number and its meaning** (`SPECIFICATION.md` C.7.1: FRAM 10-100,
  `wrnno` 60-84). What moves is *where* it is logged — once, by the coroutine that owns the
  operation, instead of at the leaf — not what is logged.
- **Multi-device SPI compatibility is preserved at today's granularity.** The bus lock is released
  and the loop yielded after every byte-level command (the 5-CS envelope), never held for a whole
  block operation — the "per command" yield policy, measured to cost 0 B against the per-block one
  (§3B.3). A second device on `spi0` therefore still gets the bus between any two commands, which
  is finer than any real device TOML needs (FRAM is alone on `spi0` everywhere) and coarser than
  today's per-CS-cycle release only by the four cycles of one envelope, all of which the chip
  itself requires to be uninterrupted.
- **F.3's hold-time principle is met by measurement, not estimate.** The longest synchronous
  stretch is one byte-level command: 5 CS cycles, 9 bytes on the wire at 1 MHz plus the RP2040's
  per-cycle overhead. Estimated well under a millisecond; measured on hardware in item T.4 before
  the change is called done.
- **`gc.collect()` appears in exactly two shipped sites**, both boot-only, both emitted or owned by
  the system's own boot code, guarded by lint (item B.3). The general prohibition for business
  logic and the run phase stands unchanged (`SPECIFICATION.md` I.4).
- **The 80,000 B floor is retired** (owner, 2026-09-19 — it was never theirs and demanded a third
  of physical memory contiguously free). `heap_headroom_after_full_system_build.py` now checks
  survivor volume, survivor *placement* and contiguity against §7A.9's measured worst reachable
  allocation instead. No threshold in it may be fitted to a board reading (§7G).
- **The branch starts clean.** At the owner's instruction (2026-09-18) every change this
  investigation made to established `src/` and test files was reverted to
  `claude/automated-build-chain-nuzumw`'s state: `src/asy_spi_driver.py` and
  `tests/test_asy_spi_driver.py` (commits `f6a182d`/`04ef56a`, the blocking CS settle and the
  post-session yield) are back to the two `await asyncio.sleep(0.001)` settles, and the Tier-0
  model pair (`tests/_heap_fragmentation_model.py`, `tests_scripts/test_heap_fragmentation_model.py`,
  commit `99080ff`) is removed. Their findings stand as measurements
  (`HEAP_FRAGMENTATION_MEASUREMENTS.md` §5.1, §8, §8.1) and are re-done *inside* A.1.1 below, with
  their tests written fresh under A.2 — nothing from the investigation's code is carried over.
- **Sequence: A first, measured alone; then B on top, measured again** (§7B.5). The (e)/(f) record
  in `SPECIFICATION.md` I.4 depends on knowing what the design fix does by itself.
- **Step-session workflow applies** (CLAUDE.md): tests first, implementation against them, then
  coverage, then stop and report. A blocking question goes to the owner at any point.

## A. The FRAM path restructure (scoped exception granted for `asy_spi_driver.py`, `asy_fram_driver.py`, `asy_fram_manager.py`)

### A.1 Design, decided

The shape is §3B's **P2** with the **per-command yield policy** (§3B.4 levers 1, 2 and 4; lever 3,
the lock hierarchy, deliberately *not* taken — see A.1.4). Board-equivalent cost per blank logger
`setup()`: 118,144 B today → 3,072 B (38x); the lock hierarchy would buy ~1,300 B (90x) but is the
riskiest abstraction change, and with B in place the two measure the same on layout (§7B.3). It is
reopened only if A.6's measurement asks for it.

1. **`asy_spi_driver.SPIDevice` gains a synchronous session.** Today one CS cycle costs two
   coroutine objects (`__aenter__`/`__aexit__`), a `Lockable` acquire/release, two awaited
   `asyncio.sleep(0.001)` settles (one of which hands the loop to other tasks *while CS is
   asserted and the bus lock is held* — the hazard §5.1 measured), and a coroutine per transfer
   (`write`/`readinto`/`write_readinto` are `async def` around a blocking C call). New:
   - `session_begin()` / `session_end()` (names to be settled in A.2's tests): plain functions
     that do what `__aenter__`/`__aexit__` do *between* the lock operations — `configure(...)`,
     CS assert, a **blocking** settle, and CS deassert + settle — with the same `initialized`
     guard and the same deassert-on-exception cleanup, **without** touching the lock. The caller
     holds the bus lock. The settle is `time.sleep_us(_CS_SETTLE_US)` with
     `_CS_SETTLE_US = const(2)`: both FRAM parts specify tCSU/tCSH >= 10 ns and tD >= 40 ns
     (MB85RS2MTA) / 60 ns (MB85RS64V) (`datasheets/fram/`), and rp2's `sleep_us()` busy-waits on
     `time_us_64()` so `sleep_us(1)` only promises an elapsed time in (0, 1] µs while 2 promises
     >= 1 µs — this is `f6a182d`'s content, re-done here as part of the synchronous session rather
     than as a separate commit. **The lesson of §8.1 is a design constraint, not a footnote**:
     removing the two awaited settles removed the CS path's only scheduling points and starved the
     loop for the whole 74-session burst. In A the scheduling points are the per-command yields in
     the coroutine that owns the operation (A.1.2/A.1.3), so they exist by construction; the test
     in A.2 that pins them (a burst of N byte-level commands lets another task run >= N times)
     is the regression cover `04ef56a` added, written fresh.
   - `write_sync()` / `readinto_sync()` / `write_readinto_sync()` (or the existing names made
     plain functions with the async ones kept as thin wrappers — A.2 decides which reads better
     against the 51 existing tests): the blocking transfer, no coroutine.
   - The async `__aenter__`/`__aexit__`/`write`/`readinto`/`write_readinto` stay for any other
     caller (a future SPI sensor driver, C.3.1), re-expressed on top of the synchronous primitives
     so there is one implementation of the CS/settle/configure sequence, not two. That gives the
     async session the blocking settle too (it must: an awaited settle inside the CS window is the
     hazard), and therefore one `await asyncio.sleep(0)` at the end of `__aexit__`, after the lock
     is released, so a burst of async sessions keeps a scheduling point per session — `04ef56a`'s
     content, re-done here.
   - `Lockable` (`base_classes.py`) is untouched.
2. **`asy_fram_driver.FRAM_SPI` gains synchronous block operations under a caller-held lock.**
   - `_send_opcode`, `_read_status`, `_wel_is_set`, `_enable_write`, `_disable_write`, `_write`,
     `_read_address`, `_check_device_id` become plain functions built on A.1.1's synchronous
     session. Each keeps its CS-cycle structure exactly (the trace test is the proof).
   - `get_values()`/`set_values()` keep their async signatures and their guards (`initialized`,
     `asy_lock.locked()`, address range) and call the synchronous body; they yield once, after
     the command, via `await asyncio.sleep(0)` — this is the per-command yield policy's one
     yield point for the driver layer, and it sits in the coroutine that owns the operation, not
     in a coroutine of its own (§3B.3's "a coroutine call is 64 B, a yield is 0").
   - **Error reporting moves up, not out.** `_write()`'s `wrnno` 84 ("currently write
     protected") / 82 ("latch did not set") and `_disable_write()`'s `wrnno` 81 ("latch did not
     clear after WRDI retry") are `await self.pr.wrn_s(...)` today, at the leaf. The synchronous
     bodies return a small status (which of the three happened) and the owning coroutine
     (`set_values()`/`set_write_protected()`) logs it with the **same** `wrnno` and the same
     message. `get_write_protected()`'s `errno` 89 stays where it is (it is already reached only
     from a coroutine). C.7.1's table rows do not change; the test in A.2 asserts each number
     is still persisted from the same public entry point.
   - `set_write_protected()`, `setup()`, `verify_present()` are rebuilt on the same primitives;
     `verify_present()`'s bounded `wait_for(self.asy_lock.acquire(), 1.0)` stays exactly as is.
   - The pre-allocated scratch buffers (`_id_buf`, `_status_buf`, `_addr_buf`) stay; the
     per-call `bytearray([opcode])` in `_send_opcode`/`_read_status` become module-level `bytes`
     constants (lever 4 — the 32-96 B size class the model cares about, §0A.3).
3. **`asy_fram_manager._AsyBaseFramChunk`: the status-byte protocol becomes plain functions and
   each block operation is one coroutine.**
   - `_set_check_sb()` and `_handle_status_bytes()` become synchronous (they are coroutines only
     because their callees were). Their `errno` spreads (`err`, `err+1`, `err+2`, `err+gap`,
     `err+2*gap`) are preserved to the number; the synchronous form returns `(uninit, errno_or_None)`
     and `_write_chunk`/`_read_chunk`/`_clear_chunk` log it — same message, same number, once.
   - `_write_chunk()`, `_read_chunk()`, `_clear_chunk()` keep their shape and their `async with
     self.fram as fram:` (the driver lock, taken once per block operation as today), and yield
     after each status-byte pair, after the payload command, and per `check_length` slice in the
     read loop exactly where the `await asyncio.sleep(0)` already sits. The `try/except
     Exception` wrappers with `errno` 26/47/58 stay.
   - Per-call small objects (lever 4): `bytearray(1)` and `bytearray([val])` in `_set_check_sb`
     → one `bytearray(1)` on the chunk; `temp` and its two `memoryview`s in `_compare_with` → a
     `check_length`-sized buffer allocated once per chunk (its size is fixed for the chunk's
     life; the `(MemoryError, OverflowError)` guard moves to construction and the chunk degrades
     the same way `get_chunk` already degrades a negative size); the `cb` closure and its cells in
     `_read_into`/`_compare_with` → state on the chunk, or the callback replaced by a returned
     tuple (A.2 decides; the observable behaviour — `valid`, `uninit`, `match`, `n_iter` — is
     what the existing 105 tests pin); `AsyFramChunkBuffer` with its own `asyncio.Lock` on every
     `get_buffer()` → **unchanged** for now (its consumers in `print_log.py` and
     `asy_sgp40_driver.py` call `get_buffer()` per operation and hold the result briefly; making
     it per-store is a consumer-side change outside the three files and is item A.7).
   - `_op_lock` (per chunk operation, across both blocks) stays as is.
   - `crc_checks.py` stays async in this step (item A.8 is §11 item 1, separate).
4. **The lock hierarchy is left as it is.** Today: chunk `_op_lock` (per chunk operation) →
   `FRAM_SPI.asy_lock` (per block operation) → bus lock (per CS cycle). After A.1.1-A.1.3 the bus
   lock is taken per byte-level command by the driver's synchronous body (one acquire/release
   per 5-CS envelope, not five). The driver lock stays per block operation. This is the
   "multi-device compatibility preserved" choice from §0 and the lower-risk one; it costs the
   ~1,800 B per setup that separates 3,072 from ~1,300, which B makes irrelevant to layout.
   **Superseded by the owner's decision, 2026-09-18: the bus lock is taken once per block
   operation, not per byte-level command.** `FRAM_SPI.__aenter__` takes the driver lock and the bus
   together; `get_values_sync()`/`set_values_sync()` are the byte-level entry points the chunk
   layer calls, with `report_get_values()`/`report_set_values()` owning every guard's number and
   message; the block operations yield after each status-byte pair, after the payload command, and
   per `check_length` slice — §3B's P2 yield points. Measured: a blank logger `setup()` costs
   **13,696 B against the base branch's 122,880 (9.0x)**, a valid one 9,152 against 80,384 (8.8x),
   wire traces byte-identical. A second SPI device now waits for a block operation (~25 CS, ~600 us)
   instead of a command (~5 CS, ~100 us). Lever 3 (per chunk operation) stays untaken: ~1,800 B
   more, and it moves the hierarchy itself. Full account: §7C/§7C.1 and §11 item 6.
   **What the paragraph below got wrong**, kept because the error is instructive. §3B's P1 **and** P2 both took the bus lock
   *once per block operation*; §3B.3's "the floor is now set entirely by lock acquisitions" counts
   four block-operation acquisitions, and its ~1,800 B is the gap between per-block-operation and
   per-*chunk*-operation locking (lever 3) - not between per-command and per-block-operation. The
   real cost of taking it per command is **~15,000 B per blank `setup()`**: A as built lands at
   18,240 B board-equivalent (6.7x) where P2 was 3,072 (38x). P2's synchronous status-byte protocol
   is also unreachable at per-command granularity, since `_set_check_sb()`'s callees are the very
   coroutines that acquire the bus. The measured ladder and the per-node costs are §7C.1; the
   decision itself is §11 item 6, now answered.

5. **What the twin and mock fakes need**: nothing new in `tests/machine.py`'s `SPI` /
   `digital_twin/machine.py`'s `SPI` (their `write`/`readinto`/`write_readinto`/`init` are already
   synchronous, as the real ones are), nothing in `tests/_fram_chip_fake.py`'s `FakeMB85RS64V` or
   `digital_twin/_fram_chip.py`'s `FramChip` (they model the chip at the byte level, which is
   what the synchronous path drives). The fault-injection hooks the twin hazard tests use
   (`_spi.device` write/read faults, the rx-overrun path) keep working because the byte-level
   calls are the same calls.

### A.2 Tests first (mock tier, `tests/`)

- [x] **The trace-equality invariant becomes a test**: `tests/test_asy_fram_wire_trace.py` (new),
      built from `proto.py`'s recorder (§10): wrap `tests/machine.py`'s `SPI`/`Pin` to record
      every CS edge, every `init`, and every transfer's bytes; run `PrintLogHistoryStore.setup()`
      against a blank chip and against a valid chip; assert the recorded traces equal the
      **golden traces checked in from the current `src/`** (342 events / 74 CS blank, 219 / 47
      valid). Written and passing against today's code *before* any refactor, so the refactor
      is measured against it. Also a `write_into` and a `read_into` on a
      `AsyFramTimestampedChunk`, and a `clear()`, each with its own golden trace. Verified to
      bite by deliberately dropping one WRDI.
      **Done**: `tests/test_asy_fram_wire_trace.py`, 8 tests, green against today's `src/`. The
      mock tier reproduces the twin's counts exactly - 342 events / 74 CS blank, 219 / 47 valid -
      plus 230 / 50 for a timestamped `write_into`, 224 / 48 for `read_into` and 138 / 30 for
      `clear()`. The golden form is one line per CS cycle; the envelope (one `SPI.init()` at the
      fixed bus config, one CS low/high pair, no transfer outside a CS window) is asserted rather
      than elided, and a test proves the compact form accounts for every raw event. Both bite
      checks pass: a single dropped WRDI and a single changed payload byte each fail it.
- [x] **`tests/test_asy_spi_driver.py`** (49 tests today, at the base branch's state): add the
      synchronous session's own tests mirroring the async ones that apply — `session_begin`
      raises before `setup()`, CS active only inside, deassert on exception in the body,
      `configure` applied fresh per session, two devices sharing a bus never have CS asserted
      simultaneously when the caller holds the lock, `readinto_sync` propagates the rx-overrun
      `OSError(EIO)` and still deasserts CS. Add, written fresh: the async session has **no
      scheduling point between CS assert and CS deassert** (the §5.1 hazard, closed), and a burst
      of 20 async sessions lets another task run >= 20 times (the §8.1 regression, covered). The
      one existing test that asserted the *awaited* settle's scheduler pass inside the session
      (`test_session_does_not_yield_to_other_tasks_while_cs_is_asserted`'s base-branch form, if it
      pins the old behaviour) is rewritten to the new invariant — the only edit to an existing
      test, and it is named here so it is not mistaken for a silent change.
      **Correction**: no test of that name exists on the base branch. The one that actually pinned
      the awaited settle is `test_aenter_releases_the_lock_if_cancelled_during_the_settle_sleep`,
      which cancelled a task parked *at* the settle and asserted the lock was released. It is the
      one rewritten, to `test_entering_a_session_is_atomic_so_cancellation_lands_only_after_it`:
      there is now no suspension point between acquiring the bus lock and releasing it, so the
      cancellation lands after the session, with the lock released and CS deasserted. Every other
      test that yields inside a session supplies its own `await asyncio.sleep(0)` in the body and
      was unaffected.
      **Done**: 49 -> 62 tests, all green, and the wire traces unchanged. Names settled:
      `session_begin()`/`session_end()` plus `write_sync()`/`readinto_sync()`/
      `write_readinto_sync()` are the new plain functions; the async `__aenter__`/`__aexit__`/
      `write`/`readinto`/`write_readinto` keep their names and are re-expressed on top of them, so
      no public entry point changes. The caller-holds-the-lock contract needed no new guard:
      `SPI.configure()`'s existing `First acquire async lock!` check already enforces it, and a
      test pins that.
- [x] **`tests/test_asy_fram_driver.py`** (71 tests today): every existing test stays green
      unchanged. Add: the 5-CS envelope is issued under **one** bus-lock hold (count acquire/
      release on `spi.async_lock`), `set_values()` yields exactly once per byte-level command
      (count scheduler passes with the existing `_StepPoller`-style counting), and each of
      `wrnno` 81/82/84 is still persisted from `set_values()`/`set_write_protected()` with the
      same message (three tests, one per number, asserting the FRAM-backed logger's history).
      **Done**: 71 -> 78 tests, all green, wire traces unchanged. The three warning tests record
      every `wrn_s()` call and assert the full `(message, wrnno)` pair and that it is logged
      exactly once, which is what "the logging site moves up, the number and message do not" needs
      pinning. Read commands get the same one-hold and one-yield tests as writes. One test in
      `tests/test_asy_fram_wire_trace.py` changed with the implementation: its bite check patched
      `FRAM_SPI._send_opcode(opcode: int)`, which is now `_send_command(command: bytes)`.
      Measured on the mock tier, settrace binary, median of five: a blank logger `setup()` went
      820,096 -> 299,328 B and a valid one 564,960 -> 238,368 B with only A.1.1 and A.1.2 in place.
- [x] **`tests/test_asy_fram_manager.py`** (105 tests today): every existing test stays green
      unchanged. Add: `_set_check_sb`/`_handle_status_bytes` errno spreads reproduced from the
      public `write`/`read`/`clear` entry points for every branch (`err`, `err+1`, `err+2`,
      `err+gap`, `err+2*gap` for `check_idle=True` and `False`); a block operation yields at
      least once between its two status-byte pairs (a concurrent task observes progress); the
      `compare_with` scratch buffer is allocated once per chunk, not per call; a `MemoryError` on
      that allocation at construction degrades the chunk the same way a negative `check_length`
      does today.
      **Done**: 105 -> 114 tests, all green. The six errno branches that had no coverage are
      now pinned from the public entry points: 19 and 20 (`_write_chunk`'s IDLE mark, bytes 1 and
      2), 33, 34 and 35 (`_read_chunk`'s BUSY mark on status byte 2 - read failure, not-idle, write
      failure) and 51 (`_clear_chunk`, byte 2). The progress test is stronger than "yields at least
      once": a concurrent task observes the block marked BUSY *and* IDLE again during one
      `write()`, which a non-yielding block operation could not show.
      **Deviation from A.1.3, bullet 1**, in its final form. Once the owner chose
      per-block-operation locking, the manager *does* hold the bus across the block operation, so
      the helpers' callees became the synchronous `get_values_sync()`/`set_values_sync()` and the
      per-command coroutine and lock went away. The helpers themselves stay coroutines, for a
      different reason: each of their branches logs a distinct message with a distinct number, and
      a persisted log entry is an `await`. Making them synchronous would recover ~1,700 B only by
      moving those messages off their decision sites, which C.7.1's auditability does not clearly
      permit. Recorded in §7C.1 as available, not taken. Their
      logging also stays at its own site: the reason for moving reporting up in the driver was
      that those bodies hold the bus lock and must not await, and these do not. What was taken
      from the bullet is the part that actually costs bytes - the per-call `bytearray(1)` and
      `bytearray([val])` become one `bytearray(1)` per chunk, the `_compare_with` scratch buffer
      and its memoryview move to construction, the two per-call callback closures become chunk
      state and one plain `_read_progress()` taking ints, and `_read_chunk`'s per-iteration slice
      tuples and doubled `mv[a:b]` slicing collapse to one slice per iteration.
- [x] **Allocation-count test, board-comparable**: `tests/test_asy_fram_allocation_budget.py`
      (new) — one blank `setup()` and one valid `setup()` each inside a collection-free window
      (the §1.2 identity `(free_before − free_after) == (alloc_after − alloc_before)` asserted),
      asserting the retained-plus-transient bytes are below a budget set from §3B.3 with margin
      (**≤ 8,192 B blank, ≤ 5,120 B valid on the settrace build**; the exact numbers are set from
      the first passing run and recorded in the test's own comment with the settrace caveat, §1.2
      item 7). This is the (e)-stage test pair I.4 asks new code to carry, in its efficiency
      form; it fails if a coroutine-per-cycle regresses back in.
      **Done**: `tests/test_asy_fram_allocation_budget.py`, 3 tests. The projected budgets did not
      survive contact with the measurement and are replaced by measured ones, with ~15% margin and
      a pair per build selected at runtime on `hasattr(sys, "settrace")`: 344,000 B blank /
      270,000 B valid on the settrace build, 34,000 / 24,000 on a settrace-free one. A third test
      asserts the budgets are not trivially satisfied, and the pair was confirmed to fail against
      the pre-restructure `src/` (798,720 B and 549,248 B on the settrace build).
- [x] **Hazard tiers 1 and 2** (CLAUDE.md's standing four-tier rule): FRAM has no I2C neighbour
      and sits alone on `spi0` in every device TOML, so the cross-device scenarios are the
      *twin* tier's real task graph under bus load. `tests/test_bus_hazard_multi_device.py`
      gains the one shape the generated scheme cannot produce for SPI — two `SPIDevice`s on one
      `SPI` bus, one driven through the synchronous session and one through the async one,
      interleaving under the shared lock without CS overlap (this is what "future multi-device
      SPI compatibility" means in a test). `tests/test_digital_twin_bus_hazard_concurrency.py`'s
      ten tests (FRAM fault injection, rx overrun, storage pause, write protect) run unchanged
      and are the twin tier's proof.
      **Done**: `tests/test_bus_hazard_multi_device.py` goes 8 -> 10, with the async and the
      synchronous session interleaving over twelve rounds each on one bus with no CS overlap, and
      an rx overrun inside the synchronous session leaving neither the shared lock nor the
      neighbour's access stranded. The twin tier's ten tests run unchanged.
- [x] **`tests/test_fram_integration.py`** (11) and **`tests/test_print_log.py`**,
      **`tests/test_notification_fram_integration.py`**, **`tests/test_ntp_fram_system_integration.py`**:
      run unchanged; they are the consumer-side pins of "public API unchanged".
      **Done**: all unchanged and green, together with `tests/test_base_classes.py` (119) and
      `tests/test_ntp_fram_system_integration.py` (12).

### A.3 Implementation

- [x] `src/asy_spi_driver.py` per A.1.1. Header docstring stays ≤ 3 lines; one short WHY note
      each on the blocking settle and on the post-session yield, next to the line.
- [x] `src/asy_fram_driver.py` per A.1.2.
- [x] `src/asy_fram_manager.py` per A.1.3.
- [x] `micropython.const()` for any new module-level constant that is an int; `bytes` constants
      for the opcode frames.
- [x] The trace test, the 51+71+105 existing tests and the new ones all green under
      `scripts/test.sh` (one Unix-port process per file, `-X heapsize` as set there).
- [x] `scripts/lint.sh` and `scripts/typecheck.sh` exit 0. **No `method-assign` suppression in
      `src/`** (the lint guard fails otherwise). `mypy --strict` on the three files: the
      synchronous/async pairs need no `type: ignore`.
- [x] Bird's-eye scan over `src/` (CLAUDE.md, "whenever a new file is added" — applied here to a
      new *shape*): `asy_i2c_driver.I2CDevice` inherits `Lockable`'s async session too, and the
      PR #105 description already reports it has no scheduling point per burst. **Do not extend
      the synchronous session to I2C in this work**; record the discrepancy (SPI now has a
      synchronous form, I2C does not) in BACKLOG.md as a flagged, not fixed, item — CLAUDE.md's
      flag-don't-fix rule and F.5.8's explicit refusal to generalise.
      **Done**: recorded in BACKLOG.md's deferred list. The scan found no other divergence - the
      synchronous/async pairing is confined to `SPIDevice`, `I2CDevice` has no CS pin, no
      per-session `configure()` and no settle to make synchronous, and every other `src/` module
      reaches the bus through one of those two.

### A.4 The digital twin

- [x] `scripts/run_digital_twin_ci.sh` / `scripts/_digital_twin_ci_suite.py` full sequence green
      at **both** `gc.threshold(-1)` and `32768` (it already runs both, in that order — I.4(e)
      then (f)). Run 11's `gc.mem_free()` trend check is the twin's run-phase leak guard and must
      stay within tolerance; the restructure changes the allocation pattern of every run-phase
      error persist, so the soak is the test that would show a new leak.
      **Done**: "every check succeeded at both gc.threshold(-1) and gc.threshold(32768)". Run 11's
      trend is a **1,274 B decline against a 12,790 B tolerance** over 808 samples, with 840 soak
      requests across every endpoint producing zero HTTP failures, the watchdog never starved, and
      zero `MemoryError`s anywhere in the sequence — caught-and-logged included, which the suite
      counts as a failure. Run 10's watchdog backstop still engaged for a genuinely wedged bus
      (`would_have_triggered_count=2`), so the blocking settle did not blunt it.
      **Re-run after the §11 item 6 rebuild**: passed again at both thresholds, Run 11's trend a
      1,021 B decline against an 11,749 B tolerance over 817 samples. One established test in
      `tests/test_digital_twin_sensortask_integration.py` needed fixing for it — see A.3's note.
- [x] `tests/test_digital_twin_sensortask_integration.py` (13 tests, including the hotspot-
      fallback one `f6a182d` once broke) green in isolation 5 of 5 runs — the scheduling-point
      regression of §8.1 is exactly the class of fault a yield-policy change can cause, and this
      is the file that caught it.
      **Done**: 13/13 on all five isolated runs — and this is the file that caught the one real
      consequence of making the FRAM path faster. `test_wifi_sta_failure_falls_back_to_hotspot_...`
      scripted a *single* `STAT_NO_AP_FOUND`, and `digital_twin/network.py`'s queue falls back to
      always-succeeding once exhausted, so the test hinged on that failure resolving *after* its
      `connection_failures = 4` seeding, separated only by `await asyncio.sleep(0.2)`. That window
      was only ever won by `wlan_connect()`'s prefix — two FRAM-backed `pr.setup()` calls — being
      slower than 0.2 s, and at 9.0x it no longer is: 2 of 2 runs failed. Ruled out as a deadlock
      (every FRAM lock free at the timeout, the WiFi warning persisted) and as the `_read_chunk`
      yield bug (it reproduced with that fixed). The test now scripts eight failures, so either
      ordering reaches `conn_fail_to_hotspot=5` through the same real state machine: 5 of 5 pass.
      Slowing production code to fit a test's timing window would have been the wrong direction.

### A.5 Measurement, A alone (twin, no hardware)

- [x] Re-run the §7A.8 protocol on the real path with A in place: settrace-free binary
      (`build-nosettrace`, §10), `gc.threshold(-1)`, calibrated heap (508k after
      `build_system()`, 560k after the task list), 15 + 6 perturbations, **largest/free** as the
      metric and the bare fill reported. Record as §7C in `HEAP_FRAGMENTATION_MEASUREMENTS.md`
      beside `base`'s 11.9-14.2% / 8.1-8.4% and the synthetic prediction for a 38x cut (9.6%,
      i.e. no layout gain expected from A alone — §7B.1). The point of this row is the honest
      (e)/(f) record, not a pass.
      **Done.** Recorded as §7C.2. **Superseded in its headline by §7D [HW], 2026-09-18: on real
      silicon A improves the in-suite largest block by 40.2% (20,592 → 28,864 B).** The twin
      measured a cold, single-purpose process, which §7D.2 shows is the configuration the defect
      does not appear in — `Board.run_isolated()` never resets, so a device script builds inside
      `main.py`'s aged heap. What follows is the [TWIN] record, still valid for construction cost
      and for the variance removal §7D.4 confirms on silicon.
      §7B.1's prediction holds *on the twin*: **A does not move the ratio and is
      slightly worse** — 12.4% against `base`'s 14.2% median after `build_system()`, 7.4% against
      8.4% after the whole sequence, with all six matched pairs below `base`. A is flat across the
      ten comparable `k` perturbations at 508k (31,328 B every run, against `base`'s 1.24x spread)
      but **not** flat at 560k (6.7-8.1%), so the churn removal reduced sensitivity to a seam
      survivor without eliminating it. The mechanism of the loss is priced: A retains **+7,232 B**,
      all of it at construction, 3,200 B of it the 20 chunks' hoisted buffers measured directly.
      **One instrument family had to be invalidated first**: the `q` perturbation injects churn
      inside `SPIDevice.__aenter__`, which A's FRAM path never enters, so it fires 74x per logger
      on `base` and 0x under A — excluded from every comparison, and it is what produced `base`'s
      apparent 30,752-60,800 B swing. The tripwire needs B, or B plus C.
- [x] Re-run the allocation census of §3A.3 for one logger `setup()` on the settrace-free build
      and confirm the 38x against the prototype's 3,072 B (the prototype was not the real code;
      this is the first real number).
      **Done, and it does not confirm the 38x.** Recorded as §7C in
      `HEAP_FRAGMENTATION_MEASUREMENTS.md`. Board-equivalent on the twin, median of five, in the
      shipped per-block-operation lock scope: a blank `setup()` costs **13,696 B against the base
      branch's 122,880 (9.0x)** and a valid one **9,152 against 80,384 (8.8x)**. The per-command
      scope A.1.4 had chosen measured 18,240 / 13,536 (6.7x / 5.9x) — the arm the owner replaced
      (§11 item 6, answered 2026-09-18), kept in §7C's table for the comparison. The synchronous
      five-CS write envelope itself is down to **32 B**, so the bus work is effectively free; what
      is left is await machinery, and §7C.1 has the per-node table plus the three residue terms
      that belong to A.7, A.8 and C.7.1 rather than to this measure. The ensemble measurement
      above is unblocked now that the scope is settled, and has not been run.

### A.6 Decision gate after A

- [x] **Owner's decision, and the criterion is corrected here.** This box was written as "does A
      alone clear the tripwire" — the wrong test: the 80,000 B floor is a regression tripwire at
      69% of one healthy board reading, not a demand any allocation makes (§7A.8, §7A.9), and the
      goal is fewer long-lived survivors scattered through the heap. **On the goal as stated, A
      alone does not get there either** — though §7D [HW] has since shown it gets **40.2% of the
      way** on real hardware, where the twin saw nothing, so the reasoning below understates A and
      the conclusion (B is still needed) is unchanged rather than merely intact:
      §7C.2 measures the survivor scatter essentially unchanged
      (44-50 distinct free runs at 99% span against `base`'s 52-55 at 97-98%; 288 → 258 survivors,
      an axis §6A.12 puts an order of magnitude below its own threshold) and the ratio slightly
      worse. So B is not pure defense in depth, it is what §7B.5 says it is, and I.4 is amended as
      B.4 states — **which is the owner's call to make, since B.4 rewrites a standing
      prohibition.**
      **ANSWERED, owner, 2026-09-18: "A6 is free from my side."** B.4's amendment is granted, so
      measure B is unblocked. The gate itself is void rather than passed — it could only ever
      resolve one way once the tripwire stopped being the criterion. **B is deliberately not
      started**: the owner asked to wait for an explicit go, because real-hardware measurements
      are coming and may change what B is measured against.
- [ ] Reopen §3B.4 lever 3 (the lock hierarchy) **only** if the combination in B.6 falls short
      and the measurement points at within-module smear rather than between-module placement
      (§7B.3 says which is which: collects fix between-module, churn fixes within-module).

### A.7 Follow-ups A creates, outside the three files (each its own decision, none silent)

- [x] **Measured on the owner's instruction, and the recommendation is against it** (§7C.3):
      saves 288 B per FRAM operation and **0 B** at `setup()`, while costing 299 B of permanent
      retention per store — ~6,300 B across the 21 stores. A ~1:1 trade of transient churn for
      permanent survivors, which is the quantity the goal names. Owner's decision.
- [x] `AsyFramChunkBuffer` per store instead of per `get_buffer()` call: `print_log.py`'s
      `_write()`/`_read()` and `asy_sgp40_driver.py`'s `ts_storage` paths.
      **RULED OUT, owner, 2026-09-18.** Not to be built. The measurement above is the reason: it
      trades transient churn for permanent survivors at roughly 1:1 and saves nothing in the phase
      the defect lives in. No scoped exception is needed after all, and `print_log.py` /
      `asy_sgp40_driver.py` stay untouched.
- [x] BACKLOG entry: I2C has no synchronous session form (A.3's flagged discrepancy).
      **Done** — `BACKLOG.md`'s deferred list, recorded as flagged and not fixed.

### A.8 §11 item 1, folded in only if the owner says so

- [x] **Measured on the owner's question** (§7C.3): the assumption is sound for the large
      buffers (256 B SGP40 backup, 255 B UART max), the means is too fine (per-byte yielding costs
      **5.8x the total wall time**), and it recovers **no memory at all** — allocation is a flat
      160 B per `_crc` call regardless of length, since `sleep(0)` is free on this build. The fix
      is size-dependent, not granularity-only. Owner's decision.
- [x] `src/crc_checks.py`'s `_crc()` yields after every byte.
      **CLOSED, owner, 2026-09-18: "pure wall clock time is not such an issue, don't touch."**
      `crc_checks.py` is not to be modified. It recovers no memory (§7C.3), so it was never part
      of the remediation; the 5.8x wall-time cost is accepted, and the owner's original reason for
      the per-byte yield stands. **Not** carried to BACKLOG as an open item — it is decided, not
      deferred. §11 item 1 is closed with it.

## B. `gc.collect()` confined to the two boot lists

### B.1 Design, decided

Exactly the owner's scheme (§7A): at the start of the setup list, after each module's `setup()`,
at the end; and the same on the task-starter list. Two sites, both in code the system's own boot
owns:

1. **The generated setup batch** — `buildgen/codegen.py`'s `_emit_build_system()` emits, for each
   `name` in `setup_order`, `await {name}.setup()` then `sysfunct.feed_watchdog()`. It gains a
   `gc.collect()` line **before the loop** and **after each `feed_watchdog()`** (the collect
   after the last module is the end-of-list collect). Emitted, not hand-written: every device's
   `sensortask_<device>.py` gets it identically. `import gc` is added to the generated module's
   imports.
2. **The task-starter list** — `system_service.SystemService.start_and_check_tasks()`'s
   `for n, starter in enumerate(task_starters)` loop gains `gc.collect()` before the loop and
   after each `_start_task()`/`sleep` pair. **None inside the `while True` supervisor** — that is
   the run phase, and the test in B.2 asserts it.

Why these and only these: the generated batch and the starter loop are the only two places the
firmware's permanent objects are born in sequence; `feed_watchdog()` already marks each boundary
in the batch (§7A.1 used exactly that seam). The collects are placement resets — each one puts
the allocator's free-scan index back to zero (`py/gc.c:612`, `gc_collect_end()`), so the next
module's survivors take the lowest fitting holes — not hygiene and not compaction (§7A.4); the
docstring says so in one line, the rest points at `SPECIFICATION.md` I.4's amended (f).

Cost: 10 + 22 mark-sweeps at boot on `dev`, each next to an existing watchdog feed; "several
milliseconds ... about 1ms on the Pyboard" per the pinned docs; boot latency is not a metric
(CLAUDE.md), starving the watchdog is, and the collect sits *after* the feed.

### B.2 Tests first

- [x] **`tests_scripts/test_buildgen_generate.py`**: beside
      `test_real_device_feeds_the_watchdog_after_every_setup_call_in_order`, a test that for every
      real device the generated `build_system()` has `gc.collect()` immediately before the first
      `await ….setup()`, immediately after every `sysfunct.feed_watchdog()`, and **nowhere else
      in the generated module** (count == len(setup_order) + 1); and that `main()` and every other
      generated function contain none.
- [x] **`tests/test_system_service.py`** (83 today, 85 now): `start_and_check_tasks()` calls
      `gc.collect()` exactly `len(task_starters) + 1` times before the first supervisor pass and
      **zero** times during N supervisor iterations (patch `gc.collect` with a counter the way the
      file already patches `machine`/`time`; the supervisor loop is driven with the existing
      `_TASK_CHECK_TIME` fakes). Also: an empty starter list still collects once (the start-of-list
      collect) and never fails.
- [x] **`tests_scripts/test_digital_twin_generated_boot.py`**: the real generated module boots
      and serves over HTTP with the collects in (both existing tests, unchanged). **Confirmed** —
      both pass untouched in the full suite run above.
- [x] **A guard test for the guard**: `tests_scripts/test_gc_collect_sites.py` (new, 4 tests) walks `src/`
      and `buildgen/` with `ast` and asserts `gc.collect(` occurs only in
      `system_service.py:start_and_check_tasks` and in `codegen.py`'s emitter string — the same
      assertion `scripts/lint.sh`'s grep makes (B.3), expressed structurally so a rename of either
      site fails the test rather than silently widening the allowance.

### B.3 Implementation

- [x] `buildgen/codegen.py` per B.1.1 (`_emit_build_system` and the import block); regenerate
      nothing by hand — `scripts/build_firmware.py`/the twin generate at build time.
- [x] `src/system_service.py` per B.1.2, with `import gc`.
- [x] **`scripts/lint.sh` guard** — **done.** `gc.collect(` under `src/` is allowed only in
      `src/system_service.py` and under `buildgen/` only in `buildgen/codegen.py`; anything else
      fails the lint gate naming `SPECIFICATION.md` I.4(f.1). Verified to bite: an injected
      `gc.collect()` in `src/print_log.py` failed lint (and the structural test) and passed again
      once removed.
      **History worth keeping, because the rule moved underneath it.** This was first written,
      verified, then **reverted**, because touching `scripts/` triggered CLAUDE.md's two-target
      clean-chroot *pre-push gate* and the trixie leg cannot run in this environment —
      `deb.debian.org:443` is `connect_rejected` by the sandbox's egress policy (confirmed against
      the agent proxy's own status endpoint; the noble leg got as far as `typecheck.sh` and died on
      a cut-off PyPI transfer, which is transient). It was then restored on merging the base
      branch, which carries the owner's decision of 2026-09-18 that **the two-target verification
      is an owner-run periodic check, not a blocking per-push gate** (`BACKLOG.md`).
      **The contradiction this entry flagged is gone** (re-checked 2026-09-19): the same base move
      also rewrote CLAUDE.md's own section, which now opens with that decision in as many words, so
      CLAUDE.md and BACKLOG.md agree. One leftover phrase inside its chroot recipe still said
      "pre-push gate" where it meant "the working tree, not a branch"; reworded, since it is
      wording rather than a rule.
- [x] `scripts/lint.sh`, `scripts/typecheck.sh`, `scripts/test.sh` exit 0. **Done**: lint clean,
      typecheck 157/47/105, suite 85/85 MicroPython files and 1237 pytest passed / 7 skipped.

### B.4 The rule amendment (`SPECIFICATION.md` I.4, CLAUDE.md)

- [x] **I.4(f)** gains one paragraph — added as **(f.1)**, its own lettered sub-item so (f)'s
      threshold rule and the boot exception cannot be confused: the boot-confined placement reset — `gc.collect()` between
      the units of the two one-time setup lists, emitted by `buildgen` and owned by
      `SystemService`, and nowhere else — is *not* a threshold and *not* a fix for an allocation
      that fails; it is placement discipline for the survivors those lists create (§7A.4's
      mechanism, `py/gc.c`'s free-scan reset), grounded in the pinned MicroPython documentation's
      own recommendation (`docs/reference/constrained.rst:413-437` at `v1.29.0`: a demanded
      collection "is advantageous ... firstly to preempt fragmentation", and "`gc.collect()`
      issued after the import will ameliorate the problem"). The measured effect on the (e)-stage
      configuration is stated with its number (§7A.8), so nobody later mistakes it for (f)-stage
      margin. Confined by `scripts/lint.sh` (B.3) and the structural test (B.2). The prohibition
      for business logic and the run phase is restated unchanged.
- [x] **I.4(e)**'s "no added `gc.collect()` calls anywhere in the business logic or the test's own
      setup" gains the cross-reference to (f)'s boot exception so the two paragraphs cannot be
      read as contradicting each other.
- [x] **CLAUDE.md**'s memory-safety hard rule (the "Standing rule, every test" sentence) gets the
      same one-clause cross-reference, no more — CLAUDE.md points, `SPECIFICATION.md` holds.
- [x] **`heap_headroom_after_full_system_build.py`**'s comment — and it also now records §7D.2's
      suite-position dependence, which makes the figure comparable only against like positions: the script still asserts before
      any threshold is set; note that `build_system()` now carries the boot collects, so the
      figure it asserts is the with-collects layout, and that a number below the floor means the
      layout regressed past what the collects recover (the dampening §7B.2 names).

### B.5 The digital twin

- [x] Full twin CI sequence green at both thresholds (as A.4). **Done**: "every check succeeded
      at both `gc.threshold(-1)` and `gc.threshold(32768)`" — I.4(e) then (f), in that order, with
      the collects in. Run 11's soak trend is **-3,692 B** (free *grew*) against a 13,719 B
      tolerance, and zero `MemoryError` anywhere, caught-and-logged included.
- [x] `digital_twin/run_generic_integration.py` needs no change: it runs the generated
      `main()`, so it gets the collects the way the board does. **Confirmed** — no twin file was
      touched, and the twin CI above exercised the collects through the real generated module.

### B.6 Measurement, A + B (twin, no hardware)

- [x] §7A.8's protocol again, real path, A and B both in. **Done, recorded as §7E** (its own
      section rather than a second §7C row set — §7C is now three subsections about A). **86.2-86.3%
      after `build_system()` and 87.5-90.2% after the whole sequence**, against `base`'s 14.2% /
      8.4% and B-alone's 45.0% / 57.8%; 10/10 and 6/6 clear both the 55% and the conservative 74%
      form. Largest contiguous 217,680 B / 255,824 B median, cross-checked by actually allocating
      it (`probe_largest` agrees to 8 bytes). The proxy's 87.5% prediction landed on the nose. The
      two levers **compound**: A alone is worth nothing on this metric, B alone 45-58%, together
      86-89%.
- [x] The same at `threshold(32768)`. **Done, §7E.2: 95.9% / 95.5%**, and 4-5 points above
      B alone there too. §7A.6's "changes nothing measurable" still reads correctly as a statement
      about B alone; the (e)-stage gain is where this scheme earns its place.
- [x] Survivor placement. **Done, §7E.1: zero survivors in the top four deciles** (`base` puts
      150 of 288 there), span 98% → 53-55%. §7A.4's predicted shape, on the real code. One
      instrument fault had to be fixed first — `basex` replicates the starter loop instead of
      calling it, so it never reached B's second collect site (§7E.3).

## C. The seam + contiguity guard (§12, carried forward; the thing that restores the tripwire's sensitivity)

- [ ] `tests/test_digital_twin_boot_contiguity.py` (new), written test-first and verified to fail
      when the invariant is deliberately broken (e.g. by disabling one collect): boot the real
      generated module for `wozi` and `dev` in the twin at the calibrated heap, and assert
      **absolute largest-contiguous against free** at the seam (after construction, before the
      setup batch) and after `build_system()`, and again after the task-starter list, with the
      perturbation held constant (§9's last row: a probe that varies its own retained size
      invalidates the comparison). The thresholds are set from B.6's measurement with margin, on
      the twin's own units (32 B blocks, x86-64), and stated as twin-only in the test's comment —
      the board's tripwire stays the hardware test.
- [ ] Runs at `gc.threshold(-1)` only (it is an (e)-stage test); listed in `scripts/test.sh`'s
      per-file loop like every other `tests/test_*.py`.

## T. Real hardware (needs its own go-ahead, in the session that runs it)

**The runnable form of this section is two files.** `REAL_HARDWARE_TEST_QUEUE.md` §1A covers
measure A and is **fully run as of 2026-09-18** — results in §1A's own rows and
`HEAP_FRAGMENTATION_MEASUREMENTS.md` §7D. What is still owed is measure B, whose runnable form is
`REAL_HARDWARE_HANDOVER_MEASURE_B.md`, indexed by queue §1B: two firmware images, the readings in
order, and each prediction with the result that would falsify it. **Both that handover and the
script it drives changed on 2026-09-19** — one of §7F's readings was a probe artefact and another
named the wrong position (§7F.8, §7F.9), so the instrument now reports `retained=` and
`after_starter_loop_end`, and what is owed is two invocations rather than a redesign. The boxes below stay here as this
plan's own record; a session at the bench should work those two.

- [~] **T.1 Tripwire — RUN, both columns, one residue** (§7F.1 [HW]). A: 20,592 → 28,864 B in-suite,
      +40.2 % (§7D.3). A + B: **PASSES in-suite**, the first image ever to, against a BEFORE arm
      reading 28,736 B and failing. What is still owed is only the exact AFTER `largest_block` —
      the test discarded it on a passing run, now fixed host-side (§7F.6), so the next in-suite run
      yields it. Note §7D.2's correction to this box's own premise: only *like suite positions* are
      comparable, so a standalone reading does not answer it.
      **Original text:** `tests_hardware/flash/test_memory_stress.py::
      test_real_gc_heap_headroom_survives_a_full_system_build` with A alone, then with A + B:
      `free` and `largest_block` after `build_system()`, `threshold(-1)`, on the `dev` board.
      Against the 80,000 B floor, since retired (§7G). Record both readings in `HEAP_FRAGMENTATION_MEASUREMENTS.md`
      §2.1's [HW] table as the third and fourth columns.
- [~] **T.2 Bus-hazard tiers 3 and 4 — flash tier done, bench tier owed.** §7F's AFTER arm ran the
      full flash suite with **zero failures**, which covers all three FRAM tests; §7F.7 calls out the
      two rewritten injectors passing on *both* arms specifically, the first real-chip proof the
      hijacked payload is refused. The bench tier's six were last run on the A-only arm (§7D.5), not
      on A + B. **Original text**:
      `tests_hardware/flash/test_bus_concurrency.py`'s three FRAM tests
      (`test_fram_same_device_read_write_concurrency`, `test_fram_cs_pin_hijack_fault_injection_and_recovery`,
      `test_fram_hard_reset_race_during_write_and_recovery`) and
      `tests_hardware/bench/test_bus_concurrency_under_api_load.py`'s six (each asserts FRAM
      stays initialized and responsive under API load) — all green. No flash-cycle or
      persistence-write marker is needed by any of them beyond what they already declare; FRAM
      is out of the wear gate's scope.
- [ ] **T.3 Every FRAM device script** under `tests_hardware/device_scripts/fram_*.py` (**13**,
      not the 12 this said before the count was checked: roundtrip, capacity, CS hijack,
      busy-status lockout, pause gating, write-protect, the two reset-race pairs and the
      error-log reset-race trio — plus `sgp40_fram_backup_restore.py`, which is not `fram_*`-named
      but is the same proof) green — they are the real-chip proof that every safety measure
      survived the restructure. **Read the FRAM-backed error logs before any `ResetErrors`**
      (CLAUDE.md), and remember these scripts overwrite production's first chunks.
- [ ] **T.4 Hold time, measured** (F.3, §3B.5): a device script that times one byte-level write
      (5 CS) and one `check_length` read slice with `time.ticks_us()` around the synchronous
      stretch, reported in the script's `RESULT:` line; the number goes into `SPECIFICATION.md`
      F.5's SPI notes beside the UART 4.4 ms figure. If it is above ~1 ms, the per-command yield
      policy is already the finest the chip allows and the finding is recorded, not "fixed".
- [x] **T.5 Boot cost of B — DONE** (§7F.7 [HW]): `build_system_ms` 943 → **1,402 ms**, so B's 11
      batch collects cost ~455 ms, about **41 ms each** on the RP2040's real heap — ~85x the twin's
      figure, and the first RP2040 collect cost this project has measured. Far under the 8,388 ms
      watchdog cap; no `WDT_RESET` across the run's reboots. `start_timers_ms` is unchanged at 789.
      **Original text**: `time.ticks_ms()` across `build_system()` and across the starter
      loop, before and after, one line each — for the record only (boot latency is not a
      metric), and to confirm no watchdog starvation on the 8,388 ms cap with the collects in.
- [ ] **T.6** `tests_hardware/flash/test_memory_stress.py`'s second test and the bench memory
      stress (`tests_hardware/bench/test_memory_stress_bench.py`) green — the run-phase check on
      silicon.
- [ ] **T.7 The starter list's own reading, which no run has taken** (added 2026-09-19, queue B6).
      §7F.2's `after_starter_list` figures are taken 4 s into the run phase, and the twin loses most
      of B's gain inside the first ~2 s there (§7F.9) — so measure B's second site has never been
      measured on silicon at all. `heap_layout_after_full_boot_sequence.py` now reports
      `after_starter_loop_end`, detected by counting starters rather than waiting a constant. Two
      invocations, one per arm, each right after that arm's suite run so the heap is aged. It also
      replaces the row §7F.8 withdrew and confirms `retained=0` on the probe.

## D. Documentation, the PR, and closing

- [ ] `HEAP_FRAGMENTATION_MEASUREMENTS.md`: §7C (A alone; A + B), §11 items 2 and 4 marked
      decided with the date and the owner's words; §0 ledger rows O12/O13 updated with the real-path
      figures; §12's guard item struck.
- [ ] `SPECIFICATION.md`: I.4 per B.4; C.3.1's `FRAM_SPI` bullet and A.4's FRAM description gain
      the synchronous-form sentence; F.5 gains T.4's number; C.7.1 unchanged (verified, not
      assumed — every number re-traced to its entry point after A.3).
- [ ] `CLAUDE.md`: the memory-safety hard rule's cross-reference (B.4); the "Do not rewrite
      `asy_fram_manager.py`/`asy_fram_driver.py` internals without a scoped exception" sentence
      in the PR description's "Constraints carried over" is superseded and says so.
- [ ] `BACKLOG.md`: A.7's two entries; nothing else new (open question 6 and the FRAM
      `verify_present()`/`set_write_protected()` "SETTLED" item are untouched).
- [ ] README.md's "Further reading": this file listed while it exists, then removed with it.
- [ ] Commits: one per lettered step with a message that says what and why; the PR description of
      #105 (or a fresh PR if #105 is merged first — a merged PR is finished, restart the branch
      from the base) updated per step; `subscribe_pr_activity` stays on.
- [ ] Verification statement in the PR, in this order and by exit code: `scripts/lint.sh`,
      `scripts/typecheck.sh`, `scripts/test.sh` (83+ files), the twin CI sequence at both
      thresholds, the chroot gate for B.3's `scripts/lint.sh` change (both targets, named), and
      the hardware tiers' status (run with the go-ahead, or explicitly not run).

## What is not in scope (so it is not done by accident)

- Changing any byte on the wire, any CS-cycle count, or any status-byte semantics.
- Re-introducing a floor fitted to a board reading, in place of §7G's requirement-derived checks.
- `gc.collect()` anywhere but the two boot sites; any `gc.threshold()` change.
- Generalising the synchronous session to `asy_i2c_driver.py` (flagged, not done).
- §11 item 3 (deferring logger setup to one pass after the batch) — owner objection on record,
  and measured clean only at dose 1.
- §11 item 0 (the settrace-free test binary) — a separate toolchain decision; A.5/B.6 use the
  scratch `build-nosettrace` binary the way §10 documents.
- Editing `ext/microdot.py` (the `max_body_length` note in §7A.9 belongs to the webserver, not here).
- Anything in `python/`, `modules/`, or the four `build-*.sh` scripts.
