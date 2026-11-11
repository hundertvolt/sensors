# The load entries re-read at 51c9c75f (W3a, agent, 2026-11-10)

## Where the cells are
- `audit/b3/load.md` at 51c9c75f holds its header and an empty table only (one commit, 656fc82f, 6 lines).
  CLOSE_STATUS P07's "audit/b3/load.md (10-22) holds the load cells" does not hold: the cells were never committed.
- They exist in two scratch records: the LD lane's full `load.md` (`S/u35/laneB/ldcm3/full/load.md`, 2026-10-28:
  52 resource x level cells (13 x 4), each with load, limit, degradation, recovery and state, plus a one-entry OR49.a (3)
  ledger) and R3's reading aid (`S/u35r/r3/d2/or49_load.md`, 2026-11-04 at 17688315: 13 resources, tests per level).
- Method: every test, file and scenario either names (105) looked up at 51c9c75f by `git grep` (script
  `ftmp_w3a/bin/check_names.py`); the cells' content re-read where the code under them changed since (1547690d
  synchronous FRAM and logging, 39e18d2a deadline grids, 25a14b4f NTP timers, ce199ebb webserver, 63a0e4cf bench).
- Result: LD 52 cells, 43 right, 8 corrected, 1 still owed; R3 13 cells, 8 right, 5 corrected. Nine lookups (eight
  distinct names) gone or renamed.
  "Owed (Hnn)" silicon cells now map to last-round steps (d: 4b flash tier, 5 bench tier; f: 12g; h: soaks).

