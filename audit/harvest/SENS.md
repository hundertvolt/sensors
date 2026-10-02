# Harvest — SENS: Sensor drivers

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`, moved to `4dc80ef` by V11).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 58, INVAR 54, MIRROR 17, LIMIT 72, RISK 15, ASSUME 57, PLATFORM 71, WORKAROUND 2, SUPPRESS 32, TODO 5, OPENQ 2, DRIFT 8, NOTE 19 — 412 items.


## src/asy_bmp3xx_driver.py

- **SENS.N001** ASSUME · `src/asy_bmp3xx_driver.py:5-7` — "Bosch BMP384/BMP388/BMP390 ... Verified
  against BST-BMP388-DS001/BST-BMP384-DS003 ... and the official BMP3_SensorAPI" — BMP390 is claimed
  supported but no BMP390 datasheet is in `datasheets/bmp3xx/` (only 384, 388, AN006). · covered-by:
  SENS.S20 · [H01]
- **SENS.N002** PLATFORM · `src/asy_bmp3xx_driver.py:36-37` — "_BMP388_CHIP_ID = const(0x50) # also
  reported by BMP384 (datasheet sec 4.3.1); BMP390 differs" — Chip-ID acceptance set {0x50, 0x60}; 0x60
  is sourced without a BMP390 datasheet (setup rejects anything else, :627-628). · related: SENS.S20 ·
  [H01]
- **SENS.N003** PLATFORM · `src/asy_bmp3xx_driver.py:49-54` — "ERR_REG bit 1 \"cmd_err\" ... STATUS bit
  4 ... bits 5+6: drdy_press — drdy_temp (sec 4.3.3)" | Register bit semantics taken from the BMP388/384
  datasheet sections cited. · related: SENS.T01 · [H01]
- **SENS.N004** PLATFORM · `src/asy_bmp3xx_driver.py:56-60` — "Datasheet sec 1, Table 2 operating ranges
  - the plausibility gate on a compensated reading." — 300-1250 hPa / -40..85 °C gate applied before
  PressOffset/TempOffset (see :486 vs :237). · covered-by: SENS.S13 · [H01]
- **SENS.N005** ASSUME · `src/asy_bmp3xx_driver.py:62` — "_CMD_RDY_TIMEOUT_MS = const(50) # cmd_rdy
  clears near-instantly outside an in-flight command" — 50 ms timeout rests on an unsourced
  "near-instantly" claim (no datasheet section cited). · related: SENS.T01 · [H01]
- **SENS.N006** PLATFORM · `src/asy_bmp3xx_driver.py:63` — "_MEAS_TIMEOUT_MS = const(300) # datasheet
  sec 3.9.2: max ~129ms at x32/x32 osr; generous margin" — Measurement timeout derived from the
  datasheet worst case. · related: SENS.S23 · [H01]
- **SENS.N007** PLATFORM · `src/asy_bmp3xx_driver.py:67-69` — "IIR filter coefficients (datasheet sec
  4.3.20 ...). Cross-checked against Bosch's reference driver, the Linux kernel IIO driver, and both
  datasheets." — Coefficient table's stated sources (low). · related: SENS.T01 · [H01] ⟨quote not
  matched at the anchor⟩
- **SENS.N008** MIRROR · `src/asy_bmp3xx_driver.py:71-72, 116-120` — "bounds kept in sync with
  _MIN/_MAX_TRIGGER_SECS by hand, since a comment cannot reference a name" — `@limits trigger_sec 1..3600`
  tag mirrors `_MIN/_MAX_TRIGGER_SECS` (and `_VAL_SI`); no test found enforcing the tag↔const agreement
  (quick grep). · related: GEN.T06, GEN.T03 · [H01]
- **SENS.N009** PLATFORM · `src/asy_bmp3xx_driver.py:118-119` — "BMP388/390's SDO pin selects the
  address: exactly 0x76 (low) or 0x77 (high)." — Address domain from SDO strapping; `@limits address in {0x76, 0x77}`
  (low). · [H01]
- **SENS.N010** DRIFT · `src/asy_bmp3xx_driver.py:89, 105` — "@web-group ... label=\"BMP388 — Pressure,
  Temperature\"" — UI label still says BMP388 although the module is BMP3XX and accepts BMP384/390
  (low). · related: PAR.S06 · [H01]
- **SENS.N011** MIRROR · `src/asy_bmp3xx_driver.py:100-103` — "_FIELDS = const((\"Pres\", \"Temp\",
  \"SLPres\", \"TS\")) # kept in sync with BMP3XX's own fields above" — Namedtuple fields vs `_FIELDS`;
  enforced by `tests_scripts/test_measurement_field_tuple_agreement.py`. · [H01]
- **SENS.N012** SETTLED · `src/asy_bmp3xx_driver.py:163-165` — "SampleInterv is a pure software timing
  knob with no hardware read-back, so it intentionally has no entry here." — Deliberate absence of a
  `_get_callbacks` entry for the failed-push recovery chain (low). · related: XCUT.T11 · [H01]
- **SENS.N013** SUPPRESS · `src/asy_bmp3xx_driver.py:171-178` — "caught here rather than by
  get_dict_cfg()'s try/except" + err_s "Error reading oversampling/filter config from sensor:" errno=22
  — Snapshot failure swallowed, fields reported None, persisted errno 22 on a REST GET path. ·
  covered-by: SENS.S18 · [H01]
- **SENS.N014** SUPPRESS · `src/asy_bmp3xx_driver.py:193-195` — err_s "Read failed:" errno=11 — Any
  exception in a measurement read swallowed to an all-None result (counted by `_error_check`). ·
  related: SENS.T03 · [H01]
- **SENS.N015** SUPPRESS · `src/asy_bmp3xx_driver.py:203-205` — err_s "Error in initial setup:" errno=10
  — Setup failure swallowed; read loop returns False for supervisor restart. · related: SENS.T14 · [H01]
- **SENS.N016** LIMIT · `src/asy_bmp3xx_driver.py:210-212` — err_s "Error reading config data!" errno=12
  — Config read failure aborts init (persisted). · related: SENS.T14 · [H01]
- **SENS.N017** INVAR · `src/asy_bmp3xx_driver.py:214-216` — "set_trigger_secs() never raises (logs
  errno=21, keeps the previous value) - a bad stored SampleInterv ... not a reason to fail this whole
  init" — Deliberate: bad stored interval degrades silently to the previous/constructor value. · [H01]
- **SENS.N018** SUPPRESS · `src/asy_bmp3xx_driver.py:221-223` — err_s "Error setting config data:"
  errno=13 — Hardware config apply failure swallowed, init fails. · [H01]
- **SENS.N019** LIMIT · `src/asy_bmp3xx_driver.py:231-234` — "comp_values = [0.0, 0.0, 0.0, 15.0]" +
  err_s "Error reading config data!" errno=14 — Degraded mode: on config read failure a fresh sample is
  published with hard-coded compensation, dropping user offsets; persisted each cycle. · covered-by:
  SENS.S25 · [H01]
- **SENS.N020** LIMIT · `src/asy_bmp3xx_driver.py:295-297` — "alarm-pool exhaustion (ENOMEM) - degrades
  gracefully ... (this sensor just never gets triggered this cycle)" — Timer arm failure is print-only
  (`pr.err`, not persisted); the sensor is then never triggered — "this cycle" understates it if
  starters run once per boot (low). · related: XCUT.T04, XCUT.S05 · [H01]
- **SENS.N021** SUPPRESS · `src/asy_bmp3xx_driver.py:310` — "# type: ignore[return-value]" —
  `get_data()` narrows base return type via ignore (C.4.2 convention). · related: SENS.T08 · [H01]
- **SENS.N022** SUPPRESS · `src/asy_bmp3xx_driver.py:327-345` — err_s "Error reading pressure
  oversampling:"/"...temperature oversampling:"/"...filter coefficient:" errno=15/17/19 — Getter
  failures swallowed to None (used by failed-push recovery chain). · related: XCUT.T11 · [H01]
- **SENS.N023** SUPPRESS · `src/asy_bmp3xx_driver.py:355-357` — err_s "Error setting trigger interval:"
  errno=21 — Invalid interval swallowed, previous kept. · [H01]
- **SENS.N024** SUPPRESS · `src/asy_bmp3xx_driver.py:364-382` — err_s "Error setting pressure
  oversampling:"/"temperature oversampling:"/"filter coefficient:" errno=16/18/20 — Setter failures
  swallowed to False. · [H01]
- **SENS.N025** ASSUME · `src/asy_bmp3xx_driver.py:408, 632` — "self._wait_time = 0.002 # just init with
  default here, set in setup()" / "change this value to have faster reads if needed" — 2 ms STATUS poll
  interval is a default nobody overrides (setup() default); tuning hint left from Adafruit (low). ·
  covered-by: SENS.S23 · [H01]
- **SENS.N026** PLATFORM · `src/asy_bmp3xx_driver.py:419-423` — "Datasheet sec 4.3.17 only documents
  encodings 0-5 (x1..x32); 6/7 are reserved and could surface from a bus disturbance" — Reserved OSR
  encodings raise OSError; the IIR field (:585-592) has no equivalent reserved-code check (all 8 codes
  mapped) (low). · related: SENS.T01 · [H01]
- **SENS.N027** PLATFORM · `src/asy_bmp3xx_driver.py:434-436` — "Forced-mode measurement (PWR_CTRL=0x13:
  press_en|temp_en|mode=forced, sec 4.3.16)." — Magic register value from datasheet (low). · related:
  SENS.T01 · [H01]
- **SENS.N028** INVAR · `src/asy_bmp3xx_driver.py:438-441, 542-544` — "Caller must already hold bmp3xx's
  device-session lock, spanning the whole operation." — `_wait_status_bits` relies on caller discipline
  for the device-session lock; not enforced. · related: BUS.T03 · [H01]
- **SENS.N029** LIMIT · `src/asy_bmp3xx_driver.py:446-447` — raise OSError("unexpected data burst read
  result") — "Unexpected" case text: non-bytes/short burst treated as bus fault (low). · [H01]
- **SENS.N030** PLATFORM · `src/asy_bmp3xx_driver.py:451-477` — "datasheet, sec 9.2 Temperature
  compensation" / "sec 9.3 Pressure compensation" — Floating compensation formulas (powers up to
  adc_p**3, 2**-65 scales) run in rp2 float32. · related: SENS.T01, PLAT.T08 · [H01]
- **SENS.N031** LIMIT · `src/asy_bmp3xx_driver.py:483-487` — "This bus has no CRC framing ... a bit flip
  in the burst read (or a NaN/inf ...) is otherwise undetectable" — Range gate is the only integrity
  check on BMP data; in-range corruption passes. · related: SENS.S13, XCUT.T23 · [H01]
- **SENS.N032** LIMIT · `src/asy_bmp3xx_driver.py:512-516` — "trimming data is verified against bounds
  this codebase doesn't have the exact values for - a factory-trimmed block is never legitimately
  all-0x00/all-0xFF" — Calibration check is an approximation of BST-MPS-AN006 (which is in
  `datasheets/bmp3xx/bst-mps-an006.pdf` — "doesn't have the exact values" may be checkable). · related:
  SENS.T01 · [H01]
- **SENS.N033** PLATFORM · `src/asy_bmp3xx_driver.py:517-521` — "See datasheet, pg. 27, table 22" /
  "forcing float math to prevent issues with boards that do not support long ints" — Calibration unpack
  layout and scaling constants; float math on a float32 target (legacy Adafruit comment). · related:
  SENS.T01, PLAT.T09 · [H01]
- **SENS.N034** PLATFORM · `src/asy_bmp3xx_driver.py:570-577` — "see
  https://www.weather.gov/media/epz/wxcalc/pressureAltitude.pdf" / "confirmed against the real Unix-port
  interpreter" — `get_altitude()` formula source; no production caller. · covered-by: SENS.S14 · [H01]
- **SENS.N035** PLATFORM · `src/asy_bmp3xx_driver.py:635-642` — "Matches Bosch's reference sequence
  (bmp3_soft_reset()) ... datasheet-confirmed 2ms post-reset settle time" — Soft-reset sequence parity
  with Bosch reference; 2 ms settle from datasheet. · related: SENS.T01 · [H01]
- **SENS.N036** LIMIT · `src/asy_bmp3xx_driver.py:644-646` — "if isinstance(err, int) and err &
  _ERR_CMD:" — The ERR_REG verification the comment promises (:637) is skipped when the read returns
  non-int (uninitialised bus → None) (low). · related: BUS.T06 · [H01]

## src/asy_isl29125_driver.py

- **SENS.N037** PLATFORM · `src/asy_isl29125_driver.py:5-7, 38-72` — "Verified against FN8424 Rev 3.00"
  / "_DEVICE_ID = const(0x7D) # datasheet p9, Table 2" ... register/bit map with page+table citations —
  Whole register map (ID, reset 0x46, CONFIG1-3 bits, INTSEL/PRST/CONVEN, STATUS bits) is taken from the
  datasheet pages cited. · related: SENS.T01 · [H01]
- **SENS.N038** INVAR · `src/asy_isl29125_driver.py:44` — "never addressed on its own - only ever
  written as the tail of a burst from 0x01/0x02" — CONFIG3 access discipline by convention. · [H01]
- **SENS.N039** PLATFORM · `src/asy_isl29125_driver.py:53, 1424-1426` — "kept 0: a 1 turns INT into an
  INPUT and inverts the whole path" — SYNC/CONVEN forced 0 explicitly at setup. · related: SENS.T05 ·
  [H01]
- **SENS.N040** PLATFORM · `src/asy_isl29125_driver.py:62-66` — "Reserved bits, which p9 says \"can
  change without any notice\" - masked out of every shadow-vs-chip comparison" — Divergence check
  depends on the reserved-bit masks (confirmed on silicon per M.1.2). · related: SENS.S24 · [H01]
- **SENS.N041** PLATFORM · `src/asy_isl29125_driver.py:72, 1246-1248` — "B7:B6 and B3 read zero on a
  working part (p12, Table 15)" — Reserved STATUS bits used as the bus-fault discriminator. · [H01]
- **SENS.N042** ASSUME · `src/asy_isl29125_driver.py:87-88` — "_CYCLE_MS_16BIT = const(303) # 3 x tINT,
  tINT = 101ms typ" / "_CYCLE_MS_12BIT = const(19) # 3 x ~6.3ms: p6 makes tINT an n-bit counter on one
  oscillator, 101 x 2**-4" — Cycle lengths use the *typical* tINT and an inferred 12-bit value; settle
  deadlines and PRST derivation depend on them (oscillator tolerance not modelled). · related: SENS.T01,
  SENS.T05 · [H01]
- **SENS.N043** SETTLED · `src/asy_isl29125_driver.py:90-91` — "Device/maths constants, deliberately NOT
  config fields - requirement 1 (SPECIFICATION.md Part M.1.1) governs preferences" — Owner requirement:
  these constants are not user-configurable. · [H01]
- **SENS.N044** ASSUME · `src/asy_isl29125_driver.py:92` — "_DARK_COUNTS = const(1) # DDark typ 1 / max
  5 counts at range 0" — Uses the typical dark count; subtraction after `<<4` at 12 bit. · covered-by:
  SENS.S17 · [H01]
- **SENS.N045** ASSUME · `src/asy_isl29125_driver.py:93-94` — "_CCT_FLOOR_COUNTS = const(64) # ~13x the
  worst-case dark count: below it a 5-count additive error moves a channel ratio by more than ~8%" —
  Derived low-light floor for CCT (below it CCT is None). · related: SENS.T01 · [H01]
- **SENS.N046** ASSUME · `src/asy_isl29125_driver.py:95-97` — "_GAIN_RATIO_MIN = const(20.0) # a
  plausibility gate around nominal, applied where an untrusted value enters (on load and on learn),
  never in the hot path" — Gate relies on ConfigManager enforcing the schema bound on load (:323
  "already schema-bounded to [20, 34] on the way in"). · related: CORE.T01, CORE.T12 · [H01]
- **SENS.N047** SETTLED · `src/asy_isl29125_driver.py:98-99, 134-136, 262-263, 628-630` — "the driver
  only ever READS GainRatio, so nothing it does can write the flash (SPECIFICATION.md Part M.1.5)" / "A
  measured candidate is published as GainMeas for the user to copy across, never adopted." — Owner
  design: calibration is RAM-only and user-applied; contrasts with THIRD_PARTY_LICENSES.md's
  "FRAM-persisted gain-ratio self-calibration". · related: LIC.S02 · [H01]
- **SENS.N048** ASSUME · `src/asy_isl29125_driver.py:100-104` — "_CAL_CONVERGE_TOL = const(0.01) # 1%:
  one bench scene measured 28.11/28.01/28.09, a 0.4% spread" — Convergence/stability tolerances and the
  120 s window ("~100 attempts at 16 bit") rest on one bench measurement. · related: SENS.T01 · [H01]
- **SENS.N049** LIMIT · `SPECIFICATION.md:6785-6805 (M.1.6, read for :137/:158)` — "no single value is
  right everywhere ... calibrate at the level you care about ... do not re-raise it as actionable" — One
  GainRatio cannot correct the level-dependent ratio (~28 → ~22); SETTLED as not actionable. · [H01]
  ⟨anchor out of bounds⟩
- **SENS.N050** RISK · `src/asy_isl29125_driver.py:107-108, 614-617` — "a stream of concurrent config
  writes can extend the settle but can never starve the read loop" / "Past the bound the reading stands
  - a possibly-stale sample beats a starved read loop, and the leaky bucket catches a persistent problem
  anyway" — Accepted: after 2 rounds a possibly mid-reconfiguration sample is published. · related:
  SENS.T04, SENS.S27 · [H01]
- **SENS.N051** SETTLED · `src/asy_isl29125_driver.py:126-128, 790-793` — "The down point is DERIVED
  from it ... a second field could only ever be used to get it wrong." / "Against the NOMINAL 26.67, not
  GainRatio - the factor 2 absorbs that field's whole [20, 34] band." — Hysteresis design decision. ·
  related: SENS.S15 · [H01]
- **SENS.N052** INVAR · `src/asy_isl29125_driver.py:138-141, 899-900` — "Excluded from get_dict_cfg()'s
  schema argument and from the bool batch below: the key is never in ConfigManager's _cache, so either
  would fail at runtime rather than at type-check time." — Command-only field must be kept out of two
  call sites by hand. · related: CORE.T03 · [H01]
- **SENS.N053** ASSUME · `src/asy_isl29125_driver.py:150` — "16 bit integrates for 101 ms, an exact
  multiple of both the 50 Hz and 60 Hz mains period, so it rejects lighting flicker" — UI text: 101 ms
  is not an exact multiple of 20 ms or 16.7 ms (100 ms is) (low). · related: SENS.T01 · [H01]
- **SENS.N054** MIRROR · `src/asy_isl29125_driver.py:153, 158, 159, 183` — "1/53.3 of it" / "Nominally
  26.667" / "for up to two minutes" / "held for ten minutes" — Hand-written @web UI texts duplicate
  `_AR_DOWN_DIVISOR`, `_GAIN_RATIO_NOMINAL`, `_CAL_WINDOW_MS`, `_CAL_HOLD_MS`. · related: GEN.T06 ·
  [H01]
- **SENS.N055** LIMIT · `src/asy_isl29125_driver.py:180` — "CCT ... Relative and uncalibrated - a
  documented placeholder RGB->XYZ matrix, so repeatable and monotonic rather than a colorimeter reading"
  — CCT is a placeholder approximation. · related: ALGO.T01 · [H01]
- **SENS.N056** SETTLED · `src/asy_isl29125_driver.py:182, 250-252` — "It used to be wrnno=12; a
  harmless, transient, always-current status belongs in the measurement output, not the error log
  (C.7.1)." — wrnno 12 retired, never reused (C.7.1 row SPECIFICATION.md:1933). · related: XCUT.T07 ·
  [H01]
- **SENS.N057** MIRROR · `src/asy_isl29125_driver.py:162-165, 172-184, 880-896` — "_FIELDS =
  const((...)) # kept in sync with ISL29125's own fields above" — `_FIELDS` is never used in this
  module; the wire keys come from the hand-written nested dict in `get_dict_data()` and the `@web ... path="RGB.R"`
  tags — the sync guard (`tests_scripts/test_measurement_field_tuple_agreement.py`) does not cover what
  reaches the wire here. · related: SENS.T08 · [H01]
- **SENS.N058** INVAR · `src/asy_isl29125_driver.py:166-170` — "Narrow on purpose: _error_check() counts
  a failed read when ANY element is None, and CCT is legitimately None in a dark room." — ISLResults
  shape is coupled to `_error_check()`'s any-None rule. · related: SENS.T03 · [H01]
- **SENS.N059** MIRROR · `src/asy_isl29125_driver.py:191-194` — "bounds kept in sync with
  _MIN/_MAX_TRIGGER_SECS by hand" / "0x44 is hard-wired (p15), so this driver has no TOML `address`
  field at all" — Tag↔const sync by hand. · related: GEN.T06 · [H01]
- **SENS.N060** PLATFORM · `src/asy_isl29125_driver.py:226-229` — "This INT is open-drain (p6), so the
  high level needs a resistor somewhere ... irq_pull_up=True enables the internal one" — Relies on
  RP2040 internal pull-up adequacy for the INT line (per board TOML). · related: SENS.T05 · [H01]
- **SENS.N061** SETTLED · `src/asy_isl29125_driver.py:282-284` — "ISLCalibrate is command-only, so
  _recover_failed_push() skips it by design." — Recovery chain covers only the four hardware-backed
  fields. · related: XCUT.T11 · [H01]
- **SENS.N062** SUPPRESS · `src/asy_isl29125_driver.py:297-299, 316, 339-341` — err_s "Error in initial
  setup:" errno=10 / "Error reading config data!" errno=12 / "Error setting config data:" errno=13 —
  Init failures swallowed, loop returns False. · related: SENS.T14 · [H01]
- **SENS.N063** DRIFT · `src/asy_isl29125_driver.py:305-306` — "it is not optional: step 9 below cannot
  decide whether to arm the thresholds without it" — No numbered "step 9" exists in the code or
  SPECIFICATION (low). · related: DOC.T16 · [H01]
- **SENS.N064** INVAR · `src/asy_isl29125_driver.py:319-320` — "set_trigger_secs() never raises (logs
  errno=25, keeps the previous value)" — ISL's set_trigger_secs also calls `_reapply_persist` (errno 24)
  after updating the period. · [H01]
- **SENS.N065** ASSUME · `src/asy_isl29125_driver.py:377-384` — "captured after the settle wait ... and
  before the first await that can yield. p13: a later push cannot change what is read, only this." —
  Correct scaling of a sample assumes data registers are unaffected by a CONFIG1 write landing between
  capture and `read_counts()`. · related: SENS.T04 · [H01]
- **SENS.N066** SUPPRESS · `src/asy_isl29125_driver.py:389-393` — "except Exception as e: #
  distinguishable from a data-read failure, and not re-raised" err_s "Status read failed:" errno=31 —
  Status read failure → all-None sample. · related: SENS.T15 · [H01]
- **SENS.N067** LIMIT · `src/asy_isl29125_driver.py:398-404` — "there is no sample to report this cycle"
  — A brownout cycle returns all-None, which `_error_check` counts as a failed read. · related: SENS.T03
  · [H01]
- **SENS.N068** LIMIT · `src/asy_isl29125_driver.py:407-409` — err_s "All-ones data with an implausible
  status byte, confirmed by a failed device-ID re-read" errno=32 — Bus-fault heuristic path. · [H01]
- **SENS.N069** SUPPRESS · `src/asy_isl29125_driver.py:428-430` — err_s "Read failed:" errno=11 — Any
  read exception swallowed. · [H01]
- **SENS.N070** SUPPRESS · `src/asy_isl29125_driver.py:436-439` — "except Exception: return False" —
  Device-ID re-read failure swallowed silently (no log). · [H01]
- **SENS.N071** ASSUME · `src/asy_isl29125_driver.py:443-455` — "persist_for_interval() always leaves
  the chip time to raise RGBTHF first, so five periodic-only decisions running means the line is not
  delivering them" + wrn_s "Range decided by the periodic path only - the interrupt may be dead."
  wrnno=13 — Dead-INT detector's inference; interacts with the INT-storm case. · related: SENS.S15,
  SENS.T05 · [H01]
- **SENS.N072** LIMIT · `src/asy_isl29125_driver.py:466-476` — wrn_s "Brownout detected - re-applying
  the whole configuration." wrnno=10 (transition only) / err_s errno=33 — Brownout recovery path; relies
  on BOUTF clearing on status read (M.1.2). · related: SENS.T03 · [H01]
- **SENS.N073** SUPPRESS · `src/asy_isl29125_driver.py:488-491` — "except Exception: return # the bus is
  down; the counts still differ, so the next cycle tries again" — Reconciliation read failure swallowed
  silently. · [H01]
- **SENS.N074** DRIFT · `src/asy_isl29125_driver.py:500` — "FiltCoeff ALONE, matching spec R5" — No "R5"
  exists in SPECIFICATION.md (BACKLOG.md:35's R5 is a bench queue row) (low). · related: DOC.T16 · [H01]
- **SENS.N075** LIMIT · `src/asy_isl29125_driver.py:503-506` — "cfg_values = [-1.0]" + err_s "Error
  reading config data!" errno=14 — Degraded: sample published with filter off on config read failure. ·
  covered-by: SENS.S25 · [H01]
- **SENS.N076** ASSUME · `src/asy_isl29125_driver.py:529` — "Lux=lux[0], # green alone: its response
  approximates the CIE Y curve (p14, Figure 13)" — Lux is an approximation from the green channel. ·
  related: SENS.T01 · [H01]
- **SENS.N077** SETTLED · `src/asy_isl29125_driver.py:546-547` — "A dark room is NOT a fault: below the
  floor ... None is the correct, expected output" — CCT None below floor, logged at `all` only. · [H01]
- **SENS.N078** LIMIT · `src/asy_isl29125_driver.py:570-572` — "the hardware path is green-only because
  INTSEL has one channel ... Peak-up with green-down oscillates" — Decision on peak of three channels vs
  green-only INT. · covered-by: SENS.S15 · [H01]
- **SENS.N079** LIMIT · `src/asy_isl29125_driver.py:575-576, 584-588` — "return None # a conversion
  restarted by the last switch has not completed yet" / "ticks_diff, never subtraction" — Range
  evaluation gated by stored-ticks deadlines (`_settle_until_ms`, `_last_switch_ms`). · covered-by:
  SENS.S27 · [H01]
- **SENS.N080** SETTLED · `src/asy_isl29125_driver.py:595-596, 605-609` — "thresholds FIRST" /
  "_active_range is deliberately NOT updated, so the next cycle re-evaluates and retries the whole
  switch - idempotent" — err_s errno 29/30 retry design. · [H01]
- **SENS.N081** RISK · `src/asy_isl29125_driver.py:646-648` — "The third leg runs even when the second
  failed, because it is also what puts the range BACK" — Calibration legs switch the chip range inside
  the read loop (stall + extra writes). · related: SENS.S17 · [H01]
- **SENS.N082** SUPPRESS · `src/asy_isl29125_driver.py:676-678` — err_s "Paired gain-ratio reading
  failed:" errno=35 — Calibration leg failure swallowed. · [H01]
- **SENS.N083** ASSUME · `src/asy_isl29125_driver.py:705-706` — "None once the hold expires, so a stale
  candidate can never be mistaken for a fresh one." — Contradicted after a ticks wrap (stored deadline).
  · covered-by: SENS.S27 · [H01]
- **SENS.N084** LIMIT · `src/asy_isl29125_driver.py:716-728, 745-755` — "a read-only snapshot costs one
  transaction and creates no read-modify-write hazard" + wrn_s "Chip configuration diverged from the
  shadow - re-applying." wrnno=11 / errno 28, 34 — A REST GET can trigger chip writes and persisted log
  entries via `_check_divergence`. · covered-by: SENS.S24 · [H01]
- **SENS.N085** SETTLED · `src/asy_isl29125_driver.py:738-742` — "Under auto-range the chip's RNG bit is
  the state machine's choice, not the user's setting" — Range omitted from the live config read under
  auto-range. · [H01]
- **SENS.N086** SUPPRESS · `src/asy_isl29125_driver.py:757-765` — err_s "Error reading", what
  errno=15/17/19/21 — Getter failures swallowed to None. · related: XCUT.T11 · [H01]
- **SENS.N087** MIRROR · `src/asy_isl29125_driver.py:768-774` — "Part G.2's numeric primitive ... the
  same narrow-then-validate shape asy_webserver_service.py's _put_notification() applies" — Validation
  shape shared with the webserver by convention; message "- out of range:" also used for type errors
  (low). · related: XCUT.T15 · [H01]
- **SENS.N088** SUPPRESS · `src/asy_isl29125_driver.py:783-787` — err_s "Error applying the derived
  transient rejection:" errno=24 — Persist reapply failure swallowed to False. · [H01]
- **SENS.N089** SETTLED · `src/asy_isl29125_driver.py:828-835` — "Reports success unconditionally once
  the type check passes ... returning False would run _recover_failed_push() on a command-only field
  that cannot be recovered (Part C.5.2.1)" — ISLCalibrate push always "Valid" (also for False, a no-op).
  · related: XCUT.T11 · [H01]
- **SENS.N090** LIMIT · `src/asy_isl29125_driver.py:854-856` — "alarm-pool exhaustion (ENOMEM) -
  degrades gracefully ... (this sensor just never gets triggered this cycle)" — Print-only; IRQ still
  armed afterwards so INT remains the only trigger path. · related: XCUT.T04 · [H01]
- **SENS.N091** RISK · `src/asy_isl29125_driver.py:857-859` — "A line held low by a fault produces
  exactly one edge and then silence - which is what the periodic path and wrnno=13 exist for, not a
  flood." — Accepted fault behaviour of the FALLING-edge IRQ. · related: SENS.T05 · [H01]
- **SENS.N092** SUPPRESS · `src/asy_isl29125_driver.py:878` — "# type: ignore[return-value]" —
  get_data() narrowing. · related: SENS.T08 · [H01]
- **SENS.N093** SUPPRESS · `src/asy_isl29125_driver.py:936, 956, 974, 1001, 1009` — err_s "Error setting
  resolution:" 16 / "range:" 18 / "Error applying the auto-range mode:" 38 / IR offset 20 / IR adjust 22
  — Setter hardware failures swallowed to False. · [H01]
- **SENS.N094** PLATFORM · `src/asy_isl29125_driver.py:942-945, 1162-1164` — "The threshold registers
  are compared against the RAW ADC value, so they are scaled to the resolution that was active when they
  were written" — Resolution change must re-arm thresholds (done only when RangeAuto). · related:
  SENS.S16 · [H01]
- **SENS.N095** PLATFORM · `src/asy_isl29125_driver.py:962-964` — "the part fires on \"below OR EQUAL
  TO\", so 0x0000 still interrupts in total darkness" — Datasheet comparison semantics behind INTSEL=00
  disarm. · related: SENS.S15 · [H01]
- **SENS.N096** LIMIT · `src/asy_isl29125_driver.py:981-988` — "The down point follows automatically -
  it is computed from this value, not stored" — Only the cached value changes; chip threshold registers
  keep the old values until the next switch. · covered-by: SENS.S16 · [H01]
- **SENS.N097** SETTLED · `src/asy_isl29125_driver.py:1032` — "flag=False is deliberately a no-op,
  matching SGP40_Reader.reset_voc()'s own contract." — Cross-driver command convention (MIRROR). ·
  related: SENS.T08 · [H01]
- **SENS.N098** INVAR · `src/asy_isl29125_driver.py:1060-1062, 1129-1131` — "Holds a SHADOW of all three
  config bytes and never reads them back to modify them" / "The caller already holds both the
  device-session and bus locks, so this takes none of its own on purpose" — Shadow-write discipline and
  lock precondition by convention. · related: BUS.T03 · [H01]
- **SENS.N099** DRIFT · `src/asy_isl29125_driver.py:1065-1066` — "the parameter exists only for test
  injection, exactly as BMP3XX_I2C's does" — BMP3XX's address is a real 0x76/0x77 choice
  (`src/asy_bmp3xx_driver.py:118-119`), not test-only (low). · [H01]
- **SENS.N100** WORKAROUND · `src/asy_isl29125_driver.py:1107` — "Register order is GREEN, RED, BLUE
  (p9, Table 1) - p13's Table 20 mislabels its own rows." — Datasheet defect worked around; removal
  trigger: none (datasheet). · related: SENS.T01 · [H01]
- **SENS.N101** SUPPRESS · `src/asy_isl29125_driver.py:1114-1115` — "except (TypeError, ValueError):
  return None" — Burst decode failure → None → OSError at :1393. · [H01]
- **SENS.N102** PLATFORM · `src/asy_isl29125_driver.py:1216-1219` — "p1 gives 375/65535 = 5.72 mlux and
  10000/65535 = 0.1526 lux per LSB" / "gain_correction is validated where an untrusted ratio ENTERS ...
  never here" — Lux scaling source + no hot-path gate. · related: SENS.T01 · [H01]
- **SENS.N103** ASSUME · `src/asy_isl29125_driver.py:1239-1241` — "A dead bus reads all-ones, which is
  exactly what this part's community failure reports show." — Bus-fault heuristic rests on community
  reports. · [H01]
- **SENS.N104** LIMIT · `src/asy_isl29125_driver.py:1258-1263` — "An unknown resolution falls back to
  \"no shift\", the conservative direction" — Fallback under-reports; dark offset subtracted after the
  12-bit shift. · covered-by: SENS.S17 · [H01]
- **SENS.N105** SETTLED · `src/asy_isl29125_driver.py:1269` — "An unreadable length answers True - a
  failed read is not evidence of divergence." — (low). · [H01]
- **SENS.N106** ASSUME · `src/asy_isl29125_driver.py:1280-1290` — "Unreachable at the current schema
  bounds - one 16-bit cycle is 303ms against a minimum 1s interval - but this is the honest degradation
  if either bound ever moves" — PRST derivation coupled to schema minimum and typical cycle length (Part
  M.1.4). · related: SENS.T05 · [H01]
- **SENS.N107** SUPPRESS · `src/asy_isl29125_driver.py:1302-1305` — "except ValueError: prst = 0" —
  Invalid shadow persist silently encoded as PRST 1 (no log). · [H01]
- **SENS.N108** SETTLED · `src/asy_isl29125_driver.py:1337-1339` — "Validate-mutate-write(-rollback)
  runs under ONE hold of the device-session lock, not just the final write (Part C.8)." — Lock-scope
  decision. · related: BUS.T03 · [H01]
- **SENS.N109** INVAR · `src/asy_isl29125_driver.py:1372-1378` — "The shadow must never claim a value
  the part did not take ... Rolled back inside the lock, so it is never observable." — Rollback
  invariant; partial burst handled by `_verify_after_failed_write`. · related: SENS.T03 · [H01]
- **SENS.N110** RISK · `src/asy_isl29125_driver.py:1380-1383` — "Outside the lock on purpose: timing
  bookkeeping, not the shadow-vs-chip consistency it protects." — Settle deadline set after lock release
  (brief window where a reader sees no settle pending) (low). · related: SENS.S27 · [H01]
- **SENS.N111** INVAR · `src/asy_isl29125_driver.py:1386-1388` — "\"6s\", NOT \"<HHH\":
  get_register_struct() returns unpacked[0] only ... fails silently" — Format discipline; a wrong format
  fails silently. · related: BUS.T01 · [H01]
- **SENS.N112** INVAR · `src/asy_isl29125_driver.py:1397-1399, 1430-1432` — "DESTRUCTIVE: the read
  clears RGBTHF and releases the INT pin ... nothing else in this driver may read 0x08 \"just to
  check\"" — One-read-per-cycle invariant by convention (also constrains `reset()`). · related: SENS.T05
  · [H01]
- **SENS.N113** WORKAROUND · `src/asy_isl29125_driver.py:1410-1411` — "Table 15 marks 0x08 \"RO\", but
  p12's own BOUTF text requires an I2C write to clear it - the marking is a datasheet defect" —
  Datasheet defect; removal trigger: none. · [H01]
- **SENS.N114** ASSUME · `src/asy_isl29125_driver.py:1420-1422` — "Kept even though the 0x46 reset and
  any status read both clear it on real silicon (Part M.1.2)" — Real-silicon behaviour measured on one
  board (2026-09-12/13). · related: HW.T07 · [H01]
- **SENS.N115** ASSUME · `src/asy_isl29125_driver.py:1430-1432` — "The datasheet specifies no post-reset
  settle, so the verify read IS the settle." — No explicit settle after reset command. · related:
  SENS.T01 · [H01]

## src/asy_scd30_driver.py

- **SENS.N116** SUPPRESS · `src/asy_scd30_driver.py:26-32` — "def cast(_typ: object, val: \"T\") ->
  \"T\": # type: ignore[no-redef] # no-op at runtime either way" — ImportError fallback defines a
  runtime `cast` shim under a type-ignore. · [H01]
- **SENS.N117** MIRROR · `src/asy_scd30_driver.py:72-81` — "Same datasheet limits the _VAL_* schema
  entries above carry, named for the driver's own argument validation (Interface Description sections
  1.4.1-1.4.6)." — Bounds duplicated between `_VAL_*` schemas (:57-61) and
  `_MEAS_INTERVAL_*`/`_AMB_PRESSURE_*`/... consts by hand. · related: SENS.T02, GEN.T06 · [H01]
- **SENS.N118** SETTLED · `src/asy_scd30_driver.py:86-89` — "Deliberately no _VAL_* entry for
  \"ContMeas\": the SCD30 cannot report whether continuous measurement is running" — ContMeas is
  write-only; the UI toggle's `defaultValue=true` does not reflect the chip state. · related: SENS.T09 ·
  [H01]
- **SENS.N119** MIRROR · `src/asy_scd30_driver.py:95` — "_FIELDS = const((...)) # kept in sync with
  SCD30's own fields above" — Enforced by `tests_scripts/test_measurement_field_tuple_agreement.py`. ·
  [H01]
- **SENS.N120** PLATFORM · `src/asy_scd30_driver.py:105-108` — "clock stretching is normally <=30ms but
  reaches 150ms once a day for internal calibration, past rp2's own 50ms I2C default ... @requires
  bus.timeout>=200000" — Datasheet + rp2 default fact; enforced by buildgen `@requires`; a 150 ms
  stretch blocks the loop inside one I2C call. · related: BUS.T10, SENS.T17 · [H01]
- **SENS.N121** ASSUME · `src/asy_scd30_driver.py:109-111` — "\"Maximal I2C speed is 100 kHz\" -
  Sensirion recommends 50 kHz or less, which every device TOML uses today." — Dated claim about all
  device TOMLs; only the 100 kHz max is enforced (`@requires bus.frequency<=100000`), not the 50 kHz
  recommendation. · related: SENS.T17, GEN.T08 · [H01]
- **SENS.N122** INVAR · `src/asy_scd30_driver.py:159` — "only ever invoked as get_dict_cfg()'s callback,
  which already wraps this call in its own try/except" — Snapshot failure handled by base errno 4. ·
  related: SENS.S18 · [H01]
- **SENS.N123** LIMIT · `src/asy_scd30_driver.py:162-163, 546-554` — "Continuous measurement isn't
  (re)started here" — A sensor with continuous measurement off (factory-fresh, or after a ContMeas=Off
  PUT) publishes nothing until a user PUTs AmbPres. · related: SENS.T14, SENS.T09 · [H01]
- **SENS.N124** SUPPRESS · `src/asy_scd30_driver.py:166-170, 184-186` — err_s "Error in initial setup:"
  errno=10 / "Read failed:" errno=11 — Setup/read exceptions swallowed. · [H01]
- **SENS.N125** INVAR · `src/asy_scd30_driver.py:178, 524-525, 596-598` — "read_measurement() must run
  exactly once per cycle, before the getters below." / "these getters must never re-check data-ready" —
  Call-order discipline around the destructive data-ready read. · related: SENS.T04 · [H01]
- **SENS.N126** LIMIT · `src/asy_scd30_driver.py:219-221` — "alarm-pool exhaustion (ENOMEM) - degrades
  gracefully ... (this sensor just never gets triggered this cycle)" — Print-only; the RDY IRQ is still
  armed (:222-225) so reads continue only via the pin. · related: XCUT.T04 · [H01]
- **SENS.N127** SUPPRESS · `src/asy_scd30_driver.py:238` — "# type: ignore[return-value]" — get_data()
  narrowing. · related: SENS.T08 · [H01]
- **SENS.N128** INVAR · `src/asy_scd30_driver.py:251-255` — "_put_sensors() calls that uniformly on
  every registered sensor, and without this every PUT /sensors touching SCD30 raised a 500" — Duck-typed
  interface SCD30 must provide by hand (not inherited). · related: SENS.T08, XCUT.T11 · [H01]
- **SENS.N129** LIMIT · `src/asy_scd30_driver.py:260-262, 297` — "with no persistence step: each
  validated field calls straight through to its own setter, a real I2C write" — Every PUT field is an
  NVM write, unconditional (no compare with read-back). · covered-by: PAR.S02 · [H01]
- **SENS.N130** SETTLED · `src/asy_scd30_driver.py:280-284, 426-428` —
  "stop_continuous_measurement(value=True) is a pure no-op whose contract returns False meaning
  \"nothing to do\"" — ContMeas=True reports "Valid" but cannot restart measurement. · related: SENS.T09
  · [H01]
- **SENS.N131** SUPPRESS · `src/asy_scd30_driver.py:303-343` — err_s "Error reading measurement
  interval:"/"self calibration enabled:"/"ambient pressure:"/"altitude:"/"temperature offset:"/"forced
  recalibration reference:" errno=14/16/18/20/22/24 — Reader-level getters swallow to None; none has a
  production caller in `src/`/`buildgen/` (SCD30 is not a SensorReaderConfig) (low). · related: SENS.T08
  · [H01]
- **SENS.N132** SUPPRESS · `src/asy_scd30_driver.py:345-397` — err_s "Error setting measurement
  interval:"... errno=15/17/19/21/23/25 — Setter failures swallowed to False ("Failed" on the wire). ·
  [H01]
- **SENS.N133** LIMIT · `src/asy_scd30_driver.py:411-420` — "Trigger the CO2 sensor IRQ if it isn't
  running (pin stays HIGH if not read!)" / "# consecutive intervals seen (500ms rate)" — Counter
  accumulates across cycles, not consecutive; forced read re-stamps cached values. · covered-by:
  SENS.S08 · [H01]
- **SENS.N134** SETTLED · `src/asy_scd30_driver.py:422-424` — "each failure is logged via self.pr (not
  swallowed silently) so a transient bus fault on a REST-triggered config get/set stays visible in the
  sensor's own error history" — Client-triggered I2C faults deliberately persisted in the fault history.
  · related: CORE.S11, SEC.T09 · [H01]
- **SENS.N135** INVAR · `src/asy_scd30_driver.py:438` — "lock for consecutive i2c communication and
  self._buffer" — 18-byte shared buffer protected only by the device-session lock. · related: BUS.T02 ·
  [H01]
- **SENS.N136** PLATFORM · `src/asy_scd30_driver.py:471, 481-483` — "await asyncio.sleep(0.05) # delay
  for response" / "the SCD30 has no repeated-start ... the delay clears the datasheet's >3ms minimum
  (Interface Description 1.4.4)" — 50 ms waits inside the bus lock per command/read. · covered-by:
  SENS.S11 · [H01]
- **SENS.N137** ASSUME · `src/asy_scd30_driver.py:495-496` — "return await
  self._read_register(_CMD_CONTINUOUS_MEASUREMENT)" — AmbPres read-back via the set/trigger command word
  is undocumented (A.4 note, SPECIFICATION.md:283-285). · covered-by: SENS.T09 · [H01]
- **SENS.N138** PLATFORM · `src/asy_scd30_driver.py:506-507` — "Volatile readback: always returns 400
  after a power cycle regardless of the last FRC value applied - the calibration curve update itself is
  permanent" — FRC read-back semantics; relevant to any "unchanged" comparison and to repeated
  recalibration. · related: PAR.S02, SENS.T13 · [H01]
- **SENS.N139** PLATFORM · `src/asy_scd30_driver.py:535, 541, 547-548, 557, 564` — "NVM-persisted -
  survives reset() and power cycles." / "0x0010 doubles as \"trigger continuous measurement\" and is
  NVM-persisted (Interface Description 1.4.1)" — NVM endurance applies to each setter. · covered-by:
  SENS.T07 · [H01]
- **SENS.N140** LIMIT · `src/asy_scd30_driver.py:568-570` — "temperature_offset must be from 0 to 655.35
  degrees Celsius" / "int(offset * 100)" — Truncation (float32 effect) and message unit "degrees
  Celsius" for a K offset (low). · covered-by: SENS.S09 · [H01]
- **SENS.N141** LIMIT · `src/asy_scd30_driver.py:580-582` — "CRC-valid firmware-version read confirms a
  real SCD30 is responding ... - the version value itself isn't checked." — Weak identity check (any
  CRC-valid word passes). · related: SENS.T09 · [H01]
- **SENS.N142** PLATFORM · `src/asy_scd30_driver.py:585-589` — "Boot-up is documented as <2s (Interface
  Description 1.1); wait the full bound since this also runs on every failure-triggered restart" — Soft
  reset + 2.5 s sleep on every setup (incl. supervisor restarts). · covered-by: SENS.S22 · [H01]
- **SENS.N143** SETTLED · `src/asy_scd30_driver.py:624-627` — "CRC-valid NaN/inf still decode;
  MicroPython's json.dumps() would ship them as bare nan/inf, breaking the whole page (Part F.1). A
  failed read instead." — Only finiteness is checked, no plausibility range. · covered-by: XCUT.T23,
  SENS.S10 · [H01]

## src/asy_sgp40_driver.py

- **SENS.N144** PLATFORM · `src/asy_sgp40_driver.py:7` — "Verified against Sensirion's SGP40 datasheet
  (datasheets/sgp40/, v1.2 - Feb 2022)." — Sensirion VOC algorithm reference is not in `datasheets/`. ·
  related: SENS.S20 · [H01]
- **SENS.N145** ASSUME · `src/asy_sgp40_driver.py:44-46` — "roughly the time how often the data written
  to the FRAM is verified. less a data safety feature here but rather a check if communication and
  integrity is generally okay" — Verify period derivation (used at :353, :410) is approximate. ·
  covered-by: SENS.S02 · [H01]
- **SENS.N146** PLATFORM · `src/asy_sgp40_driver.py:47, 356-359` — "_MAX_NTP_WAITTIME = const(600) #
  600s = 10min" — NTP wait clamp; restore retries each second meanwhile. · related: SENS.S05, PAR.S01 ·
  [H01]
- **SENS.N147** ASSUME · `src/asy_sgp40_driver.py:48, 225-227` — "_BACKUP_COUNTER_MAX = const(100000) #
  see _check_storage()'s own note on the 86400s = 1 day margin" / "counts seconds, resets at 86400 = 1
  day, give it some more space" — Counter counts read cycles (ticks), not seconds; the "1 day" note does
  not match the 100000 reset. · related: SENS.T11 · [H01]
- **SENS.N148** PLATFORM · `src/asy_sgp40_driver.py:49, 690-693` — "_SELF_TEST_PASS = const(0xD4) #
  datasheet Table 13, high byte only (the low byte is \"ignore\")" — Self-test check on high byte only.
  · related: SENS.T13 · [H01]
- **SENS.N149** INVAR · `src/asy_sgp40_driver.py:56-59, 499-502` — "Deliberately excluded from
  get_dict_cfg()'s own schema argument below - this key is never in ConfigManager's _cache." —
  Command-only field kept out of get_dict_cfg by hand (else the whole read breaks). · related: CORE.T03
  · [H01]
- **SENS.N150** MIRROR · `src/asy_sgp40_driver.py:71-72` — "_FIELDS = const((\"VOC\", \"Raw\", \"TS\"))
  # kept in sync with SGP40's own fields above" — Enforced by
  `tests_scripts/test_measurement_field_tuple_agreement.py`. · [H01]
- **SENS.N151** DRIFT · `src/asy_sgp40_driver.py:79-81, 140-141` — "fram_target maps to this driver's
  own fram_storage= kwarg, for historical reasons - buildgen/buildspec.py" — Naming divergence from Part
  C kept for history. · covered-by: SENS.S18 · [H01]
- **SENS.N152** PLATFORM · `src/asy_sgp40_driver.py:87-90` — "Table 3: fSCL max 400 kHz ... a bus shared
  with an SCD30 is additionally held to that sensor's stricter 100 kHz tag." — `@requires bus.frequency<=400000`
  enforced by buildgen. · related: SENS.T17 · [H01]
- **SENS.N153** SETTLED · `src/asy_sgp40_driver.py:93-97` — "Both are required, so an SGP40 with no
  compensation data at all has to opt in explicitly through a `_Default*`." — Wiring design (L.6.3). ·
  related: SENS.T12 · [H01]
- **SENS.N154** ASSUME · `src/asy_sgp40_driver.py:107-108, 119-120` — "25 degC is not an arbitrary pick:
  it matches SGP40_I2C.measure_raw()'s own datasheet-documented default (Table 9)" — `_Default*`
  constants mirror `measure_raw` defaults (MIRROR by hand). · related: SENS.T12 · [H01]
- **SENS.N155** INVAR · `src/asy_sgp40_driver.py:112-113` — "Every `_Default*` provider returns an
  object exposing exactly one attribute named \"value\" (a fixed contract)" — buildgen relies on the
  "value" attribute name. · related: GEN.T06 · [H01]
- **SENS.N156** SETTLED · `src/asy_sgp40_driver.py:157-159` — "registered the same way as every other
  module's real live-push field (project decision ...)" — SGPResetVOC via _push_callbacks, never
  persisted. · [H01]
- **SENS.N157** SUPPRESS · `src/asy_sgp40_driver.py:178-187` — "broad on purpose, matching
  print_log.py's own FRAM-allocation guard" `except Exception: self.ts_storage = None` + pr.err "FRAM
  backup storage allocation failed!" — Allocation failure print-only; SGP40 silently runs without
  backup. · covered-by: STOR.S08 · [H01]
- **SENS.N158** LIMIT · `src/asy_sgp40_driver.py:204-207` — err_s "Error reading config data!" errno=13
  — Persisted every 1 s cycle while config read fails. · covered-by: SENS.T15 · [H01]
- **SENS.N159** INVAR · `src/asy_sgp40_driver.py:239-241` — "Snapshotted once at entry so a concurrent
  reset_voc(flag=True) ... only ever affects the *next* cycle" — Reset bookkeeping across cycles. ·
  related: SENS.T03 · [H01]
- **SENS.N160** LIMIT · `src/asy_sgp40_driver.py:251-254` — err_s "Error clearing FRAM!" errno=15 —
  Reset stays pending until clear succeeds (retried each cycle, persisted each time). · related:
  SENS.T15 · [H01]
- **SENS.N161** ASSUME · `src/asy_sgp40_driver.py:256-262` — "get_data() never raises, but the named
  field can be None" — Compensation inputs rely on producers' never-raise contract; values unclamped. ·
  related: SENS.T12, SENS.S03 · [H01]
- **SENS.N162** SUPPRESS · `src/asy_sgp40_driver.py:265-270` — err_s "Compensation data read failed:"
  errno=18 — Producer exception swallowed. · [H01]
- **SENS.N163** SETTLED · `src/asy_sgp40_driver.py:275-280` — "retry init if triggered and no
  compensation data is available" — No VOC read without compensation data (A.4 confirmed-intentional,
  SPECIFICATION.md:276-279). · related: PAR.T03 · [H01]
- **SENS.N164** INVAR · `src/asy_sgp40_driver.py:284-288, 321-324` — "vocalgorithm_reset() never raises,
  so this half is guaranteed applied regardless of I2C outcome below" — Reset split relies on
  voc_algorithm's never-raise. · related: ALGO.T02 · [H01]
- **SENS.N165** SUPPRESS · `src/asy_sgp40_driver.py:295-297, 321-327` — "a non-numeric field from a
  caller-supplied source raises here like a genuine I2C fault and is caught below (errno=11)" err_s
  "Read failed:" — Non-numeric compensation input counted as a read failure. · [H01]
- **SENS.N166** LIMIT · `src/asy_sgp40_driver.py:313, 319` — err_s "Error deserializing!" errno=16 /
  "Error serializing!" errno=17 — Backup restore/serialize failures. · [H01]
- **SENS.N167** SUPPRESS · `src/asy_sgp40_driver.py:338-340, 348` — err_s "Error in initial setup:"
  errno=10 / "Error reading config data!" errno=12 — Init failures swallowed. · [H01]
- **SENS.N168** LIMIT · `src/asy_sgp40_driver.py:351-354, 408-412` — "int(math.ceil((10 *
  _FRAM_VERIFY_MINS) / cfg_values[0]) * 0.1)" — Verify period is 0 (disabled) for BackupPeriod 67-1440,
  off by one elsewhere. · covered-by: SENS.S02 · [H01]
- **SENS.N169** LIMIT · `src/asy_sgp40_driver.py:373-392` — wrn_s "No backup found!" wrnno=10 / "Backup
  loaded without timestamp" 11 / "Backup is too old" 12 — Restore paths; re-reads the chunk each second
  while waiting for NTP; negative ages pass. · covered-by: SENS.S05, STOR.T09 · [H01]
- **SENS.N170** LIMIT · `src/asy_sgp40_driver.py:421-446` — "set backup counter to retry serialization
  in self._read_sgp()" / err_s "Write error during backup!" errno=14 / wrn_s "Backup written without
  timestamp." wrnno=13 — voc_write reset to WaitTimeNTP after each stamped write (each later backup
  waits for NTP again). · covered-by: PAR.S03 · [H01]
- **SENS.N171** SETTLED · `src/asy_sgp40_driver.py:455-461, 507-510` — "Deliberately does NOT forward
  reset_voc()'s own return value ... always reports success once typed" / "flag=False deliberately does
  nothing (see test_reset_voc_false_is_a_no_op's own contract note)" — Command contract (mirrors ISL
  start_calibration). · related: XCUT.T11 · [H01]
- **SENS.N172** LIMIT · `src/asy_sgp40_driver.py:467-476` — "# voc algorithm needs 1s period fixed" /
  "alarm-pool exhaustion (ENOMEM) - degrades gracefully ... (this sensor just never gets triggered this
  cycle)" — 1 Hz from a soft PERIODIC timer (ticks merge in stalls); arm failure print-only and SGP40
  then never reads. · covered-by: SENS.T11 · [H01]
- **SENS.N173** SUPPRESS · `src/asy_sgp40_driver.py:492` — "# type: ignore[return-value]" — get_data()
  narrowing. · related: SENS.T08 · [H01]
- **SENS.N174** INVAR · `src/asy_sgp40_driver.py:536, 610-616` — "lock for consecutive i2c communication
  and self._command_buffer" / "self._command_buffer = self._measure_command" — Buffer aliasing restored
  without try/finally; a failed read leaves the alias. · covered-by: SENS.S01 · [H01]
- **SENS.N175** ASSUME · `src/asy_sgp40_driver.py:547-550, 568-570` — "Sized for the only readlen
  actually used anywhere in this file (readlen=1, 3 bytes/word)" — Serial read fetches 1 of 3 words. ·
  covered-by: SENS.S21 · [H01]
- **SENS.N176** RISK · `src/asy_sgp40_driver.py:586-593` — "True I2C general-call reset (datasheet Table
  17): 0x06 to the reserved address 0x00, broadcast to every device on the bus. A NAK (OSError) is
  expected, not a failure." — General-call reset hits every device sharing the bus; OSError swallowed
  (`except OSError: pass`) plus a 1 s sleep. · related: SENS.T10 · [H01]
- **SENS.N177** LIMIT · `src/asy_sgp40_driver.py:597-608` — "Temperature-to-ticks, datasheet Table 10
  ..." / "& 0xFFFF" — Out-of-range T/RH wrap instead of clamping. · covered-by: SENS.S03 · [H01]
- **SENS.N178** PLATFORM · `src/asy_sgp40_driver.py:614-615` — "100ms: >3x margin over the datasheet's
  30ms typ/max measurement duration (Table 8)" — Wait cost vs datasheet. · covered-by: SENS.S07 · [H01]
- **SENS.N179** PLATFORM · `src/asy_sgp40_driver.py:645-647` — "VOC index (1-500 ...). 100 = average of
  the last 24h" — Index range claim; 0 published during blackout. · covered-by: SENS.S04 · [H01] ⟨quote
  not matched at the anchor⟩
- **SENS.N180** ASSUME · `src/asy_sgp40_driver.py:678-682` — "word[0]==0 isn't documented by Sensirion
  ... unverified, inherited from Adafruit; kept since it's observed working on deployed hardware." —
  Undocumented serial-number assumption. · covered-by: SENS.S06 · [H01]

## src/math_helpers.py

- **SENS.N181** LIMIT · `src/math_helpers.py:164-165` — "No gamma decode - this sensor is linear in
  irradiance. A documented PLACEHOLDER: p13 Eq. 1 says the coefficients are per-setup." — ISL29125
  RGB→XYZ matrix is an uncalibrated placeholder per the datasheet · related: ALGO.T01 · [H02]
- **SENS.N182** MIRROR · `src/math_helpers.py:177-179` — "The low-light POLICY floor is a device fact
  and lives in the driver, in counts." — Split of responsibility with `asy_isl29125_driver.py` · [H02]

## tests/_bus_hazard_catalog.py

- **SENS.N183** PLATFORM · `tests/_bus_hazard_catalog.py:102,108-112` — "0x44 matches ISL29125_I2C's own
  hard-wired default address (FN8424 p15" — seeded chip facts: ISL29125 addr 0x44, device ID 0x7D
  (FN8424 p9); BMP chip ID seeded as 0x50 (BMP388 only, BMP390 not seeded) · [H03]
- **SENS.N184** ASSUME · `tests/_bus_hazard_catalog.py:281-282` — "Volatile config register
  (datasheet-confirmed, see test_bus_hazard_multi_device.py's own ... comment)" — BMP oversampling write
  assumed volatile (no NVM budget) · [H03]

## tests/test_asy_bmp3xx_driver.py

- **SENS.N185** PLATFORM · `tests/test_asy_bmp3xx_driver.py:24,232-233` — "BMP384 reports 0x50, the same
  as BMP388" — chip-ID fact from `bst-bmp384-ds003.pdf`; BMP390 = 0x60 · related: SENS.S20 · [H03]
- **SENS.N186** PLATFORM · `tests/test_asy_bmp3xx_driver.py:264-266` — "a stuck bus (SDA/SCL
  disconnected) or a corrupted read commonly reads back as all-0x00 or all-0xFF instead, per Bosch's own
  self-test app note" — calibration-validity heuristic rests on an app-note claim · related: SENS.T01 ·
  [H03]
- **SENS.N187** LIMIT · `tests/test_asy_bmp3xx_driver.py:299-301` — "Neither optional setup() parameter
  is exercised by any ... real caller in this codebase" — unused public API kept (frozen) · related:
  CORE.T10 · [H03]
- **SENS.N188** LIMIT · `tests/test_asy_bmp3xx_driver.py:353-355` — "The message then reads as a
  hardware timeout, but the poll does terminate within its bound" — a deinitialized bus produces a
  misleading "timeout" error message · related: BUS.T06 · [H03]
- **SENS.N189** SETTLED · `tests/test_asy_bmp3xx_driver.py:429-443` — "Documents the standalone
  get_pressure()/get_temperature() behavior as intentional" — each standalone getter triggers its own
  conversion (~129 ms apart when called back to back); only the combined getter is used in production ·
  covered-by: SENS.S14 · [H03]
- **SENS.N190** PLATFORM · `tests/test_asy_bmp3xx_driver.py:558,572` — "far above the 1250 hPa datasheet
  ceiling" / "past the -40 degC floor" — operating-range plausibility gate bounds from the datasheet ·
  related: SENS.S12, SENS.S13 · [H03]
- **SENS.N191** LIMIT · `tests/test_asy_bmp3xx_driver.py:584-585` — "get_altitude() - never called by
  BMP3xx_Reader today (dead from its perspective), but live, reachable public API" — tested-only API ·
  covered-by: SENS.S14 · [H03]
- **SENS.N192** PLATFORM · `tests/test_asy_bmp3xx_driver.py:710-712,794-796,1537-1539` — "the corrected
  2^index-1 encoding (0,1,3,7,15,31,63,127)" / "osr_p only documents 3-bit encodings 0-5; 6/7 are
  reserved" — datasheet encodings (sec 4.3.17) the driver depends on · related: SENS.T01 · [H03]
- **SENS.N193** SETTLED · `tests/test_asy_bmp3xx_driver.py:936-938` — "a stale stored interval should
  log and keep going, not fail init and force a task restart" — `_init_bmp()` routes BMPSampleInterv
  through the never-raising setter · [H03]
- **SENS.N194** INVAR · `tests/test_asy_bmp3xx_driver.py:1290-1291` — "15/17/19 are what /status reports
  and what a bench session reads back, and a shared or copy-pasted errno would make the three
  indistinguishable" — maintenance-status errno values are a published contract · related: XCUT.T07 ·
  [H03]
- **SENS.N195** RISK · `tests/test_asy_bmp3xx_driver.py:1347-1349` — "logs, substitutes the documented
  [0.0, 0.0, 0.0, 15.0] fallback and stores an uncompensated read" — on a config read failure the reader
  publishes an uncompensated sample · covered-by: SENS.S25 · [H03]
- **SENS.N196** LIMIT · `tests/test_asy_bmp3xx_driver.py:1746-1748` — "exercises the defensive branch a
  real caller can't actually reach" — push-wrapper type guards are unreachable from `_set_dict_cfg` ·
  [H03]

## tests/test_asy_isl29125_driver.py

- **SENS.N197** PLATFORM ·
  `tests/test_asy_isl29125_driver.py:193,237,259-260,364-365,388,433-434,498-499,647,835-836,2094-2095`
  — "Register order is GREEN, RED, BLUE (p9, Table 1); p13's Table 20 mislabels its own rows." — FN8424
  datasheet facts the driver rests on: channel order (and a datasheet erratum), DDark only at range 0,
  5.7 mlux/0.152 lux per LSB, status bit layout, reserved bits "can change without any notice",
  SYNC/CONVEN effects, tINT 101 ms, open-drain INT, low threshold fires on "below OR EQUAL" · related:
  SENS.T01 · [H03]
- **SENS.N198** NOTE(PAR) · `tests/test_asy_isl29125_driver.py:281-283,520-522` — "RIOT's own
  `(uint16_t)(65535 / max_range)` ... truncates - 6.55 becomes 6, a 9% error" / "SparkFun's reset() also
  requires STATUS == 0x00, which contradicts Table 15's documented 0x04 default" — deliberate
  divergences from reference implementations · [H03]
- **SENS.N199** PLATFORM · `tests/test_asy_isl29125_driver.py:634-636` — "the ADC restarts during the
  I2C write itself (p10, Table 7) while the driver arms its deadline once that write has RETURNED" —
  reason for the fixed two-cycle settle · [H03]
- **SENS.N200** RISK · `tests/test_asy_isl29125_driver.py:1292-1293` — "A possibly-stale sample beats a
  starved read loop, and the leaky bucket catches a persistent problem anyway." — bounded settle wait
  may publish a stale sample, accepted · related: SENS.S27, XCUT.T17 · [H03]
- **SENS.N201** SETTLED · `tests/test_asy_isl29125_driver.py:1224-1233` — "Overrange belongs in the
  measurement output, not the log (BACKLOG.md)" — retired W12 warning replaced by the `Overrange` field
  (still never run on silicon per REAL_HARDWARE_TEST_QUEUE R9) · [H03]
- **SENS.N202** SETTLED · `tests/test_asy_isl29125_driver.py:1598-1599` — "One increment, deliberately:
  the driver genuinely has no sample that cycle. That is the intended cost of a recovered brownout" —
  brownout costs one error-streak increment · [H03]
- **SENS.N203** ASSUME · `tests/test_asy_isl29125_driver.py:1838-1840` — "The fallback the reader cannot
  reach - _MIN_TRIGGER_SECS is 1s against a 303ms cycle ... Asserted so a bound change surfaces as a
  decision" — PRST fallback unreachable under current bounds · [H03]
- **SENS.N204** INVAR · `tests/test_asy_isl29125_driver.py:1848-1850,1876-1878` — "asyncio can run a
  REST handler at any of a cycle's awaits, so a Resolution PUT can land between the status read and the
  data read" — per-sample state must be captured before any await (range/mode travel with the sample) ·
  related: XCUT.T19 · [H03]
- **SENS.N205** PLATFORM · `tests/test_asy_isl29125_driver.py:1877-1878` — "p13's double buffering means
  what comes back is still the OLD config's conversion" — datasheet behaviour behind sample-scoped
  scaling · [H03]
- **SENS.N206** LIMIT · `tests/test_asy_isl29125_driver.py:1961-1963` — "A NAK partway through the burst
  leaves the chip a mixture, so normalise() scales by the old resolution while the part runs the new
  one." — partial-write inconsistency window before divergence detection · related: SENS.S24 · [H03]
- **SENS.N207** INVAR · `tests/test_asy_isl29125_driver.py:1176-1177,3184-3186` — "the read is
  destructive (it clears RGBTHF and releases the INT pin), so a second reader would silently consume
  another consumer's interrupt state" — exactly one status read per cycle; no second consumer of 0x08 ·
  [H03]
- **SENS.N208** INVAR · `tests/test_asy_isl29125_driver.py:2005-2007,3122-3123` — "35, not 11: the
  periodic read owns 11 (SPECIFICATION.md C.7.1)" — distinct errnos are a diagnostic contract · related:
  XCUT.T07 · [H03]
- **SENS.N209** SETTLED · `tests/test_asy_isl29125_driver.py:2850-2852` — "The divisor is 2x the part's
  NOMINAL 26.67, not the measured GainRatio. Deliberate" — derived down point decoupled from calibration
  · related: SENS.S15 · [H03]
- **SENS.N210** ASSUME · `tests/test_asy_isl29125_driver.py:152,2879-2881,2898-2900,2910-2912` —
  "Defence in depth (SPECIFICATION.md Part E.4)" — several guards are unreachable in production and are
  tested only by writing state directly · [H03]
- **SENS.N211** INVAR · `tests/test_asy_isl29125_driver.py:2576-2578` — "a failed init returns False
  WITHOUT entering the loop. Getting this wrong parks the task forever on read_event.wait()" —
  supervisor visibility depends on read_loop returning · related: XCUT.T02 · [H03]
- **SENS.N212** MIRROR · `tests/test_asy_isl29125_driver.py:3095-3097` — "the REST body is a
  hand-written override (the measurement group is nested), so a field can exist on the namedtuple and
  still never reach the API. That is exactly what happened" — `get_dict_data()` must be kept in sync
  with the ISLResults namedtuple by hand · [H03]
- **SENS.N213** RISK · `tests/test_asy_isl29125_driver.py:3215-3224` — "Regression for the real-hardware
  divergence finding in BACKLOG.md" — the shadow-before-lock fix is confirmed on silicon only partly
  (REAL_HARDWARE_TEST_QUEUE R9 open) · [H03]

## tests/test_asy_scd30_driver.py

- **SENS.N214** ASSUME · `tests/test_asy_scd30_driver.py:126-128,173-174` — "hardcoded bytes from the
  PDF, not this file's crc8_byte() helper" — wire-format tests are anchored to the Interface
  Description's worked examples (sections 1.4.1-1.4.10); the oracle is the datasheet transcription
  itself · related: SENS.T01 · [H04]
- **SENS.N215** SETTLED · `tests/test_asy_scd30_driver.py:282-287` — "set_ambient_pressure(-0.5) sent a
  real \"disable ambient pressure\" command to the sensor with no error raised" — validate-before-int()
  truncation rule (AmbPres and Altitude, :313-315) pinned by regression tests; `int()` truncates toward
  zero so (-1,0) would alias the 0 sentinel · [H04]
- **SENS.N216** INVAR · `tests/test_asy_scd30_driver.py:295-297,332` — "NaN compares False against every
  bound in the range check ... without an explicit check it would silently reach int(pressure_mbar)" —
  range guards need an explicit NaN check; a plain bounds comparison passes NaN · related: XCUT.T23 ·
  [H04]
- **SENS.N217** INVAR · `tests/test_asy_scd30_driver.py:348-350,364` — "the shared self._buffer must not
  be left in a state that corrupts a subsequent, unrelated, valid command" — invalid arguments must
  raise before any `_send_command`/buffer mutation; convention in src pinned by test · [H04]
- **SENS.N218** LIMIT · `tests/test_asy_scd30_driver.py:435-436` — "_read_scd()'s blanket except logs
  errno=11 and _store_scd() discards the all-None result" — non-finite measurement is handled by a
  blanket except (errno 11) rather than a dedicated path · related: SENS.S10 · [H04]
- **SENS.N219** SETTLED · `tests/test_asy_scd30_driver.py:455-457` — "Reverted from an earlier \"clear
  to None\" version per project-owner direction; see BACKLOG.md." — not-ready read leaves the cache
  untouched (legacy-proven behaviour), owner decision · related: SENS.S08 · [H04]
- **SENS.N220** INVAR · `tests/test_asy_scd30_driver.py:482-488,499-500,1216-1218` — "the SCD30's
  data-ready flag clears the instant the measurement is read" — the three getters must stay pure cache
  reads and never re-check data-ready; earlier fake queued three "ready" replies, which hid the bug
  (fake-fidelity lesson) · [H04]
- **SENS.N221** SETTLED · `tests/test_asy_scd30_driver.py:524-525` — "SCD30_I2C is the documented
  \"allowed to raise\" layer (SPECIFICATION.md Part D.2's raw-bus-call carve-out)" — raw OSError
  propagates uncaught from the chip layer by design; Reader must absorb it · [H04]
- **SENS.N222** LIMIT · `tests/test_asy_scd30_driver.py:677-679` — "this failure prints but is
  deliberately never recorded as a numbered error in the counter" — a failed SCD30 timer arm logs via
  non-counting sync `pr.err()`, so it leaves no persisted evidence · related: XCUT.T04 · [H04]
- **SENS.N223** ASSUME · `tests/test_asy_scd30_driver.py:682-684` — "that IRQ, not the timer, is what
  actually triggers a measurement read (the timer only drives scd_init_irq()'s stuck-pin watchdog)" —
  pin IRQ is wired after the guarded timer arm so a failed arm keeps the data-ready interrupt · related:
  SENS.T05 · [H04]
- **SENS.N224** LIMIT · `tests/test_asy_scd30_driver.py:951-955` — "Never caught by any prior test,
  since nothing exercised _set_dict_cfg's ContMeas branch specifically." — ContMeas=True no-op used to
  be reported "Failed"; records a past coverage hole in the dispatch branch · - (low) · [H04]
- **SENS.N225** INVAR · `tests/test_asy_scd30_driver.py:1144-1146` — "get_config_snapshot() now holds
  the device-session lock for the whole batch" — atomic six-register snapshot relies on holding the lock
  across all reads (costing ≥6×50 ms on the bus) · related: SENS.S11 · [H04]
- **SENS.N226** LIMIT · `tests/test_asy_scd30_driver.py:1395-1397` — "a real CRC8 object cannot fail
  add_into() through any command this driver sends" — `_send_dev_command()`'s CRC-generation guard is
  unreachable in practice and covered only through a fake CRC · - (low) · [H04]

## tests/test_asy_sgp40_driver.py

- **SENS.N227** LIMIT · `tests/test_asy_sgp40_driver.py:66-69` — "the 25 degC / 50 %RH themselves are a
  datasheet claim (Table 9) that nothing asserted at runtime" — buildgen-wired default compensation
  values were previously only pinned by class name (tests_scripts/test_buildgen_defaults.py); now
  asserted here · - (low) · [H04]
- **SENS.N228** SETTLED · `tests/test_asy_sgp40_driver.py:129,179` — "(feature-set check intentionally
  removed)" / "Regression test for the dropped, undocumented 0x20 0x2F check" — the SGP40 feature-set
  command was deliberately dropped from initialize(); pinned by test · related: SENS.T13 · [H04]
- **SENS.N229** ASSUME · `tests/test_asy_sgp40_driver.py:119,147` — "serial number (word[0] must be 0)"
  — fixture encodes the undocumented Adafruit serial-word assumption · covered-by: SENS.S06 · [H04]
- **SENS.N230** SETTLED · `tests/test_asy_sgp40_driver.py:168-170` — "datasheet Table 13 documents 0xD4
  0xXX as \"all tests passed, ignore 0xXX\"" — self-test check deliberately compares only the high byte,
  diverging from the deployed driver's full-word check · related: PAR.T01 (low) · [H04]
- **SENS.N231** RISK · `tests/test_asy_sgp40_driver.py:214-232` — "_reset() - true I2C general call (the
  confirmed datasheet-vs-code bug, now fixed)" / "not every device on the bus needs to support a general
  call" — SGP40 `_reset()` broadcasts a general call (0x00, 0x06) to the whole bus and tolerates a NAK;
  every general-call-listening sibling is reset too; the mock does not model any sibling reacting ·
  related: TWIN.S02 · [H04]
- **SENS.N232** SETTLED · `tests/test_asy_sgp40_driver.py:251-252` — "rounding gives 25840 (0x64F0) -
  matches _relative_humidity_to_ticks()'s own round-to-nearest convention" — ticks conversion rounds
  rather than truncates (differs from datasheet's integer example truncation) · related: SENS.S03 (low)
  · [H04]
- **SENS.N233** SETTLED · `tests/test_asy_sgp40_driver.py:407-413,434-436` — "a compensation source
  whose field is legitimately still None ... is startup jitter, not a fault, and must log no E/W entry
  at all" — None compensation data at boot is silent by design (Part C.14.2); missing comp data never
  counts as an SGP40 error (:1509-1511) · related: SENS.T12 · [H04]
- **SENS.N234** LIMIT · `tests/test_asy_sgp40_driver.py:562-564,570,581` — "start_timer() logs via the
  non-persisting pr.err(), not err_s()" — a failed SGP40 timer arm leaves no persisted log; if it raised
  instead, the sensor would never be triggered again · related: XCUT.T04 · [H04]
- **SENS.N235** SETTLED · `tests/test_asy_sgp40_driver.py:692-694` — "self.reset only clears once BOTH
  have succeeded ... neither part repeats once it succeeded" — VOC reset has two independently tracked
  sub-parts (FRAM clear, algorithm reset) · [H04]
- **SENS.N236** ASSUME · `tests/test_asy_sgp40_driver.py:833-835,857-859` — "Each source is
  caller-supplied and only structurally typed (Part C.14), so this can't be ruled out statically even
  though SCD30_Reader never raises" — compensation sources are duck-typed; robustness relies on
  _read_sgp()'s try blocks · - (low) · [H04]
- **SENS.N237** RISK · `tests/test_asy_sgp40_driver.py:917-919` — "the restore is applied anyway without
  checking BackupMaxAge - recovering a possibly-unverifiable-age baseline rather than losing it" — when
  NTP never syncs within WaitTimeNTP, an arbitrarily old VOC baseline is restored; accepted trade-off ·
  related: PAR.S01 · [H04]
- **SENS.N238** RISK · `tests/test_asy_sgp40_driver.py:971-973,1002` — "require_ntp becomes False and
  the backup is written even though NTP has not synced" — backups may be written with no timestamp (the
  "backup exists, no TS" sentinel) once the countdown expires · related: PAR.S03 · [H04]
- **SENS.N239** LIMIT · `tests/test_asy_sgp40_driver.py:1132-1134` — "The 100000 wraparound guard only
  matters when BackupPeriod is disabled (0) ... the guard is otherwise unreachable" — backup_counter
  wrap guard is reachable only with BackupPeriod=0 · - (low) · [H04]
- **SENS.N240** ASSUME · `tests/test_asy_sgp40_driver.py:1160-1162,1183` — "ceil((10 *
  _FRAM_VERIFY_MINS) / BackupPeriod) * 0.1 - roughly \"verify once per _FRAM_VERIFY_MINS (60min) worth
  of backups\"" — test pins the verify-period formula only at BackupPeriod=5 (=12); the formula's edge
  values are not checked · covered-by: SENS.S02 · [H04]
- **SENS.N241** INVAR · `tests/test_asy_sgp40_driver.py:1188-1190` — "both share the SAME buffer: the
  old state is read in, unpacked, advanced by one sample, re-packed, and written back out" — serialize
  and deserialize in one cycle share one buffer; ordering must be deserialize → process → serialize ·
  [H04]
- **SENS.N242** INVAR · `tests/test_asy_sgp40_driver.py:1211-1212` — "buf=None would instead persist a
  freshly-allocated, all-zero buffer" — a backup path passing buf=None writes an all-zero state; callers
  must thread the buffer · - (low) · [H04]
- **SENS.N243** SETTLED · `tests/test_asy_sgp40_driver.py:1892-1894` — "A raise here happens at
  construction time, before any supervisor exists, so it must degrade to None" — constructor wraps
  `get_timestamped_chunk()` despite AsyFramManager's never-raises contract (defence in depth) · related:
  XCUT.T20 · [H04]
- **SENS.N244** LIMIT · `tests/test_asy_sgp40_driver.py:2006-2008` — "reachable only via a stale value
  written before this bound existed" — WaitTimeNTP cap path only reachable via a pre-existing
  out-of-schema file · - (low) · [H04]
- **SENS.N245** LIMIT · `tests/test_asy_sgp40_driver.py:2261-2263` — "struct.unpack_from(\"32q\", ...)
  can never see a size mismatch through normal use - this fake is the only way" — too-small-backup
  branch (errno 16) is unreachable in production · - (low) · [H04]
- **SENS.N246** LIMIT · `tests/test_asy_sgp40_driver.py:2303-2305` — "reachable only by
  _read_word_from_command() returning None, which no real caller's readlen triggers" — "no sensor
  response" guards in four SGP40 methods are dead defensive code, covered only via a monkeypatch · -
  (low) · [H04]

## tests/test_base_classes.py

- **SENS.N247** SETTLED · `tests/test_base_classes.py:1135-1136` — "there are no generic force-resend
  semantics, SCD30's AmbPres being the only case that needed them and not using this path" — Push fires
  only on "Valid", never "Unchanged"; AmbPres is the single exception handled elsewhere · [H05]

## tests/test_bus_hazard_multi_device.py

- **SENS.N248** PLATFORM · `tests/test_bus_hazard_multi_device.py:66` — "hard-wired (FN8424 p15) -
  dev-only, sharing i2c1 with SCD30 and SGP40" — ISL29125 address is a datasheet fact (FN8424 p15) ·
  [H05]
- **SENS.N249** PLATFORM · `tests/test_bus_hazard_multi_device.py:282, 296` — "BMP3xx doesn't ack
  general calls (datasheet-confirmed)" — Datasheet claim that BMP3xx never ACKs a general call; the test
  swallows the resulting OSError · [H05]

## tests/test_crc_checks.py

- **SENS.N250** PLATFORM · `tests/test_crc_checks.py:27, 40` — "Table 10 of the SGP40 datasheet" /
  "0xBEEF -> 0x92 is Sensirion's other commonly-quoted worked example (e.g. SHT3x datasheet)" — CRC8
  test vectors come from datasheets; the SHT3x datasheet is not a chip this repo drives · [H05]

## tests/test_notification_scd30_integration.py

- **SENS.N251** INVAR · `tests/test_notification_scd30_integration.py:210-212` — "one faulted cycle logs
  twice (asy_scd30_driver.py's own _read_scd() catch, errno=11, then base_classes.py's generic
  _error_check() streak-counter increment, errno=1" — One fault produces two persisted entries per
  cycle; pins the double-logging shape · [H05]

## tests/test_setter_microdot_integration.py

- **SENS.N252** SETTLED · `tests/test_setter_microdot_integration.py:640-646` — "SGP40's whole setter
  surface is bus-independent" — No I2C in the SGP40 REST path; SGPResetVOC only arms RAM flags for
  read_loop() · [H05]
- **SENS.N253** ASSUME · `tests/test_setter_microdot_integration.py:695-697` — "Every SCD30 setter
  already returns bool and never raises (SPECIFICATION.md Part C)" — Contract assumption behind the
  plain bool mapping · [H05]
- **SENS.N254** PLATFORM · `tests/test_setter_microdot_integration.py:701, 817` — "special=0 matches
  SCD30's own documented AmbPres=0 "disable compensation" bypass value" — Datasheet fact · [H05]

## tests/test_voc_algorithm.py

- **SENS.N255** INVAR · `tests/test_voc_algorithm.py:445-446` — "asy_sgp40_driver.py's _run_restore()
  never calls unpack_from() at all once read_into() has failed" — Restore must short-circuit on a failed
  FRAM read · [H05]

## digital_twin/_scd30_chip.py

- **SENS.N256** PLATFORM · `digital_twin/_scd30_chip.py:193, :223` — "volatile readback always reports
  400 regardless (real hardware quirk)" — FRC readback quirk encoded in the fake · [H06]

## digital_twin/_isl29125_chip.py

- **SENS.N257** PLATFORM · `digital_twin/_isl29125_chip.py:27-64` — "`_DEVICE_ID = 0x7D # datasheet FN8424 Rev 3.00 p9, Table 2`"
  — Register map, masks and timings cite a specific datasheet revision · [H06]
