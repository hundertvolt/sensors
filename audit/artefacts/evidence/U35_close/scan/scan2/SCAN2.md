# Second pass: hidden, overlaid and higher-order overkill

Written by the lead, 2026-10-28 10:20 UTC. Range: the audit's start `25caf528` to the integration head
`497b3eda`. Read-only: nothing in the repo changed, and nothing ran on the Unix port, the twin or the tests.

The owner's request (2026-10-28): "Now with all that background and a sharpened vision, go through the changes since
the audit start again and check if you found all such runaways, cascades, overkill places; there might be more
hidden or overlaid / higher dimensional occurrences you did not see yet. And if you would remove those you already
know, there might be side effects which make more overkill visible. Nevertheless, real features, real findings
inside the minimal code, rare but real cases all keep effective."

The background it builds on (owner, the same day; `PICTURE.md` section 8): findings and decisions stay documented;
those tied to a removed cascade become obsolete with it; those in scope stay effective "with way more minimal code";
"Rare but real conditions staying in scope still shall be addressed - no regressions, but more efficiency."

**How it was done.**
- **A mechanical census of `src/`** at both ends (`tools/census.py`, `funcs.tsv`, `families.tsv`). It lists every
  new, changed or removed function with its shape changes: try, raise, guards, time calls, waits, tasks and timers,
  `report_if_fatal()`, log calls, new on/off flags, new numbers. It found 552 new, 397 changed and 379 removed
  functions (renames included), about 60 new boolean state flags, and 112 functions that gained `report_if_fatal()`.
- **Four read-only parts, split by lens rather than by module:**
  - G1: core, storage and drivers;
  - G2: network, UART and web;
  - G3: buildgen, generated code and the website;
  - G4: the shared helpers and the removal closure.

  G4 then ran a second round over G1-G3's new roots, with a crosswalk of all rows. Two rounds reached a fixpoint.
- **The lead's own checks.** Each new claim the result rests on was checked against git, the pinned MicroPython
  v1.29.0 source or the owner record (section 8). Where parts disagreed, the lead decided against the record (section
  7).

Part files: `G1.md`, `G2.md`, `G3.md`, `G4.md`, `G4b.md`; closure data `G4_closure.tsv` (1,875 rows, 143 roots) and
`G4b_closure.tsv` (254 rows, 30 roots). Line counts below are code lines at `497b3eda`, approximate, and deduplicated
across parts by mechanism.

## 1. In short

- **The first scan missed whole classes, not only single items.**
  - About 820 device lines would go beyond what the owner decided. Most of them were already in doubt in the first
    scan; about 230 lines are newly in doubt: rows rated R or K before, or never rowed.
  - About 170 more lines are the form of owner decisions that fit in far less code, for example the C-stack check:
    123 call sites become one check in the logger.
  - Outside the firmware: about 160 lines of website code frozen into every image, and about 180 lines of build-host
    code.
- **Some of the first scan's doubts were wrong the other way.**
  - 13 Wi-Fi rows (about 116 lines) are owner-settled.
  - The C-stack rows are the owner's decision.
  - The asyncio handler that keeps "Task exception wasn't retrieved" silent at level 0 carries the owner's Q6
    "Option a".
  - The loop-end labels 21 and 22 are a confirmed gap.
  - The three website items in `PICTURE.md` M13 all trace to the owner.
- **The removal closure.** Taking out every in-doubt item touches no rare-but-real condition that stays in scope. It
  also regresses no confirmed gap of `REPORT.md` section 3, as long as five things stay:
  - the unreadable-log-store branch;
  - captive DNS's 512-byte receive;
  - the shutdown's report of an unpersisted store;
  - the Q6 handler;
  - a 3-4 line Microdot hook for the C-stack decision.
- **Nothing needed a run.** Every claim the result rests on was settled from source, git or the owner record. Four
  checks are left for the hardware round or the cleanup itself (section 8).

## 2. The patterns behind it

These are the higher-order shapes: none of them shows in a single file or a single row.

1. **An unreachable state, multiplied across its consumers.** One addition made a state possible on paper, and every
   consumer then grew code for it:
   - "no I2C bus": a bool contract, 26 driver raises, and the SPI and FRAM copies (about 112 lines). The state cannot
     occur on rp2 (section 8, check 1).
   - "refused timer arm": six different handling shapes in five modules (about 85 lines), on a trigger the first scan
     refuted (alarm-pool exhaustion, A.md V6).
   - "lost FRAM chip": about 60 lines, on an unverified premise (the SPI line's level with the chip absent, on the
     hardware list).

   The cure is the same each time: remove the state where it is produced, and the consumers' code goes with it.
