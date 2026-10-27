# F4c3: finish F4c2's prepared listener-close check (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Worktree `S/wt-u35f4c`, branch `audit/u35-f4c2` (base 7172c802): F4c2's five
files are STAGED there, not committed. Logs in `S/u35/laneR/f4c3/`. Read F4c2's brief
`S/u35r/briefs/f4c2_listener_silicon_readonly.md` and its hand-back `S/u35r/handbacks_redo/F4c2.md`. The design is
reviewed by the lead; do not redesign it. It is read-only on device memory and stays so: never add a write by address,
and if a safety classifier interrupts you, stop at once and hand back.

## Why F4c2 stopped
Its last command combined a whole-tier `--collect-only` with a run of the new flash test WITHOUT `--twin`; the auto-mode
classifier denied it, correctly: tests_hardware runs only with `--collect-only` or through the twin in this session.
Never run a tests_hardware test any other way, and never retry the denied command.

## What to do
1. Review the staged diff yourself first (`git diff --cached`): it must hold no write to device memory by address, no
   flash write, no FRAM manager. Say what you checked.
2. One fix the lead found: `tests_hardware/harness.py` `elf_symbols()` passes `timeout=120` inline, while every other
   timeout in harness.py is a module constant with its `# @tunable l4.harness_*` tag and a Part N row (see
   `_PICOTOOL_LOAD_TIMEOUT_S` and SPECIFICATION.md's `l4.harness_*` rows around :12504). Make it one the same way,
   placed where D.15 and the file's constants block put it, with its Part N row in the file's rows' form (Basis
   estimated, naming the bound it mirrors, `scripts/build_firmware.py`'s nm listing; the commit cited as the other rows
   cite theirs, from `git log -S` once committed; if the check needs the hash before it exists, commit in two steps and
   say so). test_tunables_register green, and red on a scratch copy with the new tag deleted.
3. Commit F4c2's files plus the fix: subject `U35 lane F4c2: <summary>`, the two trailers.
4. The checks F4c2 could not finish, on the commit: the whole tests_hardware tier `--collect-only` alone (inside
   `unshare -n S/u24/ns_xdg.sh`, nice 19, RUNS.md lines); the new flash test once more with `--twin`; ruff, the host and
   main mypy passes (stubs at `S/shared/typings`), the comment cap, test_citations, test_decision_vocabulary,
   test_tunables_register, and the tests_scripts readers of the five files. test_twin_record stays red for the two new
   files (the lead records them at the close); name any other red.
5. The silent-failure scan of the new files (an `except` or fallback that hides a failure; a check that can pass
   vacuously): verdict per site.
Toolchain: the ELF is in `S/tc-f4c` (F4c2's private copy): use it, never its setup, never the shared toolchain for a
build. Delete nothing of S/tc-f4c; the lead removes it.

## Not yours
src/, toolchain/, digital_twin/, audit/ records, every allow-list (hand back the row you need). Do not push. Hand-back:
the commit(s), what the review checked, the fix and its red/green, each check's result with log paths, the scan's
verdicts; last line "nothing of mine is running".
