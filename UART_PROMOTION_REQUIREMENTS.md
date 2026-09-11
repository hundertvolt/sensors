# UART module promotion — ordered work list and conformance spec

**Temporary file. Delete it once `asy_uart_comm.py` is in `src/` and the promotion branch is
merged** — it is the refined scope of that one unit of work (CLAUDE.md's step-session workflow,
step 1), not a permanent specification. Anything in it that outlives the promotion belongs in
`SPECIFICATION.md`; anything protocol-facing belongs in `UART_C_PORT_CHANGELOG.md`.

## 0. What "promotion" means

Promotion is not "move the file and fix the bugs". The promoted module must be indistinguishable in
shape from one written natively for `src/`: same layering, same constructor conventions, same
injected logger, same buffer ownership, same never-raise/never-wedge contracts, same test tiers.
**The coherence test**: read `asy_fram_manager.py`, `captive_dns.py` and the promoted
`asy_uart_comm.py` back to back — nothing about the third should read as an import from elsewhere.

Sources, in precedence order: `SPECIFICATION.md` Part D (the "good enough for `src/`" checklist),
Part C (driver architecture — applies by analogy; this is not a sensor), Part G (shared-primitive
reuse), Part I (memory-safety ladder), Part F (platform facts), Part J (this protocol's own
specification), CLAUDE.md's hard rules. This file does not restate them; it derives what each
demands of *this* module, in the order the work has to happen.

## 1. How to read an item

Every work item carries the same five fields, and they are not decoration — the failure table is
the design:

- **Spec** — what must be true when the item is done.
- **Purpose** — what it is good for. An item whose purpose is only "the checklist says so" is a bad
  item and should be merged into a real one.
- **Failure modes and handling** — every way it can fail, what happens if that is left unhandled,
  and the required response. **Handling is in the same row as the mode**, so an unhandled mode is
  structurally visible rather than something to notice later.
- **Function tests** — proves it does what it should, tier-tagged `[mock]`/`[twin]`/`[flash]`/
  `[bench]`.
- **Failure tests** — proves each failure mode is actually handled as the table says. A mode with no
  failure test is not handled, it is hoped about.

`Fx.y` identifiers are stable — the changelog, the tests and any later discussion refer to them.

## 2. Build order

Dependency-ordered. A phase may not start before every item in the phase above it is done and
tested, because each phase's tests are written against the previous phase's guarantees.

| Phase | Items | Why here |
|---|---|---|
| **A — Test foundation** | A1-A4 | TDD needs a link to test against, and the link model is the one thing nothing else can substitute for |
| **B — Bus driver** | B1-B4 | The module is written once, against the driver's final API — including the framing codec and the cancel fix, both of which change that API's behaviour |
| **C — Module foundation** | C1-C5 | Construction, readiness, logging and buffers must exist before any byte moves |
| **D — Frame layer** | D1-D5 | One frame in, one frame out, fully validated |
| **E — Exchange layer** | E1-E5 | One acknowledged frame exchange, plus the recovery every failure path calls into |
| **F — Transaction layer** | F1-F7 | Trains, the public API, the role gate, the zero-copy forms |
| **G — Integration** | G1-G3 | Wiring into `dev`, the observability means, the twin |
| **H — Hazard and hardware tiers** | H1-H5 | Everything above, under concurrency and real faults |
| **I — Close-out** | I1-I3 | Docs, classification, pipeline, bird's-eye scan |

---

# Phase A — Test foundation

### A1 — Byte-stream loopback link model (`tests/machine.py`)

**Spec.** Two `machine.UART` fakes cross-connected, one independent byte FIFO per direction, each
with a fixed capacity. `POLLIN` readiness derives from that direction's real FIFO content and
`POLLOUT` from a writable gate. The fakes keep rp2's real semantics: `read`/`readinto`/`readline`
return `None` when no data is available rather than raising, and `write()` may short-write or
return `None`. The fake has **no concept of a frame** — it moves bytes.

**Purpose.** J.7 makes self-compatibility a required, tested property: one Python instance as
initiator and one as responder must interoperate perfectly. Without a link model that exists only
in-process, that property is testable solely on the dev bench, which means it would be tested
rarely and late.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| A1.1 | Harness models a perfect link | Tests pass that real hardware fails; the whole suite proves only the happy path | Every A3 fault knob is exercised by at least one test; every transaction gets both a clean-link and a faulted-link case |
| A1.2 | Fake registered with a real `select.poll()` | CI-only infinite hang — the Unix port never re-evaluates a Python object's `ioctl()` after registration; this has already happened once | Bounded poller stand-in only (A2), plus a test asserting the poller in use is not a real `select.poll` |
| A1.3 | FIFO grows without bound | A flood test exhausts the heap instead of modelling a receive overrun | Fixed capacity per direction; the overflow policy (drop newest) is explicit and asserted |
| A1.4 | Both directions share one FIFO | A sender reads back its own bytes — a self-echo real crossed wiring does not have | Per-direction FIFOs; a test asserts an instance never reads what it just wrote |
| A1.5 | Harness preserves write boundaries | Frame boundaries appear where the wire has none, hiding every desync bug | Bytes only: a write is appended to the FIFO, reads split wherever the reader asks |
| A1.6 | Fake's parameter validation drifts from real `machine_uart.c` | A construction that raises on hardware passes in tests | Validation mirrors the pinned source in the same order, as the existing fake already does; re-checked on every MicroPython pin bump |

**Function tests.** `[mock]` a byte written on A is readable on B and not on A; partial reads split
at arbitrary offsets; `POLLIN` is false on an empty FIFO and true after one byte; `POLLOUT` follows
the writable gate; a short write returns the real count.
**Failure tests.** `[mock]` writing past capacity drops per the stated policy and sets the overrun
flag; a `None` return on an empty read; the poller-identity assertion of A1.2.

**Sources.** J.7, E.4, CLAUDE.md's known-hang rule.

### A2 — Bounded poller stand-in

**Spec.** A paired poller double re-querying each fake's `ioctl()` per call, installed by
reassigning `uart.poller` after construction — the project's established mocking mechanism, keeping
`src/` free of a testability seam. Bounded by construction: it can never block indefinitely.

**Purpose.** The only mechanism that lets the real `ready()` loop run against a fake without the
Unix port's non-fd `poll()` defect. `tests/test_asy_uart_driver.py`'s `_StepPoller` already exists;
this generalizes it to a two-instance link.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| A2.1 | A real `select.poll()` is used anywhere | Infinite hang on CI only, not reproducible locally | Standing rule; asserted per test file, not left to review |
| A2.2 | Stand-in caches readiness instead of re-querying | A test passes because readiness was true once, never because the link delivered | Re-query `ioctl()` on every `ipoll()` call, asserted by a test that flips readiness between calls |
| A2.3 | Stand-in never reports not-ready | Timeout paths become unreachable, so every timeout test silently passes | A knob to force not-ready for N calls, used by the timeout tests |

**Function tests.** `[mock]` readiness tracks a FIFO going empty→non-empty→empty within one poll
loop.
**Failure tests.** `[mock]` a forced not-ready run drives `ready()` to its timeout return; the
identity assertion of A2.1.

**Sources.** CLAUDE.md's known-hang rule, J.7, E.4.

### A3 — Byte-stream fault injection surface

**Spec.** Per-direction, independently switchable: dropped bytes, corrupted bytes, mid-frame
truncation, injected noise, delayed delivery, stalled TX readiness, short writes, duplicated
frames, receive-buffer overrun, and one-sided silence. Each knob is deterministic — a seed or an
explicit schedule, never unseeded randomness.

**Purpose.** The protocol's entire resilience design (quiesce-and-resync, two-level timeouts,
deferred final ACK) exists for these cases and is otherwise untestable. J.7 names this exact list.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| A3.1 | Unseeded randomness | A flaky test nobody can reproduce, and a real bug dismissed as flake | Deterministic schedule or explicit seed, recorded in the failure message |
| A3.2 | Injection applied symmetrically only | A one-sided fault — the realistic case — is never exercised | Every knob is per-direction and independently settable |
| A3.3 | Injection knob left on by a previous test | Cross-test contamination; a later test fails for an unrelated reason | Each test constructs its own link; no module-level shared link object |
| A3.4 | "Corruption" that also changes length | Two faults at once, so a failure cannot be attributed | Corruption and truncation are separate knobs, composable but distinct |

**Function tests.** `[mock]` each knob individually changes the byte stream exactly as specified,
verified against a recorded wire log.
**Failure tests.** Each knob's own protocol-level consequence is covered by the phase that owns it
(D4, E4, F1, F2) rather than here — this item only proves the knobs work.

**Sources.** J.7.

### A4 — Digital-twin UART fake (`digital_twin/machine.py`)

**Spec.** The same link model at twin fidelity — the twin has no `UART` at all today. Wired into
the twin's bus maps, driven by the real object graph under genuine concurrent task load.

**Purpose.** C.11 item 9 makes a twin counterpart required, same session, not deferred: a module
with no twin counterpart silently regresses the Unix-port integration run's coverage.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| A4.1 | Twin fake diverges from the mock fake | Two link models disagreeing; a bug reproduces in one tier only | Shared behaviour pulled into a capability-adapter shape per E.6.2; divergence limited to fidelity, never semantics |
| A4.2 | Twin's UART shares a bus id with an existing device | The twin's single-device-per-bus-id wiring silently mis-routes | Explicit bus-id allocation, asserted at construction |
| A4.3 | Twin link runs faster than real time | Timing-dependent recovery (drain, cooldown) passes for the wrong reason | Twin timings derive from the same `timeout` the module is constructed with, never a constant |

**Function tests.** `[twin]` a full GET and a full SET between two instances inside the real task
graph; both instances' error counters stay at zero.
**Failure tests.** `[twin]` one-sided silence forces a resync and both sides recover within the
specified window.

**Sources.** C.11 item 9, A.10, E.6.1, J.7.

---

# Phase B — Bus driver (`asy_uart_driver.py`)

The driver is already promoted, reviewed and tested. Every change here keeps every existing
`tests/test_asy_uart_driver.py` test passing, extends that file's coverage, honours D.10 (every
member of a related set gets the same shape), and keeps the never-raise sentinel contract.

### B1 — Fix the external-cancel handshake

**Spec.** `cancel_read_timeout()` must reliably terminate, and a cancel request must not be lost.
Both properties are broken today, and J.5's "unsticking from outside" depends on them.

**Purpose.** A listening responder blocks indefinitely while holding the bus lock. The only safe
interruption is another task cancelling the in-flight read. If that mechanism can hang or drop
requests, the protocol's documented recovery route does not exist.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| B1.1 | Cancel arrives while the lock is held but no `ready()` is in flight — e.g. during `crc.check()`'s own per-byte yields — and the read then completes normally | `ready()` never observes `self.cancel`, so `self.cancelled` is never set and `cancel_read_timeout()` awaits it **forever**. A permanent wedge in the very mechanism that exists to prevent wedges | The cancel request is latched and acknowledged on every exit from the locked region, not only from inside `ready()`'s loop; alternatively `cancel_read_timeout()` waits with its own bound and reports the un-acknowledged case. Whichever is chosen, `cancel_read_timeout()` must be provably terminating |
| B1.2 | `ready()` begins with `self.cancel = False`, erasing a request that arrived between two reads | The cancel is silently dropped and the canceller blocks on an already-cleared `cancelled` event | A cancel is not cleared by an unrelated `ready()` entry; clearing happens only when the request is genuinely consumed and acknowledged |
| B1.3 | Two tasks cancel concurrently | One is acknowledged, the other waits for an event that is already consumed | The acknowledgement is broadcast (an `Event` stays set until the next request) or per-request |
| B1.4 | Cancel arrives when the lock is not held | Returns `False` today — correct, but indistinguishable from "tried and failed" | Keep the `False`, and document it as "nothing was in flight"; `clear()` already branches on exactly this |
| B1.5 | A fix makes cancel racy in the other direction — acknowledged before the read actually stops | The caller drains while the reader is still consuming, and they fight over the same bytes | Acknowledgement means "the read path has left the loop", tested by asserting no read occurs after the acknowledgement |

