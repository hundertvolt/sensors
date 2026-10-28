HP1 hand-back, written by the lane (2026-10-27)

Worktree S/wt-u35hp1, branch audit/u35-hp1 at 5a8c6e35. **No commits.** The tree is clean; `node_modules` is the link that was there at the start. Nothing is pushed. Logs, probes and scripts are in S/u35/laneB/hp1/. The probes are scratch copies of tests/test_digital_twin_ntp.py, made by mkprobe.py and kept in probe/, outside the worktree. RUNS.md lines are named "U35 lane HP1". All runs ended with rc=0 and 0 memory markers. I used about 75 tool calls.

## Verdict
- **A supervisor task restart does not leak**, on arzi or dev, at -1 or 32768. No supervised kind grows per restart.
- **The 147 KB per-boot step is a test-process artefact.** It is held by two things together:
  1. a stale `child_last` pointer that upstream MicroPython leaves in every native asyncio Task;
  2. the ntp test's own `_booted()`, which links each boot to the previous one.
- Neither is in src/, and neither is a twin defect, so per the brief nothing is fixed. No firmware defect was found.

## Item 1: supervisor restarts (the silicon question)
**Method.** Probe restart_extra.txt / restart2_extra.txt:
- Boot: `_booted()` without DrivenWall, so it runs on the real clock and the native run queue, as on silicon. The device's real `main()` runs, and the webserver uses one fixed port, as on silicon's port 80, so a listener left open would fail its rebind.
- Restarts: after BOOT_DONE plus 4 s, each supervised slot gets 24 restarts in turn. Each restart is: cancel the slot's task; wait until the supervisor's own pass puts a new task in the slot; `gc.collect()`; read `mem_alloc`.
- Only `sysfunct._charge_task_budget` is neutralised on the instance. That stops the 300-point budget's reboot from ending the run; the budget itself is not under test.

**Coverage.**
- arzi: 16 slots × 24 = 384 restarts. dev: 22 slots × 24 = 528 restarts. Both stages.
- 0 misses: every restart came within one pass.
- `_io_queue.map` stayed at 9-15 throughout, so registrations did not grow.
- Wall times: arzi 798 s, dev 1097-1103 s.

**Per kind** (restart_table.md, restart_summary.txt, restart_{arzi,dev}_{m1,t}.log). Each cell is the least-squares slope after the 5th restart, in bytes per restart, then the median of the last 5 samples minus the first sample:

| kind | arzi -1 | arzi 32768 | dev -1 | dev 32768 |
|---|---|---|---|---|
| WIFI.start_asy_connect | +1265 B (+28,000) | +1039 B (+25,152) | +1455 B (+51,648) | +1613 B (+52,352) |
| WIFI.start_asy_uptime | +921 B (+18,144) | +1207 B (+24,736) | +71 B (-3,808) | -45 B (+7,680) |
| WIFI.start_asy_hotspot_timeout | -103 B (+384) | +198 B (+11,584) | +233 B (-7,264) | +209 B (-6,336) |
| NTP.start_asy_sync | -90 B (+4,640) | -76 B (+2,624) | -119 B (+704) | -93 B (+800) |
| NTP.start_asy_refresh | +252 B (-800) | +10 B (-704) | +213 B (+7,040) | +169 B (-3,232) |
| NTP.start_asy_sync_age | +162 B (-2,560) | -29 B (-2,400) | -57 B (+7,136) | -46 B (+7,744) |
| FRAM.start_asy_watch_chip | +136 B (-2,592) | -17 B (-2,496) | +107 B (-8,544) | +46 B (-7,776) |
| NEOPIXEL.start_asy_overlay | +112 B (-2,048) | +88 B (-1,504) | -9 B (+6,496) | +266 B (-2,784) |
| NEOPIXEL.start_asy_signal | +422 B (+2,784) | +509 B (+4,960) | +585 B (+14,528) | +329 B (+1,632) |
| SYSTEM.start_asy_status | -109 B (+1,664) | +163 B (-1,824) | +36 B (+9,216) | +9 B (-3,904) |
| SCD30.start_asy_read | -67 B (+672) | +198 B (+0) | +123 B (-7,648) | +268 B (+11,840) |
| SCD30.start_asy_irq | -220 B (-1,024) | +202 B (-3,008) | +260 B (+8,608) | +48 B (+9,120) |
| SGP40.start_asy_read | -79 B (-480) | +187 B (-352) | -44 B (-6,336) | +146 B (-6,592) |
| NOTIFY.start_asy_monitor | -159 B (+1,600) | +206 B (-256) | -12 B (-64) | +118 B (-4,832) |
| NOTIFY.start_asy_pause | +194 B (-2,144) | +25 B (-8,544) | -260 B (-7,168) | +45 B (-9,664) |
| WEBSERVER.start_asy_serve | -19 B (-6,176) | -43 B (-4,064) | +124 B (-1,472) | +202 B (-384) |
| BMP3XX.start_asy_read | — | — | -112 B (-9,088) | -36 B (+7,392) |
| BMP3XX.start_asy_trigger | — | — | -80 B (+5,568) | -9 B (-9,632) |
| ISL29125.start_asy_read | — | — | -139 B (-8,352) | -86 B (-4,288) |
| ISL29125.start_asy_trigger | — | — | -55 B (-6,720) | -43 B (+4,160) |
| UART_init.start_asy_exercise | — | — | -21 B (+8,256) | +168 B (+9,568) |
| UART_resp.start_asy_listen | — | — | -70 B (-8,288) | +71 B (-8,032) |

