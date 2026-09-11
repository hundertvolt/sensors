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
| 2.5 | Whether it subclasses `SensorReader` is a real decision, not a default — see §19.1 | C.4.3, C.7 |

## 3. Construction contract

| # | Requirement | Source |
|---|---|---|
| 3.1 | Constructor parameter order follows the project convention: the bus handle first, then module-specific parameters, then `max_module_error` (if used), then `fram`, `history_length`, `debug`, `name`/`logger` | C.2 |
| 3.2 | `debug` is `int | None` (a log *level*), never the legacy `bool`. `self.debug` disappears entirely | C.7, print_log.py |
| 3.3 | Logger injection is supported both ways: construct one via `make_logger(fram, history_length, debug, name)`, **or** accept a caller-supplied `logger=` and reach through to it, exactly as `SensorReader.__init__` does | G.2, base_classes.py |
| 3.4 | `role` is a constructor parameter. It is not inferable and has no safe default that suits both ends | J.2 |
| 3.5 | `__init__` is synchronous and allocates only: no `await`, no I/O, no bus touch. Anything needing an await goes in `async def setup()` behind the standard `self.initialized` gate | C.13 |
| 3.6 | `self.name` is set and equals `self.pr.name` — the `_ModuleLike` registration shape the webserver keys on | asy_webserver_service.py, captive_dns.py |

## 4. Logging, counters and observability

| # | Requirement | Source |
|---|---|---|
| 4.1 | **Every one of the ~30 `if self.debug: print(...)` sites is replaced by the injected logger.** Trace/info → `pr.all()`/`pr.evt()`/`pr.one()`; anything that should count → `pr.err_s(..., errno=N)`/`pr.wrn_s(..., wrnno=N)` | C.7, G.2 |
| 4.2 | **No bespoke counter mechanism is added.** The `PrintLogHistory` error history *is* the protocol's diagnostic counter, surfaced through `/status`'s `errcount`, with optional FRAM backing — free, once the logger is in place | Owner direction, C.7 |
| 4.3 | `err_s`/`wrn_s` are **async**. A synchronous call site (a `Timer` callback, a sync validation helper) may only use the non-persisting `pr.err()`/`pr.wrn()`; if a hot path cannot afford the await, the failure is still recorded — it does not silently drop to `pr.all()` | print_log.py, system_service.py |
| 4.4 | The module gets its own `errno`/`wrnno` catalog, grouped by method, added to `SPECIFICATION.md` C.7.1's running table in the same change. The starting number depends on §19.1 | C.7 |
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
| 6.8 | If a long-running task is owned (responder listen loop), repeated failure escalates rather than spinning: either a bounded-retry shape or a consecutive-failure-streak give-up returning `False` so the task supervisor restarts it — and, in a sentinel-returning retry loop, a **capped exponential backoff**, since no `except` ever fires for a sentinel | C.9's cascading-recovery-storm convention, I.4(c) |
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
| 15.12 | Bus-hazard coverage across the four tiers is **not** triggered by this module — it is neither I2C nor SPI and shares no bus. State this explicitly rather than leaving it looking forgotten | C.8's standing rule |

## 16. Pipeline and wiring

