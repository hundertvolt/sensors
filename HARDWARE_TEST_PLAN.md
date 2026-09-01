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
- **bench role-reversal adapter** — a distinct bench capability from the fault-injection adapter
  above: instead of the bridge attacking the DUT's *uplink*, the bridge's one WiFi radio temporarily
  *becomes a client of the DUT's own hotspot*, to test the DUT's AP/DHCP/captive-portal/REST-serving
  role from a genuine external client's perspective — untestable in the twin at all. See §11 for the
  full design (verified driver timing, the single-radio sequencing constraint, and ~25 individual
  tests this unlocks).

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

## 11. Deep-dive scenario: full hotspot role-reversal test (bench, single-radio)

A richer, multi-stage bench scenario beyond the flat candidate-list items in §8: the RP2040's own
hotspot/AP mode (its own DHCP, its own captive-portal DNS spoof, full REST accessibility while *it*
is the access point) is untestable in the digital twin — `digital_twin/network.py`'s `WLAN` never
models AP-mode DHCP or a real second radio joining it — and on the mock/twin side only ever gets
exercised from the DUT's own perspective, never from a genuine external client's. On real hardware
it's fully testable, but needs the bench rig's one WiFi radio to temporarily stop being the DUT's
uplink AP and become a *client* of the DUT's own hotspot instead, then flip back. This section is
the design for that, with the concrete driver behavior it depends on verified directly against
`src/asy_wifi_service.py`, `src/asy_webserver_service.py`, and `src/captive_dns.py` — not assumed.

### 11.1 Verified facts this design depends on

- **The hotspot's SSID/password are fully deterministic, no scan/discovery needed.**
  `_configure_hotspot_ap()` (`asy_wifi_service.py`): `self.wlan.config(essid=hostname,
  password="12345678")` — SSID is whatever the `Hostname` config field currently holds (schema
  default `"SensorNode"`, `_VAL_HOST`), password is the literal hardcoded string `"12345678"`. The
  harness can compute both from the DUT's currently-configured `Hostname` without ever scanning for
  the network.
- **DHCP is handled entirely by the integrated CYW43 firmware — no dedicated Python code exists for
  it** (confirmed directly: `asy_wifi_service.py` never touches a DHCP server; `self.wlan.active(True)`
  on `network.AP_IF` is the only setup call). This means DHCP-serving robustness tests below are
  really testing the CYW43 driver/firmware, not `src/` — still a genuine, valid real-hardware-only
  test target, just worth being explicit that a bug found there isn't an `asy_wifi_service.py` bug.
- **The captive portal is DNS-only spoofing, not an HTTP-level redirect** (confirmed directly by
  reading the whole of `src/captive_dns.py`, not assumed from its name): `DNSServer.run()` answers
  *every* on-subnet DNS query with a canned A-record pointing back at the AP's own IP
  (`DNSQuery.response()`), regardless of what hostname was actually queried — including the device's
  own real `Hostname` and a genuine root-domain query (the `_parsed_ok` flag is what distinguishes a
  real root query from truncated/malformed input, both of which otherwise parse to the same empty
  `self.domain`). Off-subnet or malformed source addresses are silently ignored, never answered.
  Malformed/truncated DNS packets get no response at all (`response()` returns `None`). There is
  **no** HTTP-layer captive-portal-detection handling (no `/generate_204`, `/hotspot-detect.html`,
  `/ncsi.txt`-style interception) — the whole mechanism relies on every hostname a client's OS
  resolves eventually landing an HTTP request on the DUT's own webserver at `/`. Whether a real
  phone's OS-level "sign in to network" auto-popup actually fires against this DNS-only spoof is
  itself worth a dedicated **manual** test with a real device (see §11.5) — it's a genuine open
  question this design surfaces, not settled by reading the code alone.
