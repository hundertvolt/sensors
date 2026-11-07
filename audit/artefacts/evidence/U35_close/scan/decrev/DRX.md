DRX crosswalk, written by the part (Wed Oct 28 12:36:00 UTC 2026)

# DRX: the eight decision-review parts in one view

Input: `DR1.md`-`DR8.md`, the per-row tables (`dr5work/verdicts.tsv`, `work_DR3/verdicts.tsv`, `DR4_work/entries.tsv`,
`dr7work/DR7_rows.tsv`), the lead's extract `inputs/owner_words_lane_plan.md` (read first) and, where a quote needed its
context, `S/u35/lane_plan.md` LEAD NOTES 80-367 and `recovered/owner_rulings_after_LN118.md`. Static only: `git show`
and `git grep` at `11b66cd8` (product tree `497b3eda`), `25caf528` for the pre-audit form, the pinned MicroPython
v1.29.0 source. Nothing ran; nothing in the repo, a worktree or an earlier file changed. The totals script is
`S/u35r/decrev/drx_work/totals.py`.

Sections: 0 the extract's re-settled rows; 1 chains; 2 verdict conflicts; 3 contradictions across parts; 4 seeds;
5 the DIFFs as one set; 6 merged CHECKs; 7 totals.

## 0. Rows the extract's owner words re-settle

The extract's 56 entries hold about 30 real owner quotes; the rest are fragments of lead text (entries 1-5, 17, 42),
the lead's own questions (13, 19, 25, 28, 31) or code text (22). Each re-settled row, with the quote and its note:

| row (part) | was | now | the owner's words (LEAD NOTE) |
|---|---|---|---|
| SPEC:1898, CI mirror rate (DR8) | DIFF | OWN | "The CI failures are there for several days as far as I remember ... Maybe it actually would be good to investigate." (LN320); "What about option 3 plus cache? Is there something adversarial to using the cache?", then "Yes do it like you proposed" (LN322). The derived rate is the lead's fix inside that mechanism, "the owner's "do it like you proposed" covers making the mechanism work" (LN334). DR8's 16:48 quote was overtaken the same evening |
| SPEC:1923, cache integrity (DR8) | DIFF | OWN | LN322: the cache question was answered on integrity ("integrity via the signed index") before "Yes do it like you proposed" |
| SPEC:2607, SPEC:7556, `toolchain/micropython_overrides.py:468`, the third modlwip patch (DR8) | SAME | OWN | "Only two lines swapped? Take it as the third one." (LN164) |
| SPEC:2732, the patch's retirement condition (DR8) | SAME | OWN | "fix in the patched version and monitor upstream for real fixes, as soon as upstream is fixed drop the patch." (LN155) |
| SPEC:695, `src/asy_system_service.py:175`, loop-end 22 (DR8) | SAME | OWN | "OF-107: Handle it as you suggested" (LN163); "Event loop fallback: option b is fine." (LN166) |
| LN358, the lost cancel checked first (DR6) | SAME | OWN | "Check this first, especially if it is real at all" (LN358) |
| LN355, the overlay patch kept out of the tree (DR6) | SAME | OWN | "it's rather a structural issue and not something to patch over like that" (LN358); "trying to debug the Micropython sources,which could not be more out of our scope" (LN362) |
| LN357, CMr1n and RF1 kept (DR6) | SUP | OWN | "I don't actually want to cut back or trade anything, I just want to make sure that you set up the process such that it can finished and is not designed self-sustaining / will never end" (LN357); not superseded, see section 2, V1 |
| `closing_ledger.md:8` (items 1-7), `owner_report_items.md:159` (CMr1n), REDO.md:68 (CM3, CM4), LN349 (IN2) (DR6) | DIFF | OWN | LN357, as above |
| REDO.md:59 (RF1), REDO.md:60 (CRr2c, CRr2d), REDO.md:72 (B2r), `owner_report_items.md:71` (REC2) (DR6) | DIFF | DIFF, ledger part OWN | the finished or process parts stay DIFF; the parts on ledger items 2, 4, 6 and 9 are covered by LN357 |
| REG:574 (DR4) | SUP | SUP | stands; the words DR4 could not find are LN155's |

Confirmed, not changed, by the extract:
- **The NeoPixel 300 s rewrite** (REG:121, REG:878, SPEC:12106, `asy_neopixel_driver.py:37`, SPEC:410, REG:596b,
  `owner_report_items.md:232`, `one-timeout-mechanism`). The owner's full words (LN362, 06:37) are about this check:
  "I completely don't understand what lead you to implementing a pattern like that arbitrary 5 minutes check. That's high
  complexity on a limited device, undesirable as such. At least as far as I understand, it patches a rather hypothetical
  issue instead of cleanly and minimally implementing something clean. And anyhow, hardcoded delay checks like this are a
  very bad, very awkward pattern." The lead's LN358 check stands as the verified fact: legacy awaits the flag with no
  timeout, and the 300 s value is the default FlashInterval, an agent choice. The lost cancel was reproduced 8/8 on the
  pinned Unix port (`extmod/asyncio/funcs.py:47-50`). The DIFFs stand. The revert to the pre-audit `await ...wait()` is
  the minimal consequence, but the owner did not choose that form, so no row becomes OWN. LN360 lists "whether to keep the
  periodic rewrite" as an open owner question; the 06:37 words answer its substance.
- **REG:792** (13-15 lanes, DIFF) holds: "1 or 2 more parallel works are still fine" (item 80, 2026-10-22) allows one
  or two more works at that moment, not 13-15 lanes.
- **REG:798**, **REG:801**, **REG:795/a** OWN hold (items 89, 95; LN176).
- **REG:795/i, /j, /k** stay agent decisions. LN96 reads "Kept by lead decision under the owner's no-regression
  condition". The owner's condition ("as long as their intended behavior and resilience are either unaffected or even
  improved", LN96; "no regressions, also no hidden ones", LN97) binds every change but keeps nothing by itself.
