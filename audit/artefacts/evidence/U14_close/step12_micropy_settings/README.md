# Effective MICROPY_* settings: rp2 against both Unix-port builds (U14, step 12)

What was run: the lead built rp2 (`RPI_PICO_W`) and both Unix ports (`build-standard`, `build-settrace`) from a scratch
copy of the pinned MicroPython `v1.29.0` through the project's own build functions with `V=1`, and preprocessed each
build's `py/runtime.c` compile line with `-dM`. No repository was edited and nothing was committed.

Files kept here: `STEP12_README.md` (the run's own record: pin, method, deviations, findings),
`LEAD_NOTES.md` (the lead's review), `classification.md` (every differing setting with its source, its use in `src/`
and its F.7 row or the "used by nothing here" sentence) and the three plain `-dM` diffs. The raw `-dM` outputs,
build logs, probes and the evaluated-value diff the record names stayed in scratch and are not kept.

What it found that the docs now state: 194 settings differ in value between rp2 and Unix; standard and settrace differ
in `MICROPY_PY_SYS_SETTRACE` and three settings derived from it; `MICROPY_ASYNC_KBD_INTR` is 0 in all three builds
(the step text expected it to differ between the Unix builds); `MICROPY_TIME_SUPPORT_Y1969_AND_BEFORE` and
`Y2100_AND_BEYOND` are 0 in all three; rp2 reserves no emergency exception buffer, so a `MemoryError`'s message can be
empty there. SPECIFICATION.md F.7 rows 15-22 and its "used by nothing here" sentence come from this run (commit
`f445a7e`, with two reclassifications recorded in the register).
