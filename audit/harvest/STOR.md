# Harvest — STOR: FRAM storage

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`, moved to `4dc80ef` by V11).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 44, INVAR 35, MIRROR 8, LIMIT 30, RISK 19, ASSUME 23, PLATFORM 19, SUPPRESS 7, TODO 5, OPENQ 2, DRIFT 8, NOTE 10 — 210 items.


## src/asy_fram_driver.py

- **STOR.N001** PLATFORM · `src/asy_fram_driver.py:5-6` — "MB85RS64V 8KB or MB85RS2MTA 256KB ...
  verified against the Fujitsu MB85RS64V (DS501-00015) and MB85RS2MTA (DS501-00032) datasheets" — Only
  these two parts are supported; which part `dev` really carries is open. · related: HW.T07, STOR.T07 ·
  [H01]
- **STOR.N002** INVAR · `src/asy_fram_driver.py:8-10` — "self-healing without raising (except
  __init__()/setup()'s one-time setup errors)" — Module never-raise contract outside setup. · related:
  BUS.T01 · [H01]
- **STOR.N003** PLATFORM · `src/asy_fram_driver.py:31-35` — "manufacturer ID, then the JEDEC
  continuation-code byte, then the two Product ID bytes ... fixed values for this specific chip,
  confirmed against the datasheet" — RDID layout 0x04/0x7F from datasheet. · related: STOR.T07 · [H01]
- **STOR.N004** DRIFT · `src/asy_fram_driver.py:5, 37-43` — "RDID-detected via _KNOWN_PRODUCT_IDS" /
  "keyed by max_size so setup() can tell which of this codebase's two known SPI FRAM breakouts is
  actually wired" — Code only verifies the product ID expected for the *configured* `max_size`
  (:183-188) and raises "not found" on any other; it does not detect which chip is wired (low). ·
  related: STOR.T07, HW.T07 · [H01]
- **STOR.N005** PLATFORM · `src/asy_fram_driver.py:40-43` — "0x2000: 0x0302, # MB85RS64V ... p.10" /
  "0x40000: 0x4803, # MB85RS2MTA ... p.10" — Product IDs with datasheet page citations. · related:
  STOR.T07 · [H01]
- **STOR.N006** PLATFORM · `src/asy_fram_driver.py:61-62` — "Block protection always covers the whole
  array (BP0+BP1 together), never a sub-range." — Design choice + SR bit layout from datasheet; partial
  BP settings treated as unprotected. · covered-by: STOR.S03 · [H01]
- **STOR.N007** ASSUME · `src/asy_fram_driver.py:74-77` — "Generous headroom over a real transaction's
  low-single-digit-ms cost" / "MicroPython inlines const() at every use site regardless of name
  (verified directly)" — 1.0 s verify_present lock timeout rests on an unmeasured transaction cost;
  const-inlining platform fact. · related: PLAT.T02 · [H01]
- **STOR.N008** INVAR · `src/asy_fram_driver.py:79-81, 88-90` — "awaiting a persisted log entry is not
  something a body holding the bus lock may do" — Sync bodies must never log/await under the bus lock;
  by convention (status bitsets route to reporters). · related: STOR.S02, STOR.T04 · [H01]
- **STOR.N009** MIRROR · `src/asy_fram_driver.py:83-94` — "_W_PROTECTED = const(1) # wrnno 84" ...
  "_SV_NOT_LOCKED = const(32) # errno 99 (get) / 100 (set)" — Status-bit → errno/wrnno map mirrored in
  SPECIFICATION.md C.7.1 row (:1926). · related: STOR.T08, XCUT.T07 · [H01]
- **STOR.N010** INVAR · `src/asy_fram_driver.py:115-117` — "safe since every real caller only ever
  reaches these through this object's own asy_lock (Lockable), serializing access" — Shared scratch
  buffers; `setup()` and `set_write_protected()` reach them under the bus lock only, not `asy_lock`
  (low). · related: STOR.T04 · [H01]
- **STOR.N011** SETTLED · `src/asy_fram_driver.py:122-130` — "a second SPI device then waits ~25 CS
  rather than ~5 (SPECIFICATION.md C.8 records the owner's choice of that trade)" — Owner decision:
  driver lock + bus lock held for a whole block; lock order driver→bus. · related: STOR.T04, PERF.T04 ·
  [H01]
- **STOR.N012** SUPPRESS · `src/asy_fram_driver.py:147-148` — "except RuntimeError: # already released
  somehow - same tolerance Lockable's own exit has" — Double-release of the bus lock swallowed silently.
  · related: CORE.S13 · [H01]
- **STOR.N013** PLATFORM · `src/asy_fram_driver.py:155-156` — "WREN/WRDI are each a complete, standalone
  one-byte command (datasheet timing diagrams show CS low only for the opcode)" — CS framing from
  datasheet. · related: STOR.T11 · [H01]
- **STOR.N014** LIMIT · `src/asy_fram_driver.py:183-185` — "has no known product ID to verify against -
  add it to _KNOWN_PRODUCT_IDS" — Any other chip size raises at setup (only 0x2000/0x40000 supported). ·
  related: STOR.T07 · [H01]
- **STOR.N015** PLATFORM · `src/asy_fram_driver.py:201-203` — "Verifying via RDSR instead of trusting
  WREN blindly catches a corrupted WREN transfer, which the chip would otherwise silently ignore" — WEL
  gating fact from datasheet. · related: STOR.T03 · [H01]
- **STOR.N016** RISK · `src/asy_fram_driver.py:207-210, 328-329, 348-349` — "one cheap retry, then
  False, which the caller turns into a warning: a stuck latch doesn't undo the operation" — Stuck WEL
  after a write is accepted: persisted wrnno 81 and the write reports success. · related: STOR.T03 ·
  [H01]
- **STOR.N017** LIMIT · `src/asy_fram_driver.py:217-220, 239` — "WP active-low" / "deassert WP first -
  WP=0 would else block this WRSR too" — wp_pin modelled as whole-array protection; unreachable in
  production. · covered-by: STOR.S06 · [H01]
- **STOR.N018** SETTLED · `src/asy_fram_driver.py:224-226, 340-343` — "WP8: persisted by the caller,
  matching AsyFramManager's own \"communication paused, not writing\" precedent ... wrnno=60/70/80" —
  Refused write under protection is a persisted wrnno 84, one per refused write; "WP8" is an undefined
  label. · related: STOR.S05, DOC.S16 · [H01]
- **STOR.N019** LIMIT · `src/asy_fram_driver.py:234, 358` — "Always protects the entire array (BP0+BP1)
  - per-block ranges are unused." — No partial protection support. · related: STOR.T03 · [H01]
- **STOR.N020** ASSUME · `src/asy_fram_driver.py:255-256` — "Buffer width is fixed once in __init__ from
  max_size, which is trusted, not re-derived from _check_device_id() - see SPECIFICATION.md Part C.3.1"
  — Address width trusts configured `max_size`. · related: STOR.T07 · [H01]
- **STOR.N021** ASSUME · `src/asy_fram_driver.py:269-271` — "without one, this is the cached value from
  the last verified set_write_protected() call (see there for why re-reading the status register on
  every get isn't needed)" — Cached WP state; set_write_protected() carries no such explanation (the
  nonvolatile note is at :387) (low). · related: STOR.T03 · [H01]
- **STOR.N022** INVAR · `src/asy_fram_driver.py:281-283` — "on a bus lock the caller already holds
  (SPI.configure()'s own guard enforces that)" — Enforcement named: `SPI.configure()` guard
  (`src/asy_spi_driver.py`). · related: BUS.T04 · [H01]
- **STOR.N023** LIMIT · `src/asy_fram_driver.py:286, 319` — "if not self.asy_lock.locked(): # from
  Lockable class" — The guard proves only that *someone* holds the driver lock, not the caller
  (asyncio.Lock has no owner) (low). · related: STOR.T04 · [H01]
- **STOR.N024** SETTLED · `src/asy_fram_driver.py:299-302, 320-322` — "WP8: an internal-contract
  violation ... a real code defect if it ever fires, so errno rather than wrnno" — errno 99/100
  classification decision. · related: XCUT.T07 · [H01]
- **STOR.N025** LIMIT · `src/asy_fram_driver.py:273, 297, 331, 362, 405` — err_s "FRAM not initialized,
  run setup first!" errno=89/90/92/94/96 — Degraded mode after a failed setup: every FRAM op logs and
  refuses (into the FRAM driver's logger). · related: XCUT.S08 · [H01]
- **STOR.N026** LIMIT · `src/asy_fram_driver.py:304, 337` — err_s "get_values: Invalid FRAM address
  range!" / "set_values: ..." errno=91/93 — Range refusal messages. · related: STOR.T07 · [H01]
- **STOR.N027** LIMIT · `src/asy_fram_driver.py:346, 371` — wrn_s "FRAM write enable latch did not set,
  aborting write." wrnno=82 / "... write protection not changed." wrnno=83 — Degraded paths (write
  dropped). · related: STOR.T03 · [H01]
- **STOR.N028** INVAR · `src/asy_fram_driver.py:357-360` — "it must NOT be called from inside `async with fram:`
  - asyncio.Lock isn't reentrant and that would hang, the same caveat verify_present() carries" — Caller
  discipline; set_write_protected has no production caller. · covered-by: STOR.S05 · [H01]
- **STOR.N029** LIMIT · `src/asy_fram_driver.py:375-376` — err_s "FRAM write protection readback
  mismatch, not applied!" errno=95 — WRSR verify failure path. · related: STOR.T03 · [H01]
- **STOR.N030** PLATFORM · `src/asy_fram_driver.py:387-388` — "WPEN/BP0/BP1 are nonvolatile (datasheet)
  - re-sync _wp from hardware, not the ctor's wp=." — `_wp` only if SR&0x8C == 0x8C exactly. ·
  covered-by: STOR.S03 · [H01]
- **STOR.N031** LIMIT · `src/asy_fram_driver.py:392-393` — raise OSError("FRAM SPI device not found.") —
  A present chip with a different product ID (other part than configured) reports "not found". ·
  related: HW.T07 · [H01]
- **STOR.N032** PLATFORM · `src/asy_fram_driver.py:396` — "WP is active-low (datasheet)" — Pin polarity
  (low). · related: STOR.S06 · [H01]
- **STOR.N033** INVAR · `src/asy_fram_driver.py:401-411` — "Wait is bounded, not a bare `async with self:`,
  since asyncio.Lock isn't reentrant" — verify_present bounded wait (errno 97 "lock busy, giving up");
  no production caller. · covered-by: STOR.S05 · [H01]
- **STOR.N034** SETTLED · `src/asy_fram_driver.py:423-427` — "Provably unreachable ... kept per Part
  E.5.1's documented precedent for this exact class of defensive branch, not chased." — Deliberate dead
  defensive branch (errno 98). · related: TEST.T09 · [H01]

## src/asy_fram_manager.py

- **STOR.N035** INVAR · `SPECIFICATION.md:373-374 (via src/asy_fram_manager.py:3)` — "instantiation
  order is on-chip layout and must stay identical across firmware versions" — Chunk addresses depend
  purely on construction order; nothing but order discipline protects persisted layout. · related:
  XCUT.T09 · [H01]
- **STOR.N036** INVAR · `src/asy_fram_manager.py:3` — "every method returns a well-defined value - never
  raises" — Module-wide never-raise contract (constructors excepted implicitly). · related: BUS.T01 ·
  [H01]
- **STOR.N037** MIRROR · `src/asy_fram_manager.py:35` — "_TS_FMT = const(\"<Q\") # explicit
  little-endian, no padding - matches print_log.py's own convention" — Timestamp format duplicated with
  print_log.py. · related: STOR.T06 · [H01]
- **STOR.N038** ASSUME · `src/asy_fram_manager.py:36, 544, 597-600` — "_TS_UNINIT = const(b\"\\x00\")" —
  Timestamp 0 is the "no valid time" sentinel; a real epoch-0 time is indistinguishable. · covered-by:
  STOR.T09 · [H01]
- **STOR.N039** INVAR · `src/asy_fram_manager.py:38, 91` — "_WRN_EPISODE_BASE = const(60) #
  _episode_wrn()'s bitmask origin: this module's lowest wrnno" — `1 << (wrnno - 60)` requires every
  episode wrnno ≥ 60; by convention. · related: STOR.T08 · [H01]
- **STOR.N040** INVAR · `src/asy_fram_manager.py:61-62` — "crc_checks.py needs one instance per
  concurrent sequence - safe since fram's lock limits this manager to one
  _read_chunk/_write_chunk/_clear_chunk body running at a time" — CRC state safety depends on all CRC
  use sitting inside the FRAM lock. · related: STOR.T04 · [H01]
- **STOR.N041** INVAR · `src/asy_fram_manager.py:66-71` — "fram's lock only serializes one block at a
  time (released between block 0 and block 1); this one serializes this chunk's own
  write()/read()/clear()" — Two-lock design; scratch reuse safe only under `_op_lock`. · covered-by:
  STOR.T04 · [H01]
- **STOR.N042** LIMIT · `src/asy_fram_manager.py:73-78` — "Degrades exactly as the per-call allocation
  did: _compare_with() then reports the block as \"not verifiably valid\", and a read falls back to
  rewriting it." — Degraded mode after a failed check-buffer allocation: every read rewrites block 1
  (extra FRAM writes, wrnno 73) and verification always fails. · related: STOR.T02 · [H01]
- **STOR.N043** SETTLED · `src/asy_fram_manager.py:87-90` — "C.7.1's repeat rule, per DISTINCT code. A
  corrupted block or a held mempause warns on EVERY operation" — Per-episode persistence rule for wrnno
  60/70-73. · related: XCUT.T07, SENS.T15 · [H01]
- **STOR.N044** DRIFT · `src/asy_fram_manager.py:88-90 vs :622, 672, 716` — "a slot per operation
  refills the owner's bounded history by itself" — Chunks are constructed with `logger=self.pr` (the
  manager's RAM-only logger), not the owner's history. · covered-by: XCUT.S08 · [H01]
- **STOR.N045** LIMIT · `src/asy_fram_manager.py:98-100, 130-132, 391-393` — wrn "FRAM communication
  paused, not writing FRAM!" (60) / "not reading" (70) / "not clearing" (80) — Pause drops
  writes/reads/clears (not deferred); `clear()`'s wrnno 80 bypasses `_episode_wrn`. · covered-by:
  STOR.T05 · [H01]
- **STOR.N046** LIMIT · `src/asy_fram_manager.py:101-103, 133-135` — err_s "Data size ... does not match
  chunk size ..." errno=60/70 — Caller-size mismatch refused. · [H01]
- **STOR.N047** LIMIT · `src/asy_fram_manager.py:114-124` — err_s "Block n write verification error!"
  errno=63+n — Periodic verify every `_verify` writes (SGP40's verify period computation). · related:
  SENS.S02 · [H01] ⟨quote not matched at the anchor⟩
- **STOR.N048** RISK · `src/asy_fram_manager.py:153-155, 168-170` — "writing failed, means something is
  really wrong, better do not use data" — A failed repair write turns a readable valid copy into a
  failed read (errno 71/72). · related: STOR.T02 · [H01]
- **STOR.N049** SETTLED · `src/asy_fram_manager.py:173-177` — "Deliberate: no generation counter says
  which block is newer, so a write torn between blocks leaves two self-consistent but differing copies -
  a hard failure, not a guess." — Torn inter-block write → errno 73 on every read until the next
  successful write. · covered-by: STOR.T02 · [H01]
- **STOR.N050** LIMIT · `src/asy_fram_manager.py:235-239` — "uninit = True # no error yet" — UNINIT
  status then overwritten with BUSY; a second read reports invalid rather than uninitialised. ·
  covered-by: STOR.S01 · [H01]
- **STOR.N051** MIRROR · `src/asy_fram_manager.py:240-242, 256-258, 273, 285, 298, 342, 363` — "only
  check_idle=True needs the 3-wide spread (matches the gap below)" / "check_idle=False here, so
  _handle_status_bytes may only set err to err + 1" — Errno base+spread arithmetic (10-11, 19-20, 30-36,
  39-40, 50-51) kept in step with C.7.1 row (SPECIFICATION.md:1930) by hand. · related: STOR.S04,
  XCUT.T07 · [H01]
- **STOR.N052** SUPPRESS · `src/asy_fram_manager.py:288-290` — err_s "General write error in
  _write_chunk:" errno=26 — Any exception in a block write swallowed to False. · [H01]
- **STOR.N053** LIMIT · `src/asy_fram_manager.py:319-322` — "a zero-length buf (e.g. check_length=0)
  would never advance" + err_s errno=48 — Guard against a caller-supplied zero check_length. · [H01]
- **STOR.N054** SUPPRESS · `src/asy_fram_manager.py:353-356` — err_s "General read error in
  _read_chunk:" errno=47 — Any exception in a block read swallowed. · [H01]
- **STOR.N055** SUPPRESS · `src/asy_fram_manager.py:373-375` — err_s "General write error in
  _clear_chunk:" errno=58 — Any exception in clear swallowed. · [H01]
- **STOR.N056** INVAR · `src/asy_fram_manager.py:439-440` — "84, not 80: 80 is
  _AsyBaseFramChunk.clear()'s own errno, sharing this chunk's logger" — Errno uniqueness across chunk
  classes + FRAM_SPI sharing one logger (manager errno 83/84 vs driver wrnno 81-84 differ only by kind);
  by convention. · related: XCUT.T07 · [H01]
- **STOR.N057** SUPPRESS · `src/asy_fram_manager.py:538-543, 603-608` — "caller-supplied callback ...
  guarded broadly since it isn't guaranteed to be a specific, known-safe implementation" err_s
  errno=85/87 — NTP-sync callback failures swallowed to "not synced". · related: STOR.T06 · [H01]
- **STOR.N058** DRIFT · `src/asy_fram_manager.py:560-564` — err_s "Unpacking Timestamp failed:" errno=82
  — The guarded operation is `struct.pack_into` (packing), message says unpacking (low). · [H01]
- **STOR.N059** SUPPRESS · `src/asy_fram_manager.py:594-597` — "except Exception: ts = _TS_UNINIT[0]" —
  Timestamp unpack failure silently treated as "no timestamp" (no log). · [H01]
- **STOR.N060** LIMIT · `src/asy_fram_manager.py:609-614` — "age = time.mktime(time.gmtime()) - ts" —
  Age can be negative/jump across clock changes; err 88 only on OverflowError/OSError. · covered-by:
  STOR.T09 · [H01]
- **STOR.N061** INVAR · `src/asy_fram_manager.py:623-624, 631-633` — "matches self.pr.name - the
  _ModuleLike registration shape" / "matches base_classes.py's SensorReader.get_error_sources() shape,
  duck-typed rather than inherited" — Duck-typed registration shape mirrored with SensorReader and
  asy_webserver_service.py; convention only. · related: CORE.T09 · [H01]
- **STOR.N062** LIMIT · `src/asy_fram_manager.py:648-650, 690-692` — pr.err "Zero-size chunk requested,
  rejected!" — Print-only rejection (not persisted). · related: STOR.S08 · [H01]
- **STOR.N063** LIMIT · `src/asy_fram_manager.py:661-663, 703-705` — pr.err "FRAM out of memory!" —
  Print-only; owner silently runs RAM-only. · covered-by: STOR.S08 · [H01]
- **STOR.N064** SUPPRESS · `src/asy_fram_manager.py:732-736` — err_s "FRAM Setup failed:" errno=83 —
  Setup failure swallowed to False; the generated `build_system()` ignores the result. · related:
  PAR.S12 · [H01]
- **STOR.N065** LIMIT · `src/asy_fram_manager.py:96, 128, 389` — "override_pause: bool = False" —
  Test-only parameter on shipped API. · covered-by: STOR.S07 · [H01]

## src/print_log.py

- **STOR.N066** RISK · `src/print_log.py:273-279` — "if await self._read() or await self._write():
  self.initialized = True" — Any transient read failure at boot overwrites the persisted ring
  (FRAM-evidence rule) · covered-by: CORE.S16 · [H02]

## tests/_fram_chip_fake.py

- **STOR.N067** SETTLED · `tests/_fram_chip_fake.py:37-39` — "genuinely undetectable at this layer by
  design - payload-level data integrity is asy_fram_manager.py's CRC/dual-copy job" — payload corruption
  is by design invisible to the driver · related: STOR.T02 · [H03]
- **STOR.N068** ASSUME · `tests/_fram_chip_fake.py:41-44` — "None models WP tied high, the driver's
  assumption without a wp_pin" — the driver assumes WP is tied high when no wp_pin is given · related:
  STOR.S06 · [H03]
- **STOR.N069** PLATFORM · `tests/_fram_chip_fake.py:28` — "correct MB85RS64V ID by default" — RDID `04 7F 03 02`
  is the only product ID modelled · related: STOR.T07 · [H03]
- **STOR.N070** INVAR · `tests/_fram_chip_fake.py:108-109` — "on real hardware an overrun leaves partial
  garbage there, which is why the caller must not trust it" — fake raises before filling the buffer,
  unlike real hardware; callers must never rely on buffer content after a raise · [H03]

## tests/_sensortask_scenarios.py

- **STOR.N071** INVAR · `tests/_sensortask_scenarios.py:422-428` — "Every FRAM-chunk-owning module
  degrades to in-memory-only on allocation failure rather than raising (base_classes.py's contract)" —
  this scenario is also the per-device "does everything fit" capacity check, and only on the mock FRAM ·
  related: XCUT.T09 · [H03]
- **STOR.N072** SETTLED · `tests/_sensortask_scenarios.py:501-503` — "Owner requirement: no module may
  insist on FRAM availability" — every FRAM-backed log must work in RAM; SGP40 must run without
  backup/restore · [H03]

## tests/test_asy_fram_driver.py

- **STOR.N073** PLATFORM · `tests/test_asy_fram_driver.py:104-105,117-119` — "Real hardware finding:
  MB85RS2MTA reports product ID bytes 0x48, 0x03" — product-ID byte order and the 256 KB part's ID
  (datasheet p.10) · related: HW.T07, STOR.T07 · [H03]
- **STOR.N074** SETTLED · `tests/test_asy_fram_driver.py:403-405,695-696` — "a stuck-set WEL after both
  attempts is only ever warned about, not treated as a failed write" — WEL left set after the WRDI retry
  is housekeeping, not a failure · related: STOR.T03 · [H03]
- **STOR.N075** PLATFORM · `tests/test_asy_fram_driver.py:427-429` — "WPEN/BP0/BP1 are nonvolatile FRAM
  cells, unlike WEL which resets at power-on" — datasheet fact behind trusting the status register over
  `wp=` · related: STOR.S03 · [H03]
- **STOR.N076** PLATFORM · `tests/test_asy_fram_driver.py:544,565-567` — "WP is active-low" /
  "WEL=1/WPEN=1/WP=0 makes the status register itself unwritable" — datasheet write-protect table the
  wp_pin logic depends on · related: STOR.S06 · [H03]
- **STOR.N077** INVAR · `tests/test_asy_fram_driver.py:653-655` — "calling it inside an existing `async with fram:`
  would hang forever, asyncio.Lock not being reentrant" — `verify_present()` must never be called while
  holding the FRAM lock (caller discipline) · related: STOR.S05 · [H03]
- **STOR.N078** SETTLED · `tests/test_asy_fram_driver.py:795-829` — "Deliberately-allowed exception
  paths - inherited from asy_spi_driver.py, never caught here" — an invalid Pin at boot raises; a bus
  deinitialized under an in-flight FRAM_SPI raises RuntimeError, "the caller's responsibility"
  (signed-off precedent) · related: BUS.T06 · [H03]
- **STOR.N079** SETTLED · `tests/test_asy_fram_driver.py:847-865` — "what this layer cannot catch, by
  design (not a bug)" — the driver never verifies payload bytes; a corrupted payload reports success ·
  related: STOR.T02 · [H03]
- **STOR.N080** RISK · `tests/test_asy_fram_driver.py:895-897` — "the routine caller-contract signals
  stay on the plain, non-persisted err()/wrn()" — some FRAM driver signals are print-only by design ·
  related: STOR.S08, XCUT.T07 · [H03]
- **STOR.N081** INVAR · `tests/test_asy_fram_driver.py:1161-1162,1231-1233` — "one acquire/release and
  exactly one scheduler pass per byte-level command, whatever its CS-cycle count" — per-command bus-lock
  and yield policy (M7) is pinned here · related: BUS.T03, PERF · [H03]
- **STOR.N082** INVAR · `tests/test_asy_fram_driver.py:1321-1322` — "Without __aenter__'s try/except the
  driver's own lock would leak permanently" — two-lock entry must release the outer lock if the inner
  acquire fails · related: STOR.T04 · [H03]

## tests/test_asy_fram_manager.py

- **STOR.N083** INVAR · `tests/test_asy_fram_manager.py:88-90` — "call order must stay identical across
  firmware versions for stored data to decode" — the bump allocator's static layout is a
  cross-firmware-version compatibility contract upheld only by construction order · related: XCUT.T09,
  PAR · [H03]
- **STOR.N084** SETTLED · `tests/test_asy_fram_manager.py:329-331` — "no generation counter can say
  which is right, so this must fail, not guess" — a write torn between the two blocks (both IDLE,
  different data) is unreadable by design · related: STOR.T02, STOR.T12 · [H03]
- **STOR.N085** SETTLED · `tests/test_asy_fram_manager.py:392-394` — "a deliberate reboot pauses storage
  right before resetting ... an operator-triggered REST \"mempause\" pauses writes for a bounded
  maintenance window" — pause semantics and callers · related: STOR.T05 · [H03]
- **STOR.N086** SETTLED · `tests/test_asy_fram_manager.py:886-888` — "Intended, accepted behavior, not a
  defect (project owner, 2026-09-11; Part A.4): _read_chunk() must WRITE a transient busy marker before
  it reads" — reads are blocked under write protection · covered-by: STOR.T10 · [H03]
- **STOR.N087** INVAR · `tests/test_asy_fram_manager.py:754-755` — "a bench session reads these numbers
  out of the FRAM log to tell this apart from a real read failure (errno 37)" — errno 48 vs 37 is a
  diagnostic contract · related: STOR.T08 · [H03]
- **STOR.N088** RISK · `tests/test_asy_fram_manager.py:1334-1336,1370` — "_TS_UNINIT (0) doubles as both
  \"never written\" and the literal Unix epoch ... Inherited from the deployed design ... locked down as
  real, documented behavior" — a timestamp of exactly 0 reads as uninitialized; pinned current behaviour
  · covered-by: STOR.T09 · [H03]
- **STOR.N089** RISK · `tests/test_asy_fram_manager.py:1464-1466` — "Surprising but harmless: ... a
  negative verify makes (1 >= negative) true on the first write and verification runs every time." —
  pinned behaviour for a negative `verify` · [H03]
- **STOR.N090** RISK · `tests/test_asy_fram_manager.py:2159-2160` — "pack_into's own failure is
  swallowed (errno=82 logged) - the write itself still proceeds with whatever the tbuf ended up holding"
  — a failed timestamp pack still writes the chunk; tolerated under the never-raises contract · related:
  STOR.T06 · [H03]
- **STOR.N091** LIMIT · `tests/test_asy_fram_manager.py:2120-2122` — "struct.pack_into() and
  unpack_from() cannot fail through real use ... so this fakes the `struct` reference" — guard reachable
  only by faking · [H03]
- **STOR.N092** SETTLED · `tests/test_asy_fram_manager.py:2301-2333` — "Intended behavior, not a defect
  (Part A.4): ... an interruption leaves both copies marked. MB85RS64V reads are destructive internally"
  — an interrupted read leaves both blocks BUSY and the data is refused until the next write ·
  covered-by: STOR.T10 · [H03]
- **STOR.N093** INVAR · `tests/test_asy_fram_manager.py:2336-2338` — "the numbers and the public entry
  point they are reachable from are the contract (Part C.7.1)" — status-byte errno spread is a published
  contract · related: STOR.T08, XCUT.T07 · [H03]
- **STOR.N094** INVAR · `tests/test_asy_fram_manager.py:2477-2479,2509-2511` — "A block operation that
  never yielded would show only one of the two." — per-command yield placement (incl. before the
  blank-chip early return) is pinned · related: PERF · [H03]
- **STOR.N095** SETTLED · `tests/test_asy_fram_manager.py:2585-2587` — "Episode-scoped per distinct
  code, like asy_uart_comm.py's own _episode_wrn(); SPECIFICATION.md Part C.7.1 states the rule." —
  degraded-condition warnings persist once per episode · related: XCUT.T07 · [H03]

## tests/test_asy_fram_wire_trace.py

- **STOR.N096** SETTLED · `tests/test_asy_fram_wire_trace.py:1-2` — "A restructure ... must leave these
  byte-identical - the contract the owner's approved restructure was held to
  (HEAP_FRAGMENTATION_MEASUREMENTS.md archive 3B)" — FRAM wire traces are a pinned contract; "archive
  3B" resolves only against an older commit · related: DOC.S04 · [H03]
- **STOR.N097** SETTLED · `tests/test_asy_fram_wire_trace.py:499-501` — "Every one of these cycles is
  required by the chip; the restructure removes allocations, not CS cycles, so a change here is a
  protocol change and not an optimisation." — CS-cycle counts are fixed by decision · related: BUS.S03 ·
  [H03]
- **STOR.N098** ASSUME · `tests/test_asy_fram_wire_trace.py:519-521` — "The chip auto-clears WEL after a
  WRITE, so the skipped WRDI's own verification still passes" — the WRDI after WRITE is
  datasheet-redundant; only the trace notices its removal (the fake models the auto-clear) · related:
  STOR.T03 · [H03]

## tests/test_asy_sgp40_driver.py

- **STOR.N099** INVAR · `tests/test_asy_sgp40_driver.py:1556-1561` — "its allocated_size bump pointer
  keeps advancing, so a second SGP40_Reader would land its chunks in a fresh, never-written region" —
  FRAM chunk placement depends on replaying the identical allocation sequence on a fresh manager
  (deterministic layout contract) · related: XCUT.T09 · [H04]

## tests/test_base_classes.py

- **STOR.N100** ASSUME · `tests/test_base_classes.py:682-684, 694-696` — "AsyFramManager.get_chunk()
  never actually raises (confirmed by its own src/ promotion audit)" — Claims about the real manager
  (get_chunk never raises; `_write_chunk` wraps its whole body) rest on a past promotion audit and are
  exercised only through fakes · [H05]
- **STOR.N101** ASSUME · `tests/test_base_classes.py:1081-1083` — "allocated_size can never exceed size
  by construction, so that comparison alone is a tautology" — WP4/Topic 6's per-device FRAM-capacity
  check is only meaningful through the None-chunk signal; a check using allocated_size alone would be
  vacuous (retired WP4/Topic 6 ID) · related: TEST.T01 · [H05]

## tests/test_fram_integration.py

- **STOR.N102** DRIFT · `tests/test_fram_integration.py:3-5` — "Real RP2040 SPI write()/readinto()
  cannot raise or report a fault at all once constructed" — Contradicts SPECIFICATION.md F.5.2
  (:3710-3714) and CLAUDE.md: since 1.29 rp2 SPI readinto() of 32+ bytes can raise OSError(EIO);
  test_bus_hazard_multi_device.py:466 relies on that raise. The "deliberately not modeled" SPI fault
  rationale is stale · related: CORE.T11 · [H05]
- **STOR.N103** SETTLED · `tests/test_fram_integration.py:296-301` — "That loss is accepted behavior,
  not a defect (project owner, 2026-09-11)" — Power loss leaving both blocks BUSY loses the history; no
  recovery scheme wanted; only all-or-nothing is required · related: STOR.T12 · [H05]
- **STOR.N104** INVAR · `tests/test_fram_integration.py:219-221` — "reattaching fresh manager and reader
  objects to the same chip, in the same instantiation order, must decode both" — FRAM layout depends on
  a static allocation order across boots · [H05]
- **STOR.N105** INVAR · `tests/test_fram_integration.py:333-334` — "a wedged chunk that never takes a
  write again would be a real defect even under the accepted-loss rule" — After both-BUSY loss the chunk
  must still accept writes · [H05]
- **STOR.N106** LIMIT · `tests/test_fram_integration.py:132-134` — "get_chunk() needs no successful
  setup(), so reader.pr.fram is a real but permanently unusable chunk, not None" — A chip dead at boot
  yields a non-None but unusable chunk; a None-chunk capacity check does not detect it · related:
  STOR.S08 · [H05]

## tests/test_print_log.py

- **STOR.N107** ASSUME · `tests/test_print_log.py:580-582, 590-592` — "AsyFramManager.get_chunk() never
  actually raises (confirmed by its own src/ promotion audit)" — Same past-audit claim as
  test_base_classes.py:682-696; the defensive paths are exercised only via a Protocol fake · [H05]

## digital_twin/README.md

- **STOR.N108** RISK · `digital_twin/README.md:72-75` — "dev's own `AsyFramManager.setup()` silently
  failed its device-ID check every twin run, caught and swallowed by its own broad `except Exception`" —
  A broad except in the FRAM manager hid a wrong-chip wiring bug in every twin run; the swallow pattern
  still exists · [H06]
- **STOR.N109** RISK · `digital_twin/README.md:474-482` — "Measured here at roughly **1 abrupt restart
  in 8**. That loss is **accepted behavior** (project owner's call, 2026-09-11" — Accepted loss of FRAM
  log history on abrupt restart; run asserts all-or-nothing only · [H06]
- **STOR.N110** ASSUME · `digital_twin/README.md:487-489` — "measured **20/20** against the ~1-in-8 loss
  of run 5b's unpaused shutdown" — Single dated measurement for the mempause guarantee · [H06]
- **STOR.N111** INVAR · `digital_twin/README.md:497-502` — "`FRAM` is the one exemption ...
  `tests/_sensortask_scenarios.py` pins it as the only one" — The FRAM-log-in-memory exemption is
  test-pinned · [H06]
- **STOR.N112** MIRROR · `digital_twin/README.md:507-509` — "mirrored at the mock tier
  (`tests/test_fram_integration.py`) and on real silicon (`tests_hardware/flash/test_fram_storage.py`'s
  reset-race test)" — All-or-nothing restore claim held at three tiers · [H06]

## digital_twin/machine.py

- **STOR.N113** MIRROR · `digital_twin/machine.py:317-318` — "`_DEV_FRAM_RDID = bytes([0x04, 0x7F, 0x48, 0x03])`
  ... `asy_fram_driver.py`'s own `_KNOWN_PRODUCT_IDS[0x40000]`,
  datasheets/fram/MB85RS2MTA-DS501-00032-3v0-E.pdf p.10" — RDID constant copied from the driver table
  and datasheet · [H06]

## digital_twin/_fram_chip.py

- **STOR.N114** MIRROR · `digital_twin/_fram_chip.py:22` — "`_DEFAULT_RDID = bytes([0x04, 0x7F, 0x03, 0x02]) # real MB85RS64V device ID (datasheets/fram/)`"
  — Datasheet constant copied · [H06]