- **SENS.N258** ASSUME · `digital_twin/_isl29125_chip.py:43-46` — "Reserved bits read back ZERO ...
  (measured on real silicon 2026-09-12: writing 0xFF reads back 3f/bf/1f)" — Single dated silicon
  measurement · [H06]
- **SENS.N259** PLATFORM · `digital_twin/_isl29125_chip.py:172` — "Register order is GREEN, RED, BLUE
  (p9, Table 1) - Table 20's own row labels are wrong." — Datasheet defect claim · [H06]
- **SENS.N260** PLATFORM · `digital_twin/_isl29125_chip.py:212-215` — "Measured on real silicon: 0x08
  reads 0x00 straight after the 0x46 reset" — Silicon-measured divergence from Table 15 (M.1.2) · [H06]
- **SENS.N261** PLATFORM · `digital_twin/_isl29125_chip.py:283-286` — "Table 15 marks 0x08 \"RO\", but
  p12's own BOUTF text requires an I2C write to clear it - the marking is a datasheet defect" —
  Datasheet-defect interpretation · [H06]
- **SENS.N262** PLATFORM · `digital_twin/_isl29125_chip.py:290-309` — "measured on real silicon, a
  16-byte read from 0x00 returns id, CONFIG1-3, both thresholds, status and all six data bytes" / "it
  does NOT roll over to 0x00" — Silicon-measured pointer behaviour · [H06]
