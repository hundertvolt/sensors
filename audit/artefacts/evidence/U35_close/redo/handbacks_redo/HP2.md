HP2 hand-back, written by the lane (2026-10-27 12:05 UTC)

Worktree S/wt-u35hp1, branch audit/u35-hp1 at 5a8c6e35. **No commits**: nothing here belongs on the branch, because every change is a probe and no test changed. The tree is clean: `node_modules` is the link that was there at the start, and `tests/_tmp` is gone. Nothing is pushed.

Everything is in S/u35/laneB/hp2/:
- the probe (`probe_extra.txt`, plus `atb.py` for the GC allocation-table reader);
- the load client (`client.py`);
- the wrappers (`hp2run.sh`, `mp1.sh`, `pair.sh`);
- the summarisers (`summ.py`, `cutsumm.py`);
- one log per run (`<label>.log`, `<label>.client.log`), and `times.txt`.

The probes are scratch copies of tests/test_digital_twin_ntp.py in `hp2/probe/`, outside the worktree, as HP1's were. RUNS.md lines are named "U35 lane HP2".

## Verdict
**Bounded. Not a firmware defect.** No patch was built: the brief's item 3 says build one only if the pinned set grows.

Under the product's own task patterns, on arzi and dev at -1 and 32768, the stale `child_last` holds at most **8 finished Tasks at any instant**. The longest chain is **2**. Neither number trends with uptime (1,260 s) or with connection count (4.5-7.2k per run).
- **Worst exact cut:** 4 Tasks and **28,064 B** in one 15 s interval (dev at 32768, mixed load). That figure includes a collector noise floor of about 2.8 KB.
- **Per pinned connection handler:** about 4.7-6.3 KB (64-bit twin).
- **At rest:** 1-2 Tasks, 4.1-9.4 KB.

## Item 1: existing evidence (targeted reads)
- **Twin CI Run 11** (`scripts/_digital_twin_ci_suite.py` `_run_11_soak()`, `digital_twin/README.md` "Run 11's calibrated numbers").
  - Runs for every device at both GC stages (ci.yml `digital-twin-e2e` matrix).
  - Host-driven serial GETs over every GET route and `/`: warm-up to a plateau, then 80 measured cycles.
  - A `MEM_SAMPLE` every 100 ms, taken after a `gc.collect()`. The tolerance is 4x the in-quarter noise, about 23 KB on dev.
  - Calibrated against a planted 40 B per-request leak, which turned it red at a 55-59 KB decline.
  - **Covers:** a serial-GET retention that averages about 40 B or more per request, over about 1.4k requests.
  - **Does not cover:** overlapping connections or rejections at the ceiling; PUTs; NTP/DNS churn (the natural cadence is at least 1 h); uptime past its window. It also measures the whole heap, not the set that `child_last` holds.
- **HEAP_FRAGMENTATION_MEASUREMENTS.md** M4.2 (rounds of N=4/5/7, failure counts against heap size) and M5.1 (`serving_at_default_gc.py`, `heap_under_connection_ceiling.py`). These bound fragmentation and failure thresholds, not retention against uptime. **No record bounds a `child_last` chain.**
- **HP1's controls** (1500 s plateau, restarts) cover only an idle device and restarts.

## Item 2: the walk

### Method
**Boot.** HP1's boot on the real clock: the real `main()`, the webserver on fixed port 18080 inside the namespace, and `-X heapsize=32M` (the instrument's tables take about 6 MB).

**Recording.** Every Task is recorded at creation: `asyncio.core.create_task` and `asyncio.create_task` are patched before the boot. That catches `loop.create_task`, stream.py's per-connection task and `wait_for`'s runner. The recorded addresses are stored XOR-masked.

**Liveness oracle.** Liveness comes from the GC's own allocation table:
- It is located from `/proc/self/maps` per py/gc.c `gc_init`/`gc_setup_area`: `end` is aligned down to a block, and there is a 16 B malloc header.
- Validated: 50 of 50 live Tasks read as head blocks, and 50 of 50 dropped ones read as free.
- A user-class `__del__` never runs on this build (0 of 200 flagged), and `weakref` is not compiled in.

**Walk, every 15 s.**
1. `_async_harness._compact()`, so the harness's list drops its finished tasks.
2. `gc.collect()`.
3. For every live Task, read the `child`, `child_last` and `state` words. A stale edge is `child == NULL` with `child_last != NULL`.
4. Follow the chains from every unfinished Task, and from every finished Task that something else holds.

