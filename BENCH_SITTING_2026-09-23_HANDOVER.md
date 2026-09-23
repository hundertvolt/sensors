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

**Addendum, same day: the two ensembles this sitting's follow-up needs were audited the same way,
before the tip moved to one of them.** N = 8 (PCB 11 / SEG 64 / `MEM_SIZE` 16000 — **the ensemble
the tip now ships**, commit `79cb3b1`) and N = 10 (PCB 13 / SEG 80 / `MEM_SIZE` 20000): **zero
failing conditions each**, and `check_lwip_ensemble()` agrees. Their inbound over-commit is 4.0x and
5.0x, bracketed by image A's 3.5x and image B's 8.0x — neither of which bound (§3.5).

## 7. Suite results on this image

| Suite | Result |
| --- | --- |
| Flash tier, default | **36 passed, 3 skipped, 12 deselected**, 15:16 — clean |
| Bench tier, default | **103 passed, 4 skipped, 27 deselected**, 43:50 — clean |
| Bench tier, `--allow-persistence-writes` (S3) | **124 passed, 4 skipped, 6 deselected**, 53:55 — **clean, the first end-to-end green gated run** (2026-09-22's was `1 failed, 118 passed` and never re-run green) |

D1's ordering condition (a clean default run before the gated one) is **satisfied on this image** by
the two rows above. Read the *deselected* count, not just the word "clean": the wear gates deselect
rather than skip, so "everything that ran, passed" is not "everything ran".

**What S3 does and does not validate.** It ran on image A as rebuilt at step 5 (`buildDate
2026-09-23T07:41:10Z`, `max_connections = 7`, the pre-fix `src/`). The tip has since moved — the
bounded `_PieceWriter` in `asy_webserver_service.py` and `max_connections = 8` (commit `79cb3b1`) —
so **S3 is a clean baseline for the image before that change, not a validation of the tip.**
`REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md` §0.4's W4 re-runs the default tier on the tip; a gated
run on the tip is a separate decision, and the wear rule says not to repeat one unasked.

The 21 tests that ran only because of the flag all passed. The four skips are the expected opt-in
ones: the two NeoPixel-rig programs, the flash-cycle reflash test, and the hotspot tier's one
permanent entry. Three queue rows this run made reachable:

| row | what S3 shows |
| --- | --- |
| **R8** | **Closed.** Both tests ran on silicon for the first time and passed: `test_isl29125_calibrate_command_push_over_real_rest` and `test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value` — the adaptation to this branch's nested `PUT /sensors` body was where a first run was expected to go wrong, and it did not |
| **R5** | **A second green run** of the BMP3XX deferred-config-write arm (`test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load`, `test_bmp3xx_oversampling_and_filter_push_over_real_rest_and_readback`), after 2026-09-17's first. Whether two runs is "durable" is the owner's call |
| **R1, R4** | **Not answered.** They ride on the gated run but need their own investigation — R1 is a root-cause bisection (`RangeAuto=false`), R4 a pre-populate-then-sweep that no suite test performs. S3 passing says nothing either way |

## 8. What is still owed

| # | Row | Why |
| --- | --- | --- |
| 1 | ~~Record S3's result~~ — **done**, §7: 124 passed, clean | — |
| 2 | **Decide what to do about §4** — *root-caused and fixed in the twin the same day, limit set to 8 by the owner; silicon confirmation is `REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md` §0* | The threshold is load-bearing at the shipped ceiling. Owner's call: lower `max_connections`, relieve the allocation pressure in `_stream_dict_response()`, or accept the threshold as load-bearing and say so in the docs |
| 3 | **Qualify the claim in `HEAP_FRAGMENTATION_MEASUREMENTS.md`** — *done, §7H.3's note and §7Q* | "stable without the threshold … yes" holds for the unit tier and the twin, not for the board under combined load |
| 4 | **One more image, if the exact boundary is wanted** | A right-sized N=4 (or N=5) ensemble returns ~6 KB of heap; 5 might pass. One build, one flash |
| 5 | R1, R2, R3, R4, R6, R7, R9, R13 | Untouched by this sitting. **R3 has fresh evidence**: the spurious `W4` is in §2's log. R8 closed and R5 advanced by S3 (§7) |
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

---

## 10. Second sitting (afternoon) — `REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md` §0 on silicon

Run against tip `ece5772`/`0ce9f92` (the bounded `_PieceWriter`, `max_connections` 8, ensemble
PCB 11 / SEG 64 / `MEM_SIZE` 16000). Everything at **`gc.threshold(-1)`**, set explicitly by each
device script (`GC_THRESHOLD=-1` confirmed in every output). **Complete**: both images, W1/W2, and
the verified per-level answer in §10.6. The board is left on **F**.

### 10.1 Before anything

- `GET /status` read **before** any write (`DebugLevel` 5, uptime 7608 s, still image A):
  every module 0 except **NTP** 11 (ten `E` entries, nums 1,1,1,1,1,2,20,1,1,1) and **SYSTEM** 1
  (`W4`). These are leftovers of S3 and the morning's device scripts, not fresh evidence.
- After image G's run the log had grown (BMP3XX 8, FRAM 2, SYSTEM 10, UART_init 14, UART_resp 14,
  WEBSERVER 180, WIFI 3). Both §0 device scripts build their own `AsyFramManager`, so these are
  **not** clean evidence (CLAUDE.md FRAM caveat) — but BMP3XX/UART/SYSTEM entries appearing only
  after a run that exhausted the heap are consistent with sensor and link tasks failing too, not
  just HTTP.

