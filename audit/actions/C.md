# A-L C — phase C, the hardware rounds (HEAD b049724)

Sites read at `b049724`. Phase C (`audit/CONSOLIDATION.md` section 2: "Go-ahead per session. FRAM logs read and saved
first; lower levels run first; two-image GC proof; bench boot log and trigger timestamps; `reset_reason` codes proven;
twin corrected until it agrees; standard board state at start and end; bench Pi package check") runs after U37 (B5) and
before phase D. It is the collection point for every hardware duty planned elsewhere: the inventory below was built by
a scan of every earlier action file (`scratchpad/al/C/scan.py`, `ctx.py`, `th.py`: every action whose text names phase
C, "hardware in C", `Kind: hardware`, L3/L4, a wear marker, `mpremote`, a reflash or the bench, and every action whose
Site or Change touches `tests_hardware/{flash,bench,device_scripts,manual}` — 499 hits, 169 strong, 226 hardware-tier
test sites), each hit read, plus the 37 register blocks of `input_C.md`. Where a block's C clause had no instrument in
any earlier unit, the instrument is planned here (A.C.12-A.C.19) and co-lands with U26's work in the A-C order.

Standing rules applied to every action here: nothing runs on a board, on the bench Pi or against the bench network
without the owner's go-ahead given in that round's own conversation — "a go-ahead given to a different session, or to
an earlier session that already ended, does not carry over" and "Once granted, it covers the rest of that same
conversation" (CLAUDE.md:284-293); subagents and child sessions inherit none (plan 2.3). Only the `dev` board is ever
flashed, with a dev-native image built from its own TOML through its own generated entry point; `wozi` is never flashed
(CLAUDE.md:159-172). Text an action writes into a permanent file cites no audit ID (G9/R12, OR68.a (4)); IDs sit in
Why/Depends and `[src: …]` notes. Findings of a round pass A-C as a delta before they are applied (OR106.a). Marker and
flag names are the ones in force after U26 lands (A.U26.35, A.U26.74): `persistence_write` / `--allow-persistence-write`,
`scd30_extra_write` / `--allow-scd30-extra-write`, `flash_cycle` / `--allow-flash-cycle`, `soak_duration` /
`--soak-duration {short,mid,long}`, `multi_day_rollover` / `--allow-multi-day-rollover`, `neopixel_sweep` /
`--allow-neopixel-sweep`, `toolchain_reverify` / `--allow-toolchain-reverify`, `--repair-standard-state`,
`--skip-lower-levels` (debug only, never clean), `--image-record`.

## Actions

### A.C.01 Every round follows one frame
- **Why**: G1/R02 — "A Phase C round reads and saves the FRAM `errcount` before anything writes, builds and flashes a
  `dev` image of the tree under test, and proves the board runs it … Its runner first runs every lower level … flash/NVM
  writes only in a gated run after a clean default run; deselected counts read; an unanticipated red stops and is
  reported; ad-hoc retries capped, ad-hoc scripts under `timeout`. Each round's plan names order, expected outcomes, wear
  budget and the twin parameter each row confirms; results correct the twin until they agree" (owner A41 D1/D2
  2026-09-22; OR5.a (2), OR8.a, OR17.a (4)(5), OR28.a (1), OR45.a (2)(a) 2026-09-25/26); LEAD/R02 (standard board state,
  agent 2026-09-27); CLAUDE.md go-ahead rule (:284-293), FRAM rule and its caveat (:367-394), B.13 dead-man's switch
  (:295-301) and `br0` MAC pin (:302-306), WoZi rule (:159-172), wear rule (:249-283); OR2.c (hardware items parked,
  never decided in execution); OR106.a (C findings pass A-C as a delta).
- **Site**: the rounds A.C.02-A.C.09; each round's record `audit/c/R<n>.md` (audit working file, deleted at phase D,
  harmonization 19); the permanent procedure text is A.U36.001's `tests_hardware/README.md` "How a round runs".
