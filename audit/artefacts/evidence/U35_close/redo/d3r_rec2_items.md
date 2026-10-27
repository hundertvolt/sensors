# Items collected for D3r (docs) and REC2 (records) from the redo's hand-backs (lead, 2026-10-27)
Append-only; each line names its source hand-back in S/u35r/handbacks_redo/ or the LEAD NOTES number.

## D3r (docs text; SPEC lines re-located on the head)
- REDO.md's D3r list (V4 158/162/163, E.9 history bullet, E.2.1 device sentence, E.5.1 register, the sampler outcome,
  F3r's stale lines, C.14.1, F1r's and F2r's D3 facts, SPEC:229, 3059-3060, E.2.1, E.5.1, cur_task, A.8 import gap, I.4(e),
  C.13's is_ready wording) - from the summary of the earlier portion.
- digital_twin/README.md's fidelity table, Network row: name `--test-pin-send-buffer` (T4r2d.md, "Notes").
- tests_hardware/README.md's soak paragraph and the resume-exec entry: check they read as one account (N9.md, N10.md).
- The py/js summary field names `not_clean_reason`/`notCleanReason` now carry code 3's reason too: a comment or a rename
  question (CE2r.md, "Decision for you to review"; LEAD NOTES 203).

- SPECIFICATION.md K.10's planting rule restated with the owner's scope (CFr.md, "For D3", its proposed sentence).
- F.1's 2**30 run sentence once T4r3b finishes (T4r3.md item 5, with the real figures).
- SPECIFICATION.md E.2.1 (near :5159-5163): the integration file's driver-specific scenarios run on every device
  whose plan wires their drivers (CMr1.md "D3 sentence"), updated by CMr1b's deduplication if it lands.
- E.5.1 / CEr's e51 table: src/asy_system_service.py's `return` guard near :453-454 is unreachable in today's wiring
  and kept under the library rule (CFr2.md item 1; LEAD NOTES 219); F1r's "reachable by a cancel" refuted.

- README.md near :662: state the `--config-dir` trailing-"/" rule the runner now enforces (N12.md item 1(c); LEAD
  NOTES 230).
- SPECIFICATION.md near :4971-4974: the tests_scripts tier now also waits for the site builds, so every devices/ glob
  (build_device_websites.sh included) runs before it (N12.md item 3; LEAD NOTES 230).

- SPECIFICATION.md E.5.1: CEr1's proposed text, verbatim in S/u35r/handbacks_redo/CEr1.md ("Proposed E.5.1 text for
  D3r"): the two new tracer artifacts appended, the kept-and-uncovered list replacing the "Separately" and FRAM
  paragraphs, three stale entries dropped (LEAD NOTES 233); CEr2's covered rows applied first.

- SPECIFICATION.md E.10/E.5.3: name the checkout-write guard, its three exemptions and the kept coverage data on a
  failed render (N14.md "OWED"; LEAD NOTES 238).

- F.1's 2**30 run sentence, now with the real figures (the item above): T4r3c.md item 5 holds the agent's text (84 L1
  files, 109 jobs, 654 runs; all six derived devices' twin suites with the wrap inside Run 11's window at both
  stages, no memory marker); LEAD NOTES 243.
- SPECIFICATION Part F (Unix-port facts; CMr1e suggested F.7): with a non-fd pollable registered, the Unix port's
  zero-timeout poll waits 1 ms (v1.29.0 extmod/modselect.c :344-381 against rp2's :383-397), plus
  digital_twin/unix_port_idle_poll.py and the one file it applies in (CMr1e.md; LEAD NOTES 245).
- SPECIFICATION.md :3753-3754, the owner's Q10 answer (option a, owner, 2026-10-27). The sentence states that
  `Synced` clears at the first 10 s check at or after the last success turns three intervals old. It is a signal
  that the NTP setup may be wrong, not a precision bound, since the interval is arbitrary. No firmware change
  (S/u35r/recovered/owner_rulings_after_LN118.md, Q10; LEAD NOTES 249).

## REC2 (audit records)
- OF rows for: the D.15 counts over the unchecked scopes (N8.md; LEAD NOTES 198, owner question pending after Q10);
  the ~40 untagged real-time waits (N10.md item 2; lane N11 planned); the lint gap that lanes' ruff runs skipped
  build/generated_src (LEAD NOTES 204); the four live-read families (N9.md; closed by N9).
- Refusals: F4c2's (LEAD NOTES 194), CRr1b's (LEAD NOTES 210), the lead's heredoc slip (LEAD NOTES 196).
- The F811 exemption added to pyproject's generated boot-entry block (LEAD NOTES 206): named to the owner.
- F4e's torn+phase consequence (practically unreachable; F4e.md); F4c3's elf_symbols duplicates (closed by N10).
- LEAD NOTES 106 (b): the hold's feed-gap residual (about 3.3 s inside the 6000 ms check) to the records.
- CFr's shell-rule breaches, from its own hand-back: nohup runs, and once an rm with an unguarded "$S" glob
  (nothing lost); its plant runs leaked eight interpreters before plant.py killed process groups (LEAD NOTES 212-213).
- CMr1b's refused command (`timeout 100 tail --pid=... -f /dev/null; awk ...`, "Irreversible Local Destruction"; LEAD
  NOTES 226), not retried; named to the owner.
