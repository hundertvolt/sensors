# R5 unit CSA: the FRAM write path, three pass-through levels shorter (lead, 2026-11-11)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `csa_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Code: int `S/wt-u35int` at ca780dbd
(gate green). The need: `S/u35r/r5/BUDGETS.md` section C stack (option A) and `S/u35r/r5/HANDBACK_CS2.md`. Silicon
(bench, 2026-11-11, final image): quiet peak 5,476 B (setup, fram._send_and_read), provoked end 6,876 B of 7,936 B (87 %),
the provoked chain GET /status -> ... -> ConfigManager._get_values -> CFGMGR_NTP err_s -> ... -> FRAM SPI command. Since
the synchronous FRAM change every plain level under a FRAM-backed log entry or config-store access sits on the C stack,
about 264 B per level on the board. Code: src/asy_print_log.py (err_s/wrn_s, _store, _write, read_into/write_into hops),
src/asy_fram_manager.py (FRAMChunk read_into/write_into, _write/_read, _write_chunk/_read_chunk, _handle_status_bytes,
_set_check_sb, _compare_with).

## Owner (verbatim)
- 2026-11-11 13:24:56: "you can rebuild and reflash the image whenever it fits, and act according to the results from
  the bench" (the lead takes option A: shorten the FRAM write path).
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"

## Your work (worktree `S/wt-csa`, branch `audit/csa` from ca780dbd; create it; link `S/wt-u35int/node_modules` into it;
## commit locally, never push)
1. Map the plain-call chain under a FRAM-backed log entry (err_s/wrn_s) and under a FRAM-backed config-store read and
   write, down to the driver's SPI commands: every level, what it adds (a check, a loop, an except) or that it only
   passes through.
2. Fold the pure pass-through levels into their callers, at least three on the log-entry write path, the deepest first:
   the stored bytes, the SPI command order, every error code, log text and return value stay exactly as they are; the
   FRAM driver's public API (set_values/get_values, OR36.a (3)) stays. No new function, no new layer, net lines down.
   If a level carries behaviour (an except that records, a retry, a check), it stays: say which and why.
3. Prove it: the tests of every changed module at -1 and 32768 (FRAM byte-layout tests included), the FRAM twin tests,
   and `tests_hardware/device_scripts/c_stack_budget.py` on the twin through the harness's twin path at both thresholds
   before and after (provoked_end and the quiet peak: the twin's numbers are not the board's, the difference is).
   Update SPECIFICATION.md F.1's longest-chain sentence and any doc line naming a folded function.

## Never
Never edit `ext/`, `devices/` or int; never change a wire format, a stored byte, an error code or a log text. No
hardware, no mpremote; `tests_hardware` only with `--collect-only` or `--twin`. Never read `arduino/`; filter as
common_r1 says. Never touch `S/wt-base/.venv`, `S/tc-c` (read and run only) or `/root/pico-toolchain`. Scratch only
under `S/u35r/r5/ftmp_csa/`. While `S/u35/lead/heavy.lock` exists: reading, editing and single test files that bind no
port only.

## Checks and hand-back
`PICO_TOOLCHAIN_DIR=S/tc-c`: `bash S/u23/rebuild.sh S/wt-csa` first and after every src/ edit; ruff, the three mypy
passes (`scripts/typecheck.sh` with `S/wt-base/.venv/bin` on PATH, or mypy directly per pass), the changed modules'
tests and the FRAM and print-log twin tests at -1 and 32768, `tests_scripts/test_code_conventions.py`,
`test_ticks_wrap_scan.py`, `test_comment_block_cap.py`, `test_gc_collect_sites.py`, the await-depth test and every
tests_scripts file that reads the changed modules. The lead runs the full gate. One commit (text outside `audit/` cites no
audit IDs; trailers as common_r1). Budget about 1.2 % of the week. Hand back: `S/u35r/r5/HANDBACK_CSA.md` (at most 40
lines: the chain map, the levels folded and kept with why, the twin's stack before and after, net lines, frozen bytecode
size change), your commit, and last "nothing of mine is running".
