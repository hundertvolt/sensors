U3a hand-back (lane U). Commit **4d6568f** on f6f54cc, branch audit/u35-u, S/wt-u35u. Nothing uncommitted, and nothing of mine is running.

**Steps**
- **Hazard mode: partly applied.** `src/asy_uart_link_driver.py` gains `request_hazard_run()` and `get_hazard_report()`.
  - The command is dispatch-only and nothing is stored. It is refused on the responder, before setup() and while a run is pending. The exercise loop runs it in place of its next round, then the echo resumes.
  - It runs three hazards: two initiations at once, both ends transmitting, and the field sweep over the script's boundary values (H3). It reports facts for the reader to judge.
  - It is not counted in Transfers/Failures. `get_link_status` is unchanged.
- **Deviations from the set:**
  - Stalled TX is left out. A re-init needs the port and pins, and the driver keeps only rxbuf, baudrate, _txbuf and rx_ring (asy_uart_driver.py:472-475).
  - H1b is left out, because the lead's list does not name it.
  - Both ends transmitting is done from the initiator alone: a raw GET with a SET right behind it. The script's own form needs the responder's TX, and the live listen loop holds that lock indefinitely (see the clear() comment, asy_uart_comm.py:1053-1056).
- **Not wired; needs lane C (I stopped before touching codegen.py and definitions.py):**
  1. A dispatch-only PUT key, for example `{"UartHazards": true}` on /status beside ResetErrors, that calls `uart_link_init.request_hazard_run()` and answers VALID or FAILED. This needs `_put_status` in asy_webserver_service.py (not my file), a route field, the codegen emission, and definitions.py:55's dispatch-only list.
  2. A maintenance entry `("UARTHAZARD", uart_link_init.get_hazard_report)` beside codegen.py:539, plus definitions.py:716 if the page or API reference lists status keys.
- **148: applied.** J.7 states no figure for this measure, so the bound is now the measured 4 virtual ms with no margin (was 14); green at head. The plants measured 44/204/279 ms, all over 4, so both stay red by monotonicity; I did not re-run them.

**Effect per device and mode**
- Only dev wires `uart_link`. arzi, grkizi, klkizi, schlafzi and wozi do not construct this module, so nothing changes for them.
- On dev, until the route is wired, the only change is one flag check per round.
- Once wired: STA and AP can start one bounded run. Silent and Off have no API, so the mode is unreachable there. USB is unaffected.
- No boot ever starts in the mode. The flash-wear gate is untouched (nothing persists). The wire format, accept/reject rules and timings are unchanged.

**Seen failing and bites** (logs in S/u35/laneU/u3a/)
- Against the unchanged source the file fails at load: "KeyError: _RECOVERY_ATTEMPTS is not a const()".
- pending_kept: the run never ends (fails at run_until at 21716 ms).
- serial_inits: caught by the run bound, not by the verdict line.
- no_quiet: the chunks verdicts come out `[F,F,T,F]`.
- no_echo_return2: the echo wait fails 1000 ms after the run. My first echo bite was mis-aimed (the run never started) and was redone.

**Found and fixed**
- In the live loop, rejected frames grow the responder's listen backoff up to 5 reply budgets, so an ACK landed in the next value's window. The ACK window and the wait before each recovery are now 8 reply budgets.
- Under DrivenTime, setup() and clear() must not be awaited outside run_until (they hang), and tasks must be stopped rather than cancelled.

**Open thread:** in the mock the crossing logs NO_ACK, not PEER_INITIATED, and the first recovery try also logs NO_ACK. The test pins `errnos == [85, 81, 81]` (tests/test_asy_uart_link_driver.py, crossing block). This is deterministic in both CRC modes, but I did not trace why the first try fails.

**Red check:** tests_scripts/test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree has 5 rows with no Part N row: src :50, :52, :54, test_asy_uart_link_driver.py:489 and test_uart_comm_hazard.py:1383. It waits on D (R-17).

**Other checks**
- ruff is clean. mypy reports 0 for both the no-args pass (264 files) and `src tests tests_hardware/device_scripts` (230).
- The 12 checks: the only other red was test_code_conventions on two quoted annotations, now fixed and rerun green.
- mpy-cross: base 1879 B, head 3516 B. They differ, as expected for a behaviour change.

**Times** (s, paired base→head)
| file | -1 | 32768 |
|---|---|---|
| link_driver | 2.33 → 3.51 | 2.39 → 4.49 |
| hazard | 103.96 → 103.95 | 108.14 → 108.28 |
- Final link_driver head: 3.42 and 4.73. The growth is the new check, about 0.55 s per CRC mode at -1; the file stays under 10 s and is stated per note 20.
- It could be made cheaper with a coarser idle poll for this pair; not done.
- On dev, the 1000 ms timeout scales a run to about 3.6 min. U3b's twin will take that in real time.

**Rebuild:** all six sensortask files changed, including devices with no `uart_link`. This fits the embedded `_BUILD_DATE` stamp rather than my edit.

**Relay:** 5 `<TAG>` lines under `## D`; one Class B candidate line under `## P` (Python-internal, no C impact, only if the changelog logs exerciser changes).

**Decisions (agent, 2026-10-21)**
- Verdicts are facts judged by the reader, so `src/` holds no second copy of the J.3/J.4 rules.
- The both-ends live form, the omission of H1b, and the 8-budget window.
- The run bound is 21716 virtual ms: measured, no margin.

**Not done:** the formal silent-failure scan (CHECKLIST 16) and the 17 repo-wide scans. Both are for U3b as U's last block.

**Runs:** probe pid 1808 timed out at its own 240 s limit (the setup hang, now fixed); runall pid 4485 rc=0; both logged in RUNS.md. Disk had 9.2 GB free and at most 3 heavy processes ran.

**U3b starts from 4d6568f:** the C/webserver handover for the route; the twin test under API load; the bench test with `--collect-only`; the open thread above; the scans and readers.

