# A-L supplement — owner rows OR116-OR119 (HEAD 60b398b)

Supplement over the already-planned units U11, U16, U17, U19, U20, U23 and the in-flight U24-U26 (AC_NOTES item 27),
built from the owner rows OR116/OR116.a, OR117/OR117.a, OR118/OR118.a, OR119/OR119.a (OR119 refines OR117) and the
three owner rows that arrived while this file was written and bind it: **OR120/OR120.a** (watchdog ownership passes to
the shutdown sequence), **OR121/OR121.a** (the two commands in the existing API and website style; OR117.a (3)'s
confirmation step overtaken) and **OR122/OR122.a** (every test type at every reachable level; no dialog and none
proposed; the exact action word is the safeguard). Register blocks: LEAD/R31 and LEAD/R32 (`audit/pass2/LEAD.md`,
R32 as updated for OR120-OR122), read with LEAD/R28 (UART four-tier hazard coverage) and `SUPP_recovery.md` (the
recovery ladder).

Code sites were read at `cde3bb0`; `git diff --stat cde3bb0 60b398b -- . ':!audit' ':!PROJECT_AUDIT_PLAN.md'` is
empty, so every line number below holds at `60b398b`. Primary sources: MicroPython v1.29.0 in the scratchpad `mp/`
(`extmod/asyncio/task.py`, `stream.py`, `core.py`), datasheet text `dstxt/` (MB85RS2MTA, MB85RS64V, W25Q16JV).
Earlier actions are referenced, never repeated; section C lists every earlier action at the same sites with its
verdict. Text an action writes into a permanent file carries actor tags only; audit IDs sit in `[src: …]` notes the
executor never writes (brief rule 6). Numbers in planned code are catalog names (A.U2.01), never literals.

## Design (B): the one controlled shutdown sequence

Settled here once and used by A.S0930.09-A.S0930.30 (agent, 2026-09-30, from OR117.a, OR119.a, OR120.a, OR121.a,
OR122.a and the code at HEAD as U11/U16/U20 reshape it). Names below are the planned ones.

**Built on, not beside, the earlier plans.** U11 already turns `_reboot()` into one awaited path (A.U11.03: record →
flush every config store → pause FRAM → arm the one-shot reset `_RESET_DELAY` later, `_reset_armed` so a repeat never
re-arms; arm failure → `_force_watchdog_starve`), gives `ConfigManager` `close_writes()` (A.U11.04) and the
reset-reason record in `mem_backup()` region 0 (A.U11.05). U20 splits the supervisor into `start_tasks()` (stores
`self._tasks`/`self._task_starters`) and `supervise_tasks()` (A.U20.06). U16 removes `override_pause` (A.U16.19), and
SUPP_recovery adds the FRAM manager's own supervised task (A.U16.R03). The sequence ends in U11's `_reboot()`; it adds
no second reset path (the `machine.reset()` site invariant, `tests/test_reset_call_site_invariant.py:14-27`, holds).

**Action words** (OR122.a (2): the exact word is the safeguard; OR121.a (1): "two more `SystemCmd` enum values", same
envelope and results). `"resetconfig"` (label "Reset to defaults") and `"erasefram"` (label "Erase FRAM"). Lowercase,
no separator, like `"mempause"`/`"bootloader"` (`asy_webserver_service.py:95`). Why these words: each names its object
— `resetconfig` resets the configuration files and nothing else, so a word like "factoryreset" would overstate it (the
FRAM error logs and the SCD30's NVM survive, OR117.a (1)); `erasefram` names the store it destroys. Neither is a prefix
of the other or of an existing value, so no near-miss of one is another command. The dispatch stays the whole-string
membership test `cmd not in _SYSTEM_CMDS` (`asy_webserver_service.py:507`): no alias, prefix, case folding or number.

**Gate (S0, inside the request, before the reply).** `SystemService.reset_to_defaults()` / `erase_fram()` run under
one `self._command_lock` (`asyncio.Lock`, fixed size), so two commands never interleave their checks:
1. a shutdown already under way → answer `True` for the same purpose (idempotent, nothing new started), `False` for
   the other purpose;
2. `self._reset_armed` (U11: a reboot or bootloader reset is armed) → `False` — the armed reset would cut the
   sequence;
3. `self._shutdown = purpose` is set before any await, so from here `reboot_system()`, `reboot_bootloader()` and
   `pause_permanent_storage()` answer `False` ("Failed") and the supervisor stops restarting and escalating;
4. preflight — `resetconfig`: at least one config store resolved; `erasefram`: a FRAM manager exists, its chip is
   initialised and not write-protected (`await self._storage.erase_ready()`); a failed preflight clears
   `self._shutdown` and answers `False` with nothing changed;
5. `self._shutdown_task = asyncio.create_task(self._shutdown_sequence(purpose))` — a `MemoryError` clears
   `self._shutdown`, answers `False`, nothing changed;
6. the watchdog latch `self._feed_owned = True` (one-way): from here `feed_watchdog()` is a no-op for every caller
   (the supervisor pass in progress, the boot batch's generated feeds `codegen.py:465` / A.U11.10's `run_setups()`);
   one console line; answer `True` → `"Valid"`. The reply is written by the request's own connection task; nothing the
   sequence does cancels a connection task, and the reset fires at the earliest `_RESET_DELAY` (4 s) after S6.
   The latch is set at acceptance, before the supervisor is proven stopped — stricter than OR120.a (1)'s "from that
   moment": the supervisor pass still running between acceptance and its park cannot feed either.

**Sequence** (the task created in S0; every feed is the sequence's own `self._own_feed()`, which bypasses the latch
but honours `_force_watchdog_starve`; one feed after each bounded unit of work; no step has a timeout that moves on —
a hung unit is never fed and the watchdog resets the unit, OR120.a (2)):

| step | what | feeds | logged (once) |
|---|---|---|---|
| S1 takeover | own feed; `await self._supervisor_parked.wait()` (the supervisor loop parks at the top of its next pass once `_shutdown` is set); `self._supervisor_task.cancel()`; `await` it (catch `CancelledError`); proven by `self._supervisor_task.done()` — if not done, the sequence returns without another feed | before and after | "Shutdown: supervisor stopped, the watchdog is fed by the shutdown alone" |
| S2 config stores | `close_writes()` on every store, then per store `flush_pending()` (A.S0930.16: the pending flush read under `config_lock`) through U11's `_flush_config_stores()` wrapper, whose failure entry still persists (FRAM open) | per store | "Shutdown: config writes closed and flushed" |
| S3 FRAM | `storage_timer.deinit()` (a `mempause` auto-unpause cannot fire mid-sequence); `await self._storage.quiesce(self._own_feed)` — pause, then each chunk's `_op_lock` taken once (`wait_idle()`), so every operation already past its pause check finishes both blocks and every later one refuses at entry | per chunk | "Shutdown: FRAM writes closed" |
| S4 tasks | cancel every entry of `self._tasks` not done; then `await` each (catch `asyncio.CancelledError` and `Exception`) | per task | "Shutdown: all tasks stopped" |
| S5 purpose | `resetconfig`: per store `await store.delete_file()`; `erasefram`: `await self._storage.erase_chip(self._own_feed)` (A.S0930.17) | per file / per chunk and per 256-byte unit | "Shutdown: <purpose> done" or "… incomplete" |
| S6 reboot | own feed; `await self._reboot(code, "Reboot after <purpose>", system_reset)` — U11's path (record → flush (no-op, stores closed) → pause (already) → arm); no feed after it | once, before `_reboot()` | `_reboot()`'s own line |

`code` is `_RR_CONFIG_RESET` (7) / `_RR_FRAM_ERASED` (8), or `_RR_COMMAND_INCOMPLETE` (9) when a flush raised, a file
could not be deleted or the erase stopped early (A.S0930.15). After S6 nothing feeds: the reset fires within
`_RESET_DELAY` of the last own feed (4 s + `_reboot()`'s own few ms, under the 8000 ms `WDT`, `codegen.py:381`); an
un-armable reset timer sets `_force_watchdog_starve`, and a dropped soft Timer callback (SPEC F.1) leaves the reset task
waiting — both end in a watchdog reset, never in a fed hang. This is how OR120.a (2) reconciles with `_reboot()`'s arm
and its starve fallback: the sequence's last feed precedes the arm, and no feed site exists after it.

**Order rationale.** S1 first: ownership must pass before anything that can hang, or the supervisor would feed through
a hung step (OR120). S2 before S3: a failed flush's persisted entry still reaches FRAM (U11's own record → flush →
pause order). S3 before S4: cancelling a task inside a chunk write would tear that chunk (the cancel lands at the
`await asyncio.sleep(0)` inside `_write_chunk()`, `asy_fram_manager.py:276, 284`); after S3 no task can be inside a
chunk operation beyond its pause check. S4 before S5: nothing but the sequence runs storage code while the purpose is
applied. Cancelling the webserver's `_run()` closes its listening socket (DONE-AT-HEAD, A.S0930.18), so no new request
is accepted after S4; connection tasks already accepted run to their end and meet closed stores.

**Why the supervisor parks before it is cancelled.** The supervisor loop persists log entries (`system_service.py:
234, 238-240, 251`), i.e. it can be inside a chunk write at any moment; cancelled there, it would tear SYSTEM's chunk.
Its park point is the top of a pass (`if self._shutdown: self._supervisor_parked.set(); await self._never.wait()`),
where it holds nothing, so the cancel lands on a wait. Worst case to park: one `_TASK_CHECK_TIME` sleep (2 s,
`system_service.py:44`) plus one pass. The supervisor runs as its own task (`self._supervisor_task`, created by
`supervise_tasks()`, which then waits on `self._never` itself): `main()` must never return (A.U11.03 point 5), and
`main()` cannot be cancelled without ending `asyncio.run()`.

**States (OR119.a (1)) and how each stays correct.**

| state when the command arrives | handling |
|---|---|
| boot `setup()` batch | cannot happen: the webserver's task is started last (`codegen.py:680-686`: `webserver` closes the `_collect_task_starters()` tuple, `:683`) and only after `run_setups()` returned (A.U20.06 order), so no request is served during the batch; its feeds (`codegen.py:465` / `run_setups()`) go through `feed_watchdog()` and are latched anyway |
| boot after the batch (`start_timers()`, first NTP sync) | accepted; S1 waits until `supervise_tasks()` has created the supervisor task and it parked at its first pass (timer sequencing ≈ `_TIMER_BASE_PERIOD` 1000 ms, `system_service.py:43, 159`); nothing feeds meanwhile, so a boot that never reaches the supervisor ends in a watchdog reset |
| a config flush in flight | S2: `close_writes()` refuses new `write_config()` (re-checked inside the lock, A.S0930.16), a `write_config()` already inside the lock finishes staging, and `flush_pending()` awaits the flush task read under the lock — every write answered "Valid" before the close is on flash |
| a FRAM chunk write in flight | S3: pause first, then each chunk's `_op_lock` once — the in-flight write completes both blocks; S4's cancellations come after; the erase touches the chip only after S3 |
| inside a bus session | S4's cancel lands at an await; `async with` exits release the bus lock and deassert CS (`SPIDevice.__aexit__()`/`session_end()`, `asy_spi_driver.py:146-150, 167-178`; I2C the same shape); no transfer is interrupted (rp2 transfers are synchronous, G4/R22); FRAM is drained before; a sensor left mid-command is set up again by its driver at the next boot, after the boot bus clear (OR113.a (1)) |
| storage paused (`mempause`) | S3 deinit's the auto-unpause timer and pauses again (idempotent); the erase writes beneath the pause at driver level; a flush failure in S2 reaches the console only (the operator's own pause), accepted |
| a reboot or bootloader reset armed | refused at S0 ("Failed"), nothing changed; the armed reset proceeds |
| reboot, bootloader or mempause during the sequence | refused ("Failed"); supervisor escalation is suppressed once `_shutdown` is set (the sequence reboots anyway) |
| the other command under way | "Failed"; the same command: "Valid", nothing new started |
| two commands at once | `_command_lock` serialises S0; the second sees the first's outcome |
| a PUT on a connection accepted before S4 | a config write meets a closed store → "Failed"; `ResetErrors` meets paused FRAM → "Failed" (A.U11.31); an SCD30 field reaches the chip as an ordinary accepted write — OR119.a (2) closes the flash filesystem and FRAM, which the SCD30's NVM is neither of (agent reading, 2026-09-30); `lightCmdLED`/`PauseTime` touch RAM only |
| any step hangs | no feed; the watchdog resets the unit ≤ 8000 ms after the last own feed; the next boot reads `ResetReason` 2 (no record) and a partly applied state, which is the power-loss case below |

**Timing per step at the worst-case chip and bus** (OR120.a (2)). The FRAM runs at the `SPIDevice` default of
1,000,000 Hz: `FRAM_SPI` builds `SPIDevice(spi_bus, spi_cs)` with no baud (`asy_fram_driver.py:110`), default
`baudrate: int = 1000000` (`asy_spi_driver.py:109`); no TOML key sets it (`devices/*.toml` `[bus.spi0]` has pins only),
so 1 MHz is the one and worst speed (both chips allow far more: MB85RS2MTA 40 MHz, MB85RS64V 20 MHz, `dstxt/fram__…:24`).
FRAM needs no write-cycle wait: a byte is written when its 8 bits are in (MB85RS2MTA `dstxt/…:301-306`). One 256-byte
erase unit through `FRAM_SPI._write()` (`asy_fram_driver.py:222-231`) is five CS sessions: WREN (1 byte), RDSR (2),
WRITE (opcode + 3 address bytes on the 2 Mbit part, `_ADDR_BUF_24BIT`, 2 on the 64 Kbit part, + 256 data), WRDI (1),
RDSR (2) = 266 / 265 bytes = 2.13 / 2.12 ms of clock at 8 µs per byte. Whole chip: MB85RS2MTA 262,144 B = 1,024 units
= 2.18 s of clock; MB85RS64V 8,192 B = 32 units = 68 ms. Pass 1 per chunk: two blocks × two one-byte status writes of
11 wire bytes = 44 bytes = 0.35 ms. Each unit adds five sessions' `spi.init()` reconfigure and 2 × 2 µs CS settle
(`asy_spi_driver.py:130-151`) plus interpreter overhead — not derivable from source; measured in phase C
(A.S0930.29), and even at ten times the clock time a unit stays under 25 ms. Longest single step between two feeds:
S1's park wait, ≤ 2 s + one supervisor pass. Flash-filesystem steps (one flush, one delete): one littlefs operation
each — page programs `tPP` ≤ 3 ms and 4 KB sector erases `tSE` ≤ 400 ms (W25Q16JV, `dstxt/pico_w__Winbond…:3104-3105`);
how many erases one littlefs commit can take (metadata compaction) is not derived here, and phase C measures the
worst. Every step is therefore at least one order of magnitude under 8000 ms; the whole-chip erase is 1,024 fed steps,
not one.

**Erase pattern: 0x00, proven never to validate as a chunk.**
1. *Status gate.* A block is `[data + CRC][status 1][status 2]` (`asy_fram_manager.py:43, 65, 255`). Every read
   checks both status bytes first (`_read_chunk()` → `_handle_status_bytes(check_idle=True)`, `:299`; `_set_check_sb()`
   `:235-239`): `0x00` is `_STATUS_UNINIT` (`:29`), so the block is "uninitialised" and `_read_chunk()` returns
   `(True, 0)` before any data or CRC is read (`:306-308`); `_read_into()` calls a block valid only when
   `valid_bytes == self.size` (`:206`) and `get_chunk()` refuses a size of 0 (`:648-650`), so the block is never valid.
   Two blank blocks → `_read()` returns `False` with console-only lines (`:138-148`) and the owner re-initialises
   (`PrintLogHistoryStore.setup()`: `_read() or _write()`, `print_log.py:273-279`; SGP40 restores nothing) — the
   factory-new path, no error entry.
