# UART protocol — changes to apply to the C implementation

**Temporary file. Delete it once the C implementation has been imported and reconciled** — it exists
only to carry protocol decisions across the gap until then, and has no value afterwards.

The UART message protocol (`SPECIFICATION.md` Part J) has two implementations: this repo's Python
module, and a C implementation on the Arduino peer that is not yet in this repo. The C side mirrors
the Python implementation's *intended* behavior and is owner-validated over many real transmissions,
but **how far that mirroring extends to the known flaws is unverified** — it may share some, not
others, and may have introduced its own. Every entry below is therefore a task for the reconciliation
session, not a description of what the C code already does.

**Deployment status (owner, 2026-09-11): the C implementation is prototypical, exactly like this
repo's legacy Python.** There is no device in the field running it, so **no pair can be broken by
any change recorded here** — neither a receiver-strictness change nor an emitted-bytes flag day has
a live cost today. The two sides are reflashed together whenever the reconciliation happens. Real
hardware running the C side exists and can be connected to the dev board, so the promoted module is
testable against the genuine second implementation rather than only against itself over the
crossover jumper. This removes the *risk* from the entries below, not the *obligation*: the point of
this file is that the reconciliation session finds every change already written down instead of
re-deriving it from two diverged sources.

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
A change that alters emitted bytes is a coordinated flag-day, and **the project owner has decided
(2026-09-11) that the Python side may lead it**: changing Python behaviour is allowable without
waiting for the C implementation, provided every change is recorded here for the reconciliation
session. The receiver-strictness preference above is therefore a *preference*, no longer a gate — but
the flag-day consequence still has to be stated per entry, because an emitted-bytes change means the
link does not work at all against an un-reflashed peer, rather than working in degraded form. Where a
change would strand a deployed Arduino, the entry says so and names the interim (usually: run the
link with CRC disabled, or keep the peer on the legacy build until it is reflashed).

Status values: `proposed` (agreed in principle, not yet implemented), `applied-python` (live in
`src/`, pending the C side), `reconciled` (done on both sides — entry can be removed).

## Class A — protocol-level

