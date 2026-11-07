# lwIP write stall — root-cause check and solution options (lead, 2026-09-30)

Owner request 2026-09-30: check whether the stall is real, search how others solved it, then propose a solution.
Sources: MicroPython v1.29.0 (scratchpad `mp/`), upstream master `extmod/modlwip.c` (fetched 2026-09-30), lwIP
(scratchpad `lwip/`), CircuitPython `ports/raspberrypi/common-hal/socketpool/Socket.c` (main, fetched 2026-09-30).

## Mechanism (pinned source)
- `lwip_tcp_send()` (`extmod/modlwip.c:760-828`): a write is sized by `tcp_sndbuf()` (bytes only); if
  `tcp_write()` then returns `ERR_MEM`, it retries 200 × `mp_hal_delay_ms(50)` inside one C call, also for a
  non-blocking socket (its own comment says so). The watchdog is fed only from the asyncio supervisor
  (`src/system_service.py:249`), so a full 10 s passes the 8,388 ms cap. Asyncio's `Stream.write()` calls
  `s.write()` directly (`extmod/asyncio/stream.py:63`), so every webserver write can enter it.
- `ERR_MEM` with room reported has three sources (`lwip/src/core/pbuf.c:275-286`; `tcp_out.c:171`;
  `tcp_write_checks()` queue limit and phase 3): the `MEM_SIZE` arena, the `MEMP_TCP_SEG` pool, the per-pcb
  `TCP_SND_QUEUELEN` pbuf limit.
- Fatal case at HEAD (`MEM_SIZE` 12,000, `TCP_SND_BUF` 6400): pcbs whose peers stop reading (zero window) or
  vanish (no ACK) keep ~7.2 KB each queued for up to per-call timeout 5 s + modlwip close-abort 10 s; two of them
  fill the arena, and any other connection's next write loops the full 10 s with nothing left to free the arena
  -> WDT reset. With live peers the loop ends on the next ACK but still freezes the VM in 50 ms steps.
- Not observed on silicon: no bench test holds a connection open without reading (the abrupt-disconnect test
  closes the socket, which frees the pcb at once). Confirmation on silicon is a phase-C step.

## Upstream and others
- MicroPython issue 19704 (2026-09-16, open): "non-blocking socket blocks in send when out of memory", measured
  on OpenMV RT1062 (worst write ~1.5 s, 54 writes > 100 ms in 320 s). Open fixes: PR 19708 (non-blocking ->
  `EAGAIN` on `ERR_MEM`) and PR 19705 (non-blocking -> partial write, `ENOBUFS` when nothing fits; argues
  `EAGAIN` busy-spins because POLLOUT reads `tcp_sndbuf`); the maintainer asked 19705 whether `EAGAIN` fits
  better. Upstream commit 6e79dcf9c (2026-08-15, after v1.29.0) only swaps the 50 ms sleep for `poll_sockets()`
  with a ticks-based 10 s cap — the stall stays.
- CircuitPython (rp2): same loop, shrinks `write_len` to whole MSS multiples on `ERR_MEM`, still 10 s.
- lwIP: small writes filling `TCP_SND_QUEUELEN` before `snd_buf` is the documented `tcp_write()` `ERR_MEM` case.
- `setsockopt(TCP_NODELAY)` writes `pcb.tcp->flags` without a NULL check or the lwIP lock in both MicroPython
  (`modlwip.c:1527-1535`) and CircuitPython.

## Options
- Sizing proof only (OR112 as decided, or `TCP_OVERSIZE 0` + `TCP_SND_QUEUELEN` 10 without the unsafe call):
  about 13.3 KB (decided) or 15.4 KB (`TCP_OVERSIZE 0`, `MEM_SIZE` 26,745, 90 segments) less GC heap than today,
  against ~21 % (~40 KB) free at peak (SPEC H.7), so `max_connections` 6 needs re-measuring; 1.6 KB in flight per
  connection; holds only for this firmware's write pattern (header block, 256 B writes).
- Fix the defect: a zero-touch override compiling an anchor-checked patched copy of `modlwip.c` (non-blocking
  send returns `EAGAIN` on `ERR_MEM`, upstream PR 19708's change); feasible from the pinned CMake — a user C
  module's cmake is included after `extmod.cmake` sets `MICROPY_SOURCE_EXTMOD` and before `target_sources()`
  (`ports/rp2/CMakeLists.txt:100, 108, 518`; `py/usermod.cmake`), to be proven by a build. No heap cost; the
  webserver's per-call timeout bounds the wait cooperatively; retired when the pin carries an upstream fix.