- **STOR.N115** MIRROR · `digital_twin/_fram_chip.py:24-27` — "matches src/asy_fram_driver.py's own
  _ADDR_16BIT_MAX exactly" — Copied address-width threshold (2- vs 3-byte address) · [H06]
- **STOR.N116** PLATFORM · `digital_twin/_fram_chip.py:117, :129` — "WEL auto-clears at the CS rising
  edge after WRITE recognition" — Datasheet behaviour modelled per call pair, not per CS edge · related:
  TWIN.T04 · [H06]

## tests/test_digital_twin_bus_hazard_concurrency.py

- **STOR.N117** RISK · `tests/test_digital_twin_bus_hazard_concurrency.py:233-235` — "wozi is never
  physically flashed, so this twin run is FRAM's only fault-then-recovery verification for it" —
  Single-tier verification for wozi FRAM recovery · [H06]
- **STOR.N118** LIMIT · `tests/test_digital_twin_bus_hazard_concurrency.py:255-257, 276-277` —
  "FRAM_SPI._write() has no try/except of its own (unlike the I2C drivers); a SPI-level failure
  propagates raw" — Documents a src/ layering fact; protection lives in AsyFramManager · [H06]
- **STOR.N119** INVAR · `tests/test_digital_twin_bus_hazard_concurrency.py:260-262` — "verify_present()
  self-acquires that (non-reentrant) lock internally" — Caller must not hold the FRAM lock around
  `verify_present()` · [H06]
