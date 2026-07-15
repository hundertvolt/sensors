# src/

Files land here once they've cleared the full **production-quality** bar below — moved out of
`improved-quality/` (WIP refactor target, see CLAUDE.md) once they have. This checklist keeps
getting refined against whatever file is going through it next; apply the current version in full
to every file making the move, not just whichever ones already have. "Production quality" here
means concretely: correct against real documentation, never raises
an uncaught exception, safe to run unattended and uninterrupted indefinitely, respectful of the
RP2040's limited resources, never blocks, and always returns a well-defined value — each expanded
below.

Out of scope for this checklist: setting up the CI pipeline itself and the MicroPython Unix-port
toolchain build — that's already done (see BACKLOG.md/`toolchain/README.md`) and is a one-time
project-level setup, not something each new file redoes. What follows is what changes, and what
you check, per file.

## 0. Understand the function's purpose first

- [ ] Before judging correctness, be sure you actually understand what the function is *for* —
      read it alongside its callers, its existing comments, and any adjacent context, not in
      isolation. "It's mathematically consistent" isn't the same as "it does what it's meant to."
- [ ] If the intended purpose, expected input domain, or a caller's actual expectations are
      genuinely unclear after that, **ask up to 10 targeted clarifying questions** before
      proceeding — don't guess, and don't ask more than the ambiguity actually warrants. This is
      the same standing principle as CLAUDE.md's working agreement to flag genuinely ambiguous
      decisions rather than guess; the cap is there so "asking" doesn't become its own way of
      stalling.

## 1. Correctness, verified against real documentation

- [ ] Identify the authoritative source for every non-obvious claim the code makes or depends on
      — a published paper/standard for a formula, a hardware datasheet for a sensor's operating
      range, an external library's own docs/repo for how its API actually behaves — and verify
      against *current* sources (web search, the actual datasheet, the actual upstream repo),
      never training memory or "how it probably works." Note the source in a code comment.
- [ ] Verify the implementation actually matches that source (coefficients, sign, order of
      operations, argument order/units) — don't assume existing code is correct just because it's
      already deployed.
- [ ] **If verifying against the authoritative source surfaces a discrepancy — the code doesn't
      match the documented behavior/formula/range — do not silently change it to match.** Flag the
      specific discrepancy to the project owner and ask before altering anything that changes real
      output. (This is distinct from fixing an internal bug you introduced earlier in the very
      same review, e.g. a typo in a range you just added — that doesn't need the same round-trip.)
- [ ] Verify the coded validity range/domain matches the source's *actual* valid domain, not just
      whatever range the existing code happened to have. (Found a real bug this way:
      `wet_bulb_temperature`'s humidity lower bound was `0.5%`; Stull (2011) only validates down
      to `5%`.)
- [ ] Where the formula's own domain is wider than how it's actually used, cross-check against the
      real caller's hardware constraints instead (e.g. a sensor's datasheet operating range).
      (`altitude_baro`'s 300-1250 hPa / -40-85 degC range comes from the BMP388/390 datasheet, its
      only caller — not from the barometric formula itself, which has no such bound.)
- [ ] Look specifically for functions with **no validity range check at all** — an easy gap to
      miss since the function still "works" for any input right up until it's asked to
      extrapolate a formula miles outside where it was ever validated.
- [ ] If review surfaces an inherent quirk or non-ideality (not a bug) — e.g. two independently-
      fit formula branches that don't perfectly agree at their boundary — don't silently
      "fix" it by guessing new coefficients. Document it with a code comment and add a regression
      test with a tolerance matched to the *measured* behavior, not an idealized one.

## 2. No uncaught, unhandled exceptions

