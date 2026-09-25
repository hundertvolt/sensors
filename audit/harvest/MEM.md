# Harvest — MEM: Memory safety

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 23, INVAR 32, MIRROR 2, LIMIT 20, RISK 9, ASSUME 39, PLATFORM 1, SUPPRESS 18, TODO 4, OPENQ 8, DRIFT 1, NOTE 18 — 175 items.


## src/asy_fram_driver.py

- **MEM.N001** DRIFT · `src/asy_fram_driver.py:53-55` — "lands in the 32-96 byte size class the
  heap-layout model cares about (HEAP_FRAGMENTATION_MEASUREMENTS.md section M1)" — M1
  (HEAP_FRAGMENTATION_MEASUREMENTS.md:22-26) states the allocator has "no size classes" and names no
  32-96 B class (low). · related: DOC.T02 · [H01]

## src/asy_fram_manager.py

- **MEM.N002** ASSUME · `src/asy_fram_manager.py:443, 528` — "del data # free memory after using
  preallocated buffer" — `del` of a parameter frees nothing while the caller holds a reference (and
  nothing before the next sweep, HEAP_FRAGMENTATION_MEASUREMENTS.md:30) (low). · [H01]
- **MEM.N003** LIMIT · `src/asy_fram_manager.py:434, 453, 520, 572` — "buf = self.get_buffer() #
  preallocate buffer for payload and crc length" — "preallocate" is a fresh `AsyFramChunkBuffer` (with
  its unused lock) per write/read call. · covered-by: CORE.S07 · [H01]

## src/asy_uart_comm.py

- **MEM.N004** INVAR · `src/asy_uart_comm.py:274-276` — "Nothing is allocated per frame after this -
  zero bytes retained per transaction, pinned by test_uart_comm_hazard.py." — Zero-allocation steady
  state; enforced by `tests/test_uart_comm_hazard.py` · related: UART.T03 · [H02]
- **MEM.N005** SUPPRESS · `src/asy_uart_comm.py:290-291` — "except (MemoryError, OverflowError): return
  tx, rx, bytearray(0), ..." — MemoryError swallowed into zero-length scratch buffers; detected later by
  `_buffers_ready()` → errno 14 (degraded construction) · [H02]
- **MEM.N006** SUPPRESS · `src/asy_uart_comm.py:873-875` — "except (MemoryError, OverflowError): await
  self._err(_ERR_DEST_ALLOC, \"could not right-size the answer\")" — Caught MemoryError degrades to a
  failed GET (errno 24) · [H02]
- **MEM.N007** RISK · `src/asy_uart_comm.py:937-941` — "try: # allocated before the first data chunk is
  acknowledged ... own_dest = bytearray(room)" — Peer-declared CHUNKS sizes an allocation up to
  254·payload_size; MemoryError caught → errno 24 (BACKLOG accepted-with-caveat) · covered-by: UART.T03
  · [H02]
- **MEM.N008** RISK · `src/asy_uart_comm.py:1055, 1062-1066` — "try: # allocated before any data chunk
  is acknowledged ... dest = bytearray(room)" — Responder allocates from peer-declared CHUNKS;
  MemoryError caught → errno 24 · covered-by: UART.T03 · [H02]

## src/asy_uart_driver.py

- **MEM.N009** SUPPRESS · `src/asy_uart_driver.py:318-319, 337-338` — "except (MemoryError,
  OverflowError): return None" / "except MemoryError: return None" — Caught MemoryError in
  `read_until_complete` (no production caller); `msg += add` grows per round · related: BUS.T08 · [H02]
- **MEM.N010** SUPPRESS · `src/asy_uart_driver.py:344` — "except MemoryError: # check()'s own
  bytearr[0:n] slice allocates a fresh copy" — Caught MemoryError from CRC check copy · related:
  ALGO.S04 · [H02]
- **MEM.N011** SUPPRESS · `src/asy_uart_driver.py:415` — "except MemoryError: # unbounded across rounds,
  unlike read_until_complete()'s nbytes cap" — Unbounded line accumulation, MemoryError caught ·
  covered-by: BUS.S06 · [H02]
- **MEM.N012** SUPPRESS · `src/asy_uart_driver.py:432` — "except MemoryError: # add()'s own bytearr +
  crc_b allocates a fresh copy" — Caught MemoryError on the allocating write path (per-call copy) ·
  related: MEM.T04 · [H02] ⟨quote not matched at the anchor⟩

## src/asy_uart_link_driver.py

- **MEM.N013** RISK · `src/asy_uart_link_driver.py:96-99` — "None means \"don't care\", which is what a
  bench echo wants." — Echo SET accepts any peer-declared size, so the responder allocates up to
  254·payload_size per train · related: UART.T03 · [H02]

## src/asy_udp_socket.py

- **MEM.N014** SUPPRESS · `src/asy_udp_socket.py:178-179` — "except (OSError, MemoryError, TypeError): #
  TypeError: a malformed buf (e.g. a str) / pass" — Receive failure (incl. MemoryError of the
  `buf`-sized allocation) swallowed · related: NET.S10 · [H02]

## src/asy_webserver_service.py

- **MEM.N015** PLATFORM · `src/asy_webserver_service.py:107` — "_PieceWriter's list never outgrows 16
  slots (64 B on the RP2040)" — Pointer-size/list-cost fact for the target · related: REST.T05 · [H02]
- **MEM.N016** ASSUME · `src/asy_webserver_service.py:108-110` — "sized to the holes a fragmented heap
  still has at gc.threshold(-1)... ~870 B pieces fail with ~100 KB free (SPECIFICATION.md Part I.3)" —
  256 B chunk size rests on a single measured fragmentation figure · related: REST.T05 · [H02]

## src/base_classes.py

- **MEM.N017** RISK · `src/base_classes.py:66-68` — "A valid size can still exhaust heap (real FRAM
  chunk buffers allocate fresh on every read/write over an indefinite uptime)" — Acknowledged
  per-operation buffer churn (vs G.2 long-lived buffer rule) · covered-by: CORE.S07 · [H02]
- **MEM.N018** SUPPRESS · `src/base_classes.py:71-72` — "except (MemoryError, OverflowError): self.buf =
  None" — Caught MemoryError degrades to `buf=None`; every user must check `get_buf()` · related:
  CORE.T08 · [H02]

## src/captive_dns.py

- **MEM.N019** RISK · `src/captive_dns.py:98` — "data, addr = await self.udps.recvfrom(4096)" — 4 KB
  allocation per datagram vs I.3's 256 B bound · covered-by: NET.S10 · [H02]
- **MEM.N020** RISK · `src/captive_dns.py:109, 111, 121` — "self.pr.evt(f\"Incoming DNS request from
  {addr[0]:s}:{addr[1]}...\")" — f-strings built per query regardless of debug level · covered-by:
  NET.S12 · [H02]

## src/config_manager.py

- **MEM.N021** SUPPRESS · `src/config_manager.py:356-360` — "except (MemoryError, AttributeError) as e:
  # a non-dict `data` param... or dict()/the validation loop exhausting the heap" — Caught MemoryError →
  errno 15, whole write Failed · [H02]

## src/framing_codecs.py

- **MEM.N022** INVAR · `src/framing_codecs.py:29, 80` — "self.allocations = 0 # long-lived scratch
  allocations; 1 at most, never per frame" — Allocation contract exposed as a counter for tests ·
  related: ALGO.T04 · [H02]
- **MEM.N023** SUPPRESS · `src/framing_codecs.py:86-87` — "except (MemoryError, OverflowError):
  self._scratch = None" — Caught MemoryError → codec not ready; UART_Comm turns that into errno 14
  (`asy_uart_comm.py:235-238`) · [H02]

## src/print_log.py

