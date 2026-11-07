# U21 run ledger (CONCURRENCY.md binding; ps must match before each report)
| state | pid/kind | worktree | what | start (UTC) |
|---|---|---|---|---|
| done | agent | wt-u20close (read only) | U21 lane-plan agent (file-only, writes u21/lane_plan.md) | 15:49:32 |
| done (WIP 8c38f9d, 17:0x) | agent | wt-u21t | lane T (files: u21/files_T.txt; WIP phase: edits + L0 single files, no build) | 16:28:06 |
| done (WIP b4b6640, 17:0x) | agent | wt-u21o | lane O (files: u21/files_O.txt; WIP phase: edits + L0 single files, no build) | 16:28:06 |
| done (WIP 8023b98, 16:49) | agent | wt-u21s | lane S (files: u21/files_S.txt; WIP phase: edits + L0 single files, no build) | 16:28:06 |
| done (ruff clean, host mypy clean, L0 green except test_tunables_register: 5 Part N rows owed by D) | lead | wt-u21api | ruff + host mypy + 16 L0 files (nice 19, sequential) | 16:57:20 |
| done rc=1 17:02:38 (117 s; modlwip readback .obj vs .o) | lead (bg) | wt-u21api @ 76b6990 | flock+nice19: setup_toolchain.py test --toolchain-dir u21tc-base --jobs 2 > u21/base_build.log | 17:00:41 |
| done (WIP e20dd49, 17:2x) | agent | wt-u21o | lane O resumed 17:05 (O2: modlwip .o readback fix, tick board keyword, private u21tc-o test end to end) | 17:04:40 |
| done (final a1cfee1, 18:11; report u21/reports/T.md) | agent | wt-u21t | lane T resumed 17:06 (merge 76b6990, no-build parts; real builds after base) | 17:04:40 |
| done (final a2d7ee2, 18:1x; report u21/reports/S.md) | agent | wt-u21s | lane S resumed 17:06 (merge 76b6990, hammer code; runs after base) | 17:04:40 |
| done 17:06:43 | lane O (fg) | wt-u21o | cp -a u21tc-base u21tc-o (private toolchain copy, ~0.7 GB) | 17:06:40 |
| done rc=1 17:09:37 (152 s; host lwIP build: modlwip.c -Wsign-compare x8, SOMAXCONN) | 6159 (bg) | wt-u21o @ 5654ea1+uncommitted O2 | flock+nice19: PICO_TOOLCHAIN_DIR=u21tc-o setup_toolchain.py test --toolchain-dir u21tc-o --jobs 2 > u21/o_test_run1.log | 17:07:10 |
| done rc=0 17:11:56 (25 s; no diagnostic with the two modlwip.o flags) | 25710 (bg) | wt-u21o (read) | flock+nice19: make -k -j2 host lwIP flavour on u21tc-o (o_lwip_probe.py) > u21/o_lwip_probe1.log | 17:11:32 |
| done rc=0 17:15:05 (162 s; all flavours and readbacks, record written) | 30921 (bg) | wt-u21o @ 5654ea1+uncommitted O2 | flock+nice19: PICO_TOOLCHAIN_DIR=u21tc-o setup_toolchain.py test --toolchain-dir u21tc-o --jobs 2 > u21/o_test_run2.log | 17:12:24 |
| done 17:15:36 | lane O (fg) | wt-u21o (read) | flock+nice19: o_readback_check.py on u21tc-o (kbd .pp x4, host probe) | 17:15:34 |
| done rc=0 17:22:21 (176 s; 0 warnings; record written) | lead (bg) | wt-u21api @ 2f7543c | flock+nice19: setup_toolchain.py test --toolchain-dir u21tc-base --jobs 2 > u21/base_build2.log | 17:19:25 |
| done (final da6338a, 17:59; report u21/reports/O.md) | agent | wt-u21o | lane O resumed 17:17 (rest of lane on u21tc-o: dev tick image, refusal readback, final report) | 17:19:41 |
| incident | lane T test (pid 21907 tree) | /root/pico-toolchain | real setup_toolchain.py env --tier bench (accidental; -j4, outside flock); stopped by T; restored by lead 17:21:38 | 17:17:33 |
| done rc=0 17:23:40 | lane S (fg) | wt-u21s | cp -a u21tc-base u21tc-s (private toolchain copy) | 17:23:38 |
| done rc=134 wall=.220481159s 17:23:55 | lane S (fg) 29646 | wt-u21s | lwIP host run first_e (e stage, build-lwip) | 17:23:54 |
| done rc=134 wall=1.016633542s 17:25:12 | lane S (fg) 29975 | wt-u21s | lwIP host run run2_e (e stage, build-lwip) | 17:25:11 |
| done rc=0 27s 17:27:18 | lane S (fg) | wt-u21s | flock+nice19: private make -j2 build-lwip-copyheader on u21tc-s (host lwIP flavour + IPV6_FRAG_COPYHEADER 1, scratch only) > u21s_runs/build_copyheader.log | 17:26:51 |
| done rc=1 wall=15.981182300s 17:28:17 | lane S (fg) 3388 | wt-u21s | lwIP host run run3_e (e stage, build-lwip-copyheader) | 17:28:01 |
| done rc=0 wall=15.780020667s 17:29:30 | lane S (fg) 4046 | wt-u21s | lwIP host run run4_e (e stage, build-lwip-copyheader) | 17:29:14 |
| done rc=0 17:30:00 | lane T (fg) | wt-u21t | cp -a u21tc-base u21tc-t (private toolchain copy) | 17:29:56 |
| done rc=0 17:32:59 | lane T (bg) | wt-u21t @ 5b6dc1b | flock+nice19: PICO_TOOLCHAIN_DIR=u21tc-t setup_toolchain.py test --toolchain-dir u21tc-t --jobs 2 > u21t_runs/tc_test.log | 17:30:10 |
| done 17:30:34 | lane O (fg) | wt-u21o (read) | nice19: o_host_readback.py on u21tc-o build-lwip (O2 build, before COPYHEADER) | 17:30:33 |
| done rc=0 17:33:30 (143 s; build, kbd + timer-surviving host readback pass) | 10616 (bg) | wt-u21o (read) | flock+nice19 -j2: st.build_unix_lwip_port on u21tc-o (O3: COPYHEADER + timer probe) > u21/o_build_lwip1.log | 17:31:08 |
| done rc=1 wall=8.472207015s 17:32:24 | lane S (fg) 18509 | wt-u21s | lwIP host run run5_e (e stage, build-lwip-copyheader) | 17:32:15 |
| done rc=0 wall=24.063335700s 17:34:01 | lane S (fg) 31896 | wt-u21s | lwIP host run run6_e_1 (e stage, build-lwip-copyheader) | 17:33:37 |
| done rc=0 wall=24.112958572s 17:34:25 | lane S (fg) 32168 | wt-u21s | lwIP host run run6_e_2 (e stage, build-lwip-copyheader) | 17:34:01 |
| done rc=0 wall=24.454648672s 17:34:49 | lane S (fg) 32277 | wt-u21s | lwIP host run run6_e_3 (e stage, build-lwip-copyheader) | 17:34:25 |
| done rc=0 17:35:31 | lane S (fg) | wt-u21s | lwIP host calibration probe (u21/s_probe/calibrate.py, copyheader build, e stage) | 17:35:06 |
| done rc=0 wall=24.110118528s 17:36:06 | lane S (fg) 825 | wt-u21s | lwIP host run run6_f_1 (f stage, build-lwip-copyheader) | 17:35:42 |
| done rc=0 (see base_build3.log tail) | lead (bg) | wt-u21api @ 5797124 | flock+nice19: setup_toolchain.py test --toolchain-dir u21tc-base --jobs 2 > u21/base_build3.log | 17:36:01 |
| done rc=1 wall=24.940800629s 17:36:31 | lane S (fg) 1665 | wt-u21s | lwIP host run run6_f_2 (f stage, build-lwip-copyheader) | 17:36:06 |
| done rc=0 17:40:07 (236 s incl. flock wait; tick image built, readback True, release refusal raised) | 2863 (bg) | wt-u21o @ 9314738 (read) | flock+nice19 -j2: build_firmware.py dev with tick_offset_test=True on u21tc-o (o_tick_dev.py) > u21/o_tick_dev1.log | 17:36:12 |
| done rc=0 222s 17:40:36 | lane S (fg) | wt-u21s @ 969fb55 | flock+nice19: setup_toolchain.build_unix_lwip_port(u21tc-s, jobs 2) > u21s_runs/build_lwip_real.log | 17:36:54 |
| done rc=0 17:49:05 | lane T (bg) | wt-u21t @ fd85e05 | flock+nice19+taskset 0,1: RUN_SLOW_FIRMWARE_BUILD=1 PICO_TOOLCHAIN_DIR=u21tc-t pytest test_build_firmware.py -k real (6 devices) > u21t_runs/fw6.log | 17:37:54 |
| done 17:40:41 | lane S (fg) | wt-u21s | removed interim build-lwip-copyheader and its variant dir from u21tc-s | 17:40:41 |
| done rc=0 wall=24.236733321s 17:41:20 | lane S (fg) 4947 | wt-u21s | lwIP host run real_e_1 (e stage, build-lwip) | 17:40:56 |
| done rc=0 wall=24.198161297s 17:41:44 | lane S (fg) 6120 | wt-u21s | lwIP host run real_f_1 (f stage, build-lwip) | 17:41:20 |
| done rc=0 wall=24.234039110s 17:42:13 | lane S (fg) 7804 | wt-u21s | lwIP host run real_e_2 (e stage, build-lwip) | 17:41:49 |
| done rc=0 wall=24.037214920s 17:42:37 | lane S (fg) 9972 | wt-u21s | lwIP host run real_f_2 (f stage, build-lwip) | 17:42:13 |
| done rc=0 wall=23.724554619s 17:43:01 | lane S (fg) 11940 | wt-u21s | lwIP host run real_e_3 (e stage, build-lwip) | 17:42:37 |
| done rc=0 17:51:50 (548 s incl. flock wait; all flavours and readbacks, record) | 12238 (bg) | wt-u21o @ 9314738+uncommitted (fresh dirs, stale .pp) | flock+nice19: PICO_TOOLCHAIN_DIR=u21tc-o setup_toolchain.py test --toolchain-dir u21tc-o --jobs 2 > u21/o_test_run3.log | 17:42:43 |
| done rc=0 wall=24.376480639s 17:43:26 | lane S (fg) 13346 | wt-u21s | lwIP host run real_f_3 (f stage, build-lwip) | 17:43:01 |
| done rc=0 wall=24.302465624s 17:43:50 | lane S (fg) 14998 | wt-u21s | lwIP host run real_e_4 (e stage, build-lwip) | 17:43:26 |
| done rc=0 wall=23.808718948s 17:44:14 | lane S (fg) 17593 | wt-u21s | lwIP host run real_f_4 (f stage, build-lwip) | 17:43:50 |
| done rc=0 17:45:02 | lane S (fg) 20189 | wt-u21s | lwIP host calibration calib_loaded_e1 (e stage) | 17:44:39 |
| done rc=0 17:45:27 | lane S (fg) 22459 | wt-u21s | lwIP host calibration calib_loaded_f1 (f stage) | 17:45:03 |
| done rc=0 17:52:16 | lane S (bg) | wt-u21s @ 969fb55 | flock+nice19: one-time build-lwip-control in u21tc-s (insertion disabled in-process, u21/s_probe/build_control.py) > u21s_runs/build_control.log | 17:46:14 |
| done rc=0 17:48:08 | lane S (fg) | wt-u21s | test.sh's run_test_file on the lwIP file, build-lwip, e stage | 17:47:44 |
| done rc=0 17:48:33 | lane S (fg) | wt-u21s | test.sh's run_test_file on the lwIP file, build-lwip, f stage | 17:48:09 |
| done rc=1 wall=41.427500742s 17:53:09 | lane S (fg) 2731 | wt-u21s | lwIP host run control_e (e stage, build-lwip-control) | 17:52:28 |
| done 17:53:21 | lane S (fg) | wt-u21s | removed build-lwip-control and build_overrides_control from u21tc-s after the sensitivity run | 17:53:21 |
| done rc=0 17:53:51 | lane S (fg) | wt-u21s | flock+nice19 -j1: rp2 cmake configure (build-listenprobe in u21tc-s) + listen-pcb probe compile (u21/s_probe/rp2_listen) | 17:53:49 |
| done rc=1 0s 17:54:47 | lane S (fg) | wt-u21s | flock+nice19 -j2: link build-listenprobe firmware in u21tc-s for its symbol map + probe recompile (u21/s_probe/rp2_listen) | 17:54:47 |
| done rc=2 0s 17:54:55 | lane S (fg) | wt-u21s | flock+nice19 -j2: link build-listenprobe firmware (retry after probe include fix) | 17:54:55 |
| done rc=0 68s 17:56:12 | lane S (fg) | wt-u21s | flock+nice19 -j2: link build-listenprobe firmware (retry 2) | 17:55:04 |
| done rc=0 17:59:47 | lane T (bg) | wt-u21t @ fd85e05 | flock+nice19: PICO_TOOLCHAIN_DIR=u21tc-t setup_toolchain.py test --toolchain-dir u21tc-t --jobs 2 (final HEAD, O3 merged) > u21t_runs/tc_test2.log | 17:57:00 |
| done 17:57:02 | lane S (fg) | wt-u21s | removed build-listenprobe from u21tc-s (symbol map kept in u21/s_probe/rp2_listen/firmware_symbols.txt) | 17:57:02 |
| done rc=0 wall=24.231730207s 17:57:35 | lane S (fg) 11010 | wt-u21s | lwIP host run final_loaded_e (e stage, build-lwip) | 17:57:11 |
| done rc=0 wall=24.078877904s 17:57:59 | lane S (fg) 14095 | wt-u21s | lwIP host run final_loaded_f (f stage, build-lwip) | 17:57:35 |
| killed by lane S 18:00:29 (its pgrep matched its own command line; never exited) | lane S (bg watcher) | - | wait until no process holds or waits on the toolchain flock (for the quiet runs) | 17:59:06 |
| done rc=0 18:00:58 | lane S (fg) 1707 | wt-u21s | lwIP host calibration calib_quiet_e (e stage) | 18:00:34 |
| done rc=0 18:01:22 | lane S (fg) 1817 | wt-u21s | lwIP host calibration calib_quiet_f (f stage) | 18:00:58 |
| done rc=0 wall=24.047394381s 18:01:50 | lane S (fg) 2250 | wt-u21s | lwIP host run final_quiet_e (e stage, build-lwip) | 18:01:26 |
| done rc=0 wall=24.055158577s 18:02:14 | lane S (fg) 2563 | wt-u21s | lwIP host run final_quiet_f (f stage, build-lwip) | 18:01:50 |
| DONE ~19:45 (D FINAL 16ecb04, merged -> api 1f54552; was PAUSED 18:2x: WIP D1 e9c4fd7 + merge 20c85cb + uncommitted SPEC phase 2; status reports/D_pause.md) | agent | wt-u21d | lane D phase 1 (SPECIFICATION.md; O-based parts; WIP D1) | 18:02:02 |
| done rc=0 18:08:13 | lane T (bg) | wt-u21t @ a1cfee1 | flock+nice19: PICO_TOOLCHAIN_DIR=u21tc-t setup_toolchain.py test --toolchain-dir u21tc-t --jobs 2 (final HEAD, O final merged) > u21t_runs/tc_test3.log | 18:05:32 |
| done rc=0 (entered late; ran ~17:57 for under 10 s) | lane S (fg) | wt-u21s | flock+nice19: compile u21/s_probe/rp2_listen/pcb_fields.c with build-listenprobe's flags (struct tcp_pcb offsets) | ~17:57 |
| RESUMED 19:3x (owner go; was PAUSED 18:2x: merge dd8202a + uncommitted edits in 5 docs; status reports/E_pause.md) | agent | wt-u21e | lane E phase 1 (CLAUDE.md, BACKLOG.md, README.md, tests_hardware/README.md, HEAP_FRAGMENTATION_MEASUREMENTS.md; WIP E1) | 18:09:31 |
| done (all green except overrides' 1 cross-lane red: T board=) | lead | wt-u21api @ 00d5e72 | integration preview: S's L0 set + overrides + gate agreement + boot_contiguity -k same_interpreter_settings (nice 19, netns, sequential) | 18:10:32 |
| done (all green but tunables_register: D; lint.sh PASS 6/6) | lead | wt-u21api @ 1b43482 | merged-tree L0 before A-21: ruff, host mypy, 20 tests_scripts files, collect-only tests_hardware (nice 19, netns, sequential) | 18:14:19 |
| done rc=0 18:19:56 (161 s, 0 warnings; binaries = base shas) | lead (bg, ALONE, A-21) | wt-u21api @ 1b43482 | flock+nice19: setup_toolchain.py test --toolchain-dir /root/pico-toolchain --jobs 2 > u21/a21_shared.log (D, E acked freeze) | 18:17:15 |
| STOPPED 18:23:43-18:24:11 at the owner's pause (by pid; phase A partial: lint rc0, typecheck noargs rc0, typecheck ci rc0; test.sh -1/32768 mid-run, no result) | lead (bg) | gate worktrees @ 1b43482 | gate0 PREVIEW: gate_v10.sh 1b43482 u21/gate0 (phase A lint+typecheck, test.sh -1 and 32768 at TEST_PARALLELISM=4; B npm + 6 twins; C coverage) | 18:20:34 |
| done 19:35:47 (+ re-run of vocab/citations/legacy 19:3x; reds: citations B.14.4 x3, tunables_register D's 15 rows) | lane E (fg) | wt-u21e @ dd8202a+edits | nice19 pre-commit pytest set, sequential, one file at a time (11 files) | 19:34:54 |
| DONE 19:41:53-20:20:55 rc0 (all legs PASS; 93/93 files both stages, no retry) | lead (bg) | gate worktrees @ 895268c | gate1 FINAL: gate_v10.sh 895268c u21/gate1 (A lint+typecheck, test.sh -1 and 32768 at TEST_PARALLELISM=4; B npm + 6 twins; C coverage) - alone, nothing else runs | 19:41:49 |
| done 20:32:40 (file tools only: git ls-tree/cat-file, diff, gzip, grep; no process left) | agent | (file work, no worktree) | evidence agent: file checks, nice 19 (assembles evidence_stage_u21/, gate1/ aside) | 20:22:14 |
