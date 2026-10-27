# Items for the U35 owner report (lead, 2026-10-27)
Append-only. Items named before LEAD NOTES 242 are in S/u35/lane_plan.md: grep "owner report", "report", "refus",
"deviation" and "1d" there when the report is written; this file collects them from LEAD NOTES 242 on, each with its
source.

- D.10 observation, no change: the per-file `_driven`/`_driven_modules` helpers (timer_pool and hot_replug carried
  identical copies at base; clock_jump follows the idiom since f2fd7565). Recommendation: one shared helper in a later
  unit, once the D.15 question over the unchecked scopes is answered (LEAD NOTES 242; CMr1d.md).
- Unix-port fidelity gap, found by CMr1e and checked by the lead in v1.29.0's extmod/modselect.c :344-381 against
  rp2's :383-397. With any non-fd pollable registered (a ThreadSafeFlag), every zero-timeout poll waits 1 ms on the
  Unix port; rp2 returns at once. That makes the twin's scheduler rounds slower than silicon's. In U35 the skip
  (digital_twin/unix_port_idle_poll.py) applies only in the hot-replug twin file, proven equivalent there. Options:
  apply the skip suite-wide, or bound the wait by the timeout in toolchain/micropython_overrides.py (a toolchain
  change, every binary rebuilt). The lead's recommendation goes in the report (LEAD NOTES 245; CMr1e.md).
- The CS settle `time.sleep_us(2)` costs about 95 us on the Unix-port host against about 2 us on silicon: a second,
  smaller fidelity gap of the same kind, left as is (CMr1e.md).
- Deviations, each named by its lane: CRr2b6 appended to its own log file with a heredoc (LEAD NOTES 244); T4r3c
  re-places a wrap miss at either stage (misses never count; LEAD NOTES 243); T4r3c amended dev -1's record in place,
  marked (LEAD NOTES 243); CMr1d linked buildgen into its base copy after an ENOENT, root-caused (LEAD NOTES 242).
- CRr2b6 ran to 124 tool calls by the harness count, against the 80-call seam (LEAD NOTES 244).
- Allow-list growth, adopted by the lead: SPECIFICATION E.6.6 gains one `twin-instrument` row,
  `test_digital_twin_unix_port_idle_poll` (L3, L4). It is a twin-only test of a twin-only helper; the branch it
  covers is one rp2 compiles out, so it has no silicon counterpart. It follows the existing
  `test_digital_twin_unix_port_unretrieved_report` row. Added by CMr1f in 6f41678e, flagged by the lane, adopted by
  the lead (LEAD NOTES 250).
- The idle-poll skip is used per file, only where its cost is measured and its equivalence proven on that file's own
  rounds: hot_replug, and ntp if CMr1g's proof holds. The suite-wide question stays with the report (LEAD NOTES 250).
