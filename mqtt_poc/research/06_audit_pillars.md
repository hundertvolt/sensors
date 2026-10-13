> **Raw research report** (agent, 2026-10-07): written by a read-only research agent of the MQTT PoC research session, kept verbatim as the evidence base for `mqtt_poc/RESEARCH.md`. Tags such as [V]/[SRC] mean verified in source by that agent; [I]/[INFERENCE] are not verified; nothing here was run on hardware. Clone paths (`<research-session scratchpad>/ext/...`) refer to that session's temporary scratchpad, not to this repo. Line anchors into this repo are as of `1cff5a2`.

# 06 — Audit pillars, rules and decisions that bind an MQTT client service (PoC)

Read-only analysis of `/home/user/sensors` at branch `claude/whole-project-audit-plan-followup`
(HEAD `90b258c`, "Open the follow-up branch off claude/whole-project-audit-plan"). Sources read:
`PROJECT_AUDIT_PLAN.md` (sections 0-4 in full, OR1-OR150 rows, areas XCUT/CORE/NET/REST/SEC/MEM/PERF/PLAT/LIC),
`audit/CONSOLIDATION.md` (whole), `audit/HARVEST_REQUIREMENTS.md`, `audit/REGISTER.md`, `audit/pass2/INDEX.md`,
`audit/pass2/G6.md` and `LEAD.md` (network/REST/reliability requirements), `audit/order/WORK_ORDER.md`,
`audit/actions/U18.md`/`U19.md`/`U20.md` (titles plus selected actions), `audit/actions/SUPP_lwip.md`,
`audit/sweeps/silent_failure_scan.md` (classes and modes), `audit/DECISION_PROVENANCE.md` (skimmed),
`BACKLOG.md`, `LICENSE`, `THIRD_PARTY_LICENSES.md`, `SPECIFICATION.md` Parts B.14.2, C.2, C.4.1, C.7.2, C.8, C.9,
F.2-F.4, F.9, G.2, H.7, I.4, K, L; `toolchain/versions.toml` `[lwip]`; `toolchain/micropython_overrides.py`;
`tests_scripts/` checks named below; `legacy/`. Third-party MQTT sources were read from clones other agents left in
this session's scratchpad (`scratchpad/ext/peterhinch-mqtt_as` at `dd03ab3`, `scratchpad/ext/micropython-lib` at
`4fa59bd`, `scratchpad/ext/micropython-v1.29.0`). Line numbers are as of HEAD.

---

## 0. Where the audit stands (what "binding" means right now)

- **Phase B (execution) since 2026-10-06 (OR145).** Owner, verbatim: "With this step, there is a paradigm change:
  the pillars and rules and specifications we wrote and refined are no longer subject to change, but become effective
  and need to be adhered to inside the implementation process." OR145.a (2): "a conflict found during execution is
  parked and passes A-C as a delta (OR2.c, OR106.a), never settled by editing a rule."
- **Register header** (`audit/REGISTER.md`): lease held by session `01BWfjT6GSD7bxCP57j86vB8`; units U0-U14 (+U0R,
  U8C, U8C2) **done**; **U15-U37 and phases C, D not started**. Work order: 1,909 merged changes, 6,571 steps.
  Units still to come that own the files an MQTT service would touch: U16 STOR, **U18 NET** (194 steps),
  **U19 REST** (119), **U20 GEN** (242), **U21 TOOL** (lwIP override), U23 WEB, U24 TEST, U25 TWIN, U26 HW,
  U29 SEC, U30 MEM, U31 PERF, U34 LIC, U35 test campaign, U36 docs (Design-principles Part, one ordered checklist).
- **`main` is frozen** for the audit; one merge at close (OR52.a (4), plan 2.3). The audit branch is the one PR
  (#107); OR11.a/PQ2: "one audit branch, one PR, one merge into main".
- **Feature parity is the audit's goal** (OR12 / plan goal 8: "top-level features never change"; CLAUDE.md working
  agreement: "the same top-level features … just more consistent/stable — not a feature change"). BACKLOG's UART
  item gives the precedent for a feature that legacy never had: "adding one would be a scope addition beyond
  feature-parity rather than a postponed fix" (owner, 2026-08-20, `b6cb852`). **An MQTT client is exactly such a
  scope addition** — nothing in the audit records it, so it has no OR row, no register line and no unit.

---

## 1. Pillars and binding rules for a new network service (most binding first)

### 1.1 The concept and the pillars (`audit/CONSOLIDATION.md` section 1; OR44/OR44.a)

Owner's concept (OR44, verbatim): "a device which can run indefinitely long without any user interaction once
configured, handles all issues inside, and although barely reachable has multiple fallback layers, has premium
quality code, has all its main cases all the way through rare corner cases tested, and runs efficiently and compact
on a low end hardware device". OR44.a (3): the distilled checklist "applied thoroughly to anything added later (a
driver, a service, a route, a test, a build step, a device), produces fully fitting code on the first try".

| Pillar | Text (CONSOLIDATION.md §1) | What it demands of MQTT |
|---|---|---|
| **P1** | "Unattended indefinitely: nothing drifts, saturates or needs a person" | capped counters, bounded queues/ticks, reconnect forever without a person |
| **P2** | "Handles everything inside, at the right layer" | broker down / bad packet / link loss handled inside the module |
| **P3** | "Layered fallbacks: degrade, retry, re-setup, restart, reboot, watchdog; hardware faults escalate" | backoff → socket re-create → task end only for a real re-init |
| **P4** | "Premium code, one material, nothing in the product for tests" | Part C/D bar, config objects, no test seams |
| **P5** | "Proven main to corner cases, by tests that bite at every layer and level" | L0-L4, biting, both GC stages, fault planting |
| **P6** | "Efficient and compact on low-end hardware" | heap/lwIP budget, frozen size, loop latency |
| **P7** | "Evidence survives and stays readable" | FRAM-backed logger, one event one entry |
| **P8** | "One source of truth, generated not copied" | buildgen + `@web` tags, device set derived |
| **P9** | "Operating and testing never wear or damage anything" | no flash write without a user/API action |
| **P10** | "Extensible without edits elsewhere" | device TOML decides; no variant literals |
| **P11** | "Grounded and traceable … primary source at the pinned version" | MQTT spec + v1.29.0 source cited, never memory |
| **P12** | "Contracts at boundaries: one normative text, a named owner of change and a conformance check" | topic/payload scheme is a new external contract |

### 1.2 Binding rules, by theme (ID, location, short quote, consequence)

**A. Reliability and task integration**

1. **OR18 / OR18.a** (plan 3.2): the NTP precedent — a task "just stalling its task if the server was unreachable
   instead of handling it internally and properly self-contained. It purely relied on the global task supervisor".
   OR18.a: "abnormal but harmless situations (e.g. an unreachable server) must still be handled inside the module."
   Only "a missing, defective or stalled chip, or a configuration not matching the hardware" may escalate to reboot.
   → **An unreachable/refusing broker is never a task end.**
