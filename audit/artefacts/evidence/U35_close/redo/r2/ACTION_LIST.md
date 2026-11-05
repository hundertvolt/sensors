# R2 action list (lead)

1. 2026-11-04 13:42 UTC, O-lock-1..5 (the one port lock): not done, lead decision. Removing the CPython and JS locks
   needs a wrapper that holds the shell lock around npm's live tiers and the smoke (a new mechanism), and leaves the
   documented direct run of `scripts/_digital_twin_ci_suite.py` with no lock; R2's bounds (nothing grows, one fix
   round) and its remaining share do not hold that. The three locks stay as they are; offered to the owner in the R2
   report as a possible later item, not proposed.
2. Phase B's diff read for self-inflicted complexity (lead): 332 lines added against 3,745 removed; the additions are
   the loop end's reset, the idle event's `_own_backup` (replacing the 89 s retirement), the bounded waits' four
   limit constants, `_PROBE_LEAD_MS`, the merged twin leg in `run_digital_twin_ci.sh` and doc lines stating values
   that left the register. No new mechanism, no new file. `src/` changes are comment lines only.
3. LIST section 6's other phase-B carries, not in BRIEF_B (the hand-back's list): out of R2; they go to the later
   rounds' queue with their LIST rows.
4. 2026-11-04 14:16 UTC, the falsification (`FALSIFY.md`), verified by the lead:
   - Claim 1, doc part: confirmed (F.5.4 still has a Ctrl-D reporting 22 or 10 + p; two L1 tests drive that path,
     `test_asy_system_service.py:3666-3679, :3700-3711`). Fix F1.
   - Claim 2, `_own_backup`: confirmed from the code (`_digital_twin_scenarios.py:384-389` never looks at the count
     moved) and the agent's planted case. Fix F2.
   - Claim 3, captive DNS: confirmed (`asy_udp_socket.py` sets `_sock` before `bind()`; `connected` is set only after
     it). Fix F3.
   - Claim 5: the lead's wording error, not the change's. The eight firmware rows (facts or derived), the six
     `devices/dev.toml` rows (config) and the L2 harness values were LIST 5.1's N1, N2 and N4 out rows, which the
     owner's 11:23 answer took. No fix.
   - Claim 8: wording only (four code files grew by 1-5 lines with the loop end and the merged twin leg). No fix.
   - D1: confirmed (b315f98b removed the BMP3xx twin's EVENT register with the knob; the conformance probe reads it,
     `bmp3xx_conformance_probe.py:84-85`). LIST's N-knob-1 had it wrong. Fix F4.
   - D2: plausible, hardware-only; the test is made independent of the old watchdog delay. Fix F5, then round 1's
     queue (first bench run of the changed test).
   - D3 and the await-depth row's citation: fix F6.
   - The twin job's margin rests on this host's 54.5 s: read against the snapshot CI's job time, no change now.
5. Fix round (b930a5be..17688315, 7 commits on 433d53b2) read by the lead: 75 lines added, 59 removed; F1-F6 as
   briefed, F5 keeping the phase fact as "only a wrong phase fails" (the facts-parse rule needs it); one new test, F2's
   regression case. Gate green (test.sh both stages on 17688315; twin suite and harness both stages on 20b691bf).
   Held for the owner's word on the 39 % unit stop (15:38): no merge, no snapshot until then.
