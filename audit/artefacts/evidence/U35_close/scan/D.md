D scan, written by the lane (Wed Oct 28 07:58 UTC 2026)

Group D: `buildgen/` (with `buildgen/error_catalog.json`), `devices/*.toml`, and the generated device modules in
`build/generated_src/` judged by their emitter (`buildgen/codegen.py`). Range `25caf528..497b3eda`, worktree
`S/wt-u35int` read only; buildgen not run there. The pre-audit side is `codegen.py@25caf528` (709 lines), read, not
run, so pre-audit emitted sizes are estimates from that template (marked "est."). Device code lines are counted in the
generated output at head (wozi unless named; non-blank, non-comment lines). Buildgen's own growth is host code, given
separately: 3,681 to 6,227 lines, 2,784 to 4,819 non-blank non-comment (+2,035), plus the new 237-line catalog JSON;
`devices/` +77/-44 lines.

Rule short names used in "scheme" (each with the line that states it):
- **NH**: the owner's standing target, "nothing built on hypothetical findings; no patches; anything beyond the
  legacy firmware's behaviour is the owner's decision" (owner, 2026-10-28, `S/u35r/briefs/inv_firmware_additions.md:2-4`);
  "Speculative and hypothetical effects maybe, maybe not." (owner, 2026-10-28, `S/u35r/briefs/scan_firmware.md:6`).
- **CR**: "Resulting cascades are a red flag at least." (owner, 2026-10-28, `scan_firmware.md:6-7`).
- **MC**: "the way it flows into the firmware and buildgen is *really* minimal change" (owner, 2026-10-28,
  `scan_firmware.md:4-5`).
- **DL**: "hardcoded delay checks like this are a very bad, very awkward pattern" (owner, verbatim,
  `scan_firmware.md:106-107`). What "like this" pointed at is not in my sources; rows carrying DL are build-time
  timing-arithmetic checks, named as candidates only.
- **P4** "Premium code, one material, nothing in the product for tests" (`audit/CONSOLIDATION.md:28`); **P8** "One
  source of truth, generated not copied" (`:32`); **P7** "Evidence survives and stays readable" (`:31`).
- **TLF**: "The refactor should end up with the *same top-level features* … not a feature change" (`CLAUDE.md:508-512`).
  Every owner-decided feature beyond legacy (marked O) is the owner's own exception and is not counted as a violation.

---------------------------------------------------------------------------------------------------------------------

## 1. Boot entry `build/generated_src/sensortask_<device>_main.py` (emitter `codegen.py:820-877`)

Pre-audit emitted (`codegen.py@25caf528:696-709`): 10 lines, 8 code + 2 docstring (`import asyncio`, `import gc`, the
device import, `gc.threshold(32768)`, `try: asyncio.run(main()) finally: asyncio.new_event_loop()`). Head: 47 lines,
27 code. Not counted (checked): the docstring text, the comment lines, `gc.threshold(32768)` (pre-existing).