2. **SPEC C.7.2** "Which failures may end a task": "A task ends — and the supervisor restarts it — only when the
   restart re-initialises something real … A failure the task can meet again unchanged after a restart is routine and
   handled in place: log it …, keep counting it, retry, and recover on the next success." Restart cost: C.4.1 "A
   restart is not free" — 100 of `_TASK_FAIL_MAX` 300, decaying 1 per clean pass → "about three restarts from any
   source before it reboots itself" (system-wide budget; an MQTT task's restarts spend the sensors' budget too).
3. **G6/R23** (pass2, owner rank, C.7.2 "(owner, 2026-09-24)"): "retried on its own capped exponential backoff (NTP
   unsynced 10 s doubling to 600 s …; captive DNS 0.5-5 s …), never zero-delay, reset on first success. A task ends
   only when a restart re-initialises something real or on an exception it cannot handle". Bench tests assert "via the
   FRAM SYSTEM log that no task ended".
4. **A.U18.47** (pending U18, to SPEC C.7.2; owner 2026-09-24/09-26/09-30): "A remote fault (no or a bad NTP/DNS
   reply, a bad client datagram) is retried on its capped backoff and never escalates, since nothing local can repair
   the peer … A local fault escalates: a socket that cannot be created or bound is re-created on the next attempt; a
   timer that cannot be armed is re-armed at the next opportunity, then its task ends for the supervisor".
5. **OR113.a (2)** "recover with the smallest possible blast radius and escalate only when the milder step does not
   work" — owner: "always try to solve / recover from issues with the smallest possible blast radius". Harmonization 38.
6. **OR31 / OR31.a**: one runtime watchdog feed site, the supervisor loop, "never from a Timer/IRQ callback";
   per-task heartbeats rejected — "make sure the tasks themselves are written such that they either really work or
   return / end in any other case which cannot be handled internally (internal handling is absolutely preferred)".
   → MQTT never feeds the WDT and never blocks past the 8,000 ms watchdog.
7. **SPEC C.9** task/timer contract: modules expose `get_task_starters()` / `get_timer_starters()` /
   `get_trigger_starters()`; "every `create_task(`/`start_server(` in `src/` is a starter or a row here, checked by
   `tests_scripts/test_task_inventory.py`". Timer callbacks only `.set()` a `ThreadSafeFlag`; "A timer whose fire must
   not be lost is `PERIODIC`"; every `Timer.init()` catch is `except (MemoryError, OSError)`. G6/R37 precedent:
   non-bus 1 s timers stay out of the read-trigger stagger.
8. **OR47.a (1)/(2), OR75.a, OR84.a, harmonization 12/42**: boot phases strictly sequential — construction, the one
   ordered `setup()` list, task starts, timer starts, then the first NTP force sync; "no lazy setup inside tasks";
   every FRAM logger's store setup is in the boot batch.
9. **OR26 / OR26.a, SPEC D.2**: no unhandled exception at any layer; "special attention to task tops, Timer/IRQ
   callbacks …, and swallowing `except`s; construction completeness (setup really runs, C.13 gates honoured, no
   half-built object reachable after a failed setup)". MemoryError: implement the graceful alternative where one
   really exists, no blanket wraps (F.2, CLAUDE.md).
10. **G6/R54**: "Every task path … leaves shared state consistent when cancelled: locks, busy flags and indicators
    restored in `finally`, `CancelledError` re-raised and never swallowed". U35 runs a cancel-at-each-await sweep.
11. **G6/R49** (owner, 2026-08-03, `e72936e`): "No self-test or loopback probe of the server and no unconditional
    periodic restart … 'Both were offered and explicitly not chosen — don't re-add either … without asking again'".
12. **B02 / OR70.a (2), F.2, CLAUDE.md hard rule**: the CYW43 `isconnected()` false positive is recovered by power
    cycle, "because the owner judged an independent reachability probe not worth its complexity". An MQTT keepalive
    is a de-facto reachability probe; letting it drive WiFi recovery would reopen a settled decision (plan 2.3:
    "Settled decisions are not reopened … unless the premise is factually wrong").
13. **OR147-OR149** (silent-failure scan, `audit/sweeps/silent_failure_scan.md`): seven classes (ignored status,
    bounded storage dropping silently, detection left to chance, swallowed failures, windows where time/data is lost,
    faults without self-healing, asymmetric reporting) checked in every operating mode (boot, reset countdown, flash
    and FRAM writes, WiFi STA/AP/reconnect/IP change, long uptime, REST clients, runtime reconfiguration, load). OR149:
    "the fixes required for such reliability … are minimal, low complexity … giving the code a simple inherent way of
    handling it."

**B. Networking-specific**

14. **SPEC F.2**: "`socket.getaddrinfo()` is not called from `src/`: `asy_dns_client.py` resolves over its own
    non-blocking UDP client." F.9 row: "`getaddrinfo()` only on a numeric host (it cannot be timeout-wrapped)". At
    v1.29.0 `asyncio.open_connection()` calls it unconditionally (`extmod/asyncio/stream.py:103`, upstream comment
    "# TODO this is blocking!") and its connect wait (`yield core._io_queue.queue_write(s)`, `:122`) has no timeout.
    → resolve the broker with `resolve_ipv4()` first, pass a numeric IP, bound the connect with F.2's "one timeout
    mechanism" (`asyncio.wait_for_ms(<awaitable>, <timeout_ms>)`).
15. **SPEC F.3 / lens L-BLOCK**: nothing may block the loop beyond its budget; Part N rows `loop.sync_wait_max_us`.
    CLAUDE.md's UART no-block rule is UART-specific but states the house standard.
16. **lwIP write stall** (OR112/OR114/OR115, `audit/actions/SUPP_lwip.md`, SPEC B.14.2): `lwip_tcp_send()` retries
    `ERR_MEM` "200 × `mp_hal_delay_ms(50)` inside one C call, also for a non-blocking socket" → a 10 s VM freeze past
    the 8,388 ms WDT cap. "pcbs whose peers stop reading … keep ~7.2 KB each queued … two of them fill the arena".
    The fix (zero-touch `modlwip.c` override returning `EAGAIN`, OR114.a) is **planned for U21, not at HEAD**. A
    persistent outbound MQTT socket to a broker that stops reading is exactly the trigger. OR115.a demands hammer tests
    "at every level that can reach it".
