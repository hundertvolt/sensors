# Harvest H13 — SPECIFICATION.md lines 3422-6785, Parts F–M (snapshot 2a88cc8)

Note: the plan's SPECIFICATION.md line citations were taken at baseline `0615eba`; at `2a88cc8` the same text sits ~4 lines later (e.g. `## I.6` plan :5161 = now :5165). All cites below are at `2a88cc8`.

## SPECIFICATION.md Part F.1 — Core platform facts
- PLATFORM | SPECIFICATION.md:3426-3430 | "Deployed units run **MicroPython 1.26** ... The refactor pins **v1.29.0** ... targets whatever's most recent stable at the time" | Two runtimes in play (1.26 fielded, 1.29.0 refactor); "most recent stable" is a moving target the pin must be re-checked against. | area: PLAT | related: PLAT.T07
- PLATFORM | SPECIFICATION.md:3430-3431 | "MicroPython 1.26 bundles pico-sdk 2.1.1; since pico-sdk 2.0.0, a standalone `picotool` must match its major.minor" | The picotool/pico-sdk coupling is stated for 1.26 only, not for the pinned 1.29.0 build that the toolchain actually builds (low). | area: TOOL | related: TOOL.T09
- PLATFORM | SPECIFICATION.md:3432-3433 | "`machine.WDT` hard-caps at **8388ms**; current code uses `WDT(timeout=8000)` (388ms margin) — don't casually increase" | Silicon/port cap and the 388 ms margin every watchdog budget rests on. | area: PLAT | related: XCUT.T01, PERF.T01
- PLATFORM | SPECIFICATION.md:3433-3435 | "USB (`mp_usbd_init()`) initializes only *after* the frozen `_boot.py` returns" | A blocking `_boot.py` means USB never comes up on a hard reset; port-version-specific boot-order fact. | area: PLAT | related: PLAT.T10
- PLATFORM | SPECIFICATION.md:3435-3437 | "RP2040: dual-core Cortex-M0+ @ up to 133MHz, 264KB SRAM ... Pico W's littlefs partition (~848KB)" | Silicon/board sizing facts (partition size depends on CYW43 blob size, i.e. on the firmware build). | area: PLAT | -
- SETTLED | SPECIFICATION.md:3439-3444 | "**Dynamic imports (`__import__`, `importlib`) must never be used anywhere in this codebase** — project owner's explicit, standing rule" | Owner rule, justified by a future static frozen-module selector; no mechanical check is named here. | area: XCUT | related: XCUT.T16
- INVAR | SPECIFICATION.md:3439-3444 | "Every import stays a real, static `import`/`from ... import` statement, AST-scannable" | Rule upheld by convention; this Part names no lint/test that enforces it. | area: XCUT | related: XCUT.T16, GEN.T05
- PLATFORM | SPECIFICATION.md:3443-3444 | "`importlib` isn't frozen into this project's own manifest today" | Manifest-dependent fact (low). | area: PLAT | -
- PLATFORM | SPECIFICATION.md:3446-3450 | "`mp_sched_schedule()` drops it if MicroPython's fixed-depth scheduler queue (depth 8 on rp2 ...) is full, with no exception" | Soft Timer callbacks can be silently lost; depth-8 is a port/version constant. | area: PLAT | covered-by: XCUT.T22
- INVAR | SPECIFICATION.md:3449-3451 | "every timer that must fire uses `PERIODIC` (C.9), the WiFi hotspot shutoff included (stopped by `reconnect_wifi()` on its first delivered fire)" | Convention-only rule; the plan already records ONE_SHOT timers on critical paths contradicting it. | area: XCUT | covered-by: XCUT.S02
- SETTLED | SPECIFICATION.md:3451-3453 | "A software-timeout mitigation for this was considered and rejected ... don't re-propose without a materially different justification" | Do-not-reopen marker for dropped-soft-callback mitigation. | area: XCUT | covered-by: XCUT.T22
- PLATFORM | SPECIFICATION.md:3455-3461 | "Iterable unpacking inside a list/tuple/set *display* (`[*a, b]`) raises `SyntaxError: *x must be assignment target`" | Parser gap on the pinned version; code relies on `a + [b]` concatenation instead — re-check on bump. | area: PLAT | related: PLAT.T02
- PLATFORM | SPECIFICATION.md:3463-3467 | "`[x] * n` (list repeat) can segfault the interpreter for n in roughly 2⁶¹-2⁶³" | Measured only on the 64-bit Unix port (rp2 cannot express such n); cause "likely" an overflow — inferred, not traced. | area: PLAT | related: PLAT.T02
- INVAR | SPECIFICATION.md:3465-3467 | "Any code sizing an allocation from external/caller input must clamp the size *before* allocating, not just catch `MemoryError`" | Convention for every caller-sized allocation (`LockableBuffer`/`PrintLogHistory` as pattern). | area: MEM | related: MEM.T03
- PLATFORM | SPECIFICATION.md:3469-3478 | "`bool` is NOT a subclass of `int` on MicroPython ... Verified directly against the pinned v1.29.0 build" | Validators rely on `isinstance(x, int)` excluding bool; a version change could alter `mp_type_bool`. | area: PLAT | related: CORE.S12
- SETTLED | SPECIFICATION.md:3476-3478 | "`config_manager.py`'s `type(x) is not int` stays correct either way and is the form to copy; don't add the CPython-only guard" | Do-not-add rule for a bool guard (one was written and removed 2026-09-13). | area: CORE | -
- PLATFORM | SPECIFICATION.md:3480-3481 | "`machine.Timer.init()` can raise `OSError(ENOMEM)` if the RP2040's alarm pool is exhausted — every call site must handle it" | rp2-specific failure mode; per-site handling is a convention. | area: PLAT | covered-by: XCUT.T04
- PLATFORM | SPECIFICATION.md:3481-3483 | "**`MemoryError` is not an `OSError` subclass** ... catch `(OSError, MemoryError)` wherever both are plausible" | Exception-hierarchy fact every except clause depends on. | area: PLAT | -
- PLATFORM | SPECIFICATION.md:3485-3488 | "RP2040's real firmware uses single-precision `float` ... this project's Unix-port test rig uses double precision" | Test rig and target differ numerically; `coerce_numeric()` int→float rounding accepted "since no real schema field's bounds go near it". | area: PLAT | related: PLAT.T08, MEM.T07
- RISK | SPECIFICATION.md:3487-3488 | "accepted, since no real schema field's bounds go near it" | Accepted-by-assumption: holds only while no schema bound exceeds 2**24. | area: CORE | related: PLAT.T08
- PLATFORM | SPECIFICATION.md:3490-3494 | "`'L'` is 4 bytes on rp2 and 8 on the 64-bit Unix-port test interpreter" | Native-size struct codes read differently on target vs rig; rule: explicit `"<"` prefix. | area: PLAT | related: PLAT.T02
- LIMIT | SPECIFICATION.md:3492-3494 | "`dev_legacy/asy_bsec_driver.py`'s bare `struct.unpack(\"bbbbL\", res)` against a hardcoded size of 8 ... anything porting it forward has to fix that first" | Known defect in reference code that a future BSEC port must fix first. | area: SENS | -
- PLATFORM | SPECIFICATION.md:3496-3499 | "overflow checks added to `py/binary.c` are gated behind `MICROPY_PREVIEW_VERSION_2` ... Expect this fact to flip when upstream ships 2.0" | Silent pack truncation; explicit future-flip trigger. | area: PLAT | related: PLAT.T02
- PLATFORM | SPECIFICATION.md:3501-3510 | "A `bytearray` destination *resizes* on a length mismatch ... a `memoryview` destination raises `ValueError`" | Slice-assignment contracts, measured on the Unix port only (not on rp2); plus "no `memoryview.readonly`" and the zero-length-slice writability probe. | area: PLAT | -
- INVAR | SPECIFICATION.md:3505-3507 | "Code copying a computed span into a buffer must therefore bound-check the span itself" | Convention; `asy_uart_comm.py`'s `written + size > len(dest)` guard named as the instance. | area: MEM | related: UART.T03
- DRIFT | SPECIFICATION.md:3512-3515 | "A `micropython.const()`-wrapped value does not survive as an importable module attribute in a frozen build" | Upstream MicroPython docs say only underscore-prefixed `const()` names are hidden; non-underscore names stay module globals — claim may be wrong or narrower than stated (low, not investigated). | area: PLAT | related: PLAT.T02
- PLATFORM | SPECIFICATION.md:3517-3519 | "`time.ticks_ms()` wraps every `2**30` ms (~12.4 days) on rp2**; `ticks_diff()` is correct ... under `2**29` ms" | rp2 tick period fact. | area: PLAT | covered-by: XCUT.T25
- DRIFT | SPECIFICATION.md:3518-3519 | "every real use in `src/` is a short bounded timeout well inside that window" | Contradicted by stored-ticks sites the plan lists (ISL29125, UART hold-off). | area: DOC | covered-by: DOC.S23
- LIMIT | SPECIFICATION.md:3521-3523 | "Unix-port rig has a much larger period (`2**62`, 64-bit) and cannot empirically exercise the real `2**30` rollover — verified by shared, period-parametric code identity instead" | Rollover coverage is by argument, not by test. | area: TEST | related: XCUT.T25, TWIN.T09
- PLATFORM | SPECIFICATION.md:3519-3521 | "`time` module attributes cannot be monkeypatched (a builtin C module's globals dict is fixed)" | Test-design constraint (synthetic ticks via `ticks_add()`/`ticks_diff()`). | area: TEST | -
- PLATFORM | SPECIFICATION.md:3525-3534 | "`globals()` does not preserve a module's top-level statement order ... Nesting `asyncio.run()` ... segfaults ... `await` inside a comprehension is a `SyntaxError` ... async generator ... segfaults" | Four runtime traps; the `/status` streaming design (collect into list, `iter()`) exists because of the async-generator one. | area: PLAT | related: TEST.T01
- INVAR | SPECIFICATION.md:3525-3527 | "a test starting a background task must keep an explicit reference and cancel it in its own `finally`" | Test-discipline rule, convention only. | area: TEST | -
- ASSUME | SPECIFICATION.md:3536-3539 | "measured: ~20 pieces regressed a fixed workload +53% versus 5 pieces" | Single dated-less measurement behind the rule "keep piece count bounded to a small, fixed number of sections". | area: PERF | related: REST.S06
- INVAR | SPECIFICATION.md:3538-3539 | "keep piece count bounded to a small, fixed number of sections" | Convention for streamed responses, no mechanical cap named. | area: REST | -
- PLATFORM | SPECIFICATION.md:3540-3541 | "`asyncio.TimeoutError` is a plain `Exception`, not `OSError` — catch it separately" | Exception-hierarchy fact. | area: PLAT | related: PLAT.T01
- PLATFORM | SPECIFICATION.md:3543-3548 | "`gc.threshold()`: no-arg call returns the current threshold (or `-1` if disabled ...); called with an argument ... always returns `None`" | GC API semantics the (e)/(f) test stages depend on. | area: PLAT | -
- LIMIT | SPECIFICATION.md:3550-3553 | "`scripts/build_firmware.py`'s type-checking strip removes every comment ... an on-device traceback's line numbers won't match checked-in `src/`" | Shipped code differs from reviewed/tested text; tracebacks need re-derivation. | area: SCR | related: SCR.T10
- LIMIT | SPECIFICATION.md:3555-3558 | "`asyncio.run()`'s `KeyboardInterrupt` handling has a real gap ... its own `try`/`finally` never runs" | Upstream asyncio gap; twin `__main__` blocks compensate with an outer synchronous cleanup. | area: TWIN | -
- WORKAROUND | SPECIFICATION.md:3557-3558 | "`digital_twin/`'s `__main__` blocks re-run cleanup from plain synchronous code in an outer `except KeyboardInterrupt:`" | Workaround for the asyncio.run SIGINT gap; removal trigger none stated. | area: TWIN | -
- PLATFORM | SPECIFICATION.md:3560-3562 | "MicroPython's `json.loads()` is not a JSON validator: `extmod/modjson.c`'s tokenizer skips `,` and `:`" | Accepts malformed JSON; tests of emitted JSON must use `tests/_strict_json.py`. | area: PLAT | related: XCUT.T23
- INVAR | SPECIFICATION.md:3561-3562 | "a test of emitted JSON checks it with `tests/_strict_json.py`" | Test convention; nothing named enforces every emitted-JSON test uses it. | area: TEST | -
- PLATFORM | SPECIFICATION.md:3564-3574 | "`json.dumps()` is not a JSON serializer either — it never raises (measured against the pinned interpreter, 2026-09-24)" | Emits bare `nan`/`inf`, `<object>`; rp2 overflows to inf at ~3.4e38; measured on the Unix port. | area: PLAT | covered-by: XCUT.T23
- INVAR | SPECIFICATION.md:3568-3570 | "a value's shape is the caller's obligation, which is why `_write_guarded()` needing `json.dumps()` inside its own `try` is moot (I.3)" | Serialization safety rests on every caller, not the response layer. | area: REST | related: REST.T11
- ASSUME | SPECIFICATION.md:3575-3581 | "**Every measurement source is gated at the driver, not in the response layer** (audited 2026-09-24)" | Dated audit claim listing BMP3xx, ISL29125, SGP40, math_helpers, `ema_step()`, SCD30; the plan says "Only SCD30 checks `isfinite`". | area: XCUT | covered-by: XCUT.T23
- INVAR | SPECIFICATION.md:3580-3581 | "A new source decoding floats or computing without a range gate needs the same" | Convention for new drivers; no test named. | area: SENS | related: XCUT.T23
- MIRROR | SPECIFICATION.md:3583-3588 | "Always check current MicroPython/Microdot documentation ... Repeat every time `versions.toml`'s ref moves" | Duplicates CLAUDE.md "Platform target" standing practices (two homes for one rule) (low). | area: DOC | related: DOC.T06

## SPECIFICATION.md Part F.2 — Blocking calls / timeout-wrapping
- SETTLED | SPECIFICATION.md:3592-3594 | "For a genuinely wedged I2C bus/sensor, the hardware watchdog is the accepted backstop ... Settled." | Do-not-reopen: no I2C-level timeout mechanism. | area: BUS | related: DOC.T14
- PLATFORM | SPECIFICATION.md:3594-3597 | "`socket.getaddrinfo()` belongs in this same bucket ... (confirmed against real MicroPython issue-tracker reports). Moot for DNS" | Can't be timeout-wrapped; "moot" only for the project's own DNS — the plan notes `getaddrinfo` is still reached inside `asyncio.start_server`. | area: PLAT | related: PLAT.T04
- TODO | SPECIFICATION.md:3597-3598 | "Calls that genuinely *can* be timeout-wrapped (FRAM SPI, `asy_udp_socket.py`'s `select.poll`-driven `ready()`) should standardize on one mechanism." | Standing, undated to-do; no owner or tracking item named. | area: XCUT | -
- SETTLED | SPECIFICATION.md:3600-3601 | "Don't wrap every `asyncio` primitive call in `try`/`except` against a theoretical `MemoryError`" | Do-not-reopen; narrow exception "for a concrete, non-hypothetical threat". | area: MEM | related: DOC.T14
- LIMIT | SPECIFICATION.md:3603-3609 | "doesn't reconstruct the underlying `machine.I2C` peripheral (only a full reboot does that)" | Task respawn recovers a sensor, not a wedged bus; bus faults rely on `task_errors` escalating to watchdog starvation. | area: BUS | related: XCUT.T02
- ASSUME | SPECIFICATION.md:3607-3609 | "`start_and_check_tasks()`'s `task_errors` counter escalates repeated respawn failures to watchdog starvation" | Recovery claim for a wedged bus depends on this escalation path actually starving the WDT (not verified here). | area: CORE | related: XCUT.T02, XCUT.S01
- SETTLED | SPECIFICATION.md:3611-3617 | "**Decided: investigated, no `src/` change** ... a physical power cycle/`hard_reset()` is the accepted recovery" | CYW43 `isconnected()` false positive accepted; `WifiUptime` inaccuracy called cosmetic. | area: NET | related: DOC.T14
- PLATFORM | SPECIFICATION.md:3612-3614 | "A well-documented, long-standing upstream MicroPython characteristic (open since v1.19.1/2022) ... no upstream fix" | Upstream status to re-check on a version bump. | area: PLAT | -
- ASSUME | SPECIFICATION.md:3618-3620 | "a sustained outage essentially never self-resolves within 150s (5/5 trials ...); repeated brief flapping self-heals reliably instead (3/3 trials, ~30s)" | Small-sample bench measurements that the residual-window argument below reuses. | area: NET | related: HW.T16
- PLATFORM | SPECIFICATION.md:3621-3622 | "`network.STAT_GOT_IP` is not STA-only (an AP interface reports it too) — `_run_hotspot_mode()`'s `status != STAT_GOT_IP` branch is only true on the first tick" | CYW43/port fact that makes a code branch nearly dead. | area: NET | related: NET.S07
- RISK | SPECIFICATION.md:3624-3644 | "one narrow, accepted residual window (WP5, 2026-09-16) ... a power loss landing in that same brief window loses the just-accepted config change silently" | Accepted residual risk of the deferred flush. | area: CORE | related: CORE.T02, XCUT.T10
- ASSUME | SPECIFICATION.md:3635-3637 | "In practice this window is a single scheduler tick (microseconds to low milliseconds)" | Unmeasured estimate; the deferred flush task can queue behind other work. | area: CORE | related: CORE.T02
- INVAR | SPECIFICATION.md:3625-3626 | "Every real flash write is still *triggered* only through the REST PUT path — nothing else ever calls `ConfigManager.write_config()`" | Convention-only invariant the watchdog/WiFi backstop safety relies on. | area: CORE | related: CORE.T02
- PLATFORM | SPECIFICATION.md:3629-3631 | "the RP2040 flash write disables interrupts port-wide for its duration, and doing it inline was resetting the very HTTP connection" | rp2 flash-write IRQ-off fact behind the deferred flush. | area: PLAT | related: PLAT.T12
- ASSUME | SPECIFICATION.md:3641-3642 | "never corrupts anything: the next boot's `setup()` repairs whatever the interrupted write left, C.7.3" | littlefs/`setup()` repair claim under power loss. | area: CORE | related: XCUT.T10
- DRIFT | SPECIFICATION.md:3632-3635 vs CLAUDE.md "Hard rules" (CYW43 bullet) | "the older, stronger claim — \"a device whose API is unreachable structurally cannot have a flash write in flight\" — is no longer exactly true" | CLAUDE.md still states "structurally cannot have a write in flight" as confirmed. | area: DOC | related: DOC.T10

## SPECIFICATION.md Part F.3 — Long-blocking operations
- INVAR | SPECIFICATION.md:3648-3650 | "Any new code that blocks the event loop for a noticeable time must not do so while timing-sensitive work like the Neopixel animation needs to run" | Design principle, no mechanical check; "noticeable" undefined. | area: PERF | related: PERF.T08
- SETTLED | SPECIFICATION.md:3650-3653 | "The `get_long_block_lock()` shared-lock mechanism has been retired ... not a resurrection of the old lock" | Do-not-resurrect marker. | area: XCUT | -

## SPECIFICATION.md Part F.4 — Vendor-derived code
- SETTLED | SPECIFICATION.md:3657-3658 | "Adafruit-derived driver code is fair game to restructure/rewrite (keeping attribution)" | Policy (dup of CLAUDE.md hard rule). | area: LIC | related: LIC.T01
- SETTLED | SPECIFICATION.md:3658-3662 | "Sensirion-derived reference-algorithm ports stay literal ... a stylistic rewrite is not" | Opposite policy for `voc_algorithm.py`. | area: ALGO | related: ALGO.T02
- MIRROR | SPECIFICATION.md:3659-3661 | "internal naming traces the original C source 1:1 so it stays diffable against Sensirion's own reference" | `src/voc_algorithm.py` ↔ Sensirion C reference. | area: ALGO | covered-by: ALGO.T02

