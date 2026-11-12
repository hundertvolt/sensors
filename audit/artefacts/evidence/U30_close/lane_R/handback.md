U30 lane R FINAL

Commit a16fafd on audit/u30-r (base 64cd620, not pushed). Paired timing ran on 426c683. a16fafd is that commit amended, and the amend changes only the timing sentence in SPECIFICATION.md B.14.6. S/wt-u30r2 is still there, detached at 426c683; it is yours to remove.

**The form I chose:** a plain `#define MICROPY_ALLOC_GC_STACK_SIZE (1024)` at the end of the generated Unix variant header. `_unix_variant_header()` adds it after `_unix_kbd_intr_header()`. `apply_unix_kbd_intr_override()` writes that header for build-standard and build-settrace, and `_lwip_host_files()` starts build-lwip's header from it. The value is `UNIX_GC_STACK_ENTRIES` in its own `unix_gc_stack` section of toolchain/micropython_overrides.py, tagged `# @tunable l1.unix_gc_stack_entries = 1024`. Why this form:
- upstream's default is `#ifndef`-guarded, so this is the only definition any build reaches, and a definition upstream might add later would warn, which fails the build;
- it needs no make variable: VARIANT_DIR belongs to the SIGINT override and the lwIP host build, and CFLAGS_EXTRA to settrace's `-D`, so a `-D` would break the one-owner rule in `_merge_make_vars()`;
- it needs no override directory, so CURRENT_OVERRIDE_DIRS is unchanged;
- the firmware never reads the header.

`verify_unix_gc_stack_anchor()` checks the anchors in order before anything is written: the guarded default (py/mpconfig.h:255-257), the array (py/mpstate.h:138), and the overflow path (py/gc.c:574-582, :621-640). Both rig applies call it.

**The value: 1024.** The lead's finding re-checked: 55 children cost 514 µs per collection at 16M and 99 µs at 4M on stock, 2 µs at 1024; 30 children do not overflow. Heap maps after the churn are identical apart from the base address. 1024 against 4096 at 32768, paired, trees swapped, 2 rounds: voc_algorithm 6.38 against 6.28 s (−1.6 %), scd30 28.72 against 28.71 (0 %), webserver 7.13 against 6.97 (−2.3 %). That is under 10 %, so I kept 1024 (agent, 2026-10-20).

**The readback.** `verify_unix_gc_stack_in_build()` re-preprocesses unix_mphal.c with the build's own make variables, through a `_unix_mphal_pp()` it shares with the SIGINT readback. It requires that `mp_state_mem_t` declares exactly `gc_block_stack[(1024)]`, which is the array gc.c marks with as the build's own translation unit sees it. `_build_unix_variant()` runs it after the SIGINT readback, so all three builds get it.
- Real scratch builds of standard, 4096, settrace and lwip all pass.
- It fails by name, citing `['(64)']`, on the real standard variant fed against my build, and on a scratch build of the base code. It also refuses the 4096 build when 1024 is expected.

**Paired timing, stock against 1024.** Both started together, 2 rounds with the trees swapped, means in seconds. Every result was identical between the binaries, with 0 `MemoryError` and 0 "memory allocation failed" in every run.

| file | -1 stock → 1024 | 32768 stock → 1024 |
|---|---|---|
| voc_algorithm | 2.50 → 2.65 | 20.04 → 6.34 |
| scd30 | 22.33 → 22.26 | 43.04 → 28.77 |
| webserver | 4.46 → 4.36 | 12.36 → 7.18 |
| framing_codecs | 0.66 → 0.70 | 1.26 → 0.72 |
| uart_link | 68.89 → 66.75 | 79.40 → 70.33 |
| bus_hazard | 3.23 → 3.25 | 4.87 → 3.71 |

- **uart_link failed on its first pass:** wt-u30r's build/generated_src was stale because the generator's stamp hashes micropython_overrides.py and I had changed that file. Generated outputs were identical apart from `_BUILD_DATE`. I ran rebuild.sh and re-paired it; the table shows the re-run.
- **Settrace,** framing_codecs through tests/_coverage_runner.py: 2 pairs, then 5 alternating runs per binary. Stock 4.98±0.19 s, mine 4.72±0.15 s, coverage JSON byte-identical.

