# Bench sitting, 2026-09-23 — the connection-scaling handover, run on silicon

**Read this file alone.** It assumes no knowledge of the branch or the session that produced it.
Temporary, like every other handover here: delete it once each open row below is resolved and each
closed result has been migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`.

Board: dev bench, RPI_PICO_W, MicroPython 1.29.0, `DebugLevel = 5`, IP 192.168.85.57.
Branch: `claude/tcp-connection-scaling` (which **fully contains** `claude/heap-fragmentation-remediation`
— checked with `git merge-base --is-ancestor`, so every measurement here is against the remediated
tree, not a stale one).

---

## 0. The one thing to read if you read nothing else

`REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md`'s whole decision table is **answered**, and the
shipped `max_connections = 7` works — *with* `gc.threshold(32768)*, which the generated boot entry
sets. **At MicroPython's own reactive default of `-1`, the highest concurrency this board serves
without a single allocation failure is 4** (§4). That contradicts a claim
`HEAP_FRAGMENTATION_MEASUREMENTS.md` currently makes, and it is the one genuinely open question this
sitting leaves behind.

lwIP was never the binding constraint anywhere in this work. The GC heap was, every time.

---

## 1. What was run, in order

| # | What | Result |
| --- | --- | --- |
| 1 | `GET /status` errcount captured **before** anything wrote | §2 |
| 2 | Image A built + flashed (`buildDate 2026-09-23T07:06:56Z`) | lwIP macro verification PASS |
| 3 | Ceiling probe, serving rows, page-load row | PASS (§3.1) |
| 4 | Image B built + flashed (over-provisioned, `max_connections = 16`) | no admission wall; **service** wall found (§3.2) |
| 5 | Image A rebuilt + reflashed (`buildDate 2026-09-23T07:41:10Z`) | RAM figures byte-identical to step 2 |
| 6 | Serving sweep A vs B, error logs reset first | §3.3 |
| 7 | Flash tier, default | **36 passed, 3 skipped, 12 deselected**, 15:16 — clean |
| 8 | Bench tier, default (first attempt) | **37 failed, 21 errors** — caused by a defect of mine, §5.2 |
| 9 | Bench tier, default (after the fix) | **103 passed, 4 skipped, 27 deselected**, 43:50 — clean |
| 10 | Heap at a genuinely sustained full ceiling | PASS (§3.4) |
| 11 | Stability sweep at `gc.threshold(-1)` under combined load | **§4 — the open finding** |
| 12 | Bench tier with `--allow-persistence-writes` (S3) | see §7 |

**Three flash cycles were spent** (A, B, A). Image C was never needed and neither was an
`LWIP_STATS` build — §3.2 explains why both became unnecessary.

## 2. The pre-sitting FRAM error logs (verbatim, before anything wrote)

Read at 08:59:33 local, uptime 22 s, on the pre-branch image (`buildDate 2026-09-22T16:11:57Z`).

| module | counter | history, oldest → newest |
| --- | --- | --- |
| SGP40 | 12 | `W13 W13 W13 W13 W13 W13 W13 W13 W13 W11` |
| WIFI | 21 | `N0 N0 N0 W10 W6 W5 W4 W5 W6 W6` |
| the other 19 | 0 | `N0` ×10 |

- SGP40 `W13` = "Backup written without timestamp" (`asy_sgp40_driver.py:440`), `W11` = "Backup
  loaded without timestamp" (`:379`). Benign — NTP had not synced when the backup was written.
- WIFI `W4` = "WLAN wrong password" (`asy_wifi_service.py:607`), `W5` = AP not found, `W6` =
  connection failed. **The `W4` is queue row R3 / BACKLOG item 29's spurious `W4`, sitting in the log
  on a network whose password never changed.** Recorded here because this sitting then ran isolated
  device scripts, which build their own `AsyFramManager` over the same chip and overwrite
  production's chunks — so this table is the trustworthy reading, and anything later is not.

## 3. The decision table, filled in

### 3.1 Image A — the shipped setting (`max_connections` 7, PCB 10, SEG 56, `MEM_SIZE` 14000)

