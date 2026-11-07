# U21 lane S: final report

Lane S is complete on branch `audit/u21-s` at HEAD **a2d7ee2**. Every lane-S step is applied, and every L0 file and the lwIP hammer are green at both GC stages. Two checks are still red on the merged tree, both owned by other lanes:
- test_tunables_register: 12 Part N rows are owed by D.
- The host mypy pass: one error at `toolchain/setup_toolchain.py:514`, which T or O must fix.

The lane's commits, none pushed:
- 8023b98: the WIP S1 commit.
- 0f76444, f88bba9, 982cc52 and a2d7ee2: the work after the WIP.
- Merges of the API base: ab5f775 (76b6990), 3efc446 (2f7543c) and 969fb55 (5797124, which brings O3).

Nothing under `ext/`, `legacy/`, `arduino/`, `tests_hardware/` or `/root/pico-toolchain` was written.

## Step table

| Step | M-id | State | Note |
|---|---|---|---|
| 4 | M.TOOL.001 | applied (U21 stage) | The `key:` hashes `toolchain/micropython_overrides.py` as well. The comment is A.U21.07's sentence. actionlint and zizmor `--offline` are clean. |
| 15a | M.SCR.036 | applied (U21 stage) | `lwip_bin="$unix_dir/build-lwip/micropython"` and `toolchain_record`. `setup` runs on a missing or wrong-variant binary, a missing `toolchain-record.json`, or (plain run only) an lwIP binary that is missing or not `plain`. Each condition is checked again after setup. Message: "the Unix ports". |
| 15b | M.SCR.040 | applied (U21 stage) | `run_test_file <test_file> <status_file> [<binary>]`, default `$micropython_bin` (A-11). |
| 15c | M.SCR.041 | applied (U21 stage) | `tests/lwip_host/test_*.py` are dispatched last, each on `$lwip_bin`. They are not run under `--coverage`. |
| 15d | M.SCR.045 | applied (U21 stage); L1 already landed | Under `--coverage` each lwIP file is listed under `Skipped:` "not run under --coverage (the plain pass runs them)". L1 counting needed no change: the summary loop already puts every non-twin file in L1 (`test.sh:574-579`). |
| 15e | M.SCR.065 | applied (U21 stage) | `--toolchain-dir` gets `.expanduser().resolve()`. `st.toolchain_lock()` is held from before staging and the mpy-cross wipe until the copy. A toolchain without its record is refused with A.U21.22's message. The record line is printed and never prints None. |
| 27 | M.SCR.027 | applied (U21 stage) | A marked stub block: `typings/.stub-spec`, a wipe on a changed or missing spec, exactly one board dist-info, and the print line. Also (scan fix S-9) the record is dropped before each install. |
| 47 | M.TEST_UNIT.001 | applied, with deviations 1-6 | `tests/lwip_host/test_modlwip_eagain.py`: seven tests and seven `l1.lwip_host_*` tags, measured on the real build-lwip. |
| 60 | M.TSC.032 | applied (U21 parts c, d) | Covers a dir without a record, a relative dir resolved with the lock spanning the build, lock contention naming the holder's pid, and an honest record line for a null built_ref. |
| 77 | M.TSC.135 | applied (U21 stage) | Rebuild-condition regexes plus behavioural probe cases on stubs; the binary argument; dispatch order and binary; no lwIP under `--coverage`; the `Skipped:` line; A-12's basename guard (now also non-empty). |
| 79 | M.TSC.221 | applied (U21 stage) | Stub-block cases: a spec change wipes, an unchanged spec keeps, none or two board dist-infos fail, the print and the record, and a failed install leaves no record. |
| OF-41 | open finding | applied, closes | Every output goes to `<name>.tmp` and reaches its name by `os.replace`. A failed write gives one error line and leaves no `.tmp`. Proven structurally: the test records every write-mode open and `os.replace`. |

## Tests seen failing first, and guards

