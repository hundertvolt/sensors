# R5 unit TW: three twin-vs-chip divergences and one reboot race in the hardware tier (lead, 2026-11-11)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `tw_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Code: int `S/wt-u35int` at 015dda9f.
The bench's results: on `origin/claude/u35-bench-campaign` (fetch it), `audit/artefacts/evidence/U35_close/redo/
hw_round1/HANDBACK.md`, section "Bench 2026-11-11 11:20 UTC - d", items A and B. The twins ran on the bench host for the
first time (arm64), so `tests_hardware/flash/test_chip_conformance.py` compared chip and twin there for the first time.
`digital_twin/README.md`'s Chips rows state what each twin claims (read it filtered).

## Owner (verbatim)
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"

## Your work (worktree `S/wt-tw`, branch `audit/tw` from 015dda9f; create it; link `S/wt-u35int/node_modules` into it;
## commit locally, never push)
1. SCD30 `C03_read_before_a_command`: chip `dddddd`, twin `000000`, although the README row says the twin returns 0xDD
   (`D scd30::a_read_with_no_command_pending_returns_0xdd_bytes`). Find why the probe's sequence reaches zeros on the
   twin and fix the twin.
2. BMP3XX `B03_pwr_ctrl_during_forced`: chip `13`, twin `03` (the twin has no conversion time; its README row calls that
   accepted). Smallest correct twin: model the forced conversion's time (DS001's formula) so PWR_CTRL reads forced mode
   during it. If that ripples beyond the BMP3XX fake and its own tests, stop and hand back the options instead.
3. FRAM `C02_wel_after_write`: chip `1`, twin `0`. Read the bench part's datasheet in `datasheets/` on WEL after WRITE
   and make the twin match the chip; if the datasheet says otherwise, stop and hand back both.
4. `tests_hardware/bench/test_reset_reasons.py` escalate: `_attributed()`'s `mpremote exec` got EIO from the port while
   the budget reboot was still re-enumerating USB. Wait for the board with the harness's existing presence wait before
   that exec; add no new mechanism.
Keep the README rows true to what the twin now does. Each fix the smallest; no product file (`src/`, `devices/`,
`buildgen/`) changes.

## Never
Never edit `ext/`, `src/`, `devices/` or int. Never weaken a check or add an ignore. No hardware, no mpremote;
`tests_hardware` only with `--collect-only` or `--twin`. Never read `arduino/`; filter as common_r1 says. Never touch
`S/wt-base/.venv`, `S/tc-c` (read and run only) or `/root/pico-toolchain`. Scratch only under `S/u35r/r5/ftmp_tw/`.
While `S/u35/lead/heavy.lock` exists: reading, editing and single test files that bind no port only.

## Checks and hand-back
`PICO_TOOLCHAIN_DIR=S/tc-c`: `bash S/u23/rebuild.sh S/wt-tw` first; ruff on the changed files, the three mypy passes
(`scripts/typecheck.sh` with `S/wt-base/.venv/bin` on PATH), each changed chip's own tests/ files at -1 and 32768, the
three probes on the twin through `tests_hardware/conformance.py`'s `run_probe_on_twin()` at both thresholds (each key
now equal to the chip's value above), `tests_scripts` files that read the changed files, the comment-cap test. One
commit (text outside `audit/` cites no audit IDs; trailers as common_r1). Budget about 1 % of the week. Hand back:
`S/u35r/r5/HANDBACK_TW.md` (at most 40 lines: per item the cause, the edit, the proof), your commit, and last "nothing of
mine is running".