### 10.2 Images, built and verified

| image | `max_connections` | PCB / SEG / `MEM_SIZE` | GC heap | lwIP macros in the TU | ensemble check |
| --- | --- | --- | --- | --- | --- |
| G (local edit, never committed) | 16 | 19 / 128 / 32000 | **169,120 B** | all 11 match | clean |
| F (the tip as it ships) | 8 | 11 / 64 / 16000 | **187,712 B** | all 11 match | clean |

G has exactly the **18,592 B** less heap the handover predicts. `devices/dev.toml` and
`toolchain/versions.toml` were restored with `git checkout` before F was built. Two flashes; the
board is now on **F**.

### 10.3 W1 part 1 — per-source/route allocation need: **PASS on both images, matches the twin**

`test_every_source_and_route_fits_a_small_free_run`: worst route **`/status` 320 B**, `/sensors`
and `/measurements` 256 B, `/networking` 192 B, `/system` 160 B, `/notification` 128-144 B, every
data/config source ≤ 144 B, every errcount entry 112 B. Twin prediction was 320 B / ≤ 192 B —
exact. **But the probe list has no static-file route** (`/`, `/<path>`), which is where the real
failure is (§10.5). The bounded writer does what it claims; it just does not cover everything.

### 10.4 W1/W2 sweep — `test_serving_sweep_at_the_reactive_default`: **FAILED on both images**

**Image G (ceiling 16, levels 4..18, cumulative on one boot):** 112 × `allocating 1025 bytes`, plus
~180 route failures at 172-257 B (the writer's own pieces, `_PieceWriter.flush`/`add`,
`asy_webserver_service.py:38-65`) and 1 × 232 B at `microdot.py:383` (`Request.__init__`). The
first 1025 failure came ~35 s into the load (board uptime 75 s), i.e. at the lowest levels. At the
first route failure (`fail1`): free 20,864 B but max free run **15 blocks = 240 B**; one dump later
free was 5,888 B — at G's high levels the heap is **exhausted**, not merely fragmented. The run
ended with the board's USB CDC vanishing (`OSError: [Errno 5]` in mpremote) at board uptime
~425 s, before the device script's own window closed — **the board reset itself under load**
(cause not captured; the fixture then hard-reset it). No tallies were printed because the device
script's run was the thing that failed.

**Image F (ceiling 8, levels 4/6/8/10):** tallies `N=4 {200:48}`, `N=6 {200:72}`, `N=8 {200:96}`,
`N=10 {200:96, refused:24}` — admission and clean refusal exactly as predicted — **but 11 ×
`allocating 1025 bytes`**. The tally reads "all served" because this test only reads the status
line (`_one_request()`), so a **truncated body counts as a 200**. That is an instrument gap (§10.7).

