# WIFI_RECONNECT_INVESTIGATION.md

## RESOLVED (mostly) - findings from the session that ran this plan

**C1 (§2's hidden-cause candidate) is confirmed, decisively, as the dominant cause of the
hard_reset()-triggered flakiness.** Ran this doc's own §6 Step 3 A/B test exactly as designed:
10 control trials (plain `hard_reset()`, no AP-side intervention) vs. 10 treatment trials
(`bench.kick_all_stations()` immediately before each `hard_reset()`). **Result: 10/10 control
trials fell back to hotspot mode; 10/10 treatment trials connected cleanly.** About as clean a
signal as a real-hardware A/B test produces. Fixed: added `BenchBridge.kick_all_stations()`
(wrapping the already-existing `kick_client()`/`bench_associated_station_macs()` primitives this
doc's §2 already pointed at) and wired it into every `hard_reset()` call site that expects a real
STA reconnect afterward - the `dut_ip` fixture (both attempts), `joined_hotspot`'s recovery
fallback, and `test_real_sta_connect_reaches_established_after_a_hard_reset` (now also asserts a
real connection, not just any WiFi-related log line). Step 0's answer: only `wpa_supplicant` (via
NetworkManager's D-Bus control) runs on this bench host - no separate `hostapd` process.

**A second, distinct, real mechanism was found while confirming C1 at scale (§6 Step 6)** -
applying `kick_all_stations()` to the `ap_down()`/`ap_up()`-based outage/flap tests in
`test_network_resilience.py` did NOT fix them the same way, and direct investigation (prompted by
the project owner's own prior field observation: "the WiFi module rather tries to resolve
connectivity internally... isconnected stays True for long") found why: **the CYW43
firmware/lwIP stack can silently mask a real link disruption from `wlan.isconnected()`/
`wlan.status()` entirely.** Confirmed directly on real hardware: `iw station dump` showed the DUT
continuously "associated: yes" with a multi-hundred-second connected-time spanning an entire
`ap_down()`/`ap_up()` outage, while a real `arping` probe got zero responses and the webserver was
genuinely unreachable. Confirmed as a well-documented, long-standing (still open since MicroPython
v1.19.1, October 2022), *not* project-specific upstream characteristic via web research:
`micropython/micropython#9455` ("network becomes inaccessible when not used for some time" -
official SDK docs cited there: "both the low-level cyw43_driver and the lwIP stack require
periodic servicing"), `#9505` ("IPv4 address can persist well after wifi AP connection is lost"),
`#18797` (`socket.getaddrinfo()` blocking indefinitely under the same condition), and
[Alan Edwardes' "Raspberry Pi Pico W WiFi Resiliency"](https://alanedwardes.com/blog/posts/raspberry-pi-pico-w-wifi-resiliency/)
(independent field account, recommends an explicit connection timeout + `wlan.deinit()` before
reconnecting, since `isconnected()`/`status()` alone can't be trusted). One of the known
mitigations (disabling power-save via `wlan.config(pm=0xa11140)`) is **already** applied by
`_trigger_sta_connect()` - this project already does part of what the community recommends.

`src/asy_wifi_service.py`'s own `_wlan_isconnected_or_false()` is a bare pass-through to
`wlan.isconnected()` with no independent reachability check anywhere in that module - meaning
`_on_sta_disconnected()`'s retry logic structurally cannot fire if the firmware never reports the
disconnect. **Not fixed in `src/` - flagged as a real, disclosed architectural question for the
project owner** (whether to add an independent reachability check, e.g. periodic ping/HTTP
self-check, beyond trusting `isconnected()` alone), per this doc's own standing guardrail (§8: no
`src/` change without explicit sign-off). Mitigated at the test-harness level instead, matching
this project's own already-established `joined_hotspot` pattern: `test_real_wifi_outage_and_
recovery_while_in_normal_sta_mode`/`test_real_wifi_flaps_repeatedly_without_wedging_the_system` now
recover via a real `hard_reset()` (the one thing confirmed to reliably clear this) if the graceful
wait times out, but still re-raise afterward so the real limitation stays visible as a test
failure rather than being silently papered over - confirmed working as designed on real hardware
(the outage test failed loudly on one run, its own recovery fallback brought the board back
cleanly, and the very next test then passed normally).

**Not yet exercised**: §6 Steps 4/5 (backend `journalctl` log capture, the debug-verbosity C3
A/B test) - superseded in priority by the clean C1 confirmation and the CYW43-masking finding
above, which together account for everything observed. Worth revisiting only if a *new*,
unexplained WiFi symptom shows up later.

---

**Prepared by a cloud session, for the session resuming real-hardware work on the bench Pi4.**
Temporary planning doc, same lifecycle as `HARDWARE_TEST_PLAN.md`/`REAL_HARDWARE_HANDOFF.md`/
`REAL_HARDWARE_RUN_LOG.md` (see README.md's "Further reading"): fold anything permanently true into
`tests_hardware/README.md`/`SPECIFICATION.md`/`BACKLOG.md` and delete this once the WiFi
reconnection question below is actually resolved (or deliberately closed as "accepted, not
worth chasing further" by the project owner) — don't just delete it once a fix lands, migrate
first, same standing convention every other temp doc here follows.

This doc does not repeat `REAL_HARDWARE_RUN_LOG.md`'s "Next session should start here" list — start
there for the `dut_ip` fixture re-verification (still the literal first thing to do, see Step 0
below). This doc is additional prep specifically for **Phase 4** of that list ("further WiFi
reconnection investigation, if the project owner wants to keep chasing it") — the project owner does
want to keep chasing it, and asked for a deep-research pass plus an ordered test plan before the
next session picks it back up.

## 0. What this is responding to

The bench session's own WiFi investigation (chronology: `tests_hardware/README.md`'s "First real
run" list, then `REAL_HARDWARE_RUN_LOG.md`'s Phase 2 section) was thorough and methodical, but its
evidence-gathering stayed on two axes only: **the DUT/RP2040/cyw43-driver side** (real MicroPython C
source reads, `iw station dump` polling, a DHCP-port `tcpdump`) and **published upstream issues
about the cyw43 chip/driver itself**. It never looked at **the AP side's own backend behavior** —
which process NetworkManager is actually running for `br0-wifi-ap` (`hostapd` vs. its own internal
`wpa_supplicant` AP mode), that backend's own station-table/timeout semantics, or its own logs
during a failing cycle — and never used the bench harness's own existing tools
(`bench_control.BenchBridge.kick_client()`/`bench_associated_station_macs()`) to actively
*intervene* in AP-side state as a diagnostic, only to passively observe it. That's the gap this doc
targets first, because the existing evidence fits it unusually well (see §2).

Everything below assumes you've already read `tests_hardware/README.md`'s "Known assumptions and
open findings" WiFi bullet and `REAL_HARDWARE_RUN_LOG.md`'s Phase 2 section in full — this doc
builds directly on both and doesn't restate their content except where needed for context.

## 1. Bird's-eye picture: three separable layers, only one still genuinely open

**Layer A — test-harness-induced churn.** The `dut_ip` fixture's own `board.exec()` polling loop was
destructively soft-resetting the DUT's WiFi connection attempt on every poll (fixed in commit
`bdfc0716`, then fixed *again*, more fundamentally, in `b802d7b0` — see `REAL_HARDWARE_RUN_LOG.md`).
**Status: fixed in code, not yet verified end-to-end** (session paused mid-verification). This alone
could have inflated the observed failure rate — a bug layered *on top of* whatever real flakiness
exists, not the whole explanation for it (the original 2/5 reproduction, in an earlier session
before `tests_hardware/` existed at all, used no `board.exec()` polling at all).

**Layer B — the application-level retry/hotspot-fallback state machine**
(`src/asy_wifi_service.py`'s `wlan_connect()`/`_register_sta_connection_failure()`). Confirmed
byte-for-byte equivalent in shape to the legacy, field-proven `python/CommonDrivers/async_connect.py`
— not a refactor bug, working exactly as designed. Not a candidate for the root cause; only relevant
because its exact timing (5 attempts, ~0.5s status polls inside each, `wifi_refresh_sec=5` between
attempts — so all 5 attempts of one `conn_fail_to_hotspot` streak land within roughly a **30-45
second window**) matters for §2's hypothesis.

**Layer C — the actual, still-unexplained real-world flakiness.** This is what's still open, and
it's worth treating as *itself* possibly two or three separable contributors rather than one bug:

- **C1 (new, not yet considered — see §2): AP-side stale association/station-table state.** The
  bench AP backend may still be carrying a station-table entry for the DUT's MAC from a *previous*
  association when the DUT's abrupt, ungraceful restart (a hard reset — a real power-cycle of the
  RP2040 and, via `WL_REG_ON`, the CYW43 chip too, but **not** a graceful `wlan.disconnect()` that
  would send a real 802.11 deauthentication frame first) tries to associate again moments later.
- **C2 (already found, real, but a class of issue, not a specific fix): known upstream
  cyw43/pico-sdk timing sensitivity around rapid reconnects** (`raspberrypi/pico-sdk#2186` et al. —
  see §3). Real, but the fix that resolved *that* specific report (a `sleep_ms(10)` insert in a
  C-level polling loop) isn't directly actionable from this project's own MicroPython/Python-level
  code — see §3 for why, and §5 for what *is* actionable here.
- **C3 (already flagged in `REAL_HARDWARE_RUN_LOG.md`, not yet tested): debug-print/asyncio-scheduler
  jitter** contending with `_poll_sta_connect_status()`'s own tight ~5s-per-attempt budget.
- **C4 (lower priority, mention only): `WL_REG_ON` power-cycle settle timing** on the chip side. The
  timing here is fixed, driver-defined C code every Pico W runs, not something this project's own
  timing choices affect — least likely of the four, kept for completeness, not worth spending time
  on before C1–C3 are exhausted.

None of C1–C4 need (or should get) a `src/` code change if confirmed — see the "outside this
project's own code" bucket `tests_hardware/README.md` and `CLAUDE.md` already place I2C-bus-wedge
recovery and DHCP-client behavior in. The goal of the test plan in §6 is narrowing down *which* of
C1–C3 is actually doing the damage (very possibly more than one at once), so the project owner has a
real answer instead of an open question, and so the *test harness's own* choices (whether it kicks
stale AP state before a trial, what debug level the DUT runs at) can be set to stop making an
already-marginal real-world characteristic look artificially worse than it is in the field.

## 2. The strongest hidden-cause candidate: AP-side stale station state (C1)

**The claim:** the bench AP's own backend (whichever NetworkManager is actually running underneath
`br0-wifi-ap` — confirm which, don't assume, see Step 0 below) still has a station-table entry for
the DUT's MAC address left over from a previous association, because the DUT's hard reset never
sends it a deauthentication frame. A fresh Association Request arriving moments later from a MAC the
backend still considers (fully or partially) associated is not guaranteed to be handled as a clean
new association — general 802.11 AP/authenticator behavior (see §3's citations) only guarantees that
*eventually*, on its own inactivity timer, a stale entry gets torn down through a multi-step
disassociate→wait→deauthenticate→cleanup sequence; nothing guarantees a *concurrent* fresh
Association Request from the same MAC is fast-pathed to a clean new session before that.

**Why this fits the observed symptoms unusually well** (`REAL_HARDWARE_RUN_LOG.md`/
`tests_hardware/README.md`'s own evidence, re-read against this hypothesis):

- **"AP-side station entry stays present throughout, never removed, with flat `rx bytes` but a
  periodically-resetting `inactive time`"** — exactly the shape of a stuck/half-open entry: *some*
  management-plane frame from the DUT's MAC (an auth or (re)association attempt) reaches the backend
  on each retry, resetting its inactivity clock, but no data-plane traffic (no completed handshake)
  ever follows.
- **"6/8 trials fell back to hotspot"** in one tight burst of `hard_reset()` calls, each only tens of
  seconds apart — squarely inside a station-table entry's typical multi-minute lifetime (hostapd's
  own default `ap_max_inactivity` is 300s; see §3). A burst of trials this close together would keep
  colliding with the *same* not-yet-expired entry from the trial before, compounding across the
  whole burst — consistent with a *worse* rate in a tight burst (6/8) than in the earlier, more
  spread-out session (2/5).
- **It doesn't even need the cross-trial framing to explain a single failing boot.** One
  `conn_fail_to_hotspot` streak is 5 back-to-back attempts inside ~30-45s (Layer B above). If the
  *first* attempt's own handshake gets far enough to create a station-table entry before stalling,
  attempts 2-5 are then racing against that same entry the whole streak — which would explain why
  all 5 fail *identically*, not just why bursts of separate boots do.
- **"Recovered a stable connection this session by cycling the bench AP profile (`nmcli connection
  down/up br0-wifi-ap`)"** — a full profile bounce tears down and restarts the AP backend from
  scratch, unconditionally wiping *all* station-table state instantly. That this "fixed" the very
  next connection is exactly what C1 predicts, and is much harder to explain under the
  debug-print-jitter (C3) or chip-timing (C4) hypotheses, which have no reason to depend on the AP's
  own connection-tracking state at all.
- **It's a genuinely different mechanism from the already-fixed `wifi-sec.pmf disable` fragility**
  (`dev_legacy/README.md`) — PMF governs *protected* management frames (used for SA-query-based
  disassociation robustness), and is already disabled on this bridge; C1 doesn't depend on PMF being
  enabled at all, it's a plain "stale table entry" issue that predates and is orthogonal to that
  fix, not a variant of it (worth confirming this framing is right, not just asserting it — see the
  `iw`/backend-log evidence in §6).

**The good news: this is cheap to test, and the tool already exists.** `bench_control.py` already
has `bench_associated_station_macs(iface)` (an `iw station dump` MAC list) and
`BenchBridge.kick_client(mac_address)` (`iw station del`) — flagged in `tests_hardware/README.md` as
"not currently called by any test in this tier" and its real effect "still needs verification on
first real run." §6 turns that gap into the very first active (not just passive) diagnostic to run.

**One nuance worth knowing before relying on it**: `iw station del` "drops the client from the
authentication table without sending a proper deauthentication packet" (confirmed via web research,
§3) — it forcibly clears the *AP's own* stale entry (which is exactly the thing C1 says is stuck),
but it is not itself a clean 802.11 deauth exchange with the DUT. That's fine for the diagnostic use
in §6 (the DUT doesn't need to see anything — it's about to be power-cycled anyway), but don't read
too much into it as a "real" fix for anything beyond this bench test's own use.

## 3. Deep research — what's actually out there, and what it does/doesn't tell us

Checked directly this session (web search + issue fetches), not asserted from training-data memory
— matching this repo's own "check current docs, don't rely on memory" standing practice
(`CLAUDE.md`'s "Platform target" section):

- **`raspberrypi/pico-sdk#2186`** ("Pico W hangs connecting to WiFi in station mode"): a real,
  maintainer-triaged (milestone 2.1.1) bug in `cyw43_ll.c`'s `cyw43_do_ioctl()` polling loop,
  specifically under **`pico_cyw43_arch_lwip_poll`** mode and **specifically Pico W, not Pico 2 W**,
  triggered by *repeated* connection attempts. Reported workaround: inserting `sleep_ms(10)` inside
  the polling loop stabilized it for days. **Important caveat for this project**: this is the
  **C-level pico-sdk's own polling-mode arch layer** (`pico_cyw43_arch_lwip_poll`) — MicroPython's
  `rp2` port does **not** use `pico_cyw43_arch_lwip_poll` (it integrates `cyw43-driver` directly
  against its own scheduler/IRQ handling, not through this particular pico-sdk convenience wrapper),
  so this specific fix is not a drop-in "we're missing a sleep_ms() call" gap in this project's own
  code. What it *does* establish, credibly: `cyw43_do_ioctl()`'s own polling loop is a real,
  independently-confirmed source of timing fragility around **repeated** connection attempts on
  this exact chip — supporting evidence for C2/C3's general "this chip is timing-sensitive on rapid
  reconnects" framing, not a specific patch to port over.
- **`raspberrypi/pico-sdk#2316`** ("WiFi disconnects and does not recover"): a different-shaped
  report (an established connection silently dying, no automatic recovery attempted by the
  reporter's own polling code) — not closely analogous to this project's boot-time
  connect/reconnect scenario (`src/asy_wifi_service.py` already retries and eventually falls back
  to hotspot; the C-level SDK example in that issue apparently didn't retry at all). Filed here for
  completeness, not as a strong match.
- **`raspberrypi/pico-sdk#1054`, `#1373`** (found via search, not independently re-verified in
  depth this session — the search snippets describe further Pico W connect/timeout inconsistencies
  tied to reset/reboot sequences): consistent with the general pattern, not independently confirmed
  beyond what the earlier session's own citation already established.
- **General 802.11 AP/hostapd station-lifecycle behavior** (multiple sources, cross-checked against
  each other, not a single blog post): a station that stops responding (no explicit
  deauth/disassoc) is cleaned up via the AP's own inactivity mechanism — hostapd's documented default
  `ap_max_inactivity` is **300 seconds**, and cleanup itself is multi-step (an inactivity probe,
  then disassociate, a further ~1s wait, then deauthenticate, *then* the table entry is actually
  freed) rather than instant. `iw dev <iface> station del <mac>` forcibly removes a station-table
  entry without a proper deauth handshake — confirmed via multiple independent sources describing
  the same behavior. Neither of these is CYW43/Pico-W-specific — they're standard AP-side behavior
  that would apply to *any* client reconnecting abruptly against *any* hostapd-family AP, which is
  exactly why C1 is worth taking seriously as a general, not project-specific, mechanism.
- **NetworkManager's actual AP-mode backend is not settled by web research alone, and matters for
  how deep §6's diagnostics can go**: NetworkManager can back a WPA2 AP-mode connection with either
  a real `hostapd` process or its own internal `wpa_supplicant`-based AP-mode implementation,
  depending on what's installed/available on the host and on NetworkManager's own version/config —
  sources disagree on which is the automatic default, and none of them are about *this* specific
  bench Pi4's actual installed packages. **Do not assume either answer — confirm directly on the
  bench host** (Step 0 below is a five-second check). This determines which log source (`hostapd`'s
  own debug output vs. `wpa_supplicant`'s) is available for the deeper diagnostic in §6.4.
- **`datasheets/pico w/RP-008312-DS-2-pico-w-datasheet.pdf`**: this repo's own real Pico W
  datasheet. It's a hardware/electrical datasheet (module pinout, RF/electrical specs, antenna
  matching) — not a firmware/protocol reference, so it has essentially nothing to say about
  reconnect timing, station-table behavior, or `cyw43` firmware internals. The already-consulted
  `cyw43-driver`/MicroPython C source (`cyw43_ctrl.c`, `ports/rp2/main.c`) was and remains the right
  primary source for driver-level facts, not this PDF — noted here only so a future session doesn't
  spend time re-checking it expecting protocol-level answers it doesn't have.
- **What was *not* found, despite trying multiple phrasings**: any existing report describing this
  project's *exact* symptom combination (AP-side entry persists, flat rx bytes, periodic
  inactive-time reset, recovered by an AP profile bounce) tied explicitly to CYW43/Pico W. That
  doesn't rule C1 out — it's a generic-enough AP-side mechanism that it wouldn't necessarily be
  filed as a "Pico W" bug by anyone hitting it (most people hitting stale-AP-state issues are
  chasing it from the AP side, in router/hostapd forums, not attributing it to their client chip at
  all) — but it does mean C1 is this session's own synthesis from general 802.11/hostapd behavior
  plus this project's own specific evidence, not a "someone else already found this exact bug"
  citation. Treat it as a strong, testable hypothesis, not a confirmed external fact.

## 4. Other candidate hidden causes considered and set aside (for now)

Worth naming explicitly so a future session doesn't waste time rediscovering these were already
thought about and deprioritized, with reasons:

- **A second WiFi client on the same channel/AP interfering** — not plausible on this bench rig
  (single dedicated bridge, no other associated clients expected); would show up as *other* MACs in
  `bench_associated_station_macs()`, which is worth a quick glance while investigating anyway (near-
  zero extra cost) but isn't a serious independent hypothesis.
- **Country/regulatory-domain or channel mismatch causing the AP and DUT to briefly disagree on
  channel during a fast reconnect** — `network.country(country)` is called by
  `_trigger_sta_connect()` on every attempt using the same configured value every time; no plausible
  mechanism for this to change mid-burst. Not pursued further.
- **A DHCP-server-side issue** — already directly ruled out by the earlier session's own `tcpdump`
  evidence (zero DHCP packets during a failing cycle). Not re-opened here.
- **This project's own retry/backoff constants being too aggressive** (`conn_fail_to_hotspot=5`,
  `wifi_refresh_sec=5`) — plausible in the abstract, but changing `src/` timing to route around an
  AP-side or chip-side characteristic is exactly the kind of "don't touch this from the wrong layer"
  move `SPECIFICATION.md` Part F.3's standing principle warns against, and premature before C1-C3
  are actually distinguished. If §6's diagnostics land on "the AP genuinely can't clean up state
  fast enough, and there's no test-harness-side mitigation," *then* this becomes a real conversation
  to have with the project owner — not before.

## 5. Suggested solutions, branched by what the test plan in §6 actually finds

Don't pick one of these in advance — §6 is designed to produce enough evidence to choose correctly.
None of these branches call for a `src/` change without the project owner's explicit sign-off, per
`REAL_HARDWARE_HANDOFF.md`'s own "what to do with what you find" section.

**If §6.2/§6.3 show `kick_client()` before each reconnect drives the failure rate to ~0 (C1
confirmed as the dominant cause):**
- This is, functionally, a **test-methodology finding**, in the same family as the already-fixed
  `dut_ip` `exec()`-polling bug: the *test harness's own* choice to hammer `hard_reset()` in tight
  bursts against a real AP is what's producing a worse failure rate than the field would ever see
  (a real device only hard/WDT-resets rarely; back-to-back resets seconds apart are a
  testing-specific stress pattern, not a realistic field scenario — except see the WDT-loop caveat
  below).
- **Mitigation for the test harness itself**: have `dut_ip`'s `hard_reset()` retry path (and any
  standalone burst-reproduction script from §6.2) call `bench.kick_client(mac)` for the DUT's own
  MAC immediately before each `hard_reset()`, using the already-existing
  `bench_associated_station_macs()`/`kick_client()` primitives. Cheap, already-available, no new
  code beyond wiring it in.
- **One real field-relevance caveat to flag to the project owner even in this branch**: a device
  that's WDT-looping in the field (repeatedly rebooting because something else is wrong — the exact
  scenario `CLAUDE.md`'s "hardware watchdog is the accepted backstop" principle already anticipates
  for a wedged I2C bus) would recreate the same tight-burst-of-abrupt-resets pattern against
  whatever real AP it's on, with no bench harness able to `kick_client()` on its behalf. Worth
  naming as a real, if secondary, risk even if this is "just" a test-methodology artifact for the
  purposes of this investigation.

**If §6.4's lower-debug-verbosity A/B test shows a clear improvement (C3 confirmed or a real
contributor):**
- Points at genuine asyncio-scheduler/serial-I/O contention during the ~5s connect-poll window.
  Actionable options to raise with the project owner (don't pick unilaterally): lower this bench
  unit's *own* configured debug level for day-to-day bench use (a config change, not a `src/` code
  change); or, if judged worth it, a `src/asy_wifi_service.py` design conversation about whether
  `_poll_sta_connect_status()`'s ~5s budget has enough margin under this project's own real
  print-log volume — flag, don't implement, per `REAL_HARDWARE_HANDOFF.md`'s standing rule for
  anything that's a design-level judgment call rather than a constant tweak.

**If neither C1 nor C3 meaningfully moves the failure rate, but the chip-level `cyw43_do_ioctl`
timing-bug class (C2) still looks plausible from §6.5's evidence:**
- Check whether the MicroPython version this project pins (`v1.28.0`, `toolchain/versions.toml`)
  vendors a `cyw43-driver`/`cyw43-firmware` revision that predates or postdates whatever upstream
  fix (if any) eventually landed for the pico-sdk#2186 class of issue — this needs checking
  MicroPython's own `lib/cyw43-driver` submodule pin for `v1.28.0` specifically, not assumed from
  the pico-sdk C-example fix directly (different consumption path, per §3). If a newer MicroPython
  pin would plausibly help, that's a `toolchain/versions.toml` conversation with the project owner
  (a real version-bump decision, with its own re-verification cost per `CLAUDE.md`'s "whenever the
  pinned MicroPython version changes" standing practice) — not something to change unilaterally
  mid-investigation.
- Otherwise: document as an accepted, real hardware/firmware characteristic in the same "outside
  this project's own code" bucket as I2C-bus-wedge recovery, with the bounded `hard_reset()` retry
  already in `dut_ip`/`joined_hotspot` as the accepted mitigation — same conclusion the bench session
  had already tentatively reached before this doc, just reached with fuller evidence this time.

**If nothing in §6 produces a clean signal either way (genuinely inconclusive after the ordered
plan):**
- Say so plainly to the project owner rather than forcing a conclusion. The existing bounded-retry
  mitigations already in place are real and already reduce the practical impact
  (`REAL_HARDWARE_RUN_LOG.md`'s own fixes) — an inconclusive root cause doesn't block moving on to
  the remaining `REAL_HARDWARE_RUN_LOG.md` phases if the project owner is satisfied with "mitigated,
  not fully explained" as a resting state for now.

## 6. Ordered test plan — fastest/cheapest first, full runs last

**Design principle used throughout**: almost everything below needs only a *single* `hard_reset()`
cycle (tens of seconds) to produce a signal, not a full `pytest tests_hardware` invocation (which
re-verifies flash-tier basics every time via the `board`/`bench` fixtures and takes much longer).
Reserve the full bench suite / 20+-minute runs for **after** a fix candidate already looks promising
from a fast, isolated test — not as the way to discover one. Where a step needs a repeatable
diagnostic, write it as a **small standalone script** using `harness.Board`/`bench_control.BenchBridge`
directly (the same primitives `tests_hardware/` itself is built on), not as a new permanent
`pytest` test file, until a step's finding is solid enough to justify one — this keeps iteration
fast and avoids growing the tier with throwaway diagnostic code.

### Step 0 — seconds, no reboot, do this first

Confirm which AP-mode backend is actually running for `br0-wifi-ap` on this specific bench Pi4
(§3's open question):

```sh
ps aux | grep -E 'hostapd|wpa_supplicant'
```

Record which one (or both — NetworkManager may run `wpa_supplicant` for client-mode `br0-eth0`
concurrently with `hostapd` for the AP leg; note both PIDs/roles if so). This single fact determines
which log source Step 6.4 below can actually use, and whether `ap_max_inactivity`'s hostapd-specific
default (§3) applies literally or only by analogy.

### Step 1 — seconds, no reboot: finish the paused work first

Before any new WiFi diagnostics, close out `REAL_HARDWARE_RUN_LOG.md`'s own item 1: re-verify the
corrected `dut_ip` fixture (commit `b802d7b0`) actually works end-to-end. Run a small `-k` subset,
**not** the full bench suite:

```sh
uv run pytest tests_hardware -v -k test_get_nonsense_path_is_shaped_404_over_the_normal_network
```

This exercises `dut_ip` (one `hard_reset()`, passive `tail_log()` watch, one follow-up `exec()` +
`hard_reset()` to read the IP) without pulling in anything WiFi-investigation-specific yet. If this
fails or hangs, stop and re-diagnose the fixture itself before trusting any of the timing-sensitive
diagnostics below — they all depend on the same `hard_reset()`/`tail_log()` primitives being sound.

### Step 2 — ~30-60s per trial: build the fast, minimal repro script

Write a small standalone script (scratch file, e.g. `tests_hardware/_scratch_wifi_repro.py`, not
committed as a permanent test) that does the *minimum* needed to reproduce a single trial fast:

```python
import sys, time
sys.path.insert(0, "tests_hardware")
from harness import Board
from bench_control import BenchBridge, bench_associated_station_macs

board = Board()
bench = BenchBridge()
iface = bench.wifi_iface()

board.hard_reset()
lines = board.tail_log(duration_s=45.0)
joined = "\n".join(lines)
outcome = (
    "HOTSPOT_FALLBACK" if "Permanently no WLAN connection" in joined
    else "CONNECTED" if "WLAN connection established" in joined
    else "TIMEOUT"
)
print(f"outcome={outcome} stations_after={bench_associated_station_macs(iface)}")
```

This is deliberately **not** the `dut_ip` fixture — no HTTP-readiness wait, no `exec()` call to read
the IP back, no `hard_reset()`-retry-on-failure. Each trial is one `hard_reset()` + a bounded passive
`tail_log()` watch, nothing else, so a batch of trials runs in a few minutes rather than tens of
minutes. Run this once manually first to confirm it reproduces the known failure shape at all before
trusting it for the A/B comparison in Step 3.

### Step 3 — the key new diagnostic, ~10-15 minutes total: paired A/B with `kick_client()`

Using the Step 2 script as a base, run two back-to-back batches, same session, same conditions,
only one variable changed:

1. **Control batch** (N=10 trials): the Step 2 script as-is, no AP-side intervention.
2. **Treatment batch** (N=10 trials): immediately before each `board.hard_reset()`, first clear any
   stale station-table entry for the DUT's MAC:
   ```python
   for mac in bench_associated_station_macs(iface):
       bench.kick_client(mac)
   ```
   (On a dedicated bench bridge with nothing else associated, every entry `bench_associated_station_macs()`
   returns should be the DUT's own MAC — worth a one-time sanity check, not an assumption to bake in
   silently.)

Record the outcome distribution for both batches. This is the single most informative experiment in
this whole doc — a stark difference (e.g. control ~4-6/10 hotspot-fallback vs. treatment ~0-1/10)
is strong, direct confirmation of C1; no meaningful difference cleanly rules C1 out and redirects
effort to C3/C2 without further guessing. **This alone should take well under 20 minutes** — far
less than one full bench-suite run — and answers the question a full run wouldn't (the full suite
doesn't isolate this variable at all).

### Step 4 — seconds of extra setup, run alongside Step 3's control batch: capture backend logs

Whichever backend Step 0 identified, capture its own logs spanning a few control-batch trials in
parallel (a separate terminal/background process, not blocking the trials themselves):

```sh
sudo journalctl -u NetworkManager --since "1 minute ago" -f | tee /tmp/nm-wifi-trace.log
```

grep afterward for the DUT's MAC (get it once via `bench_associated_station_macs()` or from an
earlier `dut_ip` run's own diagnostics) to see the real auth/assoc/reassoc/EAPOL/deauth sequence (or
lack thereof) the backend logged during a failing cycle — this is the closest available substitute
for a real 802.11 management-frame capture (no monitor-mode-capable second radio is provisioned on
this bench rig, per `HARDWARE_TEST_PLAN.md` §9's own "not currently provisioned" list — don't spend
time trying to improvise one before trying this far cheaper option first). If `hostapd` is the
backend, its own default log verbosity may not show per-frame detail; a temporary, deliberately
reverted increase to `nmcli`'s exposed logging verbosity (if any) or a manual `hostapd -dd` run
against a throwaway test config are both heavier options — only worth it if this cheap `journalctl`
pass is inconclusive, not as a first move.

### Step 5 — only if Step 3 is inconclusive, ~1200s (a device restart with a lowered debug level) — testing C3

If Step 3's A/B doesn't show a clean signal, test the debug-print/scheduler-jitter hypothesis next
(cheaper than chasing C2/C4): temporarily lower this bench unit's configured debug/print verbosity
(check whether this is REST/config-reachable — `PUT` to whatever endpoint governs `debug=`/print
level, per `SensorReaderConfig`'s constructor parameter already read throughout `src/` — before
assuming a firmware rebuild is required; only rebuild+reflash if genuinely necessary, and that
crosses into flash-cycle territory, meriting a deliberate decision, not a routine step). Re-run
Step 2/3's batches at the lowered verbosity and compare.

### Step 6 — only once a candidate fix/mitigation looks promising from Steps 2-5, ~10-20 minutes: confirm at scale

Re-run a larger batch (N=15-20) under whatever condition looked best in Steps 3/5, plus the existing
permanent regression tests, to confirm the improvement holds up beyond the smaller diagnostic
batches:

```sh
uv run pytest tests_hardware -v -k "test_real_sta_connect_reaches_established_after_a_hard_reset or test_real_wifi_outage_and_recovery_while_in_normal_sta_mode or test_real_wifi_flaps_repeatedly_without_wedging_the_system"
```

### Step 7 — only after Step 6 confirms something real, resume the full plan

Once the WiFi question has a real answer (confirmed cause, or a deliberate "inconclusive, accepted"
close per §5's last branch) **and** Step 1's `dut_ip` re-verification is solid, resume
`REAL_HARDWARE_RUN_LOG.md`'s own remaining phases in the order it already lays out (full bench
suite re-run, hotspot role-reversal watched closely, the bounded soak window, the global regression
pass, wrap-up) — this doc doesn't change that ordering, it only fills in Phase 4 in more depth. Full
20+-minute runs belong here, at the end, once there's a real reason to expect them to pass cleanly —
not as an early diagnostic tool for the questions Steps 0-5 above already answer far faster.

## 7. Evidence checklist — record this regardless of which branch things land in

For whoever picks this up: capture and keep (in this file's own "Findings" section once you start,
or in `REAL_HARDWARE_RUN_LOG.md` if that's still the live log at the time) —

- [ ] Step 0's answer: `hostapd` and/or `wpa_supplicant`, which PID(s), for which connection.
- [ ] Step 2's script output for every trial in both Step 3 batches (outcome + station list after).
- [ ] Step 3's final tally: control N and fallback count vs. treatment N and fallback count.
- [ ] Step 4's `journalctl` excerpt for at least one full failing cycle, with the DUT's MAC's lines
      pulled out explicitly.
- [ ] Whether `bench_associated_station_macs()` ever showed more than one MAC during any trial (a
      genuine surprise worth its own investigation, not silently ignored if it happens).
- [ ] Step 5's result if run: pass/fail counts at each debug level tested.
- [ ] Whichever branch of §5 was ultimately taken, and why — this is what eventually migrates into
      `tests_hardware/README.md`'s WiFi section once this doc is closed out.

## 8. Guardrails (restating, not overriding, what's already established)

- No `src/` change without the project owner's explicit sign-off, whatever §6 finds — every branch
  in §5 already reflects this, restated here so it isn't missed if this section is read in
  isolation.
- `kick_client()`'s real effect was, until this doc, still flagged "needs verification on first real
  run" (`tests_hardware/README.md`) — Step 3 *is* that verification. Confirm it actually clears the
  entry (via `bench_associated_station_macs()` showing it gone afterward), don't just trust a
  zero exit code.
- Nothing in this plan needs `--allow-flash-cycle` or a UF2 reflash. If Step 5 turns out to need a
  firmware rebuild to change debug verbosity, treat that exactly as seriously as
  `REAL_HARDWARE_HANDOFF.md`'s own flash-cycle guardrail already requires — a deliberate decision,
  not a routine step, and check whether a REST-reachable config knob avoids it first.
- This doc's own hypothesis (§2) is this session's synthesis of general 802.11/AP behavior against
  this project's own specific evidence — treated with the same "confirm directly, don't trust a
  plausible-sounding narrative" discipline `tests_hardware/README.md`'s own two self-corrections
  (the SCD30 RDY-pin mistake, the `dut_ip` `exec()`-polling mistake found only after the project
  owner pushed back and asked "are you sure you didn't miss something") already had to relearn
  twice this branch. Step 3 either confirms it with real numbers or it doesn't — don't write it up
  as settled based on how well the narrative fits alone.
