# UART module promotion — conformance requirements

**Temporary file. Delete it once `asy_uart_comm.py` is in `src/` and the promotion branch is
merged** — it is the refined scope of that one unit of work (CLAUDE.md's step-session workflow,
step 1), not a permanent specification. Everything in it that outlives the promotion belongs in
`SPECIFICATION.md`; everything protocol-facing belongs in `UART_C_PORT_CHANGELOG.md`.

## 0. What "promotion" means here

Promotion is not "move the file and fix the bugs". The promoted module must be indistinguishable in
shape from a module written natively for `src/`: same layering, same constructor conventions, same
injected logger, same buffer ownership, same never-raise/never-wedge contracts, same test tiers.
**The coherence test**: read `asy_fram_manager.py`, `captive_dns.py` and the promoted
`asy_uart_comm.py` back to back — nothing about the third should read as an import from elsewhere.

Sources, in precedence order: `SPECIFICATION.md` Part D (the "good enough for `src/`" checklist),
Part C (driver architecture — applies by analogy, this is not a sensor), Part G (shared-primitive
reuse), Part I (memory-safety ladder), Part F (platform facts), Part J (this protocol's own
specification), CLAUDE.md's hard rules. This file does not restate them; it derives what each one
concretely demands of *this* module and how it will be checked.

## 1. Module and naming shape

| # | Requirement | Source |
|---|---|---|
| 1.1 | Module stays `asy_uart_comm.py`, one file, sitting above `asy_uart_driver.py` exactly as `asy_fram_manager.py` sits above `asy_fram_driver.py` | C.2 |
| 1.2 | Module docstring: **at most 3 lines**, a header not an essay. Permanent architectural facts go to `SPECIFICATION.md` Part J with a short pointer left behind | CLAUDE.md, D.11 |
| 1.3 | No per-function docstrings. Load-bearing "why" is a short `#` comment next to the line, ≤3 lines, or it moves to Part J | CLAUDE.md, D.11 |
| 1.4 | `_NAME = const("UART")` (or the chosen logger name) declared once at module level and used as the dict key everywhere — `get_error_counter()`, every `err_s`/`wrn_s` call site | C.2, C.7 |
| 1.5 | Every wire constant stays `const()`-folded: `_CMD_*`, the five header offsets, `_NUM_MSG_FIELDS`, the recovery multipliers, the `UID` ceiling | C.2, F.1 |
| 1.6 | CapWords class names (`UART_Comm` keeps the `FRAM_SPI`/`SCD30_I2C` compound convention); `lower_snake_case` methods; `_`-prefixed privates. Local names follow suit — `bGetId`/`bSetId` become snake_case | C.2 |
| 1.7 | Method ordering: privates first, then publics; within each group starters → getters → setters → others; `__init__` first | D.15 |

## 2. Layering and decomposition

| # | Requirement | Source |
|---|---|---|
| 2.1 | The module owns **no hardware access**. Every byte moves through the injected `asy_uart_driver.UART` instance; `machine.UART` is never imported here | C.1, C.3.2 |
| 2.2 | The legacy `asy_uart.AsyUART` import is replaced by `asy_uart_driver.UART`. Their method sets differ — every call site is re-derived from the promoted driver's real signatures, not assumed | D.9, D.14 |
| 2.3 | No session/protocol class split (`*_DeviceSession` + `*_I2C`). C.3.2 settles this for a point-to-point link: one merged class, because there is no bus-sharing concept and the two lock layers collapse without losing distinction | C.3.2 |
| 2.4 | This is **not** a sensor driver: no namedtuple measurement shape, no `make_dict()`, no `get_data()`/`get_dict_data()`. Registering it as a `sensors=` module would be wrong | C.4.2, J.1 |
| 2.5 | **Plain class owning a `PrintLogHistory`**, the `AsyFramManager`/`SystemService`/`DNSServer` shape — not a `SensorReader` subclass. Derived from what the existing subclasses are actually for: every one of them subclasses for a measurement snapshot (`SCD30_Reader`), a `ConfigManager`-backed schema (`AsyConnTime`, `AsyNtpClient`, `NotificationCoordinator` — all `SensorReaderConfig`), or both. This module has neither, and the module closest to it by *role* — a chunking transfer manager sitting above a bus driver, owning a logger and sharing it downstream — is `AsyFramManager`, which is a plain class | C.4.3, G.1 |
| 2.5a | **No `ConfigManager` schema.** `payload_size`/`timeout` are agreed out of band and must match both ends; making them runtime-settable would let a REST write desync a working link. They stay constructor parameters under 10.1-10.2's readiness gate | J.6 |
| 2.5b | **No measurement snapshot.** A link-state namedtuple would be a new top-level feature, which the refactor explicitly is not — the module's observability is its error history, which 4.2 already gets for free | CLAUDE.md, J.1 |
| 2.6 | **`_error_check()` is not reimplemented here** — G.1 forbids re-rolling an established primitive, and a private method on a class this module doesn't subclass cannot be reused. It is also the wrong primitive: `_error_check()`'s give-up exists so the task supervisor can re-run `_init_<sensor>()` and re-initialize hardware, and this module owns no hardware to re-initialize — a restart would accomplish nothing the quiesce-and-resync has not already done | G.1, C.4.1 |
| 2.6a | **The listen loop escalates by capped exponential backoff instead**, `captive_dns.py`'s `DNSServer.run()` shape (0.5s → 5s cap, reset on success) — C.9's cascading-recovery-storm convention, which exists precisely for a loop whose failures return sentinels rather than raising, so no outer `except` ever fires | C.9 |
| 2.6b | The loop returns (letting the supervisor restart it) **only on a readiness failure** — no bus handle, `setup()` never ran, role mismatch — never on a link fault, which is self-healing by design | C.13, J.5 |
| 2.7 | `uart_listen()` returns a module-level **namedtuple** (`cmd_id`, `cmd`, `payload`), every path returning it explicitly. Its one allocation is **per logical message, not per frame** — a 255-chunk train still allocates exactly one — so §7's zero-allocation requirement, which is about steady-state *frame* traffic, is untouched. C.6's `make_dict()` repr-parsing landmine does not apply: this namedtuple is never serialized | Owner decision, C.6, J.8 |

