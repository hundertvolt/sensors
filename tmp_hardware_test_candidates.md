# Real-hardware (mpremote) test candidates — working list

Scratch/temp file, not yet wired into BACKLOG.md or SPECIFICATION.md. Produced during the
`claude/unit-tests-future-ideation` branch discussion (branched off
`claude/digital-twin-oserror-7y00lb`) about extending the test suite onto real rp2 hardware over
mpremote, in addition to the existing mock (`tests/machine.py`) and digital-twin (`digital_twin/`)
backends — not a replacement for either. To be deleted once the tests it lists are implemented **and
verified running against real hardware** (see "Implementation status" below — implemented is not
the same as verified; no board/bench rig was attached to the session that wrote the implementation).

## Implementation status (update — a later session on this branch)

Every `[AUTO]` item below (Part 1) now has real, committed code in `tests_hardware/flash/` or
`tests_hardware/bench/`; every `[MANUAL]` item (Part 2) has real code in `tests_hardware/manual/`.
**Real-hardware execution is standing practice** on the bench Pi4, both tiers running clean end to
end — see `tests_hardware/README.md` for current status, how to run it, and the mechanisms still
flagged as unverified. Two deviations from this list worth knowing before reading further (a third,
originally listed here, was a mistake this session made and then corrected — item 4 IS implemented
as originally framed: `src/asy_scd30_driver.py` does wire a real GPIO IRQ pin plus a staged
self-healing fallback, an earlier pass here wrongly claimed otherwise from an incomplete grep, and
`test_scd30_rdy_pin_real_irq_edge` is a real test now, not a skip — see
`tests_hardware/README.md`'s own corrected section for the full account):
- **Items 15 and 16** — retagged from `[USB]` to `[USB+WiFi]` and moved into `tests_hardware/bench/`:
  both need real REST/HTTP traffic per their own descriptions, which flash tier (no network) can't
  provide. See `tests_hardware/bench/test_end_to_end_timing.py`/`test_memory_stress_bench.py`'s own
  docstrings.
- **Items 10/11** (real captive-DNS/unprivileged bind) — implemented as part of
  `HARDWARE_TEST_PLAN.md` §11's role-reversal scenario instead of standalone, per this file's own
  pre-existing cross-reference in section B below.

**Beyond this list entirely**: a later audit found this candidate list, despite covering every
numbered item, still left real gaps against what a full real-hardware mirror of the mock/twin test
suites needs — BMP3xx/SGP40 standalone plausibility, the VOC algorithm itself, FRAM
backup/error-storage, website-over-the-normal-network, top-level multi-sensor REST value sanity,
bottom-level hardware-function checks (not just readings), and real-hardware counterparts of
mock-driven integration tests (`tests/test_setter_microdot_integration.py`'s REST config-push
coverage). Ten more tests closed these (see `tests_hardware/README.md`'s "Third pass" section for
the full account) — this list was never updated item-by-item for them since they were never numbered
candidates here to begin with.

## Tags

**Tier** (follows `toolchain/setup_toolchain.py env --tier {flash,bench}`):
- **[USB]** — `flash` tier: real board over USB serial, no network.
- **[USB+WiFi]** — `bench` tier: real board + a real WiFi bridge/AP, genuine internet/NTP reachable.

**Execution mode** — kept as a hard separation, not just a label, per the project owner's direction:
a test that needs a human to physically act (unplug a wire, power-cycle the board, apply a chemical
stimulus, hold a second device up to a hotspot) is a fundamentally different kind of test artifact
than one mpremote can run unattended, and the two must not be mixed into one runner or one CI-style
pass.
- **[AUTO]** — fully scriptable over mpremote/the bench rig; no human action once the board/bench
  is wired up.
- **[MANUAL]** — requires a human to physically do something mid-test. See "Manual-test-runner
  conventions" below for the shape these must take.

## Manual-test-runner conventions (design note, not yet implemented)

Whatever eventually runs the `[MANUAL]` tests below must be structurally distinct from the
`[AUTO]` real-hardware runner (separate script/entry point, separate invocation — never silently
mixed into an unattended pass that could stall waiting on a human who isn't there):

- **Print the instruction before the window that depends on it, not after.** Each step a human must
  perform gets an explicit, printed console instruction stated in advance — what to physically do,
  which pin/connector, which device — not just a bare countdown.
- **Timing must be human-executable on a breadboard test device**, not a value carried over from an
  automated/simulated test. Concretely: tens of seconds, not milliseconds — e.g. "you have 20
  seconds to disconnect the SCD30's SDA/SCL leads now," not a 200ms window nothing but a relay could
  hit. Pick the actual number per test from what's physically involved (unplugging two jumper
  wires vs. locating a chemical stimulus vs. flipping a bench power switch), not one fixed constant
  applied everywhere.
- **Wait for explicit human confirmation before proceeding**, where the test can (e.g. "press Enter
  once disconnected") rather than only a blind timed sleep — use a countdown *and* a confirmation
  prompt together where the runner is interactive, reserving a bare countdown for the genuine
  power-cycle cases where the console itself goes away mid-step.
- **State the expected observable outcome up front**, so a human running the test knows what
  "passed" should look like even before the script's own final verdict prints (useful for the ones
  that end in a human visual/instrument check, like the Neopixel timing or the sensor-accuracy
  tests, rather than a script-only assertion).

---

# Part 1 — Automated (`[AUTO]`)

## A. Real bus/electrical timing (no simulation can produce this)

1. **SCD30 clock-stretch timing** [USB][AUTO] — real electrical clock stretching under genuine I2C
   bus load. Existing `test_scd30s_own_i2c_bus_uses_a_clock_stretch_timeout_wide_enough_for_it` only
   asserts the *configured* timeout value; this would confirm it's actually wide enough against real
   stretching, not just present.
2. **Soft `Timer` callback drop under real scheduler saturation** [USB][AUTO] — provoke enough
   concurrent real IRQs/timers to exhaust `MICROPY_SCHEDULER_DEPTH=8` and confirm a periodic timer
   self-heals on the next tick, matching SPECIFICATION.md Part F.1's documented (but never
   hardware-tested) drop behavior.
