# R5 unit C: the build chain and the website at their need, nothing dropped (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; label `c_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. The rows routed to you, with their
evidence: `S/u35r/r5/SIMPLER_4.md` #1-#7, #10, #12 and `SIMPLER_1.md`'s runner rows; `CONSENT_2.md` and its ledger
(W01, W03, W18, G02, G03, G04, S19, A01; S18's grain stays, FINDINGS 12.142); `GIVEUP_3.md` and its ledger (the
build-chain and toolchain bounds, 12.138); `CREDIT_ledger.tsv` (credits in your files); FINDINGS 12.124-12.126,
12.138, 12.142, 12.144. Code: int `S/wt-u35int` at a293d6f9. Unit G writes the firmware at the same time (`src/`, the
device TOMLs, their tests); you own `scripts/`, `toolchain/`, `.github/`, `buildgen/`'s host code, `js/`, `html/`,
`tests_js/` and `tests_scripts/` files that test those. G may change one JS mirror line (`js/poll-manager.js`'s cap).

## Owner (verbatim)
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"
- 2026-11-09 18:30:08: "Before removing any function which could be a feature which is just unused, ask me"

## Your work (worktree `S/wt-c`, branch `audit/c` from a293d6f9; create it; commit locally, never push)
Website (the image carries it: measure gz bytes per page):
1. W18: the background device check skips its /status request while an open section already polls /status.
2. W01: the browser's per-hint re-validation of build-generated definitions back to the pre-audit scope; the
   definitions shape corpus that only it needs goes with it (CONSENT_3 REMOVE 2).
3. W03: one shared errcount code table per page instead of one per group.
Build chain:
4. G02: the boot oracle leaves `generate_device()` for the test generator; its third FRAM-consumer table goes.
   G04: one module-to-file table in `buildspec.py`. G03: `trigger_spread()` goes; its bench test derives the order.
5. SIMPLER_4 #4: the website build takes the definitions the generator wrote (no second derivation). #1: set the rig
   build setting once, the five launch guards go. #2: one instrumented web run does web-unit-tests' and
   web-coverage's jobs. #3: the port lock on `flock` (its stale-takeover machinery goes). #6: one summary-block
   emitter. #10: help and usage pinned once (`test_shell_conventions.py`). #12: the memory markers from one source.
6. S19: the website stager to about its pre-audit form (the 500-line lexer and bundle checks go; a duplicate name or a
   bootstrap mismatch then fails at page load in the staged tiers - name that tier's test).
7. Bounds (12.138): `build_firmware.py`'s `nm`/`git` timeouts go (a silent "git cannot tell" no more); the toolchain's
   local-command bounds go, CI's job `timeout-minutes` is the backstop (one silently reinstalled Node); picotool's
   5 x 2 s retry named or derived.
8. SIMPLER_1's "one Python implementation per runner mechanism" and the QSTR_BYTES_IN_LEN(2) build setting, each only
   where it is lossless (measure). SIMPLER_4 #7 (setup's two throwaway images) only if lossless; else report it.
9. Credits (A01): the "owner-reviewed, 2026-11-06" tags and every audit-era STRETCHED/UNBACKED credit in your files to
   their ledger's plain form; credits dated before 2026-09-25 wait for the owner's answer.

## Never
Never remove a feature (a CLI, an option, a script's mode) without the owner: report it. Never change a /status byte,
a wire byte or a generated module's content except what an item names (state each). Never edit `ext/`; never read
`arduino/`; never open `/root/.claude/`; no hardware. No new bound or mechanism without a source. Credential filter as
common_r1 says. Scratch only under `S/u35r/r5/ftmp_c/`.

## Checks and hand-back
Touched files' tests while fixing; `lint_direct.sh`; three mypy passes; npm lint, typecheck, unit tests; then the gate
as common_r1 says, under `S/u35/lead/heavy.lock` holding `c` (unit G may hold it: wait while it exists; `rm` it,
literal path, its own command), plus the web tiers your items touch. Per-page gz sizes and dev `imageFreeBytes`
against a293d6f9; CI minutes saved where measurable. One commit; budget about 3 % of the week. Hand back by 13:00 UTC:
`S/u35r/r5/HANDBACK_C.md` (at most 40 lines: per item what went, the figure), your commit, one line per headline
result, and last "nothing of mine is running".