## 3. Construction contract

| # | Requirement | Source |
|---|---|---|
| 3.1 | Constructor parameter order follows the project convention: the bus handle first, then module-specific parameters, then `max_module_error` (if used), then `fram`, `history_length`, `debug`, `name`/`logger` | C.2 |
| 3.2 | `debug` is `int | None` (a log *level*), never the legacy `bool`. `self.debug` disappears entirely | C.7, print_log.py |
| 3.3 | **Logger injection is supported both ways, and this is the settled decision** (owner, 2026-09-11): `fram=`/`history_length=`/`debug=`/`name=` construct one via `make_logger()`, **or** a caller-supplied `logger=` reaches through to an upstream instance's own. The shape is copied from `SensorReader.__init__` (`if logger is not None: self.pr = logger else: self.pr = make_logger(...)`); the live precedent for the reach-through half is `AsyFramManager` handing `self.pr` down to `FRAM_SPI` and to every chunk | Owner decision, G.2, base_classes.py |
| 3.3a | **`fram=` is optional but always possible**, the project-wide default for every non-FRAM module: passing it selects `PrintLogHistoryStore`, omitting it selects `PrintLogHistory`, and `make_logger()` already makes that choice. No FRAM-specific code is written here | Owner decision, C.7 |
| 3.3b | **`name` is a constructor parameter with `_NAME` only as its default.** This is the first logger-owning service module that can legitimately exist more than once on one device (dev runs two — 16.9), so a hardcoded single identity would merge two instances' error histories into one stream. `ConfigManager(path, schema, name)` is the precedent | C.2, 16.9 |
| 3.4 | `role` is a constructor parameter. It is not inferable and has no safe default that suits both ends | J.2 |
| 3.5 | `__init__` is synchronous and allocates only: no `await`, no I/O, no bus touch. Anything needing an await goes in `async def setup()` behind the standard `self.initialized` gate | C.13 |
| 3.6 | `self.name` is set and equals `self.pr.name` — the `_ModuleLike` registration shape the webserver keys on | asy_webserver_service.py, captive_dns.py |

## 4. Logging, counters and observability

| # | Requirement | Source |
|---|---|---|
| 4.1 | **Every one of the ~30 `if self.debug: print(...)` sites is replaced by the injected logger.** Trace/info → `pr.all()`/`pr.evt()`/`pr.one()`; anything that should count → `pr.err_s(..., errno=N)`/`pr.wrn_s(..., wrnno=N)` | C.7, G.2 |
| 4.2 | **No bespoke counter mechanism is added.** The `PrintLogHistory` error history *is* the protocol's diagnostic counter, surfaced through `/status`'s `errcount`, with optional FRAM backing — free, once the logger is in place | Owner direction, C.7 |
| 4.3 | `err_s`/`wrn_s` are **async**. A synchronous call site (a `Timer` callback, a sync validation helper) may only use the non-persisting `pr.err()`/`pr.wrn()`; if a hot path cannot afford the await, the failure is still recorded — it does not silently drop to `pr.all()` | print_log.py, system_service.py |
| 4.4 | **`errno` numbering starts at 10 and `wrnno` at 10, aligned to the `SensorReader` reservation even though this module does not subclass it** (owner direction, 2026-09-11): `base_classes.py` owns `errno` 1-9 and `wrnno` 1-2, and `api_response.py`'s `handle_set_cmd()` owns the fixed cross-module slot `errno=99`. Alignment is for conformity and clash avoidance, and under 3.3 it is not merely cosmetic — see 4.4a. `asy_sgp40_driver.py` (`errno` 10-18, `wrnno` 10-14) is the fully-conformant precedent | Owner direction, C.7 |
| 4.4a | **A shared logger is a shared numbering space.** When `logger=` reaches through, this module's codes land in the owner's single history stream under the owner's name, so the catalog must be **disjoint from that owner's own**, not merely ≥10. `AsyFramManager` (10-88) / `FRAM_SPI` (89-98) partitioning one stream is the reference | C.7, 3.3 |
| 4.4b | The three fixed common slots are honored where applicable: `10` = init failed, `11` = the module's primary periodic operation failed, `12` = a persisted-config read at init failed (not applicable here — leave `12` unused rather than reassigning it) | C.7 |
| 4.4c | The catalog is added to `SPECIFICATION.md` C.7.1's running table in the same change, one row, grouped by method | C.7 |
| 4.5 | `async def get_error_counter(self) -> "ErrorLog"` returning `await self.pr.get_log()`, and `async def reset_error_counter(self) -> None` calling `await self.pr.reset()` — both annotated with the shared `ErrorLog` type, never a re-spelled dict | G.2 |
| 4.6 | `await self.pr.setup()` is called once, at the start of whatever long-running task the module owns (or in `setup()` if it owns none) — without it FRAM persistence stays inert | base_classes.py, C.13 |
| 4.7 | A failure is never swallowed: no `except Exception: return None` without a logged `err_s`/`wrn_s` | C.7 |

## 5. Error-handling contract