**Function tests.** `[mock]` cancel during a `ready()` wait terminates it and is acknowledged;
cancel with no read in flight returns `False`.
**Failure tests.** `[mock]` B1.1's exact sequence (cancel during the post-read CRC yield, read then
completes) terminates within a bound; B1.2's sequence (cancel between two reads) is not lost; two
concurrent cancellers both return.

**Sources.** J.5, C.3.2, D.3, D.5. **Flag, don't silently change** — this is a defect in
already-promoted code; it is reported with the fix, not folded in quietly.

### B2 — Framing-codec concept

**Spec.** The driver learns "frame in, frame out" with a constructor-injected, pluggable codec —
pass-through by default, COBS optional — with CRC keeping its current position underneath it. Write
order build → CRC → encode → delimiter; read order the exact reverse. The codec's contract has the
same family resemblance as `CRC_Base`, so a dispatch table treats every codec identically and a
pass-through codec makes every framing calculation degrade to today's fixed-size case.

**Purpose.** Resolves the changelog's open CRC-vs-COBS ownership question in the layer that already
owns the wire, keeps `UART_Comm` CRC-agnostic as J.3 requires, and makes the mechanism reusable by
any future framed protocol instead of specific to this one.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| B2.1 | A delimiter-framed read is length-unknown until the delimiter arrives | The read loop has no `nbytes` to bound it; a peer that never sends a delimiter blocks it forever | A maximum frame length bounds every codec read; exceeding it is a decode failure, not a longer wait. the never-wedge rule (D.3/D.5), applied one layer down |
| B2.2 | Resync lands mid-frame | The bytes up to the first delimiter are a fragment; decoded, they are garbage that may still pass structural checks | The first fragment after a resync is **discarded, never decoded** — a delimiter means "end of something", and only the *next* one bounds a whole frame |
| B2.3 | Two consecutive delimiters (an empty frame) | A zero-length frame reaches the protocol layer and indexes an empty buffer | Empty frames are skipped at the codec layer, never surfaced |
| B2.4 | Corrupt code byte inside a COBS frame (offset points past the frame end) | Decoder walks off the buffer | Decode validates every offset against the remaining length before following it; a violation is a decode failure returning the driver's normal sentinel |
| B2.5 | Encoded output is longer than its input and does not fit the buffer | Silent truncation, or an allocation on the hot path | Buffers sized for the worst case (`n + ceil(n/254) + 1`) once from `payload_size`, long-lived, never per frame |
| B2.6 | Codec applied to some methods only | A half-codec'd API where `write()` frames and `writefrom()` does not | D.10: every read/write method gets the same treatment, or none does |
| B2.7 | Codec selected on one end only | The link does not work at all — not degraded, dead | Codec selection is a deployment parameter like `payload_size`, agreed out of band; changing it is a flag day (changelog A11) |
| B2.8 | Codec allocation fails at construction | A driver that looks constructed but cannot frame | Degrades to the `None`-buffer/sentinel path; construction records the failure and every framed call returns its sentinel |

**Function tests.** `[mock]` round-trip through the pass-through codec is byte-identical to today's
output (the regression that proves nothing changed by default); COBS round-trips every frame the
protocol can emit; encoded output contains no `0x00`.
**Failure tests.** `[mock]` each of B2.1-B2.5 individually, plus a fuzz round-trip over random
buffers asserting decode never reads out of bounds.

**Sources.** Changelog A11 (design resolved), J.3, D.10, C.3.2.

### B3 — Optional-buffer gaps

**Spec.** Where maximum buffer reuse needs it, the driver gains optional buffer parameters under
the established scheme: *an optional buffer argument; allocate internally only when the caller
passes none*, per `voc_algorithm.py`'s `vocalgorithm_proc_ser_des(sraw, buf=None, ...)` and
`asy_fram_manager.py`'s `write()`/`write_into()` pair. **Most of it already exists** —
`readinto_until_complete()`, `writefrom()` and `readinto()` are the zero-allocation counterparts,
and using them is Phase C/D's job, not a driver change.

**Purpose.** C4's zero-allocation steady state is only reachable if the layer below also offers a
zero-allocation path for every call the protocol makes.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| B3.1 | `_write_all()` re-slices `memoryview(buf)[sent:]` per retry round | One memoryview allocation per short-write retry, on exactly the degraded link where allocation is least welcome | Carry an offset into the inner write instead of re-slicing; only matters on a short-writing link, so it is a fix-if-measured, not a speculative rewrite |
| B3.2 | A caller-supplied buffer is shorter than the requested transfer | Silent truncation or an out-of-range write | Length is validated first; a short buffer returns the method's sentinel, never a partial transfer reported as success |
| B3.3 | A `buf=` parameter is added to one method and not its siblings | An API where the zero-allocation path exists for reads but not writes, which is worse than neither | D.10 applies hardest here: the whole related set moves together |
| B3.4 | Caller reuses a buffer still referenced by an in-flight call | Data race on a shared buffer | Ownership is documented per method: the buffer belongs to the callee for the call's duration; the session lock already serializes this module's own use |

**Function tests.** `[mock]` every `_into`/`from` method moves the same bytes as its allocating
sibling; a full frame exchange under a byte-level allocation counter shows zero allocations.
**Failure tests.** `[mock]` a short caller buffer is rejected; a `None` buffer degrades to the
sentinel.

**Sources.** Owner direction, G.2, D.10, D.4.

### B4 — Driver test extension

**Spec.** `tests/test_asy_uart_driver.py` gains coverage for B1, B2 and B3, and every existing test
in it still passes unchanged.

**Purpose.** D.14: verify, don't assume. The driver is a dependency of everything above it, so a
regression here is a regression everywhere.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| B4.1 | New behaviour tested only through `UART_Comm` | A driver bug is diagnosed as a protocol bug, one layer too high | Each driver change is covered at the driver's own level first |
| B4.2 | Existing tests adjusted to fit new behaviour | The regression net is quietly loosened | Existing assertions change only where a documented, classified behaviour change requires it — and that change gets a changelog entry |

**Function tests.** The additions above.
**Failure tests.** A deliberate revert of each fix fails at least one named test — the same
"prove the test can fail" discipline Part I.3 already applies to the streaming primitive.

**Sources.** D.12, D.14, I.3.

---

# Phase C — Module foundation

### C1 — Module and class shape

**Spec.** One file, `asy_uart_comm.py`, sitting above `asy_uart_driver.py` exactly as
`asy_fram_manager.py` sits above `asy_fram_driver.py`. Module docstring ≤3 lines; no per-function
docstrings; `#` comments ≤3 lines each. `_NAME = const("UART")` as the logger-name default. Every
wire constant `const()`-folded. CapWords class (`UART_Comm`, the `FRAM_SPI`/`SCD30_I2C` compound
convention), `lower_snake_case` methods, `_`-prefixed privates, snake_case locals. Method ordering:
privates first, then publics; within each, starters → getters → setters → others; `__init__` first.
Full `--strict` typing, PEP 604 unions only, `TYPE_CHECKING` behind `try/except ImportError`, a
`Protocol` for any structurally-used caller object. No `math` import — the one `ceil()` becomes
integer arithmetic.

**Purpose.** §0's coherence test is the whole point of promotion; this item is what makes it pass on
a first read rather than after an audit.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| C1.1 | A `const()` reference inside another `const()`-wrapped tuple that is not itself `const()` | The fold silently does not happen; a RAM constant where a compile-time one was intended | Every schema/constant referenced inside another `const()` is itself `const()`-wrapped |
| C1.2 | `typing` imported unguarded | `ImportError` on the Unix-port test interpreter, which has no `typing` at all | `try/except ImportError: TYPE_CHECKING = False`, never unconditional |
| C1.3 | A `# type: ignore[method-assign]` reaches `src/` | `scripts/lint.sh`'s grep guard fails the lint gate — correctly: shipped firmware has no business reassigning a method | Never suppress it in `src/`; the suppression is the defect, not the error |
| C1.4 | Legacy one-line `if x: print(...)` bodies survive | ruff `E701` fails the gate | Removed by C3 anyway; verified by running lint, not by reading |
| C1.5 | Integer ceiling written as `math.ceil(a / b)` | A float division on a fixed-point-free target, plus an import for one call | `-(-a // b)`, commented once |

**Function tests.** Covered indirectly by every later item; the direct gate is `scripts/lint.sh` and
`scripts/typecheck.sh` reporting zero findings.
**Failure tests.** n/a — a style item's failure mode is a failing gate, not a runtime behaviour.

**Sources.** C.2, C.10, D.6, D.11, D.15, CLAUDE.md.

### C2 — Constructor, parameter validation, readiness gate

**Spec.** Sync `__init__` that only stashes and allocates — no `await`, no I/O, no bus touch.
Parameter order: bus handle, `role`, protocol parameters (`payload_size`, `timeout`),
`max_module_error` if used, then `fram`, `history_length`, `debug`, `name`, `logger`. `payload_size`
constrained to `1 … 255` and **never silently clamped**; `timeout` positive; `role` one of the two
legal values. An invalid parameter sets the standard readiness gate `self.initialized = False`, and
every entry point then returns its sentinel with a logged error. `async def setup()` does the
deferred work and flips the gate.

**Purpose.** `payload_size` and `timeout` are agreed out of band and must match on both ends;
nothing is negotiated. A clamp would convert a loud, findable configuration error into a link that
desyncs intermittently in the field — the one configuration error J.6 says the self-healing design
cannot heal.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| C2.1 | `payload_size` outside `1 … 255` | `SIZE`/`CHUNKS` are single bytes; a zero-width payload cannot carry the command ID | Readiness gate refuses; logged `err_s`; never clamped |
| C2.2 | `payload_size` valid but different from the peer's | Every frame is the wrong length; the link desyncs outright and cannot self-heal | Not detectable from one side under fixed framing — it is the reason B2's codec matters, since COBS makes it recoverable. Until then: documented as a deployment contract and asserted by the dev wiring constructing both instances from one shared constant |
| C2.3 | `timeout` zero or negative | Every wait returns immediately; the link never completes a frame, and the drain bound collapses to zero | Readiness gate refuses |
| C2.4 | `timeout` shorter than the worst-case GC pause plus a poll interval | Spurious timeouts under memory pressure, looking like link faults | Documented lower bound derived from `poll_wait_ms` and the measured ~15-21 ms worst-case GC pause; refused below it |
| C2.5 | Invalid `role` | Neither gate fires; the instance both listens and initiates | Readiness gate refuses; `role` has no default |
| C2.6 | Any public method called before `setup()` | Operating on unallocated state | Gate returns the method's normal sentinel and logs — never raises, matching this class's declared contract |
| C2.7 | `__init__` given a bus handle that is `None` or already deinit'd | Every call returns a sentinel with no explanation | Checked at construction; recorded distinctly from a parameter error so the log says which |
| C2.8 | Constructor does real work (allocates and *also* touches the bus) | An import-time or construction-time hang, outside any supervisor | Sync/allocate-only, enforced by a test asserting construction performs no bus call |
| C2.9 | The injected `UART`'s `rxbuf` is smaller than one whole framed frame | Stop-and-wait means a **complete** frame can land before the reader is next scheduled, so the driver's own buffer silently drops the tail — a frame that never completes, indistinguishable from a link fault. At `payload_size = 255` the frame is `5 + 255 + 2 = 262` bytes against the driver's **default `rxbuf = 256`**, so the maximum legal `payload_size` overruns the default outright | Checked at construction against the real frame size (header + payload + CRC + codec overhead); too small is a readiness-gate refusal with its own errno, not a silent degradation |
| C2.10 | `rxbuf` smaller than the bytes arriving between two poll rounds | Same silent tail-drop under sustained traffic. At 115200 baud a 20 ms poll interval admits ~230 bytes against a 256-byte default — ~26 bytes of margin for scheduling jitter | Second half of C2.9's check: `rxbuf` ≥ `baud/10 × (poll_wait_ms + jitter)`. G1.1's single-digit `poll_wait_ms` gives ~58 bytes at the same baud, which is where the real margin comes from |