## SPECIFICATION.md Part F.5 — MicroPython 1.29 delta (intro)
- ASSUME | SPECIFICATION.md:3669-3671 | "The pin is field-proven on the dev bench (2026-09-11) ... flash tier (25 passed), bench tier (85 passed) and mid soak tier (4 passed)" | Dated suite counts backing the 1.29 pin; will drift as tiers grow. | area: PLAT | covered-by: DOC.S17
- OPENQ | SPECIFICATION.md:3672 | "Deployed units stay on 1.26 regardless (BACKLOG open question 3)" | Field migration to 1.29 is an open question held in BACKLOG. | area: PAR | related: PAR.T11, PAR.T14
- LIMIT | SPECIFICATION.md:3673-3676 | "inducing a genuine RX overrun is not reachable from Python, so its *consequence* is pinned instead (`device_scripts/fram_busy_status_lockout.py`)" | F.5.2's EIO path is never exercised on silicon, only its downstream consequence. | area: HW | related: PLAT.T03
- DRIFT | SPECIFICATION.md:3664 vs 3852-4049 | "## F.5 MicroPython 1.29 delta (audited 2026-09-10 ...)" | F.5.7-F.5.9 are standing UART runtime facts CLAUDE.md hard rules depend on, filed under a version-delta heading. | area: DOC | covered-by: DOC.S02

## SPECIFICATION.md Part F.5.1 — I2C/SPI deinit no-ops
- PLATFORM | SPECIFICATION.md:3680-3685 | "**Both are no-ops on this port** ... rp2's `machine_i2c_p`/`machine_spi_p` ... never set that slot" | rp2 `deinit()` of I2C/SPI does nothing; peripheral and pin functions stay. | area: PLAT | covered-by: PLAT.T03
- PLATFORM | SPECIFICATION.md:3689-3694 | "`machine.I2C(id)`/`machine.SPI(id)` return a **static per-bus singleton** ... nothing is reclaimable on a `deinit()`" | No way to release an rp2 bus from Python; re-construction reconfigures the shared object. | area: PLAT | related: BUS.T10
- PLATFORM | SPECIFICATION.md:3695-3699 | "`machine.I2C.deinit()` did not exist at all before 1.29 ... a hard **1.29 floor** on its `deinit()` path" | `asy_i2c_driver.py` raises `AttributeError` on 1.28/1.26 via `deinit()`/re-`init()`; refactor code is not 1.26-compatible there. | area: BUS | related: PLAT.T03
- PLATFORM | SPECIFICATION.md:3701-3703 | "`machine.UART.deinit()`, `machine.Timer.deinit()` and `network.WLAN.deinit()` are **real** on rp2" | Which deinits actually release hardware. | area: PLAT | covered-by: PLAT.T03
- MIRROR | SPECIFICATION.md:3705-3707 | "`tests/machine.py` and `digital_twin/machine.py` model the no-op faithfully" | Fake↔real obligation in two fakes for I2C/SPI `deinit()`. | area: TEST | related: TEST.T19, TEST.T05
- LIMIT | SPECIFICATION.md:3706-3708 | "One deliberate divergence stays: both fakes hand back a **fresh object** per construction rather than a singleton" | Deliberate fake fidelity gap. | area: TWIN | related: TEST.T05
- ASSUME | SPECIFICATION.md:3708 | "Nothing in `src/` observes bus identity." | The singleton divergence is safe only while this holds; the plan records a per-bus singleton reconfigured by a later construction (`HW.S18`). | area: BUS | related: BUS.T10

## SPECIFICATION.md Part F.5.2 — rp2 SPI RX-overrun EIO
- PLATFORM | SPECIFICATION.md:3712-3714 | "`machine_spi_transfer()` gained an RX-overrun check (upstream #18471) ... `mp_raise_OSError(MP_EIO)`" | New 1.29 raise site on SPI reads. | area: PLAT | covered-by: PLAT.T03
- PLATFORM | SPECIFICATION.md:3724-3727 | "Write-only transfers can still never raise ... Only transfers of ≥ 32 bytes are affected — `dma_min_size_threshold` is 32" | Precise bounds of the fault; version-specific constants. | area: PLAT | covered-by: PLAT.T03
- MIRROR | SPECIFICATION.md:3716-3719 | "modeled at the bus level in `tests/machine.py`'s SPI fake and in `digital_twin/machine.py`'s (`rx_overrun` ... `rx_overrun_remaining` ... `inject_fault()`" | Two fakes must reproduce the ≥32-byte, read-only condition. | area: TWIN | related: TWIN.T05
- LIMIT | SPECIFICATION.md:3719-3722 | "The twin's chip-level `_fram_chip.py` `FaultInjector` ... cannot express the size threshold below, so a 1-byte status-register read would raise there when real hardware could not" | Twin fault injector over-approximates this fault. | area: TWIN | related: TWIN.T05
- INVAR | SPECIFICATION.md:3729-3733 | "It propagates uncaught out of `get_values()`, matching `asy_i2c_driver.py`'s \"a real `OSError` always propagates\" contract" | Bus-wrapper contract: no swallowing of real OSError at the bus layer. | area: BUS | related: BUS.T01
- SETTLED | SPECIFICATION.md:3741 | "So no retry is added (owner decision, 2026-09-24): the dual-copy layer already covers the read path." | Do-not-add-retry marker for SPI EIO on FRAM reads. | area: STOR | related: STOR.T10
- ASSUME | SPECIFICATION.md:3737-3740 | "a single transient overrun costs nothing at all ... Only an overrun hitting both copies degrades the read to `None`" | Recovery claim shown by mock/twin live-path tests, not on silicon. | area: STOR | related: STOR.T01
- SETTLED | SPECIFICATION.md:3743-3746 | "the chunk marked busy and unreadable until rewritten, which is **intended behavior, not a defect**" | A read-interrupted chunk is deliberately locked out (destructive-readout part). | area: STOR | related: STOR.T10
- DRIFT | SPECIFICATION.md:3735-3736 | "an earlier draft of this section that said it did was wrong" | Historic-path narrative in a current-state doc (low). | area: DOC | related: DOC.T05

## SPECIFICATION.md Part F.5.3 — Free wins in the 1.29 build
- PLATFORM | SPECIFICATION.md:3750-3756 | "The interpreter core now genuinely runs from SRAM ... Cost ... **12,918 B** of RAM no longer available as Python GC heap" | Build-layout fact tied to 1.29's linker rule; affects every Part I budget. | area: PLAT | related: MEM.T01
- INVAR | SPECIFICATION.md:3756-3758 | "the *benefit* ... has never been timed on this bench, and must not be quoted as a measured speedup" | Documentation discipline; claim unmeasured. | area: PERF | -
- ASSUME | SPECIFICATION.md:3759-3765 | "`RAM: 66,792 B / 256 KB (25.48%)` ... leaves **130,224 B free with a 115,536 B largest obtainable single block** ... a largest known single allocation of ~5.7 KB ... that is ample" | Single dated measurement (2026-09-11, dev board); "largest known allocation" is an unverified inventory claim. | area: MEM | related: HW.T16, MEM.T06
- SETTLED | SPECIFICATION.md:3768-3774 | "**That test's thresholds changed on 2026-09-19**: the owner retired its 100,000 B free / 80,000 B contiguous floors" | Owner decision; now survivor volume ≤ 100,000 B, contiguity ≥ 32,768 B, nothing placed/sitting in top 16,384 B (`tests_hardware/flash/test_memory_stress.py`). | area: HW | related: HW.T16
- DRIFT | SPECIFICATION.md:3774 | "`HEAP_FRAGMENTATION_MEASUREMENTS.md` §M2.5 has the method (archive §7G the derivation)" | "archive §" citation resolves only against the git archive commit. | area: DOC | covered-by: DOC.S04
- SETTLED | SPECIFICATION.md:3774-3777 | "measuring a loaded floor at 1.29 would need `mem_free` exposed over REST, which is deliberately not done" | Deliberate gap: no 1.29 loaded-heap floor exists; 1.28's 91,312 B is not comparable. | area: MEM | -
- DRIFT | SPECIFICATION.md:3778-3780 | "`-fno-math-errno` is now on ... so `math.sqrt` compiles to the hardware instruction" | RP2040 is a Cortex-M0+ with no FPU/sqrt instruction; "hardware instruction" is doubtful (low, not investigated). | area: PLAT | related: PLAT.T08

## SPECIFICATION.md Part F.5.4 — machine.mem_backup()
- PLATFORM | SPECIFICATION.md:3784-3789 | "**28 bytes** across two regions ... **Survives a WDT reset, `machine.reset()` and a deepsleep wake; lost on power-off.**" | rp2 watchdog-scratch facts, enabled by default in 1.29. | area: PLAT | covered-by: PLAT.T03
- SETTLED | SPECIFICATION.md:3793-3797 | "**Deliberately not adopted** (project owner, 2026-09-11) ... deliberate, temporary instrumentation, never normal-path code" | Owner decision; the plan's PLAT.T03 lists "`mem_backup()` adoption (F.5.4)" as a topic — must be triaged as settled. | area: PLAT | related: PLAT.T03, XCUT.S10

## SPECIFICATION.md Part F.5.5 — Stub defects repaired at install
- WORKAROUND | SPECIFICATION.md:3801-3812 | "`stdlib/_asyncio.pyi` privatised `Future` to `_Future` and `stdlib/asyncio/futures.pyi` ... was dropped from the wheel" | Stub repair in `scripts/typecheck.sh`; removal trigger: guarded, no-ops "once upstream re-ships". | area: SCR | covered-by: PLAT.T05
- WORKAROUND | SPECIFICATION.md:3813-3816 | "**`NotImplemented` is commented out** of `stdlib/builtins.pyi`" | Second stub repair; same removal trigger. | area: SCR | covered-by: PLAT.T05
- ASSUME | SPECIFICATION.md:3802-3803 | "accounted for **every one of the 26 findings** the version bump surfaced" | Dated count tied to stub `1.29.0.post1/.post2`. | area: PLAT | related: DOC.T08
- SETTLED | SPECIFICATION.md:3818-3821 | "Repairing the stubs is deliberate, and preferred over `type: ignore` comments in `src/`/`digital_twin/`" | Do-not-replace-with-ignores rule (dup of CLAUDE.md). | area: SCR | related: DOC.T14
- SUPPRESS | SPECIFICATION.md:3821-3824 (site src/asy_udp_socket.py:177) | "The one place a `type: ignore` *is* right is `asy_udp_socket.py`'s `recvfrom()`" | `# type: ignore[return-value]` at src/asy_udp_socket.py:177 for AF_INET-only narrowing; the same file also carries two `type: ignore[unreachable]` (:48, :136) the doc does not mention. | area: NET | -

## SPECIFICATION.md Part F.5.6 — Smaller 1.29 facts / non-events
- PLATFORM | SPECIFICATION.md:3828-3831 | "**`X: int = const(...)` now folds.** ... `\"_A\" in globals()` `True` on 1.28, `False` on 1.29" | Parser behaviour change; fielded 1.26 still has the footgun. | area: PLAT | related: PLAT.T02
- DRIFT | SPECIFICATION.md:3832 | "This project's 21 `const()`-using files are all unannotated." | `grep -lE '=\s*const\(' src/*.py` finds 25 files at 2a88cc8 (count stale, low; scope of "project" unstated). | area: DOC | related: DOC.T08
- ASSUME | SPECIFICATION.md:3833 | "the one `to_bytes` call in `src/` is always non-negative" | Single-site claim (src/asy_i2c_driver.py:141). | area: BUS | -
- PLATFORM | SPECIFICATION.md:3834-3837 | "`MICROPY_C_HEAP_SIZE` is now settable ... mpy-cross gained `-X no-source-lines` ... Not worth it at current flash headroom" | Unused knobs; the second is a decision resting on current flash headroom. | area: TOOL | -
- PLATFORM | SPECIFICATION.md:3838-3840 | "**`extmod/asyncio/` is byte-identical between the two tags** ... no timeout/cancellation support added to `socket.getaddrinfo()`" | Ruled-out item for the next bump. | area: PLAT | covered-by: PLAT.T06
- PLATFORM | SPECIFICATION.md:3841-3843 | "**Zero commits** to `py/profile.c`, `py/modsys.c`, `extmod/modselect.c`, `shared/timeutils/` ... the E.3 `select.poll()` GH-Actions hang cause and the `TZ=UTC` Unix-port fact both stand" | Non-events that keep two test-rig facts valid. | area: PLAT | covered-by: PLAT.T06
- PLATFORM | SPECIFICATION.md:3844-3848 | "I2C `WRITE1` transfer fix is behind `MICROPY_PY_MACHINE_I2C_TRANSFER_WRITE1`, which rp2 leaves at 0 ... DHCP's new `send_router` ... the captive portal is unaffected ... `gc.mem_free()` ... still call the slow `gc_info()`" | Several ruled-out 1.29 changes; "captive portal is unaffected" is an inference. | area: PLAT | covered-by: PLAT.T06
- PLATFORM | SPECIFICATION.md:3847-3848 | "The RP2350 watchdog ~16 s fix is RP2350-only — the 8388 ms cap in F.1 stands." | Silicon-specific. | area: PLAT | covered-by: PLAT.T06
- PLATFORM | SPECIFICATION.md:3849-3850 | "`SOCK_RAW` is now default-on and present in the built firmware. Noted only" | Unused capability; F.2 settles the reachability-probe question. | area: PLAT | covered-by: PLAT.T06

## SPECIFICATION.md Part F.5.7 — UART.deinit() RX buffer unrooted
- PLATFORM | SPECIFICATION.md:3858-3867 | "`mp_machine_uart_deinit()` clears `MP_STATE_PORT(rp2_uart_rx_buffer[id])` ... the UART IRQ handler resumes writing into memory the collector is free to hand out" | Upstream heap-corruption hazard on `deinit()`+same-size `init()` (rp2, 1.29.0 source). | area: PLAT | related: PLAT.T03
- INVAR | SPECIFICATION.md:3869-3875 | "`asy_uart_driver.UART.init()` therefore calls `machine.UART(...)` rather than `self._uart.init(...)`, and that choice is load-bearing" | Must-not-simplify rule; guarded only by a comment (`src/asy_uart_driver.py:199-207`) and the hardware injector `tests_hardware/device_scripts/uart_crossover_recovery.py`, no unit test named. | area: UART | related: UART.T09

## SPECIFICATION.md Part F.5.8 — UART read() blocks the loop
- PLATFORM | SPECIFICATION.md:3882-3888 | "`mp_machine_uart_read()` loops once per requested byte ... `mp_event_handle_nowait()` ... **never yields to asyncio** ... `mp_machine_uart_ioctl()` reports `POLLIN` as soon as the FIFO holds *one* byte" | rp2 1.29.0 UART read semantics behind the never-block rule; `timeout_char=1` is this project's value. | area: PLAT | covered-by: BUS.T05
- SETTLED | SPECIFICATION.md:3898-3901 | "owner direction, 2026-09-11: they may time out and handle it, but may never block synchronously, not even in a wait state" | Owner rule for `asy_uart_driver.py`/`asy_uart_comm.py` (dup of CLAUDE.md hard rule). | area: UART | covered-by: BUS.T05
- ASSUME | SPECIFICATION.md:3890-3897 | "`readinto(buf, 53)` returned 53 ... 4195 us ... 4370-4405 us" | Bench measurement (5 trials) motivating the clamp. | area: PERF | related: HW.T16
- INVAR | SPECIFICATION.md:3905-3915 | "`asy_uart_driver.UART._buffered()` is that clamp, and **every** read in the module goes through it ... `readline()` has no count to clamp and gates on `any()` instead" | Every read must clamp to `any()`; the plan records `readline()`/`readline_until_complete()` calling `machine.UART.readline()` without the clamp (`BUS.S06`). | area: BUS | related: BUS.S06
- ASSUME | SPECIFICATION.md:3914-3915 | "The docs' lower-bound wording (\"may return 1 even if there is more than one character available\") costs nothing here: under-reporting only ever means another round" | Relies on documented `any()` semantics. | area: PLAT | related: PLAT.T03
- INVAR | SPECIFICATION.md:3916-3926 | "the yield belongs there and nowhere else — `await asyncio.sleep_ms(0)` immediately before it returns `True` ... **no path through this driver reaches a read without having just yielded.**" | Single-point yield guarantee in `ready()`; `_read_delimited()` is the one loop that bypasses it, yielding every `_DELIMITED_YIELD_BYTES` (16). | area: BUS | related: BUS.S05
- INVAR | SPECIFICATION.md:3928-3929 | "A zero-length round additionally falls back to `sleep_ms(poll_wait_ms)`, so the retry can never become an unyielding spin" | Guard against `any()`/`POLLIN` disagreement. | area: BUS | covered-by: BUS.T05
- ASSUME | SPECIFICATION.md:3937-3953 | "clamped **278 us** ... Re-measured on the dev bench (2026-09-12) ... clamped **137 us** ... scheduler noise floor ... 400-900us ... 3.1ms to 6.3ms" | Dated bench figures; the doc itself notes a loop-latency probe cannot distinguish idle from blocked. | area: PERF | related: HW.T16, PERF.T08
- LIMIT | SPECIFICATION.md:3955-3959 | "UART fakes return `min(nbytes, len(rx_queue))` and never wait — they model a non-blocking read the real peripheral does not provide" | Fake fidelity gap; the defect was invisible below the bench tier. | area: TEST | related: TEST.T19
- MIRROR | SPECIFICATION.md:3960-3965 | "`UART.would_have_blocked_bytes` ... the two models are held to identical counting by `tests/_uart_link_contract.py`" | `tests/machine.py` ↔ `digital_twin/machine.py` stall counting, enforced by the shared contract. | area: TEST | related: TEST.T05
- ASSUME | SPECIFICATION.md:3967-3973 | "**All seven read paths are guarded, and that was established by breaking each one.** ... (2026-09-12) initially failed a named test for only four of the seven" | Dated mutation sweep; the plan's BUS.S06 contests two of the seven (readline paths). | area: BUS | related: BUS.S06, TEST.T02
- SETTLED | SPECIFICATION.md:3976-3982 | "**This does not generalise to `asy_i2c_driver.py`/`asy_spi_driver.py`, and must not be applied there.**" | Do-not-extend rule; I2C/SPI blocking stays under F.2's watchdog backstop. | area: BUS | related: DOC.T14
- PLATFORM | SPECIFICATION.md:3979-3981 | "`machine.I2C`/`machine.SPI` expose no equivalent ... an SCD30's 18-byte read *is* a ~1.8ms synchronous span by construction" | No partial-read API on rp2 I2C/SPI. | area: PLAT | related: BUS.T10
- ASSUME | SPECIFICATION.md:3984-3992 | "the longest non-yielding stretch is **2,849 us** ... a block operation holds the bus for **21,269 us** (measured on the dev board, HEAP_FRAGMENTATION_MEASUREMENTS.md archive §7D.6)" | Measurement cited to the git archive; "~90% interpreter overhead" is inferred from a ~300 us wire-time estimate. | area: PERF | related: PERF.T04, DOC.S04
- LIMIT | SPECIFICATION.md:3991-3995 | "No device TOML wires a second SPI device, so the 21 ms figure is a contract statement ... **That is structurally untestable rather than merely untested**" | SPI contention with FRAM is unobservable in every variant. | area: BUS | related: PERF.T04
- ASSUME | SPECIFICATION.md:3995-3998 | "**Per command (T.4, three runs, 2026-09-25)**: the 1-byte write took 2,833-3,395 us ... the whole block operation held the bus 18,089-23,148 us" | Newest dated figures; spread exceeds the single 21,269 us value quoted above. | area: PERF | related: HW.T16, PERF.T04
- OPENQ | SPECIFICATION.md:3998-3999 | "whether to yield between the envelopes of one write is open (`REAL_HARDWARE_TEST_QUEUE.md` T4)" | Open question pointing to a temporary queue row ID (spelled "T.4" two lines above). | area: STOR | related: PERF.T04, DOC.T03
- ASSUME | SPECIFICATION.md:4001-4005 | "`mp_machine_uart_write()` short-writes rather than waiting once `timeout` (0 here) elapses ... theoretical worst case is the ~1 ms it takes `ticks_ms()` to advance" | Write-path bound relies on `timeout=0` wiring and the port's short-write behaviour. | area: BUS | covered-by: BUS.T05

