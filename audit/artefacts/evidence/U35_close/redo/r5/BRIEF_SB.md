# R5 unit SB: TCP_SND_BUF 6400 -> 1600, and the harness waits for the board after a reset (lead, 2026-11-11)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `sb_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Code: int `S/wt-u35int` at ca780dbd
(gate green). The need: `S/u35r/r5/E_TRACE.md` (E2 and "E2 reopened by the 13:00 run"). Silicon on the final image:
beside 5 clients at zero window the page took 7.6 s, >10 s and 20.24 s across runs, and /status 10 s on the control
image: the shared 12,000 B MEM_SIZE arena, each stalled connection holding up to TCP_SND_BUF (6,400 B, ~7.2 KB). The
trace shows 1,600 B (2 x TCP_MSS 800) restores every bound of tests_hardware/bench/test_modlwip_send_stall.py by
construction. Unit CSA writes src/asy_print_log.py and src/asy_fram_manager.py beside you: leave those files.

## Owner (verbatim)
- 2026-11-11 13:24:56: "you can rebuild and reflash the image whenever it fits, and act according to the results from
  the bench" (the lead takes TCP_SND_BUF 1600 from the bench's results; this supersedes 2026-09-30's "[lwip] keeps its
  values" for this one option, and 2026-11-11 12:12's stated limit with its 20 s page bound).
- 2026-11-09 22:27:31: "... Lean, functional, no losses, no gaps, efficient by smart design appropriate for limited
  devices like the rp2"

## Your work (worktree `S/wt-sb`, branch `audit/sb` from ca780dbd; create it; link `S/wt-u35int/node_modules` into it;
## commit locally, never push)
1. `toolchain/versions.toml` [lwip] TCP_SND_BUF 1600. Check it against lwIP's own sanity checks in the pinned tree
   (`S/tc-c/micropython/lib/lwip/src/core/init.c`: TCP_SND_BUF >= 2*TCP_MSS, the derived TCP_SND_QUEUELEN and
   TCP_SNDLOWAT against MEMP_NUM_TCP_SEG and TCP_SND_BUF), the override's anchors (`toolchain/micropython_overrides.py`),
   and buildgen's per-device ensemble check; update every test that pins 6400 with the derivation, never a loosened check.
   Say whether the Unix-port (host/twin) build takes the [lwip] values; if it does, say what must be rebuilt (the lead
   rebuilds; you do not build firmware or the Unix port).
2. The docs: SPECIFICATION.md B.14.2.1, B.14.4 and F.9 where they state 6,400, the two-dead-clients arithmetic, "[lwip]
   keeps its values" and the stated-limit sentence commit 9b1e651d added (it becomes the fix: what five stalled clients
   now hold and what a live connection keeps), the per-page cost (+0.1-0.8 s, the trace's estimate, marked as one), and
   BACKLOG.md's running list of build-environment changes since the chroot legs (one line). Filtered views only.
3. `test_modlwip_send_stall.py`: undo 9b1e651d's page change (the page bound back to _REQUEST_MAX_S and its old client
   timeout; `_PAGE_MAX_S` gone); keep "A failed bound goes to the owner, never a quietly larger bound."
4. The reset race: on the bench, a test's first mpremote call (save_fram_raw in test_reset_reasons.py's `_evidence()`)
   got EIO because the previous test's teardown restore had reset the board and returned while USB re-enumerated. Find
   the shared place the harness resets or restores a board and make it wait for `board.is_device_present` (as
   `_attributed()` now does) before returning; the smallest edit, no new mechanism.

## Never
Never edit `ext/`, `devices/`, `src/asy_print_log.py`, `src/asy_fram_manager.py` or int. No hardware, no mpremote;
`tests_hardware` only with `--collect-only` or `--twin`. Never read `arduino/`; filter as common_r1 says. Never touch
`S/wt-base/.venv`, `S/tc-c` (read only) or `/root/pico-toolchain`; never build firmware or the Unix port. Scratch only
under `S/u35r/r5/ftmp_sb/`. While `S/u35/lead/heavy.lock` exists: reading, editing and single test files that bind no
port only.

## Checks and hand-back
`PICO_TOOLCHAIN_DIR=S/tc-c`: `bash S/u23/rebuild.sh S/wt-sb` first; ruff, the three mypy passes, every tests_scripts
file that reads versions.toml, the overrides, buildgen's validator or the changed harness files, `--collect-only` of the
changed tests_hardware files, `test_code_conventions.py`, `test_comment_block_cap.py`. One commit (text outside `audit/`
cites no audit IDs; trailers as common_r1). Budget about 0.8 % of the week. Hand back: `S/u35r/r5/HANDBACK_SB.md` (at
most 30 lines: the sanity arithmetic, what the host build takes, every file changed and why, the reset-race site), your
commit, and last "nothing of mine is running".