- **SENS.N263** PLATFORM · `digital_twin/_isl29125_chip.py:310-320` — "The counter restarts when the
  flag is CLEARED, not on every status read (measured; Part M.1.2)" — Silicon-measured
  persistence-counter behaviour that the driver depends on · [H06]

## tests/test_digital_twin_bmp3xx.py

- **SENS.N264** PLATFORM · `tests/test_digital_twin_bmp3xx.py:161-162` — "asy_bmp3xx_driver.py's own
  _read() rejects anything outside 300-1250 hPa / -40-85 degC (datasheet sec 1, Table 2)" — Datasheet
  range the fake's defaults must stay inside · [H06]

## tests/test_digital_twin_isl29125.py

- **SENS.N265** PLATFORM · `tests/test_digital_twin_isl29125.py:122-131` — "measured on real silicon
  (2026-09-12) ... Measured 2026-09-13 on a just-powered board: 0x08 read 0x04, a second read 0x00 ...
  This CONTRADICTS p12" — Single dated silicon measurements encoded as test expectations · [H06]

## tests/test_digital_twin_scd30.py

- **SENS.N266** PLATFORM · `tests/test_digital_twin_scd30.py:107-109, :150` — "volatile readback always
  400 regardless of the last value applied" / "cleared the instant it was read (Interface Description
  1.4.4)" — Sensor-specific facts encoded in tests · [H06]