**Function tests.** `[mock]` valid construction sets the gate after `setup()`; every boundary value
of `payload_size` (`1`, `255`) is accepted and (`0`, `256`) refused.
**Failure tests.** `[mock]` each of C2.1-C2.7 returns the sentinel and logs a distinct errno; a
pre-`setup()` call on every public method returns its sentinel; construction with a `None` bus
never raises; `[mock]` C2.9's `payload_size = 255` against the default `rxbuf` is refused at
construction rather than failing later as a link fault.

**Sources.** J.6, C.13, D.2, changelog A6.

### C3 — Logger injection, name, errno catalog

**Spec.** Both construction routes, exactly as `SensorReader.__init__` shapes them:
`fram=`/`history_length=`/`debug=`/`name=` through `make_logger()`, or a caller-supplied `logger=`
reaching through to an upstream instance's own — the live precedent being `AsyFramManager` handing
`self.pr` down to `FRAM_SPI` and every chunk. `fram=` optional but always possible, project-wide
default. `self.name` set and equal to `self.pr.name`. Every legacy `if self.debug: print(...)`
replaced: trace via `pr.all()`/`pr.evt()`/`pr.one()`, anything that should count via
`pr.err_s(..., errno=N)`/`pr.wrn_s(..., wrnno=N)`. `errno` numbering from 10 and `wrnno` from 10,
aligned to the `SensorReader` reservation even though this is not a subclass. `get_error_counter()`
returning `await self.pr.get_log()` typed as `ErrorLog`, and `reset_error_counter()`.

**Purpose.** This is where the diagnostic counters come from — the `PrintLogHistory` error history
*is* the counter, surfaced through `/status`'s `errcount` with optional FRAM backing. No bespoke
counter mechanism is added anywhere.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| C3.1 | A shared logger receives codes that collide with its owner's | Two modules' errors indistinguishable in one history stream; a diagnosis points at the wrong module | The catalog is **disjoint from the owner's own**, not merely ≥10 — the `AsyFramManager` (10-88) / `FRAM_SPI` (89-98) partitioning is the reference |
| C3.2 | Two instances on one device share one logger | Both instances' histories merge; `/status` shows one entry for two links | Distinct `name` per instance (`_NAME` is only the default); asserted by the dev wiring test |
| C3.3 | `err_s`/`wrn_s` called from a sync context | They are `async`; a sync call site cannot await them | Sync sites use the non-persisting `pr.err()`/`pr.wrn()` — and a failure worth counting is never demoted to `pr.all()` just to avoid the await |
| C3.4 | `await self.pr.setup()` never called | FRAM persistence stays inert; the history silently does not survive a reboot | Called once at the start of the owned task, or in `setup()` if no task is owned; asserted by a test reading the FRAM-backed history after a simulated restart |
| C3.5 | A failure path returns a sentinel without logging | A transient link fault leaves no trace; the field diagnosis has nothing to read | Every failure path logs; enforced by reviewing each `return <sentinel>` against a logged call, and by a test asserting the error count moves on each injected fault |
| C3.6 | FRAM-backed logger's chunk allocation fails | `PrintLogHistoryStore.fram` is `None`; writes silently no-op | Already handled by `print_log.py` (`_diag` reports it); this module must not assume persistence succeeded |
| C3.7 | An errno is emitted that is not in the published catalog | `/status` shows a number the table cannot explain | Catalog lives in C.7.1's table and is updated in the same change; a test enumerates every `errno=`/`wrnno=` literal in the module and asserts it is within the declared range |
| C3.8 | A permanently faulty link logs a persisted error per fault | `_store_err()` writes FRAM on **every** `err_s()` call, so a link failing once per second is a FRAM write per second — the bounded history fills with one repeated code, burying every other module's entries, and the bus time is spent on it. FRAM endurance is not the issue; losing the diagnostic value of the history is | A repeated identical fault escalates once and then degrades to the non-persisting `pr.err()`/`pr.all()` until the state changes, the same intent as C.9's backoff applied to logging. The persisted entry marks the *transition* into and out of the fault, not each occurrence |

**Function tests.** `[mock]` construction with `fram=` selects the store and without it the RAM
logger; `logger=` reach-through uses the caller's instance; `get_error_counter()` returns the
`ErrorLog` shape.
**Failure tests.** `[mock]` C3.4's uninitialized-history path; C3.7's range sweep; an injected link
fault increments the count and appears in the history with the expected errno.

**Sources.** C.7, C.7.1, G.2, owner direction 2026-09-11.

### C4 — Frame buffers and scratch allocation

**Spec.** Two long-lived `LockableBuffer(5 + payload_size, data_start=5, data_length=payload_size)`
per instance — one TX, one RX — allocated once in `__init__` from configuration; `get_buf()` is what
the driver's `writefrom()`/`readinto_until_complete()` operate on, `get_data_buf()` is the payload
region. Header fields written in place by index. Plus long-lived fixed scratch: the one-byte command
ID, the ACK frame, and a preallocated zero buffer for padding. Steady-state frame traffic allocates
nothing.

**Purpose.** The protocol chunks the wire; the API must chunk the memory too. Without this, framing
buys nothing for RAM — and the legacy implementation allocates three times per frame plus two slices
per chunk.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| C4.1 | Allocation fails at construction (fragmented heap, a large `payload_size`) | An instance that looks constructed but cannot send | `LockableBuffer` already returns `buf = None` rather than raising; every consumer's first act is `if buf is None: return <sentinel>`, and construction logs it |
| C4.2 | TX and RX share one buffer | A received frame overwrites the frame being acknowledged, or vice versa | Two separate buffers, asserted by a test that fills one and checks the other |
| C4.3 | Padding left unwritten | The previous frame's payload remnants are transmitted — a real data leak between unrelated messages | Zero-filled from the preallocated zero buffer on every frame whose `SIZE < payload_size` |
| C4.4 | A buffer is handed out and retained by a caller past the call | The next frame silently mutates data the caller still holds | Ownership documented per method; the `_into` forms take the *caller's* buffer precisely to avoid this, and the internal buffers are never returned |
| C4.5 | `payload_size` changed after construction | Buffers sized for the old value; every frame is wrong | `payload_size` is immutable after construction; no setter exists |
| C4.6 | A `memoryview` of a buffer outlives the buffer | Dangling view | Views are created per use inside the call, never stored |

**Function tests.** `[mock]` a maximum-length train exchange shows zero allocations under an
allocation counter; header fields land at the right offsets; padding bytes are zero.
**Failure tests.** `[mock]` a forced `buf = None` degrades every entry point to its sentinel; C4.3's
remnant test — send a long frame then a short one, assert the short frame's padding is zero rather
than the long frame's tail.

**Sources.** J.8, G.2, I.1, I.4(b).

### C5 — Lifecycle: setup, starters, counters

**Spec.** `async def setup()` flipping the readiness gate. `get_task_starters()` and
`get_timer_starters()` both present, even if one returns `[]` — `system_service.py` discovers every
module generically through these, never by name. A responder's listen loop is a supervised task;
the loop returns only on a readiness failure, never on a link fault. `get_error_counter()` /
`reset_error_counter()` per C3.

**Purpose.** Generic supervision, generic observability, generic debug-level push — the three things
a module must offer to be wired into a variant at all.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| C5.1 | Task starter raises at start | `system_service.py` logs and continues with a missing task; the link silently never runs | Starter is trivial (`create_task`) and cannot raise; the supervisor's own guard is the backstop, not the design |
| C5.2 | Listen loop returns on a link fault | The supervisor restarts a task that had nothing wrong with it, repeatedly, burning the task-error budget toward a reboot | Returns only on a readiness failure; link faults are handled by E4's resync and §3.2's backoff |
| C5.3 | Listen loop never returns and never yields | Starves the event loop, including the Neopixel animation | Every wait is an `await`; no busy spin without a yield |
| C5.4 | An initiator-role instance exposes a listen task | Both ends initiate; the protocol has no arbitration for that | `get_task_starters()` returns `[]` for an initiator — the role decides the task set |
| C5.5 | `reset_error_counter()` resets the history but not an internal streak counter | A reset the caller expects to be total is not | Resets everything this module counts, the way `SensorReader.reset_error_counter()` resets both |

**Function tests.** `[mock]` both starter lists are returned and are the right shape per role;
`setup()` flips the gate; a reset clears count and history.
**Failure tests.** `[mock]` an injected permanent link fault does not make the listen loop return;
a readiness failure does.

**Sources.** C.9, C.13, A.7.

---

# Phase D — Frame layer

### D1 — Header construction in place

**Spec.** `UID`, `CMD`, `SIZE`, `CHUNKS`, `CUR_CHUNK` written by index into the TX buffer's first
five bytes; payload copied into the data region; the remainder zero-filled from the zero buffer.
No per-frame allocation. Field values range-checked before being written.

**Purpose.** Replaces `_build_msg()`'s three allocations per frame, and is where every wire-visible
invariant is actually produced.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| D1.1 | A field value exceeds a byte | `struct.pack()` truncates silently on this platform; an out-of-range `CHUNKS` becomes a plausible wrong value | Written by index with an explicit range check, not packed; a violation is a caller/logic error returning the sentinel |
| D1.2 | Payload longer than `payload_size` for one frame | Overruns the data region | Length checked against the region, never the whole buffer |
| D1.3 | `SIZE` written inconsistently with the bytes actually copied | The peer reads padding as payload, or truncates real data | `SIZE` derives from the copy length, never passed independently |
| D1.4 | Zero-fill skipped for a full-width frame | Wasted work, or worse, a partially filled region | Fill only `payload_size - SIZE` bytes; a full frame fills none |

**Function tests.** `[mock]` every field lands at its documented offset; a byte-exact wire log for a
known payload matches a hand-computed frame.
**Failure tests.** `[mock]` each of D1.1-D1.3 rejected rather than emitted.

**Sources.** J.3, J.8, F.1's `struct.pack()` truncation fact.

### D2 — Frame reception into the RX buffer

