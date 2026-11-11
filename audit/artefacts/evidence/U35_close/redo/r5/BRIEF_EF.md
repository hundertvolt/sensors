# R5 unit EF: two bench tests that fail on their own actions, fixed (lead, 2026-11-11)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `ef_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Code: int `S/wt-u35int` at 015dda9f.
The trace: `S/u35r/r5/E_TRACE.md` sections E4 and E5 (never_corrupts). The bench's results: on
`origin/claude/u35-bench-campaign` (fetch it), `audit/artefacts/evidence/U35_close/redo/hw_round1/HANDBACK.md`, the
2026-11-11 sections. Unit TW writes beside you (twins, `tests_hardware/bench/test_reset_reasons.py`): leave those files.

## Owner (verbatim)
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"

## Your work (worktree `S/wt-ef`, branch `audit/ef` from 015dda9f; create it; link `S/wt-u35int/node_modules` into it;
## commit locally, never push)
1. E4 `tests_hardware/bench/test_uart_link_under_api_load.py::test_a_multi_chunk_set_echoes_intact_under_serving_load`
   and its device script: the script drives the same initiator as the exerciser's once-a-second banner, and the
   one-initiator guard refuses the loser (by design, Part J.2). Make each round wait for the exerciser's tick, then run
   inside its sleep, so the test proves echoes intact and the exerciser failing none, as it claims. Confirm the trace's
   reading first (file:line); if it is wrong, stop and hand back.
2. E5 `tests_hardware/bench/test_bus_concurrency_under_api_load.py`: `...never_corrupts...` (d) and
   `...survives_an_ntp_transient_outage...` (the rerun) each failed on SGP40 counter 2 with W65 and W35 at teardown. The
   trace reads it as the test's own ResetVOC PUTs on an unsynced clock. Confirm for both nodes, then the smallest fix
   that keeps every check (wait for the sync before the resets, or the owed-W65/W35 form fram_erase uses).
Never loosen a check or widen a tolerance; if the only fix would, stop and hand back the options.

## Never
Never edit `ext/`, `src/`, `devices/` or int. No hardware, no mpremote; `tests_hardware` only with `--collect-only` or
`--twin`. Never read `arduino/`; filter as common_r1 says. Never touch `S/wt-base/.venv`, `S/tc-c` (read and run only)
or `/root/pico-toolchain`. Scratch only under `S/u35r/r5/ftmp_ef/`. While `S/u35/lead/heavy.lock` exists: reading,
editing and single test files that bind no port only.

## Checks and hand-back
`PICO_TOOLCHAIN_DIR=S/tc-c`: ruff on the changed files, the three mypy passes (`scripts/typecheck.sh` with
`S/wt-base/.venv/bin` on PATH), `--collect-only` of the changed bench files, the `tests_scripts` files that read them
(device-script render and FRAM-region checks included), the comment-cap test. One commit (text outside `audit/` cites no
audit IDs; trailers as common_r1). Budget about 0.7 % of the week. Hand back: `S/u35r/r5/HANDBACK_EF.md` (at most 30
lines: per item the confirmed cause, the edit, the proof), your commit, and last "nothing of mine is running".
