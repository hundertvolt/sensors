UM1 hand-back, written by the lane (2026-10-27)

**Commit:** ad624cca on audit/u35-um1, on top of 5a8c6e35. It changes tests only (tests/test_asy_uart_comm.py +72, tests/test_asy_uart_driver.py +30). No product file changed. Not pushed. Nothing is uncommitted apart from the linked node_modules. Logs are in S/u35/laneB/um1/. Line numbers below are for this head; src/ is unchanged.

## 1. Provenance
- **Where the sentence comes from.** These all entered at c11ca0aa (U17, 2026-10-08), tagged "(owner, 2026-10-05)":
  - the G.2 sentence (SPECIFICATION.md:7705-7713);
  - J.8's "no caught `MemoryError` stands at them (owner, 2026-10-05; I.2, I.4(a))" at :10090-10094, which also says where the raise goes: "to the listen loop's broad catch on a responder or to the caller on an initiator";
  - the source comment at asy_base_classes.py:180 and the module docstring at :7-8;
  - changelog rows B62 and B64.
  U30 (06a8ae5d, 2026-10-20) later reworded I.2's UART row (:8926-8929) and kept the claim.
- **What the tag rests on.** It rests on PROJECT_AUDIT_PLAN.md:557, OR143.a (2), which is the lead's integration: "Both count in SPEC I's heap budget, and the memory rule's caught-`MemoryError` sites at these allocations go."
  - The owner's own note (OR143, :556) asks for three things: chunking, "a general maximum buffer size", and the ring's placement. **It says nothing about MemoryError catches.**
  - The owner tag comes from the fold convention (audit/actions/FOLD_BRIEF.md:35). REGISTER.md:494 reads "A-8 follows the owner's decision recorded as OR143.a".
- **What was removed.** Before U17, both receive allocations and both right-sizing copies caught `(MemoryError, OverflowError)` with `_fault(_ERR_ALLOC, ...)`, then returned `None` or `ListenResult(None, CMD_SET, None)` (c11ca0aa^:src/asy_uart_comm.py:243-247, 280-284, 294-298, 989-993). These are exactly the alternative flows the brief names. B64 classed the removal Class B ("Memory only: the bytes acknowledged and delivered are identical").
- **I.4(a) today** (:9097-9109): "A function catches `(MemoryError, OSError)` only where it has a true alternative flow — a defined unavailable/`None`/`False` result its caller handles — and implements that flow (owner, 2026-09-25: 'if the function has a true alternative flow for graceful degradation on expectable memory errors, this indeed shall be implemented')." That quote is from OR26.a (PROJECT_AUDIT_PLAN.md:321), whose full sentence opens "This is only true if the function experiencing the MemoryError is doomed to fail on memory error ...".
  - At c11ca0aa, I.4(a)'s trigger read "a call site that can raise `MemoryError` from a caller-controllable or growing allocation catches", with the 09-25 qualifier "only where a real graceful-degradation alternative exists".
  - The "Which call sites catch" wording arrived at 06a8ae5d.
- **Verdict:** "not caught" is a recorded decision, not just a description of the code. It is reasoned from the cap ("bounded before they happen", J.8), carried by U17 and re-affirmed by U30. But it rests on reading a bounded piece as not "expectable". OR26.a (09-25, earlier) and OR143 (10-05) have never been put side by side to the owner. The removal of a true alternative flow is in the lead's integration text, not in the owner's words.

## 2. Reachability
No new runs; the numbers come from the specification and the measurement archive.
- **How big a piece buffer can be.** Each piece is at most 256 B (Part N `uart.chunk_bytes`, the same as `web.chunk_bytes`). The cap is 12,192 B (`dev.uart_max_transfer_bytes`). That gives at most 48 pieces, 48 small objects and a list of about 200 B, with no block above 256 B (pinned by tests/test_asy_base_classes.py:603).
- **Who allocates one.** Only `dev` wires `uart_link` (devices/dev.toml:174-192); the other five images never build one.
  - On `dev` today: the banner GET (14 B, one piece, every 1000 ms) and the echo SETs (at most 103 B, one piece).
  - A train at the cap only comes from a peer that declares one. The bench script `uart_crossover_exchange.py` does; the C peer is a prototype only.
- **The heap.**
  - The GC heap is 192,488 B.
  - Free after boot: about 105,000 B (I.6). F.5.3 measured 130,224 B free, with a 115,536 B largest block, on `dev` after `build_system()`. That was on 2026-09-11, before lwIP took 5,040 B.
  - At the shipped 6-connection hammer peak: about 21 % free and a largest free block of about 1.5 KB, with 0 failures in 2,255 requests (archive §7R).
  - At limit 8, a hole too small for one ≤ 257 B piece occurred once in 1,319 requests. So 256 B is exactly the size that fails first under heavier load.
  - At `gc.threshold(32768)` in the run phase, the largest free block is 80 % of free (12 % at -1).