| # | Question | `[HW]` answer |
| --- | --- | --- |
| 1 | Admits exactly the configured 7? | **Yes — 7, 7, 7, 7, 7** over five probes |
| — | How does the refusal present? | **Clean FIN, 6 ms after connect.** Not an RST, not a silent drop, not a stall |
| 2 | Serves all 7 completely? | **Yes** — bodies complete and parsed, inside 30 s |
| 3 | Concurrent page load byte-identical? | **Yes** — 6 concurrent index loads, all 9,292 B |
| 4 | Any FRAM-backed module logged a new error? | **No** |
| 10 | Any watchdog reset, anywhere in the sitting? | **None** |

ELF, image A: `.bss` **53,676 B**, `.data` **18,208 B**, FLASH 1,118,412 B (91.02 %), RAM 74,156 B
(28.29 %), GC heap `__GcHeapEnd - __GcHeapStart` = **190,036 B**.

**The build's own lwIP verification passes on the real image**: all 11 settable macros read back out
of the firmware's own translation unit (preprocessing lwIP's `opt.h` with the exact flags CMake
compiled `firmware` with) equal what `toolchain/versions.toml` asks for.

### 3.2 Image B — over-provisioned (`max_connections` 16, PCB 19, SEG 128, `MEM_SIZE` 32000)

**Row 5, the wall: there is no admission wall below 16.** `discover_max_connections(probe_limit=64)`
returned **16, 16, 16, 16, 16**. The application ceiling is what stops the probe, not lwIP — so the
raised ensemble genuinely works on silicon and the shipped 7 has **≥ 2.3× admission margin**. Image C
was therefore unnecessary.

**But admission is not service.** At 16 the board admits all 16 and serves 13; the page-load row
returned only 4 complete bodies out of 16, the rest truncated to 3,072 B or empty.

**Row 6, which pool ran out: none of lwIP's — the GC heap.** Captured live off the serial console
during a 16-wide burst, so this is measured, not inferred, and **`LWIP_STATS` was never needed**:

```
asy_webserver_service.py:279 _get_status → :295 _build_status_pieces
  → :43 _append_coalesced_object → :37 _coalesce_json_fragments
MemoryError: memory allocation failed, allocating 862 bytes
asy_webserver_service.py:279 _get_status → :293 _build_status_pieces → :321 _dump_errcount_entry
MemoryError: memory allocation failed, allocating 296 bytes        (×2)
asy_webserver_service.py:161 _get_measurements → :54 _stream_dict_response → :49 _append_coalesced_object
MemoryError: memory allocation failed, allocating 509 bytes
```

The failing allocations are **small** (296–862 B): exhaustion under concurrent streaming, not one
oversized request. Under `SPECIFICATION.md` Part I.4(e) a caught-and-degraded `MemoryError` is a
failure, so image B fails the memory bar at its own configured ceiling.

ELF, image B: `.bss` **74,592 B**, GC heap **169,120 B**.
**The per-connection permanent cost reproduces exactly**: 74,592 − 53,676 = 20,916 B for 9 more
connections = **2,324 B each**, matching the `[BUILD]` figure in `CONNECTION_SCALING_PLAN.md` §8.1
to the byte, from two real ELFs built hours apart. The GC heap fell by precisely the same 20,916 B.

### 3.3 The A-vs-B comparison — identical sweep, identical load shape

| N | image A (shipped, ceiling 7) | image B (over-provisioned, ceiling 16) |
| --- | --- | --- |
| 4 | 4/4 `{200:4}` | 4/4 `{200:4}` |
| 6 | 6/6 `{200:6}` | 6/6 `{200:6}` |
| **7** | **7/7 `{200:7}`** | **6/7 `{200:6, 500:1}`** |
| 8 | 7/8 `{200:7, refused:1}` | 7/8 `{200:7, 500:1}` |
| 10 | 7/10 `{200:7, refused:3}` | 8/10 `{200:8, 500:2}` |
| 12 | 8/12 `{200:8, refused:4}` | 9/12 `{200:9, 500:3}` |
| 14 | 10/14 `{200:10, refused:4}` | 11/14 `{200:11, 500:3}` |
| 16 | 7/16 `{200:7, refused:9}` | 13/16 `{200:13, 500:3}` |