- Correction (LEAD NOTES 252): the Unix-port 1 ms poll is not a new finding. U35's lane V recorded it as OF-243,
  SPEC F.7 row 30 states it, and OF-243 routes its end state (the toolchain override) to U36, with OF-200
  (test_sensortask's duration) beside it. CMr1e's per-file skip is interim U35 relief, with a removal trigger for
  when OF-243's fix lands. The report states it that way, not as an open question.
- Lead deviation: four LEAD NOTES were appended with unquoted heredocs. One backticked name ran as a command (it was
  not found, and nothing else ran), and the note was repaired. The lead uses quoted heredocs only from 07:21 (LEAD
  NOTES 254).
- Rule breach by a lane: CRr2b8 used `git stash push`/`pop` to commit one item alone, against CHECKLIST 1. It was
  self-reported, and nothing was left stashed. The next brief restates the ban (LEAD NOTES 255).
- Added bench time: the ISL29125 Calibrate test now waits out its own calibration run (up to 120 s plus one
  SampleInterval plus 10 s), about +2 min per bench run. The run has no observable end before its window closes, and
  a shorter wait lets its timeout warning land in the next test's log window (LEAD NOTES 255).
- Refusal: the harness refused Q35's Write of its own summary file ("Subagents should return findings as text"). The
  lane did not retry; its content is in its saved hand-back (LEAD NOTES 256).
- Rule breach by a lane: CRr2b9 started one twin run as a nohup chain. It ran to rc 0, the lane self-reported it, and
  the next brief restates the rule (LEAD NOTES 258).
- Twin file times, base before U35's widening -> now (-1 / 32768): hot_replug -40 % / -30 %, clock_jump -30 % / -26 %,
  ntp +2.5 % / +12.1 %, bus_hazard +24 % / +32 % (bus_hazard's last lever still being tried). ntp's residual is the
  Unix-port poll tax on rounds with a socket registered (OF-243, root fix in U36). A wider skip measured ntp at
  10.9 / 13.6 s; the lead declined it so the interim helper's scope stays what was proven (LEAD NOTES 259).
- D.10 observation update: five twin test files now carry the per-file `_driven_modules` helper (timer_pool and
  hot_replug at base; clock_jump, ntp and bus_hazard since). Recommendation: one shared helper in U37's sweep
  (LEAD NOTES 259).
- Firmware defect fixed (conformance lane): I2C bus-clear and controller rungs stepped their recovery counter only
  after waiting for the bus lock, so a second reader queued behind a sibling session ran the same rung again (two
  clears, two warnings for one episode) and the first then skipped its controller rung. The counter now steps on
  entry; red-first test. Lead decisions (agent, 2026-10-27), open to the owner's override: a rung cancelled during
  its lock wait counts as run (only the shutdown sequence cancels readers); two readers whose setups fail together
  each rebuild the controller once, as `_init_failed()`'s own-episode design states.
- Allow-list growth (lead): the outage and flap bench tests' provocation sets gained NTP's mid-flight entries
  (NTP_DNS_NOT_SENT, NTP_DNS, NTP_NOT_SENT, NTP_NO_REPLY; lane CRr2b10) and E NTP_RETRIES (lead, 93c2dcbb), each
  shown reachable by a bite, since the CYW43 false positive keeps the link "up" through an outage.
- Accepted by reading (lead): _set_dict_cfg's request-sized allocations are bounded by the 2048 B body cap and have
  no alternative flow, so Microdot's dispatch catch is their handler.
- Firmware defects fixed (raising lane BR2, asy_system_service.py), each a raise that left lasting state, each with a
  red-first test: an erase command whose preflight raised wedged the shutdown gate until reboot (later commands
  answered from the stale gate, every storage pause refused); an auto-unpause that raised left storage paused until
  reboot; a raise in the boot-signature log line let the task's restart draw a second signature, which clients read
  as a reboot.
- Firmware defect fixed (raising lane BR3, asy_fram_manager.py): a chunk read's data copy could raise MemoryError
  out of the never-raise FRAM module; it now degrades to the not-read result with one logged entry, red-first test.
- Lane hygiene (named): BR3 made its one src edit with an inline string replace instead of the edit tool (same
  diff); BR2 rewrote its own two unpushed commits with `git reset --soft` (final tree identical).
- Lead process hole (closed): the lead's merge checks did not run the audit record checks (raising walk, e51 and
  review rows --check), so the CMr1 merge brought six review rows with no verdict unseen; found by lane CO2. The
  generic merge check now runs all three; the six are given their verdicts by lane BR4.
- Allow-list growth (lead, 34cd5235): the bus flapping bench test's set gained E NTP_RETRIES, shown reachable by a
  bite on the same false-positive path.
- Lead decisions, test-only (CHECKLIST 1d): the SCD30 sibling-write script's writer now waits for an SGP40 read in
  flight so its overlap check holds on every healthy run (no write added); the HTTP bench counterpart of the ISL
  overlap test cannot prove bus overlap (GET /sensors does no I2C), so the flash tier keeps that proof and the bench
  test states what it proves.
- Lead decision, test-only (CHECKLIST 1d): a twin test whose booted task graph runs beside its subject counts that
  graph's bus, LED and FRAM traffic as reach, so it runs on each distinct wiring of what that graph reaches (the
  NTP offset change, the clean-log first sync, the loop-end tests). The conservative reading of the device rule.