- [ ] Every function returns a clear "no data" sentinel (`None` here) — **never raises, under any
      input** — for:
  - missing input (`None`)
  - out-of-domain input, checked *before* any computation runs (guard clause, not a try/except)
  - any residual computational failure within the valid type contract (e.g. a near-boundary
    float edge case the range check didn't quite anticipate) — wrap only the actual computation
    in `try/except`, catching the *specific* exception types that can genuinely occur for that
    domain (`ValueError` for math domain errors, `ArithmeticError` for overflow/zero-division),
    never a bare `except:`.
- [ ] **Do not defend against out-of-contract input (wrong types) at runtime** if static typing
      already enforces the contract at every call site in CI (mypy here). That's dead weight on
      a resource-constrained target for a scenario that provably can't occur — scope defensive
      code to what the type contract actually allows through, not to "anything a Python caller
      could theoretically pass."
- [ ] Do explicitly verify `NaN`/`inf` — which *are* valid values within the type contract (still
      `float`) and which a real sensor fault could plausibly produce — degrade cleanly through
      the existing range checks. Don't assume; a naive range check usually already handles these
      correctly (a `NaN` comparison is always `False`), but confirm it and add a regression test.
- [ ] Confirm the exception net is complete: every `raise`-capable statement in the function body
      (arithmetic, indexing, attribute access, external calls) is inside a `try` that catches it,
      or is provably unreachable given the guard clauses above. Not "probably fine" — walk the
      function line by line and account for each one.
- [ ] **Specialty: raw hardware bus-transaction calls (`machine.I2C`/`machine.SPI` read/write/mem
      operations) are the one deliberate exception to "never raises."** A real transaction failure
      (`OSError` — NAK, timeout, device gone) is allowed to propagate uncaught out of a low-level
      bus driver, rather than being swallowed into a `None` sentinel here — this matches the
      legacy codebase's own existing pattern and is what every current Reader class (e.g.
      `asy_scd30_driver.py`'s `SCD30_Reader._read_scd`) already expects: it wraps a *whole*
      read/write sequence in its own `try/except Exception`, using the propagated exception itself
      to detect and count a real hardware failure. Silently returning `None` at the bus-driver
      layer instead would make that upstream detection invisible. This carve-out applies only to
      the actual bus-transaction call; a bus driver's own non-hardware failures (an uninitialized
      bus, a malformed caller-supplied format string) still get the normal `None`-sentinel
      treatment from the bullets above.
      **When reviewing a file that takes this carve-out, verify — don't assume — that every
      upstream caller of it actually closes the gap**: confirm each call site sits inside a
      `try/except` broad enough to catch what the low-level call can raise (typically `OSError`,
      but check the specific driver), so a real bus fault degrades to the caller's own error
      counting/self-healing path instead of ever reaching the top-level task supervisor and
      crashing the main loop. If a call site doesn't already do this, that's a real finding to fix
      or flag — don't take the carve-out as license to skip checking who actually catches it.

## 3. Stability for indefinite, unattended operation