Image A's error logs were **reset immediately before its sweep, and every module's counter read 0
afterwards** — zero entries at every N up to 16. Image B's sweep was not reset-isolated, so its E4
count (28) is not strictly attributable; the tracebacks above are the direct evidence there.

**The qualitative difference is the finding.** Above its ceiling image A *refuses* — the excess
arrives as a reset, reject-when-full working exactly as designed, and every admitted request still
returns a complete body. Image B *admits* the work and then fails it with a 500. **A raised ceiling
does not buy capacity; past the point the heap can serve, it converts a clean refusal into a
served-but-broken response.** And the ceiling is paid for out of the same 264 KB: image B's 9 extra
connections cost 20,916 B of the very heap that serves them, which is why its first 500 lands at
**N = 7** — exactly where image A is still clean.

Image A serving ">7" at N = 12/14 is **not** over-admission: requests complete and free slots during
the burst, so more than 7 are served across the burst's whole duration. The instantaneous ceiling is
still 7, which `discover_max_connections()` proves separately.

### 3.4 Rows 7 and 8 — the heap at a genuinely sustained full ceiling (image A)

```
[HW] ceiling=7 held=6-7, at ceiling 146/149 samples (98%)
```

| point | free | largest free run | **placeable 2,048 B blocks** |
| --- | --- | --- | --- |
| after boot | 49,360–57,680 B | 37,504–39,296 B | **19** |
| at peak, worst of ~70 samples | — | 32,288–34,048 B | **15** |

The simultaneous demand is 7 buffers; the board holds room for **15** while all 7 are parked
mid-request, and the largest free run falls only ~15 % under full load. Comfortable.
**Note this runs at `gc.threshold(-1)`** (§4 explains why) — but it only *holds* connections parked,
it does not make them serve full responses, which is what §4 does.

### 3.5 C5c — can `PBUF_POOL_SIZE` stay at 16? **Yes.**

Nothing in lwIP or in this repo checks the *aggregate* of a per-connection option against a shared
pool, and two such over-commits exist by construction:

| image | inbound `N × TCP_WND` vs `PBUF_POOL` capacity (12,832 B) | outbound `N × TCP_SND_BUF` vs `MEM_SIZE` |
| --- | --- | --- |
| A (N=7) | 44,800 B — **3.5×** | 44,800 B vs 14,000 — 3.2× |
| B (N=16) | 102,400 B — **8.0×** | 102,400 B vs 32,000 — 3.2× |

**Neither bound.** At an 8× advertised inbound over-commit the pbuf pool never surfaced, because
real inbound demand is one small capped request per connection. `cyw43_lwip.c:281` confirms every
received packet is allocated `PBUF_POOL`, so the pool really is the inbound path's — it simply never
ran out. The GC heap bound first, in both images.

---

## 4. THE OPEN FINDING — maximum stable concurrency at the reactive gc default is 4

`buildgen/codegen.py:702` puts `gc.threshold(32768)` in the generated **boot entry**, not in
`main()`. Everything in §3 that went through a normally booted board therefore ran *with* the
threshold set.

To measure without it: `tests_hardware/device_scripts/serving_stability_under_combined_load.py` runs
the real `sensortask_dev.main()` task graph and calls `gc.threshold(-1)` explicitly — explicitly,
because **`mpremote` interrupts `main.py` but does not reset the interpreter**, so the boot entry's
own 32768 is still in force when a device script starts. The first attempt reported
`GC_THRESHOLD=32768` and had to be redone.

Combined load = the real task graph (every sensor, the UART link exerciser, NTP, the webserver) with
the host driving **12 rounds of N concurrent requests** across `/status`, `/sensors`, `/`,
`/measurements`, `/networking`, `/system` — both streaming endpoints and the largest static response
included. Driven from the host, so nothing competes with the DUT's heap (Part E.9).