- The device-pick widening of four Wi-Fi integration scenarios slowed that file by about half on two devices; per
  the owner's rule it is not dropped for time: those scenarios get a driven clock first, then the widening lands,
  and whatever growth remains is reported with its cause.
- bus_hazard: the SCD30 command and erase-race tests now drive their boot (about 9-12 s off the file per stage);
  the 18 s the first attempt added was a harness artefact (one supervisor check per command), root-caused.
- Heap, task restarts (the silicon question): a supervisor restart does not leak (every kind restarted 24 times on
  two devices at both stages, flat). The twin's 147 KB step per in-process re-boot was the ntp test linking its boots
  through an upstream MicroPython quirk (a finished asyncio task stays reachable from its last parent's stale
  pointer); the test link is cut. Whether that quirk can pin a growing chain under connection churn is measured
  (HP2's result goes here), and whether to report it upstream is the owner's call.
- For the hardware round: on rp2 (not on the twin), `poll.unregister()` leaves the unregistered socket referenced
  until its slot is reused; bounded, a heap reading after many webserver connections settles it (HP2's bound).
- Lane hygiene (named): N11c edited four test files with a Python heredoc instead of the edit tool (each file's AST
  checked identical after substituting the constants back); CMr1i ran about 50 % past its hand-back seam.
- Owner option (b) done: the runtime dict check on the config write's results is removed (every override's result is
  a dict under mypy strict; the SCD30 override's three type-ignores are on other paths). The web error catalog's
  errno 5 text now reads "the _set_mgr_cfg() extension point raised", since the malformed-result case is gone.
- Raising paths: every raising call and raise in the walked modules is classed (handled 592, unreachable 538, and the
  three defect sites, all fixed).
- Lead process hole (closed): the raising record's header named the last commit that changed src/, so a commit that
  changed src/ could never carry a current record; found at the merge, re-rendered, and the tool is being fixed.
- Lane hygiene (named): BR4's first runner ran a test file's two stages at once in one scratch directory (two reds,
  root-caused, green when re-run one after the other).
- Lead process holes (closed): the merge checks from one point on ran seven reader files of the build-script tier,
  not the whole tier as the lane rules said; and one fast-forward merge ran only the record checks. Two reds got
  through to the integration branch that way (a new member out of the house order, two new twin scenarios with no
  hardware counterpart or reason row), found at the next merge and fixed in-unit. The whole tier is run again on
  every merge and by every lane on its final head.
- UART, owner option (c) done: a piece buffer that cannot be built is a UART fault with the protocol's own recovery
  (changelog A17, B90); the dev echo now streams its answer from the stored pieces instead of one 12 KB allocation
  (B91, no byte on the wire changes).
- Heap, the stale task pointer (HP2): bounded and transient, at most 8 finished tasks held at once under heavy web,
  UART and NTP/DNS churn, no growth with uptime or connections; no firmware defect. Hardware-round readings: the heap
  after many webserver connections (rp2's stale poll slots, at most 12-17, about 2.3 KB).
- Lane hygiene (named): HP2 ran two twin processes at once in one worktree, sharing a scratch directory (its
  sequential runs reproduce the same bounds).
- Owner decision (2026-10-27): the stale task pointer is left as it is, with no override and no report now; it and the
  chip's stale poll slots open a BACKLOG.md list of upstream findings to report later as one bundle, if at all, and
  Part F records both with their measured bounds.
- The typing-only checks (owner's rule, both conditions): 196 runtime type checks in src/ inventoried; 14 that only
  guard what mypy already enforces, and that today's code cannot reach, are removed (frozen image 378 B smaller);
  12 int checks stay, because MicroPython's isinstance refuses a bool that mypy lets through as an int, so typing
  alone does not cover them. The house member order restored for one new FRAM helper.
- Lane hygiene (named): D2S applied 23 citation edits in two audit data files by script (after a reviewed dry run).
- Lead process (named): the bench-test lanes' merge was checked only by the full gate, which then showed one new red
  (an unencoded text read in a bench test); a one-word lead fix. Two UART hazard tests failed at 32768 under host
  load against a 10 s real-time bound that was only ever estimated; root-caused by measurement in a lane, not retried
  away.
- Wi-Fi and reboot-record tests: the four Wi-Fi integration scenarios and the Wi-Fi modes file run on a driven clock
  and on every distinct device wiring; the reboot-record tests on four wirings instead of one; the three files
  together take about the same time with 30 more device runs.
- A heap-drift test that a healthy run failed once under load (on the base tree): taken as a test defect, its cause
  measured and its check reformed in a lane; and the Wi-Fi scenarios' log checks extended from RAM to FRAM.
- Lane hygiene (named): CMr1j ran one 30 s test-reader run outside the network namespace.
- The UART merge and walk verdicts are in; the walk shows nothing open. The unexplained CRC16 UART test failure is
  root-caused: on the desktop MicroPython build the simulator runs on, every scheduler step costs about 1.2 ms while
  an input wait is registered, against 7 us otherwise (the Pico build has no such wait), so a CRC16 frame's per-byte
  yields crossed the 1 s ACK timeout under host load. No firmware change: the tests count that deadline on a driven
  clock; the real round trip on the Pico is a reading for the hardware round. A simulator UART timing defect found
  on the way is fixed with its own test.
- The recovery-path cells are all closed with tests; no firmware defect. The FRAM read fault's log pair is measured:
  four entries per boot, nothing evicted, nothing more for the rest of the run; kept as it is (no owner question
  needed on these facts). A new bench check confirms each chip's setup reset, with volatile writes only.
- Lead merge note: the recovery lane's new DNS test was written against the old helpers that the Wi-Fi lane had moved
  to a driven clock; adapted in the merge and its planted-fault check replayed.

## N11d and CMr1l (lead, 2026-10-27T17:47)
- The gate's timeout reds on the UART hazard tests are root-caused. Under the gate's load, the three hazard runs reach
  their 10 s bound after about 2 s of CPU at 32768. No change brought it: base and head are the same.
  - Fixed by efficiency (N11d): a driven sleep costs 128 B and 22 us, down from 608 B and 27 us.
  - The lead decided (N11e) to run the hazard tests at the bench device's configured poll rates, as the twin
    already does. Verdicts are unchanged, CPU is about 3x lower, and the 10 s bound stays, to be measured. This is a
    test-only call the lead may make (CHECKLIST 1d).
- The ThreadSafeFlag poll artefact accounts for 12.6 s of test_sensortask[dev]'s wall time (16 tests).
- The waits scanner was fixed and bitten (9/9 plants). Every one of the 1003 sites is classed by reading; the
  last real waits are tagged by N11e and CMr1k.
- The drift check (CMr1l) runs on one driven clock: healthy 36/36 at slope 0.0, the 32 B and 64 B plants fail 12/12.
  - The two transients were twin artefacts: the watchdog's per-feed countdown tasks pinned by a stale child_last,
    and one stale C-stack word.
  - The parked form narrowed what the check sees, so a concurrent arm follows (CMr1m).
  - A hung cleanup cancel found on the way is being root-caused (CMr1m), in case it is a product defect.
- The FRAM read-back now covers the four widened Wi-Fi scenarios, and both bites fail 12/12.
- Merge note: N11d had tagged a real sleep that CMr1j had already moved to the driven clock. The lead dropped the tag
  in the merge, and CMr1k got the ntp/clock_jump sites by message so that cannot happen again.
- CMr1k (lead, 18:35): the clock-jump, NTP, SCD30, SGP40, launcher and runner twin tests now run once per distinct
  wiring they reach, each with a bite. The NTP tests' boot-to-boot link that kept every earlier boot alive (147 KB
  per re-boot) is cut. The last real waits in those files are tagged and measured. The files are slower (NTP up to
  62 s at 32768), mostly from the twin's 1 ms poll artefact: recommended as a twin-fidelity follow-up, the owner's
  call.
