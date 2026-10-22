# A-C review fold: brief (lead, 2026-10-05)

Folds every owner answer from the A-C review into the merged changes (`audit/consolidation/M_*.md`), so that the
work order regenerated from them (`audit/sweeps/ac_order.py --write`) carries them. Sources, in force order (the most
recent owner decision wins):

- `PROJECT_AUDIT_PLAN.md` section 3.2 rows **OR136-OR143** with their `.a` integrations (read each in full).
- `audit/actions/FOLD_ANSWERS.md`: the 68 significant/moderate decisions with the owner's status and note.
- `audit/review/routine_merge.json` `outcome` (7 routine settlements that change a first proposal) and
  `audit/actions/AC_NOTES.md` item 52 (the owed list, incl. the d-t27 test value).
- The register (`audit/pass2/*.md`) is already updated for all of these; read the named requirement when in doubt.

## Rules for every fold agent

1. **Edit only your own M files.** Never edit another agent's files, the register, the plan, AC_NOTES or the order.
2. **Amend in place** where an existing change carries the point: rewrite its Change text to the new end state, keep
   its M-ID, add the source to From (`OR136.a (1)` style, "(A-C review fold)"), and adjust Site/Unit/Depends/Blast as
   needed. A constituent the owner dropped is marked non-live in From with the parser's words (`A.U3.04 dropped
   (OR140.a (7))`); a change left with no live constituent and no new content gets Unit `— (no step; dropped by
   OR1xx.a (n))`.
3. **Add a new change** only where no existing change in your files carries the point. Number it after the file's
   highest M-ID. Slots exactly as the file's other changes: From, Site, Change, Resolved, Unit, Depends, Blast carried
   by, Kind. Put it under the section heading of its site file (add a heading if the file is new).
4. **Unit**: use the unit this brief names for the item, or, for an amended change, keep its existing staging and add
   the new part as a named stage. A part must never land before what it needs, and **every unit closes green on the
   full gate** (unit tier at both GC stages, the twin on every device, the web tier): a product change that the
   unit fakes, twin fakes or existing tests must follow lands with them in the same unit.
5. **Cross-file Depends** on a change another agent adds: write the token `[fold Fnn M_FILE]` (e.g.
   `[fold F21 M_SRC_NET]`); the lead replaces it with the real M-ID. Depends on existing M-IDs are written normally.
6. **Permanent text** a Change specifies (code comments, docs, SPEC, CLAUDE.md, README) never cites an audit ID (no
   OR/G/R/M/A IDs, no "A-C review"); decisions carry `(owner, YYYY-MM-DD)` or `(agent, YYYY-MM-DD)`.
   **Tag form:** for each of the 45 decisions with status ok in FOLD_ANSWERS.md, where a change writes that
   decision's permanent tag, the tag becomes `(agent, <date>; owner-reviewed, 2026-10-02)` (an existing owner tag
   stays as is). For the 23 answered with change/ask, the owner's ruling replaces the text and its tag is
   `(owner, 2026-10-02)`; OR141-OR143 rulings are `(owner, 2026-10-05)`.
7. **Facts**: datasheets in `datasheets/`, MicroPython v1.29.0 source (fetch raw files from
   `https://raw.githubusercontent.com/micropython/micropython/v1.29.0/<path>` when you need a line), current code at
   HEAD. Never read `arduino/`; never edit `ext/`; the legacy tree is reference only.
8. **Ledger**: append to each of your M files a section `## A-C review fold (2026-10-05)` with a table
   `| Fnn | M-ID(s) | action |`, action one of `amended`, `added`, `dropped`, `tag`, `none in this file`. Every Fnn
   below appears in every one of your files' ledgers (most as `none in this file`). Then report to the lead:
   new M-IDs per item, every `[fold …]` token you wrote, and anything you could not settle (with the reason).
9. Accuracy over speed. Read the full text of every change you amend. Do not invent behaviour beyond the sources;
   where a source leaves an execution detail open, the Change says what is decided and names the open detail as
   "decided at execution, with its reason recorded".

