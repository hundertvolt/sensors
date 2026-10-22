Line numbers are for the current tree (`.../scratchpad/wt-u35int/src/`). MP means /root/pico-toolchain/micropython at v1.29.0. To find the caller of addition 1, I read three code lines in buildgen/codegen.py (236-239), which is outside the listed sources. I used no comments, docs or commit messages as evidence.

**1. asy_uart_link_driver.py hazard mode**
- What it does: PUT /status {"UartHazards": true} reaches the driver through webserver 855-857 → 892-899, registered by codegen 236-239. That sets a flag (280-286). The initiator's exercise loop then runs one scripted sequence in place of an echo round (136-137, 180-196): two uart_set tasks at once (218-228), a raw GET crossed with a SET (122-129), 24 raw boundary-value first-chunk SETs (58-64, 198-216) and recovery exchanges. The result lists are served by get_hazard_report (265-267).
- Device cost:
  - Per run, freed afterwards: a 53 B frame, a 53/55 B ack buffer, a 103 B train, 2 Tasks and 2 `_initiate` frames.
  - Held until reboot after the first run: the results, a few hundred bytes.
  - Always: 9 more attributes on both instances; the responder never uses them (85-93).
  - Time: about 2-5 minutes per run with no echo traffic. With timeout 1000 ms (asy_uart_comm.py:112) the read window is 8 s and the quiet wait 3 s: 24 × 3-8 s plus 6 recoveries × 8-16 s.
  - Writes: no flash writes. But every fault it provokes is persisted on both ends (asy_uart_comm.py:516-518), overwriting the FRAM-backed UART_init/UART_resp history that CLAUDE.md says to read before clearing.
  - Runaway: none; one pending run at most, and requests are refused while one is pending.
- What it buys: no product failure is prevented; the output is results for a host test to judge.
  - `_two_initiations` exercises a pure-Python `_busy` flag (asy_uart_comm.py:534-536, 1183). No hardware or load can change its result, so running it on the device proves nothing the unit tests don't.
  - The raw sweep does exercise real UART timing. Whether API load changes that: premise not checkable from source.
- Test machinery in product: yes, all of it. It replays "the bench hazard script's set" and hands raw results to "the reader" (181-182, 265-267). Nothing on the device uses them.
- Simpler form: drop `_two_initiations` together with `_initiate` (146-153) and both tasks; the unit/twin tiers prove the flag completely. If an on-device check stays, one `create_task` + `await asyncio.sleep(0)` + an inline second `uart_set` gives the same "one runs, one is refused" with one task and no wrapper. I found no off-device form with the same "under API load" guarantee short of changing the bench wiring or the C peer, which is out of scope.
- Verdict: OWNER QUESTION — ship a bench-script hazard runner in dev firmware (test code in the product, provoked faults in the FRAM logs), or keep the under-load proof off-device?

**2. asy_captive_dns.py `CaptiveDNS.run()`**
- What it does: one `await asyncio.sleep(0)` per received datagram (95-97). MemoryError is now re-raised out of the address parse (102-103) and out of DNSQuery (193-194), so run()'s catch-all persists it (133-137: err_s, then a 3 s pause).
- Device cost: no task and no bytes (`sleep_ms` reuses one generator, MP extmod/asyncio/core.py:55-58). One scheduler pass per datagram. Under heap failure, at most one FRAM entry per 3 s. No flash writes.
- What it buys, checked against the source: without the yield, nothing in this loop pauses while data is queued.
  - The free-Lock acquire in `_connect()` does not yield (MP extmod/asyncio/lock.py:33-40).
  - `_poll` returns on `ipoll(0)` without awaiting (asy_udp_socket.py:104-113).
  - A UDP socket is always writable (MP extmod/modlwip.c:1630-1633).
  - Off-subnet datagrams `continue` with no await (108-110).
  - The CYW43 IRQ schedules `cyw43_poll` on PendSV (MP ports/rp2/mpnetworkport.c:86-96), refilling the 4-slot queue (modlwip.c:299, 455-465) while Python runs.
  - Result: a port-53 flood from any hotspot client starves every task, including the supervisor's watchdog feed, and the unit reboots repeatedly. The base had the same gap (base asy_udp_socket.py:138-141).
  - The heap-failure part is real too: MemoryError comes from MP py/runtime.c:1689-1696, and the old code swallowed it as "malformed" with no trace for the memory gates.