| # | Requirement | Source |
|---|---|---|
| 5.1 | **Never raises, on any path, for any input.** Every public method returns a well-defined sentinel. This is the layer-3 contract; there is no raw-bus carve-out here, because this module never touches raw hardware | C.4, D.2 |
| 5.2 | Everything downstream (`asy_uart_driver.UART`) already returns sentinels rather than raising — but the module must still handle *every* sentinel: `None` from every read, `False` from every write, `False` from `ready()`. No result is used without checking it | C.3.2, D.2 |
| 5.3 | Caller-supplied callbacks (`get_callback`/`set_callback`, and any new chunk-streaming callback) are guarded with the established dispatch shape: validate payload → `try: await/call` → `except Exception` → `err_s(...)` → defined failure result. A misbehaving callback must not be able to break the link | G.2, C.7 |
| 5.4 | Callbacks must support both sync and async forms, or the module must state which it requires and enforce it. Today they are called bare and synchronously | B4 (changelog) |
| 5.5 | A callback's *return shape* is validated, not trusted: a tuple of the wrong arity, a non-`bytes` payload, a negative expected size are all caller bugs that must degrade, not raise | D.2, G.2 |
| 5.6 | No bare `except:` anywhere (ruff E722 is deliberately enabled); every catch names its types, except where a caller-supplied callback justifies a documented broad `except Exception` | CLAUDE.md, C.4 |
| 5.7 | Every code path returns explicitly. `uart_listen()`'s fall-through — currently returns a bare `None` instead of the documented three-tuple — is a concrete instance | D.7, B1 |

## 6. Resilience: never wedge, never block, self-heal

These are the requirements the legacy module most clearly fails, and they are structural, not
incidental.