3. **`Timer.init()` `OSError(ENOMEM)` under real alarm-pool exhaustion** [USB][AUTO] — construct
   enough real Timers to genuinely exhaust the RP2040's hardware alarm pool; the twin's `Timer` is
   asyncio-task-backed and has no real pool limit to hit.
4. **SCD30 RDY pin real IRQ edge** [USB][AUTO] — confirm a real rising edge from real hardware
   drives the same code path the twin's simulated-cadence RDY pin exercises in
   `test_digital_twin_scd30.py`; observable purely by polling the pin/driver state over mpremote, no
   human action needed.
5. **Single-precision float boundary (`2**24`)** [USB][AUTO] — RP2040 firmware is
   `MICROPY_FLOAT_IMPL_FLOAT` (24-bit mantissa); the Unix port test rig is double precision and
   structurally cannot reproduce this boundary. Targets `config_manager.coerce_numeric()`'s
   int→float path specifically.
6. **`time.ticks_ms()` real `2**30` rollover** [USB][AUTO] — the Unix port's own period is `2**62`
   and structurally can't exercise the real 12.4-day rollover. Long-duration (real ~12.4-day soak),
   but needs no human interaction once started — `test_ticks_rollover.py` already proves the shared
   math correct at *this rig's* boundary; only real hardware (or this long a wait) can prove it at
   RP2040's actual boundary.

## B. Real WiFi / lwIP networking

**See `HARDWARE_TEST_PLAN.md` §11 for a much deeper, staged design of the DUT's own hotspot/AP role**
(real DHCP, real captive-DNS, full REST accessibility, fault injection, and a bench-radio role-flip
to push real STA credentials as the very last step) — that section supersedes the informal framing
of item 10 below and Part 2 items B.4/B.5 with a verified, code-grounded design and ~25 individual
tests. Kept here as the original flat-list entries; don't implement them independently of §11's
design once that work starts.

7. **Real STA connect/disconnect against a genuine AP** [USB+WiFi][AUTO] — real
   `SEEKING→ESTABLISHED` timing/RSSI, replacing the twin's instant/no-delay `WLAN.connect()`; the
   bench AP is already real infrastructure, no human involved per run.