- Test machinery in product: not the additions themselves. But the older `try` at 98-106 guards an int `addr[0]` that only the Unix port produces (raw sockaddr bytes, MP ports/unix/modsocket.c:321-323). On rp2 the address is always a str (modlwip.c:417-424), and `ipv4_to_int` never raises on a str (asy_dns_client.py:123-134). So on the device that `try` only catches what the new clause re-raises.
- Simpler form:
  - Delete the `try` at 98-106 outright.
  - Narrow DNSQuery's handler to `except (IndexError, ValueError, TypeError)`; UnicodeError is a ValueError (MP py/objexcept.c:364). MemoryError and RuntimeError then reach run()'s catch-all, which already calls report_if_fatal, so no re-raise clause is needed.
  - Optional: move the yield into `UDPSocket.ready()`, where CLAUDE.md puts the UART one.
- Verdict: the yield — KEEP. The MemoryError handling — SIMPLER FORM EXISTS, as above.

**3. asy_system_service.py controlled shutdown**
- What it does: a lock-guarded gate (366-402) claims the command, closes the config stores, hands the watchdog to the shutdown and starts `_shutdown_sequence` as a task (387). The sequence waits for the supervisor to park on an Event (432, 537-539), cancels it, flushes, quiesces FRAM, cancels and awaits every task, deletes or erases, then arms the reset (425-480).
- Device cost:
  - Per boot: one extra Task (the supervisor, split from `supervise_tasks`, 789-796), one Lock, one extra Event, and 4 attributes.
  - Per supervisor pass: one bool check.
  - Per command: one Task, and up to about 2 s waiting for the park (`_TASK_CHECK_TIME`, 71). The stores are flushed three times (444, 345, 410); the last two find nothing to write.
  - No added flash writes.
- What it buys, checked in code:
  - The supervisor restarts any ended task (561), so it must stop before the tasks are cancelled; otherwise an erased chunk or deleted file could be rewritten.
  - Once it stops nothing else feeds the watchdog, and the 8388 ms cap (Part F) makes the per-step feed necessary.
  - The Event also covers a command that arrives during boot: `start_tasks` (750-766) has no gate check, but the supervisor starts only after tasks and timers (codegen 443-452), so the park implies every task exists.
  - The separate task lets the PUT answer before the server's tasks are cancelled.
  - Runaway: none. A hung step gets no feed and ends in a watchdog reset that records code 9.
- Test machinery in product: `_shutdown_task` (230, 387) is write-only in src/. MicroPython's run and wait queues already hold the task strongly, so the attribute serves only whoever reads it outside src/.
- Simpler form:
  - The Lock: `erase_ready()` at 378 is the gate's only await. Await it first, then check and claim with no await in between; cooperative scheduling makes that atomic. The outcomes stay the same, and the tentative claim, its two rollbacks (383, 389) and the `_reset_armed` re-check (380-381) go. `_shutdown` and `_feed_owned` then always agree, so they can be one field.
  - The park-then-cancel (433-439, 539): the supervisor can `return` right after setting the Event, and the sequence only checks `task.done()` — the same proof that it stopped.
  - Keep the task and the Event.
- Verdict: SIMPLER FORM EXISTS — replace the Lock by ordering, have the supervisor return instead of park-and-cancel, and drop the write-only `_shutdown_task`.

Outside the three, the same kind of problem: asy_system_service.py:761-762, `if loop.get_exception_handler() is None`, is a product branch that only matters because the PC test tiers install their own handler.

nothing of mine is running