Heap recovery (F, W1 row 3): idle **before** load `largest_free_run` 10,080-15,232 B, free ~82 KB;
idle **after** 7,008-9,760 B, free ~80 KB. Free bytes fully recover; the largest run recovers to
~2/3. During load the largest run dipped as low as **464 B** (free 1,136 B, `load01`) — at N=4.

### 10.5 THE STATIC FILE SERVING DEFECT

**What the client sees:** `GET /` answered `HTTP/1.0 200 OK`, then a **truncated** gzip body, then
FIN. With the driver checking the body length against an idle reference (9,292 B compressed;
49,651 B decompressed), this was 10 of 72 requests at N=6 and 11 of 96 at N=8 on image G. No error
reaches the client.

**Mechanism, traced:**
1. `_serve_static()` (`src/asy_webserver_service.py:~628`) returns microdot's
   `send_file(..., compressed=True, file_extension=".gz")` — a `Response` wrapping an open file.
2. Microdot writes the status line and headers **first**, then iterates the body:
   `buf = response.body.read(response.send_file_buffer_size)` (`ext/microdot.py:746`), with
   `send_file_buffer_size = 1024` (`ext/microdot.py:567`). Each `read(1024)` allocates a **fresh
   1,025 B bytes object** (1024 + the terminating NUL MicroPython adds). A 9,292 B page is ten of
   them, per request, each needing one contiguous 1,025 B run.
3. When one fails, the `MemoryError` escapes microdot's body write — **the one real gap SPEC A.5
   already names** (microdot guards the handler, not the response write) — and lands in
   `_serve()`'s `except Exception` (`asy_webserver_service.py:697`), logged as
   `WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes`;
   the socket is closed.
4. The response is **HTTP/1.0 with `Connection: close` and no `Content-Length`** (checked with
   `curl -D -`: headers are only `Content-Type: text/html`, `Content-Encoding: gzip`,
   `Connection: close`). The end of the body is signalled only by FIN, so **a cut-off body is
   indistinguishable from a complete one at the HTTP layer.** A browser gets a 200 and a corrupt
   gzip stream.