- **STOR.N120** SETTLED · `tests/test_digital_twin_bus_hazard_concurrency.py:322-323` — "A persistent
  one degrades to None instead of propagating, and leaves the chunk marked BUSY by design - destructive
  readout" — By-design behaviour of the FRAM manager · [H06]
- **STOR.N121** MIRROR · `tests/test_digital_twin_bus_hazard_concurrency.py:412-414, 442-447, 473-475` —
  "Twin-tier parity for the chunk-level gating the mock tier proves against a fake bus and the flash
  tier against the real chip" — Same FRAM gating claims held at mock, twin and flash tiers · [H06]
- **STOR.N122** SETTLED · `tests/test_digital_twin_bus_hazard_concurrency.py:442-444` — "the accepted,
  intended behavior ... _read_chunk() has to WRITE a transient busy marker before reading, so write
  protection gates read() as well as write()" — Accepted behaviour · [H06]
- **STOR.N123** SETTLED · `tests/test_digital_twin_bus_hazard_concurrency.py:502-507` —
  "AsyFramManager.__init__ sets _pause = False and nothing restores it from FRAM, so the pause is
  RAM-only." — Pause does not survive reboot (by design) · [H06]

## tests/test_digital_twin_uart_link.py

- **STOR.N124** INVAR · `tests/test_digital_twin_uart_link.py:173-175` — "AsyFramManager is a
  bump-pointer allocator, so instantiation order IS the on-chip layout and an inserted chunk would turn
  every persisted log into garbage" — Construction order is a persistence contract · [H06]

