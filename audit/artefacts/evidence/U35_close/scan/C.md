C scan, written by the lane (Wed Oct 28 07:45:15 UTC 2026)

Group C: `src/asy_i2c_driver.py`, `src/asy_spi_driver.py`, `src/asy_neopixel_driver.py`, `src/asy_notification_service.py`,
`src/voc_algorithm.py`, `src/asy_bmp3xx_driver.py`, `src/asy_scd30_driver.py`, `src/asy_sgp40_driver.py`,
`src/asy_isl29125_driver.py`. Range `25caf528..497b3eda`, read in `S/wt-u35int` (nothing written there). None of the nine
files was renamed in the range. Brief: `S/u35r/briefs/scan_firmware.md` (with its addendum). This replaces the unfinished
`inventory/C.md` work (no file was written there).

## How to read the rows

- "pre-audit" = the file at `25caf528`; "head" = `497b3eda`. Line ranges are at head.
- **Evidence O** is split, so the owner sees what was decided where: **O-spec** = the owner decided this behaviour (a
  ruling or a review-page answer naming it); **O-gen** = an owner principle that the agent applied to a case it found by
  reading (OR113 recovery ladder, OR103/OR105 counters, OR109 races, OR31.a task ends). Both count as O, so class R, but
  every O-gen row also says whether its trigger is plausible.
- Review-page answers are `audit/review/answers.json` (status `ok` = the owner's "fine", OR140.a:
  `PROJECT_AUDIT_PLAN.md:551` "every "fine" stands as an owner-confirmed decision"); the decision text is
  `audit/review/decisions.json` under the same id. The routine group was left unanswered (OR140) and is never O here.
- **F**: no row in this group has an observed failure of the pre-audit code (bench, field, or a pre-existing test). The
  only bench observation in the range (`83c9920a`, SGP40 W13 slots after a hotspot episode, bench 2026-09-25) was a
  log-slot effect whose fix in this file was removed again when the central newest-entry rule landed (U3, OR35.b): no
  net change in `asy_sgp40_driver.py`. Fail-first tests written by a lane for its own fix are not counted as F (they
  confirm a reading against a fake); they are named where they exist.
- **Shared mechanisms outside group C** (the base reader's ladder `_recover_bus()`/`_init_failed()`, `utc_now()`,
  `report_if_fatal()`, `_timer_failed()`/`_timer_fault()`/`_rearm_timer()`, `_error_check(condition=)`, the FRAM
  tri-state read, the GET unavailable marker's base half) are rows of other groups; here only their call sites and the
  driver-side hooks are rows, classed C with the root named.
- **Scheme rules** (the field "scheme"), cited by tag:
  - MIN: owner 2026-10-28, "the way it flows into the firmware and buildgen is *really* minimal change"
    (`scan_firmware.md:4-5`).
  - HYP: owner 2026-10-28, "Speculative and hypothetical effects maybe, maybe not. Resulting cascades are a red flag at
    least." (`scan_firmware.md:6-7`); applied to H rows that carry code and to C rows.
  - DELAY: owner, "hardcoded delay checks like this are a very bad, very awkward pattern" (`scan_firmware.md:106-107`).
  - FEAT: CLAUDE.md:508-512, "The refactor should end up with the *same top-level features* ... not a feature change."
  - TYPING: owner 2026-10-27, "A strong hint for an unnecessary check is that it is proven to be fully covered by typing
    adherence alone, and that it is unreachable with today's code" (`S/u35r/recovered/owner_rulings_after_LN118.md`).
  - OR35a: `PROJECT_AUDIT_PLAN.md:338`, owner: "Console logs actually should keep printing all."
  - OR110: `PROJECT_AUDIT_PLAN.md:490`, owner: "If a timer allocates, never reaches any critical value and frees some
    seconds later, it's less critical."; with OR109 (`:488`): "If the VOC algorithms allocates and the allocation goes
    after it's done and gc can clean the mess up, everything is settled."
  - P4: `audit/CONSOLIDATION.md:28`, "Premium code, one material, nothing in the product for tests".
  - G1: SPECIFICATION.md:7621-7623, "If a match exists, use it directly, never reimplement even a version that looks
    locally simpler."
  - P6: `audit/CONSOLIDATION.md:30`, "Efficient and compact on low-end hardware".
  - A rule a row claims to serve is written "claims P1/P2/P3/P7".
- Device cost: code lines are added non-comment lines (approximate where marked ~); run-time costs per cycle or event.

## Owner quotes used (verbatim, with source)

- OR113 (2026-09-30, `PROJECT_AUDIT_PLAN.md:496`; CLAUDE.md:237-239 "(owner, 2026-09-30)"): "2. I2c option a, clear at
  boot. My instructions anyway were meant in the way "always try to solve / recover from issues with the smallest possible
  blast radius" - not like "never reset the bus", also in mid operation! So if there is a an error on the bus and / or a
  participant, try to recover mildly, but escalating up to a full bus reset is absolutely allowed if the mild measures
  don't work out. Apply this idea throughout!"
- OR101 (2026-09-29, `:472`): "My decision: Fix the bugs, and make sure the fix of (4) does not depend on a UTC timestamp
  (ant not on UTC at all)" — the list is `audit/pass3/D4.md:243` (D4.37 VOC sentinels, D4.53 SGP40 stale command, D4.55
  SGP40 ticks, D4.61 SCD30 offset rounding, D4.62 SCD30 range gate, D4.64 BMP MeanAtmTemp, D4.65 BMP PressOffset, D4.66
  ISL29125 INT). Each was "proven at the code level" by reading; the owner approved the fix.
- OR102 (2026-09-29, `:474`): "... 5. a ..." answering `audit/pass3/D4.md:255-257` "REST LED command while a signal runs:
  refuse or queue? ... (a) Refuse at once".
- led-request-internal-queue (answers.json, 2026-10-02): "Fine, and this for a reason: internal LED commands are
  guaranteed to be bounded by number and frequency, they won't flood the device. External commands might quickly flood it
  into exhaustion. The refusal and error message lets the external caller knows to try again later." (decision: "An
  internal notification request instead waits for the running signal up to a deadline and then queues").
- OR69 (2026-09-26, `:408`): "... 6. a ..."; OR69.a (6) (`:409`): "C03: the notification active window supports a window
  that spans midnight".
- OR104 (2026-09-29, `:478`): "... 2: option (a) / the "never UTC" goes for the others as well and might be a good
  candidate for a function which lives in the system service or the base classes".
- OR109 (2026-09-29, `:488`): "Latent SGP40 race: Fix this. No races allowed (see specs)."
- OR103 (2026-09-29, `:476`): "I want to add a new central requirement for the whole code: No unbounded counters
  anywhere."; OR105 (`:480`): "Concerning the counter cap, I want to exactly avoid allocations happening at some point."
- OR98 (2026-09-29, `:466`) / OR99 (`:468`): "1 a, 2 a. Conditions: * Do not use any measurement number or duration
  counter that could overflow ... * No flash writes, no extra FRAM chunk (FRAM stays optional) * The deliberately
  settable and possibly drifting over time criteria (like noise, change rate, etc.) become true config parameters with a
  reasonable default, but can be changed by the user"; review `scd30-calibration-readiness` status ok.
- OR42.b (2026-09-26, `:354`): "This is a serious gap. My goal is that the functionality you found in the legacy code is
  restored, and architectually fitted into the existing base classes setup such that it uses the same mechanism as the
  standard persistence to write only if a value differs."; OR42.c (`:355`): "Perfect match".
- OR76 (2026-09-28, `:422`): "For the overlap calibration of the ISL29125, we should add a field to the measurements API,
  a numerical code which tells if the current brightness is suitable, too high or too low for determining the calibration
  factor"; review `state-code-values` status ok.
- OR97 (2026-09-29, `:464`): "16 b 17 a 19 b" (17 = the SGP40 VOC-algorithm state field, OR97.a (17)).
- OR31.a (2026-09-25, `:331`): "Rather make sure the tasks themselves are written such that they either really work or
  return / end in any other case which cannot be handled internally".
- Review answers with status ok (answers.json; decision text in decisions.json): `timestamps-before-ntp`,
  `sgp40-wait-zero`, `pres-offset-warning`, `threshold-rewrite-failure`, `stale-as-fresh-every-driver`,
  `sgp40-chip-identity`, `negative-backup-age`, `state-code-values`, `c-stack-reboot`, `scd30-write-path`.
- Owner 2026-09-16, as quoted in commit `2977c4e0`'s message: "we do not even add errno/wrnno for the out of FRAM memory
  … Handle via mpremote."

---

## src/asy_i2c_driver.py