| # | Requirement | Source |
|---|---|---|
| 6.1 | **No unbounded loop anywhere.** The drain loop in `_clear_buffers()` currently reads until the peer stops talking, forever if it never does. It gets a deadline — and the bound must never be shorter than the peer's own drain window | A5 (changelog), D.3, D.5 |
| 6.2 | **No unbounded wait on a flag that a dropped callback can leave unset.** `await self.enable_writing.wait()` has no timeout, and the only thing that sets it is a soft one-shot `Timer` callback, which MicroPython may silently drop when the scheduler queue is full | F.1, D.5 |
| 6.3 | **The write hold-off becomes a `ticks_ms()` deadline, not a `Timer`.** A deadline cannot be dropped, needs no alarm-pool slot, and removes 6.2's wedge at its source. `asy_bmp3xx_driver.py`'s `_wait_status_bits()` is the shape to model on | C.9, F.1, B2 (changelog) |
| 6.4 | If any `machine.Timer` survives the rewrite, it is `PERIODIC` (self-healing next tick), and every `Timer.init()` is wrapped in `except (OSError, MemoryError)` — never bare `OSError` | C.9, F.1 |
| 6.5 | Every `await` that can block indefinitely is either deliberately unbounded **and** externally cancellable (the responder's listen wait, via `cancel_read_timeout()` from another task), or bounded by a timeout. No third category | J.5, D.5 |
| 6.6 | A fault path must always converge: quiesce-and-resync, then the caller's normal failure sentinel. No path may return a "success" sentinel after an aborted drain | J.5 |
| 6.7 | Recovery must not be able to recurse: a failure inside `_clear_buffers()` must not re-enter `_clear_buffers()` | D.3 |
| 6.8 | The owned responder listen loop escalates rather than spinning, via the capped exponential backoff of 2.6a — a sentinel-returning failure never triggers an `except`, so without it the loop runs at full speed and floods the log (measured at ~5 lines/second in the case this convention was written for) | C.9's cascading-recovery-storm convention, I.4(c) |
| 6.9 | The module never stalls timing-sensitive work (the Neopixel animation): every wait yields, none busy-spins without `await` | F.3, D.5 |

## 7. Memory model and buffer ownership

Part J.8 is the module-specific statement of this; G.2 is the project-wide primitive. Both apply.

| # | Requirement | Source |
|---|---|---|
| 7.1 | **Two long-lived `LockableBuffer(5 + payload_size, data_start=5, data_length=payload_size)` per instance** (one TX, one RX), allocated once in `__init__` from configuration. Steady-state frame traffic allocates nothing | J.8, G.2 |
| 7.2 | `_build_msg()` disappears in its current form. It allocates three times per frame (`bytearray(5)`, `+= payload`, `+= padding`); header fields are written into the TX buffer by index instead | J.8, D.4 |
| 7.3 | Frames are read with `readinto_until_complete(buf, nbytes, ...)` into the RX buffer, not `read_until_complete()`, which allocates a fresh `bytearray` per frame | J.8, D.4 |
| 7.4 | Frames are written with `writefrom(buf, size)`, not `write(msg)` — `write()` allocates a CRC-appended copy of the whole frame | D.4 |
| 7.5 | **The receive accumulator is preallocated, never grown.** `res = bytearray()` + `res += ...` across a train is up to 254 reallocations and a ~2× peak on a 264 kB device. The upper bound `CHUNKS × payload_size` is known from the first frame; the exact size is known whenever `exp_size` was supplied | J.8, I.1 |
| 7.6 | The send path stops slicing the payload. `payload[:size]` / `payload = payload[size:]` allocates twice per chunk and is O(n²) over a train; `memoryview` slices replace both | D.4, I.1 |
| 7.7 | **Paired transfer APIs**, the `AsyFramChunk` shape: `uart_set(id, data)`/`uart_set_into(...)`, `uart_get(id)`/`uart_get_into(id, buf)` — the convenience form allocates and copies, the `_into`/`_from` form takes a caller-owned buffer and does neither | G.2, J.8 |
| 7.8 | **A chunk-at-a-time callback form** so a transfer larger than free RAM can stream to/from FRAM or flash without ever existing whole in RAM. This is what makes "large payloads over little buffers" actually true rather than half-true | J.8 |
| 7.9 | Fixed-size scratch (the one-byte command-ID buffer, the ACK frame, the zero-fill source for padding) is preallocated per instance, the `asy_fram_driver.py` `_id_buf`/`_status_buf` pattern. `bytearray(1)` per call disappears | G.2, D.4 |
| 7.10 | **Padding is zero-filled from a preallocated zero buffer** — leaving it unwritten would transmit the previous frame's payload remnants | J.8 |
| 7.11 | **A failed allocation degrades to the module's normal failure sentinel, never an exception.** `LockableBuffer` already catches `MemoryError`/`OverflowError` and leaves `buf = None`; every consumer's first act is `if buf is None: return <sentinel>` | G.2, I.4(b) |
| 7.12 | Any remaining allocation whose size is not a small provably-fixed constant runs through the I.4 ladder at design time — catch `(OSError, MemoryError)`, degrade locally, let the supervisor restart, watchdog last — and gets its own `gc.threshold(-1)`-first stress test | I.4(a)-(f) |
| 7.13 | The payoff is the composition, and it must actually be reachable: `uart_get_into(id, chunk.get_data_buf())` must land a received payload directly in a FRAM chunk's buffer, one allocation, zero copies, the same way `asy_sgp40_driver.py` → `voc_algorithm.py` → `asy_fram_manager.py` already does | G.2 |

## 8. Concurrency and locking

| # | Requirement | Source |
|---|---|---|
| 8.1 | The bus lock (`async with self.uart as uart:`) is held for the duration of one complete transaction, so a frame exchange cannot interleave with another task's | C.8, J.5 |
| 8.2 | Lock acquisition order stays fixed and single-layer; no second lock is introduced without a stated ordering rule | C.8 |
| 8.3 | `clear()` must keep taking the lock **only** when nothing was cancelled — cancelling an in-flight read from outside the lock is the documented way to unstick a blocked listener, and taking the lock first would deadlock against it | J.5, C.3.2 |
| 8.4 | The `UID` counter is touched only under the session lock, so it stays a plain `int` — `LockedCounter` would be wrong here, and the reason is worth one comment (`NotificationSignal`'s "only ever touched by one task" note is the precedent) | C.8, base_classes.py |
| 8.5 | Shared mutable state that *is* touched across tasks uses `base_classes.py`'s locked primitives, never a bare attribute plus an ad hoc lock | G.2 |
| 8.6 | **Role is enforced structurally**: `uart_get()`/`uart_set()` refuse on a responder and `uart_listen()` refuses on an initiator, with a logged refusal returning the normal failure sentinel. The session lock alone is insufficient — it is released between `uart_listen()` calls, so an application could otherwise interleave an initiation into a listen loop and produce the simultaneous initiation the design has no arbitration for | J.2 |
| 8.7 | The responder's own answer to a GET must keep running through the internal unlocked SET path, so the role gate does not block it | J.2 |

## 9. Timer / task / IRQ integration

| # | Requirement | Source |
|---|---|---|
| 9.1 | `get_task_starters()` and `get_timer_starters()` both exist, even if one returns `[]` — `system_service.py` discovers every module generically through these, never by name. `NotificationCoordinator.get_timer_starters()` returning `[]` is the precedent | C.9 |
| 9.2 | A responder's listen loop is a supervised task via `get_task_starters()`; returning `False` from it is the supervisor's restart signal | C.9, C.4.1 |
| 9.3 | A task tied to a runtime mode transition rather than boot may legitimately opt out of generic supervision (the `captive_dns` precedent) — but the opt-out is deliberate and commented, not an omission | C.9 |
| 9.4 | No business logic in any `Timer` callback: `.set()` on a `ThreadSafeFlag` and nothing else. Preferably no `Timer` at all (6.3) | C.9 |

## 10. Parameter validation and the readiness gate

| # | Requirement | Source |
|---|---|---|
| 10.1 | `payload_size` is constrained to `1 … 255` and **never silently clamped** — a mismatch between the two ends desyncs the link outright, so a clamp would convert a loud failure into a silent one | J.6, A6 (changelog) |
| 10.2 | An out-of-range `payload_size`/`timeout`/`role` gets C.13's readiness-gate treatment: `__init__` records "not ready", every entry point returns its sentinel with a logged error, nothing raises | C.13, J.6 |
| 10.3 | The gate's name and polarity are the standard `self.initialized: bool = False → True`, unless the meaning is genuinely different | C.13 |
| 10.4 | Buffer allocation failure is a *separate* condition from the readiness gate, handled by the `Type | None` complementary mechanism (`PrintLogHistoryStore.fram`'s shape) — both can coexist | C.13 |
| 10.5 | Runtime input already guaranteed by mypy is **not** re-checked at runtime — dead weight for a case that cannot occur | D.2, D.4 |
| 10.6 | `timeout` is validated as positive; the derived `1.5 × timeout` drain and cooldown are computed from it, never hardcoded | J.5 |

## 11. Primitives that must be reused, not reinvented

Part G.1 requires searching the catalog before writing anything. The findings for this module:

| Need | Use | Never |
|---|---|---|
| Per-module logging / error history / counters | `print_log.py`'s `make_logger()`, `PrintLogHistory`, `PrintLogHistoryStore` | a `debug` flag plus `print()`, or a bespoke counter |
| Error-log envelope type | `print_log.py`'s `ErrorLog` / `ErrEntry` | a re-spelled `dict[str, dict[str, ...]]` |
| Buffer ownership / zero-copy handoff | `base_classes.py`'s `LockableBuffer`, `get_buf()`/`get_data_buf()`, paired `*_into` APIs | fresh `bytearray()` per frame, `+=` accumulation, slice copies |
| Lock-scoped object / `async with` | `base_classes.py`'s `Lockable` | a bare `asyncio.Lock()` attribute |
| Shared mutable state across tasks | `LockedCounter` / `LockedFlag` / `LockedValue` | a module-level variable plus an ad hoc lock |
| Caller-supplied callback dispatch | the `_dispatch_*` guard shape | a bare call |
| CRC framing | the `crc_checks.py` `CRC_Base` family, configured on the `UART` bus object | a hand-rolled CRC, or a second CRC layer here (unless §19.4 decides otherwise) |
| Consecutive-failure-streak give-up | `SensorReader._error_check()` | a hand-rolled counter (see §19.1) |
| Bounded retry / backoff | `captive_dns.py`'s capped exponential backoff, or `asy_ntp_client.py`'s bounded 3-try shape | an unbounded or zero-delay retry |
| Deadline-bounded polling | `asy_bmp3xx_driver.py`'s `ticks_ms()`/`ticks_diff()` loop | a one-shot `Timer` |
| Integer ceiling division | plain integer arithmetic | `math.ceil()` on a float division (drops the `math` import entirely) |

If nothing matches and something genuinely new is built, and it is plausibly reusable, it is added
to G.2 in the same change.

## 12. Platform constraints to honor

| # | Requirement | Source |
|---|---|---|
| 12.1 | Soft `Timer` callbacks can be silently dropped (fixed-depth scheduler queue) — the fact 6.2/6.3 exist for | F.1 |
| 12.2 | `Timer.init()` can raise `OSError(ENOMEM)` on alarm-pool exhaustion; `MemoryError` is **not** an `OSError` subclass, so both must be named | F.1, C.9 |
| 12.3 | `struct.pack()` truncates silently — any header packing must be range-checked first, or written byte-wise by index | F.1 |
| 12.4 | The GC is non-compacting: a large contiguous allocation can fail with substantial free RAM. This is why §7 is about *contiguous* allocation, not total | I.1 |
| 12.5 | No `u`-prefixed module names, no pre-consolidation idioms; every API is re-checked against the current pinned MicroPython, not training memory | D.9, CLAUDE.md |
| 12.6 | `poll_wait_ms` dominates throughput: the `UART` instance driving this protocol **must** be constructed with a single-digit value. This is a wiring requirement, not a module-internal one, and it must be stated where the instance is built | J.6 |

## 13. Protocol-contract obligations

| # | Requirement | Source |
|---|---|---|
| 13.1 | Every change gets a `UART_C_PORT_CHANGELOG.md` entry, Class A (protocol-level) or Class B (Python-internal). Class B is logged too, so the reconciliation session does not re-derive it | CLAUDE.md, J.1 |
| 13.2 | Python may now lead a wire change (owner decision, 2026-09-11), but every entry still states its flag-day consequence for a deployed peer | changelog policy |
| 13.3 | The receiver-strictness tightenings already agreed (A1, A2, A3, A12) land as part of the promotion, not after it | changelog |
| 13.4 | Wire-visible invariants that must survive untouched: the `0xFE → 0` `UID` wrap and the `0xFF` barrier (A8), the `1.5 × timeout` drain and cooldown (A4), the `CHUNKS ≥ 2` floor, chunk 1 carrying the command ID with `SIZE = 1` | J.3, J.4, J.5 |
| 13.5 | Any code predicting a *next* `UID` reuses the same controlled wrap, never a bare `+1` | J.3 |
| 13.6 | Part J is updated in the same change for anything the promotion settles — it is the specification, not a description of the legacy file | J.1 |

## 14. Typing and lint

| # | Requirement | Source |
|---|---|---|
| 14.1 | Every parameter and return annotated; mypy `--strict` clean, no new `type: ignore` without a scoped reason | D.6, CLAUDE.md |
| 14.2 | PEP 604 `X | None` only, never `typing.Union` | CLAUDE.md, C.10 |
| 14.3 | `TYPE_CHECKING` guarded by `try/except ImportError: TYPE_CHECKING = False`, never unconditional | C.10, D.6 |
| 14.4 | A structurally-used caller-supplied object gets a `Protocol` declared fully inside `if TYPE_CHECKING:` | C.10 |
| 14.5 | **No `# type: ignore[method-assign]` in `src/`** — `scripts/lint.sh` fails the gate on one | CLAUDE.md |
| 14.6 | ruff clean under the repo's `E`/`F`/`W`/`I`/`UP`/`B` selection — which the legacy file's `if self.debug: print(...)` one-liners and its `else:`-after-`return` already violate | CLAUDE.md |
| 14.7 | `scripts/lint.sh`, `scripts/typecheck.sh` and `scripts/test.sh` are actually run and their output read after every change, and the finding count diffed against the untouched baseline | D.14 |

## 15. Testing

| # | Requirement | Source |
|---|---|---|
| 15.1 | Tests are written **first**, against the criteria this scope settles, then the implementation is written against them | CLAUDE.md step-session workflow |
| 15.2 | Tests run under the real MicroPython Unix-port interpreter via `tests/microtest.py`, never pytest/CPython | E.1, E.2 |
| 15.3 | Mocking boundary is the raw `machine.UART` transaction only — real framing, CRC, locking and error paths all execute | E.4 |
| 15.4 | **The loopback model is a required, tested property**: one Python instance as initiator and one as responder must interoperate perfectly, modelled per direction at the `machine.UART` level, in both `tests/machine.py` and `digital_twin/machine.py` (which has no `UART` at all today) | J.7 |
| 15.5 | Byte-stream fault injection coverage: dropped and corrupted bytes, mid-frame truncation, injected noise, delayed delivery, stalled TX readiness, short writes, duplicated frames, receive-buffer overrun, one-sided silence | J.7 |
| 15.6 | **Any `uart.poller` test double must be a bounded fake like `_StepPoller`, never a real `select.poll()`** — the Unix port does not re-evaluate a Python object's `ioctl()` after registration, and this has already caused a CI-only infinite hang once | CLAUDE.md, J.7 |
| 15.7 | Protocol-specific coverage: each rejection rule independently (bad `CMD`, wrong chunk index, changed `CHUNKS`, bad `UID`, each `SIZE`-invariant position), the deferred final ACK, the empty-payload outcome as distinct from failure, `exp_size` don't-care/exactly-empty/exactly-N, the incremental and final size checks, and both recovery constants | J.4, J.5, D.12 |
| 15.8 | Memory coverage: a maximum-length train allocates nothing per frame, `LockableBuffer`-returns-`None` degrades cleanly, and the stress test passes under `gc.threshold(-1)` **before** being run with the project's chosen threshold | I.4(e), D.12 |
| 15.9 | Wedge coverage — the point of §6: a peer that never stops talking, a dropped write-gate callback, a peer that goes silent mid-train, a cancel arriving during each wait state. Every one must terminate | D.3, D.5 |
| 15.10 | Integration tests drive the real chain, not just the module in isolation, if it is wired into a variant's task graph | D.12 |
| 15.11 | No test may hang: the per-file `timeout`+retry and forced `sys.exit()` backstops stay in place | CLAUDE.md |
| 15.12 | **Comm-hazard coverage across the four tiers applies here too** (owner direction, 2026-09-11), as the UART-shaped analogue of C.8's standing bus-hazard rule — with one structural difference: a UART link has **exactly two participants, never more and never fewer**, so there is no multi-device interleaving or address-sweep dimension. What replaces each: (a) *same-instance concurrency* — two tasks initiating on one instance at once, and a `clear()`/`cancel_read_timeout()` racing an in-flight transaction, must serialize on the session lock or be refused, never corrupt a frame; (b) *both-participants-transmitting* — out of contract by design (no arbitration, J.2), so the test proves it is **detected and recovered from**, not that it works; (c) *frame/field sweep* — every `CMD`, `SIZE`, `CHUNKS`, `CUR_CHUNK` and `UID` value across its legal and illegal range, replacing the I2C address sweep | Owner direction, C.8 |
| 15.13 | Tier coverage: **mock** (byte-exact wire log of a two-instance exchange plus the field sweep), **twin** (two instances under genuine concurrent task load), **flash** (real hardware over dev's permanent UART0↔UART1 crossover jumper — `tests_hardware/flash/`), **bench** (the same link under full HTTP/API load). `tests_hardware/bus_topology.py` gains the UART link's declaration alongside its I2C/SPI ones | C.8, E.6.1 |
| 15.14 | **Hardware fault injection is in scope as future work, and the harness must not preclude it**: the two-participant model makes real injection possible (pull a line, invert it, inject noise, desync the baud rate) in a way a shared multi-drop bus does not. Structure the flash/bench tier so an injection adapter can be added without reshaping the tests, per E.6.2's capability-adapter pattern | Owner direction, E.6.2 |
| 15.15 | The real-hardware write-safety constraints still apply: no test may touch the RP2040's own flash filesystem, and if an instance's logger is FRAM-backed its writes count against the NVM budget — construct the module directly rather than through a variant's full task graph where that matters | C.8 |

## 16. Pipeline and wiring

| # | Requirement | Source |
|---|---|---|
| 16.1 | Lint/typecheck/test/firmware-build all discover `src/*.py` and `tests/test_*.py` by glob — no config change needed, but confirm rather than assume | D.13, D.14 |
| 16.2 | A digital-twin counterpart is **required, same session, not deferred**: a twin-side UART fake wired into `digital_twin/machine.py`, plus `tests/test_digital_twin_*.py` coverage | C.11 item 9, A.10 |
| 16.3 | If the module is wired into a variant: add it to that variant's `_collect_error_sources()` and `_collect_level_setters()` in `sensortask_*.py` — the level registry is per-*logger*, so a nested logger counts separately | A.7 |
| 16.4 | If wired, register it as an `error_sources=` module on `WebserverService`, satisfying `_ModuleLike` (`name`, `pr`, `get_error_counter()`, `reset_error_counter()`) | A.7, A.8 |
| 16.5 | **The website side is solved upstream of this module — the module's own obligation is to provide the means, identically to every other module that already does**: a `name` matching `self.pr.name`, `get_error_counter()` returning the shared `ErrorLog` envelope, and `reset_error_counter()`. Adding `{key, label}` to `html/definitions/<variant>.json`'s errcount list is then the wiring layer's job, one entry per instance (16.9), and the `src/`/`js/` mirror stays one change | Owner clarification, H.6, G.2 |
| 16.6 | A FRAM-backed logger consumes a chunk, and **`AsyFramManager` is a bump-pointer allocator — instantiation order is on-chip layout.** Both instances are therefore constructed **after** every existing dev module, appending to dev's chunk order rather than inserting into it; two FRAM-backed instances mean two new chunks | A.7, A.4 |
| 16.7 | The `UART` bus instance is constructed with a single-digit `poll_wait_ms` (12.6), and its pins avoid GPIO24/25 and GPIO28/29 — wireless-reserved on Pico W, and inside a UART pin-mux group, so either pair silently collides with WiFi | J.6, asy_uart_driver.py |
| 16.8 | After any merge touching `uv.lock`, re-verify the tool pins with `uv sync` + `ruff --version`/`mypy --version` — `uv lock --check` does not catch a merged-apart lock | CLAUDE.md |
| 16.9 | **The target variant is `dev`** (owner decision, 2026-09-11), wired as **two instances on one board** — one initiator on UART0, one responder on UART1 — across the bench rig's permanent TX↔RX crossover jumper (GP0↔GP9, GP1↔GP8), which exists for exactly this purpose. That makes J.7's self-compatibility property physically testable, not just modelled. Pin pairs: UART0 tx=GPIO0/rx=GPIO1, UART1 tx=GPIO8/rx=GPIO9 — clear of the wireless-reserved GPIO24/25 and GPIO28/29 groups (16.7) | Owner decision, J.7, `dev_legacy/README.md` |
| 16.10 | **UART0 on dev is mutually exclusive between the crossover jumper (GPIO0/1) and the BME688/BSEC coprocessor (GPIO16/17)** — one peripheral, one pin pair at a time. No BME688 driver exists in `src/`, so this costs nothing today, but it must be recorded where the dev wiring is declared rather than discovered later | `dev_legacy/README.md` |
| 16.11 | Two instances mean two entries everywhere the wiring enumerates modules: `_collect_error_sources()`, `_collect_level_setters()`, the webserver's `error_sources=` list, and the definitions file's errcount list. Each needs a distinct `name` (3.3b) | A.7, 16.5 |

## 17. Documentation obligations, same change

- `SPECIFICATION.md` Part J updated to describe the promoted module, not the legacy one.
- `SPECIFICATION.md` C.7.1's `errno`/`wrnno` table gains this module's row; C.3.2's "orphan module,
  no `self.pr` yet" note for `asy_uart_driver.py` is revisited once it has a real caller.
- `SPECIFICATION.md` Part G.2 gains any genuinely new reusable primitive introduced here.
- `UART_C_PORT_CHANGELOG.md` gains an entry per change, correctly classified, with each Class A
  entry's "verify in C" column filled in.
- `BACKLOG.md`'s `asy_uart_driver.py`-has-no-callers item is resolved and removed once it does.
- README.md's "Further reading" map lists this file while it exists, and stops listing it when it
  is deleted.
- `A.3 Refactor status` updated.

## 18. Legacy violation map

Line references are `python/IndividualDrivers/asy_uart_comm.py` as it stands today. This is the
"what actually has to change" view of §1-§14, not a second list of requirements.

| Lines | What it does | Requirements broken |
|---|---|---|
| 3 | `import math` for one `ceil()` on a float division | 11 (integer arithmetic), D.4 |
| 5 | imports the legacy `asy_uart.AsyUART` | 2.2 |
| 23 | untyped constructor, `debug=False`, no `fram`/`history_length`/`name`/`logger`/`role` | 3.1-3.4, 14.1 |
| 28, and ~30 sites | `self.debug` + `if self.debug: print(...)` | 4.1, 14.6 |
| 29, 45 | one-shot soft `Timer` as the write gate, `Timer.init()` unguarded | 6.2-6.4, 12.1, 12.2 |
| 42-44 | unbounded drain loop | 6.1 |
| 48-86 | `uart_listen()` falls off the end returning bare `None`; callbacks called bare and sync-only | 5.3-5.5, 5.7 |
| 59 | command ID taken from the payload without checking `SIZE == 1` | 13.3 (A12) |
| 95 | `del filled` — dead statement | D.11 |
| 100-101, 170-171 | `bytearray(1)` allocated per call for a single ID byte | 7.9 |
| 119, 139 | `res = bytearray()` grown by `+=` across the whole train | 7.5, 12.4 |
| 139 | `msg[a:b]` slice copy per chunk | 7.6 |
| 162 | `math.ceil(len(payload) / self.payload_size) + 1` | 11 |
| 164 | guard comment says "16bit payload field"; the field is 8-bit | D.1, D.11 |
| 184-185 | `payload[:size]` and `payload[size:]` — two allocations per chunk, O(n²) over a train | 7.6 |
| 190-199 | `_build_msg()` — three allocations per frame | 7.2 |
| 205 | `if not (msg[_MSG_CMD] & exp_cmd)` — bitmask, so `0x06`/`0x03` pass validation then match no dispatch branch | 13.3 (A1) |
| 208-217 | no `CHUNKS`-constancy check, no `UID` check on data chunks, no per-position `SIZE` invariant | 13.3 (A2, A3, A12) |
| 221 | `await self.enable_writing.wait()` — unbounded, set only by a droppable callback | 6.2 |
| 226, 253 | `read_until_complete()` — allocates a fresh frame buffer per read | 7.3 |
| 223, 264 | `device.write(msg)` — allocates a CRC-appended copy per write | 7.4 |
| 239-241 | `else:` after `return`; no `UID` check on a non-ACK reply | 14.6, 13.3 |
| 263 | ACK built through `_build_msg()`, allocating a fully padded frame per ACK | 7.2, 7.9 |
| (absent) | `name`, `get_error_counter()`, `reset_error_counter()`, `get_task_starters()`, `get_timer_starters()`, `setup()`, role gate, parameter validation | 3.6, 4.5, 9.1, 10.1-10.2, 8.6 |

## 19. Decisions

Settled by the project owner, 2026-09-11:

1. **Logger.** Both construction routes, exactly as `SensorReader.__init__` shapes them —
   `fram=`/`history_length=`/`debug=`/`name=` through `make_logger()`, or a `logger=` reach-through
   to an upstream instance's own, the way `AsyFramManager` hands `self.pr` down to `FRAM_SPI` and
   its chunks. Consequence: a shared logger is a shared numbering space (4.4a).
1a. **Base class** (delegated to this scope, resolved against precedent rather than by preference):
   plain class, not a `SensorReader` subclass — see 2.5-2.6b for the derivation. Every existing
   subclass is one for a measurement snapshot or a config schema; this module has neither, and
   `AsyFramManager` is its closest structural match. `_error_check()` is neither reimplemented nor
   needed: C.9's capped backoff is the primitive that fits a link fault, since there is no hardware
   to re-initialize on restart. **Reversible in one place** if a link-state snapshot is ever wanted
   as a real feature — that, not the base class, would be the decision that changes.
2. **FRAM backing.** Optional but always possible, exactly as project-wide — `fram=` selects
   `PrintLogHistoryStore`, omitting it selects `PrintLogHistory`, and `make_logger()` already makes
   that choice. Consequence: a FRAM-backed instance appends to dev's chunk order, never inserts
   into it (16.6).
3. **Target variant.** `dev`, wired as two instances across the bench rig's permanent UART0↔UART1
   crossover jumper (16.9-16.11).
4. **`errno`/`wrnno` numbering.** Aligned to the `SensorReader` reservation regardless of the base
   class — `errno` from 10, `wrnno` from 10 (4.4). Modules currently not aligned are recorded in
   BACKLOG.md as a separate fix, not corrected drive-by from this branch.
5. **Comm-hazard testing.** In scope across all four tiers, in the two-participant shape, with
   hardware fault injection as future work the harness must not preclude (15.12-15.15).
6. **Website.** Solved upstream; this module's obligation is to provide the same means every other
   module does (16.5).

7. **CRC/framing ownership** (changelog A11's open question): **`asy_uart_driver.py` gains a
   framing-codec concept** — "frame in, frame out" with a pluggable codec (none / COBS), CRC
   staying underneath it where it already lives. Not `UART_Comm` taking CRC ownership, and not a
   deferral. This is the largest consequence of this round: it makes A11 structurally possible,
   reusable by any future framed protocol, and it means a real extension to an already-promoted,
   already-tested file — see 20.1-20.6.
8. **`uart_listen()`'s return contract**: a **namedtuple**, not a bare three-tuple — call sites read
   `res.cmd_id` rather than `res[0]`, and every path returns it explicitly, including the
   currently-undefined fall-through. See 2.7 for why its allocation does not conflict with §7.
9. **`uart_get()`'s empty-payload result**: `None` means failure, a zero-length result means a
   genuinely empty payload — which the legacy code already does by accident, since it discards the
   internal `filled` flag. The `_into`/callback forms mirror it as `None` on failure vs. 0 bytes
   written. Nothing to build; it must be *documented as contract* and covered by a test that fails
   if the two ever collapse into one.
10. **The lost-final-ACK case**: folded into failure, as today — `uart_set()` returns `False`. A
    caller cannot act differently on "delivered but unconfirmed" than on "not delivered", this
    protocol has no retransmission to hang a third state off, and the application-level answer
    (re-issue, or ask) is the same either way.

## 20. Changes permitted in `asy_uart_driver.py`

Maximum buffer reuse may require reaching one layer down. That is allowed (owner direction,
2026-09-11) under one scheme and a few constraints.

**The scheme**: *an optional buffer argument; allocate internally only when the caller passes none.*
The two established shapes are `voc_algorithm.py`'s `vocalgorithm_proc_ser_des(sraw, buf=None, ...)`
and `asy_fram_manager.py`'s `write()`/`write_into()` pair — pick whichever fits the method, but
never invent a third.

**Most of it already exists** — check before adding anything: `readinto_until_complete()` is the
zero-allocation counterpart of `read_until_complete()`, `writefrom(buf, size)` of `write(msg)`, and
`readinto()` covers the drain path. Using these instead of their allocating siblings is §7's
requirement, not a driver change. Do not add a parallel API next to them.

**Required: the framing-codec concept** (owner decision, 2026-09-11 — §19.7). The driver learns
"frame in, frame out" with a pluggable codec, CRC keeping its current position underneath it:

- 20.1 The codec is a constructor-injected object with a `CRC_Base`-shaped contract — same family
  resemblance, so a dispatch table can treat every codec identically, and a pass-through codec is
  the default exactly as `CRC_Pass` is (D.10). A codec that does nothing must make every framing
  calculation degrade to today's fixed-size case automatically.
- 20.2 Write order is build → CRC → encode → delimiter; read order is the exact reverse. The codec
  therefore wraps the CRC, never replaces it, and `UART_Comm` stays CRC-agnostic as J.3 already
  requires.
- 20.3 **Every** read/write method gets the same treatment, not just the ones COBS needs — D.10
  applies hardest here, and a half-codec'd API is a worse outcome than none.
- 20.4 The codec's own buffers follow §20's optional-buffer scheme. Encoding is not in-place
  (COBS output is longer than its input), so the worst case is one extra buffer per direction,
  sized once from `payload_size` and owned long-lived, never per frame.
- 20.5 A read framed by a delimiter is **length-unknown until the delimiter arrives**, which is a
  different read loop from `read_until_complete()`'s known-`nbytes` one — it needs its own bound
  (a maximum frame length) so a peer that never sends a delimiter cannot wedge it (§6.1's rule,
  applied one layer down).
- 20.6 The codec mechanism itself is Class B (no wire effect while the pass-through codec is
  selected). **Selecting COBS is Class A and a flag day** — changelog A11, whose "open design
  question" this answer closes.

**Candidate gaps this scan found beyond the codec**, none yet confirmed as blocking:

- `_write_all()` re-slices `memoryview(buf)[sent:]` on every retry round, allocating a memoryview
  object per iteration. Only matters on a short-writing link; an offset-carrying inner write would
  avoid it.
- `read()`/`readline()` allocate a fresh `bytes` per call and have no `_into` counterpart for the
  unbounded-length case. The bounded drain path does not need one (`readinto()` exists), so this is
  only a gap if the drain ends up wanting "read whatever is there" semantics.
- There is no way to suppress CRC handling for a single call. Nothing needs this today; §19.7's COBS
  question would.

**Constraints on touching it**:

- It is already promoted, reviewed and tested. Every existing `tests/test_asy_uart_driver.py` test
  must still pass unchanged, and any new parameter gets its own coverage in that same file.
- D.10 applies hardest here: give every member of the related set the same shape. A `buf=` parameter
  added to one read method and not its siblings is a worse outcome than not adding it at all.
- The never-raise sentinel contract (C.3.2) holds for anything added — including the new
  allocation, which degrades to the method's existing sentinel rather than propagating a
  `MemoryError`.
- A driver change is Class B in `UART_C_PORT_CHANGELOG.md` (no wire effect) unless it changes
  emitted bytes, in which case it is Class A with a stated flag-day consequence.
- `asy_uart_driver.py` currently has no logger of its own (C.7.1's table says so explicitly). If a
  new failure mode needs reporting, it returns a sentinel for its caller to log — the
  silent-failure-masking convention `deinit()` already follows — rather than growing a `self.pr`.

## 21. Done criteria

The branch is done when all of the following hold, each verified by running it rather than by
inspection:

- `scripts/lint.sh`, `scripts/typecheck.sh` (all three passes) and `scripts/test.sh` exit 0 with
  zero findings, and the finding count on untouched files is unchanged.
- Every §15 test tier exists and passes, loopback and fault injection included, under the real
  MicroPython Unix-port interpreter; the flash/bench comm-hazard tiers run clean on the dev bench
  over the real crossover jumper, under the project owner's own go-ahead.
- §18's table is fully struck through — every listed violation actually fixed, not deferred.
- §19's four remaining open questions (7-10) are answered and reflected in the code.
- `SPECIFICATION.md`, `UART_C_PORT_CHANGELOG.md`, `BACKLOG.md` and README.md's doc map are updated
  in the same change set.
- A bird's-eye scan across the whole of `src/` has been re-run after the file lands, covering Part
  D's checklist and Part G's catalog, with any cross-file discrepancy **reported and discussed, not
  silently fixed**.
- The file reads as if it had always been part of `src/` (§0).