- **What no measurement covers:** a train at the cap (48 pieces, about 13 KB) on top of the web peak.
  - Part N `uart.max_transfer_bytes` says: "measurement owed: the largest free block after boot on dev against a train at the cap held in pieces, L3". H88 is owed too.
  - The UART caps are not part of `web.serving_demand_budget_b`.
  - My estimate, not a run: `dev`'s web demand of 68,790 B plus about 26 KB (one train each way) is about 95 KB. That fits within about 105 KB free, but goes past the 72,232 B budget, which exists to keep the 32,768 B contiguity reserve.
- **Verdict:** a single piece is measured placeable inside the shipped envelope. Failure at the cap under the web peak cannot be ruled out without silicon; that stays with the L3 hardware round.

## 3. Per caller
"Caught" below means the pre-U17 flow, planted as a bite. The values in parentheses are what the unit tests or the bite actually logged (timeout 30 ms).

### (a) asy_uart_comm.py:313 `_accept_set`
The responder receiving a don't-care SET (dev's echo, asy_uart_link_driver.py:117-120). It runs after the command frame's ACK (:294) and before any data ACK.
- **Today:**
  1. `uart_listen`'s finally clears `_busy` and the `async with` releases the bus.
  2. `_listen_loop`'s `except Exception` (:561-563) persists E23 UNEXPECTED, "listen loop caught: <text>" (FRAM on dev). No resync.
  3. The loop sleeps `timeout/2` (500 ms by default, :564) and doubles it (:565).
  4. The next listen reads the stranded data chunk as E80 UART_FRAME_INVALID, then resyncs and backs off again for 1000 ms.
  5. The backoff only resets on a result carrying `cmd` (:559), and a raise never returns one. So repeated failures climb to 5 × timeout.
  6. The task never ends, so nothing goes to SYSTEM and no budget is charged.

  Logged: responder [E23, E80], initiator [E81].
- **Caught:** one E20 ALLOC and an immediate resync, which drains the stranded chunk. `cmd` is set, so the loop re-listens at once with the backoff reset. Logged: responder [E20], initiator [E81].
- **What the peer sees:** the same bytes either way (one ACK, then none for chunk 2), and UART_NO_ACK at :1016. The timing differs. Today the responder is deaf for its backoff. Under repeated failures the backoff outgrows the initiator's retry after its own resync (about 4 × timeout), so later command frames fail too. That is exactly the hazard changelog A15 (Class A) removed for declined or aborted commands.
- **Class:** A, on A15's precedent. It only changes receiver-side behaviour and emits no byte. Whether the C side can reach this path is not checked here (arduino/ not read).

### (b) asy_uart_comm.py:278 `_get_unlocked`
The initiator's `uart_get` without a destination, reached through `_run_get` (:840-857). The product caller is dev's exerciser (asy_uart_link_driver.py:138). It runs after the answer header validates (:262-275) and before that header's ACK (:282).
- **Today:**
  1. `_busy` is cleared (:857) and the bus is released.
  2. The raise leaves `uart_get`. `_exercise_loop` has no try, so the task ends.
  3. The supervisor checks every 2 s (asy_system_service.py:71). `_log_dead_task` (:326-328) persists SYSTEM TASK_RAISED, "Task <name> ended with exception: <text>".
  4. The task budget rises by 100 (:73) and the task restarts. The 4th end within the decay window (−1 per clean pass) passes 300 and reboots with the task-budget code (:568-606).
  5. The initiator's UART logs nothing and has no resync and no hold-off.

  Logged: initiator [], `_busy`/hold-off both False; responder [E81]; the next GET succeeds.
- **Caught:** E20, then a resync and a hold-off. `uart_get` returns None, the exerciser counts a failure and retries 1000 ms later. No task end, no SYSTEM entry, and this site can never escalate to a reboot. Logged: initiator [E20], hold-off True; responder [E81]; the next GET succeeds.
- **What the peer sees:** the same bytes (its header goes un-ACKed). The difference is when this end initiates next.
  - Caught: it is held off past the responder's ACK wait and resync (about 2.5 s at the defaults).
  - Today: the restarted task's GET comes 0-2 s after the end with no hold-off. It can land in the responder's 1 s ACK wait, where the peer logs UART_PEER_INITIATED (:1023), or in its 1.5 s drain, where it is discarded. Either way one more transaction fails.

  This comes from reading the code at the default timings; I did not measure it.
- **Class:** A, on the same reasoning as (a).
- **Comment defect:** asy_uart_link_driver.py:133 says "Never raises out (uart_get() answers None)", which is false for this case.

### (c) asy_uart_comm.py:1111 `uart_get`'s `PieceBuffer(0, …)`
Marked Unreachable. At size 0 it allocates an empty list only, a small fixed allocation. Not a candidate.