- **SENS.N267** PLATFORM · `tests/test_digital_twin_scd30.py:227-228` — "CO2 accuracy-guaranteed
  400-10'000ppm, humidity 0-100%RH, temperature -40-70 degC" — Datasheet ranges the defaults must sit
  inside · [H06]

## tests/test_digital_twin_sgp40.py

- **SENS.N268** ASSUME · `tests/test_digital_twin_sgp40.py:49-50` — "exact content is opaque to the real
  driver (only word[0] is checked)" — Claim about driver behaviour · [H06]

## tests_hardware/flash/test_bus_concurrency.py

- **SENS.N269** OPENQ · `tests_hardware/flash/test_bus_concurrency.py:96-98` — "the two datasheet
  questions no document answers - whether a CONFIG1 write restarts the conversion, and whether PRST
  counts RGB cycles or single-channel integrations ... neither gates the pass" — Open ISL29125 datasheet
  questions, measured and reported only. · [H07]

## tests_hardware/device_scripts/isl29125_real_irq_edge.py

- **SENS.N270** OPENQ · `tests_hardware/device_scripts/isl29125_real_irq_edge.py:2-3, 24-27, 44-47` —
  "the two questions no document answers - whether a CONFIG1 write restarts the conversion, and whether
  PRST counts cycles or integrations" — CONFIG1-restart result is reported only ("inconclusive"
  allowed); PRST unit is asserted. · [H07]