**Spec.** A frame is read whole into the instance's RX buffer via the driver's
`readinto_until_complete()` (or the codec's framed read), then its payload region is slice-assigned
into the destination. It is deliberately **not** read header-first so the payload can land directly
at its final offset.

**Purpose.** The two-stage read would save one ≤`payload_size` memcpy but costs an extra `ready()`
round — one whole `poll_wait_ms`, which J.6 shows dominates throughput — and with CRC enabled is not
available at all, since the CRC covers the frame as a unit.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| D2.1 | Fewer bytes arrive than a whole frame and then silence | A half-received frame leaves the stream offset by that many bytes forever | The driver's inter-part timeout abandons the frame (J.5's anti-desync rule); the module then resyncs (E4) |
| D2.2 | More bytes arrive than one frame | The surplus is the next frame's head, or noise | Exactly one frame's worth is consumed per read; the surplus stays buffered and is validated as the next frame, or discarded by the resync |
| D2.3 | CRC check fails | Under fixed framing the frame simply never completes; the caller sees a timeout | Treated as any other frame fault: resync. The CRC's own failure is not separately distinguishable by design, and that is documented rather than worked around |
| D2.4 | Read returns `None` (timeout, cancel, or bus gone) | Indistinguishable causes conflated into one failure | Distinguished where the driver allows it (cancel vs. timeout), logged with distinct errnos, all converging on the same resync |
| D2.5 | The peer runs a different CRC algorithm or byte order — exactly the case changelog A7 creates against an un-reflashed Arduino | **Every** frame fails its CRC, so the link looks completely dead while bytes are visibly arriving. Without a diagnostic this is indistinguishable from a wiring fault and costs a bench session to find | A distinct warning when frames keep arriving but *none* ever validates: bytes-received-without-a-single-valid-frame over a resync cycle is a strong, cheap signal for a CRC, baud or `payload_size` mismatch. The interim remains running the link with `CRC_Pass` until both ends are reflashed |
| D2.6 | Baud rate or `payload_size` mismatched between the ends | Same symptom as D2.5 and the same cost to diagnose | Same diagnostic covers all three; the log names all three candidates rather than guessing one |

**Function tests.** `[mock]` a whole frame is read into the RX buffer with the payload at the right
offset; two back-to-back frames are read as two.
**Failure tests.** `[mock]` truncation mid-frame; silence after a partial frame; injected noise
before a real frame; `[mock]` a peer using the legacy CRC variant produces D2.5's diagnostic rather
than silent repeated resyncs.

**Sources.** J.5, J.6, J.8.

### D3 — UID counter and controlled wrap

**Spec.** Per-frame nonce, incremented per transmitted frame, wrapping `0xFE → 0`. **Never emitted
as `0xFF`.** An ACK echoes the received `UID` and does not consume one of the sender's own. Any code
predicting a *next* expected UID reuses the same controlled wrap, never a bare `+1`.

**Purpose.** Two properties depend on it: a free off-by-one barrier so that any implementation adding
1 to a received UID stays inside the byte, and a value space (`0 … 0xFE`, 255 values) exactly as
large as the longest possible train, so no UID repeats within one transfer and a stale ACK from an
earlier frame cannot be mistaken for the current one.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| D3.1 | Wrap "fixed" to `0xFF` | Removes the barrier and the no-repeat-within-a-train property together | Explicitly documented as do-not-change, with a test asserting `0xFF` is never emitted across a full wrap cycle |
| D3.2 | Next-UID predicted with a bare `+1` | Mispredicts precisely at the `0xFE → 0` boundary — a bug that appears once per 255 frames | One shared increment helper, used everywhere; the boundary is a named test case |
| D3.3 | A received `UID` of `0xFF` | Out of contract; a conforming peer never sends it | Rejected as a malformed frame, then resync |
| D3.4 | Counter shared between two concurrent transactions | Two trains interleave UIDs; ACK matching breaks | Touched only under the session lock, so it stays a plain `int`; documented, and the lock is what a test asserts |
| D3.5 | Counter reset mid-train | A UID repeats inside one train; a stale ACK matches the wrong frame | Only advanced, never reset outside construction |

**Function tests.** `[mock]` a full 255-step cycle emits every value in `0 … 0xFE` exactly once and
never `0xFF`; an ACK echoes rather than consumes.
**Failure tests.** `[mock]` a received `0xFF` is rejected; the `0xFE → 0` boundary predicts
correctly; a stale ACK from an earlier frame of the same train is not accepted.

**Sources.** J.3, changelog A8.

### D4 — Frame validation

**Spec.** The full invariant set, all of it checked on every received frame:

- `CMD` by **exact match** against `ACK`/`GET`/`SET`, never a bitmask.
- `CUR_CHUNK` exactly the expected index, and never greater than `CHUNKS`.
- `CHUNKS` **constant across every frame of a train**.
- `UID` validated on data chunks, not only on ACKs.
- `SIZE` per position: chunk 1 exactly 1 (the command ID); chunks 2…N−1 exactly `payload_size`;
  `SIZE == 0` legal only on the final chunk of a two-chunk train; always `0 ≤ SIZE ≤ payload_size`.
- An `ACK` frame carries `SIZE = 0`, `CHUNKS = 1`, `CUR_CHUNK = 1`.
- A frame whose `CMD` implies the wrong direction for this instance's role is rejected.

**Purpose.** Each rule closes a **silent corruption** path, not a crash path — which is why they are
worth the bytes. Today's bitmask check lets `0x03`/`0x06` pass validation and then match no dispatch
branch; an unchecked `CHUNKS` lets a peer truncate a transfer mid-train by re-declaring the total;
an unchecked first-chunk `SIZE` yields a command ID read from a padding byte.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| D4.1 | `CMD` with multiple bits set (`0x03`, `0x06`) | Passes the bitmask test, matches no dispatch branch, falls through to an undefined return | Exact match; anything else rejected → resync (changelog A1) |
| D4.2 | `CHUNKS` changes between frames of one train | The peer truncates the transfer by re-declaring the total; the receiver reports success on partial data | Latched from chunk 1 and compared on every subsequent frame (A2) |
| D4.3 | Stale or duplicated data frame | Invisible today — only ACKs check `UID` | `UID` validated on data chunks too (A3) |
| D4.4 | Chunk 1 with `SIZE != 1` | Command ID silently read from a padding byte — usually `0` | Rejected (A12) |
| D4.5 | A middle chunk short-filled | Payload silently corrupted, length still adds up if a later chunk compensates | Chunks 2…N−1 must be exactly `payload_size` (A12) |
| D4.6 | `SIZE == 0` on a non-final chunk | An empty middle chunk misread as a genuinely empty payload | Legal only on the final chunk of a two-chunk train (A12) |
| D4.7 | `CHUNKS == 1` on a SET | No data chunk exists to acknowledge; the sender floors at 2, so a conforming peer never does this | Rejected explicitly rather than left to time out |
| D4.8 | `CHUNKS == 0` | A train of no frames | Rejected (already implied by `CUR_CHUNK > CHUNKS`, but asserted directly) |
| D4.9 | An ACK with `SIZE`/`CHUNKS`/`CUR_CHUNK` ≠ the specified constants | A malformed ACK accepted as valid confirmation | Validated; rejected → resync |
| D4.10 | A data frame arriving where an ACK is expected, or the reverse | Cross-wired state machine; the exchange proceeds on the wrong frame | Each read site declares which kind it expects and rejects the other |
| D4.11 | A GET arriving at an initiator | A peer violating the role model | Rejected and logged distinctly — this is the peer's bug, and the log is how it gets found |
| D4.12 | Validation itself raises on a malformed buffer (short read, `None`) | An exception escapes a module contracted never to raise | `None`/length checked first, before any indexing |

**Function tests.** `[mock]` every legal frame shape accepted across the full field sweep of H1.
**Failure tests.** `[mock]` one test per row, each asserting rejection **and** the resulting resync,
not merely a `False` return.

**Sources.** J.3, J.4, changelog A1/A2/A3/A12.

### D5 — ACK emission

**Spec.** An ACK carries the acknowledged frame's `UID`, `SIZE = 0`, `CHUNKS = 1`, `CUR_CHUNK = 1`,
built into the preallocated ACK scratch buffer rather than through the frame builder.
**Acknowledgements are always sent**, including while the write hold-off is gating this side's own
initiations.

**Purpose.** The protocol's only positive signal. Withholding one is how a receiver signals
rejection — so an ACK sent by mistake is worse than a frame lost.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| D5.1 | ACK sent before validation completes | A rejected frame is confirmed; the sender proceeds on corrupt data | ACK is emitted only after every check for that frame passes, and the final chunk's ACK only after the total-size check |
| D5.2 | ACK gated by the write hold-off | Both sides back off simultaneously and the link stalls for no reason | The hold-off gates *initiating* transmissions only; ACKs are exempt, asserted by a test |
| D5.3 | ACK built through the padded frame builder | A full `payload_size` of padding allocated and transmitted per ACK | Preallocated scratch; airtime cost is a known property (J.6), not an accident |
| D5.4 | ACK write fails | The peer times out and resyncs while this side believes the exchange advanced | Treated as a local failure: log, resync this side too, so both converge |
| D5.5 | ACK echoes a wrong or stale `UID` | The sender rejects it and resyncs, losing a whole transfer to a local bug | `UID` copied from the frame being acknowledged, never from the counter |

**Function tests.** `[mock]` byte-exact ACK for a known frame; an ACK during an active hold-off is
still sent.
**Failure tests.** `[mock]` D5.1's ordering (a frame failing the size check is never acknowledged);
a failed ACK write triggers a local resync.

**Sources.** J.3, J.4, J.5.

---

# Phase E — Exchange layer

### E1 — Write a frame and await its ACK

**Spec.** Wait for the write gate (E3), write the TX buffer via `writefrom()`, read exactly one
frame, validate it is an ACK matching this frame's `UID`, return success. Two-level timeouts: the
wait for the ACK is bounded by `timeout`; once bytes begin arriving the inter-part timeout is also
`timeout`.

**Purpose.** Stop-and-wait at frame granularity — never more than one frame in flight, no windowing
— is the whole flow-control design. Every train is built out of this one operation.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| E1.1 | No ACK arrives | The sender waits forever | Bounded by `timeout`; on expiry → resync and failure sentinel |
| E1.2 | ACK arrives with a different `UID` | A stale ACK from an earlier frame confirms the wrong one | `UID` match required; mismatch → resync (the value space guarantees no repeat within a train, D3) |
| E1.3 | A non-ACK frame arrives instead | The peer is mid-initiation, or the stream is desynced | Rejected → resync; distinguishes "peer initiated simultaneously" in the log, since that is out of contract and worth seeing |
| E1.4 | Write returns `False` or short-writes | Partial frame on the wire; the peer sees a truncated frame | The driver already retries until complete; a real failure → log, resync, sentinel |
| E1.5 | Write succeeds but the peer never received it | Indistinguishable from E1.1 at this layer | Same handling; the distinction does not exist on the wire and is not invented |
| E1.6 | ACK received for the *final* chunk is lost | The sender resyncs and reports failure although the data arrived — the two-generals case | Folded into failure by decision: no retransmission exists to hang a third state on, and a caller cannot act differently. Documented in the API contract, covered by a test asserting the sender reports failure and the receiver reports success |

**Function tests.** `[mock]` a clean write/ACK round trip; the `UID` on the ACK matches.
**Failure tests.** `[mock]` each of E1.1-E1.4 and E1.6, each asserting the resulting resync.

**Sources.** J.4, J.5.

### E2 — Read a frame and acknowledge it

**Spec.** Read one frame (D2), validate it fully (D4), acknowledge it (D5). The wait for a *new*
message is unbounded for a listening responder and bounded by `timeout` for an initiator awaiting a
reply; the inter-part timeout is always `timeout`.