## A. LD's 52 cells (the five OR49.a (3) fields per cell)
| cell | verdict | correction or note |
|---|---|---|
| heap L1 | corrected | test now `test_a_body_parse_that_runs_out_of_heap_answers_invalid_json` (tests/test_asy_webserver_service.py:656, ce199ebb): degradation "answers code 1 Invalid JSON, nothing persisted, no settings write" (was a 500 and one E UNEXPECTED) |
| heap L2 | right | scripts/_digital_twin_ci_suite.py:795 (`_run_11_soak`), :856 (`_run_11b_full_ceiling_concurrency`) |
| heap L3 | right | flash/test_memory_stress.py:103; owed -> steps c (4g) and d (4b) |
| heap L4 | right | bench/test_memory_stress_bench.py:72; owed (H44, H83) -> step d (5) and the 5gh/5h heap loads |
| sockets L1-L2 | right | tests/test_asy_webserver_connections.py:1170; scripts/_digital_twin_scenarios.py:584 |
| sockets L3 | right | flash/test_modlwip_listener_close.py:65; owed -> step d (4b) |
| sockets L4 | right | bench/test_network_resilience.py:438; owed (H40) -> step d (5) |
| asyncio tasks L1-L4 | right | tests/test_asy_webserver_service.py:2485; SharedBoot.idle_problems() scripts/_digital_twin_scenarios.py:369; flash/test_task_supervisor.py:46; bench/test_memory_stress_bench.py:160 |
| soft-IRQ L1-L2, L4 | right | tests/_sensortask_scenarios.py:2245; tests/test_digital_twin_timer_pool.py:237; L4 justified |
| soft-IRQ L3 | right | flash/test_bus_electrical_timing.py:31; owed (H73) -> step d (4b) |
| alarm pool L1 | corrected | NTP arms no Timer since 39e18d2a (deadline grid) and 25a14b4f (its retry waits in the sync task): `test_repeated_retry_arm_failures_count_each_and_keep_one_slot` is gone. The pool's users are the four sensor trigger timers and SYSTEM's reset timer; per-module degrade tests: tests/test_asy_bmp3xx_driver.py:2070, test_asy_scd30_driver.py:945, test_asy_sgp40_driver.py:840, test_asy_isl29125_driver.py:2887, tests/test_asy_wifi_service.py:2027 |
| alarm pool L2 | corrected | now `test_an_empty_alarm_pool_leaves_the_tick_cadences_running_and_arms_no_reset` (tests/test_digital_twin_timer_pool.py:215, 39e18d2a): the cadences are deadline sleeps, so an empty pool leaves them running, persists nothing and arms no reset; no 1 s fallback or re-arm exists any more |
| alarm pool L3-L4 | right | flash/test_bus_electrical_timing.py:42 (owed H24 -> step d (4b)); BACKLOG.md:108 "The free alarm count on silicon"; L4 justified |
| bus locks L1-L4 | right | tests/_sensortask_scenarios.py:2384; tests/test_digital_twin_bus_hazard_concurrency.py:477 (FRAM has no session lock since 1547690d); flash/test_bus_concurrency.py:147 (step d, 4b); bench/test_bus_concurrency_under_api_load.py:69 (step d, 5) |
| error-log slots L1-L4 | right | tests/_sensortask_scenarios.py:2191; L2-L4 justified |
| persisted-log write queue L1 | corrected | there is no queue since 1547690d: each entry is one synchronous chunk write inside its log call (SPECIFICATION.md F.3 `stall.fram_entry`); the scenario stays (tests/_sensortask_scenarios.py:2286); resource name: "persisted-log FRAM writes" |
| persisted-log write queue L2 | right | scripts/_digital_twin_scenarios.py:584 (resource renamed as L1) |
| persisted-log write queue L3 | corrected | measured since: an entry 12.7 ms, a backup 13.0 ms on silicon (snapshot 58, FINDINGS 12.162); re-measure in step f (12g) |
| persisted-log write queue L4 | corrected | `rate.persisted_log` restated from the measured entry time (FS; endurance ~134 y / ~1,340 y); no fault-storm run on silicon is scheduled or instrumented |
| UART buffers L1-L2 | right | tests/test_asy_uart_comm.py:2723; scripts/_digital_twin_scenarios.py:2168 (its flusher now holds a slot first, bfa240fa) |
| UART buffers L3-L4 | right | flash/test_uart_crossover.py:172; bench/test_uart_link_under_api_load.py:69; owed (H37, H84, H88) -> step d |
| CPU vs watchdog L1-L2 | right | tests/_sensortask_scenarios.py:1838; scripts/_digital_twin_scenarios.py:1265 |
| CPU vs watchdog L3-L4 | right | flash/test_memory_stress.py:151; bench/test_memory_stress_bench.py:203; owed (H20) -> step d |
| request rates L1-L3 | right | tests/test_asy_webserver_service.py:4117; scripts/_digital_twin_scenarios.py:2267; L3 justified |
| request rates L4 | right | bench/test_memory_stress_bench.py:160 (owed H64 -> step d, and step h 10g for 6 h); the floor's L4 test since 63a0e4cf: bench/test_memory_stress_bench.py:117 |
| DNS queries L1, L3 | right | tests/test_asy_captive_dns.py:1089; L3 justified |
| DNS queries L2 | corrected | `a_dns_flood_leaves_the_captive_dns_answering_and_logs_nothing` is renamed: the scenario at scripts/_digital_twin_scenarios.py:1038 (its new name holds a filtered word, read by line only), the flood :1051-1059 (`_DNS_FLOOD_DATAGRAMS` 200, :129) |
| DNS queries L4 | still owed | (H62): no bench test floods the captive DNS (git grep: none in tests_hardware/bench), and no last-round step runs one. Lead: justify (L1's real socket and L2's flood cover the logic; silicon adds only lwIP's per-socket queue) or name it as a gap |
| malformed input L1 | corrected | test now `test_malformed_head_lines_reach_microdot_which_answers_400` (tests/test_asy_webserver_connections.py:857, ce199ebb): each raises inside Microdot's Request.create() and answers 400, no drop counted |
| malformed input L2-L4 | right | scripts/_digital_twin_scenarios.py:1395; L3 justified; bench/test_network_resilience.py:769 (owed H55 -> step d, 5) |

## B. R3's 13 cells
| cell | verdict | correction |
|---|---|---|
| heap, TCP sockets, UDP sockets, log slots, tasks, DNS, malformed input | right | every name present (the script's 63 lookups) |
| CPU against the watchdog | right | its "never run: P4" bench test (bench/test_memory_stress_bench.py:203) runs in steps c (5g) and d (5) |
| soft-IRQ queue | corrected | tw. `a_boot_stagger_fire_lost_to_a_full_scheduler_queue_stalls_the_timer_start_until_the_watchdog` is gone (39e18d2a: the boot stagger sleeps to its deadlines, no timer to lose); "A1 (lane M)" is tests/test_digital_twin_timer_pool.py:237 |
| alarm pool | corrected | as LD alarm pool L1 and L2 above; device script and BACKLOG.md:108 present |
| bus locks | corrected | `test_verify_present_bounded_wait_returns_false_instead_of_hanging_when_lock_already_held` went with verify_present() and the FRAM driver's lock (1547690d; SPECIFICATION.md:3188): no FRAM lock wait exists; test_lock_order.py and tests/test_asy_spi_driver.py:1083 stay |
| UART buffers | corrected | flash/test_uart_crossover.py:200 no longer "fails up front at 512 B": it asserts no loss within the 512 B ring's bound and a reported overrun past it (:200-215); BACKLOG.md:229 |
| request rates | corrected | "E.6.6 reader-saturation-floor (the floor's L4 a gap until written)": 63a0e4cf wrote bench/test_memory_stress_bench.py:117 and removed the row |

## C. OR49.a (3)'s entries at 51c9c75f (one per new load test: gap, load, limit, degradation, recovery)
LD's ledger holds one entry; its own DNS L2 cell ("new") never joined it, and 63a0e4cf / b85e5d5c added four more.
1. Full soft-callback queue (L2), tests/test_digital_twin_timer_pool.py:237: 64 soft callbacks lost back to back;
   rp2's depth-8 queue; every callback in the spell lost, nothing logged, no reset; every periodic timer fires
   twice more and every reader reads again. Still right.
2. Captive DNS flood (L2), scripts/_digital_twin_scenarios.py:1038: 200 datagrams with no pause; lwIP's per-socket
   queue (C.7.5); the excess dropped, the first drop logged on DNSSRV; a query after the flood is answered.
3. Zero-think-time readers (L4), bench/test_memory_stress_bench.py:117: four /status readers re-requesting at once
   beside a DebugLevel PUT; the serving throughput; degraded, each reader above the twin's floor; a GET and a PUT
   each within the per-call cap after, no task ended, no reset.
4. Refusals at the ceiling (L4), bench/test_network_resilience.py:471: held heads past the ceiling; `max_connections`;
   each refusal counted once in HTTPDropped, no holder a drop; the held heads answered before they close.
5. Link under API load with FRAM writes and a config flush (L4), bench/test_uart_link_under_api_load.py:99: readers'
   load, FRAM log writes, one config write mid-run; the loop and the link; every read answered, no link failure or
   entry, the config store silent; the value reads back.
6. Concurrent /status builds (L1), tests/test_asy_webserver_service.py:3909: four readers at once; one response held
   at a time (Part I.3); the others wait; all four answered.
Entries 3-5 run first in step d (bench tier, both images). Entry 6's "the others wait" is read from its comment.