- **SENS.N271** INVAR · `tests_hardware/device_scripts/isl29125_real_irq_edge.py:117-121` —
  "persist_for_interval() compares PRST x a whole RGB CYCLE against the sample interval. If the part
  answered \"channel integrations\" ... nothing else would notice" — Driver derivation depends on a
  silicon fact only this script checks. · related: SENS.T01 · [H07]

## tests_hardware/device_scripts/isl29125_lighting_scenarios.py

- **SENS.N272** LIMIT · `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:201-205` — "that
  run lives in driver state (_periodic_only_switches) which reset_error_counter() does not touch - so it
  can span scenarios" — W13 dead-interrupt warning state outlives an error-counter reset in src. ·
  related: SENS.T03 · [H07]

## tests_hardware/device_scripts/isl29125_mechanism_envelope.py

- **SENS.N273** INVAR · `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:190-196` — "The
  applied ratio is config now and only a user PUT changes it"; "reader._gain_ratio == 10000 / 375" —
  Calibration must not move the applied ratio; checked via private fields. · [H07]

## tests_hardware/device_scripts/isl29125_mock_conformance_probe.py

- **SENS.N274** PLATFORM · `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:80-81, 98, 130-132`
  — "p12: BOUTF is cleared by an I2C write, despite Table 15's \"RO\""; "p6's burst text: ... rolls over
  and goes back to the first Register Address" — Datasheet-ambiguity points the fake must match. ·
  related: SENS.T01 · [H07]