- **MEM.N024** SUPPRESS · `src/print_log.py:140-144` — "try: # still reachable well below the overflow
  boundary on a genuinely memory-constrained device ... except MemoryError: history_length = 0" — Caught
  MemoryError → zero-length history (silent) · [H02]
- **MEM.N025** RISK · `src/print_log.py:249` — "buf = self.fram.get_buffer()" — Fresh chunk buffer (with
  unused lock) allocated per persisted entry · covered-by: CORE.S07 · [H02]

## src/system_service.py

- **MEM.N026** SETTLED · `src/system_service.py:219-226` — "Measure B (SPECIFICATION.md Part I.4(f.1)):
  ... each collect puts the allocator's free-scan index back to zero. Not hygiene, not compaction, and
  never in the supervisor below." — Owner-approved boot-confined `gc.collect()`; site-confined by
  `scripts/lint.sh` + `tests_scripts/test_gc_collect_sites.py` · related: MEM.T02 · [H02]

## ext/freezefs/ffsmount.py

- **MEM.N027** LIMIT · `ext/freezefs/ffsmount.py:93-102` — "Compressed file - late import of deflate
  library ... This requires to buffer the entire file... Only useful if enough RAM is available." —
  Compressed text-mode open buffers whole files (project avoids `--compress`) · [H02]

## tests/_threshold_runner.py

- **MEM.N028** SETTLED · `tests/_threshold_runner.py:5-7` — "the whole suite must pass at
  gc.threshold(-1) ... and it must ALSO still pass with the shipped gc.threshold(32768)" — the two-stage
  memory rule this runner makes runnable (`GC_THRESHOLD`) · related: TEST.T18 · [H03]

## tests/_webserver_concurrency_scenarios.py

- **MEM.N029** NOTE(MEM) · `tests/_webserver_concurrency_scenarios.py:792-794` — "the simultaneous
  contiguous demand is max_connections x max_content_length (Part I.6) - the single most likely source
  of a new MemoryError when the ceiling goes up" — stated memory-budget coupling between two settings ·
  related: REST.S01 (I.6 stale 4×2048) · [H03]

## tests/test_asy_fram_allocation_budget.py

- **MEM.N030** ASSUME · `tests/test_asy_fram_allocation_budget.py:32-37` — "Measured 2026-09-18, mock
  tier, median of five, ~15% margin." — absolute byte budgets (34,000/24,000 settrace-free;
  344,000/270,000 settrace) from one dated measurement, binary-dependent, "NOT board figures" · related:
  TEST.S12, TEST.T03 · [H03]

## tests/test_asy_webserver_service.py

- **MEM.N031** INVAR · `tests/test_asy_webserver_service.py:1465-1467` — "bounded by connections x cap;
  with the band open it would be connections x 16 KB" — worst-case simultaneous body demand =
  max_connections × 2,048 B · related: REST.S11 · [H04]
- **MEM.N032** ASSUME · `tests/test_asy_webserver_service.py:2474-2476,2589-2590,2599,2735` — "17
  registered modules joined into one \"errcount\" piece reached ~4.9KB" / "produced 237 real
  MemoryErrors on real hardware before the streaming fix and 0 after" — dated real-hardware measurements
  (17 modules, 4.9 KB, 237 → 0) underpin the hammer tests' scale · [H04]
- **MEM.N033** ASSUME · `tests/test_asy_webserver_service.py:2541-2542` — "a whole 10-element entry is
  ~290 B, above the holes a loaded heap keeps at gc.threshold(-1)" — fragmentation figure from
  HEAP_FRAGMENTATION_MEASUREMENTS archive §7R.3 · - (low) · [H04]

## tests/test_framing_codecs.py

- **MEM.N034** INVAR · `tests/test_framing_codecs.py:188` — "allocated once from the frame bound, never
  per frame" — COBS scratch must be allocated once (asserted via the `allocations` counter) · [H05]

## tests/test_system_service.py

- **MEM.N035** INVAR · `tests/test_system_service.py:1008-1010` — "The supervisor underneath is the run
  phase, where I.4 forbids one - so the count must not move once spinning" — Boot-confined gc.collect()
  (I.4(f.1)) enforced by counting collects via a fake `gc` module · [H05]

## tests/test_uart_comm_hazard.py

- **MEM.N036** ASSUME · `tests/test_uart_comm_hazard.py:533-535, 1029-1034, 1055-1057, 1073-1078` — "0 B
  locally, 64 B and 288 B on two runners" / "~3.4kB ... Measured constant at 10, 30, 60 and 120
  failures" / "~114 B/failure" — Heap-rate bounds (< one frame, < 6 B/tx, < 16 B/failure) rest on dated
  host measurements · related: TEST.S12 · [H05]
- **MEM.N037** INVAR · `tests/test_uart_comm_hazard.py:1244-1246` — "gc.threshold() is global, so each
  body restores it" — The hammer checks run at both -1 and 32768 inside one process, so the (e) stage's
  -1 run also executes a 32768 phase here · related: TEST.T18 · [H05]

## digital_twin/README.md

- **MEM.N038** ASSUME · `digital_twin/README.md:321-328` — "16385 bytes for a real 0x2000-byte FRAM ...
  even with ~1.5MB of *total* `gc.mem_free()` still available" — Dated measurement justifying chunked
  (512 B) save/load · [H06]
- **MEM.N039** ASSUME · `digital_twin/README.md:564-567` — "A CI `MemoryError` here (`allocating ~6100 bytes`
  on `GET /status`) ... fixed by `_http_client.py`'s `_read_exact()`/`_read_until_close()`" — Past
  MemoryError attributed to the test client's reads; fixed in the oracle · related: TEST.T17 · [H06]
- **MEM.N040** SUPPRESS · `digital_twin/README.md:592-602` — "Its `gc.collect()` is measurement
  instrumentation under Part I.4(e)'s narrow exception" — A `gc.collect()` in twin code justified as
  instrumentation; min=99808/max=1347104 measured 2026-09-14 without it · related: TEST.T03 · [H06]
- **MEM.N041** ASSUME · `digital_twin/README.md:732-739` — "(~7.5KB for the largest device's frozen
  website) ... **no real device ever holds one**" — Twin-client allocation vs device behaviour;
  `py/gc.c`'s collect-and-retry cited as platform fact · [H06]
- **MEM.N042** ASSUME · `digital_twin/README.md:741-745` — "`dev`'s own frozen website (7579 bytes,
  168-483 bytes larger than the other five devices')" — Dated sizes that drift with the website · [H06]

## digital_twin/unix_port_gc_unwedge.py

- **MEM.N043** ASSUME · `digital_twin/unix_port_gc_unwedge.py:13-15` — "a collection at shutdown costs
  nothing and allocates nothing" — Justifies an unconditional `gc.collect()` outside the CLAUDE.md
  boot-confined sites (twin scope) · related: TEST.T03 · [H06]

## digital_twin/run_generic_integration.py

- **MEM.N044** SUPPRESS · `digital_twin/run_generic_integration.py:288-295` — "and an
  instrumentation-only gc.collect()" — `gc.collect()` in the twin sampler under the I.4(e) narrow
  exception · related: TEST.T03 · [H06]

## digital_twin/segfault_stress_repro.py

- **MEM.N045** SUPPRESS · `digital_twin/segfault_stress_repro.py:4-6, :54-55` — "a MemoryError at higher
  concurrency is a distinct outcome this also reports" — `MemoryError` caught and counted as a result
  rather than a failure · [H06]
- **MEM.N046** SUPPRESS · `digital_twin/segfault_stress_repro.py:92` — "`gc.collect()`" — Manual collect
  before the hammer rounds (twin tool) · related: TEST.T03 · [H06]

## tests/test_digital_twin_fram.py

- **MEM.N047** LIMIT · `tests/test_digital_twin_fram.py:193-195` — "This test is not about
  fragmentation, which no unit test reproduces deterministically" — The MemoryError the chunking fixed
  has no deterministic regression test · [H06]

