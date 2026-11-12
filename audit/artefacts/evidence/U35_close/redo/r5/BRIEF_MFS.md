# R5 unit mfs: merge fsync over ub into one green tree (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; label `mfs_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/HANDBACK_FSYNC.md`
(31 lines) and `S/u35r/r5/HANDBACK_UB.md` (27 lines), FINDINGS 12.145-12.146, and both briefs (`BRIEF_FSYNC.md`,
`BRIEF_B.md`) for what each side meant. The lead's trial merge listed 18 conflicted files, 27 hunks
(`S/u35/lead/merge_fsync_conflicts.txt`).

## Your work (worktree `S/wt-mfs`, branch `audit/mfs` at int ddf77ce8 = ub merged; commit locally, never push)
1. `git merge --no-ff e1958815` (fsync's two commits). Resolve every hunk keeping both sides' intent: fsync's
   synchronous FRAM, its one log form (`err_s()`/`wrn_s()` written inside the call, no await, no queued form) and
   its CRC rename; ub's LED lock with no logger, TickGrid cadences, SCD30 helper pair and bus release, BMP3XX wait,
   notification build check, removed stop/arm functions. Where ub deleted code fsync converted, the deletion wins;
   where ub added or moved a log call, it takes fsync's form.
2. Then run fsync's saved transform over every file ub's commit touched (`git diff --name-only 8f04f2f1 39e18d2a`):
   `python3 S/u35r/r5/ftmp_fsync/fsync_transform.py FILE...` for `src/`, `digital_twin/`, `tests_hardware/`, and the
   same with `--tests` for `tests/` (idempotent; its usage is its docstring). Every remaining `await` on a log call,
   `err_q`/`wrn_q`, `asy_crc_checks` or writer reference in the tree is a merge defect: `git grep` for them, zero left
   (`':!arduino'`, outside `audit/`).
3. The NTP no-reply scenario (`tests/_sensortask_scenarios.py`): ub's writer-idle condition in `attempt()` goes with
   the writer - the attempt ends when the peer is torn down and the mode lock is free, as on fsync's side.
4. UART changelog: one Class B entry (no C impact) after fsync's B99, for ub's touches of `asy_uart_driver.py`
   (PieceBuffer moved in), `asy_uart_comm.py`, `asy_uart_link_driver.py`; no wire change.
5. Docs that the merge leaves stale, current state, fewest lines: CLAUDE.md's boot-confined `gc.collect()` exception
   paragraph and `.claude/skills/work-routines/SKILL.md` line 111 describe the per-unit placement collects fsync's
   e1958815 removed - the lead decided their removal (FINDINGS 12.145, under the owner's 2026-11-09 19:11:51 and
   20:43:39 directions; CLAUDE.md's own "update the doc in the same session" rule); restate each as the current fact
   (no `gc.collect()` in `src/`; placement holds without it since FRAM became synchronous, `SPECIFICATION.md` I.4(f.1);
   the bench re-checks it on silicon), never a history. Any SPECIFICATION.md text the merge leaves contradictory.

## Never
Never change a stored FRAM byte, a CRC value, a wire byte or a `/status` byte beyond what the two units already
changed (the LED chunk and errcount entry gone; codes 44, 45, E19 gone). Never add a mechanism, bound or number
(common_r1's two source rules). Never edit `ext/`; never read `arduino/`; never open `/root/.claude/`; no hardware.
Credential filter as common_r1 says. Scratch only under `S/u35r/r5/ftmp_mfs/`.

## Checks and hand-back
`S/u23/rebuild.sh S/wt-mfs`; every conflicted and transformed test file at both GC stages while fixing (per-device
files for dev and arzi); `lint_direct.sh`; three mypy passes; then the gate exactly as common_r1 says, under
`S/u35/lead/heavy.lock` holding `mfs` (nothing else runs now; `rm` it, literal path, its own command, when done).
Sizes (`S/u35r/r0/module_sizes.sh`, armv6m) and dev `imageFreeBytes` against 8f04f2f1. One merge commit (subject
`U35: merge fsync - ...`, trailers as common_r1). Hand back by 07:30 UTC: `S/u35r/r5/HANDBACK_MFS.md` (at most 25
lines: each conflict's resolution in one line, the transform counts, the gate figures, sizes), your commit, and last
"nothing of mine is running".
