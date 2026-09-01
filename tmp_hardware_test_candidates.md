# Real-hardware (mpremote) test candidates — working list

Scratch/temp file, not yet wired into BACKLOG.md or SPECIFICATION.md. Produced during the
`claude/unit-tests-future-ideation` branch discussion (branched off
`claude/digital-twin-oserror-7y00lb`) about extending the test suite onto real rp2 hardware over
mpremote, in addition to the existing mock (`tests/machine.py`) and digital-twin (`digital_twin/`)
backends — not a replacement for either.

Tier tags follow `toolchain/setup_toolchain.py env --tier {flash,bench}`:
- **[USB]** — `flash` tier: real board over USB serial, no network.
- **[USB+WiFi]** — `bench` tier: real board + a real WiFi bridge/AP, genuine internet/NTP reachable.

Each item either extends an existing mock/twin test's assertion onto real silicon, or covers ground
that BACKLOG.md / SPECIFICATION.md Part F / `digital_twin/README.md`'s own "Known gaps" section
already flag as structurally unreachable by simulation.

## A. Real bus/electrical timing (no simulation can produce this)

1. **SCD30 clock-stretch timing** [USB] — real electrical clock stretching under genuine I2C bus
   load. Existing `test_scd30s_own_i2c_bus_uses_a_clock_stretch_timeout_wide_enough_for_it` only
   asserts the *configured* timeout value; this would confirm it's actually wide enough against real
   stretching, not just present.
2. **Hot-unplug/replug I2C recovery** [USB] — physically disconnect/reconnect a sensor and confirm
   the two-tier recovery (task respawn re-probes + reset/soft-reset on real hardware) actually
   works, per SPECIFICATION.md Part F.2's design. Currently "confirmed directly against the code,"
   never against real hardware.
3. **Genuinely wedged I2C bus → watchdog backstop** [USB] — physically force SDA/SCL low (or a
   locked-up sensor) and confirm the real hardware WDT actually resets the board within the 8388ms
   cap, closing the loop on CLAUDE.md's "hardware watchdog is the accepted backstop" policy. The
   digital-twin's CI Run 10 only proves `would_have_triggered_count >= 1` in simulation — never a
   literal reset.
4. **Soft `Timer` callback drop under real scheduler saturation** [USB] — provoke enough concurrent
   real IRQs/timers to exhaust `MICROPY_SCHEDULER_DEPTH=8` and confirm a periodic timer self-heals
   on the next tick, matching Part F.1's documented (but never hardware-tested) drop behavior.
5. **`Timer.init()` `OSError(ENOMEM)` under real alarm-pool exhaustion** [USB] — construct enough
   real Timers to genuinely exhaust the RP2040's hardware alarm pool; the twin's `Timer` is
   asyncio-task-backed and has no real pool limit to hit.
6. **Real WS2812/Neopixel signal timing** [USB] — verify actual PIO-driven bit timing meets
   datasheet tolerances (scope/logic-analyzer or a second device reading the real color output). The
   twin just records writes with zero electrical timing modeled.
7. **SCD30 RDY pin real IRQ edge** [USB] — confirm a real rising edge from real hardware drives the
   same code path the twin's simulated-cadence RDY pin exercises in `test_digital_twin_scd30.py`.
8. **Single-precision float boundary (`2**24`)** [USB] — RP2040 firmware is
   `MICROPY_FLOAT_IMPL_FLOAT` (24-bit mantissa); the Unix port test rig is double precision and
   structurally cannot reproduce this boundary. Targets `config_manager.coerce_numeric()`'s
   int→float path specifically (Part F.1 already flags this as accepted-not-fixed on the assumption
   no real schema field goes near it — worth confirming that assumption on real hardware once, not
   indefinitely).
9. **`time.ticks_ms()` real `2**30` rollover** [USB] — the Unix port's own period is `2**62` and
   structurally can't exercise the real 12.4-day rollover. `test_ticks_rollover.py` already proves
   the shared math correct at *this rig's* boundary; only real hardware (or a very long soak) can
   prove it at RP2040's actual boundary.

## B. Real WiFi / lwIP networking — the single most-flagged gap

10. **Real STA connect/disconnect against a genuine AP** [USB+WiFi] — real `SEEKING→ESTABLISHED`
    timing/RSSI, replacing the twin's instant/no-delay `WLAN.connect()`.
11. **Real STA-fail → hotspot fallback, observed by an actual second client** [USB+WiFi] — a real
    phone/laptop joining the fallback AP and getting a real DHCP lease. The twin (CI run 7) only
    proves the internal state machine plus a same-process synthetic UDP query.
