# Harvest — ALGO: Pure algorithms and codecs

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`, moved to `4dc80ef` by V11).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 11, INVAR 17, MIRROR 10, LIMIT 15, RISK 5, ASSUME 8, PLATFORM 3, SUPPRESS 8, TODO 1, DRIFT 2, NOTE 1 — 81 items.


## src/crc_checks.py

- **ALGO.N001** MIRROR · `src/crc_checks.py:1-4` — "CRC8 (Sensirion's documented CRC-8), CRC16
  (CRC-16/CCITT-FALSE), CRC32 (CRC-32/MPEG-2)... CRC8 poly 0x31/init 0xFF; CRC16 0x1021/0xFFFF; CRC32
  0x04C11DB7/0xFFFFFFFF" — Algorithm identities must match the Sensirion datasheets (CRC8) and the UART
  C peer (CRC16, changelog A7, "Python leads") · related: ALGO.T03 · [H02]
- **ALGO.N002** INVAR · `src/crc_checks.py:4-6` — "Every public method returns None/False on invalid
  input rather than raising, except add()/check(), which allocate and let MemoryError propagate." —
  Callers of `add()`/`check()` must catch MemoryError themselves (UART driver does) · related: ALGO.S04
  · [H02]
- **ALGO.N003** INVAR · `src/crc_checks.py:6` — "run_inc()/check_inc() hold per-instance state - never
  share one." — Convention only; FRAM chunk layer uses the incremental API on the instance it was handed
  (`src/asy_fram_manager.py:315-347`) · related: ALGO.T03 · [H02]
- **ALGO.N004** LIMIT · `src/crc_checks.py:8-10` — "a register at 0 stays 0 through further 0x00 bytes,
  so check()/check_from()/check_inc() can't detect trailing zero-padding past the buffer's true end -
  callers must supply an accurate length" — Known undetectable-error class; caller obligation · related:
  ALGO.T03 · [H02]
- **ALGO.N005** RISK · `src/crc_checks.py:18-20, 24` — "An invalid config (negative num_bytes, poly out
  of range for the width) silently degrades to pass-through mode rather than raising" — A misconfigured
  CRC silently disables integrity checking · related: ALGO.T03 · [H02]
- **ALGO.N006** LIMIT · `src/crc_checks.py:58-59, 73-74, 111-112, 131-132` — "if self.poly is None: #
  uninitialized or \"pass\" mode" — Pass mode skips bounds validation and returns the caller's object ·
  covered-by: ALGO.S04 · [H02]
- **ALGO.N007** SUPPRESS · `src/crc_checks.py:68-69, 123-124` — "except ValueError: return None" —
  `pack_into` failure swallowed to None (no comment) · [H02]
- **ALGO.N008** LIMIT · `src/crc_checks.py:155-157` — "class CRC16(CRC_Base):" — No production caller;
  UART dev link runs `CRC_Pass` · covered-by: ALGO.S05 · [H02]

## src/framing_codecs.py

- **ALGO.N009** INVAR · `src/framing_codecs.py:3` — "Every method returns None on invalid input or a
  failed allocation - never raises." — Never-raise contract · related: ALGO.T04 · [H02]
- **ALGO.N010** MIRROR · `src/framing_codecs.py:19-21, 69-70` — "Mirrors crc_checks.py's
  CRC_Base/CRC_Pass split, so a caller can hold either family behind one dispatch table." — Structural
  mirror with `crc_checks.py` · [H02]
- **ALGO.N011** INVAR · `src/framing_codecs.py:53-55, 101-124` — "a delimited codec returns a view of
  its own long-lived scratch instead" — Returned view aliases shared scratch: caller must finish writing
  before the next `encode_into()` · covered-by: ALGO.T04 · [H02]
- **ALGO.N012** LIMIT · `src/framing_codecs.py:75-77` — "class Framing_COBS(Framing_Base):" — COBS path
  unused in production (UART defaults to `Framing_Pass`) · covered-by: ALGO.T04 · [H02]
- **ALGO.N013** INVAR · `src/framing_codecs.py:127-128` — "`buf` holds one encoded frame *without* its
  delimiter - the read loop strips it" — Caller contract between `asy_uart_driver._read_delimited` and
  the codec · [H02]

## src/math_helpers.py

- **ALGO.N014** INVAR · `src/math_helpers.py:3` — "Every function returns None - never raises - for a
  None, out-of-domain, or NaN input" — Contract backed by range gates and per-function catches ·
  related: ALGO.T01 · [H02]
- **ALGO.N015** SETTLED · `src/math_helpers.py:31-33` — "anything outside means that chain is broken,
  not that the light was unusual - hence a reject rather than a clamp" — Reject-not-clamp policy for
  colour inputs (M.1.3) · [H02]
- **ALGO.N016** ASSUME · `src/math_helpers.py:36-39` — "1e-12 rather than 0.0: a denormal X+Y+Z would
  otherwise divide out to a ~1e300 chromaticity." — Thresholds reasoned in double; target is float32
  (1e300 unrepresentable) · related: ALGO.T06 · [H02]
- **ALGO.N017** MIRROR · `src/math_helpers.py:40-42` — "McCamy (1992) fits the Planckian locus over
  roughly 2000-12500 K; outside it the cubic still returns a number" — Literature-derived validity
  window · related: ALGO.T01 · [H02]
- **ALGO.N018** MIRROR · `src/math_helpers.py:46-47` — "Stull (2011) empirical wet-bulb approximation.
  Valid domain per the paper: -20-50 degC, 5-99% RH" — Domain claim to check against the paper ·
  related: ALGO.T01 · [H02]
- **ALGO.N019** SUPPRESS · `src/math_helpers.py:60-61` — "except (ValueError, ArithmeticError): return
  None" — Math errors → None (wet bulb) · [H02]
- **ALGO.N020** LIMIT · `src/math_helpers.py:65-67` — "independently fit curves, ~1 degC apart at the
  switch (see test_dew_point_branch_boundary_roughly_continuous)" — Known ~1 °C discontinuity at 0 °C in
  dew point · related: ALGO.T01 · [H02]
- **ALGO.N021** SUPPRESS · `src/math_helpers.py:82-83` — "except (ValueError, ArithmeticError): return
  None" — Math errors → None (dew point) · [H02]
- **ALGO.N022** DRIFT · `src/math_helpers.py:86-89` — "pressure at height offset dh from the p0
  reference... p0/tmean range matches the BMP388/390 datasheet (its only caller)" — Name `altitude_baro`
  returns a pressure; range claim vs BMP3xx datasheet · covered-by: ALGO.S03 · [H02]
- **ALGO.N023** SUPPRESS · `src/math_helpers.py:97-98` — "except (ValueError, ArithmeticError): return
  None" — Math errors → None (barometric) · [H02]
- **ALGO.N024** DRIFT · `src/math_helpers.py:101-112` — "a/b pick the ice- vs water-phase constants." —
  7.6/240.7 is the supercooled-water pair, not ice; unused in `src/` · covered-by: ALGO.S03 · [H02]
- **ALGO.N025** SUPPRESS · `src/math_helpers.py:115-116` — "except (ValueError, ArithmeticError): return
  None" — Math errors → None (abs humidity) · [H02]
- **ALGO.N026** LIMIT · `src/math_helpers.py:119-122` — "result is clamped to the valid 0-100% range...
  purely to reject negative/nonsensical input" — Clamps (unlike the colour chain's reject policy); no
  production caller · covered-by: ALGO.S05 · [H02]
- **ALGO.N027** SUPPRESS · `src/math_helpers.py:135-136` — "except (ValueError, ArithmeticError): return
  None" — Math errors → None (rel humidity) · [H02]
- **ALGO.N028** SETTLED · `src/math_helpers.py:163-164` — "sRGB/Rec.709 D65 primaries, pinned as
  literals: a second published rounding differs in the 6th decimal, so these must not be \"corrected\"
  (Part M.1.3)." — Don't-change rule for the matrix · [H02]
- **ALGO.N029** SETTLED · `src/math_helpers.py:189-191` — "Out-of-span results are REJECTED, not
  clamped: a clamped 12500 would look like a real one." — Reject policy for CCT · [H02]

## src/voc_algorithm.py

- **ALGO.N030** ASSUME · `src/voc_algorithm.py:5-6` — "fixed-point (Q16.16) port of the archived C
  reference (Sensirion/embedded-sgp...) via DFRobot's Python translation. Verified constant-for-constant
  and against vocalgorithm_process()'s exact operation order." — Verification claim against a C
  reference that is not in the repo · covered-by: ALGO.T02 · [H02]
- **ALGO.N031** INVAR · `src/voc_algorithm.py:7` — "Every method returns a well-defined value, never
  raises." — `vocalgorithm_process()` has no guard; relies on arithmetic never raising or looping (see
  `_fix16_div`) · related: ALGO.S06 · [H02]
- **ALGO.N032** RISK · `src/voc_algorithm.py:41-43` — "_FIX16_MINIMUM = const(0x80000000) /
  _FIX16_OVERFLOW = const(0x80000000)" — Positive in Python, INT32_MIN in C · covered-by: ALGO.S01 ·
  [H02] ⟨quote not matched at the anchor⟩
- **ALGO.N033** MIRROR · `src/voc_algorithm.py:47-50` — "vocalgorithm_process()'s own sraw guard/clamp
  bounds - bare literals in the C reference, named here" — Constants must match the C reference literals
  · related: ALGO.T02 · [H02]
- **ALGO.N034** INVAR · `src/voc_algorithm.py:52` — "_VOC_PARAMS_MEMSIZE = const(256) # 32 * 8 bytes" —
  Must stay equal to `struct.calcsize("32q")`; sizes the SGP40 FRAM chunk (persisted layout) · related:
  ALGO.T05 · [H02]
- **ALGO.N035** INVAR · `src/voc_algorithm.py:56-57` — "Field names/order trace the C reference 1:1 (see
  module docstring)" — Field order is also the persisted FRAM state layout; reordering silently corrupts
  restored state · related: ALGO.T05 · [H02]
- **ALGO.N036** SUPPRESS · `src/voc_algorithm.py:134-135` — "except Exception: return False" —
  `pack_into` failure swallowed (no comment) · [H02]
- **ALGO.N037** SUPPRESS · `src/voc_algorithm.py:142-143` — "except Exception: return False" —
  `unpack_from` failure swallowed (no comment); successful unpack is unvalidated · covered-by: ALGO.T05
  · [H02]
- **ALGO.N038** RISK · `src/voc_algorithm.py:98, 141` — "\"32q\"" — No byte-order prefix on persisted
  state, against F.1's pin-"<" rule · covered-by: ALGO.S02 · [H02]
- **ALGO.N039** MIRROR · `src/voc_algorithm.py:184-185` — "Precomputed once for _fix16_exp()... (see
  SPECIFICATION.md C.11 point 6)." — Deviation from the reference's structure justified by a spec item ·
  related: ALGO.T02 · [H02]
- **ALGO.N040** RISK · `src/voc_algorithm.py:199-202` — "def _f16(self, x: float) -> int:" — Runtime
  float32 conversion per call vs C compile-time double · covered-by: ALGO.S07 · [H02]
- **ALGO.N041** RISK · `src/voc_algorithm.py:236-247` — "divider = b if b >= 0 else (b * (-1)) &
  0xFFFFFFFF ... while divider < remainder:" — Unbounded loop for a zero-masked divider · covered-by:
  ALGO.S06 · [H02]

## tests/test_asy_sgp40_driver.py

- **ALGO.N042** SETTLED · `tests/test_asy_sgp40_driver.py:1634-1636` — "per voc_algorithm.py's module
  docstring on why this differs from Sensirion's own short-interruption-only API" — whole-state VOC
  restore across reboots deliberately exceeds Sensirion's documented short-interruption use · related:
  ALGO.T02 · [H04]

## tests/test_crc_checks.py

- **ALGO.N043** INVAR · `tests/test_crc_checks.py:123-124` — "num_bytes == 0 always nullifies it back to
  None (CRC_Base's own existing invariant)" — CRC_Pass accepts but discards poly (low) · related:
  ALGO.S04 · [H05]

## tests/test_math_helpers.py

- **ALGO.N044** LIMIT · `tests/test_math_helpers.py:40` — "0.5% used to be the (incorrect) lower bound;
  Stull's paper only validates 5-99% RH" — wet_bulb_temperature's validity domain comes from Stull's
  paper; below 5% RH returns None · related: ALGO.T01 · [H05]
- **ALGO.N045** LIMIT · `tests/test_math_helpers.py:95-100` — "measured, they disagree by about 1.03
  degC right at the boundary at 50% RH" — dew_point's water/ice coefficient sets are discontinuous at 0
  °C (~1.03 °C measured); the test tolerates 1.5 °C and only guards against growth · related: ALGO.T01,
  ALGO.S03 · [H05]
- **ALGO.N046** INVAR · `tests/test_math_helpers.py:189-190` — "the -40..85 degC range check must reject
  it before the division ever runs" — altitude_baro's divide-by-zero at tmean=-273.15 is prevented only
  by the range check · [H05]
- **ALGO.N047** PLATFORM · `tests/test_math_helpers.py:429-434` — "Exact equality, not approx(): two
  published roundings of this matrix differ in the 6th decimal (Part M.1.3)" — Pins the sRGB→XYZ
  literals by exact float equality on the double-precision Unix port; on RP2040 float32 the same
  literals round differently, so this pins source text, not device values · related: ALGO.T06 · [H05]
- **ALGO.N048** MIRROR · `tests/test_math_helpers.py:430-431` — "The constants are const()-folded and
  not readable as attributes" — The test hand-copies the matrix; src and test values must be kept in
  sync by hand · [H05]
- **ALGO.N049** LIMIT · `tests/test_math_helpers.py:535-537` — "must return None, never a clamped
  2000.0/12500.0" — cct_mccamy returns None outside the 2000-12500 K validity span · [H05]
- **ALGO.N050** INVAR · `tests/test_math_helpers.py:569` — "-1.0 is FiltCoeff's own documented "filter
  off" convention throughout src/" — ema_step and every FiltCoeff user share the -1.0 sentinel · [H05]
- **ALGO.N051** INVAR · `tests/test_math_helpers.py:593-594` — "A NaN/inf previous state ... must not
  poison every future value forever" — ema_step resets on a non-finite previous state · [H05]

## tests/test_notification_sgp40_integration.py

- **ALGO.N052** ASSUME · `tests/test_notification_sgp40_integration.py:3-9` — "a higher raw tick count
  moves the index down, raw increase meaning cleaner air on this sensor's convention" — Calibration
  facts about the VOC algorithm (45-interval blackout, settle toward 100) "verified directly"; the
  test's two-phase design depends on them · [H05]
- **ALGO.N053** MIRROR · `tests/test_notification_sgp40_integration.py:156-160` —
  "_VOCALGORITHM_INITIAL_BLACKOUT=45 plus settling time" — 160 settle cycles and an exact `VOC == 100`
  assertion depend on voc_algorithm's constants · [H05]

## tests/test_voc_algorithm.py

- **ALGO.N054** PLATFORM · `tests/test_voc_algorithm.py:90-91, 103-104` — "Datasheet Table 1: VOC Index
  output range is 1-500" / "datasheet SRAW_VOC is 0-65535 ticks; the algorithm's own valid processing
  window is narrower" — Datasheet facts; blackout is `<=` so processing starts at call 46 · [H05]
- **ALGO.N055** LIMIT · `tests/test_voc_algorithm.py:127-132, 143-145` — "only reached once the internal
  variance estimate has grown large" — Several estimator branches are reachable only with adversarial
  sustained input, found by tracing · related: ALGO.T02 · [H05]
- **ALGO.N056** SETTLED · `tests/test_voc_algorithm.py:238-244` — "not Sensirion's own
  get_states()/set_states(), which carry mean and std only, but a full 32-field dump and restore" —
  Reboot survival uses a full-state dump; a restore also advances state by one sample · related:
  ALGO.T05 · [H05]
- **ALGO.N057** LIMIT · `tests/test_voc_algorithm.py:315-321` — "only reached with a negative operand
  ... leaving them exercised only via process()'s internal calls" — `_fix16_mul` negative branches were
  previously untested directly · [H05]
- **ALGO.N058** MIRROR · `tests/test_voc_algorithm.py:360-361` — "Values from the C reference's own
  overflow guards (x >= f16(10.3972) -> FIX16_MAXIMUM, x <= f16(-11.7835) -> 0)" — Constants copied from
  the Sensirion C reference, which is not in the repo · related: ALGO.T02, ALGO.T07 · [H05]
- **ALGO.N059** ASSUME · `tests/test_voc_algorithm.py:368-373, 379-381` — "the one value whose absolute
  magnitude does not fit back into a signed 32-bit remainder" — FIX16_MINIMUM division edge cases,
  compared mod 2**32; Python ints do not wrap like C int32 · related: ALGO.S01, ALGO.S06 · [H05]
- **ALGO.N060** LIMIT · `tests/test_voc_algorithm.py:547-549` — "_vocalgorithm_set_tuning_parameters()
  has no caller anywhere in this codebase today" — Dead, Sensirion-mirroring API kept on purpose;
  smoke-tested only · related: CORE.T10 · [H05]

## tests_hardware/README.md

- **ALGO.N061** LIMIT · `tests_hardware/README.md:710-716` — "Deliberately a stability/sanity check, not
  a numerical-accuracy claim" — VOC-algorithm quality on silicon is sanity only; accuracy needs a human
  stimulus. · [H08]

## dev_legacy/README.md

- **ALGO.N062** ASSUME · `dev_legacy/README.md:81-84` — "`VOC=0` through cycle 46, real values from
  cycle 47 on" — Single observation of the 45-cycle VOC blackout on silicon. · - (low) · [H08]

## dev_legacy/*.py (reference-only 2026-08-27 on-device snapshot, MicroPython 1.24.1 — plan §2.2; field/bench behaviour only)

- **ALGO.N063** ASSUME · `dev_legacy/asy_sgp40_driver.py:75` — "voc algorithm needs 1s period fixed" —
  VOC algorithm sampling-period assumption in legacy. · - (low) · [H08]

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)

- **ALGO.N064** PLATFORM · `SPECIFICATION.md:246-251` — "45 sampling intervals must elapse before the
  index moves off 0 ... a *higher* raw tick count reads as *cleaner* air" — Sensirion VOC semantics
  depended on; reference C source not in repo. · related: SENS.S04 · [H12]

## SPECIFICATION.md Part C intro, C.1-C.2 (1475-1535)

- **ALGO.N065** SETTLED · `SPECIFICATION.md:1505-1506` — "`voc_algorithm.py`'s internals trace their
  DFRobot/Sensirion source 1:1 (F.4), casing intentionally non-compliant" — Permanent naming exception.
  · [H12]

## SPECIFICATION.md Part D (src/ Production-Quality Checklist, 2576-2728)

- **ALGO.N066** ASSUME · `SPECIFICATION.md:2603-2606` — "`wet_bulb_temperature`'s humidity lower bound
  was `0.5%`; Stull (2011) only validates to `5%` ... (`altitude_baro`'s range comes from the BMP388/390
  datasheet" — Literature/datasheet domain claims; the BMP390 PDF is absent (A.6). · related: SENS.S12 ·
  [H12]

## SPECIFICATION.md Part F.4 — Vendor-derived code

- **ALGO.N067** SETTLED · `SPECIFICATION.md:3667-3671` — "Sensirion-derived reference-algorithm ports
  stay literal ... a stylistic rewrite is not" — Opposite policy for `voc_algorithm.py`. · related:
  ALGO.T02 · [H13]
- **ALGO.N068** MIRROR · `SPECIFICATION.md:3668-3670` — "internal naming traces the original C source
  1:1 so it stays diffable against Sensirion's own reference" — `src/voc_algorithm.py` ↔ Sensirion C
  reference. · covered-by: ALGO.T02 · [H13]

## SPECIFICATION.md Part I.2 — Hotspot catalog

- **ALGO.N069** SETTLED · `SPECIFICATION.md:4890-4893` — "**`src/crc_checks.py` keeps its per-byte
  `await asyncio.sleep(0)`** (2026-09-18: \"pure wall clock time is not such an issue, don't touch\")" —
  Owner decision; ~5.8x wall-time cost accepted; 160 B per `_crc()` call. · related: ALGO.T03, PERF.T04
  · [H13]

## SPECIFICATION.md Part M.1.3 — Register ownership, prior art, colour chain

- **ALGO.N070** SETTLED · `SPECIFICATION.md:6712-6717` — "The **sRGB/Rec.709 D65 matrix is pinned as
  literals** ... **The two published McCamy forms are algebraically identical** ... Do not \"correct\"
  one into the other." — Do-not-fix markers in `math_helpers.py`. · related: ALGO.T01 · [H13]
- **ALGO.N071** INVAR · `SPECIFICATION.md:6720-6721` — "an out-of-domain input means the chain is broken
  and is rejected, not clamped" — Helper domain contract. · related: ALGO.T01 · [H13]

## BACKLOG.md

- **ALGO.N072** INVAR · `BACKLOG.md:717-719` — "One Framing_COBS instance shared between two drivers
  would corrupt both" — Every construction site makes its own; the failure would be silent. · related:
  ALGO.T04 · [H15]

## Archive `12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md` (5,553 lines) — only items still open/undecided/deferred/next-step there, with carry status in current docs

- **ALGO.N073** TODO · `ARCH:2666-2667` — "the RP2040 factor is unmeasured — queued as a device script
  beside REAL_HARDWARE_TEST_QUEUE.md §1A's A6" — Silicon wall-time factor of `crc_checks` per-byte
  yield; not carried in the current queue (no CRC row); the owner's "don't touch" (SPEC:4876-4881) makes
  it informational. · related: ALGO.T03 · [H15]
  ⟨4dc80ef: A6 script kept only in BACKLOG.md "Real-hardware work still owed" (T4)⟩

## UART_C_PORT_CHANGELOG.md (128 lines; owning area UART). Every entry is pending C-side reconciliation, which is out of scope (owner 2026-09-24).

- **ALGO.N074** SETTLED · `UART_C_PORT_CHANGELOG.md:107-124` — "Can COBS's 0x00 delimiter be confused
  with a natural UID rollover to 0x00? No" — Checked against 20,010 cases (2026-09-11). · [H15]

## Commit messages (chronological)

- **ALGO.N075** NOTE(REVERT) · `commit b0a9235 (reverts 4e2d953)` — "Revert \"Explicitly catch
  ZeroDivisionError in math_helpers.py; document exhaustiveness check\"" — Explicit ZeroDivisionError
  catch and the src/README.md "verify caught exception set against MicroPython source" checklist
  expansion were reverted without a stated reason. · status: src/math_helpers.py has no
  ZeroDivisionError (grep); reason for revert UNTRACKED (low) | - · [H17]
- **ALGO.N076** ASSUME · `commit bd00a8d` — "this assumes mypy-checked callers - MicroPython doesn't
  enforce types at runtime, but this module doesn't need to defend against that" — math_helpers
  None-safety contract relies on static typing of all callers. · tracked: src/math_helpers.py module
  docstring | - · [H17]
- **ALGO.N077** LIMIT · `commit d0abd60` — "Document a real ~1 degC discontinuity in dew_point at the
  water/ice branch boundary (inherent to stitching two independently-fit curves, not a bug)" — Accepted
  dew-point discontinuity. · tracked: tests/test_math_helpers.py regression test (per commit) | - ·
  [H17]
- **ALGO.N078** SETTLED · `commit b1059bd` — "Records the declined lookup-table CRC optimization (small
  buffer sizes in practice, not worth the RAM cost)" — Owner/session declined table-driven CRC. ·
  status: not restated in SPECIFICATION (grep finds no CRC lookup-table note) — UNTRACKED (low) | - ·
  [H17]
- **ALGO.N079** LIMIT · `commit 93b809b / c086605` — "check()/check_from()/check_inc() all silently
  validate a buffer whose caller-supplied length overruns into trailing zero bytes ... flagged to the
  project owner for confirmation rather than treated as settled" — CRC zero-padding blind spot; c086605
  then removed its three pinning tests ("aren't needed going forward"), so the behavior is documented
  only by a comment, not tested. · tracked: src/crc_checks.py:8-9 comment; test coverage removed in
  c086605 | related: ALGO.T* · [H17]
- **ALGO.N080** INVAR · `commit 32ceee8` — "incremental CRC state is instance-local by design, not
  concurrency-safe by accident of the one current caller locking around it" — run_inc/check_inc needs a
  dedicated instance per sequence (caller discipline). · tracked: src/crc_checks.py comments (per
  commit) | - · [H17]
- **ALGO.N081** INVAR · `commit 500851c` — "raising is allowed, but only in a documented, controlled
  manner, and only once proven every upstream caller handles it" — crc add()/check() MemoryError is a
  controlled raise; only asy_uart_driver calls them and must keep wrapping. · tracked: src/crc_checks.py
  docstring (per commit) | - · [H17]
