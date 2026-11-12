# R5 unit complete: every remaining place the same miss can hide, two read-only passes (lead, 2026-11-07)

## Read first
`S/u35r/r1/common_r1.md` (binding, its "Every level" lines above all; labels `complete1_`, `complete2_` by pass). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/findings/FINDINGS.md`
12.100-12.108, SPECIFICATION.md Part 0.1 and D.8 in `S/wt-u35int` (int b412d1b3; read only). What is done, never redo:
`S/u35r/r5/DESIGN_FU.md` (FRAM, CRC, logging, UART, SGP40 backup), `LEVELS_1.md` (the 79 keep-word rulings and their
OR rows), `LEVELS_2.md` (F.3's 37 rows, Part N's 191), `LEVELS_3.md` (every other `src/` module and the wozi module),
`STRETCH.md` (the /status and VOC stretches). Read their tallies, not their whole text.

## Owner direction (2026-11-07 17:57:27, verbatim)
"Go to all, be sure you really found all such occurrences, and it won't happen again."

## The miss to look for (FINDINGS 12.100)
(a) an agreement checked one file at a time while the cost lives in a combination; (b) a ruling or decision resting on
the isolated case (idle, smallest input, Unix port, one task) that fails in combination or under load, and that then
shielded the code; (c) a measurement of the harmless case standing for the worst one, or a budget naming the wrong
waiters; (d) a cost far beyond its physical need. Lens at every level; one figure per operation: need against cost.

## Pass 1 (complete1): the rulings and figures the earlier passes did not cover
1. SPECIFICATION.md statements citing a decision ("(owner, 20", "(agent, 20", "settled", "accepted", "decided",
   "deliberate") that are not among LEVELS_1's 79 lines, and CLAUDE.md's hard rules and working agreements that keep a
   time, hold, heap or wear cost (e.g. "Boot latency is not a metric", the I2C/WiFi watchdog backstops, the asyncio
   MemoryError rule). Per item that keeps a runtime cost: its facts, and whether they hold at every level today.
2. Figures in Parts A-M outside F.3 (timings, bounds, retry counts, buffer sizes, heap figures in I, recovery timings
   in J, test bounds in E): its condition, whether that is the worst case, and its real consumers in the code.

## Pass 2 (complete2): what the code passes did not read
1. `tests/` and `digital_twin/`: models or doubles that hide a cost the device pays (a bus, FRAM or CPU step modelled
   as instant, so a hold or stretch can never show); tests that measure the harmless case and stand for the worst;
   tests that pin a cost rather than a function (they would block a lean fix).
2. `buildgen/` and the five generated device modules besides wozi (`build/generated_src/`, read filtered): wiring that
   makes one device's work wait on an unrelated one, or a cost the wozi module does not show.
3. `scripts/`, `toolchain/`, `.github/workflows/ci.yml`: a step running far beyond its need (repeat work, a run whose
   result nothing reads). Headlines only; firmware findings first.

## Rules for both passes
Read only: never edit a tree. No gate or whole-tier run (bfix holds the host); a single-file probe through `run.sh` at
most. Every finding: evidence (file:line, commit, measurement), C or I, origin (original 2026-07-13 / pre-audit / audit
10-06 to 10-28 / post-restart), and the leaner form that loses nothing. No hypothesis is a finding; prefer removal.
**Every view or grep of SPECIFICATION.md, CLAUDE.md, `devices/`, generated modules, `audit/` or
`src/asy_wifi_service.py` goes through common_r1's credential filter; never view those whole.** Never read `arduino/`;
never open `/root/.claude/`; no hardware; never print, copy or write any Wi-Fi credential or the hotspot password.

## Limits and hand-back
Write only `S/u35r/r5/COMPLETE_<pass>.md` (at most 50 lines; ranked; one line saying what was checked and found
clean) and scratch under `S/u35r/r5/ftmp_complete<pass>/`. Budget about 1 % of the week each. Hand back by 21:30 UTC:
its path, one line per headline result, and last "nothing of mine is running".