These units run for years without a reboot (see CLAUDE.md/BACKLOG.md's "No leaks, no drift"). For
any file moving to `src/`:

- [ ] No unbounded growth: no list/dict/buffer that grows with each call and is never trimmed, no
      accumulating counters that assume they'll be reset externally without confirming they are.
- [ ] No retained state between calls unless the function is deliberately stateful and documented
      as such — prefer pure functions (like `math_helpers.py`'s) wherever the problem allows it;
      they can't leak or drift by construction.
- [ ] No resource acquisition (file handles, locks, bus transactions) without a guaranteed release
      on every exit path, including the exception paths from section 2.
- [ ] Verified via design discipline and code reading, not an automated soak test — there's no CI
      gate for "ran for a simulated year," so this has to be reasoned about directly per function.

## 4. Resource discipline for the RP2040 target

Dual-core Cortex-M0+ @ up to 133MHz, 264KB SRAM total (see CLAUDE.md's "Platform target") — this
is not a machine with memory or cycles to spare:

- [ ] Avoid unnecessary allocations in anything called frequently (new lists/dicts/strings per
      call add up under MicroPython's GC, and a GC pause is itself a mild blocking risk — see
      section 5). Reuse buffers where the existing codebase already has a pattern for it.
- [ ] Avoid recursion (limited stack) and large intermediate data structures — prefer the
      straight-line, fixed-size-working-set version of an algorithm over a more "elegant" one that
      needs more scratch space.
- [ ] Prefer the cheaper stdlib call where it's a drop-in equivalent (e.g. `math.sqrt(x)` over
      `math.pow(x, 0.5)` — faster and more numerically precise for a square root specifically).
- [ ] Don't add runtime type/shape checks "just in case" (see section 2's out-of-contract-input
      bullet) — every unnecessary branch and comparison is cycles spent on hardware that doesn't
      have cycles to spare.

## 5. Never block

- [ ] Confirm the function is non-blocking: no blocking I/O, no `time.sleep`, no unbounded loops.
      A pure computation like `math_helpers.py` is inherently safe here, but this must be checked
      explicitly for anything that isn't.
- [ ] If a function genuinely must do I/O or another long-running operation, it must be `async`
      and yield control appropriately — coordinate with `async_connect.py`'s
      `get_long_block_lock()` pattern (see CLAUDE.md's "Hard rules"), the project's standing
      convention for anything that could otherwise stall timing-sensitive work like the Neopixel
      animation. Never assume a one-off "it's probably fast enough."

## 6. Typing

- [ ] Type-hint every parameter and return value.
- [ ] Verify the annotation *syntax itself* is actually safe on the target runtime by checking
      *current* official docs — don't reason from general Python knowledge alone. (Confirmed via
      MicroPython's own docs that `X | None` annotations are parsed but never evaluated at
      runtime, on every version checked — so they're safe regardless of whether the runtime
      otherwise supports `X.__or__`/`UnionType`. This was a real open question on record before
      being checked, not something to assume either way.)
- [ ] "Reasonable" also means not over- or under-typing: no `Any` where a real type is knowable,
      no unnecessarily narrow type that will make legitimate future callers fight the checker.
- [ ] If a file needs typing-only utilities that aren't plain annotation syntax — `TypeVar`,
      `Protocol`, `Generic`, `overload`, `TYPE_CHECKING` itself, ... — guard the import behind
      `if TYPE_CHECKING:` with a `try/except ImportError: TYPE_CHECKING = False` fallback, rather
      than importing `typing` unconditionally. Confirmed directly: `typing` is not an importable
      module at all on the MicroPython Unix-port test interpreter (`tests/test_crc_checks.py`'s
      `run()` helper needed this guard to use `Coroutine`/`TypeVar` for its generic return type).
      Plain `X | None` annotations don't need this — the bullet above already established that
      annotation expressions are never evaluated at runtime, so names inside them don't need to
      resolve either — but a real runtime call like `TypeVar("T")` does. This is a live, present
      gap across much of `improved-quality/` too (most files there do an unconditional `from
      typing import ...`, untested against the real interpreter) — not something to fix
      opportunistically in unrelated files during an unrelated review, but the pattern every new
      `src/`/test file should use going forward.

## 7. Always-defined return values

- [ ] Every code path returns explicitly and matches the declared return type — no falling off
      the end of a function into an implicit `None` that isn't in the annotated return type, no
      partially-initialized variable reaching a `return` on some path but not others.
- [ ] mypy's `warn_return_any`/`disallow_incomplete_defs` (already enabled, see pyproject.toml)
      catch most of this statically — but still read every `return` by eye; a function that
      type-checks can still have a path that returns something *technically* valid but
      semantically wrong (e.g. a clamped value that silently clips instead of signaling invalid).

## 8. General improvement pass, without changing functionality

- [ ] Beyond the required fixes above, look for opportunities to genuinely improve the function —
      speed, resource usage, numerical accuracy, or reduced complexity — as long as the observable
      behavior for every valid input stays identical. (The `math.sqrt(x)` vs. `math.pow(x, 0.5)`
      swap in section 4 is this in practice: faster *and* more precise, zero behavior change.)
- [ ] "Without changing functionality" is a hard constraint, not a suggestion: the full existing
      test suite must still pass unchanged after the improvement, and if the improvement is
      significant enough to want its own regression test, add one rather than relying on manual
      spot-checking.
- [ ] This is a genuine pass, not a rubber stamp — but also not a mandate to rewrite working code
      for style. If nothing meaningfully improves speed/resources/accuracy/complexity, say so and
      move on rather than manufacturing a change.

## 9. Check against current MicroPython, not the version this code predates

- [ ] Much of this codebase's history predates MicroPython 1.20; the project's own build target
      has since moved forward to whatever's the latest *stable* release (see CLAUDE.md's "Platform
      target" and `toolchain/versions.toml`'s `[micropython] ref`, currently v1.28.0). Don't assume
      code written years ago still reflects the best way to do something on the current target —
      check, every time a file goes through this review, not just once.
- [ ] Check the MicroPython changelog/release notes
      ([github.com/micropython/micropython/releases](https://github.com/micropython/micropython/releases))
      between whatever version the code plausibly targeted and the current pin for anything
      relevant to the file under review: new stdlib module features, simplified semantics,
      interpreter-level performance work that changes what's worth hand-optimizing, deprecated
      patterns replaced by better ones. Note findings even when nothing needs to change in the code
      itself — that's still a useful outcome, not a wasted check. (`crc_checks.py`'s own heavy
      bytearray/memoryview slicing already benefits for free from 1.26's "avoid heap-allocating
      slices when subscripting bytearray/memoryview" interpreter change; nothing to rewrite there,
      just confirmation of why it's already reasonably fast on the current target.)
- [ ] Look specifically for the old `u`-prefixed module names (`uasyncio`, `ustruct`, `ujson`,
      `ucollections`, ...) — MicroPython consolidated these to their plain names years ago; the
      `u`-prefixed forms still work as aliases today but are the clearest tell that a file predates
      that consolidation. (`crc_checks.py` already uses the modern `asyncio`/`struct` names; other
      `improved-quality/` files — e.g. `base_classes.py`'s `from uasyncio import Lock` — still use
      the old prefixed form, a real, present instance of this in the codebase today, not a
      hypothetical concern.)
- [ ] Same "without changing functionality" hard constraint as section 8 applies when a
      modernization is purely a rewrite for currentness — the existing test suite must still pass
      unchanged. If a newer API's *semantics* genuinely differ from what the old pattern did (not
      just a rename or an interpreter-level speedup), treat that like any other behavior change
      under section 1: flag it and ask before adopting it, don't silently swap it in.

## 10. API consistency, within a file and across the project

- [ ] Within a set of related functions/classes, give every member the same shape — same
      parameter names, same parameter order, same optionality, same return convention — even
      where one member's shape looks initially unnecessary for that member alone. (`crc_checks.py`'s
      `CRC_Pass`/`CRC8`/`CRC16`/`CRC32` all take `poly: int | None = <default>` and forward it to
      `CRC_Base.__init__`, even though `CRC_Pass` can never actually use a `poly` — a caller or
      future dispatch table can treat all four identically without special-casing one of them.)
- [ ] Prefer the mechanism that makes the uniform shape *actually* consistent, not just
      superficially matching — forwarding a parameter through to a shared base/helper and letting
      *its* existing invariants do the work is more consistent than hardcoding a special case per
      member. (`CRC_Pass` forwards `poly` to `CRC_Base` and relies on the base class's own
      `num_bytes == 0` invariant to nullify it, rather than hardcoding `None` itself.)
- [ ] Beyond the current file: check how comparable functions/classes elsewhere in the project
      already express the same kind of thing — parameter naming, return-value conventions (e.g.
      `None` for invalid/no-data, matching the module's own stated contract), guard-clause
      ordering, comment style — and match them, rather than introducing a locally-plausible but
      differently-shaped alternative. Where an existing file's convention is itself questionable,
      flag it rather than silently diverging from it in the new file.
- [ ] This is a deliberate, ongoing check across the whole project, not just "whatever pattern
      happens to already be in the file you're editing" — if two files solve the same kind of
      problem in visibly different ways, that's a finding worth raising, not something to leave
      for a future session to notice.

## 11. Readability / conciseness

- [ ] One-line "why" comment per function — cite the formula's name/source and its valid domain
      where that's the "why" (see section 1). For a file organized as a set of related
      methods/classes around one shared algorithm rather than several independent formulas (e.g.
      `crc_checks.py`), a comment on what that specific method does differently from its siblings
      is enough — it doesn't need to re-cite the algorithm identity already stated once at module
      level. Don't restate what the code already says.
- [ ] Per-function/per-method explanations are always `#` comments, never docstrings — a
      module-level docstring for the file's own shared contract is expected (see below), but don't
      mix a docstring into an individual function within the same file. (Found and fixed a real
      instance of this: `crc_checks.py`'s `run_inc` had both a comment above the `def` and a
      docstring inside it saying much the same thing — keep to one, and make it a comment.)
- [ ] State a shared contract once, at module level (e.g. "returns `None`, never raises, if ...")
      instead of repeating it in every function's docstring/comment — and this applies across
      files too, not just within one: a principle already established once as a project-wide rule
      elsewhere in this checklist (e.g. section 2's "trust the type contract, mypy already enforces
      it at every call site") doesn't need independent restating in every file's own module
      docstring just because an earlier file's docstring happened to spell it out locally.
- [ ] Keep the control flow simple and in a consistent order: `None`-check, then range-check
      (plain guard clause, no `try` needed if it can't raise), then the `try`-wrapped computation.

## 12. Unit tests

- [ ] Tests must run in whatever environment the project's testing-architecture docs actually
      require (check first — e.g. this project requires the real target interpreter, not just a
      CPython stand-in; see BACKLOG.md/`tests/README.md`), not just "whatever's convenient."
- [ ] For every function, cover each parameter individually **and the combinations where
      parameters interact** (e.g. a branch selected by one parameter's sign, tested against both
      valid and invalid values of the other parameter — not just each parameter varied in
      isolation while the other stays at a fixed "safe" value):
  - `None` for each input individually, and combined
  - a valid, typical input asserted against a **sanity bound**, not an exact reference value
    (these are numerical approximations, not identities)
  - just-out-of-range on each side of every checked bound
  - the exact boundary values themselves are *accepted*, not rejected
  - `NaN` and `+inf`/`-inf` on every argument
  - any known formula-inherent quirk found in section 1, as a bounded regression check
  - physical/logical invariants where they exist (e.g. dew point never exceeds air temperature;
    an inverse pair like abs/rel-humidity round-tripping back to its own input; clamping
    behavior at the clamp's own bounds)
- [ ] Do **not** write tests for scenarios the type system already rules out (see section 2) —
      keep the suite focused on what can actually happen, not padded with impossible cases.

## 13. Wire into the existing pipeline

- [ ] Extend the lint/typecheck config's scope, and the CI job's explicit path arguments, to
      include the file's new location.
- [ ] Add the file's tests to (or confirm they're picked up by) the existing manual test-runner
      script, so the exact same command works locally and in CI.

## 14. Verify, don't assume

- [ ] After every change, actually run lint/typecheck/tests locally and read the output — don't
      report success without having done so.
- [ ] Diff the finding count before/after against files you didn't touch, to confirm you haven't
      introduced or masked a regression elsewhere.
- [ ] If working in parallel with other sessions touching the same shared infrastructure (e.g.
      after a rebase), re-check for duplicated or conflicting mechanisms and reconcile docs
      carefully — don't leave two contradictory descriptions of the same thing.

## Only then

Move the file into `src/`, and only after all of the above is actually done and passing — not
planned, not "should be fine."
