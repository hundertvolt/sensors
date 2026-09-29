# Pass 4 — summary (2026-09-29, HEAD `549445b`)

Four read-only scans (brief `audit/sweeps/pass4_prompt.md`), one file each in this directory. Lead spot checks
against primary sources are noted per scan.

| Scan | Input | Verdicts | Register lines |
|---|---|---|---|
| K counter inventory (OR105.a (4)) | every counter candidate in `src/`, codegen templates, `digital_twin/`, `js/` (+ tests/host, lower priority) | OK 24, UNBOUNDED 12, NOT-A-COUNTER 12, ALLOCATES 4, WRONG-FORM 2 | 13 |
| H history remainder | 316 BACKLOG narrative sentences (all read); 106 comment chains in scripts/toolchain/devices/.github/config/html; the 76 provenance-cited commits | part 1: KNOWN 131, PRUNED-OK 133, HOLDS 21, DRIFT 14, OVERTAKEN 9, LOST 8; part 2: HOLDS 106, DRIFT 2; part 3: KNOWN 76 (+ HOLDS 10, OVERTAKEN 8, NO-DECISION 10, MISATTRIBUTED 3, DRIFTED 1) | 17 |
| F fetched-source checks (OR108.a (3)) | 60 claims (v1.28/v1.29 comparisons, upstream trackers, NET.S19, CI.S11, outside triggers) | HOLDS 40, WRONG 7, TRIGGER-MET 2, TRIGGER-NOT-MET 7, UNREACHABLE 4 | 11 |
| R references and one test file | all 675 score-judged SPEC references (sample of 150, then every one); `tests/test_bus_hazard_multi_device.py` | RIGHT 639, WRONG-SECTION 28, STALE 4, AMBIGUOUS 4; tests KEEP 3, ADAPT 6, MOVE 1 | 4 |

Lead checks: K — `LockedCounter._step` clamps after stepping, `boot_signature` is a `LockedCounter(max_val=0xFFFFFFFF)`,
`_fix16_mul` masks with `0xFFFFFFFF` (heap int on rp2); R — `SGP40_I2C.measure_raw()` stages its shared buffer
outside the device session (`asy_sgp40_driver.py:621-632`); F — v1.29.0's `lib/mbedtls` is tag `mbedtls-3.6.6`
(`0bebf8b`), the pinned paths-filter SHA is the `v3` tag object; H — `604c7bb`/`beaf97a` and `d4814cc`/`b0f755c` read.

Not covered: F — gcc.gnu.org, bugs.debian.org, NVD and micropython#2057's comments unreachable; K — JS by regex
only, test-side `ticks_*` classed from the listing; H — JSON files carry no comments, chat-only decisions are
invisible (OR64). None of these needs a further scan pass: the tool-run items go to B0, the rest stay as noted.

## Owner questions (asked 2026-09-29)

1. VOC fixed-point arithmetic also allocation-free? (K.30)
2. BMP3xx sample-interval ceiling: 600 s or 3,600 s? (H.10)
3. ConfigManager errors: own rows or folded into module? (H.26)

The 45 register lines are merged after the answers, in one pass, as pass 3's were.
