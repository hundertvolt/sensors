# SPI driver promotion playbook (prep doc — delete once consumed)

Written at the end of the `asy_i2c_driver.py` → `src/` promotion session (PR #7, branch
`claude/i2c-driver-quality-review-f8v3j1`), for a **future, separate session** that does the same
promotion for `improved-quality/asy_spi_driver.py`. The project owner asked for "the same steps,
the same test depth, the same auditing, the same structure, the same reliability, the same idea"
— this file is the exhaustive record of what those actually were, plus the SPI-specific
translation notes so the new session doesn't have to rediscover them from scratch or blindly copy
an I2C answer that doesn't actually transfer.

**This is scratch/prep material, not a permanent doc.** Once the SPI review's findings are folded
into `BACKLOG.md` and the file has moved to `src/`, delete this file (as part of the SPI PR or a
quick follow-up commit).

**Do this work on its own fresh branch/PR** — do not stack it onto PR #7 or touch
`src/asy_i2c_driver.py`, `tests/test_asy_i2c_driver.py`, or `tests/base_classes.py` except as
explicitly noted below.

---

## 0. Required reading before starting

In this order:

1. `CLAUDE.md` in full (hard rules, working agreements, code-quality tooling section).
2. `src/README.md` in full — the canonical checklist. This playbook does not replace it or
   restate it; it only adds SPI-specific translation notes for each section. Apply the checklist
   itself as written, section by section.
3. `BACKLOG.md`:
   - lines ~124–145: the mocking-boundary plan, which explicitly names `asy_spi_driver.py`'s
     future promotion and says to extend `tests/machine.py`, not build a second mock.
   - lines ~157–238: "Bus/sensor error-recovery robustness" — several bullets are SPI-specific
     (`extra_clocks`, "FRAM's SPI bus gets the same bus-recovery treatment", the lock-coverage
     audit item that already cites `SPIDevice`).
   - lines ~411–567: the full `asy_i2c_driver.py` findings entry from this session. This is the
     level of detail and rigor to match for the SPI entry — not a summary, a comparable
     blow-by-blow.