2. *CRC gate, independent of the first.* Every product chunk has a CRC with a non-zero init: CRC8 init 0xFF (loggers,
   `print_log.py:238`), CRC32 init 0xFFFFFFFF (SGP40 backup, `asy_sgp40_driver.py:181-183`); `crc_checks.py:4, 29-33`.
   A block validates only when the register ends at 0 over data + CRC (`check_inc()` `:104`). Over an all-zero span the
   register evolves r → r·x⁸ mod P; each product polynomial (0x31, 0x1021, 0x04C11DB7) has constant term 1, so x is
   invertible mod P and a non-zero register never reaches 0. An all-zero block therefore fails the CRC even if its
   status bytes read idle. (All-zero would pass a zero-init CRC with no final XOR, the case OR117.a (2) asked to check —
   `crc_checks.py` has none — or a `CRC_Pass` chunk, which no product code allocates: `get_chunk(crc=None)` defaults to
   `CRC_Pass`, `:651`, but both product callers pass a CRC.) A.S0930.20 pins "every product chunk has a non-zero-init
   CRC" so a future `CRC_Pass` chunk is caught.
3. *Why not 0xFF.* A status byte 0xFF is neither idle nor blank: every block would log "Read status byte is not 1"
   (`:236-238`) at the next boot — error noise at the moment the unit is meant to start clean. 0x00 is the chip's own
   blank state and the manager's own clear pattern (`_clear_chunk()`, `:360-376`).
4. *Torn states.* Pass 1 marks both status bytes of every allocated block 0x00 (`chunk.invalidate()`, the same
   status-first order `_clear_chunk()` uses) before pass 2 writes any data. A cut inside pass 1 leaves each chunk
   either untouched (old, valid, consistent), with one block blank (the other copy restores it: `:137-157`), or with
   one block's status pair mixed 0x00/0x01 ("inconsistent", `:265-267`, invalid; the other copy decides). A cut inside
   pass 2 (units ascend, each a single WRITE whose bytes land one by one, `dstxt/fram__MB85RS2MTA…:301-306`) finds
   every allocated block already blank, so no partly zeroed block can read as valid, whatever the CRC width —
   without pass 1 a cut mid-unit could leave a data prefix zeroed under an idle status and an old CRC8, which
   validates with probability 2⁻⁸.

**Power loss at each step** (OR119.a (4)): S0-S1 nothing written; S2 a littlefs write is atomic at close (old or new
file); S3-S4 RAM only; S5 `resetconfig` — each `os.remove()` is one littlefs operation, so an interrupted reset leaves
a subset of the files, which load (or default, A.U11.19/A.U11.20) at the next boot; S5 `erasefram` — as the torn-state
proof above: every chunk reads valid-old or blank, never torn-valid; S6 the record is RAM (`mem_backup()`), lost on a
power cut, so the next boot reads power-on (1). Proven per step at L1 (fake cut), L2 (twin process killed mid-step)
and L3 (hard reset mid-erase), A.S0930.25/27/28.

## Actions

### Part A — the UART link in both CRC modes (LEAD/R31)