- **REG:804/805** OWN holds ("So with this, you can continue and fix the issues cleanly?", LN107; "Solutions you
  proposed agreed.", LN111). **LN113** OWN holds ("Fine, keep it.", LN115).

## 1. Chains (one decision in several sets)

Format: members with the verdict each part gave → the settled verdict. TRACKED rows of DR8 are named in brackets; they
add no verdict. 84 chains, 240 member rows.

| # | topic | members → settled |
|---|---|---|
| K01 | led-notification | NeoPixel 300 s rewrite: DR2 REG:121 DIFF; DR6 REG:878 DIFF; DR7 SPEC:12106 OBS; DR8 `asy_neopixel_driver.py:37` DIFF → **DIFF** |
| K02 | led-notification | 10,800 s sample-age checks (SF-M3-01): DR3 REG:117 DIFF; DR6 REG:870 DIFF; DR7 SPEC:12110, SPEC:12122 OBS [DR8 `asy_notification_service.py:69`, `asy_sgp40_driver.py:88`] → **DIFF** |
| K03 | driver-scd30 | W73 stuck-RDY counter: DR3 REG:119 DIFF; DR6 REG:846 DIFF; DR7 SPEC:12115 OBS → **DIFF** |
| K04 | driver-bmp3xx | POR detector (SF-B9, SF-A05): DR6 REG:833, REG:847 DIFF → **DIFF** |
| K05 | supervisor-reset-watchdog | `ResetBits` (SF-A10): DR3 REG:114 DIFF; DR6 REG:852 DIFF [DR8 SPEC:7096] → **DIFF** |
| K06 | config | W69 CONFIG_LOST (SF-M1-01): DR3 REG:111 DIFF; DR6 REG:864 DIFF [DR8 SPEC:3900] → **DIFF** |
| K07 | driver-isl29125 | shadow compare each cycle (SF-M3-04): DR6 REG:874 DIFF; DR8 SPEC:11638 DIFF → **DIFF** |
| K08 | driver-isl29125 | W75 calibration timeout (SF-B11): DR6 REG:835 DIFF; DR8 SPEC:11754 SAME → **DIFF** (V4) |
| K09 | driver-sgp40 | restart keeps live VOC state (SF-M3-05): DR6 REG:875 DIFF; DR3 REG:489 OBS [DR8 SPEC:375] → **DIFF** (V22) |
| K10 | storage-fram | E28 LOG_RAM_ONLY (SF-B12, SF-M1-03): DR6 REG:836, REG:865 DIFF; DR3 REG:112 SUP → **DIFF** (V7) |
| K11 | led-notification | notification `State` key (SF-B17): DR6 REG:841 DIFF; DR8 SPEC:422 DIFF → **DIFF** |
| K12 | config | `ConfigUnpersisted` (SF-B3, SF-M1-07): DR6 REG:827, REG:866 DIFF → **DIFF** |
| K13 | driver-bmp3xx | BMP3XX out-of-range code E27 (SF-M3-02): DR3 REG:120 SAME; DR6 REG:872 DIFF → **DIFF** (V5) |
| K14 | led-notification | default-sink recognition (SF-B2): DR2 REG:106 OBS; DR6 REG:826 OBS → **OBS** |
| K15 | timing-waits | uptime tick fallback and re-arm (SF-B5): DR6 REG:829 DIFF; DR8 SPEC:4352 DIFF → **DIFF** |
| K16 | storage-fram | mempause deadline (SF-A11): DR3 REG:113 SAME; DR6 REG:853 CHECK [DR8 SPEC:4319] → **CHECK** (V6) |
| K17 | supervisor-reset-watchdog | escalation entry bound 1,200 ms: DR5 REG:746 DIFF; DR6 REG:757/f OBS; DR7 SPEC:12060 OBS → **DIFF** |
| K18 | bus-i2c-spi | I2C timeout under half the smallest hard consumer: DR1 `stall-bounds` DIFF; DR6 REG:757/l DIFF; DR7 SPEC:13352 OBS [DR8 `buildgen/validate.py:618`] → **DIFF** |
| K19 | buildgen-toml | 200,000 µs per-bus ceiling: DR3 REG:345 FORM; DR7 SPEC:12129 FORM → **FORM** |
| K20 | webserver-rest | start retries 3 × 5 s: DR1 `webserver-start-retry` DIFF; DR7 SPEC:12032, SPEC:12033 OBS → **DIFF** |
| K21 | ci-tooling | CI job budget rule and values: DR1 `ci-budget-margin` DIFF; DR7 SPEC:13318, SPEC:13319 DIFF [DR8 SPEC:1940, :1942] → **DIFF** |
| K22 | ci-tooling | harness timeout 5×: DR1 `harness-timeout` DIFF; DR7 SPEC:13331 DIFF → **DIFF** |
| K23 | twin | shared twin retired by age, 89 s: DR5 REG:705 (2) DIFF; DR7 SPEC:12560, SPEC:12561 SAME; DR8 SPEC:6099, `digital_twin/README.md:896` SAME → **DIFF** (V12) |
| K24 | twin | reader-saturation floor: DR7 SPEC:12741 DIFF; DR8 SPEC:5886 SAME → **DIFF** (V13) |
| K25 | ci-tooling | CI apt mirror check and cache: DR6 `owner_report_items.md:198` OWN; DR8 SPEC:1898, SPEC:1923 DIFF (values: DR7 SPEC:13311-13313 SAME) → **OWN** |
| K26 | webserver-rest | third modlwip patch: DR6 REDO.md:31 OWN; DR8 SPEC:2607, :2732, :7556, `micropython_overrides.py:468` SAME → **OWN** |
| K27 | generated-code | OF-107 loop-end record: DR6 REDO.md:31/b OWN; DR8 SPEC:695, `asy_system_service.py:175` SAME → **OWN** |
| K28 | supervisor-reset-watchdog | C-stack reboot: DR1 `c-stack-reboot` OWN; DR5 REG:740 (2), REG:741 OWN; DR8 SPEC:6472 OWN → **OWN**, form only |
| K29 | led-notification | internal LED waits, external refused: DR1 `led-request-internal-queue` OWN; DR4 REG:530 OWN (value: DR7 SPEC:12105 SAME) → **OWN** |
| K30 | webserver-rest | Microdot print rebound: DR4 REG:110, REG:527 FORM; DR6 REG:879/b FORM [DR8 SPEC:567] → **FORM** (X7) |
| K31 | webserver-rest | head limits: DR1 `http-head-limits` OWN; DR7 SPEC:12030, :12031 OWN → **OWN** |
| K32 | website | unattended page: DR1 `website-unattended` OWN; DR7 SPEC:12025, :12026 OWN → **OWN** |
| K33 | website | display details: DR1 `website-display-details` OWN; DR4 REG:608 OWN; DR7 SPEC:12027, :12153 OWN; DR8 SPEC:8172, :8254, `test_error_catalog.py:731` OWN → **OWN** |
| K34 | webserver-rest | static no-cache: DR1 OWN; DR8 SPEC:1281, `asy_webserver_service.py:541` OWN → **OWN** |
| K35 | driver-scd30 | FRC readiness provisional: DR1 `scd30-calibration-readiness` OWN; DR8 SPEC:11855, `asy_scd30_driver.py:121` OWN → **OWN** |
| K36-K43 | ntp-dns, core-logging, website, release | review "ok" with its tagged line, OWN in both: `ntp-synced-goes-stale` + `asy_ntp_client.py:382`; `ntp-no-origin-check` + SPEC:3843; `dns-fallback-setting` + `asy_ntp_client.py:117`; `ntp-sync-last` + `codegen.py:449`; `timestamps-before-ntp` + SPEC:7658; `apply-failure-marks-fields` + SPEC:8106; `website-accessibility` + SPEC:7946; `reflash-runbook-erase` + README.md:447 → **OWN** each |
| K44 | tests-hardware | heap floors: DR1 OWN; DR7 SPEC:13099 OWN (gap); DR8 SPEC:8822, `heap_headroom_after_full_system_build.py:36`, `heap_bounds.py:6` OWN → **OWN** |
| K45 | licensing | licence notices: DR1 OWN; DR6 REG:787/b OWN; DR8 THIRD_PARTY_LICENSES.md:113, :208 OWN → **OWN** |
| K46 | ci-tooling | bench sudo checked: DR1 OWN; DR8 `setup_toolchain.py:738` OWN → **OWN** |
| K47 | tests-unit | driven time: DR1 OWN; DR8 SPEC:5273 OWN → **OWN** |
| K48 | tests-hardware | console-starvation test gated: DR1 OWN; DR5 REG:665 (2) OWN; DR7 SPEC:12938 OWN → **OWN** |
| K49 | ci-tooling | stub versions: DR1 OWN; DR5 REG:680 (1) OWN → **OWN** |
| K50 | twin | twin first for instruments: DR1 OWN; DR5 REG:667 OWN → **OWN**, form only |
| K51 | ci-tooling | comment width: DR1 `comment-cap-long-lines` OWN (110); DR6 REG:784/b OWN (Q6 "c", 120) → **OWN**, the later width |
| K52 | security | threat model: DR1 OWN; DR5 REG:710 OWN; DR8 SPEC:1372, :1373, :1375, :1389 OWN → **OWN** |
| K53 | twin | local NTP responder: DR1 `twin-tolerates-ntp-offline` OWN; DR8 `test_digital_twin_ntp.py:126` SAME → **OWN** |
| K54 | wifi | empty SSID to hotspot: DR4 REG:107, :515, :582 OWN; DR6 REG:857 OWN; DR8 SPEC:443 OWN → **OWN** |
| K55 | wifi | hotspot-client LED: DR6 REG:109, REG:860 OWN; DR7 SPEC:12084, :12085 OWN; DR8 SPEC:449 OWN → **OWN** |
| K56 | wifi | Wi-Fi off LED: DR1 `wifi-off-led-pattern` OWN; DR7 SPEC:12086, :12087 OWN → **OWN** |
| K57 | wifi | persisted Wi-Fi warnings: DR6 REG:859 OWN; DR8 SPEC:3738 OWN → **OWN** |
| K58 | ntp-dns | UDP idle poll 100 ms: DR1 `idle-poll-rate` OWN; DR7 SPEC:12097 OWN; DR8 SPEC:7407 OWN → **OWN** (measurement owed) |
| K59 | webserver-rest | lwIP retry, 5 s per call: DR1 OWN; DR7 SPEC:12023 OWN → **OWN** |
| K60 | uart | DMA receive ring: DR1 `uart-flash-erase-overrun` OWN; DR3 REG:355 OWN; DR7 SPEC:13351 OWN → **OWN** |
| K61 | uart | hazard mode dispatch-only: DR6 REG:795/a, REG:783/e OWN → **OWN** |
| K62 | twin | relaunch crash closed: DR6 REG:784/a, `segfault-not-reproduced` OWN → **OWN** |
| K63 | core-logging | every layer keeps its entry: DR1 `one-entry-per-fault` OWN; DR2 REG:139 OWN → **OWN** |
| K64 | driver-sgp40 | state code values: DR1 OWN; DR3 REG:441 OWN (gap "learned"); DR8 SPEC:8272 OWN → **OWN** |
| K65 | ci-tooling | two retries for timeouts: DR5 REG:706, :707, :708 OWN; DR7 SPEC:12213, SPEC:13329 OWN → **OWN** |
| K66 | docs-records | `@tunable` scheme: DR2 REG:242 OWN; DR7 N1-a, N2-a, N2-b1, N2-e OWN → **OWN** |
| K67 | core-logging | the Q6 handler: DR3 REG:285 OWN; DR6 REG:879/a OWN → **OWN** (the guard: V9) |
| K68 | ntp-dns | the cadence's one-tick fix: DR6 REDO.md:104 OBS; DR8 `asy_ntp_client.py:392` SUP → **OBS** (V19) |
| K69 | uart | PieceBuffer `read_at()` echo: DR6 `owner_report_items.md:112` FORM; DR8 SPEC:10163, UART_C_PORT_CHANGELOG.md:215 SAME → **FORM** (V16) |
| K70 | driver-sgp40 | VOC literal port: DR1 `voc-port-order`, `voc-literal-names` OWN; DR8 SPEC:3029, :6844 OWN → **OWN** |
| K71 | buildgen-toml | `hardware_family` in `[device]`: DR1 OWN; DR8 three `devices/*.toml:16`, `test_device_tomls.py:61` OWN → **OWN** |
| K72 | docs-records | WoZi wording removed: DR1 `wozi-move-owner-operation` OWN; DR6 REG:770, REG:778/a OWN → **OWN**, gap: not built |
| K73 | webserver-rest | refusal bound and chunk write order: DR6 REG:804, :805 OWN; DR8 SPEC:194, :198, :1258, `test_asy_fram_wire_trace.py:500` OWN → **OWN** (X3) |
| K74 | config | single write, flash stall accepted: DR6 REG:799, REG:754/a, REG:757/e OWN; DR8 SPEC:6791 OWN → **OWN** |
| K75 | tests-unit | unit tests at error level: DR5 REG:729 OWN; DR8 SPEC:9290 OWN → **OWN** |
| K76 | driver-scd30 | SCD30 soft reset at start: DR6 REG:783/d OWN; DR8 SPEC:11799 OWN → **OWN** |
| K77 | twin | Run 11 calibration: DR6 REDO.md:36 OWN; DR8 README.md:926, :975, `_digital_twin_ci_suite.py:209` OWN → **OWN** |
| K78 | storage-fram | per-owner CRC seed: DR6 REG:825 OWN; DR8 `test_asy_fram_wire_trace.py:8` OWN → **OWN** |
| K79 | uart | CRC-16 swap (OR88): DR8 PROJECT_AUDIT_PLAN.md:447, UART_C_PORT_CHANGELOG.md:109 OWN → **OWN** |
| K80 | driver-sgp40 | fix16 wraps (VOC-1): DR3 REG:334 OWN; DR8 `voc_algorithm.py:59` OWN → **OWN** |
| K81 | wifi | refused hotspot arm counts (b): DR4 REG:624 OWN; DR8 SPEC:3694, `asy_wifi_service.py:754` OWN → **OWN**, form only |
| K82 | ci-tooling | no GCC 14 leg: DR1 OWN; DR4 REG:565b OWN → **OWN** |
| K83 | tests-unit | lwIP host spin window: DR4 REG:599 OWN; DR7 SPEC:12512 OWN → **OWN** |
| K84 | core-logging | ResetErrors fix without allocation: DR5 REG:724, REG:739 OWN → **OWN** |

Related decisions that are not the same act (a seed and its details) are in section 4, not merged.

## 2. Verdict conflicts, settled

**V1. The closing ledger (DR6) against the owner's 05:30 words.**
- DR6: `closing_ledger.md:8` DIFF ("the ledger holds item 8 ... and item 9 only"); `owner_report_items.md:159`,
  REDO.md:68 and LN349 DIFF; LN357 SUP; `owner_report_items.md:246` OWN (the finite ledger).
- The record:
  - 05:30 (LN357): the lead's proposal to defer CMr1n and RF1 drew "I don't actually want to cut back or trade
    anything, ...". The lead withdrew it ("both stay in U35") and wrote the nine-item ledger.
  - 06:13: "Pause all tasks for now".
  - 06:37 (LN362): "... The audit verification machinery is just a temporary tool. So we will have to find a
    distinction where to put the effort." The parts quoted this without its last sentence. The lead then proposed "an
    effort distinction (three tiers) and a mapping of the paused work, for the owner's confirmation".
  - 07:02 (LN365): "Stop, I didn't give ANY go ahead yet". No later words decide the paused lanes.
- **Stands: OWN.** The 05:30 decision covers items 1-9 ("anything", CMr1n and RF1 by name) and was never withdrawn. The
  06:37 words reopen where the effort goes, but they decide nothing about these items. DR6's answers are a proposal for
  that open distinction, not a settled verdict. Recorded as owner statements that pull apart, with no question framed.
  The 06:43 words ("building upon hypothetical findings is a clear no-go") concern firmware complexity, not the records
  lanes.

**V2. N1-f (DR7 DIFF) against OR30.a (3).** OR30.a, "yes to all three", includes "(3) Accuracy: each value is checked
against the current project (timeouts vs measured run times from CI logs and local runs with a stated margin ...);
board-dependent values go to the hardware queue". **Stands: OWN** for the rows the owner's scope keeps. For in-test
literals N1-f has no separate effect: they leave the register under N1-b (V3). The 2026-10-28 tiering pulls the other
way (DR2 item 12, DR7 item 11); that is recorded as fact.

**V3. N1-b, the register scope (DR7 DIFF), against OR30/OR30.a (DR2 REG:242 OWN; DR6 `owner_report_items.md:157`
OWN; DR5 C12).**
- **Stands: DIFF on the agent's widening, OWN on the scheme (K66).**
- SPEC:11921 credits "every test tier's sleeps, bounds, timeouts, retries ..." to "(owner, 2026-09-25, paraphrase)". The
  owner's words are narrower: OR30, "runtime and timeout parameters for test suites ... essential for clear test result
  discrimination"; OR30.a (1), "every tuned (not derived) value that must be retuned as the project changes", with
  suite-level examples.
- The cut must follow that criterion, not DR7's family line:
  - family B ("step × tries is one derived deadline") and family D (inputs) fall outside "tuned, not derived";
  - the "hardware-tier budgets" OR30.a (1) names are partly in families A and C on L3/L4, and those stay.
- DR5 C12 and DR6 :157 then fit: the "runaway" label applies to scale, not to the owner's scheme.

**V4. W75 (K08): DR8 SPEC:11754 SAME against DR6 REG:835 DIFF and DR3 REG:458 OBS.**
- **Stands: DIFF**, console-only as before.
- Basis: C.md ISL-9 is H, triage implausible ("observability of a user-started run"). S2-G3-7 lists W75 as existing only
  for ISL-9.
- DR8's own reason ("an expected outcome, not a guarded fault") argues for console-only.
- The SPEC sentence "An expected condition prints only" (SPEC:3666-3668) is not owner basis. It generalises a paraphrase
  about startup jitter ("owner, 2026-09-12, `8a45060`, paraphrase").

**V5. E27 (K13): DR3 REG:120 SAME against DR6 REG:872 DIFF.**
- **Stands: DIFF** at the BMP3XX site: C.md BMP-5 is H, implausible, 3 lines, "escalation unchanged".
- E27 itself stays for the SCD30 range gate (OR101).
- DR3's rule that a code at an existing branch is no mechanism is its own classification. The owner's "really minimal
  change" and "building upon hypothetical findings is a clear no-go" decide.

**V6. The mempause deadline (K16): DR3 REG:113 SAME against DR6 REG:853 CHECK and DR7 SPEC:13025-13028 CHECK (DR1
`unpause-waiter` SUP, DR2 REG:246 SUP "in doubt").**
- **Stands: CHECK** (HW5).
- A-S21: the mechanism is confirmed in source (`shared/runtime/mpirq.c:105`, `py/scheduler.c:163-180`, depth 8); the
  triage is suspicious, the frequency unverified. The owner: "Hypothetical findings which are suspicious to be real need
  to be verified".
- DR3's two points make it suspicious either way: the pre-audit F.1/C.9 text named a must-fire one-shot a hazard, and
  the new form has one Timer fewer, at about 15 lines.
- DR1's and DR2's SUP verdicts stand (their rows were overtaken by SF-A11). Whether SF-A11 stands is the CHECK.

**V7. E28 (K10, REG:487, REG:511).**
- The three readings:
  - DR6: E28 goes, A-P4's branch stays;
  - DR3 REG:487 (gap note): keep "one E28 at setup for an unreadable store";
  - DR4 REG:511: E28 "stays only if the setup-time arm stays".
- **Stands: E28 retires.**
  - A-P4's confirmed gap (A.md V11) is "a read fault no longer writes the current ring over the stored history", and
    that needs no entry.
  - A-P3 covers every E28 arm, setup included: H, implausible, "the FRAM layer's own entries already show it";
    S2-G3-7 lists E28.
  - The owner's blast-radius note ("It should rather stay as is") keeps entries that existed; it asks for none new.
- REG:487 stays OWN for the FRAM_FULL refusal (owner, 2026-09-16).

**V8. The captive DNS heap re-raise: DR4 REG:520b DIFF against DR6 REG:795/k SAME.**
- **Stands: DIFF.**
- LN96 kept the re-raise because "narrowing DNSQuery's handler would let one bad datagram pause the server 3 s". That
  argues against a different change, narrowing the handler; it does not argue for keeping the re-raise.
- The pre-audit catch-all (`captive_dns.py@25caf528`) answers an unparsable query with the event line "Empty DNS query,
  not sending response." and pauses nothing. The re-raise is what adds E23 and the 3 s backoff (S2-G2-10, K; SCAN2 §3,
  "allocation failure split from bad input").