- **test_typecheck_sh.py** (+8): seven failed on the base.
  - The block cases failed because the markers were missing.
  - The whole-script case exited 0 on a missing dist-info.
  - `test_an_unchanged_stub_spec_keeps_the_tree` is a guard: it passes on the base's behaviour.
  - `test_an_install_that_fails_leaves_no_record...` failed before the `rm -f`.
- **test_generate_sensortask_modules.py** (+2): both failed on the base. Final names were opened directly, and a write OSError escaped as a traceback.
- **test_build_firmware.py** (+4):
  - The (c) case failed on the base with a traceback: the base went on to build mpy-cross in a toolchain with no record.
  - The relative-dir case failed on a copy of the base script: the relative path reached `st.build_firmware` unresolved, with no lock taken.
  - The null built_ref case printed "MicroPython None".
  - The lock-contention case was red until T1 merged (AttributeError), then green.
- **test_test_sh.py** (+15): eleven failed on the base. Five are guards:
  - a complete toolchain runs no setup (×2);
  - coverage does not need build-lwip;
  - a failing lwIP file fails L1;
  - the basename check. It now also asserts the set is non-empty, which would fail on the base.

## L0 wall times at nice 19 (before → after)

| File | Before | After | Host load (1-min) after |
|---|---|---|---|
| test_test_sh | 27.7 s | 24.2 s | 1.8 |
| test_build_firmware | 16.6 s | 15.1 s | 2.0 |
| test_typecheck_sh | 2.5 s | 0.7 s | 2.0 |
| test_generate_sensortask_modules | 5.6 s | 7.1 s | 1.9 |

The before and after runs had different host loads.

## The lwIP host file (L1, build-lwip sha bc36a48f, rebuilt in u21tc-s from 969fb55 by `build_unix_lwip_port()`)

- 7/7 at the e stage and 7/7 at the f stage in every run on the real binary: 6 e runs and 6 f runs, plus test.sh's own `run_test_file` once per stage.
- Wall time is 23.7-24.4 s per run at both stages, against the 240 s per-file limit.
- No MemoryError or "memory allocation failed" in any log. Not run under settrace (excluded under `--coverage` by design).
- Per test, measured quiet: (1) 0.44 s, (2) 0.10 s, (3) 0.10 s, (4) 0.35 s, (5) 0.95 s, (6) 16.8 s, (7) 5.2 s.

## Tunables for D (Part N rows)

All sites are `tests/lwip_host/test_modlwip_eagain.py`, literal on the line below each tag. Each basis reads "estimated (agent, a2d7ee2) - measurement owed: <figure> on CI at TEST_PARALLELISM=4 and on the bench Pi4". "Loaded" means load 4.1-4.4 with lane T's six-device firmware build holding the toolchain flock (17:38-17:49). "Quiet" means load 0.8-1.0 with no flock holder (18:01-18:03). All figures are from the real build-lwip at both GC stages.

| id | value | measured worst (loaded / quiet) | why the value |
|---|---|---|---|
| `l1.lwip_host_write_bound_ms` | 250 | slowest write 0.16 / 0.06 ms | The unpatched loop holds a write 10 000 ms (control: 10 000-10 065 ms). |
| `l1.lwip_host_connect_bound_ms` | 200 | slowest handshake 1.19 / 1.48 ms, 117 pairs per run | It is also the wait that marks the pool as exhausted. |
| `l1.lwip_host_recovery_s` | 15 | slowest recovery 126.6 / 120.1 ms | Covers modlwip's 10 s close-abort, which was never reached here. |
| `l1.lwip_host_rounds` | 20 | 20 rounds take 16.8 s at either load | Capacity was identical every round (10 400 B). |
| `l1.lwip_host_spin_rounds` | 1000 | test (7) takes 5.1-5.2 s | |
| `l1.lwip_host_spin_round_max_us` | 20000 | slowest round 8536 / 5896 µs | An unpatched round sleeps at least 50 000 µs. Rounds that ran a collection are left out and counted (1 per run at the 32768 stage). |
| `l1.lwip_host_spin_round_alloc_max_b` | 64 | 32 B in every run | One 32-B GC block (64-bit host) for the memoryview slice drain() makes each round. |

