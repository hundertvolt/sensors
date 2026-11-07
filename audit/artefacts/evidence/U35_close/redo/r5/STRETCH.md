stretch hand-back, written by the agent (Sat Nov  7 18:16 UTC 2026)
Read only, tree `S/wt-u35int` (b412d1b3). HB = bench `origin/claude/u35-bench-campaign` (7b204269) `.../hw_round1/HANDBACK.md`; RC = its `ROOT_CAUSES_20261105.md`. C = confirmed (code, measurement), I = inferred. Probes in `ftmp_stretch/probe/` via run.sh (`S/u35/lead/stretch_*.log`; medians of 200-300 runs, host shared with bfix's gate, so ratios, not
absolutes). "32-bit" = the i386 Unix port `S/u35r/bench/mem32` (31-bit small ints, 16 B blocks, as the RP2040); "64-bit" = tc-int's standard port. Board/port scale: RC 20's pre-fix errcount entry 29 ms vs the same walk 205-219 us = x132-141; the VOC step 41.3 ms vs 222 us (32-bit) = x186.
## 1. Serving: 104-122 ms is the probe's lag, a sum of slices; the longest /status slice is `system` (~41 ms), then the errcount entries
- The figure is a 10 ms sleeper's wake lag (`heap_probe/status_timing.py:89-103`), not one step: the pinned asyncio orders by ready time and `sleep(0)` re-queues at now
  (`extmod/asyncio/core.py:43-58`, `extmod/modasyncio.c:82-85`, v1.29.0), so a late wake waits one slice of every task queued before it; probe: 1/2/3 tasks of 30 ms slices
  give 20/50/81 ms lag (C). At 1 reader only 4 of 47 requests met a lag >= 100 ms (HB:42788), e.g. `system` 41 + one collection 20 + the 1 Hz VOC step 41 = 102 ms (I).