**Purpose.** The receive half of stop-and-wait, and the only place where an unbounded wait is
legitimate — which is exactly why it must be externally cancellable.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| E2.1 | Unbounded wait with no cancel route | A listening responder holding the bus lock is unstickable | The wait is cancellable from another task via B1's fixed handshake; this is J.5's documented recovery route |
| E2.2 | Validation fails | See D4 | Withhold the ACK, resync |
| E2.3 | A frame arrives while this side is mid-initiation | Simultaneous initiation — out of contract, no arbitration exists | Detected, logged distinctly, resync. The role gate (F5) prevents this side from causing it; the log is how the *peer's* violation becomes visible |
| E2.4 | Bus lock held across the unbounded wait | No other task can use the bus, by design — but a bug elsewhere that takes the lock deadlocks the listener | Lock ordering documented; `clear()` must not take the lock before attempting the cancel (E5) |

**Function tests.** `[mock]` a frame is received, validated and acknowledged; the unbounded wait
returns as soon as a frame arrives.
**Failure tests.** `[mock]` the unbounded wait is cancelled from another task and terminates; a
frame failing validation is not acknowledged.

**Sources.** J.4, J.5, C.3.2.

### E3 — Write hold-off as a deadline

**Spec.** After a resync, this side holds off *initiating* for `1.5 × timeout`, implemented as a
`time.ticks_ms()` deadline compared with `time.ticks_diff()` — **not** a one-shot `machine.Timer`
and not a `ThreadSafeFlag` set from a callback. ACKs are exempt (D5.2).

**Purpose.** Removes the single worst wedge in the legacy module at its source, and removes a
`machine.Timer` allocation from the alarm pool while it is at it.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| E3.1 | A soft one-shot `Timer` callback is dropped — MicroPython's fixed-depth scheduler queue can silently drop one | The flag it would have set is never set; `await enable_writing.wait()` blocks **forever**. This is the legacy module's permanent-hang mode, and it is a documented platform fact, not a theoretical risk | A deadline cannot be dropped: no callback, no alarm-pool slot, no flag |
| E3.2 | `Timer.init()` raises `OSError(ENOMEM)` on alarm-pool exhaustion | Unhandled exception out of a never-raise module | Not applicable once no `Timer` exists — which is the point. Any `Timer` that survives elsewhere catches `(OSError, MemoryError)`, never bare `OSError` |
| E3.3 | Deadline compared with a raw `now - t0` subtraction | Wrong at the `ticks_ms()` rollover (2**30 ms ≈ 12.4 days on rp2) — a fault that appears once per uptime period and is untestable by waiting | `time.ticks_diff()` only, matching every other `src/` site; `tests/test_ticks_rollover.py`'s audit extended to cover this new site |
| E3.4 | Hold-off applied to ACKs | Both sides back off together; the link stalls with neither at fault | ACKs exempt (D5.2) |
| E3.5 | Hold-off cleared by an unrelated event | The side initiates into the peer's drain window, restarting the fault | Cleared only by the deadline passing, or by `uart_listen()`'s documented reset ("if the peer requests something, it is definitely up again") |
| E3.6 | Hold-off shorter than the peer's drain window | This side transmits into the peer's drain and both resync again — a livelock | Both constants are part of the contract (`1.5 × timeout` each) and derived from `timeout`, never hardcoded (changelog A4) |