## tests_hardware/flash/test_fram_storage.py

- **STOR.N125** SETTLED · `tests_hardware/flash/test_fram_storage.py:57-59` — "Losing the whole history
  to a reset landing mid-write is accepted (owner, 2026-09-11; Part C.3.1); a PARTIAL restore never is"
  — Accepted all-or-nothing loss of error history. · related: STOR.T01 · [H07]

## tests_hardware/device_scripts/fram_error_log_reset_race_verify.py

- **STOR.N126** SETTLED · `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:17-20` —
  "Losing the whole history is accepted (owner, 2026-09-11) - SPECIFICATION.md Part C.3.1" — Accepted
  all-or-nothing loss; partial restore never. · related: STOR.T01 · [H07]

## tests_hardware/device_scripts/fram_pause_unpause_and_gating.py

- **STOR.N127** LIMIT · `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:64-65` —
  "override_pause ... (zero callers in src/, so this escape hatch has only ever been exercised against
  mocks)" — Unused src API exercised only here. (low) · related: STOR.T05 · [H07]

## tests_hardware/device_scripts/fram_same_device_rw_concurrency.py

- **STOR.N128** INVAR · `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:3` —
  "get_values()/set_values() require the caller to already hold the outer Lockable lock" — Driver caller
  contract, by convention. · related: STOR.T01 · [H07]