| # | Requirement | Source |
|---|---|---|
| 16.1 | Lint/typecheck/test/firmware-build all discover `src/*.py` and `tests/test_*.py` by glob — no config change needed, but confirm rather than assume | D.13, D.14 |
| 16.2 | A digital-twin counterpart is **required, same session, not deferred**: a twin-side UART fake wired into `digital_twin/machine.py`, plus `tests/test_digital_twin_*.py` coverage | C.11 item 9, A.10 |
| 16.3 | If the module is wired into a variant: add it to that variant's `_collect_error_sources()` and `_collect_level_setters()` in `sensortask_*.py` — the level registry is per-*logger*, so a nested logger counts separately | A.7 |
| 16.4 | If wired, register it as an `error_sources=` module on `WebserverService`, satisfying `_ModuleLike` (`name`, `pr`, `get_error_counter()`, `reset_error_counter()`) | A.7, A.8 |
| 16.5 | If wired, add `{key, label}` to `html/definitions/<variant>.json`'s errcount module list and mirror it on the `js/` side — a `src/`-side change and its `js/` mirror are one change, not two. A module with no definitions entry stays invisible on the website indefinitely | H.6, G.2, C.11 item 9 |
| 16.6 | If the logger is FRAM-backed, it consumes a chunk, and **`AsyFramManager` is a bump-pointer allocator — instantiation order is on-chip layout.** It must be constructed last, or every deployed unit's persisted logs shift address and are invalidated | A.7, A.4 |
| 16.7 | The `UART` bus instance is constructed with a single-digit `poll_wait_ms` (12.6), and its pins avoid GPIO24/25 and GPIO28/29 — wireless-reserved on Pico W, and inside a UART pin-mux group, so either pair silently collides with WiFi | J.6, asy_uart_driver.py |
| 16.8 | After any merge touching `uv.lock`, re-verify the tool pins with `uv sync` + `ruff --version`/`mypy --version` — `uv lock --check` does not catch a merged-apart lock | CLAUDE.md |

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

## 19. Decisions still open

Blocking — the answer changes the module's structure, so it is needed before the tests are written:

1. **Base class.** Plain class with an injected `make_logger()` (the `captive_dns.DNSServer`/
   `SystemService` shape, `errno` numbering free to start at 1), or `SensorReader` subclass to reuse
   `_error_check()`'s consecutive-failure-streak give-up (which forces `errno` numbering to start at
   10 and drags in a measurement-data structure the module has no use for). `NotificationCoordinator`
   is the precedent for taking `SensorReader` for `_error_check()` alone — and for having to
   renumber when it collided with the reserved base range.
2. **Logger backing.** FRAM-backed (persists a link fault across a reboot, but consumes a chunk and
   must therefore be constructed **last**, per 16.6) or RAM-only (the `WebserverService` precedent —
   deliberately RAM-only to keep the seven-chunk order unchanged).
3. **Which variant, if any, wires it.** Neither `wozi` nor `dev` has a UART peer today. If none
   does yet, 16.3-16.5 are deferred with an explicit note rather than silently skipped — but the
   module then has no live caller, which is exactly the state `asy_uart_driver.py` is already in.

Non-blocking — needed before the affected code is written, not before the scope is settled:

4. **CRC ownership** (changelog A11's open question): `UART_Comm` takes CRC ownership with the bus
   driver configured `CRC_Pass`, or `asy_uart_driver.py` gains a framing-codec concept. Only forced
   if COBS framing is adopted; not to be decided implicitly.
5. **`uart_listen()`'s return contract** — the three-tuple's shape on every path, including the
   currently-undefined fall-through.
6. **`uart_get()`'s empty-payload result** — a genuinely empty payload is a distinct outcome from
   failure (J.4); the API must express that distinction.
7. **The lost-final-ACK case** — whether "sent, unconfirmed" is surfaced as its own outcome or
   folded into failure. It is a two-generals situation, so the honest answer may be a third state.

## 20. Done criteria

The branch is done when all of the following hold, each verified by running it rather than by
inspection:

- `scripts/lint.sh`, `scripts/typecheck.sh` (all three passes) and `scripts/test.sh` exit 0 with
  zero findings, and the finding count on untouched files is unchanged.
- Every §15 test tier exists and passes, loopback and fault injection included, under the real
  MicroPython Unix-port interpreter.
- §18's table is fully struck through — every listed violation actually fixed, not deferred.
- The three blocking decisions in §19 are answered by the project owner and reflected in the code.
- `SPECIFICATION.md`, `UART_C_PORT_CHANGELOG.md`, `BACKLOG.md` and README.md's doc map are updated
  in the same change set.
- A bird's-eye scan across the whole of `src/` has been re-run after the file lands, covering Part
  D's checklist and Part G's catalog, with any cross-file discrepancy **reported and discussed, not
  silently fixed**.
- The file reads as if it had always been part of `src/` (§0).