Commits: c3df14e1 (U5), 01e8e3eb (U8), 41b47f1d (U10), cbb65df2 (U13), 06a8ae5d (U30), 72b12815 (U31), c1b55e87 (U35 CO1).
Not counted (checked): docstring/comment rewording; `async_lock` → `bus_lock`; `_PROBE_SETTLE_S` 0.1 s → `_PROBE_SETTLE_MS`
100 (same wait); probe message "No" → "no"; quoted annotations; `get_register_bytes()` (a new name for what
`get_register_struct(reg, f"{n}s")` already returned, drivers' behaviour unchanged).

**I2C-1 Boot-time bus clear** — `:24-33, 36-67, 113-119, 139`. Before the controller is built, SDA low → up to nine SCL
pulses then a STOP, each pulse waiting (synchronously, bounded by the bus timeout, 50 ms default) for a stretched SCL;
status bits. Commits cbb65df2. Origin M.SRC_SENS.008, A.U14.17 (a), OR113.a (1); code tag "(owner, 2026-09-30: clear at
boot; F.2)". Evidence O-spec (OR113 "I2c option a, clear at boot"). Legacy no (`legacy/firmware/python/IndividualDrivers/
asy_i2c_driver.py:6-14`, construct only). Form design. Depends none. Cost 42 lines; once per bus at construction: ≤ 9
pulses × 10 µs plus up to 11 bounded SCL waits (worst case ~11 × timeout when a slave holds SCL), two `Pin` objects.
Class **R**. Scheme MIN (claims P3): the SCL-stretch waits and the four status bits go beyond a plain 9-pulse + STOP
clock-out (~15 lines).

**I2C-2 Runtime bus-clear rung `clear()`** — `:70-110, 161-168, 333-338`. On a rung from the base reader: under the bus
lock, the same clock-out with awaited SCL waits (`asyncio.sleep_ms(1)` polls), then both pins back to ALT/I2C. Commits
cbb65df2, c1b55e87. Origin M.SRC_SENS.010, A.U13.R01, OR113.a (2). Evidence O-gen (OR113 "escalating up to a full bus
reset is absolutely allowed"; CLAUDE.md:237-239 names "bus clear"). Legacy no. Form design. Depends I2C-1 (same steps).
Cost 46 lines, of which `_clear_bus_awaiting()` (31) is a line-for-line copy of `_clear_bus()` ("A change to one is made
to both", `:71-72`); per rung: up to 11 awaited waits, 4 `Pin` objects. Class **X** (right intent, a duplicated
implementation). Scheme P4 ("one material"), G1, MIN.

**I2C-3 Controller rung `recover()`** — `:360, 386-396`. Clear, then re-construct `machine.I2C` with the stored
arguments under one bus-lock hold; a failed construction leaves no bus (`_REC_NO_CONTROLLER`). Commits cbb65df2,
c1b55e87. Origin M.SRC_SENS.010. Evidence O-gen (OR113; CLAUDE.md:237-239 names "controller re-init"). Legacy no. Form
design. Depends I2C-2. Cost 10 lines; per rung one controller construction. Class **R** (trigger: a reader's error
streak reaching the rung; the board decides how often). Scheme none (claims P3).

**I2C-4 `recoveries` sequence, stepped before the lock wait** — `:138, 336, 389`. A wrapping counter the base reader
compares to detect that another reader already ran a rung; CO1 moved the step before the lock wait. Commits cbb65df2,
c1b55e87. Origin M.SRC_SENS.010 (AC_NOTES 17 wrap form); CO1 (`S/u35r/handbacks_redo/CO1.md`). Evidence H (CO1's race was
found by a conformance walk and shown by a constructed fail-first test,
`tests/test_asy_base_classes.py::test_a_bus_rung_parked_behind_a_sibling_session_is_spent_for_every_reader_on_the_bus`).
Legacy no. Form patch (CO1: reorders a step so a parked second reader sees the episode). Depends I2C-2/3 and the base
`_recover_bus()`. Cost 3 lines. Class **C** (root: the ladder rungs I2C-2/3). Scheme HYP.

**I2C-5 `take_boot_clear_status()`** — `:139, 404-408`. The boot clear's status bits, handed once to the first reader that
asks (the base reader logs them). Commits cbb65df2. Origin M.SRC_SENS.010. Evidence H (OR113.a's "logged once per event"
is the lead's integration text, not the owner's words). Legacy no. Form design. Depends I2C-1. Cost 5 lines. Class **C**
(root I2C-1). Scheme HYP (claims P7).

**I2C-6 A short ACK count on a write is EIO (SF-A01), with preassembled register writes** — `:27, 170-180, 197-219,
299-305, 324-331, 429-431`. `writeto()` and both register setters go through `_write_all()`, which compares
`machine.I2C.writeto()`'s ACK count with the length and raises `OSError(EIO)` (after a STOP for a no-stop write); the
register setters build address + payload in the scratch (`_fill_reg_addr()`, `_write_buffer()`, `_MAX_ADDRSIZE`)
because `writeto_mem()` discards the count. Commits cbb65df2, 06a8ae5d. Origin SF-A01 (`audit/REGISTER.md:843`),
M.SRC_SENS.011 (1), .012 (1). Evidence H (scan by reading; lead-verified against source). Legacy no (`asy_i2c_driver.py:
46-54, 102, 108`: count returned unchecked / `writeto_mem` discards it). Form design. Depends none. Cost ~35 lines; per
register write one length compare, no allocation on the scratch path (the >32-byte fallback allocates). Triage
**suspicious**: concrete mechanism, consequence "a config write answers Valid while the chip did not take it" (SCD30 NVM,
BMP/ISL config), rare trigger. Verification **V2 confirmed** (platform source). Class **X** (confirmed gap; ~35 lines
where ~5 close it). Scheme MIN.

**I2C-7 A NACKed register byte is EIO, not a stale read (SF-A02)** — `:182-195, 250`. Register reads write the
address with no stop through `_write_all()` and then `readfrom_into()`, instead of `readfrom_mem_into()`. Commits
cbb65df2, 06a8ae5d. Origin SF-A02 (`audit/REGISTER.md:844`), M.SRC_SENS.011 (2). Evidence H (scan by reading). Legacy no
(`asy_i2c_driver.py:82, 92, 105` `readfrom_mem()`: same silent path, a fresh uninitialised buffer). Form design. Depends
I2C-6 (`_write_all`). Cost 9 lines; per register read two Python-level calls in place of one, wire-identical. Triage
**suspicious**: a BMP3XX/ISL29125 measurement burst would decode the scratch's previous bytes as a fresh reading (wrong
measurement). Verification **V1 confirmed** (platform source). Class **H — confirmed** (kept: a verified gap, already
near-minimal). Scheme none.

**I2C-8 bool/None contract** — `:289-305, 314-331, 340-347, 375-384, 445, 495-555, 535-537`. Setters return False with
no bus, `readfrom_into()` returns bool, `writeto_then_readfrom()` skips the read when the write found no bus, every
`I2CDevice` forwarder returns the bus bool, `setup()` returns True, `deinit()` returns True. Commits cbb65df2 (c3df14e1
signatures). Origin M.SRC_SENS.011-.013, A.U13.07/A.U13.09 (G3/R20). Evidence H. Legacy no (`asy_i2c_driver.py:38-108`,
no bus check at all). Form design. Depends I2C-3: at pre-audit no product path dropped the controller at run time
(`deinit()` had no runtime caller), so the no-bus state becomes reachable only through `recover()`'s
`_REC_NO_CONTROLLER`. Cost ~25 lines. Class **C** (root I2C-3). Scheme HYP.

**I2C-9 Allocation reductions: one held scratch view, whole-buffer fast paths, `get_register_into()`** — `:137, 192,
216-218, 245-252, 380-383, 429-431, 487-488`. Commits 06a8ae5d. Origin A.U30.21, A.U30.07 (G4/R42, "hot paths do not
churn same-shaped objects"). Evidence H (rule-derived; no MemoryError or fragmentation failure observed). Legacy no.
Form design. Depends none. Cost ~16 lines; saves one 16-byte memoryview per register access, one view per whole-buffer
transfer. Triage **implausible**: the saved objects are short-lived temporaries. Class **H**. Scheme OR110, HYP.

Removals (rows, no added code): **I2C-R1** `I2CDevice.setup(probe=)` parameter and **I2C-R2** the `out_start/out_end/
in_start/in_end` parameters of `writeto_then_readfrom()`/`write_then_readinto()` — c3df14e1/41b47f1d, A.U5.14/A.U10.21,
no caller passed them (grep in the action). Evidence H (no-caller reading). Class **H** (a neutral removal). Scheme
none.

## src/asy_spi_driver.py

Commits: 01e8e3eb, 41b47f1d, cbb65df2, 06a8ae5d. Not counted (checked): `async_lock` → `bus_lock`; private config
attributes; header comment; messages.

**SPI-1 bool contract with a no-bus False** — `:4-6, 55-60, 62-69, 77-105, 141-147, 164-224`. `configure()`, every
transfer and `session_begin()` return False with no bus (CS stays inactive) instead of the pre-audit `RuntimeError`; the
session still enters and holds the lock. Commits cbb65df2. Origin M.SRC_SENS.003/.004, A.U13.08 (G3/R20, BUS.S04).
Evidence H. Legacy no (`asy_spi_driver.py:39-61`). Form design. Depends none. Cost ~20 lines. Triage **implausible**: no
product path drops the SPI bus at run time (no SPI rung; `deinit()` has no runtime caller), so the branch is unreachable
today. Class **H**. Scheme HYP, TYPING-adjacent (unreachable today).

**SPI-2 `available` property** — `:40-43`. Read by the FRAM driver. Commits cbb65df2. Origin A.U13.09. Evidence H.
Legacy no. Form design. Depends SPI-1. Cost 3 lines. Class **C** (root SPI-1). Scheme HYP.

**SPI-3 CS level set before the pad becomes an output** — `:199`. `Pin.init(OUT, value=inactive)` in one call. Commits
cbb65df2. Origin A.U13.03 (G3/R16, BUS.N019, `ports/rp2/machine_pin.c:281-286`). Evidence H. Legacy no
(`asy_spi_driver.py:125-127`). Form design (net −1 line). Depends none. Cost 0 lines net. Triage **implausible**: a CS
pulse at boot with SCK idle clocks no opcode into the FRAM. Class **H**. Scheme none (no added code).

## src/asy_neopixel_driver.py

Commits: cdf6a33b, c3df14e1, 01e8e3eb, 2f049a00 (U9), 41b47f1d, 8d44fd14, c11ca0aa, f5c82557, 01032838 (U22), 72b12815,
32c4266d (U35 D2S). Not counted (checked): names, `_frame_ms` int form of the same 50 ms frame, the logger's `setup()`
moved from the signal task into the boot batch (same call), typing, comments.

**NP-1 External command refused at once while a signal runs; the external watcher task goes** — `:148-155`. Commits
2f049a00. Origin M.SRC_SENS.026, A.U9.02, D4.117. Evidence O-spec (OR102 "5. a"; led-request-internal-queue note).
Legacy partly (`neopixel_signal.py:67-73` refuses only while another external command is pending; `:101-111` queues
behind a running signal; `modules/sensortask-wozi.py:415-416` answers "busyLED"). Form design (removes a task and a
lock). Depends none. Cost +8 / −17 lines; one task fewer. Class **R**. Scheme none.

**NP-2 Internal requests wait for the running signal up to 120 s, polling each frame** — `:33-35, 165-176`. Replaces the
`sleep(0)` spin under `start_signal_lock`; past the deadline the request is dropped with an event line. Commits
2f049a00, 72b12815. Origin M.SRC_SENS.027, A.U9.04. Evidence O-spec (led-request-internal-queue: "waits for the running
signal up to a deadline and then queues", owner "Fine, and this for a reason ..."). Legacy partly
(`neopixel_signal.py:113-120`, unbounded `sleep(0)` spin). Form design. Depends NP-1. Cost 12 lines; while busy one
50 ms timed wait per frame. Class **R**. Scheme DELAY (a hardcoded 120 s deadline, `_SIGNAL_WAIT_MS`; the deadline itself
is in the approved decision text, its value is the agent's).

**NP-3 Entry sanitiser `_signal_values()`** — `:28, 44-57`. Colours clamped at entry, duration floored at 0.1 s (also for
NaN/inf) and capped at 60 s. Commits 2f049a00, 32c4266d. Origin M.SRC_SENS.022, A.U9.06 (G3/R65). Evidence H. Legacy
partly (REST bounds r/g/b 0-255, t 0.5-60 at `modules/sensortask-wozi.py:408-411`; floor 0.1 at
`neopixel_signal.py:128`). Form design. Depends none. Cost 11 lines. Triage **implausible**: the REST layer and the
notification service already bound every value that reaches the driver. Class **H**. Scheme HYP, TYPING (the colour
types are the signatures').

**NP-4 Signal task leaves a defined state on any end; overlay re-applied at (re)start** — `:77, 94, 115-119`. A cancel or
failure mid-ramp frees the slot, restores the overlay and writes black; a (re)started overlay or signal task re-applies
the overlay. Commits 2f049a00, 01032838. Origin M.SRC_SENS.025/.028, A.U9.05 (LED.T05), A.U22.01 (cites OR113). Evidence
H (OR113 claimed; the LED pixel state is not a bus or participant recovery). Legacy no (`neopixel_signal.py:122-150`).
Form design. Depends none. Cost ~7 lines. Triage **implausible**: a mid-ramp cancel happens only at shutdown or a
supervisor restart, and the worst consequence is one replayed flash. Class **H**. Scheme HYP.

**NP-5 Overlay rewritten every 300 s with no change pending** — `:36-39, 79-84`. `wait_for_ms(flag, 300000)`, then the
same rewrite under the overlay lock. Commits 01032838. Origin OF-75 (U17 lane N scan), closed at U22; value = default
notification FlashInterval, an agent choice (2026-10-06). Evidence H (lead, LEAD NOTES 358, `S/u35/lane_plan.md:4305-4322`:
"an agent choice (2026-10-06), never the owner's"); its WS2812 brownout premise is hardware-only (hardware-round list).
Legacy no (`neopixel_signal.py:90-99`, waits on the flag with no timeout). Form patch (a periodic rewrite around a
possible blanked pixel). Depends none. Cost 5 lines; one wakeup and one `wait_for_ms()` wrapper task every 300 s.
Cascade defect **confirmed by the lead, not re-verified here**: a shutdown cancel landing in the timeout's cleanup window
is lost (8/8 on the pinned Unix port, `S/u35/lead/probe/np_verify/`; `extmod/asyncio/funcs.py:47-50`,
`modasyncio.c:208-211`). Class **H** with a confirmed cascade defect. Scheme DELAY (the owner's words were about this
row), HYP, MIN.

Removals: **NP-R1** constructor `neopixel_freq`/`led_overl_bri` become fixed constants (A.U17.27, U17 commit c11ca0aa;
no device passed other values) — class **H**, scheme none. **NP-R2** the colour/duration type gates (32c4266d, U35 D2S)
— evidence O-spec (TYPING rule, owner 2026-10-27), class **R**.

## src/asy_notification_service.py

Commits: cdf6a33b, 65a0df3b, c3df14e1, 01e8e3eb, 2f049a00 (U9), 41b47f1d, 01032838 (U22), 15b8633c, 06a8ae5d, 72b12815,
970b63ba, 656fc82f, c56b366b. Not counted (checked): class rename `NotificationCoordinator` → `NotificationService`;
`register()`/`finalize()` replaced by construction-time signals (same validation, A.U5.06, OR46.b config objects);
`Interv` → `FlashInterval` and the other key renames (owner's REST key scheme, review `rest-key-scheme` ok); catalog
renumbering (errno 10-13 → 14/15/26, wrnno 5 → 13); `_now()` → `utc_now()` call; ms sleeps of the same values.

**NT-1 Notification window may span midnight** — `:140-144, 289`. Commits 2f049a00. Origin A.U9.01, G3/R62, OR69.a (6);
code tag "(owner, 2026-09-26)". Evidence O-spec (OR69 "6. a"). Legacy no (`neopixel_signal.py:170`, same-day only). Form
design. Depends none. Cost 5 lines. Class **R**. Scheme none (claims P1).

**NT-2 `State` field (0-4) and `_check_one()` → None when a signal could not be evaluated** — `:72-77, 136-137, 217-249,
269-299, 328-329`. Every cycle publishes why nothing was evaluated (off, no clock, a value unavailable, own config
unreadable); the config-unreadable branch now also stores a sample. Commits 01032838. Origin SF-B17 (agent,
`audit/REGISTER.md:841`), M.SRC_SENS.035 (2)/.037 (1). Evidence H. Legacy no. Form design. Depends NT-3. Cost ~30 lines
(68 in the touched ranges); one more field per sample. Triage **implausible**: observability; nothing behaves wrongly
without it. Class **H**. Scheme FEAT (a new API field, no owner decision), HYP, MIN.

**NT-3 A producer sample older than 10800 s counts as unavailable** — `:68-71, 226, 231-235`. Commits 01032838, c56b366b.
Origin SF-M3-01 (agent, `audit/REGISTER.md:870`), M.SRC_SENS.035 (1); code tag "(agent, 2026-10-06)". Evidence H. Legacy
no. Form patch (an age check around a frozen producer). Depends the `TS is None counts as current` exception (cascade of
`utc_now()`). Cost 5 lines; one `utc_now()` per signal per cycle. Triage **implausible**: the SCD30 re-stamps its cached
values on every not-ready read (the owner's named exception), so the bound fires only when the producer's read loop
itself stops; the consequence is one stale warning flash. Class **H**. Scheme DELAY, HYP.

**NT-4 Non-numeric and NaN values refused with E15** — `:236-242`. Commits 2f049a00. Origin A.U9.08 (G3/R68, LED.S02).
Evidence H. Legacy no. Form patch. Depends none. Cost 7 lines. Triage **implausible**: every wired producer field is a
float, int or None, and the SCD30/BMP3XX gates drop non-finite values before publishing. Class **H**. Scheme TYPING, HYP.

**NT-5 A dropped LED flash logs W67; the default sink is recognised by identity** — `:58, 86-96, 211-212, 331-340`.
Commits 2f049a00, 970b63ba. Origin SF-B2 (agent, `audit/REGISTER.md:826`), M.SRC_SENS.034 (1). Evidence H. Legacy no.
Form design. Depends NP-2 (`request_signal()` returns False only after its 120 s deadline). Cost 13 lines. Class **C**
(root NP-2). Scheme HYP.

**NT-6 The LED pause counts measured time, not wake-ups** — `:214, 307-318, 372-377`. Commits 41b47f1d (U10). Origin
A.U9.09, REF/R03. Evidence O-spec (OR104 "the "never UTC" goes for the others as well"; OR104.a (3)). Legacy no
(`neopixel_signal.py:194-207`, one decrement per `sleep(1)` round). Form design. Depends `TickSeconds` (base). Cost ~18
lines (replaces ~12). Class **R**. Scheme none (claims P1).

**NT-7 Own-config read failure logged once per episode** — `:255-273`. The pre-audit `repeat=` rule spent one slot per
run but printed every cycle; the head flag also stops the console line. Commits 06a8ae5d. Origin U30 commit subject ("A
config store's or a reader's failed reads log once per episode"). Evidence H. Legacy partly (`neopixel_signal.py:159-162`,
a debug print each cycle). Form patch. Depends none. Cost ~6 lines. Triage **implausible** (log flooding is already
handled centrally by OR35.b). Class **H**. Scheme **OR35a** (the console line no longer prints on repeats), HYP.

**NT-8 `report_if_fatal(e)` in the three broad handlers** — `:228, 324, 336`. Commits 06a8ae5d. Class **C** (root: the
C-stack reboot, review `c-stack-reboot` ok, outside group C). Cost 3 lines. Scheme none beyond the root's.

## src/voc_algorithm.py

Commits 2949ed97 (U12), 06a8ae5d (U30), 6e0d3fba (U35 D2S). Not counted (checked): docstring; the `(owner, 2026-07-21)`
comment; member order kept (OR141.a (3)).

**VOC-1 Fix16 helpers wrap to int32; FIX16_MINIMUM/OVERFLOW are INT32_MIN** — `:45-46, 58-63, 268-269, 291, 294-295,
304, 321, 329, 357`. Commits 2949ed97. Origin D4.37 (G3/R09), A.U12.11, M.SRC_SENS.015/.016; tag "(agent, 2026-09-29)".
Evidence O-spec (OR101). Legacy no (`IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:44-46`). Form design. Depends
none. Cost 16 lines; per sample a range test per helper call, a mask only out of range. Class **R**. Scheme none (claims
P11).

**VOC-2 Uptime limit 16383 instead of 32767** — `:42, 474`. Keeps both learning counters below rp2's small-int limit;
the output is unchanged (constant sigmoids from 10223 s, agent's proof by reading). Commits 2949ed97. Origin A.U12.13,
LEAD/R24; tag "(agent, 2026-09-29)". Evidence O-gen (OR105 "I want to exactly avoid allocations happening at some
point"). Legacy no (`voc_algorithm.py:43`). Form design. Depends none. Cost 1 line. Class **R**. Scheme none.

**VOC-3 Restore validation: every restored field must be int32; the two uptimes clamped; `"<32q"`** — `:110, 151-159,
194-196`. Commits 2949ed97. Origin A.U12.14 (G3/R12, ALGO.T05). Evidence H (the clamp exists for VOC-2: a backup of an
older build). Legacy no (`voc_algorithm.py:128-131`, `"31q"`, bare except). Form design. Depends VOC-2 (clamp). Cost 9
lines. Triage **implausible**: the chunk is CRC32-checked and owner-seeded, and the values were written by this same
code; `"<"` is byte-identical on rp2. Class **C** for the clamp (root VOC-2), **H** for the range check — counted as one
C row. Scheme HYP.

**VOC-4 Handlers narrowed: a MemoryError in pack/unpack propagates** — `:146, 154`. Commits 2949ed97, 06a8ae5d, 6e0d3fba.
Origin M.SRC_SENS.017 (agent decision 2026-10-01), D2S. Evidence H. Legacy no (bare except). Form design. Depends none.
Cost 0 net. Triage **implausible** (a 256-byte tuple allocation; the SGP40 caller's broad handler degrades). Class **H**.
Scheme none.

**VOC-5 35 constants pre-converted once in `__init__`** — `:217-254` and ~40 call sites. Commits 06a8ae5d; tag "(agent,
2026-10-20)". Origin U30 memory ladder (A.U30.02 catalog). Evidence H (rule-derived). Legacy no. Form design. Depends
none. Cost 35 lines; 35 permanent instance attributes; saves ~40 float conversions per sample. Triage **implausible**:
OR109.a (1) settled these per-sample temporaries ("No rework of the fix16 helpers"). Class **H**. Scheme OR110/OR109,
MIN.

## src/asy_bmp3xx_driver.py

Commits: 65a0df3b, c3df14e1, 1b59a05d, 01e8e3eb, 41b47f1d, 2949ed97, cbb65df2, 5689e2f4 (U15), f5c82557 (U19), f76385a6,
15b8633c, 06a8ae5d, 72b12815, 49fde7b5, 656fc82f. Not counted (checked): class/attribute/key renames (`PressOvers` →
`PresOvers`, `SeaLevelOffs` → `SeaLevelOffset` ...); `BMP3xx_DeviceSession` → shared `DeviceSession`; `_base_trigger()`
→ the base's `_trigger_loop()`; catalog renumbering; `altitude_baro()` → `pressure_at_height()` (math_helpers, group
outside); `get_altitude()` → `get_pressure_altitude()` with the fixed 1013.25 hPa (its only writer had gone);
`_RESET_SETTLE_MS` 3 vs 2 ms (one tick for `sleep_ms` early wake); docstring.

**BMP-1 Chip self-reset detected each cycle; stored settings re-applied (W71)** — `:46, 55, 64, 277-282, 700-703,
719-725`. One EVENT read per cycle; on `por_detected` a warning and `_apply_stored_config()` under `_set_lock`, a failed
re-apply fails the cycle into the ladder; `reset()` reads EVENT away after its own soft reset. Commits 5689e2f4. Origin
SF-B9 = SF-A05 (agent; datasheet point closed by the lead, `audit/REGISTER.md:833, 847`), M.SRC_SENS.043 (1)/.048 (1).
Evidence H. Legacy no (`asy_bmp3xx_driver.py:110-178`). Form design. Depends none. Cost 16 lines; +1 one-byte register
read per cycle on a shared bus. Triage **implausible**: after a power-on reset the chip runs at its defaults (×1, no IIR)
and forced mode is re-written every cycle, so readings stay valid at lower precision; no wrong value, hang or loss.
Class **H**. Scheme HYP, P6 (a bus read per cycle).

**BMP-2 ERR_REG `fatal_err` checked; the burst is 8 bytes from 0x02** — `:63, 69, 520-528`. Commits 5689e2f4, 06a8ae5d.
Origin SF-A05. Evidence H. Legacy no. Form design. Depends BMP-1 (same fold). Cost 5 lines; 2 bytes more per burst.
Triage **implausible** (no observed fatal_err; the range gate already rejects implausible values). Class **H**. Scheme
HYP.

**BMP-3 Conversion wait computed from the OSR byte, then STATUS polled** — `:504-510, 513-517`. One OSR register read
per conversion (reserved encodings raise), a sleep of the datasheet's typical time, then the existing poll. Commits
5689e2f4, 72b12815. Origin A.U15.25 (G3/R43, datasheet 3.9.2). Evidence H. Legacy partly (`asy_bmp3xx_driver.py:269-277`,
polls STATUS every 2 ms, unbounded). Form design. Depends none. Cost 9 lines; +1 register read, fewer STATUS polls per
cycle. Triage **implausible**: the pre-audit poll (2 ms steps, 300 ms bound) worked; this trades bus polls for a read.
Class **H**. Scheme MIN, HYP (claims P6).

**BMP-4 Participant rung: soft reset plus the stored configuration** — `:92-95, 178, 200-239, 323-333`.
`_recover_device()` under `_set_lock`; `_apply_stored_config()` returns applied / unreadable / write-failed; init
failures call the base's `_init_failed()`, success `_init_done()`. Commits 5689e2f4. Origin A.U15.R03, M.SRC_SENS.044.
Evidence O-gen (OR113 "recover mildly"; CLAUDE.md:237-239 names "the participant's own reset"). Legacy no. Form design.
Depends the base ladder. Cost ~15 lines (plus ~14 moved out of `_init_bmp()`). Class **R** (trigger: an error streak).
Scheme none (claims P3).

**BMP-5 An out-of-range reading logs its own code E27** — `:285-288`. Commits 5689e2f4. Origin SF-M3-02 (agent,
`audit/REGISTER.md:872`). Evidence H. Legacy no. Form design. Depends none. Cost 3 lines. Triage **implausible**
(observability; escalation unchanged). Class **H**. Scheme HYP.

**BMP-6 PresOffset moving the pressure outside 300-1250 hPa: SLPres None and W11** — `:45, 343-347`. Commits 5689e2f4.
Origin D4.65 (G3/R23), A.U15.24. Evidence O-spec (OR101; review `pres-offset-warning` ok). Legacy no
(`asy_bmp3xx_driver.py:171-174`). Form design. Depends none. Cost 6 lines. Class **R**. Scheme none.

**BMP-7 MeanAtmTemp lower bound −40 °C (was −50)** — `:114-115`. Commits 5689e2f4. Origin D4.64 (G3/R06), A.U15.23.
Evidence O-spec (OR101). Legacy no (`modules/sensortask-wozi.py:378`, −50..50). Form design (narrowed accept rule).
Depends none. Cost 0 net. Class **R**. Scheme none.

**BMP-8 Compensation config captured before the conversion** — `:179, 264-273, 339-342`. A PUT during a conversion
applies next cycle. Commits 5689e2f4. Origin A.U15.22 (G3/R22). Evidence O-spec (review `stale-as-fresh-every-driver`
ok). Legacy no (`asy_bmp3xx_driver.py:160-169`, read after the conversion). Form design. Depends none. Cost ~10 lines,
one 4-float list held. Class **R**. Scheme none.

**BMP-9 Compensation read failure logged once per episode** — `:180, 222, 267-271`. Commits 06a8ae5d. Origin U30
subject. Evidence H. Legacy no (`asy_bmp3xx_driver.py:163-169`, counted every time). Form patch. Depends BMP-8. Cost ~4
lines. Triage **implausible**. Class **H**. Scheme OR35a, HYP.

**BMP-10 A TS of None before the first NTP sync is no failure** — `:262, 302-303, 336-337`. Commits 41b47f1d. Origin
M.SRC_SENS.089, A.U10.06. Class **C** (root: `utc_now()` returning None before the first sync, review
`timestamps-before-ntp` ok, outside group C). Legacy no (`asy_bmp3xx_driver.py:139`, unsynced clock stamped). Cost ~3
lines. Scheme none (an owner-approved root; the same holds for SCD-10, SGP-22, ISL-18).

**BMP-11 A False bus result raises `OSError("I2C bus not initialized")` (10 sites)** — `:493-494, 505-506, 511-512,
523-524, 606-607, 618-619, 681-682, 697-698, 704-705, 723-724`. Commits cbb65df2, 5689e2f4, 06a8ae5d. Origin A.U13.09
(HR G3.034). Class **C** (root I2C-8 ← I2C-3). Cost 20 lines. Scheme HYP.

**BMP-12 A chip config read failure answers the GET's unavailable marker** — `:307-316`. Commits f5c82557. Origin SF-B8
(agent). Evidence H. Legacy no. Form design. Depends the base half (outside). Cost 5 lines. Triage **implausible**
(display only). Class **H**. Scheme HYP.

**BMP-13 Trigger interval refused unless a whole number in range (`checked_int`)** — `:452-458`. Commits 5689e2f4.
Origin A.U15.26. Evidence H. Legacy no (no validation). Form design. Depends none. Cost 4 lines. Triage **implausible**:
the schema already validates `SampleInterval` as an int before the push, and init passes the stored int. Class **H**.
Scheme TYPING.

**BMP-14 A failed timer arm wakes the task, which logs and ends; its restart re-arms** — `:376-378`. Commits 5689e2f4.
Origin A.U15.41 (G5/R09). Evidence O-gen (OR31.a "either really work or return / end"). Legacy no (no handler). Form
design. Depends the base `_timer_failed()`. Cost 2 lines. Class **R** (trigger implausible: the alarm pool holds 16,
SPECIFICATION.md:6336-6338). Scheme none.

**BMP-15 `report_if_fatal(e)` in 13 broad handlers** — `:215, 226, 290, 314, 330, 405-448`. Commits 06a8ae5d. Class **C**
(root C-stack reboot, review `c-stack-reboot` ok). Cost 13 lines.

**BMP-16 A driver-owned 8-byte burst buffer** — `:466, 521-524`. Commits 06a8ae5d. Origin A.U30.07. Evidence H
(rule-derived). Class **H** (implausible: temporaries). Cost 5 lines. Scheme OR110.

## src/asy_scd30_driver.py

Commits: cdf6a33b, 43aced07, f44b9411 (U4), c3df14e1, 1b59a05d, 01e8e3eb, 41b47f1d, 8d44fd14, cbb65df2, 5689e2f4 (U15),
f5c82557, 9bf22747, 15b8633c, 8ad2bb37, 06a8ae5d, 72b12815, 656fc82f, 18b9ff67, 4343f788. Not counted (checked): key
renames (`TempOffs` → `TempOffset`, `MeasInt` → `MeasInterval`); fixed address (`_SCD30_DEFAULT_ADDR` parameter gone, the
datasheet fixes it); `SCD30_DeviceSession` → `DeviceSession`; `@web` tag texts (incl. 4343f788's wording); catalog
renumbering; ms constants of the same waits; the `typing.cast` shim gone.

**SCD-1 FRC readiness (FRCState, FRCWait; FRCNoise/FRCRate/FRCWindow settings)** — `:96-105, 122-124, 160-161, 225-242,
299-304, 316-317, 325-335, 348-423, 432, 439-440, 455-460, 518, 525-535`. Regression window over the configured
interval, uninterrupted count to max(6 min, 5 intervals), idle ticks from the 500 ms tick, republish on stop. Commits
5689e2f4. Origin A.U15.12, REF/R06, OR98.a/OR99.a; tags "(owner, 2026-09-29: 1-2 x)", "(agent, 2026-09-29; owner-
reviewed, 2026-10-02)". Evidence O-spec (OR98/OR99; review `scd30-calibration-readiness` ok). Legacy no. Form design.
Depends SCD-2. Cost 134 lines; per new measurement ~10 float operations (temporaries), two config reads per cycle. Class
**R**. Scheme none (large but owner-specified criteria; note MIN for its size).

**SCD-2 SCD30_Reader becomes a config-file reader with a RAM-only config log** — `:193-194, 210`. Commits 5689e2f4. Origin
AC_NOTES 13, M.SRC_SENS.052. Evidence O-spec (OR99 "No flash writes, no extra FRAM chunk"). Legacy no. Form design.
Depends SCD-1. Cost 3 lines. Class **C** (root SCD-1). Scheme none.

**SCD-3 Compare-before-write PUT against a fresh chip snapshot** — `:108-112, 140-149, 244-323, 337-346`. Writes only
changed keys in a fixed order, AmbPres and ForceCalRef always sent, ContMeas last, the whole PUT refused when the
snapshot fails ("(owner, 2026-09-29)" tag), FRC keys routed to the file store, each invalid key logged E21. Commits
f44b9411, 5689e2f4. Origin OR42.a-c, A.U4.04, M.SRC_SENS.053. Evidence O-spec (OR42.b, OR42.c "Perfect match"; review
`scd30-write-path` ok). Legacy yes in intent (`modules/sensortask-arzi.py:274-287`, a compare its trailing commas
defeated, OR57). Form design. Depends SCD-1 (FRC routing). Cost ~88 lines (replaces ~35); one 6-register snapshot per
PUT with a chip key. Class **R**. Scheme none (claims P9).

**SCD-4 Temperature offset sent as the nearest 0.01 °C tick** — `:152-154, 850`. Commits f44b9411. Origin D4.61, A.U4.05.
Evidence O-spec (OR101). Legacy no (`asy_scd30_driver.py:335`, truncation). Form design. Cost 3 lines. Class **R**.
Scheme none.

**SCD-5 Measurement range gate (CO2 0-40000, T −40..70 incl. the chip offset, RH 0-100), E27** — `:65-72, 89, 489-493,
724, 852, 896-899, 918`. Setup reads the chip's offset once; `set_temperature_offset()` keeps it. Commits 5689e2f4.
Origin D4.62 (G3/R23), A.U15.01; E27 from SF-M3-02. Evidence O-spec (OR101) for the gate; H for the separate code.
Legacy no. Form design. Depends none (the offset cache is the gate's own input). Cost 17 lines; +1 register read at
setup. Class **R**. Scheme none.

**SCD-6 Not-ready counter: W73 after five data-ready reads with no new measurement** — `:90-92, 224, 429, 500-505`.
Commits 5689e2f4. Origin SF-B10 = SF-A04, M.SRC_SENS.055 (1). Evidence H. Legacy no. Form design. Depends none. Cost 10
lines. Triage **implausible** (observability; the store keeps re-publishing, the owner's named exception). Class **H**.
Scheme HYP.

**SCD-7 Participant rung: soft reset under `_set_lock`; init hooks** — `:217, 436, 441, 508-519`. Commits 5689e2f4.
Origin A.U15.R01. Evidence O-gen (OR113). Legacy no. Form design. Depends the base ladder. Cost 13 lines; a 2.5 s soft
reset per rung. Class **R**. Scheme none (claims P3).

**SCD-8 Stuck-pin tick counter capped at its threshold** — `:453-454`. Commits 5689e2f4. Origin A.U15.03. Evidence O-gen
(OR103 "No unbounded counters anywhere"). Legacy no (`asy_scd30_driver.py:141-142`). Form design. Cost 1 line. Class **R**
(trigger implausible: 17 years at 2/s). Scheme none.

**SCD-9 Timer arm failure: re-armed at the loop start, a fault checked per tick, the arm failure wakes the task** —
`:448-452, 559-561`. Commits 5689e2f4. Origin A.U15.41. Evidence O-gen (OR31.a). Legacy no (`asy_scd30_driver.py:76-78`).
Form design. Depends the base timer helpers. Cost 7 lines; one check per 500 ms tick. Class **R** (trigger implausible:
16-alarm pool). Scheme none.

**SCD-10 TS None before the first sync is no failure; store guard on values only** — `:474-475, 480, 521-523`. Commits
41b47f1d. Class **C** (root `utc_now()`, review `timestamps-before-ntp` ok). Cost ~3 lines.

**SCD-11 A False bus result raises before the CRC check** — `:729-730, 734-735, 760-761, 867-868`. Commits cbb65df2.
Class **C** (root I2C-8 ← I2C-3). Cost 8 lines. Scheme HYP.

**SCD-12 Copy-free word decode** — `:717, 882-890`. Commits 06a8ae5d. Origin A.U30.05. Evidence H (rule-derived). Class
**H** (implausible: per-interval temporaries). Cost 10 lines. Scheme OR110.

**SCD-13 `report_if_fatal(e)` in ~16 broad handlers**. Commits 06a8ae5d. Class **C** (root C-stack reboot). Cost ~16
lines.

(The SCD30 GET unavailable marker, SF-B8, is inside SCD-3's `_get_mgr_cfg()`; counted there.)

## src/asy_sgp40_driver.py

Commits: 83c9920a, cdf6a33b, 65a0df3b, c3df14e1, 1b59a05d, 01e8e3eb, 41b47f1d, 2949ed97 (U12), cbb65df2, 5689e2f4
(U15), 2977c4e0 (U16), f76385a6, 06a8ae5d, 656fc82f, 18b9ff67. Not counted (checked): attribute/key renames
(`SGPResetVOC` → `ResetVOC`); the reader's references as `ValueRef`/`SgpBackup` config objects; `SGP40_DeviceSession` →
`DeviceSession`; fixed address; catalog renumbering; the W13/W35 episode flag added by 83c9920a and removed again by U3
(net no change here); 18b9ff67's removal of an unreachable reply-length guard; `_push_reset_voc`'s isinstance check gone
(shared validation).

**SGP-1 VOCState field (0 blackout, 1 learning, 2 learned, 3 restored)** — `:86, 122-123, 128, 231-232, 464, 596-607`.
Saturating sample count to 86400. Commits 5689e2f4. Origin A.U15.19, LEAD/R23. Evidence O-spec (OR97 "17 a"; review
`state-code-values` ok). Legacy no. Form design. Cost 17 lines. Class **R**. Scheme none.

**SGP-2 A compensation sample older than 10800 s skips the cycle** — `:87-90, 179-185, 309-324`. Commits 5689e2f4. Origin
SF-M3-01 (agent), M.SRC_SENS.064 (1); tag "(agent, 2026-10-06)". Evidence H. Legacy no. Form patch. Depends the
`TS None counts as current` exception. Cost 15 lines; per cycle two TS compares. Triage **implausible** (as NT-3: the
SCD30 re-stamps; the effect is compensation with the last value). Class **H**. Scheme DELAY, HYP.

**SGP-3 Compensation inputs clamped to Table 10 (no wrap); non-finite refused** — `:91-97, 424-427, 683-692, 725-732`.
Commits 5689e2f4. Origin D4.55 (G3/R40), A.U15.14 (and G4/R10 for the finite check). Evidence O-spec (OR101) for the clamp.
Legacy no (`asy_sgp40_driver/__init__.py:367, 386`, `& 0xFFFF`). Form design. Cost 11 lines. Class **R**. Scheme none
(the finite check alone is TYPING-adjacent: the SCD30 publishes finite values only).

**SGP-4 The measure command staged inside the device session** — `:799-812`. Commits 2949ed97. Origin pass 4 R.26,
A.U12.18, OR109.a (0); tag "(owner, 2026-09-29: 'No races allowed')". Evidence O-spec (OR109 "Latent SGP40 race: Fix
this."). Legacy no. Form design (code moved into the hold). Cost ~12 lines touched, ~2 added. Class **R**. Scheme none.

**SGP-5 The default command buffer restored in a `finally`** — `:707-718`. Commits 5689e2f4, 06a8ae5d. Origin D4.53
(G3/R38), A.U15.13. Evidence O-spec (OR101). Legacy no. Form design. Cost ~4 lines added. Class **R**. Scheme none.

**SGP-6 The serial number read as all three words** — `:677, 720-723, 757-761`. Commits 5689e2f4. Origin A.U15.13 (2),
G5/R28. Evidence O-spec (review `sgp40-chip-identity` ok). Legacy yes (`asy_sgp40_driver/__init__.py:321-323`). Form
design. Cost 7 lines; a 9-byte reply buffer. Class **R** (restores legacy). Scheme none.

**SGP-7 Participant rung: heater off to idle (0x3615); init hooks** — `:66-67, 217, 338, 342, 364, 479-488, 820-825`.
Commits 5689e2f4. Origin A.U15.R02. Evidence O-gen (OR113). Legacy no. Form design. Cost 19 lines; one 2-byte write
and a 2 ms wait per rung. Class **R**. Scheme none (claims P3).

**SGP-8 WaitTimeNTP 0 restores once at the first cycle** — `:354-355`. Commits 5689e2f4. Origin G9/R03, A.U15.17.
Evidence O-spec (review `sgp40-wait-zero` ok). Legacy yes (`asy_sgp40_driver/__init__.py:71-72, 84-86`). Cost 2 lines.
Class **R**. Scheme none.

**SGP-9 A backup dated in the future is rejected** — `:578-582`. Commits 5689e2f4. Origin G5/R31, A.U15.17/A.U16.18.
Evidence O-spec (review `negative-backup-age` ok). Legacy no (`__init__.py:125`, age > max only). Cost ~2 lines. Class
**R**. Scheme none.

**SGP-10 A dated backup restored with unknown age warns W33** — `:576-577`. Commits 5689e2f4. Origin SF-M1-02
(M.SRC_SENS.063 (1)). Evidence H. Legacy partly (`__init__.py:117-128`, restored silently). Cost 2 lines. Triage
**implausible** (observability). Class **H**. Scheme HYP.

**SGP-11 While waiting for NTP the chunk is read once, then only the NTP callback per second** — `:228, 237, 241,
548-557, 572-575`; a raising callback logs E14 and counts as unsynced. Commits 5689e2f4, 2977c4e0. Origin G9/R03 ("the
chunk is not re-read every second while waiting"), A.U15.17 (4). Evidence H. Legacy no (`__init__.py:107-108`, a read
per cycle). Form design. Cost ~20 lines. Triage **implausible**: FRAM reads have effectively unbounded endurance here
(CLAUDE.md FRAM note) and the wait is ≤ 600 s once per boot. Class **H**. Scheme HYP, MIN.

**SGP-12 A task restart keeps the live VOC state (no restore over it)** — `:330, 356-360`. Commits 2977c4e0. Origin
SF-M3-05 (agent, 2026-10-06). Evidence H. Legacy n/a (legacy reboots instead of restarting, `__init__.py:186-189`). Form
patch. Depends SGP-1's counters. Cost 4 lines. Triage **implausible**: the pre-audit restart restored a backup at most
one BackupPeriod old (default 1 min). Class **H**. Scheme HYP.

**SGP-13 Tri-state restore result: unreadable warns W65, blank stays a console line** — `:559-566`. Commits 2977c4e0.
Origin U16 FRAM tri-state read, G5/R21. Class **C** (root: the FRAM manager's tri-state read, outside group C). Legacy
no (`__init__.py:110-111`, debug print). Cost 8 lines. Scheme HYP.

**SGP-14 One backup buffer allocated with the reader; a failed allocation is retried and keeps the restore pending** —
`:252-253, 296-303`. Commits 06a8ae5d, 5689e2f4. Origin SF-M3-06 (agent), A.U30 placement. Evidence H (rule-derived).
Legacy no. Form design. Cost 9 lines; one long-lived 264-byte buffer. Triage **implausible**. Class **H**. Scheme OR110,
HYP.

**SGP-15 The backup chunk carries its owner seed; only MemoryError is caught; a refusal is a console line** —
`:242-251`. Commits 2977c4e0. Origin U16 (owner-seeded chunks), SF-B1/B12. Class **C** (root: the FRAM manager's owner
seed, outside group C); the console-only refusal follows the owner's 2026-09-16 "Handle via mpremote." Legacy no. Cost
10 lines. Scheme HYP (cascade).

**SGP-16 The FRAM verify period never 0** — `:188-191, 352, 501-505`. Commits 5689e2f4. Origin SENS.S02, A.U15.17.
Evidence O-spec (OR104 "2: option (a)"; tag "(owner, 2026-09-29)"). Legacy no (`__init__.py:83`, same formula).
Cost 2 lines. Class **R**. Scheme none.

**SGP-17 A read that fails on the restore cycle keeps the backup for the next cycle** — `:473-475`. Commits 5689e2f4.
Origin A.U15 (commit subject "SGP40 restore"). Evidence H. Legacy no (`__init__.py:174-178`, the read's except keeps no
retry). Form design. Cost 3 lines. Triage **suspicious**: a measurement error on the one restore cycle loses the learned
state at the next backup (data loss). Verification **V4 confirmed**. Class **H — confirmed**. Scheme none.

**SGP-18 `measure_index_and_raw()` returning None raises "raw signal not measured"** — `:446-447`. Commits 5689e2f4.
Evidence H. Cost 2 lines. Triage **implausible**: None comes only from a failed CRC computation of a fixed 2-byte
argument. Class **H**. Scheme TYPING.

**SGP-19 False bus results raise (exchange, heater-off, general-call reset with no bus)** — `:696-705, 737-744, 822-824`.
Commits cbb65df2, 5689e2f4. Class **C** (root I2C-8 ← I2C-3). Cost ~8 lines. Scheme HYP.

**SGP-20 Timer arm failure handled (re-arm at init, fault check per wake, wake on failure)** — `:327, 379-380, 629-631`.
Commits 5689e2f4. Evidence O-gen (OR31.a). Class **R** (trigger implausible). Cost 5 lines.

**SGP-21 VOCAlgorithm built at construction; per-sample word read without a list** — `:680-681, 715-718`. Commits
06a8ae5d. Origin A.U30.04/.06. Evidence H (rule-derived). Class **H** (implausible). Cost ~6 lines. Scheme OR110.

**SGP-22 TS None before sync is no failure** — `:385-386, 411, 591-592`. Class **C** (root `utc_now()`). Cost ~3 lines.

**SGP-23 `report_if_fatal(e)` in 6 handlers**. Class **C** (root C-stack reboot). Cost 6 lines.

## src/asy_isl29125_driver.py

Commits: cdf6a33b, 65a0df3b, c3df14e1, 1b59a05d, 01e8e3eb, 41b47f1d, 8d44fd14, cbb65df2, 5689e2f4 (U15), f5c82557,
9bf22747, 15b8633c, 06a8ae5d, 49fde7b5, 656fc82f, 890c5ab1 (U35 D2S). Not counted (checked): renames (`isl` →
`_isl`, keys `SampleInterv` → `SampleInterval` ...), `ISL29125_DeviceSession` → `DeviceSession`, fixed address, member
order (U10), comment rewrites (M.SRC_SENS.092), catalog renumbering, header lines (49fde7b5). Legacy note: the legacy
driver (`legacy/firmware/python/IndividualDrivers/asy_isl29125_driver.py`, 570 lines) has no auto-range state machine,
settle tracking, calibration or brownout handling, so every row below is "legacy no" unless said.

**ISL-1 INT parked while the peak rule overrules the green window** — `:270-271, 321-328, 444-449, 464, 587-588,
714-722, 1132`. Commits 5689e2f4. Origin D4.66 (G3/R51), A.U15.32. Evidence O-spec (OR101). Form design. Depends none.
Cost 22 lines; one CONFIG3 write per park/unpark. Class **R**. Scheme none.

**ISL-2 Dead-INT re-arm once per episode** — `:272-273, 465, 591, 601-603, 825-832`. Commits 5689e2f4. Origin A.U15.R05.
Evidence O-gen (OR113 participant re-configuration). Form design. Depends ISL-1 (paused while parked) and ISL-3
(`_write_thresholds()`). Cost 14 lines. Class **R** (trigger: five periodic-only decisions; a missing pull-up is not
fixed by it). Scheme none.

**ISL-3 One threshold lock; setters rewrite the chip thresholds; thresholds scaled inside the session** — `:274-275,
909-927, 942-966, 1066-1072, 1155-1157, 1282-1290`. Commits 5689e2f4. Origin A.U15.33 (G3/R52, owner items 2026-09-13
`6023d87` / 2026-09-14 `90e5ebb` cited — those commits are not in this clone, quote not found), A.U15.S01. Evidence
O-spec (review `threshold-rewrite-failure` ok, whose decision presupposes the rewrite) and O-gen (OR109) for the lock.
Form design. Cost ~26 lines. Class **R**. Scheme none.

**ISL-4 CalLight field (0 n/a, 1 suitable, 2 too dark, 3 too bright)** — `:188-189, 280, 330-338, 730, 903`. Commits
5689e2f4. Origin A.U15.36. Evidence O-spec (OR76; review `state-code-values` ok, its fourth code "the planning's
addition"). Cost 13 lines. Class **R**. Scheme none.

**ISL-5 FiltCoeff cached and captured with the cycle** — `:290-291, 495, 700, 870, 1074-1080`. Removes the per-sample
config read and its errno-14 fallback. Commits 5689e2f4. Origin A.U15.22 (3). Evidence O-spec (review
`stale-as-fresh-every-driver` ok). Cost ~11 lines (−8 removed). Class **R**. Scheme none.

**ISL-6 A cycle whose settle outlasts its bound is discarded, not counted** — `:292, 658, 688-692, 749, 844-853`.
Commits 5689e2f4. Origin A.U15.22 (4). Evidence O-spec (review `stale-as-fresh-every-driver`: the G3/R22 text names the
ISL29125's post-bound settle publication). Cost 7 lines. Class **R**. Scheme none.

**ISL-7 The settle deadline never ages past the tick horizon** — `:1544-1550`. A passed deadline moves up to now.
Commits 5689e2f4. Origin A.U15.35 (G5/R10: "the reader publishes nothing for ~6.2 of every 12.4 days"). Evidence H.
Form design. Cost 4 lines. Triage **suspicious**: after 2**29 ms (6.2 days) without a CONFIG1 write — a fixed range,
or auto-range in steady light — the pre-audit `time_to_settle_ms()` returns up to 2**29 and `_settle_wait()` sleeps it.
Verification **V3 confirmed**. Class **H — confirmed**. Scheme none (claims P1).

**ISL-8 The other stored ticks bounded: dwell clamp, calibration window ended and candidate cleared every cycle** —
`:139, 413-418, 428-434, 564-571, 661`. Commits 5689e2f4. Origin A.U15.35. Evidence H. Cost ~14 lines. Triage
**implausible**: the dwell tick goes wrong only after 6.2 days on the high range with no switch (continuous bright
light, nights included); the candidate tick only after a user-run calibration, and shows that run's real candidate.
Class **H**. Scheme HYP.

**ISL-9 A calibration window that closes unconverged warns W75** — `:50, 394-399`. Commits 5689e2f4. Origin SF-B11.
Evidence H. Cost 7 lines. Triage **implausible** (observability of a user-started run). Class **H**. Scheme HYP.

**ISL-10 Config verified against the shadow every cycle; status read first** — `:665-686, 929-940`. Commits 5689e2f4.
Origin SF-M3-04 (agent), M.SRC_SENS.077 (1). Evidence H. Form design. Cost ~9 lines; +1 3-byte read per cycle on a
shared bus (~1 ms at 50 kHz). Triage **implausible**: the datasheet's only ways a CONFIG byte changes without our write
are a reset or brownout (BOUTF, handled), and a partial write is already reconciled by the pre-audit failed-write path.
Class **H**. Scheme HYP, P6.

**ISL-11 Participant rung: re-configuration from the shadow; init hooks** — `:247, 471, 515, 522, 801-812, 834-842`.
Commits 5689e2f4. Origin A.U15.R04. Evidence O-gen (OR113). Cost ~14 lines. Class **R**. Scheme none.

**ISL-12 Restart resets (`_filtered`, `_irq_fired`, the periodic count, the park flags)** — `:460-465`. Commits
5689e2f4. Origin A.U15.34 (G3/R56). Evidence H. Cost 6 lines. Triage **implausible** (one filter step or one decision
mis-credited after a restart). Class **H**. Scheme HYP.

**ISL-13 `_write_failures` wraps at COUNTER_CAP** — `:1372`. Commits 5689e2f4. Evidence O-gen (OR103/OR105). Cost 1
line. Class **R** (trigger implausible). Scheme none.

**ISL-14 False bus results raise (7 sites)** — `:1220-1227, 1242-1251, 1253-1260, 1287-1290, 1298-1304, 1487-1495,
1502-1522`. Commits cbb65df2, 5689e2f4, 06a8ae5d. Class **C** (root I2C-8 ← I2C-3). Cost ~16 lines. Scheme HYP.

**ISL-15 A chip config read failure answers the GET's unavailable marker** — `:779-787`. Commits f5c82557. Origin SF-B8.
Evidence H. Class **H** (implausible: display only). Cost ~5 lines. Scheme HYP.

**ISL-16 Timer arm failure** — `:993-995`. Evidence O-gen (OR31.a). Class **R** (trigger implausible). Cost 2 lines.

**ISL-17 `period is None` guard in `set_resolution()`** — `:1152-1153`. Commits 41b47f1d. Evidence H. Triage
**implausible**: its own comment says "set at construction, never None". Class **H**. Cost 1 line. Scheme TYPING.

**ISL-18 TS None and the unsettled cycle are no failure** — `:659, 749, 866-868`. Class **C** (roots `utc_now()` and
ISL-6). Cost ~3 lines.

**ISL-19 `report_if_fatal(e)` in 20 broad handlers**. Class **C** (root C-stack reboot). Cost 20 lines.

**ISL-20 Own RGB burst buffer** — `:1190s, 1487-1495`. Commits 06a8ae5d. Origin A.U30.07. Evidence H (rule-derived).
Class **H** (implausible). Cost ~3 lines. Scheme OR110.

Removals: **ISL-R1** the brownout latch `_brownout_seen` (A.U3.14): every brownout warns, the newest-entry rule spends
one slot (OR35.b, `PROJECT_AUDIT_PLAN.md:339`, owner: "just don't repeat the same error in the slots. Pure and
simple.") — class **R**, scheme none. **ISL-R2** D2S's TypeError catches and tuple-length check (890c5ab1) — evidence
O-spec (TYPING rule) — class **R**.

---

## Per-file totals

Rows and approximate added code lines per class (removal rows included in rows, 0 lines).

| file | R | K | H (of which confirmed) | X | C | rows |
|---|---|---|---|---|---|---|
| asy_i2c_driver.py | 2 / 52 | 0 | 4 (1) / 25 | 2 / 81 | 3 / 33 | 11 |
| asy_spi_driver.py | 0 | 0 | 2 / 20 | 0 | 1 / 3 | 3 |
| asy_neopixel_driver.py | 3 / 20 | 0 | 4 / 23 | 0 | 0 | 7 |
| asy_notification_service.py | 2 / 23 | 0 | 4 / 48 | 0 | 2 / 16 | 8 |
| voc_algorithm.py | 2 / 17 | 0 | 2 / 35 | 0 | 1 / 9 | 5 |
| asy_bmp3xx_driver.py | 5 / 33 | 0 | 8 / 51 | 0 | 3 / 36 | 16 |
| asy_scd30_driver.py | 7 / 263 | 0 | 2 / 20 | 0 | 4 / 30 | 13 |
| asy_sgp40_driver.py | 10 / 71 | 0 | 8 (1) / 61 | 0 | 5 / 35 | 23 |
| asy_isl29125_driver.py | 11 / 110 | 0 | 8 (1) / 49 | 0 | 3 / 39 | 22 |
| **group C** | **42 / 589** | **0** | **42 (3) / 332** | **2 / 81** | **22 / 201** | **108** |

R by evidence: O-spec 29 rows (~485 lines), O-gen 13 rows (~104 lines; every O-gen row states its trigger — six have
an implausible one: the counter caps SCD-8 and ISL-13, the timer-arm handlers BMP-14, SCD-9, SGP-20, ISL-16). No F.
The two X rows are confirmed or owner-backed intents with excess code (I2C-2's duplicate clock-out, I2C-6's write
path). No K row: every valuable finding here either carries owner backing (R) or is a plain hypothesis (H).

Scheme violations per file (a row can carry several):

| file | HYP | MIN | DELAY | TYPING | OR35a | OR110 | FEAT | P4 | G1 | P6 |
|---|---|---|---|---|---|---|---|---|---|---|
| asy_i2c_driver.py | 4 | 3 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 |
| asy_spi_driver.py | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| asy_neopixel_driver.py | 3 | 1 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| asy_notification_service.py | 5 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 0 | 0 |
| voc_algorithm.py | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| asy_bmp3xx_driver.py | 7 | 1 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 |
| asy_scd30_driver.py | 2 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| asy_sgp40_driver.py | 8 | 1 | 1 | 1 | 0 | 2 | 0 | 0 | 0 | 0 |
| asy_isl29125_driver.py | 6 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 |
| **group C** | **38** | **8** | **4** | **6** | **2** | **7** | **1** | **1** | **1** | **2** |

Rules violated most often: HYP (38 rows: code on a hypothesis, or a cascade whose root is not owner-decided), MIN (8),
OR110 (7 allocation reductions of temporaries the owner had accepted), TYPING (6 guards unreachable with today's types), DELAY (4: NP-2's 120 s deadline, NP-5's
300 s rewrite, NT-3's and SGP-2's 10800 s age checks).

## Cascades

1. **Recovery ladder (OR113)** → I2C-2/I2C-3 → I2C-4 (`recoveries`, then CO1's reorder) → `recover()`'s
   `_REC_NO_CONTROLLER` makes "no bus" reachable at run time → I2C-8 (bool contract) → BMP-11, SCD-11, SGP-19, ISL-14
   (≈ 52 lines of `if not await ...: raise OSError("I2C bus not initialized")`) → SPI-1/SPI-2 copy the contract with no
   run-time trigger. The rungs are owner-backed; the bool cascade is ≈ 77 lines for a state only a failed controller
   re-construction produces.
2. **Boot clear (OR113)** → I2C-5 `take_boot_clear_status()` → the base reader's one-time report.
3. **SF-A01 (confirmed)** → I2C-6's preassembled writes (`_fill_reg_addr`, `_write_buffer`, `_MAX_ADDRSIZE`, oversize
   fallback) → the STOP-on-short `try/except` → reused by SF-A02's `_point_at()` (I2C-7).
4. **FRC readiness (O)** → SCD-2 config reader + RAM-only log → SCD-3 routes FRC keys to the file store →
   `_capture_frc_config()`'s episode guard; the IRQ loop's idle ticks; `_republish()` on stop.
5. **SCD30 range gate (O)** → the chip-offset cache (+1 register read at setup, kept by the setter) → E27, shared with
   BMP-5.
6. **`utc_now()` None before the first sync (O, outside C)** → `condition=` in all four `_error_check()` calls (BMP-10,
   SCD-10, SGP-22, ISL-18) and the store guards → the "TS None counts as current" clauses in NT-3 and SGP-2.
7. **Stale-sample bounds (H)** NT-3 and SGP-2 → depend on cascade 6's exception.
8. **NeoPixel queue deadline (NP-2)** → NT-5 (W67, the default-sink identity, a `staticmethod` sink).
9. **NT-2 `_check_one()` → None** → the State codes → the config-unreadable branch storing a sample.
10. **BMP-1 POR detection (H)** → `reset()` reading EVENT away → `_set_lock` around the re-apply → BMP-2's 8-byte burst.
11. **ISL-10 per-cycle verify (H)** → the status read moved first (a brownout cycle skips the divergence check).
12. **ISL-1 INT parking (O)** → `_note_decision_source()` returns early while parked (else parking would trip the
    dead-INT warning) → `set_range_auto(True)` clears the flag → ISL-2's re-arm skips parked periods.
13. **ISL-6 settle discard (O)** → `_unsettled_cycle` → the `_error_check()` condition (ISL-18).
14. **VOC-2 uptime 16383 (O-gen)** → VOC-3's clamp of an older build's backup.
15. **SGP-1 VOCState counters (O)** → reused as SGP-12's "live state" test.
16. **SGP-14 one backup buffer (H)** → its re-allocation retry and the "both parts wait a cycle" path.
17. **NP-5 300 s overlay rewrite (H)** → the `wait_for_ms()` wrapper → a lost shutdown cancel (confirmed by the lead).
18. **C-stack reboot (O, outside C)** → `report_if_fatal(e)` in ~58 handlers here (NT-8, BMP-15, SCD-13, SGP-23, ISL-19).
19. **Timer-arm handling (OR31.a)** → `_timer_failed()` in each `start_timer()`, `_rearm_timer()`/`_timer_fault()` in
    each loop (BMP-14, SCD-9, SGP-20, ISL-16).

## Verifications

**V1 — SF-A02, a NACKed register byte leaves the read buffer untouched (platform). Confirmed.** Pinned source v1.29.0:
rp2's protocol struct sets no `transfer_supports_write1` (`ports/rp2/machine_i2c.c:161-164`), so `read_mem()` writes
the address with no stop and, when that write returns short, sends a STOP and returns the count (`extmod/machine_i2c.c:
556-560`); pico-sdk returns the
byte count, 0 here, for a data NACK after an ACKed address (`lib/pico-sdk/src/rp2_common/hardware_i2c/i2c.c:222-232`:
`ABRT_TXDATA_NOACK` → `rval = byte_ctr`); `machine_i2c_readfrom_mem_into()` raises only on `ret < 0` (`:625`) and
returns None with the buffer as it was (`:628`). `readfrom_mem()` (legacy) returns its fresh, uninitialised `vstr` the
same way (`:603-607`). How often a device NACKs a register byte is board-only (hardware-round list).

**V2 — SF-A01, a NACKed data byte in a register write is reported as success (platform). Confirmed.** `write_mem()`
passes the address and payload to the transfer (`extmod/machine_i2c.c:565-580`); a data NACK returns the short count
(`i2c.c:229-231`); `machine_i2c_writeto_mem()` raises only on `ret < 0` and returns None (`:645-649`), so the count never
reaches Python. Frequency board-only.

**V3 — ISL29125 settle deadline past the tick horizon (software, pre-audit code). Confirmed; head refuted.**
`S/u35r/scan/work_C/v3_isl_settle_horizon.py` drives the pre-audit `ISL29125_I2C.time_to_settle_ms()` and
`ISL29125_Reader._settle_wait()` (`25caf528` tree exported to `work_C/pre/`) with a `time` stand-in computing
`ticks_ms/ticks_diff/ticks_add` exactly as `extmod/modtime.c:166-196` on rp2's 2**30 period (`py/smallint.h:42` with
`MICROPY_OBJ_REPR_A`, `py/mpconfig.h:1925`). One CONFIG1 write, then: +1 s → 0, +1 h → 0, +6.2 d − 1 min → 0,
**+6.2 d + 1 min → 536811518 ms**, +9 d → 296142430, +12.4 d + 1 min → 0; `_settle_wait()` at +6.2 d + 1 min requests
`sleep_ms(536811518)` (≈ 6.2 days) for the read task. Runs `v3_pre_1..3` identical (logs `work_C/v3_pre_*.log`, rc 0).
The same script on head prints 0 throughout and requests no sleep (`v3_head.log`). Pinning test at head:
`tests/test_asy_isl29125_driver.py::test_a_passed_settle_deadline_never_ages_past_the_tick_horizon`.

**V4 — SGP40, a measurement that fails on the restore cycle (software, pre-audit code). Confirmed.**
`work_C/v4_sgp40_restore_lost.py` calls the pre-audit `SGP40_Reader._read_sgp()` with `deserialize=True` (the state
`_run_restore()` leaves after loading a dated backup, `voc_init = 0`) and a chip stand-in raising `OSError(5)`, then
`_check_storage()` once per second. Output: the read fails ("Read failed:", errno 11), `voc_init` stays 0, no restore is
attempted again, and at second 55 the next backup is due (`serialize=True`) — it serialises the fresh, un-restored
algorithm state over the stored backup. Runs `v4_pre_1..3` identical, rc 0. How often an SGP40 read fails on that one
cycle is board-only. Pinning test at head:
`tests/test_asy_sgp40_driver.py::test_a_restore_cycle_whose_read_fails_keeps_the_backup_for_the_next_cycle`.

Not re-verified, by the brief: NP-5 and its lost-cancel cascade (lead, LEAD NOTES 358).

Every other H row was triaged implausible (reason in the row); none was left unverified for lack of a minimal check.

RUNS.md: seven runs, each with its RUNNING and done line (`U35 scan C v3_pre_1..3`, `v3_head`, `v4_pre_1..3`), one at a
time, all `rc=0`.

## Hardware-round list

1. I2C data-byte and register-byte NACKs on the dev buses (V1, V2): whether and how often the BMP3XX, ISL29125 and SCD30
   NACK a data or register byte; the platform behaviour itself is settled.
2. SGP40 measurement failures on the restore cycle (V4): the read-error rate right after boot.
3. WS2812 blanking under Wi-Fi bursts (NP-5's OF-75 premise): does the pixel lose its state; only then is any rewrite
   needed.
4. BMP3XX `por_detected` in operation (BMP-1) and ISL29125 CONFIG bytes changing without a write (ISL-10): board-only;
   triaged implausible.
5. The boot clear freeing a held slave (I2C-1) and the runtime rungs on silicon (existing H16 row, `audit/actions/C.md:714`).

## Minimal-change list (R and confirmed items, against the pre-audit code)

Each: the change, its size, the test that pins it (existing head test, or what it would assert).

- **I2C-1 boot clear**: a `_clear_bus(scl, sda)` before `init()`: SDA low → ≤ 9 SCL pulses, then STOP. ~15 lines (head 42).
  Pin: `test_the_boot_clear_stops_pulsing_once_the_slave_releases_sda`, `..._gives_up_after_nine_pulses_...`.
- **I2C-2/3 runtime rungs**: `clear()` = run the same clock-out under the bus lock with an awaited per-pulse wait
  (one implementation with an injected wait, not two copies); `recover()` = clear then `init(*stored args)`. ~20 lines
  (head 56). Pin: `test_recover_clears_then_re_constructs_with_the_stored_frequency_and_timeout`.
- **I2C-6 SF-A01**: in `_writeto_mem()`, `buf = bytes((reg_addr,)) + payload` (every driver uses 8-bit addresses) and
  `if bus.writeto(address, buf) != len(buf): raise OSError(EIO)`. ~4 lines (head ~35). Pin:
  `test_a_nacked_data_byte_in_a_register_write_raises_eio_and_stores_nothing`.
- **I2C-7 SF-A02**: in `_read_into_scratch()`, replace `readfrom_mem_into()` with
  `if bus.writeto(address, bytes((reg_addr,)), False) != 1: bus.writeto(address, b"", True); raise OSError(EIO)` then
  `bus.readfrom_into(address, view)`. ~5 lines (head 9). Pin: `test_a_nacked_register_byte_raises_eio_instead_of_a_stale_read`.
- **NP-1**: in `led_signal()`, refuse while `start_signal_event.is_set()`, set the event directly; drop the watcher task
  and `ext_*` state. −15 lines. Pin: `test_led_signal_is_refused_at_once_while_a_ramp_runs_and_nothing_is_queued`.
- **NP-2**: in `request_signal()`, replace the `sleep(0)` spin with a frame-period wait bounded by a deadline. ~4 lines.
  Pin: a test asserting a request made while a signal runs starts after it and returns False past the deadline.
- **NP-5 (confirmed cascade defect)**: revert to the pre-audit `await self.led_overl_start.wait()` (no timeout). −5 lines.
  Pin: the lead's probe as a test — a cancel delivered while the overlay task waits ends it (S/u35/lead/probe/np_verify/).
- **NT-1**: `_in_window()` with the over-midnight branch. 5 lines. Pin: `test_sleep_window_boundaries_inclusive` and
  the midnight cases beside it.
- **NT-6**: the pause as a measured countdown (`TickSeconds`). ~6 lines over `LockedCounter`. Pin:
  `test_the_pause_counts_measured_time_not_rounds`.
- **VOC-1**: `_int32()` and its calls, the INT32_MIN constants, the masked `bit`. 16 lines. Pin: the Sensirion vector
  tests in `tests/test_voc_algorithm.py` (gas-index-algorithm 2ef9f13).
- **VOC-2**: `_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX = const(16383)` and the restore clamp (C). 4 lines. Pin:
  `test_a_restored_uptime_above_the_small_int_limit_is_clamped`.
- **BMP-4, SCD-7, SGP-7, ISL-11 participant rungs**: one `_recover_device()` each (soft reset + stored config; soft
  reset; heater off; shadow re-apply). 8 / 8 / 8 / 3 lines. Pin: each driver's rung case in the four bus-hazard tiers
  (CLAUDE.md bus-hazard rule).
- **BMP-6**: the SLPres domain test with W11. 4 lines. Pin: a reading with PresOffset pushing it past 1250 hPa stores
  SLPres None and one W11.
- **BMP-7**: `MeanAtmTemp` −40. 1 line. Pin: `test_mean_atm_temp_below_minus_40_is_refused_and_minus_40_yields_a_sea_level_pressure`.
- **BMP-8**: capture the four compensation floats before the conversion. ~6 lines. Pin: a PUT during a conversion changes
  the next stored sample, not this one.
- **SCD-1/SCD-2 FRC readiness**: as owner-specified; ~130 lines is the specification's size. Pin: the FRC table test in
  `tests/test_asy_scd30_driver.py` (`:154`).
- **SCD-3 compare-before-write**: ~60 lines over the pre-audit `_set_dict_cfg()`. Pin: the Unchanged/AmbPres/ForceCalRef
  cases in `tests/test_asy_scd30_driver.py`.
- **SCD-4**: `int(offset * 100 + 0.5)`. 1 line. Pin: `test_temperature_offset_rounds_to_the_nearest_tick`.
- **SCD-5**: the range test and the offset cache. ~10 lines. Pin: `test_range_checks_raise_before_touching_the_bus` and a
  read whose CO2 is 40001 ppm failing.
- **SCD-8, ISL-13 counters**: `if v < CAP: v += 1`. 1 line each. Pin: a test at the cap.
- **BMP-14, SCD-9, SGP-20, ISL-16 timer arm**: in each `start_timer()` `except`, hand the error to the woken task. 2 lines
  each (+ the base helper). Pin: an arm raising ENOMEM ends the task with one entry and the restart re-arms.
- **SGP-1 VOCState**: the saturating count and the four codes. ~15 lines. Pin: `test_voc_state_is_zero_through_the_blackout_then_learning`.
- **SGP-3**: clamp before converting to ticks (drop `& 0xFFFF`). 2 lines. Pin: `test_celsius_to_ticks_matches_datasheet_table_10`.
- **SGP-4**: move the command fill inside `async with self.i2c_sgp40`. 0 lines added. Pin: the SGP40 measure case in
  `tests/test_bus_hazard_multi_device.py` (`:351`).
- **SGP-5**: `try/finally` around the measure read. 3 lines. Pin: a failed read followed by `initialize()` sends a
  2-byte command.
- **SGP-6**: `readlen=3` in `initialize()`'s serial read, a 9-byte reply buffer. 2 lines. Pin:
  `test_initialize_success_probes_serial_number_then_self_test_then_resets`.
- **SGP-8**: `voc_init = max(1, wait)`. 1 line. Pin: WaitTimeNTP 0 restores on the first cycle.
- **SGP-9**: `age < 0 or age > ...`. 1 line. Pin: a backup dated in the future is rejected under a nonzero BackupMaxAge.
- **SGP-16**: `max(1, ...)` in the verify formula. 1 line. Pin: `test_init_sgp_sets_verify_to_the_documented_formula`
  (p = 67, 1440 give 1).
- **SGP-17 (confirmed V4)**: in `_read_sgp()`'s `except`, `if deserialize: self.voc_init = 1; self.backup_counter = 0`.
  3 lines. Pin: `test_a_restore_cycle_whose_read_fails_keeps_the_backup_for_the_next_cycle`.
- **ISL-1 INT parking**: `_int_held` with park/unpark in `_read_isl()` and the early return in
  `_note_decision_source()`. ~15 lines. Pin: a red-bright, green-dark scene stops re-firing INT after one PRST window.
- **ISL-2**: on the fifth periodic-only decision, once per episode, `configure(force=True)` and a threshold rewrite. ~8
  lines. Pin: five periodic-only decisions → one CONFIG burst and one threshold write.
- **ISL-3**: a threshold lock around derive-write-commit, and the rewrite in the two setters. ~15 lines. Pin: a
  resolution change rewrites the thresholds with RangeAuto off.
- **ISL-4 CalLight**: `_band_code()` and the field. ~10 lines. Pin: `test_cal_light_marks_the_calibration_band_at_its_edges`.
- **ISL-5**: cache FiltCoeff in the setter and capture it with the cycle. ~5 lines. Pin: a FiltCoeff PUT mid-cycle
  applies to the next sample.
- **ISL-6**: past the bound, return the cycle unpublished and uncounted. ~5 lines. Pin: the unsettled-cycle case at
  `tests/test_asy_isl29125_driver.py:1372`.
- **ISL-7 (confirmed V3)**: in `time_to_settle_ms()`, when the deadline has passed, set it to now and return 0. 3 lines.
  Pin: `test_a_passed_settle_deadline_never_ages_past_the_tick_horizon`.
- **ISL-R1, NP-R2, ISL-R2 removals**: as landed.
- The C rows of cascades 6 and 18 (TS-None conditions, `report_if_fatal`) follow their owner-approved roots outside
  group C; they are not listed as separate changes here.