**Where the CRC lives at HEAD** (settles the register's U17 clause): the CRC is a constructor argument of the bus
object, `asy_uart_driver.UART(..., crc: CRC_Base | None = None, ...)` → `self.crc = CRC_Pass() if crc is None else crc`
(`src/asy_uart_driver.py:58, 76`), which the generated module builds in its bus loop (`buildgen/codegen.py:391-397`,
no `crc=` emitted today). `UART_Comm` reads it from the bus (`asy_uart_comm.py:269, 282`) and `UartLinkExerciser`
never sees it (`asy_uart_link_driver.py:65-78` passes `uart` straight on). So the mode is wired at the bus construction
by codegen, and neither the exerciser nor the protocol module changes — no runtime switch exists or is added (OR36.a
(1), OR116.a (2)). Register fix 1.

### A.S0930.01 The build takes a per-link `crc` mode and checks it
- **Why**: LEAD/R31 — "Each `uart_link` instance takes a `crc` TOML key (none or crc16); buildgen refuses a pair whose
  ends differ, and its bus check counts the CRC length"; State "code in U20 (TOML key, buildgen pair check and
  bus-check CRC length)" ("I want both.", owner, 2026-09-30, OR116; OR116.a (2)); J.6 "agreed out of band and must
  match on both ends … nothing is negotiated" (owner, 2026-09-11).
- **Site**: `buildgen/buildspec.py:25-37` `OPTIONAL_TOML_FIELDS` (`"uart_link": ()`), new table after `:58`
  (`BUS_KIND_BY_DRIVER`); `buildgen/validate.py:58` (`_UART_LINK_ROLES`), `:381-382` (per-instance role check),
  `:255-278` `_check_uart_link_buses()` (docstring `:256-258`, `min_rxbuf` `:274`), `:538-553`
  `_check_uart_link_roles()`; `devices/dev.toml:148-154` (the link section's comment).
- **Change**: (1) `OPTIONAL_TOML_FIELDS["uart_link"] = ("crc",)` — optional, absent means `"none"`, the same
  "declared field → kwarg, absent → constructor default" shape the UART bus knobs use (`codegen.py:393-396`), so
  `dev.toml` keeps HEAD's no-CRC mode with no key (OR116.a (2)). (2) New hand-kept table in `buildspec.py` (the
  owner-kept generator table, harmonization 31) with a one-line comment "CRC mode of a uart_link end -> (crc_checks
  class, width in bytes); held equal to src/crc_checks.py by a test": `UART_CRC_MODES: dict[str, tuple[str, int]] =
  {"none": ("CRC_Pass", 0), "crc16": ("CRC16", 2)}`. (3) Per instance, beside the role check `:381`: `if spec.driver ==
  "uart_link" and spec.fields.get("crc", "none") not in UART_CRC_MODES: raise BuildError(model.device,
  f"{spec.label}.crc must be one of {sorted(UART_CRC_MODES)}, got {spec.fields.get('crc')!r}", instance=spec.label,
  field="crc")` (a non-string reaches the same message). (4) `_check_uart_link_roles()`, after the one-pair count and
  A.U17.32's baud comparison: the two ends' effective modes differ → `BuildError(model.device, f"uart_link pair:
  {initiator} uses crc {a!r} and {responder} uses {b!r} - both ends of a link must agree (Part J.6: agreed out of
  band, never negotiated); state one crc mode on both", instance=<responder label>, field="crc")` (rule id and fix per
  A.U20.17's contract). (5) `_check_uart_link_buses()`: `crc_len = UART_CRC_MODES[spec.fields.get("crc",
  "none")][1]`; `min_rxbuf = max(header + payload + crc_len, …)` and the message's frame size says `{header + payload
  + crc_len}`; the docstring's "generated code wires no CRC or framing, so both add 0" → "generated code wires no
  framing (adds 0); the CRC adds the width of the link's crc mode". The timeout floor is unchanged (no CRC term,
  `asy_uart_comm.py:252-260`). (6) `dev.toml`: the link section's comment gains one line "crc (optional, per end):
  "none" (default) or "crc16"; both ends must agree (Part J.6)." — no key added.
- **Blast**: callers `validate()`/`build_model()` (`validate.py:736, 752`) · generated — (valid TOMLs unchanged) · js —
  · tests existing: `tests_scripts/test_buildgen_validate.py:1240-1384` (uart_link section, `_with_uart_pair()` without
  `crc`) hold — absent is `"none"`; `:1326-1332` (`test_every_shipped_device_passes_the_uart_link_bus_check`) holds;
  `tests_scripts/buildgen_fixtures/novel_combo.toml:142-153` holds; `tests_scripts/test_device_tomls.py` field-set
  checks (grep `ALLOWED_INSTANCE_FIELDS`) accept the new optional key; new L0 `tests_scripts/test_buildgen_validate.py`
  — `crc = "crc8"`, `crc = 16`, `crc = "CRC16"` each refused naming the legal set and `(field, instance) == ("crc",
  label)`; a pair `none`/`crc16` refused naming both labels; `crc16`/`crc16` builds; with `baudrate` 9600 and
  `poll_wait_ms` 1 (so the per-poll floor is `(9600 // 10) * 6 // 1000 = 5` and the frame floor decides) `rxbuf` 54
  refused for a crc16 pair (needs 5 + 48 + 2 = 55) and 55 builds, while a no-CRC pair builds at 53;
  `test_uart_crc_modes_match_crc_checks` — reads `src/crc_checks.py` by `ast`: each `UART_CRC_MODES` class exists and
  its `__init__`'s `super().__init__(<int>, …)` first argument equals the table's width (`CRC_Pass` 0 at `:147`,
  `CRC16` 2 at `:157`) · twin — · docs SPEC L.3 key table (A.U20.35 checks it against `buildspec.py`) gains `uart_link`
  `crc` ("none" | "crc16", default "none", both ends equal); SPEC L.5/L.6.6 validation list gains the crc legal set and
  the pair agreement; SPEC C.7.2 build-refusal sentence (A.U17.32's) gains the CRC mode; J.6 (A.S0930.08) · toml
  `devices/dev.toml` comment line only · uart — (build tooling, the changelog entry is A.S0930.07's).
- **Depends**: A.U17.32 (same function, the baud comparison it sits after), A.U17.21 (same bus-check function),
  A.U20.01 (one instance per UART bus: the mode of a bus is its one link's), A.U20.17 (error contract), A.U20.35 (L.3
  table check) — A-C merges.
- **Kind**: code | test | doc

### A.S0930.02 Generated code builds each UART bus with its link's CRC
- **Why**: LEAD/R31 — "Each `uart_link` instance takes a `crc` TOML key"; "the driver has no runtime mode switch
  (OR36)" (owner, 2026-09-26, OR36.a (1); OR116.a (2)).
- **Site**: `buildgen/codegen.py:391-397` (UART bus construction in `_emit_build_system()`),
  `_emit_header_and_imports()` `:300-310` (import block).
- **Change**: before the bus loop, `link_crc = {spec.fields["bus"]: UART_CRC_MODES[spec.fields.get("crc", "none")][0]
  for spec in instances.values() if spec.driver == "uart_link"}`; in the UART branch, when `link_crc.get(bus_id,
  "CRC_Pass") != "CRC_Pass"`, `extra_kw += f", crc={link_crc[bus_id]}()"`; the comment `:393-395` gains "crc: from the
  bus's one uart_link instance, absent for no CRC". The import block emits `from crc_checks import CRC16` (the classes
  the device's links name, sorted, de-duplicated) only when one is used. `_build_args_uart_link()` (`:230-243`) is
  unchanged: it forwards `bus`/`role`/`name_ext`/`fram`/`debug` explicitly, so `crc` never reaches the exerciser.
- **Blast**: callers — · generated a crc16 device's `build_system()` UART lines and imports; every shipped device
  unchanged (no `crc` key anywhere, `devices/*.toml`) · js — · tests existing `tests_scripts/test_buildgen_generate.py`
  (every device generates; dev's text unchanged); `tests_scripts/test_generate_sensortask_modules.py` holds; new L0
  `tests_scripts/test_buildgen_generate.py` — the bench device's TOML (the one wiring a uart_link pair, found by data,
  OR78) copied to `tmp_path` with `crc = "crc16"` added to both link instances: the generated source parses, both UART
  bus lines carry `crc=CRC16()`, the import is present, and `UartLinkExerciser(` calls carry no `crc`; the unmodified
  TOML's generated source contains no `CRC16` · twin the generated module only (the twin builds whatever codegen
  emits; the crossover wiring `buildgen/twin_wiring.py` is CRC-blind) · docs SPEC L.4 (generated construction) one
  clause "a uart_link end's CRC is passed to its bus" · toml — · uart — (changelog entry A.S0930.07).
- **Depends**: A.S0930.01; A.U20.13 (frozen set from the generated imports — `crc_checks` is already frozen through
  `asy_uart_driver`), A.U20.41 (template renames) — A-C merges.
- **Kind**: code | test

### A.S0930.03 L1: the exerciser pair runs in both CRC modes
- **Why**: LEAD/R31 — "exercised in both CRC modes (none and CRC16) at L1"; State "test in U17/U24 (L1)"; OR116.a
  "at HEAD only L1 runs both modes … confirm and extend where the exerciser itself is involved" (owner, 2026-09-30,
  OR116; OR118.a (1)).
- **Site**: `tests/test_asy_uart_link_driver.py:34-47` (`Pair`), the transfer tests `:190-240`, `:308-380`, `:485-490`.
- **Change**: DONE-AT-HEAD for the protocol layer: `tests/test_uart_comm_hazard.py` registers every `_check_*` in
  both modes (`CRC_MODES = (("nocrc", None), ("crc16", CRC16))` `:51`, `_register_both_crc_modes()` `:1279-1296`, two
  mode-specific checks by construction `:1273-1276`); `tests/test_asy_uart_comm.py:2163` runs its load arm on CRC16.
  The exerciser layer runs no-CRC only (`Pair` builds both `UART(...)` without `crc`, `:38-39`). Extend: `Pair(…,
  crc: "CrcMaker | None" = None)` passes `crc=crc() if crc else None` to both buses; the exerciser tests that move
  bytes — `test_a_get_and_a_set_both_complete_with_no_errors_counted` (`:190`), `…larger_than_one_chunk…` (`:207`),
  `test_one_sided_silence…` (`:219`), `…maximum_length_train…` (`:308`), `…many_back_to_back…` (`:339`), the two
  hammer tests (`:485`, `:489`) — become `_check_*` functions registered per mode by the same `_register_both_crc_modes()`
  shape (copied, not imported: `tests/_uart_comm_harness.py` owns the protocol-layer one). New, CRC16 only: 
  `test_a_corrupted_frame_counts_one_failure_and_the_next_transfer_succeeds_crc16` — one payload byte flipped on the
  link (`UARTLink` fault knob) during one exercise round: `failures` rises by one, the next round's `transfers` rises,
  the banner is intact (the exerciser's counters are the layer this file owns).
- **Blast**: callers — · generated — · js — · tests existing file above (names gain the `_nocrc`/`_crc16` suffix; the
  runner reports each) · twin — · docs SPEC J.7 tier map row "exerciser, both modes, L1" (A.S0930.08) · toml — · uart —.
- **Depends**: A.U17.07, A.U17.18, A.U17.29 (same file, exerciser changes), A.U24's file-level actions on
  `tests/test_asy_uart_link_driver.py` — A-C merges.
- **Kind**: test

### A.S0930.04 L2: the twin link and a generated device run in both CRC modes
- **Why**: LEAD/R31 — "L2 builds the twin pair in both modes"; State "U25 (L2)" (owner, 2026-09-30, OR116/OR118).
- **Site**: `tests/test_digital_twin_uart_link.py` (generated-graph link tests), A.U17.25's new
  `tests/test_digital_twin_uart_comm_hazard.py`/`…_field_sweep.py` (already both modes), `tests_scripts/test_digital_twin_generated_boot.py`.
- **Change**: (1) A.U17.25's two twin hazard files are both-mode by their plan (payload/field sweep in both) —
  referenced, not repeated. (2) `tests/test_digital_twin_uart_link.py` runs the generated no-CRC device only; a CRC16
  arm at the pair level: a new `_check_*` set building a `UartLinkExerciser` pair on the twin's own `machine.UART`
  fakes with `UARTLink` (real wire time) and `LinkPoller` (bounded), buses constructed with `crc=CRC16()`, at
  synchronous scope (CLAUDE.md nested-`asyncio.run()` rule) — exercise rounds complete, a mid-train corrupted byte is
  caught (failure counted, next round clean), `wrnno`/`errno` history carries only the expected codes. (3)
  `tests_scripts/test_digital_twin_generated_boot.py` gains a CRC16 boot: the bench device's TOML (found by data: the
  device with a `uart_link` pair) copied to `tmp_path` with `crc = "crc16"` on both ends, generated and booted under
  the twin exactly like the shipped devices (the generated-module path this file already takes); after boot,
  `GET /status` → `sensors.UARTLINK.Transfers` rises across two polls ≥ 3 s apart and `Failures` stays 0.
- **Blast**: callers — · generated a tmp crc16 module in the test only · js — · tests new as above; the boot test's
  per-device budget (`_BOOT_TIMEOUT_S`) holds (CRC adds 2 bytes per frame) · twin `digital_twin/run_generic_integration.py`
  crossover wiring is CRC-blind (unchanged) · docs SPEC J.7 tier map "L2 both modes" (A.S0930.08) · toml — · uart —.
  (4) The CI suite's sustained-fault cell for the link (A.U25.37: `uart_link:silent` in Run 3, per instance) runs once
  per CRC mode: `scripts/_digital_twin_ci_suite.py` gains `--device-toml PATH` (generation from a derived TOML, the
  same option A.S0930.06 gives the firmware build), and `scripts/run_digital_twin_ci.sh` runs Run 3's `uart_link` cell
  a second time on the bench device's TOML derived with `crc = "crc16"` — asserting the same outcome (every faulted
  module's E entry, then the simulated reset, A.U25.36), `would_have_triggered_count == 0`, zero `MemoryError` markers.
- **Depends**: A.S0930.02, A.U17.25; co-lands with A.U25.37 (Run 3's `uart_link:silent` vocabulary and matrix),
  A.U25.36 (Run 3's escalation assertions), A.U25.32 (per-run `--config-dir`/state paths the derived run passes),
  A.U25.48 (device from data, `--device` required) — A-C merges.
- **Kind**: test

### A.S0930.05 L3: the crossover device scripts run in both CRC modes
- **Why**: LEAD/R31 — "L3 runs a device script in the other mode over the crossover jumper"; State "U26 (L3
  script)" (owner, 2026-09-30, OR116.a (2)).
- **Site**: `tests_hardware/device_scripts/uart_crossover_exchange.py:84-87`, `uart_crossover_recovery.py:76-79`,
  `uart_link_under_concurrent_system_load.py:131-134` (each builds `asy_uart_driver.UART(0/1, …)` with no `crc`);
  `tests_hardware/flash/test_uart_crossover.py` (their wrapper).
- **Change**: each script takes `CRC_MODE` from the rendered facts dict of A.U26.44 (default `"none"`) and builds both
  buses with `crc=CRC16()` when it is `"crc16"`; its `RESULT:` line names the mode. `test_uart_crossover.py` runs each
  script once per mode (`pytest.mark.parametrize("crc_mode", ["none", "crc16"])`), both over the same jumper — no
  reflash (scripts run from RAM, `run_isolated()`); the recovery script's injected faults (A.U26.33's baud desync)
  run in both. A.U26.82's `uart_comm_hazards.py` (H1a/H1b/H2/H3 over the jumper, and under the bench's API load) takes
  the same parameter and its flash and bench wrappers run it in both modes.
- **Blast**: callers the wrapper · generated — · js — · tests the flash-tier UART file (twice the runs, each bounded
  by its existing `timeout_s`) · twin each script's twin run (A.U26.05) in both modes · docs `tests_hardware/README.md`
  UART section "each crossover script runs with no CRC and with CRC16" · toml — · uart — · hardware C (flash round).
- **Depends**: A.U26.44 (rendered dict), A.U26.33, A.U26.59 (UART script folding), A.U26.82 (the hazard script and its
  two wrappers), A.U17.25 — A-C merges.
- **Kind**: test | hardware

### A.S0930.06 L4: the bench link suite runs once per mode; CRC16 behind `flash_cycle`
- **Why**: LEAD/R31 — "L4 runs the bench suite once per mode, the second on a dev image built with the key flipped
  (behind `flash_cycle`)"; OR118.a (4) "The second CRC mode's L4 run reflashes, so it sits behind `flash_cycle`"
  (owner, 2026-09-30).
- **Site**: `scripts/build_firmware.py:113-126` (arguments, `device_toml`), `:60-66` `build_stage_dir()`;
  `tests_hardware/bench/test_uart_link_under_api_load.py` (three tests `:60, :111, :159`); the reflash steps of
  `tests_hardware/flash/test_toolchain_flash_boot.py:52-90`.
- **Change**: (1) `build_firmware.py` gains `--device-toml PATH` (default `devices/<device>.toml`): the build reads that
  file instead, the image name stays `firmware-<device>.uf2` unless `--output` says otherwise; `build_stage_dir()` takes
  the path; the image record A.U26.02 writes beside the `.uf2` gains `"deviceToml"` (the path built from) and
  `"uartCrc"` (each UART bus's mode), so the bench's image check (A.U26.03) can tell the CRC16 image from the standard
  one. (2) The reflash steps (build, `picotool load -x -v`, BOOTSEL retry, passive wait for serving) move into one
  harness helper `reflash(board, uf2_path)` used by the smoke test and by (3) (A.U26.14 reworks the same retry — A-C
  merges). (3) New `tests_hardware/bench/test_uart_link_crc16.py`, one test `@pytest.mark.flash_cycle`: save FRAM
  evidence first (A.U26.22's `save_errcount()` + `save_fram_raw()`, a reflash being a clearing path); derive the bench
  board's TOML (A.U26.01) into `tmp_path` with `crc = "crc16"` on both link instances; build it with `--device-toml`;
  `reflash()`; run the three API-load link checks of `test_uart_link_under_api_load.py` (factored into module-level
  helpers both files call); in `finally`, rebuild and reflash the standard image and assert the board serves and
  `UARTLINK.Failures` stays 0 over two polls. The no-CRC run is the existing file on the standard image, unchanged.
- **Blast**: callers of `build_stage_dir()` (`tests_scripts/test_build_firmware.py` stubs) · generated a crc16 image in
  the test only · js — · tests new L0 `tests_scripts/test_build_firmware.py` — `--device-toml` builds the stage dir from
  the given file (a tmp TOML with a different hostname: the staged generated module carries it) and a missing path
  fails before staging; `tests_scripts/test_persistence_write_marker_completeness.py` unaffected (no persisting PUT);
  the wear guard (A.U26.06) sees the `flash_cycle` marker · twin — · docs `tests_hardware/README.md` flash-cycle list
  gains this test ("two reflashes: the CRC16 image and back") · toml — · uart — · hardware C (bench round, only with
  `--allow-flash-cycle`).
- **Depends**: A.S0930.01, A.S0930.02, A.U26.01, A.U26.02 (same `build_stage_dir()` signature and the image record),
  A.U26.03, A.U26.14, A.U26.22, A.U26.82 (its bench arm runs on both images), U21's actions on `scripts/build_firmware.py`
  — A-C merges.
- **Kind**: code | test | hardware

### A.S0930.07 The C-port changelog records the CRC mode key (Class B)
- **Why**: LEAD/R31 — "UART_C_PORT_CHANGELOG gets a Class B entry"; OR116.a (3) "Python-internal wiring, no wire-format
  change … Class B" (owner, 2026-09-30); CLAUDE.md UART rule ("the second class is logged too").
- **Site**: `UART_C_PORT_CHANGELOG.md` Class B table (`:70-103`, after the last row at execution, number per A.U17.30).
- **Change**: row `| B<n> | Each `uart_link` end declares its CRC mode in the device TOML (`crc`: "none", the default,
  or "crc16"); the build refuses a pair whose ends differ and sizes `rxbuf` with the CRC width; the generated module
  passes the CRC to the end's `asy_uart_driver.UART` bus. `dev` keeps no CRC; the test levels run both modes | Wiring
  only: `asy_uart_comm.py` is unchanged and CRC-agnostic (Part J.3), `UART_Comm` reads the CRC from its bus as before,
  and no default changes. A link built with "crc16" uses `crc_checks.CRC16` (CRC-16/CCITT-FALSE, big-endian), whose
  wire difference from the legacy C CRC is already entry A7 — a Python↔C pair selecting it is that flag day, not a new
  one |`.
- **Blast**: callers — · generated — · js — · tests `tests_scripts/test_uart_changelog.py` (row order and status,
  A.U17.11) · twin — · docs — · toml — · uart this is the entry.
- **Depends**: A.U17.30 (numbering in landing order), A.U17.09 (status vocabulary).
- **Kind**: doc

### A.S0930.08 Part J and the four-tier rule state the two CRC modes
- **Why**: LEAD/R31 — "doc in U36 (SPEC J/L, DEVICE_REFERENCE, UART changelog Class B)"; Home "SPEC J.6/J.7; SPEC L
  (TOML key)"; LEAD/R28 (CLAUDE.md's four-tier rule gains the UART clause, U36).
- **Site**: `SPECIFICATION.md` J.6 (`:5499-5505`), J.7 (`:5568-5620`), the CLAUDE.md four-tier bus-hazard bullet's
  UART clause (A.U17.25/U36 add it).
- **Change**: J.6 first paragraph "`payload_size` and `timeout` are **agreed out of band …**" → "`payload_size`,
  `timeout` and the CRC mode are **agreed out of band …**" plus one sentence "The CRC mode is a per-end key of the
  device TOML (`crc`: "none" or "crc16"); the build refuses a pair whose ends differ (agent, 2026-09-30, from the
  owner's 2026-09-11 no-negotiation rule)"; J.6's "Wire cost … At the defaults (`payload_size=48`, CRC16)" → "(`payload_size=48`
  with CRC16; `dev` runs without, 53 bytes)" — the default is no CRC (`asy_uart_driver.py:76`). J.7 gains after the
  loopback-model paragraphs: "**Both CRC modes at every level** (owner, 2026-09-30): no CRC and CRC16 run at L1 (the
  protocol hazard file and the exerciser), L2 (twin pair and a generated CRC16 boot), L3 (each crossover script twice
  over the jumper) and L4 (the standard image, and a CRC16 image behind `flash_cycle`)"; the tier map A.U17.25 adds to
  J.7 marks each row with its modes. CLAUDE.md's UART clause (U36's text) gains "in both CRC modes".
  DEVICE_REFERENCE.md: no `uart_link` section exists (grep) — nothing to change.
- **Blast**: callers — · generated — · js — · tests `tests_scripts/test_comment_block_cap.py` n/a (docs);
  `tests_scripts/test_doc_refs*` if the J.6 wording is pinned (grep `agreed out of band` in `tests_scripts/`: none) ·
  twin — · docs as above · toml — · uart — (the changelog is A.S0930.07).
- **Depends**: A.U17.25 (tier map), A.U17.33 (J.5 ladder paragraph nearby), U36's CLAUDE.md UART clause — A-C merges.
- **Kind**: doc

### Part B — the system commands "Reset to defaults" and "Erase FRAM" (LEAD/R32)

### A.S0930.09 `_SYSTEM_CMDS` gains `"resetconfig"` and `"erasefram"`
- **Why**: LEAD/R32 — "`SystemCmd` gains "Reset to defaults" … and "Erase FRAM""; State "code in U19 (`_SYSTEM_CMDS`)"
  ("I want to have added: "Reset to defaults" … and "Erase FRAM"", owner, 2026-09-30, OR117); OR121.a (1) "two more
  `SystemCmd` enum values on `PUT /system` … dispatched by `_dispatch_system_cmd()` and answered in the same envelope
  and results"; OR122.a (2) "a command runs only when the request carries its exact action word … no alias, prefix,
  case folding or number" (owner, 2026-09-30, OR121, OR122).
- **Site**: `src/asy_webserver_service.py:95-97` (`_SYSTEM_CMDS` and its comment), `:503-517` `_dispatch_system_cmd()`
  (unchanged logic: `cmd not in _SYSTEM_CMDS` → "Invalid", callback `True` → "Valid", `False`/raise → "Failed").
- **Change**: `_SYSTEM_CMDS = ("reboot", "bootloader", "mempause", "resetconfig", "erasefram")`. Comment (≤ 3 lines):
  "the only values ever forwarded to system_cmd(), matched as whole strings: the exact action word is what runs a
  command, so no alias, prefix or case variant does (owner, 2026-09-30). mempause's fixed 300 s lives in the callback
  (Part A.8)." The words' rationale (design block) goes to SPEC A.8, not here. No route, key or result word is added
  (OR121.a (1)). A.U19.04 already reduces the guard to `self._system_cmd is None or cmd not in _SYSTEM_CMDS`; the
  whole-string tuple membership test compares by equality, so a non-string JSON value can never match.
- **Blast**: callers `_put_system()` `:494-501` · generated `_system_cmd_callback` (A.S0930.11) · js
  `js/mock-server.js:16` `SYSTEM_CMDS` (derived from the definitions by A.U23.27; if that lands later, the two values
  are added there in the same commit) · tests existing: `tests/test_asy_webserver_service.py:520-541`
  (`"erase_flash"` → Invalid — holds, a near miss of the new word), `:543-583` hold; `tests/test_config_manager.py:556-565`
  (a literal copy of the three values as a `special` set — a type test, unaffected); new: L1 per A.S0930.21 (exact-word
  test) and L0 per A.S0930.20 (mirror) · twin — · docs SPEC A.8 `:612` (A.S0930.30) · toml — · uart —.
- **Depends**: A.U19.04 (same function), A.U19.16 (result-word constants), A.U10.29 (`_SYSTEM_CMDS` stays a tuple
  literal, const folding) — A-C merges.
- **Kind**: code

### A.S0930.10 Two more options in the "System Command" dropdown
- **Why**: LEAD/R32 — State "U20 (definitions options)"; OR121.a (2) "two more options in the existing "System
  Command" dropdown (`_SYSTEM_COMMAND_GROUP`, `buildgen/definitions.py:55-62`), labels "Reset to defaults" and "Erase
  FRAM", sent with the same Apply button; no new group, control or dialog"; OR122.a (2) "No dialog, and none proposed"
  (owner, 2026-09-30).
- **Site**: `buildgen/definitions.py:55-62` `_SYSTEM_COMMAND_GROUP`.
- **Change**: after the `mempause` option: `{"value": "resetconfig", "label": "Reset to defaults"},` and `{"value":
  "erasefram", "label": "Erase FRAM"},` — the owner's labels verbatim (OR117). Every device gets both, as every device
  gets the existing three (the group is static, `:354`): a device without a FRAM instance answers `"erasefram"` with
  "Failed" (preflight, A.S0930.12) — all six shipped TOMLs declare one (`devices/*.toml`, `driver = "fram"`). No js code
  change: `js/templates.js` renders enum options from the definitions and the Apply button sends the selected value
  (`js/render.js:188-240`); A.U23.15 resets the select to its placeholder after Apply.
- **Blast**: callers `generate_definitions()` `:354` · generated every device's definitions JSON (A.U6.03/A.U6.04 make
  them generated; `html/definitions/dev.json:806-822` and `wozi.json:194-197` if still present at execution gain the
  two options) · js — (rendered from data) · tests: L0 per A.S0930.20 · twin the website served by the twin shows the
  options · docs SPEC H (A.S0930.30) · toml — · uart —.
- **Depends**: A.U6.03, A.U6.04 (hand-written definitions retired), A.U23.27 (mirror test), A.U23.15 (select reset) —
  A-C merges.
- **Kind**: code

### A.S0930.11 The generated command callback returns the service's answer for all five words
- **Why**: LEAD/R32 — State "U20 (… generated callback)"; OR119.a (1)-(2) "refuse any further command" while a
  shutdown is under way (owner, 2026-09-30, OR119).
- **Site**: `buildgen/codegen.py:524-537` (`_system_cmd_callback` template, as A.U11.03 rewrites the reboot and
  bootloader branches), `:501-514` `_emit_flush_pending_configs()` (A.U11.03 replaces it by `_collect_config_stores()`).
- **Change**: emitted body: `if cmd == "reboot": return await sysfunct.reboot_system()`; `if cmd == "bootloader":
  return await sysfunct.reboot_bootloader()`; `if cmd == "mempause": return sysfunct.pause_permanent_storage(300)`;
  `if cmd == "resetconfig": return await sysfunct.reset_to_defaults()`; `if cmd == "erasefram": return await
  sysfunct.erase_fram()`; `return False`. Every branch returns the service's own answer (A.S0930.12 makes the three
  existing methods return `bool`: `False` while a shutdown is under way), so the webserver answers "Failed" for a
  refused command. The `mempause` 300 stays as today (U20: "`mempause` option equals `pause_permanent_storage(300)`").
