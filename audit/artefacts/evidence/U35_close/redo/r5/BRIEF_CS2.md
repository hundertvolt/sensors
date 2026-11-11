# R5 unit CS2: the C stack's real chain end and worst error path, measured (lead, 2026-11-11)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `cs2_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Code: int `S/wt-u35int` at 015dda9f.
The accounting: `S/u35r/r5/BUDGETS.md` section C stack (read all of it). The script: `tests_hardware/device_scripts/
c_stack_budget.py`; its host test `tests_hardware/flash/test_memory_stress.py::test_c_stack_peak_is_within_half_the_limit`;
SPECIFICATION.md F.1 and the C.7/G.2/A.8 stack-check paragraphs (filtered). The bench runs your script next, no flash.

## Owner (verbatim)
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"

## Your work (worktree `S/wt-cs2`, branch `audit/cs2` from 015dda9f; create it; link `S/wt-u35int/node_modules` into it;
## commit locally, never push)
The script reads the stack where a leaf is entered; the chain ends 4 Python levels deeper, and the quiet run takes no
error path. Make it measure what the budget is about, with the fewest lines:
1. Record the real chain end: wrap the FRAM driver's SPI command functions (the deepest calls under set_values and
   get_values) the same way as the existing leaves, and report the chain and the phase (setup, run, the GET /status) of
   the peak.
2. Provoke, once, the deepest static chain that ends in a FRAM-backed log write: BUDGETS.md names a log entry written
   from inside GET /status. Find it from the code (file:line, the static walk), provoke it from the script without any
   src/ change (a request or input that makes the product log it, or a test-side wrap that raises once in a leaf the
   product handles and logs), and report its real end as its own fact.
3. Keep the host test's assertion and its half-limit bound as they are (their re-derivation is the owner's after the
   reading); have it note the new facts. Update tests_hardware/README.md's C-stack paragraph to what the script now
   measures.
Run the script on the twin through the harness's twin path at both thresholds (`--twin`, or `conformance.py`'s
`run_probe_on_twin()` pattern) to prove it completes and reports the facts; the twin's numbers are not the board's.

## Never
Never edit `ext/`, `src/`, `devices/` or int. No hardware, no mpremote; `tests_hardware` only with `--collect-only` or
`--twin`. Never read `arduino/`; filter as common_r1 says. Never touch `S/wt-base/.venv`, `S/tc-c` (read and run only)
or `/root/pico-toolchain`. Scratch only under `S/u35r/r5/ftmp_cs2/`. While `S/u35/lead/heavy.lock` exists: reading,
editing and single test files that bind no port only.

## Checks and hand-back
`PICO_TOOLCHAIN_DIR=S/tc-c`: ruff, the three mypy passes (`scripts/typecheck.sh` with `S/wt-base/.venv/bin` on PATH),
the twin run above, `--collect-only` of test_memory_stress.py, the `tests_scripts` files that read the script (render,
FRAM-region and device-script checks), the comment-cap test. One commit (text outside `audit/` cites no audit IDs;
trailers as common_r1). Budget about 0.8 % of the week. Hand back: `S/u35r/r5/HANDBACK_CS2.md` (at most 30 lines: the
chain you provoke and why it is the deepest, the edit, the twin proof), your commit, and last "nothing of mine is
running".
