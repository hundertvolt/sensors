# Falsification check: the controller-rung fix (lead, 2026-11-05; read-only)

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Read `S/u35r/r1/common_r1.md`
(binding; labels `frung_`), then `S/u35r/r5/HANDBACK_RUNG.md` and `S/u35r/r4/HANDBACK_F126.md`.

## The claim to break
Branch `audit/rung` (`S/wt-rung`, commits `4aac0f38` and `9c365a27` on `3c402f85`) makes the I2C ladder meet
SPECIFICATION.md F.2: "Each rung fires at most once per failure episode - a bus rung once per bus, whichever reader on
it reaches it first". `src/asy_i2c_driver.py` gains a `rebuilds` counter stepped by `recover()`; `src/
asy_base_classes.py`'s `_recover_bus()` skips the clear if `recoveries` moved since the reader's episode began, and the
controller rung only if `rebuilds` moved; the line re-marking `_bus_mark` after a rung is gone.

Try to refute it. In particular:
1. Is there an ordering of two or three readers on one bus in which a rung still fires twice in one episode, or in
   which a reader at its 4th failure skips the rebuild although none ran? Include a reader whose episode starts after
   another's rung, a reader whose episode ends and restarts mid-way, the supervisor's restart (setup again), the boot
   clear, hot replug, and the counters' wrap at `COUNTER_CAP`.
2. Did removing the re-mark line change anything else (a reader's own clear and its later rungs; the next episode)?
3. Does anything else read `recoveries` or `bus_mark` with the old meaning: `src/`, `digital_twin/`, `tests/`,
   `tests_hardware/`, `buildgen/`, the website, a REST field?
4. Do the new tests fail on `3c402f85` and pass on the fix for the reason they state? Does the twin test's 500 ms
   start really put the SGP40's clear first on dev, and what does it do on wozi?

## Limits
Read-only: write only your hand-back. Light runs only (single test files), at most six; the host's heavy slot is
taken. Budget about 0.4 % of the week. Never read `arduino/`; never open `/root/.claude/`.

## Hand-back
`S/u35r/r5/FALSIFY_RUNG.md`, at most 20 lines: each claim held or refuted, with file:line or run evidence, and a
proposed minimal fix for any refutation. Return its path. Last line: "nothing of mine is running".