| # | Change | Rationale | Verify in C | Status |
|---|---|---|---|---|
| A1 | `CMD` validated by exact match against `ACK`/`GET`/`SET`, not by bitmask (`&`) | Today `0x06`/`0x03` pass validation and then match no dispatch branch, so a malformed frame is silently mishandled instead of rejected | Whether the C receiver also masks; whether the C sender can ever emit a multi-bit `CMD` | proposed |
| A2 | Reject a train whose declared `CHUNKS` changes between frames | Today a peer can truncate a transfer mid-train by re-declaring the total | That the C sender writes a constant `CHUNKS` across every frame of a train | proposed |
| A3 | Validate `UID` on data chunks, not just on ACKs | Today only ACK↔frame matching checks `UID`; a stale or duplicated data frame is invisible | Whether the C sender increments `UID` per chunk exactly as Python does (expected, unverified) — and, if it does not, that this validation is what will surface it | proposed |
| A4 | Recovery constants stay exactly as they are: drain until quiet for `1.5 × timeout`, then hold off initiating for a further `1.5 × timeout` | Not a change — recorded so the C side is known to be bound by the same constants. A peer draining for less transmits into the other's drain window | That the C side uses the same two durations, and that they are derived from its own `timeout` the same way | proposed (no-change) |
| A5 | Bound the receive-drain loop (today unbounded) | A peer that keeps transmitting keeps the drain looping forever | That the bound chosen is never shorter than the C side's own drain window | proposed |
| A8 | `UID` is never emitted as `0xFF`; the counter wraps `0xFE → 0` | Not a change — an author-confirmed invariant, recorded so neither side loses it. It is a deliberate off-by-one barrier so any `+1` on a received UID cannot roll over uncontrolled, and it keeps the UID space exactly as large as the longest train (no UID repeats within one transfer) | That the C counter also stops at `0xFE`, and that nothing there predicts the next UID with a bare `+1` instead of the same controlled wrap | proposed (invariant) |
| A7 | **The on-wire CRC changes algorithm and byte order**: `asy_uart.py`'s LSB-first variant over poly `0x1021`, packed native-endian → `crc_checks.py`'s MSB-first CRC-16/CCITT-FALSE, packed big-endian | Not a deliberate change — inherited from `asy_uart_driver.py`'s own promotion, which had no callers, so nobody noticed. Verified directly: each is self-consistent (residue zero), each rejects the other's frames | **The one entry so far that alters emitted bytes, so the either-order safety argument does not apply — both ends must be changed and reflashed together.** The C side's CRC routine must be replaced wholesale. **Owner decision, 2026-09-11: Python leads.** The promoted `crc_checks.py` algorithm stands and the C routine is replaced at reconciliation. Interim for a deployed peer: run the link with `CRC_Pass` (requirement "CRC optional" makes this a supported configuration, not a workaround) until both ends are reflashed together | proposed, owner-decided |
| A9 | Add a `NAK` command value, sent on a frame the receiver rejects | Today a rejected frame produces silence, so the fault costs both sides a full quiesce-and-resync (`3 × timeout`, ~3 s at the defaults) before anything can proceed. A NAK collapses that to one frame time | **Degrades safely in the one direction that matters**: a peer that does not know `NAK` fails its `CMD` validation on the frame, rejects it, and resyncs — exactly what it would have done on timeout, just sooner. Verify the C receiver's unknown-`CMD` path really does reject-and-resync rather than mishandle (this is A1's fall-through bug on the C side, if it has it) | proposed |
| A10 | Shorten the `ACK` frame to a bare 5-byte header, dropping its `payload_size` bytes of padding | An ACK carries nothing but padding today, and that padding is half of all airtime (J.6: 43.6 % → 77.4 % asymptotic efficiency, a 1.77× airtime reduction). **Frame length stays unambiguous with no framing machinery**: every read site already knows which kind it expects — the write path always awaits an ACK, the read path always awaits a data frame | That the C side's ACK read/write sites are likewise context-determined and not a single shared fixed-length frame routine. Alters emitted bytes: flag day | proposed |
| A11 | Replace fixed-length framing with COBS-delimited variable-length frames | Turns resync from *temporal* into *structural*: scan to the next `0x00` and the receiver is aligned on the next frame, so worst-case recovery drops from `3 × timeout` to roughly one frame time. That removes the cooldown, which removes the write-gate timer, which removes B2's wedge mode at the source. It also makes a `payload_size` mismatch — today the one configuration error the self-healing design cannot heal, see A6 — detectable *and* recoverable. Throughput lands near A10's, so the case for it is resilience, not speed | Largest change of any entry; the whole C framing layer is replaced. Alters emitted bytes: flag day. **Design question resolved (owner decision, 2026-09-11): the bus driver gains a framing-codec concept.** `asy_uart_driver.py` learns "frame in, frame out" with a pluggable codec (pass-through by default, COBS optional), CRC keeping its current position underneath it — write order build → CRC → encode → delimiter, read order the reverse — so `UART_Comm` stays CRC-agnostic as J.3 requires, and any future framed protocol can reuse it. The codec mechanism is Class B; **selecting COBS is this Class A entry and remains a flag day** | proposed, design resolved |
| A12 | Validate the full `SIZE` invariant per chunk position, not just `0 ≤ SIZE ≤ payload_size` | The sender's `SIZE` pattern is fully determined by construction and almost none of it is checked today: chunk 1 must be exactly 1 (the command ID) — currently unchecked, so a `SIZE=0` first chunk silently yields command ID 0 from a padding byte; chunks 2…N−1 must be exactly `payload_size` — currently unchecked, so a short middle chunk silently corrupts the payload; `SIZE == 0` is legal only on the final chunk of a two-chunk train. Each closes a *silent corruption* path, not a crash path | That the C sender emits the same pattern — in particular that its first chunk always declares `SIZE = 1`, and that it never short-fills a non-final chunk | proposed |
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
| B8 | Structural role enforcement — `role` is a constructor parameter and the initiation entry points refuse on a responder (J.2) | Removes a way for *this* implementation's caller to violate the role model; a conforming peer's traffic is unchanged. The C side is free to enforce it however it likes, or not at all |
| B9 | Buffer ownership per Part G.2: one `LockableBuffer` per frame, paired `write`/`write_into` and `read`/`read_into` APIs, plus chunk-at-a-time callback forms so a large transfer never exists whole in RAM (J.8) | Python API and allocation strategy only. The wire sequence is byte-for-byte identical whether the payload came from a caller's buffer, a pull callback, or a copy — the peer cannot observe which |
| B10 | Logger injection (`fram=`/`history_length=`/`debug=`/`name=`/`logger=`, `make_logger()`), replacing every `debug`-gated `print()`; failure paths use `err_s(..., errno=N)` | Observability only (supersedes B5's narrower framing). Worth its own entry because it is also where the protocol's diagnostic counters come from: the existing `PrintLogHistory` error history *is* the counter, surfaced through `/status`'s `errcount` with optional FRAM backing, so no bespoke counter mechanism is added. The module numbers `errno` from 10 and `wrnno` from 10, aligned to `base_classes.py`'s reserved range even though it is not a `SensorReader` subclass (owner direction); where the logger is reached through from an owner, that catalog must also stay disjoint from the owner's own, the way `AsyFramManager`/`FRAM_SPI` partition one shared stream |
| B11 | Per-instance `name` (with `_NAME` only as its default) and support for more than one instance per device | The dev bench runs two instances across its permanent UART0↔UART1 crossover jumper, one initiator and one responder, so a single hardcoded logger identity would merge two error histories. Identity is a Python-side observability concern only - the peer never sees a name, and the wire sequence is unchanged |
| B12 | `asy_uart_driver.py` may gain optional-buffer parameters (`buf=None`: use the caller's, else allocate) where maximum buffer reuse needs it | A Python-side allocation strategy one layer below the protocol. The bytes emitted and the accept/reject rules are untouched; the C side has no counterpart to this layer at all. Becomes Class A only if such a change ever alters emitted bytes, which none proposed so far does |
| B13 | `uart_listen()` returns a namedtuple (`cmd_id`, `cmd`, `payload`) on every path, including today's undefined fall-through | Caller-facing return shape only, supersedes B1's narrower framing. One allocation per logical message, never per frame. `uart_get()`'s empty-payload contract is settled in the same round (`None` = failure, zero length = genuinely empty) and a lost final ACK stays folded into failure — both are how the Python side already behaves, now stated as contract and tested |
| B14 | `asy_uart_driver.py` gains a pluggable framing codec (see A11) | The mechanism itself emits identical bytes while the pass-through codec is selected, which is the default. Only *selecting* COBS changes the wire, and that is A11's own Class A flag day |
| B15 | `asy_uart_driver.cancel_read_timeout()` reworked: the request is latched rather than cleared by an unrelated `ready()` entry, acknowledged on every exit from the locked region as well as from inside `ready()`'s loop, published through monotonic request/ack counters instead of an `asyncio.Event` (so concurrent cancellers cannot strand each other), and bounded so the call is provably terminating. A holder that never acknowledges within the bound is counted in `cancel_unacknowledged` instead of blocking the caller | Bus-driver mechanism one layer below the protocol, fixing two real hang/lost-request defects in already-promoted code (requirements B1.1-B1.5). No byte reaches the wire differently and no accept/reject rule moves. It is worth recording because J.5 designates this mechanism as the recovery route for a blocked listener, so a C-side equivalent — if the C implementation has one at all — must be equally terminating |

## Settled questions

**Can COBS's `0x00` delimiter be confused with a natural `UID` rollover to `0x00`? No — not by
convention, but by construction.** COBS's defining guarantee is that its *encoded output contains no
`0x00` byte at all, for any input whatsoever*: the encoder replaces every zero byte in the frame with
an offset-to-the-next-zero, and emits only length prefixes (always ≥ 1) and non-zero data bytes. A
`UID` of `0x00`, a CRC of `0x0000`, an all-zero payload — none of them can produce a delimiter byte,
because none of them survive encoding as a literal zero.

This matters beyond the `UID`: a reserved-value convention could never have worked here anyway, since
the frame carries arbitrary caller payload and a CRC, neither of which we can keep clear of any
chosen delimiter value. Only an encoding that provably eliminates the delimiter value can frame this
protocol, which is precisely why COBS (or an equivalent) is the candidate rather than "pick a byte
nobody sends".

Verified directly rather than taken on trust (2026-09-11): a reference encoder/decoder over 20 010
cases — including all-zero frames, 254-byte zero runs, `UID` ∈ {`0x00`, `0xFE`, `0xFF`} protocol
frames with zero CRC and zero payload, and 20 000 random buffers up to 600 bytes — produced **zero
encoded outputs containing `0x00`** and **zero round-trip mismatches**. Overhead measured as
`1 + ceil(n/254)` bytes including the delimiter, i.e. exactly 2 bytes for a 55-byte frame.

**The `0xFF` `UID` barrier (A8) is unaffected either way.** It exists to stop a `+1` on a received
UID from rolling over uncontrolled, which is a counter property, not a framing one — it neither
conflicts with nor substitutes for delimiter framing, and stays in force under every option above.