- The keep was the lead's (LN96: "Kept by lead decision"), not the owner's.

**V9. The exception-handler guard: DR6 REG:795/i DIFF against DR3 REG:285 OWN (fact F2).**
- **Stands: CHECK** (records), see section 6.
- The clause "only where no handler is set yet" landed in `8d44fd14` (U11, 2026-10-07), the day of the owner's "Yes,
  build it that way." (SPEC:6549).
- `git grep` over `audit/` at `11b66cd8` finds the answer only, not the proposal it answered. If the proposal lacked the
  guard, OR36 decides: DIFF.

**V10. The UART link's `initialized`: DR1 `uart-link-initialized` SAME against DR2 REG:270 OBS.**
- **Stands: SAME.**
- At `497b3eda` the flag is read by the exercise loop, `src/asy_uart_link_driver.py:133` `while self.initialized:`, and
  by the hazard dispatch guard at `:282`.
- REG:270's stated reason ("read only by its own `setup()`'s answer") is stale; its conclusion holds. Only the `setup()`
  bool is S2-G1-10's.

**V11. `sensorreader-logger-removed` (DR1 SAME) against REDO.md:12 (DR6 OWN).**
- **Stands: SUP** for the `logger=` half: the owner's library rule (2026-10-23: "Always regard the modules as libraries,
  not every feature must be immediately used, as long as it is a real feature") restored it.