**Function tests.** `[mock]` initiation is refused before the deadline and permitted after; an ACK
is sent throughout.
**Failure tests.** `[mock]` a simulated rollover boundary (synthetic `ticks_add()` values, the
existing audit's method) keeps the deadline correct; a dropped-callback scenario is impossible by
construction, asserted by the absence of any `Timer` in the module.

**Sources.** F.1, C.9, changelog A4/B2, `tests/test_ticks_rollover.py`.

### E4 — Quiesce-and-resync

**Spec.** On any fault — CRC failure, unexpected chunk index, size mismatch, missing ACK, malformed
frame — the side that noticed drains its receive path until the line has been quiet for
`1.5 × timeout`, then holds off initiating for a further `1.5 × timeout` (E3). Nothing is ever
re-sent. **The drain is bounded**: it cannot loop forever against a peer that keeps transmitting.

**Purpose.** With no framing marker to resync against, mutual silence is what gets both sides back
onto a clean frame boundary. Under B2's codec this becomes structural rather than temporal, but the
temporal mechanism remains the fallback and the pass-through default.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| E4.1 | Peer transmits continuously (stuck sender, noise source) | The drain loop never sees quiet and runs forever — the legacy module's unbounded `while True` | A hard bound on total drain time, never shorter than the peer's own drain window; hitting it is logged and the resync completes anyway (changelog A5) |
| E4.2 | Drain reads allocate per round | A degraded link allocates hardest, exactly when the heap is most fragmented | Drain reads into the RX scratch buffer via `readinto()`, never `read()` |
| E4.3 | A fault occurs *inside* the resync | Recursive resync, or a partially completed one | Resync is not re-entrant: a fault during it is logged and the drain continues to its bound |
| E4.4 | Resync while another task holds the lock | Deadlock, or a drain that never starts | `clear()`'s existing structure — cancel first, take the lock only if nothing was cancelled — is preserved exactly (E5) |
| E4.5 | Both sides resync at slightly different times | One starts transmitting while the other is still draining, restarting the fault | The `1.5 ×` factor on both constants is what provides the margin; changing either is a Class A change |
| E4.6 | Resync path itself returns success | A caller believes a failed transfer succeeded | Every resync path converges on the caller's failure sentinel; asserted by a test per entry point |
| E4.7 | Drain bound expressed in poll intervals rather than time | A different `poll_wait_ms` silently changes the protocol's timing contract | Bound derived from `timeout`, independent of `poll_wait_ms` |

**Function tests.** `[mock]` a fault triggers a drain that ends after the line goes quiet, followed
by the hold-off.
**Failure tests.** `[mock]` E4.1's flooding peer terminates at the bound; E4.3's nested fault; E4.6
across every public entry point.

**Sources.** J.5, changelog A4/A5.

### E5 — Unsticking from outside

**Spec.** `clear()` keeps its existing two-branch structure: attempt the external cancel **first**,
and take the lock and drain directly **only if nothing was cancelled** — because a cancelled read's
own failure path performs the drain itself.

**Purpose.** A listening responder blocks indefinitely while holding the bus lock; this is the only
safe interruption. The ordering is load-bearing, not incidental.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| E5.1 | Lock taken before attempting the cancel | Deadlock against the very blocked listener the call exists to unstick | Cancel first, lock second — preserved from the legacy structure and asserted by a test |
| E5.2 | Cancel succeeds but the cancelled path does not drain | Both branches assume the other drained; neither does | The cancelled read's failure path performs the drain; asserted by checking the line is quiet afterwards in both branches |
| E5.3 | Both branches drain | Two drains, the second into the first's silence — harmless but doubles the recovery time | Exactly one drain per `clear()`, asserted by counting drain entries |
| E5.4 | `cancel_read_timeout()` hangs | `clear()` never returns; the caller is wedged | B1's fix is a prerequisite for this item — E5 cannot be correct while B1 is broken |
| E5.5 | A cancel lands while this side is writing, not reading | `ready()` serves `POLLOUT` waits too, so the cancel can abort a write mid-frame, leaving a partial frame on the wire | Accepted and handled rather than prevented: the peer's own resync absorbs a partial frame, and this side resyncs too. Tested explicitly, because "cancel" reads as read-only from its name and the write case is the one nobody expects |

**Function tests.** `[mock]` `clear()` with a read in flight cancels and drains once; with nothing in
flight, takes the lock and drains once.
**Failure tests.** `[mock]` E5.1's ordering asserted directly; E5.3's drain count.

**Sources.** J.5, C.3.2.

---

# Phase F — Transaction layer

### F1 — Send a train

**Spec.** `CHUNKS = ceil(len(payload) / payload_size) + 1`, floored at 2, computed with integer
arithmetic. Chunk 1 is the command header (`SIZE = 1`, payload = the command ID byte); chunks 2…N
carry data, each with a fresh `UID`, each individually acknowledged before the next is sent. The
payload is consumed by `memoryview` slicing, never by re-slicing a `bytes`/`bytearray`.

**Purpose.** Even a payload-less command still has one data chunk to acknowledge, so it is confirmed
end-to-end rather than merely heard. The chunking is what lets a transfer cross a peer's small UART
buffers.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| F1.1 | Payload longer than `(0xFF − 1) × payload_size` | `CHUNKS` overflows its byte; the train is silently mis-declared | Checked before the first frame; rejected with a distinct errno, never partially sent |
| F1.2 | `payload[:size]` / `payload[size:]` slicing per chunk | Two allocations per chunk and O(n²) over the train — on the exact path that exists to save memory | `memoryview` slices; asserted by an allocation counter over a maximum-length train |
| F1.3 | Any chunk's ACK missing or wrong | The train is half-delivered | Abort at that chunk: resync, failure sentinel. Nothing is re-sent — that is the design, not a gap |
| F1.4 | `payload` is `None` | Legacy substitutes an empty `bytearray`, allocating for nothing | Treated as zero-length without allocating |
| F1.5 | Caller mutates `payload` mid-train | Chunks drawn from a buffer that changed under them | The caller's buffer is borrowed for the call's duration; documented, and the session lock prevents this module from racing itself |
| F1.6 | A `MemoryError` while preparing a chunk | An exception out of a never-raise module | `(OSError, MemoryError)` caught at the allocation site, degrading to the sentinel and a resync (I.4(a)/(b)) |

**Function tests.** `[mock]` byte-exact wire log for a multi-chunk payload; a payload-less command
produces exactly two chunks; boundary payload lengths (`payload_size − 1`, exactly `payload_size`,
`payload_size + 1`) produce the right `CHUNKS`.
**Failure tests.** `[mock]` F1.1's oversize rejection; a missing ACK at chunk 1, a middle chunk, and
the final chunk, each asserting abort-and-resync; F1.2's allocation count.

**Sources.** J.4, J.8.

### F2 — Receive a train

**Spec.** Validate each frame (D4), append its `SIZE` payload bytes to a **preallocated**
destination, acknowledge, repeat. The destination is sized from `CHUNKS × payload_size` on the first
frame, or exactly from `exp_size` when the caller supplied it — never grown incrementally. An
expected total size may be supplied as *don't care*, *exactly empty*, or *exactly N*, enforced both
incrementally (reject as soon as the running total would overshoot) and finally (exact match). The
final chunk's acknowledgement is deferred until after the total-size check passes.

**Purpose.** Requirement "large payloads over little buffers" is only half-met while the receiver
grows `res` by `+=` across the train — 254 reallocations and a ~2× peak at the final copy for a
maximum 12192-byte transfer, on a 264 kB device.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| F2.1 | Incremental `+=` accumulation | O(n²) copying plus heap fragmentation, on a non-compacting collector where contiguity is what fails | Preallocated from `CHUNKS × payload_size` or `exp_size` (C4); asserted by an allocation counter |
| F2.2 | `CHUNKS × payload_size` exceeds free contiguous heap | Allocation fails mid-transfer | Allocated **before** the first ACK, so a failure aborts the transfer cleanly rather than half-way; degrades to the sentinel and a resync |
| F2.3 | Running total would overshoot `exp_size` | A malicious or desynced peer overruns the destination | Checked incrementally, before the copy, not only at the end |
| F2.4 | Final total ≠ `exp_size` | A short transfer reported as success | Final exact-match check, and the final ACK deferred until after it — so the sender learns of the rejection by timing out |
| F2.5 | `SIZE == 0` on chunk 2 of a two-chunk train | A genuinely empty payload, which is a distinct outcome from failure | Returned as a zero-length result, not `None`; `None` means failure only (decision, §3.9) |
| F2.6 | Train never completes (peer goes silent mid-train) | The receiver holds a half-filled destination forever | Inter-part timeout abandons it; resync; sentinel |
| F2.7 | A duplicate frame arrives | The same chunk appended twice | `UID` and `CUR_CHUNK` checks reject it (D4.3) |
| F2.8 | `exp_size` larger than `CHUNKS × payload_size` could ever deliver | The transfer is doomed but runs to completion first | Rejected at the first frame, once `CHUNKS` is known |
| F2.9 | Caller-supplied destination buffer too small (`_into` form) | Overrun | Length checked against `exp_size`/`CHUNKS` before the first ACK |

**Function tests.** `[mock]` a multi-chunk payload arrives byte-identical; all three `exp_size`
modes; the empty-payload outcome distinct from failure.
**Failure tests.** `[mock]` each of F2.2-F2.9; the deferred-ACK behaviour proven by asserting the
sender times out when the final size check fails.

**Sources.** J.4, J.8, I.1, I.4.

### F3 — GET request and response

**Spec.** The initiator sends a one-chunk GET train whose payload is the command ID; the responder
answers with a **SET train in the opposite direction** whose chunk 1 echoes that same ID. A GET
answer is literally a SET transfer, which is why two primitives — send a train, receive a train —
cover all four directions, and why the responder's GET branch and the initiator's SET path are the
same code.

**Purpose.** Halves the state machine. It also means every fix to F1/F2 applies to all four
directions at once.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| F3.1 | The answering SET echoes a different command ID | The initiator accepts an answer to a question it did not ask | ID compared; mismatch → resync, sentinel |
| F3.2 | No answer arrives | The initiator waits forever | Bounded by `timeout` → resync, sentinel |
| F3.3 | The responder's `get_callback` reports invalid | A GET for something the application does not have | Withhold the answer, resync, and report the distinct outcome to the responder's caller — not silently nothing |
| F3.4 | The answer is a GET rather than a SET | Both sides initiating | Rejected (D4.10/E2.3) |

**Function tests.** `[mock]` a full GET round trip between two instances; the answer's ID matches.
**Failure tests.** `[mock]` each of F3.1-F3.4.

**Sources.** J.4.

### F4 — `uart_listen()` and callback guarding

**Spec.** Returns a module-level **namedtuple** (`cmd_id`, `cmd`, `payload`) on **every** path,
including today's fall-through, which currently returns a bare `None`. Caller-supplied callbacks
(`get_callback`, `set_callback`) are guarded with the established dispatch shape: validate payload →
`try`/`await` the callback → `except Exception` → `err_s(...)` → defined failure result. Both sync
and async callbacks are supported, or the required form is enforced. A callback's **return shape is
validated, not trusted**.

**Purpose.** This is the responder's entire public surface, and the one place where arbitrary
application code runs inside the protocol's critical section.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| F4.1 | A path falls off the end | Returns a bare `None`; a caller unpacking three values raises `TypeError` inside a never-raise module's caller | Every path returns the namedtuple explicitly; mypy enforces it once the return type is declared |
| F4.2 | Callback raises | The exception escapes into the protocol layer and kills the listen task | `try`/`except Exception` → `err_s` → defined failure result → resync |
| F4.3 | Callback returns the wrong arity or type | `TypeError`/`ValueError` on unpacking — the same escape by another route | Return shape validated before use; a malformed return is treated exactly like a raise |
| F4.4 | Callback returns a negative or absurd expected size | Propagates into F2's sizing and allocates nonsense | Validated against `0 … (0xFF − 1) × payload_size`; out of range → treated as invalid |
| F4.5 | Callback blocks for a long time | The bus lock is held; the peer times out and resyncs; worse, timing-sensitive work elsewhere stalls | Documented contract: a callback must not block. A slow callback is the application's bug, but the resulting resync must be clean and logged so it is diagnosable |
| F4.6 | Callback is `None` | Every GET or SET is unanswerable | Checked at construction or at first use, with a distinct errno — not an `AttributeError` at the worst moment |
| F4.7 | Namedtuple allocation fails | `MemoryError` out of a never-raise module | Caught; degrades to a preallocated "failure" instance or the sentinel path |
| F4.8 | Callback mutates the buffer it was handed | The frame under construction changes mid-send | Documented ownership; the callback receives a `memoryview` of a region it may fill, not the whole frame |
| F4.9 | Callback re-enters the module — e.g. a `get_callback` that itself calls `uart_set()` | `asyncio.Lock` is **not** reentrant: the callback awaits a lock its own caller holds, and the task deadlocks with the bus held. Nothing times out, because nothing is waiting on the wire | Documented as forbidden, and structurally prevented where it can be: the public entry points refuse while this instance is inside a transaction, returning the sentinel with a distinct errno rather than deadlocking |

**Function tests.** `[mock]` GET and SET both dispatch to the right callback and return the right
namedtuple; a sync and an async callback both work.
**Failure tests.** `[mock]` each of F4.1-F4.7, each asserting a logged errno and a clean resync;
`[mock]` F4.9's re-entrant callback returns a sentinel instead of deadlocking, with a bounded test
timeout proving it is not merely slow.

**Sources.** G.2's callback-dispatch guarding, C.7, decision §3.8.

### F5 — Structural role enforcement

**Spec.** `role` is a constructor parameter. `uart_get()`/`uart_set()` refuse on a responder and
`uart_listen()` refuses on an initiator, with a logged refusal returning the module's normal failure
sentinel — C.13's readiness-gate treatment, never an exception. The responder's own answer to a GET
runs through the **internal unlocked SET path**, so the gate does not block it.

**Purpose.** Holding the session lock for the duration of one `uart_listen()` call is not sufficient
on its own: the lock is released between calls, so an application could interleave an initiation
into a responder's listen loop and produce exactly the simultaneous initiation the design has no
arbitration for.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| F5.1 | Application initiates on a responder between listen calls | Both sides transmit; no arbitration exists; the link desyncs in a way neither side caused | Refused at the entry point, logged, sentinel |
| F5.2 | Gate also blocks the responder's own GET answer | A responder can never answer anything — the protocol stops working | The answer path is internal and unlocked; asserted by a test that a GET is answered while the gate is active |
| F5.3 | Gate implemented as an assertion or exception | A never-raise module raises | Sentinel + log only |
| F5.4 | Role changed at runtime | The state machine and the task set no longer match | Immutable after construction; no setter |

**Function tests.** `[mock]` an initiator's `uart_listen()` and a responder's `uart_get()`/
`uart_set()` both refuse; a responder answers a GET normally.
**Failure tests.** `[mock]` F5.1's interleaving attempt; F5.2's regression (the gate must not break
the answer path).

**Sources.** J.2.

### F6 — Paired `_into` APIs

**Spec.** `uart_set(id, data)`/`uart_set_into(...)` and `uart_get(id)`/`uart_get_into(id, buf)` —
the convenience form allocates and copies, the `_into` form takes a caller-owned buffer and does
neither. `asy_fram_manager.py`'s `AsyFramChunk` is the reference shape.

**Purpose.** The payoff is the composition, and it must actually be reachable:
`uart_get_into(id, chunk.get_data_buf())` must land a received payload directly in a FRAM chunk's
buffer — one allocation, zero copies, the same way `asy_sgp40_driver.py` → `voc_algorithm.py` →
`asy_fram_manager.py` already does.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| F6.1 | Only one half of a pair exists | The zero-copy path exists for reads but not writes — worse than neither, because it looks complete | Both halves land together; D.10 |
| F6.2 | Caller buffer too small | Overrun, or a silent truncation reported as success | Checked before the first ACK (F2.9) |
| F6.3 | Caller buffer is `None` (a failed `LockableBuffer`) | `AttributeError`/`TypeError` on use | `if buf is None: return <sentinel>` as the first act, the project-wide convention |
| F6.4 | Convenience form allocates on a path the `_into` form was added to avoid | The pair exists but the hot path still allocates | The hot path uses the `_into` form internally; the convenience form is a thin wrapper, as `AsyFramChunk.write()` wraps `write_into()` |
| F6.5 | Caller keeps using the buffer during the call | Data race | Ownership documented per method; the session lock covers this module's own use |

**Function tests.** `[mock]` both halves of each pair move identical bytes; the FRAM composition of
the Purpose paragraph works end to end.
**Failure tests.** `[mock]` F6.2 and F6.3 on every `_into` entry point.

**Sources.** G.2, J.8.

### F7 — Chunk-streaming callback forms

**Spec.** A callback form driving one chunk at a time in each direction, so a transfer larger than
free RAM can stream to or from FRAM/flash without ever existing whole in RAM.

**Purpose.** This is what makes "large payloads over little buffers" actually true rather than
half-true: without it, both endpoints must still materialise the whole payload, and the chunking
buys nothing for memory.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| F7.1 | Pull callback supplies fewer bytes than the chunk needs | A short middle chunk — which D4.5 makes the peer reject, correctly, but the fault is local | The final short chunk is legal only as the last one; a short non-final supply aborts the transfer locally with a distinct errno, before anything is sent |
| F7.2 | Pull callback supplies more than the chunk | Overrun of the frame's data region | It fills a `memoryview` of exactly the region; a longer write is impossible by construction |
| F7.3 | Push callback fails mid-train | Half the payload is stored | Abort, resync, sentinel — and the caller is told which chunk failed, since it owns the partial destination |
| F7.4 | Callback raises or returns a wrong shape | Same escape as F4.2/F4.3 | Same guard shape |
| F7.5 | Callback is slow (a real FRAM write per chunk) | The peer times out mid-train | Documented: the per-chunk budget is `timeout`; a backing store slower than that cannot be streamed to directly. This is a genuine deployment constraint, not a bug to hide |
| F7.6 | Total size unknown in advance for a pull callback | `CHUNKS` cannot be computed, and it must be declared in chunk 1 | The pull form requires a declared total size up front; a genuinely unknown length is out of scope for this protocol and is documented as such |

**Function tests.** `[mock]` a transfer streamed from a callback matches the same payload sent
whole; `[twin]` a payload streamed straight into a FRAM chunk.
**Failure tests.** `[mock]` F7.1-F7.4; `[mock]` a deliberately slow callback produces a clean
timeout and resync, not a wedge.

**Sources.** J.8.

---

# Phase G — Integration

### G1 — Wire into `dev`

**Spec.** Two instances on one board — one initiator on UART0 (tx=GPIO0, rx=GPIO1), one responder on
UART1 (tx=GPIO8, rx=GPIO9) — across the bench rig's permanent TX↔RX crossover jumper (GP0↔GP9,
GP1↔GP8), which exists for exactly this purpose. Both `UART` bus instances constructed with a
single-digit `poll_wait_ms`. Both registered in `_collect_error_sources()`, `_collect_level_setters()`
and the webserver's `error_sources=`, each with a distinct `name`.

