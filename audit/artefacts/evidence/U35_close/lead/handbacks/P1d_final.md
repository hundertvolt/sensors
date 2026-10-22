## U35 P1d: steps 145-179, located at `1dd6dd5`

All 35 steps are located (step 157 is the co-landing group and counts as one). This was read-only: the only files written are the helper scripts and extracts under `S/u35/plan_scratch/d/`. All line cites are at `1dd6dd5`. "README" means `digital_twin/README.md`, "SPEC" means `SPECIFICATION.md` and "suite" means `scripts/_digital_twin_ci_suite.py`.

**Summary.**
- **Already done, nothing to edit:** 150, 154, 155, 156, 168, 172, 173 and the six web steps 174-179.
- **Partly done:** 145, 146, 149, 151, 152, 157, 160-166, 167, 169, 171. What is left is listed per row.
- **Still to write, or waiting on B3 measurements:** 147, 148, 153, 158, 159, 170.
- **Conflicts:** five, all set out under "Conflicts" in section 4. Four come from the NTP "synced on a normal boot" claim, which cannot hold for a boot with no SSID. One is the wire log's "unbounded" label, which is now false.

### 1. Step table
| # | M.ID | files it edits | verdict and evidence |
|---|---|---|---|
| 145 | M.SPEC.156 | SPEC Part N (N.3 :11543-, N.4 :12713-) | **part landed.** Done: the renames (`led.refresh_hz` tag in `src/asy_neopixel_driver.py`; `udp.poll_wait_ms`/`poll_idle_ms`, row :11625 with the owner's 2026-10-05 "kept"; `l2.uart_link_pause_*`/`_leak_rate_bytes_per_transfer`). The withdrawals: no row or tag remains for `l1.asy_notification_service_override_tick_s`, `l2.network_neopixel_never_connects_wait_s`, `l2.sensortask_integration_dns_query_*`, `udp.conn_tries_default`, `…starter_loop_grace_ms/_poll_ms` or `*_wdt_feed_every`. Also done: `l3.device_script_feed_step_ms` under `wdt.timeout_ms`, the fold rows (`sgp40.comp_max_age_s`, `notify.sample_max_age_s`, `led.overlay_refresh_ms`, `dev.uart_rx_ring`, `uart.flash_hold_max_ms`) and the rule rows N.4 :12724-12728. **Left:** (a) rows for U35's new tags (only step 148's conditional one); (b) `loop.uart_call_span_max_us` "Checked by" still names the device script, but the verdict is read at `tests_hardware/flash/test_uart_crossover.py:135-136` (GAP-D4). |
| 146 | M.SPEC.079 | SPEC E.3.1 :5036-5130 | **part landed:** (1) :5038-5042, :5056; (2) :5062-5081; (3) :5104; (4) :5125-5130. A.U30.12 is done: no in-body `gc.threshold` remains in `tests/test_asy_webserver_service.py` (comments only, :3772/:3843), and the `gc.threshold_bytes` row :11673 lists none. **Left:** A.U35.23's history row under the list :5044-5058, after B3 measures. "WP1+WP2" :5044 and "dev-variant" :5054 are U36's (A.U36.512). |
| 147 | M.SPEC.157 | Part N Basis cells | **to write (B3) + hardware.** 386 `l0`-`l2` rows still read "estimated" (e.g. :11758, :11969-11973, :12016). The 532 `l3`/`l4` rows stay estimated until phase C: R1/R4/R5 (H55), the bands R0 (H56). A.U19.13's `web.serving_demand_budget_b` :11775 ("post-boot free heap on dev, L4") is R1 (H44). |
| 148 | M.TEST_UNIT.324 | `tests/test_uart_comm_hazard.py`; SPEC J.7 | **to write, plant first.** J.7 :9641 still reads "The accepted trade-off is that neither test would now catch a *latency* regression below 240 ms". `DrivenTime` is at `tests/_fake_time.py:15`, but the hammers already run on `PollRoundClock` (`tests/_uart_comm_harness.py:122-158`). **UART:** test only, the plant stays in a throwaway worktree; no emitted byte, accept/reject rule or recovery timing changes. **@tunable:** may add `l1.uart_comm_hazard_clean_transaction_virtual_ms`. |
| 149 | M.TSC.086 | `tests_scripts/test_digital_twin_generated_boot.py` | **part landed:** ROUTES read by `ast` :87-95; strict JSON :110-112/:294; section keys :121; errcount parity :126; Status parity :127/:279; System path :130/:300; memory markers :167/:387-391; SGP40 instances :453. **Left:** `_normal_boot_log_failures` in the `/status` branch :124-128; the boot-sequence order (already asserted in-process at `tests/_digital_twin_construction_scenarios.py:82-84`); the comment :505-506 "Session 3's". **Conflicts:** "NTPSynced turns true" (see section 4). |
| 150 | M.TWIN.011 | `digital_twin/_fram_chip.py` | **landed:** :1-3, :31-32, :136-164 (`write_count`/`writes_at`, counted only with WEL set and more than 1 byte, :292-295), :169-170, :221-223, :277-283, :313-314. |
| 151 | M.TWIN.050 | runner `_shutdown_line()` :458-467; `scripts/_twin_process.py` `ShutdownLine` :109-121, `_SHUTDOWN_INTS` :130 | **part landed:** exit codes :135-137, NTP responder :892-896, the WDT tag :151, `_watchdog` :138. **Left (U35):** `fram_writes=`, `fram_writes_by=` and `fram_writes_unattributed=`. The sources exist: `machine._current_fram_chip` (machine.py:582), `get_loggers()` (src/asy_base_classes.py:755), `_block_addr` (src/asy_fram_manager.py:95). There is no `_module` global yet. |
| 152 | M.TWIN.051 | runner :172-203, :381-412, `_test_start` :730; `tests_scripts/test_twin_runner_test_flags.py:16-18`; `scripts/_digital_twin_scenarios.py` (three host cases) | **part landed:** section comment :469-471, 11 flags. **Left:** `--test-watchdog-fault {supervisor-raise,main-exit,block}`, its `WDT_AT_FAULT <feed_count>` line, its row in the flag table, and A.U35.31's three host-side cases. |
| 153 | M.PROC.026 | new `audit/b3/conformance.md` (from `audit/actions/SUPP_recovery.md`) | **to write.** `audit/b3/` does not exist yet (A.U35.01 opens it). L3/L4 cells go to `queue_c.md`, then **hardware R1 (H71)**. |
| 154 | M.SCR.016 | `scripts/_twin_process.py` | **landed** (U25/U27): :1-3, :27, :30-34, :238, :309. No normal-boot tolerance constant exists anywhere in `scripts/` or `tests_scripts/`, which is U35's confirmation. OF-215 stage 3 joins here. |
| 155 | M.SCR.017 | `scripts/_digital_twin_scenarios.py` | **check-only:** the mechanism has landed (:5-7, registry :402-1872). A.U35.57's text lands at step 158. |
| 156 | M.SCR.047 | the suite | **landed:** imports :37-67; `-1` readers :1004/:1197/:1341/:1408; :402; `_twin_process.py:238-250`. A.U35.05 is a procedure in a throwaway worktree; its silicon arm is **hardware R1 end (H43)**. |
| 157 | M.SCR.046 + M.SCR.057 + M.TWIN.052 | the suite :200-217, :651-666, :801-841; runner :371-378; `scripts/_check_gc_collect_sites.py:68` (conditional) | **part landed:** header, imports, tags; one attempt `_run_11_soak` :779-798, `_SoakRun` :315. **Left:** (1) the window is still clock-based: `cycles_start = time.time()` :818, filter :837 `cycles_start <= ts <= cycles_end`, and the parser returns `(float, int)` :651-666; it moves to log byte offsets. (2) `MEM_SAMPLE {time.time():.3f}` :378 becomes `ticks_ms`. (3) Keep or drop the sampler's collect, its comment :372-374 and checker row :68. (4) Measured values for :207, :212, :217, plus the comment :208-210 ("one gc.collect()+print() per interval costs nothing measurable"). **Conflicts:** the "unbounded" wire-log label (see section 4). |
| 158 | M.DOCS.066 | `BACKLOG.md` chroot entry :547- | **to write:** U35's dated paragraph after the last 2026-10-21 paragraph, before the "Session 7's `max-args`" bullet. No paragraph names the heavy-list check (`scripts/test.sh:672-682`), so U35's paragraph must. |
| 159 | M.DOCS.067 | `BACKLOG.md` `## Owner questions` :1223- | **conditional:** entry 8 (1-7 are used, :1228-1292), only if A.U35.27 finds no separating window. A.U30.02 has nothing left here. |
| 160 | M.SCR.051 | the suite Run 3 :1151-1181; `audit/b3/load.md` | **part landed:** `_SUSTAINED_FAULT` :94, escalation checks, `_LEFT_OUT` :112, CRC16 check :376. **Left:** the FRAM write-count rate assertion (needs step 151's field) and `load.md`. |
| 161 | M.SPEC.076 | SPEC E.1 :4748-4758 | **part landed:** the code from A.U35.24 (1)-(2) is in: `scripts/test.sh:672-682` (exit 2) and `tests_scripts/test_test_sh.py:1988`, `:1995`. **Left:** the SPEC clause "the heavy-file dispatch list is checked against the file set" at :4753-4754, and (3) re-measuring the list order in B3. |
| 162 | M.SPEC.085 | SPEC E.9 :5690-5775 | **part landed:** :5714, :5723-5751, one attempt :5769-5771. **Left (U35):** the calibration clause, after measurement. The history bullet :5708-5714 is U25/U27's stage, not landed. |
| 163 | M.SPEC.129 | SPEC I.4(e) :8886-8887 | **to write** the outcome over "kept while a sparser sampling interval gives Run 11 the same verdict". The release proof is phase C. |
| 164 | M.TSC.084 | `tests_scripts/test_digital_twin_ci_suite_soak.py` | **part landed:** :133-141, :300, :310, `fixture_device`. **Left:** offset cases and a backwards-clock fixture; the current cases :28-43 are timestamp pairs. |
| 165 | M.TSC.095 | `tests_scripts/test_gc_collect_sites.py`; checker :67-69 | **landed** (U30); U35 only decides the `_mem_sampler` row :68, with the line. |
| 166 | M.TSC.165 | `tests_scripts/test_digital_twin_ci_suite_errcount.py` | **part landed:** :83-95, :213-269, :324, :378, :440, :519-560, :586-591, :611-616, :701-742. **Left:** `fram_writes*` parser cases; normal-boot cases (one W fails; an NTP entry fails). **Conflicts:** Run 1's NTP cases (see section 4). |
| 167 | M.TWIN.059 | README Fidelity table :187-269 | **part landed:** the FRAM write-count row :264. **Left:** A.U35.31's row ("a runner-cancelled `main()` keeps the loop and the WDT countdown alive"). |
| 168 | M.TWIN.063 | README :559-596 | **landed, check-only:** :570-584. A.U35.09 needs no README line. |
| 169 | M.TWIN.064 | README CI suite :612-863 | **to write:** Run 1 :669-679 "reads, keeps and checks the logs … then clears them". **Conflicts:** "NTP synced" (see section 4). |
| 170 | M.TWIN.065 | README :864-923 (+ :332, :780) | **to write:** :867 head; :869-870 "deliberately has no REST route" is stale (`MemFree` is at `buildgen/codegen.py:669`, SPEC :971); :873-875 wall-clock join becomes `ticks_ms` plus log position; :876-877 the B3 verdict; :892-896 "wozi's original 40"; "one attempt decides (no retry)"; `MEM_SAMPLE <time.time()>` at :332/:780. **Conflicts:** the wire-log label (see section 4). |
| 171 | M.TWIN.066 | README Runner flags :429-472 | **part landed:** 11 test flags :455-466, exit codes :472. **Left:** the `--test-watchdog-fault` row, the `main-exit` sentence, and the `fram_writes*` fields in the shutdown-line text :466-470. |
| 172 | M.TWIN.074 | README :597-611; `tests_hardware/twin_record.json` | **landed** (doc). A.U35.49 is a re-record at both GC stages after B2 and after B3: the record's content changes, its inputs (`scripts/record_twin_instrument_runs.py:27`, `:91-94`) do not. OF-229 attaches here. |
| 173 | M.TWIN.110 | `tests/test_digital_twin_fram.py` | **landed:** :774, the SF-B13 cases :414-505, :727-830. |
| 174 | M.WEB.003 | `js/poll-manager.js` | **landed:** :12-13, `tick()` :150 with no guard, :142-148. |
| 175 | M.WEB.026 | `js/nav.js` | **landed:** :20-22, :38-50, :58, :90. |
| 176 | M.WEB.025 | `js/shell.js` | **landed:** :17, :24, :50, :92, :120, :159. OF-144 is still open here. |
| 177 | M.WEB.030 | `js/main.js` | **landed:** :7-9, :34-39. |
| 178 | M.WEB.031 | `js/app.js` | **landed:** :6-10, :87-92. |
| 179 | M.WEB.051 | `tests_js/poll-manager.test.js` | **landed:** :1-2, :8 tag, :376, :421, :441, :492, the one `useRealTimers` :191. |

**Marks.**
- **UART:** only step 148 touches it, and only in a test. Step 145's UART rows are docs and have landed. No step in this range changes the wire.
- **@tunable:** step 148 may add one tag. Step 157 changes values only. No `error_catalog.json` row is added.
- **Twin record:** step 172 re-records; no step in this range edits a twin-record input.

### 2. Carried actions, each placed on a step
- A.U35.23 → 146; A.U30.12 → 146 (landed)
- A.U35.56 → 147; A.U19.13 → 147 (phase C)
- A.U35.06 → 148
- A.U35.39 → 149 and 154
- A.U35.28 → 151, 160, 166 (open); 150, 167, 173 (landed)
- A.U35.31 → 152, 167, 171
- A.U35.52 → 153
- A.U35.38 → 154 (confirm), 166, 169
- A.U35.57 → 158 (and 155's blast)
- A.U35.05 → 156 (procedure)
- A.U35.25 → 157, 163, 165, 170
- A.U35.26 → 157, 164, 170
- A.U35.27 → 157, 159, 162
- A.U27.17 → 159 (conditional), 170
- A.U30.02 → 159 (nothing left)
- A.U35.24 → 161
- A.U35.09 → 168 (nothing to add)
- A.U35.49 → 172
- A.U35.46 → 174-179 (landed)
- A.U0.54 → 170 (conflict); A.U11.08, A.U30.09, A.U25.46, A.U27.08, A.U30.17 → 170

### 3. Open findings in this range's files
- **OF-144** (`js/shell.js:104-110`): open. The watch compares only against the first build it sees, and the page reads no build date. The stager already writes `<meta name="build-date">`. Joins step 176.
- **OF-215 stage 3**: open. The harness should end a twin through the runner's `--stop-file`, with SIGINT only as the fallback; this changes `shutdown()` in `scripts/_twin_process.py:366-388`. Joins step 154, with harness boots at step 155.
- **OF-229** (`scripts/record_twin_instrument_runs.py:125-131`): open. Joins step 172's re-record, or P1c's M.TWIN.054 step; P2 picks one.
- **Nearby, but not in this range's files (P2 assigns):** OF-214 (`tests_js/live-backend-put-matrix.test.js:269`; the runner plants `DNSFallback=""` at `digital_twin/unixport/_offline_ntp_config.py:27`) and OF-231 (`tests_js/mock-data-compose.test.js`).

### 4. Packet vs code
**Renamed or moved since the packet was written:**
- `_print_wdt_status` is now `_shutdown_line()` (runner :458), plus `_print_shutdown_line` (checker :69).
- `TestFlags` has 11 fields, not 7.
- `@scenario` takes `family=`, `shared=`, `moves=` and `first_device=`.
- `_fram_chip.py` is 323 lines (the packet cites :1-157).
- `UART_Comm` is now `UARTComm`.
- The heavy-file list has 10 entries, not 15, and its check landed early.
- `rate.persisted_log` is a C/F rate-table row (SPEC:6438, 627-700 ms per chunk write), not a Part N row. Step 160's bound therefore has to be derived (agent, 2026-10-21: window ÷ 627 ms × 2 block copies, stated beside the assertion).
- `l0.cross_browser_smoke_poll_ms` does not exist; the smoke's rows are the `l0.smoke_*` rows at :11742-11757.

**Conflicts.** Each is decided on the owner's behalf (agent, 2026-10-21), taking the more conservative option:
- **NTP sync on a normal boot** (steps 149, 166, 169; also P1c's M.SCR.049). Run 1 and the generated-boot smoke start with no SSID. The runner writes only the NTP config (`_offline_ntp_config.py:19-41`); the SSID is first set in Run 5 (:1226) and Run 6 (:1357). Run 1 asserts both time fields are null (suite :1090-1098; README :669-671), and SPEC:5737-5738 says "a fresh hotspot-mode boot never syncs NTP". **Decision:** the normal-boot check asserts no E or W entry, read before `l2.scenario_shared_boot_deadline_s` (SGP40's untimestamped-backup W lands after it), with no NTPSynced requirement. NTP sync stays proven at Run 5 :1236 and Run 8 :1409. The step 166 NTPSynced-bound case targets `_wait_for_ntp_sync` (:1713).
- **The wire log's "unbounded (agent, 2026-09-14)" label** (steps 157, 170; A.U0.54). The wire log is now bounded: `digital_twin/machine.py:809` `_WireLog(_WIRE_LOG_MAXLEN)`, runner :833-834, README :881. **Decision:** keep the tree's wording.

**Packet parts that belong to other units:**
- **M.SCR.046** wanted no `global` left. U27 instead added a reasoned per-file PLW0603 entry (`pyproject.toml:309-312`), and the tree keeps that.
- **I.4(e) item (6), the DebugLevel sentence,** is absent. It was U30's stage; REGISTER.md:729's owner decision governs, and P2 should rule on it.
- **The two U18 hotspot owner-question entries** are absent. They were not U35's to write.

**Not settled by reading:**
- Whether a 20/100 ms plant turns the `PollRoundClock` hammers red (step 148): run the plant.
- The sampler verdict and the Run 11 window calibration (steps 157, 162, 163, 170): the B3 runs.
- Whether a boot with no SSID logs a W inside the smoke's window: one twin boot.

### 5. Files and the steps that edit them
- `SPECIFICATION.md`: 145, 146, 147, 148, 161, 162, 163
- `tests/test_uart_comm_hazard.py`: 148
- `tests_scripts/test_digital_twin_generated_boot.py`: 149
- `digital_twin/run_generic_integration.py`: 151, 152, 157
- `scripts/_twin_process.py`: 151, 154 (OF-215)
- `scripts/_digital_twin_scenarios.py`: 152, 155 (OF-215)
- `tests_scripts/test_twin_runner_test_flags.py`: 152
- `scripts/_digital_twin_ci_suite.py`: 157, 160
- `scripts/_check_gc_collect_sites.py`: 157/165 (conditional)
- `audit/b3/{conformance,load,timing,queue_c}.md`: 153, 160, 146/147/157, 153
- `BACKLOG.md`: 158, 159
- `tests_scripts/test_digital_twin_ci_suite_soak.py`: 164
- `tests_scripts/test_digital_twin_ci_suite_errcount.py`: 166
- `digital_twin/README.md`: 167, 169, 170, 171
- `tests_hardware/twin_record.json`: 172 (plus `scripts/record_twin_instrument_runs.py` for OF-229)
- `js/shell.js`: 176 (OF-144 only)
- No edit (landed): `digital_twin/_fram_chip.py` (150), `tests/test_digital_twin_fram.py` (173), `js/poll-manager.js`, `js/nav.js`, `js/main.js`, `js/app.js`, `tests_js/poll-manager.test.js` (174-179)

**Hardware rounds:**

| Round | Item | Steps |
|---|---|---|
| R0 | H56 (speed-probe bands) | 147 |
| R1 | H44 (post-build free heap) | 147 |
| R1 | H55 (estimated l3/l4/web tunables) | 147 |
| R1 | H71 (silicon-only rung cells) | 153 |
| R1 | H83 (loaded `MemFree` floor; documentation only here) | 170 |
| R1 end | H43 (hardware memory gates turn red) | 156 |
| R4, R5 | H55 | 147 |
| phase C | release proof | 163 |