- **SAME** for the type-check half (the owner's typing rule, 2026-10-27). Counted as SUP.

**V12. The shared-boot deadline (K23): DR5 DIFF against DR7 SAME and DR8 SAME.**
- **Stands: DIFF.**
- The basis is the commit's own facts:
  - the failure was named by module, level and code;
  - its trigger is an event, the first untimestamped backup;
  - an idle dev twin measured that event at +94.0 s and +155.1 s, so 89 s is only the earliest time.
- Further basis: OR37.a (3), and N.1's own rule that host load cannot fail a healthy test. The owner's delay-check quote
  was about a firmware check; it supports the answer but is not the basis.

**V13. The reader floor (K24): DR7 DIFF against DR8 SPEC:5886 SAME.** **Stands: DIFF** for the floor clause. The basis
is OR72 ("1. Not sure. Only okay if it ever has a realistic chance to pass. Very hypothetical test.") and OR72.a (1)
("as an OR49.a degradation check only"). DR8's own note reads "degradation check only".

**V14. `runner.port_lock_attempts`: DR7 SPEC:13330 OBS against DR1 `port-lock-reader` FORM, `port-lock-inherit` SAME
and DR5 REG:639 SAME.** **Stands: SAME.** The runaway is the lock's three copies (P8), not the lock: CLAUDE.md's "Two
suites that both bind real ports must never run at the same time" needs it.

**V15. Narrowing branches: DR8 SPEC:5585 and UART_C_PORT_CHANGELOG.md:213 DIFF against DR1 `isl-counts-check`, DR2
REG:256 and DR6 REDO.md:16 FORM.** **Stands: FORM.** It is the same decision (narrow for the type checker) in a smaller
form, a cast (SCAN2 §9).

**V16. PieceBuffer `read_at()` (K69): DR8 SAME against DR6 FORM.**
- **Stands: FORM.**
- The F row DR8 credits is "a measured 12 KB copy per GET in the audit's own UART echo path" (REPORT, the notes under
  section 2's table), so it is the cost of a cascade. SCAN2 §6 corrects the saving to −13 lines; `trim()` stays.
- The smaller form must still keep the 12 KB copy gone, through dev's cap near the echo's need (G2 chain 7). Its side
  effect is DR4 C12.

**V17-V18. CI apt (K25), the third patch (K26), the loop-end record (K27).** DR8's DIFF and SAME become **OWN** on the
extract (section 0).

**V19. The NTP rounding (K68): DR8 SUP against DR6 OBS.**
- **Stands: OBS.**
- Q10 answered the stale rule's slack (rulings file: "Q10, the NTP stale rule's up-to-10 s slack ... Option a, the 10s
  don't matter at all relative to the interval"). It did not answer the cadence fix, and the rounding is still at head
  (`:392`).
- The rounding goes with the cadence chain (S2-G4-13), whose DIFF (REDO.md:25) rests on Q10's reasoning.

**V20. VOC-5: DR8 `src/voc_algorithm.py:219` DIFF against DR5 REG:676 (3) SUP.**
- DR5's superseding decision includes "constants built once (OF-90, U30)".
- **Stands: DIFF for the constants.**
  - OR109: "If the VOC algorithms allocates and the allocation goes after it's done and gc can clean the mess up,
    everything is settled."
  - OR109.a (1): "No rework of the fix16 helpers".
  - The literal-port rule; C.md VOC-5 H.
- DR5's SUP stands for the rig's GC mark stack half (REG:723 SAME).

**V21. The boot-contiguity control arm: DR3 REG:492 FORM against DR7 SPEC:12188, SPEC:12189 SAME and DR2 REG:192
SAME.**
- **Stands: FORM**, and the two arm-ratio values become OBS.
- The owner's words in OR21.a are "yes, but the control arms are overkill". "Existing control arms ... are left as they
  are" is the integrated text, the agent's reading.
- REG:492 added two guards to the arm on 2026-10-07, after OR21.a.
- REG:192 (the live band) stays SAME.

**V22. SGP40 restart (K09): DR3 REG:489 OBS against DR6 REG:875 DIFF.** **Stands: DIFF.** REG:489 is the rule as built
at U16, the same decision as SF-M3-05.

**V23. REG:112 SUP against REG:836/865 DIFF (K10):** one chain, **DIFF**. REG:112's SUP holds for FRAM_FULL.

**V24. The twin NTP test (K53): DR8 SAME → OWN.** It is the owner's change note on `twin-tolerates-ntp-offline`.

**V25. OF-16's per-file count: DR2 REG:243 SAME (with contradiction 1) against DR7 N2-b2 DIFF.**
- Attribution only:
  - The owner's "That's actually a combination you don't need to ask me for." (LN175, CHECKLIST 1d) covers a
    test-only, no-wear, coverage-adding change, so the 2026-10-26 extension was within the lead's delegation (DR7 is
    right on that).
  - Both parts end at the same answer: no count; OF-16 stays a documented blind spot.
- The records' "OF-16 open ... waits for the owner" is stale.

**V26. LN355, LN358, LN357** (section 0).

Checked and **not** in conflict:
- **The NeoPixel chain** (section 0).
- **The routine batch.**
  - DR1 (contradiction 1) and DR6 (`review-and-go-ahead` DIFF) agree. The rule "silence on a routine batch counts as
    approval" is the page's own owner-step text (`decisions.json`, `owner_steps`).
  - OR140 is the lead's record row ("the routine group left unanswered"), not owner words.
  - Against the rule: OR48.a ("recorded decisions I took (not the session agent)"); 2026-10-28 "Decisions I really
    took are still valid." (rulings file, "Validity"); "The OK in the review stay valid." (the answer to the question on
    the "ok" ticks).
  - OR145 ("the pillars and rules and specifications we wrote and refined ... become effective and need to be adhered
    to") made the written rules binding for execution. That is why the routine items ran. It adopts no item.
- **`rel_humidity()`.**
  - DR1 judges the review item: OWN, with the no-clamp as its gap. DR3 judges the U12 row that went past the note:
    REG:342 DIFF.
  - They give the same answer: the clamp returns. Legacy (`math_helpers.py:65-66`) and pre-audit
    (`25caf528:src/math_helpers.py`, `max(0.0, min(100.0, rh))`) both clamp.
  - "Adapt the humidity to the verified range" is about the Magnus pair (SPEC:7832, `src/math_helpers.py:58`).
  - The no-clamp sources are OR140.a (4)'s integrated text and the pre-audit D.7 review hint ("a clamp that silently
    clips instead of signaling invalid", `SPECIFICATION.md@25caf528:2655`), a checklist hint, not a rule.
- **Per-episode flags.**
  - DR2 (contradiction 10) and DR5 (D5) agree: U3's central rule stands (OR35.a "Console logs actually should keep
    printing all."; OR35.b "... Pure and simple.").
  - Precision: S2-G4-8's seven flags come from several units:
    - four (config `_read_failing`, BMP3XX `_comp_unreadable`, notification `cfg_unreadable`, FRAM
      `_no_check_logged`) sit in modules U30's squash `06a8ae5d` touched;
    - two timer flags belong to the refused-arm family (A-B14/A-B6/A-S20);
    - `quiet=` stays while Wi-Fi's settled re-arm passes it (SCAN2 §7.5).
  - The config store's per-episode logging is a U30 unit-table row (REGISTER:56) in no owner-review list (X15).

## 3. Contradictions across parts

**X1. REG:244 against the routine review item `utc-valid-no-argument`.**
- REG:244 (U10, DR2 DIFF) added `set_utc_valid(*, valid=True)` for the tests.
- The page's routine item (DR1 SAME) reads "set_utc_valid() takes no argument; it only ever marks the clock valid."
- Neither part saw the other side. The item stands: OR36, and the "ok" on `timestamps-before-ntp`.

**X2. S2-G3-7 against DR1 `warning-names` and `dnssrv-warning-code`.**
- S2-G3-7 lists "W12 SOCKET_TEARDOWN: B-DNS-7 (H)" among the codes that exist only for a doubted mechanism.
- At head W12 is also the captive DNS teardown warning, `asy_captive_dns.py:145`. That event is pre-audit:
  `captive_dns.py@25caf528:153`, "DNS Server socket teardown did not complete cleanly." (wrnno=3).
- NTP uses W12 too, at `asy_ntp_client.py:275`.
- **DR1 stands:** W12 stays when DNS-7's site goes. DR4 REG:514's list of codes to retire correctly leaves W12 out.

**X3. The refusal path: SCAN2 §7 item 7 (close, then trace) against REG:804/805 (owner-agreed).**
- The parts recorded this as facts: DR6 C4, DR7 item 7, DR8.
- Checked LN106, LN110 and LN111.
  - The report the owner answered named "the refusal trace bounded at one per-call timeout through the existing
    parameter, every pre-close trace in _serve() under the same bound, and the FRAM chunk's write order".
  - "trace-before-close kept as the pacing it is" is LN106's decision text, not in that summary.
- **No contradiction.** Under the owner's background note (decisions tied to an issue a cascade introduced may become
  obsolete), close-then-trace is a smaller form of the owner's drop trace (OR102.a (9)). The bound stays on the other
  arms. The pre-audit "decision 3" has no owner words (DR6).

