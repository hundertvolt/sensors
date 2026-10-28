DR3 decision review, written by the part (Wed Oct 28 11:48:48 UTC 2026)

# DR3: the owner-review list, units U11-U16 (CORE, ALGO, BUS, PLAT, SENS, STOR)

Input: `inputs/DR3_register_rows.txt`, 206 rows (`REG:111`-`REG:122`, the scan-fold rows of U11/U15/U16, and
`REG:276`-`REG:493`). Read-only: nothing in the repo, a worktree or an earlier scan file was changed, nothing ran.
Static checks only: `git show`/`git grep` at `11b66cd8`, `497b3eda` (head product tree) and `25caf528` (pre-audit);
`legacy/` read through `git show 11b66cd8:`; the scan rows (`scan_pub/A.md`, `C.md`, `B.md`, `D.md`, `E.md`,
`REPORT.md`; `scan2/SCAN2.md`, `G1.md`, `G2.md`, `G3.md`, `G4.md`, `G4b.md`); the owner's record
(`PROJECT_AUDIT_PLAN.md` OR rows, `recovered/owner_rulings_after_LN118.md`, `inputs/answers.json`,
`inputs/DR1_review_decisions.tsv`). The verdict list behind the counts is
`S/u35r/decrev/work_DR3/verdicts.tsv` (id, verdict, topic, line).

**How the verdicts were drawn (one rule, applied the same way everywhere).**
- A decision that *created* a mechanism the scans class H (found by reading, never observed) with no confirmed gap
  behind it, and that today's owner words reject, is **DIFF**. A decision that only settles a detail (a value, a
  test, a doc line, a sub-branch) of such a mechanism is **OBS**, with the mechanism as its root.
- A plain log line at an existing decision point (a new code, a warning text) is not a "mechanism" in L2's sense
  ("a task, a timer, a flag, a fallback or a retry; a timed check"); a counter, a flag, a key or a check is.
  That is why REG:116 (W33) and REG:120 (E27) are SAME while REG:119 (W73's counter) and REG:111 (W69's flags) are
  DIFF.
- A cheap structural form built on a mechanism confirmed in the pinned source is SAME under L2's second half
  ("a bound that costs nothing and is part of the design ... is wanted even for improbable cases"): REG:113.
- Test, twin, tooling and doc decisions that follow the landed code, model the board, or root-cause a flake are
  SAME; the audit machinery's own growth beyond its step (planted self-tests, control arms) is FORM.

## 1. Counts

206 rows: **205 decisions, 1 fact** (REG:372).

| verdict | rows |
|---|---|
| SAME | 157 |
| FORM | 7 |
| DIFF | 8 |
| OBS | 16 |
| OWN | 11 |
| SUP | 6 |
| CHECK | 0 |
| fact | 1 |

Per topic:

| topic | total | SAME | FORM | DIFF | OBS | OWN | SUP | fact |
|---|---|---|---|---|---|---|---|---|
| tests-unit | 40 | 39 |  |  | 1 |  |  |  |
| docs-records | 29 | 27 |  |  | 1 |  | 1 |  |
| process | 21 | 20 |  |  |  |  | 1 |  |
| driver-sgp40 | 14 | 9 |  | 1 | 2 | 2 |  |  |
| tests-hardware | 9 | 8 |  |  | 1 |  |  |  |
| ci-tooling | 9 | 8 | 1 |  |  |  |  |  |
| storage-fram | 8 | 4 |  | 1 |  | 1 | 1 | 1 |
| driver-scd30 | 8 | 7 |  | 1 |  |  |  |  |
| uart | 8 | 5 |  | 1 | 1 | 1 |  |  |
| twin | 8 | 7 |  |  | 1 |  |  |  |
| supervisor-reset-watchdog | 6 | 3 |  | 1 |  | 2 |  |  |
| core-logging | 5 | 2 |  |  | 2 | 1 |  |  |
| driver-other | 5 | 2 |  | 1 | 1 | 1 |  |  |
| memory-gc | 5 | 3 | 1 |  |  |  | 1 |  |
| bus-i2c-spi | 5 | 2 | 2 |  | 1 |  |  |  |
| config | 4 | 1 | 1 | 1 |  | 1 |  |  |
| error-catalog | 4 | 2 |  |  | 1 | 1 |  |  |
| webserver-rest | 4 | 2 |  |  |  |  | 2 |  |
| buildgen-toml | 4 | 3 | 1 |  |  |  |  |  |
| driver-isl29125 | 4 |  |  |  | 3 | 1 |  |  |
| ntp-dns | 3 | 3 |  |  |  |  |  |  |
| driver-bmp3xx | 2 |  | 1 |  | 1 |  |  |  |
| timing-waits | 1 |  |  | 1 |  |  |  |  |

