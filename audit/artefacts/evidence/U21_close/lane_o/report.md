# U21 lane O: final report (toolchain/micropython_overrides.py, tests_scripts/test_micropython_overrides.py)

Branch `audit/u21-o`, worktree `scratchpad/wt-u21o`. New since the accepted O2 (merged as 2f7543c):
- `9314738` WIP O3 (already sent): IPV6_FRAG_COPYHEADER and a runtime probe that runs the timers; the L0 cases of every section.
- `c91676c`: each override directory starts empty; a stale .pp is never read (both from the silent-failure scan).
- `da6338a`: D.15 member order in the test file (a pure reorder, the file's last edit).

Earlier commits: O1 `b4b6640`, O2 `e20dd49`, and the merges `5654ea1` and `5c60c42`. Nothing pushed.

## Step table

| step | M-id | state | note |
|---|---|---|---|
| 6 | M.TOOL.036 | applied | `_embeddable()` covers whitespace and `"'\$#;:`. Every `apply_*()` passes both dirs (and `extra_include_dirs`) through it before any read or write. |
| 15f | M.TOOL.037 | applied | Banner and message point to B.14.1. Adds `UNIX_KBD_INTR_SENTINEL`, `UNIX_KBD_INTR_DIR_NAME` and `_unix_kbd_intr_header()`; the emitted comment no longer names CLAUDE.md. Manifest uses `!r`; the make `include` stays unquoted. The one-file mbedtls line is in the variant mk. A.SDEP.11 outcome (a): the pin did not move. |
| 15g | M.TOOL.038 | applied | Floor comment uses A.U21.31's text with "(agent, 2026-09-22)". `:270-272` now reads "…the floor above". Adds `_lwip_redefines()`, quoted `include("…")`, `!r` manifest, keyword-only `extra_include_dirs` and the board-cmake mbedtls line. **Already landed:** tags `:177, :182`; A.U14.30's comment `:264-266`. `_MIN_TCP_SND_QUEUELEN` is U28's. |
| 15h | M.TOOL.039 | applied | modlwip_eagain section. Anchors re-verified at v1.29.0; the copy header names "MicroPython 1.29.0", read from `py/mpconfig.h`. Pin unchanged; #19704 still open. |
| 15i | M.TOOL.040 | applied | `apply_unix_lwip_host_override()` plus the build gate's outcome: two flags private to modlwip.o, and IPV6_FRAG_COPYHEADER (see Deviations). |
| 15j | M.TOOL.041 | applied | Three readbacks plus the tick readback. Forms pinned from the real build (below). **Already landed:** tag `:353`. |
| 52 | M.TOOL.042 | applied | `CURRENT_OVERRIDE_DIRS` holds the five names. Its L0 case derives them from a real run of every `apply_*()`. |
| 53 | M.TOOL.044 | applied (O half) | Branch 2b lines in the kbd and host variant mk and in the board cmake. Confirmed in the real rp2 `flags.make` (below). |
| 59 | M.TOOL.080 | applied | Tick-offset section on A-10's mechanism. Adds keyword-only `board`, per the lead's ruling. The `dev` image was built once (below). |
| 62 | M.TSC.114 | applied (U21 stage) | Every fake `run` takes `(cmd, cwd=None, **_kwargs: object)`; the new tests are module-level functions. The `Test*` classes stay (A-9). The "flavour" renames of the existing names are U24/U36. |
| 63 | M.TSC.115 | applied | Header test pins the sentinel and its order. Readback cases over fake `.pp` texts; the argv case uses a fake `make` on a test PATH. |
| 64 | M.TSC.116 | applied (U21 stage) | `!r` and quoted-include asserts; all nine refused characters; a relative dir; every `apply_*()` refuses before reading. The 18-anchor count is U24's. |
| 65 | M.TSC.117 | applied | modlwip anchors, apply and readback; structural tests for both rp2 overrides and the lwIP flavour. `:194-203` follows A-3; `:855-859` uses `\[lwip\]`; `:643-646` renamed. |
| 80 | M.TSC.229 | applied | Tick cases, including a structural case that is **red until T's `board=` lands** (below). |

## Deviations (each conservative, reversible, decided on the owner's behalf for review; agent, 2026-10-08)

1. **The packet's `.c.obj` was wrong** (`packet_laneO.md:570, :2195, :2205`). pico-sdk 2.3.0 sets `CMAKE_${LANG}_OUTPUT_EXTENSION .o` (`lib/pico-sdk/cmake/preload/toolchains/util/pico_gcc_common.cmake:45`).
   - The readback is pinned to the real form: the `build.make` rule `CMakeFiles/firmware.dir<copy>.o: <copy>`, and exactly one non-empty `*modlwip.c.o`, at `CMakeFiles/firmware.dir/<copy without its leading />.o`.
2. **The tick override takes keyword-only `board`** (lead's ruling) and returns `{"BUILD": "build-<board>-tickoffset"}`. §3's signature is amended.
   - T's call on the API base (`setup_toolchain.py:514`) lacks it. `audit/u21-t` 5b6dc1b already passes `board=board`.
3. **Two flags on the host build, private to modlwip.o**, in the host variant mk only. The first real build (exit 1, `u21/o_test_run1.log`) needed exactly these; nothing else in lwIP or the port warned on GCC 13.3.0 x86-64.
   - `-Wno-sign-compare`: 8 unmodified upstream lines compare `mp_uint_t` with `-1`. rp2 compiles with `-Wall -Werror` only (`ports/rp2/CMakeLists.txt:540-541`), and in C `-Wsign-compare` comes only with `-Wextra`, which the Unix port adds (`ports/unix/Makefile:55`).
   - `-DSOMAXCONN=2`: `ports/unix/mpconfigport.h:176` reads `<sys/socket.h>`'s SOMAXCONN, which modlwip.c never includes; 2 gives rp2's default from `py/mpconfig.h:2148`.
   - `private` keeps both flags off the shared headers that modlwip.o's build may trigger.
4. **`#define IPV6_FRAG_COPYHEADER 1` in the host lwipopts.h only** (S found it; the lead confirmed it). With 8-byte pointers, `struct ip6_reass_helper` outgrows `IP6_FRAG_HLEN`, and `ip6_reass_tmr()` asserts on that every second (`lib/lwip/src/core/ipv6/ip6_frag.c:117-120`).
   - lwIP's own remedy for "sizeof(void*) > 4" is this define (`lwip/ip6_frag.h:60-72`). rp2 is 32-bit, and its assert is a no-op.
5. **The host readback's runtime probe now runs lwIP's timers.** It runs `lwip.reset(); time.sleep_ms(2500); lwip.callback()` and prints a sentinel; the old probe never ran the timers.
6. **"Insertion inside the loop" holds by construction.** `_MODLWIP_INSERT_AFTER` is a substring of the loop anchor and both occur exactly once; an L0 case pins this. A separate runtime check would be unreachable code.
7. **Extra anchors** beyond A.U21.12's list, all from plan §1 15i's spot-check list:
   - `py/scheduler.c`'s hook call in `mp_event_handle_nowait()`;
   - the Unix Makefile's `include $(TOP)/py/mkrules.mk` after the variant include (the vpath order);
   - rp2's six lwIP settings. The host header restates them, each anchored, because rp2's `lwipopts.h` includes `pico/rand.h`.
8. **The kbd readback passes `BUILD=` explicitly** when the build's own variables lack it (the default flavour). It refuses a mismatched `BUILD`.
9. **From the silent-failure scan** (new finding): each `apply_*()` empties its own directory before writing, and the kbd readback removes a stale `.pp` first.
10. **D.15:** the test file is reordered (its last edit). **`micropython_overrides.py` is not.**
    - The role order would scatter every section. Their banners carry the plan's texts and decision tags ("(owner, 2026-09-30)", "(owner, 2026-10-01)"), and D.15 would need them removed first.
    - The reorder of host scopes is U36's (A.U36.038; G5/R50 "code in U36 — the reorder beyond `src/`"). U20 left `buildgen/` the same way: 12 of its 26 modules are out of D.15 order today, by a simplified check.
    - Owner-review item.
11. **The tick readback preprocesses `py/mphal.h`** with the build's `flags.make` and reads the sentinel, which is A-10's method, rather than reading "compile definitions" (M.TOOL.080's wording).
12. **The `dev` tick image was built through a scratch driver.**
    - The driver runs `scripts/build_firmware.py` with `functools.partial(st.build_firmware, tick_offset_test=True)`, and a shim that adds `board=` to T's not-yet-merged call.
    - S passes no tick flag at U21, so there was no in-tree path.

## Facts for D (SPECIFICATION.md)

- **B.14 general shape** (A.U21.08):
  - Every path written into a generated file is resolved, and refused when it contains whitespace, `"`, `'`, `\`, `$`, `#`, `;` or `:`. The message names the character and the remedy (a `--toolchain-dir` without them).
  - Anchors are verified before anything is written.
  - Each override empties its own directory under `build_overrides/` first: a stale file would still be compiled (a variant's `*.c`) or found first on an include path.
  - Directories: `unix_kbd_intr_variant`, `lwip_connection_counts_board`, `modlwip_eagain`, `unix_lwip_host_variant`, `tick_offset_test` (`CURRENT_OVERRIDE_DIRS`).
- **B.14.1, verified paragraph:** every Unix build re-proves the override.
  - It runs `make <the build's own variables> BUILD=<dir> <dir>/unix_mphal.pp`, which is MicroPython's own `$(BUILD)/%.pp` rule (`py/mkrules.mk:119-121`). `make` is resolved on the build's PATH.
  - Required: `#define MICROPY_SENSORS_KBD_INTR_OVERRIDE_APPLIED 1`; the last `#define MICROPY_ASYNC_KBD_INTR` reads `(0)`; `sighandler()` (up to `void mp_hal_set_interrupt_char`) calls `mp_sched_keyboard_interrupt()` and never `nlr_jump(`. The `.pp` is removed before and after.
  - Real `-dD` lines: `#define MICROPY_ASYNC_KBD_INTR (!MICROPY_PY_THREAD_GIL)`, `#undef MICROPY_ASYNC_KBD_INTR`, `#define MICROPY_ASYNC_KBD_INTR (0)`, the sentinel.
  - Passed on real build-standard, build-settrace and build-lwip (three runs on u21tc-o). With the real standard variant, it is refused ("sentinel absent").
- **B.14.2:**
  - The board cmake includes the real board file by quoted `include("…")`, and manifests relay by `include('…')` (repr).
  - The test image adds `include_directories(BEFORE "<tick dir>")`. A release build's generated files carry no tick line.
- **B.14.4 `modlwip_eagain`** (implemented).
  - **Anchors in `extmod/modlwip.c`, each exactly once:**
    - the 13-line ERR_MEM retry loop (`:801-813`); its insertion point (`:806-809`) lies inside it by construction;
    - `#include "modnetwork.h"` (`:40`).
  - **Wiring anchors, in order:**
    - `extmod/extmod.cmake`: `    ${MICROPY_EXTMOD_DIR}/modlwip.c` (`:27`), inside `set(MICROPY_SOURCE_EXTMOD`;
    - `ports/rp2/CMakeLists.txt`: the extmod include (`:100`), then the usermod include (`:108`), then the QSTR append (`:500-501`), then `target_sources(… ${MICROPY_SOURCE_PY} ${MICROPY_SOURCE_EXTMOD}` (`:518-520`);
    - `ports/rp2/Makefile`: `-DUSER_C_MODULES` (`:40`);
    - `py/usermod.cmake`: `:54` and `:63`.
  - **The copy:** `build_overrides/modlwip_eagain/modlwip.c`. Its 2-line header reads "…of MicroPython 1.29.0 - SPECIFICATION.md B.14. Do not edit.", with the version taken from `py/mpconfig.h`.
    - The include is rewritten to `extmod/modnetwork.h`.
    - The EAGAIN block sits right after `tcp_output()`'s `ERR_OK` check and before `MICROPY_PY_LWIP_EXIT`/`mp_hal_delay_ms(50)`.
    - It has no `#line`.
  - **The swap:** `micropython.cmake` (byte text as A.U21.09), passed as `USER_C_MODULES=<dir>`.
  - **Readback form, pinned from the real build:** the `build.make` rule `CMakeFiles/firmware.dir<copy>.o: <copy>`; the object at `CMakeFiles/firmware.dir/<copy minus leading />.o` with a `.o.d` beside it; neither path of the original present.
    - The `.o` extension is pico-sdk 2.3.0's own; CMake 3.28.3 on this host mirrors the absolute path.
    - A layout change fails as "layout changed".
  - **Scope:** non-blocking sockets only; blocking ones keep the 10 s loop. No `src/` site sends on a blocking TCP socket: accepted asyncio sockets are non-blocking (`extmod/asyncio/stream.py:172`), and `src/` otherwise uses UDP.
  - **Removal trigger:** the pin carries a real fix for issue 19704.
  - **Host build (the third flavour), files under `build_overrides/unix_lwip_host_variant/`:**
    - `mpconfigvariant.h`: the kbd header plus `void mp_lwip_host_poll(void);` and `#define MICROPY_INTERNAL_EVENT_HOOK mp_lwip_host_poll()`;
    - `mpconfigvariant.mk`: `include <standard mk>`, `INC += -I<variant>/lwip_inc`, `vpath extmod/modlwip.c <variant>/src`, the mbedtls line, the two private modlwip.o flags;
    - `manifest.py`: a relay;
    - `src/extmod/modlwip.c`: byte-identical to the rp2 copy;
    - `lwip_inc/lwipopts.h`: rp2's six settings, then `LWIP_RAND() ((u32_t)rand())`, then the common block, then `MEM_ALIGNMENT` set to `struct.calcsize("P")` (8 here), then `IPV6_FRAG_COPYHEADER 1`, then the `[lwip]` redefines with their sentinel;
    - `arch/cc.h`: a loud assert that ends in `abort()`;
    - `arch/sys_arch.h`: empty;
    - `lwip_host_port.c`: `sys_now()`, the DNS preference 4, and `mp_lwip_host_poll()` (`netif_poll_all(); sys_check_timeouts();` behind a re-entry flag).
  - **Host make variables:** `VARIANT=standard VARIANT_DIR=… BUILD=build-lwip MICROPY_PY_LWIP=1 MICROPY_PY_LWIP_LOOPBACK=1 MICROPY_PY_SOCKET=0`.
  - **Host anchors:** `extmod/extmod.mk` (`\textmod/modlwip.c \`, `ifeq ($(MICROPY_PY_LWIP),1)`, the LOOPBACK block); the Unix Makefile's variant include before `extmod.mk`, then `ifeq ($(MICROPY_PY_SOCKET),1)`, then `$(wildcard $(VARIANT_DIR)/*.c)`, then `mkrules.mk`; `py/mkrules.mk`'s `vpath %.c . $(TOP)`; `py/mphal.h`'s `#ifndef MICROPY_INTERNAL_EVENT_HOOK`; `py/scheduler.c`'s hook call; `poll_sockets()`'s body; `opt.h`'s `LWIP_HAVE_LOOPIF` and `LWIP_NETIF_LOOPBACK_MULTITHREADING` lines; rp2's six settings; `lib/lwip/src/core/tcp_out.c` exists.
  - **Host readback:** `build-lwip/extmod/modlwip.P` names the copy first and never the original. The real form is `build-lwip/extmod/modlwip.o: \` followed by ` <copy> \` on the next line, because a long path wraps.
    - The copy must hold the EAGAIN block.
    - The binary runs `import lwip, socket, time; print(socket is lwip); lwip.reset(); time.sleep_ms(2500); lwip.callback(); print('lwip timers ok')`, which must print `True` then the sentinel, exit 0, within `_PREPROCESS_TIMEOUT_S`.
- **B.14.5 `tick_offset_test`** (test-only):
  - **Mechanism (A-10):** a copy of `ports/rp2/mphalport.h` in `build_overrides/tick_offset_test/`, found first because `build_firmware()` passes the directory as `extra_include_dirs`. The generated board cmake then gains `include_directories(BEFORE …)`, and in the real `flags.make` the tick dir is first in `C_INCLUDES`.
  - **Why it reaches every translation unit:** `py/mphal.h:36` includes `<mphalport.h>` in angle brackets, and no `ports/rp2`, `extmod` or `shared` file includes it with quotes (grep).
  - **The copy:** `#define MICROPY_SENSORS_TICK_OFFSET_MS (4294067296u)` and the sentinel `#define MICROPY_SENSORS_TICK_OFFSET_TEST_APPLIED 1` are prepended, and exactly one line is replaced. `return to_ms_since_boot(get_absolute_time());` becomes `return (mp_uint_t)(to_ms_since_boot(get_absolute_time()) + MICROPY_SENSORS_TICK_OFFSET_MS);` (`:96-98`; 32-bit unsigned arithmetic; the timer is never written).
  - **Build dir:** `build-<board>-tickoffset`, a separate CMake cache per board.
  - **Readback:** `py/mphal.h` is preprocessed with the build's own `flags.make` and the sentinel read back. `verify_tick_offset_in_build(build_dir, expected=…)` runs after every rp2 build. Expected false on a build that carries it raises "a release build carries the tick-offset test override".
  - **Proven once on `dev`** (u21tc-o, `u21/o_tick_dev1.log`):
    - the image built (2 320 384 B uf2);
    - `tick_offset_in_build` returned True;
    - `0xfff24460` (= `TICK_OFFSET_MS`) appears in 16 literal pools, `mp_hal_ticks_ms` and `ticks` among them;
    - the release readback over that image was refused.
  - **Release builds:** a release build's readback passes (the frozen-verify rp2 build in all three `test` runs). CI's `firmware-build-verify` proves the absence for every device.
- **B.7 / B.7.1 (A-3, branch 2b):**
  - Unix: `$(BUILD)/lib/mbedtls/library/ctr_drbg.o: CFLAGS += -Wno-array-bounds`, in both generated variant mks.
  - rp2: `set_source_files_properties("${MICROPY_DIR}/lib/mbedtls/library/ctr_drbg.c" PROPERTIES COMPILE_OPTIONS "-Wno-array-bounds")`, in the board cmake.
  - Confirmed in the real rp2 build: `flags.make` lists `# Custom options: …/lib/mbedtls/library/ctr_drbg.c.o_OPTIONS = -Wno-array-bounds` for that one object, and its `build.make` rule appends the flag after `$(C_FLAGS)`.
  - Reason line as written: "not yet re-checked on a GCC >= 14 host with the pin's mbedtls 3.6.6 … (agent, 2026-10-08)". `lib/mbedtls` is v3.6.6 `0bebf8b8c` (`git describe`). Compilers here: gcc 13.3.0 and arm-none-eabi-gcc 13.2.1.
  - **B.7 host-only list:** `extmod/modlwip.o`: `-Wno-sign-compare` and `-DSOMAXCONN=2` (reasons in Deviation 3). Nothing else.
- **F.7 host-lwIP rows:**
  - a loopback netif instead of CYW43;
  - 64-bit struct sizes, so pool and arena thresholds differ from rp2's; `MEM_ALIGNMENT` 8 against 4;
  - `IPV6_FRAG_COPYHEADER` 1 (rp2 0);
  - lwIP is driven from `MICROPY_INTERNAL_EVENT_HOOK` (`mp_event_handle_nowait()`, on every `mp_event_wait_ms()`), not PendSV;
  - `LWIP_PLATFORM_ASSERT` aborts (rp2's is a no-op); `LWIP_RAND()` is libc `rand()`;
  - modlwip.o is built with `-Wno-sign-compare` and `SOMAXCONN=2`, so the default `listen()` backlog is 2, as on rp2;
  - lwIP is not started at boot (the Unix port has no boot hook): tests call `lwip.reset()` first. Without it every socket fails with `OSError: [Errno 12] ENOMEM`, seen on the real binary;
  - the loopback netif copies each sent packet into the lwIP arena (S's measurement and numbers).
  - Row 14 "every Unix build" and the two-pcbs row are S's and D's own items.
- **Part N:** O adds, renames and withdraws no tag. `tool.preprocess_timeout_s = 120` (`micropython_overrides.py`, tag unchanged) now bounds four proofs: lwIP's `-E`, the tick `-E`, the kbd `make …/unix_mphal.pp`, and the host runtime probe (which sleeps 2.5 s). Its row's text should say so.
- **The S603 reason for T's `pyproject.toml`, `toolchain/micropython_overrides.py`:**
  > S603: the overrides' post-build proofs run the preprocessor (`-E`, with the argv CMake recorded in the real build's flags.make), `make <build>/unix_mphal.pp` with the build's own make variables (`make` resolved on the build's PATH), and the built host binary's runtime probe; every argv comes from repo constants and the build's own recorded flags.

## Facts for E

- CLAUDE.md: three Unix binaries. build-lwip runs the firmware's patched modlwip.c over loopback lwIP, with the two modlwip.o flags and `IPV6_FRAG_COPYHEADER`.
- The mbedtls flag is no longer a make-line constant: it is one generated rule per target, scoped to `ctr_drbg.c` (A-3).
- BACKLOG chroot paragraph:
  - `micropython_overrides.py` resolves and screens every path, empties each override directory before writing, and proves `unix_kbd_intr` in every Unix binary.
  - It gains `modlwip_eagain` (a patched copy proven in every rp2 image), the host lwIP build (proven to run lwIP's timers), and the test-only tick-offset override that a release build refuses.
  - The GCC ≥ 14 leg decides the mbedtls flag.
- HEAP_FRAGMENTATION and README: the three build flavours, as T lands them.

## For the lead

- **Allow-lists:** O adds no line. `_decision_vocab_allowlist.txt:593` (the `SPARE_TCP_PCBS` comment) still matches, unchanged. No citation allow-list line for my files.
- **Any-baseline (A-15):** the host pass is clean without `[mypy-test_micropython_overrides]` (checked with a scratch ini). The only error left is T's `setup_toolchain.py:514`. T can drop the section from `host_typecheck.ini`; this is U24's part landed early.
- **New raises,** all `OverrideError`, each named:
  - path character;
  - a repeated or misplaced anchor (`_count_once`, `_require_in_order`);
  - modlwip outside the extmod source list; a missing version define;
  - host `tcp_out.c` missing;
  - the kbd `.pp` checks (sentinel, define, handler), `make` missing, failed, hung, or BUILD mismatched;
  - the modlwip readback (no rule, original compiled, object missing or empty, layout changed);
  - the host readback (no `.P`, original or other source, the socket not being modlwip, timers not survived, binary missing or hung);
  - the tick anchor; the tick readback (unreadable answer, a release build carrying it, a test build missing it).
- **Cross-lane red** until T's `board=board` (in `audit/u21-t` 5b6dc1b) merges:
  - `tests_scripts/test_micropython_overrides.py::test_build_firmware_applies_the_tick_override_only_for_the_test_image_and_proves_every_build[test]`, which fails with "TypeError: apply_tick_offset_override() missing 1 required keyword-only argument: 'board'";
  - host mypy `toolchain/setup_toolchain.py:514:21: error: Missing named argument "board"`.
- **Still red on the tree:** `test_tunables_register.py` (5 `tool.*` rows owed by D).
- **New public names for T:** `MODLWIP_COPY_NAME = "modlwip.c"` (T hardcodes `"modlwip.c"`), and `TICK_OFFSET_BUILD_SUFFIX`, which replaces O1's `TICK_OFFSET_BUILD_DIR_NAME`.
- **Lane T finding** (`setup_toolchain.py`): `build_firmware()` labels every build that has a `frozen_manifest` as "with the frozen verification module (build-only check)", including device builds through `build_firmware.py`. This is cosmetic and was already there at HEAD.

## Tests

- **L0 `tests_scripts/test_micropython_overrides.py`** (pytest, CPython, so one GC stage does not apply):
  - before: 127 cases, 1.12 s wall at `nice -n 19` (at f76385a);
  - after: 256 cases, 255 passed plus the one cross-lane red, 2.36-2.66 s wall over three runs.
- **Seen failing first.** The final test file was run against older modules:
  - the base module (f76385a): 130 failed, 117 passed. Every new case failed except three guards that read T's and S's files (`test_a_setup_run_builds_every_build_flavour`, `test_the_shell_side_looks_for_every_build_flavour_where_it_is_built`, the renamed floor test);
  - the O1 module (b4b6640): 11 failed;
  - the O2 module (e20dd49): only the cross-lane red failed.
  - Each fix was seen failing before it was written:
    - the `.c.o` readback case (the same message as the lead's base build);
    - the per-board tick case (TypeError);
    - the host-flags pin;
    - the 6 timer-probe cases, then the real build-lwip (exit -6, the ip6_frag assertion);
    - the COPYHEADER placement case;
    - the stale `.pp` case and the 5 stale-directory cases.
- **Whole-tree checks**, each green before every commit: ruff (my two files and `toolchain/`); host mypy (only T's line); `test_decision_vocabulary`, `test_citations`, `test_comment_block_cap`, `test_legacy_paths`, `test_import_placement`, `test_code_conventions`, `test_host_annotations`, `test_tool_help`, `test_lint_ceilings`, `test_mypy_any_baseline`.
  - `test_tunables_register` is red only on D's 5 rows.
  - The main mypy pass, no-args and `src tests tests_hardware/device_scripts`, was clean at O1. My files are not in it.
- **During the lead's shared-toolchain incident**, my one read of /root/pico-toolchain was this L0 file: 135 passed in the window, and 135 passed again on re-run (already reported).

## Runs (all on my private `u21tc-o`, under the flock at `-j2` and `nice -n 19`, each entered in RUNS.md; every one exited)

| start-end (UTC) | pid | what | exit | log |
|---|---|---|---|---|
| 17:06:40-17:06:43 | fg | `cp -a u21tc-base u21tc-o` | 0 | - |
| 17:07:05-17:09:37 | 6159 | `setup_toolchain.py test` | **1** (host build: 8 × `-Wsign-compare`, SOMAXCONN) | `u21/o_test_run1.log` |
| 17:11:31-17:11:56 | 25710 | `make -k` host flavour with the two flags | 0 (no diagnostic) | `u21/o_lwip_probe1.log` |
| 17:12:23-17:15:05 | 30921 | `setup_toolchain.py test` | 0 | `u21/o_test_run2.log` |
| 17:15:34-17:15:36 | fg | the four readbacks on the real artifacts, plus two planted misses | 0 | - |
| 17:30:33-17:30:34 | fg | the timer probe on the O2 build-lwip | **1** (seen failing, -6) | - |
| 17:31:07-17:33:30 | 10616 | `st.build_unix_lwip_port()` with COPYHEADER | 0 | `u21/o_build_lwip1.log` |
| 17:36:11-17:40:07 | 2863 | `dev` tick-offset image plus release refusal | 0 | `u21/o_tick_dev1.log` |
| 17:40 | fg | `arm-none-eabi-objdump -d` of the tick image | 0 | `scratchpad/u21o_tick/dis.txt` |
| 17:42:42-17:51:50 | 12238 | `setup_toolchain.py test`, final module | 0 (548 s including the flock wait; record `input_sha256` = the committed module) | `u21/o_test_run3.log` |

No process of mine is left. u21tc-o (703 MB) is kept for the lead and holds `build-RPI_PICO_W-tickoffset`.

## Files the lead must run

- `tests_scripts/test_micropython_overrides.py`: green once T's `board=` lands.
- On the merged tree: `test_setup_toolchain_env.py` and `test_build_firmware.py` (they import my module), `test_tunables_register.py` (after D), the host mypy pass, and a `setup_toolchain.py test` on the rebuilt base (record and readbacks).

## Silent-failure scan (both passes, my two files; tooling modes first)

| # | class | mode | finding | covered by |
|---|---|---|---|---|
| 1 | 6 | re-run over a dirty toolchain | Each override wrote into existing directories, so a file an older generator left was still compiled (a variant's `*.c`) or found first (the BEFORE include dirs). | **new, fixed at U21** (`c91676c`), with 5 L0 cases |
| 2 | 3/4 | run killed mid-way (a readback cut off) | A `.pp` left behind could pass a later `make` that produced nothing. | **new, fixed at U21** (`c91676c`), with an L0 case |
| 3 | 3 | lwIP host instrument, a lwIP timer tick | The binary aborted on the first IPv6 reassembly tick, and the readback never ran the timers. | S's finding; **fixed at U21** (`9314738`) |
| 4 | 4 | host binary start | Without `lwip.reset()` every socket fails with `ENOMEM`: loud, but it reads as memory pressure. | inherently loud; F.7 row for D. An option, not taken during S's calibration: a constructor that calls `lwip_init()`, as rp2's `main.c:173` does at boot |
| 5 | 5 | send path under EAGAIN | Retries are a cooperative busy wait until the peer ACKs, bounded by the connection's own timeout. | known cost: S's hammer (A.U21.13) and phase C (A.U21.14, E's owed row) |
| 6 | 7 | the tick image's output path | `build_firmware.py`'s default output name would carry a tick image as if it were a release. No U21 path makes one; the image itself carries no marker. | U27 (M.SCR.067 build info, M.SCR.074 runner); every rp2 build's readback refuses it as a release build meanwhile |
| 7 | — | run killed mid-way (apply, tick build) | A partial generated file is rewritten by the next apply (now from empty), and every build applies first. A partial tick build dir is removed by the next tick build, and release builds never use it. | inherently safe |
| 8 | — | concurrent second run | `_fresh_dir` makes a concurrent apply more destructive. | T's per-directory lock (M.TOOL.062); L0 never applies into a real toolchain |
| 9 | — | offline run, stalled mirror, stale record, bench bridge | None of these touches my code. The record is T's. | n/a |
| 10 | — | blocking sockets | They keep the 10 s loop, past the 8 388 ms WDT. | no `src/` site (asyncio streams are non-blocking, `extmod/asyncio/stream.py:172`; UDP otherwise); B.14.4 says so |
| 11 | — | release build carrying the tick offset | Refused after every build; CI proves it per device. | M.TOOL.055/.080 (landed) |

Modes checked with no finding: boot/first build, a layout change (every readback fails loudly by name), hangs (every subprocess is bounded by `_PREPROCESS_TIMEOUT_S`, which kills its child), and the memory gate (no `MemoryError` or "memory allocation failed" text in any output).