17. **lwIP ensemble, SPEC B.14.2 / H.7**: `MEMP_NUM_TCP_PCB >= max_connections + 3` (`SPARE_TCP_PCBS`, for closing
    pcbs), `MEM_SIZE` share ≥ 2,000 B per admitted connection, `MEMP_NUM_TCP_SEG >= max_connections × 8`, all checked
    by `check_lwip_ensemble()` and `buildgen/validate.py` **for webserver connections only**. Pinned
    `[lwip]`: PCB 9, SEG 48, `MEM_SIZE` 12,000 for `max_connections = 6` (owner, 2026-09-24, `db3bf52`). "A connection
    costs 2,324 B of GC heap". H.7 measured: at 6, **~21 % free heap at peak, largest free block ~1.5 KB**; at 7,
    ~14 % — "only 6 keeps the conventional 20-30 % free at peak". A persistent MQTT connection silently consumes one
    of the three spare PCBs and a `MEM_SIZE` share nobody budgets today.
18. **UDP PCB budget** (A.U18.18, pending): `MEMP_NUM_UDP_PCB = 5`, "Peak 3 of 5" — NTP fetch or resolver "one at
    a time". MQTT's broker lookup through `resolve_ipv4()` adds a concurrent resolver user; must be released in
    `finally` like NTP.
19. **C.8 / G6/R26 `wifi_mode_lock`**: WLAN state is owned by `WifiService`; NTP reads `network_available_locked()`
    under `wifi_mode_lock` and resolves DNS before taking it. A.U18.33 (pending) "One networking snapshot: getters read
    it, never the radio"; A.U18.34 writes a lock-hold table into SPEC C.8 "with tests" — any new lock holder joins it.
    NET.S02 shows the cost of a long hold (WiFi ticks collapse, `/status` nulls). An MQTT client must never drive WLAN
    itself and must not hold `wifi_mode_lock` across a connection.
20. **NET.T10** (open topic): "Sockets across WLAN mode switches and `wlan.deinit()` … in-flight TCP connections …
    when the netif is torn down (STA↔AP, deactivation)". A.4/G6/R25 WiFi machine: hotspot fallback, 60 s silent
    retry, permanent deactivation after a second failed streak → MQTT must idle cleanly in hotspot/deactivated mode.
21. **G6/R36** (owner, 2026-09-26, OR71.a (5)): DHCP faults are a documented limitation; robustness tests "treat
    'WiFi up, no internet' as NTP/DNS unreachable, never inject DHCP faults".
22. **G6/R52 / OR52.a (3) / OR49.a** (client input): "Every byte a client sends is bounded before it is allocated";
    "malformed, partial or oversized input never crashes anything". For MQTT the broker is the input source: the
    4-byte remaining-length (up to 256 MB) must be capped before allocation (MEM.T03 "Client-controllable allocation …
    each bounded before allocation"; OR143.a chunking precedent for UART peer-declared sizes).

**C. Memory**

23. **CLAUDE.md memory-safety discipline / SPEC I.4 / OR39.a / OR40.a**: design for zero `MemoryError` first;
    "`gc.collect()` only at OR39.a's boot sites; the only other `gc` use is the one `gc.threshold(32768)`", enforced by
    `tests_scripts/test_gc_collect_sites.py` (allowance: `asy_system_service.py` `start_and_check_tasks` + codegen);
    whole suite green at `gc.threshold(-1)` and at 32768 with zero `MemoryError`/"memory allocation failed" markers,
    caught-and-logged included. Long-lived allocations land at boot (I.4(f.1) placement).
24. **OR103 / OR105.a / OR110 / LEAD/R24**: "No unbounded counters anywhere"; every cap ≤ 2**30 − 1 (rp2 small int),
    "Saturation checks before it steps (`if v < CAP: v += 1`) … never `min(v + 1, CAP)`"; "objects which reside in the
    heap forever, never are eligible for gc collection, and which can grow, are the forbidden case" (subscription
    tables, outbound queues, topic strings). LEAD/R24 also: no peer-derived string may reach an interning path
    (`getattr` with non-literal names, `**` keys, str indexing). Packet ids are wrap-by-design (G5/R10), not counters.
25. **OR49 / OR49.a / harmonization 41**: load tests on "every finite shared software resource: heap,
    sockets/connections, asyncio tasks, … CPU time against the watchdog"; pass = graceful degradation, explicit return
    to baseline, no crash/reboot/WDT/MemoryError marker, no log flood; one end-of-execution entry per new load test.
    OR89.a (2): "the webserver withstands any mix of clients … filling the whole connection ceiling" — an MQTT
    connection must not break that contract.
26. **F.1 platform workarounds** (F.9 table): no async generators, list concat not `[*a, b]`, "Shape validated
    before `struct.pack()` (silent truncation)", sizes clamped before `[x] * n`.

**D. Evidence and logging**

27. **OR28.a / SPEC C.7.1**: "One global catalog, one meaning per number project-wide … module-specific codes in
    non-overlapping per-module ranges"; a test reads every `err_s`/`wrn_s` against the catalog. A new module gets its
    own range plus shared-band codes.
28. **OR35.b**: "just don't repeat the same error in the slots. Pure and simple" (central rule in `print_log`);
    **OR56.a (1)**: "One event, one persisted entry … either as an error or as a warning, never both". No per-module
    episode flags.
29. **CLAUDE.md FRAM-forensics hard rule**: the list of FRAM-backed loggers in `/status` `errcount` is named in
    CLAUDE.md; a new FRAM-wired logger joins it (and the per-device FRAM chunk fit check, A.U20.11).
30. **OR60.a / F.5.4**: intended resets write `reset_reason` in `mem_backup()`; MQTT adds no reset path (if it ever
    did, it needs a code).

**E. Product purity, code shape, API**

31. **OR36 / OR36.a** (P4): "contains zero artifacts specifically added for testing, neither functions, nor specific
    variables. Testing must adapt to fit the code, never vice versa." Precedents removed: `conn_tries`, `_NTP_UDP_PORT`
    non-const, `resolve_ipv4(port=)`, `self.uart` public.
32. **OR46.b**: config objects instead of flat parameters, `max-args = 8`; "no post-construction registration methods
    (a half-configured object)". SPEC G.2 "Config objects".
33. **SPEC C.2 naming**: `asy_<x>_service.py` → `<X>Service`, acronyms upper-case (`NTPClient`), attributes private
    by default. **OR96.a**: members sorted by role then alphabetically. **OR81.a**: mypy `disallow_any_explicit` on in
    all three passes. PEP 604 unions. Comment cap: one header block, inline ≤ 3 lines (CLAUDE.md, OR51).
34. **OR43.a**: every value a module holds is placed — settings in their GET/PUT route, health and errors in
    `/status`; "GET returns exactly what PUT accepts"; Part H placement rule ("Networking = Wi-Fi/NTP/identity");
    "nothing may assume six devices". A.U20.25 (pending): "A schema field without a `@web` tag … fails the build".
35. **OR58.a / harmonization 33 / OR52.a (2) / LEAD/R08**: one key scheme before release; persisted config keys and
    file names "a public interface" from the release on (golden stored-config fixture). An MQTT topic/payload scheme is
    a new P12 contract.