2. **One mechanism per site instead of one in the shared base.**
   - `report_if_fatal()` at 123 broad handlers, 118 of which already hand the exception to a logger.
   - Memory-gate console lines, both per site and in the logger, two layers for one test need.
   - Per-episode log flags in several modules, on top of the owner's central newest-entry rule.
   - Two consumers each checking a producer's sample age.
   - Typing-only guards across drivers.
3. **A placement that creates its own problem, then a fix for that.**
   - The refused web connection now waits for its FRAM trace. That created OF-254, and OF-254 then got a 5 s bound.
     The pre-audit code closed the connection at once: "cheapest, doesn't risk the rejection path itself becoming a
     resource consumer".
   - Already known from the first scan: the NeoPixel 300 s check that lost a cancel, the UDP deadline that lost a
     cancel, the NTP cadence chain.
4. **Machinery that checks what the same build already guarantees.**
   - Build checks that no TOML value can ever trip. This is not only "no current TOML": shown by arithmetic from the
     src constants and four probes on modified copies.
   - The browser re-validating definitions that the build generated, checked and parsed back: about 135 lines of
     JS in every image.
   - dev's UART values checked both at build and at construction.
   - The boot oracle running on every firmware build, for tests only.
5. **Test needs inside the product (P4).**
   - Console lines for the memory gates.
   - `setup()`, `deinit()` and `set_level()` widened to bool, with one product reader on dev only.
   - A guard kept for a PC test tier.
   - Buildgen exports and TOML keys read only by tests, the twin or the bench.
6. **Code with no reader left.**
   - Eight writes of the fatal flag after its only reader has stopped.
   - `restored`.
   - The notification's whole state machinery, once its /status key goes.
   - The reset-flag registers and their `mem32` read, once `ResetBits` goes.
   - Twenty branches "kept to narrow the Optional for the type checker".
7. **One addition seeding many records.** Each mechanism brought catalog codes, /status keys, tunables, JS fields
   and spec text.
   - 15 catalog codes exist only for doubted mechanisms.
   - Under the catalog's "Retired numbers are never reused" rule (agent text, no owner words found), removing them
     leaves 15 tombstones.
8. **An owner's general principle applied by an agent to a case found by reading, and rated R.**
   - Four driver timer re-arms (BMP-14, SCD-9, SGP-20, ISL-16).
   - ISL29125's dead-INT re-arm (ISL-2).
   - `_init_failed()` inside the recovery ladder.

   They stand on unobserved or refuted triggers, so they are H. The ladder itself stays R: OR113, "Apply this idea
   throughout!".

## 3. The finds, by mechanism

"Go" means the lines that would go; "stays" means the minimal form that keeps a real effect.

### Firmware: newly in doubt, or larger than the first scan had it

