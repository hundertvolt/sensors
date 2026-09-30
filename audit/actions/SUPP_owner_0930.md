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
   (`PrintLogHistoryStore.setup()`: `_read() or _write()`, `print_log.py:273-277`; SGP40 restores nothing) — the
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