## Sensitivity run (one time, as A.U21.13 asks; recorded here, never committed)

`build-lwip-control` was built at 17:52 in u21tc-s, under the flock. It used the installer's own path with the EAGAIN insertion disabled in-process (`u21/s_probe/build_control.py`). The build asserted that the control copy lacks the block and compiles its own copy. It was run at the e stage (load 1.5-2.6, no flock holder), then deleted.

| Test | Patched build | Control build | What shows the patched block was reached |
|---|---|---|---|
| (1) | bounded writes; EAGAIN at the last connection's first write | **red**: one write took 10 065 ms | timing |
| (4) | every writing phase ends in EAGAIN | **red**: one write took 10 000 ms | timing |
| (5) | green | **red**: one write took 10 001 ms | timing |
| (6) | green | **red**: one write took 10 000 ms | timing |
| (2) | EAGAIN at exactly 32 × 16 = 512 B, POLLOUT set | **red**: no EAGAIN at 512 B; the edge came after 1 200 B as ENOMEM (each ERR_MEM round slept 50 ms, ACKs freed the queue and the writes went on) | the different outcome |
| (3) | EAGAIN at exactly 48 segments | **red**: no EAGAIN in 51 one-byte segments | the different outcome |
| (7) | the spin holds for every round | **red**: as (2), it never reached the queue-limit spin | the different outcome |

The control run took 41.4 s and ended 0/7. Every patched edge is also checked with one timeout-0 `POLLOUT` readiness check. It is set at each edge, which proves `tcp_sndbuf() > 0`: the patched ERR_MEM branch, not the send-buffer edge.

## Deviations

1. **Loads use whole-MSS writes.** The test (1) loads and the load/drain cycle of (5) and (6) write 800-B pieces, not 256-B ones.
   - The cause is a host-only behaviour: the loopback netif copies every sent packet into the 12 000-B arena (netif_loop_output, PBUF_RAM).
   - So at the arena edge, a 256-B write varied from run to run between three outcomes: accepted, ENOMEM from tcp_output (with its bytes queued), and EAGAIN.
   - With whole-MSS writes, every edge is the zero-window EAGAIN, and every later write into the full arena EAGAINs before anything is sent. That makes every write's outcome exact, as you asked.
2. **(3) uses one-byte NODELAY segments**, round robin over three connections, instead of MSS pieces. With MSS pieces the arena runs out after about 13 segments, far short of the 48-segment pool.
3. **(4) has no separate non-reading loader.** It writes in phases: the reader holds off until the window closes and the arena edge comes (EAGAIN), then drains everything. With a loader, every edge ended in ENOMEM on this host.
4. **One listener serves the whole file and is never closed.** Upstream's listener close trips lwIP's LISTEN-state assert (finding S-1). The file header says so in 3 lines.
5. **(7) leaves rounds that ran a collection out of both maxima, and counts them.** Without that, one GC pause inside a round at the 32768 stage reached 22 ms once, on the interim binary.
6. **Exactness:** every accepted write is asserted to take its whole piece, and every edge kind is asserted for its case. ENOMEM is never accepted in place of EAGAIN.
7. **No whole `scripts/test.sh` run.** The script has no single-file mode. The test.sh change is proven by single-file and `-k` runs of test_test_sh.py, and by running test.sh's own `_flag_memory_errors` and `run_test_file` on the real lwIP file and build-lwip at both stages: PASS, attempt 1/3, no markers.
8. **No L0 case for the action's cache key.** No lane-S test reads the action; A.U28.08 owns that check at U28.
9. **typecheck.sh drops the record before each install** (scan fix S-9). This goes beyond A.U21.04's text.
10. **The test.sh header** said `setup` "verifies all four artifacts". That sentence is false after U21 and now reads "builds and verifies every artifact".
11. **D.15 member order** is applied to the new hammer (AST-verified pure reorder) and to `_generate_sensortask_modules.py`. The existing tests_scripts files keep their sectional helper layout; D.15's check covers only src/.