- **Blast**: callers `WebserverService(system_cmd=…)` (`codegen.py:618`) · generated every device's callback · js — ·
  tests existing `tests/_sensortask_scenarios.py:953-983` (reboot Valid, flush-then-reboot, bogus Invalid) hold;
  new L0 per A.S0930.20 (the callback's compared words equal `_SYSTEM_CMDS`) · twin — · docs SPEC L.4 names the
  callback's branches only by reference to A.8 · toml — · uart —.
- **Depends**: A.U11.03 (reboot branches, `_collect_config_stores()`), A.S0930.12, A.U20.41/A.U20.42 (template renames,
  the `assert` narrowing goes) — A-C merges.
- **Kind**: code

### A.S0930.12 `SystemService`: the command gate for the two new commands
- **Why**: LEAD/R32 — "Either may arrive in any state (… a reboot or the other command under way, two at once) and
  breaks nothing beyond its intended effect: one controlled shutdown sequence answers the request, refuses further
  commands"; State "U11 (`SystemService`)" (owner, 2026-09-30, OR119, OR119.a (1)-(2)); OR117.a (2) "Erase FRAM … the
  whole chip" (owner, 2026-09-30).
- **Site**: `src/system_service.py:63-109` (`__init__`), `:347-351` `reboot_system()`/`reboot_bootloader()` (async
  after A.U11.03), `:353-373` `pause_permanent_storage()`, new `reset_to_defaults()`, `erase_fram()`,
  `_request_shutdown()`.
- **Change**: state in `__init__` (all fixed-size): `self._command_lock = asyncio.Lock()`, `self._shutdown = 0`
  (0, or the purpose's reset code, A.S0930.15), `self._shutdown_task: asyncio.Task[None] | None = None`, `self._feed_owned
  = False` (A.S0930.13). `async def reset_to_defaults(self) -> bool: return await
  self._request_shutdown(_RR_CONFIG_RESET)`; `async def erase_fram(self) -> bool: return await
  self._request_shutdown(_RR_FRAM_ERASED)`. `_request_shutdown(purpose)` under `async with self._command_lock:` runs the
  design block's S0 in order: (1) `if self._shutdown: return self._shutdown == purpose`; (2) `if self._reset_armed:`
  print "Command refused: a reset is already armed", `return False`; (3) `self._shutdown = purpose`; (4) preflight —
  config reset: `if not self._config_stores` → refuse; erase: `if self._storage is None or not await
  self._storage.erase_ready()` → refuse; a refusal prints one line naming the reason, sets `self._shutdown = 0`,
  returns `False`; (5) `try: self._shutdown_task = asyncio.create_task(self._shutdown_sequence(purpose))` / `except
  MemoryError as e:` print, `self._shutdown = 0`, `return False`; (6) `self._feed_owned = True`; `self.pr.evt("System
  command accepted, controlled shutdown for", _PURPOSE_NAME[purpose])`; `return True`. Refusals print only: the client
  sees "Failed", and nothing failed inside the unit (the repeat rule's "expected condition", A.U3). Existing commands:
  `reboot_system()`/`reboot_bootloader()` → `-> bool`: `if self._shutdown: return False`, else the U11 path and `return
  True` (a repeat while armed stays U11's "request ignored" with `True`); `pause_permanent_storage(duration) -> bool`:
  `if self._shutdown: return False` first, else today's body and `return True`. `_PURPOSE_NAME` is a two-entry
  `const()`-folded tuple lookup, not a dict built at runtime (the names "config reset"/"FRAM erase" appear only in
  console lines). The supervisor-escalation guard is A.S0930.13's.
- **Blast**: callers the generated callback (A.S0930.11); device scripts calling `reboot_*`/`pause_permanent_storage`
  directly (grep `tests_hardware/device_scripts/`: `reboot_fallback_starves_the_watchdog.py:38` calls `_reboot()`, not
  these; none else) · generated — (A.S0930.11) · js — · tests existing: `tests/test_system_service.py:618-800` (reboot
  and pause tests) assert side effects, not return values — they hold, gaining `is True` where the call's result is
  read; new L1 per A.S0930.21/.22 · twin — · docs SPEC A.8 command semantics (A.S0930.30) · toml — · uart —.
- **Depends**: A.U11.03 (`_reset_armed`, async reboots, `_config_stores`), A.U5.02 (`storage` parameter kept as
  `self._storage`), A.S0930.13-A.S0930.17; `max-args = 8` unaffected (no new parameter, A.U11.05's count).
- **Kind**: code

### A.S0930.13 Watchdog ownership passes to the sequence; the supervisor parks and is proven stopped
- **Why**: LEAD/R32 — "watchdog ownership passes to the sequence — the supervisor feed loop is stopped and proven
  stopped, every other feed site latched off, the sequence feeds once per bounded step, so a healthy run never trips
  the watchdog and a hung step is never fed"; OR120 "Probably it's best to completely stop the loop feeding the
  watchdog, really making sure it actually IS stopped, and feeding it inside the sequence doing the reset work. So
  neither the watchdog inteerrupts the sequence, nor is there any risk the watchdog is fed although something hangs.
  Both of these are extremely important!" (owner, 2026-09-30); OR120.a (1)-(2).
- **Site**: `src/system_service.py:111-116` `feed_watchdog()`; `:216-255` the supervisor loop (U20's
  `supervise_tasks()`, A.U20.06); new `_own_feed()`, `_supervise()`; `__init__` state.
- **Change**: (1) `feed_watchdog()`: `if self.watchdog is not None and not self._force_watchdog_starve and not
  self._feed_owned: self.watchdog.feed()`; its comment (≤ 3 lines): "Every feed site but the shutdown sequence's goes
  through here; once a shutdown command is accepted the sequence alone feeds (owner, 2026-09-30), so this is a no-op
  from then on." (2) `_own_feed()`: `if self.watchdog is not None and not self._force_watchdog_starve:
  self.watchdog.feed()`, comment "The shutdown sequence's own feed, once per bounded step; a hung step is never fed."
  (3) U20's `supervise_tasks()` becomes: `self._supervisor_task = asyncio.create_task(self._supervise())`; `await
  self._never.wait()` — `main()` never returns and is never cancelled (A.U11.03 point 5); the loop body moves into
  `_supervise()`. State: `self._supervisor_task = None`, `self._supervisor_parked = asyncio.Event()`, `self._never =
  asyncio.Event()` (never set). (4) `_supervise()`'s pass begins with `if self._shutdown:
  self._supervisor_parked.set(); await self._never.wait()` — the park point, where the loop holds no lock and is inside
  no log write, so the cancel of S1 lands on a wait; inside the pass, the dead-task restart loop breaks when
  `self._shutdown` is set, and the escalation branch (A.U11.03 point 5) runs only `if not self._shutdown` (the sequence
  reboots anyway, and an escalation's own reset armed mid-sequence would cut it). Its `feed_watchdog()` call is
  latched from acceptance on. (5) S1 of the sequence (A.S0930.14) cancels `self._supervisor_task` after the park and
  awaits it to done — the proof OR120.a (1) asks for. A shutdown accepted before `supervise_tasks()` ran (during
  `start_timers()`/the first NTP sync) is covered: the supervisor task parks at its first pass.
- **Blast**: callers generated `main()` (`await sysfunct.supervise_tasks()`, A.U20.06 — unchanged call); boot batch
  feeds through `feed_watchdog()` (`codegen.py:465` / A.U11.10's `run_setups()`) — latched only if a shutdown was
  accepted, which cannot happen during the batch; `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py:44-47`
  (feeds through `feed_watchdog()`, no shutdown) holds · generated — · js — · tests existing:
  `tests/test_system_service.py:1027-1080` (supervisor feeds / stops feeding once starved / no watchdog) — the loop now
  runs in a task: each drives `supervise_tasks()` in a task, asserts on `feed_count`, and cancels at the end (A.U20.06
  already moves them onto `start_tasks()`/`supervise_tasks()`); `:1236-1253` (budget reboot) as A.U11.03 rewrites it;
  `tests/test_digital_twin_sensortask_integration.py:482-523` drives the supervisor directly (A.U20.06's blast) — it
  cancels `supervise_tasks()`'s task and now also the supervisor task (`sysfunct._supervisor_task`, from outside);
  `tests/_boot_contiguity_probe.py`/`heap_layout_after_full_boot_sequence.py` never enter the supervisor (hold); new L1
  per A.S0930.24 · twin the twin WDT's `feed_count` becomes the observable (A.S0930.27) · docs SPEC A.4/A.7 supervisor
  and watchdog paragraphs, SPEC G.2's `feed_watchdog()` entry ("the one reusable feed access point" gains "except the
  shutdown sequence's own feed, which takes ownership", A.S0930.30); CLAUDE.md boot-latency rule's "what
  `SystemService.feed_watchdog()` exists to prevent" holds · toml — · uart —.
- **Depends**: A.U20.06 (`start_tasks()`/`supervise_tasks()`, `self._tasks`), A.U11.03 (escalation branch, starve flag),
  A.U11.10 (`run_setups()` feeds), A.U10.07/A.U10.08 (feed-site pins name `supervise_tasks`) — A-C merges.
- **Kind**: code

### A.S0930.14 The controlled shutdown sequence
- **Why**: LEAD/R32 — "one controlled shutdown sequence answers the request, refuses further commands, stops every
  supervised task without restart, lets in-flight storage writes finish under their locks, closes write access to flash
  filesystem and FRAM, applies the purpose and reboots; each step bounded and logged once … a power loss at any step
  leaves a state the next boot handles"; OR119 "shut all down controlled, erase, reboot" (owner, 2026-09-30); OR119.a
  (2)-(4); OR120.a (2); OR117.a (1)-(2).
- **Site**: `src/system_service.py` new `_shutdown_sequence(purpose)`; uses `self._tasks` (A.U20.06),
  `self._config_stores` and `_flush_config_stores()` (A.U11.03), `_reboot()` (A.U11.03), `self.storage_timer`
  (`:85, 353-373`).
- **Change**: the design block's S1-S6, as code: S1 `self._own_feed()`; `await self._supervisor_parked.wait()`; `task
  = self._supervisor_task`; `task.cancel()`; `try: await task` / `except asyncio.CancelledError: pass`; `if not
  task.done(): return` (no feed follows — the watchdog resets); one `evt` line; `self._own_feed()`. S2 `for store in
  self._config_stores: store.close_writes()`, then per store U11's guarded flush (`try: await store.flush_pending()` /
  `except Exception` → persisted CALLBACK entry, `ok = False`) followed by `self._own_feed()`; one line. S3
  `self.storage_timer.deinit()`; `if self._storage is not None: await self._storage.quiesce(self._own_feed)`; one line.
  S4 `for t in self._tasks: if t is not None and not t.done(): t.cancel()`; then per task `try: await t` / `except
  (asyncio.CancelledError, Exception): pass`, `self._own_feed()`; one line. S5 config reset: `for store in
  self._config_stores: ok = await store.delete_file() and ok; self._own_feed()`; erase: `ok = await
  self._storage.erase_chip(self._own_feed)`; one line ("done" / "incomplete"). S6 `self._own_feed()`; `await
  self._reboot(purpose if ok else _RR_COMMAND_INCOMPLETE, <message>, system_reset)`. Comment at the method (≤ 3
  lines): "One controlled shutdown for a system command (owner, 2026-09-30): no step has a timeout that moves on — a
  hung step is not fed, so the watchdog resets the unit; the order is explained in SPECIFICATION.md Part A.8." No
  `gc.collect()` (CLAUDE.md sites rule); allocation: the S0 task object, one `bytearray(256)` in the erase (A.S0930.17),
  log strings — nothing proportional to the chip or file sizes. `except (asyncio.CancelledError, Exception)` in S4
  never catches the twin's `SimulatedRebootError(BaseException)` (A.U25.07).
- **Blast**: callers `_request_shutdown()` (A.S0930.12) only · generated — · js — · tests L1-L4 per A.S0930.21-.29 ·
  twin runs the same code (A.S0930.27) · docs SPEC A.8 (the sequence and its order), A.4 (reset path: "every
  deliberate reset pauses FRAM first" holds — S3 and `_reboot()` both pause), F.2 (the commanded-reboot sentence
  gains the two commands), I.4 (a known bounded allocation, no threshold), A.S0930.30 · toml — · uart —.
- **Depends**: A.S0930.12, .13, .15, .16, .17; A.U11.03, A.U11.04, A.U11.05, A.U20.06; A.U16.R03 (the FRAM manager's
  supervised task is one of `self._tasks`; cancelled in S4) — A-C merges.
- **Kind**: code

### A.S0930.15 Reset reasons 7, 8 and 9 for the two commands
- **Why**: LEAD/R32 — "applies the purpose and reboots … logged once" (OR119.a (3)); G5/R03 "every intended reset
  writes [the record]" (owner, 2026-09-26, OR60, OR60.a (1)-(4): "integrate it into the system service and its
  endpoints (e.g. "reset_reason" with a corresponding number code)").
- **Site**: `src/system_service.py` reset-reason constants (A.U11.05's block), SPEC A.8 code table (A.U11.05's).
- **Change**: `_RR_CONFIG_RESET = const(7)` "reboot after "Reset to defaults""; `_RR_FRAM_ERASED = const(8)` "reboot
  after "Erase FRAM""; `_RR_COMMAND_INCOMPLETE = const(9)` "reboot after either command whose purpose did not complete
  (a flush raised, a file stayed, the erase stopped)" — the persisted trace of steps that ran with FRAM closed. The
  record is written by `_reboot()` (U11); `begin_boot()` decodes 7-9 like 3-6 (valid record → its code). 10 + p stays
  the boot-failure range (7-9 were free).
- **Blast**: callers `_shutdown_sequence()` · generated — · js the `/status` `ResetReason` code table (G7/R39, U23's
  clickable table, and A.U6.23's mock sample) gains the three rows · tests A.U11.07's L1 decode table gains 7-9
  (A.S0930.21); A.U25.55's Run 12 and A.U26.28's bench table gain them (A.S0930.27/.29) · twin A.U25.08's `mem_backup`
  model carries them unchanged · docs SPEC A.8 code table rows; `tests_hardware/README.md` "Reset codes proven on the
  bench" rows (A.U26.28) · toml — · uart —.
- **Depends**: A.U11.05, A.U11.07, A.U6.23, A.U26.28, A.U25.55 — A-C merges.
- **Kind**: code | doc

### A.S0930.16 `ConfigManager`: closing is race-free, and a store deletes its own file
- **Why**: LEAD/R32 — "finish pending config flushes, delete every schema-backed `config_<name>.cfg`, reboot … lets
  in-flight storage writes finish under their locks, closes write access to flash filesystem"; OR117.a (1) (owner,
  2026-09-30, OR117, OR119).
- **Site**: `src/config_manager.py:299-308` (`write_config()` entry and lock), `:390-400` `flush_pending()`, new
  `delete_file()`; A.U11.04's `close_writes()`.
- **Change**: (1) `write_config()`: the `_closed` check A.U11.04 places "first, before the lock" is repeated as the
  first statement inside `async with self.config_lock:` — a call that passed the first check while a close was pending
  then refuses too, so no flush task can be created once `close_writes()` has returned and the lock has cycled. (2)
  `flush_pending()`: after releasing a deferred flush (A.U11.28's `_commit_ready`), `async with self.config_lock:
  pending = self._pending_flush`, then `if pending is not None: await pending` — a `write_config()` holding the lock
  finishes staging before the pending task is read, so the flush it created is the one awaited. (3) New `async def
  delete_file(self) -> bool`: `self.close_writes()` (idempotent); `async with self.config_lock:` `try: os.remove(
  self.config_file)` / `except OSError as e:` `if e.errno == errno.ENOENT: return True` (absent is the goal; `import
  errno` from A.U11.19), else `self.pr.err(self.config_file, "- could not be deleted:", e)` and `return False`; after
  success `self.pr.evt(self.config_file, "- deleted, defaults at the next boot")`, `return True`. Console only: the
  sequence runs it with FRAM closed; the reset code 9 is the persisted trace. It deletes whatever file the store owns,
  readable or not (an unreadable file that A.U11.20 never overwrites is removed by this explicit command). Comment
  (≤ 3 lines): "Reset to defaults (owner, 2026-09-30): the next boot serves the schema defaults; the SCD30 keeps its
  settings in its own NVM and has no file."
- **Blast**: callers `SystemService._shutdown_sequence()` (S2 via `_flush_config_stores()`, S5); `flush_pending()`'s
  other callers — U11's `_reboot()`/`_reset_when_due()`, device scripts (A.U11.28's blast: the flush-guard allowlist in
  `tests_scripts/test_device_script_config_flush.py`) — keep their semantics (wait for the last accepted write) · generated
  — · js — · tests existing: `tests/test_config_manager.py` flush and staging tests (`:1736-1782`, the
  `create_task(` count `:2529-2541`) hold; A.U11.04's close tests hold; new L1 per A.S0930.21/.22/.25 · twin — · docs
  SPEC C.5.2/C.7.3 "a closed store refuses writes; `delete_file()` removes the store's file for the config reset" · toml
  — · uart —.
- **Depends**: A.U11.04 (`close_writes()`, `_closed`), A.U11.19 (`errno` import, missing file serves defaults and
  writes nothing — the next boot after the reset), A.U11.20, A.U11.22, A.U11.28 (same methods) — A-C merges.
- **Kind**: code

### A.S0930.17 FRAM manager: close, erase readiness and the whole-chip erase
- **Why**: LEAD/R32 — "Erase FRAM (pause every FRAM writer, hold the FRAM lock, overwrite the whole chip with a pattern
  no valid chunk accepts, reboot)"; State "U16 (FRAM manager erase)"; OR117 "Erase FRAM, which plainly clears the whole
  chip" (owner, 2026-09-30); OR117.a (2) "checked against `crc_checks.py` in A-L, since an all-zero block may pass a
  zero-init CRC"; OR120.a (2) "the whole-chip overwrite in chunks"; OR36.a (3) (API of the hardware stays).
- **Site**: `src/asy_fram_manager.py:41-86` (`_AsyBaseFramChunk.__init__`), `:360-399` (`_clear_chunk()`/`clear()`,
  beside which the two new chunk methods go), `:618-628` (`AsyFramManager.__init__`), `:645-724`
  (`get_chunk()`/`get_timestamped_chunk()`), `:726-728` `set_pause()`, new manager methods; constants `:29-38`.
- **Change**: (1) Chunk: `async def wait_idle(self) -> None: async with self._op_lock: pass` — comment "returns once
  this chunk's in-flight operation has finished; used after the pause, so none starts again"; `async def
  invalidate(self) -> bool`: under `self._op_lock`, for each block `async with self.fram as fram:` →
  `_handle_status_bytes(fram, addr, _STATUS_UNINIT, check_idle=False, …)` (the status write `_clear_chunk()` makes
  first, `:364`, with its codes as A.U2.09 names them); `False` on the first failed block — no pause check: only the
  erase calls it, after the manager closed the chunk layer. (2) Manager: `self._chunks: list[_AsyBaseFramChunk] = []`
  (grows once per allocation during construction only, like every boot collector); `get_chunk()`/
  `get_timestamped_chunk()` append the chunk they return. (3) `async def quiesce(self, step_done: "Callable[[], None]")
  -> None`: `self.set_pause(value=True)`; `for chunk in self._chunks: await chunk.wait_idle(); step_done()`. (4)
  `async def erase_ready(self) -> bool`: `self.fram.initialized and not await self.fram.get_write_protected()` (the
  driver's own guard; A.U16.R03's lost chip reads `initialized` False). (5) `async def erase_chip(self, step_done:
  "Callable[[], None]") -> bool`: `if not await self.erase_ready(): self.pr.err("FRAM erase refused: chip not ready or
  write-protected"); return False`; pass 1 `for chunk in self._chunks: ok = await chunk.invalidate() and ok;
  step_done()`; `try: unit = bytearray(_ERASE_UNIT)` / `except MemoryError: self.pr.err("FRAM erase: no buffer, chunks
  blanked only"); return False`; pass 2 `size = await self.fram.get_size()` (the driver's hardware API, OR36.a (3));
  `for addr in range(0, size, _ERASE_UNIT): async with self.fram as fram: status = fram.set_values_sync(unit, addr)`;
  `if status and not await self.fram.report_set_values(status): self.pr.err("FRAM erase stopped at", addr); return
  False`; `step_done()`; `await asyncio.sleep(0)`; end: `self.pr.evt("FRAM erased:", size, "bytes")`, `return ok`.
  `_ERASE_UNIT = const(256)` — "one erase write: 2.1 ms at the 1 MHz bus, divides both chip sizes; the size class the
  webserver's chunked writes use (Part I.3)". Both chip sizes are multiples (0x2000/0x100 = 32, 0x40000/0x100 = 1,024;
  A.U16.20 limits `max_size` to these). The manager's log is RAM-only (A.U16.13), so nothing it logs here writes FRAM.
  Comment at `erase_chip()` (≤ 3 lines): "Erase FRAM (owner, 2026-09-30): every chunk's blocks are marked blank first,
  so no interrupted later write can leave a block that validates; then every byte is zeroed — the chip's own blank
  state (Part A.4)."
- **Blast**: callers `SystemService` (A.S0930.12/.14); chunk owners unaffected (`print_log.py:238`,
  `asy_sgp40_driver.py:181-183`); the chunk API's `override_pause` removal (A.U16.19) makes `invalidate()` the only
  path past the pause, used only by the erase · generated — · js — · tests existing: `tests/test_asy_fram_manager.py`
  allocator tests (`:71-100`) hold (a list append per allocation); `tests/test_asy_fram_allocation_budget.py` (per-chunk
  allocation count) gains one list slot per chunk — re-derive its bound; A.U16.02's pinned layout unaffected (no
  address changes); new L1 per A.S0930.21-.25 · twin the twin chip (`digital_twin/_fram_chip.py`, rollover per
  A.U25.15) takes 1,024 writes of 256 B on dev · docs SPEC A.4 FRAM bullet (erase and the 0x00 proof), C.3.1 FRAM API
  list (`quiesce()`, `erase_ready()`, `erase_chip()`), C.8 (the erase holds both FRAM locks per unit, never across an
  await of another lock) · toml — · uart —.
- **Depends**: A.U16.19 (`override_pause` gone), A.U16.22 (chunk `get_size()`/`get_pause()` gone — the manager uses the
  driver's `get_size()`), A.U16.05/A.U16.06/A.U16.09 (same chunk class; A.U16.09's blank-block read without a busy
  marker is what keeps an erased chunk blank across repeated reads), A.U16.10 (both locks), A.U16.13 (RAM-only log),
  A.U16.17/A.U16.R03 (task and loss state), A.U16.R01 (one WREN retry per unit write), A.U2.09 (codes), A.U5.13 (chunk
  constructors) — A-C merges.
- **Kind**: code

### A.S0930.18 Cancelling the webserver's task closes its listening socket (DONE-AT-HEAD, pinned)
- **Why**: LEAD/R32 — "stops every supervised task without restart" (OR119.a (2)); the sequence's S4 relies on a
  cancelled webserver accepting no new request.
- **Site**: `src/asy_webserver_service.py:733-739` `_run()` (`await server.wait_closed()`).
- **Change**: DONE-AT-HEAD — no product change. `Server.wait_closed()` is `await self.task` (`mp/extmod/asyncio/
  stream.py:141-142`, v1.29.0); cancelling a task that waits on another task forwards the cancel to the awaited one
  (`task.py:164-166`); the server task's `CancelledError` handler closes the listening socket and, since `close()` was
  not called, re-raises (`stream.py:149-159`), so `_run()` ends with `CancelledError` and the port is closed. New L1
  test pins it because a MicroPython bump could change it (CLAUDE.md standing practice): in
  `tests/test_asy_webserver_service.py`, a `WebserverService` on `127.0.0.1` and a free port with the real
  `asyncio.start_server()` (the Unix port binds real sockets), its `_start_serving()` task cancelled and awaited →
  `asyncio.open_connection()` to that port raises `OSError`; an accepted connection opened before the cancel still
  completes its request (connection tasks are not cancelled).
- **Blast**: callers — · generated — · js — · tests new as above; `scripts/test.sh`'s port rule (ephemeral port, CLAUDE.md
  "two suites that bind real ports") · twin — · docs SPEC F.5 (the forwarded-cancel fact, cited once, used by A.8's
  sequence text) · toml — · uart —.
- **Depends**: A.U19.09 (same function: the start retry wraps `start_server()`, the `wait_closed()` stays) — A-C merges.
- **Kind**: test

### A.S0930.19 The wear gate counts `"resetconfig"` as a persisting write
- **Why**: OR118 "with the reset config gated behind the flash write flag"; OR118.a (2) "A test whose owned write is the
  config reset carries `persistence_write`" (owner, 2026-09-30); CLAUDE.md wear rule (owner, 2026-09-17/-18).
- **Site**: `tests_scripts/test_persistence_write_marker_completeness.py:22` (`_ROUTE_DISPATCH_FIELDS`), its
  `_persisting_put_functions()` detector, `:340-344` (`test_a_dispatch_only_put_is_not_flagged`); `tests_hardware/README.md:1336-1343`.
- **Change**: `SystemCmd` stays dispatch-only in general, but a body whose `SystemCmd` value is the config-reset word
  counts as persisting: a new `_PERSISTING_COMMAND_WORDS` set, read by `ast` from `src/asy_webserver_service.py`'s
  `_SYSTEM_CMDS` and narrowed to the one word whose purpose writes the flash filesystem, pinned by name with its reason
  ("deletes every config file"); the detector flags a function whose PUT body literal carries it, so an unmarked test
  fails. `"erasefram"` stays unflagged (FRAM is outside the gate, OR118.a (3)). README: the dispatch-only sentence
  gains "— except `SystemCmd` `"resetconfig"`, whose purpose deletes every config file (a flash-filesystem write the
  test owns, owner, 2026-09-30)".
- **Blast**: callers — · generated — · js — · tests existing `:340-344` gains a parameter `'{"SystemCmd": "erasefram"}'`
  (not flagged) and a new case `'{"SystemCmd": "resetconfig"}'` flagged; the synthetic-bite test pattern (`:330-337`)
  repeated for the command · twin — · docs README as above · toml — · uart —.
- **Depends**: A.U26.71 (the guard derives the dispatch-only classes from A.U6.17's tags and counts the always-executed
  class as persisting — the config-reset word is expressed in that derivation, as a value-level exception of the
  `SystemCmd` dispatch field), A.U26.06 (the guard sees device scripts — the L3 reset script is one), A.U26.74 — A-C merges.
- **Kind**: test | doc

### Tests for the two commands — every type at every level (OR118.a, OR120.a (3), OR122.a (1))

Matrix (rows: the test types OR122.a (1) lists; cells: the action that plans it; "—" with its reason):

| type | L0 host | L1 unit | L2 twin | L3 flash | L4 bench |
|---|---|---|---|---|---|
| function (exactly its purpose) | .20 definitions, callback, mirror, mock | .21 (a)-(c) | .27 (1) | .28 (1)-(2) | .29 (1)-(2) |
| every refusal and error path | .20 mock near misses | .21 (d)-(g) | .27 (1c) | .28 (3) near misses in-script | .29 (3) |
| concurrency and race (OR119.a states) | — (no runtime) | .22 | .27 (2) | .28 (4) | .29 (4) |
| bus and storage hazards (four-tier rule) | — | .23 (mock tier) | .27 (3) (twin tier) | .28 (5) (flash tier) | .29 (5) (bench under API load) |
| watchdog handling (OR120.a) | .20 (feed-site guard, generated code) | .24 | .27 (4) | .28 (6) | .29 (6) |
| power loss per step | — | .25 | .27 (5) | .28 (7) (reset mid-erase) | .29 (7) manual power cut |
| gc −1/32768 and `MemoryError` bars | — | .26 (both stages; allocation independent of chip size) | .27 (6) | .28 (8) soak markers | .29 (8) soak markers |

### A.S0930.20 L0: definitions, callback, mirror, mock, website and feed-site guards
- **Why**: LEAD/R32 — "Both get full tests at L0-L4"; OR118.a (1) "L0 (definitions, website, buildgen)"; OR121.a (2);
  OR122.a (1)-(2) "a test pins that near-misses are refused as `"Invalid"`"; OR120.a (3) "no feed from any other site
  after takeover" (owner, 2026-09-30).
- **Site**: `tests_scripts/test_buildgen_definitions.py`, `tests_scripts/test_buildgen_generate.py`,
  `tests_scripts/test_js_api_mirrors.py` (A.U23.25/A.U23.27's file), `tests_js/mock-server.test.js:224-244`,
  `tests_js/render.test.js:583-620`, `tests/test_reset_call_site_invariant.py` (A.U24.54 extends it), new
  `tests_scripts/test_fram_chunk_crc_sites.py`.
- **Change**: (1) definitions — per device from `DEVICE_NAMES`: the "command" group's `SystemCmd` options are exactly
  `_SYSTEM_CMDS` (read by `ast` from `src/asy_webserver_service.py`) in order, the two new labels exactly "Reset to
  defaults" and "Erase FRAM", no field of the group carries a confirmation key (OR121.a (2)). (2) mirror — A.U23.27's
  "generated `SystemCmd` option values equal `_SYSTEM_CMDS`" covers both words; its bite arm drops `"erasefram"` from a
  copied definitions dict and must fail. (3) generated callback — per device, the string constants compared in
  `_system_cmd_callback` (by `ast`) equal `_SYSTEM_CMDS`, every branch `return`s its call, and the two new branches call
  `sysfunct.reset_to_defaults()`/`sysfunct.erase_fram()`. (4) mock — `tests_js/mock-server.test.js`: both words →
  "Valid", never persisted into `systemConfig`, a repeat stays "Valid"; the near-miss list `"ResetConfig"`,
  `"RESETCONFIG"`, `"resetconfig "`, `" erasefram"`, `"erasefram\n"`, `"reset"`, `"erase"`, `"EraseFRAM"`,
  `"erase_fram"`, `"fram"`, `""`, `1`, `0`, `true`, `false`, `null`, `["erasefram"]`, `{"cmd": "erasefram"}` → each
  "Invalid". (5) website — `tests_js/render.test.js`: choosing "Erase FRAM" and Apply sends one PUT to `/system` with
  body exactly `{"SystemCmd":"erasefram"}` and calls no `window.confirm` (a spy asserts zero calls); the same for
  "Reset to defaults"; the select returns to its placeholder after Apply (A.U23.15). (6) feed-site guard —
  `tests/test_reset_call_site_invariant.py` gains `test_the_watchdog_is_fed_only_inside_system_service`: `.feed(`
  appears in `src/*.py` and `build/generated_src/*.py` (A.U24.54's scan set) only in `system_service.py`, exactly twice,
  inside `feed_watchdog()` and `_own_feed()` (function spans found by line scan of `def`); a bite fixture with a third
  `.feed(` fails it. (7) chunk CRC sites — `test_fram_chunk_crc_sites.py`: every `get_chunk(`/`get_timestamped_chunk(`
  call in `src/` passes `crc=` one of `CRC8()`, `CRC16()`, `CRC32()` (by `ast`) — the second erase gate (a non-zero
  CRC init) cannot be lost to a future `CRC_Pass` chunk; bite: a synthetic call without `crc=` fails.
- **Blast**: callers — · generated read only · js `tests_js/*` as above · tests new/extended as above · twin — · docs
  SPEC E (test catalog rows, U36) · toml — · uart —.
- **Depends**: A.S0930.09-.13, A.U23.25, A.U23.27, A.U23.15, A.U24.54, A.U6.03/A.U6.04 — A-C merges.
- **Kind**: test

### A.S0930.21 L1: function, every refusal and every error path
- **Why**: OR122.a (1) "function (each command does exactly its purpose), every refusal and error path"; OR117.a (1)-(2);
  OR119.a (4); OR118.a (1) (owner, 2026-09-30).
- **Site**: `tests/test_system_service.py` (new section after the reboot tests `:618-800`), `tests/test_config_manager.py`,
  `tests/test_asy_fram_manager.py`, `tests/test_asy_webserver_service.py:520-590`; fakes `tests/_fram_chip_fake.py`
  (A.U24.22's `size=`), `tests/machine.py` (`WDT`, `Timer`, A.U11.07's `mem_backup`).
- **Change**: (a) `test_reset_to_defaults_closes_flushes_quiesces_stops_deletes_then_reboots_with_code_7` — two stores
  recording calls, a real `AsyFramManager` on the fake chip, two supervised tasks sleeping, the supervisor running as
  its task: `run(svc.reset_to_defaults())` is `True`; after pumping, the recorded order is close×2, flush×2, pause,
  `wait_idle` per chunk, both tasks cancelled and done, delete×2, region-0 record code 7, reset timer armed; after
  `reset_timer.trigger()` and a pump `machine.reset_count` rose by one. (b) `test_erase_fram_zeroes_every_byte_and_reboots_with_code_8`
  — on the 8 KB and the 256 KB fake (A.U24.22), memory seeded with valid logger chunks and 0xA5 elsewhere: afterwards
  `chip.memory == bytearray(size)`, code 8; the SPI log shows `size // 256` unit writes at ascending addresses, each
  after every chunk's pass-1 status writes. (c) `test_an_erased_chip_boots_like_a_new_one` — fresh manager and loggers
  over the erased memory: every logger `initialized`, `ErrCount` 0, the FRAM log holds no error entry;
  `test_an_all_zero_block_never_validates_even_with_an_idle_status` — a block crafted with status 0x01 0x01 over all-zero
  data and CRC reads invalid for a CRC8 and a CRC32 chunk (the second gate alone). (d) refusals, each answering `False`
  with nothing changed (no task, `_feed_owned` False, stores open, pause unchanged, chip bytes unchanged, no timer
  armed): a reset armed first; no config store; no storage (erase); chip uninitialised; chip write-protected (fake status
  0x8C); `asyncio.create_task` replaced from outside by a function raising `MemoryError`; the other command under way
  (`False`) and the same one (`True`, still one task); `reboot_system()`, `reboot_bootloader()` and
  `pause_permanent_storage(300)` during a shutdown → `False`, no timer armed, pause unchanged. (e) step errors, the
  sequence continuing to the reboot with code 9 and never hanging: a store's `flush_pending()` raising (one persisted
  CALLBACK entry, the other store still flushed); `cm.os` replaced from outside with an `os` stand-in whose `remove`
  raises `OSError(5)` for one file (that file stays, the others go, one console line, no persisted entry); the fake chip
  with `drop_wren = True` from the first pass-2 unit (erase stops, every status byte already 0x00); the module
  attribute `asy_fram_manager.bytearray` shadowed from outside by a function raising `MemoryError` (chunks blanked, code
  9). (f) `tests/test_config_manager.py` — `delete_file()`: an existing file → `True`, gone; absent → `True`; `OSError(5)`
  → `False`, one console line; `write_config()` after it → `(False, {})`. (g) `tests/test_asy_webserver_service.py` —
  `test_system_put_systemcmd_runs_only_on_the_exact_action_word`: the near-miss list of A.S0930.20 (4) as JSON bodies
  → "Invalid" and the fake callback records no call; `"resetconfig"`/`"erasefram"` → one call each with that exact
  word, "Valid" for `True`, "Failed" for `False`, "Failed" plus errno 2 for a raise.
- **Blast**: callers — · generated — · js — · tests new as above; existing reboot/pause tests per A.S0930.12's blast ·
  twin — · docs — · toml — · uart —.
- **Depends**: A.S0930.09-.17; A.U11.07 (`mem_backup` fake), A.U24.22 (FRAM fake size), A.U4.06 (`WriteCountingOpen`) —
  A-C merges.
- **Kind**: test

### A.S0930.22 L1: every OR119.a state, raced deterministically
- **Why**: OR119.a (1) "Either command may arrive in any state: during the boot `setup()` batch, during a config flush
  or a FRAM chunk write, inside a bus session, while storage is paused (`mempause`), while a reboot or the other command
  is already under way, or twice at once; it breaks nothing beyond its own intended effect"; OR122.a (1) "concurrency and
  race (the OR119.a states)" (owner, 2026-09-30).
- **Site**: `tests/test_system_service.py` (system-command section), `tests/test_config_manager.py`,
  `tests/test_asy_fram_manager.py`.
- **Change**: each interleaving forced by a suspended fake (an `asyncio.Event` gate, G2/R15's driven-interleaving rule),
  never by sleeps: (1) boot — accepted before `supervise_tasks()` ran: the sequence waits; once the supervisor task starts
  it parks at its first pass and the sequence proceeds; `feed_watchdog()` never fed meanwhile. (2) config flush in flight
  — `_flush_staged()` suspended inside a gated `open` stand-in when the command arrives: the file ends holding the
  accepted value; a `write_config()` suspended inside the lock (its logger gated) finishes staging and its flush is the
  one S2 awaits; one queued behind the lock at close time answers `(False, {})`. (3) FRAM write in flight — a logger write
  suspended between block 0 and block 1 (gated fake chip): after the command both blocks hold the entry (reset: kept;
  erase: blanked afterwards), and a write started after S3 is refused with the chip unchanged. (4) bus session — a task
  inside an `I2CDevice` session (lock held, suspended) cancelled by S4: the lock is free afterwards and a sibling's next
  session succeeds; no exception escapes S4. (5) `mempause` active — `pause_permanent_storage(300)` then `erase_fram()`:
  `storage_timer` is deinit'd (triggering the fake timer afterwards leaves the pause set), the erase completes. (6)
  reset armed → refused; `reboot_system()` during the sequence → `False`; the supervisor with tasks dying past the budget
  during the sequence arms nothing (one record written, the command's code). (7) the other and the same command at once —
  `asyncio.gather()` of both orders: different → exactly one `True`; same → both `True`, one task. (8) a command, a
  reboot and a mempause at once — exactly one reset armed, its code matching the accepted request. (9) a PUT through an
  accepted connection during S5 (webserver dispatched in-process): a config field → "Failed"; `ResetErrors` → "Failed"
  per field (A.U11.31).
- **Blast**: callers — · generated — · js — · tests new · twin — · docs — · toml — · uart —.
- **Depends**: A.S0930.12-.17; A.U11.31 (`ResetErrors` per field) — A-C merges.
- **Kind**: test

### A.S0930.23 L1: bus and storage hazards (mock tier of the four-tier rule)
- **Why**: CLAUDE.md "A new bus-facing (I2C/SPI) device gets bus-hazard test coverage across all four test tiers …
  same-device read-vs-write concurrency, cross-device interleaving … and an address/command sweep" (owner's standing
  direction) — the erase is a new SPI operation on the FRAM; OR122.a (1) "bus and storage hazards" (owner, 2026-09-30).
- **Site**: `tests/test_bus_hazard_multi_device.py` (mock tier).
- **Change**: (a) same device — `erase_chip()` started while a chunk write and a chunk read of the same FRAM are
  suspended mid-operation: the in-flight ones finish with both copies equal, later ones are refused, no chunk is left
  torn; the fake SPI log shows each erase unit's five sessions contiguous (no other CS cycle between them) because the
  unit holds both FRAM locks. (b) cross-device — FRAM is alone on its SPI bus in every shipped TOML (SUPP_recovery's U16
  table), so the cross-device case is S4's cancellations on a shared I2C bus: two sensors on one bus, one cancelled
  inside its session, the other's next transaction succeeds and the lock is free. (c) sweep — erase unit addresses cover
  `[0, size)` exactly once, ascending, with the 3-byte address header on the 256 KB fake and 2-byte on the 8 KB one, and
  no `_SV_BAD_RANGE` status ever; pass-1 status writes address exactly the two status bytes of each allocated block
  (from the chunk registry) and nothing else. Storage: after a config reset the scenario's config directory holds no
  `config_*.cfg`; a file is never seen half-written or half-deleted by a concurrent reader (reads and delete take the
  store's lock).
- **Blast**: callers — · generated — · js — · tests new cases in the mock hazard file · twin L2 half is A.S0930.27 (3) ·
  docs — · toml — · uart —.
- **Depends**: A.S0930.17; A.U24.27 (generated bus hazards drive every writer — same file) — A-C merges.
- **Kind**: test

### A.S0930.24 L1: watchdog ownership proven
- **Why**: OR120.a (3) "Both properties are proven by tests at every level that can reach them: no feed from any other
  site after takeover, the sequence never trips the watchdog on a healthy run (worst-case chip and bus speed), and a hang
  injected in any step ends in a watchdog reset, not in a fed hang" (owner, 2026-09-30, OR120: "Both of these are
  extremely important!").
- **Site**: `tests/test_system_service.py` (system-command section); `tests/machine.py:684-691` `WDT` (gains a
  `feed_times` list of `ticks_ms()` stamps, bounded like the other fake logs).
- **Change**: (a) takeover — after acceptance, `svc.feed_watchdog()` called directly, from a supervisor pass in progress
  (gated so it reaches its feed after acceptance) and through `run_setups()`'s feed leaves `feed_count` unchanged;
  after S1 `svc._supervisor_task.done()` is `True` and awaiting it raises `CancelledError` (read from outside). (b)
  healthy run — `feed_count` rises by exactly the planned steps: 2 (S1) + stores + chunks + tasks + (stores | chunks +
  size / 256) + 1 (S6), on the 256 KB fake; the largest gap between consecutive `feed_times` entries during the
  sequence stays under 1,000 ms (host time; the silicon figure is A.S0930.28 (6)). (c) hang in each step, never fed —
  one test per step, the hang injected from outside: S1 a supervisor pass suspended on a gate that never opens (it never
  parks); S2 a store whose `flush_pending()` never returns; S3 a chunk whose `_op_lock` a test task holds forever; S4 a
  supervised task that catches `CancelledError` and keeps sleeping; S5 reset a store whose `config_lock` is held
  forever; S5 erase a fake FRAM driver whose `report_set_values()` never returns (the chip refusing the first unit); S6
  a reset Timer whose callback never fires. Each: pump the loop for 1 s of real time after the hang point; `feed_count`
  is the same as at the hang point, the sequence task is not done, no reset was armed except in S6. (d) `_reboot()`'s
  arm failing in S6 (the fake Timer's `init` raising `OSError(12)`) sets `_force_watchdog_starve` and `_own_feed()` then
  feeds nothing.
- **Blast**: callers — · generated — · js — · tests new; `tests/machine.py` `WDT` gains `feed_times` (A.U24.07 resets
  fake state per test — the list joins its reset hook) · twin L2 proof of the reset itself is A.S0930.27 (4) · docs —
  · toml — · uart —.
- **Depends**: A.S0930.13, A.S0930.14; A.U24.07, A.U24.17 (the shared machine-fake contract gains `feed_times`) — A-C
  merges.
- **Kind**: test

### A.S0930.25 L1: a power loss at each step leaves a bootable state
- **Why**: OR119.a (4) "A power loss at any point leaves a state the next boot handles: an interrupted delete leaves some
  files, which load or default as today; an interrupted overwrite leaves chunks that fail their check and start fresh";
  OR122.a (1) "power loss per step" (owner, 2026-09-30).
- **Site**: `tests/_fram_chip_fake.py` (new knob), `tests/test_asy_fram_manager.py`, `tests/test_system_service.py`.
- **Change**: knob `cut_after_bytes: int | None` on the FRAM fake: after that many further WRITE data bytes the fake
  stops applying writes (a power cut; the byte-granular analogue of A.U25.54's twin `lose_power_after(k)`), and a raise
  of a test-local `PowerCut(BaseException)` ends the run. Proof split per CLAUDE.md's "prove the invariant, not by scale"
  rule: (1) structural — after pass 1 every allocated block's two status bytes are 0x00 (read from the chip), and in
  the SPI log no pass-2 data byte precedes the last pass-1 status write; (2) enumerated — every cut point inside pass 1
  (every byte, a few hundred on the 8 KB layout) and the first byte, a middle byte and the last byte of every pass-2 unit
  that overlaps an allocated block: a fresh manager and loggers over the cut memory restore each ring exactly as it was
  or blank, never other content, and log only codes from {status bytes disagree, block uninitialised}; the next write
  lands. Config: `cm.os` replaced from outside so `remove` raises `PowerCut` after k removals, k = 0 … stores: a rebuild
  over the directory serves each remaining file's values and the defaults for the rest, writes nothing at boot
  (A.U11.19). S1-S4 and S6 write nothing a power loss can tear (S2's flush is the existing write path, whose atomicity
  is littlefs's and phase C's to show; the Unix port's filesystem is not littlefs).
- **Blast**: callers — · generated — · js — · tests new; `tests/_fram_chip_fake.py` gains the knob (A.U24.22 reshapes
  the same class) · twin L2 enumeration A.S0930.27 (5) · docs SPEC A.4 FRAM bullet cites the proof (A.S0930.30) · toml
  — · uart —.
- **Depends**: A.S0930.16, A.S0930.17; A.U24.22, A.U11.19, A.U25.54 (twin analogue) — A-C merges.
- **Kind**: test

### A.S0930.26 L1: per-device scenarios under both gc stages
- **Why**: OR118.a (1) "under the standing gc and `MemoryError` bars"; OR122.a (1); CLAUDE.md memory rule (the whole
  suite passes at `gc.threshold(-1)` and at 32768 with zero `MemoryError`/"memory allocation failed" markers) (owner,
  2026-09-30).
- **Site**: `tests/_sensortask_scenarios.py` (after `:953-983`), registered in every `tests/test_sensortask_<device>.py`.
- **Change**: per generated device: build, `run_setups()`, `start_tasks()`, `supervise_tasks()` in a task (A.U20.06),
  then through the webserver dispatch: (1) `PUT /system {"SystemCmd": "resetconfig"}` → "Valid"; after the sequence
  the scenario's config directory holds no `config_*.cfg`, a reset is armed with code 7; a second build over the same
  directory boots on defaults (`GET /networking` Hostname = the device TOML's `hostname`, SSID ""), and its boot writes
  no file (A.U11.19). (2) `erasefram` → "Valid"; the device's fake chip (its TOML `max_size`, A.U24.22) is all zero,
  code 8; a rebuild's every FRAM-backed logger reads `ErrCount` 0. (3) the near-miss list → "Invalid", nothing changes.
  (4) allocation independent of chip size: `gc.mem_alloc()` growth across `erase_chip()` differs by less than 256 bytes
  between the 8 KB and the 256 KB fake (no per-byte allocation). The file runs at both stages through `scripts/test.sh`
  (`-1`, then `GC_THRESHOLD=32768`), whose marker gate fails on any `MemoryError` or "memory allocation failed" line.
- **Blast**: callers — · generated every device · js — · tests new scenarios; per-device wrappers pick them up by the
  existing registration · twin — · docs — · toml — · uart —.
- **Depends**: A.S0930.09-.17; A.U20.06, A.U24.22, A.U11.19 — A-C merges.
- **Kind**: test

### A.S0930.27 L2: the commands on the twin — function, states, hazards, watchdog, power loss
- **Why**: LEAD/R32 — State "test in … U25 (L2)"; OR118.a (1) "L2 twin"; OR120.a (3); OR122.a (1) (owner, 2026-09-30);
  V.U25.53 (the U25 actions this must adapt).
- **Site**: `scripts/_digital_twin_ci_suite.py` (a new run after A.U25.55's Run 12), new
  `tests/test_digital_twin_system_commands.py` (in-process, generated module on the twin), `tests/test_digital_twin_bus_hazard_concurrency.py`,
  A.U25.54's `tests/test_digital_twin_fram_crash_points.py`, `digital_twin/machine.py` `class SPI` (`:339-420`).
- **Change**: (1) CI suite Run 13 "system commands", per device (A.U25.48), fresh per-run state (A.U25.32/A.U25.35):
  (a) `PUT /system {"SystemCmd": "resetconfig"}` → "Valid"; the process ends with `_EXIT_SIMULATED_RESET` (A.U25.09);
  relaunch over the same `--config-dir`: the directory holds no `config_*.cfg`, `/networking` Hostname is the TOML's,
  `ResetReason` 7; (b) `erasefram` → "Valid" → reset exit → relaunch over the same `--fram-state-path`: every
  FRAM-backed errcount entry is counter 0, `ResetReason` 8; (c) the near-miss list → "Invalid" and the process keeps
  serving (uptime rises); `would_have_triggered_count == 0` on every launch. A.U25.55's Run 12 code list gains 7 and 8
  (read by `ast` from `src/system_service.py`, A.U25.36's helper). (2) states, in-process (the generated
  `_system_cmd_callback` called directly, as A.U25.57 does — no HTTP inside the DUT heap, A.U25.46): accepted during
  `start_timers()`; while a twin FRAM chunk write is suspended (the twin chip's `--hang`-style op delay, A.U25.37); with
  `mempause` active; concurrent with a reboot; both commands at once — outcomes as A.S0930.22. (3) hazards — in
  `test_digital_twin_bus_hazard_concurrency.py`: the erase racing a logger write on the twin chip (in-flight completes,
  later refused, no torn chunk), a sensor task cancelled inside its I2C session on a shared bus (the sibling's next
  read succeeds); the twin chip's rollover (A.U25.15) never reached (every unit address below `size`). (4) watchdog on
  the twin's real-time `WDT` (`digital_twin/machine.py:841-896`): healthy — the dev erase with a new twin SPI knob
  `wire_time_us_per_byte` (default 0; set to 8 for the 1 MHz bus, a blocking `time.sleep_us(len(buf) * 8)` per transfer,
  so the 256 KB erase takes its real ≈2.2 s of clock) ends with `would_have_triggered_count == 0`; hang per step (the same
  seven hang points as A.S0930.24 (c), injected from outside): after 8.5 s `would_have_triggered_count >= 1` and
  `feed_count` unchanged since the hang point — the twin records rather than resets (owner, 2026-08-12; A.U25.55); a
  blocking hang inside one SPI transfer (the knob set to a 9 s transfer for one unit) is caught by `WDT._arm()`'s
  late-feed backstop at the next own feed (`:865-877`). (5) power loss — A.U25.54's `SPI.lose_power_after(k)` over the
  erase on dev's layout: every k inside pass 1 and the transactions of the first and last pass-2 unit overlapping each
  allocated block; a fresh manager and stores over the same twin chip restore each ring exactly or blank; the reset
  command's delete loop cut by a test-side `os.remove` stand-in after k removals (as A.S0930.25). (6) gc bars — the
  suite's log gate (`scripts/_digital_twin_ci_suite.py`) at both stages covers Run 13; the in-process files run under
  `scripts/test.sh` at both.
- **Blast**: callers — · generated every device under the twin · js the live JS tier's command matrix
  (`tests_js/_live_matrix_command.js`, A.U23.33 lists `reboot`/`bootloader` as L1/C): the two new words are listed the
  same way (they end the twin process) · tests new as above; `tests/test_digital_twin_sensortask_integration.py:802`
  (`mempause` over the twin) holds · twin `digital_twin/machine.py` `SPI` gains `wire_time_us_per_byte`; fidelity table
  row (A.U25.01) "SPI wire time: off by default, 8 µs/byte for timing proofs" · docs `digital_twin/README.md` (the knob;
  Run 13) · toml — · uart —.
- **Depends**: A.S0930.09-.17; co-lands with A.U25.09 (reset exit), A.U25.15 (FRAM fake rollover and `silent` —
  `erasefram` against a `silent` chip is refused by the preflight: a case in (2)), A.U25.32/A.U25.35 (per-run
  `--config-dir`, so the reset deletes the run's files and never `digital_twin/config/`), A.U25.36/A.U25.55 (Run 12's
  code list gains 7 and 8; Run 5c's commanded-reboot path unchanged — reboot does not join the sequence, see Agent
  proposals), A.U25.37 (hang/fault vocabulary), A.U25.46 (no HTTP in the DUT heap), A.U25.54 (`lose_power_after()`) —
  A-C merges.
- **Kind**: test | code (twin knob)

### A.S0930.28 L3: the commands on the dev board over USB
- **Why**: LEAD/R32 — "test in … U26 (L3/L4, gated as stated)"; OR118.a (2)-(3) (owner, 2026-09-30); CLAUDE.md FRAM-log
  rule ("read the FRAM-persisted per-module error logs … BEFORE … otherwise clearing state"); OR120.a (3); OR122.a (1).
- **Site**: new `tests_hardware/flash/test_system_commands.py`; new device scripts
  `tests_hardware/device_scripts/system_command_config_reset.py`, `system_command_fram_erase.py`,
  `system_command_hang.py`; `fram_raw_dump.py` (A.U26.22); `tests_hardware/flash/test_bus_concurrency.py`.
- **Change**: every script builds the real generated dev system over a scratch config path (A.U26.10's pattern; scratch
  removed on every path, A.U26.18), takes board facts from the rendered dict (A.U26.44), calls the generated
  `_system_cmd_callback(<word>)` and ends in the product reset (`run_isolated_expect_reset()`). (1)
  `test_config_reset_deletes_every_config_file_and_reboots` `@pytest.mark.persistence_write` — the script first writes
  one changed value per store (so each scratch file exists), then `"resetconfig"`; after the reset a read-only script
  lists the scratch directory: empty; the production `config_*.cfg` names and bytes are unchanged (read before and
  after). (2) `test_fram_erase_blanks_the_chip_and_every_logger_restarts_empty` — first `save_fram_raw(board,
  "before-erase")` (A.U26.22: the command destroys the evidence by design); `"erasefram"`; after the reset and the
  production boot, `fram_raw_dump.py` over `[0, size)`: every byte outside the build's chunk layout (A.U16.02's pinned
  layout) is 0x00 and every chunk decodes as an empty ring or blank. Not wear-gated (FRAM is outside the gate,
  OR118.a (3)). (3) refusals in-script — the near-miss list through the callback's webserver dispatch → "Invalid", no
  reset; `"erasefram"` with the chip write-protected first (`set_write_protected(value=True)`, restored in `finally`)
  → "Failed", no reset. (4) states — the erase started while the script's own logger-write loop and an I2C read loop run
  (a FRAM write in flight, a bus session in flight); `mempause` active first. (5) bus hazard (flash tier of the
  four-tier rule) — `test_bus_concurrency.py` gains the erase racing a chunk write on the real chip: after the reset the
  raw dump shows no torn chunk. (6) watchdog on silicon — `system_command_fram_erase.py` wraps `sysfunct.watchdog` from
  outside with a recording proxy (forwards `feed()`, records `ticks_ms()`): the script prints the largest gap between
  feeds and the erase's duration; the test asserts the gap < 100 ms and records both figures (the per-unit cost the
  design leaves to phase C); `test_a_hung_shutdown_step_ends_in_a_watchdog_reset` `@pytest.mark.persistence_write`
  (scratch writes) — `system_command_hang.py` replaces one store's `delete_file` from outside with a never-ending
  coroutine, issues `"resetconfig"` and prints `HANG <ticks>`; the board resets 8.0-10.0 s after that line (serial
  loss timed by the harness), i.e. by the watchdog, never fed through the hang. (7) power loss —
  `test_a_reset_mid_erase_leaves_every_chunk_old_or_blank`: seed a known ring into every logger chunk, start the erase,
  `hard_reset()` at 0.2 s, 1.0 s and 2.0 s after the script's `ERASE START` line (inside the ≈2.2 s erase of the 256 KB
  chip), then the raw dump: each chunk holds the seeded ring or is blank, none other. (8) soak markers — each wrapper
  reads the script output through `MEMORY_ERROR_MARKERS` (A.U26.47).
- **Blast**: callers — · generated the dev image unchanged · js — · tests new; `tests_scripts/test_persistence_write_marker_completeness.py`
  and A.U26.06's guard see the markers; `tests_scripts/test_bench_restores_serving.py` covers the new modules (they run
  device scripts) · twin each script's twin run (A.U26.05) · docs `tests_hardware/README.md` "System commands" subsection
  (what each test spends: scratch flash writes behind `persistence_write`; the erase destroys the FRAM logs after the raw
  save) · toml — · uart — · hardware C (flash round).
- **Depends**: A.S0930.09-.17; A.U26.05, A.U26.10, A.U26.18, A.U26.22, A.U26.44, A.U26.47, A.U26.61 (a script that can
  outlast the watchdog feeds it in short steps — here the product feeds it) — A-C merges.
- **Kind**: test | hardware

### A.S0930.29 L4: the commands over REST on the bench
- **Why**: LEAD/R32 — "a config-reset test carries `persistence_write` and restores the bench unit's config files inside
  the same test; an Erase-FRAM test reads and archives the FRAM error logs first"; OR118.a (2) "a hardware reset test
  saves the dev board's config files first and restores them after (inside the same gated test), since the reset drops
  the bench unit's Wi-Fi"; OR118.a (3); OR120.a (3); OR122.a (1) (owner, 2026-09-30).
- **Site**: new `tests_hardware/bench/test_system_commands.py`; new device scripts `config_files_dump.py` (read-only)
  and `config_files_restore.py`; `tests_hardware/bench/test_bus_concurrency_under_api_load.py`;
  `tests_hardware/manual/` (power-cut step).
- **Change**: (1) `test_config_reset_over_rest_brings_back_the_defaults` `@pytest.mark.persistence_write`: start —
  leftover repair (A.U26.15's pattern: a board holding no `config_*.cfg` means an aborted earlier run; restore from the
  newest saved set, `result_note`); `save_errcount(dut_ip, …)` (A.U26.22); `config_files_dump.py` prints every
  `config_*.cfg` verbatim → saved to the evidence dir (A.U26.22's `save_text`); `PUT /system {"SystemCmd":
  "resetconfig"}` → "Valid"; passive wait for the reboot; the unit has no SSID now, so the bench joins its hotspot
  (`bench.join_dut_hotspot(<TOML hostname>, <TOML hotspot_password>)`, both read from the board's TOML, A.U26.49):
  `GET /status` `ResetReason` 7, `GET /networking` Hostname = the TOML's, SSID "", `GET /system` DebugLevel 0. `finally`:
  `leave_dut_hotspot_and_restore_bridge()`; `config_files_restore.py` writes the saved files back verbatim (one flash
  write per file, owned by this test); `hard_reset()` through A.U26.29's helper; serving on the bench WLAN with the
  saved SSID and hostname, verified by GET. (2) `test_fram_erase_over_rest_blanks_every_error_log`: `save_errcount()` and
  `save_fram_raw()` first (CLAUDE.md FRAM rule); `PUT … "erasefram"` → "Valid"; after the reboot `GET /status`:
  `ResetReason` 8, every FRAM-backed module's counter 0 and history empty (the set derived as A.U26.23 does). Not
  wear-gated. (3) `test_near_miss_action_words_do_nothing_over_rest`: the near-miss list over real HTTP → "Invalid"
  each, `SysUptime` keeps rising, config GETs unchanged — a bare or misspelt call does nothing (OR122.a (2)). (4)
  concurrency — `test_erase_reboot_and_mempause_at_once`: three threads send `erasefram`, `reboot`, `mempause`
  together: exactly one reset follows, and `ResetReason` is 8 when `erasefram` answered "Valid", 3 when `reboot` did
  (the other shutdown-side answers "Failed"); no flash write, so ungated. (5) bus hazard (bench tier of the four-tier
  rule) — `test_bus_concurrency_under_api_load.py` gains `erasefram` issued while its API hammer runs: reply "Valid",
  reboot with `ResetReason` 8, serving afterwards, every FRAM-backed log empty. (6) watchdog — (2) and (5) assert
  `ResetReason` 8 (the sequence's reset), not 2 (a watchdog reset); the reply-to-serving time is recorded
  (`result_note`) for phase C. (7) power loss — manual step appended to `tests_hardware/manual/manual_persistence.py`'s
  power-cycle tests: "issue `erasefram`, cut power within 1 s of the reply; after power returns the unit serves,
  `ResetReason` 1, and each FRAM-backed history is either its old content or empty; repeat with `resetconfig` (then
  restore the config files as (1) does)". (8) soak markers through A.U26.47's shared gate.
- **Blast**: callers — · generated — · js — · tests new; the wear guard (A.U26.06) and the marker completeness test
  (A.S0930.19) see (1) as marked and (2)-(5) as unflagged (`erasefram`, `reboot`, `mempause`) · twin — · docs
  `tests_hardware/README.md` "System commands" subsection (restore mechanics, hotspot join, evidence saved first) and
  the reset-code table (A.U26.28) rows 7/8 · toml — · uart — · hardware C (bench round; (1) only with
  `--allow-persistence-writes`).
- **Depends**: A.S0930.09-.17, A.S0930.19; A.U26.06, A.U26.15, A.U26.22, A.U26.23, A.U26.28, A.U26.29, A.U26.47,
  A.U26.49 — A-C merges.
- **Kind**: test | hardware

### A.S0930.30 The specification and the operator docs state the commands
- **Why**: LEAD/R32 — "doc in U36 (SPEC A.8, H, tests_hardware/README)"; Home "SPEC A.8; SPEC H"; OR121.a; OR122.a (2);
  CLAUDE.md FRAM-log rule (owner, 2026-09-08).
- **Site**: `SPECIFICATION.md` A.8 (`:611-613` PUT shapes), A.4 (`:226-231` reset path, FRAM bullet), A.7 (supervisor),
  C.3.1 (FRAM API), C.5.2/C.7.3, C.8, F.2, F.5, G.2 (`feed_watchdog()`), H (`:4378`, `:4525-4530` dispatch-only
  semantics), I.4; `tests_hardware/README.md:1336-1343`; `CLAUDE.md` FRAM-log rule.
- **Change**: SPEC A.8 `:612` "`"SystemCmd": "reboot"|"bootloader"|"mempause"`" → "… `|"resetconfig"|"erasefram"`", and a
  new paragraph "**The two shutdown commands** (owner, 2026-09-30): `resetconfig` ("Reset to defaults") deletes every
  config file and reboots — the unit comes back on the schema defaults, as the hotspot with its TOML hostname and
  hotspot password; FRAM logs and the SCD30's NVM are untouched. `erasefram` ("Erase FRAM") zeroes the whole chip and
  reboots — every FRAM log and the SGP40 backup start fresh. A command runs only on its exact word (no alias, prefix or
  case variant, owner, 2026-09-30); no confirmation step (owner, 2026-09-30). Both run one controlled sequence: take over
  the watchdog (the supervisor parks, is cancelled and awaited; every other feed is a no-op), close and flush the config
  stores, close FRAM (pause, then wait each chunk's operation), stop every supervised task, apply the purpose, reboot
  through the reset path — each step fed once and never timed out, so a hung step ends in a watchdog reset (owner,
  2026-09-30). Refused ("Failed") while a reset is armed or another command runs; a same command repeated answers
  "Valid". Reset codes 7, 8, 9." plus the design block's order rationale and power-loss table in compact form; A.4 FRAM
  bullet: the 0x00 erase and its two-gate proof, "a blank block reads as a new chip's"; A.4 `:226-231`: "every deliberate
  system reset pauses FRAM first" gains "the two shutdown commands close FRAM before stopping tasks"; A.7: the supervisor
  runs as its own task and parks for a shutdown; C.3.1: `quiesce()`, `erase_ready()`, `erase_chip()`; C.5.2/C.7.3:
  closed stores and `delete_file()`; C.8: the erase holds both FRAM locks per 256-byte unit; F.2: the commanded-reboot
  sentence gains the two commands and "a hung shutdown step ends in a watchdog reset"; F.5: the v1.29 forwarded-cancel
  fact (A.S0930.18); G.2: `feed_watchdog()` "the one reusable feed access point" gains "until a shutdown command takes
  ownership; then only the sequence's own feed"; H: the dispatch-only row names the exact-word rule and the two options
  (no dialog); I.4: the sequence's allocation is fixed (one task, one 256-byte unit). `tests_hardware/README.md` per
  A.S0930.19/.28/.29. CLAUDE.md FRAM-log rule "BEFORE issuing any `PUT /status {"ResetErrors": true}` call or otherwise
  clearing state" → "… call, a `SystemCmd` `"erasefram"`, or otherwise clearing state".
- **Blast**: callers — · generated — · js — · tests `tests_scripts/test_comment_block_cap.py` n/a; doc-reference checks
  (U33's) re-run · twin — · docs as above · toml — · uart —.
- **Depends**: U36 (doc owner), A.U11.05 (A.8 code table), A.U14.R01 (F.2 ladder text), A.U17.33 — A-C merges.
- **Kind**: doc

## Agent proposals (for the OR2.c review, not planned as firm)

1. **Reboot and bootloader on the same controlled sequence** (OR119.a (5): "an agent proposal for the OR2.c review, not
   part of this decision"). Today's and U11's reboot path flushes, pauses FRAM and arms the reset 4 s later while every
   task keeps running and the supervisor keeps feeding (A.U11.03/A.U11.04). Running `reboot`/`bootloader` through
   S1-S4 and S6 (no S5) would give them the same guarantees the two new commands get: no chunk torn by the reset (tasks
   stopped after FRAM is drained), no fed hang (ownership passes to the sequence), one code path for every commanded
   reset. Consequences: a commanded reboot takes up to one supervisor pass longer (≤ 2 s park); A.U11.03's
   `_reset_when_due()` final flush pass becomes redundant for commanded resets (it stays for the supervisor escalation);
   A.U25.36's Run 5c and A.U26.28's reboot/bootloader tests would assert the sequence's step lines too. Not planned:
   the decision is the owner's (OR119.a (5)). (No confirmation-dialog proposal is made: withdrawn by OR122.a (2).)

## C. Earlier actions at the same sites — closing inventory

Scope: every action of U11, U16, U17, U19, U20, U23, U24, U25, U26 and SUPP_recovery whose Site names a file this
supplement changes (found by script over the action files at HEAD, `scratchpad/al/S0930/sites.py`, 217 actions), plus
the actions this file cites that sit on other files. Verdicts: **co-land** — same lines or same mechanism, A-C merges
the edits into one; **own** — this file's action is the one that makes the change (the earlier action names it);
**blast-only** — same file, other lines; this file only has to keep it green.

| unit | co-land (with the action here) | own | blast-only |
|---|---|---|---|
| U11 | A.U11.03 (`_reboot()`, async reboots, `_reset_armed`, escalation, `_collect_config_stores()`, callback → .11-.14), A.U11.04 (`close_writes()`, `flush_pending()` → .16, conflict 1), A.U11.05 (codes, record → .15), A.U11.07 (decode test gains 7-9 → .21), A.U11.19 (missing file serves defaults → .16, .26, register fix 2), A.U11.22 and A.U11.28 (staging order, deferred flush in `flush_pending()` → .16), A.U11.31 (`ResetErrors` per field during the sequence → .22) | — | A.U11.01, .02, .06, .08, .10, .12, .15, .17, .20, .21, .23, .24, .25, .29, .30, .32, .34, .39 |
| U16 | A.U16.05, .06, .09 (same chunk class; .09 keeps an erased block blank across reads → .17), A.U16.10 (both locks → .17), A.U16.17 and A.U16.R03 (the manager's task is stopped in S4; `initialized` gates `erase_ready()` → .14, .17), A.U16.19 (`override_pause` gone; `invalidate()` is the erase's own path, conflict 4), A.U16.20 (legal sizes are 256-multiples → .17), A.U16.22 (chunk `get_size()` gone; the driver's is used → .17) | — | A.U16.01, .02 (layout pin used by .28), .03, .08, .13 (RAM-only log relied on), .15 (partial WP reads protected → preflight refuses), .16, .18, .21, .23, A.U16.R01 (one WREN retry per unit), A.U16.R02 |
| U17 | A.U17.21 (same bus-check function → .01), A.U17.32 (same roles function; its "both ends agree by construction" sentence changes, conflict 6 → .01), A.U17.30 (numbering of the Class B row → .07), A.U17.25 (tier map both modes → .04, .08) | — | A.U17.07, .08, .09, .10, .11, .15, .18, .19, .26, .29 (exerciser and changelog, other lines; .03 extends the same test file) |
| U19 | A.U19.04 (same dispatch guard → .09), A.U19.09 (same `_run()`; .18 pins its cancellation) | — | A.U19.01, .02, .03, .05, .06, .07, .08, .10, .11, .12, .13, .15, .16 (result words), .17, .20 (the REST reference lists the new values from `_SYSTEM_CMDS`), .22, .23 (feeder gap test; the supervisor runs as a task), .24 |
| U20 | A.U20.01 (one instance per UART bus → .01), A.U20.06 (`supervise_tasks()`, `self._tasks`; conflict 2 → .13), A.U20.17 (error contract for the new refusals → .01), A.U20.35 (L.3 table → .01), A.U20.41 and A.U20.42 (callback template → .11) | — | A.U20.02, .03, .04, .05, .07, .08, .10, .11, .13 (frozen set from imports), .14, .15, .16, .18, .20, .22, .25, .27, .30, .34, .38, .40 |
| U23 | A.U23.15 (select reset after Apply → .10, .20), A.U23.20 (code labels gain 7-9 → .15), A.U23.25 and A.U23.27 (mirror module and derived mock → .09, .20), A.U23.33 (the live tier lists the two words as L1/C like `reboot` → .27) | — | A.U23.03, .04, .05, .06, .08, .11, .12, .13, .14, .16, .17 (its `window.confirm` pattern is not used: OR121.a (2), OR122.a (2), conflict 5), .18, .19, .22, .23, .24, .26, .28, .29, .30, .40, .42, .45, .48, .49 |
| U24 | A.U24.07 (`feed_times` joins the reset hook → .24), A.U24.17 (contract suite gains `feed_times` → .24), A.U24.22 (FRAM fake size; `cut_after_bytes` → .21, .25), A.U24.27 (hazard file → .23), A.U24.43 (the supervisor scenario runs `supervise_tasks()` as a task and cancels it → .13), A.U24.54 (feed-site guard in the same file → .20), A.U24.79 (boot helpers used by .26) | — | A.U24.01, .06, .08, .15, .16, .18, .20, .21, .23, .24, .26, .31, .32, .36, .41, .45, .48, .50, .60, .63, .64, .65, .67, .69, .73, .74, .77, .78, .80 |
| U25 | A.U25.03 and A.U25.16 (twin `SPI` class gains `wire_time_us_per_byte` → .27), A.U25.07, .08, .09 (reset exit, `mem_backup`), A.U25.15 (rollover, `silent`), A.U25.32, .35 (per-run config dir and state), A.U25.36, .55 (Run 12 codes), A.U25.37 (vocabulary; `uart_link:silent` per CRC mode → .04), A.U25.46 (no HTTP in the DUT heap), A.U25.48 (device from data), A.U25.54 (`lose_power_after()`) — all → .04/.27 | — | A.U25.02, .04, .05, .06, .10, .12, .17, .19, .20, .22, .23, .24, .25, .28, .29, .30, .34, .38, .42, .57 (the `mempause` dispatch it drives now answers "Failed" during a shutdown), .59, .63, .64, .66, .68, .69, .71 |
| U26 | A.U26.01, .02, .03, .14 (bench board by TOML, image record, image check, reflash helper → .06), A.U26.05, .10, .18, .44, .47, .61 (twin runs of scripts, scratch config path, rendered dict, markers → .05, .28), A.U26.06, .71, .74 (wear guard → .19), A.U26.15, .22, .23, .28, .29, .49 (leftover repair, evidence, logger set, reset codes, reset helper, TOML values → .29), A.U26.33, .59, .82 (UART scripts both modes → .05, .06) | — | A.U26.54, .75, .85 |
| SUPP_recovery | A.U16.R03 (as U16 row) | — | A.U13.R02 (bus rung in the same hazard file), A.U16.R01, A.U16.R02 |
| others cited | A.U5.02 (`storage` parameter → .12), A.U6.03/.04 (definitions generated → .10), A.U6.23 (mock `ResetReason` sample → .15), A.U2.09 (codes named in `invalidate()` → .17), A.U3 (print-only refusals → .12), A.U10.07/.08 (feed-site pins → .13), A.U10.29 (`_SYSTEM_CMDS` const folding → .09), A.U14.R01 (F.2 text → .30) | — | — |

No earlier action is **own** for any change here: OR116-OR122 postdate every unit file (AC_NOTES item 27).

**Conflicts named for A-C:**
1. A.U11.04 checks `_closed` in `write_config()` "first, before the lock" and awaits `_pending_flush` without the lock;
   A.S0930.16 adds the re-check inside the lock and reads `_pending_flush` under it. Additive — without it a
   `write_config()` queued on the lock at close time could stage a flush after S2 returned. Keep both checks.
2. A.U20.06 runs the supervisor loop inline in `supervise_tasks()`, awaited by `main()`; A.S0930.13 runs it as a task
   (`self._supervisor_task`) with `supervise_tasks()` parked on an event, because OR120.a (1) requires the loop to be
   cancelled and awaited to done and `main()` must not end. A.U20.06's L0 test (`main()`'s awaited call order) holds;
   its direct-caller blast list adapts to a task (and A.U24.43's scenario).
3. A.U11.03 point 5 keeps the supervisor escalating to a reboot; A.S0930.13 suppresses escalation while a shutdown
   runs (the sequence reboots). Not a contradiction; A-C writes both into the one loop.
4. A.U16.19 removes `override_pause` as a test seam; A.S0930.17's `invalidate()` writes past the pause. It is the
   erase's own product path (OR117/OR36.a (3): a function of the chip — clearing it), called only by `erase_chip()`, and
   no test reaches it except through the erase; A-C must not read it as the seam returning.
5. The brief and LEAD/R32's earlier text named "U23's A.U23.17 confirm"; OR121.a (2) overtook the confirmation and
   OR122.a (2) withdrew even the proposal — nothing here uses `window.confirm`, and A.S0930.20 (5) asserts it is never
   called.
6. A.U17.32's sentence "the codec come from `UartLinkExerciser`'s own source defaults, so both ends agree by
   construction" no longer holds for the CRC once each end declares `crc`; A.S0930.01 adds the pair check in the same
   function, and A.U17.32's sentence becomes "`payload_size`, `timeout` and the framing codec come from the source
   defaults; the CRC mode is compared".
7. A.U26.71 rewrites the wear guard's dispatch-only derivation; A.S0930.19's value-level exception for `"resetconfig"`
   must be written into that derivation, not beside the removed `_ROUTE_DISPATCH_FIELDS`.

## Ledger
| register block | clause for this unit (short) | result |
|---|---|---|
| LEAD/R31 | code in U20 — `crc` TOML key, pair refusal, bus check counts the CRC length | A.S0930.01, A.S0930.02 |
| LEAD/R31 | code in U17 — `UartLinkExerciser` passes the CRC through | register fix 1: premise wrong at HEAD — the CRC is the bus object's (`asy_uart_driver.py:58, 76`), passed by codegen (A.S0930.02); no exerciser change |
| LEAD/R31 | test in U17/U24 — L1 both modes | DONE-AT-HEAD for the protocol layer (`tests/test_uart_comm_hazard.py:51, 1273-1296`; `tests/test_asy_uart_comm.py:2163`); exerciser layer A.S0930.03 |
| LEAD/R31 | test in U25 — L2 twin pair in both modes | A.S0930.04 |
| LEAD/R31 | test in U26 — L3 script in the other mode; L4 per mode, second behind `flash_cycle` | A.S0930.05, A.S0930.06 |
| LEAD/R31 | doc in U36 — SPEC J/L, DEVICE_REFERENCE, changelog Class B | A.S0930.07, A.S0930.08 (DEVICE_REFERENCE: no `uart_link` section exists, nothing to change); SPEC L via A.S0930.01's Blast |
| LEAD/R32 | code in U19 — `_SYSTEM_CMDS` | A.S0930.09 (exact-word rule); A.S0930.18 (DONE-AT-HEAD: the cancelled server closes its socket, pinned) |
| LEAD/R32 | code in U20 — definitions options, generated callback | A.S0930.10, A.S0930.11 |
| LEAD/R32 | code in U11 — `SystemService` | A.S0930.12 (gate), .13 (watchdog ownership, OR120), .14 (sequence), .15 (codes 7-9); `ConfigManager` (U11's file) A.S0930.16 |
| LEAD/R32 | code in U16 — FRAM manager erase | A.S0930.17 (pattern 0x00, proof in the design block) |
| LEAD/R32 | U23 — two dropdown options, existing rendering | no js code change (options rendered from data); L0 website tests A.S0930.20 (5); register fix 4 |
| LEAD/R32 | test in U19/U24 — L0/L1 | A.S0930.19, .20, .21, .22, .23, .24, .25, .26 |
| LEAD/R32 | test in U25 — L2 | A.S0930.27 |
| LEAD/R32 | test in U26 — L3/L4, gated as stated | A.S0930.28, A.S0930.29 |
| LEAD/R32 | doc in U36 — SPEC A.8, H, tests_hardware/README | A.S0930.30 (plus A.S0930.19's README sentence) |
| LEAD/R28 | read for the tier map (UART four-tier hazard coverage); no clause names this supplement | NO-CLAUSE — its tier map (A.U17.25, A.U26.82) gains the two CRC modes through A.S0930.03-.06 and .08 |

## Register fixes
1. **LEAD/R31** State "code in U20 (TOML key, buildgen pair check and bus-check CRC length), U17 (`UartLinkExerciser`
   passes the CRC through)" → "code in U20 (TOML key, buildgen pair check and bus-check CRC length, codegen passes the
   CRC to the UART bus constructor)". Evidence: the CRC is `asy_uart_driver.UART`'s constructor argument
   (`src/asy_uart_driver.py:58, 76`), read by `UART_Comm` from the bus (`asy_uart_comm.py:269, 282`); the exerciser
   passes the bus straight on (`asy_uart_link_driver.py:65-78`) and needs no change (A.S0930.02).
2. **LEAD/R32** Req "defaults are written by each `ConfigManager.setup()` at boot" → "each `ConfigManager.setup()` serves
   its defaults at the next boot (a missing file writes nothing, owner, 2026-09-26, OR71.a (2))". Evidence: HEAD writes
   them (`config_manager.py:459-460, 474-478`), but A.U11.19 implements OR71.a (2) ("a first boot with no config file
   writes nothing"); the reset's effect (defaults in force) is the same with fewer flash writes. OR117.a (1)'s phrase
   describes HEAD's path, not a decision to keep the write.
3. **LEAD/R32** Req "(pause every FRAM writer, hold the FRAM lock, overwrite the whole chip …)" → "(pause every FRAM
   writer and wait out each chunk's in-flight operation, then overwrite the whole chip in 256-byte units, each holding
   both FRAM locks …)". Evidence: exclusion comes from the pause plus the per-chunk drain (A.S0930.17); a single hold
   across the 1,024-unit erase is not needed and the per-unit hold is what lets the sequence feed per unit (OR120.a (2)).
4. **LEAD/R32** State "U23 (two dropdown options, existing rendering)" → "U23 (L0 website tests; the options are
   `buildgen/definitions.py`, U20's)". Evidence: `_SYSTEM_COMMAND_GROUP` lives in `buildgen/definitions.py:55-62`; the
   js renders options from definitions with no per-value code (`js/templates.js`, `js/render.js:188-240`).
5. **LEAD/R32** Sources `buildgen/definitions.py:57-61` → `:55-62` (the group spans `:55-62`, as OR121.a cites).

## Open points
None. Every choice was settled from the owner rows and the code: the action words (OR122.a (2) leaves them to the
agent, justified in the design block), the `crc` key optional with "none" as default (OR116.a (2): `dev.toml` keeps no
CRC), a command refused while a reset is armed (the more conservative option, OR2.c), the SCD30 NVM outside the
closed stores (OR119.a (2) names the flash filesystem and FRAM), the latch set at acceptance (stricter than OR120.a (1)).
The one owner-level item is OR119.a (5)'s, listed under Agent proposals for the OR2.c review.