**Purpose.** Makes J.7's self-compatibility property physically testable rather than only modelled,
and gives the module a live caller — the state `asy_uart_driver.py` has been missing since its own
promotion.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| G1.1 | `poll_wait_ms` left at its 20 ms default | Poll granularity dominates throughput: a 480-byte transfer spends ~1.1 s to move 480 bytes over an 11.5 kB/s link, ~4 % of capacity, almost all of it poll latency — making every other efficiency property irrelevant | Single-digit value, stated at the construction site with a pointer to J.6 |
| G1.2 | A wireless-reserved pin pair chosen (GPIO24/25 or GPIO28/29) | Silently collides with WiFi on Pico W — both pairs are inside a UART pin-mux group | The chosen pairs avoid both; the constraint is commented where the pins are declared |
| G1.3 | UART0 claimed by both the crossover jumper (GPIO0/1) and a BME688 (GPIO16/17) | One peripheral, one pin pair — the second construction silently wins or fails | Recorded where the dev wiring is declared; no BME688 driver exists in `src/` today, so it costs nothing now and everything later if unrecorded |
| G1.4 | A FRAM-backed logger inserted into dev's existing chunk order | `AsyFramManager` is a bump-pointer allocator — instantiation order *is* on-chip layout, so every existing chunk shifts and previously persisted logs become garbage | Both instances constructed **after** every existing dev module; two FRAM-backed instances mean two new chunks appended, never inserted |
| G1.5 | Both instances share one logger | Two links' histories merge into one `/status` entry | Distinct `name` per instance (C3.2) |
| G1.6 | Instances constructed with mismatched `payload_size`/`timeout` | The link desyncs outright and cannot self-heal (C2.2) | Both constructed from one shared constant, asserted by a test |
| G1.7 | Wiring added to `wozi` as well | wozi is never physically flashed; it would carry an untestable, unused peripheral and shift its FRAM layout | `dev` only, deliberately; stated so it does not look forgotten |
| G1.8 | Both instances constructed on the same UART peripheral id | The second construction re-inits the first's peripheral; one link object silently owns nothing | Distinct ids (UART0 and UART1), asserted by the wiring test |
| G1.9 | `rxbuf`/`txbuf` left at the driver default while `payload_size` is large | C2.9/C2.10's silent tail-drop, introduced at the wiring layer rather than in the module | Both sized from the real frame size at the construction site, next to the `poll_wait_ms` comment |

**Function tests.** `[twin]` the dev object graph constructs both instances and both appear in the
error-source and level-setter lists; `[flash]` a real GET and SET across the jumper.
**Failure tests.** `[twin]` G1.5's distinct-name assertion; G1.6's shared-constant assertion;
`[twin]` the FRAM chunk order is unchanged for every pre-existing module (G1.4).

**Sources.** J.6, J.7, A.7, `dev_legacy/README.md`, owner decision 2026-09-11.

### G2 — Observability means

**Spec.** The module provides what every other module provides: `name` matching `self.pr.name`,
`get_error_counter()` returning the shared `ErrorLog` envelope, `reset_error_counter()`. The website
side — a `{key, label}` entry per instance in `html/definitions/dev.json`'s errcount list, and its
`js/` mirror — is the wiring layer's job, solved upstream identically to every other module.

**Purpose.** The counters come free with the logger (C3); this item is only about exposing them
through the established registration shape rather than a bespoke one.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| G2.1 | `name` ≠ `self.pr.name` | The registration keys on one and the history on the other; `/status` shows an empty entry | Set together in `__init__`, asserted by a test |
| G2.2 | `get_error_counter()` annotated with a re-spelled dict type | Loses the `TypedDict` precision that lets callers index `ErrNum[-1]` without narrowing | Annotate `"ErrorLog"`, the single shared declaration |
| G2.3 | A `src/`-side change without its `js/` mirror | Backend and frontend encode different policies | One change, not two — G.2's cross-language rule |
| G2.4 | An instance missing from the definitions list | Its counters exist but are invisible on the website indefinitely | One entry per instance, checked by the definitions-file validation |

**Function tests.** `[mock]` the registration shape is satisfied; `[twin]` `/status`'s `errcount`
contains both instances.
**Failure tests.** `[twin]` a forced error on one instance appears under that instance's key only.

**Sources.** H.6, G.2, A.8.

### G3 — Twin integration

**Spec.** `tests/test_digital_twin_*.py` coverage driving the real object graph with both instances,
per C.11 item 9 — same session, not deferred.

**Purpose.** A module with no twin counterpart silently regresses the Unix-port integration run's
coverage.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| G3.1 | Twin coverage deferred "until the module is done" | It never happens, and the regression is invisible because nothing fails | Same session; the done criteria list it explicitly |
| G3.2 | Twin run leaves sibling tasks parked at exit | The whole test process hangs after the last test's pass line — a known, already-diagnosed failure shape | `tests/microtest.py`'s forced `sys.exit()` already covers it; do not reintroduce a bounded-completion path that relies on idle detection |

**Function tests.** `[twin]` a full exchange inside the real task graph.
**Failure tests.** `[twin]` one-sided silence recovers; the run terminates.

**Sources.** C.11 item 9, A.10, CLAUDE.md's known hang cause #2.

---

# Phase H — Hazard and hardware tiers

### H1 — Mock comm-hazard suite

**Spec.** The UART-shaped analogue of C.8's standing bus-hazard rule, with one structural
difference: a UART link has **exactly two participants, never more and never fewer**, so there is no
multi-device interleaving or address-sweep dimension. What replaces each:

- *Same-instance concurrency* — two tasks initiating on one instance at once, and a `clear()`/
  `cancel_read_timeout()` racing an in-flight transaction, must serialize on the session lock or be
  refused, never corrupt a frame.
- *Both-participants-transmitting* — out of contract by design, so the test proves it is **detected
  and recovered from**, not that it works.
- *Frame/field sweep* — every `CMD`, `SIZE`, `CHUNKS`, `CUR_CHUNK` and `UID` value across its legal
  and illegal range, replacing the I2C address sweep.

**Purpose.** Byte-exact wire-log proof at the cheapest tier, where a failure is diagnosable in
seconds rather than on a bench.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| H1.1 | Two tasks initiate concurrently on one instance | Interleaved frames; both transactions corrupt | Session lock serializes them, or the role gate refuses; asserted on the wire log, not just by return values |
| H1.2 | `clear()` races an in-flight transaction | The drain consumes the transaction's own ACK | E5's ordering; asserted by a test that the transaction either completes or fails cleanly, never silently half-completes |
| H1.3 | Both participants transmit at once | Out of contract; no arbitration | Detected, logged distinctly, both resync; asserted that both sides return to a working exchange afterwards |
| H1.4 | Sweep covers only legal values | Every rejection path is untested, which is most of D4 | The sweep spans illegal values too, one assertion per D4 row |
| H1.5 | Sweep asserts return values only | A frame rejected *and* one silently mishandled both return failure | Wire-log assertions: what was emitted, and that nothing was emitted where an ACK must be withheld |

**Function tests.** `[mock]` the legal half of the sweep.
**Failure tests.** `[mock]` the illegal half, plus H1.1-H1.3.

**Sources.** C.8, owner direction 2026-09-11.

### H2 — Twin concurrency suite

**Spec.** Both instances under genuine concurrent task load inside the real object graph — the
webserver, the sensor readers and the link all running together.

**Purpose.** Realistic stateful/concurrent/timing behaviour that the mock tier's synthetic scheduling
cannot reach.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| H2.1 | Link work starves other tasks | The Neopixel animation stutters; a sensor trigger is missed | Every wait yields; asserted by checking other tasks keep progressing during a maximum-length transfer |
| H2.2 | Other tasks starve the link | Frames time out under load and the link resyncs continuously | Timeouts sized with headroom over the worst observed scheduling delay; a load test asserts a clean transfer under full system load |
| H2.3 | A GC pause lands mid-frame | A spurious inter-part timeout | `timeout` ≫ the measured ~15-21 ms worst-case pause (C2.4); asserted under a forced-collection test |

**Function tests.** `[twin]` a full transfer under concurrent load.
**Failure tests.** `[twin]` H2.1-H2.3.

**Sources.** E.6.1, I.1, F.3.

### H3 — Flash tier over the crossover jumper

**Spec.** Real hardware, dev bench, over the permanent jumper, under the project owner's go-ahead
given directly in the running session.

**Purpose.** Real timing, real UART peripheral behaviour, real `poll_wait_ms` latency — the three
things no fake reproduces.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| H3.1 | Test touches the RP2040's own flash filesystem | A real write-safety constraint violated | Construct the module directly (the DUT), never through a variant's full task graph, per C.8's standing constraint |
| H3.2 | A FRAM-backed logger writes on every injected fault | The NVM write budget is spent by a test suite | At most one real write per hazard group, via a session-scoped fixture; or RAM-only loggers for the hazard tier |
| H3.3 | Real electrical behaviour differs from the fake (line idle state, break detection) | A fault class that only exists on hardware is never exercised | This tier is where it is found; findings feed back into A3's knob list rather than being fixed only on hardware |
| H3.4 | A run is attributed to wozi's code | Testing nothing at all — the documented false-bug trap | Genuinely dev-native code via dev's own entry point, never wozi's build forced onto dev hardware |

**Function tests.** `[flash]` a GET and a SET across the jumper; a maximum-length train.
**Failure tests.** `[flash]` one-sided silence (hold one side off) recovers; a deliberately
mismatched `payload_size` fails loudly rather than silently corrupting.

**Sources.** C.8, E.6.3, CLAUDE.md's hardware go-ahead rule and wozi/dev mismatch rule.

### H4 — Bench tier under API load

**Spec.** The same link under the full HTTP stack and concurrent API load.

**Purpose.** Proves the link and the webserver coexist — the realistic deployed condition.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| H4.1 | Link transfer blocks a request, or vice versa | Both degrade under combined load in a way neither shows alone | Concurrent-load test asserting both complete within their own budgets |
| H4.2 | Worker set extended with unsafe requests | A `PUT` that persists, run in a loop, burns flash | `GET` always safe; `PUT` only where documented command-only/never-persisted |

**Function tests.** `[bench]` a transfer completes while the API is hammered.
**Failure tests.** `[bench]` an injected link fault does not disturb the API, and an API overload
does not corrupt a transfer.

**Sources.** C.8 tier 4, E.6.1.

### H5 — Fault-injection adapter seam

**Spec.** The flash/bench tiers are structured so a real fault-injection adapter (pull a line, invert
it, inject noise, desync the baud rate) can be added **without reshaping the tests** — per E.6.2's
capability-adapter pattern, where each backend supplies a narrow adapter rather than a
reimplementation.

**Purpose.** The two-participant topology makes real hardware injection genuinely possible in a way a
shared multi-drop bus does not. Owner direction: it is future work, but the harness must not preclude
it.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| H5.1 | Tests written against the mock's injection API directly | Adding a hardware injector means rewriting every test | Shared test bodies take a capability object; each backend supplies the adapter |
| H5.2 | `flash` has no injector | A shared body silently skips, or fails | Each shared function's docstring states applicable/N-A backends — documentation discipline, as E.6.2 already specifies |

**Function tests.** n/a — this item is structural.
**Failure tests.** n/a. Its verification is that H1's bodies run unchanged on the twin tier.

**Sources.** E.6.2, owner direction 2026-09-11.

---

# Phase I — Close-out

### I1 — Documentation

**Spec.** `SPECIFICATION.md` Part J describes the promoted module, not the legacy one. C.7.1's
`errno`/`wrnno` table gains this module's row(s). C.3.2's "orphan module, no `self.pr` yet" note for
`asy_uart_driver.py` is revisited now that it has a real caller. Part G.2 gains any genuinely new
reusable primitive (the framing codec is a candidate). A.3's refactor status and A.7's chunk order
are updated. `tests/test_ticks_rollover.py`'s audit note covers the new deadline site.
BACKLOG.md's `asy_uart_driver.py`-has-no-callers item is resolved and removed. README.md's doc map
drops this file when it is deleted.

