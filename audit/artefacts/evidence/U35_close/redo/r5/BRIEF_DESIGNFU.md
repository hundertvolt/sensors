# R5 unit designfu: design check of the FRAM, CRC, logging and UART parts against the pillars (lead, 2026-11-07)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `designfu_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/plan/PLAN.md`
section 0, and the owner's words of 2026-10-28 in `S/u35r/recovered/owner_rulings_after_LN118.md` (the block "The
morning of 2026-10-28") and its last entry (2026-11-07 16:45:25). Evidence: `S/u35r/findings/FINDINGS.md` entries
12.89, 12.95 and 12.96; the bench's trace files (`git -C S/wt-u35int show origin/claude/u35-bench-campaign:audit/
artefacts/evidence/U35_close/redo/hw_round1/uart_trace_20261107/attempt3_trace.txt`, attempt1/2 likewise; the TRACE
lines come from a bench-only image whose code is branch `audit/uart-trace`). Code: the integration tree `S/wt-u35int`.

## Owner ruling behind this unit (2026-11-07 16:45:25 UTC, verbatim)
"If you check the whole situation against our pillars, which you should already have done before even asking me, it
would have been plainly obvious that only option B stays - what would any setting of FRAM or UART ever have cross
dependencies? It's two completely different devices. That's a violation already. Then, these 8s should have made you
suspicious if it had been way less, that's overkill, runaway, all these situations we tried to prevent a few days ago.
Yet another violation of the pillars. So is option B sufficient at all? The whole affected software parts need a
review and design check again."
B = (i) the UART link independent of FRAM timing, and (ii) the FRAM hold fixed at its source.

## The pillars to check against (the owner's words and CLAUDE.md)
- Clean, minimal code; a few lines per module; no patching one mechanism over another; nothing built on a hypothesis.
- Low complexity: of two forms that both hold, the one with fewer lines, branches and states.
- Modules are libraries and self-contained: one device's or module's work never makes an unrelated one wait.
- Long-blocking work never stalls timing-sensitive work (SPECIFICATION.md F.3); the UART modules never block the loop.
- A number far beyond what the physics needs (8 s for a 528-byte FRAM write; 0.5-1 s even unloaded) marks a design
  defect, never a fact to document.
- No uncaught exceptions; the memory discipline; no hardcoded delay checks.

## Your work (read-only)
1. Per part, its pillar violations (file:line, which pillar, the effect shown by evidence or derivable from the code,
   marked confirmed or inferred): `src/asy_crc_checks.py`; `src/asy_fram_manager.py` (every chunk operation: write,
   read, clear, verify, invalidate, erase); `src/asy_fram_driver.py`; `src/asy_print_log.py`'s FRAM persistence;
   `src/asy_uart_comm.py` and `src/asy_uart_driver.py`'s exchange paths; `src/asy_sgp40_driver.py`'s backup (does it
   run inside the sensor's own sampling loop, and what does an 8-20 s backup do to that loop?).
2. The coupling sweep over all of `src/`: every path that awaits a FRAM write (an `err_s`/`wrn_s`, a chunk write)
   inside timing-sensitive work (the watchdog feed and the supervisor, sensor loops with a fixed period, the
   webserver's request handling, Wi-Fi/NTP/DNS, the UART), and every lock held across yields (FRAM, SPI, I2C, config).
   For each: who can make whom wait, and how long at most, from the code and the evidence.
3. Answer: is B sufficient? If not, what else, at its root.
4. The smallest design for each fix B and item 3 need: the change, its cost (lines, RAM, CPU), whether stored FRAM
   data stays readable, and the tests that would pin it. Prefer removing a cause over adding a mechanism.
5. One candidate exists, stopped half-built and uncommitted in `S/wt-uartq` (`git -C S/wt-uartq diff`, 11 files,
   +370/-54): the logger records and prints at once and writes FRAM in one background task per logger, which the UART
   uses. Judge it against the pillars as one option among others, not as the answer.
A Unix-port timing probe under your own `ftmp/` is allowed where it settles a relative cost (it says nothing absolute
about the RP2040); run it through `S/u35/lead/run.sh`.

## Never
Never edit any tree. Never read `arduino/`; never open `/root/.claude/`. No hardware. Never print, copy or write any
Wi-Fi credential or the hotspot fallback password.

## Limits
Write only `S/u35r/r5/DESIGN_FU.md` (and scratch under your own `ftmp/`). Budget about 1 % of the week. Hand back by
19:00 UTC.

## Hand-back
`S/u35r/r5/DESIGN_FU.md`, at most 70 lines: the violations (item 1), the coupling table (item 2), the answer to B
(item 3), the designs (item 4), the candidate's verdict (item 5). Return its path, one line per headline result, and
last "nothing of mine is running".

## Added by the owner (2026-11-07 16:47:31 UTC, verbatim)
"Especially keep in mind: all gaps closed, (really) agreed on features implemented, and from there on minimal,
efficient and lean changes."