- **Change**: every round, in this order:
  (1) **Go-ahead**: the owner's go-ahead for this round is quoted with its date at the top of the round record; without
  it nothing below starts. The record then states the plan: rows in order, each with its expected outcome, its wear
  (flash writes, SCD30 NVM writes, flash cycles; FRAM is not wear, G1/R04) and the twin parameter or fidelity row it
  confirms (OR17.a (4)).
  (2) **Bench host network** (CLAUDE.md :295-306, SPEC B.13): the session reaches the bench Pi over its wired uplink,
  checked first (`ip -o route get <session peer>` names the uplink or `br0`). `nmcli -g bridge.mac-address connection
  show br0` must equal the uplink's real hardware MAC as the installer reads it (`get_interface_mac()`,
  `toolchain/setup_toolchain.py:865`); a mismatch stops the round for the owner —
  never auto-repaired, since cycling a live bridge's MAC risks the lockout B.13 records (`ensure_bench_bridge()` itself
  only warns, `toolchain/setup_toolchain.py:843-880`). Every step that creates, tears down or reconfigures `br0` or one
  of its slaves — bridge creation by `env --tier bench` (armed by the installer itself, A.U21.23), the manual `br0`
  recipe, and every bench-tier run, whose tests take the `br0-wifi-ap` slave down, join the DUT's hotspot or install
  `iptables`/`tc` faults (`tests_hardware/bench_control.py:72-83, 201-246`; `bench/test_{network_resilience,
  hotspot_role_reversal,wifi_networking,end_to_end_timing,rest_endpoints_over_sta,bus_concurrency_under_api_load}.py`,
  `conftest.py`) — runs inside an armed recovery timer: B.13's recovery script recreated fresh in the session's
  scratchpad, `sudo systemd-run --unit=bench-recovery --on-active=<window>` with the window set to the run's measured
  duration plus margin (the first run of a kind: its runner's own overall timeout plus margin), armed state confirmed
  before the run, the outcome polled right after it (`ip -o -4 addr show br0`, a default route, the DUT reachable),
  then disarmed and confirmed gone. A timer that fires restores wired access; the round then stops and is reported.
  (3) **Evidence first** (CLAUDE.md :367-394, OR28.a (1), G1/R11): before anything writes to the board — before the
  first device script, reflash, reboot, `ResetErrors` or config PUT — the FRAM error logs are read and saved verbatim
  (A.U26.22's session fixture: `save_fram_raw(board, "session-start")` and `save_errcount(dut_ip, "session-start")`,
  the full `GET /status` body, `ResetReason` included once it exists) and copied from the evidence directory into the
  round record, so the evidence archive's rotation never drops a round's evidence while the audit runs. Caveat stated in
  the record every round: an isolated-driver device script builds its own FRAM manager over the same chip and its first
  chunk is production's first chunk, so after the flash tier has run, a FRAM-backed history is evidence only of what ran
  since; before treating one as evidence, the record names what has run against the board (CLAUDE.md :387-394;
  A.U26.22 (5) makes each script clear its own chunk).
  (4) **Lower levels first**: the round's commit is recorded (`git rev-parse HEAD`, dirty flag); the flash and bench
  runners run L0, L1 and L2 at both GC stages on it and stop before touching the board if one fails
  (`scripts/_run_lower_levels.sh`, A.U7.18); a round never uses `--skip-lower-levels` for a reported result.
  (5) **Image**: `scripts/build_firmware.py <bench device>` with the bench device taken from data (`bench_device_name`,
  A.U26.01; `dev` today, never `wozi`), which writes the image record beside the `.uf2` (A.U26.02); the board is flashed
  by the README's "Flashing a real board" steps (the harness `reflash()` helper, A.S0930.06 (2) with A.U26.14's
  exit-249-only retry). This flash is the round's planned prerequisite write, listed in its wear budget (A.U1.06's tool
  table); a local-only image (built in a throwaway worktree, record `dirty: true`) is reverted to the round's standard
  image at once after the rows that need it (G1/R02).
  (6) **Image proof and standard state**: the bench tier's `board_image` fixture compares `/system`'s build date and the
  lwIP ensemble with the image record before any bench test (A.U26.03); `standard_state` checks the board at session
  start and end — release image, `DebugLevel` 5, FRAM write-protect clear, no `config_HWTEST_*` file, SCD30 snapshot
  unchanged at the end (A.U26.79); a deviation fails the session start unless the round's plan names
  `--repair-standard-state`, whose writes are listed prerequisites.
  (7) **Order and gates**: default flash tier, then default bench tier (`scripts/run_bench_hardware_suite.sh` runs L3
  as its own step, then L4, A.U7.18), each verdict's deselected count read and recorded, not only "clean" (A.U7.14);
  a gated run only after a clean default run of the same image in the same round (owner D1, 2026-09-22, BACKLOG.md:
  353-358), with only the flags the round's plan names; ad-hoc scripts run under `timeout` with retries capped
  (`tests_hardware/README.md` "Bench traps"; A.U26.13/A.U26.29 report every recovery as a recovery pass).
  (8) **End**: the board is left on the round's release `dev` image in the standard state (A.U26.79's end check), the
  final `errcount` saved; the record lists every `ResetReason` seen, the boot log (A.U26.41 (1), saved every round) and
  every measured figure with its image.
  (9) **Failure** (every round): an unanticipated red stops the round at that row and is reported to the owner with its
  evidence; nothing is retried to green, no bound is widened to pass, no hardware item is decided in the session (OR2.c:
  parked for the owner). A defect a round proves goes the OR12.a path as a delta (regression test first, then fix), and
  the round's affected rows re-run on the fixed image under the same conversation's go-ahead. Named cases: a failed lwIP
  bound goes to the owner as a change to the modlwip override (a short POLLOUT back-off after `EAGAIN`, AC_NOTES 21,
  OR114.a), never a larger bound; a watchdog-coded reset (`ResetReason` 2) where an attributed code was expected, a fed
  hang, or a feed gap ≥ 8,000 ms in the controlled shutdown sequence is an OR120.a / OR130.a defect; a failure on a
  moved firmware pin goes to the owner with the choice to hold the pin back (OR129.a (5), A.SDEP.08).
- **Blast**: callers — · generated the `dev` image, built per round · js — · tests the fixtures named (A.U26.03,
  A.U26.22, A.U26.79), the runners (A.U7.18, A.U7.14) · twin every row names its twin parameter; A.C.10 applies the
  corrections · docs A.U36.001's "How a round runs" is this frame's permanent text; the round records are audit files ·
  toml — · uart —.
- **Depends**: all of U0-U37 executed and A-C's delta list applied; A.U7.14, A.U7.18, A.U26.01-A.U26.03, A.U26.13,
  A.U26.22, A.U26.29, A.U26.79, A.U36.001, A.S0930.06 (2).
- **Kind**: rule, hardware