## SPECIFICATION.md Part F.5.9 — Idle ready() poll cost
- INVAR | SPECIFICATION.md:4011-4013 | "Part J.6 requires a single-digit `poll_wait_ms` precisely because poll granularity, not baud rate, dominates" | Deployment constraint on `poll_wait_ms`. | area: UART | related: UART.T10
- ASSUME | SPECIFICATION.md:4018-4021 | "**14 039 poll rounds** over a ~60 s run with one rate, against **839** with the idle rate" | Twin-soak count (single run). | area: PERF | related: PERF.T07
- ASSUME | SPECIFICATION.md:4023-4027 | "**Confirmed on real hardware (2026-09-12, dev bench.)** ... **1244 / 1233 poll rounds over 3 s at 2 ms against 60 / 60 at 50 ms**" | Dated bench measurement. | area: PERF | related: HW.T16, PERF.T07
- ASSUME | SPECIFICATION.md:4029-4035 | "an idle listener at 2 ms takes **~18-23 %** of that task's throughput ... and the inference is withdrawn" | Corroborating measurement only; notes heap-state-dependent spread (history narrative of a withdrawn inference). | area: PERF | related: PERF.T07, DOC.T05
- INVAR | SPECIFICATION.md:4037-4042 | "a wait with no deadline is by construction an idle listener — `_read_frame(device, -1)` inside `uart_listen()` is the only one this protocol issues" | Rate selection assumes every deadline-less wait is an idle listen; the plan notes `_write_all` also waits on `ready(POLLOUT)` with no deadline at the idle rate (`BUS.S05`). | area: UART | related: BUS.S05
- INVAR | SPECIFICATION.md:4044-4048 | "`poll_idle_ms` bounds how late the first byte of a frame is noticed, so it belongs well under the peer's own reply timeout ... opt-in per instance" | Partly enforced: `buildgen/validate.py:270-273` requires `timeout >= 2*poll_wait + poll_idle + gc_pause`; an instance without `poll_idle_ms` keeps the idle CPU cost. | area: UART | related: UART.T05, PERF.T07

## SPECIFICATION.md Part F.6 — SIGINT during gc_collect() wedges the Unix-port heap
- PLATFORM | SPECIFICATION.md:4052-4065 | "measured at the same ~5% rate on Unix ports built from both `v1.28.0` and `v1.29.0` ... `MemoryError: memory allocation failed, heap is locked`" | Unix-port-only upstream race (stuck `GC_COLLECT_FLAG`). | area: TWIN | related: TWIN.T07
- WORKAROUND | SPECIFICATION.md:4067-4076 | "**The recovery is `gc.collect()`, and only `gc.collect()`.** ... **`micropython.heap_unlock()` is not a substitute**" | `digital_twin/unix_port_gc_unwedge.py`; removal trigger: none — kept as defence in depth after the root-cause fix (4117-4121). | area: TWIN | related: TWIN.T07
- ASSUME | SPECIFICATION.md:4069-4070 | "Verified 3/3 on captured failures." | Small-sample verification. | area: TWIN | -
- ASSUME | SPECIFICATION.md:4075-4076 | "**`src/` needs nothing** — it has no `KeyboardInterrupt` shutdown path, and rp2 has no SIGINT" | Claim about src/ and about rp2 (USB-REPL Ctrl-C raises KeyboardInterrupt on rp2 too) (low). | area: PLAT | -
- DRIFT | SPECIFICATION.md:4084-4085 | "in violation of this Part's own stated rule (\"call it first ... before `flush_fram()`/`flush_scd30()`\")" | The quoted rule text no longer appears anywhere in F.6 (only the paraphrase in `digital_twin/unix_port_gc_unwedge.py:2`) (low). | area: DOC | related: DOC.T02
- DRIFT | SPECIFICATION.md:4087-4089 vs 4107-4116 | "gated on `MICROPY_ASYNC_KBD_INTR`, which the `standard` build variant used here has enabled" | Present-tense statement superseded by the amendment (override forces it to 0) in the same Part (history narrative). | area: DOC | related: DOC.T05
- ASSUME | SPECIFICATION.md:4095-4101 | "**This was not reproduced locally** ... offered as the one concrete, source-confirmed gap ... not as a confirmed root cause" | The `grkizi` `exit code -9` failure's cause is unconfirmed. | area: TWIN | -
- SETTLED | SPECIFICATION.md:4107-4121 | "**Amendment (2026-09-15): the root cause above is now closed** ... `unwedge_heap_after_interrupt()`'s three call sites are kept, deliberately, as defense in depth" | Do-not-remove marker; call sites `digital_twin/run_generic_integration.py:395, 435`, `digital_twin/launch.py:432`. | area: TWIN | related: TWIN.T07
- INVAR | SPECIFICATION.md:4113-4115 | "there is no other build path — every script that needs this binary goes through `toolchain/setup_toolchain.py setup`" | The root-cause closure holds only while no binary is built outside this path; the plan notes nothing proves `MICROPY_ASYNC_KBD_INTR == 0` in the built binary. | area: TOOL | related: TOOL.S07
- LIMIT | SPECIFICATION.md:4122-4126 | "they still prove the *shutdown paths themselves* stay correct, just not this specific recovery branch within them" | The unwedge branch is no longer exercised by any real interrupt. | area: TWIN | related: TWIN.T07

## SPECIFICATION.md Part G.0-G.1 — Shared primitive reuse rule
- INVAR | SPECIFICATION.md:4146-4153 | "Search G.2, then the wider codebase, for an existing primitive ... never reimplement even a version that looks locally simpler ... add it to G.2 in the same change" | Review-only discovery procedure. | area: XCUT | covered-by: XCUT.T15
- MIRROR | SPECIFICATION.md:4153-4155 | "A new feature with both a `src/` and `js/` side must encode the *identical* policy in the same change" | src↔js policy mirror, one change. | area: WEB | covered-by: WEB.T04

## SPECIFICATION.md Part G.2 — Known reusable primitives
- INVAR | SPECIFICATION.md:4159-4161 | "`type_or_range_error()`/`coerce_numeric()` ... Never hand-roll a cast/range comparison." | Convention-only validation primitive rule. | area: CORE | related: CORE.T03, XCUT.T15
- INVAR | SPECIFICATION.md:4162-4164 | "validate payload, `try/await` the callback, `except Exception` → `err_s(...)` → `\"Failed\"`" | Callback dispatch-guard shape; broad catch by design. | area: CORE | related: XCUT.T11
- INVAR | SPECIFICATION.md:4165-4166 | "`api_response.py`'s `make_response()` only, never a hand-built `{\"res\", \"code\", \"descr\", \"result\"}` dict" | Envelope rule; generated code and `js/` included? not stated. | area: REST | related: XCUT.T15
- INVAR | SPECIFICATION.md:4167-4171 | "`Lockable`/`LockedCounter`/`LockedFlag`/`LockedValue`, never a bare module-level variable plus an ad hoc lock ... `make_logger()`/`PrintLog`... never a bespoke print-based counter" | Convention-only rules. | area: CORE | related: CORE.T08
- INVAR | SPECIFICATION.md:4172-4180 | "Anything returning a `get_log()`/`get_error_counter()` result annotates it `\"ErrorLog\"` — never a re-spelled `dict[...]`" | Typing convention; historical counts "12 `src/` files and 7 test files", "three" ignores removed. | area: CORE | -
- INVAR | SPECIFICATION.md:4189-4192 | "**Every transfer method comes in pairs** — `write(data)`/`write_into(buf)` and `read()`/`read_into(buf)`" | Buffer-API shape rule; `AsyFramChunk` is the reference. | area: MEM | related: XCUT.T15
- INVAR | SPECIFICATION.md:4196-4198 | "**A failed allocation degrades to a `None` buffer, never an exception** ... every consumer's first act is `if buf is None: return False`" | Caller-discipline rule for every `LockableBuffer` consumer. | area: MEM | related: CORE.T08
- INVAR | SPECIFICATION.md:4206-4209 | "`_scratch` is the one shared by more than one caller ... sound only because each method fills and decodes it with no `await` in between" | Convention-only safety of the shared I2C scratch. | area: BUS | covered-by: BUS.T02
- INVAR | SPECIFICATION.md:4210-4214 | "Any route whose response scales with device configuration returns `await _stream_dict_response(result, self._chunk_bytes)` instead of `return result`" | Streaming rule (dup of CLAUDE.md); no test named that every scaling route complies. | area: REST | related: MEM.T03
- SETTLED | SPECIFICATION.md:4215-4218 | "never a new `async with` per transfer. I2C deliberately has no equivalent (BACKLOG's deferred list)" | Deliberate I2C/SPI asymmetry, deferred in BACKLOG. | area: BUS | covered-by: BUS.T07
- INVAR | SPECIFICATION.md:4224-4228 | "write order is build → CRC → encode → delimiter and read order the exact reverse ... A pass-through codec is the default and emits byte-for-byte what the driver emitted before" | Wire-order contract; a default change would alter emitted bytes (Class A territory). | area: UART | related: ALGO.S05
- MIRROR | SPECIFICATION.md:4229-4231 | "`js/mock-server.js` must match the real `src/` endpoint field for field, bound for bound; a `src/`-side policy change and its `js/` mirror are one change" | src↔js mock-server mirror. | area: WEB | covered-by: WEB.T04
- INVAR | SPECIFICATION.md:4232-4240 | "`instance_name()`, never a hand-rolled string-concatenation ... `_WIRING` ... never a getter/callback function ... every top-level module implements `get_error_sources()`/`get_loggers()`" | Three convention-only shape rules (C.14.1-C.14.3). | area: CORE | related: XCUT.T15
- INVAR | SPECIFICATION.md:4241-4247 | "Only ever called from a one-time or bounded-loop context, never a place that could keep feeding a genuinely hung system forever - that constraint lives with the caller" | `feed_watchdog()` caller-discipline rule; nothing mechanical. | area: CORE | related: XCUT.T03

## SPECIFICATION.md Part G.3 — Re-validation
- INVAR | SPECIFICATION.md:4251-4256 | "grep the whole tree for the *shape* of each G.2 primitive's problem ... A periodic, ongoing check, not a one-time pass" | Review-only recurring obligation; findings are flag-and-discuss. | area: XCUT | covered-by: XCUT.T15

## SPECIFICATION.md Part H.1 — Website purpose and constraints
- INVAR | SPECIFICATION.md:4265-4266 | "Every REST endpoint's functionality must be reachable somewhere in the GUI." | Standing product constraint; contradicted for `/system`'s `build` by L.7 (plan WEB.S20). | area: WEB | covered-by: WEB.S20
- ASSUME | SPECIFICATION.md:4266-4271 | "Standing constraints, all met: ... `render.js`/`nav.js` have zero device-specific branching ... stable on major browsers" | Blanket "all met" claim over several constraints (full REST coverage, no deps, browsers). | area: WEB | related: WEB.T09, WEB.T12
- SETTLED | SPECIFICATION.md:4273-4276 | "`html_raw/{general,arzi,dev,wozi}` is the legacy, still-deployed site ... This Part's website targets the refactored REST shape from the start — not a reskin." | Legacy site is reference; new site speaks only the new REST shape. | area: PAR | related: PAR.T10

## SPECIFICATION.md Part H.2 — Folder structure and module map
- INVAR | SPECIFICATION.md:4304-4306 | "`js/mock-server.js` is deliberately never staged at all — its `fetch` patching has no business near production" | Build rule; cross-checked by `tests_scripts/test_build_website_sh.py`. | area: WEB | related: WEB.T06
- INVAR | SPECIFICATION.md:4310-4312 | "the bundler strips local `import` lines but never `export` lines ... a split-out module (`field-format.js`) must never be *re-exported*" | Bundling constraint upheld by convention. | area: WEB | related: WEB.T06
- DRIFT | SPECIFICATION.md:4312-4315 | "Concatenation order is fixed so every file follows the local files it imports from ... `scripts/build_website.sh` re-checks that mechanically on every build" | Plan WEB.S14: no such check exists and the order is violated. | area: WEB | covered-by: WEB.S14
- LIMIT | SPECIFICATION.md:4315-4318 | "`tsc`'s JSDoc checking doesn't cover inline scripts (accepted — it's a thin bootstrap)" | Accepted type-check gap for `index.html`'s inline module. | area: WEB | -

## SPECIFICATION.md Part H.3 — Visual vs mechanics layering
- INVAR | SPECIFICATION.md:4323-4324 | "A purely visual/layout redesign must never require editing data-fetching, validation, submission, or poll-coordination code." | Standing layering requirement; review-only. | area: WEB | covered-by: WEB.T11
- INVAR | SPECIFICATION.md:4334-4340 | "controllers reach into a template only via `data-*` attributes/CSS classes ... Controllers only ever set the semantic `data-apply-status` value" | The `data-*` contract list is the redesign-stable interface; not mechanically checked. | area: WEB | covered-by: WEB.T11
- LIMIT | SPECIFICATION.md:4340-4342 | "**In-place refresh only ever touches a number/string field's caption** — a toggle/enum field's round-trip needs a genuine full remount" | Toggle/enum state is not refreshed by polling. | area: WEB | related: WEB.S01, WEB.S10

## SPECIFICATION.md Part H.4 — Architecture decisions table
- ASSUME | SPECIFICATION.md:4352 | "A realistic depth stays well under 20 entries, rides along in `/status`" | No pagination rests on this history-depth assumption. | area: WEB | -
- INVAR | SPECIFICATION.md:4353 | "Measurements and status/settings groups are never polled concurrently by design" | Single-flight rule. | area: WEB | related: WEB.T03
- MIRROR | SPECIFICATION.md:4354 | "`poll-manager.js`'s `DEFAULT_TIMEOUT_MS` deliberately **equals** `asy_webserver_service.py`'s `outer_cap_s` (15.0s)" | js↔src constant mirror, enforced by `tests_scripts/test_request_timeout_ceiling.py`; rationale contested by WEB.S06 (client clock starts before connect). | area: WEB | related: WEB.S06, GEN.T06
- RISK | SPECIFICATION.md:4354 | "The heaviest real request is `PUT /status {\"ResetErrors\": true}` ... this ceiling is a product constraint for its operators" | 15 s ceiling vs a sequential reset whose cost grows with readers (BACKLOG 24). | area: PERF | covered-by: PERF.T03
- SETTLED | SPECIFICATION.md:4355 | "No dedicated API-browser page" | Deliberate UI scope decision. | area: WEB | -
- ASSUME | SPECIFICATION.md:4356 | "Strict — visible error banner on mismatch" | Strictness claim for `validateDefinitions`; plan records it as shallow (WEB.S18/WEB.S23). | area: WEB | related: WEB.T05, WEB.S23
- INVAR | SPECIFICATION.md:4359 | "`textContent` only, never `innerHTML` | XSS-safe by construction." | Security rule with no lint enforcement. | area: SEC | covered-by: WEB.S17
- MIRROR | SPECIFICATION.md:4360 | "`type_or_range_error()`/`coerce_numeric()`, mirrored in `mock-server.js`" | src↔js validation mirror. | area: WEB | covered-by: WEB.T04
- INVAR | SPECIFICATION.md:4361 | "derive the set from the tags, never from this list alone" | The dispatch-only list in the doc is illustrative; tags are authoritative. | area: WEB | related: WEB.T01
- INVAR | SPECIFICATION.md:4361 | "a PUT to any *other* field is written straight through to the RP2040's flash filesystem ... why a dispatch-only PUT is deliberately outside [the `persistence_write` gate]" | The dispatch-only/persisting split is what the hardware wear gate depends on. | area: HW | related: HW.T01, HW.T13
- LIMIT | SPECIFICATION.md:4361 | "An enum field with no GET-matching state renders a blank placeholder by default." | UI degraded display for command-only enums. | area: WEB | -
- RISK | SPECIFICATION.md:4365 | "Known accepted gap | An empty string can't be set via this UI for any field ... Accepted." | Accepted UI gap (`PW` open-network sentinel unreachable). | area: WEB | -
- MIRROR | SPECIFICATION.md:4367-4370 | "`js/mock-server.js` mirrors every real backend quirk, not just the happy path: `PW` masked ... `ForceCalRef` always reports `400` ... `ContMeas`/`SGPResetVOC` never reported" | Mock↔backend quirk parity, covered by `tests_js/mock-server.test.js`; plan lists divergences. | area: WEB | related: WEB.S12

## SPECIFICATION.md Part H.5 — Definitions JSON schema
- INVAR | SPECIFICATION.md:4377-4380 | "`websiteVersion` ... build provenance only, not validated or rendered anywhere in the UI ... never conflate the two" | Two version fields with different meaning. | area: WEB | related: GEN.T14
- LIMIT | SPECIFICATION.md:4386-4393 | "`dispatch: true` ... is only consulted for `kind: \"toggle\"` and `kind: \"enum\"`" | Flag is inert on other kinds; behaviour relies on sparse-omission rules. | area: WEB | related: WEB.S02
- DRIFT | SPECIFICATION.md:4393-4396 | "An earlier version of this paragraph said ... (resolved 2026-09-18 by reading the one consumer, `js/render.js`)" | Historic narrative in a current-state doc (low). | area: DOC | related: DOC.T05
- DRIFT | SPECIFICATION.md:4399-4401 | "nearly identical field content (same three drivers); only `device.id`/`displayName` and I2C bus pairing differ" | `devices/dev.toml` wires ISL29125 too (`:103`) and `html/definitions/dev.json` carries ISL fields, so dev ≠ wozi's three drivers. | area: DOC | related: WEB.T05
- DRIFT | SPECIFICATION.md:4402-4408 | "`wozi`/`dev` keep their existing hand-written files unchanged (`tests_js/` reads those exact files as fixtures)" | Contradicts K.4 "never hand-maintained" / K.8 "regenerates automatically". | area: DOC | covered-by: DOC.S03
- TODO | SPECIFICATION.md:4408 | "see H.5.1's own \"Not yet built\" note for what's still open" | Open retirement of hand-written definitions. | area: WEB | covered-by: WEB.S13