## tests/test_digital_twin_sensortask_integration.py

- **MEM.N048** SUPPRESS · `tests/test_digital_twin_sensortask_integration.py:543-546, 627, 705, 779` —
  "a known failure mode on this file's shared heap otherwise, where orphaned task references starved a
  later build_system() with a real MemoryError before this collect() was added" — `gc.collect()` added
  to prevent a MemoryError in tests · covered-by: TEST.S11 · [H06]

## tests/test_digital_twin_uart_link.py

- **MEM.N049** SUPPRESS · `tests/test_digital_twin_uart_link.py:296, 361, 370, 401, 452, 461` —
  "`gc.collect()`" — Six manual collects in tests (forced-GC scenario, leak measurements, churn
  recovery) · related: TEST.T03, TEST.S11 · [H06]
- **MEM.N050** LIMIT · `tests/test_digital_twin_uart_link.py:377-379, 475` — "The bound is generous -
  this asserts \"no per-transfer leak\", not an allocation budget" / "`assert leaked < 8192`" — Absolute
  heap-delta bound · covered-by: TEST.S12 · [H06]
- **MEM.N051** SUPPRESS · `tests/test_digital_twin_uart_link.py:399` — "`except MemoryError: # the pressure this test exists to create`"
  — Deliberately induced and swallowed MemoryError inside the unit tier, next to the MemoryError log
  gate · related: TEST.T18 · [H06]
- **MEM.N052** SETTLED · `tests/test_digital_twin_uart_link.py:426-428` — "Run under MicroPython's own
  default (no proactive collection) as well as the project's 32768" — Both GC stages exercised in-test ·
  [H06]

## tests_hardware/flash/test_memory_stress.py

- **MEM.N053** SETTLED · `tests_hardware/flash/test_memory_stress.py:58-60` — "What the owner asked
  these tests to express (2026-09-19): long-lived objects must not colonise the top of the heap" —
  Owner-set placement requirement. · related: MEM.T02 · [H07]

## tests_hardware/device_scripts/heap_headroom_after_full_system_build.py

- **MEM.N054** SETTLED · `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:24-35`
  — "Not re-derived on purpose ... the retired 80,000 B floor was 30% - a third of physical memory,
  which is what the owner retired it for on 2026-09-19. Nothing here may be raised to fit a reading" —
  `_MIN_LARGEST_BLOCK = 32768` is a requirement, not a fitted floor. · related: MEM.T06 · [H07]

## tests_hardware/README.md

- **MEM.N055** INVAR · `tests_hardware/README.md:292-295` — "A reset before any response at the ceiling
  is a refusal and expected (`http_client.is_ceiling_close()`, owner's rule)" — Stability verdict = zero
  true failures and zero `MEMORY_ERROR_MARKERS` lines (caught ones included). · related: HW.T05 · [H08]
- **MEM.N056** ASSUME · `tests_hardware/README.md:296-303` — "Rounds of N parallel requests with pauses
  are typical load and overstate free heap" — Peak-load method; also "every device-script boot drops and
  rejoins WLAN at ~6 s uptime". · [H08]
- **MEM.N057** INVAR · `tests_hardware/README.md:306-309` — "An instrument that changes the system may
  measure but not judge" — A `gc.collect()`-per-sample run's stability verdict is not evidence; verdict
  from the least-instrumented run. · [H08]
- **MEM.N058** ASSUME · `tests_hardware/README.md:311-315` — "a device script's own code and globals
  cost heap production's frozen `main.py` does not pay (2,720 B" — Single measured instrument price;
  samplers ~10-20% throughput; GC tables ~4.3-4.5 KB. · [H08]
- **MEM.N059** LIMIT · `tests_hardware/README.md:321-322` — "a minimum from a 5 s snapshot bounds the
  true peak from one side only" — Sampled minima understate the true peak. · [H08]
- **MEM.N060** ASSUME · `tests_hardware/README.md:326-328` — "Device allocation lines come in pairs per
  failure ... so lines ÷ 2 = host 500s" — Counting convention assumes exactly two log lines per
  allocation failure. · - (low) · [H08]
- **MEM.N061** ASSUME · `tests_hardware/README.md:485-490` — "the heap probe read 95,104 B and passed;
  deep in a suite the *same* firmware read 28,864 B" — Any heap figure must state suite position. ·
  related: HW.T16 · [H08]
- **MEM.N062** INVAR · `tests_hardware/README.md:655-666` — "add it to the staged `main.py` a build
  produces, before flashing, and never commit the edit" — Reusable GC-instrumentation technique;
  `exec()` against a live system forbidden. · [H08]

## REAL_HARDWARE_TEST_QUEUE.md (snapshot only; being updated by another session)

- **MEM.N063** OPENQ · `REAL_HARDWARE_TEST_QUEUE.md:227` — "**MEASURED 2026-09-25**, owner to close:
  in-suite `after_build_system` `largest_block` **84,112 B**" — T1: archive comparison figures "no
  longer in the tree and look like a different position" — owner to close or name the position. ·
  related: HW.T16 · [H08]
- **MEM.N064** ASSUME · `REAL_HARDWARE_TEST_QUEUE.md:227` — "`-1` at 0.8 s after reset, `32768` at 38 s"
  — §M3.8 gc.threshold race confirmed on silicon; pre-2026-09-24 heap corpus threshold "unrecoverable
  per run". · [H08]
- **MEM.N065** TODO · `REAL_HARDWARE_TEST_QUEUE.md:276` — "So the (e) bar itself, zero allocation
  failures under real load, has no silicon arm." — G8 OPEN (script to write): every flash/bench run is
  an (f)-stage run at 32768. · [H08]
- **MEM.N066** LIMIT · `REAL_HARDWARE_TEST_QUEUE.md:342-345` — "A `largest_block` figure that is exactly
  192 KB / 2, / 4, / 8 … is the probe, not the heap." — Probe artefact values; `retained=` equals
  `largest_block` then. · [H08]
- **MEM.N067** LIMIT · `REAL_HARDWARE_TEST_QUEUE.md:346-348` — "\"After the starter list\" and \"after
  boot\" are not the same position, and the gap is seconds." — Measure B must be judged at
  `after_starter_loop_end`. · [H08]

## dev_legacy/README.md

- **MEM.N068** ASSUME · `dev_legacy/README.md:145-150` — "costs ~140-180 KB of heap to import raw/`.mpy`
  over a mount, against ~196 KB free ... drops that same closure's cost to ~33 KB" — Dated heap figures
  for mount vs frozen import. · - (low) · [H08]

## scripts/lint.sh

- **MEM.N069** INVAR · `scripts/lint.sh:36-49` — "`gc.collect()` is confined to the two one-time boot
  lists" — Grep is file-granular (any site in `src/system_service.py` or `buildgen/codegen.py` passes);
  structural check is `tests_scripts/test_gc_collect_sites.py`; tests/ and digital_twin/ are out of
  scope by I.4(e)/F.6. · related: SCR.T02 · [H09]

## scripts/_digital_twin_ci_suite.py

- **MEM.N070** RISK · `scripts/_digital_twin_ci_suite.py:127-133` — "one gc.collect()+print() per
  interval costs nothing measurable" — The soak's memory sampler runs `gc.collect()` inside the DUT
  every 25 ms, so the soak measures a heap collected far more often than either GC stage it claims to
  test. · related: TEST.T03 · [H09]
- **MEM.N071** SETTLED · `scripts/_digital_twin_ci_suite.py:159-162, 1304-1313` — "main() therefore runs
  run_suite() twice, once per value, never once with one hardcoded." — Whole suite runs at -1 then 32768
  (Part I.4(e)). · [H09]

## buildgen/codegen.py

- **MEM.N072** SETTLED · `buildgen/codegen.py:456-458, 466` — "Measure B (SPECIFICATION.md Part
  I.4(f.1)): one collect before the batch and one after each module, nowhere else." — The owner-approved
  boot-confined `gc.collect()` exception; enforced by lint.sh:46-49, `test_gc_collect_sites.py`,
  `test_digital_twin_boot_contiguity.py`. · [H09]