4. The finished reference implementation and its test suite — these are the concrete "same
   structure, same depth" bar, not just a description of one:
   - `src/asy_i2c_driver.py`
   - `tests/test_asy_i2c_driver.py` (77 tests)
   - `tests/machine.py` (the fake `machine` module — extend this, don't replace it)
   - `tests/base_classes.py` (temporary `Lockable` stand-in)
   - `tests/README.md` (documents the mocking-boundary pattern; already says to extend
     `tests/machine.py` with a fake `SPI` class for this exact promotion)
5. Both real SPI driver files, side by side, the same way the I2C review compared legacy vs. WIP:
   - `improved-quality/asy_spi_driver.py` (current WIP target of this promotion)
   - `python/IndividualDrivers/asy_spi_driver.py` (legacy, for correctness cross-checking only —
     do not edit)
6. **Every real caller**, end-to-end: `improved-quality/asy_fram_driver.py` (the only current
   `SPIDevice` consumer) and `improved-quality/asy_fram_manager.py` for context. See section 2
   below for why this matters more here than it did for I2C.
7. PR #7 itself (`hundertvolt/sensors`, branch `claude/i2c-driver-quality-review-f8v3j1`) — the
   actual commit history/diffs/PR description, as a concrete example of the expected shape and
   commit-message style, in addition to what's summarized here.

## 1. Methodology that must carry over unchanged

This is the actual working process used for I2C, distilled. Apply it identically:

- **Understand before judging.** Read the function alongside its callers and existing comments
  first (`src/README.md` section 0). If intent is genuinely unclear, ask up to 10 targeted
  clarifying questions — don't guess, don't over-ask either.
- **Verify every API claim against current documentation/source, never training memory, and never
  by assuming an I2C finding transfers to SPI unchecked.** `docs.micropython.org` direct fetches
  got 403'd during the I2C session; `raw.githubusercontent.com` fetches of the RST doc sources and
  of `ports/rp2/machine_*.c` worked instead — use the same fallback if the same block happens
  again. Concretely, research fresh for SPI (do not assume I2C's answers):
  - `machine.SPI`'s real constructor signature, `deinit()` behavior, and the exact return-value
    semantics of `write()`/`readinto()`/`write_readinto()` (does `readinto()` actually return a
    byte count, or always `None`? does `write_readinto()` require equal-length buffers, or
    truncate, or raise, or something undefined, on a mismatch?).
  - Real RP2040 SPI `OSError` conditions via `ports/rp2/machine_spi.c` — do **not** assume the
    I2C pair (`EIO` for NAK/fault, `ETIMEDOUT` for bus-busy/clock-stretch) applies unchanged; SPI
    has no ACK concept and no clock-stretch concept, so the actual fault surface is probably
    different. Confirm from source, the same way the I2C errno pair was confirmed rather than
    guessed.
  - Whether `configure()`'s comment ("micropython build for rp2 does not recognize pins keyword")
    and its `type: ignore[call-arg]` are still accurate on the current pinned target
    (`toolchain/versions.toml`'s `[micropython] ref`) — `src/README.md` section 9's "check against
    current MicroPython, not the version this code predates" applies here directly.
- **Never silently fix a discrepancy between code and documented/legacy behavior — flag it and ask
  first**, same as the `wet_bulb_temperature` humidity-bound precedent in `src/README.md` section
  1.
- **Never silently apply a behavior change** — every decision point in section 5 below needs its
  own `AskUserQuestion`, answered fresh for SPI, not inherited from the I2C session's answers.
- **Build tests first, then refactor, then verify green throughout** — this was an explicit,
  emphatic instruction for I2C ("do NOT apply refactor suggestions until tests are built and
  passing"), and it produced real bugs found before the refactor changed anything. Apply the same
  order for SPI, not tests-after-the-fact.
- **In-function comments: at most 3 lines, concise, only the non-obvious "why."** This rule was
  retrofitted onto `asy_i2c_driver.py` at the very end of the I2C session because the comments had
  grown to 6–14 lines in places. Apply it from the start for SPI — don't write verbose
  rationale-dump comments and trim them later; write the 3-line version the first time.
- Comments are `#`, never docstrings, on individual functions; state the shared contract once at
  module level (`src/README.md` section 11).
- **Final gate: an explicit paragraph-by-paragraph validation against every numbered section of
  `src/README.md`**, producing a verdict summary — not just "looks done."
- **Run `scripts/lint.sh`, `scripts/typecheck.sh src tests`, `scripts/test.sh` after every
  substantive change**, and diff the `improved-quality/` finding count against the pre-change
  baseline (320 as of this session's end — re-check the current count at the start of the SPI
  session, it may have drifted) to prove no regression on untouched files (`src/README.md` section
  14).
- **Bird's-eye scan over the whole of `src/`** once `asy_spi_driver.py` lands there too
  (`CLAUDE.md`'s hard rule) — check cross-file consistency against `asy_i2c_driver.py`,
  `math_helpers.py`, `crc_checks.py`. **If the scan surfaces a discrepancy, report it and discuss
  before changing anything** — don't silently fix it (same "flag, don't silently change"
  treatment as section 1's formula-discrepancy rule, applied to cross-file consistency).
- **Draft PR, immediately subscribe to its activity, meaningful description mirroring any PR
  template, then periodic ~hourly check-ins via `send_later`** until merged/closed. This is a
  standing `CLAUDE.md` rule already, not new for SPI.

### Facts already confirmed empirically this session — reusable directly, no need to re-derive

These are protocol-agnostic MicroPython/asyncio facts, verified against the real interpreter
during the I2C session. They apply equally to SPI work without re-checking:

- `asyncio.Lock`: double-release raises `RuntimeError: Lock not acquired`; reentrant acquisition
  on the same task deadlocks (not reentrant); `asyncio.wait_for` exists and raises `TimeoutError`
  on timeout, and the lock is still left in a correct state afterward.
- Task cancellation while holding a lock inside `async with` still runs `__aexit__` via
  `CancelledError` propagating through the block — same as CPython. This is directly relevant to
  confirming `SPIDevice.__aexit__`'s CS-pin-deassert step still runs under cancellation (see
  section 4 below — this is a stronger requirement for SPI than it was for I2C).
- `memoryview` slicing clamps gracefully for any out-of-range start/end — never raises.
- The MicroPython Unix port's own `machine` module has **no** `I2C`/`SPI`/real `Pin` — only
  `PinBase`/`Signal`/`mem8`/`mem16`/`mem32`/`idle`/`time_pulse_us`. This is exactly why
  `tests/machine.py` exists and must be extended (not bypassed) for SPI.
- `scripts/test.sh` requires `MICROPYPATH="src:tests:.frozen"` — `.frozen` must stay in the path
  or `import asyncio` breaks with no clear error, since `MICROPYPATH` replaces the interpreter's
  default `sys.path` rather than extending it. Already fixed in `scripts/test.sh`; nothing to do,
  just know why if something async fails to import.
- `typing` is not an importable module at all on the real Unix-port test interpreter. Guard any
  typing-only construct (`TypeVar`, `Protocol`, `TracebackType`, etc.) behind
  `if TYPE_CHECKING: ... try/except ImportError: TYPE_CHECKING = False`, per `src/README.md`
  section 6. Plain `X | None` annotations don't need this (never evaluated at runtime).

## 2. Known structural differences from I2C — do not assume anything transfers 1:1

| | I2C | SPI |
|---|---|---|
| Addressing | 7-bit device address + hardware ACK/NAK | No addressing; per-device CS pin instead |
| "Is a device present" | `I2CDevice.setup(probe=True)` does a real zero-byte-write ACK probe | No ACK concept exists at this layer — there is no equivalent probe possible |
| Base class | `I2CDevice(Lockable)` — subclasses the shared lock/aenter/aexit base | `SPIDevice` currently **hand-rolls** its own `__aenter__`/`__aexit__` instead of subclassing `Lockable` |
| Register-level helpers | `get_bits`/`set_bits`/`get_register_struct`/`set_register_struct` | None — and none should be invented; SPI has no register/bit-field concept at the bus-driver layer, it's a raw byte stream |
| Real production callers today | Effectively zero (only the not-yet-migrated `asy_isl29125_driver.py` uses the register helpers) | **`asy_fram_driver.py` actively uses `SPIDevice` today**, three real call sites (`write()`, `readinto()`, `write_readinto()`) across a multi-step read and a 3-transaction write sequence |
| Fault detectability | Real bus fault → `OSError` (NAK/timeout), confirmed via source | Largely unresearched — SPI has no ACK, so many "wire disconnected" scenarios may be silently undetectable at this layer (garbage data in, no exception) rather than surfacing as `OSError` at all — **research this before writing "irregular condition" tests that assume an exception where none may occur** |

Specific consequences to work through explicitly, not gloss over:

- **`SPIDevice` vs. `Lockable`**: `improved-quality/base_classes.py`'s `Lockable.__aenter__`/
  `__aexit__` (lines 16–39) do exactly the acquire/release-with-`RuntimeError`-swallow that
  `SPIDevice`'s own hand-rolled `__aenter__`/`__aexit__` already duplicate. This is the same kind
  of API-consistency finding (`src/README.md` section 10) that shaped several I2C fixes, but it's
  a **bigger structural change** than anything done to `I2CDevice` (which already subclassed
  `Lockable` from day one — nothing had to change there). Converting `SPIDevice` to
  `class SPIDevice(Lockable)` would mean overriding `__aenter__`/`__aexit__` to call
  `await super().__aenter__()` / `return await super().__aexit__(...)` around the extra
  CS-pin/`configure()` logic. **Raise this explicitly as an `AskUserQuestion`, not an assumed
  yes** — lay out the tradeoff (more consistent, less duplicated logic, vs. a real shape change to
  a class with live production callers).
- **`configure()`'s `RuntimeError`**: `if self._spi is not None and self.async_lock.locked(): ...
  else: raise RuntimeError("First acquire async lock!")` is a real, uncaught raise from what looks
  like an operational path — unlike I2C's fully-None-sentinel operational contract
  (`src/README.md` section 2). Work out whether this is (a) a programmer-error guard against
  calling `configure()` outside `async with device:` — which might deserve its own carve-out
  reasoning distinct from both the "one-time setup can raise" and "operational calls never raise"
  categories already established — or (b) something that should become a no-op/`None` return like
  everything else. **Flag and ask — don't assume either existing precedent applies unmodified.**
- **`extra_clocks`**: legacy `python/IndividualDrivers/asy_spi_driver.py`'s `SPIDevice` docstring
  mentions an `extra_clocks` parameter ("cycle the bus after CS deassert", used for SD cards — see
  `BACKLOG.md`'s bus-recovery section) but it was **never actually implemented** as a real
  constructor parameter even in legacy code — pure aspirational documentation. `improved-quality/`
  dropped even the docstring mention. This is not a live regression to fix; it's flagged in
  `BACKLOG.md` as an example bus-recovery mechanism worth extending consistently during the
  eventual full refactor, not during this quality-promotion pass. **Don't resurrect it without
  asking first** even if it seems like low-hanging fruit — this promotion changes shape/quality,
  not features (same constraint the I2C session held to throughout: every new parameter added was
  a pre-existing `machine.SPI`/`machine.I2C` capability exposed as a no-op default, never a new
  feature).
- **No register/bit-field/struct helpers**: don't invent SPI equivalents of `get_bits`/
  `set_bits`/`get_register_struct`/`set_register_struct`. SPI's actual shape at this layer is
  simpler — raw `write`/`readinto`/`write_readinto` only. Don't force I2C's shape onto it.

## 3. Specific known findings already visible in the current file — verify each empirically before fixing

Do not port the I2C fix blindly; each of these needs its own confirmation against real SPI
behavior/docs, per section 1's methodology, even where the shape of the finding looks identical:

- **`deinit()`**: unlike I2C's original bug (never called the real `machine.I2C.deinit()` at
  all), SPI's `deinit()` already calls the real `self._spi.deinit()`. It still wraps the whole
  thing in `try: ... except AttributeError: pass`. The I2C review's own finding entry
  (`BACKLOG.md` ~line 418–423) already predicted this exact SPI cleanup: a bound method on a real
  `machine.SPI` object doesn't raise `AttributeError`. **Confirm this empirically for
  `machine.SPI` specifically** (don't just cite the I2C finding as sufficient) before removing the
  `except AttributeError`.
- **Old `u`-prefixed import**: `from uasyncio import Lock` alongside a redundant top-level
  `import asyncio` — same fix pattern as I2C: consolidate to `asyncio.Lock()`, drop the
  `uasyncio` import (`src/README.md` section 9).
- **Typing imports**: `from typing import Type`, unconditional, plus a bare
  `try: from types import TracebackType except Exception: pass` that swallows everything. Both
  need the `if TYPE_CHECKING:` guard pattern (section 6, `tests/test_crc_checks.py`'s precedent)
  instead of a runtime `try/except`. `typing`'s unavailability was already confirmed empirically
  this session; **`types.TracebackType`'s availability was not checked** (the I2C file ended up
  needing no typing import at all, so this was never exercised) — confirm it directly against the
  real interpreter before deciding the guard's exact shape.
- **`configure()`'s workaround comment/`type: ignore[call-arg]`**: verify against current
  `machine.SPI.init()` docs/source whether the "pins keyword not recognized" workaround is still
  needed on the current pinned target (`src/README.md` section 9).
- **`write()`/`readinto()`/`write_readinto()` return values when `self._spi is None`**: already
  return `None` for the uninitialized-bus case, matching the convention I2C was fixed to use — but
  `readinto()`'s declared return type is `int | None`, forwarding `self._spi.readinto(...)`'s
  return value directly. **Check current `machine.SPI.readinto()` docs for what it actually
  returns** — if it's always `None` (in-place operation, no natural "bytes read" count the way
  I2C's ACK-based transaction has), the `int` half of that union may be dead/wrong and should be
  corrected, not left as an untested assumption.
- **`write_readinto()` buffer-length validation**: no check at all today for
  `buffer_out`/`buffer_in` length compatibility. Research `machine.SPI.write_readinto()`'s actual
  behavior for mismatched lengths (raise? truncate to the shorter? require equal length and behave
  undefined otherwise?) and decide whether a guard belongs here — this is the SPI-specific
  instance of `src/README.md` section 1's "look specifically for functions with no validity range
  check at all" gap-finding pattern that caught `get_bits`/`set_bits` for I2C.
- **No `timeout` parameter on `SPI.__init__`/`init()`**: `machine.I2C`'s constructor has one
  (clock-stretch/bus-busy); check current `machine.SPI` docs for whether a real
  timeout-equivalent parameter exists at all — SPI has no inherent stretch/timeout concept the way
  I2C does, so there may genuinely be nothing to add here. Confirm rather than assume based on the
  I2C precedent (don't add a parameter that doesn't correspond to anything real).
- **`configure()` runs on every single `__aenter__`**: `SPIDevice.__aenter__` calls
  `self.spi.configure(...)` unconditionally on every transaction, even if the bus is already
  configured identically from the previous one. Worth evaluating as part of the "is this
  efficient?" architecture-review pass (`src/README.md` sections 4/8) — matches the same kind of
  question asked and answered for the I2C file's own shape/efficiency review.

## 4. Test depth required — same breadth as I2C's 77 tests, translated to SPI's actual protocol shape

The project owner's literal requirement for I2C (reproduce this list, adapted):

- Single- and multi-session transfers.
- Asyncio interlock/parallelism of two or more concurrent bus requests — reuse the
  `asyncio.gather` + `max_concurrent`-counter pattern from `tests/test_asy_i2c_driver.py` directly,
  it's protocol-agnostic.
- Interrupted transfers: both raised exceptions mid-transaction and real task cancellation —
  confirm `__aexit__` (lock release **and** CS-pin deassert) still runs via `CancelledError`
  propagating through `async with`, reusing the fact already confirmed for `asyncio.Lock` this
  session. **SPI-specific addition, no I2C equivalent**: explicitly assert the CS pin returns to
  its inactive value on every one of these exit paths (normal, exception, double-exit/pre-released
  lock, cancellation) — a stuck-asserted CS is a bus-wide fault affecting every other device on
  the bus, which I2C has no equivalent failure mode for (I2C has no chip-select concept at all).
- Regular bus conditions specific to SPI: CS assert/deassert sequencing and the
  `asyncio.sleep(0.001)` settle delays around it, `configure()` being (re)applied per transaction,
  deinit/reinit mid-session, double-deinit idempotency.
- Irregular bus conditions: **model only what's actually detectable** — research first (section 1
  above). Most likely shape: `OSError` injection on `write`/`readinto`/`write_readinto` at each
  step of a multi-step operation, mirroring `asy_fram_driver.py`'s real WREN / WRITE-address+data /
  WRDI three-transaction write sequence, so a fault partway through that sequence is exercised the
  way a real caller would hit it. If SPI genuinely cannot detect a disconnected-wire scenario at
  this layer (no ACK), **document why rather than writing a test that asserts an exception that
  can't actually occur** — an untestable/misleading test is worse than no test.
- Both successful and unsuccessful transfers for every method.
- Bus shutdown/reset handled well.
- Deep asyncio context-manager behavior: `__aenter__`/`__aexit__` under every condition — normal,
  exception inside the block, double-exit/pre-released lock, reentrant acquisition (deadlock
  bounded by `asyncio.wait_for`, confirmed pattern from I2C), cancellation while holding the lock.
- Valid and invalid function call parameters.
- Buffer size mismatches, especially too-small buffers — particularly `write_readinto`'s two-buffer
  interaction (see section 3 above for the open research question this depends on).

### Mock: extend `tests/machine.py`, don't replace it

`BACKLOG.md` already states this explicitly: *"`asy_spi_driver.py`'s own future `src/` promotion
should extend this same file with a fake `SPI` class rather than inventing a second,
differently-shaped mock."*

- Add `class SPI` alongside the existing `class I2C`/`class Pin` in `tests/machine.py`. Reuse the
  same fault-injection shape (`inject_fault(op, exc, times=)`, a call `log`, a `busy` flag) for
  consistency.
- Unlike I2C's register-dict store (`registers: dict[(address, reg_addr), bytearray]`), SPI has no
  addressing — model something like a configurable next-read-data queue so a test can prime what
  `readinto()`/`write_readinto()` "receives" from the simulated downstream device.
- If the CS-pin-deassert assertions above need it, extend `Pin` to support a readable `.value()`
  state (currently `Pin` in `tests/machine.py` is I2C's minimal SCL/SDA stand-in with no readback)
  — check what real `machine.Pin.value()` returns/accepts first.
- Add `tests/test_asy_spi_driver.py` mirroring `tests/test_asy_i2c_driver.py`'s structure and
  helpers (a `run(coro)` wrapper, a `make_spi()`/`make_device()` factory, a `fake()` accessor into
  the mock).
- `tests/base_classes.py` needs no changes unless section 2's `SPIDevice`/`Lockable` question is
  answered "yes" — if it is, the existing stand-in is reusable as-is (it's already what
  `I2CDevice` uses).

## 5. Decision points to raise fresh with `AskUserQuestion` — do not assume the I2C answers apply

For each, the I2C session's answer is noted for context, but **ask again for SPI** — several may
land differently given `SPIDevice`'s live production caller:

1. **Dead `except AttributeError` around `deinit()`** — I2C: fixed without much debate (this is
   actually a new-for-I2C fix that SPI's `deinit()` already partially avoided by calling the real
   method; only the leftover except clause needs removing here). Likely the same low-stakes "yes,
   remove it" answer, but confirm.
2. **Mocking boundary** — already a standing, previously-decided plan (`BACKLOG.md`); just execute
   it by extending `tests/machine.py`. No need to re-ask.
3. **None-sentinel vs. some other convention for operational (non-hardware) failures** — I2C:
   "switch to `None` sentinel, track that upstream callers need to handle it as a follow-up
   backlog item since nothing called those code paths yet." **Re-ask for SPI explicitly, because
   `SPIDevice` has real callers today** — if the answer is still "yes, `None`," the three
   `asy_fram_driver.py` call sites (`write()`, `readinto()`, `write_readinto()`, currently around
   lines 51–141) must be checked and, if needed, fixed **in this same session**, not deferred to a
   future pass the way I2C's zero-caller methods could be.
4. **OSError-propagation carve-out for raw bus-transaction calls** — I2C: "let it propagate,"
   already generalized into `src/README.md` section 2 to name `machine.SPI` explicitly, so this is
   very likely the same answer. Still explicitly verify (not assume) that
   `asy_fram_driver.py`'s own `try/except` already closes the gap for every `SPIDevice` call site
   — this is precisely the "verify, don't assume every upstream caller closes the gap"
   requirement `src/README.md` section 2 now states in general terms; this is its first concrete
   application to a file with a real caller to check.
5. **New for SPI**: whether to refactor `SPIDevice` to subclass `Lockable` (section 2 above) — lay
   out the tradeoff, don't assume yes just because it would look more consistent with `I2CDevice`.
6. **New for SPI**: whether `configure()`'s `RuntimeError`-on-unlocked-call path should change
   shape at all, stay as-is, or get its own documented carve-out category (section 2 above).

## 6. Order of operations (mirror exactly what happened for I2C)

1. Understand the current file, its legacy equivalent, and every real caller
   (`asy_fram_driver.py`) end-to-end; ask clarifying questions if intent is genuinely unclear.
2. Research current `machine.SPI` docs/source fresh; note every discrepancy from existing
   comments/assumptions in the WIP file.
3. Propose findings/fixes (correctness, exception-safety, typing, consistency) as suggestions;
   get explicit sign-off via `AskUserQuestion` on every behavior-changing item (section 5) before
   applying anything.
4. Build/extend `tests/machine.py`'s fake `SPI` first.
5. Write the full test suite (section 4) — build it before refactoring, per the explicit
   instruction this pattern is based on; confirm it's genuinely exercising both current and
   agreed-fixed behavior as directed once fixes are scoped.
6. Apply the agreed fixes/refactor with tests genuinely green throughout, not just at the end —
   re-run after each meaningful change, not once at the finish.
7. Run the architecture-review pass: "is this file in good shape / complete / reasonable /
   efficient / anything missing or badly implemented?" — the same open-ended review pass applied
   to I2C after its mechanical fixes landed.
8. Do the final, explicit paragraph-by-paragraph validation against every `src/README.md` section,
   producing a verdict summary table before considering the file done.
9. Do the bird's-eye scan over the whole of `src/` once the file actually lands there (`CLAUDE.md`
   hard rule) — flag, don't silently fix, any cross-file discrepancy found.
10. Update `BACKLOG.md` with a new finding entry matching the depth of the existing
    `asy_i2c_driver.py` entry (`BACKLOG.md` lines ~411–567).
11. Run `scripts/lint.sh`, `scripts/typecheck.sh src tests`, `scripts/test.sh`; confirm the
    `improved-quality/` finding-count diff against the pre-change baseline for files this work
    didn't touch.
12. `git mv` into `src/`, commit, push to a fresh branch, open a draft PR with a full description
    (check for a PR template first), subscribe to its activity, and begin the same ~hourly
    check-in cadence used for PR #7 until merged/closed.
13. Delete this playbook file once its content has been folded into `BACKLOG.md` and the promotion
    is complete.

## 7. Explicit non-goals / guardrails

- Don't touch `src/asy_i2c_driver.py`, `tests/test_asy_i2c_driver.py`, or `tests/base_classes.py`
  except to extend `tests/machine.py` itself (additive only — add `class SPI`, don't restructure
  the existing `class I2C`/`class Pin`).
- Don't implement `extra_clocks` or any other new feature — this is a quality/shape promotion,
  not a feature addition. Every parameter the I2C session added was a pre-existing
  `machine.I2C` capability exposed as a no-op default (`timeout`, `addrsize`); hold SPI to the
  same constraint — only surface what `machine.SPI` itself already provides.
- Don't edit `asy_fram_driver.py`'s or `asy_fram_manager.py`'s own logic beyond what's strictly
  required to keep them correct against an agreed `SPIDevice` signature/behavior change (e.g. a
  `None`-check the driver needs to add if decision point 3 lands on widening a return type) — that
  narrow follow-through is in scope; a wider refactor of those files is not.
- Don't restyle `python/CommonDrivers/microdot.py` or any other unrelated file.
- Keep this whole effort on its own fresh branch/PR, separate from PR #7.