## Facts owed to other lanes

**For D (SPEC):**
- **The stub record.**
  - `typings/.stub-spec`: line 1 is the spec (`micropython-rp2-rpi_pico_w-stubs==<X.Y.Z>.*`), line 2 the resolved board-stub version. It is dropped before each install and written after the exactly-one-dist-info check. A changed or missing record wipes `typings/` first.
  - Print line: `== MicroPython stubs: <v> (for firmware <X.Y.Z>)`.
  - Error: `error: found N stub dist-info directories (typings/micropython_rp2_rpi_pico_w_stubs-*.dist-info), expected exactly one - remove typings/ and re-run`.
- **test.sh.**
  - An lwIP job's tag is its basename, its level L1, and its `--coverage` Skipped reason is "not run under --coverage (the plain pass runs them)".
  - `run_test_file <test_file> <status_file> [<binary>]`.
  - Probe lines: `== no toolchain record at <path> - rebuilding the Unix ports` and `== the lwIP host build <bin> is missing or not the 'plain' variant - rebuilding the Unix ports`, each followed by a matching `error:` if setup leaves it so.
- **build_firmware.py messages.**
  - Lock: T's message, printed as `FAILED: another setup or firmware build (pid N) is using <dir> - wait for it to finish, or use another --toolchain-dir`.
  - No record: `error: the toolchain at <dir> is incomplete or predates the build record - run \`uv run toolchain/setup_toolchain.py setup\` first`.
  - Record line: `== Toolchain: MicroPython <built_ref> (<commit>), recorded in <dir>/toolchain-record.json`. With a null built_ref it names `<pinned_ref> as pinned (built by \`test\`, ref not recorded)`.
- **The generator:** writes through rename; its error is `error: cannot write <file>: <strerror>`.
- **Host lwIP facts (F.7 / B.14.4):**
  - The host admits 4 connection pairs. MEMP_NUM_TCP_PCB is 9 and each pair takes two pcbs, since both ends are in-process; that is about half of rp2's connections.
  - A fresh connection writes 10 400 B (13 MSS) to a non-reading peer before EAGAIN.
  - The queue-limit edge is 32 segments (TCP_SND_QUEUELEN = (4·6400+799)/800). The segment-pool edge is 48.
  - Host divergences:
    - the loopback copy draws on the arena, so a write can get ENOMEM from tcp_output before EAGAIN;
    - IPV6_FRAG_COPYHEADER 1 is needed on 64-bit (O3);
    - lwIP asserts abort, so a listener close aborts;
    - select's timeout-0 poll on a non-fd object sleeps 1 ms on the Unix port (`poll(NULL, 0, 1)`, POSIX optimisations), so a host spin round includes that sleep;
    - the GC block is 32 B (rp2: 16 B).

**For E:** the BACKLOG chroot paragraph's lane-S clauses (plan §7) hold as written. The cache key also hashes `micropython_overrides.py`.

**For the lead:**
- No allow-list lines are retired or added: citations and decision vocabulary are green without edits.
- No Any-baseline lines and no new raises.
- Still red on the merged tree:
  - `test_tunables_register.py`: 7 `l1.lwip_host_*` plus 5 `tool.*` rows, owed by D.
  - Host mypy: `toolchain/setup_toolchain.py:514: Missing named argument "board" for "apply_tick_offset_override"`. This is T's caller against O2's keyword.

## Silent-failure scan (lane S's files, tooling modes first)