- **`/networking`'s PUT already triggers the reconnect** — `sensortask_wozi.py`:
  `SettingsGroup(conn, ("SSID", "PW", "Country", "Hostname"), post_fct=conn.reconnect_wifi)`. No
  second REST call or reboot is needed to apply new STA credentials; a single successful PUT already
  calls `reconnect_wifi()`.
- **Real timing budget, traced through the code, not measured on hardware yet**: `reconnect_wifi()`
  only sets a flag; `wlan_connect()`'s own loop picks it up within `wifi_refresh_sec` (constructor
  default **5s**); `_handle_reconnect_trigger()` itself sleeps **5s**; `_switch_wlan_mode()` adds
  disconnect→sleep(**2s**)→deinit→sleep(**1s**)→reinit→sleep(**1s**); `_handle_reconnect_trigger()`
  ends with one more sleep(**3s**) settle. **Total: roughly 15–20 seconds** from the PUT succeeding
  to the DUT issuing its first real STA connect attempt. Not a hard real-time race — a scripted
  `nmcli connection up br0-wifi-ap` (typically low single-digit seconds) comfortably fits inside
  that window if fired immediately after the PUT call returns.
- **A missed window degrades gracefully, doesn't strand the board**: `connection_failures` retries
  up to `conn_fail_to_hotspot` (constructor default **5**) STA attempts before falling back to its
  own hotspot again on its own. So even if the bench radio's flip-back is somehow delayed past the
  ~15–20s window, the DUT doesn't get stuck — it re-enters hotspot mode and the whole scenario can
  retry from stage 6 (§11.4) rather than needing a full reset.
- **While a client stays associated to the DUT's hotspot, the DUT's own *idle* reconnect-retry timer
  is suppressed** (`_hotspot_client_connected()`: "if client connected, do not stop hotspot"). Only
  the explicit REST-triggered `reconnect_wifi()` cuts through this — which is exactly what makes
  "connection setting only as the very last step" an enforceable property of this design, not just
  an intention: nothing else in the scenario can accidentally trigger an early reconnect while the
  bench radio is deliberately staying connected through stages 1–5.

### 11.2 Bench hardware constraint: one radio (confirmed)

