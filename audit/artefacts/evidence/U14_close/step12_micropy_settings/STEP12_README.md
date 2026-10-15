# M.PROC.016 (U14 step 12): effective `MICROPY_*`/`MP_*` settings, rp2 vs the two Unix builds

Audit tool run, scratch only. Nothing was edited or committed in any repository, and nothing was
written under `/root/pico-toolchain`.

## Pin and sources seen

- Project tree read: `scratchpad/wt-u12on11` at `081b60e370b256fa14a912493c59293fe72f6060` (2026-10-07 10:31 UTC),
  `toolchain/versions.toml` `[micropython] ref = "v1.29.0"`, board `RPI_PICO_W`.
- MicroPython: copy of `/root/pico-toolchain/micropython`, `git describe` = `v1.29.0`,
  HEAD `0fd6c573ea815774668bbb16b8e197c8822368b2`, clean working tree.
- Submodules used by these builds (from `git submodule status` of the source tree):
  `lib/pico-sdk` 98a542c1a62f (2.3.0; the firmware compiles against this one, since `build_env()` passes
  no `PICO_SDK_PATH`), `lib/lwip` 77dcd25a7250 (STABLE-2_2_1_RELEASE), `lib/cyw43-driver` 055d64274b01 (v1.1.1),
  `lib/btstack` 77e752abd6a0, `lib/mbedtls` 0bebf8b8c7f0 (v3.6.6), `lib/micropython-lib` ee4bb8ff139e,
  `lib/tinyusb` b549ac1d84cb (0.21.0-micropython1), `lib/berkeley-db-1.xx` 0f3bb6947c2f.
  (`/root/pico-toolchain/pico-sdk` is also at 98a542c1a62f but is not what the firmware build reads.)
- Compilers: `arm-none-eabi-gcc` 13.2.1 20231009 (`/usr/bin`), host `gcc` 13.3.0 (Ubuntu 24.04); cmake 3.28.3.

## Method

1. `cp -a /root/pico-toolchain/micropython step12/mp` (the shared `ports/unix/build-*` dirs were then removed from
   the copy; the shared tree had no rp2 build dir).
2. `driver/run_builds.py` imports the worktree's own `toolchain/setup_toolchain.py` (with `python3 -B`, so no
   `__pycache__` lands in the worktree) and calls its real functions against the copy, with `toolchain_dir=step12`
   so the overrides are generated into `step12/build_overrides/`:
   - `build_mpy_cross(mp, 4)`;
   - `build_firmware(mp, "RPI_PICO_W", 4, toolchain_dir=step12)` - applies `apply_lwip_connection_counts_override()`
     (BOARD_DIR = `step12/build_overrides/lwip_connection_counts_board`), `CFLAGS_EXTRA=-Wno-array-bounds`, the
     board's own frozen manifest, then the project's own `verify_lwip_macros_in_build()`, which passed;
   - `build_unix_port(mp, step12, 4)` and `build_unix_port(mp, step12, 4, settrace=True)` - both apply
     `apply_unix_kbd_intr_override()` (`VARIANT=standard VARIANT_DIR=step12/build_overrides/unix_kbd_intr_variant`),
     the settrace one adds `-DMICROPY_PY_SYS_SETTRACE=1` and `BUILD=build-settrace`.
   The ONLY change to the project's commands: `run()` was wrapped to append `V=1` to each `make` in `ports/`, so the
   compile lines are printed. All three builds still passed the project's own `error:`/`warning:` gates.
3. `cmd_*.txt` = the `py/runtime.c` compile line from each `make V=1` log (`logs/*.log`) verbatim. The two Unix lines
   end in the Makefile recipe's own `|| (echo -e "See ...Build-Troubleshooting"; false)` hint, kept verbatim;
   the rp2 line runs in `ports/rp2/build-RPI_PICO_W`, the Unix ones in `ports/unix`.
4. `driver/dm.py`: drop that `||` suffix, remove `-c`, `-o X`, `-MD`, `-MT X`, `-MF X`, insert `-dM -E`, run in
   the same cwd; keep `#define MICROPY_*`/`#define MP_*`, sort -> `defs_*.txt` (864 / 811 / 811 lines); the exact
   preprocess commands are in `logs/dm_cmd_*.txt`, the full `-dM` output in `logs/dM_all_*.txt`.
5. `diff_*.txt` = plain `diff` of the sorted `defs_*.txt` (536 / 540 / 4 lines).
6. Beyond the brief, because a text diff of `-dM` lines misses value changes: `driver/effective.py` fully expands
   every object-like macro inside the same translation unit (`#include` of the real `runtime.c` plus one probe line
   per macro, same flags, `-E -P`) and evaluates integer constant expressions; `driver/widthprobe.py` compiles the
   14 `sizeof`/typedef-dependent macros to assembly with each build's flags and reads the constants back. Result:
   `diff_effective_values.txt` (194 settings whose value differs) and `logs/effective.json`, `logs/width_values.json`.
7. `driver/classify.py` builds `classification.md` from those plus the per-setting judgements in its `C`/`NOT`
   tables (source citations from the copy at v1.29.0, usage greps over `src/*.py`, `ext/microdot.py` and
   `wt-u12on11/build/generated_src/*.py`, which buildgen had generated at 10:32 UTC, after the HEAD commit; buildgen
   was not run).