## tests_hardware/device_scripts/fram_write_protect_roundtrip.py

- **STOR.N129** SETTLED · `tests_hardware/device_scripts/fram_write_protect_roundtrip.py:2-3, 36-38` —
  "Reads being gated too is intended, accepted behavior - SPECIFICATION.md Part A.4's FRAM entry" —
  Accepted behaviour, asserted identically in mock and twin. · [H07]

## tests_hardware/README.md

- **STOR.N130** RISK · `tests_hardware/README.md:401-402` — "A FRAM pair E31 ... + W73 ... is what a
  block write cut off by a reset leaves" — Accepted: two-copy scheme recovers; the pair seeds the error
  log (see handover 5.4). · [H08]
- **STOR.N131** RISK · `tests_hardware/README.md:429-438` — "a script leaving a well-formed chunk behind
  fabricates a plausible one" — Hardware runs overwrite production FRAM chunks (deterministic bump
  allocator); `fram_error_log_reset_race_seed_and_race.py` seeds `errno=5` into SYSTEM's chunk. ·
  covered-by: HW.T17 · [H08]
- **STOR.N132** LIMIT · `tests_hardware/README.md:721-725` — "A \"fresh boot\" is simulated by
  constructing a brand-new `AsyFramManager`" — FRAM backup/restore "fresh boot" is object-level, not a
  real reboot. · - (low) · [H08]
- **STOR.N133** SETTLED · `tests_hardware/README.md:746-750` — "a *read* is rejected too, because
  `_read_chunk()` must write a transient busy marker first (intended behavior" — Write-protect test sets
  non-volatile WPEN\|BP0\|BP1 on the real chip. · related: HW.S07 · [H08]
- **STOR.N134** LIMIT · `tests_hardware/README.md:915-925` — "Read hijack: the buffer comes back all
  zero bytes ... never the real seeded pattern, never an exception" — CS-hijack (5/5, 2026-09-04): a
  hijacked read silently yields zeros. · [H08]
- **STOR.N135** LIMIT · `tests_hardware/README.md:931-938` — "this cannot prove a genuinely torn
  (partially-written) transfer" — True mid-byte power loss unreachable by any interpreter-level race. ·
  [H08]
- **STOR.N136** SETTLED · `tests_hardware/README.md:1214-1217` — "Confirmed structural (E.6.6 exception
  2: neither method has a REST route at all, by grep)" — FRAM write-protect gate is flash-tier only. ·
  related: HW.T09 · [H08]
- **STOR.N137** TODO · `tests_hardware/README.md:1287-1291` — "not confirmed to exist yet, so left named
  rather than guessed at" — NOTIFY FRAM chunk has no hard-reset-recovery test; needs a BackupTS-like
  signal (queue G4). · [H08]
  ⟨4dc80ef: G4 scratched by the owner 2026-09-25 (230a8df); tests_hardware/README.md:1287-1292 now says
  so⟩