**Purpose.** The specification is the normative artefact — a promoted module whose spec still
describes its ancestor is worse than an unpromoted one, because the next session trusts the document.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| I1.1 | Part J still describes the legacy shape | The specification and the code disagree, and the specification is the normative one | Updated in the same change, not a follow-up |
| I1.2 | An errno emitted but not tabled | `/status` shows an unexplainable number | C3.7's range sweep catches it mechanically |
| I1.3 | This file survives the merge | A temporary scope document becomes stale permanent documentation | Deleted at merge; the doc map entry goes with it |
| I1.4 | A permanent fact is left only in this file | It is deleted at merge and the fact is lost | Anything outliving the promotion migrates to `SPECIFICATION.md` first; the deletion commit is where that is checked |

**Function tests.** n/a — verified by review against the merged code, plus C3.7's mechanical errno
sweep and the definitions-file validation.
**Failure tests.** n/a.

**Sources.** CLAUDE.md's documentation rules, C.7.1, A.3, A.7.

### I2 — Changelog classification

**Spec.** Every change classified Class A (protocol-level, must be mirrored in C) or Class B
(Python-internal, logged as explicitly no-impact), with each Class A entry's "verify in C" column
filled in and its flag-day consequence stated.

**Purpose.** The C implementation is not in this repo, so this log is the only thing carrying these
decisions across the gap. A missed entry is a silently incompatible peer discovered on a bench.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| I2.1 | A wire-visible change logged as Class B | The reconciliation session misses it; the C peer is silently incompatible | Classification rule applied per change: does it alter emitted bytes, accept/reject rules, or timing the peer depends on? |
| I2.2 | A Class B change not logged at all | A future session re-derives it from scratch | Class B is logged precisely so it is visibly considered and dismissed |
| I2.3 | Emitted-bytes change without a stated interim | A deployed Arduino is stranded with no recorded route back | Each such entry names the interim — usually running the link with `CRC_Pass`, or keeping the peer on the legacy build until reflashed |
| I2.4 | An entry asserts what the C side does | Its conformance is expected but **unverified** — it may not share every known flaw and may have its own | Every Class A entry states what to *check*, never what is true; re-verified against the real C source when it lands |

**Function tests.** n/a — a documentation gate.
**Failure tests.** n/a. Its check is that every commit touching wire behaviour also touches the
changelog, verifiable from the diff.

**Sources.** J.1, CLAUDE.md's two-implementation hard rule.

### I3 — Pipeline verification and bird's-eye scan

**Spec.** `scripts/lint.sh`, `scripts/typecheck.sh` (all three passes) and `scripts/test.sh` run and
their output read — not assumed — with the finding count diffed against untouched files. Then the
bird's-eye scan over the whole of `src/` that CLAUDE.md requires whenever a new file lands there,
covering Part D's checklist and Part G's catalog.

**Purpose.** Everything above is a claim until the gates actually run; and a new file in `src/` is
the moment the project re-checks that its conventions still hold everywhere, not just here.

| # | Trigger | Symptom if unhandled | Required handling |
|---|---|---|---|
| I3.1 | Success reported without running the gates | The exact thing D.14 exists to prevent | Run them; read the output |
| I3.2 | The scan surfaces a cross-file discrepancy and it is silently fixed | A behaviour change nobody agreed to, buried in a promotion diff | Report and discuss before changing — the same "flag, don't silently change" treatment D.1 gives formula discrepancies |
| I3.3 | `uv.lock` touched by a merge | The tool pins are silently bypassed; `uv lock --check` does not catch it | `uv sync` then compare `ruff --version`/`mypy --version` against the pins |
| I3.4 | Tests pass but would also pass with the fix reverted | A test suite that proves nothing, as happened once with the streaming hammer tests | For each substantive fix, revert it locally and confirm a named test fails |
| I3.5 | A test hangs rather than fails | The per-file timeout fires and the cause is attributed to infrastructure | The `timeout`+retry, line buffering and forced-exit backstops stay in place; a new hang is diagnosed against the two already-known causes before being treated as new |

**Function tests.** The gates themselves, run and read.
**Failure tests.** I3.4's revert-and-confirm pass over every substantive fix in the branch.

**Sources.** D.13, D.14, CLAUDE.md's bird's-eye-scan rule and hang backstops.

---

# 3. Settled decisions

Owner decisions, 2026-09-11, with the derivations they drive:

1. **Logger.** Both construction routes, exactly as `SensorReader.__init__` shapes them —
   `fram=`/`history_length=`/`debug=`/`name=` through `make_logger()`, or a `logger=` reach-through
   to an upstream instance's own, the way `AsyFramManager` hands `self.pr` down to `FRAM_SPI` and
   its chunks. Consequence: a shared logger is a shared numbering space (C3.1).
2. **Base class** (delegated to this scope, resolved against precedent): plain class, not a
   `SensorReader` subclass. Every existing subclass is one for a measurement snapshot or a
   `ConfigManager`-backed schema; this module has neither — `payload_size`/`timeout` are out-of-band
   agreements a runtime write must not be able to desync, and a link-state snapshot would be a new
   top-level feature the refactor is not for. `AsyFramManager` is its closest structural match.
   `_error_check()` is neither reimplemented (G.1) nor needed: its give-up exists so the supervisor
   can re-run `_init_<sensor>()` and re-initialize hardware, and this module owns none. C.9's capped
   exponential backoff is the primitive that fits a link fault (C5.2).
3. **FRAM backing.** Optional but always possible, exactly as project-wide. Consequence: G1.4.
4. **Target variant.** `dev`, two instances across the crossover jumper (G1).
5. **`errno`/`wrnno` numbering.** Aligned to the `SensorReader` reservation regardless of base class
   — `errno` from 10, `wrnno` from 10 (C3). Modules currently not aligned are recorded in BACKLOG.md
   as a separate fix, not corrected drive-by from this branch.
6. **Comm-hazard testing.** All four tiers, two-participant shape, hardware fault injection as
   future work the harness must not preclude (H1-H5).
7. **Website.** Solved upstream; this module provides the same means every other module does (G2).
8. **`uart_listen()` returns a namedtuple** (`cmd_id`, `cmd`, `payload`) on every path. Its one
   allocation is per logical message, not per frame — a 255-chunk train still allocates exactly one
   — so the zero-allocation frame path is untouched. C.6's `make_dict()` repr-parsing landmine does
   not apply: it is never serialized.
9. **`uart_get()`'s empty-payload result.** `None` means failure, a zero-length result means a
   genuinely empty payload. The `_into`/callback forms mirror it as `None` vs. 0 bytes written.
   Nothing to build — it must be documented as contract and covered by a test that fails if the two
   ever collapse (F2.5).
10. **Lost final ACK** folds into failure. A caller cannot act differently on "delivered but
    unconfirmed", no retransmission exists to hang a third state on, and the application-level
    answer is the same either way (E1.6).
11. **CRC/framing ownership.** `asy_uart_driver.py` gains a framing-codec concept (B2), which
    resolves changelog A11's open design question. The mechanism is Class B; selecting COBS is A11's
    own Class A flag day.

# 4. Legacy violation map

Line references are `python/IndividualDrivers/asy_uart_comm.py` as it stands today, each mapped to
the item that fixes it. This is the "what actually has to change" view, not a second requirement
list.

| Lines | What it does | Fixed by |
|---|---|---|
| 3 | `import math` for one `ceil()` on a float division | C1.5, F1 |
| 5 | imports the legacy `asy_uart.AsyUART` | C2 |
| 23 | untyped constructor, `debug=False`, no `fram`/`history_length`/`name`/`logger`/`role` | C1, C2, C3 |
| 28, ~30 sites | `self.debug` + `if self.debug: print(...)` | C3, C1.4 |
| 29, 45 | one-shot soft `Timer` write gate, `Timer.init()` unguarded | E3.1, E3.2 |
| 42-44 | unbounded drain loop | E4.1 |
| 48-86 | `uart_listen()` falls off the end returning bare `None`; callbacks called bare and sync-only | F4.1-F4.3 |
| 59 | command ID taken from the payload without checking `SIZE == 1` | D4.4 |
| 95 | `del filled` — dead statement | C1 |
| 100-101, 170-171 | `bytearray(1)` allocated per call for a single ID byte | C4 |
| 119, 139 | `res = bytearray()` grown by `+=` across the train | F2.1 |
| 139 | `msg[a:b]` slice copy per chunk | D2, F2.1 |
| 162 | `math.ceil(len(payload) / self.payload_size) + 1` | F1, C1.5 |
| 164 | guard comment says "16bit payload field"; the field is 8-bit | I1 |
| 184-185 | `payload[:size]` / `payload[size:]` — two allocations per chunk, O(n²) over a train | F1.2 |
| 190-199 | `_build_msg()` — three allocations per frame | D1, C4 |
| 205 | `if not (msg[_MSG_CMD] & exp_cmd)` — bitmask, so `0x06`/`0x03` pass then match no branch | D4.1 |
| 208-217 | no `CHUNKS`-constancy check, no `UID` check on data chunks, no per-position `SIZE` invariant | D4.2, D4.3, D4.4-D4.6 |
| 221 | `await self.enable_writing.wait()` — unbounded, set only by a droppable callback | E3.1 |
| 226, 253 | `read_until_complete()` — allocates a fresh frame buffer per read | D2, C4 |
| 223, 264 | `device.write(msg)` — allocates a CRC-appended copy per write | D1, C4 |
| 239-241 | `else:` after `return`; no `UID` check on a non-ACK reply | C1.4, E1.2 |
| 263 | ACK built through `_build_msg()`, allocating a fully padded frame per ACK | D5.3 |
| (absent) | `name`, `get_error_counter()`, `reset_error_counter()`, starters, `setup()`, role gate, parameter validation | C2, C3, C5, F5 |

# 5. Findings raised, not fixed here

Both follow CLAUDE.md's "flag, don't silently change" rule.

- **`asy_uart_driver.cancel_read_timeout()` can hang forever, and can drop a cancel request** (B1.1,
  B1.2) — a defect in already-promoted code, in the exact mechanism J.5 designates as the recovery
  route for a blocked listener. It is a prerequisite for E5, so this branch must fix it; it is
  reported rather than folded in quietly.
- **Seven `src/` modules number `errno`/`wrnno` inside the range `base_classes.py` reserves** —
  BACKLOG.md item 16. No live clash today; a real defect the moment any of them gains a `logger=`
  reach-through, which is precisely the pattern this module adopts.

# 6. Done criteria

Each verified by running it, not by inspection:

- `scripts/lint.sh`, `scripts/typecheck.sh` (all three passes) and `scripts/test.sh` exit 0 with zero
  findings, and the finding count on untouched files is unchanged.
- Every item above has its function tests **and** its failure tests, and every `Fx.y` row has at
  least one test that fails if its handling is removed (I3.4).
- The flash and bench comm-hazard tiers run clean on the dev bench over the real crossover jumper,
  under the project owner's go-ahead given directly in that session.
- §4's table is fully struck through — every listed violation actually fixed, not deferred.
- `SPECIFICATION.md`, `UART_C_PORT_CHANGELOG.md`, `BACKLOG.md` and README.md's doc map are updated in
  the same change set.
- The bird's-eye scan over `src/` has been re-run after the file lands, with any cross-file
  discrepancy reported and discussed rather than silently fixed.
- The file reads as if it had always been part of `src/` (§0).