## tests_hardware/README.md

- **SENS.N275** LIMIT · `tests_hardware/README.md:167-170` — "Absolute lux and CCT against a WS2812's
  three narrow emission lines are meaningless and are asserted nowhere" — Light tests assert only
  relative properties; absolute accuracy is manual-tier only. · [H08]
- **SENS.N276** ASSUME · `tests_hardware/README.md:191-200` — "The auto-range hysteresis band, measured
  covered at this geometry (2026-09-12)" — Single dated measurement; levels 2-8 inside the band cannot
  force a switch; "Re-measure if the rig or the cover changes". · [H08]
- **SENS.N277** ASSUME · `tests_hardware/README.md:204-216` — "Measured 2026-09-13, six forced crossings
  per setting" — PRST 4/2/1 table (1212/606/303 ms windows) is the basis for deriving the window (M.1.4)
  and reading `wrnno=13` as a dead INT line. · related: SENS.T05 · [H08]
- **SENS.N278** LIMIT · `tests_hardware/README.md:653-658` — "software alone can't fully distinguish a
  genuine hardware IRQ firing from the self-healing fallback" — SCD30 RDY real-edge test cannot prove
  the IRQ path without a scope. · related: SENS.T05 · [H08]
- **SENS.N279** SETTLED · `tests_hardware/README.md:1157-1170` — "There is currently no way to force
  this hazard on a live, already-running system via REST at all" — SGP40 general-call hazard has zero
  bench-tier coverage; recorded as structural exception. · related: HW.T09 · [H08]

## REAL_HARDWARE_TEST_QUEUE.md (snapshot only; being updated by another session)

- **SENS.N280** TODO · `REAL_HARDWARE_TEST_QUEUE.md:242` — "the connection ceiling is a second candidate
  with the same signature (BACKLOG 30), and the test's retry now hides it" — R1 OPEN: ISL29125
  connection reset (PUT+2 readers 6/18); first answer from Step 6's `CEILING_RETRIES`; else
  `RangeAuto=false` bisection. · [H08]
  ⟨4dc80ef: R1 closed 2026-09-25: BACKLOG 30 not reproduced (18/18 clean), item and row retired
  (79423dd)⟩
- **SENS.N281** TODO · `REAL_HARDWARE_TEST_QUEUE.md:247` — "the `Overrange` field that replaced `W12`
  has still never run" — R9 OPEN: ISL29125 shadow-divergence fix re-confirmation under real load +
  `Overrange` first run. · [H08]
  ⟨4dc80ef: R9 shadow half confirmed on silicon; Overrange half rides S3b (BACKLOG.md ISL29125 open
  question)⟩

## HARDWARE_TEST_HANDOVER.md (snapshot only; sitting IN PROGRESS in another session)

- **SENS.N282** LIMIT · `HARDWARE_TEST_HANDOVER.md:36` — "(no silicon trigger exists; it must simply
  stay quiet)" — SCD30 non-finite-word rejection cannot be exercised on silicon. · related: XCUT.T23 ·
  [H08]
  ⟨4dc80ef: section retired with the file (03f8bcf): open rows moved to BACKLOG.md "Real-hardware work
  still owed"; the traps live in tests_hardware/README.md, CLAUDE.md and SPECIFICATION.md⟩
- **SENS.N283** RISK · `HARDWARE_TEST_HANDOVER.md:163-166` — "9 slots after one hotspot episode, so the
  ring loses what preceded the outage" — SGP40 `W13` persists once per backup minute without NTP;
  candidate for BACKLOG 50 / C.7.1 per-episode rule. · related: SENS.T15 · [H08]
  ⟨4dc80ef: F18 owner decision open: open in BACKLOG.md "Real-hardware work still owed" (F18)⟩

## dev_legacy/README.md

- **SENS.N284** PLATFORM · `dev_legacy/README.md:77-80` — "one grace-period reading completing roughly
  1s after the stop command ... (not documented by Sensirion" — SCD30 undocumented behaviour: data-ready
  after stop; IRQ-sync resync within ~3 s (2026-08-28). · related: SENS.T05 · [H08]
- **SENS.N285** RISK · `dev_legacy/README.md:649-651` — "**SCD30 temperature offset is still 1.5°C** ...
  NVM-persisted, so it survives a power cycle" — Non-default SCD30 NVM state on the bench (dated
  2026-09-02); tests may assume defaults. · related: HW.T03, HW.S03 · [H08]

## dev_legacy/*.py (reference-only 2026-08-27 on-device snapshot, MicroPython 1.24.1 — plan §2.2; field/bench behaviour only)

- **SENS.N286** PLATFORM · `dev_legacy/asy_scd30_driver.py:180` — "CO2 Sensor IRQ triggern falls es
  nicht läuft (Pin bleibt HIGH wenn nicht gelesen!)" — Legacy field knowledge: SCD30 RDY stays high
  until the data is read, which is why a timer fallback starts reads when the edge was missed (:183-190,
  "meas rate 500ms"). · related: SENS.T05 · [H08]
- **SENS.N287** PLATFORM · `dev_legacy/asy_scd30_driver.py:306-309` — "not mentioned by datasheet, but
  required to avoid IO error" — Legacy SCD30 soft reset needs a 0.2 s settle beyond the datasheet. ·
  [H08]
- **SENS.N288** PLATFORM · `dev_legacy/asy_scd30_driver.py:319-320, 329-330, 349-350, 358-360` — "This
  value will be saved and will not be reset on boot or by calling `reset`." — SCD30 measurement
  interval, ASC, altitude and temperature offset persist in sensor NVM — the state bench scripts can
  leave behind. · related: HW.T03, HW.S03 · [H08]
- **SENS.N289** PLATFORM · `dev_legacy/asy_scd30_driver.py:417-420` — "separate readinto because the
  SCD30 wants an i2c stop before the read (non-repeated start)" — Protocol fact with a min 3 ms delay
  before the read. · - (low) · [H08]
- **SENS.N290** PLATFORM · `dev_legacy/asy_sgp40_driver.py:400-408` — "This is a general call Reset.
  Several sensors may see this and it doesn't appear to ACK before resetting" — Legacy SGP40 reset is an
  I2C general call whose `OSError` is expected and swallowed — the bus-hazard source the tier tests. ·
  related: HW.T09 · [H08]

## scripts/_digital_twin_ci_suite.py

- **SENS.N291** ASSUME · `scripts/_digital_twin_ci_suite.py:901-903` — "a read racing SCD30's cold start
  used to log a spurious E18/W14 pair (Part C.14.2, fixed 2026-09-12). Now only a settle window" — A
  settle wait remains for a fixed race. (low) · [H09]

## buildgen/buildspec.py

- **SENS.N292** PLATFORM · `buildgen/buildspec.py:29-31` — "0x44 is hard-wired (no address-select pin,
  datasheet p15) ... the INT line is open-drain (p6)" — ISL29125 datasheet facts behind the schema. ·
  [H09]
- **SENS.N293** PLATFORM · `buildgen/buildspec.py:61-63` — "BMP388/390: SDO pin selects 0x76/0x77" —
  Only bmp3xx is address-capable; datasheet fact. · [H09]

## devices/dev.toml

- **SENS.N294** SETTLED · `devices/dev.toml:100-101` — "irq_pull_up = false: the board carries its own
  external pull-up on GPIO6" — Bench-board hardware fact. · [H09]

## pyproject.toml

- **SENS.N295** SUPPRESS · `pyproject.toml:248-252` — "The `_push_*` dispatch family takes the
  config-VALUE union, where bool is a JSON value" — src/asy_bmp3xx_driver.py, src/asy_scd30_driver.py:
  FBT001; src/asy_wifi_service.py: S106 (accepted hotspot password), FBT001. · [H09]

## tests_scripts/buildgen_fixtures/multi_instance.toml

- **SENS.N296** PLATFORM · `tests_scripts/buildgen_fixtures/multi_instance.toml:6-8` — "sgp40 has no
  address-select pin, so the two instances must sit on different buses - a real hardware constraint" —
  Datasheet fact (SGP40 fixed address) the fixture shape depends on · [H10]

## tests_scripts/buildgen_fixtures/novel_combo.toml

- **SENS.N297** PLATFORM · `tests_scripts/buildgen_fixtures/novel_combo.toml:10-11` — "BMP3xx at the
  alternate hardwired-address-select value (0x76, every real device uses 0x77)" — Chip address fact and
  a claim about all real devices · [H10]

## tests_scripts/test_buildgen_limits.py

- **SENS.N298** PLATFORM · `tests_scripts/test_buildgen_limits.py:196-197` — "0x44 is hard-wired with no
  address-select pin at all" — ISL29125 fixed I2C address fact · [H10]

## tests_scripts/test_buildgen_requires_tag.py

- **SENS.N299** ASSUME · `tests_scripts/test_buildgen_requires_tag.py:174-175` — "each traced to its own
  datasheet citation in the driver file itself" — Datasheet provenance of the bus limits is asserted in
  comments, not checked · related: SENS.T17 · [H10]

## tests_scripts/test_buildgen_schema_ast.py

- **SENS.N300** ASSUME · `tests_scripts/test_buildgen_schema_ast.py:156-157` — "ContMeas is deliberately
  freestanding (no _VAL_* constant at all" — Pinned: SCD30 ContMeas has no schema; AmbPres schema =
  ("int", None, 700, 1400, 0) · [H10]

## tests_scripts/test_buildgen_validate.py

- **SENS.N301** PLATFORM · `tests_scripts/test_buildgen_validate.py:1051-1053,1061-1063,1071` —
  "Interface Description p.2's hard datasheet maximum ... an over-clocked SCD30 bus built cleanly and
  only misbehaved on real hardware" — SCD30 100 kHz and SGP40 400 kHz (Table 3) bus limits; shared bus
  held to the stricter tag · related: SENS.T17 · [H10]

## tests_scripts/test_buildgen_web_tag.py

- **SENS.N302** LIMIT · `tests_scripts/test_buildgen_web_tag.py:477-479` — "each of these three fields
  has a documented \"0 means X\" meaning despite an ordinary (special=None) schema tuple" — SGP40
  BackupPeriod/BackupMaxAge/WaitTimeNTP "0 means" semantics live only in the @web tag, not in the schema
  (the "real generator-behavior finding" Part L flags) · related: PAR.S01 · [H10]

## tests_scripts/test_measurement_field_tuple_agreement.py

- **SENS.N303** SETTLED · `tests_scripts/test_measurement_field_tuple_agreement.py:5-7` — "It stays
  deliberately: mypy's namedtuple plugin infers field names only from a literal at the call site" —
  Hand-duplicated `_FIELDS` + NamedTuple in seven src/ modules is a deliberate choice · [H10]
- **SENS.N304** MIRROR · `tests_scripts/test_measurement_field_tuple_agreement.py:9-11,60-75` — "Drift
  here is silent and reaches the wire" — `_FIELDS` (make_dict → /measurements keys) must equal the
  module's measurement NamedTuple; guard passes if `_FIELDS` equals ANY public NamedTuple in the module,
  and only literal-tuple declarations are recognised (floor >= 7 modules) · [H10]

## html/definitions/dev.json

- **SENS.N305** LIMIT · `html/definitions/dev.json:194` — "Relative and uncalibrated - a documented
  placeholder RGB->XYZ matrix, so repeatable and monotonic rather than a colorimeter reading." —
  ISL29125 CCT is a stated approximation surfaced to users · [H11]
- **SENS.N306** ASSUME · `html/definitions/dev.json:583` — "The switch-back-down point is derived from
  this - 1/53.3 of it" — user-facing text encodes a driver constant (hysteresis ratio); MIRROR with
  src/asy_isl29125_driver.py · [H11]
- **SENS.N307** ASSUME · `html/definitions/dev.json:648` — "Nominally 26.667; every real part differs,
  and the error shows as a step at each range change." — user-facing text encodes the nominal 375/10000
  lx range ratio (low) · [H11]
- **SENS.N308** ASSUME · `html/definitions/dev.json:209` — "Not an error - a transient, harmless,
  always-current status." — Overrange declared harmless (low) · [H11]
- **SENS.N309** LIMIT · `html/definitions/dev.json:548` — "12 bit is ~16x faster and rejects none." —
  12-bit resolution rejects no mains flicker, stated limitation (low) · [H11]

## tests_js/live-backend-put-matrix.test.js

- **SENS.N310** PLATFORM · `tests_js/live-backend-put-matrix.test.js:185-187` — "SCD30's TempOffs has a
  real 0.01° hardware truncation (SPECIFICATION.md, near the ForceCalRef/AmbPres notes)" — probe values
  rounded to 2 dp because of a chip resolution fact (SPECIFICATION.md:243); vague pointer · [H11]

## tests_js/mock-server.test.js

- **SENS.N311** MIRROR · `tests_js/mock-server.test.js:325-327` — "this readback always reports 400,
  never whatever was just applied." — stronger than src/asy_scd30_driver.py:506's "always returns 400
  after a power cycle"; mock and live matrix (ALWAYS_REMOUNTS_AS) both assume always-400 (low) · [H11]

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)

- **SENS.N312** SETTLED · `SPECIFICATION.md:237-240` — "SCD30's `AmbPres` is stored in the sensor's own
  NVM ... hence a static config value even on wozi ... Confirmed deliberate by the project owner." —
  Owner-confirmed; `force=True` resend doubles as resume-measurement command. · related: SENS.T09 ·
  [H12]
- **SENS.N313** SETTLED · `SPECIFICATION.md:241-242` — "SCD30's `ForceCalRef` recalibration is manual
  ... No automation planned." — No FRC automation. · related: SENS.T13 · [H12]
- **SENS.N314** LIMIT · `SPECIFICATION.md:243-245` — "`set_temperature_offset()` sends `int(offset * 100)`
  — a genuine truncation ... silently truncated by the chip, not rejected" — Silent truncation; text
  attributes it to "the chip" though `int()` in the driver truncates. · covered-by: SENS.S09 · [H12]
- **SENS.N315** ASSUME · `SPECIFICATION.md:283-285` — "`get_ambient_pressure()` reuses the same command
  word used to *set* it ... even though neither Sensirion reference driver documents that command as
  readable" — Undocumented readback relied on (legacy-proven). · covered-by: SENS.T09 · [H12]

## SPECIFICATION.md Part A.6 (Datasheets, 337-356)