- **STOR.N138** SETTLED · `tests_hardware/README.md:1402-1414` — "**Deliberately not
  `fram.allocated_size <= fram.size`** ... **mpremote-only by design (owner's own decision)**" — FRAM
  capacity check uses a `None` chunk as signal; no `/status` field by owner decision. · related:
  XCUT.S09 · [H08]

## REAL_HARDWARE_TEST_QUEUE.md (snapshot only; being updated by another session)

- **STOR.N139** ASSUME · `REAL_HARDWARE_TEST_QUEUE.md:154-156` — "it does not overwrite production's
  error logs" — A6 script writes at 0x3FF00 ("clear of every production chunk") — valid only for the 256
  KB `max_size=0x40000` chip; run under an 8 s WDT armed by a prior `exec`. · - (low) · [H08]
  ⟨4dc80ef: A6 script kept only in BACKLOG.md "Real-hardware work still owed" (T4)⟩
- **STOR.N140** ASSUME · `REAL_HARDWARE_TEST_QUEUE.md:248` — "`SPECIFICATION.md` Part A.7's FRAM
  setup-cost figures are twin-only." — R7 OPEN: twin FRAM has zero wire time; A6 showed ~90 % is
  interpreter/`machine.SPI` overhead. · related: PERF.T06 · [H08]
  ⟨4dc80ef: A6 script kept only in BACKLOG.md "Real-hardware work still owed" (T4); R7 measured
  2026-09-25 on silicon, retired into SPECIFICATION.md A.7 (38b270d)⟩
- **STOR.N141** TODO · `REAL_HARDWARE_TEST_QUEUE.md:274` — "Needs an observable-write signal analogous
  to SGP40's `BackupTS` first." — G4 OPEN: NOTIFY FRAM hard-reset recovery test. · [H08]
  ⟨4dc80ef: G4 scratched by the owner 2026-09-25: src/ is never changed only for a test (230a8df;
  BACKLOG.md:92-94)⟩
- **STOR.N142** RISK · `REAL_HARDWARE_TEST_QUEUE.md:330-332` — "Every sitting since 2026-09-22 ran
  isolated-driver device scripts, which overwrite production's first chunks." — The board's FRAM logs
  are not a clean production record. · covered-by: HW.T17 · [H08]
  ⟨4dc80ef: trap kept: CLAUDE.md FRAM-forensics caveat and tests_hardware/README.md:431⟩
- **STOR.N143** SETTLED · `REAL_HARDWARE_TEST_QUEUE.md:384-388` — "**Don't chase
  `asy_fram_manager.py`/`asy_fram_driver.py` internals** from anything found here" — Scoped-review rule
  (C.3.1); §1A failures belong to the PR #105 session. · [H08]
  ⟨4dc80ef: not migrated: the don't-chase note was tied to the closed PR #105 scoped exception; nothing
  to keep⟩

## HARDWARE_TEST_HANDOVER.md (snapshot only; sitting IN PROGRESS in another session)

- **STOR.N144** RISK · `HARDWARE_TEST_HANDOVER.md:172-175` — "entering BOOTSEL this way can cost one
  FRAM log entry; the harness's `enter_bootloader()` has the same property" — `machine.bootloader()`
  mid-write → E31+W73 at first boot. · related: HW.T17 · [H08]
  ⟨4dc80ef: F18 owner decision open: open in BACKLOG.md "Real-hardware work still owed" (F18)⟩

## dev_legacy/README.md

- **STOR.N145** PLATFORM · `dev_legacy/README.md:44` — "chip is a **MB85RS2MTA**, 256 KB
  (`max_size=0x40000`); deployed `wozi` uses CS=GPIO1, an **MB85RS64V**, 8 KB" — Dev vs field FRAM
  part/size/CS differ; which part dev physically carries is disputed across docs. · related: HW.T07,
  HW.S17 · [H08]
- **STOR.N146** DRIFT · `dev_legacy/README.md:642-648` — "**FRAM's first ~720 bytes hold real,
  structured data again** — 7 chunks" — Stale: ~21 chunks on dev now and device scripts overwrite
  production chunks. · related: HW.S20, XCUT.S09 · [H08]

## dev_legacy/*.py (reference-only 2026-08-27 on-device snapshot, MicroPython 1.24.1 — plan §2.2; field/bench behaviour only)

- **STOR.N147** PLATFORM · `dev_legacy/asy_fram_driver.py:127-129` — "block protection always protects
  the entire memory (BP0 and BP1)" — Legacy write-protect sets WPEN\|BP0\|BP1 (non-volatile status bits)
  for the whole array. · related: HW.S07 (low) · [H08]
- **STOR.N148** RISK · `dev_legacy/testprint.py:6-27` — "asyncio.run(foo.err_s(\"ErrTest\", errno=5))" —
  A snapshot script that seeds FRAM error-log entries (errno 5/6/7/127, wrnno likewise) at the first
  chunk of the 256 KB chip — historical fabricated-log source. · related: HW.T17 (low) · [H08]
- **STOR.N149** ASSUME · `dev_legacy/framtest.py:17-59` — "foo = fram.get_timestamped_chunk(400, tsfake,
  crc=CRC32(), verify=0)" — Writes 400-byte test patterns into low FRAM addresses — plausible origin of
  the "stale test-pattern garbage" dev_legacy/README.md:646-648 describes. · - (low) · [H08]

## scripts/_digital_twin_ci_suite.py

- **STOR.N150** SETTLED · `scripts/_digital_twin_ci_suite.py:68-71` — "The one registered error source
  deliberately not FRAM-backed: AsyFramManager builds a plain PrintLogHistory" — FRAM's own log is
  in-memory only by design; set pinned by `_sensortask_scenarios.py`. · related: XCUT.S08 · [H09]
- **STOR.N151** SETTLED · `scripts/_digital_twin_ci_suite.py:726-728` — "Losing history when the chip
  was unavailable is accepted (owner, 2026-09-11)" — Error-history loss while FRAM is faulted is
  accepted. · [H09]
- **STOR.N152** ASSUME · `scripts/_digital_twin_ci_suite.py:734-736` — "Run 3's fault can leave a chunk
  torn, and the self-healing read correctly logs that as a fresh FRAM entry" — FRAM's own log excluded
  from Run 4's reset-to-0 sweep. · [H09]
- **STOR.N153** RISK · `scripts/_digital_twin_ci_suite.py:798-804` — "the restore read fails and its
  fallback stores the empty ring. Roughly 1 restart in 8. That loss is accepted (owner, 2026-09-11)" —
  Abrupt shutdown loses the whole error ring ~1 in 8; only all-or-nothing is asserted. · [H09]
- **STOR.N154** ASSUME · `scripts/_digital_twin_ci_suite.py:830-832` — "so no status byte is left busy
  and the restore is deterministic, 20/20 measured" — Commanded-reboot no-loss claim rests on a 20-trial
  measurement. · [H09]

## devices/dev.toml

- **STOR.N155** INVAR · `devices/dev.toml:96-98` — "Last among the sensor drivers for FRAM chunk order
  (Part A.7); wozi has no such instance, so no byte-identity constraint applies." — TOML declaration
  order determines FRAM chunk layout; the "byte-identity constraint" referred to is not defined here. ·
  related: XCUT.T09 · [H09]
- **STOR.N156** PLATFORM · `devices/dev.toml:118-119` — "# MB85RS2MTA, 256KB." — dev FRAM part and size
  (`max_size = 0x40000`). · related: XCUT.T09 · [H09]

## devices/wozi.toml

- **STOR.N157** PLATFORM · `devices/wozi.toml:81-82` — "# MB85RS64V, 8KB." — wozi FRAM part/size. ·
  related: XCUT.T09 · [H09]

## devices/arzi.toml

- **STOR.N158** ASSUME · `devices/arzi.toml:70-72` — "max_size = 0x2000" — FRAM size stated without a
  part number (8 KB assumed). (low) · related: XCUT.T09 · [H09]

## devices/klkizi.toml

- **STOR.N159** ASSUME · `devices/klkizi.toml:70-73` — "max_size = 0x2000" — FRAM size without part
  number. (low) · related: XCUT.T09 · [H09]

## tests_scripts/test_digital_twin_ci_suite_errcount.py

- **STOR.N160** SETTLED · `tests_scripts/test_digital_twin_ci_suite_errcount.py:117-119` —
  "AsyFramManager cannot persist its own history through the store that failed, the one legitimate
  exemption" — FRAM is the only in-memory-only error source (also pinned in
  tests/_sensortask_scenarios.py) · related: STOR.S08 · [H10]

## SPECIFICATION.md Part A.2 (Architecture at a glance, 94-127)

- **STOR.N161** DRIFT · `SPECIFICATION.md:114-115` — "Used today for SGP40's VOC baseline backup." —
  Understates FRAM use: since WP1-WP3 every FRAM-wired logger/cfgmgr owns a chunk (A.7 lists 16-21). ·
  related: XCUT.S09 · [H12]

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)

- **STOR.N162** INVAR · `SPECIFICATION.md:170-178` — "The byte-level path is synchronous under a
  caller-held lock (2026-09-18 restructure, wire-identical)" — FRAM command bodies must never await
  while holding driver+bus lock; blocking 2 us CS settle; "wire-identical" is a claim. · related:
  STOR.T04 · [H12]
- **STOR.N163** ASSUME · `SPECIFICATION.md:174-175` — "Every `errno`/`wrnno` keeps its number and
  meaning; only the logging site moved up." — Claim after the sync restructure; C.7.1's FRAM row vs code
  already disputed. · related: STOR.S04 · [H12]