**X4. DR1 `harness-timeout` against the owner's retry rule.**
- DR1's new answer: "a small multiple of the slowest measured run ... and few attempts".
- The owner: "Two retries everywhere" (REG:706, 2026-10-20), narrowed to "tests running into timeout" (REG:708).
- **The DIFF holds only with the owner's two retries kept** (DR7's version of the same chain keeps them).

**X5. DR7 N1-b's family cut against OR30.a (1).** See V3: hardware-tier budgets stay, derived values go.

**X6. DR7 N1-g and N2-c (FORM) against OR30.a (2)/(3).** "Estimated" is one of the owner's columns. On rows that stay,
the pending accuracy check must stay visible, so the FORM holds only with that.

**X7. Microdot's print: DR4 REG:110/527 against DR6 REG:879/b and S2-G2-8.**
- DR4's smaller form keeps "one level-gated logger line". DR6 and S2-G2-8 keep "the plain print".
- Pre-audit, Microdot printed through its own vendored `print_exception`. The level gate is WS-9's motive: H, its
  premise G2's console-stall check.
- **Stands: the plain print** plus the C-stack report, unless that check shows a stall (section 6, item 4). The asyncio
  handler's level gate is separate and the owner's (Q6).

**X8. DR3 REG:485 against DR6 REG:836/865.**
- DR3 REG:485 brings back the SGP40's own persisted no-backup warning, on the owner's blast-radius note. DR6 removes the
  logger's E28.