- **SENS.N316** SETTLED · `SPECIFICATION.md:354-356` — "BMP390 ... The project owner has confirmed the
  whole family shares the same register map/protocol ... a documentation gap only" — Owner-confirmed
  assumption covering the missing BMP390 PDF. · covered-by: SENS.S20 · [H12]

## SPECIFICATION.md Part C intro, C.1-C.2 (1475-1535)

- **SENS.N317** INVAR · `SPECIFICATION.md:1517-1519` — "`_NAME`'s string and the namedtuple's type-name
  string must be identical, always" — Holds today for SCD30/SGP40/BMP3XX/ISL29125 by convention; no test
  named. · related: SENS.T08 · [H12]
- **SENS.N318** MIRROR · `SPECIFICATION.md:1524-1531` — "`<Sensor>_DeviceSession(Lockable)` — pure
  boilerplate, identical in all three drivers ... Copy verbatim" — Copied boilerplate across drivers
  (four now incl. ISL29125). · related: DOC.S08 · [H12]
- **SENS.N319** INVAR · `SPECIFICATION.md:1532-1536` — "`*_Reader` constructor order (match exactly):
  bus handle, ... `max_module_error: int = 5`, `name_ext: str = \"\"` ... `debug: int — None = None`" |
  Constructor-shape convention (divergences seeded). · covered-by: SENS.S18 · [H12]

## SPECIFICATION.md Part C.3 (Layer 2 protocol class, 1537-1566)

- **SENS.N320** DRIFT · `SPECIFICATION.md:1545-1547` — "A class built entirely on
  `I2CDevice.get_register_struct()`/`get_bits()` (`BMP3XX_I2C`) has no scratch buffer at all" — Stale
  per seed. · covered-by: SENS.S19 · [H12]
- **SENS.N321** INVAR · `SPECIFICATION.md:1552-1555` — "Contract: raises on any real failure — the layer
  that does not return sentinels." — Layer-2 contract. · related: BUS.T01 · [H12]
- **SENS.N322** INVAR · `SPECIFICATION.md:1561-1563` — "`setup()` verifies identity ... and raises if
  the sensor doesn't respond — fails loudly once at boot rather than degrading silently forever" —
  Identity-check obligation. · related: SENS.S06 · [H12]
- **SENS.N323** INVAR · `SPECIFICATION.md:1568-1569` — "Compensation/calibration math and datasheet
  operating-range checks live here — reject and raise rather than return an implausible value silently."
  — SCD30 lacks a range gate per seed. · related: SENS.S10 · [H12]

## SPECIFICATION.md Part C.4 (Layer 3 Reader, 1624-1697)

- **SENS.N324** INVAR · `SPECIFICATION.md:1630-1632` — "Contract: never raises. ... Every layer-2 call
  is wrapped in its own `try/except Exception` ... (never bare `except:`)" — Layer-3 never-raise
  contract. · related: BUS.T01 · [H12]
- **SENS.N325** SUPPRESS · `SPECIFICATION.md:1673-1676` — "identity return + scoped `# type: ignore[return-value]`
  ... the settled convention over a local `cast()` shim" — Settled suppression; sites
  `src/asy_bmp3xx_driver.py:310`, `asy_isl29125_driver.py:878`, `asy_notification_service.py:251`,
  `asy_ntp_client.py:365`, `asy_scd30_driver.py:238`, `asy_sgp40_driver.py:492`,
  `asy_wifi_service.py:684`. · [H12]
- **SENS.N326** DRIFT · `SPECIFICATION.md:1676-1677, 2314` — "`typing.cast()` still applies to narrowing
  a `struct.unpack()` result" / "`typing.cast()` has no runtime presence (C.4.2)" — SCD30 defines its
  own runtime no-op `cast()` shim (`src/asy_scd30_driver.py:27-31`), the shape C.4.2 calls the
  non-settled option. (low) · [H12]
- **SENS.N327** ASSUME · `SPECIFICATION.md:1698-1699` — "(BMP3xx: 3 of 8 fields; SGP40: none; SCD30: all
  fields)" — Dated live-readback field counts. · [H12]

## SPECIFICATION.md Part C.5 / C.5.1-C.5.3 (Config schema system, 1699-1797)

- **SENS.N328** INVAR · `SPECIFICATION.md:1767-1770` — "a setter whose own return means something else
  (`reset_voc()`'s `False` = no-op, not failed) needs its wrapper to report success unconditionally" —
  Wrapper convention (SGP40 reset, SCD30 ContMeas). · [H12]

## SPECIFICATION.md Part C.7 (Error handling & logging contract, 1807-1891)

- **SENS.N329** INVAR · `SPECIFICATION.md:1883-1886` — "A call site with just one pass/fail flag passes
  a fixed one-element sentinel and drives the flag through `condition=`" — Style convention. (low) ·
  [H12]
- **SENS.N330** INVAR · `SPECIFICATION.md:1887-1889` — "A per-field get/set forward always logs via
  `err_s()`/`wrn_s()` on failure, never a bare `except Exception: return None`" — Visibility convention.
  · related: SENS.T15 · [H12]

## SPECIFICATION.md Part C.7.1 (Running errno/wrnno table, 1893-1941)

- **SENS.N331** DRIFT · `SPECIFICATION.md:1933` — "`asy_isl29125_driver.py` (`ISL29125`) — 10-38 | ...
  35=... 38=`set_range_auto()`" | Range 10-38 with 23, 36, 37 unassigned in the text. (low) · related:
  XCUT.T07 · [H12]

## SPECIFICATION.md Part C.8 (Concurrency & locking model, 2016-2188)

- **SENS.N332** RISK · `SPECIFICATION.md:2055-2063` — "`writeto(0x00, b\"\\x06\")` is a true I2C
  general-call broadcast ... Low-risk, not fixed ... flagged for a project-owner decision if ever
  revisited" — Accepted risk; fires on every SGP40 restart. · related: SENS.T10 · [H12]
- **SENS.N333** ASSUME · `SPECIFICATION.md:2058-2060` — "neither sibling's datasheet documents
  general-call listening, and address `0x00` gets no special handling in the pinned rp2 `machine_i2c.c`"
  — "Neither sibling" fits dev (SCD30/ISL29125, per the named test); wozi's i2c1 sibling is BMP3xx.
  (low) · [H12]
- **SENS.N334** ASSUME · `SPECIFICATION.md:2153-2154` — "BMP3xx's/ISL29125's own config registers, both
  volatile per their datasheets" — Datasheet claim licensing unrestricted real writes. · [H12]

## SPECIFICATION.md Part C.9.1 (Read-trigger timer stagger, 2211-2298)

- **SENS.N335** LIMIT · `SPECIFICATION.md:2281-2293` — "`asy_scd30_driver.py` does not use the
  counter-based mechanism ... the strict \"never coincide\" proof above applies rigorously to
  BMP3xx/ISL29125/SGP40" — SCD30 read moment is IRQ-modulated, outside the proof. · related: XCUT.S06 ·
  [H12]

## SPECIFICATION.md Part C.14 / C.14.1 (Instance naming, 2380-2428)

- **SENS.N336** INVAR · `SPECIFICATION.md:2413-2426` — "REST dict keys must use `self.name` too, not a
  driver's `_NAME` module constant ... applied uniformly across every promoted driver" — Multi-instance
  key rule; "three promoted drivers" count stale. · related: GEN.T04 · [H12]

## SPECIFICATION.md Part C.14.3 (Error-source and logger fan-in, 2534-2572)

- **SENS.N337** LIMIT · `SPECIFICATION.md:2577-2580` — "a required field with nothing wired can still
  build clean via an explicit `{default = true, ...}` opt-in ...
  `_DefaultTemperatureSource`/`_DefaultHumiditySource` provide a constant fallback" — Constant
  compensation fallback possible by config. · related: SENS.T12 · [H12]

## SPECIFICATION.md Part E.5 / E.5.1-E.5.3 (Coverage, 2951-3088)

- **SENS.N338** ASSUME · `SPECIFICATION.md:3016-3017` — "`asy_sgp40_driver.py`'s `readlen is None` early
  return (no caller passes it — the buffer above is sized for the one `readlen=1`" — Serial read length
  seeded as a datasheet deviation. · related: SENS.S21 · [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **SENS.N339** LIMIT · `SPECIFICATION.md:3501-3503` — "`dev_legacy/asy_bsec_driver.py`'s bare
  `struct.unpack(\"bbbbL\", res)` against a hardcoded size of 8 ... anything porting it forward has to
  fix that first" — Known defect in reference code that a future BSEC port must fix first. · [H13]
- **SENS.N340** INVAR · `SPECIFICATION.md:3589-3590` — "A new source decoding floats or computing
  without a range gate needs the same" — Convention for new drivers; no test named. · related: XCUT.T23
  · [H13]

## SPECIFICATION.md Part K (intro) and K.1 — Before writing code

- **SENS.N341** INVAR · `SPECIFICATION.md:5712-5714` — "Place the real PDF under `datasheets/<name>/`
  ... every hardware-interaction claim in code comments cites a page number against it" — Citation
  discipline; plan notes A.6's datasheet list omits isl29125. · related: DOC.S08 · [H13]

## SPECIFICATION.md Part L.6.4 — Comment-tag family

- **SENS.N342** PLATFORM · `SPECIFICATION.md:6504-6506` — "`# @requires bus.timeout>=200000`/`bus.frequency<=100000`
  and `bus.frequency<=400000` ... (`bmp3xx` is deliberately untagged — its datasheet supports every I2C
  mode)" — Datasheet-derived bus limits (`src/asy_scd30_driver.py:108, 111`,
  `src/asy_sgp40_driver.py:90`); ISL29125 status not mentioned. · related: GEN.T08 · [H13]

## SPECIFICATION.md Part M.1.1 — Settled requirements (owner's list)

- **SENS.N343** SETTLED · `SPECIFICATION.md:6606-6653` — "1. **Every setting is API-settable and
  persisted.** ... 21. ... Saturation status is a measurement-output field (`Overrange`), never a log
  entry" — 21 owner requirements the driver is audited against (req. 14 superseded). · related: SENS.T08
  · [H13]
- **SENS.N344** SETTLED · `SPECIFICATION.md:6620-6621` — "9. **HSB's low-light behaviour is accepted** —
  no log scaling and no validity flag. Do not re-propose either." — Do-not-re-propose marker. · related:
  DOC.T14 · [H13]
- **SENS.N345** PLATFORM · `SPECIFICATION.md:6615-6616` — "the datasheet's bare-sensor guidance of ~40
  codes is the applicable default, not p10's `0xBF`" — IR-compensation default rests on the enclosure
  assumption (no IR-tinted cover). · related: SENS.T01 · [H13]
- **SENS.N346** INVAR · `SPECIFICATION.md:6634-6637` — "16. **The driver is self-healing and never
  reports a stale value as fresh.** ... a sample the driver cannot prove is current is reported as
  `None`, never re-stamped" — Plan seed: on config-read failure ISL29125 still publishes a freshly
  stamped sample. · related: SENS.S25, SENS.T04 · [H13]
- **SENS.N347** INVAR · `SPECIFICATION.md:6638-6641` — "17. **Auto-range must not depend on the
  interrupt alone.** ... the interrupt is the *fast* path, the periodic read the *guaranteed* one" —
  Dual-path requirement. · related: SENS.T05, SENS.S15 · [H13]
- **SENS.N348** ASSUME · `SPECIFICATION.md:6644-6645` — "19. ... No driver in `src/` rounds any output;
  the renderer's `decimals` hint does (H.5)." — Whole-`src/` claim (duplicates H.5.1). · [H13]
- **SENS.N349** INVAR · `SPECIFICATION.md:6646-6648` — "20. **Construction and `setup()` must complete
  on a bus where the chip never answers** ... proven for the buildgen-generated object graph" —
  Absent-chip requirement. · related: SENS.T14 · [H13]

## SPECIFICATION.md Part M.1.2 — Measured chip behaviour

- **SENS.N350** PLATFORM · `SPECIFICATION.md:6657-6668` — "Measured on real hardware (2026-09-12/13) ...
  `BOUTF` ... **cleared** by a status read, by the `0x46` reset command, and by writing `0x00` to
  `0x08`. p12 names only the write" — Silicon facts diverging from the datasheet (single specimen); twin
  `_isl29125_chip.py` models every row. · related: TWIN.T01, HW.T16 · [H13]
- **SENS.N351** ASSUME · `SPECIFICATION.md:6670-6672` — "a real brownout is reported exactly once — what
  `_recover_brownout()`'s `_brownout_seen` latch assumes" — Depends on exactly one destructive status
  read per cycle. · related: SENS.T03 · [H13]
- **SENS.N352** ASSUME · `SPECIFICATION.md:6675-6681` — "At `PRST = 4`, one status read per second set
  `RGBTHF` in exactly 4 of 8 reads ... the restart half is reproduced by the method above" —
  Measurement; only the unit is asserted on silicon by `isl29125_real_irq_edge.py`. · related: HW.T16 ·
  [H13]

## SPECIFICATION.md Part M.1.3 — Register ownership, prior art, colour chain

- **SENS.N353** INVAR · `SPECIFICATION.md:6685-6695` — "The driver keeps a shadow of `CONFIG1`-`CONFIG3`
  and writes it back whole; that is sound only while exactly one function touches each register." —
  Sole-writer table (`configure()`, `set_thresholds()`, `clear_brownout()`, `reset()`), convention-only;
  plan notes `set_autorange_thresh()` does not rewrite threshold registers. · related: SENS.S16 · [H13]
- **SENS.N354** SETTLED · `SPECIFICATION.md:6697-6701` — "Deliberately unused, so nobody adds them
  later: `SYNC` ... `CONVEN` ... `RGBCF` and `CONVENF`" — Do-not-add markers; `reset()` deliberately
  skips the status check. · [H13]
- **SENS.N355** LIMIT · `SPECIFICATION.md:6706-6708` — "**Nobody does auto-range or CCT** — both are
  this driver's own ... there is no reference to differential-test against" — No external oracle for
  auto-range/CCT. · related: TEST.T17 · [H13]
- **SENS.N356** LIMIT · `SPECIFICATION.md:6718-6721` — "**The matrix is a placeholder by the datasheet's
  own statement** ... so the reported colour is relative. There is **no gamma decode**" — Reported
  colour/CCT is relative, not calibrated. · [H13]
- **SENS.N357** SETTLED · `SPECIFICATION.md:6726-6728` — "**The Renesas application notes are
  unobtainable — do not re-attempt.**" — Do-not-re-attempt marker; 12-bit cycle time derived (~6.3 ms).
  · [H13]

## SPECIFICATION.md Part M.1.4 — Auto-range

- **SENS.N358** SETTLED · `SPECIFICATION.md:6732-6734` — "(owner, 2026-09-13/14): **a value whose only
  correct settings are a function of another field is derived, never exposed**" — Owner design rule. ·
  [H13]
- **SENS.N359** ASSUME · `SPECIFICATION.md:6736-6742` — "At 16 bit / 1 s that is 2; at 12 bit ... it is
  8 ... Measured (2026-09-13): a hand-set `PRST = 4` (1,212 ms) lost 5 of 6 crossings ... `PRST = 2`
  (606 ms) led 6 of 6" — Dated silicon measurement; `SampleInterv` writes `CONFIG3` (a config write
  triggers a chip write). · related: HW.T16 · [H13]
- **SENS.N360** SETTLED · `SPECIFICATION.md:6743-6746` — "`_AR_DOWN_DIVISOR`, with the divisor `2 × 26.67`
  — the part's *nominal* range ratio, deliberately not the measured `GainRatio`" — Deliberate
  decoupling. · [H13]
- **SENS.N361** SETTLED · `SPECIFICATION.md:6747-6750` — "**The settle margin is a constant**,
  `_SETTLE_CYCLES = 2` ... No scene, light level or resolution makes another value right." — Constant by
  design. · related: SENS.S27 · [H13]
- **SENS.N362** INVAR · `SPECIFICATION.md:6751-6755` — "counts a decision as interrupt-led only with
  **both** [flag and edge]; five periodic-led decisions in a row warn that the line looks dead" —
  Dead-INT-line detector contract (C.7.1 ISL29125 row). · related: SENS.T05 · [H13]

## SPECIFICATION.md Part M.1.5 — Calibration

- **SENS.N363** INVAR · `SPECIFICATION.md:6761-6764` — "`GainRatio` ... **changed only by a user PUT**:
  the driver never writes its own config, so every flash write stays on the REST path Part F.2's
  power-cycle recovery argument depends on" — Plan seed: an ISL29125 `GET /sensors` can write the chip
  and the FRAM ring. · related: SENS.S24, CORE.T02 · [H13]
- **SENS.N364** INVAR · `SPECIFICATION.md:6765-6766` — "`ISLCalibrate` is command-only ... nothing
  schedules it, so normal operation pays nothing" — Calibration only on demand; UI resend risk noted in
  WEB.S01. · related: WEB.S01 · [H13]
- **SENS.N365** LIMIT · `SPECIFICATION.md:6773-6775` — "**A refusal is reported by absence** (`GainMeas`
  stays `None`) ... so it logs only at debug level" — Calibration refusal silent at default log level by
  design. · [H13]