**Why it is a delivery bug, not only a resource limit** (the owner's point): a resource failure
should end in an error response or no response — never a success status with wrong content. Two
independent defects combine:
- **(a) an unbounded-by-design allocation on the static path**: 1 KB contiguous per chunk, per
  request, four times the 256 B the JSON routes were just bounded to. The §0 fix did not touch it,
  and the per-route probe (§10.3) does not include the route, so the twin evidence could not see it.
- **(b) a failure after the 200 is invisible**: no `Content-Length`. The frozen VFS knows each
  file's size (`os.stat`), so the length could be sent; a truncated body would then be a
  client-visible `IncompleteRead`, not silent corruption.

**Fix candidates (not applied — owner's decision):** set `Response.send_file_buffer_size` to 256
from our code (a class attribute; no edit to vendored `ext/microdot.py`), or wrap the file in a
`readinto()`-based iterator over one preallocated buffer (zero per-chunk allocation); and send
`Content-Length` for static files. Then add `/` to `allocation_need_per_source.py`'s probes and a
body-length check to the sweep test.

*Annotation, 2026-09-23 evening (the twin session): applied — the first candidate plus
`Content-Length`, and both instrument additions. Microdot's own per-response
`send_file_buffer_size`, no vendored edit. `REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md` §00 is
the re-run; MEASUREMENTS §7Q.14 the twin evidence.*

**Earlier data this touches:** the morning's §4 driver only checked `len(body) > 0` for `/`, so a
truncated static page there would also have passed as served. At N ≤ 4 that run had 0 allocation
lines on the device, so the "4" stands; the failures at N ≥ 5 may have included 1025s in addition
to the ~870 B JSON pieces.

### 10.6 Maximum stable concurrency at `gc.threshold(-1)`, combined load, measured per level

Same definition as §4 (real task graph, every sensor/UART/NTP task running, 12 rounds of N
concurrent GETs across `/status`, `/sensors`, `/`, `/measurements`, `/networking`, `/system`), one
**fresh boot per level**, now with the static page's **body length** checked and every host error's
reason recorded. "Stable" = every request 200 with a complete body **and zero allocation-failure
lines on the device**.

**Image G (ceiling 16):**

| N | served (complete) | device allocation-failure lines | notes |
| --- | --- | --- | --- |
| 2 | 24/24 | 0 | worst largest free run 640 B |
| 4 | 47/48, then **48/48** | **0, 0** | the one miss: a host-side `URLError` on `/sensors`, no device-side line |
| 6 | 62/72 | 10 | all 10 are `/` truncated (1025 B) |
| 8 | 85/96 | 11 | all 11 are `/` truncated (1025 B) |
| 10 | 95/120 | 36 | 12 `/` truncated, 12 × `/status` 500 (251-256 B pieces), 1 host timeout |
| 12 | 99/144 | 66 | 24 `/` truncated, 20 × `/status` 500, 1 × `/measurements` 500; worst run 128 B |

(A first N=10 attempt was void: the driver's own reference fetch was reset and its thread died; fixed
and re-run.)

**Image G result: max stable = 4, first failure at 6.** The first failure at 6 is the static
page. Route (JSON) failures appear only from 10 upward, so **the JSON fix did move the JSON wall
from 5 (image A, 190,036 B heap) to ~10** — on a heap 20,916 B smaller — the static path is what now binds.

**Image F (ceiling 8) — the tip as it ships.** Every level after N=6's first pass was repeated
because a single clean run did not hold up:

| N | runs | served (complete) per run | device allocation-failure lines | notes |
| --- | --- | --- | --- | --- |
| 2 | 1 | 24/24 | 0 | |
| 3 | 1 | 36/36 | 0 | |
| **4** | 2 | 48/48, 47/48 | **0, 0** | the one miss: `/status` `TimeoutError` after 30 s, **no line at all on the device** (no allocation failure, no reclaim warning) |
| 5 | 3 | 60/60, 60/60, **59/60** | 0, 0, **1** | the failure: `/` truncated, 1,025 B |
| 6 | 2 | 72/72, **71/72** | 0, **1** | `/` truncated, 1,025 B |
| 7 | 2 | 80/84, 82/84 | 4, 2 | all `/` truncated, 1,025 B |
| 8 | 1 | 90/96 | 6 | all `/` truncated, 1,025 B; worst largest free run 80 B |

**Every failure on F, at every level, is the static page.** Not one JSON route failed on F at any
level up to its ceiling of 8 — the bounded writer holds on silicon. The static page fails
*probabilistically* from 5 upward (1 in 60-72 requests at 5-6, rising with N), which is why single
runs at 5 and 6 passed and repeats did not.

**Verified answer for the tip at `gc.threshold(-1)` under combined load: 4.** N=4 is the highest
level with zero allocation failures on every run (4 runs across G and F, 192 requests, 0 device
lines). It is not perfectly clean: in 2 of those 4 runs a single request stalled on the host
(`/sensors` `URLError` on G, `/status` 30 s timeout on F) with nothing logged on the device.
Every run shows the same one `WLAN is disconnected` / `reconnect triggered` pair, clean runs
included, so that pair is the boot-time reconnect after `mpremote` interrupts `main.py`, not the
cause. **Cause of the stalls: not established.** 5 fails 1 run in 3, 6 fails 1 in 2, 7 and 8 fail every time.

What this does and does not say: the JSON routes are no longer what limits concurrency (none
failed up to 8 on F, and on G none until 10). The static page's 1,025 B chunk reads are what limits
it now, and they turn a memory failure into a silent truncated 200 (§10.5). With that path bounded
like the JSON ones, the board has to be measured again: the JSON evidence suggests at least 8, but
nothing on the static path has been measured yet.

### 10.7 Instrument gaps found in this sitting

- `test_serving_sweep_at_the_reactive_default` counts a response as served from its **status line
  alone**; a truncated body is a 200 there. It still failed correctly, only because the
  allocation-marker gate caught the log lines. It should check the body against a reference length.
- `allocation_need_per_source.py` probes every JSON route and data source but **no static route**.
- The morning's combined-load driver (`stability_sweep.py`, scratch) had the same `len > 0` gap for
  `/`; the version used in §10.6 checks the length and records each error's reason.

### 10.8 What was NOT done (deliberately)

W3 (`test_end_to_end_timing.py`) and W4 (the full bench tier on F) are **not run**: the handover says
"if W2 fails below 10 on silicon … record it and stop", and both would have to be re-run on a fixed
image anyway.

### 10.9 The per-boot sweep tool, and its raw output

The driver behind §10.6 is now `tests_hardware/combined_load_sweep.py` (it was a scratch script
during the sitting). Usage: `DUT_IP=<ip> uv run python tests_hardware/combined_load_sweep.py 2 4 5 5 6 6 8
--raw-dir <dir>`. That is one fresh boot per listed level, a repeated level means a repeated run, and the
exit code is 0 only if every level is STABLE. It
runs `device_scripts/serving_stability_under_combined_load.py` with `gc.threshold` substituted
(`--threshold`, default -1). **One deliberate difference from §10.6:** its load mix adds
`/js/app.js` (every page load fetches it, and the handover's sweep now loads it too), and it checks
that script's body length as well. So a result from it is the §10.6 measurement plus one more static
file, not a like-for-like repeat of it.

Raw result lines of the sitting, verbatim (`MemoryError lines` counts every device line matching
`MEMORY_ERROR_MARKERS`; `BAD200` on `/` is a body shorter than the idle reference of 9,292 B):

```
# image G, levels 2 4 6 8 10 12 (N=10 void: driver thread died)
                  ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
         ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
           ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
                              '_open', req)
           ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                              ~~~~~~~~~~~~~~~~~^^
               ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
           ~~~~~~~~~~~~~~~~~~~~^^^
N= 2 GC_THRESHOLD=-1 | served 24/24 over 12 rounds | worst placeable2K=0 worst_largest_run=640 | MemoryError lines=0 | {}
N= 4 GC_THRESHOLD=-1 | served 47/48 over 12 rounds | worst placeable2K=0 worst_largest_run=336 | MemoryError lines=0 | {'/sensors URLError': 1, 'rounds': {8}}
N= 6 GC_THRESHOLD=-1 | served 62/72 over 12 rounds | worst placeable2K=0 worst_largest_run=320 | MemoryError lines=10 | {'/ BAD200': 10, 'rounds': {1, 3, 4, 5, 6, 7, 8, 9, 10, 11}}
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
N= 8 GC_THRESHOLD=-1 | served 85/96 over 12 rounds | worst placeable2K=0 worst_largest_run=432 | MemoryError lines=11 | {'/ BAD200': 11, 'rounds': {0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11}}
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
N=10 GC_THRESHOLD=-1 | served 0/0 over 12 rounds | worst placeable2K=0 worst_largest_run=624 | MemoryError lines=0 | {}
N=12 GC_THRESHOLD=-1 | served 99/144 over 12 rounds | worst placeable2K=0 worst_largest_run=128 | MemoryError lines=66 | {'/ BAD200': 24, 'rounds': {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}, '/status BAD500': 20, '/measurements BAD500': 1}
      MemoryError: memory allocation failed, allocating 252 bytes
      WEBSERVER Unhandled exception in route handler: memory allocation failed, allocating 252 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      MemoryError: memory allocation failed, allocating 253 bytes
      MemoryError: memory allocation failed, allocating 256 bytes
      site: File "asy_webserver_service.py", line 55, in add_value
      site: File "asy_webserver_service.py", line 56, in add_value
      site: File "asy_webserver_service.py", line 61, in add_value
      site: File "asy_webserver_service.py", line 62, in add_value
      site: File "asy_webserver_service.py", line 65, in add_value
      site: File "asy_webserver_service.py", line 73, in _stream_dict_response
      site: File "microdot.py", line 1464, in dispatch_request
      site: File "microdot.py", line 45, in invoke_handler

# image G, repeat 4 and 10
N= 4 GC_THRESHOLD=-1 | served 48/48 over 12 rounds | worst placeable2K=0 worst_largest_run=240 | MemoryError lines=0 | {}
N=10 GC_THRESHOLD=-1 | served 95/120 over 12 rounds | worst placeable2K=0 worst_largest_run=128 | MemoryError lines=36 | {'/ BAD200': 12, 'rounds': {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}, '/status BAD500': 12, "/sensors URLError:TimeoutError('timed out')": 1}
      MemoryError: memory allocation failed, allocating 256 bytes
      WEBSERVER Unhandled exception in route handler: memory allocation failed, allocating 256 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      MemoryError: memory allocation failed, allocating 251 bytes
      WEBSERVER Unhandled exception in route handler: memory allocation failed, allocating 251 bytes
      site: File "asy_webserver_service.py", line 42, in add
      site: File "asy_webserver_service.py", line 46, in flush
      site: File "asy_webserver_service.py", line 54, in add_value
      site: File "asy_webserver_service.py", line 55, in add_value
      site: File "asy_webserver_service.py", line 62, in add_value
      site: File "asy_webserver_service.py", line 65, in add_value
      site: File "microdot.py", line 1464, in dispatch_request
      site: File "microdot.py", line 45, in invoke_handler

# image F, levels 2 3 4 5 6 8
N= 2 GC_THRESHOLD=-1 | served 24/24 over 12 rounds | worst placeable2K=0 worst_largest_run=384 | MemoryError lines=0 | {}
N= 3 GC_THRESHOLD=-1 | served 36/36 over 12 rounds | worst placeable2K=0 worst_largest_run=1632 | MemoryError lines=0 | {}
N= 4 GC_THRESHOLD=-1 | served 48/48 over 12 rounds | worst placeable2K=0 worst_largest_run=752 | MemoryError lines=0 | {}
N= 5 GC_THRESHOLD=-1 | served 60/60 over 12 rounds | worst placeable2K=0 worst_largest_run=560 | MemoryError lines=0 | {}
N= 6 GC_THRESHOLD=-1 | served 72/72 over 12 rounds | worst placeable2K=0 worst_largest_run=640 | MemoryError lines=0 | {}
N= 8 GC_THRESHOLD=-1 | served 90/96 over 12 rounds | worst placeable2K=0 worst_largest_run=80 | MemoryError lines=6 | {'/ BAD200': 6, 'rounds': {0, 2, 3, 5, 7, 10}}
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes

# image F, repeat 6, then 7 twice
N= 6 GC_THRESHOLD=-1 | served 71/72 over 12 rounds | worst placeable2K=0 worst_largest_run=1296 | MemoryError lines=1 | {'/ BAD200': 1, 'rounds': {5}}
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
N= 7 GC_THRESHOLD=-1 | served 80/84 over 12 rounds | worst placeable2K=0 worst_largest_run=336 | MemoryError lines=4 | {'/ BAD200': 4, 'rounds': {10, 2, 3, 5}}
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
N= 7 GC_THRESHOLD=-1 | served 82/84 over 12 rounds | worst placeable2K=0 worst_largest_run=608 | MemoryError lines=2 | {'/ BAD200': 2, 'rounds': {2, 5}}
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes

# image F, 5 twice, then 4
N= 5 GC_THRESHOLD=-1 | served 60/60 over 12 rounds | worst placeable2K=0 worst_largest_run=784 | MemoryError lines=0 | {}
N= 5 GC_THRESHOLD=-1 | served 59/60 over 12 rounds | worst placeable2K=0 worst_largest_run=624 | MemoryError lines=1 | {'/ BAD200': 1, 'rounds': {6}}
      WEBSERVER Unexpected error serving connection: memory allocation failed, allocating 1025 bytes
N= 4 GC_THRESHOLD=-1 | served 47/48 over 12 rounds | worst placeable2K=0 worst_largest_run=640 | MemoryError lines=0 | {"/status URLError:TimeoutError('timed out')": 1, 'rounds': {4}}
```

