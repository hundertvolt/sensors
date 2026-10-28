F4a hand-back, saved by the lead from the message it sent (2026-10-26). Commit 4de10081 on audit/u35-f4.

F4a hand-back. Commit `4de10081` on audit/u35-f4 (parent 656fc82). Not pushed, nothing left uncommitted. Logs are in S/u35/laneR/f4/ (S = the scratchpad).

**What changed.** The modlwip_eagain copy now carries a second patch: `if (socket->pcb.tcp->state != LISTEN)` around tcp_err/tcp_recv, and `&& socket->pcb.tcp->state != LISTEN` added to tcp_poll's existing guard. tcp_arg and tcp_close are untouched. The patch has its own anchor (`_MODLWIP_CLOSE_CALLBACKS`, pinned :1682-1690, counted once) and its own reverify text (`_MODLWIP_CLOSE_REVERIFY`). The copy's header names both patches.
- Files: toolchain/micropython_overrides.py, tests_scripts/test_micropython_overrides.py, the new tests/lwip_host/test_modlwip_listener_close.py, tests/lwip_host/test_modlwip_eagain.py (header and one comment now say what is true), SPECIFICATION.md (A.5 sentence near :605, B.14.4, a new catalog row plus the 19704 row's trigger), BACKLOG.md (watch entry and open question 30).
- Diff of the final copy against the pin: the include, the EAGAIN block, the guard, nothing else (final_copy.c).

**DEVIATION: the MemoryError case is not fixed and its test is not committed.** The brief's premise does not hold.
- listen() stores `incoming.connection.alloc = backlog` (modlwip.c:1098) before m_new0 (:1099). The union then aliases it into `incoming.tcp.pbuf`. close() runs `lwip_socket_free_incoming()` (:383-384) before the guard, so it calls `pbuf_free((pbuf*)backlog)`.
- On build-lwip this is a segfault in pbuf_free (rdi = 4 after listen(4)), with or without the guard (probe_memerr_guard_gdb.log, matrix.log). On rp2 it is a pbuf_free of a bootrom address.
- Scratch variants, both GC stages (matrix.log): storing `alloc` after the m_new0, plus the pcb-state guard, passes. The same swap with a socket->state guard aborts at tcp.c:2070. So the pcb-state design is the right one, but only once the alias is fixed.
- I stopped here per CHECKLIST 24 (the measured result missed its premise). The candidate is ready: probe/test_listen_memoryerror.py, variant.py, and bins/modlwip-*.c (the variant copies). It is recorded as BACKLOG open question 30, tagged "(agent, 2026-10-26)".

**Proofs**
1. New host test, red then green:
   - Red: exit 134 at tcp.c:2070 on the shared build-lwip, at both GC stages (red_listener_close_unpatched.log).
   - Green: 3/3 on build-lwip rebuilt with the guard, at both stages (green_listener_close.log).
   - Bite: leaving the listener unclosed fails "port 50100 is still held" (bite_unclosed_listener.log).
   - No memory-gate markers in any output.
2. Override tests: 8 red before the code change (red_overrides_tests.log), all green after. They cover the new anchor in the real pin, its own reverify text, the parametrization over every anchor, a repeated block refused, the exact copy diff, and nothing written on a refusal.
3. Toolchain copy:
   - Copied to S/u35r/f4tc; there was 23 GB free after.
   - build-lwip rebuilt there in 16 s, and its readback passed.
   - Dev firmware build rc=0 (build_fw.log). The image record lists overrides ['modlwip_eagain'].
   - The compiled object branches on `pcb->state` (offset 60) == LISTEN before tcp_err/tcp_recv and before tcp_poll (fw/ioctl_disasm.txt).
   - The final generated copy is byte-identical to the one the firmware compiled.
   - f4tc is deleted.
4. Consumers: build_firmware.py's `_overrides_in_build`, setup_toolchain's build/apply/readback, and test_build_firmware, test_board_image_fixture, test_setup_toolchain_env, test_test_sh.
   - On the guard build: test_modlwip_eagain 9/9, 22.5 s at each stage; the new file 3/3 in 0.03 s.
   - 28 tests_scripts reader files: 1666 passed, 6 skipped (the opt-in slow firmware build) (readers.log).
   - After the comment rewrap: citations, comment cap, overrides, decision vocabulary and test_sh files, 1140 passed (checks2.log).

**Checks.** lint.sh and typecheck.sh refuse to run here: _require_venv.sh insists on the worktree's own .venv. So I ran their ruff and mypy commands directly. ruff on all scopes plus build/generated_src: clean. mypy main pass (266 files) and host pass (308 files): clean, from a cold cache with the temporary typings symlink, removed afterwards.

**Brief's "verify each".** All three same-class sites are confirmed unreached:
- POLL_WR (:1639), send/write (:760) and a non-blocking sendall (:1417) read tcp_sndbuf. setsockopt(TCP_NODELAY) (:1528-1535) writes the flags.
- asyncio only polls the listener for reading (stream.py:149) and accepts from it. src/ and ext/ make no TCP_NODELAY call.
- All three are named in the BACKLOG watch entry.

**Owed to the lead**
- CLAUDE.md :53-55 is now stale. I did not edit it, because an agent message cannot authorize a CLAUDE.md change. Proposed text: "For the `modlwip_eagain` override it also asks, patch by patch, whether the new pin carries a real upstream fix — micropython issue 19704 (PRs 19705/19708) for the EAGAIN patch, a `close()` that skips the listener callbacks for the other — and a fixed patch is removed, not re-anchored, the override with its last patch (owner, 2026-09-30; owner, 2026-10-26)."
- Chroot list: yes, this is a build-environment change. toolchain/ now generates a different modlwip.c for every rp2 image and for build-lwip.
- Silent-failure scan: the only new finding is BACKLOG #30 (the failed-listen close, firmware, every device).
- Operating modes: the effect is limited to closing the webserver's listener, in every mode that runs the webserver, and is identical on every device.

**Runs.** All logged in RUNS.md and all exited 0: the copy, build-lwip, two scratch variants, the firmware build, the eagain file at both stages, and the readers.

nothing of mine is running

---
F4a second hand-back (third patch), saved by the lead from the message it sent (2026-10-26). Commit d7198011.

F4a, third patch. All three patches are in and tested. New commit `d7198011` on audit/u35-f4, after `4de10081`; nothing amended, not pushed, nothing uncommitted. Logs are in S/u35/laneR/f4/.

**Patch 3 (agent, 2026-10-26, under the owner's ruling).** In `lwip_socket_listen()` the copy now allocates the accept-queue array first and stores `alloc` after it, with a one-line `// Patched:` comment.
- After a MemoryError the union's pbuf view stays NULL.
- A `listen()` that succeeds stores the same two values as upstream.
- It has its own anchor, `_MODLWIP_LISTEN_ALLOC` (pinned :1098-1099, counted once), its own reverify text and its own removal trigger: upstream stores `alloc` only once the allocation succeeds, or close() no longer frees the value it aliases.
- The copy's header is now three lines and names all three patches.
- Against the pin, the final copy differs only in the include, the EAGAIN block, the reordered listen() stores and the close guard (final3_copy.c).

**Host test:** `test_closing_a_socket_whose_listen_ran_out_of_heap_frees_its_port` was added to test_modlwip_listener_close.py, and the file header now covers it.
- Red on the guard-only build: 3 PASS, then exit 139 (segfault) at the new test, at both GC stages (red3_listener_close_guardonly.log).
- Matrix (matrix3.log): with the swap alone, and with the swap plus a `socket->state` guard, the MemoryError case aborts with 134 at tcp.c:2070 at both stages. The original guard-only result (segfault in pbuf_free, p = 4) is in matrix.log.
- Green with all three patches: 4/4 at both stages (green3_listener_close.log).
- No memory-gate markers in any of these logs. The deliberate MemoryError is caught silently.

**Override tests.** The third anchor now gets the same set as the second: real pin (a new dedicated test, which first failed with AttributeError, red3_realpin.log), load-bearing with its own reverify, the parametrization over every anchor, the host anchor list, a repeated block refused, the exact copy diff, a new end-state test (array stored before `alloc`, each once), and nothing written on a refusal.
- Red before the code change: 8 failures plus the real-pin test (red3_overrides_tests.log).
- Green after: the override, build_firmware, board_image_fixture and setup_toolchain_env files give 524 passed, 6 skipped (the opt-in slow firmware build).

**Firmware.**
- Toolchain copied to S/u35r/f4tc after a disk check (23 GB free after).
- build-lwip final built rc=0 with its readback. test_modlwip_eagain passes 9/9 on it, 22.5 s at each stage.
- Dev firmware rc=0 in 38 s (build_fw3.log); the image record lists overrides ['modlwip_eagain'].
- Compiled `lwip_socket_listen` stores `alloc` after the allocation (fw/listen_disasm.txt): `bl m_malloc0` at d4, then `str r0,[r4,#12]` (the array) at da, then `strb r3,[r4,#8]` (alloc) at dc.
- The image's rp2 copy, the host copy and a fresh generation from the final code are byte-identical.
- f4tc and the binaries are deleted.

**Docs.**
- SPECIFICATION B.14.4: a third-patch paragraph; mechanism, header, anchors (five modlwip.c anchors in the host list), measured results and removal triggers updated; the heading now reads "a listener's close is safe"; the "separate defect" sentence is gone.
- SPECIFICATION catalog: a third-patch row.
- BACKLOG: the watch entry now carries the third patch, and open question 30 is removed.
- CLAUDE.md is left to you. The proposed text from my first hand-back still holds, with "and listen()'s allocation order for the third" added.

**Checks.**
- ruff, all scopes: clean.
- mypy main pass (266 files) and host pass (308 files): clean, from a cold cache with the temporary typings symlink, removed afterwards.
- 28 tests_scripts reader files, including citations, the comment cap, decision vocabulary, test_sh and the override files: 1674 passed (readers3.log).
- Chroot list: still a build-environment change, since toolchain/ generates the copy for every rp2 image and for build-lwip.

**Runs.** All have lines in RUNS.md and all exited 0: the copy, three variant builds plus the final build-lwip, the eagain file at both stages, the firmware build and the readers.

nothing of mine is running
