# R5 unit stretch: two loop stretches the board measured above the 21 ms routine bound (lead, 2026-11-07)

## Read first
`S/u35r/r1/common_r1.md` (binding; label `stretch_`; its credential filter for every repo text view). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/LEVELS_2.md` item 2,
`S/u35r/findings/FINDINGS.md` 12.100-12.106, SPECIFICATION.md Part 0 and D.8 in `S/wt-u35int` (int b412d1b3: every
level, cost against need), F.3's `con.routine_stall`, `stall.voc_process` and `lag.loop` rows, J.6's reply floor. Board
evidence: the bench branch (`git -C S/wt-u35int show origin/claude/u35-bench-campaign:<path>`, files under
`audit/artefacts/evidence/U35_close/redo/hw_round1/`).

## Owner direction (2026-11-07, verbatim)
16:47:31: "Especially keep in mind: all gaps closed, (really) agreed on features implemented, and from there on minimal,
efficient and lean changes." 17:31:00: "[...] all necessary scans and checks, can start immediately and run through."

## Your work (read-only)
1. Streaming a `GET /status` holds the loop 104-122 ms per request after the stall fix (739 ms before), against the
   21 ms `con.routine_stall`. Find, from the code and the board's figures, which synchronous step holds it (which value
   or loop, how many bytes or iterations), its physical need, and the smallest fix at its source.
2. `stall.voc_process` measured 41.3 ms on the board (3 runs; its test fails). Find which part of the VOC step costs
   it, compare with what the computation needs on a Cortex-M0+ without an FPU (Sensirion's own reference, the legacy
   port's field behaviour), and the smallest fix at its source, or show the bound is the defect.
3. For the 21 ms bound itself: who actually needs it (the consumers in the code: UART receive ring and reply floor,
   watchdog feed, LED frames, others) and at which value each breaks, so a fix is sized against a real consumer.
A Unix-port probe under your own `ftmp_stretch/` may settle a relative cost; run it through `S/u35/lead/run.sh`.

## Never
Never edit any tree. No hardware. Never read `arduino/`; never open `/root/.claude/`. Never print, copy or write any
Wi-Fi credential or the hotspot fallback password.

## Limits and hand-back
Write only `S/u35r/r5/STRETCH.md` (at most 40 lines; C/I marks, origin, file:line) and scratch under
`S/u35r/r5/ftmp_stretch/`. Budget about 0.5 % of the week. Hand back by 20:30 UTC: its path, one line per result, and
last "nothing of mine is running".