8. **Real NTP round-trip over genuine lwIP/UDP** [USB+WiFi][AUTO] — the single most explicitly
   flagged gap (BACKLOG.md open question #5): real `POLLERR`/`POLLHUP` delivery, real truncation,
   connected-socket source filtering. The twin's `_unix_port_udp_addr_shim.py` only papers over
   Unix-port-only quirks to let the code *execute*; it never verifies the real rp2/lwIP transport is
   correct.
9. **Real DNS resolution via `asy_dns_client.py`'s own resolver** [USB+WiFi][AUTO] — same rationale
   as #8, over a real upstream DNS server.
10. **Real captive-DNS answering a real external client** [USB+WiFi][AUTO] — the bench Rpi4 itself
    (already the bridge host) can run a scripted raw UDP DNS query against the device's hotspot,
    extending CI run 7's same-process query to a genuinely separate real host with no human
    involved. (A literal phone/laptop client is a stronger, but manual, variant — see Part 2.)
11. **Real unprivileged `bind(53)`** [USB+WiFi][AUTO] — confirms `captive_dns.py`'s unconditional
    privileged-port bind genuinely works bare-metal (no privilege concept at all), without the
    `CAP_NET_BIND_SERVICE` workaround the twin's CI needs on Linux.
12. **Real NTP-unreachable timeout under genuine network jitter/loss** [USB+WiFi][AUTO] — scripted
    on the bench Rpi4 bridge host (e.g. a temporary `iptables` drop rule), no physical action needed.

## C. Real reboot / persistence (soft-reset path only — see Part 2 for genuine power loss)

13. **Real `config.json` survives a soft reset** [USB][AUTO] — `machine.reset()` triggered over
    mpremote, confirms `write_config()`'s on-disk state on real littlefs survives a clean reboot.
    Deliberately narrower than genuine power loss — see Part 2 item 6 for that case.
14. **`modules/_boot.py`'s `import sensortask.py` mechanism** [USB][AUTO] — read-only observation on
    real 1.26 hardware to finally resolve BACKLOG.md open question #1, which CLAUDE.md explicitly
    forbids editing blind without this.
15. **Real `SystemService._reboot()` sequencing** [USB][AUTO] — confirms `storage_pause()`-then-wait
    genuinely completes before the real reset fires, and that WDT isn't starved mid-sequence, on
    real timing; triggered via a REST call, observed via mpremote logs.

## D. Real memory / stress soak — explicit BACKLOG owner plan

16. **Real-hardware memory-leak soak test** [USB][AUTO] — port the Unix-port `gc.mem_free()`
    recovery-peak-trend methodology to run against real firmware under HTTP soak traffic; RP2040's
    real allocator isn't guaranteed to match the Unix port's.
17. **Real concurrent-client-burst stress test** [USB+WiFi][AUTO] — scripted clients from the bench
    host; the segfault this originally chased is confirmed compiled out of real rp2 firmware
    (`MICROPY_PY_SELECT_POSIX_OPTIMISATIONS=0` there), so this is standing robustness validation of
    the burst scenario itself, not chasing a bug.
18. **Real single-core timing headroom under full load** [USB][AUTO] — sensor reads + webserver +
    WiFi + Neopixel animation all real, at real 133MHz — confirms Part F.3's "don't stall
    timing-sensitive work" principle actually holds on real silicon.

## E. Real toolchain / flash / boot (recurring runs, after one-time physical setup)

19. **`env --tier flash`/`--tier bench` recurring verification** [USB / USB+WiFi][AUTO] — BACKLOG.md
    already flags initial physical setup (board/WiFi-adapter attachment) as not yet done once; after
    that one-time attach, `toolchain/setup_toolchain.py env` re-runs are themselves scripted/
    idempotent.
20. **Real UF2 flash-and-boot smoke test, board already running firmware** [USB][AUTO] —
    `machine.bootloader()` can be triggered remotely over mpremote to drop an already-flashed board
    into BOOTSEL mode, then picotool flashes automatically; only the *first-ever* flash of a blank
    board needs a human (see Part 2).

## F. Real sensor accuracy (plausibility only — see Part 2 for reference-calibrated checks)

21. **SCD30 real CO2/temp/humidity plausibility** [USB][AUTO] — sane real-world value bounds (e.g.
    CO2 400–2000ppm, indoor temp/humidity ranges) from a real sensor, checked as sanity bounds, not
    an exact reference — no human needed. Exact-reference calibration is Part 2 item 8's job.

## G. Real end-to-end timing

22. **Cold-boot-to-first-response latency** [USB+WiFi][AUTO] — real WiFi-connect + NTP +
    sensor-init timing budget; boot itself can be triggered via `machine.reset()`, no human action.
23. **`scripts/mpremote_connect.sh` connection-stability baseline** [USB][AUTO] — a basic sanity
    check that the tooling itself reliably talks to a real board, worth having as its own smoke test
    before layering the above on top.

---

# Part 2 — Manual-interaction (`[MANUAL]`)

Needs its own runner shape per the "Manual-test-runner conventions" above: printed step-by-step
instructions, human-feasible timing windows, confirmation prompts where the console survives the
step.

## A. Real bus/electrical timing

1. **Hot-unplug/replug I2C recovery** [USB][MANUAL] — instruct the human to physically disconnect
   then reconnect a sensor's I2C leads, with a breadboard-realistic window (tens of seconds) for
   each half; confirms the two-tier recovery (task respawn re-probes + reset/soft-reset) from
   SPECIFICATION.md Part F.2 actually works, not just "confirmed against the code."
2. **Genuinely wedged I2C bus → watchdog backstop** [USB][MANUAL] — instruct the human to physically
   hold SDA (or SCL) low for a stated window, then confirm the real hardware WDT actually resets the
   board within the 8388ms cap once released enough for the reset to be observed, closing the loop
   on CLAUDE.md's "hardware watchdog is the accepted backstop" policy — the digital twin's CI Run 10
   only proves this in simulation. (Could become `[AUTO]` if the bench rig ever gains a programmable
   GPIO fault-injection harness; not currently provisioned.)
3. **Real WS2812/Neopixel signal timing** [USB][MANUAL] — instruct the human to attach a
   scope/logic analyzer (or, at minimum, visually confirm color/animation correctness) since the
   twin only records writes with zero electrical timing modeled; state the expected color/animation
   sequence up front so a human knows what "correct" looks like before the script's own verdict.

## B. Real WiFi / lwIP networking

4. **Real STA-fail → hotspot fallback, observed by an actual second client** [USB+WiFi][MANUAL] —
   instruct the human to join the fallback AP with a real phone/laptop within a stated window and
   confirm a real DHCP lease is obtained; stronger evidence than Part 1 item 7's own-process check.
5. **Real end-to-end hotspot session (real client)** [USB+WiFi][MANUAL] — instruct the human to join
   the AP, then load the device's webserver in a real browser; the full real path from a genuine
   client's perspective. (Could become `[AUTO]` with a dedicated second WiFi test client provisioned
   on the bench rig; not currently available — the bench rig's one WiFi adapter already hosts the
   AP.)

