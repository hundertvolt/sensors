# F4a: the listener-close guard in the patched modlwip copy (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first (environment, rules). Worktree `S/wt-u35f4`, branch `audit/u35-f4` at
`656fc82`; logs in `S/u35/laneR/f4/`. The lead's re-check of the defect: `S/u35/lane_plan.md` LEAD NOTES 154-155.

## The owner's decision (verbatim, 2026-10-26)
The question: "How do you want this handled?" (the listener-close defect, and whether to report it upstream). The
answer: "Let's handle them like the similar findings: fix in the patched version and monitor upstream for real fixes,
as soon as upstream is fixed drop the patch. Double check your proposed solution is complete and works without
affecting other places."
"Like the similar findings" = the existing `modlwip_eagain` precedent (owner, 2026-09-30): `toolchain/
micropython_overrides.py` :466-600, SPECIFICATION.md B.14.4 (its removal trigger near :2601), BACKLOG.md's "watched
upstream" entry (:1219-1224), CLAUDE.md :54. No upstream report is posted.

## The defect (re-checked by the lead today; re-check it yourself)
`extmod/modlwip.c` v1.29.0 :1678-1690, `MP_STREAM_CLOSE`, `MOD_NETWORK_SOCK_STREAM`: `tcp_err()` and `tcp_recv()` run
on every TCP pcb, `tcp_poll()` only when `socket->state != STATE_LISTENING`. lwIP forbids all three on a LISTEN pcb
(`lib/lwip/src/core/tcp.c` :2024, :2070 and tcp_poll's assert); rp2's assert is a no-op (`ports/rp2/lwip_inc/arch/cc.h:6`),
so the stores land past `struct tcp_pcb_listen` (72 B; recv 172, errf 184; U21's probe,
`audit/artefacts/evidence/U21_close/lane_s/`). Host repro: build-lwip aborts at tcp.c:2070, exit 134
(`S/u35r/of122/repro.log`).
A second case the lead found: `lwip_socket_listen()` sets `socket->pcb.tcp = new_pcb` (:1091) and only then allocates
the backlog array with `m_new0` (:1099); a MemoryError there leaves a LISTEN pcb under `socket->state == STATE_NEW`.
Our backlog is `max_connections + 1` (src/asy_webserver_service.py:584), so the allocation happens; our start retry
(`_serve_loop`, :970-992) drops that socket, and its GC finaliser (`__del__` = close) then calls all three, tcp_poll
included. A guard on `socket->state` misses this case.

## The fix
In the copy, skip `tcp_err()`, `tcp_recv()` and `tcp_poll()` whenever the pcb's own state is `LISTEN`
(`socket->pcb.tcp->state`, a field both structs share): lwIP's own precondition, so it covers both cases. `tcp_arg()`
and `tcp_close()`/`tcp_abort()` stay as they are (tcp_arg is allowed on a listener; tcp_close frees a listener
synchronously and returns ERR_OK, tcp.c tcp_close_shutdown's LISTEN case). For every non-listening pcb the three calls
must run exactly as upstream's do, in the same order. Make the change the smallest anchored replacement that does this.
- Its own verified anchor (the exact unguarded block, counted once) and its own reverify text, next to the EAGAIN
  patch's, in the same copy. Each patch has its own removal trigger: this one goes when the pin skips these calls for a
  listening pcb, removed, not re-anchored; the copy and its wiring go only when both patches are gone. The anchor check
  failing at a pin move is the upstream watch (no upstream issue exists; nearest, PR 17333, is a different path).
- Keep the override's name `modlwip_eagain` (minimal change); state in its comment and in B.14.4 that the copy carries
  both patches. The generated copy's header names both.
- A comment block at most 3 prose lines, no audit IDs anywhere outside `audit/`.

## Proof, each red first
1. Host test, a new file in `tests/lwip_host/`: closing a listening socket; and the MemoryError case (bind, then
   `micropython.heap_lock()`, `listen(4)` raises, unlock, close). Seen aborting (exit 134) on the current build-lwip,
   which lacks the guard; then passing on a build-lwip rebuilt with it, at both GC stages, the way scripts/test.sh runs
   this tier. Any deliberate MemoryError is caught silently and nothing printed carries the memory gates' markers
   (`tests_hardware/harness.py` MEMORY_ERROR_MARKERS). Also show that a guard on `socket->state` alone still aborts on the
   second case (a scratch variant of the copy, not committed), so the test tells the two designs apart.
2. `tests_scripts/test_micropython_overrides.py`: the new anchor in the real pinned source; load-bearing (dropping it
   refuses, naming its reverify text); the parametrization that covers every anchor the code checks; the generated copy
   carries the guard; nothing written on a refusal. Seen failing before the code change where that applies.
3. Build-lwip and the rp2 firmware: never rebuild in the shared `/root/pico-toolchain` (other blocks use it). Copy it
   (`cp -a /root/pico-toolchain S/u35r/f4tc`, about 1.1 GB; a disk check first, at least 3 GB free after) and build there
   with `PICO_TOOLCHAIN_DIR` pointing at the copy. Build the dev firmware once with the patched copy
   (scripts/build_firmware.py, its modlwip readback must pass; arm-none-eabi-gcc is at /usr/bin) and show the
   compiled copy carries the guard. Delete the copy when done and say so.
4. Everything else that reads the copy or its tests: grep for every consumer of `_modlwip_eagain_source`,
   `MODLWIP_*` and the lwip_host tier, and run each. `tests/lwip_host/test_modlwip_eagain.py:2-3` says a close "trips
   lwIP's LISTEN-state assert, which aborts here": make it state what is true after the fix.
Checks: ruff and the host mypy pass on the changed files (scripts/lint.sh, scripts/typecheck.sh, as CI runs them),
the comment-cap test, test_citations, the override tests in full.

## Docs (yours)
SPECIFICATION.md B.14.4 (the patch, the reason in one or two sentences, its removal trigger), and the tunables or
override catalog rows that list this override's patches (grep near SPECIFICATION.md :605 and :7366); BACKLOG.md's
"watched upstream" list gets the listener-close entry beside the 19704 one, naming the same class's three unreached
upstream sites (POLL_WR and sendall() read `tcp_sndbuf()` past a listener; `setsockopt(TCP_NODELAY)` writes its flags:
our firmware polls the listener for reading only, never sends on it, and makes no TCP_NODELAY call) - verify each; CLAUDE.md :54 if it names the override's
retire rule. Decision tag "(owner, 2026-10-26)". BACKLOG's chroot list: say in the hand-back whether this counts as a
build-environment change (it changes toolchain/), the lead writes that entry.

## Not yours
src/, the twin, other blocks' worktrees, the shared toolchain directory, audit/ records (the lead's REC2).
Commit subject `U35 lane F4a: <summary>`, the two trailers; do not push. Hand-back: what changed (files, commit), each
proof with its red and green and log path, every consumer found and run, anything that surprised you; last line
"nothing of mine is running".