- **SENS.N366** LIMIT · `SPECIFICATION.md:6776-6779` — "a strongly coloured scene can be parked on the
  high range where its green is too small to calibrate from. **Operator procedure: park the scene dark
  first ...**" — Known limitation handled by an operator procedure (not in DEVICE_REFERENCE per this
  Part). · related: DOC.T11 · [H13]
- **SENS.N367** ASSUME · `SPECIFICATION.md:6781-6783` — "Proven on silicon (2026-09-14): three runs at
  ~138 lx ... nine candidates within 23.70–24.13 ... from 11.4 % to 0.4 %" — Dated single-board
  measurement. · related: HW.T16 · [H13]

## SPECIFICATION.md Part M.1.6 — Range ratio varies with level

- **SENS.N368** SETTLED · `SPECIFICATION.md:6787-6788, 6798-6800` — "not an open question and not a
  defect ... do not re-raise it as actionable" — Do-not-reopen marker. · related: DOC.T14 · [H13]
- **SENS.N369** ASSUME · `SPECIFICATION.md:6788-6793` — "six illuminants × three channels, 2026-09-12
  ... 28.08, 23.29, 22.49 and 21.55 ... Low-range compression and high-range under-read at small counts
  fit equally well" — Single-specimen measurement; cause undetermined (needs reference meter / second
  board). · related: HW.T16 · [H13]
- **SENS.N370** LIMIT · `SPECIFICATION.md:6795-6798` — "no single value is right everywhere — a ratio
  measured in the overlap band (~22–23) ... makes low-light cross-range comparisons slightly worse" —
  Accepted accuracy limit of one `GainRatio`. · [H13]

## DEVICE_REFERENCE.md

- **SENS.N371** MIRROR · `DEVICE_REFERENCE.md:31-35` — "`BackupPeriod` (minutes, 0–1440) ...
  `BackupMaxAge` (minutes, 0–10080)" — Mirrors src/asy_sgp40_driver.py:51-52 (they match). · [H14]
- **SENS.N372** LIMIT · `DEVICE_REFERENCE.md:31-32` — "**`0` disables periodic backup entirely** —
  nothing is ever written" — Undocumented: FRAM backup verification is effectively disabled for
  BackupPeriod 67-1440 and off by one elsewhere. · related: SENS.S02 · [H14]
- **SENS.N373** LIMIT · `DEVICE_REFERENCE.md:43-51` — "They are *not* sRGB, not colorimetric, and not
  white-balanced ... `CCT` is a relative indicator computed with McCamy's approximation" — ISL29125
  colour output is relative only. CCT is reported only for 2000–12500 K and is blank in dim light
  (src/asy_isl29125_driver.py:93, 548; math_helpers `cct_mccamy`). · [H14]
- **SENS.N374** MIRROR · `DEVICE_REFERENCE.md:53-58` — "the defaults (offset off, adjust 40) are a
  reasonable indoor starting point" — Mirrors src/asy_isl29125_driver.py:131-132 (`IrCompOffset` 0,
  `IrCompAdjust` 40); they match. IR compensation also shifts lux. · [H14]
- **SENS.N375** ASSUME · `DEVICE_REFERENCE.md:60-65` — "**nothing should visibly jump when `RangeAct`
  changes**. If it does, that is worth reporting." — Depends on the gain ratio (nominal 26.667) and the
  range logic; related auto-range seeds show INT storms and ~6.2-day stalls. · related: SENS.S15,
  SENS.S27 · [H14]
- **SENS.N376** SETTLED · `DEVICE_REFERENCE.md:67-73` — "It is gone from the settings on purpose ...
  changing the measurement interval now also reconfigures the sensor" — The chip-persistence (PRST)
  setting was removed and is now derived from the measurement interval and ADC resolution. · [H14]
- **SENS.N377** LIMIT · `DEVICE_REFERENCE.md:75-81` — "there is no setting that raises the ceiling
  further" — Overrange readings are clipped at 10000 lx (auto-range) or at the pinned range. · [H14]
- **SENS.N378** SETTLED · `DEVICE_REFERENCE.md:83-94` — "The unit will measure the real ratio on *this*
  chip, but only when you ask and it never applies the result by itself." — The calibration window is ≤2
  min and the result is held 10 min (src/asy_isl29125_driver.py:95, 100-101). Only a user entry changes
  Range Gain Ratio. THIRD_PARTY_LICENSES.md calls the calibration "FRAM-persisted". · related: LIC.S02 ·
  [H14]

## BACKLOG.md

- **SENS.N379** TODO · `BACKLOG.md:99-127` — "fixed in code and unit-tested; real-hardware
  re-verification still pending" — Unnumbered "ISL29125 chip configuration divergence under concurrent
  API load" (HIGH IMPORTANCE): `configure()`'s device-session lock widened; real-HW re-run queued as R9
  with the `Overrange` half. · related: SENS.S24 · [H15]
  ⟨4dc80ef: reworded: the shadow fix is confirmed on silicon, only the Overrange half owes a run
  (03f8bcf)⟩
- **SENS.N380** SETTLED · `BACKLOG.md:128-140` — "resolved differently, by design rather than by fixing
  a bug (project owner, 2026-09-15)" — `W12` retired; saturation is the live `Overrange` field;
  `isl29125_mechanism_envelope.py` updated but "also pending real-hardware re-run". · [H15]
- **SENS.N381** SETTLED · `BACKLOG.md:477-479` — "FiltCoeff keeps its two meanings - SETTLED, owner,
  2026-09-24." — Same key on BMP3xx and ISL29125; renaming = stored-config migration. · related: WEB.S15
  · [H15]
- **SENS.N382** RISK · `BACKLOG.md:909-912` — "safe today only because every setter is REST-triggered
  ... Don't add a periodic/high-frequency caller" — SCD30 NVM endurance unpublished. · covered-by:
  SENS.T07; related: PAR.S02 · [H15]

## Commit messages (chronological)

- **SENS.N383** LIMIT · `commit e960d44` — "The returned value isn't checked against anything (no
  documented set of valid firmware versions exists)" — SCD30 identity check = any CRC-valid
  firmware-version read. · status: by design; not restated in SPECIFICATION (low) | related: SENS.T* ·
  [H17]
- **SENS.N384** ASSUME · `commit 5ff8c0b` — "Reduced the post-measurement delay from 500ms to the
  datasheet's documented 100ms typical conversion time" — SGP40 wait value provenance; the plan's seed
  says 100 ms vs a 30 ms datasheet maximum — the commit's "100ms typical" claim disagrees with that
  seed. · covered-by: SENS.S07 · [H17]
- **SENS.N385** SETTLED · `commit 5ff8c0b` — "Dropped the feature-set check (0x20 0x2F): its result was
  read but never used" — SGP40 identity check reduced vs legacy (feature-set read removed). · status: by
  design (low) | related: PAR.T* · [H17]
- **SENS.N386** LIMIT · `commit 6ee7182` — "The exact per-coefficient bounds live in a header file this
  codebase doesn't have ... rejects an all-0x00/all-0xFF read" — BMP3xx trim-data plausibility is only a
  stuck-byte check, not Bosch's per-coefficient bounds; EVENT por_detected check declined. · tracked:
  src/asy_bmp3xx_driver.py:514-515 | related: SENS.T* · [H17]
- **SENS.N387** MIRROR · `commit 91ed578` — "a flagged-but-not-fixed cross-file consistency gap
  (unchecked add_into() return in measure_raw())" — SGP40 measure_raw CRC add_into return. · status:
  done (src/asy_sgp40_driver.py:627,630 now check `is None`) | - · [H17]
- **SENS.N388** TODO · `commit f030f56` — "its location in the config-schema block makes \"add a
  ContMeas schema entry\" the more likely original intent ... recorded the real gap in BACKLOG.md" —
  ContMeas schema gap. · status: resolved by design (src/asy_scd30_driver.py:86 "Deliberately no _VAL_*
  entry for ContMeas") | - · [H17]
- **SENS.N389** SETTLED · `commit 110f3db` — "a genuine not-ready cycle now reuses the last good reading
  with a fresh timestamp and does NOT count as an error (matching legacy)" — SCD30 can report a previous
  cycle's values under a new timestamp by owner choice (legacy parity over "safer-looking" change). ·
  status: not found restated in SPECIFICATION (grep) — UNTRACKED (low) | related: SENS.T*, PAR.T* ·
  [H17]
- **SENS.N390** LIMIT · `commit eff19bf` — "Add a best-effort/non-proven SPI sensor section (3.1),
  extrapolated ... since no SPI sensor has been promoted yet" — SPI-sensor driver guidance is unproven
  extrapolation. · status: still no SPI sensor in src/ (low); check SPECIFICATION Part C SPI section
  wording | related: SENS.T* · [H17]
- **SENS.N391** TODO · `commit d268f4b` — "SCD30_Reader.get_dict_cfg() (entirely) and three of
  BMP3xx_Reader.get_dict_cfg()'s fields ... can return a torn read across fields" — Torn live-readback
  gap. · status: done-in b6cb852 ("torn-read fix") | - · [H17]
- **SENS.N392** NOTE(UNTRACKED-THEN-TRACKED) · `commit 9de1b86 -> b8683a1` — "a separate, pre-existing
  race ... tracked separately" — "no such tracking existed anywhere" — Race traced to SGP40/SCD30 boot
  race. · status: done-in 7727ad1 | - · [H17]
- **SENS.N393** NOTE(OWNER) · `commits 0780d85, a2ea347, 5d57b02` — ISL29125 settled requirements (every
  setting API-settable, OperationMode not exposed, RGB 0-1, HSB low-light accepted, nested output) —
  Owner decisions. · tracked: SPEC Part M (moved in 5b97af3) | - · [H17]
- **SENS.N394** NOTE(DESIGN-REQ) · `commit 5d57b02` — "CONFIG1 now has two writers ... the driver needs
  a shadow copy"; "re-apply its whole configuration when it sees [BOUTF] set" — Requirements for
  promoted driver. · status: done (src/asy_isl29125_driver.py:70,248,397 brownout handling) | - · [H17]
- **SENS.N395** NOTE(OPEN-DECISION) · `commit f099ce8` — CCT "Proposed, not assumed ... carries as the
  one open decision" — Scope addition. · status: done (CCT in src/asy_isl29125_driver.py:164, "relative
  and uncalibrated - a documented placeholder RGB->XYZ matrix") | - · [H17]
- **SENS.N396** NOTE(PLACEHOLDER) · `src/asy_isl29125_driver.py:180 (from f099ce8 line)` — CCT uses "a
  documented placeholder RGB->XYZ matrix" — Placeholder calibration shipped. · tracked: in-code @web
  description (not in BACKLOG) | - · [H17]
- **SENS.N397** NOTE(FLAG) · `commit 7890e2b` — "SGPResetVOC is the only one of the 30 config field
  names in src/ that carries a device prefix ... whether SGPResetVOC is a deliberate exception is the
  project owner's call" — Naming discrepancy. · status: done-in 9b83336 (rule: command-only fields carry
  the prefix) | - · [H17]
- **SENS.N398** NOTE(SPEC-DEFECTS) · `commit b95a0d7` — "Three specification defects found while
  implementing ... to be reported: the gain correction's direction was inverted, the reset verify's
  STATUS == 0x00 check contradicts Table 15 ... thresholds must be scaled" — Reported. · status: done
  (recorded in ISL29125_FUNCTION_SPEC §9, later retired; gain ratio later removed — 080cde3) | - · [H17]
- **SENS.N399** NOTE(OWNER-LEFT) · `commit 1ea08ad / f333def` — "the range ratio is not a constant (~28
  at low counts falling to ~22 near full scale, BACKLOG 20)"; "making the gate range-aware ... is left
  for the owner" — ISL gain-ratio model question. · status: moot/done — gain ratio removed from FRAM
  later (080cde3 "the gain ratio stopped living in FRAM") | - · [H17]
- **SENS.N400** NOTE(DEFENSIVE) · `commit 1809110` — "errno 35/37 guard a contract the real class does
  not violate today ... kept as an explicitly-labelled defense-in-depth test" — Dead-in-practice error
  paths. · status: moot (gain-ratio FRAM path later removed, 080cde3) | - · [H17 (also H17)]
- **SENS.N401** NOTE(OWNER) · `commits f05f82d, 6023d87, 5860ad5` — ISL gain ratio user-calibrated
  (sandwich measurement, GainMeas by absence); AutoRangePersist derived; wrnno=17 removed — Owner
  decisions. · tracked: SPEC C.11.3 (:6746-6780), DEVICE_REFERENCE.md:89-92 | - · [H17]
- **SENS.N402** LIMIT · `commit f05f82d` — "the model is still one scalar ... the level-dependence
  itself stays recorded as the limit of what one number can do" — Accepted accuracy limit. · tracked:
  SPECIFICATION.md:6787-6795 | - · [H17]
- **SENS.N403** NOTE(OWNER) · `commit 05f4746 / 179a10c` — "BACKLOG 20 is PARKED, not deferred: there is
  one device"; "BACKLOG 29 is out of scope for the ISL29125 promotion" — Parked ISL ratio question;
  out-of-scope tool fix. · tracked: SPEC C.11.4 (ratio); frozen-asyncio probe done-in 12640c2 | - ·
  [H17]
- **SENS.N404** NOTE(FINDING) · `commit a11feca` — "the migration emits two W4s rather than one, and the
  calibration band gate tests green counts while the range decision tests peak counts" — ISL calibration
  can never run for colour-dominant scene on high range. · tracked: SPEC C.11.3 (operator procedure:
  park dark first) | - · [H17]
- **SENS.N405** NOTE(UNREACHABLE) · `commit 1da9650 / b937dab` — "_read_sensor_dict() and
  _snapshot_field() both guard against decode_config() returning None, which get_config_snapshot()
  cannot produce" — Dead guards kept. · tracked: SPEC E.5.1 | - · [H17]
- **SENS.N406** NOTE(OVERRIDE-RULE) · `commit 2ad5d9e` — "the owner's standing ruling that the legacy
  driver has no proven field behaviour to preserve for this device is kept because it overrides a
  CLAUDE.md rule" — Exception to "verify against legacy field behaviour" for ISL29125. · tracked: SPEC
  C.11.5 (Part M after 5b97af3); not mentioned in CLAUDE.md's rule itself | - · [H17]
- **SENS.N407** NOTE(DISCARDED-PR-FINDINGS) · `commits 1909d8b, 3f7cc25 (from PR #84)` — ISL29125
  shadow-divergence (HIGH IMPORTANCE) and "a config-persisting PUT /sensors resets its own HTTP
  connection under concurrent API load" — Findings rescued from a discarded branch. · status: shadow
  divergence done-in 5872365; connection reset tracked: BACKLOG #30 ("root-cause not yet established") |
  related: REST.T* · [H17]
- **SENS.N408** NOTE(EXCEPTION) · `commit f341543` — "asy_scd30_driver.py's own read trigger is
  IRQ-gated ... flagged rather than silently smoothed over" — Exception to timer no-coincidence design.
  · tracked: SPEC C.9.1 | - · [H17]
- **SENS.N409** NOTE(ONLY-IN-TEMP-DOC) · `commit 21560a4` — "SGP40 W13 fills its ring while NTP is
  absent" ("one 'backup written without timestamp' slot per backup (1 min), 9 slots after one hotspot
  episode ... Suggested: apply C.7.1's per-episode repeat rule ... a candidate for BACKLOG 50's list") —
  Same warning-flood class as item 35, unfixed; BACKLOG 50 was already closed (b5450aa) when this was
  found, and the finding lives only in the throwaway HARDWARE_TEST_HANDOVER.md:163. · UNTRACKED (medium;
  temp doc only) | related: SENS.T*, STOR.T* · [H17 (also H17)]
  ⟨4dc80ef: F18 owner decision open: open in BACKLOG.md "Real-hardware work still owed" (F18)⟩

## GitHub PRs and issues (hundertvolt/sensors)

- **SENS.N410** NOTE(DEAD-CODE) · `https://github.com/hundertvolt/sensors/pull/30` —
  "`BMP3XX_I2C.get_altitude()` has zero callers anywhere in `src/` — dead code, left for a future
  cluster's decision" — Still no src caller at 2a88cc8 (src/asy_bmp3xx_driver.py:570); not in
  BACKLOG/SPEC · UNTRACKED | - · [H17]

## Delta `2a88cc8` → `4dc80ef` (main head, V11)

- **SENS.N411** INVAR · `src/asy_sgp40_driver.py:167, 433, 440, 443-444` — "one slot per NTP outage, not
  per backup - a timestamped backup ends the episode" — W13 now follows C.7.1's repeat rule through an
  in-RAM episode flag; a reboot or task restart mid-outage opens a new episode. · covered-by: SENS.S28 ·
  [D1]
- **SENS.N412** SETTLED · `SPECIFICATION.md:1939` — "one slot per outage, which a timestamped backup
  ends" — C.7.1's SGP40 row records W13's episode rule with the bench finding behind it (nine slots in
  one hotspot episode). · related: XCUT.T07 · [D1]