## SPECIFICATION.md Part H.5.1 — Definitions-file autogeneration
- DRIFT | SPECIFICATION.md:4410 | "## H.5.1 Definitions-file autogeneration" | Heading level `##` for a subsection. | area: DOC | covered-by: DOC.S01
- LIMIT | SPECIFICATION.md:4416-4418 | "a best-effort, never-imported AST read of each driver's real `ConfigSchema`/`FieldSchema` constant (`buildgen/schema_ast.py`" | Schema inference is best-effort static evaluation. | area: GEN | related: GEN.S10
- INVAR | SPECIFICATION.md:4414-4416 | "built on `buildgen/tag_comments.py`'s shared near-miss-enforcing scanner exactly like `@requires` — never a second, separately-tested detector" | One scanner for every tag family. | area: GEN | related: GEN.T03
- INVAR | SPECIFICATION.md:4424-4428 | "`submitGroup=self` is a reserved sentinel ... used by scd30/sgp40/bmp3xx, the only drivers a device can carry more than one instance of" | Multi-instance set named in prose; ISL29125's status not stated (low). | area: GEN | related: GEN.T04
- LIMIT | SPECIFICATION.md:4430-4433 | "a quoted value may not contain a literal `\"` (no escaping), and every tag is a single physical line" | Deliberately minimal tag grammar. | area: GEN | related: GEN.T03
- INVAR | SPECIFICATION.md:4435-4444 | "`tests_hardware/website_identity.py` runs `build_model()` + `generate_definitions()` ... Nothing is hardcoded: a new `[[instance]]` is covered the day it is declared" | Hardware-tier check that the served page matches the generator. | area: HW | related: HW.T05
- MIRROR | SPECIFICATION.md:4453-4457 | "`validateDefinitions()` rejects a `path` on anything but a `kind=readonly` field ... `buildgen/web_tag.py` enforces the identical rule at generation time" | Python↔JS duplicate validation of `path`. | area: GEN | related: GEN.T15
- MIRROR | SPECIFICATION.md:4463-4466 | "bounded 0–100 ... checked at generation time in `buildgen/web_tag.py` and again in `js/definitions.js`'s `validateFieldHints()`" | `web_tag._MAX_DECIMALS` ↔ `validateFieldHints`. | area: GEN | covered-by: GEN.T15
- ASSUME | SPECIFICATION.md:4461-4462 | "`js/field-format.js`'s `formatFieldValue()` is the one place in the whole stack that rounds an emitted value (no driver in `src/` rounds anything)" | Unverified whole-stack claim. | area: WEB | -
- INVAR | SPECIFICATION.md:4469-4470 | "A schema-declared sentinel special value must have a matching tag `special:<value>=\"<meaning>\"` or the build fails loud" | Enforced by the generator. | area: GEN | related: GEN.T09
- MIRROR | SPECIFICATION.md:4479-4482 | "`_WARN_SIGNAL_WEB_CATALOG`, the same precedent `buildgen.codegen._KNOWN_SIGNALS` ... kept in sync by cross-reference/comment, not import" | Hand-mirrored catalog pair, comment-only sync. | area: GEN | covered-by: GEN.T06
- ASSUME | SPECIFICATION.md:4484-4486 | "**Correctness proof**: `generate_definitions()` ... reproduces the existing hand-written `wozi.json`/`dev.json` exactly (order-insensitive)" | "Exactly" is order-insensitive only; generated field order differs. | area: GEN | covered-by: WEB.S13
- TODO | SPECIFICATION.md:4490-4493 | "**Not yet built**: retiring the two hand-written `wozi.json`/`dev.json` files ... done as of Session 6" | Open item; "Session 6" is an undefined label. | area: WEB | related: WEB.S13, DOC.T09

## SPECIFICATION.md Part H.6 — Errcount and dispatch-only conventions
- INVAR | SPECIFICATION.md:4497-4501 | "plus each module's `CFGMGR_<name>` (except SCD30, NVM-backed) plus `WEBSERVER` ... **Keyed per logger instance, not per driver kind**" | Key-naming rule shared by firmware and website. | area: WEB | related: GEN.T06
- RISK | SPECIFICATION.md:4501-4504 | "Getting this wrong fails in both directions and neither is visible ... a row with no published source renders a permanent, reassuring `0` from `templates.js`'s own `?? {counter: 0}` fallback" | Silent failure mode of errcount wiring. | area: WEB | related: WEB.S09
- LIMIT | SPECIFICATION.md:4505-4506 | "a fixed `history_length`-long list, no per-entry timestamp — `type` only colors `num`" | Error history carries no timing. | area: CORE | related: XCUT.T24
- INVAR | SPECIFICATION.md:4508-4512 | "`lightCmdLED` (r/g/b/t, bounds matching legacy exactly, rejecting not clamping) ... a well-formed submission always reports `\"Valid\"`, including on an identical repeat (never `\"Unchanged\"`)" | Dispatch-only semantics; plan notes `lightCmdLED` yields "Failed" not "Invalid" for bad keys. | area: REST | related: REST.S10
- MIRROR | SPECIFICATION.md:4512-4513 | "`js/mock-server.js` mirrors this via dedicated dispatch functions — none ever persisted" | Mock dispatch mirror. | area: WEB | covered-by: WEB.T04
- RISK | SPECIFICATION.md:4513-4515 | "if a `SettingsGroup`'s post-write hook raises, every field that group attempted is reported `\"Failed\"` ... while the overall envelope still reports success" | Deliberate envelope-success-with-field-failure contract. | area: REST | related: XCUT.T11

## SPECIFICATION.md Part H.7 — Digital twin integration / connection ceiling
- LIMIT | SPECIFICATION.md:4519-4528 | "CI/local test hooks build the real production `wozi` website automatically ... `live-backend-put-matrix.test.js` extends this to every real writable field in `wozi.json`" | Browser/live tiers cover wozi only. | area: TEST | covered-by: TEST.S19, WEB.T12
- DRIFT | SPECIFICATION.md:4530, 4664 | "### The connection ceiling ..." / "### Cross-browser coverage" | Unnumbered subsections, cited elsewhere as "H.7". | area: DOC | covered-by: DOC.S01
- INVAR | SPECIFICATION.md:4535-4536 | "seven modules concatenated into one `js/app.js`, plain text concatenation, safe since none use default exports/dynamic imports/re-exports" | Bundling safety rests on a convention; module count "seven" is a count to re-check. | area: WEB | related: WEB.T06
- SETTLED | SPECIFICATION.md:4540-4544 | "**`max_connections` is `6`** (owner decision ...) ... `MEMP_NUM_TCP_PCB` is at least `max_connections + 3` ... anything less is a build error" | Owner decision; relation enforced by `check_lwip_ensemble()`'s `SPARE_TCP_PCBS`. | area: REST | related: REST.T06, PERF.T02
- PLATFORM | SPECIFICATION.md:4545-4549 | "`tcp_alloc()` reclaims TIME_WAIT, LAST_ACK and CLOSING pcbs ... a FIN_WAIT one only at a lower priority ... `extmod/modlwip.c` aborts a close still unfinished only after 10 s" | lwIP/modlwip version-specific behaviour. | area: PLAT | related: PLAT.T04
- ASSUME | SPECIFICATION.md:4550-4551 | "Every limit measured on silicon ran with these three spares; nothing leaner has been measured." | Spare count is empirical, not derived. | area: REST | related: HW.T16
- PLATFORM | SPECIFICATION.md:4557-4560 | "an arrival that finds it full is reset inside lwIP (`ERR_BUF`), where nothing in `src/` can see it" | Invisible refusal path. | area: PLAT | related: PLAT.T04
- INVAR | SPECIFICATION.md:4563-4568 | "`backlog` derives `max_connections + 1` ... buildgen refuses a `[device].backlog` below `max_connections` or above `max_connections + 1` ... `WebserverService` itself only clamps a lower value up" | Build-time enforced; runtime only clamps up. | area: REST | related: REST.T06
- ASSUME | SPECIFICATION.md:4570-4579 | "**6** | **0 of 2,255** (5 boots, E6′ among them) | **~21 %** ..." | Measured table cited to archive §7R; "E6′" undefined label. | area: PERF | related: HW.T16, DOC.S04, DOC.S16
- ASSUME | SPECIFICATION.md:4581-4585 | "the board is CPU-bound at ~2.2 requests/s ... each open connection ~7.5-8 KB of live heap at peak" | Capacity figures from archive §7R.4. | area: PERF | covered-by: PERF.T02
- PLATFORM | SPECIFICATION.md:4586-4590 | "A refusal is a FIN ~6 ms after connect, or an RST if the client's request bytes had already arrived (`modlwip.c` frees them unread ...)" | lwIP close semantics. | area: PLAT | related: PLAT.T04
- SETTLED | SPECIFICATION.md:4591-4596 | "back-to-back clients see ~70 % refused ... **It stays that way** (settled 2026-09-24)" | Slot held until close completes; do-not-release-earlier marker; pinned by unit and twin tests. | area: REST | related: REST.T06
- ASSUME | SPECIFICATION.md:4597-4598 | "`gc.threshold(32768)` does not move the limit ... A browser opens at most 6 connections per host and a page load here needs 2" | Measured/assumed; the browser figure is browser-dependent. | area: PERF | related: WEB.T16
- LIMIT | SPECIFICATION.md:4600-4605 | "The ordinary twin runs on the Unix port, which has **no lwIP at all** ... **cannot** validate a PCB ceiling ... an ad-hoc instrument, never a gate" | Twin fidelity gap for connection limits. | area: TWIN | covered-by: TWIN.T08
- INVAR | SPECIFICATION.md:4606-4609 | "every admitted connection must come back with a complete, correct, parseable response ... A test that only counts `200`s passes on a truncated body" | Test-oracle rule across tiers. | area: TEST | related: TEST.T01
- SETTLED | SPECIFICATION.md:4625-4627 | "HTTP keep-alive is deliberately not implemented ... persistent connections proved fragile when tried in application code" | Do-not-add keep-alive. | area: REST | related: REST.T12
- LIMIT | SPECIFICATION.md:4628-4629 | "`max_connections` only ever rejects a *new* arrival — never touches an already-open connection, reclaimed only by its own timeout" | No eviction of open connections. | area: REST | related: REST.T06

## SPECIFICATION.md Part H.7.1 — Connection lifetime and instruments
- ASSUME | SPECIFICATION.md:4633-4645 | "Measured on the dev bench, 2026-09-23 ... **5.12 / 5.14 / 5.16 s** ... **15.08 / 15.13 s** ... drain ... **0.71–0.84 s**" | Dated bench figures; "No connection can be held longer than ~15 s on this firmware". | area: REST | related: HW.T16, REST.T06
- INVAR | SPECIFICATION.md:4642-4644 | "released even when that close's own warning raises `MemoryError` on an exhausted heap, since a skipped release would refuse everyone until reboot" | Slot-release must survive MemoryError in `_serve()`'s `finally`. | area: REST | related: REST.T06
- WORKAROUND | SPECIFICATION.md:4646-4649 | "`extmod/modlwip.c` has freed the pcb but its state (6) still passes the write path's error check, so microdot's 400 would reach `tcp_write(NULL)` ... `_TimeoutStreamProxy` drops every write once a read of the pair raised `OSError`" | Workaround for an upstream modlwip defect; removal trigger none stated. | area: REST | related: REST.T06, PLAT.T04
- INVAR | SPECIFICATION.md:4653-4659 | "**A walk's per-connection dwell stays under `per_call_timeout_s`, and the whole walk under `outer_cap_s`**, or no ceiling is ever reached" | Instrument constraint; a violating instrument "fails silently, not loudly" (4634-4635). | area: HW | related: HW.T12

## SPECIFICATION.md Part H.7 — Cross-browser coverage
- LIMIT | SPECIFICATION.md:4666 | "Vitest's browser mode only automates Chromium-family browsers via Playwright." | Non-Chromium engines covered only by the narrow smoke script. | area: TEST | related: WEB.T12
- SETTLED | SPECIFICATION.md:4673-4676 | "Deliberately narrow scope (not a second exhaustive PUT matrix ...), and single-session" | Cross-browser smoke scope decision. | area: TEST | -
- INVAR | SPECIFICATION.md:4678-4679 | "CI always installs all three (a skip there is the bug to chase)" | CI must never skip a browser engine. | area: CI | related: CI.S06
- WORKAROUND | SPECIFICATION.md:4687-4692 | "Ubuntu's `firefox` package is a snap-only stub ... conda-forge, reached through a standalone `micromamba` binary" | Workaround for distro packaging and network policy; removal trigger none stated. | area: CI | related: CI.S06
- SETTLED | SPECIFICATION.md:4692-4694 | "That install is deliberately **unpinned** ... whatever conda-forge publishes today is acceptable" | Deliberate unpinned supply-chain input (Firefox, geckodriver, micromamba). | area: CI | covered-by: CI.S06

## SPECIFICATION.md Part H.8 — Web CI / tooling stack
- SETTLED | SPECIFICATION.md:4705 | "**`@vitest/coverage-v8`** (report-only, no threshold" | JS coverage never gates. | area: CI | related: CI.T11, CI.S12
- WORKAROUND | SPECIFICATION.md:4705-4710 | "writing to `htmlcov_js/` rather than its default `coverage/`, which Python imports as a namespace package ... `exclude: [\"**/*.json\"]` because the provider re-parses every file V8 reported as JavaScript" | Two tool-interaction workarounds; the JSON exclusion is pinned by `tests_scripts/test_js_coverage_excludes_json.py`; removal trigger none stated. | area: CI | -
- SETTLED | SPECIFICATION.md:4713-4718 | "**ESLint's rule set is curated, not `eslint:all`** ... pure style-preference bans (`no-bitwise`, `no-plusplus`, ...) left out" | Deliberate lint-scope decision (contrast ruff `select = ["ALL"]`). | area: CI | -
- DRIFT | SPECIFICATION.md:4718-4720 | "`js/poll-manager.js`'s \"Poll failed:\" is the poll loop's only failure diagnostic and is asserted by a test" | Plan: the `console.error("Poll failed:")` is dead (`fetchOnce` catches everything) and lives in `render.js`, not `poll-manager.js`. | area: WEB | covered-by: WEB.S11
- INVAR | SPECIFICATION.md:4722-4724 | "Complexity ceilings (`complexity` 41, `max-depth` 4, `max-nested-callbacks` 4) sit at the measured maximum ... and only ever ratchet down" | Ratchet-down rule is convention; values are dated measurements (mock-server dispatcher 41, `validateDefinitions` 37). | area: CI | -
- INVAR | SPECIFICATION.md:4725-4727 | "`scripts/build_website.sh` relies on it importing the literal `../js/app.js`" | The inline bootstrap's import path must never change. | area: WEB | related: WEB.T06
- SETTLED | SPECIFICATION.md:4729-4731 | "`dorny/paths-filter` gate job ... deliberately not a second workflow file with its own trigger-level filter" | CI structure decision. | area: CI | related: CI.T02, CI.S11
- SETTLED | SPECIFICATION.md:4738-4748 | "The workflow triggers on `push` to every branch as well as on `pull_request`, and that is not redundancy." | Do-not-narrow marker, born of the 2026-09-18 "128 commits went unverified" incident. | area: CI | related: CI.T09
- INVAR | SPECIFICATION.md:4748-4749 | "**When judging whether a branch is green, check that CI actually ran on its head commit**, not just that nothing is red." | Review-only practice rule. | area: CI | related: CI.T09

## SPECIFICATION.md Part H.8.1 — JSDoc typedef imports
- INVAR | SPECIFICATION.md:4755-4758 | "**Convention**: declare a narrow, structural local typedef instead of importing the real one" | Convention to keep Node-context type-check programs DOM-free. | area: WEB | -
- INVAR | SPECIFICATION.md:4758-4760 | "poll for the exact expected rendered text, never a fixed sleep" | JS test-timing rule, review-only. | area: TEST | related: TEST.T14

## SPECIFICATION.md Part I (intro)
- ASSUME | SPECIFICATION.md:4766-4770 | "Written up during the 2026-09-07 systematic memory-safety audit ... Everything else scanned was already correct." | Dated whole-`src/` audit conclusion; predates several modules. | area: MEM | covered-by: MEM.T01

## SPECIFICATION.md Part I.1 — MicroPython memory-management facts
- PLATFORM | SPECIFICATION.md:4774-4778 | "**The collector is mark-and-sweep, non-compacting** ... a 16-byte block on a 32-bit target" | GC design facts behind every contiguity rule. | area: PLAT | related: MEM.T06
- ASSUME | SPECIFICATION.md:4783-4785 | "every accumulation loop in `src/` either bounds total size or already guards the one failure that matters, `asy_uart_driver.py`" | Whole-`src/` claim from the 2026-09-07 scan. | area: MEM | related: MEM.T01, MEM.T04
- ASSUME | SPECIFICATION.md:4790-4793 | "A real `gc.collect()` pause is ~1ms typically, up to ~15-21ms measured on real target hardware under hammer load ... conclusively ruled out as a cause of any real watchdog reset" | Dated silicon measurement used to exclude GC from WDT post-mortems and in no-yield budgets. | area: PERF | related: PERF.T08, HW.T16
- PLATFORM | SPECIFICATION.md:4793-4796 | "**No async-generator-shaped alternative exists anywhere** ... every MicroPython PEP 525 discussion converges on the same \"not implemented\" status" | Upstream-status fact to re-check on a version bump. | area: PLAT | related: PLAT.T07
- RISK | SPECIFICATION.md:4799-4801 | "Pico W's CYW43 firmware genuinely reduces usable heap versus a plain Pico (roughly half the 264KB SRAM) — an accepted, unavoidable fact of this board choice" | Accepted board-level constraint. | area: MEM | -
- PLATFORM | SPECIFICATION.md:4809-4816 | "`gc_alloc()` takes `(size_t n_bytes, unsigned int alloc_flags)` and nothing else (`py/gc.c:891`) ... `MICROPY_GC_SPLIT_HEAP` is unavailable on this board: `ports/rp2/mpconfigport.h:100-101`" | Pinned-source line citations that move with the version. | area: PLAT | related: PLAT.T13
- SETTLED | SPECIFICATION.md:4811-4812 | "`gc.collect()`/`gc.threshold()`/`gc.disable()` as the only Python-visible knobs — all of which I.4 forbids as remedies" | Restates the no-GC-knob-as-fix rule. | area: MEM | related: DOC.T14
- SETTLED | SPECIFICATION.md:4828-4833 | "The C-level technique would need a fork of vendored MicroPython, which CLAUDE.md forbids; **the Python-level analogue needs no fork** — allocate the long-lived objects first" | Placement design principle; C.13's init/setup split is the mechanism. | area: MEM | related: MEM.T02
- INVAR | SPECIFICATION.md:4831-4833 | "why (f.1)'s two boot lists are the only places left where placement has to be managed explicitly" | Assumes all other long-lived allocations land in `__init__`; run-phase long-lived allocations would violate it. | area: MEM | covered-by: MEM.T02
- ASSUME | SPECIFICATION.md:4838-4840 | "**No free-heap target is published.** ... The 20-30 % free at peak that H.7 uses is general embedded practice." | H.7's `max_connections` target rests on a practice figure, not a requirement. | area: MEM | related: PERF.T02

## SPECIFICATION.md Part I.2 — Hotspot catalog
- ASSUME | SPECIFICATION.md:4851-4858 | "**Reviewed, found already safe (no change made)**: ... `captive_dns.py`'s `DNSQuery` (bounded by a single DNS datagram's structural limits) ... `asy_wifi_service.py` (no `network.WLAN.scan()` call anywhere)" | Dated per-file safety verdicts; plan seed shows `captive_dns` receiving `recvfrom(4096)` per datagram. | area: MEM | related: MEM.T01, NET.S10
- RISK | SPECIFICATION.md:4852-4853 | "`asy_uart_driver.py`'s accumulation loops (wrapped in `try/except MemoryError`, bounded or documented-unbounded-and-accepted)" | Accepted unbounded accumulation paths in the UART driver. | area: BUS | related: BUS.S06, MEM.T03
- INVAR | SPECIFICATION.md:4866-4869 | "safe only because each of these methods fills and decodes it with no `await` in between and no `Timer`/`Pin.irq` callback in this codebase touches I2C — both verified against the real code" | Shared-scratch safety invariant (verified 2026-09-18, not mechanically guarded). | area: BUS | covered-by: BUS.T02
- LIMIT | SPECIFICATION.md:4869-4874 | "A read larger than the scratch ... falls back to the allocating call ... **That fallback is structurally unexercised on this hardware**" | Dead-on-dev fallback kept deliberately; "BMP3XX's 21-byte calibration block is the largest" is a dated inventory claim. | area: BUS | related: BUS.T08
- SETTLED | SPECIFICATION.md:4878-4881 | "**`src/crc_checks.py` keeps its per-byte `await asyncio.sleep(0)`** (2026-09-18: \"pure wall clock time is not such an issue, don't touch\")" | Owner decision; ~5.8x wall-time cost accepted; 160 B per `_crc()` call. | area: ALGO | related: ALGO.T03, PERF.T04
- SETTLED | SPECIFICATION.md:4882-4886 | "**Each FRAM-backed logger's `PrintLogHistoryStore.setup()` stays first in its module's own `setup()`** ... (2026-09-21)" | Owner decision; cites undefined "measures A and B". | area: CORE | related: CORE.T05, DOC.S16