- The live tier's config-file leak (about 1000 files in /tmp from makeConfigDir() without its separator), fixed by N12
  and the files removed by the lead (LEAD NOTES 230); N13's template-literal blind spot.
- CRr2b's deviation: a `find -exec rm` inside its own plant copy (nothing lost; CRr2b.md "Deviation"; LEAD NOTES 231);
  and its D.15 re-sort of bench/conftest.py while the owner's D.15 question is pending, undone by CRr2b2.
- N13's two observations ruled by the lead (LEAD NOTES 233); CEr1's offline render failure (dumps deleted) and the
  root config_SYSTEM.cfg leak (N14).
- CMr1c's deviation: batchB (bus_hazard) ran under six heavy processes, above CHECKLIST 12's four (LEAD NOTES 235);
  its two D.15 reorders of pre-existing code, reverted by CMr1d.
- CEr2's deviation: some debug runs outside the namespace, summarised in RUNS.md (LEAD NOTES 236).
- CRr2b4's refused command (an inline edit chained with `[ -d "$P" ] && rm -r "$P"`, "irreversible local destruction";
  LEAD NOTES 237), not retried; its plant tree S/u35/laneC/crr2b4/plant_i1 left in place by the lead; its plant run
  outside run.sh (a deviation). Named to the owner.
- REC2: the owner's Q10 decision (the NTP stale rule's tick slack, option a, verbatim in
  S/u35r/recovered/owner_rulings_after_LN118.md) gets its register row with the date (LEAD NOTES 249).
- REC2: the owner's D.15 decision ("Option d is fine", owner, 2026-10-27): the tree-wide D.15 sweep over the seven
  unchecked scopes and js/, plus the check over all scopes, are staged to U37 in the register, with N8's counts
  (tests 31/136, tests_scripts 91/201, digital_twin 1/23, buildgen 11/26, scripts 7/16, toolchain 2/2,
  tests_hardware 10/163; js/ not measured) (LEAD NOTES 251).