36. **OR78 / OR78.a** (owner, 2026-09-28): "nothing about the WoZi and Dev build shall remain hardcoded at any place";
    enabled per `devices/<name>.toml` only; a `tests_scripts` check fails on variant literals.
37. **OR142.a**: the dynamic-import ban "covers all code this project writes, generates or vendors into an image:
    `src/`, `ext/`, the generated boot, device and website modules", enforced per image by
    `tests_scripts/test_import_graph.py`. `tests_scripts/test_import_placement.py`: "no import inside a function body
    … in the eight lint scopes".
38. **Part G (CLAUDE.md hard rule)**: check the primitive catalog first — `TickSeconds`, `utc_now()`, `make_logger()`
    + `LogConfig`, `compare_before_write()`, `LockedCounter` with cap, `type_or_range_error()`, `instance_name()`,
    error-source fan-in, `feed_watchdog()` (never hand-rolled). A new `src/` file triggers the bird's-eye scan.
39. **Part K / OR10 / OR10.a / harmonization 4**: the per-module checklist (K.1-K.11: buildspec, driver_registry
    `_OVERRIDES` for non-`SensorReader` services like `notification`/`fram`/`uart_link`, codegen handler,
    definitions, twin, tests at every tier, TOMLs, docs, K.11 certification). "Modules are the general case; sensor
    drivers are a specific module". Part K becomes "the one ordered checklist" in U36 (not yet written).

**F. Wear, threat model, writes**

40. **OR70.a (3) / harmonization 37 / CLAUDE.md**: "firmware never writes to a limited-endurance store (SCD30 NVM,
    the flash filesystem) without a user or API action"; "written only by an accepted PUT that changed a value".
    CLAUDE.md WiFi-backstop rule rests on: "every real flash write is reachable only through the REST PUT path, so a
    device whose API is unreachable structurally cannot have a write in flight" (SPEC F.2 "triggered only through the
    REST PUT path"). **An MQTT subscription that writes config adds a second trigger and changes that premise.**
41. **PQ5 / OR52.a (3)**: "trusted home LAN. Unauthenticated REST writes and `bootloader` are accepted properties,
    documented as known limitations"; radio-range attacks out. CLAUDE.md: never commit real credentials. G6/R29: a
    password is never disclosed on GET; a PUT of the mask stores it like any value (OR104.a).
42. **CLAUDE.md wear rule / OR37.a / OR49.a (2)**: no avoidable wear on target or host SSD; load tests write no
    limited-endurance store; prerequisite writes unmarked, owned writes behind `persistence_write`.

**G. Testing**

43. **OR45.a / SPEC E.6.1**: one ladder L0 host, L1 unit, L2 twin, L3 flash, L4 bench; "every twin scenario has a
    real-hardware counterpart, adapted"; "Flash has no network, so network scenarios land in bench".
44. **OR20.a / SPEC E.9 Driver/DUT separation**: twin/hardware test logic in a separate host CPython process (a test
    broker belongs host-side); OR125.a moves every twin scenario host-side.
45. **OR19.a / OR21.a / OR16.a / OR25.a**: biting tests proven by planted faults; intent coverage per layer; every
    unexecuted line covered or listed with its reason.
46. **OR41.a + CLAUDE.md shared-resource hard rule** (owner, 2026-09-03, `da3a5b5`: "note down to never forget
    this"; "every shared resource, owner, 2026-09-26"): "A new device on a shared resource — an I2C/SPI bus and every
    other shared resource (locks, FRAM, the config file, sockets, the heap) — gets hazard test coverage across all four
    test tiers". OR41.a's interaction matrix gains MQTT as an actor (vs. REST, WiFi reconnect, NTP/DNS, config writes,
    FRAM logging, supervisor restarts).
47. **OR38.a (3)**: "a test that chooses its own port asks the OS for a free one (port 0)"; product-fixed ports used
    by one tier at a time under a lock; CLAUDE.md "two suites that bind real ports" rule; bounded fake pollers only
    (CLAUDE.md hang rule).

**H. Dependencies and vendoring** (detail in section 3)

