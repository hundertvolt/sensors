# UART protocol — changes to apply to the C implementation

**Temporary file. Delete it once the C implementation has been imported and reconciled** — it exists
only to carry protocol decisions across the gap until then, and has no value afterwards.

The UART message protocol (`SPECIFICATION.md` Part J) has two implementations: this repo's Python
module, and a C implementation on the Arduino peer that is not yet in this repo. The C side mirrors
the Python implementation's *intended* behavior and is owner-validated over many real transmissions,
but **how far that mirroring extends to the known flaws is unverified** — it may share some, not
others, and may have introduced its own. Every entry below is therefore a task for the reconciliation
session, not a description of what the C code already does.

## How to use this file

Every change to the module during its `src/` promotion gets an entry, in one of two classes:

- **Class A — protocol-level, must be mirrored in C.** It alters the bytes emitted, which received
  frames are accepted vs. rejected, or any timing the peer depends on.
- **Class B — Python-internal, no C impact.** Logged anyway, so the reconciliation session can see
  the change was considered and dismissed instead of re-deriving it.

**Standing preference: a Class A change should only ever tighten receiver validation, never alter
emitted bytes.** A receiver-strictness change rejects only frames a *conforming* peer never sends, so
new-Python ↔ old-C keeps working and the Arduino reflash can happen in either order. That safety
argument is conditional on the C side genuinely conforming, so **each Class A entry must be
re-verified against the real C source when it lands** — the "verify in C" column says what to check.
A change that alters emitted bytes is a coordinated flag-day and needs an explicit owner decision
before it is made.

Status values: `proposed` (agreed in principle, not yet implemented), `applied-python` (live in
`src/`, pending the C side), `reconciled` (done on both sides — entry can be removed).

## Class A — protocol-level

| # | Change | Rationale | Verify in C | Status |
|---|---|---|---|---|
| A1 | `CMD` validated by exact match against `ACK`/`GET`/`SET`, not by bitmask (`&`) | Today `0x06`/`0x03` pass validation and then match no dispatch branch, so a malformed frame is silently mishandled instead of rejected | Whether the C receiver also masks; whether the C sender can ever emit a multi-bit `CMD` | proposed |
| A2 | Reject a train whose declared `CHUNKS` changes between frames | Today a peer can truncate a transfer mid-train by re-declaring the total | That the C sender writes a constant `CHUNKS` across every frame of a train | proposed |
| A3 | Validate `UID` on data chunks, not just on ACKs | Today only ACK↔frame matching checks `UID`; a stale or duplicated data frame is invisible | **Blocking**: whether the C sender increments `UID` per chunk exactly as Python does (expected, unverified). Do not implement until confirmed | proposed, blocked |
| A4 | Recovery constants stay exactly as they are: drain until quiet for `1.5 × timeout`, then hold off initiating for a further `1.5 × timeout` | Not a change — recorded so the C side is known to be bound by the same constants. A peer draining for less transmits into the other's drain window | That the C side uses the same two durations, and that they are derived from its own `timeout` the same way | proposed (no-change) |
| A5 | Bound the receive-drain loop (today unbounded) | A peer that keeps transmitting keeps the drain looping forever | That the bound chosen is never shorter than the C side's own drain window | proposed |
| A6 | `payload_size` constrained to `1 … 255`, identical on both ends, never silently clamped | `SIZE`/`CHUNKS` are single bytes; a zero-width payload cannot carry the command ID. A mismatch desyncs the link outright | That the C side's compile-time constant is within range and matches the Python deployment value | proposed (constraint) |

## Class B — Python-internal, explicitly no C impact

| # | Change | Why it has no wire effect |
|---|---|---|
| B1 | Well-defined return value for the unexpected-command case in `uart_listen()` | Caller-facing return shape only; the frame is rejected either way (see A1 for the wire-visible half) |
| B2 | Replace the one-shot `machine.Timer` write re-enable with a `ticks_ms()` deadline | Same hold-off duration (A4); removes a dropped-soft-callback permanent hang |
| B3 | `Timer.init()`/`MemoryError` exception guards | Failure handling inside one implementation |
| B4 | Guarded callback dispatch, plus async-callback support, in the responder path | Callback API of the Python module; the peer never observes it |
| B5 | `print_log.py` logger instead of `debug`-gated `print()` | Observability only |
| B6 | Preallocated TX/RX frame buffers, `memoryview` chunking | Allocation strategy; identical bytes emitted |
| B7 | Typing, lint cleanups, and the mechanics of parameter validation (readiness gate vs. clamp) | Internal; the *constraint* itself is A6 |