## SPECIFICATION.md Part I.3 — Bounded response assembly
- INVAR | SPECIFICATION.md:4890-4895 | "Every GET route whose response grows with device configuration ... writes its JSON through one `_PieceWriter` ... `chunk_bytes` ... default **256**, that also sets the static-file read size below, so the two bounds cannot drift apart" | One parameter bounds both paths; piece bound is in characters per plan REST.S06. | area: REST | covered-by: REST.T05
- INVAR | SPECIFICATION.md:4901-4903 | "The bytes are **identical** to what the routes emitted before ... pinned against MicroPython's own `json.dumps()` by `tests/test_asy_webserver_service.py`" | Byte-parity mirror `_PieceWriter.add_value()` ↔ `json.dumps()` (separators, non-string keys), test-enforced. | area: REST | related: REST.T05
- ASSUME | SPECIFICATION.md:4904-4909 | "that scales with module count (17 on real hardware, ~4.9 KB for one section ...). At 256 B `dev`'s `/status` is 29 pieces (11 at the old 1024 B); its wall-clock on silicon is `REAL_HARDWARE_TEST_QUEUE.md` row W3" | Dated counts; permanent doc cites a temporary queue row ID. | area: REST | related: DOC.T03, DOC.T08
- ASSUME | SPECIFICATION.md:4911-4920 | "with 1,024 B pieces the board served at most 4 concurrent requests without a `MemoryError` ... `/status` 320 B (1,024 B with the old cap), every other route and data source ≤ 256 B" | Measured need per path on the 32-bit twin (archive §7R.3/§7Q.10). | area: MEM | related: HW.T16, DOC.S04
- LIMIT | SPECIFICATION.md:4922-4933 | "the ceiling is the longest string any schema permits, which is `NTP_Host`'s 1,024 characters ... the long-value case is bounded by argument, not measured ... do not read \"≤ 256 B\" as covering a device whose user has typed a long server address" | Known over-cap piece (~1,026 B) on `/networking`/`/status`; would not fit at a limit of 7. | area: MEM | related: REST.S06, REST.T05
- SETTLED | SPECIFICATION.md:4927, 4931-4932 | "the bound is settled, BACKLOG's deferred list ... a shorter `NTP_Host` bound is the lever, and the owner settled it" | Owner decision keeping `NTP_Host` at 1,024. | area: NET | -
- ASSUME | SPECIFICATION.md:4925-4926 | "Only a string config value can be that scalar — `errcount` holds ints alone (`_shape_errcount_entry()`), and `history_length` bounds its list" | Premise of the over-cap analysis; non-ASCII SSID/hostname bytes not considered (REST.S06). | area: REST | related: REST.S06
- WORKAROUND | SPECIFICATION.md:4935-4944 | "`_serve_static()` now opens the file itself, passes it to `send_file(stream=...)`, sets that attribute on the one response to the same `chunk_bytes` (**256**) and adds `Content-Length`" | Wraps vendored microdot's 1,024 B `send_file_buffer_size` default without editing `ext/`; removal trigger none stated. | area: REST | related: REST.T07
- INVAR | SPECIFICATION.md:4944-4951 | "**A write-phase failure is never a success**: a response whose body can still fail after its status line goes out must carry its length ... `_TimeoutStreamProxy.awrite()` holds the block until its blank line and sends it as one write" | Framing invariant plus a workaround for microdot writing headers piecewise. | area: REST | related: REST.T06, REST.T12
- ASSUME | SPECIFICATION.md:4953-4955 | "**256, not smaller**: at 128 ... the measured ceiling does not move (archive §7Q), while the write count doubles" | Measurement cited to the git archive. | area: PERF | related: DOC.S04
- DRIFT | SPECIFICATION.md:4960-4962 | "since an 8MB Unix-port heap trivially absorbs a payload this small" | `scripts/test.sh:369` now runs `-X heapsize=16M` (CLAUDE.md: 8M → 32M → 16M) (low). | area: DOC | related: DOC.T08
- LIMIT | SPECIFICATION.md:4959-4963 | "added after confirming the original hammer tests would still pass even with a fix fully reverted" | Unix-port heap cannot reproduce contiguity failure; tests assert stream shape instead. | area: TEST | related: TEST.T01, TWIN.T06
- INVAR | SPECIFICATION.md:4971-4973 | "a `chunk_bytes` of 0 is clamped: microdot's body loop ends only on a short read, and `read(0)` never is one" | Guard against a microdot behaviour. | area: REST | related: REST.T05

## SPECIFICATION.md Part I.4 — Multi-stage memory-error scheme, (a)-(e)
- INVAR | SPECIFICATION.md:4977-4979 | "**Every module in `src/`, present and future, follows this ladder** for anything that can plausibly exhaust memory" | Standing design ladder; review-enforced (dup of CLAUDE.md). | area: MEM | related: MEM.T01
- SETTLED | SPECIFICATION.md:4982-4990 | "a caught `MemoryError`, even one that never crashes anything, is a design defect to fix at its source, not a handled case to accept" | Standing rule (a). | area: MEM | related: DOC.T14
- INVAR | SPECIFICATION.md:4990-4993 | "a caught failure produces a well-defined \"unavailable\"/`None`/`False` result, never an unguarded re-raise (`_write_guarded()`/`_write_errcount_entry()` substitute `{\"error\":\"unavailable\"}`" | Degrade contract (b); the UI renders it as "—" with no signal (WEB.S09). | area: MEM | related: WEB.S09
- ASSUME | SPECIFICATION.md:4995-4998 | "the `task_errors` counter escalates past repeated restarts to `reboot_system()`, at which point the loop stops feeding the watchdog" | Stage (d) claim; plan seeds show the supervisor's reboot branch `return`s and reboot timer behaviour. | area: CORE | related: XCUT.T02, XCUT.S11, XCUT.S03
- INVAR | SPECIFICATION.md:5000-5009 | "The whole suite — digital twin and real hardware alike ... must run to completion with `gc.threshold(-1)` ... with no nonstandard `gc` settings or added `gc.collect()` calls" | Stage (e) bar; the plan records `gc.collect()` props present in tests. | area: TEST | covered-by: TEST.S11, TEST.T03
- INVAR | SPECIFICATION.md:5010-5014 | "`scripts/test.sh` (added 2026-09-22, having been the gap) searches each test file's own captured output and fails the run ... checked on a passing file too" | Enforced gate; plan lists processes outside the four gates. | area: SCR | related: TEST.T18
- PLATFORM | SPECIFICATION.md:5016-5021 | "the interpreter's own `MemoryError` message is `\"memory allocation failed, allocating N bytes\"` (or `\", heap is locked\"`; both raised from `py/runtime.c:1692/1696`, and there is no third wording in the pinned source)" | Gate patterns depend on pinned-source wording and line numbers. | area: PLAT | related: TEST.T18
- PLATFORM | SPECIFICATION.md:5033-5036 | "rp2 resolves to `MICROPY_ERROR_REPORTING_NORMAL` (through `MICROPY_CONFIG_ROM_LEVEL_EXTRA_FEATURES`) — of the four reporting levels only `NONE` ... strips exception messages" | Hardware-gate premise tied to build config. | area: PLAT | related: PLAT.T13
- INVAR | SPECIFICATION.md:5025-5033 | "There are **four** such gates ... All four now match `MemoryError` *or* `memory allocation failed` ... pinned by `tests_scripts/test_memory_error_gate_agreement.py` ... Don't narrow any of them back" | Enforced agreement; do-not-narrow marker. | area: TEST | related: TEST.T18
- ASSUME | SPECIFICATION.md:5036-5040 | "measured over a full 85-file run at `gc.threshold(-1)` ... all 26 of the suite's own deliberate injections ... 25 read `\"simulated allocation failure\"` (11 ... 14 ...) and one reads `\"starved\"`" | Dated counts (85 files is stale vs 87). | area: TEST | covered-by: DOC.S08
- INVAR | SPECIFICATION.md:5040-5043 | "`tests_scripts/test_memory_error_gate_agreement.py` walks `tests/` and `digital_twin/` with `ast` for every injected exception message and fails one that borrows the interpreter's own words" | Enforced for tests/ and digital_twin/ only (not tests_hardware/device_scripts or tests_js). | area: TEST | related: TEST.T18
- SETTLED | SPECIFICATION.md:5044-5058 | "**One narrow, evidence-backed exception**: `digital_twin/run_generic_integration.py`'s `_mem_sampler()` calls `gc.collect()` ... don't re-flag it without new evidence" | Do-not-reflag marker for the sampler's collect. | area: TWIN | related: TEST.T03
- ASSUME | SPECIFICATION.md:5052-5055 | "measured on a genuinely healthy `wozi` run: `min=99808, max=1347104` across 20 cycles, a false-positive \"trend declined by 413990 bytes\" against an 18318-byte tolerance" | Single dated measurement justifying the exception. | area: TWIN | -

## SPECIFICATION.md Part I.4 — (f), (f.1), (g)
- SETTLED | SPECIFICATION.md:5059-5067 | "**(f) A `gc.threshold()` value (or a `gc.collect()` call) is defense in depth applied only once (e) already holds — never the fix itself" | Standing rule; every generated boot entry sets `gc.threshold(32768)`. | area: MEM | related: DOC.T14
- INVAR | SPECIFICATION.md:5068-5071 | "`GC_THRESHOLD=32768 scripts/test.sh` (E.3) runs every file through `tests/_threshold_runner.py` ... CI's own `unit-tests-gc-threshold` job does the same" | Enforced second stage; the plan notes twin launches run only at 32768, never at -1. | area: TEST | related: TEST.T18
- SETTLED | SPECIFICATION.md:5073-5083 | "**(f.1) The one structural exception: a boot-confined placement reset.** `gc.collect()` between the units of the two *one-time* setup lists ... **and nowhere else whatsoever**" | Owner-approved exception (2026-09-18 per CLAUDE.md). | area: MEM | related: DOC.T14
- PLATFORM | SPECIFICATION.md:5079-5081 | "`gc_collect_end()` resets the allocator's free-scan index to zero (`py/gc.c`), so the following module's permanent objects take the lowest fitting holes" | The placement effect depends on this allocator detail of the pinned version. | area: PLAT | related: PLAT.T13
- ASSUME | SPECIFICATION.md:5085-5094 | "on the twin at `gc.threshold(-1)` ... a factor of 3.2 to 6.9 on largest-contiguous-over-free ... At the shipped `gc.threshold(32768)` it changes nothing measurable" | Twin measurements cited to archive §7A; cites `docs/reference/constrained.rst:413-437` at v1.29.0. | area: MEM | related: DOC.S04
- INVAR | SPECIFICATION.md:5096-5103 | "`tests_scripts/test_gc_collect_sites.py` walks `src/` with `ast` and asserts the only `gc.collect()` call site is `system_service.start_and_check_tasks` ... plus a textual assertion that `buildgen/` emits one only from `codegen.py`" | Enforced (test + `scripts/lint.sh`); generated output itself is checked only textually at the emitter. | area: MEM | related: TEST.S11
- LIMIT | SPECIFICATION.md:5112-5116 | "Bounds are derived from the measured worst case with margin and are **twin-only**. The board ... does **not** reproduce the twin's two headline ratios at its own fill" | Boot-contiguity bounds are not a silicon property. | area: TWIN | related: TWIN.T06, HW.T16
- DRIFT | SPECIFICATION.md:5115-5116 | "measure B's silicon confirmation is a different metric (archive §7F)" | Undefined label "measure B"; archive-only citation. | area: DOC | covered-by: DOC.S16
- INVAR | SPECIFICATION.md:5116-5118 | "no `gc.collect()` in business logic, none in the run phase (the supervisor loop under the starter list is the run phase and is asserted to have none)" | Run-phase prohibition. | area: MEM | related: TEST.T03
- INVAR | SPECIFICATION.md:5120-5123 | "fix it with a design-level technique that relieves the pressure directly ... never a GC-policy change or an added `gc.collect()` call" | Rule (g). | area: MEM | related: MEM.T06
- INVAR | SPECIFICATION.md:5125-5128 | "run it through (a)-(d) at design time and give it its own (e)/(f)-shaped test pair" | Review-only obligation for every new allocation-holding function/module. | area: MEM | related: TEST.T06

## SPECIFICATION.md Part I.5 — Real-hardware confirmation
- ASSUME | SPECIFICATION.md:5132-5135 | "confirmed on real target hardware (2026-09-08): `gc.threshold(32768)` (real hammer-load `mem_free` floor 91312 bytes vs. 128 bytes at the reactive-only default)" | Dated 1.28-era silicon figures (a 128 B floor at -1 under hammer). | area: MEM | related: HW.T16
- DRIFT | SPECIFICATION.md:5135-5137 | "The piece cap's 2026-09-08 headroom figure (~48x) is withdrawn" | Withdrawn-figure narrative (low). | area: DOC | related: DOC.T05
- ASSUME | SPECIFICATION.md:5138-5141 | "a 120s always-run hammer test plus a `long_soak`-gated 600s variant) — nothing from this audit remains open pending hardware" | Closure claim for the 2026-09-07 audit. | area: HW | related: HW.S14

## SPECIFICATION.md Part J (intro)
- SETTLED | SPECIFICATION.md:5150-5153 | "No vendor document or prior specification exists — this Part **is** the specification, reconstructed from the field-proven legacy implementation ... confirmed by the project owner (2026-09-11)" | Part J is the normative contract for both implementations. | area: UART | related: UART.T01
- INVAR | SPECIFICATION.md:5155-5159 | "a never-raise contract on every entry point" | `UART_Comm` never-raise contract. | area: UART | related: UART.T01
- PLATFORM | SPECIFICATION.md:5159-5162 | "The jumper uses UART0 on GP0/GP1 and UART1 on GP8/GP9 ... GPIO24/25 and GPIO28/29 each have a half the wireless chip takes ... GPIO16/17 is left free because a BME688's BSEC coprocessor wants UART0 there" | Board pin-mux facts and a reservation for a future peripheral. | area: GEN | related: GEN.T07
- MIRROR | SPECIFICATION.md:5162-5163 | "the differences are enumerated in `UART_C_PORT_CHANGELOG.md`" | Part J ↔ changelog ↔ legacy `python/IndividualDrivers/asy_uart_comm.py`. | area: UART | covered-by: UART.T07

## SPECIFICATION.md Part I.6 — Request-body cap (sits inside Part J)
- DRIFT | SPECIFICATION.md:5165 | "## I.6 The request-body cap, and why both of Microdot's limits must move together" | Part I subsection placed after Part J's intro. | area: DOC | covered-by: DOC.S01
- PLATFORM | SPECIFICATION.md:5176-5182 | "`handle_request()` calls `Request.create()` (`:1400`), which reads the body at `:426`, and only then `dispatch_request()` (`:1410`), whose 413 check is at `:1443` ... not fixed by a version bump" | Vendored microdot ordering (v2.6.2 and upstream `main`), cited by line. | area: REST | related: REST.T09
- DRIFT | SPECIFICATION.md:5184-5186, 5194-5195 | "`max_connections` is 4, so up to **four** such buffers ... takes the four-connection worst case to 4 x 2,048 = 8,192 B" | `max_connections` is now 6 (H.7) → 12,288 B. | area: DOC | covered-by: REST.S11
- ASSUME | SPECIFICATION.md:5190-5195 | "the largest legitimate body is **1,312 B** on `PUT /networking` ... real traffic measures 232 B. So 2048 clears the schema maximum with **1.56x** margin" | Dated per-route measurements; pinned per device by `tests_scripts/test_request_body_cap_headroom.py`. | area: REST | related: REST.T01
- INVAR | SPECIFICATION.md:5197-5204 | "a cap must serve what the API accepts, not what one client happens to send" | Cap sized per route; `/sensors` grows per driver. | area: REST | related: REST.T01
- INVAR | SPECIFICATION.md:5206-5212 | "`tests_scripts/test_request_body_cap_headroom.py` computes both sides ... asserts no route can be sent a legitimate body the cap would reject" | Enforced guard. | area: REST | related: REST.T01
- INVAR | SPECIFICATION.md:5214-5218 | "**Both are set from the one constructor parameter**, so they cannot drift apart again ... `tests/test_asy_webserver_service.py`'s F.2b section pins this" | Enforced; test section label "F.2b" collides visually with Part F numbering. | area: REST | related: DOC.T03, REST.S01
- LIMIT | SPECIFICATION.md:5220-5225 | "a socket cannot distinguish \"buffered then rejected\" from \"rejected unread\" ... The binding itself stays a mock-tier and source-level claim, never a hardware-confirmed one" | Hardware tier cannot prove the no-allocation property. | area: HW | -
- ASSUME | SPECIFICATION.md:5227-5234 | "**Run on silicon, 2026-09-19** [HW]. W1-W4 pass ... (2047 -> 200, 2048 -> 200, 2049 -> 413 ...)" | Dated bench result; cites queue rows W1-W5. | area: HW | related: HW.T16, DOC.T03
- DRIFT | SPECIFICATION.md:5236-5255 | "**the resets are a property of concurrency against `max_connections = 4`** ... 3 free slots, 4 clients, **1 refusal = the measured 25 %**" | W5 analysis and its reset-rate curve were taken at the old ceiling of 4; not restated for 6. | area: DOC | related: REST.S11, PERF.T02
- RISK | SPECIFICATION.md:5248-5255, 5275-5281 | "A slot is released in `_serve()`'s `finally`, *after* `_close_writer(writer)` has awaited the close — so it outlives the response the client already holds" | Slot-release lag makes an immediate follow-up request refusable; tests compensate with `wait_until()`/`time.sleep(1.0)`. | area: REST | covered-by: PERF.T02
- ASSUME | SPECIFICATION.md:5257-5273 | "Across the 96 concurrent requests ... **not one was answered with the wrong status** ... 20 of 24 requests answered against a floor of 4" | Dated replay and silicon results. | area: HW | related: HW.T16
- DRIFT | SPECIFICATION.md:5283-5284 | "(owner's decision; `REAL_HARDWARE_TEST_QUEUE.md` §2A F11 has the account)" | Deleted queue row F11 still cited. | area: DOC | covered-by: DOC.S06
- SETTLED | SPECIFICATION.md:5290-5293 | "**Related, deliberately not changed:** `NTP_Host`'s 1024-character bound mirrors the deployed pre-refactor handler ... the owner's call" | Settled bound (plan §2.3). | area: NET | -
- MIRROR | SPECIFICATION.md:5290-5292 | "mirrors the deployed pre-refactor handler (`modules/sensortask-*.py`'s `update_valid_json(..., 3, 1024, ...)`)" | Legacy ↔ refactor bound parity. | area: PAR | related: PAR.T01

## SPECIFICATION.md Part J.1 — Scope and two-implementation contract
- SETTLED | SPECIFICATION.md:5298-5301 | "The module is **standalone and self-contained** ... Its first use case (a BME688/BSEC coprocessor) is explicitly *not* part of its scope" | Owner scope decision (dup of CLAUDE.md). | area: UART | related: DOC.T14
- ASSUME | SPECIFICATION.md:5303-5312 | "checked rather than assumed (2026-09-13). `dev_legacy/asy_bsec_driver.py`'s whole `BSEC_UART` control flow replays over the promoted module ... Two conformance tests ... demonstrate rather than constrain" | BSEC-serving claim rests on two tests that "any API able to express the flow passes". | area: UART | -
- LIMIT | SPECIFICATION.md:5313-5315 | "**One deployed value has to change in a faithful port**: `rxbuf` 32 is refused (`errno` 15) against this module's 80-byte per-poll-interval `rxbuf` floor (J.6)" | Legacy deployment parameters are not drop-in compatible. | area: UART | related: UART.T05
- ASSUME | SPECIFICATION.md:5320-5323 | "It mirrors the Python implementation's *intended* behavior ... **how far that mirroring extends to the known flaws is unverified** ... Establishing that is future work" | C peer conformance explicitly unverified (C side out of scope, owner 2026-09-24). | area: UART | related: UART.T07
- MIRROR | SPECIFICATION.md:5320-5331 | "**A second implementation of this protocol exists in C** ... **Every protocol-level change is logged in `UART_C_PORT_CHANGELOG.md`**" | Python↔C two-implementation mirror; changelog is the only bridge. | area: UART | covered-by: UART.T07
- TODO | SPECIFICATION.md:5328-5329 | "a temporary file, deleted once the C side is reconciled" | Deletion trigger unreachable while reconciliation is out of scope. | area: DOC | covered-by: DOC.S14
- SETTLED | SPECIFICATION.md:5332-5337 | "**Prefer Class A changes that only tighten receiver validation, never ones that change emitted bytes.** ... A change to emitted bytes is a coordinated flag-day needing an explicit owner decision" | Change-class policy. | area: UART | related: UART.S04
- OPENQ | SPECIFICATION.md:5335-5336 vs 5324-5326 | "conditional on the C side actually conforming, which each such change must re-verify against the C source" | Per-change re-verification against a C source whose reconciliation is out of scope (owner, 2026-09-24) — the obligation has no reachable executor (low). | area: UART | related: DOC.S14, UART.T07

