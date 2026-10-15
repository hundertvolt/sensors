# U26 close: owner questions (draft, at most 3)

Each entry is in BACKLOG.md's "Owner questions" form (CLAUDE.md decision-records rule (4)): a decision in at most 10 words, then
the options, each with its consequence per device and bus. BACKLOG.md's list holds entries 1 and 2 at `ee42b0e`, so these would
be 3, 4 and 5 (renumber, never reuse). The entry text carries no audit ID; the notes under it do.

## 3. The SCD30 NVM writes the extra-write flag admits

Entry text (decision line: 9 words):

- **3. Cap the SCD30 NVM writes the extra-write flag admits?** (entered 2026-10-15, agent) The SCD30 keeps its settings in an
  on-chip NVM for which Sensirion publishes no endurance figure. Hardware tests write it only behind `--allow-persistence-write`,
  and a test spending more than the one write that flag admits needs `--allow-scd30-extra-write` on top. The documented rule
  caps a session at one SCD30 write, the extra flag being for one test firing it "a second time"; the tests now carry more.
  (a) keep what the tests carry: with both flags, one flash-and-bench session on `dev` spends up to 13 owned writes to its
  SCD30 on `i2c1` (1 under the global flag; under the extra flag 2 and up to 3 on the flash tier, up to 3 and 4 on the bench
  tier), plus at most one start command the session itself may send; a default run spends 0, at most 1; the manual power-cut
  steps state theirs (up to 22 and 2) before each confirmation. (b) one further write per session: the extra flag admits a
  single further owned write, so its five tests run one per session, chosen by name, and covering all five takes five sessions
  on `dev`. Either way the SCD30s of `arzi`, `grkizi`, `klkizi`, `schlafzi` and `wozi` (each on `i2c0`) are never written by a
  test: only `dev` is flashed. Until answered: (a), what the tests carry.

Notes for the lead (not entry text):
- The 2026-09-16 cap, quoted: SPECIFICATION.md:3528-3529, "**SCD30's own on-chip NVM write is opt-in, off by default, and capped
  at one real write per test session** (owner, 2026-09-16, `98dc1b2`)", and :3539-3540, "Any additional test that needs to fire
  SCD30's own write a second time is gated behind a further, narrower flag/marker pair". The owner's own words are NOT found:
  `98dc1b2` (2026-09-16, an agent commit) says "Per project-owner direction, every real SCD30 write now requires the single global
  --allow-scd30-writes permission ... with --allow-scd30-extra-write AND-gated on top of it for the one test that spends a second
  write"; `4f1c802` (same day) says the two-flag shape "was intentional all along - confirmed directly by the project owner"; the
  question asked is not recorded. `audit/DECISION_PROVENANCE.md` row A16 marks it "owner-claimed" and asks to "Recheck the budget
  under OR42.c (4): an unchanged value will no longer spend a write."
- The counts are `tests_hardware/README.md`'s budget table at ee42b0e (the "`--allow-scd30-extra-write`" row: flash
  `test_scd30_config_write_does_not_disturb_concurrent_sibling_reads` 2, `test_scd30_argument_reaction_is_recorded` up to 3;
  bench `test_scd30_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load` up to 3,
  `test_scd30_altitude_takes_effect_while_ambient_pressure_is_zero` 4; the global row
  `test_scd30_same_device_read_write_concurrency` 1; the prerequisite 0-1). "No published endurance figure": SPECIFICATION.md:10259.
- Lane X's meaning change in CLAUDE.md (review list) made the wear rule read "the further SCD30 NVM writes beyond those
  `persistence_write` admits", following the code; SPEC C.8 still carries the "second time" text, so the two now differ in reach.
  Lane X's hand-back: "Still open for the owner: SCD30 two writes per session against the 2026-09-16 cap."