| mechanism | evidence | go | stays |
|---|---|---|---|
| I2C/SPI "no bus" contract (I2C-3's failure branch, I2C-8, 26 raises, SPI-1/2, E52) | rp2's `machine_i2c.c:61-118` and `machine_pin.c`: the re-construction with the stored arguments cannot fail | ~112 | the ladder's rungs |
| refused timer arm, six shapes (incl. BMP-14, SCD-9, SGP-20, ISL-16 from R) | trigger refuted (A.md V6); the pre-audit code caught every arm | ~85 | the pre-audit catch per arm; Wi-Fi's settled re-arm |
| memory-gate console lines, per site plus the logger arm | P4; the owner chose test-side logging for the gates ("Option 1 is good", 2026-10-20) | ~70 | the catches; their text through an existing logger |
| typing-only guards and the 20 "narrow the Optional" branches | TYP (2026-10-27 rule); the code's own comments | ~100 | a typing-side form for the narrowings |
| the lost-FRAM chain, and what it leaves | premise unverified (hardware item) | ~60 | the declared-chip escalation (OR89) |
| sample-age checks at two consumers (plus SCD-6) | they fire only for a loop that stops without ending; the SCD30 re-stamps its cached values every cycle, `ContMeas` Off included (`_store_scd()`) | ~30 | nothing |
| the resolver widened to `(address, cause)` and `pr=` (DNS-3, NTP-5: K) | one caller; two catalog codes | ~30 | `resolve_ipv4() -> str or None` |
| per-episode log flags | over the owner's newest-entry rule; one reachable trigger for the config reads (a directory at a config path) | ~25 | the newest-entry rule (A-P1) |
| notification state machinery, once the `State` key goes (S2-G4X-2) | no other reader | ~25 | `Triggered`, `TS`, E15 |
| `setup()`/`deinit()`/`set_level()` bools | read only by tests, except `UARTComm.setup()` on dev | ~20 | that one bool |
| W69 and its reset-reason exclusion | its own false positive | ~20 | nothing |
| pre-setup log merge | unreachable through the generated boot order | ~20 | the unreadable-store branch (a confirmed gap) |
| webserver start retries | beside the supervisor's restart | ~19 | nothing |
| `ResetBits` registers and `mem32` (S2-G4X-1) | go with the H key | ~17 | the reset-reason decode (OR60) |
| /status keys for H mechanisms | follow their mechanisms | ~16 | ResetReason |
| ISL29125 dead-INT re-arm (ISL-2, from R) | unobserved; a quiet INT line is no error the ladder sees | ~14 | ISL-1's parking |
| NTP cadence chain (two `TickSeconds`) | a 10 s slack the owner called irrelevant | ~14 | `_sync_age` |
| the escalation's 1,200 ms bound | the record is written before the wait; the watchdog keeps the reboot | ~14 | the record, then a plain entry write |
| unavailable-marker producers beyond the base | K | ~12 | the base producer and one JS check |
| UART DMA-ring guards for states no product path creates | `rp2_dma.c` and grep | ~11 | the ring (OR141) |
| `timed_out`, the W49/W50 split | K | ~10 | one code |
| `_init_failed()` (from inside A-B13) | inverts OR113's mild-first order | ~10 | `_rungs = 0`, I2C-5's boot-clear report |
| the LED drop warning W67 and the default-sink identity test | the deadline answers False only because of the deadline | ~10 | the deadline (owner-approved text) |
| fatal-flag writes after the reader stopped | the supervisor is gone | 8 | nothing |
| NTP-3 and DNS-1 covering each other | neither reachable from a pre-audit file (key renamed) | 8 | NTP-1's PUT check |
| allocation failure split from bad input | K | 7 | UC-4's catches (owner option c) |
| the participant rung guarded twice; boot-race guards; small dead constants | grep | ~12 | the hooks' own catches |
| WS-2's refusals and WS-9's print rebind, one motive | a console stall needs a USB host that never reads; field units have none | ~38 | WS-1's bounds; a 3-4 line rebind for the C-stack report |
| the refusal path (close, then trace) | the pre-audit "reject cheaply" rationale; OF-254's root | ~2 moved | WS-3's traces, WS-4's count; WS-6's bound on the other arms |

### Firmware: owner decisions in far less code (form only)

| decision | as landed | smaller form |
|---|---|---|
| C-stack reboot (review `c-stack-reboot` "ok") | 123 `report_if_fatal()` calls, plus a flag | one check in the logger's `_line()`, 4 explicit calls and the Microdot hook: ~118 lines go |
| rejected setting costs no flash write (review `failed-push-no-flash-write` "ok") | `defer=`, `commit()`, `_commit_ready`, its reach into the reset path | one `write_config()` after the push loop: ~30 lines go, ~3 stay |
| the reset and shutdown path (owner) | "a reset is under way" in six flags; flushes at several layers | one phase value: ~15 lines go |
| the LED internal-request wait (review `led-request-internal-queue`, "Fine, and this for a reason ...") | the 120 s deadline (its value is the agent's) | stays as decided; only W67 and the identity test go |

### Website and build host

| mechanism | evidence | go |
|---|---|---|
| the browser's definitions validator, one per hint | the definitions are generated, checked by buildgen and parsed back, all frozen together | ~135 (JS, every image) |
| the page build-date stamp (OF-144) | an agent scan; the owner's first-build compare runs at page start | ~18 (JS and stager) |
| errcount table twice per site; the device watch's extra /status | gzip absorbs most of it | ~6 |
| build checks that no TOML value can trip (budget, loop hold, UART bounds) | arithmetic from src constants; four probes | ~60 (one boot-clear timing check stays) |
| buildgen exports, helpers and TOML keys only tests read | grep | ~75 |
| the boot oracle in every firmware build | only the twin and tests read it | moves to the test side |
| the module-file table restated six times; `_urgency` | grep | ~26 |
| the catalog's owners and bands, read by one test | grep | ~20 (optional) |

## 4. What the removal makes visible (the closure)

Order 2 and 3, after the known items go:
- `verify_present()` loses its only product caller once the lost-FRAM chain goes, and `is_ready()` becomes an alias
  of `initialized` with one user.
- `console()` keeps one caller outside the gates, so it becomes a plain `print()`.
- `arm_tick_timer()` shrinks to a four-line try. With the pre-audit per-site catch restored, it goes altogether.
- `_ERR_TIMER = const(17)` is defined in four modules; it stays only in Wi-Fi (WF-7).
- The default LED sink's `staticmethod` and its identity test exist only because the deadline lets the request
  answer False.
- Two of six `TickSeconds` exist only for the NTP cadence chain.
- `DNS_NAME_MAX`, the reader base's `_ERR_CALLBACK`, and buildgen's parse of four UART constants then have no user.
- Every removed code becomes a `"retired": true` catalog row under the never-reuse rule.

The second round added 8 rows and reached a fixpoint after two rounds. No rare-but-real condition drops out.

## 5. What stays effective

**Owner decisions in their smallest form:**
- the recovery ladder's rungs (OR113);
- the C-stack reboot (logger check, explicit calls, Microdot hook);
- the newest-entry rule;
- the staged write after the pushes;
- the reset path and system commands;
- the NeoPixel queueing and REST refusal, with NP-5 reverted;
- the FRAM per-owner seed;
- the UART DMA ring and hazard mode;
- WS-1's head bounds;
- WS-3's drop traces and WS-4's count;
- the Q6 handler;
- the Wi-Fi behaviour as decided;
- the website items the owner approved.

**Confirmed gaps** (`REPORT.md` section 3), each with its 1-14 line fix:
- I2C NACKs that rp2 swallows (I2C-6/7);
- the ISL29125 settle horizon;
- the SGP40 restore cycle;
- the blank FRAM chunk;
- the layout shift (kept);
- the cut config write;
- staging before task creation;
- the unreadable log store;
- the zero NTP transmit timestamp;
- captive DNS's 512-byte receive and one yield per datagram;
- the emergency exception buffer;
- the loop-end labels 21 and 22;
- the lwIP listener close;
- the CRC32 efficiency gap (or leave it);
- the light-theme contrast (as landed).

**Rare but real conditions that stay in scope** (G4b section 4):
- a wedged bus at boot;
- a chip that errors in operation;
- a declared FRAM chip that never sets up;
- an unreadable store at boot;
- an unpersisted store at shutdown;
- a C-stack overflow caught by any handler.

**Cheap bounds by construction** (L2): the counter caps, and the one-comparison `ticks_diff()` horizon in UART comm
(UC-7, now K and kept).

## 6. Corrections to the first scan and the picture

- **REPORT section 4 item 7:** NTP holds no per-episode flag at `497b3eda`; U3 removed them (`65a0df3b`).
- **The deferred flush** (A-B10, A-C10) is the mechanism of the owner's "ok" on `failed-push-no-flash-write`. It is
  R, with a smaller form, not H.
- **Moved to H:** BMP-14, SCD-9, SGP-20, ISL-16, ISL-2, I2C-3's failure branch and `_init_failed()` (from R); the
  bool return (from A-B16).
- **Moved to R:** A-S15, A-P13 and the call-site rows of the C-stack decision (owner "ok"); A-S25 and A-P12 (Q6
  "Option a"); 13 Wi-Fi rows and WF-5/WF-14 (owner-settled).
- **`PICTURE.md` M13 is withdrawn.** The tones are the CalLight "fixed tone table" (review `website-display-details`,
  "Fine, and ..."). The inert drawer is review `website-accessibility` ("Fine, and ..."). The section-switch wait
  keeps the owner's drop trace free of navigation noise (commit 9bf22747). `REPORT.md` section 6 point 4 is
  corrected.
- **`hardware_family`** is answered (OR141.a (1): it stays in `[device]`, checked and never emitted). It is not an
  open question.
- **REPORT section 5:** the PieceBuffer saving is −13 lines, not −25; `trim()` serves `uart_get()` and `readline()`.
- **The Altitude warning** is the owner's (OR100, "20 c").

## 7. Where the parts disagreed, and how the lead decided

1. **The deferred flush** (G1 H, G4 R): **R.** Review `failed-push-no-flash-write` "ok" reads: "A setting is staged
   first and written to flash once after it was pushed to the chip." Smaller form as in section 3.
2. **The LED deadline** (G1 R, G4 H): **R.** The approved text says "waits for the running signal up to a deadline
   and then queues ... but bounded", answered "Fine, and this for a reason ...". The 120 s value is the agent's
   (C.md NP-2).
3. **`ContMeas` Off as a frozen-sample path** (G4 K, G1 H): **H.** `_store_scd()` stores a not-new cycle with
   `utc_now()`, so the age never grows. G4 withdrew its row.
4. **The escalation's 1,200 ms bound** (G1 C/DELAY, G4 keep): **goes.** The reset record is written before the wait;
   a hung write ends in the watchdog reboot the decision asks for anyway.
5. **`quiet=`** (G1/G4 go, G2 stays): **stays** while Wi-Fi's settled re-arm passes it. Wi-Fi is form only.
6. **The loop-end clause** (G3 back to the pre-audit `try/finally`, G4 keep the labels): **keep labels 21 and 22.**
   They are a confirmed gap (REPORT section 3); only the BaseException width and the pre-bind go.
7. **The refusal path** (G2 close-then-trace, G4 no change): **close, then trace.** It restores the pre-audit
   "reject cheaply" design. The owner-agreed bound (2026-10-22) becomes obsolete on that arm with its cascade (the
   background note), and stays on the others.
8. **Code tones** (G3 owner, G4 H): **owner** (review `website-display-details`).
9. **`_init_failed()`** (G1 H/OV, G4 keep without analysis): **H**, with the regression flag that `_rungs = 0` and
   I2C-5's report stay.
10. **ISL-2** (first scan R, G1 H): **H**, as item 8 of section 2.
11. **Class labels only** (console lines C or H, bus contract C or H, narrowings H or X): same removal, no decision
    needed.
12. **The section-switch hand-over:** kept (see section 6).

## 8. Checks

**Settled by the lead from source, git or the record:**
1. **rp2 I2C re-construction cannot fail with the stored arguments.** `ports/rp2/machine_i2c.c:61-118` (v1.29.0) uses a
   static object and raises only ValueError for a bad id or pin. `recover()` calls `init(*self._args)` with the
   arguments that already succeeded at boot.
2. **The "Uninitialized, call setup first!" lines in old unit-test logs** come from A-P4's failed-read branch, in tests
   that never set FRAM up, not from the pre-setup merge.
3. **The refusal path at head traces, then closes**, where 25caf528 closed at once ("decision 3").
4. **No per-episode flag in NTP** at head (`65a0df3b`).
5. **The catalog's never-reuse rule is agent text** (`65a0df3b`, SPECIFICATION.md:3653); no owner words were found in
   the plan, the rulings or the review page.
6. **`hardware_family`:** OR141.a (1).
7. **The SCD30 re-stamp:** `_store_scd()` stores `results[3]`, which is `utc_now()` at the read.
8. **The Q6 handler is needed.** In the pinned asyncio (`extmod/asyncio/core.py:222-240`), a detached task that ends
   raising and is never awaited reaches the exception handler, and the supervisor only polls `done()`
   (`asy_system_service.py:563`). Without the handler, the default prints at every level.
9. **The review texts** of `led-request-internal-queue`, `failed-push-no-flash-write`, `website-display-details` and
   `website-accessibility`, and the owner's notes on them.

**Left open, none needed for the cleanup's direction:**
- **Hardware round (with the owner's go-ahead):**
  - 100 `I2C.recover()` calls per bus (optional; the source proof stands);
  - a USB host that never reads, against the pre-audit image (the motive of WS-2/WS-9);
  - the FRAM SPI line with the chip absent (already listed).
- **During the cleanup:**
  - the logger-side C-stack check, run on the Unix port with a near-exhausted C stack;
  - the refused connection's effect on the 9-socket pool (it changes the label from form to behaviour fix, not the
    action).

## 9. Points for the cleanup plan (not questions now)

- **The catalog's never-reuse rule** (agent text) turns each removed code into a tombstone. Whether the rule stays is
  for the cleanup plan.
- **The memory gates without product lines.** The owner's "Option 1" (2026-10-20) sets the direction. The handlers
  that have no logger route their text through the owning module's logger, which is product evidence (P7), not a
  test artefact.
- **The narrowing branches** need a typing-side form (an assertion or a cast) before they can go.
- **The two clock-valid flags** answer differently after an NTP settings change. That split is agent-documented, but
  each step is owner-decided. Conservative: unchanged.