| # | Site | Class / mode | Status |
|---|---|---|---|
| S-1 | upstream `extmod/modlwip.c:1680-1682` (close of a listening socket), rp2 firmware | 1 (lwIP's assert is `{ assert(1); }` on rp2, `ports/rp2/lwip_inc/arch/cc.h:6`) leading to silent memory corruption / controlled shutdown (the webserver's listener close) and a GC finaliser closing a dropped listener | **new, registered by the lead.** See the detail below. |
| S-2 | upstream `lwip_tcp_send()` | 4 (a "failed" write whose bytes are queued) / send path at the arena edge | **new.** See the detail below. |
| S-3 | host build: IPV6_FRAG_COPYHEADER | build-lwip aborted about 1 s after `lwip.reset()` (ip6_frag.c:118) | covered: O3 (9314738) |
| S-4 | host loopback arena copies | F.7 fact | covered: D's F.7 row; the hammer's loads use whole-MSS writes |
| S-5 | `scripts/test.sh`, `scripts/build_firmware.py`: the record is checked for presence only | 3 / a stale record (a toolchain built from older overrides runs the suite on stale Unix binaries) | **partly covered.** A.U21.07 says `input_sha256` detects this, but nothing compares it. Firmware images are not affected: the overrides are re-applied on every build. Proposal for U27's `unix_port_ensure`: compare `input_sha256` with the three files. |
| S-6 | `typecheck.sh`'s `uv pip install`, test.sh's `uv run`s | 5 / a stalled mirror holds the run until CI's timeout-minutes | **new**, for U27 (stub pins) or U28 (budgets) |
| S-7 | two `typecheck.sh` runs in one worktree | concurrent second run: one wipes `typings/` under the other's mypy (visible, transient) | covered procedurally by CONCURRENCY rule 4 |
| S-8 | `build_firmware.py` `shutil.copy(uf2, output)` | 2/4 / a kill mid-copy leaves a truncated image | covered at U27 (M.SCR.067 (1), M.TSC.032 (1), SF-M4-07) |
| S-9 | `typecheck.sh` `.stub-spec` | 6 / a failed or killed install kept the record of a complete one | **fixed here** (dropped before the install, written after), with a test |
| S-10 | generator writes in place | 3 / re-run over a tree in use (OF-41) | **fixed here** |
| S-11 | empty `tests/lwip_host/` | 3 / a lost file would silently thin L1 | **fixed here** (asserted non-empty) |
| S-12 | missing record on the shared or default toolchain dir | a post-U21 `scripts/test.sh` runs `setup` there (visible, but it writes the shared toolchain) | covered: A-21 (the lead writes the record before any post-U21 gate) and CI's cold cache by design. My tests set HOME to tmp_path and exit before the probe; no lane-S test can reach it. |

**S-1 in detail.**
- Facts from the rp2 build's own flags (cmake configure plus a probe compile in u21tc-s):
  - `sizeof(struct tcp_pcb_listen)` = 72, and the listen pool's element stride is 72 (MEMP_SIZE 0, MEMP_MEM_MALLOC 0), 8 elements.
  - `offsetof(struct tcp_pcb, recv)` = 172 and `errf` = 184.
- memp_init builds the free list in reverse (`lib/lwip/src/core/memp.c:194-196`), so the first listener gets element 7. Its close stores NULL 100 and 112 bytes past the listen pool's end.
- In the linked image, that is the TCP_PCB pool's element 0, at offsets 96 (`rtseq`) and 108 (`lastack`). The image is build-listenprobe: release flags, default manifest; `memp_memory_TCP_PCB_LISTEN_base` is at 0x2000d082 (size 0x243) and `memp_memory_TCP_PCB_base` at 0x2000d2c5 (size 0x6e7).
- Element 0 is the last pcb handed out, so a live connection is hit only while all 9 pcbs are in use. Otherwise the stores land in free memory, which tcp_alloc clears with memset.
- A listener at element i ≤ 5 instead hits element i+2's `remote_ip` (in-element offsets 28 and 40). That is never the free-list link (offset 0).
- A device image's own map should confirm the adjacency: `arm-none-eabi-nm -n firmware.elf | grep memp_memory_TCP_PCB`.
- Host reproduction: `scratchpad/u21/s_listener_close_repro.py` prints `lwIP assertion failed: invalid socket state for err callback (../../lib/lwip/src/core/tcp.c:2070)` and exits with 134.