| N | served | **`MemoryError` lines** | worst placeable 2 KB | worst largest free run |
| --- | --- | --- | --- | --- |
| 7 (shipped ceiling) | 64/84 | **28** | 0 | 800 B |
| 6 | 57/72 | **18** | 0 | 864 B |
| 5 | 48/60 | **14** | 0 | 768 B |
| **4** | 45/48, then 44/48 on repeat | **0**, **0** | 1 | 2,192 / 3,376 B |
| 3 | 33/36 | **0** | 0 | 688 B |
| 2 | 22/24 | **0** | 0 | 976 B |

**5 is the first level that fails**, and it fails exactly as image B did —
`MemoryError: memory allocation failed, allocating ~870 bytes` inside `_stream_dict_response()`,
surfacing as a 500 on `/status`. At 7 the heap is driven down to an 800-byte largest free run.

The `ConnectionResetError` appearing at every level is **one per distinct path in the first round**,
while the board settles; it is not a failure mode and does not scale with N.

### What follows from it

1. **The shipped 7 depends on `gc.threshold(32768)`.** With the threshold set, 7/7 serves cleanly and
   the whole bench tier is green (§1 rows 7 and 9). Without it, 7 is not stable. CLAUDE.md's standing
   rule is that a threshold is defence in depth and *"is forbidden as the fix itself for a design
   that still needs one"* — by that rule, 7 does not currently stand on its own.
2. **A documented claim is contradicted on silicon.** `HEAP_FRAGMENTATION_MEASUREMENTS.md` states
   *"whether the system is stable without the threshold is settled and the answer is yes"*, resting
   on the unit tier (85/85 files) and the twin CI. **Neither runs lwIP, the real sensor set, or real
   concurrent HTTP.** That sentence needs qualifying to the tiers that actually support it.
3. **The number is measured on image A's ensemble, which is sized for 7.** An image right-sized for 4
   would return roughly 6 KB of heap (`MEM_SIZE` 8000 vs 14000, `MEMP_NUM_TCP_SEG` 32 vs 56), so 4
   has more margin than shown and **5 might pass**. Pinning that boundary costs one build and one
   flash, and has not been done.

### What is NOT claimed

That 7 is unsafe in production. The shipped firmware sets the threshold, and with it set every tier
is green. What is claimed is narrower and is the project's own bar: the design does not currently
survive its own ceiling at MicroPython's default, so the threshold is load-bearing rather than
defence in depth.

---

## 5. Defects found and fixed

Every one was in an instrument that had **never been executed on hardware**. Each failed silently
rather than loudly, which is the part worth carrying forward.

### 5.1 `discover_max_connections()` could never measure a ceiling — `tests_hardware/harness.py`

The probe dwelled `settimeout(10.0)` per connection. The server closes an idle admitted connection
after `per_call_timeout_s = 5.0`, answering `HTTP/1.0 400 N/A` rather than a bare FIN — **measured at
5.12 / 5.14 / 5.16 s**. So every connection died before the next was opened, at most ~2 were ever
held at once, and against a board whose true ceiling was 4 the probe walked past 12 and raised *"the
ceiling is higher than this probe looks"*.

**Fixed**: `dwell_s = 0.3`; a hard failure if a held connection answers instead of staying open (the
walk outran the timeout, so the reading is not a ceiling); and `_assert_probe_held()` re-checking
every counted socket is still open at the moment the refusal lands. Validated against the pre-branch
image at dwells 0.4 / 0.25 / 0.15 s: **4, 4, 4**.

### 5.2 No settle after filling the ceiling — `harness.py`, and it cost a suite run

A slot is released in `_serve()`'s `finally`, *after* the writer close is awaited, so it outlives the
client's own close — **measured at 0.818 / 0.842 / 0.709 s**. A caller that has just measured the
ceiling has filled it, so its next request is refused; the ceiling test died with
`ConnectionResetError`. **Fixed** with `_wait_for_slots_to_drain()` inside the probe's own `finally`,
so the guarantee lives in one place instead of being a per-call-site obligation.