- Slices: a build yields after each of its 28 top-level values (`asy_webserver_service.py:240-243`, `:663-692`). Above 21 ms: `system`, 41 ms mean / 70 max pre-fix (RC 20, C),
  its write only 7 % cheaper after the fix (180->167 us, C), so ~41 ms now (I): ~23 ms writing ~330 B (two 8-member time dicts, not "flat") + ~16 ms its source (I). Each
  errcount entry: 298 B out, 125-144 us now on the ports (205-219 pre-fix), ~17-20 ms on the board (I). One build allocates 160 KB for ~7.4 KB of JSON (6.6 KB per entry;
  32-bit, C): ~5 collections of ~20 ms at 32768, each landing inside a slice (I). Build CPU ~400-480 ms per /status (I: 739 ms x the ports' 0.54-0.65).
- Need: C json.dumps of one 298 B entry is 12-16 us (~2 ms board, I), but one 298 B block breaks the 256 B piece rule (I.3). Smallest fix at source: `_write_errcount_entry()`
  (`:910-917`) writes each history item as one fragment `'{"type": "%s", "num": %d}'`, dropping `_shape_errcount_entry()`'s dicts (`:988-998`) and the generic walk
  (`:220-238`): bytes identical on both ports (C; MicroPython's key order, "history" before "counter", so a test pins it against json.dumps), 41-46 us (3.1x) and 2,064 B
  (3.2x) per entry (C), ~6 ms on the board; build ~160 ms CPU, ~2 collections (I). `system`, only for LED frames (3): a yield per section member (`_write_status_source()`,
  `:929-936`) leaves its source (~16 ms, I) or LocalTime (50-62 us, ~7 ms, I) as the largest slice. Origin: shape pre-audit 08-12 (d49a0f7b), walk 09-23 (79cb3b1b),
  flat dump and per-value yield post-restart 11-06 (6cc6af1a).
## 2. VOC: 41.3 ms is the port's 32-bit C emulation on boxed ints, ~900x the computation's need; a bit-identical form is 2.5x cheaper
- Per full step (C, counted): 42 `_fix16_mul` (exp's included), 11 bit-serial `_fix16_div`, 6 `_fix16_exp`, 2 `_fix16_sqrt`, 79.5 `_f16()` float conversions of constants;
  18.5 KB allocated per step on the 32-bit port (values past 2**30 become mpz, floats boxed), 5 KB on 64-bit (floats only). Stages (32-bit): mean-variance estimator 53 %
  (gamma's sigmoids), sigmoid-scaled 24 %, adaptive lowpass 15 %, MOX 4 % (C).
- Need: Sensirion's reference is this fix16 C, made for FPU-less MCUs (`voc_algorithm.py:5-8`); these op counts are ~10**4 Cortex-M0+ cycles, <= 0.1 ms at 125 MHz (I:
  counts C, cycles estimated). Legacy ran the same port synchronously in its 1 s read (`legacy/firmware/python/IndividualDrivers/asy_sgp40_driver/__init__.py:44`, `:457`;
  107 `_f16(` sites, same div), in the field with no consumer under 50 ms (I, never timed).
- Smallest fix at source (`voc_algorithm.py:209-279`): fold the 53 constant `_f16()` expressions to ints (103 sites; double as C's F16(); a float32 evaluation gives the same
  53 ints, C by emulation) and compute mul/div as exact Python-int products with libfixmath's rounding and overflow. 0 mismatches in 20,168 mul and 30,000 div vectors, equal
  index and packed state over 4,000 steps with clamped and out-of-range raws (C, both ports); median 222->88 us (32-bit), 100->39 us (64-bit), 18.7->6.4 KB per step (C)
  -> ~16 ms on the board, under 21; VOC alone triggers a 32768 collection every ~1.75 s -> ~5 s (I). Not the bound makes it a defect (41 ms crosses no real consumer, 3), D.8's
  cost far beyond need does. Origin: emulation original (legacy port); `_int32` wraps audit 10-07 (2949ed97).
## 3. Who needs 21 ms: nothing in the code at that value; it acts only as J.6's floor term
- Floor `2 x poll_wait + poll_idle + 21` (`asy_uart_comm.py:598-605`, `buildgen/validate.py:986-993`) and hard consumer `reply - (2 x poll_wait + poll_idle + 21)`
  (`validate.py:1318-1330`): dev's 1,000 ms link tolerates 925-946 ms (C). Only a link set at its floor (75 ms on dev's polls) breaks at 21 ms; none is (I). Silicon's loop lag
  reaches 155 ms, p99 64 ms (HB:42795): the floor's right term is that lag, not one collection, 209 ms on dev's polls, still under 1,000 (I). Origin: floor 09-11 (c63ef97a);
  `con.routine_stall` audit 10-21 (72b12815).
- Others and their breaking value (C unless marked): RX ring with a stop-and-wait peer past the 2,129 ms flash-hold floor; a continuous sender laps 512 B in 44 ms (bench only,
  overrun accepted, J.6). Watchdog 6,000 ms (F.3). LED frames 50 ms, cosmetic (`asy_neopixel_driver.py:29`, `:66`, `:100`), the smallest real one: serving lags cross it, VOC
  does not. DNS 500 ms, HTTP 5 s; UDP and UART waits read the poller/ring before their deadline (`asy_udp_socket.py:124-129`; F.3), so a stretch fakes no timeout. Soft-IRQ
  queue (depth 8, `ports/rp2/mpconfigport.h:131`): Python stretches run pending callbacks (`py/vm.c:1341-1372`), only C ones (collections, flash) count. NTP sets whole
  seconds (`asy_ntp_client.py:220-233`); sensor waits only lengthen. A slice that allocates carries the collection it triggers (1): a per-slice bound is slice + one (I).
Slip: two version prints (`-c sys.implementation`) ran on the two ports outside run.sh at 18:03. Scratch: filtered HB/RC copies, `ds/` datasheet text, `probe/lean/` copy.
