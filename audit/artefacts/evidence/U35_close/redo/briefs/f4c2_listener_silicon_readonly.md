# F4c2: the listener-close patch checked on silicon, read-only, prepared (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base `a304353e` or later (named at launch); worktree and branch named at
launch; logs in `S/u35/laneR/f4c2/`. Facts: F4a's hand-back `S/u35r/handbacks_redo/F4a.md` (the three modlwip patches and
the host lwIP test that proves them red then green), SPECIFICATION.md B.14.4, and U21's evidence
`audit/artefacts/evidence/U21_close/lane_s/probe/rp2_listen/` (its map of the lwIP pools on an earlier image).

## The goal
The host lwIP test is the emulated proof. For the hardware round, prepare a flash-tier check that the patched image
behaves on silicon: closing a listening socket, and closing one whose `listen()` failed for lack of heap, leaves the
connection-pcb pool as it was and the board keeps serving. It is read-only: the device script uses the normal socket
API and reads memory, and it never writes to device memory by address (owner's least-wear rule; and a write by
address is out of this brief's scope).

## What to prepare (never run on hardware: there is none in this session)
1. The addresses come from the image under test: the host side reads the dev ELF's symbols (arm-none-eabi-nm) for the
   TCP listen and connection pcb pools, and passes them to the script; nothing hard-coded. Cross-check them and the
   struct sizes against U21's map, and say where they differ.
2. The device script, run isolated with production stopped: read the connection-pcb pool's bytes; open and close a
   listener; then the failed-`listen()` case (bind, heap locked, `listen()` raises, heap unlocked, close); read the pool
   again. Every slot free before and after must be byte-identical; report any difference by slot and offset. Then a
   short socket round trip shows the stack still works. No FRAM manager (an isolated script's own FRAM manager
   overwrites production's logs, tests_hardware/README.md), no flash write, no extra flash cycle.
3. The host test in the flash tier, and the script's entry where tests_hardware/README.md lists the flash tier's scripts.
   Run it `--collect-only`, and through any twin or fake backend the harness itself offers for its host side.
4. If a safety classifier interrupts you at any point, stop at once and hand back what you have; do not rework around it.

Checks: ruff, the host mypy pass, the comment cap, test_citations and the tests_scripts readers of the files you add
(device-script facts, run records, watchdog lists). The dev firmware build for the ELF uses your private toolchain
copy (named at launch); never run its setup; nothing pointed at the shared toolchain that could rebuild it.

## Not yours
src/, toolchain/, the twin files, audit/ records, every allow-list (hand back the row you need). Commit subject
`U35 lane F4c2: <summary>`, the two trailers; do not push. Hand-back: the commit, the address derivation and its
cross-check, the script's steps and what each was verified against in the pinned source, the collect-only result; last
line "nothing of mine is running".