8. Cross-check: the copy's Unix `genhdr/moduledefs.h`, `root_pointers.h` and `qstrdefs.generated.h` are
   byte-identical to the shared `/root/pico-toolchain/.../build-{standard,settrace}/genhdr/` ones, and both
   settrace binaries report `hasattr(sys, "settrace") == True` (the shared binary was only executed, not written).

## Findings in brief

- **standard vs settrace**: the raw `-dM` diff is exactly one line, `MICROPY_PY_SYS_SETTRACE` `(0)` -> `1`.
  `MICROPY_ASYNC_KBD_INTR` does NOT differ between them: it is `(0)` in all three builds, because
  `build_unix_port()` applies the `unix_kbd_intr` override to both variants (without it the Unix value would be
  `(!MICROPY_PY_THREAD_GIL)` = 1, `ports/unix/variants/mpconfigvariant_common.h:32`; rp2 takes mpconfig.h's default
  0, `py/mpconfig.h:847-848`). By value, settrace also flips three settings derived from it whose `-dM` text is
  unchanged: `MICROPY_PERSISTENT_CODE_SAVE` 0->1 (`py/mpconfig.h:422-423`), `MICROPY_PY_BUILTINS_CODE` 1->3 (FULL,
  `py/mpconfig.h:1419`), `MICROPY_EXPOSE_MP_COMPILE_TO_RAW_CODE` 0->1 (`py/compile.h:34`). Nothing else differs.
- **rp2 vs Unix**: 194 settings differ in value. 176 differ in `-dM` text too (Section A). 18 have identical
  `-dM` text but a different value (Section B): the three settrace-derived ones above, ten `sizeof(mp_uint_t)`-derived
  ones read back by the width probe (`MICROPY_BYTES_PER_GC_BLOCK` 16 vs 32, `MICROPY_PY_TIME_TICKS_PERIOD` 2**30 vs
  2**62, `MP_SMALL_INT_*`, `MP_BYTES_PER_OBJ_WORD`, ...), and five whose identical text refers to a differing setting
  (`MICROPY_EMIT_INLINE_ASM`, `MICROPY_PY_LWIP_SOCK_RAW`, `MP_FLOAT_EXP_BIAS`, `MP_INT_MAX`, `MP_INT_MIN`). A further
  68 differ in text only with the same value (Section C: 49 `MP_E*` errno constants, 19 spelling-only cases).
- **F.7**: 62 of the 194 fall into 15 F.7 row candidates (classification.md Section D); 132 go into the
  "differ, used by nothing here" sentence (Section E). Five groups are new relative to A.U14.28's rows 1-14:
  exception message detail, machine-module fakes, soft-callback scheduling, module loading/search path,
  filesystem; plus two low ones (random seed, C-stack recursion margin).
- Two facts worth carrying into F.7 row 11: (a) no `micropython.alloc_emergency_exception_buf()` call exists in
  `src/`, `ext/microdot.py` or `build/generated_src` at this tree (A.U14.28 row 11 says "the boot entry reserves
  one"); (b) without a buffer, `py/objexcept.c:478-505` turns a `MemoryError` whose message object cannot be
  allocated into an exception with no args, so on rp2 `str(e)` can be `''` - no "memory allocation failed" text
  for a log-grep gate to find - while the rig's static 256 B buffer always keeps the message.

## Could not reproduce exactly / deviations

- `V=1` appended to every `make` (the brief's own instruction); nothing else changed.
- `-j4` instead of the project's default `os.cpu_count()`; does not affect flags.
- rp2 built with the board's own frozen manifest, not a device's generated one (`scripts/build_firmware.py <device>`
  needs the website build). The defines are the same either way: `ports/rp2/CMakeLists.txt:48-66` always sets a
  manifest and `py/mkrules.cmake:47-50` adds the same two frozen defines for any manifest.
- Unix: only the final (vanilla) rebuilds that `run_verification_sequence()` leaves were reproduced, not its
  intermediate frozen-verify-module build, which is deleted afterwards and is not a rig binary.
- Paths in the commands point at the scratch copy (`step12/mp`, `step12/build_overrides`) instead of
  `/root/pico-toolchain/...`; the generated override files are otherwise the project's own output.
- Limits of the method: `-dM` on `runtime.c` sees only macros visible in that translation unit (settings defaulted
  locally inside another `.c` file are not listed); lwIP options are not `MICROPY_*`/`MP_*` and are out of scope
  (B.14.2 verifies them separately; the build's own `verify_lwip_macros_in_build()` passed).

## Time

About 17 minutes wall clock for copy + four builds + extraction (builds: mpy-cross 0.4 s, Unix standard 8 s,
Unix settrace 9 s, rp2 35 s at `-j4`), plus the classification work; started 10:52 UTC.

## Files

`cmd_rp2.txt`, `cmd_unix_standard.txt`, `cmd_unix_settrace.txt`; `defs_*.txt`; `diff_rp2_vs_standard.txt`,
`diff_rp2_vs_settrace.txt`, `diff_standard_vs_settrace.txt`; `diff_effective_values.txt` and `effective_*.txt` (extra: expanded/evaluated value of every macro per build);
`classification.md`; `driver/` (the scripts); `logs/` (build logs, `-dM` commands and full outputs, probes,
JSON intermediates). The MicroPython copy and its build objects were deleted at the end.