## Items

Units: U3 log rule, U10 cross-cutting contracts, U11 core (`config_manager`, `base_classes`, `system_service`), U12
algorithms, U13 bus layer (I2C/SPI/UART driver), U15 sensors, U16 FRAM, U17 UART protocol, U18 network, U19 REST,
U20 buildgen and system commands, U21 toolchain/overrides, U23 website, U24 test tiers, U25 twin, U26 hardware tiers,
U27 scripts, U28 CI, U30 memory, U31 timing, U32 parity/runbook, U35 test campaign, U36 docs pass, U37 close, C
hardware rounds.

### Owner rows OR136-OR139

- **F01 (OR136.a)** A genuinely absent config file (open fails ENOENT) is written once at that boot with the schema
  defaults through the compare-before-write path; unreadable/corrupt never overwritten; bad/missing/unknown key: one
  repair write per boot; command-only schema has no file. Unit U11 (M.SRC_CORE.043/.047 and their test carriers).
  Also: SPEC C.7.3, CLAUDE.md wear and flash-write wording, the Reset-to-defaults text ("after the reboot each file is
  written once with its defaults"), and every L1-L4 test or doc asserting "no write on a fresh filesystem" (it now
  expects exactly one write per file on a fresh filesystem; on hardware this write is a prerequisite, not the write
  under test, so it stays unmarked by `persistence_write`).
- **F02 (OR137.a + FOLD_ANSWERS status-fields note)** `HTTPDropped` = drops in the last 24 h: a reusable hourly window
  counter primitive (24 int bins allocated once at construction, lazy advance from `SysUptime` seconds, bins capped at
  `COUNTER_CAP`, sum capped, `reset()`), beside the other shared counters in `base_classes.py`, entered in SPEC Part G's
  catalog; the webserver's drop path increments it, `get_dropped_count()` returns the sum, `ResetErrors` clears it;
  each drop still traces once; catalog description "in the last 24 hours, hourly resolution". Unit U19 (the primitive
  lands with its first user). Tests: driven-clock unit tests (bin shift, gap ≥ 1 day, cap, reset, zero allocation per
  drop/read) in U19; twin/bench HTTPDropped assertions adjusted where they assume a monotonic total.
- **F03 (OR138.a)** `/status` `ConfigFaults`: names of modules whose config file existed at this boot but was
  unreadable or damaged; fixed at the end of the boot setup batch; bounded by the build's config stores; listed for
  the rest of the boot even after repair. Reset to defaults deletes every schema-backed config file without reading it,
  regardless of readable state; a failed delete logs and answers "Failed". Units: `ConfigManager` fault state U11;
  `/status` generated block and the delete path U20 (system-command code lands in U20); website row U23; tests L0-L2 in
  the same units; SPEC A.8/C.7.3.
- **F04 (OR139.a)** Rollover round on a tick-offset test image: a test-only define applied by
  `toolchain/micropython_overrides.py` (`mp_hal_ticks_ms()` returns time since boot + 2**32 ms − 15 min) with its
  anchor check and a refusal for any release build carrying it (U21); the build info names the override (U21/U27, where
  build info is produced); the rollover runner (M.SCR.074, U27) flashes the test image and polls ~2 h; M.PROC.041 (R6)
  becomes a ~2 h round inside session 1 after R5 and before R4 (one flash cycle, counted in the budget); hardware phase
  = two sessions; `tests_hardware/README.md`, SPEC B.14 and E.6 updated; driven-clock proofs stay.

### OR140.a items (owner notes on the page)

- **F05 (1)** Bench AP password: a throwaway password used once, passed plainly (env var to nmcli on the command line
  is acceptable); no interactive-mode workaround, no known-limitation fallback; still never committed (A.U21.19).
- **F06 (2)** The console-starvation bench test runs only behind the persistence-write flag (M.HW_BENCH.082, A.U19.23).
- **F07 (3)** The website asks for confirmation (browser `confirm()`) before every system command and before clearing
  the error history, as well as before the DNS fallback Clear; the API stays one command per request. U23.