## C. Real reboot / persistence — genuine power loss (distinct from Part 1's soft-reset tests)

6. **Real FRAM persistence across an actual power cycle** [USB][MANUAL] — instruct the human to
   physically cut power to the board (not `machine.reset()`) after a stated write completes, wait a
   stated interval, then restore power; confirms the real MB85RS64V's dual-copy+CRC contents survive
   genuine power loss, not just the twin's "second `AsyFramManager` against the same simulated chip"
   proxy or Part 1's soft-reset variant.
7. **Real SCD30 NVM persistence across a real power cycle** [USB][MANUAL] — same idea for the
   sensor's own onboard NVM (measurement interval, ambient pressure, altitude, temp offset,
   self-cal).
7b. **Genuine power-loss mid-write** [USB][MANUAL] — instruct the human to cut power at a stated
    moment *during* an active `config.json`/FRAM write (not after it completes), testing real
    torn-write behavior on real flash — ground Part 1's soft-reset test and the twin's simulation
    can't reach at all, since neither can interrupt a write mid-flight the way a genuine power loss
    can.

## D. Real toolchain / flash / boot — first-time-only

8. **First-ever UF2 flash of a blank board** [USB][MANUAL] — instruct the human to hold BOOTSEL
   while plugging in USB (no already-running firmware to trigger `machine.bootloader()` from);
   confirms the board re-enumerates as mass storage and accepts the real `build_firmware.py` UF2.
   Every subsequent flash of that same board is Part 1 item 20's `[AUTO]` path.

## E. Real sensor accuracy — reference-calibrated

9. **BMP3xx real pressure/temperature vs. a known reference** [USB][MANUAL] — instruct the human to
   supply a reference reading (a calibrated barometer, or a known-altitude/known-pressure location)
   and enter it for comparison; the twin's own README explicitly flags its calibration block as "not
   sourced from a real chip," so this is the only way to validate the compensation formula against
   genuine factory trim.
10. **SGP40 real VOC-index response to a real stimulus** [USB][MANUAL] — instruct the human to apply
    a stated chemical stimulus (e.g. an isopropyl-alcohol swab held near the sensor) for a stated
    window, then remove it, and confirm the VOC index rises then decays as expected — confirms the
    ported Sensirion algorithm behaves sensibly against a genuine gas-sensor signal, something no
    simulation can produce.

## Deferred note (not a candidate)

`asy_uart_driver.py` has full unit tests but isn't wired into the `wozi` variant's `build_system()`
at all — no real-hardware UART candidate until some variant actually uses it.

---

# Mock/twin overlap findings (from the same discussion, for reference)

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
