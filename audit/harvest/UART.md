# Harvest — UART: UART protocol

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`, moved to `4dc80ef` by V11).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 72, INVAR 74, MIRROR 28, LIMIT 26, RISK 10, ASSUME 26, PLATFORM 8, WORKAROUND 1, SUPPRESS 9, TODO 13, OPENQ 1, DRIFT 4, NOTE 10 — 282 items.


## src/asy_uart_comm.py

- **UART.N001** INVAR · `src/asy_uart_comm.py:3` — "Every method returns a well-defined sentinel, never
  raises - a link fault is never an exception." — Module-wide never-raise contract upheld by per-method
  discipline; only `_listen_loop`'s catch-all (:1123) backs it at runtime · related: UART.T01 · [H02]
- **UART.N002** MIRROR · `src/asy_uart_comm.py:4-5` — "Wire constants and recovery timings are a
  two-implementation contract with the C peer: every change to one gets a UART_C_PORT_CHANGELOG.md
  entry." — Python↔C (`arduino/…Async_UART_Comm`, out of scope) and code↔`UART_C_PORT_CHANGELOG.md`; no
  mechanical check that a const change gets an entry · related: UART.T07 · [H02]
- **UART.N003** SETTLED · `src/asy_uart_comm.py:5-6` — "The write hold-off waits out its deadline rather
  than refusing, so no caller is told \"failed\" about a link that is merely quiescing (J.5)." —
  Deliberate design choice for the hold-off; ties to the stored-deadline ticks issue · related: UART.S07
  · [H02]
- **UART.N004** SUPPRESS · `src/asy_uart_comm.py:19` — "except ImportError: # typing has no runtime
  presence on MicroPython" — Swallowed ImportError for `typing`, standard pattern (same in most `src/`
  files, listed per file below) · [H02]
- **UART.N005** SETTLED · `src/asy_uart_comm.py:81` — "0xFF is never emitted - a deliberate off-by-one
  barrier, see J.3" — Wire invariant `_UID_MAX = 0xFE`; mirrored as changelog A8 ("That the C counter
  also stops at 0xFE" unverified) · related: UART.T01 · [H02]
- **UART.N006** MIRROR · `src/asy_uart_comm.py:86-89` — "Both are 1.5 x timeout and both are part of the
  wire contract (changelog A4)." — `_RESYNC_NUM/_DEN` are a Python↔C contract; C side's use of the same
  durations is unverified per changelog A4 · related: UART.T02 · [H02]
- **UART.N007** ASSUME · `src/asy_uart_comm.py:90-92` — "A multiple of the quiet window, so it can never
  be shorter than the peer's own drain" — `_DRAIN_BOUND_MULT = 4` assumes the peer drains with the same
  quiet window (changelog A5: "never shorter than the C side's own drain window" unverified) · related:
  UART.T02 · [H02]
- **UART.N008** ASSUME · `src/asy_uart_comm.py:93` — "_GATE_STEP_MS = const(20) # longest single sleep
  inside the write gate, so a cancel lands promptly" — Cancel latency of the write gate assumed bounded
  by 20 ms steps · related: UART.T09 · [H02]
- **UART.N009** ASSUME · `src/asy_uart_comm.py:94` — "_GC_PAUSE_WORST_MS = const(21) # measured
  worst-case collection pause, SPECIFICATION.md Part I" — Single measured number is a term of the
  `_min_timeout()` floor (:260); invalidated by heap/threshold/firmware changes · covered-by: UART.T10 ·
  [H02]
- **UART.N010** ASSUME · `src/asy_uart_comm.py:95` — "_POLL_JITTER_MS = const(5) # scheduling slack
  added to poll_wait_ms when sizing rxbuf" — Unmeasured scheduling-slack constant feeding the rxbuf
  floor and the boot-drain first probe (:1097) · related: UART.T10 · [H02]
- **UART.N011** MIRROR · `src/asy_uart_comm.py:97` — "cap = 5 x timeout, matching captive_dns.py's own
  0.5s -> 5s shape" — Backoff shape claimed to mirror `captive_dns.py`'s (check that side still has 0.5
  s → 5 s) · related: UART.S05 · [H02]
- **UART.N012** ASSUME · `src/asy_uart_comm.py:98` — "_DIAG_RESYNC_STREAK = const(2) # resyncs with
  bytes seen but no frame ever valid before the diagnostic fires" — Heuristic threshold for the "link
  unintelligible" errno 32 diagnostic · related: UART.T02 · [H02]
- **UART.N013** MIRROR · `src/asy_uart_comm.py:104-106` — "errno catalog - 10 upward, aligned to
  base_classes.py's SensorReader reservation even though this is not a subclass (owner direction)...
  Mirrored in SPECIFICATION.md Part C.7.1." — errno 10-34 / wrnno 10-14 catalogue mirrored in Part C.7.1
  and must stay disjoint from any reached-through owner's range (owner direction); no mechanical check ·
  related: XCUT.T07 · [H02]
- **UART.N014** INVAR · `src/asy_uart_comm.py:143-145` — "One allocation per logical message, never per
  frame (J.9)." — Allocation contract; per-transaction retained bytes pinned by
  `tests/test_uart_comm_hazard.py` (per :276) · related: UART.T03 · [H02]
- **UART.N015** INVAR · `src/asy_uart_comm.py:162-163` — "Anything predicting a *next* UID uses this,
  never a bare +1, which mispredicts precisely at the 0xFE -> 0 boundary." — Caller discipline for UID
  prediction (also changelog A8's C-side question) · [H02]
- **UART.N016** PLATFORM · `src/asy_uart_comm.py:200` — "asyncio.Lock is not reentrant, so re-entry is
  refused, not awaited" — Re-entrancy guarded by a plain `_busy` flag rather than the lock · related:
  XCUT.T06 · [H02]
- **UART.N017** LIMIT · `src/asy_uart_comm.py:212-214` — "_validate_config() stops at its first finding,
  so a non-integer can still be sitting here under a different errno." — Only the first construction
  finding is reported/persisted · related: UART.T05 · [H02]
- **UART.N018** LIMIT · `src/asy_uart_comm.py:224-226` — "__init__ is sync, so the persisted entry is
  written by setup(); this is the non-persisting counterpart" — A construction failure is print-only
  until `setup()` runs (log string "Construction failed, errno" :226; persisted at :1087) · related:
  UART.T05 · [H02]
- **UART.N019** SETTLED · `src/asy_uart_comm.py:231-232` — "Never clamps: a clamped payload_size turns a
  loud configuration error into a link that desyncs intermittently" — Deliberate no-clamp policy
  (changelog A6) · related: UART.T05 · [H02]
- **UART.N020** INVAR · `src/asy_uart_comm.py:245-246, 254-260` — "J.6: a GC pause or the peer's idle
  poll would read as a fault" — Timeout floor = 2·poll_wait_ms + poll_idle_ms + 21 ms; assumes the
  peer's idle poll equals this side's `poll_idle_ms` · covered-by: UART.T05 · [H02]
- **UART.N021** ASSUME · `src/asy_uart_comm.py:262-270` — "per_poll = ((bus.baudrate // 10) *
  (bus.poll_wait_ms + _POLL_JITTER_MS)) // 1000" — rxbuf floor assumes 10 bits per byte on the wire
  (8N1) and the 5 ms jitter slack · related: UART.T05 · [H02]
- **UART.N022** DRIFT · `src/asy_uart_comm.py:327-318 vs :328-329 (agent cited src/asy_uart_comm.py:316-318 vs :328-329)`
  — "Exactly two entries per fault episode" vs "a single transient leaves one entry rather than a
  matched pair" — The two comments give different per-episode entry counts (low) · related: UART.T04 ·
  [H02] ⟨re-anchored: quote found at line 327⟩
- **UART.N023** LIMIT · `src/asy_uart_comm.py:321` — "self.pr.err(\"Repeated errno\", errno, *args) #
  visible, not persisted, not counted" — Repeats are neither persisted nor counted, vs C.7.1's "still
  counts it" · covered-by: UART.S01 · [H02]
- **UART.N024** INVAR · `src/asy_uart_comm.py:335-337` — "One persisted warning per episode, the rest
  visible only." — Per-episode warning dedupe (C.7.1 repeat rule) · related: UART.T04 · [H02]
- **UART.N025** RISK · `src/asy_uart_comm.py:351-355` — "await self.pr.err_s(\"Not initialized\",
  errno=self._init_errno or _ERR_NOT_READY)" — Every call on an uninitialised instance persists an
  entry, no dedupe · covered-by: UART.S03 · [H02]
- **UART.N026** MIRROR · `src/asy_uart_comm.py:435-436` — "ceil(total / payload_size) + 1, floored at 2:
  even a payload-less command has one data chunk to acknowledge." — CHUNKS formula is wire behaviour the
  C sender must reproduce (Part J) · related: UART.T01 · [H02]
- **UART.N027** MIRROR · `src/asy_uart_comm.py:451, 455` — "exact match, never a bitmask" / "a
  conforming peer never emits 0xFF" — Receiver rules mirrored as changelog A1/A8; C-side behaviour
  unverified · related: UART.T01 · [H02]
- **UART.N028** MIRROR · `src/asy_uart_comm.py:482-493` — "The sender's SIZE pattern is fully determined
  by construction... (changelog A12)." — Per-position SIZE rules are a Class A receiver tightening; C
  sender conformance unverified; GET's CHUNKS=1 not enforced here · covered-by: UART.S02 · [H02]
- **UART.N029** SETTLED · `src/asy_uart_comm.py:508-510` — "never gated by the write hold-off: the
  hold-off covers *initiating* only... Both sides gating ACKs would stall a healthy link" — Deliberate
  ACK exemption from the hold-off (wire-level behaviour) · related: UART.T02 · [H02]
- **UART.N030** WORKAROUND · `src/asy_uart_comm.py:517-519` — "A deadline, never a one-shot Timer:
  MicroPython's scheduler queue can silently drop a soft callback... the legacy module's permanent
  hang." — Replaces a Timer against the soft-callback-drop platform defect (changelog B2); removal
  trigger: none stated · related: XCUT.T04 · [H02]
- **UART.N031** RISK · `src/asy_uart_comm.py:203, 520-529` — "self._holdoff_deadline = time.ticks_ms() #
  only meaningful while _holdoff_active is set" — Stored ticks deadline compared with `ticks_diff` after
  arbitrary time · covered-by: XCUT.T25 · [H02]
- **UART.N032** LIMIT · `src/asy_uart_comm.py:551-555` — "Visible only, and flagged rather than
  persisted here... setup()'s boot drain owns no episode at all" — Drain-bound hit during the boot drain
  is never persisted (log "Drain bound reached, resyncing anyway") · related: UART.T02 · [H02]
- **UART.N033** LIMIT · `src/asy_uart_comm.py:578` — "self.uart.resync_framing() # inert unless a
  delimited codec is selected (Part G.2)" — Framing resync is a no-op on the production `Framing_Pass`
  path · related: ALGO.T04 · [H02]
- **UART.N034** SETTLED · `src/asy_uart_comm.py:580-588` — "bytes arriving but no frame ever valid -
  check CRC algorithm, baud rate and payload_size" — Parameter mismatch is diagnosed, never negotiated
  (CLAUDE.md owner decision 2026-09-11); diagnostic persisted as errno 32 · related: UART.T02 · [H02]
- **UART.N035** DRIFT · `src/asy_uart_comm.py:593-594` — "rather than a convention repeated at
  twenty-eight call sites" — Snapshot has 32 `await self._fault(` call sites (low) · [H02]
- **UART.N036** INVAR · `src/asy_uart_comm.py:599-601` — "One bit per id, not just the last, so an
  alternation cannot refill it." — Rejection dedupe bitmap; `ResetErrors` clears it (:1147) · related:
  UART.T04 · [H02]
- **UART.N037** INVAR · `src/asy_uart_comm.py:613-615` — "Cancel FIRST, outside the lock: a listening
  responder holds it indefinitely, so locking first would deadlock" — Lock-ordering rule for `clear()` ·
  related: UART.T09 · [H02]
- **UART.N038** MIRROR · `src/asy_uart_comm.py:622-625` — "The driver's counter is cumulative, so
  reading it as a flag reported every later cancel" — Relies on
  `asy_uart_driver.UART.cancel_unacknowledged` staying a cumulative counter · [H02]
- **UART.N039** SETTLED · `src/asy_uart_comm.py:649-651` — "Out of contract - there is no arbitration -
  so it is logged as the peer's violation" — Simultaneous initiation out of contract (CLAUDE.md strict
  initiator/responder) · related: UART.T01 · [H02]
- **UART.N040** SUPPRESS · `src/asy_uart_comm.py:675` — "result = await result # type: ignore[misc]" —
  mypy suppression in shipped code · [H02]
- **UART.N041** SUPPRESS · `src/asy_uart_comm.py:676` — "except Exception as e: # caller-supplied code;
  its runtime behaviour is not statically known" — Broad catch around callbacks, logged as errno 26 ·
  related: MEM.T09 · [H02]
- **UART.N042** SUPPRESS · `src/asy_uart_comm.py:687` — "if len(result) != _CALLBACK_PAIR_LEN: # type:
  ignore[arg-type]" — mypy suppression in shipped code · [H02]
- **UART.N043** SUPPRESS · `src/asy_uart_comm.py:689` — "valid = result[0] # type: ignore[index]" — mypy
  suppression in shipped code · [H02]
- **UART.N044** SUPPRESS · `src/asy_uart_comm.py:690` — "payload = result[1] # type: ignore[index]" —
  mypy suppression in shipped code · [H02]
- **UART.N045** INVAR · `src/asy_uart_comm.py:729-731` — "Every abort here is mid-train though, so it
  quiesces - else this side transmits into the peer's own drain." — Mid-train abort must always resync ·
  related: UART.T02 · [H02]
- **UART.N046** INVAR · `src/asy_uart_comm.py:765, 784` — "Checked before the copy, so a desynced or
  hostile peer cannot overrun." / "the final ACK is deferred until after the total-size check below" —
  Receiver overrun guard and final-ACK withholding (wire behaviour) · related: UART.T08 · [H02]
- **UART.N047** INVAR · `src/asy_uart_comm.py:815-816` — "buf is borrowed for the call's duration and
  never retained past it; this instance's own uses are serialized by the session lock." — Caller must
  not mutate the buffer during the call (convention) · [H02]
- **UART.N048** SETTLED · `src/asy_uart_comm.py:836-837` — "A genuinely unknown length is out of scope
  for this protocol, by design." — Streaming SET needs a declared total · [H02]
- **UART.N049** INVAR · `src/asy_uart_comm.py:859-860, 1071-1073` — "None means failure; a zero-length
  result means a genuinely empty payload. The two must never collapse into one value (J.9)." —
  Return-value contract for GET and listen · related: UART.T01 · [H02]
- **UART.N050** RISK · `src/asy_uart_comm.py:988-990` — "the hold-off is dropped here - the one
  documented reset besides the deadline itself" — Hold-off otherwise persists until next write ·
  covered-by: UART.S07 · [H02]
- **UART.N051** INVAR · `src/asy_uart_comm.py:996` — "if not await self._read_frame(device, -1): # the
  one legitimate unbounded wait" — Only unbounded read in the module; relies on driver `poll_idle_ms`
  for idle cost (F.5.9) · related: BUS.T05 · [H02]
- **UART.N052** LIMIT · `src/asy_uart_comm.py:1026-1027` — "the caller is told which command was asked
  for and that the answer was withheld, while the peer learns it by timing out" — No NACK: a declined
  command costs the peer a full timeout + resync (changelog A9 proposed) · related: UART.S05 · [H02]
- **UART.N053** SUPPRESS · `src/asy_uart_comm.py:1078-1080` — "except (MemoryError, OverflowError):
  await self._err(_ERR_DEST_ALLOC, \"could not right-size the received train\")" — Caught MemoryError
  after a fully received and ACKed SET: the peer was told success, the local result is dropped ·
  related: UART.T08 · [H02]
- **UART.N054** INVAR · `src/asy_uart_comm.py:1085` — "await self.pr.setup() # without this the FRAM
  history silently never persists" — Logger `setup()` must be called by the owner's `setup()` · related:
  XCUT.T08 · [H02]
- **UART.N055** SETTLED · `src/asy_uart_comm.py:1094-1102` — "A boot-time drain is expected on a live
  link and is deliberately not counted" — Boot drain deliberately not persisted (changelog B16) · [H02]
- **UART.N056** INVAR · `src/asy_uart_comm.py:1109-1111` — "A link fault is handled by the resync and
  the backoff below, never by letting the task die" — Listen task must not end on link faults
  (supervisor budget); returns only on readiness failure · related: XCUT.T02 · [H02]
- **UART.N057** SUPPRESS · `src/asy_uart_comm.py:1123` — "except Exception as e: # uart_listen() is
  contracted never to raise; a contract is not an enforcement" — Broad catch in the listen loop, logged
  as errno 30 · related: UART.S05 · [H02]
- **UART.N058** SETTLED · `src/asy_uart_comm.py:1129-1130` — "an initiator exposing a listen task would
  mean both ends initiate, and the protocol has no arbitration for that" — Role decides task set · [H02]
- **UART.N059** SETTLED · `src/asy_uart_comm.py:1136` — "return [] # no machine.Timer anywhere in this
  module, deliberately" — Deliberate Timer-free module · [H02]
- **UART.N060** INVAR · `src/asy_uart_comm.py:1142-1143, 1148` — "the streak state behind C.7.1's
  escalate-once rule must not survive a reset" / "in place: a reset must not depend on the heap having
  room" — Reset is total and allocation-free · related: UART.S06 · [H02]

## src/asy_uart_driver.py

- **UART.N061** MIRROR · `src/asy_uart_driver.py:77-79` — "Write order is build -> CRC -> encode ->
  delimiter, read the exact reverse... selecting a delimited one is a wire change (changelog A11)." —
  Layer order is part of the Python↔C wire contract · related: UART.T01 · [H02]

## src/asy_uart_link_driver.py

- **UART.N062** SETTLED · `src/asy_uart_link_driver.py:4-5` — "Never a SensorReader/SensorReaderConfig
  subclass (mirrors UART_Comm's own owner-confirmed standalone status, SPECIFICATION.md Part J.1)" —
  Owner-confirmed standalone status; construction depends on `buildgen/driver_registry.py:20`
  `_OVERRIDES` entry (MIRROR) · related: UART.T06 · [H02]
- **UART.N063** SUPPRESS · `src/asy_uart_link_driver.py:16` — "except ImportError: # typing has no
  runtime presence on MicroPython" — Swallowed ImportError for `typing` · [H02]
- **UART.N064** SETTLED · `src/asy_uart_link_driver.py:31-33` — "Bench-only: nothing about a deployed
  unit's real behavior depends on either." — Command ids 0x01/0x02 are bench application semantics, not
  protocol · [H02]
- **UART.N065** ASSUME · `src/asy_uart_link_driver.py:37-40` — "_EXERCISE_PERIOD_MS = const(1000)" — 1
  Hz exercise rate chosen so coexistence claims are about a live link; combined with non-deduped
  `_ready()` errors it can persist one entry per second · covered-by: UART.S03 · [H02]
- **UART.N066** LIMIT · `src/asy_uart_link_driver.py:88-89` — "withholding validity is how the responder
  signals \"no such command\", which the peer sees as a withheld answer" — No negative reply; peer pays
  a timeout · related: UART.S05 · [H02]
- **UART.N067** ASSUME · `src/asy_uart_link_driver.py:111-113` — "Never raises out: uart_get() is
  contracted to return None rather than raise" — Exercise loop has no try; relies on UART_Comm's
  never-raise contract, else supervisor restart · related: UART.T06 · [H02]
- **UART.N068** MIRROR · `src/asy_uart_link_driver.py:123-125` — "Registered as a maintenance sensor,
  not a new /status key... (matches asy_sgp40_driver.py's own maintenance-status precedent)" — Reporting
  path mirrors SGP40's maintenance-status precedent · related: UART.T06 · [H02]
- **UART.N069** SETTLED · `src/asy_uart_link_driver.py:143` — "empty - no machine.Timer anywhere in this
  file either" — Deliberately Timer-free · [H02]
- **UART.N070** RISK · `src/asy_uart_link_driver.py:157-160` — "self.transfers = 0 / self.failures = 0"
  — `ResetErrors` also wipes measurement counters · covered-by: UART.S06 · [H02] ⟨quote not matched at
  the anchor⟩

## src/framing_codecs.py

- **UART.N071** MIRROR · `src/framing_codecs.py:4-6` — "Selecting a delimited codec changes the bytes on
  the wire and is a coordinated flag day - UART_C_PORT_CHANGELOG.md A11." — Codec choice is a Python↔C
  wire contract (owner-resolved design, proposed Class A) · related: UART.T07 · [H02]

## tests/_uart_comm_harness.py

- **UART.N072** LIMIT · `tests/_uart_comm_harness.py:59-61` — "a test that passes only one models a
  mismatched pair rather than a protected link" — CRC is per bus below the protocol; the harness does
  not reject a one-sided CRC · [H03]

## tests/test_asy_uart_comm.py

- **UART.N073** SETTLED · `tests/test_asy_uart_comm.py:93-96` — "A clamp turns a loud configuration
  error into a link that desyncs intermittently in the field" — out-of-range construction parameters are
  refused, never clamped (J.6) · related: UART.T05 · [H04]
- **UART.N074** ASSUME · `tests/test_asy_uart_comm.py:106-107` — "Below this a routine collection pause
  reads as a link fault" — the timeout floor rests on a measured GC-pause bound (`_GC_PAUSE_WORST_MS`) ·
  covered-by: UART.T10 · [H04]
- **UART.N075** ASSUME · `tests/test_asy_uart_comm.py:166-167` — "At 115200 baud a 20ms poll interval
  plus the module's 5ms of scheduling slack admits ~288 bytes" — rxbuf per-poll floor derived from baud
  × (poll_wait + 5 ms slack); the 5 ms slack is a module assumption · related: UART.T10 · [H04]
- **UART.N076** INVAR · `tests/test_asy_uart_comm.py:153-155` — "5 + 255 = 260 bytes against the
  driver's own 256-byte default rxbuf" — construction must refuse payload_size whose frame exceeds
  rxbuf, else frames never complete and look like link faults · related: UART.T05 · [H04]
- **UART.N077** SETTLED · `tests/test_asy_uart_comm.py:235-237,252-253` — "Exactly two entries per fault
  episode - the transition in and the transition back out - never one per occurrence" — UART
  persisted-log volume discipline (C.7.1); closing entry only if the fault repeated · related: UART.T04
  · [H04]
- **UART.N078** INVAR · `tests/test_asy_uart_comm.py:277-283,302,308-316` — "/status must never show a
  number the catalog cannot explain, so the ranges are checked mechanically against the source" —
  errno/wrnno ranges and no-bare-number rule enforced by a source-scanning test against _ERRNO_MIN/_MAX,
  _WRNNO_MIN/_MAX · related: XCUT.T07 · [H04]
- **UART.N079** INVAR · `tests/test_asy_uart_comm.py:368-369` — "Leaving the remainder unwritten
  transmits the previous frame's payload remnants - a real data leak between unrelated messages." — TX
  padding must be cleared on every frame · related: SEC.T01 (low) · [H04]
- **UART.N080** SETTLED · `tests/test_asy_uart_comm.py:388-389,1204-1206` — "An initiator exposing a
  listen task would mean both ends initiate, and the protocol has no arbitration for that." — strict
  initiator/responder roles; simultaneous initiation out of contract (CLAUDE.md) · [H04]
- **UART.N081** INVAR · `tests/test_asy_uart_comm.py:399-401` — "\"there is no Timer\" is a structural
  property, not an observable behaviour" — no machine.Timer in asy_uart_comm.py, enforced by a
  source-scan test (E3, changelog B2) · [H04]
- **UART.N082** SETTLED · `tests/test_asy_uart_comm.py:408-415,838-839` — "A boot-time drain is not a
  fault and must not be counted." — setup() drain deliberately uncounted (changelog B16) so FRAM history
  is not polluted on every boot · [H04]
- **UART.N083** ASSUME · `tests/test_asy_uart_comm.py:426-427` — "A zero-delay retry is captive_dns.py's
  measured recovery storm" — listen backoff justified by a measurement in another module; must reset on
  recovery · related: UART.S05 (low) · [H04]
- **UART.N084** SETTLED · `tests/test_asy_uart_comm.py:493-494` — "The 0xFE -> 0 wrap is a deliberate
  off-by-one barrier" — UID 0xFF is never emitted; UID space equals the longest train (Class A wire
  rule) · related: UART.T01 · [H04]
- **UART.N085** INVAR · `tests/test_asy_uart_comm.py:653-654` — "If the hold-off gated ACKs too, both
  sides would back off simultaneously and the link would stall" — write hold-off must never gate ACK
  writes · related: UART.T02 · [H04]
- **UART.N086** LIMIT · `tests/test_asy_uart_comm.py:688` — "Indistinguishable from a lost ACK at this
  layer, and the distinction is not invented." — a mid-train response loss and a lost ACK produce the
  same failure report · - (low) · [H04]
- **UART.N087** SETTLED · `tests/test_asy_uart_comm.py:704-705,722-723` — "J.9: the two-generals case,
  folded into failure by decision" — a lost final ACK makes the initiator report failure while the
  responder has delivered the data · covered-by: UART.T08 · [H04]
- **UART.N088** SETTLED · `tests/test_asy_uart_comm.py:1009` — "Nothing is re-sent - that is the design,
  not a gap." — no retransmission in the protocol · related: UART.T08 · [H04]
- **UART.N089** MIRROR · `tests/test_asy_uart_comm.py:742-743` — "Changelog A4: both constants are 1.5 x
  timeout and neither is hardcoded" — drain window and hold-off = 1.5 × timeout must match the C side
  (Class A, UART_C_PORT_CHANGELOG.md A4) · related: UART.T02 · [H04]
- **UART.N090** SETTLED · `tests/test_asy_uart_comm.py:802-803,821` — "Exactly one, not both: the budget
  the whole episode gets is still a single persisted warning." — W11 (babbling peer) replaces W10 within
  an episode; one persisted warning per resync episode · related: UART.T04 · [H04]
- **UART.N091** INVAR · `tests/test_asy_uart_comm.py:861-862` — "read() would allocate per round, on
  exactly the degraded link where the heap is most fragmented" — drain must use a preallocated readinto,
  asserted via the fake's call log · related: UART.T03 · [H04]
- **UART.N092** INVAR · `tests/test_asy_uart_comm.py:901-902` — "Taking the lock before attempting the
  cancel deadlocks against the very listener this exists to free" — clear() must cancel before acquiring
  the lock · related: UART.T09 · [H04]
- **UART.N093** SETTLED · `tests/test_asy_uart_comm.py:931-933` — "cancel_unacknowledged is cumulative,
  and clear() read it as a flag" — wrnno 13 fires on a rise of the cumulative counter only (changelog
  B28) · [H04]
- **UART.N094** INVAR · `tests/test_asy_uart_comm.py:1059-1060` — "None means failure and a zero-length
  result means genuinely empty" — J.9 return-shape contract callers depend on · [H04]
- **UART.N095** PLATFORM · `tests/test_asy_uart_comm.py:1180-1182` — "asyncio.Lock is not reentrant, so
  a callback that calls back in would await a lock its own caller holds" — re-entrant calls from
  callbacks are refused with a sentinel instead of deadlocking · related: PLAT.T01 · [H04]
- **UART.N096** SETTLED · `tests/test_asy_uart_comm.py:1334` — "CHUNKS has to be in chunk 1, so an
  unknown length is out of scope by design." — streaming requires the total length up front · - (low) ·
  [H04]
- **UART.N097** ASSUME · `tests/test_asy_uart_comm.py:1340-1341` — "Each case was confirmed against the
  real interpreter before its guard existed" — the audit-pass argument guards were validated on the Unix
  port, not rp2 · - (low) · [H04]
- **UART.N098** SETTLED · `tests/test_asy_uart_comm.py:1566-1567` — "Optional by design: a GET-only
  responder has nothing to deliver" — `deliver` callback optional for responders · - (low) · [H04]
- **UART.N099** LIMIT · `tests/test_asy_uart_comm.py:1888-1890` — "the one place the two ends
  legitimately disagree: the final ACK is already out" — responder right-sizing MemoryError after the
  final ACK loses data while the sender believes it delivered · related: UART.T08 · [H04]
- **UART.N100** INVAR · `tests/test_asy_uart_comm.py:1947-1949` — "_busy is cleared in a finally rather
  than on the return path" — a cancelled task must not leave the instance refusing calls as re-entrant ·
  related: UART.T09 · [H04]
- **UART.N101** LIMIT · `tests/test_asy_uart_comm.py:1984-1986` — "The half J4's own fix still left
  open. Remembering only the last declined id suppresses a repeat but not an alternation" — declined-id
  dedupe now covers alternation; the separate last-errno dedupe (UART.S03) is not addressed here ·
  related: UART.S03 · [H04]
- **UART.N102** RISK · `tests/test_asy_uart_comm.py:2002-2004` — "every abort here leaves the peer
  mid-train: it drains for 1.5 x timeout" — a pull-callback abort mid-train forces the peer into a
  drain; hold-off must protect it · related: UART.T09 · [H04]
- **UART.N103** SETTLED · `tests/test_asy_uart_comm.py:2039-2041` — "A demonstration, deliberately not a
  constraint - the module is standalone" — the legacy BSEC use case (dev_legacy/) constrains nothing
  (Part J.1) · [H04]

## tests/test_asy_uart_link_driver.py

- **UART.N104** INVAR · `tests/test_asy_uart_link_driver.py:248-249` — "this wrapper holds no error
  state of its own, so its counter has to be the inner UART_Comm's or a /status read reports zero" —
  UartLinkExerciser must forward get_error_counter/reset to the inner UART_Comm · related: UART.S06 ·
  [H04]

## tests/test_framing_codecs.py

- **UART.N105** INVAR · `tests/test_framing_codecs.py:157-158` — "skipping *empty frames on the wire* is
  the read loop's job, not this layer's" — Division of responsibility between the COBS codec and
  asy_uart_driver's read loop · [H05]

## tests/test_uart_comm_hazard.py

- **UART.N106** SETTLED · `tests/test_uart_comm_hazard.py:48-50` — "Standing rule (project owner,
  2026-09-12): every check runs both with and without a CRC - the deployed link is CRC_Pass" — Every
  check is registered in both CRC modes except the two mode-specific payload-corruption checks
  (:1271-1277) · [H05]
- **UART.N107** MIRROR · `tests/test_uart_comm_hazard.py:33-45` — "_CMD_ACK = 0x01 / _CMD_GET = 0x02 /
  _CMD_SET = 0x04 ... _FRAME = 5 + _PAYLOAD" — Wire constants and field offsets hand-copied from
  src/asy_uart_comm.py's `const()`s (Class A contract values); drift is not detected · related: UART.T01
  · [H05] ⟨quote not matched at the anchor⟩
- **UART.N108** ASSUME · `tests/test_uart_comm_hazard.py:30-32` — "every value still clears the module's
  own floor of 2 x poll_wait_ms + poll_idle_ms plus the worst-case GC pause - 24ms here" — The 30 ms
  tier timeout rests on the measured worst-case GC pause · related: UART.T10 · [H05]
- **UART.N109** SETTLED · `tests/test_uart_comm_hazard.py:207-208, 625-626` — "Simultaneous initiation
  is out of contract - there is no arbitration anywhere in the design" — Tests prove detection and
  recovery, never that it works · [H05]
- **UART.N110** INVAR · `tests/test_uart_comm_hazard.py:187-188` — "The unbounded listen wait holds the
  bus lock, so this is the only safe interruption" — clear() is the only safe way to unstick a parked
  listener · related: UART.T09 · [H05]
- **UART.N111** RISK · `tests/test_uart_comm_hazard.py:705-707, 741-743` — "with no CRC configured, a
  bit flip in the payload passes every structural check and reaches the caller as good data" —
  Documented property of the deployed CRC_Pass configuration: payload corruption is undetected ·
  covered-by: UART.S04 · [H05]
- **UART.N112** SETTLED · `tests/test_uart_comm_hazard.py:796-798` — "parameters are agreed out of band
  and never negotiated, so a pair configured differently is diagnosed (errno 32), never recovered" —
  Owner decision (J.6) · [H05]
- **UART.N113** SETTLED · `tests/test_uart_comm_hazard.py:854-856` — "Pins the known blind spot, not the
  desired behaviour: errno 32 never fires here ... Accepted rather than fixed (SPECIFICATION.md Part
  J.6); this inverts if it is" — Test pins a known limitation: mismatch on this path reports as generic
  errno 22 · [H05]
- **UART.N114** RISK · `tests/test_uart_comm_hazard.py:1108-1110` — "a lost one leaves the peer having
  accepted the whole train while this side reports failure. A caller that retries on False must tolerate
  that" — At-least-once delivery seam · covered-by: UART.T08 · [H05]
- **UART.N115** MIRROR · `tests/test_uart_comm_hazard.py:1223-1225` — "the C peer appends its own CRC in
  the platform's NATIVE order and is deliberately not wire-compatible with this one (SPECIFICATION.md
  Part J, UART_C_PORT_CHANGELOG.md A7)" — Python↔C byte-order divergence pinned big-endian here ·
  related: UART.S04 · [H05]
- **UART.N116** INVAR · `tests/test_uart_comm_hazard.py:23-24, 50` — "CRC_Base carrying state the two
  ends must not share" — A CRC instance must never be shared between link ends · [H05]

## digital_twin/machine.py

- **UART.N117** INVAR · `digital_twin/machine.py:436-439` — "Must comfortably exceed a whole
  stop-and-wait exchange's worth of frames" — `_UART_INFLIGHT_MAX = 4096` sized by convention to
  protocol frame sizes · [H06]
- **UART.N118** MIRROR · `digital_twin/machine.py:482-484` — "Models the dev bench's permanent GP0<->GP9
  / GP1<->GP8 jumper (dev_legacy/README.md)" — Twin topology mirrors a physical bench jumper
  (dev_legacy/README.md:54-60) · [H06]
- **UART.N119** LIMIT · `digital_twin/machine.py:497-499` — "`_LinkDirection(..., uart_a.baudrate)`" —
  Each direction is timed at the sender's baud; a baud mismatch between the ends (CLAUDE.md's "dead link
  that carries bytes") is unmodelled (low) · [H06]
- **UART.N120** ASSUME · `digital_twin/machine.py:533-534` — "counted and dropped, never raised into the
  driver, which real hardware never does either" — Claim about rp2 UART overrun behaviour · [H06]
- **UART.N121** ASSUME · `digital_twin/machine.py:608-610` — "Real machine.UART() re-inits the
  peripheral rather than refusing, so a second instance on one id supersedes the first" — Port behaviour
  claim behind the supersede model; class-level `_live`/`superseded` shared across tests · related:
  TEST.T07 · [H06]
- **UART.N122** PLATFORM · `digital_twin/machine.py:695-697` — "Real machine.UART.any() drains the RX
  FIFO before counting, so it never under-reports what a preceding POLLIN saw" — Port behaviour the
  driver's read clamp depends on · [H06]
- **UART.N123** LIMIT · `digital_twin/machine.py:701-703` — "these fakes serve what they hold and
  return, so the stall is counted here instead of taken" — Twin UART reads never block on `timeout_char`
  (F.5.8); a loop-blocking regression shows only via `would_have_blocked_bytes` (class-level) · [H06]
- **UART.N124** LIMIT · `digital_twin/machine.py:741-750` — "`if self.write_limit is not None: data = data[: self.write_limit]`"
  — TX side has no FIFO/`txbuf`/wire-time backpressure; `write()` returns immediately (low) · [H06]

## digital_twin/run_generic_integration.py

- **UART.N125** LIMIT · `digital_twin/run_generic_integration.py:263-265` — "Without it the twin models
  a dev board whose jumper is missing, and the exerciser spends the run timing out" — UART wiring
  depends on the plan's `uart` key and on private `uart._uart`/`poller` attributes · related: TWIN.T12 ·
  [H06]

## tests/test_digital_twin_machine_uart.py

- **UART.N126** ASSUME · `tests/test_digital_twin_machine_uart.py:29-31` — "Real machine.UART() re-inits
  the peripheral rather than refusing" — Port behaviour claim · [H06]

## tests/test_digital_twin_uart_link.py

- **UART.N127** LIMIT · `tests/test_digital_twin_uart_link.py:86-91` — "Drives the responder's own
  UART_Comm.uart_listen() directly rather than UartLinkExerciser's real listen-loop task, deliberately"
  — Real listen-loop task not exercised in this file · [H06]
- **UART.N128** SETTLED · `tests/test_digital_twin_uart_link.py:147-148` — "payload_size and timeout are
  out-of-band agreements that must match on both ends, and nothing is negotiated" — CLAUDE.md owner
  decision restated · [H06]
- **UART.N129** ASSUME · `tests/test_digital_twin_uart_link.py:284-285` — "timeout is sized well above
  the measured worst-case collection pause" — Relies on a measured GC pause on the host, not rp2 · [H06]

## tests_hardware/flash/test_uart_crossover.py

- **UART.N130** LIMIT · `tests_hardware/flash/test_uart_crossover.py:44-46` — "One Python instance as
  initiator and one as responder interoperating perfectly is a required, tested property" — Jumper tests
  prove Python↔Python only; the C peer (out of scope) is never on the other end here. · related:
  UART.T07 · [H07]
- **UART.N131** SETTLED · `tests_hardware/flash/test_uart_crossover.py:52-53` — "the one it deliberately
  cannot - which must therefore be diagnosed rather than absorbed" — Parameter mismatch is diagnosed,
  never negotiated (owner decision in CLAUDE.md). · [H07]
- **UART.N132** PLATFORM · `tests_hardware/flash/test_uart_crossover.py:59-61` — "POLLIN fires on the
  first byte, so asking the peripheral for a whole frame blocks the event loop for its remaining wire
  time" — F.5.8 platform fact, asserted on silicon. · related: UART.T10 · [H07]

## tests_hardware/device_scripts/uart_crossover_exchange.py

- **UART.N133** LIMIT · `tests_hardware/device_scripts/uart_crossover_exchange.py:34-36, 72-73` — "a
  link that never answers parks the listener in uart_listen()'s one unbounded read, and waiting that out
  outlasts the watchdog"; "clear() is the module's own documented unstick" — src listener has an
  unbounded read; scripts must poll-and-feed and call clear() (J.5). · related: UART.T02 · [H07]

## tests_hardware/device_scripts/uart_crossover_recovery.py

- **UART.N134** SETTLED · `tests_hardware/device_scripts/uart_crossover_recovery.py:139-141` — "A
  mismatched payload_size is agreed out of band and never negotiated, so it cannot be recovered from -
  only diagnosed" — Owner decision (no negotiation) pinned on silicon. · [H07]

## tests_hardware/device_scripts/uart_idle_poll_rate.py

- **UART.N135** LIMIT · `tests_hardware/device_scripts/uart_idle_poll_rate.py:49-51` — "UART1 alone:
  nothing drives UART0 ... the listener parks in the one deadline-less wait this protocol issues" — Only
  the responder's deadline-less wait is covered. (low) · related: UART.T02 · [H07]

## tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py

- **UART.N136** LIMIT · `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:4-5, 46, 60` —
  "Raw machine.UART on purpose: this pins the behaviour the driver's clamp exists to avoid, so it stays
  true independently of how asy_uart_driver is arranged internally" — Measures the platform hazard and a
  hand-written clamp, not asy_uart_driver's own clamp — a driver regression would not fail it. ·
  related: UART.T10 · [H07]

## tests_hardware/README.md

- **UART.N137** ASSUME · `tests_hardware/README.md:439-448` — "96 passed, 2 known-permanent skips, 41
  min, with the four SCD30-EEPROM-write tests deselected" — Dated 2026-09-12 run; F.5.8 4394 us vs 121
  us; F.5.9 1336/1266 vs 60/60 rounds. · related: PERF.T07 · [H08]
- **UART.N138** ASSUME · `tests_hardware/README.md:466-471` — "a responder notices the first byte of a
  frame up to 50 ms late by design" — First-frame latency on the rig includes `POLL_IDLE_MS`; not a link
  fault. · related: PERF.T07 · [H08]
- **UART.N139** TODO · `tests_hardware/README.md:1256-1262` — "no real-hardware run ever calls the
  actual shipped clamp" — F.5.8 never-block invariant tested only via raw `machine.UART` (queue G12). ·
  [H08]
- **UART.N140** TODO · `tests_hardware/README.md:1265-1269` — "\"bench ⊇ flash\" (E.6.1) doesn't hold
  for the multi-chunk SET train" — Exerciser only calls `uart_get(_CMD_BANNER)`; needs a
  production-exerciser change (queue G1). · related: UART.T06 · [H08]
- **UART.N141** SETTLED · `tests_hardware/README.md:1276-1279` — "**Answered 2026-09-22 (owner): it is a
  structural exception, for now.**" — Mock UART hazard catalog (~20 scenarios) stays mock-only as
  E.6.6's fourth exception; "Revisit when that hardware exists". · related: HW.T09 · [H08]

## REAL_HARDWARE_TEST_QUEUE.md (snapshot only; being updated by another session)

- **UART.N142** TODO · `REAL_HARDWARE_TEST_QUEUE.md:219` — "it still needs a `UART_C_PORT_CHANGELOG.md`
  entry, which should be confirmed" — N3 OPEN: W11-over-W10 persisted-slot change unobserved on silicon
  (needs R13's babbling peer); changelog entry B32 exists (UART_C_PORT_CHANGELOG.md:103). · [H08]
  ⟨4dc80ef: N3 needs a babbling peer the bench lacks: open in BACKLOG.md "Real-hardware work still owed"
  (R13 + N3); R13 needs a babbling peer the bench lacks: open in BACKLOG.md "Real-hardware work still
  owed" (R13 + N3)⟩
- **UART.N143** TODO · `REAL_HARDWARE_TEST_QUEUE.md:249` — "confirm `GET /status` shows `W11` rather
  than `W10` ... and that a *boot* drain ... persists nothing" — R13 OPEN (low urgency): babbling-peer
  run over the crossover jumper. · [H08]
  ⟨4dc80ef: R13 needs a babbling peer the bench lacks: open in BACKLOG.md "Real-hardware work still
  owed" (R13 + N3)⟩
- **UART.N144** TODO · `REAL_HARDWARE_TEST_QUEUE.md:272` — "The bench UART exerciser never issues a
  multi-chunk SET" — G1 OPEN: wire a periodic SET into `UartLinkExerciser._exercise_loop()`. · related:
  UART.T06 · [H08]
  ⟨4dc80ef: G1 scratched by the owner 2026-09-25: src/ is never changed only for a test (230a8df;
  BACKLOG.md:92-94)⟩
- **UART.N145** TODO · `REAL_HARDWARE_TEST_QUEUE.md:277` — "no silicon run calls `asy_uart_driver`'s own
  `ready()`/`_buffered()` clamp" — G12 OPEN (script to write). · [H08]
  ⟨4dc80ef: G12 done 2026-09-25: uart_driver_read_never_blocks_the_loop.py, 7/7 (2f48f86)⟩
- **UART.N146** SETTLED · `REAL_HARDWARE_TEST_QUEUE.md:301-303` — "`arduino/` is outside this project's
  scope (owner, 2026-09-24), reconciliation included" — G10 excluded. · [H08]
  ⟨4dc80ef: G10 excluded on purpose (arduino/ out of scope): BACKLOG.md "Still owed elsewhere"⟩

## buildgen/codegen.py

- **UART.N147** SETTLED · `buildgen/codegen.py:631-633` — "Only the initiator side owns real
  transfer/failure counts" — Responder reports no link status. · [H09]

## buildgen/validate.py

- **UART.N148** SETTLED · `buildgen/validate.py:256-258` — "a config mismatch the owner puts out of
  runtime scope (Part C.7.2), so the build refuses it instead" — UART link timing/buffer floors enforced
  at build time only; "generated code wires no CRC or framing, so both add 0". · [H09]

## devices/dev.toml

- **UART.N149** ASSUME · `devices/dev.toml:38-40` — "Buffers and poll rates are sized from the real
  53-byte frame and this bench's poll rate, not the driver defaults (J.6)." — UART rxbuf/txbuf/poll
  values bench-tuned; the crossover jumper (GP0<->GP9, GP1<->GP8) is physical. · [H09]
- **UART.N150** SETTLED · `devices/dev.toml:150-154` — "wozi never gets a UART instance: it is never
  flashed, so the peripheral would be untestable (CLAUDE.md)" — Per-end FRAM chunk for each uart_link
  (WP3). · [H09]

## tests_scripts/test_buildgen_validate.py

- **UART.N151** MIRROR · `tests_scripts/test_buildgen_validate.py:1241-1246` — "Mirrors dev.toml's
  uart0/uart1 initiator/responder shape ... dev.toml's bus knobs too" — Fixture copies dev.toml's UART
  knobs (115200, rxbuf/txbuf 512, poll_wait 2, poll_idle 50) by hand · [H10]
- **UART.N152** MIRROR · `tests_scripts/test_buildgen_validate.py:1256-1257,1268,1279,1290-1291,1302` —
  "2 x 2 + poll_idle_ms + 21ms GC pause against UartLinkExerciser's 1000ms timeout: 975 is the last idle
  poll that fits" — Build-time UART arithmetic pins the measured 21 ms GC pause, 53-byte frame (5 header
  + 48 payload), UART defaults (rxbuf 256, poll 20 ms) and errno 11/15 of `UART_Comm.setup()`; build and
  runtime checks must agree · related: UART.T10 · [H10]

## tests_scripts/test_digital_twin_ci_suite_errcount.py

- **UART.N153** LIMIT · `tests_scripts/test_digital_twin_ci_suite_errcount.py:129-130` — "uart_link's
  peer is a second UART_Comm rather than a faultable fake, so it is out by mechanism" — UART link is
  outside the twin's bus-fault matrix (Runs 3/4/5c) · related: TWIN.T05 · [H10]

## SPECIFICATION.md Part A.3 (Refactor status, 129-146)

- **UART.N154** SETTLED · `SPECIFICATION.md:142-145` — "`wozi` deliberately does not, since it is never
  physically flashed and would otherwise carry an untestable peripheral" — UART pair on dev only, never
  wozi. · related: PAR.S13 · [H12]

## SPECIFICATION.md Part A.7 (wozi's construction order and dependency graph, 358-569)

- **UART.N155** INVAR · `SPECIFICATION.md:446-451` — "The variant also runs a small link exerciser task
  on the initiator side ... surface through `/status`, which the bench tier asserts advancing under
  load" — Dev-only bench mechanism; its counters live in `/status`. · related: UART.T06 · [H12]

## SPECIFICATION.md Part C.3.2 (UART variant, 1598-1622)

- **UART.N156** SETTLED · `SPECIFICATION.md:1608-1610` — "Settled precedent: one merged class, not a
  session+protocol pair ... the accepted shape for any future point-to-point wrapper" — UART shape
  decision. · [H12]

## SPECIFICATION.md Part C.7 (Error handling & logging contract, 1807-1891)

- **UART.N157** ASSUME · `SPECIFICATION.md:1859-1864` — "Across a 20.8s window carrying three
  back-to-back `ResetErrors` calls (~6.9s each ...) ... 23 further transfers with zero failures" —
  Single silicon run supporting the UART never-block invariant. · [H12]

## SPECIFICATION.md Part C.7.1 (Running errno/wrnno table, 1893-1941)

- **UART.N158** DRIFT · `SPECIFICATION.md:1914-1916` — "`repeat=True`, which still counts it and still
  writes the updated count through to FRAM" — UART repeats go to sync `pr.err()` which neither persists
  nor counts. · covered-by: UART.S01 · [H12]
- **UART.N159** SETTLED · `SPECIFICATION.md:1944` — "`wrnno` 11 outranks 10 for the episode's single
  slot (owner decision, 2026-09-18" — UART resync warning priority. · [H12]

## SPECIFICATION.md Part E.6 / E.6.1-E.6.6 (Shared behaviours, real-hardware tier, 3090-3225)

- **UART.N160** SETTLED · `SPECIFICATION.md:3220-3227` — "The UART fault-injection catalog stays
  mock-only until injection hardware exists (owner decision, 2026-09-22)" — Deferred; revisit trigger =
  hardware exists. · [H12]

## SPECIFICATION.md Part E.8 (Measurement traps, 3271-3362)

- **UART.N161** INVAR · `SPECIFICATION.md:3367-3370` — "every hazard check runs in both CRC modes ... 48
  checks, 96 tests ... The deployed link runs `CRC_Pass`" — Standing rule; counts dated; dev link is
  uncrc'd. · related: UART.S04 · [H12]

## SPECIFICATION.md Part F.5.7 — UART.deinit() RX buffer unrooted

- **UART.N162** INVAR · `SPECIFICATION.md:3878-3884` — "`asy_uart_driver.UART.init()` therefore calls
  `machine.UART(...)` rather than `self._uart.init(...)`, and that choice is load-bearing" —
  Must-not-simplify rule; guarded only by a comment (`src/asy_uart_driver.py:199-207`) and the hardware
  injector `tests_hardware/device_scripts/uart_crossover_recovery.py`, no unit test named. · related:
  UART.T09 · [H13]

## SPECIFICATION.md Part F.5.8 — UART read() blocks the loop

- **UART.N163** SETTLED · `SPECIFICATION.md:3907-3910` — "owner direction, 2026-09-11: they may time out
  and handle it, but may never block synchronously, not even in a wait state" — Owner rule for
  `asy_uart_driver.py`/`asy_uart_comm.py` (dup of CLAUDE.md hard rule). · covered-by: BUS.T05 · [H13]

## SPECIFICATION.md Part F.5.9 — Idle ready() poll cost

- **UART.N164** INVAR · `SPECIFICATION.md:4023-4025` — "Part J.6 requires a single-digit `poll_wait_ms`
  precisely because poll granularity, not baud rate, dominates" — Deployment constraint on
  `poll_wait_ms`. · related: UART.T10 · [H13]
- **UART.N165** INVAR · `SPECIFICATION.md:4049-4054` — "a wait with no deadline is by construction an
  idle listener — `_read_frame(device, -1)` inside `uart_listen()` is the only one this protocol issues"
  — Rate selection assumes every deadline-less wait is an idle listen; the plan notes `_write_all` also
  waits on `ready(POLLOUT)` with no deadline at the idle rate (`BUS.S05`). · related: BUS.S05 · [H13]
- **UART.N166** INVAR · `SPECIFICATION.md:4056-4060` — "`poll_idle_ms` bounds how late the first byte of
  a frame is noticed, so it belongs well under the peer's own reply timeout ... opt-in per instance" —
  Partly enforced: `buildgen/validate.py:270-273` requires `timeout >= 2*poll_wait + poll_idle + gc_pause`;
  an instance without `poll_idle_ms` keeps the idle CPU cost. · related: UART.T05, PERF.T07 · [H13]

## SPECIFICATION.md Part G.2 — Known reusable primitives

- **UART.N167** INVAR · `SPECIFICATION.md:4236-4240` — "write order is build → CRC → encode → delimiter
  and read order the exact reverse ... A pass-through codec is the default and emits byte-for-byte what
  the driver emitted before" — Wire-order contract; a default change would alter emitted bytes (Class A
  territory). · related: ALGO.S05 · [H13]

## SPECIFICATION.md Part J (intro)

- **UART.N168** SETTLED · `SPECIFICATION.md:5163-5166` — "No vendor document or prior specification
  exists — this Part **is** the specification, reconstructed from the field-proven legacy implementation
  ... confirmed by the project owner (2026-09-11)" — Part J is the normative contract for both
  implementations. · related: UART.T01 · [H13]
- **UART.N169** INVAR · `SPECIFICATION.md:5168-5172` — "a never-raise contract on every entry point" —
  `UART_Comm` never-raise contract. · related: UART.T01 · [H13]
- **UART.N170** MIRROR · `SPECIFICATION.md:5175-5176` — "the differences are enumerated in
  `UART_C_PORT_CHANGELOG.md`" — Part J ↔ changelog ↔ legacy `python/IndividualDrivers/asy_uart_comm.py`.
  · covered-by: UART.T07 · [H13]

## SPECIFICATION.md Part J.1 — Scope and two-implementation contract

- **UART.N171** SETTLED · `SPECIFICATION.md:5311-5314` — "The module is **standalone and
  self-contained** ... Its first use case (a BME688/BSEC coprocessor) is explicitly *not* part of its
  scope" — Owner scope decision (dup of CLAUDE.md). · related: DOC.T14 · [H13]
- **UART.N172** ASSUME · `SPECIFICATION.md:5316-5325` — "checked rather than assumed (2026-09-13).
  `dev_legacy/asy_bsec_driver.py`'s whole `BSEC_UART` control flow replays over the promoted module ...
  Two conformance tests ... demonstrate rather than constrain" — BSEC-serving claim rests on two tests
  that "any API able to express the flow passes". · [H13]
- **UART.N173** LIMIT · `SPECIFICATION.md:5326-5328` — "**One deployed value has to change in a faithful
  port**: `rxbuf` 32 is refused (`errno` 15) against this module's 80-byte per-poll-interval `rxbuf`
  floor (J.6)" — Legacy deployment parameters are not drop-in compatible. · related: UART.T05 · [H13]
- **UART.N174** ASSUME · `SPECIFICATION.md:5333-5336` — "It mirrors the Python implementation's
  *intended* behavior ... **how far that mirroring extends to the known flaws is unverified** ...
  Establishing that is future work" — C peer conformance explicitly unverified (C side out of scope,
  owner 2026-09-24). · related: UART.T07 · [H13]
- **UART.N175** MIRROR · `SPECIFICATION.md:5333-5344` — "**A second implementation of this protocol
  exists in C** ... **Every protocol-level change is logged in `UART_C_PORT_CHANGELOG.md`**" — Python↔C
  two-implementation mirror; changelog is the only bridge. · covered-by: UART.T07 · [H13]
- **UART.N176** SETTLED · `SPECIFICATION.md:5345-5350` — "**Prefer Class A changes that only tighten
  receiver validation, never ones that change emitted bytes.** ... A change to emitted bytes is a
  coordinated flag-day needing an explicit owner decision" — Change-class policy. · related: UART.S04 ·
  [H13]
- **UART.N177** OPENQ · `SPECIFICATION.md:5348-5349 vs 5324-5326` — "conditional on the C side actually
  conforming, which each such change must re-verify against the C source" — Per-change re-verification
  against a C source whose reconciliation is out of scope (owner, 2026-09-24) — the obligation has no
  reachable executor (low). · related: DOC.S14, UART.T07 · [H13]

## SPECIFICATION.md Part J.2 — Role model

- **UART.N178** SETTLED · `SPECIFICATION.md:5354-5357` — "This is not a symmetric peer protocol ...
  simultaneous initiation is out of contract rather than a case to handle" — No collision arbitration by
  design. · related: DOC.T14 · [H13]
- **UART.N179** INVAR · `SPECIFICATION.md:5364-5371` — "**The role is enforced structurally, not by
  convention.** ... The responder's own answer to a GET ... runs through the internal unlocked SET path,
  not through the public `uart_set()` entry point" — Role gate on public entry points; internal unlocked
  path must stay unexposed. · related: UART.T01 · [H13]

## SPECIFICATION.md Part J.3 — Frame format

- **UART.N180** INVAR · `SPECIFICATION.md:5375-5377` — "Every frame is exactly `5 + payload_size` bytes
  ... **the fixed size is the framing**" — Wire-format contract (Class A). · covered-by: UART.T01 ·
  [H13]
- **UART.N181** LIMIT · `SPECIFICATION.md:5385-5386` — "Without a CRC, the only integrity checking left
  is this layer's own structural validation" — `dev` runs `CRC_Pass` (codegen never passes `crc=`). ·
  covered-by: UART.S04 · [H13]
- **UART.N182** SETTLED · `SPECIFICATION.md:5382-5384` — "Selecting a delimited codec is a wire change
  and a coordinated flag day (changelog A11), not a local decision." — Owner-gated change. · [H13]
- **UART.N183** PLATFORM · `SPECIFICATION.md:5388-5393` — "an LSB-first/right-shifting variant over poly
  `0x1021` with init `0xFFFF`, appended in the platform's **native** byte order ... interoperates
  between the two peers only because both happen to be little-endian" — Legacy CRC wire compatibility
  depends on both MCUs' endianness. · related: ALGO.T03 · [H13]
- **UART.N184** MIRROR · `SPECIFICATION.md:5389-5397` — "`python/IndividualDrivers/asy_uart.py`'s own
  `CRC16`, which is what the C peer mirrors ... `src/crc_checks.py`'s `CRC16` is a genuine MSB-first
  CRC-16/CCITT-FALSE appended big-endian. **The two are not wire-compatible**" — Legacy↔C mirror broken
  by the refactor's CRC; flag-day recorded as changelog A7. · related: ALGO.T03, UART.T07 · [H13]
- **UART.N185** INVAR · `SPECIFICATION.md:5401, 5411-5423` — "**Never `0xFF`** ... Do not \"fix\" the
  wrap to `0xFF`: it removes the barrier and the no-repeat-within-a-train property together" — Settled
  UID space (author-confirmed 2026-09-11). · related: UART.T01 · [H13]
- **UART.N186** INVAR · `SPECIFICATION.md:5419-5420` — "Any code predicting the *next* expected UID must
  reuse the same controlled wrap, never a bare `+1`" — Convention for any UID-predicting code (both
  languages). · related: UART.T01 · [H13]
- **UART.N187** ASSUME · `SPECIFICATION.md:5416-5418` — "The value space (`0 … 0xFE`, 255 values) is
  **exactly** as large as the longest possible train ... so no UID repeats within a single train" —
  Property holds only if one UID per frame and CHUNKS ≤ 255. · related: UART.T01 · [H13]

## SPECIFICATION.md Part J.4 — Transactions

- **UART.N188** INVAR · `SPECIFICATION.md:5427-5430` — "**Every frame is individually acknowledged
  before the next is sent** — stop-and-wait at frame granularity ... no windowing and no NAK" —
  Transaction contract. · covered-by: UART.T01 · [H13]
- **UART.N189** INVAR · `SPECIFICATION.md:5432-5434` — "`CHUNKS = ceil(len(payload) / payload_size) + 1`,
  floored at 2" — SET train sizing rule. · covered-by: UART.T01 · [H13]
- **UART.N190** INVAR · `SPECIFICATION.md:5436-5440` — "the initiator sends a one-chunk GET train" — GET
  is one chunk; receiver does not enforce `CHUNKS=1`. · covered-by: UART.S02 · [H13]
- **UART.N191** INVAR · `SPECIFICATION.md:5448-5450` — "Rejection is signalled by withholding an ACK ...
  The final chunk's acknowledgement is deliberately deferred until after the total-size check passes" —
  Rejection semantics; basis of the at-least-once seam (J.9). · covered-by: UART.T08 · [H13]

## SPECIFICATION.md Part J.5 — Timing, flow control, recovery

- **UART.N192** INVAR · `SPECIFICATION.md:5454-5457` — "A half-received frame must complete promptly or
  the whole frame is abandoned — the anti-desync rule." — Two-level timeout contract. · covered-by:
  UART.T02 · [H13]
- **UART.N193** INVAR · `SPECIFICATION.md:5459-5470` — "drains its receive path until the line has been
  quiet for `1.5 × timeout`, then holds off initiating for a further `1.5 × timeout` ... **Both
  constants are part of the contract**" — Class A recovery timings; "found violating this on 2026-09-13
  and fixed" for local mid-train aborts. · covered-by: UART.T02 · [H13]
- **UART.N194** INVAR · `SPECIFICATION.md:5472-5473` — "The write hold-off gates *initiating*
  transmissions only: acknowledgements are always sent" — Hold-off scope. · related: UART.S07 · [H13]
- **UART.N195** INVAR · `SPECIFICATION.md:5484-5492` — "**Hitting the bound is reported by flagging the
  caller, never by logging in place**: the boot drain is not a fault and so persists nothing, while a
  resync persists the more specific of its two warnings" — Logging contract for drains (C.7.1 `wrnno`
  10/11). · related: UART.T02, UART.T04 · [H13]

## SPECIFICATION.md Part J.6 — Deployment parameters

- **UART.N196** SETTLED · `SPECIFICATION.md:5496-5500` — "`payload_size` and `timeout` are **agreed out
  of band** ... nothing is negotiated, now or at the C reconciliation (owner decision, 2026-09-11)" — No
  version/capability negotiation. · related: DOC.T14 · [H13]
- **UART.N197** SETTLED · `SPECIFICATION.md:5502-5516` — "**That diagnostic has a known blind spot,
  accepted rather than fixed** (owner decision, 2026-09-12) ... `errno` 32 never fires" — Accepted
  diagnostic gap for a speak-when-spoken-to peer; pinned by `tests/test_uart_comm_hazard.py`'s
  `..._a_peer_that_never_produces_a_valid_frame_is_diagnosed`. · [H13]
- **UART.N198** LIMIT · `SPECIFICATION.md:5508-5511` — "**What it misses is a speak-when-spoken-to
  peer** ... presents as repeated `errno` 22 (read timeout) plus `wrnno` 10 resync warnings" — Known
  misdiagnosis signature. · [H13]
- **UART.N199** INVAR · `SPECIFICATION.md:5516-5519` — "`payload_size` must be in `1 … 255` ... an
  out-of-range value must never be silently clamped — C.13's readiness-gate treatment instead" —
  Construction contract. · related: UART.T05 · [H13]
- **UART.N200** RISK · `SPECIFICATION.md:5521-5527` — "21.8 % efficiency for a single-chunk transfer,
  39.7 % at 480 bytes, and an asymptote of **43.6 %**. This is accepted for the intended traffic" —
  Accepted wire inefficiency; A10/A11 candidates. · [H13]
- **UART.N201** INVAR · `SPECIFICATION.md:5529-5537` — "**A `UART` instance driving this protocol must
  therefore be constructed with a single-digit `poll_wait_ms`**; leaving the default in place makes
  every other efficiency property of the protocol irrelevant" — Not mechanically enforced:
  `buildgen/validate.py:270-276` checks only the timeout/rxbuf floors; driver default stays 20 ms. ·
  related: UART.T05, UART.T10 · [H13]
- **UART.N202** INVAR · `SPECIFICATION.md:5543-5547` — "**That is a construction refusal, not just a
  rule** — `timeout`'s floor below is the enforcement, and it carries `poll_idle_ms`" — Enforced in
  `src/asy_uart_comm.py:260` and `buildgen/validate.py:271-273`. · covered-by: UART.T05 · [H13]
- **UART.N203** INVAR · `SPECIFICATION.md:5549-5561` — "**`rxbuf` is checked at construction against two
  independent floors** ... `timeout` has a floor too: `2 × poll_wait_ms + poll_idle_ms +` the measured
  worst-case GC pause" — Floors rely on the measured 21 ms GC constant. · covered-by: UART.T10 · [H13]
- **UART.N204** LIMIT · `SPECIFICATION.md:5552-5553` — "at `payload_size = 255` that is 260 bytes
  against the driver's own 256-byte default, so the maximum legal `payload_size` overruns the default
  outright" — Driver default `rxbuf` cannot carry a max-size frame. · related: UART.T05 · [H13]

## SPECIFICATION.md Part J.8 — Memory model

- **UART.N205** INVAR · `SPECIFICATION.md:5635-5640` — "**Two long-lived frame buffers per instance**
  ... sized ... `framing.max_encoded(5 + payload_size + crc_length)` ... Steady-state frame traffic
  allocates nothing." — Zero-allocation frame path claim. · related: UART.T03 · [H13]
- **UART.N206** INVAR · `SPECIFICATION.md:5648-5649` — "**A failed allocation degrades to the module's
  normal failure sentinel** and the quiesce-and-resync path, never an exception" — Never-raise contract
  for allocation failures. · related: UART.T03 · [H13]
- **UART.N207** SETTLED · `SPECIFICATION.md:5651-5655` — "a received frame is read whole into the
  instance's RX frame buffer and its payload region then slice-assigned ... *not* read header-first" —
  Deliberate design choice. · [H13]
- **UART.N208** INVAR · `SPECIFICATION.md:5657-5659` — "**Padding must be zero-filled from a
  preallocated zero buffer** ... leaving them unwritten would transmit the previous frame's payload
  remnants" — Data-leak invariant. · related: UART.T01 · [H13]

## SPECIFICATION.md Part J.9 — Module contract

- **UART.N209** SETTLED · `SPECIFICATION.md:5663-5671` — "**A plain class, not a `SensorReader`
  subclass** (owner-delegated decision, 2026-09-11, resolved against precedent)" — Base-class decision;
  errno/wrnno still align to `base_classes.py`'s reservation. · [H13]
- **UART.N210** INVAR · `SPECIFICATION.md:5673-5678` — "**`None` means failure; an empty result means a
  genuinely empty payload.** The two must never collapse, at any of the four result shapes" — Sentinel
  contract; `exp_size=None` vs `0`. · related: UART.T01 · [H13]
- **UART.N211** INVAR · `SPECIFICATION.md:5680-5683` — "**`uart_listen()` returns a `ListenResult`
  namedtuple** ... on every path ... Its one allocation is per logical message" — Result-shape contract.
  · related: UART.S05 · [H13]
- **UART.N212** SETTLED · `SPECIFICATION.md:5686-5692` — "**A lost final ACK folds into failure**,
  deliberately ... a caller that retries on a failed `uart_set()` must tolerate the peer seeing the
  message twice" — At-least-once seam; idempotency obligation on callers, unenforced. · covered-by:
  UART.T08 · [H13]

## CLAUDE.md

- **UART.N213** INVAR · `CLAUDE.md:119-126` — "every change made to it gets an entry in
  `UART_C_PORT_CHANGELOG.md`" — Every change is classified as protocol-level (Class A) or
  Python-internal, and both are logged. Convention only: no test or hook checks the changelog; only
  src/asy_uart_comm.py, src/framing_codecs.py and tests/test_uart_comm_hazard.py name it. · covered-by:
  UART.T07 · [H14]
- **UART.N214** TODO · `CLAUDE.md:123-125` — "a temporary file, deleted once the C side is reconciled
  ... reconciling it is outside this project's scope, owner, 2026-09-24" — A temporary file whose
  deletion trigger can never be reached. · covered-by: DOC.S14 · [H14]
- **UART.N215** SETTLED · `CLAUDE.md:126-129` — "Prefer a protocol-level change that only tightens
  *receiver* validation over one that alters emitted bytes" — Changing emitted bytes is a flag-day that
  needs the owner's decision (e.g. enabling CRC). · related: UART.S04 · [H14]
- **UART.N216** ASSUME · `CLAUDE.md:129-131` — "The C side's conformance is expected but unverified" —
  Every Class A entry must be re-verified against the C source at reconciliation, which is out of scope.
  · related: UART.T07 · [H14]
- **UART.N217** RISK · `CLAUDE.md:131-135` — "prototypical ... with no device in the field running it
  (owner, 2026-09-11)" — Accepted premise: no changelog entry can break a live pair, because both sides
  are reflashed together. · [H14]
- **UART.N218** SETTLED · `CLAUDE.md:137-140` — "no version or capability negotiation is to be added" —
  Owner, 2026-09-11. `payload_size`/`timeout`/baud are fixed out of band; a mismatch is diagnosed as a
  dead link that carries bytes. · related: DOC.T14 · [H14]
- **UART.N219** SETTLED · `CLAUDE.md:141-143` — "strictly initiator/responder, never a symmetric peer —
  there is no collision arbitration" — Simultaneous initiation is out of contract. The module is
  standalone; its BME688/BSEC use case constrains nothing. · related: UART.T01 · [H14]
- **UART.N220** SETTLED · `CLAUDE.md:144-145` — "`dev` carries two instances across its permanent
  crossover jumper and `wozi` carries none" — Matches devices/dev.toml:156-172; wozi.toml has no
  `uart_link`. · [H14]
- **UART.N221** INVAR · `CLAUDE.md:145-147` — "a change to any of them is Class A by definition" —
  Covers the `const()` wire constants and recovery timings in asy_uart_comm.py. Classification is
  convention only. · related: UART.T10 · [H14]

## README.md

- **UART.N222** INVAR · `README.md:680-684` — "its durable contracts are Part J (J.9 in particular), its
  open items are in BACKLOG.md" — Claims full migration of UART_PROMOTION_REQUIREMENTS.md. · related:
  UART.T01 · [H14]
- **UART.N223** TODO · `README.md:694-699` — "Carries those decisions across the gap until that C source
  ... is reconciled - outside this project's scope (owner, 2026-09-24) - then gets deleted." — The
  deletion trigger can never be reached. · covered-by: DOC.S14 · [H14]

## BACKLOG.md

- **UART.N224** TODO · `BACKLOG.md:89-91` — "a real-hardware test for UART's F.5.8 'never blocks'
  invariant against the actual shipped driver (not a hand-rolled clamp)" — Follow-on (a): no silicon
  test of the shipped driver's never-block invariant. · related: BUS.T05 · [H15] ⟨quote not matched at
  the anchor⟩
- **UART.N225** TODO · `BACKLOG.md:91` — "wiring a periodic SET into the bench UART exerciser's live
  load" — Follow-on (b): the bench exerciser carries no periodic SET. · related: UART.T06 · [H15]
  ⟨4dc80ef: G1 scratched by the owner 2026-09-25 (230a8df); tests_hardware/README.md:1265-1269 now says
  so⟩
- **UART.N226** SETTLED · `BACKLOG.md:480-482` — "arduino/ is out of this project's scope - SETTLED,
  owner, 2026-09-24." — Covers the UART C implementation's reconciliation and BME688/BSEC licensing. ·
  covered-by: LIC.T04 · [H15]
- **UART.N227** RISK · `BACKLOG.md:699-704` — "lets the peer size a heap allocation ... up to ~64 kB at
  payload_size = 255" — Responder whose `set_callback` returns `None`; caught and degraded; deliberately
  left. · covered-by: UART.T03, MEM.T03 · [H15]
- **UART.N228** INVAR · `BACKLOG.md:711-716` — "UART_Comm.setup() called a second time while its own
  listen loop is running would deadlock" — Unreachable only because the supervisor re-calls starters,
  never `setup()`. · related: XCUT.T02 · [H15]
- **UART.N229** SETTLED · `BACKLOG.md:838-846` — "owner-confirmed this stays as-is" — No sensor behind
  the UART link; BME688/BSEC out of scope. · [H15]

## UART_C_PORT_CHANGELOG.md (128 lines; owning area UART). Every entry is pending C-side reconciliation, which is out of scope (owner 2026-09-24).

- **UART.N230** SETTLED · `UART_C_PORT_CHANGELOG.md:3-4, 7-9` — "Temporary file. Delete it once the C
  implementation has been reconciled" — Its deletion trigger cannot be reached while reconciliation is
  out of scope. · covered-by: DOC.S14, UART.T07 · [H15]
- **UART.N231** ASSUME · `UART_C_PORT_CHANGELOG.md:10-13` — "how far that mirroring extends to the known
  flaws is unverified" — C-side conformance is unverified; every entry is a reconciliation task. · [H15]
- **UART.N232** SETTLED · `UART_C_PORT_CHANGELOG.md:15-23` — "the C implementation is prototypical ...
  no pair can be broken by any change recorded here" — Owner 2026-09-11; the obligation to record stays,
  the deployment risk does not. · [H15]
- **UART.N233** DRIFT · `UART_C_PORT_CHANGELOG.md:27` — "Every change to the module during its src/
  promotion gets an entry" — CLAUDE.md requires an entry for every change, not only changes made during
  promotion. (low) · related: UART.T07 · [H15]
- **UART.N234** SETTLED · `UART_C_PORT_CHANGELOG.md:34-46` — "the project owner has decided (2026-09-11)
  that the Python side may lead it" — Receiver-strictness is a preference, not a gate; each entry must
  still state its flag-day consequence. · [H15]
- **UART.N235** MIRROR · `UART_C_PORT_CHANGELOG.md:55` — "A1 — CMD validated by exact match against
  ACK/GET/SET, not by bitmask (&)" | Class A, status applied-python. To check in C: bitmask validation,
  multi-bit CMD. · related: UART.T01 · [H15]
- **UART.N236** MIRROR · `UART_C_PORT_CHANGELOG.md:56` — "A2 — Reject a train whose declared CHUNKS
  changes between frames" | Class A, status applied-python. · related: UART.T01 · [H15]
- **UART.N237** MIRROR · `UART_C_PORT_CHANGELOG.md:57` — "Whether the C sender increments UID per chunk
  exactly as Python does (expected, unverified)" — A3 (validate UID on data chunks), Class A, status
  applied-python. · related: UART.T01 · [H15]
- **UART.N238** MIRROR · `UART_C_PORT_CHANGELOG.md:58` — "Recovery constants stay exactly as they are:
  drain until quiet for 1.5 × timeout, then hold off" — A4, Class A, no change: both sides are bound by
  the same constants. · related: UART.T02 · [H15]
- **UART.N239** MIRROR · `UART_C_PORT_CHANGELOG.md:59` — "A5 — Bound the receive-drain loop (today
  unbounded)" | Class A, status applied-python. The bound must never be shorter than the C side's drain
  window. · related: UART.T02 · [H15]
- **UART.N240** INVAR · `UART_C_PORT_CHANGELOG.md:60` — "UID is never emitted as 0xFF; the counter wraps
  0xFE → 0" — A8, an author-confirmed invariant that both sides must keep. · related: UART.T01 · [H15]
- **UART.N241** MIRROR · `UART_C_PORT_CHANGELOG.md:61` — "The on-wire CRC changes algorithm and byte
  order" — A7, the only applied change that alters emitted bytes. Owner decision: Python leads. The flag
  day is recorded but not triggered: dev leaves `crc=` unset, so CRC_Pass runs and no CRC is on the
  wire; selecting CRC16 triggers it. · covered-by: UART.S04 · [H15]
- **UART.N242** TODO · `UART_C_PORT_CHANGELOG.md:62` — "A9 — Add a NAK command value, sent on a frame
  the receiver rejects" | Class A, status proposed. Degrades safely only if the C side's unknown-CMD
  path rejects and resyncs. · [H15]
- **UART.N243** TODO · `UART_C_PORT_CHANGELOG.md:63` — "A10 — Shorten the ACK frame to a bare 5-byte
  header" | Class A, status proposed. A flag day. · [H15]
- **UART.N244** TODO · `UART_C_PORT_CHANGELOG.md:64` — "A11 — Replace fixed-length framing with
  COBS-delimited variable-length frames" | Class A, status proposed, design resolved (the codec concept,
  B14). Selecting COBS is a flag day. · related: ALGO.T04 · [H15]
- **UART.N245** MIRROR · `UART_C_PORT_CHANGELOG.md:65` — "A12 — Validate the full SIZE invariant per
  chunk position" | Class A, status applied-python. Closes silent-corruption paths. · related: UART.T01
  · [H15]
- **UART.N246** INVAR · `UART_C_PORT_CHANGELOG.md:66` — "payload_size constrained to 1 … 255, identical
  on both ends, never silently clamped" — A6, fixed by out-of-band agreement. A mismatch desyncs the
  link. · related: UART.T05 · [H15]
- **UART.N247** SETTLED · `UART_C_PORT_CHANGELOG.md:72, :84` — "B1 — Well-defined return value for the
  unexpected-command case" | Superseded by B13 (namedtuple on every path). Class B. · related: UART.T08
  · [H15]
- **UART.N248** PLATFORM · `UART_C_PORT_CHANGELOG.md:73` — "Replace the one-shot machine.Timer write
  re-enable with a ticks_ms() deadline" — B2 (removes the dropped-soft-callback hang). The deadline is
  subject to the ticks_diff 2**29 horizon. · related: UART.S07, XCUT.T25 · [H15]
- **UART.N249** SETTLED · `UART_C_PORT_CHANGELOG.md:74-78` — "B3 — Timer.init()/MemoryError exception
  guards" | B3 to B7 (guards, guarded callbacks, logger, preallocated buffers, typing). B5 is superseded
  by B10. Class B. · [H15]
- **UART.N250** INVAR · `UART_C_PORT_CHANGELOG.md:79-80` — "the initiation entry points refuse on a
  responder (J.2)" — B8 (role enforcement) and B9 (buffer ownership per G.2, chunk-at-a-time forms). ·
  [H15]
- **UART.N251** INVAR · `UART_C_PORT_CHANGELOG.md:81` — "that catalog must also stay disjoint from the
  owner's own" — B10: errno and wrnno are numbered from 10; the catalogue stays disjoint by convention
  only. · related: XCUT.T07 · [H15]
- **UART.N252** SETTLED · `UART_C_PORT_CHANGELOG.md:82` — "B11 — Per-instance name ... support for more
  than one instance per device" | Class B. · [H15]
- **UART.N253** INVAR · `UART_C_PORT_CHANGELOG.md:84` — "None = failure, zero length = genuinely empty
  ... a lost final ACK stays folded into failure" — B13 contract. · related: UART.T08 · [H15]
- **UART.N254** INVAR · `UART_C_PORT_CHANGELOG.md:87` — "setup() drains the receive path once ...
  deliberately not counted as a fault" — B16. · [H15]
- **UART.N255** INVAR · `UART_C_PORT_CHANGELOG.md:88` — "at payload_size = 255 a frame is 260 bytes
  against this driver's own 256-byte default rxbuf" — B17 construction-time floors on rxbuf and timeout.
  · related: UART.T05, UART.T10 · [H15]
- **UART.N256** SETTLED · `UART_C_PORT_CHANGELOG.md:89` — "A distinct diagnostic when bytes keep
  arriving and not one frame ever validates" — B18 (errno 32). · [H15]
- **UART.N257** PLATFORM · `UART_C_PORT_CHANGELOG.md:90` — "MicroPython truncates that assignment
  silently (0x101 became 0x01)" — B19: validates caller arguments (errno 34). · related: PLAT.T02 ·
  [H15]
- **UART.N258** SETTLED · `UART_C_PORT_CHANGELOG.md:91` — "wrnno 10/11 ... are persisted at most once
  per fault episode" — B20 logging discipline. · related: UART.S03, UART.T04 · [H15]
- **UART.N259** SETTLED · `UART_C_PORT_CHANGELOG.md:92` — "uart_listen()'s owned task loop gains an
  optional message_callback" — B21 closes the gap where a responder could never see a SET payload. ·
  [H15]
- **UART.N260** INVAR · `UART_C_PORT_CHANGELOG.md:93` — "uart_set_stream(id, n, None) ... transmitted n
  bytes of padding and returned success" — B22 input validation (fixed). · [H15]
- **UART.N261** PLATFORM · `UART_C_PORT_CHANGELOG.md:94` — "a MicroPython bytearray slice assignment
  resizes on a length mismatch instead of raising" — B23: construction refused unless every buffer is
  allocated. · related: MEM.T03 · [H15]
- **UART.N262** LIMIT · `UART_C_PORT_CHANGELOG.md:97` — "errno 32 fires for a peer that spews onto an
  idle line ... but NOT for a speak-when-spoken-to peer" — B26, an accepted limitation (owner
  2026-09-12). Look for errno 22 plus wrnno 10 instead. · related: UART.T02 · [H15]
- **UART.N263** INVAR · `UART_C_PORT_CHANGELOG.md:98` — "a timeout that does not cover 2 x poll_wait_ms
  + poll_idle_ms + the worst-case GC pause" — B27 construction gates, including a codec with `ready() is False`.
  · related: UART.T05, UART.T10 · [H15]
- **UART.N264** SETTLED · `UART_C_PORT_CHANGELOG.md:99` — "one unimplemented command id polled by the
  peer cost two slots per round" — B28: wrnno 14 is persisted once per id; wrnno 13 fires on a rise. ·
  related: UART.S03 · [H15]
- **UART.N265** INVAR · `UART_C_PORT_CHANGELOG.md:100` — "every fault this module reports also resyncs,
  without exception" — B29: enforced structurally by the `_fault()` helper. · [H15]
- **UART.N266** INVAR · `UART_C_PORT_CHANGELOG.md:101` — "a declined command id is remembered in a
  32-byte one-bit-per-id map" — B30: three streamed-send abort paths now resync. · related: UART.T03 ·
  [H15]
- **UART.N267** SETTLED · `UART_C_PORT_CHANGELOG.md:102` — "reverses an earlier, incorrect 'never'
  decision" — B31 (WP3): FRAM/logger wiring runs through `UartLinkExerciser`. · related: UART.T06 ·
  [H15] ⟨quote not matched at the anchor⟩
- **UART.N268** SETTLED · `UART_C_PORT_CHANGELOG.md:103` — "wrnno 11 (drain bound reached) now outranks
  wrnno 10 (resync)" — B32 (owner 2026-09-18): the boot drain persists neither. · related: UART.S03 ·
  [H15]
- **UART.N269** SETTLED · `UART_C_PORT_CHANGELOG.md:126-128` — "The 0xFF UID barrier (A8) is unaffected
  either way." — · [H15]

## Commit messages (chronological)

- **UART.N270** SETTLED · `commit c9006dc` — "not adding rts/cts/flow support, no plan to revisit" —
  Owner decision: no UART hardware flow control. · tracked: SPECIFICATION.md:279-280 ("intentionally
  exposes no hardware flow control") | related: UART.T* · [H17]
- **UART.N271** INVAR · `commit 9e418ed` — "classify init()'s remaining raise surface as the same
  deliberate \"controlled path\" __init__ already was, and recorded in BACKLOG.md that upstream callers
  must handle it" — UART init() may raise; callers must handle. · status: BACKLOG entry no longer
  present; module docstring carries it (per commit) | related: UART.T* · [H17]
- **UART.N272** MIRROR · `commit 5f76c4e / 6a2d43e` — "Each is self-consistent ... and each rejects the
  other's frames ... A7 owner-decided (Python leads; CRC_Pass is the supported interim for a
  not-yet-reflashed peer)" — UART CRC variant differs from the legacy/C peer's; flag-day change
  recorded, C side out of scope. · tracked: UART_C_PORT_CHANGELOG.md A7; BACKLOG "arduino/ is out of
  this project's scope - SETTLED" | related: UART.T07 · [H17]
- **UART.N273** NOTE(FACT / DEFERRED) · `commit 8850974` — bytearray index-store truncates to 8 bits
  silently; four further UART findings deferred — Platform fact + deferred UART findings. · tracked:
  BACKLOG (UART items) / SPEC F.1 | related: PLAT.T* · [H17]
- **UART.N274** NOTE(DIVERGENCE) · `commit 9f4c084` — "the GET entry points validate their arguments
  before the readiness gate while the SET ones gate first" — Flagged, not changed; still true
  (uart_get_into checks buf before gating; uart_set_into gates first). · UNTRACKED (low) | related:
  UART.T* · [H17 (also H17)]
- **UART.N275** NOTE(FACT) · `commit 430be67` — GPIO16/17 reserved for a future BME688 BSEC UART0 — Pin
  reservation. · tracked: SPECIFICATION.md:5174 | - · [H17]
- **UART.N276** NOTE(RED-PUSH) · `commit 441de83` — "PUSHED DELIBERATELY WITH ONE RED TEST, on the
  project owner's direction ... tests/test_digital_twin_run_dev_integration.py is at 16/17" — Twin soak
  regression left red; UART fakes' wait "logged as deferred work"; H4 bench claim "vacuous ... Left open
  deliberately". · status: done-in 7cf989d (root cause = GC placement, fake counts would-block bytes)
  and dc05ce8 (H4 made real) | related: TEST.T* · [H17]
- **UART.N277** NOTE(OWNER / KNOWN-DEFECT) · `commit dc970fb` — "errno 32, the mismatched-peer
  diagnostic, cannot fire in the scenario it exists for ... Owner decision: document it" — Diagnostic
  dead in its target scenario; test pins current behaviour. · tracked: SPEC Part J.6,
  UART_C_PORT_CHANGELOG B26 | related: UART.T* · [H17 (also H17)]
- **UART.N278** NOTE(FLAG) · `commit 839c31e` — "wrnno 11 ... can never reach FRAM through the path that
  produces it ... BACKLOG open question 17 with the five-line patch" — Persisted-warning slot ordering.
  · status: done-in b0f755c (SPEC:1940 "wrnno 11 outranks 10 ... owner decision, 2026-09-18") | - · [H17
  (also H17)]
- **UART.N279** NOTE(PORT-NOTE) · `commit c0638bc` — "One deployed value has to change in a faithful
  port: rxbuf 32 is refused with errno 15"; legacy BSEC "struct.unpack(\"bbbbL\") ... only holds where a
  native long is 4 bytes" — Guidance for a future BSEC driver port. · status: recorded only in the
  conformance test / commit; no BACKLOG entry for a BSEC port (BSEC first use case declared out of scope
  in CLAUDE.md) | - · [H17]
- **UART.N280** NOTE(DEAD-CODE-KEPT) · `commit dfcbbe9` — "six in asy_uart_comm.py are a buffer or bound
  re-checked right after the check that already settled it, unreachable through any call path that
  exists - flagged rather than removed" — Deliberately kept unreachable guards. · tracked: SPEC
  E.5.1:2991 | - · [H17]
- **UART.N281** NOTE(SCOPE) · `commit dd734c0 / 12640c2` — "main's 2026-09-13 arduino/ import carries
  the UART protocol's C implementation ... The reconciliation is cloud work that gates G10" -> owner:
  arduino/ out of scope — C peer never reconciled. · tracked: BACKLOG (arduino/ SETTLED), queue G10
  Excluded | - · [H17]

## GitHub PRs and issues (hundertvolt/sensors)

- **UART.N282** NOTE(OUT-OF-SCOPE) · `https://github.com/hundertvolt/sensors/pull/81` — "**Three
  independent reasons the promoted Python cannot talk to the existing Arduino today**" — Open draft with
  Arduino C findings · SETTLED (arduino/ out of scope, 12640c2) | - · [H17]