## SPECIFICATION.md Part J.2 — Role model
- SETTLED | SPECIFICATION.md:5341-5344 | "This is not a symmetric peer protocol ... simultaneous initiation is out of contract rather than a case to handle" | No collision arbitration by design. | area: UART | related: DOC.T14
- INVAR | SPECIFICATION.md:5351-5358 | "**The role is enforced structurally, not by convention.** ... The responder's own answer to a GET ... runs through the internal unlocked SET path, not through the public `uart_set()` entry point" | Role gate on public entry points; internal unlocked path must stay unexposed. | area: UART | related: UART.T01

## SPECIFICATION.md Part J.3 — Frame format
- INVAR | SPECIFICATION.md:5362-5364 | "Every frame is exactly `5 + payload_size` bytes ... **the fixed size is the framing**" | Wire-format contract (Class A). | area: UART | covered-by: UART.T01
- LIMIT | SPECIFICATION.md:5372-5373 | "Without a CRC, the only integrity checking left is this layer's own structural validation" | `dev` runs `CRC_Pass` (codegen never passes `crc=`). | area: UART | covered-by: UART.S04
- SETTLED | SPECIFICATION.md:5369-5371 | "Selecting a delimited codec is a wire change and a coordinated flag day (changelog A11), not a local decision." | Owner-gated change. | area: UART | -
- PLATFORM | SPECIFICATION.md:5375-5380 | "an LSB-first/right-shifting variant over poly `0x1021` with init `0xFFFF`, appended in the platform's **native** byte order ... interoperates between the two peers only because both happen to be little-endian" | Legacy CRC wire compatibility depends on both MCUs' endianness. | area: UART | related: ALGO.T03
- MIRROR | SPECIFICATION.md:5376-5384 | "`python/IndividualDrivers/asy_uart.py`'s own `CRC16`, which is what the C peer mirrors ... `src/crc_checks.py`'s `CRC16` is a genuine MSB-first CRC-16/CCITT-FALSE appended big-endian. **The two are not wire-compatible**" | Legacy↔C mirror broken by the refactor's CRC; flag-day recorded as changelog A7. | area: UART | related: ALGO.T03, UART.T07
- INVAR | SPECIFICATION.md:5388, 5398-5410 | "**Never `0xFF`** ... Do not \"fix\" the wrap to `0xFF`: it removes the barrier and the no-repeat-within-a-train property together" | Settled UID space (author-confirmed 2026-09-11). | area: UART | related: UART.T01
- INVAR | SPECIFICATION.md:5406-5407 | "Any code predicting the *next* expected UID must reuse the same controlled wrap, never a bare `+1`" | Convention for any UID-predicting code (both languages). | area: UART | related: UART.T01
- ASSUME | SPECIFICATION.md:5403-5405 | "The value space (`0 … 0xFE`, 255 values) is **exactly** as large as the longest possible train ... so no UID repeats within a single train" | Property holds only if one UID per frame and CHUNKS ≤ 255. | area: UART | related: UART.T01

## SPECIFICATION.md Part J.4 — Transactions
- INVAR | SPECIFICATION.md:5414-5417 | "**Every frame is individually acknowledged before the next is sent** — stop-and-wait at frame granularity ... no windowing and no NAK" | Transaction contract. | area: UART | covered-by: UART.T01
- INVAR | SPECIFICATION.md:5419-5421 | "`CHUNKS = ceil(len(payload) / payload_size) + 1`, floored at 2" | SET train sizing rule. | area: UART | covered-by: UART.T01
- INVAR | SPECIFICATION.md:5423-5427 | "the initiator sends a one-chunk GET train" | GET is one chunk; receiver does not enforce `CHUNKS=1`. | area: UART | covered-by: UART.S02
- INVAR | SPECIFICATION.md:5435-5437 | "Rejection is signalled by withholding an ACK ... The final chunk's acknowledgement is deliberately deferred until after the total-size check passes" | Rejection semantics; basis of the at-least-once seam (J.9). | area: UART | covered-by: UART.T08

## SPECIFICATION.md Part J.5 — Timing, flow control, recovery
- INVAR | SPECIFICATION.md:5441-5444 | "A half-received frame must complete promptly or the whole frame is abandoned — the anti-desync rule." | Two-level timeout contract. | area: UART | covered-by: UART.T02
- INVAR | SPECIFICATION.md:5446-5457 | "drains its receive path until the line has been quiet for `1.5 × timeout`, then holds off initiating for a further `1.5 × timeout` ... **Both constants are part of the contract**" | Class A recovery timings; "found violating this on 2026-09-13 and fixed" for local mid-train aborts. | area: UART | covered-by: UART.T02
- INVAR | SPECIFICATION.md:5459-5460 | "The write hold-off gates *initiating* transmissions only: acknowledgements are always sent" | Hold-off scope. | area: UART | related: UART.S07
- INVAR | SPECIFICATION.md:5462-5469 | "`asy_uart_driver.py` keeps `cancel_read_timeout()` and infers \"a read is in flight\" from the lock rather than a flag ... **latched and bounded** ... (changelog B15)" | Cancel-handshake contract. | area: BUS | covered-by: BUS.T05
- INVAR | SPECIFICATION.md:5471-5479 | "**Hitting the bound is reported by flagging the caller, never by logging in place**: the boot drain is not a fault and so persists nothing, while a resync persists the more specific of its two warnings" | Logging contract for drains (C.7.1 `wrnno` 10/11). | area: UART | related: UART.T02, UART.T04

## SPECIFICATION.md Part J.6 — Deployment parameters
- SETTLED | SPECIFICATION.md:5483-5487 | "`payload_size` and `timeout` are **agreed out of band** ... nothing is negotiated, now or at the C reconciliation (owner decision, 2026-09-11)" | No version/capability negotiation. | area: UART | related: DOC.T14
- SETTLED | SPECIFICATION.md:5489-5503 | "**That diagnostic has a known blind spot, accepted rather than fixed** (owner decision, 2026-09-12) ... `errno` 32 never fires" | Accepted diagnostic gap for a speak-when-spoken-to peer; pinned by `tests/test_uart_comm_hazard.py`'s `..._a_peer_that_never_produces_a_valid_frame_is_diagnosed`. | area: UART | -
- LIMIT | SPECIFICATION.md:5495-5498 | "**What it misses is a speak-when-spoken-to peer** ... presents as repeated `errno` 22 (read timeout) plus `wrnno` 10 resync warnings" | Known misdiagnosis signature. | area: UART | -
- INVAR | SPECIFICATION.md:5503-5506 | "`payload_size` must be in `1 … 255` ... an out-of-range value must never be silently clamped — C.13's readiness-gate treatment instead" | Construction contract. | area: UART | related: UART.T05
- RISK | SPECIFICATION.md:5508-5514 | "21.8 % efficiency for a single-chunk transfer, 39.7 % at 480 bytes, and an asymptote of **43.6 %**. This is accepted for the intended traffic" | Accepted wire inefficiency; A10/A11 candidates. | area: UART | -
- INVAR | SPECIFICATION.md:5516-5524 | "**A `UART` instance driving this protocol must therefore be constructed with a single-digit `poll_wait_ms`**; leaving the default in place makes every other efficiency property of the protocol irrelevant" | Not mechanically enforced: `buildgen/validate.py:270-276` checks only the timeout/rxbuf floors; driver default stays 20 ms. | area: UART | related: UART.T05, UART.T10
- ASSUME | SPECIFICATION.md:5520-5522 | "a 480-byte transfer spends roughly 1.1 s of wall clock ... about 4 % of link capacity" | Measurement at driver defaults (undated). | area: PERF | related: UART.T10
- INVAR | SPECIFICATION.md:5530-5534 | "**That is a construction refusal, not just a rule** — `timeout`'s floor below is the enforcement, and it carries `poll_idle_ms`" | Enforced in `src/asy_uart_comm.py:260` and `buildgen/validate.py:271-273`. | area: UART | covered-by: UART.T05
- INVAR | SPECIFICATION.md:5536-5548 | "**`rxbuf` is checked at construction against two independent floors** ... `timeout` has a floor too: `2 × poll_wait_ms + poll_idle_ms +` the measured worst-case GC pause" | Floors rely on the measured 21 ms GC constant. | area: UART | covered-by: UART.T10
- MIRROR | SPECIFICATION.md:5536-5548 (sites buildgen/validate.py:246-276, src/asy_uart_comm.py:95, 260, 270) | "`baud/10 × (poll_wait_ms + jitter)` ... `2 × poll_wait_ms + poll_idle_ms +` the measured worst-case GC pause" | Floor formulas duplicated in buildgen (`validate.py:247` "mirrored here rather than read") and the module. | area: GEN | covered-by: UART.T05
- LIMIT | SPECIFICATION.md:5539-5540 | "at `payload_size = 255` that is 260 bytes against the driver's own 256-byte default, so the maximum legal `payload_size` overruns the default outright" | Driver default `rxbuf` cannot carry a max-size frame. | area: UART | related: UART.T05

## SPECIFICATION.md Part J.7 — Loopback testing model
- DRIFT | SPECIFICATION.md:5555-5556 vs 5561-5563 | "`digital_twin/machine.py` (twin tier, which has no `UART` at all today)" | Contradicted four lines later ("Both models exist ... `digital_twin/machine.py`'s") and by `digital_twin/machine.py:481-488` (`UARTLink`). | area: DOC | related: DOC.T10
- MIRROR | SPECIFICATION.md:5561-5565 | "They are held to one shared set of assertions in `tests/_uart_link_contract.py` — the two may differ in fidelity, never in semantics" | Mock↔twin UART link mirror, test-enforced. | area: TEST | related: TEST.T05
- LIMIT | SPECIFICATION.md:5567-5573 | "**The mock tier's `timeout` is a scheduling budget, not a wire budget** ... `scripts/test.sh` deliberately oversubscribes the runner (4× the core count" | Mock-tier timing assertions depend on host scheduling. | area: TEST | related: TEST.T04
- ASSUME | SPECIFICATION.md:5580-5591 | "real `dev` link | 1000 ms | 2·2 + 50 + 21 = 75 ms | 13.3× ... same file, no CRC | 30 ms | 24 ms | **1.25×**" | Margin table built on the 21 ms GC constant; failure seen on CI run `35468454090`. | area: TEST | related: UART.T10, TEST.S14
- SETTLED | SPECIFICATION.md:5593-5599 | "The accepted trade-off is that neither test would now catch a *latency* regression below 240 ms" | Accepted test-coverage gap for `_hammer_clean`/`_measure_retention`. | area: TEST | related: TEST.T04
- INVAR | SPECIFICATION.md:5601-5607 | "**Constraint — a loopback harness must never register a fake UART with a real `select.poll()`.**" | Hang/segfault avoidance rule (CLAUDE.md known hang cause); `digital_twin/unix_port_poll_prewarm.py` records a `modselect.c` segfault with non-fd poll objects. | area: TEST | related: TWIN.T07

## SPECIFICATION.md Part J.8 — Memory model
- LIMIT | SPECIFICATION.md:5611-5617 | "the receiver grows `res` by `+=` across the whole train (254 reallocations and a ~2× peak at the final copy for a maximum 12192-byte transfer" | Legacy behaviour the refactor replaced (parity/migration context). | area: PAR | -
- INVAR | SPECIFICATION.md:5622-5627 | "**Two long-lived frame buffers per instance** ... sized ... `framing.max_encoded(5 + payload_size + crc_length)` ... Steady-state frame traffic allocates nothing." | Zero-allocation frame path claim. | area: UART | related: UART.T03
- INVAR | SPECIFICATION.md:5632-5634 | "**Preallocate from `CHUNKS`, never grow.** The total upper bound `CHUNKS × payload_size` is known the moment the first frame of a train arrives" | Peer-declared size drives allocation (BACKLOG accepted-with-caveat). | area: MEM | covered-by: UART.T03
- INVAR | SPECIFICATION.md:5635-5636 | "**A failed allocation degrades to the module's normal failure sentinel** and the quiesce-and-resync path, never an exception" | Never-raise contract for allocation failures. | area: UART | related: UART.T03
- SETTLED | SPECIFICATION.md:5638-5642 | "a received frame is read whole into the instance's RX frame buffer and its payload region then slice-assigned ... *not* read header-first" | Deliberate design choice. | area: UART | -
- INVAR | SPECIFICATION.md:5644-5646 | "**Padding must be zero-filled from a preallocated zero buffer** ... leaving them unwritten would transmit the previous frame's payload remnants" | Data-leak invariant. | area: UART | related: UART.T01

## SPECIFICATION.md Part J.9 — Module contract
- SETTLED | SPECIFICATION.md:5650-5658 | "**A plain class, not a `SensorReader` subclass** (owner-delegated decision, 2026-09-11, resolved against precedent)" | Base-class decision; errno/wrnno still align to `base_classes.py`'s reservation. | area: UART | -
- INVAR | SPECIFICATION.md:5660-5665 | "**`None` means failure; an empty result means a genuinely empty payload.** The two must never collapse, at any of the four result shapes" | Sentinel contract; `exp_size=None` vs `0`. | area: UART | related: UART.T01
- INVAR | SPECIFICATION.md:5667-5670 | "**`uart_listen()` returns a `ListenResult` namedtuple** ... on every path ... Its one allocation is per logical message" | Result-shape contract. | area: UART | related: UART.S05
- DRIFT | SPECIFICATION.md:5670-5671 | "C.6's `make_dict()` repr-parsing landmine does not apply" | The landmine C.6 describes no longer exists in code. | area: DOC | covered-by: DOC.S09
- SETTLED | SPECIFICATION.md:5673-5679 | "**A lost final ACK folds into failure**, deliberately ... a caller that retries on a failed `uart_set()` must tolerate the peer seeing the message twice" | At-least-once seam; idempotency obligation on callers, unenforced. | area: UART | covered-by: UART.T08

## SPECIFICATION.md Part K (intro) and K.1 — Before writing code
- INVAR | SPECIFICATION.md:5691-5695 | "Use it as a literal checklist ... Where a step doesn't apply ... say so explicitly rather than silently skipping it" | Process rule for every promotion; review-only. | area: DOC | related: TEST.T06
- INVAR | SPECIFICATION.md:5699-5701 | "Place the real PDF under `datasheets/<name>/` ... every hardware-interaction claim in code comments cites a page number against it" | Citation discipline; plan notes A.6's datasheet list omits isl29125. | area: SENS | related: DOC.S08
- INVAR | SPECIFICATION.md:5702-5706 | "Check Part G's shared-primitive catalog before writing anything new ... website-facing needs its `src/`↔`js/` mirror obligation honored too (Part G.3)" | Restates G.1/G.3 obligations per promotion. | area: XCUT | covered-by: XCUT.T15

## SPECIFICATION.md Part K.2 — Driver to the Part C/D bar
- INVAR | SPECIFICATION.md:5724-5729 | "Ruff's `FBT001`/`FBT002` ... reject a `bool`-typed parameter that isn't keyword-only" | Enforced by lint (`select = ["ALL"]`). | area: CI | -
- LIMIT | SPECIFICATION.md:5730-5737 | "this project's own `tests/machine.py`/`digital_twin/machine.py` fakes both type `pull` as a plain `int` with a `-1` sentinel, not `int | None`, so the real MicroPython-idiomatic `pull=None` would need both fakes' own signatures widened" | Fake signatures diverge from the real `machine.Pin` API and constrain `src/` call shapes. | area: TEST | related: TEST.T19

## SPECIFICATION.md Part K.3 — Wire into buildgen
- INVAR | SPECIFICATION.md:5742-5744 | "confirm by actually running `buildgen/generate.py` against a fixture TOML ... not by inspection alone" | Review-only process step. | area: GEN | -
- SETTLED | SPECIFICATION.md:5746-5747 | "**`buildgen/buildspec.py`** — the one hand-maintained per-driver table (its own docstring says so; every other buildgen table is AST-derived from `src/`)" | Hand-maintenance settled (plan §2.3); "every other table AST-derived" conflicts with the plan's list of other hand catalogs (`_SENSOR_DRIVERS`, `_ERRCOUNT_CATALOG`, ...). | area: GEN | related: GEN.T06
- RISK | SPECIFICATION.md:5751-5755 | "**Check the datasheet for a real address-select pin before deciding `ADDRESS_CAPABLE_DRIVERS` vs. `FIXED_ADDRESS_DRIVERS`** ... guessing this wrong lets a device TOML declare a meaningless `address` field that silently does nothing" | Silent misconfiguration risk; ISL29125 address hardwired (FN8424 p15). | area: GEN | related: GEN.T13
- ASSUME | SPECIFICATION.md:5756-5762 | "Only add a `_OVERRIDES` entry if the driver genuinely can't follow that convention (today: `fram`, `neopixel`, `notification`, `uart_link`" | Dated inventory of overrides. | area: GEN | covered-by: GEN.T13
- INVAR | SPECIFICATION.md:5766-5769 | "Every optional TOML field gets emitted only `if \"<field>\" in f:` ... never unconditionally" | Codegen convention, tested per field in `test_buildgen_generate.py`. | area: GEN | related: GEN.T02
- RISK | SPECIFICATION.md:5770-5772 | "add the driver to `_SENSOR_DRIVERS` ... Skipped, the driver silently never appears on the website with no error anywhere" | Hand catalog whose omission fails silently. | area: GEN | covered-by: GEN.T06
- INVAR | SPECIFICATION.md:5773-5778 | "Add a case only if the driver needs a *real interrupt/GPIO line the twin's chip fake has to drive edges on* (today: `scd30`, `isl29125` — see `compute_twin_wiring()`'s own `if spec.driver in (\"scd30\", \"isl29125\")` branch)" | Hardcoded driver tuple in `twin_wiring.py`, another hand catalog. | area: GEN | related: GEN.T06, TWIN.T12
- MIRROR | SPECIFICATION.md:5779-5781 | "`uart_link`'s `UART_ROLE` table, transcribed from the Pico W datasheet" | `buildgen/pico_gpio.py` ↔ Pico W datasheet. | area: GEN | related: GEN.T07

## SPECIFICATION.md Part K.4 — @web tags
- DRIFT | SPECIFICATION.md:5785-5786 | "`html/definitions/<device>.json` is generated at build time from every tagged `src/` file (Part H.5.1); it is never hand-maintained" | wozi/dev definitions are hand-written (H.5). | area: DOC | covered-by: DOC.S03
- INVAR | SPECIFICATION.md:5794-5798 | "Every tag family gets full accept/reject grammar test coverage ... extending a tag family's own grammar ... needs new tests in that same file" | Review-only test obligation. | area: GEN | related: GEN.T03

## SPECIFICATION.md Part K.5 — Digital twin
- INVAR | SPECIFICATION.md:5802 | "A chip fake is **required, not optional**, the same session as promotion (C.11 item 9)" | Process rule. | area: TWIN | related: TWIN.T01
- DRIFT | SPECIFICATION.md:5803-5804 | "wired into `digital_twin/machine.py`'s `_build_i2c_chip()`/`_build_spi_chip()` dispatch (matched by `driver` string" | `_build_spi_chip()` does not exist (twin has `_wire_spi_device()`, FRAM only). | area: DOC | covered-by: DOC.S22
- MIRROR | SPECIFICATION.md:5810-5812 | "Add `Pin.PULL_UP`/whatever other `machine`-fake constant the real driver now references to **both** `tests/machine.py` and `digital_twin/machine.py`" | Two-fake mirror obligation. | area: TEST | related: TEST.T19

