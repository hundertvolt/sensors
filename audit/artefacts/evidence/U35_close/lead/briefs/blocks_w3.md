# U35 wave 3 blocks (lead, 2026-10-21)

Each block reads `S/u35/briefs/common_u35.md` first, then its own section here. About 60-80 tool calls each: count
them, and at 70 finish the step in hand, commit, and hand back the rest (CHECKLIST 21). CHECKLIST 22 (disk) is binding.

## P2a (lane P: the chip fake, the system-service copy swap, Y1's six annotations)
Start: branch audit/u35-p at `0dd3148` in S/wt-u35p and P1's hand-back `S/u35/handbacks/P1_final.md`. Files this block:
tests/_fram_chip_fake.py, tests/test_asy_system_service.py.
- 35 (P1a's row 35): the fake gains `cut_after_bytes`/`bytes_written`, and test_asy_system_service.py's local copy (the
  block P1a cites at :1043-1079) goes for it; the opcode `match=` key; the "1.29" citation reads "v1.29.0"; `TEST_API`.
  Each new fake part is seen failing first through its own case.
- LEAD NOTES 15 (Y1's carry): the file's six `Task[object]` annotations become `Task[None]` (Y1's hand-back names the
  lines; locate by text). Prove with `scripts/typecheck.sh` that the main pass then accepts the TaskStarter form Y1
  tested, and relay `<TASKNONE> <hash>` under `## Y`; a later Y block clears `asy_system_service`.
- Check-only on the base: 94, 95, 96, one line each.
- Runs: test_asy_system_service.py paired base/head at both stages (U32 24.92/26.40; over 10 s, so it must not grow,
  LEAD NOTES 4); every importer of `_fram_chip_fake` at both stages on the head; the readers of your files.
- Hand-back: steps by verdict; P2b's start state.

## P2b (lane P: R-8, the blank chunk against an undriven bus)
Start: P2a's head `a77baac` and hand-back `S/u35/handbacks/P2a_final.md`. Files: src/asy_fram_manager.py, tests/test_asy_fram_manager.py,
tests/test_digital_twin_fram.py, and where R-8 needs them digital_twin/_fram_chip.py, src/asy_fram_driver.py,
tests/test_asy_fram_wire_trace.py (LEAD NOTES 2a).
- Before writing the probe (LEAD NOTES 2a): state from the code, per device, when a blank status byte is read in steady
  state (boot, chunk allocation, each errcount read behind `/status`, other). If one can recur per request, measure the
  probe's SPI cost per request on the twin, state it, and keep the probe bounded, its bound recorded "(agent,
  2026-10-21)". An undriven bus reads every chunk blank, so no bound may hide a chip that stops answering: a test shows
  that.
- R-8: a blank status byte is followed by `verify_present()` (RDID) after the read has released the SPI lock, with a
  preallocated buffer. A chip that answers keeps the blank chunk as today; one that does not takes the existing lost path
  and the chip watch. No non-zero blank marker (it would change the FRAM layout).
- Seen failing first (OF-167): the twin's undriven read and the L1 fake read as blank where the test expects lost.
- `src/` edits: the mpy-cross compare of both stages' bytes (LEAD NOTES 7); test_twin_record goes red, expected.
- Effect per device and bus: all six devices, on the FRAM's SPI bus; one RDID transaction, only on a blank read. Name it
  per mode (STA, AP, Silent, Off, USB).
- LEAD NOTES 24 (T2b's finding): digital_twin/_fram_chip.py counts no write while `silent` (:287 returns before
  `_count_write`), so Run 3's rate check reads 0. Give the chip a count of the writes issued while silent, in its
  `TEST_API`, seen failing first in tests/test_digital_twin_fram.py; relay `<SILENTW> <hash>` under `## P`.
- P2a's ten unrun test_sensortask runs (LEAD NOTES 21): the four devices other than arzi and dev at -1, all six at
  32768, on your head.
- Runs: fram_manager and twin_fram paired base/head at both stages; ntp_fram_system (U32 7.63/7.68) and the twin
  integration for dev (U32 22.95/23.65) on the head at both stages as the product smoke; the P readers (P2.2) that read
  your files, plus lock_order (R-8).
- Hand-back: steps by verdict; the per-device blank-read statement and any bound; the facts D2 needs for R-8's FRAM
  sentence, relayed as one line under `## D`; P3's start state.

## U2 (lane U: the link-driver sweep, the twin link's long set, the hazard plant)
Start: branch audit/u35-u at `7158212` in S/wt-u35u and U1's hand-back `S/u35/handbacks/U1_final.md` (its sweep form:
`PollRoundClock` unpaced, the peer cancelled with the path). Files: tests/test_asy_uart_link_driver.py,
tests/test_digital_twin_uart_link.py, tests/test_uart_comm_hazard.py. The two UART comm/driver files are Y's now (R-16).
UART: test only; no emitted byte, accept/reject rule or recovery timing changes (R-18).
- 62: a new cancel sweep in test_asy_uart_link_driver.py, seen failing on a planted missing cleanup.
- 100: the twin link test also runs a 140-byte `uart_set(0x02, ...)`, asserted True while the noise tasks run; seen
  failing on a planted drop.
- 148 and 144's evidence: the 20 ms and 100 ms latency plants, made in a throwaway worktree (never committed), must turn
  the `PollRoundClock` hammers red. If either does not, add a bound test and the tag
  `l1.uart_comm_hazard_clean_transaction_virtual_ms`, relayed as `<TAG name value basis>` under `## D`. Either way relay
  one line under `## D` with the plants' result for J.7's latency sentence (D2 rewrites it).
- Runs: paired base/head at both stages: link_driver (U32 2.35/2.43), twin uart_link (55.35/59.39) and hazard
  (104.88/108.69); the last two are over 10 s and must not grow (LEAD NOTES 4). Readers: import_placement,
  mypy_any_baseline, suppression_form, uart_changelog, and grep's.
- U's complete checks are U3's (LEAD NOTES 17). Hand-back: steps by verdict; U3's start state.

## Y3 (lane Y: OF-32, then the two UART files' `Any`)
Start: Y2's head and hand-back, after the lead has merged U's handover head `7158212` into audit/u35-y (LEAD NOTES 16; the
lead states the merge commit in your prompt). Files: digital_twin/machine.py, tests/test_digital_twin_machine.py,
tests/test_asy_uart_comm.py, tests/test_asy_uart_driver.py, and Y's config files for the baseline lines.
- OF-32 (R-30) first: re-anchor `_epoch_us` and the stall offset in digital_twin/machine.py (Y1's hand-back names both
  sites and the 2**29 bound); seen failing first in test_digital_twin_machine.py on a twin `ticks_us` driven past 2**29.
  The 2**30 build's confirmation is B1's `<T30>`, not yours. Runs: test_digital_twin_machine.py paired base/head at both
  stages, and the twin integration for dev at both stages on the head.
- R-15 for `test_asy_uart_comm` and `test_asy_uart_driver`: each leaves in one commit with its baseline line, its ANN401
  entry and its `_RESIDUAL` row, or stays listed with its sites. Typing only: `scripts/typecheck.sh` after each, and the
  files' head times at both stages against U1's figures (LEAD NOTES 4's annotation rule).
- Hand-back: steps by verdict; the baseline now per pass; Y4's start state.