### 5.3 The heap-at-peak holder never held a peak — `tests_hardware/bench/test_heap_under_connection_ceiling.py`

Four separate defects, in layers, each only visible once the one above it was fixed:

- **It could not hold anything.** It opened N connections with partial headers and slept for
  `_HOLD_S = 55.0`, recording the count *at open time*, so `held_out[0] == ceiling` passed while every
  sample after ~5 s measured an idle heap. Measured: a parked connection with no further bytes is
  closed after **5.35 / 5.40 s**; dripping a header line every 2 s extends it to **15.08 / 15.13 s**,
  which is `outer_cap_s = 15.0` exactly. **No connection can be held longer than ~15 s on this
  firmware**, so a 55 s hold is impossible by construction.
- **My first rewrite expired in lockstep.** All N workers started together, so all N hit the 15 s cap
  together and the live count oscillated 7 → 0 → 7. Fixed by staggering each worker by
  `i × _RECYCLE_S / N` and recycling proactively at 10 s, inside the cap.
- **My holder's daemon threads outlived their test — this is what produced the 37-failure bench run.**
  `hammer.join(timeout=30.0)` returned while 7 workers kept connecting in a retry loop, and they then
  hammered the DUT for the rest of the pytest session. The cascade begins exactly at this test and
  every network-facing test after it fails. Fixed with a `threading.Event`, an unconditional `finally`
  that sets it, a real join, and an assertion that the holder is not still alive.
- **It never put the board back.** `run_isolated()` leaves `main.py` stopped, so the webserver is
  gone; this is the *only* bench test that runs a device script, and every bench test after it failed
  on a refused connection. Fixed with `_restore_board_to_serving()` — `kick_all_stations()` (stale
  AP-side entries stop the DUT reassociating) → `hard_reset()` → wait for real HTTP.

### 5.4 The device script and its parser were written to different contracts

`heap_under_connection_ceiling.py` emitted `<<<MEM label` / `MEM>>>`; `heap_map.parse_labelled()`
matches `=== MAP <label> ===` / `=== ENDMAP <label> ===`. Every dump was discarded and the test saw
zero maps. **Fixed** in the device script, to the format the other, working script already uses.

### 5.5 `gaps_at_least()` was the wrong metric for a simultaneous demand — `tests_hardware/heap_map.py`

It counts free *runs* at least N long, so one 40 KB run reads as **1** — and the test asserted
`>= ceiling`, which a healthy board can never satisfy. The question is capacity, not gap count
(handover §5B rule 10). **Added `HeapMap.placeable(size)`** (`sum(run // size)`), used it there, and
pinned the distinction in `tests_scripts/test_heap_map_parser.py`.

### 5.6 Two wrong constants in the lwIP ensemble checker — `toolchain/micropython_overrides.py`

`ports/rp2/lwip_inc/lwipopts.h` sets **`LWIP_IPV6 = 1`**, so `pbuf.h:80` takes `PBUF_IP_HLEN = 40`,
not 20. Ground-truthed out of the real firmware translation unit: `PBUF_IP_HLEN = 40`,
`PBUF_TRANSPORT_HLEN = 20`, `PBUF_LINK_HLEN = 14`, `PBUF_LINK_ENCAPSULATION_HLEN = 0`.

- `_PBUF_PROTOCOL_HEADER_BYTES` was **54**, is **74**.
- `PBUF_POOL_BUFSIZE` was derived as **856**, the compiler's own value is **876**.

**The two errors cancel exactly** in the one check where both appear (`TCP_WND` against
`PBUF_POOL_SIZE × (BUFSIZE − headers)`: the usable 802 B/pbuf is identical either way), so **no
verdict this repo ever reported was wrong** — but the pool's real RAM cost was understated by 20 B
per pbuf (16 × 876 = 14,016 B, not 13,696 B). Both fixed, with a test pinning the IPv6-derived value.

## 6. The independent lwIP audit (asked for explicitly, and worth keeping)

