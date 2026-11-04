# R3 action list, the lead's complexity read of ROWS.md (lead, 2026-11-04 16:21 UTC)

Basis: `ROWS.md` (phase A), PLAN.md's R3 row, the owner's "Generally target low complexity" and 06:11's "take extra
care that we are not currently creating a runaway, self-inflicted complexity increase"; 16:16's "Work which has to
be done anyway and which is independent and does not cause interference can already be started".

1. **A2 cut.** The twin record and its test are not committed to the product tree again. The runner's JSON and the
   listed exceptions go to `S/u35r/r3/m/` and into the next snapshot's evidence. Reason: the owner's "ok"
   (`twin-first-for-instruments`) names the runner and listed exceptions; R0 removed the ~1,600 lines. Stated in R3's
   report as a decision taken on the owner's behalf.
2. **A1 in its smallest form.** The full soft-callback queue test (~79 lines, `tests/test_digital_twin_timer_pool.py`)
   goes in: it is the only test of the product's recovery after the drop. The DNS flood goes in only inside a boot
   the exclusive port-53 leg already makes: no new boot, no timeout change. If it needs its own boot it is not added;
   reason for the report: L1 (`test_asy_captive_dns.py:149`, `test_asy_wifi_service.py:4025`) and L4
   (`bench/test_hotspot_role_reversal.py:219`) cover it, and L2 would add one boot to each of 12 jobs.
3. **A3-A9 only on a real gap, and the lead admits each.** No lane adds a test for a gap on its own (except A1): each
   gap goes to the hand-back with its evidence (a surviving plant, an unexecuted error path, a forced interleaving, a
   missing cell with no test anywhere) and the proposed test in one line. One fix round then adds the admitted ones.
4. **A10** goes to `digital_twin/README.md`'s existing fidelity table only as rows; a disagreement that needs the twin
   corrected is the last round's (PLAN), not R3's.
5. **Working tables stay working records** under `S/u35r/r3/`: the matrices, load, timing, conformance (rungs, bus
   hazard, wear). Each cell is a test name or a reason in a few words. `audit/b3/*.md` stay as they are until D.
6. **Limits for the owner** (OR19, OR39): stated in R3's report, one sentence each; no question. OR29.a (2)'s
   "no datasheet" limit is withdrawn (owner, 16:30: all are in `hundertvolt/datasheets`, `/home/user/datasheets/`).
7. **"owner" items**: a dead line from the coverage sweep is listed, never removed; a U35-37 class (a) hit is listed.
   Both go to the owner only if found.
8. **R2 carries** `--only` and `ss`: the findings list (D1 writes the two lines in its hand-back).
9. **Lanes** (the owner's parallel scheme; disjoint files, one test run at a time):
   - **M** (`S/wt-r3`, branch `audit/r3`): every test run (P2's collect-only, coverage, plants, the twin instrument
     runner, the heap probe, the bench probes on the twin), A1, then the fix round and R3's gate.
   - **D1** (read-only, `S/wt-u35int` at `17688315`): OR16 (2) skip reasons, OR19 verdicts, OR25 and OR26
     subtraction, OR37 and OR38 read, U35-37. Static walks only (seconds, no ports, no test runner, no build).
   - **D2** (read-only, `S/wt-u35int`): OR41 with U35-09, OR49 cells, U35-52 rungs, the bus-hazard and wear tables,
     round 1's P1, P4, P7 and P8.
   - The D lanes never read `S/wt-r3` (M plants faults there). They write only under `S/u35r/r3/d1/` and `d2/`.
10. **Close**: the lead admits the gaps, one fix round in `S/wt-r3`, R3's gate (both stages), the falsification
    check, the merge, a snapshot, CI, the report.
11. **D1's gaps** (2026-11-04, lead verified at the source in `S/wt-u35int`): admitted for the fix round (lane M):
    - G1: `test_start_timer_degrades_when_the_alarm_pool_is_exhausted` (ISL29125) takes its siblings' assertions;
    - G2: the twin BMP3XX power-cycle test checks the error slots too and the chip's reset values its name claims;
    - G3: `test_the_lowered_uptime_limit_leaves_the_output_unchanged` goes with its mechanism (the 16383 limit,
      gone in `1206e862`), with any doc line naming it;
    - G4: the runner's five behaviour tests come back from `497b3eda:tests_scripts/test_twin_record.py` (`:23-48`,
      `:83-138`), smallest form, no committed record (A2 stays cut): the runner stays, so its behaviour keeps a test.
    D1's slip: one `rm` on a variable path, its own scratch file in `d1/`; recorded, nothing else touched.