- **Compatible.** "It should rather stay as is" keeps per-layer entries that existed (REG:485's is pre-audit,
  `asy_sgp40_driver.py@25caf528:373-374`). E28 never existed before the audit.

**X9. The product console-line DIFFs against CLAUDE.md's memory gates.**
- The DIFFs: DR5 D3, DR4 REG:514's UDP part, DR6 REG:854/871/REDO.md:28 (OBS), DR8 SPEC:7680 (OBS).
- CLAUDE.md's four gates must see a caught-and-logged allocation failure.
- **Compatible only with SCAN2 §9's routing:** "The handlers that have no logger route their text through the owning
  module's logger". DR5 C4 records that the gates' reach rests on agent text; the owner's direction is "Option 1"
  (test side).

**X10. The LED deadline.**
- The approved text: an internal request "waits for the running signal up to a deadline and then queues".
- The code drops the request at 120 s (DR1 22, DR7 8, DR2 REG:106).
- A record fact: the deadline is the owner's (SCAN2 §7.2), the drop and W67 are the agent's. W67 goes (K14). No
  question, since the topic is decided.

**X11. REPORT.md's "What went wrong (agent, 2026-10-28; the owner agreed: "I agree with wour conclusions about scope and
effort.")".**
- The agreement (LN362, 06:37) answered the lead's drift assessment in the conversation. REPORT.md was written at 08:03.
- DR2 (REG:329), DR4 and DR7 (N1-f) cite REPORT's items 2-3 as agreed; their DIFFs also rest on other owner words of
  that day. Fact for the lead.

**X12. Agent text credited to the owner, seven sites (one mechanism, L7):**
- OR21.a (2), "existing control arms ... are left as they are" (V21);
- OR140.a (4), "and the helpers with the no-clamp rule";
- SPEC:11921, "(owner, 2026-09-25, paraphrase)" (V3);
- SPEC:3666-3668, "An expected condition prints only", generalised from startup jitter (V4);
- OR143.a's "catches go" (DR4 C1);
- REG:637's "(owner, 2026-10-08)" on three agents (DR4 C6);
- SPEC I.4(e)'s "Option 1" on product console lines (DR6 C2).

**X13. Owner statements that pull apart, merged (facts for the lead, no question framed):**
- (a) OR30.a against the 2026-10-28 tiering (DR2 12, DR7 11; V2).
- (b) 05:30 against 06:37 (DR6 C6; V1).
- (c) the lost UART frame: the review "change" note against the 2026-10-22 accepted degradation (DR4 C8, DR6 C9).
- (d) the console at DebugLevel 0: OR35.a against the 2026-10-07 handler design, Q6 and "Keep as is, no added
  complexity." (DR4).
- (e) OR56 "never both" against the `one-entry-per-fault` note, on FRAM's E+W pair for one block (DR3 F1, DR4 C11,
  DR2 9).
- (f) the refused hotspot arm, option (b), against Q2 (DR4 REG:624, DR8).
- (g) the hazard row added to A.11 after the sign-off (DR8).
- (h) new here: "Adapt the humidity to the verified range" (REG:331) against the wet bulb's cold-dry corner, which
  REG:342 returns to the pre-audit domain. DR3 reads the words as humidity only; the corner is Stull's own validity
  limit.

**X14. Records that contradict the tree (merged):**
- OF-16 "open" (DR2) and OF-120 "open" (DR4), both already done.
- REG:796 still "For the owner as questions"; REG:806 lacks the 2026-10-26 go; the REG:808/809/811 placeholders (DR6).
- SPEC:7450 is stale (DR3 REG:393); the `audit/actions/U3.md` preamble too (DR2 11).
- REG:121's unit is U22, not U9 (DR2).
- CLAUDE.md tags two notes as paraphrase although the owner's verbatim notes exist (DR5 REG:665 (2), REG:680 (1)).
- The catalog reads "learned" where the owner approved "settled" (DR3 REG:441).
- The WoZi wording (K72).

**X15. Decisions in no part's set:**
- the U0 deletion of F.2's "only worth closing for a concrete, non-hypothetical threat" (`195f3ed3`; DR2, PICTURE M1);
- U30's per-episode config-read logging (REGISTER:56; S2-G1-8 H). U3's owner-ruled central rule decides it: it goes;
- the catalog's "Retired numbers are never reused" (SPEC:3653, untagged; SCAN2 §8.5).

**X16. DR5 REG:730 (3) and DR2 REG:272 (SAME) are dependants of the `deinit()`/`set_level()` bool widening**, whose seed
`setup-returns-bool` is DIFF (SCAN2 §3: "~20 go"). The comment on `deinit()` returning True goes with the bool. Minor.

**X17. `ci.unit_tests_coverage_timeout_min` = 95 (DR7, DR6 LN246 SAME) against DR5 REG:713 FORM:** the value follows
the form. Minor.

**X18. DR1 `fram-waits-unbounded` against the pre-audit bounded `fram.verify_lock_timeout_ms`** (DR7 SPEC:12130, DR2
REG:257 SAME): a pre-audit exception in `verify_present()`. Nothing to change.

**X19. DR4 C12 against K69.** A dev cap near the echo's need (the smaller form) also shortens the bench's largest-train
proof (`uart_crossover_exchange.py:140`). It is a value question for the cleanup plan; the wire is untouched.

## 4. Seeds and their dependants