## SPECIFICATION.md Part K.6 — Tests, every tier
- INVAR | SPECIFICATION.md:5816-5820 | "every parameter individually and in combination ... out-of-range on both sides of every bound, exact boundary values accepted, `NaN`/`±inf` on every float argument" | Per-driver unit-test bar (D.12). | area: TEST | related: TEST.T02
- INVAR | SPECIFICATION.md:5822-5831 | "that module needs its own direct, dedicated tests too — exercising it only incidentally through the new driver's own fixture values is not enough" | Shared-module test rule (PR #87 gap). | area: TEST | related: ALGO.T01
- INVAR | SPECIFICATION.md:5852-5854 | "`test_device_tomls.py` — which real devices carry this driver (an explicit allow-list assertion ... never let a new instance land on a device by omission of a check)" | Allow-list rule per driver. | area: GEN | -
- INVAR | SPECIFICATION.md:5858-5876 | "**Bus-hazard coverage, all four tiers, standing rule** ... Add the new driver to `tests/_bus_hazard_catalog.py`'s `I2C_HAZARD_CATALOG`" | Four-tier rule; cross-sensor now generated. | area: TEST | related: TEST.T06
- DRIFT | SPECIFICATION.md:5867-5868 vs 5966-5967 | "**Cross-sensor hazard coverage is automatic ... no longer hand-paired per driver.**" vs "(auto-generated if that capability has landed by the time you read this — check; hand-paired otherwise)" | K.11 still hedges on a capability K.6 says has landed; CLAUDE.md's four-tier list still names `test_bus_hazard_multi_device.py` as the mock tier (low). | area: DOC | related: DOC.T10

## SPECIFICATION.md Part K.7 — devices/*.toml
- INVAR | SPECIFICATION.md:5880-5885 | "Wiring facts ... must come from **real, bench-validated hardware**, never invented — cite where the fact came from in a TOML comment" | Review-only provenance rule. | area: GEN | related: GEN.T08
- RISK | SPECIFICATION.md:5886-5888 | "Placement within the `[[instance]]` list has FRAM-chunk-order consequences (bump-pointer allocator, Part A.7) — no hard rule ... which usually just means \"last.\"" | Reordering instances silently remaps FRAM chunks. | area: STOR | covered-by: XCUT.T09
- MIRROR | SPECIFICATION.md:5892-5895, 5970-5971 | "The on-target sweep (`device_scripts/bus_topology_autodetect_and_hazard_sweep.py`) keeps its own address table ... needs the new address added by hand" | `KNOWN_ADDRESSES` ↔ `devices/*.toml`, hand-kept, no cross-check. | area: HW | related: HW.T08

## SPECIFICATION.md Part K.8 — Regenerate and spot-check
- DRIFT | SPECIFICATION.md:5899 | "`html/definitions/<device>.json` regenerates from K.4's tags automatically" | Not true for hand-written wozi/dev. | area: DOC | covered-by: DOC.S03
- LIMIT | SPECIFICATION.md:5900-5903 | "a stale `mockdata/<device>.json` ... is a real, found-twice gap ... worth checking for explicitly, not just assumed fine because nothing failed" | Mock fixtures are not validated against the real schema. | area: WEB | covered-by: WEB.T15

## SPECIFICATION.md Part K.9 — Documentation
- INVAR | SPECIFICATION.md:5907-5923 | "a new `M.<n>` section for any real, datasheet-derived findings ... A `C.7.1` errno/wrnno table row ... `DEVICE_REFERENCE.md` — end-user-facing notes only ... BACKLOG.md — only for a genuinely still-open question" | Documentation obligations per promotion; review-only. | area: DOC | related: DOC.T06
- TODO | SPECIFICATION.md:5921-5923 | "\"no pytest gate wired for the new conformance-probe script yet\" — PR #83's own disclosed, not-silently-resolved gap" | Example of an open gap; whether still open is not stated here (low). | area: TEST | related: TEST.S20

## SPECIFICATION.md Part K.10-K.11 — Verification and certification
- INVAR | SPECIFICATION.md:5929-5932 | "**Actually generate all six real device TOMLs** ... inspect the output ... don't infer correctness from tests alone" | Manual review step; generated modules otherwise unlinted (GEN.S17). | area: GEN | related: GEN.T10
- ASSUME | SPECIFICATION.md:5935-5939 | "`scripts/run_digital_twin_ci.sh <device>` ... already runs the whole suite **twice**, once at `gc.threshold(-1)` and once at the shipped `gc.threshold(32768)`" | Claim about the twin runner's two passes. | area: SCR | related: TEST.T18
- INVAR | SPECIFICATION.md:5944-5981 | "Check off per promotion; note explicitly (not silently) anywhere a step didn't apply" | Certification checklist; no record of past check-offs is required anywhere. | area: DOC | -

## SPECIFICATION.md Part L.1 — Device variants and acceptance criteria
- ASSUME | SPECIFICATION.md:5996-6001 | "`klkizi`/`grkizi`/`schlafzi` (the three \"ArZi neu\" units — currently identical hardware ...) ... `wozi`/`dev` are the only two carrying a `bmp3xx` instance; every SCD30-carrying `i2c0` bus gets `timeout = 200000`" | Dated per-device inventory (true at 2a88cc8 per `devices/*.toml`); the 200000 timeout is a per-file convention. | area: GEN | related: GEN.T08, PAR.T13
- LIMIT | SPECIFICATION.md:6003-6005 | "Two criteria define the scheme and must keep holding — they are the thing a change to `buildgen/` can most easily break without any test naming them" | Self-declared: the two acceptance criteria have no named guarding test. | area: GEN | related: GEN.T06, CI.T07
- DRIFT | SPECIFICATION.md:6006-6009 vs 5741-5772 | "**A new driver needs exactly one association** ... True of every driver in `src/` today." | K.3 lists `buildspec.py` rows, a `_build_args_<name>()` handler and a `_SENSOR_DRIVERS` entry for every new driver. | area: DOC | related: GEN.T06
- DRIFT | SPECIFICATION.md:6012-6019 | "**A new hardware combination of already-known drivers needs exactly one new file**, the device's own TOML" | Hardcoded six-device CI matrices, `KNOWN_DEVICES`, and per-device `tests/test_sensortask_<device>.py` wrappers each need an edit too. | area: GEN | related: CI.T07, WEB.S22
- SETTLED | SPECIFICATION.md:6021-6022 | "**Real hardware flashing is out of scope for this scheme**, and the watchdog stays fixed (hardcoded 8000 ms, uniform, never per-device)" | Uniform watchdog decision. | area: GEN | related: XCUT.S13

## SPECIFICATION.md Part L.2 — Core design decisions
- SETTLED | SPECIFICATION.md:6027-6032 | "**Generation is build-time only; nothing generated is committed.** ... No static `src/sensortask_*.py` file exists" | Build design decision. | area: GEN | related: XCUT.T14
- RISK | SPECIFICATION.md:6034-6036 | "the hotspot password is a per-device TOML field defaulting to the existing hardcoded `\"12345678\"` (accepted risk, CLAUDE.md)" | Accepted credential risk. | area: SEC | related: GEN.T08
- RISK | SPECIFICATION.md:6040-6043 | "a value outside either field's schema bounds is dropped back to that shared default at boot rather than failing - for the password, back to the one published in `src/`" | Silent runtime fallback to the published password; build-time caps mitigate. | area: SEC | related: GEN.T15
- MIRROR | SPECIFICATION.md:6040-6042 | "`[device].hostname` is capped at `network.hostname()`'s own 32 characters at build time, and `[device].hotspot_password` is held to WPA2-PSK's own 8-63" | buildgen bounds ↔ `asy_wifi_service` `_VAL_*` bounds. | area: GEN | covered-by: GEN.T15
- INVAR | SPECIFICATION.md:6049-6054 | "**Every real cross-instance link gets a TOML-visible `[instance.wiring]`/`[device.wiring]` field** — none stay hardcoded in `build_system()`" | Plan seed: codegen hardcodes `fram=` for device-level consumers and `conn.set_ext_led`. | area: GEN | related: GEN.S09
- INVAR | SPECIFICATION.md:6059-6063 | "**No getters and no callback functions in generated code.**" | Generated-code convention; `signal_sink` resolves to a bound method (`mode="attr"`, 6225-6227), arguably a callback. | area: GEN | related: GEN.T04
- ASSUME | SPECIFICATION.md:6068-6070 | "every producer's locked-value holder has a safe, defined initial value at construction and every consumer treats that \"not yet measured\" state as normal" | Convention across all producers/consumers; not mechanically checked. | area: XCUT | related: XCUT.T17
- INVAR | SPECIFICATION.md:6075-6078 | "no hardcoded pins anywhere in generated or hand-written driver-wiring code" | Scope excludes device scripts (plan HW.S18: ~20 scripts hardcode pins). | area: GEN | related: HW.T08
- INVAR | SPECIFICATION.md:6079-6082 | "Frozen-module selection is dependency-driven ... Dynamic imports are disallowed project-wide, which is what makes the closure sound." | Soundness depends on F.1's rule. | area: GEN | covered-by: GEN.T05
- DRIFT | SPECIFICATION.md:6083-6086 | "Tests are generic bodies driven by each device's TOML and generated module, never hand-written or generated per-variant test files." | Six hand-written per-device wrappers exist (`tests/test_sensortask_<device>.py`, 11 lines each) (low). | area: DOC | related: CI.T07

## SPECIFICATION.md Part L.3 — Device TOML schema
- INVAR | SPECIFICATION.md:6098-6106 | "Their per-device-tunable knobs ... live directly in `[device]`, **required, not defaulted** ... `max_connections`/`backlog` ... `ntp_retry_s`/`ntp_retry_max_s` ... buildgen checks the effective value either way" | Required-vs-defaulted split; "checks the effective value either way" is a claim to verify. | area: GEN | related: GEN.T01
- INVAR | SPECIFICATION.md:6231-6236 | "resolves against the TOML's own `driver`+`name_ext` identity — **never** against `instance_name()`/each driver's own `_NAME` constant ... `_NAME` is `\"NOTIFY\"`, not `\"NOTIFICATION\"`" | Two naming spaces that must not be mixed. | area: GEN | related: GEN.T04
- DRIFT | SPECIFICATION.md:6223 vs 4234-4236 | "**`_WIRING`'s shape** (a `# @wiring` comment tag, not a Python tuple — L.6)" | G.2 still describes "a `_WIRING: \"WiringSchema\"` tuple next to a driver's `_VAL_*` schema tuples"; `src/` has only `# @wiring` tags (e.g. `src/asy_bmp3xx_driver.py:114`). | area: DOC | related: DOC.T10
- LIMIT | SPECIFICATION.md:6238-6239 | "`tests_scripts/test_device_tomls.py` is a minimal shape/collision smoke-test suite run directly against the six real files" | Deliberately minimal independent check. | area: GEN | -

## SPECIFICATION.md Part L.4 — Generator pipeline
- INVAR | SPECIFICATION.md:6243 | "`buildgen/` is a real top-level CPython package, never imported by `src/`" | Package boundary. | area: GEN | -
- INVAR | SPECIFICATION.md:6258-6261 | "every failure is a `buildgen.errors.BuildError` naming the device, instance and field responsible" | Contract; plan seeds show raw `KeyError`/`AttributeError`/`ValueError` escapes. | area: GEN | covered-by: GEN.T01, GEN.T12
- LIMIT | SPECIFICATION.md:6262-6264 | "each signal's threshold default/range and flash colour is a fixed, generator-owned catalog (`buildgen.codegen._KNOWN_SIGNALS`) ... no per-device override for them today" | No per-device tuning of warning signals. | area: GEN | related: GEN.T06
- MIRROR | SPECIFICATION.md:6276-6281 | "scd30/sgp40's fixed hardware address (`FIXED_ADDRESSES`, matching `src/`'s own hardcoded defaults) and FRAM's real RDID reply bytes (`digital_twin/machine.py`'s `_FRAM_RDID_BY_MAX_SIZE`, keyed by size as the best available proxy)" | Twin-side hand tables mirroring `src/` defaults; `buildgen/twin_wiring.py:12` also lists `isl29125`, so the doc's list is stale (low). | area: GEN | covered-by: GEN.T06
- ASSUME | SPECIFICATION.md:6284-6285 | "No hand-typed wiring literal exists anywhere." | Absolute claim; the FIXED_ADDRESSES/RDID tables above are hand-typed wiring facts. | area: TWIN | related: TWIN.T12
- DRIFT | SPECIFICATION.md:6286-6288 vs 3439-3444 | "`digital_twin/run_generic_integration.py` boots any `sensortask_<device>` module ... resolving it via `__import__(--module)`" | F.1 forbids `__import__`/`importlib` "anywhere in this codebase"; sites: `digital_twin/run_generic_integration.py:356`, `tests/_sensortask_scenarios.py:127`, `tests/_webserver_concurrency_scenarios.py:100`, `tests/_digital_twin_construction_scenarios.py:98`, `tests/_boot_contiguity_probe.py:125`, `tests/test_asy_isl29125_driver.py:1301, 1306`, `buildgen/validate.py:6, 194-197`. | area: XCUT | related: XCUT.T16
- ASSUME | SPECIFICATION.md:6288-6292 | "asserts a real `GET` against five REST endpoints returns 200 — for all six real devices plus both synthetic fixtures" | Five of the six routes; plan notes this test reads output only on nonzero exit. | area: TEST | related: TEST.T18
- LIMIT | SPECIFICATION.md:6293-6295 | "**Known twin limitation**: `machine.py`'s single-chip SCD30/FRAM globals only persist the *last-wired* instance's NVM state across a simulated reboot on a multi-instance device" | Twin fidelity gap for multi-instance devices. | area: TWIN | related: TWIN.T10

## SPECIFICATION.md Part L.5 — Build/generator script quality bar
- INVAR | SPECIFICATION.md:6307-6311 | "**Detect and react to every error class that would make a real build impossible**" | Build-tool contract (abort, not degrade). | area: GEN | covered-by: GEN.T01
- INVAR | SPECIFICATION.md:6312-6333 | "**Global-resource-collision checks are their own error class and must not be skipped.** ... Every one of these must produce a specific, human-readable error naming the two colliding declarations" | GPIO, per-bus address, instance identity (two naming spaces), bus-id collisions. | area: GEN | related: GEN.T12
- INVAR | SPECIFICATION.md:6337-6344 | "**Driver-declared bus requirements are enforced via a `# @requires` comment tag, never a real Python variable**" | Tag parsed as text, never imported. | area: GEN | related: GEN.T03
- SETTLED | SPECIFICATION.md:6345-6349 | "**Every driver-declared fact the running firmware never reads is a comment tag, not a Python value** (project owner's ruling, 2026-09-10) ... The one exception is a `_Default<Field>` class" | Owner ruling. | area: GEN | related: DOC.T14
- INVAR | SPECIFICATION.md:6350-6357 | "a tag that is present, or close to present with a typo, must be verified correct in every dimension ... or fail the build loud, never be silently treated as \"no tag here.\"" | Standing near-miss rule; plan notes column-0 comments inside function bodies are treated as module level. | area: GEN | related: GEN.T03, GEN.S10
- INVAR | SPECIFICATION.md:6357-6398 | "Each family's unit tests must cover the whole matrix: **the accept side needs full dimensionality** ... **the reject side covers each dimension once without recombining**" | Test-matrix bar per tag family; reference files `test_buildgen_tag_comments.py`, `test_buildgen_requires_tag.py`. | area: TEST | related: GEN.T03
- DRIFT | SPECIFICATION.md:6371 | "trailing inline on a module-level statement, last line with no trailing newline, beside `_WIRING`" | `_WIRING` is no longer a Python tuple in `src/` (L.3) (low). | area: DOC | related: DOC.T16
- ASSUME | SPECIFICATION.md:6398-6401 | "a driver signature change once silently broke two `tests_hardware/device_scripts/` call sites for a full day, undetected because nothing in that scope was checked at all" | Motivating incident; device_scripts are now in the main mypy pass (CLAUDE.md). | area: GEN | -
- INVAR | SPECIFICATION.md:6402-6404 | "**Never produce a corrupted or partial build.** ... no partial `build/<device>/` output left behind" | Atomic-build contract; not stated to be tested. | area: GEN | related: GEN.T16
- INVAR | SPECIFICATION.md:6405-6408 | "not a raw traceback, not a silent wrong-default fallback" | Plan seeds record raw `KeyError`/`AttributeError`/`ValueError`. | area: GEN | covered-by: GEN.T01
- INVAR | SPECIFICATION.md:6409-6415 | "every abort condition gets its own test, driven by deliberately malformed fixture definition files" | Test obligation for buildgen error paths. | area: TEST | related: GEN.T01
- INVAR | SPECIFICATION.md:6416-6417 | "Newly-built generator/validator modules join `pyproject.toml`'s ruff/mypy scope ... from day one" | Scope rule. | area: CI | related: CI.T05

## SPECIFICATION.md Part L.6.1-L.6.2 — Wiring defaults
- SETTLED | SPECIFICATION.md:6429-6431 | "Both are real, intentional device shapes rather than configuration errors, so the fix is a TOML-authored fallback the driver constructs itself — never a relaxed validator." | Design decision for absent producers. | area: GEN | -
- INVAR | SPECIFICATION.md:6435-6436 | "**Opt-in, never implicit**: a wiring field is never silently defaulted just because it is absent" | Explicit `{default = true, ...}` required. | area: GEN | related: GEN.T01
- INVAR | SPECIFICATION.md:6441-6443 | "That signature *is* the schema for the sub-table's allowed and required keys, never hand-duplicated in `buildgen/buildspec.py`" | AST-derived schema; plan notes `defaults.default_init_params` ignores keyword-only args. | area: GEN | related: GEN.S10

## SPECIFICATION.md Part L.6.3 — Per-value measurement wiring
- INVAR | SPECIFICATION.md:6452-6456 | "resolved at build time by checking that `source`'s `get_data()` result exposes an attribute named `field`" | Plan seed: `field` existence is never checked. | area: GEN | covered-by: GEN.S06
- LIMIT | SPECIFICATION.md:6467-6469 | "Name-matching is the whole mechanism — there is no separate property or unit tag system" | No unit/semantic check: any same-named field wires regardless of unit. | area: GEN | -
- INVAR | SPECIFICATION.md:6460-6462 | "both self-contained, with no cross-module import, so a device with `sgp40` but no `scd30` never pulls `asy_scd30_driver` into its frozen-module set" | Default providers must stay import-free. | area: GEN | related: GEN.T05

## SPECIFICATION.md Part L.6.4 — Comment-tag family
- ASSUME | SPECIFICATION.md:6474-6475 | "Measured saving ... ~3,576 bytes, about 2.6 % of `src/`'s frozen bytecode" | Dated measurement. | area: TOOL | related: DOC.T08
- DRIFT | SPECIFICATION.md:6495-6498 | "`asy_bmp3xx_driver.py`'s `_LIMITS` ... — the only driver with a real, datasheet-documented `_LIMITS` constraint today" | `src/asy_isl29125_driver.py:194` also carries `# @limits trigger_sec 1..3600`. | area: DOC | covered-by: DOC.S08
- PLATFORM | SPECIFICATION.md:6489-6491 | "`# @requires bus.timeout>=200000`/`bus.frequency<=100000` and `bus.frequency<=400000` ... (`bmp3xx` is deliberately untagged — its datasheet supports every I2C mode)" | Datasheet-derived bus limits (`src/asy_scd30_driver.py:108, 111`, `src/asy_sgp40_driver.py:90`); ISL29125 status not mentioned. | area: SENS | related: GEN.T08

## SPECIFICATION.md Part L.6.5 — Pico W GPIO legality
- PLATFORM | SPECIFICATION.md:6502-6515 | "`buildgen/pico_gpio.py` hardcodes the Pico W's real, fixed GPIO→peripheral table ... **GP22/GP28** have no I2C or SPI function at all. **GP23–25/29** are reserved" | Board-specific table transcribed from datasheet Figure 2 p.4; no board parameterization. | area: GEN | covered-by: GEN.T07
- MIRROR | SPECIFICATION.md:6502-6504 | "transcribed from `datasheets/pico w/RP-008312-DS-2-pico-w-datasheet.pdf` Figure 2 (p.4)" | Code table ↔ datasheet figure. | area: GEN | covered-by: GEN.T07

## SPECIFICATION.md Part L.6.6 — Validation coverage
- INVAR | SPECIFICATION.md:6526-6538 | "Every check raises `buildgen.errors.BuildError` naming the device, instance and field responsible — never a generic failure, a raw traceback or a silent partial build" | Coverage claim contested by plan seeds GEN.S03/S04/S10. | area: GEN | covered-by: GEN.T01
- LIMIT | SPECIFICATION.md:6540-6546 | "**Known limitation**: `buildgen/buildspec.py`'s per-driver TOML-field schema ... is still hand-maintained ... BACKLOG.md's \"Deferred\" section" | Deferred work, settled as hand-maintained for now. | area: GEN | related: GEN.T06

## SPECIFICATION.md Part L.7 — Product versioning
- INVAR | SPECIFICATION.md:6550-6558 | "`GET /system` gains one nested, never-flattened `\"build\"` sub-entry ... never through `SettingsGroup` ... Never conflate the two" | Build-info shape contract. | area: REST | related: GEN.T14
- DRIFT | SPECIFICATION.md:6560-6561 vs 4265-4266 | "Neither version nor the build date is rendered in the UI" | Contradicts H.1's "every REST endpoint's functionality must be reachable somewhere in the GUI". | area: DOC | covered-by: WEB.S20
- SETTLED | SPECIFICATION.md:6563-6568 | "**Single source of truth: `buildgen/version.py`** ... No bump mechanism exists: one clear, documented place to change the two constants, no automation" | Manual bumping by design. | area: GEN | related: GEN.T14
- MIRROR | SPECIFICATION.md:6556-6558 (sites buildgen/version.py:7-8, html/definitions/wozi.json:3, dev.json:3) | "The website version also appears independently as a top-level `websiteVersion` key in `definitions.json`" | Hand-written wozi/dev JSON hard-code `"2.0b0"`, so a `WEBSITE_VERSION` bump leaves them behind. | area: WEB | covered-by: GEN.T14

## SPECIFICATION.md Part M (intro) and M.1 — ISL29125
- SETTLED | SPECIFICATION.md:6581-6584 | "CLAUDE.md's rule to verify a driver against the legacy driver's field-proven behaviour **has no purchase here** ... (owner)" | Legacy ISL29125 parity explicitly not a reference. | area: PAR | -
- LIMIT | SPECIFICATION.md:6576-6577 | "Only the ISL29125 has needed one so far." | Other chips (SCD30, SGP40, BMP3xx, FRAM) have no Part M entry (low). | area: DOC | related: TEST.S20

## SPECIFICATION.md Part M.1.1 — Settled requirements (owner's list)
- INVAR | SPECIFICATION.md:6588-6589 | "the numbering is load-bearing and must not be re-flowed" | Requirement numbers are cited from code/tests. | area: DOC | related: DOC.T02
- SETTLED | SPECIFICATION.md:6591-6638 | "1. **Every setting is API-settable and persisted.** ... 21. ... Saturation status is a measurement-output field (`Overrange`), never a log entry" | 21 owner requirements the driver is audited against (req. 14 superseded). | area: SENS | related: SENS.T08
- SETTLED | SPECIFICATION.md:6605-6606 | "9. **HSB's low-light behaviour is accepted** — no log scaling and no validity flag. Do not re-propose either." | Do-not-re-propose marker. | area: SENS | related: DOC.T14
- PLATFORM | SPECIFICATION.md:6600-6601 | "the datasheet's bare-sensor guidance of ~40 codes is the applicable default, not p10's `0xBF`" | IR-compensation default rests on the enclosure assumption (no IR-tinted cover). | area: SENS | related: SENS.T01
- INVAR | SPECIFICATION.md:6619-6622 | "16. **The driver is self-healing and never reports a stale value as fresh.** ... a sample the driver cannot prove is current is reported as `None`, never re-stamped" | Plan seed: on config-read failure ISL29125 still publishes a freshly stamped sample. | area: SENS | related: SENS.S25, SENS.T04
- INVAR | SPECIFICATION.md:6623-6626 | "17. **Auto-range must not depend on the interrupt alone.** ... the interrupt is the *fast* path, the periodic read the *guaranteed* one" | Dual-path requirement. | area: SENS | related: SENS.T05, SENS.S15
- SETTLED | SPECIFICATION.md:6627-6628 | "18. **Scope is the `dev` variant only.** `devices/wozi.toml` declares no `isl29125` instance and must not gain one." | Enforced by `test_isl29125_only_present_on_dev` (K.6). | area: GEN | -
- ASSUME | SPECIFICATION.md:6629-6630 | "19. ... No driver in `src/` rounds any output; the renderer's `decimals` hint does (H.5)." | Whole-`src/` claim (duplicates H.5.1). | area: SENS | -
- INVAR | SPECIFICATION.md:6631-6633 | "20. **Construction and `setup()` must complete on a bus where the chip never answers** ... proven for the buildgen-generated object graph" | Absent-chip requirement. | area: SENS | related: SENS.T14

## SPECIFICATION.md Part M.1.2 — Measured chip behaviour
- PLATFORM | SPECIFICATION.md:6642-6653 | "Measured on real hardware (2026-09-12/13) ... `BOUTF` ... **cleared** by a status read, by the `0x46` reset command, and by writing `0x00` to `0x08`. p12 names only the write" | Silicon facts diverging from the datasheet (single specimen); twin `_isl29125_chip.py` models every row. | area: SENS | related: TWIN.T01, HW.T16
- MIRROR | SPECIFICATION.md:6643 | "`digital_twin/_isl29125_chip.py` models every row" | Chip fake ↔ measured behaviour table. | area: TWIN | related: TWIN.T01
- ASSUME | SPECIFICATION.md:6655-6657 | "a real brownout is reported exactly once — what `_recover_brownout()`'s `_brownout_seen` latch assumes" | Depends on exactly one destructive status read per cycle. | area: SENS | related: SENS.T03
- ASSUME | SPECIFICATION.md:6660-6666 | "At `PRST = 4`, one status read per second set `RGBTHF` in exactly 4 of 8 reads ... the restart half is reproduced by the method above" | Measurement; only the unit is asserted on silicon by `isl29125_real_irq_edge.py`. | area: SENS | related: HW.T16

## SPECIFICATION.md Part M.1.3 — Register ownership, prior art, colour chain
- INVAR | SPECIFICATION.md:6670-6680 | "The driver keeps a shadow of `CONFIG1`-`CONFIG3` and writes it back whole; that is sound only while exactly one function touches each register." | Sole-writer table (`configure()`, `set_thresholds()`, `clear_brownout()`, `reset()`), convention-only; plan notes `set_autorange_thresh()` does not rewrite threshold registers. | area: SENS | related: SENS.S16
- SETTLED | SPECIFICATION.md:6682-6686 | "Deliberately unused, so nobody adds them later: `SYNC` ... `CONVEN` ... `RGBCF` and `CONVENF`" | Do-not-add markers; `reset()` deliberately skips the status check. | area: SENS | -
- LIMIT | SPECIFICATION.md:6691-6693 | "**Nobody does auto-range or CCT** — both are this driver's own ... there is no reference to differential-test against" | No external oracle for auto-range/CCT. | area: SENS | related: TEST.T17
- SETTLED | SPECIFICATION.md:6697-6702 | "The **sRGB/Rec.709 D65 matrix is pinned as literals** ... **The two published McCamy forms are algebraically identical** ... Do not \"correct\" one into the other." | Do-not-fix markers in `math_helpers.py`. | area: ALGO | related: ALGO.T01
- LIMIT | SPECIFICATION.md:6703-6706 | "**The matrix is a placeholder by the datasheet's own statement** ... so the reported colour is relative. There is **no gamma decode**" | Reported colour/CCT is relative, not calibrated. | area: SENS | -
- INVAR | SPECIFICATION.md:6705-6706 | "an out-of-domain input means the chain is broken and is rejected, not clamped" | Helper domain contract. | area: ALGO | related: ALGO.T01
- SETTLED | SPECIFICATION.md:6711-6713 | "**The Renesas application notes are unobtainable — do not re-attempt.**" | Do-not-re-attempt marker; 12-bit cycle time derived (~6.3 ms). | area: SENS | -

## SPECIFICATION.md Part M.1.4 — Auto-range
- SETTLED | SPECIFICATION.md:6717-6719 | "(owner, 2026-09-13/14): **a value whose only correct settings are a function of another field is derived, never exposed**" | Owner design rule. | area: SENS | -
- ASSUME | SPECIFICATION.md:6721-6727 | "At 16 bit / 1 s that is 2; at 12 bit ... it is 8 ... Measured (2026-09-13): a hand-set `PRST = 4` (1,212 ms) lost 5 of 6 crossings ... `PRST = 2` (606 ms) led 6 of 6" | Dated silicon measurement; `SampleInterv` writes `CONFIG3` (a config write triggers a chip write). | area: SENS | related: HW.T16
- SETTLED | SPECIFICATION.md:6728-6731 | "`_AR_DOWN_DIVISOR`, with the divisor `2 × 26.67` — the part's *nominal* range ratio, deliberately not the measured `GainRatio`" | Deliberate decoupling. | area: SENS | -
- SETTLED | SPECIFICATION.md:6732-6735 | "**The settle margin is a constant**, `_SETTLE_CYCLES = 2` ... No scene, light level or resolution makes another value right." | Constant by design. | area: SENS | related: SENS.S27
- INVAR | SPECIFICATION.md:6736-6740 | "counts a decision as interrupt-led only with **both** [flag and edge]; five periodic-led decisions in a row warn that the line looks dead" | Dead-INT-line detector contract (C.7.1 ISL29125 row). | area: SENS | related: SENS.T05

## SPECIFICATION.md Part M.1.5 — Calibration
- INVAR | SPECIFICATION.md:6746-6749 | "`GainRatio` ... **changed only by a user PUT**: the driver never writes its own config, so every flash write stays on the REST path Part F.2's power-cycle recovery argument depends on" | Plan seed: an ISL29125 `GET /sensors` can write the chip and the FRAM ring. | area: SENS | related: SENS.S24, CORE.T02
- INVAR | SPECIFICATION.md:6750-6751 | "`ISLCalibrate` is command-only ... nothing schedules it, so normal operation pays nothing" | Calibration only on demand; UI resend risk noted in WEB.S01. | area: SENS | related: WEB.S01
- LIMIT | SPECIFICATION.md:6758-6760 | "**A refusal is reported by absence** (`GainMeas` stays `None`) ... so it logs only at debug level" | Calibration refusal silent at default log level by design. | area: SENS | -
- LIMIT | SPECIFICATION.md:6761-6764 | "a strongly coloured scene can be parked on the high range where its green is too small to calibrate from. **Operator procedure: park the scene dark first ...**" | Known limitation handled by an operator procedure (not in DEVICE_REFERENCE per this Part). | area: SENS | related: DOC.T11
- ASSUME | SPECIFICATION.md:6766-6768 | "Proven on silicon (2026-09-14): three runs at ~138 lx ... nine candidates within 23.70–24.13 ... from 11.4 % to 0.4 %" | Dated single-board measurement. | area: SENS | related: HW.T16

## SPECIFICATION.md Part M.1.6 — Range ratio varies with level
- SETTLED | SPECIFICATION.md:6772-6773, 6783-6785 | "not an open question and not a defect ... do not re-raise it as actionable" | Do-not-reopen marker. | area: SENS | related: DOC.T14
- ASSUME | SPECIFICATION.md:6773-6778 | "six illuminants × three channels, 2026-09-12 ... 28.08, 23.29, 22.49 and 21.55 ... Low-range compression and high-range under-read at small counts fit equally well" | Single-specimen measurement; cause undetermined (needs reference meter / second board). | area: SENS | related: HW.T16
- LIMIT | SPECIFICATION.md:6780-6783 | "no single value is right everywhere — a ratio measured in the overlap band (~22–23) ... makes low-light cross-range comparisons slightly worse" | Accepted accuracy limit of one `GainRatio`. | area: SENS | -

## Coverage
Every line of SPECIFICATION.md 3422-6785 was read in full, in chunks (no keyword-only pass).
| Part/subsection | lines read | items |
|---|---|---|
| F.1 Core platform facts | 3422-3589 | 46 |
| F.2 Blocking calls / backstops | 3590-3645 | 16 |
| F.3 Long-blocking operations | 3646-3654 | 2 |
| F.4 Vendor-derived code | 3655-3663 | 3 |
| F.5 intro | 3664-3677 | 4 |
| F.5.1 I2C/SPI deinit | 3678-3709 | 7 |
| F.5.2 SPI RX-overrun EIO | 3710-3747 | 9 |
| F.5.3 1.29 build wins | 3748-3781 | 7 |
| F.5.4 mem_backup | 3782-3798 | 2 |
| F.5.5 Stub defects | 3799-3825 | 5 |
| F.5.6 Smaller 1.29 facts | 3826-3851 | 9 |
| F.5.7 UART.deinit unrooted | 3852-3876 | 2 |
| F.5.8 UART read blocks loop | 3877-4006 | 18 |
| F.5.9 Idle poll cost | 4007-4049 | 6 |
| F.6 SIGINT/gc_collect wedge | 4050-4129 | 10 |
| G intro, G.0, G.1 | 4130-4156 | 2 |
| G.2 Primitive catalog | 4157-4248 | 14 |
| G.3 Re-validation | 4249-4259 | 1 |
| H.1 | 4260-4277 | 3 |
| H.2 | 4278-4319 | 4 |
| H.3 | 4320-4343 | 3 |
| H.4 | 4344-4371 | 13 |
| H.5 | 4372-4409 | 6 |
| H.5.1 | 4410-4494 | 13 |
| H.6 | 4495-4516 | 6 |
| H.7 (incl. connection ceiling) | 4517-4630 | 17 |
| H.7.1 | 4631-4663 | 4 |
| H.7 cross-browser | 4664-4695 | 5 |
| H.8 | 4696-4750 | 9 |
| H.8.1 | 4751-4763 | 2 |
| I intro | 4764-4771 | 1 |
| I.1 | 4772-4841 | 10 |
| I.2 | 4842-4887 | 6 |
| I.3 | 4888-4974 | 13 |
| I.4 (a)-(e) | 4975-5058 | 13 |
| I.4 (f), (f.1), (g) | 5059-5129 | 11 |
| I.5 | 5130-5147 | 3 |
| J intro | 5148-5164 | 4 |
| I.6 (inside Part J) | 5165-5295 | 15 |
| J.1 | 5296-5338 | 8 |
| J.2 | 5339-5359 | 2 |
| J.3 | 5360-5411 | 8 |
| J.4 | 5412-5438 | 4 |
| J.5 | 5439-5480 | 5 |
| J.6 | 5481-5549 | 11 |
| J.7 | 5550-5608 | 6 |
| J.8 | 5609-5647 | 6 |
| J.9 | 5648-5682 | 5 |
| K intro, K.1 | 5683-5716 | 3 |
| K.2 | 5717-5738 | 2 |
| K.3 | 5739-5782 | 8 |
| K.4 | 5783-5799 | 2 |
| K.5 | 5800-5813 | 3 |
| K.6 | 5814-5877 | 5 |
| K.7 | 5878-5896 | 3 |
| K.8 | 5897-5904 | 2 |
| K.9 | 5905-5924 | 2 |
| K.10-K.11 | 5925-5984 | 3 |
| L intro, L.1 | 5985-6023 | 5 |
| L.2 | 6024-6090 | 10 |
| L.3 (incl. example TOML) | 6091-6240 | 4 |
| L.4 | 6241-6299 | 8 |
| L.5 | 6300-6418 | 12 |
| L.6.1-L.6.2 | 6419-6449 | 3 |
| L.6.3 | 6450-6470 | 3 |
| L.6.4 | 6471-6499 | 3 |
| L.6.5 | 6500-6523 | 2 |
| L.6.6 | 6524-6547 | 2 |
| L.7 | 6548-6571 | 4 |
| M intro, M.1 | 6572-6585 | 2 |
| M.1.1 | 6586-6639 | 9 |
| M.1.2 | 6640-6667 | 4 |
| M.1.3 | 6668-6714 | 7 |
| M.1.4 | 6715-6741 | 5 |
| M.1.5 | 6742-6769 | 5 |
| M.1.6 | 6770-6785 | 3 |

## Totals per kind
| kind | count |
|---|---|
| INVAR | 156 |
| ASSUME | 72 |
| SETTLED | 68 |
| PLATFORM | 62 |
| LIMIT | 47 |
| DRIFT | 38 |
| MIRROR | 28 |
| RISK | 15 |
| WORKAROUND | 8 |
| TODO | 5 |
| OPENQ | 3 |
| SUPPRESS | 1 |
| **total** | **503** |

## Top 10
1. DRIFT F.1:3439-3444 vs L.4:6286-6288: the owner's "no `__import__`/`importlib` anywhere" rule is broken at 9+ sites (`digital_twin/run_generic_integration.py:356`, four `tests/` scenario helpers, `buildgen/validate.py:6,194-197`), and L.4 documents one of them. Frozen-set soundness (L.2:6079-6082) rests on this rule.
2. DRIFT I.6:5184-5195 and 5236-5255: the body-cap exposure maths (4 × 2048) and the whole W5 reset analysis still assume `max_connections = 4`. It is 6 now (related REST.S11).
3. DRIFT J.7:5555-5556: says `digital_twin/machine.py` "has no `UART` at all today". Four lines later the doc says both models exist, and `UARTLink` is at `digital_twin/machine.py:481-488`.
4. DRIFT G.2:4234-4236 vs L.3:6223: G.2 still prescribes a `_WIRING: "WiringSchema"` Python tuple, but `src/` only has `# @wiring` comment tags.
5. INVAR F.5.7:3869-3875: `asy_uart_driver.UART.init()` must construct `machine.UART(...)`, not re-`init()`, or rp2's heap gets corrupted. Only a comment and a hardware injector guard this.
6. INVAR/DRIFT F.5.8:3905-3926 and F.5.9:4037-4042: the claims "every read clamped", "all seven paths guarded" and "the only deadline-less wait is `uart_listen`" are contested by BUS.S05 and BUS.S06 (readline paths, `_write_all`).
7. RISK F.2:3624-3644: the accepted deferred-flush power-loss window, and the related DRIFT with CLAUDE.md, which still says "structurally cannot have a write in flight". The "single scheduler tick" size is unmeasured. M.1.5:6746-6749 depends on the same REST-only write premise (SENS.S24).
8. LIMIT I.3:4922-4933: `NTP_Host`'s settled 1,024-character bound produces a ~1,026 B piece. That is outside the 256 B bound, only argued, never measured, and would not fit at `max_connections` 7.
9. INVAR J.6:5516-5524: "must be constructed with a single-digit `poll_wait_ms`" has no enforcement (buildgen checks only the floors). J.5/J.6's Class A constants and the C-side re-verification obligation (5335-5336) have no reachable executor.
10. DRIFT F.5.6:3832 ("21 `const()` files", 25 now), F.1:3512-3515 (the const-attribute claim conflicts with upstream docs) and F.5.3:3778-3780 ("hardware" sqrt on a Cortex-M0+). These are PLATFORM facts that need re-checking against source at 1.29.0.