**From WIFI.start_asy_hotspot_timeout down, every kind is flat.**
- Slopes are -260 to +585 B per restart, and their sign changes between stages and devices.
- The spread is inside the running device's own sawtooth, which is about ±10 KB.

**The WIFI.start_asy_connect and WIFI.start_asy_uptime rises are the boot warm-up, not the restarts.** Those two kinds run first, in the first ~100 s after boot. Three controls show it:
- **No-restart control** (ctl_arzi_m1, 200 samples at 2 s): +57 KB in the first 120 s with no restart at all, the same rise.
- **Late re-run** (late_{arzi_m1,arzi_t,dev_m1}): the same two kinds, 60 restarts each, after a 200 s settle.
  - Slopes: connect +169 / +353 / +259 B per restart; uptime +77 / +73 / +77.
  - This matches the control's own time-driven rate at that age, about 130 B per 2 s period.
- **Long no-restart control** (ctl_long_{m1,t}, 1500 s): the device plateaus.
  - From 900 s to 1500 s: -3,200 B at -1 and +9,088 B at 32768, inside the sawtooth.
  - A container-size walk at 150 s, 600 s and the end found that only three containers grow:
    - the twin NeoPixel's `_pixel.writes` (36 → 200);
    - the twin WDT's `feed_times` (88 → 200);
    - `_async_harness._tracked` (43 → 66, which compacts).
  - The first two are twin logs that reach their cap of 200. **No src/ or generated container grows.**

## Item 2: the per-boot holder

### What holds it
**A native Task keeps its last child.**
- A Task (extmod/modasyncio.c:45-51) embeds a pairing-heap node with three pointers: `child`, `child_last` and `next`.
- At pinned v1.29.0, nothing ever clears `child_last`:
  - `mp_pairheap_init_node` (py/pairheap.h:68-72) and `mp_pairheap_pop` (py/pairheap.h:93-97) clear only `child`/`next`;
  - `mp_pairheap_delete` (py/pairheap.c:89 ff.) clears only `child`/`next` as well;
  - only meld writes `child_last` (py/pairheap.c:52, :59).
- The GC scans every word of a heap block (py/gc.c:548-549). So a Task that was once a parent keeps its last child Task reachable after both have left every queue, and with it that child's coroutine frame.

**The chain in tests/test_digital_twin_ntp.py.** For each boot:
1. The boot's `sysfunct._supervisor_task` has a stale `child_last`. It points to that test's run_timed `wait_for` Task.
2. That Task's coroutine frame holds the test's `whole()`.
3. `whole()` holds the `built()` closure in `_booted()`.
4. `built()` captures `earlier = getattr(module, "webserver", None)`, which is the previous boot's webserver.
5. That webserver reaches the previous boot's whole graph, including its supervisor Task, and the chain repeats.

**Proofs** (pair6_*; 6 arzi boots; the probe allocates nothing between readings):