## tests_scripts/test_buildgen_generate.py

- **MEM.N073** INVAR · `tests_scripts/test_buildgen_generate.py:69-97` — "The \"nowhere else\" half is
  the load-bearing one - this is a boot-only exception to I.4" — Pins the boot-confined `gc.collect()`
  exception: one collect before the first setup and one after each, total = setups+1, none in `main()`
  (Measure B, I.4(f.1)); "PLAN B.1.1" is a reference to a retired plan · related: TEST.T03 · [H10]

## tests_scripts/test_device_script_gc_threshold.py

- **MEM.N074** ASSUME · `tests_scripts/test_device_script_gc_threshold.py:62-63` — "the reason the
  pre-2026-09-24 flash-tier readings' threshold is unknown (MEASUREMENTS M3.8)" — Every flash-tier heap
  figure measured before 2026-09-24 has an unknown GC threshold · related: HW.T16 · [H10]

## tests_scripts/test_digital_twin_boot_contiguity.py

- **MEM.N075** INVAR · `tests_scripts/test_digital_twin_boot_contiguity.py:1-3` — "The regression guard
  for SPECIFICATION.md Part I.4(f.1)'s boot-confined placement reset" — The effect-side guard of the
  only sanctioned `gc.collect()` exception (site-side: test_gc_collect_sites.py, lint.sh) · related:
  TEST.T03 · [H10]
- **MEM.N076** ASSUME · `tests_scripts/test_digital_twin_boot_contiguity.py:46-80` — "worst live 452,832
  (1.47x); best suppressed 218,528 (1.41x under)" — All bounds are single-campaign twin measurements
  times a thin margin ("the ARMS are only 2.07x apart here"); ratios 2.36x/4.64x and 12.96x/13.93x;
  retention drift 0.05% vs 1% tolerance (MEASUREMENTS archive §7L.7/§7L.3/7A.1) · related: HW.T16 ·
  [H10]
- **MEM.N077** ASSUME · `tests_scripts/test_digital_twin_boot_contiguity.py:28-30` — "those proved
  heap-size independent at 8M and 16M" — Heap-size independence measured at two sizes only · [H10]
- **MEM.N078** LIMIT · `tests_scripts/test_digital_twin_boot_contiguity.py:59-61` — "The batch's own
  reach and band count no longer separate the arms (8,160 B and 0 in BOTH)" — Since the settrace-free
  re-derivation, two of the bounds are tripwires only, not proof the collects work · [H10]
- **MEM.N079** LIMIT · `tests_scripts/test_digital_twin_boot_contiguity.py:39-42,203-205` — "Running it
  for all six would double the subprocess count" / "so this UNDERSTATES" — Control (suppressed) arm runs
  on wozi/dev only and still keeps the anchor collect · [H10]
- **MEM.N080** ASSUME · `tests_scripts/test_digital_twin_boot_contiguity.py:189-191` — "the run phase
  undoes most of the gain within ~2 s and the position stops discriminating (MEASUREMENTS M3.9)" —
  Placement benefit is transient at the reactive default; measurement taken at the starter loop's end
  only · related: MEM.T02 · [H10]
- **MEM.N081** LIMIT · `tests_scripts/test_digital_twin_boot_contiguity.py:127-140` — "assert
  completed.returncode == 0" / "assert \"RESULT: PASS\" in completed.stdout" — Probe stdout is not
  scanned for `MemoryError`/`memory allocation failed` (not one of the four gates) · covered-by:
  TEST.T18 · [H10]

## tests_scripts/test_digital_twin_ci_suite_errcount.py

- **MEM.N082** INVAR · `tests_scripts/test_digital_twin_ci_suite_errcount.py:336-377` — "matching
  \"MemoryError\" alone only ever caught an uncaught traceback" — Pins the twin gate's `memory allocation failed`
  half; a missing log is deliberately not a MemoryError failure · related: TEST.T18 · [H10]

## tests_scripts/test_digital_twin_ci_suite_soak.py

- **MEM.N083** LIMIT · `tests_scripts/test_digital_twin_ci_suite_soak.py:94-96,81-83` — "the SAME
  200-byte decline gets a tighter tolerance from a quiet quarter than a noisy one" — Leak tolerance is
  derived from each run's own within-quarter spread (no fixed floor); a slow leak smaller than the run's
  noise passes by design; needs >= 4 samples · related: HW.S14 · [H10]
- **MEM.N084** ASSUME · `tests_scripts/test_digital_twin_ci_suite_soak.py:8-10` — "the \"gc.mem_free()
  has no other source\" exception (Part I.4(e))" — Soak relies on a sanctioned `gc.mem_free()` sampler
  exception in the twin · [H10]

## tests_scripts/test_digital_twin_generated_boot.py

- **MEM.N085** LIMIT · `tests_scripts/test_digital_twin_generated_boot.py:163-190` — "output =
  proc.stdout.read() if proc.stdout else \"\"" — Twin output is read only on a nonzero exit; no
  `MemoryError`/`memory allocation failed` scan of a passing boot · covered-by: TEST.T18 · [H10]

## tests_scripts/test_gc_collect_sites.py