All **18** relevant `#error` conditions were re-derived from `lib/lwip/src/core/init.c` rather than
trusted through `check_lwip_ensemble()`, with the switches that decide which checks are live at all
ground-truthed out of the real translation unit:

| fact | value | why it matters |
| --- | --- | --- |
| `LWIP_DISABLE_TCP_SANITY_CHECKS` | undefined → 0 | **every** TCP sanity check really is live |
| `MEMP_MEM_MALLOC` / `MEM_USE_POOLS` | 0 / 0 | the memp pool checks are live |
| `LWIP_NETCONN` / `LWIP_SOCKET` | 0 / 0 | **`MEMP_NUM_NETCONN` is genuinely dead on this port**, confirming the PR's own correction |
| `MEM_ALIGNMENT` | 4 | the alignment `derive_lwip_dependents()` assumes |
| `LWIP_WND_SCALE` | 0 | so `TCP_WND` must fit `u16_t` |
| `TCP_MSL` | 60000 ms | and `tcp_alloc()` reclaims the oldest TIME_WAIT only **after** `memp_malloc()` has already failed — the margin argument for PCB 10 vs 7 is sound |

Derived values confirmed against `opt.h`'s own formulas: `TCP_SND_QUEUELEN` 32, `TCP_SNDLOWAT` 3200,
`TCP_SNDQUEUELOWAT` 16, `PBUF_POOL_BUFSIZE` 876.

**Images A, B and C: zero failing conditions each.** The ensembles are globally coherent.

## 7. Suite results on this image

| Suite | Result |
| --- | --- |
| Flash tier, default | **36 passed, 3 skipped, 12 deselected**, 15:16 — clean |
| Bench tier, default | **103 passed, 4 skipped, 27 deselected**, 43:50 — clean |
| Bench tier, `--allow-persistence-writes` (S3) | **RUNNING when this document was written — the next session must read `bench_persist.log` and record the outcome here** |

D1's ordering condition (a clean default run before the gated one) is **satisfied on this image** by
the two rows above. Read the *deselected* count, not just the word "clean": the wear gates deselect
rather than skip, so "everything that ran, passed" is not "everything ran".

## 8. What is still owed

| # | Row | Why |
| --- | --- | --- |
| 1 | **Record S3's result** | It was still running; §7 has the log path |
| 2 | **Decide what to do about §4** | The threshold is load-bearing at the shipped ceiling. Owner's call: lower `max_connections`, relieve the allocation pressure in `_stream_dict_response()`, or accept the threshold as load-bearing and say so in the docs |
| 3 | **Qualify the claim in `HEAP_FRAGMENTATION_MEASUREMENTS.md`** | "stable without the threshold … yes" holds for the unit tier and the twin, not for the board under combined load |
| 4 | **One more image, if the exact boundary is wanted** | A right-sized N=4 (or N=5) ensemble returns ~6 KB of heap; 5 might pass. One build, one flash |
| 5 | R1, R2, R3, R4, R5, R6, R7, R8, R9, R13 | Untouched by this sitting. **R3 has fresh evidence**: the spurious `W4` is in §2's log |
| 6 | M1, S3b, S4, F1, T1, T2, T4, G1/G3/G4/G6/G8/G10, H1 | Untouched |

## 9. Traps this sitting learned the hard way

- **An instrument that has never run is not evidence.** Six of the defects above sat in code that
  read correctly and had never executed once. Every one failed *silently* — a count recorded before
  it could decay, a parser that matched nothing, a metric that answered a different question.
- **Any host-side load generator must be stoppable and joined.** A daemon thread that outlives its
  test does not fail that test; it fails the next thirty-seven.
- **`mpremote` does not reset the interpreter.** Anything a device script wants to know about global
  state — `gc.threshold()` above all — it must set explicitly, not inherit.
- **A `pgrep -f "<pattern>"` wait loop matches its own command line.** A waiter written that way
  never exits. Wait on a marker in the log instead.
- **Two suites that both bind real ports must not overlap** (already in CLAUDE.md) — and the same
  applies to a device script that stops `main.py` while later tests still need the webserver.