- Bus facts from `devices/*.toml` at ee42b0e (the `scd30` instance's `bus`).

## 4. The SCD30 soft reset at every boot and task restart

Entry text (decision line: 8 words):

- **4. Keep the SCD30 soft reset at every start?** (entered 2026-10-15, agent) Every boot, every restart of the SCD30's read
  task and the second consecutive failed read send the SCD30 its soft reset, which puts the sensor into the state it has after
  powering up (Interface Description 1.4.10). A power loss within the first 7 days after automatic self-calibration (ASC) is
  switched on aborts its search for calibration parameters (1.4.6); whether a soft reset does the same is not stated, and the
  sensor reports no ASC progress, so the bench cannot measure it. (a) keep it: on every device a boot or a read-task restart
  soft-resets the SCD30 (`i2c0` on `arzi`, `grkizi`, `klkizi`, `schlafzi` and `wozi`, `i2c1` on `dev`) and waits 2.5 s; if the
  reset counts as a power loss, a device rebooted within 7 days of switching ASC on restarts its search, and a sensor left
  mid-command by the previous run always starts clean. (b) reset only on the failed-read rung: boots and task restarts no
  longer reset the sensor, so ASC's search survives a reboot whatever the reset does, and the first read after a boot takes the
  sensor as the previous run left it, a confused sensor recovering at its second failed read instead. Until answered: (a), the
  current behaviour.

Notes for the lead (not entry text):
- SPECIFICATION.md:302-311 ("Every boot, every SCD30 task restart and the participant rung send the soft reset ... whether a soft
  reset does the same is not stated there (agent, 2026-10-06)") and :10238-10243 ("Each read-task (re)start, supervisor restarts
  included, sends a soft reset and waits 2.5 s and never a start-continuous command (owner, 2026-09-26)"). Option (b) changes an
  owner decision of 2026-09-26 (paraphrase in SPEC; the owner's words not looked up here), so it is put as a question, not taken.
- The open point is a README bullet (`tests_hardware/README.md:1221-1222`); M.HW_BENCH.131 (1) calls "whether that boot reset is
  needed" the owner-review question; lane X's hand-back: "The ASC owner question is not written."
- `src/asy_scd30_driver.py:876-880` `reset()` (the 2.5 s wait, `scd30.soft_reset_wait_s`); the SelfCal field's own description
  already warns of the 7-day search (`:132`). Option (b) is a `src/` change at the driver's next unit (U30).

## 5. The UART comm hazards under the bench's API load

Entry text (decision line: 8 words):

- **5. Leave the UART hazards under API load untested?** (entered 2026-10-15, agent) `dev`'s two UART links (`uart0` initiator,
  `uart1` responder, joined by the bench's crossover jumper) have their comm hazards (two initiations at once, both ends
  transmitting, boundary values, a stalled transmit) and the field sweep tested on the board with the firmware stopped, and in
  the digital twin. Under the bench's real API load only the link's normal multi-chunk echo runs, because the hazard script
  needs the raw UART pair while a serving firmware owns it. (a) leave it so: on `dev` the hazards are proven with the firmware
  stopped and the link's normal traffic under load, but no hazard with the web API busy beside it; no other device has a UART
  link. (b) add a hazard mode to the firmware's own UART exerciser, driven from the bench test while readers hammer the API:
  a firmware change for `dev`'s build only (the exerciser is wired on `dev` alone), and one more bench test of about the
  hazard script's length. Until answered: (a).

Notes for the lead (not entry text):
- OF-180 (lane E's deviation 1; the lead's review list E1, "-> open finding + owner report"). The CLAUDE.md rule it meets: "A new
  device on a shared resource ... gets hazard test coverage across all four test tiers that apply to it — never forget this"
  (owner, 2026-09-03, `da3a5b5`: 'note down to never forget this'; every shared resource, owner, 2026-09-26). The gap is recorded
  as E.6.6 row `uart-hazards-under-api-load` (SPECIFICATION.md:4976, agent, 2026-10-14).
- (b)'s files: `src/asy_uart_link_driver.py` (next unit U32), `tests_hardware/bench/test_uart_link_under_api_load.py` and
  `tests_hardware/device_scripts/uart_comm_hazards.py` (U36). The UART wire format is not touched in either option.

## Not asked

- OF-122, OF-127 and OF-36 keep their stated defaults (R-13); none is in BACKLOG.md's list at ee42b0e (they were put at the U21
  and U11 unit ends). dev's receive ring (lane D2's 8192 relay) has a standing agent decision and a parked measurement (C), not a
  question. Every other U26 item has a conservative default and an agent target (`of_updates.md`, `of_new.md`).