("driver-other" holds the ALGO helpers: `math_helpers.py`, `asy_crc_checks.py`, and the base reader's typing.)

## 2. DIFF rows

**REG:111** (U11, SF-M1-01)
- As taken: one SYSTEM warning W69 `CONFIG_LOST` when the config file is absent while FRAM history survives (not
  after reset reasons 7 and 9), instead of each store persisting its absent-file line.
- New answer: no W69. An absent file is an expected condition: printed, then written once with defaults (OR136).
- Basis: A-S28 (H, triage implausible: a filesystem reformat). S2-G4-21, "An addition with its own false positive":
  OF-184 (`audit/sweeps/open_findings.md`) shows every scratch build records a false W69 in the production SYSTEM
  history. SCAN2 §3 row "W69 and its reset-reason exclusion | its own false positive | ~20 | nothing". Owner,
  2026-10-28: "building upon hypothetical findings is a clear no-go".
- Topic config; line L2 misfit.
- Change if taken: ~20 lines go (`asy_system_service.py:757-760` at head, `absent_at_boot`, the W69 reader of the
  logger's `restored`, the 7/9 exclusion). Catalog 69 is retired, SYSTEM's W band (REG:284) is left empty, about
  20 test lines in 3 files and 5 in `tests_hardware/` go, and OF-184 closes.

**REG:114** (U11, SF-A10)
- As taken: the raw reset bits are exposed undecoded as a new `/status` key `ResetBits`.
- New answer: not exposed and not read. The decoded `ResetReason` (OR60) stays the one reset diagnostic.
- Basis: A-S4 (H; OF-40: the bits cannot tell a soft reset from a hard one). S2-G4X-1, by grep: the two register
  addresses, their masks and the `mem32` read exist only to publish this key. The unit's own F.5.4 text (REG:412)
  says "the decoded reset record above is the discriminator". Owner, 2026-10-28, as above.
- Topic supervisor-reset-watchdog; line L2 misfit, L6 (a `/status` key carried by every image).
- Change if taken: ~17 lines go (src ~9, 6 generated lines, 1 emitter line) plus the definitions site row. Tests:
  1 file/4 lines, tests_scripts 1/3, the twin's register model 1/4. F.5.4's "which ResetBits mark with TIMER" and
  `get_reset_bits()` (an item of REG:344) go too.

**REG:117** (U15, SF-M3-01)
- As taken: a stale-sample bound of 10,800 s in both consumers (notification, SGP40 compensation), tunable-tagged.
- New answer: no age check at the consumers.
- Basis: owner, 2026-10-28: "hardcoded delay checks like this are a very bad, very awkward pattern" (PICTURE M2
  names "the two 10,800 s sample-age checks"). S2-G1-18 and S2-G4-10, settled from source (SCAN2 §8 check 7):
  `_store_scd()` stores `results[3]` = `utc_now()` on every not-ready cycle, so the SCD30 path the bound was meant
  for never ages; a dying producer reboots through its ladder and the task budget long before 3 h. What is left (a
  loop that stops without ending) is the watchdog's.
- Topic timing-waits; line L2 misfit, L3 misfit (a second mechanism outside the owning layer).
- Change if taken: ~12-20 lines go (`asy_notification_service.py:68-71, 231-235`, `asy_sgp40_driver.py:88-90,
  179-185`): two constants, two tunable rows, the "TS None counts as current" clauses, and REG:471's Part N row.
  NT-2's state 3 loses its "stale" reason. Tests: 2 files/6 lines and 2/4.

**REG:119** (U15, SF-B10/A04)
- As taken: a stuck-RDY warning W73 after 5 consecutive not-ready reads; the re-stamp stays.
- New answer: no W73 counter; the re-stamp (the owner's named exception) stays.
- Basis: SCD-6 (H, never observed, observability only: "the store keeps re-publishing, the owner's named
  exception"). SCAN2 §3 lists "(plus SCD-6)" with the age checks that go, with nothing staying. Owner, 2026-10-28:
  "building upon hypothetical findings is a clear no-go".
- Topic driver-scd30; line L2 misfit.
- Change if taken: ~10 lines (`asy_scd30_driver.py:90-92, 224, 429, 500-505`), the W73 catalog row (a tombstone
  under the never-reuse rule, S2-G4X-6), the `scd30.not_ready_warn_at` tunable (an item of REG:433), tests.

**REG:337** (U12, changelog B48)
- As taken: UART reads return an empty result for `nbytes` ≤ 0; writes of nothing succeed and send nothing.
- New answer: no guard; the pre-audit driver.
- Basis: UD-7 (H, "simplest alternative: pre-audit"; "no caller passes zero, by the recorded decision"). The unit's
  own A.U12.03 Why records "callers never pass a zero-length payload". Owner, 2026-10-27: "A strong hint for an
  unnecessary check is ... that it is unreachable with today's code"; owner, 2026-10-28, as above.
- Topic uart; line L2 misfit.
- Change if taken: 8 lines (`asy_uart_driver.py:535-536, 600-601, 787-788, 809-810`), their tests, and the B48
  changelog entry (Class B, so there is no C impact).

**REG:342** (U12)
- As taken: `pressure_at_height()` replaces `altitude_baro()` with no alias; `rel_humidity()` refuses outside
  0-100 % instead of clamping; the wet bulb refuses Stull's cold-dry corner.
- New answer: the rename stays. `rel_humidity()` keeps the pre-audit/legacy clamp to 0-100 %. The wet bulb keeps the
  pre-audit domain, with no cold-dry corner.
- Basis:
  - The owner's note on review `humidity-helpers-removed` ("change"): "Keep them, they are also one of the kind
    "useful, complete the functional suite, small, lightweight. Adapt the tests to be in line with the others." It
    keeps the helpers and asks for the *tests* to change, not the helpers.
  - The "no-clamp rule" exists only in agent text: OR140.a (4) ("(no quote) Integrated"), and G3/R06's "no helper
    clamps", which the unit's own Q1 option (a) recommended keeping the legacy clamp against.
  - Pre-audit `src/math_helpers.py` (25caf528) ends `return max(0.0, min(100.0, rh))`; legacy
    `legacy/firmware/python/CommonDrivers/math_helpers.py` clamps (`if rh > 100.0: rh = 100.0`) and accepts the
    whole Stull box.
  - A-H1 (H, scheme D1: "real output changed without an owner decision"); REPORT §4 item 9.
  - The same unit's REG:331: "the stored decisions keep each derived formula's legacy form".
  - CLAUDE.md working agreement: "verify against the legacy driver's own actually-proven field behavior".
- Topic driver-other; line L1 misfit (an output change nobody asked for), L7 misfit (agent text taken as an owner
  rule).
- Change if taken: ~6 lines (the corner gate and its 4 constants), ~3 lines (clamp back), REG:332's rounding
  allowance (2 lines) and their tests; SPEC M.2's domain sentence. SCD30's published `WetBulb` returns in the corner.

**REG:467** (U15)
- As taken: OF-30's raw `None` logs READ through `RuntimeError("raw signal not measured")` inside the read's `try`.
- New answer: no `None` branch at that site. At most a typing-side form, if mypy needs the narrowing (SCAN2 §9).
- Basis: SGP-18 (H, TYPING): "None comes only from a failed CRC computation of a fixed 2-byte argument" (head
  `asy_sgp40_driver.py:807-811` returns None only when `crc.add_into()` fails on the fixed command buffer). The
  S2-G1-19 family. Owner, 2026-10-27: "if the check you remove really solely covers typing breakages and nothing
  else it can go (option b)".
- Topic driver-sgp40; line L2 misfit (PICTURE M4).
- Change if taken: 2 lines (`:446-447`) and the pinning test
  `test_a_raw_signal_that_cannot_be_measured_logs_one_read_entry`. REG:436's confirmed restore fix is untouched.

**REG:485** (U16, lane-plan default A-9)
- As taken: an SGP40 backup read that is blank or CRC-invalid is a console line, not a persisted `SGP_NO_BACKUP`. The
  FRAM layer persists its own block-invalid entry, and an unreadable read keeps W65.
- New answer: as before the audit, the SGP40 keeps its own persisted "no backup" warning for a backup that fails to
  read as valid, beside the FRAM layer's own entry.
- Basis: the owner's note on review `one-entry-per-fault` ("change", 2026-10-01): "It should rather stay as is,
  upstream layers reacting to a downstream fault may encounter following errors going above the original fault, so
  getting a notion of a traceback and blast radius of an error is actually desirable." Pre-audit
  `src/asy_sgp40_driver.py:373-374` (25caf528): `if not res: wrn_s("No backup found!", wrnno=10)` for any not-valid
  read. Head `asy_sgp40_driver.py:561-564` keeps the persisted entry only for the unreadable case, the exact
  "layers above only print" shape the owner turned down.
- Topic storage-fram; line L3 misfit (the owner's blast-radius rule), L7.
- Change if taken: 1-2 lines (one `wrn_s` in the not-None branch), the U15/U16 test expectations, and REG:490's
  reflash bound +1 per SGP40 chunk. The pre-audit code persisted for a blank backup too: "stay as is" keeps that,
  and the cleanup may still keep a first boot's blank read print-only.

## 3. OBS rows

| id | root it depends on (scan row) | topic |
|---|---|---|
| REG:118 | BMP3XX power-on-reset detection and re-apply: BMP-1 (H; after a POR the chip runs at its defaults and forced mode is rewritten every cycle, "no wrong value, hang or loss"); W71 in S2-G3-7 | driver-bmp3xx |
| REG:284 | W69 `CONFIG_LOST`: A-S28 (H), S2-G4-21 (its own false positive, OF-184); the W24 retirement and W22's text stand | error-catalog |
| REG:332 | the no-clamp `rel_humidity()`: A-H3 (agent text, REG:342 DIFF), A-H4 (C) | driver-other |
| REG:350 | the SPI/FRAM "no bus" contract: S2-G1-3, S2-G4-4 (no SPI rung; rp2's SPI object is static, `ports/rp2/machine_spi.c:111, 166`) | tests-unit |
| REG:352 | the participant rung guarded twice: S2-G1-22 (the hooks' contract "never a raise", `asy_base_classes.py:658-659`); S2-G4X-3 (E14 then has no user) | bus-i2c-spi |
| REG:362 | closed-channel guards inside the DMA ring: S2-G2-11 ("verified by reading as unreachable in the product": `close()` only in `setup_rx_ring()`'s failure arm, which drops both references) | uart |
| REG:373 | the SPI bool contract: S2-G1-3, S2-G4-4 ("The SPI bools have no reader") | tests-hardware |
| REG:378 | the log store's write lock and generation count: A-P8 (H; "the lock hand-off is FIFO at the pinned version, so the newest state already landed last") | core-logging |
| REG:397 | the same `_write_lock`: A-P8 | docs-records |
| REG:443 | ISL29125's per-cycle shadow verify `_check_divergence()`: ISL-10 (H; the datasheet's only causes are a reset or brownout, already handled) | driver-isl29125 |
| REG:448 | the twin's POR flag exists for BMP-1 (H) | twin |
| REG:458 | W75 `ISL_CAL_TIMEOUT`: ISL-9 (H; W75 in S2-G3-7); the `_verify_config()` naming: ISL-10 | driver-isl29125 |
| REG:463 | "status read first" and the expiry checks: ISL-10 and ISL-8 (H, implausible) | driver-isl29125 |
| REG:471 | Part N `sgp40.comp_max_age_s`: the age bound SGP-2, S2-G4-10 (REG:117 DIFF); `sgp40.self_test_wait_ms` stands | driver-sgp40 |
| REG:488 | the pre-setup merge: A-P2 and S2-G1-15 (unreachable through the generated boot order); its outcome for a clean read, no write, is the pre-audit behaviour and stays | core-logging |
| REG:489 | the restart keeps live VOC state: SGP-12 (H; "the pre-audit restart restored a backup at most one BackupPeriod old") | driver-sgp40 |

These H roots are in neither REPORT §3's confirmed gaps nor the owner's decisions. The target state the owner was
offered (REPORT §6 point 5: pre-audit code plus the §3 fixes plus the decided features) leaves them out, and the
owner's background (PICTURE §8) keeps these decisions documented as general knowledge.

## 4. FORM rows

| id | the smaller form | scan row | topic |
|---|---|---|---|
| REG:295 | `_closed_for_reset()` keeps only the under-lock check; the pre-lock one goes ("the under-lock one decides"). The commit flag goes with the deferred flush's smaller form: one `write_config()` after the push loop, ~30 lines go and ~3 stay, the owner's `failed-push-no-flash-write` "ok" kept whole | S2-G1-13; SCAN2 §3 "owner decisions in far less code", §7 item 1 | config |
| REG:345 | no per-bus 200,000 µs ceiling and no `i2c.timeout_max_us` tunable: the boot-clear budget (REG:346) holds the condition alone. The 1 µs floor is plain TOML input validation and may stay | S2-G3-1 ("Either way the other check holds the condition alone"); G3 keep list "`bus.boot-clear-budget` alone" | buildgen-toml |
| REG:347 | one clock-out routine for both clears, with an injected wait, instead of the 31-line `_clear_bus_awaiting()` copy. The SCL wait itself stays: waiting for a released SCL is ordinary I2C clock synchronisation, and the SCD30 stretches up to 150 ms (`SPECIFICATION.md:739`). This corrects C.md I2C-1's MIN note, which counted the waits as excess | REPORT §5 "I2C clear"; C.md I2C-2 (X), minimal-change list I2C-2/3 | bus-i2c-spi |
| REG:351 | the `addrsize` refusal goes with the register-write preassembly. I2C-6's minimal form is `buf = bytes((reg_addr,)) + payload` plus the ACK-count compare ("every driver uses 8-bit addresses"), ~4 lines for the confirmed NACK gap | C.md I2C-6 (X) and its minimal-change entry; REPORT §5 "I2C short-ACK write path ~35 → ~4" | bus-i2c-spi |
| REG:386 | the tick-wrap scan as its step asked (every tick user, the arithmetic rule), without a planted negative per rule | E.md tests_scripts "Excessive: 100 'bite/planted' self-tests in 58 files"; owner 2026-10-23: "Planting errors for those straightforward tests would be complete overkill"; owner 2026-10-28: "The audit verification machinery is just a temporary tool" | ci-tooling |
| REG:446 | `_apply_stored_config()` answers a bool. The third value only routes `_init_failed()` (H/OV) and the POR re-apply (BMP-1, H); the participant rung reads `== _APPLIED` (head `asy_bmp3xx_driver.py:232-235, 280, 333`) | S2-G1-4; C.md BMP-1 | driver-bmp3xx |
| REG:492 | the check measures the firmware's placement (stays), on all six devices with the live bounds, without the control arm, its live-versus-suppressed ratio and the two control guards | owner OR21.a: "yes, but the control arms are overkill"; E.md tests_scripts (bite/planted family) | memory-gc |

## 5. OWN rows

| id | the owner's words, source | does what was built follow? gap |
|---|---|---|
| REG:278 | OR136 (2026-10-01): "if the file is genuinely missing, it shall be written once with defaults." | Yes (A-C2 R). It supersedes the earlier "writes nothing" text, as the row says |
| REG:283 | OR120 (2026-09-30): "Probably it's best to completely stop the loop feeding the watchdog, really making sure it actually IS stopped" | Yes (A-S12 R). The `finally` cancel serves callers that cancel only the outer task, which are tests and the twin; no product cost |
| REG:285 | owner, 2026-10-07, on the lead's handler design: "Yes, build it that way. And test it thoroughly, hammering, ..."; Q6: "Option a" (silent at level 0, `owner_rulings_after_LN118.md`) | The handler and its level gate follow (S2-G4X-7: keep). Gap: "installed only when no handler is set" exists for the PC tiers (the code's own comment, `asy_system_service.py:776`; S2-G1-11, one condition line). The row does not show whether that guard was part of the approved design; recorded as a fact in §7 |
| REG:292 | OR120: "... feeding it inside the sequence doing the reset work. So neither the watchdog inteerrupts the sequence, nor is there any risk the watchdog is fed although something hangs." | Yes: an armed reset stops every feed. It relies on the same confirmed drop mechanism (V8) as REG:113, consistently |
| REG:331 | owner, 2026-10-07: "Adapt the humidity to the verified range" | Yes for the form and the −30..40 °C domain. The 237.4 → 237.3 digit is the agent's reading of "verified" (A-H2 R); noted, not a gap |
| REG:334 | OR101: "My decision: Fix the bugs" (D4.37 in OR101.a's list; VOC-1 R) | Yes. The reference-vector sources are the agent's choice, SAME |
| REG:340 | OR109: "Latent SGP40 race: Fix this. No races allowed (see specs)." | Yes (SGP-4 R; the minimal form adds 0 lines) |
| REG:355 | OR141: "UART in the DMA ring buffer, but keep a strict eye on how that integrates with the heap allocation and fragmentation"; OR146 (overflow must reach the sender) | Yes (UD-1 R). Form: S2-G2-11's ~11 lines of closed-channel and deinit-mid-read guards go (REG:362 OBS); the re-init re-arm stays as a library feature |
| REG:441 | review `state-code-values` "ok": "VOCState: 0 blackout (first 46 samples), 1 learning (first 24 h after a fresh start), 2 settled, 3 restored from backup (first 24 h)." | **Gap:** the catalog reads "learned (past the 24 h learning time)" for 2 (`buildgen/error_catalog.json` `status.VOCState.2` at head). The decision-vocabulary check, temporary machinery, renamed the owner-approved word. The owner's text stands |
| REG:457 | OR109: "No races allowed (see specs)." | Yes (ISL-3 R) |
| REG:487 | owner, 2026-09-16: "we do not even add errno/wrnno for the out of FRAM memory … Handle via mpremote." | Yes for the refusal (A-P15 R): `FRAM_FULL` dropped, no counted entry. **Gap:** the `LOG_RAM_ONLY` (E28) retention in the same row is not covered by those words. A-P3 is H, and S2-G4-8/G4R07 judge its per-run `_write_failing` flag an episode flag ("`_keep()` alone"). The smaller form keeps one E28 at setup for an unreadable store (a rare but real case in scope; the owner's blast-radius note supports that entry), without the run flag or the heap-failure arm (A-P15's heap half, H) |

## 6. SUP and CHECK rows

**SUP**

| id | superseded by | does the later one stand? |
|---|---|---|
| REG:112 | REG:487 (U16): `FRAM_FULL` dropped under the owner's 2026-09-16 words | Yes (owner). REG:112's `LOG_RAM_ONLY` half is carried into REG:487's gap note |
| REG:297 | U27 `15b8633c` removed `parse_cmd_request()` (A-A3 R: OR46.a (2) "confirmed leftovers … are removed"; grep at head: no occurrence) | Yes |
| REG:298 | U19's `checked_int(payload, _PAUSE_TIME_FIELD)` at head `asy_webserver_service.py:770`, validation of real REST input | Yes |
| REG:343 | owner, 2026-10-27, on D.15: "Option d is fine" (the sweep at U37; lanes order only their own new code) | Yes. The U12 reorders were pure and AST-checked, so nothing to undo |
| REG:393 | A.U18.12 / UDP-1 (R, OR36.a): `UDPSocket` takes only a `(host, port)` tuple (head `asy_udp_socket.py:42-43`) | Yes. **Records gap:** `SPECIFICATION.md:7450` at 11b66cd8 still reads "never in `src/`, except the one accommodation row 1 names", while row 1 itself says `UDPSocket` "refuses anything else": the sentence is stale |
| REG:484 | U18's console line for `RegionBuffer`'s failed allocation (A-B18; M.SRC_CORE.027 (1)) | **No.** The later line is a memory-gate console line, P4 (S2-G1-9; OR36 "zero artifacts specifically added for testing"). REG:484's silent `None` with one comment is the answer that fits today |

**CHECK:** none. Three rows looked suspicious and were settled statically:
- REG:113: the pinned source confirms a full scheduler queue drops a soft one-shot (V8), and the pre-audit F.1/C.9
  rule already named a must-fire one-shot a hazard. The deadline adds no object. SAME.
- REG:347: the SCD30's documented 150 ms clock stretch makes the SCL wait ordinary master behaviour. FORM.
- REG:490: an owner-words reading, not a check; recorded as a fact in §7.

## 7. Contradictions, and the likely counterparts in other sets

**Pairs that cannot both hold (14):**
1. REG:342 vs review `humidity-helpers-removed` (owner note "Keep them ... Adapt the tests to be in line with the
   others."). The owner's side stands: the helpers stay as they were and their tests adapt.
2. REG:342 vs REG:331 (same unit: "the stored decisions keep each derived formula's legacy form"). REG:331's rule
   stands; legacy and the pre-audit code clamp.
3. REG:441 ("learned") vs review `state-code-values` "ok" ("2 settled"). The owner's side stands.
4. REG:485 (the upper layer only prints) vs review `one-entry-per-fault` (owner "It should rather stay as is ...").
   The owner's side stands.
5. REG:112 (`FRAM_FULL` entry) vs owner 2026-09-16 ("we do not even add errno/wrnno for the out of FRAM memory").
   The owner stands; REG:487 already resolved it.
6. REG:117 (age bound) vs REG:119 (the re-stamp stays) and review `stale-as-fresh-every-driver` "ok". The re-stamp
   keeps every SCD30 sample fresh, so the bound never sees the path it was built for (SCAN2 §8 check 7). The
   owner's exception stands; REG:117 goes.
7. REG:345 vs REG:346: one condition checked twice. S2-G3-1: the budget alone holds it, so REG:346 stands.
8. REG:484 vs U18's `RegionBuffer` console line (another set). REG:484 stands (OR36).
9. REG:393 vs A.U18.12 (another set). The later removal stands; the F.7 sentence is stale.
10. REG:473 vs review `sgp40-cadence-ram` (unanswered, an agent decision: "sets its backup period in RAM, so it
    needs no persisting write"). REG:473 records that a RAM-only override is impossible without a config write;
    REG:473 stands (a fact), and the review text is stale. OF-55 (a persisting defaults write on a board missing a
    config file) is the open consequence.
11. REG:492 (control arm kept) vs OR21.a ("the control arms are overkill"). The owner stands, hence FORM.
12. REG:386 (a planted negative per rule) vs owner 2026-10-23 ("Planting errors for those straightforward tests
    would be complete overkill"). The owner stands, hence FORM.
13. REG:337 (a zero-length guard) vs the same unit's A.U12.03 record "callers never pass a zero-length payload".
    The record stands, hence DIFF.
14. REG:352 (a return after a raising hook's CALLBACK entry) vs the hooks' own contract "never a raise"
    (`asy_base_classes.py:658-659`). The contract stands, hence OBS.

**Owner statements that seem to pull apart. Facts for the lead, no question framed:**
- **F1, REG:490.**
  - OR56 (2026-09-26): ""each UART fault writes an error entry and a warning entry into one shared log" - that's
    already conceptually wrong. Either it's a fault or a warning, but never both at a time. That is common sense
    and should be globally checked and applied."
  - The later `one-entry-per-fault` note (2026-10-01): "It should rather stay as is, upstream layers reacting to a
    downstream fault ...".
  - Facts: for one CRC-invalid block, FRAM's own logger gets an E (`_read_chunk`, head `asy_fram_manager.py:334`)
    and a W (`_read`, `:236`/`:244`); both use `self.pr = manager.pr` (`:86`). The pre-audit code did the same
    (A.md V1: "E31 twice, W71, W72"). `tests_scripts/test_fault_or_warning_never_both.py` judges per function
    ("other functions' entries pass", its docstring), so it never sees this pair. REG:490's bound of 4 per chunk
    encodes it. The 10-01 note is the owner's most recent word on layering.
- **F2, REG:285.**
  - The owner's 2026-10-07 approval of the lead's handler design.
  - OR36: "contains zero artifacts specifically added for testing".
  - Facts: the "only when no handler is set" guard exists for the PC tiers (`asy_system_service.py:776` comment;
    `digital_twin/unix_port_unretrieved_report.py:24` installs one first). SPECIFICATION.md places the owner's quote
    right after that clause (`:6549`), but the row does not record the proposal text the owner answered.

**Consistency across my set:** REG:113/REG:279 and REG:292 both rest on V8's confirmed drop, consistently. The
log-line versus mechanism rule (§0) separates REG:116/REG:120 (SAME) from REG:111/REG:119 (DIFF). REG:117 DIFF and
REG:471 OBS go together, as do REG:342 DIFF and REG:332 OBS, and REG:114 DIFF with REG:344's `get_reset_bits()` item.

**Likely counterparts in other sets (by their words):**
- **Review page:**
  - `humidity-helpers-removed`: REG:331, REG:332, REG:342.
  - `state-code-values`: REG:441.
  - `one-entry-per-fault`: REG:485, REG:487, REG:490.
  - `failed-push-no-flash-write`: REG:295.
  - `reset-reason-codes`: REG:115 (code 21), REG:114.
  - `system-command-sequence-details`: REG:276, REG:283, REG:292.
  - `stale-as-fresh-every-driver` and `timestamps-before-ntp`: REG:117, REG:119, REG:454.
  - `scd30-calibration-readiness`: REG:450-452.
  - `negative-backup-age`, `sgp40-wait-zero`: REG:116, REG:472.
  - `sgp40-cadence-ram` (unanswered): REG:473.
  - `envelope-codes-equal-http`: REG:277.
  - `unreadable-config-file` and OR136: REG:278, REG:293.
  - `driven-time-and-rtc-steps`: REG:427, REG:428.
  - `heap-floors-kept`: REG:478, REG:492.
  - `uart-flash-erase-overrun` and OR141/OR146: REG:355-358.
  - `c-stack-reboot`: REG:433's "`report_if_fatal()` omitted until U30".
- **Other units' register rows:**
  - U10's mempause row (A.U10.15, G5/R08): REG:113, REG:279.
  - U17's UART rows (readline cap, PieceBuffer): REG:337, REG:344, REG:362.
  - U18's console-rules row (M.SRC_CORE.027 (1)): REG:484.
  - U18's UDP row (A.U18.12): REG:393.
  - U19's pause dispatch and envelope codes: REG:298, REG:277.
  - U20's `ResetBits` key, boot entry, emergency buffer and `ResetReason` wording: REG:114, REG:405, REG:411,
    REG:412.
  - U27's `parse_cmd_request()` removal: REG:297.
  - U31's buildgen I2C checks (D-H17/H18): REG:345, REG:346.
  - U35's loop-end code 22 (F4b): REG:115.
- **Owner rulings:** the D.15 "Option d" ruling (REG:343, REG:370); the catalog's never-reuse rule, agent text (SCAN2
  §9), which REG:284, REG:438 and REG:458 feed with tombstones.

## 8. SAME rows (one line each)

| id | topic | a few words |
|---|---|---|
| REG:113 | storage-fram | mempause ends by a deadline on the existing 1 s pass; a Timer, task and flag fewer; V8 confirms the dropped one-shot; a cheap bound by construction (L2) |
| REG:115 | supervisor-reset-watchdog | code 21: the loop-end label is a confirmed gap (REPORT §3; SCAN2 §7 item 6); extends the owner-reviewed table |
| REG:116 | driver-sgp40 | restore as legacy; W33 is one log line at an existing branch (SGP-10, not on SCAN2's go list) |
| REG:120 | error-catalog | one shared out-of-range code across drivers (L5); the gate itself is OR101's |
| REG:122 | driver-scd30 | recorded as an open finding; no code, no bench write |
| REG:276 | process | staging of the owner-decided reset path (A-S6..A-S13 R) |
| REG:277 | webserver-rest | codes 4/5/100 staged to U19; end state is the `envelope-codes-equal-http` "ok" |
| REG:279 | storage-fram | the REG:113 deadline; the bool is the `mempause` command's REST answer (`codegen.py:254`) |
| REG:280 | uart | changelog numbering |
| REG:281 | process | steps named with the unit that lands them |
| REG:282 | docs-records | current-state documentation rule |
| REG:286 | core-logging | the report lives with the logger, the one module that prints |
| REG:287 | core-logging | nested try costs one line; its None-context reason is typing-only, unrowed by the scans |
| REG:288 | tests-unit | handler restore, test placement, stub types |
| REG:289 | tests-hardware | gates read SYSTEM's log before any clear (CLAUDE.md FRAM rule); read-only |
| REG:290 | supervisor-reset-watchdog | slot emptied after logging: C of A-S13 (R, OR130); upstream note fits "later and bundled, if at all" |
| REG:291 | tests-unit | root-caused scheduling dependence; no product change |
| REG:293 | config | SYSTEM's unavailable marker, K for legacy parity (A-B8; S2-G4-17 keeps it) |
| REG:294 | tests-unit | static schema check matches the real records |
| REG:296 | tests-unit | the fake follows littlefs `remove` |
| REG:299 | ci-tooling | a needed type ignore stays |
| REG:300 | tests-unit | route tests scope by the groups' field tuples |
| REG:301 | tests-unit | fakes model the board (real `LockableBuffer`, allocator's None) |
| REG:302 | tests-unit | an underscore `const()` is no module attribute: local mirrors |
| REG:303 | tests-unit | nested groups accepted per SPEC M.1 |
| REG:304 | tests-unit | staging to U20 |
| REG:305 | tests-hardware | today's script form; the status pass drives the deadline |
| REG:306 | ci-tooling | explicit-Any baseline only shrinks |
| REG:307 | tests-unit | a scenario that never made its write now does (biting) |
| REG:333 | driver-sgp40 | verified against the C reference; no clamp added |
| REG:335 | driver-sgp40 | names over literals, same values |
| REG:336 | driver-other | CRC32 small-int form: confirmed efficiency gap (V4; "~22 lines, or leave it") |
| REG:338 | tests-unit | the allocation-failure test keeps its target |
| REG:339 | memory-gc | Part I figure per width, from the code |
| REG:341 | tests-hardware | today's script form, bounded under the watchdog |
| REG:344 | process | 30 conservative lane defaults; its `get_reset_bits()` item goes with REG:114 |
| REG:346 | buildgen-toml | the one boot-clear check G3 keeps (S2-G3-1) |
| REG:348 | tests-unit | deterministic SCL-held tests without fake time |
| REG:349 | tests-unit | exact write-half fault injection |
| REG:353 | bus-i2c-spi | the STOP after a failed no-stop write is in I2C-7's minimal form |
| REG:354 | twin | ladder scenario that fails a lockless mutant |
| REG:356 | uart | ring armed before the boot drain (OR141 ring) |
| REG:357 | uart | a re-init marks an overrun (OR146); re-init is a library feature (S2-G2-11 keep) |
| REG:358 | uart | follows the ring: `machine.UART` never sees `rxbuf` |
| REG:359 | uart | no change to `read()` |
| REG:360 | tests-unit | hazard tests follow the ring |
| REG:361 | tests-unit | DMA registry reset per build |
| REG:363 | tests-unit | fixed-occupancy fake logs; honest retention checks |
| REG:364 | twin | verified `deque` fact; uncounted drops now counted |
| REG:365 | tests-unit | per-construction I2C fake |
| REG:366 | tests-unit | fake Pin latch read |
| REG:367 | tests-unit | capped fake log, measured placement effect |
| REG:368 | twin | held lines are kept twin fidelity (E.md twin "Keep") |
| REG:369 | tests-unit | estimated test parameters |
| REG:370 | process | staged to OF-42; D.15 later under "Option d" |
| REG:371 | docs-records | docs follow the landed code |
| REG:374 | ci-tooling | outside-set lists only shrink |
| REG:375 | process | gate race root-caused (OF-41) |
| REG:376 | docs-records | union of sites in one SPEC row |
| REG:377 | tests-unit | root-caused by stall injection; no product defect |
| REG:379 | docs-records | merged comment kept |
| REG:380 | ntp-dns | the comment matches what the catch does |
| REG:381 | docs-records | placement of a merged comment |
| REG:382 | twin | comment cites the right F.7 row |
| REG:383 | tests-unit | section header kept until U18 |
| REG:384 | docs-records | the upstream issue link kept |
| REG:385 | ci-tooling | tick-users list in repo paths |
| REG:387 | tests-unit | the fake raises as the board does (`extmod/modtime.c:178-196`) |
| REG:388 | tests-unit | pointers follow the rewritten header |
| REG:389 | tests-unit | pins `TickSeconds`' horizon (A-B4 R) |
| REG:390 | docs-records | pointer timing |
| REG:391 | tests-unit | expectation follows the boot clear |
| REG:392 | tests-unit | two wrap crossings, tests only |
| REG:394 | docs-records | F.9 cell unchanged |
| REG:395 | docs-records | F.5.1 wording made true |
| REG:396 | docs-records | D.2 made true; actor tag |
| REG:398 | memory-gc | figure not re-measured: lanes may not build |
| REG:399 | docs-records | traced sqrt fact, false claim dropped |
| REG:400 | docs-records | an unopened source is not cited |
| REG:401 | docs-records | a measured-false claim not written |
| REG:402 | docs-records | claims follow the pin |
| REG:403 | docs-records | settings classified by use |
| REG:404 | docs-records | measured `MICROPY_ASYNC_KBD_INTR` stated |
| REG:405 | memory-gc | "can be empty"; the emergency buffer is a confirmed gap fixed at U20 |
| REG:406 | docs-records | a recorded decision keeps its scope (L7) |
| REG:407 | ci-tooling | lists only shrink |
| REG:408 | process | the lead runs the build lanes may not run |
| REG:409 | process | staging to U18 |
| REG:410 | process | staging to U19 |
| REG:411 | process | staging to U20 |
| REG:412 | supervisor-reset-watchdog | F.5.4's `reset_cause()` sentence is scoped and labelled "(agent, 2026-09-29)" |
| REG:413 | docs-records | fake clauses wait for the fakes |
| REG:414 | docs-records | only the proof clause changes |
| REG:415 | docs-records | one home per fact |
| REG:416 | tests-unit | `ticks_us()` in the fake |
| REG:417 | tests-unit | file-local helper until U24 |
| REG:418 | ntp-dns | no false "2037" text left |
| REG:419 | ci-tooling | staged to U21, corrected there |
| REG:420 | tests-hardware | one owed measurement row |
| REG:421 | process | claims re-read on merged code |
| REG:422 | process | an item that lands nothing |
| REG:423 | docs-records | NDEBUG fact; no false clause |
| REG:424 | docs-records | stages kept; mechanism sentence re-run |
| REG:425 | ntp-dns | existing ALLOC code; staging to U18 |
| REG:426 | tests-unit | a comment citing removed helpers goes |
| REG:427 | tests-unit | real 2**30 wrap crossings |
| REG:428 | tests-unit | every tick user tested; within `driven-time-and-rtc-steps` "ok" |
| REG:429 | docs-records | `utc_now()` stated; "published" staged |
| REG:430 | docs-records | edited in place |
| REG:431 | process | no lane edits a file another running lane edits (OR107) |
| REG:432 | process | pointers by file owner |
| REG:433 | process | conservative defaults; its ERR_REG burst and `scd30.not_ready_warn_at` items go with REG:118/REG:119 |
| REG:434 | process | no early start (OR107) |
| REG:435 | process | smallest corrections, stages kept |
| REG:436 | driver-sgp40 | OF-30's restore fix is the confirmed SGP-17 gap (REPORT §3, 3 lines); its raw-None half is REG:467 |
| REG:437 | driver-scd30 | no new code; a physical-domain None stays unlogged |
| REG:438 | error-catalog | numbering; W71/W73/W75 follow their mechanisms (S2-G3-7) |
| REG:439 | buildgen-toml | tags name their tables |
| REG:440 | bus-i2c-spi | type-only narrowing |
| REG:442 | tests-hardware | end-form script with a type-check stub; no run before U26 |
| REG:444 | twin | follows SCD30's RAM-only config log (OR99 "no extra FRAM chunk") |
| REG:445 | driver-other | bare class annotations, type-only |
| REG:447 | process | commit composition |
| REG:449 | tests-unit | real sibling wiring (bus-hazard rule) |
| REG:450 | driver-scd30 | FRC readiness detail under OR99 / review "ok" |
| REG:451 | driver-scd30 | FRC reset after the participant rung's soft reset |
| REG:452 | driver-scd30 | FRC window and idle-path details |
| REG:453 | driver-scd30 | bounds a chip-read value used in arithmetic |
| REG:454 | driver-scd30 | capture rule (`stale-as-fresh-every-driver` "ok") |
| REG:455 | twin | in-process cycles until U24 |
| REG:456 | buildgen-toml | one schema source for `ContMeas` |
| REG:459 | docs-records | wording only |
| REG:460 | tests-unit | file-local CONFIG helper (OF-53) |
| REG:461 | tests-unit | test-side deadline handling |
| REG:462 | tests-unit | local imports go |
| REG:464 | driver-sgp40 | comment, names, placement |
| REG:465 | driver-sgp40 | a schema bound; real inputs are gated to Table 10 first (SGP-3) |
| REG:466 | driver-sgp40 | split for the complexity limits |
| REG:468 | driver-sgp40 | `TYPE_CHECKING` NamedTuple kept |
| REG:469 | driver-sgp40 | staging of REG:116's warning |
| REG:470 | tests-unit | root-caused sleep patch |
| REG:472 | docs-records | documents `negative-backup-age` |
| REG:473 | tests-hardware | fact: no RAM-only override; outdates `sgp40-cadence-ram` |
| REG:474 | tests-hardware | typed tick store |
| REG:475 | docs-records | machinery-forced wording, no meaning change |
| REG:476 | process | partial landings named |
| REG:477 | process | cross-lane reds, no `src/` behaviour change |
| REG:478 | webserver-rest | pins re-derived, not loosened (the `heap-floors-kept` principle) |
| REG:479 | tests-unit | device taken from the TOMLs (owner 2026-10-23) |
| REG:480 | ci-tooling | lists only shrink |
| REG:481 | twin | planted defects in a complex ladder test (allowed by owner 2026-10-23) |
| REG:482 | ci-tooling | a stub read as Python |
| REG:483 | process | lane defaults |
| REG:486 | tests-hardware | today's script form, U26 converts |
| REG:490 | storage-fram | the bound follows the per-layer entries the owner's "stay as is" keeps (§7 F1) |
| REG:491 | storage-fram | never rewriting the chip's NVM unasked fits OR70 (3); E53 itself is H (A-D4) |
| REG:493 | tests-unit | leak test with a planted retention (planting is allowed for leaks) |

**Fact (no verdict):** REG:372, the FRAM electrical figures read from the datasheet PDFs. C.3.1's sentence matches.