- Correction to the D3r F-row item above (LEAD NOTES 245): SPEC F.7 row 30 (:7401) already states the 1 ms poll
  (written at U35's lane V), and OF-243 routes its end state (an override in toolchain/micropython_overrides.py) to
  U36. D3r writes no new F row. If digital_twin/unix_port_idle_poll.py lands, D3r adds at most a clause to row 30
  naming the helper as interim, in the files that use it, until OF-243's fix; the helper's README entry already carries
  its removal trigger (P36a.md, contradiction 4; LEAD NOTES 252).
- D3r direction rule (P36a.md, overlaps): the docs hold current state, so the E.9 item (V4 step 162) is written as a
  current fact, never as a history bullet (A.U36.548 would only remove it again). Where a D3r sentence overlaps a U36
  action, write it so that action can build on it (S/u36prep/scope_draft.md lists the pairs). README :662's
  trailing-slash rule: say it where the runner's own `--help` can carry it too, if the help text is not already the
  place (LEAD NOTES 252).
- REC2: OF-139, OF-214 and OF-245 (all routed to U36, all "open") are at least partly addressed on the head. For each
  row, check which commit landed what (P36a.md, contradictions 1-3). Close it at U35 with that evidence, or mark it
  partly done with what remains for U36 (LEAD NOTES 252).
- REC2: REGISTER :806 still records the owner's deferral of U36 preparation (2026-10-22). Record the later go
  verbatim, with its date: "If it makes sense / works out, you can start preparing the next units in parallel" and
  "Still wait after U35 is done, but as I said, preparing the next units is fine" (owner, 2026-10-26;
  S/u35r/recovered/owner_rulings_after_LN118.md). Record P36a's read-only inventory (S/u36prep/) as that preparation
  (LEAD NOTES 252).
- D3r: "never raises" (the seven modules' headers; SPEC D.2/G.2). BR1 found it holds only modulo a MemoryError at call
  entry on an exhausted heap (the *args tuple, the generator, the star-call array: G.2's task-top caveat). If D.2 or
  G.2 already scopes the term that way, nothing changes. Otherwise one sentence in D.2 scopes it once. No src change
  (BR1.md point 3; LEAD NOTES 258).
- REC2 (lead, at the BR1-3 merge): the raising walk renders each verdict file's "conventions" key into raising.md, one
  short section per module, after the three lanes' JSON files are merged and the walk is re-run (BR1.md point 2;
  LEAD NOTES 258).
- Owner report: network_resilience's outage and flap tests lacked the NTP mid-flight group that CRr2b4's research
  assigned them; CRr2b10 adds it (LEAD NOTES 258). CRr2b9's nohup chain is a named breach.
- (BR3, 2026-10-27) asy_fram_driver.py's module comment and G5/R17 say it never raises; SPECIFICATION.md C.3.1/F.5.2
  say get_values() on a 32-byte-or-larger buffer can raise OSError(EIO), caught by _read_chunk(). Name the
  exception in the comment and the G5/R17 wording (docs pass; no behaviour change).
- (CMr1h, 2026-10-27) The E.2.1 replacement text for SPECIFICATION.md (lines 5159-5163 at cce274e1) is in
  S/u35r/handbacks_redo/CMr1h.md item 5; CMr1i re-checks it against its result.
- SPECIFICATION.md Part F (after HP2's verdict): one short paragraph each, citing the v1.29.0 lines. (a) A native
  asyncio Task's pairing-heap `child_last` is never cleared (py/pairheap.c:52/:59/:144 only write it), so a finished
  task can stay reachable through one that was once its parent; a heap step that repeats per in-process twin boot
  means a test linking its boots (HP1), with HP2's measured bound on product patterns. (b) rp2 builds with
  MICROPY_PY_SELECT_POSIX_OPTIMISATIONS 0, where `poll.unregister()` leaves the stream in its deleted map slot until
  reuse (extmod/modselect.c:505-520); the Unix port sets 1, so the twin cannot show it; HP2's bound.
- REC2: the raising walk's three "defect" rows (BR2's fixed mempause groups, asy_system_service :530, :713/:717 at
  7008730e) are re-classed by what the raise does on today's tree, the fix commit and its red-first test cited.
- REC2: faults.md, open_findings.md and REGISTER.md cite pre-fix lines in asy_system_service.py, asy_fram_manager.py
  and asy_base_classes.py (past :366): re-locate from BR4.md's mapping (tool S/u35/laneB/br4/tools/cites.py).
- Part F paragraphs (a)/(b) above: HP2's bounds go in: at most 8 finished Tasks held at once, chains at most 2, no
  trend with uptime or connections (twin, both stages); rp2's stale poll slots 12-17, at most about 1.4-2.3 KB.
- BACKLOG.md (owner, 2026-10-27): a new entry "upstream MicroPython findings, to report later as one bundle, if at
  all", starting with (1) asyncio's pairing-heap `child_last` never cleared (bounded: HP2's numbers) and (2) rp2's
  `poll.unregister()` leaving the stream in its deleted map slot; no firmware change, no override. The Part F
  paragraphs above point at it, and the version-bump re-check (CLAUDE.md's standing practice) looks for an upstream fix.
- REC2: faults.md and REGISTER.md cites moved by D2S's ten commits: re-locate from D2S.md's mapping.
- SPECIFICATION.md E.2.1 (:5160-5170 at 9ce2e376) and the l2.wifi_modes_sleep_scale tunables row (:12571): CMr1j's
  replacement text, S/u35r/handbacks_redo/CMr1j.md "E.2.1 text"; matrices rows from its "Matrices rows".
- digital_twin/README.md: a ThreadSafeFlag wait on the Unix port loops poll() at the ioctl call period (POSIX
  optimisations, a non-fd pollable), so a waiting LED overlay costs twin CPU (about 70 ms per persisted entry, CMr1j);
  rp2 waits in mp_event_wait_ms() (extmod/modselect.c, v1.29.0). Twin time only, no product effect.
- digital_twin/README.md and SPECIFICATION.md Part F / J.7: on the Unix port a scheduler step costs about 1.16 ms
  while any non-fd pollable is registered (6.9 us otherwise; S/u35/lead/tsf_poll.log), from modselect.c's 1 ms ioctl
  period under POSIX optimisations; rp2 has none. A protocol deadline over yield-heavy code is counted on a driven
  clock on the twin (UM4's text). BACKLOG.md candidate: twin fidelity of the poll step against rp2, for a later unit.
- Hardware-round reading: a CRC16 frame-and-ACK round trip on the dev bench under API load, against the 1000 ms ACK
  timeout (the per-byte yield's real cost on rp2).
- (lead, 2026-10-27T18:35) BACKLOG twin-fidelity candidate, add CMr1k's figure: 85 % of a silent-fetch twin boot is
  the Unix-port 1 ms poll per scheduler step while a ThreadSafeFlag and a socket both wait (rp2 polls once); the
  NTP and clock-jump files grew to 55.7-61.8 s and 31.0-34.6 s from the widening's added boots. A toolchain-level
  lever (the Unix test build's select path) is the owner's call, not this unit's.
- (lead) E.2.1: the clock-jump, NTP, SCD30, SGP40, launcher and runner twin tests run once per distinct wiring they
  reach (CMr1k), and the supervised-death test runs on the driven clock (CMr1l finding 4).
- (lead) CLAUDE.md's "Two suites that both bind real ports" bullet: its "overlap safely" covers the port-53 bind, not
  datagram delivery between processes sharing it; corrected text from N15's hand-back, plus digital_twin/README.md's
  shim section (the per-process loopback address).
