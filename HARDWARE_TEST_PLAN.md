# HARDWARE_TEST_PLAN.md

Temporary planning doc (same lifecycle as the repo's earlier `WIRING_CONTRACT.md`/`WEBSITE_PLAN.md`/
`AUDIT_PLAN.md`: deleted once this effort merges back, with everything permanent it settles migrated
into `SPECIFICATION.md`/`BACKLOG.md`/`CLAUDE.md` first — see README.md's "Further reading" section).

Produced on branch `claude/unit-tests-future-ideation` (branched off
`claude/digital-twin-oserror-7y00lb`) during an ideation/discussion session with the project owner
about where unit testing goes next — **no implementation has happened yet**. This document is the
refined-scope deliverable from that discussion (CLAUDE.md's "Step-session workflow" step (1)); a
future session picking this up should treat it as the starting point for step (2) (clarifying
questions — most already resolved below, but re-check with the project owner before assuming
anything marked "not yet decided" is settled) through step (6).

**Read this whole document before writing any code against it.** It assumes familiarity with
SPECIFICATION.md Part E (testing architecture), Part D (the `src/` promotion checklist), Part F
(MicroPython/RP2040 platform facts), `digital_twin/README.md`, and BACKLOG.md's open question #5
("Real-hardware verification gap for `asy_udp_socket.py`/`captive_dns.py`" — this plan is the
"deciding deliberately with the project owner what a hardware-in-the-loop test tier should look
like" work that entry calls for).

## 1. Goal

Extend the test suite onto real rp2 hardware over `mpremote`, **in addition to** the existing mock
(`tests/machine.py`) and digital-twin (`digital_twin/`) backends — never as a replacement for
either. The project owner's own framing, verbatim from the discussion: consolidate testing so that,
where the same property is checked across multiple backends, it has "multiple call options (e.g.
mock, real, real with special features)" without "implementing the same test in multiple
configurations at multiple places." A second, later-added hard constraint: **running these tests
must not include additional flash cycles beyond, at most, one at the very beginning to prepare the
board.**

## 2. Findings established before any design work started

These are facts checked directly against the repo during this discussion, not assumptions — a
future session should trust them without re-deriving, but should re-verify if significant time has
passed or the relevant code has changed materially.

### 2.1 Generic tests vs. digital twin: no duplicated test logic today

Six files test pure `src/` logic with no hardware fake at all (`test_math_helpers.py`,
`test_crc_checks.py`, `test_config_manager.py`, `test_api_response.py`,
`test_reset_call_site_invariant.py`, `test_ticks_rollover.py`). Two of those six
(`test_reset_call_site_invariant.py`, a static text-scan over `src/*.py`; `test_ticks_rollover.py`,
pure MicroPython interpreter-behavior verification) never execute any `src/` module and so can never
overlap with anything. The other four (`math_helpers`, `crc_checks`, `config_manager`,
`api_response`) do get their real code paths executed as a side effect when the digital twin runs
the full assembled system (confirmed concretely: `asy_bmp3xx_driver.py`/`asy_scd30_driver.py` call
`math_helpers.altitude_baro`/`wet_bulb_temperature`/`dew_point` inside `get_dict_data()`, which
`test_digital_twin_sensortask_integration.py` does call) — but this is **line-coverage overlap
only**, never **assertion overlap**: the twin treats the return as an opaque shape to check, never a
value, so no test logic is actually duplicated.

### 2.2 Mock vs. digital-twin: mostly complementary, one real duplication cluster

Six subsystem pairs were scanned in full (every `test_*` function read, not just names) for real
duplicate assertions vs. complementary coverage:

| Pair | Verdict |
|---|---|
| BMP3xx | complementary; 1 near-duplicate (same compensation formula, forward vs. inverse direction) |
| SGP40 | complementary; 1 near-duplicate (same CRC8 worked example, independently reimplemented — a deliberate cross-check, not accidental) |
| FRAM | complementary (166 mock tests vs. 18 twin tests, two independently-built fake-chip opcode interpreters); small low-value pocket of duplicated basic WREN/WRITE/WEL protocol semantics |
| Neopixel/WiFi | essentially no meaningful duplication — genuinely different SUTs |
| Webserver | complementary; 2 near-duplicates, both already self-documented in their own code comments as deliberate re-tests at a different backend/timeout scale |
| **Sensortask** | complementary overall, but **the one real, concentrated cluster**: 4 near-identical pairs, all "same REST endpoint round-trip, once via a direct call, once over real HTTP against the twin" — module-construction check, SCD30 PUT round-trip, notification PUT round-trip, measurements/sensors GET shape check |

**Conclusion carried into the architecture below**: consolidation effort should target the
REST-round-trip shape specifically (see §4), not force uniformity onto pairs that are already
correctly complementary. Forcing shared bodies onto genuinely backend-specific coverage (mock's
byte-frame assertions, twin's persistence/IRQ/random-walk behavior) would manufacture the
redundancy this effort is trying to remove, not fix it.

### 2.3 The dev-environment tiers already align with the backend model needed here

`toolchain/setup_toolchain.py env --tier {generic,flash,bench}` (SPECIFICATION.md Part B.12) already
defines exactly the tier boundary this plan needs:
- `generic` — Python/Node deps + the Unix-port toolchain build. Everything mock/twin need. No real
  hardware.
- `flash` — `generic` + real USB serial access to a board. No network.
- `bench` — `flash` + a real WiFi bridge/AP on the host (NetworkManager), so a flashed board reaches
  genuine internet/NTP.

This is a strict superset chain (`bench` ⊇ `flash` ⊇ `generic`), and maps directly onto the
mock/twin/flash/bench backend model in §3 below — this section is not a new invention, it's
recognizing that the infrastructure tiering already matches the testing-backend tiering needed.

## 3. The five-backend model

| | **mock** | **twin** | **flash** | **bench** | **manual** |
|---|---|---|---|---|---|
| **Executes on** | MicroPython Unix-port, `tests/machine.py`/`tests/_fram_chip_fake.py` fakes | MicroPython Unix-port, `digital_twin/` fakes (real asyncio object graph) | real RP2040, USB serial (`mpremote`) | real RP2040, USB + real WiFi bridge/AP (bench Rpi4 host) | rides on **flash** or **bench** hardware — not an independent substrate |
| **"Next test" boundary** | fresh interpreter process per `tests/test_*.py` file (free) | fresh process per file, or an explicit reboot within a soak run | `machine.soft_reset()` between isolated-driver checks; live-system mode just keeps running | same as flash, plus bridge-side network state reset | a human physically restores the condition (replug a wire, restore power, remove a stimulus) |
| **Flash cost** | none | none | **one, ever**, at setup | **one, ever**, at setup (same physical board as flash) | at most one *extra* flash — only for a literally blank board's first-ever flash |
| **Fault injection** | synthetic, in-process (`tests/network.py`/`tests/machine.py`'s `raise_on`-style queues) | synthetic but higher-fidelity, same interface shape (`digital_twin/_fault_injection.py`'s `FaultInjector`) | none — no bridge to control | **real**, via the bridge host: AP down/up (`nmcli`), `iptables` drops, credential rotation, client kick | N/A — the human closes the loop instead of a fault-injection call |
| **What only it can prove** | raw bus byte/frame correctness, config-schema boundaries, bus-NAK/CRC error paths | realistic stateful/concurrent/timing/persistence behavior of the whole assembled system, without real silicon | real electrical timing, real WDT reset, real Timer/IRQ/scheduler behavior, real flash/littlefs persistence, real BOOTSEL | real lwIP/WiFi transport, real fault-injected network scenarios, real end-to-end timing under genuine network conditions | anything a script structurally cannot perform: unplug/replug, genuine power loss, a chemical stimulus, a real second device joining a hotspot, a blank board's first flash |
| **Automated?** | yes | yes | yes | yes | **no** — needs its own separate runner; see §6 |

**Hierarchy, not five independent silos:**
- `bench` ⊇ `flash` — same physical board, same one-time flash. Everything `flash` can do, `bench`
  can also do; the reverse isn't true (no bridge on `flash` means no real network, no real fault
  injection).
- `manual` is an **execution mode**, not a tier — it attaches to whichever hardware (`flash` or
  `bench`) a given test needs, and is kept structurally separate specifically so an unattended
  automated pass never silently stalls waiting on a human who isn't there.
- `mock`/`twin` stay Unix-port-only, with no relationship to the real-hardware tiers beyond sharing
  the same `src/` code under test and (see §4) the same shared-behavior-catalog interface shape
  where a behavior applies to more than one backend.

## 4. Architecture: shared behavior catalog + per-backend capability adapters

**Core move**: pull only the *backend-agnostic* claims (round-trips, boundary acceptance/rejection,
"a bus fault degrades cleanly," "a REST field persists end-to-end") into a shared layer of plain
functions, each taking a small, explicit **capability object** rather than a raw driver —
e.g. a `driver_factory()` callable for object-level checks, an `http_client` for REST-level checks,
a `reboot()` callable for persistence checks, a `raise_on(...)`-shaped fault-injection callable for
WiFi-fault-shaped checks. Every backend then supplies just that narrow adapter, not a
reimplementation of the check itself:

- **mock adapter** — constructs the object against `tests/machine.py` fakes, in-process, synchronous.
- **twin adapter** — constructs against `digital_twin/` fakes, or drives via
  `digital_twin/_http_client.py` for HTTP-level checks.
- **flash/bench isolated-driver adapter** — one generic `mpremote run`-backed mechanism ("run this
  snippet against real hardware, capture its printed result") implemented **once**, so individual
  shared-behavior functions never need to know they're talking over serial.
- **flash/bench live-system adapter** — a real HTTP client pointed at the board's reachable address
  (bench: real IP over the bridge network), mirroring `digital_twin/_http_client.py`'s own interface
  closely enough that the sensortask REST-round-trip cluster (§2.2) can run **the same shared test
  body** against twin, and now flash/bench, by swapping only which client object is passed in.
- **bench fault-injection adapter** — the real equivalent of `network.py`'s/`_fault_injection.py`'s
  synthetic `raise_on`/`script_connect_outcomes` surface, backed by real actions on the bridge host:
  bring the AP down/up (`nmcli connection down/up br0-wifi-ap`), block UDP 53/123 upstream with a
  scoped, temporary `iptables` rule, rotate AP credentials to force a real auth failure, kick an
  associated client. All of this lives entirely on the bridge host side — it never touches the DUT's
  flash, so it doesn't violate the no-extra-flash-cycles constraint. `flash` tier has **no** adapter
  for this capability at all, correctly — there's no bridge to control there, and that absence
  should show up as an explicit "N/A, no bridge" row in the manifest (§5), not a silent gap.

**What stays out of the shared layer, deliberately** (per §2.2's evidence): mock's raw byte/frame
assertions, twin's persistence/IRQ/random-walk chip behavior, and every real-hardware-only
electrical/timing check in §7 below. These are correctly backend-specific and must not be
force-fit into a common shape.

## 5. Anti-drift mechanism: one manifest, not memory

A single checked-in table — behavior name → which backends apply, with an explicit stated reason for
any "N/A" — is what actually prevents this architecture from drifting apart over time, as opposed to
trusting whoever adds a new test to remember every backend it should also cover. Concretely:

- Location/format not yet decided — candidates: a plain Python module (`tests/_shared/
  backend_matrix.py`, a dict literal, importable by both the shared-behavior module and a
  consistency-check test) or a small JSON/TOML manifest read by both. Prefer whichever format the
  MicroPython Unix-port interpreter can also read directly if the consistency check itself should
  run as a `tests/test_*.py` file (matching this project's existing testing architecture, per
  SPECIFICATION.md Part E) rather than a separate CPython-only script.
- A consistency check (same spirit as the existing `tests/test_reset_call_site_invariant.py`'s
  static-scan pattern) walks the shared-behavior module against the manifest and fails if: a shared
  behavior has no manifest row, a manifest row names a backend with no adapter actually registered
  for it, or an adapter exists with no manifest row acknowledging it.
- This is the mechanism that answers the project owner's original ask directly: "ensure they will
  not drift apart, stay synced and complete" is not a process discipline to maintain by hand, it's
  something that fails CI when violated.

**Not yet decided — flag to the project owner or resolve in step (2) of the next session**: exact
manifest schema; whether the consistency check also needs to verify each adapter's *interface
shape* (e.g. via a `Protocol`, consistent with BACKLOG.md's own noted future typing-strategy work
for test-wrapper classes) or only its *presence*.

## 6. Real-hardware harness: honoring "no extra flash cycles"

### 6.1 One-time provisioning

The one allowed flash puts the **real, unmodified production UF2** on the board — the exact
artifact `scripts/build_firmware.py` produces for a real deployed unit, never a special
test-instrumented build. This matters for validity: real-hardware tests must exercise the actual
shipped firmware, not a variant that could behave differently from what ships. First-ever flash of a
genuinely blank board needs a human (hold BOOTSEL while plugging in USB) — this is the one
`[MANUAL]` step in an otherwise fully-automated real-hardware pass; see §7's Part 2 item D.8. Every
subsequent flash-equivalent (e.g. re-provisioning after a firmware update) can be automated via
`machine.bootloader()` triggered remotely over `mpremote` from an already-running board, then
`picotool` — but this still counts as "a flash cycle" and should not happen as part of routine test
runs, only as a deliberate re-provisioning step.

### 6.2 Two execution modes after provisioning

- **Live-system mode**: the board just runs, auto-booted, normally (via `boot_entry/wozi_boot.py` /
  `sensortask_wozi.main()`, same as a real deployed unit). Tests interact only through its real
  external interfaces: HTTP (via the live-system adapter, §4), real WiFi/NTP/DNS (bench only), real
  serial log tailing. **No `mpremote run` script injection in this mode at all.** This is where
  almost all of §7 Part 1's automated items live, plus several manual items (real sensor stimulus
  observed via `/measurements`, real hotspot join observed by a human).
- **Isolated-driver mode**: for object-level checks that want direct control rather than going
  through the full running system (clock-stretch timing, RDY-pin edge, Timer/scheduler-saturation,
  boot-import check, ...). `mpremote run <script>` interrupts the auto-started system (a soft
  interrupt into the raw REPL, not a flash), executes a short script that imports the real frozen
  driver modules directly (they're already resident in flash and importable by any script `mpremote`
  runs) and exercises them, then the harness issues `machine.soft_reset()` to restore the normal
  auto-booted state before the next test. **Soft resets are free and unlimited** — the constraint is
  specifically about flashing, not resetting.

### 6.3 Orchestrator shape

Mirrors what already exists for the digital twin (`digital_twin/run_wozi_integration.py` /
`scripts/run_digital_twin_ci.sh`, see `digital_twin/README.md`'s "Automated CI suite" section for
the model to follow): one real script per tier (`scripts/run_flash_hardware_suite.sh` /
`scripts/run_bench_hardware_suite.sh`, names not yet settled) drives live-system checks first, then
the isolated-driver batch, then a final soft reset — never touching flash again after the initial
provisioning step covered in §6.1. Not yet designed: the concrete script(s), their flag vocabulary
(should probably mirror `digital_twin/launch.py`'s/`run_wozi_integration.py`'s existing
`--fault DEVICE:OP[:TIMES]` vocabulary for the bench fault-injection adapter, for consistency with
what a project owner already knows from the twin), and how results get reported/aggregated across a
run (does it reuse `tests/microtest.py`'s PASS/FAIL convention somehow, given these are
`mpremote`-driven rather than direct Unix-port-interpreter invocations?).

## 7. Manual-test runner: design note (from the discussion, not yet implemented)

Kept structurally separate from the automated flash/bench runner (§6.3) — a different script/entry
point, never silently mixed into an unattended pass:

- **Print the instruction before the window that depends on it, not after.** Each physical step gets
  an explicit, printed console instruction stated in advance — what to do, which pin/connector,
  which device — not just a bare countdown.
- **Timing must be human-executable on a breadboard test device**, not a value carried over from an
  automated/simulated test: tens of seconds, not milliseconds. Pick the actual number per test from
  what's physically involved (unplugging two jumper wires vs. locating a chemical stimulus vs.
  flipping a bench power switch), not one fixed constant applied everywhere.
- **Wait for explicit human confirmation before proceeding** where the console can (e.g. "press
  Enter once disconnected"), reserving a bare countdown for the genuine power-cycle cases where the
  console itself goes away mid-step.
- **State the expected observable outcome up front**, so a human running the test knows what
  "passed" should look like even before the script's own final verdict prints — useful for tests
  ending in a human visual/instrument check (Neopixel timing, sensor-accuracy-vs-reference checks)
  rather than a script-only assertion.

Not yet decided: concrete script name/entry point; whether it reuses the same shared-behavior
functions/adapters as the automated runner where a check applies to both modes (the design intent
is yes — e.g. the FRAM power-loss test should reuse the same "read back FRAM contents" shared check,
just wrapped in a human power-cycle step — but this hasn't been built or verified).

## 8. Candidate test inventory

The full, itemized 33-candidate list (14 flash-automated, 8 bench-automated, 1 either-tier tooling
item, 9 flash-manual, 2 bench-manual), organized by category (bus/electrical timing, WiFi/lwIP
networking, reboot/persistence, memory/stress soak, toolchain/flash/boot, sensor accuracy,
end-to-end timing) with rationale per item, lives in **`tmp_hardware_test_candidates.md`** at the
repo root. That file is itself temporary — the project owner's stated intent is to delete it once
the tests it lists are implemented and verified running. **Whoever deletes it must first migrate
anything still permanently true into SPECIFICATION.md** (most likely a new Part, or an extension of
Part E, given testing-architecture content already lives there) **and update this document's
references accordingly** — don't just delete it once the items are done; fold forward first, per
this repo's standing "resolved items move into a permanent doc, not silently dropped" convention
(see CLAUDE.md's "Working agreements").

## 9. What's genuinely unsettled — do not assume these are decided

- **Manifest file format/location** (§5) — sketched, not chosen.
- **Adapter interface signatures** (§4) — described narratively (`driver_factory()`, `http_client`,
  `reboot()`, `raise_on(...)`), never written as actual code/types.
- **Orchestrator script names, flag vocabulary, result-reporting convention** (§6.3) — not designed.
- **Manual-runner entry point and code reuse with the automated runner** (§7) — intent stated, not
  built.
- **Two real-hardware capabilities flagged as "not currently provisioned"** during the discussion,
  each with a candidate-list item depending on it:
  - A programmable GPIO fault-injection harness on the bench rig, which would upgrade the
    "genuinely wedged I2C bus → watchdog backstop" test (candidate list Part 2, item A.2) from
    `[MANUAL]` to `[AUTO]`.
  - A dedicated second WiFi test client on the bench rig (the bench rig's one WiFi adapter already
    hosts the AP), which would upgrade "real end-to-end hotspot session" (candidate list Part 2,
    item B.5) from `[MANUAL]` to `[AUTO]`.
  Neither is assumed to be worth building — flag to the project owner as an explicit choice, not a
  default plan.
- **Result-reporting/coverage story for real-hardware runs** — SPECIFICATION.md Part E.5's coverage
  pipeline is Unix-port-`sys.settrace`-specific; whether/how real-hardware runs report anything
  analogous (or whether that's simply out of scope for this backend) hasn't been discussed.

## 10. Suggested next step for whoever picks this up

Per CLAUDE.md's "Step-session workflow": this document is step (1)'s deliverable. Step (2)
(clarifying questions) has already had a substantial real discussion behind it (captured throughout
this document), but the open items in §9 above are genuine step-(2)-shaped questions that still need
the project owner's input before step (3) (writing tests first, TDD) can start in earnest. Don't
skip straight to implementation without resolving at least the adapter interface shapes and manifest
format — those are foundational enough that guessing wrong means rework across every backend, not
just one file.