The bench Rpi4 has a single WiFi radio — no simultaneous "still hosting the bridge AP" +
"also a client of the DUT's hotspot" is possible. The design is therefore a **sequential role
flip**: the one radio's NetworkManager profile switches from `br0-wifi-ap` (AP-hosting) to a client
profile joining the DUT's hotspot for stages 1–5, then back to `br0-wifi-ap` for stage 7 — safe
specifically because of the ~15–20s measured budget in §11.1, not because the flip itself is
instant. If a second radio is ever added to the bench rig, this constraint disappears entirely (see
HARDWARE_TEST_PLAN.md §9's existing "not currently provisioned" note) and the whole scenario
simplifies to "one radio always hosts the bridge, a second radio does stages 1–5 without ever
touching the bridge" — worth remembering as a future simplification, not assumed available now.

### 11.3 The pause mechanism — test-side only, never in `src/`

Real-world timing (RF association retries, DHCP negotiation slop, `nmcli` command latency, a DUT
that needed more than one of its 5 allowed STA attempts) can plausibly exceed the ~15–20s figure
above on a given run. The fix is a **bounded poll-until-condition wait in the test harness**, never
a change to `asy_wifi_service.py`'s own timing — that timing is real product behavior with its own
reasons (SPECIFICATION.md Part F.3's "don't stall timing-sensitive work" principle among them), and
changing it to suit a test would be exactly the "don't edit `src/` only to make a test pass" mistake
CLAUDE.md already warns against elsewhere (see BACKLOG.md's NTP/DNS real-hardware-verification
entry for the same principle applied to the digital twin).

Concretely: a small, reusable harness primitive —

```
wait_until(check_fn, timeout_s, poll_interval_s, description) -> bool
```

— polling `check_fn()` on `poll_interval_s` centers until it returns truthy or `timeout_s` elapses,
then failing with a message naming what was being waited for and how long was allowed (never a bare
`assert` with no context). Suggested default `timeout_s` generous relative to the traced budget —
e.g. 90s, covering real RF/DHCP slop plus headroom for the DUT needing more than one of its 5
allowed STA attempts. Used at two points in the flow below: waiting for the bench radio's own DHCP
lease after associating to the DUT's hotspot (§11.4 stage 2), and waiting for the DUT to become
reachable again over the normal bridge network after the role-flip-back (§11.4 stage 7/8) — this
second use is the concrete answer to "if time is not sufficient... add a pause mechanism to the test
(not the actual code)."

This should become the first entry in a small "bench harness primitives" module, not duplicated
inline per test — consistent with this project's own standing discovery habit (CLAUDE.md's
"whenever a new file is added to `src/`" scan rule, extended here to test-harness code: check for an
existing primitive before writing a new wait/poll loop).

### 11.4 Staged flow (unchanged in shape from the earlier discussion, now with verified specifics)

0. **Precondition** — PUT `/networking {"SSID": ""}` forces the DUT into hotspot mode on demand via
   the same `reconnect_wifi()` post-hook (no need to wait for an organic STA failure).
1. Bench radio flips from `br0-wifi-ap` to a client profile, associates to the DUT's hotspot using
   the deterministic SSID/password from §11.1.
2. Bench radio obtains a real DHCP lease from the DUT's CYW43-integrated DHCP server.
3. Captive-DNS behavior exercised (§11.1's DNS-spoof-only mechanism).
4. Full REST surface reachability check over the hotspot link (reuses §4's shared live-system HTTP
   behaviors against a third client-adapter variant: "bench radio as the DUT's own hotspot client").
5. Fault injection *from the client side*, attacking the DUT's server/AP role — the complement to
   §4's bridge-side fault-injection adapter, which attacks the DUT's *uplink* instead.
6. **Last, mutating step**: PUT `/networking` with the real bench SSID/password/hostname.
7. Bench radio flips back to `br0-wifi-ap` — can start immediately after the PUT call returns, given
   §11.1's timing budget.
8. Poll (via `wait_until`, §11.3) until the DUT is reachable again over the normal bridge network —
   confirms the real STA connect succeeded end to end.

### 11.5 Individual tests

Broken out per stage so each is independently nameable/runnable, not one monolithic scenario test —
roughly 25 candidates:

**Stage 0 — precondition**
1. DUT enters hotspot mode within a bounded window after `SSID=""` is PUT.
2. Hotspot SSID exactly matches the currently-configured `Hostname`.
3. Hotspot password matches the known fixed value (also documents this as a known weak, hardcoded
   credential for whoever reads the test — not something to silently "fix" here, see CLAUDE.md's
   credential-handling hard rule; flag to the project owner separately if this is news to them).

**Stage 1 — association**
4. Bench radio associates to the DUT's hotspot within `wait_until`'s bounded window.

**Stage 2 — DHCP**
5. Bench radio receives a valid lease (IP/netmask/gateway) within a bounded window.
6. The leased IP falls within the AP's own advertised subnet.
7. *(fault injection)* Repeated associate/disassociate + DHCP renew cycles don't wedge or exhaust the
   CYW43 DHCP server — a firmware/driver robustness check, not an `src/` one (see §11.1).

**Stage 3 — captive DNS**
8. A query for an arbitrary hostname resolves to the AP's own IP.
9. A query for the device's real `Hostname` resolves the same way (not special-cased differently).
10. A genuine root-domain query is answered correctly (the `_parsed_ok` root-vs-malformed
    distinction `captive_dns.py`'s own code comments call out).
11. A malformed/truncated DNS packet gets silently dropped — no response, no crash.
12. *(fault injection, needs a raw-socket feasibility check on the bench Rpi4 before committing to
    this one — not confirmed practical yet)* A spoofed off-subnet source address is ignored.
13. *(fault injection)* Flooding the DNS port with malformed packets produces the real
    `_RECV_FAIL_BACKOFF_INITIAL_S`→`_RECV_FAIL_BACKOFF_MAX_S` (0.5s doubling to a 5s cap) backoff
    curve in observed timing/logs, and legitimate queries are served again once the flood stops.

**Stage 4 — REST surface over the hotspot link**
14. Every documented GET endpoint (`/measurements`, `/sensors`, `/networking`, `/system`,
    `/notification`, `/status`, `/`) is reachable and shaped correctly via the hotspot's own IP.
15. A representative PUT on each mutable group round-trips correctly over the hotspot link — reusing
    §4's shared REST-round-trip behaviors — **deliberately excluding** `/networking`'s
    SSID/PW/Country/Hostname fields, reserved for stage 6.
16. Real static-website content (gzip, real title, real `app.js`) serves correctly over the hotspot
    link, the same property `test_digital_twin_real_website_integration.py` already proves for the
    twin, now over real hardware/RF.

**Stage 5 — client-side fault injection against the DUT's server role**
17. Malformed/oversized HTTP requests against the webserver in hotspot mode behave the same as the
    already-covered mock/twin cases, now over a genuine wireless link where real packet loss/
    reordering is possible (not a loopback socket).
18. Rapid associate/disassociate churn from the bench radio doesn't wedge or leak resources in
    `_get_hotspot_stations()`/`_manage_hotspot_stations()`'s station-management path.
19. *(scope-limited note, not a gap to silently paper over)*: a genuine concurrent-multi-client burst
    like §7 Part 1 item 17's bridge-side test isn't reproducible here with only one bench radio —
    document this stage's ceiling explicitly rather than overselling single-client coverage as
    equivalent.

**Stage 6 — the mutating step**
20. An **invalid** SSID/password combination (e.g. a WPA2 password too short) PUT to `/networking`
    *before* the real one — run earlier in the sequence, not literally last — is rejected, and
    **needs verification** whether `SettingsGroup`'s `post_fct` fires only on a successfully-
    validated write or unconditionally on any PUT to those field names; if it's unconditional, this
    test would itself trigger an unwanted early reconnect and needs redesigning before use.
21. The real PUT (SSID/PW/Country/Hostname matching the bench AP) succeeds and its response
    confirms the accepted values.

**Stage 7/8 — role-flip-back and closure**
22. Bench radio's flip back to `br0-wifi-ap` completes (`nmcli` profile activation succeeds).
23. The DUT becomes reachable again over the normal bench bridge network within `wait_until`'s
    bounded window — the concrete exercise of §11.3's pause mechanism.
24. Post-condition: the DUT reports itself STA-connected (not hotspot) via an observable equivalent
    of `_conn_phase` (e.g. `/networking`'s own connection-status field, if it exposes one — needs
    checking) — confirms the transition genuinely completed, not just "happened to become
    reachable" by coincidence.
25. *(manual, real device)* A genuine phone/laptop's OS-level captive-portal auto-detection is
    observed against the DNS-only spoof from §11.1 — an open question this design surfaced, not
    something the automated tests above can answer on their own.

### 11.6 Still open / needs verification before implementation

- Item 12 above (spoofed off-subnet source address) — raw-socket feasibility on the bench Rpi4 not
  yet checked.
- Item 20 above — whether `post_fct=conn.reconnect_wifi` fires on every PUT to those field names or
  only after successful validation; changes whether item 20 is safe to run as designed.
- Item 24 above — whether `/networking`'s GET response actually exposes a connection-phase/mode
  field a test could assert on, or whether that needs a small, deliberate addition to the REST
  response shape (a real `src/` change, not test-only, and therefore its own scoped decision — flag
  to the project owner rather than assuming it's fine to add).
- Item 25 — whether observing a real phone's OS behavior is worth automating in any way (e.g.
  scripted against a spare Android device via `adb`) or is intentionally manual-only; not decided.
