# Do-not-reopen index (DOC.T14)

Decided matters an auditor must not re-argue; a finding may only say that the repo text still owes its correction. Built
from `audit/DECISION_PROVENANCE.md` (the 263 decisions, lists A-E answered by OR68-OR73, section 4 by its OR rows, section
5 by OR71.a (0)) and owner rows OR54-OR73 (PROJECT_AUDIT_PLAN.md 3.2). Later rows are used only to drop or re-tag an
entry and are named where they do. Foreclosure words ("don't re-propose", "settled", "never") are not carried: this index
is the foreclosure. Actor is the source of the decision as answered; a date is the owner's or the introducing commit's.
Sites: SPEC SPECIFICATION.md, CL CLAUDE.md, BL BACKLOG.md, THR tests_hardware/README.md, DTR digital_twin/README.md, UCL
UART_C_PORT_CHANGELOG.md, DR DEVICE_REFERENCE.md, HFM HEAP_FRAGMENTATION_MEASUREMENTS.md, DLR dev_legacy/README.md; line
numbers are DECISION_PROVENANCE's (pre-audit), so locate by text.

## 1 Owner rows OR54-OR73 not already a provenance entry

| Row | Decision | Actor, date | Correction owed |
|---|---|---|---|
| OR54.a (1) | Every website tier (device list, site build, mock and live backends, cross-browser) derives its device set from `devices/*.toml`; no tier names a device | owner, 2026-09-26 | B1 one-source website definitions change |
| OR55.a | `gc.collect()` is synchronous and complete on return; a test may read the heap in the next statement; a collection never sits inside a timed or watchdog-sensitive window | owner + fact (`v1.29.0` source), 2026-09-26 | replaces OR39.a (1)'s "don't measure in the next line" wherever stated |
| OR56.a (1) | One event, one persisted entry: an error or a warning, never both, never two of one kind | owner, 2026-09-26 | every `err_s`/`wrn_s` pair in `src/` and the generated code; UART fault `errno` + resync `wrnno`; read `errno` 11 + streak `errno` 1 (`base_classes.py:223`) |
| OR56.a (2) | `_FALLBACK_DNS_SERVERS` becomes a website-visible, user-changeable, emptyable config value with today's servers as default | owner, 2026-09-26 | `asy_dns_client.py:20` hard-coded list goes |
| OR57.a | Legacy parity is with legacy's evident intent; a legacy bug defeating its intent is a legacy defect, never a behaviour to keep | owner, 2026-09-26 | every legacy comparison read this way |
| OR58.a | The refactor's API is the only reference; no legacy REST path is restored; key names follow one scheme before the release, harmonised with every consumer | owner, 2026-09-26 | SPEC C.5.3's live `/net/cmd`/`/led/cmd` text; legacy-derived key spellings |
| OR59.a | The reflash runbook erases the filesystem every time; the generated boot puts `.frozen` ahead of `''` and `/lib` on `sys.path` before any product import | owner, 2026-09-26 | runbook; generated boot line with its buildgen and shadowing tests |
| OR60.a | Intended resets are marked in `machine.mem_backup()` region 0 and published as a numeric `reset_reason` in `/status`; FRAM is not used for it | owner, 2026-09-26 | `SystemService`, SPEC code table, twin `mem_backup()` fake (also V43) |
| OR61.a (1) | Every legacy unit runs MicroPython 1.24.1 | owner, 2026-09-26 | "1.26" in CL platform target and `_boot.py` rule, BL, SPEC Part F, runbook (also V05, V06) |
| OR61.a (2) | "Field", "fielded", "deployed" mean the owner's own units with full access; no requirement rests on units being out of reach | owner, 2026-09-26 | wording wherever a requirement leans on an unreachable fleet (also V03, A01, A05) |
| OR63.a | Codecov uploads and every mention go; coverage stays in the Job Summary and the HTML artifact, advisory | owner, 2026-09-26 | `ci.yml:525-540`, `zizmor.yml` comment, README.md:193, SPEC E.5, :877, :925, CL "Code quality tooling" |
| OR64.a, OR65.a | SGP40's general-call reset (0x06 to 0x00, NAK tolerated) as implemented stays: the owner's accepted risk; no replacement mechanism | owner, 2026-09-26 | SPEC C.8 "(owner, 2026-09-26)", parked clause dropped (V55); the (2) boundary is re-read by OR113.a (smallest-blast-radius recovery) |
| OR66.a, OR67.a | SGP40 compensation: a wired source that is unavailable skips the read; with no live source a constant (25 °C / 50 %RH unless the TOML sets one) stated explicitly as `{default = true}`; both `@value-wiring` tags stay `required` | owner, 2026-09-26 | SPEC A.4 :276-278 and its CL/SPEC mirrors (DECISION_PROVENANCE's "tags become optional" is overtaken by OR67.a) |
| OR68.a (4) | The five prevention rules: actor and date on every decision; owner words and question quoted; no meaning change in compaction; one BACKLOG owner-question list, no temporary-plan citations; a `tests_scripts` check on actorless vocabulary and dead citations | owner, 2026-09-26 | CL working agreements in B0; the check with its shrinking allow-list (A.U0.08) |

## 2 List A — owner tag at introduction, confirmed in bulk (OR68.a (1), 2026-09-26)

Correction owed by every row: "(owner, date)" in its text at its sites; the column adds only what more is owed.

| ID | Decision | Actor, date | Correction owed |
|---|---|---|---|
| A01 | The UART C peer is prototypical; no device in the field runs it | owner, 2026-09-11 | read "field" per OR61.a (2) |
| A02 | The Python side may lead a UART wire flag-day; CRC_Pass is the interim | owner, 2026-09-11 | CL:127-129 states it (V02) |
| A03 | The UART module is standalone; the BME688/BSEC use case is out of scope; no sensor behind the link | owner, 2026-08-20 / 2026-09-11 | — |
| A04 | Part J's protocol facts as established with the owner; simultaneous initiation out of contract | owner, 2026-09-11 | one tag over J.1-J.9 as a whole |
| A05 | wozi is never flashed; only dev is; a dev-native bench result counts for wozi | owner, 2026-09-03 | README "5 units deployed" reframed (OR61.a); the bench board named by data, not a literal (OR78.a) |
| A06 | dev carries two UART instances | owner, 2026-09-11 | the "untestable peripheral" reason and the wozi prohibition are labelled the agent's |
| A07 | The timeout/cancellation mechanism is prioritized | owner, 2026-09-11 | BL:58-67 gets a closure state (OR5); its getaddrinfo half is C04 |
| A08 | Adafruit-derived driver code may be restructured, attribution kept | owner, 2026-07-13 | — |
| A09 | Boot latency is not a metric; the setup batch is not trimmed or reordered for speed | owner, 2026-09-16 (WP6 background) | — |
| A10 | The FRAM busy-marker lockout after an interrupted read is intended | owner, 2026-09-10 | — |
| A11 | FRAM write protection also gates reads, intended | owner, 2026-09-11 | cite by content, not "#13" |
| A12 | FRAM capacity is checked via mpremote only; no errno/wrnno or `/status` field for it | owner (quoted), 2026-09-16 | — |
| A13 | SPEC A.4 "confirmed intentional" behaviours (LED sequencing, BackupPeriod 0, WiFi deactivation, numbers-only UI, FRAM headroom) | owner, 2026-07-13 | SGP40 bullet rewritten per OR66.a; bullets added later (C03) do not inherit the tag |
| A14 | ForceCalRef recalibration is manual | owner, 2026-08-11 | restore the tag (SPEC:241-242) |
| A15 | SCD30 "not ready" keeps cached values (legacy behaviour) | owner, 2026-07-22 | — |
| A16 | Real SCD30 NVM writes are opt-in, one per session, AND-gated | owner, 2026-09-16 | narrowed to owned writes (OR90.a); budget rechecked under OR42.c (4) |
| A17 | Generated bus-hazard coverage is required | owner, 2026-09-15 | — |
| A18 | The heap-floor thresholds (100,000 / 80,000 B) are retired | owner, 2026-09-19 | replacement thresholds labelled the agent's |
| A19 | UID 0xFF stays out of the UID space | owner, 2026-09-11 | "(owner, 2026-09-11)" replaces "author-confirmed" |
| A20 | The UART driver/comm never block the asyncio loop, not even waiting | owner, 2026-09-11 | the `poll_idle_ms` extension labelled the agent's |
| A21 | A lost final ACK is folded into failure | owner, 2026-09-11 | tag replaces "by decision" (`tests/test_asy_uart_comm.py:704`) |
| A22 | SGP40 feature-set check removed; serial read + self-test gate success; 100 ms delay | owner, 2026-07-21 | merge the two comment reasons (`asy_sgp40_driver.py:670-671`) |
| A23 | Visual/mechanics layering; the REST API is stable long-term | owner, 2026-08-21 | restore the tag; "stable" read with OR58.a/OR52.a (2) |
| A24 | The UI cannot set an empty string | owner, 2026-08-22 | restore the tag (SPEC:4382) |
| A25 | Dark mode follows the OS; no toggle | owner, 2026-08-21 | — |
| A26 | A revealed errcount history shows without a second click | owner, 2026-08-21 | "session 2" becomes the date |
| A27 | No pagination or truncation of error history | owner, 2026-08-21 | — |
| A28 | Error `type` is never shown as text, only colours `num` | owner, 2026-08-21 | — |
| A29 | `max_connections` is 6 | owner, 2026-09-24 | — |
| A30 | The recommended connection ceiling ships on every device | owner, 2026-09-22 | the value is the agent's sweep; lwIP half not silicon-validated |
| A31 | Exceeding `max_connections` rejects only the new arrival | owner, 2026-08-25 | — |
| A32 | A reset before any response at the ceiling is a refusal, expected | owner, 2026-09-23 | — |
| A33 | Frozen-port twins (64- and 32-bit) are ad-hoc instruments, never committed or CI-gated | owner (quoted), 2026-09-23 | tag at SPEC:4622; both widths (OR89.a (3)) |
| A34 | Four heap research gaps closed; reopened only on a new symptom | owner, 2026-09-24 | — |
| A35 | The W5 health check is fixed in the test | owner, 2026-09-19 | — |
| A36 | SPEC M.1.1, the owner's ISL29125 requirement list | owner, 2026-09-12 | later edits are B10-B12; requirement 18 is a wiring fact (OR74.a) |
| A37 | ISL29125 W12 retired; saturation is the output field Overrange (requirement 21) | owner, 2026-09-15 | restore "added later, not one of the original twenty" |
| A38 | Gain-ratio calibration is user-started, bounded, never self-applied | owner, 2026-09-13 | — |
| A39 | ISL29125 PUT /sensors divergence is high importance | owner, 2026-09-15 | the tag covers the PUT /sensors half only |
| A40 | No bench-rig hardware will be bought | owner, 2026-09-22 | "don't re-propose", "permanently [MANUAL]" labelled the agent's |
| A41 | Bench sittings spend flash/NVM writes only after a clean default run | owner, 2026-09-22 | — |
| A42 | R13 needs hardware the bench does not have | owner, 2026-09-25 | — |
| A43 | Credential rotation is not a bench capability | owner, 2026-09-22 | — |
| A44 | All build scripts are under the full CI | owner (quoted), 2026-09-10 | — |
| A45 | The chroot verification is an owner-run periodic check, not a gate | owner, 2026-09-18 | — |
| A46 | Proactive PR creation is authorised | owner, 2026-07-13 | — |
| A47 | `[device]` name/hostname/hotspot_password are wired into the boot path | owner, 2026-09-18 | — |
| A48 | Soft-timer drop: no software-timeout mitigation | owner, 2026-07-18 | restore the tag (SPEC:3465-3467) |
| A49 | Permanent WLAN deactivation is a safety feature and survives task restarts | owner, 2026-07-13 / 2026-08-11 | — |
| A50 | The uptime timer degrades on ENOMEM instead of rebooting | owner, 2026-07-18 | — |
| A51 | Recombination timing tests | owner, 2026-09-04 | — |
| A52 | `/measurements` and `/sensors` are the streaming candidates | owner (quoted), 2026-09-07 | — |

## 3 List A2 — answered by OR68.a (2) and OR69.a

| ID | Decision | Actor, date | Correction owed |
|---|---|---|---|
| A2-01 | An abrupt reset mid-write may lose a module's whole FRAM error history; all-or-nothing, never partial; a commanded reboot loses nothing | owner, 2026-09-26 (OR69.a (1)) | SPEC A.4 :189-198 with the date |
| A2-02 | L.1's "exactly one association per driver" yields to A2-03 (most recent owner decision) | owner, 2026-09-18 (OR68.a (2)) | L.1 criterion 1 names the one table edit per new driver |
| A2-03 | The buildspec schema stays hand-maintained | owner, 2026-09-18 (OR68.a (2)) | SPEC:6560-6566 and BL:652-658 agree |
| A2-04 | `write_config()` coordination is the WP5 deferred flush (`9ac59cf`) | owner, 2026-09-16 (OR68.a (2)) | BL:167-173 drops "fast enough not to matter" |
| A2-05 | The supervisor counter's decay stays intended | owner, 2026-07-13 (OR68.a (2), OR18.a) | — |
| A2-06 | Soak stays a dedicated opt-in run on top of the bench tier; OR45.a's levels exclude it | owner, 2026-09-04 (OR68.a (2)) | — |
| A2-07 | `FiltCoeff` keeps both meanings (BMP3xx IIR index, ISL29125 EMA coefficient), namespaced per sensor | owner, 2026-09-26 (OR69.a (2)) | the "deployed units" reason is replaced (BL:478-480) |

## 4 List B — owner words widened; answered by OR70.a and OR71.a

| ID | Decision | Actor, date | Correction owed |
|---|---|---|---|
| B01 | The shared hotspot fallback password is accepted permanently, a known limitation under the trusted-LAN threat model | owner, 2026-09-26 (OR70.a (1)) | CL, SPEC :6053/:6136, `asy_wifi_service.py:50-52`, `pyproject.toml:233` say so with the date |
| B02 | A reachability probe is not worth its complexity; power-cycle recovery stays | owner, 2026-09-04 (`655e4f9`), 2026-09-26 (OR70.a (2)) | drop "intended recovery feature, don't propose"; THR:625-641 "not decided here" updated; "current state, backstopped" (OR89.a (4)) |
| B03 | The SCD30 driver never starts continuous measurement itself; the first ambient-pressure PUT does. Firmware never writes a limited-endurance store without a user/API action (FRAM outside); config repair at most one write per boot | owner, 2026-09-26 (OR70.a (3), OR71.a (2)) | state the rule; fix the dangling CL pointer (`asy_scd30_driver.py:162-163`); first-boot clause superseded by OR136.a |
| B04 | Real-hardware write constraints: (a) NVM budget is CL's owner wear rule (2026-09-17); (b) protocol-layer construction, no flash-FS I/O (`7c8dbbc`) | owner, 2026-09-17 / 2026-09-03 (OR70.a, actor corrected 2026-09-29) | SPEC:2107-2111 tags each with its source |
| B05 | `test_bus_hazard_multi_device.py` is the permanent home for generic hazard shapes | owner, 2026-09-15 (OR71.a, from facts) | its tests take OR33.a necessity verdicts one by one; "never retired" goes |
| B07 | The UART error-32 blind spot is fixed: bytes discarded on a short-frame timeout count toward `_resync()`'s drained total | owner, 2026-09-26 (OR70.a (5)) | SPEC:5507, UCL:97, `tests/test_uart_comm_hazard.py:856`; tests L1/L2; UCL entry Python-internal |
| B08 | A `ResetErrors` whose `_write()` reports a detected failure answers "Failed" for that field; an acknowledged write stays trusted | owner, 2026-09-26 (OR70.a (6)) | SPEC:1840-1848 |
| B09 | `ResetErrors` stays global only, permanently | owner, 2026-09-26 (OR70.a (7)) | "for now" and the actorless "decision" go (`tests/test_asy_webserver_service.py:1052`) |
| B10 | ISL29125 HSB low-light behaviour accepted as is | owner, 2026-09-12 | "Settled; do not re-propose either" goes (agent-derived, OR71.a (3)) |
| B11 | ISL29125 item rulings (AutoRangePersist leaves the API, 2026-09-13/14) | owner, 2026-09-13/14 | the general "derived, never exposed" rule is labelled agent-derived, open to change (OR71.a (3)) |
| B12 | ISL29125 requirement 1: every setting API-settable and persisted | owner, 2026-09-12 | "device and maths constants are not settings" labelled agent-derived (OR71.a (3)) |
| B13 | wozi's firmware on dev hardware is an invalid test; wozi never runs on dev | owner, 2026-09-03 (OR70.a (8)) | DLR:620-632 drops "not a real bug … isn't tracked"; phase C dev-native runs cover the shared bus |
| B14 | The step-session workflow is the audit's: research first, owner questions only at requirement recording and consolidation, tests first, pause = sync point, no owner stop-points inside a unit | owner, 2026-09-26 (OR71.a (1)) | CL:449-462 rewritten |
| B15 | No version or capability negotiation, now or at the C reconciliation | owner, 2026-09-11, confirmed 2026-09-26 (OR70.a (10)) | tag both clauses (CL:138-140, SPEC:5501-5502) |

## 5 List C — no owner trace; answered by OR68.a-OR72.a

| ID | Decision | Actor, date | Correction owed |
|---|---|---|---|
| C01 | A power loss between a PUT's response and its deferred flash write may lose that change silently; the write never corrupts | owner, 2026-09-26 (OR69.a (3)) | SPEC F.2 :3653-3657, `buildgen/codegen.py:502-503`, `tests/_sensortask_scenarios.py:967` |
| C02 | SCD30's data-ready read may coincide with other reads on its bus; outside OR47.a's spacing | owner, 2026-09-26 (OR69.a (5)) | SPEC:2286-2298 tag replaces "not a defect" |
| C03 | The notification window may span midnight (`OnH` > `OffH`), legacy's intent | owner, 2026-09-26 (OR69.a (6)) | product change with L1/L2 tests and website; SPEC:280-283 leaves the owner list |
| C04 | Stale: `socket.getaddrinfo()` is no longer in `src/` | owner, 2026-09-26 (OR68.a (2)) | CL:193-196's getaddrinfo half goes; backstopped calls are current state (OR89.a (4)) |
| C05 | The refactor stays pinned to a chosen MicroPython version and moves only on the owner's call | owner, 2026-09-26 (OR69.a (9)) | SPEC:3441-3442 reworded |
| C06 | A device's TOML decides its sensors | owner, 2026-09-26 (OR71.a (4)) | DR:100-101 drops "and never will" |
| C07 | The watchdog is hardcoded at a uniform 8000 ms ("must be hardcoded so no error ever can circumvent it"); "flashing out of scope" states the build scheme's scope | owner, 2026-08-11 (FINAL_WIRING_PLAN Step 1), 2026-09-26 (OR70.a) | SPEC:6039-6040 tag and source |
| C08 | DHCP-client faults are a documented known limitation | owner, 2026-09-26 (OR71.a (5)) | THR:828-837, `test_network_resilience.py:3` |
| C10 | Free heap (`gc.mem_free()`) becomes a `/status` field | owner, 2026-09-26 (OR71.a (7)) | SPEC:3790-3791 "deliberately not exposed" goes; OR43.a inventory |
| C11 | Legacy BSEC `rxbuf` 32 concerns the out-of-scope BSEC use (A03) | agent, 2026-09-13 (`c0638bc`; OR70.a) | relabel as agent design (`tests/test_asy_uart_comm.py:2159`) |
| C14 | `res` is "OK" when the request was processed; non-"OK" means a broken request; content outcomes are per field (Valid/Invalid/Failed/Unchanged) | owner, 2026-09-26 (OR69.a (4)) | SPEC A.8/C and the nine test sites, with the owner's reason; "Final project decision" goes |
| C15 | A live-readback `GET /sensors` reads a module's fields in one step | owner, 2026-09-26 (OR71.a (8)) | the characterization test (`tests/test_asy_webserver_service.py:1108-1137`) becomes a consistency test |
| C16 | An integer for a float field is coerced (`config_manager.py:163-164`) | fact, 2026-09-26 (OR71.a) | README.md:611-613 corrected |
| C17 | A connection counts until it has closed; ~70 % refusals of back-to-back clients at the limit stay expected | owner, 2026-09-26 (OR69.a (8)) | SPEC:4610 tag |
| C18 | A dead-man's switch is armed before any destructive bench-network change | owner, 2026-09-26 (OR72.a (9)) | CL:295-301, SPEC:1027-1030 tag |
| C19 | dev's generated config is held to the same standard as every device | owner, 2026-09-26 (OR72.a (10)) | CL:156-158, BL:865-866 "dev quirks are not bugs" goes |

## 6 List D — parked questions; answered by OR72.a

| ID | Decision | Actor, date | Correction owed |
|---|---|---|---|
| D01 F18 | Four zero-think-time readers are a degradation check only (no crash, reboot, task end or MemoryError marker; full recovery); writer starvation under it is accepted; no admission fairness | owner, 2026-09-26 (OR72.a (1)), confirmed 2026-09-28 (OR83.a (2)) | BL:381-392 parked text replaced |
| D01 T4 | The FRAM per-command loop hold (~3 ms per 1-byte write) stays | owner, 2026-09-26 (OR72.a (2)) | BL:450-461, SPEC:4009-4016 parked text replaced |
| D01 W3 | The 256 B response pieces and their +17 % on `/status` are the price of SPEC I.3's bound | owner, 2026-09-26 (OR72.a (3)) | as above |
| D01 T1 | Closed on the flash-tier figure; `test_memory_stress.py` echoes its `GC_THRESHOLD` | owner, 2026-09-26 (OR72.a (4)) | as above |
| D02 | `ResetErrors` resets the FRAM-backed logs concurrently; then a bench time budget is set | owner, 2026-09-26 (OR72.a (5)) | BL:318-327; `tests_hardware/error_log_helpers.py` |
| D03 | No hotspot phase field; the indirect check stays | owner, 2026-09-26 (OR72.a (6)) | "put to the owner" goes (`test_hotspot_role_reversal.py:426`) |
| D04 | The littlefs resize (SPEC B.14.3) is dropped until flash space is short | owner, 2026-09-26 (OR72.a (7)) | SPEC:1390-1393 |
| D05 | The DNS server's error history is shown with the networking data | owner, 2026-09-26 (OR72.a (8)) | `asy_wifi_service.py:168-169`; OR43.a inventory |

## 7 List E — pointers into deleted plans, text recovered

| ID | Decision | Actor, date | Correction owed |
|---|---|---|---|
| E01 | Only the FRAM module never has its own FRAM logging; every other module has it optionally | owner (quoted), 2026-09-16 | SPEC:392-394 "Topic 11" becomes the tag and the short quote |
| E02 | The project targets the Raspberry Pi Pico W (RP2040 + CYW43439) only | owner, 2026-09-26 (OR73.a) | SPEC:6522-6523 "(owner, 2026-09-26)" replaces "(project owner confirmed, §6.5)" |
| E03 | Website brief (WEBSITE_PLAN §1/§3) and the visual/mechanics separation (§12) | owner, 2026-08-21 | tag those H.4 rows; "versus legacy" read under OR58.a |
| E05 | Capacity rejection is a silent close, no 503; `Connection: close` per the protocol spec | owner, 2026-08-12 | `asy_webserver_service.py:112-113, 123-124, 387, 698`: SPEC references and tags replace "decision 3/6/7"; decision 6's reason labelled the agent's |
| E06 | A webserver timeout is logged as a warning | owner (quoted), 2026-08-12 | quote and date in SPEC A.8; "decision 8" goes (`tests/test_asy_webserver_service.py:1069`) |
| E07 | Watchdog escalation is both asserted (`would_have_triggered_count == 0`) and observable on a manual run | owner, 2026-08-13 | cite by content and date (`tests/test_digital_twin_sensortask_integration.py:421`) |
| E08 | The middle integration tier is built | owner (quoted), 2026-08-13 | restore the quote or drop "decision 10" (`tests/_digital_twin_construction_scenarios.py:165`) |
| E09 | Twin FRAM state persists by default for the manual entry point, written on explicit shutdown; automated tests use ephemeral paths | owner, 2026-08-13 | `.gitignore:75-76` names the retired `run_wozi_integration.py` |

## 8 Section 4 — decided by an OR row

| ID | Decision | Actor, date | Correction owed |
|---|---|---|---|
| V01 | `arduino/` and the C reconciliation are post-audit work | owner, 2026-09-25 (OR5.a (3), OR11.a) | CL:123-126, SPEC:38-39, 5342-5344, BL:481-483, README:697-698 say "post-audit only" |
| V02 | The UART wire format is frozen for the audit; Python may lead a wire change (A02) | owner, 2026-09-25 (OR24.a (2), OR5.a (3)) | CL:118-129 agrees with UCL |
| V03 | The owner holds every unit; hardware parity is not "structurally impossible" | owner, 2026-09-26 (OR61.a) | SPEC:3209-3213 |
| V04 | The legacy tree moves to `legacy/` and may run in scratch as a reference oracle | owner, 2026-09-25/26 (OR32.a, OR52) | CL:170-183, SPEC:911-912, `scripts/lint.sh:15`; SPEC B.9/B.11 drop legacy build work |
| V05 | `modules/_boot.py`'s dotted import is not changed (rule kept, new path) | owner, 2026-09-25/26 (OR32.a (4), OR61.a (1)) | 1.26 → 1.24.1 (CL:92-100, BL:142-151) |
| V06 | Legacy units run 1.24.1; no migration, a reflash runbook | owner, 2026-09-26 (OR61.a, OR52.a (1)) | BL:160-162, SPEC:3686 |
| V07 | Vendored Microdot is never edited | owner, 2026-09-25 (OR24.a (2)) | — |
| V08 | A wedged I2C chip keeps the hardware-watchdog backstop until a reliable non-blocking alternative exists | owner, 2026-09-25 (OR18.a), 2026-09-29 (OR89.a (4)) | SPEC:3606-3608 "current state, backstopped"; the getaddrinfo half is C04 |
| V09 | No blanket MemoryError wrapping; a gap is closed where a real graceful-degradation alternative exists | owner, 2026-09-25 (OR26.a) | CL:204-206, SPEC:3614-3615, 5005-5008 and I.4(a) take that criterion |
| V10 | The boot `setup()` batch is not staggered | owner, 2026-09-25/26 (OR31.a (2), OR47.a (1)) | — |
| V11 | Read timers share a t0 and keep a minimum separation within one second | owner, 2026-09-26 (OR47.a (3)) | SPEC:2226-2237 |
| V12 | The FRAM chunk layout is fixed only within one firmware build | owner, 2026-09-26 (OR56.a (3), OR47.a (2)) | SPEC:215-217, 378-379, 486, 2521-2523; `tests/test_asy_fram_manager.py:90` |
| V13 | No module may insist on FRAM | owner, 2026-09-26 (OR60) | — |
| V14 | FRAM `verify_present()`/`set_write_protected()` stay | owner, 2026-09-26 (OR36.a (3)) | — |
| V15 | FRAM leftovers are never wiped automatically; errcount is read and saved first | owner, 2026-09-26 (OR38.a (4)) | THR:481-485 "Residue is the accepted outcome" goes |
| V16 | FRAM error logs are read before any `ResetErrors` | owner, 2026-09-26 (OR38.a (4), OR28.a (1)) | — |
| V17 | The new API is the reference; no "accepted debt" toward `html_raw/` | owner, 2026-09-26 (OR58.a) | SPEC:264-265, 1799-1801; dangling CL pointer at `asy_notification_service.py:68-70` |
| V18 | SCD30 AmbPres is static | owner, 2026-09-26 (OR42.c (2)) | SPEC:237-240's force=True fact is wrong: code follows OR42.c |
| V19 | SCD30 NVM setters compare before write | owner, 2026-09-26 (OR42.a-c) | BL:910-913 "safe today" goes |
| V20 | The wear gate covers the write a test owns, not a prerequisite | owner, 2026-09-18 (OR45.a (3), OR49.a) | — |
| V21 | No avoidable wear, host SSD included | owner, 2026-09-17 (OR37.a, OR49.a) | CL:249-283 adds "FRAM writes are not wear" |
| V22 | Four-tier bus-hazard coverage for every new bus device, extended to every shared resource | owner, 2026-09-26 (OR41.a (3)) | CL:237-248, SPEC:2070-2071, 5876 |
| V23 | Flash-tier coverage is a subset of bench; exception shapes are listed and reviewed at close | owner, 2026-09-26 (OR45.a) | THR:1085-1089, SPEC:2160-2165 |
| V24 | Cross-device tests cover every device, derived | owner, 2026-09-26 (OR41.a (1), OR43.a) | SPEC:2193-2201 "complete coverage, not a gap" goes |
| V25 | Heavy twin integration tests are not wozi-only | owner, 2026-09-25/26 (OR22.a, OR43.a) | SPEC:2836-2839 |
| V26 | No hard-coded `wozi` in the real-website twin test | owner, 2026-09-26 (OR43.a, OR54.a) | `tests/test_digital_twin_real_website_integration.py:121` |
| V27 | The hand-written `html/definitions` are retired | owner, 2026-09-26 (OR43.a (3), OR54.a) | SPEC:4422-4425, 4507; BL:822-826 |
| V28 | Every new module joins the digital twin in the same session | owner, 2026-08-20 (OR16.a, OR45.a; tag OR87.a (b)) | SPEC:672-676, 2338-2346 tag; the definitions clause goes (OR43.a) |
| V29 | Every mock/twin hardware-facing test has a real-hardware counterpart or a listed exception | owner, 2026-09-26 (OR45.a (2b)/(3)) | SPEC:3197-3199: the four exceptions reviewed per OR45.a (3) |
| V30 | Twin persistence/IRQ/random-walk scenarios: counterpart or listed exception each | owner, 2026-09-26 (OR45.a (3)/(4)) | SPEC:3155-3156 |
| V31 | PUT /sensors reaches SCD30 NVM | fact + owner, 2026-09-26 (OR42.a) | SPEC:3215-3218, THR:757-759, 1138-1145 |
| V32 | Structural test exceptions are listed and reviewed at audit close | owner, 2026-09-26 (OR45.a (3)) | THR:1239-1249 |
| V33 | The UART fault-injection catalog is a listed exception reviewed at close | owner, 2026-09-26 (OR45.a (3), OR5.a) | one wording at SPEC:3225-3232, BL:90-92, THR:1276-1279 |
| V34 | Coverage never gates; no threshold | owner, 2026-09-25 (OR23.a (2)) | Codecov text goes (OR63.a) |
| V35 | The coverage job's test result gates; its number is advisory | owner, 2026-09-26 (OR63.a) | `ci.yml:506` names the actor |
| V36 | The three-attempt `uv sync` retry stays | owner, 2026-09-26 (OR37.a (2)) | — |
| V37 | The per-file timeout + two retries is a standing backstop | owner, 2026-09-26 (OR37.a (2)) | — |
| V38 | Driver/DUT process separation | owner, 2026-09-25 (OR20.a) | — |
| V39 | The twin `_mem_sampler()` collect stays the one twin exception if B3 shows its 25 ms collection does not decide Run 11 | owner, 2026-09-26 (OR54.a (2)) | SPEC:5062-5076, 3399-3400; `test_gc_collect_sites.py` extended to `digital_twin/` |
| V40 | GC discipline: both stages; boot-confined `gc.collect()`; a threshold is never the fix | owner, 2026-09-26 (OR39.a, OR40.a, OR55.a) | tags; "don't measure in the next line" replaced (OR55.a) |
| V41 | The `gc.collect` lint gate also covers `tests/` and `digital_twin/` | owner, 2026-09-26 (OR39.a, OR54.a) | `scripts/lint.sh:38` |
| V42 | The heap-unwedge call sites retire once the override test exists | owner, 2026-09-26 (OR52.a (6)) | SPEC:4134-4136 |
| V43 | `machine.mem_backup()` is adopted for `reset_reason` | owner, 2026-09-26 (OR60.a) | SPEC:3807-3808 |
| V44 | UART wire efficiency (43.6 %): the wire is not touched | owner, 2026-09-25 (OR24.a (2)) | SPEC:5530-5532 drops "accepted" |
| V45 | One global errno catalog | owner, 2026-09-25 (OR28.a) | `asy_uart_comm.py:104-106` |
| V46 | Reserved-range codes are renumbered in this audit, in one pass | owner, 2026-09-25 (OR28.a) | SPEC:1913-1915, BL:21-35 |
| V47 | One global repeat rule in `print_log.py` | owner, 2026-09-26 (OR35.a/OR35.b) | SPEC:1921-1926 |
| V48 | UART code ranking follows OR35.b and one event, one entry | owner, 2026-09-26 (OR35.b, OR56.a (1)) | SPEC:1949, its empty pointer repaired |
| V49 | Every failing notification cycle logs on the console only | owner, 2026-09-26 (OR35.b) | `tests/test_asy_notification_service.py:839` |
| V50 | NTP never ends its task; an unreachable server is handled in place | owner, 2026-09-25 (OR18.a) | tag at SPEC:1958-1961, 2311; `asy_ntp_client.py:115, 441-442` |
| V51 | Out of scope: hardware inoperational from the start or a stalled chip; escalation up to reboot is intended | owner, 2026-09-25 (OR18.a) | SPEC:1976-1980 |
| V52 | The config-write reboot loop decision of 2026-09-24 | owner, 2026-09-24 (OR42.a (1)) | SPEC:1990-1994 says what was decided |
| V53 | Config repair writes are bounded by boots; no cross-boot skip | owner, 2026-09-26 (OR42.a (1)) | — |
| V54 | The two device-script loose ends are answered | owner, 2026-09-26 (OR38.a (4), OR33.a) | BL:721-728 entry deleted |
| V55 | SGP40 general-call reset: see OR64.a | owner, 2026-09-26 (OR64.a, OR65.a) | SPEC:2060-2068, `tests/_bus_hazard_catalog.py:507` |
| V56 | No legacy config migration; from the release a golden-fixture migration test | owner, 2026-09-26 (OR52.a (1)/(2)) | BL:154-159 |
| V57 | Every API value is on its page (version and build date included) | owner, 2026-09-26 (OR43.a (2)) | SPEC:6580-6581 |
| V58 | `max-args` 8; ceilings are not raised by agents | owner, 2026-09-26 (OR46.a/OR46.b) | `pyproject.toml:202`, SPEC:4741 |
| V59 | Zero twin-awareness in `src/` | owner, 2026-09-26 (OR36) | dead "this step" pointer at `digital_twin/machine.py:302-304` |
| V60 | Each FRAM logger's store `setup()` comes first in its module's `setup()` | owner, 2026-09-26 (OR47.a (2)) | re-check once chunk setup joins the boot batch |
| V61 | Hazard-test latency blindness is corrected or justified by a sensitivity proof | owner, 2026-09-25 (OR21.a) | SPEC:5615-5617 |
| V62 | Legacy intent is the requirement | owner, 2026-09-26 (OR48.a, OR57.a) | SPEC:6601-6604 restated |
| V63 | The Renesas application notes are on the owner's unreachable-sources list | owner, 2026-09-25 (OR4.a) | SPEC:6731 drops "do not re-attempt" |
| V64 | Tests needing a `src/` change are scratched; their intents re-homed per OR33.a | owner, 2026-09-25 | BL:93-94 |
| V65 | The real-hardware go-ahead is per conversation | owner, 2026-09-25 (OR5.a (2)) | — |
| V66 | The bench flash write is a gated (owned) or a prerequisite write | owner, 2026-09-26 (OR45.a (3), OR40.a (3)) | DLR:176-178 |
| V67 | dev wiring facts move to their canonical home | owner, 2026-09-25 (OR32.a (3)) | DLR:30-34, 49, 57 |
| V68 | Consistency changes are made directly | owner, 2026-09-25 (OR24.a (1)) | CL:89-93 |
| V69 | Same top-level features after the refactor | owner, 2026-09-25 (OR12) | — |
| V70 | The three-line comment cap | owner, 2026-09-26 (OR51) | exemptions and counting labelled the agent's |
| V71 | Checker candidates (vulture etc.) stay out of `lint.sh`; the audit uses one once | owner, 2026-09-26 (OR46.a (2)) | — |
| V72 | The final-wiring owner requirement is fulfilled | owner, 2026-09-25 (OR20.a, OR22) | BL:848-859 item closed |
| V73 | The annotation quoting rule is harmonised in the audit | owner, 2026-09-25 (OR24.a (1)) | SPEC:2658-2661 "not mass-edited" goes |
| V74 | Self-chosen test ports use port 0; product ports run under a lock | owner, 2026-09-26 (OR38.a (3)) | SPEC:2793-2794 |
| V75 | Unreachable defensive branches get a verdict per line | owner, 2026-09-26 (OR25.a (3), OR46.a) | SPEC:2999-3030, `asy_fram_driver.py:424-426` |
| V76 | A retry never counts as a fix | owner, 2026-09-26 (OR37.a (2), OR6.a) | SPEC:3427-3431: the Run 11 retry changes or gets an owner exception |
| V77 | `cfg_schema`'s "for the legacy REST layer" reason is gone | owner, 2026-09-26 (OR36.a (1), OR58) | `tests/test_asy_ntp_client.py:2259`, `test_asy_wifi_service.py:2487` |
| V78 | The WDT is hardcoded, the first statement of the generated boot entry | owner, 2026-09-25 (OR31.a (1)) | `tests/test_reset_call_site_invariant.py:30` |
| V79 | The webserver binds 0.0.0.0 | owner, 2026-09-26 (OR52.a (3)) | — |
| V80 | `segfault_stress_repro.py`'s `gc.collect()` goes; the tool is collected or inventoried | owner, 2026-09-26 (OR54.a, OR16.a (2)) | DTR:886-893 |
| V81 | The DNS backoff-growth branch is covered or justified | owner, 2026-09-25 (OR25.a (3)) | THR:890-895 |

## 9 Section 5 — engineering-local, kept (OR71.a (0)); actor per OR82.a/OR83.a

| ID | Decision | Actor, date | Correction owed |
|---|---|---|---|
| L01 | `voc_algorithm.py` stays a literal port: upstream names, casing, order | owner, 2026-10-05 (OR141.a (3)) | — |
| L02 | The FRAM path holds driver lock and SPI bus for a whole block operation | owner, 2026-09-18 | tag; trade figures are the agent's |
| L03 | FRAM_SPI's D.4 violation | agent, 2026-08-19 | fix (OR5) |
| L04 | `NeopixelDriver` has no config schema | owner, 2026-08-05 | tag |
| L05 | No hardware flow control on the UART driver | owner, 2026-07-23 | tag |
| L06 | `get_ambient_pressure()` reads back via the set command: "leave as-is, no alternate documented read-back exists" | owner, 2026-07-22 (OR83.a (1)) | restore those words for "confirmed intentional — don't fix" |
| L07 | `DEV_UNIQUE_GROUPS` | agent, 2026-09-08 | fix the false sentence; OR43.a (2) supersedes |
| L08 | Two Unix-port binaries | owner, 2026-09-21 | tag |
| L09 | CI keeps `needs:` sequencing without gating | agent, 2026-09-10 | relabel |
| L10 | The Unix-port heap flag is never raised as a fix | agent, 2026-09-17 | relabel; measured changes allowed (OR30.a/OR39.a (3)) |
| L11 | Dynamic imports banned in the firmware graph | agent, 2026-09-09 (OR83.a); owner scope 2026-10-05 (OR141.a (2), OR142.a) | SPEC F.1 lists the host/test loaders as exceptions |
| L12 | Driver facts the firmware never reads are comment tags | owner (quoted), 2026-09-10 | keep the quote |
| L13 | A tag present or near-present verifies in every dimension or fails the build | owner, 2026-09-10 | restore the tag |
| L14 | The UART module is a plain class (delegated) | agent, 2026-09-11 | relabel as delegated agent design |
| L15 | The `uart.any()` clamp is not applied to I2C/SPI | agent (fact-backed), 2026-09-11 | — |
| L16 | Every UART hazard check runs in both CRC modes | agent, 2026-09-12 | relabel; fix "deployed link … in the field" |
| L17 | The bus driver gains a pluggable framing codec (UCL A11) | owner, 2026-09-11 | tag |
| L18 | A UART bus-parameter mismatch is refused at build | agent, 2026-09-24 | relabel the extension |
| L19 | WiFi lock-contract inconsistency | agent, 2026-07-27 | change (OR24.a (1)) |
| L20 | `SGPResetVOC` registered like other live-push fields | agent, 2026-08-04 (OR83.a) | name the actor |
| L21 | No int→float round-trip check while field bounds stay below 2**24 | owner, 2026-08-24 | tag |
| L22 | The config cache repairs an externally corrupted file | agent, 2026-07-16 | relabel; fix the dangling CL pointer (`config_manager.py:5-7`) |
| L23 | The inline bootstrap is not type-checked | agent, 2026-08-26 | relabel |
| L24 | Frontend/mock simulate a backend gap fixed in `323a1a7` | agent, 2026-08-22 | fix (stale) |
| L25 | Per-field failure marking differs from legacy | agent, 2026-08-22 | relabel |
| L26 | No HTTP keep-alive | agent, 2026-08-25 | relabel |
| L27 | Rejected heap remedies stay rejected | agent (measured), 2026-09-24 | — |
| L28 | `PBUF_POOL_SIZE` left alone | agent (measured), 2026-09-22 | — |
| L29 | The CYW43 heap cost is unavoidable | agent (fact), 2026-09-07 | — |
| L30 | `crc_checks.py` keeps its per-byte yield: "pure wall clock time is not such an issue, don't touch" | owner (quoted), 2026-09-18 | keep the quote |
| L32 | The body-cap binding is not hardware-confirmed | agent (fact), 2026-09-19 | — |
| L33 | The ISL29125 range-ratio spread is a recorded property, not actionable | owner, 2026-09-14 | tag |
| L34 | ISL29125 registers and colour chain follow datasheet FN8424 | agent (fact), datasheet | — |
| L35 | The CCT matrix is the datasheet placeholder | agent (fact), datasheet | — |
| L36 | `br0` presents `eth0`'s MAC and never auto-repairs | agent (observed), 2026-09-04 | — |
| L37 | The chroot check needs both noble and trixie | owner, 2026-09-11 | tag |
| L38 | Explicit-Any work deferred | agent, 2026-07-13 | close; switched on in this audit (OR81.a) |
| L39 | Ruff E722 stays enabled so bare excepts show as findings | owner, 2026-07-13 | tag |
| L40 | `method-assign` stays enabled; `src/` never suppresses it | owner, 2026-09-10 | tag |
| L41 | `ruff format` unused | agent, 2026-07-13 | relabel |
| L42 | zizmor `self-repository` disabled | agent, 2026-09-10 | relabel; name the revisit trigger (actionlint support) |
| L43 | max-args trixie-leg risk judged low | agent, 2026-09-12 | relabel |
| L44 | Lint exemptions live centrally "rather than as # noqa comments scattered inline" | owner, 2026-09-10 (OR83.a (1)) | restore "rather than" for "never" |
| L45 | The duplicate conftest gap | agent, 2026-09-24 | relabel |
| L46 | SPIDevice/I2CDevice asymmetry | agent, 2026-09-18 | change (OR24) |
| L47 | I2C register reads go through `readfrom_mem_into()` | owner, 2026-09-18 | tag |
| L48 | A transient SPI RX overrun is not retried | owner, 2026-09-24 | drop "don't re-propose" |
| L49 | BMP390 shares the BMP3xx register map | agent → datasheet, 2026-08-11 | replace the owner tag with the datasheet citation |
| L50 | WS2812 on USB 5 V behind a level shifter; levels settled | owner (quoted), 2026-09-25 | — |
| L51 | `dev`'s real website is the most biting test; every device's real site, never a hard-coded one | owner, 2026-09-23 (OR83.a (1), OR54.a (1), OR78.a) | SPEC:657-658 restored |
| L52 | The UART driver shape is a precedent for future wrappers | agent, 2026-08-08 | relabel |
| L53 | `get_data()` narrows via identity return + scoped `type: ignore[return-value]` | owner, 2026-07-23 | tag |
| L55 | `make_dict()` dormant landmine | agent, 2026-07-30 | fix (OR5) |
| L56 | Bus/socket layers do not log | owner, 2026-08-20 | drop "coverage audit closed" (OR16/OR25) |
| L58 | The `_WIRING` import exception | agent, 2026-09-10 | relabel |
| L59 | Bus OSError is the one exception to "never raises" | agent, 2026-07-15 | relabel; check under OR26.a |
| L60 | The allocator is a mocking surface | agent, 2026-09-13 | relabel |
| L61 | No forced further mock/twin sharing | agent, 2026-09-04 | relabel |
| L62 | `get_long_block_lock()` retired; a new long block needs a fresh mechanism | agent, 2026-07-28 (OR83.a) | relabel |
| L63 | Fakes return a fresh bus object | agent, 2026-09-10 | add to the OR17.a fidelity table |
| L64 | Stub defects are repaired, not `type: ignore`d | agent, 2026-09-10 | relabel |
| L65 | `-X no-source-lines` not adopted | agent, 2026-09-10 | relabel; P6 may revisit |
| L66 | I2C has no multi-transfer session primitive | agent, 2026-09-24 | close the deferral (OR5) |
| L68 | The twin UART `wire_log` is unbounded | agent, 2026-09-14 | relabel |
| L69 | COBS cannot confuse its delimiter | agent (measured, 20,010 cases) | — |
| L70 | Unknown-length pull transfers are outside the wire format (J.3) | agent (fact) | — |
| L71 | The CRC zero-padding limitation | agent (fact) | — |
| L72 | The debug level goes through a registry of bound `set_level()` methods | owner, 2026-08-11 | — |
| L73 | NTP setters "out of scope" | agent, 2026-07-24 | fix (stale: setters exist since `3f1fcc0`) |
| L74 | FRAM golden wire traces stay byte-identical across restructures | agent, 2026-09-18 (OR83.a) | name the agent plan as the source |
| L75 | Twin single-chip persistence limitation | agent, twin note | — |

## 10 Left out (reopened, deferred or still open)

- **B06** `NTP_Host`'s 1,024-character bound: re-decided with the key harmonization (OR70.a (4)).
- **OR62.a** SGP40 addressed heater-off: overtaken by OR64.a.
- **C09** off-subnet spoofing as a permanent bench skip: overtaken by OR79.a (the test is attempted).
- **C12, C13** UART peer-sized allocations, unbounded `readline_until_complete()`: deferred by OR69.a (7); work since OR143.a.
- **E04** unpinned Firefox install: agent design still to be weighed against OR50.a's pin rule.
- **L31, L54** dead scratch fallback, ConfigManager's defensive catches: decided in the dead-code pass (OR25.a (3), OR46.a).
- **L57** hotspot DNS task outside generic supervision: checked against OR31.a first.
- **L67** hand version bump: deferral or close still open.