- **STOR.N164** PLATFORM · `SPECIFICATION.md:178-181` — "MB85RS64V reads are destructive internally ...
  \"as an FRAM memory operates with destructive readout mechanism\"" — Datasheet fact driving the
  busy/idle-on-read design; power loss mid-read is a real risk. · related: STOR.T10 · [H12]
- **STOR.N165** SETTLED · `SPECIFICATION.md:182-188` — "an interruption hitting *both* copies makes
  every later read fail the status check (errno 31) ... don't \"fix\" it" — Chunk stays unreadable until
  rewritten, by design; pinned by `tests/test_asy_fram_manager.py` test named at :187-188. · related:
  STOR.S01 · [H12]
- **STOR.N166** RISK · `SPECIFICATION.md:189-195` — "an abrupt reset mid-write loses that module's whole
  persisted error history ... That is accepted" — Owner decision 2026-09-11: evidence loss on abrupt
  reset accepted; twin-measured ~1 in 8. · related: CORE.T11 · [H12]
- **STOR.N167** ASSUME · `SPECIFICATION.md:192` — "Measured in the digital twin at roughly 1 abrupt
  restart in 8." — Single twin measurement, no silicon rate. · [H12]
- **STOR.N168** INVAR · `SPECIFICATION.md:193-195` — "the invariant that must hold instead is that the
  loss is *all-or-nothing*, never a partial or garbled restore" — Stated invariant; tested per :198-200
  (mock/twin/flash). · related: STOR.T12 · [H12]
- **STOR.N169** SETTLED · `SPECIFICATION.md:201-205` — "Write protection gates reads too, and that is
  intended (project owner, 2026-09-11)" — WP chip makes `chunk.read()` return None — an access gate, not
  data loss. · related: STOR.T03 · [H12]
- **STOR.N170** SETTLED · `SPECIFICATION.md:214` — "\"Both copies valid but different\" is a hard
  failure (no generation counter), never guessed." — Design decision: no generation counter. · related:
  STOR.T02 · [H12]
- **STOR.N171** INVAR · `SPECIFICATION.md:214-215` — "return `(ntp_synced, utc, success)` — `success` is
  third, not first; don't reorder." — Return-order contract upheld by caller discipline. · related:
  STOR.T06 · [H12]
- **STOR.N172** DRIFT · `SPECIFICATION.md:278-279` — "FRAM's 8KB has ample headroom over SGP40's
  ~250-byte usage" — Headroom claim predates the 16-21 logger/cfgmgr chunks now sharing the chip. ·
  covered-by: XCUT.S09 · [H12]

## SPECIFICATION.md Part C.3 (Layer 2 protocol class, 1537-1566)

- **STOR.N173** LIMIT · `SPECIFICATION.md:1548-1550` — "`FRAM_SPI`'s
  `_check_device_id()`/`_read_status()`/`_send_opcode()` do this (a real, low-severity D.4 violation
  left as-is" — Accepted per-call allocation; `_send_opcode()` doesn't exist. · covered-by: STOR.S04 ·
  [H12] ⟨quote not matched at the anchor⟩

## SPECIFICATION.md Part C.3.1 (SPI sensor variant, 1567-1596)

- **STOR.N174** PLATFORM · `SPECIFICATION.md:1596-1600` — "Two real chips: `MB85RS64V` (8KB, `0x2000`)
  and `MB85RS2MTA` (256KB, `0x40000`, ... p.10) ... A genuinely new size needs its own table entry." —
  Address-width table; which part dev carries is disputed. · related: HW.T07 · [H12]

## SPECIFICATION.md Part C.7 (Error handling & logging contract, 1807-1891)

- **STOR.N175** RISK · `SPECIFICATION.md:1835-1844` — "A `ResetErrors` answering `OK` on a write the
  chip acknowledged but did not physically store is accepted behaviour, not a defect (owner decision,
  2026-09-17" — Accepted: "if the bus transfer completed without error, the chip is trusted to have
  stored the value"; detected `_write()` False not reflected in the response. · related: REST.S04 ·
  [H12]

## SPECIFICATION.md Part C.7.1 (Running errno/wrnno table, 1893-1941)

- **STOR.N176** DRIFT · `SPECIFICATION.md:1930` — "`AsyFramManager` 10-88 ... (manager `errno` 17-88 +
  `wrnno` 80 ...)" — Row states the manager range two ways; code uses 10/11/19/20. · covered-by:
  STOR.S04 · [H12 (also H12)]
- **STOR.N177** INVAR · `SPECIFICATION.md:1930` — "because a synchronous body holding the bus lock must
  not await a persisted log entry" — Reporter split rule for FRAM. · related: STOR.S02 · [H12]

## SPECIFICATION.md Part C.8 (Concurrency & locking model, 2016-2188)

- **STOR.N178** SETTLED · `SPECIFICATION.md:2036-2047` — "the FRAM path's is a whole block operation,
  not a single transaction (owner's decision, 2026-09-18)" — ~25 CS cycles per hold; I2C keeps
  per-transaction scope (F.5.8). · related: PERF.T04 · [H12]

## SPECIFICATION.md Part F.5.2 — rp2 SPI RX-overrun EIO

- **STOR.N179** SETTLED · `SPECIFICATION.md:3750` — "So no retry is added (owner decision, 2026-09-24):
  the dual-copy layer already covers the read path." — Do-not-add-retry marker for SPI EIO on FRAM
  reads. · related: STOR.T10 · [H13]
- **STOR.N180** ASSUME · `SPECIFICATION.md:3746-3749` — "a single transient overrun costs nothing at all
  ... Only an overrun hitting both copies degrades the read to `None`" — Recovery claim shown by
  mock/twin live-path tests, not on silicon. · related: STOR.T01 · [H13]
- **STOR.N181** SETTLED · `SPECIFICATION.md:3752-3755` — "the chunk marked busy and unreadable until
  rewritten, which is **intended behavior, not a defect**" — A read-interrupted chunk is deliberately
  locked out (destructive-readout part). · related: STOR.T10 · [H13]

## SPECIFICATION.md Part F.5.8 — UART read() blocks the loop

- **STOR.N182** OPENQ · `SPECIFICATION.md:4010-4011` — "whether to yield between the envelopes of one
  write is open (`REAL_HARDWARE_TEST_QUEUE.md` T4)" — Open question pointing to a temporary queue row ID
  (spelled "T.4" two lines above). · related: PERF.T04, DOC.T03 · [H13]
  ⟨4dc80ef: T4 measured 2026-09-25, owner decisions open: open in BACKLOG.md "Real-hardware work still
  owed" (T4, holds A6's script)⟩

## SPECIFICATION.md Part K.7 — devices/*.toml

- **STOR.N183** RISK · `SPECIFICATION.md:5899-5901` — "Placement within the `[[instance]]` list has
  FRAM-chunk-order consequences (bump-pointer allocator, Part A.7) — no hard rule ... which usually just
  means \"last.\"" — Reordering instances silently remaps FRAM chunks. · covered-by: XCUT.T09 · [H13]

## DEVICE_REFERENCE.md

- **STOR.N184** ASSUME · `DEVICE_REFERENCE.md:33-35` — "**`0` disables this staleness check** — a
  restored backup is accepted no matter how old it is" — With a nonzero limit, negative ages (RTC set
  backwards, `NTP_Offset_S` shifts) are also accepted. · related: STOR.T09 · [H14]

## BACKLOG.md

- **STOR.N185** SETTLED · `BACKLOG.md:52-57` — "FRAM's verify_present()/set_write_protected() stay in
  src/ — SETTLED, do not re-raise." — Zero-caller FRAM APIs kept by repeated owner decision. ·
  covered-by: STOR.S05 · [H15]
- **STOR.N186** SETTLED · `BACKLOG.md:473-476` — "A transient SPI RX overrun is not retried - SETTLED,
  owner, 2026-09-24." — 1.29's `OSError(EIO)` on ≥32-byte rp2 SPI reads is absorbed by FRAM dual copy
  (errno 47, block-1 fallback). · related: PLAT.T03 · [H15]
- **STOR.N187** ASSUME · `BACKLOG.md:474-476` — "is absorbed by the FRAM layer's dual copy" — Premise of
  [052]; plan seeds say a transient read fault at logger `setup()` makes `_write()` overwrite the
  persisted ring. · related: CORE.S16, CORE.T11 · [H15]

## Archive `12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md` (5,553 lines) — only items still open/undecided/deferred/next-step there, with carry status in current docs

- **STOR.N188** OPENQ · `ARCH:2697-2705` — "Recommendation: do not take A.7." — Per-store
  `AsyFramChunkBuffer` measured as a ~1:1 churn-for-permanent-retention trade (288 B/op vs 299 B/store ×
  21); a recommendation with no recorded owner decision; not carried; plan CORE.S07 flags the per-entry
  fresh buffer + unused Lock without this evidence. · related: CORE.S07 · [H15]
- **STOR.N189** TODO · `ARCH:2491-2498` — "recorded as available, not taken" — Making
  `_set_check_sb()`/`_handle_status_bytes()` synchronous would recover ~1,700 B but moves log messages
  off their decision sites (C.7.1). Not carried. (low) · [H15]
- **STOR.N190** TODO · `ARCH:5504-5506` — "Lever 3 (per chunk operation) is not taken ... A.6 reopens it
  only if the combination with the boot collects falls short." — Conditional reopen of per-chunk FRAM
  lock scope; current SPEC states per-block-operation scope (SPECIFICATION.md:2036); the reopen
  condition is not carried. (low) · related: STOR.T04 · [H15]

## Commit messages (chronological)

- **STOR.N191** SETTLED · `commit 96031eb` — "get_size() also has zero callers today (kept as legitimate
  API surface ...); get_values()/set_values() don't reject a zero-length buffer" — Zero-caller FRAM API
  and zero-length buffer acceptance deliberately left. · status: not restated in BACKLOG (which only
  settles verify_present/set_write_protected) — UNTRACKED (low) | related: STOR.T* · [H17]