### (d) asy_uart_driver.py:660 `readline_until_complete`
- **Callers:** no product caller in src/, the generated modules or digital_twin. Only tests and tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:151 call it.
- **Today:** it allocates before reading any byte, and the raise goes to the caller with nothing consumed.
- **Caught:** it returns None and the line stays in the ring.
- **What the peer sees:** nothing; this is not a Part J path (B62). Class B.
- **In-file inconsistency (D.10):** the same file's `readline()` at :648 and `read_until_complete` at :523/:549/:573 catch and return None with console text (B82/B84, 06a8ae5d).

### Others
- **The webserver** has no `PieceBuffer` caller. Its `_PieceWriter` (asy_webserver_service.py:215) catches nothing. A raise there ends in Microdot's catch and `_handle_unhandled_exception` (:791-797), which persists UNEXPECTED and answers 500. `_body_as_dict` re-raises `MemoryError` on purpose (:200-201). For a route, the 500 is its alternative flow, so the webserver is no precedent either way.
- **Beside the brief:** dev's echo answer allocates `bytearray(len(stored))` (asy_uart_link_driver.py:112), up to 12,192 B in one block. It is guarded by `_call` (:413) and becomes E CALLBACK.

## 4. Injection tests (ad624cca)
- **The tests:**
  - tests/test_asy_uart_comm.py:2536 (SET) and :2570 (GET), using `_UnbuildablePieceBuffer` at :2513;
  - tests/test_asy_uart_driver.py:1336, using its own `_UnbuildablePieceBuffer` at :1330.
- **What they show:** each pins today's path, with the facts listed under item 3.
- **Bite:** each one fails with a local catch planted at its site in a scratch copy: SET at :2565 (responder [E20]), GET at :2592, readline at :1355.
- **Results:** both files are green at -1 and 32768 with zero memory markers: comm 206/206 (64 s / 65 s), driver 175/175 (7 s / 14 s). The base log interleaves its files, so I could not read per-file base times from it; the new tests use 30 ms timeouts.
- **Checks:** ruff (lint_direct.sh, every pass) and mypy's cold main pass (272 files) are clean. 15 tests_scripts files that read these test files passed (883; one warning, about the datasheets submodule not being initialised, which is environmental).
- **Seen first:** my own first run went red twice. The cause was a name clash: an existing `_RefusingPieceBuffer` at :3542 replaced mine. Fixed by renaming mine.

## 5. Options and recommendation
- **(A) Leave it as it is.**
  - The docs stay consistent, and on the initiator the I.4(c)/(d) ladder works: the task ends, restarts and finally reboots.
  - The cost: on the responder, the A15 backoff hazard comes back under repeated failures and two codes are logged per event. On the initiator, an ordinary transfer failure becomes a task end that spends the reboot budget and can make the next transaction fail too.
  - The comment at link_driver:133 would need correcting.
- **(B) Catch only at :278 and :313**, restoring the pre-U17 `_fault(_ERR_ALLOC)` flows and printing the caught text so the memory gates see it (B80/B81 precedent).
  - It meets I.4(a) and J's "every fault resyncs", and A15's re-listen rule.
  - It reverses OR143.a (2)'s clause for these two sites.
  - It needs a Class A changelog entry: receiver-side, no byte emitted, the recovery timing restored.
  - Docs to change: G.2, J.8, I.2, asy_base_classes.py:7-8/:180, and a note on B64.
  - The two committed tests flip and become the fix's red-first tests.
  - A failure that persists no longer reboots through this site. It degrades and logs E20 each time; repeats are collapsed into one slot, and the writes go to FRAM, which is not wear.
- **(C) Do (B), and also catch at readline :660** with a None return (Class B). It matches how the same file's other read paths handle this; readline has no product caller.
- **Recommendation: (C)**, with (B) as the minimum if the owner wants to change only the protocol. The deciding fact is not likelihood, which only silicon can settle (Part N, L3). It is that today's path is worse at both ends than the alternative flow the protocol already chose: J's fault-then-resync, A15's re-listen, and a sentinel instead of a task end. OR26.a (09-25) asks for exactly that flow. Because this reverses an owner-tagged clause, it is the owner's question (CHECKLIST 1c). I implemented nothing.

## Deviations
My three short probes (S/u35/laneB/um1/probe*/, each under 10 s, binding no port) ran without `unshare`/`nice` and without RUNS.md lines. That breaks CHECKLIST 12. The bite's copies of src/ files are deleted.

## Runs (all exited as noted)
drv_m1 rc 0; comm_m1 rc 1 (the name clash above); comm_m1b rc 0; bite_drv rc 1 and bite_comm rc 1 (expected); final_driver/comm at -1 and 32768 rc 0; lint rc 0; mypy rc 0; ts_readers rc 0. Each has a RUNS.md line.

nothing of mine is running
