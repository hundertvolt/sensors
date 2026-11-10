# R5 unit APT: apt's wall-clock step limit goes; apt's own stall timeout and the mirror check stay (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; label `apt_`). S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-
8798-ed52081f7df8/scratchpad`. FINDINGS (`S/u35r/findings/FINDINGS.md`) 12.159 (the CI failure and the evidence),
12.138; `S/u35r/r5/GIVEUP_3.md` D5 and its ledger rows for `tool.apt_*`; `CONSENT_2_ledger.tsv` S14 (the mirror check
and cache: owner 2026-10-27, KEEP) and T12. Code: int `S/wt-u35int` at the head the lead names when starting you
(T and P9 merged first). You own `toolchain/setup_toolchain.py`, `.github/`, `scripts/ci_apt_cache.py`,
`scripts/setup_cross_browser_toolchain.sh`, their tests_scripts tests, and the SPEC lines that state this limit.

## The evidence
Snapshot 58 CI (run 42793916276): a 588 MB `apt-get install --download-only` cut three times by `_APT_STEP_TIMEOUT_S` =
150 s while the mirror still delivered; no test ran. 25caf528 bounds no apt call. apt's own
Acquire::http(s)::Timeout ends a stalled read; the 150 s wall-clock limit also ends a slow live download (the owner's
give-up pattern, 2026-11-09 21:57:36). Each CI job's `timeout-minutes` is the backstop (CLAUDE.md hang rule).

## Your work (worktree `S/wt-apt`, branch `audit/apt`; commit locally, never push)
1. The wall-clock limit around every apt call goes: setup_toolchain's update and download, apt-cache-restore's update
   (`timeout "$step_s"`), and any other site of `tool.apt_step_timeout_s`; the tunable and its Part N row go with it.
   apt's `Acquire::Retries` and `Acquire::http(s)::Timeout` stay unless common_r1's source rules remove them: judge,
   say which and why, in one line each.
2. The mirror check stays (owner, 2026-10-27). Its yardstick moves from the removed limit to the calling job's own
   `timeout-minutes`, the way the playwright site already passes `ci.playwright_install_timeout_min`: for
   firmware-build-verify, `ci.firmware_build_verify_timeout_min`, read from its own site. No new number.
3. Tests that pin the old limit follow the code (no new test unless a behaviour lost its only catcher).
4. The SPEC lines that state the limit (B.10.1, the apt update and download lines, Part N) say the new fact; no other
   SPEC edit.

## Never
No new bound, retry or mechanism. Never drop the package cache or the mirror check. No `src/` change. Never edit
`ext/`; never read `arduino/` (`':!arduino'` in every git grep and git log); never open `/root/.claude/`; no hardware.
Credential filter as common_r1 says. Scratch only under `S/u35r/r5/ftmp_apt/`.

## Checks and hand-back
The touched tests_scripts files (single-process pytest through the shared venv); `lint_direct.sh`; host mypy pass;
then under `S/u35/lead/heavy.lock` holding `apt` (wait while it exists; `rm` it, literal path, its own command)
`uv run pytest tests_scripts` once. Lines removed and added. One commit; budget about 1 % of the week. Hand back:
`S/u35r/r5/HANDBACK_APT.md` (at most 20 lines), your commit, one line per headline result, and last "nothing of mine
is running".