| run | -1, per re-boot | 32768, per re-boot |
|---|---|---|
| baseline | +147,424 B, at every re-boot | +147,424 B, at every re-boot |
| cut 1: zero the `child_last` word (via uctypes) of every Task each boot created, after the boot | +224 B once, then 0, 0, 0, 0 | +224 B once, then 0, 0, 0, 0 |
| cut 2: `earlier` holds the webserver's `id()` instead of the object; no other change | +224 B once, then 0, 0, 0, 0 | +224 B once, then 0, 0, 0, 0 |

Each cut alone removes the step, so both halves are needed.

### How it was located (logs in S/u35/laneB/hp1/)
- **Module-dict clears** (clear_*, cuts_a, cuts_b): every old boot hangs off the latest boot's graph. That graph is reached both from the device module's globals and from `microdot.print_exception`, which src/asy_webserver_service.py:564 rebinds to the latest webserver's bound method.
- **Attribute cuts on the latest boot's 12 instances** (cuts_allinst): only `sysfunct._supervisor_task` freed the old boots, 448,352 B, which is 3 boots. Cutting that Task's `data` and `state` freed nothing (cuts_task).
- **Raw read of that Task**, labelled by a create_task wrapper (raw_m1, pair_plain_m1): its word 2, `child_last`, points to that test's `wait_for` Task.

### Ruled out (cheapest first)
- **Twin registries.** `machine`/`network` are reset after each boot. A BFS walk over module, class and instance dicts plus Task fields (walk_ntp_m1) finds exactly one instance of each product class and identical type counts at every boot.
- **The asyncio IO queue.** `io_map` is 0 after every boot. Unix's `poll.unregister()` nulls the value (extmod/modselect.c:509-517).
- **`micropython.schedule`.** Its queue is bounded.
- **Module- and class-level references in src/ and the generated modules.** The walk saw no container grow, and cutting every attribute of the Microdot class freed nothing.

### Two side facts, for the record
- **Instance `delattr` keeps the old value.** `del obj.attr` on an instance leaves the old value in the member table (py/objtype.c:805 does not null it, unlike dict deletion). src/ has no `del self.x`. My probes overwrite instead, because a delattr bisection frees nothing.
- **rp2 only, a reading that only silicon can settle (hardware round).**
  - rp2 builds with `MICROPY_PY_SELECT_POSIX_OPTIMISATIONS` = 0 (py/mpconfig.h:1893). There, `poll.unregister()` leaves the `poll_obj_t`, and so the unregistered stream, in its map slot until the slot is reused (extmod/modselect.c:509-520).
  - The Unix port sets it to 1 (ports/unix/variants/mpconfigvariant_common.h:110), so the twin cannot show it.
  - It is bounded by the poll map's size. A heap reading after many webserver connections would settle whether it matters.

## Item 3: decision
- **The step is a test-process artefact.** It needs the test's own boot-to-boot link (`earlier`). Silicon runs `build_system()` once per power-up. It is not a twin defect, so it is not fixed (brief item 3).
- **The stale pointer itself is upstream C.** asyncio's TaskQueue uses it on rp2 too. There it can keep a finished task, with its frame, reachable from a live Task that was once its parent. The restart runs exercise exactly that path for every kind and show no accumulation. So under the brief's rule it is not a firmware defect, and there is no red-first test to write.

## Questions for the owner
1. **Report the stale `child_last` to MicroPython upstream?** The fix would be to clear `child_last` wherever `child` is set to NULL (init_node, pop, delete). Recommendation: report it upstream, and add no `toolchain/micropython_overrides.py` override for now. No growth is measured on any restart path, and an override is a firmware C fork decision. Revisit if the hardware round's heap readings drift.
2. **Make the ntp test hold the previous webserver's `id()`?** It is a one-line change in `_booted()`'s `earlier`/`built()` and removes 147 KB per re-boot from that test process. Recommendation: optional and low value. It is not a defect, and the file's peak, about 4 MB, is far below the 16M heap.
3. **For the lead: record the mechanism in SPECIFICATION.md Part F?** One short Part F paragraph would stop a later session from re-diagnosing per-boot twin heap growth as a product leak. The paragraph would say: a Task's pairing-heap `child_last` is never cleared, so a finished task can stay reachable through a live one; a heap step that repeats per in-process boot means a test linking its boots.

nothing of mine is running