| seed (verdict) | dependants across sets | agreement |
|---|---|---|
| U2 catalog, OR28 (owner) + "never reused" (agent, no verdict anywhere) | REG:132 FORM (bands); about 20 tombstones from every removed code (W67, W69, W71, W73, W75, E28, E52-E54, E91/E92, E115, W16, W62, E72-E74); REG:532 SAME notes the rule's reason ("FRAM history across reflashes") is not required (OR47.a: "no requirement for the fram to stay consistent through firmware re-flashes") | the owner's half holds; the agent rule is unjudged (X15) and turns each DIFF into a tombstone. W12 is not among them (X2) |
| U3 central newest-entry rule (owner) | REG:139/142 OWN; REG:738 (2) DIFF; REG:511 DIFF; S2-G4-8's flags; U30's config episode (X15) | agree |
| `@tunable` scheme, OR30 (owner, K66) → widening to test literals (agent, SPEC:11921) | N1-b DIFF; N1-f OWN (V2); REG:757/c OWN; `owner_report_items.md:157` OWN (scheme); families A-E (value verdicts SAME); the seven E1 waits DIFF | agree after V2/V3; the family SAME rows judge values, not register membership |
| REG:329, the binding open-findings rule (agent, DIFF) | every unverified finding that became code: OF-75 (K01), OF-222 (K17), OF-215 (REG:704 (2)), OF-224 (REG:747 (2)), OF-61 (REG:511), OF-144 (REG:615b), OF-247 (REDO.md:25), OF-30 (REG:467), OF-142 (REDO.md:11), all DIFF; OF-250 CHECK; the routing rows (REG:656, 666, 681, 703, 718, 727) SAME | agree: documenting stays, the automatic route to code goes |
| F.2's deleted hypothetical rule (U0, no row) | BR3 (`owner_report_items.md:67`, DIFF), BR2 (CHECK), the H memory catches | agree |
| U10 contracts (DR2 seeds) | `setup()` → bool DIFF: REG:268 OBS, REG:270 SAME (V10), `setup-function-type` OBS, `notification-setup` OBS (bool half), REG:272/REG:730 (3) SAME (X16); `valid=` DIFF (X1); `utc_now()`/`TickSeconds` R: the "TS None counts as current" clauses OBS (SPEC:373, :420) with K02 | one minor mismatch (X16) |
| refused timer arm (A-B6/A-B14/A-S20, trigger refuted, V6 of A.md) | K15 DIFF; REG:828, REG:868 OBS; REG:732 OBS; SPEC:12386 OBS; SPEC:5878 OBS; REG:783/c OWN (Q2); Wi-Fi's re-arm OWN (K81), `quiet=` kept | agree |
| `wait_for_ms` for every boundable wait (`one-timeout-mechanism`, DIFF) | K01 DIFF, UDP-4 (`owner_report_items.md:234` FORM, `unit-test-d-t30` SUP), K17 DIFF, the LC1 primitive (`:232` DIFF), WS-6 on the refusal arm (X3) | agree |
| the lost-FRAM chain, A-D1 (CHECK, section 6 item 1) | REG:793/a, REDO.md:24, SPEC:12132 CHECK; REG:670 (b) OBS; SPEC:303 [lean OBS]; `verify_present()`'s product caller; E54 | agree; REG:670 (b) holds either way (S2-G4-5: the read-path question goes in both outcomes) |
| memory-gate reach (CLAUDE.md "caught-and-logged included", agent per DR5) + U30 lane X2 | REG:730 (2) DIFF; REG:854, REG:871, REDO.md:28, :105, REG:757/k, REG:750/b OBS; REG:510 OBS; REG:514 (UDP) DIFF; SPEC:7680 OBS; REG:484 SUP (later line does not stand) | agree, with X9's routing |
| OR2.c "conservative" read as protective (DR4 umbrella rows SAME as process; DR6 C15; `end-of-execution-review` OWN with gap) | the H DIFFs of DR3, DR4, DR6 (SF parked deltas) | agree: the process stands, its protective reading is what the DIFFs undo |
| the 2026-10-06 first-pass scans (SF parked deltas, agent) | K02-K13, K15, K16 and their U11/U15/U16 detail rows (REG:118, :443, :458, :463 OBS) | agree after V5 and V22 |
| OR21.a's integrated text (agent) | REG:492 (FORM), SPEC:12188/12189 (OBS, V21), REG:192 SAME | agree after V21 |
| OR140.a (4)'s "no-clamp rule" (agent) | REG:342 DIFF, REG:332 OBS, A-H4 (C) | agree |
| the hazard mode exception (owner, REG:801) | K61 OWN; REG:664 (1) SUP; `l1.uart_comm_hazard_*` SAME; DR8's hazard rows [REG:795] | agree |
| REG:659's boot sharing (U25, efficiency) | REG:705 (2) DIFF (its timed fix, K23) | agree: the sharing stays, the fix's form changes |
| U9 LED pilot (mixed) | owner parts OWN (NP-1, NP-2, NT-1, NT-6); NP-4 (`led-task-defined-state` SAME, [DR8 lean DIFF]); K14 OBS; K01 DIFF | agree (DR8's lean is no verdict) |

## 5. The DIFFs as one set (82 after settlement)

By topic (chains counted once):
- **timing, led:** K01, K02, K15, K17, K20, `one-timeout-mechanism`, `float-sleep-everywhere`, REDO.md:25 (cadence),
  REG:705 (2) (K23), `owner_report_items.md:232`.
- **drivers:** K03, K04, K07, K08, K09, K13, `bmp-conversion-wait`, `i2c-scratch-view`, REG:342 (clamp, wet bulb),
  REG:467, REG:485, SPEC:11606 (`_init_failed()`), `voc_algorithm.py:219`.
- **core, storage, config:** K05, K06, K10, K12, `setup-returns-bool`, REG:244, REG:511, REG:750/c (E115),
  REG:795/j, REDO.md:18, `owner_report_items.md:67` (BR3).
- **network, UART, web:** K11 (State), K18, `new-dns-ntp-errnos`, REG:514, REG:519, REG:520b, REG:795/k (V8),
  REG:531, REG:337, REG:730 (2), REG:738 (1), REG:738 (2), REG:795/b, REG:820, REG:839, REDO.md:11,
  REDO.md:25/b, REG:615b.
- **tests, twin, CI:** K21, K22, K24, REG:616b, REG:704 (2), REG:747 (2), N1-b, N2-b2, the seven E1 waits,
  REG:795/c, LN196/b, LN230, LN281, REDO.md:54, `owner_report_items.md:206`.
- **process, records:** REG:329, REG:792, `review-and-go-ahead`, REDO.md:59, :60, :72, :108, :113,
  `owner_report_items.md:71`.

**Against each other.** No two DIFFs contradict. Checked pairs:
- `one-timeout-mechanism` with REG:746: both leave the escalation's write unbounded, with the watchdog behind it.
- `stall-bounds` with REG:345 FORM and REG:557: one I2C timing check stays, the boot-clear budget.
- REG:514, REG:839 and `new-dns-ntp-errnos` retire E72-E74 and W16 but not W12 (X2).
- REG:750/c with REG:750/d: code 2 carries the supervisor's fault.
- REDO.md:25 with `ntp-synced-goes-stale`: NTP-11 runs on `_sync_age`.
- REG:827 with `failed-push-no-flash-write`: the unpersisted flag stays for the shutdown flush.
- REG:342 with REG:331: different aspects of the same helpers.
- The E1 waits with N1-b: their values become poll backstops, outside the register.

**Against owner decisions.** Three conditions:
1. `harness-timeout` and `ci-budget-margin` keep the owner's two retries (X4).
2. N1-b's cut keeps the hardware-tier budgets of OR30.a (1), and N1-g's form keeps OR30.a (3)'s pending check visible
   (X5, X6).
3. Every DIFF passes LN97's test: "double check where it came from what it affects, what its intended function is ... no
   regressions, also no hidden ones".

The DIFFs above rest on scan rows that state provenance. The cleanup still owes the per-change table LN97 asked for
(`briefs/blocks_zmo.md`).

**Against SCAN2 §5's keep list.**
- **Owner decisions in smallest form**, all kept:
  - the C-stack reboot (K28): REG:746 removes only the bound; the Microdot hook stays (K30);
  - the NeoPixel queueing and refusal, "with NP-5 reverted": K01 does exactly that, and the 120 s deadline stays (K29);
  - the staged write after the pushes (K12 keeps the flag);
  - the FRAM seed (K78), the DMA ring and hazard mode (K60, K61), WS-1 (K31), WS-3/WS-4 (REG:529 FORM keeps a trace
    per drop);
  - the Q6 handler (K67, whatever V9's check finds), Wi-Fi as decided.
- **Confirmed gaps**, none touched:
  - the unreadable log store: K10 removes E28 only, A-P4's branch stays;
  - captive DNS's 512-byte receive and one yield per datagram: REG:520b removes only the re-raise, REG:839 keeps the
    receive;
  - the zero transmit timestamp (REG:821 SAME, not REG:820);
  - I2C-6/7 (`i2c-scratch-view` leaves them; REG:351 FORM keeps ~4 lines);
  - the SGP40 restore cycle: SGP-17 is a different case from K09's SGP-12;
  - the loop-end labels (K05 removes only `ResetBits`; K27 OWN);
  - the emergency buffer (REG:405), the listener close (K26 OWN), the cut config write (SPEC:3932).
- **Rare but real:**
  - a wedged bus at boot: the budget check (K19) and the SCL wait (REG:347 FORM) stay;
  - a chip erroring in operation: the ladder stays, and SPEC:11606 moves setup failures onto it mild-first, keeping
    `_rungs = 0` and I2C-5's report (SCAN2 §7.9);
  - a declared FRAM chip that never sets up: OR89's escalation stays in either outcome of the CHECK;
  - an unreadable store at boot (A-P4, `ConfigFaults`);
  - an unpersisted store at shutdown (K12's flag);
  - a C-stack overflow (K28).

**What taking them all would regress, unless handled:**
- **The memory gates' sight.** The UART driver, UDP and RegionBuffer caught failures go silent unless their text is
  routed through the owning logger (X9). Not a product regression, but CLAUDE.md's standing rule.
- **The VOC test time.** VOC-5's revert takes away one of the two causes of `test_voc_algorithm.py`'s 20.0 → 6.3 s
  (REG:676 (3)). "Test duration going up like this is anyhow something to fix - not cutting back strictness, but making
  it more efficient" asks for that to be measured.
- **A visible output change.** REG:342 returns SCD30's published `WetBulb` in Stull's cold-dry corner, back to legacy
  (X13 (h)).
- **The bench proof.** K69's smaller form shortens the bench's largest-train proof (X19).

Not regressions: OF-75's WS2812 premise goes back to the hardware list (DR2), and W67's removal leaves a dropped internal
LED request untraced only when the signal task never restarts, which is the watchdog's case (L3).

## 6. Needs verification (merged, by what depends on them)

1. **The FRAM SPI SO level with the chip absent, on dev at the pre-audit image** (REPORT §7 item 2).
   - From: DR6 REG:793/a, REDO.md:24; DR7 SPEC:12132; SCAN2 §8.
   - It decides the lost-FRAM chain (~60 lines), the RDID probe, OF-250, `fram.chip_probe_at`, E54 and
     `verify_present()`'s product caller.
   - 0x00 → the chain goes. 0xFF → the parts differ on what stays:
     - DR6: only the status-bit-0 refusal, ~4 lines;
     - DR7: the write-path detection and its value.
   - Read the 0xFF case against S2-G4-5's "keep" before acting.
2. **HW5: whether 8 or more soft callbacks queue at once under the shipped load**, on dev across a config flush.
   - From: DR6 REG:853; DR7 SPEC:13025-13028; V6.
   - It decides SF-A11's deadline against the pre-audit one-shot, and the four l3 margins with it.
   - Seen → keep the deadline. Never → the one-shot with its catch.
3. **The logger-side C-stack check on the Unix port with a near-exhausted C stack, and the board's peak** (SCAN2 §8;
   REPORT §7.1; DR1).
   - The ~118-line form of the owner's C-stack reboot depends on the check working there.
4. **A USB host that never reads, against the pre-audit image** (G2 NV-3; SCAN2 §8; DR4 C9).
   - It decides WS-2's ~38 lines, the Microdot gate (X7) and the console-starvation test's premise (SPEC:12938).
5. **BR2's three fixes:** at the parent of `7008730e`, name the raising call at each site and read it in v1.29.0
   (DR6 `owner_report_items.md:62`). Only a MemoryError at call entry → revert under F.2's restored rule; anything else →
   keep.
6. **The handler guard's proposal text** (V9): find the 2026-10-07 proposal the owner answered "Yes, build it that way."
   (the lead's records of U11).
   - Guard in it → OWN, form note only.
   - Not in it → DIFF (OR36), one line.
7. **W29 entries in dev's FRAM log** over the hardware round's boots, read before any `ResetErrors` (DR7 SPEC:12131,
   A-D3). None → pattern 8, the retry goes. Any → SAME.
8. **The refused connection's effect on the 9-socket pool** (SCAN2 §8). It changes X3's label from form to behaviour
   fix, not the action.
9. **Owed measurements, deciding no verdict:**
   - the 100 ms idle rate (K58);
   - the SCD30 readiness defaults (K35);
   - dev's post-boot heap (OF-105, REG:528);
   - the VOC test time after VOC-5 (section 5);
   - optional: 100 `I2C.recover()` calls per bus; NV-1 (S2-G3-15).
10. **The WS2812 state loss under Wi-Fi bursts** (OF-75; DR2). Only if someone wants a fix back; it decides nothing now.

## 7. Totals

Raw sum of the eight parts: 3,021 decisions:

| SAME | OWN | FORM | DIFF | OBS | SUP | CHECK | TRACKED |
|---|---|---|---|---|---|---|---|
| 2,299 | 298 | 76 | 107 | 82 | 68 | 10 | 81 |

After the crosswalk:
- DR8's 81 TRACKED rows are removed (each is a row of another set);
- the 84 chains (240 rows) count once, with the settled verdict;
- 17 single rows are re-settled (V1, V2, V8-V11, V14, V15, V21, V26).

**2,784 decisions**, facts not counted:

| SAME | OWN | FORM | DIFF | OBS | SUP | CHECK |
|---|---|---|---|---|---|---|
| 2,278 | 201 | 75 | 82 | 71 | 66 | 11 |

Most of the OWN drop is the merging of review "ok" items with their tagged lines and Part N values, not a change of
mind.

Counts in this file: 84 chains; 26 verdict conflicts settled (V1-V26); 19 cross-part contradictions (X1-X19), each with
its side that stands or its facts; 10 merged checks.