**voc_algorithm's −1 delta is noise.** 12 alternating sequential runs per binary (6 in each tree): stock 2.534±0.106 s, 1024 2.470±0.094 s, so 1024 is 0.06 s faster, under one standard deviation. Two further points:
- The stock and 1024 text sections differ in only 332 scattered bytes, displacements and gc.c's constant; no code moved.
- 1024 can never trace more than 64 does, since the marked set is the same and there are no re-scans.

The lead's earlier +0.2 s was tree and load noise.

**Part N row, written under ## R in S/u30/relay.md:** `l1.unix_gc_stack_entries` | 1024 entries | `toolchain/micropython_overrides.py` — `1024` | the header's MICROPY_ALLOC_GC_STACK_SIZE in all three builds, read back by `verify_unix_gc_stack_in_build()`; cost scales with `l1.unix_heapsize` | measured 2026-10-20 (the figures above, plus 4096 saving 1.6/0.0/2.3 %) | upstream's large-heap value (`ports/rp2/mpconfigport.h:94`); 4096 saves <3 % more (agent, 2026-10-20) | the pin moves, `l1.unix_heapsize` changes, or a file's 32768 time grows.

**Docs:**
- SPECIFICATION.md: new B.14.6, B.14's intro (five implemented, and B.14.6 writes no override directory), a new F.7 row 31, and one sentence in E.5.2.
- BACKLOG.md: a 2026-10-20 entry in the chroot list.

**Tests written first and seen failing:** 39 failures before implementation (`S/u30/laneR/seen_failing_1.txt`). These include the header test with no new line, the readback tests, and the host anchors not refusing a missing mark-stack anchor. Guards bitten in scratch copies, each failing as it should (`S/u30/laneR/bites.txt` and `bite7.txt`):
- a firmware board header carrying the define;
- `UNIX_GC_STACK_ENTRIES` set to 64;
- a no-op readback;
- the readback call dropped from `_build_unix_variant`;
- an anchor that only the code checks;
- the host header built without the mark stack;
- the define line dropped from the rig header.

**Checks:**
- test_micropython_overrides 289 passed (about 2.5 s, no base time listed);
- test_setup_toolchain_env 159, test_unix_port_sh 55, test_citations 15, test_decision_vocabulary 6, test_comment_block_cap 618, test_buildgen_validate 409;
- legacy_paths, import_placement, code_conventions, error_catalog, host_annotations, lint_ceilings, mypy_any_baseline, memory_error_gate_agreement all green;
- ruff on all eight scopes clean; host mypy pass clean (296 files); tests_hardware `--collect-only` 196/226.

**One red check:** test_tunables_register.py, `toolchain/micropython_overrides.py:162: l1.unix_gc_stack_entries is tagged but has no SPECIFICATION.md Part N row` (expected; waits on your row). Its second red line, gc.threshold_bytes's Sites listing tests/test_asy_webserver_service.py, is already red on 64cd620 (N's step 105).

**Before anyone merges a16fafd:**
- The shared toolchain then reads as stale: `_unix_port.sh check` names "stale micropython_overrides.py", and `ensure` reruns setup on /root/pico-toolchain.
- Every tree's build/generated_src becomes stale and needs rebuild.sh.
- So install the three binaries at the sync point before any lane's tree carries the commit.

**Effect per operating mode** (STA, AP, Silent, Off, USB): none. The firmware image is untouched and only the host test rig changes. Silent-failure scan of my files: no findings.

**Decisions, all (agent, 2026-10-20):**
- the header form over CFLAGS_EXTRA;
- 1024 over 4096;
- readback on the struct's array dimension;
- micropython_overrides.py left in its section order rather than D.15 order, following REGISTER.md:572's U21 precedent;
- `_KBD_INTR_PP_SOURCE` renamed to `_UNIX_MPHAL_PP_SOURCE`, since both readbacks now share it.

**Runs** (all logged in S/u21/RUNS.md, every one exited 0): the base-config build build-u30r-stock and the four lane R builds (std1024, std4096, settrace, lwip); 1024 against 4096 pairs (pid 2728); stock against 1024 pairs (6555); uart_link re-pair (9072); voc alternation (9563); settrace pair (9907); settrace alternation (10025).

**Cleanup:** all five ports/unix/build-u30r-* directories are removed by literal path, and the micropython checkout's git status is clean. Nothing of mine is running. Logs are in S/u30/laneR/.