- **MEM.N086** INVAR · `tests_scripts/test_gc_collect_sites.py:8-12` — "_ALLOWED_SRC_SITES =
  {(\"system_service.py\", \"start_and_check_tasks\")}" — Pinned allowance for I.4(f.1): src/ only in
  `system_service.start_and_check_tasks`, buildgen/ only in `codegen.py` (textual); also grepped by
  scripts/lint.sh · related: TEST.T03 · [H10]
- **MEM.N087** LIMIT · `tests_scripts/test_gc_collect_sites.py:15-22,44-59` — "and node.func.value.id ==
  \"gc\"" — Detects only `gc.collect()` spelled through the name `gc` in src/*.py (flat, non-recursive
  glob); `from gc import collect`, aliases, and every other scope (tests/, digital_twin/,
  tests_hardware/) are unchecked here; buildgen check is presence-per-file, not count or placement ·
  related: TEST.S11 · [H10]

## tests_scripts/test_heap_map_parser.py

- **MEM.N088** INVAR · `tests_scripts/test_heap_map_parser.py:271-274` — "a probe that degrades
  internally still returns normally, so RES says ok - only the log between its TRY and RES shows it" —
  `parse_allocation_need` must treat a logged `memory allocation failed` as a failure (I.4(e)); this
  file itself carries that literal string in fixture text · related: TEST.T18 · [H10]

## tests_scripts/test_lint_sh.py

- **MEM.N089** LIMIT · `tests_scripts/test_lint_sh.py:86-98` — "the exclusion is `grep -v \"^src/system_service.py:\"`,
  anchored and with the colon" — lint.sh's gc.collect allowance is file-granular (any function in
  system_service.py / codegen.py passes); function-level attribution exists only in
  test_gc_collect_sites.py · [H10]

## tests_scripts/test_memory_error_gate_agreement.py

- **MEM.N090** MIRROR · `tests_scripts/test_memory_error_gate_agreement.py:2-39 (agent cited tests_scripts/test_memory_error_gate_agreement.py:28-39)`
  — "each holding its own copy of the pattern. This keeps all four agreeing" —
  harness.MEMORY_ERROR_MARKERS ↔ ci_suite._MEMORY_ERROR_MARKERS ↔ test.sh `local pattern="MemoryError|memory allocation failed"`
  (substring-presence check only, not how the grep uses it) · related: TEST.T18 · [H10] ⟨re-anchored:
  quote found at line 2⟩
- **MEM.N091** LIMIT · `tests_scripts/test_memory_error_gate_agreement.py:54,63-83` — "_INJECTION_SCOPES
  = (\"tests\", \"digital_twin\")" — Injection-wording scan covers tests/ and digital_twin/ only (not
  tests_hardware/), sees only literal string args of `MemoryError(...)` or raises through a
  non-*Error/*Exception callee; f-strings/variables are invisible (floor >= 12) · [H10]

## tests_scripts/test_test_sh.py

- **MEM.N092** INVAR · `tests_scripts/test_test_sh.py:558-629` — "a degrade-and-pass went by in silence"
  — Unit-tier MemoryError gate: both PASS and FAIL exits flagged, flag sets failed=1 and is named in the
  summary (structural substring checks); injections worded "simulated allocation failure" (15 sites) ·
  related: TEST.T18 · [H10]
- **MEM.N093** ASSUME · `tests_scripts/test_test_sh.py:602-603` — "measured over a full 85-file run, the
  suite's own output contains neither pattern once" — Dated measurement justifying the gate's
  false-positive rate; "85 files" is a dated count · related: DOC.S08 · [H10]

## tests_scripts/test_threshold_runner.py

- **MEM.N094** MIRROR · `tests_scripts/test_threshold_runner.py:11` — "_SHIPPED_THRESHOLD = 32768 # what
  buildgen emits into the generated boot entry (codegen.py)" — Hand copy of the firmware's gc.threshold
  value; not cross-checked against codegen here · related: SCR.S10 · [H10]

## SPECIFICATION.md Part B.14.2 / B.14.2.1 (`lwip_connection_counts`, 1215-1379)

- **MEM.N095** SETTLED · `SPECIFICATION.md:1321-1325` — "`PBUF_POOL_SIZE` is deliberately left alone.
  ... Confirmed on silicon: at an 8x advertised inbound over-commit ... it never surfaced" — Deliberate;
  evidence in git-only archive §7R.2. · related: DOC.S04 · [H12]
- **MEM.N096** ASSUME · `SPECIFICATION.md:1328-1364` — "Measured cost, from real builds ... Absolute
  heaps are from the builds of that day; the deltas are what transfer." — Undated build-size tables;
  shipped 6-connection GC heap 192,488 / linker 192,360 B. · related: DOC.T08 · [H12]

## SPECIFICATION.md Part C.8 (Concurrency & locking model, 2016-2188)

- **MEM.N097** ASSUME · `SPECIFICATION.md:2032-2034` — "it took a blank FRAM-backed logger `setup()`
  from 122,880 to 13,696 board-equivalent bytes" — Measurement cited to git-only archive §7C. · related:
  DOC.S04 · [H12]

## SPECIFICATION.md Part E.5 / E.5.1-E.5.3 (Coverage, 2951-3088)

- **MEM.N098** ASSUME · `SPECIFICATION.md:3030-3043` — "measured false on 2026-09-18 ...
  `py/profile.c:190` ... 651,680 B — 137,120 B (4.75x)" | Dated allocation table; line-anchored upstream
  citation. · [H12]

## SPECIFICATION.md Part E.8 (Measurement traps, 3271-3362)

- **MEM.N099** ASSUME · `SPECIFICATION.md:3318-3321` — "`gc.threshold(32768)` hid it in the twin by
  re-placing the working set, and on silicon at peak did not reduce failures at all" — Silicon finding
  (git-only archive §7Q.11). · related: DOC.S04 · [H12]
- **MEM.N100** INVAR · `SPECIFICATION.md:3322-3334` — "Collect before any heap sample, and say so ...
  Never let the offered load scale with the setting under test ... Ballast guards use the largest free
  run, never `gc.mem_free()`" — Measurement rules; review-only. · related: TEST.T03 · [H12]

## SPECIFICATION.md Part E.9 (Driver/DUT process separation, 3364-3421)

- **MEM.N101** SETTLED · `SPECIFICATION.md:3385-3387` — "keeps only `_mem_sampler()` ... plus the
  `gc.collect()` that settles it before each sample (I.4(e)'s own narrow, separately-litigated
  exception)" — Approved `gc.collect()` in the twin runner. · related: TEST.T03 · [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **MEM.N102** INVAR · `SPECIFICATION.md:3465-3467` — "Any code sizing an allocation from
  external/caller input must clamp the size *before* allocating, not just catch `MemoryError`" —
  Convention for every caller-sized allocation (`LockableBuffer`/`PrintLogHistory` as pattern). ·
  related: MEM.T03 · [H13]
- **MEM.N103** INVAR · `SPECIFICATION.md:3505-3507` — "Code copying a computed span into a buffer must
  therefore bound-check the span itself" — Convention; `asy_uart_comm.py`'s `written + size > len(dest)`
  guard named as the instance. · related: UART.T03 · [H13]

## SPECIFICATION.md Part F.2 — Blocking calls / timeout-wrapping

- **MEM.N104** SETTLED · `SPECIFICATION.md:3600-3601` — "Don't wrap every `asyncio` primitive call in
  `try`/`except` against a theoretical `MemoryError`" — Do-not-reopen; narrow exception "for a concrete,
  non-hypothetical threat". · related: DOC.T14 · [H13]

## SPECIFICATION.md Part F.5.3 — Free wins in the 1.29 build

- **MEM.N105** ASSUME · `SPECIFICATION.md:3759-3765` — "`RAM: 66,792 B / 256 KB (25.48%)` ... leaves
  **130,224 B free with a 115,536 B largest obtainable single block** ... a largest known single
  allocation of ~5.7 KB ... that is ample" — Single dated measurement (2026-09-11, dev board); "largest
  known allocation" is an unverified inventory claim. · related: HW.T16, MEM.T06 · [H13]
- **MEM.N106** SETTLED · `SPECIFICATION.md:3774-3777` — "measuring a loaded floor at 1.29 would need
  `mem_free` exposed over REST, which is deliberately not done" — Deliberate gap: no 1.29 loaded-heap
  floor exists; 1.28's 91,312 B is not comparable. · [H13]

## SPECIFICATION.md Part G.2 — Known reusable primitives

- **MEM.N107** INVAR · `SPECIFICATION.md:4189-4192` — "**Every transfer method comes in pairs** —
  `write(data)`/`write_into(buf)` and `read()`/`read_into(buf)`" — Buffer-API shape rule; `AsyFramChunk`
  is the reference. · related: XCUT.T15 · [H13]
- **MEM.N108** INVAR · `SPECIFICATION.md:4196-4198` — "**A failed allocation degrades to a `None`
  buffer, never an exception** ... every consumer's first act is `if buf is None: return False`" —
  Caller-discipline rule for every `LockableBuffer` consumer. · related: CORE.T08 · [H13]

## SPECIFICATION.md Part I (intro)

- **MEM.N109** ASSUME · `SPECIFICATION.md:4766-4770` — "Written up during the 2026-09-07 systematic
  memory-safety audit ... Everything else scanned was already correct." — Dated whole-`src/` audit
  conclusion; predates several modules. · covered-by: MEM.T01 · [H13]

## SPECIFICATION.md Part I.1 — MicroPython memory-management facts

- **MEM.N110** ASSUME · `SPECIFICATION.md:4783-4785` — "every accumulation loop in `src/` either bounds
  total size or already guards the one failure that matters, `asy_uart_driver.py`" — Whole-`src/` claim
  from the 2026-09-07 scan. · related: MEM.T01, MEM.T04 · [H13]
- **MEM.N111** RISK · `SPECIFICATION.md:4799-4801` — "Pico W's CYW43 firmware genuinely reduces usable
  heap versus a plain Pico (roughly half the 264KB SRAM) — an accepted, unavoidable fact of this board
  choice" — Accepted board-level constraint. · [H13]
- **MEM.N112** SETTLED · `SPECIFICATION.md:4811-4812` — "`gc.collect()`/`gc.threshold()`/`gc.disable()`
  as the only Python-visible knobs — all of which I.4 forbids as remedies" — Restates the
  no-GC-knob-as-fix rule. · related: DOC.T14 · [H13]
- **MEM.N113** SETTLED · `SPECIFICATION.md:4828-4833` — "The C-level technique would need a fork of
  vendored MicroPython, which CLAUDE.md forbids; **the Python-level analogue needs no fork** — allocate
  the long-lived objects first" — Placement design principle; C.13's init/setup split is the mechanism.
  · related: MEM.T02 · [H13]
- **MEM.N114** INVAR · `SPECIFICATION.md:4831-4833` — "why (f.1)'s two boot lists are the only places
  left where placement has to be managed explicitly" — Assumes all other long-lived allocations land in
  `__init__`; run-phase long-lived allocations would violate it. · covered-by: MEM.T02 · [H13]
- **MEM.N115** ASSUME · `SPECIFICATION.md:4838-4840` — "**No free-heap target is published.** ... The
  20-30 % free at peak that H.7 uses is general embedded practice." — H.7's `max_connections` target
  rests on a practice figure, not a requirement. · related: PERF.T02 · [H13]

## SPECIFICATION.md Part I.2 — Hotspot catalog

- **MEM.N116** ASSUME · `SPECIFICATION.md:4851-4858` — "**Reviewed, found already safe (no change
  made)**: ... `captive_dns.py`'s `DNSQuery` (bounded by a single DNS datagram's structural limits) ...
  `asy_wifi_service.py` (no `network.WLAN.scan()` call anywhere)" — Dated per-file safety verdicts; plan
  seed shows `captive_dns` receiving `recvfrom(4096)` per datagram. · related: MEM.T01, NET.S10 · [H13]

## SPECIFICATION.md Part I.3 — Bounded response assembly

- **MEM.N117** ASSUME · `SPECIFICATION.md:4911-4920` — "with 1,024 B pieces the board served at most 4
  concurrent requests without a `MemoryError` ... `/status` 320 B (1,024 B with the old cap), every
  other route and data source ≤ 256 B" — Measured need per path on the 32-bit twin (archive
  §7R.3/§7Q.10). · related: HW.T16, DOC.S04 · [H13]
- **MEM.N118** LIMIT · `SPECIFICATION.md:4922-4933` — "the ceiling is the longest string any schema
  permits, which is `NTP_Host`'s 1,024 characters ... the long-value case is bounded by argument, not
  measured ... do not read \"≤ 256 B\" as covering a device whose user has typed a long server address"
  — Known over-cap piece (~1,026 B) on `/networking`/`/status`; would not fit at a limit of 7. ·
  related: REST.S06, REST.T05 · [H13]

## SPECIFICATION.md Part I.4 — Multi-stage memory-error scheme, (a)-(e)

- **MEM.N119** INVAR · `SPECIFICATION.md:4977-4979` — "**Every module in `src/`, present and future,
  follows this ladder** for anything that can plausibly exhaust memory" — Standing design ladder;
  review-enforced (dup of CLAUDE.md). · related: MEM.T01 · [H13]
- **MEM.N120** SETTLED · `SPECIFICATION.md:4982-4990` — "a caught `MemoryError`, even one that never
  crashes anything, is a design defect to fix at its source, not a handled case to accept" — Standing
  rule (a). · related: DOC.T14 · [H13]
- **MEM.N121** INVAR · `SPECIFICATION.md:4990-4993` — "a caught failure produces a well-defined
  \"unavailable\"/`None`/`False` result, never an unguarded re-raise
  (`_write_guarded()`/`_write_errcount_entry()` substitute `{\"error\":\"unavailable\"}`" — Degrade
  contract (b); the UI renders it as "—" with no signal (WEB.S09). · related: WEB.S09 · [H13]

## SPECIFICATION.md Part I.4 — (f), (f.1), (g)

- **MEM.N122** SETTLED · `SPECIFICATION.md:5059-5067` — "**(f) A `gc.threshold()` value (or a
  `gc.collect()` call) is defense in depth applied only once (e) already holds — never the fix itself" —
  Standing rule; every generated boot entry sets `gc.threshold(32768)`. · related: DOC.T14 · [H13]
- **MEM.N123** SETTLED · `SPECIFICATION.md:5073-5083` — "**(f.1) The one structural exception: a
  boot-confined placement reset.** `gc.collect()` between the units of the two *one-time* setup lists
  ... **and nowhere else whatsoever**" — Owner-approved exception (2026-09-18 per CLAUDE.md). · related:
  DOC.T14 · [H13]
- **MEM.N124** ASSUME · `SPECIFICATION.md:5085-5094` — "on the twin at `gc.threshold(-1)` ... a factor
  of 3.2 to 6.9 on largest-contiguous-over-free ... At the shipped `gc.threshold(32768)` it changes
  nothing measurable" — Twin measurements cited to archive §7A; cites
  `docs/reference/constrained.rst:413-437` at v1.29.0. · related: DOC.S04 · [H13]
- **MEM.N125** INVAR · `SPECIFICATION.md:5096-5103` — "`tests_scripts/test_gc_collect_sites.py` walks
  `src/` with `ast` and asserts the only `gc.collect()` call site is
  `system_service.start_and_check_tasks` ... plus a textual assertion that `buildgen/` emits one only
  from `codegen.py`" — Enforced (test + `scripts/lint.sh`); generated output itself is checked only
  textually at the emitter. · related: TEST.S11 · [H13]
- **MEM.N126** INVAR · `SPECIFICATION.md:5116-5118` — "no `gc.collect()` in business logic, none in the
  run phase (the supervisor loop under the starter list is the run phase and is asserted to have none)"
  — Run-phase prohibition. · related: TEST.T03 · [H13]
- **MEM.N127** INVAR · `SPECIFICATION.md:5120-5123` — "fix it with a design-level technique that
  relieves the pressure directly ... never a GC-policy change or an added `gc.collect()` call" — Rule
  (g). · related: MEM.T06 · [H13]
- **MEM.N128** INVAR · `SPECIFICATION.md:5125-5128` — "run it through (a)-(d) at design time and give it
  its own (e)/(f)-shaped test pair" — Review-only obligation for every new allocation-holding
  function/module. · related: TEST.T06 · [H13]

## SPECIFICATION.md Part I.5 — Real-hardware confirmation

- **MEM.N129** ASSUME · `SPECIFICATION.md:5132-5135` — "confirmed on real target hardware (2026-09-08):
  `gc.threshold(32768)` (real hammer-load `mem_free` floor 91312 bytes vs. 128 bytes at the
  reactive-only default)" — Dated 1.28-era silicon figures (a 128 B floor at -1 under hammer). ·
  related: HW.T16 · [H13]

## SPECIFICATION.md Part J.8 — Memory model

- **MEM.N130** INVAR · `SPECIFICATION.md:5632-5634` — "**Preallocate from `CHUNKS`, never grow.** The
  total upper bound `CHUNKS × payload_size` is known the moment the first frame of a train arrives" —
  Peer-declared size drives allocation (BACKLOG accepted-with-caveat). · covered-by: UART.T03 · [H13]

## CLAUDE.md

- **MEM.N131** INVAR · `CLAUDE.md:307-320` — "design for zero `MemoryError`s first,
  catch→degrade→restart→watchdog as a last-resort backstop" — A caught MemoryError counts as a design
  defect. The supervisor catches MemoryError. · related: MEM.T06 · [H14]
- **MEM.N132** INVAR · `CLAUDE.md:320-329` — "the whole suite must pass with `gc.threshold(-1)` ... and
  with zero `MemoryError`s — caught-and-logged included" — Enforced by scripts/test.sh:321-329,
  scripts/_digital_twin_ci_suite.py:185-187, tests_hardware/harness.py:37 and
  tests_scripts/test_memory_error_gate_agreement.py. · related: TEST.T18 · [H14]
- **MEM.N133** LIMIT · `CLAUDE.md:329-335` — "There are FOUR such gates — the unit tier, the twin tier
  and the flash/bench real-hardware soak gates" — MicroPython processes outside those four are never
  scanned: tests_scripts twin boots, Vitest live twins, cross-browser smoke, and other hardware tests. ·
  covered-by: TEST.T18 · [H14]
- **MEM.N134** ASSUME · `CLAUDE.md:331-333` — "`src/` logs `str(e)`, not the class, so a real
  caught-and-degraded allocation failure never contains the word \"MemoryError\"" — The gate design
  depends on this logging convention, which nothing enforces. · related: TEST.T18 · [H14]
- **MEM.N135** SETTLED · `CLAUDE.md:339-347` — "One structural exception, added 2026-09-18 with the
  owner's approval: the boot-confined placement reset" — Enforced by scripts/lint.sh:42-49,
  tests_scripts/test_gc_collect_sites.py and tests_scripts/test_digital_twin_boot_contiguity.py. ·
  related: DOC.T14 · [H14]
- **MEM.N136** ASSUME · `CLAUDE.md:353-354` — "(80% held against 12% at the reactive default)" — Single
  silicon measurement, with no image or commit named. · related: HW.T16 · [H14]
- **MEM.N137** INVAR · `CLAUDE.md:355-360` — "it is forbidden as the fix itself for a design that still
  needs one big contiguous allocation somewhere" — A threshold or `gc.collect()` is never the fix.
  Convention only. · covered-by: MEM.T06 · [H14]

## BACKLOG.md

- **MEM.N138** OPENQ · `BACKLOG.md:874-883` — "Part I.2's hotspot catalog has never been re-walked with
  a placement lens." — Run-phase long-lived allocation during churn: open question, no measurement
  points at one. · covered-by: MEM.T02 · [H15]

## HEAP_FRAGMENTATION_MEASUREMENTS.md (current, 393 lines; owning area HW)

- **MEM.N139** ASSUME · `HEAP_FRAGMENTATION_MEASUREMENTS.md:33-41` — "The placement law [TWIN, confirmed
  per object with no counterexample]" — Twin-only law; the board's per-object picture was never measured
  (closed as not pursued, M8). · [H15]
- **MEM.N140** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:109-122` — "the twin's placement ratios,
  applied to the board — does not" | Metrics table: kept%, free-run counts, cross-heap-size ratios,
  post-burst probing and twin ratios do not work. · related: TWIN.T06 · [H15]
- **MEM.N141** SETTLED · `HEAP_FRAGMENTATION_MEASUREMENTS.md:128-137` — "Never raise a threshold to fit
  a board reading." — Thresholds derived from the worst reachable allocation (16,384 B when derived;
  2,048 B since SPEC I.6). · [H15]
- **MEM.N142** SETTLED · `HEAP_FRAGMENTATION_MEASUREMENTS.md:359-378` — "Measured, not argued; don't
  re-spend time on them without a new mechanism." — Ruled-out remedies (churn cut, hoisting, bigger
  heap, removing sleeps, `ThreadSafeFlag`, write-path components, combinations, `gc.collect()`/threshold
  as fix). · related: DOC.T14 · [H15]
- **MEM.N143** SETTLED · `HEAP_FRAGMENTATION_MEASUREMENTS.md:387-393` — "Closed by the owner, 2026-09-24
  — re-open only if a new layout symptom appears." — Four research gaps closed as not pursued. · [H15]

## Archive `12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md` (5,553 lines) — only items still open/undecided/deferred/next-step there, with carry status in current docs

- **MEM.N144** OPENQ · `ARCH:520 (+ :414-418)` — "Gap 2's positive branch at real positions (§0B.4) —
  the one remaining mechanism gap." — Placement law confirmed 20+ times synthetically, zero times at a
  real survivor position. NOT carried: current M8 (:389-393) closes four gaps but not this one. · [H15]
- **MEM.N145** OPENQ · `ARCH:521-528` — "What in base's churn does the stranding at a given dose is
  still open" — Carried: current M8 :390 (closed as not pursued, owner 2026-09-24). · [H15]
- **MEM.N146** OPENQ · `ARCH:529-532` — "What is still untested is whether parallelism matters after
  boot" — Carried: current M8 :390-391. · [H15]
- **MEM.N147** OPENQ · `ARCH:560-564` — "what stays unmeasured is the per-object question" — 16 B board
  blocks move the one-block immunity boundary. Carried: current M8 :391-392. · [H15]
- **MEM.N148** OPENQ · `ARCH:296 (+ :273)` — "The survivors' own size class is what makes them
  vulnerable — [U] — and this is a sharp, untested prediction" | §0A.7's closure summary ("1, 3, 5 and 7
  closed; 6 and 8 dissolved; 2 ... still open") never accounts for item 4; not carried. (low) · [H15]
- **MEM.N149** LIMIT · `ARCH:2306-2309, :2876-2882` — "The run phase over months of uptime is still
  untouched" — No layout measurement over months; current docs carry only the 6 h soak (queue S4). Not
  carried as such. · related: MEM.T02 · [H15]
- **MEM.N150** OPENQ · `ARCH:2961-2967` — "if a later measurement finds survivors born in that gap, the
  question reopens as its own decision" — Third boot stretch (`start_timers()` + `ntp_force_sync()`
  between the two setup lists) has no boot-confined collect; not carried in the current heap doc or SPEC
  I.4(f.1). · related: MEM.T02 · [H15]
- **MEM.N151** TODO · `ARCH:3383-3388` — "a heapsize decision, which is the owner's call and bigger than
  this change. Recorded as an option, not built." — Calibrated-heap host-side layout gate; partly
  superseded by the heap-size-independent twin guard (current :242-247). · [H15]
- **MEM.N152** TODO · `ARCH:5551-5553` — "Optional, not started: rebuild the frozen port ... and run the
  exact same-binary A/B" — Carried: current M8 :392 (closed as not pursued). · [H15]
- **MEM.N153** LIMIT · `ARCH:2581-2583` — "Gap, stated rather than papered over ... Closing it needs the
  pre-restructure frozen binary rebuilt" — Not carried (superseded by later silicon runs). (low) · [H15]
- **MEM.N154** ASSUME · `ARCH:96` — "whether that clears the floor is untested" — C9; moot since the
  80,000 B floor was retired (§7G). Not carried. (low) · [H15]
- **MEM.N155** TODO · `ARCH:1874-1877` — "the sub-76 regime is untested — and that is precisely where
  remedy lever (b) operates" — Superseded inside the archive by §6A.12 (lever killed); listed for
  completeness. (low) · [H15]
- **MEM.N156** SETTLED · `ARCH:5391` — "Nothing is open here any more." — §11 owner decisions (settrace
  split, CRC "don't touch", FRAM exception, no-defer ordering, boot collects, lock per block op, floor
  retired); the CRC and ordering ones are carried at SPECIFICATION.md:4876-4885. · [H15]

## Commit messages (chronological)

- **MEM.N157** SETTLED · `commit c55f012 / 3ab1dae` — "wrapping every asyncio primitive call in
  try/except against a theoretical internal MemoryError is overkill" — Closed open question #14;
  standing rule. · tracked: CLAUDE.md hard rule + SPECIFICATION F.2 | - · [H17]
- **MEM.N158** SETTLED · `commit 887da0e / b7d889e` — "Set gc.threshold(32768) as defense in depth ...
  closed per explicit project owner direction - a data-gathering question about an already-decided
  threshold" — Threshold choice rests on single ~90 s runs per candidate (non-monotonic hammer trend
  never repeated). · tracked: CLAUDE.md memory rule, SPECIFICATION Part I.4 | related: MEM.T* · [H17]
- **MEM.N159** NOTE(ROLLBACK) · `commit d4814cc` — "WP2's extra per-ConfigManager FRAM chunk caused real
  MemoryErrors that were resolved by raising -X heapsize from 8M to 16M ... the fix CLAUDE.md's
  memory-safety ladder explicitly forbids" — WP work rolled back. · status: WP1/WP2 later re-done;
  heapsize history tracked in SPEC E.3.1 (32M then back to 16M after per-device split) | related: MEM.T*
  · [H17]
- **MEM.N160** NOTE(KNOWN-DEFECT) · `commit 15715d4 / f83ca14 / e723f2f` — "the remaining failure being
  the pre-existing heap-fragmentation defect" (largest block 115,536 -> 20,592 after WP1+WP2) — Heap
  fragmentation fails test_memory_stress.py 80,000 B floor. · tracked:
  HEAP_FRAGMENTATION_MEASUREMENTS.md, SPEC I.4(f.1) (boot-confined gc.collect placement reset,
  owner-approved 2026-09-18) | related: MEM.T* · [H17]
- **MEM.N161** NOTE(NOT-COMMITTED) · `commit e723f2f` — "Every remedy candidate's ensembled numbers, and
  the two that are measured but deliberately not committed pending the owner's decision" — Pending owner
  decisions on heap remedies. · status: resolved by owner-approved boot placement reset (CLAUDE.md
  2026-09-18); two owner decisions moved to SPEC I.2 in 17b4354 | - · [H17]
- **MEM.N162** NOTE(OPEN-MODEL) · `commits 34097d7, b70a63a` — "One thing deliberately left open:
  whether the small-object COUNT threshold ... is mediated by collection frequency"; "Ten open items, of
  which four are mechanism-critical" — Heap model open items. · status: partly closed in a6be008;
  remainder in archive (12640c2) — condensed doc keeps method only (not re-verified item-by-item) |
  related: MEM.T* · [H17]
- **MEM.N163** NOTE(INSTRUMENT-TRAP) · `commit 99080ff / 4f39c0b` — free_run_profile() MemoryErrors on
  its own probe; lint gate misread from tail of output — Measurement/verification traps. · tracked:
  HEAP_FRAGMENTATION_MEASUREMENTS.md §M (traps) | - · [H17]
- **MEM.N164** NOTE(RESOLVED) · `commit 3ecf840 / 1ef697a` — "The floor is a regression tripwire, not a
  consumer's demand"; "Reported, not changed: the 4,096 B max_content_length bounds what is answered,
  not what is allocated. Request.max_body_length stays at microdot's 16 KB default" — 80,000 B floor
  semantics; oversized PUT buffered whole. · status: max_body_length done
  (src/asy_webserver_service.py:370 sets Request.max_body_length = max_content_length) | - · [H17]
- **MEM.N165** NOTE(UNSHIPPED-BY-DECISION) · `commit 3db1382` — "PR #84 ... none of its
  build-and-instrument tooling ... exists on any other branch, so closing leaves it unshipped by
  decision" — GC-policy-as-build-property tooling abandoned. · tracked: commit message only (not in
  BACKLOG) | - · [H17 (also H17)]
- **MEM.N166** NOTE(HW-FINDING) · `commit 1519f10` — "The defect is position-dependent ... Every
  standalone heap reading measures the wrong thing"; "A ... broke the two FRAM fault injectors"; "F1 --
  wifi_service_reconnect_repro.py persists a garbage SSID and never restores it, which stranded the
  bench" — Measurement validity + harness breakage. · status: injectors and F1 done-in da9bcf1;
  position-dependence tracked in HEAP_FRAGMENTATION_MEASUREMENTS.md | - · [H17]
- **MEM.N167** NOTE(OBSERVATION) · `commit 7ccbe8d` — "The real main() runs start_timers() and an NTP
  sync between the two lists, so the firmware has a third boot stretch with no collect in it - B's
  design covers the two lists deliberately and widening it would widen the I.4 exception, so it is
  recorded as an observation, not changed" — Uncovered boot stretch for the placement reset. · UNTRACKED
  (low; SPEC I.4(f.1) at :5073 names only the two lists, not this gap) | related: MEM.T* · [H17]
- **MEM.N168** NOTE(FLAGGED) · `commit c500bb9` — "SPECIFICATION.md I.3's 49152 B hammer-load figure has
  the artefact's exact signature ... flagged in place and queued as R16, not corrected" — Suspect
  measurement in SPEC. · status: SPEC no longer contains "49152"/"49,152" (grep) — likely corrected
  later; R16 not present in queue at 2a88cc8 (not re-verified) | - · [H17]
- **MEM.N169** NOTE(OWNER) · `commit 3fe0fb2` — "The owner's decision, 2026-09-19: the floor was never
  theirs ... replace it with three checks" (used <= 100,000 B; placement above top survivor; largest
  free >= 32,768 B) — 80,000 B floor retired. · tracked: tests_hardware (heap_map.py), queue | - · [H17]
- **MEM.N170** NOTE(UNVERIFIED-ON-SILICON) · `commit 3fe0fb2 / f5920e5` — "It has never been measured on
  silicon, on any image"; "32,768 B is NOT verified for the board - reported, not asserted" — New heap
  checks unproven on hardware. · status: HEAP doc condensation mentions §7R.2 bench results 2026-09-23
  (not re-verified which checks) | related: HW.T* · [H17]
- **MEM.N171** NOTE(HW-FINDING) · `commit e486877` — "with gc.threshold(32768) set before the run, the
  run-phase decay does not happen ... the threshold is not defence in depth on top of B, it is what
  carries B's gain into the run phase ... reported, not asserted" — Threshold load-bearing for run-phase
  layout. · tracked: CLAUDE.md (memory rule: "on silicon it is what carries the boot placement gain into
  the run phase") | related: MEM.T* · [H17]
- **MEM.N172** NOTE(NOT-ASSERTED) · `commit 309857c` — "The settled position is measured and
  deliberately not asserted on - dev's suppressed arm reads better there than its live arm, so the
  run-phase decay can invert the ranking" — Boot contiguity guard stops at the list ends. · tracked:
  HEAP annex / tests_scripts/test_digital_twin_boot_contiguity.py | - · [H17]
- **MEM.N173** NOTE(QUEUED) · `commit 5c5a2d0` — "G8: CLAUDE.md's (e) stage has no silicon arm at all,
  because build_firmware.py stages the boot entry as main.py and it sets gc.threshold(32768), so every
  flash- and bench-tier run is an (f)-stage run" — CLAUDE.md's "every test ... real hardware alike"
  (e)-stage requirement is not met on silicon. · tracked: REAL_HARDWARE_TEST_QUEUE.md:276 (G8) |
  related: MEM.T*, HW.T* · [H17 (also H17)]
- **MEM.N174** NOTE(HW-NEGATIVE) · `commit 3d9e22d` — "the twin's two transferable ratios do NOT survive
  the trip to silicon: batch median depth 0.69x (inverted) against the host's 2.07x" — Twin placement
  metrics do not transfer to board fill. · tracked: HEAP annex §7M, SPEC I.4(f.1) note (4daa3cf) |
  related: TWIN.T* · [H17 (also H17)]
- **MEM.N175** NOTE(OWNER-CALL) · `commit 8ef8ce9` — "the generated boot entry's gc.threshold(32768) is
  load-bearing. At MicroPython's own reactive -1 ... the board serves at most 4 without an allocation
  failure ... It is the owner's call what to do about it" — Contradicted the (e)-stage claim. · status:
  done — bounded _PieceWriter (79cb3b1), static 256 B reads + Content-Length (db1866e), limit 6 clean at
  -1 on silicon (25c6cbb) | related: MEM.T* · [H17]