**B1 Watchdog armed as the entry's first statement and passed in as `main(watchdog=)`**
- where: `codegen.py:850-854, :861`, `_BOOT_SIGNATURE :34-36`; `sensortask_wozi_main.py:4-6, :32`; module `:121-123, :236-237`
- what: `WDT(timeout=8000)` armed before any product import (pre-audit: first line of `build_system()`, after the device module and its imports loaded); same 8 s.
- commits: f76385a6 (`_WDT_TIMEOUT_MS` shared with `validate.py:95`)
- origin: A.U20.02, M.GEN.001/.005/.006; OR31.a (1)
- evidence: O — "the WDT is created as the first statement of the generated boot entry, before the device-module import" (owner, 2026-09-25, OR31.a (1), quoted in `audit/actions/U20.md` A.U20.02); SPECIFICATION.md:684-686 "(owner, 2026-09-25)".
- legacy: partly — `WDT(timeout = 8000)` at module level after its imports (`legacy/firmware/modules/sensortask-wozi.py:77`, imports `:1-18`).
- form: design (boot policy). depends on: none.
- device cost: 2 code lines, moved (net 0; the module's `watchdog` global goes). The ~1.1 s product import now runs under the armed watchdog before the first feed (SPECIFICATION.md:13355, `boot.unfed_stretch_1_ms`).
- class: **R**. scheme: none.

**B2 `.frozen` first on `sys.path`**
- where: `codegen.py:824-826`; `_main.py:8-11`
- what: a filesystem `.py`/`.mpy` can no longer replace a frozen module.
- commits: f76385a6. origin: A.U20.03, OR59/OR59.a (2)
- evidence: O — OR59 "c" — runbook and firmware guard both (owner, 2026-09-26); OR59.a (2) "the generated boot entry puts `.frozen` ahead of `''` and `/lib` on `sys.path` before importing any product module … a buildgen test pins the line" (`U20.md` A.U20.03). Emitted tag "(owner, 2026-09-26)".
- legacy: no (`legacy/firmware/modules/_boot.py:16`, no path edit). form: design. depends: none.
- device cost: 2 code lines; one list insert per boot. class: **R**. scheme: none.

**B3 Emergency exception buffer, 100 B**
- where: `codegen.py:828-831`; `_main.py:15-18`
- what: a MemoryError raised with the heap full keeps its "memory allocation failed" text.
- commits: f76385a6. origin: A.U20.04, G1/R38; "pass 3 C1.10 is 'owner: n', an agent-level choice carried by U20" (`audit/actions/U7.md:306`); Part N `gc.emergency_exc_buf_bytes` basis "estimated (agent, 2026-10-08)" (SPECIFICATION.md:12146).
- evidence: H (source reading).
- legacy: no. form: design. depends: none.
- device cost: 2 code lines; one 100 B heap block held for the run.
- class: **H** (mechanism confirmed, V1).
- triage: implausible as a device fault — the trigger (heap exhaustion) is rare and the effect is an empty message, not a hang, reset, data loss or wrong reading. It does reach the evidence: `src/` logs `str(e)`, so the four memory gates (CLAUDE.md memory rule, "match `MemoryError` OR `memory allocation failed`") would miss such an entry (P7). One source read settles it, so verified anyway: V1 confirmed.
- scheme: none (serves P7).

**B4 No-autostart boot-entry variant**
- where: `codegen.py:840-849`; `sensortask_<device>_main_noautostart.py`; `generate.py:137-151` (`_output_names`, compile)
- what: an image whose `main.py` arms nothing, prints the start line and returns to the REPL; frozen only by `scripts/build_firmware.py --no-autostart`.
- commits: f76385a6. origin: A.U20.05, OR86, M.GEN.001/.019
- evidence: O — OR86 "a command line option for building a firmware which builds a version without autostart" (owner, 2026-09-28; `U20.md` A.U20.05).
- legacy: no. form: design. depends: B1 (prints the `WDT(timeout=8000)` line).
- device cost: release image 0; a no-autostart image carries 11 code lines in place of the 27.
- class: **R**. scheme: none (P4 holds: the release image does not carry it).

**B5 Ctrl-C ending the loop writes reset reason 21**
- where: `codegen.py:856, :862-866`; `_main.py:25, :33-37`
- what: `KeyboardInterrupt` out of `asyncio.run()` writes `RR_INTERRUPTED` before re-raising, so the next boot reads 21, not a plain watchdog reset (2).
- commits: f76385a6 (comment 5f63546e)
- origin: M.GEN.001 (1) "(A-C fold, silent-failure scan SF-A14, 2026-10-06)". The owner later answered a decode-order question about this record ("B is fine, very rare edge case", owner, 2026-10-26, `owner_rulings_after_LN118.md` Q4) — not a decision to add it.
- evidence: H (scan).
- legacy: no (`sensortask-wozi.py:610-613`, `try`/`finally` only). form: patch — a handler that relabels one console-only exit.
- depends on: G1 (the reset-reason record).
- device cost: 4 code lines (with the `asy_system_service` import line it shares with B6); one `mem_backup` write on Ctrl-C only.
- class: **K** — the knowledge holds (a console Ctrl-C ends the loop and the reset then reads as 2: V4), the code is in doubt.
- triage: implausible — the trigger is a person at the USB console (bench/development, never a field unit); the reset happens the same way with or without it, only its code differs.
- scheme: NH.

**B6 Any other exception ending the loop: recorded (22), printed, never re-raised**
- where: `codegen.py:856, :867-874`; `_main.py:24-25, :38-45`
- what: a `BaseException` leaving `asyncio.run()` writes reset reason 22 after `BOOT_DONE` (nothing during boot), runs `report_if_fatal()`, prints through `console()`/`sys.print_exception`, and is swallowed so `main.py` ends under the armed watchdog.
- commits: 16121317, 980c0f7d, 5f63546e
- origin: OF-107 (`audit/sweeps/open_findings.md:115`, "U20 lane C scan"); SPEC A.7 tag "(agent, 2026-10-26)" (SPECIFICATION.md:694-695); run as redo item F4b under "F4 (owner, 2026-10-26, LEAD NOTES 155-157)" (`S/u35r/REDO.md:31`) — the owner's words for F4 not found (searched `owner_rulings_after_LN118.md`, `lead_notes_119_148.md`, `owner_report_items.md`, `closing_ledger.md`).
- evidence: H (scan).
- legacy: no (`sensortask-wozi.py:610-613`). form: patch — a catch-all around the loop to relabel a reset.
- depends on: G1, G2, B5.
- device cost: 6 code lines (incl. `from asy_print_log import console, report_if_fatal`); at a loop end one `mem_backup` write and a print; nothing per wake.
- class: **K** — knowledge holds (V4: an exception ending the loop reads as code 2), code in doubt (a catch-all plus its own cascade, B7).
- triage: implausible — no `src/` code raises a non-`Exception` `BaseException` (no `SystemExit`/`sys.exit` in `src/*.py`), and an `Exception` out of the loop core already ends in the same watchdog reset under the pre-audit entry (V4); the addition changes the reset code from 2 to 22.
- scheme: NH; CR (root of B7).

**B7 `ended` pre-bound before the loop**
- where: `codegen.py:858-859`; `_main.py:29-30`
- what: a module-level slot so B6's `except … as ended` rebinding does not grow the globals dict at the failure moment.
- commits: 16121317, c87249c6, b8b7207e (a `noqa` added, then moved to a per-file lint exemption)
- origin: the emitted comment (agent; no tag). evidence: H. legacy: no.
- form: patch — works around B6's own allocation. depends on: B6.
- device cost: 1 code line; one global slot. class: **C** (root B6). scheme: CR.

---------------------------------------------------------------------------------------------------------------------

## 2. Device module `build/generated_src/sensortask_<device>.py` (emitter `codegen.py`)

Pre-audit emitted ~280 lines (est.); head: wozi 249 lines / 212 code (9 are the `TYPE_CHECKING` block the frozen copy
strips), dev 264/227, arzi/grkizi/klkizi/schlafzi 246/209.

Not counted (checked): the `TYPE_CHECKING` block, annotation-only globals, removed `= None`/asserts/`Any`, the removed
write-only `timers_running` ThreadSafeFlag (typing and removals, A.U20.42/A.U10.12); renames (module/class names,
`trigger_sec`→`trigger_s`, `network_available`→`network_available_locked`, `_gmtimestruct_to_dict`'s and /status's
key spellings, build-info keys; the refactor-added duplicate `IP` key dropped); moves (`LogConfig`, `WifiConfig`,
`NtpTiming`, `ServingLimits`/`RouteSources`/`StaticSite` objects in place of loose keywords; SGP40 `ValueRef`;
notification signals passed at construction instead of `register()`/`finalize()`; the neopixel built before `conn` and
passed as `ext_led` instead of `conn.set_ext_led()` — `graph.py:59-61`, construction order only, setup order unchanged;
level setters as a provider; one SGP40 maintenance adapter per instance, same output on all six devices; the LED R/G/B/T
checks moved into the webserver); explicit `ServingLimits`/`NtpTiming`/`TransferLimits` values read from `src/`
defaults (equal to the constructor defaults); the pause callback's `return await notification.set_override_led(payload)`
(41b47f1d) — no behaviour change, V3; the D.15 member reorder (656fc82f, ~1,118 changed lines, move only); `_lit()`,
`_sorted_imports()`, `_natural()`, `_member_rank()` (15b8633c, ~30 buildgen lines) so the generated tree lints like
`src/` (restyling of emitted text).

**G1 Reset record read first: `reset_reason = begin_boot()`, passed to SystemService**
- where: `codegen.py:165-166, :211-214`; module `:127, :138`
- what: `build_system()`'s first statement reads and clears the `mem_backup` reset record (published as G14).
- commits: f76385a6. origin: A.U11.05, M.GEN.005, OR60.
- evidence: O — OR60 "b, but don't use FRAM, as it's optional. Micropython 1.29 offers a special RAM storage area surviving reboots … integrate it into the system service and its endpoints (e.g. "reset_reason" with a corresponding number code)" (owner, 2026-09-26; `U11.md` A.U11.05).
- legacy: no. form: design (mechanism in `src/asy_system_service.py`, other lane). depends: none.
- device cost: 1 code line + 1 keyword; once per boot. class: **R**. scheme: none.

**G2 Boot-phase marks**
- where: `codegen.py:438-453`; module `:238, :240, :242, :244, :247` (+ import `:24`)
- what: `main()` marks BOOT_SETUP/TASKS/TIMERS/NTP/DONE; a reset during boot reads 10 + phase.
- commits: f76385a6. origin: A.U11.06, OR102 (6)
- evidence: O — OR102 (6) "a, bot only if this is possible with the special RAM section, and for sure without flash writes and without FRAM. If not, leave it silent" (owner, 2026-09-29; `U11.md` A.U11.06).
- legacy: no. form: design. depends: G1. device cost: 5 code lines; 5 RAM-register writes per boot. class: **R**. scheme: none.

**G3 Boot order: setups, tasks, timers, first NTP sync last, then supervision**
- where: `codegen.py:438-453`; module `:236-248`
- what: tasks start before timers and the first NTP force sync follows both (pre-audit emitted timers → NTP sync → tasks with supervision).
- commits: f76385a6. origin: A.U20.06, OR75/OR75.a
- evidence: O — OR75 "Boot order is tasks before timers" (owner, 2026-09-28; `U20.md` A.U20.06); NTP last "(agent, 2026-09-28; owner-reviewed, 2026-10-02)" (module `:245`), owner review `ntp-sync-last` status "ok" (2026-10-02, `audit/review/answers.json`).
- legacy: partly — timers (staggered) → tasks → first NTP sync → supervisor (`sensortask-wozi.py:575, :578-581, :583, :585-609`).
- form: design. depends: none. device cost: 0 net lines. class: **R**. scheme: none.

**G4 One setup list run by `sysfunct.run_setups()`; `webserver.setup` and every reader's setup in it**
- where: `codegen.py:313-316, :443, :758-770`; module `:186-188, :239`
- what: the one-time setup batch is a list SystemService loops, feeds and collects over (pre-audit: 30 unrolled lines, `await X.setup()` / `sysfunct.feed_watchdog()` / `gc.collect()` per unit, results discarded); `webserver.setup()` and each SensorReader's logger setup join it (at boot instead of lazily in tasks).
- commits: f76385a6, 41b47f1d. origin: A.U11.10, A.U20.06, A.U10.10, M.GEN.010/.041
- evidence: O — OR84 "a sysfunct function which gets the list of the setup functions to be called, and all of the looping, collecting and feeding is done automatically" (owner, 2026-09-28; `U11.md` A.U11.10); OR47.a (2) "every chunk setup (`pr.setup()`) moves into the one-time boot `setup()` batch" (owner, 2026-09-26; `U10.md` A.U10.10).
- legacy: partly (`sensortask-wozi.py:542, :571-573`: a one-time list holding `fram.setup` only, no feeds).
- form: design. depends: none. device cost: 3 emitted code lines where 30 were (-27). class: **R**. scheme: none.

**G5 Read triggers collected apart from the timer starters**
- where: `codegen.py:447, :456-469`; `driver_registry.py:88` `class_has_read_triggers`; module `:229-234, :243`
- what: only the sensor readers' read triggers enter the one-second stagger; the other timers start unstaggered.
- commits: 41b47f1d. origin: A.U10.12, M.GEN.010
- evidence: O — WP7 "staggered evenly across exactly one second in total … must not be changed into a fixed per-task gap, nor rescaled" (owner, 2026-09-16) and OR47.a (3) (owner, 2026-09-26), both in `U10.md` A.U10.12's Why.
- legacy: partly — every timer staggered over 1000 ms (`sensortask-wozi.py:100-110, :575`).
- form: design. depends: none. device cost: 5 code lines; a list of ≤ 3 starters at boot. class: **R**. scheme: none.

**G5b Bus-spread order of the read triggers (`trigger_spread`)**
- where: `codegen.py:457-458, :903-911`; tests `tests_scripts/test_buildgen_generate.py:976-998, :1035`
- what: readers sharing a bus are put furthest apart in the stagger order.
- commits: 41b47f1d. origin: A.U10.12's Req "bus-sharing sensors placed furthest apart" (the register's text; no owner words for the ordering found in `U10.md`).
- evidence: H. legacy: no (list order). form: design. depends on: G5.
- device cost: 0 device lines; 9 buildgen lines.
- class: **H**. triage: implausible — V5: on all six devices the spread order equals the construction order (wozi `(sgp40, bmp3xx)` both on `i2c1`; dev `(sgp40, bmp3xx, isl29125)` on `i2c1, i2c0, i2c1`; arzi/neu `(sgp40,)`), so nothing that runs changes.
- scheme: NH; MC (code with no effect on any device).