- **F08 (4)** `abs_humidity()`/`rel_humidity()` stay in the maths helpers; every change removing them or their tests
  is dropped; their tests are aligned with the other helpers' (shape, vectors, edge cases) and the helpers follow the
  project's no-clamp rule. U12.
- **F09 (5)** LED: internal notification requests wait then queue (bounded by number and rate); external REST LED
  commands are refused while busy, and the refusal message tells the caller to retry later. Check the merged text says
  this; tag owner-reviewed.
- **F10 (6)** The old work-in-progress folder's code counts as reference for the owner's intent unless something states
  otherwise (doc wording only, G9/R02).
- **F11 (7)** "One entry per fault" is dropped: every layer that meets a fault keeps its own persisted entry, as today.
  A.U3.04 and every carrier of it (code, tests, `test_one_entry_per_event.py`-style checks, docs) are dropped or reverted
  to the per-layer rule; keep only parts of U3 that do not depend on it (check each).
- **F12 (8)** Reset-reason codes are clickable on the website like errno/wrnno (show their description). U23.
- **F13 (9)** A bench session that finds the board outside its standard state prints a console message saying what
  was found and which repair options exist (the opt-in repair flag among them). U26.
- **F14 (11)** The MicroPython stub version moves with every MicroPython bump, enforced by a check (A.U27.02 pin plus a
  check that the stub version's major.minor.patch equals `versions.toml`'s MicroPython ref). U27.
- **F15 (12)** No SCD30 write can happen while a system-command sequence runs: tests prove it watertight (only
  API-triggered SCD30 writes exist, and every API command is refused while the sequence runs, the SCD30 setters
  included). U20 (unit), U25 (twin).
- **F16 (13)** The twin gets a local NTP responder (replacing the planned log tolerance of A.U35.38/.39, which is
  dropped); new NTP-client unit tests use it: function, error handling, the biting cases and regressions. Units: the
  responder in U25; the client tests in U25 after it. The twin's normal-boot log check then expects NTP synced.
- **F17 (15)** The browser Back button walks back through the sensor subpages opened from the menu (history entries
  per subpage; forward works; a deep link opens its subpage). U23.
- **F18 (16)** The website shows a sensible number of decimals per value (2-3), configured in the website configuration
  and derived from the value's source (schema or tagged config, i.e. a field in the `@web` tag / schema that buildgen
  carries into the generated definitions); the API keeps full resolution. U23 (tag field, buildgen, definitions, JS).
- **F19 (17)** The Wi-Fi-off (deactivated) LED pattern respects the Wi-Fi LED setting: silent when off, the current
  pattern when turned on (M.SRC_NET.077/.100). U18.
- **F20 (18)** No build except `dev` is special; leftover WoZi-specific wording from the promotion ("WoZi is the
  exemplary/base variant", "never flashed", owner's WoZi operation in the runbook, etc.) is removed from the docs and
  replaced by the general rule (all normal builds alike, dev the contained exception). U36 (docs), plus any test or
  tooling text that singles WoZi out without a technical reason.
- **F21 (status ok/ask tags)** Tag form per rule 6 for all 68 decisions where your files write their permanent tag.

### OR141-OR143 (2026-10-05)

- **F22 (OR141.a (1))** `bench` and `hardware_family` stay in the device files' `[device]` section; checked by the
  build, never emitted. Confirm the merged changes say so; nothing else.
- **F23 (OR141.a (2), OR142.a)** Dynamic-import ban: all code the project writes, generates or vendors into an image
  (`src/`, `ext/`, generated boot/device/website modules) has none — zero at HEAD in all six devices; the check
  enforces it per image. SPEC F.1 lists by name the host/test exceptions (`tests_scripts/_script_loader.py`,
  `tests_scripts/conftest.py`, `tests_scripts/test_buildgen_validate.py`, `tests_scripts/test_js_coverage_report_dir.py`,
  `buildgen/validate.py`, `digital_twin/run_generic_integration.py`, `tests/_boot_contiguity_probe.py`,
  `tests/_digital_twin_construction_scenarios.py`, `tests/_sensortask_scenarios.py`,
  `tests/_webserver_concurrency_scenarios.py`, `tests/test_asy_isl29125_driver.py`, `ext/freezefs/ffsextract.py`) and
  records MicroPython's two bundled sites as platform facts (`extmod/asyncio/__init__.py:29` lazy loader;
  micropython-lib `dht.py:14`), re-read at each version bump. Every change that **rewrites** one of
  those loaders to remove its dynamic import is dropped (the function-level-import moves are unaffected). The import
  check fails on an unlisted site. U10.
