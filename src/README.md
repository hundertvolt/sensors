# src/

Files land here once they've cleared the full quality bar below — moved out of
`improved-quality/` (WIP refactor target, see CLAUDE.md) once they have. `math_helpers.py` is the
first file to make this move; this checklist is distilled from that review, for reuse on the next
one.

Out of scope for this checklist: setting up the CI pipeline itself and the MicroPython Unix-port
toolchain build — that's already done (see BACKLOG.md/`toolchain/README.md`) and is a one-time
project-level setup, not something each new file redoes. What follows is what changes, and what
you check, per file.

## 1. Correctness

- [ ] Identify the formula/algorithm's authoritative source (published paper, standard,
      datasheet) — verify via current web search, not training memory or assumption. Note the
      source in a code comment.
- [ ] Verify the implementation actually matches that source (coefficients, sign, order of
      operations) — don't assume existing code is correct just because it's already deployed.
- [ ] Verify the coded validity range/domain matches the formula's *actual published* valid
      domain, not just whatever range the existing code happened to have. (Found a real bug this
      way: `wet_bulb_temperature`'s humidity lower bound was `0.5%`; Stull (2011) only validates
      down to `5%`.)
- [ ] Where the formula's own domain is wider than how it's actually used, cross-check against
      the real caller's hardware constraints instead (e.g. a sensor's datasheet operating range).
      (`altitude_baro`'s 300-1250 hPa / -40-85 degC range comes from the BMP388/390 datasheet, its
      only caller — not from the barometric formula itself, which has no such bound.)
- [ ] Look specifically for functions with **no validity range check at all** — an easy gap to
      miss since the function still "works" for any input right up until it's asked to
      extrapolate a formula miles outside where it was ever validated.
- [ ] If review surfaces an inherent quirk or non-ideality (not a bug) — e.g. two independently-
      fit formula branches that don't perfectly agree at their boundary — don't silently
      "fix" it by guessing new coefficients. Document it with a code comment and add a regression
      test with a tolerance matched to the *measured* behavior, not an idealized one.

## 2. Robustness / exception safety

- [ ] Every function returns a clear "no data" sentinel (`None` here) — **never raises** — for:
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

## 3. Typing

- [ ] Type-hint every parameter and return value.
- [ ] Verify the annotation syntax is actually safe on the target runtime by checking *current*
      official docs for that runtime — don't reason from general Python knowledge alone.
      (Confirmed via MicroPython's own docs that `X | None` annotations are parsed but never
      evaluated at runtime, on every version checked — so they're safe regardless of whether the
      runtime otherwise supports `X.__or__`/`UnionType`. This was a real open question on record
      before being checked.)

## 4. Readability / conciseness / performance

- [ ] Prefer the more specific/faster stdlib call where it's a drop-in equivalent (e.g.
      `math.sqrt(x)` over `math.pow(x, 0.5)` — faster and more numerically precise than the
      generic `pow` path for a square root specifically).
- [ ] One-line "why" comment per function: cite the formula's name/source and its valid domain.
      Don't restate what the code already says.
- [ ] State a shared contract once, at module level (e.g. "returns `None`, never raises, if ...")
      instead of repeating it in every function's docstring/comment.
- [ ] Keep the control flow simple and in a consistent order: `None`-check, then range-check
      (plain guard clause, no `try` needed if it can't raise), then the `try`-wrapped computation.

## 5. Unit tests

- [ ] Tests must run in whatever environment the project's testing-architecture docs actually
      require (check first — e.g. this project requires the real target interpreter, not just a
      CPython stand-in; see BACKLOG.md/`tests/README.md`), not just "whatever's convenient."
- [ ] For every function, cover:
  - `None` for each input individually, and combined
  - a valid, typical input asserted against a **sanity bound**, not an exact reference value
    (these are numerical approximations, not identities)
  - just-out-of-range on each side of every checked bound
  - the exact boundary values themselves are *accepted*, not rejected
  - `NaN` and `+inf`/`-inf` on every argument
  - any known formula-inherent quirk found in step 1, as a bounded regression check
  - physical/logical invariants where they exist (e.g. dew point never exceeds air temperature;
    an inverse pair like abs/rel-humidity round-tripping back to its own input; clamping
    behavior at the clamp's own bounds)
- [ ] Do **not** write tests for scenarios the type system already rules out (see 2.) — keep the
      suite focused on what can actually happen, not padded with impossible cases.

## 6. Wire into the existing pipeline

- [ ] Extend the lint/typecheck config's scope, and the CI job's explicit path arguments, to
      include the file's new location.
- [ ] Add the file's tests to (or confirm they're picked up by) the existing manual test-runner
      script, so the exact same command works locally and in CI.

## 7. Verify, don't assume

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