12. **Real NTP round-trip over genuine lwIP/UDP** [USB+WiFi] — this is *the* explicitly flagged gap
    (BACKLOG.md open question #5): real `POLLERR`/`POLLHUP` delivery, real truncation,
    connected-socket source filtering. The twin's `_unix_port_udp_addr_shim.py` only papers over
    Unix-port-only quirks to let the code *execute*; it never verifies the real rp2/lwIP transport is
    correct.
13. **Real DNS resolution via `asy_dns_client.py`'s own resolver** [USB+WiFi] — same rationale as
    #12, over a real upstream DNS server.
14. **Real captive-DNS answering a real external client** [USB+WiFi] — extends CI run 7
    (same-process query) to a genuine second device querying the real hotspot's DNS server.
15. **Real unprivileged `bind(53)`** [USB+WiFi] — confirms `captive_dns.py`'s unconditional
    privileged-port bind genuinely works bare-metal (no privilege concept at all), without the
    `CAP_NET_BIND_SERVICE` workaround the twin's CI needs on Linux.
16. **Real NTP-unreachable timeout under genuine network jitter/loss** [USB+WiFi] — replaces the
    twin's RFC 5737 black-hole IP (an instant, clean "no response" under Unix sockets) with
    real-world latency/partial-loss behavior.
17. **Real end-to-end hotspot session** [USB+WiFi] — a real client joins the AP, gets DHCP, resolves
    via captive DNS, loads the real webserver — the full path, not each piece in isolation.

## C. Real reboot / power / persistence

18. **Real FRAM persistence across an actual power cycle** [USB] — genuinely power-cycle (or
    `machine.reset()`) the board and confirm the real MB85RS64V's dual-copy+CRC contents survive, vs.
    the twin's "second `AsyFramManager` against the same simulated chip" proxy.
19. **Real SCD30 NVM persistence across a real power cycle** [USB] — same idea for the sensor's own
    onboard NVM (measurement interval, ambient pressure, altitude, temp offset, self-cal).
20. **Real `config.json` survives a genuine reboot on real littlefs** [USB] — the ~848KB Pico W
    partition, not a host filesystem; confirms `write_config()` behavior under real flash-wear/timing
    characteristics.
21. **`modules/_boot.py`'s `import sensortask.py` mechanism** [USB] — read-only observation on real
    1.26 hardware to finally resolve BACKLOG.md open question #1, which CLAUDE.md explicitly
    forbids editing blind without this.
22. **Real `SystemService._reboot()` sequencing** [USB] — confirms `storage_pause()`-then-wait
    genuinely completes before the real reset fires, and that WDT isn't starved mid-sequence, on
    real timing.

## D. Real memory / stress soak — explicit BACKLOG owner plan

23. **Real-hardware memory-leak soak test** [USB] — port the Unix-port `gc.mem_free()`
    recovery-peak-trend methodology to run against real firmware under HTTP soak traffic; RP2040's
    real allocator isn't guaranteed to match the Unix port's.
24. **Real concurrent-client-burst stress test** [USB+WiFi] — the segfault this originally chased is
    confirmed compiled out of real rp2 firmware (`MICROPY_PY_SELECT_POSIX_OPTIMISATIONS=0` there), so
    this is standing robustness validation of the burst scenario itself, not chasing a bug.
25. **Real single-core timing headroom under full load** [USB] — sensor reads + webserver + WiFi +
    Neopixel animation all real, at real 133MHz — confirms Part F.3's "don't stall timing-sensitive
    work" principle actually holds on real silicon, not the Unix port host's arbitrary CPU speed.

## E. Real toolchain / flash / boot

26. **`env --tier flash`/`--tier bench` real-hardware verification** [USB / USB+WiFi] — BACKLOG.md
    already flags this as not yet done; USB detection and bench AP creation were only exercised
    against empty `/sys`/no NetworkManager in a cloud sandbox.
27. **Real UF2 flash-and-boot smoke test** [USB] — flash `build_firmware.py`'s real output via
    mpremote/picotool and confirm it boots to a working webserver; CI's `firmware-build-verify` job
    builds but never flashes.
28. **Real BOOTSEL/UF2 re-enumeration** [USB] — confirms `machine.bootloader()` genuinely drops into
    mass-storage mode for a subsequent flash to succeed.

## F. Real sensor accuracy (not just protocol correctness)

29. **BMP3xx real pressure/temperature vs. a known reference** [USB] — the twin's own README
    explicitly flags its calibration block as "not sourced from a real chip"; only real silicon can
    validate the compensation formula against genuine factory trim.
30. **SCD30 real CO2/temp/humidity plausibility** [USB] — sane real-world values from a real sensor,
    not just protocol-correct simulated ones.
31. **SGP40 real VOC-index response to a real stimulus** (e.g. isopropyl vapor) [USB] — confirms the
    ported Sensirion algorithm behaves sensibly against a genuine gas-sensor signal.

## G. Real end-to-end timing

32. **Cold-boot-to-first-response latency** [USB+WiFi] — real WiFi-connect + NTP + sensor-init timing
    budget; meaningless to measure on the Unix port's arbitrary host timing.
33. **`scripts/mpremote_connect.sh` connection-stability baseline** [USB] — a basic sanity check that
    the tooling itself reliably talks to a real board, worth having as its own smoke test before
    layering the above on top.

## Deferred note (not a candidate)

`asy_uart_driver.py` has full unit tests but isn't wired into the `wozi` variant's `build_system()`
at all — no real-hardware UART candidate until some variant actually uses it.

## Mock/twin overlap findings (from the same discussion, for reference)

Six subsystem pairs were scanned for duplicate assertions between the mock and digital-twin test
backends (not real-hardware related, kept here since it was part of the same session):

- BMP3xx: complementary, 1 near-duplicate (same compensation formula, forward vs. inverse).
- SGP40: complementary, 1 near-duplicate (same CRC8 worked example, independently reimplemented —
  deliberate cross-check).
- FRAM: complementary, small low-value pocket of duplicated basic WREN/WRITE/WEL protocol semantics.
- Neopixel/WiFi: essentially no meaningful duplication — different SUTs entirely.
- Webserver: complementary, 2 near-duplicates, both self-documented in-file as deliberate.
- Sensortask: complementary overall, but the largest cluster — 4 near-identical pairs, all "same
  REST endpoint round-trip, once direct, once over real HTTP against the twin" (module-construction
  check, SCD30 PUT, notification PUT, measurements/sensors GET shape).