- **STOR.N192** INVAR · `commit dbdb6da` — "any future caller of
  get_write_protected()/set_write_protected()/verify_present() (currently zero callers) must apply the
  same discipline" — Future callers must wrap these in broad try/except (SPIDevice RuntimeError
  carve-out). · tracked: BACKLOG "FRAM's verify_present()/set_write_protected() stay in src/ — SETTLED"
  (partial; the caller-discipline half is not restated) | - · [H17]
- **STOR.N193** LIMIT · `commit 75778ab` — "max_size is trusted from the caller (not validated/clamped)
  since this driver's RDID check is hardwired to one real 8KB chip" — FRAM max_size unvalidated. ·
  status: code now keys `_KNOWN_PRODUCT_IDS` by max_size (src/asy_fram_driver.py:38,183) — partially
  superseded | - · [H17]
- **STOR.N194** SETTLED · `commit 892a591 / e128331` — "FRAM-out-of-memory not persisting to the error
  history (an architectural sync/async constraint ...), and the timestamped write's (ntp_synced, utc,
  success) tuple order" — get_chunk() out-of-FRAM logs console-only by owner decision; timestamped tuple
  order is inherited API. · status: tracked in code comments per commit (not re-verified) | related:
  STOR.T* · [H17]
- **STOR.N195** ASSUME · `commit c9dde56` — "board capacitance is sized against the datasheet's
  power-supply falling-time spec as the primary mitigation, with this software protocol as the second
  layer" — Destructive-read torn-read protection relies primarily on board hardware sizing (unverified
  in repo; no schematics exist per b64857d). · tracked: SPECIFICATION.md:178-180 | related: STOR.T* ·
  [H17]
- **STOR.N196** LIMIT · `commit 8eb1894 / 55e4453` — "epoch-0 timestamp sentinel collision) that lock
  down already-flagged, deliberately-unfixed quirks ... negative verify (a real, confirmed-not-a-bug
  \"verifies every write\" quirk)" — Deliberately unfixed FRAM-manager quirks pinned by tests. ·
  tracked: tests/test_asy_fram_manager.py:1465,1502 comments; epoch-0 collision not found by grep (low)
  | - · [H17]
- **STOR.N197** TODO · `commit 6d730f0` — "flagging what's still open (verifying the watchdog-starve
  path's implicit wait is enough margin, and preserving this invariant as more reset/reboot call sites
  potentially get added" — Reset-must-pause-FRAM invariant. · status: done (SPECIFICATION.md:226-232
  margin stated; tests/test_reset_call_site_invariant.py enforces reset sites) | - · [H17]
- **STOR.N198** SETTLED · `commit 5bdabf5` — "FRAM write-protection also blocks chunk reads (the
  busy-status protocol itself needs write access) - a project-owner call" — Owner later ruled it
  intended. · tracked: SPECIFICATION.md:201 ("Write protection gates reads too, and that is intended") |
  - · [H17]
- **STOR.N199** SETTLED · `commit 2e523d2` — "Correct: the busy-status lockout is intended, not a
  defect" — A chunk with both blocks left BUSY stays unreadable until rewritten (destructive-readout
  part). · tracked: SPECIFICATION Part A.4 / F.5.2 | related: STOR.T* · [H17]
- **STOR.N200** LIMIT · `commit 399c027` — about 1 abrupt restart in 8 loses the whole FRAM ring
  (all-or-nothing restore); owner "keep deferred" — Accepted data-loss window. · tracked:
  SPECIFICATION.md:194-198 | related: STOR.T* · [H17]
- **STOR.N201** NOTE(OWNER) · `commit 6cf82a1` — owner rulings: mem_backup is diagnostic only;
  clean-chroot recipe gains a trixie leg; legacy tree reference-only; FRAM-residue trap from isolated
  device scripts; heap figures 130,224 B / 115,536 B — Decisions later promoted to CLAUDE.md. · tracked:
  CLAUDE.md (Hard rules FRAM caveat; Build-environment trixie) | - · [H17]
- **STOR.N202** NOTE(CONSTRAINT) · `commit 9b83336 / 0b1e7622` — isl_reader "must therefore be
  constructed after notify_service and take chunk 8" (bump allocator = on-chip layout) — FRAM layout
  invariant. · tracked: SPEC Part A.7.1 | related: STOR.T* · [H17]
- **STOR.N203** NOTE(OWNER) · `commit 699836e` — "BACKLOG 27: the FRAM hard-reset test now expects
  E31/W71/W72 instead of requiring an empty log" — Contract decision: torn writes leave a trace. ·
  tracked: tests_hardware | - · [H17]
- **STOR.N204** NOTE(OWNER) · `commit d370413` — "Item 27 is settled with the owner's reasoning (a chip
  that ACKs a write it did not store would need deferred read-back; if the bus transfer was clean, the
  chip is trusted)" — PUT /status ResetErrors answers OK even when a FRAM write silently failed —
  accepted. · tracked: BACKLOG history only (item closed); not found in SPEC by this pass (low) |
  related: STOR.T* · [H17 (also H17)]
- **STOR.N205** NOTE(OWNER) · `commit 6811f03` — "The status-byte pair, the two copies, the CRC and
  every CS cycle are integrity features, not redundancy: recorded as the owner gave them" — FRAM
  protocol rationale. · tracked: HEAP_FRAGMENTATION_MEASUREMENTS archive §3B.1 / SPEC (not re-verified
  in SPEC) | - · [H17]
- **STOR.N206** NOTE(OPEN-DECISION) · `commit 9415902` — "the choice itself - per command, per block
  operation, or per chunk operation ... is put to the owner as open decision item 6 rather than taken
  unilaterally" — FRAM bus-lock scope. · status: to check in later chunks | - · [H17 (also H17)]
- **STOR.N207** NOTE(OWNER) · `commit 8951387` — "The owner's answer to open decision item 6": FRAM bus
  lock held per block operation; "Lever 3, one lock per chunk operation, stays untaken"; "A second SPI
  device now waits for a block operation (~25 CS, ~600 us)" — Bus-lock scope decision; latency trade for
  a hypothetical second SPI device. · tracked: SPEC C.8 | related: BUS.T* · [H17 (also H17)]
- **STOR.N208** NOTE(OWNER) · `commit 23e5443` — "A.7: ruled out ... A.8: closed - 'pure wall clock time
  is not such an issue, don't touch'. crc_checks.py is not to be modified" — Decisions on CRC yield and
  chunk buffers. · tracked: SPEC I.2 (moved in 17b4354) | - · [H17]
- **STOR.N209** NOTE(OWNER) · `commit 6acc9c0` — "§11 item 3 ... leave as is, do not defer the
  per-logger store setup"; "NTP_Host keeps its 1024-character bound"; "A.6's lever 3: closed" —
  Decisions. · tracked: SPEC I.2, BACKLOG.md:483 | - · [H17]
- **STOR.N210** NOTE(ONLY-IN-TEMP-DOC) · `commit 21560a4 / HARDWARE_TEST_HANDOVER.md:172` — "FRAM E31 +
  W73 at the first boot after flashing: mpremote exec machine.bootloader() most likely landed mid-write
  ... entering BOOTSEL this way can cost one FRAM log entry" — Bootloader entry can tear a FRAM write. ·
  UNTRACKED (low; temp doc only) | - · [H17]
  ⟨4dc80ef: F18 owner decision open: open in BACKLOG.md "Real-hardware work still owed" (F18)⟩