**S-2 in detail.**
- `lwip_tcp_send()` returns ENOMEM when `tcp_output_nagle()` fails after `tcp_write()` has already queued the bytes.
- Seen on the host: a write raised ENOMEM, and its 256 bytes still arrived (`u21/s_probe/enomem_queued.py`).
- On rp2, tcp_output can fail with ERR_MEM where a pure ACK or an ARP-queued copy needs arena. This is not reproduced.
- A caller that retries would duplicate the bytes. asyncio's drain() raises OSError instead, so Microdot drops the connection.

**Modes checked with no finding:**
- The generator killed mid-way: inherently safe. Each file is whole, and `.tmp` leftovers are never read and are rewritten by the next run.
- `build_firmware.py` killed: the OS releases the lock, and the next build wipes mpy-cross.
- An offline run: every failure is visible.
- Re-run over a dirty toolchain: every build-dir is wiped first by `_build_unix_variant()`.
- The tick-offset refusal: not lane S's files.

## Runs started (all entered in `u21/RUNS.md`; every one has exited)

- `cp -a u21tc-base u21tc-s`: rc 0.
- The interim private `build-lwip-copyheader`: rc 0, 27 s; deleted afterwards. The hammer runs on it were for calibration only, and none of their numbers are used above.
- `build_unix_lwip_port()` on u21tc-s: rc 0, 222 s including the flock wait.
- Hammer runs: first_e (rc 134, the IPv6 assert), run2_e (rc 134, the listener assert), then run3-run6 on the interim build. On the real binary, real_e/f 1-4, final_loaded_e/f and final_quiet_e/f all rc 0.
- The calibration runner: loaded and quiet, each at e and f, all rc 0.
- test.sh's `run_test_file` on the lwIP file: e and f, rc 0.
- The control build: rc 0, deleted afterwards. The control run: rc 1, 0/7 as expected.
- rp2 configure plus probe: rc 0. The firmware link for the map: rc 1 (a probe include), rc 2 (awk), then rc 0; build dir deleted afterwards. The `pcb_fields` compile: rc 0 (entered in RUNS.md after it ran).
- My flock-watcher (background) never exited, because its pgrep matched its own command line. I killed it by its pid at 18:00:29 (recorded).
- `ps` shows no lane-S process. `u21tc-s` remains, about 0.7 GB, for the lead to delete at the close.

## Files the lead must run on the merged tree

- `tests_scripts/test_test_sh.py`, `test_build_firmware.py`, `test_typecheck_sh.py` and `test_generate_sensortask_modules.py`.
- `tests/lwip_host/test_modlwip_eagain.py`, on build-lwip at both GC stages, through `scripts/test.sh` (it is dispatched last, in L1).
- `test_micropython_overrides.py` (it reads test.sh's literal binary paths), `test_digital_twin_boot_contiguity.py -k same_interpreter_settings` and `test_memory_error_gate_agreement.py`.
- The whole-tree checks.
- shellcheck on `scripts/test.sh` and `scripts/typecheck.sh`; actionlint and zizmor `--offline` on `.github/`.
- `scripts/test.sh --coverage`, to see the `Skipped:` line.

## Files outside my set

None edited.
- Read only: `/root/pico-toolchain`'s build-standard binary, for test_test_sh's probes and one compile check.
- My own scratch probes are under `scratchpad/u21/s_probe/` and `scratchpad/u21s_runs/`.