48. **CLAUDE.md "Every external dependency is refreshed as one step"** (owner, 2026-09-30: "Check all external
    dependencies for updates - both modules, repos and tooling, just everything."): "the vendored `ext/` code (only
    as an unmodified upstream tag or commit) … Read each update's changelog and the diff of the parts this repo uses;
    fix what breaks … re-check every standing workaround in SPECIFICATION.md Part F.9". OR129.a / LEAD/R33.
49. **CLAUDE.md vendoring hard rule / OR24.a (2) / G6/R53 / OR131.a**: `ext/` "never edited" — "re-vendoring an
    unmodified upstream tag stays the one way it changes"; hash pinned by a `tests_scripts` check; upstream stubs, if
    any, vendored byte-identical.

**I. Process (for whoever builds the PoC)**

50. **CLAUDE.md workflow + decision-record rules (OR68.a (4), OR71)**: research and cross-check first; owner
    questions only at requirement recording or consolidation; tests first, then implementation, then coverage tests;
    unforeseen decisions → "the more conservative, more easily reversible option grounded in sources", logged; every
    decision names actor and date; owner questions numbered, ≤ 10-word decision, options with consequences, effects
    per device and bus; `tests_scripts/test_decision_vocabulary.py` / `test_citations.py` gate the docs.
51. **Real hardware**: owner go-ahead in that very conversation; FRAM logs read before any clear; wear gates; bench
    `br0` MAC and dead-man's-switch rules (CLAUDE.md).

---

## 2. Reliability and self-healing — what it concretely means here

**The ladder (P3, SPEC I.4 (a)-(d), C.7.2, OR113.a (2), A.U18.47):**

1. *Handle in place* — routine/remote faults (server unreachable, garbage reply, network down) are logged once under
   the repeat rule, counted, and retried on a **capped exponential backoff that resets on first success and is never
   zero-delay**. Precedents: NTP unsynced 10 s ×2 up to 600 s, rounded to its 10 s tick, per-device
   `ntp_retry_s`/`ntp_retry_max_s` checked by buildgen as a pair; synced resync retries `_NTP_SYNC_RETRIES` × 15 s;
   captive DNS 0.5-5 s; UART listen `timeout/2` to `5 × timeout`. "an attempt skipped for 'network not up' leaves
   [the backoff] alone" (C.7.2). NTP "syncs only with an STA IP" (U18 ledger, G9/R04). "Confirmed on silicon
   (2026-09-25): with UDP 123 blocked, one `E71` slot (count 3), no task ended".
2. *Degrade* — a caught failure yields a defined `None`/`False`/"unavailable" (I.4 (b)); `/status` sources degrade
   per source (`_write_guarded()`).
3. *Re-setup locally* — a socket that cannot be created/bound is re-created on the next attempt; a timer that cannot
   be armed is re-armed at the next opportunity (A.U18.23/.24 precedent: NTP/WiFi re-arm and persist a failed timer).
4. *Task end → supervisor restart* — only when "the restart re-initialises something real" (C.7.2); costs 100 of
   300 (≈3 restarts system-wide before reboot), decays 1 per clean 2 s pass (`_TASK_CHECK_TIME`).
5. *Reboot* — supervisor escalation through `_reboot()`; feeding stops one-way (OR130.a: feeds once more at the first
   task end past the budget, then stops); `reset_reason` recorded in `mem_backup()` (OR60.a).
6. *Watchdog* — 8,000 ms hard-coded (OR70.a C07), one feed site; final backstop for anything blocking
   (wedged bus, a lost one-shot, the modlwip stall until U21's override).
7. *Power cycle* — the accepted recovery for the CYW43 `isconnected()` false positive (B02).

**Link-loss precedents an MQTT client must copy:**
- WiFi (A.4 / G6/R25): a link established once "never escalates: a later disconnect retries silently every 60 s";
  empty SSID or 5 failed attempts → hotspot; second streak after hotspot → permanent deactivation (power cycle only).
  A WLAN mode switch tears down the netif, freeing pcbs (A.U18.18: "a mode switch deinitialises the interface, which
  stops the STA DHCP client and frees its pcb").
- NTP: never ends its task (V50 "NTP never ends its task; an unreachable server is handled in place", owner via OR18);
  `ntp_force_sync()` after a settings PUT; `Synced` goes stale 3 intervals after the last success (A.U18.20).
- DNS: `resolve_ipv4()` returns sentinels and "never raise[s]"; DHCP server first, then the configurable fallback
  (`DNSFallback`, A.U18.10, owner OR56.a (2)); one A record, QNAME ≤ 255 octets.
- UDP: `AsyUDPSocket` content-agnostic, `disconnect()` in `finally` (A.U18.15), one connect attempt (A.U18.13).
- Webserver: `_serve()` retries a failed server start before the task ends (A.U19.09); per-call timeouts and an
  outer cap; `peer_gone` suppression after a reset (F.9 row); no probe, no periodic restart (owner, 2026-08-03).
- Bus layer: the OR113.a ladder (retry → participant recovery → bus clear → controller re-init → task restart →
  reboot → watchdog), "each rung bounded, logged once per event … race-free … tested at every level".

**What "self-healing" is NOT allowed to be:** a reboot or task end for an external outage (OR18.a), a zero-delay retry
loop, an `except` that swallows without logging/counting (silent-failure class 4), a recovery nobody can observe
(class 6), a probe that drives WiFi recovery (B02), periodic unconditional restarts (G6/R49).

**Evidence:** every failure leaves persisted, attributable evidence (lens L-DIAG): FRAM-backed per-module history
(10-slot ring, `ErrCount`), catalog codes, one event one entry, repeats spend no slot; SYSTEM logs one entry per task
end; `LastTaskEnd` in `/status` (OR128.a); `reset_reason` and `ResetBits` (U11).

---

## 3. Vendoring and licence constraints for a third-party MQTT library

### 3.1 The three policies in force

| Policy | Where stated | Rule |
|---|---|---|
| **Vendored, unmodified** (`ext/`) | CLAUDE.md hard rule; OR24.a (2); OR131.a; G6/R53; CLAUDE.md dependency-refresh bullet; `tests_scripts/test_vendored_freezefs.py` | "No edits, no restyling, ever (owner, 2026-09-25) — any behavior change needed is handled by wrapping/calling it from our own code"; changes only by re-vendoring "an unmodified upstream tag or commit" (freezefs precedent: no upstream tags, pinned by commit + SHA-256 per file); hash check in `tests_scripts`; upstream stubs vendored byte-identical; refreshed in every dependency refresh; "`src/` and `ext/` are copied flat into one directory and frozen together" |
| **Derived and restructured, attribution kept** (`src/`) | CLAUDE.md hard rule; SPEC F.4; THIRD_PARTY_LICENSES.md "Restructured/rewritten" | "Adafruit-derived driver code is fair game to restructure/rewrite (keeping attribution) (owner, 2026-07-13, `b64857d`)". THIRD_PARTY_LICENSES.md already extends this to non-Adafruit MIT sources: `asy_isl29125_driver.py` (jposada202020, "the same restructure-with-attribution treatment applies to the one non-Adafruit file"), `asy_ntp_client.py` (micropython-lib `ntptime.py`, MIT), `asy_dns_client.py` ("Inspired by vshymanskyy/aiodns (MIT), not a port") |
| **Literal port** | SPEC F.4 | Sensirion reference algorithm stays 1:1 — "(agent, 2026-07-21)", the named exception |

F.4's heading is "two opposite policies **by vendor**". No rule names an MQTT library or a generic "third-party
networking library" — **which policy applies is not decided** and is an owner question (6.3). Under OR2.c the
conservative default during execution would be to wrap, never edit — but see 3.2: wrapping cannot neutralise every
construct.

### 3.2 Would an unmodified MQTT library fit `ext/`? (checked against the two common candidates in the scratchpad)

Neither is in the stock Pico W image: at `v1.29.0` `ports/rp2/boards/RPI_PICO_W/manifest.py` requires only
`bundle-networking` and `aioble`, and `ports/rp2/boards/manifest.py` adds `onewire`, `ds18x20`, `dht`, `neopixel`;
micropython-lib's `bundle-networking` (master, fetched 2026-10-07) lists `mip`, `ntptime`, `ssl`, `requests`,
`webrepl`, `urequests` — no `umqtt`. `scripts/build_firmware.py:43` includes the board manifest unchanged, so an MQTT
library would have to be vendored or written.

| Construct in candidate (unmodified) | Rule it collides with |
|---|---|
| `mqtt_as/__init__.py` (Peter Hinch, MIT, `dd03ab3`, no tags): four module-level `gc.collect()` at import (`:15, :19, :23, :28`) and in run loops (`:876, :907`) | OR40.a (1)/CLAUDE.md "no `gc.collect()` calls … anywhere in the business logic"; I.4(e) stage proof. (`test_gc_collect_sites.py` scans only `src/` and codegen, so the gate would not catch it — a silent hole, not permission) |
| `mqtt_as` creates and drives `network.WLAN(STA_IF)` itself (`:191-192`, `connect(ssid, pw)` `:720-747`) | C.8 / G6/R25-R27: WLAN state is `WifiService`'s under `wifi_mode_lock` |
| `mqtt_as` `time.sleep(0.1)` loop (`:197`, ESP-NOW gateway path) | F.3 / L-BLOCK |
| `mqtt_as` connectivity probe `s.connect(("8.8.8.8", 53))` (`:406`) | B02 (probe declined), OR56.a (2) (no hard-coded DNS servers), G6/R49 (no probes) |
| `mqtt_as` `socket.getaddrinfo(self.server, self.port)` (`:790`); `umqtt.simple` the same (`simple.py:80`) | F.2 / F.9 "`getaddrinfo()` only on a numeric host" |
| `umqtt.simple`: blocking socket, `settimeout()` (`:79`), `setblocking(True)` (`:197`); `umqtt.robust`: `time.sleep(self.DELAY)` (`robust.py:10`) | F.3, OR31.a (would starve the WDT on a slow broker) |
| function-body imports (`mqtt_as` `import aioespnow`, `ssl`) | F.1 static-import rule (`test_import_placement.py` covers lint scopes only; OR142.a covers `ext/` for *dynamic* imports) |
| no type stubs in either package (`find … -name '*.pyi'`: none) | mypy `--strict` + `disallow_any_explicit` (OR81.a); OR131.a removed the `microdot` import ignores from `src/` — an untyped `ext/` import reintroduces them |
| no upstream tags (`mqtt_as`: `git tag` count 0) | allowed: CLAUDE.md "unmodified upstream tag **or commit**", freezefs precedent |
| unbounded inbound `remaining length` allocation (protocol allows 256 MB) | G6/R52, MEM.T03, OR143.a — must be bounded before allocation |

Conclusion: an unmodified vendored copy of either candidate cannot meet the binding rules by wrapping alone — the
import-time `gc.collect()` and the library's own WLAN/probe logic run inside the frozen image whatever our wrapper
does. A library whose blocking or WLAN paths are never *reached* through our wrapper may be defensible (Microdot is
used the same way: our code avoids its gaps), but import-time side effects are always reached. This is evidence for the
owner question, not a decision.

### 3.3 Licence compatibility

- Project `LICENSE`: MIT, "Copyright (c) 2026 hundertvolt". THIRD_PARTY_LICENSES.md: "MIT overall with that one
  documented exception" (Apache-2.0 `DNSQuery` portion).
- `mqtt_as`: MIT ("(C) Copyright Peter Hinch 2017-2025. Released under the MIT licence."; `LICENSE` © 2017 Peter
  Hinch). `umqtt.simple`/`.robust`: micropython-lib, MIT ("Copyright (c) 2013, 2014 micropython-lib contributors";
  manifest: "Originally written by Paul Sokolovsky"; micropython-lib's `LICENSE` says each module carries its own
  terms, MIT by default).
- MIT into MIT is compatible. Obligations the project already applies: licence text beside vendored code
  (`ext/LICENSE-microdot`, `ext/freezefs/LICENSE` pattern); an entry in THIRD_PARTY_LICENSES.md ("Vendored,
  unmodified" or "Restructured/rewritten, attribution retained"); SPDX/attribution header in a derived `src/` file;
  LIC.T08 checks headers ↔ doc both ways; LIC.T05 checks the frozen set against the doc; LIC.T06 notice duty if a UF2
  ever leaves the owner's hands (public MIT repo, OR52.a (7); none published today). An Apache-2.0 or LGPL/GPL
  library would change the "MIT overall" statement — avoid or ask.
- U34 (LIC, not started) rewrites THIRD_PARTY_LICENSES.md (LIC.S01-S07 seeds); an MQTT entry added now will be
  re-touched there.

### 3.4 Dependency-refresh duty

Whatever is adopted joins the "everything external" refresh (CLAUDE.md; OR129.a (2) scope list; LEAD/R33): changelog
and diff read at each refresh, workarounds listed in SPEC F.9 with their retirement trigger, pins stay pinned, a
hash-pin test like `test_vendored_freezefs.py`. A host-side test broker (Python package or `mosquitto`) is a new dev
or bench dependency: pinned `[dependency-groups] dev` entry (CLAUDE.md "nothing is installed by hand"), BACKLOG's
chroot-run list entry, and for the bench Pi the package check (OR50.a (3)).

---

## 4. How the audit's moving parts intersect an MQTT PoC

| Module the MQTT service depends on | Audit unit(s) | State | Pending changes that move the ground |
|---|---|---|---|
| `src/asy_wifi_service.py` (link state, `wifi_mode_lock`, `network_available_locked()`, `get_dns_server_ip()`) | U18 NET | not started | A.U18.33 one networking snapshot ("getters read it, never the radio"); A.U18.32 STA retry waits unlocked, poll stops at `STAT_GOT_IP`; A.U18.34 lock-hold table in SPEC C.8 with tests; A.U18.42 removes `wlan_isconnected()` (don't depend on it); A.U18.40 removes test-only constructor parameters; A.U18.24 timer re-arm; A.U18.28-.30 hotspot/deactivation behaviour |
| `src/asy_dns_client.py`, `asy_udp_socket.py` (broker resolution) | U18 | not started | A.U18.08-.10 (`DNSFallback` config value), .12 tuple-only address, .13 one connect attempt, .15 `finally` disconnect, .45 `resolve_ipv4()` loses `port=`, .18 UDP pcb budget text |
| `src/asy_ntp_client.py` (closest precedent to copy) | U18 | not started | A.U18.14-.26 (send failure logging, `Synced` staleness, settings change clears `Synced`, re-arm) |
| `src/asy_system_service.py` (supervisor, starters, `feed_watchdog()`, `reset_reason`) | U11 done; U20 stages | partly | U20 lands the system-command gate, controlled shutdown, feed ownership, `run_setups()`, generated `begin_boot()`/`boot_phase()`/`reset_reason=`, `config_stores=` (REGISTER U11 notes); LEAD/R32 "Reset to defaults"/"Erase FRAM" (U11/U16/U19/U20) — deletes every schema-backed `config_<name>.cfg`, so an MQTT config store is covered only if it is schema-backed |
| `src/asy_config_manager.py`, `asy_base_classes.py`, `asy_print_log.py`, `asy_api_response.py` | U2/U3/U4/U5/U10/U11 done | settled | use as-is: catalog (U2), central repeat rule (U3), `compare_before_write()` (U4), config objects/`max-args 8` (U5), `TickSeconds`/`utc_now()`/`LockedCounter` caps (U10), `ConfigFaults`, supervisor task (U11); SF-B3 `unpersisted` flag still staged U11/U20 |
| `src/asy_fram_manager.py` (logger chunk) | U16 STOR | not started | `FRAM_FULL`, `LOG_RAM_ONLY`, erase-FRAM, chunk-fit check per device (A.U20.11) |
| `src/asy_webserver_service.py` (MQTT settings GET/PUT, `/status`) | U19 REST | not started | A.U19.01 every PUT key answered; .05 typed static routes; .07 request-head guard; .10 `HTTPDropped`/`WifiTS`; .12 config GET holds the write lock; .15 one envelope catalog; .16 result-word constants; .18 Microdot hash pin; **.20 one route table + generated normative REST reference (LEAD/R08)**; .24 EAGAIN hammer |
| `buildgen/` (`buildspec.py`, `driver_registry.py` `_OVERRIDES`, `codegen.py`, `definitions.py`, `validate.py`), `devices/*.toml` | U20 GEN | not started (242 steps) | A.U20.06 generated `main()` restructure (setup list, task starts, timers, NTP; supervisor split); .07 boot sequence recorded and asserted per device; .11 FRAM chunk fit; .16/.41/.42 templates; .17 build errors name rule/place/fix; .19 TOMLs checked by `build_model()` + fuzz; .25 schema field without `@web` fails the build; .29 one TOML layout; .35 L.3 key table vs `buildspec.py`; .38 GET-key/logger-name collisions refused; .40 no variant names |
| `toolchain/versions.toml` `[lwip]`, `toolchain/micropython_overrides.py` | U21 TOOL | not started | modlwip `ERR_MEM` → `EAGAIN` override (OR114.a); ensemble checks; the lwIP stall is unfixed until then |
| `js/`, `html/` (settings page) | U6 done; U23 WEB | partial | definitions are generated from `@web` tags (U6); page rendering/placement checks U23 |
| tests (`tests/`, `tests_scripts/`, `digital_twin/`, `tests_hardware/`) | U24, U25, U26, U35 | not started | U25 moves twin scenarios host-side (OR125.a, M.TEST_HELP.033); U26 rewrites bench scripts; U35 interaction matrices (OR41.a), load tests (OR49.a), fault planting, cancel-at-each-await sweep |
| docs (SPEC C/K/H/N, CLAUDE.md, README, DEVICE_REFERENCE) | U29 SEC, U30 MEM, U31 PERF, U33/U36 DOC, U34 LIC | not started | threat-model statement (U29); C-stack budget LEAD/R06 (U30); budget table (U31); Design-principles Part, Part K → one ordered checklist, `integrate-module` skill M.DOCS.109 (U36) |

**How to avoid fighting the audit (agent recommendation, 2026-10-07):**
- Put the PoC in **new files only** (`src/asy_mqtt_client.py` or `asy_mqtt_service.py`, its unit tests, a host-side
  test broker) and consume existing public APIs read-only. The four hottest shared files — `asy_wifi_service.py`
  (U18), `asy_webserver_service.py` (U19), `buildgen/codegen.py` + `buildspec.py` + `devices/*.toml` (U20),
  `toolchain/versions.toml` `[lwip]` (U21) — are exactly where the pending 600+ steps land; an edit there now
  conflicts with work-order steps written against quoted text (REGISTER header: "every site is located by its quoted
  text").
- Do not depend on names U18 removes (`wlan_isconnected()`, `resolve_ipv4(port=)`, `conn_tries`), and expect the
  networking snapshot getter (A.U18.33) to become the way to read link state.
- Wire into buildgen only after U20, or keep any interim wiring minimal and additive (one `_OVERRIDES` entry like
  `notification`; a `dev`-only TOML opt-in).
- Never touch `PROJECT_AUDIT_PLAN.md`, `audit/` or the register (lease held by the audit session; plan 4.7 (4)).
  Never push to `main` (frozen). Follow the non-interference rules (REGISTER "Non-interference (A.U0.04)"): own
  worktree, own network namespace (`unshare -n`) for port-binding suites, `flock /tmp/sensors-audit-toolchain.lock`
  for firmware builds.
- Note doc drift seen on the way: plan 2.2/4.2/REST still say Microdot `v2.6.2`; CLAUDE.md and
  THIRD_PARTY_LICENSES.md say `v2.7.0` (re-vendored in U0R).

---

## 5. Prior intent: MQTT, push, home automation — and how data is consumed today

- **No prior MQTT intent anywhere.** `git grep -i` over the tree outside `legacy/` and `datasheets/` for
  `mqtt|broker|telemetry|influx|node-red|home assistant|iobroker|fhem` finds nothing in code, SPEC, README,
  DEVICE_REFERENCE, CLAUDE.md, BACKLOG or the audit apparatus. `git log --grep` cannot settle history (shallow clone,
  189 commits).
- **The only push-like intent: remote syslog.** BACKLOG.md:868-871: "SystemService's settings store grows with
  device-wide settings — the timezone offsets … future rsyslog settings … Owner-deferred goal (owner-confirmed,
  2026-08-11, `249f2ae`: 'per the owner's explicit intent, this is meant to grow into a general, module-independent
  system-settings store', paraphrase)". `audit/artefacts/ENV/history_trace.md:163` records it as "lost" in code
  ("rsyslog" has 0 hits, G9/R24).
- **Legacy never had MQTT or any push mechanism.** `legacy/firmware/` (MicroPython 1.24.1) has only the Microdot HTTP
  server, NTP/DNS over UDP and the captive DNS; its manifest is `include(RPI_PICO_W manifest)` + `freeze(".")`; no
  `umqtt`, `urequests` client use, outbound TCP connect, webhook or syslog.
- **Consumption today is pull: OpenHAB polls the REST API.** Owner's named load case, quoted in A.U19.21 from
  `5d47a8b` (2026-08-25): "an OpenHAB instance querying two endpoints and a full browser session in parallel" —
  implemented as `tests/_webserver_concurrency_scenarios.py:216-218` (`_openhab_poll()`: two concurrent GETs) and
  `:567-584` (`realistic_mixed_openhab_polling_and_browser_session_concurrently`, run for every device in the twin).
  OR89 (owner, 2026-09-29): "There is no typical openhab load case, this can always be subject to change. So it
  should withstand b)" → OR89.a (2): any client mix filling the whole ceiling. A.U26.64 (pending) adds an L4 bench
  scenario with two pollers on `GET /measurements` and `GET /status` (`l4.openhab_poll_interval_s`).
- Implication: an MQTT publisher would be a second consumer path beside REST polling. The REST contract (6
  connections, any mix) stays binding regardless.

---

## 6. Owner questions the MQTT PoC must raise

Format per CLAUDE.md's decision-record rule (4): numbered, decision ≤ 10 words, options each with its consequence,
effects per device and bus. "Bus" here: no I2C/SPI/UART bus is touched by any option; effects are on WiFi/lwIP, the
heap and the flash filesystem.

1. **MQTT: new feature beyond feature parity, or PoC only?**
   (a) New feature with its own owner row — CLAUDE.md's "same top-level features" goal gains a named exception;
   every device can opt in through its TOML; full Part K/L0-L4 bar applies.
   (b) PoC only, never in a shipped image — no device's frozen size, heap or lwIP budget changes; the code may live
   off-image or `dev`-only.

2. **Where does the MQTT work merge, relative to the audit?**
   (a) Separate branch, merged after the audit closes — no audit unit changes; the PoC rebases over U15-U37 (U18
   WiFi, U19 webserver, U20 buildgen rewrites) and no device carries MQTT until then.
   (b) Into the audit branch as a new owner row and unit after U21 — it lands on final shapes and is covered by U24-
   U36's test and doc passes; adds scope to every remaining unit for devices that opt in.
   (c) Into the audit branch now — collides with pending U18-U21 steps on the same files; the work order would need
   re-derivation.

3. **Third-party MQTT library: vendor unmodified, derive, or write?**
   (a) Vendor unmodified in `ext/` (Microdot policy) — hash-pinned and refreshed with all dependencies; candidates
   carry import-time `gc.collect()`, their own WLAN control, blocking `getaddrinfo()`/`time.sleep()`, which wrapping
   cannot remove; affects every device that opts in.
   (b) Derive into `src/` with attribution (ISL29125/NTP precedent) — full Part C/D/G bar, own tests at every level,
   no foreign behaviour in the image; THIRD_PARTY_LICENSES.md "restructured" entry.
   (c) Write a minimal MQTT 3.1.1 client in `src/` — no third-party notice; the OASIS spec is the primary source
   (P11); most code to write and test.

4. **May MQTT messages change configuration or run commands?**
   (a) Publish only (plus subscribe without writes) — SPEC F.2's "every flash write … only through the REST PUT path"
   and the WiFi power-cycle safety argument stay true on every device.
   (b) Subscribe may write settings through `compare_before_write()` — a second flash-write trigger; F.2, CLAUDE.md
   and harmonization 37 are reworded; retained messages re-delivered at each reconnect must answer "Unchanged" (no
   wear).
   (c) Also system commands (reboot, bootloader, reset to defaults, erase FRAM) — any LAN publisher can take a device
   offline until physical intervention (bootloader); accepted only under the trusted-LAN model.

5. **Who pays the MQTT connection's heap and lwIP share?**
   (a) Add it on top of `max_connections` 6 — `MEMP_NUM_TCP_PCB`, `MEM_SIZE` and `MEMP_NUM_TCP_SEG` grow for opting
   devices (≈2.3 KB GC heap plus client buffers); measured peak free heap (~21 %) moves toward the 7-connection
   profile (~14 %), so a bench re-measure is owed per opting device.
   (b) Lower `max_connections` to 5 on opting devices — keeps the measured headroom; one fewer simultaneous web client
   (OpenHAB's two pollers plus one browser tab still fit).
   (c) Count MQTT against the existing spares — no build change; a closing-pcb burst can exhaust the pool and reset
   new web connections inside lwIP on opting devices.

6. **Broker transport: plain TCP or TLS?**
   (a) Plain TCP 1883 under the trusted-LAN model — no mbedTLS session heap; consistent with unauthenticated REST.
   (b) TLS 8883 — tens of KB of heap per session against ~40 KB free at peak; likely forces (5)(b) or fewer web
   connections on every opting device.

7. **Broker credentials: stored and shown like the WiFi password?**
   (a) Yes — plain in the module's config file, never disclosed on GET, mask PUT stores like any value (G6/R29,
   OR104.a); same exposure as WiFi `PW` over USB-REPL.
   (b) No credentials (anonymous broker only) — no secret on any device; the broker must allow anonymous LAN clients.

8. **Topic and payload scheme: mirror the REST keys?**
   (a) Mirror `/measurements` (and `/status`) keys and JSON per module — one key scheme (OR58.a), one normative
   reference with the REST API (LEAD/R08), frozen at the release.
   (b) Own flat topic per value — easier for OpenHAB channels; a second contract with its own conformance test and
   freeze.

9. **May MQTT keepalive loss trigger WiFi recovery?**
   (a) No — a broker outage is a remote fault, retried on backoff, never escalates (A.U18.47); the CYW43 false
   positive keeps its power-cycle recovery (B02) on every device.
   (b) Yes — the keepalive becomes the reachability probe declined on 2026-09-04/09-26; reopens B02 with a changed
   premise (the probe would already exist); every opting device can restart its radio on a broker outage.

10. **Test broker for L2 and L4: which one?**
    (a) A pinned Python broker as a `dev` dependency, run host-side (E.9) on a port-0 listener — runs in CI and the
        twin; one more pinned dependency in the refresh.
    (b) `mosquitto` from apt on CI and the bench Pi — closest to a real deployment; adds an apt package to the
        toolchain list, the chroot check and the bench package check (OR50.a (3)).
    (c) A minimal in-repo fake broker — no new dependency; fidelity limited to what the fake models (a twin fidelity
        row).

---

## 7. Checklist distilled for the PoC (agent reading of the rules above, 2026-10-07)

- Module `src/asy_mqtt_<client|service>.py`, class `MQTTClient`/`MQTTService`; config object(s), ≤ 8 args, no test
  seams; one `make_logger()` with `LogConfig`, FRAM-wired by TOML; catalog range in C.7.1; `@tunable` + Part N rows
  for keepalive, backoff base/cap, connect timeout, max inbound packet, publish interval; `@web` tags for every
  setting and status value; settings on the Networking page.
- One supervised task from `get_task_starters()`; no extra `create_task()` unless added to C.9's table; no
  `machine.Timer` unless needed (then soft, flag-only callback, `PERIODIC` if must-fire, `(MemoryError, OSError)`
  catch); 1 s ticks via `TickSeconds`, timestamps via `utc_now()`.
- Gate on STA link (`network_available_locked()` under a brief `wifi_mode_lock`, or the U18 snapshot getter); idle in
  hotspot/deactivated; never touch WLAN; never hold the lock across I/O.
- Resolve with `resolve_ipv4()`; connect with a numeric IP under `asyncio.wait_for_ms`; non-blocking stream I/O with
  per-call timeouts; cap inbound remaining-length before allocating; preallocate fixed buffers at setup (boot batch
  placement); validate before `struct.pack()`.
- Broker unreachable/refused/garbage → log once (repeat rule), count (capped ≤ 2**30 − 1, check-before-step), capped
  exponential backoff never zero, reset on success; task ends only for a local fault after the re-create/re-arm rung;
  never feeds the WDT; cancellation-safe (`finally`, re-raise `CancelledError`).
- Tests: L1 unit (bounded fakes, both GC stages, zero memory markers), L2 twin with a host-side broker (E.9, port 0),
  L4 bench counterpart or a listed E.6.6 exception; hazard coverage for sockets, heap, config file, FRAM, locks across
  all four tiers (CLAUDE.md); interaction rows vs REST at the full ceiling (OR89.a), WiFi reconnect/mode switch, NTP;
  load test with recovery to baseline (OR49.a); broker that stops reading (modlwip stall, OR115.a); fault planting.
- Docs: SPEC C/C.7.1/C.8/C.9/H/N, DEVICE_REFERENCE operator actions (LEAD/R14), THIRD_PARTY_LICENSES.md if derived or
  vendored, README "Further reading" if a doc is added; bird's-eye `src/` scan on adding the file.
