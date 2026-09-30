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
  run in both. The A.U17.25 L3 hazard script (H1a/H1b/H2/H3 over the jumper, U26's) takes the same parameter.
- **Blast**: callers the wrapper · generated — · js — · tests the flash-tier UART file (twice the runs, each bounded
  by its existing `timeout_s`) · twin each script's twin run (A.U26.05) in both modes · docs `tests_hardware/README.md`
  UART section "each crossover script runs with no CRC and with CRC16" · toml — · uart — · hardware C (flash round).
- **Depends**: A.U26.44 (rendered dict), A.U26.33, A.U26.59 (UART script folding), A.U17.25 (L3 hazard script) —
  A-C merges.
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
  the path. (2) The reflash steps (build, `picotool load -x -v`, BOOTSEL retry, passive wait for serving) move into one
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
- **Depends**: A.S0930.01, A.S0930.02, A.U26.01, A.U26.14, A.U26.22, U21's actions on `scripts/build_firmware.py`
  (A-C merges).
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
- **Depends**: A.U26.06 (wear guard sees device scripts, class markers, raw sockets — the L3 reset script is a device
  script) — A-C merges.
- **Kind**: test | doc