**G6 Task names for the supervisor (`_collect_task_names`, `task_names=`)**
- where: `codegen.py:345-351, :445`; module `:217-221, :241`
- what: each supervised task is named `<module>.<starter>` in the supervisor's log lines and in LastTaskEnd.
- commits: 970b63ba. origin: A.U32.06, OR128
- evidence: O — OR128 "(a) Yes: publish it as `LastTaskEnd` in `/status`" (owner, 2026-09-30; `U32.md` A.U32.06).
- legacy: partly — `Task_LastErr` is the task's index (`sensortask-wozi.py:93, :496, :591`).
- form: design. depends: none. device cost: 5 code lines; one small `str` per task starter built at boot and kept. class: **R**. scheme: none.

**G7 The FRAM manager's task and timer starters are collected**
- where: `codegen.py:339-356` (fram no longer excluded); module `:213, :225`
- what: the FRAM chip-watch task runs; a declared chip that dies escalates like any chip.
- commits: 2977c4e0. origin: A.U16.17/A.U16.R03, OR89.a (5)
- evidence: O — OR89 (5) "5. the same as all other chips" (owner, 2026-09-29; `U16.md` A.U16.17); OR18.a "escalation through the task supervisor up to a reboot is acceptable and even intended, since a reboot may recover a stalled chip" (owner, 2026-09-25).
- legacy: no. form: design. depends: none. device cost: 0 emitted lines; +1 supervised task (the src lane's cost). class: **R**. scheme: none.

**G8 Config-store collector for the shutdown sequence (`_collect_config_stores`, `config_stores=`)**
- where: `codegen.py:213, :329-338`; module `:138, :202-209`
- what: every ConfigManager is handed to SystemService, which flushes staged writes in its shutdown for every command (pre-audit: a generated `_flush_pending_configs()` before reboot and bootloader only).
- commits: f76385a6. origin: A.U11.03, A.S0930.11/.31, M.GEN.007
- evidence: O — A.U11.03's supervisor fixes "approved (owner, 2026-09-29, OR101.a)"; OR126.a (3) "`reboot` and `bootloader` run the same controlled shutdown sequence as the two new commands (no apply step)" (owner, 2026-09-30; `SUPP_owner_0930.md` A.S0930.31); emitted tag "(owner, 2026-09-26)".
- legacy: no (reboot pauses storage, then resets: `legacy/firmware/python/CommonDrivers/system_service.py:35-42`).
- form: design. depends on: G9. device cost: 7 code lines where the pre-audit helper had 15 (-8); a list built per shutdown. class: **R**. scheme: none.

**G9 System commands `resetconfig` and `erasefram`**
- where: `codegen.py:249-261`; module `:78-81`
- what: two new REST system commands, each through the controlled shutdown and a reboot.
- commits: f76385a6. origin: A.S0930.11/.12, OR117/OR119
- evidence: O — OR117.a (2) "Erase FRAM … the whole chip" (owner, 2026-09-30; `SUPP_owner_0930.md` A.S0930.12); owner review `system-command-words` ("Reset to defaults is sent as SystemCmd 'resetconfig', Erase FRAM as 'erasefram'") status "ok", 2026-10-02.
- legacy: no (`sensortask-wozi.py:519`: reboot, bootloader, mempause). form: design. depends: none.
- device cost: 4 code lines. class: **R**. scheme: TLF, owner-decided (not counted).

**G10 The command callback answers the service's verdict**
- where: `codegen.py:250-260`; module `:71-82`
- what: every word returns the service's bool, so a command during a shutdown answers Failed (pre-audit: True after the call).
- commits: f76385a6. origin: A.S0930.11
- evidence: O — OR119.a (1)-(2) "refuse any further command" while a shutdown is under way (owner, 2026-09-30, OR119; `SUPP_owner_0930.md` A.S0930.11).
- legacy: partly (fixed answer text, no refusal: `sensortask-wozi.py:524-537`). form: design. depends on: G8/G9.
- device cost: 0 net lines. class: **R**. scheme: none.

**G11 A REST LED command is refused while a signal runs (callback calls `led_signal`)**
- where: `codegen.py:262-266`; module `:84-85`
- what: refused at once while busy (pre-audit called `request_signal()`, which looped `while … is_set(): await asyncio.sleep(0)` until the running signal ended, `src/asy_neopixel_driver.py@25caf528:145-153`).
- commits: 2f049a00 (the R/G/B/T checks' move: f5c82557). origin: U9, A.U19.02, M.GEN.008
- evidence: O — owner review `led-request-internal-queue` (decision "Your rule refuses a REST LED command at once while a signal runs."), owner's note "Fine, and this for a reason: internal LED commands are guaranteed to be bounded by number and frequency, they won't flood the device. External commands might quickly flood it into exhaustion. The refusal and error message lets the external caller knows to try again later." (2026-10-02, `audit/review/answers.json`).
- legacy: yes (`sensortask-wozi.py:415`, `led_signal` → "busyLED"). form: design. depends: none.
- device cost: 1 emitted code line where 15 were (est.; the checks moved). class: **R**. scheme: none.

**G12 Networking status from one Wi-Fi snapshot, no radio read per request**
- where: `codegen.py:276-286`; module `:94-102`
- what: IPv4/Subnet/Gateway/DNS/RSSI come from the 1 Hz snapshot (pre-audit: `get_wlan_ifconfig()` and `get_wlan_rssi()` per GET).
- commits: f1f800e7. origin: A.U18.33, RF206
- evidence: O (thin) — the register's Req "(L19 "change", OR24.a (1))" (`U18.md` A.U18.33); owner review `deactivated-snapshot` ("…without asking the radio") status "ok", 2026-10-02.
- legacy: no (`sensortask-wozi.py:148-149`). form: design. depends: none.
- device cost: -1 code line; two radio/lock reads fewer per GET /status. class: **R**. scheme: none.

**G13 `HTTPDropped` and `WifiTS` in /status**
- where: `codegen.py:284`; module `:101`
- what: dropped web connections over the last 24 h, and the Wi-Fi snapshot's time.
- commits: f5c82557. origin: A.U19.08/.10, OR137
- evidence: O — "Sounds good, and handle the dropped Http connections the same way as the dropped (general) connections, as we already discussed - last 24h with 24 counter buckets, no dynamic allocation and capped counters." (owner, 2026-10-02, `answers.json` `status-fields-added-and-left-out`).
- legacy: no. form: design. depends: none. device cost: 1 code line; one awaited call + 2 keys per GET /status. class: **R**. scheme: none.

**G14 `ResetReason` in /status** — `codegen.py:293`, module `:109`; f76385a6; A.U11.05; O (OR60, as G1); legacy no; design; depends G1; 1 code line (shared with G14b, G15). class **R**. scheme none.

**G14b `ResetBits` in /status**
- where: `codegen.py:293`; module `:109`. commits: f76385a6. origin: M.GEN.008 (2) "(A-C fold, silent-failure scan SF-A10, 2026-10-06)".
- evidence: H. legacy: no. form: design. depends on: G1. device cost: 0 extra lines; one call per GET /status.
- class: **H**. triage: implausible — diagnostic only (the chip's raw reset flags beside the decoded code); no fault mechanism. scheme: NH.

**G15 `MemFree` in /status** — `codegen.py:293`, module `:109`; f76385a6; A.U11.08; O — OR71.a (7) "free heap (`gc.mem_free()`) becomes a `/status` field" (owner, 2026-09-26; `U11.md` A.U11.08); legacy no; design; 0 extra lines, one `gc.mem_free()` per GET. class **R**. scheme none.

**G16 `ConfigFaults` in /status**
- where: `codegen.py:297`; module `:111`. commits: f76385a6. origin: OR138, M.GEN.008
- evidence: O — OR138 "(`ConfigFaults` in `/status`; Reset to defaults deletes unreadable files too)", an owner review answer (`audit/actions/AC_NOTES.md:188`, item 52); owner note "As discussed and stored here: "Damaged config files (OR138)"" (`answers.json` `unreadable-config-file`, 2026-10-01).
- legacy: no. form: design. device cost: 1 code line (shared with G17); one list copy per GET. class: **R**. scheme: none.

**G17 `ConfigUnpersisted` in /status**
- where: `codegen.py:297`; module `:111`. commits: f76385a6. origin: M.GEN.008 (1) "(A-C fold, silent-failure scan SF-B3 and SF-M1-07, 2026-10-06)".
- evidence: H. legacy: no. form: design. depends on: G16. device cost: 0 extra lines; one list copy per GET (+ src state).
- class: **H**.
- triage: suspicious on its face (a failed config write leaves settings RAM-only, lost at the next reboot: data loss on a rare trigger). V2: refuted as a gap — the pre-audit ConfigManager already logged exactly this case, errno 14 "- Error writing config data, running unpersisted:" (`src/config_manager.py@25caf528:378-380`), in the module's `CFGMGR_<name>` log that /status `errcount` shows (reproduced 3/3).
- scheme: NH; P8 (a second surface for one fact).

**G18 `LastTaskEnd` in /status** — `codegen.py:298`, module `:112`; 970b63ba; A.U32.06; O (OR128, as G6); legacy partly (`Task_LastErr`, `sensortask-wozi.py:496`); design; depends G6; 1 code line. class **R**. scheme none.

**G19 `UTCTime` null until the clock is set this boot**
- where: `codegen.py:290`; module `:106`. commits: 1b59a05d, 656fc82f. origin: A.U6.21 (rp2's RTC starts at 2021-01-01, `ports/rp2/main.c:141-145` v1.29.0)
- evidence: O — owner review `timestamps-before-ntp`, decision "Until NTP first sets the clock after a boot, readings are published with TS null, and UTCTime/LocalTime read null. … Once set, the clock counts as valid for the rest of the boot, even if a later sync fails." status "ok" (2026-10-01).
- legacy: no (UTC from `gmtime()` always, `sensortask-wozi.py:190`). form: design. device cost: 1 code line; one awaited call per GET. class: **R**. scheme: none.

**G20 `UnixTime` in /status** — `codegen.py:299`, module `:113`; 9bf22747, 656fc82f; A.U23.22; O — Req "`/status` publishes the current Unix time (epoch seconds, UTC) again, as legacy `/time/status`" (owner, 2026-09-29, OR94.a (15); `U23.md`); legacy **yes** (`sensortask-wozi.py:189` "Unix"); design; 0 extra lines. class **R**. scheme none.

**G21 `TimeStale`; UTCTime and the SGP40 backup keep the clock set this boot through a stale sync**
- where: `codegen.py:290, :300, :490-492`; `graph.py:65`; module `:106, :114, :140`
- what: /status `TimeStale` (null before the first sync, then "the last sync is no longer recent"); UTCTime and `SgpBackup` read `ntp.ntp_clock_valid` (set at the first sync, cleared by an NTP settings change) instead of `ntp_issynced` (pre-audit SGP40: `fram_ntp_callback=ntp.ntp_issynced`).
- commits: 656fc82f (SgpBackup grouping c3df14e1). origin: OF-79 (`open_findings.md:87`, "U18 lane N scan"), owner 2026-10-21
- evidence: O — "Clock time: Option b, but with a flag in /status showing it might be stale. Should be visible on the website as well - probably the current time actually is already showing on the status page? Then this would be easy to add." (owner, 2026-10-21, to "Keep timestamping once the NTP sync goes stale?"; commit 656fc82f; `owner_rulings_after_LN118.md`). The flag's form is "the agent's, decided on the owner's behalf for review".
- legacy: partly (`"Synced"` On/Off, `sensortask-wozi.py:189`; the backup timestamp gated on `conn.ntp_issynced`, `:86`).
- form: design. depends on: G19. device cost: 1 code line; one awaited call + `utc_now()` per GET. class: **R**. scheme: none.

**G22 Notification `State` code in /status**
- where: `codegen.py:307`; module `:119`. commits: 01032838.
- origin: the U22 commit ("stores a State code with each cycle (0 all evaluated, 1 off by setting, 2 no local time, 3 partly, 4 its own configuration unreadable)"); no owner decision found (searched `audit/review/decisions.json` + `answers.json`, `audit/actions/U22.md`, `open_findings.md`).
- evidence: H. legacy: no. form: design. depends: none. device cost: 0 extra lines; one key per GET (+ a state per cycle in src).
- class: **H**. triage: implausible as a fault — diagnostic; the trigger is normal (before NTP, warnings off) but nothing malfunctions without it.
- scheme: NH ("anything beyond the legacy firmware's behaviour is the owner's decision"); TLF.

**G23 ResetErrors refused while a reset is decided or the FRAM pause holds**
- where: `codegen.py:615-617`; module `:164`. commits: 06a8ae5d. origin: OF-145 (`open_findings.md:153`), A.U30.19
- evidence: O — "1 b, 2 b" (owner, 2026-10-13) to "Clear nothing when ResetErrors answers Failed in mempause?" and "Refuse ResetErrors from the supervisor's own reboot decision too?" (commit 06a8ae5d, OF-145).
- legacy: no (no ResetErrors in legacy). form: design. depends on: G8-G10 (the reset decision).
- device cost: 1 code line; a 2-tuple of bound methods; 2 calls per ResetErrors PUT. class: **R**. scheme: none (serves P7).

**G24 The webserver reads the system uptime (`uptime_s=`)** — `codegen.py:640`, module `:181`; f5c82557; OR137.a (1) "the uptime reader" (M.GEN.009); O (as G13: "last 24h with 24 counter buckets"); legacy no; design; depends G13; 1 code line. class **R** (part of G13's owner-decided form). scheme none.

**G25 `TestOverrides` in the build info, test images only** — `codegen.py:611-613`, `generate.py:180`; 15b8633c; OR139, M.GEN.009; O — "the tick test image (owner, 2026-10-01)" (`audit/REGISTER.md:580`; the verbatim owner text not in the files searched); legacy no; design; release image 0 lines. class **R**. scheme none (P4 holds for a release image).

**G26 SCD30 built with `cfg_path` (its config store)** — `codegen.py:481`, module `:139`; 5689e2f4; A.U15.12; O — OR99 "Do not use any measurement number or duration counter that could overflow … No flash writes, no extra FRAM chunk … true config parameters with a reasonable default, but can be changed by the user (that is an allowed API triggered flash write)" (owner, 2026-09-29; `U15.md` A.U15.12); legacy no (no SCD30 key in `sensortask-wozi.py:21`); design; 0 lines (keyword). class **R**. scheme none.

**G27 Networking settings: `HotspotPW` writable, `DNSFallback` group**
- where: `validate.py:118-125` (SETTINGS_GROUPS), `codegen.py:602-605, :747-755`; module `:151, :154`
- what: HotspotPW joins the identity group (masked, reconnect hook); DNSFallback a new NTP setting (default 8.8.8.8,1.1.1.1, emptiable).
- commits: f1f800e7, f76385a6. origin: A.U18.38, A.U18.10
- evidence: O — OR56.a (2) "becomes a config value with today's servers as its default: a website-visible, user-changeable networking setting that can be emptied; no hard-coded server remains" (owner, 2026-09-26; `U18.md` A.U18.10); HotspotPW: OR43.a (2) and A47 "(owner, 2026-09-18)" (tags only in `U18.md` A.U18.38).
- legacy: no. form: design. device cost: 1 code line. class: **R**. scheme: TLF, owner-decided (not counted).

**G28 (dev) UART receive-ring size per bus** — `codegen.py:183`; dev `:141-142` `rx_ring=512`; f76385a6; M.GEN.066, OR141 (4), OR143.a (2); O — OR143.a (2) "the cap and the DMA ring size … declared together in the bus/instance TOML and checked" (M.GEN.066 From); OR141 "all as recommended" (`AC_NOTES.md:188`); legacy no (no UART link in `legacy/firmware/modules/sensortask-dev.py`); design; 0 lines (keyword, value = driver default). class **R**. scheme none.

**G29 (dev) `TransferLimits` with the receive cap per link** — `codegen.py:561-572`; dev `:27, :155-156`; f76385a6; M.GEN.066, OR143 (tag only: "OR143 (go-ahead note, status withheld): the parked UART chunking becomes work", `AC_NOTES.md:188`); O; legacy no; design; depends G28; 1 import line; values = `DEFAULT_LIMITS`. class **R**. scheme none.

**G30 UART CRC per link (emitter; no device sets it)** — `codegen.py:110-118, :184-186, :407-409`, `buildspec.py` UART_CRC_MODES; f76385a6; A.S0930.01/.02; O — OR116 "I want both." and OR123 "Option a." (owner, 2026-09-30; `SUPP_owner_0930.md`); legacy no; design; 0 device lines on all six; 14 buildgen lines. class **R**. scheme none ("Always regard the modules as libraries", owner, 2026-10-23).

**G31 (dev) UART hazard-mode wiring**
- where: `codegen.py:230-239`; dev `:182` (`("UART_init", …get_hazard_report)`), `:199` (`add_status_command("UartHazards", …)`)
- what: dev's initiator publishes a hazard report and takes a dispatch-only `UartHazards` command that runs two initiations at once.
- commits: 656fc82f. origin: owner 2026-10-21/22
- evidence: O — "b - system shall be proven stable unter max load allover" (owner, 2026-10-21); "the link module is a necessity for testing, and it's testing code inside a module, but for a good reason, and the guard from being included in real deployed firmware is the fact that the module is never included in the config files for deployment boards. So this is a substantial exception from the usual scheme, but for good reasons." (owner, 2026-10-22; commit 656fc82f). The mode's form is the agent's.
- legacy: no. form: design. depends on: G29. device cost: dev only, 1 code line + one tuple entry; 0 on the five field devices.
- class: **R**. scheme: P4 — by design, the owner's stated exception.

The NeoPixel overlay's 300 s rewrite (OF-75, U22) lives in `src/asy_neopixel_driver.py`, outside group D; not recorded here.

---------------------------------------------------------------------------------------------------------------------

## 3. `devices/*.toml`

Not counted (checked): `trigger_sec`→`trigger_s`; FRAM part comments (A.U20.10); `# @tunable` tag comments (Part N
data); banners, wiring comments, the legacy path rewrite.

**D1 dev `rx_ring = 512` (×2)** — `devices/dev.toml` bus.uart0/uart1; f76385a6; feeds G28; O (as G28); Part N basis "estimated (agent, 2026-10-08)" (SPECIFICATION.md:12179); 2 TOML lines; value = default. class **R**. scheme none.

**D2 dev `max_transfer_bytes = 12192` (×2)** — dev `[[instance]]` uart_link; f76385a6; feeds G29; O (as G29); Part N "estimated (agent, 2026-10-08)" (SPECIFICATION.md:12180); 2 TOML lines. class **R**. scheme none.

**D3 dev `bench = true`** — 0c0ad52c; A.U26.01, OR78.a; O — OR78.a (1)-(2) "the bench board is named by data, not code … the pass-2 exception 'the hardware tier's fixed `dev`' … is withdrawn" (owner, 2026-09-28; `U26.md` A.U26.01); never emitted (`validate.py:77-79`); legacy no; 1 TOML line, device 0. class **R**. scheme none.

**D4 grkizi/klkizi/schlafzi `hardware_family = "arzi-neu"`**
- where: each `[device]`; checked `validate.py:485-487`; never emitted. commits: f76385a6. origin: A.U20.19; TOML comment "(agent, 2026-09-14)".
- evidence: H. legacy: no. form: design (a test label). device cost: 0 (1 TOML line ×3).
- class: **H**. triage: not a defect finding; implausible as a fault. Whether the tests' use of it is the "matrix deduplication" the owner allows (owner, 2026-10-23, `owner_rulings_after_LN118.md`) is not established here (test code, outside D).
- scheme: none established.

---------------------------------------------------------------------------------------------------------------------

## 4. Buildgen, host side (no device code)

Line figures are non-blank, non-comment; per row they are estimates from the function spans; the `rule=`/`fix=` lines
(363 in buildgen, 190 of them in `validate.py`) are counted once, in H1.

**H1 Error contract: rule, place and fix on every build error; raw exceptions become BuildError; BuildInternalError**
- where: `errors.py:1-26`; every raise in `buildgen/` (363 `rule=`/`fix=` lines); `model.py` `toml.*`; `twin_wiring.py` (OF-95)
- commits: f76385a6 (+ later units). origin: A.U20.17, A.U27.29
- evidence: O — "every message names what rule was broken, where … and how to fix it; user errors show the message without a Python traceback … every error path has a test asserting the exit code and that the message carries what, where and the fix" (owner, 2026-09-25, OR23.a (3); `U20.md` A.U20.17).
- legacy: n/a. form: design. depends: none. cost: device 0; ~370 host lines. class: **R**. scheme: none.

**H2 Atomic CLI output** — `generate.py:119-134` `_write_outputs` (tmp then rename, cleanup on error); f76385a6; A.U20.17's Req "on error no partial output remains" (owner, OR23.a (3)); O; ~16 lines. class **R**. scheme none.

**H3 Compile check of every generated text** — `generate.py:45-51` `_compiled`; f76385a6; A.U20.18 "(agent, 2026-09-14, `6db3199`; OR23.a (3), OR26.a)"; H; ~7 lines. class **H**. triage: implausible — it guards a generator bug, and the generated tree is already compiled by ruff/mypy and by every test that imports it. scheme: NH.

**H4 Frozen set seeded from the generated module's imports (`CORE_MODULES` gone)**
- where: `frozen_modules.py:1-78`. commits: f76385a6. origin: A.U20.13, G5/R48
- evidence: O — Req "A device's frozen-module set is the seed (declared drivers plus the fixed core) closed over real static imports after `TYPE_CHECKING` stripping … A machine check guards the graph" (owner, 2026-09-09, `6aed3c9`, L11; `U20.md` A.U20.13).
- device effect (by reading): the five field images no longer freeze `asy_uart_driver` (pre-audit `CORE_MODULES` listed it; only `asy_uart_link_driver` imports it at head) — a smaller image.
- form: design. cost: device -1 frozen module on five images; host -4 lines. class: **R**. scheme: none (serves P8).

**H5 Parse/import caches** — `frozen_modules.py` `_imports_in` (lru_cache), `source_ast.py` (parse cache, new 20 lines), `generate.py` `_sets_config_log_off`; f76385a6/15b8633c; OF-154 (`open_findings.md:162`); evidence **F** — measured on the pre-cache code: "spends 17 of 42 s tearing down 5.2M objects … 49 of 57 s of `generate_device` under cProfile"; design; ~25 host lines. class **R**. scheme none.

**H6 `expected_facts` boot oracle**
- where: `generate.py:27, :61-117, :137-151`. commits: f76385a6 (+0c0ad52c). origin: A.U20.07, OR47.a (1)
- evidence: O — "proven for every generated device by recording the real boot sequence in the twin and asserting it" (owner, 2026-09-26, OR47.a (1); `U20.md` A.U20.07).
- form: design, but `_expected_setups` re-implements codegen's setup-order rule (`generate.py:61-67` vs `codegen.py:758-770`) and `_fram_wired` codegen's `_fram_var` rule — deliberately "never read back from the generated text" (`generate.py:138-139`).
- cost: device 0; ~70 host lines. class: **X** — right intent, a second copy of two codegen rules.
- scheme: P8; P4 (a test oracle in the build chain, though not in the image).

**H7 Generated REST reference** — `api_reference.py` (new, 205 lines / 167 code), `build/generated_src/api/*.json` (not an input of `scripts/build_website.sh`, so not in the image); f5c82557; A.U19.20, M.GEN.033; O — Req "The new API is the only reference" (owner, 2026-09-26, G6/R38) and owner review `rest-api-frozen-at-release` "ok" (2026-10-01); design; device 0. class **R** (whether 167 lines is the least that serves it was not judged). scheme none (serves P12).

**H8 Website definitions follow the new firmware** — `definitions.py` (+275 code), `web_tag.py` (+203 code); output `build/generated_src/definitions/*.json`, inlined into the frozen site (`scripts/build_website.sh:68-82`); 1b59a05d and later; status rows for G13-G22, the command options with a confirmation (owner, 2026-10-02), errcount rows for BMP3xx and the SCD30 store, field keys (`format`, `codes`, `decimals`: owner note "Fine, and maintain a reasonable number of digits per value … But only for the website, the API delivers full resolution.", 2026-10-02), the `web.*` checks (A.U20.25: OR43.a (2) "every API value wired to the website, nothing missing", owner, 2026-09-26); O (mostly); device: website bytes only (wozi definitions 63,083 B before gzip), no firmware code; the website lane owns the content. class **R**. scheme: not judged at this grain (website lane).

**H9 Error-number catalog** — `error_catalog.json` (new, 237 lines; read by tests and definitions, not frozen); 43aced07 + later: 127 code rows at creation (the numbers `src/` already logged, renumbered into owner bands), +33 code rows in later units (U9 1, U11 1, U13 3, U15 5, U16 4, U17 4, U18 8, U19 3, U30 3, U31 1 — each a `src/` log-entry type whose evidence is the src lanes'), status tables ResetReason/VOCState/FRCState/CalLight/NotifyState; O — "harmonize errno and wrnno globally (owner, 2026-09-25, paraphrase)" (commit 43aced07), and owner review `reset-reason-codes` "Good, and make the numbers clickable in the website like the errno and wrnno numbers." (2026-10-02); design; device 0. class **R**. scheme: P11 (`CONSOLIDATION.md:35`, "an owner decision quotes the owner") — only a paraphrase is recorded for the catalog itself.

**H10 UART receive checks: ring size, receive cap, CRC width in the rxbuf floor** — `validate.py:1073-1126`, `_uart_crc_width`; f76385a6; M.GEN.066, A.S0930.01 (5); O (OR143.a (2), OR116/OR123 as G28/G30); ~45 lines. class **R**. scheme none.

**H11 UART CRC mode and pair agreement** — `validate.py:1047-1070, :1129-1167` (crc parts); f76385a6; A.S0930.01; O ("I want both.", "Option a.", owner, 2026-09-30); ~20 lines. class **R**. scheme none.

**H12 Pair baud agreement** — `validate.py:1129-1167` (`instance.uart-baud-mismatch`); c11ca0aa; A.U17.32 (J.6 "agreed out of band … nothing is negotiated", owner, 2026-09-11 — the rule; the build check is the agent's extension); H; ~8 lines. class **H**. triage: implausible — dev states 115200 on both ends; only a TOML edit trips it. scheme: NH.

**H13 One instance per UART bus** — `validate.py:1016-1034` (`bus.uart-shared`); f76385a6; A.U20.01 ("Both ends on one bus build clean", by reading; the owner rule is one initiator + one responder); H; ~19 lines. class **H**. triage: implausible (dev uses uart0 and uart1; a TOML edit only). scheme: NH.

**H14 UART timing ranges: poll-wait 1-9 ms, poll-idle range, reply-timeout ceiling** — `validate.py:1170-1213` (the reply-timeout floor is pre-audit); c11ca0aa, f76385a6; A.U20.18, A.U17.21 ("build-time half extends the owner's C.7.2 scope (owner, 2026-09-24) (L18, agent extension)"); H; ~32 lines. class **H**. triage: implausible (dev's values are the defaults). scheme: NH; DL (candidate).

**H15 UART value ranges: baud, rxbuf, txbuf** — `validate.py:981-1013`; f76385a6; A.U20.34 "(agent, 2026-09-26, widened 2026-09-28)"; H; ~25 lines. class **H**. triage: implausible (a TOML edit only). scheme: NH.

**H16 I2C frequency and timeout ranges** — `validate.py:579-612`; f76385a6; A.U20.34 (agent); H; ~20 lines. class **H**. triage: implausible. scheme: NH.

**H17 I2C timeout ceiling and loop-hold bound** — `validate.py:615-634` (`bus.i2c-timeout-consumer`), `HardConsumer`, `smallest_hard_consumer()` (also read by the twin loop-lag scenario and the bench lag test), `bus.i2c-timeout-max`; 72b12815, f76385a6; A.U31.08 "(agent, 2026-10-21)"; H; ~45 lines. class **H**. triage: implausible — wozi's `i2c0` and dev's `i2c1` state 200 000 µs (400 ms for a two-transfer read) against the 5 000 ms watchdog room and dev's link slack, and pass; a TOML edit only. scheme: NH; DL (candidate); CLAUDE.md:237-242 ("a call that never returns is the watchdog's") — touched, not violated: it adds no I2C-level timeout.

**H18 Boot bus-clear budget** — `validate.py:97, :202-218` (`bus.boot-clear-budget`, 3/4 of the watchdog); f76385a6; Part N `wdt.timeout_ms` row "(agent, 2026-10-07)" (SPECIFICATION.md:12052); H; ~18 lines; depends on the src boot clear (OR113 "I2c option a, clear at boot", owner, 2026-09-30). class **C** (root: the boot bus clear). triage: implausible (all six TOMLs build). scheme: CR; DL (candidate); NH.

**H19 `[device]` ranges: `conn_fail_to_hotspot` ≥ 1, `hotspot_time_min` 1..35791** — `validate.py:446-465`; f76385a6; A.U20.34 (agent; RF148/RF152 by reading: "0 or negative builds, then hotspots on the first failure … or becomes a 0/negative Timer period"); H; ~20 lines. class **H**. triage: implausible (all six state 5 and 8). scheme: NH.

**H20 Hostname as a host label at build** — `validate.py:407-443` (part), `_host_label_ok`; f76385a6; A.U6.29 (agent); H; ~13 lines. class **H**. triage: implausible — the pre-audit build already pins `hostname == "SensorStation<name>"` (`validate.py@25caf528` `_check_device_table`), and each name is fixed in its TOML. scheme: NH; P8.

**H21 NTP retry-cap range** — `validate.py:830-862` (`device.ntp-retry-max-range`); f76385a6; agent; H; ~8 lines. class **H**. triage: implausible (no TOML states it). scheme: NH.

**H22a Non-finite numbers refused in `@limits` fields** — `validate.py:787-827`; f76385a6; A.U20.24; O — Req "`nan`/`inf` are rejected" (owner-confirmed "(owner, 2026-09-10)", `12d62b6`, L13; `U20.md` A.U20.24); ~6 lines. class **R**. scheme none.

**H22b `irq_pull_up` must be a bool; a multi-instance driver must state `name_ext`** — `validate.py:668-695, :865-903`; f76385a6; A.U20.18 (agent), A.U20.29 (agent); H; ~15 lines. class **H**. triage: implausible (dev states `irq_pull_up = false`; every sensor instance states `name_ext`). scheme: NH.

**H23 Name collisions: mandatory loggers and `CFGMGR_<name>` in the logger check; GET settings-key collisions** — `validate.py:717-747, :922-937`; f76385a6; A.U20.38 (G6.078 by reading; the runtime's last-wins rule is owner-confirmed, 2026-08-12); H; ~34 lines. class **H**. triage: implausible (the six devices pass; only a new driver or setting could collide). scheme: NH.

**H24 A `{source, field}` reference must name a `get_data()` field** — `validate.py:940-978`, `driver_registry.data_fields` (`:193`); f76385a6; A.U20.20 — SPEC L.6.3 claimed this check and none existed (G8.020, by reading); H; ~25 lines here (+ `data_fields`, H32). class **K** — the knowledge holds (the spec claimed an absent check); the code is in doubt (correcting the claim was the smaller fix). triage: implausible (the TOMLs name Temp/Hum/CO2/VOC). scheme: NH.

**H25 `warn_*` only on the notification instance** — `validate.py:1240-1264`, `signals.py` (catalog moved from codegen); f76385a6; A.U20.30 "(agent, 2026-09-09)"; the unknown-signal refusal moved from codegen (pre-audit raised it there); the instance restriction is new; H; ~12 lines. class **H**. triage: implausible. scheme: NH.

**H26 Keyword-only `_Default<Field>` parameters join the default sub-table** — `defaults.py`, `validate.py:341-381`; f76385a6; A.U20.21 (gap by reading; OR67 "yes, that is the case, so the current state looks correct to me", owner, 2026-09-26, confirms the explicit default, not this coverage); H; ~8 lines. class **H**. triage: implausible (no current TOML uses a default provider with keyword-only parameters; not counted further). scheme: NH.

**H27 Build reads `src/` facts by AST instead of mirrored constants** — `validate.py` `module_int/float/str_const`, `ntp_backoff`, `init_int_default`, `_wifi_schema_bounds`, `_owns_config_store`; codegen's explicit ServingLimits/NtpTiming/TransferLimits values; f76385a6; A.U20.27; O — Req "Two build tables stay hand-kept … Every other value buildgen restates from `src/` … is AST-read or pinned both ways" (owner, 2026-09-18 and 2026-09-24; OR43.a (3), OR68.a (2); `U20.md` A.U20.27); ~70 lines; device 0 (values equal the defaults). class **R**. scheme none (serves P8).

**H28 GPIO legality per RP2040 Table 279** — `pico_gpio.py` (83→73 lines), `validate.py:221-254` (moved); f76385a6; A.U20.09; O — OR53 (1) "1. a" — "`buildgen/pico_gpio.py` accepts every pin function the RP2040 offers (datasheet Table 279) … its wrong comments are corrected, with a test per newly legal pin" (owner, 2026-09-26); widened (GP22/GP28 I2C, SPI on GP20-22/26-28, UART1 on 20/21), `csn` role dropped; device 0 (no TOML uses the new pins). class **R**. scheme none.

**H29 Tag parsers refuse what they cannot read** — `schema_ast.py` (+87 code: unreadable/malformed schema), `tag_comments.py` (+32: `specs_for()` registration, column-0 comments), `limits.py` (+50), `requires_tag.py` (+28: non-finite, typed comparison), every schema field `@web`-tagged or hidden; f76385a6; A.U20.24/.25; O — L13 "every family runs on `buildgen/tag_comments.py`'s shared scanner, registered mechanically …; `nan`/`inf` are rejected; a column-0 comment inside a function is not module level" (owner-confirmed "(owner, 2026-09-10)"), and OR43.a (2) (owner, 2026-09-26); ~150 lines net of H1. class **R**. scheme none.

**H31 Twin wiring plan typed, one producer, chip addresses read from the drivers** — `twin_wiring.py` (66→137); f76385a6; A.U20.28 "(agent, 2026-09-11, `fcc5339`; OR43.a)", OF-95 (scan); H; ~48 lines; twin/test only. class **H**. triage: implausible (no device effect). scheme: NH.

**H32 Registry helpers** — `driver_registry.py` (120→244): `data_fields()` (for H24), `class_has_read_triggers()` (for G5), `parse_name_constant()` (for H23, H6, H8), renamed overrides; f76385a6, 41b47f1d; ~92 lines. class **C** (roots H24, H23; G5 for the read triggers). scheme: CR.

Not counted (checked): `graph.py` (+30: the edges that follow the constructor-keyword wiring, construction order only),
`model.py` (+45: typed TOML, `device_wiring`, `MAINTENANCE_NAMES`), `signals.py` (catalog moved from codegen),
`jsontypes.py` (types), `value_wiring.py`/`wiring.py` (grammar restated; setter mode removed with its last `src/`
user), `buildspec.py` (UART_CRC_MODES is G30's; `trigger_s` rename), `version.py` (the 2.0b0 value), `__init__.py`.

---------------------------------------------------------------------------------------------------------------------

## 5. Per-file totals (rows; code lines)

| file | R | K | H | X | C | violations by rule |
|---|---|---|---|---|---|---|
| boot entry `_main.py` | 3 (4; B4: 0 in a release image) | 2 (10) | 1 (2) | 0 | 1 (1) | NH 2, CR 2 |
| device module `sensortask_<d>.py` | 29 (39 new wozi lines, +2 dev; -61 removed: G4 -30, G8 -15, G11 ~-15, G12 -1) | 0 | 4 (0: keys on R lines) | 0 | 0 | NH 4, MC 1, P8 1, TLF 1 (+ P4 1 owner-excepted, G31) |
| `devices/*.toml` | 3 (5 TOML lines, dev) | 0 | 1 (3 TOML lines) | 0 | 0 | none |
| buildgen host | 13 (≈1,516, the remainder; + 237-line JSON) | 1 (≈25) | 15 (≈314) | 1 (≈70) | 2 (≈110) | NH 17, DL 3 (candidates), CR 2, P8 2, P4 1, P11 1 |

Device totals: R 35 rows (32 emitted, 3 TOML): 43 emitted code lines on wozi (2 of them moved) + 2 on dev, 5 TOML
lines; K 2 rows, 10 lines; H 6 rows, 2 emitted lines + 3 TOML lines; C 1 row, 1 line. Buildgen's +2,035 host lines:
R ≈1,516, K ≈25, H ≈314, X ≈70, C ≈110 (estimates from function spans; the R figure is the remainder).

Most-violated rules in group D: NH 23 rows (B5, B6, G5b, G14b, G17, G22, H3, H12-H21, H22b, H23-H26, H31 — 17 of them
buildgen rows, 16 of those build-time checks no current TOML can trip); CR 4 (B6 as root, B7, H18, H32); DL 3
candidates (H14, H17, H18); P8 3 (G17, H6, H20).

## 6. Cascades

1. **Reset-record chain** (root G1, O): G1 → G2 (O) → G14 (O), G14b (H) → B5 (K) → B6 (K) → B7 (C). The H/K links exist
   so that console and loop-end exits do not read as a plain watchdog reset; the src decode-order changes (F4d, F4e,
   owner-answered) sit on the same chain, src side.
2. **Controlled shutdown** (all O): G9 → G10 → G8 → G23 (`is_reset_decided`).
3. **Clock validity** (O at each step): G19 (gate on the first sync) → OF-79 (gating on `ntp_issynced` blanked UTCTime and
   the SGP40 timestamps on a stale sync) → G21 (`ntp_clock_valid`, TimeStale; the SGP40 backup moves to it).
4. **Drop window** (O): G13 → G24.
5. **UART link, dev** (O): D1/D2 → H10 → G28/G29; G30 → H11; G31 → G29.
6. **Trigger stagger**: G5 (O) → G5b (H, no effect on any device) → `class_has_read_triggers` (H32, C).
7. **Timing-budget checks**: the src boot bus clear (O, OR113) → H18 (C) → H17 (H) → `smallest_hard_consumer()`, also
   read by twin and bench tests outside D.
8. **Source-field check**: H24 (K) → `data_fields()` (H32, C).
9. **Error contract** (O): H1 → the `rule=`/`fix=` lines on every check (190 in `validate.py`).
10. **Lint-clean generated text** (restyling): `_lit()`/`_sorted_imports()` → B7's `noqa` churn (c87249c6 ↔ b8b7207e).

## 7. Verifications

- **V1 (B3), platform, pinned source** `/root/pico-toolchain/micropython` (v1.29.0): `py/objexcept.c:399-415` allocates
  the message's `mp_obj_str_t` with `m_new_obj_maybe`; with no emergency buffer (or one too small) it returns
  `mp_obj_exception_make_new(exc_type, 0, 0, NULL)`, an exception with no message; `ports/rp2/mpconfigport.h:126`
  enables the buffer feature with size 0 ("implies dynamic allocation", `py/mpconfig.h:836`), so nothing is reserved
  until `alloc_emergency_exception_buf()` runs. **Confirmed** (mechanism). Whether a real exhaustion on rp2 leaves no
  16 B for the string is heap-state dependent: hardware round.
- **V2 (G17), reproduction against the pre-audit code**: `src/` of `25caf528` extracted to `work_D/pre/src` (git archive,
  no worktree write); `work_D/v2_unpersisted_pre.py` sets up a ConfigManager, points its file into a missing directory
  and writes a value. 3 runs (RUNS.md `v2_pre_1..3`, rc=0 each), identical: `write True {'A': 'Valid'}` and
  `CFGMGR_T … ErrNum [..., 3, 14]`, i.e. E14 "running unpersisted" logged and shown in errcount (`work_D/v2_run1..3.log`).
  **Refuted**: the pre-audit code did not hide an unpersisted config.
- **V3 (pause callback), code reading**: head `src/asy_notification_service.py:375-377` `set_override_led()` always
  returns True ("clamps, never refuses"), as the pre-audit callback did. **Refuted** (no behaviour change; not counted).
- **V4 (B5, B6), pinned source**: `ports/rp2/main.c:243-262` — after `main.py` returns (an exception printed by pyexec
  included) the friendly REPL loop runs with the watchdog still armed, so the pre-audit entry already ended in the same
  watchdog reset; only `PYEXEC_FORCED_EXIT` (a `SystemExit`) soft-resets, and `src/*.py` raises none. **Confirmed**: the
  findings' mislabel (code 2) is real; the consequence is the label only.
- **V5 (G5b), generated output**: `_collect_trigger_starters` on all six devices against their construction order and
  buses (wozi `(sgp40, bmp3xx)`, both `i2c1`; dev `(sgp40, bmp3xx, isl29125)`, `i2c1, i2c0, i2c1`; arzi/neu `(sgp40,)`).
  **Refuted**: the spread changes no device's order.

No other H row in group D was triaged suspicious, so no further run was made.

## 8. Hardware-round list

1. B3/V1: a caught heap-exhaustion MemoryError on the dev board printing its full text (Part N
   `gc.emergency_exc_buf_bytes`, "measurement owed … L3").
2. B1: the first unfed stretch — `WDT()` through the ~1.1 s product import and construction to the first setup feed —
   stamped on silicon (Part N `boot.unfed_stretch_1_ms`, SPECIFICATION.md:13355).
3. G1/G2, B5/B6: reset reasons 21, 22 and 10 + phase read back on silicon (OF-107's "C (round R1, items H10/H12)").
4. G28/D1: dev's 512 B receive ring's peak fill during a config flush (Part N `dev.uart_rx_ring`, "measurement owed").

## 9. Minimal-change list (R and confirmed items), against `codegen.py@25caf528` unless named

| item | smallest change | size | pinning test |
|---|---|---|---|
| B1 | boot entry starts `from machine import WDT` / `watchdog = WDT(timeout=8000)`, calls `main(watchdog=watchdog)`; `build_system()` takes it and drops its own WDT line and global | ~6 emitter lines changed | `test_real_device_boot_entry_arms_the_watchdog_as_its_first_statement`, `test_real_device_module_constructs_no_watchdog_and_its_boot_entry_exactly_one` |
| B2 | `import sys` / `sys.path.insert(0, ".frozen")` before the device import | +2 | `test_real_device_boot_entry_puts_frozen_code_first_before_any_product_import` |
| B3 (confirmed) | `import micropython` / `micropython.alloc_emergency_exception_buf(100)` | +2 | `test_real_device_boot_entry_reserves_the_emergency_exception_buffer_before_the_device_import` |
| B4 | an `autostart=False` branch: the shared head + the printed start line; written by the CLI, frozen by `--no-autostart` | ~12 emitter + ~5 `generate.py` | `test_real_device_boot_entry_variants_share_one_head_and_differ_only_in_the_watchdog_and_the_tail` |
| G1, G14 | `reset_reason = begin_boot()` first in `build_system()`, `reset_reason=` to SystemService, `"ResetReason"` key | +3 | `test_real_device_build_system_only_constructs_with_the_reset_reason_read_first` |
| G2, G3 | five `sysfunct.boot_phase(...)` lines; `start_tasks()` before `start_timers()`, the NTP force sync after them, then `supervise_tasks()` | +5, 3 moved | `test_real_device_main_runs_the_boot_sequence_with_its_phase_marks` |
| G4 | the unrolled batch (`codegen.py@25caf528:441-466`) becomes `await sysfunct.run_setups([...])` with `webserver.setup` last | -27 emitted | `test_real_device_hands_every_setup_to_one_list_in_the_fixed_order` |
| G5 | the readers' `get_trigger_starters()` in construction order, passed first to `start_timers()` — without G5b's spread | +5 emitted, ~8 emitter | `test_real_device_main_starts_read_triggers_apart_from_the_timer_starters` |
| G6, G18 | `_collect_task_names()`, `task_names=`, `"LastTaskEnd"` key | +6 | `test_real_device_names_each_task_starter_once_over_the_starters_own_module_tuple` |
| G7 | drop the fram exclusion from the task/timer collectors (`codegen.py@25caf528:660-664`) | -3 emitter | `test_real_device_collects_the_fram_managers_starters` |
| G8 | `_flush_pending_configs()` becomes `_collect_config_stores()` passed as `config_stores=`; the callback's two flush calls go | -8 emitted | `test_real_device_collects_every_config_store_for_the_service_to_flush` |
| G9, G10 | two `if cmd == …: return await sysfunct.…()` arms; the existing three return the service's bool | +4 | `test_real_device_system_command_callback_answers_the_service_for_every_command_word` |
| G11 | `return neopixel.led_signal(r, g, b, t)` in place of the `request_signal` call | 1 line | `test_real_device_led_callback_takes_the_validated_values_and_only_signals` |
| G12 | read IPv4/Subnet/Gateway/DNS/RSSI from the one `conn.get_data()` snapshot | 4 lines changed | `test_real_device_networking_status_reads_one_wifi_snapshot_and_no_radio` |
| G13, G24 | `"HTTPDropped"`, `"WifiTS"` keys; `uptime_s=sysfunct.get_uptime` | +2 | `test_real_device_networking_status_reads_the_webservers_drop_window`, `test_real_device_webserver_reads_the_system_uptime_for_its_drop_window` |
| G15, G16, G20 | `"MemFree"`, `"ConfigFaults"`, `"UnixTime"` keys | +1-2 | `test_real_device_system_status_reports_every_system_key_in_order` |
| G19, G21 | `utc = time.gmtime() if await ntp.ntp_clock_valid() else None`; `"TimeStale"`; the SGP40 backup's clock callback `ntp.ntp_clock_valid` | +3 | `test_real_device_shows_utc_time_through_a_stale_sync_and_flags_it`, `test_real_device_gates_the_voc_backup_timestamp_on_the_clock_set_this_boot` |
| G23 | `reset_refusals=(sysfunct.is_reset_decided, fram.get_pause)` | +1 | `test_real_device_reset_errors_is_refused_by_the_reset_decision_and_the_fram_managers_own_pause` |
| G25 | `"TestOverrides"` in the build info only when given | +2 emitter | `test_a_test_override_is_named_in_the_build_info_and_a_release_build_names_none` |
| G26 | `cfg_path=cfg_path` in `_build_args_scd30` | +1 | `test_real_device_constructs_scd30_with_the_boot_config_path` |
| G27 | `"HotspotPW"` in the identity group; `SettingsGroup(ntp, ("DNSFallback",))` | +1-2 | `test_real_device_networking_settings_publish_the_hotspot_password_and_the_dns_fallback` |
| G28/D1, G29/D2 | `rx_ring` in the UART keyword list; `TransferLimits(...)` with `max_transfer_bytes`; the two TOML keys per link | ~4 emitter + 4 TOML | `test_real_device_passes_each_uart_bus_its_stated_rx_ring`, `test_real_device_hands_each_link_its_transfer_limits_as_one_object` |
| G30 | `crc` TOML key → `crc=CRC16()` on the link's bus | ~10 emitter + H11 | `test_a_link_naming_a_crc_mode_gets_that_check_on_its_uart_bus_and_its_import` |
| G31 | dev's `("UART_init", …get_hazard_report)` entry and `add_status_command("UartHazards", …)` | +2 emitter | would assert: dev's module registers `UartHazards` and no field device's does (definitions side: `test_every_command_and_the_error_reset_ask_before_they_are_sent`) |
| D3 | `bench = true` in dev.toml and its bool check | +1 TOML, +2 | `test_device_bench_flag_is_accepted_and_emitted_nowhere` |
| H1, H2 | `rule=`/`fix=` on each raise; tmp-then-rename output | as built (owner's requirement covers every site) | `test_each_rule_aborts_with_one_line_naming_place_and_fix`, `test_a_write_failing_part_way_leaves_no_output_file` |
| H4 | seed the closure from the generated module's imports | ~15 | `test_the_frozen_set_is_the_closure_of_the_generated_modules_imports` |
| H5 (F) | memoise each file's parse by its text | ~10-25 | would assert: one parse per file text across six `generate_device()` calls |
| H7 | the generated REST reference | 167 (not minimised here) | `test_the_routes_are_exactly_the_route_table_and_no_legacy_path` |
| H9 | the catalog file | 237 JSON | `test_catalog_shape` |
| H10, H11 | ring/cap/CRC checks | ~65 | `test_each_rule_aborts_with_one_line_naming_place_and_fix[bus.uart-rx-ring]` and its `instance.uart-transfer-cap`/`instance.uart-crc-mismatch` rows |
| H22a | `math.isfinite()` refusal in `@limits` fields | ~6 | `test_a_non_finite_value_in_a_limited_field_is_rejected` |
| H27 | AST reads of the `src/` defaults | ~70 | the source-agreement tests (`test_ntp_timing_carries_the_effective_backoff_pair`) |
| H28 | the Table 279 pin table | ~+4 | `test_newly_legal_pin_is_accepted` |
| H29 | refusals in the tag parsers | ~150 | `test_each_rule_aborts_with_one_line_naming_place_and_fix[tag.non-finite-number]` and the schema rows |
| H8 | website definitions | website lane | — |

Scratch: `S/u35r/scan/work_D/` (`v2_unpersisted_pre.py`, `v2_run1..3.log`, `pre/src`, `catalog_evo.py`, `why.sh`,
`validate_old.py`). RUNS.md lines: `U35 scan D v2_pre_1`, `_2`, `_3`, each with its done line.