- **F24 (OR141.a (3))** `src/voc_algorithm.py` stays literal: upstream names, casing and order; the one named exception
  to the naming rules and to the member-ordering rule (D.15); only the class other modules import follows the scheme.
  Every change reordering or renaming inside it is dropped; D.15 and the naming Part name it. U10/U12.
- **F25 (OR141.a (4)) UART DMA receive ring.** Read OR141.a (4) in full. Parts and units:
  - U13: `asy_uart_driver.py` receive path — a DMA channel paced by the RX DREQ into a naturally aligned power-of-two
    ring (ring on the write address); after every init clear RXIM/RTIM in UARTIMSC and set RXDMAE in UARTDMACR; never
    call receive-side `any()`/`read()`/`readinto()`/poll; `machine.UART` rxbuf at its minimum; progress from TRANS_COUNT
    only (RP2040-E12); a chained channel reloads the count (≤ 2**30 − 1, no big-int read); fill level by modular
    difference; lap → handled as the receive overrun; `ready()` keeps its yield and rates, reading the fill level; reads
    copy by index into the existing frame buffer (no slices, no allocation); the ring allocated once in `setup()` (a
    unit of the one-time setup list, so the I.4(f.1) placement reset applies, OR143.a (5)), held for life, never
    reallocated by a restart. Unit fakes (`tests/machine.py` or a `tests/rp2.py`: a time-driven DMA + UART register
    model) and twin fakes (`digital_twin/`: same, so dev's twin boots) land in U13 with it. Unit tests in U13: count
    reload and modular wrap, a frame split across the ring end, lap → overrun, mask cleared after every init,
    refusals, zero allocation per read at `gc.threshold(-1)`; hammering (thousands of back-to-back transactions at
    line rate, ring at its fill boundary, random consumer stalls within and beyond the bound).
  - U17: `asy_uart_comm.py` ring-size floor (the larger of today's floors and the stop-and-wait bytes during the longest
    synchronous flash write, rounded up to a power of two; refused like `rxbuf`), lap as J.7 receive overrun; UART
    changelog row "no C impact" (Python-internal).
  - U25: twin flash-write stall (the twin's config flush stalls the loop for the datasheet erase time) and the
    concurrent-load test (both dev links + webserver hammer + FRAM writes + config PUTs, both GC stages, zero
    MemoryError).
  - U26 (written) / C (run): a dev device script for the interrupts-off sweep without a flash write
    (`machine.disable_irq()` + busy-wait on `time.ticks_us()` for 3 ms, 45 ms, 400 ms and one beyond the bound, while
    the other UART streams frames fed by its own DREQ-paced TX DMA over the crossover jumper; every in-bound frame
    intact, UARTRSR OE clear, the over-bound window read as an overrun); a soft reset during traffic; the heap cost and
    largest free block before/after; one one-time run of the old interrupt-driven path showing byte loss (not a
    permanent control arm); an optional real config write during traffic behind `--allow-persistence-writes`. Add its
    C.md-style round row to the hardware changes (R1-type, session 1).
  - SPEC J.6/J.7, F.5.8/F.5.9 (the receive path), I (ring heap entry), U36 or the unit that changes the code (docs
    follow the merge's convention). A.U31.01's `stall.flash_program` row and A.U31 open point 2: the UART consumer is no
    longer crossed (the ring absorbs it); amend the carriers.
- **F26 (OR141.a (5))** The five note replies: hand-run rows (M.PROC.038) keep three one-time measurements (read time
  per driver over 100 reads, the longest LED ramp, recovery-step failure counts from the default run) and drop two (the
  NTP-outage watch — covered by the twin NTP responder — and the image without the 100 ms hotspot settle; the settle
  stays); the idle poll rate 100 ms stays with its measurement owed (twin and bench; add the measurement where the
  idle-rate change lands, A.U18.05); the build date is a build input: real builds stamp their UTC build time into the
  build info, the reproducibility check builds twice with one fixed date and compares everything else byte for byte,
  and a check proves changing only the date changes only that line (M.SCR.066 and its tests).
- **F27 (OR143.a)** UART chunking and receive cap. U17: `UARTComm` constructor args `chunk_bytes` (reasoned default,
  modelled on `WebserverService`'s) and `max_transfer_bytes` (default); a train with no caller destination
  (`_accept_set()` don't-care, `_get_unlocked()` with `exp_size=None`) is assembled in pieces ≤ `chunk_bytes` held in a
  small shared piece primitive (Part G first; the webserver's `_PieceWriter` is the model), caller-supplied
  destinations unchanged; a declared size over `max_transfer_bytes` is refused before any allocation via the withheld
  ACK and logged once; the caught-`MemoryError` sites at those allocations go; UART changelog Class A ("must be
  mirrored in C", receiver-only). U13: `readline_until_complete()` capped, no growth by concatenation, over-cap →
  discard the line, return None, log. U20: the cap and the ring size declared together in the device TOML and
  checked together by buildgen. Tests (unit, hammering, concurrent load, a bench maximum-size transfer) in the same
  units / U25 / C. BACKLOG's owner question for it (M.DOCS.067 entry 1) is removed; the parked "uart-chunking" item is
  work.

### Routine settlements that change a first proposal (routine_merge.json `outcome`, AC_NOTES 52)

- **F28 (initialized-flags)** `self.initialized` only where product code reads it (FRAM, SPI, UART and logging
  classes); not added to `SensorReader`, `WebserverService`, `NeopixelDriver`, `NotificationService`. Amend
  M.SRC_CORE.036/.039, M.SRC_NET.119, M.SRC_SENS.023/.033, A.U10.22's check scope and the test carriers.
- **F29 (ntp-malformed-text)** NTP reply parser allocation failure logs the shared ALLOC errno 20; errno 69 stays
  "malformed" only (M.SRC_NET.049 and its tests).
- **F30 (status-ip-and-ipv4)** `/status` keeps `IPv4` only; the refactor-added `IP` key goes (M.GEN.008,
  `buildgen/definitions.py`, the hand definitions `html/definitions/*.json`, mockdata, tests, docs).
- **F31 (twin-choice-17)** A clock-jump twin file is added: with the twin NTP responder (F16) the two sync-dependent
  clock-jump cases also run in the twin, keeping their unit-level proofs. U25 after F16.
- **F32 (device-script-sleeps)** Each fixed wait in the device scripts becomes a bounded poll for the state it waits on
  where that state is readable; a named, measured delay stays only where there is nothing to read or a check would
  disturb the test (G7/R23).
- **F33 (d-t27)** M.TEST_UNIT.291's `:629` case (both copies BUSY) stays `_read() is False`, not `None`; correct its
  Resolved (D-T27) line.

## Assignment (disjoint)

- **Agent P (product + website)**: M_SRC_CORE, M_SRC_NET, M_SRC_SENS, M_GEN, M_WEB.
- **Agent T (unit tests + twin)**: M_TEST_UNIT, M_TEST_HELP, M_TWIN.
- **Agent H (tooling, scripts, hardware, process)**: M_TSC, M_TOOL, M_SCR, M_HW_BENCH, M_HW_DEV, M_PROC.
- **Agent D (docs)**: M_SPEC, M_DOCS.