12. **D2's gaps** (2026-11-04, lead read against the bench research and `b4341646`):
    - G1 admitted: the fallback half of the SCD30 twin test `b4341646` removed with W73 (edge muted, pin held high,
      one read within `_trigger_half_ticks`, no entry); the fallback stays in `src/`, so its L2 cell keeps a test.
    - G2 admitted: the flash tier's loop-lag test goes into `PERMANENT_SKIPS` with its reason (on silicon it needs
      the bench network, so its silicon run is the bench tier's; RESEARCH 7); one line, no check weakened.
    - G3 admitted: `uart_comm_hazards.py` adds both drivers' counters and each link logger's newest entries to a
      failing exchange's facts (test side only; PLAN round 1's crc16 rerun needs them).
    - G4: throwaway scripts in `S/u35r/hw_handover/mp/` (outside the tree), one per row, plus `long_fram.py`'s 8 MHz
      overnight edit; a row needing the owner's hands states its setup on the sheet. Lane D2 writes them.
    - Also into the fix round: D1's G2 takes the BMP388's reset values from DS001 Table 24 (p. 30), not the test's
      "x1, no IIR", and `SPECIFICATION.md:364` states the same; `src/asy_scd30_driver.py:171`'s `Datasheets/` path.
    - D2's slips: one read-only `python3 -c` outside run.sh; one `sed` put dev.toml's hotspot value in its terminal,
      in no record (the lead's scan, before 17:13 UTC, time not taken, found it only in lane M's `ftmp/` source
      copies, never published).
13. **D2's follow-up** (G4): nine throwaway scripts in `S/u35r/hw_handover/mp/`, host-compiled, none run; the sheet
    names each row's instrument. The lead's edit to `long_fram.py`: it feeds the watchdog the final image's boot
    arms (a soft reset leaves it armed), every 64 iterations beside its existing 1 ms sleep; D2 had found it would
    be reset within about 8.4 s. Lead's slips in that edit: the compile check ran outside run.sh, and the
    `__pycache__` cleanup `rm` sat in a compound command, not its own call (literal path; nothing else touched).
14. **Lane M** (hand-back before 19:19 UTC, `HANDBACK_M.md`): six runs done, A1 `26705ef8` (+121/-12: the
    timer-pool test, and the DNS flood inside the existing hotspot boot, its wait loop now one helper it reuses). Lead
    read the diff: no new mechanism, no new file. Admitted for the fix round:
    - G1: ContMeas False with the stop command NAKed answers `Failed` and logs one E (its test went with `dddb3902`);
    - G2: a runtime I2C `clear()` with SCL held lets a sibling task run (plant `r3.i2c.stretch_yield` survived);
    - G3: `listener_close_leaves_the_pcb_pools.py`'s twin half takes a port below the host's ephemeral range;
    - A10: fidelity rows 1-5 into `digital_twin/README.md`'s table; the three twin corrections are the last round's.
    Changed by M's probes: item 12's `SPECIFICATION.md:364` line is withdrawn (the bench's part read OSR 0x00, the
    datasheet and twin 0x02: round 1 sheet row 16b settles it); D1's G2 compares against the twin model's own reset
    values, no literal. Not for the snapshot: `m/data/plant_set_r3.py` (a planting script, SNAP_EXCLUDE).
15. **Fix round** (lane M's hand-back before 21:17 UTC, time not taken; `5613c35e`, +219/-41 on `26705ef8`). Lead
    read the diff: tests and records only, one new file (the runner's restored tests), no new mechanism; `src/` one
    comment line, bytecode equal. Item 10 (M stopped it): admitted the close-order fix M measured, the client closing
    before the accepted connection, so its TIME_WAIT holds the client's ephemeral port, not 30100 (rp2 never connects).
    Lead's commit `13a833c7`; red first was M's `r3m_fx10_try` (1 of 10), then `r3_lead_lc10` and `r3_lead_lc10b`
    10 of 10; `r3_lead_lc` lint, three mypy passes and the test green. Ruff's TRY300 on the first form fixed by
    an `else:`. Falsification brief `FALSIFY_BRIEF.md`, worktree `S/wt-r3f` at `13a833c7`.
16. **Falsification** (`FALSIFY.md`, 21:52 UTC; lead verified each refutation at the source). Fixed in `66e42f05`,
    each new assertion red on the agent's plant (`r3_lead_plants`, `r3_lead_plants2`), then green at both stages
    (`r3_lead_green`, every device for the timer pool; the DNS scenario wozi -1 and dev 32768; `r3_lead_hazards`):
    - 1(b) a one-second timer fires at most once in the spell; 1(c) the answer after the flood is checked like the
      first, and the flood gets no reply; 2(d) a sibling runs between any two reads of the held SCL (the first form
      missed reads after its last turn; caught on the re-run); 3 the summary writes the staged line only once a board
      took the stage; 5 h2's log is read after the recovery again; README row 241 and the listener comment corrected.
    - 1(a) not changed: the tick plant turns a PERIODIC timer one-shot, which the unit tier pins
      (`tests/test_asy_base_classes.py:1033`, `test_arm_tick_timer_arms_a_periodic_one_second_timer`).
    - Not restored: the record-format checks that went with the record in R0 (A2 stays cut; only the evidence reads it).
    - Port 30100 gets no row in `tests/_port_bands.py`: no device script's fixed port has one (50100 had none).
    - Owner item, listed, kept: the generated `_system_cmd_callback`'s last `return False` is reachable by no product
      path (its one caller passes a member of `_SYSTEM_CMDS`); lead's recommendation: keep it, since without it an
      unknown command would fall into the last case, erasefram.
    - To the findings list: twin.md's uart_crossover row holds one (c) case; the SGP40 quality red at 32768 only is
      unexplained; `named.fram_alloc`'s "comparable allocation" reading is contested.