**Cuts.**
- **Final cut:** zero every stale `child_last` (the upstream patch's semantics, applied in place), `gc.collect()`, then count the Tasks and bytes freed. Those are exactly the ones reachable only through it.
- **Cut arm:** the same cut at every walk.

**Load.** A CPython client in the same namespace, on this schedule:

| s | phase |
|---|---|
| 0-120 | settle |
| 120-300 | NTP/DNS churn: the product's own `_ntp_sync_trigger_event` set every 1.5 s; NTPHost is a hostname resolved through DNSFallback 127.0.0.1 to the client's DNS responder (port 53 redirected) |
| 300-540 | serial: 8 GET routes, plus a malformed PUT every 10th request |
| 540-780 | bursts of 8 concurrent connections, which also exercise rejection at the ceiling |
| 780-900 | idle |
| 900-1140 | mixed: serial, bursts and NTP churn together |
| 1140-1260 | idle |

- About 280 syncs and about 280 DNS answers per run.
- The server's connection count equals the client's ok+err count (for example 7,166 = 5,708 + 1,457 + 1), so the "err" ones are the ceiling rejections.

### Numbers (all rc=0, 0 memory markers)
**Stock runs:** the walk at every interval, one cut at the end.

| run | conns | tasks | pinned max | serial / bursts / mixed / idle2 | chain max | final cut |
|---|---|---|---|---|---|---|
| arzi -1 | 7,166 | 170,677 | 8 | 4 / 6 / 8 / 4 | 2 | 2 Tasks, 4,096 B |
| arzi 32768 | 5,947 | 140,689 | 6 | 4 / 5 / 6 / 3 | 2 | 4,096 B |
| dev -1 | 6,081 | 159,135 | 6 | 5 / 6 / 6 / 3 | 2 | 1 Task, 4,352 B |
| dev 32768 | 4,579 | 119,889 | 5 | 5 / 5 / 5 / 4 | 2 | 9,376 B |

- The Task count of the two 32768 final cuts misread as 0: that count had no type-word check, and its own temporaries reuse the freed blocks. The bytes are right. The count was fixed for the later runs.
- In the idle phases the set falls back to 1-5 Tasks, the same after 7k connections as after 3k.

**UART exerciser only** (dev, 285 s, no HTTP, no NTP churn):

| stage | transfers / failures | pinned max | chain max | final cut |
|---|---|---|---|---|
| -1 | 265 / 0 | 2 | 1 | 2 Tasks, 5,056 B |
| 32768 | ~255 / 0 | 2 | 1 | 1 Task, 4,352 B |

The UART also ran through the full dev runs: 1,084 transfers and 0 failures in cut_dev_t.

**Cut arm** (exact, per 15 s interval: what only `child_last` held since the last cut):

| run | conns | idle cuts | serial | bursts | mixed | in all |
|---|---|---|---|---|---|---|
| arzi -1 | 7,091 | ≤ 2 Tasks, mean 2.6-3.9 KB | ≤ 3, ≤ 12,960 B | ≤ 4, ≤ 21,664 B | ≤ 4, ≤ 20,736 B | 81 Tasks over 86 cuts |
| dev 32768 | 4,538 | ≤ 3 Tasks | ≤ 3, ≤ 17,504 B | ≤ 4, ≤ 27,392 B | ≤ 4, ≤ 28,064 B | 59 Tasks over 86 cuts |

- **The noise floor** (cuts that freed no Task) is about 2.8 KB.
- **No interval amount rises over the run.**

**What is pinned, and by what.**
- The pinned Tasks are per-connection `handle_request`/`_serve` Tasks and `wait_for`'s `_run` Tasks, and once the probe's own `_ntp_churn`.
- They are held by live heads that re-enter the run queue and so refresh the pointer: the `_serve` accept loop, `_refresh_loop`, `_signal_loop`, `_watch_chip_loop`, `_trigger_loop` and `main`.
- They are also held by the twin's own `_run_connect` (digital_twin/network.py) and `_countdown` (digital_twin/machine.py).

**Controls.**
- **Burst sweep** (`snip_burst`): 10 to 4,000 Tasks created at once, finished and dropped. The chain hanging from the creator's `child_last` is 0 at both stages.
  - A burst does link its own Tasks into one long chain: 199 long was seen while the unmasked table pinned everything.
  - That chain is garbage as soon as the burst's own list is dropped.
- **rp2's soft-timer heap** uses the same pairing heap. Its nodes are the product's Timer objects, and all 12 `Timer()` calls in src/ are in constructors. So a stale link there points at a live Timer, and there is no growth path.

## Item 3: decision
- **Bounded, as stated in the Verdict.** Instantaneous worst: 8 Tasks.
  - That instant was not cut. At the cut arm's worst of about 6.3 KB per pinned Task, it would be at most about 50 KB. This is an estimate, not a measurement.
  - rp2's 4-byte words make these objects roughly half the size.
- **Transient, but it falls at the peak.** The stale pointer keeps finished connection handlers' frames for the seconds until the head re-enters the queue. That happens during load, when the heap is tightest.
- Per the brief, there is no patch and no override decision.

## Item 4: the rp2 poll-map bound
**The twin cannot show it.**
- Unix's POSIX path NULLs the value on unregister.
- The twin's poll prewarm also pre-grows the asyncio poller's map to alloc 521.

**Measured instead: peak concurrent registrations** in asyncio's IOQueue (a hook on `_enqueue`):

| device | peak | idle set | enqueues in a full run |
|---|---|---|---|
| arzi | 12 | 11: 10 `ThreadSafeFlag` waits (the Timer-to-task flags) + the listening socket | 19-21k |
| dev | 16 | 15: 14 `ThreadSafeFlag` waits + the listening socket | 19-21k |

**Design ceiling.** Loopback requests arrive whole, so connection sockets rarely wait in the queue. Over WiFi they will.
- The ceiling is: the idle set + `max_connections` (6) + refused connections in flight (at most the backlog, 7).
- That gives 24 for arzi and 28 for dev.

**rp2 map growth** (py/map.c):
- The map rehashes only when every slot holds a live key. The sizes go 2, 4, 6, 8, 10, 12, 17, 23, 29.
- Alloc is 12 (arzi) or 17 (dev) at the twin's peak, and at most 29 at the design ceiling.
- A rehash copies only live keys, so stale values die at every growth.

**What a stale slot pins.** At most alloc minus the live registrations. Each one pins:
- one `poll_obj_t`: 12 B, so one 16 B block;
- its stream, and the only churning streams are connection sockets. A closed socket keeps only its `lwip_socket_obj_t`, about 60 B with IPv6 on, so 64 B: `incoming` is freed on close (extmod/modlwip.c:1670).

That is at most 80 B per slot.

**Bound:**
- about 1.4 KB at dev's twin peak (17 slots);
- at most 2.3 KB at the design ceiling (29 slots);
- independent of uptime.

**What the hardware round reads:**
- after a burst of connections and then quiet, `gc.collect()` and `mem_alloc()` against the reading before the burst;
- directly, the asyncio poller's map through uctypes. On 32-bit, `mp_obj_poll_t` words 1-3 are `used<<3|flags`, `alloc` and `table`; count the slots whose key is 0 or 4 (`MP_OBJ_SENTINEL`) and whose value is non-zero.

## Deviations
- **Concurrent runs in one worktree.** The two stock pairs (full_*_m1, then full_*_t) each ran two twin processes in the same worktree, against "one test run per worktree at a time". Both processes of a pair also shared one state directory, `tests/_tmp/digital_twin_ntp/1/`: the TmpScratch key plus its counter.
  - FRAM is in memory, and the config files carry the same values. The measured topology is unaffected.
  - The sequential runs reproduce the pairs' bounds: uart_dev_*, cut_arzi_m1 and cut_dev_t.
  - Every run after the pairs ran alone.
- **Instrument faults, fixed before any reported number:**
  - an unmasked address table pinned every Task (the GC scans a bytearray's words too);
  - the allocation table's end alignment;
  - the threshold runner's path to `atb`.
- **Smoke and failed runs** (their numbers are not used):
  - smoke_arzi: rc=1; the harness found a task left parked;
  - the first full_*_t: rc=1 after 1 s, ImportError;
  - smoke2_arzi and smoke3_arzi: rc=0, used only to check the instrument.

## Question for the owner (in prose)
HP1's question 1 (report the stale `child_last` upstream?) now has the measured bound behind it. My recommendation is unchanged: report it upstream, and add no `toolchain/micropython_overrides.py` override.

The retention never grows. Its whole cost is a transient hold on a few finished connection handlers during bursts: at most about 28 KB measured per interval on the 64-bit twin, roughly half that on rp2.

An override would fork the firmware's C for that. Revisit it if the hardware round's heap readings during a burst show it mattering against rp2's headroom.

nothing of mine is running
